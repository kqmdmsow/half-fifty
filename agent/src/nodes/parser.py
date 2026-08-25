"""Parser Module (규칙 기반, LLM 호출 없음).

계약서 원문을 조항 단위로 분리한다.
- "제N조", "제 N 조"가 줄 시작에 있을 때만 새 조항으로 분리 (문장 중간의
  "제4조 제1항을 위반한..." 같은 조 참조나 "제6조의3" 같은 법령 인용은 제외)
- "특약사항" 이하 목록("1." 및 "Ÿ"/"•"/"-"/"*" 불릿)도 개별 조항으로 취급
- 별지·별표·부록·부칙은 **버리지 않고 별도 구획으로 파싱한다** (#174). 수수료율표,
  위약금 기준, 추가 특약이 여기 들어가는 경우가 많아 버리면 정작 위험한 조건을
  놓친다. 서명란 이후만 버린다 (계약 조항이 아님).
- PDF 쪽번호 줄과, 체크박스 빈칸만 있고 문장이 없는 양식 안내 항목도 제외한다
  (무엇을 뺐는지는 항상 경고로 알린다 — 조용한 누락 금지)
표준계약서(공정위 표준약관, 국토부 표준계약서)는 형식이 규칙적이므로 규칙 기반으로 충분하다.
"""

import re
from typing import List

import logging

logger = logging.getLogger(__name__)

from src.state import Clause, PipelineState

# "제1조", "제 1 조", "제1조(목적)", "제9조의2(계약갱신)" 등을 줄 시작에서만 잡는다.
# 실제 계약서는 "제9조의2" 형태의 가지조문 표제를 쓰므로 "조의N"도 조항 시작이다
# (중간보고서에서 제9조의2가 앞 조항에 병합되던 버그 — 자문 §2 지적 사항).
# 단, 표제는 뒤에 "("나 공백/개행이 오고, "제6조의3에 따라" 같은 법령 인용은
# 조사(에/를/과…)가 바로 붙으므로 [\s(] 요구로 구분한다.
_ARTICLE_PATTERN = re.compile(
    r"(?=^[ \t]*제\s*\d+\s*조(?:\s*의\s*\d+)?(?=[\s(]))",
    re.MULTILINE,
)

# 특약사항 구간의 항목 구분자: "1." 번호 목록 또는 "Ÿ"/"•"/"-"/"*" 불릿.
# 줄 시작이거나 공백 뒤에 오는 경우만 인정한다 (예: "-【예시】"처럼 뒤에 공백이
# 없는 하이픈은 불릿이 아니라 문장 안의 기호이므로 제외).
_SPECIAL_ITEM_PATTERN = re.compile(
    r"(?=(?:^|(?<=\s))(?:\d+\.\s|[Ÿ•\-*]\s))",
    re.MULTILINE,
)

# 부속문서 헤더: 줄 전체가 "별지1)", "별표 2", "부록", "부칙" 등으로만 이루어진 경우.
# 본문 중 "(별지1)을 확인하세요"처럼 문장에 섞인 참조는 매칭하지 않는다.
#
# 예전에는 별지 이후를 통째로 버리고 "중요한 내용이 있으면 따로 붙여넣으라"고
# 사용자에게 떠넘겼다. 그런데 **수수료율표·위약금 기준·추가 특약이 정확히 거기
# 들어간다.** 위험이 숨는 자리를 스스로 잘라내고 있었던 셈이라, 버리지 않고
# 구획으로 나눠 분석 대상에 포함한다 (#174).
_ANNEX_HEADER_PATTERN = re.compile(
    r"^[ \t]*(별지|별표|부록|부칙|첨부)\s*(\d+)?\s*[).\]]?[ \t]*$", re.MULTILINE)

# PDF에서 추출한 원문에 남는 쪽번호 줄("- 1 / 4 -", "- 2 -", "3 / 10").
# 쪽번호가 조항 본문 한가운데 끼면 그 뒤 표 조각까지 같은 조항으로 묶여 판정
# 근거가 오염된다 (docs/eval_normal_fp.md housing_std clause_005).
# 하이픈으로 감싼 형태나 "쪽/전체" 형태만 지운다 — 숫자만 있는 줄은 표에서
# 떨어져 나온 금액·면적일 수 있어 건드리지 않는다.
_PAGE_NUMBER_PATTERN = re.compile(
    r"^[ \t]*(?:-[ \t]*\d+[ \t]*(?:/[ \t]*\d+[ \t]*)?-|\d+[ \t]*/[ \t]*\d+)[ \t]*$",
    re.MULTILINE,
)

# 한국어 서술문의 종결 신호. 계약 문언은 "…한다.", "…없습니다"처럼 끝나지만,
# 양식의 빈칸 안내는 "( □ 없음 □ 있음 ※공사시기 :"처럼 종결되지 않고 끊긴다.
# "다"로 끝나는 어절은 서술어로 보되, "없음/있음"은 체크박스 선택지의 명사형
# 레이블이므로 마침표가 붙었을 때만 종결로 인정한다.
_SENTENCE_END_PATTERN = re.compile(r"[다요][.。]|습니다|[음함임][.。]|다(?=[\s)\]]|$)")

# 양식 빈칸 신호: 체크박스, 날짜·금액 빈칸, 콜론 뒤 공백으로 끝나는 항목.
_FORM_BLANK_PATTERN = re.compile(r"[□■☐]|년\s+월\s+일|년\s+월(?!\s*\S)|:\s*$|\(\s*\)")

# 서명란 시작을 알리는 문구. 이 뒤로는 서명/날인 표 등 조항이 아닌 내용이다.
_SIGNATURE_BLOCK_MARKER = "본 계약을 증명하기 위하여"


def _truncate_boilerplate(text: str) -> tuple[str, List[str]]:
    """서명란 이후처럼 계약 조항이 아닌 꼬리 텍스트만 잘라낸다.

    별지·별표·부록·부칙은 여기서 자르지 않는다 — _split_sections가 별도 구획으로
    떼어내 분석 대상에 포함한다 (#174).
    """
    warnings: List[str] = []
    sig_idx = text.find(_SIGNATURE_BLOCK_MARKER)
    if sig_idx != -1:
        text = text[:sig_idx]
    return text, warnings


def _split_sections(text: str) -> List[tuple[str, str]]:
    """(구획명, 본문) 목록으로 나눈다. 첫 구획은 항상 "본문"이다.

    부속문서 헤더("별지1)", "별표 2", "부칙")를 경계로 삼는다. 헤더 줄 자체는
    구획명이 되고 본문에서는 빠진다 — 조항 텍스트에 섞이면 판정 근거가 오염된다.
    """
    matches = list(_ANNEX_HEADER_PATTERN.finditer(text))
    if not matches:
        return [("본문", text)]

    sections: List[tuple[str, str]] = [("본문", text[: matches[0].start()])]
    for i, m in enumerate(matches):
        kind, num = m.group(1), m.group(2)
        name = f"{kind}{num}" if num else kind
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((name, text[m.end():end]))
    return [(n, b) for n, b in sections if b.strip()]


def _is_form_artifact(chunk: str) -> bool:
    """계약 문언이 아니라 양식에 인쇄된 빈칸·안내 조각인지 판별한다.

    표준계약서를 PDF에서 뽑으면 체크박스 선택지와 안내문이 특약사항 항목처럼
    잡혀 위험 판정 대상이 된다 (docs/eval_normal_fp.md housing_std clause_016:
    "Ÿ 상세주소가 없는 경우 … ( □ 동의 ※ 소요기간 : □ 미동의) 개월) …"이
    '주의/일방적 계약 해지'로 오탐).

    두 조건을 모두 만족할 때만 조각으로 본다 — 어느 하나로는 정상 조항을
    잘라낼 위험이 있기 때문:
    - 완결된 서술문이 하나도 없다 (양식 빈칸은 문장이 끊긴 채 끝난다)
    - 체크박스나 날짜·금액 빈칸이 있다 (양식 서식의 직접 증거)

    임차인이 손으로 써 넣은 특약("보증금은 반환하지 않는다")은 완결 문장이
    있으므로 남는다 — 특약사항이야말로 위험 조항이 숨는 자리라 과잉 제거는
    누락보다 나쁘다.
    """
    if _SENTENCE_END_PATTERN.search(chunk):
        return False
    return bool(_FORM_BLANK_PATTERN.search(chunk))


def _split_one_section(name: str, text: str) -> List[tuple[str, str]]:
    """구획 하나를 조항 단위로 쪼갠다. 반환: (구획명, 조항 텍스트) 목록.

    구획마다 규칙이 다르고, **본문 규칙은 손대지 않는다.** 본문에는 의도된
    비대칭이 있기 때문이다: 문서에 "제N조"가 문장 중간(법령 참조)에만 있으면
    조항 0건으로 떨어지고, "제N조"가 아예 없으면 통짜로 보존된다
    (test_parser_real_documents.py에 고정돼 있다). 부속문서를 살리려다 이
    규칙을 바꾸면 정상 문서의 파싱이 조용히 달라진다.
    """
    if name == "본문":
        # 본문 안의 "특약사항" 이하는 별도 구획으로 뗀다 (헤더 자체는 버린다)
        parts = re.split(r"(특약사항|특약\s*사항)", text, maxsplit=1)
        if len(parts) > 2:
            body = re.sub(r"[\[\]\s]+$", "", parts[0])
            special = re.sub(r"^[\[\]\s]+", "", parts[2])
            return (_split_one_section("본문", body)
                    + _split_one_section("특약사항", special))
        text = re.sub(r"[\[\]\s]+$", "", text)
        if not text.strip():
            return []
        # 기존 규칙 그대로 (변경 금지)
        has_articles = re.search(r"제\s*\d+\s*조", text) is not None
        body_parts = [p.strip() for p in _ARTICLE_PATTERN.split(text) if p.strip()]
        if has_articles:
            body_parts = [p for p in body_parts if _ARTICLE_PATTERN.match(p)]
        return [("본문", p) for p in body_parts]

    if not text.strip():
        return []

    if name == "특약사항":
        # 기존 규칙 그대로: 번호·불릿 목록 단위
        return [("특약사항", p) for p in _SPECIAL_ITEM_PATTERN.split(text) if p.strip()]

    # 부속문서(별지·별표·부록·부칙) — 형식이 제각각이라 단계적으로 시도한다.
    # 어느 패턴에도 안 걸리면 구획 전체를 조항 하나로 둔다. 쪼개지 못했다고
    # 버리면 수수료율표·위약금 기준을 통째로 놓치기 때문이다.
    if re.search(r"제\s*\d+\s*조", text):
        parts = [p.strip() for p in _ARTICLE_PATTERN.split(text) if p.strip()]
        parts = [p for p in parts if _ARTICLE_PATTERN.match(p)]
        if parts:
            return [(name, p) for p in parts]

    parts = [p.strip() for p in _SPECIAL_ITEM_PATTERN.split(text) if p.strip()]
    if len(parts) > 1:
        return [(name, p) for p in parts]

    return [(name, text.strip())]


def split_clauses(raw_text: str) -> List[Clause]:
    """원문 텍스트 -> 조항 리스트 (하위 호환 래퍼)."""
    clauses, _ = split_clauses_with_warnings(raw_text)
    return clauses


def split_clauses_with_warnings(raw_text: str) -> tuple[List[Clause], List[str]]:
    """원문 텍스트 -> (조항 리스트, 추출 경고 리스트)."""
    text, warnings = _truncate_boilerplate(raw_text.strip())
    text = _PAGE_NUMBER_PATTERN.sub("", text).strip()
    if not text:
        return [], warnings

    # 부속문서(별지·별표·부록·부칙)를 버리지 않고 구획으로 나눈다 (#174)
    chunks: List[tuple[str, str]] = []          # (구획명, 조항 텍스트)
    for section_name, section_text in _split_sections(text):
        chunks.extend(_split_one_section(section_name, section_text))

    annex_names = sorted({n for n, _ in chunks} - {"본문", "특약사항"})
    if annex_names:
        warnings.append(
            f"부속문서({', '.join(annex_names)})도 분석에 포함했습니다. "
            "수수료율·위약금 기준 같은 실질 조건이 부속문서에 들어가는 경우가 "
            "많아 함께 확인합니다."
        )

    # 양식 빈칸·안내 조각 제외 (조용한 누락 금지 원칙에 따라 경고로 알린다)
    kept = [(n, c) for n, c in chunks if not _is_form_artifact(c)]
    dropped = len(chunks) - len(kept)
    if dropped:
        logger.info("양식 빈칸·안내 조각 %d개 제외", dropped)
        warnings.append(
            f"계약서 양식의 빈칸·안내 문구로 보이는 {dropped}개 항목은 조항 "
            "분석에서 제외했습니다. 손으로 써 넣은 특약이 빠졌다면 그 부분만 "
            "따로 붙여넣어 다시 분석해 보세요."
        )
    chunks = kept

    clauses = [
        Clause(clause_id=f"clause_{i + 1:03d}", text=chunk, section=name)
        for i, (name, chunk) in enumerate(chunks)
    ]

    # 커버리지 점검: 분리된 조항이 (보일러플레이트 제거 후) 본문의 70% 미만이면
    # 형식 문제로 누락이 의심되는 상황 — 조용히 넘기지 않고 경고한다 (자문 §2).
    covered = sum(len(c["text"]) for c in clauses)
    if text and covered / len(text) < 0.7:
        warnings.append(
            "문서의 일부가 조항으로 분리되지 않았습니다 (형식이 표준 계약서와 "
            "다를 수 있습니다). 분석 결과에 빠진 조항이 없는지 원문과 대조해 "
            "확인하세요."
        )
    return clauses, warnings


def parser_node(state: PipelineState) -> dict:
    """LangGraph 노드: raw_text -> clauses, parse_warnings."""
    clauses, warnings = split_clauses_with_warnings(state["raw_text"])
    if warnings:
        logger.warning("추출 경고 %d건: %s", len(warnings), warnings)
    # 파이프라인 진입 시 이미 쌓인 경고(개인정보 마스킹 고지 등)를 보존한다 —
    # LangGraph는 반환 키를 병합이 아니라 교체하므로 여기서 이어 붙인다.
    return {"clauses": clauses, "parse_warnings": state.get("parse_warnings", []) + warnings}
