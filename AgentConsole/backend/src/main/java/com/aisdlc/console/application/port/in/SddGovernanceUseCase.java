package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectDetailView;
import com.aisdlc.console.domain.model.engine.SddFsmState;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * SDD 治理：核准凍結（人工閘，API-SGN-06）與編輯專案的 FSM 專案（API-PRJ-08）。契約 §1.10.2、§1.10.7；D-115-03、D-115-14。
 * 這是 Console 對 FSM 唯一的寫入動詞所在（v1.5 起；經 Bridge 的 {@code :freeze}，Bridge 再經 CLI 子行程寫 FSM 狀態檔）。
 */
public interface SddGovernanceUseCase {

    /**
     * 核准凍結請求（未驗證的原始值；用例在專案存在之後才驗，違規 400）。
     *
     * @param reason          核准理由（去前後空白後 1～500 字元、無控制字元）；寫進 FSM {@code decision_trace} 與稽核
     * @param stage           選填；{@code ^[A-Za-z0-9._-]{1,64}$}；省略＝Bridge 用 {@code Stage-<n>}
     * @param docs            選填（null）；相對專案根的 POSIX 路徑 1～20 項；省略＝專案已綁定的規格檔
     * @param expectedDigests 選填；核准人當時看到的摘要 {@code {<docs 內路徑>: "sha256:<64 hex>"}}
     */
    record FreezeRequest(String reason, String stage, List<String> docs, Map<String, String> expectedDigests) {
    }

    /**
     * 核准凍結：{@code HUMAN_PENDING → SPEC_FROZEN}（契約 §1.10.2 驗證順序）：404 專案 → 400 請求驗證 → 503 沒有寫入權杖 →
     * 唯讀取標準鍵 → 綁定唯一性檢查與寫回（短交易，先於 Bridge 寫入）→ Bridge {@code :freeze}。非冪等。
     *
     * @param approver 一律取 JWT subject（人工 signoff 不可匿名，也不可由 client 指定）
     * @return 凍結後的 FSM 狀態（與 {@code GET /engines/sdd} 的 {@code fsm} 同形）
     */
    SddFsmState freeze(UUID projectId, FreezeRequest request, String approver);

    /**
     * 編輯專案的 FSM 專案鍵（改綁）：存入去空白後的值，<b>不檢查狀態檔是否存在、不呼叫 Bridge</b>；先檢查唯一性（409
     * {@code sdd_binding_conflict}）；相同值再送＝冪等（不寫稽核）。
     *
     * @param sddProject 新的鍵；null＝清除，回到「用預設」（專案名）。非 null 須去前後空白後 1～100 字元且無控制字元（否則 400，欄位 {@code sddProject}）
     */
    ProjectDetailView bind(UUID projectId, String sddProject);
}
