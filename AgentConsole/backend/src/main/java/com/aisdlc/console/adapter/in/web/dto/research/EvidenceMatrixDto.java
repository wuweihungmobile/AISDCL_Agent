package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.model.research.ResearchViews.Matrix;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import tools.jackson.core.JacksonException;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 證據矩陣的一個版本（契約 §1.3 {@code EvidenceMatrixDto}）：{@code items} 取自 {@code research_evidence_items}；{@code counterEvidence}、{@code honestBounds}、
 * {@code searchLog} 取自 {@code research_artifacts}（{@code kind=EVIDENCE_ITEMS}）的 {@code content} 全文（D-43；P0 不另立表）——全文是 Bridge 驗證過的
 * {@code evidence_items.json}（鍵為 snake_case：{@code counter_evidence}、{@code honest_bounds}、{@code search_log}），這裡逐項轉成 camelCase；
 * 缺鍵或全文解不出來一律給空值（不丟例外）。
 */
@Schema(name = "EvidenceMatrixDto", description = "證據矩陣的一個版本（反證、誠實劃界、搜尋紀錄取自 EVIDENCE_ITEMS 產物全文）")
public record EvidenceMatrixDto(
        @NotNull @Schema(description = "版本號；尚無任何矩陣版本時為 0（空矩陣）") int matrixVersion,
        @NotNull int scopeRev,
        @NotNull @Schema(description = "該版本 evidence_matrix.md（沒有則 evidence_items.json）的 sha256；空矩陣為空字串") String sha256,
        @NotNull List<EvidenceItemDto> items,
        @NotNull List<CounterEvidenceDto> counterEvidence,
        @NotNull HonestBoundsDto honestBounds,
        @NotNull List<SearchLogDto> searchLog) {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final TypeReference<Map<String, Object>> OBJECT = new TypeReference<>() { };

    /** 每個證據項恰一筆反證結論（研究方法 S5）。 */
    @Schema(name = "CounterEvidenceDto")
    public record CounterEvidenceDto(
            @NotNull String evidenceNo,
            @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "反證搜尋的 Q-NNN 或 null") String searchId,
            @NotNull @Schema(description = "WEAKEN｜LIMIT｜IRRELEVANT｜NOT_FOUND｜NOT_SEARCHED") String conclusion,
            @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String sourceNo,
            @NotNull String note) {
    }

    /** 誠實劃界三桶（研究方法 S8）。 */
    @Schema(name = "HonestBoundsDto")
    public record HonestBoundsDto(
            @NotNull List<NotFoundDto> notFound,
            @NotNull List<String> summaryOnly,
            @NotNull List<String> notReadFully) {
    }

    /** 搜尋了但沒找到的紀錄。 */
    @Schema(name = "HonestBoundsNotFoundDto")
    public record NotFoundDto(@NotNull String query, @NotNull String date, @NotNull String result) {
    }

    /** 研究者自己發出的搜尋紀錄（觀測者標為 AGENT_DECLARED）。 */
    @Schema(name = "SearchLogDto")
    public record SearchLogDto(
            @NotNull @Schema(description = "Q-NNN") String searchNo,
            @NotNull String layer,
            @NotNull @Schema(description = "WebSearch｜WebFetch") String tool,
            @NotNull String query,
            @NotNull @Schema(description = "ISO-8601 帶 offset（原樣）") String at,
            @NotNull List<String> resultUrls) {
    }

    public static EvidenceMatrixDto from(Matrix matrix) {
        Map<String, Object> doc = parse(matrix.itemsJson());
        List<CounterEvidenceDto> counter = new ArrayList<>();
        for (Object item : Iso.list(doc.get("counter_evidence"))) {
            Map<String, Object> row = Iso.map(item);
            counter.add(new CounterEvidenceDto(Iso.text(row.get("evidence_no"), ""), Iso.text(row.get("search_id")),
                    Iso.text(row.get("conclusion"), ""), Iso.text(row.get("source_no")), Iso.text(row.get("note"), "")));
        }
        Map<String, Object> bounds = Iso.map(doc.get("honest_bounds"));
        List<NotFoundDto> notFound = new ArrayList<>();
        for (Object item : Iso.list(bounds.get("not_found"))) {
            Map<String, Object> row = Iso.map(item);
            notFound.add(new NotFoundDto(Iso.text(row.get("query"), ""), Iso.text(row.get("date"), ""), Iso.text(row.get("result"), "")));
        }
        List<SearchLogDto> log = new ArrayList<>();
        for (Object item : Iso.list(doc.get("search_log"))) {
            Map<String, Object> row = Iso.map(item);
            log.add(new SearchLogDto(searchNo(row.get("id")), Iso.text(row.get("layer"), ""), Iso.text(row.get("tool"), ""),
                    Iso.text(row.get("query"), ""), Iso.text(row.get("at"), ""), Iso.strings(row.get("result_urls"))));
        }
        return new EvidenceMatrixDto(matrix.matrixVersion(), matrix.scopeRev(), matrix.sha256(),
                matrix.items().stream().map(EvidenceItemDto::from).toList(), List.copyOf(counter),
                new HonestBoundsDto(List.copyOf(notFound), Iso.strings(bounds.get("summary_only")), Iso.strings(bounds.get("not_read_fully"))),
                List.copyOf(log));
    }

    /** {@code Q-NNN}：字串原樣；整數（資料庫的 search_no）補零成三位。 */
    private static String searchNo(Object id) {
        if (id instanceof Number n) {
            return String.format("Q-%03d", n.intValue());
        }
        return Iso.text(id, "");
    }

    private static Map<String, Object> parse(String json) {
        if (json == null || json.isBlank()) {
            return Map.of();
        }
        try {
            return JSON.readValue(json, OBJECT);
        } catch (JacksonException e) {
            return Map.of();
        }
    }
}
