# agent — LangGraph 4단계 파이프라인

담당: 최민제

## 구조

```
agent/
├── main.py              # FastAPI 진입점 (백엔드가 호출)
├── demo.py              # 파이프라인 단독 실행 데모
├── src/
│   ├── state.py         # 상태 스키마 + 임계값/재시도 상수
│   ├── graph.py         # 그래프 조립 (재생성 루프 포함)
│   ├── nodes/
│   │   ├── parser.py    # 규칙 기반 조항 분리 (LLM 아님)
│   │   ├── analysis.py  # 4종 출력 생성 ← 현재 더미, LLM 교체 대상
│   │   ├── persona.py   # 페르소나 적응 ← 현재 더미, LLM 교체 대상
│   │   └── judge.py     # 4 Aspect 채점 ← 현재 더미, LLM 교체 대상
│   └── prompts/         # LLM 연동 시 사용할 프롬프트 (버전 관리 대상)
```

## 실행

```bash
cd agent
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 1) 파이프라인만 실행 (API 없이)
python demo.py

# 2) API 서버로 실행
uvicorn main:app --reload --port 8000
```

## API 키

```bash
cp .env.example .env   # 실제 키 입력. .env는 깃에 올라가지 않음
```

## 다음 작업 (LLM 연동)

각 노드 파일의 `_xxx_dummy` 함수를 실제 LLM 호출로 교체.
프롬프트는 코드에 하드코딩하지 말고 `src/prompts/*.txt`를 로드해서 사용
(프롬프트 수정 이력이 깃에 남아 실험 기록이 됨).

- [ ] 메인 LLM 확정 (담당: 민제) — 개발 Haiku 4.5 / Judge Sonnet 4.6 이원화로 운영하며 비용 데이터 수집, 중간보고서에 확정 근거 기재
- [ ] 사람-LLM 상관도 통계 분석 (담당: 민제) — Pearson r / Spearman ρ 계산 및 해석. 사람 평가 데이터 수집·진행은 민찬 담당 (Phase 2)
