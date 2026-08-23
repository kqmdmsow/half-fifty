"""PDF 텍스트 추출 + 은닉 텍스트 탐지·격리 (#174).

추출한 텍스트는 Parser(src/nodes/parser.py)에 넘긴다. Parser는 이미 별지·
서명란·조 참조 노이즈를 걸러내도록 튜닝돼 있으므로 여기서는 텍스트 추출과
**은닉 공격 격리**를 담당한다.

## 왜 PDF 층에 방어가 필요한가

텍스트 인젝션은 사용자가 붙여넣은 글자를 대상으로 한다. 그런데 실제 금융
계약서는 상대방이 **PDF로** 건넨다. PDF에서는 사람 눈에 전혀 보이지 않는
텍스트를 넣을 수 있다:

- **백색 글자**: 흰 배경에 흰 글씨. 인쇄물에도 화면에도 안 보이지만
  텍스트 레이어에는 그대로 들어가고 LLM은 읽는다.
- **극소 폰트**: 0.4pt 글자. 점 하나로 보이거나 아예 안 보인다.
- **화면 밖 좌표**: MediaBox 밖에 배치. 뷰어는 안 그리지만 추출은 된다.

즉 **사람이 서명한 문서와 AI가 읽은 문서가 다를 수 있다.** 이 서비스는
"사람이 서명하려는 그 문서"를 판정해야 하므로, 사람이 볼 수 없는 텍스트는
계약 내용이 아니라고 본다.

## 원칙: 보이지 않는 텍스트는 판정에 넣지 않는다

공격이든 아니든 은닉 텍스트는 분석에서 제외한다. 공격일 때만 빼면 "공격
판정이 틀리면 그대로 통과"하는 구멍이 남고, 무엇보다 **사람이 못 본 문구가
판정을 바꾸면 그 판정은 사용자에게 거짓말**이 된다. 대신 무엇을 뺐는지는
전부 사용자에게 보고한다.
"""

import io
from typing import List, Tuple, TypedDict

import pdfplumber

_EMPTY_PDF_ERROR = "텍스트를 추출할 수 없는 PDF입니다 (스캔본일 수 있음)"

# 본문에 쓰일 수 없는 크기. 계약서 최소 활자가 6pt 안팎이라 3pt면 충분히 낮다.
_MIN_VISIBLE_FONT_PT = 3.0
# 배경(흰색)과 사실상 구별되지 않는 밝기.
_NEAR_WHITE = 0.9


class HiddenTextFinding(TypedDict):
    reason: str   # white_text | tiny_font | offscreen
    page: int
    text: str


_REASON_LABEL = {
    "white_text": "배경과 같은 색(흰색) 글자",
    "tiny_font": "육안으로 읽을 수 없는 극소 활자",
    "offscreen": "페이지 밖에 배치돼 화면에 그려지지 않는 글자",
}


def _is_near_white(color) -> bool:
    """채움색이 흰 배경과 구별되지 않는가. gray·RGB·CMYK를 모두 다룬다."""
    if color is None:
        return False
    if isinstance(color, (int, float)):
        return color >= _NEAR_WHITE
    try:
        vals = [float(v) for v in color]
    except (TypeError, ValueError):
        return False
    if len(vals) == 4:                      # CMYK — 전 성분이 0에 가까우면 흰색
        return all(v <= 1 - _NEAR_WHITE for v in vals)
    if len(vals) in (1, 3):                 # gray 또는 RGB
        return all(v >= _NEAR_WHITE for v in vals)
    return False


def _backdrops(page) -> List[tuple]:
    """흰 글자를 보이게 만드는 어두운 배경들의 bbox 목록.

    정부 표준계약서에는 색 박스 위의 흰 제목이 흔하다(주택임대차표준계약서
    4페이지 "법의 보호를 받기 위한 중요사항!"은 보라색 띠 위 흰 글씨다).
    배경을 보지 않고 "흰색이면 은닉"으로 판단하면 **정부 표준 양식의 본문을
    삭제**하게 된다 — 실제로 실측에서 그 사고가 났고 이 함수를 추가했다.
    """
    out = []
    for r in list(page.rects) + list(page.curves):
        if not r.get("fill"):
            continue
        if _is_near_white(r.get("non_stroking_color")):
            continue
        out.append((r["x0"], r["top"], r["x1"], r["bottom"]))
    for im in page.images:          # 이미지 위 글자도 보인다고 본다
        out.append((im["x0"], im["top"], im["x1"], im["bottom"]))
    return out


def _covered(ch: dict, boxes: List[tuple]) -> bool:
    return any(x0 <= ch["x0"] + 1 and x1 >= ch["x1"] - 1
               and top <= ch["top"] + 1 and bottom >= ch["bottom"] - 1
               for x0, top, x1, bottom in boxes)


def _hidden_reason(ch: dict, width: float, height: float,
                   backdrops: List[tuple] = ()):
    """이 문자가 사람에게 보이지 않는 이유. 보이면 None."""
    if ch.get("size", 99) < _MIN_VISIBLE_FONT_PT:
        return "tiny_font"
    if (ch.get("x1", 0) <= 0 or ch.get("x0", 0) >= width
            or ch.get("bottom", 0) <= 0 or ch.get("top", 0) >= height):
        return "offscreen"
    if _is_near_white(ch.get("non_stroking_color")) and not _covered(ch, backdrops):
        return "white_text"
    return None


def _group_runs(chars: List[Tuple[int, str, str]]) -> List[HiddenTextFinding]:
    """연속된 은닉 문자를 (페이지, 사유)별 문자열로 묶는다."""
    runs: List[HiddenTextFinding] = []
    for page, reason, text in chars:
        if runs and runs[-1]["page"] == page and runs[-1]["reason"] == reason:
            runs[-1]["text"] += text
        else:
            runs.append(HiddenTextFinding(reason=reason, page=page, text=text))
    return [r for r in runs if r["text"].strip()]


def extract_with_hidden_report(pdf_bytes: bytes) -> Tuple[str, List[HiddenTextFinding]]:
    """(사람이 볼 수 있는 텍스트, 은닉 텍스트 목록).

    은닉 문자는 추출 결과에서 제외한다 — 격리다. 뒤 단계는 사용자가 실제로
    보는 문서만 읽는다.
    """
    visible_pages: List[str] = []
    hidden_chars: List[Tuple[int, str, str]] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            w, h = page.width, page.height
            backs = _backdrops(page)
            for ch in page.chars:
                reason = _hidden_reason(ch, w, h, backs)
                if reason:
                    hidden_chars.append((page.page_number, reason, ch.get("text", "")))

            def _visible(obj, _w=w, _h=h, _b=backs):
                if obj.get("object_type") != "char":
                    return True
                return _hidden_reason(obj, _w, _h, _b) is None

            visible_pages.append(page.filter(_visible).extract_text() or "")

    return "\n".join(visible_pages), _group_runs(hidden_chars)


def hidden_text_is_attack(findings: List[HiddenTextFinding]) -> bool:
    """은닉 텍스트가 AI 조작 지시문인가 (단순 서식 잔여물과 구분)."""
    from src.injection_check import detect_injection

    return any(detect_injection(f["text"]) for f in findings)


def hidden_text_notice(findings: List[HiddenTextFinding]) -> str:
    """사용자 고지 — 무엇을 왜 뺐는지 밝힌다.

    경고 강도를 둘로 나눈다. 정부 표준 양식에도 서식 잔여물(빈칸 안내 문구
    등)이 흰 글씨로 남아 있는 경우가 실제로 있다. 그때까지 "공격!"이라고
    외치면 늑대소년이 되어, 정작 진짜 공격 때 사용자가 무시하게 된다.
    """
    kinds = sorted({_REASON_LABEL.get(f["reason"], f["reason"]) for f in findings})
    preview = findings[0]["text"].strip()[:50]
    if hidden_text_is_attack(findings):
        return (
            f"🚫 이 PDF에 **사람 눈에 보이지 않게 숨긴 AI 조작 지시문**이 "
            f"{len(findings)}곳 있습니다 (유형: {', '.join(kinds)}). "
            f"예: \"{preview}…\". 분석에서 전부 제외했습니다. 정상적인 계약서에는 "
            f"이런 텍스트가 들어갈 이유가 없습니다 — 이 문서를 건넨 상대방에게 "
            f"반드시 확인하고, 인쇄본과 대조하세요."
        )
    return (
        f"ℹ️ 이 PDF에서 화면에 보이지 않는 텍스트 {len(findings)}곳을 분석에서 "
        f"제외했습니다 (유형: {', '.join(kinds)}). 예: \"{preview}…\". "
        f"서식 작성 안내 문구 같은 잔여물로 보이며 조작 지시문은 아닙니다. "
        f"사람이 볼 수 없는 문구는 계약 내용이 아니므로 판정에 넣지 않습니다."
    )


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """PDF 바이트 -> 사람이 볼 수 있는 텍스트 (기존 호출부 호환용).

    은닉 텍스트는 제외된다. 무엇이 제외됐는지까지 알아야 하는 호출부는
    extract_with_hidden_report를 쓴다.
    """
    text, _ = extract_with_hidden_report(pdf_bytes)
    if not text.strip():
        raise ValueError(_EMPTY_PDF_ERROR)
    return text
