package com.aisdlc.console.application.port.in;

import java.time.Instant;
import java.util.Map;

/**
 * 手動觸發備份（{@code POST /backups/jobs}；TCS-SysAdminBackup-20261027 §C3.4、D-BK-T13；API-BK-04）。呼叫者的角色（僅 ADMIN）由安全層把關。
 *
 * <p>驗證序固定（先中者定案，任一前序失敗都零列、零檔）：本文是 JSON 物件（框架）→ {@code type} 合法（422 {@code invalid_request}）→
 * {@code confirm} 為布林 true（400 {@code backup_confirm_required}）→ 控制面可用（503 {@code backup_control_unavailable}）→ 無進行中
 * （409 {@code backup_job_in_progress}）→ 頻率（409 {@code backup_too_frequent}）→ 建列並寫請求檔。
 */
public interface BackupJobUseCase {

    /** 202 的回應內容：{@code status} 恆為 {@code QUEUED}。 */
    record Accepted(String id, String type, String status, Instant requestedAt) {
    }

    /**
     * 觸發一次工作。{@code body} 是請求本文原樣的 JSON 物件（多餘的鍵忽略、不解譯成指令；{@code id} 一律由伺服器產生）。
     *
     * @param user JWT 帳號（寫入 {@code requested_by}）
     */
    Accepted trigger(String user, Map<String, Object> body);
}
