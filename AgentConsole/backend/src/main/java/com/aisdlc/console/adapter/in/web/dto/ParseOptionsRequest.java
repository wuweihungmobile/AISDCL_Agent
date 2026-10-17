package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.imports.ParseOptions;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.util.UUID;

/**
 * 觸發 AI 解析的選項（契約 §1.1.3）。{@code executionPath} 的絕對路徑格式由用例驗（400）；Bridge 的 allowlist 在執行時才驗。
 *
 * <p>v1.5（契約 §3.3.2 補充、§1.10.8）的 {@code specFile}／{@code sddProject}／{@code targetProjectId} 三個選填欄位只對路徑 A 有意義：
 * {@code specFile} 須與明示的 {@code specDir} 並用（用例驗，400）；帶 {@code targetProjectId} 時 {@code executionPath}／{@code sddProject}／
 * {@code specDir}／{@code specFile} 取自目標專案，請求另帶不同值 → 409 {@code sdd_binding_conflict}。
 */
@Schema(name = "ParseOptions")
public record ParseOptionsRequest(
        @Min(value = 1, message = "自治等級必須介於 1 到 10") @Max(value = 10, message = "自治等級必須介於 1 到 10")
        @Schema(description = "預設 3；也成為落庫專案的 autonomyLevel", defaultValue = "3") Integer autonomyLevel,
        @NotBlank(message = "執行路徑不能為空") @Size(max = 500, message = "執行路徑長度不可超過 500 字元")
        @Schema(description = "專案執行路徑（絕對路徑格式：POSIX、磁碟機代號或 UNC）") String executionPath,
        @Size(max = 4000, message = "補充說明長度不可超過 4000 字元") String additionalPrompt,
        @Size(max = 500, message = "specDir 長度不可超過 500 字元")
        @Schema(description = "明示的 SDD 規格目錄（絕對路徑）；省略則以 executionPath 探測") String specDir,
        @Size(max = 500, message = "specFile 長度不可超過 500 字元")
        @Schema(description = "v1.5：要編譯的規格檔——相對 specDir 的 POSIX 路徑，或 specDir 之下的絕對路徑；須與明示的 specDir 並用，單獨帶 → 400")
        String specFile,
        // 只放一條約束（長度與控制字元同一個 pattern）：兩條各自判一半時，過長或空字串會同時違反兩條而回兩筆同欄位的錯誤；
        // minLength／maxLength 改由 @Schema 文件化（契約 yaml 的 ParseOptions.sddProject：minLength 1、maxLength 200、pattern 同下）
        @Pattern(regexp = "^[^\\x00-\\x1f\\x7f]{1,200}$", message = "sddProject 須為 1～200 字元，且不可包含控制字元")
        @Schema(minLength = 1, maxLength = 200,
                description = "v1.5：FSM 專案名的有效值（可以是原名；Console 不淨化，由 Bridge 的淨化鏡像處理）；帶 targetProjectId 時取自目標專案，"
                        + "請求另帶不同值 → 409 sdd_binding_conflict") String sddProject,
        @Schema(description = "v1.5：併入既有專案（Console 專案是錨）；目標專案須存在且未軟刪除（否則 404）；省略＝建立新專案") UUID targetProjectId) {

    public ParseOptions toDomain() {
        return new ParseOptions(executionPath, autonomyLevel, additionalPrompt, specDir, specFile, sddProject,
                targetProjectId);
    }

    /** 回應用：匯入記錄詳情的 {@code parseOptions}（契約 §1.1.9，C-10）——最近一次 parse 請求的選項，形狀與請求相同。 */
    public static ParseOptionsRequest from(ParseOptions options) {
        return new ParseOptionsRequest(options.autonomyLevel(), options.executionPath(), options.additionalPrompt(),
                options.specDir(), options.specFile(), options.sddProject(), options.targetProjectId());
    }
}
