package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SiReconcileUseCase.ConsoleWrites;
import io.swagger.v3.oas.annotations.media.Schema;

import java.time.OffsetDateTime;
import java.util.List;

/**
 * {@code GET /api/v1/si/console-writes} 的 {@code data}（TCS-SelfImprovingDecide-P2b W14；TCS-SelfImprovingDecideDedupe W-D3）：Console 稽核列與帳本的對帳。
 * {@code items[]} 鍵集合恰為 {@code auditRef、kind、dkind、user、role、time、subjectId、digest、keyId、ingested、supersededBy}（十一鍵，鍵恆在、值可為 null）——
 * <b>沒有 body 與 mac</b>；量不到（{@code reconcile.status}＝{@code NOT-EVALUABLE}）時 {@code ingested}、{@code supersededBy} 與 {@code orphans} 為
 * {@code null}，<b>不是</b>空陣列也不是 {@code false}。被同一決定的已入帳列取代的待入帳列，{@code ingested} 仍為 {@code false}、{@code supersededBy} 為
 * 那一列的 {@code auditRef}。
 */
@Schema(name = "SiConsoleWrites", description = "Console 稽核列與 SelfImproving 帳本的對帳結果")
public record SiConsoleWritesResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "稽核列（時間新到舊、同刻依 auditRef 升冪）") List<Item> items,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "表內還有更舊的列（以 limit 取回更多）") boolean truncated,
        @Schema(nullable = true, description = "帳本中 carrier 為 console、Console 表內卻沒有對應列的項（紅色警示來源）；量不到時為 null") List<Orphan> orphans,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Reconcile reconcile) {

    /** 一筆 Console 稽核列（不含 body 與 mac）。 */
    @Schema(name = "SiConsoleWriteItem")
    public record Item(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, format = "uuid") String auditRef,
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"decide", "obs-add", "obs-close", "sched-set", "run-request", "src-registry"}) String kind,
            @Schema(nullable = true, description = "kind 為 decide 的列＝該決定的動詞（九個之一，原樣透傳）；其餘 kind 與看不出動詞的列為 null") String dkind,
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String user,
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String role,
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, format = "date-time", description = "稽核 body 的 time（同一瞬間；以 UTC 表示）") OffsetDateTime time,
            @Schema(nullable = true, description = "decide＝PROP 號（resume 為 RUN 號）、obs-close＝OBS 號、obs-add＝入帳後回填的新列號（入帳前為 null）") String subjectId,
            @Schema(nullable = true, description = "卡面 digest（只有六種決定動詞才有）；src-registry 列存登記快照的 registry_sha256") String digest,
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "簽章金鑰的 sha256 前 8 碼") String keyId,
            @Schema(nullable = true, description = "帳本是否已有同 auditRef 的 dec／obs.add／obs.close 事件或觀察列標記；量不到時為 null") Boolean ingested,
            @Schema(nullable = true, format = "uuid", description = "待入帳的帶 digest 的決定列，若同一決定（同對象、同 digest、同動詞）已有另一列入帳＝那一列的 auditRef"
                    + "（已入帳者中 time 最早；與 limit 無關）；ingested 仍為 false。其餘（含量不到、無 digest 的動詞）為 null") String supersededBy) {
    }

    /** 帳本有、Console 表內沒有的 carrier=console 項。 */
    @Schema(name = "SiConsoleWriteOrphan")
    public record Orphan(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String auditRef,
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"decide", "obs-add", "obs-close", "sched-set", "run-request", "src-registry"}) String kind,
            @Schema(nullable = true, description = "dec 的 prop（resume 為 run）、觀察列的 id、obs.close 的 obs") String subject) {
    }

    /** 對帳狀態；量不到時 {@code reason} 為四個原因之一。 */
    @Schema(name = "SiReconcile")
    public record Reconcile(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"ok", "NOT-EVALUABLE"}) String status,
            @Schema(nullable = true, allowableValues = {"si_unavailable", "bridge_unreachable", "bridge_timeout", "scan_cap_exceeded"},
                    description = "量不到的原因；ok 時為 null") String reason,
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, minimum = "0", description = "本次回填 subject_id 的筆數（量不到時為 0）") int backfilled) {
    }

    public static SiConsoleWritesResponse from(ConsoleWrites writes) {
        return new SiConsoleWritesResponse(
                writes.items().stream().map(i -> new Item(i.auditRef(), i.kind(), i.dkind(), i.user(), i.role(), i.time(), i.subjectId(),
                        i.digest(), i.keyId(), i.ingested(), i.supersededBy())).toList(),
                writes.truncated(),
                writes.orphans() == null ? null
                        : writes.orphans().stream().map(o -> new Orphan(o.auditRef(), o.kind(), o.subject())).toList(),
                new Reconcile(writes.reconcile().status(), writes.reconcile().reason(), writes.reconcile().backfilled()));
    }
}
