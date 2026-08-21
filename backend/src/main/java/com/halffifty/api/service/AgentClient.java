package com.halffifty.api.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.halffifty.api.dto.AnalyzeRequest;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import com.halffifty.api.dto.AnalyzeResponse;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.ClientHttpRequestFactories;
import org.springframework.boot.web.client.ClientHttpRequestFactorySettings;
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
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build(); // 스트리밍은 읽기 타임아웃 없음 — async 600s(application.yml)가 상한

    public AgentClient(@Value("${agent.base-url}") String agentBaseUrl, ObjectMapper objectMapper) {
        this.agentBaseUrl = agentBaseUrl;
        this.objectMapper = objectMapper;
        // 타임아웃 (#52): 미설정 시 에이전트가 죽으면 요청이 무한 대기했다.
        // read 7분 = 최악 케이스(21조항 + judge 재시도 2회 ≈ 5분) + 여유.
        ClientHttpRequestFactorySettings settings = ClientHttpRequestFactorySettings.DEFAULTS
                .withConnectTimeout(Duration.ofSeconds(10))
                .withReadTimeout(Duration.ofMinutes(7));
        this.restClient = RestClient.builder()
                .baseUrl(agentBaseUrl)
                .requestFactory(ClientHttpRequestFactories.get(settings))
                .build();
    }

    public AnalyzeResponse analyze(AnalyzeRequest request) {
        return restClient.post()
                .uri("/analyze")
                .body(request)
                .retrieve()
                .body(AnalyzeResponse.class);
    }

    /** 교육 콘텐츠 프록시 (#104). */
    public String learn(String language) {
        return restClient.get()
                .uri(uriBuilder -> uriBuilder.path("/learn")
                        .queryParam("language", language == null ? "ko" : language).build())
                .retrieve().body(String.class);
    }

    /** 교육 챗봇 프록시 (#103). */
    public String learnChat(String requestJson) {
        return restClient.post()
                .uri("/learn-chat")
                .header("Content-Type", "application/json")
                .body(requestJson)
                .retrieve()
                .body(String.class);
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
        HttpRequest httpRequest = HttpRequest.newBuilder(URI.create(agentBaseUrl + "/analyze-stream"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(request)))
                .build();
        pipeStream(httpRequest, out);
    }

    /**
     * 파일(PDF·사진) 스트리밍 프록시 — 에이전트 /analyze-file-stream으로 multipart
     * 전송 후 NDJSON을 그대로 중계한다. JDK HttpClient는 multipart를 지원하지
     * 않으므로 바디를 직접 조립한다 (파일은 메모리에서만 전달, 저장하지 않음).
     */
    public void streamAnalyzeFile(byte[] bytes, String filename, MediaType contentType,
            String persona, String language, String domain, OutputStream out) throws IOException {
        String boundary = "----jomokjomok" + UUID.randomUUID();
        // 파일명은 multipart 헤더 문법을 깨는 문자(따옴표·개행)만 치환해 전달
        String safeName = (filename == null || filename.isBlank() ? "upload" : filename)
                .replaceAll("[\"\\r\\n]", "_");

        ByteArrayOutputStream body = new ByteArrayOutputStream();
        writeFormField(body, boundary, "persona", persona);
        writeFormField(body, boundary, "language", language == null ? "ko" : language);
        writeFormField(body, boundary, "domain", domain == null ? "" : domain);
        body.write(("--" + boundary + "\r\n"
                + "Content-Disposition: form-data; name=\"file\"; filename=\"" + safeName + "\"\r\n"
                + "Content-Type: " + contentType + "\r\n\r\n").getBytes(StandardCharsets.UTF_8));
        body.write(bytes);
        body.write(("\r\n--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8));

        HttpRequest httpRequest = HttpRequest.newBuilder(URI.create(agentBaseUrl + "/analyze-file-stream"))
                .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                .POST(HttpRequest.BodyPublishers.ofByteArray(body.toByteArray()))
                .build();
        pipeStream(httpRequest, out);
    }

    private static void writeFormField(ByteArrayOutputStream body, String boundary,
            String name, String value) throws IOException {
        body.write(("--" + boundary + "\r\n"
                + "Content-Disposition: form-data; name=\"" + name + "\"\r\n\r\n"
                + value + "\r\n").getBytes(StandardCharsets.UTF_8));
    }

    /** 교육 콘텐츠 프록시 (#104). */
    public String learn() {
        return restClient.get().uri("/learn").retrieve().body(String.class);
    }

    /** 요청을 보내고 응답 바디를 버퍼링 없이 클라이언트로 흘려보낸다. */
    private void pipeStream(HttpRequest httpRequest, OutputStream out) throws IOException {
        try {
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
