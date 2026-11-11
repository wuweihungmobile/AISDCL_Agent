package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniBridge;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 單筆提案 {@code items[0].detail} 的 backend 面（{@code GET /api/v1/si/proposals/{id}}；TCS-SiFlowVisibility-20261111 AT-966-4-3～4-5；
 * Bridge 的 4-1、4-2、4-6、4-E-1 在 {@code test_si_proposal_detail.py}）。
 * 為什麼重要：根層加了 {@code detail}（diff、本文、來源觀察、評估集摘要、沙盒、驗證、下一步、時間線）後，backend 只准做一件事——換欄名風格原樣轉出。
 * 若它把 {@code null} 丟掉（畫面就分不出「量不到」與「缺席」）、把舊根層沒有的 {@code detail} 補成空物件、對陣列內的物件不轉鍵，
 * 或把 256 KiB 的 diff 截短，前端詳情對話框就會說謊。
 */
class SiProposalDetailApiIT extends AbstractExecutionIT {

    private static final String ONE = "/api/v1/si/proposals/PROP-SI-901";
    private static final String ID = "PROP-SI-901";
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Pattern SNAKE = Pattern.compile("[a-z][a-z0-9]*(?:_[a-z0-9]+)+");
    private static final Path ROOT_GOLDEN = Path.of("..", "..", "tools", "tests", "fixtures", "selfimproving", "p7", "detail.golden.json");
    private static final Path LOCAL_GOLDEN = Path.of("src", "test", "resources", "si", "p7", "detail.golden.json");

    private static Map<String, Object> map(Object... keyValues) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            out.put((String) keyValues[i], keyValues[i + 1]);
        }
        return out;
    }

    /** {@code DETAIL()}：C-3 的 {@code detail} 基準夾具（camelCase；八欄俱全）。 */
    private static Map<String, Object> detail() {
        return map(
                "patch", map("rel", "docs/06_quality/SelfImproving_Proposals/PROP-SI-901/r2.patch", "bytes", 120,
                        "text", "diff --git a/x b/x\r\n--- a/x\r\n+++ b/x\r\n@@ -1 +1 @@\r\n-舊\t行\r\n+新 😀   行", "truncated", false),
                "body", map("rel", "docs/06_quality/SelfImproving_Proposals/PROP-SI-901/r2.md", "bytes", 28, "text", "# 提案 901\n\n症狀…\n",
                        "truncated", false),
                "sourceObs", List.of(map("id", "OBS-SI-001", "context", "巡邏日誌", "symptom", "提案卡了三天沒人處理", "severity", "P2",
                        "disposition", "proposed"), map("id", "OBS-SI-002", "missing", true)),
                "heldout", map("frozen", true, "seq", 60, "n", 7, "min", 5, "belowMin", false, "frozenBy", "凍結者甲", "digest8", "0a1b2c3d",
                        "neNote", null),
                "sandbox", map("seq", 61, "id", "APP-SI-901", "applied", true, "touchedOk", true, "rollbackOk", true, "failCode", null,
                        "failText", null),
                "verify", map("seq", 62, "id", "APP-SI-901", "verdict", "PASS", "baselineRed", true, "patchedGreen", true, "mutatedRed", true,
                        "probesN", 6, "carrierProof", true, "reasons", List.of(map("code", "VERIFY-OK", "text", "三步證據齊全，驗證通過"))),
                "next", map("code", "WAIT-PROMOTE-DECISION", "who", "掌舵者", "text", "驗證通過，等你決定是否晉升"),
                "timeline", List.of(map("seq", 12, "t", "2026-11-10T09:00:00+08:00", "by", "巡邏器", "kind", "prop", "action", "提出提案")));
    }

    private static Map<String, Object> item(Map<String, Object> detail) {
        Map<String, Object> item = map("id", ID, "state", "verified", "rev", 2, "last_seq", 120, "sources", List.of("OBS-SI-001"), "card", "卡面");
        if (detail != null) {
            item.put("detail", detail);
        }
        return item;
    }

    private static String snakeOf(String key) {
        StringBuilder out = new StringBuilder();
        for (char c : key.toCharArray()) {
            out.append(Character.isUpperCase(c) ? "_" + Character.toLowerCase(c) : String.valueOf(c));
        }
        return out.toString();
    }

    /** 把整棵樹的 camelCase 鍵改成 snake_case（模擬「某鍵以 snake_case 到達」的根層輸出）。 */
    private static Object snake(Object value) {
        if (value instanceof Map<?, ?> m) {
            Map<String, Object> out = new LinkedHashMap<>();
            m.forEach((k, v) -> out.put(snakeOf((String) k), snake(v)));
            return out;
        }
        if (value instanceof List<?> list) {
            List<Object> out = new ArrayList<>();
            list.forEach(v -> out.add(snake(v)));
            return out;
        }
        return value;
    }

    private static String camelOf(String key) {
        if (!SNAKE.matcher(key).matches()) {
            return key;
        }
        String[] parts = key.split("_");
        StringBuilder out = new StringBuilder(parts[0]);
        for (int i = 1; i < parts.length; i++) {
            out.append(Character.toUpperCase(parts[i].charAt(0))).append(parts[i].substring(1));
        }
        return out.toString();
    }

    private static JsonNode camelTree(JsonNode node) {
        if (node.isObject()) {
            var out = JSON.createObjectNode();
            node.properties().forEach(e -> out.set(camelOf(e.getKey()), camelTree(e.getValue())));
            return out;
        }
        if (node.isArray()) {
            var out = JSON.createArrayNode();
            node.forEach(x -> out.add(camelTree(x)));
            return out;
        }
        return node;
    }

    private Resp fetch(String token) {
        return api.get(token, ONE);
    }

    private static JsonNode data(Resp resp) {
        return JSON.readTree(resp.body()).get("data");
    }

    // ── AT-966-4-3：兩種欄名風格對映與未知鍵透傳 ────────────────────────────────────────────────

    @Test
    void AT_966_4_3_bothKeyStylesMapToTheSameCamelCaseKeysAndUnknownKeysPassThrough() {
        String viewer = viewer();
        Map<String, Object> camel = detail();
        camel.put("futureThing", "未知鍵");
        ((Map<String, Object>) camel.get("heldout")).put("extra_key", "未知內層鍵");
        MINI.proposalDetail(ID, item(camel));
        JsonNode fromCamel = data(fetch(viewer)).at("/items/0/detail");

        @SuppressWarnings("unchecked")
        Map<String, Object> snakeDetail = (Map<String, Object>) snake(camel);
        assertThat(snakeDetail).as("夾具確實是 snake_case").containsKey("source_obs").doesNotContainKey("sourceObs");
        assertThat((Map<String, Object>) snakeDetail.get("heldout")).containsKeys("below_min", "frozen_by");
        assertThat((Map<String, Object>) snakeDetail.get("sandbox")).containsKeys("touched_ok", "rollback_ok", "fail_code");
        assertThat((Map<String, Object>) snakeDetail.get("verify")).containsKeys("baseline_red", "patched_green", "mutated_red", "probes_n",
                "carrier_proof");
        MINI.proposalDetail(ID, item(snakeDetail));
        JsonNode fromSnake = data(fetch(viewer)).at("/items/0/detail");

        assertThat(fromSnake).as("(b) 全 snake_case 被轉成與 (a) 相同的鍵名").isEqualTo(fromCamel);
        assertThat(fromCamel.at("/futureThing").asString()).isEqualTo("未知鍵");
        assertThat(fromCamel.at("/heldout/extraKey").asString()).as("未知內層鍵依規則透傳（extra_key→extraKey）").isEqualTo("未知內層鍵");
        assertThat(fromCamel.at("/verify/reasons/0/code").asString()).isEqualTo("VERIFY-OK");
        assertThat(fromCamel.at("/verify/reasons/0/text").asString()).isEqualTo("三步證據齊全，驗證通過");
        assertThat(fromCamel.at("/sandbox/failText").isNull()).as("null 保留").isTrue();
        assertThat(fromCamel.at("/heldout/neNote").isNull()).isTrue();
        assertThat(fromCamel.at("/sourceObs/1").toString()).as("缺列形態只有 id 與 missing").isEqualTo("{\"id\":\"OBS-SI-002\",\"missing\":true}");
        assertThat(fromCamel.at("/timeline/0/action").asString()).isEqualTo("提出提案");
        assertThat(fromCamel.at("/patch/text").asString()).as("patch.text 位元組相等").isEqualTo((String) ((Map<?, ?>) camel.get("patch")).get("text"));
        assertThat(fromCamel.at("/body/text").asString()).isEqualTo("# 提案 901\n\n症狀…\n");
        assertThat(data(fetch(viewer)).at("/items").size()).as("items 恰一筆").isEqualTo(1);

        // ne[] 含根層新碼項時逐項透傳（含 text 鍵）
        Map<String, Object> export = MiniBridge.Si.proposalExport(item(camel));
        export.put("ne", List.of(map("field", "patch", "reason", "PATCH-UNREADABLE", "text", "修補檔讀不到")));
        MINI.si.payloads.put("proposal:" + ID, export);
        assertThat(data(fetch(viewer)).at("/ne/0/text").asString()).isEqualTo("修補檔讀不到");
        assertThat(data(fetch(viewer)).at("/ne/0/reason").asString()).isEqualTo("PATCH-UNREADABLE");
    }

    /** 黃金樣本列（整個 {@code items[0]}）：先斷言複本逐位元組等於根層檔，再驗透傳。 */
    @Test
    void AT_966_4_3_theGoldenSampleCopyEqualsTheRootFileAndPassesThrough() throws IOException {
        assertThat(Files.readAllBytes(LOCAL_GOLDEN)).as("複本與根層黃金樣本必須逐位元組相等").isEqualTo(Files.readAllBytes(ROOT_GOLDEN));
        @SuppressWarnings("unchecked")
        Map<String, Object> goldenItem = JSON.readValue(Files.readString(LOCAL_GOLDEN, StandardCharsets.UTF_8), Map.class);
        MINI.proposalDetail(String.valueOf(goldenItem.get("id")), goldenItem);
        Resp resp = api.get(viewer(), "/api/v1/si/proposals/" + goldenItem.get("id"));
        assertThat(resp.status()).isEqualTo(200);
        assertThat(data(resp).at("/items/0/detail")).isEqualTo(camelTree(JSON.valueToTree(goldenItem.get("detail"))));
        assertThat(data(resp).at("/items").size()).isEqualTo(1);
    }

    // ── AT-966-4-4：null 與缺席區分 ────────────────────────────────────────────────────────────

    @Test
    void AT_966_4_4_jsonNullAndAbsentAreDistinguishedAndAnEmptyArrayIsNotNull() {
        String viewer = viewer();
        // (a) 區塊與值為 null：鍵存在且值為 JSON null
        Map<String, Object> nulls = detail();
        nulls.put("patch", null);
        nulls.put("body", null);
        nulls.put("sandbox", null);
        nulls.put("verify", null);
        ((Map<String, Object>) nulls.get("heldout")).put("seq", null);
        ((Map<String, Object>) nulls.get("heldout")).put("n", null);
        MINI.proposalDetail(ID, item(nulls));
        JsonNode a = data(fetch(viewer)).at("/items/0/detail");
        for (String key : List.of("patch", "body", "sandbox", "verify")) {
            assertThat(a.has(key)).as("(a) %s 存在", key).isTrue();
            assertThat(a.get(key).isNull()).as("(a) %s 為 JSON null", key).isTrue();
        }
        assertThat(a.at("/heldout").has("seq") && a.at("/heldout/seq").isNull()).as("(a) heldout.seq 存在且為 null").isTrue();
        assertThat(a.at("/heldout").has("n") && a.at("/heldout/n").isNull()).isTrue();
        // (b) 完全沒有 detail 鍵：不補 null、不補 {}
        MINI.proposalDetail(ID, item(null));
        JsonNode itemB = data(fetch(viewer)).at("/items/0");
        assertThat(itemB.has("detail")).as("(b) 沒有 detail 鍵").isFalse();
        assertThat(itemB.get("id").asString()).isEqualTo(ID);
        // (c) reasons 為空陣列：不是 null、不是缺席
        Map<String, Object> empty = detail();
        ((Map<String, Object>) empty.get("verify")).put("reasons", List.of());
        MINI.proposalDetail(ID, item(empty));
        JsonNode reasons = data(fetch(viewer)).at("/items/0/detail/verify/reasons");
        assertThat(reasons.isArray()).as("(c) reasons 是陣列").isTrue();
        assertThat(reasons.isEmpty()).as("(c) reasons 為空陣列").isTrue();
        // ne[] 逐項透傳
        Map<String, Object> export = MiniBridge.Si.proposalExport(item(empty));
        export.put("ne", List.of(map("field", "heldout", "reason", "HELDOUT-MIN-UNKNOWN", "text", "最低案例數量不到")));
        MINI.si.payloads.put("proposal:" + ID, export);
        assertThat(data(fetch(viewer)).at("/ne/0").toString()).isEqualTo(
                "{\"field\":\"heldout\",\"reason\":\"HELDOUT-MIN-UNKNOWN\",\"text\":\"最低案例數量不到\"}");
    }

    // ── AT-966-4-5：256 KiB patch 往返 ─────────────────────────────────────────────────────────

    private static String text256K(char tail) {
        String unit = "ab中\r\n";          // 2 + 3 + 2 = 7 位元組
        int size = 262144;
        int reps = size / 7;
        String text = unit.repeat(reps) + String.valueOf(tail).repeat(size - reps * 7);
        assertThat(text.getBytes(StandardCharsets.UTF_8)).hasSize(size);
        return text;
    }

    @Test
    void AT_966_4_5_aTwoHundredFiftySixKibPatchAndBodyRoundTripByteForByte() {
        String patchText = text256K('x');
        String bodyText = text256K('y');
        Map<String, Object> big = detail();
        big.put("patch", map("rel", "p.patch", "bytes", 262144, "text", patchText, "truncated", true));
        big.put("body", map("rel", "b.md", "bytes", 262144, "text", bodyText, "truncated", true));
        MINI.proposalDetail(ID, item(big));

        long started = System.nanoTime();
        Resp resp = fetch(viewer());
        long millis = (System.nanoTime() - started) / 1_000_000;

        assertThat(resp.status()).isEqualTo(200);
        JsonNode d = data(resp).at("/items/0/detail");
        assertThat(d.at("/patch/text").asString().getBytes(StandardCharsets.UTF_8)).as("patch.text 逐位元組相等")
                .isEqualTo(patchText.getBytes(StandardCharsets.UTF_8));
        assertThat(d.at("/body/text").asString().getBytes(StandardCharsets.UTF_8)).as("body.text 逐位元組相等")
                .isEqualTo(bodyText.getBytes(StandardCharsets.UTF_8));
        assertThat(d.at("/patch/truncated").asBoolean()).isTrue();
        assertThat(d.at("/patch/bytes").asInt()).isEqualTo(262144);
        assertThat(millis).as("單次請求在測試逾時內完成").isLessThan(15_000);
        assertThat(MINI.countRequests("GET /si/proposals/" + ID)).isEqualTo(1);
    }
}
