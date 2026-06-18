# AutoSDD_improving_33 — 收尾 open 缺陷（A 軌 DEF-31-001 + B 軌 DEF-30-001）

> 軌道① 整合迭代第 33 輪。**主柱（🔴 掌舵者選定）**：本輪不開大型新功能，聚焦**收尾既有 open
> 缺陷**——A 軌 DEF-31-001（轉譯保真度 negation marker 收斂）+ B 軌 DEF-30-001（RFC 狀態欄
> 標準化 + lint 缺欄強制）。**零退化（Zero-Regression）**為絕對前提。

---

## 階段一：現況重偵察（Zero-Trust Re-Audit）

派出 re-audit agent + 主 agent 親跑實測，硬閘全 PASS：

| 檢查 | 命令 | 實測 | 判定 |
|------|------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3209 passed / 122 skipped / 0 failed**（112.23s） | ✅ floor 3209 持平 |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | ✅ |
| (c) LOC 分級 | `python tools/check_loc_budget.py` | violations=0（total=18506 / cap=20438） | ✅ |
| (d) Snapshot | `python tools/snapshot_sync.py --check` | OK（對齊一致） | ✅ FRESH |
| (e) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0（v0.01:1478 / v0.14:1593 / scripts:38、RFC lint clean） | ✅ |
| (f) improving_32 構件 | — | `sdd_to_playbook_adapter.py:269-274` 狀態碼否定路徑存在 + 測試覆蓋 | ✅ |

**硬閘判定：PASS**（無 failed、未低於上輪 floor 3209）→ 准進階段二。

open/routed 缺陷盤點與本輪處置：

| 缺陷 | 軌 | 本輪處置 |
|------|----|---------|
| DEF-31-001 | A | **本輪 fix** — negation marker 排除慣用語 |
| DEF-30-001 | B | **本輪 fix** — RFC 狀態欄標準化 + lint 升級 |
| DEF-32-002 | A | 維持 routed（刻意 scope，Rule 2 投機，無實證案例） |
| DEF-19-001 | B | 維持 routed（catch 漸進 4/39，非本輪 scope） |
| DEF-01-007 | — | 維持 open（cc-switch 環境工具缺裝，非倉內可修） |
| DEF-01-009 | C | 維持 open watch（已自癒 violations=0，本輪未動該 plugin） |
| DEF-17-001 | B | 維持（fire 側已 fixed、catch 側轉 DEF-18-001/19-001） |

---

## 階段二：本輪增量設計

### W-33-1（A 軌，DEF-31-001）：`_NEGATION_MARKER` 排除「not only / is not empty」慣用語

**缺陷**：`sdd_to_playbook_adapter.py:_NEGATION_MARKER` 含裸 `\bnot\b`，當 Then 行在引號**前**含
「not only … but」「is not empty」等「含 not 但語意非否定」片語時，誤把引號片段分流為負向
（`(?!.*X)`）。

**介面 delta**：單一模組級常數 `_NEGATION_MARKER` 內 `\bnot\b` → `\bnot\b(?!\s+(?:only|empty)\b)`。
`_gherkin_to_regex` 分流邏輯（行 247 引號路徑 / 行 273 狀態碼路徑）**零改動**——兩處共用同一
marker，**對稱受惠**。無新檔/類/port/plugin/flag/常數。

**LOC 預算落點**：adapter 313→315 行（+2 註解，< 400 adapter tier）。`.importlinter` 各 contract
零影響（無 import 變動）。checkpoint additive 欄位需求：無（純函式轉譯路徑）。

### W-33-2（B 軌，DEF-30-001）：RFC 狀態欄標準化 + lint 缺欄 advisory 強制

**缺陷**：RFC「已決」標記無標準化欄位（現有用 `已歸檔`/`EXECUTED`/無），致雙信號 lint 無法覆蓋
所有已決 RFC。

**介面 delta**（皆落 **shared infra `scripts/`，免 Copy-on-Evolve**）：
- `rfc_lifecycle_lint.py`：(a) `_CLOSED_STATUS_RE` 值集補標準英文 token `decided`；(b) 新增
  `_STATUS_FIELD_RE` + `find_active_rfcs_missing_status()` + `missing_status()`；(c) `main()` 加
  advisory `::warning::`（缺欄不影響 exit code）；(d) docstring 文件化 `**狀態**：proposed|decided`
  標準慣例（lint 即 SSOT）。
- B 軌 Brownfield SOP：RFC `SDD_improving_Automation_29.md`（active→archive 完整生命週期 dogfooding）。

**對 `.importlinter`/LOC/TLC 影響**：lint 在 AISDLC_SDD/scripts（非 AutoClaude，不受其 importlinter/
check_loc_budget 管轄）；read-only 純觀察者，不寫 FSM-STATE、不碰 churn/meta-loop（守 R-9.37.4）；
**不動任一 v0.0X 凍結本體 → 無 v0.15、五軌 TLC 不觸發**。

兩 W 項皆附 `<Architecture_Design_Review>`（見階段三實作前輸出，四項全過：架構純潔/持久化相容/
安全防護網/對外 I/O 安全）。

---

## 階段三：實作與雙重驗證

### W-33-1 落地

- `autoclaude/infra/adapters/sdd_to_playbook_adapter.py:75` marker 收斂 + 行 69-77 註解延伸。
- `tests/infra/test_sdd_to_playbook_adapter.py::TestNegationIdiomFidelity` 5 case：
  not only 慣用語維持正向 / is not empty 慣用語維持正向 / 真否定 not contain 仍負向 /
  左掃（慣用語後接真否定）仍負向 / 強標記 should not 不受影響哨兵。
- **單測**：`test_sdd_to_playbook_adapter.py` 49→**54 passed**。
- **M1 突變**（marker 退回裸 `\bnot\b`）：正好 2 慣用語 case 轉紅、其餘 3 case 維持綠（行為一致），
  in-memory 還原（遵 DEF-32-001 禁 git checkout）後 54 passed。證測試非假。

### W-33-2 落地

- `scripts/rfc_lifecycle_lint.py`（docstring + `decided` token + `_STATUS_FIELD_RE` + 兩函式 + main advisory）。
- `scripts/tests/test_rfc_lifecycle_lint.py` 11→**15 passed**（+4：decided token fire / 缺欄 advisory
  非硬違規 / proposed 全乾淨 / CLI 缺欄 warn 但 exit 0）。
- **M2a 突變**（移除 `decided`）：正好 decided-token case 轉紅；**M2b 突變**（反轉缺欄邏輯）：正好
  3 缺欄 case 轉紅；in-memory 還原後 15 passed。證測試非假。
- **RFC _29 dogfooding 生命週期自驗**：`**狀態**：proposed` 起 → lint 真實 repo 乾淨 → 翻 `decided`
  仍留 active/ → lint 以新標準 token 攔下「decided 滯留 active/」（exit 1 實證）→ `mv` 入 archive/
  → active/ 復乾淨 lint exit 0。

---

## 階段四：CI 平價收斂（零退化驗證矩陣）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3209 / 0 failed | **3214 / 122 / 0**（+5） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0** |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK / FRESH** |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | **exit 0**（v0.01:1478 / v0.14:1593 / scripts:42、RFC lint clean） |
| DAL 等價 | full pytest 內含 | 三後端等價 | 無 DAL 變更（覆蓋於全套） |
| 五軌 TLC | （僅 FSM 變更時） | — | **不觸發**（無 FSM/*.tla 變更） |

**零退化收斂達成**：AutoClaude 3209→**3214**（floor +5）、scripts 38→**42**（+4）、lint 8/0、LOC 0、
snapshot FRESH、ci-gate exit 0、TLC 不觸發、零 Copy-on-Evolve（無 v0.15）。

---

## §6 RTM（需求追溯矩陣）

| 需求 | 缺陷 | 設計 | 實作（file:line） | 測試 | 狀態 |
|------|------|------|-------------------|------|------|
| AC-33-1 negation marker 排除慣用語 | DEF-31-001 | W-33-1 | `sdd_to_playbook_adapter.py:75` | `TestNegationIdiomFidelity` 5 case（含 M1 突變） | ✅ |
| AC-33-2 RFC 狀態欄標準化 + decided token | DEF-30-001 | W-33-2 | `rfc_lifecycle_lint.py` `_CLOSED_STATUS_RE` | `test_closed_status_decided_token_fires` | ✅ |
| AC-33-3 active/ RFC 缺欄 advisory warn | DEF-30-001 | W-33-2 | `rfc_lifecycle_lint.py` `missing_status()`/`main()` | `test_active_rfc_missing_status_warns_not_fails` / `test_main_missing_status_warns_but_exits_zero` | ✅ |
| AC-33-4 proposed 全乾淨（不誤報/不誤 fire） | DEF-30-001 | W-33-2 | 同上 | `test_proposed_status_clean_no_warn_no_fire` | ✅ |
| AC-33-5 RFC 生命週期 dogfooding 自驗 | DEF-30-001 | W-33-2 | `SDD_improving_Automation_29.md`（archive） | lint 實跑 proposed→decided→archive | ✅ |

---

## <Architecture_Design_Review>（實作前輸出，存證）

**W-33-1**：1) 架構純潔——僅收斂既有模組級常數單一 alternative，adapter 仍 Thin 轉譯器，無
God-object；2) 持久化相容——純函式、無狀態、不觸 PlaybookCheckpoint/DAL；3) 安全防護網——marker
收斂只減少誤判，不放寬任何指令生成/消毒路徑；4) 對外 I/O——不新增 `ToolInvocationPort`。

**W-33-2**：1) 架構純潔——僅改 shared infra lint，read-only 純觀察者，守 R-9.37.4；2) 持久化相容
——不涉持久化；3) 安全防護網——純文字掃描，不生成指令、不外呼；4) 對外 I/O——N/A；不動凍結本體
→ 無 v0.15、TLC 不觸發。
</content>
