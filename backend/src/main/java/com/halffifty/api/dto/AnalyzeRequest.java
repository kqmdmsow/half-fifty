package com.halffifty.api.dto;

/**
 * 계약서 분석 요청.
 *
 * @param text    계약서 원문 텍스트
 * @param persona 사용자 페르소나 ("adult" | "senior")
 */
public record AnalyzeRequest(String text, String persona) {
}
