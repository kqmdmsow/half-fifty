"""개인정보 마스킹 (docs/privacy_data_handling.md 과제 1순위).

파이프라인 진입 전에 계약서 텍스트에서 식별 번호류를 가린다.
적용 지점은 run_pipeline 입구 — Parser 이전에 가려야 화면 표시·인용 검사·
LLM 전송이 전부 같은 텍스트를 보므로 citation_check가 깨지지 않는다.

설계 원칙: 위험 판정에 쓰이는 숫자(보증금·월세 금액, 날짜, 조항 번호,
연체 기수)는 절대 건드리지 않는다. 그래서 패턴이 자명한 것(주민등록번호·
전화번호·이메일·카드번호)만 무조건 가리고, 금액과 형태가 겹치는 계좌번호는
'계좌' 류 키워드가 앞에 있을 때만 가린다.

한계(문서화): 이름은 NER 없이는 못 가린다. 주소는 임대차 목적물 특정에
필요해 가리지 않는다. 사업자등록번호는 법인 식별 정보라 보류.
"""

import re
from typing import Dict, Tuple

# 순서 중요: 주민등록번호(6-7)를 전화번호(지역 02-XXXX-XXXX)보다 먼저 처리해야
# 뒷자리가 부분 매칭으로 쪼개지지 않는다.
_PATTERNS = [
    # 주민등록번호/외국인등록번호: 생년 6자리 - 성별코드(1~8) + 6자리
    ("주민등록번호", re.compile(r"\d{6}\s*[-–]\s*[1-8]\d{6}")),
    # 경계는 \b가 아니라 (?<!\d)/(?!\d)를 쓴다 — 한글 조사가 바로 붙는 경우
    # ("6789로 연락")에 \b는 digit→한글이 둘 다 \w라서 성립하지 않는다.
    # 카드번호: 4-4-4-4 (구분자 필수 — 구분자 없는 16자리는 금액과 충돌 위험)
    ("카드번호", re.compile(r"(?<!\d)\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}(?!\d)")),
    # 휴대전화: 010/011/016/017/018/019
    ("전화번호", re.compile(r"(?<!\d)01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)")),
    # 지역전화: 02-XXXX-XXXX, 031-XXX-XXXX 등 (구분자 필수)
    ("전화번호", re.compile(r"(?<!\d)0\d{1,2}[-.]\d{3,4}[-.]\d{4}(?!\d)")),
    ("이메일", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
]

# 계좌번호는 하이픈 포함 숫자열이 금액·기간과 형태가 겹치므로 키워드 앵커 필수.
# 키워드와 번호 사이에 은행명·콜론 등 최대 20자 허용 ("입금계좌 : 국민은행 123-456-789012").
_ACCOUNT_PATTERN = re.compile(
    r"(계좌번호|입금\s*계좌|계좌|가상계좌)([^\d\n]{0,20})(\d[\d-]{7,18}\d)"
)


def mask_pii(text: str) -> Tuple[str, Dict[str, int]]:
    """식별 번호류를 [유형] 토큰으로 치환하고 유형별 개수를 반환한다."""
    counts: Dict[str, int] = {}

    for label, pattern in _PATTERNS:
        text, n = pattern.subn(f"[{label}]", text)
        if n:
            counts[label] = counts.get(label, 0) + n

    def _mask_account(m: re.Match) -> str:
        counts["계좌번호"] = counts.get("계좌번호", 0) + 1
        return f"{m.group(1)}{m.group(2)}[계좌번호]"

    text = _ACCOUNT_PATTERN.sub(_mask_account, text)

    return text, counts


def masking_notice(counts: Dict[str, int]) -> str:
    """마스킹 결과를 사용자 고지 문장으로 변환 (parse_warnings 배너용)."""
    if not counts:
        return ""
    parts = ", ".join(f"{label} {n}건" for label, n in counts.items())
    return f"개인정보 보호를 위해 {parts}을(를) 자동으로 가렸어요. 분석에는 영향이 없어요."
