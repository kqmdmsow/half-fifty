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
    # 제1~13조 + 특약(Ÿ 불릿) 1건. 나머지 Ÿ 항목 2건은 체크박스 빈칸만 있는
    # 양식 안내라 제외된다 (docs/eval_normal_fp.md clause_016 오탐 대응)
    ("contract_05_molit_standard.txt", 14),
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


def test_mid_sentence_article_reference_not_split():
    text = (DATA_DIR / "contract_05_molit_standard.txt").read_text(encoding="utf-8")
    clauses = split_clauses(text)
    clause_007 = next(c for c in clauses if c["text"].startswith("제7조"))
    assert "제4조 제1항을 위반한 경우 계약을 해지할 수 있다" in clause_007["text"]
    assert not any(c["text"].startswith("제4조 제1항") for c in clauses)


def test_byulji2_numbered_list_not_treated_as_clauses():
    text = (DATA_DIR / "contract_05_molit_standard.txt").read_text(encoding="utf-8")
    clauses = split_clauses(text)
    assert not any("임차인이 2기의" in c["text"] and c["text"].startswith("1.") for c in clauses)


def test_bracketed_header_leaves_no_residual_bracket():
    text = (DATA_DIR / "contract_05_molit_standard.txt").read_text(encoding="utf-8")
    clauses = split_clauses(text)
    assert not any(c["text"].endswith("[") or c["text"].endswith("]") for c in clauses)


def test_branch_article_heading_splits():
    # 중간보고서 버그: "제9조의2" 표제가 앞 조항에 병합되던 문제 (자문 §2)
    text = "제9조(수리비) 임차인이 부담한다.\n제9조의2(계약갱신 요구) 임차인은 갱신을 요구할 수 있다.\n제10조(반환) 보증금을 반환한다."
    clauses = split_clauses(text)
    assert len(clauses) == 3
    assert clauses[1]["text"].startswith("제9조의2")


def test_line_start_article_citation_with_josa_not_split():
    # "제6조의3에 따라"처럼 조사가 붙은 법령 인용은 줄 시작이어도 표제가 아니다
    text = "제1조(목적) 본 계약의 목적.\n제6조의3에 따라 갱신 요구권이 인정된다. 이하 내용."
    clauses = split_clauses(text)
    assert len(clauses) == 1  # 인용 줄은 제1조에 병합


def test_별지는_버리지_않고_구획으로_보존한다():
    """#174 — 예전에는 별지 이후를 통째로 버렸다.

    그런데 수수료율표·위약금 기준·추가 특약이 정확히 거기 들어간다. 위험이
    숨는 자리를 스스로 잘라내고 사용자에게 "따로 붙여넣으라"고 떠넘기고
    있었던 셈이라, 분석 대상에 포함하도록 바꿨다.
    """
    from src.nodes.parser import split_clauses_with_warnings
    text = "제1조(목적) 계약의 목적을 정한다.\n별지1)\n첨부 수수료율 표"
    clauses, warnings = split_clauses_with_warnings(text)
    assert len(clauses) == 2
    assert clauses[0]["section"] == "본문"
    assert clauses[1]["section"] == "별지1"
    assert "수수료율" in clauses[1]["text"]
    assert any("부속문서" in w for w in warnings)


def test_별표_부록_부칙도_각각_구획이_된다():
    from src.nodes.parser import split_clauses_with_warnings
    text = ("제1조(목적) 계약의 목적을 정한다.\n"
            "별표 2\n위약금은 계약금액의 30%로 한다.\n"
            "부칙\n제1조(시행일) 이 약관은 즉시 시행한다.")
    clauses, _ = split_clauses_with_warnings(text)
    sections = [c["section"] for c in clauses]
    assert "별표2" in sections and "부칙" in sections
    # 부속문서 안의 "제N조"도 조항 단위로 갈린다
    assert any("시행일" in c["text"] for c in clauses)


def test_문장_중간의_별지_참조는_구획_경계가_아니다():
    # "(별지1)을 확인하세요"처럼 본문에 섞인 참조로 문서가 쪼개지면 안 된다.
    from src.nodes.parser import split_clauses_with_warnings
    text = "제1조(목적) 자세한 내용은 별지1)을 확인하세요. 계약의 목적을 정한다."
    clauses, warnings = split_clauses_with_warnings(text)
    assert len(clauses) == 1
    assert clauses[0]["section"] == "본문"
    assert not any("부속문서" in w for w in warnings)


def test_normal_document_no_warnings():
    from src.nodes.parser import split_clauses_with_warnings
    text = "제1조(목적) 계약의 목적.\n제2조(기간) 계약 기간은 2년으로 한다."
    _, warnings = split_clauses_with_warnings(text)
    assert warnings == []


def test_low_coverage_produces_warning():
    from src.nodes.parser import split_clauses_with_warnings
    preamble = "표지 문구와 안내문이 아주 길게 이어진다. " * 30
    text = preamble + "\n제1조(목적) 짧은 조항."
    _, warnings = split_clauses_with_warnings(text)
    assert any("분리되지 않았습니다" in w for w in warnings)


def test_page_number_line_removed():
    # PDF 쪽번호가 조항 본문에 끼면 뒤따르는 표 조각까지 같은 조항으로 묶인다
    from src.nodes.parser import split_clauses_with_warnings
    text = "제5조(해제) 계약을 해제할 수 있다.\n- 1 / 4 -\n이어지는 본문이다."
    clauses, _ = split_clauses_with_warnings(text)
    assert len(clauses) == 1
    assert "1 / 4" not in clauses[0]["text"]


def test_bare_number_line_kept():
    # 숫자만 있는 줄은 표에서 떨어져 나온 금액·면적일 수 있어 지우지 않는다
    from src.nodes.parser import split_clauses_with_warnings
    text = "제1조(보증금) 보증금은 아래와 같다.\n50000000\n원정으로 한다."
    clauses, _ = split_clauses_with_warnings(text)
    assert "50000000" in clauses[0]["text"]


def test_form_blank_item_excluded_with_warning():
    # 체크박스 선택지만 있고 완결 문장이 없는 항목은 계약 문언이 아니다
    # (docs/eval_normal_fp.md housing_std clause_016 오탐의 직접 원인)
    from src.nodes.parser import split_clauses_with_warnings
    text = (
        "제1조(목적) 계약의 목적을 정한다.\n"
        "특약사항\n"
        "Ÿ 주택의 철거 또는 재건축에 관한 구체적 계획 ( □ 없음 □ 있음 ※공사시기 :\n"
    )
    clauses, warnings = split_clauses_with_warnings(text)
    assert len(clauses) == 1
    assert any("빈칸·안내" in w for w in warnings)


def test_handwritten_special_clause_kept():
    # 특약사항은 위험 조항이 숨는 자리다 — 완결 문장이 있으면 반드시 남긴다
    from src.nodes.parser import split_clauses_with_warnings
    text = (
        "제1조(목적) 계약의 목적을 정한다.\n"
        "특약사항\n"
        "1. 임대인은 보증금을 반환하지 않는다.\n"
    )
    clauses, warnings = split_clauses_with_warnings(text)
    assert len(clauses) == 2
    assert "보증금을 반환하지 않는다" in clauses[1]["text"]
    assert warnings == []


def test_form_item_with_checkbox_but_complete_sentence_kept():
    # 체크박스가 있어도 완결 문장이면 당사자가 합의하는 계약 항목이다
    # (housing_std clause_014 분쟁조정 동의 항목 — 제외하면 안 된다)
    from src.nodes.parser import split_clauses_with_warnings
    text = (
        "제1조(목적) 계약의 목적을 정한다.\n"
        "특약사항\n"
        "Ÿ 분쟁이 있는 경우 조정위원회에 조정을 신청한다 ( □ 동의 □ 미동의)\n"
    )
    clauses, _ = split_clauses_with_warnings(text)
    assert len(clauses) == 2
