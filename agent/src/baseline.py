"""Baseline: 단일 LLM 호출로 4종 출력을 한 번에 생성하는 비교군.

착수보고서 <표 6> 성능 검증 시나리오의 Baseline("단일 LLM 호출, 사용자 적응
없이 4종 출력을 한 번에 요구")을 구현한다. Ours(4단계 파이프라인)와 공정하게
비교하기 위해:
- Parser는 Ours와 완전히 동일하게 사용해 조항 분리를 맞춘다.
- Analysis/Persona 각 단계 호출과 Judge 재생성 루프 없이, 전체 조항을 한 번의
  프롬프트로 묶어 4종 출력을 요구하는 단일 LLM 호출로 대체한다 (페르소나 적응 없음).
- 모델은 Ours의 Analysis와 동일한 MODEL_WORKER를 사용해 모델 차이가 아니라
  파이프라인 구조 차이만 비교되도록 한다.
- Judge는 Ours와 완전히 동일한 judge_node/judge_rubric.txt를 그대로 재사용해
  같은 기준으로 채점한다 (공정 비교의 핵심).
"""

from pathlib import Path
from typing import List

from src.llm import get_worker_llm, invoke_json
from src.nodes.judge import judge_node
from src.nodes.parser import parser_node
from src.state import AnalysisResult, Clause, PipelineState

PROMPT_PATH = Path(__file__).parent / "prompts" / "baseline.txt"
_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")

_PARSE_ATTEMPTS = 2  # 최초 시도 + 재시도 1회 (Judge 재생성 루프와는 무관한 파싱 재시도)
_FALLBACK_EVIDENCE = "분석 실패 (수동 확인 필요)"


def _fallback_result(clause_id: str) -> AnalysisResult:
    return AnalysisResult(
        clause_id=clause_id,
        explanation="",
        risk_level="주의",
        risk_type="해당 없음",
        risk_evidence=_FALLBACK_EVIDENCE,
        check_questions=[],
    )


def _call_baseline_llm(clauses: List[Clause]) -> List[AnalysisResult]:
    clause_list_text = "\n".join(f"[{c['clause_id']}] {c['text']}" for c in clauses)
    prompt = _PROMPT_TEMPLATE.replace("{clause_list}", clause_list_text)
    llm = get_worker_llm()

    for attempt in range(_PARSE_ATTEMPTS):
        try:
            data = invoke_json(llm, prompt)
            by_id = {item["clause_id"]: item for item in data["results"]}
            results = []
            for c in clauses:
                item = by_id.get(c["clause_id"])
                if item is None:
                    results.append(_fallback_result(c["clause_id"]))
                    continue
                results.append(
                    AnalysisResult(
                        clause_id=c["clause_id"],
                        explanation=item["explanation"],
                        risk_level=item["risk_level"],
                        risk_type=item["risk_type"],
                        risk_evidence=item["risk_evidence"],
                        check_questions=item["check_questions"],
                    )
                )
            return results
        except Exception as exc:  # JSON 파싱 실패, 키 누락 등
            if attempt + 1 == _PARSE_ATTEMPTS:
                print(f"[Baseline] 분석 실패, 전체 폴백 처리: {exc}")

    return [_fallback_result(c["clause_id"]) for c in clauses]


def run_baseline(raw_text: str, persona: str = "adult") -> PipelineState:
    """Baseline 1회 실행 헬퍼. run_pipeline과 동일한 형태의 상태를 반환한다."""
    parser_result = parser_node({"raw_text": raw_text})
    clauses = parser_result["clauses"]

    results = _call_baseline_llm(clauses)

    state: PipelineState = {
        "raw_text": raw_text,
        "persona": persona,  # type: ignore[typeddict-item]
        "clauses": clauses,
        "analysis_results": results,
        "adapted_results": results,  # 페르소나 적응 없음 - Analysis 결과를 그대로 사용
        "judge_scores": {  # type: ignore[typeddict-item]
            "clarity": 0.0,
            "faithfulness": 0.0,
            "risk_coverage": 0.0,
            "actionability": 0.0,
        },
        "retry_count": 0,  # 재생성 루프 없음
        "needs_review": False,
    }

    judge_update = judge_node(state)
    state["judge_scores"] = judge_update["judge_scores"]

    return state
