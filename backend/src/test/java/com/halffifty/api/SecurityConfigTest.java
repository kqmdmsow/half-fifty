package com.halffifty.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

/**
 * 로그인 도입이 "로그인 없이 쓰는 제품"을 깨지 않았는지 지키는 계약 테스트 (#102).
 *
 * <p>에이전트가 떠 있지 않으므로 200을 기대하지 않는다 — 요점은 인증 때문에
 * 막히지(401/403) 않아야 한다는 것.
 */
@SpringBootTest
@AutoConfigureMockMvc
class SecurityConfigTest {

    @Autowired MockMvc mvc;

    private void 인증없이_막히지_않는다(int status) {
        assertThat(status).isNotIn(401, 403);
    }

    @Test
    void 헬스체크는_공개() throws Exception {
        인증없이_막히지_않는다(mvc.perform(get("/health")).andReturn().getResponse().getStatus());
    }

    @Test
    void 계약_분석은_로그인_없이_가능() throws Exception {
        인증없이_막히지_않는다(mvc.perform(post("/api/contracts/analyze")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"text\":\"제1조 테스트\",\"persona\":\"adult\"}"))
                .andReturn().getResponse().getStatus());
    }

    @Test
    void 교육_콘텐츠와_챗봇도_로그인_없이_가능() throws Exception {
        인증없이_막히지_않는다(mvc.perform(get("/api/contracts/learn"))
                .andReturn().getResponse().getStatus());
        인증없이_막히지_않는다(mvc.perform(post("/api/contracts/learn-chat")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"question\":\"신탁이 뭔가요\",\"language\":\"ko\"}"))
                .andReturn().getResponse().getStatus());
    }
}
