package com.halffifty.api.controller;

import com.halffifty.api.dto.AnalyzeRequest;
import com.halffifty.api.dto.AnalyzeResponse;
import com.halffifty.api.service.AgentClient;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

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
@CrossOrigin(origins = "http://localhost:5173")
public class ContractController {

    private final AgentClient agentClient;

    public ContractController(AgentClient agentClient) {
        this.agentClient = agentClient;
    }

    @PostMapping("/analyze")
    public AnalyzeResponse analyze(@RequestBody AnalyzeRequest request) {
        return agentClient.analyze(request);
    }
}
