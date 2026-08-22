package com.halffifty.api.config;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

/**
 * 교육 챗봇(/learn-chat, #103) 비용 상한 — IP별 시간당 호출 횟수 제한.
 *
 * 자유 입력 챗봇은 심사위원이 오래 붙들면 LLM 호출이 무제한으로 쌓일 수 있어
 * 크레딧 폭증 위험이 있다. 단일 인스턴스 배포(Render)라 인메모리 슬라이딩
 * 윈도로 충분 — 인증이 없는 익명 엔드포인트라 세션 대신 IP를 키로 쓴다.
 */
@Component
public class LearnChatRateLimiter {

    private static final int MAX_PER_WINDOW = 20;
    private static final long WINDOW_MS = 60 * 60 * 1000; // 1시간

    private final Map<String, Deque<Long>> hits = new ConcurrentHashMap<>();

    /** 허용되면 true(호출 기록), 상한 초과면 false. */
    public synchronized boolean allow(String clientKey) {
        long now = System.currentTimeMillis();
        Deque<Long> timestamps = hits.computeIfAbsent(clientKey, k -> new ArrayDeque<>());
        while (!timestamps.isEmpty() && now - timestamps.peekFirst() > WINDOW_MS) {
            timestamps.pollFirst();
        }
        if (timestamps.size() >= MAX_PER_WINDOW) {
            return false;
        }
        timestamps.addLast(now);
        return true;
    }
}
