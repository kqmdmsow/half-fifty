package com.halffifty.api.service;

import com.halffifty.api.dto.AnalyzeRequest;
import com.halffifty.api.dto.AnalyzeResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;

/**
 * Python Agent Service(FastAPI) 호출 클라이언트.
 *
 * TODO(동훈):
 *  - 타임아웃/재시도 설정
 *  - 비동기 처리 (분석이 오래 걸릴 경우 @Async 또는 작업 큐)
 *  - 에러 응답 표준화 (@ControllerAdvice)
 */
@Service
public class AgentClient {

    private final RestClient restClient;

    public AgentClient(@Value("${agent.base-url}") String agentBaseUrl) {
        this.restClient = RestClient.builder()
                .baseUrl(agentBaseUrl)
                .build();
    }

    public AnalyzeResponse analyze(AnalyzeRequest request) {
        return restClient.post()
                .uri("/analyze")
                .body(request)
                .retrieve()
                .body(AnalyzeResponse.class);
    }

    /**
     * PDF 업로드 프록시. 전문가 자문 §7 반영 — 모든 요청이 백엔드를 거치도록
     * 프론트→에이전트 직통 경로를 제거하고 이 메서드로 일원화한다.
     * 파일은 메모리에서만 전달하며 백엔드에 저장하지 않는다.
     */
    public AnalyzeResponse analyzePdf(byte[] pdfBytes, String filename, String persona) {
        return forwardFile("/analyze-pdf", pdfBytes, filename, MediaType.APPLICATION_PDF, persona);
    }

    /** 계약서 사진(OCR) 프록시 — 에이전트 /analyze-image로 전달. */
    public AnalyzeResponse analyzeImage(
            byte[] imageBytes, String filename, MediaType contentType, String persona) {
        return forwardFile("/analyze-image", imageBytes, filename, contentType, persona);
    }

    private AnalyzeResponse forwardFile(
            String uri, byte[] bytes, String filename, MediaType contentType, String persona) {
        // MultipartBodyBuilder는 내부에서 reactive-streams(Publisher)를 참조해
        // WebFlux 없는 클래스패스에서는 NoClassDefFoundError로 죽는다 —
        // 블로킹 스택 표준인 MultiValueMap + HttpEntity 방식으로 구성한다.
        ByteArrayResource fileResource = new ByteArrayResource(bytes) {
            @Override
            public String getFilename() {
                return filename;
            }
        };
        HttpHeaders fileHeaders = new HttpHeaders();
        fileHeaders.setContentType(contentType);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new HttpEntity<>(fileResource, fileHeaders));
        body.add("persona", persona);

        return restClient.post()
                .uri(uri)
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(body)
                .retrieve()
                .body(AnalyzeResponse.class);
    }
}
