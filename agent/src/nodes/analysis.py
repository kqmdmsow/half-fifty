"""Analysis Agent: 조항별 4종 출력 생성.

① 쉬운 설명 ② 위험 여부/유형 ③ 위험 근거 ④ 확인 질문

src/prompts/analysis.txt 프롬프트로 MODEL_WORKER를 호출한다.
JSON 파싱 실패 시 1회 재시도하고, 그래도 실패하면 "주의" + 수동 확인 안내로 폴백한다.

구조적 위험 체크리스트(임대차 계약서 밖 위험 — 등기부 2회 확인·깡통전세·전입신고·
신탁 임대인·HUG 가입)는 2026-08 팀 결정(#65)으로 LLM 파이프라인 밖의 프론트 카드로
구현이 이관됐다: 잔금일 타임라인·깡통전세 계산기·가중 요인 체크·HUG 배너
(frontend JeonseCalculator/JeonseTimeline). 여기 있던 고정 부착 코드는 judge 채점
오염 문제와 함께 제거됨 — 근거 리서치는 docs/jeonse_fraud_causes_research.md.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

import logging

logger = logging.getLogger(__name__)

from src.llm import get_worker_llm, invoke_json
from src.citation_check import find_fabricated_quotes
from src.schemas import AnalysisOutput
from src.state import AnalysisResult, PipelineState

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "analysis.txt"
_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")

_PARSE_ATTEMPTS = 2  # 최초 시도 + 재시도 1회
_FALLBACK_EVIDENCE = "분석 실패 (수동 확인 필요)"

# 구조적 위험 체크리스트 본체는 제거됐지만(#65) eval.py가 이 clause_id로
# 리콜·오탐 집계에서 방어적으로 필터링하고 있어(STRUCTURAL_RISK_CLAUSE_ID
# import) 상수만 남긴다 — 지우면 eval.py가 ImportError로 죽는다.
STRUCTURAL_RISK_CLAUSE_ID = "checklist_structural_risk"

# 프롬프트 캐싱: {clause_text} 앞의 정적 부분(위험 유형 정의·규칙·앵커 예시)은
# 조항 호출 간 동일하므로 캐시 블록으로 분리한다. 도메인 컨텍스트는 프리픽스에
# 주입되지만 문서당 상수라 캐시 효율을 해치지 않는다 (_build_prompt_parts 참조).
_PROMPT_PREFIX, _PROMPT_SUFFIX = _PROMPT_TEMPLATE.split("{clause_text}")

# 문서 유형명·[표준 조항 예외] 판정 기준 문구는 조항 원문이 아니므로 따옴표
# 인용 금지를 명시한다 — 출처 표지(민법/보호법/제N조 등) 없이 이 문구들만
# 인용되면 find_fabricated_quotes가 창작 인용으로 오판해 위험 판정이 폴백되는
# 사례가 실측됐다(이슈 #70). citation_check 검사 범위는 조항 원문으로 좁게
# 유지하면서(#69) 이 프롬프트 지시만으로 오탐을 막는다.
_DOMAIN_CONTEXT_KNOWN = (
    "[문서 유형] 이 조항이 속한 문서는 {domain} 유형으로 판별되었습니다{evidence_part}. "
    "유형에 따라 판정이 갈리는 규칙(차임 연체 해지의 주택/상가 구분 등)은 "
    "이 문서 유형을 우선 적용하세요. 단, risk_evidence에서 이 문서 유형명이나 "
    "[표준 조항 예외]의 판정 기준 문구(예: 2기 이상 연체 시 해지)를 근거로 "
    "언급할 때는 따옴표로 감싸지 말고 말로 풀어 서술하세요 — 따옴표 인용은 "
    "조항 원문을 그대로 옮길 때만 쓰는 것으로 한정합니다."
)
# 도메인 미상이면 컨텍스트 줄을 아예 넣지 않는다 — 무도메인 프롬프트가 v2.1과
# 바이트 단위로 동일해져 평가·폴백 경로의 회귀가 원천 차단된다 (문구 실험 결과
# 어떤 안내문이든 넣으면 train/val 판정이 미세하게 흔들렸다).


def _build_prompt_parts(domain: str = "", domain_evidence: str = "") -> tuple[str, str]:
    """(cached_prefix, suffix) 조립 — 도메인 컨텍스트는 프리픽스에 주입.

    도메인은 문서당 상수이므로 같은 문서의 조항들끼리 캐시가 히트한다
    (도메인 미주입 시에는 전 문서 공유 프리픽스라 기존 캐싱과 동일).
    """
    if domain and domain != "알 수 없음":
        ev = f"(근거: {domain_evidence[:80]})" if domain_evidence else ""
        ctx = _DOMAIN_CONTEXT_KNOWN.format(domain=domain, evidence_part=ev)
        prefix = _PROMPT_PREFIX.replace("{domain_context}", ctx)
    else:
        prefix = _PROMPT_PREFIX.replace("{domain_context}\n\n", "").replace("{domain_context}", "")
    return prefix, _PROMPT_SUFFIX


def build_prompt(text: str, domain: str = "", domain_evidence: str = "") -> str:
    """전체 프롬프트 문자열 (평가 하네스용 — 캐싱 없이 단일 문자열이 필요할 때)."""
    prefix, suffix = _build_prompt_parts(domain, domain_evidence)
    return prefix + text + suffix


# 조항 분석은 서로 독립이라 병렬 호출한다. API rate limit을 고려한 보수적 동시성.
# 기본 5(보수적). API 티어가 허용하면 LLM_CONCURRENCY 환경변수로 상향 —
# 조항 분석·페르소나가 병렬 폭만큼 빨라진다 (16조항 기준 5→10이면 약 절반).
_MAX_CONCURRENCY = int(os.getenv("LLM_CONCURRENCY", "5"))


def _analyze_clause(clause_id: str, text: str, domain: str = "",
                    domain_evidence: str = "") -> AnalysisResult:
    prefix, suffix = _build_prompt_parts(domain, domain_evidence)
    llm = get_worker_llm()

    for attempt in range(_PARSE_ATTEMPTS):
        try:
            # Pydantic 검증: 스키마 이탈은 예외 → 재시도. 사소한 이탈(리스트
            # risk_type, 번호 접두사)은 스키마 정규화가 흡수한다 (src/schemas.py).
            data = AnalysisOutput.model_validate(
                invoke_json(llm, text + suffix, cached_prefix=prefix))
            # 인용 원문 존재 검사 (자문 §5, 규칙 기반): 창작 인용은 스키마
            # 위반과 동급으로 취급 → 재시도, 소진 시 폴백.
            # 검사 대상은 조항 원문(text)만 유지한다 — 프롬프트 전체(prefix+suffix)로
            # 넓히면 모델이 프롬프트 안의 예시 문구를 조항과 무관하게 그대로
            # risk_evidence에 베껴도 "입력에 있으니 통과"로 새어나가는 구멍이
            # 생긴다(2026-08 실측, test_citation_check.py의 회귀 테스트 참조).
            # 도메인 주입 후 법령 인용 오탐은 citation_check.py의
            # _LEGAL_SOURCE_MARKER(출처 표지 기반 면제)만으로 해결되므로 검사
            # 범위 자체를 넓힐 필요가 없다.
            fabricated = find_fabricated_quotes(data.risk_evidence, text)
            if fabricated:
                raise ValueError(f"원문에 없는 인용 {len(fabricated)}건: {fabricated[0][:30]}…")
            return AnalysisResult(
                clause_id=clause_id,
                explanation=data.explanation,
                risk_level=data.risk_level,
                risk_type=data.risk_type,
                risk_evidence=data.risk_evidence,
                check_questions=data.check_questions,
            )
        except Exception as exc:  # JSON 파싱 실패, 키 누락, 스키마 검증 실패 등
            if attempt + 1 == _PARSE_ATTEMPTS:
                # exc는 창작 인용 30자(위 ValueError)나 LLM 원응답 일부(최대 200자,
                # src/llm.py invoke_json)를 담을 수 있어 종류만 WARNING, 전체
                # 내용은 DEBUG로만 남긴다 (#58, privacy_data_handling.md 정합).
                logger.warning("%s 분석 실패, 폴백 처리: %s", clause_id, type(exc).__name__)
                logger.debug("%s 분석 실패 상세", clause_id, exc_info=exc)

    return AnalysisResult(
        clause_id=clause_id,
        explanation=text,
        risk_level="주의",
        risk_type="해당 없음",
        risk_evidence=_FALLBACK_EVIDENCE,
        check_questions=[],
        analysis_failed=True,  # 프론트 현지화용 기계 판독 마커 (#100)
    )


def analysis_node(state: PipelineState) -> dict:
    """LangGraph 노드: clauses -> analysis_results.

    조항별 분석은 독립이므로 스레드 풀로 병렬 호출한다 (순서 보존).
    도메인 컨텍스트(문서당 상수)를 모든 조항 호출에 전달한다.
    """
    domain = state.get("domain", "")
    evidence = state.get("domain_evidence", "")
    with ThreadPoolExecutor(max_workers=_MAX_CONCURRENCY) as pool:
        results: List[AnalysisResult] = list(
            pool.map(lambda c: _analyze_clause(c["clause_id"], c["text"], domain, evidence),
                     state["clauses"])
        )
    return {"analysis_results": results}
