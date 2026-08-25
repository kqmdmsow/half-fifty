"""운영 가드레일 (#174) — 서비스 토큰·호출 제한·비용 상한.

배포 URL은 심사 기간 동안 누구나 접근할 수 있다. 분석 1건이 약 282원이라,
누가 스크립트로 수천 건을 돌리면 크레딧이 말라 심사위원이 접속했을 때
서비스가 죽어 있다. 결격 사유로 직결되는 위험이다.
"""

import os

import pytest
from fastapi.testclient import TestClient

import main as agent_main
from src import guardrails as g

client = TestClient(agent_main.app)


# ---- 서비스 토큰 -----------------------------------------------------

def test_토큰_미설정이면_검사하지_않는다(monkeypatch):
    # 로컬 개발과 기존 배포가 토큰 없이도 돌아가야 한다.
    monkeypatch.delenv("AGENT_SERVICE_TOKEN", raising=False)
    assert g.check_service_token({}) is True
    assert g.service_token_required() is False


def test_토큰이_설정되면_일치해야_통과(monkeypatch):
    monkeypatch.setenv("AGENT_SERVICE_TOKEN", "s3cret")
    assert g.check_service_token({"x-service-token": "s3cret"}) is True
    assert g.check_service_token({"x-service-token": "wrong"}) is False
    assert g.check_service_token({}) is False


def test_토큰_불일치_요청은_403(monkeypatch):
    monkeypatch.setenv("AGENT_SERVICE_TOKEN", "s3cret")
    res = client.post("/analyze", json={"text": "제1조 테스트", "persona": "adult"})
    assert res.status_code == 403
    assert "백엔드" in res.json()["detail"]


def test_헬스체크는_토큰_없이도_열려_있다(monkeypatch):
    # 외부 모니터링이 5분마다 때리는 곳이다. 막히면 감시가 죽는다.
    monkeypatch.setenv("AGENT_SERVICE_TOKEN", "s3cret")
    assert client.get("/health").status_code == 200


# ---- 호출 제한 -------------------------------------------------------

def test_한도_안에서는_통과하고_넘으면_막힌다():
    limit = g._RATE_MAX
    for _ in range(limit):
        assert g.rate_limit_ok("1.2.3.4") is True
    assert g.rate_limit_ok("1.2.3.4") is False


def test_클라이언트마다_따로_센다():
    # 상한이 전역이면 한 명이 다 써 버린다.
    for _ in range(g._RATE_MAX):
        g.rate_limit_ok("1.2.3.4")
    assert g.rate_limit_ok("5.6.7.8") is True


# ---- 비용 상한 -------------------------------------------------------

def test_상한_미설정이면_무제한(monkeypatch):
    monkeypatch.setattr(g, "_BUDGET_TOKENS", 0)
    assert g.budget_remaining() == -1
    assert g.budget_ok() is True


def test_상한을_소진하면_거부한다(monkeypatch):
    monkeypatch.setattr(g, "_BUDGET_TOKENS", 100)
    assert g.budget_ok() is True
    g.record_spend(60)
    assert g.budget_remaining() == 40
    g.record_spend(50)
    assert g.budget_remaining() == 0
    assert g.budget_ok() is False


def test_상한_도달시_안전하다는_뜻이_아님을_알린다(monkeypatch):
    """조용히 실패하면 '판정을 못 받았다'가 '문제 없다'로 읽힌다."""
    monkeypatch.setattr(g, "_BUDGET_TOKENS", 10)
    g.record_spend(20)
    res = client.post("/analyze", json={"text": "제1조 테스트", "persona": "adult"})
    assert res.status_code == 503
    assert "안전하다는 뜻이 아닙니다" in res.json()["detail"]


def test_헬스체크가_가드레일_상태를_노출한다():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "budget_remaining" in body["guardrails"]
    assert "rate_limit_per_min" in body["guardrails"]
