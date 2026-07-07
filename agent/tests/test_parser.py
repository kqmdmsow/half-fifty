"""Parser Module 단위 테스트."""

from pathlib import Path

import pytest

from src.nodes.parser import split_clauses

DATA_DIR = Path(__file__).parent.parent.parent / "data"

# (파일명, 기대 조항 수) — data/labels.md 기준
CONTRACT_CLAUSE_COUNTS = [
    ("sample_lease_contract.txt", 5),  # 제1~3조 + 특약 2건
    ("contract_02_finance_loan.txt", 7),  # 제1~5조 + 특약 2건
    ("contract_03_lease_normal.txt", 7),  # 제1~7조, 특약 없음
    ("contract_04_gym_membership.txt", 7),  # 제1~5조 + 특약 2건
]


@pytest.mark.parametrize("filename,expected_count", CONTRACT_CLAUSE_COUNTS)
def test_contract_clause_count(filename, expected_count):
    text = (DATA_DIR / filename).read_text(encoding="utf-8")
    clauses = split_clauses(text)
    assert len(clauses) == expected_count


def test_teuyak_header_not_a_clause():
    text = (DATA_DIR / "sample_lease_contract.txt").read_text(encoding="utf-8")
    clauses = split_clauses(text)
    assert all(c["text"] != "특약사항" for c in clauses)


def test_title_line_before_first_article_not_a_clause():
    text = (DATA_DIR / "contract_02_finance_loan.txt").read_text(encoding="utf-8")
    clauses = split_clauses(text)
    assert all(c["text"] != "금전소비대차 계약서" for c in clauses)


def test_article_pattern_with_spaces():
    clauses = split_clauses("제 1 조(목적) 가나다.\n\n제2조(내용) 라마바.")
    assert len(clauses) == 2


def test_plain_text_without_articles_becomes_single_clause():
    clauses = split_clauses("이것은 그냥 아무 조항 표시 없는 일반 텍스트입니다.")
    assert len(clauses) == 1


def test_multiple_blank_lines_between_articles():
    clauses = split_clauses("제1조 가나다.\n\n\n\n\n제2조 라마바.")
    assert len(clauses) == 2


def test_empty_input_returns_empty_list():
    assert split_clauses("") == []
    assert split_clauses("   ") == []
