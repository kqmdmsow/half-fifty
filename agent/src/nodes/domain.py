"""Domain Detection: 문서 수준 계약 유형 판별 (조항 판정 전 1회).

왜 필요한가 (docs/risk_taxonomy_v2.md §C): 같은 문언이라도 문서 유형에 따라
판정이 갈린다 — "2기 연체 시 해지"는 주택 임대차면 민법 §640 표준(안전),
상가면 상가임대차보호법의 3기 보호를 축소(위험). 조항 단독으로는 원리적으로
구분 불가능하므로, 문서 전체에서 유형을 한 번 판별해 모든 조항 판정에 주입한다.
(평가 데이터의 도메인 프리픽스 수기 부착을 제품 기능으로 흡수한 것.)

실패 시 "알 수 없음"으로 폴백 — Analysis는 기존처럼 조항 문언만으로 판단하므로
이 노드의 실패가 파이프라인을 깨지 않는다 (감지 실패 = v2.1 기존 동작).

유형 값의 출처 (팀 회의 안건 D 반영):
1) 사용자 선택 (기본) — 업로드 시 사용자가 고른 유형이 state["domain"]으로
   들어오면 그대로 사용. LLM 호출 없음. "자동분류는 검증 대상이 하나 더
   늘어난다"는 팀 정리에 따라 이것이 기본 경로다.
2) LLM 자동 판별 (opt-in) — DOMAIN_DETECTION=llm 환경변수를 켠 경우에만,
   사용자 선택이 없을 때 보조로 동작. 기본값은 꺼짐.
사용자 선택도 없고 자동 판별도 꺼져 있으면 "알 수 없음" → 기존 동작.
"""

import os

from pathlib import Path

from src.llm import get_worker_llm, invoke_json
from src.state import PipelineState

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "domain.txt"
_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")

DOMAIN_UNKNOWN = "알 수 없음"

# domain.txt [허용 유형]과 동일하게 유지할 것
ALLOWED_DOMAINS = frozenset({
    "주택임대차", "상가임대차", "임대차(구분불명)", "보험", "대출·여신",
    "신용카드", "예금·수신", "투자·신탁", "가맹(프랜차이즈)", "상조·멤버십",
    "매매·분양", "근로계약", "기타",
})

# 문서 앞부분에 제목·당사자·목적 조항이 몰려 있어 판별 지표 밀도가 가장 높다.
# 뒷부분 특약에도 지표(권리금·전입신고 등)가 있을 수 있어 꼬리도 일부 포함.
_HEAD_CHARS = 1800
_TAIL_CHARS = 600


def _detect_domain(raw_text: str) -> tuple[str, str]:
    """(domain, evidence) 반환. 어떤 실패든 (알 수 없음, 사유)로 폴백."""
    text = raw_text.strip()
    if len(text) > _HEAD_CHARS + _TAIL_CHARS:
        excerpt = text[:_HEAD_CHARS] + "\n(중략)\n" + text[-_TAIL_CHARS:]
    else:
        excerpt = text
    prompt = _PROMPT_TEMPLATE.replace("{document_excerpt}", excerpt)
    try:
        data = invoke_json(get_worker_llm(), prompt)
        domain = str(data.get("domain", "")).strip()
        if domain not in ALLOWED_DOMAINS:
            return DOMAIN_UNKNOWN, f"허용 외 응답: {domain[:40]}"
        return domain, str(data.get("evidence", ""))[:200]
    except Exception as exc:
        print(f"[Domain] 판별 실패, '{DOMAIN_UNKNOWN}' 폴백: {exc}")
        return DOMAIN_UNKNOWN, str(exc)[:80]


def domain_node(state: PipelineState) -> dict:
    """LangGraph 노드: (사용자 선택 도메인 | 자동 판별 | 알 수 없음) -> domain."""
    user_domain = state.get("domain", "")
    if user_domain and user_domain in ALLOWED_DOMAINS:
        print(f"[Domain] 사용자 선택 유형 사용: {user_domain}")
        return {"domain": user_domain, "domain_evidence": "사용자 선택"}

    if os.getenv("DOMAIN_DETECTION", "").lower() != "llm":
        return {"domain": DOMAIN_UNKNOWN, "domain_evidence": "사용자 선택 없음 (자동 판별 비활성)"}

    domain, evidence = _detect_domain(state["raw_text"])
    print(f"[Domain] 자동 판별 유형: {domain}" + (f" (근거: {evidence[:60]})" if domain != DOMAIN_UNKNOWN else ""))
    return {"domain": domain, "domain_evidence": evidence}
