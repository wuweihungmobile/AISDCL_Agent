package com.aisdlc.console.domain.model.engine;

/**
 * Bridge {@code GET /sdd/version} 的投影（契約 §1.7.1；D-16）。{@code root} 是 <b>Bridge 看到的</b>目錄路徑
 * （Docker 下是容器內路徑；開發機上是主機絕對路徑），僅供顯示，前端預設只秀 {@code latest}。
 *
 * @param latest SDD 版本目錄名（例 {@code AISDLC_SDD_v0.30}）
 */
public record SddVersion(String latest, String root) {
}
