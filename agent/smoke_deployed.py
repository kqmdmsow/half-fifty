"""실배포 스모크 E2E — 배포된 URL이 심사에 쓸 수 있는 상태인가 (#174).

## 왜 로컬 테스트로는 부족한가

로컬 테스트 229개가 다 통과해도 배포본이 죽어 있으면 소용이 없다. 심사는
**제출한 URL**로 이뤄지고, 접근 불가는 결격 사유다(9/7 11:00 ~ 9/11 23:59).
로컬과 배포는 환경변수·플랜·콜드스타트·CORS가 전부 다르다.

## 무엇을 보는가

1. **3계층 생존** — 프론트·백엔드·에이전트가 각각 응답하는가.
2. **콜드스타트 시간** — 첫 응답이 몇 초인가. 심사위원은 30초를 기다리지
   않는다. Free 플랜에서 90초를 넘긴 실측이 있다(#84).
3. **실제 분석 완주** — 헬스체크만 200이고 분석이 죽는 경우가 실제로 있다.
   조항 하나를 실제로 넣어 판정까지 받아 본다.
4. **가드레일 상태** — 비용 상한이 남아 있는가. 소진돼 있으면 심사 중에
   서비스가 거부를 낸다.

크레딧을 쓰는 검사(3번)는 조항 1건짜리라 원가가 무시할 수준이다.

사용법: cd agent && python smoke_deployed.py
  FRONT_URL / BACKEND_URL / AGENT_URL 로 대상 변경
  SKIP_ANALYZE=1 로 3번 생략 (크레딧 미사용)
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

FRONT = os.getenv("FRONT_URL", "https://halffifty.onrender.com")
BACKEND = os.getenv("BACKEND_URL", "https://halffifty-backend.onrender.com")
AGENT = os.getenv("AGENT_URL", "https://halffifty-agent.onrender.com")
SKIP_ANALYZE = os.getenv("SKIP_ANALYZE") == "1"

# 콜드스타트 허용치. 심사위원 이탈 기준으로 잡았다 — 넘으면 실패가 아니라
# 경고로 낸다(서비스는 살아 있으므로).
_WARN_SECONDS = 15.0
_TIMEOUT = 240

# gold=위험인 짧은 조항. 판정이 '안전'으로 나오면 배포본에 문제가 있는 것이다.
PROBE_CLAUSE = ("제3조(기한의 이익 상실) 을이 이자 지급을 1회라도 지체한 경우 "
                "갑은 즉시 대출금 전액의 상환을 청구할 수 있다.")

results = []


def check(name: str, fn):
    start = time.perf_counter()
    try:
        detail = fn()
        ok, err = True, ""
    except Exception as exc:                     # 네트워크·파싱·검증 실패 전부
        detail, ok, err = "", False, f"{type(exc).__name__}: {exc}"
    elapsed = time.perf_counter() - start
    slow = ok and elapsed > _WARN_SECONDS
    mark = "OK  " if ok and not slow else ("느림" if slow else "실패")
    print(f"[{mark}] {name} ({elapsed:.1f}s) {detail}{err}")
    results.append({"name": name, "ok": ok, "slow": slow,
                    "seconds": elapsed, "error": err})


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=_TIMEOUT) as r:
        body = r.read().decode("utf-8", "replace")
    return json.loads(body) if body.strip().startswith("{") else {"raw": body[:80]}


def front_alive():
    with urllib.request.urlopen(FRONT, timeout=_TIMEOUT) as r:
        assert r.status == 200, f"status {r.status}"
    return ""


def backend_health():
    body = _get(f"{BACKEND}/health")
    assert body.get("status") == "ok", f"unexpected: {body}"
    return ""


def agent_health():
    body = _get(f"{AGENT}/health")
    assert body.get("status") == "ok", f"unexpected: {body}"
    g = body.get("guardrails", {})
    remaining = g.get("budget_remaining", -1)
    assert remaining != 0, "비용 상한 소진 — 심사 중 분석이 거부된다"
    token = "토큰 강제" if g.get("service_token_enforced") else "토큰 미설정"
    return f"— {token}, 남은 예산 {'무제한' if remaining == -1 else remaining}"


def analyze_probe():
    payload = json.dumps({"text": PROBE_CLAUSE, "persona": "adult"}).encode()
    req = urllib.request.Request(
        f"{BACKEND}/api/contracts/analyze", data=payload,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        body = json.loads(r.read().decode("utf-8"))
    clauses = body.get("results") or []
    assert clauses, "조항이 하나도 안 나왔다 (파서 또는 분석 실패)"
    level = clauses[0].get("risk_level")
    assert level != "안전", f"gold=위험 조항을 '{level}'으로 판정"
    # #174 필드가 REST 경로에서 유실되지 않는지도 함께 본다
    assert "injection_suspected" in clauses[0], "방화벽 필드가 응답에서 누락됐다"
    return f"— 판정 {level}, 조항 {len(clauses)}건"


def main():
    print(f"실배포 스모크 — front={FRONT}\n              backend={BACKEND}\n"
          f"              agent={AGENT}\n")
    check("프론트 접속", front_alive)
    check("백엔드 /health", backend_health)
    check("에이전트 /health", agent_health)
    if SKIP_ANALYZE:
        print("[생략] 실제 분석 (SKIP_ANALYZE=1)")
    else:
        check("실제 분석 완주", analyze_probe)

    failed = [r for r in results if not r["ok"]]
    slow = [r for r in results if r["slow"]]
    print()
    if slow:
        print(f"⚠️  {len(slow)}건이 {_WARN_SECONDS:.0f}초를 넘겼다 "
              f"({', '.join(r['name'] for r in slow)}). 콜드스타트라면 유료 플랜 "
              f"전환이 필요하다 — 심사위원은 기다리지 않는다.")
    if failed:
        print(f"❌ {len(failed)}건 실패: {', '.join(r['name'] for r in failed)}")
        sys.exit(1)
    print("✅ 전부 통과 — 배포본이 심사에 쓸 수 있는 상태다.")


if __name__ == "__main__":
    main()
