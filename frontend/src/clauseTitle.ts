// 조항 원문에서 "제N조(제목)" 표제를 뽑아 카드·상세 제목으로 쓴다.
// 위험 유형(risk_type)만 제목으로 쓰면 안전 조항이 전부 "표준 조항"으로 떠서
// 사용자가 올린 조항 중 어느 것인지 구분할 수 없다 — 원문 표제를 제목으로,
// 유형은 괄호 보조 표기로 내린다. 표제가 없는 원문은 앞부분을 잘라 보여준다.
//
// 비한국어 언어에서는 조 번호를 해당 언어 표기(第4条/Article 4/Điều 4…)로
// 바꾸고, 괄호 제목은 에이전트가 보내준 원문 번역(original_text_translated)의
// 첫 괄호에서 추출한다 — 번역에서 못 찾으면 한국어 제목을 그대로 둔다.

import type { LangCode } from './i18n'

const HEADING =
  /^\s*(제\s*\d+\s*조(?:의\s*\d+)?)\s*(?:\(([^)\n]{1,30})\)|【([^】\n]{1,30})】|\[([^\]\n]{1,30})\])?/

// 번역문 서두의 표제 괄호: "第4条（特約）…", "Article 4 (Special Terms) …"
const TRANS_TITLE = /^[^\n（(【\[]{0,24}[（(【\[]([^)）】\]\n]{1,40})[)）】\]]/

// 조 번호의 언어별 표기. '제10조의2'는 숫자를 하이픈으로 이어 "10-2"로 처리.
const ARTICLE_LABEL: Record<LangCode, (n: string) => string> = {
  ko: (n) => `제${n}조`,
  ja: (n) => `第${n}条`,
  zh: (n) => `第${n}条`,
  en: (n) => `Article ${n}`,
  vi: (n) => `Điều ${n}`,
  th: (n) => `ข้อ ${n}`,
  id: (n) => `Pasal ${n}`,
  tl: (n) => `Artikulo ${n}`,
  ne: (n) => `धारा ${n}`,
  km: (n) => `មាត្រា ${n}`,
  my: (n) => `အပိုဒ် ${n}`,
  mn: (n) => `${n}-р зүйл`,
  uz: (n) => `${n}-modda`,
  si: (n) => `${n} වගන්තිය`,
  bn: (n) => `ধারা ${n}`,
  ru: (n) => `Статья ${n}`,
}

function snippet(text: string): string | null {
  const s = text.trim().replace(/\s+/g, ' ')
  if (!s) return null
  return s.length > 18 ? `${s.slice(0, 18)}…` : s
}

export function clauseHeading(
  originalText: string | null | undefined,
  language: LangCode = 'ko',
  translatedText?: string | null,
): string | null {
  if (!originalText) return null
  const m = HEADING.exec(originalText)
  if (m) {
    const nums = m[1].match(/\d+/g) ?? []
    const label = (ARTICLE_LABEL[language] ?? ARTICLE_LABEL.ko)(nums.join('-'))
    let title = (m[2] ?? m[3] ?? m[4])?.trim()
    if (language !== 'ko' && translatedText) {
      const tm = TRANS_TITLE.exec(translatedText)
      if (tm) title = tm[1].trim()
    }
    // CJK는 붙여 쓰고(제4조(특약)), 그 외 문자권은 괄호 앞을 띄운다 (Article 4 (…))
    const sep = language === 'ko' || language === 'ja' || language === 'zh' ? '' : ' '
    return title ? `${label}${sep}(${title})` : label
  }
  // 표제 없는 원문(특약 문장 등): 비한국어면 번역 스니펫을 우선한다
  if (language !== 'ko' && translatedText) {
    return snippet(translatedText) ?? snippet(originalText)
  }
  return snippet(originalText)
}
