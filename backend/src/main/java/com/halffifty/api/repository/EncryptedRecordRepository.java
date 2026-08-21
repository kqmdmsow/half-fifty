package com.halffifty.api.repository;

import com.halffifty.api.domain.Account;
import com.halffifty.api.domain.EncryptedRecord;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface EncryptedRecordRepository extends JpaRepository<EncryptedRecord, String> {
    List<EncryptedRecord> findByAccountOrderBySavedAtDesc(Account account);

    /** id만으로 찾지 않는다 — 남의 기록 id를 알아도 접근할 수 없게 계정을 함께 건다. */
    Optional<EncryptedRecord> findByIdAndAccount(String id, Account account);

    long countByAccount(Account account);

    void deleteByAccount(Account account);
}
