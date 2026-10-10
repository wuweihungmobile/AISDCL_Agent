# AutoSDD_improving_113（R211）— PRD v2.1 剩餘收斂輪：模型角色參數化（W1）＋ §2.2 重盤選定的 W2／W3

> **軌道①**（AISDLC-SDD × AutoClaude 深度整合；驅動器＝`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`）。
> 本輪三柱分佈：**C 柱（指揮官 AutoClaude 的核心排程與 Token 治理系統本體，PRD v2.1）** 為主；
> **A 柱** 無；**B 柱** 僅維持 dogfooding 最小面（既有 FSM 狀態 SPEC_DRAFTING 不另設 SDD_PROJECT——session 已啟動、env 不可變；缺陷「發現即記」紀律照走）。
> 下一份檔名＝AutoSDD_improving_114.md（尚未建立；動工前仍以 `ls` 實查 docs/04_planning 最大號＋1）。
> **雙編號說明**：軌道① 編號 113；帳本時鐘（`tools/check_defect_log_crossref.py` 的 current_round 讀
> `docs/06_quality/CrossPlatform_R<N>_*.md` ∪ `docs/04_planning/R<N>_HANDOFF.md` 檔名最大號）本輪由 210 推進到 **211**
> ——本輪審計證據檔命名為 docs/06_quality/CrossPlatform_R211_ZeroTrust_Audit_113.md（即範本「四件套」第 2 件，冠 R 前綴是為了讓
> 護欄棘輪重釘列、接鏈列與帳本時鐘同一個輪號；同 commit 補 ADR-XPLAT-002 §6 一列與 governance_docs 登記）。
>
> **掌舵者 2026-10-09 開場指令（原文逐字）**：「依 docs/04_planning/AutoSDD_Iteration_Prompt_Template.md 開軌道①新一輪
> （動工前 ls 實查 docs/04_planning/ 最大號＋1），主題＝Token 監控 PRD 剩餘 25～30%；子代理一律 Sonnet，主控 Fable。
> ==> 我加上進階，讓主控與子代理，可以依照本系統參數檔依照參數進行設定不同模型版本」。
> ⇒ **W1 由掌舵者直接立案**：主控／子代理模型版本改由本系統參數檔（repo 根 `.env`；唯一規格表＝`ENV_SPEC`，
> 生成物 `.env.example`）設定。本檔＝SCG-0/1 載體（規格先行：§1～§3 先落地才進階段三；§4～§6 只准階段三／四回填）。
> 人員：主控 Fable 5.1 兼 Architect；盤點／實作／審查 agent 一律 Sonnet（`model: sonnet`）。

## §1 本輪輸入（自上輪繼承）

| 來源 | 條目 | 本輪處置 |
|---|---|---|
| `docs/04_planning/AutoSDD_improving_112.md` §4-1 | 水位預警哨兵擴充＋PRD v2.1.6 落款 | ✅ 已落地：`tools/lib/quota_escalation.py` B1～B3 與 `tools/tests/test_context_budget_guard.py` 的鎖；帳本 DEF-200-148 fixed（`docs/06_quality/AutoSDD_Defect_Log_archive_67.md`）；程序債＝PRD 修訂表 L11（v2.1.6）字面仍寫「待實作」（登記證據檔〈三〉） |
| 同 §4-2 | Windows 側待驗清單 | 承接載體＝`docs/06_quality/CrossPlatform_R210_Debt_Closure_Final_Evidence.md`〈八〉（只能在 Windows 機驗；本輪 mac，不排） |
| 同 §4-3 | 引擎側額度軸接電（第三方刷新者） | ❌ 未做且全 docs 零追蹤列（`AutoClaude/autoclaude/core/ports/quota_meter.py:15-45` 自陳缺刷新者、`AutoClaude/tests/test_r82_quota_axis_and_shipped_defaults.py:797` 釘住「引擎側零寫入者」）；本輪登記證據檔〈三〉、列入 improving_114 候選（W-C′(i)） |
| 同 §4-4 | SD/Arch 順手項（prepare 閂鎖鍵、混軸鍵補記來源軸） | ❓ 本輪未逐項重驗（誠實標記） |
| 同 §5 | 「PRD 收斂度 65%→估 72~75%，精確值下輪開場重盤」 | 本輪 §2.2 重盤（兩種算法各給一個數字） |
| 缺陷帳本 | `python tools/check_defect_log_crossref.py --unresolved-count` 逐字：「未結列數＝0／全部 207 列｜warn=86 fail=98」；外部阻塞軌 5 筆、結構性長債軌 6 筆 | 無 open/routed 待處置；本輪新列依 🐶 紀律入帳（W1 立案列見 §7） |
| 上輪 QA 延後條目 | 無（improving_112 §2 四方閉環已收） | — |

## §2 階段一：現況重偵察（Zero-Trust Re-Audit；全部本輪實測，2026-10-09，macOS，開發 venv `.venv`）

### 2.1 零退化基線

| 檢查 | 指令 | 本輪實測（逐字） | 對照 |
|---|---|---|---|
| AutoClaude 全套 | `python -m pytest tests/ -q`（AutoClaude/ 下） | `4864 passed, 156 skipped in 36.69s`，rc=0 | 表② macOS 欄 4764 passed／222 skipped 為**乾淨 venv** 值；開發 venv 多裝相依故 skip 較少，兩者不可相減 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | `Contracts: 9 kept, 0 broken.` rc=0 | 契約條數 SSOT＝AutoClaude/.importlinter |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh`（AISDLC_SDD/ 下） | `✅ 本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.30）`；逐軌計數 AISDLC_SDD_v0.01:1475 AISDLC_SDD_v0.30:1979 scripts/tests:362，rc=0 | 與 R210 同值 |
| 根層 tools/tests | `python tools/run_root_unittests.py` | `✅ unittest 數量下限釘選通過：發現 5207 個測試（下限 5101）`；skip 47 支全數有標籤；真實 TEMP 圍籬零變動；rc=0 | 與 R210 同值 |
| 守門工具 | crossref／carriers／archive／sync-baselines | crossref rc=0（未結 0）；`python tools/check_handoff_carriers.py` rc=0；`python tools/archive_defect_log.py --check` rc=0；`python tools/sync_onboarding_baselines.py --check` 與 `--check-snapshot` rc=0 | 盤點 agent 實跑 |

硬閘判定：無 failed、passed 數不低於上輪 ⇒ 准入階段二。

### 2.2 PRD v2.1 覆蓋度重盤（盤點 agent 唯讀交件；408 個 path:line 經腳本驗證行號有效、語意抽樣 70 個）

| 算法 | 數字 | 說明 |
|---|---|---|
| (a) PRD 模組列加權（✅=1、⚠️=0.5、❌=0、➖ 不入分母） | **60.3%**（80 列：✅22／⚠️44／❌7／➖7；分母 73） | 含 §10／§11／§15.5 共 90 列＝58.6%；再含 7 份修憲施工圖＝59.9% |
| (a) 敏感度 | ⚠️ 權重 0.25→45.2%；0.72→**73.5%**（≈ improving_112 引用的 72~75%）；下限（➖ 全計 ❌）55.0% | 掌舵者口述「剩 25～30%」只在把 ⚠️ 算成約七成落地時成立；按「缺規範性機制即 ⚠️」逐列誠實計，約剩四成 |
| (b) R98「下一波建議任務清單」12 項 | 嚴格 **25%**（✅3：#3 DEF-200-176、#6 §4.2.4 平穩性、#7 §8-4 checksum）；部分計半分 33%（⚠️#1 LOC 瘦身三檔仍零餘裕、#10 §8 items 11~14） | ❌#2／#5／#8／#9／#11／#12；#4 未查證 |
| (c) §6 的 78 個 .env 鍵逐鍵 | 38.9%（✅14／⚠️21／❌28／➖15） | 鍵級低≠功能缺：PRD §6 以 Daemon 形態寫成，換形態後多數鍵無對映 |

剩餘缺口構成（缺口質量＝❌×1＋⚠️×0.5，合計 33.5／81 列）：安全小缺口 16%、多 Agent 整合 15%、遙測 13%、**引擎無人值守 12%**、驗收證據 10%、配速長尾 9%、**喚醒鏈細節 9%**、設定面 9%、可觀測性 6%。
真正直接提升「無人值守續航」的只有四處：R121 受控 commit／push（碼面碰守衛面，本輪只能出決策包，未排）、`resume_cost_pp` 喚醒成本無資料（→ **W2**）、
AutoClaude 引擎獨立跑時額度軸不存在（缺第三方刷新者；improving_112 §4-3 承接，全 docs 零追蹤列→ 本輪登記證據檔理論洞、列入 improving_114 候選）、引擎路徑單次長睡（→ **W3**）。
本輪新發現：R108 BURN-DOWN 為 Adopted 但零落地、R121 為 Proposed 零落地；`resume_cost_pp` 全庫零命中；本機 claude 2.1.295 不在 `VERIFIED_CLI_VERSIONS`（僅 2.1.223／2.1.233）⇒ AutoClaude 每次啟動 loud＋DRY_RUN（→ W3(iii)）。
修憲候選 12 筆＋程序債 1 筆（座標見審計證據檔）；`[需核對]` 11 處中 8 處答案已在附錄 B、3 件未解；「依設計未實作」2 處＝DEF-200-246。
improving_112 §4 四項承接：§4-1 ✅（DEF-200-148 fixed；PRD 修訂表 L11 字面仍寫「待實作」＝程序債）、§4-2 ➖ 本輪不排、§4-3 ❌ 未做且零追蹤列、§4-4 ❓ 未逐項重驗。

### 2.3 模型角色現況（W1 的零信任偵察；盤點 agent 實測，座標皆現查）
- 真正「替角色決定模型／寫死模型名」的站點只有 4 處：降級建議行字面 `sonnet/haiku`（tools/lib/quota_messages.py:814-819）；
  喚醒續跑 argv 不帶 `--model`（tools/lib/resume_route.py:146 與 :157；spawn 點 tools/session_resume_planner.py:1225，
  該行以 `{**os.environ, UNATTENDED_ENV: "1"}` 交環境）；額度付費探針寫死 `haiku`（tools/session_resume_planner.py:476／:502）；
  子代理模型今天**零機械物**——只靠記憶檔紀律「派工帶 model=sonnet」。
- 全 repo 沒有任何程式讀 `CLAUDE_CODE_SUBAGENT_MODEL`（PRD 附錄 B-11 只有兩行文字）；repo `.claude/settings.json` 無 `model` 鍵；
  互動主視窗模型來自使用者層 settings（本機實值 `claude-fable-5-1[1m]`）⇒ `.env` 管不到互動主視窗自己的模型。
- `ENV_SPEC`（28 列）的 `kind` 只有 float／int／flag；`attr=None` 的 8 列不經 `load_policy`，各消費者自讀自驗；
  `.env` 進 hook／planner 行程的唯一通道＝`quota_gate.apply_env_defaults`（只填 ENV_SPEC 宣告的鍵）。
- Claude Code 官方（code.claude.com/docs，本機 2.1.295）：子代理模型序位＝呼叫時 `model` 參數 ＞ 子代理定義 frontmatter ＞
  `CLAUDE_CODE_SUBAGENT_MODEL` ＞ 主對話模型；`CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` 時 Claude 無法再傳 model。
  主 session：`/model` ＞ `--model` ＞ `ANTHROPIC_MODEL` ＞ settings `model` ＞ `ANTHROPIC_DEFAULT_MODEL`；續跑時 `--model` 優先於轉錄還原的模型。
  `fable` 為官方別名。Agent 工具 `model` 參數 schema＝enum 四別名，恰等於 `MODEL_FAMILIES`。
- LOC 餘裕（`python AutoClaude/tools/check_loc_budget.py --json`）：hook `.claude/hooks/context_budget_guard.py` SPECIAL 1089/1089（**零餘裕**）；
  planner 746/750；quota_gate 495/500；quota_messages 369/400；session_brief 317/400；quota_policy_env 178/400；resume_route 81/400。
  tools/tests E501 存量債 139＝上限（新增測試行寬須 ≤100 欄、CJK 算 2 欄）。

### 2.4 三軸成熟度（L0–10 rubric）
本輪未重新量測 A／B／C 三軸級別；沿用既有基線宣稱並誠實標記「未量測」。

## §3 階段二：本輪增量設計

### 3.1 W1 模型角色參數化（掌舵者立案；PRD §4.2.3 第 7 步「模型降級致動器」與附錄 B-11 的落地）

**問題陳述**：§2.3 的四處寫死＋零機械物，使「主控用哪個模型、子代理用哪個模型」只活在人的記憶與指令字面裡；
喚醒窗口的主控模型由存檔／設定鏈決定，repo 參數無從指定；降級建議是常數字串。

<Architecture_Design_Review>
1. 架構純潔性：新增**純函式模組** tools/lib/model_roles.py（零 I/O、py39 相容、bare import、`from __future__ import annotations`）；
   不造 God-object；`ENV_SPEC` 仍是唯一規格表（+3 列 `attr=None`、`kind="model"`）；**不動** `load_policy`／`Policy`／`DEFAULT_POLICY`
   ——字串型角色鍵若走整組退回語意，一個拼錯的模型名會把整套額度門檻重設（耦合方向錯）。
2. 持久化相容：無 checkpoint 欄位；DAL 三後端零影響；AutoClaude 零改動（ACQ-02 autoclaude 不得 import harness；AutoClaude/.env.example
   不抄新鍵——該檔有「每鍵須有真讀者」鎖）。
3. 安全防護網：值域驗證＝`family_key()` 須命中四家族之一（別名或含家族字的完整 id：claude-sonnet-5-5、sonnet[1m] 皆可）＋字元白名單
   `^[A-Za-z0-9._\[\]-]+$`；壞值→退預設＋problems 出聲一次（沿用 planner `_transcript_cap`／relay_machine `_int_env` 紀律）；argv 為 list、不經 shell。
4. 對外 I/O：無新增 ToolInvocationPort 外呼。
</Architecture_Design_Review>

**介面 delta**（新檔／新函式於落地後才以反引號引用）：

| 鍵（ENV_SPEC +3 列） | 預設 | 語意與消費端 |
|---|---|---|
| AUTOSDD_MODEL_HELMSMAN | （空） | 無人值守喚醒（RESUME）與 FRESH 窗口的主控模型。**空＝不帶 `--model`**（沿用存檔／設定鏈＝現況行為；非空預設會讓沒有 Fable 存取的機器喚醒靜默失敗，故出廠留空、本機 `.env` 設 `fable`）。非空 ⇒ argv 追加 `["--model", v]`，位置在 `--settings <檔>` 之後、`--add-dir` 之前（9 支 argv 形狀鎖不紅） |
| AUTOSDD_MODEL_SUBAGENT | sonnet | 子代理預設模型。①喚醒窗口子行程環境注入 `CLAUDE_CODE_SUBAGENT_MODEL=v`（官方序位 4：只是預設，呼叫時明寫 model 仍優先；**刻意不設 `_FORCE`**，否則 Agent 工具失去 model 參數、守衛讀不到派工目標）；②`--pace` 與 SessionStart 簡報印出角色行，供互動窗主控派工時明寫 `model:` |
| AUTOSDD_MODEL_DOWNGRADE | haiku | 降級建議第二階（`model_hint_line` 字面改讀角色，預設輸出逐字仍為 `sonnet/haiku`）；額度付費探針模型（`probe_quota` 預設） |

- model_roles.py：ModelRoles(helmsman, subagent, downgrade)；load_model_roles(env) → (roles, problems)；child_env(roles) → dict；
  model_argv(roles) → list；roles_line(roles, problems) → 一行人話。
- tools/lib/resume_route.py：`_posture_argv()` 尾端 + model_argv；新 probe_argv(claude, model)（探針 argv 組裝自 planner 搬來，planner 淨 0 行）。
- tools/session_resume_planner.py：`probe_quota(model=None)` → `model or roles.downgrade`；`_run_resume` 的 env 於**同一物理行**併入 child_env；斷言行淨 ≤ +1（餘裕 4）。
- tools/lib/quota_messages.py：`model_hint_line(decision, roles=None)`；新渲染 model_roles_line。tools/lib/quota_gate.py：`pace_report` +1 行印角色（餘裕 5）。
  tools/lib/session_brief.py：`sessionstart_brief` +1～2 行印角色。.claude/hooks：**零改動**。
- `.env.example`：`python tools/lib/quota_policy.py --print-env-example > .env.example` 重生（72→78 行）。
- 讀者鎖：tools/tests/test_context_budget_guard.py 的 attr=None 讀者元組加 model_roles.py（1 行）。
- 新測試 tools/tests/test_model_roles.py：預設／別名／完整 id／壞值退預設且出聲／空 helmsman 不帶旗標／child_env／argv 位置與既有姊妹鎖同形／
  render→parse round-trip 含新鍵。每支先紅再綠（紅側以合成注入）。

**LOC 落點**：model_roles ≤120 斷言行（guardrail_lib 上限 400）；守衛面接線 planner ≤+1、quota_gate +1、quota_messages ≤+8、session_brief ≤+2；hook 0。
**契約影響**：`.importlinter` 無（根層 tools 不在 AutoClaude 契約內）；AutoClaude pytest 零改動。**checkpoint additive 欄位**：無。

**RTM**

| 需求 | 規格座標 | 實作落點 | 測試 |
|---|---|---|---|
| R1 主控模型可由參數檔設定並於喚醒續跑生效 | PRD §6 新區塊；附錄 B-11 | resume_route model_argv | test_model_roles＋既有 argv 形狀鎖 |
| R2 子代理模型可由參數檔設定並於喚醒窗口生效 | 同上 | child_env @ `_run_resume` | test_model_roles；planner env 超集既有測試 |
| R3 降級建議與付費探針讀參數 | PRD §4.2.3 第 7 步 | `model_hint_line`／probe_argv | 既有 3 支字面鎖＋新鎖 |
| R4 互動窗主控看得到角色值 | PRD §4.5.7 簡報 | model_roles_line @ `pace_report`／`sessionstart_brief` | session_brief 既有測試擴一支 |
| R5 壞值不靜默 | ENV_SPEC 紀律 | load_model_roles problems | test_model_roles |

**守衛面准入聲明**：本項為掌舵者 2026-10-09 直接立案（原文見檔頭），非審查構造性發現；暴露證據＝掌舵者真機指令（本 session sid da844569）。
守衛面只留接線行，邏輯住非守衛面 model_roles.py／quota_policy_env.py／resume_route.py；hook 零改動。

**PRD 修憲**：v2.1.16——§6 新區塊「模型角色（三鍵）」＋§4.2.3 第 7 步落款（致動器參數化；`[需核對]` 的旗標半句已由 B-11 核實）；施工圖＝本節；走本輪 §6 四方審查。

**設計期誠實劃界**：(1) 互動主視窗自己的模型 `.env` 管不到（由使用者層 settings `model`／`--model`／`/model` 決定），`--pace` 與簡報只印三鍵設定值並註明此限、不印互動視窗實際模型；(2) hook 對 Agent 未帶 model 的「缺席＝視窗模型」假設與官方序位
（general-purpose 會跟 `CLAUDE_CODE_SUBAGENT_MODEL`）有落差，方向保守（多擋不少擋），第一版不動 hook（零餘裕＋R197 准入），登記證據檔理論洞；
(3) `claude -p -r <sid> --model X` 真機行為以拋棄式 session 探針驗一次（≤2 次便宜呼叫，不碰真實 session）；(4) Windows 側本輪未驗證（mac 開發）。

### 3.2 W2 `resume_cost_pp` 喚醒成本落帳（PRD §11.3「記錄本次喚醒的實際額度成本」、§9 `autoclaude_resume_cost_pp`、§15.4 P1；R112 REQ-W6(b)(c)）

**問題陳述**：無人續跑每個窗醒來「第一個 assistant 請求吃掉多少 context／額度」全庫零資料（`resume_cost_pp` 零命中）⇒ `AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES`
（32MiB）無從校準、導出式 RESUME 門檻無資料、PRD §11.3／§9 同欠。

<Architecture_Design_Review>
1. 架構純潔性：新純函式模組 tools/lib/resume_cost.py（取值純函式與 I/O 分離；AST 鎖：不得 import `quota_gate`／`quota_escalation`，防成環）；
   唯一接線點＝`tools/lib/relay_machine.py` 的 `settle_window` 收尾（非守衛面；+≈8 行）。`tools/session_resume_planner.py` 零改動（餘裕 4、守衛面）。
2. 持久化：痕跡一行 jsonl 落持久目錄（`endurance_env.trace_dir()`），走既有 `quota_ledger.append_record()` 原子 append；零 checkpoint 欄位。
3. 安全：零 token、零網路——資料全部來自本機逐字稿（第一筆 `type=assistant` 且晚於該窗 spawn 的 `message.usage`）。**量不到寫 `measured:false`，不得寫 0**。
4. 對外 I/O：無。
</Architecture_Design_Review>

**介面 delta**：record 欄位 `{session_id, relay_seq, first_assistant_ts, input_tokens, cache_creation_input_tokens, cache_read_input_tokens, pct_before, pct_after, measured}`；
spawn 時刻不動 planner 的區域變數，改以逐字稿內「最後一筆早於 `state['reset_at']` 的 assistant 之後的第一筆」定位（`relay_machine.py:369-381` 已有 `state['transcript']`）；
`pct_before/after` 只在兩次額度快取讀數皆量得到時才填。
**LOC 落點**：resume_cost 估 ≤90 斷言行（guardrail_lib 400；落地實測 99，含採納審查鏡 spawn 錨補丁 +10，仍遠低於 tier）；relay_machine 251→≤260（400；落地 256）。**契約影響**：無。**checkpoint 欄位**：無。
**測試** tools/tests/test_resume_cost.py：(1) 合成逐字稿取值正確、cache_creation／cache_read 分流；(2) 無 usage／逐字稿缺席／無 assistant ⇒ `measured:false` 且數值欄不為 0；
(3) 零喚醒 ⇒ 痕跡檔位元組數不變（可偵測性鎖）；(4) 原子 append 不掉行；(5) 既有 `ResumeTickWritesStateOnlyAfterConfirmingTest` 不得轉紅；(6) AST 防成環鎖。
**RTM**：R6 每窗落一行成本紀錄（§11.3）→ resume_cost＋settle_window → (1)(3)(4)；R7 量不到不得寫 0 → measured 欄 → (2)。
**派工序**：與 W1 同動 tools/tests 棘輪表 ⇒ **串行於 W1 之後**（鐵律七檢查表 #2）；檔案面與 W1 不重疊。

### 3.3 W3 AutoClaude 引擎無人值守硬化包（PRD §4.5.2／§4.5.5 分片休眠；§15.5 R-6.2-2 CLI 相容性清單）

**問題陳述**：(ii) 引擎路徑 `AutoClaude/autoclaude/core/services/auto_resume.py:218`／`:283` 兩處單次 `time.sleep(wait)` 長睡——睡著後醒來超時、時鐘跳躍無法修正、
>2h 的等待仍在行程內硬等（哨兵路徑已走 OS 排程，引擎路徑沒有）；(iii) 本機 claude 2.1.295 不在 `VERIFIED_CLI_VERSIONS` ⇒ 每次 `python -m autoclaude` 啟動 loud＋DRY_RUN，
R-6.2-2 的 loud 失去鑑別力。第三方額度刷新者 (i) 本輪**不做**（需真機排程器取證＋週期打真端點的紅線 1 四條件自證），登記證據檔理論洞、列入 improving_114 候選。

<Architecture_Design_Review>
1. 架構純潔性：新純函式 AutoClaude/autoclaude/utils/sliced_sleep.py（注入式 wall／mono／sleep／stop，≈45 行）；`AutoResumeService` 兩處改呼叫它；
   不反向 import 根層 `tools/`（`.importlinter` 禁）：剩餘 > `max_inprocess_wait_seconds`（PRD §4.5.5 寫 2h；實作出廠值依本機實測校準，見 §4）時**拒絕長睡**——checkpoint 已落（帶真實續跑時刻）＋非零 rc＋log 明示需外部重啟；**本版無自動承接者**（HEAD 上無任何根層元件重啟引擎或消費其 checkpoint），登記證據檔〈三〉#3。
2. 持久化相容：`TokenGuardConfig` 加三欄（`sleep_slice_seconds`／`clock_jump_tolerance_seconds`／`max_inprocess_wait_seconds`，`Field(ge, le)`，帶預設⇒ config.yaml 零必改）；checkpoint 零新欄。
3. 安全：無新外呼；中斷（既有 `_interrupt_event`／hotkey）優雅退出。
4. 對外 I/O：無。
</Architecture_Design_Review>

**介面 delta**：`sliced_sleep(wait, slice_s, tol_s, *, wall, mono, sleep, stop) -> SleepOutcome`（每片比較 wall／mono 增量差 > tol ⇒ 重算剩餘；stop 事件 ⇒ 提早回）；
`auto_resume.py` 兩處改走它，並在剩餘 > max_inprocess 時回「拒絕長睡」結果；`verified_cli_versions.py` 補 `2.1.295` 一筆，`verified` 欄只寫本輪零 token 實測事實
（`claude --version`＝`2.1.295 (Claude Code)`；`--permission-mode default` 被接受；`--settings`／`--add-dir`／`--allowed-tools`／`--resume`／`--model` 在 help；`--max-turns` **不在** help，不得寫「存在」）。
**LOC 落點**：sliced_sleep ≤45；auto_resume 淨 ≤+15（tier 餘裕以 `python AutoClaude/tools/check_loc_budget.py --json` 現查）；config +3 欄；verified_cli_versions +25。
**契約影響**：`.importlinter` 必須仍 9 kept 0 broken（utils 不得 import core／infra）。**checkpoint 欄位**：無。
**測試**：新 AutoClaude/tests/utils/test_sliced_sleep.py（注入式時鐘，不真睡）：(1) 正常睡滿；(2) wall 跳躍 > tol ⇒ 重算並可提早結束；(3) 剩餘 > max_inprocess ⇒ 拒絕長睡、rc 非零、checkpoint 已落；
(4) 中斷 ⇒ 優雅退出；(5) wait ≤ 0 ⇒ 零 sleep；(6) AST 鎖：`auto_resume.py` 不得再直接呼叫 `time.sleep`；coverage ≥90%。
AutoClaude/tests/test_r100_boot_self_check.py +2：`cli_version_verdict('2.1.295')` ⇒ dry_run False；`verified` 文字不得含 `--max-turns` 字面。
**RTM**：R8 引擎等待不單次長睡且可被時鐘跳躍修正（§4.5.2）→ sliced_sleep → (1)(2)(4)(5)(6)；R9 >2h 不行程內硬等（§4.5.5）→ 拒絕長睡 → (3)；R10 已驗證 CLI 版本含本機 2.1.295（R-6.2-2）→ 清單 → +2 測。
**派工序**：鎖持有面在 AutoClaude/（與 W1／W2 的 tools/ 不重疊）⇒ 可與 W1 並行；任何 AutoClaude/tests 位元組變動 ⇒ 表② 指紋回填為 commit 前最後一步（收尾單人窗口）。

## §4 階段三：實作紀錄（回填；三個 Sonnet Developer 包＋兩個修復包；逐字輸出與全文住 R211 證據檔〈二〉）

| W | 落地物 | Developer 驗收逐字（主控親跑者另標） |
|---|---|---|
| W1 | `ENV_SPEC` +3 列（attr=None、kind="model"）；新 `tools/lib/model_roles.py`（`ModelRoles`／`load_model_roles`／`child_env`／`model_argv`／`roles_line`；`inherit` 只限 SUBAGENT＝不注入）；`tools/lib/resume_route.py` 接線（`_posture_argv` 尾端 `--model`、`probe_argv`、`role_env`）；planner 探針預設改讀降級角色、`_run_resume` 同一物理行併入子行程 env（planner 淨 0 行）；`quota_messages.model_hint_line` 改讀角色、`model_lines` 組合角色行；`quota_gate.pace_report` 淨 0、`session_brief` +10；`.env.example` 重生（+6 行）；讀者鎖加 model_roles；兩支 compat-ci yml paths 補新檔；新測試 `tools/tests/test_model_roles.py` 60 支 | `Ran 60 tests`／`OK`；指定集合 774 OK；修復後 14 組 `Ran 867 tests in 121.724s`／`OK`；ruff `All checks passed!`；`--print-env-example \| diff - .env.example` 零輸出；LOC violations 空（planner 746/750、quota_gate 494/500、hook raw 1089 零改動）；真機探針 call1 `--model haiku`＝modelUsage 只含 haiku，call2 `-r <sid> --model sonnet`＝haiku（累計舊回合）＋sonnet（本回合，與頂層 usage 逐項相等），合計 $0.0396。**主控親跑**（2026-10-10，本機 .env 設 fable／sonnet／haiku）：`resume_argv` 逐字＝`[…, '--settings', '<unattended.json>', '--model', 'fable', '--add-dir', …]`；`role_env()`＝`{'CLAUDE_CODE_SUBAGENT_MODEL': 'sonnet'}`；`--pace` 印「🤖 模型角色（.env AUTOSDD_MODEL_*）：主控=fable｜子代理=sonnet｜降級=haiku…」 |
| W2 | 新 `tools/lib/resume_cost.py`（落地斷言行 99／153 raw；含審查鏡 spawn 錨補丁）；`tools/lib/relay_machine.py` `settle_window` 入口接線 `record_window(state, log=log)`（+`contextlib.suppress` 第二道網；斷言行 256）；record＝規格九欄＋`model`＋`reason`＋`recorded_at`；痕跡檔 `autosdd_resume_cost.jsonl` 於 `endurance_env.trace_dir()`；新測試 `tools/tests/test_resume_cost.py` 6 支 197 行（含最終 QA 提供的 spawn 錨鎖） | `test_resume_cost` 5 OK；relay 相關 18 類 82 OK；指定五模組 339 OK；ruff `All checks passed!`；LOC 四類 violations 空；隔離變異 23 擊殺 22（餘 1 為 py3.11 等價變異）；真逐字稿 260 筆手算交叉一致。v1 限制：pct 欄恆 None；接力第二窗起 measured:false（relay-chain-anchor）；timeout 砍掉的窗不落帳 |
| W3 | 新 `AutoClaude/autoclaude/utils/sliced_sleep.py`（32 斷言行／58 raw）；`AutoResumeService` 兩處改分片休眠＋拒絕長睡（`KernelResult` halted、reason `external_resume_required`、main rc=1、checkpoint 寫回真實續跑時刻）；`TokenGuardConfig` +3 欄（出廠 30／5／18000，含 `le`）；`main.py` 接 `is_interrupted`；`verified_cli_versions.py` 補 2.1.295（三條零 token 事實）；新測試 `AutoClaude/tests/utils/test_sliced_sleep.py` 34 個方法（參數化後 53 案）＋boot self check 2＋修復包邊界／上界測試 | Developer：`4910 passed, 156 skipped in 34.59s`；修復後 `4919 passed, 156 skipped in 37.85s`；**主控親跑**（2026-10-10）：`4919 passed, 156 skipped in 36.05s`、`Contracts: 9 kept, 0 broken.`；ruff 十檔乾淨；LOC violations 空（auto_resume 295／service ≤500）；snapshot_sync rc=0；真 FileStateRepository 端到端 22 PASS |

## §5 零退化驗證矩陣（收尾單人窗口、最終工作樹、主控親跑；逐字見 R211 證據檔〈五〉）

| 檢查 | 命令 | 本輪實測 | 通過條件 |
|---|---|---|---|
| AutoClaude 全套 | `python -m pytest tests/ -q` | `4919 passed, 156 skipped in 37.34s`，rc=0 | ≥ 4864 passed／0 failed（上輪實測 floor）；乾淨 venv 回填表② ＝ 4819 passed／222 skipped |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | `Contracts: 9 kept, 0 broken.` rc=0 | 全部 kept／0 broken |
| LOC 分級 | `python AutoClaude/tools/check_loc_budget.py --json` | `total_violation: False`；absolute／tier／special／root_tools violations 皆 `[]` | 五類 violations 皆空 |
| Snapshot | `python tools/snapshot_sync.py --check`（AutoClaude/） | `[snapshot_sync] OK — Snapshot 區段 + sprint 骨架對齊一致` rc=0 | 新鮮 |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | `✅ 本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.30）` 逐軌 1475／1979／362，rc=0 | pytest not-chaos 全綠 + arch_fitness exit<2 |
| DAL 等價 | `AutoClaude/tests/equivalence/` 隨全套 | 隨全套通過；本輪無新 DAL／checkpoint 改動故無新增 round-trip 契約（N/A 類型 2） | 三後端等價 |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | N/A（類型 1：本輪零碰 `*.tla`／`_HAPPY_PATH`，`git diff --stat` 無 AISDLC_SDD/ 改動） | — |
| 根層 tools/tests | `python tools/run_root_unittests.py` | `✅ unittest 數量下限釘選通過：發現 5273 個測試（下限 5273）`，rc=0；skip 47 支全數有標籤；真實 TEMP 圍籬零變動 | rc=0；MIN_TESTS 重釘 5101→5273 |
| 守門工具 | crossref／carriers／archive／sync／nightly-anchor | crossref rc=0（`未結存量 0 列`、`具名治理文件 165 份皆已登記`）；carriers rc=0；`archive_defect_log.py --check` rc=0；`sync_onboarding_baselines.py --check`／`--check-snapshot` rc=0（表② macOS 欄指紋相符 autoclaude=1975dfb92b6d）；`refresh_nightly_anchor.py --check-head` rc=0（nightly-run=37324659627）；`ruff check tools/ .claude/hooks/` `All checks passed!` | 皆 rc=0 |

## §6 四方 Zero-Trust 審查閉環（全文與逐條 findings 住 R211 證據檔〈二〉）
- W3：QA 鏡 CONDITIONAL（QA3-01）＋ SD／Architect 鏡 CONDITIONAL（SD3-01～04）→ 修復包全數處置（預設 30／5／18000、無自動承接者文字、真實續跑時刻寫回、邊界鎖）。
- W1：SD／Architect 鏡 CONDITIONAL（SD1-01、SD1-02）＋ QA 鏡 CONDITIONAL（QA1-01）→ 修復包處置（CI paths、`inherit` 出口、無消費者 re-export 移除、PRD 12 條訂正）。
- W2：SD＋QA 合一鏡 APPROVE，附三份補丁（主控採納並套用）。
- 最終 QA 複審：REJECT（FQ-01：spawn 錨未接線 `log=log`，死碼＋零測試）→ 主控一字接線＋落地 QA 提供的鎖測試（接線前紅、接線後綠）→ 主控親驗；FQ-02～05（P3）全數處置、FQ-06～08（P4）登記。
- 流程缺陷自我登記：主控任務書曾允許 QA 鏡在共用樹就地突變（SD1-13）；已改為一律隔離副本並寫入記憶。

## §7 本輪缺陷帳本列
- DEF-200-507（模型角色零參數化）fixed（2026-10-10）；DEF-200-508（喚醒成本零資料）fixed（2026-10-10）。未結 0／209 列；外部阻塞軌 5、結構性長債軌 6 不變。

## §8 誠實劃界
- 本輪全程 macOS 開發驗證；Windows 側 improving_113 期間未驗證（待辦見 R211 證據檔〈六〉）。
- `inherit`／`CLAUDE_CODE_SUBAGENT_MODEL` 在真實喚醒窗口內的子代理行為層只有官方文件＋二進位字串證據；`claude -p -r <sid> --model` 真機探針 1 次（拋棄式 session）。
- W2 v1：pct 欄恆 null；timeout 砍掉的窗不落帳；§9 Prometheus 指標未接。W3：PG／Dual 後端 pin 路徑未實跑；機器睡眠下單調鐘行為只依文件；拒絕長睡無自動承接者。
- 三軸成熟度本輪未重量測；B 柱 dogfooding 只維持最小面（既有 FSM 狀態、缺陷紀律）；C 軌工作流帳本未另立 `AutoClaude/docs/04_planning/` 新檔，W3 以本檔 §3.3／§4 為載體（AutoClaude 自身 G0~G6 以 pytest／lint-imports／LOC／snapshot 四閘門實跑代替）。
- 護欄層本輪淨增 +787（回歸鎖軌 309、主軌 478，款(11) 連升第 1 輪）；下一輪若主軌仍為正即連升第 2 輪，第三輪必須 ≤0。（史料：improving_114 終輪以 R211 同輪第二列 −9 併計，系列隨後休眠，見該檔 §6。）
- PRD 覆蓋度：按「缺規範性機制即 ⚠️」逐列計 60.3%（⚠️=0.5），掌舵者口述的「剩 25～30%」對應 ⚠️≈0.72 權重；下一輪重盤請沿用 R211 姊妹檔矩陣的同一算法。（史料：已由 PRD v2.1.17 §16.3／§16.5 取代——之後不重盤、不當門檻。）

<!-- guard-total:R211 --> R211 護欄層累積淨額＝ 114811 → 115592（+781，回歸鎖軌申報 309、主軌 472 ≤ 517，款(11) 連升第 1 輪；improving_114 終輪同輪第二列 −9、T1 立案第三列 +3 併計）——improving_113 收尾單人窗口：test_model_roles.py 573、test_resume_cost.py 197、attr=None 讀者鎖 +2，加本表自身漂移（重釘列、回歸鎖軌同輪列、接鏈列 DEF-200-507）。逐檔清單見 CrossPlatform_R211_ZeroTrust_Audit_113.md〈二〉〈五〉。
