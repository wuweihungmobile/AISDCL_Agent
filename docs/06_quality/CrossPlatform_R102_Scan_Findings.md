# CrossPlatform R102 — 掃描發現與逐檔清單（DEF-200-204 PRD §4.2.4 平穩性機制交付）

<!-- guard-total:R102 --> **本輪護欄層累積淨額（稽核痕跡合計）＝ 87784 → 88415（+631）**
——逐檔清單見下方〈§B 逐檔清單〉與〈§D DEF-200-218 逐檔清單〉。

- **輪次**：R102（與 R101 治理修憲並行進行，R101 先落地；本輪收尾單人窗口把 DEF-200-204
  的並行成果併入護欄層重釘）
- **範圍**：PRD §4.2.4 動態配速平穩性機制——可得性軸遲滯（`quota_availability.py`）、
  死區／變化率限制／最小停留時間（`quota_stability.py`）、啟動自檢（`session_resume_planner.py`
  接線）。四方終審 4/4 `APPROVE_WITH_FIXES`（無 REJECT），Fix 全數落地並複驗。
- **本檔性質**：`_GUARD_LINES_REPIN_LOG` 兩筆 R102 列逐字指名的「逐檔清單的家」（款(9)
  `[未附刪除清單]` 要求）。

---

## §A 立案事實：DEF-200-204 的交付與殘留

`docs/06_quality/AutoSDD_Defect_Log.md` 的 `DEF-200-204` 原列（R100 收尾窗口稽核）記載
「PRD §4.2.4 D 段遲滯（掛量測可得性軸）完全未實作：H1~H7 一格未動、
`AVAILABILITY_EXIT_STREAK`／`AVAILABILITY_MIN_DWELL_SECONDS` 兩鍵 grep 0 命中、新存取器
不存在」。本輪（並行於 R101 進行、於本收尾窗口併入護欄層重釘）新增
`tools/lib/quota_availability.py`（可得性軸遲滯狀態機與持久化）、
`tools/lib/quota_stability.py`（死區／變化率限制／最小停留時間）、`tools/lib/quota_boot_check.py`
（啟動自檢），並接線 `quota_gate.py`／`quota_ledger.py`／`quota_policy.py`／
`quota_policy_env.py`／`session_resume_planner.py`。四方獨立審查終審 4/4
`APPROVE_WITH_FIXES`，Fix 逐項落地（F1／F3／F5／F9／F14／F15／F16／F17／F19／F23／F24／F25
等審查意見）。

殘留（誠實記載，不隨本輪關閉一併結案）：
- **H1 fixture 未落地**——H2~H7 已有回歸測試覆蓋，H1 的測試夾具本輪未補齊。
- **啟動自檢 60 秒佔位值**（`session_resume_planner.py` 的 H6／H7）待 P0 觀測資料回填
  校準，目前為工程估計值，非量測值。

兩項殘留已記於 `docs/06_quality/AutoSDD_Defect_Log.md` 的 `DEF-200-204` 狀態欄，未另開
新列（避免推高帳本未結列存量，見同檔 `--unresolved-count` 現查）。

---

## §B 逐檔清單（護欄層 87784 → 88372，+588）
（本節記載本輪原始交付；R102 收尾追加的 DEF-200-218 修復見下方〈§D〉，兩節合計
即上方 guard-total 引用的 87784 → 88387，+603。）

本輪淨額由兩部分組成：

### B.1 DEF-200-204 回歸測試（功能成長，非漂移）

| 檔案 | 舊值 | 新值 | 淨額 | 內容 |
|------|-----:|-----:|-----:|------|
| `test_quota_policy.py` | 2432 | 2993 | +561 | 可得性軸遲滯／死區·變化率限制·最小停留時間／啟動自檢（H2~H7）的回歸測試 |
| `test_context_budget_guard.py` | 8081 | 8092 | +11 | 同批持久狀態隔離治具（避免 `quota_availability`／`quota_stability` 的持久檔跨測試污染 cap／streak） |

小計：**+572**。淨額 572 < `net_cap_for_round(102)`＝750，未觸及款(10)；緊接 R101 的
一次性核准例外之後，`repin_growth_problems()` 的連續上升計數在核准輪重置為零，本輪為
streak 第 1 輪，未觸及款(11)。無需 `_REPIN_APPROVED_ROUND_OVERAGE` 例外。

### B.2 本檔自身編修（護欄層重釘自身編修）

| 項目 | 淨額 | 內容 |
|------|-----:|------|
| `_GUARD_LINES_REPIN_LOG` 兩筆新列 ＋ `_FROZEN_GUARD_LINES` 兩處數值更新 ＋ prefix_len／sha256 ／`_FROZEN_PREFIX_REWRITE_LEDGER` 新增一列 ＋ 兩份新增文件（本檔／`R102_HANDOFF.md`）與 `governance_docs.py` 登記引用的座標散文 | +16 | 同 R95~R101 既有體例（合法出口逐條實查：純數字與註解無可抽結構、無死碼可刪） |

小計：**+16**（本檔自身逐檔漂移合計，`test_adr_xplat001_c1c2_lock.py` 6070 → 6086）。

**B.1 + B.2 = 572 + 16 = 588**，與 `_GUARD_LINES_REPIN_LOG` 兩筆 R102 列的淨額合計逐字相符。

---

## §C 交叉引用

- `docs/04_planning/R102_HANDOFF.md`
- `docs/06_quality/AutoSDD_Defect_Log.md` — `DEF-200-204`
- `docs/04_planning/R101_HANDOFF.md`（並行輪次交棒書）

---

## §D DEF-200-218 逐檔清單（R102 收尾：修復 push 被擋下的三項既存缺陷，護欄層 88372 → 88387，+15）

R100／R101／R102 三個 commit 從未真的 `git push` 過，本機 pre-push 閘門首次觸發
`run_root_unittests.py` 便揪出以下三項既存缺陷（帳本索引列＝`docs/06_quality/AutoSDD_Defect_Log.md`
的 `DEF-200-218`，本節為其逐字座標與修法，依 `ROW_MAX_BYTES` 紀律不塞回帳本列本身）：

1. `test_check_pytest_baseline_sites.py` 的 `_SCAN_FILES` 只納管了
   `AutoClaude/autoclaude/core/ports/quota_meter.py`，漏了 R100 同批新增、含同型
   「誤配 pytest 摘要字面」反例引文的回歸測試
   `AutoClaude/tests/test_r100_quota_refusal_false_positive.py`（未納管站點棘輪
   114→115，逐檔清單見下方 D.1）。
2. `AutoClaude/tests/test_r100_boot_self_check.py:239` 的
   `git ls-files --error-unmatch` 未帶 `-c core.quotepath=false`；已補上該旗標。
3. `docs/04_planning/R102_HANDOFF.md` 有兩筆「未落地」否定宣稱與一筆「仍未執行」宣稱
   缺機讀證偽標的／現查指令；已補 `absent-if:` 標記與現查指令。

三項皆已直接修復並回歸驗證，逐字命令與 rc 見主控交件回報；本檔不重複貼一份會漂移的
複本（同 `_PHASE2_REVIEW_LOG` 一份知識一個家的紀律）。

### D.1 未納管站點棘輪漏檔（功能修復，非漂移）

| 檔案 | 舊值 | 新值 | 淨額 | 內容 |
|------|-----:|-----:|-----:|------|
| `test_check_pytest_baseline_sites.py` | 299 | 301 | +2 | `_SCAN_FILES` 補納管 `AutoClaude/tests/test_r100_quota_refusal_false_positive.py`（同型 `4290 passed` 反例引文，R100 只納管了受測模組 `quota_meter.py` 本身，漏了它自己的回歸測試） |

小計：**+2**。

### D.2 本檔自身編修（護欄層重釘自身編修）

| 項目 | 淨額 | 內容 |
|------|-----:|------|
| `_GUARD_LINES_REPIN_LOG` 一筆新列 ＋ `_FROZEN_GUARD_LINES` 兩處數值更新 ＋ prefix_len／sha256 ／`_FROZEN_PREFIX_REWRITE_LEDGER` 新增一列（含一次理由欄改寫，避免與 `check_pytest_baseline_sites.py` 自身判準互踩） | +13 | 同 R95~R101 既有體例（合法出口逐條實查：純數字與註解無可抽結構、無死碼可刪） |

小計：**+13**（本檔自身逐檔漂移，`test_adr_xplat001_c1c2_lock.py` 6086 → 6099）。

**D.1 + D.2 = 2 + 13 = 15**，與 `_GUARD_LINES_REPIN_LOG` 該筆 R102 列的淨額逐字相符。

另兩項既存缺陷（`AutoClaude/tests/test_r100_boot_self_check.py:239` 補
`-c core.quotepath=false`；`docs/04_planning/R102_HANDOFF.md` 補齊 `absent-if:`／現查
標記）不動任何護欄層檔案的行數，故不進本節逐檔清單。
