package com.halffifty.api.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/**
 * 로그인 계정 (#102).
 *
 * <p>비밀번호 자체는 서버에 오지 않는다. 클라이언트가 비밀번호에서 PBKDF2로
 * 두 값을 파생해 <b>인증 증명(authProof)만</b> 전송하고, 암호화 키는 기기를
 * 떠나지 않는다. 서버는 그 인증 증명을 다시 BCrypt로 해싱해 보관하므로
 * DB가 통째로 유출돼도 사용자의 기록을 복호화할 수 없다.
 */
@Entity
@Table(name = "accounts")
public class Account {

    @Id
    @GeneratedValue
    private Long id;

    /** 로그인 식별자. 소문자로 정규화해 저장한다. */
    @Column(nullable = false, unique = true, length = 320)
    private String email;

    /** BCrypt(authProof) — 원문 비밀번호도, 암호화 키도 아니다. */
    @Column(nullable = false, length = 100)
    private String authHash;

    @Column(nullable = false)
    private Instant createdAt = Instant.now();

    protected Account() {}

    public Account(String email, String authHash) {
        this.email = email;
        this.authHash = authHash;
    }

    public Long getId() {
        return id;
    }

    public String getEmail() {
        return email;
    }

    public String getAuthHash() {
        return authHash;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
