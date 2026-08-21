"""교육 콘텐츠 다국어 서빙 (#104) — 번역본 구조·폴백 계약 테스트."""

from src.learn_content import RISK_TYPE_GUIDE, SCAMS, _TRANSLATIONS, localized_learn


def test_한국어는_원문_그대로():
    d = localized_learn("ko")
    assert d["content_language"] == "ko"
    assert d["risk_types"][0]["what"] == RISK_TYPE_GUIDE[0]["what"]


def test_번역_없는_언어는_ko_폴백():
    d = localized_learn("xx")
    assert d["content_language"] == "ko"
    assert len(d["risk_types"]) == len(RISK_TYPE_GUIDE)


def test_번역본_구조가_원문과_일치():
    # 커밋된 번역 파일의 언어들은 유형 수·id·signals 길이가 원문과 같아야 한다
    for lang, tr in _TRANSLATIONS.items():
        assert len(tr["risk_types"]) == len(RISK_TYPE_GUIDE), lang
        for a, b in zip(tr["risk_types"], RISK_TYPE_GUIDE):
            assert a["id"] == b["id"], lang
            assert len(a["signals"]) == len(b["signals"]), (lang, b["id"])
        assert len(tr["scams"]) == len(SCAMS), lang


def test_번역_언어는_본문이_교체되고_사례_기관명은_유지():
    if "en" not in _TRANSLATIONS:  # 생성 전이면 스킵과 동일 (폴백 테스트가 커버)
        return
    d = localized_learn("en")
    assert d["content_language"] == "en"
    assert d["risk_types"][0]["what"] != RISK_TYPE_GUIDE[0]["what"]
    with_cases = next(rt for rt in d["risk_types"] if rt["cases"])
    assert "조정" in with_cases["cases"][0]["agency"]  # 기관명은 원문 유지
