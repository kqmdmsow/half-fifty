"""domain 필드에 null이 오면 422로 막히던 실배포 장애 회귀 테스트.

백엔드(Java record AnalyzeRequest)는 도메인 미선택 시 domain 필드를 null로
직렬화한다. 에이전트의 domain: str 필드가 이를 거부해 배포 서비스의
/api/contracts/analyze가 전부 502(에이전트 422 래핑)로 죽는 사고가 있었다
(2026-08-31, "Failed to fetch" 신고 조사 중 발견·재현·수정).
"""

import pytest
from pydantic import ValidationError

from main import AnalyzeRequest, DisclosureRequest


def test_공백만_있는_텍스트는_거절된다():
    # 빈 텍스트를 그대로 통과시키면 파이프라인이 재시도 2회+judge까지 태우고서야
    # 빈 결과로 끝난다 — 프론트가 text.trim()으로 막고 있지만 요청 단계에서도
    # 방어해 다른 호출 경로의 크레딧 낭비를 막는다.
    with pytest.raises(ValidationError):
        AnalyzeRequest(text="   ", persona="adult")


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


def test_persona_null이면_adult로_정규화된다():
    # persona도 domain과 같은 계열(Literal 필드가 null을 거부해 422) — 실제
    # 프론트는 TS 필수 파라미터라 도달하지 않지만 API 직접 호출 등 다른
    # 경로도 안전하게 만든다.
    req = AnalyzeRequest(text="제1조 테스트", persona=None)
    assert req.persona == "adult"
