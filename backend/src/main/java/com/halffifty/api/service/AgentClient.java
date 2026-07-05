package com.halffifty.api.service;

import com.halffifty.api.dto.AnalyzeRequest;
import com.halffifty.api.dto.AnalyzeResponse;
import org.springframework.beans.factory.annotation.Value;
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
}
