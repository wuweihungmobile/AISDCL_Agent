# ADR-XPLAT-008 — 機械 autocompact：百分比旋鈕而非 token 數，84/94 訊號帶

- **狀態**：Accepted（R92 掌舵者裁決：「compaction 要真的被執行，不能只靠模型自律；context 訊號各喊一次」；閾值 84/94 為主控裁決的錯開值）
- **日期**：2026-08-15
- **平台**：量測在 macOS（claude 2.1.233，本機 binary 逐字驗證）；設定鍵為 harness 官方契約，平台中立
- **上游**：[ADR-XPLAT-004](ADR-XPLAT-004-token-endurance-protocol.md)（context 水位守衛／續航）
- **改動面**：根 `.claude/settings.json`（頂層 `autoCompactEnabled` ＋ `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`）；`.claude/hooks/context_budget_guard.py`（75/90 → 84/94）；PRD v2.1 `CONTEXT_COMPACT_PERCENT` 75 → 84

---

## 1. 問題

掌舵者要求「約 90% 就壓縮、絕不撞頂」且**機械執行**。官方結論（zero-trust 重驗）：模型無法自己下 `/compact`、hook 只能通知不能觸發 ⇒ 唯一機械化管道是 harness 自己的 autocompact。可用旋鈕三個（settings.md 逐字）：

- `autoCompactEnabled`（settings 頂層，預設 `true`）：*"Automatically compact the conversation when context approaches the limit."*
- `autoCompactWindow`（settings 頂層，`100000`–`1000000` tokens）：*"How full the context window gets before Claude Code compacts automatically, in tokens"*；*"When unset, Claude Code uses a window tuned for your model."*（本機 binary 逐字：`autoCompactWindow:ut().int().min(1e5).max(1e6).optional()`）
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`（env-vars.md 逐字）：*"Set the percentage (1-100) of the auto-compact window at which auto-compaction triggers. Use lower values like 50 to compact earlier; the variable can't raise the threshold"*；*"Applies to both main conversations and subagents"*（本機 binary 內該名字命中 3 處，與 `CLAUDE_CODE_AUTO_COMPACT_WINDOW`、`DISABLE_AUTO_COMPACT` 同住已知 env 名冊）

## 2. 裁決

**落 `autoCompactEnabled: true` ＋ `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=90`；刻意不落 `autoCompactWindow` token 數。**

百分比制在任何 window 變體上都對；「只能調低」使方向恆安全（絕不撞頂）。`autoCompactWindow` 寫死 token 數被否決的三條理由各自獨立成立：

1. **repo 層設定跟著 checkout 走**：本 repo session 的模型 window 未知（200K／1M 皆實際出現過），任何寫死 token 數對其中一種變體必錯——與 `.claude/settings.json` 內 R78 拒釘 `AUTOSDD_CONTEXT_WINDOW=1000000` 的既有判例逐字同型。
2. **guard 把該鍵讀成釘死分母**（`context_budget_guard.py` 的 `SOURCE_PINNED_CC_SETTING`）：釘 900000 會讓守衛在 200K session 的真硬線結構性靜默（危險方向）；釘 180000 會把 1M session 的壓縮點砍到 18%。
3. **機械鎖已禁止**：`tools/tests/test_context_budget_guard.py::SettingsChainTest::test_the_repo_settings_carries_neither_window_key`——repo settings 出現 `autoCompactWindow`／`model` 即紅（e2e 隔離前提）。

## 3. 訊號帶 84/94（為何不是 85/95）

主控原裁 85/95 與額度尺出廠錨點（`quota_policy` 的 `PREPARE_PCT=85`／`HALT_PCT=95`，使用者原文、PRD 憲法量）**同值相撞**；兩把尺分母不同（context window vs 額度視窗），同值會讓讀者把百分比認錯尺，且 `test_quota_thresholds_are_not_the_context_thresholds` 機械釘住不得同值。主控改裁 **84/94**（動新尺、不動憲法尺）：84＝機械 autocompact 點（PCT=90 ⇒ ~90%）之前的收斂前置訊號；94＝「壓縮沒發生」的失效警報——autocompact 正常時結構上走不到，走到即代表機械路徑失效，訊息附 `--check-autocompact` 現查指引與可重啟點任務書 SOP。

## 4. 誠實劃界（R92 複審 C-01 改寫——Q-1 修復後仍然真實的三條）

- **posture 的 `enabled` 是保守合併，不是 CC 的有效語意**：`autocompact_posture()`（R92 起）對 settings 鏈**逐檔各讀一次**，任一層 `autoCompactEnabled: false` 即報關閉——而 CC 的有效值走 first-wins，高優先層的 true 蓋得掉低層的 false ⇒ 兩者刻意不同。posture 的職責是「把有人關過它攤在陽光下」，訊息因此只點名該層＋說「可能仍開啟」，不斷言現在關著（只有 kill env 那款可以斷言，機械鎖＝`AutocompactPostureTest`）。
- **pct override 的讀取面**：優先讀行程 env（CC 注入的有效值）；行程 env 沒有時退而掃 settings 鏈各層的 `env` 區塊（B-02），拿到的是**宣告值不是有效值**——launchd／獨立 shell 下兩者可能不同，posture 不宣稱分辨得出。
- **PCT=90 的分母是「auto-compact window」**（未設 `autoCompactWindow` 時＝模型調校值，官方未公開其與全 window 的比例），非模型全 window ⇒ 「84% 訊號 < 壓縮點」的順序宣稱**不可證**，只能說方向安全：實際觸發點只會 ≤ 名義值（至多提早壓縮／多喊一次，不會晚喊）。
