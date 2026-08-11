"""Judge Agent: LLM-as-a-Judge 정량 평가.

4 Aspect x 5점 Rubric (착수보고서 <표 5>):
- Clarity        : 설명이 페르소나 난이도에 적합한가
- Faithfulness   : 원문에 없는 내용을 추가하지 않았는가 (환각)
- Risk Coverage  : 위험 조항을 누락 없이 식별했는가
- Actionability  : 실행 가능한 행동(질문)을 제시하는가

src/prompts/judge_rubric.txt로 MODEL_JUDGE를 호출해 채점한다.
점수 근거(rationale)는 사람-LLM 상관도 분석 참고용으로 콘솔에 로그로 남긴다.
"""

import json
import random
from pathlib import Path

from src.llm import get_judge_llm, invoke_json
from src.state import JudgeScores, PipelineState

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "judge_rubric.txt"
_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")

_ASPECTS = ["clarity", "faithfulness", "risk_coverage", "actionability"]

_ASPECT_RUBRIC = {
    "clarity": (
        "clarity (이해용이성): 설명이 지정된 페르소나({persona})의 난이도에 적합한가?\n"
        "   1점 예시: senior 페르소나 출력에 \"임차인의 계약갱신요구권 포기 약정은 "
        "주택임대차보호법 제6조의3 제1항의 강행규정성에 반하여 원칙적 무효이나 신뢰보호원칙에 "
        "따른 항변이 배척된다\"처럼 법률 문장을 그대로 노출 → 1점 (페르소나 눈높이 미고려)\n"
        "   3점 예시: 쉬운 말로 풀었으나 \"강행규정\", \"항변\" 같은 법률 용어가 설명 없이 "
        "섞여 있음 → 3점 (부분적으로만 적합)\n"
        "   5점 예시: \"집주인이 '앞으로 재계약 연장은 요구하지 않기로 한다'는 조건을 걸었더라도, "
        "법이 세입자에게 준 재계약 요구 권리이기 때문에 특별한 사정이 없다면 이 조건은 효력이 "
        "없습니다\"처럼 페르소나 눈높이에 맞게 완전히 풀어씀 → 5점"
    ),
    "faithfulness": (
        "faithfulness (충실성): 원문에 없는 내용을 추가하지 않았는가?\n"
        "   ※ 판정 기준 명확화: 조항 밖의 법령·판정례·일반 법률 지식을 근거로 인용하는 것"
        "(예: '민법 제640조 기준과 일치', '조정위 무효 판정 사례가 있음')은 위반이 아니라"
        " 오히려 근거 품질 요소입니다. 위반은 **원문에 없는 수치·금액·조건을 창작**하는"
        " 것입니다(예: 원문에 없는 '연 20%'를 지어냄).\n"
        "   1점 예시: 원문 조항(hldcc id=37)이 \"판결 시 정하는 법정이자\"라고만 되어 있는데 "
        "출력이 \"연 20%의 고금리가 적용됩니다\"처럼 원문에 없는 구체적 이율을 창작 → 1점 (환각)\n"
        "   3점 예시: 원문 수치(예: 위약금 비율 \"○○%\")를 그대로 인용하지 않고 \"적당한 수준의 "
        "위약금\"처럼 뭉뚱그려 표현 → 3점 (원문 정보 손실, 창작은 아님)\n"
        "   5점 예시: 원문의 조항 번호·금액·기간을 그대로 인용하며 해설만 추가 → 5점"
    ),
    "risk_coverage": (
        "risk_coverage (위험 식별): 위험 조항을 누락 없이 식별했는가?\n"
        "   1점 예시: 원문에 \"이 사건 주택에 관한 모든 수리비용은 임차인의 책임으로 한다\" "
        "(hldcc id=20, 정부 조정위가 무효로 확정판정)가 있는데 [최종 출력]에 이 조항에 대한 "
        "언급 자체가 없음 → 1점 (핵심 위험 완전 누락)\n"
        "   3점 예시: 위 조항을 다뤘고 \"주의가 필요하다\"고는 했으나 risk_type을 "
        "\"불명확한 수수료·이자 조건\"으로 잘못 분류(정확히는 \"책임 면제\") → 3점 "
        "(탐지는 했으나 위험 유형 오분류)\n"
        "   5점 예시: risk_type=\"책임 면제\"로 정확히 분류하고, check_questions에 "
        "\"모든 수리비용을 임차인이 부담한다는 조항은 임차인에게 일방적으로 불리해 무효로 "
        "판단될 수 있어요. 임대인과 이 부분을 다시 협의해보셨나요?\"까지 생성 → 5점\n"
        "   신탁관계 예시: 조항에 \"당사는 신탁계약의 수탁자로서... 임대보증금 반환책임에 "
        "대하여 일체의 책임이 없으며\"(LBox id=2488, 실제 신탁부동산 임대차 사기 패턴)처럼 "
        "신탁·수탁자·위탁자 표현이 등장하면 risk_type=\"신탁관계·소유권 불안정 고지\"로 "
        "분류해야 함 — 이걸 놓치고 \"책임 면제\"로만 분류하거나 위험 자체를 놓치면 감점\n"
        "   일관성 체크: [최종 출력]에서 risk_level=\"주의\"인데 risk_type=\"해당 없음\"으로 "
        "되어 있으면 이는 그 자체로 논리적 결함이다 — risk_coverage 점수를 낮게 주고 "
        "rationale에 이 모순을 반드시 지적할 것"
    ),
    "actionability": (
        "actionability (행동 지침): 사용자가 실행 가능한 행동을 제시하는가?\n"
        "   1점 예시: \"이 조항은 위험할 수 있으니 주의하세요\"로 끝나고 무엇을 확인/요청해야 "
        "하는지 없음 → 1점 (모호함)\n"
        "   3점 예시: \"전문가와 상담해보세요\"처럼 일반적 권고만 있고 이 조항에 특정된 질문이 "
        "없음 → 3점\n"
        "   5점 예시: AI Hub 상가임대차 서식처럼 위약금 비율이 \"○○%\"로 공란인 조항에 대해 "
        "\"계약서에 위약금 비율 숫자가 비어 있어요. 서명 전에 임대인에게 구체적인 숫자를 "
        "채워달라고 요청하고, 그 비율이 보증금의 몇 %인지 직접 확인하세요\"처럼 이 조항에 "
        "특정된 구체적 행동을 제시 → 5점"
    ),
}


def _judge(state: PipelineState) -> JudgeScores:
    original_clauses = "\n".join(
        f"[{c['clause_id']}] {c['text']}" for c in state["clauses"]
    )
    final_output = json.dumps(state["adapted_results"], ensure_ascii=False, indent=2)

    # aspect 나열 순서를 매 호출마다 무작위화 (position bias 대응,
    # docs/human_llm_judge_agreement_design.md 10.2절 (3))
    shuffled_aspects = _ASPECTS.copy()
    random.shuffle(shuffled_aspects)
    rubric_block = "\n".join(
        f"{i}. {_ASPECT_RUBRIC[aspect]}" for i, aspect in enumerate(shuffled_aspects, start=1)
    )

    prompt = (
        _PROMPT_TEMPLATE.replace("{rubric_block}", rubric_block)
        .replace("{persona}", state["persona"])
        .replace("{original_clauses}", original_clauses)
        .replace("{final_output}", final_output)
    )

    data = invoke_json(get_judge_llm(), prompt)

    scores = {}
    rationale = {}
    for aspect in _ASPECTS:
        aspect_data = data[aspect]
        scores[aspect] = float(aspect_data["score"])
        rationale[aspect] = aspect_data["rationale"]
        print(f"[Judge] {aspect}: {aspect_data['score']}점 — {aspect_data['rationale']}")

    return JudgeScores(
        clarity=scores["clarity"],
        faithfulness=scores["faithfulness"],
        risk_coverage=scores["risk_coverage"],
        actionability=scores["actionability"],
        rationale=rationale,
    )


def judge_node(state: PipelineState) -> dict:
    """LangGraph 노드: adapted_results -> judge_scores."""
    scores = _judge(state)
    return {"judge_scores": scores}
