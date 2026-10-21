package com.aisdlc.console.adapter.in.web.dto;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 欄名對映函式 {@link SiKeyNames}（TCS-SelfImprovingMirror-P1b R9；AT-932-1-4 與其補強）。
 * 為什麼重要：AC-SI-32-1 的「頁面逐欄等於 export」只允許欄名經這一個函式改變——對映寫鬆了會多轉（{@code a__b}、
 * {@code PROP-SI-004} 這類鍵被改名而與黃金檔對不上），寫緊了會漏轉（前端拿不到 {@code marksKv}）；值（含 {@code null}）
 * 與鍵序一個字都不能動。
 */
class SiKeyNamesTest {

    @Test
    void AT_932_1_4_theMappingTableIsExactAndEveryOtherKeyIsIdentity() {
        String[][] table = {
                {"http_status", "httpStatus"}, {"touched_sha256", "touchedSha256"}, {"marks_kv", "marksKv"},
                {"schema_rev", "schemaRev"}, {"next_since", "nextSince"}, {"opened_seq", "openedSeq"},
                {"digest8", "digest8"}, {"PROP-SI-004", "PROP-SI-004"}, {"quota-band", "quota-band"},
                {"來源", "來源"}, {"a__b", "a__b"}, {"_x", "_x"}, {"x_", "x_"}, {"Http_status", "Http_status"},
                {"sha_256", "sha256"}, {"id", "id"}, {"", ""},
                // 補：多段、數字開頭的段、已含大寫、含連字號的鍵
                {"a_b_c", "aBC"}, {"x_1", "x1"}, {"touched_Sha", "touched_Sha"}, {"a-b_c", "a-b_c"}};
        for (String[] row : table) {
            assertThat(SiKeyNames.camel(row[0])).as("camel(%s)", row[0]).isEqualTo(row[1]);
        }
    }

    @Test
    void AT_932_1_4_theFunctionIsStatelessAndRejectsNullLoudly() {
        assertThat(SiKeyNames.camel("generated_at")).isEqualTo(SiKeyNames.camel("generated_at")).isEqualTo("generatedAt");
        assertThatThrownBy(() -> SiKeyNames.camel(null)).isInstanceOf(NullPointerException.class);
    }

    @Test
    void AT_932_1_4_camelKeysConvertsEveryLevelButNeverTouchesValuesNullsOrKeyOrder() {
        Map<String, Object> inner = new LinkedHashMap<>();
        inner.put("inner_key", null);
        inner.put("quota-band", "free");
        Map<String, Object> event = new LinkedHashMap<>();
        event.put("seq", 5);
        event.put("touched_sha256", "sha256:abc");
        event.put("by_who", "主控\n全形：「」");
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("schema_rev", 1);
        root.put("head_sha", null);
        root.put("items", List.of(event, "plain_string_value", 7));
        root.put("x_meta", inner);
        root.put("next_since", null);

        @SuppressWarnings("unchecked")
        Map<String, Object> out = (Map<String, Object>) SiKeyNames.camelKeys(root);

        assertThat(out.keySet()).containsExactly("schemaRev", "headSha", "items", "xMeta", "nextSince");
        assertThat(out).containsEntry("headSha", null).containsEntry("nextSince", null);
        @SuppressWarnings("unchecked")
        List<Object> items = (List<Object>) out.get("items");
        assertThat(items).hasSize(3);
        @SuppressWarnings("unchecked")
        Map<String, Object> mappedEvent = (Map<String, Object>) items.get(0);
        assertThat(mappedEvent.keySet()).containsExactly("seq", "touchedSha256", "byWho");
        assertThat(mappedEvent.get("byWho")).as("字串值逐位元組不動（含換行與全形字元）").isEqualTo("主控\n全形：「」");
        assertThat(items.get(1)).isEqualTo("plain_string_value");
        assertThat(items.get(2)).isEqualTo(7);
        @SuppressWarnings("unchecked")
        Map<String, Object> mappedInner = (Map<String, Object>) out.get("xMeta");
        assertThat(mappedInner.keySet()).containsExactly("innerKey", "quota-band");
        assertThat(mappedInner).containsEntry("innerKey", null);
        assertThat(root.keySet()).as("不改輸入").containsExactly("schema_rev", "head_sha", "items", "x_meta", "next_since");
    }

    @Test
    void AT_932_1_4_twoSourceKeysThatMapToOneNameNeverLoseAField() {
        Map<String, Object> source = new LinkedHashMap<>();
        source.put("x_1", "converted");       // 轉出 x1，但 x1 本來就存在（不變的鍵先保有名字）
        source.put("x1", "identity");
        source.put("a1_b", "first");           // 兩者都轉出 a1B：先到者得 a1B，後到者保留原鍵
        source.put("a_1_b", "second");

        @SuppressWarnings("unchecked")
        Map<String, Object> out = (Map<String, Object>) SiKeyNames.camelKeys(source);

        assertThat(out).hasSize(4).containsEntry("x1", "identity").containsEntry("x_1", "converted")
                .containsEntry("a1B", "first").containsEntry("a_1_b", "second");
        assertThat(new ArrayList<>(out.values())).containsExactlyInAnyOrder("converted", "identity", "first", "second");
    }
}
