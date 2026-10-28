package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.architecture.BackupReasonsContractTest;
import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 備份控制面「未設定」情境（共用預設 Spring context：沒有任何 {@code console.backup.*} 設定；TCS-SysAdminBackup-20261027 AT-BK-05-1-1、AT-BK-05-1-2；R-BK-23）。
 * 為什麼重要：不在 Docker 全棧（例如本機 bootRun）時，備份頁必須<b>明說</b>「備份控制面未設定」，不能把「沒有設定」讀成「沒有備份」或 0 份——
 * 那會讓掌舵者以為資料庫沒有備份而恐慌，或更糟：以為備份正常。所以 200 加 {@code control.reason=not_configured}、所有資料區塊為 null（不是空陣列或 0）；
 * 觸發則一律 503 {@code backup_control_unavailable}，且零列、零檔（沒有目錄可寫）。
 */
class BackupApiUnconfiguredIT extends AbstractApiIT {

    private static final String BACKUPS = "/api/v1/sysadmin/backups";

    @Test
    void AT_BK_05_1_1_everyRoleGetsAnHonestNotConfiguredEnvelopeWithAllDataBlocksNull() {
        for (String token : List.of(viewer(), operator(), admin())) {
            Resp resp = api.get(token, BACKUPS);

            assertThat(resp.status()).isEqualTo(200);
            assertThat(resp.<Boolean>read("$.data.control.available")).isFalse();
            assertThat(resp.<Boolean>read("$.data.control.canTrigger")).isFalse();
            assertThat(resp.<String>read("$.data.control.reason")).isEqualTo("not_configured");
            assertThat(resp.<Object>read("$.data.control.heartbeatAgeSeconds")).isNull();
            assertThat(resp.<Object>read("$.data.control.exportAgeSeconds")).isNull();
            assertThat(resp.<Object>read("$.data.control.exportGeneratedAt")).isNull();
            assertThat(resp.<List<Object>>read("$.data.control.warnings")).isEmpty();
            for (String block : List.of("cards", "backups", "schedule", "repos", "walArchive", "activeJob", "timezone")) {
                assertThat(resp.<Object>read("$.data." + block)).as("資料區塊 %s 必須是 null（不是 [] 或 0）", block).isNull();
            }
            assertThat(resp.body()).as("鍵都在、只是 null").contains("\"cards\":null").contains("\"backups\":null").contains("\"walArchive\":null");
        }
        assertThat(api.get(null, BACKUPS).status()).as("沒有 token ＝ 401").isEqualTo(401);
    }

    @Test
    void AT_BK_05_1_2_triggeringWithoutAConfiguredControlPlaneIsA503WithNoRowsAndNoFiles() {
        Resp resp = api.post(admin(), BACKUPS + "/jobs", Map.of("type", "full", "confirm", true));

        assertThat(resp.status()).isEqualTo(503);
        assertThat(resp.<String>read("$.reason")).isEqualTo("backup_control_unavailable");
        assertThat(resp.has("$.data")).as("任何失敗都沒有 data").isFalse();
        assertThat(resp.<String>read("$.message")).isEqualTo(BackupReasonsContractTest.apiMessagesUnchecked().get("backup_control_unavailable"));
        assertThat(jdbc.queryForObject("select count(*) from console.backup_jobs", Integer.class)).as("零列").isZero();
    }
}
