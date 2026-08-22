package com.halffifty.api.controller;

import com.halffifty.api.dto.AnalyzeRequest;
import com.halffifty.api.dto.AnalyzeResponse;
import com.halffifty.api.service.AgentClient;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

/**
 * 계약서 분석 API.
 *
 * 프론트(React, localhost:5173) -> 백엔드(8080) -> 에이전트(8000) 흐름의 관문.
 *
 * TODO(동훈):
 *  - JWT 인증 필터 적용
 *  - 계약 문서 저장 (MySQL) 및 분석 이력 조회 API
 *  - CORS 설정을 WebMvcConfigurer로 분리 (지금은 개발용으로 컨트롤러에 임시 지정)
 */
@RestController
@RequestMapping("/api/contracts")
@CrossOrigin(origins = "${cors.allowed-origin:http://localhost:5173}")
public class ContractController {

    private final AgentClient agentClient;

    public ContractController(AgentClient agentClient) {
        this.agentClient = agentClient;
    }

    @PostMapping("/analyze")
    public AnalyzeResponse analyze(@RequestBody AnalyzeRequest request) {
        return agentClient.analyze(request);
    }

    /**
     * 조항별 점진 스트리밍 분석 (NDJSON 프록시). 에이전트 /analyze-stream을
     * 그대로 중계한다 — 조항이 끝나는 대로 프론트에 결과가 도착한다.
     */
    @PostMapping(value = "/analyze-stream", produces = "application/x-ndjson")
    public ResponseEntity<StreamingResponseBody> analyzeStream(@RequestBody AnalyzeRequest request) {
        StreamingResponseBody body = out -> agentClient.streamAnalyze(request, out);
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("application/x-ndjson"))
                .body(body);
    }

    /** 이해 확인 퀴즈 프록시 (#92) — 에이전트 /quiz 중계. */
    @PostMapping("/quiz")
    public String quiz(@RequestBody String request) {
        return agentClient.quiz(request);
    }

    /** 재설명 프록시 (#76) — 에이전트 /reexplain 중계. */
    @PostMapping("/reexplain")
    public String reexplain(@RequestBody String request) {
        return agentClient.reexplain(request);
    }

    /** 업로드 허용 최대 크기 (application.yml multipart 한도와 함께 이중 방어). */
    private static final long MAX_PDF_BYTES = 10 * 1024 * 1024;

    /**
     * PDF 업로드 분석. 전문가 자문 §7 반영:
     * - 모든 요청 백엔드 경유 (프론트→에이전트 직통 제거)
     * - 파일 형식(매직 바이트)·용량 검사
     * - 파일은 메모리에서만 중계, 저장하지 않음
     */
    @PostMapping(value = "/analyze-pdf", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public AnalyzeResponse analyzePdf(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "persona", defaultValue = "adult") String persona,
            @RequestParam(value = "language", defaultValue = "ko") String language,
            @RequestParam(value = "domain", defaultValue = "") String domain)
            throws IOException {
        if (file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "파일이 비어 있습니다.");
        }
        if (file.getSize() > MAX_PDF_BYTES) {
            throw new ResponseStatusException(
                    HttpStatus.PAYLOAD_TOO_LARGE, "PDF는 10MB 이하만 지원합니다.");
        }
        byte[] bytes = file.getBytes();
        // 매직 바이트 검사 — Content-Type 헤더는 위조 가능하므로 실제 바이트로 판별
        if (bytes.length < 5
                || !new String(bytes, 0, 5, StandardCharsets.US_ASCII).startsWith("%PDF-")) {
            throw new ResponseStatusException(
                    HttpStatus.UNSUPPORTED_MEDIA_TYPE, "PDF 파일이 아닙니다.");
        }
        if (!"adult".equals(persona) && !"senior".equals(persona) && !"foreigner".equals(persona)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "지원하지 않는 페르소나입니다.");
        }
        return agentClient.analyzePdf(bytes, file.getOriginalFilename(), persona, language, domain);
    }

    /**
     * 계약서 사진 업로드 분석 (OCR). 매직 바이트로 jpg/png/webp 판별 —
     * Content-Type 헤더 위조 방어는 analyze-pdf와 동일 원칙.
     */
    @PostMapping(value = "/analyze-image", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public AnalyzeResponse analyzeImage(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "persona", defaultValue = "adult") String persona,
            @RequestParam(value = "language", defaultValue = "ko") String language,
            @RequestParam(value = "domain", defaultValue = "") String domain)
            throws IOException {
        if (file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "파일이 비어 있습니다.");
        }
        if (file.getSize() > MAX_PDF_BYTES) {
            throw new ResponseStatusException(
                    HttpStatus.PAYLOAD_TOO_LARGE, "이미지는 10MB 이하만 지원합니다.");
        }
        byte[] bytes = file.getBytes();
        MediaType type = sniffImageType(bytes);
        if (type == null) {
            throw new ResponseStatusException(
                    HttpStatus.UNSUPPORTED_MEDIA_TYPE, "jpg/png/webp 이미지만 지원합니다.");
        }
        if (!"adult".equals(persona) && !"senior".equals(persona) && !"foreigner".equals(persona)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "지원하지 않는 페르소나입니다.");
        }
        return agentClient.analyzeImage(bytes, file.getOriginalFilename(), type, persona, language, domain);
    }

    /**
     * 파일(PDF·사진) 업로드의 조항별 점진 스트리밍 (NDJSON 프록시).
     * 검증(용량·매직 바이트·페르소나)은 기존 파일 엔드포인트와 동일하게 스트림을
     * 열기 전에 수행하고, 통과하면 에이전트 /analyze-file-stream을 그대로 중계한다.
     */
    @PostMapping(value = "/analyze-file-stream", consumes = MediaType.MULTIPART_FORM_DATA_VALUE,
            produces = "application/x-ndjson")
    public ResponseEntity<StreamingResponseBody> analyzeFileStream(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "persona", defaultValue = "adult") String persona,
            @RequestParam(value = "language", defaultValue = "ko") String language,
            @RequestParam(value = "domain", defaultValue = "") String domain)
            throws IOException {
        if (file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "파일이 비어 있습니다.");
        }
        if (file.getSize() > MAX_PDF_BYTES) {
            throw new ResponseStatusException(
                    HttpStatus.PAYLOAD_TOO_LARGE, "파일은 10MB 이하만 지원합니다.");
        }
        byte[] bytes = file.getBytes();
        boolean isPdf = bytes.length >= 5
                && new String(bytes, 0, 5, StandardCharsets.US_ASCII).startsWith("%PDF-");
        MediaType imageType = isPdf ? null : sniffImageType(bytes);
        if (!isPdf && imageType == null) {
            throw new ResponseStatusException(
                    HttpStatus.UNSUPPORTED_MEDIA_TYPE, "PDF 또는 jpg/png/webp 파일만 지원합니다.");
        }
        if (!"adult".equals(persona) && !"senior".equals(persona) && !"foreigner".equals(persona)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "지원하지 않는 페르소나입니다.");
        }
        MediaType contentType = isPdf ? MediaType.APPLICATION_PDF : imageType;
        String filename = file.getOriginalFilename();
        StreamingResponseBody body = out -> agentClient.streamAnalyzeFile(
                bytes, filename, contentType, persona, language, domain, out);
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("application/x-ndjson"))
                .body(body);
    }

    /**
     * 교육 콘텐츠 프록시 (#104) — 정적 번역본이 있는 언어는 번역해서 반환.
     * 내장 챗봇(#103)은 세션당 대화 상한·인젝션 방어 조건을 걸고 나서
     * 별도 PR로 합류한다.
     */
    @org.springframework.web.bind.annotation.GetMapping("/learn")
    public String learn(
            @org.springframework.web.bind.annotation.RequestParam(defaultValue = "ko") String language) {
        return agentClient.learn(language);
    }

    /** 매직 바이트로 이미지 형식 판별. 미지원 형식은 null. */
    private static MediaType sniffImageType(byte[] b) {
        if (b.length >= 3 && (b[0] & 0xFF) == 0xFF && (b[1] & 0xFF) == 0xD8 && (b[2] & 0xFF) == 0xFF) {
            return MediaType.IMAGE_JPEG;
        }
        if (b.length >= 4 && (b[0] & 0xFF) == 0x89 && b[1] == 'P' && b[2] == 'N' && b[3] == 'G') {
            return MediaType.IMAGE_PNG;
        }
        if (b.length >= 12 && b[0] == 'R' && b[1] == 'I' && b[2] == 'F' && b[3] == 'F'
                && b[8] == 'W' && b[9] == 'E' && b[10] == 'B' && b[11] == 'P') {
            return MediaType.parseMediaType("image/webp");
        }
        return null;
    }
}
