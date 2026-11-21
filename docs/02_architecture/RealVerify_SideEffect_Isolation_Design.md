# 真機驗證的副作用隔離（RealVerify SideEffect Isolation）設計稿——載具不得對真環境留下會自己動的東西

> 🔒 **spec-frozen（r5，2026-11-21）**：approver＝掌舵者（常態規則 2026-10-20，sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13；主控執行）；reason＝聯合 QA 第五輪 `r218_joint_specqa5_report.md`（本稿 r5 PASS）、第六輪 `r218_joint_specqa6_report.md`（PASS、無缺陷）；主控親驗 PRD 只追加；與 QuotaWall r8 同 commit 凍結，§10.2.1 X-1～X-22 為兩稿介面單一真相源。

> 角色：SD 系統設計（R218-B，AISDLC 第 2 階段）。**r2**（2026-11-20）：依 SCG 獨立審查 FAIL（P1×1、P2×8、P3×7，scratchpad `r218b_specqa_report.md`）逐條改版，處置見附錄 B。**r3**（2026-11-21）：依第二輪 QA FAIL（P1×1、P2×6、P3×8，scratchpad `r218b_specqa2_report.md`）逐條改版，處置見附錄 C。**r4**（2026-11-21）：依第三輪 QA FAIL（P1×1、P2×4、P3×5，scratchpad `r218b_specqa3_report.md`）逐條改版，並與 QW r6 **聯合改版**（同一 SD 同時改兩稿）：兩稿交叉的介面字面以本稿 **§10.2.1 跨規格介面對照表**為單一真相源，處置見附錄 D。**r5**（2026-11-21）：依聯合 QA 第四輪 FAIL（P2×2、P3×2，scratchpad `r218_joint_specqa_report.md`）與 QW r7 聯合改版：正式目標替身不留哨兵孤兒、L2 加認 `AutoSDD_RVprod_`（D-27）、spawn 站點拒絕一律以 `RC_SIDEEFFECT_REFUSED` 常數連 reason 斷言、§10.2.1 修 X-4／X-11 並補 X-19～X-22，處置見附錄 E。第五輪聯合 QA（本稿 r5 PASS、P3×1）：只補 TCS 表頭 r5 列與「相容＝QW r7／r8」（B5-P3-1），及 X-19 的 `reason=sentinel_off` 字面（隨 QW r8 QW5-P3-2，不改本稿任何 REQ／AT／E2E／MU）。量測基準 HEAD＝`133c3a38`（工作樹另有 R217 期 A 與 R218 F5 未提交實作，見 §10 前置）。
> 輸入：Architect 報告（下稱 **ARC**，scratchpad `r218b_architect_report.md`）、SA 報告（下稱 **SA**，同目錄 `r218b_sa_report.md`）、F6 分析稿（下稱 **F6**，`r218_f6_analysis.md`）、F5 設計稿（下稱 **F5**，`r218_f5_design.md`；已落地未提交 `tools/lib/realverify/interactive.py`）。四檔在 sid 4a45bc75 的 scratchpad，收尾窗口把關鍵段落抄進證據檔。
> 事故逐字稿：`C:\Users\wuwei\.claude\projects\C--Users-wuwei-AppData-Local-Temp-AutoSDD-RV-sbx-78znhvop\57d0ccad-fa1b-4e17-bc44-e31c7642f8a3.jsonl`（下稱 **T57**）；真痕跡 `~/.autosdd/traces/autosdd_session_switch.jsonl`（下稱 **SW**）、`autosdd_sentinel_unloads.jsonl`（下稱 **UL**）。行號＝檔案行號。
> 上游：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`（下稱 **PRD**）。修憲走 §16.5 (i)，本棒已追加修訂表 v2.1.25 列、§11.4 註記、新增 §11.9（R-VER-1～6）、§15.5 紅線 13、§16.6 新列（只追加、修憲前原文一字不動，見附錄 A）。
> 相容：R218 `docs/02_architecture/QuotaWall_CacheContinuity_Design.md` r7／r8（下稱 **QW**；r8 為 QW 第五輪 QA 內部修訂，交叉介面僅 X-19 補 `reason=sentinel_off` 字面；§7.1 `backup_fire_at`、§7.3 job 內重登記、§7.4 `--fork-session`、§7.5 失敗鏈、§7.6 哨兵接手、S-17、E2E-QW-13）。需 QW 同步的項目列 §10.2；兩稿交叉的介面字面列 §10.2.1（QW 引用同一節，不另抄）。
> 驗收規格：`docs/03_testing/contracts/TCS-SideEffectIsolation-20261120.md`（下稱 **TCS**；前綴 `REQ-SE-`／`AT-SE-`／`E2E-SE-`／`MU-SE-`）。
> 本稿新增的程式路徑在實作 commit 前不存在於磁碟；落點依 `docs/02_architecture/Root_Layout_and_Module_Placement.md` §2，實作 commit 時同步登記該檔 §3。

---

## 0. 結論與代決

### 0.1 結論（五句）
1. 57d0ccad 不是「漏清一支排程」，是**隔離手段的射程**問題：現行隔離只有「行程環境變數」與「案例內 finally」兩樣，前者過不了 OS 排程器（job 以登入者真環境執行，env 一個都帶不過去——居所鍵與行為開關〔模式、通知、哨兵〕都一樣），後者過不了行程死亡（撞額度中斷、taskkill /F）（ARC §一；r2 補行為開關面）。
2. 這是一類：SA 普查到沙盒 park 排程進入產品正式前綴 `AutoSDD_HandoffSpawn_*` **17 筆、其中 11 筆被真排程器觸發（9 skip＋2 真 spawn）**（SA §2.3，UL L73～L97），外加 handback、`.checked` 閂鎖、context_feed 三種真目錄外洩與 `~/.claude.json` 兩把失效信任鍵（SA §2.2、§2.4）；`sched=True` 案例 25 個都是潛在外洩點（SA §4.3）。
3. 產品面完全沒有「目標合法性」判準：`park --fire`／`spawn_resume`／`handoff.spawn` 只問「有沒有人在動」「交接包是否 live」，從不問「這個目標是不是一個驗證沙盒、它的主人還在不在」（`park_cli.py:372-435`、`:318-369`；`handoff.py:406-469`）。
4. 結構正解＝四層，依序：**L1 產品面拒絕**（單一判準只吃目標自帶的資料：沙盒身分檔＋租約，不讀環境變數，穿得過排程邊界與行程死亡；拒絕是終局，不進任何失敗鏈或接手）＞ **L4 job 環境允許表帶過排程邊界**（job argv 以 `--job-env` 攜帶 7 個居所鍵＋模式／通知（只准關閉值）／哨兵開關，以 `--claude` 攜帶替身執行檔；撤掉 `real_traces=True` 與「交接目錄不加 env 出口」兩個直通真環境的例外）＞ **L2 先登記後動作的副作用帳＋排程自毀**（下一次任何 realverify 執行開頭自動撤孤兒；主人可驗證存活者永不當孤兒）＞ **L3 每案副作用快照 diff**（新型外洩第一次出現就紅）。
5. 三項真機證明不需人按鍵、不燒額度、**任何 E2E 都不真開 claude 視窗**（正控一律以 argv 帶入的假 `claude` 替身，**每一次 spawn 嘗試都用同一個替身**；L1 另拒「沙盒目標卻要用沙盒外的執行檔且未授權開窗」，**對沙盒目標**忘了帶替身也開不出真窗，r3；r4 限縮：正式目標替身 repo〔E2E-SE-09〕不是沙盒、L1 不管，改以「登記前預算 F4＝RESUME＋登記後刻意留未追蹤檔」使 FRESH 被現行 `handoff._refusals` 在 runner 之前拒絕，D-23）：重放本案（真排程到點 ⇒ 拒開＋自拆）、案例中途 taskkill（下次執行自動撤孤兒）、全批案例前後快照含沙盒字樣的差異為空（TCS §4 E2E-SE-01／02／03）。

### 0.2 主控代決（任務書已定，照做）
| 代號 | 決定 | WHY |
|---|---|---|
| Q-1 | 不改掌舵者全域 `~/.claude.json`；本設計任何程式也不得寫它 | 掌舵者鐵令；F5 已裁 A6e 預植信任為違規 |
| Q-2 | 每個功能真機 E2E、E2E 不得需人按鍵 | 掌舵者 2026-11-18 指令；本輪任務書 |
| Q-3 | PRD 只走 §16.5 追加 | PRD §16.5、§16.6 體例 |
| Q-4（r2） | 排程 job 環境改「允許表」`JOB_ENV_KEYS`：7 個居所鍵＋`AUTOSDD_SESSION_SWITCH_MODE`＋`AUTOSDD_DESKTOP_NOTIFY`（只准關閉值）＋`AUTOSDD_SENTINEL_OFF`，經 job argv 帶過排程邊界；正控一律用 argv 帶入的假 `claude`，任何 E2E 都不得真開窗 | QA P1-1：`switch.switch_mode` 缺席即 `auto`（`switch.py:198-205`）、`notify` 只讀 `AUTOSDD_DESKTOP_NOTIFY`（`quota_escalation.py:551`）——沙盒 env 設的行為開關到了 job 全部不見，與 57d0ccad 同型成因；E2E-SE-01(e)／09 原寫法會在驗收時重演事故 |
| Q-5（r2） | QA P2-1～P2-7 照其建議修法；E2E-QW-13 改用假 `claude` 注入失敗，列為需 QW 同步改項 | 主控裁示 |
| Q-6（r2） | PRD 版號說明與 r3 一致（v2.1.24＝R218 QuotaWall r3 含 R218-C；本稿 v2.1.25）；§16.6 結案格改 OI 標記 | QA P2-8；R217 附錄 A-5／A-11 |
| Q-7（r3） | 第二輪 QA P1：`--claude` 涵蓋**每一次** spawn 嘗試（RESUME、FRESH、fork、失敗鏈另一路、哨兵接手），L1 spawn 類站點加 `sandbox_real_exe` 判準（身分檔 `window` 旗標進判準）；P2-1～P2-6、P3-1～P3-8 照 QA 修法 | 主控裁示（2026-11-21）；QA 報告 `r218b_specqa2_report.md`。WHY：替身只接 RESUME 路時，FRESH 路與失敗鏈仍打真 `claude`（`park_cli.py:428`→`handoff.py:443` 預設 `"claude"`＋`CREATE_NEW_CONSOLE`），E2E 會在未信任沙盒開出停在信任框的真窗——正是本案同型；只靠「每處都記得傳」是紀律，L1 結構判準讓忘記傳也開不出真窗 |
| Q-8（r4） | 第三輪 QA P1-1、P2-1～P2-4、P3-1～P3-5 全照 QA 修法（D-20 改寫、D-21 擴、D-22 擴、D-23～D-26 新增）；與 QW r6 聯合改版，交叉介面以 §10.2.1 為單一真相源 | 主控裁示（2026-11-21，`r218_joint_sd_brief.md`）。WHY：前三輪新缺陷多半是「一邊改介面、另一邊 E2E 沒跟上」，一人同改兩稿並以一張表對齊 |

### 0.3 SD 代決（主控／掌舵者可隨時以 T1 推翻）
| 代號 | 決定 | WHY |
|---|---|---|
| D-1 | 沙盒身分以**沙盒家目錄的身分檔** `.autosdd_sandbox.json` 為主證、路徑段 `AutoSDD_RV_sbx_*`／slug 段 `AutoSDD-RV-sbx-` 為副證；任一成立即「是沙盒」。**家目錄**＝一般沙盒的根；worktree 沙盒的外層（worktree 本身在 `<外層>/wt`，r2）。`is_sandbox` 對給定路徑查「本層或上一層」的身分檔 | 排程 job 跑的是沙盒內 `tools/` 複本（UL L97 argv0 在沙盒），`_REPO` 就是沙盒根——「目標 slug 必須等於本 repo 主 checkout」在這條路上恆成立、擋不住；只有目標自帶的資料能穿過排程邊界。r2：`git worktree add` 要求目的目錄不存在或為空（QA P2-1），身分檔改放外層才建得起來 |
| D-2 | 預設**拒絕**：沙盒目標要放行，必須有租約（`allow_until` 未過期 **且** 主人行程可驗證仍活）；租約由案例當下明示授與，預設上限 `LEASE_MAX`＝30 分；案例可在原始碼常數宣告 `lease_minutes`，上限 `LEASE_CAP`＝300 分（兩者皆程式常數、不開 env） | 安全預設；案例崩潰 ⇒ 主人死 ⇒ 立刻失效。r2：QW 長案例（V-W1 4 小時、park＝醒來＋10 分）在 30 分上限下結構上做不到（QA P2-4）；主人存活是主判準、時限是 pid 重用兜底，放寬到 5 小時的代價只在「pid 重用且建立時間相同」時出現 |
| D-3 | 判準住**單檔共用工具** `tools/lib/sandbox_scope.py`，不建套件 | 呼叫者橫跨 sessionctl 套件、openitems 套件、扁平的 planner／quota_escalation／engine_resume_job；`Root_Layout` §2：套件間不得互 import，只准 import 共用單檔。判準只有一支檔、PRD 無後續階段 |
| D-4 | 判準模組**不讀任何環境變數**（AST 鎖：無 `os.environ`／`getenv`），也不開行程（git 根以「往上找 `.git`」解析，r2） | ARC §五：產品讀 `AUTOSDD_REALVERIFY=1` 自我拒絕＝到點 job 看不到；r2：`git rev-parse` 會吃 `GIT_DIR` 等環境變數且違反「不開行程」（QA P3-2） |
| D-5 | 排程 job 不改沙盒前綴（仍用產品正式名稱，驗的是真路徑）；改以 L1（到點照樣拒）＋L2（登記即可撤）＋**沙盒目標登記時加 OS 自毀**（Windows `EndBoundary`＝租約到期、`DeleteExpiredTaskAfter`＝PT0S） | 前綴只解決「掃得到」不解決「到點照開」；自毀只對沙盒目標加，**正式目標不加**（正式 park 遇睡眠需補跑） |
| D-6 | job 環境轉送用單一旗標 `--job-env <KEY>=<VAL>`（可重複），只轉送**行程環境中顯式設定**且屬 `JOB_ENV_KEYS` 的鍵，值受各鍵允許值約束；入口最先套用；正式環境無顯式值 ⇒ argv 逐字不變 | 統一形態取代 oldwin／openitems 各自的 `--trace-dir`；正式行為零變動是回歸判準。r2 由 `--residence` 擴為 `--job-env`（Q-4） |
| D-7 | 副作用帳住 `~/.autosdd/realverify_leases/<run_id>.jsonl`（realverify 自有、只追加）；撤銷只在 realverify 執行開頭／`realverify sweep` 做；`sessionctl status` 只唯讀報孤兒數 | 撤銷是破壞性動作，只給載具自己做；status 是唯讀契約 |
| D-8 | 產品自己開出的視窗沒法「先登記」，以**沙盒 sid** 為登記鍵：撤銷時查 `Win32_Process.CommandLine` 含已登記沙盒 sid 或沙盒根者才砍（先驗身分、驗不到不砍）。QW §7.4 的 `claude -r <sid> --fork-session` 新窗命令列仍帶舊 sid，比對成立（r2） | 與 `procstop` 的「先驗行程身分、驗不到不砍」同原則 |
| D-9 | 快照 diff（單案層**與批次層**）只把「含沙盒根／沙盒 sid／沙盒 slug／run_id／`AutoSDD_RV_sbx_` 字樣」的差異與 `~/.claude.json` 新增鍵判 fail，其他差異只記 note（r2：批次層對齊，QA P2-6） | 掌舵者的真主控、`AutoSDD_OpenItem_OI-*`、真哨兵同時在跑會產生真變化 |
| D-10 | 桌面通知（toast）結構上量不到 ⇒ 以 L1 在通知站點拒絕＋**job 環境轉送通知關閉值**（r2，案例行程與 job 兩側都關）＋快照檢查真痕跡無沙盒 sid 的通知事件，三者合起來覆蓋；殘餘盲區列誠實劃界 | ARC S13；QA P1-1③ |
| D-11 | `realverify run` 開頭重放副作用帳；有撤不掉的孤兒 ⇒ 整批拒跑（rc 2，末行 `REALVERIFY_VERDICT=fail reason=orphans`），**同時寫 handback 並依通知開關入佇列**；人工出口 `sweep --abandon <run_id> --why "<至少 8 字>"`；`unverified` 行程若已不存在即轉 `revoked`（r2，QA P3-1）。r3：handback 與佇列都走 `endurance_env` 的居所（`AUTOSDD_HANDBACK_DIR`、`trace_dir()`；預設即真 `~/.autosdd`），不寫死路徑；abandoned 豁免同時套到**發現式掃描**的項目——以 `git_root` 同一套正規化（`resolve()`＋`normcase`）比對 abandoned ident，命中者只記 note、不再使 run 拒跑 | Fail loud；接 nightly 後不得每夜靜默失敗。r3：寫死 `~/.autosdd/handback` 會讓 E2E-SE-18 在真環境留檔、依掌舵者真實開關入真佇列（QA P2-5）；不套發現式掃描則沙盒根被 P1 鎖住時第二次 NOOP 仍拒跑（QA P3-5） |
| D-12 | R217 a1／E2E-08「把 `realverify run --all --long` 接進 nightly／SI 巡邏」**在本設計 E2E-SE 全 PASS 前不得接**；機械鎖範圍含本機 nightly 安裝器與 local_ci_gate，判準為 token 級（r2，QA P2-7） | SA §4.3 C |
| D-13（r2） | **L1 拒絕＝終局 `refused`**：永不進 QW §7.3 讓路觀察、§7.5 失敗鏈（另一路嘗試、handback、通知佇列、`notify()`）、§7.6 哨兵接手；標記狀態寫 `refused`（不是 `failed`，§7.6 只認 `failed`）。**r4：涵蓋 fire 站點（`_cmd_fire` 首判）與 spawn 站點（`spawn_resume`／`handoff.spawn` 開頭）兩種拒絕**；spawn 站點以專屬 rc `RC_SIDEEFFECT_REFUSED` 告知呼叫端（D-24），`_cmd_fire` 與 QW §7.5／§7.6 見到即走 `refused` 終局 | QA P2-3：失敗鏈在沙盒裡就是 S14 通知外洩；L1 拒絕代表「目標不該被叫醒」，不是「叫醒失敗」 |
| D-14（r2；r3 擴） | 會起 `claude` 的站點（互動與無頭皆算）的執行檔以 argv `--claude <path>` 傳入（`spawn_resume`、`handoff.spawn` 已有 `claude` 參數，`park_cli.py:321`、`handoff.py:410`），登記行程收到時原樣進 job argv；**`_cmd_fire` 一次執行內的每一次 spawn 嘗試都用同一個值**：F4 選的路（RESUME `spawn_resume`／FRESH `handoff.spawn`）、QW §7.4 fork、QW §7.5 失敗鏈的另一路；QW §7.6 哨兵接手改讀 park 標記的 `claude` 欄（`park` 登記時把 `--claude` 寫進標記，缺席＝`"claude"`）。E2E 一律用 realverify 產生的**GUI 子系統替身**（§4.4；模式 `resume_ok`／`fresh_ok`／`fail`） | 「判準出錯」那條路也不燒額度、不開真窗（QA P1-1）；替身走 argv 不走 env，D-4 不破。r3：r2 只接 RESUME 路，FRESH 路 `(S.get("spawn") or handoff.spawn)(pkg)`（`park_cli.py:428`）沒帶參數（第二輪 QA P1-1） |
| D-15（r2） | 沙盒目標登記排程時 `fire_at > allow_until` ⇒ 拒（`lease_shorter_than_fire`）；續租（再 `grant`）不延長已登記工作的 `EndBoundary`；長案例一律在登記前以宣告的 `lease_minutes` 授與 | QA P2-4：EndBoundary ≤ StartBoundary 的排程行為無現查證據；登記前就拒，設計不依賴該未知行為 |
| D-16（r2） | L2 孤兒判準：主人**可驗證存活**（pid 存在且建立時間相符）⇒ 一律不是孤兒；`expires_at` 只在主人存活驗不到（讀不到建立時間）時當兜底 | QA P2-5：第二個 realverify 執行開頭不得撤掉仍在跑的長案例 |
| D-17（r2） | job 入口套用 `--job-env` 時，若任一居所值位於沙盒路徑段之下而其沙盒家目錄已不存在 ⇒ **不套用、不寫任何檔、不建任何目錄**，stderr 一行後 rc `RC_RESIDENCE_MISSING`＝**9**（`endurance_env` 常數，r3；`ResidenceMissing`）；排程由 EndBoundary 或下次 L2 發現式掃描撤 | 真 tools 帶居所進已刪沙盒時，第一筆痕跡就會把沙盒目錄重新建出來（建在 %TEMP%，且讓 `target_missing` 判不到）。r3：rc 3 與 `sessionctl._USAGE_RC=3`、`park_cli._RC_NOSID=3` 撞號，`LastTaskResult=3` 當唯一證據會假綠（QA P3-1）；9 在五個入口（`sessionctl.py`、`session_resume_planner.py`、`openitems.py`、`selfimproving.py`、`engine_resume_job`）現查無人使用，AT-SE-48 以 AST 鎖住「與入口其他 rc 字面不相等」 |
| D-18（r3） | **L1 spawn 執行檔判準 `sandbox_real_exe`**：spawn／tick／headless 類站點把要用的執行檔（`claude` 參數，未給＝`"claude"`）傳進判準；目標是沙盒、租約全過、**執行檔不在沙盒家目錄之下**（`resolve()`＋`normcase` 後前綴比對；裸名一律算「不在」）**且**身分檔 `window≠true` ⇒ `refuse sandbox_real_exe`（終局，同 D-13） | 第二輪 QA P1-1 修法 2：只看目標自帶資料（身分檔）與 argv，不違 D-4；`window` 旗標原本在判準中無作用，此後成為「沙盒內准用真執行檔」的唯一授權（只有 `grant_side_effects(window=True)` 經 F5 `assert_trusted` 才寫得出來，§7） |
| D-19（r3） | `realverify run --all` **排除 `sideeffect` 與 `sideeffect_selftest` 兩個家族**；兩家族只能以 `--family`／`--case` 指名執行 | RV-SE03 案例內跑 `run --all`，若 `sideeffect` 在 `--all` 內會跑到自己而遞迴（QA P2-4）；家族排除是結構正解，環境標記防重入是測試用 env 鉤（否決，§12） |
| D-20（r3；r4 改寫） | `job_env_argv(env, *, sandbox)`（`sandbox`＝登記站點先跑的 `register_verdict` 判為沙盒目標，即 `reason=="sandbox_lease"`）：**沙盒目標**——對 `JOB_ENV_KEYS` 中顯式設定者轉送，值不在允許值 ⇒ 拋 `JobEnvValueError`，登記站點 rc 2、不登記、stderr 點名鍵與值；**正式目標**——永不拋例外；值不在允許值內的鍵**一律不轉送**（argv 不因它改變），允許值照 D-6 轉送 ⇒ 掌舵者自行 opt-in 的 `AUTOSDD_DESKTOP_NOTIFY=1` 或顯式空的 `AUTOSDD_SENTINEL_OFF=` 都不改 argv、登記照常成功，job 端該開關照產品自己的規則取值（現行＝讀 job 行程環境；QW Q3 後通知改讀 park 標記 `desktop_notify`，QW S-17）。兩種目標皆把**顯式空值的 `AUTOSDD_SENTINEL_OFF`** 視同未設。`apply_job_env` 剝 `--job-env` 時遇第一個 `--` 即停（其後原樣保留） | r3：到點才 rc 2＝靜默壞掉（QA P3-4；例：`cases/prd_px_wake2.py:95/105`）；`runlong -- <argv…>` 的子指令旗標不得被吃（QA P3-2）。r4（第三輪 QA P2-3）：r3 對正式目標也拋例外 ⇒ 掌舵者依 `quota_escalation.py:99-102` 開通知或 `.env.example:114` 留空哨兵鍵時，正式 `park`／oldwin／SI 登記全部 rc 2，違反 REQ-SE-15「正式行為逐字不變」，並與 QW S-17「正式登記把通知原值寫進標記」衝突；圍籬只對沙盒有意義 |
| D-21（r3；r4 擴） | park 標記新狀態 `refused`：**`park.STATUSES`（`park.py:31`，`read_marker` 的驗證表，`:159`）加 `refused`**（r4，否則讀取端把 `refused` 標記當無效標記）；讀取端：`park --status` 印 `refused` 與 reason；`park.yields` 視為非 armed（不讓路）；`park.stop_verdict` 不視為續航憑證；SessionStart 公告以「到點被產品面拒絕（目標不合法）」一行列出、不當成失敗 | 新狀態不被讀取端認得＝當成未知值走預設分支（QA P3-3） |
| D-22（r3） | SITES 普查加認「`claude` 執行形態」：重用 `realverify/interactive.py` 的偵測器（`_yields_claude` 升為公開名 `yields_claude`，舊名保留為別名），並擴兩形：`<名> or "claude"`（BoolOp）、參數預設值／argparse `default="claude"`；**不套** `_is_interactive_argv` 的非互動過濾（無頭 `-p` 一樣燒額度）。新列入 `SITES`：`session_resume_planner.probe_quota` 呼叫者（`--probe-quota` 動詞、`_run_resume`、`_sentinel_tick`）、`selfimproving/patrolrun.launch`（`patrolrun.py:282`）、SI 巡邏到點入口 `tools/selfimproving.py patrol`（fire 類）。`--claude` 統一：planner 收 `--claude`，`--probe-command` 降為同 dest 的別名（相容一版）；SI `patrol`／`sched arm` 收 `--claude`。**r4**：①偵測器擴充會改變 `interactive.spawn_markers` 的掃描結果 ⇒ S5 同一 commit 重跑 `tools/tests/test_realverify_lib.py::InteractiveWindowEntryLockTest`，新命中逐筆列入 commit 訊息並在該鎖登記（不得以放寬判準消紅）；②**SITES 普查範圍（glob）**＝`tools/*.py`、`tools/lib/**/*.py`、`.claude/hooks/*.py`；排除 `tools/tests/**`（測試）、`tools/probe/**`（量測探針，不在任何排程到點路徑；被正式到點路徑 import 的函式不得住 probe）、`tools/lib/realverify/**`（含 `cases/**`；載具自有，REQ-SE-34 管） | 普查只認開窗旗標、排程、通知時漏掉無頭燒額度站點（QA P2-3）；`selfimproving/sched.py:334` 的 `which("claude") is None` 屬存在檢查、不執行，列 `CLAUDE_PRESENCE_ONLY`（附 WHY）豁免。r4（第三輪 QA P3-3）：普查範圍未定 ⇒ 實作者各自解讀 |
| D-23（r4） | **沙盒工作樹保持乾淨**：`Sandbox.create` 在 `git init` 後把 `sandbox.LOCAL_EXCLUDES` 一次寫進 `<根>/.git/info/exclude`；`LOCAL_EXCLUDES`＝`/.autosdd_sandbox.json`＋7 個居所目錄名（由 `Sandbox.env()` 的同一張表 `RESIDENCE_DIRS` 推得，不手抄）＋`/bin/`＋`/fakeclaude.*`；`install_tools` 的 `_EXCLUDES`（`cases/sessionctl_park.py:35`）改由同一常數推得。正式目標替身 repo（E2E-SE-09）以同一輔助函式寫 exclude，登記後再**刻意**加一個不在 exclude 的未追蹤檔 `RVPROD_DIRTY.txt`、HEAD 不打 wip tag | 第三輪 QA P2-1：居所、替身、設定檔都落在 git 根下 ⇒ `park` 的 `spawn_preflight`（`park_cli.py:165`）與 `handoff._refusals`（`handoff.py:340-353`）拒絕，E2E-SE-01／02／04～06／09／10／17 跑不起來。第三輪 QA P1-1 修法 2：正式替身 repo 不受 L1 保護，以現行前置檢查（不靠環境變數）讓 FRESH 結構上開不了窗；RESUME 路（`spawn_resume`）現行不驗工作樹，不受影響 |
| D-24（r4） | spawn 站點（`spawn_resume`〔含 `fork=True`〕、`handoff.spawn`）的 L1 拒絕回**專屬 rc `RC_SIDEEFFECT_REFUSED`＝10**（常數住 `sandbox_scope`，與 `_RC_REFUSED`＝4、spawn 失敗 1、`RC_RESIDENCE_MISSING`＝9 及入口其他 rc 字面皆不相等，AT-SE-48 鎖）並落 `sideeffect_refused`；呼叫端見此 rc ⇒ **終局 `refused`**：`_cmd_fire`（QW Q3 前與後同語意）`_settle(..., "refused", reason)`、不寫 handback、不入佇列、不嘗試另一路、自拆、rc 0；QW §7.5 該次 `park_attempt` 記實際 rc 與 `reason=sideeffect_refused`（不再有第 2 筆）、`session_switch_spawning` 同 attempt 寫失敗列；互動 `handoff --spawn` 以 rc 10 結束、stderr 一行理由。排程登記站點的 L1 拒絕維持 rc 4（CLI 既有拒絕碼）但必須同時落 `sideeffect_refused` 痕跡並在 stderr 帶 reason，驗收一律斷言 reason（不只斷言 rc） | 第三輪 QA P2-2：r3 宣稱 spawn 站點拒絕是終局，但 `_cmd_fire` 只拿到 rc≠0，現行會寫 handback 並設 `failed`（`park_cli.py:433-435`），QW §7.5-1 還會改走另一路；第三輪 QA P3-2：rc 4 已用於無人窗口、模式非 auto、量不到 reset（`park_cli.py:75-83`），只斷言 rc 4 會假綠 |
| D-25（r4） | `cases/sessionctl_park.ctl_env` 對 `AUTOSDD_SENTINEL_OFF` 的 pop（`:124`）**撤除**：沙盒一律帶 `SENTINEL_OFF=1`；真要武裝沙盒哨兵的案例（E2E-SE-07、E2E-SE-17(d)(e)、QW E2E-QW-15）以 `ctl_env(arm_sentinel=True)` 顯式要求，原始碼該處附 WHY 註解，且必在有效租約內＋`--claude` 替身（L1／L2／D-18 兜底） | 第三輪 QA P3-5：無條件 pop ⇒ 每個沙盒 `park` 都真的武裝 `AutoSDD_Sentinel_<沙盒 sid>`；顯式要求使「誰需要真哨兵」可 grep、可審 |
| D-27（r5） | **正式目標替身（`AutoSDD_RVprod_<run_id>`）不得留下哨兵孤兒**：①E2E-SE-09 (a)(b) 的登記行程設 `AUTOSDD_SENTINEL_OFF=1`（不武裝）；②(c) 刻意不關（驗 D-20 的顯式空值），故在 `park` 之前先把 `AutoSDD_Sentinel_<替身 sid>` 以 `sched_job` 記入 L2（`intent`），QW Q3 後斷言它真的被武裝（`Get-ScheduledTaskInfo` 的 `NextRunTime` 非空）再撤除並回讀確認不存在；QW Q3 前斷言它不存在並把該列記 `revoked`；③L2 發現式掃描加認 `AutoSDD_RVprod_`（§5.3），以 `<run_id>` 的帳主人判孤兒——案例崩潰時下一次 `run`／`sweep` 撤得掉 | 聯合 QA 第四輪 B-P2-1：QW §7.1「park 登記時嘗試武裝本 sid 哨兵」在 Q3 後對正式替身 repo 生效；正式目標不帶 `EndBoundary`、發現式掃描只認 `AutoSDD_RV_sbx_`，`sweep` 撤不掉 ⇒ repo 刪掉後該工作每次巡邏都啟動失敗、永不自我解除（紅線 13 那一類），L3 也會判 LEAK。前綴 `AutoSDD_RVprod_` 只由 E2E-SE-09 產生，加認它不會撤到真工作 |
| D-26（r4） | PRD R-VER-2「起 `claude`…由替身承接」限定為**到點 job 的**開窗或起 `claude` | 第三輪 QA P3-4：未限定時與既有案例真跑 `claude -p`、E2E-SE-16、QW E2E-QW-14／27 的真無頭呼叫字面衝突 |

### 0.4 待主控決定（開放問題）
1. **工作包先後**：QW r3 §12 已採本稿建議序（A9＋F5 → SE S1 → {S2∥S3∥S5} → S6 → QW Q 系列），r1 的本題已關閉。新題：E2E-SE-17（QW 新站點的 L1 真機驗證）的案例程式只能在 QW Q3 之後寫，持有面是 `cases/**`——本稿建議**由 QW Q6 一併落地**（§10.2 第 4 項），本稿 S7 對 E2E-SE-17 以 OI 承接到 QW Q6 收尾。
2. **既有外洩物的刪除**：`~/.autosdd` 內 6 件沙盒產物（§9）由 `realverify sweep --legacy --apply` 刪除需主控同意；`~/.claude.json` 兩把失效沙盒信任鍵屬全域設定，只寫建議、須掌舵者同意。
3. **F5 宿主一次性信任**仍待掌舵者決定（F5 §6）；未信任時 E2E-SE-16 判 ENV。本設計三項真機證明都不需要開窗，不受此題阻塞。
4. **EndBoundary 自刪實測**（r2）：Windows 對「從未執行就過了 `EndBoundary` 的一次性工作」何時刪除，無現查證據。設計不依賴它（L1＋L2 已足）；S1 第一動作跑 `tools/probe/sandbox_scope_endboundary.py`（只登記一支 `AutoSDD_RV_probe_*` 停用工作、Action＝`pythonw -c pass`，登記前寫 L2 帳），把實測秒數寫進證據檔，E2E-SE-04(b) 以此為判準來源。實測若顯示 OS 不刪停用工作，E2E-SE-04(b) 改以「工作過期後 `sweep` 發現式掃描撤除」為判準，並把 D-5 的 OS 自毀降為「到點不執行」單一語意（屆時回報主控）。

**本節判準**：§0.2～§0.3 每個代決在 TCS 有對應 REQ 或 AT；§0.4 四題在交卷時列給主控。

---

## 1. 問題與證據

| # | 事實 | 座標 |
|---|---|---|
| E1 | 案例 07:45 建沙盒 session；10:45:19 `park_armed`（正式前綴、fire 10:47:00）；10:47:00.99 真排程器 `park_job_start`；10:47:01 `park_route RESUME`；10:47:02 `session_resume_spawned ok=true` | T57 L4／L27；SW L480～L485；UL L97 |
| E2 | 幽靈階段 11 次 API 回應：output 6,504、cache_read 560,249、cache_create 83,497（`message.id` 去重）；視窗佔桌面 7 小時 2 分；17:49 掌舵者被迫在該窗互動 | SA §1.2～1.3；T57 L37～L148 |
| E3 | 沙盒 env 只設 `AUTOSDD_TRACE_DIR`、`AUTOSDD_SENTINEL_OFF` | `tools/lib/realverify/sandbox.py:173-179` |
| E4 | `handoff_dir()` 刻意不給 env 出口 | `sandbox.py:88-90` |
| E5 | park 案例 `real_traces=True` 移除 trace 圍籬 | `cases/sessionctl_park.py:121-129` |
| E6 | park job argv 只帶 `--pkg`，不帶任何居所；oldwin 已帶 `--trace-dir` | `park_cli.py:28-33`；`oldwin_sched.py:80-91` |
| E7 | 清理只認 `AutoSDD_RV_*`（批次正常結束才掃）與 oldwin 沙盒前綴 | `realverify/sched.py:23,113-124`；`runner.py:82`；`sandbox.py:213-235` |
| E8 | 第二起實證：沙盒 truqufqq 的 handback 落真 `~/.autosdd/handback`；PX11 沙盒 sid 的 `.checked` 落真 `handoff/` | SA §2.2；F6 §5 |
| E9 | 沙盒 park 排程 17 筆入正式命名空間，11 筆真觸發（9 skip＋2 spawn） | SA §2.3 |
| E10 | 每案 `git init` ⇒ 互動視窗必跳信任框；F5 以宿主 worktree 解（未提交） | F5 §2、§4 |
| E11（r2） | job 端行為開關只讀行程環境：模式缺席＝auto（`switch.py:198-205`）；通知只讀 `AUTOSDD_DESKTOP_NOTIFY`（`quota_escalation.py:551`）；通知佇列居所＝`trace_dir()`（`quota_escalation.py:568-570`） | QA P1-1 |
| E12（r2） | `interactive.trusted_sandbox` 先 `mkdtemp` 再 `git worktree add <root>`（`interactive.py:162-167`）；`_cmd_fire` 第一筆痕跡 `park_job_start` 在讀標記之前（`park_cli.py:379-380`） | QA P2-1、P2-2 |
| E13（r3） | `_cmd_fire` 只在 RESUME 路把執行檔交給 `spawn_resume`；FRESH 路 `(S.get("spawn") or handoff.spawn)(pkg)` 不帶（`park_cli.py:425-428`），`handoff.spawn` 以預設 `"claude"`＋`CREATE_NEW_CONSOLE` 開窗（`handoff.py:442-444`）；spawn 成功判準＝行程存活且逐字稿增長或出現新檔，與 rc 無關（`park_cli.py:351-362`、`handoff.py:450-461`）；無頭站點 `patrolrun.py:282`、planner `probe_quota(claude="claude")`（`session_resume_planner.py:478`、`--probe-command` `:961`） | 第二輪 QA P1-1、P2-1、P2-3 |

暴露證據（守衛面准入）：E1／E2 為非構造性真實發生＋掌舵者真機回報（sid 57d0ccad），L1 動到 `tools/lib/sessionctl/**` 與 `session_resume_planner.py`、L4 動到 `endurance_env.py` 已滿足准入。

---

## 2. 副作用清單（面 × 隔離家 × 本設計的層）

| # | 副作用面 | 產生站點（例） | 沙盒內的家（L4） | 崩潰後（L2） | 到點／他行程（L1） | 偵測（L3） |
|---|---|---|---|---|---|---|
| S1 | 排程 `AutoSDD_HandoffSpawn_*` | `park_cli._cmd_park`；QW §7.3 job 內重排 | job argv `--job-env` | 帳列 `sched_job`；Action 含沙盒字樣亦撤 | `_cmd_fire` 首判；登記站點判 | 排程名＋Action |
| S2 | 排程 `AutoSDD_Sentinel_*`／`SessionResume_*` | `sentinel_lifecycle`、planner | 同上 | 同上 | `_run_resume`／`_sentinel_tick`（含 QW §7.6 接手）首判 | 同上 |
| S3 | 排程 `AutoSDD_OldWinCloseSbx_*` | `oldwin_sched.schedule_retry` | 同上（`--trace-dir` 併入 `--job-env`） | 同上 | 登記站點判；到點走 `_cmd_fire` 首判 | 同上 |
| S4 | 排程 openitems／`AutoSDD_EngineResume_*`／SI | `openitems/drive.py:122`、`engine_resume_job.arm`、`selfimproving/schedarm.arm` | 同上 | 同上 | 登記站點、driver／resume job 入口 | 同上 |
| S5 | 排程 `AutoSDD_RV_*` | `realverify/sched.py` | — | 帳列（取代 `cleanup_all_rv`） | 不適用（載具自有） | 同上 |
| S6 | 互動視窗／`claude` 行程（含無頭 `claude -p`，r3） | `spawn_resume`（含 `fork=True`）、`handoff.spawn`、planner `probe_quota`、SI `patrolrun.launch`、F5 探針與 `open_window` | cwd＝沙盒；E2E 一律假 `claude`，每一次嘗試同一個（D-14） | 帳列 `process`（依沙盒 sid／根比對命令列） | spawn／headless 站點首判，含 `sandbox_real_exe`（D-18） | 行程命令列 |
| S7 | 交接包 `~/.autosdd/handoff` | `handoff_build` | `AUTOSDD_HANDOFF_DIR` | 隨沙盒根刪 | pkg 檔頭 `repo 根` 參與判準 | 檔名集合 |
| S8 | handback／plans | park 失敗、哨兵、QW §7.5 失敗鏈 | `AUTOSDD_HANDBACK_DIR`、`AUTOSDD_PLAN_DIR` | 同上 | L1 拒絕永不進失敗鏈（D-13） | 同上 |
| S9 | 痕跡 `~/.autosdd/traces`（含 park 標記、通知佇列） | `switch.trace`、`park.write_marker`、`notify_queue_path` | `AUTOSDD_TRACE_DIR`（撤 `real_traces`） | 同上 | — | 真 jsonl 新行含沙盒字樣 |
| S10 | context_feed／額度快取／SI 目錄 | `harness_feed`、`quota_meter`、`selfimproving/events` | `AUTOSDD_CONTEXT_FEED_DIR`、`AUTOSDD_QUOTA_CACHE_DIR`、`AUTOSDD_SI_DIR` | 同上 | — | (名稱, mtime, size)；變動檔讀內容找沙盒字樣（r2） |
| S11 | `~/.claude/projects/<沙盒 slug>` | Claude Code | 無（CC 行為） | 帳列 `transcript_dir` | — | 目錄集合 |
| S12 | `~/.claude/sessions/*.json` | Claude Code | 無 | 行程撤銷後 CC 自清；殘留列 note | — | sid／cwd |
| S13 | `~/.claude.json` 信任鍵 | 互動 claude 在未信任目錄 | F5 宿主 worktree（不寫全域） | 不撤（全域檔，不寫）；快照新增鍵＝fail | — | projects 鍵名集合（唯讀） |
| S14 | 桌面通知 toast | `quota_escalation.notify`、QW §7.5 | job 環境轉送通知關閉值（r2） | — | 通知站點判（有目標上下文時）；L1 拒絕不進失敗鏈 | 盲區＋真痕跡無沙盒 sid 通知事件 |
| S15 | `%TEMP%` 目錄／鎖檔 | mkdtemp、`AutoSDD_RV_sched.lock`、探針 debug log、假 `claude` 替身 | — | 帳列 `sandbox_root`、`temp_file` | — | 沙盒前綴目錄集合 |
| S16（r2） | **行為開關**：選路模式、通知開關、哨兵開關 | job 行程讀登入者環境 | `--job-env` 轉送 `AUTOSDD_SESSION_SWITCH_MODE`、`AUTOSDD_DESKTOP_NOTIFY`（只准空）、`AUTOSDD_SENTINEL_OFF`（只准 `1`） | — | L1 不依賴它們（D-4） | 由 E2E-SE-01(e)／09／10 以 job 端痕跡驗 |

**本節判準**：TCS §1 的 REQ 對 S1～S16 每列至少一條；`JOB_ENV_KEYS` 恰為 S7～S10 的 7 個居所鍵＋S16 三鍵（＋AST 普查新增的居所鍵）。

---

## 3. L1 產品面拒絕：`tools/lib/sandbox_scope.py`

### 3.1 身分檔與家目錄
```
{"schema": 1, "run_id": "<uuid>", "sid": "<沙盒 sid>", "owner_pid": <int>, "owner_started": "<ISO+offset>",
 "created_at": "<ISO+offset>", "allow_until": null | "<ISO+offset>", "window": false}
```
- **一般沙盒**（`Sandbox.create`）：家目錄＝沙盒根。`mkdtemp` 後第一動作原子寫身分檔（`git init` 接受非空目錄），`git init` 後立即把 `sandbox.LOCAL_EXCLUDES`（身分檔、7 個居所目錄、`/bin/`、`/fakeclaude.*`；r4，D-23）追加進 `<根>/.git/info/exclude`。
- **worktree 沙盒**（`interactive.trusted_sandbox`）：家目錄＝`mkdtemp` 外層；外層第一動作寫身分檔；worktree 建在 `<外層>/wt`（`git worktree add` 的目的目錄不存在 ⇒ 成功）。身分檔不在 worktree 內，工作樹不受影響；另把同一樣式追加進宿主 common-dir 的 `info/exclude`（冪等，縱深防禦）。宿主信任以 worktree 歸屬判定，路徑多一層不影響（F5 §4；AT-SE-01 與 E2E-SE-16 驗）。
- 共同判準：寫身分檔前後 `git status --porcelain` 逐字相同、`worktree add` rc 0；**r4：一般沙盒建好 7 個居所、替身與其全部設定檔後 `git status --porcelain` 為空**（`park` 的 `spawn_preflight` 與 `handoff._refusals` 才會放行；AT-SE-01）。
- `owner_pid`＝建立沙盒的 realverify 行程；`owner_started` 用於縮小 pid 重用窗。

### 3.2 介面（純函式＋檔案 I/O；零 token；不讀環境變數；不開行程）
| 函式 | 行為 |
|---|---|
| `write_identity(home, *, run_id, sid, owner_pid, now)` | 寫身分檔；回路徑 |
| `sandbox_home(path) -> Path \| None` | 本層或上一層有身分檔者；否則依路徑段 `AutoSDD_RV_sbx_*` 取該段為家（不要求存在）；都無 ⇒ None |
| `grant(home, *, until, now, max_minutes=LEASE_MAX, window=False)` | 寫 `allow_until`＝`min(until, now+min(max_minutes, LEASE_CAP))`；`LEASE_MAX`＝30、`LEASE_CAP`＝300（程式常數）；再呼叫即續租（不改已登記排程，D-15） |
| `revoke(home)` | `allow_until`＝null |
| `is_sandbox(path) -> bool` | `sandbox_home(path)` 非 None ∨ 路徑段含 slug 片段 `AutoSDD-RV-sbx-`；Windows 不分大小寫 |
| `git_root(path) -> Path` | 往上找 `.git`（目錄或檔案皆可）；找不到回原路徑；回傳前 `resolve()`＋`os.path.normcase` |
| `pkg_root(pkg) -> Path \| None` | 讀交接包檔頭 `repo 根：` 一行（格式 SSOT＝`handoff_build`，名稱以常數共用）；讀不到 None |
| `target_verdict(*, cwd, pkg=None, transcript=None, exe=None, now) -> Verdict` | 見 §3.3；`Verdict(allow, reason, roots)`；`exe`＝本次要用的 `claude` 執行檔（spawn／tick／headless 類站點必傳，未給 `--claude` 時傳 `"claude"`；其他類別傳 None，r3） |
| `exe_in_home(exe, home) -> bool` | `exe` 經 `resolve()`＋`normcase` 後位於 `home` 之下；裸名（無目錄成分）一律 False；不查 PATH（r3） |
| `register_verdict(*, cwd, pkg=None, fire_at, now) -> Verdict` | `target_verdict` ＋ 沙盒放行時 `fire_at > allow_until` ⇒ `refuse lease_shorter_than_fire`（D-15） |
| `job_expiry(home, now) -> datetime \| None` | 正式目標 ⇒ None；沙盒且租約有效 ⇒ `allow_until` |
| `SITES` | 站點登記表（模組、函式、類別 spawn／register／fire／tick／notify），AST 鎖用 |

### 3.3 判準（依序，第一個命中即回）
1. 收集：`cwd` 的 `git_root`；`pkg` 路徑與 `pkg_root(pkg)`（正規化同上）；`transcript` 路徑的父目錄 slug（只用於 `is_sandbox`；呼叫端以 `_REPO` 算出路徑即可，不必讀檔）。
2. 沙盒旗標集合 F＝上述各項中 `is_sandbox` 為真者。F 非空且其中任一實體（pkg 檔、pkg 根、cwd 根、沙盒家目錄）不存在 ⇒ `refuse target_missing`。**F 為空時不做存在檢查**（正式 pkg 已刪的情形照舊由後段 `skip expired` 處理，正式痕跡不變）。
3. `cwd` 根與 `pkg` 根皆可得且不同 ⇒ `refuse root_mismatch`（真 tools＋沙盒交接包；正式路徑中這只在交接包被誤導到別的 checkout 時出現，拒絕即正確）。
4. F 非空 ⇒ 讀家目錄身分檔：讀不到／schema 不符 ⇒ `refuse sandbox_unreadable`；`allow_until` null ⇒ `sandbox_no_lease`；已過期 ⇒ `sandbox_lease_expired`；主人不在（或建立時間不符）⇒ `sandbox_owner_dead`；`exe` 非 None ∧ `not exe_in_home(exe, 家目錄)` ∧ 身分檔 `window` 不為 true ⇒ `sandbox_real_exe`（r3，D-18）；全過 ⇒ `allow sandbox_lease`。
5. 其他 ⇒ `allow production`。
- 例外一律 `refuse error:<類名>`（fail-closed）；呼叫端把判準拋出的例外同樣視為拒絕並落痕跡。
- 正式目標的成本＝字串比對＋往上找 `.git` 數次 `exists`；回歸判準＝正式路徑行為與痕跡逐字不變（AT-SE-31、E2E-SE-09）。

### 3.4 站點（呼叫點與拒絕後的動作）
| 站點 | 類別 | 呼叫位置 | 拒絕後 |
|---|---|---|---|
| `park_cli._cmd_fire` | fire | **釘死在 `park_job_start` 痕跡之後、`park.read_marker`／`.ack` 檢查／`handoff.list_handoffs`／`live_driver` 之前**，並先於 QW §7.3 的 holder 讀取、`park_yield_primary`、`OBSERVE_SEC` 觀察與 §7.5 的 `park_attempt`；輸入只用 `cwd=_REPO`、`--pkg`、sid（transcript 路徑由 `_REPO` slug＋sid 算出）、`exe=opts.claude or "claude"`（r3）；放行後本次 job 的**每一次** spawn 嘗試（F4 選的路、§7.4 fork、§7.5 另一路）都以同一個 `opts.claude` 呼叫 spawn 函式（D-14） | 痕跡 `sideeffect_refused`（site、reason、sid、roots）；**之後**才讀標記，屬本 job 且 armed ⇒ `_settle(..., "refused", reason)`；`_disarm_verified` 自拆；rc 0；**終局**：不重排、不嘗試另一路、不寫 handback、不入通知佇列、不呼叫 `notify`（D-13） |
| `park_cli.spawn_resume`（含 QW `fork=True`）、`handoff.spawn` | spawn | runner 呼叫之前（函式開頭，涵蓋 fork 變體）；`exe=claude or "claude"`（r3） | rc `RC_SIDEEFFECT_REFUSED`（10，r4，D-24）、stderr 一行理由、同痕跡；不寫 `.resumed`／`.spawned`；呼叫端（`_cmd_fire`、QW §7.5／§7.6）見此 rc 即走 `refused` 終局 |
| `session_resume_planner.probe_quota` 的呼叫者（`--probe-quota` 動詞、`_run_resume`、`_sentinel_tick`）、`selfimproving/patrolrun.launch` | headless（r3） | 起 `claude -p` 之前；`exe`＝`--claude`（planner 的 `--probe-command` 為別名）／SI `--claude`，未給＝`"claude"` | 不起行程；planner 走既有 disarm／probe 失敗語意但痕跡為 `sideeffect_refused`；SI 本心跳結束不運轉、不入 SI 帳 |
| SI 巡邏到點入口 `tools/selfimproving.py patrol` | fire（r3） | 入口最先（讀 SI 帳之前）；`cwd=_REPO`、`exe` 同上 | 不運轉、痕跡同上、rc 0；排程照 SI 既有一次性語意 |
| `park_cli._cmd_park`、QW §7.3「重排到 wake_at＋寬限」的 job 內登記、`oldwin_sched.schedule_retry`、`sentinel_lifecycle` 武裝、`engine_resume_job.arm`、`openitems/drive.drive_item`、`selfimproving/schedarm.arm` | register | 登記排程之前，用 `register_verdict`；其判決同時決定 `job_env_argv(env, sandbox=…)`（D-20） | rc 4、stderr 帶 reason、痕跡 `sideeffect_refused site=<站點>`、不登記（驗收斷言 reason，D-24）；放行且目標是沙盒 ⇒ 登記時帶 `job_expiry`（§5.4） |
| `session_resume_planner._run_resume`、`_sentinel_tick` 的 probe／resume 分支與 QW §7.6 park 接手分支 | tick | spawn `claude -p -r`／跑 §7.4～7.5 之前 | 不 spawn、不接手；哨兵自我解除（既有 disarm 路）；痕跡同上。§7.6 只認標記 `failed`，L1 拒絕寫 `refused`，結構上不會被接手 |
| openitems driver 到點入口（`tools/openitems.py` 的 fire 動詞） | fire | 執行案例之前 | 不執行、自拆、痕跡同上 |
| `quota_escalation` 帶目標上下文的通知呼叫者（`patrol_housekeeping`、`alert`、QW §7.5 失敗鏈第 3 步） | notify | 呼叫 `notify`／入列之前；`notify` 本身不改簽名 | 不出 toast、不入列、痕跡 `sideeffect_refused site=notify` |

- **SITES 普查**（AST；範圍 glob 見 D-22）認得的站點形態：`CREATE_NEW_CONSOLE` 名稱、`getattr(subprocess, "CREATE_NEW_CONSOLE", …)` 的字串形態、`creationflags=` 帶字面 `0x10`／`16`（`park_cli.py:342`、`handoff.py` 同型）、`backend.arm`／`register`／`Register-ScheduledTask`、`NotifyIcon`、`notify_queue_path` 寫入、**`claude` 執行形態**（r3，D-22：重用 `interactive.yields_claude`，擴 `<名> or "claude"` 與參數／argparse 預設 `"claude"`；互動與無頭皆算；`CLAUDE_PRESENCE_ONLY` 只收存在檢查並附 WHY）。普查集合必須＝`SITES` 且每個都呼叫 `target_verdict`／`register_verdict`（realverify 載具自有站點除外，由 REQ-SE-34 管）。
- **QW 新站點**（`fork=True`、§7.3 重排、§7.5 第 3 步、§7.6 接手）在 QW Q3 寫出時必須同 commit 進 `SITES`；AST 鎖會使漏登記即紅（這是 QW 需同步項，§10.2）。§7.5 另一路與 §7.6 接手的 spawn 呼叫同樣傳 `exe`（§7.5 用 `opts.claude`；§7.6 用標記 `claude` 欄），即使漏傳，D-18 也會以 `sandbox_real_exe` 終局拒絕而不開真窗（spawn 站點回 `RC_SIDEEFFECT_REFUSED`，呼叫端走 `refused`，不改走另一路，D-24）。
- **誠實劃界**：`notify` 的呼叫者若沒有目標上下文（純系統事件）不判——那種事件不會由沙盒產生（案例與 job 兩側都關通知）。macOS launchd 無 `EndBoundary` 對等物，靠 L1＋L2。

---

## 4. L4 job 環境允許表帶過排程邊界

### 4.1 `endurance_env` 新增
- `RESIDENCE_KEYS`＝`AUTOSDD_TRACE_DIR`、`AUTOSDD_HANDOFF_DIR`、`AUTOSDD_HANDBACK_DIR`、`AUTOSDD_PLAN_DIR`、`AUTOSDD_QUOTA_CACHE_DIR`、`AUTOSDD_CONTEXT_FEED_DIR`、`AUTOSDD_SI_DIR`（F6 §2 七鍵）。
- `JOB_ENV_KEYS`＝`RESIDENCE_KEYS` ∪ {`AUTOSDD_SESSION_SWITCH_MODE`、`AUTOSDD_DESKTOP_NOTIFY`、`AUTOSDD_SENTINEL_OFF`}，每鍵附允許值：居所鍵＝絕對路徑；模式＝`auto|notify|off`；通知＝**只准空字串**（關閉）；哨兵＝**只准 `1`**（關閉）。WHY 只准關閉值：job 環境轉送是「把案例的圍籬帶過去」，不是給案例一個在真環境開啟功能的管道。
- 刻意**不收** `AUTOSDD_UNATTENDED`：它會讓 spawn 站點在 L1 之前以另一個理由拒絕，遮住 L1 的真機驗證；L1 不依賴它（§8）。
- `job_env_argv(env, *, sandbox: bool) -> list[str]`（r4，D-20）：`sandbox=True`——對 `JOB_ENV_KEYS` 中 **env 顯式有值**者（通知鍵：顯式設為空也算；哨兵鍵顯式空值視同未設）產 `--job-env KEY=VAL`，鍵序固定；顯式值不在允許值內 ⇒ 拋 `JobEnvValueError`，登記站點 rc 2、不登記。`sandbox=False`（正式目標）——同樣只轉送顯式且在允許值內者，**不在允許值內者靜默不轉送**、永不拋；正式環境無顯式值 ⇒ `[]`（argv 逐字不變）。`sandbox` 由同站點先跑的 `register_verdict` 決定，站點不得自行推斷。
- `apply_job_env(argv) -> argv'`：入口最先呼叫，剝掉 `--job-env` 並寫進 `os.environ`；**遇第一個 `--` 即停**，其後原樣保留（r3，D-20）；非 `JOB_ENV_KEYS` 的鍵或不在允許值內 ⇒ rc 2；居所值位於沙盒路徑段而其家目錄不存在 ⇒ `ResidenceMissing`，入口 stderr 一行、rc `RC_RESIDENCE_MISSING`（9）、**不寫任何檔也不建目錄**（D-17）。
- AST 鎖①：`tools/lib/**/*.py` 中所有 `AUTOSDD_[A-Z_]*_DIR` 字面 ⊆ `RESIDENCE_KEYS`。AST 鎖②：`Sandbox.env()` 與各案例 env 輔助函式設定的每一鍵 ⊆ `JOB_ENV_KEYS` ∪ `SANDBOX_LOCAL_ONLY`（`sandbox.py` 內的 dict，鍵→WHY；例：`PYTHONUTF8`「只影響案例行程輸出編碼」、`AUTOSDD_UNATTENDED`「見上」）；新鍵未分類即紅。

### 4.2 job argv 與入口
- 改用 `job_env_argv`：`park_cli.job_argv`、`oldwin_sched.job_argv`（`--trace-dir` 併入，入口相容舊旗標一版）、`openitems/drive.action_argv`（同）、`engine_resume_job.arm`、哨兵 job argv、`selfimproving/schedarm`、QW §7.3 job 內重排。
- `--claude <path>`（D-14、D-22）：`park`／`park --fire`、`handoff --spawn`、`session_resume_planner`（續跑、`--probe-quota`、`--sentinel-tick`；`--probe-command` 為同 dest 別名）、`selfimproving.py patrol`／`sched arm` 收此旗標；登記行程收到時原樣寫進 job argv；`park` 另把它寫進標記 `claude` 欄（供 QW §7.6 接手）；`_cmd_fire` 內每一次 spawn 嘗試都傳同一值；未給 ⇒ argv 與標記與現行逐字相同、spawn 用 `"claude"`。
- 入口最先 `apply_job_env`：`tools/sessionctl.py`、`tools/session_resume_planner.py`、`tools/openitems.py`、`tools/selfimproving.py`（只在排程動詞）。
- 鎖：`SITES` 中 register 類站點的 argv 建構函式必須呼叫 `job_env_argv`（AST）。

### 4.3 沙盒 env 與兩個例外撤除
- `Sandbox.env()` 把 7 個居所鍵全部指到 `<家>/<名>`、`AUTOSDD_DESKTOP_NOTIFY`＝空、`AUTOSDD_SENTINEL_OFF`＝`1`；模式由案例顯式設定（未設 ⇒ 不轉送 ⇒ job 端照真環境，該案例若會到點，L1 必須拒或租約放行時以假 `claude` 承接）。
- 撤 `cases/sessionctl_park.ctl_env(real_traces=True)` 與 `prd_px_pace2.py:75` 的 trace 移除；撤 `sandbox.handoff_dir()` 的真目錄定義與 `cleanup_handoff_for` 對真目錄的使用。
- **r4**：撤 `ctl_env` 對 `AUTOSDD_SENTINEL_OFF` 的 pop（`:124`）；需要真武裝沙盒哨兵者走 `ctl_env(arm_sentinel=True)`＋WHY 註解（D-25）。7 個居所目錄、`bin/`、`fakeclaude.*` 一律列入 `<根>/.git/info/exclude`（`LOCAL_EXCLUDES`，D-23），沙盒工作樹在案例動作前恆為乾淨。
- 鎖：realverify 原始碼中 `Path.home()`／`".autosdd"` 字面只准出現在允許表（`leases` 目錄、`realverify_kept`、`rv_host`）。r3：D-11 拒跑 handback 改走 `endurance_env` 的 handback 居所，不再需要字面例外。

### 4.4 假 `claude` 替身（S5，`tools/lib/realverify/fakeclaude.py`）
- 以 PowerShell 5.1 `Add-Type -OutputType WindowsApplication -OutputAssembly <家>/bin/claude.exe` 產生（Windows 內建、無需安裝；GUI 子系統 ⇒ `CREATE_NEW_CONSOLE` 下不建主控台視窗）。`<家>`＝執行檔所在 `bin` 目錄的上一層；設定檔皆在 `<家>`。
- **行為（r3，第二輪 QA P2-1）**：先把 argv、cwd、時間、採用的模式寫成一行 JSON 到 `<家>/fakeclaude.jsonl`，再依 `<家>/fakeclaude.mode`（缺席＝`fail`）：

| 模式 | 適用 argv | 動作 | 對應現行 spawn 成功判準 |
|---|---|---|---|
| `resume_ok` | 含 `-r <sid>` 且不含 `--fork-session` | 往 `<projdir>/<sid>.jsonl` 追加一行 `{"type":"fakeclaude",…}`，之後存活 `fakeclaude.sleep` 秒（缺席＝20）再 rc 0 | `spawn_resume`：逐字稿變大∧行程活（`park_cli.py:351-362`） |
| `fresh_ok` | 不含 `-r`，或含 `--fork-session` | 新建 `<projdir>/<uuid4>.jsonl`（一行同上），存活 `sleep` 秒再 rc 0 | `handoff.spawn`：出現新檔∧行程活（`handoff.py:450-461`）；QW fork |
| `fail` | 任何 | 立即以 `fakeclaude.rc`（缺席＝1；可設 0 模擬「起來了但沒寫逐字稿」）結束 | 兩者皆判失敗 |
| 成功模式遇不適用 argv | — | 照 `fail` | 防止「模式設錯也綠」 |

- `<projdir>` 取自 `<家>/fakeclaude.projdir`（案例以 `handoff._project_dir(<cwd>)` 算出後寫入；缺席 ⇒ 照 `fail`，不自行推算 slug——slug 規則的 SSOT 留在 Python 端）。成功模式寫入的 `<projdir>` 在寫 `fakeclaude.projdir` **之前**先登記 L2 `transcript_dir` 列（沙盒 slug 目錄 `Sandbox.create` 已登記；正式替身 repo〔E2E-SE-09〕與家外替身由該 E2E 自己登記）。
- 判定表的 SSOT＝純函式 `fakeclaude.decide(argv, cfg) -> Action`；C# 原始碼由同一張表產生（AT-SE-46 驗表、E2E 驗真執行檔）。
- **QW 的正控用 `resume_ok`**（§10.2-7）；fork／FRESH 路的正控用 `fresh_ok`；失敗注入用 `fail`。
- 產生前寫 L2 `temp_file` 列；產生失敗（無 PowerShell 5.1）⇒ 依賴它的 E2E 判 ENV。
- **家外替身**（E2E-SE-01(i)、E2E-SE-06(c)）：同一產生器輸出到 `%TEMP%\AutoSDD_RVout_<run_id>\bin\claude.exe`（名稱刻意不含 `AutoSDD_RV_sbx_`，不在任何沙盒家目錄之下；先登記 L2 `temp_file`）——用來驗 D-18，突變拿掉判準時被叫到的也只是替身。

---

## 5. L2 副作用帳與崩潰安全清理：`tools/lib/realverify/leases.py`

### 5.1 帳格式（`~/.autosdd/realverify_leases/<run_id>.jsonl`，只追加、原子 append）
`{"at","kind","ident","undo","owner_pid","owner_started","expires_at","state"}`；`kind ∈ {sandbox_root, sched_job, transcript_dir, process, worktree, temp_file}`；`state ∈ {intent, made, revoked, unverified, abandoned, closed}`。

### 5.2 先登記後動作；收尾順序
- 每個副作用**之前**寫 `intent` 列；做完寫 `made`。只寫了 `intent` 的列在重放時同樣要撤。
- 載具自己做的：`Sandbox.create`（`sandbox_root`、`transcript_dir`）、`sched.register_once`（`sched_job`）、`interactive.trusted_sandbox`（`sandbox_root`〔外層〕、`worktree`、探針 `process`、`temp_file`）、`open_window`（`process`，以沙盒 sid 為鍵）、假 `claude`（`temp_file`）。
- 被測產品做的：以 `sandbox_root` 與沙盒 sid 兩列涵蓋——重放時 Action 字樣含沙盒根的排程、命令列含沙盒 sid／根的行程，一律歸該沙盒（§5.3 發現式掃描）。
- **`ctx.close()` 第一步 `revoke` 該 run 所有沙盒的租約**，再拆行程、排程、目錄（r2，QA P3-7：拆到一半時到點的 job 必被 L1 拒）。

### 5.3 重放（`replay(now)`）
- 孤兒判準（D-16）：主人**可驗證存活**（pid 存在且建立時間相符）⇒ 不是孤兒、不撤；主人可驗證已死（pid 不在，或建立時間不符）⇒ 孤兒；主人存活驗不到（讀不到建立時間）⇒ 以 `expires_at` 已過為準。
- 撤銷順序：process（先驗命令列含沙盒 sid 或根——含 QW `--fork-session` 新窗，其命令列帶舊 sid——驗不到不砍，記 `unverified`；下次重放時該 pid 已不存在 ⇒ 轉 `revoked`）→ sched_job（`Unregister`，回讀確認不存在）→ worktree（`worktree remove`＋`prune`，宿主不動）→ sandbox_root／transcript_dir／temp_file（rmtree，失敗 5 次重試同 `_remove_tree`）。每項寫 `revoked`；全數 revoked 或 abandoned 寫 `closed`。
- 發現式掃描（未登記殘留）：排程 `AutoSDD_*` 的 Execute／Arguments／WorkingDirectory 含 `AutoSDD_RV_sbx_`、且無「主人可驗證存活」的身分檔指向它 ⇒ 撤；**（r5，D-27）含 `AutoSDD_RVprod_<run_id>`（E2E-SE-09 的正式目標替身 repo；刻意無身分檔）⇒ 以該 `<run_id>` 的 L2 帳主人判：主人可驗證存活 ⇒ 留；帳不存在、主人已死或帳已 `closed` ⇒ 撤**；`%TEMP%\AutoSDD_RVprod_*` 目錄與 `~/.claude/projects/*AutoSDD-RVprod-*` 同一主人判準 ⇒ 刪；`%TEMP%\AutoSDD_RV_sbx_*` 家目錄的身分檔主人已死（或無身分檔且 mtime 超過 `LEASE_CAP`）⇒ 刪；`~/.claude/projects/*AutoSDD-RV-sbx-*` 而沙盒家已不存在 ⇒ 刪（`~/.claude/sessions` 有活 cwd 指向者跳過）。
- 撤不掉的 ⇒ 回 `unrevoked` 清單；`runner.run` 開頭見非空 ⇒ 整批拒跑（D-11），並：寫 handback `<handback 居所>/realverify_orphans_<run_id>.md`（居所＝`endurance_env` 的 `AUTOSDD_HANDBACK_DIR`，預設真 `~/.autosdd/handback`；列每項 ident、撤不掉的原因、`sweep --abandon` 指令）、依 `quota_escalation.enqueue` 既有語意入通知佇列（佇列居所＝`trace_dir()`；通知開關關閉時照其規則不入列）。
- `sweep --abandon <run_id> --why "<至少 8 字>"`：把該帳未完成列記 `abandoned`（附 why）後寫 `closed`；只動帳，不砍行程、不刪檔；之後 run 不再因該帳拒跑。殘留物仍由發現式掃描在條件成立時處理；**發現式掃描的項目若以正規化路徑（`resolve()`＋`normcase`）等於任一 abandoned ident 或位於其下 ⇒ 只記 note，不計入 `unrevoked`**（r3，D-11）。

### 5.4 OS 自毀（沙盒目標專屬）
`schedule_backend` 登記一次性工作新增選用參數 `expire_at`：Windows 寫 Trigger `EndBoundary`＋Settings `DeleteExpiredTaskAfter=PT0S`；macOS 忽略（誠實劃界）。站點呼叫 `sandbox_scope.job_expiry(home)`，正式目標回 None ⇒ XML 與現行逐字相同。因 `register_verdict` 已保證 `fire_at ≤ allow_until`，登記出來恆有 `EndBoundary ≥ StartBoundary`；「從未執行即過期」的自刪時延以 §0.4-4 探針實測。

### 5.5 收斂成一個家
`sched.cleanup_all_rv`、`Sandbox._disarm_oldwin_tasks`、`cases/sessionctl_park.park_cleanup`、`sandbox.sweep_orphans` 改為呼叫 `leases.replay`／`leases.revoke_run(run_id)` 的薄殼；鎖：realverify 套件內呼叫排程撤銷的函式只准在 `leases.py`。

### 5.6 入口
`python tools/realverify.py sweep [--dry-run]`（重放＋發現式掃描；末行 `SWEEP_VERDICT=clean|revoked n=<k>|unrevoked n=<k>`，判決 rc 0，真錯誤才非 0）；`--abandon <run_id> --why`；`--legacy [--apply]` 見 §9。`sessionctl status` 增一行「realverify 孤兒 n」（唯讀，只讀帳檔）。

---

## 6. L3 每案副作用快照：`tools/lib/realverify/snapshot.py`

### 6.1 面（全部唯讀）
| 面 | 取法 |
|---|---|
| 排程 | `AutoSDD_*` 名稱＋Action 文字（`Get-ScheduledTask`；macOS `launchctl list`） |
| 真 `~/.autosdd` 一般目錄 | `handoff/`、`handback/`、`plans/`、`traces/park/`、`traces/keepwarm/`、`traces/watch/` 第一層檔名 |
| 真 `~/.autosdd` S10 目錄（r2） | `context_feed/`、額度快取目錄、`selfimproving/` 第一層 (名稱, mtime, size)；diff 時對新增或 (mtime, size) 改變的檔讀內容（上限 1 MB）找沙盒字樣 |
| 真痕跡 jsonl | `traces/*.jsonl` 各檔的位元組長度；diff 時只讀新增段、找沙盒字樣 |
| `~/.claude/projects` | 目錄名集合 |
| `~/.claude/sessions` | 檔名＋（sid, cwd） |
| `~/.claude.json` | `projects` 鍵名集合（只讀鍵名，不讀值、不寫） |
| 行程 | 名稱 `claude*`／`node*` 的（pid, 命令列） |

### 6.2 斷言
`runner.run_case`：前快照 → 案例 → `ctx.close()`（先 revoke 再清理）→ 後快照 → diff；含沙盒字樣（D-9）的新增或改動項 ⇒ 案例判 `fail`，detail 首行 `SIDE-EFFECT LEAK`，逐項列出；其他差異進 notes `SNAPSHOT-NOISE`。`~/.claude.json` 新增鍵**一律**判 fail。**批次層**（r2）：批次前 vs 批次後整體 diff **只判同一規則**（含本批任一沙盒字樣的項＋`~/.claude.json` 新增鍵）⇒ `REALVERIFY_VERDICT=fail reason=leak`；其他差異只記入批次 notes。
入口：`python tools/realverify.py snapshot --out <檔>`、`snapshot --diff <前> <後> [--tokens <檔>]`（唯讀）。

---

## 7. F5 信任框方案的定位

- F5（`interactive.py`）解的是 **S13 與「載具自己開的窗」**。它不處理產品在未來或他行程開的窗——那是 L1。
- 接點：案例要讓**產品**開真窗（RV-PR3 類正控）時，必須 ①沙盒來自 `trusted_sandbox`（`assert_trusted` 過）②`grant(window=True)`；`CaseContext.grant_side_effects(sb, minutes, window=True)` 先呼叫 `assert_trusted`，不過即 `NotTrusted`（判 ENV）。身分檔 `window=true` 是 D-18 唯一的放行條件（r3）：沒有它，沙盒目標的任何 spawn／headless 站點都不准用沙盒家目錄外的執行檔。**本設計的 E2E 一律不走這條**（D-14：產品開窗的驗證用假 `claude`）；它只供 F5／QW 的「真窗半」使用。
- F5 自己產生的副作用全部進 L2 帳（§5.2）；worktree 改建在 `<外層>/wt`（§3.1）。
- `close()` 先 `revoke`（§5.2）。

---

## 8. 模式、無人窗口、讀不到

| 情形 | L1 | L2／L3 |
|---|---|---|
| 正式目標（掌舵者真 session） | 放行；無新增痕跡、無 `EndBoundary` | 不涉及 |
| 沙盒目標、租約有效 | 放行；登記排程帶自毀；`fire_at > allow_until` ⇒ 拒 | 帳記錄、案例結束先 revoke 再撤 |
| 沙盒目標、租約過期／主人死／身分檔讀不到 | 拒（終局，不進失敗鏈） | 下次 realverify 開頭撤（主人可驗證存活者不撤） |
| 無人窗口（`AUTOSDD_UNATTENDED`） | 判準不讀 env，行為同上；既有圍籬照舊在其後 | 同上 |
| `AUTOSDD_SESSION_SWITCH_MODE=notify/off`（案例經 `--job-env` 轉送到 job） | 判準先於模式檢查；拒絕時痕跡是 `sideeffect_refused` 而非模式訊息 | 同上 |
| 沙盒目標、租約有效，但 spawn／headless 要用沙盒家目錄外的執行檔（含未帶 `--claude`）且身分檔 `window≠true` | 拒 `sandbox_real_exe`（終局，r3，D-18）；spawn 站點回 `RC_SIDEEFFECT_REFUSED`、呼叫端記 `refused`（r4，D-24） | 同上 |
| 正式目標、掌舵者行程環境 `AUTOSDD_DESKTOP_NOTIFY=1` 或顯式空 `AUTOSDD_SENTINEL_OFF=` | 判準不讀 env；登記照常成功、job argv 與現行逐字相同（D-20 r4） | 不涉及 |
| 判準拋例外 | 拒（fail-closed） | — |
| 居所指向已刪沙盒（真 tools） | 入口 `ResidenceMissing` rc 9（`RC_RESIDENCE_MISSING`）、零寫入（D-17） | 發現式掃描撤該工作 |

**沒有逃生口環境變數**（D-4）。要在沙盒驗真窗，唯一路徑是案例授與租約＋F5（`window=true`，不在本設計 E2E 內；E2E-SE-16 的隱藏視窗由載具自有入口 `open_window` 起，不經產品 spawn 站點）。

---

## 9. 現存外洩清單與處置建議（只讀普查結果，2026-11-20；本棒不動）

| # | 物件 | 現況 | 建議處置 | 誰做 |
|---|---|---|---|---|
| X1 | `~/.autosdd/handoff/_quarantine/57d0ccad-…_20261120T024515Z.md`＋`.resumed` | F6 已隔離 | 保留到本設計 E2E-SE-01 重放取完樣本後刪 | 主控（`sweep --legacy --apply`） |
| X2 | `~/.autosdd/handoff/_quarantine/handback/ccddda28-….md` | 已隔離 | 同上 | 同上 |
| X3 | `~/.autosdd/handoff/aab03328-….checked`、`d7ad5eb4-….checked` | **仍在真目錄** | 刪 | 同上 |
| X4 | `~/.autosdd/context_feed/57d0ccad-….json` | **仍在** | 刪 | 同上 |
| X5 | `~/.autosdd/traces/park/57d0ccad-….json` | 仍在（終態） | 刪 | 同上 |
| X6 | `traces/autosdd_session_switch.jsonl` L469～L473、L480～L485；`autosdd_sentinel_unloads.jsonl` L73～L97 中沙盒列 | 共用只追加帳 | **不刪**（史料；量測面以沙盒字樣過濾） | — |
| X7 | `~/.claude/projects/*AutoSDD-RV-sbx-*` 3 目錄（78znhvop、og6lrctv、truqufqq） | 沙盒根皆已不在 | 78znhvop 保留到 E2E-SE-01 取樣後刪；其餘 `realverify sweep` 刪 | 主控 |
| X8 | `~/.claude.json` 兩把 `AutoSDD_RV_sbx_78znhvop` 信任鍵 | 失效 | **建議移除**；全域設定，須掌舵者同意；本設計任何程式不寫此檔 | 掌舵者 |
| X9 | `realverify_kept/` 65 目錄 | 屬設計 | 不屬外洩；另案訂上限 | — |

`realverify sweep --legacy`：以上 X1～X5、X7 的固定清單＋「真 `~/.autosdd` 任意檔名含已知沙盒 sid」；無 `--apply` 只列；`--apply` 才刪；永不觸及 X6、X8。

---

## 10. 工作包切分（鐵律七：鎖的持有面）

前置（全部包）：**R217 期 A 收尾 commit（A9）＋R218 F5 `interactive.py` 落 commit**。WHY：`sandbox.py`、`runner.py`、`driver.py`、`park_cli.py`、`handoff.py`、`tools/realverify.py`、`tools/sessionctl.py`、`test_realverify_lib.py` 目前皆為 M，`interactive.py` 為 ??；同一持有面不得並行。
與 QW 的序（QW r3 §12 已採）：A9＋F5 → S1 → {S2 ∥ S3 ∥ S5} → S6 → QW Q 系列（Q1／Q2／Q5 可與 S2／S3／S5 並行）→ QW Q6（含 E2E-SE-17 案例，§10.2）→ S7 的 E2E-SE-17 OI 結案。共通：並行包不重釘棘輪、不寫帳本、不改 CI paths。

### 10.1 本稿工作包
| WP | 內容 | 動到的檔 | 前置 | 並行 |
|---|---|---|---|---|
| S1 | §0.4-4 EndBoundary 探針（第一動作）；判準核心 `sandbox_scope.py`（§3；含常數 `RC_SIDEEFFECT_REFUSED`，D-24）；`endurance_env` 的 `RESIDENCE_KEYS`／`JOB_ENV_KEYS`／`job_env_argv`／`apply_job_env`（§4.1）；`schedule_backend` 的 `expire_at`（§5.4） | 新：`tools/lib/sandbox_scope.py`、`tools/tests/test_sandbox_scope.py`、`tools/probe/sandbox_scope_endboundary.py`；改：`tools/lib/endurance_env.py`（守衛面）、`tools/lib/schedule_backend*.py` 與既有測試 | A9＋F5 | 單人（定介面） |
| S2 | sessionctl 站點：`_cmd_fire`（位置依 §3.4；RESUME 與 FRESH 兩路都傳 `opts.claude`，r3）／`spawn_resume`／`handoff.spawn`（`exe` 入判準）／`_cmd_park`（`--claude` 寫進標記 `claude` 欄）／`oldwin_sched` 的判準、`job_env_argv`（含 `JobEnvValueError`）、`--claude` 轉送；`refused` 讀取端（`park.STATUSES` 加 `refused`、`park --status`、`yields`、`stop_verdict`、SessionStart 公告，D-21）；spawn 站點回 `RC_SIDEEFFECT_REFUSED`、`_cmd_fire` 見之走 `refused` 終局（D-24）；`job_env_argv(env, sandbox=…)` 依 `register_verdict` 判決（D-20 r4）；`tools/sessionctl.py` 最先 `apply_job_env`；`status` 孤兒行（只讀帳檔，sessionctl 不 import realverify；格式常數由測試核對相等） | `tools/lib/sessionctl/{park_cli,handoff,oldwin_sched,park}.py`、`tools/sessionctl.py`、`tools/tests/test_sessionctl_{park,park_route,handoff,oldwin}.py` | S1 | 與 S3、S5 並行；子代理產 diff、主控親套（守衛面） |
| S3 | 非 sessionctl 站點：planner `_run_resume`／`_sentinel_tick`／`--probe-quota`（headless，D-22）、哨兵武裝、`engine_resume_job.arm`、openitems `drive`／入口、`quota_escalation` 呼叫者、`selfimproving/schedarm`、SI `patrol` 入口與 `patrolrun.launch`（r3）；planner 的 `--claude`（`--probe-command` 降別名）、SI 的 `--claude` | `tools/session_resume_planner.py`、`tools/lib/{sentinel_lifecycle,engine_resume_job,quota_escalation}.py`、`tools/lib/openitems/drive.py`、`tools/openitems.py`、`tools/lib/selfimproving/{schedarm,patrolrun}.py`、`tools/selfimproving.py` 與對應既有測試 | S1 | 與 S2、S5 並行 |
| S4 | （併入 S1～S3：job 環境轉送的各站點改動跟著站點所屬包走；本列保留編號以對應 ARC L4） | — | — | — |
| S5 | realverify 載具：身分檔與家目錄（含 worktree 改 `<外層>/wt`、`info/exclude`；r4：`LOCAL_EXCLUDES`／`RESIDENCE_DIRS` 單一常數、`install_tools._EXCLUDES` 改由其推得、`ctl_env` 撤 pop＋`arm_sentinel=`，D-23／D-25；`yields_claude` 擴充後重跑 InteractiveWindowEntryLockTest，D-22）、`Sandbox.env` 與 `SANDBOX_LOCAL_ONLY`、撤 `handoff_dir`／`real_traces`、`leases.py`（含 D-11 拒跑出口、`--abandon`）、`snapshot.py`（含 S10 (mtime,size)、批次層規則）、`fakeclaude.py`（三模式＋`decide` 表＋家外替身，r3）、`run --all` 排除 `sideeffect`／`sideeffect_selftest`（D-19）、`interactive._yields_claude` 升公開名、`cases/prd_px_wake2.py` 的通知開啟值不得進登記路徑（D-20）、`run_case`／`run` 包快照與開頭重放、`close()` 先 revoke、`interactive` 進帳、`CaseContext.grant_side_effects`（含 `lease_minutes`）、`realverify.py` 新動詞 `sweep`／`snapshot`、四套舊清理改薄殼；既有案例撤 `real_traces` 與需要到點放行的案例改用假 `claude` | `tools/lib/realverify/{sandbox,runner,sched,interactive,leases,snapshot,fakeclaude}.py`、`tools/realverify.py`、`tools/lib/realverify/cases/{sessionctl_park,prd_px_pace2,prd_px_wake2}.py`＋其他受影響案例（實作時以 AST 掃 `SITES` 觸發者列清單）、`tools/tests/test_realverify_lib.py`、新 `tools/tests/test_realverify_leases.py` | S1 | 與 S2、S3 並行；**與 QW Q6 不得並行** |
| S6 | E2E 家族 `sideeffect`（TCS §4，E2E-SE-17 除外）＋`cases.json` | 新：`tools/lib/realverify/cases/sideeffect.py`；改：`docs/06_quality/RealVerify_Protocol/cases.json` | S2、S3、S5 commit | 單人 |
| S7 | 收尾：棘輪重釘（新增 2 測試檔）、`Root_Layout` §3（新列 sandbox_scope；realverify 列加 `leases`、`snapshot`、`fakeclaude`、`interactive`；probe 列）、ADR-XPLAT-004 新節（編號現查）、根 CLAUDE.md（守衛面清單加 `tools/lib/sandbox_scope.py`；速查表加 `realverify sweep`／`snapshot`）、缺陷帳本 DEF（P1，現查最大號＋1）、PRD §16.6 本列 OI 回填與逐條結案、E2E 全跑入帳、`sweep --legacy --apply`（經主控同意）、REQ-SE-61 鎖 | 收尾面 | S1～S6 | 單人 |

### 10.2 需 QuotaWall 同步改的項目（本稿不改 QW；交 QW 持有者）
1. **E2E-QW-13** 改寫：不得以「SE L1 未授權時真拒絕」驗失敗鏈（D-13：L1 拒絕永不進失敗鏈）；改為沙盒授與足夠租約（`lease_minutes` 宣告）、以 `--claude <假 claude>` 且 `fakeclaude.rc`≠0 注入失敗，驗 §7.5 失敗鏈；handback／通知佇列必須落在沙盒居所（`--job-env` 轉送），通知開關經 `--job-env` 關閉。
2. QW Q3 新增的 `spawn_resume(fork=True)`、§7.3 job 內重排、§7.5 第 3 步通知與入列、§7.6 `_sentinel_tick` 接手分支，同 commit 進 `sandbox_scope.SITES` 並呼叫判準（AT-SE-17 的 AST 鎖會使漏登記即紅）；§7.3 重排用 `register_verdict`。
3. QW §7.3 的讓路觀察（`OBSERVE_SEC`）、`park_yield_primary`、`park_attempt` 一律排在 fire 站點 L1 之後（§3.4 第一列）；QW 的 `_cmd_fire` 黃金序列以 `park_job_start`→（L1 放行無痕跡）→ 原 QW 序列為準。**r4（QW r6 已同步，QW §7.0／§7.5-1a）**：spawn 站點 L1 拒絕（`RC_SIDEEFFECT_REFUSED`）＝終局 `refused`，不算失敗、不走另一路、不寫 handback／佇列／`notify`；該次 `park_attempt` 恰 1 筆（`reason=sideeffect_refused`、rc 記實際值）。
4. **E2E-SE-17**（QW 新站點的 L1 真機驗證，TCS §4）的案例程式隨 QW Q6 落在 `cases/sideeffect.py`（cases 單一持有面）；SE S7 對它以 OI 承接，QW Q6 收尾時結案。
5. QW 全部 E2E：需到點真跑產品 spawn 的一律帶 `--claude <假 claude>`；QW 長案例（V-W1 4 小時）在 `grant` 時宣告 `lease_minutes`（≤ `LEASE_CAP`），登記時刻須滿足 `fire_at ≤ allow_until`。
6. QW 附錄 A／PRD 修訂表若引用「v2.1.25」，以本稿附錄 A 新版號說明為準（兩稿一致：v2.1.24＝R218 QuotaWall r3 含 R218-C；v2.1.25＝R218-B）。
7. **（r3）替身模式**：QW r4 §16 V-W7 的「替身 rc 0 ⇒ 正控」改為「替身 `fakeclaude.mode=resume_ok`（RESUME 路）／`fresh_ok`（fork 或 FRESH 路）⇒ 正控」；`fail`（`fakeclaude.rc`≠0）⇒ 失敗鏈注入。rc 0 而不寫逐字稿在現行成功判準下是**失敗**（§4.4），QW 原寫法做不出正控。正控案例須讓 F4 選路可預期（RESUME：逐字稿含 usage 記錄、上下文小、快取冷；FRESH：逐字稿無 usage ⇒ 量不到），並斷言 `park_route` 的 route 與所設模式一致。
8. **（r3）每一次 spawn 嘗試同一執行檔**：QW Q3 的 §7.4 fork、§7.5 失敗鏈另一路一律傳 `opts.claude`；§7.6 哨兵接手讀 park 標記的 `claude` 欄（SE S2 讓 `park` 寫入；QW S-17「job 只吃標記與 argv」相容）。QW Q3 同 commit 補 AT：三處 runner argv[0] 皆為替身。漏傳時 D-18 以 `sandbox_real_exe` 終局拒絕（不進失敗鏈）。
9. **（r3；r4 擴）黃金序列重釘**：AT-SE-31、E2E-SE-09 的 `_cmd_fire` 正式路徑黃金序列，以及 **E2E-SE-01(e1)(e3)、E2E-SE-09(b) 的 `park_attempt` 斷言**（Q3 前 0 筆、Q3 後恰 1 筆 `attempted=true`）與 E2E-SE-09(c) 的標記 `desktop_notify`＝`1` 斷言，在 QW Q3 改動 `_cmd_fire` 後必須重釘，**由 QW Q3 同一個 commit 負責**（序列＝`park_job_start`→〔L1 放行無痕跡〕→QW 新序列）；SE S2 先以 Q3 前的序列釘一次。
10. **（r4）spawn 站點 L1 拒絕的呼叫端語意**：QW §7.5 與 §7.6 見 `RC_SIDEEFFECT_REFUSED` 一律走 `refused` 終局（D-24），QW AT-QW-69 第③例與 MU-QW-44 鎖；SE MU-SE-25 的預期隨之為「標記 `refused`、無第 2 筆 `park_attempt`、無 handback、替身 0 行」。
11. **（r4）到點時刻**：QW Q3 起排程登記在 `backup_fire_at`＝`--at`＋`BACKUP_GRACE_MIN`（10 分）。SE 的 E2E 一律以標記 `backup_fire_at`（Q3 前＝`--at`）或排程器 `NextRunTime` 決定等待，不寫死；租約檢查以實際登記時刻比 `allow_until`（E2E-SE-02 改 `park --at +10`）。
12. **（r4）正式目標的行為開關**：正式登記遇不允許值（例：`AUTOSDD_DESKTOP_NOTIFY=1`）不轉送、不拋、登記照常（D-20 r4），通知開關由 QW S-17 的標記 `desktop_notify` 承接；沙盒登記遇不允許值 rc 2。

### 10.2.1 跨規格介面對照表（r4；r5 補 X-19～X-22；QW r8 補 X-19 字面；兩稿共用的唯一真相源，QW r7／r8 §0.4-8 引用本節）
任一列字面改動須兩稿同一 commit 改；兩稿凍結以本表逐列 diff 核對為前置。
| # | 介面字面 | 值／語意 | SE 座標 | QW 座標 |
|---|---|---|---|---|
| X-1 | 替身執行檔 | `<家>/bin/claude.exe`（GUI 子系統）；家外替身 `%TEMP%\AutoSDD_RVout_<run_id>\bin\claude.exe` | §4.4 | §0.6 R-8、§16 表頭；TCS §4 共通 |
| X-2 | 替身模式載體 | `<家>/fakeclaude.mode`；缺席＝`fail` | §4.4；REQ-SE-27 | §0.4-8；TCS §4 共通 |
| X-3 | 三模式 | `resume_ok`（`-r <sid>` 且無 `--fork-session`，追加原 sid 逐字稿）／`fresh_ok`（無 `-r` 或含 `--fork-session`，新建 uuid 逐字稿）／`fail`（立即以 `fakeclaude.rc`〔缺席 1〕結束）；成功模式遇不適用 argv 照 `fail` | §4.4 表；AT-SE-46 | §0.4-8、§16 V-W7／V-W8；TCS §4 共通 |
| X-4 | 存活秒數 | `<家>/fakeclaude.sleep`，缺席 20 | §4.4 | §0.4-8（「成功模式存活 `fakeclaude.sleep`〔缺席 20 秒〕」）；TCS §4 共通（r5 改座標：S-20 只引用「行程仍活」判準、不提秒數） |
| X-5 | 逐字稿目錄 | `<家>/fakeclaude.projdir`（案例以 `handoff._project_dir` 算後寫入，先登記 L2） | §4.4 | TCS §4 共通 |
| X-6 | 執行檔傳遞 | argv `--claude <path>`；`_cmd_fire` 每一次 spawn 嘗試同一值；哨兵接手讀 park 標記 `claude` 欄（`park` 登記寫入，缺席＝`"claude"`） | D-14、§4.2；REQ-SE-25 | §7.4、§7.6；REQ-QW-44 |
| X-7 | fire 站點 L1 | `_cmd_fire` 在 `park_job_start` 之後、讀標記之前；拒絕 ⇒ `sideeffect_refused`、標記 `refused`、自拆、rc 0、無 `park_attempt` | §3.4 第一列；REQ-SE-10／16 | §7.0；REQ-QW-39 |
| X-8 | spawn 站點 L1 rc | `RC_SIDEEFFECT_REFUSED`＝10（`sandbox_scope` 常數）⇒ 呼叫端 `refused` 終局；該次 `park_attempt` 恰 1 筆 `reason=sideeffect_refused` | D-24、§3.4；REQ-SE-11 | §7.5-1a；REQ-QW-34／39；AT-QW-69③ |
| X-9 | 登記站點拒絕 | rc 4＋stderr reason＋`sideeffect_refused site=<站點>`；`lease_shorter_than_fire` 於 `fire_at > allow_until` | D-15、D-24；REQ-SE-12／18 | §7.3 A；REQ-QW-32 |
| X-10 | 標記狀態 | `park.STATUSES`＝既有五值＋`refused`；哨兵只接手 `failed` | D-21；REQ-SE-16 | §7.0、§7.6；REQ-QW-36 |
| X-11 | 到點時刻 | 排程登記於 `backup_fire_at`＝`primary_wake_at`＋`BACKUP_GRACE_MIN`（10 分）；Q3 前＝原登記時刻（`--at` 登記＝`--at` 值；短窗／`--why` 登記＝短窗 reset＋s）（r5） | §10.2-11；TCS E2E 共通 | §7.1、S-6；REQ-QW-30 |
| X-12 | `park_attempt` 計數 | Q3 後每次 spawn 嘗試（含成功）1 筆；單路成功＝恰 1 筆 `attempted=true`；Q3 前 0 筆 | §10.2-9 | §7.5-2；REQ-QW-34 |
| X-13 | 租約 | `LEASE_MAX`＝30、`LEASE_CAP`＝300 分；長案例宣告 `lease_minutes`；`fire_at ≤ allow_until` | D-2、D-15 | §16 表頭；TCS §4 共通 |
| X-14 | job 環境轉送 | `job_env_argv(env, sandbox=)`：通知只准空、哨兵只准 `1`（顯式空視同未設）、模式 `auto|notify|off`；沙盒遇不允許值拋（登記 rc 2）；正式遇不允許值靜默不轉送、永不拋 | D-20 r4、§4.1 | S-17；TCS §4 共通 |
| X-15 | 通知開關到 job | 正式：標記 `desktop_notify`（登記行程原值）AND argv 關閉值；沙盒：argv 帶空值 ⇒ 關；沙盒案例要驗「開」只能在登記後改寫標記（登記行程不得帶開啟值） | D-10、D-20；E2E-SE-09(c) | S-17、§7.5-3；REQ-QW-35；TCS §4 共通、E2E-QW-15 |
| X-16 | QW 新站點進 `SITES` | `spawn_resume(fork=True)`、§7.3 job 內重排（`register_verdict`）、§7.5 第 3 步通知與入列、§7.6 接手；QW Q3 同 commit | §10.2-2；REQ-SE-17 | §12 Q3；REQ-QW-39 |
| X-17 | 沙盒工作樹乾淨 | `LOCAL_EXCLUDES` 寫 `.git/info/exclude` ⇒ 建好居所與替身後 porcelain 空（FRESH 正控與 park 登記的前置） | D-23；AT-SE-01 | TCS §4 共通 |
| X-18 | 黃金序列重釘 | AT-SE-31、E2E-SE-09、E2E-SE-01(e1)(e3)、09(b)(c) 的 Q3 後版本由 QW Q3 同 commit 重釘 | §10.2-9 | §12 Q3 |
| X-19 | （r5）park 登記附帶武裝本 sid 哨兵 | QW Q3 起 `park` 登記時走既有 `--arm-sentinel` 路武裝 `AutoSDD_Sentinel_<sid>`（遵守 `AUTOSDD_SENTINEL_OFF`：有設 ⇒ 零次排程器呼叫、末行 `sentinel=absent reason=sentinel_off`〔QW r8 補字面〕；其他拒絕時末行 `sentinel=absent reason=…`）；SE 側：沙盒 `ctl_env()` 恆帶 `SENTINEL_OFF=1`、哨兵是 register 類站點（`sentinel_lifecycle` 武裝，§3.4）；正式目標替身（`AutoSDD_RVprod_`）的 E2E 要嘛設 `SENTINEL_OFF=1`、要嘛先記入 L2 並撤除；L2 發現式掃描認 `AutoSDD_RVprod_` | D-25、D-27、§3.4、§5.3；E2E-SE-09 | §7.1；REQ-QW-30；AT-QW-37、AT-QW-82（r8） |
| X-20 | （r5）痕跡名與 reason 詞彙 | 痕跡：`park_job_start`、`park_route`、`park_resumed`、`park_spawned`、`park_attempt`、`park_chain_failed`、`sideeffect_refused`（欄 `site`、`reason`）；L1 reason：`target_missing`／`root_mismatch`／`sandbox_unreadable`／`sandbox_no_lease`／`sandbox_lease_expired`／`sandbox_owner_dead`／`sandbox_real_exe`／`lease_shorter_than_fire`／`error:<類名>`；QW 失敗鏈 reason：`sideeffect_refused`（spawn 站點）、`platform_unsupported`、`intent_expired`、前置拒絕原因原樣 | §3.3、§3.4；REQ-SE-10～12 | §7.0、§7.5、§7.6；REQ-QW-34／36／38 |
| X-21 | （r5）沙盒哨兵顯式要求 | `cases/sessionctl_park.ctl_env(arm_sentinel=True)`＋呼叫點上方 `# WHY`；其餘沙盒一律 `SENTINEL_OFF=1` | D-25；AT-SE-18 | TCS E2E-QW-15 |
| X-22 | （r5）`park --status` 輸出 | SE：`refused` 狀態印 `refused` 與 reason（D-21）；QW：主載具／備援／哨兵三列（`primary: live pid wake_at mode`／`absent`、`next_run`／`absent`／`absent(platform)`、哨兵）；兩稿各自加列、互不改對方列，`refused` 標記下三列照印 | D-21；AT-SE-43 | §10、S-9；REQ-QW-37；AT-QW-55 |

**本節判準**：任兩包並行欄對稱；`sandbox_scope.py` 只出現在 S1 commit（S2／S3／S5 與 QW Q3 只消費、只在 `SITES` 加列）；`cases/sideeffect.py` 與 `cases.json` 只出現在 S6 與 QW Q6 commit；棘輪重釘只在 S7。

---

## 11. 模組落點表（照 `Root_Layout_and_Module_Placement.md` §2）

| 元件 | 路徑 | §2 格 |
|---|---|---|
| 判準（單檔共用工具） | `tools/lib/sandbox_scope.py` | 函式庫單檔（D-3） |
| job 環境轉送 | `tools/lib/endurance_env.py`（既有 SSOT 擴充） | 既有額度／守衛單檔 |
| 副作用帳、快照、假 claude | `tools/lib/realverify/leases.py`、`snapshot.py`、`fakeclaude.py` | 函式庫（realverify 既有套件） |
| 探針 | `tools/probe/sandbox_scope_endboundary.py` | 探針 |
| 指令入口 | `tools/realverify.py` 新動詞 `sweep`、`snapshot`；`tools/sessionctl.py status` 增一行 | 指令入口薄殼 |
| 測試 | `tools/tests/test_sandbox_scope.py`、`tools/tests/test_realverify_leases.py`（新 2 檔）；其餘擴充既有檔 | 測試 |
| E2E | `tools/lib/realverify/cases/sideeffect.py`；結果帳 `docs/06_quality/RealVerify_Result_Ledger.md` | realverify 既有套件 |
| 執行期資料 | `~/.autosdd/realverify_leases/`；沙盒家目錄 `/.autosdd_sandbox.json` | repo 外執行期資料 |
| 痕跡 | `trace_dir()` 下既有 `autosdd_session_switch.jsonl`（事件 `sideeffect_refused`） | repo 外執行期痕跡 |
| 規格 | 本稿；`docs/03_testing/contracts/TCS-SideEffectIsolation-20261120.md` | 需求／設計、測試契約 |
| 守衛面 | `tools/lib/sandbox_scope.py`（新增進根 CLAUDE.md 守衛面清單）、`tools/lib/sessionctl/**`、`tools/lib/endurance_env.py`、`tools/session_resume_planner.py` | 守衛面（暴露證據見 §1） |
| CI | 單檔由既有 `tools/lib/**` paths 涵蓋（S7 現查 `test_ci_paths_cover_root_consumers.py`）；不新增 workflow | CI 接線 |

---

## 12. 被否決的方案

| 方案 | 否決理由 | 反向鎖 |
|---|---|---|
| 擴大 env 黑名單／改白名單（只在案例行程） | env 是案例行程的屬性，排程 job 繼承不到 | AT-SE-05、AT-SE-35 |
| 產品讀 `AUTOSDD_REALVERIFY=1` 自我拒絕 | 同上；只製造假外觀 | MU-SE-02 |
| 「目標 slug＝本 repo 主 checkout」單獨當判準 | 到點 job 跑沙盒內 tools 複本，恆成立（D-1） | AT-SE-03、E2E-SE-01 |
| 改寫 `USERPROFILE`／`HOME` 到沙盒 | `claude` 認證與信任綁家目錄 | — |
| 強化 finally／atexit／signal | taskkill /F、撞額度、斷電都不跑 | E2E-SE-02 |
| 全部 mock、禁真排程 | 違反「所有功能真機 E2E」鐵令；本設計改以假 `claude` 只替換「會燒額度、會開窗」的那一個執行檔，排程、行程、目錄、痕跡全真 | — |
| 預植 `~/.claude.json` 信任鍵／用 `CLAUDE_CONFIG_DIR` | 掌舵者禁止 | AT-SE-24 |
| 只把排程改沙盒前綴 | 只解決「掃得到」，到點照開 | E2E-SE-01 |
| 對所有一次性排程加 `EndBoundary` | 正式 park 遇睡眠補跑會被丟掉 | AT-SE-11 |
| 專用 Windows 帳號／VM | 需管理員與第二組憑證；遠期候選 | — |
| 快照 diff 全差異判 fail（單案或批次） | 真主控並行工作造成假紅 | AT-SE-21、MU-SE-19 |
| 給 L1 一個逃生口 env | D-4 被推翻；要驗真窗走租約 | MU-SE-02 |
| （r2）L1 拒絕走 QW 失敗鏈以便「不得無聲」 | 失敗鏈的 handback／通知在沙盒裡就是 S14 外洩；拒絕本身有痕跡與 job 結局，不是無聲 | AT-SE-38、MU-SE-16 |
| （r2）job 環境轉送 `AUTOSDD_UNATTENDED` | 會在 L1 之前以另一理由拒絕，遮住 L1 的驗證 | AT-SE-35 |
| （r2）job 環境轉送通知「開啟」值 | 案例不得藉此在真桌面開 toast | AT-SE-35 |
| （r2）以 env 鍵指定替身 `claude` | 測試用環境變數鉤；改走 argv `--claude` | AT-SE-36 |
| （r2）EndBoundary ≤ StartBoundary 也照登 | 排程器行為無現查證據；改登記前拒 | AT-SE-40、MU-SE-18 |
| （r2）身分檔放 worktree 根 | `worktree add` 要求空目錄；且弄髒工作樹 | AT-SE-01 |
| （r3）只在 RESUME 路傳 `--claude`、其他路靠紀律 | FRESH 路與失敗鏈仍打真 `claude`（第二輪 QA P1-1）；改為每一次嘗試同一值＋D-18 結構兜底 | AT-SE-44、AT-SE-45、MU-SE-25／26 |
| （r3）替身寫完 argv 即 rc 0 當「成功」 | 現行 spawn 成功判準與 rc 無關（逐字稿增長／新檔＋行程活），恆判失敗；正控與「恰 1 次」做不出 | AT-SE-46、MU-SE-31 |
| （r3）RV-SE03 以環境標記防重入 | 測試用環境變數鉤；家族排除是結構正解 | AT-SE-47、MU-SE-27 |
| （r3）`job_env_argv` 遇不允許值靜默略過 | 到點才 rc 2＝靜默壞掉 | AT-SE-48、MU-SE-30 |
| （r4）不允許值對正式目標也拋例外 | 掌舵者自行 opt-in 通知即讓正式 park／oldwin／SI 登記全壞（REQ-SE-15） | AT-SE-49、MU-SE-32 |
| （r4）spawn 站點拒絕沿用 rc 4 | 與無人窗口／模式非 auto 等既有拒絕撞號，呼叫端分不出「不該叫醒」與「叫醒失敗」 | AT-SE-50、MU-SE-33 |
| （r4）正式替身 repo 以環境變數擋 FRESH | 測試用環境變數鉤；改用現行 `handoff._refusals`（未追蹤檔＋無 wip tag） | E2E-SE-09 |
| （r4）沙盒居所改放 git 根之外 | 居所在 `<家>/<名>` 是 L2 撤銷與快照比對的前提；`.git/info/exclude` 不動目錄結構即可 | AT-SE-01 |

---

## 13. Token 帳（推論標明）

- 本案損失（SA 去重值）：幽靈階段 output 6,504、cache_read 560,249、cache_create 83,497；另 17:49 冷重寫 34,631＋後續數筆。L1 在 10:47 到點即拒 ⇒ 這些全部不發生（推論：判準在 spawn 前）。
- 判準本身零 token；正式路徑多一次 `is_sandbox`（字串）與幾次 `exists`。
- E2E-SE：除 E2E-SE-03（既有 `realverify run --all` 的花費）與 E2E-SE-16（F5 宿主下一次 haiku 啟動）外，**全部不呼叫真 `claude`**；正控與突變實跑一律打到假 `claude`（D-14），MU-SE-05 等「判準被拿掉」的突變實跑也只會讓假 `claude` 被呼叫一次，不開窗、不燒額度。

---

## 附錄 A：PRD 修憲（§16.5 (i)；已由本棒追加進 PRD，修憲前原文一字不動）

| 編號 | 落點 | 內容摘要 |
|---|---|---|
| A-1 | 修訂表 v2.1.24 列之後 | 新列 **v2.1.25**（R218-B）。版號說明（r2）：v2.1.23 由 R217 預留；v2.1.24 由 R218 QuotaWall r3（含 R218-C）佔用；本列取 v2.1.25 |
| A-2 | §11.4 最末條之後 | `【v2.1.25 註記】`：本節「成功註冊 OS 排程任務」在驗證載具中執行時受 §11.9 約束 |
| A-3 | §11.8 之後、`---` 之前 | 新增 `### 11.9 真機驗證載具的副作用隔離【v2.1.25 新增】`：R-VER-1～6。r3 就地改（草案未凍結）：R-VER-2「通知與哨兵只准帶關閉值；選路模式可帶合法值（`auto`／`notify`／`off`），開窗後果一律由替身承接」「F5 宿主隱藏視窗除外」；R-VER-4 加「沙盒目標要用沙盒外的執行檔另須授權明示允許開窗」。r4 就地改：R-VER-2「開窗或起 `claude`」前加「到點 job 的」（D-26）、加「關閉方向以外的值只在沙盒目標拒絕登記；正式目標不轉送該值、照常登記」（D-20 r4） |
| A-4 | §15.5 第 12 條之後 | `13.【v2.1.25 新增】驗證載具不得對真環境留下會自己動的東西` |
| A-5 | §16.6 表最末列之後 | 新列 2026-11-20（第二列）。結案格（r2）依 R217 附錄 A-5／A-11 **不用 ⏸**，寫 `〔OI〕`：主控凍結本規格時以 `python tools/openitems.py open` 登記（實作 1＋E2E 18）後把 OI id 回填本格；E2E-SE-17 的 OI 標註「隨 QW Q6 結案」 |

**本附錄判準**：E2E-SE-14 以修憲前 blob（R217 收尾 commit 已落地則用其 SHA，否則 `133c3a38`）比對——修憲前每一行位元組不變，本稿新增恰為上表五處；R217 對既有行的行內改動（工作樹 diff 現有 3 個 `-` 行，hunk `@@ -2676`、`@@ -2720`、`@@ -2787`）以「行內只增不刪」判準（舊行為某一新行的字元子序列）放行，豁免來源＝`docs/02_architecture/WorkProgress_Axis_Design.md` 附錄 A；R218 QuotaWall 的並行追加另列。

---

## 附錄 B：SCG 審查 FAIL（r1）逐條處置

| QA 條 | 處置 | 座標 |
|---|---|---|
| P1-1 行為開關沒帶過排程邊界 | `JOB_ENV_KEYS` 允許表（7 居所＋模式＋通知只准空＋哨兵只准 1）、`--job-env`；AST 鎖改「沙盒 env 鍵 ⊆ JOB_ENV_KEYS ∪ SANDBOX_LOCAL_ONLY」；`--claude` 走 argv＋GUI 替身；E2E-SE-01(e)／09 改用假 `claude` | Q-4、D-6、D-14、§4、TCS REQ-SE-20～25、AT-SE-15／35／36、E2E-SE-01(e)／09／10 |
| P2-1 身分檔擋 worktree add、弄髒工作樹 | worktree 改 `<外層>/wt`、身分檔在外層；一般沙盒寫 `.git/info/exclude`；AT 斷言 porcelain 不變、add rc 0 | D-1、§3.1、REQ-SE-01、AT-SE-01 |
| P2-2 E2E-SE-01(c)(d) 跑不到預期 reason | L1 釘在 `park_job_start` 之後、讀標記之前；(c) argv 帶 `--job-env` 指向沙盒；(d) 改斷言 LastTaskResult≠0＋無開窗＋sweep 撤；`target_missing` 改在 (c′) 驗；新增 (h) ResidenceMissing | §3.3、§3.4、D-17、REQ-SE-10／26、E2E-SE-01 |
| P2-3 QW r3 新站點與 QW-13 衝突 | SITES 納入 fork／§7.3 重排／§7.5 通知／§7.6 接手；D-13 L1 終局；L1 先於 OBSERVE_SEC 與 r3 痕跡；fork 命令列帶舊 sid；QW-13 改假 `claude` | D-8、D-13、§3.4、§10.2、REQ-SE-16／17、AT-SE-10／38／39、E2E-SE-17 |
| P2-4 租約上限與到點不相容 | `register_verdict` 拒 `fire_at > allow_until`；`LEASE_CAP` 與案例宣告 `lease_minutes`；續租不延 EndBoundary；EndBoundary 探針；E2E-SE-04 改兩變體；E2E-SE-02 park 改 +20 分 | D-2、D-15、§0.4-4、§5.4、REQ-SE-03／18、AT-SE-40、E2E-SE-02／04 |
| P2-5 L2 誤撤活案例 | 主人可驗證存活 ⇒ 不是孤兒；`expires_at` 只兜底 | D-16、§5.3、REQ-SE-31、AT-SE-19 |
| P2-6 批次層全差異判 leak | 批次層同 D-9 規則 | D-9、§6.2、REQ-SE-41、AT-SE-21 |
| P2-7 REQ-SE-61 範圍與判準 | 加 `tools/run_local_nightly.*`、`tools/install_windows_nightly.ps1`、`tools/local_ci_gate*`；token 級判準；注入串列形態必紅 | D-12、REQ-SE-61、AT-SE-32 |
| P2-8 PRD 版號說明與 ⏸ | 修訂表版號說明改與 r3 一致；§16.6 改 `〔OI〕`；TCS §7 改 OI 判準；附錄 A-1／A-5 同步 | 附錄 A、TCS §7、PRD 修訂表 v2.1.25 列與 §16.6 第二列 |
| P3-1 拒跑無出口 | 拒跑寫 handback＋依通知語意入列；`sweep --abandon`；`unverified` 行程已不在轉 `revoked` | D-11、§5.3、REQ-SE-37、AT-SE-41、E2E-SE-18 |
| P3-2 git 根解析開行程、吃 env | `git_root` 往上找 `.git`；比對前 `resolve()`＋`normcase` | D-4、§3.2、REQ-SE-04、AT-SE-07 |
| P3-3 AST 普查漏字串形態與 0x10 | SITES 普查認 `getattr` 字串與字面 `0x10`／`16` | §3.4、REQ-SE-07、AT-SE-17 |
| P3-4 MU-SE-05 實跑會跳真窗 | 全部 E2E 帶 `--claude <假 claude>`；突變轉紅的證據是假 `claude` 被呼叫，不開真窗；TCS 寫明 | D-14、§13、TCS §5 檔頭 |
| P3-5 PRD 行級比對會紅 | 「行內只增不刪」＝舊行為某新行字元子序列，限定三個 R217 hunk，豁免來源列明 | 附錄 A 判準、REQ-SE-60、AT-SE-34 |
| P3-6 覆寫既有檔假綠 | S10 目錄取 (名稱, mtime, size)、改動檔讀內容找字樣 | §6.1、REQ-SE-40、AT-SE-42 |
| P3-7 close 未先 revoke | `ctx.close()` 第一步 revoke | §5.2、§7、REQ-SE-31、AT-SE-23、MU-SE-20 |

---

## 附錄 C：第二輪 SCG 審查 FAIL（r2）逐條處置

| QA 條 | 處置 | 座標 |
|---|---|---|
| P1-1 `--claude` 只接 RESUME 路 | REQ-SE-25 改「每一次 spawn 嘗試（RESUME、FRESH、fork、§7.5 另一路、§7.6 接手〔讀標記 `claude` 欄〕）同一值」；L1 新判準 `sandbox_real_exe`（沙盒∧執行檔不在家目錄下∧`window≠true` ⇒ 拒，身分檔 `window` 進判準）；補 FRESH 路 AT 與 MU | Q-7、D-14、D-18、§3.2～3.4、§4.2、§8、§10.2-8；TCS REQ-SE-08／25、AT-SE-44／45、MU-SE-25／26、E2E-SE-01(e3)(i) |
| P2-1 替身不能模擬成功 | 替身 `mode=resume_ok|fresh_ok|fail`，成功模式寫逐字稿並存活 `sleep` 秒；`projdir` 先登記 L2；`decide` 表為 SSOT；QW 正控用 `resume_ok` | §4.4、§10.2-7；TCS REQ-SE-27、AT-SE-46、MU-SE-31、E2E-SE-01(e1)(e3)／09(b) |
| P2-2 真 traces 位元組不變違反 D-9 | E2E-SE-09、10 改「真 traces 新增段無沙盒或替身字樣」 | TCS E2E-SE-09／10 |
| P2-3 普查漏 headless 站點 | 普查重用 `interactive.yields_claude` 並擴 BoolOp／預設值；planner `probe_quota` 呼叫者、`patrolrun.launch`、SI `patrol` 入口入 `SITES`；`--claude` 統一、`--probe-command` 降別名 | D-22、§3.4、§4.2；TCS REQ-SE-07／25、AT-SE-17／36、E2E-SE-06(c) |
| P2-4 RV-SE03 遞迴 | `--all` 排除 `sideeffect`／`sideeffect_selftest` | D-19；TCS REQ-SE-38、AT-SE-47、MU-SE-27、E2E-SE-03 |
| P2-5 E2E-SE-18 在真環境留副作用 | D-11 handback／佇列走居所；NOOP 以沙盒居所執行，斷言真 handback 與真佇列前後不變 | D-11、§5.3；TCS E2E-SE-18 |
| P2-6 PRD R-VER-2 與 DES 不一致 | R-VER-2 改「通知與哨兵只准關閉值；模式可帶合法值，開窗後果由替身承接」 | PRD §11.9 R-VER-2；附錄 A-3 |
| P3-1 rc 3 撞號 | `RC_RESIDENCE_MISSING`＝9；AT 鎖與入口其他 rc 不相等 | D-17、§4.1；TCS AT-SE-48、E2E-SE-01(h) |
| P3-2 `--job-env` 越過 `--` | `apply_job_env` 遇 `--` 即停 | D-20、§4.1；TCS AT-SE-48、MU-SE-29 |
| P3-3 `refused` 讀取端 | `park --status`／`yields`／`stop_verdict`／SessionStart 公告認得 `refused` | D-21；TCS REQ-SE-16、AT-SE-43、MU-SE-28 |
| P3-4 不允許值到點才失敗 | `job_env_argv` 拋 `JobEnvValueError`，登記時 rc 2；`prd_px_wake2` 列入 S5 | D-20、§4.1、§10.1 S5；TCS REQ-SE-21、AT-SE-48、MU-SE-30 |
| P3-5 abandoned 不套發現式掃描 | 正規化路徑比對 abandoned ident | D-11、§5.3；TCS REQ-SE-37、AT-SE-41 |
| P3-6 MU 缺兩條 | MU-SE-23（abandon 後仍拒跑）、MU-SE-24（abandon 動到行程或檔案） | TCS §5 |
| P3-7 黃金序列在 QW Q3 後要重釘 | 由 QW Q3 同一 commit 負責 | §10.2-9；TCS AT-SE-31、E2E-SE-09 |
| P3-8 R-VER-2 與 F5 隱藏視窗字面衝突 | R-VER-2 加「F5 宿主隱藏視窗除外」；§8 註明 E2E-SE-16 走載具自有入口 | PRD §11.9 R-VER-2、§8；TCS 檔頭 |

---

## 附錄 D：第三輪 SCG 審查 FAIL（r3）逐條處置（r4，與 QW r6 聯合改版）

| QA 條 | 處置 | 座標 |
|---|---|---|
| P1-1 E2E-SE-09 漏傳 `--claude` 會在未信任目錄開真窗 | (b) 登記前以同一輸入預算 `park.fire_route`，非 RESUME 即調整逐字稿直到是；登記後刻意留未追蹤檔 `RVPROD_DIRTY.txt`、HEAD 不打 wip tag ⇒ 任何 FRESH 嘗試都被 `handoff._refusals` 在 runner 前拒絕；斷言「FRESH 嘗試若發生，以前置拒絕收場、替身記錄只有 RESUME 那 1 行」；§0.1-5 限縮為「沙盒目標」 | §0.1-5、D-23；TCS E2E-SE-09 |
| P2-1 沙盒工作樹變髒、前置檢查全拒 | `LOCAL_EXCLUDES`（身分檔＋7 居所＋`bin/`＋`fakeclaude.*`）寫 `.git/info/exclude`，與 `install_tools._EXCLUDES` 同源；AT-SE-01 斷言建好居所與替身後 porcelain 空 | D-23、§3.1、§4.3、§10.1 S5；TCS REQ-SE-01／23、AT-SE-01 |
| P2-2 spawn 站點拒絕的呼叫端語意 | 專屬 rc `RC_SIDEEFFECT_REFUSED`＝10；`_cmd_fire` 與 QW §7.5／§7.6 見之走 `refused` 終局；MU-SE-25 預期改寫；列 §10.2-10 | D-13、D-24、§3.4、§10.2-10、§10.2.1 X-8；TCS REQ-SE-11、AT-SE-12／50、MU-SE-25／33；QW §7.5-1a、AT-QW-69③、MU-QW-44 |
| P2-3 D-20 正式回歸、與 QW S-17 衝突 | 不允許值只在沙盒目標拋；正式目標不轉送該鍵、argv 逐字不變、登記照常；顯式空哨兵鍵視同未設；補 AT／MU；E2E-SE-09(c) 真機驗 | D-20、§4.1、§8、§10.2-12、§10.2.1 X-14／X-15；TCS REQ-SE-21、AT-SE-49、MU-SE-32；QW S-17 |
| P2-4 QW r5 介面未反映到 SE E2E | E2E-SE-02 改 `park --at +10`；01／04 到點時刻改讀標記 `backup_fire_at`／`NextRunTime`；(e1)(e3)、09(b) 改「`park_attempt` 恰 1 筆 `attempted=true`（Q3 前 0 筆）且無 `park_chain_failed`」；§10.2-9 重釘範圍加 (e1)(e3)、09(b) | §10.2-9／-11、§10.2.1 X-11／X-12；TCS §4 共通、E2E-SE-01／02／04／09 |
| P3-1 `park.STATUSES` 未擴 | D-21 寫明加 `refused` | D-21、§10.1 S2；TCS REQ-SE-16、AT-SE-43 |
| P3-2 rc 4 假綠 | 登記站點拒絕仍 rc 4，但驗收一律同時斷言 stderr reason 或 `sideeffect_refused` 痕跡；spawn 站點改專屬 rc | D-24；TCS AT-SE-11／12、E2E-SE-04(b)／05／06(a) |
| P3-3 `yields_claude` 擴充的連動 | 重跑 InteractiveWindowEntryLockTest、新命中入 commit 訊息與鎖；SITES 普查 glob 明定 | D-22；TCS REQ-SE-07、AT-SE-17 |
| P3-4 R-VER-2 未限定到點 job | PRD 句首加「到點 job 的」 | D-26、附錄 A-3；PRD §11.9 R-VER-2 |
| P3-5 `ctl_env` pop SENTINEL_OFF | 撤 pop；需要真哨兵者 `ctl_env(arm_sentinel=True)`＋WHY | D-25、§4.3；TCS REQ-SE-23、AT-SE-18 |

---

## 附錄 E：聯合 QA 第四輪（r4 FAIL：P2×2、P3×2）逐條處置（r5，與 QW r7 聯合改版）

| QA 條 | 處置 | 座標 |
|---|---|---|
| B-P2-1 QW §7.1 武裝哨兵使 E2E-SE-09 留真排程孤兒 | D-27：09 (a)(b) 登記行程設 `SENTINEL_OFF=1` 並斷言 `sentinel=absent`、該工作不存在；(c) 先把 `AutoSDD_Sentinel_<替身 sid>` 以 `sched_job` 記入 L2，Q3 後斷言武裝（`NextRunTime` 非空）再撤除、回讀不存在，Q3 前斷言不存在；(c) 的 Arguments 比對改為「(a) 去掉 `--job-env AUTOSDD_SENTINEL_OFF=1` 一組後逐字相同」；L2 發現式掃描加認 `AutoSDD_RVprod_`（以 `<run_id>` 帳主人判）；§10.2.1 補 X-19 | D-27、§5.3、§10.2.1 X-19；TCS REQ-SE-32、AT-SE-26、E2E-SE-09、MU-SE-34 |
| B-P2-2 spawn 站點 rc 殘留 rc 4 | AT-SE-39 與 E2E-SE-17(a) 的 `spawn_resume(fork=True)` 無租約改為以 `sandbox_scope.RC_SIDEEFFECT_REFUSED` 常數比對並斷言 reason `sandbox_no_lease`＋`sideeffect_refused`；E2E-SE-17(a) 拆兩種觸發：(a1) 直接呼叫 spawn 站點 ⇒ 常數 rc；(a2) 經真排程 `_cmd_fire` ⇒ fire 站點先拒（標記 `refused`、無 `park_attempt`、fork spawn 0 次）；§7.3 重排的登記站點拒絕仍 rc 4＋reason `lease_shorter_than_fire` | TCS AT-SE-39、E2E-SE-17(a)；D-24、X-8、X-9 |
| B-P3-1 09(b) 漏傳 `--claude` 的殘餘 | E2E-SE-09 前置：先跑 AT-SE-44（QW Q3 後再加 AT-QW-71）；任一紅 ⇒ 判 ENV、不登記 | TCS E2E-SE-09 |
| B-P3-2 09(c) 不敲 toast 的理由 | 寫明 (c) 模式＝`notify`：到點只到 `park_route` 後模式拒絕、不 spawn、不進失敗鏈，故 `desktop_notify`＝1 也不會呼叫 `notify` | TCS E2E-SE-09 |
| Q-P3-2／Q-P3-3（QW 報告，屬本表） | X-4 的 QW 座標改為 §0.4-8 與 TCS 共通；X-11 寫明 Q3 前 `--why`／短窗登記＝reset＋s；補 X-20（痕跡名與 reason 詞彙）、X-21（`ctl_env(arm_sentinel=True)`）、X-22（`park --status` 兩稿加列） | §10.2.1 |
| 計數 | REQ 42、AT 50、E2E 18 不變；MU 33→34（+MU-SE-34）；覆蓋 42／42 | TCS 表頭；PRD §16.6 第二列 |