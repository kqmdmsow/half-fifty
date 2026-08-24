"""설명문 난이도 지표 (규칙 기반, LLM 불요) — 페르소나 효과 측정용 (#174).

## 왜 필요한가

"고령층 모드는 쉬운 말로 설명한다"는 주장은 지금까지 검증된 적이 없다.
사람 대상 사용성 조사가 정석이지만 표본을 모으는 데 시간이 걸리고, 그
전까지 주장을 근거 없이 쓸 수는 없다. 그래서 사람 없이 잴 수 있는 부분을
먼저 자동 지표로 고정한다.

**이 지표가 이해도를 재는 것은 아니다.** 문장이 짧고 전문용어가 적으면
읽기 쉬울 개연성이 높다는 것뿐이고, 실제로 이해했는지는 사람에게 물어야
안다. 대외 문서에 쓸 때 이 한계를 함께 적을 것.

## 무엇을 재는가

- 평균 문장 길이(글자): 긴 문장은 작업기억 부담이 크다.
- 문장당 어절 수: 길이와 별개로 절이 많이 붙는지 본다.
- 전문용어 비율: 계약·법률 용어가 얼마나 남아 있는가.
- 읽기 시간 추정: 한국어 묵독 속도를 분당 500자로 잡은 대략치.
"""

import re
from typing import Dict, List

# 계약·금융 문서에 흔한 전문용어. 고령층·외국인 설명에서는 이런 말이 줄고
# 일상어로 풀어써야 한다. 목록은 위험 유형 정의와 표준약관에서 뽑았고,
# 완전하지 않다 — 상대 비교용이지 절대 난이도 척도가 아니다.
_JARGON = frozenset({
    "기한의 이익", "기한이익", "상실", "면책", "면책사유", "귀책사유", "구상권",
    "채무불이행", "이행지체", "지체상금", "손해배상", "손해배상액의 예정",
    "위약벌", "약정", "특약", "해지", "해제", "철회", "취소", "무효", "취소권",
    "항변권", "상계", "충당", "변제", "담보", "근저당", "질권", "유치권",
    "수탁자", "위탁자", "수익자", "신탁", "명도", "원상회복", "임차권",
    "대항력", "우선변제권", "확정일자", "전대", "전대차", "차임", "보증금",
    "청약", "승낙", "약관", "고지의무", "통지의무", "선관주의", "선량한 관리자",
    "부당이득", "이의제기", "관할", "전속관할", "제소전 화해", "중재",
    "연체이율", "중도상환수수료", "기산일", "산정", "공제", "정산", "잔여기간",
    "일할계산", "갈음", "준용", "불가항력", "일방적", "포괄", "의제",
})

# 문장 경계: 한국어 종결부호. "1.5%" 같은 소수점은 뒤에 숫자가 오므로 제외.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。！？])(?=\s|$)")
# 한국어 묵독 속도 대략치(분당 글자). 정확한 값이 아니라 상대 비교용.
_CHARS_PER_MINUTE = 500


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def jargon_hits(text: str) -> List[str]:
    """본문에 남아 있는 전문용어 목록 (중복 제거, 등장 순)."""
    seen, hits = set(), []
    for term in _JARGON:
        if term in text and term not in seen:
            seen.add(term)
            hits.append(term)
    return sorted(hits, key=text.index)


def measure(text: str) -> Dict[str, float]:
    """설명문 하나의 난이도 지표."""
    text = text.strip()
    if not text:
        return {"chars": 0, "sentences": 0, "avg_sentence_chars": 0.0,
                "avg_words_per_sentence": 0.0, "jargon_count": 0,
                "jargon_per_100_chars": 0.0, "read_seconds": 0.0}
    sents = _sentences(text) or [text]
    words = text.split()
    hits = jargon_hits(text)
    return {
        "chars": len(text),
        "sentences": len(sents),
        "avg_sentence_chars": len(text) / len(sents),
        "avg_words_per_sentence": len(words) / len(sents),
        "jargon_count": len(hits),
        "jargon_per_100_chars": len(hits) / len(text) * 100,
        "read_seconds": len(text) / _CHARS_PER_MINUTE * 60,
    }


def aggregate(texts: List[str]) -> Dict[str, float]:
    """여러 설명문의 평균 지표. 빈 목록이면 0으로 채운다."""
    rows = [measure(t) for t in texts if t and t.strip()]
    if not rows:
        return measure("")
    keys = rows[0].keys()
    return {k: sum(r[k] for r in rows) / len(rows) for k in keys}
