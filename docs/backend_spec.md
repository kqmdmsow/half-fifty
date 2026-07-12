# 백엔드 기능 명세서

> 하프피프티 · Spring Boot API 서버 (포트 8080)
> 담당: 전동훈 · 스택: Java 17 + Spring Boot + Gradle (+ MySQL, JPA)

---

## 1. 백엔드의 역할과 데이터 흐름

백엔드는 **직접 데이터를 만들지 않는다.** 데이터 원천은 두 곳뿐이다.

| 데이터 | 어디서 오나 | 백엔드가 하는 일 |
| --- | --- | --- |
| 계약서 원문 (텍스트/PDF) | **프론트 사용자 입력** | 검증 후 에이전트로 전달, 저장하지 않음(개인정보) |
| 분석 결과 (조항별 위험 판정) | **에이전트(FastAPI, 8000)** 응답 | 프론트로 반환 + (선택) DB에 이력 저장 |
| 평가용 계약서 데이터 | `data/` 폴더 (공정위 표준약관·분쟁조정 사례) | 백엔드와 무관 — 에이전트 평가(eval.py)용 |

```
프론트(5173) ──HTTP──> 백엔드(8080) ──HTTP──> 에이전트(8000) ──> Claude API
                          │
                          └──> MySQL (분석 이력, 24시간 보관)
```

즉 백엔드는 ① 관문(검증·에러 표준화·타임아웃) ② 프록시(에이전트 중계) ③ 저장소(이력 저장/삭제) 세 가지 책임만 가진다. 외부 API나 크롤링 데이터는 없다.

---

## 2. 현재 상태

| 항목 | 상태 |
| --- | --- |
| `POST /api/contracts/analyze` (텍스트) | ✅ 구현됨 (단순 중계만) |
| PDF 분석 중계 | ❌ 없음 — 프론트가 에이전트 8000을 직접 호출 중 (아키텍처 위반) |
| 타임아웃/재시도 | ❌ RestClient 기본값 (분석 수십 초 → 터짐) |
| 에러 표준화 | ❌ 에이전트 5xx가 그대로 500으로 노출 |
| 입력 검증 | ❌ 없음 |
| DB / 이력 | ❌ 없음 |
| CORS | ⚠️ 컨트롤러에 하드코딩 |
| 테스트 | ❌ 없음 |

---

## 3. API 명세 (전체)

### 3-1. `POST /api/contracts/analyze` — 텍스트 분석 ✅보강

| 항목 | 내용 |
| --- | --- |
| 요청 | `{ "text": string, "persona": "adult" \| "senior" }` |
| 검증 | text: 필수, 30자 이상 30,000자 이하 · persona: enum |
| 처리 | 에이전트 `POST /analyze` 중계 (타임아웃 120s) → (선택) 이력 저장 |
| 응답 200 | `{ "analysisId": string, "clause_count": int, "retry_count": int, "needs_review": bool, "judge_scores": object, "results": ClauseResult[] }` |

`ClauseResult`: `clause_id`, `original_text`, `explanation`, `risk_level(안전|주의|위험)`, `risk_type`, `risk_evidence`, `check_questions[]`

### 3-2. `POST /api/contracts/analyze-pdf` — PDF 분석 🔥신규·최우선

| 항목 | 내용 |
| --- | --- |
| 요청 | `multipart/form-data`: `file`(PDF), `persona` |
| 검증 | MIME `application/pdf` + 매직바이트(`%PDF`) 확인, 최대 10MB (`spring.servlet.multipart.max-file-size`) |
| 처리 | 에이전트 `POST /analyze-pdf`로 multipart 그대로 중계. **파일을 디스크에 저장하지 않는다** (메모리/스트림 처리) |
| 응답 | 3-1과 동일 |
| 완료 조건 | 프론트 `api.ts`에서 `AGENT_BASE_URL` 직접 호출 제거 가능해짐 |

### 3-3. `GET /api/contracts/{analysisId}` — 분석 결과 조회 (P1)

이력 저장을 구현할 때만. 24시간 내 재조회용. 만료·미존재 시 404.

### 3-4. `DELETE /api/contracts/{analysisId}` — 즉시 삭제 (P1)

프론트 "지금 모두 삭제" 버튼과 연결. 결과·원문 관련 데이터 하드 삭제 후 204.

### 3-5. `GET /api/health` — 헬스체크 (P2)

`spring-boot-starter-actuator` 사용. 에이전트 연결 상태 포함하면 시연 때 유용.

### 3-6. 인증 (JWT) — ⚠️ 스코프 판단

회원 개념이 없는 서비스라 **데모 범위에서는 생략 권장**. 넣는다면 익명 세션 토큰(분석 결과 소유 증명용) 정도로 축소.

---

## 4. 에러 응답 표준 (`@RestControllerAdvice`)

공통 포맷:

```json
{ "code": "SCANNED_PDF", "message": "텍스트 추출이 안 되는 PDF예요.", "status": 422 }
```

| 상태 | code | 상황 |
| --- | --- | --- |
| 400 | `INVALID_INPUT` | 검증 실패 (text 길이, persona 등) |
| 413 | `FILE_TOO_LARGE` | 10MB 초과 |
| 415 | `UNSUPPORTED_FILE` | PDF 아님 |
| 422 | `SCANNED_PDF` | 에이전트 422 (텍스트 추출 불가) |
| 404 | `NOT_FOUND` | 만료/미존재 분석 ID |
| 502 | `AGENT_ERROR` | 에이전트 5xx/연결 실패 |
| 504 | `AGENT_TIMEOUT` | 분석 타임아웃 |

에이전트의 상태코드를 백엔드 코드로 매핑해서 프론트가 **백엔드 포맷 하나만** 알면 되게 한다.

---

## 5. DB 설계 (P1 — 이력 저장 시)

원문은 저장하지 않는 게 원칙("분석 후 즉시 삭제" 약속). 결과만 저장.

```
analysis (분석 이력)
├── id            VARCHAR(36) PK (UUID)
├── persona       VARCHAR(10)
├── clause_count  INT
├── retry_count   INT
├── needs_review  BOOLEAN
├── judge_scores  JSON
├── created_at    DATETIME
└── expires_at    DATETIME  -- created_at + 24h

clause_result (조항 결과)
├── id              BIGINT PK AUTO_INCREMENT
├── analysis_id     VARCHAR(36) FK → analysis.id (ON DELETE CASCADE)
├── clause_id       VARCHAR(50)
├── original_text   TEXT
├── explanation     TEXT
├── risk_level      VARCHAR(10)
├── risk_type       VARCHAR(50)
├── risk_evidence   TEXT
└── check_questions JSON
```

- 자동 삭제: `@Scheduled(cron = "0 */10 * * * *")` 로 `expires_at < now()` 삭제 → "24시간 보관" 약속 이행
- 시연만 목표면 MySQL 대신 H2(인메모리)로 대체 가능

---

## 6. 비기능 요구사항 (백엔드 정석 체크리스트)

- [ ] **타임아웃**: RestClient connect 5s / read 120s 명시 설정
- [ ] **CORS 분리**: `WebMvcConfigurer` 전역 설정 + 허용 origin을 `application.yml` 프로퍼티로
- [ ] **검증**: `spring-boot-starter-validation`, DTO에 `@Valid` + `@NotBlank`/`@Size`/`@Pattern`
- [ ] **환경 분리**: `application-local.yml` / `application-prod.yml`, 에이전트 URL·CORS origin 프로퍼티화
- [ ] **로깅**: 요청 단위 분석 소요시간·에이전트 응답코드 로그 (개인정보인 원문은 로그 금지)
- [ ] **개인정보**: 계약서 원문 미저장·미로깅, multipart 임시파일 즉시 정리
- [ ] **테스트**: ① 컨트롤러 슬라이스 테스트(`@WebMvcTest` + AgentClient 모킹) — 검증/에러 매핑 위주 ② 에이전트 장애 시나리오(타임아웃, 5xx)
- [ ] **API 문서**: springdoc-openapi로 Swagger UI 자동 생성 (`/swagger-ui.html`) — 보고서 첨부용
- [ ] **비동기 처리**: 분석이 2분 넘게 걸리면 작업 큐 + 폴링 구조 필요하나, 현재 소요시간 기준 **동기 유지 권장** (범위 축소)

---

## 7. 작업 우선순위

| 순위 | 작업 | 이유 |
| --- | --- | --- |
| **P0** | `analyze-pdf` 프록시 + 타임아웃 + `@RestControllerAdvice` 에러 표준화 + CORS 분리 + 검증 | 아키텍처 완성 + E2E 통합의 전제 |
| **P1** | 이력 저장(H2/MySQL) + 조회/삭제 API + 24h 자동 삭제 스케줄러 | 프론트 "결과 삭제" 기능 실배선, 차별점 |
| **P2** | 헬스체크, Swagger, 테스트 보강, docker-compose | 시연 안정성 + 보고서 |

P0가 끝나면 곧바로 프론트·에이전트와 E2E 통합 테스트(성공 + 422/415/타임아웃 실패 케이스)를 진행한다.
