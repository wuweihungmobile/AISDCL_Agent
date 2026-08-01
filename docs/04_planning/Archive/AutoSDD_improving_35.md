# AutoSDD_improving_35 — C 軌 SD_09 W1 GoalSynthesis mutation pilot 準備（多模組鎖定契約前置）

> **軌道①整合迭代** 第 35 輪。**本輪主柱＝C 軌（指揮官 AutoClaude）**。🔴 掌舵者定調：
> 推進 SD_09 W1 GoalSynthesis mutation pilot **準備**（軸 D 安全區），本輪交付 W-35-1＝
> 多模組鎖定契約測試前置。下一份：`AutoSDD_improving_36`（按需）。
>
> **凍結**：2026-06-18。tag 待定。前輪：improving_34（C 軌 W0 狀態檢點輪，零源碼變更，tag v2026.06.18-32）。

---

## 0. 本輪定位與防跨軌誤指

| 項目 | 內容 |
|------|------|
| 軌道 | ① 整合迭代（根層 docs/） |
| 主柱 | **C 軌**（AutoClaude 自身能力 / SD_09 W1 pilot 準備） |
| 工作流帳本 | `AutoClaude/docs/04_planning/SD_Improving_09.md`（C 軌沿用其 G0~G6 與 W 紀律） |
| 缺陷回流 | 根層 `docs/06_quality/AutoSDD_Defect_Log.md`（新增 DEF-35-001） |
| 下一份 | `AutoSDD_improving_36`（按需） |

---

## 1. 階段一：現況重偵察（Zero-Trust Re-Audit，硬閘通過）

Explore agent 主樹實測（皆附證據，禁文件宣稱）：

| 項目 | 實測 | 結論 |
|------|------|------|
| (a) AutoClaude 全套 pytest | **3214 passed / 122 skipped / 0 failed**（112.08s） | = 上輪基線，硬閘通過 |
| (b) lint-imports | 8 kept / 0 broken | PASS |
| (c) LOC / snapshot | violations=0（18506≤20438）/ FRESH | PASS |
| (d) AISDLC_SDD ci-gate | v0.01:1478 + v0.14:1593 全綠 + arch_fitness exit 0 | PASS |
| (e) improving_34 構件 | improving_34.md / Audit_34.md / `tools/g0_gate_check.ps1`（commit 77d3321）全存 | PASS |
| (f) 缺陷帳本 open/routed | open 6 / routed 3，已盤點 | — |

**本輪 floor = 3214 passed。**

### 1.1 W1 真實狀態（誠實 scoping — 決定本輪 scope 的關鍵事實）

研究 agent 與主 agent 親讀 [SD09_Execution_Guide.md:307-341](../../AutoClaude/docs/05_development/SD09_Execution_Guide.md)、[g0_gate_check.ps1](../../AutoClaude/tools/g0_gate_check.ps1)、[goal_synthesis_plugin.py](../../AutoClaude/autoclaude/plugins/goal_synthesis_plugin.py)、[mutation_baseline_lock.py](../../AutoClaude/tools/mutation_baseline_lock.py) 後確認：

1. **W1「執行」被 G0 閘門 blocked**：G0 = #2 AC4 ready（12/14，~06-20）+ #3 obs/drift green_streak≥30（22/30，~06-26）兩者皆過，**最遲 06-26 才開**。W1 task list 之 T1-B1（tag）、T1-B6（兩週 nightly）、T1-B7（Report）全依賴 G0。#1 unique sha 解凍須 W1 合法改 token_guard 源碼自然產生，**紀律 #12 明禁人工 churn**；主 agent 亦不得偽造 nightly。
2. **mutation 多模組鎖定核心邏輯已存在**：[mutation_baseline_lock.py:38-60](../../AutoClaude/tools/mutation_baseline_lock.py#L38-L60) 的 `TARGETS`／`_MODULE_PATHS` 已含 `goal_synthesis`（目標 0.70 / effective 0.63），`should_lock`/`append_history`/`write_baseline` 全 per-module 參數化。→ T1-B4/B5「確認支援多模組」≈ 已支援。
3. **唯一真實缺口 = 多模組並存契約測試不存在**：T1-B8 指定的 `tests/contract/test_mutation_multi_module_lock.py` 不存在。

**結論**：本輪非「大型 Wave」，而是受 06-26 G0 閘門限制的小型安全區前置。掌舵者定調本輪交付 **W-35-1（補多模組契約測試）**。

---

## 2. 階段二：增量設計（W-35-1）

### <Architecture_Design_Review>

1. **架構純潔性**：純新增單一測試檔 `tests/contract/`，**零生產源碼變更**、無新 God-object、Thin Facade 不受影響。
2. **持久化相容**：未觸碰 PlaybookCheckpoint／DAL 三後端，零停機相容維持。
3. **安全防護網**：未新增任何指令生成路徑，CONDITIONAL 三層防禦不受影響。
4. **對外 I/O 安全**：未新增 `ToolInvocationPort` 外呼路徑，allowlist 不受影響。

### 2.1 W-35-1 設計（介面 delta / 不重疊定位）

| 項目 | 內容 |
|------|------|
| 新增檔 | `AutoClaude/tests/contract/test_mutation_multi_module_lock.py`（4 case + 3 helper） |
| LOC 落點 | 測試檔，不納入 `check_loc_budget` 生產分級（violations=0 維持） |
| `.importlinter` 影響 | 無（測試不在 8 條 contract 約束範圍） |
| checkpoint additive | 無 |
| 不重疊性（Rule 3） | 既有 `test_mutation_baseline_lock.py`（contract+tools 兩處）多在 `should_lock` 純函數層或單模組 `run()`；本檔聚焦「兩模組並存於同一 `.mutation_history.jsonl`／`.mutation_baseline.toml`、經 `run()` 端到端 + `load_module_history` 篩選」整合層契約 |

**關鍵事實**：[mutation_baseline_lock.py:326](../../AutoClaude/tools/mutation_baseline_lock.py#L326) `should_lock` 用 `history[-7:]` **不自行 filter module**——模組隔離靠 `load_module_history(path, module)` 先篩選。故隔離驗證對象為 `load_module_history` + `run()` 端到端。

### 2.2 四 case 設計（對應 T1-B8）

| case | 驗證 | 隔離/語意 |
|------|------|----------|
| 1 `test_two_modules_lock_independently_via_run` | GS+TG 各連續達標 → `run()` 端到端各自鎖定，baseline 兩行並存 | write_baseline per-module upsert 不互踩 |
| 2 `test_shared_history_file_module_isolation` | 同一 history 檔交錯兩模組各 7 筆 → `load_module_history` 篩選隔離 + 各自 `should_lock` | tail 不被他模組污染 |
| 3 `test_one_module_dip_does_not_block_other` | TG 單日抖動跌破不鎖；GS 達標仍鎖 | 一模組抖動不波及另一 |
| 4 `test_per_module_threshold_applied_distinctly` | 同一 0.65 落 GS(eff 0.63) 與 TG(eff 0.68) 之間 → GS 鎖、TG 拒鎖 | per-module TARGETS 正確套用 |

### 2.3 誠實 scope 邊界（不偽造覆蓋，Rule 12）

- **T1-B8 字面第 4 項「模組間 LRU 順序」** 屬 ci.yml 三 cron active-module 輪替（排程層、W1 執行期），`mutation_baseline_lock` 純函數層**無 LRU 機制**；本檔以「per-module 目標差異隔離」（case 4）覆蓋等價的模組區分語意，**LRU 輪替留 W1 執行期**，誠實標示不偽造。
- 測試全程以 `run(..., source_path=<tmp mock dir>)` 注入 mock 模組目錄，**不依賴真實 `_MODULE_PATHS` 佈局**——既保穩健（Rule 9），亦迴避 DEF-35-001（見 §5），不把 bug 釘成期望行為。

---

## 3. 階段三：實作與雙重驗證

- 實作：新增 `test_mutation_multi_module_lock.py`（4 case）。
- 單元驗證：`pytest tests/contract/test_mutation_multi_module_lock.py -v` → **4 passed**。
- **突變實證（Rule 9，in-memory 還原禁 git checkout，DEF-32-001）**：
  - M1：`should_lock` 門檻寫死 `target = 0.75`（不依 module）→ `test_per_module_threshold_applied_distinctly` **FAILED**（GS 被誤套 0.68 門檻，stderr `reject reason=kill_rate_below_threshold threshold=0.6800`）。
  - M2：`write_baseline` 非 upsert（`existing = {}`）→ `test_two_modules_lock_independently_via_run` **FAILED**（先鎖模組被覆蓋）。
  - 還原後 4 passed，source 零內容 diff（CRLF→LF 行尾差異以 `git checkout` 補正——該檔本輪無有意改動，安全）。

---

## 4. 階段四：CI 平價收斂（零退化矩陣）

| 檢查 | 命令 | 通過條件（floor=3214） | 實測 |
|------|------|----------------------|------|
| AutoClaude 全套 | `pytest tests/ -q` | ≥ 3214 / 0 failed | **3218 / 122 / 0**（+4）✅ |
| 架構契約 | `lint-imports` | 全 kept | **8 kept / 0 broken** ✅ |
| LOC 分級 | `check_loc_budget.py` | 全過 | violations=0 ✅ |
| Snapshot | `snapshot_sync.py --check` | 新鮮 | OK / 對齊 ✅ |
| AISDLC_SDD 閘門 | `ci-gate.sh` | not-chaos 全綠 | 本輪**零碰**，引階段一 v0.01:1478 / v0.14:1593 全綠 ✅ |
| DAL 等價 | equivalence | 三後端等價 | 未改 DAL，不受影響 ✅ |
| 五軌 TLC | — | — | 無 FSM/*.tla 變更，不觸發 ✅ |

---

## 5. 缺陷（DEF-35-001，routed W1）

**發現**：W-35-1 設計期親驗 — `autoclaude/plugins/goal_synthesis` **目錄不存在**（實體為單檔 `goal_synthesis_plugin.py`），但 [mutation_baseline_lock.py:58](../../AutoClaude/tools/mutation_baseline_lock.py#L58) `_MODULE_PATHS["goal_synthesis"]` 與 W1 T1-B3 的 `--paths-to-mutate=autoclaude/plugins/goal_synthesis` 都當它是目錄。

**後果**：W1 啟動後 `compute_source_sha256("goal_synthesis")` 對不存在目錄 `rglob` → 永遠回 `"unknown"` → GS 無法滿足 unique sha 鎖定；mutmut 亦找不到 mutate 目標。

**分流**：routed SD_09 W1 執行期（修法涉 production 配置——`_MODULE_PATHS` 指向單檔 + `compute_source_sha256` 支援單檔，或將 goal_synthesis 拆 package 比照 token_guard；屬 production 行為變更，超出本輪安全區，**確認前不動實作**）。詳見 Defect_Log。

---

## 6. RTM（需求可追溯矩陣）

| 需求 | 設計 | 實作 | 驗證 |
|------|------|------|------|
| W-35-1 多模組並存鎖定回歸保護 | §2.1/§2.2 四 case | `test_mutation_multi_module_lock.py` | 4 passed + M1/M2 突變實證 |
| 零退化 | §4 矩陣 | 純新增測試 | 3218/122/0、lint 8/0、LOC 0、snapshot OK |
| 誠實 scope（不偽造 LRU/不依賴真實佈局） | §2.3 | source_path 注入 + case 4 等價語意 | 主樹 zero-trust OVERALL PASS 5/5 |
| W1 前置缺陷揭露 | §5 | DEF-35-001 | audit 親驗屬實，routed W1 |

---

## 7. 結案

- W-35-1 交付完成，零退化、4 case 全綠 + 突變實證、主樹 zero-trust OVERALL PASS 5/5。
- DEF-35-001 記入帳本 routed W1（W1 啟動前必修，否則 GS mutation 無法鎖定）。
- **下一份 `AutoSDD_improving_36`（按需）**：建議＝06-26 G0 開啟後的 W1 正式執行輪（先修 DEF-35-001 module path，再啟 GS pilot 兩週 nightly）。
- 審計證據見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_35.md`。
