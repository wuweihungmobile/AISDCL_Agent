package com.aisdlc.console.domain.model.execution;

/**
 * 引擎行程樹的資源取樣（契約 §3.1.2；D-12；US-M-10）：Bridge {@code RunStateOut.resources} 的投影，值<b>原樣</b>帶出，
 * console-api 不重算也不四捨五入。不含 pid、命令列與環境變數。
 *
 * @param cpuPercent   整機正規化的 CPU 百分比（0～100，小數 1 位）
 * @param memoryBytes  行程樹各行程 RSS 的總和（上界估計，共用頁會重複計入）
 * @param processCount 取樣當下仍存活的行程數（含引擎根行程；Windows 的 venv 啟動器會多一層殼，不得斷言精確值）
 * @param sampledAt    取樣時間，Bridge 的 ISO-8601 字串（含 offset，例：{@code …+00:00}）原樣保留
 */
public record ResourceUsage(double cpuPercent, long memoryBytes, int processCount, String sampledAt) {
}
