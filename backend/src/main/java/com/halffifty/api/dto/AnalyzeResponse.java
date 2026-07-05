package com.halffifty.api.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

/** 분석 결과 전체. Agent Service 응답 스키마와 1:1 대응. */
public record AnalyzeResponse(
        @JsonProperty("clause_count") int clauseCount,
        @JsonProperty("retry_count") int retryCount,
        @JsonProperty("needs_review") boolean needsReview,
        @JsonProperty("judge_scores") Map<String, Double> judgeScores,
        List<ClauseResult> results
) {
}
