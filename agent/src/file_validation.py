"""업로드 파일 방어 (매직 바이트·용량) — 백엔드 ContractController와 동일 기준.

agent는 render.yaml상 public web service라 백엔드를 거치지 않고 직접 호출
가능하다(이슈 #77). 백엔드의 Content-Type 위조 방어(실제 바이트로 판별)와
용량 제한을 agent 엔드포인트에도 동일하게 적용해 우회를 막는다.
"""

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # backend ContractController.MAX_PDF_BYTES와 동일


def is_pdf_magic(data: bytes) -> bool:
    return len(data) >= 5 and data[:5] == b"%PDF-"


def sniff_image_type(data: bytes) -> str | None:
    """매직 바이트로 이미지 형식 판별. 미지원 형식은 None (backend sniffImageType 이식)."""
    if len(data) >= 3 and data[0:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 8 and data[0:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
