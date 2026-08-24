package com.halffifty.api.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

/**
 * 분석 결과 전체. Agent Service 응답 스키마와 1:1 대응.
 *
 * <p>parse_warning_codes는 프론트가 경고 문구를 16개 언어로 현지화하는 데 쓴다.
 * 이 DTO에 없으면 REST 경로에서만 경고가 한국어 원문으로 떨어진다.
 */
public record AnalyzeResponse(
        @JsonProperty("clause_count") int clauseCount,
        @JsonProperty("parse_warnings") List<String> parseWarnings,
        @JsonProperty("parse_warning_codes") List<String> parseWarningCodes,
        @JsonProperty("retry_count") int retryCount,
        @JsonProperty("needs_review") boolean needsReview,
        @JsonProperty("judge_scores") Map<String, Double> judgeScores,
        List<ClauseResult> results
) {
}
