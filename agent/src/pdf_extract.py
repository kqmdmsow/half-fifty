"""PDF 텍스트 추출 (디지털 PDF 전용, 스캔본/OCR은 범위 밖).

추출한 텍스트는 그대로 Parser(src/nodes/parser.py)에 넘긴다. Parser는 이미
별지·서명란·조 참조 노이즈를 걸러내도록 튜닝돼 있으므로 여기서는 텍스트
추출만 담당한다.
"""

import io

import pdfplumber

_EMPTY_PDF_ERROR = "텍스트를 추출할 수 없는 PDF입니다 (스캔본일 수 있음)"


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """PDF 바이트 -> 페이지별 텍스트를 이어붙인 문자열.

    텍스트 레이어가 없는 페이지(스캔 이미지 등)는 빈 문자열로 건너뛴다.
    전체 결과가 공백뿐이면 스캔본으로 간주해 ValueError를 던진다.
    """
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]

    text = "\n".join(pages)
    if not text.strip():
        raise ValueError(_EMPTY_PDF_ERROR)

    return text
