package com.aisdlc.console.adapter.out.persistence.research;

import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.sql.Array;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 研究讀配接器共用的取值小工具（只讀）：時間一律以 {@link OffsetDateTime} 取（資料庫欄位皆為 timestamptz），JSONB 欄位以文字取出後解析，SQL 陣列轉 {@code List<String>}。
 * 這個套件只讀 {@code console.research_*}（Bridge 是唯一寫入者），讀取一律經 {@code JdbcClient}。
 */
final class ResearchJdbc {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final TypeReference<Map<String, Object>> OBJECT = new TypeReference<>() { };

    private ResearchJdbc() {
    }

    static OffsetDateTime ts(ResultSet rs, String column) throws SQLException {
        return rs.getObject(column, OffsetDateTime.class);
    }

    static UUID uuid(ResultSet rs, String column) throws SQLException {
        return rs.getObject(column, UUID.class);
    }

    static Integer nullableInt(ResultSet rs, String column) throws SQLException {
        int value = rs.getInt(column);
        return rs.wasNull() ? null : value;
    }

    /** 同上，以欄位序號取（聚合函式的無名欄位）。 */
    static Integer nullableInt(ResultSet rs, int index) throws SQLException {
        int value = rs.getInt(index);
        return rs.wasNull() ? null : value;
    }

    static Long nullableLong(ResultSet rs, String column) throws SQLException {
        long value = rs.getLong(column);
        return rs.wasNull() ? null : value;
    }

    /** 同上，以欄位序號取（聚合函式的無名欄位）。 */
    static Long nullableLong(ResultSet rs, int index) throws SQLException {
        long value = rs.getLong(index);
        return rs.wasNull() ? null : value;
    }

    /** JSONB（以 {@code ::text} 取出）→ 物件；缺值或空白→空物件；不是合法 JSON 物件（資料庫的 JSONB 型別保證合法，這裡不會發生）→ 空物件。 */
    static Map<String, Object> object(String json) {
        if (json == null || json.isBlank()) {
            return Map.of();
        }
        return JSON.readValue(json, OBJECT);
    }

    /** SQL 陣列欄位（text[]／varchar[]）→ 字串清單；NULL→空清單。 */
    static List<String> strings(ResultSet rs, String column) throws SQLException {
        Array array = rs.getArray(column);
        if (array == null) {
            return List.of();
        }
        Object[] items = (Object[]) array.getArray();
        List<String> out = new ArrayList<>(items.length);
        for (Object item : items) {
            out.add(item == null ? null : item.toString());
        }
        return List.copyOf(out);
    }
}
