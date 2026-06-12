# Improving012 Phase 0 凍結後 Next Action

**日期**: 2026-06-13 | **狀態**: Phase 0 ✅ 完成（SCG-0 凍結，tag `v2026.06.12-02`，commit `94ea1f9`）
**權威計畫**: [AutoClaude_Improving_012.md](../04_planning/AutoClaude_Improving_012.md)（已凍結，範圍變更須重開變更單重走 SCG-0）

## Phase 0 結果摘要

- 三方（Architect / SA·SD / QA）zero-trust audit：初始 P0=0 / P1=6（跨角色重複 1）/ P2=8 → **全數修復、無豁免**；複審期抓出修復自身引入之 P0=1（CLAUDE.md:4 行長 842cp 破 contract test）即修；2 輪 QA 複審 PASS。
- nightly 親跑 run_id=233820 六 stage 全綠（TD-N01/N02/N03 錨點 log:227/125/243；前 4 跑 perf BLOCK 經對照實驗定位為 PowerShell 載具 CPU 量測膨脹偽陽性，分析已入計畫文件 §3 下方取證）。
- 最終閘門：full pytest 2,853 passed / 122 skipped、mirror tests/tools/ 421、importlinter 7 kept、LOC violations=0、snapshot OK。

## Next Action（依凍結計畫順序）

1. **Phase 1 — 記憶基座（C 能力）**：先過 SCG-1（SRD 增補 + Port 介面規格 🔴）→ SCG-2（ADR-AGT-003 記憶分層 🔴）→ 依序 F-C3（KB metrics 持久化，P0）→ F-C1（PreferenceStore）→ F-C2（GoalProgressLedger）。
2. **Phase 2 — 閉環強化（B 能力）**：F-B1 AlertLadder（feature flag 預設 off）→ F-B2 Correction 效果事後驗證。
3. **Phase 3 — 自主拆解與工具（A 能力）**：F-A2 ToolInvocationPort + allowlist → F-A1 GoalDecomposer（🔴 signoff）。

## Audit 遺留 backlog（本輪未修，非阻斷）

| 項目 | 說明 | 建議時點 |
|------|------|---------|
| ruff 鎖版 + 全量清理 | pyproject 僅 `ruff>=0.4` 未鎖版，本機 0.15.12 對全 codebase 報 ~1,330 errors；ci.yml 不跑 ruff（僅 lint-imports）。本輪僅清掉觸碰檔 4 違規 | 鎖版後一次性清理，另開工作項 |
| `AutoClaude_Guide.md` 升版 | 自我標示為 R61 快照（9 ports / 13 plugins / 2,732 基線），數字已過時 | 與 Phase 1 文件更新一併處理 |
| 巢狀 repo 對齊 | `AutoClaude/` 為巢狀 git repo（branch `sprint/sd_09_phase9`，有未 commit 變更）；monorepo 快照與巢狀 repo 歷史並行，nightly log 之 branch/commit 取自巢狀 repo | 由人工決定巢狀 repo commit/merge 策略 |
