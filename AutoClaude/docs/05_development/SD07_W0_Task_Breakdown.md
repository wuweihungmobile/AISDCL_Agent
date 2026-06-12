# SD_07 W0 Task Breakdown — Tech Lead 交付

| 項目 | 內容 |
|------|------|
| 提交者 | Tech Lead |
| 提交日期 | 2026-05-18（G0 啟動前置 DoD） |
| 對應規劃 | [SD_Improving_07.md](../04_planning/SD_Improving_07.md) v1.1 §4 W0 / [SD07_Execution_Guide.md](SD07_Execution_Guide.md) §3 W0 |
| ADR 依據 | [ADR-SD07-001-loc-policy.md](../04_planning/ADR/ADR-SD07-001-loc-policy.md) v1.0 §4.2 / §5 |
| W0 PD | 3 PD |
| G0 啟動日 | 2026-05-20 |
| 文件狀態 | APPROVED（PM 形式核准後可進入 W0 執行）|

---

## 1. W0 任務細項拆解（T0-1 ~ T0-9）

| 任務 ID | 子任務 | 預估 PD | 負責角色 | 依賴 | 交付物 |
|--------|--------|---------|---------|------|--------|
| T0-1 | ADR-SD07-001-loc-policy.md（規劃階段已完成 ✅）| 0（已完成）| Architect + SA + SD | — | `docs/04_planning/ADR/ADR-SD07-001-loc-policy.md` |
| T0-2 | 升級 `tools/check_loc_budget.py` 為分級判定 | 0.5 | SD | T0-1 | upgraded `tools/check_loc_budget.py` |
| T0-3 | 新建 `.loc-budget.toml`（per-file overrides + 書面理由欄位）| 0.2 | SD | T0-2 | `.loc-budget.toml` |
| T0-4 | 重新測算 baseline（吸收 W3 alembic / adapter 永久增量）| 0.3 | SD | T0-2, T0-3 | 更新 `.loc_baseline` |
| T0-5 | `tests/contract/test_loc_budget_tiered.py`（≥ 6 case 各分級邊界 + override + 750 紅線）| 0.5 | SD + QA | T0-2 | 新測試檔（≥ 6 case） |
| T0-6 | SD_07 AC Matrix scaffolding（≥ 18 條 AC，各含量測命令）| 0.5 | SA | — | `docs/03_testing/SD07_AC_Matrix.md` |
| T0-7 | `tests/integration/fixtures/sd07_e2e_samples/`（5 種 Brain/Executor 失敗情境 fixture）| 0.4 | SD | — | fixture YAML × 5 |
| T0-8 | `.env.example` 補 LOC_BUDGET_POLICY_VERSION=v2 + SD07_REAL_PG_E2E_ENABLED=true | 0.1 | Tech Lead | — | 更新 `.env.example` |
| T0-9 | 撰寫 SD07_Execution_Guide.md（規劃階段已完成 ✅）| 0（已完成）| Tech Lead | — | `docs/05_development/SD07_Execution_Guide.md` |
| **合計** | | **2.5 PD** | | | （含 0.5 PD 緩衝）|

> 注：T0-1 + T0-9 已於規劃階段完成；W0 實際執行剩 7 項，0.5 PD 緩衝給 T0-2 工具升級風險。

---

## 2. 分級 LOC Budget Table 設計（依 ADR §4.2 落實）

### 2.1 LOC_TIERS 設計表

| 分類 | budget | 識別模式（glob/path）| 既有檔案範例 |
|------|--------|---------------------|-------------|
| `data` | **≤ 150** | `autoclaude/models/*.py`<br>`autoclaude/core/ports/*.py`（Protocol-only） | `playbook.py`、`decision.py`、`escalation.py` |
| `plugin_entry` | **≤ 250** | `autoclaude/plugins/*_plugin.py`<br>`autoclaude/plugins/*/plugin.py` | `checkpoint_plugin.py`、`token_guard_plugin.py`、`goal_synthesis_plugin.py` |
| `strategy` | **≤ 300** | `autoclaude/core/services/mutation/*.py`<br>`autoclaude/decision/prompt_builder.py`<br>`autoclaude/execution/error_classifier.py` | `_simple_mutations.py`、`_conditional.py` |
| `adapter` | **≤ 400** | `autoclaude/infra/adapters/*.py`<br>`autoclaude/infra/repositories/*.py` | `pty_executor.py`、`minimax_brain.py`、`pg_state_repository.py` |
| `service` | **≤ 500** | `autoclaude/core/services/*.py`<br>`autoclaude/execution/steps_orchestrator/*.py`<br>`autoclaude/execution/playbook_runner.py`<br>`autoclaude/execution/*.py`（非 strategy）| `auto_resume.py`、`failure_tracker.py`、`embedding_writer.py` |
| `contract` | **≤ 400** | `autoclaude/core/hookspec.py`<br>`autoclaude/core/wiring.py`<br>`autoclaude/execution/types.py` | `hookspec.py`、`wiring.py`、`types.py` |
| `absolute_limit` | **≤ 750** | `*`（global hard cap）| 任何檔案 |
| `test` | **不設上限** | `tests/**/*.py` | — |

### 2.2 分級判定優先序（path-based first-match）

```
1. tests/**/*.py            → test（豁免）
2. .loc-budget.toml [overrides] 內檔案 → 強制套用 override.tier
3. autoclaude/models/、autoclaude/core/ports/ → data
4. autoclaude/plugins/*_plugin.py、autoclaude/plugins/*/plugin.py → plugin_entry
5. autoclaude/core/services/mutation/、autoclaude/decision/prompt_builder.py、autoclaude/execution/error_classifier.py → strategy
6. autoclaude/infra/adapters/、autoclaude/infra/repositories/ → adapter
7. autoclaude/core/hookspec.py、autoclaude/core/wiring.py、autoclaude/execution/types.py → contract
8. autoclaude/core/services/、autoclaude/execution/steps_orchestrator/、autoclaude/execution/playbook_runner.py、autoclaude/execution/*.py → service
9. fallback → absolute_limit（750）
```

### 2.3 既有 14 違規檔處置（ADR §4.4 落實）

| 檔案 | 現 LOC | 分級 | budget | 狀態 | 處置 |
|------|--------|------|--------|------|------|
| `steps_orchestrator/_impl.py` | 736 | service | 500 | ⚠️ **超 236** | **W1 拆解**（強制）|
| `pg_state_repository.py` | 485 | adapter | 400 | ⚠️ **超 85** | W1 評估：拆 `_read_path.py + _write_path.py` 或 `.loc-budget.toml` override |
| `prompt_builder.py` | 416 | strategy | 300 | ⚠️ **超 116** | W1 評估：拆三純函式檔 或 `.loc-budget.toml` override |
| `playbook_runner.py` | 440 | service | 500 | ✅ 通過 | — |
| `failure_tracker.py` | 371 | service | 500 | ✅ 通過 | — |
| `dual_state_repository.py` | 316 | adapter | 400 | ✅ 通過 | — |
| `hookspec.py` | 311 | contract | 400 | ✅ 通過 | — |
| `embedding_writer.py` | 310 | service | 500 | ✅ 通過 | — |
| `playbook_evolver.py` | 309 | service | 500 | ✅ 通過 | — |
| `minimax_client.py` | 292 | adapter | 400 | ✅ 通過 | — |
| `config_resolver.py` | 285 | service | 500 | ✅ 通過 | — |
| `wiring.py` | 263 | contract | 400 | ✅ 通過 | — |
| `types.py` | 258 | contract | 400 | ✅ 通過 | — |
| `auto_resume.py` | 258 | service | 500 | ✅ 通過 | — |

**結果**：12/14 立即合規；3 個 W1 處置（_impl.py 必拆，pg_state / prompt_builder 評估）

---

## 3. 工具升級交付物（對應項目 2 Architect 規範）

| 交付物 | 路徑 | 負責 | 驗收 |
|--------|------|------|------|
| `tools/check_loc_budget.py` 升級版 | `tools/check_loc_budget.py` | SD | `python tools/check_loc_budget.py` 分級制下 violations ≤ 3 |
| `.loc-budget.toml` 配置檔 | `.loc-budget.toml`（PROJECT_ROOT） | SD | `cat .loc-budget.toml \| grep "^\[overrides\]"` 存在 |
| Contract test | `tests/contract/test_loc_budget_tiered.py` | SD | `pytest tests/contract/test_loc_budget_tiered.py -v` ≥ 6 case 綠 |
| Baseline 校準 | `.loc_baseline` | SD | 吸收 SD_06 W3 alembic 0007-0014 永久增量 |
| 環境變數 | `.env.example` | Tech Lead | 含 `LOC_BUDGET_POLICY_VERSION=v2` + `SD07_REAL_PG_E2E_ENABLED=true` |
| Execution Guide | `docs/05_development/SD07_Execution_Guide.md` | Tech Lead | 已完成 ✅ |

完整工具升級規範詳見：[SD07_W0_check_loc_budget_Upgrade_Spec.md](../02_architecture/SD07_W0_check_loc_budget_Upgrade_Spec.md)（Architect 草擬）

---

## 4. W0 Gate G0 驗收條件（SSOT 沿用 SD_Improving_07.md §4 W0 / SD07_Execution_Guide.md §3 W0）

```bash
[  ] python tools/check_loc_budget.py                                      # 分級制下 violations ≤ 3
[  ] python -m pytest tests/contract/test_loc_budget_tiered.py -v          # ≥ 6 case 綠
[  ] cat .loc-budget.toml | grep "^\[overrides\]"                          # 存在
[  ] ls docs/04_planning/ADR/ADR-SD07-001-loc-policy.md                    # 存在 + 三方+PM 簽名
[  ] python -m pytest tests/ -q --tb=no | tail -3                          # ≥ 1,808 passed（+6 W0 新測）
[  ] grep "LOC_BUDGET_POLICY_VERSION\|SD07_REAL_PG_E2E_ENABLED" .env.example  # 兩行
[  ] ls docs/03_testing/SD07_AC_Matrix.md                                  # ≥ 18 條 AC
[  ] ls tests/integration/fixtures/sd07_e2e_samples/                       # 5 個 fixture YAML
```

---

## 5. 風險與緩解（W0 內）

| 風險 | 等級 | 緩解 |
|------|------|------|
| 分級判定錯誤導致 false positive | 🟠 | `.loc-budget.toml` overrides + Architect/SD 雙簽 |
| baseline 校準漂移過大破壞既有 CI | 🟠 | T0-4 校準前先 dry-run + Architect 確認 |
| contract test 覆蓋率不足 | 🟠 | T0-5 強制 ≥ 6 case 含各分級邊界 + override + 750 紅線 |
| AC Matrix scaffolding 不夠細 | 🟡 | T0-6 強制 ≥ 18 條（AC0×3 / AC1×3 / AC2×2 / AC3×2 / AC4×2 / AC5×3 / AC6×3）|

---

## 6. PM 形式核准點

依 ADR-SD07-001 §10 + SD_07 §9.2.2，PM 已於 2026-05-18 形式核准 LOC 政策（#1）。本 W0 Task Breakdown 為 G0 前置 DoD 交付物，**無需另一輪 PM 簽核**，提交即視為 Tech Lead 就位。

---

## 7. 文件版本

| 版本 | 日期 | 內容 |
|------|------|------|
| v1.0 | 2026-05-18 | Tech Lead 初版交付（G0 啟動前置 DoD）|
