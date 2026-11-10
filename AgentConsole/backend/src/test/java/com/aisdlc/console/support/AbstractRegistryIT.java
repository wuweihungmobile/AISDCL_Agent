package com.aisdlc.console.support;

import com.aisdlc.minibridge.MiniBridge;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;

/**
 * 研究來源單一化的登記同步整合測試共同基底（TCS-ResearchRegistry §5.5）：沿 {@link AbstractSiWriteIT}，另重設迷你 Bridge 的研究旋鈕，並提供
 * {@code MINI.registry(text, sha)}（快照回放）與 {@link #mirror}（SI 鏡像的 {@code research_registry}、{@code research.registry} 事件與抓取上限）。
 * 路徑常數 {@link #REGISTRY}＝{@code /api/v1/si/research-registry}。
 */
public abstract class AbstractRegistryIT extends AbstractSiWriteIT {

    protected static final String REGISTRY = "/api/v1/si/research-registry";
    protected static final String SYNC = REGISTRY + "/sync";
    /** 「鍵缺席」哨兵（根層尚未升版）。 */
    protected static final Object DROP = MiniBridge.Si.DROP;
    protected static final String SHA_D = "sha256:" + "d".repeat(64);
    protected static final String SHA_E = "sha256:" + "e".repeat(64);
    protected static final String SHA_F = "sha256:" + "f".repeat(64);
    protected static final String T1 = "2026-10-24T10:00:00+08:00";
    protected static final String T2 = "2026-10-24T11:00:00+08:00";
    protected static final String T3 = "2026-10-24T12:00:00+08:00";
    /** 根層 TCS 附錄 B 的 golden（複本；sha256 在載入時先驗）。 */
    protected static final String APPENDIX_B = resource("appendix-b.json");
    protected static final String APPENDIX_B_SHA = "sha256:147fccd6a1b9efb61423579e26fbbc7437366a937806e239c69f334732aff0e8";

    @BeforeEach
    void resetRegistryFixtures() {
        MINI.research.reset();
        mirror(null, List.of(), DROP);
    }

    @AfterEach
    void restoreRegistryFixtures() {
        MINI.research.reset();
    }

    protected static String resource(String name) {
        try (InputStream in = AbstractRegistryIT.class.getResourceAsStream("/research-registry/" + name)) {
            if (in == null) {
                throw new IllegalStateException("找不到測試資源 research-registry/" + name);
            }
            byte[] bytes = in.readAllBytes();
            if ("appendix-b.json".equals(name) && !sha256(bytes).equals("147fccd6a1b9efb61423579e26fbbc7437366a937806e239c69f334732aff0e8")) {
                throw new IllegalStateException("附錄 B 複本的 sha256 不符（夾具漂移）");
            }
            return new String(bytes, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
    }

    protected static String sha256(byte[] bytes) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    /** Bridge 回放的登記快照（原樣）。 */
    protected void snapshot(String text, String sha) {
        MINI.research.registry(text, sha);
    }

    /** 鏡像最新已入帳的登記：{@code {seq, audit_ref, registry_sha256, watch_enabled}}。 */
    protected static Map<String, Object> latest(String auditRef, String sha) {
        return map("seq", 7, "audit_ref", auditRef, "registry_sha256", sha, "watch_enabled", 10);
    }

    /**
     * 設定 SI 鏡像：{@code status.items[0].research_registry}（{@code null}＝從未同步、{@link #DROP}＝鍵缺席、{@link #latest} 的物件）、
     * {@code status.items[0].research_fetch_max}（{@link #DROP}＝鍵缺席）與 {@code research.registry} 事件（每個已入帳 ref 一筆）。
     */
    @SuppressWarnings("unchecked")
    protected void mirror(Object researchRegistry, List<String> ingestedRefs, Object fetchMax) {
        Map<String, Object> first = ((List<Map<String, Object>>) MINI.si.payloads.get("status").get("items")).get(0);
        if (researchRegistry == DROP) {
            first.remove("research_registry");
        } else {
            first.put("research_registry", researchRegistry);
        }
        if (fetchMax == DROP) {
            first.remove("research_fetch_max");
        } else {
            first.put("research_fetch_max", fetchMax);
        }
        List<Map<String, Object>> events = new ArrayList<>();
        int seq = 1;
        for (String ref : ingestedRefs) {
            Map<String, Object> event = event(seq++, "research.registry", "console", ref, null, null);
            event.put("registry_sha256", SHA_D);
            events.add(event);
        }
        MINI.si.payloads.put("events", export("events", events, false, null));
    }

    /** 登記同步的稽核列夾具（body 為佔位 JSON；digest 為該列同步的登記 digest）。 */
    protected void insertRegistryWrite(String auditRef, String digest, String timeIso) {
        insertAudit(auditRef, "src-registry", null, digest, "{\"registry_text\":\"x\"}", timeIso);
    }

    protected static long registryRequests() {
        return MINI.research.countCalls("GET", "/research/registry");
    }
}
