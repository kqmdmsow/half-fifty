package com.halffifty.api.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.halffifty.api.dto.AnalyzeRequest;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
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
    private final String agentBaseUrl;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient = HttpClient.newHttpClient();

    public AgentClient(@Value("${agent.base-url}") String agentBaseUrl, ObjectMapper objectMapper) {
        this.agentBaseUrl = agentBaseUrl;
        this.objectMapper = objectMapper;
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
    public AnalyzeResponse analyzePdf(byte[] pdfBytes, String filename, String persona, String language,
            String domain) {
        return forwardFile("/analyze-pdf", pdfBytes, filename, MediaType.APPLICATION_PDF, persona, language, domain);
    }

    /** 계약서 사진(OCR) 프록시 — 에이전트 /analyze-image로 전달. */
    public AnalyzeResponse analyzeImage(
            byte[] imageBytes, String filename, MediaType contentType, String persona, String language,
            String domain) {
        return forwardFile("/analyze-image", imageBytes, filename, contentType, persona, language, domain);
    }

    private AnalyzeResponse forwardFile(
            String uri, byte[] bytes, String filename, MediaType contentType, String persona,
            String language, String domain) {
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
        body.add("language", language == null ? "ko" : language);
        body.add("domain", domain == null ? "" : domain);

        return restClient.post()
                .uri(uri)
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(body)
                .retrieve()
                .body(AnalyzeResponse.class);
    }

    /**
     * 조항별 점진 스트리밍 프록시 — 에이전트 /analyze-stream의 NDJSON을
     * 버퍼링 없이 곧바로 클라이언트로 흘려보낸다. RestClient는 응답 스트리밍을
     * 지원하지 않아 JDK HttpClient를 사용한다.
     */
    public void streamAnalyze(AnalyzeRequest request, OutputStream out) throws IOException {
        try {
            HttpRequest httpRequest = HttpRequest.newBuilder(URI.create(agentBaseUrl + "/analyze-stream"))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(request)))
                    .build();
            HttpResponse<InputStream> response =
                    httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofInputStream());
            try (InputStream in = response.body()) {
                byte[] buffer = new byte[8192];
                int read;
                while ((read = in.read(buffer)) != -1) {
                    out.write(buffer, 0, read);
                    out.flush(); // 조항 단위 이벤트가 즉시 전달되도록 청크마다 플러시
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("에이전트 스트리밍 중단", e);
        }
    }
}
