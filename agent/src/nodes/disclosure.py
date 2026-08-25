"""설명·서명 대조 검증 (#175, 2순위).

계약서 조항 판정 결과 + 상담 발화를 대조해 "무엇을 설명했고 무엇에 서명했는가"의
간극을 찾는다.

## 왜 이 기능이 따로 필요한가

1순위 방화벽은 **문서**를 지킨다. 그런데 불완전판매는 문서가 아니라 **판매 현장**에서
일어난다. 계약서에는 있는데 말로는 안 해 준 수수료, 계약서와 다르게 설명한 조건,
아예 언급하지 않은 위험. 금소법 설명의무 위반 과징금(관련 수입 최대 50%)과
위법계약해지권이 걸리는 지점이고, 불완전판매 민원의 30% 이상이 60세 이상이다.

## 품질 장치 — 1순위와 같은 규율을 적용한다

- **인용 이중 검증.** 지적마다 계약서 인용과 발화 인용을 요구하고, 둘 다 원문에
  실재하는지 코드로 대조한다. 지어낸 인용이 하나라도 있으면 그 지적을 폐기한다.
  허위 지적은 사용자가 상대방과 다투게 만들어 **실제 피해**를 준다. 못 찾는 것보다
  나쁘다.
- **발화도 적대적 입력으로 취급한다.** 상담 녹취·스크립트는 판매자 측이 제출할 수
  있는 자료다. 계약서와 똑같이 무력화·격리·난수 구분자를 적용한다.
- **위치를 함께 낸다.** 지적이 계약서·발화의 어느 대목인지 좌표로 돌려줘서
  사용자가 직접 대조할 수 있게 한다.
"""

import json
import logging
import os
import secrets
from pathlib import Path
from typing import List, Optional, TypedDict

from src.citation_check import locate_quotes
from src.injection_check import detect_injection, quarantine, sanitize
from src.llm import get_worker_llm, invoke_json
from src.schemas import DisclosureOutput
from src.state import AnalysisResult

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "disclosure.txt"
_PROMPT_PREFIX, _PROMPT_SUFFIX = PROMPT_PATH.read_text(encoding="utf-8").split("{payload}")

_PARSE_ATTEMPTS = 2
# 발화가 이보다 짧으면 상담으로 보기 어렵다. 빈 녹취에 "설명 누락 투성이"를
# 내면 사용자를 오도한다.
_MIN_TRANSCRIPT_CHARS = 100
# 대조는 위험·주의 조항 중심으로 한다. 안전 조항까지 넣으면 프롬프트가 길어져
# 정작 중요한 조항의 비중이 낮아진다. 비용 조항은 안전이어도 포함한다.
_COST_HINTS = ("수수료", "이자", "위약금", "해지", "비용", "요율", "연체", "환불")


class DisclosureFindingOut(TypedDict):
    finding_type: str
    clause_id: Optional[str]
    clause_quote: Optional[str]
    speech_quote: Optional[str]
    explanation: str
    severity: str
    clause_spans: list
    speech_spans: list


class TranscriptTooShortError(ValueError):
    """대조할 발화가 사실상 없는 상태.

    조용히 "지적 없음"을 내면 "설명의무를 다했다"로 읽힌다. 정반대 결론이다.
    """


def _relevant(result: AnalysisResult, clause_text: str) -> bool:
    if result.get("risk_level") in ("위험", "주의"):
        return True
    return any(h in clause_text for h in _COST_HINTS)


def _build_payload(pairs, transcript: str, nonce: str) -> str:
    # .get을 쓴다 — 판정 결과가 폴백 경로로 오면 일부 필드가 비어 있을 수 있고,
    # 대조 검증이 그것 때문에 통째로 죽으면 안 된다.
    clauses = [{"clause_id": r.get("clause_id", ""),
                "risk_level": r.get("risk_level", "주의"),
                "risk_type": r.get("risk_type", "해당 없음"),
                "text": text} for text, r in pairs]
    body = json.dumps({"계약서 조항": clauses, "상담 발화": transcript},
                      ensure_ascii=False, indent=1)
    return f"<<<DATA:{nonce}>>>\n{body}\n<<<END:{nonce}>>>"


def _grounded(finding, clause_by_id, transcript) -> Optional[DisclosureFindingOut]:
    """인용이 원문에 실재하는 지적만 통과시킨다. 위치도 함께 계산한다."""
    clause_spans: list = []
    if finding.clause_quote:
        source = clause_by_id.get(finding.clause_id or "", "")
        clause_spans = locate_quotes(f"「{finding.clause_quote}」", source)
        if not clause_spans:
            logger.info("계약서 인용 미검증 — 지적 폐기: %.40s", finding.clause_quote)
            return None

    speech_spans: list = []
    if finding.speech_quote:
        speech_spans = locate_quotes(f"「{finding.speech_quote}」", transcript)
        if not speech_spans:
            logger.info("발화 인용 미검증 — 지적 폐기: %.40s", finding.speech_quote)
            return None

    # 미고지 유형은 "발화에 없음"이 핵심이므로 speech_quote가 있으면 모순이다.
    if finding.finding_type.startswith("미고지") and finding.speech_quote:
        logger.info("미고지인데 발화 인용이 붙음 — 지적 폐기: %s", finding.finding_type)
        return None

    return DisclosureFindingOut(
        finding_type=finding.finding_type,
        clause_id=finding.clause_id,
        clause_quote=finding.clause_quote,
        speech_quote=finding.speech_quote,
        explanation=finding.explanation,
        severity=finding.severity,
        clause_spans=clause_spans,
        speech_spans=speech_spans,
    )


def verify_disclosure(
    clauses: List[dict], results: List[AnalysisResult], transcript: str,
) -> dict:
    """계약서 조항 판정 + 상담 발화 -> 설명의무 간극 목록.

    반환: {"findings": [...], "transcript": 정제된 발화, "warnings": [...],
           "checked_clauses": 대조한 조항 수}
    """
    transcript, _ = sanitize(transcript)
    warnings: List[str] = []
    if detect_injection(transcript):
        body, removed = quarantine(transcript)
        if removed:
            warnings.append(
                f"🚫 상담 발화에서 AI에게 내리는 지시로 보이는 문장 {len(removed)}건을 "
                f"검증에서 격리했습니다. 녹취 자료가 조작됐을 수 있으니 원본을 확인하세요.")
            transcript = body

    if len(transcript.strip()) < _MIN_TRANSCRIPT_CHARS:
        raise TranscriptTooShortError(
            "대조할 상담 내용이 충분하지 않습니다. 녹취가 제대로 전사됐는지 "
            "확인해 주세요. 이 상태로는 '설명의무를 다했다'고 판단할 수 없습니다.")

    text_by_id = {c["clause_id"]: c["text"] for c in clauses}
    pairs = [(text_by_id.get(r.get("clause_id", ""), ""), r) for r in results]
    pairs = [(t, r) for t, r in pairs if t and _relevant(r, t)]
    if not pairs:
        return {"findings": [], "transcript": transcript, "warnings": warnings,
                "checked_clauses": 0}

    nonce = secrets.token_hex(8)
    payload = _build_payload(pairs, transcript, nonce)
    llm = get_worker_llm()

    for attempt in range(_PARSE_ATTEMPTS):
        try:
            data = DisclosureOutput.model_validate(
                invoke_json(llm, payload + _PROMPT_SUFFIX, cached_prefix=_PROMPT_PREFIX))
            grounded = [g for g in (_grounded(f, text_by_id, transcript)
                                    for f in data.findings) if g]
            dropped = len(data.findings) - len(grounded)
            if dropped:
                logger.info("인용 미검증으로 지적 %d건 폐기", dropped)
                warnings.append(
                    f"근거 인용이 원문과 맞지 않아 지적 {dropped}건을 제외했습니다. "
                    f"확인되지 않은 지적으로 상대방과 다투게 만들지 않기 위해서입니다.")
            return {"findings": grounded, "transcript": transcript,
                    "warnings": warnings, "checked_clauses": len(pairs)}
        except Exception as exc:
            if attempt + 1 == _PARSE_ATTEMPTS:
                logger.warning("설명 대조 실패: %s", type(exc).__name__)
                logger.debug("설명 대조 실패 상세", exc_info=exc)

    warnings.append(
        "설명 대조 분석에 실패했습니다. 지적이 없다는 뜻이 아니라 검증을 "
        "수행하지 못했다는 뜻입니다. 다시 시도해 주세요.")
    return {"findings": [], "transcript": transcript, "warnings": warnings,
            "checked_clauses": len(pairs), "failed": True}
