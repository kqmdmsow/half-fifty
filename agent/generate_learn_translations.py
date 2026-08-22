"""교육 콘텐츠 정적 번역본 생성 (#104 — 콘텐츠 다국어화).

전략: 런타임 LLM 번역(지연·비용·환각 위험) 대신, 워커 LLM으로 **한 번**
번역해 src/learn_translations.json으로 커밋한다. /learn?language=xx가
이 파일을 서빙 — 첫 화면 지연 0, 내용이 리뷰 가능한 산출물로 남는다.
콘텐츠가 바뀌면 이 스크립트를 다시 실행해 재생성한다.

번역 대상: RISK_TYPE_GUIDE(what/signals/tip) + SCAMS(what/signal/outside/case)
+ 각주 사례 요약(result). 유형명(title)은 프론트가 riskTypeLabel로 이미
현지화하므로 여기서는 참고용으로만 함께 번역한다. 기관명·사건번호는
원문 유지 관례라 번역하지 않는다.

사용법: cd agent && python generate_learn_translations.py [lang ...]
        (인자 없으면 ko 제외 15개 언어 전부)
"""

import json
import sys
from pathlib import Path

from src.learn_content import RISK_TYPE_GUIDE, SCAMS
from src.case_footnotes import _TABLE
from src.llm import invoke_json

LANGS = ["en", "zh", "vi", "th", "id", "tl", "ne", "km", "my", "mn", "uz", "si", "bn", "ru", "ja"]
OUT = Path(__file__).parent / "src" / "learn_translations.json"

LANG_NAMES = {
    "en": "English", "zh": "Simplified Chinese", "vi": "Vietnamese", "th": "Thai",
    "id": "Indonesian", "tl": "Tagalog", "ne": "Nepali", "km": "Khmer", "my": "Burmese",
    "mn": "Mongolian", "uz": "Uzbek", "si": "Sinhala", "bn": "Bengali", "ru": "Russian",
    "ja": "Japanese",
}


def _source() -> dict:
    cases = {}
    for cs in _TABLE.values():
        for c in cs:
            cases[c["case_id"]] = c["result"]
    return {
        "risk_types": [{"id": g["id"], "title": g["title"], "what": g["what"],
                        "signals": g["signals"], "tip": g["tip"]} for g in RISK_TYPE_GUIDE],
        "scams": [{"id": s["id"], "title": s["title"], "what": s["what"],
                   "signal": s["signal"], "outside": s["outside"], "case": s["case"]} for s in SCAMS],
        "cases": cases,
    }


PROMPT = """다음은 한국 계약서 위험 교육 콘텐츠의 JSON입니다. 모든 문자열 값을 {lang_name}로 번역해 **동일한 구조의 JSON만** 출력하세요.

규칙:
- "id" 값은 번역하지 말고 그대로 유지.
- 배열 길이·키 구조를 절대 바꾸지 마세요.
- 법률 용어는 일반인이 이해할 수 있는 쉬운 표현으로.
- 한국 제도 고유명사(전세/jeonse, 임차권등기명령, HUG 등)는 음차 후 필요하면 짧은 부연.
- 금액·법조문 번호·사건번호·기관명은 원문 그대로.
- JSON 외 다른 텍스트 금지.

{payload}"""


def main():
    langs = sys.argv[1:] or LANGS
    src = _source()
    out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    # 긴 문자 체계 언어(크메르·미얀마 등)는 전체 페이로드가 워커 기본
    # 타임아웃(90초)을 넘겨 실측 실패 — 페이로드를 둘로 나누고 타임아웃 5분.
    from langchain_anthropic import ChatAnthropic
    import os as _os
    llm = ChatAnthropic(model=_os.getenv("MODEL_WORKER", "claude-haiku-4-5"),
                        temperature=0, timeout=300, max_tokens=16384)
    half1 = json.dumps({"risk_types": src["risk_types"], "cases": src["cases"]}, ensure_ascii=False)
    half2 = json.dumps({"scams": src["scams"]}, ensure_ascii=False)
    for lang in langs:
        print(f"[{lang}] 번역 중...", flush=True)
        d1 = invoke_json(llm, PROMPT.format(lang_name=LANG_NAMES[lang], payload=half1))
        d2 = invoke_json(llm, PROMPT.format(lang_name=LANG_NAMES[lang], payload=half2))
        data = {**d1, **d2}
        # 구조 검증 — 실패 시 해당 언어는 저장하지 않음(서빙은 ko 폴백)
        assert len(data["risk_types"]) == len(src["risk_types"]), f"{lang} risk_types 수 불일치"
        assert len(data["scams"]) == len(src["scams"]), f"{lang} scams 수 불일치"
        assert set(data["cases"].keys()) == set(src["cases"].keys()), f"{lang} cases 키 불일치"
        for a, b in zip(data["risk_types"], src["risk_types"]):
            assert a["id"] == b["id"] and len(a["signals"]) == len(b["signals"]), f"{lang} {b['id']} 구조 불일치"
        out[lang] = data
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[{lang}] 저장 완료")
    print(f"총 {len(out)}개 언어 → {OUT}")


if __name__ == "__main__":
    main()
