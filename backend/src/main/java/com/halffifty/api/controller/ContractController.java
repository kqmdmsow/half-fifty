package com.halffifty.api.controller;

import com.halffifty.api.dto.AnalyzeRequest;
import com.halffifty.api.dto.AnalyzeResponse;
import com.halffifty.api.service.AgentClient;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

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
            @RequestParam(value = "persona", defaultValue = "adult") String persona)
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
        if (!"adult".equals(persona) && !"senior".equals(persona)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "지원하지 않는 페르소나입니다.");
        }
        return agentClient.analyzePdf(bytes, file.getOriginalFilename(), persona);
    }
}
