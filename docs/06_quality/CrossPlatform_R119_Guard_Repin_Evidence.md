# R119 — P1-6 護欄層淨額收斂證據檔

- **輪籤**：R119（單一實作包，串行）
- **範圍**：P1-6——「新增平台專屬 skip 要四層齊補、漏一層紅一輪」的結構解（R115 red-4 同型
  漏補：commit `7f8c96a` 補齊 skip 天花板①②③三張表的平台互補上修，卻漏補第四層 M6 落款
  `docs/06_quality/skip_id_ledger.json`，直到下一個 commit `5d5dd37` 才補上；詳見
  `docs/04_planning/R118_HANDOFF.md` 的 P1-6 節）。

## §1 落地形態：共同變更鎖（co-change lock）

四層座標、已否決形態（層與層互相派生／「① 總和 vs ④ 列表長度」靜態互查——後者判準是
`total_got > total_cap` 的上限語意，漏補只會讓 ④ 更小，對目標痛點恆綠）已由 R118_HANDOFF.md
的 P1-6 節定案，本輪不重複。落地物件：

- `tools/tests/test_skip_ceiling_ratchet_direction.py::skip_ledger_co_change_problems()`
  ——純函式判準：`changed_paths`（repo 相對 posix 路徑清單）若含
  `tools/lib/skip_group_policy.py`／本檔自己（①②）任一，`docs/06_quality/skip_id_ledger.json`
  （④）也必須在同一份清單裡，否則回問題清單。
- `tools/tests/test_skip_ceiling_ratchet_direction.py::_origin_main_head_diff()`
  ——取數半邊：`git diff --name-only` 介於 `merge-base(origin/main, HEAD)` 與 `HEAD` 之間。
  比較基準選 `origin/main`（而非工作樹 vs HEAD）：後者只在 commit 前有鑑別力，一旦 commit
  完成即恆綠；`origin/main..HEAD` 涵蓋「本次 push 要帶出去的全部 commit」，命中的正是
  R115 red-4 實際發生的窗口（commit 完 `7f8c96a` 之後、push 之前）。誠實劃界：CI
  （`windows-compat-ci.yml`／`macos-compat-ci.yml`）是 push 事件之後才觸發，該函式在 CI
  上結構性 no-op（HEAD 此時已是新 origin/main 本身）；真正的執行點是本機 pre-push
  （`tools/git-hooks/pre-push` 在 push 前呼叫 `tools/run_root_unittests.py`）。
- `TestSkipLedgerCoChangeLock`（同檔）：四格反事實（動工前必做的證偽）＋一支生產接線
  wiring 測試。

## §2 反事實四格實測（動工前的證偽，證明鎖有牙）

以 commit `7f8c96a`（R115 漏補④）／`5d5dd37`（補回④）的真實檔案集合重演：

| 餵入 | 預期 | 實測 |
|---|---|---|
| `7f8c96a` 單獨（①②，未動④） | 紅 | `test_skip_ledger_co_change_catches_the_r115_red4_commit_alone` PASS |
| `7f8c96a` ∪ `5d5dd37`（①②③④全到齊） | 綠 | `test_skip_ledger_co_change_is_clean_once_the_ledger_joins` PASS |
| 只動④ | 綠 | `test_skip_ledger_co_change_allows_touching_only_the_ledger` PASS |
| 完全無關的變更 | 綠 | `test_skip_ledger_co_change_has_zero_crosstalk_on_unrelated_files` PASS |

```
python -m pytest tools/tests/test_skip_ceiling_ratchet_direction.py -q -rs
...........
11 passed in 0.30s
```

## §3 compat-CI paths 覆蓋

`skip_group_policy.py`／`skip_runtime_report.py` 兩檔本輪前已在 `windows-compat-ci.yml`／
`macos-compat-ci.yml` 的 push／pull_request paths 中（各檔 4 處：push+pull_request ×
windows+macos）；本輪未新增任何根層生產檔 import，`AISDLC_SDD/scripts/tests/
test_ci_paths_cover_root_consumers.py` 全綠（49 passed），無需改動 paths。

## §4 護欄層淨額收斂（自身編修的自指問題）

`test_adr_xplat001_c1c2_lock.py` 的 `_FROZEN_GUARD_LINES` 表含**本檔自己**：追加落款列時，
落款文字本身又會改變本檔行數，需要後續列吸收自身編修的殘差；本輪另外撞上
`_REPIN_NET_CAP_DUE_ROUND=119`（早於本輪存在的到期義務，本輪落款後 `current_round` 一到
119 就必須兌現）與 `_FROZEN_PREFIX_REWRITE_LEDGER`（凍結前綴指紋每變一次都要留一筆協同
改寫痕跡，DEF-ID 須真的存在於缺陷帳本），逐輪收斂後 R119 落地五列（第一批兩列為
P1-6 本體落地；第二批三列為 §6 全套背景跑覆審揪出真違規後的修復追記）：

1. `("R119", 91247, 91384, 137, ...)`：P1-6 落地（`test_skip_ceiling_ratchet_direction.py`
   165→302，+137）。
2. `("R119", 91384, 91402, 18, ...)`：本表自身編修（新增上列稽核列＋本列自身＋凍結表值
   同步＋`_REPIN_NET_CAP_SCHEDULE` 到期義務兌現列 `(119, 564)` 與重新武裝註解＋
   `_FROZEN_PREFIX_REWRITE_LEDGER` 新列，`test_adr_xplat001_c1c2_lock.py` 7122→7140，+18）。
3. `("R119", 91402, 91410, 8, ...)`：§6 修復一（subprocess encoding，
   `test_skip_ceiling_ratchet_direction.py` 302→304，+2）＋本表自身編修（+6：7140→7146）。
4. `("R119", 91410, 91417, 7, ...)`：`_FROZEN_PREFIX_REWRITE_LEDGER` 第二筆協同改寫列＋
   本表值同步（本檔 +7：7146→7153，此列本身 append 之後又反噬 +7，已一併吸收）。

淨額 91247→91417（+170），R119 上限＝`net_cap_for_round(119)`＝570（現查，R118 淨額 -6
已終止上升 streak，本輪允許正淨額）。全額歸功能軌（`[全額功能軌]` 標記，見主表理由欄）
——本輪工作是新增治理鎖，非驗收既有 PRD/ADR 指定的回歸測試，不進 `_REGRESSION_LANE_LOG`。

同輪兌現到期義務：`_REPIN_NET_CAP_SCHEDULE` 追加 `(119, 564)`，cap 570→564；同輪重新武裝
下一段到期輪 R121、目標 559（步伐 5 < 前段 6，續守「步伐刻意變小」）。凍結前綴協同改寫
帳本追加**兩列**（`("R119", "862ff00ae26d", "7f11c682ae08", "DEF-200-240")` ＋
`("R119", "7f11c682ae08", "21bdbf9b9595", "DEF-200-240")`），載體 DEF-200-240
為本輪新立（`docs/06_quality/AutoSDD_Defect_Log.md`，發現情境欄依既有慣例標「本欄刻意
零輪號＝不推當前輪時鐘」，避免把 `current_round()` 由 100 誤推高到 119 而引爆
ADR-XPLAT-002 §6 逐輪覆蓋表的 SC-10 連鎖義務——這是本輪實測踩到、後改正的一個岔路）。

文件側「護欄層累積總量」對帳（`doc_guard_total_problems()`，min_sites=2）：markers 落在
`docs/06_quality/CrossPlatform_R119_Scan_Findings.md`（新建，短索引＋marker）與
`docs/04_planning/R119_HANDOFF.md`（新建，本輪交棒書），兩份皆已登記進
`tools/lib/governance_docs.py::_GOVERNANCE_DOCS`（治理文件涵蓋面體積守門＋
`archive_defect_log.py` 指針稽核）。

## §5 全套背景跑揪出的兩筆真違規（非設計缺陷，是實作疏漏）

第二輪全套 `python tools/run_root_unittests.py`（`Ran 3854 tests in 690.226s`／
`FAILED (failures=4, skipped=42)`／`rc=1`）揪出：

1. **`docs/04_planning/R119_HANDOFF.md` 對 `TestR78HandoffClaimsCarryLiveCommands` 零射程**
   （2 筆失敗＋1 筆下游連鎖失敗）：該鎖要求「最新一份交棒書」至少收得到一筆帶現查指令的
   stale 宣稱（`_HANDOFF_STALE_WORDS`＝「尚未／還沒／仍缺／未執行／沒跑／未推送／仍未」，
   節標題需含 `_HANDOFF_SECTION_WORDS`），本輪初版只有「已驗證」「下一步」「禁止事項」三節，
   零命中。修法：補「## 還沒做的」節，沿用 R118_HANDOFF.md 既有未結項（DEF-200-212／
   P1-7／P1-8）逐條帶 `git grep` 現查指令。連鎖：`TestR67R3ThisFileMakesNoUnstatedPlatformAssumption`
   把整個姊妹套件在模擬 `sys.platform` 下重跑一次，此問題在 darwin 模擬下也會現形，修好
   根因後一併轉綠（獨立驗證：`Ran 1 test in 109.849s` / `OK`）。
2. **`_origin_main_head_diff()` 兩處 `subprocess.run(text=True)` 缺 `encoding=`**
   （`test_subprocess_encoding_hygiene.py:585`）：Windows 非 UTF-8 codepage 下讀取 git
   輸出可能 `UnicodeDecodeError`／亂碼。修法：補 `encoding="utf-8", errors="replace"`。

兩筆修復後獨立覆核：`TestR78HandoffClaimsCarryLiveCommands`（7 passed）、
`test_repo_trees_have_no_unencoded_text_subprocess`（1 passed）；六檔合併重跑
`792 passed, 310 subtests passed`。**第三輪全套背景跑（最終驗證，含 ci-gate＋
AutoClaude pytest 分鐘級子階段的完整合併重跑）：`Ran 3854 tests in 679.864s`／
`OK (skipped=42)`／`rc=0`。全綠。**

## §6 驗證指令與結果

```
python -m pytest tools/tests/test_skip_ceiling_ratchet_direction.py -q -rs
  ⇒ 11 passed

python -m pytest AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py -q -rs
  ⇒ 49 passed

python -m pytest tools/tests/test_negative_existence_claims_r82.py tools/tests/test_check_defect_log_crossref.py tools/tests/test_skip_ceiling_ratchet_direction.py tools/tests/test_adr_xplat001_c1c2_lock.py tools/tests/test_subprocess_encoding_hygiene.py tools/tests/test_doc_loc_baseline_freshness_r60.py -q -rs
  ⇒ 792 passed, 310 subtests passed

python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
  ⇒ 淨額 91417→91417 (+0)、逐檔漂移 0 支

python tools/check_defect_log_crossref.py            ⇒ rc=0
python tools/archive_defect_log.py --check            ⇒ rc=0
python tools/check_handoff_carriers.py                ⇒ rc=0
python AutoClaude/tools/check_loc_budget.py --json    ⇒ rc=0（total=17107 ≤ cap=20438）
```
