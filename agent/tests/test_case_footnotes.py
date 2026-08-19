"""실제 사건 각주 조회 테스트 (#91). LLM 호출 없는 순수 dict 조회."""

from src.case_footnotes import get_related_cases
from src.schemas import RISK_TYPES


def test_알려진_유형은_사례_목록_반환():
    cases = get_related_cases("책임 면제")
    assert len(cases) >= 1
    for c in cases:
        assert c["grade"] == "A"
        assert c["agency"]
        assert c["result"]


def test_미커버_유형은_빈_리스트():
    """v1은 신탁관계·소유권 불안정 고지를 커버하지 않는다(#91 — 검증 가능한
    사건번호 출처가 골든셋에 없어 일부러 비워둠). 틀린 사건번호보다
    빈 목록이 낫다는 원칙을 여기서 고정한다."""
    assert get_related_cases("신탁관계·소유권 불안정 고지") == []


def test_해당없음은_빈_리스트():
    assert get_related_cases("해당 없음") == []


def test_모든_risk_type이_스키마와_어긋나지_않음():
    """큐레이션 테이블의 키가 RISK_TYPES(schemas.py)에 없는 오타면 그 유형은
    영원히 조회되지 않는다 — API 없이 드리프트를 잡는다."""
    import json
    from pathlib import Path

    table = json.loads(
        (Path(__file__).parent.parent.parent / "data" / "case_footnotes.json")
        .read_text(encoding="utf-8")
    )
    for key in table:
        if key == "_readme":
            continue
        assert key in RISK_TYPES, f"'{key}'가 RISK_TYPES에 없음 — 오타 의심"
