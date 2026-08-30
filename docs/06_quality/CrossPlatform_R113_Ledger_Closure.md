# CrossPlatform R113 結案輪證據檔（結構性長債分軌輪）

> **輪次性質**：純結案輪（mac；掌舵者直接指令觸發，禁新功能、禁平行發現 wave、禁 `--no-verify`）。
> 本檔＝R113 全部結案動作的具名證據載體；帳本列只放索引，實測輸出全文在此。
> 本檔初稿由 429 斷點後的喚醒鏈無頭續跑寫成（權限牆擋落盤，全文暫存於逐字稿）；
> 收尾單人窗口 2026-08-31 回填當回合憑證後落盤。事件完整時間線見 §8。

## §0 量測頭（開場四件套，2026-08-30 實跑）

- HEAD＝`a00014a7515ca04940493415bb50c1ed3b60211a`（工作樹乾淨起步）
- `python tools/check_defect_log_crossref.py --unresolved-count` → **未結 61／全 165 列**（warn=86／fail=98）；外部阻塞軌 8 筆
- `python tools/check_archive_required.py` → 未觸發歸檔門檻
- `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` → 89452→89452（+0）
- `python tools/session_resume_planner.py --pace` → recommended=8｜band=free｜binding=seven_day 27%
- 棘輪餘裕現查：`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS=2`（R111 淨額 −15 已歸零 streak）；`_REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES=1`（已用於 R101）
- 輪型判定：**純結案輪**（新增 0 ≤ 結案 7；DEF-200-212 原列為第 8 筆、經 R3 複審 B1 改判回 open——見 §3 與 §5 #22）

## §1 主菜：結構性長債軌落地（掌舵者 2026-08-30 核准，存證＝AutoSDD_TechDebt_Paydown_Playbook.md §6 第 3 條）

機械物：`tools/lib/ledger_closing_guards.py`——`STRUCTURAL_DEBT_SOURCE_RE`＝`結構性長債-\S+`（scoped 枚舉，與外部軌四值互斥）＋`_STRUCTURAL_DEBT_MAX_ROWS=7` 成長棘輪＋`external_blocked_log_problems()` 參數化複用（log_name／source_re）；`check_defect_log_crossref.py` **零改動**（raw-line 餘裕恰 5＝下限）。回歸鎖＝TestStructuralDebtLog 九支（全注入固定日期）。

### 遷軌 SOP 逐列（動工前重量：DEF-101 未結 22 筆中合格 7 筆，非 2026-08-27 快照的 29）

1. DEF-101-018｜結構性長債-ruff存量分批清｜解鎖＝`ruff check .` 歸零或殘量 shrink-only 棘輪進閘（掌舵者 2026-08-29 裁維持逐筆清；2026-08-30 現查存量 3579）｜主帳本列收斂為指向長債軌的索引
2. DEF-101-398｜結構性長債-dev_start拆分｜解鎖＝check_loc_budget --json 之 dev_start.py loc<1952 且 bootstrap_lock.py／nightly_heartbeat.py 存在（現查 1952/1952 headroom 0）｜同上
3. DEF-101-701｜結構性長債-run_root_unittests行數死結｜解鎖＝run_root_unittests.py headroom>0 且 MIN_TESTS 重釘路徑有指紋一致斷言（現查 759/759）｜同上
4. DEF-101-702｜結構性長債-R68稽核波｜解鎖＝CrossPlatform_R68_Scan_Findings.md「狀態@R69」欄 open/partial 計數＝0（2026-08-30 現值 28）｜同上
5. DEF-101-886｜結構性長債-工作樹序列化待裁決｜解鎖＝根 CLAUDE.md 或 ADR 出現具名序列化條款＋tools/tests/ 規則鎖（現查 CLAUDE.md 零命中 worktree 條款）｜同上
6. DEF-101-960｜結構性長債-skip剖面需Windows實機｜解鎖＝skip_id_ledger.json 出現 nightly(solo win32) 與 CI(ubuntu) 剖面鍵（現查僅 darwin/linux/win32 三鍵）｜同上
7. DEF-101-980｜結構性長債-ADR-XPLAT-005待裁決｜解鎖＝該 ADR 檔頭狀態行 ≠ Proposed（現查 :8 逐字 `Proposed（R81）`）｜同上

排除說明：DEF-101-981（六子項併列）刻意**不遷**——路線圖第 4 條判準：併列應拆分不應整列遷軌，遷了會把子項埋掉。

遷軌後實測（實作包 1 當回合）：`--unresolved-count` → **54 列**；長債軌輸出行「結構性長債軌（AutoSDD_Structural_Debt_Log.md，不計入未結列 warn/fail 分母）：7 筆」；全套 root unittest `Ran 3735 tests … OK (skipped=44)` rc=0。

## §2 已結列殘留待辦清理（crossref warning 3→0）

偵測器＝`check_defect_log_crossref.py::residual_todo_notes()`（正則 `未指派|擇機|留待|下一輪|下輪|尚未|待辦|backlog`，掃狀態欄＋分流去向欄，反引號遮蔽）。

1. **DEF-101-338（:83，分流去向欄）**：`建議下一輪調查根因（是否有測試未用 \`tmp_path\`）` → `根因已於 R107 查明（見狀態欄），原建議語失效`（該調查 R107 已做：test_drift_monitor.py 34 處全用 tmp_path、v0.01 四支假 SHA 檔已 git rm——判例＝DEF-101-205 同手法）
2. **DEF-101-559（:93，分流去向欄）**：`…**承接輪次：未指派**（依 …R59 硬規則②明標…）` → `…已於 R107 由掌舵者裁決落地；原承接輪次欄語（R59 硬規則②）隨之失效`（升版已落地：AISDLC_SDD_v0.30 hub-push.yml 八站點 checkout@v5／setup-python@v6／upload-artifact@v6；ADR-XPLAT-011 §4 條件② blob 分裂已 materialize＝去重恰 2 顆）
3. **DEF-200-228（:228，狀態欄）**：`…；下輪 Windows 真機需覆核實測 census` → `…＝站點盤點式保守上界，給多不判紅；覆核條件逐字在 \`tools/lib/skip_group_policy.py\` R100 註`（真待辦不失蹤：覆核指令逐字住在該做事的檔＝skip_group_policy.py R100 註；結構性缺口另有 open 列 DEF-101-981② 承接）

## §3 verify-only：DEF-200-212 複驗（🔴 R3 複審 B1 改判＝**不結案**，列回 open（交由R114））

> 改判理由（R3 親跑取證）：①的 `ledger_def_ids(unresolved_only=True)` 只在 `--self-test` 合成場景使用，
> 生產呼叫 `main()`（`check_handoff_carriers.py:469`）未傳該參數＝原始缺陷行為在生產路徑仍可重現；
> 接線刻意延後是對的（現接會因帳本時鐘滯後 R100 生 3 筆假陽性，函式 docstring 自陳），
> 但「fixed」宣稱沒有承接這個限定詞＝部分完成標 fixed（§4.7 否決清單）。以下自證輸出保留為「已完成那一半」的證據。

**原列逐字保全**（帳本列已瘦身為索引，原文唯一保全處＝本節）：

- 原「現象與證據」欄全文：`tools/check_handoff_carriers.py` 兩個同族假綠：① 判準② 帳本側 `:173-190` `ledger_def_ids()` 無狀態過濾 ⇒ `fixed` 列 ID 即可滿足「有承接載體」，而它要證明的是有**未結**承接單位；② `:237-240` 載體面用 `_REPO_ROOT.glob()`（檔案系統）卻在 `:40`／`:294` 自稱 **tracked** ⇒ 未追蹤檔被計為 tracked（實證：本窗口未追蹤的 `R100_HANDOFF.md` 使普查 85 → 86 並通過驗證）
- 原狀態欄：`open（交由R112）：②已修①已落接線待結案輪@R111`

**現況複驗**（R113 分診包，唯讀）：①`check_handoff_carriers.py:168`／`:203` 已用 `gate._UNRESOLVED_CLASSES` 過濾；②`carrier_files()` :275-279 已走 `git_paths.ls_files`＋:341 退化告警；③已進 `tools/git-hooks/pre-push:357-363` 生產路徑；④自帶 `--self-test`（:374）。

**針對性驗證（`python3 tools/check_handoff_carriers.py --self-test`）輸出**：

2026-08-31 收尾單人窗口實跑，rc=0，逐字輸出：

```
[self-test] 判準① 提交訊息 → 帳本承接列
  PASS  宣告延後到未來輪、帳本零承接 ⇒ 紅
  PASS  帳本有未結列承接更後面的輪次 ⇒ 綠
  PASS  承接輪號比宣告目標小一輪 ⇒ 不足以接手 ⇒ 紅
  PASS  歷史宣告的目標輪 < 當前輪 ⇒ 自動出局（無需豁免名單）
[self-test] `defer_rounds()` 樣式與敘事濾網
  PASS  「皆留 ＋ 輪號」命中
  PASS  「交給 R81」命中
  PASS  「兩列 ＋ 輪號」＝敘事引述 ⇒ 不命中（實測假紅）
  PASS  「本列 R14」＝帳本 SSOT 負向回顧仍生效
  PASS  code span 內逐字引述 ⇒ 不命中
[self-test] 判準② 交接載體 → 帳本 DEF-ID
  PASS  延後行無 DEF-ID ⇒ 紅
  PASS  延後行指名帳本內存在的 DEF-ID ⇒ 綠
  PASS  指名一個帳本裡查無列的 DEF-ID ⇒ 仍紅（引用 ≠ 有列）
[self-test] 判準② 取數面兩假綠（DEF-200-212；strict 路徑，閘門接線待結案輪）
  PASS  已結（fixed）列的 ID 不算承接載體（改前本注入為綠＝假綠重演）
  PASS  未結列的 ID 仍是承接載體（對照組）
  PASS  glob 命中 ∩ tracked：未追蹤路徑被剔除（tracked 語意補真）
  PASS  tracked 取不到 ⇒ 退回 glob 並標記 fallback（fail-loud，判準③ 出聲）

[self-test] ✅ 全部通過
```

## §4 外部阻塞軌複查（3 筆複查日 2026-08-21 → 2026-08-30）

三筆阻塞源皆為 `Windows 實機`（DEF-101-693／DEF-200-063／DEF-200-147）。複查判定：本輪執行面＝darwin，三筆解鎖條件（Windows 真機執行紀錄／`claude -p --debug hooks` 真機取證／govwrite 九格 rc 矩陣真機重跑）逐字皆需 Windows 真機，2026-08-30 無 Windows 窗口 ⇒ 阻塞仍成立，僅更新複查日。附帶動作：外部軌檔頭補分界句（兩軌枚舉互斥），拆除 `test_the_real_doc_is_well_formed` 的 date.today() 日期引信（改斷言 fails-only；若不拆，2026-09-05 起 3 筆 warn 會把 pre-push＋root-infra-ci 一起打紅）。

## §5 輪內暫存清單裁決表（節流閘 §5 稽核義務，23 筆逐筆留痕）

| # | 發現 | 裁決 |
|---|---|---|
| 1 | DEF-200-169/065 列上敘事 stale（quota_gate loc 現測 391、skip_group_policy 現測 362/400） | advisory 記錄，列仍 open 自行承接 |
| 2 | DEF-200-137 列上 verify_cmd 已失效（4 命中全為散文，照跑會誤判已修） | advisory 記錄，列仍 open |
| 3 | DEF-200-133 原實例已消失（fake_pty 已 tracked）但判準仍零 | advisory 記錄，列仍 open |
| 4 | check_handoff_carriers --self-test 無 tools/tests 消費者（與 DEF-200-188① 同構） | 併入既有列 188①，不立列 |
| 5 | DEF-200-172 ⑦已修⑥未修、⑥docstring 與實作矛盾（12 鍵硬列） | advisory 記錄，列仍 open |
| 6 | 外部軌真檔測試 date.today() 日期引信（2026-09-05 起必紅） | 當場修掉未立列（斷言改 fails-only） |
| 7 | AutoSDD_External_Blocked_Log.md 漏登體積守門 | 當場修掉未立列（補登 _GOVERNANCE_DOCS＋逐字檔名 glob） |
| 8 | 兩軌枚舉與散文零雙向綁定 | advisory 記錄（scoped 測試部分緩解，綁定鎖另案） |
| 9 | 遷軌列狀態欄形狀無格式鎖（archive_67 已有漂移實例） | advisory 記錄（本輪 7 列用統一模板） |
| 10 | check_defect_log_crossref.py raw-line 餘裕恰 5＝下限 | 記錄（本輪零改動遵守） |
| 11 | DEF-101-338 實際污染面 v0.02/03/04 各 4 支假 SHA 檔仍 tracked（共 12 支，帳外；R78 Debt_Audit :122 早有記載） | **呈報單**：需掌舵者 Copy-on-Evolve 例外核准 git rm（同原 338 判例）；核准後 <30 分鐘可修；不立列，寫入 R113_HANDOFF 呈報單 |
| 12 | hub-push.yml blob 分裂機械化前提已成熟（`git ls-files -s` 去重恰 2，R107 懸空 6 輪） | advisory 記錄，HANDOFF 下一步候選 |
| 13 | DEF-200-155／DEF-101-981 承接輪次落在過去（R98→改派R101／R82→改派R91） | 帳本時鐘 R100 滯後所致，記錄 |
| 14 | 帳本時鐘落後 13 輪（current_round=R100），承接稽核無牙窗口 | 記錄；本輪刻意不立新列維持時鐘，重新武裝留給下一個立列輪 |
| 15 | playbook 附錄 B 誤分類 DEF-101-863 入 Windows 實機族（實為 darwin 可完成的靜態 reason 判準） | 記錄訂正於本檔（附錄 B 是快照不回改） |
| 16 | DEF-101-863 等效兌現候選（[ENV-DISABLED]/[TOOL-ABSENCE] 標籤族已落地、reason 內容斷言未落） | 記錄，本輪不改判 |
| 17 | DEF-200-211 到期義務破線（_PHASE2_DUE_ROUND=111，R113 已逾 2 輪；[維持觀察] 名額已罄） | 本輪處置：_PHASE2_REVIEW_LOG 追加 (113,[提案]) 引掌舵者既存裁決（playbook §6 第 1 條）；(b)(c) 落地由 DEF-200-211 承接、與 207 同批四方 |
| 18 | DEF-200-207 列上「U1~U7 全 ☐」stale（U5 已 ▣@R111） | advisory 記錄 |
| 19 | DEF-200-206③ 局部失效（STATE_RETAIN_VERSIONS 已有 env 讀取路徑，餘兩鍵仍零） | advisory 記錄 |
| 20 | DEF-200-217 E5 落點 .importlinter 不在 repo 根（在 AutoClaude/）且 E5 無 ledger 指針 | advisory 記錄 |
| 21 | DEF-200-222 列上解鎖條件不可機械查、與 playbook 判定矛盾 | advisory 記錄（下輪二擇一改寫） |
| 22 | DEF-200-212 機制蓋好列未更新 | 複審改判：**不結案**——②已修①未接線（main():469），列改 open（交由R114）；--self-test 16 PASS rc=0 保留為①函式面證據（§3、R3 複審 B1） |
| 23 | MIN_TESTS=3735 屬中途值（複審後如有增減須再釘） | HANDOFF 交代 |
| 24 | R1-a：`_STRUCTURAL_DEBT_MAX_ROWS` 無 frozen 影子、無鬆弛偵測（調大不紅） | advisory 記錄，Windows 輪補雙邊咬人棘輪 |
| 25 | R1-b：DEF-101-960 token 自述「需Windows實機」與外部軌枚舉語意重疊 | advisory 記錄，14 天複查時重議軌別 |
| 26 | R1-c：裁決文「外部授權」vs 落地文「內部授權」詞面相反（所指相同） | advisory 記錄，playbook 分類表補對映註記（下輪） |
| 27 | R1-d：P1 級列（886）進長債軌後僅 14 天 warn 級複查 | advisory 記錄，HANDOFF 排具名複查 |
| 28 | R1-e：`_PHASE2_REVIEW_LOG` (113,[提案]) 列內未指名提案檔名 | advisory 記錄，DEF-200-211 承接時補 |
| 29 | R1-f：`.claude/settings.unattended.json` 實作批須同步納 block_destructive_git 保護面＋測試 | advisory 記錄，已屬 PRD 實作批義務（Windows 輪） |
| 30 | R3-4：701 吸收 746、886 吸收 214/217 的併入關係只在長債軌登記備注，主帳本無反向指標 | advisory 記錄，下輪確認可查性 |

## §6 護欄層 R113 重釘對帳

- 淨額：89452 → 89592（**+140** < 每輪上限 585；streak 第 1 輪／上限 2）。逐檔：test_check_defect_log_crossref.py 3794→3906（+112）、test_defect_id_reference_integrity.py 274→281（+7）、test_adr_xplat001_c1c2_lock.py 6391→6412（+21）
- 到期義務兌現：`_REPIN_NET_CAP_SCHEDULE` 追加 `(113, 585)`（R111 預先武裝的既定值）；同輪重新武裝 `(115, 577)`——步伐 8 < 前一段的 10，續守「步伐刻意變小」
- Phase2 五輪時效：`_PHASE2_REVIEW_LOG` 追加 `(113, "[提案]", …)`，引 ADR-XPLAT-013_Phase2_Proposal_R108.md 與掌舵者「三方向全做」既存裁決
- 逐列超標豁免自動收緊（DEF-101-018 縮身跌破 700 觸發）：`OVERSIZE_ROW_CEILING` 44→43、`OVERSIZE_ROW_EXCESS_CEILING` 34712→27682；ledger_rotation 兩條 `*_HISTORY` 追加＋封印延長＋`_SEAL_TABLE_SHA256` 重算
- MIN_TESTS 同行重釘 3631→3735＋`sync_onboarding_baselines.py --write` 回填
- guard-total 標記：`<!-- guard-total:R113 -->` 落 CrossPlatform_R106_Scan_Findings.md（寄居判例）＋AutoSDD_improving_112.md 兩相異檔

## §7 收尾單人窗口處置記錄（2026-08-31 回填）

1. ✅ `python3 tools/check_handoff_carriers.py --self-test` → 16 PASS、rc=0（全文 §3）
2. ✅ `python tools/check_defect_log_crossref.py` → rc=0；殘留待辦 warning=0；未結 54（212 改判回 open 後）；治理文件雙向核對通過
3. ⏳ `python -m unittest tools.tests.test_check_defect_log_crossref -q`（本檔落盤＋governance 登記後重驗）
4. ⏳ 四方複審（範圍＝本輪全部狀態欄改動＋回歸鎖 diff＋Phase2 [提案] 議程）
5. ⏳ R113_HANDOFF.md（含呈報單：暫存清單 #11）→ 全套閘門（最後寫文件之後）→ commit → push（timeout 480000ms+）→ 等雲端 CI completed
6. 禁止事項：不准 `--no-verify`；不准 AUTOCLAUDE_SKIP_HOOKS；不准調高任何棘輪常數換綠

## §8 喚醒鏈實戰事件（2026-08-30 深夜；mac 首次四段全通的實戰樣本）

| 時刻（台北） | 事件 | 證據 |
|---|---|---|
| 23:39~23:40 | 文件批實作包撞 429（session limit，reset 00:10），主控行程隨之死亡 | 429 通知 req_011CeZBCLDtZ7SehvX7ixizg；bootout log `parent-gone 2026-08-30T15:40:48Z` |
| 23:40 起 | 哨兵偵測 parent-gone → 自我重掛 → 巡邏偵測未處理撞線 → arm_reset 武裝於 00:10 | `~/.autosdd/traces/autosdd_sentinel_launchd_…8da09c11….log`「arm_reset…觀測 reset=2026-08-31 00:10:00+08:00」×3 |
| 00:10:50 | 哨兵醒來 → 探針確認額度恢復（`探針 rc=0 kind=none open=True`）→ 判定 resume | 同上 log「判定 resume：探針通過＝額度已恢復」；bootout log `2026-08-30T16:10:50Z` |
| 00:10~00:31 | 無頭續跑本 session：完成噪音 3 列清理、playbook 落款、外部軌複查日、212 列改寫；Write 新檔全被無人核准權限牆擋（含 scratchpad 任務書）→ PushNotification → 留交接總結於逐字稿後收手 | 本 session 逐字稿 16:10Z~16:31Z 段；工作樹 diff（未越權、零 commit） |
| 00:31 之後 | 交接總結只存在於逐字稿與一則推播，使用者終端無任何可見回饋；直到掌舵者 2026-08-31 手動回訊才續上 | 掌舵者 2026-08-31 訊息（自陳被消耗 9% 且不知情） |
| 00:32:42 | 續跑結束後哨兵 bootout、**無後續 bootstrap**＝開火一次即死，喚醒鏈自此斷線 | bootout log 第 9-10 行 `parent-gone 2026-08-30T16:32:42Z`／`bootout rc=0` 之後無 bootstrap 行 |
| 08-31 上午 | `--pace` 自報「armed stamp 說已武裝、排程器現查卻沒有這支工作 ⇒ 哨兵已死、喚醒鏈斷線」；收尾窗口手動 `--arm-sentinel` 復活 | 憑證＝`launchctl print rc=0`＋interval 900s＋plist 持久化＋argv 7 項逐項回讀相符 |

判定：喚醒鏈「偵測→武裝→喚醒→續跑」四段全通（mac 首次實戰全通，推翻「mac 從未成功」的先前認知），敗在最後一哩四缺口——①無頭窗口權限姿態（連任務書都落不了盤）②交接可見性（使用者無感）③續跑單回合即止、無配額內自循環④哨兵不自癒（fire-once 即死，見上表 00:32 與 08-31 兩列）。①②③對應帳本 DEF-200-234/235/236（R112 喚醒鏈修憲案 Proposed），④併 DEF-200-234 的哨兵巡邏機制承接；工程化設計見 PRD_Amendment_R113_WakeChain_LastMile.md §3（G1~G4），落款軌＝AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md 修憲程序與 R113_HANDOFF。
