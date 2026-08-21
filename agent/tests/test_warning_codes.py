"""경고 코드 분류 테스트 (#86-②) — 생성부 문구와 분류기의 결합을 잠근다."""

from src.masking import mask_pii, masking_notice
from src.warning_codes import classify


def test_마스킹_고지_분류():
    _, counts = mask_pii("연락처 010-1234-5678")
    assert classify(masking_notice(counts)) == "pii_masked"


def test_인젝션_경고_분류():
    # injection_check 모듈은 PR #131에서 합류 — 여기서는 문두 문구로 검증
    # (#131 머지 후 injection_warning() 직접 호출로 강화할 것)
    assert classify("⚠️ 이 문서에서 AI 분석 결과를 조작하려는 것으로 보이는 문구 2건이 감지되었습니다") == "injection_detected"


def test_파서_경고_분류():
    # 생성부(src/nodes/parser.py) 문구가 바뀌면 이 테스트가 함께 깨져야 한다
    assert classify("별지(첨부 문서) 이후 내용은 조항 분석에서 제외했습니다. ...") == "byulji_excluded"
    assert classify("문서의 일부가 조항으로 분리되지 않았습니다 ...") == "low_coverage"


def test_모르는_경고는_None():
    assert classify("완전히 새로운 경고 문구") is None
