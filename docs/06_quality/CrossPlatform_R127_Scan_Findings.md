# R127 落地輪 — 護欄層淨額承認

> **性質**：本輪不是掃描輪。本檔承擔 `repin_log_problems()` 款(9) 強制的**護欄層累積淨額承認**
> （下節的 `guard-total` 標記行，與 `_GUARD_LINES_REPIN_LOG` 表尾雙向對帳，寫錯即紅）、回歸鎖軌
> 分流申報的對帳、U9 勘查座標，並記下落地過程中順手撞到但不屬本輪射程的發現。逐筆結案取證在
> `CrossPlatform_R127_Debt_Closure.md`。
> **體例**：不使用「延後到R／交給R／留給R／承接輪次：R」等前瞻輪號句型。

---

## §1 護欄層累積淨額承認

<!-- guard-total:R127 --> 本輪護欄層行數 `92306→92268`（淨額 −38）。

| 列 | 起 → 後 | 淨額 | 性質 |
|---|---|---|---|
| 1 | 92306 → 92268 | −38 | 主表單列：`DEF-200-133` 回歸鎖（+159，全額申報於 `_REGRESSION_LANE_LOG` R127 列）＋三支鎖檔散文搬遷抵銷（doc_loc −165、cbg −42、quota_policy −10，含 `DEF-200-260` helper 合併）＋鎖檔自身重釘與 U9 展延（+20） |

**回歸鎖軌分流**：`_REGRESSION_LANE_LOG` R127 列宣告 159（＝`test_doc_loc_baseline_freshness_r60.py`
新增的 `DEF-200-133` 判準純函式與測試類別，記帳誠實度分類）；D-6 上限 309 未撞。主表淨額本身已
≤ 0，「子項不得大於母項」那一款對母項 ≤ 0 不判。
**款(11)**：主表 −38 ≤ 0 ⇒ 連續上升 streak（R123 +322、R126 +316 為第 1／第 2 輪）歸零。
款(10)：未撞（上限 555）。款(12)：到期輪 128／目標 552 尚未到（現查輪 127）。
**落地過程自我抓包**：第一版只搬 cbg／quota_policy 兩檔、主表 +127，靠回歸鎖軌宣告 159 讓「功能軌」
轉負——鎖檔自身的真表測試 `test_the_real_repin_log_stays_inside_the_cost_envelope` 對真表**不吃分軌**
（呼叫 `repin_growth_problems()` 未傳 lane）而判 `[只升不降]` 三連紅；分軌申報又被款 3「子項不得大於
母項」擋下。改為再搬 `test_doc_loc_baseline_freshness_r60.py` 十四段沿革散文（−165）讓主表真的 ≤ 0，
兩道鎖都綠——「款(11) 的合法出口只有主表淨額 ≤ 0」在真表上仍是硬規則，分軌只在 `repin_log_problems()`
那條路生效（見 §2 第 7 點）。

**逐檔漂移**（`--print-guard-lines` 實測，最終收斂為零漂移）：

| 檔 | 前 → 後 | 來源 |
|---|---|---|
| `test_doc_loc_baseline_freshness_r60.py` | 7131 → 7125 | `DEF-200-133` AST import 判準＋測試（+159，回歸鎖軌）；沿革散文十四段搬出（−165） |
| `test_context_budget_guard.py` | 9902 → 9860 | 散文搬遷八段（−）＋`DEF-200-260` `_tmpdir` helper 合併既有 addCleanup 行（−）＋helper 與 `TmpdirHygieneTest`（+） |
| `test_quota_policy.py` | 3406 → 3396 | 散文搬遷三段 |
| `test_adr_xplat001_c1c2_lock.py` | 7278 → 7298 | 本輪重釘儀式自身（主表列、回歸鎖軌列、指紋鏈列）＋U9 到期輪展延理由 |

`DEF-200-206` 的回歸鎖落在 `AutoClaude/tests/`，不計入本層。

---

## §2 途中發現（不屬本輪射程，記下不展開）

1. **R121 裁決卡的設計指針指向不存在的節**：`AutoSDD_Adjudication_Packet_R121.md:448` 寫「設計見
   `CrossPlatform_R121_Debt_Closure.md §DEF-200-206`」，該檔對 `206` 零命中；本輪改以設計卡＋三方複審為據。
   同型：帳本 `DEF-200-206` 列與 R121 裁決都寫「④ 見 §D-11」，而 §D-11 只有 ①②③。**裁決文字引用的座標
   也要現查**，不是只有帳本字面。
2. **`QueueOutcome.listed_only` 同時承載兩種語意**（SD 鏡）：`ABORT`（拒絕啟動）與 HUMAN_REVIEW／DRAINING／
   DRY_RUN（只登記）都放 `listed_only`，只靠 `problems` 分得開；今天唯一消費者 `boot_self_check()` 有正確聚合，
   未來只讀 `listed_only` 的呼叫端會誤讀。候選＝加顯式欄位（如 `aborted: bool`）。
3. **兩支 tools/tests 鎖檔的可搬散文已近枯竭**：`[他包回報]` cbg 全檔可搬僅約 57 行（低＋中風險）、
   quota_policy 約 25 行；前幾輪（R89／R95／R104／R122）已把大段沿革搬走。下一輪若還要靠搬遷抵銷，
   要換到尚未搬過的鎖檔（`test_platform_neutral_paths.py` 5720、`test_check_defect_log_crossref.py` 3891、
   `test_doc_loc_baseline_freshness_r60.py` 7290 為候選）。
4. **`Measure-Object -Line` 不計最後一行**：`[他包回報]` 勘查員用它讀 cbg 得 8578、實際 9902，改 `.NET
   ReadAllLines` 才對；R118 記憶已有同型（不計空行）。取行數一律用 Read／`--print-guard-lines`。
5. **Stop 稽核器把治理檔 non-blocking 提醒歸「載具失敗」**（R122／R123／R126 同型，第四度復現）：本輪編輯
   `quota_gate.py` 以外的治理面亦觸發；仍未入帳本（與前三輪同一判斷：純訊息分類，零機械後果）。
6. **`Workflow` 工具在 weekly_scoped 進 converge 帶時被 `context_budget_guard` 整支擋下**（「數不到」不是「太多」）
   ⇒ 本輪全程改逐一 `Agent`（每 300s ≤3）。這是設計行為，記在此供下一輪派工前預期。
7. **回歸鎖軌分流對「真表」測試無效**：`test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet::
   test_the_real_repin_log_stays_inside_the_cost_envelope` 呼叫 `repin_growth_problems(_GUARD_LINES_REPIN_LOG)`
   不傳 `regression_lane`，而 ADR-XPLAT-013 Phase 2 (b)（R116 落地）只把分軌接進 `repin_log_problems()`
   那條路 ⇒ 真表上款(11) 的唯一出口仍是主表淨額 ≤ 0，分軌宣告只影響閘門路徑。這是 R116 落地時漏
   更新的一支測試（兩條判準對同一張表給不同答案），本輪**刻意不改那支測試**（改它＝為讓紅變綠放寬
   判準），改用真搬遷達標；是否要讓該測試也吃分軌屬設計裁決，記於此不當場展開。
8. **`test_doc_loc_baseline_freshness_r60.py` 的沿革散文本輪已搬十四段**（−165），上方第 3 點的候選清單
   應改讀為 `test_platform_neutral_paths.py`／`test_check_defect_log_crossref.py`。

---

## §3 U9 舊尺勘查座標（`[他包回報]`，供真拆窗口直接消費）

舊尺 over_by（本輪親量）：`quota_gate.py` 90／`quota_meter.py` 67／`hook_wiring.py` 28／`session_resume_planner.py` 0。

**`tools/lib/quota_gate.py`（docstring 內可搬段，行號＝勘查當下）**：模組 docstring 3-15、17-20、22-25、27-37、
39-45；`quota_cache_path` 257-261；`core_signature` 309-317；`draining` 482-489（🔴 high：「沒量到卻宣稱量到」
逐字見 `test_quota_policy.py:1525`）；`degraded_posture` 600-604；`note_degraded` 621-625；
`refresh_quota_blocking` 667-679。低＋中風險合計約 76 行，略低於 90；放寬到 3 行段落可再補約 15-20 行。

**`tools/lib/quota_meter.py`**：`_keychain_token` 215-218；`token_detail` 309-314、316-324（🔴 high：具名
`MeterFailureShapesTest`）、326-331；`bucket_readings` 425-430（🔴 high：naive 時間戳句型與
`test_quota_policy.py:3288` 重疊）；`account_posture` 511-516（🔴 high：事故訊息字串住
`test_context_budget_guard.py:1043`／`check_claim_provenance.py:50`）、518-521、523-526（🔴 欄位名重疊）、
528-535（🔴 DEF-200-114 廣泛互引）、536-544、546-557（🔴 與 `test_context_budget_guard.py:8799`／
`test_quota_policy.py:1983` 重疊）；`fetch_usage` 605-610；`retry_after_at` 672-676（medium：與根 CLAUDE.md 準則
同句）；`rate_limited_reading` 712-715、717-727；`measure_detail` 746-750、752-757。低＋中合計約 66 行（差 1 行
覆蓋 67）。

**`tools/lib/hook_wiring.py`**：零段——全檔 docstring 皆單行摘要，沿革全住 `#` 註解（檔頭 4-13 行自述
「換載體省不到一行」指的是新尺；對舊尺而言 `#` 本就免費）。28 行超額只能靠真拆（抽共用模組）。
