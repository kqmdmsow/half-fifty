package com.halffifty.api.service;

import com.halffifty.api.dto.AnalyzeRequest;
import com.halffifty.api.dto.AnalyzeResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.stereotype.Service;
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
        MultipartBodyBuilder builder = new MultipartBodyBuilder();
        builder.part("file", new ByteArrayResource(pdfBytes) {
                    @Override
                    public String getFilename() {
                        return filename;
                    }
                })
                .contentType(MediaType.APPLICATION_PDF);
        builder.part("persona", persona);

        return restClient.post()
                .uri("/analyze-pdf")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(builder.build())
                .retrieve()
                .body(AnalyzeResponse.class);
    }
}
