"""테스트용 최소 PDF 생성기 — 외부 의존성 없이 은닉 텍스트 공격을 재현한다.

reportlab 같은 생성 라이브러리를 새로 넣지 않으려고 PDF 문법을 직접 쓴다.
한글은 CID 폰트가 필요해 복잡하므로 ASCII 공격 문구를 쓴다 — 탐지 대상은
색상·크기·좌표이지 언어가 아니다.
"""

from typing import List, Tuple

# (텍스트, x, y, 폰트크기, 색상 rgb 0~1) — 색상 None이면 기본(검정)
Item = Tuple[str, float, float, float, tuple]


def build_pdf(items: List[Item], width: float = 595, height: float = 842) -> bytes:
    ops = []
    for text, x, y, size, color in items:
        esc = text.replace("\\\\", "\\\\\\\\").replace("(", "\\\\(").replace(")", "\\\\)")
        if color is not None:
            ops.append(f"{color[0]} {color[1]} {color[2]} rg")
        else:
            ops.append("0 0 0 rg")
        ops.append(f"BT /F1 {size} Tf {x} {y} Td ({esc}) Tj ET")
    content = "\n".join(ops).encode("latin-1")

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
         f"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>").encode("latin-1"),
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n").encode()
    return bytes(out)
