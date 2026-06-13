# ADR-AGT-001 — 工具自主使用：ToolInvocationPort + allowlist 安全閘

| 項目 | 內容 |
|------|------|
| 編號 | ADR-AGT-001 |
| 狀態 | **ACCEPTED — koalawu 2026-06-13（SCG-2 🔴 AskUserQuestion 互動核准）** |
| 落地狀態 | **PLANNED → 實作啟動**（Phase 3 F-A2，先行；SCG-3 介面凍結後開工） |
| 提出者 | sd-architect（Improving_012 Phase 3） |
| 提出日期 | 2026-06-13 |
| 對應計畫 | [AutoClaude_Improving_012.md](../AutoClaude_Improving_012.md) §1 F-A2 / §4 風險（SCG-0 已凍結） |
| 相依 ADR | ADR-SD08-004（IObservabilityPort，審計 log 通道）/ ADR-SD07-001（LOC 分級） |

> ✅ **SCG-2 已確認**（koalawu 2026-06-13）：決策凍結；SCG-3 介面凍結後實作 F-A2（先行）。

## 1. 背景

A 能力「工具自主使用」缺口：AutoClaude 本體無統一工具抽象。PtyExecutor 委派之 Claude Code CLI 雖內建 WebSearch/WebFetch，但在 AutoClaude 層缺乏可治理（allowlist / 審計）的對外 I/O 抽象。直接開放任意 URL/API 呼叫為**高風險**（凍結計畫 §4）。

## 2. 決策

1. **新增 `IToolInvocation` port**（`core/ports/tool_invocation.py`，Protocol）：單一入口 `invoke(ToolRequest) -> ToolResult`，kind ∈ {web_search, http_request, send_message}（ports 12→13）。
2. **預設 deny 安全閘**：`config.tool_invocation.enabled` 預設 `False`；即使啟用，`allowlist` 空 = 全拒。放行依據唯一為 allowlist domain 比對（純本地，不呼叫 Brain）。
3. **全程審計**：放行與拒絕皆經 `IObservabilityPort` 寫審計 log（kind/target/allowed/audit_id）。
4. **send_message 不開放任意端點**：僅延伸既有 notification，經 **EventBus 委派** `notification_plugin`（不直接 import，遵守 importlinter Rule 1）。
5. **feature flag 上線**：`enabled=False` 預設，flag-off 零行為變更（比照 AlertLadder）。

## 3. 後果

- **正面**：對外 I/O 集中可治理；預設 deny + 審計達成「最小權限 + 可稽核」；與 CLI 內建工具正交不衝突；零既有流程回歸（flag-off）。
- **負面/成本**：新增 1 port + 1 adapter + config 區段；adapter 須守 LOC ≤400。
- **importlinter**：新 port 為 Protocol（core 不依賴 infra）；是否需新增 contract（如「plugin 不直接 import IToolInvocation」）待 SCG-3 介面凍結時評估。

## 4. 替代方案

| 方案 | 否決理由 |
|------|---------|
| 直接用 CLI 內建工具、不做 AutoClaude 層抽象 | 無 allowlist / 審計治理，無法滿足 §4 安全風險緩解 |
| 每種工具一個 port | 過度抽象（Rule 2）；單一 `invoke` + kind 已足夠 |
| 預設 allow + 黑名單 | 違反最小權限；新端點預設可達，風險高 |

## 5. SCG-2 🔴 確認（✅ 已確認 koalawu 2026-06-13）

- [x] 安全閘設計（預設 deny + allowlist + 審計）接受
- [x] send_message 委派模式接受
- [x] port/adapter/flag 落點接受

**確認人**: koalawu　**日期**: 2026-06-13　**方式**: 親簽（AskUserQuestion 互動核准後回填，流程改善 #4）
