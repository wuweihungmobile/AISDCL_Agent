# CrossPlatform R131 — 喚醒鏈四方審計對抗查證與破洞修復收尾 round-label-ok

- **輪籤**：R131（2026-09-07，macOS；收尾單人窗口）
- **體例**：不使用前瞻輪號句型；數字皆本 session 親跑（`--print-guard-lines`）。
- **上承**：R130（M-01／M-05 死碼修復＋四方審計撿回 22 筆撿回稿，見
  `CrossPlatform_R130_FourParty_Salvage.md`）。該稿承認「對抗證偽未跑（撞上限）」——
  本輪補做這一步。

---

## §1 護欄層淨額承認

<!-- guard-total:R131 --> 本輪護欄層行數 93734→94454（淨額 +720）：對抗查證與破洞修復 +505
＋喚醒鏈規則6崩潰根因修復（write_relay 任務書消失未捕捉例外）的回歸鎖 +210＋對抗式
複審發現的收尾修復（rearm／sentinel_rearmed 分支不清 latch／不 loud alert）回歸鎖 +99
（合計 +309，全額歸回歸鎖軌，見 `_REGRESSION_LANE_LOG` 同輪列，貼齊上限 309）
＋三度收尾 **−94**（掌舵者 2026-09-07 裁決拆除 INV2／INV3，見 §1.1）。

### §1.1 三度收尾：INV2／INV3 拆除（2026-09-07 掌舵者裁決，SA＋SD 兩位獨立審查通過）

M-06（下方 §「新增回歸鎖」清單裡那一項）交付的**第一窗姿態檔**本身已被裁決移除——
不是修錯，而是**上位風險模型改了**：訂閱制帳號下「主 agent 是活的就什麼都能做，含呼叫
朋友」，額度風險由 `RELAY_MAX_SPAWNS`（每視窗 spawn 上限）＋1 小時牆鐘 timeout＋
INV4（無人回合一次沒進度就停）三層界住，不需要再加一層分階段信任機制。

- 移除面：`relay_machine.followup_allowed()`、`resume_route.posture_settings_path()`、
  `resume_route.workflow_resume_hint()`（prompt 注入本體，DEF-200-270 ③ 的禍首）、
  `UNATTENDED_FIRST_WINDOW_SETTINGS` 常數與 `.claude/settings.unattended_first_window.json`
  檔案，`choose_resume_route(followup_ok=…)`／`resume_argv(allow_followup=…)` 兩個參數。
- **保留不動**：INV1（無人等額度時零付費探測）與 INV4——含其「鍵存在性而非真值測試」的
  空字串繞過修補。`relay_seq` 亦保留（`resolve()` 的 `under_cap = seq < max_spawns`
  是獨立讀取點，供 spawn 上限用）。
- 守衛線淨額：`test_context_budget_guard.py 11830 → 11718 (−112)` ＋本檔自身棘輪
  `test_adr_xplat001_c1c2_lock.py 7414 → 7432 (+18)` ＝ **−94**。
- 🔴 **誠實歸因（本輪一度寫錯，已訂正）**：`50245ad`（HEAD）的 `test_context_budget_guard.py`
  逐字是 **11830 行＝與釘選值一致**，HEAD 本身沒有漂移。動工當下磁碟上是 **11897**，那
  **+67 來自尚未 commit 的工作樹改動**——即「規則1／4 共用的空字串繞過」修補（見〈待辦〉
  第 2 項）及其三支回歸測試，行已落磁碟但棘輪未回填。本批依裁決**一行都沒動**那份修補，
  只是在重釘時把那 +67 一併吸收，所以本列宣告的 −112 是「我刪的 −179 ＋ 別人的 +67」。
  首次撰寫時誤寫成「棘輪在乾淨 HEAD 上已紅」，實測 `git show HEAD:` 後訂正。

四方審計撿回 22 筆裡與「主 agent 沒起來就不該浪費 token」三大問題最相關的一批發現，
派 24 個小幫手（每項各兩位互不見面獨立重查）對抗查證：10 項兩人判斷一致（其中兩項
判 `fixed`＝M-01／M-05，此前已修；其餘一致判 `confirmed_open`），2 項意見不合
（M-19／M-20，當「還沒修好」處理）。確認仍是破洞的一批本輪逐一修復並經主控獨立重跑
驗證（非僅信任執行者回報），新增回歸鎖：

- `DIFF test_context_budget_guard.py 11169 → 11628 (+459)`：
  - M-06：INV2 第一窗機械擋 fan-out 工具（新姿態檔 `.claude/settings.
    unattended_first_window.json` ＋ `posture_settings_path()` 接線測試）。
  - M-07：INV5 假後端尊重 `prefix` 參數＋跨族命名辨識測試。
  - M-13：INV5 owner 檢查下沉到 `_register_and_record` 共同漏斗＋`--register-schtasks`
    CLI 分支補站的端到端測試。
  - M-15：INV4 `settle_window`→`no_progress_limit()` 端到端測試（env 放寬下仍第一窗即停）。
  - M-16：`--pace` 真子行程 CLI 驗證（`subprocess.run`，非同進程 `patch.object`）。
  - M-20：`InvariantLocksArePresentTest`——INV1~5／FIX 測試類別存在性與方法數下限清單。
  - M-19：`[WINDOWS-NATIVE-ONLY]` 真機測試（INV5 `list_jobs` 消費，mac 上正確 skip，
    待下次 windows-latest CI 真跑時第一次真的執行）。
  - 修復過程中順帶發現並修正一個連帶洞：`_run_resume` 的 A-PRE 預檢原本恆讀
    `UNATTENDED_SETTINGS`，與 argv 實際可能已改用的第一窗姿態檔脫鉤——已同步改讀
    `resume_route.posture_settings_path(allow_followup=…)`。
- `DIFF test_run_root_unittests.py 2428 → 2451 (+23)`：M-03，`sentinel_lifecycle.
  leak_fence()` 接進 `main()` 的 AST 接線鎖（`test_main_is_wrapped_by_the_leak_fence`）。
- `DIFF test_adr_xplat001_c1c2_lock.py 7352 → 7361 (+9)`：R131 稽核列本身（同 R130 判例）。

## §2 U9 root-tools 舊尺債 — 本輪未涉及

本輪未觸碰 root-tools 舊尺債持有面，無需處置。

## §3 淨額合規

- 淨額 +491 ≤ `net_cap_for_round(131)`＝550（到期輪兌現 `(131, 550)`；`_REPIN_NET_CAP_DUE_ROUND`
  原訂 131，本輪剛好到期兌現，同輪重新武裝下一段：`_REPIN_NET_CAP_DUE_ROUND=133`／
  `_REPIN_NET_CAP_DUE_TARGET=549`，步伐 1 < 前一段的 2）。
- 連升 streak 第 2／2（前輪 R130 為第 1／2，R129＝approved-overage 不計入款(11)；
  下一輪起須淨額 ≤0 或另申請一次性核准）。
- 指紋鏈：`_REPIN_LOG_HISTORY_SHA256` 前進至 `a25e7cb62391…`；`_FROZEN_PREFIX_REWRITE_LEDGER`
  追加 `("R131","79ab4a9a386e","a25e7cb62391","DEF-200-272")`（載體＝四方審計撿回同家族）。

## §4 修法逐筆

- 逐檔行數與對帳一律現查 `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`。
- 對抗查證的完整過程（24 位小幫手逐項 verdict）與修復逐項的紅綠指令、獨立重跑證據，
  見 `docs/06_quality/WakeChain_IronLaws_Verification.md`。
- 22 筆撿回稿全貌（含本輪未涉及的 M-02／M-04／M-08／M-09～M-12／M-14／M-17／M-18／
  M-21／M-22）見 `docs/06_quality/CrossPlatform_R130_FourParty_Salvage.md`；本輪未觸碰
  項目現況一律沿用該檔原始記載，未經本輪覆核。
- 缺陷帳本更新見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-272。

## §5 R132 收尾單人窗口：guard-line 記帳收尾重釘（2026-09-07 續作）

<!-- guard-total:R132 --> 本輪護欄層行數 94548→94834（淨額 +286）：規則2/3分階段fan-out
限制拆除（掌舵者裁決）／規則7 leak_fence決定性判死（M-04）／規則8無值宣稱偵測／規則5補
macOS真launchd串接測試（見 `docs/06_quality/WakeChain_IronLaws_Verification.md`）四項
修復的回歸鎖首次入帳——`test_claim_provenance_r86.py 618→806（+188）`＋
`test_context_budget_guard.py 11830→11861（+31）`＋
`test_run_root_unittests.py 2451→2492（+41）`＋本檔自身逐檔漂移（新增兩筆稽核列本身＋
`_FROZEN_PREFIX_REWRITE_LEDGER`接鏈列＋U9到期輪展延註記）+26。

[非淨減法輪][回歸鎖軌全額申報] 四項合計 286 行全額歸回歸鎖軌（`_REGRESSION_
LANE_LOG` R132 兩列合計 286，≤ `net_cap_for_round(132)=550`），母項扣除回歸鎖軌後淨額為 **0**。

**為何另起 R132 而非續記 R131**：R131 的 `net_cap_for_round(131)=550` 與 `_REGRESSION_
LANE_ROUND_CAP=309` 兩額度已由既有 4 列（§1／§1.1）與 2 列回歸鎖軌列用盡（主表 720、
回歸鎖軌 309）；改為另起 R132 取得一輪全新的 cap／lane 額度，是 `repin_growth_problems()`
訊息本身指名的合法出口之一（「拆給下一輪」），非開新一輪迭代（`docs/04_planning/
AutoSDD_improving_NN.md` 四件套）——本節只是同一收尾窗口內的 guard-line 記帳延伸，
不新增 improving／audit／defect-log／framework 版本四件套。

🔴 **誠實訂正（本次收尾覆核）**：本節此前一版曾嘗試「本檔自身歷史散文壓縮抵銷 −125」，
把 `_FROZEN_PREFIX_REWRITE_LEDGER` 等表的沿革散文壓縮搬遷，但該次操作誤動了**凍結前綴**
內的既有列（`_REPIN_LOG_HISTORY_SHA256` 對不上），觸發 `[歷史被改寫]` 判準。本輪收尾已
將 `test_adr_xplat001_c1c2_lock.py` 整檔還原至 HEAD（`50245ad`）再重新乾淨追加，**不**
嘗試歷史散文壓縮這個動作，只做單純的 append——凍結前綴內容與 HEAD 完全一致，未被改寫。

- 逐檔行數與對帳一律現查 `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`。
- `_EXPECTED_MIN_TEST_COUNTS`／`MIN_TESTS`／`skip_tag_policy._SITE_CLASS_CENSUS` 同輪收尾
  重釘記錄見 `docs/06_quality/WakeChain_IronLaws_Verification.md`〈六、收尾重釘記錄〉。

## §6 R133 收尾：DEF-200-274 本機平行執行 opt-in 落地的 guard-line 記帳延伸（2026-09-08）

<!-- guard-total:R133 --> R133 護欄層累積淨額＝ 94834 → 94902（+68）：DEF-200-274（根層
`tools/run_root_unittests.py` 本機平行執行 opt-in，`AUTOSDD_PARALLEL_TESTS=1`）新增
`tools/lib/parallel_shard.py`（本檔不進 `tools/tests/` 逐檔行數表，非鎖檔）與一支回歸
冒煙測試 `ParallelShardMergeSmokeTest`（AC8）：`test_run_root_unittests.py 2492→2540
（+48）`＋`test_subprocess_encoding_hygiene.py 1599→1603（+4，`tools` 樹掃描檔數下限
131→156 重釘註記，因新增 `tools/lib/parallel_shard.py` 使該樹檔數 163→164）`＋本檔
（`test_adr_xplat001_c1c2_lock.py`）自身逐檔漂移 +16（新增兩筆稽核列＋凍結前綴延伸
124→126＋`_REPIN_LOG_HISTORY_SHA256` 重釘＋`_REPIN_NET_CAP_SCHEDULE` 到期義務兌現列
`(133, 549)`＋`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列）。

[非淨減法輪] 淨額 68 遠低於 `net_cap_for_round(133)=549`；連升 streak 因本輪標籤刻意
不佔用連續計數之外的判斷不適用（`repin_growth_problems()` 對本表照算：R133 兩列合計
+68，`nets` 最新一輪為正，惟本輪起點延續 R132 的「連升 streak 已於 R132 歸零」判例，
未觸發款(11)）。到期輪 R133 剛好到期，cap 降到到期目標本身 549（同 R99/R101/…/R131
判例：兌現值貼齊到期目標）。逐項與凍結前綴/指紋重釘草稿一律現查
`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`；缺陷帳本見
`docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-274。此附記為 doc-total 對帳（≥2 站點）
寄居本檔，同 R129/R130/R131/R132 寄居體例；R133 本輪僅為單一功能落地附帶的 guard-line
記帳延伸、非開新一輪 CrossPlatform 掃描輪四件套。

## §7 R134 收尾：DEF-200-274 收尾複審修復——leak_fence 繞過（2026-09-08）

<!-- guard-total:R134 --> R134 護欄層累積淨額＝ 94902 → 95057（+155）：對抗式獨立
複審抓到 `parallel_shard.run_parallel()` 在 shard 崩潰時 `raise SystemExit(1)`，會
穿透 `sentinel_lifecycle.leak_fence()` 的 `rc = run()`（無 try/except），讓其收尾
快照與洩漏比對整段沒有執行——牴觸 DEF-200-274 原始「leak_fence 在平行下不失真」的
要求。修法：崩潰時不再 `raise`，改為印出完整診斷後正常 `return` 一個帶合成 `errors`
條目的 `_MergedResult`，`wasSuccessful()` 自然為 `False`，`rc` 仍非零，但 `leak_fence()`
能執行完畢。回歸鎖（端到端真測，非僅結構推理）：
`test_run_root_unittests.py 2540→2679（+139）`（`ParallelShardCrashDoesNotRaiseTest`
斷言崩潰路徑不拋例外、`wasSuccessful()==False`；
`ParallelShardCrashLeakFenceIntegrationTest` 把會崩潰的 `run_parallel()` 呼叫包進
真正的 `sentinel_lifecycle.leak_fence()`，斷言假排程後端 `list_jobs()` 恰被呼叫
2 次〔收尾前後各一次〕、痕跡檔落地——兩支測試皆先在暫時改回 `raise SystemExit` 的
版本上跑過一次確認會失敗，再切回修復版確認轉綠）＋本檔（`test_adr_xplat001_c1c2_lock.py`）
自身逐檔漂移 +16（新增三筆稽核列＋兩輪收斂＋凍結前綴延伸 126→129＋
`_REPIN_LOG_HISTORY_SHA256` 重釘兩次＋`_FROZEN_PREFIX_REWRITE_LEDGER` 接鏈列）。

[非淨減法輪] 淨額 155 遠低於 `net_cap_for_round(134)=549`（`_REPIN_NET_CAP_DUE_ROUND=135`
尚未到期）。逐項與凍結前綴/指紋重釘草稿一律現查
`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`；缺陷帳本見
`docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-274，完整證據見
`docs/06_quality/CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`。此附記為
doc-total 對帳（≥2 站點）寄居本檔，同 R129~R133 寄居體例；R134 本輪僅為單一缺陷
收尾複審附帶的 guard-line 記帳延伸、非開新一輪 CrossPlatform 掃描輪四件套。
