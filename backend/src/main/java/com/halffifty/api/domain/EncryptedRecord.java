package com.halffifty.api.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Lob;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

/**
 * 사용자가 명시적으로 저장한 분석 기록 — <b>암호문 그대로</b> 보관 (#102).
 *
 * <p>서버는 도메인·조항 수·위험 건수 같은 메타데이터조차 갖지 않는다. 목록
 * 화면에 필요한 정보는 전부 암호문 안에 있고 클라이언트가 복호화해 렌더한다.
 * 서버가 아는 것은 "누가, 언제, 몇 바이트를 맡겼는가"뿐이다.
 */
@Entity
@Table(name = "encrypted_records")
public class EncryptedRecord {

    /** 클라이언트가 만든 기록 id (기기 간 동일해야 하므로 서버 생성이 아니다). */
    @Id
    @Column(length = 64)
    private String id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "account_id", nullable = false)
    private Account account;

    /** AES-GCM 초기화 벡터(base64). */
    @Column(nullable = false, length = 32)
    private String iv;

    /** AES-GCM 암호문(base64). 서버는 복호화 키를 갖지 않는다. */
    @Lob
    @Column(nullable = false)
    private String ciphertext;

    /** 사용자 기기 기준 저장 시각 — 정렬용. 내용 정보가 아니다. */
    @Column(nullable = false)
    private long savedAt;

    protected EncryptedRecord() {}

    public EncryptedRecord(String id, Account account, String iv, String ciphertext, long savedAt) {
        this.id = id;
        this.account = account;
        this.iv = iv;
        this.ciphertext = ciphertext;
        this.savedAt = savedAt;
    }

    public String getId() {
        return id;
    }

    public String getIv() {
        return iv;
    }

    public String getCiphertext() {
        return ciphertext;
    }

    public long getSavedAt() {
        return savedAt;
    }

    public void update(String iv, String ciphertext, long savedAt) {
        this.iv = iv;
        this.ciphertext = ciphertext;
        this.savedAt = savedAt;
    }
}
