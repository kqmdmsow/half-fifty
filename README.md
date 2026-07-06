# half-fifty

금융 취약계층을 위한 사용자 맞춤형 계약 문서 단순화 및 위험 안내 에이전트
(2026 전기 졸업과제 · 하프피프티)

## 구조

```
half-fifty/
├── agent/      # Python + LangGraph 4단계 파이프라인 (담당: 최민제)
├── backend/    # Java Spring Boot API 서버 (담당: 전동훈)
├── frontend/   # React + TypeScript + TailwindCSS (담당: 김민찬)
├── data/       # 평가용 데이터셋 (공정위 표준약관 등)
└── docs/       # 보고서, 회의록, 설계 문서
```

## 아키텍처

```
프론트(5173) → 백엔드(8080) → 에이전트(8000)
                                └─ Parser → Analysis → Persona → Judge
                                              ↑ 점수 미달 시 최대 2회 재실행 ┘
```

## 실행 순서 (각각 별도 터미널)

1. **에이전트** — `agent/README.md` 참고 (포트 8000)
2. **백엔드** — `backend/README.md` 참고 (포트 8080)
3. **프론트** — `frontend/README.md` 참고 (포트 5173)

브라우저에서 http://localhost:5173 접속 → 계약서 붙여넣기 → 분석하기.

## 브랜치 규칙

- `main` 직접 push 금지, 항상 동작하는 상태 유지
- 작업 브랜치: `feat/기능이름`, `fix/버그이름`
- Pull Request → 팀원 1명 이상 리뷰 후 merge

## 역할 분담

- **agent** (리드) — 최민제
- **backend** — 전동훈
- **frontend + 데이터셋 + 사람 평가** — 김민찬

각 파트 상세 TODO는 해당 폴더의 README(`agent/README.md`, `backend/README.md`, `frontend/README.md`) 참고.
