import { useEffect, useState } from 'react'
import type { LangCode } from '../i18n'

/** 히어로 회전 헤드라인 (#134) — '쉬운'류 키워드를 축으로 좌우 단어가 바뀐다.
 *
 * 언어마다 어순이 달라(형용사 전치/후치, 동사 위치) 언어별 설정으로 푼다:
 * - hl: 고정 강조어('쉬운'의 각 언어 대응)
 * - pairs: 회전하는 [a, b] 슬롯 4쌍 (전세/대출/근로/보험 소재)
 * - order: 세 조각의 표시 순서 — 예: ko는 a-hl-b('이해하기 쉬운 전세계약'),
 *   th는 a-b-hl('สัญญาเช่า เข้าใจง่าย')
 * 움직임 최소화 설정이면 인터벌을 걸지 않아 첫 문구로 고정된다.
 * 스크린리더에는 회전 대신 고정 문구(aria-label)를 읽어준다.
 */
type Order = Array<'a' | 'hl' | 'b'>

interface Config {
  hl: string
  order: Order
  pairs: Array<[string, string]>
}

const CONFIG: Partial<Record<LangCode, Config>> = {
  ko: { hl: '쉬운', order: ['a', 'hl', 'b'], pairs: [['이해하기', '전세계약'], ['읽기', '대출약정'], ['알기', '근로계약'], ['확인하기', '보험약관']] },
  en: { hl: 'easy', order: ['a', 'hl', 'b'], pairs: [['Leases,', 'to understand'], ['Loan terms,', 'to read'], ['Job contracts,', 'to grasp'], ['Insurance,', 'to check']] },
  zh: { hl: '轻松', order: ['a', 'hl', 'b'], pairs: [['租房合同', '看懂'], ['贷款条款', '读懂'], ['劳动合同', '弄懂'], ['保险条款', '查清']] },
  ja: { hl: 'わかりやすく', order: ['a', 'hl', 'b'], pairs: [['賃貸契約を', '確認'], ['ローン条項を', '理解'], ['雇用契約を', '把握'], ['保険約款を', '点検']] },
  vi: { hl: 'dễ', order: ['a', 'hl', 'b'], pairs: [['Hợp đồng thuê', 'hiểu'], ['Điều khoản vay', 'đọc'], ['Hợp đồng lao động', 'nắm'], ['Điều khoản bảo hiểm', 'kiểm tra']] },
  th: { hl: 'ง่าย', order: ['a', 'b', 'hl'], pairs: [['สัญญาเช่า', 'เข้าใจ'], ['สัญญากู้', 'อ่าน'], ['สัญญาจ้าง', 'รู้'], ['กรมธรรม์', 'เช็ก']] },
  id: { hl: 'mudah', order: ['a', 'hl', 'b'], pairs: [['Kontrak sewa', 'dipahami'], ['Syarat pinjaman', 'dibaca'], ['Kontrak kerja', 'dimengerti'], ['Polis asuransi', 'dicek']] },
  tl: { hl: 'Madaling', order: ['hl', 'a', 'b'], pairs: [['basahin', 'ang kontrata sa upa'], ['intindihin', 'ang kasunduan sa utang'], ['unawain', 'ang kontrata sa trabaho'], ['suriin', 'ang polisiya ng seguro']] },
  ne: { hl: 'सजिलै', order: ['a', 'hl', 'b'], pairs: [['भाडा सम्झौता', 'बुझ्नुहोस्'], ['ऋण सर्तहरू', 'पढ्नुहोस्'], ['रोजगार सम्झौता', 'जान्नुहोस्'], ['बीमा सर्तहरू', 'जाँच्नुहोस्']] },
  km: { hl: 'ងាយ', order: ['a', 'b', 'hl'], pairs: [['កិច្ចសន្យាជួល', 'យល់'], ['លក្ខខណ្ឌកម្ចី', 'អាន'], ['កិច្ចសន្យាការងារ', 'ដឹង'], ['ធានារ៉ាប់រង', 'ពិនិត្យ']] },
  my: { hl: 'လွယ်ကူစွာ', order: ['a', 'hl', 'b'], pairs: [['ငှားရမ်းစာချုပ်ကို', 'နားလည်'], ['ချေးငွေစည်းကမ်းကို', 'ဖတ်ရှု'], ['အလုပ်စာချုပ်ကို', 'သိရှိ'], ['အာမခံစည်းကမ်းကို', 'စစ်ဆေး']] },
  mn: { hl: 'хялбар', order: ['a', 'hl', 'b'], pairs: [['Түрээсийн гэрээг', 'ойлгоно'], ['Зээлийн нөхцөлийг', 'уншина'], ['Хөдөлмөрийн гэрээг', 'мэднэ'], ['Даатгалын нөхцөлийг', 'шалгана']] },
  uz: { hl: 'oson', order: ['a', 'hl', 'b'], pairs: [['Ijara shartnomasini', 'tushuning'], ['Kredit shartlarini', "o'qing"], ['Mehnat shartnomasini', 'biling'], ["Sug'urta shartlarini", 'tekshiring']] },
  si: { hl: 'පහසුවෙන්', order: ['a', 'hl', 'b'], pairs: [['කුලී ගිවිසුම', 'තේරුම් ගන්න'], ['ණය කොන්දේසි', 'කියවන්න'], ['රැකියා ගිවිසුම', 'දැනගන්න'], ['රක්ෂණ කොන්දේසි', 'පරීක්ෂා කරන්න']] },
  bn: { hl: 'সহজে', order: ['a', 'hl', 'b'], pairs: [['ভাড়ার চুক্তি', 'বুঝুন'], ['ঋণের শর্ত', 'পড়ুন'], ['চাকরির চুক্তি', 'জানুন'], ['বিমার শর্ত', 'যাচাই করুন']] },
  ru: { hl: 'легко', order: ['a', 'hl', 'b'], pairs: [['Договор аренды —', 'понять'], ['Условия кредита —', 'прочитать'], ['Трудовой договор —', 'разобрать'], ['Условия страховки —', 'проверить']] },
}

/** 교체 주기 4.8초 — 문구 4종이라 한 바퀴 약 19초. */
const CYCLE_MS = 4800
/** 사라지는 데 쓰는 시간. 이 시간이 지난 뒤에 다음 문구가 올라온다.
 *  예전에는 옛 글자가 즉시 사라져 '깜빡'하고 바뀌는 느낌이었다(#134 피드백). */
const FADE_OUT_MS = 700

export function RotatingTitle({ language = 'ko' }: { language?: LangCode }) {
  const [idx, setIdx] = useState(0)
  const [leaving, setLeaving] = useState(false)
  const cfg = CONFIG[language] ?? CONFIG.ko!

  useEffect(() => {
    setIdx(0)
    setLeaving(false)
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    let swapTimer: number | undefined
    const timer = setInterval(() => {
      setLeaving(true) // ① 천천히 사라지고
      swapTimer = window.setTimeout(() => {
        setIdx((i) => (i + 1) % cfg.pairs.length) // ② 다음 문구로 바꾼 뒤
        setLeaving(false) // ③ 천천히 올라온다
      }, FADE_OUT_MS)
    }, CYCLE_MS)
    return () => {
      clearInterval(timer)
      if (swapTimer) clearTimeout(swapTimer)
    }
  }, [language, cfg.pairs.length])

  const [a, b] = cfg.pairs[idx % cfg.pairs.length]
  const label = cfg.order
    .map((part) => (part === 'hl' ? cfg.hl : part === 'a' ? cfg.pairs[0][0] : cfg.pairs[0][1]))
    .join(' ')

  const seg = (part: Order[number]) => {
    if (part === 'hl') {
      return (
        <span
          key="hl"
          aria-hidden
          className="bg-[linear-gradient(transparent_60%,rgb(var(--c-brand-100))_60%)] px-1"
        >
          {cfg.hl}
        </span>
      )
    }
    const text = part === 'a' ? a : b
    return (
      <span
        key={`${part}-${idx}-${language}`}
        aria-hidden
        className={`${leaving ? 'word-leave' : 'word-enter'} ${part === 'b' ? 'text-brand-500' : ''}`}
      >
        {text}
      </span>
    )
  }

  return (
    <span aria-label={label}>
      {cfg.order.map((part, i) => (
        <span key={`${part}-wrap`}>
          {i > 0 && ' '}
          {seg(part)}
        </span>
      ))}
    </span>
  )
}
