package com.halffifty.api.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * 접근 로그 (#80, 자문 §7 "오류 및 접근 기록 관리").
 *
 * 원칙: 개인정보(파일명·계약 내용·쿼리스트링)는 남기지 않는다 —
 * 메서드·경로·상태코드·소요시간·요청 크기만. 심사 기간 장애 시
 * Render 대시보드 로그로 원인을 추적하기 위한 최소 운영 기록이다.
 */
@Component
public class AccessLogFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger("access");

    @Override
    protected void doFilterInternal(
            HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        long start = System.currentTimeMillis();
        try {
            chain.doFilter(request, response);
        } finally {
            log.info("{} {} -> {} ({}ms, {}B)",
                    request.getMethod(),
                    request.getRequestURI(),
                    response.getStatus(),
                    System.currentTimeMillis() - start,
                    Math.max(request.getContentLengthLong(), 0));
        }
    }
}
