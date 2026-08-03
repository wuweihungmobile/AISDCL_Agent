# AutoSDD_improving_86 — per-step token% 可觀測性 emit + 真跑填值（A 軌 × C 軌）

> **本輪柱位**：**A 軌（整合：pty/sdk per-step 真實 token% A/B + 多輪聚合）× C 軌（指揮官：生產 Kernel 加 per-step token% 可觀測性 emit）**。
> **下一份**：improving_87。
> **框架版**：本輪零碰 AISLDC_SDD 框架本體 → 免 Copy-on-Evolve、維持 v0.27。`L_合體=min(A,B,C)=L5` 不變（同源能力加固，非成熟度推進）。
> **掌舵者裁示**：AskUserQuestion 兩問——①柱位「真 token session 長 playbook A/B」；②真跑探測揭露可行性牆後二次裁「**加 per-step token% emit + 真跑填值**」（推薦選項）。

---

## §1 本輪輸入（自上輪繼承）

### 1.1 improving_85 結案狀態（RTM 收尾）
- improving_85＝A 軌 spec-format-version「生產端」閃閉 + Copy-on-Evolve v0.27（commit 14ab6bc，直推 main）。
- 已完成 W 項：W-85-1（生產端 v0.27 TCS 模板宣告）/ W-85-2（消費端 additive SddSpec + sdd_compile 退碼 5）/ W-85-3（+5 測）。
- 未完成 W 項：無（85 四件套完成、三鏡全 PASS）。
- 上輪審計遺留：無阻斷項；兩鏡非阻斷觀察已當場閉環（SA-SD 路徑小瑕、QA pytest 浮動註記）。

### 1.2 缺陷帳本 open / routed（本輪處置計畫）
| 缺陷 | 狀態 | 本輪處置 |
|------|------|---------|
| DEF-01-007（cc-switch GUI 環境缺裝 P3） | open | 不涉多後端切換 → 維持原狀態 |
| DEF-01-009（sdd_governance_plugin LOC watch P3） | open watch | 零碰 sdd_governance_plugin → 維持 |
| DEF-23-005（RFC 生命週期 P3） | open | 不涉 → 維持 |
| DEF-62-001（auto_recovery 註解滯後 P3） | open | 不涉 → 維持 |
| DEF-17-001（遙測） | routed | 不涉 → 維持 |
| DEF-19-001（catch 漸進） | routed | 不涉 → 維持 |
| DEF-35-001（goal_synthesis mutmut P2，繫 C 軌 SD_09 W1） | routed | 本輪非 SD_09 W1 → 維持 |

### 1.3 上輪遺留候選（improving_85 §8）
- (a) SD_09 W1 觀察期 #1 source-sha 閘門——時間閘 ~2026-06-29 成熟（今 6/27 未到）→ 本輪不取。
- (b) **真 token session 跑更長 playbook 取 pty/sdk 逐步驟實測差異（載具 improving_76 已備 per-step）→ 本輪取（掌舵者裁示）。**
- (c) v2.0 不相容格式端到端驗證防漂移閘——待 production 真跨版漂移，本輪不取。

---

## §2 階段一實測（Zero-Trust Re-Audit，2026-06-27）

> 派 Explore agent 全程親跑（非採信文件宣稱），硬閘 PASS 才進階段二。

| 項目 | 命令 | 實測 | 狀態 |
|------|------|------|------|
| (a) AutoClaude 全套 pytest | `python -m pytest tests/ -q`（Bash） | **3493 passed / 0 failed / 122 skipped**（總收集 3615；floor 3488 +5） | ✅ 硬閘 PASS |
| (b) lint-imports | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ |
| (c) LOC budget | `python tools/check_loc_budget.py` | violations=0（total 19778 / cap 20438） | ✅ |
| (d) snapshot | `python tools/snapshot_sync.py --check` | OK（FRESH） | ✅ |
| (e) AISDLC_SDD ci-gate | `bash scripts/ci-gate.sh` | exit 0（v0.01:1478 / v0.27:1665 / scripts:129；arch_fitness fail=0） | ✅ |
| (f) git 工作樹 | `git status --short` | 乾淨 | ✅ |
| (g) 上輪構件 | 開檔核對 | spec_format_version 欄(spec_source.py:67)/load_spec 寫入(adapter:132)/sdd_compile 退碼5(:95-99)/v0.27 4 TCS 模板宣告 全存在 | ✅ 無虛報 |

### 2.1 (f) 外部工具依賴形態確認（本輪涉真 claude 真跑）
- claude CLI＝`/c/Users/wuwei/.local/bin/claude` 2.1.144（在 PATH）；credentials.json 今 09:06 更新（訂閱 OAuth 有效）；SDK 0.2.110 已裝。
- ab_configs 齊備：ab_pty / ab_sdk / lowthr_compact / lowthr_halt。

### 2.2 真跑探測鐵證（improving_77/81 紀律：不採信推測、真跑驗證）
單輪真跑 `sdd_bridge_smoke.yaml`（pty config，scratchpad workdir）：
- `KernelResult.peak_token_pct` = **6.1566%**（整輪 observer 真值，端到端流動，與 improving_83 吻合）。
- `TOKEN_COMPACT`/`TOKEN_HALT` marker = **0 個**（低負載未撞 80/90% 門檻）。
- per-step token% 訊號 = **不存在**（`peak_token_pct` 整輪只 1 次、非逐步驟）。

**結論（決定本輪設計）**：載具 per-step token% 只能從門檻 marker 擷取，而 observer 真值是整輪單一數字 → **低負載真跑下 per-step token% 恆 0%**。要取逐步驟真值，要嘛撞門檻（~80 萬 token，極貴且 improving_84 已證觸發路徑端到端會動＝冗餘），要嘛**在生產 Kernel 加 per-step token% 可觀測性 emit**（仿 improving_71 per-step CORRECTION）。掌舵者裁「加 emit + 真跑填值」。

---

## §3 階段二增量設計

### 3.1 W 項（≤3）

| W 項 | 軌道 | 內容 | LOC 落點 |
|------|------|------|---------|
| **W-86-1** | C 軌（生產 Kernel） | `_run_step` execute 後、consult_token_guard 前，`observer.peak_pct > 0` 時 emit `=== STEP_TOKEN_PEAK \| step=Sxx pct=NN.NNNN ===`（observability-only、additive、零行為變更，仿 improving_71 CORRECTION marker line 245-247） | kernel.py +~5 行（380→~385，service tier ≤500、absolute ≤750） |
| **W-86-2** | A 軌（載具） | (1) 新 regex `_RE_STEP_TOKEN_PEAK` 解析 marker → `per_step[sid].peak_token_pct = max(...)`（使低負載真跑 per-step token% 為真值）；(2) `AggregateMetrics` 加 per-step 多輪聚合維度（`StepAggregate` + `per_step_agg` + `format_step_aggregate_comparison`）——候選 (3) 明標「per-step 多輪聚合誠實切分未做」缺口 | ab_compare_backends.py +~55 行 |
| **W-86-3** | A 軌（真跑） | 真 token 跑 `sdd_bridge_smoke.yaml` pty/sdk 各 N 輪，取逐步驟真實 token% A/B + 多輪聚合，實證新 per-step 訊號端到端流動 | 無新生產碼（真跑取證） |

### 3.2 介面 delta
- **kernel.py**（W-86-1）：`_run_step` 內新增一段 `logger.info("=== STEP_TOKEN_PEAK | step=%s pct=%.4f ===", task.step_id, observer.peak_pct)`，**guard `if observer.peak_pct > 0`**。落點＝execute（line 191）後、`_consult_token_guard`（line 195）前——涵蓋所有 attempt（成功/失敗），與 `_consult_token_guard` 自身 `peak_pct<=0` 不 emit 的零退化原則對齊。無新方法、無簽名變更、無新 import（`observer` 已在作用域）。
- **ab_compare_backends.py**（W-86-2）：
  - `_RE_STEP_TOKEN_PEAK = re.compile(r"STEP_TOKEN_PEAK\s*\|\s*step=([A-Za-z0-9_\-]+)\s+pct=(\d+(?:\.\d+)?)")`
  - `parse_run_metrics`：TOKEN_COMPACT/HALT 迴圈後加一段 `for mt in _RE_STEP_TOKEN_PEAK.finditer(...)` → `_step_of(m, sid).peak_token_pct = max(existing, pct)`。**不影響** `m.peak_token_pct`（整輪 marker peak）與 `observer_peak_token_pct`（KernelResult 真值），僅補 per-step。
  - 新 `@dataclass StepAggregate(step_id, n, peak_token_pct_mean, peak_token_pct_max, compact_count_total, correction_count_total)`。
  - `AggregateMetrics` 加 `per_step_agg: dict[str, StepAggregate] = field(default_factory=dict)`（additive）。
  - `aggregate_runs`：聚合 per-step——收集 N 輪所有 step_id 聯集，每 step_id 取出現輪數 n、peak mean/max、compact/correction total。
  - 新 `format_step_aggregate_comparison(pty, sdk, max_steps=30)`：逐步驟多輪聚合 pty vs sdk 表，沿用 improving_76 有界截斷（防彈渲染器）。
  - `main` 多輪分支（n>1）追加印 `format_step_aggregate_comparison`。

### 3.3 `.importlinter` 各 contract 影響分析
- W-86-1：kernel.py 無新 import（observer、logger 既有）→ 8 contract 全不受影響。
- W-86-2：載具屬 `tools/`，非 `autoclaude/` 套件，不在 importlinter 掃描範圍 → 零影響。

### 3.4 checkpoint additive 欄位需求
- 無。STEP_TOKEN_PEAK 是純 log marker，不寫 PlaybookCheckpoint、不碰 DAL 三後端 → 持久化零影響。

### 3.5 RTM 需求列（測試意圖，Rule 9）
| RTM | 意圖（守什麼） | 測試 |
|-----|--------------|------|
| RTM-86-1 | peak>0 時 Kernel 發 STEP_TOKEN_PEAK marker（per-step token% 唯一可觀測來源；缺失即 A/B 無法量 per-step token） | `test_step_token_peak_marker_emitted_when_peak_positive`（caplog + SequencedTokenExecutor pct=6.0） |
| RTM-86-2 | peak==0（dry-run/fake 無 token 訊號）時**不發** marker（零退化、不虛報 token） | `test_no_step_token_peak_marker_when_no_token_signal`（pct=None） |
| RTM-86-3 | 載具解析 STEP_TOKEN_PEAK 進 per_step[sid].peak_token_pct（低負載即真值、不靠門檻） | `test_parse_step_token_peak_into_per_step` |
| RTM-86-4 | 載具 per-step 多輪聚合：mean/max/total 正確（候選 3 缺口） | `test_aggregate_per_step_across_runs` |
| RTM-86-5 | per-step 多輪聚合 format 含有界截斷（防彈渲染器） | `test_format_step_aggregate_bounded` |

### 3.6 <Architecture_Design_Review>
1. **架構純潔性**：W-86-1 是 observability-only `logger.info`（不改控制流、不創 God-object）；kernel.py +~5 行仍 < service tier 500、< absolute 750；Thin Facade（playbook_runner）零碰。✅
2. **持久化相容**：無新 checkpoint 欄位（純 log marker）；DAL 三後端零影響、零停機維持。✅
3. **安全防護網**：無新 CONDITIONAL 路徑（marker 是內部 log，非從文件生成指令）；白名單消毒無新攻擊面。✅
4. **對外 I/O 安全**：無新 `ToolInvocationPort` 外呼路徑；allowlist/SSRF 不適用。✅

### 3.7 B 軌 dogfooding scope
- 本輪零碰 AISLDC_SDD 框架本體（生產碼在 AutoClaude `core/kernel.py` + 載具 `tools/`）→ 免 Copy-on-Evolve、免五軌 TLC（零碰 `*.tla`/FSM）。
- 計畫書（本檔）= SCG-0/1 載體；§3 介面 delta = SCG-2；§3.5 RTM = SCG-5 雛形。

---

## §4 實作與雙重驗證（階段三回填）

### 4.1 實作進度
- **W-86-1**（kernel.py:192-202）：`_run_step` execute 後加 `if observer.peak_pct > 0` → emit `=== STEP_TOKEN_PEAK | step=Sxx pct=%.4f ===`。kernel.py 380→390 行（< service 500 / absolute 750）。測試 `tests/core/test_kernel_step_token_peak.py`（RTM-86-1/2，2 測）→ core 全套 318 passed 零退化。
- **W-86-2**（ab_compare_backends.py）：`_RE_STEP_TOKEN_PEAK` regex + parse 解析進 per_step + `StepAggregate` + `AggregateMetrics.per_step_agg` + `aggregate_runs` per-step 聚合 + `format_step_aggregate_comparison`（有界截斷）+ main n>1 分支追印。載具 547→627 行（< absolute 750）。測試 +6（RTM-86-3/4/5）→ 載具 65 passed。
- **W-86-1+2 合計 +8 新測**；lint 8 kept / 0 broken、LOC violations=0。

### 4.2 受控突變實證（非空殼，禁 git checkout，遵 [[git-checkout-mutation-revert-hazard]]）
| 突變 | 改動 | 預期轉紅 | 實測 |
|------|------|---------|------|
| MUT-86-1 | kernel guard `>0`→`>=0`（無訊號也印 0.0000） | RTM-86-2 | ✅ 轉紅（`step=S01 pct=0.0000` 被印），Edit 還原復綠 |
| MUT-86-2 | 載具 parse `float(mt.group(2))`→`0.0`（不取真值） | RTM-86-3/相關 | ✅ 3 測轉紅（per_step 全 0），Edit 還原復綠 |
| MUT-86-3 | aggregate per-step `mean`→`max`（破壞統計語意） | RTM-86-4 | ✅ 轉紅（mean 期望 6.0 得 8.0），Edit 還原復綠 |

還原後 67 passed（2 kernel + 65 載具）；git diff 僅預期新增行（kernel +10 / 載具 +85/-2），無突變殘留。

### 4.3 真跑取證（W-86-3）
**單輪 pty 真跑（端到端鐵證）**：production log 印出
`STEP_TOKEN_PEAK | step=S01 pct=6.0613` + `step=S02 pct=6.1760`，KernelResult 整輪 `peak_token_pct=6.176`（= max(S01,S02)，一致）。
> **🔴 真跑浮動註記（SA-SD 鏡複核）**：pct 絕對值每次真跑略有浮動（claude 回應長度不同；SA-SD 鏡獨立真跑得 S01 6.0580/S02 6.1726），屬真跑正常差異——**不變式「整輪 peak = 各步 max」恆成立、per-step token% 恆 >0（修前恆 0）**，數值浮動不影響本輪結論。**per-step token% 修前恆 0%、現低負載真跑即真值** → W-86-1 端到端閉合、候選 (3) per-step 真值缺口解除。

**N=2 完整 pty/sdk A/B（多輪聚合 + per-step 聚合，exit 0）**：

整輪多輪聚合：兩後端皆 N=2、一次通過率 100%、0 correction、0 violation、2/2 success；**token 峰值 pty 6% vs sdk 2%**（有訊號輪數 2/2，非 marker-only 的 0%）。

**per-step 多輪聚合（W-86-2 新交付，首次有真值）**：
| 步驟 | pty (peak mean/max% / compact / corr) | sdk (peak mean/max% / compact / corr) |
|------|------|------|
| S01 | 6/6% / 0 / 0 (n=2) | 2/2% / 0 / 0 (n=2) |
| S02 | 6/6% / 0 / 0 (n=2) | 2/2% / 0 / 0 (n=2) |

**意義**：修前此表所有 token% 格恆 0%（per-step token 只能從門檻 marker 來、低負載恆乾）；W-86-1 emit + W-86-2 解析後，**逐步驟真實 token% 的 pty-vs-sdk A/B 差異首次呈現**（pty ~6% / sdk ~2%，3 倍差＝PtyExecutor 解析 claude -p PARTIAL_OUTPUT vs SDK `get_context_usage().percentage` 兩條管道的真實讀數差，與 improving_83 整輪 6.2/2.0 吻合）。候選 (3)「per-step 多輪聚合誠實切分未做」缺口閉合。

> **誠實限制**：本 smoke 刻意簡短（2 步、皆 attempt 1 過），per-step compact/correction 維度恆 0（未觸發）；本輪真正分出的是**逐步驟 token% 的後端差異**。更長 playbook 會顯示更多步驟的 per-step 差異（載具有界截斷已備），但成本更高，非本輪必要。

---

## §5 零退化驗證矩陣（階段四回填「實測」欄）

| 檢查 | 命令 | 通過條件（floor=improving_85 實測） | 實測 |
|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3488 passed / 0 failed | ✅ **3501 / 0 / 122 skipped**（3493 基線 +8 新測） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken | ✅ 8 kept / 0 broken |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0 | ✅ violations=0（total 19783 / cap 20438；kernel 390 / 載具 627） |
| Snapshot | `python tools/snapshot_sync.py --check` | FRESH | ✅ OK |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 | ✅ **N/A 類型①**——本輪零碰 AISLDC_SDD/（`git status --short AISDLC_SDD/`=空白 鐵證）；階段一已實測 exit 0 |
| DAL 等價 | equivalence job | 三後端等價 | ✅ **N/A 類型②**——`tests/equivalence/` 隨全套 3501 通過、本輪零 DAL/checkpoint 改動、無新 round-trip 契約 |
| 五軌 TLC | （僅 FSM 變更時） | 五軌 0 violation | ✅ **N/A 類型①**——零碰 `*.tla`/FSM/`_HAPPY_PATH`（git diff 僅動 kernel.py + 載具 + 測試 + docs）、TLC 不在 pytest 全套需 Java |

---

## §6 缺陷帳本本輪更新
- **本輪無新增 DEF**：W-86-1 是 observability-only log marker（不改控制流、不從文件生成指令）；W-86-2 是純載具解析/聚合；真跑無揭露新框架摩擦或工具錯誤。
- open/routed 缺陷複驗：DEF-01-007 / DEF-01-009 / DEF-23-005 / DEF-62-001（open）+ DEF-17-001 / DEF-19-001 / DEF-35-001（routed）全維持原狀態——本輪只動 kernel.py + 載具 + 測試，未觸碰任一缺陷標的、無重現惡化。

## §7 結案總結
本輪＝**A 軌 × C 軌：per-step token% 可觀測性 emit + 真跑填值**。閉合候選 (3)「per-step 多輪聚合誠實切分未做」與「逐步驟真實 token% 差異」缺口。
- W-86-1（C 軌生產 Kernel）：`STEP_TOKEN_PEAK` 可觀測標記，使低負載真跑亦逐步驟可觀測（additive、observability-only、零退化）。
- W-86-2（A 軌載具）：解析該標記進 per_step + per-step 多輪聚合（StepAggregate）+ 有界渲染。
- W-86-3（A 軌真跑）：真 token N=2 pty/sdk A/B，per-step 多輪聚合首次有真值（S01/S02 各 pty 6% vs sdk 2%）。
- 零退化 3501/0/122、lint 8 kept、LOC 0、snapshot OK；3 受控突變全轉紅還原；零碰 AISLDC_SDD。`L_合體=L5` 維持（同源能力加固）。

## §8 誠實限制與遞延候選
- **誠實限制**：(1) smoke 2 步皆 attempt 1 過 → per-step compact/correction 維度恆 0（未觸發），本輪真正分出的是逐步驟 token% 後端差異；(2) per-step token% 是「成功 attempt 觀測到的峰值」逐步驟呈現，撞門檻（80/90%）仍需 ~80 萬 token 長 playbook（improving_84 已證觸發路徑端到端會動，非本輪標的）。
- **遞延候選 improving_87**：(a) SD_09 W1 觀察期 #1 source-sha 閘門（時間閘 ~6/29 成熟）；(b) 更長/更重 playbook 真跑取多步驟 per-step token% 差異（載具有界截斷已備、本輪 2 步已驗機制）；(c) v2.0 不相容格式端到端驗證防漂移閘 production 攔阻。
