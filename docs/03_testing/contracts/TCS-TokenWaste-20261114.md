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
