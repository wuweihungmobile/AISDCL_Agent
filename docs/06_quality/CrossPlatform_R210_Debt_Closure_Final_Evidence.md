# CrossPlatform R210 技術債結案終輪證據檔（最後 2 筆結案 → 未結 0 ＋ 循環令 §7 總結帳）

- **輪籤**：R210（2026-10-09，macOS；主控 Fable 5.1 兼 Architect；Developer 2 包、SA／SD 獨立審查、QA 零信任複審皆 Sonnet）
- **輪型**：結案輪（`docs/04_planning/TechDebt_Paydown_Cycle_Prompt.md` §2）的終輪；依 R209 證據檔〈五〉第 1 與第 4 項，同一個 commit 內做完：帳本時鐘改源、ADR-XPLAT-013 翻 Accepted、DEF-200-207／DEF-101-887 結案、§7 總結帳。
- **起點**：`python tools/check_defect_log_crossref.py --unresolved-count` ＝ **2**（本場開場實跑：DEF-101-887、DEF-200-207；外部阻塞軌 5、結構性長債軌 7）。
- **體例**：不使用前瞻輪號的「延後／交給」句型；本檔每個數字皆本場親跑或子代理報告逐字（子代理的數字標〔他包回報〕，主控重跑過的標〔親跑〕）。帳本列內「詳 CrossPlatform_R210_Debt_Closure_Final_Evidence.md」即指本檔。

---

## 〇、一句話結論

主帳本未結列 **2 → 0**（`--unresolved-count` 本場實跑，見〈四〉），循環令 §7 終止條件達成；三個讓收斂「結構上永遠差一步」的根因同一個 commit 拆除：帳本時鐘改讀 R 系列文件檔名最大號（不再凍在 R100）、DEF-101-887 真修（nightly 樣本記樹狀態、判準剔除 dirty 樣本）、ADR-XPLAT-013 補行四方複審翻 Accepted 並退役 U9 到期輪永動源。含側軌的總債務 62（R125 收）→ 11（主 0＋外部 5＋長債 6）。

## 一、三個「收斂不了」的根因與本輪處置

| # | 根因（主控查證，非假設） | 處置 | 載體 |
|---|---|---|---|
| 1 | `current_round()` 取帳本「發現情境」欄最大輪號，而 R100 起帳本列刻意零輪號 ⇒ 時鐘凍結 109 輪；`check_handoff_carriers.py` 判準① 因此要求帳本永遠留一筆未結列當 R100／R109 舊 commit 的承接載體（R209〈三〉#1） | 時鐘改讀 `docs/06_quality/CrossPlatform_R<N>_*.md` ∪ `docs/04_planning/R<N>_HANDOFF.md` 檔名最大號（純函式 `round_from_doc_names`＋檔案系統 glob、不走 git）；硬規則②／lagging 注入式 `cur`；carriers／script_parity／SC-10 消費端同步；改前 carriers 對 3 個舊 commit 紅、改後 0 筆前瞻宣告 | 包 A（Sonnet Developer）；DEF-200-207 |
| 2 | nightly 三軌樣本不記工作樹狀態，收輪中途被排程打到的中間態樣本事後無法剔除（QA 於 R209 證偽主控的「觀察期已結束」改判） | 新增 `AutoClaude/tools/tree_state.py`；三 collector 的 record 加 `tree` 欄（起跑態經 env 傳入、寫入時再抓、不等即 changed_during_run）；`ac4_progress_check.evaluate`／`ga_window.evaluate` 算 streak 前剔除 `valid is False` 樣本並回報 excluded_dirty（缺欄位視為有效；全 dirty ⇒ not ready＋caveat）；ps1 起跑匯出 `AUTOCLAUDE_NIGHTLY_TREE_START`（由 tree_state.py --start-token 產出，與採樣端同一套 dirty 判定）、END observation progress 行之後印 AC4 excluded_dirty。QA P2-1（真實語料重現）：dirty 判定排除 nightly 自寫的 AutoClaude/.perf_baseline.toml，否則 drift／obs 兩軌在 Windows 近乎每晚被剔除 | 包 B（Sonnet Developer）＋QA P2-1 修法（主控落地）；DEF-101-887 |
| 3 | ADR-XPLAT-013 機械物 R100 先上生產、四方複審（U1～U4）從未進行；U9 靠到期輪常數自 121 具名展延至 213、真拆零次＝輪號型義務的永動源（掌舵者 2026-10-07：只由症狀驅動） | 補行四方獨立審查（SA／SD 唯讀鏡＋整合後 Architect 鏡與 QA 鏡，皆 Sonnet；主控為提案者不投票）；U7 改封閉史料、U9 四方明文接受舊尺長債並退役到期輪機制（刪常數、旗標、lookahead 雙生子、判準與五支測試，史料搬 Guard_Line_History_2.md）；守衛＝現行尺 LOC 閘門（射程如實寫入 ADR §9.5） | 包 C／D 審查、主控落地；DEF-200-207 |

**四方審查結論（ADR-XPLAT-013 §7.1 的證據）**：

| 票 | 執行者 | 結論 | 關鍵條件（落地後由 QA 核對） |
|---|---|---|---|
| U2 SA | Sonnet 唯讀鏡（包 C） | CONDITIONAL→APPROVE | C1 解 ADR §9.3 第 3 點與帳本 fixed 的矛盾；C2 守衛射程如實；C3 U8 對應訂正（E5＝DEF-200-217@R126、E2＝DEF-200-209@R116，結 207 不處理任何 E 項）；C4 check_loc_budget.py 註解一行訂正；C5 移除「☐ 未進行」「落地未完成」字樣＋具名記錄；C6 條文四輪號時鐘須記錄 |
| U3 SD | Sonnet 唯讀鏡（包 D） | CONDITIONAL→APPROVE | C1 同 commit 處理 9 處幽靈引用（鎖檔凍結字串 4、交棒書 5）且不得寫出旗標設為真的字面；C2 ADR 如實寫守衛射程並推翻 §9.3 第 3 點；C3 ADR 編輯後 r60 量測 token 鎖／crossref rc=0／無禁用字樣；C4 凍結前綴 sha 重釘＋接鏈列 |
| U1 Architect | Sonnet 唯讀鏡（整合後） | CONDITIONAL→APPROVE | C1 U6 special 改現查值（7）；C2 佔位符清零；C3 〈三〉#6 載明 SC-10／TestR71 復活；C4 ADR §6 第 7 項補「逾期紅燈的合法回應＝修憲非重登」——四條全數落地 |
| U4 QA | Sonnet 零信任複審（整合後） | CONDITIONAL→APPROVE | SA C1～C6／SD C1～C4 全數成立；P2-1 nightly 自寫檔誤判 dirty（修法見〈二〉）、P2-2 佔位符清零、P2-3 表② 回填＋最終樹全套全綠——三條皆於本輪落地；P3 15 條文字訂正全數採納、P4 9 條登記〈三〉 |

主控對審查意見的採納：全數採納（含 QA P2-1 的程式修法與 P3 十五條文字訂正）。SA／SD 對主控提案的三處修正（E5 對應、守衛射程、hook_wiring.py 看 special_violations）已反映在 ADR 文字；SA 另指出「舊尺長債不止四支檔（根層母體 14 支／1,589 行）」已寫入 §9.5 事實 (b)。

## 二、改了什麼（逐檔；`git diff --stat` 見〈四〉）

- **時鐘**：`tools/check_defect_log_crossref.py`（`_ROUND_DOC_GLOBS`／`_ROUND_DOC_NAME_RE`／`round_from_doc_names`／`current_round(repo_root)`；`orphan_backlog_problems`／`lagging_clock_notes` 注入式 `cur`；摘要文字改源；相容殼於整合時移除）、`tools/check_handoff_carriers.py`（`cur = gate.current_round()`、census 字樣、檔頭追加「時鐘改源」段、判準② 指路訊息）、`tools/check_script_parity.py`（`_current_round()` 委派、刪無人用的帳本路徑常數）、`tools/lib/ledger_staleness.py`（一句 docstring）、`tools/tests/test_check_defect_log_crossref.py`（+78：時鐘鎖 7 支、注入式時鐘 3 支、DEF-200-241 兩支改注入凍結值、carriers 類允許未結列為 0）、`tools/tests/test_adr_xplat001_c1c2_lock.py` SC-10 段（`_current_round_live`）、`docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md` §6 追加 R210 列（並訂正兩處舊時鐘散文）、`AutoClaude/tests/contract/test_ac_matrix_scaffolding.py`／`AutoClaude/tests/test_conftest_windows_native_skip_report.py` 改無引數呼叫、`docs/06_quality/CrossPlatform_Scan_Dimensions.md`／`CrossPlatform_Maturity_Criteria.md` 各一句舊時鐘散文。
- **DEF-101-887**：`AutoClaude/tools/tree_state.py`（新；`capture`／`is_invalid_sample`／`exclude_invalid`；git 失敗 ⇒ unknown 不 raise；起跑態 head 前綴比對；QA P2-1 修法：`_SELF_WRITTEN_PATHSPECS` 讓 dirty 判定排除 nightly 自寫的 `.perf_baseline.toml`，`start_token()`＋CLI `--start-token` 讓 ps1 起跑態與採樣態同一套規則——同時解掉 QA P3-14「週末未回收 baseline 時起跑態即 dirty」）、`observability_snapshot.py`／`drift_log_snapshot.py`／`ac4_nightly_collector.py`（record 加 `tree`；雙路 import 後備）、`ac4_progress_check.py`（evaluate 先剔除、報表 excluded_dirty、全 dirty caveat、CLI 人讀行）、`ga_window.py`（同上；全 dirty 不報 stale）、`run_local_nightly.ps1`（起跑態改由 `tools/tree_state.py --start-token` 產出、單一賦值；Get-Ac4Gate 讀 excluded_dirty；END observation progress 行之後另印 AC4 SAMPLE VALIDITY 一行；END observation progress 那一條未動、仍恰一處）、`AutoClaude/tests/tools/test_tree_state.py`（新，47 案）＋六支既有測試檔擴充（`test_run_local_nightly_static.py` 的 UTC 錨由字面改 regex，因清 UP017 舊債）。
- **ADR-XPLAT-013**：狀態行 Accepted；〈關係〉(b)(c) 現況；§6 註記＋第 7 項（條文四輪號時鐘登記不處置）；§7 補行結果段、U1～U10 表改寫、§7.1 具名記錄、末段；§8 表頭改「封閉史料」；§9.1／§9.3 指針、§9.5 新節（事實／裁決／守衛／射程／重開症狀／不涵蓋）；§3.6／§10 §5.4 §5.5／§11 §6.3 第 4 點各一句 R210 註；退役符號全去反引號。
- **U9 退役**：`tools/tests/test_adr_xplat001_c1c2_lock.py` −80（到期輪常數、清償旗標、lookahead 界與凍結孿生、判準函式、`TestRootToolsOldScaleDebtDueRound` 五支；凍結字串 4 處去反引號）；`docs/06_quality/CrossPlatform_Guard_Line_History_2.md` 新節保全原址註解；`docs/04_planning/R116_HANDOFF.md`（3 行）／`R122_HANDOFF.md`／`R127_HANDOFF.md` 去反引號；`tools/lib/governance_docs.py`／`AutoClaude/tools/check_loc_budget.py` 各一行註解。
- **帳本**：`AutoSDD_Defect_Log.md` DEF-200-207／DEF-101-887 兩列 fixed（整列 ≤700 bytes，原文逐字保全於 R209 證據檔附錄 B）；`AutoSDD_External_Blocked_Log.md` 5 列複查日 2026-10-09＋條件尾註（DEF-101-693 條件改「全部步驟」、DEF-200-075 配方指針改 local_ci_gate）＋〈複查記錄〉新節；`AutoSDD_Structural_Debt_Log.md` 6 列複查日＋尾註（DEF-101-398／DEF-101-960 條件改寫為可成立的真載體）、DEF-101-886 解鎖條件已成立移出本表（7→6）＋〈複查記錄〉新節。
- **棘輪與常設檔**：見〈七〉；`tools/tests/test_archive_defect_log.py` +7（未結歸 0 的合法終態）；`docs/04_planning/AutoSDD_improving_112.md`／`docs/06_quality/CrossPlatform_R145_Scan_Findings.md` 各加 guard-total:R210 行；本檔登記 `tools/lib/governance_docs.py`。

## 三、不改什麼＋理論洞清單（P4；只登記不修——R197〈守衛面准入〉：沒有暴露證據不立輪、不同輪修）

- 守衛面（`.claude/hooks/**`、`.claude/settings*.json`、指定七支 `tools/lib`、`session_resume_planner.py`）零改動；五問協定、輪帳本零改動；根 CLAUDE.md 零改動。本輪唯一新文件＝本檔（掌舵者：省去非必要文件）。
- **理論洞清單**（每條附「何時會變成症狀」）：
  1. 現行尺 LOC 閘門是路徑觸發型：純根層改動（尤其 `tools/session_resume_planner.py`、`.claude/hooks/*.py`）撐破預算時，根層 pre-push 與 root-infra-ci 都不跑 `check_loc_budget.py`，要到當晚 nightly 或下一個含 `AutoClaude/` 的 push 才紅（SD Q2 靜讀；ADR §9.5 已如實登記）。症狀＝一次「純根層 push 撐破 [ROOT-TOOLS] 預算、事後才被別的 push 或 nightly 發現」的真實事件。
  2. 三軌 collector 的同日去重是 latest-wins：同一 UTC 日後跑的 dirty 樣本會覆寫先前的乾淨樣本（覆寫後該日被判準剔除、streak 出現空洞而非假綠）。症狀＝某日 nightly 乾淨樣本後又被手動跑的 dirty 樣本覆寫且 streak 因此延後達標。
  3. ADR-XPLAT-012 條文五 §6 的 Phase 2 五輪視窗（`_PHASE2_REVIEW_LOG`，自 R129 起十三列空轉重登）與 `_REPIN_NET_CAP_DUE_ROUND` 仍是輪號型到期義務；兩者的時鐘＝棘輪稽核紀錄最大輪號，沒有新的 R 輪就不會到期（休眠而非永動）。症狀＝下一個重釘輪 `[時效逾期]`／`[到期未下修]` 轉紅。
  4. `tools/ruff.toml` 的 `tests/*.py` E501 豁免寫有到期日 2026-11-02，由 `test_subprocess_encoding_hygiene.py` 以當日日期比對——**已知日期、必然發生**（該日起根層全套紅），是 repo 內唯一會在無人動工時自己轉紅的日曆義務，與掌舵者 2026-10-07 原則同型（SA 附帶發現 A1、QA P4-3）。承接＝〈六〉呈報單第 2 項（掌舵者裁決刪日期不續期、改症狀驅動）。
  5. DEF-101-887 的 Windows 半邊：首筆真樣本只會由 Windows nightly 產出；ps1 改動只以 pwsh 7 ParseFile、靜態鎖與 mac 上的 pwsh 7 真跑鏈路驗過，PS 5.1 未驗。症狀＝Windows nightly 末筆 `.ac4_history.jsonl` 缺 `tree` 欄或 G0 區塊無 excluded_dirty 行。
  6. ADR-XPLAT-002 §6 覆蓋表 R101～R209 期間零列（時鐘凍結使 SC-10 零訊號）；本輪只補 R210 列、不回頭補史料。症狀＝讀者依該表反推平台覆蓋得出與開發史相反的結論（DEF-101-756 同型）。**時鐘改源後 SC-10（§6 須有當前輪那一列且不含草稿字樣）與 TestR71（程式碼輪號標籤不得超前）自下一個 R 輪起恢復約束**：該輪第一份 R 系列證據檔／交棒書建立時，同 commit 須補 §6 一列——這是還原 R74 原設計、事件驅動（建立輪次文件才觸發）而非日曆義務；是否保留由掌舵者具名裁決（Architect 鏡建議保留）。
  7. `AutoClaude/tests` 內的自陳站點不在 ADR-013 §8 母體；U7 普查只涵蓋非測試 .py。症狀＝同 U7 重開條件。
  8. 外部阻塞軌 DEF-200-075 的「阻塞源」在 mac 上沒有擋任何事（剩餘工作＝97 筆 untagged＋6 筆 env-disabled 補標籤，屬內部債）；本輪只改複查日與配方指針、不改軌別（改軌需掌舵者具名裁決，見〈六〉呈報單）。
  9. R129～R176 的 R 號是護欄重釘輪計數而非帳本結案輪，附錄 A 逐輪表在該段的 commit 對輪靠 repin 日誌列與內文標記（包 E [M6]），個別 follow-up commit 歸屬可能 ±1；不影響任何未結數（每個 Δ 皆為兩個真實 commit 之差、全程恆等式成立）。
  10. nightly 其他會回寫 tracked 檔的 stage（QA P4-4）：`refresh_nightly_anchor.py --write` 寫 ONBOARDING.md 在 Windows 排於 Cleanup 之前、mac 為最末 stage，皆在三個 collector 之後，現況不影響樣本；若日後 stage 順序調動使它排到 collector 之前，須加進 tree_state 的自寫檔排除清單。症狀＝obs／drift 樣本的 tree.dirty_entries 恆為 1 且 porcelain 只剩 ONBOARDING.md。
  11. obs／drift 兩軌的 excluded_dirty 不印進 nightly log（ps1 只印 AC4 那一條；QA P3-15）：ga_check 的 `--json` 已含該欄，ps1 的 Get-ObsGaPass／Get-DriftGaPass 未讀。症狀＝obs／drift 被剔除卻只看到 staleness 類訊息；處置＝Windows 機上補兩行 Log（本輪 mac 不改無法驗的 ps1 區塊）。

## 四、驗證（本場親跑；rc 與關鍵輸出行逐字；沒跑的標「未驗證」）

| 項目 | 指令（repo 根；根層 unittest 於 tools/tests 下載入） | rc／關鍵輸出（逐字） |
|---|---|---|
| 未結存量 | `python tools/check_defect_log_crossref.py --unresolved-count` | rc=0；「未結列數＝0／全部 207 列｜warn=86 fail=98」「外部阻塞軌…5 筆」「結構性長債軌…6 筆」 |
| 帳本跨文件一致 | `python tools/check_defect_log_crossref.py` | rc=0；「✅ 缺陷帳本跨文件狀態一致：帳本 207 筆有效狀態紀錄…當前輪 R210 係由 R 系列證據檔／交棒書檔名最大號現查推得」；逾期複查 warn 由 10 條降為 0 |
| 交接載體 | `python tools/check_handoff_carriers.py --census` ／ 無旗標 | rc=0；「當前輪＝R210（R 系列證據檔／交棒書檔名最大號現查；未結承接輪號＝空）」「前瞻延後行 0 筆」「commit 訊息＝739 則；其中含前瞻延後宣告 0 筆」；「✅ 每一筆前瞻延後宣稱都有帳本承接載體」（改前：3 個舊 commit 紅） |
| 歸檔門檻／腳本對等 | `python tools/check_archive_required.py`；`python tools/check_script_parity.py` | 皆 rc=0（「退場輪號皆不超前當前輪 R210」） |
| 護欄棘輪 | `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` | rc=0；「# 淨額 114811→114811 (+0)」「# 逐檔漂移 0 支」；sha bcdb57dd180d… 與檔內釘值相同 |
| LOC 閘門 | `python AutoClaude/tools/check_loc_budget.py --json` | rc=0；五類 violations 皆空；cap_basis_pinned true；policy_version＝baseline_policy_version；warn band tier 0／special 7／root_tools 4（Architect 鏡與 QA 各自重量相同） |
| ruff | `ruff check`（自動發現設定）根層碰過的 10 檔、AutoClaude 碰過的 17 檔 | 皆「All checks passed!」（含 skip_tag_policy.py 註解行） |
| 根層全套（最終樹） | `AUTOSDD_PARALLEL_TESTS=1 python tools/run_root_unittests.py` | **ROOT_RC=0**；「✅ unittest 數量下限釘選通過：發現 5207 個測試（下限 5101）」；「[skip census] tools/tests@darwin 共 47 支…欠債型 0 支」「[M6 id 集合]…✅」「✅ 真實 TEMP 圍籬…零變動」。前兩次：靜態掃描早退（樹檔數下限 222→223 重釘）、唯一紅＝本檔引用已撤回的缺陷編號（已改句） |
| AutoClaude 全套（乾淨 venv、表② 回填載具） | `python tools/lib/clean_venv_carrier.py` | CVC_RC=0；「[autoclaude-pytest-snapshot:]（macOS 欄）→ {'passed': 4764, 'skipped': 222}」「[cigate-v001-snapshot:] 1475」「[cigate-v030-snapshot:] 1979」「[cigate-scripts-snapshot:] 362」；暫存 venv 已刪 |
| 表①／表② | `python tools/sync_onboarding_baselines.py --check`／`--check-snapshot` | 皆 rc=0；「✅ §7 表② 指紋相符 macOS 欄（…autoclaude=7ee75a0db226）」；Windows 欄只能在 Windows 機量（〈八〉） |
| AutoClaude 針對模組 | `python -m pytest -o addopts="" tests/tools -q`；兩支改無引數呼叫的測試檔 | 「1017 passed, 52 skipped」；「55 passed」；`tests/tools/test_tree_state.py` 47 passed |
| ps1 | `pwsh` ParseFile；`file` | parse_errors=0；「UTF-8 (with BOM) text … with CRLF line terminators」；bare LF 0 |
| 四方審查 | 包 C／D／F／G 報告（scratchpad，摘要見〈一〉） | SA CONDITIONAL→APPROVE、SD CONDITIONAL→APPROVE、Architect 鏡 CONDITIONAL→APPROVE、QA CONDITIONAL→APPROVE；全部條件於本 commit 落地並由主控親跑上列閘門核對 |

未驗證（只能在該環境驗）：Windows nightly 首筆 `tree` 樣本與 `AC4 SAMPLE VALIDITY` 行、PS 5.1 實跑、Windows 機表② 欄、三支 workflow 的雲端實跑（push 後對帳，run id 於下方補記）。

雲端對帳（commit 824330d0 push 後現查 `gh run list --branch main --commit <sha>` 與 `gh run view <id> --json jobs`）：四支 run 全部 `completed success`——AutoClaude CI 37942783417（Tests + LOC Budget／CLAUDE.md Budget + Snapshot Freshness／PG Contract Tests／Equivalence Snapshot 皆 success；nightly 類與 workflow_dispatch 類 job 依 push 規則 skipped）、root-infra-ci 37942783512（root infra guard success）、macos-compat-ci 37942783446（macOS smoke success；nightly-full 與失敗提醒 job 依 push 規則 skipped）、windows-compat-ci 37942783398（Windows smoke success；同上 skipped）。shellcheck-ci／aisdlc-sdd-ci 依 paths 未觸發（缺席＝未驗證）。本回填 commit 自身的雲端 run 由下一個開場視窗對帳。

## 五、循環令 §7 總結帳（起點 49@R125 → 終點 0；逐輪淨減歸因）

**口徑**：主帳本 `--unresolved-count`（狀態欄首詞 ∈ open／routed／None）；量法＝對每一輪收輪 commit 的帳本文字以同一支工具現算（包 E 以 13 個歷史 commit 各自的舊工具＋舊帳本交叉驗證，與復刻值全等；262 個 commit 的序列在本輪改工具後重跑一致）。起點 49 核對無差異（`a463357a` 與循環令 v2 改版 `ba02501a` 皆 49）；註腳：R124 刻意把分母 40→57（拆 17 列），起點 49 內有 11 筆是拆列產物。

**(a) 階段小計**（F＝fixed、C＝closed-by-decision、W＝wontfix）〔他包回報：包 E〕

| 階段 | 列數 | 未結 | 淨 | 結案 | 移軌 | 撤回 | 新立 | 新立即結 | 說明 |
|---|---:|---|---:|---|---:|---:|---:|---:|---|
| R126～R128 落地輪 | 3 | 49→31 | −18 | 20（F15／C2／W3） | 0 | 0 | 2 | 0 | 循環令起點後的三個落地輪；R126 一輪 13 筆 |
| R129～R176 工程系列 | 44 | 31→38 | +7 | 16（F16） | 0 | 2 | 25 | 112 | 喚醒鏈、多核測試、單一 .venv、多 CPU、dev_start、console 洩漏、單一 hook 載具；R 號＝重釘輪；新立 25＞結案 16 |
| R177～R198 五問系列 | 22 | 38→29 | −9 | 33（F25／C8） | 0 | 0 | 24 | 66 | 五問四方覆核（Windows／Mac 輪替）＋②′ 修憲；24 筆新立抵銷近半結案 |
| R199～R207 收斂／再評 | 9 | 29→29 | 0 | 5（F3／C2） | 0 | 0 | 5 | 11 | 不是閒置：R202→R207 每輪結 1 新立 1 的接力鏈 490→499→501→503→504→506，R208 結 506 後不再新立 |
| R208～R209 收尾 | 2 | 29→2 | −27 | 25（F7／C18） | 2 | 0 | 0 | 0 | R208 nightly 錨改機械回填；R209 結案輪一次 −26 |
| R126～R209 合計 | 80 | 49→2 | −47 | 99（F66／C30／W3） | 2 | 2 | 56 | 189 | 恆等式 49−99−2−2+56＝2 |
| R210 本輪 | 1 | 2→0 | −2 | 2（F2） | 0 | 0 | 0 | 0 | DEF-101-887／DEF-200-207 真修結案（本檔） |

**(b) 總帳**：R126→R210 結案 101（fixed 68／closed-by-decision 30／wontfix 3）＋移外部軌 2（DEF-101-856／DEF-200-253，換帳不是解決）＋撤回 2（DEF-200-273 於 eb5d7afc 移除主帳本落款；另一筆於 628f6e99 整列撤回、帳本家族已無該號）＝出 105；新立（進入未結）56 事件＝55 個 ID；出 105＝起點 49＋新立 56 ✓。另有 189 筆「新立即結」從未進過未結集合。**(c) Δ 為正的輪** 14 個合計 +28（R148／R191 各 +4 最大）；Δ<0 共 25 輪合計 −75。**(d) 淨減最多**：R209 −26、R126 −13、R128／R190 並列 −3。**(e) 零變動最長**：R133～R141 與 R199～R207 各 9 個 R 號；未結集合零進出最長＝R159～R165（7 個 R 號；期間另有 15 筆新立即結，不進未結集合）。**(f) 起點 cohort 去向**：49 筆中 47 筆於 R209（含）以前處置（R126 13／R127 3／R128 3／R151 1／R189 2／R190 3／R196 1／R198 3／R209 18），餘 2 筆於本輪；起點後新立的 55 個 ID 全數處置、無一殘存。**(g) 含側軌總債務**：R125 收 62（49＋6＋7）→ R209 收 14（2＋5＋7）→ 本輪 11（0＋5＋6）。**(h) 口徑誠實劃界**：「終點 0」只指主帳本；closed-by-decision 30＋wontfix 3＋移軌 2＋撤回 2＝37 筆消失不是靠 fixed；帳本輪替（R179 主檔 333→111 列搬 archive）不影響未結數。

**(i) 為什麼之前一直收斂不了（結構性歸因，供 Q2 決策）**：①發現快於結案——R129～R198 兩個系列新立 49 筆、即結 178 筆，每輪派人找問題就每輪長出新債（R207 退役時間型觸發、R209 改「結案輪不挖新問題」後才止血）；②分母側被三個結構性根因鎖住最後幾筆（本檔〈一〉），它們不是「努力不夠」而是「規則互鎖」：時鐘凍結逼帳本永遠留一筆、到期輪常數每輪展延、ADR 停在 Proposed；③結案吞吐天生是 1（跨檔參照稅使收尾只能單人窗口做），而發現可平行化。

## 六、兩條側軌逐筆現況與最近複查日（2026-10-09；複查證據與指令見包 E 報告，主控親跑守衛函式驗證 fails／warns 皆空）

| DEF-ID | 軌 | 今日判定 | 本輪動作 |
|---|---|---|---|
| DEF-101-693 | 外部（Windows 實機） | 仍成立（mac 不可查；先行測試仍在） | 複查日；條件「22 步」改「全部步驟（現查 27 步）」 |
| DEF-200-075 | 外部（其他-macOS實機） | 部分（量測已做、欠債 103 支未清） | 複查日；配方指針改 local_ci_gate；〈複查記錄〉新節；軌別呈報（下） |
| DEF-200-313 | 外部（Windows 實機） | 仍成立（mac 不可查） | 複查日 |
| DEF-200-253 | 外部（Windows 實機） | 仍成立（今日剛登記） | 備註現鍵含 +pgext |
| DEF-101-856 | 外部（Windows 實機） | 仍成立（今日剛登記） | 備註引用物仍在 |
| DEF-101-018 | 長債（ruff 存量） | 仍成立（根 3566／AutoClaude 681，縮小非 0） | 複查日 |
| DEF-101-398 | 長債（dev_start 拆分） | 部分（loc 僅差 1 行、兩模組不存在） | 複查日；條件前半改「低於 1951」 |
| DEF-101-701 | 長債（run_root_unittests 行數） | 部分（headroom 0） | 複查日 |
| DEF-101-702 | 長債（R68 稽核波） | 仍成立（open 23＋partial 5） | 複查日 |
| DEF-101-886 | 長債（工作樹序列化） | **已解鎖**（2026-09-01 即成立：CLAUDE.md 檢查表＋規則鎖皆在） | 移出本表（7→6）＋〈複查記錄〉新節；主列歷史狀態不改 |
| DEF-101-960 | 長債（skip 剖面） | 仍成立（原條件指向錯表、結構上不可能成立） | 複查日；條件改指 `_UNMEASURED_RUNNER_PROFILES` 的 2 鍵 |
| DEF-101-980 | 長債（ADR-XPLAT-005） | 仍成立（檔頭仍 Proposed，自 08-16 未動） | 複查日 |

**呈報單（需掌舵者拍板，本輪不代決）**：

1. DEF-200-075 的軌別——①留在外部阻塞軌（現狀）；②改判結構性長債軌（需具名裁決；長債軌現 6 列、上限 7，可容納）；③以 closed-by-decision 結案（天花板只准降、nightly 每日量測）。主控建議②（它是內部債、不是外部阻塞）。
2. `tools/ruff.toml` 的 tests/*.py E501 豁免到期日 2026-11-02（〈三〉#4）：①刪到期日、改為「存量只准降」的棘輪（`_E501_DEBT_CEILING` 已存在，症狀驅動）；②續期一次（最多 120 天，問題不消失）。主控建議①。

## 七、護欄層重釘（`test_adr_xplat001_c1c2_lock.py`）

- 淨額 114790→114811（+21）＝主表淨額，全額歸回歸鎖軌（DEF-200-207／DEF-101-887 結案回歸鎖）；主軌 0 ≤ 0（款(11) 連升維持歸零）。`--print-guard-lines` 末態「淨額 114811→114811 (+0)」「逐檔漂移 0 支」。
- 構成：`test_check_defect_log_crossref.py` +78；`test_archive_defect_log.py` +7；本檔 −80（U9 退役）＋自身漂移（重釘列、回歸鎖軌同輪列、到期兌現列、接鏈列）。
- 到期義務：`_REPIN_NET_CAP_DUE_ROUND` 210 到期——兌現 `(210, 517)` 並重新武裝 212／516；`_PHASE2_REVIEW_LOG` 到期 213 未到不動；U9 到期輪常數退役（〈一〉#3）。
- 凍結前綴：`_REPIN_LOG_FROZEN_PREFIX_LEN` 329→330、`_REPIN_LOG_HISTORY_SHA256` 重釘為 bcdb57dd…（凍結字串 4 處去反引號＋新列）、`_FROZEN_PREFIX_REWRITE_LEDGER` 追加接鏈列（715cab768f05 → bcdb57dd180d，DEF-200-207）。
- 兩份常設檔的 `<!-- guard-total:R210 -->` 行：`docs/04_planning/AutoSDD_improving_112.md`、`docs/06_quality/CrossPlatform_R145_Scan_Findings.md`。

## 八、只在 Windows 機做的事（事實驅動，無輪號義務）

1. `git pull` → `gh auth status` → `& "$(git rev-parse --show-toplevel)\.venv\Scripts\python.exe" tools\lib\clean_venv_carrier.py` 回填 ONBOARDING §7 表② Windows 欄 → `python tools\sync_onboarding_baselines.py --check-snapshot` 看到「相符」→ 一併 commit。
2. 下一次 Windows nightly 後現查 `AutoClaude/.ac4_history.jsonl` 末筆含 `tree` 欄（`valid` 應為 true——若為 false 且 porcelain 只剩 nightly 自寫檔，即排除清單有漏）、`logs/nightly_latest.log` 在 END observation progress 行之後印出 `AC4 SAMPLE VALIDITY: excluded_dirty=`；缺任一即重開 DEF-101-887。順手補 Get-ObsGaPass／Get-DriftGaPass 的 excluded_dirty Log 兩行（〈三〉#11）。
3. 順手複查外部阻塞軌四列 Windows 實機項（DEF-101-693／DEF-200-313／DEF-200-253／DEF-101-856）能否解鎖。

## 附錄 A：逐輪未結列數序列（R125 → R209 收輪 commit；包 E 以 `git show <sha>:docs/06_quality/AutoSDD_Defect_Log.md` 逐一現算，量法見〈五〉口徑）

| 輪 | 收輪 commit | 日期 | 未結列數 | Δ | 毛流量(−出 +入) | 新立即結 | 外/長 | 一句話歸因 |
|---|---|---|---:|---:|---|---:|---|---|
| R125 | a463357a | 2026-09-04 | **49**（起點） | −8（R124 收 57） | −8（94b06f50） | — | 6/7 | 純結案輪：8 筆真結案（57→49）＝循環令 v2 起點；v2 改版 commit ba02501a 當下亦為 49 |
| R126 | 3dbdb9f7 | 2026-09-04 | 36 | −13 | −13 | — | 6/7 | 落地輪：13 筆結案（11 fixed／2 closed-by-decision）＋四方設計複審 |
| R127 | 2f0c3b81 | 2026-09-04 | 34 | −2 | −3 +1 | — | 6/7 | 落地輪：結 206／133／260，新立 264 |
| R128 | 7b0de7d7 | 2026-09-05 | 31 | −3 | −4 +1 | — | 6/7 | 落地輪：呈報單七項落款，結 255／256／259（wontfix）＋264，新立 265 |
| R129 | b1ef81f5 | 2026-09-06 | 31 | 0 | — | 6 | 6/7 | 無人喚醒鏈零浪費重設計（ADR-XPLAT-015）；6 筆新立即結，未結不動 |
| R130 | 297ecc0a | 2026-09-06 | 31 | 0 | — | 1 | 6/7 | 喚醒 tick 標無人＋followup 接線測試；新立即結 1 筆 |
| R131 | 50245adb | 2026-09-07 | 31 | 0 | −1 +1 | — | 6/7 | 喚醒鏈四方審計破洞修復；273 登記後撤回主帳本落款，淨 0 |
| R132 | a3360f70 | 2026-09-08 | 33 | +2 | +2 | — | 6/7 | 喚醒鏈對抗式稽核收尾；273 重登＋新立 274（多核 runner） |
| R133／R134 | dcf14019 | 2026-09-08 | 33 | 0 | — | — | 6/7 | 根層 tools/tests opt-in 平行執行模式（DEF-200-274 前期）；未結不動 |
| R135／R136／R137 | a2186316 | 2026-09-09 | 33 | 0 | −1 +1 | 1 | 6/7 | DEF-200-274 第五輪（TOCTOU 全庫排查）：結 273，新立 275，淨 0 |
| R138／R139 | 001101ee | 2026-09-09 | 33 | 0 | — | — | 6/7 | DEF-200-274 第六輪（頭重腳輕根因）；未結不動 |
| R140 | b59a7d99 | 2026-09-09 | 33 | 0 | — | — | 6/7 | DEF-200-274 第七輪（負載不均偵測）；未結不動 |
| R141 | f61cb455 | 2026-09-10 | 33 | 0 | — | — | 6/7 | DEF-200-274 第八輪（CI 診斷可視化）；未結不動 |
| R142 | f334ea15 | 2026-09-10 | 32 | −1 | −1 | 1 | 6/7 | DEF-200-275 三輪修復＋277 CI 修復：結 275 |
| R143 | ea6113d5 | 2026-09-11 | 32 | 0 | — | 1 | 6/7 | DEF-200-275 第四輪＋278（hook 改讀真實 usage）；新立即結 |
| R144 | fda29038 | 2026-09-11 | 34 | +2 | +2 | 2 | 6/7 | DEF-200-275 第五輪＋281／282：新立 279／280 |
| R145 | e90ee11c | 2026-09-12 | 32 | −2 | −2 | 1 | 6/7 | DEF-200-275 第六輪：結 279／280 |
| R146 | ce12e46b | 2026-09-12 | 33 | +1 | +1 | 4 | 6/7 | DEF-200-275 第七輪＋287／288：新立 286 |
| R147 | e86f6868 | 2026-09-13 | 32 | −1 | −1 | — | 6/7 | DEF-200-274 第九輪（預設自動多核）：結 274 |
| R148 | 54ae6e9f | 2026-09-13 | 36 | +4 | +4 | 2 | 6/7 | DEF-200-274 第十輪：新立 289／290／291／292 |
| R149 | c2ad02cd | 2026-09-14 | 36 | 0 | — | 2 | 6/7 | pre-push `--dist loadgroup` 改問 SSOT 等；新立即結 |
| R150 | 5e25ec48 | 2026-09-14 | 36 | 0 | — | 4 | 6/7 | 單一 .venv 收斂 297～300；新立即結 |
| R151 | ddaf6301 | 2026-09-15 | 34 | −2 | −2 | 6 | 6/7 | 單一 .venv 收斂＋nightly 12 連紅解除：結 183／291 |
| R152 | 7b102176 | 2026-09-17 | 37 | +3 | +3 | 8 | 4/7 | 單一 .venv 四方審查殘餘＋mac launchd nightly：新立 311／315／316；外部軌 6→4 |
| R153 | 07909c4d | 2026-09-18 | 35 | −2 | −3 +1 | 2 | 4/7 | 多 CPU 四方審查收尾：結 289／290／292，新立 318 |
| R154 | 4f74e4fb | 2026-09-18 | 35 | 0 | — | 1 | 4/7 | 多 CPU 複審收尾（320 新立即結；319 已於 R153 尾 commit 先落） |
| R155 | 19f3e75b | 2026-09-19 | 34 | −1 | −1 | 3 | 4/7 | 單一 .venv 最後一哩：結 315 |
| R156 | 5134ee87 | 2026-09-19 | 34 | 0 | — | 1 | 4/7 | 整合閘門 core 補 `--dist loadgroup` 判準；新立即結 |
| R157 | 628f6e99 | 2026-09-19 | 33 | −1 | −2 +1 | 7 | 4/7 | 多 CPU 第十四輪收尾：結 318；補正 2／3 新立 332 後撤回 |
| R158 | 1d406c8c | 2026-09-20 | 36 | +3 | +3 | 9 | 4/7 | 新視窗「被擋」與 status line 四問：新立 340／341／342 |
| R159 | 2206a3a0 | 2026-09-20 | 36 | 0 | — | 4 | 4/7 | 多 CPU 第十五輪 345～348；新立即結 |
| R160 | 6fe58e24 | 2026-09-21 | 36 | 0 | — | 1 | 4/7 | 多 CPU 第十六輪；新立即結 |
| R161 | ad88dbd7 | 2026-09-21 | 36 | 0 | — | 1 | 4/7 | 多 CPU 第十七輪；新立即結 |
| R162 | 5b69f284 | 2026-09-22 | 36 | 0 | — | 3 | 4/7 | 多 CPU 第十八輪；新立即結 |
| R163 | f3865103 | 2026-09-22 | 36 | 0 | — | 4 | 3/7 | 多 CPU 第十九輪；DEF-101-703 解鎖移出外部軌（4→3） |
| R164 | f93450ea | 2026-09-22 | 36 | 0 | — | 2 | 3/7 | DEF-200-358 dev_start [1/7] git 平台判定；新立即結 |
| R165 | 8ed4a1c2 | 2026-09-22 | 36 | 0 | — | — | 3/7 | DEF-200-359 WindowsSmoke 逃生口；新立即結 |
| R166 | f4020022 | 2026-09-22 | 37 | +1 | +1 | 1 | 3/7 | DEF-200-360 前沿 rev 判定：新立 361 |
| R167 | c3ee62be | 2026-09-23 | 37 | 0 | — | 1 | 3/7 | DEF-200-362 跨機切換摘要；新立即結 |
| R168 | ff91997e | 2026-09-23 | 37 | 0 | — | 5 | 3/7 | 多 CPU 第二十輪（Windows 真機覆核）363～367；新立即結 |
| R169 | f3f3425a | 2026-09-23 | 37 | 0 | — | 5 | 3/7 | 多 CPU 第二十一輪 368～372；新立即結 |
| R170 | 50042dc7 | 2026-09-24 | 39 | +2 | +2 | 6 | 3/7 | 多 CPU 第二十二輪 373～380：新立 379／380 |
| R171 | ccd4227e | 2026-09-25 | 39 | 0 | −2 +2 | 6 | 3/7 | 多 CPU 收斂後重驗：結 379／380，新立 381／386，淨 0 |
| R172 | ee4bdd44 | 2026-09-25 | 39 | 0 | — | 5 | 3/7 | Windows console 洩漏 389～393；新立即結 |
| R173 | a7ec2772 | 2026-09-26 | 39 | 0 | −1 +1 | 3 | 3/7 | 多 CPU 複驗與前輪遺留：結 386，新立 395，淨 0 |
| R174 | e4bf51af | 2026-09-26 | 39 | 0 | — | 1 | 3/7 | 多 CPU 收斂後複驗 II；新立即結 |
| R175 | f717181b | 2026-09-26 | 39 | 0 | — | 2 | 3/7 | 雲端假紅根治 399／400；新立即結 |
| R176 | cdae9028 | 2026-09-27 | 38 | −1 | −1 | — | 3/7 | DEF-200-316 方案 B 單一 hook 載具落地：結 316 |
| R177 | 1118bc30 | 2026-09-27 | 37 | −1 | −1 | 1 | 3/7 | 掌舵者五問四方審查：結 340；401 新立即結 |
| R178 | ee0d455e | 2026-09-28 | 38 | +1 | +1 | 4 | 3/7 | Windows 切換啟動輪 402～405：新立 403 |
| R179 | 6369db47 | 2026-09-28 | 38 | 0 | −1 +1 | 3 | 3/7 | 五問 Windows 真機覆核：結 342，新立 410，淨 0 |
| R180 | 006f1ae8 | 2026-09-28 | 37 | −1 | −1 | 1 | 3/7 | 五問覆核：結 410；411 新立即結 |
| R181 | 198f09c3 | 2026-09-28 | 36 | −1 | −1 | 1 | 3/7 | 五問覆核：341 重開結案；412 新立即結 |
| R182 | d8b05dba | 2026-09-28 | 37 | +1 | +1 | 6 | 3/7 | 五問覆核＋閃黑框歸因 417：新立 418 |
| R183 | 90b6123d | 2026-09-29 | 37 | 0 | — | 3 | 3/7 | 五問覆核 420～422；新立即結 |
| R184 | 9ccb5ace | 2026-09-29 | 39 | +2 | +2 | 4 | 3/7 | 五問覆核：新立 427／428 |
| R185 | 38f4cbde | 2026-09-30 | 39 | 0 | −1 +1 | 5 | 3/7 | 五問覆核：結 428，新立 434，淨 0 |
| R186 | 0a945f30 | 2026-10-01 | 37 | −2 | −2 | 10 | 3/7 | 五問覆核：結 427／434（closed-by-decision） |
| R187 | 1fbbc64b | 2026-10-01 | 38 | +1 | +1 | 3 | 3/7 | 五問 Mac 驗證輪：新立 447 |
| R188 | 9fb0a604 | 2026-10-01 | 37 | −1 | −1 | 2 | 3/7 | 五問 Mac 再驗證輪：結 447 |
| R189 | 7e1ac27c | 2026-10-02 | 36 | −1 | −3 +2 | 4 | 3/7 | 五問家族級結構鎖審計：結 086／231／286，新立 455／456 |
| R190 | 933f0b16 | 2026-10-02 | 33 | −3 | −5 +2 | 1 | 3/7 | 五問修復輪：結 197／198／203／455／456，新立 458／459 |
| R191 | d337e3f6 | 2026-10-03 | 37 | +4 | +4 | 3 | 3/7 | 五問驗證輪：新立 463～466 |
| R192 | a0514681 | 2026-10-03 | 38 | +1 | −1 +2 | 4 | 3/7 | 判準②′ 生效第 1 輪：結 464，新立 471／472 |
| R193 | 7efc4c06 | 2026-10-03 | 38 | 0 | −4 +4 | 4 | 3/7 | 五問首次 Windows 11 執行輪：結 463／466／471／472，新立 476～479，淨 0 |
| R194 | 128f8dcc | 2026-10-03 | 36 | −2 | −2 | 2 | 3/7 | 五問覆核：結 476／477 |
| R195 | 1a9564e8 | 2026-10-04 | 35 | −1 | −1 | 1 | 3/7 | 五問覆核：結 478 |
| R196 | 28514cc1 | 2026-10-04 | 33 | −2 | −4 +2 | 1 | 3/7 | 五問覆核：結 246／459／465／479，新立 485／486 |
| R197 | b5b093b5 | 2026-10-05 | 31 | −2 | −2 | — | 3/7 | ②′ 協定 v2 修憲：485／486 以 closed-by-decision 結 |
| R198 | f106d364 | 2026-10-05 | 29 | −2 | −3 +1 | 3 | 3/7 | 症狀閘首評：結 193／199／242（closed-by-decision），新立 490 |
| R199 | 865f061c | 2026-10-05 | 29 | 0 | — | 3 | 3/7 | 症狀閘第二次評估；未結不動 |
| R200 | d2b16c6d | 2026-10-05 | 29 | 0 | — | 3 | 3/7 | 症狀閘第三次評估；未結不動 |
| R201 | 18adf468 | 2026-10-05 | 29 | 0 | — | 2 | 3/7 | Mac 他機輪；未結不動 |
| R202 | 234eebe0 | 2026-10-06 | 29 | 0 | −1 +1 | 1 | 3/7 | Windows 評估機第 1 次達標：結 490，新立 499（接力） |
| R203 | 835ac5b9 | 2026-10-06 | 29 | 0 | −1 +1 | 1 | 3/7 | 第 2 次達標＝宣告收斂：結 499，新立 501（接力） |
| R204 | 2d5c06b8 | 2026-10-06 | 29 | 0 | −1 +1 | — | 3/7 | Stop hook 否定句修法：結 501，新立 503（接力） |
| R205 | 3f164979 | 2026-10-06 | 29 | 0 | −1 +1 | — | 3/7 | 宣告收斂後首次再評：結 503，新立 504（接力） |
| R206 | 9192cd0b | 2026-10-07 | 29 | 0 | — | 1 | 3/7 | Mac 他機輪＋carriers 引號濾網；505 新立即結 |
| R207 | 6fdd5dfa | 2026-10-07 | 29 | 0 | −1 +1 | — | 3/7 | 五問協定修憲（時間型再評退役）：結 504，新立 506（接力） |
| R208 | 999c53f3 | 2026-10-09 | 28 | −1 | −1 | — | 3/7 | nightly 錨機械回填（refresh_nightly_anchor.py）：結 506 |
| R209 | dfeabe48 | 2026-10-09 | 2 | −26 | −26 | — | 5/7 | 技術債結案輪：24 結案（18 closed-by-decision／6 fixed）＋2 移外部軌 |
| **R210（工作樹，未 commit）** | — | 2026-10-09 | **0** | −2 | −2 | 0 | 5/6 | DEF-101-887（tree_state 樣本剔除）／DEF-200-207（ADR-XPLAT-013 翻 Accepted＋U9 退役）於工作樹改 fixed；本包只量帳本狀態、不驗修法 |
