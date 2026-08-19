package com.halffifty.api.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientResponseException;

/**
 * 에이전트 장애를 사용자 친화적 JSON으로 표준화 (#52, backend_spec.md §2).
 *
 * 범위를 에이전트 호출 예외 2종으로 한정한다 — ResponseStatusException 등
 * 컨트롤러가 의도적으로 던지는 예외는 Spring 기본 처리를 유지해 상태코드와
 * 사유(파일 형식·용량 검증 메시지)가 그대로 전달되게 한다.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    public record ErrorResponse(String message) {
    }

    /** 에이전트 연결 실패·타임아웃 → 503. 프론트 '다시 시도' UX와 연결. */
    @ExceptionHandler(ResourceAccessException.class)
    @ResponseStatus(HttpStatus.SERVICE_UNAVAILABLE)
    public ErrorResponse agentUnreachable(ResourceAccessException e) {
        // 사용자 응답은 일반 문구, 원인은 서버 로그로 — 심사 기간 장애 추적용 (#80)
        log.error("에이전트 연결 실패", e);
        return new ErrorResponse("분석 서버에 연결하지 못했어요. 잠시 후 다시 시도해주세요.");
    }

    /** 에이전트가 4xx/5xx를 반환 → 502로 감싸 내부 스택 노출 방지. */
    @ExceptionHandler(RestClientResponseException.class)
    @ResponseStatus(HttpStatus.BAD_GATEWAY)
    public ErrorResponse agentError(RestClientResponseException e) {
        log.error("에이전트 오류 응답: HTTP {}", e.getStatusCode().value(), e);
        return new ErrorResponse("분석 처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요.");
    }
}
