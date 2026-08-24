# R102 交棒書（收尾單人窗口）

<!-- guard-total:R102 --> **本輪護欄層累積淨額（稽核痕跡合計）＝ 87784 → 88425（+641）**
——逐檔清單見 [`CrossPlatform_R102_Scan_Findings.md`](../06_quality/CrossPlatform_R102_Scan_Findings.md)。

- **輪次**：R102（與 R101 治理修憲並行進行；DEF-200-204 四方終審 4/4 `APPROVE_WITH_FIXES`
  於 R101 commit 之後由收尾單人窗口併入護欄層重釘）
- **性質**：收斂輪——把並行完成的 PRD §4.2.4 動態配速平穩性機制併入受監測樹，並修復
  該批工作暴露的三個跨檔案缺口（幽靈符號殘留引用、護欄層淨額未重釘、帳本輪次標籤超前）

---

## §1 已驗證什麼（逐字實測輸出 ＋ rc；不採信任何未附輸出的宣稱）

### 1.1 幽靈符號殘留引用（`test_quota_policy.py` docstring 誤指已改名的測試函式）

見主控交件回報逐字貼出的 RED／GREEN 輸出與 rc（
`tools.tests.test_doc_loc_baseline_freshness_r60.TestR78GhostSymbolClaims.test_no_new_ghost_symbols`）；
本檔不重複貼一份會漂移的複本。

### 1.2 護欄層重釘（DEF-200-204 功能成長 572 ＋ 本檔自身編修 16，合計 +588）

重釘後自我覆核（`--print-guard-lines`）：

```
# 淨額 88372→88372 (+0)
# 逐檔漂移 0 支（淨額為 0 時本行仍會說話——那正是 R79 補它的理由）
```

淨額 588 由 `_GUARD_LINES_REPIN_LOG` 兩筆 R102 列合計而來（572 + 16），逐檔清單見
`CrossPlatform_R102_Scan_Findings.md` §B。`net_cap_for_round(102)` ＝ 750，588 < 750，
未觸及款(10)；緊接 R101 一次性核准例外之後，連續上升計數在核准輪重置為零，本輪為
streak 第 1 輪，未觸及款(11)——無需 `_REPIN_APPROVED_ROUND_OVERAGE` 例外，
`net_cap_for_round()`／`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS` 等棘輪常數本體逐字未動。

### 1.3 帳本輪次標籤超前（DEF-200-204 程式碼多處自稱 R102，帳本當前輪原停在 R100）

實測發現：把帳本「發現情境」欄的當前輪正式推進到 R102（例如補一筆發現情境含 `R102`
的索引列）會**連帶**讓硬規則②（孤兒承接輪次，見 `DEF-200-204`）對 41 筆既有「承接輪次：R101」等舊列
同時轉紅——那是一次獨立的「推輪帳本維護」工作（同型前例：`DEF-200-106`），不是這批
散文標籤修復的射程。故本輪改採**同行具名豁免**（`round-label-ok`，同 R101 commit 對
自身 R101 引用的既有作法）：對 `tools/lib/quota_availability.py`／`quota_stability.py`／
`quota_boot_check.py`／`quota_gate.py`／`quota_ledger.py`／`quota_policy.py`／
`quota_policy_env.py`／`endurance_env.py`／`governance_docs.py`／
`session_resume_planner.py`／`test_quota_policy.py`／`test_context_budget_guard.py`
共 38 處提及 `R102` 的散文行逐一加上豁免標記，`current_round()` 本身維持 R100 不動。
另把 `DEF-200-204` 原列狀態欄改寫為 `fixed@R102`，誠實反映本輪實際交付與殘留
（H1 fixture 未落地、啟動自檢 60 秒佔位值待 P0 觀測資料校準），順帶讓未結列存量
由 97 降為 96。
<!-- absent-if: def test_h1_ -->（H2~H7 在 `test_quota_policy.py` 皆循
`def test_h6_…`／`def test_h7_…` 命名；H1 落地時比照同一命名慣例，此字面才會現身）

---

## §2 全檔總覽

```
python -m unittest tools.tests.test_quota_policy tools.tests.test_context_budget_guard tools.tests.test_adr_xplat001_c1c2_lock -v
python tools/check_defect_log_crossref.py
```

見主控交件回報逐字貼出的完整輸出與 rc；本檔不重複貼一份會漂移的複本（同
`_PHASE2_REVIEW_LOG` 一份知識一個家的紀律）。

---

## §3 還沒做什麼

- **H1 fixture 未落地**——H2~H7 已有回歸測試覆蓋，H1 的測試夾具本輪未補齊，已記於
  `DEF-200-204` 狀態欄，未另開新列（帳本未結列存量已逼近 warn 線，見
  `--unresolved-count` 現查）。
  <!-- absent-if: def test_h1_ -->（同 §1.3 註記：H1 落地時比照 H2~H7 的
  `def test_h6_…`／`def test_h7_…` 命名慣例，此字面才會現身）
- **啟動自檢 60 秒佔位值待校準**——`session_resume_planner.py` 的 H6／H7 目前為工程估計
  值，非量測值，待 P0 觀測資料回填後才能改為量測校準值。
- ADR-XPLAT-013 §7 的 U1~U7（四方獨立審查打勾）仍未執行，`R101_HANDOFF.md` §3 已承接
  至 R102，本輪窗口未觸碰（範圍外）。現查：
  `python -c "import pathlib; print(pathlib.Path('docs/04_planning/ADR/ADR-XPLAT-013-loc-pricing-assertion-only.md').read_text(encoding='utf-8').count('未進行'))"`
  應 > 0（U1~U4 逐列仍是「未進行」）。
- ~~🔴 既存失敗、非本輪造成：`TestPricingChangeExemptionExpiresOnItsOwn...`~~
  **已於本輪 push 收尾追加回合執行並訂正，見下方 §6**——此處保留刪除線是誠實記載
  本節初稿落筆那一刻**尚無人動手**，不是回頭假裝一開始就做完；不要因為看到下面
  §6 已經解決就誤刪這行、讓下一個讀者以為 §3 從頭就沒漏過這件事。

## §4 下一步的確切指令

```bash
python -m unittest tools.tests.test_quota_policy tools.tests.test_context_budget_guard tools.tests.test_adr_xplat001_c1c2_lock -v
python tools/check_defect_log_crossref.py
```

## §5 禁止事項

- 不准調整 `net_cap_for_round()`／`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`／
  `_REPIN_ROUND_CAP_SINCE`／`UNRESOLVED_ROWS_WARN`／`UNRESOLVED_ROWS_FAIL`／
  `ROW_MAX_BYTES` 等棘輪常數本體。
- 不准把 H1 fixture／啟動自檢佔位值的殘留另開帳本新列以外的方式悄悄結案（例如把
  `DEF-200-204` 狀態欄寫成完全體 `fixed` 卻不提殘留）。

---

## §6 push 收尾追加回合（context 重啟後續作，本輪真正的最後一段）

§1~§5 寫完當時 push 尚未重試；context 逼近上限先安全收斂、重啟 session 後才完成以下
三個 commit，一併記在這裡，避免下一輪讀者只看到 §1~§5 就誤以為 R102 在那裡結束：

| commit | 內容 |
|---|---|
| `6fea8a3` | 落地 `--repin-cap`／`--update` 四方裁決（`DEF-200-207`）＋修復連帶的
  `frozen_cap` 測試 fixture 與 `test_the_next_round_cannot_reuse_the_exemption`
  前提＋護欄層重釘 |
| `6d48a62` | `DEF-200-219`：`6fea8a3` 新增的 R102 註解漏帶 `round-label-ok`，補標後
  觸發 `test_e501_debt_only_shrinks`，拆行修復＋護欄層重釘一次到位 |
| `4845724` | `ONBOARDING.md` §7 表② 快照回填（`DEF-200-210` 再次觸發，因
  `6d48a62` 動到測試樹指紋來源檔） |

**push 最終狀態**（獨立驗證，非轉述）：`git fetch origin main` 後
`git rev-list --left-right --count origin/main...HEAD` = `0 0`，
`git rev-parse HEAD origin/main` 兩者逐字相同（`4845724...`）。10 個既有 commit ＋
本節 3 個，共 **12 個 commit 全部確認已同步 `origin/main`**。

**過程中的一次環境污染事故**：回填 ONBOARDING 快照用的乾淨 venv 建在
`AutoClaude/.venv-onboarding-clean/`（repo 樹內），未被 `.gitignore` 涵蓋，污染 6 支
全樹掃描型治理測試，已 `rm -rf` 清除，教訓記入 memory
`project_onboarding_baseline_needs_clean_venv.md`：下次乾淨 venv 一律建在 repo 樹外。

**尚未量測**：本次 push 觸發的雲端 CI（`macos-compat-ci`）結果——push 前最後一筆雲端
紀錄是 failure（`DEF-101-733` advisory，不影響本機 rc），這次 push 之後的雲端結果需
另外去 GitHub Actions 頁面查，本檔不代為宣稱。

## §7 承接至 R103（本輪確認仍未做，逐項現查指令）

1. **H1 fixture 未落地**（同 §3 第一項，未變）。
   <!-- absent-if: def test_h1_ -->
2. **啟動自檢 60 秒佔位值待校準**（同 §3 第二項，未變）。
3. **`ADR-XPLAT-013` 正式轉 `Accepted` ＋ §7 的 U1~U7 四方獨立審查打勾**——現查：
   `python -c "import pathlib; print(pathlib.Path('docs/04_planning/ADR/ADR-XPLAT-013-loc-pricing-assertion-only.md').read_text(encoding='utf-8').count('未進行'))"`
   應 > 0。這是 `DEF-200-207` 唯一還沒關的部分（E1/E3/E4 已在 §6 執行落地）。
4. **雲端 CI 本次 push 的結果未查**——見 §6 最後一段。
5. `DEF-200-209`（`.claude/hooks/`／`tools/` 缺 ruff `E701`/`E702` 閘門）、
   `DEF-200-211`（`ADR-XPLAT-013` Phase 2 (b)(c) 未開始）——本輪皆未觸碰，帳本原樣承接。
