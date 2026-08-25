"""운영 가드레일 — 서비스 토큰·호출 제한·비용 상한 (#174).

## 왜 필요한가

배포 URL은 심사 기간(9/7 11:00 ~ 9/11 23:59) 동안 누구나 접근할 수 있다.
그 상태에서 세 가지가 현실적 위험이다.

1. **크레딧 고갈로 서비스 사망.** 분석 1건이 약 282원이다. 누군가 스크립트로
   수천 건을 돌리면 크레딧이 마르고, 심사위원이 접속했을 때 서비스가 죽어
   있다. 결격 사유로 직결된다.
2. **백엔드 우회.** 프론트→백엔드→에이전트 구조인데 에이전트가 공개
   URL이면 백엔드의 용량·형식 검사를 건너뛰고 직접 때릴 수 있다.
3. **한 사람이 전부 소진.** 상한이 전역이면 한 명이 다 써 버린다.

세 가지를 각각 막는다. 어느 것도 정상 사용자를 막지 않는 값으로 잡되,
막을 때는 조용히 실패하지 않고 이유를 분명히 알린다.
"""

import os
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

# ── 서비스 토큰 ───────────────────────────────────────────────────────
# 백엔드만 아는 토큰. 미설정이면 검사하지 않는다 — 로컬 개발과 기존 배포가
# 토큰 없이도 돌아가야 하기 때문이다. 운영에서는 반드시 설정할 것.
_TOKEN_HEADER = "x-service-token"


def service_token_required() -> bool:
    return bool(os.getenv("AGENT_SERVICE_TOKEN"))


def check_service_token(headers) -> bool:
    """백엔드를 거쳐 온 요청인가. 토큰 미설정 환경에서는 항상 통과."""
    expected = os.getenv("AGENT_SERVICE_TOKEN")
    if not expected:
        return True
    return headers.get(_TOKEN_HEADER) == expected


# ── 호출 제한 (슬라이딩 윈도우) ───────────────────────────────────────
# 분석은 1건에 70~90초 걸리는 무거운 작업이라 정상 사용자가 분당 여러 번
# 부를 일이 없다. 넉넉히 잡아도 남용은 걸린다.
_RATE_WINDOW_SEC = 60
_RATE_MAX = int(os.getenv("ANALYZE_RATE_PER_MIN", "6"))

_hits: Dict[str, Deque[float]] = defaultdict(deque)
_rate_lock = threading.Lock()


def rate_limit_ok(client_key: str) -> bool:
    """이 클라이언트가 분당 한도 안인가. 한도를 넘으면 False."""
    now = time.monotonic()
    with _rate_lock:
        q = _hits[client_key]
        while q and now - q[0] > _RATE_WINDOW_SEC:
            q.popleft()
        if len(q) >= _RATE_MAX:
            return False
        q.append(now)
        return True


def reset_rate_limits() -> None:
    """테스트용 — 윈도우 상태를 비운다."""
    with _rate_lock:
        _hits.clear()


# ── 비용 상한 ─────────────────────────────────────────────────────────
# 누적 출력 토큰으로 상한을 건다. 입력 토큰은 캐싱 때문에 실제 비용과 어긋나고,
# 출력 토큰이 단가가 높아 비용을 더 잘 대표한다.
#
# 상한에 걸리면 새 분석을 받지 않고 503을 낸다. 조용히 실패하거나 폴백으로
# 흡수하면 "판정을 못 받았다"가 "안전하다"로 읽힐 수 있어 더 위험하다.
_BUDGET_TOKENS = int(os.getenv("DAILY_OUTPUT_TOKEN_BUDGET", "0"))  # 0 = 무제한
_budget_lock = threading.Lock()
_budget_state = {"day": None, "spent": 0}


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def budget_remaining() -> int:
    """남은 출력 토큰. 상한 미설정이면 -1 (무제한)."""
    if _BUDGET_TOKENS <= 0:
        return -1
    with _budget_lock:
        if _budget_state["day"] != _today():
            return _BUDGET_TOKENS
        return max(0, _BUDGET_TOKENS - _budget_state["spent"])


def budget_ok() -> bool:
    return budget_remaining() != 0


def record_spend(output_tokens: int) -> None:
    """분석 1건이 끝난 뒤 사용량을 누적한다. 날짜가 바뀌면 초기화."""
    if _BUDGET_TOKENS <= 0:
        return
    with _budget_lock:
        today = _today()
        if _budget_state["day"] != today:
            _budget_state.update(day=today, spent=0)
        _budget_state["spent"] += max(0, output_tokens)


def reset_budget() -> None:
    """테스트용."""
    with _budget_lock:
        _budget_state.update(day=None, spent=0)


def status() -> dict:
    """/health 등에서 노출할 운영 상태."""
    return {
        "service_token_enforced": service_token_required(),
        "rate_limit_per_min": _RATE_MAX,
        "daily_output_token_budget": _BUDGET_TOKENS or None,
        "budget_remaining": budget_remaining(),
    }
