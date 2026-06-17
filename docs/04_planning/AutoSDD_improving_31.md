# AutoSDD_improving_31 — A 軌正向轉譯保真度（負向斷言 negation-aware）

> **本輪主柱**：**A 軌（整合 / 雙向協作）** — 推進 AISDLC-SDD × AutoClaude 深度整合（北極星第 3 點）。
> **下一份**：`AutoSDD_improving_32.md`（按需）。
> **防跨軌誤指**：本輪在 **A 柱（雙向協作）**，非 B 柱（手腳框架）亦非 C 柱（指揮官內部）。
> 本輪**零框架 v0.0X 變更**（無 Copy-on-Evolve、五軌 TLC 不觸發），所有交付在 AutoClaude 側。
>
> **角色**：Dr. Alan（L10 自治系統與微核心架構總監）
> **日期**：2026-06-18 ｜ **承上**：improving_30 結案（B 軌 RFC 生命週期機械強制，tag `v2026.06.18-28` / commit `527d30b`）

---

## 0. 北極星對齊

對齊北極星**第 3 點「完美協調溝通機制」**：AutoClaude 利用 AISLDC_SDD 進行軟體開發、建立兩者**雙向橋接**，成為端到端自動化開發 Agent。

逆向鏈（Playbook→SDD 覆蓋寫出/讀回/趨勢）已於 improving_24/27/28 成熟；正向鏈（SDD→Playbook 轉譯保真度）improving_29 閉合「多引號 AND under-specify」缺口。本輪續推正向鏈：閉合**負向斷言語意顛倒（mis-specify）**缺口——較 under-specify 更嚴重的保真度錯誤。

成熟度三軸（`AutoSDD_Maturity_Rubric.md`，`L_合體 = min(A,B,C)`）：本輪續推 **A 軌（協作自治）**。**禁宣稱 L 級躍升**：本輪僅補一條負向斷言分流（純函式、向後相容、零持久化），是正向橋接保真度的最小誠實一步，`L_合體` 仍受最弱軸卡住、不變。

---

## 1. 階段一：現況重偵察（Zero-Trust Re-Audit）— 實測事實

派 Explore agent 親跑實測（**硬閘 PASS**，准入階段二）。所有數字來自當前回合真實 tool_result：

| 檢查 | 命令 | 實測 | 判定 |
|------|------|------|------|
| AutoClaude pytest | `python -m pytest tests/ -q` | **3196 passed / 122 skipped / 0 failed**（127.75s） | ✅ floor=3196 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ |
| LOC budget | `python tools/check_loc_budget.py` | total=18489 / cap=20438，violations=0 | ✅ |
| snapshot | `python tools/snapshot_sync.py --check` | OK（FRESH） | ✅ |
| AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | exit 0（v0.01:1478 + v0.14:1593 + scripts:38） | ✅ |
| 最新框架版本 | — | **v0.14**（active RFC 已清空、archive 53；本輪零觸碰） | — |

**外部工具依賴（階段一 (f)）**：本輪純 AutoClaude 整合層內部純函式增量（gherkin 文字 → regex），無 A/B 後端切換、無外部 CLI/服務、無訊息平台——不適用（DEF-01-007 cc-switch 維持 open，與本輪無關）。

**A 軌標的測繪（決定 W 項，zero-trust 親讀碼）**：

| 段 | 構件 | 現況（file:line） |
|----|------|-------------------|
| 逆向寫出/讀回/趨勢 | `playbook_to_rtm_adapter.py` / `evolution_plugin.py` | 成熟（improving_24/27/28） |
| 正向多引號 AND | `sdd_to_playbook_adapter.py` `_gherkin_to_regex` ≥2 引號→lookahead | 成熟（improving_29） |
| **正向負向斷言（mis-specify）** | `_gherkin_to_regex` 對所有引號一律當正向 → 「不應包含「X」」譯成要求 X 出現 | **本輪標的（語意顛倒缺口）** |

---

## 2. 階段二：增量設計（🔴 掌舵者選定 A 軌）

### 2.1 scope 決策

🔴 掌舵者選定主柱＝**A 軌**。延續 improving_29 正向轉譯保真度線，親讀碼後在 Explore 提的 5 候選中，依「真缺口 > 投機」「修正 > 完整」原則排除投機項（如未被消費的 precondition metadata），鎖定**負向斷言語意顛倒**為最高價值缺口：

- 現況 `_gherkin_to_regex` 對所有引號字面值一律當正向要求。`Then 回應不應包含「password」`→ `re.escape("password")`＝**要求** password 出現，語意完全顛倒（mis-specify）。
- 安全/隱私類 AC 高度依賴否定句式（不洩漏、不得包含、should not expose），此 codebase 安全面（SSRF/注入）尤甚→**非投機，是常見且現被顛倒的真缺口**。
- 直接複用 improving_29 的 lookahead 基礎設施：正向 `(?=.*P)` 要求出現、負向 `(?!.*N)` 要求不出現。

### 2.2 本輪 W 項（單一 W，Rule 2 最小）

| W 項 | 構件 | 檔案 | tier/LOC |
|------|------|------|----------|
| **W-31-1** | `_gherkin_to_regex` 依「引號之前是否有否定標記」分流正向/負向引號片段；含負向 → `\A` 錨定 lookahead 組合（`(?=.*P)`＋`(?!.*N)`）；純正向 ≥2 / 單引號 / status / 量化 / fallback 路徑 bit-for-bit 不變 | `infra/adapters/sdd_to_playbook_adapter.py` | adapter ≤400（284→304） |

**零新 config flag、零新 port/plugin、零新方法**：surgical 重構既有 `_gherkin_to_regex` + 新增 1 個 module-level `_NEGATION_MARKER` 常數（Rule 2/3）。

### 2.3 介面 delta

```python
# 新增否定標記常數（引號「之外、之前」才視為負向）：
_NEGATION_MARKER = re.compile(
    r"不應|不得|不可|不能|不會|不要|不准|不再|禁止|沒有|無法"
    r"|不存在|不包含|不顯示|不出現|不回傳|不允許|不洩漏|不暴露"
    r"|\bshould\s+not\b|\bmust\s+not\b|\bshall\s+not\b|\bcannot\b"
    r"|\bnot\b|\bnever\b|\bno\s+longer\b", re.I)

# _gherkin_to_regex 分流（其餘 status/量化/fallback 不變）：
pos_frags, neg_frags = [], []
for line in then_lines:
    m = _QUOTED_LITERAL.search(line)
    if not m: continue
    frag = re.escape(m.group(1))
    (neg_frags if _NEGATION_MARKER.search(line[:m.start()]) else pos_frags).append(frag)
if neg_frags:                         # 含負向 → \A 錨定（re.search 下負向 lookahead 必須錨定）
    parts = [f"(?=.*{q})" for q in pos_frags] + [f"(?!.*{q})" for q in neg_frags]
    return "(?s)\\A" + "".join(parts), False
if len(pos_frags) >= 2:               # improving_29 格式不變（不加 \A）
    return "(?s)" + "".join(f"(?=.*{q})" for q in pos_frags), False
if pos_frags:                         # 單引號維持 re.escape
    return pos_frags[0], False
# ...status / 量化 / fallback 原封不變...
```

### 2.4 `<Architecture_Design_Review>`（寫實質 Python 前自我驗證）

1. **架構純潔性**：純函式（無 IO/副作用）+ 1 module 常數；零新 import 邊（不碰任一 importlinter contract）；adapter 284→304 < 400。Thin Facade 不動、無 God-object、無新 port/plugin/方法。✅
2. **持久化相容**：零 checkpoint schema 變更、零 DAL 變更、零 alembic → 三後端零影響。✅
3. **安全防護網**：負向片段同樣全程 `re.escape`，產物進 `expected_output_regex`（evaluator `re.search` 比對輸出，**非 shell 指令**）→ 無 shell 注入面；否定標記只讀已過 AT row 白名單的 gherkin；CONDITIONAL 三層消毒 + `_EVALUATOR_TEMPLATES` 白名單完全不動。✅
4. **對外 I/O 安全**：未新增 `ToolInvocationPort` 外呼路徑，allowlist 不涉及。✅
5. **紅線守界 / 零退化**：僅偵測到否定標記（且在引號之外、之前）才走 `\A` 錨定 lookahead；正向路徑 bit-for-bit 不變（improving_29 的 16+ case 不破）；否定標記在引號內不誤觸發。零 `_HAPPY_PATH`/`*.tla` 變更 → 五軌 TLC 不觸發；AutoClaude 側改動 → 零 Copy-on-Evolve。✅

### 2.5 正則陷阱（設計關鍵）

負向 lookahead `(?!.*X)` 配 `re.search` **必須 `\A` 錨定**，否則恆真：`re.search(r"(?s)(?!.*err)", "has err here")` 會在 err **之後**的位置匹配成功（放行含禁詞字串＝語意顛倒）；`re.search(r"(?s)\A(?!.*err)", "has err here")` 才正確回 None。故含負向片段者一律加 `\A`；純正向路徑無此需求，維持不加 `\A`（保留 improving_29 格式）。Architect 鏡已實跑反證此必要性。

### 2.6 B 軌 dogfooding — SCG 閘門對應

| SCG | 載體 |
|-----|------|
| SCG-0/1（需求/規格凍結） | 本計畫書 §0~§2 + 🔴 掌舵者 scope 選定（A 軌 / W-31-1） |
| SCG-2（介面設計） | §2.3 介面 delta + §2.4 設計審查 + §2.5 正則陷阱 |
| SCG-3（契約） | `_gherkin_to_regex` 負向分流純函式契約 |
| SCG-4（PR/實作） | §3 實作 + 單元/突變測試全綠 |
| SCG-5（RTM 覆蓋） | §4 RTM（本輪 AT 100% 覆蓋） |

---

## 3. 階段三：實作與雙重驗證

逐支開發-編譯-測試循環（絕不累積）。新增 **0 支源碼檔**，surgical 改 1 源碼 + 1 測試檔：

- `autoclaude/infra/adapters/sdd_to_playbook_adapter.py`（`_NEGATION_MARKER` 常數 + `_gherkin_to_regex` 分流，284→304 行）
- `tests/infra/test_sdd_to_playbook_adapter.py`（+`TestNegativeAssertionFidelity` **7 case** + `_NEG_SPEC` 輔具）

**共 +7 測試**（3196→3203），只增不減、0 failed。**突變實證**：把 `(?!` 翻成 `(?=`（語意顛倒）→ 5/7 負向測試轉紅；把切片 `line[:m.start()]` 改整行 `line` → 引號內否定測試轉紅；把 `if neg_frags:` 改 `if False:` → 5/7 轉紅；三組突變還原後 7/7 回綠（diff clean），證測試非假且鎖定 load-bearing 行為。

---

## 4. RTM（需求追溯矩陣）— 本輪 AT 100% 覆蓋

| AC | AT | 測試 | 狀態 |
|----|----|------|------|
| AC-31-1（負向斷言保真度） | AT-31-1-1 單負向→`\A(?!.*X)` 不出現語意（含→不過、不含→過） | `::TestNegativeAssertionFidelity::test_single_negative_requires_absence` | ✅ |
| AC-31-1 | AT-31-1-2 正負混合→`\A(?=.*P)(?!.*N)`（正存負缺過、含禁詞不過、缺正向不過） | `::test_mixed_positive_and_negative` | ✅ |
| AC-31-1 | AT-31-1-3 多負向→全部須不出現（count `(?!`==2） | `::test_multiple_negatives_all_absent` | ✅ |
| AC-31-1 | AT-31-1-4 英文否定標記（should not contain） | `::test_english_negation_marker` | ✅ |
| AC-31-2（向後相容，零行為變化） | AT-31-2-1 否定字眼在引號內→仍正向 `re.escape`（不含 `(?!`/`\A`） | `::test_negation_inside_quote_is_positive` | ✅ |
| AC-31-2 | AT-31-2-2 純正向 ≥2 引號維持 improving_29 格式（防退化哨兵，斷言 `\A`/`(?!` 不得出現） | `::test_positive_only_unchanged_no_anchor` | ✅ |
| AC-31-1 | AT-31-1-5 端到端：security 規格經 load_spec→expected_regex 同含 `(?=.*查詢成功)`＋`(?!.*password)` | `::test_end_to_end_negative_regex` | ✅ |

**覆蓋率**：本輪 2 AC / 全部 7 AT 100% 通過（+既有 `TestMultiAssertionCombination` 7 case + `test_gherkin_to_regex.py` 等全綠，證零退化）。

---

## 5. 階段四：CI 平價收斂（零退化驗證矩陣）

| 檢查 | 命令 | floor（improving_30 實測） | 本輪實測 | 判定 |
|------|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3196 / 0 failed | **3203 passed / 122 skipped / 0 failed**（115.84s） | ✅ +7 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | 8 kept / 0 broken | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 | total=18503 / cap=20438，violations=0 | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | FRESH | OK（FRESH，無新 port/plugin） | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 全綠 | exit 0（v0.01:1478 + v0.14:1593 + scripts:38） | ✅（持平，本輪零觸碰框架） |
| DAL 等價 | equivalence | 三後端等價 | 零 checkpoint/repository 變更（純轉譯），含於全套 | ✅ |
| 五軌 TLC | （僅 FSM 變更時） | — | **不觸發**（零 `_HAPPY_PATH`/`*.tla` 變更） | N/A |

---

## 6. 缺陷分流

- **本輪零框架缺陷、零整合層阻塞缺陷**（純 AutoClaude 正向轉譯保真度增強，零框架 v0.0X 變更）。
- **新增 DEF-31-001（P3，A 軌）**：SA-SD 鏡揭露——`_NEGATION_MARKER` 的孤立 `\bnot\b`/`\bnever\b` 對 `not only…but`、`is not empty` 等「含 not 但非否定語意」句式可能誤判為負向（僅同句含引號字面值時生效，影響面極小）。routed 觀察，若未來實測 SDD 規格出現此句式再行收斂；非阻塞本輪。
- open/routed 既有缺陷複驗：DEF-30-001（RFC 已決標記標準化，routed B 軌，**非本輪 A 軌 scope**）、DEF-19-001（catch 漸進覆蓋，routed B 軌）、DEF-01-007（cc-switch GUI，環境側 NOT FOUND 仍重現）、DEF-01-009（sdd_governance LOC watch，本輪未動該 plugin、violations=0 自癒，不觸發）、DEF-17-001（routed）——詳見 `AutoSDD_Defect_Log.md`。

**本輪新增防退化資產（非缺陷）**：`_gherkin_to_regex` 負向斷言分流由 `TestNegativeAssertionFidelity` 7 case 鎖定，正向橋接負向斷言 mis-specify 缺口閉合。三組突變實證（翻轉 lookahead / 整行切片 / 停用分流）證非假測試。

---

## 7. 結案四件套

1. 本計畫書 `docs/04_planning/AutoSDD_improving_31.md`
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_31.md`（審計 + 三鏡複審證據）
3. `docs/06_quality/AutoSDD_Defect_Log.md`（improving_31 複驗註記 + 新增 DEF-31-001）
4. 框架本體改進：**無**（零 v0.0X 變更）
