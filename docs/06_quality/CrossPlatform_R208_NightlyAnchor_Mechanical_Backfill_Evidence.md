# CrossPlatform R208 — ONBOARDING 表③ nightly 錨機械回填（DEF-200-506 結案；證據檔）

> R 系列治理文件（根 CLAUDE.md〈三條改進軌道〉附列）。上輪決策檔：`docs/06_quality/CrossPlatform_R207_FiveQuestion_Retire_Time_Triggers_Decision.md`〈五〉。本輪不是五問輪：不改協定、不加輪帳本列、不改根 CLAUDE.md。轉述標 `[主控提供]`／`[SA 讀碼]`／`[QA 回報]`，其餘為本場親跑。

## 〇、一句話結論
nightly 錨與表③-b 由 `tools/refresh_nightly_anchor.py` 機械回填（本機 nightly 每日一次，輸出是 GitHub 狀態的純函式、零本機時鐘），pre-push 與 CI 以 `--check-head` 把關；對這個錨不再有日曆義務（掌舵者 2026-10-07 裁決：維護只由症狀驅動）`[主控提供]`。DEF-200-506 結案（`fixed（2026-10-08）`）。

## 一、事實與理由
1. **機制與否決** `[主控提供]`：本機 nightly 把 gh 現查結果寫回工作樹（先例＝perf baseline 由 nightly 寫回、隨 chore commit 收，0da65578）。否決排程 workflow 以 bot 回寫：①繞過本機 pre-push 全部閘門；②bot commit 與掌舵者直推 main 競態；③需 `contents: write`，且紅因判讀需要人與帳本。
2. **設計書查證** `[SA 讀碼]`：`cloud_fail_open_jobs()` 現回 4 支，其中 `autoclaude-pg-e2e-on-label.yml`、`autoclaude-mutation-on-change.yml` 無排程可取樣 ⇒ 表③-b 列集合＝fail-open ∧ job 層 `if:` 放行 `schedule` 者（今日 2 支；Architect 核定）。Windows 自成 stage 的依據：`dev_start.py` 只解析 `END exit decision`、`sdd_chaos_latest` 有同型先例、`Invoke-Stage` 把 rc=2 當 WARN。
3. **設計書未列、實作時才撞到的連鎖**：①凍結前綴自緊（`_REPIN_LOG_FROZEN_PREFIX_LEN` 要等於全部列數）；②`_PHASE2_REVIEW_LOG` 到期（上一列為 [維持觀察]、名額已用罄，只能追加 [提案]）；③分桶棘輪：新測試類別含 `ONBOARDING.md` 路徑 token 被判 prose 桶，改用合成檔名讓它如實落在 selfcontained；④`_TREE_FILE_FLOORS` 的 `tools/tests` 下限 68→69；⑤基線數字站點鎖：測試檔內「同行有 ≥4 位數字且含 skipped」會被判新家，`skipped` 的斷言須獨立成行、與帶 4 位數字的行分開；⑥兩支 compat-CI 的 paths：新根層消費檔須列入（由 `test_ci_paths_cover_root_consumers.py` 在 clean_venv_carrier 的 ci-gate 軌抓到，根層全套看不到）。
4. **暴露證據**（根 CLAUDE.md〈守衛面准入〉；新 `--check-head` 與新測試不在守衛面清單內，僅登記）：R207 輪（2026-10-07）掌舵者視窗實際依 SOP 第 6 步人工回填一次（commit 6fdd5dfa 訊息可查）；`useMacWin.md` 疑難排解表記載的「久未開發後第一次 push 撞到過期帶」事件類型。
5. **QA 複審（一次退回、一次 CONDITIONAL）與處置** `[QA 回報]`：退回理由只有測試無牙與文字（工具本體、零寫入、棘輪數字經其逐項重跑皆無缺陷）。F1（取較早 run）、F2（`skipped` 算紅）兩條 P2 與 F3（`--write` 寫後自檢）、F4（離線判準 P3／P4／P12／ISO8601 與 `parse_rows` 靜默略過）兩條 P3 已補斷言並以突變複驗殺死（見〈四〉突變列）；F5 於〈六〉補句；F6 於帳本狀態欄與〈三〉補範圍；F8 與 QA 文字訂正九條已落地。新測試 19 支、M＝309（≤309）。QA 第二輪複驗判 CONDITIONAL：〈三〉三句覆蓋缺口理由不實，已改為事實句，並補 `test_subprocess_call_contract_is_pinned_on_the_injected_runner` 一支（M55 轉 KILLED）。

## 二、改了什麼（逐檔；淨行數＝`git diff --numstat HEAD` 的新增／刪除，新檔為其行數；新檔已 `git add -N`＝intent-to-add、非 commit）
| 檔 | 淨行 | 內容 |
|---|---|---|
| `tools/refresh_nightly_anchor.py` | +582／−0 | 新 CLI：預覽／`--write`／`--check`／`--check-head`；純函式（解析、判準、渲染）與 I/O（gh、git、檔案）分離可注入；`NIGHTLY_MAX_AGE_DAYS` 與 `cloud_fail_open_jobs()` 的單一居所；修復輪只改兩處訊息字串（`ADVICE_WRITE` 句尾、`gh` 逾時訊息補分隔），判斷邏輯零改動 |
| `tools/tests/test_refresh_nightly_anchor.py` | +305／−0 | 新測試 19 支（注入式、零 skip、不打真 gh／git）；修復輪補「較早 run」「`skipped` 算紅」「寫後自檢」三類斷言與離線判準四款反例；第二次修復補子行程呼叫契約（注入 runner 的整組 kwargs）一支 |
| `tools/tests/test_doc_loc_baseline_freshness_r60.py` | +11／−41 | 判準檔改 import 新工具的常數與掃描函式（搬家，淨減）；`sop` 訊息改指路 `--write`；[1/5] |
| `tools/tests/test_pre_push_dispatcher.py` | +7／−0 | 假 repo 夾具補第 11 支守門替身 |
| `tools/tests/test_root_infra_parity.py` | +2／−2 | 下限貼齊 12／17（行數不變） |
| `tools/tests/test_adr_xplat001_c1c2_lock.py` | +36／−9 | 護欄層棘輪連鎖（見〈六〉） |
| `tools/lib/skip_tag_policy.py` | +3／−1 | 樹檔數下限 `tools/tests` 68→69（實測 87 支；掃描器逐字指示） |
| `tools/lib/baseline_origin.py` | +2／−2 | [1/4]→[1/5]（現在式宣稱） |
| `tools/lib/governance_docs.py` | +4／−0 | 登記本檔 |
| `tools/git-hooks/pre-push` | +7／−3 | 快層迴圈加 `--check-head`、三處計數「十支」→「十一支」 |
| `.github/workflows/root-infra-ci.yml` | +15／−2 | 第 17 道檔頭條目＋對等 step、檔頭「十六道→十七道」 |
| `.github/workflows/macos-compat-ci.yml` | +10／−0 | paths 清單（push／pull_request 各一）加 `tools/refresh_nightly_anchor.py`（被 tools/tests 以 import 消費；DEF-101-042 同構） |
| `.github/workflows/windows-compat-ci.yml` | +10／−0 | 同上（push／pull_request 各一） |
| `AutoClaude/tools/run_local_nightly.sh` | +14／−8 | stage 5 `nightly_anchor`（排在 sdd_ci_gate 之後）、`STAGE_TOTAL=5`、說明同步 |
| `AutoClaude/tools/run_local_nightly.ps1` | +41／−7 | 自成 stage `nightly-anchor-refresh`（排在 Cleanup 之前）＋四個同步點＋rc=2 正規化成 1；僅用 Edit 工具（BOM＋CRLF 不變） |
| `tools/install_windows_nightly.ps1` | +1／−1 | [1/4]→[1/5]（散文） |
| `AutoClaude/tests/tools/test_run_local_nightly_sh_static.py` | +25／−10 | [N/5]、`FAIL=5`、新增位置鎖（第 5 個 stage 排最後、指紋先於所有 stage） |
| `AutoClaude/tests/tools/test_run_local_nightly_static.py` | +24／−1 | 新增 Windows wiring 鎖（四處同步點、rc=2 正規化、不得 `$null =` 吞掉） |
| `ONBOARDING.md` | +49／−38 | §7 表③-b 說明段／表頭／SOP 第 6 步／錨行散文改字（回填 stage 位置：mac＝第 5 個、Windows＝Cleanup 之前）；表③-b 兩列與錨三欄由工具 `--write` 產生；§8 一句訂正（mac nightly 只串四支驗證腳本，第 5 個 stage 是回填而非回歸檢查）；另含 clean_venv_carrier 回填的表② darwin 指紋錨（autoclaude=2fc35cd37c96，measured-at=2026-10-08）與 AutoClaude pytest 快照 4686→4688 |
| `useMacWin.md` | +1／−1 | 疑難排解表一列改成新處置（`git add ONBOARDING.md` 優先） |
| `docs/06_quality/AutoSDD_Defect_Log.md` | +1／−1 | DEF-200-506 → `fixed（2026-10-08）`（646→639 bytes，狀態欄尾註「Windows／launchd 實跑未驗證」；其餘列逐列 bytes 不變） |
| `docs/04_planning/AutoSDD_improving_112.md` | +1／−0 | 檔尾 `guard-total:R208` 一行 |
| `docs/06_quality/CrossPlatform_R145_Scan_Findings.md` | +1／−0 | 檔尾 `guard-total:R208` 一行 |
| `docs/06_quality/CrossPlatform_R208_NightlyAnchor_Mechanical_Backfill_Evidence.md` | +107／−0 | 本檔 |

## 三、不改什麼
- 判準本體零改動（`_nightly_provenance_problems`／`cloud_nightly_red_problems`／`parse_cloud_fields`／`cloud_status_problems`）。R207 理論洞清單沿用、只登記不修：①`run_id not in onboarding_text` 的比對面含錨行本身而恆真（新工具的離線判準改綁表③-b 資料列；CI 判準本體未動）；②README 的 S1～S6 與 `charter_sa.md` 章節名撞號。
- 五問協定、輪帳本、根 CLAUDE.md、守衛面（`.claude/hooks`／`.claude/settings*.json`／指定七支 `tools/lib`／`session_resume_planner.py`）零改動；除 DEF-200-506 外不改既有帳本列；不新增 open 列。
- 不做：bot 回寫 workflow；Windows 機的表② 欄回填——Windows 欄指紋只能在 Windows 機量測，本輪未量測；該欄現值（autoclaude=69fdad8c334d）與目前樹不符，Windows 機上 `--check-snapshot` 會因此為紅，`tools/lib/clean_venv_carrier.py` 在該機重跑後解除 `[推論；未在 Windows 機驗證]`；`ONBOARDING.md` 內帶日期的 [N/4] 歷史敘述、帳本與歷史證據檔不改寫。
- 既存漂移不修：ONBOARDING §8 Windows「7 stage」清單與 `.ps1` 檔頭計數——本輪新增的 `nightly-anchor-refresh` 不在其內，該清單本身早已漂移（含 `sdd_chaos_latest`；設計書〈十〉#5 刻意不動 `.ps1` 內同款計數），§8 該行維持原文。
- 測試覆蓋缺口、本輪不補（突變複驗存活 8 個：M08／M21／M27／M43／M44／M45／M52／M53，皆不在設計書〈六-C〉明文測試清單內）：M08（`_SCHEDULE_IF_RE` 也放行只含 `workflow_dispatch` 的 `if:`）、M21（同名 job 靜默取第一筆；設計 2-D #9 要求 ≥2 筆 fail-loud）、M43（`parse_jobs` 容忍缺欄）、M44（`_table_span` 不驗分隔列）、M45（`render_rows` 不排序）；M27（`read_onboarding` 的 CR 檢查；`--write`／預覽另有第二道〔`rewrite_onboarding` 開頭〕，但 `--check` 對 CRLF 工作樹只靠這一道——本場以 ONBOARDING.md 的 CRLF 副本實測：原版 rc=1「含 CR」、M27 變體 rc=0 ✅——且無測試覆蓋 `--check` 的 CR 路徑）；M52／M53（`--status`／`--limit` 字面）：測試以注入的假 gh 取代真子行程，且沒有斷言它收到的 argv 值（`_gh(…, calls)` 已記錄 argv），故存活——是「未斷言」，不是「構造性看不到」。M55（`encoding` 字面）原本同因存活，且 `test_subprocess_encoding_hygiene` 並不守它：該鎖的 AST 判準只認尾名 ∈ {run, Popen, check_output, check_call, call}（該檔 :60），本工具以注入參數 `runner(...)` 呼叫（`refresh_nightly_anchor.py:403`），不在射程——本場對原版與 `encoding` 被拿掉的 M55 副本跑 `scan_files` 皆回 offenders=[]、stale=[]、parse_fail=[]；現由 `test_subprocess_call_contract_is_pinned_on_the_injected_runner` 以整組 kwargs（`encoding`／`timeout`／`stdin`／`cwd`／無 `shell`）作替代鎖，M55 與同族 M59～M66 皆 KILLED（見〈四〉突變列）。M31（`parse_rows` 靜默略過不合格式列）已補斷言（補時 M＝301）；M21／M43 維持為缺口，現 M＝309＝回歸鎖軌上限 309，無餘裕再補。

## 四、驗證（本場親跑；rc 與關鍵輸出行逐字取自 tool_result；表格內的 `|` 以全形 `｜` 代；沒跑的標「未驗證」）
| 指令 | 預期 | 實得 |
|---|---|---|
| `python tools/refresh_nightly_anchor.py --help` | rc=0 | rc=0；「用法：python tools/refresh_nightly_anchor.py [--write ｜ --check ｜ --check-head ｜ --help]」 |
| `python tools/refresh_nightly_anchor.py --bogus` | rc=2 並點名 | rc=2；「❌ refresh_nightly_anchor.py：未知引數 --bogus——本工具**不會**靜默忽略它並改跑預設路徑（那正是 rc=0 假綠的來源，見 R67-D20）。可用引數：--write／--check／--check-head／--help／-h」 |
| `python tools/refresh_nightly_anchor.py（唯讀預覽）` | rc=0，不落檔 | rc=0；「nightly-red=none」；「nightly-run=37324659627」；「nightly-checked-at=2026-10-05T14:26:01+00:00」；「與工作樹：一致」 |
| `python tools/refresh_nightly_anchor.py --write（現況）` | rc=0 並印「無變更」（首次回填的 rc=0 與「已回填」行見下一列） | rc=0；「✅ 無變更：表③-b 與錨的 nightly 三欄已與 GitHub 現況一致（nightly-run=37324659627 nightly-checked-at=2026-10-05T14:26:01+00:00）」（修復輪前親跑；修復輪依指示不跑 `--write`） |
| 首次 `python tools/refresh_nightly_anchor.py --write`（改字後第一次） | rc=0、已回填 | rc=0；「✅ 已回填 ONBOARDING.md：nightly-run=37324659627 nightly-checked-at=2026-10-05T14:26:01+00:00 nightly-red=none（表③-b 2 列）」（接著第二次回 rc=0「無變更」）（修復輪前親跑） |
| `git diff --stat -- ONBOARDING.md` | 只動預期位元組：11 個 hunk 逐一歸類＝表③ 改字與工具回填 46／35（8 個 hunk）＋§8 一句訂正 1／1＋clean_venv_carrier 回填 2／2（表② darwin 指紋錨、AutoClaude pytest 快照 4686→4688） | rc=0；「1 file changed, 49 insertions(+), 38 deletions(-)」 |
| `python tools/refresh_nightly_anchor.py --check` | rc=0 | rc=0；「✅ nightly 錨判準通過（工作樹）：nightly-run=37324659627 nightly-checked-at=2026-10-05T14:26:01+00:00（3 天前，上限 14 天）nightly-red=none」 |
| `python tools/refresh_nightly_anchor.py --check-head` | 對舊 HEAD 判綠（設計行為：舊錨 1 天前、run id 在舊表③-b、紅集合一致；未 commit 前 HEAD 仍是舊錨） | rc=0；「✅ nightly 錨判準通過（HEAD）：nightly-run=37324659627 nightly-checked-at=2026-10-07T08:50:29+08:00（1 天前，上限 14 天）nightly-red=none」 |
| `cd tools/tests && python -m unittest test_refresh_nightly_anchor` | OK | rc=0；「Ran 19 tests in 0.105s」；「OK」 |
| `cd tools/tests && python -m unittest test_doc_loc_baseline_freshness_r60` | OK | rc=0；「Ran 281 tests in 108.653s」；「OK」 |
| `cd tools/tests && python -m unittest test_root_infra_parity` | OK | rc=0；「Ran 13 tests in 0.010s」；「OK」 |
| `cd tools/tests && python -m unittest test_pre_push_dispatcher` | OK | rc=0；「Ran 37 tests in 21.828s」；「OK」 |
| `cd tools/tests && python -m unittest test_check_wrapper_thinness` | OK | rc=0；「Ran 45 tests in 4.980s」；「OK」 |
| `cd tools/tests && python -m unittest test_subprocess_encoding_hygiene` | OK | rc=0；「Ran 39 tests in 15.313s」；「OK」 |
| `cd tools/tests && python -m unittest test_platform_neutral_paths` | OK | rc=0；「Ran 177 tests in 61.781s」；「OK」 |
| `cd tools/tests && python -m unittest test_adr_xplat001_c1c2_lock` | OK | rc=0；「Ran 192 tests in 13.789s」；「OK」 |
| `cd AutoClaude && python -m pytest tests/tools/test_run_local_nightly_sh_static.py tests/tools/test_run_local_nightly_static.py -q` | 全綠（Windows-native-only 於 mac skip，如實列出） | rc=0；「93 passed, 51 skipped in 8.24s」 |
| `bash -n AutoClaude/tools/run_local_nightly.sh` | rc=0 | rc=0；「（無輸出）」 |
| `bash AutoClaude/tools/run_local_nightly.sh --help` | rc=0、印 5 個 stage | rc=0；「stage：[1/5] macos_smoke ／ [2/5] root_unittests ／ [3/5] autoclaude_gate ／ [4/5] sdd_ci_gate ／ [5/5] nightly_anchor」 |
| `pwsh Parser::ParseFile AutoClaude/tools/run_local_nightly.ps1` | 0 | rc=0；「ParseErrors=0」 |
| `pwsh Parser::ParseFile tools/install_windows_nightly.ps1` | 0 | rc=0；「ParseErrors=0」 |
| `git ls-files -s AutoClaude/tools/run_local_nightly.sh tools/git-hooks/pre-push` | 100755 不變 | rc=0；「100755 AutoClaude/tools/run_local_nightly.sh」；「100755 tools/git-hooks/pre-push」 |
| `file AutoClaude/tools/run_local_nightly.ps1 tools/install_windows_nightly.ps1` | BOM＋CRLF 不變 | rc=0；「Unicode text, UTF-8 (with BOM) text, with very long lines (540), with CRLF line terminators」；「Unicode text, UTF-8 (with BOM) text, with CRLF line terminators」 |
| `ruff check tools/ .claude/hooks/ --no-cache` | rc=0 | rc=0；「All checks passed!」 |
| `cd AutoClaude && ruff check（兩支靜態測試）--no-cache` | rc=0 | rc=0；「All checks passed!」 |
| `python tools/check_defect_log_crossref.py` | rc=0 | rc=0；「✅ 缺陷帳本跨文件狀態一致：帳本 207 筆有效狀態紀錄、19 份掃描目標皆無矛盾；…；具名治理文件 160 份皆已登記…」 |
| `python tools/check_defect_log_crossref.py --unresolved-count` | 28（29→28） | rc=0；「未結列數＝28／全部 207 列｜warn=86 fail=98」 |
| `python tools/check_handoff_carriers.py` | rc=0 | rc=0；「✅ 每一筆前瞻延後宣稱都有帳本承接載體」 |
| `python tools/sync_onboarding_baselines.py --check` | rc=0（表① 活格不變） | rc=0；「✅ [rootunit-baseline-live:] {'tests': 5101}（來源：tools/run_root_unittests.py 的 MIN_TESTS）」 |
| `python tools/check_pytest_baseline_sites.py` | rc=0、未納管存量 114 不變 | rc=0；「✅ pytest 基線站點守門通過：12 份掃描檔中僅 SSOT（ONBOARDING.md）載有基線數字（另 34 筆豁免行，見 warning）；發現面另有 114 支未納管存量檔（shrink-only 棘輪，新增即紅；日期性文物樹依 _DATED_ARTIFACT_PREFIXES 豁免）」 |
| `python AutoClaude/tools/check_loc_budget.py --json` | rc=0 | rc=0；「rc=0」 |
| `python tools/probe/audit_session.py --protocol-status` | sha 仍 97bbef35…、無 PROTOCOL-CHANGED | rc=0；「protocol_sha256=97bbef35f0d58c8fdbe04088d56a790951eaea1c01b78bd8c0f94d56a446fed4（manifest 11 檔）」 |
| `env -i HOME PATH=/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin .venv/bin/python tools/refresh_nightly_anchor.py` | 極簡 PATH（模擬 launchd）下 gh 可解析、預覽成功 | rc=0；「nightly-run=37324659627」；「與工作樹：一致」 |
| `PATH=/usr/bin:/bin .venv/bin/python tools/refresh_nightly_anchor.py --write` | 取不到 gh ⇒ rc=3、零寫入 | rc=3；「❌ 找不到 gh（PATH 上沒有）⇒ 無法回填。處置：安裝 GitHub CLI 並執行 `gh auth login`」；「ONBOARDING.md 位元組前後相同=True」（修復輪前親跑） |
| `cd tools/tests && PATH=/usr/bin:/bin ../../.venv/bin/python -m unittest test_refresh_nightly_anchor` | gh 不在 PATH 單跑仍全綠 | rc=0；「Ran 19 tests in 0.063s」；「OK」 |
| `gh run list --commit 6fdd5dfaf82421a28121921159148b993c1f1516 --json databaseId,name,status,conclusion,event,createdAt` | R207 push 後四支雲端 run 全 success（開場對帳；短 sha 會回空陣列，須完整 40 碼） | rc=0；「10 筆；completed/success 10 筆；macos-compat-ci 37562626722、windows-compat-ci 37562626718、AutoClaude CI 37562626762、root-infra-ci 37562626691」 |
| 突變複驗（scratchpad 副本樹逐一套用 59 個變體，每次單跑 `test_refresh_nightly_anchor`，`-B` 且每輪清 pyc；**不碰 repo**） | 補測後 F1～F4 對應變體必死 | KILLED 51／SURVIVED 8；M02、M02b、M03、M49、M31、M32、M34、M35、M36、M55、M59、M60、M61、M62、M63、M64、M65、M66 皆 KILLED（逐字：「KILLED  M02 anchor_from: take samples[0] instead of the earliest  -> ['test_checked_at_is_the_earlier_run_in_utc_plus_00_00_form']」；「KILLED  M03 red: only failure/cancelled count (skipped/neutral/timed_out NOT red)  -> ['test_red_is_the_non_success_subset_or_none']」；「KILLED  M31 parse_rows: silently skip malformed rows  -> ['test_the_offline_gate_rejects_each_bad_anchor_shape']」；「KILLED  M49 _write: post-write self-check ignored (always green)  -> ['test_write_self_check_fails_after_writing_a_stale_anchor']」；「KILLED  M55 _run_tool: drops encoding/utf-8  -> ['test_subprocess_call_contract_is_pinned_on_the_injected_runner']」；「KILLED  M63 _run_tool: adds shell=True  -> ['test_subprocess_call_contract_is_pinned_on_the_injected_runner']」）；存活 8 個＝M08／M21／M27／M43／M44／M45／M52／M53（登記於〈三〉）；副本樹基線＝19 支中 1 支（`test_offline_verdicts_agree_with_the_ci_judge_and_share_one_home`）因副本不含 R60 模組恆紅、已排除，repo 內該支為綠 |
| `python tools/run_root_unittests.py`（背景阻塞；修復輪 01:04:41～01:06:38，其後證據檔只更新本列與下一列的數字；原輪 23:28:46～23:30:41 為 ROOT_RC=0／5197） | ROOT_RC=0 | 「ROOT_RC=0」「✅ unittest 數量下限釘選通過：發現 5199 個測試（下限 5101）」「[skip census] tools/tests@darwin 共 47 支…欠債型 0 支（目標 0）」「✅ 真實 TEMP 圍籬：…零變動」 |
| MIN_TESTS 餘裕（同上輸出） | 無重釘提醒 | 輸出內無「重釘」「MIN_TESTS」字樣；`MIN_TESTS` 維持 5101、發現數 5199（原輪證據檔載 5197；多 2＝兩次修復各新增 1 支：寫後自檢、子行程呼叫契約） |
| `"$(git rev-parse --show-toplevel)/.venv/bin/python" tools/lib/clean_venv_carrier.py`（Docker 全程未啟動，不帶 `--allow-pg-extras`） | rc=0、乾淨 venv 必刪 | 第一次 CARRIER_RC=1（ci-gate 軌 `scripts/tests/test_ci_paths_cover_root_consumers.py` 2 failed：`tools/refresh_nightly_anchor.py` 未列入兩支 compat-CI paths）；補 paths 後第二次 23:13:50～23:15:29「CARRIER_RC=0」「✅ 已回填 [snapshot-fingerprints-darwin:] → {'v001': '8ffe3c3dabbd', 'v030': '6d46814f9084', 'scripts': 'ec35ee2838d0', 'autoclaude': '2fc35cd37c96'}」；事後 TEMP 下 cleanvenv 目錄 0 個（原輪親跑；修復輪未動 `AutoClaude/tests/**`，見下兩列） |
| `python tools/sync_onboarding_baselines.py --check-snapshot` | rc=0 | rc=0；「✅ §7 表② 指紋相符 macOS 欄（v001=8ffe3c3dabbd, v030=6d46814f9084, scripts=ec35ee2838d0, autoclaude=2fc35cd37c96）」；Windows 欄指紋只能在 Windows 機量測，本機該欄印 ℹ️、不計入本機 rc |
| `git diff --stat -- AutoClaude/tests` | 只有兩支靜態測試 | rc=0；「2 files changed, 49 insertions(+), 11 deletions(-)」 |
| `python（sorted(AutoClaude/tests/**/*.py) 的相對路徑＋內容 sha256，與 carrier 完成當下所記比對）` | 與 carrier 之後所記相同（修復輪未動 `AutoClaude/tests/**`，不必重跑 carrier） | rc=0；「sha256=cf3c3c67…；與 carrier 之後所記相同」 |
| 未驗證項 | — | ①Windows 機上由 schtasks 觸發的 `nightly-anchor-refresh` stage 實跑與該機 gh 可用性（只能在 Windows 機量測，本場未驗證）；②mac launchd 02:00 排程下 stage 5 的實跑（本場只以 `env -i` 極簡 PATH 的預覽驗 gh 可解析、登入有效；launchd 無人值守下 gh 憑證能否取用未驗證）；③`run_local_nightly.sh` 不帶旗標的整輪實跑（本場只驗 `--help`／`bash -n`／沙箱靜態測試）；④`.ps1` 的標的引擎是 Windows PowerShell 5.1，本場只在 pwsh 7 驗了 `ParseFile`，5.1 下實際執行未驗證；⑤「dispatch 取樣勝出」分支只被假 gh 的單元測試驗過，無真資料對照。 |

## 五、交棒
無。對這個錨沒有任何日曆義務；過期只由症狀驅動（工具 rc≠0、心跳 `FAIL=`、`--check-head` 擋 push）。

## 六、護欄層重釘（`test_adr_xplat001_c1c2_lock.py`）
- 軌別與淨額：歸回歸鎖軌（Architect 核定採①）。主表淨額 114350→114659（+309）＝M；軌列＝309（精確相等）；主軌 0 ≤ 0（款(11) 連升自此歸零）；M ≤ 軌上限 309（現 M 恰等於軌上限）。`--print-guard-lines` 末態印「淨額 114659→114659 (+0)」「逐檔漂移 0 支」。
- M 的構成（逐檔）：新測試檔 +305（305 行、19 支）；`test_pre_push_dispatcher.py` +7；`test_doc_loc_baseline_freshness_r60.py` −30；本檔自身 +27；`test_root_infra_parity.py` 0。第一次修復補測試使 M 由 284 增至 301，第二次修復補子行程呼叫契約一支而增至 309。
- 到期義務：`_REPIN_NET_CAP_SCHEDULE` 追加 `(208, 518)` 兌現，`_REPIN_NET_CAP_DUE_ROUND` 198→210、`_REPIN_NET_CAP_DUE_TARGET` 518→517；U9 到期輪具名展延 198→213；`_PHASE2_REVIEW_LOG` 追加 `(208, "[提案]")`（上一列 [維持觀察] 名額已用罄），到期輪由末列導出為 213；該列為既存 R129 未決提案的重新登記、無新判斷（體例同既有 R189 列）。
- 凍結前綴：`_REPIN_LOG_FROZEN_PREFIX_LEN` 327→328、`_REPIN_LOG_HISTORY_SHA256` 重釘，`_FROZEN_PREFIX_REWRITE_LEDGER` 追加 `("R208", "7c1d18c28c25", "1e22b76a4c99", "DEF-200-506")`。
- 兩份常設檔的 `<!-- guard-total:R208 -->` 行：`docs/04_planning/AutoSDD_improving_112.md`、`docs/06_quality/CrossPlatform_R145_Scan_Findings.md`（檔尾各一行）。
- 其餘表：`tools/lib/skip_tag_policy.py` 的 `_TREE_FILE_FLOORS["tools/tests"]` 68→69；`check_pytest_baseline_sites.py` 的未納管站點棘輪 114 不變；E501 存量債上限不變（新增行 EAW 實量零超線）；分桶棘輪（prose／guard_self）未成長。
