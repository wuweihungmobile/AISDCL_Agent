# R99 — 護欄層行數棘輪重釘證據

- **日期**：2026-08-22
- **建立者**：R99 收尾單人窗口（多包並行收尾後的單人重跑窗口）

<!-- guard-total:R99 --> **本輪護欄層累積淨額＝ 85248 → 86097（+849）** —— 多包並行波
留下的既有成長（含本檔＝`test_adr_xplat001_c1c2_lock.py` 自身編修的逐輪追加共 +17 行）
加上收斂波四方複審對抗包一次修完的 +158（見下方新增段），再加上最後收尾窗口把
`test_doc_loc_baseline_freshness_r60.py` 的 +19 殘留漂移併帳（收斂為 +7，含本檔自身
編修，見下方〈收尾：殘留漂移併入重釘〉節），逐檔漂移詳見下方〈逐檔漂移〉表；本輪淨額
849 未超過該輪上限 850（`_REPIN_NET_CAP_SCHEDULE` 到期輪 R99 兌現值，餘裕僅 1），且
R98 淨額為 -439（已 ≤0），故不觸發 `[只升不降]`（`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`）。

## 觸發原因（逐檔漂移）

四個並行修復包在本輪各自新增回歸鎖，收尾單人窗口在全部包停工後一次重釘：

- `test_check_defect_log_crossref.py` +237 —— ADR 幽靈路徑／幽靈符號兩道新判準
  （`TestR81GhostPathClaims`／`TestR78GhostSymbolClaims` 的生產面）。
- `test_archive_defect_log.py` +162 —— `tools/archive_defect_log.py --repin-oversize`
  帳本逐列超標三常數（`OVERSIZE_ROW_CEILING`／`OVERSIZE_ROW_EXCESS_CEILING`／
  `OVERSIZE_ROW_GRANDFATHERED`）自動重釘的回歸鎖。
- 新檔 `test_guard_line_taxonomy_r99.py` +148 —— `tools/lib/guard_line_taxonomy.py`
  觀察模式回歸鎖（ADR-XPLAT-012 落地，Phase 1：只印不擋）。
- `test_quota_policy.py` +106 —— 額度門檻新判準回歸鎖。
- `test_ps_engine_ssot.py` +21。
- `test_adr_xplat001_c1c2_lock.py` 淨 **-8**（收尾者刪除已閉合的 `DEF-101-324` 基線
  豁免登記：ADR-XPLAT-011 §2 正式裁決後，帳本狀態欄已不再帶「凍結基線」與「wontfix」
  同格字樣，該列不再落入 ADR-XPLAT-001 §4.3.1；同步刪除 ADR §7〈未結落差〉表對應列，
  依該節自訂規則「閉合即刪，不留歷史狀態」）。

四包分別為：P1（機械物：`net_new_vs_closed_problems()`／`external_blocked_log_problems()`／
`tools/lib/oversize_repin.py`）、P2（文件／ADR：ADR-XPLAT-010／011／012 三份新 ADR）、
P3（雜項小鎖：`DEF-101-596`／`DEF-200-164`／`DEF-200-176`／`DEF-101-889` 等）、P4
（Windows-hooks）。逐筆 zero-trust 複驗紀錄見
`docs/06_quality/CrossPlatform_R99_Ledger_Closure.md`。

## 收斂波：四方複審對抗包一次修完（同輪追加）

上述收尾窗口之後，四方複審（Architect／SA／QA／稽核舵手 H1／H2）對抗包驗出兩個 QA
blocking 缺陷與若干機制缺口，單一收斂包一次修完，逐檔漂移 +158：

- `test_check_defect_log_crossref.py` +51 —— R-01（`NAMED_BLOCKER_SOURCE_RE` 改
  `fullmatch` 防「合法字首＋自由文字」繞過外部阻塞軌具名枚舉）／R-02（淨額棘輪
  fail-open 時補 stderr 警告，比照 `print_external_blocked_count` 的永遠可見設計）／
  R-09（CI 實際呼叫的無參數 `main()` 併印外部阻塞軌筆數），各附回歸測試。
- `test_adr_xplat001_c1c2_lock.py` +107 —— R-10：新增
  `frozen_prefix_rewrite_problems()`（`_FROZEN_PREFIX_REWRITE_LEDGER` ＋
  `_FROZEN_PREFIX_REWRITE_LAUNCH_SHA`），把「凍結前綴指紋改寫」的稽核錨點從
  同檔同 commit 的 `_REPIN_LOG_HISTORY_SHA256` 移到跨檔的缺陷帳本 DEF-ID 存在性檢查，
  堵住「改資料同時重釘」的協同改寫缺口（`[歷史被改寫]` 只防疏忽、不防協同動作）；
  附回歸測試與本列自身編修，同步重釘 `_REPIN_LOG_FROZEN_PREFIX_LEN`（42→43）／
  `_REPIN_LOG_HISTORY_SHA256`。

🔴 誠實記錄（落地當時）：同一時段 `test_doc_loc_baseline_freshness_r60.py` 另有 +19 行
既有漂移（ADR-XPLAT-012 §2.4 幽靈路徑登記，`_GHOST_PATH_BASELINE_CEILING` 17→18），非本
收斂包射程（未指派給本包的檔），故當時的重釘**不**涵蓋該筆——`_FROZEN_GUARD_LINES` 對該
檔的登記值暫留舊值，`test_the_line_ratchet_took_over_and_has_teeth` 在該筆併入前持續
顯示 +19 的殘留漂移，留待下一個收尾窗口一併重釘。**下一節即該收尾窗口的落地紀錄。**

## 收尾：殘留漂移併入重釘

上一節結尾言明的 +19 殘留，由本輪最後一個序列收尾窗口（工作樹上其餘並行包已全數停工）
處理，落地在 `_GUARD_LINES_REPIN_LOG` 的最後一列（`("R99", 86090, 86097, 7, …)`）。

### 幽靈路徑登記 WHY（`tools/tests/test_doc_loc_baseline_freshness_r60.py` 程式碼指標指向本節）

ADR-XPLAT-012 §2.4「幽靈路徑」回填段引用了一個**歷史上真的寫錯**的路徑（早期草稿誤寫、
審查抓出、v3 已訂正），供讀者核對「當時錯在哪」。這是「引用一個幽靈當反例」，不是
「宣稱一個幽靈」，但 `test_doc_loc_baseline_freshness_r60.py` 判準的反引號擷取器分不出
兩者。上一版曾改用〔方括號註記〕規避掃描，經 QA／H1／H2 一致判定為「對任何人都通用、
且完全不留稽核痕跡的繞過配方」而訂正：改回反引號＋走 `_GHOST_PATH_BASELINE` 表正式登記。

🔴 該段實際引用了**兩個**歷史錯誤路徑（`tools/lib/check_loc_budget.py` 與
`tools/check_loc_budget.py`），但只有前者需要登記——後者在本判準的多基準解析下會
**意外解析得到**（`path_claim_bases()` 含 `AutoClaude` 這個子專案基準，
`AutoClaude/tools/check_loc_budget.py` 恰好真實存在，於是「tools/check_loc_budget.py」
被判成子專案相對路徑而非幽靈）。這是本判準既有的寬鬆設計（多基準解析），非本輪引入；
硬塞進本表會讓 `test_the_baseline_is_not_stale` 立刻判 stale。天花板
`_GHOST_PATH_BASELINE_CEILING` 同步 17→18（同 R81 QA B-3 的 18→19 判例：擴掃描面才看見
的既有存量／新落地文件帶進的既有欠債皆可登記，不是「偷偷放寬」——`test_the_ceiling_has_
teeth` 在漲跌兩向都咬人，漲的方向只要求「當回合實測直接填入、寫明理由」）。

### 護欄層行數收斂（合法出口③：搬史料進證據檔）

`test_doc_loc_baseline_freshness_r60.py` 落地時原文帶上述 WHY 的完整散文（19 行：12 行
幽靈路徑段落註解 + 1 行登記 + 6 行天花板重釘註解），落在前一節重釘的 86090 基準之外
（RM1／RM2 兩包並行時序落差：RM1 先夭折於連線中斷，RM2 隨後才落檔）。依棘輪自己列的
合法出口③，本收尾窗口把上述散文整段搬到本節，程式碼側改為緊貼在登記行與重釘行上的
單行指標（各附 `round-label-ok` 具名豁免，且改用不掛長篇釋義的精簡形式以同時滿足
`tools/tests/` E501 存量債棘輪 `_E501_DEBT_CEILING=139`——首版指標行一度把過長行數
由 139 推到 143，經二次收斂折回 139）：刪散文 18 行，該檔淨額僅 +3
（新登記的 1 個必要幽靈路徑項目 + 2 行指標，7135→7138）。連同本檔
（`test_adr_xplat001_c1c2_lock.py`）自身新增本稽核列與 R-10 協同改寫錨點
（`_FROZEN_PREFIX_REWRITE_LEDGER`）逐檔漂移 +4（5480→5484），本列總淨額
+7（86090→86097）。

## 逐檔漂移

| 檔案 | 舊行數 | 新行數 | Δ |
|---|---:|---:|---:|
| test_adr_xplat001_c1c2_lock.py | 5363 | 5373 | −8（後續本檔自身編修另計 +17，詳見 `_GUARD_LINES_REPIN_LOG` 第二列） |
| test_archive_defect_log.py | 3846 | 4008 | +162 |
| test_check_defect_log_crossref.py | 3327 | 3564 | +237 |
| test_ps_engine_ssot.py | 933 | 954 | +21 |
| test_quota_policy.py | 2226 | 2332 | +106 |
| test_guard_line_taxonomy_r99.py（新檔） | 0 | 148 | +148 |
| test_check_defect_log_crossref.py（收斂波追加） | 3564 | 3615 | +51 |
| test_adr_xplat001_c1c2_lock.py（收斂波追加，R-10） | 5373 | 5480 | +107 |
| test_doc_loc_baseline_freshness_r60.py（收尾窗口併帳） | 7135 | 7138 | +3 |
| test_adr_xplat001_c1c2_lock.py（收尾窗口併帳，本稽核列＋R-10 錨點自身） | 5480 | 5484 | +4 |

<!-- guard-total:R99 --> 護欄層累積總量現值 **85932 → 86097（+165）**；逐項立案見
`docs/06_quality/CrossPlatform_R99_Ledger_Closure.md`，重釘稽核痕跡見
`tools/tests/test_adr_xplat001_c1c2_lock.py::_GUARD_LINES_REPIN_LOG`（草稿指令：
`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`）。
