# R108 交接書 — 架構輪（續跑鏈設計批交付＋DEF-200-230 回歸鎖落地）

<!-- guard-total:R108 --> **本輪護欄層累積淨額（稽核痕跡合計，同輪多列合併）＝ 89124 → 89314（+190）** —— DEF-200-230 回歸鎖落地（`test_quota_policy.py` 3071→3152）＋DEF-200-233 修復（macos-compat-ci：`test_run_root_unittests.py` 2201→2283）＋鎖檔自身稽核列與凍結前綴延伸（`test_adr_xplat001_c1c2_lock.py` 6282→6309）。逐檔清單見 `CrossPlatform_R108_Review.md`〈護欄層重釘逐檔清單〉節。

> 本輪是 **C 架構輪**：產出以「設計 + 提案 + 取證」為主，程式面只落一道回歸鎖。
> 修憲批與 ADR 皆為 **Proposed**，**未生效**——本檔任何一處都不得被讀成「已實作」。

---

## 一、已驗證什麼（皆為本輪當回合 tool_result）

### 1.1 複審鏈

- 四方複審鏈收斂：**19 → 7 → 4 → 0** blocking。一審四方（19）→ 修復包 #1/#2 → 二審三鏡（7）
  → 修復包 #3/#4 → 終審 QA＋Architect（4，Architect 對修憲案的 REJECT 已解除）→ 微修包 #5
  收口全部殘餘 blocking 與 non-blocking。逐筆判決全文＝`docs/06_quality/CrossPlatform_R108_Review.md`。
- 🔴 誠實劃界：四鏡皆為**唯讀複審、零測試執行**，本輪沒有任何一鏡做過「全綠」宣稱。

### 1.2 五份產出（行數為本輪實測 `Get-Content | Measure-Object`）

| 檔 | 行 | 狀態 |
|---|---|---|
| `docs/04_planning/PRD_Amendment_R108_Pacing.md` | 1181 | Proposed（修憲級，待裁決） |
| `docs/04_planning/ADR/ADR-XPLAT-014-resume-chain-hardening.md` | 1175 | Proposed（待裁決 Q1~Q7） |
| `docs/04_planning/PRD_Amendment_R108_BurnDown_Addendum.md` | 549 | Proposed（清倉模式，待裁決 QB1~QB6） |
| `docs/04_planning/ADR-XPLAT-013_Phase2_Proposal_R108.md` | 359 | 提案（待裁決 D-1~D-6） |
| `docs/06_quality/CrossPlatform_R108_Sentinel_Forensics.md` | 354 | 取證報告（已登記治理文件） |
| `docs/06_quality/CrossPlatform_R108_Review.md` | 103 | 一審紀錄（已登記治理文件） |

### 1.3 哨兵死因已證實（DEF-200-231 ③）

`AUTOSDD_RESUME_OFF=1` 住 **User 層**（主控親驗：User=1／Machine=空／行程=1）⇒ 哨兵巡邏走
`quota_back_no_resume` 分支、於 14:02:09 **自刪排程**。四疊加缺陷 D1~D4 逐項證據＝
`CrossPlatform_R108_Sentinel_Forensics.md`。**這是設計性自我解除，不是崩潰**——現存同值的
哨兵會重演同一條路。

### 1.4 額度閘門三度真擋扇出（活體證據）

本輪派鏡時 `context_budget_guard.py` 的**扇出節流層**三度真的攔下 Agent 呼叫（每 300s 上限
2 次、已用 3 次）。🔴 **擋的是扇出節流層，不是 cap 致動層**——DEF-200-198 引用時兩層不得混為
一談（該列訴求是「cap 一次都沒真的限制過派工」，本證據不能拿來結它）。

### 1.5 本窗口落地的機械物與帳本（逐項 rc 見〈六〉）

- `tools/lib/governance_docs.py`：登記 `CrossPlatform_R108_Review.md`＋
  `CrossPlatform_R108_Sentinel_Forensics.md`（各附 WHY 一句）。登記前 `check_defect_log_crossref.py`
  rc=1（2 筆未登記、早退壓住 12 道檢查）；登記後 rc=0，治理文件 **74 份**、12 道檢查首次真跑。
- `tools/tests/test_quota_policy.py`：DEF-200-230 回歸鎖
  `TestUsageUrlHasExactlyOneHome::test_usage_url_single_home_is_quota_meter`（＋同類的注入
  紅綠自證）。現況實測：全庫 tracked `*.py` **5,572** 支中帶完整端點 URL 字面者**恰 1**
  ＝`tools/lib/quota_meter.py`。`-k usage_url` 實跑 **2 passed**；該檔全套 **244 passed
  ／394 subtests**。
- 重釘稅同窗付清：`_FROZEN_GUARD_LINES` 兩支檔重釘、`_GUARD_LINES_REPIN_LOG` 追加 R108 稽核列
  （89124→89218，+94）、`_REPIN_LOG_FROZEN_PREFIX_LEN` 76→77、`_REPIN_LOG_HISTORY_SHA256`
  `abd0dc217e2b`→`21c85dff06f9`、`_FROZEN_PREFIX_REWRITE_LEDGER` 追加一列（錨 DEF-200-230）。
- 帳本：未結列 **64 → 63**（DEF-200-230 結案；本輪**零新增列**）。

---

## 二、還沒做什麼（R109 候選；本輪一律未動）

> 🔴 本節每一項都**沒有**落地。凡有帳本載體者逐項標出 DEF-ID；沒有載體者以「無帳本列」
> 明示——那正是它下一輪最容易蒸發的地方。
>
> 本節整體現查（一條就能核對哪些 DEF-ID 還開著）：
> `python tools/check_defect_log_crossref.py --unresolved-count`

1. **修憲批落地 W0~W6**（DEF-200-197／198／199）：修憲案與增補案皆 Proposed，**未落款、未實作**。
2. **裁決題堆疊**（全部待掌舵者；機械承接載體＝**DEF-200-232**，解鎖條件寫在該列狀態欄）：
   - ADR-XPLAT-014 Q1~Q7（其中 Q1／Q2／Q7 為 DEF-200-231 ①②③ 的前置）；
   - 修憲案 Q1~Q9（含候選 (iv) 未實測）；
   - BurnDown 增補 QB1~QB6（清倉模式）；
   - Phase 2 提案 D-1~D-6（DEF-200-211）；
   - `AUTOSDD_RESUME_OFF` User 層值的去留（本輪**明令不得動**）。
3. **SD 鏡 F4**：「30 版 `hub-push.yml` 同一 blob 分裂為恰 2 顆」尚未機械化。🔴 分裂在收尾
   commit 之後才 materialize ⇒ **commit 前寫斷言必假紅**，只能在 commit 後落地。無帳本列。
   現查（數目前有幾顆相異 blob）：
   `git ls-files -s -- 'AISDLC_SDD/*/.github/workflows/hub-push.yml'`
4. **ADR-XPLAT-013 Phase 2 (b)(c)**（DEF-200-211）：提案已交付、**未實作**；其到期義務
   `_PHASE2_DUE_ROUND` 與護欄層 `_REPIN_NET_CAP_DUE_ROUND=109`／`_REPIN_NET_CAP_DUE_TARGET=610`
   兩者皆在下一輪到期——屆時 `_REPIN_NET_CAP_SCHEDULE` 必須追加 `(109, ≤610)`，否則
   `[到期未下修]` 當場紅。
5. **`tools/lib/quota_meter.py` 兩句過期 docstring**（無帳本列，本輪未修）：
   - `:721` 自稱「唯一的呼叫端 `quota_gate.refresh_quota_blocking()`」——射程宣稱未複驗；
   - `:753` 具名 `quota_gate.refresh_quota_cache()`，而該符號**全庫實查零定義**
     （本輪 Grep：僅這句 docstring 提到它）⇒ 指針確定過期。
6. **通道 B/C 殘留與修憲案 Q9 候選 (iv)**：未實測。無帳本列。
7. **DEF-200-231 ①②③**：設計已交付（ADR-XPLAT-014 Proposed），三項**皆未實作**。
8. **機器重生檔** `AutoClaude/.perf_baseline.toml`／`AutoClaude/tests/fixtures/pgvector_real_ground_truth.json`
   本輪以 chore 併入收尾 commit（照 R107 判例），非缺陷。

---

## 三、下一步的確切指令（開場量測四件套）

```powershell
python d:\CursorProject\AISDCL_Agent\tools\session_resume_planner.py --pace
python d:\CursorProject\AISDCL_Agent\tools\check_defect_log_crossref.py --unresolved-count
python d:\CursorProject\AISDCL_Agent\AutoClaude\tools\check_loc_budget.py --json
python d:\CursorProject\AISDCL_Agent\tools\tests\test_adr_xplat001_c1c2_lock.py --print-guard-lines
```

- 讀 rc 一律不接管線（先接變數，或用 Python `subprocess.run(...).returncode`）。
- 帳本歸檔壓力現查：`python tools/archive_defect_log.py --check`（本輪未跑，無宣稱）。

## 四、禁止事項

- 不准 `--no-verify`；不准 `AUTOCLAUDE_SKIP_HOOKS=1`；不准 `AUTOSDD_QUOTA_GUARD_OFF=1`
  （額度閘門攔下時等視窗，不關守衛）。
- 不准動 `AUTOSDD_RESUME_OFF` User 層變數（掌舵者裁決項）。
- 修憲案／ADR-XPLAT-014／BurnDown 增補／Phase 2 提案**一律不得落款生效**，須先有裁決。
- 不得把本檔任何「已交付」讀成「已實作」；重啟後第一件事是重驗，不採信本檔任何宣稱
  （zero-trust 對自己上一段亦然）。
- 最後一次全套閘門必須在**最後一次寫文件之後**（R96 教訓：寫帳本會改變閘門判準的輸入）。

---

## 附件一：帳本前後量測（`--unresolved-count` 三次實跑，第三次為續跑包）

| | 未結列 | 全部列 | 外部阻塞軌 |
|---|---|---|---|
| 收尾窗口動工前 | **64** | 160 | 8 |
| 收尾窗口完成後 | **63** | 160 | 8 |
| 續跑包補承接載體後 | **64** | 161 | 8 |

- **新增 0／結案 1／淨額 −1**。結案＝DEF-200-230（`fixed@R108`，憑證＝測試類名＋當回合實跑）。
- 狀態欄指針補列（不改分子分母）：DEF-200-231（設計交付＋死因證實指針）、DEF-200-198／199
  （修憲案已交付指針）。
- DEF-200-197 **刻意不補指針**：該列現為 682 bytes，`ROW_MAX_BYTES=700` 只剩 18 bytes，
  任何指針句都會破線——帳本列是索引不是報告，寧可不寫也不擠。
- 本輪**零新增 DEF 列**：所有新發現一律由本檔〈二〉承接（Playbook §5 發現節流閘）。
- 🔴 **續跑包訂正（第二顆 commit）**：上一項的「零新增」**只對第一顆 commit 成立**。`tools/check_handoff_carriers.py` 判準① 對收尾 commit 判紅（交接散文宣告的目標輪在帳本家族內無未結列承接得住），依該閘門指定的唯一出口補列 **DEF-200-232**（狀態欄逐字 `open（承接輪次：**R109**）`，677 bytes ≤ 700）⇒ 未結 63→64、全部 160→161。**整輪**（基準 `5c724ba^`）淨額仍為 **0**（新增 DEF-200-232／結案 DEF-200-230）；淨額棘輪對第二顆 commit 的 post-commit 輸入面實測回空。

## 附件二：護欄層淨額落款與重釘清單

- 落款兩處（`_GUARD_TOTAL_DOC_MIN_SITES=2`，須相異檔）：本檔頂部 `guard-total:R108` 標記行、
  `docs/06_quality/CrossPlatform_R106_Scan_Findings.md`（寄居，同 R107 寄居該檔的既有判例）。
- 重釘清單（舊 → 新）：

| 標的 | 舊 | 新 |
|---|---|---|
| `_FROZEN_GUARD_LINES["test_quota_policy.py"]` | 3071 | 3152 |
| `_FROZEN_GUARD_LINES["test_adr_xplat001_c1c2_lock.py"]` | 6282 | 6295 |
| 稽核痕跡總量（`_GUARD_LINES_REPIN_LOG` 表尾） | 89124 | 89218（+94） |
| `_REPIN_LOG_FROZEN_PREFIX_LEN` | 76 | 77 |
| `_REPIN_LOG_HISTORY_SHA256`（前 12 碼） | `abd0dc217e2b` | `21c85dff06f9` |

- **同輪追加（DEF-200-233／macos-compat-ci 修復窗口）**——上表是 DEF-200-230 那一包的重釘，
  逐字保留；本包的重釘另計，兩包合計即頂部標記行的 89124 → 89314（+190）：

| 標的 | 舊 | 新 |
|---|---|---|
| `_FROZEN_GUARD_LINES["test_run_root_unittests.py"]` | 2201 | 2283 |
| `_FROZEN_GUARD_LINES["test_adr_xplat001_c1c2_lock.py"]` | 6295 | 6309 |
| 稽核痕跡總量（`_GUARD_LINES_REPIN_LOG` 表尾） | 89218 | 89314（+96） |
| `_REPIN_LOG_FROZEN_PREFIX_LEN` | 77 | 78 |
| `_REPIN_LOG_HISTORY_SHA256`（前 12 碼） | `21c85dff06f9` | `4e0397833463` |

- 單輪淨額上限 **630**（`_REPIN_NET_CAP_SCHEDULE` 末列 `(107, 630)`），本輪兩包合計 +190
  未越線；上一輪淨額為負 ⇒ 連續上升輪數自本輪起算 1
  （`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS=2`）。
- 逐檔清單與「合法出口逐條實查」＝`CrossPlatform_R108_Review.md`〈護欄層重釘逐檔清單〉節。
- 非護欄層改動（不入上表）：`tools/lib/governance_docs.py` 現為 **350 行**（`guardrail_lib`
  tier 上限 400，本輪實測餘裕 50）——`tools/lib/` 不在 `tools/tests/*.py` 行數棘輪掃描面內。

## 附件三：外部阻塞軌與輪內暫存清單裁決

- **外部阻塞軌 8 筆**（不計入未結列 warn/fail 分母）：DEF-101-518、DEF-101-693、DEF-101-703、
  DEF-200-063、DEF-200-075、DEF-200-147、DEF-200-174、DEF-200-186。本輪未新增、未遷出。
- 輪內暫存清單裁決（Playbook §5，三選一）：
  - **當場修掉、不立列**：兩檔未登記治理文件（crossref 17 紅的全部來源）；
    `CrossPlatform_R108_Review.md` 一行前瞻延後無 DEF-ID 載體（改寫為事實陳述）。
  - **併既有列**：哨兵死因 D1~D4 併入 DEF-200-231（不開新列，任務書明定）。
  - **寫進本檔不佔分母**：〈二〉的 3／5／6 三項（`hub-push.yml` blob 斷言、
    `quota_meter.py` 兩句過期 docstring、通道 B/C 殘留），皆無帳本列。

---

## 附件四：PRD v2.1 尚未完成功能清單（掌舵者要求）

| # | 項目 | 現狀 |
|---|---|---|
| 1 | 修憲批 DEF-200-197／198／199 | Proposed，未落款未實作 |
| 2 | 配速三改動 (a) thrifty floor／(b) `bursting_ok()` 接線／(c) must-finish 收尾保留段 | 提案（(b) 修憲級），未實作 |
| 3 | 清倉模式（BurnDown 增補） | Proposed，未實作 |
| 4 | 續跑鏈三缺陷 DEF-200-231 ①②③ | 設計已交付（ADR-XPLAT-014），未實作 |
| 5 | ADR-XPLAT-013 Phase 2 (b)(c)（DEF-200-211） | 提案已交付，未開始 |
| 6 | 外部阻塞軌 8 筆 | 阻塞源在 repo 外，本輪無進展 |

---

## 收尾書記最後全套（本檔寫完之後執行）

順序與指令：`python tools/run_root_unittests.py`／AutoClaude `python -m pytest tests/ -q`／
`$env:PYTHONUTF8=1; lint-imports`／`python tools/check_defect_log_crossref.py`／
`python tools/check_handoff_carriers.py`／`python AutoClaude/tools/check_loc_budget.py --json`／
`ruff check <本輪改到的 .py>`。

🔴 **逐項 rc 一律見交件回報，不寫進本檔**：本檔是閘門的判準輸入之一（`R*_HANDOFF.md` 在
`_GUARD_TOTAL_DOC_GLOBS` 與 `_CARRIER_GLOBS` 兩個掃描面上），把 rc 寫回來就得再改一次文件、
使那次量測失效（R96／DEF-200-163 家族的形態本身）。全綠才 commit；任何一步紅＝修復後從紅的
那一套重跑全部。
