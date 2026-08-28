// 심사용 원클릭 데모 샘플 (#81) — docs/hackathon_finance_ai/데모_시나리오.md 기반.
// 판정 근거가 되는 핵심 조항은 실제 분쟁조정례·판결 검수 조항 원문 그대로이며
// (data/real_clause_labels_*.csv 출처), 주변에 표준 조항을 더해 실제 계약서
// 형태로 구성했다 — 여러 조항 중 위험을 골라내는 모습까지 데모되도록.
// 파일 샘플 2종(PDF·사진)은 frontend/public/samples/ 정적 자산.
//
// 텍스트 샘플 6종의 본문·페르소나·도메인은 sampleTexts.json이 단일 출처다 —
// agent/generate_sample_cache.py가 같은 JSON을 읽어 사전 분석 캐시
// (sampleResults.json)를 만들기 때문에, 여기 하드코딩을 남기면 화면 입력과
// 캐시 결과의 원문이 어긋날 수 있다.

import type { Persona } from '../api'
import sampleTexts from './sampleTexts.json'

export interface DemoSample {
  id: string
  labelKey: 'sp1' | 'sp2' | 'sp3' | 'sp4' | 'sp5' | 'sp6' | 'sp7' | 'sp8'
  /** 핵심 확인 포인트의 예상 판정 — 배지 표시용 */
  expected: '위험' | '안전'
  kind: 'text' | 'file'
  domain: string
  persona?: Persona
  text?: string
  fileUrl?: string
  fileName?: string
  fileType?: string
}

interface SampleText {
  id: string
  domain: string
  persona?: Persona
  text: string
}

// JSON 추론 타입은 persona가 string이라 Persona 유니온으로 좁혀 준다.
// (값 자체는 agent/main.py의 Literal["adult","senior","foreigner"]와 동일 관리)
const TEXT_SAMPLES = new Map(
  (sampleTexts as unknown as SampleText[]).map((sample) => [sample.id, sample]),
)

/** sampleTexts.json에서 id로 본문·도메인·페르소나를 가져온다. */
const textSample = (id: string): Pick<DemoSample, 'id' | 'domain' | 'persona' | 'text'> => {
  const sample = TEXT_SAMPLES.get(id)
  if (!sample) throw new Error(`sampleTexts.json에 없는 샘플 id: ${id}`)
  return { id: sample.id, domain: sample.domain, persona: sample.persona, text: sample.text }
}

export const DEMO_SAMPLES: DemoSample[] = [
  {
    ...textSample('loan-acceleration'),
    labelKey: 'sp1',
    expected: '위험',
    kind: 'text',
  },
  {
    ...textSample('insurance-coverage'),
    labelKey: 'sp2',
    expected: '안전',
    kind: 'text',
  },
  {
    ...textSample('card-liability'),
    labelKey: 'sp3',
    expected: '위험',
    kind: 'text',
  },
  {
    ...textSample('efinance-standard'),
    labelKey: 'sp4',
    expected: '안전',
    kind: 'text',
  },
  {
    ...textSample('jeonse-trust'),
    labelKey: 'sp5',
    expected: '위험',
    kind: 'text',
  },
  {
    ...textSample('senior-mode'),
    labelKey: 'sp6',
    expected: '위험',
    kind: 'text',
  },
  {
    id: 'pdf-standard',
    labelKey: 'sp7',
    expected: '안전',
    kind: 'file',
    domain: '주택임대차',
    fileUrl: '/samples/sample_lease_standard.pdf',
    fileName: '주택임대차표준계약서.pdf',
    fileType: 'application/pdf',
  },
  {
    id: 'photo-ocr',
    labelKey: 'sp8',
    expected: '위험',
    kind: 'file',
    domain: '주택임대차',
    fileUrl: '/samples/sample_lease_photo.jpg',
    fileName: '계약서_사진.jpg',
    fileType: 'image/jpeg',
  },
]
