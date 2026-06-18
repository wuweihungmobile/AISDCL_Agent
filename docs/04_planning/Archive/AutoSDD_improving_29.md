# AutoSDD_improving_29 — A 軌正向轉譯保真度（多重斷言組合）

> **本輪主柱**：**A 軌（整合 / 雙向協作）** — 推進 AISDLC-SDD × AutoClaude 深度整合（北極星第 3 點）。
> **下一份**：`AutoSDD_improving_30.md`（按需）。
> **防跨軌誤指**：本輪在 **A 柱（雙向協作）**，非 B 柱（手腳框架）亦非 C 柱（指揮官內部）。
> 本輪**零框架 v0.0X 變更**（無 Copy-on-Evolve、五軌 TLC 不觸發），所有交付在 AutoClaude 側。
>
> **角色**：Dr. Alan（L10 自治系統與微核心架構總監）
> **日期**：2026-06-17 ｜ **承上**：improving_28 結案（A 軌 RTM 跨輪覆蓋趨勢讀回，tag `v2026.06.17-26` / commit `b074f30`）

---

## 0. 北極星對齊

對齊北極星**第 3 點「完美協調溝通機制」**：AutoClaude 利用 AISLDC_SDD 進行軟體開發、建立兩者**雙向橋接**，成為端到端自動化開發 Agent。

improving_24 補逆向 `Playbook→SDD` 覆蓋報告**寫出**；improving_27/28 補 RTM **讀回**（最新單筆 + 跨輪趨勢諮詢邊）。逆向鏈已成熟。本輪轉回**正向 `SDD→Playbook` 轉譯保真度**：improving_28 §1 標記正向 `sdd_to_playbook_adapter` ~80% 成熟、缺口為「Given/When、複雑斷言組合」。階段一親讀碼證實 `_gherkin_to_regex`（`sdd_to_playbook_adapter.py:224-239`）對**多重 Then/And 斷言只取首條**——quoted 迴圈跨全部 Then 行只回傳**首個** quoted literal、後續 `And` 斷言被丟棄，生成的 `expected_output_regex` **欠規格化（under-specify）**，evaluator 只驗一半契約。本輪 W-29-1 把多斷言組合為「順序無關 AND」（lookahead），使橋接忠實驗證全部契約斷言。

成熟度三軸（`AutoSDD_Maturity_Rubric.md`，`L_合體 = min(A,B,C)`）：本輪續推 **A 軌（協作自治）**——提升正向轉譯保真度。**禁宣稱 L 級躍升**：本輪僅補一條多斷言組合邏輯（純函式、向後相容、零持久化），是正向橋接保真度的最小誠實一步，`L_合體` 仍受最弱軸卡住、不變。

---

## 1. 階段一：現況重偵察（Zero-Trust Re-Audit）— 實測事實

派背景 agent 親跑實測（**硬閘 PASS**，准入階段二）。所有數字來自當前回合真實 tool_result：

| 檢查 | 命令 | 實測 | 判定 |
|------|------|------|------|
| AutoClaude pytest | `python -m pytest tests/ -q` | **3189 passed / 122 skipped / 0 failed**（118.35s） | ✅ floor=3189 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ |
| LOC budget | `python tools/check_loc_budget.py` | total=18482 / cap=20438，violations=0 | ✅ |
| snapshot | `python tools/snapshot_sync.py --check` | FRESH（port 16 / plugin 17） | ✅ |
| AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | exit 0（v0.01:1478 + v0.14:1593 + scripts:27） | ✅ |
| 最新框架版本 | — | **v0.14**（本輪零觸碰） | — |

**外部工具依賴（階段一 (f)）**：本輪純 AutoClaude 整合層內部純函式增量（gherkin 文字 → regex），無 A/B 後端切換、無外部 CLI/服務、無訊息平台——不適用（DEF-01-007 cc-switch 維持 open，與本輪無關）。

**A 軌標的測繪（決定 W 項，zero-trust 親讀碼）**：

| 段 | 構件 | 現況（file:line） |
|----|------|-------------------|
| 逆向寫出 | `rtm_writeback_plugin.py` + `playbook_to_rtm_adapter.py` | 成熟（improving_24） |
| 逆向讀回（單筆+趨勢） | `evolution_plugin.py` `_rtm_gap/_rtm_trend_annotation` | 成熟（improving_27/28，諮詢用） |
| **正向 SDD→Playbook（多斷言保真度）** | `sdd_to_playbook_adapter.py:224-239` `_gherkin_to_regex` 多斷言只取首條 | **本輪標的（under-specify 缺口）** |
| 正向（Given/When 脈絡） | gherkin 全文已嵌入 prompt（`:119-122`） | 已涵蓋（非缺口） |

> 註：improving_28 §1 同時列「Given/When」為缺口候選，但親讀碼證實 Given/When 全文已隨 gherkin 嵌入 task.prompt（`:119-122`）→ 非實際缺口，本輪聚焦多斷言組合（Rule 2 最小、Rule 1 surface 假設）。

---

## 2. 階段二：增量設計（🔴 掌舵者選定 A 軌 / 沿用正向缺口）

### 2.1 scope 決策

🔴 掌舵者選定主柱＝**A 軌**。improving_28 W3 全結、無字面未完 W 項；「沿用」忠實錨定到 improving_28 §1 親標的**正向轉譯 ~80% 成熟之缺口**。親讀碼後在兩候選（Given/When、複雜斷言組合）中，依 zero-trust 排除已涵蓋者（Given/When 已嵌 prompt），鎖定**多重斷言組合 under-specify** 為真缺口。

**🔴 設計衝突和解（Rule 7／Rule 8 教訓，實作期揭露）**：初版設計把「任意 ≥2 可推導斷言（含 status+quoted 混合）」皆組合為 AND，跑全套時撞既有測試 `tests/infra/test_gherkin_to_regex.py::test_quoted_wins_over_status_code`——該測試以具名方式編碼 improving_01 §3.1 的**刻意設計決策「quoted wins over status code」**（同行有引號與狀態碼時引號勝出、status 忽略），非缺陷。而 improving_28「複雑斷言組合」僅一行**推測性缺口註記**。依 Rule 7（衝突取更成熟/更受測者）+ Rule 2（最小、不投機），**收斂 scope 為「僅組合多個引號字面值」**：`Then「A」And「B」` 兩引號丟一個＝真 under-spec（且**無任何既有測試覆蓋**→ 純 additive、零退化）；status+quoted 混合**完整保留 quoted-wins 決策**。教訓：階段一測繪漏讀 `test_gherkin_to_regex.py`（Rule 8「read before write」），由開發-編譯-測試循環當場攔截、未流出。

### 2.2 本輪 W 項（單一 W，Rule 2 最小）

| W 項 | 構件 | 檔案 | tier/LOC |
|------|------|------|----------|
| **W-29-1** | `_gherkin_to_regex` 加多引號組合分支：收集 then_lines 全部引號字面值，**≥2 個**→`(?s)` + 順序無關 lookahead AND；**單/零引號→維持既有逐行推導**（向後相容、保留 quoted-wins-over-status 決策） | `infra/adapters/sdd_to_playbook_adapter.py` | adapter ≤400 |

**零新 config flag、零新 port/plugin、零新方法**：僅 surgical 增強既有 `_gherkin_to_regex`（Rule 2/3）。

### 2.3 介面 delta

```python
# _gherkin_to_regex 開頭新增多引號組合分支（其餘既有邏輯原封保留）：
quoted_frags = [re.escape(m.group(1))
                for line in then_lines
                if (m := _QUOTED_LITERAL.search(line))]
if len(quoted_frags) >= 2:
    return "(?s)" + "".join(f"(?=.*{q})" for q in quoted_frags), False
# 單引號 / 無引號 → 維持既有 quoted 迴圈 / status 迴圈 / fallback（零行為變化）
```

### 2.4 `<Architecture_Design_Review>`（寫實質 Python 前自我驗證）

1. **架構純潔性**：`_gherkin_to_regex` 多引號組合分支為 adapter 內純函式（無 IO/副作用），零新 import 邊（不碰任何 importlinter contract）；adapter 272→283 行 < 400（adapter tier）。Thin Facade 不動、無 God-object。✅
2. **持久化相容**：零 checkpoint schema 變更、零 DAL 變更（純轉譯）→ 三後端零影響。✅
3. **安全防護網**：組合片段來自已過 AT row 白名單 regex 的 gherkin 文字 + 全程 `re.escape`；片段進 `expected_output_regex`（evaluator `re.search` 比對輸出，**非 shell 指令**）→ 無 shell 注入面；CONDITIONAL 三層消毒 + `_EVALUATOR_TEMPLATES` 白名單完全不動、未弱化。✅
4. **對外 I/O 安全**：未新增 `ToolInvocationPort` 外呼路徑，allowlist 不涉及。✅
5. **紅線守界**：嚴格向後相容——僅 ≥2 可推導斷言才走組合路徑，單/零斷言零行為變化（既有 29 測試不破）；weak fallback 保留；不改 evaluator 模板、不碰凍結硬閘。✅

### 2.5 B 軌 dogfooding — SCG 閘門對應

| SCG | 載體 |
|-----|------|
| SCG-0/1（需求/規格凍結） | 本計畫書 §0~§2 + 🔴 掌舵者 scope 選定（A 軌 / W-29-1） |
| SCG-2（介面設計） | §2.3 介面 delta + §2.4 設計審查 |
| SCG-3（契約） | `_gherkin_to_regex` 多引號組合純函式契約（凍結後實作） |
| SCG-4（PR/實作） | §3 實作 + 單元/契約測試全綠 |
| SCG-5（RTM 覆蓋） | §4 RTM（本輪 AT 100% 覆蓋） |

---

## 3. 階段三：實作與雙重驗證

逐支開發-編譯-測試循環（絕不累積）。新增 **0 支源碼檔**，surgical 改 1 源碼 + 1 測試檔：

- `autoclaude/infra/adapters/sdd_to_playbook_adapter.py`（`_gherkin_to_regex` 多引號組合分支，+~10 行）
- `tests/infra/test_sdd_to_playbook_adapter.py`（+`TestMultiAssertionCombination` **7 case** + `_MULTI_SPEC`/`_gtr`/`_block` 輔具）

**共 +7 測試**（3189→3196），只增不減、0 failed。**開發循環當場攔截 1 次設計衝突**（見 §2.1 和解）+ 1 次測試資料瑕疵（負例字面含目標字 → 修正），均於本檔測試層修復、未流出全套。

---

## 4. RTM（需求追溯矩陣）— 本輪 AT 100% 覆蓋

| AC | AT | 測試 | 狀態 |
|----|----|------|------|
| AC-29-1（多引號組合保真度） | AT-29-1-1 雙 quoted→AND lookahead（順序無關 match、缺一不過） | `test_sdd_to_playbook_adapter.py::TestMultiAssertionCombination::test_two_quoted_assertions_combined` | ✅ |
| AC-29-1 | AT-29-1-2 三 quoted→全部納入（count==3、順序無關） | `::test_three_quoted_assertions_all_combined` | ✅ |
| AC-29-1（保留設計決策） | AT-29-1-3 status+quoted 混合→引號勝出、不組合 | `::test_quoted_wins_when_mixed_with_status` | ✅ |
| AC-29-1 | AT-29-1-4 引號+量化 NFR→量化跳過、單引號不組合 | `::test_quantitative_excluded_keeps_single_quoted` | ✅ |
| AC-29-2（向後相容，零行為變化） | AT-29-2-1 單 quoted→維持 `re.escape`（非 lookahead） | `::test_single_quoted_unchanged` | ✅ |
| AC-29-2 | AT-29-2-2 單 status→維持 `(?i)(code\|phrase)` | `::test_single_status_unchanged` | ✅ |
| AC-29-2 | AT-29-2-3 端到端：雙引號 AT 經 load_spec→expected_regex 同時驗證兩斷言 | `::test_end_to_end_multi_assertion_regex` | ✅ |

**覆蓋率**：本輪 2 AC / 全部 7 AT 100% 通過（+既有 `test_gherkin_to_regex.py` quoted-wins 等 8 case 全綠，證零退化）。

---

## 5. 階段四：CI 平價收斂（零退化驗證矩陣）

| 檢查 | 命令 | floor（improving_28 實測） | 本輪實測 | 判定 |
|------|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3189 / 0 failed | **3196 passed / 122 skipped / 0 failed**（114.07s） | ✅ +7 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | 8 kept / 0 broken | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 | total=18489 / cap=20438，violations=0 | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | FRESH | FRESH（無新 port/plugin，純轉譯增強） | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 全綠 | exit 0（v0.01:1478 + v0.14:1593 + scripts:27，階段一實測） | ✅（持平，本輪零觸碰框架） |
| DAL 等價 | equivalence | 三後端等價 | 零 checkpoint/repository 變更（純轉譯），含於全套 | ✅ |
| 五軌 TLC | （僅 FSM 變更時） | — | **不觸發**（零 `_HAPPY_PATH`/`*.tla` 變更） | N/A |

---

## 6. 缺陷分流

- **本輪零新框架缺陷、零新整合層缺陷**（純 AutoClaude 正向轉譯保真度增強，零框架 v0.0X 變更）。
- open/routed 既有缺陷複驗：DEF-23-005（RFC 生命週期自動化，routed B 軌，**非本輪 A 軌 scope**）、DEF-19-001（catch 漸進覆蓋，routed B 軌）、DEF-01-007（cc-switch GUI，環境側）、DEF-01-009（sdd_governance LOC watch，本輪未動該 plugin，不觸發）、DEF-17-001（routed）——詳見 `AutoSDD_Defect_Log.md`。

**本輪新增防退化資產（非缺陷）**：`_gherkin_to_regex` 多引號組合邏輯由 `TestMultiAssertionCombination` 7 case 鎖定（雙/三引號 AND 組合 / 混合 quoted-wins 保留 / 量化排除 / 向後相容 / 端到端），正向橋接多引號 under-specify 缺口閉合。QA 鏡突變驗證（`>=2`→`>=99`）證 3 關鍵測試轉紅＝非假測試。

---

## 7. 結案四件套

1. 本計畫書 `docs/04_planning/AutoSDD_improving_29.md`
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_29.md`（審計 + 三鏡複審證據）
3. `docs/06_quality/AutoSDD_Defect_Log.md`（improving_29 複驗註記；零新缺陷）
4. 框架本體改進：**無**（零 v0.0X 變更）
</content>
</invoke>
