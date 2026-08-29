// 데모 샘플 사전 분석 캐시 — agent/generate_sample_cache.py가 생성한
// sampleResults.json을 조회한다. 캐시는 sampleTexts.json의 텍스트 샘플 6종을
// 실제 파이프라인(언어 ko, 샘플 지정 페르소나)으로 미리 돌린 결과라
// AnalyzeResponse와 필드가 1:1로 같다 — evidence_spans·related_cases까지
// 그대로 담겨 '자세히 보기'도 실분석과 동일하게 동작한다.
//
// 생성 실패 등으로 파일이 빈 객체({})면 조회가 전부 null이 되고,
// 프론트는 기존 실분석 경로로 그대로 폴백한다 (App.tsx applySample).

import type { AnalyzeResponse } from '../api'
import sampleResults from './sampleResults.json'

// JSON 추론 타입은 risk_level 등이 넓은 string이라 응답 타입으로 좁혀 준다.
// 값은 agent/main.py의 AnalyzeResponse(pydantic)를 그대로 직렬화한 것.
const CACHE = sampleResults as unknown as Record<string, AnalyzeResponse>

/** 샘플 id의 사전 분석 결과. 캐시가 없거나 비정상이면 null (실분석 폴백). */
export function cachedSampleResult(id: string): AnalyzeResponse | null {
  const hit = CACHE[id]
  return hit && Array.isArray(hit.results) && hit.results.length > 0 ? hit : null
}
