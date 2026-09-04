---
version: alpha
name: 조목조목 (half-fifty)
description: 금융·계약 안심 도우미 — KRDS(대한민국 정부 디자인시스템) 토큰 기반 시각 언어
colors:
  # 실값의 단일 출처는 src/index.css의 CSS 변수(KRDS 출처 토큰명 주석 포함).
  # 여기서는 라이트 모드 기준 hex를 병기한다 — 고대비 모드는 변수 스왑으로 전환된다.
  primary: "#0b50d0" # = brand-500 별칭 (에이전트 키 컬러 자동 생성 방지)
  on-primary: "#ffffff"
  white: "#ffffff"
  ink-900: "#131416"
  ink-700: "#1e2124"
  ink-600: "#33363d"
  ink-400: "#464c53"
  ink-300: "#58616a"
  ink-200: "#cdd1d5"
  ink-100: "#e6e8ea"
  ink-50: "#f4f5f6"
  ink-25: "#f4f5f6"
  brand-50: "#ecf2fe"
  brand-100: "#d8e5fd"
  brand-500: "#0b50d0"
  brand-600: "#083891"
  brand-700: "#052561"
  danger-50: "#fdefec"
  danger-500: "#de3412"
  danger-600: "#bd2c0f"
  caution-50: "#fff3db"
  caution-500: "#9e6a00"
  caution-700: "#8a5c00"
  safe-50: "#eaf6ec"
  safe-500: "#228738"
  safe-700: "#267337"
typography:
  h1:
    fontFamily: Pretendard GOV
    fontSize: 26px
    fontWeight: 700
    letterSpacing: -0.02em
  h1-desktop:
    fontFamily: Pretendard GOV
    fontSize: 30px
    fontWeight: 700
    letterSpacing: -0.02em
  h2:
    fontFamily: Pretendard GOV
    fontSize: 24px
    fontWeight: 700
    letterSpacing: -0.02em
  section-label:
    fontFamily: Pretendard GOV
    fontSize: 14px
    fontWeight: 700
  card-title:
    fontFamily: Pretendard GOV
    fontSize: 14px
    fontWeight: 700
  body:
    fontFamily: Pretendard GOV
    fontSize: 15px
    lineHeight: 2
  body-sm:
    fontFamily: Pretendard GOV
    fontSize: 14px
    lineHeight: 1.625
  caption:
    fontFamily: Pretendard GOV
    fontSize: 13px
  micro:
    fontFamily: Pretendard GOV
    fontSize: 12px
rounded:
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
spacing:
  xs: 8px
  sm: 12px
  md: 16px
  lg: 20px
  xl: 24px
components:
  card:
    backgroundColor: "{colors.white}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  card-item:
    backgroundColor: "{colors.white}"
    rounded: "{rounded.lg}"
    padding: 16px 20px
  card-well:
    backgroundColor: "{colors.ink-25}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  card-alert:
    backgroundColor: "{colors.danger-50}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  card-nested:
    backgroundColor: "{colors.ink-25}"
    rounded: "{rounded.md}"
    padding: 12px 16px
  card-elevated:
    backgroundColor: "{colors.white}"
    rounded: "{rounded.xl}"
    padding: "{spacing.xl}"
  button-primary:
    backgroundColor: "{colors.brand-500}"
    textColor: "{colors.white}"
    rounded: "{rounded.lg}"
    height: 48px
  badge:
    rounded: "{rounded.sm}"
    padding: 4px 10px
---

## Overview

조목조목은 계약서의 위험을 외국인·고령층도 이해할 수 있게 풀어 주는 공공 성격의
서비스다. 시각 언어의 뿌리는 **KRDS(대한민국 정부 디자인시스템)**이고, 실제 색·치수
토큰은 `src/index.css`에 KRDS 출처 토큰명 주석과 함께 이식되어 있다. 이 문서는 그
토큰을 "어떻게 조합해야 하는가"를 정한다 — 값의 단일 출처는 여전히 `index.css`다.

인상 목표: 관공서의 신뢰감 + 민간 서비스의 친절함. 흰 바탕에 잉크 텍스트,
파랑(brand)은 행동 유도에만, 빨강·노랑·초록은 위험도 의미에만 쓴다.

## Colors

- **ink 계열**: 본문과 구조. `ink-900` 제목, `ink-700` 본문, `ink-600` 보조 본문,
  `ink-400` 섹션 라벨·캡션, `ink-100` 테두리, `ink-25` 면(well) 배경.
- **brand (#0b50d0)**: 클릭할 수 있는 것에만. 링크·주 버튼·재설명 칩. 장식 금지.
- **danger / caution / safe**: 위험도 의미 전용. 색만으로 구분하지 않고 항상
  아이콘+텍스트를 병기한다(KRDS 접근성 원칙, ui.tsx RiskBadge의 3중 인코딩).
- 모든 텍스트/배경 조합은 WCAG AA(4.5:1)를 지켜 토큰을 선정했다 — 선정 근거는
  `index.css` 주석 참조. 임의 hex를 새로 만들지 않는다.

## Typography

Pretendard GOV 단일 서체. 크기 단계는 12·13·14·15·16·24·26(30)px로 제한한다.

- 페이지 제목 `h1`(26→md:30px), 조항 제목 `h2`(24→md:28px).
- **섹션 라벨은 한 가지뿐이다**: 14px bold `ink-400` (`section-label`).
  "쉽게 설명하면", "계약 상대방에게 물어보세요" 등 화면의 모든 섹션 제목이
  같은 스타일을 쓴다 — 크기·색을 달리해 위계를 임의로 만들지 않는다.
- 카드 안의 제목(`card-title`)은 14px bold `ink-900`.
- 읽기 본문은 15px `leading-loose`, 보조 본문은 14px `leading-relaxed`.

## Layout

- 콘텐츠 폭: 페이지 `max-w-5xl`, 단일 포커스 화면(로그인 등) `max-w-md`.
- 섹션 사이 간격은 **24px(`mt-6`) 하나로 통일**한다. 목록 항목 사이는 10px(`space-y-2.5`).
- 카드 안쪽 여백은 계층당 하나: 콘텐츠 카드 20px(`p-5`), 목록 항목 카드
  16×20px(`px-5 py-4`), 중첩 면 12×16px(`px-4 py-3`).

## Elevation & Depth

그림자는 두 단계뿐이다 — `shadow-card`(정지), `shadow-float`(호버 부양).
색은 KRDS alpha-shadow 토큰. 페이지 내부 콘텐츠 카드는 **그림자를 쓰지 않고**
테두리(`ink-100`)나 면 색(`ink-25`)으로 구분한다. 그림자는 랜딩·독립 카드
(`card-elevated`)처럼 페이지에서 떠 있어야 하는 요소에만 허용한다.

## Shapes

모서리 반경은 계층을 나타낸다. 깊이가 한 단계 들어갈 때마다 한 단계 줄인다.

- `xl`(24px): 페이지에서 독립적으로 떠 있는 카드 (랜딩 카드, 로그인 Card).
- `lg`(16px): 화면 본문의 콘텐츠 카드·목록 항목·well — **본문 카드의 기본값**.
- `md`(12px): 카드 안에 중첩된 면 (인용 박스, 기관 행, 안내 줄).
- `sm`(8px): 배지·칩·복사 버튼 등 인라인 요소.

같은 깊이의 형제 카드는 반드시 같은 반경·같은 여백을 쓴다.

## Components

- **card**: 본문 콘텐츠 카드. 흰 배경 + `ink-100` 테두리 + `lg` 반경 + 20px 여백.
- **card-item**: 목록 항목(확인 질문, 유사 사례). card와 같되 여백 16×20px.
- **card-well**: 설명 면. `ink-25` 배경, 테두리 없음. 긴 읽기 본문(쉽게 설명하면)용.
- **card-alert**: 계약서 원문처럼 주의를 끄는 카드. `danger-50` 배경 +
  `danger-500/20` 테두리. 위험도 의미가 있을 때만 쓴다.
- **card-nested**: 카드 안의 중첩 면. `ink-25` 배경 + `md` 반경 + 12×16px.
- **button-primary**: brand-500, 높이 48px(KRDS 터치 타깃 최소) — 모든 버튼 공통.
- **badge**: 위험도 배지. 색+아이콘+텍스트 3중 인코딩 필수.

## Do's and Don'ts

- DO: 새 화면을 만들 때 위 컴포넌트 어휘로만 조합한다. 어휘에 없으면 이 문서에
  먼저 추가하고 쓴다.
- DO: 값이 필요하면 `index.css` 변수·Tailwind 토큰 클래스를 참조한다.
- DON'T: `p-4`·`p-6`처럼 계층 규격에 없는 카드 여백을 새로 만들지 않는다.
- DON'T: 같은 화면에서 형제 요소에 다른 반경(`rounded-2xl` 옆 `rounded-3xl`)을
  섞지 않는다.
- DON'T: brand 색을 장식(비클릭 요소)에 쓰지 않는다. 위험도 색을 의미 없이 쓰지
  않는다.
- DON'T: 섹션 제목에 임의 크기·색을 쓰지 않는다 — `section-label` 하나뿐이다.
