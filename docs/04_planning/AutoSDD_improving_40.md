# AutoSDD_improving_40 — A 軌整合橋接：DEF-32-002 負向狀態碼斷言片語級保真度修復

> **軌道①整合迭代 第 40 輪**。本輪主柱＝**A 軌（雙向協作橋接 SDD→Playbook）**。
> 🔴 掌舵者 AskUserQuestion 兩問拍板：(Q1) 主柱＝**A 軌·推進 SDD→Playbook 整合橋接**（活標的 DEF-32-002）；(Q2) **DEF-19-001 正式收尾為 milestone**（escalation-scoped 7/7=100% 結構天花板已達）。
> 本輪改 AutoClaude `sdd_to_playbook_adapter.py`（A 軌整合橋接入口），**零 Copy-on-Evolve、零框架 v0.0X 變更、TLC 不觸發**。
> 北極星對齊：A 協作自治（規格驅動轉譯的負向斷言保真度——把「不應回傳 500」的誤放缺口修正為片語級否定，提升 SDD→Playbook 轉譯契約的端到端可信度）。

---

## §0 本輪定位（防跨軌誤指）

| 項目 | 內容 |
|------|------|
| 軌道 | ① 整合迭代，**A 柱（雙向協作橋接）** |
| 活標的 | **DEF-32-002**（負向狀態碼斷言保真度 scope 漏洞，P3，open/routed→本輪 fixed） |
| 為何非 C 軌 | C 軌 SD_09 **W1 正式執行輪因 06-26 G0 閘門未開而 blocked**（今 2026-06-21），不啟 W1/不跑 mutmut/不偽造 nightly |
| 為何 A 軌 | 🔴 掌舵者 Q1 拍板；DEF-32-002 為 routed 中的 A 軌活標的（SddToPlaybookAdapter＝有規格時規格驅動轉譯入口），修負向斷言保真度提升端到端橋接可信度 |
| 連帶處置 | 🔴 掌舵者 Q2 拍板：**DEF-19-001 正式收尾為 milestone**（routed→closed） |
| 下一份 | improving_41（按需） |
| 框架版本 | **無變更**（A 軌純改 AutoClaude，非框架 dogfooding，無 Copy-on-Evolve） |

---

## §1 階段一：現況重偵察（Zero-Trust Re-Audit，實測）

派 general-purpose agent 重新實測（禁引文件宣稱值），六項基線全綠 HARD GATE PASS：

| 項目 | 實測值 | 判定 |
|------|--------|------|
| AutoClaude `pytest tests/ -q` | **3221 passed / 122 skipped / 0 failed** | ✅ = floor，0 failed |
| `lint-imports` | 8 kept / 0 broken | ✅ |
| `check_loc_budget.py` | violations=0（total 18506 < cap 20438） | ✅ |
| `snapshot_sync.py --check` | OK / FRESH | ✅ |
| AISDLC_SDD `ci-gate.sh` | exit 0；v0.01:1478 / v0.17:1611 / scripts:44 | ✅ |
| git 工作樹 | porcelain 空（乾淨） | ✅ |
| 活標的構件 | `sdd_to_playbook_adapter.py` 存在；負向斷言 W-31-1/W-32-1 已實作（行 277-282） | ✅ |

- **階段一 (f) 外部工具依賴**：本輪 A 軌純改 AutoClaude Python adapter，**不涉外部 CLI/GUI/服務**，N/A。
- **DEF-32-002 根因實測**：[sdd_to_playbook_adapter.py](../../AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py) 修復前負向狀態碼路徑只否定數字 `code`（`(?s)\A(?!.*{code})`），而 `_STATUS_CODE`（行 66）的 group(2) 尾隨片語（如 "Internal Server Error"）**未納入負向 lookahead**。對照正向路徑（行 279-282）已把 group(2) 納入 `(?i)(500|internal server error)` → **負正不對稱**＝缺口。系統輸出僅含片語不帶數字時漏放（誤判通過）。

---

## §2 階段二：本輪增量設計（2 實作 W 項 + 1 帳本）

### <Architecture_Design_Review>

1. **架構純潔性**：無 God-object。僅在既有純函式 `_gherkin_to_regex` 的負向狀態碼分支內把 group(2) 片語納入負向 lookahead；不新增方法、不改控制流、Thin Facade 不受影響。
2. **持久化相容**：零 FSM-STATE / checkpoint 寫入，純 regex 生成邏輯，DAL 三後端零影響。
3. **安全防護網**：負向片語經 `re.escape` 轉義（與既有正向路徑同強度），不削弱 `_sanitize`／白名單模板／CONDITIONAL 三層防禦；regex 僅作 evaluator 輸出比對、非指令生成路徑。
4. **對外 I/O 安全**：不新增 `ToolInvocationPort` 外呼路徑，N/A。
5. **零退化（關鍵）**：純數字否定（無 group(2)）逐位元維持 `(?s)\A(?!.*{code})`——哨兵測試鎖定 `test_single_negative_status_requires_absence`／`test_negative_status_english_marker` 不變；只有含尾隨片語時才加 `(?is)` + 片語 lookahead。正向路徑 `(?i)(code|phrase)` 完全不動。
6. **case 一致性（上輪明示注意點）**：片語沿用正向路徑完全相同的正規化 `re.escape(group(2).strip().lower())`，並以 `(?is)` 全域 flag 確保大小寫無關匹配——負正兩路徑 case 處理對稱可審。
7. **紅線**：純轉譯保真度修復、不碰 maturity、不碰 meta、不提 Token 上限。

### W-40-1 — 負向狀態碼斷言納入 group(2) 片語（DEF-32-002 修復）

| 項目 | 內容 |
|------|------|
| 落點 | `sdd_to_playbook_adapter.py:276-285` `_gherkin_to_regex` 負向狀態碼分支（276 W-40-1 註解起、280-285 邏輯） |
| 介面 delta | `neg=[code]`；有 group(2) 時 append `re.escape(group(2).strip().lower())`；flags `(?s)`→`(?is)`（含片語時）；回 `flags + "\\A" + 串接 (?!.*p)` |
| 零退化 | 無片語時逐位元 `(?s)\A(?!.*code)`（哨兵鎖定）；正向路徑不動 |
| LOC 影響 | adapter 316→322 行（+6，<400 adapter tier） |
| `.importlinter` 影響 | 無（同模組內，無新跨層 import） |
| TLC | 不觸發（純 AutoClaude，零框架/FSM 變更） |

### W-40-2 — 測試：改寫缺陷編碼測試 + 新增 case + M1 突變實證

- 改寫 `test_negative_status_ignores_trailing_phrase`→`test_negative_status_includes_trailing_phrase`（原測試編碼舊缺陷行為「刻意忽略片語」，修 DEF-32-002 後須改成新行為，Rule 9）；
- 新增 `test_negative_status_phrase_only_output_caught`（**核心修復**：輸出僅含 "Internal Server Error" 不帶 500 時，修正前漏放、修正後擋下）；
- 新增 `test_negative_status_phrase_case_insensitive`（case 一致性：任意大小寫洩漏輸出皆攔）；
- **M1 突變**（退回只否定數字 `(?s)\A(?!.*{code})`）實證 3 片語 case 精確轉紅、4 純數字零退化哨兵維持綠（in-memory 反向 Edit 還原，DEF-32-001 紀律）。

### W-40-3 — 缺陷帳本：DEF-32-002 fixed + DEF-19-001 正式收尾

- **DEF-32-002（P3, open/routed → fixed@improving_40）**：見 §5。
- **DEF-19-001（P3, routed → closed@improving_40 milestone）**：🔴 掌舵者 Q2 拍板正式收尾。FSM-escalation catch 機制覆蓋已達結構天花板 7/7=100%；其餘 32 條非 FSM-escalation catch-可歸因（設計使然非缺口）；「其他守門機制覆蓋度量」另立新標的。

### A 軌 SCG 對應（整合橋接 brownfield）

- SCG-0/1（需求/設計凍結）＝本計畫書 §1/§2（活標的＝負向斷言片語級保真度）；SCG-2 架構＝<Architecture_Design_Review>（純轉譯邏輯、零拓樸變更）；SCG-3 契約＝負向 lookahead 納入 group(2) 片語的對稱性契約；SCG-4 實作 PR＝§3；SCG-5 RTM＝§6。

---

## §3 階段三：實作與雙重驗證

逐項實作即測（開發-編譯-測試循環）：

1. **W-40-1**：adapter 負向狀態碼分支改寫，加片語 lookahead + case 一致性 flags。
2. **W-40-2**：`test_sdd_to_playbook_adapter.py::TestNegativeStatusAssertionFidelity` 改寫 1 + 新增 2 case。
3. **即測**：`pytest tests/infra/test_sdd_to_playbook_adapter.py tests/infra/test_gherkin_to_regex.py -q` → **66 passed**（0.56s）。
4. **M1 突變**：退回只否定數字 → 3 片語 case 轉紅 / 4 純數字哨兵維持綠；反向 Edit 還原後 66 passed、`grep M1-MUTANT`=0 無殘留。

---

## §4 階段四：CI 平價收斂（零退化驗證矩陣，全項實測）

| 檢查 | 命令 | 通過條件（floor=improving_39 實測） | 本輪實測 | 判定 |
|------|------|------|------|------|
| AutoClaude 全套 | `pytest tests/ -q` | ≥ 3221 passed / 0 failed | **3223 / 122 / 0**（+2 新 case） | ✅ |
| 架構契約 | `lint-imports` | 全 kept / 0 broken | 8 kept / 0 broken | ✅ |
| LOC 分級 | `check_loc_budget.py` | 全過 | violations=0（adapter 322<400） | ✅ |
| Snapshot | `snapshot_sync.py --check` | 新鮮 | FRESH | ✅ |
| AISDLC_SDD 閘門 | `ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | 本輪零碰框架，引階段一 exit 0；v0.01:1478 / v0.17:1611 / scripts:44 | ✅ |
| DAL 等價 | equivalence | 三後端等價 | AutoClaude DAL 未動，N/A | ✅ |
| 五軌 TLC | （僅 FSM 變更時） | 5 軌 0 violation | 不觸發（零框架變更） | ✅ |

> - AutoClaude 3223 = floor 3221 + 2（W-40 淨增：改寫 1〔不計增〕 + 新增 2）。
> - 本輪零碰 AISLDC_SDD 框架本體、零 Copy-on-Evolve、零 v0.0X 變更。

---

## §5 缺陷處置

- **DEF-32-002（P3）→ fixed@improving_40**（A 軌；負向狀態碼斷言納入 group(2) 片語，負正對稱、零退化、M1 突變實證；見帳本狀態欄）。
- **DEF-19-001（P3）→ closed@improving_40（milestone）**：🔴 掌舵者 Q2 拍板正式收尾。escalation-scoped catch 機制覆蓋達結構天花板 7/7=100%；其餘 32 條非 FSM-escalation catch-可歸因。
- **本輪無其他新增缺陷**。
- 未推進（維持原狀態）：DEF-01-007（open，cc-switch 環境缺裝，本輪不涉多後端）、DEF-01-009（open watch，本輪改 adapter 未動 sdd_governance_plugin、violations=0 不觸發）、DEF-17-001（routed，遙測，本輪未推進）、DEF-31-001（fixed@improving_33）。

---

## §6 RTM（需求可追溯矩陣）

| 需求 | 設計 | 實作 | 驗收 |
|------|------|------|------|
| 負向狀態碼斷言納入尾隨片語（DEF-32-002）| §2 W-40-1 | adapter 負向分支 group(2) lookahead | `test_negative_status_includes_trailing_phrase`（regex==`(?is)\A(?!.*500)(?!.*internal\ server\ error)`）|
| 修復誤放（核心）| §2 W-40-1 | 片語 lookahead | `test_negative_status_phrase_only_output_caught`（僅片語輸出擋下、200 放行）|
| case 一致性 | §2 設計#6 | `(?is)` 全域 flag + `.lower()` | `test_negative_status_phrase_case_insensitive`（任意 case 洩漏皆攔）|
| 零退化（純數字否定）| §2 設計#5 | 無片語逐位元 `(?s)\A(?!.*code)` | `test_single_negative_status_requires_absence`/`test_negative_status_english_marker` 哨兵不變 |
| 零退化（正向路徑）| §2 設計#5 | 正向 `(?i)(code\|phrase)` 不動 | `test_positive_status_unchanged_sentinel`/`test_single_status_unchanged` |
| 修復有效性 | §2 W-40-2 | M1 突變 | M1 退回只否定數字→3 片語 case 轉紅、4 純數字哨兵綠 |
| DEF-19-001 收尾 | §2 W-40-3 | 帳本 milestone | 帳本狀態欄 closed@improving_40（🔴 掌舵者拍板）|

---

## §7 結案證據契約（closure-evidence，反幻覺機械閘門 DEF-20-001）

```yaml
closure-evidence:
  base_sha: cc00788a675dba6e351c3b2ed018f9e85c134429  # 本輪所建之上的 HEAD（improving_39 收尾後）
  claimed_commits: []        # 待結案 commit 後回填
  claimed_tag: ""            # 待回填
  pytest:
    autoclaude: "3223 passed / 122 skipped / 0 failed（floor 3221 +2）"
    adapter_focused: "66 passed（test_sdd_to_playbook_adapter.py + test_gherkin_to_regex.py）"
  lint_imports: "8 kept / 0 broken"
  loc: "violations=0; adapter 322<400"
  snapshot: "FRESH"
  ci_gate: "本輪零碰框架；引階段一 exit 0 / v0.01:1478 / v0.17:1611 / scripts:44"
  tlc: "N/A — 零框架/FSM 變更"
  copy_on_evolve: "N/A — A 軌純改 AutoClaude，無 v0.0X 變更"
  mutation_m1: "退回只否定數字 → 3 片語 case 轉紅 / 4 純數字哨兵綠；in-memory 反向 Edit 還原，grep M1-MUTANT=0"
```
