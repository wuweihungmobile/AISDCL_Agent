# AutoSDD_improving_75 — A 軌 pty-vs-sdk A/B 載具 compaction-cost 量測補強

> **本輪柱位**：**A 軌（整合）**——pty vs sdk 後端 A/B 對比載具的 compaction 成本量測能力補強（`tools/ab_compare_backends.py`）。
> **下一份**：`AutoSDD_improving_76.md`。
> **誠實級別**：**載具能力補強輪**（補 improving_73/74 §8 遞延候選 (a) 的**前置使能**：A/B 載具新增「壓縮次數 compact_count」差異維度 + 修 `halted` dead-parse〔DEF-75-001〕）。**非成熟度推進**，`L_合體 = min(A=L5, B=L5, C=L5) = L5` 維持。
> **🔴 誠實邊界（zero-trust，fail-loud）**：候選 (a) 完整面貌＝「**真跑**更長/觸發 compaction 的 playbook 取得 pty/sdk 實測 token 差異」，該真跑需**真 Claude API token、非離網 headless**（[ab_compare_backends.py:25,234-247](../../AutoClaude/tools/ab_compare_backends.py#L234-L247) 實跑模式呼叫真 `autoclaude` CLI → 真模型），本環境無法誠實完成 → **真跑部分維持延後**（待真 token session）。本輪交付的是「**讓真跑能分出差異**」的載具使能：目前載具只量 `peak_token_pct`（取 TOKEN_COMPACT 行最大 %），兩後端撞同一 80% 門檻時 peak 皆 ~80%、**分不出差異**；補上 compact_count 後，真跑時方能量化「各後端在長 playbook 下壓縮幾次」的成本差。
> **Copy-on-Evolve / 五軌 TLC**：本輪純 AutoClaude `tools/` 載具 + 其測試（`tests/tools/test_ab_compare_backends.py`），**未動 `AISDLC_SDD/` 任一檔、未碰 `*.tla`/FSM/DAL、未動 autoclaude/ 生產碼** → **免 Copy-on-Evolve、免五軌 TLC、DAL 等價 N/A**。

---

## 1. 本輪輸入（自上輪繼承）

### 1.1 improving_74 RTM / 遺留
- improving_74（commit 1d92b11）已結案：A 軌 wexpect 路徑 TIMEOUT/auto-respond/except 四出口分支測試覆蓋補強（生產碼零改），基線升至 **3381 passed / 122 skipped / 0 failed**。
- improving_74 §8 遞延 improving_75 候選：**(a)** 用更長/會觸發 compaction 的 playbook 跑 A/B 分出 token 峰值差異；**(b)** SD_09 W1 觀察期 #1 source-sha 閘門（時間閘 ~06-29~07-01 成熟後）。
- **本輪選 (a) 的可離網使能部分**：候選 (b) 時間閘未到（今日 2026-06-26 < ~06-29，延後正當）；候選 (a) 的**真跑**需真 token、非離網（誠實邊界，見題頭），但其**載具使能**（compact_count 差異維度）是具體、可單元測試、零生產碼風險的補強，當場做最符合「不要無謂延後」紀律（[[no-defer-unless-justified]]）——把「真跑才需 token」與「載具能力可離網先備好」誠實切分，不把整個 (a) 一律推延。

### 1.2 缺陷帳本 open/routed（階段一複驗）
- open：DEF-01-007（cc-switch GUI，P3，環境工具缺裝）/ DEF-01-009（sdd_governance_plugin LOC watch，P3）/ DEF-62-001（auto_recovery 註解滯後，P3 routed）/ DEF-23-005（RFC 生命週期自動化，P3 routed）。
- routed：DEF-17-001 / DEF-19-001 / DEF-35-001（P2，C 軌 SD_09 W1）/ DEF-42-001 等（皆 P3 除 DEF-35-001）。
- 本輪只動 `tools/ab_compare_backends.py`（載具解析函式）與其測試，未動 `sdd_governance_plugin`、未動 `auto_recovery`、未動 autoclaude/ 生產碼、未碰多後端真跑 A/B（不需 cc-switch）、未動 goal_synthesis → **不觸發任何既有 open/routed 缺陷**，全維持原狀態。
- **本輪新增 DEF-75-001**（P3）：A/B 載具 `halted` dead-parse（regex 解析進 `bools` 卻未寫回 RunMetrics），階段二設計時發現、**本輪閉環內以 W-75-3 修復**（見 §3 / Defect_Log）。

---

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit）— 硬閘 PASS

| 項目 | 命令 | 實測 | 判定 |
|------|------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3381 passed / 122 skipped / 0 failed**（69.06s） | = improving_74 實測值，**硬閘 PASS** |
| (b) lint-imports | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | 過 |
| (c) LOC 分級 | `python tools/check_loc_budget.py` | **violations=0**（total=19385 baseline=17032 cap=20438） | 過 |
| (d) Snapshot | `python tools/snapshot_sync.py --check` | **OK（FRESH）** | 過 |
| (e) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **exit 0**（v0.01:1478 / v0.26:1665 / scripts:129） | 過 |
| (f) 外部依賴形態 | 候選 (a) 真跑需真 token（[ab_compare_backends.py:234-247](../../AutoClaude/tools/ab_compare_backends.py#L234-L247) `subprocess.run` 呼叫真 `autoclaude` CLI → 真模型，**非離網 headless**） | 本輪只做**離網可測**的載具 parse 補強，**不觸發**真跑路徑 | 誠實邊界已確認、非 DEF-10-002a 陷阱 |
| (g) 本輪 W 項缺口偵察 | 載具現況：`RunMetrics.peak_token_pct` 取 TOKEN_COMPACT 行最大 %（[:111-118](../../AutoClaude/tools/ab_compare_backends.py#L111-L118)），**無壓縮次數指標**；`_RE_FIELD_BOOL` 含 `halted`（[:50](../../AutoClaude/tools/ab_compare_backends.py#L50)）但解析進 `bools` 後**僅取 success/escalated**（[:105-106](../../AutoClaude/tools/ab_compare_backends.py#L105-L106)），`halted` 從未寫回 → RunMetrics 無 `halted` 欄 | compact_count 缺口成立（差異維度）；halted dead-parse 缺陷成立 | **有實質 delta** |

> **硬閘**：(a) 基線 3381 = improving_74 實測值，無 failed、無低於上輪 → 准進階段二。

---

## 3. 階段二：增量設計

### 3.1 <Architecture_Design_Review>（寫實質 Python 前自審）

1. **架構純潔性**：**零 autoclaude/ 生產碼變更**——本輪僅改 `tools/ab_compare_backends.py`（A/B 分析載具，非 autoclaude 微核心生產碼）之純函式（`parse_run_metrics` / `aggregate_runs` / 兩個 `format_*`）+ additive dataclass 欄位。無新 class、無 God-object；`playbook_runner.py` Thin Facade 全無觸碰。載具不在 `autoclaude` package 相依圖內 → `.importlinter` 8 contract 不受影響。
2. **持久化相容**：**無新 PlaybookCheckpoint 欄位**、不動 DAL 三後端、不動 checkpoint → 零停機。新增的是載具解析結果 dataclass（`RunMetrics`/`AggregateMetrics`）的 additive 欄位，純記憶體、無持久化。
3. **安全防護網**：**不新增任何 autoclaude 生產碼路徑**、不新增「從文件生成指令」或 shell 字串路徑、不弱化 CONDITIONAL 三層。新增邏輯為純 log 文字 regex 計數（`TOKEN_COMPACT` 行計數、`halted` 布林讀回），無指令生成、無外呼。
4. **對外 I/O 安全**：**不新增 `ToolInvocationPort` 外呼路徑**、無 Web/HTTP/訊息新能力 → allowlist/SSRF 攻防本輪 N/A。

### 3.2 介面 delta

| 構件 | delta | LOC 落點 |
|------|-------|---------|
| `tools/ab_compare_backends.py` 模組常數 | 加 `_RE_TOKEN_COMPACT = re.compile(r"TOKEN_COMPACT")`（compact 行計數，與既有 peak 取值的 `"TOKEN_COMPACT" not in line` 字串判定同源語意） | 加 ~1 行 |
| `RunMetrics` dataclass | additive 加 `compact_count: int = 0` + `halted: bool = False`（向後相容，既有測試不檢查 → 不受影響） | 加 ~2 行 |
| `parse_run_metrics` | (1) compact_count = TOKEN_COMPACT 行數（與既有 peak 迴圈共用同一掃描，計 line 數）；(2) `m.halted = bools.get("halted", False)`（修 dead-parse） | 加 ~2 行 |
| `format_comparison` | 加列「壓縮次數（compact）」+「halted」 | 加 ~2 列 |
| `AggregateMetrics` dataclass | additive 加 `compact_count_mean: float=0.0` / `compact_count_total: int=0` / `compact_count_max: int=0` / `halted_count: int=0` | 加 ~4 行 |
| `aggregate_runs` | 聚合 compact_count（mean/total/max）+ halted_count（計數，對稱 success_count/escalated_count） | 加 ~4 行 |
| `format_aggregate_comparison` | 加列「壓縮次數 (mean / total / max)」+ halted 併入完成度列 | 加 ~2 列 |
| `tests/tools/test_ab_compare_backends.py` | 新增 W-75-1/2/3 回歸測試（synthetic log，含多 TOKEN_COMPACT 行 + `halted=True` 場景） | 新增測試 |

- **importlinter**：載具非 autoclaude package 成員、無新 autoclaude 跨層 import → **8 kept** 不變。
- **LOC**：`ab_compare_backends.py` 現 ~308 行，+~15 行 ≈ ~323，遠低於絕對紅線 750；`tests/` 不受 LOC tier。階段四以 `check_loc_budget` 實測 violations=0 驗證。

### 3.3 設計關鍵：為何這兩個維度值得補、且能以受控突變實證守界

候選 (a) 的價值在「長 playbook 觸發 compaction 時分出 pty/sdk 差異」。但既有載具的 `peak_token_pct` 在「兩後端都撞 80% compact 門檻」時**雙雙飽和於 ~80%、分不出差異**——peak 是「最高水位」，無法反映「churn 成本」。

- **W-75-1（compact_count）**：壓縮**次數**才是 churn 成本的直接代理——長 playbook 下，某後端若反覆逼近門檻被迫多次 `/compact`，其 token 重整成本顯著高於只壓一次的後端，但 peak 兩者相同。守界意圖（Rule 9）：compact_count = TOKEN_COMPACT 行數（每次達門檻印一行，[steps_orchestrator/_impl.py:233-235](../../AutoClaude/autoclaude/execution/steps_orchestrator/_impl.py#L233-L235)）；未觸發 → 0（誠實表「無壓縮」，非崩潰）。受控突變：把計數來源 regex 改成永不匹配 → compact_count 測試轉紅。
- **W-75-2（多輪聚合）**：N 輪統計才有對比力（沿 improving_72 W-72-2 既有聚合慣例）；compact_count 取 mean（平均每輪壓幾次）/ total（總壓縮）/ max（最壞單輪）。
- **W-75-3（halted dead-parse 修復，DEF-75-001）**：halt（≥90%）是 compact（≥80%）的孿生升級指標——撞 halt 代表該後端 token 失控到需 checkpoint 暫停，是比 compact 更嚴重的成本訊號。既有載具 regex 已解析 `halted` 卻丟棄（[:101-106](../../AutoClaude/tools/ab_compare_backends.py#L101-L106)），補上 RunMetrics.halted + halted_count 使 compaction 成本圖譜完整。守界意圖：`halted=True` 的 KernelResult → `m.halted is True`。受控突變：把 `m.halted = bools.get("halted", False)` 改回丟棄（`m.halted = False`）→ halted 測試轉紅。

---

## 4. 階段三：實作與雙重驗證

> （階段三/四回填：實作後填寫實作摘要、受控突變結果、測試守界意圖。）

### 4.1 實作（純 AutoClaude A 軌載具層、零 autoclaude/ 生產碼、無 Copy-on-Evolve）

- [tools/ab_compare_backends.py](../../AutoClaude/tools/ab_compare_backends.py)（git diff +35/-7）：
  - `RunMetrics` additive 加 `compact_count: int=0` + `halted: bool=False`（向後相容，既有測試不檢查新欄 → 不受影響）。
  - `parse_run_metrics`：(1) KernelResult bool 區塊加 `m.halted = bools.get("halted", False)`（修 DEF-75-001 dead-parse）；(2) 既有 peak 掃描迴圈內加 `compact_count += 1`（與 peak 共用同一次掃描，零額外迭代）。
  - `format_comparison` 加「壓縮次數（compact）」列 + 「run 成功 / escalated / halted」列（原 escalated 列擴 halted）。
  - `AggregateMetrics` additive 加 `compact_count_mean/total/max` + `halted_count`。
  - `aggregate_runs` 聚合 compact_count（mean/total/max）+ halted_count（計數，對稱 success/escalated_count）。
  - `format_aggregate_comparison` 加「壓縮次數 (mean / total / max)」列 + halted 併入完成度計數列。
- [tests/tools/test_ab_compare_backends.py](../../AutoClaude/tests/tools/test_ab_compare_backends.py)：新增 synthetic log `_TWO_COMPACTS`（兩次壓縮、peak 91%）/ `_HALTED`（撞 ≥90% halt）+ **9** 回歸測試（compact 計數 / 未壓縮回 0 / halted 寫回 / 未 halt 對稱 / halted 欄缺席兜底〔audit_75 SA-SD P1-1 閉環補〕/ 聚合 mean-total-max / 聚合 halted_count / 兩個 format 可讀性契約）+ 擴充既有 `test_aggregate_empty_is_zero_no_crash` 斷言新欄空輸入 default 0〔audit_75 SA-SD P1-2 閉環補〕。
- **autoclaude/ 生產碼零改動**（`git diff --stat` 只含 `tools/ab_compare_backends.py` + 測試兩檔，無 `autoclaude/` 任一檔）；載具非 autoclaude package 成員 → `.importlinter` 8 kept 不受影響。
- 載具 CLI 解析模式 smoke（不花 token）實證端到端：pty(2 壓縮/halted=False) vs sdk(0 壓縮/halted=True)，輸出表正確顯示 `壓縮次數 2 vs 0`、`halted False vs True`——peak 飽和分不出時，新維度分得出（中文 stdout 受 Windows cp950 顯示亂碼不影響數值，載具讀 UTF-8 log 檔）。

### 4.2 受控突變實證（測試非空殼，R-75-4）

| 突變 | 改動 | 對應測試 | 結果 |
|------|------|---------|------|
| MUT-75-1 | `parse_run_metrics` `compact_count += 1` → `+= 0` | `test_compact_count_counts_token_compact_lines` | **轉紅**（`AssertionError: 0 == 2`） |
| MUT-75-2 | `aggregate_runs` `compact_count_total = sum(cmp_)` → `= 0` | `test_aggregate_compact_count_mean_total_max` | **轉紅**（`AssertionError: 0 == 2`） |
| MUT-75-3 | `parse_run_metrics` `m.halted = bools.get("halted", False)` → `= False`（回退 dead-parse） | `test_halted_parsed_from_kernel_result` + `test_aggregate_halted_count` | **轉紅**（`AssertionError: 0 == 1` / halted is False） |

- 三處突變均以 **Edit 還原**（禁 `git checkout`，本輪含 tracked 未 commit 改動〔ab_compare_backends.py / test〕+ untracked 新檔〔計畫書〕，遵 [[git-checkout-mutation-revert-hazard]]）。
- 還原後 `grep MUT-75` 無殘留、載具 **26 passed** 復綠（原 17 + 9 新；含 audit_75 SA-SD 閉環補的 P1-1/P1-2）。

### 4.3 測試守界意圖（Rule 9）

- **W-75-1（compact_count）**：`assert m.compact_count == 2 and m.peak_token_pct == 91.0` 同守兩件事：壓縮次數與峰值**正交**——peak 取最高水位，compact_count 取 churn 次數；長 playbook 下兩後端 peak 可同為 ~80% 卻次數天差地別，次數才分得出成本差。MUT-75-1 證實計數退化即紅。
- **W-75-2（聚合）**：`mean==1.0 / total==2 / max==2`（N=2＝壓 2 次 + 壓 0 次）固化「多輪統計真實反映輪間 churn 離散」，非取首輪/末輪。MUT-75-2 證實聚合歸零即紅。
- **W-75-3（halted dead-parse 修復）**：`assert m.halted is True`（單輪）+ `halted_count == 1`（聚合 N=3）固化「halt〔≥90%〕是比 compact〔≥80%〕更嚴重的 token 失控訊號須被載具記錄」——既有 regex 已解析卻丟棄。MUT-75-3 證實回退丟棄即紅。`test_perfect_run_not_halted` 對稱守「預設不誤判為 True」。

## 5. 階段四：零退化驗證矩陣（全項實測，結案）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3381 / 0 failed | **3390 / 122 / 0**（floor 3381 + 9 新測〔含 audit P1 閉環補 1〕，68.09s） ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept | **8 kept / 0 broken** ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0**（total=19385 baseline=17032 cap=20438；載具 +35 行遠低於絕對紅線 750、tests/ 不受 tier） ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK（FRESH）** ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 | **N/A — 本輪零碰 AISDLC_SDD/**（`git status --short AISDLC_SDD/` = 空 鐵證）；階段一已實測 exit 0（v0.01:1478 / v0.26:1665 / scripts:129），本輪無觸發路徑 |
| 五軌 TLC | — | 僅 FSM 變更時 | **N/A — 條件未觸發**（git status 鐵證零碰 `*.tla`/FSM；TLC 不在 pytest 全套、需 Java+tla2tools，本輪確實未跑） |
| DAL 等價 | `tests/equivalence/`（隨全套） | 三後端等價 | **既有等價測試隨全套 3389 通過** ✅；本輪無新 DAL/checkpoint 改動 → 無新增針對性 round-trip 契約 |

---

## 6. RTM（需求追溯矩陣）

| 需求 | 來源 | 驗證 |
|------|------|------|
| R-75-1 A/B 載具量測壓縮次數（compact_count），分出長 playbook 下 pty/sdk churn 差異 | `parse_run_metrics` compact_count | `test_compact_count_counts_token_compact_lines` + `test_no_compact_means_zero_count` **PASS** |
| R-75-2 compact_count 多輪聚合（mean/total/max），對齊 improving_72 統計 A/B 口徑 | `aggregate_runs` | `test_aggregate_compact_count_mean_total_max` **PASS** |
| R-75-3 修復 halted dead-parse（DEF-75-001）：RunMetrics.halted 寫回 + halted_count 聚合 | `parse_run_metrics` halted + aggregate | `test_halted_parsed_from_kernel_result` + `test_perfect_run_not_halted` + `test_aggregate_halted_count` **PASS** |
| R-75-4 測試非空殼（受控突變實證） | 暫改載具對應分支 | MUT-75-1（`+=1`→`+=0`）+ MUT-75-2（total→0）+ MUT-75-3（halted 回退）各令對應測試**轉紅**，Edit 還原後 26 passed 復綠（§4.2） |
| R-75-5 零退化 | 收斂矩陣 | **3390/0**、8 kept、LOC 0、snapshot FRESH、零碰 SDD（§5） |
| R-75-6 報告可讀性契約：對比表含新指標標題 | `format_comparison` / `format_aggregate_comparison` | `test_format_comparison_has_compact_and_halted` + `test_format_aggregate_has_compact` **PASS** |

---

## 7. 多專家 Zero-Trust 審查結論

證據見 [AutoSDD_ZeroTrust_Audit_75.md](../06_quality/AutoSDD_ZeroTrust_Audit_75.md)。三鏡（Architect / SA-SD / QA）**全 OVERALL PASS、P0=0**：

- **Architect**：`git diff --stat` 實證只動 2 個 tracked AutoClaude 檔、零 autoclaude/ 生產碼；載具非 autoclaude package（`tools/__init__.py` 不存在、無 autoclaude import）→ importlinter 8 kept 不受影響；LOC 0、snapshot FRESH；計畫書誠實邊界切分清楚（「載具使能」非「已取得差異數字」）、未誇大；DEF-75-001 帳本證據與源碼一致、無漏記/虛報；ci-gate/TLC N/A 屬「條件未觸發」正當類型。**P0=0 / P1=0**。
- **SA-SD**：覆蓋缺口真偽確認——compact_count 差異維度論述成立（peak 飽和分不出時靠次數）、halted 確為真 dead-parse（改動前 RunMetrics 連 halted 欄都無、解析後完全丟棄）；設計正確（compact 與 peak 共用單次掃描、aggregate 慣例一致、halted_count 對稱 success/escalated_count）；8 測真綁 business logic 非空殼；載具 25 passed 實測。**揪 2 個 P1 測試對稱性缺口（非生產碼缺陷）**：P1-1 halted 欄缺席兜底未專測、P1-2 空輸入聚合新欄 default 未顯式斷言 → 依 [[no-defer-unless-justified]] **閉環內當場補**（新增 `test_halted_absent_field_defaults_false` + 擴充 `test_aggregate_empty_is_zero_no_crash`），載具 25→**26 passed**、全套 3389→**3390**。**P0=0 / P1=2（均已閉環補測）**。
- **QA**：_（序列化獨佔主樹複審回填：獨立全套 + 重做受控突變）_

---

## 8. 誠實級別標註

本輪＝**A 軌 A/B 載具 compaction-cost 量測能力補強輪（零 autoclaude/ 生產碼、修 1 個載具 P3 dead-parse），非成熟度推進**，`L_合體=min(A=L5,B=L5,C=L5)=L5` 維持。

- **首要成果**（待階段四定稿）：①A/B 載具新增 compact_count 差異維度（單輪 + 多輪聚合），使候選 (a) 真跑時方能量化「長 playbook 下 pty/sdk 壓縮成本差」（peak 飽和分不出時的補強）；②修復 halted dead-parse（DEF-75-001），補齊 compaction 成本圖譜（compact ≥80% + halt ≥90% 孿生指標）；③新測皆以受控突變實證非空殼。
- **🔴 誠實邊界**：候選 (a) 的**真跑**部分（真 token、長 playbook 實測 pty/sdk token 差異）本環境無法離網完成，**維持延後**至真 token session；本輪只交付離網可測的載具使能。**不虛報「已分出 token 峰值差異」**——本輪交付的是「讓真跑能分出差異」的能力，非差異數字本身。
- **遞延 improving_76 候選**：(a-真跑) 真 token session 跑更長 playbook 取得 pty/sdk compact_count/peak 實測差異（載具本輪已備好）；(b) SD_09 W1 觀察期 #1 source-sha 閘門（時間閘 ~06-29~07-01 成熟後）；(c) W-67-2 producer 端 SDD 模板 spec-format-version（需 Copy-on-Evolve v0.27）。

三件套：improving_75 / ZeroTrust_Audit_75 / Defect_Log（improving_75 recap + DEF-75-001）。
