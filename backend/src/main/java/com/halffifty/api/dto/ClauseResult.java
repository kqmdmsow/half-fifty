package com.halffifty.api.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

/**
 * 조항 1개에 대한 출력. Agent Service 응답 스키마와 1:1 대응.
 *
 * <p>record는 매핑되지 않은 필드를 조용히 버린다. 스트리밍 경로
 * (/analyze-stream)는 원시 바이트 프록시라 에이전트 응답이 그대로 흐르지만,
 * REST 경로(/analyze·/analyze-pdf·/analyze-image)는 이 DTO를 거치므로
 * 여기 없는 필드는 사라진다. 실제로 analysis_failed·related_cases가 그렇게
 * 유실되고 있었다 — 같은 서비스가 호출 경로에 따라 다른 정보를 주면 안 된다.
 * 에이전트 ClauseResult에 필드를 추가하면 반드시 여기도 함께 추가할 것.
 */
public record ClauseResult(
        @JsonProperty("clause_id") String clauseId,
        @JsonProperty("original_text") String originalText,
        String explanation,
        @JsonProperty("risk_level") String riskLevel,
        @JsonProperty("risk_type") String riskType,
        @JsonProperty("risk_evidence") String riskEvidence,
        @JsonProperty("check_questions") List<String> checkQuestions,
        @JsonProperty("original_text_translated") String originalTextTranslated,
        @JsonProperty("check_questions_translated") List<String> checkQuestionsTranslated,
        @JsonProperty("risk_evidence_translated") String riskEvidenceTranslated,
        /** 실제 사건 각주 (#91) — 표시 전용이라 구조를 강제하지 않고 그대로 중계한다. */
        @JsonProperty("related_cases") List<Map<String, Object>> relatedCases,
        /** 재시도 소진 폴백 (#100) — 프론트가 안내 문구를 현지화하는 마커. */
        @JsonProperty("analysis_failed") boolean analysisFailed,
        /** 이 조항에서 프롬프트 인젝션 흔적이 탐지됐는가 (#174). */
        @JsonProperty("injection_suspected") boolean injectionSuspected,
        /** 격리해 LLM 입력에서 제외한 조작 문장 수 (#174). */
        @JsonProperty("quarantined") int quarantined,
        /** 격리 후 근거가 남지 않아 판정을 거부했는가 (#174, fail-closed). */
        @JsonProperty("verdict_withheld") boolean verdictWithheld,
        /** 판정 안전장치가 등급을 올렸다면 모델의 원래 판정 (#174, 감사 추적). */
        @JsonProperty("original_risk_level") String originalRiskLevel
) {
}
