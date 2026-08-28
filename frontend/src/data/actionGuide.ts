/** 조항별 행동 가이드 (과제 B) — "다음 행동": 협상 문구 + 구제기관 매칭.
 *
 * 판정(위험·주의)에서 끝나지 않고 행동까지 연결한다:
 * ① 상대방에게 요구할 협상 문구 — 위험 유형 10종별로 사람이 작성한 규칙 기반
 *    문구. LLM 호출이 없어 환각 위험이 0이고(판정 경로의 fail-closed 철학과
 *    동일), 판정 프롬프트를 건드리지 않아 제출 직전 회귀 위험도 없다.
 * ② 조율 실패 시 연결할 구제기관 — 문서 도메인(Upload에서 사용자가 고른
 *    유형, agent/src/nodes/domain.py ALLOWED_DOMAINS와 동일 값)별 매칭.
 *
 * 유형별 요구 문구의 근거: docs/risk_taxonomy_v2.md의 유형 정의(약관규제법
 * 대응 조문 포함)와 agent/src/learn_content.py RISK_TYPE_GUIDE의 tip.
 * 법 조문 인용은 학습 페이지에서 이미 검수된 내용만 재사용한다.
 *
 * 문구는 법률 자문이 아니라 "요구·확인 도움말" — 화면에는 agDisclaimer
 * 고지를 함께 띄운다 (사건 각주 #91의 단정 회피 원칙과 동일).
 */

import type { ClauseResult } from '../api'

/* ---------- ① 협상 문구 ---------- */

// 키는 에이전트가 반환하는 risk_type 한국어 원문과 글자 그대로 일치해야 한다
// (i18n.ts RISK_TYPES · agent schemas.RISK_TYPES와 동일 문자열).
const NEGOTIATION_DEMANDS: Record<string, string> = {
  '과도한 위약금':
    '위약금이 실제 손해를 넘지 않도록 산정 기준과 상한을 숫자로 명시하고, ' +
    '잔여 기간 요금 전액 부과가 아니라 실제 손해 기준(일할 계산)으로 조정해 주시기 바랍니다. ' +
    '과도한 손해배상 예정은 무효가 되거나 감액될 수 있습니다(약관규제법 제8조, 민법 제398조).',
  '일방적 계약 해지':
    '해지할 수 있는 사유를 구체적으로 정하고, 해지 전 서면 통지 절차와 ' +
    '14일 이상의 시정 기간을 조항에 함께 명시해 주시기 바랍니다. ' +
    '사전 통지 없는 즉시 해지 조항은 무효로 판단될 수 있습니다(약관규제법 제9조).',
  '보증금 반환 지연':
    "보증금·환급금의 반환 기한을 '계약 종료일부터 며칠 이내'로 못 박고, " +
    '지연 시 적용할 지연이자(이율)를 함께 명시해 주시기 바랍니다. ' +
    '반환 의무를 부당하게 미루는 조항은 무효로 판단될 수 있습니다(약관규제법 제9조).',
  '책임 면제':
    "면책 범위를 '고의·중과실은 제외'로 한정하고, 법이 정한 수선 의무·하자담보책임은 " +
    '그대로 유지된다고 명시해 주시기 바랍니다. ' +
    '사업자의 고의·중과실 책임까지 면제하는 조항은 무효입니다(약관규제법 제7조).',
  '불명확한 수수료·이자 조건':
    '수수료·이자의 요율과 산정 기준, 부과 시점을 계약서에 숫자로 명시해 주시기 바랍니다. ' +
    '뜻이 명백하지 않은 조항은 고객에게 유리하게 해석되는 것이 원칙입니다(약관규제법 제5조).',
  '신탁관계·소유권 불안정 고지':
    '신탁원부를 제시해 임대 권한이 누구에게 있는지 확인해 주시고, 보증금 반환 책임의 ' +
    '주체와 신탁회사(수탁자)의 동의 여부를 계약서에 명시해 주시기 바랍니다. ' +
    '확인 전에는 계약금 지급을 보류하겠습니다.',
  '부당한 비용·세금 전가':
    '이 비용·세금이 법률상 누구 부담인지 근거를 알려 주시고, 소유자·사업자 부담분은 ' +
    '원래 부담 주체가 내는 것으로 수정해 주시기 바랍니다. ' +
    '사업자가 부담할 비용을 고객에게 떠넘기는 조항은 무효로 판단될 수 있습니다(약관규제법 제6조).',
  '일방적 급부·조건 변경':
    '계약 내용을 바꿀 때는 사전 개별 통지 절차와 고객의 거부·해지권을 조항에 명시하고, ' +
    "'통지 없이 변경'이나 '무응답 시 동의 간주' 문구는 삭제해 주시기 바랍니다. " +
    '상당한 이유 없이 급부를 일방적으로 바꾸는 조항은 무효로 판단될 수 있습니다(약관규제법 제10조).',
  '선택권 제한·구입 강제':
    '지정 상품·업체 이용이 계약 목적에 꼭 필요한 이유를 설명해 주시고, ' +
    '필수가 아니라면 선택 사항으로 바꿔 주시기 바랍니다. ' +
    '고객의 선택권을 부당하게 제한하는 조항은 무효로 판단될 수 있습니다(약관규제법 제6조).',
  '권리행사 제한':
    '법이 보장한 해지권·이의제기·소송 제기 권리는 제한하지 않는 것으로 문구를 수정해 ' +
    '주시기 바랍니다. 고객의 항변권·제소권을 부당하게 제한하는 조항은 ' +
    '무효입니다(약관규제법 제11조·제14조).',
}

// 유형을 못 알아본 경우의 일반 요구 — 아무것도 안 보여주는 것보다 낫다
const GENERIC_DEMAND =
  '이 조항이 한쪽에만 유리하게 해석되지 않도록, 적용 기준과 절차를 구체적인 ' +
  '숫자와 문구로 계약서에 명시해 주시기 바랍니다.'

const MAX_QUOTE = 60

/** 인용문을 한 줄·60자로 다듬는다 — 협상 문구가 원문 전체를 삼키지 않게. */
function truncate(text: string): string {
  const oneLine = text.replace(/\s+/g, ' ').trim()
  return oneLine.length > MAX_QUOTE ? `${oneLine.slice(0, MAX_QUOTE)}…` : oneLine
}

/** 협상 문구에 인용할 원문 구절.
 *  1순위 evidence_spans(백엔드가 지정한 근거 구간) → 2순위 risk_evidence 안의
 *  따옴표 인용 → 3순위 조항 원문 앞부분. */
function evidenceQuote(
  clause: Pick<ClauseResult, 'risk_evidence' | 'original_text' | 'evidence_spans'>,
): string {
  const span = clause.evidence_spans?.[0]
  if (span && span.length === 2) {
    const sliced = clause.original_text.slice(span[0], span[1]).trim()
    if (sliced) return truncate(sliced)
  }
  const quoted = clause.risk_evidence?.match(/["“「]([^"”」]{4,})["”」]/)
  if (quoted) return truncate(quoted[1])
  return truncate(clause.original_text)
}

/** risk_type 문자열 정규화 — 스키마 이탈 방어.
 *  docs/risk_taxonomy_v2.md §부작용: 유형이 "3. 보증금 반환 지연, 4. 책임 면제"
 *  처럼 번호·다중값으로 오는 사례가 있어, 정확 일치가 없으면 문자열에 포함된
 *  첫 번째 알려진 유형으로 매칭한다. */
function normalizeRiskType(riskType: string): string | null {
  if (riskType in NEGOTIATION_DEMANDS) return riskType
  for (const known of Object.keys(NEGOTIATION_DEMANDS)) {
    if (riskType.includes(known)) return known
  }
  return null
}

/** 상대방(한국인)에게 보여줄 협상 문구 — 조항 근거 인용 + 유형별 요구.
 *  번역 방침(i18n.ts 상단)대로 한국어 유지: 상대방에게 보여주는 용도라
 *  비한국어 UI에서는 라벨(agKoreanHint)로 용도를 설명한다. */
export function buildNegotiation(
  clause: Pick<ClauseResult, 'risk_type' | 'risk_evidence' | 'original_text' | 'evidence_spans'>,
): string {
  const type = normalizeRiskType(clause.risk_type)
  const demand = type ? NEGOTIATION_DEMANDS[type] : GENERIC_DEMAND
  return `계약서의 「${evidenceQuote(clause)}」 부분에 대해 요청드립니다. ${demand}`
}

/* ---------- ② 구제기관 매칭 ---------- */

/** 기관 한 줄 설명의 i18n 키 — doSvc*는 Done 화면(UI_SCREENS)과 공용,
 *  agSvc*는 이 기능에서 추가(UI_ACTION). */
export type AgencyDescKey = 'doSvcKlac' | 'doSvcJeonse' | 'doSvcFss' | 'agSvcHldcc' | 'agSvcKca'

export interface RescueAgency {
  /** 기관명 — 고유명사라 한국어 유지 (번역 방침) */
  name: string
  phone: string | null
  url: string
  descKey: AgencyDescKey
}

/** 기관 데이터의 단일 원천 — Done.tsx buildConsultServices도 여기서 가져다
 *  써서 이름·전화·URL이 두 화면에서 어긋나지 않게 한다. */
export const AGENCIES = {
  klac: {
    name: '대한법률구조공단',
    phone: '132',
    url: 'https://www.klac.or.kr',
    descKey: 'doSvcKlac',
  },
  jeonse: {
    name: '전세피해지원센터',
    phone: '1533-8119',
    url: 'https://www.khug.or.kr/jeonse',
    descKey: 'doSvcJeonse',
  },
  fss: {
    name: '금융감독원 금융민원센터',
    phone: '1332',
    url: 'https://www.fss.or.kr',
    descKey: 'doSvcFss',
  },
  hldcc: {
    name: '주택임대차분쟁조정위원회',
    phone: '132',
    url: 'https://www.hldcc.or.kr',
    descKey: 'agSvcHldcc',
  },
  kca: {
    name: '한국소비자원',
    phone: '1372',
    url: 'https://www.kca.go.kr',
    descKey: 'agSvcKca',
  },
} as const satisfies Record<string, RescueAgency>

// Upload.tsx DOMAINS(= agent ALLOWED_DOMAINS)의 값 기준 그룹.
const LEASE_DOMAINS = ['주택임대차', '상가임대차', '임대차(구분불명)']
const FINANCE_DOMAINS = ['대출·여신', '보험', '신용카드', '예금·수신', '투자·신탁']

/** 문서 도메인 → 구제기관 목록.
 *  - 임대차: 분쟁조정위(조정) + 전세피해지원센터 + 법률구조공단
 *  - 금융: 금융감독원(1332) + 법률구조공단
 *  - 근로계약: 소비자 계약이 아니라 한국소비자원 안내가 어긋난다 —
 *    범용 무료 법률상담인 법률구조공단만 안내
 *  - 그 외(모름 포함): 한국소비자원(1372) + 법률구조공단 */
export function agenciesForDomain(domain: string): RescueAgency[] {
  if (LEASE_DOMAINS.includes(domain)) return [AGENCIES.hldcc, AGENCIES.jeonse, AGENCIES.klac]
  if (FINANCE_DOMAINS.includes(domain)) return [AGENCIES.fss, AGENCIES.klac]
  if (domain === '근로계약') return [AGENCIES.klac]
  return [AGENCIES.kca, AGENCIES.klac]
}
