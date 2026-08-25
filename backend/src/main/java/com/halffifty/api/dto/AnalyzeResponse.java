package com.halffifty.api.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

/**
 * 분석 결과 전체. Agent Service 응답 스키마와 1:1 대응.
 *
 * <p>record는 매핑되지 않은 필드를 조용히 버린다. parse_warning_codes는 프론트가
 * 경고 문구를 16개 언어로 현지화하는 근거이고, 이 DTO에 없으면 REST 경로에서만
 * 경고가 한국어 원문으로 떨어진다 (#175에서 실제로 그 사고가 났다).
 * 에이전트 AnalyzeResponse에 필드를 추가하면 반드시 여기도 함께 추가할 것.
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
