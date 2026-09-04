# R126 落地輪 — 護欄層淨額承認

> **性質**：本輪不是掃描輪。本檔承擔 `repin_log_problems()` 款(9) 強制的**護欄層累積淨額承認**
> （下節的 `guard-total` 標記行，與 `_GUARD_LINES_REPIN_LOG` 表尾雙向對帳，寫錯即紅），並記下
> 落地過程中順手撞到、但不屬本輪射程的發現。逐筆結案取證在 `CrossPlatform_R126_Debt_Closure.md`。
> **體例**：不使用「延後到R／交給R／留給R／承接輪次：R」等前瞻輪號句型。

---

## §1 護欄層累積淨額承認

<!-- guard-total:R126 --> 本輪護欄層行數 `91990→92306`（淨額 +316）。

| 列 | 起 → 後 | 淨額 | 性質 |
|---|---|---|---|
| 1 | 91990 → 92286 | +296 | 全額功能軌：13 筆結案的回歸鎖落地（六支鎖檔） |
| 2 | 92286 → 92306 | +20 | 鎖檔自身重釘：`_GUARD_LINES_REPIN_LOG` 新列＋到期義務兌現列＋指紋鏈列＋旁註 |

款(10) 上限 559 未撞。款(11)：R123（+322）為連續上升第 1 輪、R124／R125 淨額 0 未記列，本輪為
**第 2 輪**——上限是 2 ⇒ **下一個結案窗口的淨額必須 ≤ 0**（合法出口＝史料搬遷抵銷／刪行／
合併鎖檔；先例 R122 `Guard Prose Migration`）。款(12)：到期輪 124／目標 555 在稽核痕跡未走到的
輪次到期，本輪是其後第一次重釘故就地兌現 `(126, 555)`，同輪重新武裝 `128／552`（步伐 3 < 前段 4）。

**逐檔漂移**（`--print-guard-lines` 實測，最終收斂為零漂移）：

| 檔 | 前 → 後 | 來源 |
|---|---|---|
| `test_check_defect_log_crossref.py` | 3858 → 3891 | `DEF-200-241` 判準①② 讀結案事實的回歸鎖 |
| `test_context_budget_guard.py` | 9835 → 9902 | `DEF-200-257` 等待窗方向鎖＋`DEF-200-137` PRD 邊際 |
| `test_quota_policy.py` | 3316 → 3406 | `DEF-200-244` gate_excluded＋`DEF-200-243` tightest 掃描鎖 |
| `test_smoke_ci_sync.py` | 1258 → 1353 | `DEF-101-951` skip 模組清單同步鎖 |
| `test_run_root_unittests.py` | 2422 → 2428 | `DEF-101-803` 具名 fail |
| `test_doc_loc_baseline_freshness_r60.py` | 7126 → 7131 | `DEF-200-247` 幽靈路徑基線一筆 |
| `test_adr_xplat001_c1c2_lock.py` | 7258 → 7278 | 本輪重釘儀式自身（含 `_FROZEN_PREFIX_REWRITE_LEDGER` 指紋鏈列） |

`DEF-200-217`／`DEF-200-263` 的回歸鎖落在 `AutoClaude/tests/`、`DEF-200-248` 的落在
`AISDLC_SDD/scripts/tests/`，不計入本層。

**分桶棘輪**：prose 桶一度實測 +41（新測試類別 `TestDef200241…` 的參照面只有 `docs/` 路徑 ⇒ 被
exclusive 歸屬丟進 prose 桶），在類別 docstring 指名受測模組 `tools/check_handoff_carriers.py` 後
歸回混合面，實測 4111（基準 4182，在 5% 容忍帶內、未觸發過時）。

---

## §2 途中發現（不屬本輪射程，記下不展開）

1. **`_loc_budget.json` 出現在 repo 根**：`AutoClaude/tools/check_loc_budget.py --json` 只印 stdout、
   不寫檔——該檔是本 session 早期把 stdout 重導向到檔名的手誤產物，曾被 `git add -A` 一併暫存；
   複審 Architect 鏡點名後已移除。教訓：收尾 `git add -A` 前先看 `git status`。
2. **`tools/tests/test_quota_policy.py` 的 `-k` 過濾會連帶把同一次呼叫裡別的檔案也 deselect**：
   本輪一次把 `test_logger.py` 與 `-k NoHarnessImport` 放同一句，導致 logger 測試一支都沒跑而
   摘要仍是綠的 `5 passed`；後補跑才抓到 `%r` 路徑雙反斜線的假紅。把「N passed」當驗證時要看
   deselected 數。
3. **舊乾淨 venv（`autoclaude_cleanvenv_20260827`）的 pytest 已損毀**（`No module named
   pytest.__main__`，site-packages 多個 `.pth` 掛掉），ONBOARDING 表② 回填改用新建的
   `autoclaude_cleanvenv_20260904`；ONBOARDING provenance 的 interpreter 欄已同步。
4. **`ruff check --config tools/ruff.toml` 與自動探索結果不同**（前者對同一批檔多報 49 筆存量
   E501）——R73 已判過「禁帶 `--config`」，本輪再踩一次後回到自動探索，記於此防下次。
5. **第一次全套三紅，全是收尾層的自我抓包**：① `TestRootToolsLintPolicy::test_e501_debt_only_shrinks`
   量的是**東亞寬度**（中文一字兩欄），ruff 自動探索全綠不代表這道棘輪綠——本輪新寫 11 行
   註解／斷言訊息超過 100 欄，逐行縮短文字（不折行，避免守衛線再重釘）後 61→61；② 刪
   `verify_token_guard_e2e.py` 連帶少一處 stderr reconfigure 站點，`_FROZEN_STDIO_FORCE_TREES`
   的 `AutoClaude` 格須同步 24→23（這是「刪除須同步的登記面」之一，R81 的「5 檔 7 處」估算
   沒點名它）；③ 到期義務兌現列的第二行提到 R124／R125 卻沒掛 `round-label-ok`——豁免逐**物理行**
   生效，多行註解每一行都要掛。
6. **Stop 稽核器把 `block_destructive_git.py` 對治理檔的 non-blocking 提醒歸成「本平台載具失敗」**
   （本輪 8 筆，皆為編輯 `quota_policy.py`／`quota_gate.py`／`quota_pace.py`／`context_budget_guard.py`
   時的「只出聲不阻斷」提醒）——與 R122／R123 途中發現同型，第三度復現，仍未入帳本；對應守衛測試
   本輪皆已親跑（quota_policy 261 passed、PrdDrain 5 passed、lock 檔 192 passed）。
