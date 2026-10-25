package com.aisdlc.console.application.port.in;

import java.time.OffsetDateTime;
import java.util.List;

/**
 * Console 稽核列與 SelfImproving 帳本的對帳讀面（TCS-SelfImprovingDecide-P2b W14；PRD AC-SI-33-2、AC-SI-35-5）。
 *
 * <p><b>對帳在 backend 一次全量做</b>（前端的清單分頁只載入部分帳本，逐頁判會把「在後面頁」的已入帳誤報成待入帳）：以 Bridge 的
 * {@code observations}、{@code events} 各自 {@code limit=500} 迴圈取頁（上限各 20 頁）。「已入帳」＝帳本有同 {@code audit_ref} 的
 * {@code dec}／{@code obs.add}／{@code obs.close} 事件，或 {@code marks_kv.audit_ref} 相同的觀察列。<b>讀路徑唯一的副作用</b>是把 obs-add 稽核列
 * 的 {@code subject_id}（NULL）依帳本的新列號回填（冪等）。量不到（Bridge 失敗、逾時、頁數超限）＝{@code NOT-EVALUABLE}：
 * {@code ingested} 與 {@code orphans} 為 {@code null}、不回填，<b>絕不</b>以空陣列或 {@code false} 冒充「沒有待入帳」。
 */
public interface SiReconcileUseCase {

    /** {@code limit} 的預設與上限。 */
    int DEFAULT_LIMIT = 100;
    int MAX_LIMIT = 500;

    /** 對帳狀態：{@code ok}。 */
    String STATUS_OK = "ok";
    /** 對帳狀態：量不到（NFR-SI-09 對稱）。 */
    String STATUS_NOT_EVALUABLE = "NOT-EVALUABLE";

    /**
     * @param limit 1～{@value #MAX_LIMIT}；{@code null}＝{@value #DEFAULT_LIMIT}；不合丟 {@code ValidationException}（400）
     */
    ConsoleWrites consoleWrites(Integer limit);

    /**
     * @param items     稽核列（時間新到舊、同刻依 {@code auditRef} 升冪；<b>沒有 body 與 mac</b>）
     * @param truncated 表內還有更舊的列
     * @param orphans   帳本中 carrier 為 console、表內卻沒有對應列的項；量不到時為 {@code null}
     */
    record ConsoleWrites(List<Item> items, boolean truncated, List<Orphan> orphans, Reconcile reconcile) {

        public ConsoleWrites {
            items = List.copyOf(items);
            orphans = orphans == null ? null : List.copyOf(orphans);
        }
    }

    /**
     * @param subjectId decide＝PROP 號（resume 為 RUN 號）、obs-close＝OBS 號、obs-add＝入帳後回填的新列號（入帳前為 {@code null}）
     * @param digest    只有帶卡面 digest 的六種動詞才有
     * @param ingested  帳本是否已有這筆；量不到時為 {@code null}
     */
    record Item(String auditRef, String kind, String user, String role, OffsetDateTime time, String subjectId, String digest,
                String keyId, Boolean ingested) {
    }

    /**
     * @param kind    {@code decide}｜{@code obs-add}｜{@code obs-close}
     * @param subject dec 的 prop（resume 為 run）、observation 列的 id、obs.close 的 obs
     */
    record Orphan(String auditRef, String kind, String subject) {
    }

    /**
     * @param status     {@value #STATUS_OK}｜{@value #STATUS_NOT_EVALUABLE}
     * @param reason     量不到的原因：{@code si_unavailable}｜{@code bridge_unreachable}｜{@code bridge_timeout}｜{@code scan_cap_exceeded}；ok 時為 {@code null}
     * @param backfilled 本次回填 {@code subject_id} 的筆數
     */
    record Reconcile(String status, String reason, int backfilled) {
    }
}
