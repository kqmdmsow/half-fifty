"""parse_warnings 기계 판독 코드 (#86-② 경고문 다국어화).

경고 문자열은 한국어 그대로 유지(한국어 사용자·하위 호환)하고, 각 경고에
대응하는 코드를 병행 전송한다 — 프론트는 코드를 알면 16개 언어 사전으로
현지화하고, 모르는 코드/신규 경고는 원문 문자열로 폴백한다 (#100의
analysis_failed 마커와 동일 패턴).

classify()는 경고 생성부의 문두 문구에 의존한다 — 문구를 바꿀 때 여기와
테스트(test_warning_codes.py)를 함께 갱신할 것.
"""

from typing import List, Optional

_PREFIXES = [
    ("pii_masked", "개인정보 보호를 위해"),          # src/masking.py masking_notice
    ("byulji_excluded", "별지(첨부 문서) 이후"),      # src/nodes/parser.py
    ("low_coverage", "문서의 일부가 조항으로"),       # src/nodes/parser.py
    ("injection_detected", "⚠️ 이 문서에서"),        # src/injection_check.py
    ("injection_neutralized", "🛡️ 이 문서에"),        # src/injection_check.py (#174)
    ("pdf_hidden_attack", "🚫 이 PDF에 "),            # src/pdf_extract.py (#174)
    ("pdf_hidden_benign", "ℹ️ 이 PDF에서"),           # src/pdf_extract.py (#174)
    ("clause_quarantined", "🚫 이 조항에서"),          # src/injection_check.py (#174)
    ("ocr_layer_mismatch", "🚨 이 PDF는"),            # src/pdf_extract.py (#174)
]


def classify(warning: str) -> Optional[str]:
    for code, prefix in _PREFIXES:
        if warning.startswith(prefix):
            return code
    return None


def classify_all(warnings: List[str]) -> List[Optional[str]]:
    """warnings와 인덱스 정렬이 보장되는 코드 목록."""
    return [classify(w) for w in warnings]
