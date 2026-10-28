package com.aisdlc.console.application.port.out;

import java.io.IOException;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

/**
 * console-api 與 sidecar 之間的控制面檔案 I/O（TCS-SysAdminBackup-20261027 §C1；兩個具名卷）。console-api 對 sidecar <b>只有檔案 I/O</b>——沒有行程啟動、
 * 沒有網路呼叫（R-BK-58）。實作：{@code FileBackupControlAdapter}（純 Java 檔案 I/O，Windows 與 Linux 皆可跑）。
 *
 * <p>讀取面（輸出卷，{@code :ro,nocopy}）：以相對於 {@code export-dir} 的路徑讀（例 {@code export/info.json}、{@code results/<uuid>.json}）；
 * 缺席與讀不出來是兩件事——缺席回空，I/O 失敗（含「路徑是目錄」「不是合法 UTF-8」）丟 {@link java.io.UncheckedIOException}。解析與分類由呼叫端做。
 * 寫入面（請求卷）：寫 {@code .tmp} 後原子改名，失敗時清掉 {@code .tmp} 並丟 {@link IOException}（不丟未檢查例外）。
 */
public interface BackupControlPort {

    /** 寫給 sidecar 的請求（只有封閉詞彙的五個鍵：schema_rev、id、type、requested_at、expires_at）。 */
    record Request(UUID id, String type, Instant requestedAt, Instant expiresAt) {
    }

    /** 讀 {@code export-dir} 下的檔案文字；缺席回空；I/O 失敗丟 {@link java.io.UncheckedIOException}。 */
    Optional<String> read(String relativePath);

    /** 原子寫請求檔 {@code <request-dir>/<id>.json}（先寫 {@code .tmp}、{@code ATOMIC_MOVE} 改名）；失敗清掉 {@code .tmp} 並丟 {@link IOException}。 */
    void writeRequest(Request request) throws IOException;

    /** 刪自己的請求檔（終態後、過期後）；本來就不存在也算成功；回是否確定已不存在。 */
    boolean deleteRequest(UUID id);

    /** 啟動時清殘檔：刪除請求目錄內最後修改時間早於 {@code olderThan} 的 {@code *.json} 一般檔（不跟隨符號連結）；回刪了幾份。 */
    int deleteStaleRequests(Instant olderThan);
}
