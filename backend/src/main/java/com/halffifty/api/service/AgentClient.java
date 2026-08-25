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
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
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

    /** 에이전트가 백엔드 경유 여부를 판별하는 헤더 (#174). */
    private static final String SERVICE_TOKEN_HEADER = "X-Service-Token";

    private final RestClient restClient;
    private final String agentBaseUrl;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build(); // 스트리밍은 읽기 타임아웃 없음 — async 600s(application.yml)가 상한

    /**
     * 에이전트 서비스 토큰 (#174). 에이전트가 공개 URL이면 프론트→백엔드→에이전트
     * 구조를 우회해 직접 때릴 수 있고, 그러면 백엔드의 용량·형식 검사가 전부
     * 무의미해진다. 미설정이면 빈 문자열이고 에이전트도 검사하지 않는다 —
     * 로컬 개발과 기존 배포가 토큰 없이도 돌아가야 하기 때문이다.
     */
    private final String serviceToken;

    public AgentClient(@Value("${agent.base-url}") String agentBaseUrl,
            @Value("${agent.service-token:}") String serviceToken,
            ObjectMapper objectMapper) {
        this.agentBaseUrl = agentBaseUrl;
        this.serviceToken = serviceToken;
        this.objectMapper = objectMapper;
        // 타임아웃 (#52): 미설정 시 에이전트가 죽으면 요청이 무한 대기했다.
        // read 7분 = 최악 케이스(21조항 + judge 재시도 2회 ≈ 5분) + 여유.
        ClientHttpRequestFactorySettings settings = ClientHttpRequestFactorySettings.DEFAULTS
                .withConnectTimeout(Duration.ofSeconds(10))
                .withReadTimeout(Duration.ofMinutes(7));
        RestClient.Builder builder = RestClient.builder()
                .baseUrl(agentBaseUrl)
                .requestFactory(ClientHttpRequestFactories.get(settings));
        if (!serviceToken.isBlank()) {
            builder = builder.defaultHeader(SERVICE_TOKEN_HEADER, serviceToken);
        }
        this.restClient = builder.build();
    }

    public AnalyzeResponse analyze(AnalyzeRequest request) {
        return restClient.post()
                .uri("/analyze")
                .body(request)
                .retrieve()
                .body(AnalyzeResponse.class);
    }

    /** 이해 확인 퀴즈 프록시 (#92) — JSON 그대로 중계. */
    public String quiz(String requestJson) {
        return restClient.post()
                .uri("/quiz")
                .header("Content-Type", "application/json")
                .body(requestJson)
                .retrieve()
                .body(String.class);
    }

    /** 재설명 프록시 (#76) — JSON 그대로 중계. */
    public String reexplain(String requestJson) {
        return restClient.post()
                .uri("/reexplain")
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
     * 설명·서명 대조 검증 프록시 (#175) — JSON 그대로 중계한다.
     *
     * <p>응답을 DTO로 받지 않고 문자열로 흘리는 이유: findings의 필드가 아직
     * 굳지 않았고, record로 받으면 매핑 안 된 필드를 조용히 버려 프론트에서만
     * 정보가 사라진다(#175에서 실제로 그 사고가 났다). 스키마가 안정되면 DTO로 옮긴다.
     */
    public String verifyDisclosure(String requestJson) {
        return restClient.post()
                .uri("/verify-disclosure")
                .header("Content-Type", "application/json")
                .body(requestJson)
                .retrieve()
                .body(String.class);
    }

    /**
     * 계약서 파일 + 상담 녹취(음성) 대조 검증 프록시 (#175).
     * 파일 두 개를 multipart로 조립해 전달한다 — 둘 다 메모리에서만 중계하고
     * 저장하지 않는다.
     */
    public String verifyDisclosureAudio(
            byte[] contract, String contractName, byte[] audio, String audioName,
            String persona, String language, String domain) throws IOException {
        String boundary = "----jomokjomok" + UUID.randomUUID();
        ByteArrayOutputStream body = new ByteArrayOutputStream();
        writeFormField(body, boundary, "persona", persona);
        writeFormField(body, boundary, "language", language);
        writeFormField(body, boundary, "domain", domain);
        writeFilePart(body, boundary, "contract", contractName, contract);
        writeFilePart(body, boundary, "audio", audioName, audio);
        body.write(("\r\n--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8));

        HttpRequest request = withServiceToken(
                HttpRequest.newBuilder(URI.create(agentBaseUrl + "/verify-disclosure-audio"))
                        .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                        .timeout(Duration.ofMinutes(9))   // 전사 + 분석 + 대조
                        .POST(HttpRequest.BodyPublishers.ofByteArray(body.toByteArray())))
                .build();
        try {
            HttpResponse<String> response =
                    httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() >= 400) {
                throw new ResponseStatusException(
                        HttpStatus.valueOf(response.statusCode()), response.body());
            }
            return response.body();
        } catch (InterruptedException exc) {
            Thread.currentThread().interrupt();
            throw new IOException("대조 검증이 중단됐습니다.", exc);
        }
    }

    /** multipart 파일 파트 조립 — 파일명의 따옴표·개행만 치환해 헤더 문법을 지킨다. */
    private static void writeFilePart(ByteArrayOutputStream body, String boundary,
            String name, String filename, byte[] bytes) throws IOException {
        String safe = (filename == null ? "upload" : filename).replaceAll("[\"\\r\\n]", "_");
        body.write(("--" + boundary + "\r\n"
                + "Content-Disposition: form-data; name=\"" + name + "\"; filename=\"" + safe + "\"\r\n"
                + "Content-Type: application/octet-stream\r\n\r\n").getBytes(StandardCharsets.UTF_8));
        body.write(bytes);
    }

    /**
     * 조항별 점진 스트리밍 프록시 — 에이전트 /analyze-stream의 NDJSON을
     * 버퍼링 없이 곧바로 클라이언트로 흘려보낸다. RestClient는 응답 스트리밍을
     * 지원하지 않아 JDK HttpClient를 사용한다.
     */
    public void streamAnalyze(AnalyzeRequest request, OutputStream out) throws IOException {
        HttpRequest httpRequest = withServiceToken(
                HttpRequest.newBuilder(URI.create(agentBaseUrl + "/analyze-stream"))
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(
                                objectMapper.writeValueAsString(request))))
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

        HttpRequest httpRequest = withServiceToken(
                HttpRequest.newBuilder(URI.create(agentBaseUrl + "/analyze-file-stream"))
                        .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                        .POST(HttpRequest.BodyPublishers.ofByteArray(body.toByteArray())))
                .build();
        pipeStream(httpRequest, out);
    }

    /** RestClient와 달리 JDK HttpClient는 기본 헤더가 없어 매번 붙여야 한다. */
    private HttpRequest.Builder withServiceToken(HttpRequest.Builder builder) {
        return serviceToken.isBlank() ? builder
                : builder.header(SERVICE_TOKEN_HEADER, serviceToken);
    }

    private static void writeFormField(ByteArrayOutputStream body, String boundary,
            String name, String value) throws IOException {
        body.write(("--" + boundary + "\r\n"
                + "Content-Disposition: form-data; name=\"" + name + "\"\r\n\r\n"
                + value + "\r\n").getBytes(StandardCharsets.UTF_8));
    }

    /** 교육 콘텐츠 프록시 (#104) — 정적 번역본이 있는 언어는 번역해서 반환. */
    public String learn(String language) {
        return restClient.get()
                .uri(uriBuilder -> uriBuilder.path("/learn")
                        .queryParam("language", language == null ? "ko" : language).build())
                .retrieve().body(String.class);
    }

    /** 교육 챗봇 프록시 (#103) — JSON 그대로 중계. 비용 상한은 컨트롤러가 처리. */
    public String learnChat(String requestJson) {
        return restClient.post()
                .uri("/learn-chat")
                .header("Content-Type", "application/json")
                .body(requestJson)
                .retrieve()
                .body(String.class);
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
