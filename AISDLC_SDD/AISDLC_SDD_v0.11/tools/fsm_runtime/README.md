# FSM Runtime（Phase D ACT-010）

將 `SDD_FSM_ENGINE.md` 的狀態機定義升級為可執行引擎，供 `.claude/hooks/` 調用。

## 安裝

```bash
pip install pyyaml
```

## CLI 用法

```bash
# 顯示當前狀態
python -m tools.fsm_runtime.fsm_runtime show

# 記錄閘門結果
python -m tools.fsm_runtime.fsm_runtime gate --gate SCG_VALIDATION --result FAIL --reason "AC-003-1 模糊"

# Reconcile CI-EVENT
python -m tools.fsm_runtime.fsm_runtime reconcile

# 狀態強制轉換（僅用於恢復）
python -m tools.fsm_runtime.fsm_runtime transition --to SPEC_DRAFTING

# 記錄 SPEC_FROZEN
python -m tools.fsm_runtime.fsm_runtime spec-frozen --stage Stage-2 --doc docs/01_requirements/FRD-X.md

# 檢查 IMPLEMENTATION budget
python -m tools.fsm_runtime.fsm_runtime check-impl
```

## Python API

```python
from tools.fsm_runtime import FSMRuntime

runtime = FSMRuntime.bootstrap()  # 從 $SDD_PROJECT 讀 project 名
runtime.assert_tool_allowed("Write", "docs/01_requirements/FRD-X.md")
runtime.record_gate_result("SCG_VALIDATION", "FAIL", reason="SLV-002")
runtime.reconcile_ci_events()
```

## 測試

```bash
python -m unittest tools.fsm_runtime.tests.test_transitions
```

## 檔案結構

- `state_loader.py` — 讀寫 `FSM-STATE-{project}.yaml`（含 atomic write + .bak）
- `transition_rules.py` — 轉換規則與 retry 上限（與 `SDD_FSM_ENGINE.md` 同步）
- `event_reconciler.py` — 消費 `CI-EVENT-*.yaml`
- `fsm_runtime.py` — Facade 與 CLI
- `tests/test_transitions.py` — 覆蓋所有 happy-path + error-path 轉換

## 與 SDD_FSM_ENGINE.md 同步驗證

`tests/test_sync.py` 會 parse 文件中的「狀態轉換表」section，驗證 Python 規則與文件一致。
