package com.aisdlc.console.adapter.out.persistence;

/**
 * 「待簽核草案」的<b>唯一一組述詞</b>（契約 §1.4.1 的 {@code pendingSignoffs}、§1.8.1 的 {@code GET /signoffs/pending}；D-18）。
 *
 * <p>四種草案各一段 {@code FROM … WHERE …}：計數是 {@code select count(*) <段>}，清單是 {@code select <欄位> <段>}。通知摘要的總數
 * （{@link #TOTAL}）、待審批清單的四個計數（{@link #COUNTS}）與清單本身（{@link #ITEMS}）全部由這四段組出來，所以<b>不可能</b>各說各話
 * ——「頂列徽章的數字大於點得到的項目」正是 v1.3 以前儀表板清單（前端用專案與目標 API 另外組的近似）的缺陷（完整性審查 I-05）。
 * 要改判準只改這一個檔案；{@code SignoffQueueAdapter} 與 {@code NotificationCountsAdapter} 都不得自己寫第二份。
 *
 * <p>{@code is_deleted} 在 DDL 允許 NULL，一律以 {@code coalesce(…, false)} 視為未刪除。判準：
 * <ol>
 *   <li>{@code PROJECT}：{@code signed_off=false} 且未軟刪；</li>
 *   <li>{@code GOAL}：{@code signed_off=false} 且未軟刪，且所屬專案未軟刪；</li>
 *   <li>{@code TASK}：{@code signed_off=false} 且未軟刪，且所屬目標與專案都未軟刪；</li>
 *   <li>{@code IMPORT}：狀態是 {@code PARSED}／{@code REVIEWING} 且 {@code signed_off=false}（{@code UPLOADED}、{@code PARSING} 尚無可簽核內容；
 *       {@code IMPORTED}、{@code REJECTED} 是終態，皆不計）。</li>
 * </ol>
 */
final class PendingSignoffSql {

    private static final String PROJECT_FROM = """
            from console.projects p
            where p.signed_off = false and coalesce(p.is_deleted, false) = false
            """;

    private static final String GOAL_FROM = """
            from console.goals g join console.projects p on p.id = g.project_id
            where g.signed_off = false and coalesce(g.is_deleted, false) = false
              and coalesce(p.is_deleted, false) = false
            """;

    private static final String TASK_FROM = """
            from console.tasks t
              join console.goals g on g.id = t.goal_id
              join console.projects p on p.id = g.project_id
            where t.signed_off = false and coalesce(t.is_deleted, false) = false
              and coalesce(g.is_deleted, false) = false and coalesce(p.is_deleted, false) = false
            """;

    private static final String IMPORT_FROM = """
            from console.import_records i
            where i.status in ('PARSED', 'REVIEWING') and i.signed_off = false
            """;

    /** 四個計數一次取出（同一個敘述＝同一個快照）：欄位 {@code projects}、{@code goals}、{@code tasks}、{@code imports}。 */
    static final String COUNTS = "select (select count(*) " + PROJECT_FROM + ") as projects, "
            + "(select count(*) " + GOAL_FROM + ") as goals, "
            + "(select count(*) " + TASK_FROM + ") as tasks, "
            + "(select count(*) " + IMPORT_FROM + ") as imports";

    /** 通知摘要的 {@code pendingSignoffs}：四個計數的總和（{@link #COUNTS} 的同一組述詞）。 */
    static final String TOTAL = "select (select count(*) " + PROJECT_FROM + ") "
            + "+ (select count(*) " + GOAL_FROM + ") "
            + "+ (select count(*) " + TASK_FROM + ") "
            + "+ (select count(*) " + IMPORT_FROM + ")";

    /**
     * 清單：欄位 {@code kind、id、project_id、project_name、parent_id、title、created_at}；依 {@code created_at} 升冪（NULL 排最後）、
     * 同值以 {@code id} 升冪（決定性），前 {@code ?} 筆。{@code IMPORT} 項沒有專案（{@code confirm} 之前還沒建專案），三個欄位為 NULL；
     * 標題是檔名，貼上文字沒有檔名（NULL 或空白）時為「貼上文字」。
     */
    static final String ITEMS = "select kind, id, project_id, project_name, parent_id, title, created_at from ("
            + "select 'PROJECT' as kind, p.id as id, p.id as project_id, p.name as project_name, "
            + "cast(null as uuid) as parent_id, p.name as title, p.created_at as created_at " + PROJECT_FROM
            + "union all select 'GOAL', g.id, p.id, p.name, p.id, g.name, g.created_at " + GOAL_FROM
            + "union all select 'TASK', t.id, p.id, p.name, g.id, t.name, t.created_at " + TASK_FROM
            + "union all select 'IMPORT', i.id, cast(null as uuid), cast(null as text), cast(null as uuid), "
            + "coalesce(nullif(btrim(i.source_file_name), ''), '貼上文字'), i.created_at " + IMPORT_FROM
            + ") pending order by created_at asc nulls last, id asc limit ?";

    private PendingSignoffSql() {
    }
}
