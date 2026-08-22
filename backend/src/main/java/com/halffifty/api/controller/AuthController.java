package com.halffifty.api.controller;

import com.halffifty.api.domain.Account;
import com.halffifty.api.repository.AccountRepository;
import com.halffifty.api.repository.EncryptedRecordRepository;
import com.halffifty.api.security.JwtService;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import jakarta.validation.Valid;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/**
 * 로그인·회원가입 (#102).
 *
 * <p><b>서버는 비밀번호도, 복호화 키도 받지 않는다.</b> 클라이언트가 비밀번호에서
 * PBKDF2로 두 값을 파생해 인증 증명(authProof)만 보내고, 암호화 키는 기기에
 * 남는다(frontend/src/crypto.ts). 서버는 authProof를 BCrypt로 한 번 더 해싱해
 * 저장하므로, DB가 유출돼도 저장된 기록을 열 수 없다.
 *
 * <p>이 설계 덕분에 "서버 무저장" 원칙이 로그인 도입 후에도 유지된다 — 서버가
 * 보관하는 것은 계약 내용이 아니라 열 수 없는 봉투다.
 */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private static final Logger log = LoggerFactory.getLogger(AuthController.class);

    /** 무차별 대입 완화 — 이메일당 15분에 10회. 서버 재시작 시 초기화되는 경량 방어. */
    private static final int MAX_ATTEMPTS = 10;
    private static final Duration WINDOW = Duration.ofMinutes(15);

    private final AccountRepository accounts;
    private final EncryptedRecordRepository records;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final Map<String, Attempts> attempts = new ConcurrentHashMap<>();

    public AuthController(
            AccountRepository accounts,
            EncryptedRecordRepository records,
            PasswordEncoder passwordEncoder,
            JwtService jwtService) {
        this.accounts = accounts;
        this.records = records;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
    }

    public record Credentials(
            @Email @NotBlank @Size(max = 320) String email,
            /** 비밀번호가 아니라 클라이언트가 파생한 인증 증명(base64, 44자). */
            @NotBlank @Size(min = 32, max = 200) String authProof) {}

    public record TokenResponse(String token, String email) {}

    @PostMapping("/signup")
    @Transactional
    public TokenResponse signup(@Valid @RequestBody Credentials body) {
        String email = normalize(body.email());
        if (accounts.existsByEmail(email)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "이미 가입된 이메일이에요.");
        }
        accounts.save(new Account(email, passwordEncoder.encode(body.authProof())));
        log.info("계정 생성"); // 이메일은 로그에 남기지 않는다 (#58 개인정보 처리 원칙)
        return new TokenResponse(jwtService.issue(email), email);
    }

    @PostMapping("/login")
    public TokenResponse login(@Valid @RequestBody Credentials body) {
        String email = normalize(body.email());
        if (isBlocked(email)) {
            throw new ResponseStatusException(
                    HttpStatus.TOO_MANY_REQUESTS, "시도가 너무 많아요. 잠시 후 다시 해주세요.");
        }
        Account account = accounts.findByEmail(email).orElse(null);
        // 계정 없음과 비밀번호 틀림을 같은 응답으로 — 가입 여부가 새어나가지 않게.
        if (account == null || !passwordEncoder.matches(body.authProof(), account.getAuthHash())) {
            recordFailure(email);
            throw new ResponseStatusException(
                    HttpStatus.UNAUTHORIZED, "이메일 또는 비밀번호가 맞지 않아요.");
        }
        attempts.remove(email);
        return new TokenResponse(jwtService.issue(email), email);
    }

    /** 탈퇴 — 계정과 보관 중인 암호문을 함께 삭제한다(무저장 원칙의 마무리). */
    @DeleteMapping("/me")
    @Transactional
    public ResponseEntity<Void> deleteAccount(java.security.Principal principal) {
        Account account = accounts.findByEmail(principal.getName())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED));
        records.deleteByAccount(account);
        accounts.delete(account);
        return ResponseEntity.noContent().build();
    }

    private static String normalize(String email) {
        return email.trim().toLowerCase();
    }

    private boolean isBlocked(String email) {
        Attempts a = attempts.get(email);
        return a != null && a.count.get() >= MAX_ATTEMPTS && !a.expired();
    }

    private void recordFailure(String email) {
        attempts.compute(email, (k, a) -> (a == null || a.expired()) ? new Attempts() : a).count.incrementAndGet();
    }

    private static final class Attempts {
        final Instant since = Instant.now();
        final AtomicInteger count = new AtomicInteger();

        boolean expired() {
            return since.plus(WINDOW).isBefore(Instant.now());
        }
    }
}
