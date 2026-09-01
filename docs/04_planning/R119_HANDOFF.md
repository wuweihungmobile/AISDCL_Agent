# R119 單一實作包交棒書

- **輪籤**：R119（單一實作包，串行；接續 R118 收尾單人窗口）
- **範圍**：P1-6——「新增平台專屬 skip 要四層齊補、漏一層紅一輪」的結構解（見
  `docs/04_planning/R118_HANDOFF.md` 的 P1-6 節；R115 red-4 同型漏補：commit `7f8c96a`
  補齊 skip 天花板①②③三張表卻漏補第四層 M6 落款，直到 `5d5dd37` 才補上）。

## 本輪摘要

1. **P1-6 已落地**：共同變更鎖 `skip_ledger_co_change_problems()`／`_origin_main_head_diff()`
   （`tools/tests/test_skip_ceiling_ratchet_direction.py::TestSkipLedgerCoChangeLock`）。
   動工前先以 commit `7f8c96a`／`5d5dd37` 的真實檔案集合做反事實四格證偽（見
   `docs/06_quality/CrossPlatform_R119_Guard_Repin_Evidence.md` §2），確認鎖有牙才落地。
2. 比較基準取 `origin/main..HEAD`（非工作樹 vs HEAD）：理由與 CI fresh clone 上的誠實劃界
   見 `_origin_main_head_diff()` docstring。
3. `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` 全綠，未新增根層生產檔
   import，compat-CI paths 無需改動。
4. 守衛線重釘：淨額 91247→91417（+170），`net_cap_for_round(119)`＝570（現查），全額歸
   功能軌；同輪兌現 `_REPIN_NET_CAP_DUE_ROUND=119` 到期義務（cap 570→564）並重新武裝下一段
   （到期輪 R121、目標 559，步伐 5 < 前段 6）；凍結前綴協同改寫帳本追加兩列，載體皆＝
   `DEF-200-240`（本輪新立，記錄 R115 red-4 四層漏補與 P1-6 修復）。逐項見
   `docs/06_quality/CrossPlatform_R119_Guard_Repin_Evidence.md`。
5. 全套根層背景跑第一輪（rc=1）揪出真違規：`skip_tag_policy._SITE_CLASS_CENSUS` 站點普查
   漂移（已重釘 24→25）；第二輪（Ran 3854 tests, rc=1, failures=4）再揪出兩類真違規並修復：
   ① 本檔（當時尚無〈還沒做的〉節）在 `TestR78HandoffClaimsCarryLiveCommands` 下零 stale
   宣稱可查（已補本節，且連帶解掉 `TestR67R3ThisFileMakesNoUnstatedPlatformAssumption`
   的下游紅）；② `_origin_main_head_diff()` 兩處 `subprocess.run(text=True)` 缺
   `encoding=`（已補 `encoding="utf-8", errors="replace"`）。四筆逐一以目標測試檔覆核轉綠。

<!-- guard-total:R119 --> **守衛線追記：護欄層累積淨額＝ 91247 → 91646（+399）** ——
逐項見 `docs/06_quality/CrossPlatform_R119_Guard_Repin_Evidence.md`。

## 已驗證（本包親跑，非轉述）

- `python -m pytest tools/tests/test_negative_existence_claims_r82.py tools/tests/test_check_defect_log_crossref.py tools/tests/test_skip_ceiling_ratchet_direction.py tools/tests/test_adr_xplat001_c1c2_lock.py tools/tests/test_subprocess_encoding_hygiene.py tools/tests/test_doc_loc_baseline_freshness_r60.py -q -rs`
  ⇒ 792 passed, 310 subtests passed（四筆真違規修復＋round-label-ok 訂正後的最終合併重跑，
  含當初標紅的兩支鎖檔全套）。
- `python -m pytest AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py -q -rs`
  ⇒ 49 passed。
- `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` ⇒ 淨額
  91417→91417（+0）、逐檔漂移 0 支。
- `python tools/check_defect_log_crossref.py` ⇒ rc=0。
- `python tools/archive_defect_log.py --check` ⇒ rc=0。
- `python tools/check_handoff_carriers.py` ⇒ rc=0。
- `python AutoClaude/tools/check_loc_budget.py --json` ⇒ rc=0（total=17107 ≤ cap=20438）。
- 全套根層 `python tools/run_root_unittests.py`：
  - 第二輪（修復前）：`Ran 3854 tests in 690.226s`／`FAILED (failures=4, skipped=42)`／`rc=1`。
  - 四筆逐一覆核已轉綠：
    `TestR67R3ThisFileMakesNoUnstatedPlatformAssumption.test_every_lock_in_this_file_holds_under_every_simulated_platform`
    （獨立跑 `Ran 1 test in 109.849s` / `OK`）、
    `TestR78HandoffClaimsCarryLiveCommands` 全類（`7 passed`）、
    `test_subprocess_encoding_hygiene.TestSubprocessEncodingHygiene::test_repo_trees_have_no_unencoded_text_subprocess`
    （`1 passed`）。
  - **第三輪（修復後，本包最終驗證）：`Ran 3854 tests in 679.864s`／`OK (skipped=42)`／`rc=0`。**
    全綠，本包工作完成。

## 還沒做的（本包已全數完工；以下沿自 R118_HANDOFF.md，非本包射程，不塗綠）

1. **DEF-200-212 仍未結案**（承接自 R118，本包非其擁有者，未動）。現查
   `git grep -n "DEF-200-212" docs/06_quality/AutoSDD_Defect_Log.md`
   （狀態欄仍是未結字面＝仍未結案）。
2. **P1-7 的 SD-4 面仍未接線**（無主模式處置面 cap 收斂）。現查
   `git grep -n "cap_prepare" tools/lib/quota_escalation.py`（零命中＝仍未接）。
3. **P1-8 盤點仍未進行**（Pacing／BurnDown 落款後與現行實作的逐條差異）。現查
   `git grep -n "已由實作超越" docs/04_planning/PRD_Amendment_R108_Pacing.md`
   （零命中＝仍未盤點）。

## 下一步

本包（P1-6）工作與驗證皆已完工，全套三輪根層背景跑最終為 `rc=0`。下一步是主控 commit／
push（本包禁止自行 commit），或承接上方〈還沒做的〉任一項（皆非本包射程）。

## 禁止事項

- 不准 commit、不准 push（由主控執行）。
- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`。
- 不准調高任何 cap／天花板類常數（`_REPIN_ROUND_NET_CAP`／`_RUNTIME_SKIP_CEILING_MAX` 等）。
