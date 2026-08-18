"""조항별 점진(스트리밍) 분석 — NDJSON 이벤트 생성기.

/analyze는 전체 파이프라인이 끝나야 응답하므로 21조항 기준 70~90초를 빈 화면으로
기다려야 한다. 이 모듈은 같은 단계(마스킹→Parser→Analysis→Persona→Judge 게이트)를
조항이 끝나는 대로 이벤트로 내보내는 실행기다.

이벤트 순서 (한 줄 = JSON 하나):
  {"event":"meta", "clause_count":N, "parse_warnings":[...], "clauses":[{clause_id,text}...]}
  {"event":"clause", "done":k, "total":N, "revision":r, "result":{...}}   # 완료 순서대로
  {"event":"judge", "judge_scores":{...}, "needs_review":b, "retry_count":r}
  {"event":"done"}

게이트 의미는 graph.py와 동일(FAITHFULNESS_MIN hard-fail, 평균 JUDGE_THRESHOLD,
MAX_RETRIES). 재시도가 발생하면 revision을 올려 clause 이벤트를 다시 내보내고,
프론트는 clause_id 기준으로 교체한다. **주의: 조항 이벤트는 Judge 검증 전
결과이므로 프론트는 '검증 중' 상태를 표시하고, judge 이벤트로 확정해야 한다.**

graph.py와 제어 흐름이 중복된다 — 임계값·단계를 바꿀 때 양쪽을 함께 수정할 것
(상수는 state.py에서 공유하므로 임계값 자체는 한 곳이다).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Iterator, List

from src.masking import mask_pii, masking_notice
from src.nodes.analysis import _MAX_CONCURRENCY, _analyze_clause
from src.nodes.domain import domain_node
from src.nodes.judge import judge_node
from src.nodes.parser import split_clauses_with_warnings
from src.nodes.persona import _adapt
from src.state import (
    FAITHFULNESS_MIN,
    JUDGE_THRESHOLD,
    MAX_RETRIES,
    AnalysisResult,
    Clause,
    judge_score_avg,
)


def _analyze_and_adapt(
    clause: Clause, persona: str, language: str, domain: str, domain_evidence: str
) -> tuple[AnalysisResult, dict | None]:
    result = _analyze_clause(clause["clause_id"], clause["text"], domain, domain_evidence)
    return _adapt(result, persona, language, clause["text"])


def _emit_clauses(
    clauses: List[Clause], persona: str, language: str, revision: int,
    domain: str = "", domain_evidence: str = "",
) -> Iterator[dict]:
    """전 조항을 병렬 분석+적응하고 완료 순서대로 clause 이벤트를 낸다.

    번역(원문·질문)은 이벤트 payload에만 싣는다 — judge 입력(adapted 결과)에는
    섞지 않는다 (persona._adapt docstring 참조).
    """
    done = 0
    clause_text = {c["clause_id"]: c["text"] for c in clauses}
    with ThreadPoolExecutor(max_workers=_MAX_CONCURRENCY) as pool:
        futures = [
            pool.submit(_analyze_and_adapt, c, persona, language, domain, domain_evidence)
            for c in clauses
        ]
        for future in as_completed(futures):
            result, translation = future.result()  # 양쪽 모두 내부 폴백 보유
            done += 1
            yield {
                "event": "clause",
                "done": done,
                "total": len(clauses),
                "revision": revision,
                "result": {
                    **result,
                    "original_text": clause_text[result["clause_id"]],
                    **(translation or {}),
                },
            }


def stream_analysis(
    raw_text: str, persona: str, language: str = "ko", domain: str = ""
) -> Iterator[dict]:
    masked, pii_counts = mask_pii(raw_text)
    clauses, warnings = split_clauses_with_warnings(masked)
    if pii_counts:
        warnings = [masking_notice(pii_counts)] + warnings

    # domain_node와 동일 로직(사용자 선택 우선, 자동판별은 opt-in) — graph.py와
    # 제어 흐름이 중복된다는 모듈 docstring 경고대로 여기도 함께 갱신해야 한다.
    domain_result = domain_node({"domain": domain, "raw_text": masked})  # type: ignore[arg-type]
    resolved_domain = domain_result["domain"]
    domain_evidence = domain_result["domain_evidence"]

    yield {
        "event": "meta",
        "clause_count": len(clauses),
        "parse_warnings": warnings,
        "domain": resolved_domain,
        "clauses": [{"clause_id": c["clause_id"], "text": c["text"]} for c in clauses],
    }

    results_by_id: Dict[str, AnalysisResult] = {}
    retry = 0
    needs_review = False
    numeric_scores: Dict[str, float] = {}

    while True:
        _EVENT_ONLY_KEYS = {"original_text", "original_text_translated", "check_questions_translated"}
        for event in _emit_clauses(clauses, persona, language, revision=retry,
                                   domain=resolved_domain, domain_evidence=domain_evidence):
            results_by_id[event["result"]["clause_id"]] = {
                k: v for k, v in event["result"].items() if k not in _EVENT_ONLY_KEYS
            }  # type: ignore[assignment]
            yield event

        ordered = [results_by_id[c["clause_id"]] for c in clauses]
        judge_state = {
            "raw_text": masked,
            "persona": persona,
            "clauses": clauses,
            "analysis_results": ordered,
            "adapted_results": ordered,
            "retry_count": retry,
            "needs_review": False,
        }
        scores = judge_node(judge_state)["judge_scores"]  # type: ignore[arg-type]
        numeric_scores = {k: v for k, v in scores.items() if isinstance(v, (int, float))}
        avg = judge_score_avg(scores)
        faith = scores["faithfulness"]

        gate_failed = faith < FAITHFULNESS_MIN or avg < JUDGE_THRESHOLD
        if gate_failed and retry < MAX_RETRIES:
            retry += 1
            yield {"event": "retry", "retry_count": retry,
                   "reason": "faithfulness" if faith < FAITHFULNESS_MIN else "avg"}
            continue
        needs_review = gate_failed
        break

    yield {
        "event": "judge",
        "judge_scores": numeric_scores,
        "needs_review": needs_review,
        "retry_count": retry,
    }
    yield {"event": "done"}
