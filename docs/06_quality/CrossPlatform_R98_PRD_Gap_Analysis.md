# R98 — 《AutoClaude Token 監控與喚醒機制 PRD v2.1》對照現況差距分析

- **日期**：2026-08-21
- **範圍**：對照 `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（全 1833 行，含附錄 A/B）逐節核對本 monorepo 現有程式碼；不預設 PRD §15.8 的目錄結構（`.autoclaude/`／`governor/`／`hooks/`），只問「PRD 要的能力落在現有哪支檔案」。
- **方法**：Read 全份 PRD；Grep/Read 核心實作檔（`tools/lib/quota_*.py`、`tools/session_resume_planner.py`、`.claude/hooks/context_budget_guard.py`、`AutoClaude/autoclaude/plugins/*`、`AutoClaude/autoclaude/core/wiring.py`）；PowerShell 工具實跑三批測試（447+408+62 passed，見 §2）；PowerShell 工具實跑 SDD↔AutoClaude 橋接的 `--compile-only`（零 token）；查既有真跑證據 `AutoClaude/docs/03_testing/AutoSDD_improving_96_bridge_e2e_pty_evidence.json`。全程未 commit／push，未動 `AutoSDD_Defect_Log.md` 既有列。

---

## 1. PRD 模組 ↔ 實作對照表

圖例：✅ 已實作　⚠️ 部分實作　❌ 未實作　➖ CLI 原生已涵蓋（依 §0.6/§15.2 決策矩陣不需自建）

### 1.1 §3 系統架構與狀態機

| PRD 概念 | 狀態 | 實作位置 / 證據 |
|---|---|---|
| 10 態具名 FSM（`INIT/CRUISING/BURSTING/THROTTLING/DRAINING/FREEZING/WAITING_RESET/LONG_HIBERNATE/RESUMING/HALTED_MANUAL`） | ⚠️ | **沒有一個持久行程在跑這個 FSM**——本 repo 的實際架構是**無狀態**：`quota_policy.decide(state, now, policy)`（`tools/lib/quota_policy.py:536`）每次呼叫都是純函式重新求值，不維護 `ControllerState.concurrency` 這種會逐步爬升的狀態。PRD 5 態水位（CRUISING/THROTTLING/DRAINING/FREEZING…）對應本 repo 的 5 段水位帶 `BAND_FREE/NOTICE/CONVERGE/PREPARE/HALT`（`quota_policy.py:106-110`，四個錨點 50/70/85/95 逐格對齊 PRD `TOKEN_WARN/DRAIN/HALT` 出廠值，由 `PrdDrainPercentMapsToTheBandsTest` 機械對帳，`quota_gate.py:427-437`）。`WAITING_RESET/RESUMING` 對應 `choose_resume_route()` 的 RESUME/FRESH/REFUSE 三態選路（`session_resume_planner.py:1074`）。`LONG_HIBERNATE` 對應 `register_endurance()`（OS 排程交棒，`session_resume_planner.py:785`）。`HALTED_MANUAL` 對應 `AUTOSDD_QUOTA_GUARD_OFF` 逃生口（性質不同：是「關掉守衛」不是「使用者暫停」）。**沒有 `BURSTING` 這個獨立具名狀態**——其語意（reset 將近、額度充裕時加速）由 `pace_near=2.0` 乘數吸收（`quota_policy.py:222`），非狀態機分支 |
| 單向鎖存（DRAINING 以上不可回落） | ✅ | `quota_latch_path()` 的 95% halt 閂鎖（`quota_gate.py:272,631-648`），一個視窗一次；band 本身雖是無狀態重算，但 halt 動作（任務書骨架＋喚醒武裝）有閂鎖防重複觸發 |
| 狀態轉移圖／遲滯進出邊界 | ❌ | 見 §1.4 平穩性機制 |

### 1.2 §4.1 遙測引擎

| PRD 概念 | 狀態 | 實作位置 / 證據 |
|---|---|---|
| T1 OTel 結構化遙測 | ❌ | 全 repo 對 `CLAUDE_CODE_ENABLE_TELEMETRY`／`OTEL_EXPORTER_PROMETHEUS_*` 零命中（`tools/`、`AutoClaude/autoclaude/` 皆掃過）。PRD §0.6 建議「採用」，本 repo 從未接線 |
| T2 逐字稿本機加總 | ⚠️ | 未做「加總 token usage」，但有**單軸地板**：`quota_gate.quota_floor_reading()`（`quota_gate.py:607`）讀逐字稿裡「未復原的撞線」事件當 100% 地板，是 T5 全滅時唯一還算數的離線證據 |
| T3 statusLine hook | ❌ | 未接 CLI 原生 statusLine（`rate_limits.*`），沒有 `.claude/statusline.sh` 或等效腳本 |
| T4 `/usage` 程式化解析 | ❌ | 未做 |
| **T5 未公開端點 `GET /api/oauth/usage`** | ✅ | **本 repo 實際的唯一認可主源**（PRD v2.1.4 修憲後的現行規範）。`tools/lib/quota_meter.py:73`（`USAGE_URL`）；四項升格依據（零 token／帳號層級權威讀數／R90 四通道實測勝出／失效 fail-safe）逐條在檔頭有量測依據；TTL≥180s 節流（`quota_gate.py:141`）；失效降級 cap（`degraded_cap=4`，`quota_policy.py:218`）。**PRD 自己的 §15.5 紅線 1 已為此開了四條件豁免**，本 repo 完全滿足該四條件（唯讀 GET／單一程式站點／TTL 節流／失效出聲） |
| 本機推估安全邊際 `LOCAL_ESTIMATE_SAFETY_MARGIN` | ❌ | 未實作——因為本 repo 走的是 T5 帳號層級權威讀數（伺服器直接算好 %），不是「本機加總」，PRD 這條假設的風險（本機看不到其他裝置用量）在 T5 路徑下不成立 |
| §4.1.2 新鮮度/逾時分級（180s→THROTTLING、600s→DRAINING、1200s→FREEZING） | ⚠️ | 有 TTL 概念（180s，`QUOTA_CACHE_TTL_SECONDS`）但過期時**直接降級為「量不到」**（`_blank("stale-cache",...)`, `quota_gate.py:410-419`）走 `degraded_cap`，不是 PRD 的三段式時間分級；語意等價（都是保守降級）但不是同一套機制 |
| §4.1.3 視窗重置偵測（`ΔU<-20pp`→清空歷史） | ✅ | 本 repo 用 R86 的跨窗攤提機制（`quota_pace.py`）+ `burn_ratio()`（`quota_gate.py:356`）處理歷時樣本；且 R93 起有 `core_signature()` 分區（換帳號/換方案時舊樣本結構上不會混入新估計池，`quota_gate.py:300-323`），比 PRD 描述的「清空緩衝」更精細（分區而非整批清空） |
| §4.1.4 帳號/方案變更偵測 | ✅ | **完整落地且已修過兩輪**：R93 首次用 `KNOWN_KINDS` 桶名集合當指紋（`quota_policy.py:144`），R93 二次訂正加入 `account_key_of()`（回應標頭 `anthropic-organization-id`/`anthropic-workspace-id` 雜湊，零額外網路/token/憑證，`quota_meter.py:620`）解決 R90 實測的桶名集合碰撞（3 命中 2 假陽性、29% 偽陰性）。ADR-XPLAT-009 全文記載 |

### 1.3 §4.2 配速控制器

| PRD 概念 | 狀態 | 實作位置 / 證據 |
|---|---|---|
| §4.2.1 EWMA 燃燒率估計 | ❌（改走等價設計） | 沒有 `V_actual`/EWMA/`BURN_RATE_EWMA_ALPHA`。改用 §4.2.8 的 `pace_index` 路線（PRD 自己在 §4.2.8 建議「以 pace_index 為主控訊號，V_eff 僅作輔助診斷」——本 repo **直接跳過 V_eff，只做 pace_index**），見 `quota_pace.py`／`quota_policy._pace_of()`（`quota_policy.py:505`） |
| §4.2.2 安全燃燒率/目標併發 `C_raw=floor(...)` | ➖（設計已被 PRD 自己取代） | 同上，PRD §4.2.8 已明說「完全免除冷啟動、EWMA 調參與視窗重置誤判」，本 repo 走的正是這條路 |
| §4.2.3 閘門優先序（8 步短路） | ✅ | `quota_policy.decide()`（`quota_policy.py:536-611`）：halt 否決一切、halt 帶不吃覆寫、保險軸不得一票否決主力（R89 憲法裁決，比 PRD 原文更進一步處理了 overage/extra_usage 這個 PRD 完全沒想到但 R87 真實炸過的坑） |
| §4.2.4 平穩性機制（遲滯/死區/±1 變化率/最小停留時間） | ❌ | 全庫零命中 `hysteresis`/`dwell`/`slew`/`遲滯`/`死區`/`停留時間`/`變化率`。**架構性原因**：本 repo 是無狀態純函式決策（每次重算），沒有「持續爬升的併發值」需要限速；PRD 的遲滯/停留時間是為了防止一個**持續運作的控制迴圈**在門檻邊界抖動，而本 repo 沒有這樣的迴圈。殘餘風險：pct 剛好卡在 70.0/85.0 邊界時，連續兩次 `--pace` 呼叫可能得到不同 band——這個風險存在但發生機率與後果都遠低於 PRD 設想的持續 Daemon 場景 |
| §4.2.5 BURSTING 判準（全部 6 條 AND，含週額度否決） | ⚠️ | 沒有獨立 BURSTING 狀態，但週額度否決這個 PRD 認為「最危險的缺漏」已用不同機制解決：`FALLBACK_KINDS`/`account_posture()` 確保保險池不會誤導主力判斷，`WEEKLY_PACE_CEILING`（`Policy.pace_ceiling` 欄位，`quota_policy.py:226`；對應 `ENV_SPEC` 項見 `tools/lib/quota_policy_env.py:83-84`）對齊 PRD §4.2.8 表列的官方配速門檻（0.9/0.72 等） |
| §4.2.6 參考實作（Python dataclass 控制器） | ➖ | PRD 自己在 §4.2.8 承認參考實作可被 pace_index 完全取代 |
| §4.2.8 pace_index 對齊 CLI 內建配速門檻 | ✅ | `Policy.pace_ceiling`（`quota_policy.py:226`）＋ `AUTOSDD_QUOTA_PACE_CEILING`（`ENV_SPEC` 項，本輪 LOC 拆分包已把 `ENV_SPEC` 搬到獨立檔 `tools/lib/quota_policy_env.py:83-84`；`quota_policy.py:636-643` 僅 re-export，函式定義本身在 `quota_policy_env.py:148`）＋ `WEEKLY_PACE_CEILING_*`／`FIVE_HOUR_PACE_CEILING` 概念由 `pace_near`/`pace_far` 乘數承接（R84/SA-01 起可由 `.env` 調） |

### 1.4 §4.3 上下文壓縮策略

| PRD 概念 | 狀態 | 實作位置 / 證據 |
|---|---|---|
| `K_ctx ≥ CONTEXT_COMPACT_PERCENT`（84%，R92 修憲） | ✅ | `.claude/hooks/context_budget_guard.py` 的水位量測；`CONTEXT_COMPACT_PERCENT` 75→84 已隨 R92 修憲同步（PRD 版本歷史 v2.1.1 逐字記載） |
| `U5h + COMPACT_COST_BUDGET_PP ≤ DRAIN_PERCENT`（三個 AND 的第二條） | ✅（R91 修復） | `quota_gate.draining()` 三態分流（`quota_gate.py:440-457`）；`DEF-200-137` 記載此條此前漏做，已 open→由 R91/R95 陸續補上（`emit_to_model` 單一發射口，`quota_gate.py:95-102`），現況為兩把尺（額度／context）各自獨立判讀後在 hook 內合流 |
| PreCompact/PostCompact hook 做 checkpoint | ➖ | PRD §0.6／B-07 已核實 CLI 原生有這兩個 hook；本 repo 未見專屬 PreCompact 腳本，但 `CheckpointPlugin`（AutoClaude 引擎層，非 hook 層）已覆蓋「壓縮/中斷前存檔」需求 |

### 1.5 §4.4 多 Agent 隔離與整合

| PRD 概念 | 狀態 | 實作位置 / 證據 |
|---|---|---|
| 自建 git worktree 管理（`.autoclaude/worktrees/`） | ➖ | PRD §0.6 自己核實 CLI 原生 `Agent(isolation:"worktree")`／`EnterWorktree`／`ExitWorktree` 已涵蓋；本 repo 確實用原生工具（`.claude/hooks/block_destructive_git.py` 明文把 `git stash create` 等列為「這是可重啟點四條件指定的保全手法」，且未見任何自建 worktree 腳本） |
| 序列化整合佇列（rebase→驗證→FF-only merge） | ❌ | 未見專屬實作；本 repo 目前是單 Daemon/單工作樹為主的執行模式（AutoClaude 引擎跑單一 playbook，不做 PRD 設想的「3 個 Agent 同時修改相鄰模組」那種平行整合），Console UI（見 CLAUDE.md 記憶〈Agent Console UI 規劃〉）是未來才要做多服務並行的規劃，尚未落地 |
| Agent 硬性預算（MAX_STEP_TURNS/WALL_SECONDS/QUOTA_PP） | ⚠️ | AutoClaude 引擎有 `MAX_STEP_TURNS` 等價概念（`--max-turns` 等 CLI 旗標／`token_guard` plugin 的 halt 判斷），但沒有 PRD 逐字要求的「該 Step 允許推升的 U5h 百分點」`MAX_STEP_QUOTA_PP` 這個精確會計欄位 |

### 1.6 §4.5 狀態保全與喚醒（PRD 篇幅最大的一章，也是本 repo 落地最深的一章）

| PRD 概念 | 狀態 | 實作位置 / 證據 |
|---|---|---|
| §4.5.1 凍結流程（各 worktree commit + state.json 原子寫入） | ⚠️ | 有「可重啟點任務書」機制（`render_plan()`/`write_relay()`，`session_resume_planner.py:792,810`）承接同等意圖，但不是 PRD 描述的「逐一 worktree commit」（本 repo 目前非多 worktree 並行架構，見 §1.5） |
| §4.5.2 分片休眠（非單次長 sleep，含時鐘跳躍偵測） | ✅ | 完全走 OS 排程交棒（schtasks/launchd 一次性喚醒任務），不是「Daemon 自己 sleep」——比 PRD 描述的分片 sleep 更徹底地解決了「機器睡著/行程掛掉」問題，因為排程本身就是跨行程存活的 |
| §4.5.3 重置驗證與喚醒（`RESET_CONFIRM_PERCENT` 後 full-jitter 重試） | ⚠️ | 有 `probe_quota()`（`session_resume_planner.py:540`）在喚醒前現查額度，但沒有 PRD 描述的 full-jitter 退避重試序列 |
| §4.5.4 喚醒策略（SESSION_RESUME/FRESH_SESSION_WITH_STATE/AUTO） | ✅ | `choose_resume_route()` 三態選路（`session_resume_planner.py:1074-1097`）：依逐字稿大小門檻（`_transcript_cap()`）自動選 `claude -p -r <sid>`（RESUME）或全新 session＋任務書交棒（FRESH）；任務書缺席時 REFUSE（不靜默派空 prompt）。**未使用 `--dangerously-skip-permissions`**（符合 PRD §12/§15.5 紅線 9），`DEF-200-143` 記載此為 R95 落地、11 支回歸鎖 |
| §4.5.5 長休眠 OS 排程交棒（跨 5h／7d） | ✅ | `register_endurance()`＋`endurance_schtasks_script()`（`session_resume_planner.py:692-785`）Windows schtasks／`schedule_backend.py` 的 `LaunchdBackend`（macOS）；四項排程設定（WakeToRun/StartWhenAvailable/DisallowStartIfOnBatteries/StopIfGoingOnBatteries）已在 CLAUDE.md 與 `install_windows_nightly.ps1` 落地 |
| §4.5.6 撞線喚醒閉環（R-4.5.6-1~6） | ✅ | `quota_escalation.py`／`sentinel_lifecycle.py` 全量落地，`DEF-200-146` 記載 R95 四修（保 RELAY／自癒＋分形／loud alert／哨兵活性欄／多軸 reset 裁決），回歸鎖見 `test_context_budget_guard.py` |
| §4.5.7 主控閒置盲區與預防性提醒（R-4.5.7-1~3） | ✅ | `quota_escalation._main_transcript_idle_seconds()`／`_idle_prepare_watch()`／`patrol_housekeeping()`（`quota_escalation.py:231,267,327`）；`DEF-200-148` 記載此為掌舵者定級 P0，已 fixed@R95（commit `1c3a4c1`），B1~B3 三支測試綠燈 |
| §4.5.8 哨兵武裝狀態漂移自癒（C1~C4） | ✅ | `sentinel_lifecycle.armed_but_missing()`＋`quota_escalation._heal_armed_drift()`；C1~C4 四支測試綠燈，PRD 本節逐字標「已實作」 |

### 1.7 §4.6 跨平台防休眠

| PRD 概念 | 狀態 | 實作位置 / 證據 |
|---|---|---|
| macOS `caffeinate -i -m -w <PID>` | ❌ | 全 repo（含 `AutoClaude/`）對 `caffeinate`/`SetThreadExecutionState`/`systemd-inhibit`/`ES_CONTINUOUS` 零程式碼命中——只在 PRD 文件本身與 3 份 ADR/HANDOFF 文件裡被討論過，從未寫成程式碼。ADR-XPLAT-007 §1.1 C12 只驗證了「這台 mac 上 `which caffeinate` 存在」，不是「本 repo 呼叫了它」 |
| Windows `SetThreadExecutionState` | ❌ | 同上，未實作 |
| Linux `systemd-inhibit` | ❌ | 同上，未實作 |
| 驗證手段（`pmset -g assertions`/`powercfg /requests`） | ➖（已有等價替代） | **架構性替代而非缺漏**：本 repo 的實際策略是「不阻止睡眠，改用 OS 排程的 WakeToRun 喚醒睡著的機器」（§4.5.5 的 schtasks/launchd 四項設定），這其實比 PRD 的「短等待用 keep-awake」更徹底——PRD 自己在 §4.6 也承認「防休眠只用於短等待，長等待改用排程器交棒」，本 repo 選擇**統一走排程器交棒**（不分短/長等待都排程），代價是極短暫等待（幾分鐘）時多一次排程開銷，但換來零平台專屬 keep-awake API 的維護面。**誠實劃界**：mac 端已知限制（CLAUDE.md〈mac 已知邊界〉）——睡著的 Mac 若電源方案未設「永不睡」，`pmset repeat` 需 sudo，本專案刻意不碰，只做到「失效可偵測」（`endurance_env.py` 的 `MacSleepPostureIsSaidOutLoudTest`） |

### 1.8 §4.7 帳號配額仲裁

| PRD 概念 | 狀態 | 實作位置 / 證據 |
|---|---|---|
| `~/.autoclaude/accounts/<fingerprint>/quota.lock`／`leases/<daemon_id>.json`（TTL 120s） | ⚠️ | **功能等價但形狀不同**：本 repo 用系統暫存目錄下的**目錄項式派發帳**（`autosdd_quota_dispatch.d/`，`quota_gate.py:174`，`quota_ledger.py`），刻意**不帶 session id**（"一個帳號、一份帳"，`quota_gate.py:168-173`）——這正是 PRD §4.7 要解決的「同帳號多專案/多 Daemon 各自以為額度充足」的問題，且因為系統暫存目錄是機器級/使用者級共用，天然涵蓋「同機多專案」情境。沒有 PRD 描述的 lease TTL／daemon_id 個別租約結構，改用滾動視窗派發率（`FANOUT_WINDOW_SECONDS=300`，`quota_gate.py:137`）+ O_EXCL 原子目錄項，理由記載於 `quota_gate.py:460-467`（in-flight 併發數在 Workflow 47/47「background 啟動即結束」的實測下恆讀 ≈0，故改記派發率） |
| Daemon 單實例鎖 `.autoclaude/daemon.lock` | ➖ | 本 repo 沒有持久 Daemon 行程（見 §1.1 架構性原因），不需要這把鎖 |

### 1.9 §5 API Key 模式

| PRD 概念 | 狀態 |
|---|---|
| `AUTOCLAUDE_AUTH_MODE=API_KEY`、`API_BUDGET_HARD_USD`、正規化層 | ❌ 未實作。本 repo 全面走 OAuth（`~/.claude/.credentials.json`／macOS Keychain，`quota_meter.py:77-100`），未見任何 API Key 模式的預算正規化層。若使用者確實只用訂閱制 Claude Code CLI（未走原生 Anthropic API Key），此節可能是低優先級；但若有計畫用 API Key 跑無人看管 CI，這整節目前是真空 |

### 1.10 §6 設定檔規範（.env.example）

| PRD 概念 | 狀態 | 實作位置 / 證據 |
|---|---|---|
| 全量 `.env.example` schema v2 | ✅（換了骨架，內容對得上） | `.env.example`（根層）由 `render_env_example()` 生成（非手寫；`ENV_SPEC` 唯一真相源現住 `tools/lib/quota_policy_env.py:60-113`——本輪 LOC 拆分包已把它從 `quota_policy.py` 搬出，`quota_policy.py:636-643` 僅 re-export；`render_env_example()` 定義本身在 `quota_policy_env.py:148`）。本輪 AST 現查：`ENV_SPEC` 實為 **21 個鍵**（16 筆 `section="policy"`〔15 筆有 `attr`、1 筆 `attr=None`：`AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES`〕＋ 5 筆 `section="escape"`：`AUTOSDD_QUOTA_GUARD_OFF`／`AUTOSDD_SENTINEL_OFF`／`AUTOSDD_CONTEXT_GUARD_OFF`／`AUTOSDD_CONTEXT_SIGNAL_OFF`／`AUTOSDD_RESUME_OFF`），訂正先前記載的「17 個鍵（14 政策鍵＋3 逃生口）」。**未逐一比對 PRD 列出的全部 ~50 個鍵**——本 repo 只生成「治理決策」相關的 16 政策鍵＋5 逃生口，PRD §6 的第 8~15 節（安全／API_KEY／狀態持久化／Git 整合／防休眠）等未落地的模組自然也沒有對應鍵 |
| §6.1 啟動自檢不變式（10 條） | ⚠️ | `policy_monotonicity_problems()`（`quota_policy.py:430`）機械守「pct 愈高 cap 愈鬆」這條不變式＋ pace 方向鎖，但沒有 PRD 逐字列的全部 10 條（如 `1≤C_min≤C_default≤C_max`——本 repo 沒有這幾個常數，因為沒有走 EWMA 併發模型） |

### 1.11 §7 state.json Schema v2

| PRD 概念 | 狀態 | 實作位置 / 證據 |
|---|---|---|
| 多 Agent 陣列、checksum_sha256、原子寫入、`resume_plan` 結構化 | ❌／⚠️ 兩套各自為政的替代品 | 全 repo 零命中 `schema_version.*2\.0\.0`／`agents":\s*\[`／`checksum_sha256` 這組 PRD 字面。實際存在**兩套不同層級的持久化**：①`AutoClaude/autoclaude/utils/checkpoint_manager.py` 的 `PlaybookCheckpoint`（單 playbook／單 session 導向：`step_idx`／`completed_step_log`／`failure_history`／各種突變計數器，`checkpoint_manager.py:30-55`）；②`session_resume_planner.py` 的「可重啟點任務書」＋ RELAY 狀態塊（`render_relay()`/`parse_relay()`，`session_resume_planner.py:428-452`，額度層級的喚醒交棒）。兩者合起來覆蓋了 PRD §7 想解決的問題（無損暫停/恢復），但**沒有一個是多 Agent 陣列**——因為本 repo 目前不是多 worktree 並行架構（同 §1.5） |

### 1.12 §9 可觀測性

| PRD 概念 | 狀態 |
|---|---|
| Prometheus/OTLP 指標（`autoclaude_u5h_percent` 等 11 個具名指標） | ❌ 未實作，全 repo 零命中 |
| 結構化決策日誌（含全部輸入變數） | ✅ 等價存在：`quota_burn.jsonl`／`autosdd_quota_degraded.jsonl`／`_append_trace()` 系列（`quota_escalation.py:291`）——每次降級/巡邏/自癒都留 JSONL 痕跡，含理由字面，但不是 Prometheus/OTLP 格式，是本 repo 自建的治理痕跡檔家族 |
| 告警（DRAINING 以上/LONG_HIBERNATE/DIRTY_UNSAVED/NEEDS_HUMAN） | ⚠️ 部分：halt/prepare 兩帶有桌面通知（`quota_escalation.notify()`），但沒有 `DIRTY_UNSAVED`／`NEEDS_HUMAN` 這兩種特定告警類型 |

### 1.13 §12 安全性

| PRD 要求 | 狀態 | 證據 |
|---|---|---|
| 唯讀本機憑證、不落痕跡 | ✅ | `quota_meter.access_token()` 明文「token 值永遠不回傳給呼叫端以外的任何地方；不進 log、不進痕跡、不進任務書」（`quota_meter.py:275-278`） |
| 不預設 `--dangerously-skip-permissions` | ✅ | `choose_resume_route()` 產生的 argv 全程沒有這個旗標（`session_resume_planner.py:1088,1095`） |
| 禁止 Agent 改治理層設定/狀態檔 | ✅ | `.claude/hooks/block_destructive_git.py` 的「治理檔禁寫」（PRD §15.5 紅線 10 對應項，`DEF-200-144` 記載已落地：`_GOV_EXACT` 白名單＋`AUTOSDD_GOVWRITE_GUARD_OFF` 逃生口） |
| 日誌遮蔽敏感字串 | ⚠️ | 未見全庫統一的 `REDACT_SECRETS_IN_LOGS` 開關，但關鍵路徑（token/憑證）本身就設計成不落痕跡（見上），敏感面沒有落地，等於不需要遮蔽 |

### 1.14 §15.4 P0～P5 分階段

| 階段 | PRD 出場條件 | 本 repo 現況 |
|---|---|---|
| P0 觀測 | 24h 零 token 觀測、燃燒率分布 | ⚠️ 沒有專屬 24h dry-run 觀測期記錄，但有 `--watch` 重量入口（`quota_meter.py:764-778`）與跨輪校準文件（ADR-XPLAT-005/007/009 皆有真實觀測數據） |
| P1 保全 | 5 秒內落盤、kill -9 後可回退 | ⚠️ 有任務書/checkpoint 機制，未見專屬「5 秒內完成」的計時驗收 |
| P2 配速 | 離線模擬器 + DRY_RUN 一週 | ❌ 沒有離線模擬器（`governor/simulate.py` 等價物不存在）；`quota_policy` 的性質測試（無抖動/無暴衝/收斂性）改用單元測試合成注入達成同等目的，但不是 PRD 要求的「一週 DRY_RUN 上線觀察」 |
| P3 閘門 | `PreToolUse` 攔截 + 動態調整併發環境變數 | ✅ `context_budget_guard.py`／`quota_gate.py` 正是這條路線（PreToolUse 攔截 `Agent`/`Workflow` 工具），比 PRD 設想的更精確（`quota_ledger` 派發率節流） |
| P4 韌性 | 帳號仲裁鎖、週上限長休眠、三平台防休眠 | ⚠️ 帳號仲裁與長休眠已做（見 §1.6/1.8），三平台防休眠未做（見 §1.7） |
| P5 硬化 | 安全 + 設定不變式 + 24h 端到端 | ⚠️ 安全面大致做到（§1.13），24h 端到端測試未見 |

### 1.15 §8 例外與邊界條件逐項核對（14 項，本輪補查——先前版本漏對照本節）

圖例同上。逐項為本輪 Grep/Read 現查（部分項起點由 SA 抽查給出，已獨立複驗；其餘 11 項為本輪新查）。

| # | PRD 異常事件 | 狀態 | 證據 |
|---|---|---|---|
| 1 | 非預期 429（full-jitter 退避、無標頭時 `sleep=rand(0,min(300,10·2^n))`，且視為遙測低估上修 `U5h`） | ❌ | SA 抽查＋本輪獨立複驗：全 `tools/lib/*.py` 對 `jitter`／`Retry-After`／`429` 零命中 |
| 2 | 重置時間漂移（醒來確認 `U5h<RESET_CONFIRM_PERCENT`，未達則 30s→300s 退避、最多 10 次） | ⚠️ | 有功能相近但形狀不同的重試：`probe_quota()`（`tools/session_resume_planner.py:540`）單次探測 + `tick_plan()`（`:565-609`）依 `MAX_PROBE_ATTEMPTS=5`（`:291`）／`TRANSIENT_RETRY_SECONDS=300`（`:297`，**固定值、非 30s→300s 遞增，也無 jitter**）決定 rearm/stop。retry 概念存在，但門檻與級距與 PRD 描述不同 |
| 3 | Git index.lock 殘留（須查 mtime **與** 持有 PID 存活，僅清陳舊者） | ❌ | SA 抽查＋本輪獨立複驗：全 repo `*.py` 對 `index.lock` 零命中 |
| 4 | 斷電／強制重啟（checksum 驗證＋原子寫入＋`resume`/`--force-fresh`＋checksum 失敗回退到最近有效版本） | ⚠️ | **原子寫入已做**：暫存檔寫入後 `tmp_p.replace(p)` 原子取代＋寫失敗即刪暫存（`AutoClaude/autoclaude/infra/repositories/file_state_repository.py:44-52`）；**`--fresh` 旗標已做**（`AutoClaude/autoclaude/main.py:90`，功能對應 PRD 的 `--force-fresh`）。**缺**：無 `checksum_sha256` 欄位——載入失敗（含 JSON 損毀）走 `except Exception: logger.warning(...); return None`（`file_state_repository.py:87-89`），效果是「這份 checkpoint 作廢、從頭開始」，而非 PRD 要的「回退到 `STATE_RETAIN_VERSIONS` 中最近的有效版本」（本 repo 一個 playbook 只留一份 checkpoint 檔，沒有版本保留） |
| 5 | 機器在等待中睡著（時鐘跳躍偵測→立即重新輪詢→若已過重置點直接 `RESUMING`） | ➖ | 架構性替代，同 §1.6 §4.5.2：本 repo 不做「Daemon 自己 sleep＋事後偵測時鐘跳躍」，改走 OS 排程（schtasks/launchd）在該喚醒的時間點**重新啟動整個行程**，喚醒後本來就會對 `probe_quota()` 做一次即時現查（見上），等於天然規避了「進程內時鐘跳躍」這個問題本身；本輪確認 `quota_escalation.py`／`session_resume_planner.py` 對「時鐘」／`clock`／「系統睡眠」等關鍵字零命中，沒有專屬的 in-process 時鐘跳躍偵測程式碼 |
| 6 | 遙測來源永久失效（依 `TELEMETRY_SOURCE_ORDER` 降級；全部失效→`DRAINING`+告警，絕不猜測用量續派工） | ⚠️ | 有等價降級：`quota_gate.py` 的 `_blank("stale-cache",...)` 等降級路徑走 `degraded_cap`（絕不放寬併發上限，等同「不猜測用量續派工」的精神）＋ JSONL 降級痕跡（`autosdd_quota_degraded.jsonl`，`_append_trace()`）；但**沒有** PRD 具名的 `TELEMETRY_SOURCE_ORDER` 多階清單（本 repo 只有 T5 主源 + T2 單軸地板兩層，非可設定清單），也**沒有**具名 `DRAINING` 狀態轉移（架構本身無狀態機，見 §1.1） |
| 7 | 同帳號多 Daemon 超燒（§4.7 帳號配額仲裁鎖+租約） | ⚠️ | 已於 §1.8 記載：功能等價的目錄項式派發帳（`quota_gate.py:174`），非 PRD 描述的 lease 檔+TTL 結構，不重複列證據 |
| 8 | Worktree 有未提交變更且無法提交（依序 `commit --no-verify`→`git stash`→patch 檔；三者皆失敗→標記 `DIRTY_UNSAVED` 並禁止自動喚醒） | ❌ | SA 抽查＋本輪獨立複驗：全 repo 對 `DIRTY_UNSAVED` 零命中（僅出現在本文件與 PRD 原文兩份 `.md`）；未見任何「三段式嘗試保存」的程式碼 |
| 9 | Agent 無回應／卡死（硬性預算逾時→優雅終止序列；連續 N 次卡死同一 Step→標記 `NEEDS_HUMAN`） | ⚠️ | **功能對應存在但標記不同名**：AutoClaude 引擎的 `ESCALATION`（超過 `max_retries` 後桌面通知 + `EscalationDump` + `PlaybookEvolver` 嘗試自動演化，見 `AutoClaude/CLAUDE.md`〈PlaybookRunner 關鍵行為〉）是「卡死同一 Step 後升級給人」的功能等價物；但**沒有** PRD 具名的 `NEEDS_HUMAN` 狀態標記寫回 state（本輪獨立複驗：全 repo 對 `NEEDS_HUMAN` 零命中，同 SA 抽查結果） |
| 10 | 喚醒後上下文已不可用（自動降級為 `FRESH_SESSION_WITH_STATE`） | ✅ | 已於 §1.6 §4.5.4 記載：`choose_resume_route()` 三態選路本身就含這條退路（`session_resume_planner.py:1074-1097`），不重複列證據 |
| 11 | 整合驗證失敗（退回佇列並記錄；`CONFLICT_POLICY` 決定是否派 Agent 修復） | ❌ | 本輪獨立複驗：全 repo `*.py` 對 `CONFLICT_POLICY`／`integration_queue` 字面零命中；先前一次寬鬆關鍵字掃描命中的 8 個檔案經覆核，全部只是巧合命中中文詞「整合驗證」（測試檔案名慣用詞，語意是「integration test」，與 PRD 的多 Agent 合併佇列無關），不構成實作證據 |
| 12 | Prompt injection（工具白名單+寫入範圍限制在 worktree+禁止未經確認網路存取+ Agent 狀態回報 schema 驗證） | ⚠️ | 部分子項有真實對應：**工具白名單（deny-by-default）已做**——`build_tool_allowlist_predicate()`（`AutoClaude/autoclaude/infra/adapters/sdk_executor_adapter.py:59-70`，僅 allowlist 內工具放行、predicate 例外時 fail-closed deny）；**寫入範圍限制**由 CLI 原生 `isolation:"worktree"` 承接（➖ 性質，同 §1.5，非本 repo 自建）。**未見**：專屬的「未經確認網路存取」攔截層（僅隨工具白名單間接生效，若 WebFetch/WebSearch 不在 allowlist 內才會被擋，非獨立控制）；Agent 狀態回報的驗證是一般型別化 dataclass（如 `AutoClaude/autoclaude/models/step_mutation.py`／`models/decision.py`），屬正常軟體工程實務，並非針對「防止 Agent 自然語言偽造狀態」設計的資安控制 |
| 13 | CLI 版本升級破壞相容性（啟動時記錄版本並比對已驗證清單；未知版本→`DRY_RUN`+人工確認） | ❌ | 本輪查證：全 repo 對「CLI 版本比對」／版本白名單機制零命中 |
| 14 | 磁碟空間不足（啟動與凍結前檢查可用空間；不足則清理已合併 worktree 並告警） | ❌ | 本輪查證：全 repo 對 `shutil.disk_usage`／磁碟空間檢查零命中 |

**本節小結**：14 項中 ✅ 1 項、⚠️ 6 項、➖ 1 項、❌ 6 項。真空最明確的三項（429 full-jitter 退避、git lock 陳舊性+PID 存活檢查、`DIRTY_UNSAVED`/`NEEDS_HUMAN` 狀態標記）與 SA 抽查結果一致，本輪對其餘 11 項做了獨立現查，未照抄未驗證的結論。

### 1.16 §13 合規聲明核對

PRD §13 本質是「明確禁止並不予實作」的清單 + 一項人工檢核提示，性質與前面「PRD 概念是否已實作」的表不同——這裡的✅代表「確實沒有違反禁令」。

| PRD 條款 | 狀態 | 證據 |
|---|---|---|
| 禁止多帳號輪替、帳號池化、憑證共享以規避單帳號限制 | ✅ | 本輪查證全 `tools/lib/*.py` 對帳號輪替/池化/憑證共享相關字面零命中；且 §4.7 的仲裁設計本身刻意「一個帳號、一份帳」（`quota_gate.py:168-173`，不帶 session id），與池化方向相反，屬設計上主動排除 |
| 禁止任何形式的限流／計費繞過、請求偽裝 | ✅ | T5 端點呼叫（`quota_meter.py`）走正規唯讀 GET + 本機 OAuth token（`Authorization` 標頭），無偽裝 User-Agent／無繞過計費的程式碼路徑 |
| 對未公開介面的高頻探測限制（選用的 T5 來源須遵守輪詢間隔且失敗即降級） | ✅ | 已於 §1.2（§4.1.1）記載：TTL≥180s 節流（`quota_gate.py:141`）＋失效降級 cap，本節不重複列證據 |
| `[需核對]`：實作前應確認使用條款對「自動化使用」「未公開端點存取」的規定，以及訂閱制方案是否允許長時間無人看管自動化運行 | ❌／人工待辦 | 本輪查證：repo 內未見任何文件記載此項使用條款核對已經完成（非程式碼可回答的問題）。PRD 原文自己標注這是「上線前的必要檢核項，非技術問題」——現況是這件事尚未被記載為已完成，屬於懸而未決的人工/法務事項，不是可以用程式碼補的缺口 |

**本節小結**：3 項禁令 3 項皆✅（未違反），1 項人工檢核事項尚無完成記載。

---

## 2. 測試覆蓋現況（本輪實跑，非引用舊結果）

PowerShell 工具實跑，全部使用 `.venv\Scripts\python.exe`：

| 測試檔 | 對應 PRD 章節 | 本輪實測結果 |
|---|---|---|
| `tools/tests/test_context_budget_guard.py` | §4.3／§4.5.6／§4.5.7／§4.5.8／§9 一部分 | **447 passed, 167 subtests passed**（79.95s） |
| `tools/tests/test_quota_policy.py` | §4.1／§4.2／§4.2.8／§0.6 新發現 1/2 | 與另兩檔合跑：**408 passed, 394 subtests passed**（26.98s） |
| `tools/tests/test_defect_id_reference_integrity.py`／`test_check_defect_log_crossref.py` | 帳本治理（非 PRD 本體，交叉驗證用） | 同上批次一起綠 |
| `AutoClaude/tests/plugins/test_token_guard_plugin.py`／`test_sdd_governance.py` | §4.2.3 致動器／SDD 橋接 SCG 閘門 | **62 passed**（1.71s） |

覆蓋缺口（沒有測試、需要點名）：
- §4.2.4 平穩性機制：無測試，因為無實作（見 §1.3）。
- §4.5.1 凍結流程的「5 秒內」時間驗收：無專屬計時測試。
- §9 Prometheus/OTLP 指標格式：無測試，因為無實作。
- §11.2「DRY_RUN 一週」／§11.8「24h 端到端」：結構上無法用單元測試表達，需要專屬長跑載具，目前沒有。
- §7 state.json v2 schema（agents 陣列/checksum）：無測試，因為現行兩套持久化（PlaybookCheckpoint／RELAY 任務書）走的是不同 schema，PRD 描述的那個 schema 本身未被實作。

---

## 3. Plugin 架構有效性評估（回應「每輪都在做帳本/文件瘦身，很浪費」）

### 3.1 架構現狀（實測，非猜測）

`AutoClaude/autoclaude/core/wiring.py` 的 `_REGISTER_ORDER` 現況共 **19** 個具名註冊項（`hotkey` 為條件式第 20 項），每個都是真實運作的 Plugin（`build_kernel()`/`wire_plugins_with_registry()` 兩條組裝路徑共用同一份 SSOT，避免漂移）。`token_guard_plugin.py`／`checkpoint_plugin.py` 兩支表面上只有 13~14 行，但那是**刻意的 backward-compat shim**（真正實作已拆到 `autoclaude/plugins/token_guard/`（5 子模組）與 `autoclaude/plugins/checkpoint/`（7 子模組）），不是死碼或半成品——保留薄殼是為了不動既有 30+ 支測試的 patch path。**結論：Plugin 架構不是掛名的裝飾，是本輪實測仍在生效、仍持續被使用（AutoSDD_improving_9x 系列每一輪都在新增/調整這裡的 Plugin）的活架構。**

### 3.2 它有沒有能力把「帳本/文件瘦身」封裝成一個 Plugin？

**結論：架構上「可以」，但這是問錯問題——不是「Plugin 架構擋住了」，而是「這件事的正確落點本來就不是 Plugin」。**

三個獨立理由，各自成立：

1. **Plugin 的生命週期綁在單一 playbook 執行**（`KernelPhase.PRE_RUN`→…→`POST_RUN`），而「帳本瘦身」是**跨輪次、跨 session 的治理行事曆事件**（每輪迭代結束時做一次，不是每次 AI 任務執行時做一次）。要用 Plugin 做，得先有一個專屬的「housekeeping.yaml」playbook，每輪手動 `python -m autoclaude housekeeping.yaml` 觸發——這其實只是把「手動執行 archive_defect_log.py」換一層包裝，並沒有解決「要有人記得觸發」這個真正的問題。
2. **這件事本身已經是一個確定性工具，不需要 AI 判斷**（Rule 5：模型只做判斷類工作，不做確定性轉換）。`tools/archive_defect_log.py` **已經存在且相當成熟**：有 `--check`（唯讀健檢，已掛進 `tools/git-hooks/pre-push` 的守門迴圈）與 `--apply`（真的執行搬遷，含五項判準：狀態關鍵字比對／散文掃描「向未來輪次交棒」字樣／自動在索引文件登記 bullet 等，`archive_defect_log.py:33-110`）。它本身就是一支可重複執行、有測試（`test_archive_defect_log.py`）的 CLI 工具。**真正缺的不是「把它包成 Plugin」，是「沒有人/沒有排程自動呼叫 `--apply`」**——目前只有 `--check` 被排進 pre-push（唯讀警示），`--apply` 仍要人手動跑。
3. **真正的自動化落點是既有的排程/巡邏基礎設施，不是 Plugin 系統**。本 repo 已經有一套成熟的「巡邏 tick」機制（`quota_escalation.patrol_housekeeping()`／哨兵排程），專門用來做「每隔一段時間檢查一件事、量不到就不動作」這類治理行事曆工作——這正是帳本瘦身要的形狀（定期檢查「帳本是否接近歸檔上限」，若是則自動 `--apply`），而不是「掛在某次 AI 任務的某個 phase 上」。

### 3.3 具體設計建議（不實作，只給規模估計）

若要真的自動化，按落點分兩個選項（不是二選一，可以疊加）：

- **選項 A（最小改動，建議優先）**：在既有 `tools/local_ci_gate.ps1`／nightly 腳本（`tools/run_local_nightly.ps1`）新增一步：`archive_defect_log.py --check`失敗（代表帳本已越過警戒線）時自動接著跑 `--apply`（而非只警示）。估計規模：**改動 ≤30 行**（nightly 腳本一個新 stage + 呼叫既有 CLI），零新架構元件。同類可疊加的還有 `framework_status_snapshot.py --write`（AISDLC_SDD 版本快照）、`sync_onboarding_baselines.py --write`（ONBOARDING 基線）——這些全部已經是「有 `--check`／`--write` 兩態的確定性工具」，只差「自動接手 apply」這一步。
- **選項 B（若要走 AutoClaude 引擎）**：寫一支極薄的 `HousekeepingPlugin`（訂閱 `POST_RUN`，只在 `cfg.playbook.workflow_type == "governance_housekeeping"` 時啟用），呼叫上述 CLI 工具的 Python 函式（不重寫邏輯）。估計規模：**≤60 行**（比照 `evolution_plugin.py` 的薄殼模式），但仍需要「每輪手動觸發這個 playbook」，並沒有解決自動化本身，純粹是「讓這個動作也能被記進 playbook 執行歷史」這個次要價值——**優先度低於選項 A**。

### 3.4 是否有結構性缺陷擋住這件事？

**沒有**。Plugin 架構（19 個 Plugin、EventBus、`_REGISTER_ORDER`）本身健康、有測試、持續被使用；LOC 分級治理（`AutoClaude/tools/check_loc_budget.py`）也沒有卡住任何相關檔案的擴充空間（`archive_defect_log.py` 不在 AutoClaude LOC 分級管轄內，是根層 `tools/` 的獨立治理面）。唯一的「架構」問題是：**帳本瘦身這件事的性質（跨輪治理行事曆、確定性轉換）從一開始就不屬於 Plugin 系統要解決的問題域**（Plugin 系統解決的是「單次 AI 任務執行期間的橫切關注點」）。把它硬塞進 Plugin 只會多一層不必要的間接，正解是排程/CI 補一步呼叫既有工具。

---

## 4. AISDLC_SDD 啟動驗證

### 4.1 橋接機制盤點（兩條獨立路徑，職責不同）

1. **`SDD_ACTIVE_VERSION` + `sdd_hook_router.py`**：用於「直接在 Claude Code CLI 互動 session 中對 AISDLC_SDD 框架本身做開發（B 軌 dogfooding）」，把根層 session 的 hook 事件（SessionStart/PreToolUse/PostToolUse）轉發到 `AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/` 的實體 hook，讓 FSM 治理／context-ledger 生效。這不是「AutoClaude 驅動 SDD」，是「在 SDD 自己的地盤上工作時讓 SDD 自己的守門生效」。已讀完全文（225 行），本輪未變更、確認 no-op 守衛（`SDD_ACTIVE_VERSION` 未設即休眠）與路徑逃逸防護（`DEF-CLDREV-028` 修復）邏輯完好。
2. **`SddGovernancePlugin` + `SddToPlaybookAdapter`**（`AutoClaude/autoclaude/plugins/sdd_governance_plugin.py` + `AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py`）：這才是「AutoClaude 引擎自動驅動 SDD 流程做需求開發」的真正實作——一個 `workflow_type: aisdlc_sdd` 的 playbook 若指定 `workflow_path` 指向一個含真實 `TEST-CONTRACT-SPEC-*.md`＋`build/reports/fsm/FSM-STATE-*.yaml`（AISDLC_SDD FSM runtime 的真實輸出格式）的目錄，Plugin 會在 `PRE_RUN` 讀取規格、依 AC/AT Gherkin 契約編譯出 `PlaybookTask`，並在整個執行期間用 `SCG-0~6` 閘門序守門（越級存取即 Veto）。

### 4.2 實測結果：**能，但只驗證到「compile 通過」，SCG 閘門本身從未在真跑中被啟用過**

- **零 token 驗證（本輪實跑）**：`python AutoClaude/tools/run_bridge_e2e.py --source scripts/bridge_e2e/strutils_prd_plan.yaml --compile-only` → **成功**編譯出完整 playbook YAML（5 個 step，`workflow_type=aisdlc_sdd`），證明橋接編譯鏈路在**今天的程式碼**上仍然活著。
- **既有真跑證據（非本輪產生，讀取既有檔案核實）**：`AutoClaude/docs/03_testing/AutoSDD_improving_96_bridge_e2e_pty_evidence.json` 記載一次**真花 Claude token** 的端到端執行——`python -m autoclaude` 真跑一個標了 `workflow_type=aisdlc_sdd` 的 playbook（strutils 字串工具庫，SPEC→TDD 紅→實作至綠），結果 `5/5 步成功、pass_rate=1.0、kernel_success=true、escalated=false`。**這證明 AutoClaude 能自動驅動一個規格先行/TDD 的開發流程並跑到成功**。
- **關鍵落差（本輪讀原始碼發現）**：這次真跑用的來源是 `three_tier_to_playbook.compile_to_playbook()`（Archy 產生的 PRD 三層計畫），**不是** `SddToPlaybookAdapter.load_spec()` 讀真實 AISDLC_SDD 規格檔。`SddGovernancePlugin._on_pre_run()` 在 `workflow_path` 為空／找不到 spec_dir 時會**降級為記帳-only、不阻斷**（`sdd_governance_plugin.py:162-168`）——也就是說，那次真跑雖然標籤是 `aisdlc_sdd`，**SCG 閘門實際上很可能是在降級模式下運作，並未真的執行「越閘擋下」的守門邏輯**。
- **格式相容性已核實（本輪新查，非既有文件）**：`SddToPlaybookAdapter._read_contract_spec()` 找的檔名規則（含「CONTRACT」＋「SPEC」或 `TCS-` 開頭）與 AISDLC_SDD_v0.30 官方模板 `docs_template/sdd/testing/TEST-CONTRACT-SPEC-TEMPLATE.md` 相容；`_assert_frozen()` 找的路徑 `build/reports/fsm/FSM-STATE-*.yaml` 與 AISDLC_SDD 真實 FSM runtime（`tools/fsm_runtime/state_loader.py:78`：`DEFAULT_STATE_DIR/FSM-STATE-{project}.yaml`）逐格對齊。**格式面沒有相容性問題**。
- **測試覆蓋現況**：`AutoClaude/tests/plugins/test_sdd_governance.py` 的 20 支測試全部用 `tmp_path` 合成假的 TEST-CONTRACT-SPEC/FSM-STATE 內容（本輪 Grep 全庫確認零命中任何指向真實 `AISDLC_SDD_v0.3x` 樹的 `workflow_path`/`spec_dir`），**沒有一次是拿真實 AISDLC_SDD 框架產出的規格檔跑過**。

### 4.3 結論

**能**：AutoClaude 引擎技術上可以驅動規格先行/TDD 式的需求開發（已有真花 token 的成功案例，5/5）。**但**「用 AutoClaude 引擎驅動、且真的被 AISDLC_SDD 自己的 SCG 閘門/FSM 凍結狀態守門」這個更嚴格的閉環，**從未在真實 token 消耗的跑動中被驗證過**——只有格式相容性核實（本輪新做）與合成 fixture 單元測試（既有 20 支全綠）。這是一個**驗證缺口**，不是相容性缺陷（兩個框架的檔案格式是對得上的）。

### 4.4 反向檢查：AISDLC_SDD 框架本身是否有不利於 AutoClaude 整合的摩擦點

實查發現一個具體、此前未被記錄的潛在缺陷（已列入帳本 `DEF-200-176`，見下）：`SddToPlaybookAdapter._read_contract_spec()` 用 `sorted(candidates)[0]`（字母序取第一個）在 `spec_dir` 內挑規格檔，而 AISDLC_SDD_v0.30 官方模板同時提供 `TEST-CONTRACT-SPEC-TEMPLATE.md`、`CONTRACT-TEST-SPEC-INTEGRATION-TEMPLATE.md`、`CONTRACT-TEST-SPEC-MIGRATION-TEMPLATE.md`、`ENV-CONTRACT-SPEC-TEMPLATE.md` 四種都同時含「CONTRACT」與「SPEC」的檔名。若一個真實專案的 spec 目錄裡同時存在多種（例如同時有行為契約與整合測試契約），字母序會讓 `CONTRACT-TEST-SPEC-INTEGRATION-*`（C 開頭）排到 `TEST-CONTRACT-SPEC-*`（T 開頭）前面，adapter 可能靜默讀到錯誤的規格檔——SCG 閘門仍會「通過」（因為它讀到了「一份」規格），但契約內容與真正要守的行為契約無關。這是本輪新發現，尚未修復。

---

## 5. 跨平台（Mac/Windows）架構合理性複核

### 5.1 現有雙軌設計盤點

| 關注點 | Windows | macOS | 共用/各自的理由 |
|---|---|---|---|
| 排程載具 | `SchtasksBackend`（`schedule_backend.py:275`） | `LaunchdBackend`（`schedule_backend.py:364`） | **合理不可合併**：兩個 OS 的排程 API 語意本質不同（schtasks 用 `NextRunTime` 當憑證；launchd 從不回報下次執行時間，只能用 `launchctl print` 的 rc 當憑證）。已有 `NoCarrierBackend`（`schedule_backend.py:762`）處理兩者皆無的情境，`select()`（`schedule_backend.py:803`）是唯一分派點 |
| 憑證判準 | `next_run_time()` 讀 `NextRunTime` 字串 | `armed_but_missing()` 讀 rc | 同上，兩把尺**故意不共用同一個值**（CLAUDE.md 明文「Windows 用 `Get-ScheduledTask`；macOS 用 `launchctl list`，憑證是 rc 不是時間值」）——這不是重複邏輯，是同一個抽象概念（「排程是否還在」）在兩個 OS 上唯一可行的兩種量測方式，**合併會需要其中一個平台假造一個它結構上量不到的欄位**，方向是錯的 |
| 防休眠 | 未實作 keep-awake API | 未實作 keep-awake API，只做「失效可偵測」（`pmset -g custom` 現查） | 見 §1.7：**這其實是唯一可以合併、且已經合併的部分**——兩個平台共用同一套策略（不做 keep-awake，改用排程喚醒），差別只在「怎麼問這台機器睡眠設定」，不是兩套獨立邏輯 |
| 憑證讀取（OAuth token） | `CREDENTIALS` 檔案路徑 | `_keychain_token()` 走 macOS Keychain | **合理不可合併**：Windows/Linux/WSL 憑證是明碼 JSON 檔案，macOS 是系統 Keychain——`_fetch_token(plat, runner)` 已收斂成**單一平台分支的家**（`quota_meter.py:263`，R83/F2-③ 訂正過此前「兩個函式各判一次平台」的漂移風險），不是重複邏輯 |
| Console 視窗抑制 | `NO_WINDOW`（`CREATE_NO_WINDOW\|CREATE_NEW_PROCESS_GROUP`） | 不需要（POSIX 無此概念，`getattr(...,0)` 取 0） | **本來就是單一平台專屬 API，沒有合併空間**；但實作方式有一個**已知的、repo 自己記載的重複**：同一個 `NO_WINDOW` 常數字面在 `quota_meter.py:112` 與 `.claude/hooks/context_budget_guard.py` 各有一份（因為反向 import 會成環），有相等鎖 `test_the_duplicated_no_window_expression_still_equals_the_ssot` 守著兩份不漂開——**這是刻意的、有測試保護的重複，不是可以簡化的重複** |

### 5.2 找到的具體可簡化點

1. **`quota_gate.py`／`quota_policy.py`／`session_resume_planner.py` 三支同時卡在 LOC 天花板（本輪實測 500/500、400/400、750/750，皆為零餘裕）**。這不是「跨平台」問題但直接影響下一波任何 PRD 缺口的修補能力——**任何**要對 §4.1~§4.7 做增補的任務，第一步都得先在同一個 tier 內找到等量可刪的東西（鐵律七同型的資源競用）。這是本輪最具體、影響面最廣的一個結構限制，建議列為下一波任務清單的前置項。
2. **PRD §4.6 防休眠的「未實作」與跨平台無關**——兩個平台都沒做（不是「Windows 做了 Mac 沒做」的不對稱），且不做是有意的架構選擇（統一走排程喚醒）。沒有「為了相容性而過度複雜」的現象——反而是「為了避開三份平台專屬 API 的維護面，選擇只維護一套排程喚醒邏輯」，是**簡化**而非過度複雜。
3. **沒有發現「Windows-only 或 Mac-only 但明明可以共用」的邏輯**。逐一檢視後，雙軌的每一處分支都對應到真實的 OS API 語意差異（憑證存放位置、排程器回報格式、console 視窗行為），沒有找到可以安全合併卻被迫寫成兩份的案例。這與 CLAUDE.md〈鐵律三〉逐一條列的「觸發清單」精神一致——本 repo 在 quota 治理這條軸線上似乎確實做到了「每個平台分支都問過『這在另一個平台是什麼值』」。

### 5.3 誠實劃界

本次複核**只讀程式碼與既有量測記錄，未在真實 macOS 機器上重跑**（本 session 為 Windows）。CLAUDE.md 記載的 mac 側已知限制（睡眠喚醒需 sudo、真機覆蓋仍為 0）本輪未變更也未重新驗證，原樣引用既有記載。

---

## 結論摘要（給決策者）

### 逐模組一行結論

- ✅ §4.1.1 T5 遙測（唯一認可主源，四豁免條件皆滿足）
- ✅ §4.1.3/§4.1.4 視窗重置偵測／帳號方案變更指紋（比 PRD 描述更精細，已修過兩輪真實假陽性）
- ⚠️ §3 狀態機（無持久 FSM，改用無狀態 band 決策函式；語意大致對應但無獨立 BURSTING 狀態）
- ❌ §4.2.4 平穩性機制（遲滯/死區/slew/dwell 全無，因架構是無狀態純函式而非持續控制迴圈）
- ✅ §4.2.8 pace_index（PRD 建議的簡化路線，已落地且對齊官方配速門檻）
- ✅ §4.3 壓縮治理三 AND 條件（R91 補齊後完整）
- ➖ §4.4 worktree 隔離（CLI 原生已涵蓋，本 repo 確實在用原生）
- ✅ §4.5.5~4.5.8 喚醒閉環全鏈（本 PRD 落地最深的一章，四輪缺陷迭代修到位）
- ❌ §4.6 三平台防休眠 API（架構性替代：統一走 OS 排程喚醒，非缺漏）
- ⚠️ §4.7 帳號配額仲裁（功能等價的目錄項派發帳，非 PRD 描述的 lease 檔結構）
- ❌ §5 API Key 模式（全未實作，本 repo 純 OAuth）
- ⚠️ §7 state.json v2（兩套各自為政的持久化，皆非多 Agent 陣列 schema）
- ❌ §9 Prometheus/OTLP 指標（自建 JSONL 痕跡等價存在，官方格式未接）
- ✅ §12 安全性核心三條（憑證唯讀不落痕跡／不用 skip-permissions／治理檔禁寫）
- ❌ §8 三大真空（本輪新查，見 §1.15）：429 full-jitter 退避、git index.lock 陳舊性+PID 存活檢查、`DIRTY_UNSAVED`/`NEEDS_HUMAN` 狀態標記——三者全 repo 零命中，是 §8 十四項中證據最明確的缺口
- ✅ §13 合規聲明（見 §1.16）：三項禁令（帳號輪替/池化/憑證共享、限流繞過、未公開介面高頻探測）皆未違反；唯一未落地的是 `[需核對]` 使用條款人工檢核，性質是法務/商業待辦而非程式碼缺口

### AISDLC_SDD 啟動驗證結果

**能**驅動規格先行/TDD 開發流程（有真花 token 的 5/5 成功案例），**但** SCG 閘門本身在真跑中很可能只是降級記帳模式（spec_dir 未真的指向 AISDLC_SDD 框架輸出）——格式相容性已核實對得上，只是這條「真的被 SDD 閘門守門」的路徑從未真的被跑過。發現一個新的潛在缺陷（規格檔選擇的字母序歧義），已列 `DEF-200-176`。

### Plugin 架構結論

架構本身健康、活著、有測試（19 Plugin，非裝飾）。它**不是**帳本/文件瘦身的正確落點——那是跨輪治理行事曆事件，不是單次 playbook 執行的橫切關注點，且瘦身本身已是確定性工具（`archive_defect_log.py --apply`），只缺「自動呼叫」這一步。建議走排程/CI 補一步（選項 A，≤30 行），而非新建 Plugin。

### 下一波建議任務清單（按優先序）

1. **【P0，前置】** 為 `tools/lib/quota_gate.py`／`quota_policy.py`／`tools/session_resume_planner.py` 三支零餘裕檔案規劃一次瘦身或分拆，否則後續任何 §4.1~§4.7 增補都會立刻卡在 LOC 天花板（鐵律七同型）。
2. **【P1，新增】** 補 §8 三大真空（見 §1.15，證據最明確的缺口）：
   - 429 退避改 full-jitter（`sleep=rand(0,min(300,10·2^n))`）並把 429 視為遙測低估證據上修 `U5h`——目前重試（`session_resume_planner.py` 的 `tick_plan()`）走固定 300s、無 jitter，多 Agent 同時撞牆有雷群風險。
   - Git `index.lock` 陳舊性判準（mtime + 持有 PID 存活檢查後才清理）——目前無此程式碼，`block_destructive_git.py` 的既有鎖檔處理不含這條。
   - `DIRTY_UNSAVED`／`NEEDS_HUMAN` 狀態標記寫回可重啟點任務書——目前 worktree 保全失敗、Agent 卡死升級皆無專屬標記可供下游（喚醒邏輯/人工）辨識這兩種情境，僅有功能相近但未明確標記的機制（ESCALATION/EscalationDump）。
3. **【P1】** 修復 `DEF-200-176`：`SddToPlaybookAdapter._read_contract_spec()` 的規格檔選擇歧義（多份含「CONTRACT+SPEC」檔名時的字母序陷阱）。
4. **【P1】** 找一個真實（或最小可行的）AISDLC_SDD 專案，實跑一次 `spec_dir` 指向真實 `TEST-CONTRACT-SPEC-*.md`＋`FSM-STATE-*.yaml` 的端到端 AutoClaude playbook，驗證 SCG 閘門真的會在越級存取時 Veto（目前只有合成 fixture 單元測試）。
5. **【P2】** 選項 A：把 `archive_defect_log.py --apply`（以及 `framework_status_snapshot.py --write`／`sync_onboarding_baselines.py --write`）接進 nightly/local_ci_gate 的自動流程，而非每輪手動觸發。
6. **【P2】** §4.2.4 平穩性機制：評估是否真的需要補（目前無狀態設計下風險本身就低），若需要，優先做「band 邊界的簡單遲滯」而非整套 EWMA/slew-rate（PRD 自己都建議這條路可以整套跳過）。
7. **【P2，新增】** §8 item 4 補 checksum 與版本保留：`FileStateRepository` 目前一個 playbook 只留一份 checkpoint、載入失敗即視同從頭開始；若要對齊 PRD「checksum 失敗回退到最近有效版本」，需要至少保留 1~2 份歷史版本並加 checksum 欄位——目前原子寫入已到位，缺的只是「留一手」。
8. **【P3】** §9 可觀測性：評估是否要接 `CLAUDE_CODE_ENABLE_TELEMETRY`/Prometheus exporter，或維持現行自建 JSONL 痕跡家族（需要先確認有沒有下游消費者要接 Grafana 等外部工具，沒有的話現狀已經夠用）。
9. **【P3】** §5 API Key 模式：若無 API Key 自動化計畫可直接不做；若有，需要從零設計正規化層。
10. **【P3，新增】** §8 items 11~14（整合驗證失敗佇列、CLI 版本相容性檢查、磁碟空間檢查）：三者皆全 repo 零命中，但對應的風險場景（多 worktree 並行整合、CLI 升級破壞旗標相容性、磁碟塞爆）目前發生機率相對低（本 repo 非多 worktree 並行架構、CLI 版本由使用者手動升級可先人工留意），可視資源排在 §9/§5 之後。
11. **【P4】** §7 state.json v2 多 Agent 陣列 schema：只有在 Console UI（多服務並行）規劃真的動工、需要多 worktree 並行狀態追蹤時才有必要，目前優先度低。
12. **【P4，新增】** §13 `[需核對]` 使用條款人工檢核：請掌舵者或有權限的人確認 Claude Code 訂閱制方案的使用條款是否允許本專案這種長時間無人看管自動化（含存取未公開端點）——這不是程式碼任務，但目前沒有任何記載顯示已經做過，應在下一次上線前補齊此人工確認並記錄結論。
