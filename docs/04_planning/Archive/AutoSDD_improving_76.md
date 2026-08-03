# AutoSDD_improving_76 — A 軌 pty-vs-sdk A/B 載具「逐步驟指標歸因 + 有界渲染」

> **本輪柱位**：**A 軌（整合）**——pty vs sdk 後端 A/B 對比載具的「**更長 playbook**」量測使能（`tools/ab_compare_backends.py`）：補上**逐步驟（per-step）指標歸因**與**有界渲染（bounded truncation）對比報告**。
> **下一份**：`AutoSDD_improving_77.md`。
> **誠實級別**：**載具能力補強輪 + 跨輪觀測缺口修復（DEF-76-001 載具側）**（接續 improving_75，補候選 (a)「真跑更長 playbook」的**前置使能**：現載具只有「整輪」總和指標，長 playbook 看不出**哪幾步**造成 pty/sdk 分歧；補上 per-step 拆分 + 長報告有界截斷。**並於 audit 期 zero-trust 複核揭露並修復 DEF-76-001**：載具 peak/compact 原僅解析 `TOKEN_COMPACT`〔只在**已棄用** `_impl.py:233` 印〕，production 唯一正式路徑 Kernel 不印它 → improving_71/75 的 peak/compact 在真跑恆 0；本輪載具側納入 production 的 `TOKEN_HALT` marker 解析）。**非成熟度推進**，`L_合體 = min(A=L5, B=L5, C=L5) = L5` 維持。
> **🔴 設計演進誠實標註**：本計畫書 §3 原設計為 2 個 W 項（per-step 歸因 + 有界渲染，純載具能力補強）。**§4.1 起的 W-76-2（TOKEN_HALT/DEF-76-001）係階段三 audit 三鏡複核時新發現**（SA-SD 揪 CORRECTION 雙 emit site → parent zero-trust 連帶查出 token marker production-blind）——非事前規劃，閉環內補入（遵 [[no-defer-unless-justified]]：載具側可離網即修者當場修，production Kernel marker 需生產碼者 routed improving_77）。據實標註以維 SDD 規格先行誠實性，不偽裝成事前已設計。
> **🔴 誠實邊界（zero-trust，fail-loud）**：候選 (a) 完整面貌＝「**真跑**更長/觸發 compaction 的 playbook 取得 pty/sdk 實測 token 差異」，該真跑需**真 Claude API token、非離網 headless**（[ab_compare_backends.py:255-268](../../AutoClaude/tools/ab_compare_backends.py#L255-L268) 實跑模式呼叫真 `autoclaude` CLI → 真模型），本環境無法誠實完成 → **真跑部分維持延後**（待真 token session）。本輪交付的是「**讓真跑能逐步驟分出差異**」的載具使能：以合成 log（錨 production Kernel 真實標記格式）覆蓋 per-step 解析與有界渲染，**不花 token、不觸發真跑路徑**。
> **Copy-on-Evolve / 五軌 TLC**：本輪純 AutoClaude `tools/` 載具 + 其測試（`tests/tools/test_ab_compare_backends.py`），**未動 `AISDLC_SDD/` 任一檔、未碰 `*.tla`/FSM/DAL、未動 autoclaude/ 生產碼** → **免 Copy-on-Evolve、免五軌 TLC、DAL 等價 N/A**。

---

## 1. 本輪輸入（自上輪繼承）

### 1.1 improving_75 RTM / 遺留
- improving_75（commit b39eb49）已結案：A 軌 A/B 載具 compaction-cost 量測補強（compact_count 差異維度 + 多輪聚合 + 修 DEF-75-001 halted dead-parse），基線升至 **3390 passed / 122 skipped / 0 failed**。
- improving_75 §8 遞延 improving_76 候選：**(a-真跑)** 真 token session 跑更長 playbook 取得 pty/sdk compact_count/peak 實測差異（載具已備好整輪維度）；**(b)** SD_09 W1 觀察期 #1 source-sha 閘門（時間閘 ~06-29~07-01）；**(c)** W-67-2 producer 端 SDD 模板 spec-format-version（需 Copy-on-Evolve v0.27）。
- **本輪選 (a) 的下一段可離網使能（使用者拍板）**：候選 (b) 時間閘未到（今日 2026-06-26 < ~06-29，延後正當）；候選 (c) 需開 v0.27 凍結版、本輪不啟動框架本體演化。候選 (a) 的**真跑**需真 token、非離網（誠實邊界，見題頭），但 improving_75 只補了「整輪」compact_count——**真跑一旦在長 playbook（多步）上跑，整輪總和無法定位是哪一步驟驅動分歧**，這個 per-step 缺口是具體、可單元測試、零生產碼風險的補強，當場做最符合「不要無謂延後」紀律（[[no-defer-unless-justified]]）：把「真跑才需 token」與「逐步驟載具能力可離網先備好」誠實切分。

### 1.2 缺陷帳本 open/routed（階段一複驗）
- 活躍 open/routed（階段一複驗，逐一核對狀態欄真相源）：DEF-01-007（cc-switch GUI，P3，環境工具缺裝）/ DEF-01-009（sdd_governance_plugin LOC watch，P3）/ DEF-62-001（auto_recovery 註解滯後，P3 routed）/ DEF-17-001（routed，殘留面已轉 DEF-18-001）/ DEF-42-001（AISDLC_SDD test_file_lock Windows flaky，P3 routed）/ DEF-35-001（P2，C 軌 SD_09 W1 時間閘）。
- improving_75 recap 誤列為 open/routed 的 DEF-23-005 / DEF-19-001，階段一核對狀態欄真相源確認實為 **fixed@improving_30 / closed@improving_40**（口誤沿錄，非真 open）。
- 本輪只動 `tools/ab_compare_backends.py`（載具解析/格式函式）與其測試，未動 `sdd_governance_plugin`、未動 `auto_recovery`、未動 autoclaude/ 生產碼、未碰多後端真跑 A/B（不需 cc-switch）、未動 goal_synthesis → **不觸發任何既有 open/routed 缺陷**，全維持原狀態。
- 本輪**未新增缺陷**（階段三/四回填確認；若實作中發現框架摩擦即記入 Defect_Log）。

---

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit）— 硬閘 PASS

實測由獨立 Explore/general-purpose agent 親跑（非引用文件宣稱值）：

| 項目 | 命令 | 實測 | 判定 |
|------|------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3390 passed / 122 skipped / 0 failed**（69.86s） | = improving_75 實測值，**硬閘 PASS** |
| (b) lint-imports | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（196 files / 492 deps） | 過 |
| (c) LOC 分級 | `python tools/check_loc_budget.py` | **violations=0**（total=19385 baseline=17032 cap=20438） | 過 |
| (d) Snapshot | `python tools/snapshot_sync.py --check` | **OK（FRESH）** | 過 |
| (e) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **exit 0**（v0.01:1478 / v0.26:1665 / scripts:129；arch_fitness advisory warn 不阻擋） | 過 |
| (f) improving_75 構件查證 | `tools/ab_compare_backends.py` compact_count（:65）/ 多輪聚合（:176-178,187）/ DEF-75-001 halted 修復（:109）+ 測試覆蓋（`test_ab_compare_backends.py:248,266,289,303`） | 真實存在且被測試覆蓋，**無虛報** | 過 |
| (g) 本輪 W 項缺口偵察 | 載具現況：`RunMetrics` 全為**整輪總和**（completed/total、first_pass_rate、correction_count、peak_token_pct、compact_count、halted）——**無逐步驟拆分**；`format_comparison` 僅整輪 7 列、無 per-step 表；長 playbook（多步）下無法定位哪步驟驅動 pty/sdk 分歧 | per-step 歸因缺口成立（長 playbook 量測使能）；無 bounded 渲染（長報告會無限長） | **有實質 delta** |

> **生產碼標記格式查證（zero-trust，直接讀生產碼非憑測試 fixture）**：三種標記皆帶步驟 id，per-step 歸因有鐵證——
> - TOKEN_COMPACT：`=== STATE: TOKEN_COMPACT | [%s] %.0f%% >= %.0f%% ===`（[steps_orchestrator/_impl.py:233-234](../../AutoClaude/autoclaude/execution/steps_orchestrator/_impl.py#L233-L234)，`task.step_id` → `[S01]`）
> - ✓ 成功標記：`f"[{task.step_id}] {task.name} ✓ (attempt {attempt + 1})"`（[core/kernel.py:185](../../AutoClaude/autoclaude/core/kernel.py#L185) + [_impl.py:257](../../AutoClaude/autoclaude/execution/steps_orchestrator/_impl.py#L257)）
> - CORRECTION：`=== STATE: CORRECTION | step=%s attempt=%d ===`（[core/kernel.py:224](../../AutoClaude/autoclaude/core/kernel.py#L224)，`task.step_id` → `step=S01`）

> **硬閘**：(a) 基線 3390 = improving_75 實測值，無 failed、無低於上輪 → 准進階段二。

---

## 3. 階段二：增量設計

### 3.1 <Architecture_Design_Review>（寫實質 Python 前自審）

1. **架構純潔性**：**零 autoclaude/ 生產碼變更**——本輪僅改 `tools/ab_compare_backends.py`（A/B 分析載具，非 autoclaude 微核心生產碼）之純函式（`parse_run_metrics` 解析 + 新增 `format_step_comparison`）+ additive dataclass（新 `StepMetrics` + `RunMetrics.per_step` 欄）。無 God-object（`StepMetrics` 為純資料 dataclass，無方法/無副作用）；`playbook_runner.py` Thin Facade 全無觸碰。載具不在 `autoclaude` package 相依圖內 → `.importlinter` 8 contract 不受影響。
2. **持久化相容**：**無新 PlaybookCheckpoint 欄位**、不動 DAL 三後端、不動 checkpoint → 零停機。新增的是載具解析結果 dataclass（`StepMetrics`/`RunMetrics.per_step`）的 additive 欄位，純記憶體、無持久化。
3. **安全防護網**：**不新增任何 autoclaude 生產碼路徑**、不新增「從文件生成指令」或 shell 字串路徑、不弱化 CONDITIONAL 三層。新增邏輯為純 log 文字 regex 計數與分組（依 `[Sxx]` / `step=Sxx` 把既有指標歸到步驟），無指令生成、無外呼。
4. **對外 I/O 安全**：**不新增 `ToolInvocationPort` 外呼路徑**、無 Web/HTTP/訊息新能力 → allowlist/SSRF 攻防本輪 N/A。

### 3.2 介面 delta

| 構件 | delta | LOC 落點 |
|------|-------|---------|
| `tools/ab_compare_backends.py` 模組常數 | 加 `_RE_STEP_TAG = re.compile(r"\[([A-Za-z0-9_\-]+)\]")`（自 TOKEN_COMPACT/✓ 行抽步驟 id）；`_RE_CORRECTION_STEP = re.compile(r"STATE:\s*CORRECTION\s*\|\s*step=([A-Za-z0-9_\-]+)")`（CORRECTION 行抽 step=） | 加 ~2 行 |
| `StepMetrics` dataclass（新） | 純資料：`step_id: str` + `compact_count: int=0` + `peak_token_pct: float=0.0` + `correction_count: int=0`（三維皆既有整輪指標的逐步驟拆分；無方法、無副作用） | 加 ~8 行 |
| `RunMetrics` dataclass | additive 加 `per_step: dict[str, StepMetrics] = field(default_factory=dict)`（向後相容，既有測試不檢查 → 不受影響；空 dict＝無 per-step 資訊，誠實表「無步驟標記」） | 加 ~1 行 |
| `parse_run_metrics` | 既有掃描迴圈內順帶歸因：TOKEN_COMPACT 行抽 `[Sxx]` → per_step[sxx].compact_count++ / peak=max；CORRECTION 行抽 `step=Sxx` → per_step[sxx].correction_count++。整輪總和**不變**（per_step 為旁路新增，不改既有欄位語意） | 加 ~12 行 |
| `format_step_comparison`（新） | 產出 per-step × backend Markdown 表（步驟 id × {pty compact/peak/correction} vs {sdk ...}）；**有界渲染（bounded truncation）**：`max_steps` 參數（預設 30），超出時截斷並印 `… (N more steps elided)`，杜絕長 playbook（數十步）報告無限長/Token 爆炸（對齊範本「防彈渲染器」紀律）。步驟順序＝兩後端 step_id 聯集、穩定排序 | 加 ~22 行 |
| `main()` CLI | 解析模式（`--pty-log`+`--sdk-log`）額外印 `format_step_comparison`（整輪表後附 per-step 表）；`--max-steps` 參數（預設 30）透傳 bounded 上限 | 加 ~3 行 |
| `tests/tools/test_ab_compare_backends.py` | 新增 W-76 回歸測試（synthetic「長 playbook」log，含 ≥6 步、逐步驟不同 compact/correction 樣態 + 超 max_steps 截斷場景） | 新增測試 |

- **importlinter**：載具非 autoclaude package 成員、無新 autoclaude 跨層 import → **8 kept** 不變。
- **LOC**：`ab_compare_backends.py` 現 329 行，+~48 行 ≈ ~377，遠低於絕對紅線 750（tools/ 受絕對紅線管轄、不受 tier 分級）；`tests/` 不受 LOC tier。階段四以 `check_loc_budget` 實測 violations=0 驗證。

### 3.3 設計關鍵：為何 per-step 與 bounded 渲染值得補、且能以受控突變實證守界

候選 (a) 的價值在「**長** playbook 觸發 compaction 時分出 pty/sdk 差異」。improving_75 已補整輪 compact_count，但「整輪壓了幾次」在多步 playbook 下**無法定位是哪一步驟**逼近門檻——A/B 報告若只說「pty 壓 8 次、sdk 壓 3 次」，舵手仍不知該優化哪一步。長 playbook 的可行動性，仰賴**逐步驟拆分**。

- **W-76-1（per-step 歸因）**：把既有三個 churn/成本維度（compact_count / peak_token_pct / correction_count）依 log 內步驟 id（`[Sxx]` / `step=Sxx`，§2 生產碼鐵證）歸到各步驟。守界意圖（Rule 9）：per_step 為整輪總和的**精確拆分**——`sum(s.compact_count for s in per_step) == 整輪 compact_count`（不變式），且無步驟標記時 per_step 為空 dict（誠實表「無 per-step 資訊」，非崩潰、非臆造）。受控突變：把 CORRECTION 的 step 抽取改成永不匹配 → per-step correction 歸因測試轉紅。
- **W-76-2（有界渲染對比報告）**：長 playbook 可能數十步，逐步驟表若不截斷會無限長、撐爆報告/Token（範本〈防彈渲染器〉：有界截斷 + 揭露省略數）。`format_step_comparison(pty, sdk, max_steps=30)` 超出時只印前 `max_steps` 步 + `… (N more steps elided)` 一行，杜絕 OOM/Token 爆炸；步驟順序為兩後端聯集穩定排序（A/B 對齊，缺一邊的步驟以 0 補位、誠實表「該後端未在此步留標記」）。守界意圖：6 步表完整顯示、超 max_steps 必出現 elided 行且行數有界。受控突變：移除截斷邏輯（印全部） → 截斷測試（斷言「不含尾部步驟、含 elided」）轉紅。

- **W-76-2（DEF-76-001 載具側修復，audit 期新增）**：載具 `parse_run_metrics` 掃描迴圈原僅認 `TOKEN_COMPACT`，本輪納入 `TOKEN_HALT`（`is_halt = "TOKEN_HALT" in line`）——production 唯一正式路徑 Kernel（`main.py:123`「雙路徑已移除」）不印 TOKEN_COMPACT〔只棄用 `_impl.py:233` 印〕、token 壓力以 `_token_halt.py:46` 的 `TOKEN_HALT | [Sxx] context NN%`（≥90%）表達。納入後 peak/per-step peak「哪路徑印就抓哪個」（halt≠compact churn 故 compact_count 不計入 halt）。**production 端 Kernel observability marker 補強需生產碼 → routed improving_77**（justified：非純載具、仿 W-71-2 為 Kernel 補 CORRECTION）。守界意圖：TOKEN_HALT 92% 餵入 peak。受控突變 MUT-76-4（`is_halt` 改 `False`）→ production peak 歸 0 轉紅。
- **附：CORRECTION per-step 下界誠實邊界（audit SA-SD P1）**：CORRECTION 兩 emit site——Kernel `kernel.py:224` 帶 `step=`（per-step production 有效）、已棄用 `_impl.py:437`「諮詢 Minimax」不帶 → per-step correction 為**下界**（`sum(per_step) ≤ 整輪`，等號僅 Kernel 路徑成立）。原「三種標記皆帶 step id」overclaim 已訂正為此誠實邊界。

> **本輪不做（誠實切分，避免 scope creep，Rule 2）**：per-step 的**多輪聚合**（N 輪逐步驟統計）暫不做——第一次長 playbook A/B 真跑 N=1 即可逐步驟定位，N 輪逐步驟統計是更重的維度，列為 improving_77 候選；本輪只交付單輪 per-step + 有界對比報告 + DEF-76-001 載具側修復。

---

## 4. 階段三：實作與雙重驗證

> （階段三/四回填：實作後填寫實作摘要、受控突變結果、測試守界意圖。）

### 4.1 實作（純 AutoClaude A 軌載具層、零 autoclaude/ 生產碼、無 Copy-on-Evolve）

- [tools/ab_compare_backends.py](../../AutoClaude/tools/ab_compare_backends.py)：
  - 模組常數加 `_RE_STEP_TAG`（自 TOKEN_COMPACT/✓ 行抽 `[Sxx]`）+ `_RE_CORRECTION_STEP`（CORRECTION 行抽 `step=Sxx`）。
  - 新 `StepMetrics` dataclass（純資料：step_id / compact_count / peak_token_pct / correction_count）；`RunMetrics` additive 加 `per_step: dict[str, StepMetrics]`（向後相容，既有測試不檢查新欄 → 不受影響）。
  - `parse_run_metrics`：(1) CORRECTION 旁路歸因（`_RE_CORRECTION_STEP.findall` → per_step[sid].correction_count++，整輪 correction_count 仍以 `_RE_CORRECTION` 計、語意不變；誠實邊界＝per-step 為下界，見上）；(2) token 掃描迴圈納入 **TOKEN_COMPACT + TOKEN_HALT 兩 marker**（`is_compact`/`is_halt`）：peak=max(line_peak) 兩者皆餵、compact_count 僅 TOKEN_COMPACT 計（halt≠churn）、per_step[sid] peak/compact 對應歸因。整輪總和欄位語意對既有 TOKEN_COMPACT-only log 零變更（TOKEN_HALT 為 additive 新認）。新增 `_step_of` helper。
  - 新 `format_step_comparison(pty, sdk, max_steps=30)`：per-step × backend 表（每格 compact/peak/corr），步驟順序＝兩後端 step_id 聯集穩定（lexical）排序、缺一邊以 `0 / 0% / 0` 補位；**有界截斷**——超 max_steps 只印前 max_steps 步 + `… (N more steps elided)` 一行（`max(0, max_steps)` 守負索引）。
  - `main()` 解析模式附印 per-step 表；argparser 加 `--max-steps`（預設 30）。
- [tests/tools/test_ab_compare_backends.py](../../AutoClaude/tests/tools/test_ab_compare_backends.py)：新增合成「長 playbook」log（`_PER_STEP_LOG` / `_long_log(n)` / `_HALT_MARKER_LOG` / `_MIXED_CORRECTION_LOG`）+ **12** 回歸測試（per-step compact/peak 歸因 / per-step correction 歸因 / 不變式逐步驟和==整輪 / 無標記→空 dict / 兩後端兩欄+步驟列 / 缺步驟零補位 / 有界截斷真截斷 / 未超限不誤截 / **max_steps=0 全省略〔SA-SD P2〕** / **雙空純表頭〔SA-SD P3〕** / **TOKEN_HALT 餵 peak〔DEF-76-001〕** / **per-step correction 下界〔SA-SD P1〕**）。
- **autoclaude/ 生產碼零改動**（`git status --short` 只含 `tools/ab_compare_backends.py` + 測試兩 tracked 檔，無 `autoclaude/` 任一檔）；載具非 autoclaude package 成員 → `.importlinter` 8 kept 不受影響。

### 4.2 受控突變實證（測試非空殼，R-76-5）

| 突變 | 改動 | 對應測試 | 結果 |
|------|------|---------|------|
| MUT-76-1 | `parse_run_metrics` per-step `sm.compact_count += 1` → `+= 0` | `test_per_step_compact_and_peak_attribution` + `test_per_step_sum_equals_whole_invariant` | **轉紅**（`AssertionError: 0 == 3`） |
| MUT-76-2 | `parse_run_metrics` per-step `sm.correction_count += 1` → `+= 0` | `test_per_step_correction_attribution` + `test_per_step_sum_equals_whole_invariant` | **轉紅**（`AssertionError: 0 == 3`） |
| MUT-76-3 | `format_step_comparison` `shown = step_ids[:max_steps]` → `shown = step_ids`（移除截斷） | `test_format_step_comparison_bounded_truncation` | **轉紅**（無 elided 行、S06/S08 全列出） |
| MUT-76-4 | `parse_run_metrics` `is_halt = "TOKEN_HALT" in line` → `= False`（移除 TOKEN_HALT 辨識＝DEF-76-001 病灶） | `test_token_halt_marker_feeds_peak_and_per_step` | **轉紅**（`0.0 == 92.0`，production peak 歸 0） |

- 四處突變均以 **Edit 還原**（禁 `git checkout`，本輪含 tracked 未 commit 改動〔ab_compare_backends.py / test〕+ untracked 新檔〔計畫/審計文件〕，遵 [[git-checkout-mutation-revert-hazard]]）。
- 還原後 `grep MUT-76` 無殘留、載具 **38 passed** 復綠（原 26 + 12 新）。

### 4.3 測試守界意圖（Rule 9）

- **W-76-1（per-step compact/peak）**：`per_step["S02"].compact_count==2 / peak==88.0` vs `["S01"]==1 / 82.0` 固化「長 playbook 下哪步驟壓最多次/水位最高」——整輪總和（壓 3 次 peak 88%）看不出此分布。MUT-76-1 證實歸因歸零即紅。
- **W-76-2（per-step correction）**：`["S02"].correction_count==2 / ["S01"]==1` 固化「哪步驟最常被 CORRECTION」。MUT-76-2 證實歸因歸零即紅。
- **不變式（R-76-3）**：`sum(per_step compact)==整輪 compact==3` 且 correction 同——固化「per_step 為整輪精確拆分、語意不漂移」（生產格式每筆標記皆帶步驟 id）。MUT-76-1/2 任一令不變式轉紅。
- **有界渲染（W-76-3）**：8 步 max_steps=5 → 含「(3 more steps elided)」、含 S05、不含 S06/S08、行數==8（有界）。MUT-76-3 證實移除截斷即紅。`test_format_step_comparison_no_truncation_when_within_limit`（未超限不誤截）+ `max_steps=0 全省略`（SA-SD P2，守 `max(0,..)`）+ `雙空純表頭`（SA-SD P3，渲染端對稱）對稱守界。
- **TOKEN_HALT / DEF-76-001（W-76-2）**：`peak==92.0 / per_step["S03"].peak==92.0 / compact_count==0 / halted is True`（`_HALT_MARKER_LOG`）固化「載具須認 production 的 TOKEN_HALT marker，否則真跑 peak 恆 0」。MUT-76-4 證實移除辨識即紅。
- **per-step correction 下界（SA-SD P1）**：`_MIXED_CORRECTION_LOG`（Kernel 帶 step= + 棄用 _impl.py 不帶）→ `correction_count==2`（整輪）但 `sum(per_step)==1`（下界）固化「不帶 step= 的 CORRECTION 不歸因、等號僅 Kernel 路徑成立」，誠實守 overclaim 邊界。

## 5. 階段四：零退化驗證矩陣（全項實測，結案）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3390 / 0 failed | **3402 / 122 / 0**（floor 3390 + 12 新測，67.82s） ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept | **8 kept / 0 broken** ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0**（total=19385 baseline=17032 cap=20438；載具 +~48 行遠低於絕對紅線 750、tests/ 不受 tier） ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK（FRESH）** ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 | **N/A — 本輪零碰 AISDLC_SDD/**（`git status --short` 僅 2 tracked AutoClaude 檔 + improving_76.md，無 `AISDLC_SDD/` 任一檔 鐵證）；階段一已實測 exit 0（v0.01:1478 / v0.26:1665 / scripts:129），本輪無觸發路徑 |
| 五軌 TLC | — | 僅 FSM 變更時 | **N/A — 條件未觸發**（git status 鐵證零碰 `*.tla`/FSM；TLC 不在 pytest 全套、需 Java+tla2tools，本輪確實未跑） |
| DAL 等價 | `tests/equivalence/`（隨全套） | 三後端等價 | **既有等價測試隨全套 3402 通過** ✅；本輪無新 DAL/checkpoint 改動 → 無新增針對性 round-trip 契約 |

---

## 6. RTM（需求追溯矩陣）

| 需求 | 來源 | 驗證 |
|------|------|------|
| R-76-1 A/B 載具逐步驟歸因 compact_count / peak_token_pct（分出長 playbook 哪步驟驅動 token 成本） | `parse_run_metrics` per_step（TOKEN_COMPACT `[Sxx]` 抽取） | `test_per_step_compact_and_peak_attribution` + `test_per_step_empty_when_no_markers` **PASS** |
| R-76-2 A/B 載具逐步驟歸因 correction_count（分出哪步驟最常被 CORRECTION） | `parse_run_metrics` per_step（CORRECTION `step=Sxx` 抽取） | `test_per_step_correction_attribution` **PASS** |
| R-76-3 per_step 為整輪總和精確拆分（不變式：逐步驟和 == 整輪值） | `parse_run_metrics` | `test_per_step_sum_equals_whole_invariant` **PASS** |
| R-76-4 有界渲染：長 playbook 逐步驟報告超 max_steps 截斷 + 揭露省略數（防 OOM/Token 爆炸） | `format_step_comparison` bounded truncation | `test_format_step_comparison_bounded_truncation` + `test_format_step_comparison_no_truncation_when_within_limit` + `test_format_step_comparison_missing_step_zero_filled` + `test_format_step_comparison_shows_both_backends_and_steps` **PASS** |
| R-76-5 測試非空殼（受控突變實證） | 暫改載具對應分支 | MUT-76-1/2/3/4 各令對應測試**轉紅**，Edit 還原後 38 passed 復綠（§4.2） |
| R-76-6 零退化 | 收斂矩陣 | **3402/0**、8 kept、LOC 0、snapshot FRESH、零碰 SDD/autoclaude 生產碼（§5） |
| R-76-7（DEF-76-001 載具側）載具納入 production token marker（TOKEN_HALT），修 peak/compact production-blind | `parse_run_metrics` `is_halt` 分支 | `test_token_halt_marker_feeds_peak_and_per_step` **PASS**；MUT-76-4 轉紅實證 |
| R-76-8（SA-SD P1）per-step correction 下界誠實邊界（不帶 step= 的 CORRECTION 不歸因） | `parse_run_metrics` per-step correction | `test_per_step_correction_is_lower_bound_for_untagged` **PASS**（whole 2 / per-step 1） |

---

## 7. 多專家 Zero-Trust 審查結論

> 證據見 [AutoSDD_ZeroTrust_Audit_76.md](../06_quality/AutoSDD_ZeroTrust_Audit_76.md)。（回填三鏡 Architect / SA-SD / QA 結論）

---

## 8. 誠實級別標註

本輪＝**A 軌 A/B 載具「逐步驟指標歸因 + 有界渲染」量測使能輪 + DEF-76-001 載具側修復（零 autoclaude/ 生產碼），非成熟度推進**，`L_合體=min(A=L5,B=L5,C=L5)=L5` 維持。

- **首要成果**：①A/B 載具新增 per-step 歸因（compact_count / peak_token_pct / correction_count 逐步驟拆分），使候選 (a) 真跑時方能**逐步驟定位**長 playbook 下 pty/sdk 成本差（整輪總和分不出哪步驟）；②有界渲染對比報告（bounded truncation）杜絕長 playbook 報告無限長/Token 爆炸；③**audit 期揭露並修復 DEF-76-001**（載具側）：載具納入 production 的 `TOKEN_HALT` marker 解析，修「peak/compact 只認棄用路徑 TOKEN_COMPACT → production 真跑恆 0」的跨輪觀測缺口；④新測皆以受控突變（MUT-76-1~4）實證非空殼。
- **🔴 誠實邊界**：
  - 候選 (a) 的**真跑**部分（真 token、長 playbook 實測 pty/sdk 逐步驟差異）本環境無法離網完成，**維持延後**至真 token session；本輪只交付離網可測的載具使能。**不虛報「已逐步驟分出 token 差異」**。
  - **per-step correction 為下界**（不帶 step= 的已棄用 `_impl.py:437` CORRECTION 不歸因；等號僅 production Kernel 路徑成立）——原「三種標記皆帶 step id」overclaim 已訂正（SA-SD P1）。
  - **DEF-76-001 僅載具側閉環**：production 端 Kernel observability marker 補強需動 autoclaude 生產碼（仿 W-71-2），**routed improving_77**；本輪載具側「哪路徑印就抓哪個」是部分緩解，不宣稱已完全打通 production token 量測。
- **遞延 improving_77 候選**：(a-真跑) 真 token session 跑更長 playbook 取得逐步驟實測差異（載具本輪已備好 per-step + TOKEN_HALT）；**DEF-76-001 production 端 Kernel token marker 補強（需生產碼）**；per-step 多輪聚合（N 輪逐步驟統計，本輪誠實切分未做）；(b) SD_09 W1 觀察期 #1 source-sha 閘門（時間閘 ~06-29~07-01 成熟後）；(c) W-67-2 producer 端 SDD 模板 spec-format-version（需 Copy-on-Evolve v0.27）。

三件套：improving_76 / ZeroTrust_Audit_76 / Defect_Log（improving_76 recap）。
