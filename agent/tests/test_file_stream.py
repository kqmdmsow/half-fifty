"""/analyze-file-stream 엔드포인트 테스트 — LLM·OCR 없이 이벤트 계약만 검증.

stream_analysis와 텍스트 추출을 monkeypatch로 대체해 다음을 확인한다:
- 추출 성공: extract 이벤트가 맨 앞에 오고 이후 stream_analysis 이벤트가 이어진다
- 추출 실패: error 이벤트(status 422)가 오고 스트림이 닫힌다
- 검증 실패(용량·형식)는 스트림 이전이므로 기존과 동일하게 HTTP 상태로 응답한다
"""
import json

from fastapi.testclient import TestClient

import main as agent_main

client = TestClient(agent_main.app)

_PDF_BYTES = b"%PDF-1.7\nfake pdf body"
_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF fake"


def _events(response):
    return [json.loads(line) for line in response.text.strip().split("\n")]


def _fake_stream(text, persona, language, domain):
    yield {"event": "meta", "clause_count": 1, "parse_warnings": [], "domain": domain,
           "clauses": [{"clause_id": "clause_001", "text": text}]}
    yield {"event": "judge", "judge_scores": {}, "needs_review": False, "retry_count": 0}
    yield {"event": "done"}


def test_pdf_extract_후_스트림_이벤트_순서(monkeypatch):
    monkeypatch.setattr(agent_main, "extract_text_from_pdf", lambda raw: "제1조 텍스트")
    monkeypatch.setattr(agent_main, "stream_analysis", _fake_stream)

    res = client.post("/analyze-file-stream",
                      files={"file": ("c.pdf", _PDF_BYTES, "application/pdf")},
                      data={"persona": "adult", "domain": "주택임대차"})
    assert res.status_code == 200
    events = _events(res)
    assert [e["event"] for e in events] == ["extract", "meta", "judge", "done"]
    assert events[1]["domain"] == "주택임대차"


def test_이미지는_ocr_경유(monkeypatch):
    monkeypatch.setattr(agent_main, "document_parse_text", lambda raw, name: "제1조 텍스트")
    monkeypatch.setattr(agent_main, "stream_analysis", _fake_stream)

    res = client.post("/analyze-file-stream",
                      files={"file": ("c.jpg", _JPEG_BYTES, "image/jpeg")})
    assert res.status_code == 200
    assert [e["event"] for e in _events(res)][:2] == ["extract", "meta"]


def test_추출_실패는_error_이벤트(monkeypatch):
    from src.ocr import OcrUnavailableError

    def fail(raw, name):
        raise OcrUnavailableError("UPSTAGE_API_KEY 미설정")

    monkeypatch.setattr(agent_main, "document_parse_text", fail)

    res = client.post("/analyze-file-stream",
                      files={"file": ("c.jpg", _JPEG_BYTES, "image/jpeg")})
    assert res.status_code == 200  # 스트림은 이미 열렸으므로 이벤트로 실패를 알린다
    events = _events(res)
    assert events[0]["event"] == "extract"
    assert events[1]["event"] == "error"
    assert events[1]["status"] == 422


def test_스캔본_pdf는_ocr_폴백(monkeypatch):
    def no_text_layer(raw):
        raise ValueError("텍스트 레이어 없음")

    monkeypatch.setattr(agent_main, "extract_text_from_pdf", no_text_layer)
    monkeypatch.setattr(agent_main, "document_parse_text", lambda raw, name: "제1조 텍스트")
    monkeypatch.setattr(agent_main, "stream_analysis", _fake_stream)

    res = client.post("/analyze-file-stream",
                      files={"file": ("scan.pdf", _PDF_BYTES, "application/pdf")})
    assert [e["event"] for e in _events(res)][:2] == ["extract", "meta"]


def test_지원하지_않는_형식은_415():
    res = client.post("/analyze-file-stream",
                      files={"file": ("c.txt", b"plain text", "text/plain")})
    assert res.status_code == 415


def test_용량_초과는_413():
    big = b"%PDF-" + b"0" * (10 * 1024 * 1024 + 1)
    res = client.post("/analyze-file-stream",
                      files={"file": ("big.pdf", big, "application/pdf")})
    assert res.status_code == 413
