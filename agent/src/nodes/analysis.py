"""Analysis Agent: 조항별 4종 출력 생성.

① 쉬운 설명 ② 위험 여부/유형 ③ 위험 근거 ④ 확인 질문

src/prompts/analysis.txt 프롬프트로 MODEL_WORKER를 호출한다.
JSON 파싱 실패 시 1회 재시도하고, 그래도 실패하면 "주의" + 수동 확인 안내로 폴백한다.

docs/jeonse_fraud_causes_research.md 리서치 결론(전세사기의 대부분은 계약서 조항이
아니라 임대인 재무상태·시세조작·이중계약 등 계약서 밖 구조적 요인에서 발생)에 따라,
조항 분석과 별개로 항상 노출되는 구조적 위험 체크리스트(_STRUCTURAL_RISK_CHECKLIST)를
결과 목록 끝에 고정 추가하는 기능을 준비해뒀다. LLM 호출 없이 결정적으로 생성되며,
조항 원문에 대응하지 않는 항목이라 eval.py의 clause_level_labels.csv 매칭에서는
자동으로 제외되게 설계돼 있다(라벨이 없는 clause_id는 집계에서 건너뜀).

2026-07 팀 리뷰 결정: 모든 계약서에 도메인 무관하게 고정 부착되는 현재 방식은 이번
PR에서는 비활성화한다(_ENABLE_STRUCTURAL_CHECKLIST=False). 노출 위치·조건(예: 임대차
계약에서만 노출할지)에 대한 설계는 다음 PR에서 다룬다. 코드는 지우지 않고 그대로
남겨 다음 작업에서 이어갈 수 있게 한다.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

from src.llm import get_worker_llm, invoke_json
from src.state import AnalysisResult, PipelineState

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "analysis.txt"
_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")

_PARSE_ATTEMPTS = 2  # 최초 시도 + 재시도 1회
_FALLBACK_EVIDENCE = "분석 실패 (수동 확인 필요)"

STRUCTURAL_RISK_CLAUSE_ID = "checklist_structural_risk"

# 2026-07 팀 리뷰: 도메인 무관 고정 부착 방식은 이번 PR에서는 비활성화.
# 노출 위치/조건 설계는 다음 PR 과제 (코드는 유지).
_ENABLE_STRUCTURAL_CHECKLIST = False

_STRUCTURAL_RISK_CHECKLIST = AnalysisResult(
    clause_id=STRUCTURAL_RISK_CLAUSE_ID,
    explanation=(
        "이건 이 계약서의 특정 조항에 대한 분석이 아니에요. 전세사기 피해는 대부분 "
        "계약서 문구가 아니라 임대인의 재무상태, 시세 조작, 이중계약처럼 계약서만 봐서는 "
        "알 수 없는 곳에서 발생해요. 아래 항목은 조항 내용과 상관없이 항상 확인하는 게 안전해요."
    ),
    risk_level="주의",
    risk_type="해당 없음",
    risk_evidence=(
        "계약서 조항 분석만으로는 확인할 수 없는 구조적 위험 — "
        "docs/jeonse_fraud_causes_research.md 리서치 근거"
    ),
    check_questions=[
        "등기부등본을 계약 직전과 잔금 지급 직후 두 번 확인해 소유권·근저당 변동이 없는지 확인하세요.",
        "국토교통부 실거래가 공개시스템에서 같은 지역 시세와 비교해 보증금이 지나치게 높지 않은지(깡통전세 여부) 확인하세요.",
        "전입신고와 확정일자를 계약 당일 최대한 빨리 받아 대항력 발생 시점을 앞당기세요.",
        "임대인이 신탁회사이거나 등기부상 실제 소유자와 계약 상대방이 다른지 확인하세요.",
        "전세보증금반환보증(HUG 등) 가입이 가능한 매물인지 확인하세요.",
    ],
)


# 프롬프트 캐싱: {clause_text} 앞의 정적 부분(위험 유형 정의·규칙·앵커 예시)은
# 모든 조항 호출에서 동일하므로 캐시 블록으로 분리한다.
_PROMPT_PREFIX, _PROMPT_SUFFIX = _PROMPT_TEMPLATE.split("{clause_text}")

# 조항 분석은 서로 독립이라 병렬 호출한다. API rate limit을 고려한 보수적 동시성.
_MAX_CONCURRENCY = 5


def _analyze_clause(clause_id: str, text: str) -> AnalysisResult:
    llm = get_worker_llm()

    for attempt in range(_PARSE_ATTEMPTS):
        try:
            data = invoke_json(llm, text + _PROMPT_SUFFIX, cached_prefix=_PROMPT_PREFIX)
            return AnalysisResult(
                clause_id=clause_id,
                explanation=data["explanation"],
                risk_level=data["risk_level"],
                risk_type=data["risk_type"],
                risk_evidence=data["risk_evidence"],
                check_questions=data["check_questions"],
            )
        except Exception as exc:  # JSON 파싱 실패, 키 누락 등
            if attempt + 1 == _PARSE_ATTEMPTS:
                print(f"[Analysis] {clause_id} 분석 실패, 폴백 처리: {exc}")

    return AnalysisResult(
        clause_id=clause_id,
        explanation=text,
        risk_level="주의",
        risk_type="해당 없음",
        risk_evidence=_FALLBACK_EVIDENCE,
        check_questions=[],
    )


def analysis_node(state: PipelineState) -> dict:
    """LangGraph 노드: clauses -> analysis_results.

    조항별 분석은 독립이므로 스레드 풀로 병렬 호출한다 (순서 보존).
    """
    with ThreadPoolExecutor(max_workers=_MAX_CONCURRENCY) as pool:
        results: List[AnalysisResult] = list(
            pool.map(lambda c: _analyze_clause(c["clause_id"], c["text"]), state["clauses"])
        )
    if _ENABLE_STRUCTURAL_CHECKLIST:
        results.append(_STRUCTURAL_RISK_CHECKLIST)
    return {"analysis_results": results}
