package com.aisdlc.console.adapter.in.web.dto.research;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 對帳結果（契約 §1.3 {@code ReconcileResult}；API-RP-18 {@code reconcile}）：只報告、不修復；{@code consistent} 僅在全部 check 為 ok 時為真。
 *
 * <p><b>讀 Bridge 的真形狀</b>（D-76(3)；Bridge {@code app/research/gates/reconcile.py} 的 {@code file_check}／{@code mapping_check}／{@code reconcile_result}，
 * README〈對帳結果契約〉）：{@code checks[]} 的識別鍵是 <b>{@code id}</b>（轉出為 {@code name}，前端靠 {@code name === "fsm_flow_mapping"} 辨識對映漂移）；
 * 漂移列的兩個摘要欄在 Bridge 端已是 camelCase（{@code expectedSha256}、{@code actualSha256}），原樣讀、原樣轉出。{@code drift} 陣列原樣轉出
 * （Bridge 恆帶：沒有漂移＝空陣列；本文沒有該鍵時才省略）。Bridge 另帶的 {@code present}、{@code detail}、{@code driftCount} 不在契約 DTO 內，不轉出。
 */
@Schema(name = "ReconcileResult", description = "對帳結果（只報告、不修復）")
public record ReconcileResultDto(
        @NotNull boolean consistent,
        @NotNull List<CheckDto> checks) {

    /** 一項對帳檢查。 */
    @Schema(name = "ReconcileCheckDto")
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record CheckDto(
            @NotNull @Schema(description = "檢查項識別（Bridge 的 id）：fsm_flow_mapping｜prd_sha256｜review_card｜evidence_matrix｜task_decomposition｜route_decision") String name,
            @NotNull @Schema(description = "ok｜drift｜NOT_EVALUABLE｜pending_correction（D-128：build／TCS_PENDING 而內環鍵已凍結 Stage-2，待 Bridge 校正游標；不是 drift）") String status,
            List<DriftDto> drift) {
    }

    /** 一筆漂移（檔案內容與庫內登記的雜湊不符、檔案缺失…；{@code fsm_flow_mapping} 的漂移列兩個摘要皆為 null）。 */
    @Schema(name = "ReconcileDriftDto")
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record DriftDto(@NotNull String kind, @NotNull String path, String expectedSha256, String actualSha256) {
    }

    public static ReconcileResultDto from(Map<String, Object> body) {
        List<CheckDto> checks = new ArrayList<>();
        for (Object item : Iso.list(body.get("checks"))) {
            Map<String, Object> check = Iso.map(item);
            List<DriftDto> drift = null;
            if (check.get("drift") instanceof List<?> rows) {
                drift = new ArrayList<>();
                for (Object row : rows) {
                    Map<String, Object> d = Iso.map(row);
                    drift.add(new DriftDto(Iso.text(d.get("kind"), ""), Iso.text(d.get("path"), ""), Iso.text(d.get("expectedSha256")),
                            Iso.text(d.get("actualSha256"))));
                }
            }
            checks.add(new CheckDto(Iso.text(check.get("id"), ""), Iso.text(check.get("status"), "NOT_EVALUABLE"), drift));
        }
        return new ReconcileResultDto(Iso.flag(body.get("consistent")), List.copyOf(checks));
    }
}
