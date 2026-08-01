# AutoSDD_improving_32 — A 軌正向轉譯保真度（狀態碼否定斷言 negation-aware）

> **本輪主柱**：**A 軌（整合 / 雙向協作）** — 推進 AISDLC-SDD × AutoClaude 深度整合（北極星第 3 點）。
> **下一份**：`AutoSDD_improving_33.md`（按需）。
> **防跨軌誤指**：本輪在 **A 柱（雙向協作）**，非 B 柱（手腳框架）亦非 C 柱（指揮官內部）。
> 本輪**零框架 v0.0X 變更**（無 Copy-on-Evolve、五軌 TLC 不觸發），所有交付在 AutoClaude 側。
>
> **角色**：Dr. Alan（L10 自治系統與微核心架構總監）
> **日期**：2026-06-18 ｜ **承上**：improving_31 結案（A 軌引號負向斷言 negation-aware，tag `v2026.06.18-29` / commit `1d547c1`）

---

## 0. 北極星對齊

對齊北極星**第 3 點「完美協調溝通機制」**：AutoClaude 利用 AISLDC_SDD 進行軟體開發、建立兩者**雙向橋接**，成為端到端自動化開發 Agent。

正向鏈（SDD→Playbook 轉譯保真度）已於 improving_29（多引號 AND under-specify）、improving_31（**引號**負向斷言 mis-specify）連續閉合。本輪閉合 improving_31 在**姊妹分支留下的對稱缺口**：`_gherkin_to_regex` 的 **status-code 路徑仍有與引號路徑完全相同的 mis-specify bug**——`Then 系統不應回傳 500` 被 `_STATUS_CODE` 匹配為 `(?i)(500)`＝**要求** 500 出現，語意完全顛倒。improving_31 只修了引號路徑、未碰狀態碼路徑，本身留下**對稱不一致**；閉合它屬「修正 > 完整」最高優先類別。

成熟度三軸（`AutoSDD_Maturity_Rubric.md`，`L_合體 = min(A,B,C)`）：本輪續推 **A 軌（協作自治）**。**禁宣稱 L 級躍升**：本輪僅補一條狀態碼否定斷言分流（純函式、向後相容、零持久化），是正向橋接保真度的最小誠實一步，`L_合體` 仍受最弱軸卡住、不變。

---

## 1. 階段一：現況重偵察（Zero-Trust Re-Audit）— 實測事實

派 Explore agent 親跑實測（**硬閘 PASS**，准入階段二）。所有數字來自當前回合真實 tool_result：

| 檢查 | 命令 | 實測 | 判定 |
|------|------|------|------|
| AutoClaude pytest | `python -m pytest tests/ -q` | **3203 passed / 122 skipped / 0 failed**（109.59s） | ✅ floor=3203 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ |
| LOC budget | `python tools/check_loc_budget.py` | total=18503 / cap=20438，violations=0 | ✅ |
| snapshot | `python tools/snapshot_sync.py --check` | OK（FRESH） | ✅ |
| AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | exit 0（v0.01:1478 + v0.14:1593，arch_fitness fail=0/warn=3 advisory） | ✅ |
| 最新框架版本 | — | **v0.14**（active RFC 已清空、.gitkeep only；本輪零觸碰） | — |

**外部工具依賴（階段一 (f)）**：本輪純 AutoClaude 整合層內部純函式增量（gherkin 文字 → regex），無 A/B 後端切換、無外部 CLI/服務、無訊息平台——不適用（DEF-01-007 cc-switch `command -v` NOT FOUND 仍重現，與本輪無關）。

**上輪構件複驗（zero-trust）**：improving_31 宣稱構件真實存在——`_NEGATION_MARKER`（`sdd_to_playbook_adapter.py:71`/`:247`）、`TestNegativeAssertionFidelity`（`test_sdd_to_playbook_adapter.py:303`）。

**A 軌標的測繪（決定 W 項，zero-trust 親讀碼 + 真實模板對照）**：

| 段 | 構件 | 現況（file:line） |
|----|------|-------------------|
| 正向多引號 AND | `_gherkin_to_regex` ≥2 引號→lookahead | 成熟（improving_29） |
| **引號**負向斷言 | `_gherkin_to_regex` pos/neg_frags 分流（引號路徑） | 成熟（improving_31） |
| **狀態碼**負向斷言（mis-specify） | `_gherkin_to_regex` status-code 路徑（`:263-272`）對否定一律當正向 → 「不應回傳 500」譯成 `(?i)(500)`＝要求 500 出現 | **本輪標的（improving_31 留下的對稱缺口）** |

**候選排除（誠實揭露，Rule 2 反投機）**：親查證實際框架規格——
- Gherkin `But` 關鍵字支援：`AISDLC_SDD` 全庫 `^\s*But\s` **零出現** → 排除（投機，同 DEF-31-001 戒）。
- 未消費的 precondition metadata、`_scenario_of` 順序偏置：影響面低 / 非保真度核心 → 排除。

---

## 2. 階段二：增量設計（A 軌，掌舵者已選定主柱）

### 2.1 scope 決策

🔴 掌舵者選定主柱＝**A 軌（續推雙向橋接保真度）**。親讀碼後鎖定 improving_31 在 status-code 姊妹分支留下的**對稱 mis-specify 缺口**為最高價值標的：

- improving_31 修了引號路徑的負向語意顛倒，但 `_gherkin_to_regex` 的 status-code fallback 路徑（無引號時才走）**仍對否定一律當正向**：`Then 系統不應回傳 500` → `_STATUS_CODE` 匹配 → `(?i)(500)`＝**要求** 500 出現，與「不應回傳 500」語意完全顛倒。
- 這是 improving_31 **自己引入的對稱不一致**（修引號、漏姊妹分支），非新臆測缺口；改法可直接複用 `_NEGATION_MARKER`。
- 安全/隱私類 AC 高度依賴否定句式（不洩漏內部錯誤碼、不得回傳 5xx 堆疊），此 codebase 安全面尤甚——與 improving_31 §2.1 立論的**同一 bug class**（improving_31 測試用例 `不應顯示「internal error」` 等亦非模板逐字，立論依 bug class 而非模板背書）。

### 2.2 本輪 W 項（單一 W，Rule 2 最小）

| W 項 | 構件 | 檔案 | tier/LOC |
|------|------|------|----------|
| **W-32-1** | `_gherkin_to_regex` status-code 路徑加入 negation-aware：偵測狀態碼**之前**是否有否定標記，命中 → `(?s)\A(?!.*<code>)`（要求不出現），否則維持既有 `(?i)(code\|phrase)`。引號路徑 / 多引號 / 量化 / quoted-wins / fallback bit-for-bit 不變 | `infra/adapters/sdd_to_playbook_adapter.py` | adapter ≤400（305→313） |

**零新 config flag、零新 port/plugin/常數/方法**：surgical 重構既有 status-code 分支，複用 improving_31 既有 `_NEGATION_MARKER`（Rule 2/3）。

### 2.3 介面 delta

```python
# _gherkin_to_regex status-code 路徑（其餘 quoted/量化/fallback 不變）：
status = _STATUS_CODE.search(line)
if status:
    code = status.group(1)
    if _NEGATION_MARKER.search(line[: status.start()]):   # 否定標記在狀態碼之前
        return rf"(?s)\A(?!.*{code})", False               # 要求該碼不出現（\A 錨定同 W-31-1）
    parts = [code]                                          # 正向路徑 bit-for-bit 不變
    if status.group(2):
        parts.append(re.escape(status.group(2).strip().lower()))
    return "(?i)(" + "|".join(parts) + ")", False
```

### 2.4 `<Architecture_Design_Review>`（寫實質 Python 前自我驗證）

1. **架構純潔性**：純函式（無 IO/副作用），零新 import 邊（不碰任一 importlinter contract）；adapter 305→313 < 400。Thin Facade 不動、無 God-object、無新 port/plugin/常數/方法。✅
2. **持久化相容**：零 checkpoint schema 變更、零 DAL 變更、零 alembic → 三後端零影響。✅
3. **安全防護網**：負向片段（純狀態碼數字）進 `expected_output_regex`，走 evaluator `re.search`（**非 shell 指令**）→ 無 shell 注入面；否定標記只讀已過 AT row 白名單的 gherkin；CONDITIONAL 三層消毒 + `_EVALUATOR_TEMPLATES` 白名單完全不動。✅
4. **對外 I/O 安全**：未新增 `ToolInvocationPort` 外呼路徑，allowlist 不涉及。✅
5. **紅線守界 / 零退化**：僅偵測到否定標記（且在狀態碼之前）才走 `\A(?!...)`；正向 status 路徑 bit-for-bit 不變（improving_01 `(?i)(201|created)` 不破）；quoted-wins 保留（status 僅在無引號時評估）；量化路徑（`_QUANTITATIVE`）不變。零 `_HAPPY_PATH`/`*.tla` 變更 → 五軌 TLC 不觸發；AutoClaude 側改動 → 零 Copy-on-Evolve。✅

### 2.5 正則陷阱（設計關鍵）

負向 lookahead `(?!.*X)` 配 `re.search` **必須 `\A` 錨定**（同 W-31-1），否則於 X 之後位置恆真（放行含禁碼字串＝語意顛倒）；正向 status 路徑無此需求，維持 `(?i)(code|phrase)` alternation。**scope 邊界（誠實揭露，Rule 2/12）**：僅否定**狀態碼數字**（canonical 信號、case 無關）；尾隨描述片語（如 "Internal Server Error"）刻意不納入負向 lookahead，避免引入 `(?i)` 與既有 W-31-1 負向格式不一致的複雜度——若未來實測規格需片語級否定再行擴充。

### 2.6 B 軌 dogfooding — SCG 閘門對應

| SCG | 載體 |
|-----|------|
| SCG-0/1（需求/規格凍結） | 本計畫書 §0~§2 + 🔴 掌舵者 scope 選定（A 軌 / W-32-1） |
| SCG-2（介面設計） | §2.3 介面 delta + §2.4 設計審查 + §2.5 正則陷阱 |
| SCG-3（契約） | `_gherkin_to_regex` status-code 否定分流純函式契約 |
| SCG-4（PR/實作） | §3 實作 + 單元/突變測試全綠 |
| SCG-5（RTM 覆蓋） | §4 RTM（本輪 AT 100% 覆蓋） |

---

## 3. 階段三：實作與雙重驗證

逐支開發-編譯-測試循環（絕不累積）。新增 **0 支源碼檔**，surgical 改 1 源碼 + 1 測試檔：

- `autoclaude/infra/adapters/sdd_to_playbook_adapter.py`（status-code 路徑加 negation-aware 分流，305→313 行）
- `tests/infra/test_sdd_to_playbook_adapter.py`（+`TestNegativeStatusAssertionFidelity` **6 case** + `_NEG_STATUS_SPEC` 輔具）

**共 +6 測試**（3203→3209），只增不減、0 failed。**突變實證**（兩組，皆 in-memory 備份還原，不碰 git）：
- **M1**：把 `if _NEGATION_MARKER.search(line[: status.start()]):` 改 `if False:`（停用否定分流）→ 4 負向測試轉紅、正向哨兵 + quoted-wins 維持綠。
- **M2**：把 `(?!` 翻成 `(?=`（語意顛倒回去）→ 4 負向測試轉紅。
- 兩組還原後 49/49 回綠（diff clean），證測試非假且鎖定 load-bearing 行為。

> **本輪流程教訓（記入缺陷帳本 DEF-32-001）**：M1 突變初次用 `git checkout -- <file>` 還原，誤抹除本輪**未提交**的 W-32-1 源碼改動（git checkout 還原到 HEAD=improving_31）。當場以 grep 偵測 `W-32-1 GONE` 後重新套用，並改用 in-memory 備份還原做 M2。教訓：對未提交工作樹改動做突變還原，**禁用 `git checkout`**，須用 in-memory／備份還原。

---

## 4. RTM（需求追溯矩陣）— 本輪 AT 100% 覆蓋

| AC | AT | 測試 | 狀態 |
|----|----|------|------|
| AC-32-1（狀態碼否定斷言保真度） | AT-32-1-1 單否定狀態碼→`\A(?!.*500)` 不出現語意（不含→過、含→不過） | `::TestNegativeStatusAssertionFidelity::test_single_negative_status_requires_absence` | ✅ |
| AC-32-1 | AT-32-1-2 英文否定標記（must not return 403） | `::test_negative_status_english_marker` | ✅ |
| AC-32-2（向後相容，零行為變化） | AT-32-2-1 正向狀態碼維持 `(?i)(201\|created)`（防退化哨兵，斷言 `\A`/`(?!` 不得出現） | `::test_positive_status_unchanged_sentinel` | ✅ |
| AC-32-1 | AT-32-1-3 scope 邊界：僅否定狀態碼數字、尾隨片語不納入（regex 不含 "internal"） | `::test_negative_status_ignores_trailing_phrase` | ✅ |
| AC-32-2 | AT-32-2-2 quoted-wins 保留：引號 + 否定狀態碼混合 → 走引號路徑、狀態碼不評估 | `::test_quoted_wins_over_negative_status` | ✅ |
| AC-32-1 | AT-32-1-4 端到端：security 規格經 load_spec→expected_regex == `(?s)\A(?!.*500)` | `::test_end_to_end_negative_status_regex` | ✅ |

**覆蓋率**：本輪 2 AC / 全部 6 AT 100% 通過（+既有 `TestNegativeAssertionFidelity` 7 case + `TestMultiAssertionCombination` 7 case + status-code 既有 case 全綠，證零退化）。

---

## 5. 階段四：CI 平價收斂（零退化驗證矩陣）

| 檢查 | 命令 | floor（improving_31 實測） | 本輪實測 | 判定 |
|------|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3203 / 0 failed | **3209 passed / 122 skipped / 0 failed**（110.22s） | ✅ +6 |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | 8 kept / 0 broken | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 | total=18506 / cap=20438，violations=0 | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | FRESH | OK（FRESH，無新 port/plugin） | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 全綠 | exit 0（持平，本輪零觸碰框架） | ✅ |
| DAL 等價 | equivalence | 三後端等價 | 零 checkpoint/repository 變更（純轉譯），含於全套 | ✅ |
| 五軌 TLC | （僅 FSM 變更時） | — | **不觸發**（零 `_HAPPY_PATH`/`*.tla` 變更） | N/A |

---

## 6. 缺陷分流

- **本輪零框架缺陷、零整合層阻塞缺陷**（純 AutoClaude 正向轉譯保真度增強，零框架 v0.0X 變更）。
- **新增 DEF-32-001（P3，A 軌 / 流程摩擦，fixed@improving_32）**：突變測試還原誤用 `git checkout -- <file>` 抹除未提交改動（見 §3 教訓）。已當場偵測重套並改 in-memory 還原；institutionalize 為紀律「對未提交工作樹改動做突變還原禁用 git checkout」。
- **新增 DEF-32-002（P3，A 軌 / 保真度 scope，routed 未來輪）**：SA-SD 鏡揭露——負向狀態碼斷言只比對數字，當規格為「不應回傳 500」而被測系統輸出僅含描述片語（如 "Internal Server Error"）不帶數字時會**漏放**（誤判通過）。已於 §2.5/AT-32-1-3 文件化為刻意 scope 限縮；屬「不完整」而非「錯誤」，仍**單調優於修正前的語意顛倒**（修正前要求 500 出現）。觸發需「規格用否定狀態碼句式 + 系統輸出只含片語不含數字」雙條件，且框架真實 gherkin 此組合尚未出現。routed：待未來實測規格出現片語級否定需求再擴充。
- open/routed 既有缺陷複驗：DEF-31-001（`_NEGATION_MARKER` 孤立 `\bnot\b`/`\bnever\b` 誤判，routed）——本輪複用同一 marker，**誤判 root cause（裸 not 過度匹配）不變，但覆蓋路徑由引號路徑延伸至狀態碼路徑**（SA-SD 鏡實測 `Then the cache is not warm but 系統回傳 500` 同行裸 not + 狀態碼會被誤分流為 `(?s)\A(?!.*500)`）；根因同 DEF-31-001、歸其 routed 範疇，狀態碼同行裸 not 組合於真實框架 gherkin 未出現。DEF-30-001（RFC 已決標記標準化，routed B 軌）、DEF-19-001（catch 漸進覆蓋 39 規則 catch_count 機制已就位待 runtime 資料，routed B 軌）、DEF-01-007（cc-switch GUI，環境側 NOT FOUND 仍重現）、DEF-01-009（sdd_governance LOC watch，本輪未動該 plugin、violations=0 不觸發）、DEF-17-001（routed）——詳見 `AutoSDD_Defect_Log.md`。

**本輪新增防退化資產（非缺陷）**：`_gherkin_to_regex` status-code 否定斷言分流由 `TestNegativeStatusAssertionFidelity` 6 case 鎖定；正向橋接「狀態碼否定 mis-specify」缺口閉合，improving_31 留下的引號/狀態碼對稱不一致消解。M1/M2 兩組突變實證證非假測試。

---

## 7. 結案四件套

1. 本計畫書 `docs/04_planning/AutoSDD_improving_32.md`
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_32.md`（審計 + 三鏡複審證據）
3. `docs/06_quality/AutoSDD_Defect_Log.md`（improving_32 複驗註記 + 新增 DEF-32-001）
4. 框架本體改進：**無**（零 v0.0X 變更）
</content>
</invoke>
