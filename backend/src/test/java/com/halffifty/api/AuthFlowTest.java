package com.halffifty.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

/** 로그인 · 영지식 기록 보관 흐름 (#102). */
@SpringBootTest
@AutoConfigureMockMvc
class AuthFlowTest {

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;

    /** authProof는 클라이언트가 비밀번호에서 파생한 값 — 테스트에서는 고정 문자열. */
    private String credentials(String email) {
        return """
                {"email":"%s","authProof":"ZGVyaXZlZC1hdXRoLXByb29mLWZvci10ZXN0aW5nLTEyMw=="}
                """.formatted(email);
    }

    private String signup(String email) throws Exception {
        String body = mvc.perform(post("/api/auth/signup").contentType(MediaType.APPLICATION_JSON)
                        .content(credentials(email)))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        return json.readTree(body).get("token").asText();
    }

    private String envelope(String ciphertext) {
        return """
                {"iv":"YWJjZGVmZ2hpamts","ciphertext":"%s","savedAt":1700000000000}
                """.formatted(ciphertext);
    }

    private JsonNode listRecords(String token) throws Exception {
        return json.readTree(mvc.perform(get("/api/records").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString());
    }

    @Test
    void 가입_저장_갱신_삭제_흐름() throws Exception {
        String token = signup("flow@example.com");

        mvc.perform(put("/api/records/rec_1").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content(envelope("Y2lwaGVy")))
                .andExpect(status().isCreated());
        JsonNode saved = listRecords(token);
        assertThat(saved).hasSize(1);
        assertThat(saved.get(0).get("ciphertext").asText()).isEqualTo("Y2lwaGVy");

        // 같은 id로 다시 저장하면 갱신 — 중복 생성이 아니다
        mvc.perform(put("/api/records/rec_1").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content(envelope("dXBkYXRlZA==")))
                .andExpect(status().isNoContent());
        assertThat(listRecords(token)).hasSize(1);

        mvc.perform(delete("/api/records/rec_1").header("Authorization", "Bearer " + token))
                .andExpect(status().isNoContent());
        assertThat(listRecords(token)).isEmpty();
    }

    @Test
    void 남의_기록은_id를_알아도_볼_수_없다() throws Exception {
        String mine = signup("owner@example.com");
        String other = signup("stranger@example.com");
        mvc.perform(put("/api/records/secret_1").header("Authorization", "Bearer " + mine)
                        .contentType(MediaType.APPLICATION_JSON).content(envelope("bWluZQ==")))
                .andExpect(status().isCreated());

        assertThat(listRecords(other)).isEmpty();
        // 남의 id로 삭제를 시도해도 원 소유자 기록은 그대로
        mvc.perform(delete("/api/records/secret_1").header("Authorization", "Bearer " + other))
                .andExpect(status().isNoContent());
        assertThat(listRecords(mine)).hasSize(1);
    }

    @Test
    void 토큰_없으면_기록에_접근_불가() throws Exception {
        assertThat(mvc.perform(get("/api/records")).andReturn().getResponse().getStatus())
                .isIn(401, 403);
    }

    @Test
    void 중복_가입은_409_틀린_증명은_401() throws Exception {
        signup("dup@example.com");
        mvc.perform(post("/api/auth/signup").contentType(MediaType.APPLICATION_JSON)
                        .content(credentials("dup@example.com")))
                .andExpect(status().isConflict());
        mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"email":"dup@example.com","authProof":"d3JvbmctcHJvb2YtdmFsdWUtaGVyZS0xMjM0NTY3"}
                                """))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 없는_계정_로그인도_같은_401_가입여부가_새지_않는다() throws Exception {
        mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content(credentials("nobody@example.com")))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void 탈퇴하면_계정과_기록이_함께_사라진다() throws Exception {
        String token = signup("quit@example.com");
        mvc.perform(put("/api/records/rec_q").header("Authorization", "Bearer " + token)
                        .contentType(MediaType.APPLICATION_JSON).content(envelope("Ynll")))
                .andExpect(status().isCreated());
        mvc.perform(delete("/api/auth/me").header("Authorization", "Bearer " + token))
                .andExpect(status().isNoContent());

        // 같은 이메일로 재가입해도 이전 기록이 딸려오지 않는다
        assertThat(listRecords(signup("quit@example.com"))).isEmpty();
    }
}
