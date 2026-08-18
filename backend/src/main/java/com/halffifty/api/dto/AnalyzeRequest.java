package com.halffifty.api.dto;

/**
 * 계약서 분석 요청.
 *
 * @param text     계약서 원문 텍스트
 * @param persona  사용자 페르소나 ("adult" | "senior" | "foreigner")
 * @param language 설명 출력 언어 — null이면 에이전트가 ko 처리
 * @param domain   사용자가 선택한 문서 유형 (예: "주택임대차", 미선택이면 빈 값)
 */
public record AnalyzeRequest(String text, String persona, String language, String domain) {
}
