# frontend — React + TypeScript + TailwindCSS

담당: 김민찬

## 요구사항

- Node.js 20 이상 (`brew install node`)

## 실행

```bash
cd frontend
npm install
npm run dev
```

http://localhost:5173 접속. 백엔드(8080)와 에이전트(8000)가 켜져 있어야
분석 버튼이 동작한다.

## 현재 구현

- 계약서 텍스트 입력 + 페르소나 선택(일반 성인/고령층)
- 조항별 결과 카드: 위험도 배지, 쉬운 설명, 근거, 확인 질문
- 재생성 횟수 / "주의 필요" 플래그 표시

## TODO

- [ ] PDF 업로드 (텍스트 추출 가능한 PDF)
- [ ] Judge 점수 시각화
- [ ] 분석 이력 페이지 (백엔드 DB 연동 후)
