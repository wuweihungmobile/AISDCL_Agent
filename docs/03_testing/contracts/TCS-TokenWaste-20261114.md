# TCS-TokenWaste-20261114：等待與續跑造成的 token 浪費（需求＋驗收合一）

> 落檔：`docs/03_testing/contracts/TCS-TokenWaste-20261114.md`。設計全文＝`docs/04_planning/ADR/ADR-XPLAT-004-token-endurance-protocol.md` §2.14（下稱 ADR；本棒 `ADR_SECTION.md`）。缺陷帳本列＝DEF-200-587（一列涵蓋續棒冷熱、收斂、快層先行、探針四件，見 §9）。
> 來源任務書＝四方任務書（sid `680d8411-58ac-4adb-9e23-521f6a7bb557`，2026-11-14）；SA 浪費帳＝`SA_WASTE_REPORT.md`＋探針；Architect 定案＝`ARCH_DESIGN.md`。
> **狀態（2026-11-15）**：實作已併入 main；AT 全數有測試（狀態對照見 §2.9）。hook 與 settings 接線隨 `.claude/` 批次由主控親套，套用前 hook 層 AT 為預期紅。🔴 §3 真機驗證 V-T1～V-T3／V-G1／V-G2／V-P1／V-C2 皆**待主控真機驗證**，未驗，不得寫成已驗。
> 測試一律注入縫：時間注入 `now`（aware datetime）、路徑注入 tmp 圍籬（`projects_dir`／`HOME`／`AUTOSDD_TRACE_DIR`／`AUTOSDD_HANDOFF_DIR`），**不讀本機真實 `~/.claude`、不起真排程、不起真 claude、不起 Docker、不外呼 GitHub**。

## 0. 範圍與模組落點表（照 Root_Layout §2）

第一期（本 TCS 要實作者）：G1 續棒看快取冷熱、G2 收斂閘、G4 pre-push 快層先行、浪費帳探針入 repo。**條件項**：G3 `long-runner` 子代理型別（§4：V-T1～V-T3 通過才落地，實作只產 staged 檔）。**不做**：G5～G8（ADR §2.14 已否決或延後）。

| 元件 | 路徑 | §2 格 | 持有者（見 `DEV_BRIEF.md`） |
|---|---|---|---|
| 冷熱判準（純函式） | `tools/lib/sessionctl/cachestate.py`（新） | 模組套件 | Dev-1 |
| 收斂閘判準 | `tools/lib/sessionctl/converge.py`（新） | 模組套件 | Dev-1 |
| 續棒閘改寫 | `tools/lib/sessionctl/roster.py::resume_gate`（既有） | 模組套件 | Dev-1 |
| 門檻鍵 `HARD_CTX_KEY`、`trace()` | `tools/lib/sessionctl/switch.py`（既有）；宣告 `tools/lib/quota_policy_env.py::ENV_SPEC` | 模組套件／政策單一家 | Dev-1 |
| 已出聲查詢 `is_advised` | `tools/lib/sessionctl/handoff.py`（既有；`_trace` 改委派 `switch.trace`） | 模組套件 | Dev-1 |
| hook 接線 | `.claude/hooks/sessionctl_guard.py`（既有；staged） | 守衛面 | Dev-1（staged，主控親套） |
| hook 註冊 | `.claude/settings.json` sessionctl PreToolUse 條目（staged 片段） | 守衛面 | Dev-1（staged，主控親套） |
| G3 子代理型別 | long-runner 定義檔（.claude/agents/ 下，尚未進 repo）（新；staged；**條件項**） | 守衛面（受保護路徑） | Dev-1（staged） |
| pre-push 快層先行 | `tools/git-hooks/pre-push`（既有） | 非守衛面 | Dev-2 |
| 浪費帳函式庫 | `tools/lib/wastecensus/{__init__,reader,metrics,report}.py`（新套件） | 模組套件 | Dev-2 |
| 浪費帳入口（薄殼探針） | `tools/probe/waste_census.py`（新；不含判準；不接閘門 rc） | 量測探針 | Dev-2 |
| 測試（新三檔） | `tools/tests/test_sessionctl_cachegate.py`、`test_sessionctl_converge.py`、`test_waste_census_metrics.py` | 測試 | Dev-1：前二；Dev-2：後一 |
| 測試（既有檔增量） | `test_sessionctl_hooks.py`、`test_sessionctl_roster.py`、`test_sessionctl_switch.py`、`test_pre_push_dispatcher.py`、`test_check_hooks_liveness.py`（基準表一格）、`test_quota_policy.py`（若鎖數鍵數） | 測試 | 見 DEV_BRIEF 所有權表 |
| Stop 推回判準 | `tools/lib/sessionctl/converge.py::stop_verdict`（與 `converge_verdict` 同檔共用 `_gate`） | 模組套件 | Dev-1 |
| Stop 接線 | `.claude/hooks/sessionctl_guard.py` Stop 分支（staged，主控親套） | 守衛面 | Dev-1（staged） |
| 規格／帳本 | 本檔；ADR-XPLAT-004 §2.14；`docs/06_quality/AutoSDD_Defect_Log.md`；Root_Layout §3 登記表新增兩格 | 03／04／06／02 | Closer |

涵蓋判定（現查，詳 `LOCK_SURVEY.md`）：CI `paths` 兩支 compat workflow 已含 `tools/lib/sessionctl/**`、`tools/probe/**`、`tools/git-hooks/**`、`tools/tests/**`；新套件 `tools/lib/wastecensus/**` 已於收尾補入（同 commit）。SelfImproving `non_evolvable_globs`：`tools/lib/sessionctl/**` 已涵蓋新檔；`wastecensus` 是量測不是守衛，不納入。

## 1. 需求（FR）

每條需求對回任務書 §2 成功判準（下稱 CR1～CR5）與 SA 指標（M1～M5、M2b／M2c／M2d／M3d）。

| FR | 內容 | 對應判準／指標 | 守衛面暴露證據（§6） |
|---|---|---|---|
| FR-TW-01 | SendMessage 目標代理「冷」＝目標最後一筆 assistant 記錄距今 ≥ 其實際快取壽命減安全邊際；冷 ∧ 上下文 ≥ `AUTOSDD_RESUME_AGENT_TOKENS` ⇒ **互動與無人皆阻斷**（rc 2），訊息給確切下一步（派新代理＋短任務書指向交卷檔） | CR3（接續成本有上界）；M2b、M3a | E-1、E-2 |
| FR-TW-02 | 快取壽命取證據不取設定：目標代理尾端 256 KB 內任一筆 assistant usage 的 `cache_creation.ephemeral_1h_input_tokens > 0` ⇒ 1 小時，否則 5 分鐘 | M2b、M2d | E-1 |
| FR-TW-03 | 熱（未冷）的互動續棒放行且**不出聲**（取代 ADR §2.13.9 X4 的「互動只出聲」）；無人窗口行為不放寬：上下文 ≥ 門檻一律照舊阻斷（不論冷熱） | CR3；不放寬既有門檻 | E-1 |
| FR-TW-04 | 互動逃生口：SendMessage 的 `message` 含 `續棒理由：<WHY>`（全形冒號、WHY 去頭尾空白後 ≥ 8 字）⇒ 放行並落痕跡 `resume_gate_override`；`AUTOSDD_UNATTENDED` 有設時逃生口無效 | M3d | E-1 |
| FR-TW-05 | 收斂閘：本 session 已出聲（`<handoff>/<sid>.advised` 存在）∧ 主控上下文 ≥ `AUTOSDD_SWITCH_HARD_CTX_TOKENS` ⇒ PreToolUse 對 `Agent`／`Task`／`Workflow` 回 rc 2；`Read`／`Edit`／`PowerShell`／`SendMessage` 等一律不擋；訊息逐字給三條出口（交卷→`--finalize`→`--spawn`／`/compact`／逃生口） | CR2；M2、M1 | E-3 |
| FR-TW-06 | `AUTOSDD_SWITCH_HARD_CTX_TOKENS` 住 `ENV_SPEC`，出廠 290,000，**只准下修**（覆寫大於出廠退出廠值＋出聲）；`AUTOSDD_SESSION_SWITCH_MODE` 為 `notify`／`off`、或 `AUTOSDD_UNATTENDED` 有設時收斂閘不阻斷 | CR2；不放寬既有門檻 | E-3 |
| FR-TW-07 | hook 面：`sessionctl_guard.py` 多認 `Agent`／`Task`／`Workflow`；`settings.json` 同一條 PreToolUse 條目的 matcher 擴為 `SendMessage\|Agent\|Task\|Workflow`；解析不到、逐字稿讀不動、payload 退化一律放行（fail-open）；任何例外 rc 0 | 守衛面不退化 | E-3 |
| FR-TW-08 | pre-push 先跑快層（十一支守門＋`ruff check tools/ .claude/hooks/` 及其後兩道），**快層任一紅即停**：印出紅的那一道與「修完再推」、rc≠0、**不啟動慢層與任何背景 leg**；快層全綠才進 AutoClaude／SDD／root-infra 慢層；慢層內部維持「失敗累積進 rc、不中斷其他 leg」 | CR4；M4 | E-4 |
| FR-TW-09 | 浪費帳探針入 repo：`tools/probe/waste_census.py` 薄殼＋`tools/lib/wastecensus/` 套件；重現 SA 基線（M1、M3a、M4、M5）並新增 M2b、M2c（按代理型別分組）、M2d、M3d 與 `--replay-hard-ctx`（收斂閘門檻取值重放）；零 token、只讀逐字稿、不接閘門 rc | CR1、CR5 | E-1、E-3 |
| FR-TW-10 | **條件項（§4）** long-runner 定義檔（.claude/agents/ 下，尚未進 repo）：`model: sonnet`、`experimental.cacheTtl: 1h`、不寫 `tools`；本文只寫「依任務書、讀根 CLAUDE.md、交卷用 SubagentHandback」。V-T1～V-T3 通過才落地 | CR3（接續成本）；M2c、M2d | E-5 |
| FR-TW-11 | 痕跡事件寫 `endurance_env.trace_dir()/autosdd_session_switch.jsonl`：`resume_gate_block`、`resume_gate_override`、`converge_block`；欄位見 DEV_BRIEF；寫不進去不拋 | CR5；M3d | — |
| FR-TW-12 | 等待自帶截止且短於主控快取壽命：`tools/ci_wait.py` 的預設 `timeout_min` 必須 < 60（主控 1 小時壽命）；現值 40，由 `tools/tests/test_ci_wait.py::RobustnessTest::test_default_deadline_is_shorter_than_the_main_cache_lifetime` 釘住（收尾棒已加） | CR1 | E-6 |
| FR-TW-13 | 回合結束（Stop）時，若：本 session 已出聲（`<handoff>/<sid>.advised` 存在）∧ 主控上下文 ≥ `AUTOSDD_SWITCH_HARD_CTX_TOKENS` ∧ 無執行中背景**代理**（背景 shell 不算；優先讀 payload `background_tasks`，缺席退讀檔名冊）∧ 本 session 無「已 finalize」的 live 交接包 ∧ `stop_hook_active` 為假 ∧ 非 `AUTOSDD_UNATTENDED` ∧ `AUTOSDD_SESSION_SWITCH_MODE=auto` ⇒ 輸出 `{"decision":"block","reason":…}` 推回一次，reason 給確切下一步（補完交接包主控層 → `handoff --finalize` → `--spawn`；或 `/compact`；或 `AUTOSDD_SESSION_SWITCH_MODE=notify`）。第二次 Stop（`stop_hook_active` 為真）一律放行＝每回合至多一個額外回合。有背景代理在跑時維持既有 `systemMessage` 出聲、不推回。不寫閂鎖（上下文降到門檻下即自動解除）。落痕跡 `converge_stop_block`（欄位 `sid`、`ctx`、`hard`）。任何例外、逐字稿讀不動一律放行（fail-open） | CR1（事故形態：大上下文＋背景等待＋結束回合）、CR2 | E-3（事故：Stop 時點恰在 20:52 之後；G2 對該序列零介入） |

## 2. 驗收測試（AT）

縫代號：`NOW`＝`now`；`FS`＝tmp 圍籬造逐字稿／meta／handoff 目錄；`ENV`＝`env` mapping 參數；`TRACE`＝`AUTOSDD_TRACE_DIR` 指 tmp；`PAYLOAD`＝手造 hook payload。每條 AT 附「為何業務邏輯改掉時會紅」。

### 2.1 冷熱判準（`test_sessionctl_cachegate.py::CacheStateTest`；縫 FS、NOW）

函式：`cachestate.cache_state(path, now) -> {"tier": "5m"|"1h", "idle_s": float|None, "cold": bool}`。夾具：`_agent(ctx, minutes_ago, h1=0)` 寫一筆 assistant 記錄，`usage.cache_creation = {"ephemeral_5m_input_tokens": x, "ephemeral_1h_input_tokens": h1}`。

| AT | 前置 | 動作 | 預期 | 為何會紅（意圖） |
|---|---|---|---|---|
| AT-TW-01 | 5m 型代理，最後 assistant 記錄 10 分鐘前 | `cache_state` | `tier=="5m"`、`cold is True` | 把閾值改回只看上下文大小，冷熱欄就不存在 |
| AT-TW-02 | 5m 型，1 分鐘前 | 同 | `cold is False` | 若冷判準寫成「有 usage 就冷」，熱續棒會被誤擋（逼人白重做） |
| AT-TW-03 | 5m 型，恰 `300−CACHE_MARGIN_SECONDS` 秒前；與少 1 秒 | 同 | 前者 `cold is True`、後者 `False`（邊界；`CACHE_MARGIN_SECONDS=30`） | 守住「hook 判斷時刻早於實際請求時刻」的偏差；SA 實證有一筆 299.995 秒間隔仍整份重寫（`rewrite` 列 sid `d4ed2654`…該筆 `gap_s=299.995`、`rewrite_tokens=625,290`），沒有邊際會放行它 |
| AT-TW-04 | 尾端內某筆 usage `ephemeral_1h_input_tokens>0`，最後記錄 10 分鐘前 | 同 | `tier=="1h"`、`cold is False` | 若 tier 只看**最後一筆** usage，純讀回合（寫入 0）會把 1h 代理誤判成 5m，熱代理被誤擋 |
| AT-TW-05 | 同上但最後記錄 61 分鐘前 | 同 | `tier=="1h"`、`cold is True` | 1h 的冷線不得沿用 5 分 |
| AT-TW-06 | usage 無 `cache_creation` 欄（舊格式） | 同 | `tier=="5m"` | 缺欄必退保守（5m＝較早判冷＝較不浪費的方向）；若改成缺欄當 1h，舊格式代理會漏擋 |
| AT-TW-07 | 最後一筆記錄是 `user`（tool_result），其前的 assistant 記錄在 8 分鐘前 | 同 | `idle_s` 以**最後 assistant 記錄**起算（約 480）、`cold is True` | tool_result 不重設快取計時器；用「任何記錄」起算會把冷代理誤判成熱 |
| AT-TW-08 | 檔不存在／空／壞 JSON／無 assistant 記錄 | 同 | `cold is False`、`idle_s is None`（fail-open） | 量不到不得單方面阻斷（誤擋只差一步的代理代價更高；既有 AT-SC-64 同方向） |

### 2.2 續棒閘（`test_sessionctl_cachegate.py::ResumeGateTest`＋`test_sessionctl_roster.py` 既有 AT-SC-61 改寫；縫 FS、ENV、TRACE、NOW）

`resume_gate(payload, env, now=None) -> (rc, text)`（新增可選 `now`；缺省取現在，向後相容）。

| AT | 前置 | 動作 | 預期 | 為何會紅 |
|---|---|---|---|---|
| AT-TW-09 | 互動；目標 5m 型、上下文 150,000、**10 分鐘前**最後記錄 | `resume_gate` | `rc==2`；訊息含 `續棒成本閘`、`改派新代理＋短任務書`、`續棒理由：` | 若互動仍只出聲（X4 原狀），冷續棒逃過阻斷；SA 基線 141 件中 140 件是冷（`rewrite` 列 `gap_s>=300`），合計 68.2M tok |
| AT-TW-10 | 互動；同上但 **1 分鐘前** | 同 | `(0, "")`（放行、不出聲） | 熱續棒只付 0.1× 讀，比新代理便宜；阻斷它＝逼人多付；若仍出聲＝新增只出聲提醒（任務書禁止） |
| AT-TW-11 | 互動；冷、上下文 149,999 | 同 | `(0, "")` | 門檻邊界；上下文小的冷代理重寫成本低於新代理的啟動成本 |
| AT-TW-12 | 互動；冷、150,000；`message`＝`續棒理由：上一棒只差一個檔未寫完` | 同 | `rc==0`、輸出不含阻斷；TRACE 檔新增一行 `event=="resume_gate_override"`，含 `target`、`ctx`、`reason` | 沒有逃生口＝守衛會被整個關掉（鐵律五同判準）；沒有痕跡＝M3d 量不到放行次數 |
| AT-TW-13 | 互動；冷、150,000；`message`＝`續棒理由：因為` （少於 8 字） | 同 | `rc==2` | 理由必填是逃生口不淪為整包 noqa 的唯一約束 |
| AT-TW-14 | **無人**（`AUTOSDD_UNATTENDED=1`）；冷、150,000；帶合格 `續棒理由：…` | 同 | `rc==2`（逃生口無效） | 無人窗口沒有人可問；與 `git-guard-ok` 的分層慣例同 |
| AT-TW-15 | **無人**；**熱**（1 分鐘前）、450,000 | 同 | `rc==2`（既有 AT-SC-62／65 行為不放寬） | 若無人窗口也跟著「熱放行」，等於放寬 E1 的既有阻斷；任務書禁止放寬 |
| AT-TW-16 | 互動；冷；`tool_input.recipient`（缺 `to`） | 同 | 同 AT-TW-09（目標欄後援） | 目標欄後援是既有契約（沙盒 V-S2） |
| AT-TW-17 | 互動；冷、150,000、阻斷發生 | 同 | TRACE 新增 `event=="resume_gate_block"`，含 `target`、`ctx`、`idle_s`、`tier` | M3d 的分子；沒有就量不到機制自身成本與效果 |
| AT-TW-18 | 目標不存在／`to` 非字串／逐字稿壞（既有 AT-SC-64 全部樣本） | 互動與無人各一遍 | 皆 `(0, "")` | fail-open 不得被改寫 |
| AT-TW-19（改寫） | 既有 `test_at_sc_61_*`（函式層與 hook 層）：互動、150,000、**1 分鐘前** | 原動作 | 預期由「出聲含改派新代理」改為「`(0,"")`／stdout stderr 皆空」；原斷言保留到 AT-TW-09（冷）上 | 這是 X4 修訂的明文後果；改寫必須在 commit 訊息與 ADR §2.14 記錄 |

### 2.3 收斂閘（`test_sessionctl_converge.py`；縫 FS、ENV、TRACE）

函式：`converge.converge_verdict(payload, env) -> (rc, text)`；`handoff.is_advised(sid, base=None, env=None) -> bool`（唯讀、不 mkdir）。夾具：tmp 逐字稿 `<sid>.jsonl` 末筆 assistant usage 合計 `ctx`；`<handoff>/<sid>.advised` 存在與否。

| AT | 前置 | 動作 | 預期 | 為何會紅 |
|---|---|---|---|---|
| AT-TW-20 | 已出聲；ctx=290,000；tool=`Agent` | `converge_verdict` | `rc==2`；訊息含 `收斂閘`、實際 ctx 數字、`handoff --finalize`、`--spawn`、`/compact`、`AUTOSDD_SESSION_SWITCH_MODE=notify` | 沒有「確切下一步」的阻斷是死路，守衛會被關 |
| AT-TW-21 | 已出聲；ctx=289,999；`Agent` | 同 | `(0, "")` | 邊界；若寫成 `>` 而非 `>=`，**事故 sid 的 20:52 上下文（293,672）與門檻 290,000 的差距**就被一格邊界吃掉 |
| AT-TW-22 | **未出聲**（無 `.advised`）；ctx=400,000；`Agent` | 同 | `(0, "")` | 沒被告知就被擋＝不公平且不可解釋；「出聲在先」是閘的前提 |
| AT-TW-23 | 已出聲；ctx=400,000；tool=`Read`／`Edit`／`PowerShell`／`Grep`／`SendMessage`／`Bash` 各一 | 同 | 全部 `(0, "")` | 收斂本身需要這些；擋到無法收斂的守衛會被整個關掉（鐵律五、context_budget_guard 同判準） |
| AT-TW-24 | 已出聲；ctx=400,000；`Task`／`Workflow` | 同 | `rc==2` | 三個展開型工具名一個都不能漏；matcher 與腳本射程各自釘 |
| AT-TW-25 | 已出聲；ctx=400,000；`AUTOSDD_UNATTENDED=1` | 同 | `(0, "")` | 無人窗口的換 session 由 planner FRESH 路負責（ADR §2.13.5）；無人時擋展開型工具＝窗口卡死 |
| AT-TW-26 | 已出聲；ctx=400,000；`AUTOSDD_SESSION_SWITCH_MODE=notify`／`off` | 同 | 各 `(0, "")`；`auto`（及缺席、未知值）⇒ `rc==2` | 逃生口語意＝既有 `switch_mode` |
| AT-TW-27 | 已出聲；逐字稿不存在／無 assistant usage／壞 JSON；payload 無 `transcript_path` | 同 | 皆 `(0, "")` | fail-open |
| AT-TW-28 | 已出聲；ctx=400,000；payload 帶非空 `agent_id`（子代理自己的呼叫） | 同 | `(0, "")` | 閘管主控；子代理上下文由 D6／TTL 管 |
| AT-TW-29 | 已出聲；阻斷發生 | 同 | TRACE 新增 `event=="converge_block"`，含 `sid`、`ctx`、`hard`、`tool` | M2 的上界驗證需要分子 |
| AT-TW-30 | 已出聲；先 ctx=400,000 ⇒ 阻斷；再把逐字稿尾端追加一筆 assistant usage 合計 120,000（模擬 `/compact` 後新回合） | 同一 payload 再判 | 第二次 `(0, "")`（自動解除，不需任何人關） | 若阻斷進閂鎖（擋一次就記住），`/compact` 之後仍被擋 |
| AT-TW-31 | `AUTOSDD_SWITCH_HARD_CTX_TOKENS` 覆寫 200,000／400,000／`abc`／`-1` | `switch.threshold(HARD_CTX_KEY, env)` | 200,000 生效；400,000 退出廠值＋stderr；病態值退出廠值＋stderr | 方向鎖：放寬＝回到「出聲後無限續做」（SA：事故 session 出聲後續做 3.7 小時） |
| AT-TW-32 | 讀 `ENV_SPEC` | 斷言 | `HARD_CTX_KEY` 的 `default <= 290000`、`HARD_CTX_KEY in switch._DOWNWARD_ONLY`、`HARD_CTX_KEY > R1 出廠值`（硬門檻必須高於提醒門檻，否則出聲前就擋） | 只准下修由「出廠值上限」鎖＋「必須嚴格大於 R1」雙向鎖；改大即紅 |

### 2.4 hook 層與註冊（`test_sessionctl_hooks.py` 既有檔增量＋`test_check_hooks_liveness.py` 基準表一格；hook 子程序 AT 在 staged hook 套用前整組紅屬預期，見 `DEV_BRIEF.md` APPLY）

| AT | 前置 | 動作 | 預期 | 為何會紅 |
|---|---|---|---|---|
| AT-TW-33 | 子程序跑 hook；PreToolUse／`Agent`、已出聲、ctx 400,000 | `_run_hook` | rc 2、stderr 含 `收斂閘`、stdout 空 | hook 沒轉發 rc＝閘只存在於函式層 |
| AT-TW-34 | 同上但 `Bash`、`Read`（matcher 被改寬時的第二道限縮） | 同 | rc 0、無輸出 | 既有 `test_other_events_and_other_tools_are_ignored` 擴樣本：`Bash` 仍被忽略，`Agent` 不再被忽略 |
| AT-TW-35 | 子程序；`SendMessage`、冷、150,000、互動 | 同 | rc 2、stderr 含 `續棒成本閘`（hook 層對應 AT-TW-09） | hook 層必須吃到互動阻斷 |
| AT-TW-36 | 子程序；`SendMessage`、熱、150,000、互動 | 同 | rc 0、stdout／stderr 皆空 | 同 AT-TW-10 的 hook 層 |
| AT-TW-37 | 空 payload／壞 JSON／`AUTOSDD_SESSIONCTL_GUARD_OFF=1`＋已達閘 | 同 | rc 0 | 既有 fail-open 與逃生口不得被擴射程破壞 |
| AT-TW-38 | 讀 `.claude/settings.json` | 取 sessionctl 的 PreToolUse 條目 | 恰一條、`matcher == "SendMessage\|Agent\|Task\|Workflow"`；exec form（`args[0]` 以 `_hook_launcher.py` 結尾）；Stop 條目不變 | 少註冊一個工具＝閘對該工具靜默失效而表徵與修好相同 |
| AT-TW-39 | `test_check_hooks_liveness._REGISTRATION_BASELINE[("PreToolUse", sessionctl_guard)]` | 讀值 | 為 `{"SendMessage","Agent","Task","Workflow"}`；shrink-only 棘輪：拿掉任一工具即 `registration_shrink_problems` 非空 | 基準表不更新＝射程縮小而棘輪看不見 |

### 2.5 pre-push 快層先行（`test_pre_push_dispatcher.py` 既有檔增量；縫 FS＝fake repo、marker）

沿用該檔 `TestPrePushDispatcher` 的 fake repo 夾具（每個 leg 以 marker 檔證明有沒有被啟動）。

| AT | 前置 | 動作 | 預期 | 為何會紅 |
|---|---|---|---|---|
| AT-TW-40 | push 範圍含 `AutoClaude/` 與根層檔（兩 leg 皆觸發）；快層一支守門（`check_ntfs_paths.py`）回 rc 1 | 跑 dispatcher | rc 1；輸出含 `check_ntfs_paths.py 失敗` 與 `修完再推`；`marker_autoclaude`、`marker_sdd`、`marker_rootinfra`（慢層）**皆不存在**；輸出不含 `背景並行` 字樣 | 這是今天事故的形態：快層（ruff）在慢層**之後**才跑，紅了前面全白跑。若順序沒換，三個 marker 會存在 |
| AT-TW-41 | 同上但快層全綠 | 同 | rc 0；三個 marker 皆存在；快層輸出行號**先於**任一 leg 啟動行（取輸出字串 index 比大小：快層標頭行 index < `push 範圍含 AutoClaude/` 行 index） | 若快層被誤刪或快層紅也續跑，AT-TW-40／41 之一必紅；index 比較守的是「先」而不只是「有」 |
| AT-TW-42 | 純子專案 push（只 `AutoClaude/x.txt`）；快層守門紅 | 同 | rc 1；`marker_autoclaude` 不存在（既有 `test_root_guard_fast_tier_failure_blocks_push` 的加強：現況 AutoClaude leg 仍會先啟動） | 既有測試只斷言 rc 與訊息，不斷言「慢層未啟動」；這正是順序缺陷能通過既有鎖的原因 |
| AT-TW-43 | 快層**多支**同時紅（兩支守門各回 1） | 同 | 兩支皆被列出（快層內部維持「逐支跑完累積」；只在快層出口短路） | 判準是「快層全跑完再決定停」，不是「第一支紅就停」——否則修一個再推又紅一個，多一輪 |
| AT-TW-44 | 慢層內部：`run_root_unittests` 紅、py_compile 紅 | 同 | 兩者皆被印出（慢層內部累積不中斷，既有 `test_syntax_error_under_tools_fails_the_rootinfra_leg` 不動） | 取捨只動「快→慢」之間，不動慢層內部 |
| AT-TW-45 | 刪遠端分支／空 stdin fail-safe（既有 `test_branch_deletion_*`、`test_empty_stdin_failsafe_*`） | 跑既有 | 全綠 | 順序重排不得改分流語意 |
| AT-TW-46 | `tools/tests/test_root_infra_parity.py` 的 `test_guard_count_claims_match_loop`、`test_pre_push_fast_layer_runs_ruff_too`、`test_the_executor_lock_is_not_satisfied_by_an_echo` | 跑既有 | 全綠（迴圈項數與「十一支守門工具」宣稱不變；執行行字面 `if ! ruff check tools/ .claude/hooks/ --no-cache` 保留） | 重排時最容易誤刪的就是這兩條字面 |

### 2.6 浪費帳探針（`test_waste_census_metrics.py`；縫 FS＝tmp 合成逐字稿、NOW）

夾具：`_write_main(sid, turns)`／`_write_agent(sid, aid, turns)` 造最小逐字稿（每回合含 `message.id`、`usage`、`timestamp`）。**不讀真實 `~/.claude`**（`--base` 參數指 tmp）。

| AT | 前置 | 動作 | 預期 | 為何會紅 |
|---|---|---|---|---|
| AT-TW-50 | 合成：子代理 5m 型，交卷後 10 分鐘被續棒（重寫＝ctx） | `reader.collect` → `metrics.rewrites` | 1 件、`tier=="5m"`、`rewrite_tokens` 約等於 ctx、`cause=="other_user"` | 重寫判準是整個探針的根；歸因錯了所有指標失真 |
| AT-TW-51 | 合成：主控 1h 型，閒置 70 分鐘後整份重寫、prev_ctx 300,000 | `metrics.m1` | 計 1 件；閒置 50 分鐘者計 0 | M1 的 `gap_s>3600`、`prev_ctx>=250,000` 邊界 |
| AT-TW-52 | 合成：子代理 `other_user` 起因重寫 4 件，其中 prev_ctx 149,999 一件、≥150,000 三件 | `metrics.m2b` | `count==3`、另回 `le60min` 子計 | M2b 以 `AUTOSDD_RESUME_AGENT_TOKENS` 為分界，門檻改了指標隨之改（取 `switch.threshold`，不寫死） |
| AT-TW-53 | 合成：子代理 `tool_result`／`task_notification` 起因、間隔 ≤60 分重寫 3 件，分屬 `general-purpose`×2、`long-runner`×1 | `metrics.m2c` | 總 3；按 `agent_type`（取自 meta.json `agentType`，缺則 `unknown`）分組 `{general-purpose:2,long-runner:1}` | G3 上線後分組欄是判斷「1h 型是否真的消掉長等待重寫」的唯一證據 |
| AT-TW-54 | 合成：兩個 `long-runner` 代理，一個有 ≥6 分鐘間隔的回合、一個全程連續 | `metrics.m2d` | `zero_wait_share==0.5` | 選錯型別的溢價監看；沒有此欄 G3 選錯時純虧而無人知 |
| AT-TW-55 | TRACE 內合成 `resume_gate_block`×3、`resume_gate_override`×1、`converge_block`×2 | `metrics.m3d` | `{blocked:3, overridden:1, converge_blocked:2}`；缺檔回全 0 | 機制自身效果與逃生口使用量的唯一量測 |
| AT-TW-56 | 合成主控逐字稿三個 session（首次 ≥R1 後各自走到不同 ctx）＋派工事件 | `report.replay_hard_ctx(r1, candidates)` | 輸出每個候選 H 的 `sessions_reaching_H`、`room_turns_median`、`room_turns_p25`、`blocked_dispatches`、`incident_blocked`（事故 sid/ts 可由參數指定） | 取值可重放是 Q-A1 的驗收；探針不能重放＝門檻只剩一個魔術數字 |
| AT-TW-57 | `--out` 預設 | 跑 CLI（`subprocess`，`--base tmp`） | rc 0；stdout 含 `浪費排序`、`M1`、`M2b`；jsonl 每列有 `kind`；**不寫入 repo 內任何檔** | 探針不接閘門 rc、不污染工作樹 |
| AT-TW-58 | 逐字稿某行壞 JSON／缺 usage | 同 | 略過該行、不拋、`summary` 內 `skipped_lines` 計數 | 真實逐字稿必有壞行；探針崩潰＝不可重放 |
| AT-TW-59 | 包結構 | 斷言 | `tools/probe/waste_census.py` 非空薄殼（斷言行 ≤ 80，無判準函式定義，只 import `lib.wastecensus`）；`lib/wastecensus/*.py` 每檔 ≤ 400 斷言行 | 落點規範與 LOC 分級：探針判準住 lib、入口薄殼 |

### 2.7 其他（既有鎖不得退化；跑既有，不新增）

| AT | 內容 |
|---|---|
| AT-TW-60 | `test_quota_policy.py`／`test_context_budget_guard.py` 的 `.env.example` 生成物鎖與「ENV_SPEC 每鍵有讀取點」鎖全綠：新鍵常數 `HARD_CTX_KEY` 必須住 `switch.py`（該鎖的消費者清單只含 `switch.py`），`.env.example` 以 `--print-env-example` 重生 |
| AT-TW-61 | `test_doc_loc_baseline_freshness_r60.py::TestR74…`／`TestR79…`：根 CLAUDE.md〈機械守衛總表〉sessionctl 列仍點名 `sessionctl_guard.py`，且（Closer）列文改述射程 |
| AT-TW-62 | `test_root_module_layout.py`：Root_Layout §3 登記表新增反引號路徑皆存在於磁碟（`tools/lib/sessionctl/cachestate.py`、`converge.py`、`tools/lib/wastecensus/`、`tools/probe/waste_census.py`）；`tools/lib/` 無新增未成套件同前綴散檔 |
| AT-TW-63 | `test_sessionctl_*` 既有 AT-SC-01～90 全綠（改寫僅限 AT-TW-19 所列） |

### 2.8 Stop 推回（`test_sessionctl_converge.py::StopVerdictTest`＋`test_sessionctl_hooks.py::HookConvergeTest`）

縫：tmp 逐字稿、`env` mapping（`AUTOSDD_HANDOFF_DIR` 指 tmp）、`AUTOSDD_TRACE_DIR` 指 tmp、payload `background_tasks`／`stop_hook_active`。

| AT | 前置 | 動作 | 預期 | 為何會紅 |
|---|---|---|---|---|
| AT-TW-70 | 已出聲；ctx=300,000；無背景代理；無已 finalize 包 | `stop_verdict`；hook 層餵 Stop payload | 回非空 reason，含 `收斂閘（Stop）`、`300,000`、`handoff --finalize`、`--spawn`、`/compact`、`只推回這一次`；痕跡一列 `converge_stop_block`；hook 層 rc 0 且 stdout JSON `decision=="block"` | 事故形態的唯一介入點；沒有這條，G2 對「掛背景輪詢後結束回合」零作用 |
| AT-TW-71 | 同上但 `stop_hook_active` 為真 | 同 | `""`／hook 層無輸出、不寫痕跡 | 迴圈煞車；少了它會把主控困在每次 Stop 都被推回的無限迴圈 |
| AT-TW-72 | 同 AT-TW-70 但 `background_tasks` 含執行中 `subagent` | 同 | `""`；hook 層只出 `systemMessage`、無 `decision`。同表另驗：只有 `shell` 仍推回、`completed` 的代理不算、payload 缺欄時讀檔名冊（最近有記錄＝執行中）也不推回（AT-TW-72b） | 等代理交卷是出口 ① 的第一步，推回它會逼主控丟下仍在跑的工作；背景 shell 不是代理（任務書明文） |
| AT-TW-73 | 同 AT-TW-70，但 handoff 目錄有本 sid 已 finalize 的 live 包 | 同 | `""`。對照：只有骨架（含 `TODO:`）的包 ⇒ 仍推回且 reason 指向該包路徑；他 sid 的包不算 | 已把交接包做完就是收斂完成，不可再推；骨架不算做完 |
| AT-TW-74 | 同 AT-TW-70，分別設 `AUTOSDD_UNATTENDED`／`SESSION_SWITCH_MODE=notify`／`off` | 同 | 皆 `""` | 無人窗口換 session 由 planner FRESH 路負責；notify／off 是逃生口 |
| AT-TW-75 | 未出聲且 ctx=400,000；已出聲且 ctx=289,999；已出聲且 ctx=290,000 | 同 | 前兩者 `""`、後者非空（邊界 `>=`） | 出聲在先；邊界與 G2 一致 |
| AT-TW-76 | 逐字稿缺／無 `transcript_path`／非 dict payload | 同 | `""`，不拋 | fail-open |
| AT-TW-77 | 先推回（ctx=300,000）；逐字稿尾端追加 ctx=100,000 的新回合 | 同一 payload 再判 | 第二次 `""` | 不寫閂鎖，`/compact` 之後自動解除 |
| AT-TW-78 | 同一 Stop payload（含 `last_assistant_message`＝「這件事待掌舵者決定。」）依序餵 `sessionctl_guard.py` 與 `check_pending_handoff.py`（子行程） | 同 | 第一次兩者皆 `decision:block`；`stop_hook_active` 為真時兩者皆無輸出 | 疊加最壞兩個額外回合、不死鎖：兩支各自「每回合至多推一次」，且都吃 CC 給的同一個迴圈煞車旗標 |
| AT-TW-79 | 本 sid 有已 finalize 的 live 包；ctx 在硬門檻之下、未出聲；`background_tasks` 含執行中的 `shell`（另驗執行中的 `subagent`） | `stop_verdict` | 非空 reason，含 `冷叫醒閘`、`TaskStop`、任務數、`只推回這一次`；痕跡一列 `finalized_wake_block` | DEF-200-588 事故形態：交棒後留著的背景任務結束時把舊 session 冷叫醒、整份重寫；放行這條＝交棒後的 session 還會自己燒額度 |
| AT-TW-80 | 同上，逐一換成：任務已結束／空陣列／payload 無該欄／無 finalize 包／只有他 sid 的包／`stop_hook_active`／無人／`off` | 同 | 皆 `""` | 假紅面：沒交棒時掛著等 CI 是正當用法；無欄位不猜 |
| AT-TW-81 | 已出聲、ctx=300,000、`background_tasks` 只有執行中的 `shell` | hook 層餵 Stop payload | stdout JSON `decision=="block"` | 出聲不得蓋掉推回：原接線先出聲就返回，判準層的推回在掛著背景 shell 時永遠到不了 |


### 2.9 AT 實作狀態對照（2026-11-15 收尾；單檔 `discover` 實跑）

| AT | 落點 | 狀態 |
|---|---|---|
| AT-TW-01～18 | `test_sessionctl_cachegate.py`（20 條） | 綠 |
| AT-TW-19 | `test_sessionctl_hooks.py`、`test_sessionctl_roster.py`（AT-SC-61 改寫：熱續放行不出聲、冷續阻斷） | 綠 |
| AT-TW-20～32 | `test_sessionctl_converge.py`（26 條，含 Stop 與 `is_advised`）、`test_sessionctl_switch.py` | 綠 |
| AT-TW-33／34／37／38／70～72／78 | `test_sessionctl_hooks.py` hook 層與註冊面 | **hook 與 settings 套用前預期紅**；以套用後鏡像根（`SESSIONCTL_APPLIED_ROOT`）驗過綠 |
| AT-TW-39 | `test_check_hooks_liveness.py` 註冊下限表四工具 | settings 套用前預期紅 |
| AT-TW-40～46 | `test_pre_push_dispatcher.py`（43 條）、`test_root_infra_parity.py` | 綠 |
| AT-TW-50～59 | `test_waste_census_metrics.py`（10 條） | 綠 |
| AT-TW-60 | `.env.example` 生成物鎖與每鍵有讀取點鎖 | 綠（收尾重生 `.env.example`） |
| AT-TW-61 | 根 `CLAUDE.md` sessionctl 列射程文字 | 綠（hook 套用後版面） |
| AT-TW-62 | `test_root_module_layout.py` 登記面 | 綠 |
| AT-TW-63 | 既有 `test_sessionctl_*` | 綠 |
| AT-TW-73～77 | `test_sessionctl_converge.py::StopVerdictTest` | 綠 |
| AT-TW-79～81（DEF-200-588） | `test_sessionctl_converge.py::StopVerdictTest` 的兩條 `test_def_200_588_*`；`test_sessionctl_hooks.py::HookConvergeTest::test_def_200_588_a_background_shell_never_masks_the_stop_pushback` | 綠 |

真機驗證 V-G1、V-G2、V-P1、V-C2、V-T1～V-T3 全數待主控；`long-runner` 只有 staged 檔、不接線、無 repo 測試。

## 3. 真機驗證（主控親跑；不得由開發棒代驗；結果寫進缺陷帳本列）

| V | 步驟 | 通過判準 | 對應 |
|---|---|---|---|
| V-G1 | 派一支 sonnet 代理做小事並交卷；等 >5 分鐘；對它 `SendMessage`（上下文先以門檻覆寫 `AUTOSDD_RESUME_AGENT_TOKENS=1` 壓低以免真造 15 萬上下文） | 被擋、訊息含「改派新代理＋短任務書」；加 `續棒理由：<≥8 字>` 後放行；trace 檔 `autosdd_session_switch.jsonl` 新增 `resume_gate_block`、`resume_gate_override` 各一行；交卷 1 分鐘內再續一次不被擋 | AT-TW-09～12、35、36 |
| V-G2 | 在已出聲（`~/.autosdd/handoff/<sid>.advised` 存在）的 session，以 `AUTOSDD_SWITCH_HARD_CTX_TOKENS=1` 壓低門檻，派 `Agent` | 被擋；`Read`／`PowerShell` 照常；`/compact` 後（或把覆寫移除）同一 `Agent` 呼叫放行；trace 有 `converge_block`。🔴 同場驗：`/compact` 之後第一個 PreToolUse 讀到的上下文是新值而非壓縮前的舊值（若是舊值，AT-TW-30 的「新回合才解除」在真機延遲一回合，需補讀 `compact_boundary`） | AT-TW-20、30、33 |
| V-P1 | 在一個拋棄式分支故意留一個 `ruff` 錯誤（`tools/` 下一行 `import os` 未用），同時改 `AutoClaude/` 一檔，`git push --dry-run` 之外的真推送用本機 bare remote | 快層秒級擋下；輸出無任何 leg 啟動字樣；修掉後同一推送進慢層 | AT-TW-40、41 |
| V-T1 | **條件項**：long-runner 定義檔（.claude/agents/ 下，尚未進 repo） 套用後，派一支 `subagent_type: long-runner` 的小任務，讀其 `agent-*.jsonl` | 任一筆 usage `cache_creation.ephemeral_1h_input_tokens > 0`；`message.model` 為 sonnet 家族 | G3 |
| V-T2 | 同代理：看其首則 user 記錄 | 含根 `CLAUDE.md` 內容（system-reminder 形式）；不含 ⇒ 本文補「先讀根 CLAUDE.md」並重驗，仍不含 ⇒ G3 撤回 | G3 |
| V-T3 | 讓它前景等待 6～10 分鐘後再呼叫一次工具 | 該回合 `cache_read_input_tokens` ≥ 前回合上下文的 90% | G3 |
| V-C2 | 在已出聲（`~/.autosdd/handoff/<sid>.advised` 存在）的 session，以 `AUTOSDD_SWITCH_HARD_CTX_TOKENS=1` 壓低門檻、無背景代理，直接結束回合 | 被推回一次（畫面出現收斂閘 reason）；補寫交接包主控層後 `--finalize` 通過，再結束回合不再被推回；第二次 Stop 在沒補的情況下也放行；trace 有 `converge_stop_block`。🔴 同場驗：與 `check_pending_handoff` 同回合疊加時，掌舵者看到的是兩個推回合併成一個額外回合還是兩個（影響訊息措辭，不影響正確性） |

## 4. 條件項 G3：`long-runner`（撤回路徑與落地條件）

- **落地條件**：V-T1～V-T3 **全部**通過。V-T1 不過＝frontmatter `experimental.cacheTtl` 在此版本不生效（可能版本不足或訂閱制忽略）；V-T2 不過＝自訂型別拿不到根 CLAUDE.md，其紀律（Windows 單一載具、鐵律）會靜默缺席，風險高於收益；V-T3 不過＝1h 寫了但等待後沒讀到。任一不過 ⇒ 刪 staged 檔、ADR §2.14 決策 3 改寫為「已驗證不可行」、缺陷帳本列註記。
- **撤回路徑**：刪一個檔 long-runner 定義檔（.claude/agents/ 下，尚未進 repo）；無程式、無 hook、無設定依賴。探針 `m2c` 的 `agent_type` 分組欄對無此型別時回空，不報錯。
- **派工規則**（落地後由主控寫進根 CLAUDE.md〈派工模型〉一句）：任務書含「預期 >4 分鐘的指令」（根層全套、AutoClaude 全套、E2E、Docker 棧、CI 等待）的棒，`subagent_type: long-runner`，並照舊明寫 `model`；其餘不變。
- **回頭收緊的監看**：探針 `m2d`（long-runner 代理中零長等待者占比）> 0.5 ⇒ 派工規則過寬，收緊。
- **實作範圍**：Dev-1 只產 staged 檔（內容規格見 `DEV_BRIEF.md` §Dev-1 G3）；**不寫 repo 內測試**（真機驗證決定去留）。若落地，AT-TW-53／54 的 `long-runner` 分組樣本已涵蓋探針側。

## 5. C2：Stop 時推回（已升入第一期；正式規格見 §1 FR-TW-13、§2.8、§3 V-C2）

事故重放發現 G2 對事故序列零介入（19:21:07 出聲後到 22:12:38 之間沒有任何展開型呼叫；78 分鐘閒置是背景輪詢加結束回合），主控依裁決 O-1 採納 Stop 推回。判準與 G2 共用 `_gate`（出聲、門檻、模式、無人判準同一份）；`AUTOSDD_SESSIONCTL_GUARD_OFF` 同時關掉兩者。痕跡新增 `converge_stop_block`；浪費帳 `m3d` 暫不計此欄，要計時另加一欄 `converge_stop_blocked`（缺欄時照三欄計、不報錯）。

## 6. 守衛面暴露證據座標（准入：三取一；引非構造性資料）

| 編號 | 座標 | 類別 |
|---|---|---|
| E-1 | SA `waste_census.jsonl`（本機重跑：`python tools/probe/waste_census.py --since-days 14`）`kind=="rewrite"`、`axis=="子代理"`、`cause=="other_user"`、`prev_ctx>=150000` 共 141 件（`gap_s>=300` 者 140 件、重寫合計 68,205,932 tok）。兩筆座標：① sid `d4ed2654-9181-4df1-a6e6-2d712956e23b`、thread `agent-a7acf763b38462428`、ts `2026-11-12T11:31:18+08:00`、tier 5m、gap_s 4,457、重寫 849,635 tok；② sid `245e80aa-71c4-443b-b8fe-d59f87a9f0e8`、thread `agent-a9ed4ac127e9195af`、ts `2026-11-02T04:47:05+08:00`、tier 5m、gap_s 536、重寫 847,240 tok。另 ADR §2.13.0 E1（掌舵者真機回報） | 非構造性逐字稿＋掌舵者回報 |
| E-2 | 同 jsonl 第三筆：sid `d4ed2654-9181-4df1-a6e6-2d712956e23b`、thread `agent-a9395d4c65e49edb7`、ts `2026-11-11T22:58:45+08:00`、gap_s 10,630、重寫 828,812 tok | 非構造性逐字稿 |
| E-3 | 掌舵者真機回報：sid `680d8411-58ac-4adb-9e23-521f6a7bb557`（2026-11-14 22:2x）「剛剛因此又浪費了20%的 Token」。逐字稿座標：`voice_aftermath` 列（voice_ts `2026-11-14T19:21:09+08:00`、ctx_at_voice 255,403、turns_after 39、hours_after 3.7、rewrites_after 1、rewrite_tokens_after 262,204）；`incident_turn` 列 ts `2026-11-14T20:52:00+08:00`、ctx 294,287 | 掌舵者回報＋逐字稿 |
| E-4 | 任務書 §1〔親驗〕今天第一次推送被 `ruff check tools/ .claude/hooks/` 擋下；SA `push` 列 `outcome=="fail"` 11／96（失敗牆鐘合計約 100 分） | 非構造性逐字稿 |
| E-5 | SA／Architect `arch_q3`：子代理前景輪詢後重寫 47 件（例：sid `245e80aa-71c4-443b-b8fe-d59f87a9f0e8` 子代理連續 `Wait-Process`，上下文 73～78 萬）；SA M2c 基線 70 件 | 非構造性逐字稿 |
| E-6 | 事故本身（`gh run list --commit <短 SHA>` 永不成立、78 分鐘無人叫醒；DEF-200-586） | 掌舵者回報 |

## 7. Q-A1 收斂硬門檻取值（Q-A1＝主控已代決「用探針重放取值」）

**條件**：(a) 事故 sid `680d8411-…` 在 2026-11-14 20:52 的上下文會被擋；(b) 自 R1（250,000）起仍留有完成一個工作單元的空間。

**取值過程**（可重放；本棒腳本 `sd\hardctx_replay.py`、`sd\hardctx_dispatch_replay.py`，輸出 `hardctx_replay_out.txt`、`hardctx_dispatch_out.txt`，進 repo 後等價指令 `python tools/probe/waste_census.py --replay-hard-ctx --r1 250000`，見 AT-TW-56）：

1. 母體：近 14 天主控逐字稿 18 個 session（含子代理檔外的 22 個檔），其中曾達 R1 者 11 個。
2. 事故 20:52:00 之前最後上下文＝**293,672**（20:52:02 回合 294,287；與 Architect 引的 294,956 差在取樣回合）。條件 (a) ⇒ H ≤ 293,672。
3. 對候選 H 重放「從該 session 首次 ≥R1 的回合，走到首次 ≥H 的回合數」（＝收斂前的工作空間，單位回合）：

| H | 達 H 的 session | 空間中位（回合） | p25 | 事故 20:52 被擋 | 事故 session 自身首次達 H（距 R1 回合偏移／時刻） |
|---|---|---|---|---|---|
| 260,000 | 11 | 1 | 0 | 是 | 4／20:09 |
| 280,000 | 11 | 3 | 1 | 是 | 12／20:14 |
| **290,000** | 11 | 5 | 1 | **是（差 3,672）** | **19／20:31（距 R1 71 分）** |
| 294,000 | 11 | 7 | 1 | 否（差 −328） | 24／20:52:02 |
| 300,000 | 11 | 8 | 2 | 否 | 30／22:12 |
| 350,000 | 10 | 18 | 6 | 否 | — |
| 400,000 | 10 | 36 | 9 | 否 | — |

4. **取值：`AUTOSDD_SWITCH_HARD_CTX_TOKENS` 出廠 290,000**。理由：滿足 (a) 且為滿足 (a) 的**最大**整數千位值（294,000 起即漏掉事故），空間最大化；事故 session 自身在 R1 後 71 分、19 回合才碰到 290,000，對「完成一個工作單元」是充裕的。
5. **誠實揭露（不得略去）**：
   - 跨 session 空間中位只有 5 回合、p25 只有 1 回合：多數 session 本來就**從 ≥R1 的高上下文起跑**（續跑／壓縮後），不是事故 session 那種「出聲後才長大」。收斂閘在這些 session 一出聲就接近門檻。
   - **派工事件重放（`hardctx_dispatch_out.txt`）**：首次 ≥R1 後共 202 次展開型派工，H=290,000 時 174 次（86%）在 ≥H 的上下文發出；也就是說，**一旦出聲，絕大多數後續派工都會被擋**——這是設計意圖（出聲後只收斂），但也是守衛被關掉的最大風險，列 `OPEN.md` O-2。
   - 事故 session 在出聲後（19:21:07）到 22:12:38 之間**沒有任何展開型派工**，所以 G2 對事故本身不介入（見 §5）。
6. 方向鎖：出廠值只准下修；`HARD_CTX_KEY` 進 `switch._DOWNWARD_ONLY`；AT-TW-32 同時鎖「必須嚴格大於 R1 出廠值」。

## 8. 成功判準對照（任務書 §2）

| CR | 本 TCS 的處置 | 驗收 |
|---|---|---|
| CR1 事故重放時機制在 20:52 前或當下介入 | **達成（待真機）**：事故序列 20:52 之後第一個 Stop（ctx 294,287 ≥ 290,000、無背景代理、無已 finalize 包、非無人）命中 C2 推回；等待自己結束另靠 `ci_wait` | AT-TW-70～78、V-C2；`--incident-sid` 重放 |
| CR2 出聲後不可能再無感連續工作數小時 | G2 擋出聲後的展開型派工；C2 擋「結束回合後閒置在大上下文」；兩者合起來才覆蓋事故形態。仍有缺口（誠實揭露）：純讀、改、跑測試的連續小工作不被擋（O-1） | AT-TW-20～32、70～78、V-G2、V-C2 |
| CR3 派工預估與切斷接續成本有上界 | 預估閘延後（Architect §3.6）；接續成本由 FR-TW-01 封頂；G3 縮長等待重寫（條件項） | AT-TW-09～19；M3a、M2c |
| CR4 推送預檢涵蓋 pre-push 靜態閘 | FR-TW-08：快層先行 | AT-TW-40～46、V-P1；M4 |
| CR5 機制自身成本有量測值且遠小於省下 | 探針 M5（hook 呼叫耗時）＋M3d（阻斷／逃生次數）；hook 每次展開型呼叫多一次行程（SA 基線 hook 中位 51 ms）、零模型 token | AT-TW-55、57；`mech_cost` 列 |

## 9. 缺陷帳本列

DEF-200-587（`docs/06_quality/AutoSDD_Defect_Log.md`，fixed@R215 同 commit）涵蓋四件：續棒不看快取冷熱、出聲後無機械收斂（含 Stop 推回）、pre-push 快層在慢層之後、浪費帳無可重跑量測。G3 `long-runner` 為條件項，依 V-T1～V-T3 結案，不在本列。

## 10. 額度配速與快取保全（第一期：配速床＋趕工戳記＋量測；2026-11-15；設計全文＝ADR-XPLAT-004 §2.15）

> 來源任務書＝第二主題四方任務書（掌舵者原話 sid `eb1cb524-de09-4ad5-a068-69fa180dc64b` 2026-11-15 00:1x，全文見 ADR §2.15.0）；Architect 定稿＝`ARCH_PACE.md`；SA 數據＝`HB_SA.md`。缺陷帳本列＝DEF-200-589（草稿見 §10.9）。
> **狀態（2026-11-15）**：規格階段；實作尚未開始，AT 尚無測試；§10.6 真機驗證 V-P1～V-P5 與 §10.7 第二期前置 V-K1～V-K4、V-S1、V-M1、V-U1、V-C4 皆**待真機驗證**，未驗，不得寫成已驗。
> 測試注入縫沿用 §2 前言：`now`（aware datetime）、`AUTOSDD_TRACE_DIR` 指 tmp（戳記與痕跡落此）、`env` mapping、tmp 快取檔；**不讀本機真實 `~/.claude` 與 `~/.autosdd`、不起真排程、不起真 claude、不外呼網路**。

### 10.0 範圍

第一期做：D1 窗內配速床、D2 趕工戳記。**實作狀態回填（2026-11-15）：D5 量測補指標與 AC-7 回放（本章 §10.4 的 AT-QP-56～63、§10.6 的 V-P6）本期未做，改列後續期（未落地）；本章對應 AT 與 V 保留為後續期規格，不計入第一期驗收。**WHY：規格不得宣稱磁碟上不存在的元件；第一期已落地的另含為騰出 hub 餘裕自 `quota_gate` 抽出的 `tools/lib/quota_halt_marker.py`。**不做**：保溫致動（ADR §2.15.2 D4 只記決策與決策表，實作屬第二期）、模型降級阻斷、R1 下修、開場瘦身、statusline 取樣、牆前預先交接與 reset 自動開窗、C-5 冷時只給交接出口（皆列 ADR §2.15.5 分期表，本期不寫 AT）。DEF-200-588（冷叫醒閘）已另案完成，見 ADR §2.14.5，不在本章。

### 10.1 模組落點與所有權表（照 Root_Layout §2；全部在已登記的扁平額度守衛家族 `tools/lib/quota_*.py` 與 wastecensus 套件內，無新落點格）

| 元件 | 路徑 | 動作 | 持有者 |
|---|---|---|---|
| 配速床判準（純函式、零 I/O、Python 3.9 可載入） | `tools/lib/quota_pace_floor.py` | 新 | Dev（單人串行） |
| 趕工戳記讀寫、疊入、痕跡、`cli` | `tools/lib/quota_rush.py` | 新 | 同上 |
| halt 標記三函式（自 `quota_gate` 抽出，gate 單行 re-export；實作時新增） | `tools/lib/quota_halt_marker.py` | 新 | 同上 |
| 政策欄位與接線：`Policy` 三欄、`decide`／`axes_of` 的 `pace_floor` 參數、`Decision.pace`、`describe` 提示句、單調性判準 | `tools/lib/quota_policy.py`（現 301／400） | 改 | 同上 |
| `ENV_SPEC` 三鍵 | `tools/lib/quota_policy_env.py`（現 215／400） | 改 | 同上 |
| env 疊入一行、`draining()` 傳 `pace_floor=False`、gate 路徑落款一行、`pace_report` 一段 | `tools/lib/quota_gate.py`（**hub tier 500／500，餘裕 0**） | 改（淨行數 ≤0） | 同上；先抽出等量程式再接線 |
| `rush` 分派 | `tools/sessionctl.py`（薄殼） | 改 | 同上 |
| 配速指標與回放（**後續期，未落地**） | wastecensus 套件內的 `pace_metrics`、`pace_replay` 兩模組（尚無檔）；`report.py` 加旗標 | 後續期 | 同上 |
| 入口薄殼 | `tools/probe/waste_census.py` | 只分派新旗標 | 同上 |
| 測試（新） | `tools/tests/test_quota_pace_floor.py`、`tools/tests/test_quota_rush.py` | 新 | 同上 |
| 測試（既有檔增量） | `test_quota_policy.py`、`test_waste_census_metrics.py` | 改 | 同上 |
| 不動 | `quota_pace.py`（現 371／400；`resolve` 簽名與行為不改）、`.claude/**`（本期無 hook 與 settings 變更） | — | — |
| 文件連動 | 見 §10.8 | — | Closer |

並行紀律（根 CLAUDE.md 鐵律七）：以上全是同一條判準的常數／判準／消費端，**不得切給並行包**；一棒做完、主控親驗後才派下一棒。

### 10.2 介面契約（以真實函式簽名為準；以下為新增或改動部分）

**常數與政策欄位**

| 名稱 | 住處 | 出廠值／格式 | 方向鎖 |
|---|---|---|---|
| `Policy.pace_burst_pp` ／ `AUTOSDD_QUOTA_PACE_BURST_PP` | `quota_policy.Policy`／`ENV_SPEC` | `20.0`，`float`，`lo=0.0`、`hi=20.0` | 只准下修：大於出廠值＝越界＝該鍵退預設＋進 `problems`（`_parse_env_number` 現行語意：**單鍵退預設，不是整組**） |
| `Policy.pace_step_pp` ／ `AUTOSDD_QUOTA_PACE_STEP_PP` | 同上 | `10.0`，`float`，`lo=1.0`、`hi=10.0` | 同上 |
| `Policy.pace_rush_until` ／ `AUTOSDD_QUOTA_PACE_RUSH_UNTIL` | 同上 | 預設 `None`（範例檔留空）；`float`，`lo=0.0`、`hi=None`；值＝epoch 秒 | 有效判準在 `decide`：`0 < until − now ≤ RUSH_MAX_SECONDS`；其餘一律當未趕工（較緊方向） |
| `RUSH_MAX_SECONDS` | `quota_pace_floor` | `18000.0`（5 小時）；`quota_rush.issue` 的 `hours` 上限由它導出 | 只准下修 |
| `NOTE_PACE` | `quota_pace_floor` | `"pace-floor"`（併入逐軸 note 與 `Decision.reason`） | — |
| 無環境變數形態的總開關 | — | **刻意不提供**（床的逃生口只有趕工戳記；burst 只能往 0 調） | — |

`policy_monotonicity_problems(p)` 新增：`pace_burst_pp < 0` 或 `pace_step_pp <= 0` ⇒ 一條以 `[方向]` 起首的 problem。

**`tools/lib/quota_pace_floor.py`**

```
class PaceFloor(NamedTuple):
    kind: str; pct: float; minutes: float | None; window: float | None
    allowed_pp: float | None   # 100×elapsed + burst；算不出為 None
    over_pp: float | None      # pct − allowed_pp
    level: float | None        # 餵入水位下限；無則 None
    state: str                 # "lifted" | "within" | "exempt-rush" | "exempt-weekly-reset"
                               # | "exempt-hold" | "unknown" | "n/a"

def pace_floor(pct, minutes, window, burst, step, converge, prepare, halt) -> float | None
    # lead = quota_pace.lead_pp(pct, minutes, window)；None ⇒ None
    # over = lead − burst；over <= 0 ⇒ None
    # level = prepare if over > step else converge；回 min(level, halt − 1.0)

def rush_active(policy, now) -> bool
    # policy.pace_rush_until 非 None 且 0 < until − now.timestamp() <= RUSH_MAX_SECONDS

def evaluate(rows, deltas, policy, now, *, skip=(), hold=()) -> tuple[PaceFloor, ...]
    # rows＝quota_policy._rows(state) 形狀 [(kind, pct, resets_at, pct_note)]；deltas＝[(帶號分鐘|None, note)]
    # 與 rows 同序；最短窗軸（quota_pace.mask_windows(quota_pace.windows(...), skip) 之窗長最小者）
    # 逐軸判：趕工 ⇒ "exempt-rush"；lead 為 None ⇒ "unknown"；hold 為真 ⇒ "exempt-hold"；
    # 存在更長窗軸且其分鐘數 0<=m<本軸剩餘分鐘（嚴格小於）⇒ "exempt-weekly-reset"；
    # pace_floor 回 None ⇒ "within"；否則 "lifted"。其餘軸 "n/a"。
    # converge／prepare／halt／burst／step 一律取自傳入的 policy（恆有值，無「錨點缺席」分支）；
    # 畸形輸入（pct 非數、resets_at 非字串）不拋，該軸 "unknown"。

def apply(resolved, floors) -> tuple
    # resolved＝quota_pace.resolve 的 [(feed, horizon, minutes, note)]；回同形狀；
    # state=="lifted" 的軸 feed = max(feed, level)；僅當 level > feed 時 note 以 "+" 併入 NOTE_PACE

def line(floors) -> str
    # 每個最短窗軸一行（兩空格縮排、換行結尾）；無最短窗軸 ⇒ ""；全文不得出現 "%"，一律 pp；每行帶 "kind=<k>" 與整數剩餘分鐘
```

**接線契約（`quota_policy`）**

- `axes_of(state, now, p, ratio=None, ratio_note="", active_model=None, relax=None, pace_floor=True)`：`resolve()` 之後，`pace_floor` 為真時 `resolved = quota_pace_floor.apply(resolved, evaluate(_rows(state), deltas, p, now, skip=_amort_skip(state, active_model), hold=(relax[1] if relax else ())))`；為假時**不呼叫** evaluate／apply（逐位元等於改前）。
- `decide(state, now, p, ratio=None, ratio_note="", active_model=None, burndown=None, pace_floor=True)`：透傳；`Decision` 新增欄位 `pace: object = ()`（`PaceFloor` 的 tuple，同 `amort` 先例；`pace_floor=False` 時為 `()`）。`pace_contract.write` 不序列化它。
- `describe(decision)`：reason 含 `pace-floor` 時尾端附一句出口：`（配速床：如需趕工 python tools/sessionctl.py rush --hours <H> --why <WHY>）`；不含時不附；全文不得新增孤立 `%`。
- `quota_gate.policy_env(root=None)`：回傳前經 `quota_rush.overlay`（見下）；`quota_gate.draining()` 以 `pace_floor=False` 呼叫 `decide`；`pace_report` 把 `quota_pace_floor.line(decision.pace)` 併入輸出（位置在攤提行之後）；`quota_gate()` 路徑在 `if decision.cap is None or event != "PreToolUse": return 0` 之後呼叫 `quota_rush.log_floor(decision, now)`。

**`tools/lib/quota_rush.py`**

```
SCHEMA = "autosdd.quota_rush/1";  STAMP_NAME = "quota_rush.json"
EVENTS_NAME = "autosdd_pace_floor.jsonl";  RUSH_KEY = "AUTOSDD_QUOTA_PACE_RUSH_UNTIL"
MIN_WHY_CHARS = 8;  UNATTENDED_ENV = "AUTOSDD_UNATTENDED"

def stamp_path() -> Path                      # endurance_env.trace_dir() / STAMP_NAME
def read_stamp(path=None) -> dict | None      # fail-closed：缺檔／壞 JSON／schema 不符／缺欄／型別錯／until 或 issued_at 為 naive／
                                              # until_epoch 與 until 不一致／until − issued_at > RUSH_MAX_SECONDS + 1 ⇒ None
def active(now=None, env=None, path=None) -> dict | None
    # env 有 UNATTENDED_ENV ⇒ None；read_stamp 有效且 0 < until − now ≤ RUSH_MAX_SECONDS ⇒ 該 dict 加 "left_minutes"
def overlay(env, now=None, path=None) -> dict
    # 回 dict(env) 的複本（不改原 mapping）；RUSH_KEY 缺席／空白／數值 <=0 且 active(...) 成立 ⇒ 設 RUSH_KEY=str(until_epoch)；
    # 已有正值不覆蓋；任何例外吞掉並回無疊入的複本
def issue(hours, why, sid="", now=None, env=None, path=None) -> tuple[int, str]
    # rc 0 寫入（覆寫舊戳記＝延長）並落 pace_rush_on；rc 2 拒絕（無人窗口／hours 不是 0<H<=5 的有限數／why 去頭尾空白（含全形）後 <8 字）不寫檔；rc 1 檔案系統錯誤
def revoke(now=None, path=None) -> tuple[int, str]    # 有檔：刪除＋落 pace_rush_off，rc 0；無檔：rc 0、訊息「無趕工戳記」、不落事件
def status_text(now=None, env=None, path=None) -> str
def log_event(event, path=None, **fields) -> bool
def log_floor(decision, now, path=None) -> bool       # decision.pace 內有 state=="lifted" ⇒ 追加一列 pace_floor；否則不寫；寫不進去回 False 不拋
def cli(argv) -> int
```

戳記檔（`endurance_env.trace_dir()/quota_rush.json`）：`{"schema":"autosdd.quota_rush/1","issued_at":"<ISO 帶 offset>","until":"<ISO 帶 offset>","until_epoch":<float>,"hours":<float>,"why":"<str>","sid":"<str，預設取 CLAUDE_CODE_SESSION_ID>"}`。痕跡檔（同目錄 `autosdd_pace_floor.jsonl`，單行 JSON、`ensure_ascii=False`、`\n` 結尾）事件：`pace_rush_on`（`at`、`until`、`hours`、`why`、`sid`）、`pace_rush_off`（`at`、`reason:"revoked"`）、`pace_floor`（`at`、`kind`、`pct`、`minutes`、`allowed_pp`、`level`、`cap`、`band`）。只用 `Path.write_text`／`open(...,"a")`／`unlink`，不引入 `os.replace`／`rename`（Windows 檔案鎖原語鎖）。

**命令列 `python tools/sessionctl.py rush`（分派到 `quota_rush.cli`）**

| 形式 | 行為 | rc |
|---|---|---|
| `rush --hours <H> --why "<WHY>" [--sid <SID>]` | 發戳記；成功輸出到期時刻與剩餘分鐘 | 0 成功；2 拒絕（見 `issue`）；1 檔案系統錯誤 |
| `rush --off` | 撤銷 | 0 |
| `rush --status` | 輸出有效／已過期／無戳記與 why | 0（無戳記也是 0） |
| 無旗標、`--hours` 缺 `--why`、`--off` 與 `--hours` 並用、未知旗標 | 用法錯誤（與 `sessionctl.py` 既有 `_USAGE_RC` 同值） | 3 |

`tools/sessionctl.py` 的用法錯誤訊息與檔頭用法說明加入 `rush`。

**`--pace` 新行文字契約**（逐字措辭由開發棒定，AT 只釘關鍵片段）：最短窗軸一行以 `配速床：` 起首、含 `kind=<軸名>`、整數剩餘分鐘、`pp`；各 state 的必含片段——`lifted`：`允許線`、`超線`、`水位至少抬到`；`within`：`未超線`；`exempt-rush`：`趕工戳記`；`exempt-weekly-reset`：`先 reset`；`exempt-hold`：`清倉`；`unknown`：`不明`。

### 10.3 需求（FR）

| FR | 內容 | 對應 | 暴露證據 |
|---|---|---|---|
| FR-QP-01 | 最短窗軸超出允許線 ⇒ 餵入水位至少抬到 converge（`over≤S`）或 prepare（`over>S`），上界 `halt−1`；永不調低 | ADR D1；AC-1、AC-3 | E-P1～E-P3 |
| FR-QP-02 | 窗尾（允許線 ≥100）與長窗先翻頁、窗長／距離不明、清倉 hold 時不抬 | AC-2、AC-5 | 同上 |
| FR-QP-03 | 趕工戳記有效 ⇒ `decide` 輸出與無本功能逐位元相同；過期、超過 5 小時、無人窗口、結構錯誤一律當無戳記（較緊方向） | AC-4 | 同上 |
| FR-QP-04 | `sessionctl rush` 寫／撤／查；`hours` 上限 5、`why` ≥8 字、無人窗口拒絕 | AC-4 | 同上 |
| FR-QP-05 | 三個新鍵進 `ENV_SPEC`，burst／step 只准下修；`.env.example` 為生成物 | AC-6 | 同上 |
| FR-QP-06 | 所有走 `policy_env()` 的消費端看到同一個 cap；`draining()` 不吃床 | ADR D2、§2.15.3 | 同上 |
| FR-QP-07 | `--pace` 說出床的狀態；床造成的阻斷訊息附趕工出口 | AC-8 | 同上 |
| FR-QP-08 | 補量測 M-P1／P3／P4／P7、M-C1 與 AC-7 回放；零 token、不接閘門 rc | ADR D5 | 同上 |

### 10.4 驗收測試（AT；AT-QP-56～63 為後續期，第一期未落地）

縫：`NOW`＝`now`（aware）；`TRACE`＝`AUTOSDD_TRACE_DIR` 指 tmp；`ENV`＝`env` mapping；`CACHE`＝tmp 額度快取（`quota_gate.read_quota` 讀的那份）；`FS`＝tmp 合成逐字稿／落款／halt 標記。預設政策＝burst 20、step 10、converge 70、prepare 85、halt 95；窗長 300 分；「X 分」＝剩餘分鐘。預期 cap 以現行 `quota_policy._cap_for` 為準（converge×far＝2、prepare×far＝1，SD 已以真實函式核對）。

#### 10.4.1 `pace_floor()` 純函式（`test_quota_pace_floor.py::PaceFloorFnTest`）

| AT | 前置 | 動作 | 預期 | 為何會紅（意圖） |
|---|---|---|---|---|
| AT-QP-01 | 三個實測點：(38, 247)、(43, 244)、(48, 230)，窗 300 | `pace_floor` | 皆回 `70.0` | 三個真實事故點（ADR §2.15.0）；少算 burst 或把允許線算錯，三點之一會偏離 |
| AT-QP-02 | 邊界 over＝0：(50, 210)；over＝+1：(51, 210) | 同 | 前者 `None`、後者 `70.0` | `over <= 0` 寫成 `< 0` 會把「剛好在線上」也煞車，床變成嚴格線性 |
| AT-QP-03 | 邊界 over＝S：(60, 210)；over＝S+1：(61, 210) | 同 | 前者 `70.0`、後者 `85.0` | `over > S` 寫成 `>= S` 會讓邊界點越級進 prepare，觸發任務書落盤副作用 |
| AT-QP-04 | 窗尾：(99, 30)；並掃 minutes∈{0,5,…,60}×pct∈{0,…,100} | 同 | 全部 `None` | AC-2：窗尾 use-it-or-lose-it 不得被床破壞（B＝20 時第 240 分起允許線 ≥100） |
| AT-QP-05 | minutes 為 `None`／負數；window 為 `None`／0 | 同 | 皆 `None` | 期程不明不得抬水位（同 `lead_pp` 前置；抬了就是無證據的新煞車） |
| AT-QP-06 | `prepare=96`、`halt=95`（病態政策）；(61, 210) | 同 | 回 `94.0`（`halt−1`） | 推導值永不觸發 halt（halt 只由伺服器真實水位開火）；去掉夾層即回 96 |
| AT-QP-07 | pct 0～100（步長 1）×minutes 0～300（步長 5） | 掃描 | 結果∈{`None`}∪[converge, halt−1]；固定 minutes 時 pct 增加結果不遞減；固定 pct 時剩餘分鐘減少（時間流逝）結果不遞增 | AC-3 的網格性質；任何符號寫反或單位寫錯會在某一格破單調 |
| AT-QP-08 | 同網格；burst 20→10→0、step 10→5→1 逐步調小 | 同 | 每格結果「不更鬆」（`None` 視為 −∞；level 只增不減） | 方向鎖：調小一定更緊，調大才是放寬；方向反了＝可調旋鈕成了放寬後門 |
| AT-QP-09 | window＝600、minutes＝540、pct＝35；對照 window＝300、minutes＝270、pct＝35 | 同 | 兩者結果相同（皆 `70.0`） | 窗長歸一化；若寫死 300，非五小時窗軸（如日窗）會錯 |
| AT-QP-10 | 資料自相矛盾：minutes＝400 > window＝300，pct＝25 | 同 | `70.0`（lead＝pct＝25、over＝5） | 與 `lead_pp` 夾 0 的保守側一致；用負 elapsed 計算會得到放寬的錯誤答案 |
| AT-QP-11 | 以 `AUTOSDD_QUOTA_PACE_BURST_PP=0`、`AUTOSDD_*` 全清兩種 `os.environ` 各呼叫一次 | 同 | 結果相同 | 純函式不讀環境、不讀時鐘；環境只能經 `Policy` 進場 |

#### 10.4.2 `evaluate()`／`apply()`（`test_quota_pace_floor.py::EvaluateApplyTest`；夾具 `_rows`、`_deltas`、預設 `Policy`，resolved 由 `quota_pace.resolve` 現算）

| AT | 前置 | 動作 | 預期 | 為何會紅 |
|---|---|---|---|---|
| AT-QP-12 | five_hour 38@247、session 同 reset、weekly_all 60@8000 | `evaluate`＋`apply` | five_hour／session 的 state＝`lifted`、level＝70；apply 後兩軸 feed＝70.0、note 含 `pace-floor`；weekly_all feed 不變 | AC-1 的軸級形態；少了 `max` 或套錯軸會立刻現形 |
| AT-QP-13 | 同 AT-QP-12，`Policy.pace_rush_until`＝now＋1 小時 | 同 | 兩軸 state＝`exempt-rush`；`apply` 輸出與 `resolve` 原值逐位元相等（tuple 相等） | AC-4 免套用①；若趕工只「壓低」不「還原」，輸出會差一格 |
| AT-QP-14 | weekly_all 的 reset 為 100 分（<247）；對照 247 分（相等）與 248 分 | 同 | 100 分：five_hour state＝`exempt-weekly-reset`、feed 不變；247／248 分：`lifted` | AC-5 與嚴格小於的邊界；寫成 `<=` 會讓「週軸剛好同時結束」也免套用 |
| AT-QP-15 | five_hour 的 resets_at 為 `None`／非字串；pct 為 `"x"` | 同 | state＝`unknown`、不拋、feed 不變 | 免套用③＋畸形輸入 fail-open；拋例外會讓整條 gate 變故障源 |
| AT-QP-16 | `hold` 遮罩對 five_hour 為真 | 同 | state＝`exempt-hold`、feed 不變 | 免套用④：床不得與清倉授權相抗；少了它床會把使用者明示要用盡的額度又擋回去 |
| AT-QP-17 | weekly_all 90@8000（極度超前）、seven_day 同；five_hour 在允許線內 | 同 | weekly_all／seven_day state＝`n/a`、feed 不變；five_hour state＝`within` | 只作用最短窗軸（X24）；套到週軸會與週用滿目標直接衝突 |
| AT-QP-18 | weekly_scoped 為別家模型（`skip` 遮罩為真）且其 reset 為 100 分 | 同 | **不**構成免②（five_hour 仍 `lifted`） | 遮罩軸不得影響本模型的床（與攤提同尺，DEF-200-438 的同型） |
| AT-QP-19 | session 與 five_hour 同 reset、水位不同（40 與 60，剩 200 分） | 同 | 兩軸各以自己的水位算：level 各自為 70 與 85、皆 `lifted` | 同窗長的多軸要逐軸算；只算第一軸會漏另一軸 |
| AT-QP-20 | 攤提已把 five_hour 的 feed 抬到 90（以 ratio 構造）；床 level＝70 | 同 | apply 後 feed 仍 90、note **不含** `pace-floor` | `max` 不是覆寫：覆寫會把更高的攤提水位壓回 70，變成放寬 |
| AT-QP-21 | five_hour 90@230（已在 prepare 帶上方，level＝85） | 同 | state＝`lifted` 但 feed 仍 90、note 不含 `pace-floor` | note 只在「真的抬了」時出現；否則 M-P4 的「床擋過」近似會被稀釋 |

#### 10.4.3 說明行（`test_quota_pace_floor.py::LineTest`）

| AT | 前置 | 動作 | 預期 | 為何會紅 |
|---|---|---|---|---|
| AT-QP-22 | 六種 state 各造一組 floors | `line` | 各行含 §10.2 該 state 的必含片段、`kind=<軸名>`、整數分鐘、`pp`；全文**無** `%` 字元 | AC-8／M7：畫面必須一行內回答「為什麼空著也不能衝」與「為什麼這次放行」 |
| AT-QP-23 | 全為 `n/a`（無最短窗軸）或空 tuple | 同 | 回 `""` | 沒有最短窗軸時不得印一句空話（本 repo 判例：訊息混一句假話比少一欄更難看見） |
| AT-QP-24 | session＋five_hour 兩個最短窗軸 | 同 | 兩行，各帶自己的 kind | 逐軸說明；合併成一行會把不同水位說成同一個數 |

#### 10.4.4 決策、政策、env、gate（`test_quota_policy.py` 增量：`PaceFloorDecideTest`、`PaceFloorPolicyTest`；縫 NOW、CACHE、TRACE）

| AT | 前置 | 動作 | 預期 | 為何會紅 |
|---|---|---|---|---|
| AT-QP-25 | AC-1：five_hour 38@247＋session 同＋weekly_all 71@8467＋weekly_scoped(Fable) 78@8467；`active_model="fable"` | `decide` | five_hour 的 per_axis 讀數 band＝`converge`、horizon＝`far`、cap＝2；reason 含 `pace-floor`；`Decision.pace` 含 `lifted`。對照 `decide(pace_floor=False)`：five_hour 讀數 band＝`free`、cap＝`None`（整體 `Decision.cap` 因 weekly_scoped 78 本來就 ≤2，不具鑑別力；鑑別看 five_hour 的逐軸讀數） | 事故實測點；對照組證明差異來自床而非其他軸（證據 3 的 `cap=None` 就是對照組現狀） |
| AT-QP-26 | 08:56 點（43@244）與 70 分鐘點（48@230） | 同 | band＝`converge`、cap＝2 | 另外兩個真實點，防止只對單點調參 |
| AT-QP-27 | 61@210 | 同 | band＝`prepare`、cap＝1 | S 的分級要真的進致動器，不只停在函式層 |
| AT-QP-28 | AC-2：80@40（已過 86.7%） | `decide` 與 `decide(pace_floor=False)` | 兩者 cap、recommended_fanout、band、binding.kind、per_axis 全欄、reason **逐欄相等**，reason 不含 `pace-floor` | use-it-or-lose-it 在 `decide` 層同樣成立 |
| AT-QP-29 | AC-5：weekly_all 的 reset 為 100 分、five_hour 38@247 | 同 | 同 AT-QP-28 的逐欄相等 | 免套用②在整合層成立；軸級對、整合層漏接線是本 repo 反覆記載的失敗型 |
| AT-QP-30 | AC-4：`Policy.pace_rush_until`＝now＋3600 | `decide` 與 `decide(pace_floor=False)` | 逐欄相等（含 reason、per_axis 的 note、`Decision.pace`＝`()` 或全為 `exempt-rush`） | 「與無本功能逐位元相同」的直接斷言 |
| AT-QP-31 | 趕工邊界：until＝now＋18000 秒（有效）；＋18001 秒（超上限）；now（恰好到期）；now−1（已過期） | 同 | 有效者＝趕工（逐欄同 `pace_floor=False`）；其餘三者床照常套用 | 上限與到期都是嚴格不等式；`<=`／`<` 寫錯一格就讓 6 小時戳記或剛到期的戳記仍然生效 |
| AT-QP-32 | 確定性網格：pct∈{0,10,…,100}×minutes∈{0,30,…,300}×weekly 狀態三種（低／在 converge 上方／同時 reset） | `decide` 對 `decide(pace_floor=False)` | 每格：cap（`None`＝∞）不大於無床 cap；recommended_fanout 不大於；band 序不低於 | AC-3「餵入≥原值、永不放寬」的整合層網格；任何一格變鬆即紅 |
| AT-QP-33 | `GOLDEN_LEGACY`：12 個 state 的 `(cap, recommended_fanout, band, binding.kind)` 字面表，**Developer 動工前（step 0）從未改版程式擷取** | `decide(pace_floor=False)` | 逐一相等 | 證明關閉路徑＝改前行為；沒有凍結的外部基準，「與自己比」永遠綠 |
| AT-QP-34 | `Policy()` 預設；`replace` 出 burst＝−1、step＝0、step＝−5 | `policy_monotonicity_problems` | 預設空；三種病態各自非空且含 `[方向]` | 單調判準管「值與值之間的關係」，`ENV_SPEC` 的 lo／hi 管不到（既有判詞） |
| AT-QP-35 | AC-6：`AUTOSDD_QUOTA_PACE_BURST_PP` 為 `"25"`、`"15"`、`"-1"`；`..._STEP_PP` 為 `"11"`、`"0.5"`、`"0"`；`..._RUSH_UNTIL` 為 `"abc"`、`"1e12"`；並同帶 `AUTOSDD_QUOTA_CONVERGE_PCT="65"` | `load_policy` | `"25"`→ problems 含鍵名與「高於上界 20.0」、值 20.0；`"15"`→ 15.0 無 problems；`"-1"`、`"11"`、`"0.5"`、`"0"`→ 各自 problems 且退預設；`"abc"`→ problems、`None`；`"1e12"`→ 解析成功（`decide` 層忽略）；CONVERGE＝65 仍生效（單鍵退預設，不連坐） | 只准下修由 `hi` 鎖住；放寬＝可調旋鈕變後門；單鍵語意與 Architect 稿「整組退預設」不同，以程式為準，此條釘現況 |
| AT-QP-36 | 既有 `.env.example` 生成物鎖與「ENV_SPEC 每鍵有讀取點」鎖 | 跑既有＋新斷言 | 三鍵出現於 `render_env_example()`；`env_example_problems(磁碟檔)`＝`[]`；`RUSH_UNTIL` 範例行為空值（不是 `0`） | 生成物不同步＝使用者抄範例得到錯誤預設；範例值 `0` 會讓 `overlay` 的「空白或 ≤0 才覆蓋」判準失去意義 |
| AT-QP-37 | CACHE：five_hour 55@240（已過 60 分、允許線 40、over＝15＞S ⇒ 床會抬到 prepare）；其餘軸低 | `quota_gate.draining()`；`compact_margin_breached` | `draining()`＝`"no"`（55＋3＜85、band 以無床計為 notice）；同狀態 `decide()` 預設 band＝`prepare`（證明床確實會讓 `band ∈ DRAINING_BANDS`） | `draining` 若吃床，水位 55 就被判「不得壓縮」，與 context 守衛要求壓縮相衝（ADR §2.15.3）；用 45@240 這種只抬到 converge 的點測不出差別 |
| AT-QP-38 | AC-8：CACHE 同 AT-QP-25、注入 `now` | `quota_gate.pace_report` | 輸出含 `配速床：`、`kind=five_hour`、整數剩餘分鐘、`pp`；既有 M7 判準（每個 `%` 皆帶 kind 與分鐘）對全文綠；未超線的情境印 `within` 說明行 | `--pace` 是派工前的詢問口；不說床就看不出為何被擋 |
| AT-QP-39 | CACHE：five_hour／session 38@247，**weekly 軸一律低（30，以免週軸本身就擋而失去鑑別力）**；TRACE tmp、tmp 派發帳；payload＝`Agent` 的 PreToolUse | `quota_gate.quota_gate` 連呼 3 次（同一 300 秒內） | 前 2 次 rc 0、第 3 次 rc 2 且 stderr 含 `pace-floor`；同情境 `quota_rush.issue` 後 3 次皆 rc 0 | 致動器真的接上了：函式層對、gate 層沒人叫＝「機制蓋好沒接電」 |
| AT-QP-40 | 床造成的阻斷（AT-QP-39 第 3 次）與非床阻斷（一般 prepare 帶） | 讀 stderr | 床阻斷含 `sessionctl.py rush --hours`；非床阻斷**不含** | 阻斷必有確切下一步；非床阻斷不得推銷趕工（誤導） |

#### 10.4.5 趕工戳記與痕跡（`test_quota_rush.py`；縫 NOW、ENV、TRACE）

| AT | 前置 | 動作 | 預期 | 為何會紅 |
|---|---|---|---|---|
| AT-QP-41 | now 固定、`hours`＝1、why 合格、sid 給定 | `issue` | rc 0；檔存在；JSON 欄位齊（schema、issued_at、until＝now＋1 小時、until_epoch、hours、why、sid）；痕跡檔一列 `pace_rush_on` | 戳記格式是讀取端 fail-closed 的對手；欄位缺漏讀取端會全當無效 |
| AT-QP-42 | `hours`＝0、−1、5.01、`nan`、`"abc"`；另 5.0、0.01 | `issue` | 前五者 rc 2 且**不寫檔**；5.0 與 0.01 rc 0 | 上限 5 小時是 §2.15 的安全邊界；`<=` 寫成 `<` 或上限放寬一格即紅 |
| AT-QP-43 | why 為 7 字、8 字、前後半形／全形空白包住的 8 字、全形空白 only | `issue` | 7 字與空白 only rc 2；8 字（含包空白）rc 0 | 理由必填是戳記不淪為隨手關閉的唯一約束；字數以去頭尾空白後計 |
| AT-QP-44 | `env` 帶 `AUTOSDD_UNATTENDED=1`，其餘合格 | `issue` | rc 2、不寫檔、訊息含 `無人` | 無人窗口無人可宣告趕工；放行＝夜間自動窗口可自我解除煞車 |
| AT-QP-45 | 有效戳記；until＝now；until＝now−1s；壞 JSON；缺欄；schema 不符；until 為 naive；until−issued_at＞5 小時＋1 秒；until 與 until_epoch 不一致；有效戳記但 `env` 帶 UNATTENDED | `active` | 有效者回 dict 且 `left_minutes`＞0；其餘各自回 `None`（九種） | 每一種結構異常都必須 fail-closed（當無戳記＝床套用＝較緊）；任一種誤判有效＝放寬 |
| AT-QP-46 | 有效戳記；原 mapping 已有正值鍵；鍵為空字串／`"0"`；無戳記／過期／UNATTENDED；戳記檔不可讀 | `overlay` | 有效且鍵缺席／空白／≤0 ⇒ 回複本含 `RUSH_KEY`＝until_epoch 字串、原 mapping 未被改；鍵已有正值 ⇒ 不覆蓋；其餘 ⇒ 與輸入相等且無新鍵；不可讀 ⇒ 不拋 | `policy_env` 是所有 hook 的熱路徑，疊入失敗不得變故障源；覆蓋明示環境值＝吞掉操作者意圖 |
| AT-QP-47 | TRACE tmp；`issue(hours=1)` | `quota_gate.policy_env()` → `load_policy` → `decide`；再 `revoke` 後重跑 | 疊入後 `Policy.pace_rush_until`＝until_epoch、床不套用；撤銷後床恢復 | 端到端：戳記經唯一出口抵達 `Policy`；少接一段就是「戳記寫了沒生效」 |
| AT-QP-48 | 有戳記／無戳記 | `revoke` | 有：檔刪除、rc 0、一列 `pace_rush_off`；無：rc 0、訊息含「無趕工戳記」、**不**落事件 | M-P7 的 off 事件只能是真撤銷；無檔也寫事件會稀釋指標 |
| AT-QP-49 | 已有戳記後再 `issue` | 同 | 新戳記取代舊戳記（until 為新值）；痕跡兩列 `pace_rush_on` | 延長趕工＝重發；讀取端只認單一戳記 |
| AT-QP-50 | `cli` 各形式：發、`--off`、`--status`；無旗標；`--hours` 缺 `--why`；`--off` 與 `--hours` 並用；未知旗標；值不合法 | `cli` | 前三者 rc 0（`--status` 輸出含到期時刻、剩餘分鐘、why；無戳記亦 rc 0）；四種用法錯誤 rc 3；值不合法 rc 2 | rc 契約是呼叫端（主控）判斷成敗的依據；用法錯誤與拒絕要分得開 |
| AT-QP-51 | 子行程 `python tools/sessionctl.py rush …`（`AUTOSDD_TRACE_DIR` tmp） | 跑 | rc 0、stdout 含到期時刻；未知子指令的 rc 3 訊息含 `rush` | 薄殼分派真的接上；漏接＝文件宣稱有、命令列沒有 |
| AT-QP-52 | `decision.pace` 含 `lifted`；含 `within`；含 `exempt-*`；路徑指向目錄 | `log_floor` | 僅 `lifted` 追加一列 `pace_floor`（含 `at`、`kind`、`pct`、`minutes`、`allowed_pp`、`level`、`cap`、`band`）；其餘不寫；目錄路徑回 `False` 不拋 | M-P4 撤回條件的分子；不在 lifted 時寫＝分子灌水 |
| AT-QP-53 | PreToolUse＋`Agent`＋床抬水位；PostToolUse＋`Read`＋同水位；PreToolUse＋床未抬 | `quota_gate.quota_gate` | 僅第一種新增一列 `pace_floor` | PostToolUse 對每個工具都判，若也落款，一個窗內會寫出數千列；落款點只在派發邊緣 |
| AT-QP-54 | 痕跡檔 | 讀回 | 每列單行合法 JSON、`ensure_ascii=False`、`\n` 結尾；檔位於 `AUTOSDD_TRACE_DIR` 圍籬內，不寫真實 home | 測試不得污染開發機真實痕跡（本 repo 的圍籬慣例） |
| AT-QP-55 | 掃描 `tools/`、`.claude/hooks/` 下生產碼的 `load_policy(` 站點 | AST 掃 | 站點清單等於釘住的 frozenset（逐站點標註是否經 `quota_gate.policy_env()`）；新增站點即紅 | 戳記只經 `policy_env()` 進場；新站點若自建 env 就看不到戳記（床恆套用＝較緊，但同一件事兩個數）；只准縮不准長 |

#### 10.4.6 量測與回放（`test_waste_census_metrics.py` 增量；縫 FS）

| AT | 前置 | 動作 | 預期 | 為何會紅 |
|---|---|---|---|---|
| AT-QP-56 | tmp halt 目錄：五個標記——三個 binding 為五小時窗軸（窗長以文法判，不寫桶名）、一個週軸、一個早於 `--since-days`；另一個壞 JSON | `pace_metrics.m_p1` | `count==3`、`per_week==3/(days/7)`、`skipped==1` | M-P1 是主指標；把週軸 halt 算進來會讓「撞牆次數」被週額度事件污染 |
| AT-QP-57 | 合成落款：A 窗前 40% 時間內達 75pp；B 窗平穩；C 窗僅 2 樣本；一列缺 `resets_at` | `m_p3` | `windows==2`、`early_burn==1`、`share==0.5`、缺欄列計入 `skipped` | 分母須排除樣本不足的窗（落款稀疏是最大誤差源）；否則占比被稀釋成假改善 |
| AT-QP-58 | 合成三個週：末列距 reset 6 小時／30 小時／12 小時；reset 字串帶 `:59:59.9` 與 `:00:00.1` 微秒抖動；桶名 `seven_day_foo` | `m_p4` | 只計末列 ≤24 小時者（2 週）；抖動兩字串同組；中位數與最小值正確；`seven_day_foo` 以窗長文法判為長窗 | M-P4 是週用滿護欄；分組錯誤或把 30 小時前的讀數當「reset 前最後讀數」會偽造不退化 |
| AT-QP-59 | 事件檔含兩筆 `pace_rush_on`（各帶 `until`）；兩個五小時窗中一個與戳記區間重疊；無事件檔 | `m_p7` | `share==0.5`；無檔回全 0、不拋 | M-P7 的「床太緊」訊號；區間重疊判錯會讓 50% 門檻失去鑑別力 |
| AT-QP-60 | 合成主控逐字稿 4 個請求，`cache_creation` 為 1000／2000／3000／6000；另有子代理檔 | `m_c1` | `n==4`、`mean==3000`、`median==2500`；子代理不計 | M-C1 是主控成本的唯一量測；混入子代理會稀釋 |
| AT-QP-61 | CLI `--pace-metrics`（子行程，`--base` 等指 tmp） | 跑 | rc 0；stdout 含 `M-P1`、`M-P3`、`M-P4`、`M-P7`、`M-C1`；不寫 repo 內任何檔；缺全部輸入時印無資料說明、rc 0 | 探針不接閘門 rc、不污染工作樹（同 AT-TW-57） |
| AT-QP-62 | AC-7：合成 burn 三列（帶 `resets_at`）：38@247、30@247、99@30；一列缺 `resets_at`；halt 標記一件 | `--replay-pace-floor` | 輸出「會開床的列數＝1」與各列 `cap_with`／`cap_without`；撞牆窗的最早開床時刻有值；缺欄列計入 `skipped`；全程不呼叫網路、不讀真實 home | AC-7 要交 QA 判讀的回放；少了有／無床對照就無法回答「床會不會擋掉正常工作」 |
| AT-QP-63 | 套件結構 | 斷言 | `pace_metrics`、`pace_replay` 兩模組各 ≤400 斷言行；`tools/probe/waste_census.py` 仍為薄殼（新旗標只分派、無判準函式定義） | 落點規範與 LOC 分級（同 AT-TW-59） |

#### 10.4.7 其他與既有鎖（不得退化）

| AT | 內容 |
|---|---|
| AT-QP-64 | `python AutoClaude/tools/check_loc_budget.py --json` rc 0：`quota_gate.py` count_loc ≤500（淨 ≤0）、`quota_pace_floor.py`、`quota_rush.py`、`quota_policy.py`、`quota_policy_env.py` 皆在 guardrail_lib 400 內；`quota_pace.resolve` 的簽名參數名序列與改前相等（本期不改它） |
| AT-QP-65 | 既有 `test_quota_policy.py`、`test_context_budget_guard.py`、`test_quota_burndown.py`、`test_session_brief.py`、`test_selfimproving_*` 全綠。**因床而改的既有測試**逐條列於交卷檔，改法只准兩種：把該測試的狀態改到允許線內，或顯式 `pace_floor=False`；**不得刪除或弱化斷言**；每條附 WHY |
| AT-QP-66 | `quota_pace_floor.py`、`quota_rush.py` 以既有 Python 3.9 相容鎖（現查名稱）檢查：無 `match`、無執行期 `A\|B`、無 `slots=`、無 `zip(strict=)` |
| AT-QP-67 | AST 掃：`quota_pace_floor.py` 無 `open`／`write_text`／`os.environ`／`datetime.now`（零 I/O、零時鐘）；寫戳記與痕跡的呼叫只出現在 `quota_rush.py` |
| AT-QP-68 | `test_root_module_layout.py`、`test_doc_loc_baseline_freshness_r60.py` 的 `TestR74…`／`TestR79…` 綠；`.env.example` 與 `render_env_example()` 同步 |
| AT-QP-69 | Windows 檔案鎖原語鎖（`test_platform_neutral_paths.py::TestDirEntryPrimitivesAreAccountedFor`）綠：`quota_rush.py` 只用 `write_text`／`open(…,"a")`／`unlink`，不引入 `os.replace`／`rename` |
| AT-QP-70 | M7 全文鎖：`quota_pace_floor.line` 與 `describe` 新增句對 `quota_policy` 既有 M7 判準（每個 `%` 皆帶 `kind=` 與剩餘分鐘）綠；新增文字不出現孤立 `%` |

### 10.5 突變清單（QA 逐條實打；每條至少一條 AT 應轉紅，未轉紅＝補斷言）

| 編號 | 突變 | 應被殺掉的 AT |
|---|---|---|
| MU-01 | `apply` 把 `max(feed, level)` 改成 `feed`（不抬）或 `level`（覆寫） | AT-QP-12、20、25、32 |
| MU-02 | 免套用②的 `<` 改 `>` 或 `<=` | AT-QP-14、29 |
| MU-03 | `over <= 0` 改 `< 0` | AT-QP-02 |
| MU-04 | `over > step` 改 `>= step` | AT-QP-03 |
| MU-05 | 移除 `min(level, halt−1)` | AT-QP-06 |
| MU-06 | 床套到非最短窗軸 | AT-QP-17 |
| MU-07 | `active` 不看 UNATTENDED | AT-QP-44、45 |
| MU-08 | `rush_active` 到期判準 `>` 改 `>=`，或移除上限 `<= RUSH_MAX_SECONDS` | AT-QP-31 |
| MU-09 | `issue` 的 hours 上限 5 改 6，或下限放寬到負數 | AT-QP-42 |
| MU-10 | why 最小字數 8 改 4，或不剝全形空白 | AT-QP-43 |
| MU-11 | burst 或 step 的 `hi` 移除 | AT-QP-35 |
| MU-12 | `draining()` 不傳 `pace_floor=False` | AT-QP-37 |
| MU-13 | `overlay` 覆蓋已有的明示正值 | AT-QP-46 |
| MU-14 | `read_stamp` 放寬（結構異常仍判有效） | AT-QP-45 |
| MU-15 | `log_floor` 在非 lifted 時也寫 | AT-QP-52、53 |
| MU-16 | 免套用④（hold）移除 | AT-QP-16 |
| MU-17 | 免②計入被 `skip` 遮罩的軸 | AT-QP-18 |
| MU-18 | 窗長寫死 300 | AT-QP-09 |
| MU-19 | `pace_floor=False` 路徑仍呼叫 evaluate／apply 並改動輸出 | AT-QP-33、28 |
| MU-20 | `policy_env` 忘記疊入戳記 | AT-QP-47、39 |
| MU-21 | `decide` 未把 `pace_floor` 透傳給 `axes_of` | AT-QP-25、33 |
| MU-22 | `line` 在 state 為 `n/a` 時仍輸出一行 | AT-QP-23 |

### 10.6 真機驗證（本期；主控親跑；不得由開發棒代驗；結果寫進缺陷帳本列；一律「待真機驗證」）

| V | 步驟 | 通過判準 | 對應 |
|---|---|---|---|
| V-P1 | 下一個真實五小時窗內，窗前 90 分鐘內以並行派工把水位推過允許線（或回放確認某時刻已超線）後，跑 `python tools/session_resume_planner.py --pace`，再連續派 `Agent` 三次（同一 300 秒內） | `--pace` 印出 `配速床：` 且 state 為超線；第三次被擋、訊息含 `pace-floor` 與 `sessionctl.py rush --hours`；貼輸出與時間戳 | AT-QP-25、38～40 |
| V-P2 | 同情境 `python tools/sessionctl.py rush --hours 0.05 --why "<≥8 字>"`，再派三次；等 3 分鐘到期後再派 | 趕工期間三次皆放行、`--pace` 印趕工戳記生效；到期後床自動恢復（第三次又被擋）；痕跡檔有 `pace_rush_on`；`rush --status` 在到期前後各印一次 | AT-QP-30、39、41、47 |
| V-P3 | 另開一個**已在跑**的 Claude session，在主視窗發戳記後，於該 session 直接派 `Agent` | 該 session 下一次呼叫即生效，不必重啟（驗 `policy_env` 出口熱讀） | AT-QP-46、47 |
| V-P4 | 本機 `.env` 設 `AUTOSDD_QUOTA_PACE_BURST_PP=25` 後跑 `--pace`；移除後再跑 | 輸出尾端出聲「⚠️ … 高於上界 20.0」、實際用 20；移除後無出聲 | AT-QP-35 |
| V-P5 | `AUTOSDD_UNATTENDED=1 python tools/sessionctl.py rush --hours 1 --why "<≥8 字>"` | rc 2、無戳記檔、訊息含 `無人` | AT-QP-44 |
| V-P6 | 跑 `python tools/probe/waste_census.py --since-days 14 --pace-metrics` 與 `--replay-pace-floor`（真實 `quota_burn.jsonl`） | rc 0；M-P4 基線與 ADR §2.15.7 的現算值同量級；回放輸出「會開床的列數」與五件撞牆窗最早開床時刻，交 QA 判讀（不設通過數字） | AT-QP-61、62 |

### 10.7 第二期前置真機驗證（本期**只登記、不寫 AT、不實作**；全數待真機驗證）

| V | 步驟 | 通過判準 |
|---|---|---|
| V-K1 | 互動主控以自己的 `ScheduleWakeup`（50 分）發保溫請求（固定字面：不做任何工作、重排下一次、結束） | 保溫請求 usage `cache_read ≥ 0.95×N`、`cache_creation ≤ 5k`；逐字稿 assistant 時戳間隔≈50 分（同時驗「喚醒真的發生」——`ScheduleWakeup` 無憑證） |
| V-K2 | five_hour 在 95～99% 時 wake 仍發得出 | 請求未被拒、`status` 非 rejected |
| V-K3 | 先讀 settings-reference 的 `idleCompaction`，再在保溫期間觀察 | 閒置 50 分內 idle compaction 不觸發（逐字稿無 `compact_boundary`） |
| V-K4 | 保溫回合結束時 | 不被 `check_pending_handoff`／`sessionctl_guard` 的 Stop 推回而多出回合 |
| V-S1 | schtasks（使用者登入時）一次性 `handoff --spawn` | 能開互動視窗；新 session 的 SessionStart 公告交接包 |
| V-M1 | 先讀 statusline 文件，再在 statusline 腳本取樣 | 確認 `prompt_cache` 與（若有）rate limit 欄位；有才接每請求取樣，無則維持落款稀疏的誠實劃界 |
| V-U1 | 同 sid 連續兩次 `claude -p -r` 間隔 50 分 | 仍命中；與哨兵雙駕駛判準（§2.11）共存不誤判 OTHER_DRIVER（第三期） |
| V-C4 | 子代理與 `-p` 是否收到根 CLAUDE.md 的 rules 與 skill 描述 | 確認後才動開場瘦身（第三期） |

### 10.8 連動面清單（Developer 與 Closer 同一個 commit 收齊；不分批）

1. **`.env.example`**：以 `render_env_example()` 重生（三個新鍵；不手寫）；`python tools/lib/quota_policy.py --print-env-example` 現查。
2. **根 `CLAUDE.md`（只改兩處，不動機械守衛總表——本期無 hook）**：(a)〈現查指令速查表〉新增一列「配速床狀態／趕工戳記」→ `python tools/sessionctl.py rush --status`、`python tools/session_resume_planner.py --pace`（配速床行）；(b)〈額度哨兵〉所在段「額度 ≠ context 水位」之後加一句：五小時窗內另有配速床（`quota_pace_floor`），逃生口＝趕工戳記，數字現查 `--print-env-example`。不複寫任何數字。
3. **落點表 `docs/02_architecture/Root_Layout_and_Module_Placement.md`**：額度守衛列的「測試」欄補 `test_quota_pace_floor.py`、`test_quota_rush.py`；wastecensus 列的 `pace_metrics`、`pace_replay` 屬後續期、待落地時再補；同步 `test_root_module_layout.py` 的登記面。
4. **測試檔下限與棘輪重釘**：新增兩個測試檔與既有檔增量，依本 repo 重釘儀式（`_TREE_FILE_FLOORS`、onboarding 基線與 `python tools/sync_onboarding_baselines.py`；順序與數字現查，不在本章複寫）。
5. **CI paths**：套件目錄（`tools/lib/wastecensus/**`）已在 compat workflow 的 `paths`；扁平檔則是**逐檔名**列在 `paths`（現況例：`tools/lib/quota_meter.py`、`quota_escalation.py`、`quota_limits.py`、`quota_ledger.py`；`quota_pace.py`／`quota_gate.py` 是否列名現查）。新增的 `quota_pace_floor.py`、`quota_rush.py` 是否必須列名，以 CI paths 覆蓋鎖的判準為準（現查該鎖測試），需要則兩支 compat workflow 同 commit 補；`non_evolvable_globs` 不納入量測套件（沿用 §0 判斷），`quota_pace_floor.py`／`quota_rush.py` 屬守衛面判準檔，納入須先現查 SelfImproving 設定。
6. **LOC**：`quota_gate.py` 先抽出等量程式再接線（候選：halt 標記三函式、`pace_state`＋`settled_quota`），同 commit 重釘 hub 棘輪，不得調高 hub 預算。
7. **缺陷帳本**：DEF-200-589 一條（草稿見 §10.9），由 Closer／主控寫，本章不改帳本。
8. **ADR §2.15**：已落檔；實作落地後把 §2.15.5 第一期欄位改「已落地」，並把 §2.15.7 的 M-P 基線以實測回填。
9. **既有測試改動清單**：交卷檔列出（AT-QP-65）。

### 10.9 守衛面暴露證據座標與缺陷帳本草稿

| 編號 | 座標 | 類別 |
|---|---|---|
| E-P1 | 掌舵者原話：sid `eb1cb524-de09-4ad5-a068-69fa180dc64b` 2026-11-15 00:1x「當Token一小時就用完時…將Token盡量維持分配五小時」；主控親驗同 sid 23:03 8% → 00:1x 56%（70 分 48pp） | 掌舵者回報 |
| E-P2 | 逐字稿 sid `04b38d83` 2026-11-13T13:22:57Z `apiError:"usage_limit_reached"`、`status:"rejected"`；halt 標記 binding＝five_hour 近 14 天 5 件（11-07 17:13、11-13 04:43、11-14 00:49、11-14 22:44 等） | 非構造性逐字稿 |
| E-P3 | 真實輸出：sid `ff7d69c4-aa33-4ced-bbf0-cbd780a539cd` 約 2026-11-15 08:56 gate 輸出 `kind=five_hour 43% 剩 244 分鐘 band=free horizon=far cap=None note=burn-ahead` | 真實輸出 |

**DEF-200-589 草稿（Closer 貼入缺陷帳本；內容不得改動語意）**：「額度配速：五小時窗內超前燃燒對 cap 零煞車力，且無『非趕工時攤平五小時』的動作層。根因：`quota_pace.burn_step` 判超前只把視野夾到 far，free 帶 `_base_cap=None` ⇒ `None×0.5` 仍不設限；攤提只在長窗自軸達 converge 才收緊。表徵：2026-11-14 23:03～2026-11-15 00:1x 五小時窗 70 分鐘用掉 48pp，08:56 gate 輸出 `band=free cap=None note=burn-ahead`。修法（第一期）：新增窗內配速床（`quota_pace_floor`：允許線＝100×已過比例＋`AUTOSDD_QUOTA_PACE_BURST_PP`（出廠 20、只准下修），超線抬水位至 converge／prepare，窗尾與長窗先翻頁免套用）與趕工戳記（`sessionctl rush`，上限 5 小時、`why`≥8 字、無人窗口拒絕，戳記由 `policy_env()` 疊入），並補量測 M-P1／P3／P4／P7、M-C1 與回放。保溫（主控有條件推翻 X9）僅記決策，實作屬第二期，前置真機驗證 V-K1～V-K4。設計＝ADR-XPLAT-004 §2.15；驗收＝本 TCS §10；真機驗證 V-P1～V-P6 待主控。」
