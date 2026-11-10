package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractRegistryIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniResearch.Reply;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 登記同步狀態 API-SI-14（TCS-ResearchRegistry AT-965-7-1～7-4；契約 §5A.4）。為什麼重要：這個狀態是掌舵者判斷「我的設定到底生效沒有」的唯一依據——讀不到
 * 若被當成「已同步」或「從未同步」、有更新的待入帳寫入時仍以舊鏡像判已同步（D→E→D），畫面就會說謊；每一態的判定序都用表驅動逐列鎖住。
 */
class SiRegistryStatusApiIT extends AbstractRegistryIT {

    private record Row(String label, Object latest, List<String> ingested, List<String[]> writes, String state, String ingestedSha, String pendingRef) {
    }

    private static String[] w(String ref, String digest, String time) {
        return new String[] {ref, digest, time};
    }

    // ── AT-965-7-1 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_7_1_theFourStatesAreJudgedInTheDocumentedOrder() {
        String r1 = ref("f1", 1);
        String r2 = ref("f1", 2);
        String r3 = ref("f1", 3);
        List<Row> rows = List.of(
                new Row("a 最新已入帳＝當前", latest(r1, SHA_D), List.of(r1), List.<String[]>of(w(r1, SHA_D, T1)), "synced", SHA_D, null),
                new Row("b 未入帳列 digest＝當前", latest(r1, SHA_E), List.of(r1), List.<String[]>of(w(r1, SHA_E, T1), w(r2, SHA_D, T2)), "pending", SHA_E, r2),
                new Row("c 無相符列", latest(r1, SHA_E), List.of(r1), List.<String[]>of(w(r1, SHA_E, T1)), "unsynced", SHA_E, null),
                new Row("d 從未同步", null, List.of(), List.of(), "unsynced", null, null),
                new Row("e 已入帳＝D 且同時有較新的未入帳 D", latest(r1, SHA_D), List.of(r1), List.<String[]>of(w(r1, SHA_D, T1), w(r2, SHA_D, T2)), "pending", SHA_D, r2),
                new Row("h 已入帳＝D 但有較新的未入帳 E（D→E→D 的當下）", latest(r1, SHA_D), List.of(r1), List.<String[]>of(w(r1, SHA_D, T1), w(r2, SHA_E, T2)), "unsynced", SHA_D, null),
                new Row("i 未入帳 E 的 time 早於最新已入帳列（REG-STALE 會拒收）", latest(r2, SHA_D), List.of(r2), List.<String[]>of(w(r1, SHA_E, T1), w(r2, SHA_D, T2)), "synced", SHA_D, null),
                new Row("f A→B→A：舊的 D 已入帳不判 pending", latest(r2, SHA_E), List.of(r1, r2), List.<String[]>of(w(r1, SHA_D, T1), w(r2, SHA_E, T2)), "unsynced", SHA_E, null),
                new Row("k 多個未入帳列相符時取 time 最新者", latest(r1, SHA_E), List.of(r1), List.<String[]>of(w(r1, SHA_E, T1), w(r2, SHA_D, T2), w(r3, SHA_D, T3)), "pending", SHA_E, r3));
        for (Row row : rows) {
            MINI.si.reset();
            MINI.research.reset();
            jdbc.execute("TRUNCATE console.si_console_writes");
            snapshot("{}\n", SHA_D);
            mirror(row.latest(), row.ingested(), DROP);
            for (String[] write : row.writes()) {
                insertRegistryWrite(write[0], write[1], write[2]);
            }

            Resp resp = api.get(viewer(), REGISTRY);

            assertThat(resp.status()).as(row.label()).isEqualTo(200);
            assertThat(resp.<String>read("$.data.state")).as("%s：state", row.label()).isEqualTo(row.state());
            assertThat(resp.<String>read("$.data.currentSha256")).as("%s：currentSha256 恆為當前 digest", row.label()).isEqualTo(SHA_D);
            assertThat(resp.<Object>read("$.data.ingestedSha256")).as("%s：ingestedSha256", row.label()).isEqualTo(row.ingestedSha());
            assertThat(resp.<Object>read("$.data.pendingAuditRef")).as("%s：pendingAuditRef", row.label()).isEqualTo(row.pendingRef());
            assertThat(resp.<Object>read("$.data.unknownCause")).as("%s：非 unknown 時沒有原因", row.label()).isNull();
        }
        // g：鏡像缺 research_registry 鍵（根層尚未升版）＝200 的 unknown，不當成從未同步
        MINI.si.reset();
        MINI.research.reset();
        jdbc.execute("TRUNCATE console.si_console_writes");
        snapshot("{}\n", SHA_D);
        mirror(DROP, List.of(), DROP);
        Resp missing = api.get(viewer(), REGISTRY);
        assertThat(missing.status()).isEqualTo(200);
        assertThat(missing.<String>read("$.data.state")).isEqualTo("unknown");
        assertThat(missing.<String>read("$.data.unknownCause")).isEqualTo("si_unavailable");
        assertThat(missing.<String>read("$.data.currentSha256")).isEqualTo(SHA_D);
        assertThat(missing.<Object>read("$.data.ingestedSha256")).isNull();
        assertThat(missing.<Object>read("$.data.pendingAuditRef")).isNull();
    }

    // ── AT-965-7-2 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_7_2_anUnreadableMirrorIsUnknownWithACauseAndAFailedSnapshotIsNeverDowngraded() {
        snapshot("{}\n", SHA_D);
        record Mirror(String label, Runnable setup, String cause) {
        }
        List<Mirror> mirrors = new ArrayList<>();
        mirrors.add(new Mirror("SI 不可用", () -> MINI.si.unavailable = Map.of("cause", "nonzero_rc", "detail", "rc=3"), "si_unavailable"));
        mirrors.add(new Mirror("掃描超上限", () -> MINI.si.payloads.put("events", export("events", List.of(), true, 1)), "scan_cap_exceeded"));
        mirrors.add(new Mirror("鏡像逾時", () -> {
            readTimeout.cap(Duration.ofMillis(400));
            MINI.si.delayMillis = 2_500;
        }, "bridge_timeout"));
        mirrors.add(new Mirror("鏡像 500", () -> MINI.si.status500 = true, "si_unavailable"));
        for (Mirror m : mirrors) {
            MINI.si.reset();
            readTimeout.reset();
            mirror(latest(ref("f2", 1), SHA_D), List.of(ref("f2", 1)), DROP);
            m.setup().run();
            Resp resp = api.get(viewer(), REGISTRY);
            assertThat(resp.status()).as(m.label()).isEqualTo(200);
            assertThat(resp.<String>read("$.data.state")).as("%s：不為 synced", m.label()).isEqualTo("unknown");
            assertThat(resp.<String>read("$.data.unknownCause")).as(m.label()).isEqualTo(m.cause());
            assertThat(resp.<Object>read("$.data.ingestedSha256")).as("%s：其餘欄為 null", m.label()).isNull();
            assertThat(resp.<Object>read("$.data.researchFetchMax")).isNull();
        }
        readTimeout.reset();
        MINI.si.reset();
        // 快照自身失敗：非 200，不降級成 unknown
        Map<String, Reply> snapshotFailures = new java.util.LinkedHashMap<>();
        snapshotFailures.put("research_requires_db", Reply.error(503, "research_requires_db"));
        for (Map.Entry<String, Reply> failure : snapshotFailures.entrySet()) {
            MINI.research.reset();
            MINI.research.always("registry", failure.getValue());
            Resp resp = api.get(viewer(), REGISTRY);
            assertThat(resp.status()).as(failure.getKey()).isEqualTo(503);
            assertThat(resp.<String>read("$.reason")).isEqualTo(failure.getKey());
            assertThat(resp.has("$.data")).isFalse();
        }
        MINI.research.reset();
        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        Resp down = api.get(viewer(), REGISTRY);
        assertThat(down.status()).isEqualTo(502);
        assertThat(down.<String>read("$.reason")).isEqualTo("bridge_unreachable");
        resetSystemConfigs();
        readTimeout.cap(Duration.ofMillis(400));
        MINI.research.delayMillis = 2_500;
        Resp slow = api.get(viewer(), REGISTRY);
        assertThat(slow.status()).isEqualTo(504);
        assertThat(slow.<String>read("$.reason")).isEqualTo("bridge_timeout");
    }

    // ── AT-965-7-3 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_7_3_allRolesCanReadAndTheKeySetIsExactlyTheEightDocumentedKeys() {
        snapshot("{}\n", SHA_D);
        mirror(latest(ref("f3", 1), SHA_D), List.of(ref("f3", 1)), 10);
        for (String token : List.of(viewer(), operator(), admin())) {
            Resp resp = api.get(token, REGISTRY);
            assertThat(resp.status()).isEqualTo(200);
            Map<String, Object> data = resp.data();
            assertThat(data.keySet()).containsExactlyInAnyOrder("state", "unknownCause", "currentSha256", "ingestedSha256", "ingestedAuditRef", "pendingAuditRef",
                    "pendingTime", "researchFetchMax");
            assertThat(resp.body()).doesNotContain("\"body\"").doesNotContain("\"mac\"").doesNotContain("keyId").doesNotContain("registryText");
        }
        assertThat(api.get(null, REGISTRY).status()).as("匿名 401").isEqualTo(401);
        List<String> required = api.get(viewer(), "/v3/api-docs").read("$.components.schemas.ResearchRegistrySyncStatus.required");
        assertThat(required).containsExactlyInAnyOrder("state", "unknownCause", "currentSha256", "ingestedSha256", "ingestedAuditRef", "pendingAuditRef",
                "pendingTime", "researchFetchMax");
    }

    // ── AT-965-7-4 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_7_4_researchFetchMaxOnlyRelaysAPositiveIntegerFromTheMirror() {
        snapshot("{}\n", SHA_D);
        List<Object[]> cases = new ArrayList<>();
        cases.add(new Object[] {10, 10});
        cases.add(new Object[] {12, 12});
        cases.add(new Object[] {DROP, null});
        cases.add(new Object[] {"10", null});
        cases.add(new Object[] {-1, null});
        cases.add(new Object[] {0, null});
        for (Object[] c : cases) {
            mirror(latest(ref("f4", 1), SHA_D), List.of(ref("f4", 1)), c[0]);
            Resp resp = api.get(viewer(), REGISTRY);
            assertThat(resp.status()).isEqualTo(200);
            assertThat(resp.<Object>read("$.data.researchFetchMax")).as("輸入 %s", c[0] == DROP ? "缺鍵" : c[0]).isEqualTo(c[1]);
        }
        for (String file : List.of("SiRegistryMirror.java", "SiConsoleWriteService.java")) {
            assertThat(hasLiteralFetchMaxDefault(readSource(file))).as("%s 沒有把數字當 researchFetchMax 的預設值", file).isFalse();
        }
        assertThat(hasLiteralFetchMaxDefault("Integer researchFetchMax = 10;")).as("負控：掃描器抓得到字面預設").isTrue();
        assertThat(hasLiteralFetchMaxDefault("fetchMax = value == null ? 10 : value;")).as("負控：三元式預設").isTrue();
        assertThat(hasLiteralFetchMaxDefault("Integer researchFetchMax = fetchMaxOf(x);")).isFalse();
    }

    private static String readSource(String file) {
        try {
            return java.nio.file.Files.readString(java.nio.file.Path.of("src", "main", "java", "com", "aisdlc", "console", "application", "service", file),
                    java.nio.charset.StandardCharsets.UTF_8);
        } catch (java.io.IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
    }

    /** 去註解後，researchFetchMax／fetchMax 是否被指派數字字面或以三元式、getOrDefault 帶數字預設值。 */
    private static boolean hasLiteralFetchMaxDefault(String source) {
        String code = source.replaceAll("(?s)/\\*.*?\\*/", "").replaceAll("//[^\n]*", "");
        return java.util.regex.Pattern.compile("(?i)(researchFetchMax|fetchMax)\\s*=\\s*(\\d|[^;]*\\?\\s*\\d|[^;]*getOrDefault\\([^;]*,\\s*\\d)").matcher(code).find();
    }
}
