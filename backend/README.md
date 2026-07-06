# backend — Spring Boot API 서버

담당: 전동훈

## 요구사항

- JDK 17
- IntelliJ IDEA (권장) 또는 Gradle

## 실행

IntelliJ에서 `backend` 폴더를 열면 Gradle 프로젝트로 자동 인식 →
`ApiApplication` 실행. 또는 터미널에서:

```bash
cd backend
gradle wrapper   # 최초 1회 (gradlew 생성)
./gradlew bootRun
```

## 현재 구현

- `POST /api/contracts/analyze` : 요청을 Python 에이전트(8000)로 전달하고 결과 반환
- 에이전트 주소는 `application.yml`의 `agent.base-url`

## 테스트

에이전트 서버(8000)가 켜진 상태에서:

```bash
curl -X POST http://localhost:8080/api/contracts/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "제1조 임차인은 보증금을 지급한다.", "persona": "adult"}'
```

## TODO

- [ ] JWT 인증 (spring-boot-starter-security)
- [ ] MySQL 연동: 계약 문서/분석 이력 저장 (JPA)
- [ ] 비동기 처리 (분석 장시간 소요 대비)
- [ ] Docker Compose 구성
- [ ] 보안/개인정보 대책 구현 (담당: 동훈) — 착수보고서 Ⅵ장 대책 반영
  - 업로드 계약서 파일은 분석 완료 후 자동 삭제
  - 서버 로그에 계약서 원문 미저장 (조항 ID와 메타데이터만 기록)
