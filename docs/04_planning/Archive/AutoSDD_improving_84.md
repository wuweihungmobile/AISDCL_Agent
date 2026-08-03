# AutoSDD_improving_84 — C 軌：token-guard compact/halt 編排「端到端真跑」首證 + 可重跑驗證載具

> **軌道**：① 整合迭代 / **C 柱（指揮官 AutoClaude 自身能力 — 觀測與驗證載具）**
> **下一份**：`AutoSDD_improving_85.md`
> **驅動器**：`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md`
> **狀態**：階段二設計落地（§1-§3 先寫）→ 階段三/四回填（§4 真跑/突變、§5 驗證矩陣實測欄）
> **規格先行聲明**：本檔於動任何 code 前先落地（§1 輸入 / §2 階段一實測 / §3 增量設計含 `<Architecture_Design_Review>`、介面 delta、RTM）。§4.2 真跑結果、§5「本輪實測」欄為階段三/四回填，非事後補寫。

---

## §1 本輪輸入（自上輪繼承）

### 1.1 上輪（improving_83）已完成 W 項
- **W-83-1**：修載具 `ab_compare_backends.py` DEF-83-001（`effective_peak_token_pct = max(observer, marker)` SSOT property，單/多輪 display 改用）。
- **DEF-81-001**（SDK 支）：真跑驗證閉合（零生產碼），PTY+SDK 雙支全閉合。
- **DEF-83-002**：訂正 improving_82 §8.2「SDK 真跑仍 0」未驗證宣稱。

### 1.2 上輪交棒（improving_83 結論明示的 84 候選）
> 「設計一個夠長、會真撞 80/90% 門檻的 playbook 真跑，端到端實證 compact/halt 在真實負載下真的觸發——訊號源（81-83）和編排接線（78/79）現在都通了，就差『夠長到撞門檻』這一哩的真跑驗證。」

### 1.3 缺陷帳本（`AutoSDD_Defect_Log.md`）open/routed 複驗（階段一）
- **DEF-01-007**（cc-switch GUI，P3）：open，本輪不涉多後端 A/B profile 切換，未觸發。
- **DEF-01-009**（`sdd_governance_plugin.py` LOC watch，P3）：open watch，本輪零碰該檔（純 tools/ + scripts/ + tests/），不觸發。
- **DEF-19-001**（catch 漸進覆蓋，P3）/ **DEF-17-001**（fire 側遙測，routed）/ **DEF-23-005**（RFC 生命週期自動化，P3）/ **DEF-35-001**（goal_synthesis mutmut 目錄，P2，C 軌 SD_09）/ **DEF-62-001**（auto_recovery 註解滯後，P3）：皆非本輪 scope，未推進，維持原狀態。

### 1.4 掌舵者本輪拍板（AskUserQuestion 紀錄）
1. **本輪 scope**：鎖定上輪交棒候選——「端到端真跑實證 compact/halt 在真實負載下觸發」。
2. **真跑策略**：**調低門檻的真跑**（成本/忠實度權衡）——在測試 config 把 compact/halt 門檻調至低於真跑觀測到的 token% 峰值（上輪 PTY 6.2 / SDK 2.0），讓「觀測% ≥ 設定門檻 → 觸發編排」這條核心邏輯在**真跑**（非 mock）中端到端走完。

---

## §2 階段一：現況重偵察（Zero-Trust Re-Audit，實測）

### 2.1 基線實測（硬閘：無 failed、≥ 上輪 floor 3474）
| 檢查 | 命令 | 本輪實測 | 結果 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3474 passed / 0 failed / 122 skipped**（74.88s） | ✅ = floor |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（199 files / 502 deps） | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | **violations=0**（total=19767 / cap=20438） | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | **OK**（無 stale） | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **PASS**（exit 0；v0.01 1478 + v0.26 1665 + scripts 129；arch_fitness fail=0） | ✅ |

> 硬閘通過：基線等於上輪 floor 3474、零 failed，准進階段二。

### 2.2 上輪構件存在性核對（zero-trust，親查 file:line）
- `tools/ab_compare_backends.py:121` `effective_peak_token_pct` property 存在（W-83-1 真實構件，546 行）。
- `tools/ab_compare_backends.py:248/391` 單輪/多輪 display 已改用 `effective_peak_token_pct`。

### 2.3 真實路徑勘查（本輪要驗證的 production 編排）
- **觸發點**：`core/kernel.py:283` `_consult_token_guard(peak_pct)` — 以 executor 觀測到的真實 token% emit `ON_TOKEN_USAGE` → TokenGuardPlugin 決策。
  - `peak_pct <= 0` 直接 return None（無訊號零退化）。
  - `tu.request_halt` → 印 `=== STATE: TOKEN_HALT | [步驟] context NN% >= halt 門檻 ===`（kernel.py:303）+ 回 `StepOutcome(HALT)`。
  - `tu.request_compact` → `_handle_compact`（kernel.py:314）→ `perform_compact` 送 /compact 印 `TOKEN_COMPACT` marker。
- **門檻判定**：`plugins/token_guard/policy.py:164-191` — **halt 先判、優先於 compact**（peak ≥ halt → halt；compact ≤ peak < halt → compact）。
- **門檻來源**：config 頂層 `token_guard:` 的 `compact_threshold_pct` / `halt_threshold_pct`（`utils/config.py:96-158`，Pydantic 防呆 halt > compact）；亦支援 `PlaybookTask.token_guard` per-step override（`models/playbook.py:46`）。
- **Gap-008-E**：`plugins/token_guard/compactor.py:26` `critical_threshold=2` — 連續 2 次 compact 失敗（POST_COMPACT 後 token% 仍 ≥ compact 門檻）→ 強制 HALT。

### 2.4 真跑入口（既有，零新增）
- `tools/ab_compare_backends.py:455` `run_backend()`：`subprocess [python -m autoclaude <playbook> --fresh --config <cfg>]`，讀 `<workdir>/logs/autoclaude.log` 解析 marker。
- smoke 基底：`scripts/sdd_bridge_smoke.yaml`（2 步 TDD add 函式，自包含、會真呼叫 claude）。
- 既有 config：`scripts/ab_configs/ab_{pty,sdk}_config.yaml`（無 token_guard override → 沿用預設 80/90 → **故真跑 marker 從未出現**＝本輪要補的缺口）。

### 2.5 缺口認定（本輪存在理由）
78/79 已把 compact/halt 編排接進 production Kernel、81-83 已修通訊號源（真跑 peak 6.2/2.0%），但**從來沒有一次真跑讓 `TOKEN_COMPACT` / `TOKEN_HALT` marker 真的出現**——因真跑觀測峰值（~6%）遠低於預設門檻（80/90%）。**compact/halt 編排在真跑中端到端觸發＝至今只有單元測試（mock 事件/門檻）證明，無真跑鐵證。** 本輪補上這最後一哩，並留下可重跑的回歸守衛。

---

## §3 階段二：本輪增量設計

### 3.1 本輪 W 項（≤3）
| W 項 | 內容 | 類型 | 觸碰面 |
|------|------|------|--------|
| **W-84-1** | 兩份調低門檻 config（compact-demo / halt-demo），衍生自 `ab_pty_config.yaml` | 測試構件（YAML） | `scripts/ab_configs/`（零生產碼） |
| **W-84-2** | `tools/verify_token_guard_e2e.py` 端到端驗證載具 + 單元測試 | 工具 + 測試 | `tools/` + `tests/tools/`（零生產碼） |
| **W-84-3** | 執行調低門檻真跑、記錄 marker 鐵證（compact 觸發 / halt 觸發），fail-loud | 階段三真跑 | 真跑取證（§4.2） |
| **W-84-4**（階段三真跑後新增） | 修 DEF-84-001：compact 動態門檻 decay floor=65 默默夾掉 config 低門檻 → surgical 修 `thresholds.py` + 單測 | **production 修復** | `autoclaude/plugins/token_guard/thresholds.py`（1 表達式）+ `tests/plugins/` |

> **設計初衷 vs 真跑修正（誠實紀律）**：階段二設計時 W-84-1/2/3 規劃為**零碰生產碼**（compact/halt 編排已於 78/79 接線、單測鎖定，只加測試 config + 驗證載具 + 真跑鐵證）。但**階段三 W-84-3 真跑 dogfooding 揭露 DEF-84-001**——compact 調低門檻真跑（compact=1%）竟不觸發，根因為 `get_dynamic_compact_threshold` 的 decay floor 硬寫 65.0 把 config 低門檻默默夾到 65（halt 路徑無此 floor 故 halt 真跑成功）。這是真跑才現形的真實 production 缺陷，依 dogfooding 紀律 surgical 修復（W-84-4），並以重跑真跑證明修復端到端解除 compact 觸發。**故本輪實際動了 1 處生產碼**（非零碰）——此即「真跑驅動修復」的價值，§3.4 ADR 隨之訂正。

### 3.2 W-84-1 介面 delta — 調低門檻 config
兩份 config 皆繼承 `ab_pty_config.yaml` 既有設定（backend=pty / dummy minimax key / yaml_only / goal_synthesis_enabled=false），additive 加 `token_guard:` section：

- **`scripts/ab_configs/lowthr_compact_config.yaml`**（compact 觸發 demo）
  ```yaml
  token_guard:
    enabled: true
    compact_threshold_pct: 1.0     # 遠低於真跑峰值(~2~6%) → 必觸 compact
    halt_threshold_pct: 99.0       # 高於真跑峰值 → 門檻層不觸 halt（隔離出 compact 路徑）
  ```
  預期：peak ≥ 1% → `TOKEN_COMPACT` marker 出現（compact 編排觸發）。註：若 POST_COMPACT 後 token% 仍 ≥1%，Gap-008-E 連續 2 次 → 後續轉 HALT（真跑據實記錄）；無論如何 **`TOKEN_COMPACT` marker 出現即證 compact 編排已觸發**。

- **`scripts/ab_configs/lowthr_halt_config.yaml`**（halt 觸發 demo）
  ```yaml
  token_guard:
    enabled: true
    compact_threshold_pct: 0.3     # 兩者皆低於真跑峰值
    halt_threshold_pct: 1.0        # peak ≥ 1% → halt 先判優先 → 立即 HALT（早於 compact）
  ```
  預期：peak ≥ 1% ≥ halt 門檻 → halt 先判 → `TOKEN_HALT` marker + `KernelResult(halted=True)`（compact 路徑被 skip）。

> **門檻數值選擇依據**：上輪真跑觀測 PTY 6.2 / SDK 2.0%，故門檻取 ≤1% 確保**兩 backend 皆會撞**。這是「調低門檻真跑」策略的具體落點——驗證的是 `observed_pct ≥ configured_threshold → 觸發` 這條與門檻數值無關的核心比對邏輯（§8 誠實標記其忠實度邊界）。

### 3.3 W-84-2 介面 delta — 端到端驗證載具
`tools/verify_token_guard_e2e.py`（純驗證工具，重用 `ab_compare_backends.parse_run_metrics`，**不重複造解析輪子**）：

純函式（offline，零 token，供單測 + 既有 log 重驗）：
- `assert_compact_fired(m: RunMetrics) -> tuple[bool, str]`：判 `m.compact_count >= 1`（`TOKEN_COMPACT` 出現過）→ (True, 理由) / (False, fail-loud 理由)。
- `assert_halt_fired(m: RunMetrics) -> tuple[bool, str]`：判 `m.halted is True`（`KernelResult.halted=True`，即 `TOKEN_HALT` 路徑落地）→ (True/False, 理由)。

真跑模式（需授權 token，階段三用）：
- `--run-compact <playbook> --config <cfg> --workdir <dir>`：跑一次 → 讀 log → `assert_compact_fired`，未觸發 fail-loud（exit 非 0）。
- `--run-halt <playbook> --config <cfg> --workdir <dir>`：跑一次 → 讀 log → `assert_halt_fired`，未觸發 fail-loud。
- `--parse-log <logfile> --expect {compact,halt}`：對既有 log 離線斷言（零 token，回歸重驗用）。

fail-loud：log 不存在 / marker 缺席 → 明確 exit 非 0（沿 `_load_log_or_raise` 紀律，不靜默回 0）。

### 3.4 `<Architecture_Design_Review>`
```
<Architecture_Design_Review>
1. 架構純潔性：階段二設計為零碰生產碼；階段三真跑揭露 DEF-84-001 後，**surgical 修 1 處
   生產碼**——`plugins/token_guard/thresholds.py` 的 `get_dynamic_compact_threshold` 改
   `effective_floor = min(floor, base_threshold)`（純函式內 1 表達式，無新狀態、無新依賴、
   無 God-object）。kernel/ports/其餘 plugins 不動。新增 tools/ 驗證載具 + scripts/ 測試
   config + tests/。verify_token_guard_e2e.py 重用 ab_compare 既有 parse_run_metrics（不造
   God-object、不複製解析邏輯）。Thin Facade（playbook_runner）不受影響。
2. 持久化相容：零碰 PlaybookCheckpoint / DAL；無新狀態欄位。halt 真跑會寫 checkpoint（既有
   行為，improving_78 已接線），本輪只「觀測」其發生，不改持久化結構。三後端零停機維持。
3. 安全防護網：本輪不新增任何「從文件生成指令」路徑；config 僅調 token_guard 門檻數值（Pydantic
   驗證 halt>compact 仍生效）。CONDITIONAL 白名單不受影響（無新 command 來源）。
4. 對外 I/O 安全：本輪零新增 ToolInvocationPort 外呼路徑（無 Web/HTTP/訊息）。真跑經既有
   PtyExecutor 呼叫本機 claude CLI，非新對外網路 I/O。allowlist 路徑不受影響。
5. LOC：verify_token_guard_e2e.py 屬 tools/（不在 autoclaude/ LOC 計數域，與 ab_compare 同），
   仍自我約束 < 絕對紅線 750。thresholds.py 修改為 strategy tier，實測 total 19767→19768
   （+1），violations=0、未破任何 tier。
6. importlinter：tools/ 不在 autoclaude 套件 contract 圖內；驗證載具 import 另一 tools 模組
   （ab_compare），不觸 8 條 contract 任一。thresholds.py 修改不改 import 結構。
7. 零退化：thresholds.py 修改對 base ≥ floor（production 預設 80）為 no-op（min(65,80)=65，
   回傳值與修前完全一致）——既有 base=80 測試（test_token_guard_plugin.py:58-66）全綠不變；
   只影響 base < 65 的低門檻 config（修前默默夾值＝缺陷）。新增測試只增不減。
</Architecture_Design_Review>
```

### 3.5 RTM 需求列（階段四回填實測欄）
| RTM ID | 需求 | 驗證方式 | 狀態 |
|--------|------|---------|------|
| RTM-84-1 | compact-demo config 在真跑使 `TOKEN_COMPACT` marker 出現 | 真跑（修 DEF-84-001 後）+ `assert_compact_fired` | ✅ TOKEN_COMPACT ×2、peak 6.4%、completed 2/2 |
| RTM-84-2 | halt-demo config 在真跑使 `TOKEN_HALT` + `KernelResult(halted=True)` | 真跑 + `assert_halt_fired` | ✅ TOKEN_HALT ×11、halted=True、completed 0/2 |
| RTM-84-3 | `assert_compact_fired`/`assert_halt_fired` 對「無觸發 log」回 False（Rule 9：測試能失敗） | 單測 fixture log（無 marker） + MUT-84-2/3 | ✅ 6 斷言測試 + MUT-84-2/3 轉紅 |
| RTM-84-4 | 驗證載具 fail-loud：log 不存在 → RuntimeError；marker 缺席 → exit 非 0 | 單測 | ✅ `test_load_log_missing_raises` + exit1 測試 |
| RTM-84-5 | 零退化：全套 pytest ≥ 3474 / 0 failed；lint 8 kept；LOC 0；snapshot OK；ci-gate PASS | 階段四矩陣 | ✅ 3488/0/122、8 kept、0、OK、PASS |
| RTM-84-6 | DEF-84-001 修：compact_threshold_pct < 65 honor config、不被 decay floor 默夾；base≥65 no-op | `test_dynamic_threshold_low_base_honored...` + MUT-84-1 | ✅ 通過 + MUT-84-1 轉紅 |

---

## §4 階段三：實作與雙重驗證

### 4.1 實作逐項紀錄（每項完成即跑單測）
- **W-84-1**：`scripts/ab_configs/lowthr_{compact,halt}_config.yaml` 建立 → `load_config` 驗證兩份通過 schema（compact=1.0/halt=99.0、compact=0.3/halt=1.0，halt>compact 不變式成立）。
- **W-84-2**：`tools/verify_token_guard_e2e.py`（assert_compact_fired / assert_halt_fired 純函式 + 真跑/離線/fail-loud 三模式）+ `tests/tools/test_verify_token_guard_e2e.py` **13 passed**。CLI script 直跑驗證（stderr 亦 reconfigure utf-8，cp950 不炸）。
- **W-84-4**（DEF-84-001 修）：`thresholds.py` `effective_floor = min(floor, base_threshold)` + `test_dynamic_threshold_low_base_honored_not_clamped_to_floor`，`test_token_guard_plugin.py` **40 passed**。

### 4.2 真跑鐵證（compact / halt 端到端，本 session 親跑）
真跑：`python tools/verify_token_guard_e2e.py --run-{compact,halt} scripts/sdd_bridge_smoke.yaml --config scripts/ab_configs/lowthr_{compact,halt}_config.yaml --workdir <tmp>`（claude 2.1.144，backend=pty）。

| 情境 | config 門檻 | 真跑結果 | marker 鐵證 | KernelResult |
|------|-----------|---------|------------|--------------|
| **halt** | compact 0.3 / halt 1.0 | **PASS**（exit 0） | `=== STATE: TOKEN_HALT \| [S01] context 6% >= halt 門檻 ===` ×11 | peak 12.0%、**halted=True**、completed 0/2 |
| **compact（修 DEF-84-001 前）** | compact 1.0 / halt 99.0 | **FAIL**（exit 1） | TOKEN_COMPACT ×0 | peak 6.2%、halted=False、completed 2/2 → **揭露 DEF-84-001** |
| **compact（修 DEF-84-001 後）** | compact 1.0 / halt 99.0 | **PASS**（exit 0） | `=== STATE: TOKEN_COMPACT \| [S01] context 6% >= compact 門檻 ===` + `[S02]` ×2 | peak 6.4%、halted=False、**completed 2/2 success** |

> **首證意義**：improving_78/79 接線、81-83 修通訊號源後，**這是 compact 與 halt 編排首次在真跑中端到端觸發留下 marker**（過去真跑峰值 ~6% 遠低於預設 80/90 故 marker 從未出現）。halt 路徑一次到位；compact 路徑真跑揭露 DEF-84-001、修後到位。
>
> **數字澄清（audit_84 SA-SD 觀察）**：halt 列「peak 12.0%」是 `TokenObserver` 該次 run **全程觀測到的最高水位**（KernelResult.peak_token_pct），marker 行文字 `context 6%` 是 token-guard 印 marker **當下那一瞬間**的 token%（`%.0f%%` 取整）；兩者為不同時間點的量測、可並存不矛盾（峰值 ≥ 任一瞬時值）。compact 修後 peak 6.4% 同理為該次 run 峰值。

---

## §5 階段四：零退化驗證矩陣（實測）

| 檢查 | 命令 | 通過條件（floor=上輪實測） | 本輪實測 | 結果 |
|------|------|------------------------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3474 passed / 0 failed | **3488 passed / 0 failed / 122 skipped**（+14：13 verify + 1 threshold） | ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | **8 kept / 0 broken** | ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0**（total=19768 / cap=20438；thresholds.py +1） | ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK** | ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | **PASS**（v0.01 1478 + v0.26 1665 + scripts 129；git status 證零碰框架本體） | ✅ |
| DAL 等價 | equivalence job | 三後端等價 | **既有 `tests/equivalence/` 隨全套 pytest 通過；本輪零 DAL/repositories/checkpoint 改動**（git diff 證實只動 thresholds.py + tools/ + scripts/ + tests/） | ✅（N/A 類型②：既有隨全套通過） |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | 五軌 0 violation | **N/A 類型①：本輪零碰 `*.tla`/FSM/`_HAPPY_PATH`**（git status 證零 AISDLC_SDD 改動；TLC 不在 pytest 全套、需 Java，未跑） | N/A① |

**受控突變（Rule 9 證測試非空殼）**：
- **MUT-84-1**：thresholds.py `min(floor, base)` → `floor` → `test_dynamic_threshold_low_base_honored...` 轉紅（`65.0 == 1.0` 失敗）。
- **MUT-84-2**：載具 `assert_compact_fired` `>= 1` → `>= 0`（恆真）→ `test_no_trigger_log_fails_compact_assert` + CLI exit1 測試轉紅。
- **MUT-84-3**：載具 `assert_halt_fired` `is True` → `is not None`（恆真）→ `test_no_trigger_log_fails_halt_assert` + CLI exit1 測試轉紅。
- 三突變皆以 Edit 還原（非 git checkout，避免抹除 untracked 新檔），還原後 53 passed、thresholds.py 無殘留。

---

## §6 缺陷處置

- **DEF-84-001**（P3，新增，本輪 dogfooding 真跑揭露）：`get_dynamic_compact_threshold`（`plugins/token_guard/thresholds.py`）的 decay `floor=65.0` 用預設值未從 config 傳入，導致 `compact_threshold_pct` 設定**低於 65 時被硬下限默默夾到 65**（如 config 設 1% → 真跑撞不到，compact 編排不觸發）；halt 路徑（`should_halt_decision` 直接 `token_pct >= halt_threshold`）無此 floor 故正常。config 契約被硬寫值默默違反。**fixed@improving_84（W-84-4）**：`effective_floor = min(floor, base_threshold)`——decay floor 不得高於 base，honor config 低門檻；base ≥ floor（production 預設 80）為 no-op、零退化。證據：MUT-84-1 轉紅 + 修後 compact 真跑 TOKEN_COMPACT ×2 端到端觸發。
- **上輪 open/routed 複驗**：DEF-01-007 / DEF-01-009 / DEF-19-001 / DEF-17-001 / DEF-23-005 / DEF-35-001 / DEF-62-001 皆非本輪 scope，未觸發/未推進，維持原狀態（見 §1.3）。

## §7 結案契約

```yaml
closure-evidence:
  round: improving_84
  track: C  # 指揮官 AutoClaude 自身能力（token-guard 編排端到端真跑首證 + DEF-84-001 修）
  pytest: "3488 passed / 0 failed / 122 skipped"   # floor 3474 + 14 新測
  lint_imports: "8 kept / 0 broken"
  loc_violations: 0   # total 19768
  snapshot: fresh
  aisdlc_sdd_cigate: PASS  # 零碰框架本體
  real_run_halt: {marker: "TOKEN_HALT ×11", halted: true, peak_pct: 12.0, completed: "0/2"}
  real_run_compact_before_fix: {marker: "TOKEN_COMPACT ×0", halted: false, peak_pct: 6.2}  # 揭露 DEF-84-001
  real_run_compact_after_fix: {marker: "TOKEN_COMPACT ×2", halted: false, peak_pct: 6.4, completed: "2/2"}
  mutations: "MUT-84-1/2/3 全轉紅 + Edit 還原無殘留"
  new_tests: 14  # 13 verify + 1 threshold
  production_files_touched: 1   # autoclaude/plugins/token_guard/thresholds.py（DEF-84-001 修，1 表達式）
  tooling_files_touched: 1      # tools/verify_token_guard_e2e.py（新驗證載具）
  config_files_added: 2         # scripts/ab_configs/lowthr_{compact,halt}_config.yaml
  aisdlc_sdd_touched: 0
  framework_version: v0.26  # 不變
  maturity: L5  # L_合體不變
  defects:
    - DEF-84-001: "fixed@improving_84（compact decay floor=65 默夾 config 低門檻；真跑揭露 + surgical 修 + 真跑復證）"
```

## §8 誠實限制
1. **「調低門檻」忠實度邊界**：本輪驗證的是 `observed_pct ≥ configured_threshold → 觸發 compact/halt 編排` 這條**與門檻數值無關**的核心比對邏輯，在**真跑**中端到端走完。它**不等於**「真實 80 萬 token 高負載撞 80/90%」——後者極貴極慢（掌舵者明示採此成本/忠實度權衡）。誠實標記：production 80/90% 的**數值**邊界本身未在真跑驗（但門檻比對是同一段 `peak >= threshold`，數值無關，故編排觸發路徑已端到端證實）。
2. **DEF-84-001 修的副作用面誠實界定**：`min(floor, base)` 只改變 `base < 65` 的低門檻 config（修前為缺陷態）；production 預設 base=80 完全 no-op（min(65,80)=65，回傳值逐位相同），故零退化。修後 `base ≤ floor` 時動態門檻 = base 常數（無 decay range），此為 honor config 的正確取捨（無法在 base 之下再 decay）。
3. **compact 真跑「未轉 Gap-008-E halt」屬幸運非保證**：修後 compact 真跑兩步各 compact 一次即成功（completed 2/2），未累積 2 次連續 compact 失敗觸發 Gap-008-E。此依真實 /compact 後 token% 行為而定，非本輪可控；本輪斷言 `assert_compact_fired` 只問「TOKEN_COMPACT 是否出現」（compact 編排是否走到），不要求「不轉 halt」，故結論穩健。
4. **規格先行遵循 + 真跑驅動修正**：§1-§3 於階段二先落地（含 W-84-1/2/3 設計 + RTM）、才動碼；§4/§5 為階段三/四回填。階段二原設計為零生產碼，階段三真跑 dogfooding 揭露 DEF-84-001 → 新增 W-84-4 production 修復，§3.1/§3.4 已同步訂正「實際動 1 處生產碼」，非事後掩飾。
