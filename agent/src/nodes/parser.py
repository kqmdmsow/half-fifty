"""Parser Module (규칙 기반, LLM 호출 없음).

계약서 원문을 조항 단위로 분리한다.
- "제N조", "제 N 조" 패턴을 기준으로 분리
- "특약사항" 이하 번호 목록(1., 2., ...)도 개별 조항으로 취급
표준계약서(공정위 표준약관)는 형식이 규칙적이므로 규칙 기반으로 충분하다.
"""

import re
from typing import List

from src.state import Clause, PipelineState

# "제1조", "제 1 조", "제1조(목적)" 등을 잡는 패턴
_ARTICLE_PATTERN = re.compile(r"(?=제\s*\d+\s*조)")
# 특약사항 구간의 "1.", "2." 목록 패턴
_NUMBERED_PATTERN = re.compile(r"(?=^\s*\d+\.\s)", re.MULTILINE)


def split_clauses(raw_text: str) -> List[Clause]:
    """원문 텍스트 -> 조항 리스트."""
    text = raw_text.strip()
    if not text:
        return []

    # 1) 특약사항 앞뒤로 분리
    special_split = re.split(r"(특약사항|특약\s*사항)", text, maxsplit=1)
    body = special_split[0]
    special = "".join(special_split[1:]) if len(special_split) > 1 else ""

    chunks: List[str] = []

    # 2) 본문: 제N조 단위 분리
    body_parts = [p.strip() for p in _ARTICLE_PATTERN.split(body) if p.strip()]
    chunks.extend(body_parts)

    # 3) 특약: 번호 목록 단위 분리
    if special:
        special_parts = [p.strip() for p in _NUMBERED_PATTERN.split(special) if p.strip()]
        chunks.extend(special_parts)

    return [
        Clause(clause_id=f"clause_{i + 1:03d}", text=chunk)
        for i, chunk in enumerate(chunks)
    ]


def parser_node(state: PipelineState) -> dict:
    """LangGraph 노드: raw_text -> clauses."""
    clauses = split_clauses(state["raw_text"])
    return {"clauses": clauses}
