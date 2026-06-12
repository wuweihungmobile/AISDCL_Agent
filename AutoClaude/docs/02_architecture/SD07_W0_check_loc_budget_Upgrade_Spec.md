# SD_07 W0 — `tools/check_loc_budget.py` 升級規範（Architect 草擬）

| 項目 | 內容 |
|------|------|
| 提交者 | Architect |
| 提交日期 | 2026-05-18（G0 啟動前置 DoD） |
| ADR 依據 | [ADR-SD07-001-loc-policy.md](../04_planning/ADR/ADR-SD07-001-loc-policy.md) v1.0 §4.2 / §5.1 / §5.2 |
| W0 對應任務 | T0-2 / T0-3 / T0-4 / T0-5 |
| 文件狀態 | APPROVED（三方共識 + PM 形式核准後即生效）|

---

## 1. 升級目標

### 1.1 既有問題（升級前）

`tools/check_loc_budget.py` 目前為「**個別 hardcoded 路徑 + 總量 cap × 1.20**」二元判定：

```python
BUDGETS: list[tuple[str, int, str]] = [
    ("autoclaude/core/kernel.py",                   250, "Kernel"),
    ("autoclaude/core/event_bus.py",                200, "EventBus + ResolutionPolicy"),
    ("autoclaude/plugins/*.py",                     250, "Plugin"),
    ("autoclaude/core/services/mutation/*.py",       80, "IMutationStrategy"),
]
TOTAL_INCREASE_LIMIT = 1.20
```

**缺陷**：
- 大部分檔案（adapter / service / orchestrator）未被 per-file 檢查
- 缺乏分級判定（一律 250 一刀切過嚴）
- 無 per-file override 機制（純函數庫合理超 250 也會誤警）
- 總量 cap 隨 W3 alembic / adapter 永久增量持續超標（13847 > 12904）

### 1.2 升級後

依 ADR-SD07-001 §4.2 採**分級 LOC budget + per-file override + 絕對紅線 750**：

| 機制 | 來源 |
|------|------|
| `LOC_TIERS` table（內建分級規則）| 程式碼常數 |
| `.loc-budget.toml` overrides（per-file 例外）| TOML 配置 |
| 絕對紅線 ≤ 750 LOC | 程式碼常數 |
| 總量 baseline 自動 fallback | 既有機制保留（向後相容）|

---

## 2. 升級規格（§5.1 + §5.2 落實）

### 2.1 LOC_TIERS 內建表（程式碼常數）

```python
# 分級判定優先序：path-based first-match
LOC_TIERS: list[dict] = [
    {
        "name": "test",
        "budget": None,  # 不設上限
        "patterns": ["tests/**/*.py"],
    },
    {
        "name": "data",
        "budget": 150,
        "patterns": [
            "autoclaude/models/*.py",
            "autoclaude/core/ports/*.py",
        ],
    },
    {
        "name": "plugin_entry",
        "budget": 250,
        "patterns": [
            "autoclaude/plugins/*_plugin.py",
            "autoclaude/plugins/*/plugin.py",
        ],
    },
    {
        "name": "strategy",
        "budget": 300,
        "patterns": [
            "autoclaude/core/services/mutation/*.py",
            "autoclaude/decision/prompt_builder.py",
            "autoclaude/execution/error_classifier.py",
        ],
    },
    {
        "name": "adapter",
        "budget": 400,
        "patterns": [
            "autoclaude/infra/adapters/*.py",
            "autoclaude/infra/repositories/*.py",
        ],
    },
    {
        "name": "contract",
        "budget": 400,
        "patterns": [
            "autoclaude/core/hookspec.py",
            "autoclaude/core/wiring.py",
            "autoclaude/execution/types.py",
        ],
    },
    {
        "name": "service",
        "budget": 500,
        "patterns": [
            "autoclaude/core/services/*.py",
            "autoclaude/core/services/**/*.py",
            "autoclaude/execution/steps_orchestrator/*.py",
            "autoclaude/execution/playbook_runner.py",
            "autoclaude/execution/*.py",
        ],
    },
]
ABSOLUTE_LIMIT = 750   # 全域絕對紅線（任何分級不得超）
TOTAL_INCREASE_LIMIT = 1.20  # 向後相容保留
```

### 2.2 `.loc-budget.toml` overrides 格式

```toml
# .loc-budget.toml — per-file LOC budget overrides
# 必須附書面理由（PR description 註記）+ Architect / SD 雙簽
# 季度 review（避免長期積累）

[overrides]
# 純函數庫例外（多獨立函數可共處，拆散反致呼叫端散亂）
"autoclaude/decision/prompt_builder.py" = { tier = "service", reason = "纯函式集中，拆散反致呼叫端散亂；W1 評估後決定" }

# 後續可視需要添加
# "<path>" = { tier = "<tier_name>", reason = "<書面理由>" }
```

**override 欄位規範**：
- `tier`：必須為 `LOC_TIERS` 中存在的 `name`
- `reason`：必須為非空字串（≥ 1 句書面理由）
- override 後仍受 `ABSOLUTE_LIMIT=750` 約束

### 2.3 升級後判定流程

```
for each *.py in PROJECT_ROOT:
    1. 若匹配 tests/**/*.py → skip（不設上限）
    2. 若 path 在 .loc-budget.toml [overrides] → 強制套用 override.tier 的 budget
    3. 否則依 LOC_TIERS 順序 first-match path glob
    4. fallback → 使用 ABSOLUTE_LIMIT=750（不歸入任何分級）
    5. 若 loc > budget → 記錄違反
    6. 若 loc > ABSOLUTE_LIMIT=750（即使有 override）→ 記錄違反（紅線不可越）
```

### 2.4 輸出格式

```
[check_loc_budget v2] tier=service path=autoclaude/execution/steps_orchestrator/_impl.py loc=736 > budget=500
[check_loc_budget v2] tier=adapter  path=autoclaude/infra/repositories/pg_state_repository.py loc=485 > budget=400
[check_loc_budget v2] tier=strategy path=autoclaude/decision/prompt_builder.py loc=416 > budget=300

[check_loc_budget v2] total=13847 baseline=11540 cap=13848 violations=3
```

### 2.5 CLI 參數

| 參數 | 說明 |
|------|------|
| `(無)` | 執行檢查（CI gate）；違反 return exit code 1 |
| `--update` | 更新總量 baseline（謹慎使用） |
| `--report` | 輸出 JSON 格式統計（per-tier loc 分佈 + violations） |
| `--audit-overrides` | 列出所有 `.loc-budget.toml` overrides + 季度 review 提醒 |

---

## 3. 實作交付物（W0 必交付）

| 交付物 | 路徑 | 驗收命令 | 預期結果 |
|--------|------|---------|---------|
| 升級版 `check_loc_budget.py` | `tools/check_loc_budget.py` | `python tools/check_loc_budget.py` | violations ≤ 3（W0 末）/ violations=0（W1 末）|
| `.loc-budget.toml` | PROJECT_ROOT/`.loc-budget.toml` | `python -c "import tomllib; tomllib.load(open('.loc-budget.toml','rb'))"` | parse 成功 |
| Contract test | `tests/contract/test_loc_budget_tiered.py` | `pytest tests/contract/test_loc_budget_tiered.py -v` | ≥ 6 case 綠 |
| Baseline 校準 | `.loc_baseline` | `cat .loc_baseline` | 吸收 W3 alembic 後合理數值 |

### 3.1 Contract Test 設計（T0-5，≥ 6 case）

```python
# tests/contract/test_loc_budget_tiered.py

def test_data_tier_budget_enforced():
    """data 分級 ≤ 150 LOC：autoclaude/models/playbook.py 等"""

def test_plugin_entry_tier_budget_enforced():
    """plugin_entry 分級 ≤ 250 LOC：autoclaude/plugins/*_plugin.py"""

def test_strategy_tier_budget_enforced():
    """strategy 分級 ≤ 300 LOC：autoclaude/core/services/mutation/*.py"""

def test_adapter_tier_budget_enforced():
    """adapter 分級 ≤ 400 LOC：autoclaude/infra/adapters/, repositories/"""

def test_service_tier_budget_enforced():
    """service 分級 ≤ 500 LOC：playbook_runner / orchestrator"""

def test_absolute_limit_750_enforced():
    """ABSOLUTE_LIMIT 紅線：任何檔案不得超 750 LOC（包含 override）"""

# 可選擴增：
def test_override_mechanism_respected():
    """.loc-budget.toml override 套用後 tier 變更"""

def test_test_files_skipped():
    """tests/**/*.py 完全豁免"""
```

---

## 4. 向後相容

| 項目 | 處理 |
|------|------|
| 既有 `BUDGETS` 個別檔案規則（Kernel / EventBus / Plugin / IMutationStrategy）| **取代為** `LOC_TIERS` 中 plugin_entry / strategy 分級 |
| `TOTAL_INCREASE_LIMIT = 1.20` 總量 cap | **保留**（向後相容）；分級違反 + 總量超 cap 都記錄 |
| `--update` baseline 更新 | **保留**（既有行為不變）|
| `.loc_baseline` 檔案 | **保留**（總量 baseline）|
| exit code 1 表示違反 | **保留**（CI gate 不變）|

---

## 5. 風險與緩解

| 風險 | 等級 | 緩解 |
|------|------|------|
| `LOC_TIERS` patterns 衝突（多分級同時匹配）| 🟠 | first-match 優先序 + contract test 覆蓋邊界 |
| TOML parse 失敗破壞 CI | 🟠 | `.loc-budget.toml` 缺失時 fallback 至 empty overrides + warning |
| override 濫用（規避真正應拆的檔案）| 🟠 | 季度 audit + Architect/SD 雙簽 + `--audit-overrides` 列出 |
| ABSOLUTE_LIMIT 紅線被誤繞過 | 🔴 | 即使有 override，最後仍強制比對 750；contract test 覆蓋 |
| 升級後 false positive 暴增 | 🟠 | T0-4 baseline dry-run；W0 末 violations ≤ 3 為合格門檻 |

---

## 6. 與 ADR-SD07-001 §5.1 / §5.2 對應

| ADR 條目 | 本規範對應 |
|---------|----------|
| §5.1 LOC_TIERS dict | §2.1 LOC_TIERS list（保留結構，調為 list 以保 first-match 順序）|
| §5.2 `.loc-budget.toml` overrides | §2.2 TOML 格式 + override 欄位規範 |
| §5.3 contract test ≥ 6 case | §3.1 Contract Test 設計 |
| §6.1 絕對紅線 ≤ 750 | §2.1 ABSOLUTE_LIMIT + §2.3 判定流程 step 6 |
| §6.2 例外申請流程（Architect/SD 雙簽 + 季度 review）| §2.2 override 欄位 reason 強制 + §2.5 `--audit-overrides` |
| §4.4 既有 14 檔處置 | §2.3 判定流程 + 既有 12/14 立即合規 |

---

## 7. 三方審查狀態

| 角色 | 狀態 | 立場 |
|------|------|------|
| Architect | ✅ APPROVED（本草案）| 落實 ADR §5.1 / §5.2；ABSOLUTE_LIMIT=750 紅線設計合理 |
| SA | ⏳ 待 SD 實作後審查 | 分級判定邏輯 + override 機制與 ADR 一致即可 |
| SD | ⏳ 待實作交付 | W0 T0-2/T0-3/T0-5 同步交付，避免 CI 失守 |

---

## 8. 文件版本

| 版本 | 日期 | 內容 |
|------|------|------|
| v1.0 | 2026-05-18 | Architect 初版草擬（G0 啟動前置 DoD）|
