# R99 帳本減半 — 書記收斂證據檔

> 本檔是 R99「帳本減半」波單一書記對四個修復包（P1 機械物／P2 文件-ADR／P3 雜項小鎖／
> P4 Windows-hooks）回報的逐筆 zero-trust 複驗紀錄，以及 B 類（宣稱已修）／E 類（外部
> 阻塞）兩批的裁決依據。主帳本 `AutoSDD_Defect_Log.md` 對應列僅留一句結論＋本檔章節指
> 標；完整查證過程與命令輸出留在本檔，供之後任何人回溯核對。
>
> 複驗方法：每筆皆重新對磁碟現況跑一次可重現指令（grep／pytest／檔案存在性），不採信
> 任何包「已修」的自陳，除非命令輸出可親自核對。

---

## 甲、四包回報逐筆複驗

### P1（機械物）
本包三個機械物（淨額棘輪 `net_new_vs_closed_problems()`、外部阻塞軌
`external_blocked_log_problems()`、oversize repin 自動化 `tools/lib/oversize_repin.py`）
屬本輪自建工具，非既有帳本缺陷之修復，**不落地為帳本列**（追認式登記無意義：它們本身
就是本輪收斂動作所依賴的工具）。複驗：三者皆已在下方「丁、驗收」一節被實際使用且行
為與回報一致。

殘留兩項：
- **`tools/lib/ledger_rotation.py` 的 `*_HISTORY`／封印表同步**：由本書記在同一次變更內
  完成（見〈丁、驗收〉），不落帳本列（工具維護，非缺陷）。
- **`tools/sync_onboarding_baselines.py` raw-line 餘裕＝0**：複驗屬實（`python
  AutoClaude/tools/check_loc_budget.py` 現查 `[special<=1499] .../sync_onboarding_baselines.py:
  1499 （餘裕 0 行）`），非阻塞（rc 不受影響，只是 SPECIAL-WARN），但是真實新發現 ⇒
  落地為 `DEF-200-187`（見丙）。

### P2（文件／ADR）
| DEF-ID | 複驗方法 | 複驗結果 |
|---|---|---|
| DEF-101-402 | `find . -iname test_ci_paths_cover_root_consumers.py` | 只命中 `AISDLC_SDD/scripts/tests/`；`tools/tests/` 下無此檔。P2 對 A1 給錯路徑的糾正屬實。維持 routed，指向正確子專案路徑 |
| DEF-101-748 | `ls docs/04_planning/ADR/ADR-XPLAT-010-*.md` | 檔案存在（7803 bytes），內容含 §2.1／§2.2 兩項決策裁決，非空殼。測試 docstring／`ruff.toml` 回指未做（跨包邊界），故維持未完全解鎖，首詞升級為 `partial`（比 `open` 更準確：文件面已落地） |
| DEF-101-978 | `grep -n "開輪機械第一動作" docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` | 命中（:151-156 起），內容與缺陷描述吻合：SOP 已將「先寫帳本第一列」列為開輪機械第一動作 | fixed |
| DEF-101-998 | `grep -n DB_Only_Switch_Runbook AutoClaude/docs/04_planning/AutoClaude_Guide.md AutoClaude/docs/AutoClaude_Guide.md` | 兩份 Guide 皆已改為指向 Runbook 的指針（分別於 :591、:170/:492/:568），README.md 原已合規。PG 設定段落四個家已收斂為一個 SSOT＋三指針 | fixed（僅此子問題；兩份 Guide 整檔版本漂移未列入本輪範圍，另計 backlog，不開新列——非阻塞性文件維護債） |
| DEF-200-090 | `grep -n "四方複審產出一律先落檔" docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` | 命中（:278），內容與缺陷描述吻合 | fixed |
| DEF-101-235 | 見 `docs/04_planning/ADR/ADR-XPLAT-011-*.md` §1；逐項覆驗：`grep -n "restype\|argtypes" tools/dev_start.py`零命中（①仍真實殘留）；`grep -n Copy-ItemWithRetry AutoClaude/tools/run_local_nightly.ps1`命中（③已修）；`sed -n '1,15p' AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/run_tlc.ps1`確認 R65 薄殼化、無版本守衛（④原始形狀消失） | ADR 對四個子項都給出明確裁決（①維持已知邊界不修＋可執行退場條件；②③訂正為已修復；④訂正為架構前提改變）。這是「已充分審查並做出決定」而非「還沒處理」⇒ 裁決 `closed-by-decision` |
| DEF-101-324 | ADR §2；`grep -n "def sanitize_component" -A 50 AISDLC_SDD/scripts/component_sanitizer.py` | 碰撞行為與帳本原記載一致（無 hash/uniqueness），ADR 給出比例原則裁決（advisory 內部檔名、非可利用攻擊面），為既有 backlog 提供正式決策文件 | `closed-by-decision` |
| DEF-101-399 | ADR §3；`grep -rn workflow_call .github/workflows/` 零命中；`wc -l` 兩份 workflow 已達 1782/1296 行 | 現況與原記載方向一致（規模持續增長、無 parity 鎖），ADR 記錄了架構提案與退場條件 | `closed-by-decision`（watch item 正式落點，非阻擋） |
| DEF-101-559 | ADR §4；`cat` `hub-push.yml` 檔頭 | 政策問題本身仍未被任何人裁決，ADR 只是把解鎖條件列清楚，**不代為裁決**——這正是本列一直以來的狀態，未變 | 維持 `routed`（未指派，政策擁有者決策） |

### P3（雜項小鎖）
逐筆重跑對應測試，全數綠燈，判定 `fixed`（除 DEF-200-165 外）：

```
$ cd AISDLC_SDD/AISDLC_SDD_v0.30 && python3 -m pytest tools/fsm_runtime/tests/test_hub_sync.py -q
55 passed in 0.63s                                                   # DEF-101-596

$ cd AutoClaude && python3 -m pytest tests/tools/test_perf_baseline_lock.py tests/infra/test_sdd_to_playbook_adapter.py -q
103 passed in 2.55s                                                  # DEF-200-164, DEF-200-176
```
DEF-101-889（`sync_onboarding_baselines.py::_run_cigate()` env 推導修復）：程式碼現查
`import os` 於檔頭、`_run_cigate()` 內以 `sys.executable` 推導 `PATH` 插入 `env=` 傳給
`subprocess.run`——與回報描述一致，判定 `fixed`。

DEF-200-165：本機（mac）`python3 -c "…逐位元組掃 165 支 .toml/.json…"` 與
`git ls-files --eol` 雙證交叉核實 0/165 CRLF 漂移，與 R96 原始「142/165」不符。書記複驗
同意 P3 的判斷——**這是「量到 0」不是「證明沒問題」**，R96 的量測極可能發生在另一台
Windows 機器的工作樹陳舊副本上，本 session 無法代為證偽或復現。維持 `open`，待 Windows
真機復驗。

### P4（Windows／hooks）
```
$ python3 -m pytest tools/tests/test_dev_start.py -q
250 passed, 12 skipped, 23 subtests passed                            # DEF-101-758
$ python3 -m pytest tools/tests/test_ps_engine_ssot.py -q
28 passed, 10 subtests passed                                         # DEF-101-797
$ (cd AISDLC_SDD && python3 -m pytest scripts/tests/test_install_post_commit_windowsapps_guard.py -q)
8 passed, 2 skipped                                                    # DEF-101-797（另一半座標）
$ bash -n tools/git-hooks/pre-push && bash -n tools/git-hooks/post-commit
SYNTAX_OK
$ grep -n "BOM\|DEF-101-918" tools/git-hooks/post-commit         → 命中，反向判準已落地（DEF-101-918）
$ grep -n "DEF-101-733\|gh run list" tools/git-hooks/pre-push    → 命中，push 前唯讀廣播已落地
$ grep -n "DEF-200-117\|不是全過" tools/git-hooks/pre-push       → 命中，rc≠0 失敗摘要已落地
$ python3 AutoClaude/tools/check_loc_budget.py --json            → violations=0（DEF-101-758 未撞棘輪）
```
DEF-101-769：本機（mac）`shutil.which("pwsh")` 命中 7.6.3，但**沒有原生 `powershell.exe`
5.1**——這不是「機器前提已具備」（A1／P4 皆指 R73/75 記載的是另一台 Windows 機器），而
是「本 session 環境結構上做不到」，`test_ps51_compat.py -rs` 3 支 `[WINDOWS-NATIVE-ONLY]`
skip 為證。維持 `open`，殘留兩項仍須真 Windows。

DEF-101-926：`grep -n "check_sh_eol\|check_ps1_encoding" .claude/settings.json
AutoClaude/.claude/settings.json` 命中 9 處，橫跨兩份 settings.json，搬遷需同時動兩份
註冊面＋根 CLAUDE.md 守衛表＋AutoClaude 側測試路徑，四個持有面沒有一個在單一修復包射
程內。維持 `routed`。

---

## 乙、B 類複驗（A1「已實質修好只是沒改狀態」宣稱之逐筆證偽）

🔴 **結論：5 筆全數證偽——A1 的 B 類判定不成立，全部維持原本的未結狀態**，理由如下（皆
為本書記親自重跑，非轉述）：

| DEF-ID | 複驗指令 | 結果 |
|---|---|---|
| DEF-101-803 | `grep -n "結構性修法.*已登記 DEF-101-803" tools/tests/test_run_root_unittests.py` | 命中 `:1553`，程式碼**自己**仍逐字宣告本缺陷未結案。遞迴主因已斷（`_ZERO_DEP_PROBE_ENV`），但外層探針仍跑一次整棵樹的殘留原封不動。**不成立**，維持 `partial` |
| DEF-101-876 | 查其自身狀態欄引用的 `DEF-101-060`（依賴債） | DEF-101-060 現況仍為 `open`（「13 條無上限相依要先建白名單機械物」未做）。DEF-101-876 自己的邏輯是「依賴債未清前不得結案」，前提未變 ⇒ **不成立**，維持 `open` |
| DEF-200-128 | `grep -rn "待驗清單.*可重跑腳本" docs/06_quality/CrossPlatform_R91_Scan_Findings.md` | R91 已明載「尚無通用可重跑腳本落地」；`find . -iname "*rerunnable*"` 全 repo零命中，本輪複查同樣零命中 ⇒ 結構性修法（可重跑載體）從未建置。**不成立**，維持 `open` |
| DEF-200-141 | `grep -n "^| \*\*v2.1.4" docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` | PRD 版本表原文逐字仍是「經掌舵者 2026-08-16 拍板、**待四方複審後生效**」，未見任何後續版本項訂正此狀態（對照 v2.1.6→v2.1.7 那樣的「已完整實作並回歸鎖驗證通過」寫法，v2.1.4 沒有對應的後繼確認列）。**不成立**，維持 `open` |
| DEF-200-142 | `grep -n "仍標注.*待四方複審" docs/06_quality/CrossPlatform_R95_Pace_Actuator_Evidence.md` | 命中 :67，證據檔自己承認「掌舵者裁決的授權放寬）仍標注待四方複審」，且未見任何後續複審完成紀錄。**不成立**，維持 `open` |

---

## 丙、E 類（外部阻塞）處置與拆列

8 筆全數確認為「機械上此刻真的做不了任何事」，移入
`docs/06_quality/AutoSDD_External_Blocked_Log.md`；主帳本原列收斂為 `closed-by-decision`
索引（不得同時以未結狀態留在主帳本，見交叉鎖）。

**DEF-101-755／DEF-101-866 依規定拆列**（不可整筆移出）：

- **DEF-101-755**：條件 (a)（shim 依 `os.name` 分派 `.cmd` 形態＋移除 `skipIf`）已於 R71
  落地，本輪複驗 `python3 -m pytest tools/tests/test_dev_start.py -k
  "TestGetPythonGeMinPowerShell" -q` 環境限制下無法在 mac 上重跑 Windows-only 分支，但
  R71/P4 兩輪均有 Windows 真機 4/4 zero-skip 紀錄可查（`test_dev_start.py:5304` 起）
  ⇒ 條件 (a) 判定 `fixed`；主帳本 DEF-101-755 收斂為 `fixed@R99`。條件 (b)（Windows CI
  真跑一次＋skip 明細取證）結構上需要 GitHub Actions 通道 ⇒ 拆出 **DEF-200-185**
  進外部阻塞軌，具名阻塞源＝`GitHub Actions 帳務`。
- **DEF-101-866**：條件 (a)（本機可驗的 PS 5.1 parse-error 紅綠對照）R77 已跑通，本輪
  複驗 `grep -n "乾淨組 0／毒化組各 2 errors" docs/06_quality/AutoSDD_Defect_Log.md` 原文
  仍在（歷史保全）；主帳本 DEF-101-866 收斂為 `fixed@R99`（僅指 (a) 那一半）。條件 (b)
  （nightly-full 端到端雲端成功）拆出 **DEF-200-186** 進外部阻塞軌，具名阻塞源＝
  `GitHub Actions 帳務`。

外部阻塞軌完整 8 列見 `AutoSDD_External_Blocked_Log.md`。

---

## 丁、驗收（原始輸出見對話回覆本文）

三處機械維護（非帳本內容，而是帳本編輯的必然機械後果，已於本輪一併完成）：
1. `tools/lib/defect_ledger_index.py`：`OVERSIZE_ROW_GRANDFATHERED`／`OVERSIZE_ROW_CEILING`／
   `OVERSIZE_ROW_EXCESS_CEILING` 依本輪編辑后的實際列位元組數重新量測並下修（僅減不增，
   遵循既有 shrink-only 慣例）；`_UNPINNED_HANDOVER_GRANDFATHERED`（`DEF-101-235`／
   `DEF-101-324`，本輪雙雙結案）清空，`_UNPINNED_HANDOVER_CEILING` 2→0。
2. `tools/lib/ledger_rotation.py`：對應 `*_HISTORY` 追加新值（末元素＝現值），封印表視
   `_SEAL_TAIL_MAX` 需要同步。
3. 本次僅為配合帳本瘦身的機械同步，不含任何新裁決；理由與精確數字見對話回覆〈丁、驗收〉
   與相關檔案內的 commit-time 註解。

## 戊、同輪追加（收尾單人窗口的護欄層重釘）

四包停工後，收尾單人窗口重跑根層 unittest 閘門，逐支修復並重釘護欄層行數棘輪：

- 內容修正五支（`_EXCESS_CEILING` 幽靈符號補全名／ADR-XPLAT-012 `violations=0` 改寫／
  `test_archive_defect_log.py` 入口點 UTF-8 stdio 保護／`sync_onboarding_baselines.py`
  瘦身 79 行並下修 `SPECIAL_FILES` 上限至 1430／`DEF-101-324` 基線豁免登記因
  ADR-XPLAT-011 §2 正式裁決而刪除，ADR-XPLAT-001 §7 同步訂正）。
- ONBOARDING §7 表① 回填（乾淨 venv，見對話回覆〈二〉的取證）：`total` 20416→20426。
- 護欄層 `_GUARD_LINES_REPIN_LOG` 新增兩列，合計淨額 +684（見
  `CrossPlatform_R99_Scan_Findings.md`）；`_REPIN_NET_CAP_SCHEDULE` 追加到期兌現列
  `(99, 850)`；到期義務常數重新武裝為 `_REPIN_NET_CAP_DUE_ROUND=101`／
  `_REPIN_NET_CAP_DUE_TARGET=750`。
- 過程中發現並補列 `.github/workflows/macos-compat-ci.yml`／`windows-compat-ci.yml`
  漏列的四支根層 SSOT（`tools/lib/ci_run_status.py`／`guard_line_taxonomy.py`／
  `ledger_closing_guards.py`／`oversize_repin.py`，DEF-101-042 同構）；
  `tools/lib/governance_docs.py` 補登記 `CrossPlatform_R99_Scan_Findings.md`。

---

## 己、凍結稽核前綴的一次具名訂正（主控收尾，非收尾窗口動作）

**背景**：獨立複核者（R99 `V-independent-verify`）逐檔通讀 `git diff` 後，發現 `_GUARD_LINES_REPIN_LOG`
的 R99 列裡有一則**敘事與實際變更不符**——行數對，括號裡的內容描述錯：

| | 內容 |
|---|---|
| 訂正前 | `test_check_defect_log_crossref.py +237（ADR 幽靈路徑／幽靈符號兩道新判準）` |
| 實際 diff | 該 +237 全部是三個新測試類別 `TestNetNewVsClosedRatchet`／`TestExternalBlockedLog`／`TestClosingRoundProblemsWiring`（對應新模組 `tools/lib/ledger_closing_guards.py`） |
| 幽靈路徑／幽靈符號兩判準的真實住處 | `tools/tests/test_doc_loc_baseline_freshness_r60.py`，且該檔本輪**零 diff** |
| 訂正後 | `test_check_defect_log_crossref.py +237（淨額棘輪／外部阻塞軌／收輪接線三個新測試類別）` |

**為何非改不可**：這是會永久進 git 歷史的稽核敘事。行數對但理由錯，下一個依它去找東西的人會撲空——
與本輪 ADR-XPLAT-012 §2.4 記載的「結論不變但理由錯了也要說」是同一條紀律。

**訂正的代價（誠實記錄，不藏）**：
1. 第一版訂正把一行拆成兩行 ⇒ 護欄層行數 85932→85933，`TestGuardLayerRatchet` **當場轉紅**（`+1`）。
   ⇒ 改寫成**單行**版本，行數回到 85932，不動任何棘輪額度。
2. 動到**凍結前綴內**某一列的文字 ⇒ `_REPIN_LOG_HISTORY_SHA256` 指紋失配，鎖報「[歷史被改寫]」。
   ⇒ 依該鎖訊息指示重釘：`1ffeffb74191 → 93731d665caf`。
   🔴 **這是一次真正的「改寫凍結歷史」**，因此在此具名留痕：改的是**敘事欄**、非任何數值欄，
   淨額 667／彙總 684／上限 850 三個數字一格未動。複驗 `Ran 138 tests … OK`、`GLC_LINES=85932`。

**留給下一個人的判準**：凍結前綴的指紋鎖**分不出**「竄改數字」與「訂正錯誤敘事」——它只知道前綴變了。
所以每一次重釘 `_REPIN_LOG_HISTORY_SHA256` 都必須像本節這樣具名說明改了什麼、為什麼，
否則那道鎖就退化成「改完重釘一下就好」的橡皮圖章。
