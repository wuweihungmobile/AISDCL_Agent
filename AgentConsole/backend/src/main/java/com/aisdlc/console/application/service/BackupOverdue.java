package com.aisdlc.console.application.service;

import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.util.List;
import java.util.Optional;

/**
 * 「逾期」的判定（TCS-SysAdminBackup-20261027 R-BK-18、R-BK-19、D-BK-T10；純函式）。前端<b>只顯示</b> {@code card.overdue}、不重算
 * （沒有 cron 函式庫、沒有寬限識別字）。時間由呼叫端傳入（取自 {@code BackupClock}）。
 *
 * <p>規則：{@code overdue = now > lastDueAt + 寬限}（<b>嚴格大於</b>；寬限預設 30 分）且「成功時間」早於 {@code lastDueAt} 且該工作<b>未進行中</b>；
 * 從未成功（狀態檔與清單皆無）⇒ {@code never=true}、{@code overdue=false}（量不到不是逾期）；cron 解析不了或回溯窗內沒有觸發 ⇒
 * {@code lastDueAt=null}、{@code overdue=false}。
 *
 * <p>成功時間＝{@code max(狀態檔 last_success_at, 清單端)}；清單端＝（已設定的各 repo 中）最近一份符合者的 {@code stop} 之<b>最舊者</b>，
 * 任一已設定 repo 沒有符合者 ⇒ 清單端缺席（保守：不能保證每個 repo 都有成功）。dump、verify 只取狀態檔（呼叫端傳空清單）。
 */
final class BackupOverdue {

    /**
     * 判定結果。{@code lastDueAt} 為 null＝算不出（cron 解析不了或窗內沒有觸發）；{@code successAt} 為 null＝從未成功。
     */
    record Result(Instant lastDueAt, boolean overdue, boolean never, Instant successAt, boolean cronUnparsable) {
    }

    private BackupOverdue() {
    }

    /**
     * @param cron         該工作的五欄 cron（可為 null：schedule.json 沒有此工作）
     * @param stateSuccess 狀態檔的 {@code last_success_at}（可為 null）
     * @param repoLatest   各已設定 repo 的最近符合備份 {@code stop}；某 repo 沒有符合者放 null；空清單＝清單端不提供
     * @param running      該工作目前進行中（進行中不逾期）
     */
    static Result evaluate(String cron, ZoneId zone, Instant now, Duration grace, Instant stateSuccess,
                           List<Instant> repoLatest, boolean running) {
        Instant listSide = listSide(repoLatest);
        Instant success = latest(stateSuccess, listSide);
        boolean never = success == null;
        boolean unparsable = cron != null && BackupCron.parse(cron).isEmpty();
        Optional<Instant> lastDue = cron == null ? Optional.empty() : BackupCron.lastDue(cron, zone, now);
        Instant lastDueAt = lastDue.orElse(null);
        boolean overdue = !never && !running && lastDueAt != null && now.isAfter(lastDueAt.plus(grace))
                && success.isBefore(lastDueAt);
        return new Result(lastDueAt, overdue, never, success, unparsable);
    }

    /** 清單端：各 repo 最近者的最舊者；沒有清單或任一 repo 缺席則缺席。 */
    static Instant listSide(List<Instant> repoLatest) {
        if (repoLatest == null || repoLatest.isEmpty() || repoLatest.contains(null)) {
            return null;
        }
        return repoLatest.stream().min(Instant::compareTo).orElse(null);
    }

    private static Instant latest(Instant a, Instant b) {
        if (a == null) {
            return b;
        }
        if (b == null) {
            return a;
        }
        return a.isAfter(b) ? a : b;
    }
}
