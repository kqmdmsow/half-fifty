"""OCR: 사진·스캔본에서 텍스트 추출 (Upstage Document Parse).

왜: 타깃 사용자(고령층·금융 취약계층)의 자연스러운 입력은 종이 계약서를
사진 찍는 것이지 텍스트 복사가 아니다. 기존 pdf_extract는 텍스트 레이어가
있는 디지털 PDF만 처리 — 스캔본 PDF와 사진(jpg/png)은 여기서 처리한다.

Document Parse를 쓰는 이유: 단순 OCR과 달리 레이아웃·표를 구조로 인식한다 —
계약서 별표(수수료율 표 등)가 핵심 위험 정보인 우리 도메인에 적합
(전문가 자문 §2 "별표·부칙·특약·표가 보존되는지"와 같은 문제의식).

주의: 팀 7월 회의에서 OCR은 Phase 2 스트레치로 보류됐던 항목 — 2026-08-12
팀(동훈) 결정으로 선구현. UPSTAGE_API_KEY 없으면 기능이 조용히 꺼진 것과
같은 동작(예외)이므로 기존 경로에는 영향 없다.
"""

import os

import requests

_API_URL = "https://api.upstage.ai/v1/document-digitization"
_TIMEOUT_SEC = 120  # 다페이지 스캔본 대비 넉넉히

# 백엔드 매직 바이트 검사와 일치시킬 것 (jpg/png/webp/pdf)
SUPPORTED_IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp")


class OcrUnavailableError(RuntimeError):
    """키 미설정·API 실패 등으로 OCR을 쓸 수 없는 상태."""


def document_parse_text(file_bytes: bytes, filename: str) -> str:
    """파일(스캔 PDF·이미지) -> 텍스트. 실패 시 OcrUnavailableError."""
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        raise OcrUnavailableError("UPSTAGE_API_KEY 미설정 — OCR 비활성")

    try:
        resp = requests.post(
            _API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"document": (filename, file_bytes)},
            data={"model": "document-parse", "output_formats": "['text']"},
            timeout=_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        payload = resp.json()
    except OcrUnavailableError:
        raise
    except Exception as exc:  # 네트워크·인증·파싱 실패 모두 동일 처리
        raise OcrUnavailableError(f"Document Parse 호출 실패: {exc}") from exc

    text = (payload.get("content") or {}).get("text", "")
    if not text.strip():
        raise OcrUnavailableError("OCR 결과가 비어 있음 (판독 불가 이미지일 수 있음)")
    return text
