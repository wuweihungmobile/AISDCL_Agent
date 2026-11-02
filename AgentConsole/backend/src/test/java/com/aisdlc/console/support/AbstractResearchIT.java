package com.aisdlc.console.support;

import com.aisdlc.console.application.service.ResearchQueryService;
import com.aisdlc.console.domain.model.auth.Role;
import com.aisdlc.console.infrastructure.security.JwtTokenService;
import com.aisdlc.minibridge.MiniResearch;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Import;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 研究整合測試的共同基底（TCS-ResearchToPRD-P0 §5）：沿 {@link AbstractExecutionIT} 的完整 context、真 PostgreSQL 與迷你 Bridge（含研究面 {@link MiniResearch}），
 * 另以 {@link ResearchSeam} 提供可切換的研究寫入權杖與可縮短的讀取逾時。每個測試開始前與結束後：重設迷你 Bridge 的研究旋鈕、權杖覆寫與讀取逾時，並丟棄 console-api 的
 * 能力探針快取（30 秒快取會把上一個測試的 {@code web_layer_enabled} 帶進下一個測試）。研究表的資料由 {@link ResearchFixtures} 直接寫入（測試扮演唯一的寫入者 Bridge）。
 */
@Import(ResearchSeam.class)
public abstract class AbstractResearchIT extends AbstractExecutionIT {

    @Autowired
    protected ResearchSeam.SwitchableEndpoints endpoints;
    @Autowired
    protected SiWriteSeam.ReadTimeoutCap readTimeout;
    @Autowired
    protected ResearchQueryService researchQuery;
    @Autowired
    protected JwtTokenService jwt;

    protected ResearchFixtures fx;

    @BeforeEach
    void resetResearchFixtures() {
        fx = new ResearchFixtures(jdbc);
        MINI.research.reset();
        endpoints.reset();
        readTimeout.reset();
        researchQuery.invalidateCapabilities();
    }

    @AfterEach
    void restoreResearchFixtures() {
        MINI.research.reset();
        endpoints.reset();
        readTimeout.reset();
        researchQuery.invalidateCapabilities();
    }

    protected static final String RESEARCH = "/api/v1/research";

    protected MiniResearch bridge() {
        return MINI.research;
    }

    /** 以任意帳號名鑄 ADMIN 角色的 access token（approver、decided_by 只取 JWT subject 的案例用；{@link #admin()} 的帳號名是 {@code admin}）。 */
    protected String adminAs(String username) {
        return jwt.issue(username, Role.ADMIN).accessToken();
    }

    protected long rows(String table) {
        Long count = jdbc.queryForObject("select count(*) from console." + table, Long.class);
        return count == null ? 0 : count;
    }

    /** 合法的建立請求本文（四層：academic 與 oss 開）。 */
    protected static Map<String, Object> validCreate(String slug) {
        Map<String, Object> layers = new LinkedHashMap<>();
        layers.put("academic", true);
        layers.put("industry", false);
        layers.put("oss", true);
        layers.put("community", false);
        Map<String, Object> scope = new LinkedHashMap<>();
        scope.put("layers", layers);
        scope.put("inScope", java.util.List.of("範圍內一項"));
        scope.put("recencyYears", 2);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("slug", slug);
        body.put("title", "研究標題");
        body.put("topic", "研究議題");
        body.put("scope", scope);
        body.put("depthLevel", "STANDARD");
        return body;
    }
}
