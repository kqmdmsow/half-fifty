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
(상수는 state.py에서 공유하므로 임계값 자체는 한 곳이다). aspect별 재생성
분기(#75)도 graph.py의 _route_retry_target과 동일 로직을 state.py의
failing_aspects/shortcut_eligible로 공유해 드리프트를 막는다. Judge rationale을
재생성 프롬프트에 주입하는 부분은 측정 결과(FP 증가) 제외했다 — 별도 이슈.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Iterator, List, Sequence

from src.case_footnotes import get_related_cases
from src.injection_check import detect_injection, injection_warning, sanitize, sanitize_notice
from src.masking import mask_pii, masking_notice
from src.nodes.analysis import _MAX_CONCURRENCY, _analyze_clause
from src.nodes.domain import domain_node
from src.nodes.judge import judge_node
from src.nodes.parser import split_clauses_with_warnings
from src.warning_codes import classify_all
from src.nodes.persona import _adapt
from src.state import (
    FAITHFULNESS_MIN,
    JUDGE_THRESHOLD,
    MAX_RETRIES,
    AnalysisResult,
    Clause,
    failing_aspects,
    judge_score_avg,
    shortcut_eligible,
)


def _analyze_and_adapt(
    clause: Clause, persona: str, language: str, domain: str, domain_evidence: str,
) -> tuple[AnalysisResult, dict | None]:
    result = _analyze_clause(clause["clause_id"], clause["text"], domain, domain_evidence)
    return _adapt(result, persona, language, clause["text"])


def _persona_only_adapt(
    clause: Clause, prior_result: AnalysisResult, persona: str, language: str,
) -> tuple[AnalysisResult, dict | None]:
    return _adapt(prior_result, persona, language, clause["text"])


def _emit_clauses(
    clauses: List[Clause], persona: str, language: str, revision: int,
    domain: str = "", domain_evidence: str = "",
) -> Iterator[dict]:
    """전 조항을 병렬 분석+적응하고 완료 순서대로 clause 이벤트를 낸다.

    번역(원문·질문)·related_cases(실제 사건 각주, #91)는 이벤트 payload에만
    싣는다 — judge 입력(adapted 결과)에는 섞지 않는다 (persona._adapt
    docstring, src/case_footnotes.py 격리 원칙 참조).
    """
    done = 0
    clause_text = {c["clause_id"]: c["text"] for c in clauses}
    clause_section = {c["clause_id"]: c.get("section", "본문") for c in clauses}
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
                    "section": clause_section.get(result["clause_id"], "본문"),
                    **(translation or {}),
                    "related_cases": get_related_cases(result["risk_type"]),
                },
            }


def _emit_persona_only(
    clauses: List[Clause], persona: str, language: str, revision: int,
    prior_results: Dict[str, AnalysisResult],
) -> Iterator[dict]:
    """clarity-only 단축(#75): analysis는 건너뛰고 직전 판정으로 persona만 재실행.

    risk_level/risk_type/risk_evidence/check_questions은 prior_results 그대로
    유지된다(persona._adapt는 explanation만 덮어씀). 피드백 미주입 상태라
    temperature=0에서는 explanation이 그대로 나올 수 있으나, risk_coverage·
    faithfulness를 재검증 없이 통과시키지 않는 안전장치(shortcut_eligible)
    자체가 이 PR의 목적이다 — 개선 효과(피드백 주입)는 별도 이슈에서 다룬다.
    """
    done = 0
    clause_text = {c["clause_id"]: c["text"] for c in clauses}
    clause_section = {c["clause_id"]: c.get("section", "본문") for c in clauses}
    with ThreadPoolExecutor(max_workers=_MAX_CONCURRENCY) as pool:
        futures = [
            pool.submit(_persona_only_adapt, c, prior_results[c["clause_id"]], persona, language)
            for c in clauses
        ]
        for future in as_completed(futures):
            result, translation = future.result()
            done += 1
            yield {
                "event": "clause",
                "done": done,
                "total": len(clauses),
                "revision": revision,
                "result": {
                    **result,
                    "original_text": clause_text[result["clause_id"]],
                    "section": clause_section.get(result["clause_id"], "본문"),
                    **(translation or {}),
                    "related_cases": get_related_cases(result["risk_type"]),
                },
            }


def stream_analysis(
    raw_text: str, persona: str, language: str = "ko", domain: str = "",
    extra_warnings: Sequence[str] = (),
) -> Iterator[dict]:
    masked, pii_counts = mask_pii(raw_text)
    # 인젝션 1층 탐지 + 2층 무력화 (#67·#174). 순서가 중요하다:
    # ① 탐지는 무력화 이전 원문으로 — 지우고 나면 알릴 근거가 사라진다.
    # ② 무력화는 조항 분할 **이전**에 — 분할 후에 하면 조항 경계를 조작하는
    #    구획 표지 위장이 이미 파서를 통과한 뒤가 된다.
    injections = detect_injection(masked)
    masked, report = sanitize(masked)
    clauses, warnings = split_clauses_with_warnings(masked)
    if pii_counts:
        warnings = [masking_notice(pii_counts)] + warnings
    # PDF 은닉 텍스트 격리 등 파이프라인 진입 전 경고 (#174)
    warnings = list(extra_warnings) + warnings
    if report.changed:
        warnings = [sanitize_notice(report)] + warnings
    # 조작 문구 탐지 시 경고를 최상단에 — 분석은 계속하되 사용자가 판정을
    # 의심하고 원문을 대조하게 만든다
    if injections:
        warnings = [injection_warning(injections)] + warnings

    # domain_node와 동일 로직(사용자 선택 우선, 자동판별은 opt-in) — graph.py와
    # 제어 흐름이 중복된다는 모듈 docstring 경고대로 여기도 함께 갱신해야 한다.
    domain_result = domain_node({"domain": domain, "raw_text": masked})  # type: ignore[arg-type]
    resolved_domain = domain_result["domain"]
    domain_evidence = domain_result["domain_evidence"]

    yield {
        "event": "meta",
        "clause_count": len(clauses),
        "parse_warnings": warnings,
        "parse_warning_codes": classify_all(warnings),
        "domain": resolved_domain,
        "clauses": [{"clause_id": c["clause_id"], "text": c["text"]} for c in clauses],
    }

    results_by_id: Dict[str, AnalysisResult] = {}
    retry = 0
    needs_review = False
    numeric_scores: Dict[str, float] = {}
    persona_only = False  # clarity-only 단축 여부 (#75)

    while True:
        # related_cases(#91)는 표시 전용 — 빠지면 judge_state["adapted_results"]로
        # 새어 들어가 Judge가 채점 근거로 잘못 읽을 위험이 있다(격리 원칙).
        _EVENT_ONLY_KEYS = {
            "original_text", "original_text_translated",
            "check_questions_translated", "risk_evidence_translated",
            "related_cases",
            # 하이라이트 좌표·문서 구획 라벨(#174) — 화면 표시 전용. judge가
            # 채점 근거로 잘못 읽지 않도록 related_cases와 동일하게 제외한다
            # (#179가 빠뜨렸던 부분, #190 배포 점검 중 발견).
            "evidence_spans", "section",
        }
        if persona_only:
            events = _emit_persona_only(clauses, persona, language, revision=retry,
                                        prior_results=results_by_id)
        else:
            events = _emit_clauses(clauses, persona, language, revision=retry,
                                   domain=resolved_domain, domain_evidence=domain_evidence)
        for event in events:
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
            # 재생성 대상 분기 (#75/#35): clarity만 미달 & risk_coverage·
            # faithfulness가 임계값보다 확실히 위일 때만 persona 단축 허용.
            # 아슬아슬하면 analysis 전체 재실행 (#35 실측: 마진 없이 단축을
            # 허용했더니 FP 3→7로 증가).
            failing = set(failing_aspects(scores))
            persona_only = failing == {"clarity"} and shortcut_eligible(scores)
            yield {"event": "retry", "retry_count": retry,
                   "reason": "faithfulness" if faith < FAITHFULNESS_MIN else "avg",
                   "target": "persona" if persona_only else "analysis"}
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
