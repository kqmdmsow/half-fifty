"""Parser Module (규칙 기반, LLM 호출 없음).

계약서 원문을 조항 단위로 분리한다.
- "제N조", "제 N 조"가 줄 시작에 있을 때만 새 조항으로 분리 (문장 중간의
  "제4조 제1항을 위반한..." 같은 조 참조나 "제6조의3" 같은 법령 인용은 제외)
- "특약사항" 이하 목록("1." 및 "Ÿ"/"•"/"-"/"*" 불릿)도 개별 조항으로 취급
- 별지(첨부문서)와 서명란 이후 텍스트는 계약 조항이 아니므로 파싱 전에 버린다
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

# 별지(첨부문서) 헤더: 줄 전체가 "별지1)", "별지 2" 등으로만 이루어진 경우.
# 본문 중 "(별지1)을 확인하세요"처럼 문장에 섞인 참조는 매칭하지 않는다.
_BYULJI_HEADER_PATTERN = re.compile(r"^[ \t]*별지\s*\d+\s*\)?[ \t]*$", re.MULTILINE)

# 서명란 시작을 알리는 문구. 이 뒤로는 서명/날인 표 등 조항이 아닌 내용이다.
_SIGNATURE_BLOCK_MARKER = "본 계약을 증명하기 위하여"


def _truncate_boilerplate(text: str) -> tuple[str, List[str]]:
    """별지 첨부문서, 서명란 등 계약 조항이 아닌 꼬리 텍스트를 잘라낸다.

    자문 §2("추출 실패나 누락 가능성을 사용자에게 알리는지") 반영: 무엇을
    제외했는지 경고로 수집해 사용자에게 노출한다 — 조용한 누락 금지.
    """
    cut_points = []
    warnings: List[str] = []

    byulji_match = _BYULJI_HEADER_PATTERN.search(text)
    if byulji_match:
        cut_points.append(byulji_match.start())
        warnings.append(
            "별지(첨부 문서) 이후 내용은 조항 분석에서 제외했습니다. "
            "별지에 수수료율·특약 등 중요한 내용이 있다면 해당 부분만 "
            "따로 붙여넣어 다시 분석해 보세요."
        )

    sig_idx = text.find(_SIGNATURE_BLOCK_MARKER)
    if sig_idx != -1:
        cut_points.append(sig_idx)

    if cut_points:
        text = text[: min(cut_points)]

    return text, warnings


def split_clauses(raw_text: str) -> List[Clause]:
    """원문 텍스트 -> 조항 리스트 (하위 호환 래퍼)."""
    clauses, _ = split_clauses_with_warnings(raw_text)
    return clauses


def split_clauses_with_warnings(raw_text: str) -> tuple[List[Clause], List[str]]:
    """원문 텍스트 -> (조항 리스트, 추출 경고 리스트)."""
    text, warnings = _truncate_boilerplate(raw_text.strip())
    text = text.strip()
    if not text:
        return [], warnings

    # 1) 특약사항 앞뒤로 분리 (헤더 자체는 버리고 그 뒤 내용만 취한다)
    special_split = re.split(r"(특약사항|특약\s*사항)", text, maxsplit=1)
    body = special_split[0]
    special = special_split[2] if len(special_split) > 2 else ""
    # "[특약사항]"처럼 대괄호로 감싼 헤더의 괄호 잔여물 제거
    # (여는 괄호는 본문 끝에, 닫는 괄호는 특약 텍스트 앞에 남는다)
    body = re.sub(r"[\[\]\s]+$", "", body)
    special = re.sub(r"^[\[\]\s]+", "", special)

    chunks: List[str] = []

    # 2) 본문: 제N조 단위 분리 (조항 패턴이 있다면, 첫 조항 앞의 제목/전문은 버린다)
    has_articles = re.search(r"제\s*\d+\s*조", body) is not None
    body_parts = [p.strip() for p in _ARTICLE_PATTERN.split(body) if p.strip()]
    if has_articles:
        body_parts = [p for p in body_parts if _ARTICLE_PATTERN.match(p)]
    chunks.extend(body_parts)

    # 3) 특약: 번호/불릿 목록 단위 분리
    if special:
        special_parts = [p.strip() for p in _SPECIAL_ITEM_PATTERN.split(special) if p.strip()]
        chunks.extend(special_parts)

    clauses = [
        Clause(clause_id=f"clause_{i + 1:03d}", text=chunk)
        for i, chunk in enumerate(chunks)
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
