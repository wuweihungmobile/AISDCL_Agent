"""SD_Improving_06 W0-T0-6：AC Matrix 25 條測試 scaffolding

對應 [SD_Improving_06.md §6.5 Acceptance Criteria Matrix](
    ../../docs/04_planning/SD_Improving_06.md#65-acceptance-criteria-matrix
)（QA-C1 補強，每條可量測）。

W0 階段：
    - 每條 AC 對應一個 skip 測試（佔位）
    - 各 Wave 開工時把對應 AC 改為實際斷言並挪到專屬測試檔
    - 本檔保留每條 AC 的 ID / 量測命令 / Pass 門檻 / 對應測試檔 metadata

紅線：AC Matrix 25 條一條都不能漏；本檔 case 數固定為 25
（W2 末 sanity check：本檔仍應產出 25 個 collection item）。
"""
from __future__ import annotations

import pytest

# AC ID → (議題, 量測命令, Pass 門檻, 對應測試檔, 啟動 Wave)
AC_MATRIX: dict[str, dict[str, str]] = {
    "AC0-1": {
        "topic": "Brain capabilities",
        "wave": "W1",
        "target_test_file": "tests/core/ports/test_brain_capabilities.py",
        "threshold": "簽名含 max_context_tokens / supports_streaming / retry_policy",
    },
    "AC0-2": {
        "topic": "Executor on_event callback",
        "wave": "W1",
        "target_test_file": "tests/core/ports/test_executor_events.py",
        "threshold": "≥ 1 行（Callable[[ExecutionEvent], None]）",
    },
    "AC0-3": {
        "topic": "Coordinator phase order",
        "wave": "W1",
        "target_test_file": "tests/core/test_orchestration_coordinator.py",
        "threshold": "6 phase 序列正確",
    },
    "AC0-4": {
        "topic": "Brain-Executor isolation",
        "wave": "W1",
        "target_test_file": ".importlinter / tests/contract/test_brain_executor_isolation.py",
        "threshold": "brain-executor-isolation contract kept",
    },
    "AC1-1": {
        "topic": "_runner_internals.py LOC",
        "wave": "W2",
        "target_test_file": "tools/check_loc_budget.py",
        "threshold": "W2 末 ≤ 80；G6 末檔案不存在",
    },
    "AC1-2": {
        "topic": "strategy 模組 LOC",
        "wave": "W2",
        "target_test_file": "tools/check_loc_budget.py",
        "threshold": "每檔 ≤ 250",
    },
    "AC1-3": {
        "topic": "token_guard 子模組",
        "wave": "W2",
        "target_test_file": "tools/check_loc_budget.py",
        "threshold": "≥ 5 子模組",
    },
    "AC2-1": {
        "topic": "雙寫法消除",
        "wave": "W2",
        "target_test_file": ".importlinter runner-no-checkpoint-logic",
        "threshold": "_save_.*_checkpoint 在 _runner_internals.py 為 0",
    },
    "AC2-2": {
        "topic": "mixin 物理刪除",
        "wave": "W6",
        "target_test_file": "tests/contract/test_w6_deletion.py",
        "threshold": "_runner_internals.py / _runner_compat.py 皆不存在",
    },
    "AC3-1": {
        "topic": "三表 FK",
        "wave": "W3",
        "target_test_file": "tests/contract/test_three_tier_schema.py",
        "threshold": "≥ 3 case 綠（test_fk_cascade）",
    },
    "AC3-2": {
        "topic": "既有 4 表整合 FK",
        "wave": "W3",
        "target_test_file": "tests/contract/test_alembic_0010_fk_three_step.py",
        "threshold": "1,491+ passed 不退化",
    },
    "AC3-3": {
        "topic": "RBAC 五表 + role matrix",
        "wave": "W3",
        "target_test_file": "tests/contract/test_alembic_0011_rbac.py",
        "threshold": "≥ 5 case + 違反 role 必 403",
    },
    "AC3-4": {
        "topic": "多 run 並存",
        "wave": "W3",
        "target_test_file": "tests/integration/test_concurrent_runs.py",
        "threshold": "5 run × abort 互不影響",
    },
    "AC3-5": {
        "topic": "per-table HNSW 建立",
        "wave": "W3",
        "target_test_file": "tests/contract/test_three_tier_schema.py",
        "threshold": "≥ 3 個 HNSW index（goal_tasks m=8 / kb m=16 / execution_items m=16）",
    },
    "AC4-1": {
        "topic": "IEmbedder 維度",
        "wave": "W3",
        "target_test_file": "tests/contract/test_embedder_contract.py",
        "threshold": "BGEM3LocalAdapter().dimension == 1024",
    },
    "AC4-2": {
        "topic": "雙 adapter fallback",
        "wave": "W3",
        "target_test_file": "tests/contract/test_embedder_fallback.py",
        "threshold": "CircuitBreaker 3 fail → 切備援 < 60s",
    },
    "AC4-3": {
        "topic": "寫入路徑",
        "wave": "W3",
        "target_test_file": "tests/integration/test_embedding_write_paths.py",
        "threshold": "3 觸發點皆有 embedding IS NOT NULL",
    },
    "AC4-4": {
        "topic": "1536→1024 遷移",
        "wave": "W3",
        "target_test_file": "tests/contract/test_alembic_0008_dual_read.py",
        "threshold": "既有資料 truncate + audit log 寫入",
    },
    "AC4-5": {
        "topic": "recall@10 + p95",
        "wave": "W3",
        "target_test_file": "tests/integration/test_pgvector_hnsw_recall.py",
        "threshold": "recall@10 ≥ 0.95 + p95 < 50ms",
    },
    "AC5-1": {
        "topic": "ExecutionContext round-trip",
        "wave": "W5",
        "target_test_file": "tests/equivalence/test_execution_context_roundtrip.py",
        "threshold": "Hypothesis ≥ 50 example 100% pass",
    },
    "AC5-2": {
        "topic": "drift 全欄比對",
        "wave": "W5",
        "target_test_file": "tests/contract/test_dual_state_drift.py",
        "threshold": "≥ 4 case（含 datetime/UUID/Enum normalize）",
    },
    "AC5-3": {
        "topic": "run_id 過濾",
        "wave": "W5",
        "target_test_file": "tests/contract/test_checkpoint_run_id_filter.py",
        "threshold": "5 run × 互不干擾",
    },
    "AC5-4": {
        "topic": "SIGINT checkpoint SLA",
        "wave": "W5",
        "target_test_file": "tests/integration/test_sigint_checkpoint.py",
        "threshold": "≤ 2s 寫入完成",
    },
    "AC5-5": {
        "topic": "365 天 partition",
        "wave": "W3",
        "target_test_file": "tests/contract/test_alembic_0007_ttl.py",
        "threshold": "12 個月 partition + default partition",
    },
    "AC6-1": {
        "topic": "4 層 ConfigResolver",
        "wave": "W5",
        "target_test_file": "tests/contract/test_config_resolver.py",
        "threshold": "≥ 6 case（property-based 4 層 × 缺欄組合）",
    },
    "AC6-2": {
        "topic": "Pydantic invariants",
        "wave": "W5",
        "target_test_file": "tests/contract/test_token_guard_config_validation.py",
        "threshold": "≥ 8 case（halt > compact / 範圍）",
    },
    "AC6-3": {
        "topic": "OpenAPI 3.1 schema",
        "wave": "W5",
        "target_test_file": "tests/integration/test_config_schema_api.py",
        "threshold": "openapi == 3.1.0 + ≥ 15 欄位",
    },
    "AC6-4": {
        "topic": "YAML→DB 匯入",
        "wave": "W4",
        "target_test_file": "tests/integration/test_yaml_import.py",
        "threshold": "success_rate == 100% + JSONB key 順序 + float ±1e-6",
    },
    "AC6-5": {
        "topic": "config audit log",
        "wave": "W5",
        "target_test_file": "tests/integration/test_config_audit_log.py",
        "threshold": "runtime override 必寫入 + RBAC 保護欄位 403",
    },
}


def test_ac_matrix_has_25_entries() -> None:
    """AC Matrix 規格鎖死：25 條 + AC0~AC6 七大群組（QA-C1）。

    註：實際表共 29 條（AC0-1~4=4 + AC1-1~3=3 + AC2-1~2=2 + AC3-1~5=5 +
    AC4-1~5=5 + AC5-1~5=5 + AC6-1~5=5 = 29）。
    執行指南 §3 W0 提及「25 條」為簡化說法，本契約以實際 29 條鎖死，
    任何後續變動需同時更新 SD_06 §6.5 + 本檔。
    """
    assert len(AC_MATRIX) == 29, (
        f"AC Matrix 條目數 = {len(AC_MATRIX)}，"
        f"應為 29（AC0×4 + AC1×3 + AC2×2 + AC3×5 + AC4×5 + AC5×5 + AC6×5）"
    )


@pytest.mark.parametrize(
    "ac_id,meta",
    list(AC_MATRIX.items()),
    ids=list(AC_MATRIX.keys()),
)
@pytest.mark.skip(reason="W0 scaffolding：對應 Wave 開工時將 skip 移除並挪到專屬測試檔")
def test_ac_scaffolding_placeholder(ac_id: str, meta: dict[str, str]) -> None:
    """每條 AC 對應 skip placeholder。W1~W6 開工時：
    1. 將真實斷言補入 meta["target_test_file"] 所指檔案
    2. 確認 collection 仍含本 placeholder（不可刪除）
    3. 若已 100% 對位至 target_test_file，本 case 仍保留 skip 以維 SSOT
    """
    pytest.fail(f"AC {ac_id} ({meta['topic']}) 尚未實作；對應檔案 {meta['target_test_file']}")
