package com.halffifty.api.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/** 조항 1개에 대한 4종 출력. Agent Service 응답 스키마와 1:1 대응. */
public record ClauseResult(
        @JsonProperty("clause_id") String clauseId,
        @JsonProperty("original_text") String originalText,
        String explanation,
        @JsonProperty("risk_level") String riskLevel,
        @JsonProperty("risk_type") String riskType,
        @JsonProperty("risk_evidence") String riskEvidence,
        @JsonProperty("check_questions") List<String> checkQuestions
) {
}
