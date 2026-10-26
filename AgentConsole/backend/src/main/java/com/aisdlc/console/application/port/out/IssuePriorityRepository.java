package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.issue.IssuePriority;

import java.util.Collection;
import java.util.Map;

/**
 * 議題優先順序表（{@code console.issue_priority}；TCS-IssueCenter-20261027 R-IC-59、§C6）的出站埠。寫入面只有兩個動作——{@link #upsert}
 * 與 {@link #delete}（資料庫端各一條敘述），加一個唯讀查詢。唯一的實作是 JDBC 配接器（整個 backend 唯一存取這張表的類別，ArchUnit 鎖住）。
 *
 * <p>失敗（資料庫不可用等）一律以 Spring 的 {@code DataAccessException} 丟出、<b>不吞</b>：讀不到順位表時整個請求失敗，不回缺 priority 的清單
 * （那會把「量不到」顯示成「未排」）。
 */
public interface IssuePriorityRepository {

    /** 以議題編號查順位（一次查詢）；沒有列的編號不在結果內。{@code issueIds} 為空時不查詢、回空 Map。 */
    Map<String, IssuePriority> findByIssueIds(Collection<String> issueIds);

    /** 新增或覆寫該議題的順位（單列原子：並發時恰留一列、值完整，後提交者生效）。 */
    void upsert(IssuePriority priority);

    /** 刪除該議題的順位；列不存在也不是錯（冪等）。 */
    void delete(String issueId);
}
