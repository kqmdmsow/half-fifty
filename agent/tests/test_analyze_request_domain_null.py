"""domain 필드에 null이 오면 422로 막히던 실배포 장애 회귀 테스트.

백엔드(Java record AnalyzeRequest)는 도메인 미선택 시 domain 필드를 null로
직렬화한다. 에이전트의 domain: str 필드가 이를 거부해 배포 서비스의
/api/contracts/analyze가 전부 502(에이전트 422 래핑)로 죽는 사고가 있었다
(2026-08-31, "Failed to fetch" 신고 조사 중 발견·재현·수정).
"""

from main import AnalyzeRequest, DisclosureRequest


def test_domain_null이면_빈_문자열로_정규화된다():
    req = AnalyzeRequest(text="제1조 테스트", persona="adult", language=None, domain=None)
    assert req.domain == ""
    assert req.language is None


def test_domain_생략해도_기본값_빈_문자열():
    req = AnalyzeRequest(text="제1조 테스트")
    assert req.domain == ""


def test_disclosure_request도_domain_null_허용():
    req = DisclosureRequest(text="t", transcript="상담 내용입니다", domain=None)
    assert req.domain == ""
