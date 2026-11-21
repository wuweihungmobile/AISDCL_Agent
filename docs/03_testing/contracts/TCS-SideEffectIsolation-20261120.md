# TCS-SideEffectIsolation-20261120：真機驗證的副作用隔離（產品面拒絕／job 環境允許表／副作用帳／快照 diff）——需求＋驗收合一

> 角色：SD（R218-B，AISDLC 第 2 階段）。**r2**（2026-11-20）：依 SCG 審查 FAIL 逐條改版（處置見 DES 附錄 B）。**r3**（2026-11-21）：依第二輪 QA FAIL 逐條改版（處置見 DES 附錄 C）。**r4**（2026-11-21）：依第三輪 QA FAIL 逐條改版並與 QW r6 聯合改版（處置見 DES 附錄 D；兩稿交叉介面＝DES §10.2.1）。**r5**（2026-11-21）：依聯合 QA 第四輪 FAIL 逐條改版並與 QW r7 聯合改版（處置見 DES 附錄 E）；第五輪 QA（R218-B r5 PASS、P3×1）只補本表頭版次（B5-P3-1）與 DES §10.2.1 X-19 的 `reason=sentinel_off` 字面（隨 QW r8 QW5-P3-2），不改任何 REQ／AT／E2E／MU。設計全文＝`docs/02_architecture/RealVerify_SideEffect_Isolation_Design.md`（下稱 **DES**）；上游＝`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（下稱 **PRD**，修訂表 v2.1.25 列、§11.9 R-VER-1～6、§15.5 紅線 13、§16.6 2026-11-20 第二列）；相容＝`docs/02_architecture/QuotaWall_CacheContinuity_Design.md` r7／r8（下稱 **QW**；r8 只改 QW 內部 S-24②／S-25／S-26 與補 AT-QW-82，交叉介面僅 X-19 字面）。
> 前綴：`REQ-SE-`、`AT-SE-`（單元／整合，縫注入）、`E2E-SE-`（真機）、`MU-SE-`（突變，必須讓指定測試轉紅）。計數：REQ 42、AT 50、E2E 18、MU 34（r5：+MU-SE-34；AT-SE-26／39、E2E-SE-09／17 就地改，見 DES 附錄 E）。
> 🔴 掌舵者 2026-11-18 指令：每個功能都要有真機 E2E（真行程／真排程／真 `claude -p` 子行程／真 hook／真逐字稿重放才算，單元測試不算）；E2E 結果一律入 `docs/06_quality/RealVerify_Result_Ledger.md`，未入帳＝未結。
> 🔴 本輪鐵令：**任何 E2E 不得需要人按鍵**；**不得燒真額度**；**任何 E2E 都不真開 claude 視窗**——凡可能走到產品 spawn（互動或無頭）的 E2E 一律以 argv `--claude <假 claude>` 帶入 GUI 子系統替身（DES §4.4；不建主控台視窗；模式 `resume_ok`／`fresh_ok`／`fail`），**同一次到點的每一次 spawn 嘗試都用同一個替身**；即使漏帶，沙盒目標也會被 L1 以 `sandbox_real_exe` 拒絕（DES D-18），連「判準被拿掉」的突變實跑也只會打到替身（驗 D-18 本身的 E2E 用家外替身）。只有 E2E-SE-03（既有 `realverify run --all` 的花費）與 E2E-SE-16（F5 宿主下以隱藏旗標起一次 haiku，經載具自有入口 `open_window`，PRD R-VER-2 的「F5 宿主隱藏視窗除外」）呼叫真 `claude`。**不得寫 `~/.claude.json`**（E2E 只唯讀其鍵名）。
> 🔴 等待超過 5 分鐘的 E2E（01、02、04、17、18）若由子代理執行，一律 `sessionctl runlong`＋`waitfor` 分段等待（根 CLAUDE.md〈不讓快取過期〉②）。
> 測試慣例沿用 sessionctl／realverify：時間注入 `now`、路徑圍籬 tmp、不讀本機真實 `~/.claude`（E2E 除外）、不開測試用環境變數鉤、禁用 skip。E2E 結束後沙盒家目錄、`~/.claude/projects/<沙盒 slug>`、本 run 的副作用帳皆須 `closed`／不存在。
> 自驗家族：`sideeffect`（`RV-SE01`～`RV-SE18` 對應 `E2E-SE-01`～`18`；`RV-SE17` 的案例程式隨 QW Q6 落地，DES §10.2-4）；輔助案例家族 `sideeffect_selftest`（`RV-SE-OWNER`、`RV-SE-SEED`、`RV-SE-LEAK`、`RV-SE-NOOP`、`RV-SE-LOCK`）只由 `sideeffect` 案例以子行程呼叫。**兩個家族都不在 `--all` 內**（r3，DES D-19；RV-SE03 案例內跑 `run --all`，不得跑到自己），只能以 `--family sideeffect`／`--case` 指名執行。

## 0. 模組落點表
照 DES §11（本檔不重抄）。§5.6 檔案集合＝DES §11「路徑」欄全部。

## 1. 需求（REQ）

### 1.1 判準核心（S1，DES §3）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-SE-01 | 身分檔 `.autosdd_sandbox.json`（schema 1：run_id、sid、owner_pid、owner_started、created_at、allow_until=null、window）在**家目錄**原子寫入：一般沙盒＝根（`mkdtemp` 後第一動作，`git init` 後立即把樣式追加進 `.git/info/exclude`）；worktree 沙盒＝外層（外層第一動作寫入，worktree 建在 `<外層>/wt`，宿主 common-dir `info/exclude` 冪等追加）；寫入前後 `git status --porcelain` 逐字相同、`worktree add` rc 0；r4：一般沙盒把 `LOCAL_EXCLUDES`（身分檔＋7 居所目錄〔由 `RESIDENCE_DIRS` 推得〕＋`/bin/`＋`/fakeclaude.*`）寫進 `.git/info/exclude`、`install_tools._EXCLUDES` 同源，建好居所與替身及其設定檔後 porcelain 為空 | §3.1、D-1、D-23 | S1、S5 |
| REQ-SE-02 | `is_sandbox(path)`：本層或上一層有身分檔 ∨ 任一路徑段以 `AutoSDD_RV_sbx_` 開頭 ∨ 路徑段含 `AutoSDD-RV-sbx-`；Windows 不分大小寫 | §3.2、D-1 | S1 |
| REQ-SE-03 | 租約：`grant(until, max_minutes=LEASE_MAX)` 存 `min(until, now+min(max_minutes, LEASE_CAP))`（`LEASE_MAX`＝30、`LEASE_CAP`＝300，程式常數，不開 env）；案例以原始碼常數 `lease_minutes` 宣告；`revoke` 設 null；有效＝`allow_until` 非 null ∧ now < allow_until ∧ 主人 pid 存活 ∧（可得時）建立時間相符 | §3.2、D-2 | S1、S5 |
| REQ-SE-04 | `target_verdict` 依序：沙盒旗標集合非空且任一實體不存在 ⇒ `target_missing`（集合為空不做存在檢查）；cwd 根≠pkg 根（皆以「往上找 `.git`」＋`resolve`＋`normcase` 解析，不開行程）⇒ `root_mismatch`；沙盒 ⇒ `sandbox_unreadable`／`sandbox_no_lease`／`sandbox_lease_expired`／`sandbox_owner_dead`／`allow sandbox_lease`；否則 `allow production`；例外 ⇒ `refuse error:<類名>` | §3.3、D-4 | S1 |
| REQ-SE-05 | 判準模組不讀環境變數（無 `os.environ`／`getenv`／`environ`）、不開行程；正式目標路徑不新增任何痕跡事件 | §3.3、D-4 | S1 |
| REQ-SE-06 | `job_expiry(home)`：正式 ⇒ None；沙盒且租約有效 ⇒ `allow_until` | §3.2、§5.4、D-5 | S1 |
| REQ-SE-07 | `SITES` 站點登記表；AST 鎖：tools 內所有開窗（`CREATE_NEW_CONSOLE` 名稱、`getattr(subprocess, "CREATE_NEW_CONSOLE", …)` 字串形態、`creationflags=` 字面 `0x10`／`16`）、排程登記（`backend.arm`／`register`／`Register-ScheduledTask`）、到點入口、toast（`NotifyIcon`）、通知佇列寫入、**`claude` 執行形態**（r3：重用 `interactive.yields_claude`，擴 `<名> or "claude"`、參數與 argparse 預設 `"claude"`；互動與無頭 `-p` 皆算；`CLAUDE_PRESENCE_ONLY` 只收存在檢查並附 WHY）的產品函式都在 `SITES` 且呼叫 `target_verdict`／`register_verdict`（realverify 載具自有站點除外，由 REQ-SE-34 管）；`SITES` 至少含 planner `probe_quota` 呼叫者、`selfimproving/patrolrun.launch`、`tools/selfimproving.py patrol` 入口；r4：普查範圍＝`tools/*.py`、`tools/lib/**/*.py`、`.claude/hooks/*.py`，排除 `tools/tests/**`、`tools/probe/**`、`tools/lib/realverify/**`；`yields_claude` 擴充後重跑 InteractiveWindowEntryLockTest、新命中登記 | §3.2、§3.4、D-22 | S1（表）、S2／S3（接線）、S5（偵測器） |
| REQ-SE-08 | **`sandbox_real_exe`**（r3）：spawn／tick／headless 類站點把執行檔（未給 `--claude` ＝ `"claude"`）傳入判準；沙盒目標租約全過但執行檔不在沙盒家目錄之下（`resolve`＋`normcase` 前綴；裸名算不在；不查 PATH）且身分檔 `window≠true` ⇒ `refuse sandbox_real_exe`，終局同 REQ-SE-16；`window=true` 或執行檔在家目錄下 ⇒ 不因此拒；正式目標不判 | §3.3、D-18 | S1、S2、S3 |

### 1.2 產品站點（S2、S3，DES §3.4）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-SE-10 | `park_cli._cmd_fire`：判準釘在 `park_job_start` 痕跡之後、`park.read_marker`／`.ack`／`handoff.list_handoffs`／`live_driver` 之前，輸入只用 `_REPO`、`--pkg`、sid；拒絕 ⇒ 痕跡 `sideeffect_refused`（site、reason、sid、roots），之後才讀標記並在屬本 job 且 armed 時記 `refused`、`_disarm_verified` 自拆、rc 0；不得出現 `park_route`、不得呼叫 oldwin gate | §3.4 | S2 |
| REQ-SE-11 | `park_cli.spawn_resume`（含 `fork=True`）、`handoff.spawn`：runner 前判；拒絕 ⇒ rc `RC_SIDEEFFECT_REFUSED`（10，`sandbox_scope` 常數，r4）、stderr 一行理由、同痕跡；不寫 `.resumed`／`.spawned`；`_cmd_fire` 見此 rc ⇒ 標記 `refused`、不寫 handback、不入佇列、不嘗試另一路、自拆、rc 0（QW §7.5／§7.6 同語意） | §3.4、D-24 | S2（QW Q3 保持） |
| REQ-SE-12 | 排程登記站點（`_cmd_park`、`oldwin_sched.schedule_retry`、哨兵武裝、`engine_resume_job.arm`、`openitems/drive.drive_item`、`selfimproving/schedarm.arm`）：登記前 `register_verdict`；拒絕 ⇒ rc 4、stderr 帶 reason、痕跡 `sideeffect_refused site=<站點>`、不登記；放行且目標為沙盒 ⇒ 帶 `expire_at=job_expiry`（Windows `EndBoundary`＋`DeleteExpiredTaskAfter=PT0S`）；正式目標 ⇒ 登記內容與修改前逐字相同 | §3.4、§5.4 | S1（後端）、S2、S3 |
| REQ-SE-13 | `session_resume_planner._run_resume` 與 `_sentinel_tick` 的 probe／resume 分支：spawn 前判；拒絕 ⇒ 不 spawn、走既有 disarm、痕跡同上 | §3.4 | S3 |
| REQ-SE-14 | openitems 到點入口、`quota_escalation` 帶目標上下文的通知呼叫者：拒絕 ⇒ 不執行／不出 toast／不入通知佇列、痕跡 `sideeffect_refused site=<站點>` | §3.4、D-10 | S3 |
| REQ-SE-15 | 正式回歸：正式目標的 park 到點、spawn、登記、哨兵、openitems、通知行為與痕跡序列逐字不變（無 `sideeffect_*` 事件、無 `EndBoundary`）；正式交接包已刪仍照舊走 `skip expired` | §3.3、§8 | S2、S3 |
| REQ-SE-16 | **L1 拒絕＝終局**：不讀 holder、不進 QW §7.3 讓路觀察（`OBSERVE_SEC`）、不落 `park_yield_primary`／`park_attempt`／`park_chain_failed`、不嘗試另一路、不寫 handback、不入通知佇列、不呼叫 `notify`；標記寫 `refused`（QW §7.6 只接手 `failed`）；涵蓋 fire 站點與 spawn 站點（`RC_SIDEEFFECT_REFUSED`）兩種拒絕；**讀取端認得 `refused`**（r3）：`park.STATUSES` 含 `refused`（r4，`read_marker` 視為有效標記）、`park --status` 印狀態與 reason、`park.yields` 視為非 armed、`park.stop_verdict` 不當續航憑證、SessionStart 公告列一行「到點被產品面拒絕」且不當失敗 | D-13、D-21、§3.4 | S2（QW Q3 保持） |
| REQ-SE-17 | QW r3 新站點（`spawn_resume(fork=True)`、§7.3 job 內重排、§7.5 第 3 步通知與入列、§7.6 `_sentinel_tick` 接手）在 `SITES` 且呼叫判準；§7.3 重排用 `register_verdict`；`--fork-session` 新窗命令列含舊 sid，L2 行程比對成立 | §3.4、D-8、§10.2 | QW Q3（站點）、S5（比對） |
| REQ-SE-18 | 沙盒目標登記時 `fire_at > allow_until` ⇒ `refuse lease_shorter_than_fire`；續租不改已登記工作的 `EndBoundary`；登記出來恆 `EndBoundary ≥ StartBoundary` | D-15、§5.4 | S1、S2、S3 |

### 1.3 job 環境允許表（S1、S2、S3、S5，DES §4）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-SE-20 | `endurance_env.RESIDENCE_KEYS`＝7 鍵（TRACE／HANDOFF／HANDBACK／PLAN／QUOTA_CACHE／CONTEXT_FEED／SI）；AST 鎖：`tools/lib/**/*.py` 的 `AUTOSDD_[A-Z_]*_DIR` 字面 ⊆ `RESIDENCE_KEYS` | §4.1 | S1 |
| REQ-SE-21 | `job_env_argv(env, *, sandbox)` 只對顯式設定的 `JOB_ENV_KEYS` 產 `--job-env KEY=VAL`（鍵序固定；`sandbox` 取自同站點 `register_verdict` 判決）；顯式空值的 `AUTOSDD_SENTINEL_OFF` 視同未設；顯式值不在允許值：**沙盒目標** ⇒ 拋 `JobEnvValueError`，登記站點 rc 2、不登記、stderr 點名鍵與值；**正式目標** ⇒ 該鍵不轉送、不拋、登記照常（r4）；`apply_job_env(argv)` 剝旗標寫環境、**遇第一個 `--` 即停**（其後原樣保留，r3），非允許鍵或非允許值 ⇒ rc 2；正式環境 argv 逐字不變 | §4.1、D-6、D-20 | S1 |
| REQ-SE-22 | 所有排程 job argv 經 `job_env_argv`（park、oldwin、openitems、engine resume、哨兵、SI schedarm、QW §7.3 重排）；四個入口（`sessionctl.py`、`session_resume_planner.py`、`openitems.py`、`selfimproving.py` 排程動詞）最先 `apply_job_env`；舊 `--trace-dir` 相容一版 | §4.2 | S2、S3 |
| REQ-SE-23 | `Sandbox.env()` 7 居所鍵指向家目錄下、`AUTOSDD_DESKTOP_NOTIFY`＝空、`AUTOSDD_SENTINEL_OFF`＝1；撤 `real_traces`、`sandbox.handoff_dir()` 真目錄與其清理；撤 `ctl_env` 對 `AUTOSDD_SENTINEL_OFF` 的 pop，需要真哨兵者 `ctl_env(arm_sentinel=True)` 且原始碼附 WHY（r4）；realverify 原始碼 `Path.home()`／`".autosdd"` 字面只准在允許表 | §4.3、D-25 | S5 |
| REQ-SE-24 | `JOB_ENV_KEYS`＝`RESIDENCE_KEYS` ∪ {`AUTOSDD_SESSION_SWITCH_MODE`（`auto|notify|off`）、`AUTOSDD_DESKTOP_NOTIFY`（只准空）、`AUTOSDD_SENTINEL_OFF`（只准 `1`）}；不收 `AUTOSDD_UNATTENDED`；AST 鎖：`Sandbox.env()` 與案例 env 輔助函式設定的每一鍵 ⊆ `JOB_ENV_KEYS` ∪ `SANDBOX_LOCAL_ONLY`（鍵→WHY） | §4.1、Q-4 | S1、S5 |
| REQ-SE-25 | `--claude <path>`（r3 改寫）：`park`／`park --fire`、`handoff --spawn`、planner（續跑、`--probe-quota`、`--sentinel-tick`；`--probe-command` 為同 dest 別名、相容一版）、`selfimproving.py patrol`／`sched arm` 接受；登記行程收到時原樣寫進 job argv，`park` 另寫進標記 `claude` 欄；**`_cmd_fire` 一次執行內的每一次 spawn 嘗試都用同一個值**——F4 選的 RESUME（`spawn_resume`）與 FRESH（`handoff.spawn`）、QW §7.4 fork、QW §7.5 失敗鏈另一路；QW §7.6 哨兵接手用標記 `claude` 欄；未給 ⇒ argv、標記與現行逐字相同、spawn 用 `"claude"` | §4.2、D-14、D-22 | S2、S3（QW Q3 保持） |
| REQ-SE-26 | `apply_job_env` 遇居所值位於沙盒路徑段而其家目錄不存在 ⇒ 不套用、不寫任何檔、不建任何目錄，stderr 一行、rc `RC_RESIDENCE_MISSING`＝9（r3：與五個入口其他 rc 字面皆不相等） | §4.1、D-17 | S1 |
| REQ-SE-27 | `fakeclaude`（r3）：GUI 子系統替身；先記一行（argv、cwd、時間、模式）到 `<家>/fakeclaude.jsonl`；`fakeclaude.mode`：`resume_ok`（argv 含 `-r <sid>` 且無 `--fork-session`）⇒ 往 `<projdir>/<sid>.jsonl` 追加一行並存活 `fakeclaude.sleep` 秒（預設 20）後 rc 0；`fresh_ok`（無 `-r` 或含 `--fork-session`）⇒ 新建 `<projdir>/<uuid4>.jsonl` 並存活後 rc 0；`fail`（缺席預設）或成功模式遇不適用 argv ⇒ 立即以 `fakeclaude.rc`（預設 1）結束；`<projdir>` 只取自 `fakeclaude.projdir`（缺席 ⇒ fail），寫入前已登記 L2 `transcript_dir`；判定 SSOT＝`fakeclaude.decide(argv, cfg)`；產生前登記 `temp_file` | §4.4 | S5 |

### 1.4 副作用帳與崩潰安全清理（S5，DES §5）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-SE-30 | `~/.autosdd/realverify_leases/<run_id>.jsonl` 只追加；每個載具副作用之前寫 `intent`、之後寫 `made`；kind ∈ {sandbox_root, sched_job, transcript_dir, process, worktree, temp_file} | §5.1、§5.2 | S5 |
| REQ-SE-31 | `replay`：主人可驗證存活 ⇒ 不是孤兒；可驗證已死 ⇒ 孤兒；驗不到 ⇒ 以 `expires_at` 兜底；撤銷序 process→sched_job→worktree→目錄；process 只在命令列含沙盒 sid／根時砍，否則記 `unverified`，下次重放該 pid 已不存在即轉 `revoked`；排程撤後回讀確認；全數完成寫 `closed`；`intent` 列同樣撤；`ctx.close()` 第一步 `revoke` 租約 | §5.2、§5.3、D-16 | S5 |
| REQ-SE-32 | 發現式掃描：Action 含 `AutoSDD_RV_sbx_` 而無可驗證存活主人的 `AutoSDD_*` 排程；（r5，D-27）Action 含 `AutoSDD_RVprod_<run_id>` 而該 `<run_id>` 帳不存在、主人已死或帳已 `closed` 的 `AutoSDD_*` 排程（同判準套用 `%TEMP%\AutoSDD_RVprod_*` 與 `~/.claude/projects/*AutoSDD-RVprod-*`）；主人已死（或無身分檔且 mtime 超過 `LEASE_CAP`）的 `%TEMP%\AutoSDD_RV_sbx_*`、沙盒家已不在的 `~/.claude/projects/*AutoSDD-RV-sbx-*`（`~/.claude/sessions` 有活 cwd 者跳過） | §5.3 | S5 |
| REQ-SE-33 | `realverify run` 開頭先 `replay`＋發現式掃描；有撤不掉者（不含已 abandoned 的 ident）⇒ 不執行任何案例、rc 2、末行 `REALVERIFY_VERDICT=fail reason=orphans` | §5.3、D-11 | S5 |
| REQ-SE-34 | 單一家：`sched.cleanup_all_rv`、`_disarm_oldwin_tasks`、`park_cleanup`、`sweep_orphans` 成薄殼；AST 鎖：realverify 套件內呼叫排程撤銷的函式只准在 `leases.py` | §5.5 | S5 |
| REQ-SE-35 | `python tools/realverify.py sweep [--dry-run]` 末行 `SWEEP_VERDICT=clean\|revoked n=<k>\|unrevoked n=<k>`、判決 rc 0；`--legacy` 只列 DES §9 X1～X5、X7 與含已知沙盒 sid 的真 `~/.autosdd` 檔；`--legacy --apply` 才刪；永不觸及 X6 與 X8 | §5.6、§9 | S5 |
| REQ-SE-36 | `sessionctl status` 增一行 `realverify 孤兒 n=<k>`，只讀帳檔（不 import realverify、不撤銷、不改任何檔） | §5.6、D-7 | S2 |
| REQ-SE-37 | 拒跑出口：REQ-SE-33 拒跑時寫 handback `<handback 居所>/realverify_orphans_<run_id>.md`（居所＝`AUTOSDD_HANDBACK_DIR`，預設真 `~/.autosdd/handback`，r3；每項 ident、原因、`--abandon` 指令）並依 `quota_escalation` 既有語意入通知佇列（佇列居所＝`trace_dir()`）；`sweep --abandon <run_id> --why "<≥8 字>"` 只把帳記 `abandoned`→`closed`（不砍、不刪），之後該帳 ident 撤不掉只記 note、不再拒跑；**發現式掃描的項目以正規化路徑等於或位於 abandoned ident 之下者同樣只記 note**（r3） | §5.3、D-11 | S5 |
| REQ-SE-38 | `realverify run --all` 排除 `sideeffect` 與 `sideeffect_selftest` 家族（r3）；兩家族只能以 `--family`／`--case` 指名 | D-19 | S5 |

### 1.5 每案快照（S5，DES §6）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-SE-40 | `snapshot.take()` 唯讀取 DES §6.1 各面；S10 目錄取 (名稱, mtime, size)，diff 時對新增或改動檔讀內容（≤1 MB）找沙盒字樣；`~/.claude.json` 只取 `projects` 鍵名 | §6.1 | S5 |
| REQ-SE-41 | `run_case`：前快照→案例→`ctx.close()`→後快照→diff；含沙盒字樣的新增／改動 ⇒ `fail`，detail 首行 `SIDE-EFFECT LEAK`；其他差異進 notes `SNAPSHOT-NOISE`；`~/.claude.json` 新增鍵一律 fail；**批次層同一規則**（含本批任一沙盒字樣項＋`~/.claude.json` 新增鍵）⇒ `REALVERIFY_VERDICT=fail reason=leak`，其他差異只記批次 notes | §6.2、D-9 | S5 |
| REQ-SE-42 | `realverify.py snapshot --out <檔>`、`snapshot --diff <前> <後> [--tokens <檔>]` 唯讀、rc 0 | §6.2 | S5 |

### 1.6 F5 接點（S5，DES §7）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-SE-50 | `CaseContext.grant_side_effects(sb, minutes, window=True)` 先 `interactive.assert_trusted(sb)`，不過即 `NotTrusted`（判 ENV） | §7 | S5 |
| REQ-SE-51 | tools 內任何程式不寫 `~/.claude.json`（AST／字面鎖：`open(..., "w"/"a")`、`write_text`、`json.dump`、`os.replace` 目標不得解析到該檔名） | §0.2 Q-1、§12 | S5 |
| REQ-SE-52 | F5 自身副作用進帳：外層家目錄、worktree 登記、隱藏探針行程、探針 debug log、`open_window` 行程（以沙盒 sid 為鍵） | §5.2、§7 | S5 |

### 1.7 規格與政策（本棒／S7）
| REQ | 內容 | DES | WP |
|---|---|---|---|
| REQ-SE-60 | PRD 修憲只追加：修訂表 v2.1.25 列、§11.4 註記、§11.9 新節、§15.5 第 13 條、§16.6 新列；修憲前既有每一行位元組不變，例外只有 R217 三個 hunk（`@@ -2676`、`@@ -2720`、`@@ -2787`）的行內改動，且須滿足「舊行是某一新行的字元子序列」 | 附錄 A | 本棒、S7 |
| REQ-SE-61 | E2E-SE 全 PASS 前，`.github/workflows/**`、`tools/lib/selfimproving/**`、`tools/lib/openitems/**`、`tools/openitems.py`、`tools/run_local_nightly.ps1`／`.sh`、`tools/install_windows_nightly.ps1`、`tools/local_ci_gate*` 不得出現「同一呼叫內同時有 `realverify` 與 `--all` token」的呼叫（字串、串列 `["run", "--all"]`、`--all --long` 皆算） | D-12 | S7 |

## 2. PRD 追溯
| PRD 座標 | 關係 | REQ |
|---|---|---|
| §11.9 R-VER-1 副作用清單 | 新增 | 23、40 |
| §11.9 R-VER-2 隔離契約（含排程 job、替身、F5 隱藏視窗例外） | 新增 | 20～27 |
| §11.9 R-VER-3 崩潰安全清理 | 新增 | 18、30～38、52 |
| §11.9 R-VER-4 產品面拒絕 | 新增 | 01～08、10～17 |
| §11.9 R-VER-5 每案快照 diff | 新增 | 40～42 |
| §11.9 R-VER-6 全域設定不寫 | 新增 | 50、51 |
| §11.4【v2.1.25 註記】 | 註記 | 12、18 |
| §15.5 紅線 13 | 新增 | 05、23、24、41、51 |
| §4.5.6／§4.5.10 喚醒、§4.3 交棒（`park --fire`、`--spawn`、哨兵續跑）、§4.5.11（v2.1.24）續航矩陣的備援路徑 | 喚醒對象合法性（R-VER-4 的產品面落點） | 10～17 |
| §16.5 (i)、§16.6 新列、修訂表 v2.1.25 | 修憲程序 | 60、61 |

## 3. 驗收測試（AT；縫：`NOW`、`FS`（tmp 圍籬含 `trace_dir`、假家目錄）、`ENV`、`PS`（假行程表：pid→存活／建立時間／命令列）、`SCH`（假排程後端：arm／list／disarm／XML）、`TR`（合成或截取逐字稿）、`RUN`（假 spawn runner）、`GIT`（git 呼叫記錄））
| AT | REQ | 輸入 | 預期 |
|---|---|---|---|
| AT-SE-01 | 01 | `Sandbox.create`；`trusted_sandbox`（假 prober、真 git 於 tmp 宿主）；`GIT` 記錄每次呼叫當下身分檔是否存在 | 第一次 git 呼叫時身分檔已存在且欄位齊、`allow_until=null`、owner_pid＝本行程；worktree 在 `<外層>/wt`、`worktree add` rc 0；兩種沙盒寫身分檔前後 `git status --porcelain` 逐字相同；exclude 檔含樣式；r4：一般沙盒再建 7 個居所目錄（各放一檔）、`bin/claude.exe`（假檔）、`fakeclaude.{mode,sleep,rc,projdir,jsonl}` 後 porcelain **為空**；`LOCAL_EXCLUDES` ⊇ `Sandbox.env()` 指向的每個家目錄下目錄名（以 `RESIDENCE_DIRS` 推得，於 tmp 加一個新居所鍵而未進 exclude ⇒ 紅）；`install_tools._EXCLUDES` 與其同源 |
| AT-SE-02 | 02 | 路徑：①有身分檔、名稱無前綴 ②`…\autosdd_rv_SBX_x`（大小寫異）無身分檔 ③`~/.claude/projects/C--…-AutoSDD-RV-sbx-abc` ④一般 tmp 目錄 ⑤身分檔在上一層的 `wt` 子目錄 | True／True（Windows）／True／False／True |
| AT-SE-03 | 04 | 模擬排程 job 跑沙盒內 tools 複本：cwd＝沙盒根、pkg 檔頭 `repo 根`＝同一沙盒、slug 同沙盒、無租約 | `refuse sandbox_no_lease` |
| AT-SE-04 | 03 | `grant(until=now+120 分)`；`grant(until=now+400 分, max_minutes=600)`；`grant(until=now+200, max_minutes=300)`；`revoke` | 存 +30／+300／+200；revoke 後 null；寫入皆原子 |
| AT-SE-05 | 05 | AST 掃 `sandbox_scope.py`；同一輸入在 `ENV` 設任意 `AUTOSDD_*`（含 `AUTOSDD_REALVERIFY=1`、`AUTOSDD_UNATTENDED=1`、`GIT_DIR`）前後 | 無 environ 參照、無 subprocess；判決逐位元組相同 |
| AT-SE-06 | 03、04 | `PS`：主人活／未過期；死／未過期；活／過期；活／null；活但建立時間不符 | allow sandbox_lease／owner_dead／lease_expired／no_lease／owner_dead |
| AT-SE-07 | 04 | cwd＝tmp 正式 repo 子目錄（大小寫、斜線形態不同），pkg 檔頭 `repo 根`＝沙盒；兩者同為正式 repo；worktree 的 `.git` 為檔案 | `refuse root_mismatch`／`allow production`／worktree 根正確解析 |
| AT-SE-08 | 04、15 | 沙盒家已刪、pkg 指向它；沙盒存在而 pkg 檔已刪；正式 pkg 已刪（無任何沙盒旗標） | `target_missing`／`target_missing`／`allow production`（後段照舊 skip expired） |
| AT-SE-09 | 04 | 身分檔為亂碼／schema 2／讀取拋 `PermissionError` | `sandbox_unreadable`／`sandbox_unreadable`／`refuse error:PermissionError` |
| AT-SE-10 | 10 | `_cmd_fire`：標記 armed、label 屬本標記、沙盒無租約；`SCH`、`RUN`；`read_marker`、`list_handoffs`、`live_driver`、oldwin gate 以 spy 替換 | 痕跡序列＝`park_job_start`→`sideeffect_refused`；`list_handoffs`／`live_driver`／gate 呼叫 0 次；`read_marker` 只在拒絕痕跡之後呼叫；標記 `refused`；disarm 1 次；rc 0；`RUN` 0 次 |
| AT-SE-11 | 06、12 | 各登記站點：正式目標／沙盒有租約／沙盒無租約 | 正式：`expire_at=None` 且 XML 與修改前黃金檔逐字相同；有租約：`EndBoundary`＝allow_until、`DeleteExpiredTaskAfter=PT0S`；無租約：rc 4、`arm` 0 次、stderr 含 `sandbox_no_lease`、痕跡 `sideeffect_refused site=<站點>`（r4：只斷言 rc 4 不算，rc 4 另用於無人窗口等既有拒絕） |
| AT-SE-12 | 11 | `spawn_resume`（`fork` False／True）、`handoff.spawn`：沙盒無租約，模式 auto、Windows | rc＝`sandbox_scope.RC_SIDEEFFECT_REFUSED`（以常數比對，非字面）、stderr 含 reason、痕跡 `sideeffect_refused`、`RUN` 0 次、無 `.resumed`／`.spawned` |
| AT-SE-13 | 13 | planner `_run_resume`、`_sentinel_tick`（halt 標記使其要 resume／probe），目標沙盒無租約 | subprocess spawn 0 次；disarm 路徑走到；痕跡 `sideeffect_refused site=sentinel` |
| AT-SE-14 | 14 | openitems 到點入口、`patrol_housekeeping`／`alert` 帶沙盒 cwd；`notify` 與 `enqueue` 以 spy 替換；`ENV` 通知開啟 | 案例執行 0 次、自拆；`notify`／`enqueue` 0 次；兩條痕跡 |
| AT-SE-15 | 20、21、22 | `ENV` 設 3 個居所鍵；設 0 鍵；`apply_job_env(["--job-env","FOO_DIR=x"])`；七個 job argv 建構函式 | 3 個旗標固定序／`[]`／rc 2；七者 argv 皆含 `job_env_argv` 結果、0 鍵時與修改前逐字相同 |
| AT-SE-16 | 20 | AST 普查 `tools/lib/**`；於 tmp 複本注入新字面 `AUTOSDD_NEWTHING_DIR` | 現況綠；注入後紅並點名檔案 |
| AT-SE-17 | 07、22 | AST 普查 tools 產品碼；tmp 注入五個函式：①`CREATE_NEW_CONSOLE` ②`getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10)` ③`creationflags=0x10` ④`subprocess.run([shutil.which("claude") or "claude", "-p", "x"])` ⑤`def f(claude="claude"): runner([claude, "-p", "x"])`，皆未呼叫判準；另在 `CLAUDE_PRESENCE_ONLY` 加一列無 WHY | 現況：普查集合＝`SITES`（含 `probe_quota` 呼叫者、`patrolrun.launch`、SI `patrol` 入口）且每個都呼叫判準；`selfimproving/sched.py` 的存在檢查只在 `CLAUDE_PRESENCE_ONLY`；五種注入與無 WHY 列各自紅；偵測器與 `interactive.yields_claude` 為同一函式物件；r4：普查只掃 D-22 的 glob（在 `tools/probe/` 與 `tools/tests/` 的 tmp 複本注入①不紅、在 `tools/lib/` 注入紅）；擴充後 InteractiveWindowEntryLockTest 綠且新命中逐筆登記 |
| AT-SE-18 | 23 | `Sandbox.env()`；AST 掃 realverify 原始碼 | 7 鍵皆在家目錄下、通知鍵＝空、哨兵鍵＝1；全庫無 `real_traces`；`Path.home()`／`".autosdd"` 只在允許表；r4：`ctl_env()` 回傳含 `AUTOSDD_SENTINEL_OFF=1`、`ctl_env(arm_sentinel=True)` 才無此鍵；AST：`arm_sentinel=True` 的每個呼叫點上方三行內有 `# WHY` 註解 |
| AT-SE-19 | 30、31 | 假副作用函式斷言 `intent` 列已存在；`replay`：①主人死 ②主人活且 `expires_at` 已過 ③主人建立時間讀不到且已過期；process 命令列含沙盒 sid／含 `--fork-session` 與舊 sid／不含；第二次 replay 時 unverified 的 pid 已不在 | intent 先於副作用；①撤、序 process→sched→worktree→目錄 ②**不撤** ③撤；不含者記 `unverified`、kill 0 次；第二次轉 `revoked`；結尾 `closed` |
| AT-SE-20 | 33 | 帳中有一列撤銷必失敗（`SCH.disarm` 回非 0） | `run` 不執行任何案例、rc 2、末行 `REALVERIFY_VERDICT=fail reason=orphans` |
| AT-SE-21 | 41 | 案例期間假家目錄 `handoff/` 新增一個與沙盒無關 sid 的檔；批次層：批次期間新增 `AutoSDD_OpenItem_OI-x` 排程與無關痕跡行，另一組新增含本批 run_id 的檔 | 案例 pass、notes `SNAPSHOT-NOISE`；批次第一組不 fail（notes），第二組 `REALVERIFY_VERDICT=fail reason=leak` |
| AT-SE-22 | 40、41 | 假 `~/.claude.json` 案例期間新增一個與沙盒無關的鍵；值內放哨兵字串 | 案例 fail `SIDE-EFFECT LEAK`；快照輸出不含哨兵字串 |
| AT-SE-23 | 31、41 | 案例在 `~/.claude/projects` 建沙盒 slug 目錄、`close()` 刪除；spy 記錄 `close()` 內呼叫序 | pass（後快照在清理之後）；`revoke` 是 `close()` 的第一個呼叫，早於任何 disarm／kill／rmtree |
| AT-SE-24 | 51 | AST／字面普查 `tools/**`、`.claude/hooks/**` 寫檔呼叫的目標 | 無任何寫入 `.claude.json`；tmp 注入 `Path.home()/".claude.json"` 的 `write_text` ⇒ 紅 |
| AT-SE-25 | 50 | `grant_side_effects(window=True)`：一般 `Sandbox`；`WorktreeSandbox(trust_verdict="ready")` | `NotTrusted`／成功且身分檔 `window=true` |
| AT-SE-26 | 32 | `SCH` 列出 Action 含沙盒根的工作：主人死／主人活；tmp 家目錄無身分檔 mtime 301 分前／5 分前；projects 目錄有活 session cwd；（r5）`SCH` 列出 `AutoSDD_Sentinel_<sid>`，Action 含 `AutoSDD_RVprod_<run_id>`：該 run 帳主人活／主人死／帳不存在／帳 `closed`；Action 只含一般正式 repo 路徑（無兩種前綴）的 `AutoSDD_Sentinel_*` | 撤／留；刪／留；跳過；留／撤／撤／撤；不動（不屬發現式掃描） |
| AT-SE-27 | 34 | AST 掃 realverify 套件撤銷呼叫 | 只在 `leases.py`；舊四函式僅委派 |
| AT-SE-28 | 36 | `FS` 兩份帳：一份 `state=made` 主人死、一份 `closed`；跑 `sessionctl status` | 印 `realverify 孤兒 n=1`；所有檔 mtime／位元組不變；sessionctl 套件無 `realverify` import |
| AT-SE-29 | 35 | `sweep`（`FS`）；`--legacy`；`--legacy --apply`（假家目錄放 X1～X8 對應檔） | 末行判決、rc 0；`--legacy` 不改檔；`--apply` 只刪 X1～X5、X7，X6／X8 位元組不變 |
| AT-SE-30 | 52 | `trusted_sandbox`（假 prober、假 git）＋`open_window`（`RUN`） | 帳含 sandbox_root（外層）、worktree、process（探針）、temp_file（debug log）、process（視窗，鍵＝沙盒 sid）各列，順序 intent 先 |
| AT-SE-31 | 15 | `_cmd_fire` 正式目標（tmp 正式 repo、pkg 同根）＋`RUN` | 痕跡序列與修改前黃金序列逐字相同；無 `sideeffect_*`。黃金序列 S2 先以 QW Q3 前的序列釘；**QW Q3 改 `_cmd_fire` 後由 Q3 同一 commit 重釘**（DES §10.2-9） |
| AT-SE-32 | 61 | token 級普查 REQ-SE-61 範圍（字串與 AST 串列兩種）；tmp 注入 `["python","tools/realverify.py","run","--all"]` 與 `realverify.py run --all --long` | 現況 0 筆；兩種注入各自紅 |
| AT-SE-33 | 42 | 兩份合成快照 `--diff` 有／無 tokens 檔 | 有 tokens：只列含字樣項；無：全列；rc 0 |
| AT-SE-34 | 60 | `git show <修憲前 SHA>:<PRD>` 對工作樹 PRD | 修憲前每行在新檔中逐字存在且相對次序不變，例外限 REQ-SE-60 三 hunk 且符合子序列判準；新增行只落在附錄 A 五處＋豁免來源所列並行追加；把任一舊行刪一字的突變輸入 ⇒ 紅 |
| AT-SE-35 | 21、24 | `job_env_argv`：模式 `notify`、通知空、哨兵 1、`AUTOSDD_UNATTENDED=1`；`apply_job_env`：通知 `1`、哨兵 `0`、模式 `xyz`、`AUTOSDD_UNATTENDED=1`；AST 鎖②：tmp 在 `Sandbox.env()` 加未分類鍵 | 前者產 3 旗標、不含 UNATTENDED；後者四者皆 rc 2；注入後紅 |
| AT-SE-36 | 25 | park `job_argv` 與標記、`handoff --spawn`、planner 續跑／`--probe-quota`（`--claude` 與別名 `--probe-command` 各一次）、SI `patrol`／`sched arm`：有／無 `--claude`；`fakeclaude.build`（`PS` 縫記錄指令） | 有：argv 帶 `--claude <path>`、標記 `claude` 欄＝path、傳到 runner／subprocess argv[0]；別名與 `--claude` 結果相同；無：argv 與標記與修改前逐字相同；build 指令含 `-OutputType WindowsApplication`、輸出在家目錄、先寫 `temp_file` intent |
| AT-SE-37 | 26 | `FS`：居所值指向不存在的 `…\AutoSDD_RV_sbx_gone\traces`；同一 argv 經 `tools/sessionctl.py` 入口 | rc 9、stderr 一行；`FS` 前後檔案與目錄集合完全相同（未重建 `AutoSDD_RV_sbx_gone`）；無任何痕跡 |
| AT-SE-38 | 16 | `_cmd_fire` 沙盒無租約；holder、sleep、`park_attempt` 寫入、handback 寫入、`enqueue`、`notify` 皆 spy；另以標記 `refused` 跑 `_sentinel_tick` | holder 讀 0、sleep 0、上列痕跡 0、handback 0、enqueue 0、notify 0；標記 `refused`；tick 不接手（無 `sentinel_park_takeover`） |
| AT-SE-39 | 17 | （隨 QW Q3 落地）`spawn_resume(fork=True)` 無租約／有租約＋`RUN`；§7.3 重排在 `fire' > allow_until`／`≤`；`leases` 行程比對對 `claude -r <sid> --fork-session …` 命令列 | （r5）無租約：rc＝`sandbox_scope.RC_SIDEEFFECT_REFUSED`（以常數比對，非字面）、stderr 與痕跡 `sideeffect_refused` 的 reason＝`sandbox_no_lease`、RUN 0／有租約：argv 含 `-r <sid> --fork-session`；重排（登記站點）rc 4＋stderr 與痕跡 reason `lease_shorter_than_fire`、不登記／登記帶 `EndBoundary`；比對成立 |
| AT-SE-40 | 03、18 | `register_verdict`：`fire_at = allow_until − 1 分`／`+1 分`；登記後再 `grant` 延長 | allow／`lease_shorter_than_fire`；延長後已登記 XML 的 `EndBoundary` 不變 |
| AT-SE-41 | 37 | `ENV` 設 `AUTOSDD_HANDBACK_DIR`／`AUTOSDD_TRACE_DIR` 指向 tmp；帳一列撤不掉 ⇒ `run`；之後 `sweep --abandon <id> --why "測試人工出口"`、`--why "短"`（`PS`／`SCH`／rmtree 皆 spy）；再 `run`；另一組：abandoned ident＝沙盒根，發現式掃描回報該根（大小寫、斜線形態不同）與其子目錄 | handback 檔在 tmp 居所（假家目錄真 `handback/` 無新增）且列 ident 與 `--abandon` 指令；`enqueue` 依開關呼叫；短 why rc 2；abandon 期間 kill 0、disarm 0、rmtree 0；abandon 後帳 `closed`、`run` 不再拒跑且該 ident 撤不掉只記 note；發現式掃描兩項皆只記 note、`run` 不拒跑 |
| AT-SE-42 | 40 | `FS`：真 `context_feed/` 既有檔 `x.json` 案例期間被覆寫成含沙盒 sid 的內容（大小相同、mtime 改）；另一既有檔被覆寫成無關內容 | 前者 fail `SIDE-EFFECT LEAK`；後者 notes `SNAPSHOT-NOISE` |
| AT-SE-43 | 16 | 標記 `status=refused`（含 reason）：`park.read_marker`、`park --status`、`park.yields`、`park.stop_verdict`（短窗達準備門檻）、SessionStart 公告函式 | `read_marker` 回該標記（非 None；`"refused" in park.STATUSES`）；status 印 `refused` 與 reason；yields False；stop_verdict 推回（不當續航憑證）；公告一行含「產品面拒絕」、不含失敗字樣；四者皆不拋例外 |
| AT-SE-44 | 25 | `_cmd_fire`（沙盒有租約、`--claude <假>`、`S` 不替換 spawn 函式、`RUN` 縫）：F4 判 RESUME／判 FRESH 兩組；（隨 QW Q3）§7.5 第一路失敗後走另一路、§7.4 fork、§7.6 接手（標記 `claude` 欄＝假） | 每一次 `RUN` 呼叫的 argv[0] 皆＝假 `claude`；FRESH 組 `handoff.spawn` 收到的 `claude` 參數＝假；無 `sideeffect_refused` |
| AT-SE-45 | 08 | `target_verdict(exe=…)` 矩陣：沙盒有租約 × exe ∈ {None〔非 spawn 類〕、`"claude"`、家目錄外絕對路徑、家目錄下 `bin/claude.exe`（大小寫異）、`..` 逃出家目錄的路徑} × `window` ∈ {false, true}；正式目標 × `"claude"` | 非 spawn 類 allow；`"claude"`／家外／`..` 逃出 且 window=false ⇒ `sandbox_real_exe`；window=true 皆 allow；家下 allow；正式 allow production；判準不查 PATH（`ENV` 改 PATH 前後判決相同） |
| AT-SE-46 | 27 | `fakeclaude.decide` 全表：模式 {resume_ok, fresh_ok, fail, 缺席} × argv {`-r S P`、`P`、`-r S --fork-session P`} × projdir {有, 缺} × rc 檔 {缺, 0, 3} | resume_ok 只對 `-r S P` 回「追加 S.jsonl＋存活」；fresh_ok 對 `P` 與 fork 回「新建＋存活」；其餘與 projdir 缺席回「立即結束 rc＝檔值或 1」；C# 原始碼產生器輸出包含表中每一列（由同一張表產生） |
| AT-SE-47 | 38 | `runner` 解析 `--all` 的案例清單；`--family sideeffect` | `--all` 清單與 `sideeffect`／`sideeffect_selftest` 交集為空；`--family` 可指名；`cases.json` 中兩家族的每個 id 都不在 `--all` |
| AT-SE-48 | 21、26 | `apply_job_env(["--job-env","AUTOSDD_TRACE_DIR=X","runlong","--","x","--job-env","Y=1"])`；`job_env_argv` 於 `ENV` 通知＝`1`、哨兵＝`0` 時由 park／oldwin／SI 登記站點對**沙盒目標**呼叫；AST 收集五個入口（含其分派的 `tools/lib/sessionctl/**`、`engine_resume_job.py`）全部 `return`／`sys.exit` 整數字面與 `_RC_*`／`_USAGE_RC` 常數 | `--` 之後原樣保留（含第二個 `--job-env`）；登記站點 rc 2、`arm` 0 次、stderr 含鍵與值；`RC_RESIDENCE_MISSING`＝9 與 `RC_SIDEEFFECT_REFUSED`＝10 皆不在收集集合內、兩者互不相等（r4） |
| AT-SE-49 | 15、21 | （r4，D-20）正式目標（tmp 正式 repo）與沙盒目標各一：`ENV` ①通知＝`1` ②哨兵＝`""`（顯式空）③模式＝`xyz` ④無任何鍵；park／oldwin／SI 三個登記站點 | 正式：①②③④皆登記成功、job argv 與修改前黃金檔逐字相同（不含任何 `--job-env`）、無 stderr、無 `sideeffect_*`；沙盒：①③ rc 2、`arm` 0 次、stderr 點名鍵與值；② 視同未設（不產哨兵旗標、不拋）；④ 只產沙盒預設鍵 |
| AT-SE-50 | 11、16 | （r4，D-24）`_cmd_fire`（沙盒有租約、`--claude <假>`）：F4＝FRESH 而 `S["spawn"]` 回 `RC_SIDEEFFECT_REFUSED`；F4＝RESUME 而 `S["resume"]` 回同值；對照組 spawn 回 1；`handback` 寫入、`enqueue`、`notify`、`spawn_resume`／`handoff.spawn` 呼叫次數皆 spy | 前兩組：標記 `refused`（reason 帶 spawn 站點理由）、handback 0、enqueue 0、notify 0、spawn 函式各只被呼叫 1 次（無另一路）、自拆 1 次、rc 0、痕跡無 `park_resume_failed`／`park_spawn_failed`；對照組：標記 `failed`、handback 1（Q3 後依 QW §7.5 另走一路） |

## 4. 真機 E2E（全部做成 RealVerify 家族 `sideeffect`，id `RV-SE01`～`RV-SE18`）
共通：沙盒＝`realverify.sandbox.Sandbox`（`install_tools` 複製工作樹 `tools/`，排程 job 的 argv0 在沙盒內，與事故同形）；假 `claude`＝`<家>/bin/claude.exe`，預設模式 `fail`，正控才改 `resume_ok`／`fresh_ok`，且正控一律同時斷言沙盒痕跡 `park_route` 的 route 與所設模式一致（route 不符＝FAIL，不是 ENV）；排程一律真 schtasks；**主人行程**＝背景啟動的 `python tools/realverify.py run --case RV-SE-OWNER`（建沙盒、建假 `claude`、授與租約、`park --at … --claude <家>/bin/claude.exe`、寫 `ready` 檔後睡眠），E2E 以 `taskkill /F /PID <主人 pid>`（**不帶 /T**）殺之；「沒有開窗」判準＝到點前 10 秒至到點後 60 秒每 2 秒查 `Win32_Process`：無任何命令列含沙盒 sid 的真 `claude` 行程，且 `EnumWindows` 查無屬假 `claude` pid 的可見頂層視窗；「假 claude 呼叫次數」＝`<家>/fakeclaude.jsonl` 行數；每個 E2E 結尾跑 `python tools/realverify.py sweep` 並斷言 `SWEEP_VERDICT=clean`；無任何人工按鍵。**r4 共通**：①「到點」一律指標記 `backup_fire_at`（QW Q3 前＝`--at` 值；Q3 後＝`--at`＋`BACKUP_GRACE_MIN` 10 分，DES §10.2.1 X-11），案例讀標記或 `Get-ScheduledTaskInfo` 的 `NextRunTime` 決定等待，不寫死；租約檢查一律以實際登記時刻比 `allow_until`。②`park_attempt`：QW Q3 前 0 筆、Q3 後每次 spawn 嘗試 1 筆（X-12）；凡寫「恰 1 筆」者在 Q3 前讀作 0 筆，重釘由 QW Q3 同 commit 負責（DES §10.2-9）。③沙盒建好後、任何產品指令前先斷言 `git status --porcelain` 為空（DES D-23），不空判 FAIL「沙盒髒」，不是 ENV。④L1 拒絕的 rc 一律連 reason 一起斷言（spawn 站點以 `RC_SIDEEFFECT_REFUSED` 常數、登記站點 rc 4＋stderr reason＋`sideeffect_refused`）。

| E2E | REQ | 載具 | 斷言 |
|---|---|---|---|
| E2E-SE-01 **重放本案（證明一）** | 01～06、08、10、12、15、16、24～27 | 主人行程建沙盒；把 T57 L1～L27 真實行複製到沙盒 slug 的 projects 目錄（檔名＝沙盒 sid）；沙盒內 `handoff --build`／`--finalize`；`grant(120 分)`（驗存成 +30）；`park --at <now+2 分> --claude <假>`（產品正式前綴；到點＝標記 `backup_fire_at`，Q3 後約 +12 分，仍 ≤ allow_until）。變體：(a) 殺主人後等到點；(b) 主人活、到點前 `revoke`；(c) 以 repo 本體的 `tools/sessionctl.py park --fire`（真 tools）經 `AutoSDD_RV_` 前綴真排程觸發，argv 帶 `--job-env`（7 居所指向沙盒、通知空、哨兵 1）＋沙盒 pkg＋`--claude <假>`；(c′) 同 (c)，到點前刪 pkg 檔（家目錄保留）；(d) 到點前刪沙盒家目錄（沙盒 tools 複本）；(e1) RESUME 正控：主人活、租約有效、`--job-env AUTOSDD_SESSION_SWITCH_MODE=auto`、替身 `resume_ok`（T57 L1～L27 含 usage 記錄、時間戳原樣＝冷、上下文小 ⇒ F4 判 RESUME；案例登記前以同一輸入呼叫 `park.fire_route` 預算，不是 RESUME 就改取更短前綴直到是，前綴行數入證據檔）；(e2) 同 (e1) 但模式 `notify`；(e3) FRESH 正控：同 (e1) 但複製進沙盒的逐字稿剝掉全部 usage 記錄（上下文量不到 ⇒ F4 判 FRESH）、替身 `fresh_ok`；(f) 登記後以 `grant(until=now+1 分)` 縮短，到點時已過期；(g) 刪身分檔、保留家目錄；(h) 同 (c)，到點前刪沙盒家目錄；(i) 同 (e1) 但 `--claude` 指向**家外替身**（DES §4.4，`%TEMP%\AutoSDD_RVout_<run_id>\bin\claude.exe`，模式 `resume_ok`） | 身分檔在 `.git` 之前建立；登記的工作 XML `EndBoundary`＝allow_until ≥ StartBoundary；(a) 沙盒痕跡 `park_job_start`→`sideeffect_refused reason=sandbox_owner_dead`、無 `park_route`／`park_yield_primary`／`park_attempt`／`park_chain_failed`、沙盒 handback 目錄與通知佇列檔無新增、沒有開窗、假 claude 0 次、工作已自拆、標記 `refused`；(b) `sandbox_no_lease`；(c) `root_mismatch`；(c′) `target_missing`；(d) `LastTaskResult≠0`、沒有開窗、家目錄未被重建、下一次 `sweep` 撤掉該工作；(e1) `park_route route=RESUME`、假 claude **恰 1 次**（argv 含 `-r <沙盒 sid>`、cwd＝沙盒根）、沙盒逐字稿多一行替身記錄、`park_resumed`、標記 `fired`、`park_attempt` **恰 1 筆且 `attempted=true`**（QW Q3 前 0 筆，r4）、無 `park_resume_failed`／`park_chain_failed`、沙盒 handback 無新增、無可見視窗、無 `sideeffect_*`；(e2) 有 `park_route`、因模式拒絕、假 claude 0 次（證明模式由 `--job-env` 帶到 job）；(e3) `park_route route=FRESH`、假 claude **恰 1 次**（argv 不含 `-r`、含沙盒交接包路徑、cwd＝沙盒根；**證明 FRESH 路也用同一替身**）、沙盒 projects 目錄多一個新逐字稿、`park_spawned`、標記 `fired`、`park_attempt` 恰 1 筆 `attempted=true`（Q3 前 0 筆）、無 `park_chain_failed`、無 `sideeffect_*`（前置：沙盒 porcelain 空，否則 FRESH 被 `handoff._refusals` 拒）；(f) `sandbox_lease_expired`；(g) `sandbox_unreadable`；(h) `LastTaskResult=9`（`RC_RESIDENCE_MISSING`，與入口其他 rc 不撞號）、家目錄未被重建、真痕跡新增段無沙盒字樣；(i) `sideeffect_refused reason=sandbox_real_exe`、家外替身記錄 0 行、沙盒替身 0 行、標記 `refused`、無失敗鏈痕跡、工作已自拆；全部變體：真 `~/.autosdd/{handoff,handback,traces}` 無新增含沙盒 sid 項（快照）；到點 job 跑在排程器真環境 |
| E2E-SE-02 **中途 taskkill（證明二）** | 30～34、36 | 背景 `run --case RV-SE-SEED`：建沙盒（帳）、`sched.register_once` 一支 `AutoSDD_RV_` 工作（+60 分）、經產品 `park --at`（+10 分，租約 30 分；r4：QW Q3 後登記於 `backup_fire_at`≈+20 分 ≤ allow_until，`+20` 會被 `lease_shorter_than_fire` 拒）、啟動睡眠子行程（命令列含沙盒 sid，cwd 沙盒）、另以 `Register-ScheduledTask` 直接建一支 Action 含沙盒根但**不記帳**的工作，寫 `ready` 後睡；見 ready 即 `taskkill /F /PID <runner>`；隨即 `sessionctl status`；再跑 `run --case RV-SE-NOOP`；最後 `sweep` 兩次 | kill 後三支工作、沙盒根、睡眠行程皆存在；`status` 印 `realverify 孤兒 n=1` 且其後三支工作仍在；`RV-SE-NOOP` 輸出開頭列出 revoked 項、其後三支工作查無、沙盒根不存在、睡眠行程不在、projects 沙盒 slug 不存在、帳檔 `closed`；兩次 `sweep`＝`clean`；`RV-SE-NOOP` PASS |
| E2E-SE-03 **全批快照差異為空（證明三）** | 23、33、38、40、41、51 | `snapshot --out before.json`；`python tools/realverify.py run --all`（非 long）；`snapshot --out after.json`；`snapshot --diff before.json after.json --tokens <本批所有 run 帳推得的字樣>` | `run --all` 的案例清單不含任何 `RV-SE*`（結果帳本批無 `sideeffect`／`sideeffect_selftest` 列；不遞迴）；`run` 開頭重放無孤兒；無任何案例 detail 含 `SIDE-EFFECT LEAK`；整體 diff 含字樣項＝0；`~/.claude.json` 鍵名集合前後相同；本批所有帳檔 `closed`；`REALVERIFY_VERDICT` 不因 `reason=leak`／`orphans` 失敗 |
| E2E-SE-04 | 06、12、18 | (a) 主人活；租約 30 分；`park --at <now+3 分> --claude <假>`；登記後 `revoke`；(b) 租約 30 分、`park --at <now+40 分>`；(c) 租約 30 分、`park --at <now+3 分>`、登記後 `Disable-ScheduledTask`，等過 `EndBoundary` 後輪詢 15 分；(d) 案例宣告 `lease_minutes=300`：`grant(200 分)`、`grant(400 分)` | （r4：`park --at +3` 的到點＝`backup_fire_at`，Q3 後約 +13 分仍 ≤ 30；`+40` 的到點 Q3 前 +40、後 +50，皆 > 30）(a) XML 有 `EndBoundary` ≥ StartBoundary；到點 `sandbox_no_lease`、自拆、假 claude 0 次；(b) rc 4＋stderr `lease_shorter_than_fire`＋`sideeffect_refused`、`Get-ScheduledTask` 無新工作；(c) 依 DES §0.4-4 探針結論為判準：工作在時限內被 OS 刪除（實測秒數入帳）；(d) 存 +200／+300 |
| E2E-SE-05 | 11 | 沙盒、無租約、模式 auto：真跑沙盒內 `python tools/sessionctl.py handoff --spawn <pkg> --claude <假>`；`park --fire` 走到 `spawn_resume` 的變體（以有效租約通過 `_cmd_fire`、spawn 前 `revoke`，由案例以 spy 掛點觸發） | `handoff --spawn` 行程 rc＝10（`RC_SIDEEFFECT_REFUSED`，r4）、stderr 含 `sandbox_no_lease`；`park --fire` 變體：標記 `refused`、無 handback、無另一路嘗試、job rc 0；兩者皆沒有開窗、假 claude 0 次、無 `.spawned`／`.resumed`、痕跡 `sideeffect_refused` |
| E2E-SE-06 | 07、08、12 | (a) 沙盒無租約：真跑 `park --at`、oldwin 重試排程、`session_resume_planner.py --arm-sentinel`、`openitems.py` 驅動登記、`engine_resume_job` 武裝、`selfimproving.py` 排程動詞；(b) 再以有租約各跑一次；(c) headless／SI 站點：沙盒內真跑 `session_resume_planner.py --probe-quota` 與 `selfimproving.py patrol`（沙盒 SI 居所預置一個已到期的運轉，使巡邏會走到 `patrolrun.launch`），各三組——無租約＋沙盒替身、有租約＋家外替身、有租約＋沙盒替身（`fail` 模式） | (a) 全部 rc 4 且 stderr 含 `sandbox_no_lease`、各站點 `sideeffect_refused site=<站點>` 一列、無新工作（r4：只看 rc 4 不算）；(b) 各工作 XML 帶 `EndBoundary`、Arguments 含 `--job-env`，`sweep` 撤後查無；站點清單＝`SITES` 中 register 類全部（逐一對表）；(c) 第一組 `sandbox_no_lease`、第二組 `sandbox_real_exe`，兩組替身記錄皆 0 行、無 `claude` 行程；第三組沙盒替身恰 1 行（證明判準放行後確實用 `--claude`，不是因別的理由沒起）；三組皆只寫沙盒居所，真 `~/.autosdd/selfimproving`、真 traces 新增段無沙盒字樣 |
| E2E-SE-07 | 13 | 沙盒有租約武裝哨兵後 `revoke`；放合成 halt 標記使 `--sentinel-tick` 要 probe／resume；真排程觸發 tick | 沒有 `claude -p` 行程（命令列含沙盒 sid）；哨兵自我解除；沙盒痕跡 `sideeffect_refused site=sentinel` |
| E2E-SE-08 | 14 | 沙盒行程環境把通知鍵設為開啟、無租約：觸發 `patrol_housekeeping` 的準備帶通知分支；openitems 到點入口對沙盒項目 | 沙盒痕跡 `sideeffect_refused site=notify`／`site=openitems`；通知佇列檔無新增；openitems 案例未執行、工作自拆。誠實劃界：toast 本身量不到；若判準被拿掉（突變實跑），可能出現一則非模態 toast（自動消失、不需按鍵），入證據檔 |
| E2E-SE-09 | 15、21、25、27 | 正式目標替身：`%TEMP%\AutoSDD_RVprod_<run_id>` 拋棄式 git repo（名稱非 `AutoSDD_RV_sbx_`、無身分檔；本 E2E 先把該 repo 與其 `~/.claude/projects/<slug>` 登記進自己的 L2 帳再動作，收尾撤）裝入 tools、以 D-23 同一輔助函式寫 `.git/info/exclude`、假 claude（`<repo>/bin/claude.exe`，`projdir`＝該 slug 目錄）、一份含 usage 的小逐字稿；居所經 `--job-env` 指向替身內。**前置（r5，B-P3-1）**：先跑 AT-SE-44（QW Q3 落地後另加 AT-QW-71）；任一紅 ⇒ 本 E2E 判 ENV、不登記任何排程（防 Q3 迴歸漏傳 `--claude` 時在不受 L1 保護的正式替身 repo 開真窗）。(a) 模式 `notify`、登記行程設 `AUTOSDD_SENTINEL_OFF=1`（r5，D-27）；(b) 模式 `auto`、替身 `resume_ok`、登記行程設 `AUTOSDD_SENTINEL_OFF=1`（r5）；(c)（r4，D-20）登記行程環境另設 `AUTOSDD_DESKTOP_NOTIFY=1` 與顯式空 `AUTOSDD_SENTINEL_OFF=`（不設 1），其餘同 (a)（**模式 `notify`：到點只到 `park_route` 後即因模式拒絕，不 spawn、不進失敗鏈，故標記 `desktop_notify`＝1 也不會呼叫 `notify`、不會敲 toast**，r5，B-P3-2）；**(c) 先把 `AutoSDD_Sentinel_<替身 sid>` 以 `sched_job` 記入本 E2E 的 L2 帳（`intent`，撤銷法＝`Unregister`＋回讀）再 `park`**（r5，D-27：QW §7.1 Q3 後 park 登記會在正式命名空間武裝它，正式目標不帶 `EndBoundary`）；皆 `park --at <now+2 分> --claude <假>`。**(b) 防真窗（r4，第三輪 QA P1-1）**：登記前以同一逐字稿、同一 now 呼叫 `park.fire_route` 預算，結果非 RESUME 即截短逐字稿重算直到 RESUME（行數入證據檔），否則判 ENV 不登記；登記成功後在 repo 根寫一個**不在 exclude** 的未追蹤檔 `RVPROD_DIRTY.txt`、HEAD 不打 `*-wip-preserved` ⇒ 到點任何 FRESH 嘗試（F4 漂移、或 QW §7.5 另一路）都被 `handoff._refusals` 在 runner 之前拒絕 | 工作 XML **無** `EndBoundary`；(a) 痕跡序列＝`park_job_start`→`park_route`→模式拒絕、假 claude 0 次；(b) `park_route route=RESUME`、假 claude 恰 1 次（argv 含 `-r`）、cwd＝替身 repo、`park_resumed`、`park_attempt` 恰 1 筆 `attempted=true`（QW Q3 前 0 筆）、無 `park_chain_failed`；**若有任何 FRESH 嘗試，必以前置拒絕收場**（`park_attempt` 該列 reason 含 dirty／wip、該次 runner 呼叫 0 次、替身記錄只有 RESUME 那 1 行），假 claude 記錄出現不含 `-r` 的行 ⇒ FAIL；(a)(b)（r5）park 末行 `sentinel=absent`（QW Q3 後；Q3 前無此欄）、`Get-ScheduledTask` 查無 `AutoSDD_Sentinel_<替身 sid>`；(c) 登記 rc 0、Arguments 不含 `AUTOSDD_DESKTOP_NOTIFY`／`AUTOSDD_SENTINEL_OFF`（r5：與 (a) 的 Arguments 去掉 `--job-env AUTOSDD_SENTINEL_OFF=1` 一組後逐字相同）、無 stderr；QW Q3 後另斷言標記 `desktop_notify`＝`1`（登記行程原值，QW S-17；由 Q3 同 commit 補釘，DES §10.2-9）；（r5，D-27）QW Q3 後 park 末行 `sentinel=armed`、`AutoSDD_Sentinel_<替身 sid>` 的 `NextRunTime` 非空（證明真的武裝過），隨即由本 E2E 撤除、回讀查無、L2 該列 `revoked`；QW Q3 前斷言該工作不存在、L2 該列直接記 `revoked`；通知 sink 0 則（模式 notify 不進失敗鏈）；三者無 `sideeffect_*`、與 AT-SE-31 黃金序列一致（QW Q3 後以其重釘版為準）；**真 `traces/*.jsonl` 新增段不含沙盒或替身字樣**（`AutoSDD_RVprod_<run_id>`、替身 sid、run_id；D-9：主控並行寫入不判） |
| E2E-SE-10 | 20、21、22、24 | 沙盒 `park --at`（模式 notify、通知空、哨兵 1）；讀 `Get-ScheduledTask` Action Arguments；到點；repo 本體以乾淨環境跑 `python tools/sessionctl.py park --status`；跑 `--job-env FOO_DIR=x status`、`--job-env AUTOSDD_DESKTOP_NOTIFY=1 status`、`--job-env AUTOSDD_SESSION_SWITCH_MODE=xyz status`；沙盒行程環境設 `AUTOSDD_DESKTOP_NOTIFY=1` 後真跑 `park --at` | Arguments 含 7 個居所＋3 個開關的 `--job-env` 且居所值在沙盒下；到點事件全落沙盒痕跡、**真 `traces/*.jsonl` 新增段無沙盒字樣**（D-9）；乾淨環境 rc 0；三個非法 rc 2；通知開啟值登記 rc 2、stderr 點名 `AUTOSDD_DESKTOP_NOTIFY`、無新工作（登記時就失敗，不等到點） |
| E2E-SE-11 | 23 | 真跑既有 park／watch／keepwarm 家族案例（`RV-K*`、`RV-PR1`、`RV-PR2` 與 `sessionctl_watch`、`sessionctl_keepwarm`），每案前後快照 | 每案無 `SIDE-EFFECT LEAK`；真 `~/.autosdd/{handoff,handback,plans,context_feed,traces/park}` 無含沙盒 sid 的新檔或改動 |
| E2E-SE-12 | 35 | 真家目錄跑 `sweep --legacy`（不帶 `--apply`）；前後對 `~/.autosdd` 全檔做雜湊清單 | 列出 DES §9 中仍存在的 X 項、rc 0；雜湊清單前後相同；輸出不含 X6、X8 路徑作為刪除對象 |
| E2E-SE-13 | 32、41、42 | 背景 `run --case RV-SE-LEAK`（繞過 env 在真 `~/.autosdd/handoff/<沙盒 sid>.probe` 寫檔，並以 `Register-ScheduledTask` 建一支 Action 含沙盒根的工作且不記帳）；之後 `snapshot --diff` | 案例 `fail`、detail 首行 `SIDE-EFFECT LEAK` 且列出兩項；`snapshot --diff` 也列出兩項；收尾刪 probe 檔、`sweep` 撤該工作後 `clean` |
| E2E-SE-14 | 60、61 | 真 repo：以修憲前 blob 對工作樹 PRD 跑 AT-SE-34 判準；REQ-SE-61 範圍跑 AT-SE-32 判準 | 兩者皆綠（輸出入證據檔） |
| E2E-SE-15 | 50 | 真 `Sandbox.create` 後呼叫 `grant_side_effects(window=True)` | 拋 `NotTrusted`；身分檔 `allow_until` 仍 null；不需宿主信任 |
| E2E-SE-16 | 52 | `interactive.trusted_sandbox`（真宿主、真隱藏探針）＋`open_window(visible=False)` 起 `claude --model haiku`（不帶提示）後收 | 帳依序含 sandbox_root（外層）、worktree、process（探針）、temp_file、process（視窗）並全數 `closed`；worktree 在 `<外層>/wt` 且探針判 ready（證明多一層不影響宿主信任）；宿主 worktree 登記無殘留；**宿主未信任 ⇒ 判 ENV（不是 PASS）** |
| E2E-SE-17 **QW 新站點**（案例隨 QW Q6 落地） | 16、17、25 | 沙盒、假 claude：(a) `spawn_resume(fork=True)`——無租約／有租約（替身 `fresh_ok`、`fakeclaude.sleep=120`），有租約時其後殺主人並 `sweep`；(b) park 標記 holder 活、`wake_at > now`，觸發 §7.3 重排：租約不足以覆蓋新時刻／足以覆蓋；(c) 租約有效、替身 `fail`（`fakeclaude.rc=1`）注入失敗，走 §7.5 失敗鏈（＝改寫後的 E2E-QW-13）；(d) 標記 `refused` 與 `failed`（無租約）兩種，真排程觸發 `_sentinel_tick`；(e) 標記 `failed`、`claude` 欄＝沙盒替身（`resume_ok`）、有租約，真排程觸發 `_sentinel_tick` 接手 | (a)（r5，B-P2-2；兩種觸發分開寫）**(a1) 直接呼叫 spawn 站點**（案例以 `park_cli.spawn_resume(..., fork=True, claude=<假>)` 呼叫，無租約）⇒ rc＝`sandbox_scope.RC_SIDEEFFECT_REFUSED`（以常數比對，非字面）、stderr 與痕跡 `sideeffect_refused` 的 reason＝`sandbox_no_lease`、假 claude 0 次；**(a2) 經真排程 `_cmd_fire` 觸發**（無租約）⇒ fire 站點先拒：痕跡 `park_job_start`→`sideeffect_refused reason=sandbox_no_lease`、標記 `refused`、無 `park_attempt`、fork spawn 呼叫 0 次、假 claude 0 次、工作自拆；有租約假 claude argv 含 `-r <sid> --fork-session`，`sweep` 以命令列比對撤掉該行程（`revoked`，非 `unverified`）；(b) 不足 ⇒ `lease_shorter_than_fire`、無新工作；足 ⇒ 新工作帶 `EndBoundary`；(c) `park_attempt` ×2、假 claude 恰 2 行且兩行 argv[0] 相同（另一路也用同一替身）、`park_chain_failed`、handback 與通知佇列只在沙盒居所、真目錄無新增、無 toast（通知經 `--job-env` 關）；(d) `refused` 不接手；`failed`＋無租約 ⇒ `sideeffect_refused site=sentinel`、無 spawn；(e) 接手的 spawn 打到標記所記替身恰 1 次、無真 `claude` 行程 |
| E2E-SE-18 **拒跑出口** | 31、33、37 | 本 E2E 先建自己的沙盒 H（記帳）作為居所；背景 `run --case RV-SE-LOCK`：建沙盒 X（帳）、記一列 `process`（命令列不含沙盒 sid 的睡眠行程 P1，cwd 在 X 根內使 rmtree 失敗）、寫 ready 後睡；kill runner；記錄真 `~/.autosdd/handback/` 檔名集合與真通知佇列檔（`trace_dir()` 下）位元組長度；以 `H.env()`（7 居所指向 H、通知空、哨兵 1）跑 `run --case RV-SE-NOOP`；`sweep --abandon <run_id> --why "E2E-SE-18 驗人工出口"`（同一 env）；再跑 `RV-SE-NOOP`（同一 env）；`taskkill /F /PID <P1>`；`sweep` | 第一次 NOOP：rc 2、`reason=orphans`、`<H>/handback/realverify_orphans_<run_id>.md` 存在且列 ident 與 `--abandon` 指令、H 的通知佇列無新增（通知關）、P1 未被砍（`unverified`）；abandon 期間 P1 仍活、X 根仍在（abandon 不動行程與檔）；abandon 後帳 `closed`；第二次 NOOP PASS（帳列與發現式掃描到的 X 根皆只記 note）；殺 P1 後 `sweep` 刪除 X 根、`clean`；**全程真 handback 檔名集合與真佇列位元組長度前後相同**；收尾撤 H（寫真 handback 的正向路徑由 AT-SE-41 以 tmp 居所驗） |

## 5. 突變（MU；每條必須讓指定測試轉紅）
突變實跑一律在帶假 `claude` 的 E2E 上進行：「判準被拿掉」的突變轉紅證據是假 claude 被呼叫或痕跡出現 `park_route`，**不會開出真 claude 視窗、不需按鍵**（DES D-14、§13）。

| MU | 突變 | 必紅 |
|---|---|---|
| MU-SE-01 | `is_sandbox` 只認身分檔（拿掉路徑／slug 副證） | AT-SE-02、E2E-SE-01(g) |
| MU-SE-02 | 判準讀 `AUTOSDD_REALVERIFY`／任一 env 作為放行或拒絕依據 | AT-SE-05 |
| MU-SE-03 | 租約有效性不看主人存活 | AT-SE-06、E2E-SE-01(a) |
| MU-SE-04 | `grant` 不套上限 | AT-SE-04、E2E-SE-01（存值斷言） |
| MU-SE-05 | `_cmd_fire` 的判準移到 `fire_route` 之後 | AT-SE-10、E2E-SE-01(a)（假 claude 被呼叫） |
| MU-SE-06 | 拿掉 `root_mismatch` | AT-SE-07、E2E-SE-01(c) |
| MU-SE-07 | 正式目標也帶 `EndBoundary` | AT-SE-11、E2E-SE-09 |
| MU-SE-08 | park `job_argv` 不帶 `job_env_argv` | AT-SE-15、E2E-SE-10 |
| MU-SE-09 | `replay` 砍行程不驗命令列 | AT-SE-19 |
| MU-SE-10 | `run` 開頭遇撤不掉的孤兒仍繼續 | AT-SE-20、E2E-SE-18 |
| MU-SE-11 | 單案快照 diff 把非沙盒字樣差異也判 fail | AT-SE-21 |
| MU-SE-12 | 後快照取在 `ctx.close()` 之前 | AT-SE-23 |
| MU-SE-13 | `grant_side_effects(window=True)` 不呼叫 `assert_trusted` | AT-SE-25、E2E-SE-15 |
| MU-SE-14 | `sessionctl status` 順手撤銷孤兒 | AT-SE-28、E2E-SE-02 |
| MU-SE-15 | `job_env_argv` 不轉送模式鍵 | AT-SE-35、E2E-SE-01(e2) |
| MU-SE-16 | L1 拒絕後仍走失敗鏈（寫 handback／入列） | AT-SE-38、E2E-SE-01(a) |
| MU-SE-17 | 孤兒判準改回「主人不在 ∨ 過期」 | AT-SE-19 |
| MU-SE-18 | `register_verdict` 不比 `fire_at` 與 `allow_until` | AT-SE-40、E2E-SE-04(b) |
| MU-SE-19 | 批次層 diff 全差異判 leak | AT-SE-21 |
| MU-SE-20 | `ctx.close()` 最後才 `revoke` | AT-SE-23 |
| MU-SE-21 | `apply_job_env` 接受通知開啟值 | AT-SE-35、E2E-SE-10 |
| MU-SE-22 | `apply_job_env` 遇居所家目錄缺席仍套用 | AT-SE-37、E2E-SE-01(h) |
| MU-SE-23 | `sweep --abandon` 後 abandoned ident（含發現式掃描的正規化比對）仍計入 `unrevoked` | AT-SE-41、E2E-SE-18 |
| MU-SE-24 | `sweep --abandon` 順手砍行程或刪檔 | AT-SE-41、E2E-SE-18 |
| MU-SE-25 | `_cmd_fire` 的 FRESH 路不傳 `claude` 參數 | AT-SE-44、E2E-SE-01(e3)（r4：D-18 於 spawn 站點以 `sandbox_real_exe` 拒絕、回 `RC_SIDEEFFECT_REFUSED` ⇒ 標記 `refused`、無第 2 筆 `park_attempt`〔不走另一路〕、無 handback、替身 0 行、無 `park_spawned`；不開真窗；E2E 轉紅點＝標記非 `fired`） |
| MU-SE-26 | 拿掉 `sandbox_real_exe` 判準（或不讀身分檔 `window`） | AT-SE-45、E2E-SE-01(i)（家外替身被呼叫 1 次）、E2E-SE-06(c) |
| MU-SE-27 | `run --all` 不排除 `sideeffect` 家族 | AT-SE-47 |
| MU-SE-28 | `refused` 讀取端當成 armed（`yields` 讓路）或當成失敗公告 | AT-SE-43 |
| MU-SE-29 | `apply_job_env` 越過 `--` 繼續剝旗標 | AT-SE-48 |
| MU-SE-30 | `job_env_argv` 遇不允許值靜默略過 | AT-SE-48、E2E-SE-10 |
| MU-SE-31 | 替身成功模式不寫逐字稿或立即結束 | AT-SE-46、E2E-SE-01(e1)／(e3) |
| MU-SE-32 | （r4）`job_env_argv` 對正式目標也拋 `JobEnvValueError`（或對正式目標轉送不允許值） | AT-SE-49、E2E-SE-09(c) |
| MU-SE-33 | （r4）`_cmd_fire`（或 QW §7.5）把 `RC_SIDEEFFECT_REFUSED` 當一般失敗（寫 handback、標 `failed`、改走另一路） | AT-SE-50、E2E-SE-05（`park --fire` 變體） |
| MU-SE-34 | （r5，D-27）發現式掃描不認 `AutoSDD_RVprod_`（只認 `AutoSDD_RV_sbx_`） | AT-SE-26（RVprod 四例） |

## 6. 逐功能 E2E 覆蓋表（每個 REQ ≥1 個真機 E2E）
| REQ | E2E |
|---|---|
| 01 | 01、16 |
| 02 | 01 |
| 03 | 01、04 |
| 04 | 01 |
| 05 | 01 |
| 06 | 01、04 |
| 07 | 06 |
| 08 | 01、06 |
| 10 | 01 |
| 11 | 05、01(e3) |
| 12 | 01、04、06 |
| 13 | 07 |
| 14 | 08 |
| 15 | 01、09 |
| 16 | 01、17 |
| 17 | 17 |
| 18 | 04 |
| 20 | 10 |
| 21 | 09、10 |
| 22 | 10 |
| 23 | 03、11 |
| 24 | 01、10 |
| 25 | 01、09、17 |
| 26 | 01 |
| 27 | 01、09 |
| 30 | 02 |
| 31 | 02、18 |
| 32 | 02、13 |
| 33 | 02、03、18 |
| 34 | 02 |
| 35 | 12 |
| 36 | 02 |
| 37 | 18 |
| 38 | 03 |
| 40 | 03 |
| 41 | 03、13 |
| 42 | 13 |
| 50 | 15 |
| 51 | 03 |
| 52 | 16 |
| 60 | 14 |
| 61 | 14 |

覆蓋率 42／42。E2E-SE-16 依賴 F5 宿主一次性信任；未信任時判 ENV（非 PASS），屬環境前置。E2E-SE-17 的案例程式隨 QW Q6 落地。三項必備真機證明＝E2E-SE-01、02、03。

## 7. 交卷判準（S7 收尾窗口；OI 承接）
規格凍結時，主控以 `python tools/openitems.py open` 登記「實作 1＋E2E 18」共 19 項 OI，把 OI id 回填 PRD §16.6 2026-11-20 第二列（結案格 `〔OI〕`，不用 ⏸；R217 附錄 A-5／A-11）。各 OI 結案條件：
1. **實作 OI**：AT 50／50 綠（AT-SE-39、AT-SE-44、AT-SE-50 的 QW 部分隨 QW Q3 落地，未落地前此 OI 不結）、MU 34／34 各自使指定測試轉紅（突變實跑輸出入證據檔）；根層全套（runlong／waitfor）與 `ruff check tools/ .claude/hooks/` 綠；`Root_Layout` §3 落點鎖、CI paths 覆蓋鎖綠；QA 獨立審查 PASS。
2. **E2E OI（每列一個）**：該 E2E 在 `RealVerify_Result_Ledger.md` 最近一次結果為 PASS（ENV 不算）。E2E-SE-16 若為 ENV，其 OI 維持未結並註明「F5 宿主一次性信任」為唯一前置；E2E-SE-17 的 OI 標註「隨 QW Q6 結案」。
3. PRD §16.6 本列轉 ✅＝19 項 OI 全部結案；DES §9 X1～X5、X7 經主控同意以 `sweep --legacy --apply` 處置並入證據檔；X8 由掌舵者決定。
4. R217 a1／E2E-08（realverify 接 nightly／SI）在第 3 條成立後才准實作（REQ-SE-61 鎖同時解除）。
