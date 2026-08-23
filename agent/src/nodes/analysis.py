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
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

import logging

logger = logging.getLogger(__name__)

from src.llm import get_worker_llm, invoke_json
from src.citation_check import find_fabricated_quotes
from src.injection_check import (detect_injection, is_analyzable, quarantine,
                                 quarantine_notice, sanitize)
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


def wrap_clause(text: str) -> str:
    """조항 원문을 예측 불가능한 난수 구분자로 감싼다 (#174, 3층 구조적 격리).

    프롬프트로 "지시를 따르지 마세요"라고 설득하는 것은 확률적 방어다. 반면
    구분자를 난수로 만들면 **공격자가 구분자를 위조할 수 없다** — 문서를 쓰는
    시점에 이번 호출의 난수를 알 수 없기 때문이다. 위조 마커로 프롬프트 구조를
    가로채는 공격(`템플릿_마커_위장`)이 구조적으로 불가능해진다.

    난수는 반드시 **캐시되지 않는 구간**에만 넣는다. 캐시 프리픽스에 넣으면
    호출마다 프리픽스가 달라져 프롬프트 캐싱이 전부 무효화된다(원가 약 1.6배).
    """
    nonce = secrets.token_hex(8)
    return f"<<<CLAUSE:{nonce}>>>\n{text}\n<<<END:{nonce}>>>"


def build_prompt(text: str, domain: str = "", domain_evidence: str = "") -> str:
    """전체 프롬프트 문자열 (평가 하네스용 — 캐싱 없이 단일 문자열이 필요할 때).

    실제 호출 경로와 동일하게 무력화·격리를 거친다 — 평가가 운영보다 약한
    방어를 측정하면 수치가 실제를 과소평가한다.
    """
    prefix, suffix = _build_prompt_parts(domain, domain_evidence)
    return prefix + wrap_clause(sanitize(text)[0]) + suffix


# 조작이 탐지된 조항에 붙는 전용 risk_type (#174). 10가지 위험 유형 어디에도
# 넣지 않는다 — 약관 자체의 불공정성이 아니라 문서에 조작 시도가 섞였다는
# 별개의 사실이기 때문이다. 골든셋에는 등장하지 않으므로 평가 수치에 영향이 없다.
TAMPER_RISK_TYPE = "문서 조작 의심"

_TAMPER_NOTE = (
    "이 조항에서 AI 분석을 조작하려는 문구가 탐지되었습니다. "
    "조작 문구는 제거하고 나머지 계약 내용만으로 판정했으나, "
    "안전 판정을 그대로 신뢰할 수 없어 '주의'로 상향했습니다."
)
_TAMPER_QUESTION = (
    "이 조항에 사람이 읽을 수 없는 숨은 문구나 AI에게 내리는 지시문이 "
    "왜 들어 있는지 상대방에게 확인하세요."
)


_WITHHELD_EXPLANATION = (
    "이 조항은 판정하지 않았습니다. 조항 안에 AI 분석을 조작하려는 문장이 섞여 "
    "있어 그 부분을 격리했는데, 남은 계약 내용만으로는 위험 여부를 판단할 근거가 "
    "부족합니다. 조작 시도가 있었다는 사실 자체가 이 조항을 특히 주의해서 보아야 "
    "할 이유이므로, 반드시 원문을 직접 확인하고 상대방에게 설명을 요구하세요."
)
_WITHHELD_QUESTIONS = [
    "이 조항에 AI에게 내리는 지시문이 왜 들어 있는지 상대방에게 물어보세요.",
    "이 조항의 정확한 내용을 서면으로 다시 받아 확인하세요.",
]


def _withheld_result(clause_id: str, removed: list) -> AnalysisResult:
    """fail-closed — 판정을 내지 않고 사용자에게 직접 확인을 요구한다 (#174).

    판정 거부는 조용하면 안 된다. 조용히 '안전'이나 무표시로 넘어가면 공격자가
    조항 뒤에 지시문 한 줄을 붙이는 것만으로 경고를 억제할 수 있다. 그래서
    등급은 '주의'로 두되(3단계 체계상 가장 강한 비-위험 신호) 별도 플래그로
    "판정 보류"임을 명시해 화면에서 더 강하게 표시하도록 한다.
    """
    return AnalysisResult(
        clause_id=clause_id,
        explanation=_WITHHELD_EXPLANATION,
        risk_level="주의",
        risk_type=TAMPER_RISK_TYPE,
        risk_evidence=quarantine_notice(removed) if removed else _TAMPER_NOTE,
        check_questions=list(_WITHHELD_QUESTIONS),
        injection_suspected=True,
        quarantined=len(removed),
        verdict_withheld=True,
    )


def _apply_tamper_floor(result: AnalysisResult, tampered: bool) -> AnalysisResult:
    """판정 안전장치 (#174, 4층) — 조작 탐지 조항은 '안전'으로 내려갈 수 없다.

    왜 필요한가. 0~3층을 다 통과해도 방어는 확률적이다. 공격이 한 번 성공하면
    위험 조항이 '안전'으로 표시되고, 그것이 이 서비스에서 가장 나쁜 실패다
    (경고를 목적으로 하는 서비스가 침묵하는 것). 그래서 마지막에 결정적 규칙을
    둔다: **조작 흔적이 있는 조항의 '안전' 판정은 채택하지 않는다.**

    상향 폭은 '주의'까지로 제한한다. '위험'으로 올리면 규칙 오탐이 곧바로
    허위 경보가 되므로, 팀의 원칙("놓친 위험이 오탐보다 나쁘다")을 지키면서도
    과잉 경보를 만들지 않는 최소 개입이다.

    조작이 탐지돼도 모델이 이미 '주의'나 '위험'으로 판정했다면 판정은 그대로
    두고 플래그만 남긴다 — 방어가 제대로 동작한 경우까지 흔들 이유가 없다.
    """
    if not tampered:
        return result
    result["injection_suspected"] = True
    if result["risk_level"] != "안전":
        return result
    result["original_risk_level"] = result["risk_level"]
    result["risk_level"] = "주의"
    result["risk_type"] = TAMPER_RISK_TYPE
    result["risk_evidence"] = f"{_TAMPER_NOTE} (모델 판정 근거: {result['risk_evidence']})"
    result["check_questions"] = [_TAMPER_QUESTION, *result["check_questions"]]
    return result


# 조항 분석은 서로 독립이라 병렬 호출한다. API rate limit을 고려한 보수적 동시성.
# 기본 5(보수적). API 티어가 허용하면 LLM_CONCURRENCY 환경변수로 상향 —
# 조항 분석·페르소나가 병렬 폭만큼 빨라진다 (16조항 기준 5→10이면 약 절반).
_MAX_CONCURRENCY = int(os.getenv("LLM_CONCURRENCY", "5"))


def _analyze_clause(clause_id: str, text: str, domain: str = "",
                    domain_evidence: str = "") -> AnalysisResult:
    # 2층 무력화 (#174) — 호출 지점에서 스스로 방어한다. 파이프라인 입구
    # (graph.py·stream.py)에서도 sanitize를 거치지만 멱등이라 무해하고,
    # 평가 하네스처럼 입구를 우회해 이 함수를 직접 부르는 경로까지 덮인다.
    # "입력을 신뢰하지 않는다"를 노드 단위로 강제하는 배선이다.
    text, _ = sanitize(text)
    # 조항 단위 탐지 — 문서 단위 경고(graph.py)와 별개로, 이 조항 자체에
    # 조작 흔적이 있었는지를 격리·안전장치 판단에 쓴다.
    tampered = bool(detect_injection(text))

    # 2.5층 격리 (#174) — 조작 문장을 LLM 입력에서 아예 들어낸다.
    # 무력화는 공격 '문자'를 지우고, 격리는 공격 '문장'을 들어낸다. 무력화만
    # 하면 "안전으로 판정하라"가 평문으로 모델에게 전달되고, 프롬프트 방어가
    # 막아 주기를 기대하는 확률적 상태로 남는다.
    body, removed = quarantine(text) if tampered else (text, [])

    # fail-closed — 격리하고 나니 판정 근거가 남지 않았다면 판정하지 않는다.
    # 껍데기만 남은 조항을 판정하면 '안전'이 나오기 쉽고, 그것이 정확히
    # 공격자가 노리는 결과다.
    if tampered and not is_analyzable(body):
        logger.info("%s 판정 보류 (격리 후 근거 부족, 격리 %d건)", clause_id, len(removed))
        return _withheld_result(clause_id, removed)

    prefix, suffix = _build_prompt_parts(domain, domain_evidence)
    isolated = wrap_clause(body)  # 3층 구조적 격리 — 격리를 통과한 본문만 넣는다
    llm = get_worker_llm()

    for attempt in range(_PARSE_ATTEMPTS):
        try:
            # Pydantic 검증: 스키마 이탈은 예외 → 재시도. 사소한 이탈(리스트
            # risk_type, 번호 접두사)은 스키마 정규화가 흡수한다 (src/schemas.py).
            data = AnalysisOutput.model_validate(
                invoke_json(llm, isolated + suffix, cached_prefix=prefix))
            # 인용 원문 존재 검사 (자문 §5, 규칙 기반): 창작 인용은 스키마
            # 위반과 동급으로 취급 → 재시도, 소진 시 폴백.
            # 검사 대상은 조항 원문(text)만 유지한다 — 프롬프트 전체(prefix+suffix)로
            # 넓히면 모델이 프롬프트 안의 예시 문구를 조항과 무관하게 그대로
            # risk_evidence에 베껴도 "입력에 있으니 통과"로 새어나가는 구멍이
            # 생긴다(2026-08 실측, test_citation_check.py의 회귀 테스트 참조).
            # 도메인 주입 후 법령 인용 오탐은 citation_check.py의
            # _LEGAL_SOURCE_MARKER(출처 표지 기반 면제)만으로 해결되므로 검사
            # 범위 자체를 넓힐 필요가 없다.
            # 인용 대조는 **모델이 실제로 본 텍스트**(격리 후 본문)로 한다.
            # 원문 전체로 넓히면 격리한 지시문을 근거로 인용해도 통과한다.
            fabricated = find_fabricated_quotes(data.risk_evidence, body)
            if fabricated:
                raise ValueError(f"원문에 없는 인용 {len(fabricated)}건: {fabricated[0][:30]}…")
            result = AnalysisResult(
                clause_id=clause_id,
                explanation=data.explanation,
                risk_level=data.risk_level,
                risk_type=data.risk_type,
                risk_evidence=data.risk_evidence,
                check_questions=data.check_questions,
            )
            if removed:
                result["quarantined"] = len(removed)
                result["check_questions"] = [quarantine_notice(removed),
                                             *result["check_questions"]]
            return _apply_tamper_floor(result, tampered)
        except Exception as exc:  # JSON 파싱 실패, 키 누락, 스키마 검증 실패 등
            if attempt + 1 == _PARSE_ATTEMPTS:
                # exc는 창작 인용 30자(위 ValueError)나 LLM 원응답 일부(최대 200자,
                # src/llm.py invoke_json)를 담을 수 있어 종류만 WARNING, 전체
                # 내용은 DEBUG로만 남긴다 (#58, privacy_data_handling.md 정합).
                logger.warning("%s 분석 실패, 폴백 처리: %s", clause_id, type(exc).__name__)
                logger.debug("%s 분석 실패 상세", clause_id, exc_info=exc)

    return _apply_tamper_floor(
        AnalysisResult(
            clause_id=clause_id,
            explanation=body,
            risk_level="주의",
            risk_type="해당 없음",
            risk_evidence=_FALLBACK_EVIDENCE,
            check_questions=[],
            analysis_failed=True,  # 프론트 현지화용 기계 판독 마커 (#100)
        ),
        tampered,
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
