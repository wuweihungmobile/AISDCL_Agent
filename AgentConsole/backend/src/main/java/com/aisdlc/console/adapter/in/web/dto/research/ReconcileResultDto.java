package com.aisdlc.console.adapter.in.web.dto.research;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 對帳結果（契約 §1.3 {@code ReconcileResult}；API-RP-18 {@code reconcile}）：只報告、不修復；{@code consistent} 僅在全部 check 為 ok 時為真。Bridge 本文的
 * {@code expected_sha256}／{@code actual_sha256} 轉成 camelCase；沒有 {@code drift} 的 check 省略該鍵。
 */
@Schema(name = "ReconcileResult", description = "對帳結果（只報告、不修復）")
public record ReconcileResultDto(
        @NotNull boolean consistent,
        @NotNull List<CheckDto> checks) {

    /** 一項對帳檢查。 */
    @Schema(name = "ReconcileCheckDto")
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record CheckDto(
            @NotNull String name,
            @NotNull @Schema(description = "ok｜drift｜NOT_EVALUABLE") String status,
            List<DriftDto> drift) {
    }

    /** 一筆漂移（檔案內容與庫內登記的雜湊不符、檔案缺失…）。 */
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
                    drift.add(new DriftDto(Iso.text(d.get("kind"), ""), Iso.text(d.get("path"), ""), Iso.text(d.get("expected_sha256")),
                            Iso.text(d.get("actual_sha256"))));
                }
            }
            checks.add(new CheckDto(Iso.text(check.get("name"), ""), Iso.text(check.get("status"), "NOT_EVALUABLE"), drift));
        }
        return new ReconcileResultDto(Iso.flag(body.get("consistent")), List.copyOf(checks));
    }
}
