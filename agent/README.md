# agent — LangGraph 4단계 파이프라인

담당: 최민제

LLM 연동 완료 상태. Parser는 규칙 기반, Analysis/Persona/Judge는 실제
Claude API를 호출한다. 모델은 이원화되어 있다: Analysis/Persona는
`MODEL_WORKER`(기본 Haiku, 저렴한 생성용), Judge는 `MODEL_JUDGE`(기본
Sonnet, 채점 정확도용)를 사용한다.

## 구조

```
agent/
├── main.py              # FastAPI 진입점 (백엔드가 호출)
├── demo.py              # 파이프라인 단독 실행 데모
├── eval.py              # data/ 계약서 5건 자동 평가 (리콜/오탐/시간/토큰)
├── src/
│   ├── state.py         # 상태 스키마 + 임계값(JUDGE_THRESHOLD)/재시도(MAX_RETRIES) 상수
│   ├── graph.py          # 그래프 조립 (재생성 루프 포함, 재시도/판정 로그 출력)
│   ├── llm.py            # LLM 클라이언트 생성 + JSON 파싱 + 토큰 사용량 추적 공통 유틸
│   ├── nodes/
│   │   ├── parser.py    # 규칙 기반 조항 분리 (LLM 아님, 줄 시작 앤커링 + 별지/서명란 컷오프)
│   │   ├── analysis.py  # 4종 출력 생성 (analysis.txt 프롬프트, MODEL_WORKER)
│   │   ├── persona.py   # 페르소나 적응 (persona_*.txt 프롬프트, MODEL_WORKER)
│   │   └── judge.py     # 4 Aspect 채점 (judge_rubric.txt 프롬프트, MODEL_JUDGE)
│   └── prompts/         # 실제 사용 중인 프롬프트 (버전 관리 대상)
└── tests/
    └── test_parser.py   # Parser 단위 테스트 (pytest)
```

## 실행

```bash
cd agent
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 1) 파이프라인만 실행 (샘플 계약서 1건)
python demo.py

# 2) data/ 계약서 5건 전체 자동 평가 (리콜/오탐/실행시간/토큰 -> docs/eval_results_v2.md)
python eval.py

# 3) 단위 테스트
pytest tests/ -v

# 4) API 서버로 실행
uvicorn main:app --reload --port 8000
```

## API 키 / 모델 설정

```bash
cp .env.example .env   # 실제 키 입력. .env는 깃에 올라가지 않음
```

`.env`에 `ANTHROPIC_API_KEY` 외에 `MODEL_WORKER`, `MODEL_JUDGE`를 지정할 수
있다 (미지정 시 각각 `claude-haiku-4-5`, `claude-sonnet-4-6` 기본값 사용).

## 재생성 루프

`JUDGE_THRESHOLD`(기본 3.5) 미만이면 Analysis부터 최대 `MAX_RETRIES`(기본
2)회까지 재실행하고, 그래도 미달이면 `needs_review=True` 플래그와 함께
반환한다. 콘솔에 매 Judge 호출마다 4 Aspect 점수/근거와 재시도 여부가
로그로 남는다.

## 다음 작업

- [ ] 사람-LLM 상관도 통계 분석 (담당: 민제) — Pearson r / Spearman ρ 계산 및 해석. 사람 평가 데이터 수집·진행은 민찬 담당 (Phase 2)
- [ ] eval.py의 리콜을 조항 단위 정답 매칭으로 정교화 (현재는 문서별 위험 건수 대 정답 건수 근사치)
