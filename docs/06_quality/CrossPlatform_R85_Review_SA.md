# CrossPlatform_R85_Review_SA — R85 四方複審／SA（需求對齊守門人）

> **角色**：逐條查證掌舵者訴求「宣稱做到的是不是真的做到」＋「有沒有訴求被靜默漏掉」。
> **平台**：macOS（`darwin`）。凡涉 Windows 執行期者一律標「**靜態推論、未真機驗證**」。
> **紀律**：不採信任何自陳（交棒書／計畫書／各包報告）。每一筆附**我這回合真跑過**的指令與輸出。
> **唯讀**：本包除本檔外未寫入任何檔、零 git 寫入。
>
> 🔴 **本檔自己會踩一顆雷，先講**：檔名符合 `CrossPlatform_*.md` 慣例，
> 依 `tools/lib/governance_docs.py` 的 `_GOVERNANCE_DOCS` 須登記，否則
> `check_defect_log_crossref.py` 轉紅（**現況已因 `CrossPlatform_R85_Review_Architect.md`
> 未登記而 rc=1，見 SA-03**）。我持有面只有本檔、不得改 `tools/lib/` ⇒
> **收尾窗口必須把本檔與 Architect 檔一併登記**。

---

## §0 我這回合真跑過的指令與輸出（取證清單）

**快照時刻＝`2026-08-12T10:15:30+0800`，工作樹 `git diff` sha256 前 16 碼＝`fe748f3587c2178b`。**
🔴 **本輪工作樹在我複審期間仍在變動**（見 SA-14），下列 rc 皆附取得時刻。

| # | 指令（絕對路徑 python，**讀 rc 不接管線**） | 結果 |
|---|---|---|
| 1 | `.venv/bin/python tools/run_root_unittests.py` | **rc=1**；`[skip census] tools/tests@darwin 共 44 支：platform=44／debt=0／untagged=0` |
| 2 | `cd tools/tests && ../../.venv/bin/python -m unittest discover` | **rc=1**；`Ran 3284 tests`／`FAILED (failures=8, skipped=44)` |
| 3 | `.venv/bin/python tools/check_defect_log_crossref.py` | **rc=1**（10:15 快照；09:5x 時為 rc=0）＋ **早退：12 道檢查未執行** |
| 4 | `.venv/bin/python tools/check_defect_log_crossref.py --unresolved-count` | rc=0；`未結列數＝89／全部 181 列｜warn=86 fail=98` |
| 5 | `.venv/bin/python tools/check_hooks_liveness.py` | rc=0 |
| 6 | `.venv/bin/python tools/check_ntfs_paths.py` | rc=0（27628 tracked，0 違規） |
| 7 | `.venv/bin/python AutoClaude/tools/check_loc_budget.py --json` | rc=0 |
| 8 | `.venv/bin/python tools/check_wrapper_thinness.py` | rc=0 |
| 9 | `cd AutoClaude && ../.venv/bin/python -m pytest tests -q -rs` | **rc=0**；`4466 passed, 73 skipped in 98.56s` |
| 10 | `../.venv/bin/python tools/local_ci_gate.py --census-only` | rc=0；`AutoClaude/tests@darwin+pg+nested 共 73 支：platform=53／tool-absence=3／env-disabled=13／structural-pair=1／debt=3／untagged=0／欠債型 **19** 支（目標 0）` |
| 11 | `.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` | rc=0；`# 淨額 83319→83319 (+0)` |
| 12 | `repin_round_nets(_GUARD_LINES_REPIN_LOG)[-6:]` | `[(80,2334),(81,3033),(82,5400),(83,5260),(84,3755),(85,**481**)]` |
| 13 | `doc_guard_total_problems(docs, 83319, 'R85')` | **3 筆紅**（逐字見 SA-02） |
| 14 | `unittest tools.tests.test_platform_neutral_paths.TestXplatInjectionMatrix` | rc=0；`[Xplat injection matrix] Win2mac=6/12 mac2Win=5/10` |
| 15 | AST：`test_platform_neutral_paths.py` 檔級 `scan_*` 定義 vs `_injection_criteria()` 接線 | **12 定義／8 接線**（4 支未接線） |
| 16 | `gh run list --limit 12` | rc=0；最近一次 push（R84）**6/6 workflow failure，各 3s** |
| 17 | `launchctl list \| grep AutoSDD_Sentinel` | `-  0  AutoSDD_Sentinel_c426c871-…`（已武裝，rc=0） |
| 18 | `pmset -g custom` | `AC Power: … sleep 0 … displaysleep 10`（AC 段永不休眠） |
| 19 | `ls -l docs/06_quality/AutoSDD_Defect_Log.md` | **211,736 bytes**（warn 245,760 ⇒ 餘裕 **34,024 B ≒ 33.2 KB**） |
| 20 | `git diff --numstat`（全 tracked 樹） | `+2306 −1308 net=**+998**` |
| 21 | `diff .env.example .env` | **rc=0（逐位元組相同）**；`git check-ignore .env` rc=0；`.env` 未被 tracked |
| 22 | `.venv/bin/python tools/session_resume_planner.py --pace` | rc=0；`可派 4／cap=4／band=notice／binding=seven_day 68% 剩 5271 分鐘`；`來源=cache` |
| 23 | SA 第三方注入 `lib.unattended_authz.authz_hits` | **13/13 正確**（6 應擋全擋、7 應放全放，含 `git stash create` 正確放行） |
| 24 | SA 第三方注入 `autoclaude.execution.evaluator.portability_note` | **16/16 正確**（10 POSIX-only 全出聲、6 可攜全靜默，假陽性 0） |

**取數管道自證（凡「零命中」皆附對照組）**：
- 訴求 8 掃描（SA-04）：`Container/docker/compose` 全 0，**對照組同一份語料** `Archive=47`／`前沿=22`／`pmset=13` 皆非 0 ⇒ 管道有效，0 是真的 0。
- SDD hooks 缺 `CREATE_NO_WINDOW`（SA-07）：該目錄 grep rc=1（零命中），**對照組** 根 `.claude/hooks/sdd_hook_router.py:237` 命中 ⇒ 缺席為真。

---

## §1 逐條訴求真實狀態表（首要交付）

圖例：✅達成／🟡部分達成／❌未達成／⛔做不到（附結構性理由）

| # | 訴求 | 判定 | 憑證（我這回合實測） |
|---|---|---|---|
| **1** | mac／Win11 部署執行開發**無任何相容性 Bug** | ⛔ **今天不能宣稱** | 本輪 Windows **零真機**；且 CI 6/6 failure（取證 #16）⇒ **連雲端剖面都沒跑**。P4 自己也把所有 Windows 結論標「靜態推論」。這句話今天結構上不可查證，不是「查了沒問題」。 |
| **2** | 架構簡潔／不重複模組／**拿掉不合理機制** | ❌ | 全樹 **net +998 行**（#20）；護欄層 R85 **+481**（#12），與計畫書自封的「減法輪」相反。真減法確有（`check_wrapper_thinness.py` −177、SDD agents −75），但**被加法蓋過**。Architect ARCH-03 亦判「最大一筆可執行減法一行未動」。 |
| **3** | mac↔Win 雙向零落差 | ❌ | M5 未攔到題數 **Win→mac 6／mac→Win 5**（#14），門檻各 ≤1；**與 R84 逐字相同＝本輪零改善**，且接線率退步（#15）。 |
| **4** | Windows 低級錯誤**根因**徹底解決 | 🟡 | 機械物齊（`block_bash_on_windows`／`lint_powershell_command`／`block_destructive_git`）；`misstep_attribution.py` rc=0 可重跑（n=1243）。但最大桶仍是「宣稱先於查證」，而**本輪自己就犯了**（SA-02）⇒ 根因未解。 |
| **5** | 每輪挖深、Developer 清技術債 | 🟡 | 挖深屬實（P4 找出 `_SAFE_COND_PATTERN` 擋正解放反例，我複驗成立）。但**債總量上升**：未結 88→89、E501 139→141、護欄 +481。 |
| **6a** | 隨時監控、水位用 **%** | ✅ | #22 印 % 與剩餘分鐘；`--check` 印水位 39.9%。 |
| **6b** | %Usage＋Reset ⇒ 可派 Agent 數 | ✅ | #22 一行印可派數／cap／band／最緊軸具名＋距 reset 分鐘；`來源=cache`＝**零 token**。閾值 50/70 落地（#下）。 |
| **6C** | 85% 準備、95% 停止 | ✅ | `quota_policy.py --print-env-example`：`NOTICE=50／CONVERGE=70／PREPARE=85／HALT=95`，與訴求逐字對齊。 |
| **6c** | 不用盡、停止前記錄狀態 | 🟡 | 機制在（PREPARE 帶寫可重啟點任務書）。但**本輪未觸發過該帶** ⇒ 端到端未驗。 |
| **6d** | 用盡時**喚起同 session** 續作 | 🟡 | 哨兵已武裝且**活著**（#17；trace 09:56 仍在寫）。但痕跡**只有 `patrol` 分支**（逐字「無未處理撞線…續巡（本次零 token）」×8）⇒ **`arm_reset`／`probe` 兩個真正兌現 6d 的分支，production 從未走過**。 |
| **6e** | 度過 0~5h／**mac 調不休眠** | ✅（不休眠）／🟡（度過） | #18 `AC Power … sleep 0`＝永不休眠 ✅。「每 50 分鐘喚醒」已由 15 分鐘零 token 巡邏取代且理由充分。闔蓋期間不喚醒為**已知邊界**（`pmset repeat` 需 sudo，掌舵者否決）。 |
| **6f** | `.env.example` 測試、copy 到根 `.env`、**調成最佳值** | 🟡 | `.env` 存在於根、已 gitignore、未被 tracked ✅。但 **`diff` rc=0＝逐位元組複本**（#21）⇒「依實務調整成最佳值」**未做**。 |
| **6z** | 搜尋最新**前沿** AI Agent 設計參考 | ✅ | 新建 `docs/04_planning/ADR/ADR-XPLAT-007-frontier-token-governance.md`；`前沿` 22 命中。 |
| **7** | R79 哨兵**仍有彈視窗** ⇒ 修到無彈窗 | ❌ | **未修**。SDD LATEST 3 支 `git` spawn 零 `CREATE_NO_WINDOW`，且**不在任何 console-spawn 掃描面**（SA-07）。QA「不得計入」裁決**成立**。 |
| **8** | **Container 環境整理** | ❌ **靜默漏掉** | 7 份 R85 文件＋全部新程式碼，`Container/docker/compose` **命中 0**（對照組有效）。**從頭到尾沒有人碰**。 |
| **AC-(a)** | 舵手被喚醒回來 | ✅（依 R83 裁決） | `AutoClaude/tests/execution/test_unattended_capability_gate_r85.py` 落地；裁決是「不再嘗試自動變回真舵手，改把 headless 能力面寫清楚」，本輪把 R84 的散文變成機械面。🔴 我一度判它「被漏掉」，**實測推翻了我自己**。 |
| **AC-(b)** | `example_playbook.yaml` `global_goal`＋`tasks` 開發應用（含 PG） | 🟡 | `test_r85_subtraction_locks.py` 有 AC-(b) 啟動阻塞鎖（`example_playbook`/`global_goal` 各 11/10 命中）；PG 容器 up **且已 migrate**（`pg_autodetect()` 回 True＋DSN）。但**未見端到端真跑一次應用開發**的取證。 |
| **AC-(c)** | 彈窗 | ❌ | 同訴求 7。 |
| **SDD** | 重新檢視**所有** Agents（尤 Architect/SA/SD/QA） | ✅ | 19 支 agent yaml 實改 `+387/−462`（net −75），含 04.sa／05.sd／07.qa／sd-web／sd-mobile／qa-lead 等。🔴 **但計畫書 §3 說它「未派、順延」**（SA-12）。 |
| **S1** | 徹底解決 skipped、**全部可測** | ❌ | 根 44 全 platform（#1）；AC 側 73 skip 中**欠債型 19 支**（#10，目標 0）。且根 44 的「它們在 Windows 會跑」今天**無證據**（#16 CI 全紅）。 |
| **S2** | 帳本逼近警告線 ⇒ **全力消除技術債** | ❌ | 未結 88→**89**（#4），warn 86 已越過，距 fail 98 僅 9。計畫書 §5 要求 **≤80**。 |
| **注②** | 當前平台**確實執行驗證測試** | 🟡 | mac 側確實跑了（#1/#2/#9 皆真跑）。但**根層閘門是紅的**（rc=1）而本輪仍在收斂中。 |
| **注③** | 歷史文件太多請 **Archive** | ❌ | `AutoSDD_R85_Archive_Proposal.md` 自陳「**一個檔都沒有被搬動**」。理由（並行輪不得做淨減法／跨檔參照稅）**結構上站得住**，但訴求本身未達成。 |
| **注⑤** | 每輪給 **M1~M6 評估** | 🟡 | 7 份 R85 文件內 `成熟度` **命中 0** ⇒ 各包無自評；由四方複審補（本檔 §4）。 |
| **注⑥** | CI 額度用盡 ⇒ **先用 act 與 Docker 本機驗證** | 🟡 | Docker/PG 本機驗證確實在用（#9 PG 已 migrate）。但 `act` 本輪無取證；且 #16 證實雲端已全紅 ⇒ 本機驗證是**唯一**剖面，這件事本身未被當成風險登記。 |

**達成統計**：✅ 7｜🟡 9｜❌ 8｜⛔ 1。

---

## §2 被靜默漏掉的訴求

**只有 1 條是「從頭到尾沒有人碰」**：

### 🔴 SA-04（blocking）訴求 8「Container 環境整理」零覆蓋
- **現查**：`cat <7 份 R85 文件> > /tmp/sa_all85.txt`（2798 行）後
  `grep -ic Container|docker|compose` → **0／0／0**；新程式碼（3 支 AC 測試＋2 支 tools）亦 **0**。
- **對照組（證明管道有效）**：同一份語料 `Archive=47`、`前沿=22`、`pmset=13`。
- **為何是問題**：它不在計畫書 §3 的 P1~P4 射程內，**也不在 §3 那句「未派、順延」的名單裡**
  （該句只點名 SDD Agents）⇒ 它不是被延期，是**沒有人記得它存在**。這正是本節要找的形態。
- **修法草案**：R86 計畫書 §3 必須附一張「訴求全表 × 本輪持有面」對照，缺項顯式標 `未派`。
- **持有面**：計畫書（收尾窗口）。**嚴重度：blocking**（訴求級遺漏）。

**其餘看似漏掉、實測推翻的**（我自己的誤判，如實登記）：AC-(a)／AC-(b) 在文件面 0 命中，
但**程式碼面有機械物** ⇒ 不算漏。⇒ **只看文件會誤判**，這一點對下一輪的複審者同樣成立。

**被「已交棒」代替結算的**：訴求③ Archive（提案代替搬檔）、訴求 7（定位代替修復）——
兩者都**誠實劃界了**，不是隱瞞，但訴求狀態仍是未達成。

---

## §3 宣稱 vs 現況的落差（M4 判準）

### 🔴 SA-01（blocking）§5 驗收條件「全樹閘門 rc=0」未達成
```
.venv/bin/python tools/run_root_unittests.py                    → rc=1
cd tools/tests && ../../.venv/bin/python -m unittest discover   → rc=1  Ran 3284, failures=8
.venv/bin/python tools/check_defect_log_crossref.py             → rc=1（且早退 12 道未執行）
```
8 支紅逐字：`test_appending_one_row_keeps_the_history_digest_stable`／`test_editing_an_existing_row_in_place_is_red`／
`test_the_docs_cite_the_live_guard_total`／`test_the_extended_doc_surface_covers_the_handoff_without_false_reds`／
`test_the_real_repin_log_stays_inside_the_cost_envelope`／`test_the_repin_log_accounts_for_the_frozen_table`／
`test_new_rows_are_bounded_and_point_at_the_findings_doc`／`test_e501_debt_only_shrinks`。
**持有面**：`tools/tests/test_adr_xplat001_c1c2_lock.py` ＋ 三份文件（收尾窗口）。**blocking**。

### 🔴 SA-02（blocking）本輪的**定位本身**是假的：宣稱 +0，磁碟 +481
- 計畫書 `AutoSDD_improving_109.md:99` 逐字：
  `<!-- guard-total:R85 --> **本輪護欄層累積淨額＝ 82838 → 82838（+0）** —— …**第一個非上升輪**`
  並標 `[P2 當回合實測]`。
- 磁碟現況：`repin_round_nets(...)` → `(85, **481**)`；`_FROZEN_GUARD_LINES` 總量 **83319**。
- 機械物**已經在說話**：`doc_guard_total_problems(docs, 83319, 'R85')` 回 **3 筆紅**，逐字：
  - `[總量不符] docs/04_planning/AutoSDD_improving_109.md:99 引用的護欄層總量 82838 不等於…83319`
  - `[總量不符] docs/06_quality/CrossPlatform_R85_Scan_Findings.md:497 …`
  - `[形態不符] docs/06_quality/AutoSDD_R85_Archive_Proposal.md:161 帶著 guard-total:R85 標記，卻讀不出三元組`
- **公允之處**：收尾窗口**已經追加**第二列重釘並標 `[非淨減法輪]`，逐字承認
  「本輪方向仍與 M1 相反（護欄層總量上升）」⇒ **帳面上是誠實的**，
  病在**三份文件沒跟上**，而 §5 驗收條件（淨額 ≤0）也因此未達成。
- **修法草案**：三處文件改寫為 `82838 → 83319（+481）`，並把計畫書 §1／§5 的「減法輪」定位
  依 Architect ARCH-04 建議改寫為「減法佔比進入 ~28% 帶、淨額仍為正、M1 債務滾入 R86」。
- **持有面**：三份 `.md`（收尾窗口單人）。**blocking**。

### 🔴 SA-03（blocking）帳本閘門紅＋**早退 12 道檢查未執行**
```
❌ 具名治理文件涵蓋面與磁碟脫節（**3 筆**）：
  - CrossPlatform_R85_Review_Architect.md：符合 CrossPlatform_*.md 命名慣例卻未登記進 _GOVERNANCE_DOCS
  - CrossPlatform_R85_Review_QA.md：同上
  - CrossPlatform_R85_Review_SA.md：同上（**本檔**）
🔴 早退：本次尚有 12 道檢查**未執行**（…帳本體積與逐列位元組上限）
```
**為何是問題**：這與我的簡報警告的 `run_root_unittests` 短路**同型**——
rc=1 之外，「其餘 12 道乾淨」是**未知**不是「通過」。
🔴 **我對這一筆做了預測並當場驗證**：落檔前該閘門是 1 筆，落檔後實跑回 **3 筆**
（Architect／QA／SA；QA 檔在我複審期間出現）⇒ 四方複審**每多一份就多一筆紅**，
這是流程層的結構缺陷，不是誰忘了登記。
**修法**：收尾窗口在 `tools/lib/governance_docs.py` 一次登記四份複審檔；
或（更治本）把 `_GOVERNANCE_DOC_GLOB` 的發現面與登記面接成「發現即要求登記」的單一來源。
**持有面**：`tools/lib/governance_docs.py`（**不在我的持有面**）。**blocking**。

### 🔴 SA-06（blocking）M5 接線率**被本輪做差**
AST 實測 12 定義／8 接線，未接線 4 支：
`scan_foreign_exe_argv`（**本輪新建**）／`scan_git_path_enumeration`／`scan_naive_timestamp_persist`／`scan_ps_platform_sites`。
⇒ P4 把「判準集漏三分之一」列為 blocking，本輪**新增第 12 支卻沒接線**，8/11 → **8/12**。
**這與 Architect ARCH-02 獨立同結論**（我先量後讀，非採信）。
**修法**：`_injection_criteria()` 補接線；接線率本身應上棘輪（只准升）。
**持有面**：`test_platform_neutral_paths.py`（消費端＋史料）＋ `_FROZEN_GUARD_LINES`（另一支檔）⇒ **鐵律七：收尾窗口**。**blocking**。

### 🔴 SA-05（blocking）S2 帳本反向：88 → **89**
`--unresolved-count` → `未結列數＝89／全部 181 列｜warn=86 fail=98`。§5 要求 **≤80**。
**公允之處**：本輪帳本 bytes **確實洩壓成功**：244,877 → **211,736**（−33,141），
餘裕 33.2 KB **超過** §5 要求的 13 KB ⇒ 死結治本這一半 ✅。
且 P9 的兩筆**駁回**（`DEF-101-755`／`DEF-101-377`）我複驗**皆成立**——
前者條件 (b) 需 Windows CI 而 CI 全紅（#16 佐證）、後者是拿 A 機乾淨證 B 機乾淨。
**P9「三方 84 列次只找到 3 列真的已修」的查證結果**：措辭應更精確——
P9 逐列查了 **15 列**、P1 查了 **8 列**（共 23 列），結論是**沒有一列真的已修**；
本輪實際結案 **3 列**（`DEF-200-081`／`DEF-101-991`／`DEF-200-020`）。
⇒ **「未結存量高不是因為沒人去結，是它們真的還沒修」這個判讀我認同**，
但那不改變「訴求 S2 未達成」與「越過 warn 線」兩個事實。**blocking**。

### SA-07（major）訴求 7／AC-(c)：彈窗**未修**，且「不閃窗」正是 fail-open 表徵
```
grep -nE 'subprocess\.(run|Popen|call|check_output)' AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/*.py
  → closure_evidence_verify.py:68 / post_commit_drift.py:54,72   （3 筆，argv[0] 皆 git）
grep -rn 'CREATE_NO_WINDOW|creationflags|startupinfo' <同目錄>  → rc=1（零命中）
對照組：.claude/hooks/sdd_hook_router.py:237 → creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)  ✅命中
```
掃描面實查：`ConsoleFreeSpawnTest._sources()` ＝ `tools/session_resume_planner.py`＋`tools/lib/schedule_backend.py`
＋`tools/lib/{quota_*,sentinel_*}.py`＋`.claude/hooks/*.py`；R84 另加 `AutoClaude/tools/hooks/**`。
⇒ **`AISDLC_SDD/**/.claude/hooks/` 不在任何掃描面**。
**QA 裁決「AC-(c) 部分交付、訴求 7 本體不得計入」——我判定成立。**
🔴 **對簡報那一問的正面回答**：根 `CLAUDE.md` 鐵律一之二逐字記載
「exec form 載具解析不到時 CC 只記一行 ERROR 就放行（fail-open），六支守衛全部靜默失效，
而螢幕上的表徵就是『終於不閃窗了』」⇒ **在本輪（mac、無 console 概念）條件下，
「不閃窗」不可能被觀測，也不能當證據**。今天唯一能說的是：**這 3 支 spawn 在 Windows 上會配新 console（靜態推論、未真機驗證）**。
**修法**：3 個站點補 `creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)`；掃描面擴到 SDD LATEST hooks。
**持有面**：SDD LATEST hooks ＋ `test_context_budget_guard.py`（跨兩持有面 ⇒ 收尾窗口）。**major**。

### SA-08（major）S1「徹底解決 skipped」的**理由本身今天不成立**
根 44 支全 `platform=[WINDOWS-NATIVE-ONLY]`，計畫書 §2 據此判「在 macOS 結構性不可消除，**它們在 Windows 上會跑**」。
**但 `gh run list` 實測**：R84 push 的 6 支 workflow **全部 failure，各 3 秒**（`windows-compat-ci` 在內）。
⇒ 「它們在 Windows 會跑」今天**沒有任何當輪 rc 佐證**，而 M6 門檻**逐字要求**「當輪實跑 rc 佐證」。
⇒ 這 44 支目前落在 M6 第①條「從未被任何軌執行過」的**嫌疑區**，不能記為已覆蓋。
AC 側另有**欠債型 19 支**（tool-absence 3／env-disabled 13／debt 3），該群自陳「**可歸零的那一半**」。
**修法**：CI 帳務恢復前，以 act／本機 Windows 剖面補一次取證；欠債型 19 支逐群設環境變數／裝工具。
**持有面**：CI 帳務（**外部**）＋ `AutoClaude/tests`。**major**。

### SA-09（major）E501 棘輪**上升**，且複審期間仍在漲
```
139（凍結） → 140（09:4x 首測） → **141**（10:0x 複測）
AssertionError: 141 not less than or equal to 139
```
違反 §6 禁止事項 3「只准下修」的精神（雖非調高常數，而是債本身變多）。**major**。

### SA-10（major）注意事項③ Archive：**零搬檔**
`AutoSDD_R85_Archive_Proposal.md` 逐字「**射程宣告 —— 本輪只做盤點與提案，一個檔都沒有被搬動、刪除或改寫**」。
`docs/06_quality/Archive/` 現有 99 檔、`AutoSDD_Defect_Log_archive_*.md` 66 份仍全在 `docs/06_quality/` 根層。
**理由結構上成立**（並行輪禁淨減法、跨檔參照稅），但**這已是可預期的第二輪順延** ⇒
R86 必須把它排進**收尾單人窗口**，否則它會永遠沒有合法時機。**major**。

### SA-11（minor）誠實訂正列自己的算術不對帳
R85 第二列重釘理由逐字寫「本輪真值＝0 + **468** = 468」，逐檔歸因 `221+148+93+6 = 468`；
但該列 net 欄與實際皆為 **481** ⇒ **13 行未歸因**（正是閘門訊息裡「83306 ≠ 83319」那 13）。
**minor**（方向誠實，數字差 13）。

### SA-12（minor）計畫書 §3 說 SDD Agents「未派、順延」，實際已改 19 支
`git diff --stat -- AISDLC_SDD/**/agent/` → **19 files changed, +387 −462**。
計畫書 §3 逐字：「🔴 **未派、順延的**：AISDLC_SDD Agents 精進…列入第二波或 R86」。
⇒ 第二波確實做了，但**計畫書沒回填** ⇒ 讀計畫書的人會低估本輪射程（與 SA-02 同病）。**minor**。

### SA-13（minor）6f「調成最佳值」未做
`diff .env.example .env` → **rc=0（逐位元組相同）**。⇒ 只完成「copy 到根目錄」，未完成「依實務調整」。**minor**。

### 🔴 SA-14（major）本輪的四方複審對象是**移動標的**
同一份工作樹，我三次量測得到三種結果：
| 時刻 | `check_defect_log_crossref` | E501 | 護欄 ratchet 紅數 |
|---|---|---|---|
| ~09:5x | rc=**0** | 140 | 6 |
| ~10:0x | — | **141** | 8（另兩支自癒） |
| 10:15 | rc=**1** | 141 | 8 |
**為何是問題**：M2／M3／M4 全部要求「該輪」的分子分母，而分母在複審期間仍在變
⇒ 四方複審的結論**無法對應到任何一個確定狀態**，這正是 M2 判準②「分母不穩不得讀成任一極端」的形態。
**修法**：複審開始前由收尾窗口宣告**凍結點**（`git diff` sha 或 commit），四方一律對該點複審。
**持有面**：流程（收尾窗口）。**major**。

---

## §4 成熟度 M1~M6（訴求⑤；SSOT＝`CrossPlatform_Maturity_Criteria.md` 逐條門檻欄）

| # | 門檻（SSOT 逐字要點） | R85 判定 | 理由（我的量測） |
|---|---|---|---|
| **M1** | **合取**：①UEP 半（§8.1 出現回執 **或** ADR 宣告終態並凍 `_EXEMPT_PAIRS`）**且** ②護欄總量**連續三輪不上升** | ❌ | **兩半皆不成立**。①`ADR-XPLAT-002-platform-surface-reduction.md:1268~1270` **逐行實查**：回執表只有一列佔位符 `\| （尚無回執。R67 建立本容器時 item 7／8 皆自 R60 起零回執，共六輪） \| — \| — \| — \| — \|` ⇒ **回執列數＝0**（非引用該檔散文自陳，是直接讀表）。②`repin_round_nets` 末六輪 `2334,3033,5400,5260,3755,**481**` ⇒ R85 **仍上升**，連續不上升輪數＝**0**。 |
| **M2** | 分子（失實宣稱）**連續三輪 ≤1 且無 P1** | ❌ | 分母＝發現情境含 R85 的帳本列 **14**。分子：Architect **5 blocking／駁回 4 筆**、本檔 blocking **6 筆**，且含 P1 級（SA-02 本輪定位造假）。⇒ 遠超 ≤1。**非 N/A**（本輪四方複審有跑、分母非 0）。 |
| **M3** | 第三方注入**連續兩輪 100%**，**且抽樣面含既有鎖庫隨機 20 支** | ❌ | 我這輪做了 2 支新鎖的第三方注入，**皆 100%**（#23 13/13、#24 16/16）——這是正面事實。但①**既有鎖庫 20 支抽樣至今一次都沒做過**（SSOT 逐字「目前最大量測缺口」）；②本輪存在**接了鎖卻沒接線**的反例（SA-06）＝新增判準對矩陣零效果。 |
| **M4** | 宣稱射程≡實作射程 **一輪內 0 筆** | ❌ | 至少 **6 筆**：SA-02（3 份文件 guard-total 過期，機械物已紅）、SA-11（重釘列算術差 13）、SA-12（計畫書 §3 射程過期）、SA-08（S1 理由的 Windows 前提今天不成立）。 |
| **M5** | 兩向**未攔到題數各 ≤1**，連續三輪不回升 | ❌ | `Win2mac=6/12 mac2Win=5/10` ⇒ 未攔到 **6／5**，門檻 ≤1。**與 R84 逐字相同＝本輪零改善**；且接線率 8/11→**8/12** 退步（SA-06）。 |
| **M6** | ①「從未被任何軌執行過」為 **0**，**且**②有**當輪實跑 rc** 佐證 | ❌ | ②**結構性失守**：`gh run list` 6/6 failure（3s）⇒ 根層 44 支 `[WINDOWS-NATIVE-ONLY]` 本輪**無任何軌的 rc 佐證**。①AC 側另有欠債型 **19 支**（目標 0）。 |

### 🔴 R85 成熟度總判：**0 / 6**（與 R80~R84 相同）

**唯一的方向性進展**（不計分，如實登記）：`_REPIN_NET_CAP_SCHEDULE` 分段上限表把
「款(10) 要求 ≥3755／款(12) 要求 ≤3200」的**互斥死結**解開，且形狀鎖（append-only／輪號遞增／
上限只准遞減）我逐條讀過，**設計是好的**——`_REPIN_ROUND_NET_CAP` 由 5400 降至 **3200**，
並重新武裝到 `DUE_ROUND=87／DUE_TARGET=2600`。**§5 那一條驗收條件是本輪唯一乾淨達成的。**

---

## §5 我駁回的本輪宣稱（附實測）

| # | 被駁回的宣稱 | 出處 | 我的實測 |
|---|---|---|---|
| 1 | 「本輪護欄層淨額 **+0**，連八輪上升後**第一個非上升輪**」 | `AutoSDD_improving_109.md:99`（標 P2 當回合實測） | `repin_round_nets` → `(85, **481**)`；`doc_guard_total_problems` **3 筆紅** |
| 2 | 「R85 是**減法輪**」 | 計畫書 §1 標題 | 全樹 `git diff --numstat` → **net +998** |
| 3 | 「§5 全樹閘門 rc=0」 | 計畫書 §5 | `run_root_unittests` rc=1／`discover` 8 failures／`crossref` rc=1 |
| 4 | 「帳本未結 ≤80」 | 計畫書 §5 | **89**（且越過 warn 86） |
| 5 | 「AISDLC_SDD Agents 未派、順延」 | 計畫書 §3 | 19 支 agent yaml 實改 `+387/−462` |
| 6 | 「根層 44 支 skip 在 Windows 上會跑」（S1 的免責理由） | 計畫書 §2 第 1 列 | `gh run list` **6/6 failure，各 3s** ⇒ 今天無任何佐證 |
| 7 | 訴求 7 已處置 | （若有人如此讀 QA「部分交付」） | SDD LATEST 3 支 spawn 零 `CREATE_NO_WINDOW`＋掃描面不含該目錄 |

**我未駁回、複驗成立的**：P9 對 `DEF-101-755`／`DEF-101-377` 的兩筆駁回（理由與證據皆成立）；
Architect ARCH-01／ARCH-02（我先獨立量測，結論一致）；Archive 提案的「並行輪不得淨減法」理由；
`DEF-200-020` 取 `closed-by-decision` 而非 `fixed`（**寫 fixed 會謊稱 6e 已達成**，這個分寸我認同）。

---

## §6 blocking 清單（附持有面）

| # | 標題 | 持有面 | 能否併行修 |
|---|---|---|---|
| **SA-01** | 根層閘門 rc=1（8 支紅） | `tools/tests/test_adr_xplat001_c1c2_lock.py`＋3 份 `.md` | ❌ 收尾單人窗口 |
| **SA-02** | 本輪定位造假：宣稱 +0／實為 +481，3 份文件過期 | `AutoSDD_improving_109.md`／`CrossPlatform_R85_Scan_Findings.md`／`AutoSDD_R85_Archive_Proposal.md` | ❌ 收尾單人窗口（與 SA-01 同一次） |
| **SA-03** | 帳本閘門 rc=1 ＋ **12 道檢查未執行**；Architect／SA 複審檔未登記 | `tools/lib/governance_docs.py` | ❌ 收尾（**我沒有這個持有面**） |
| **SA-04** | **訴求 8 Container 零覆蓋**（唯一從頭到尾沒人碰的訴求） | R86 計畫書 | ❌ 收尾／R86 派工 |
| **SA-05** | 帳本未結 88→**89**，越過 warn 86，§5 要求 ≤80 | `AutoSDD_Defect_Log.md`＋`defect_ledger_index.py`＋`ledger_rotation`（**三持有面**） | ❌ 鐵律七：收尾單人窗口 |
| **SA-06** | M5 接線率被做差 8/11→**8/12**（本輪新 scanner 未接線） | `test_platform_neutral_paths.py`＋`_FROZEN_GUARD_LINES`（另一檔） | ❌ 鐵律七：收尾，且須與 SA-01 同一次 |

**major**：SA-07（彈窗未修）／SA-08（S1 理由不成立）／SA-09（E501 141>139）／SA-10（Archive 零搬檔）／SA-14（複審對象是移動標的）。
**minor**：SA-11（算術差 13）／SA-12（計畫書射程過期）／SA-13（`.env` 未調值）。

---

## §7 誠實劃界（本檔量得到什麼、量不到什麼）

1. **Windows 側全部是靜態推論**。本輪 macOS 單平台，SA-07／SA-08 涉 Windows 執行期者未真機驗證。
2. **CI 剖面本輪完全不可用**（6/6 failure／3s，帳務指紋）⇒ 任何「雲端會跑」的宣稱本輪都不可查證。
3. **我的量測本身是移動標的上的取樣**（SA-14）。§0 已標快照時刻與 `git diff` sha；
   **我不宣稱其後未再變動**。
4. **M3 我只注入了 2 支新鎖**，非本輪全部新鎖；既有鎖庫 20 支抽樣**我也沒做**（該缺口自 SSOT 建立以來未動）。
5. **AC-(b) 我只驗到「機械面存在＋PG 已 migrate」**，未端到端跑一次 playbook 應用開發。
6. **我一度誤判 AC-(a)/(b) 被漏掉**（只掃文件面），實測程式碼面後推翻自己——
   **如實留痕**：這說明「掃文件面判有無交付」是一個會產生假陽性的方法。
7. **本檔未登記進治理面** ⇒ 落地後 `check_defect_log_crossref.py` 會多一筆紅（見 SA-03）。
