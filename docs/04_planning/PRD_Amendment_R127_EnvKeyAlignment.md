# PRD v2.1.15 施工圖 — §6 三鍵前綴對齊 ＋ `CONFLICT_POLICY` 三值行為補述（DEF-200-206）

> **Status**: Adopted（掌舵者 2026-09-02 採 R121 呈報單 `DEF-200-206` 方向 A；R127 三方設計複審
> Architect／SA／SD 各自獨立審 Q1～Q5，條件已於同批落款；程式面同批落地並過定點複審）。
> **對象 PRD**：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（修訂表 v2.1.15 列）。
> **體例**：依「一版號一施工圖」慣例另開本檔；主 PRD 只改鍵名字面、補述與痕跡，不改既有條文語意
> （R110 判例不疊層）。

## §0 立案（帳本 `DEF-200-206`，R100 交付稽核 B4／B5／B6）

| 鍵 | PRD 側（修前） | 實作側（修前） | 歧異 | 裁決 |
|---|---|---|---|---|
| `STATE_RETAIN_VERSIONS` | §6 區塊 12 無前綴、值 5 | `file_state_repository.py` 讀 `AUTOCLAUDE_STATE_RETAIN_VERSIONS`、預設 2 | 前綴＋值 | ① **修憲**（前綴跟隨全庫 `AUTOCLAUDE_*` 慣例）；值 **採 5**（R127 三方定案） |
| `CONFLICT_POLICY` 枚舉 | 三值 `ABORT｜RETRY_WITH_AGENT｜HUMAN_REVIEW` | `("HUMAN_REVIEW", "AUTO_AGENT")` | 互有對方沒有的值 | ② **修實作**：`AUTO_AGENT` 更名 `RETRY_WITH_AGENT`、補 `ABORT` |
| `CONFLICT_POLICY`／`DIRTY_SAVE_RETRIES` env 面 | §6 明列 | 零 `os.environ` 讀取路徑 | 改設定不生效 | ③ **修實作**：補讀取路徑；鍵名前綴同 ① |

## §1 條文變更（主 PRD 逐處）

1. **§6 區塊 11**：`CONFLICT_POLICY=HUMAN_REVIEW` → `AUTOCLAUDE_CONFLICT_POLICY=HUMAN_REVIEW`，並補三值
   行為與非法值處置的註解。
2. **§6 區塊 12**：`STATE_RETAIN_VERSIONS=5` → `AUTOCLAUDE_STATE_RETAIN_VERSIONS=5`（值域 0..9）；
   `DIRTY_SAVE_RETRIES=1` → `AUTOCLAUDE_DIRTY_SAVE_RETRIES=1`。
3. **§6.2 R-6.2-1**：補述三值各一種行為——`RETRY_WITH_AGENT` ⇒ 重排（`DRAINING` 以上與 DRY_RUN 改只登記）；
   `HUMAN_REVIEW` ⇒ 只登記；`ABORT` ⇒ **拒絕啟動**（非零退出碼、清單照列、零重排、零 worktree 寫入）。
   與不變式 12「CLI 版本未知不阻止啟動」方向相反是刻意的：`ABORT` 是人顯式 opt-in 的策略，不變式 12
   防的是系統被動漂移把守衛整個關掉（SA 複審條件）。
4. **§6.2 G1 驗收表**：控制組加 (iii) `ABORT`＋殘留項 ⇒ `problems` 非空、清單照列、零重排；空佇列放行；
   (iv) `RETRY_WITH_AGENT` 在 `DRAINING` 以上或 DRY_RUN ⇒ 只登記。
5. **§8 列 4**：`STATE_RETAIN_VERSIONS` → `AUTOCLAUDE_STATE_RETAIN_VERSIONS`（出廠值 5）。
6. **§8 列 11**：補 `ABORT` ⇒ 拒絕啟動一句。

## §2 實作（同批落地，`AutoClaude/`）

| 檔 | 變更 |
|---|---|
| `autoclaude/execution/boot_self_check.py` | `CONFLICT_POLICIES = ("ABORT", "RETRY_WITH_AGENT", "HUMAN_REVIEW")`＋具名常數；`CONFLICT_POLICY_ENV`／`conflict_policy_from_env()`（非法值原樣回傳交不變式 11 報紅）；`scan_queue()` 的 `ABORT` 分支（先於 hold）；非法字面併入 hold（只登記，不落預設重排） |
| `autoclaude/main.py` | `boot_self_check(..., conflict_policy=conflict_policy_from_env(), ...)` |
| `autoclaude/infra/adapters/dirty_worktree_rescue.py` | `DIRTY_SAVE_RETRIES_ENV`／`dirty_save_retries_from_env()`（非整數 ⇒ WARNING＋出廠值；超界 ⇒ WARNING＋既有夾取） |
| `autoclaude/core/wiring.py` | `build_worktree_rescue(...)` 傳 `retries=dirty_save_retries_from_env()` |
| `autoclaude/infra/repositories/file_state_repository.py` | 出廠值 `"2"` → `"5"` |
| `.env.example` | 三鍵登記（皆有讀者；平常留註解） |

## §3 驗收（回歸鎖）

- `tests/test_r100_boot_self_check.py`：PRD 鏡射鎖 `test_def_200_206_the_policy_enum_mirrors_the_prd_literal`
  （讀 PRD §6 那一行的枚舉字面比對 tuple 與出廠值）；`ABORT` 三支（有殘留項拒絕啟動／空佇列放行／不被
  DRY_RUN 與 DRAINING 軟化）；env 讀取（未設／設了／非法）；非法值＋非空佇列不重排；`main` 接線鎖。
- `tests/test_r100_dirty_worktree_rescue.py`：`test_def_200_206_dirty_save_retries_is_read_from_env`（含 caplog）。
- `tests/integration/test_def_200_205_production_wiring.py`：`test_wiring_reads_dirty_save_retries_from_env`。
- `tests/test_r100_power_loss_protection.py` 既有值域斷言 `0 ≤ STATE_RETAIN_VERSIONS ≤ 9` 對出廠值 5 仍成立。

## §4 三方複審結論摘要（Architect／SA／SD，`model: sonnet`，唯讀）

| 題 | Architect | SA | SD | 落地時採納的條件 |
|---|---|---|---|---|
| Q1 出廠值 2 vs 5 | APPROVE（分層正確） | AWC：採 5，否則理由須寫回 PRD | AWC：兩邊同值即可；另立列追蹤 `retain_versions` 未接進 `estimate_freeze_bytes` 呼叫 | **採 5**；SD 的接線缺口另立帳本列 |
| Q2 前綴命名 | AWC：三處（程式 2／PRD 5／`.env.example` 引用不存在的 v2.1.15）不一致 | APPROVE | AWC：PRD 三行須同批改 | 三處同批收斂（本檔即 v2.1.15） |
| Q3 ABORT 語意 | APPROVE（先於 hold 不破壞 G3／G5） | AWC（blocking）：PRD 條文須補述 | APPROVE | R-6.2-1／§8 列 11／G1 (iii)(iv) 同批補 |
| Q4 非法值 | APPROVE | APPROVE | APPROVE；non-blocking：非法值＋非空佇列不得落預設重排 | 併入 hold ＋ 補測試 |
| Q5 ④ 複驗範圍 | APPROVE | AWC：§5／§9「查無具名項」須附證偽錨 | AWC：F5 須由能開檔者親核 | 見 `CrossPlatform_R127_Debt_Closure.md` §DEF-200-206（附 grep 座標） |
