package com.aisdlc.console.domain.model.engine;

import java.util.List;

/**
 * Bridge {@code GET /sdd/fsm} 的回應（契約 §3.1.3）：{@code <SDD_ROOT>/build/reports/fsm/} 底下符合 {@code FSM-STATE-<name>.yaml}
 * 的專案清單（依專案名不分大小寫升冪，console-api 不重排）。
 *
 * @param root     SDD 版本目錄名
 * @param errors   讀不動的<b>檔名</b>（不含路徑與內容）；console-api 只記 WARN 日誌，<b>不轉發</b>給前端
 */
public record SddFsmList(String root, List<SddProjectEntry> projects, List<String> errors) {

    public SddFsmList {
        projects = projects == null ? List.of() : List.copyOf(projects);
        errors = errors == null ? List.of() : List.copyOf(errors);
    }
}
