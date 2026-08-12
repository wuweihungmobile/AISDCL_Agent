# CrossPlatform R85 Ledger Closure — 帳本洩壓包（P1）的原文保全面

> **本檔為何屬於「具名治理文件」**（`_GOVERNANCE_DOCS` 的資格判準，逐項對照）：
> ① 它是 15 列已結缺陷**被替換掉的狀態欄與現象欄逐字原文**的唯一居所——主檔那些列
>    已依 `ROW_MAX_BYTES` 瘦身成索引，**唯一還能重驗那些結案是否為真的地方就是本檔**
>    ⇒ 承擔與帳本同等的可讀性義務 ⇒ 受體積守門；
> ② 它逐節寫出「某 DEF-ID 的原文現居本檔某節」的座標宣稱 ⇒ 受 `archive_defect_log`
>    的指針稽核。
> 體例照抄 `CrossPlatform_R82_Ledger_Closure.md`（同一個動作的上一次先例）。
>
> 🔴 **原文一律逐字、零改寫**：下列每一節的 fenced block 內是**整列的原始 markdown**
> （含所有欄位分隔符），直接取自瘦身前的主檔，不做任何摘要或訂正。要複驗某列的結案
> 判定，讀那一整列即可，不需要回去翻 git 歷史。

---

## §0 本輪做了什麼（bytes 死結的出路①）

R84 交棒書 §3／§5.4 對「帳本 bytes 死結」（`DEF-200-053`）明載**兩條非放寬出路**：
① 把超標列的長文搬進具名證據檔（主檔只留索引＋一句話摘要）；② 天花板改為現查值 ≤ 史料末元素。
本包執行的是 **①**，涵蓋 15 列**已結**的超長列（closed-by-decision／fixed，逐列見下）。

**為何只挑已結列**：未結列在結構上不可歸檔、且它們的長文多半是「解鎖條件」——那是還在
約束今日行為的活文字，搬走會讓承接者讀不到。已結列的長文是史料，索引化零操作損失。

**為何結案與瘦身必須是同一個動作**：`OVERSIZE_ROW_EXCESS_CEILING` 是零成長容忍的棘輪，
在那些列上「追加一句結案理由」方向本身就是錯的（先例逐字寫在 `defect_ledger_index.py`
該常數上方的 R80 包 C 段）。


## §1 DEF-01-009（原文逐字）

瘦身前 2203 bytes。以下為整列原始 markdown：

```markdown
| DEF-01-009 | 2026-06-12 | 三專家審查（Architect） | sdd_governance_plugin.py raw 250 行恰貼 plugin_entry ≤250 上限（工具計非空行 217 過關）——後續任何擴充必須先拆 <feature>_plugin/ package | P3 | 下輪擴充前置作業（watch item） | closed-by-decision｜🔴 R75 訂正首詞（原文逐字接於後）：open watch（2026-06-14 improving_06 結案盤點複驗：raw 仍 250、受控指標非空行 **224 < 250**、`check_loc_budget` violations=0＝已自癒；續 watch：對該 plugin 任何擴充前必先拆 package；本輪零擴充不觸發；2026-06-14 improving_08 階段一複驗 raw 仍 250、violations=0 已自癒持平，零擴充不觸發，維持 open watch；2026-06-14 improving_09 階段一複驗 raw 仍 250、`check_loc_budget` violations=0 已自癒持平，本輪零擴充不觸發，維持 open watch；**2026-06-15 improving_14：watch 首次真正觸發並處置**——W-14-2 拓樸橋接擴充 `sdd_governance_plugin.py`，count_loc 自 224→恰貼 250 上限（零餘量）。依本 watch「擴充前先拆」紀律，將拓樸載入邏輯抽出 `plugins/_sdd_topology_signoff.py`（27 行 helper，非 importlinter Rule 1 independence 清單成員 → plugin→helper 合法），plugin 降回 **243 < 250（餘 7）**、`check_loc_budget` violations=0、`lint-imports` 8 kept。watch 紀律有效運作，維持 open watch 續守後續擴充）。**improving_22 複驗：本輪零擴充 sdd_governance_plugin（W 項為 AISLDC_SDD 框架側），watch 不觸發，維持 open watch**；**improving_98 複驗（2026-06-30）：raw 277、`check_loc_budget` violations=0（count_loc 受控指標 < cap 250、自癒持平），本輪 W 為框架側 Copy-on-Evolve（零擴充該 plugin），watch 不觸發；正確處置＝維持 open watch、不投機拆 package（守工程紀律 Rule 2/3）**｜🔴 **R75 複驗（類別 B）**：watch 的行動項（擴充前先拆 package）已被更強機械物涵蓋：`check_loc_budget.py` 的 `SCAN_ROOT=autoclaude` 確實涵蓋本檔，現測 `count_loc=243`／cap 250，越線在當回合即紅（`--json` 現查 `tier_violations: []`、本檔零命中）。硬閘留原地續守。 |
```

## §2 DEF-101-068（原文逐字）

瘦身前 4570 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-068 | 2026-07-14 | R3 Mac/Windows 相容性複審（四方「架構最佳化建議」彙整，非本輪阻擋項，記事存證供下一輪參考） | **跨平台架構優化建議清單（本輪不逕行實作，範圍限於解決本輪 P0~P2 阻擋項）**：(a) Architect＝CI paths 白名單應由「條列法」改為「單一事實來源」（擴充 `test_ci_paths_cover_root_consumers.py` 涵蓋全部 4 個 CI workflow，而非只查自己）；(b) Architect/SD＝腳本雙軌維護（`.sh`+`.ps1` 各自完整實作）長期宜降為「薄 wrapper + 共用 Python 核心」（`tools/dev_start.py` 為既有示範模式），候選：`bootstrap`/`integration_gate`/`local_ci_gate`/`install_git_hooks`/`install-hooks`；(c) SD＝git hooks liveness 偵測邏輯在 `integration_gate.{sh,ps1}` 與 `local_ci_gate.{sh,ps1}` 重複 4 份、Git Bash/WSL 偵測樣板在至少 3 支 `.ps1` 重複，建議抽共用模組；(d) SD＝`check_script_parity.py` 目前只比對 step 標籤序列（docstring 自承不比語意），可選擇性加深至「雙邊實際執行 + 粗粒度輸出 diff」；(e) SA＝建議寫 `check_defect_log_crossref.py` 機械掃描文件內 `DEF-\d+-\d+` 引用，與帳本實際狀態比對揪跨文件同步落差（DEF-101-066 這類問題的治本解）；(f) QA＝「生產端接線」驗證應制度化為三段式檢核（觸發/執行/斷言），建議寫成可重用的 meta-lint 而非每輪人工複審碰運氣；(g) QA＝nightly-alert 類「等真實失敗才走到的分支」宜於設計時就內建可測試性（本輪已用 `simulate_nightly_failure` 落地此建議，其餘同類機制可比照）；(h) SA＝`gh issue create`（windows/macos-nightly-alert）缺 `--label`，與既有慣例（`aisdlc-sdd-fsm-chaos-nightly.yml` 有 `--label "p0,chaos,fsm-runtime"`）不一致 | P3（架構建議，非缺陷） | 記事存證，排入下一輪 B 軌/C 軌評估；(c)(g) 已落地 | closed-by-decision｜🔴 R75 訂正首詞（原文逐字接於後）：open（記事存證；(g) 已於本輪 `simulate_nightly_failure` 落地；**(c) 已於 S11 落地**：liveness 偵測抽出 `tools/check_hooks_liveness.py`（四呼叫點 `local_ci_gate.{ps1,sh}`/`integration_gate.{ps1,sh}` 改一行呼叫）+ Git Bash 偵測抽出 `tools/lib/Find-GitBash.ps1`（三呼叫點 `ci-gate.ps1`/`install_git_hooks.ps1`/`install-hooks.ps1` dot-source 改一行呼叫），單元測試 `tools/tests/test_check_hooks_liveness.py`；其餘子項 **R14 補記（2026-07-20 Architect 檢視 ARCH-GAP-5，訂正帳本滯後實況）**：(a) **已落地**（`AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py:10` S6 明文本子項、已擴至 4 份 CI workflow）；(e) **已落地**（`tools/check_defect_log_crossref.py`，`root-infra-ci.yml:44` 明文 DEF-101-068(e)）；(h) **已落地**（windows/macos-compat 兩 workflow `gh issue create` 已帶 `--label "p1,…,nightly"`）；(b) **部分落地**（local_ci_gate 已於 R12 收斂薄殼＋Python 單核心；bootstrap／integration_gate 仍雙原生實作，維持 defer）；(d) **維持 defer 並明文觸發判準**——下一個「同名 step 語意漂移」實證出現才投資「雙邊執行＋輸出 diff」重型基建；(f) **降級處置**——可機械子集（守門工具三處清單同步）已由 `tools/tests/test_root_infra_parity.py` 覆蓋，泛用 meta-lint 難寫準，殘餘改為迭代範本 checklist 條目、不硬寫泛用 lint。另註（守門侷限實證）：本列子項進度低於 `check_defect_log_crossref.py` 守門粒度（該工具只比對狀態字、無法偵測列內子項滯後），本次滯後即此侷限之實證；**R22 校正**：經 R22 四方一審核實，(b) 候選已於 R16（DEF-101-232）完整落地——`bootstrap_core.py`（348 行）／`integration_gate_core.py`（260 行）／`AutoClaude/tools/run_act_core.py` 皆已收斂為 Python 核心＋薄殼，本列 R14 快照所稱「仍雙原生實作，維持 defer」已過期，訂正為 fixed@R16（(b) 全部候選）｜🔴 **R75 複驗（類別 B）**：八子項現查：(a)(b)(c)(e)(g)(h) 皆已落地——`tools/check_hooks_liveness.py`、`tools/lib/Find-GitBash.ps1`、`tools/bootstrap_core.py`、`tools/integration_gate_core.py`、`AutoClaude/tools/run_act_core.py`、`tools/tests/test_root_infra_parity.py` 六支具名產物全在，`root-infra-ci.yml:59` 逐字具名「DEF-101-068(e) 落地」；(d)(f) 是**已拍板的決定**（附觸發判準／降級處置），不是待辦。`pytest` 兩支 → **41 passed，rc=0**。 |
```

## §3 DEF-101-200（原文逐字）

瘦身前 4115 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-200 | 2026-07-20 | R14 Architect 架構檢視（ARCH-GAP-2） | **排程「初次安裝」能力反向不對等——mac 有一鍵安裝器、Windows 沒有**：`AutoClaude/tools/fix_nightly_catchup.ps1:16-25` 以 `$ErrorActionPreference='Stop'`＋`Get-ScheduledTask` 開場，任務不存在直接炸＝僅能校正既有任務；新 Windows 機器（或任務誤刪後）無一鍵重建路徑，亦無 `--status` 心跳三態對等物 | P2 | 排下輪 Windows 輪（需實機驗證，勿在 mac 輪盲改）：升級為 ensure 語意（不存在→`Register-ScheduledTask` 建立）＋加 `-Status`，或另立 `install_win_nightly.ps1` 並更新 parity 登記 | fixed@R23｜🔴 R75 訂正首詞（原文逐字接於後）：open（routed 下輪 Windows 輪；ARCH-OPT-5 設計已載於本列分流欄；**R15 補三筆 Windows 輪同捆項**：ARCH-R15-5〔`run_local_nightly.ps1` 每日 RunId log 無保留期 prune、mac 側 R15 已落 14 天，兩平台政策須對齊〕、ARCH-R15-1 Windows 側〔`nightly_latest.log` 為全量 log 非 3 行契約，FAIL 內容哨兵需另設計〕、SCAN-C-11〔windows-compat nightly-full 取消語意與 macos 側 R13 CI-5 不對齊，僅 dispatch 連發情境〕）；**R22 校正**：核心訴求（ensure 語意安裝＋`-Status`）fixed@R19（`tools/install_windows_nightly.ps1` 新建，DEF-101-245）+R20 硬化（DEF-101-248/249/253/255）。三個 R15 riders 逐項訂正：ARCH-R15-5（nightly log 無保留期）本輪 fixed@R22——`run_local_nightly.ps1` 補 14 天輪替並排除 `nightly_latest.log`（比照 mac 側既有政策），新增 `test_nightly_log_retention_rotation_present` 靜態鎖；**R23 校正**：ARCH-R15-1（Windows FAIL 內容哨兵設計）**fixed@R23**——先讀 `run_local_nightly.ps1` 確認收尾處本已存在穩定機械可讀行 `Log ("END exit decision: exit={0} (failed stages: ...)" / "exit=0 (no failed stages...)")`（R9 複審 (c) 既有設計，非新增），故不需先補寫摘要行；新增 `tools/dev_start.py::_windows_heartbeat_fail_note()` tail 位元組窗格（16KB）掃描此行、`_check_nightly_heartbeat()` windows 分支改呼叫（原邏輯只判 mtime 新鮮度，讀不到「持續紅燈但仍在跑」狀態），新增 `TestWindowsHeartbeatFailSentinel`（原 4 tests：exit=1 帶 failed stages 告警＋summary／exit=0 零告警／大型全量 log 雜訊下仍命中尾端錨點／找不到錨點安全回 None；**R23 一審後追加至 7 tests**——SD 一審 bug-injection 命中原正則對空白數量/大小寫零容忍造成假陰性〔冒號後多空白／`END`小寫／`END`後多空白三種真實變體皆偵測不到 FAIL〕，`_WINDOWS_EXIT_DECISION_RE` 改為 `\s+`+`re.IGNORECASE` 並補 3 支對應測試；SD 二審另指出放寬後假陽性面擴大〔任何以 end 結尾單字緊接 `exit decision: exit=N` 皆會誤觸發，如 append/recommend/weekend〕，判定為既有設計弱點被放大而非新類別風險、且只影響 advisory 訊息，記入 DEF-101-263 供下輪視情況加 `\b` 邊界收斂）；SCAN-C-11（nightly-full 取消語意對齊）**fixed@R23**——`windows-compat-ci.yml` 原 workflow 層級單一 concurrency group 改為 job 層級三組獨立 concurrency（比照 `macos-compat-ci.yml` R13/CI-5 既有修復模式：windows-smoke per-ref+cancel=true、windows-nightly-full／windows-nightly-alert 各自固定字串 group+cancel=false），修復「同 event_name 內連續 workflow_dispatch 互踩取消」風險；`test_workflow_permission_concurrency_lock.py` 等既有 workflow 相關測試全數複跑通過，`yaml.safe_load` 驗證語法正確｜🔴 **R75 複驗（類別 A）**：核心 fixed@R19、三筆 R15 riders 各 fixed@R22／R23，本欄早已逐項載明、只有首詞沒跟。現查具名產物皆在：`tools/install_windows_nightly.ps1`、`dev_start.py::_windows_heartbeat_fail_note`、`dev_start.py:1658 _WINDOWS_EXIT_DECISION_RE`、`test_run_local_nightly_static.py` 14 天輪替鎖。`pytest ...::TestWindowsHeartbeatFailSentinel` → **10 passed**；`-k retention` → **1 passed**，皆 rc=0。 |
```

## §4 DEF-101-278（原文逐字）

瘦身前 2035 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-278 | 2026-07-23 | R28 四方一審 Architect（複核 DEF-101-277 修復完整性時延伸檢查） | **ONBOARDING.md §6.1 `root-infra-ci.yml` 條目第 6 項與 `.github/workflows/root-infra-ci.yml:25` 檔頭註解，皆仍用「腳本對等閘：成對 `.sh`/`.ps1` 的 step 標籤」概括描述 `check_script_parity.py`**——與 DEF-101-277 訂正的 §6 本體同款簡化措辭，但 Architect 複核後判定：此處是**兩處彼此一致**的既有精簡摘要（ONBOARDING 本行明文「詳細內容以 workflow 檔頭註解為準」，刻意不重複展開機制細節以避免雙處同步負擔），非本輪新引入的漂移，且 `check_script_parity.py` 整體仍保留 step 標籤比對機制本身（僅 bootstrap/integration_gate/run_act 四對目前改掛 thinness hash、`_MARKER_PAIRS` 對這幾對是空清單，機制本身未被移除），故此摘要句並非錯誤陳述 | P4（記事存證；非本輪新漂移、非錯誤陳述，兩處一致且互為對照，不影響任何機械閘門判準） | 若下一輪要進一步精確化，可在此摘要句補一句「（現無任何 pair 掛此機制，見 §6 本體）」；非必要 | fixed@R78（原首詞為 `open watch`，原文完整接於後）🔴 **R78 逐處實查後結案**：① ONBOARDING §6.1 那一處**已不存在**——R68 訂正② 把該列逐道列舉整段刪除，現行文字改為「一律以 workflow 檔頭註解為準」；② workflow 那一處還在（行號由 `:25` 漂到 `:40`），已就地改寫為「註冊完整性」主述並標明 `_MARKER_PAIRS` 現為空清單、沿革一律以 `check_script_parity.py` docstring 為準（不複寫第二份）。`check_script_parity.py` rc=0（只改註解、機制零改動）。逐處實查與紅→綠見 `CrossPlatform_R78_Debt_Audit.md` §一 ｜以下為原文逐字保留：open watch（R28 四方一審 Architect 發現，記事存證；Architect 本人判定優先度低於 DEF-101-277、不必立即修，僅供未來若再擴充此段時參考） |
```

## §5 DEF-101-297（原文逐字）

瘦身前 2135 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-297 | 2026-07-24 | R33 修復 DEF-101-295 控制字元淨化時，主控親自撰寫交叉測試發現 | **`tools/git-hooks/pre-commit` 的 `_ntfs_seg_bad()` 偵測不到路徑段內嵌的 `\n`（0x0A）控制字元**：`printf '%s' "$p" \| LC_ALL=C grep -q '[[:cntrl:]]'` 逐行比對時，換行本身被 `printf` 當成實際換行輸出、成為 grep 的行分隔符而被「消耗」，不會出現在任一行的內容裡讓 `[[:cntrl:]]` 字元類別比對到；兩個 Python 版（`ord(ch) < 0x20` 逐字元迭代，見 `check_ntfs_paths.py:71`／`logger._sanitize_log_filename`）不受此限、皆能正確偵測。已用 `bash -c` 實測重現（`CLEAN` vs 預期 `BAD`） | P4（狹窄既有限制，非本輪引入；CI 端 `check_ntfs_paths.py`（root-infra-ci.yml 全變更觸發）仍會擋下含 `\n` 的路徑，非完全繞過，只是本機 `pre-commit` 少了一層即時攔截，非本輪範圍內改寫 bash 邏輯的理由——改寫需換一套非逐行比對的偵測法，屬另一輪範圍） | 如實記載，暫不修復（backlog）；`tools/tests/test_windows_forbidden_filename_parity.py` 的控制字元交叉鎖測試已明確排除 `\n` 並在程式碼註解說明原因，避免此已知限制被誤判為測試缺陷 | fixed@R78（原首詞為 `open`，原文完整接於後）🔴 **R78 修**：在原 grep 之前加一道不經行分隔載具的 bash pattern match（`case "$p" in *[[:cntrl:]]*)`），原 grep 保留為第二層＝POSIX 字元類若不受支援時行為與今日完全相同、不新增假紅。Git Bash 5.2.37 實測：內嵌 `\n` 舊式 MISS／新式 HIT；`\r\t`／ESC／DEL 兩式皆 HIT；全 repo 27534 條 tracked 路徑 case-pattern 命中 0（含 CJK 與含空白路徑）。抽出活函式端到端驅動：內嵌 LF → rc=0 `含控制字元`。`bash -n` rc=0。**射程**＝本機 hook 追上 CI（`check_ntfs_paths.py` 走 Python str 本就看得到）；**未測**＝bash 3.2。見 `CrossPlatform_R78_Debt_Audit.md` §一 ｜以下為原文逐字保留：open（backlog，如實記載存證，CI 端防線仍在，不影響本輪其餘驗證結論） |
```

## §6 DEF-101-351（原文逐字）

瘦身前 2954 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-351 | 2026-07-24 | 同 DEF-101-350 情境下額外發現，經初步排查後判斷非本輪範圍內可安全速修，如實記載待查而非臆測修復 | `tools/tests/test_bash_probe_spec_contract.py::TestUsableBashEndToEndWithRestrictedPath::test_usable_bash_rejects_candidate_when_path_lacks_dirname` 在本機失敗：測試用 `mock.patch.dict(os.environ, {"PATH": ""}, clear=True)` 模擬「PATH 缺 dirname」情境，預期 `bash_probe.usable_bash()` 應回傳 `None`，實際卻回傳可用路徑。同檔案另一支姊妹測試（`TestProbeCmdRealSubprocessBehavior::test_fails_when_path_lacks_dirname`，直接對 `subprocess.run` 傳入 `env={"PATH": ""}`）行為符合預期、確實會失敗——兩者差異可能在於 `usable_bash()` 未顯式傳 `env=` 給 subprocess（依賴繼承 `os.environ`），而本機 Git Bash/MSYS2 runtime 疑似在僅有單一 PATH 鍵的 env 與 `os.environ.clear()` 後殘留其他 Windows 系統變數（如 `SystemRoot`）的 env 之間，觸發不同的內部 PATH 補齊路徑，導致縱使 PATH 為空仍解析得到 `dirname`——此為 MSYS2 runtime 內部行為推測，未實際查證到底層機制，不確定修復 `usable_bash()` 本身、或修正測試 mock 手法何者為正確方向，故如實記載待查，不臆測修復。**不影響 push 閘門**：本測試不在 `tools/run_root_unittests.py`（pre-push 實際執行的 unittest discover 範圍）內被發現/執行（該指令跑 420 tests 全綠，不含此測試），僅在 `pytest tools/tests/` 全套跑會發現此失敗 | P3（不阻擋 push 閘門，範圍侷限於單一 mock 情境的 wiring 層測試） | open（backlog，下一輪或有餘裕時查證 MSYS2 runtime 內部 PATH 解析機制） | fixed@R71｜🔴 R75 訂正首詞（原文逐字接於後）：open（**R51 根層修復包複核**：本機 macOS/Darwin 環境重新執行 `tools/tests/test_bash_probe_spec_contract.py` 全部 5 項與 `tools/tests/` 全套〔486 passed／4 skipped／40 subtests passed〕皆 100% PASSED，未能重現本列所述失敗；因原始現象疑似為 Windows Git Bash／MSYS2 runtime 特有的 PATH 補齊行為，macOS 環境結構性不具備該 runtime，本次重跑結果不足以判定原始缺陷已消失，狀態維持 open、待下次於原始 Windows/MSYS2 環境重新驗證方能改判——僅如實記載本次複核落差，避免帳本停留在 R45 之後未再驗證的舊狀態）｜🔴 **R75 複驗（類別 A）**：🔴 本欄自訂改判條件逐字為「待下次於原始 Windows/MSYS2 環境重新驗證方能改判」——R75 正在 Windows 11 原生 PowerShell 上，條件到期。實跑本列具名那一支 `test_usable_bash_rejects_candidate_when_path_lacks_dirname` → **PASSED**，同檔全套 **19 passed／2 subtests**，皆 rc=0。成因＝R71 為 `DEF-101-628` 落地的 `_platform_helpers.py:97 honours_external_path` 一併治好，故記 R71 而非 R75。 |
```

## §7 DEF-101-242（原文逐字）

瘦身前 2840 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-242 | 2026-07-21 | R17 四方一審（QA 獨立 bug-injection 反向驗證） | QA 複審 DEF-101-241 ①③ 兩項修復時，用 bug-injection 揪出兩個「測試提供的保護力比表面看起來弱」的殘留缺口（非本輪引入的新回歸，但本輪修復恰好觸及）：**①（P2）`tools/tests/test_find_git_bash_parity.py` 只做結構等價比對（regex 抽取兩份原始碼的候選路徑/排除字面片段），不驗證行為**——QA 把 `find_git_bash()` 呼叫點改回舊版 `"system32" not in found.lower()`（只改呼叫點、不動 `_has_system32_segment()` 定義），parity 測試仍全綠，因 regex 抽取到的仍是死代碼裡的同一段文字；對呼叫點本身的行為迴歸零防護力。**②（P2）DEF-101-241① 手動補上的三行 CI paths**（`tools/lib/platform_utils.py`／`tools/bootstrap_core.py`／`AutoClaude/tools/run_act_core.py`）**本身未受機械鎖保護**——QA 對稱移除 `windows-compat-ci.yml` 兩側的 `platform_utils.py` 一行，`test_ci_paths_cover_root_consumers.py` 9 個測試仍全部 PASS（根因：`test_platform_utils_dedup.py` 用 `rglob` 掃描消費這三檔，掃描器的 `_IMPORT_RE` BFS 只認得 `import X` 陳述式，看不到這種消費模式，故對稱誤刪無法被現有覆蓋率檢查抓到；先前單側移除是被另一支對稱性檢查意外攔到，非真被覆蓋率檢查抓到） | P2×2（QA 一審判定均非阻斷，本輪合入不受影響） | ①排下輪：補一支對 `find_git_bash()`/`_has_system32_segment()` 直接呼叫的行為測試（不依賴 regex 結構比對）；②排下輪：仿 `test_known_consumers_detected()`「已知消費檔必被掃出」手法，替這三檔補一條專屬機械存在性鎖 | fixed@R19｜🔴 R75 訂正首詞（原文逐字接於後）：open（QA 一審明確判定非阻斷，記事存證排入下一輪 backlog；四方一審 Architect/SA/SD/QA 對本輪其餘修復之獨立覆核皆確認有效）；**R22 校正**：①②經核實已 fixed@R19（見 DEF-101-244①②：`test_find_git_bash_parity.py::TestFindGitBashBehavior` 行為測試、`test_ci_paths_cover_root_consumers.py::_resolve_sys_path_insert_dirs`/`_KNOWN_SUBPROCESS_ONLY_CONSUMERS` 存在性鎖），本列狀態文字過期未同步，本輪訂正；QA 一審 bug-injection 複驗 `TestFindGitBashBehavior` 回歸鎖確實有鑑別力｜🔴 **R75 複驗（類別 A）**：本列僅 ①② 兩項且 R22 已核實皆 fixed@R19，本欄亦自載「狀態文字過期未同步」。兩鎖現查皆綠：`pytest tools/tests/test_find_git_bash_parity.py::TestFindGitBashBehavior` → **8 passed**；`pytest AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` → **34 passed**（含 `_resolve_sys_path_insert_dirs`／`_KNOWN_SUBPROCESS_ONLY_CONSUMERS`），皆 rc=0。 |
```

## §8 DEF-101-435（原文逐字）

瘦身前 2492 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-435 | 2026-07-27 | R55 Workflow 五維掃描（Scan-C 發現）＋round 1 SA／Architect 確認為真但與平台無關 | `.github/workflows/aisdlc-sdd-artifact-cleanup.yml` 檔頭註解宣稱「drift-daily-report 無 upload」，但 `aisdlc-sdd-drift-daily.yml` 第 88-95 行確有 upload-artifact 步驟，`ALLOWLIST_PREFIXES` 未含 `drift-daily-report` 前綴，文件與程式碼矛盾 | P4（確認屬實但 `drift-daily.yml` 為 `runs-on: ubuntu-latest`，純 CI artifact 配額治理議題，與 macOS/Windows 平台相容性無關） | 建議記入一般 CI 維護缺陷帳本或下一輪 C 軌工作流帳本處理，非本輪 Mac/Windows 相容性授權範圍 | fixed@R78（原首詞為 `open`，原文完整接於後）｜open（deferred；本輪未修改任何程式碼，僅如實記載） 🔴 **R60 改派（round 1 QA-R60-04【4】／Scan-G G-03）**：本列分流欄的「一般 CI 維護缺陷帳本」**這個容器不存在**——`grep -rn "一般 CI 維護" --include=*.md .` 全庫只命中主檔 L101／L102（即 `DEF-101-434` 與本列自己），`find . -iname '*defect*'` 只有 `AutoSDD_Defect_Log*` 家族與 30 份分類模板 ⇒ 指向不存在的容器＝死信。前提今日仍成立（`aisdlc-sdd-artifact-cleanup.yml:17` 仍寫「drift-daily.yml 無 upload」，而 `aisdlc-sdd-drift-daily.yml:88-94` 確有 `upload-artifact@v6`／`name: drift-daily-report`，`ALLOWLIST_PREFIXES` 不含該前綴）。**改派為：未指派 backlog（C 軌／一般 CI 維護）**，並訂正容器名：本 repo **沒有**「一般 CI 維護缺陷帳本」，合法容器只有本帳本與 `AutoClaude/docs/04_planning/` C 軌帳本。回執規則同硬規則③。見 DEF-101-555（現居 archive_33）。🔴 **R78 修並結案**（原文逐字保全於前）：當回合複驗前提**仍成立**（cleanup.yml:17 假事實在、drift-daily.yml:88-95 確有 `upload-artifact@v6`／`name: drift-daily-report`／`retention-days: 90`、allowlist 三個前綴不含它）。修法＝**只改註解不改刪除行為**：把假事實改寫為「刻意不列入 allowlist」的具名決策並寫明理由（retention 90 > 本檔 7 天門檻＝長期取證產物，納入即殲滅，與 AutoClaude 家族排除理由同構），檔頭維護指示改雙欄使新 artifact 不能兩邊都不寫。不逕自加進 allowlist：那是行為變更、需人拍板，而缺陷本體逐字是「文件與程式碼矛盾」。見 `CrossPlatform_R78_Debt_Audit.md` §一 |
```

## §9 DEF-101-500（原文逐字）

瘦身前 3434 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-500 | 2026-07-27 | R57 round 3 四方其餘 P4（Architect ×3、QA ×1、SD ×2，**皆不影響正確性，統一登記處置**） | ①**ARCH-R57R3-01**：新寫的 Scan-E 判例節，其「觀測不同對象 → 保留多份」分支所舉的 `bash_probe_spec.py` 例證是**跨語言**，在上一節的第一層分診問句就已被路由走，該分支目前無可達實例——雙重路由會讓下一輪難判斷第二層是細分還是覆蓋第一層。②**ARCH-R57R3-02**：`_platform_helpers.py` 首句契約仍寫「測試 fixture 輔助函式」，但已進駐一支原始碼解析 SSOT（PowerShell 剝註解器，佔全檔一半以上行數），契約與內容脫節＝雜物抽屜早期訊號。③**ARCH-R57R3-04**：DEF-101-496 的 B3 deferred 只點名「解析 LATEST 版目錄」helper，未涵蓋同家族的 `_FROZEN_SDD_VERSION_RE` + `_exclude_frozen_sdd_versions()`（bash_parity:244／cross_consistency:415 逐字相同）與 `_FROZEN_VERSION_DIR_RE`（另 2 檔）——其失效模式與本輪修的完全同型（`\d+\.\d+` 抓不到 `v1.0.1` 三段版號時四份會同時靜默誤分類）。④**QA-R57R3-01**：`_ci_scan_anchors.py` docstring 的「已實測涵蓋（`_FORM_EVASIONS` 逐條釘住）」把 `ls` 也列入，但 `_FORM_EVASIONS` 實際未含 `ls` 樣本。⑤**SD-R57R3-02**：`cut_ps_inline_comment` 收斂進 SSOT 後全 repo 無真實消費端，只被自己的單元測試呼叫，卻仍列於 `_PS_STRIPPER_SYMBOLS` 的呼叫端鎖要求內。⑥**SD-R57R3-03**：`[IO.Directory]::EnumerateFiles(...)` 同樣三錨全綠但未列入 `_KNOWN_UNCOVERED` | P4 ×6（三方一致認定不影響任何正確性或閘門） | ①②④⑥ 本輪修復；③⑤ 列 R58 backlog | fixed@R57 round 3｜🔴 R60 round 2 補《格式定義》合法首詞（原首詞非合法值，原文完整接於後）：fixed/deferred@R57 round 3：**①** 判例節該處加註「此例其實在第一層即已路由，此處僅借其『獨立訊號』語意」，並補一行「本判準於 R57 僅套用於 `_CI_TREE_RE` 一組，repo-wide 同語言重複掃描列 R58 backlog」避免下一輪誤判 R57 兩套標準。**②** 模組首句契約改為明列兩類收納物（跨平台測試 fixture 輔助函式 **與** 供靜態鎖消費的原始碼解析 SSOT）並補第二類判準；更徹底的「拆到 `_ps_source.py`」需連動呼叫端鎖翻修，依 Rule 3 外科式原則列 R58。**④⑥** docstring 涵蓋清單與釘選表對齊（**R57 round 4 SA-R57R4-03 訂正本欄原文**：原記為「移除未釘住的 `ls`」，與實際落地**相反**——實際做的是**保留** docstring 的 `ls` 宣稱、改為在 `_FORM_EVASIONS` **補上 `"R3 ls alias"` 樣本**，因 Architect round 3 已實測 `ls` 確實會被 cmdlet 錨命中〔宣稱本身為真，缺的只是常駐樣本〕，補樣本比刪宣稱更好；⑥ 則確為補列 `EnumerateFiles` 進 `_KNOWN_UNCOVERED`。**本欄寫反這件事本身，正是本輪反覆在抓的「宣稱與實況不符」在帳本層的復發**，由 round 4 SA 逐項回源實查抓出，如實留痕不掩飾）。**③** 已在 DEF-101-496 的 B3 敘述補上範圍延伸（點名四份姊妹複本），R58 收斂時一併納入。**⑤** `cut_ps_inline_comment` 目前確為零消費端，但移除它會讓 `strip_ps_comments` 的單行邏輯失去獨立測試面；判為 deferred，R58 若仍無消費端則刪除 |
```

## §10 DEF-101-550（原文逐字）

瘦身前 2928 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-550 | 2026-07-28 | R60 Scan-E（E-A-04）落地包 Pkg-6 撰寫 ADR 時實查發現（非掃描者、非反駁者原始清單內） | `DEF-101-370`（fixed@R44，P2）拍板：`AISDLC_SDD/AISDLC_SDD_v0.30/EVOLUTION_LOG.md` 為「未來查詢『Copy-on-Evolve 是否曾被打破、在什麼條件下』」的**權威索引入口**（帳本為逐版驗證細節的權威出處，兩者互補不重複），並據此在 R44 新增「凍結基線例外」結構化章節。實查該檔：`grep -n "凍結基線例外"` 只有 `:7 …（R44，2026-07-25）` 與 `:22 …（R45，2026-07-25）` **兩節**；…（完整證據見 `CrossPlatform_R60_Fix_Evidence.md`） | P3（流程／文件治理缺口，與 DEF-101-370 同型同級；不影響 R46 修復本身之正確性——該修復已由 `tools/tests/test_sanitize_component_frozen_sdd_versions_lock.py` 等機械鎖守） | AISDLC_SDD 領域（`AISDLC_SDD_v0.30` 為 LATEST、可修改版本，非 Pkg-6 檔案範圍）；Pkg-6 已在 ADR-XPLAT-001 §7 列為 routed 落差 | fixed@R77（🔴 **R77 訂正首詞**（原欄文自下方冒號後**完整保留、語意零變更**；體例比照 `DEF-101-433`／`DEF-101-556`）：解鎖條件早在 **R60 當輪即已達成**，只是沒有人回頭改首詞，於是本列在未結存量裡躺了 16 輪。R77 回樹逐項複驗 `AISDLC_SDD/AISDLC_SDD_v0.30/EVOLUTION_LOG.md`：`:37` 有「凍結基線例外：v0.01～v0.29 `path_cost.py` 檔名淨化回補（R46，2026-07-26）」章節，`:45`~`:52` 八欄一欄不缺（範圍／日期+signoff／打破理由／修法／TLC 證據／驗證／殘留落差／回退指引），且本列特別要求的「核准依據事後被證偽」在 `:46` 與 `:51` 兩處都誠實寫到；`:41` 逐字自述「本節為 R60 補記」並點名本列 ID ⇒ 開列的那一輪自己就把它做完了。本輪同時把「解鎖條件命名了具名檔案章節」這一類列改為可批次體檢，配方見 `DEF-101-871`）：open（承接輪次：**未指派**；R60 Pkg-6 僅查證並記錄，未修）：🔴 **R60 round 2 補（round 1 SA-R60-08）**：原僅寫「AISDLC_SDD 領域」＝領域不是輪次，違反 `CrossPlatform_Scan_Dimensions.md:149` R59 硬規則②，故明標承接輪次為**未指派**（解鎖條件本身已具體到可直接執行，見下）。建議在 `AISDLC_SDD/AISDLC_SDD_v0.30/EVOLUTION_LOG.md` 補「凍結基線例外：v0.01～v0.29 `path_cost.py` 淨化回補（R46，2026-07-26）」章節，欄位比照既有兩節八欄（範圍／日期+signoff／打破理由／修法／TLC 證據／驗證／殘留落差／回退指引），內容可直接取自 `docs/04_planning/ADR/ADR-XPLAT-001-…md` §3.3（含「核准依據事後經 SA 複驗證偽（實際為 FileNotFoundError／零消費者）但修復未回退、僅訂正帳本敘事」這項必須誠實記載的…（完整證據見 `CrossPlatform_R60_Fix_Evidence.md`） |
```

## §11 DEF-101-560（原文逐字）

瘦身前 4252 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-560 | 2026-07-28 | R60 round 2 帳本包自身寫入時被**新加的落地前斷言**當場抓到（非四方複審、非掃描發現——本包為避免重蹈自己第一版的錯而加的「每列必須切成 7 欄」斷言反手抓出一筆存量真缺陷） | **帳本表格列含未轉義的字面 pipe，使該列被切成 8~9 欄，兩道閘門取到的「最後一欄」是散文碎片而不是狀態欄**（兩者的欄位切分都只把**未被反斜線前導的** pipe 當分隔符：`check_defect_log_crossref.py:115`、`archive_defect_log.py:84 _CELL_SPLIT_RE`）。**主檔唯一命中且有活體後果的是 `DEF-101-524`**：其真實狀態欄是 `no_action_needed（流程紀錄）`（應分類 `closed-by-decision`），但因狀態欄內兩處 code span 含字面 pipe，`cells[-1]` 取到散文碎片、`_classify` 在碎片裡命中 `open` ⇒ **被兩道閘門一致誤判為活躍 `open`**。全家族掃描：**15 列欄數異常**（主檔 1＋archive 14）（逐列清單與命令輸出見 `CrossPlatform_R60_Fix_Evidence.md` 的 `## DEF-101-560` 節） | P3（主檔那一列使兩道閘門的分類與帳本真實狀態**相反**——`closed-by-decision` 被讀成 `open`，一筆已結案的流程紀實被永久當成活躍待辦並永遠擋在歸檔外；archive 側 14 列今日零活體後果〔那些 ID 只存在於 archive，`check()` 的主檔↔archive 分類比對會直接 `continue`〕故不調升） | 主檔那一列本輪 round 2 立即修復；archive 側 14 列**具名不修**（理由見狀態欄）；「每列必須切成 7 欄」的機械斷言屬 `tools/` 閘門擁有包，已提跨包請求 | fixed@R60（主檔）／open（archive 側 14 列，承接輪次：**未指派**）：**主檔** `DEF-101-524` 兩處字面 pipe 各加一個反斜線前導，落地後該列切為 7 欄、`_classify` 由 `'open'` 轉為 `'closed-by-decision'`，並附**零語意變更證明**（把產物的轉義 pipe 全部還原成裸 pipe 後與原文逐字元相同）。**archive 側 14 列刻意不動，理由具名**：(a) 今日零活體後果；(b) 「pipe 在 code span 內即為字面」這條啟發式實測只能正確處理 15 列中的 9 列，其餘 6 列（archive_04:86／87、archive_09:13／14／15、archive_16:48）需**逐列人工判定**；(c) 盲目轉義的失敗模式比現況嚴重得多——誤把真正的分隔符轉義會讓整列欄位靜默左移、七欄全錯位，而那沒有任何現存閘門會抓到（正是本筆要治的病，不該用同一種病去治）。承接者可直接執行的落地建議見證據檔該節。🔴 **R60 r3 進度補述**：「每列必須切成 7 欄」的機械斷言已由 Pkg-P6 於 `check_defect_log_crossref.py` 落地（`row_arity_problems()`，Pkg-P5 實查主檔 **0 筆問題**）；archive 側 14 列仍**具名不修**（Pkg-P5 以 `_row_cells()` 實算切片數 != 表頭 9 者確為 14 列），但已由 Pkg-P7 新增的判準(7) 以**具名基線**承載（主檔零豁免）而非留在解析面外；`archive_defect_log.py` 自帶的 `_cells()` 複本亦已由 **Pkg-P7 收斂完成**（本地零複本、全部委派 `gate.*`）。🔴 該次移除同時打斷一處**刻意依賴** `ADL._CELL_SPLIT_RE` 的呼叫端、根層全套翻紅——見 `DEF-101-581`。🔴 **R60 r3 Pkg-P11 補述（archive 側欄數異常列首次有機械載具管住）**：那批列維持**不修**，但處置由「留在解析面外」升為 `archive_defect_log._ARITY_BASELINE` **具名基線 ＋ stale 自檢 ＋ 只准往下改**（逐檔筆數以該常數與 `--check` 逐檔列印為權威，本列不複寫一份）；主檔與**新建**的 archive **零豁免**（`apply()` 只建新檔、新檔名不在基線內 ⇒ 壞列一律硬擋）。Pkg-P11 獨立實測：那批列的 DEF-ID 與主檔現有 ID **交集為空** ⇒ 「今日零活體後果」的宣稱成立。⚠️ **給未來輪次的警示**：`_ARITY_BASELINE` 帶 stale 自檢，任何人**編輯 archive 檔的表格列**而改變欄數異常筆數，`--check` 會 **fail-loud**（實測數 > 登記數與 < 登記數皆紅，不會靜默通過）——請照它印出的訊息把數字往下改，或把該列欄內的字面豎線加反斜線轉義。 |
```

## §12 DEF-101-561（原文逐字）

瘦身前 6803 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-561 | 2026-07-29 | R60 round 1 四方複審（ARCH-R60-09，P3 系統性視角）；**本列＝如實記載該架構判斷，刻意不加第 N+1 道鎖**（加鎖正是該 finding 指認的病） | **護欄層已與被護的生產系統同體積，本輪三個 blocking 假綠全在護欄層自己身上**。Architect 量測：`tools/tests/*.py` R57(`75aab89`)=**43**→R59(`f9435c5`)=**45**→HEAD tracked=**45**＋7 未追蹤、累計 **20,188** 行；主控 round 2 後重量＝**55 支／21,861 行**。對照 AutoClaude 生產碼 `check_loc_budget` total=**20,361**／cap=20,438 ⇒ 護欄層行數**已超過**被它護的生產碼；`MIN_TESTS` **616→661→756**。定性：三個假綠（ARCH-R60-01 稽核面缺角／-02 `assertIn(rc,(0,1))` 恆真／-06 掃描器對 docstring 誤命中致檔案級全豁免）**無一發生在被鎖的生產碼上**＝新鎖正以比它擋下的缺陷更高的速率生產新的未受檢面 | P3（架構級趨勢判斷，非現存缺陷、不阻擋閘門） | **不加同構的鎖**，改做合併／精簡。承接者＝**R61 主控**（非「下一輪某人」：R61 第一份任務書須含下列三項，結論回寫本列） | fixed@R61（🔴 **R74 訂正首詞**（原欄文自下方冒號後**完整保留、語意零變更**；體例比照 `DEF-101-433`／`DEF-101-556`）：`_classify()` 取狀態欄**最早出現**的關鍵字，首詞停在未結分類就會讓一筆已做出處置的列被長期計入未結存量。本列指派給 R61 的義務是「評估三項並把結論回寫本列」，而同欄下段的「R61 Architect 評估結論」已逐項回覆①②③（①②評估後不執行並轉記 `DEF-101-614`、③實測本輪新增鎖檔數＝0）⇒ 指派已履行、無殘留承接者，`routed` 首詞已無對應物。🔴 **本列承載的「禁止新增鎖檔、只准合併／刪除」政策不因本列結案而失效**：它的機械載體是 `tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `_FROZEN_GUARD_FILE_COUNT` shrink-only 棘輪，`tools/tests/test_check_hooks_liveness.py` 亦逐字指名本列為裁決來源）：routed@R61：R61 動工前**必評**三項，各附可機械查判準——①**抽共享 AST 剝除層**（ARCH-R60-09(c)）：把 `tools/tests/test_ps_engine_ssot.py` 的四支 AST helper（`_parse`／`_is_engine_which_call`／`_engine_selection_linenos`／`_function_bodies_code`）搬成 `tools/tests/_source_strip.py`，判準＝`grep -lc 'ast.parse' tools/tests/*.py` 命中檔數下降；剝除層只能純 AST（不可走「塗白 STRING token 再餵 regex」，理由見該檔 docstring）。②**同缺面四處合併**：「只剝整行註解／不剝 docstring」已踩四次（R46 `_has_ssot_guard`、DEF-101-482 `_ps1_code_lines()`、ARCH-R60-06 `_ps_engine`、`check_wrapper_thinness._normalize`），判準＝四處共用同一剝除層＋「整行註解／行尾註解／heredoc／docstring」四載體各一支 fixture。③**邊際效益量測入收輪報告**：記「新增鎖數」與「鎖抓到的生產碼缺陷 : 鎖自己的缺陷」，判準＝比值連兩輪 <1 即下一輪**禁止新增鎖、只准合併**。🔴 **round 3 訂正③（ARCH-R60R2-06／SA-R60R2-05）**：原寫法把觸發推給未來＝再拖一輪，而**該條件在 R60 已滿足**——round 1 三個 blocking 假綠全在護欄層自己身上、round 2 Architect 六筆新發現**零筆落在生產碼**、round 3 主控自己十二筆 blocking 亦全在治理文件與鎖上。故**現在即判定已觸發**：R61 開輪即進入「禁止新增鎖檔、只准合併／刪除」模式，須寫在 R61 第一份任務書首段。另「Scan-H 護欄層自檢」維度：原寫「已具名 routed 給該檔獨佔包」＝交棒給一個輪內已消滅的實體、無輪次無回執，**恰違反同輪自己新訂的硬規則③第三點（死信）**；**round 3 已就地落地**（`CrossPlatform_Scan_Dimensions.md` 標題 Scan-A~G→A~H、維度表新增 Scan-H 列、另立「為何 R60 必須加 Scan-H」實證段與 5 條必跑項），故本句由 routed 轉為 fixed。🔴 **R61 Architect 評估結論（本輪逐項回覆①②③，不再空泛「留給下輪」）**：①②**評估後判定本輪不執行，理由見下；已轉記獨立可追溯項 `DEF-101-614`（fixed，另案）**——①的四支 AST helper 是 Python 原始碼掃描（判斷 `shutil.which(...)` 呼叫節點是否為真呼叫，非文字剝除），②的四處是 bash／PowerShell **文字**剝除（剝整行 `#`／`<#…#>`），親讀四份原始碼後確認**語意不相容**：`_has_ssot_guard`（`tools/tests/test_windowsapps_guard_bash_parity.py:334`）逐行文字掃描 + 位置錨定正則，其 docstring 明文記載對 heredoc／死函式無鑑別力且「複雜度遠超本檔工具定位，留待出現真實呼叫點再評估」（R46 三審拍板，非本輪可單方推翻）；`_ps1_code_lines()`（`AISDLC_SDD/scripts/tests/test_ci_gate_version_resolution.py:241`）只剝整行、刻意不剝行尾註解（另有 `_cut_ps_inline_comment` 專治該案）；`check_wrapper_thinness._normalize()` 除整行剝除外還處理 `<#…#>` 區塊＋BOM 前提（`_read_source()` 已剝 BOM，`_normalize()` 刻意不重複處理）＋rstrip＋去空行。三者剝除語意互不相同（是否剝塊注解／是否剝行尾註解／是否剝空行），若強行合一至共用層，依 ADR-XPLAT-002 §4.2 rule 3 dominance test 須為每一份既有斷言逐一構造突變證明新機制同樣抓得到——尤其 `_has_ssot_guard` 三輪 bug-injection 調校過的位置錨定正則，貿然重寫的回歸風險遠高於它省下的行數（GLC 本身在 §4.3 已定位為「報表、不設上限」，不是需要優化的閘門指標）。**本輪改執行風險更低、且有 ADR 明文設計、直接移動被閘門追蹤指標的 Phase 1-B**（`AutoClaude/tools/install_git_hooks`／`AISDLC_SDD/scripts/install-hooks` 由 `_EXEMPT_PAIRS` 遷入 `_THINNESS_ENROLLED`＋hash 釘選，UEP 8→6、AC 42→46，符合 rule 2 對應關係），另加 Phase 1-C 最小可行切片（`check_script_parity.py --print-collapse` 印出 UEP／AC，零新檔）。③**邊際效益量測**：本輪新增鎖檔數＝**0**（`tools/tests/*.py` 仍 56 支，行數 28,118→**28,194**（+76，來自擴充既有測試檔，round 1 SA/Architect 複審訂正原「不變」誤寫），改動全落在既有的 `check_script_parity.py`／`check_wrapper_thinness.py` 兩支既有檔＋既有測試檔），檔數零新增，完全符合 R60 round 3 訂正的「R61 開輪即禁止新增鎖檔、只准合併／刪除」模式。詳見 `docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md` R61 裁決段與 `docs/06_quality/CrossPlatform_R61_Architect_Evidence.md` |
```

## §13 DEF-101-565（原文逐字）

瘦身前 2098 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-565 | 2026-07-29 | R60 round 2 Architect 複審（ARCH-R60R2-06，P3 架構級裁決）——**第二組獨立資料點** | **`DEF-101-561` 的③ 把觸發條件推給未來（「比值連兩輪 <1 即下一輪禁止新增鎖」）＝允許再評估一次＝再拖一輪，而該條件在 R60 已滿足。** 量化：`tools/tests/*.py` round 1 = 52 支／20,188 行 → round 2 = 56 支／22,524 行（**一輪 +11.6%**，而 round 2 的唯一任務是修 round 1 的 21 筆）→ round 3 主控實測 56 支（🔴 **R60 r3 訂正（`ARCH-R60R3-03`）**：原記「23,329 行」為 stale，Pkg-E 與 Architect 各自獨立實測皆得到另一個值；依 `ADR-XPLAT-002` §4.3 新規則，行數一律**不引數字**、以該節指令現查）；護欄層行數**已超過**它所護的 AutoClaude 生產碼。定性：round 2 Architect 六筆新發現**零筆落在生產碼**（三筆治理文件、一筆新鎖自己的 docstring、一筆新稽核的方言邊界、一筆趨勢本身） | P3（架構級趨勢判斷，非現存缺陷、不阻擋閘門） | 根層治理／R61 開輪條件 | fixed@R60 round 3（判定層）＋ routed@R61（執行層）：①561③ 已訂正為「**現在即判定已觸發**」，R61 開輪即進入「禁止新增鎖檔、只准合併／刪除」，須寫在 R61 第一份任務書首段；②ARCH 指出的合併標的與判準已在 561 內具名，R61 **直接執行不必再評估**；③Scan-H 第 4 條必跑項納入「同一語意的雙平台實作對數必須下降」（`check_script_parity` round 3 實測 13 對 ＋ 18 支單邊）——把標的從「再加一道驗證」轉為「減少需要驗證的平面」，護欄行數上升不算成果。🔴 **主控自我揭露（不辯解）**：round 3 我自己的修復又讓護欄層繼續增長（行數不引數字，見 `ADR-XPLAT-002` §4.3 指令現查值）；緩解措施是**零新增鎖檔**（全部擴充既有檔）＋淨效果是把表② 4 格「零機制」欄位收進既有機制 ⇒ 未受檢面淨減少。但行數確實仍在漲，ARCH 的警告第三次成立 |
```

## §14 DEF-101-726（原文逐字）

瘦身前 2694 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-726 | 2026-08-02 | R69 第三波多包並行時本包自身被 LOC 閘門打紅 | **容量事實登帳（收輪前預警）**：(a) `tools/dev_start.py` 貼著 SPECIAL 上限 **2000**，第三波曾達 **2011 行**、`special_violations` 1 筆、LOC 閘門 `rc=1`，稍後由他包壓回 1999（**餘裕 1 行**）；(b) monorepo `total` 已落入 `ADR-SD07-001` §6.3 **預警帶第 1 輪**（`total_warn_band=true`）。**實害已發生**：本波出現過「一包只加 18 行**註解**就打紅全樹 LOC 閘」（本包自身，已壓縮至 +4 行解決）⇒ 這個水位下**連寫註解都有配額**，而多包並行時沒人看得見別包吃掉多少 | P2 | 本帳本（本列）＋`AutoClaude/tools/check_loc_budget.py`；實質收斂標的見 `DEF-101-706` | fixed@R74｜🔴 R75 訂正首詞（原文逐字接於後）：open watch（登帳，**不結案**）。🔴 **本列刻意不寫死 `total`／`cap`／餘裕數字**（`DEF-101-713` 家族紀律）——真相源＝`cd AutoClaude && python tools/check_loc_budget.py --json` 現查＋`ONBOARDING.md` §7 表① live 格。憑證＝本包量測期間兩次輸出，`special_violations` 由 **1 筆轉空**、`total_warn_band` 皆 **true**。解鎖條件＝走完 §6.3 正式程序（Architect＋SD 雙簽）重校 baseline，或真把生產碼收斂到餘裕 ≥ 100 行。🔴 **禁止**直接上調 `.loc_baseline`。承接輪次：**未指派**｜🔴 **R75 複驗（類別 A）**：兩半皆達標。(a) 原記「`dev_start.py` 貼上限 2000、餘裕 1 行」——現測 `count_loc=1506`／上限 2000 ⇒ **餘裕 494 行**，且不在 `special_violations`。(b) 原記 `total_warn_band=true`——現查 **false**。解鎖條件「收斂到餘裕 ≥ 100 行」現為 **142 行**（`total=20296`／`cap=20438`），`baseline` 仍 17032 ⇒ 非靠上調 baseline。　🔴 **R77 訂正上段 (a) 半邊（原文逐字保全於前；首詞維持 `fixed`，理由見末句）**：(a) 的達標宣稱是**拿錯量測面比出來的**——`SPECIAL_FILES` 的 2000 是 **raw line** 預算，而上段引用的 1506 是 `count_loc`（排除空行與純註解），工具自己在 `SPECIAL_WARN_MARGIN` 上方就警告過兩者度量面不同。R77 實跑 `--json`：`../tools/dev_start.py` `loc=1999`／`budget=2000`／**`headroom=1`**、落在 `special_warn_band` ⇒ 真實餘裕 **1 行**。(b) 半邊複驗無誤。**為何不改回未結**：`dev_start.py` 貼線這個活體風險已有 `DEF-101-271`／`DEF-101-274` 兩筆 open 列承接，且其解鎖條件逐字就是同一個棘輪轉紅；重開本列只會讓同一件事有三個載體並淨增未結存量。**追貼線請看 271／274。** |
```

## §15 DEF-101-792（原文逐字）

瘦身前 2701 bytes。以下為整列原始 markdown：

```markdown
| DEF-101-792 | 2026-08-04 | R74 Scan-T（問「為何會累積到上百筆未結」） | **未結存量（列數）零機械上限**：bytes 有 warn／fail 線，未結列數什麼都沒有。加上未結列中僅少數真的指派了承接輪號、多數合法性靠 R68 建立的存量豁免白名單，而該棘輪自 R70 起三輪零收縮 ⇒ 死結在成形過程中**沒有任何東西會叫**。另一個同源現象：同一份工作樹上「未結存量」有三個互斥且不可重現的數字（82／107／93），因為量測法各不相同、且沒有唯一入口 | P1 | 本輪修復（建立唯一量測入口 ＋ 列數上限機械物 ＋ 收縮存量豁免棘輪） | fixed@R77（🔴 **R77 回執＋訂正首詞**（原欄文自下方破折號後**完整保留、語意零變更**）：本列 R76 改派給 R77 的解鎖條件＝「逐列開啟 archive_55 的 11 筆已結列，每列各附一條當回合可重跑的複驗指令與 rc」，本輪**已執行完畢**：11 筆逐列複驗，判準與逐列實測結果寫在 `AutoSDD_Defect_Log_archive_55.md` 標頭新增的〈R77 逐列複驗〉段（與被複驗的對象同住一檔，不另立會漂移的外部證據檔），**零筆「未修卻標已修」**。附帶量到一筆散文漂移（`DEF-101-005` 記該腳本有 9 處「或真」短路守衛、現查 15 處）——那是該檔長大，不是誤標，故不改該列狀態。R77 另把「歸檔後零複驗」這個**結構**補成常設判準，見 `DEF-101-872`）：**partial@R74**（承接輪次：**R75**）— 判準與棘輪已落地、帳本已回到 warn 線下；**未完成**＝主控未逐筆複驗 PKG-2 對 9 筆「假陽性」的逐列查證（該 agent 於本輪稍後因 session 額度上限中止），解鎖條件＝R75 開場對 archive_55 的每一列做一次獨立回查，確認無「未修卻標已修」 ｜🔴 承接輪次 **R79**（沿革：R76 首度改派、指定的那一輪未做完，R78 未處理故續改派，見 `DEF-101-878`）（R76 PKG-0 逐列查證後改派；R75 未服務本列解鎖條件，上方原文逐字保全未動）。**當回合查證**：`git grep -n archive_55` 全樹 5 命中，全為 R74 交棒書、`AutoSDD_Defect_Log_archive_INDEX.md` 的建檔紀錄與本帳本自身，**查無任何 R75 對 archive_55 逐列回查的紀錄**；R75 交棒書 §3 記的「25 筆逐筆查證」對象是**主檔**未結列，不是 archive_55。**解鎖條件（可直接執行）**＝逐列開啟 `docs/06_quality/AutoSDD_Defect_Log_archive_55.md` 的 11 筆已結列，每列各附一條當回合可重跑的複驗指令與 rc，確認無「未修卻標已修」；有出入者就地回填訂正並記錄。 |
```

---

## §16 帳本時鐘推進與 7 列承接輪次就地推移（`DEF-200-091`）

帳本「當前輪」由 `current_round()` 從**發現情境**欄現查推得。本包落首列（`DEF-200-091`）
之前，該值仍停在 **R84**，於是任何已在程式碼註解寫下 `R85` 的並行包都被
`TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound` 打紅——當回合實測 **5 個站點／3 支檔**
（`test_adr_xplat001_c1c2_lock.py`、`test_check_script_parity.py`、`test_check_wrapper_thinness.py`），
而每一包看到的都是「別人造成的紅」。這正是 `DEF-101-978` 記載的形態，其正解逐字為「開帳本列」。

首列落地後 `current_round()` 現查回 **R85**，窗口關閉。

**連帶處置**：時鐘一推進，7 列原本落在 fail-open 窗口內（承接輪次 `**R84**`＝當時的當前輪）
的列就變成硬規則② 的孤兒。R84 對這 7 列**皆未動工**（各列狀態欄自陳），故就地把承接輪次
推到 R85。**逐列位元組數不變**（`R84` → `R85` 等長），下表是推移前後的對照：

| DEF-ID | 推移前 | 推移後 |
|---|---|---|
| DEF-200-010 | 承接輪次：**R84** | 承接輪次：**R85** |
| DEF-200-012 | 承接輪次：**R84** | 承接輪次：**R85** |
| DEF-200-015 | 承接輪次：**R84** | 承接輪次：**R85** |
| DEF-200-020 | 承接輪次：**R84** | 承接輪次：**R85** |
| DEF-200-023 | 承接輪次：**R84** | 承接輪次：**R85** |
| DEF-200-042 | 承接輪次：**R84** | 承接輪次：**R85** |
| DEF-200-043 | 承接輪次：**R84** | 承接輪次：**R85** |

🔴 **誠實劃界**：這是**改寫**承接輪次欄而不是「就地追加改派附記」。選這個形態的唯一理由是
位元組——那 7 列當時 615~700 bytes，追加任何附記都會把其中 4 列推過 `ROW_MAX_BYTES` 而
當場轉紅（它們不在存量豁免清單內）。原值不因此消失：本節這張表就是它的居所。

---

## §17 `residual_todo_notes()` 的鑑別力訂正（逐筆判讀）

**病**：R68 立案文自己寫的射程是「它**狀態／分流欄**裡寫的『承接輪次：未指派』『留待下一輪』」，
而實作一路都在 `_RESIDUAL_TODO_RE.findall(line)`——掃**整列**，含「現象與證據」欄的敘事。
更嚴重的是字集含 `承接` 與 `改派`：**那是承接機制自己的詞彙**，任何一列只要在歷史上走過一次
交棒／改派，它的狀態欄就永遠留著那兩個字，**即使它後來已經被修好**。⇒ 該偵測器逐輪列印的
是「所有走過交棒的已結列」，而不是「還有待辦的已結列」。

**當回合實測（同一本帳本、同一次執行）**：

| 掃描面／字集 | 命中 |
|---|---|
| 整列 × 原字集（含 `承接`／`改派`） | 34 |
| 狀態＋分流欄、遮 code span × 原字集 | 30 |
| 狀態＋分流欄、遮 code span × **移除 `承接`／`改派`** | **13** |

被移除的 21 筆逐筆讀過，全部是敘事引述，形態三類：
① **指針**（`由 DEF-200-070① 承接`／`由 DEF-200-086 承接`——待辦在**別列**）；
② **史料**（`R81 改派，承接輪次：R82` 寫在一列後來已 `fixed` 的列上，是它被修好之前的沿革）；
③ **主題詞**（該列談的就是承接／改派機制本身，例如 `DEF-200-088`／`DEF-200-041`）。

留下的 13 筆全部**指名了一個沒有填的格子**：`未指派`（欄位空著）或
`擇機`／`留待`／`尚未`／`待辦`／`backlog`／`下一輪`／`下輪`（時點沒定）。

🔴 **牙沒有掉**：`承接輪次：未指派` 這個真待辦形態照樣命中（由 `未指派` 接住），既有雙向
注入測試（該命中的 `fixed@R70（殘餘兩項，承接輪次：未指派）` 命中／乾淨已結列不命中）
一支未改、皆綠。

🔴 **誠實劃界**：這是**提高訊噪比**，不是把偵測器關小。它仍然抓不到「用完全不同措辭寫的
待辦」（例如「這件事還沒人做」不含任何關鍵詞）——那需要語意判斷，本鎖不假裝有。
`DEF-101-867` 已為同一族啟發式判過「訊噪比約 25% ⇒ 上線即需白名單」，本次的方向正是
不新增白名單、而是把零鑑別力的字拿掉。

---

# §P9 帳本第二輪（P9 包）— 逐筆查證憑證

> 本節的義務與 §1~§15 相同：主檔那些列已瘦身成索引，**唯一還能重驗這些結案是否為真的地方就是這裡**。
> 每一筆都附「P9 這一回合真跑過的指令與 rc」。凡 P9 未親自複驗者一律逐字標明**未驗證**，不加背書。

## §P9-1 `DEF-200-081`（①②③ 全綠 → fixed@R85）

上級（P6）判讀為「①② 可結、③ 未提」。**P9 逐項複驗後判定三項全綠**，故整列結案——
這是往「比上級判讀更寬」方向的訂正，證據逐項如下。

**① `sdd-zero-trust-auditor` 未登記進 `auto_load_config`**
```
grep -n "zero-trust-auditor" AISDLC_SDD/AISDLC_SDD_v0.30/AISDLC_SDD_INIT.md
  :332  # DEF-200-081①（R85 接線）：本條之前…
  :343  - path: "agent/specialized/sdd-zero-trust-auditor-zh.yaml"   ← 真的進了載入清單
  :605  | agent/specialized/sdd-zero-trust-auditor-zh.yaml | … | Runtime / 系統級（R85 補列）|
```
⇒ 已接線，且計數表與清單表同步補列。

**② SCG 英文閘門名 SSOT 自身互斥（SCG-2/3/4/6）**
P9 自製抽取器（兩種磁碟上真實存在的形態：表格 cell 與 `SCG-n（Name）` 標題）比對兩份 SSOT，
**先跑正對照組自證管道有效**（已知磁碟上有 `RTM Completeness Gate`，抽取器確實抽到它）：
```
SCG-0 一致  Requirement Spec Gate     SCG-1 一致  Design Spec Gate
SCG-2 一致  Architecture Spec Gate    SCG-3 一致  API Contract Gate（Contract Freeze）
SCG-4 一致  PR Review Gate            SCG-5 一致  RTM Completeness Gate
SCG-6 一致  Release Gate              ⇒ 互斥數 = 0    （rc=0）
```
🔴 **一個會騙人的細節**：`SDD_GUIDE.md:33` 仍逐字寫著 `SCG-2 | Architecture Review Gate`／
`SCG-3 | Contract Freeze Gate` 等四個**舊名**——照字面 grep 會誤判「還沒修」。實查 :30-38 為
**訂正協議要求逐字保留的原文區塊**（開頭即「本表的英文閘門名原本與 SCG SSOT 互斥，四支不一致」），
是史料不是現行宣稱。⇒ 這一格只能讀「表格本體」，不能讀整檔 grep。

**③ ci-gate rc=1 的 6 筆共享 infra**
```
grep -c "tools/lib/sdd_latest.py" .github/workflows/aisdlc-sdd-ci.yml   → 4（兩處 paths 各 2 行）
.venv/bin/python -m pytest AISDLC_SDD/scripts/tests/test_hook_wiring_cwd_safety.py \
        tools/tests/test_install_windows_nightly.py -q                  → 50 passed, 5 skipped  rc=0
bash AISDLC_SDD/scripts/ci-gate.sh                                      → rc=0
   逐軌計數：AISDLC_SDD_v0.01:1478  AISDLC_SDD_v0.30:1747  scripts/tests:343
```
（5 skipped 全為 `WINDOWS-NATIVE-ONLY`，mac 上屬預期，非靜默跳過。）

## §P9-2 P9 對上級判讀的四筆駁回／訂正（實測為準）

| # | 上級判讀 | P9 實測 | 處置 |
|---|----------|---------|------|
| 1 | P3：`_notify_enabled` **約 15 個呼叫點** | `git grep -n "_notify_enabled" -- AutoClaude/` 全庫僅 **2 筆**（`playbook_runner.py:127` 賦值／`:210` 讀）；`self._notify(…)` 呼叫點實為 `:390`／`:400` **2 個** | 缺陷本體（零回歸鎖）成立，數字訂正後入 `DEF-200-098` |
| 2 | P8：**三支 probe 全無 smoke 測試** | 逐支查「有沒有**執行**它的測試」：`shell_command_corpus` 被 `test_block_destructive_git_r83.py:1090/1100/1130` **import 並執行**；`misstep_attribution` 被 `test_check_hooks_liveness.py:1641` **import**；`reset_window_distribution` 只在 `test_context_budget_guard.py:1603` 的**散文字串**裡被提到 | 「全無」為假。真正的發現更銳利：**唯一沒有執行面測試的那一支，正是今天 rc=1 的那一支** ⇒ 寫進 `DEF-200-095` |
| 3 | P8：根 `.env` **不存在** ⇒ 訴求 6f 從未執行 | `ls -la .env` → **存在**，3196 bytes（今日 09:03）。`diff .env .env.example` **rc=0**（逐字元相同）；`diff <(python tools/lib/quota_policy.py --print-env-example) .env.example` **rc=0** | **不立列**。三者位元組相同 ⇒ 13 個政策鍵確實等於出廠預設，但那是**設計如此**不是缺陷；`.env` 未被 git 追蹤（`git ls-files --error-unmatch .env` rc=1），而因與預設等值，全新 clone 行為零差異 |
| 4 | P3：無 `MINIMAX_API_KEY` **即 raise** | `main.py:110` 建 `MinimaxClient`，但 `:116-118` 有 `except MinimaxError` → `logger.error` → `return 1` | 使用者可見後果（example 跑不起來）成立，但形態是**被接住的 rc=1**、非未捕獲例外；訂正後入 `DEF-200-099` |

## §P9-3 兩則「取數管道自證」的自我修正（本包自己踩到兩次）

本包兩次拿到「命中 0」而**差點**寫成結論，都是管道壞了不是事實為零：
1. 比對 SCG 閘門名的第一版正則要求名字在**括號內**，磁碟上實為表格 cell ⇒ 七關全回空集合，
   畫面與「完全一致」無法區分。加正對照組後當場現形。
2. 比對 `.env.example` 與程式預設的第一版腳本自己解析 `quota_policy.py` 原始碼 ⇒ 13 個鍵
   全回 `code_default=None`。正解是改用該檔**自己提供的** `--print-env-example`（SSOT 出口）。
⇒ 教訓與根 `CLAUDE.md` 鐵律四同型：**「命中 0」是一個宣稱，它和任何 PASS 宣稱一樣需要憑證。**

## §P9-4 `DEF-200-053` 的實量：未結列被切成兩個結構不同的群，且「動不了」比想像中窄

P9 開工時先量了一次「哪些未結列**我這個包動得了**」，結果與直覺不同，登記於此供承接者用。

**兩群的分界是 `ROW_MAX_BYTES`(700)**，當回合實測（未結 82 列時）：

| 群 | 筆數 | 我能不能改 |
|---|---:|---|
| ≤700 bytes（不在 `OVERSIZE_ROW_GRANDFATHERED`） | **35** | ✅ 可，但改完必須仍 ≤700（否則 `OVERSIZE_ROW_CEILING` 66 當場 +1） |
| >700 bytes（在豁免清單內） | **47** | ⚠️ 見下 |

🔴 **本節最重要的一句，是一個對「動不了」的訂正**：我原本（與 `DEF-200-049` 的敘述一致）
以為那 47 列**完全**動不了。逐行讀 `oversize_row_problems()` 後發現不是——三條判準的方向並不對稱：

- `excess > OVERSIZE_ROW_EXCESS_CEILING` ⇒ **只擋變長，不擋變短**（`>` 不是 `==`）。
- `len(GRANDFATHERED) > OVERSIZE_ROW_CEILING` ⇒ 同樣只擋變多。
- `stale = GRANDFATHERED - set(over)` ⇒ **這一條才是真正的牆**：把豁免列縮到 ≤700 會讓它變成
  「過期豁免」而轉紅，修法須同時改 `defect_ledger_index.py` 三個常數＋`ledger_rotation` 史料
  ——那是**別的持有面**（鐵律七的教科書實例）。

⇒ **可行的結案動作實際上是**：把 >700 的未結列**結案並「瘦身但不瘦破 700」**（狀態欄換成
「結案字＋一句話＋指向本檔的指針」，只要落地後仍 >700 即可）。這條路今天**沒有被任何棘輪擋住**，
`excess` 下降是合法的。先前把整群 47 列讀成「碰不得」，使這條出口在 R84／R85 兩輪都沒有被用過。

**誠實劃界**：本節只證明這條路**機械上合法**，未證明那 47 列**實質上該結案**——後者要逐列查證，
P9 本輪查了其中 15 列（`DEF-101-950`／`951`／`960`／`974`／`980`／`991`／`998`／`200-010`／`020`／
`059`／`063`／`065`／`067`／`075`／`090`），**沒有一列真的已修**（逐筆理由見交棒回報），與
P1 對另外 8 列的結論同向。⇒ 未結存量高不是因為沒人去結，是因為**它們真的還沒修**。

## §P9-5 本輪結案的三列（逐列憑證）＋ 兩筆**被 P9 駁回**的結案建議

### 結案① `DEF-200-081`（①②③）→ `fixed@R85`
見 §P9-1。

### 結案② `DEF-101-991` → `fixed@R85`
本列**自訂**的解鎖條件逐字是「缺 mac 真機」（R82 改派時寫下）。R85 正在 macOS(darwin) 上 ⇒ 條件到期。
P9 當回合實跑：
```
.venv/bin/python -c "from lib import quota_meter, quota_ledger, quota_limits"   → rc=0
.venv/bin/python -m pytest tools/tests/test_quota_policy.py -q
   → 117 passed, 277 subtests passed      rc=0
```
⇒ 三支模組在該平台的行為已被真的執行過，不再是「整組行為在該平台未被觀測」。

### 結案③ `DEF-200-020` → `closed-by-decision@R85`
原列的可觀測主張是「**磁碟零站點**」（該輪只完成劃界，repo 內沒有任何 pmset 相關程式）。今日已不成立：
```
grep -c pmset tools/lib/endurance_env.py          → 11
grep -c pmset tools/tests/test_mac_endurance_r83.py →  8
.venv/bin/python -m pytest tools/tests/test_mac_endurance_r83.py -q -k MacSleepPosture
   → 8 passed, 4 subtests passed          rc=0
```
**另一半刻意不做**：由 repo 自己下喚醒憑證（`pmset repeat`）需 sudo 且會改動掌舵者機器的電源行為，
**已由掌舵者否決**（根 `CLAUDE.md` 逐字記載為「本專案刻意不碰」）。⇒ 依該檔已宣告的處置，
這是**已知邊界**不是待辦，故取 `closed-by-decision` 而非 `fixed`——寫 `fixed` 會謊稱 6e 已達成。

---

### 🔴 駁回① `DEF-101-755`（複驗 agent 判「可結案」，P9 **不採納**）
該 agent 的證據是「`TestGetPythonGeMinPowerShell` 類內已無 `skipIf(os.name=="nt")`」＋ 4 passed。
兩者 P9 都複驗為真（AST 實查：該類唯一裝飾器是 `skipUnless(_ps_any_engine(), …)`＝能力閘、
非平台閘，且本機確實跑了 4 支）。**但那只滿足解鎖條件 (a)，而 (a) 早在 R71 就已滿足。**
本列逐字寫著條件 **(b)「於 Windows CI 實跑一次，附『該支不再出現在 skip 明細』的取證」**，
而**同一個 agent 在同一份回報裡**量到：`gh run list` 最新 push **6/6 workflow failure**、
job `steps=0`／耗時 2 秒＝`DEF-101-866` 記載的帳務阻擋指紋 ⇒ (b) 今天結構上不可能滿足。
⇒ 依它自己的解鎖條件，本列**維持 open**。這正是根 `CLAUDE.md` 鐵律四那一型（宣稱先於查證）：
證據為真、結論卻越過了條件。

### 🔴 駁回② `DEF-101-377`（同上，P9 **不採納**，且該 agent 自己也要求主控裁決）
它量到「本 checkout 宣告 `eol=lf` 而工作樹 `w/crlf` ＝ 0 支」（正對照 `w/lf` 26,863，管道有效）。
數字為真，**但量錯了工作樹**：本列原文說的是**那台 Windows 開發機**的工作樹殘留，而 P9 這一輪在 mac 上。
根 `CLAUDE.md` 對「本機工作樹漂移」已判過三件事：`git status` 看不見（正規化只作用於 index）、
CI 看不見（`actions/checkout` 必定重新 smudge）⇒ **只有那台機器自己看得到**。
拿 A 機的乾淨去證 B 機乾淨，正是 `DEF-101-766`「單平台判準不可無條件外推」同型。⇒ **維持 open**。


---

## §R85-CLOSE-AGT11 — `DEF-200-092`（AGT-11）立案數字訂正與判準性質裁決

> 由 R85 收尾單人窗口寫入（帳本列已瘦身成索引，本節是它指名的逐筆證據）。

### 1. 立案數字：199／198 → **302／301**（低報約三分之一）

| 來源 | 數字 | 取數方式 |
|---|---|---|
| P6 原記 | 199 / 198 | 未留可重跑產物 |
| SD 複審 | 302 / 301 | 獨立重量 |
| **F2 複驗（採信值）** | **HEAD 302**（data 79／tasks 97／checklists 75／tools 51）；**工作樹 0 findings** | `git archive HEAD` 抽副本 → **用 lint 自己的判準**跑 → 302 hits；同一管道跑工作樹 → 0 hits ⇒ **取數管道自證成立**（是「真的沒有」不是「查不到」） |

🔴 **那個假數字住三個家**，SD 只找到兩個，第三個由 F2 補齊：
`AISDLC_SDD/scripts/agent_template_lint.py:24`、
`AISDLC_SDD/scripts/tests/test_agent_template_lint.py:156/158`、
`AISDLC_SDD/AISDLC_SDD_v0.30/agent/core/05.sd-architect-zh.yaml:222`。
三份皆已訂正，**原文逐字保留**。這是本 repo 反覆踩的「同一份知識住多個家、只有一個家被改」，
只是這次連「被改的那一個」本身也是錯的。

### 2. 判準性質：**純寫入面判準，不是恆綠裝飾品**（推翻 SD 的裁決）

四桶今日活分母：**data 1／tasks 0／checklists 0／tools 0**（SD 據此判為恆綠裝飾品）。
F2 以**拋棄式真實樹副本**做合成注入，兩個方向都跑：

| 動作 | 結果 |
|---|---|
| 注入 `ghost-<bucket>-asset.md`（四桶各一） | **四桶皆 rc=1 且命中該桶** |
| 還原 | **四桶皆 rc=0**（基準未注入亦 rc=0） |

⇒ 存量已清空不等於判準失效；它守的是「**下一個人寫出違規時當場紅**」。
該事實（活分母＝1）已誠實寫進判準 docstring，免下一輪誤以為它在守三百條。

### 3. 🔴 同輪順帶抓到的遞迴式缺陷（F2 發現，SD 與 P6 皆未見）

P6 的 `test_ghost_bare_name_in_each_dep_bucket_fails` **迴圈跑的是被測模組自己的常數**
（`atl.DEP_ASSET_BUCKETS`）⇒ 把該常數縮成 `("data",)`（刪三桶）後，該 case **單獨跑仍 passed**。
也就是說：**判準 4 要治的「分母被常數窄化」，原封不動搬到了測試自己身上。**
F2 已補 `test_dep_asset_buckets_may_not_shrink`（**不從被測模組取期望值**），突變後轉紅。
⇒ 這個形態（**測試從被測模組取期望值**）值得獨立登記為可複用判例。

### 4. `_TMPL_EXT` 逃生門（SD 判讀成立）

`test_dep_bucket_non_file_entry_is_not_a_false_red` 把 fail-open 釘成契約，
且其 docstring 宣稱「在防假紅」為假——全判準面 160 條（四桶 1／templates 42／BARE 117）
**被逃生門略過者＝0 條**，它防的是空集合；同時可被利用：同一個不存在的標的
**拿掉副檔名**就從 rc=1 變 rc=0。已依 P6 體例改寫為
`test_tmpl_ext_escape_hatch_is_registered_not_endorsed`（原意圖逐字保留、測試未刪、新增紅綠兩段斷言）。
**刻意不逕行收緊判準**：收緊屬判準變更，需自帶立案事實。
