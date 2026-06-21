# AutoSDD_improving_41 — A 軌整合橋接：狀態碼斷言跨行聚合保真度修復（DEF-41-001）

> **軌道①整合迭代 第 41 輪**。本輪主柱＝**A 軌（雙向協作橋接 SDD→Playbook）**。
> 🔴 掌舵者 AskUserQuestion 兩問拍板：(Q1) 主柱＝**A 軌·新整合橋接標的**（活標的 DEF-41-001）；(Q2) 推進幅度＝**≤3 W 項**。
> 本輪改 AutoClaude `sdd_to_playbook_adapter.py`（A 軌整合橋接入口），**零 Copy-on-Evolve、零框架 v0.0X 變更、TLC 不觸發**。
> 北極星對齊：A 協作自治（規格驅動轉譯的狀態碼斷言保真度——把「多條負向狀態碼只擋首條 / 正負混合丟棄負向」的 under-specify 漏放修正為跨行聚合，提升 SDD→Playbook 轉譯契約的端到端可信度）。

---

## §0 本輪定位（防跨軌誤指）

| 項目 | 內容 |
|------|------|
| 軌道 | ① 整合迭代，**A 柱（雙向協作橋接）** |
| 活標的 | **DEF-41-001**（狀態碼斷言單條截斷 under-specify，P3，本輪新開→fixed） |
| 為何非 C 軌 | C 軌 SD_09 **W1 正式執行輪因 06-26 G0 閘門未開而 blocked**（今 2026-06-21），不啟 W1/不跑 mutmut/不偽造 nightly |
| 為何 A 軌 | 🔴 掌舵者 Q1 拍板；DEF-32-002 已 fixed@improving_40 後 A 軌無 active 標的，本輪偵察 SddToPlaybookAdapter 揭露與引號路徑對稱的新缺口 DEF-41-001 |
| 下一份 | improving_42（按需） |
| 框架版本 | **無變更**（A 軌純改 AutoClaude，非框架 dogfooding，無 Copy-on-Evolve）；最新框架版實測 **v0.17** |

---

## §1 階段一：現況重偵察（Zero-Trust Re-Audit，實測）

六項基線全綠 HARD GATE PASS：

| 項目 | 實測值 | 判定 |
|------|--------|------|
| AutoClaude `pytest tests/ -q`（基線） | **3223 passed / 122 skipped / 0 failed** | ✅ = floor，0 failed |
| `lint-imports` | 8 kept / 0 broken | ✅ |
| `check_loc_budget.py` | violations=0（total 18510 < cap 20438） | ✅ |
| `snapshot_sync.py --check` | OK / FRESH | ✅ |
| AISDLC_SDD `ci-gate.sh` | exit 0；v0.01:1478 / v0.17:1611 / scripts:44 | ✅ |
| git 工作樹（root） | porcelain 空（乾淨） | ✅ |
| 框架最新版 | **v0.17**（親 `sort -V` 實證；Explore 兵初報 v0.09 中 `v0.0*` glob 十位邊界陷阱，主 agent 糾正） | ✅ |

- **階段一 (f) 外部工具依賴**：本輪 A 軌純改 AutoClaude Python adapter，**不涉外部 CLI/GUI/服務**，N/A。
- **DEF-41-001 根因實測**（親跑 repro 證明，非僅讀碼）：[sdd_to_playbook_adapter.py](../../AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py) 修復前狀態碼路徑 `for line in then_lines: ... if status: return ...` **只取「首條」status 行即 return**，而引號路徑（244-260）會跨行聚合 pos/neg 片段。實證三例：
  - 多負向「不應回傳 500」And「不應回傳 403」→ `(?s)\A(?!.*500)`（403 丟棄）；含 403 輸出 `re.search==True`＝漏放（應擋下）。
  - 正負混合「回傳 200」And「不應回傳 500」→ `(?i)(200)`（負向 500 完全丟棄）；含 500 輸出 `re.search==True`＝漏放。
  - 對照組多負向引號「不應顯示「錯誤A」」And「不應顯示「錯誤B」」→ `(?s)\A(?!.*錯誤A)(?!.*錯誤B)`（兩條皆聚合）＝證實 status 路徑與引號路徑**非對稱缺口**。

---

## §2 階段二：本輪增量設計（1 實作 W 項 + 1 測試 W 項 + 1 帳本）

### <Architecture_Design_Review>

1. **架構純潔性**：僅在既有純函式 `_gherkin_to_regex` 的狀態碼分支內，把「首條 return」改為「跨行聚合」（對齊同函式內引號路徑 244-260 的既有結構）。不新增方法、不改控制流、Thin Facade 不受影響、無 God-object。
2. **持久化相容**：零 FSM-STATE / checkpoint 寫入，純 regex 生成，DAL 三後端零影響。
3. **安全防護網**：負向/正向片語沿用既有 `re.escape(...strip().lower())`（與 W-40 同強度），不削弱 `_sanitize`／白名單模板／CONDITIONAL 三層防禦；regex 僅作 evaluator 輸出比對、非指令生成路徑。
4. **對外 I/O 安全**：不新增 `ToolInvocationPort` 外呼路徑，N/A。
5. **零退化（關鍵）**：**單條負向**逐位元維持 `(?s)\A(?!.*code)` / 含片語 `(?is)\A(?!.*code)(?!.*phrase)`（哨兵鎖定）；**單條/多條純正向**維持 `(?i)(code|phrase)` 取首條（哨兵鎖定，多正向沿用既有「首條 wins」設計，不臆測聚合——對齊 quoted-wins 決策）。只有**多條負向**與**正負混合**（先前直接丟棄負向＝缺口、無哨兵）才改變行為。
6. **對稱性**：正負混合採與引號路徑 259 行完全相同的 `(?=.*P)`+`(?!.*N)` 形式；正向以 `(?=.*(?:碼|片語))`（alternation 任一出現即表該狀態）、負向碼/片語各自 `(?!.*x)`；case flag 沿用 W-40「含片語→(?is)」規則，負正對稱可審。
7. **紅線**：純轉譯保真度修復、不碰 maturity/meta、不提 Token 上限。

### W-41-1 — 狀態碼斷言跨行聚合（DEF-41-001 修復）

| 項目 | 內容 |
|------|------|
| 落點 | `sdd_to_playbook_adapter.py:267-296` `_gherkin_to_regex` 狀態碼分支（跨行收集 pos_status/neg_status，含片語 has_phrase 旗標） |
| 介面 delta | 迴圈收集所有 Then/And status；`neg_status` 碼+片語各 `(?!.*x)`；`pos_status` 以 `(?=.*(?:碼\|片語))`；含負向→`flags+\A+串接`；純正向→`(?i)(首條)` |
| 零退化 | 單負向/單正向逐位元維持既有格式（哨兵鎖定）；引號路徑完全不動（status 路徑僅在零引號片段時執行） |
| LOC 影響 | adapter 322→334 行（+12，<400 adapter tier） |
| `.importlinter` 影響 | 無（同模組內，無新跨層 import） |
| TLC | 不觸發（純 AutoClaude，零框架/FSM 變更） |

### W-41-2 — 測試：新增聚合 case + 哨兵 + M1 突變實證

- 新增 `TestStatusAssertionAggregation` 6 case：
  - `test_multiple_negative_status_all_aggregated`（**核心 A**：多負向皆入 lookahead，`(?s)\A(?!.*500)(?!.*403)`，403 輸出擋下）；
  - `test_positive_and_negative_status_mixed`（**核心 B**：`(?s)\A(?=.*(?:200))(?!.*500)`，正向要求 + 負向擋下）；
  - `test_multiple_negative_status_with_phrases_case_insensitive`（含片語多負向，`(?is)\A` case 一致性）；
  - `test_single_negative_status_unchanged_sentinel` / `test_single_positive_status_unchanged_sentinel`（防退化哨兵，逐位元鎖定既有格式）；
  - `test_end_to_end_multi_negative_status_regex`（端到端經 `_MULTI_STATUS_SPEC` 凍結載入）。
- **M1 突變**（status 收集迴圈尾加 `break` 退回「只取首條」）實證 **4 紅（multi-neg/pos+neg/multi-neg-phrase/端到端聚合）/ 2 綠（單負向、單正向哨兵）**；in-memory 反向 Edit 還原，`grep M1-MUTANT`=0 無殘留（DEF-32-001 紀律）。

### W-41-3 — 缺陷帳本：DEF-41-001 open→fixed@improving_41

- **DEF-41-001（P3, open → fixed@improving_41）**：見 §5。

### A 軌 SCG 對應（整合橋接 brownfield）

- SCG-0/1（需求/設計凍結）＝本計畫書 §1/§2（活標的＝狀態碼斷言跨行聚合保真度）；SCG-2 架構＝<Architecture_Design_Review>（純轉譯邏輯、零拓樸變更）；SCG-3 契約＝狀態碼斷言與引號路徑對稱之跨行聚合契約；SCG-4 實作 PR＝§3；SCG-5 RTM＝§6。

---

## §3 階段三：實作與雙重驗證

逐項實作即測（開發-編譯-測試循環）：

1. **W-41-1**：adapter 狀態碼分支改寫為跨行聚合。
2. **即測（首測）**：`pytest tests/infra/test_sdd_to_playbook_adapter.py tests/infra/test_gherkin_to_regex.py -q` → 修復後 repro 三例皆正確擋下、66 既有測試零退化。
3. **W-41-2**：新增 `TestStatusAssertionAggregation` 6 case → **72 passed**（66+6）。
4. **M1 突變**：迴圈尾加 `break` → 4 聚合 case 轉紅 / 2 單條哨兵維持綠；反向 Edit 還原後 72 passed、`grep M1-MUTANT`=0 無殘留。

---

## §4 階段四：CI 平價收斂（零退化驗證矩陣，全項實測）

| 檢查 | 命令 | 通過條件（floor=improving_40 實測） | 本輪實測 | 判定 |
|------|------|------|------|------|
| AutoClaude 全套 | `pytest tests/ -q` | ≥ 3223 passed / 0 failed | **3229 passed / 122 skipped / 0 failed**（+6 新 case） | ✅ |
| 架構契約 | `lint-imports` | 全 kept / 0 broken | 8 kept / 0 broken | ✅ |
| LOC 分級 | `check_loc_budget.py` | 全過 | violations=0（adapter 334<400；total 18518） | ✅ |
| Snapshot | `snapshot_sync.py --check` | 新鮮 | FRESH | ✅ |
| AISDLC_SDD 閘門 | `ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | 本輪零碰框架，引階段一 exit 0；v0.01:1478 / v0.17:1611 / scripts:44 | ✅ |
| DAL 等價 | equivalence | 三後端等價 | AutoClaude DAL 未動，N/A | ✅ |
| 五軌 TLC | （僅 FSM 變更時） | 5 軌 0 violation | 不觸發（零框架變更） | ✅ |

> - AutoClaude 3229 = floor 3223 + 6（W-41-2 淨增 6 新 case）。
> - 本輪零碰 AISLDC_SDD 框架本體、零 Copy-on-Evolve、零 v0.0X 變更。

---

## §5 缺陷處置

- **DEF-41-001（P3）→ fixed@improving_41**（A 軌；狀態碼斷言跨行聚合，與引號路徑對稱、零退化、M1 突變實證；見帳本狀態欄）。
- **本輪無其他新增缺陷**。
- 未推進（維持原狀態）：DEF-01-007（open，cc-switch GUI 環境缺裝，本輪不涉多後端）、DEF-01-009（open watch，本輪改 adapter 未動 sdd_governance_plugin、violations=0 不觸發）、DEF-17-001（routed，遙測，本輪未推進）、DEF-19-001（closed@improving_40 milestone）。

---

## §6 RTM（需求可追溯矩陣）

| 需求 | 設計 | 實作 | 驗收 |
|------|------|------|------|
| 多負向狀態碼皆納入 lookahead（DEF-41-001 核心 A）| §2 W-41-1 | 跨行收集 neg_status 各 `(?!.*x)` | `test_multiple_negative_status_all_aggregated`（regex==`(?s)\A(?!.*500)(?!.*403)`，403 擋下）|
| 正負混合保留負向（DEF-41-001 核心 B）| §2 W-41-1 | `(?=.*(?:碼))`+`(?!.*碼)` | `test_positive_and_negative_status_mixed`（regex==`(?s)\A(?=.*(?:200))(?!.*500)`）|
| 含片語多負向 case 一致性 | §2 設計#6 | `(?is)\A` 全域 flag | `test_multiple_negative_status_with_phrases_case_insensitive` |
| 零退化（單條負向）| §2 設計#5 | 聚合 1 項時逐位元 `(?s)\A(?!.*code)` | `test_single_negative_status_unchanged_sentinel` + 既有 W-32/W-40 哨兵不變 |
| 零退化（單/多正向）| §2 設計#5 | 純正向取首條 `(?i)(code\|phrase)` | `test_single_positive_status_unchanged_sentinel` + `test_single_status_unchanged` |
| 修復有效性 | §2 W-41-2 | M1 突變 | M1 迴圈尾加 break→4 聚合 case 轉紅、2 單條哨兵綠 |
| 端到端凍結載入 | §2 W-41-2 | `_MULTI_STATUS_SPEC` | `test_end_to_end_multi_negative_status_regex` |

---

## §7 結案證據契約（closure-evidence，反幻覺機械閘門 DEF-20-001）

```yaml
closure-evidence:
  base_sha: 7461bcb  # 本輪所建之上的 HEAD（improving_40 回填收尾後）
  claimed_commits:
    - "{{CLAIMED_COMMIT}}"
  claimed_tag: v2026.06.21-41
  pytest:
    autoclaude: "3229 passed / 122 skipped / 0 failed（floor 3223 +6）"
    adapter_focused: "72 passed（test_sdd_to_playbook_adapter.py + test_gherkin_to_regex.py）"
  lint_imports: "8 kept / 0 broken"
  loc: "violations=0; adapter 334<400; total 18518"
  snapshot: "FRESH"
  ci_gate: "本輪零碰框架；引階段一 exit 0 / v0.01:1478 / v0.17:1611 / scripts:44"
  tlc: "N/A — 零框架/FSM 變更"
  copy_on_evolve: "N/A — A 軌純改 AutoClaude，無 v0.0X 變更"
  mutation_m1: "status 迴圈尾加 break → 4 聚合 case 轉紅 / 2 單條哨兵綠；in-memory 反向 Edit 還原，grep M1-MUTANT=0"
```
