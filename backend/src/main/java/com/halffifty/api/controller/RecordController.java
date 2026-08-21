package com.halffifty.api.controller;

import com.halffifty.api.domain.Account;
import com.halffifty.api.domain.EncryptedRecord;
import com.halffifty.api.repository.AccountRepository;
import com.halffifty.api.repository.EncryptedRecordRepository;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.security.Principal;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/**
 * 기록 동기화 (#102) — 서버는 암호문 봉투만 받고, 열지 않는다.
 *
 * <p>요청·응답 어디에도 계약 내용이나 그 메타데이터(도메인·위험 건수)가 없다.
 * 목록에 필요한 정보는 클라이언트가 복호화해서 만든다.
 */
@RestController
@RequestMapping("/api/records")
public class RecordController {

    /** 계정당 보관 상한 — 무제한 업로드로 저장소를 잠식하지 않게. */
    private static final long MAX_PER_ACCOUNT = 50;

    private final AccountRepository accounts;
    private final EncryptedRecordRepository records;

    public RecordController(AccountRepository accounts, EncryptedRecordRepository records) {
        this.accounts = accounts;
        this.records = records;
    }

    public record Envelope(
            @NotBlank @Size(max = 32) String iv,
            @NotBlank @Size(max = 2_000_000) String ciphertext,
            long savedAt) {}

    public record StoredEnvelope(String id, String iv, String ciphertext, long savedAt) {}

    @GetMapping
    public List<StoredEnvelope> list(Principal principal) {
        return records.findByAccountOrderBySavedAtDesc(account(principal)).stream()
                .map(r -> new StoredEnvelope(r.getId(), r.getIv(), r.getCiphertext(), r.getSavedAt()))
                .toList();
    }

    @PutMapping("/{id}")
    @Transactional
    public ResponseEntity<Void> upsert(
            @PathVariable String id, @Valid @RequestBody Envelope body, Principal principal) {
        Account account = account(principal);
        var existing = records.findByIdAndAccount(id, account);
        if (existing.isPresent()) {
            existing.get().update(body.iv(), body.ciphertext(), body.savedAt());
            return ResponseEntity.noContent().build();
        }
        if (records.countByAccount(account) >= MAX_PER_ACCOUNT) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT, "보관함이 가득 찼어요. 오래된 기록을 지운 뒤 저장해주세요.");
        }
        records.save(new EncryptedRecord(id, account, body.iv(), body.ciphertext(), body.savedAt()));
        return ResponseEntity.status(HttpStatus.CREATED).build();
    }

    @DeleteMapping("/{id}")
    @Transactional
    public ResponseEntity<Void> delete(@PathVariable String id, Principal principal) {
        records.findByIdAndAccount(id, account(principal)).ifPresent(records::delete);
        return ResponseEntity.noContent().build();
    }

    private Account account(Principal principal) {
        return accounts.findByEmail(principal.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED));
    }
}
