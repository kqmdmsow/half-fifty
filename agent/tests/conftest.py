"""테스트 공통 설정.

운영 가드레일(#174)은 프로세스 전역 상태를 쓴다 — 호출 제한 윈도우와 비용
누적. 테스트는 같은 프로세스에서 같은 엔드포인트를 수십 번 때리므로, 초기화
없이는 뒤에 도는 테스트가 429로 떨어진다. 실제로 test_용량_초과는_413이
그렇게 깨졌다.

프로덕션 동작을 바꾸지 않고 테스트 사이에만 상태를 비운다.
"""

import pytest

from src.guardrails import reset_budget, reset_rate_limits


@pytest.fixture(autouse=True)
def _reset_guardrails():
    reset_rate_limits()
    reset_budget()
    yield
