"""OCR 모듈 테스트 — 실호출 없이 응답 계약을 검증 (실호출 검증은 2026-08-12 수행)."""
import pytest

import src.ocr as ocr
from src.ocr import OcrUnavailableError, document_parse_text


class _FakeResp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p


def test_no_key_raises(monkeypatch):
    monkeypatch.delenv("UPSTAGE_API_KEY", raising=False)
    with pytest.raises(OcrUnavailableError, match="미설정"):
        document_parse_text(b"x", "a.png")


def test_success_extracts_text(monkeypatch):
    monkeypatch.setenv("UPSTAGE_API_KEY", "k")
    monkeypatch.setattr(ocr.requests, "post",
                        lambda *a, **kw: _FakeResp({"content": {"text": "제1조 목적"}}))
    assert document_parse_text(b"x", "a.png") == "제1조 목적"


def test_empty_text_raises(monkeypatch):
    monkeypatch.setenv("UPSTAGE_API_KEY", "k")
    monkeypatch.setattr(ocr.requests, "post",
                        lambda *a, **kw: _FakeResp({"content": {"text": "  "}}))
    with pytest.raises(OcrUnavailableError, match="비어"):
        document_parse_text(b"x", "a.png")


def test_network_error_wrapped(monkeypatch):
    monkeypatch.setenv("UPSTAGE_API_KEY", "k")
    def _boom(*a, **kw): raise ConnectionError("down")
    monkeypatch.setattr(ocr.requests, "post", _boom)
    with pytest.raises(OcrUnavailableError, match="호출 실패"):
        document_parse_text(b"x", "a.png")
