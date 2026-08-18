"""업로드 파일 매직 바이트 검사 테스트 (#77 — agent 직접 호출 우회 방어)."""
from src.file_validation import is_pdf_magic, sniff_image_type

JPEG_HEADER = b"\xff\xd8\xff\xe0\x00\x10JFIF"
PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
WEBP_HEADER = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP"


def test_pdf_magic_accepted():
    assert is_pdf_magic(b"%PDF-1.7\n%...")


def test_pdf_magic_rejects_non_pdf():
    assert not is_pdf_magic(JPEG_HEADER)
    assert not is_pdf_magic(b"")
    assert not is_pdf_magic(b"PDF-")  # % 없음


def test_jpeg_sniffed():
    assert sniff_image_type(JPEG_HEADER) == "image/jpeg"


def test_png_sniffed():
    assert sniff_image_type(PNG_HEADER) == "image/png"


def test_webp_sniffed():
    assert sniff_image_type(WEBP_HEADER) == "image/webp"


def test_unsupported_bytes_rejected():
    assert sniff_image_type(b"%PDF-1.7") is None
    assert sniff_image_type(b"not an image") is None
    assert sniff_image_type(b"") is None


def test_content_type_스푸핑_방어():
    """Content-Type 헤더를 image/png로 위조해도 실제 바이트가 PDF면 sniff는 속지 않는다."""
    fake_png_but_actually_pdf = b"%PDF-1.4\n..."
    assert sniff_image_type(fake_png_but_actually_pdf) is None
