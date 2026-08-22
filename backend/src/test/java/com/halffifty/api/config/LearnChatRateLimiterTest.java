package com.halffifty.api.config;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

/** 교육 챗봇 비용 상한(#137) — IP별 시간당 20회 슬라이딩 윈도 검증. */
class LearnChatRateLimiterTest {

    @Test
    void allowsUpToTheLimit() {
        LearnChatRateLimiter limiter = new LearnChatRateLimiter();
        for (int i = 0; i < 20; i++) {
            assertTrue(limiter.allow("1.2.3.4"), "20회까지는 허용돼야 한다 (회차 " + i + ")");
        }
    }

    @Test
    void blocksBeyondTheLimit() {
        LearnChatRateLimiter limiter = new LearnChatRateLimiter();
        for (int i = 0; i < 20; i++) {
            limiter.allow("1.2.3.4");
        }
        assertFalse(limiter.allow("1.2.3.4"), "21번째 호출은 차단돼야 한다");
    }

    @Test
    void tracksEachClientIndependently() {
        LearnChatRateLimiter limiter = new LearnChatRateLimiter();
        for (int i = 0; i < 20; i++) {
            limiter.allow("1.2.3.4");
        }
        // 다른 IP는 첫 번째 IP가 상한에 걸려도 영향받지 않는다
        assertTrue(limiter.allow("5.6.7.8"), "다른 클라이언트는 독립적으로 카운트돼야 한다");
    }
}
