# SDD CI/CD 基礎層規格
# SDD CI/CD Base Layer Specification

**版本**: v1.1
**建立日期**: 2026-04-12
**最後更新**: 2026-04-18
**文件類型**: 部署規格（Deployment Specification）
**所屬分類**: docs/08_deployment/
**Spec Gate**: 🔷 SCG-2 Architecture Spec Gate
**Phase A 強化**: 加入 Token Budget Check + FSM Retry State 驗證步驟

---

## 🎯 目的

定義 SDD 轉型中 CI/CD Pipeline 的基礎層（L0）擴充規格，加入文件導向的品質驗證步驟。

---

## 🏗️ L0 基礎層 SDD 擴充定義

### 現有 L0 基礎層（繼承自 AISDLC v0.09）

```
Build → Unit Test → Lint → Security Scan → Deploy
```

### SDD 擴充後 L0 基礎層（v1.1）

```
Build → Unit Test → Lint → DocLint → SpecTrace → SLV Check → Token Budget Check → Security Scan → Deploy
                              ↑           ↑            ↑                ↑
                    （SDD 品質閘門）  （邏輯一致性）  （閉環防護）
```

---

## 📋 新增品質驗證步驟

### Step: DocLint（文件格式 Lint）

**目的**：驗證所有文件的格式符合 SDD 規範

**觸發條件**：每次 PR / Merge 時自動執行

**驗證內容**：
```yaml
doc_lint_rules:
  markdown:
    - "所有 .md 文件通過 markdownlint 規則"
    - "標題層級正確（H1 只有一個）"
    - "表格格式規範"
    - "程式碼區塊有指定語言"

  naming_convention:
    - "ADR 文件命名：ADR-{NNN}-{kebab-title}.md"
    - "CONTRACT 文件命名：CONTRACT-{module}-{version}.yaml"
    - "TCS 文件命名：TCS-{feature}-{date}.md"
    - "PBS 文件命名：PBS-{system}-{date}.md"
    - "SAD 文件命名：SAD-{system}-{date}.md"
    - "IaCS 文件命名：IaCS-{env}-{date}.md"

  directory_placement:
    - "ADR 文件必須在 docs/02_architecture/adr/"
    - "API Contract 必須在 docs/02_architecture/api/"
    - "測試契約必須在 docs/03_testing/contracts/"
    - "IaC 規格必須在 docs/08_deployment/iac/"

  link_check:
    - "所有內部 Markdown 連結可解析"
    - "相關文件引用存在"
```

**失敗處理**：DocLint 失敗時，Pipeline 中斷，必須修正後才能繼續。

---

### Step: SpecTrace（規格追溯驗證）

**目的**：驗證需求追溯鏈完整性（RTM 一致性）

**觸發條件**：每次 Stage 交付文件時執行

**驗證內容**：
```yaml
spec_trace_rules:
  traceability_chain:
    - "每個 Feature（F-XXX）必須有父 EPIC（EPIC-XXX）"
    - "每個 User Story（US-XXX）必須有父 Feature（F-XXX）"
    - "每個 AC（AC-XXX-Y）必須有父 US（US-XXX）"
    - "每個 AT（AT-XXX-Y-Z）必須有父 AC（AC-XXX-Y）"

  adr_coverage:
    - "每個架構決策點必須有對應 ADR 文件"
    - "ADR 文件狀態不可為空（Proposed/Accepted/Deprecated）"

  api_contract_coverage:
    - "每個 API 端點必須有對應 CONTRACT 文件"
    - "CONTRACT 文件 x-aisdlc.related_us 必須存在"

  rtm_freshness:
    - "RTM 最後更新日期不得超過 7 天（與需求變更同步）"
```

**分階段阻塞策略（ACT-005）**：
```yaml
spec_trace_blocking:
  sprint_1_to_2:
    fail_on_error: false
    threshold_warning: 70%
    message: "早期 Sprint 允許追溯不完整，須在 Sprint 3 前補齊"

  sprint_3_and_beyond:
    fail_on_error: true
    threshold_error: 80%
    message: "RTM 追溯完整性不足（< 80%），無法繼續合併。請更新 RTM。"
```

**判斷當前 Sprint 編號**：讀取 `build/reports/fsm/FSM-STATE-{project}.yaml` 中的 `current_sprint`。

**失敗處理**：
- Sprint 1~2：輸出缺失追溯項目清單，Pipeline 警告（不中斷）
- Sprint 3+：覆蓋率 < 80% 時 Pipeline 中斷，必須更新 RTM 後才能繼續

---

### Step: SLV Check（Spec 邏輯一致性驗證）🆕

**目的**：在 SCG-0 / SCG-3 閘門通過後，CI/CD 層面驗證邏輯規則未被後續修改破壞

**觸發條件**：
- `docs/01_requirements/FRD-*.md` 有變更時
- `docs/02_architecture/api/CONTRACT-*.yaml` 有變更時

**驗證內容**：
```yaml
slv_ci_rules:
  - "SLV-001: NFR 數值物理可行性（response_time_ms > 0）"
  - "SLV-002: AC 包含可量化判定條件"
  - "SLV-004: API nullable 欄位與 FRD 必填規則相符"
```

**失敗處理**：SLV CI 失敗時，Pipeline 中斷，輸出違規清單。

---

### Step: Token Budget Check（閉環防護監控）🆕

**目的**：在 CI 流程中記錄 SCG retry_count 狀態，偵測異常重試模式

**觸發條件**：每次 SCG Gate 執行後（任意 SCG-N）

**驗證內容**：
```yaml
token_budget_check:
  fsm_retry_state:
    - "讀取當前 SCG retry_count（從 build/reports/verification/ 最新 SCG 報告）"
    - "若 SCG_VALIDATION retry_count ≥ 2（達到上限的 2/3）→ 輸出 WARNING"
    - "若 PR_REVIEW retry_count ≥ 4（達到上限的 4/5）→ 輸出 WARNING"
    - "若任一 retry_count 達到上限 → Pipeline 輸出 ESCALATION 建議"
    
  pattern_report:
    - "輸出 SCG retry 歷史摘要至 build/reports/fsm/SCG-RETRY-{date}.md"
    - "若偵測到相同 SCG failure_reason 連續出現 → 標記 PATTERN_DETECTED"
```

**輸出**：
```
build/reports/fsm/SCG-RETRY-{date}.md
```

**失敗處理**：Token Budget Check 失敗不中斷 Pipeline，輸出 WARNING 至報告。

---

### Step: FSM Spec-Runtime Sync Check（MD ↔ Python 雙源一致性）🆕 Phase E / ACT-022

**目的**：防止 `SDD_FSM_ENGINE.md` 狀態轉換表與 `tools/fsm_runtime/transition_rules.py._HAPPY_PATH` 漂移（E-03 漏洞）。

**觸發條件**：每次 PR 到 main/develop 分支、且異動以下任一檔案即觸發：
- `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md`
- `tools/fsm_runtime/transition_rules.py`
- `tools/fsm_runtime/fsm_runtime.py`

**驗證內容**：
```yaml
fsm_sync_check:
  command: "pytest tools/fsm_runtime/tests/test_md_python_sync.py -v"
  assertions:
    - "MD 中每條 happy-path edge 都能在 _HAPPY_PATH 中找到"
    - "Python _HAPPY_PATH 中每條 core edge 都在 MD 狀態轉換表中出現（AUTO_COMPACT_PENDING / RESUME_VERIFICATION / REMINDER 為抽象來源，豁免）"
    - "all_states() 中的每個狀態名都在 MD 全文中被提及"
  required: true
```

**失敗處理**：FSM Sync 失敗即 Pipeline 中斷；修復方式為同步更新 MD 轉換表或 `_HAPPY_PATH`。

**緊急 bypass**：commit message 含 `[skip-fsm-sync]` 可跳過，但必須在 24h 內補齊同步修正（由 nightly job 追蹤）。

---

### Step: FSM Chaos Verification（nightly，標記 slow，非 PR 必跑）🆕 Phase E / ACT-029

**目的**：在非 PR 時段以 100 輪隨機故障注入驗證 FSM 有界停機保證，防止 ACT-020~026 防護失效（L4.9 Phase E 驗收憑證）。

**觸發條件**：
- **nightly cron**：UTC 每天 02:00 在 `main` 上跑一次
- **手動**：`workflow_dispatch`（供緊急驗證）
- **PR 上不跑**（避免 CI 過慢影響開發節奏）

**驗證內容**：
```yaml
fsm_chaos_check:
  runner: ubuntu-latest          # P1-05 鎖定：seed 指令依賴 Python stdlib，runner 不可為 windows-*
  rounds: 100
  reference_workflow: .github/workflows/aisdlc-sdd-fsm-chaos-nightly.yml  # P1-04 實體化的 nightly workflow
  seed_strategy: "Python stdlib (跨 runner safe，不依賴 GNU/BSD date)"
  seed_command: 'python -c "import datetime; print(datetime.date.today().strftime(''%Y%m%d''))"'
  command: "python -m tools.fsm_runtime.chaos_runner --rounds 100 --seed ${SEED}"
  assertions:
    bounded_count_eq_total: true   # bounded_count == total_rounds（整數比較，避免浮點歧義）
    avg_tokens_lt: 25000           # 平均 token 消耗 < 25K
    max_steps_lte: 120             # 單輪步數硬上限
  pytest_backup:
    pr_command: "pytest tools/fsm_runtime/tests/ -m \"not chaos\""   # PR 上跑（排除 chaos）
    nightly_command: "pytest tools/fsm_runtime/tests/ -m chaos"      # nightly 跑 chaos marker
    success_criteria:
      - "exit_code == 0"
      - "ChaosAggregateTests::test_100_rounds_are_all_bounded passed"
      - "ChaosAggregateTests::test_100_rounds_average_tokens_under_budget passed"
  output: "build/reports/verification/FSM-CHAOS-{date}.json"
```

**跨平台注意事項**（ACT-029 P1-05）：
- 原版 `$(date +%Y%m%d)` 為 POSIX shell 語法，在 Windows runner（PowerShell）失敗
- 改用 `python -c "import datetime; print(datetime.date.today().strftime('%Y%m%d'))"` 確保 Linux/macOS/Windows 三平台一致
- 即便 runner 鎖定 ubuntu-latest，下游 fork repo 採 self-hosted 時仍可繼承 Python 版本

**故障注入類型**（§SDD_improving_Automation_04.md §ACT-029 L583）：
- `STATE_CORRUPTION`：覆寫 FSM-STATE YAML 為亂碼，驗證 `.bak` recovery
- `RETRY_TAMPER`：篡改 retry_count 為極端值，驗證 retry 上限仍守門
- `CI_EVENT_DUP`：投遞重複 `CI-EVENT-*.yaml`，驗證 reconciler 冪等
- `TIMEOUT_SIM`：將 `entered_at` 設為 >168h 前，驗證 timeout_checker 自動 ESCALATION
- `AUTO_COMPACT_BURST`：連續觸發 `trigger_auto_compact`，驗證 ACT-026 per-stage 上限
- `PR_REVIEW_JITTER`：語意相同但措辭不同的失敗理由，驗證 ACT-021 semantic matcher
- `SCG_INFINITE_FAIL`：無限 SCG 失敗，驗證 Rule 9.1 retry budget = 3
- `TRAJECTORY_PREDICTION`：retry_count ≥ 1 時呼叫 consult_predictor，驗證 ACT-035/036 提早切換省 retry budget

**失敗處理**：
- `bounded_ratio < 1.0` 或 `avg_tokens ≥ 25000`：觸發 ESCALATION Issue（P0 bug），並把當次報告附加到 Issue
- 連續 3 個 nightly 失敗：QA Round-3 P1-02 後由 workflow 內建 `track-streak-and-lock` job 執行：
  1. 透過 `gh api /repos/.../workflows/.../runs` 計算連續失敗數（`failure` / `timed_out` 累計，`success` / `cancelled` 歸零）。
  2. 連續失敗 ≥ 3 次時呼叫 `gh issue create` 自動開 P0 Issue（label：`p0,chaos,fsm-runtime`）。
  3. 同時 best-effort 呼叫 `PUT /repos/.../branches/main/protection` 啟用 `required_linear_history` + `required_approving_review_count=2`，收緊 main。
  4. Token 權限不足時以 `::warning::` 註記並留待 repo admin 手動處理（不遮蔽 chaos 失敗本身）。

**緊急 bypass**：無（`main` 的 chaos verification 不可跳過，這是 Phase E 驗收憑證本身）。

---

### Step: Multimodal SpecTrace（跨媒介錨點驗證）🆕 Phase F / ACT-031

**目的**：在 SCG-1 / SCG-2 凍結前，驗證 FRD/SRD 的 `<!-- anchor:<modality>:<id> -->` 錨點與其引用的非文字 artifact（UI mockup / OpenAPI / DB schema / C4 diagram）一致。

**觸發條件**：
- 任一 PR diff 內 FRD/SRD/api yaml/db schema/C4 變更
- nightly main（與其他 step 同批跑）
- 預設 advisory（SLV-008~011 為 `trust_level: proposed`，per Rule 9.11.3）

**驗證內容**：
```yaml
multimodal_spectrace_check:
  runner: ubuntu-latest
  scan_targets:
    - docs/01_requirements/FRD-*.md
    - docs/02_architecture/SRD-*.md
  command: |
    python -m tools.fsm_runtime.multimodal_validator \
      docs/01_requirements/FRD-*.md docs/02_architecture/SRD-*.md \
      --backend session
  strict_mode_command: |
    # 將 SLV-008~011 升級為 verified 後（人工 review），改用此指令以 issue_count > 0 阻擋 PR
    python -m tools.fsm_runtime.multimodal_validator <specs> --backend session --strict
  backend_priority:
    - session       # 預設，零成本（OPEN-F.3 RESOLVED）
    - claude-api    # opt-in；vision 解析 PNG mockup（待 SDK 配置）
    - minimax       # 保留 drop-in（OPEN-F.3 補述）
  assertions:
    proposed_mode:
      - "exit_code == 0（advisory，不阻擋 PR）"
      - "issue_count 寫入 build/reports/verification/MULTIMODAL-{date}.json"
    verified_mode:
      - "exit_code == 0 且 issue_count == 0"
  output: "build/reports/verification/MULTIMODAL-{date}.json"
```

**驗證類別**（4 種 anchor，對應 SLV-008~011）：
- `anchor:ui:<id>` → `docs/99_media/ui/<kebab-id>.{html,md,png,svg}` 對應的 widget 與 AC keywords 是否齊
- `anchor:api:<METHOD> <PATH>` → OpenAPI `paths.<PATH>.<method>` 是否存在 + requestBody required field 對應 UI input
- `anchor:db:<table>` → `docs/07_design/db/{schema.sql,*.yaml}` 是否定義 table 且 backtick 欄位齊全
- `anchor:c4:<component>` → `docs/02_architecture/C4-*.md` Mermaid/PlantUML 是否定義且 SRD 文字提及

**失敗處理**：
- proposed 模式：advisory only — 結果寫入 PR comment（建議檢視），不阻 merge
- verified 模式（M4 末 promote 後）：`issue_count > 0` 即 fail，PR 必須補齊 anchor target 才能合併

**緊急 bypass**：proposed 階段無需 bypass（本來就不阻塞）；verified 後若需臨時放行，須在 PR description 加 `[skip-multimodal: <reason>]` 並由 reviewer 確認。

**相關規格**：
- 工具：[`tools/fsm_runtime/multimodal_validator.py`](../tools/fsm_runtime/multimodal_validator.py)
- 4 adapter：[`tools/fsm_runtime/modality/`](../tools/fsm_runtime/modality/)
- Anchor schema：[`docs_template/sdd/architecture/SPEC-ANCHOR-TEMPLATE.md`](../docs_template/sdd/architecture/SPEC-ANCHOR-TEMPLATE.md)
- 規則庫：`.claude/skills/spec-logical-validator/rules/SLV-008~011.yaml`

---

### Step: Media Store Size Lint（媒體檔案大小強制）🆕 Phase F / QA Round-2 補件

**目的**：強制 Rule 9.13.5 / OPEN-F.4 — `docs/99_media/` 內單檔 < 500 KB（硬上限），≥ 300 KB 警告。從規格層級降到 CI runtime 層，避免大型 PNG/SVG 不知不覺進入 Git LFS。

**觸發條件**：
- 任一 PR diff 觸及 `docs/99_media/**`
- nightly main（同 Multimodal SpecTrace 批次）

**驗證內容**：
```yaml
media_size_check:
  runner: ubuntu-latest
  scan_targets:
    - docs/99_media/**
  command: |
    # 預設 — fail PR 僅在硬上限被破時
    python -m tools.fsm_runtime.media_size_check
  strict_mode_command: |
    # 高 governance 期需要連 warn (≥ 300 KB) 都阻擋時
    python -m tools.fsm_runtime.media_size_check --strict
  thresholds:
    warn_bytes: 307200    # 300 KB
    hard_bytes: 512000    # 500 KB
  assertions:
    - "exit_code == 0 表示無 hard fail（warn 允許通過）"
    - "exit_code == 1 表示至少一個檔案 ≥ 500 KB"
    - "exit_code == 2 表示 root 不存在（CI 配置錯誤）"
```

**失敗處理**：
- `≥ 500 KB`：永遠 fail PR；維護者必須壓縮或拆分（建議使用 `pngquant` / `svgo`）
- `≥ 300 KB`：預設只警告；需 `--strict` 才會 fail

**相關規格**：
- 工具：[`tools/fsm_runtime/media_size_check.py`](../tools/fsm_runtime/media_size_check.py)
- 媒體治理：[`docs/99_media/README.md`](../docs/99_media/README.md)
- 規則出處：CLAUDE.md Rule 9.13.5 + 規劃文件 §5.8 R-31.4

---

### Step: FSM Formal Verification（TLA+/TLC 形式化停機證明）🆕 Phase G / ACT-041~042

**目的**：把 Phase E M2.5 的 Chaos 經驗性驗證升級為 TLA+ 形式化證明，給 SDD FSM 的 bounded halting 一個數學憑證（對應 CLAUDE.md Rule 9.18）。

**觸發條件**：
- PR diff 觸及 `tools/fsm_runtime/transition_rules.py` 或 `tools/fsm_runtime/formal/SDD_FSM.tla` / `*.cfg`
- nightly main（與其他 step 同批）
- 手動 `workflow_dispatch`

**驗證內容**：
```yaml
fsm_formal_check:
  runner: ubuntu-latest
  rounds: 1                            # TLC 為窮舉檢查，單次完整即可
  java_version: "21"                   # OpenJDK 11+ 即可，Phase G v1 採 21
  tlc_version: "v1.8.0"
  cache:
    - tools/fsm_runtime/formal/lib/tla2tools.jar  # 4.2 MB，僅首次 PR 下載
  # QA 修 6：實體化 [skip-tla] bypass — 對齊 §FSM Chaos Verification 規格
  if: "!contains(github.event.head_commit.message, '[skip-tla]')"
  pre_check:
    # Rule 9.18.1 雙源一致性 — 在 TLC 之前先跑 pair-by-pair sync test
    pair_sync_command: "pytest tools/fsm_runtime/tests/test_tla_python_sync.py -v"
    pair_sync_must_pass: true
  command: |
    bash tools/fsm_runtime/formal/run_tlc.sh
  parse_summary:
    # run_tlc.sh / .ps1 在末尾輸出 machine-readable summary 三行（QA 修 1）：
    #   TLC_DISTINCT=583
    #   TLC_GENERATED=2901
    #   TLC_DEPTH=30
    distinct: "grep -oE 'TLC_DISTINCT=[0-9]+' | cut -d= -f2"
    generated: "grep -oE 'TLC_GENERATED=[0-9]+' | cut -d= -f2"
    depth: "grep -oE 'TLC_DEPTH=[0-9]+' | cut -d= -f2"
  assertions:
    exit_code: 0                       # 全 INVARIANT 通過
    distinct_states_min: 500           # 至少 500 個 (state×retry×recovery) tuples
    reachable_state_coverage_min: 0.95 # Rule 9.18.3 — 26 declared / reachable ≥ 25
  output: "build/reports/formal/TLC-COVERAGE-{date}.md"
  strict_mode_command: |
    # M5 v2 落地後改用 strict（含 liveness 證明）
    DEPTH=80 bash tools/fsm_runtime/formal/run_tlc.sh
```

**雙源一致性硬式守門**（QA 修 2 / Rule 9.18.1）：
CI 在 TLC 之前先跑 `tools/fsm_runtime/tests/test_tla_python_sync.py`：
- `test_tla_covers_every_happy_path_pair` — `_HAPPY_PATH` 每條 (src, dst) 必須對應 .tla transition
- `test_all_python_states_declared_in_tla_state_sets` — 所有 state 必須在 .tla 4 大集合宣告
- `test_tla_extra_pairs_have_python_basis` — .tla 不可引入 transition_rules 不允許的虛構 transition
- 🆕 `test_all_declared_states_reachable_from_init_offline` — **離線 BFS 窮舉**：所有宣告狀態從 INIT 可達（reachable=N/N=100%，**零 Java 依賴**，每次 PR gate 強制，取代「推算 reachable」）
- 🆕 `test_every_state_can_reach_a_terminal_offline` — 反向 BFS：每狀態都能抵達 terminal（EventuallyTerminal 結構必要條件，離線可驗）

任一 fail 立即 block PR；不需等 TLC 跑完。離線可達性不變量讓 reachable coverage 在**無 Java 環境**也被機器守門。

**Nightly streak lock**（QA 修 6）：對齊 §FSM Chaos Verification:251 的 track-streak-and-lock 規格：
- `nightly cron`：UTC 每天 02:30 在 `main` 上跑（與 Chaos 02:00 錯開）
- 連續 3 個 nightly fail → workflow 內建 `track-streak-and-lock` job：
  1. `gh api /repos/.../workflows/.../runs` 計算連續 fail 數
  2. ≥ 3 → `gh issue create` 開 P1 Issue（label: `p1,formal,fsm-tla`）
  3. best-effort `PUT /repos/.../branches/main/protection` 收緊 main（required reviews=2）
- Token 不足時 `::warning::` 並由 admin 手動處理

**檢查項目**：
- `TypeOK` — 所有 reachable state ∈ States（structural 守門）
- `RetryBounded` — retry ≤ MAX_RETRY（Rule 9.1）
- `RecoveryBounded` — recovery ≤ MAX_RECOVERY（Rule 9.14.1）
- `NotInBothSets` — ObservationStates ∩ Terminals = ∅（Rule 9.18.4 結構約束）
- 全部宣告 FSM state 必須可達（≥ 95%；目前 41/41 = 100%，2026-06-02 本地 TLC 實證 807 distinct states / No error found）

**雙源一致性檢查**（Rule 9.18.1）：
- 若 PR 修改 `_HAPPY_PATH` 但未同步 `SDD_FSM.tla`，TLC reachable 數會劇烈變化（< 23 / > 30）→ fail
- 反之若 .tla 加入新 state 但 transition_rules 沒對應，pytest `test_md_python_sync` fail（沿用 ACT-022 雙源檢查鏈）

**失敗處理**：
- `Invariant violated`：直接 fail PR，必須修正 .tla 或 transition_rules，並更新 `TLC-COVERAGE-{date}.md`
- `Reachable < 95%`：表示有狀態無法從 INIT 到達，可能是 transition rule 漏了 → fail PR
- `Liveness counterexample`（v2 後）：fail PR 並要求補 fairness 註記

**緊急 bypass**：commit message 含 `[skip-tla]` 可跳過（已實體化於上方 yaml `if:` 條件），但須在 24h 內補齊；nightly streak lock 會記分連續違反並自動開 P1 issue + 收緊 main。

**相關規格**：
- 規格：[`tools/fsm_runtime/formal/SDD_FSM.tla`](../tools/fsm_runtime/formal/SDD_FSM.tla)
- 配置：[`tools/fsm_runtime/formal/SDD_FSM.cfg`](../tools/fsm_runtime/formal/SDD_FSM.cfg)
- 執行入口：[`run_tlc.sh`](../tools/fsm_runtime/formal/run_tlc.sh)（CI/Linux）／🆕 [`tlc_runner.py`](../tools/fsm_runtime/tlc_runner.py)（**跨平台，Windows PowerShell 5.1 亦可**：`python -m tools.fsm_runtime.tlc_runner --download`；opt-in pytest `SDD_RUN_TLC=1 pytest -m tlc`）／`run_tlc.ps1`（需 PowerShell Core / pwsh）
- 雙源一致性測試：[`tools/fsm_runtime/tests/test_tla_python_sync.py`](../tools/fsm_runtime/tests/test_tla_python_sync.py)
- 規則出處：CLAUDE.md Rule 9.18.1 ~ 9.18.4
- 報告範本：`build/reports/formal/TLC-COVERAGE-{date}.md`

---

### Step: Drift Daily Report（nightly，標記 slow）🆕 Phase G M4 / ACT-040

**目的**：每日累積 PostCommit drift 報告，產出 7-day rolling daily summary（Rule 9.17.4）。

```yaml
fsm_drift_daily:
  type: scheduled-nightly
  schedule: "30 2 * * *"          # UTC 02:30（與 Chaos 02:00 / TLC 02:30 streak lock 錯開排程，避開競爭）
  command: |
    python -c "from tools.fsm_runtime.drift_monitor import write_daily_report; write_daily_report()"
  output_path: build/reports/drift/DAILY-{YYYY-MM-DD}.md
  rolling_days: 7
  failure_action: warning_only      # advisory，不阻擋 main
```

**邊界**：
- 連續 3 commits drift_score ≥ 0.3 → 自動寫 `CONSECUTIVE-{date}.yaml` + 警告 PR Reviewer（Rule 9.17.3）
- PostCommit hook 失敗一律 advisory（Rule 9.17.1），不阻擋 commit

**相關規格**：
- 設計：[`cicd/SDD_DRIFT_MONITOR.md`](SDD_DRIFT_MONITOR.md)
- 實作：[`tools/fsm_runtime/drift_monitor.py`](../tools/fsm_runtime/drift_monitor.py)
- 安裝腳本：[`tools/install_hooks/install_post_commit.sh`](../tools/install_hooks/install_post_commit.sh) / `.ps1`
- 規則出處：CLAUDE.md Rule 9.17.1 ~ 9.17.4

---

## 🔄 DocPipeline 標準化

**定義**：文件 CI/CD Pipeline 的標準化執行流程

```yaml
doc_pipeline:
  name: "AISDLC SDD DocPipeline"
  version: "v1.0"
  trigger:
    - "PR 到 main/develop 分支"
    - "文件目錄（docs/）有變更時"

  stages:
    - name: "Markdown Lint"
      tool: "markdownlint-cli2"
      config: ".markdownlint.yaml"
      fail_on_error: true

    - name: "Link Check"
      tool: "markdown-link-check"
      config: ".mlc_config.json"
      fail_on_error: false
      notes: "內部連結失敗為警告，外部連結失敗忽略（可能因網路限制）"

    - name: "ADR Index Update"
      tool: "adr-index-maintenance（technical-writer skill）"
      trigger: "docs/02_architecture/adr/ 有新增或修改時"
      output: "docs/02_architecture/adr/ADR-INDEX.md 自動更新"
      fail_on_error: false

    - name: "OpenAPI Validate"
      tool: "spectral / openapi-validator"
      config: ".spectral.yaml"
      trigger: "docs/02_architecture/api/ 有新增或修改時"
      validation_rules:
        - "OpenAPI 3.1 語法正確"
        - "所有 endpoint 有 summary"
        - "所有 Response Schema 已定義"
        - "x-aisdlc.related_us 欄位不為空"
        - "安全機制已定義（securitySchemes）"
      fail_on_error: true
      output: "build/reports/verification/APISpec-Validation-{date}.md"

    - name: "RTM Completeness Check"
      tool: "custom SpecTrace script"
      trigger: "docs/03_testing/RTM-*.md 有變更時"
      validation_rules:
        - "所有 US 都有對應 AC（無空白 AC 欄）"
        - "AC 覆蓋率 ≥ 80%（有 AT 的 AC 數 / 總 AC 數）"
        - "EPIC → Feature → US → AC 四層追溯完整"
        - "NFR 至少 1 個已對應到 US"
      fail_on_error: false
      output: "build/reports/verification/RTM-Completeness-{date}.md"
      notes: "覆蓋率低於 80% 為警告，低於 60% 為錯誤（中斷 Pipeline）"

    - name: "Spec Compliance Report"
      tool: "spec_compliance_check（Agent skill）"
      output: "build/reports/verification/SpecCompliance-{date}.md"
      fail_on_error: false
      notes: "生成報告供人工審查，不自動中斷 Pipeline"
```

---

---

## 🔗 CI/CD → FSM 狀態橋接（ACT-007）

**目的**：將 CI/CD Pipeline 驗證結果橋接至 FSM_STATE.yaml，確保 CI 失敗能觸發 FSM retry_count 遞增。

**橋接流程**：
```yaml
ci_to_fsm_bridge:
  trigger: "每次 CI/CD Stage 完成後（成功或失敗）"
  
  output_event:
    path: "build/reports/fsm/CI-EVENT-{date}-{pipeline_id}.yaml"
    schema:
      pipeline_id: "{uuid}"
      stage: "DocLint | SpecTrace | SLV | OpenAPI | RTM"
      result: "PASS | FAIL | WARNING"
      failure_reason: "{描述}"
      scg_gate: "SCG-N"  # 對應的 SCG 閘門（若有）
      timestamp: "{ISO8601}"
      
  fsm_update_rules:
    DocLint_FAIL:
      action: "寫入 CI-EVENT，FSM 下次執行時讀取並輸出警告"
      update_retry_count: false  # DocLint 是格式問題，不計入 SCG retry
    SLV_FAIL:
      action: "寫入 CI-EVENT，觸發 SCG_VALIDATION retry_count++"
      update_retry_count: true
      target_counter: "SCG_VALIDATION"
    SpecTrace_FAIL:
      action: "寫入 CI-EVENT，記錄為 WARNING（Sprint 3+ 轉為 ERROR）"
      update_retry_count: false
    OpenAPI_FAIL:
      action: "寫入 CI-EVENT，觸發 SCG_VALIDATION retry_count++"
      update_retry_count: true
      target_counter: "SCG_VALIDATION"
      
  fsm_read_timing: "FSM 在每次 SCG_VALIDATION 開始時，掃描所有未處理的 CI-EVENT-*.yaml"
```

**FSM-STATE 更新**：CI-EVENT 被讀取後，FSM 將 `processed: true` 寫入 CI-EVENT 文件，防止重複計數。

---

## 📁 相關配置範本位置

```
docs/08_deployment/iac/
└── IaCS-cicd-base-layer.md  ← IaC 規格文件（此文件補充）

docs/08_deployment/
└── SDD_CICD_BASE_LAYER.md   ← 本文件
```

---

## 🧪 本機優先 CI 平價層（Local-First CI Parity，ADR-001 / 2026-06-11）

> **動機**：上版 GitHub 反覆紅燈，根因為 CI 基礎設施（artifact 配額耗盡 / 推送
> 競爭 / Node20 退役）而非程式碼；且 push/PR 原本沒有任何 workflow 跑離線測試。
> 對策：讓「地端與雲端跑同一組檢查」，push 前本機強制把關。詳見
> `docs/02_architecture/adr/ADR-001-local-first-ci-parity.md`。

**單一真相源**：`scripts/ci-gate.sh`（Windows 用 `scripts/ci-gate.ps1`）——離線閘門
= `pytest -m "not chaos"`（含 offline reachability BFS / 1473+）+ `arch_fitness`
（structural fail 才擋）；`--full-tlc` 另跑五軌 TLA+/TLC。

| 支柱 | 檔案 | 用途 |
|------|------|------|
| 一、迷你正式環境 | `docker/Dockerfile.ci`、`docker-compose.yml`（`ci-runner`） | python:3.11-slim + Java + tla2tools.jar，鏡像 ubuntu-latest，消除 Win/Linux 差異 |
| 二、act 地端跑 Actions | `.actrc`、`scripts/act-ci.sh`、`.github/act/push-event.json` | 用 Docker 在地端模擬 `.github/workflows/`，抓 YAML/步驟/相容性錯 |
| 三、自動攔截點 | `.pre-commit-config.yaml`、`.githooks/pre-push`、`scripts/install-hooks.{sh,ps1}` | push 前強制跑 `ci-gate.sh`，本機過才能 push |
| 四、Mock / 地端 LLM | `tools/fsm_runtime/modality/llm_backend.py`（`MockBackend`、`LocalOpenAIBackend`） | 外部 API/LLM 地端 Mock 或指向 localhost（Ollama/vLLM）；CI 預設 `session` 維持 hermetic |

**雲端硬化（同 ADR-001）**：所有 `upload-artifact` 改 `continue-on-error: true` +
降 `retention-days`（observability-only，配額耗盡不判紅）；`drift-daily` 與
`arch-fitness`(nightly) 共用 `main-push-serialize` concurrency + rebase-retry 消除
推送競爭；action 升至 Node24 相容（checkout@v5 / setup-python@v6）；新增
`.github/workflows/aisdlc-sdd-ci.yml`（monorepo 根層）於 push(main)/PR 跑離線閘門（呼叫同一份 `ci-gate.sh`）。
另新增 `.github/workflows/aisdlc-sdd-artifact-cleanup.yml`（每日 03:00 UTC + 手動）用 gh CLI 刪除
expired/逾齡 artifact，做配額長期治本（ADR-001 Next Action #1）。

**啟用步驟**：
```bash
bash scripts/install-hooks.sh            # 啟用 pre-push 閘門（或 .ps1）
docker compose run --rm ci-runner        # 迷你正式環境跑離線閘門
bash scripts/act-ci.sh                    # 選用：act 跑 aisdlc-sdd-ci.yml
docker compose --profile llm up -d local-llm   # 選用：地端 LLM（Ollama）
```

---

## 🔗 相關文件

- [SDD 核心原則](../02_architecture/SDD_Core_Principles.md)
- [Spec-First Gate Workflow](../../AISDLC_v0.09/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)
- [Phase 01 執行藍圖](../04_planning/AISDLC_TO_SDD_Planning_Phase_01.md)
- [ADR-001 本機優先 CI 平價層](../../docs/02_architecture/adr/ADR-001-local-first-ci-parity.md)（repo-root docs/ = 框架自身 SDD 產出，見 CLAUDE.md 目錄樹）

---

**建立者**: AISDLC SDD 轉型架構師
**最後更新**: 2026-06-11（ADR-001 本機優先 CI 平價層）
