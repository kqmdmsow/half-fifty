package com.halffifty.api.security;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.JwtException;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/** 로그인 세션 토큰 발급·검증 (#102) — HS256, 서명 키는 JWT_SECRET 환경변수. */
@Service
public class JwtService {

    private static final Logger log = LoggerFactory.getLogger(JwtService.class);

    private final SecretKey key;
    private final Duration ttl;

    public JwtService(
            @Value("${auth.jwt-secret:}") String secret,
            @Value("${auth.token-days:30}") long tokenDays) {
        if (secret == null || secret.isBlank()) {
            // 개발 편의용 임시 키 — 재시작하면 기존 토큰이 무효가 된다.
            // 배포에서 이 경로를 타면 사용자가 매 배포마다 로그아웃되므로 경고를 남긴다.
            byte[] random = new byte[32];
            new SecureRandom().nextBytes(random);
            this.key = new SecretKeySpec(random, "HmacSHA256");
            log.warn("JWT_SECRET 미설정 — 임시 키로 부팅합니다(재시작 시 전원 재로그인 필요).");
        } else {
            this.key = new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
        }
        this.ttl = Duration.ofDays(tokenDays);
    }

    public String issue(String email) {
        Instant now = Instant.now();
        return Jwts.builder()
                .subject(email)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plus(ttl)))
                .signWith(key)
                .compact();
    }

    /** 유효하면 이메일(subject), 아니면 null — 만료·위조를 호출부에서 구분하지 않는다. */
    public String verify(String token) {
        try {
            return Jwts.parser().verifyWith(key).build().parseSignedClaims(token).getPayload().getSubject();
        } catch (JwtException | IllegalArgumentException e) {
            return null;
        }
    }
}
