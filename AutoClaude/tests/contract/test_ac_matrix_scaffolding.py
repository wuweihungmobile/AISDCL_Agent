"""SD_Improving_06 AC Matrix — 每條 AC 的**真斷言落點指標**（SSOT）

對應 [SD_Improving_06.md §6.5 Acceptance Criteria Matrix](
    ../../docs/04_planning/SD_Improving_06.md#65-acceptance-criteria-matrix
)（QA-C1 補強，每條可量測）。

本檔的職責（本輪重寫；WHY 見下方〈自鎖型技術債〉）：
    - 每條 AC 登記 ID / 議題 / Pass 門檻 / 啟動 Wave / **真斷言住在哪個檔**
    - 真斷言**不住這裡**——它住 `target_test_file` 所指的那個檔（測試檔，或
      `.importlinter` 這種以契約形式落地的量測點）
    - 本檔負責的是**指標完整性**：那個檔今天還在不在

紅線：AC Matrix 一條都不能漏；條目數由 `test_ac_matrix_has_25_entries` 鎖死。

──────────────────────────────────────────────────────────────────────
自鎖型技術債的拆解（本輪；R76 §2.2 點名、`DEF-101-856` 第 ⑤ 項承接）
──────────────────────────────────────────────────────────────────────
本檔此前把「佔位」與「未實作」綁成同一件事：29 個 case 全部掛無條件
`pytest.mark.skip`，而函式體是 `pytest.fail(...)`。三個後果環環相扣：

  1. 想清這筆債的人（把 skip 拿掉）**第一步就吃一個紅**，而那個紅不告訴他
     下一步該做什麼 ⇒ 債會自我保存（制度在懲罰誠實）。
  2. skip reason 說「開工時將 skip 移除」、docstring 第 3 條說「仍保留 skip
     以維 SSOT」——**兩句話互斥**，讀者無從判斷哪幾條是真的還沒做。
  3. 整檔唯一真的會執行的斷言是「條目數 == 29」，而它比對的是同檔上方那個
     字面 dict ⇒ 恆真。29 個 case 的鑑別力合計為零。

本輪的形態（三件事各歸各位）：
  · **佔位不再是無條件 skip**：target 檔存在 ⇒ 斷言它存在並**通過**（指標活著）；
    target 檔尚未建立 ⇒ `pytest.skip()`，reason 內寫得出「誰該建它、建在哪」。
    這讓「哪幾條是真的沒做」變成 skip 明細裡看得見的東西，而不是全部 29 條一起黑。
  · **存量債進棘輪**：`_AC_TARGET_PENDING` 是等值判準 ＋ shrink-only 天花板
    （同 `tools/lib/skip_tag_policy.py` 兩張棘輪的既有慣例）。清掉一筆時仍會紅一次，
    但那個紅**逐字說出要改哪一個常數、改成什麼值** ⇒ 是有路可走的紅，不是死路。
  · **`pytest.fail` 只留給真的該紅的情形**：本檔現在一處都不用它——「還沒做」的
    正確顏色是 skip（帶得出承接資訊），不是 fail。
"""
from __future__ import annotations

from pathlib import Path

import pytest

#: `AutoClaude/`——`target_test_file` 的解析基準（本檔住 `AutoClaude/tests/contract/`）。
_AC_ROOT = Path(__file__).resolve().parents[2]

# AC ID → (議題, 量測命令, Pass 門檻, 對應測試檔, 啟動 Wave)
#
# `target_test_file` 的契約（本輪收緊）：必須是**單一、可解析**的 repo 相對路徑
# （相對 `AutoClaude/`）。此前有兩筆把「契約檔 ＋ 測試檔」混寫成一個欄位
# （中間夾空白或斜線），於是那兩筆對任何路徑判準都解析不到——看起來有指標、
# 實際上指不到任何東西。混寫的那一半已移進 `threshold` 欄（它本來就是描述用的）。
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
        "target_test_file": "tests/contract/test_brain_executor_isolation.py",
        "threshold": "brain-executor-isolation contract kept（該測試跑 .importlinter 契約）",
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
        "target_test_file": ".importlinter",
        "threshold": "runner-no-checkpoint-logic 契約：_save_.*_checkpoint 在 "
                     "_runner_internals.py 為 0",
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


#: 🔴 **存量債棘輪**：`target_test_file` 尚未在磁碟上存在的 AC 條目（本輪實測 4 筆）。
#:
#: 判準是**等值**而非「不得增加」，理由同 `tools/lib/skip_tag_policy.py` 各棘輪：只擋
#: 一個方向的表會就地腐化（`MIN_TESTS` 腐化 11 輪是本 repo 已付過的學費）。等值判準的
#: 代價是「清掉一筆時也會紅一次」——本輪刻意接受這個代價，但把訊息寫成**逐字說出要改
#: 哪一個常數、改成什麼值**：有路可走的紅與死路一條的紅是兩件事，後者才是自鎖。
_AC_TARGET_PENDING: frozenset[str] = frozenset({
    "AC2-2",   # tests/contract/test_w6_deletion.py        — W6 尚未開工
    "AC3-4",   # tests/integration/test_concurrent_runs.py — W3 多 run 並存
    "AC5-4",   # tests/integration/test_sigint_checkpoint.py
    "AC6-3",   # tests/integration/test_config_schema_api.py
})

#: 上表的 **shrink-only 天花板**（同 `_POSIX_TAG_RATCHET_CEILING` 的既有慣例）。
#: 沒有它，等值判準的合法出口之一就是「把新的欠債加進上表」——鎖當場全綠，而欠債
#: 悄悄變大且看起來像在維護基線。要真的加大欠債，必須在**同一個 commit** 顯式上修
#: 本常數並在 PR 說明理由；那是一個會出現在 diff 裡、可被複審點名的決定。
_AC_TARGET_PENDING_CEILING = 4


def _pending_targets() -> set[str]:
    """實測：`target_test_file` 在磁碟上**不存在**的 AC 條目（純函式，只讀檔案系統）。"""
    return {
        ac_id for ac_id, meta in AC_MATRIX.items()
        if not (_AC_ROOT / meta["target_test_file"]).exists()
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


def test_pending_targets_match_the_ratchet() -> None:
    """存量債棘輪：磁碟實況必須與 `_AC_TARGET_PENDING` 逐筆相等（雙向都說話）。

    WHY（Rule 9，測意圖非僅行為）：這支才是「AC Matrix 有幾條真的還沒做」的唯一
    量測入口。少了它，`_AC_TARGET_PENDING` 會變成一張只進不出的名單——有人補了
    target 檔卻沒下修，鑑別力靜默歸零；有人新增一條指不到檔的 AC，也沒有任何東西
    會說話。兩個方向的失敗訊息都必須寫出「改哪一個常數、改成什麼」，否則這支自己
    就變成下一個自鎖點。
    """
    assert _AC_TARGET_PENDING <= frozenset(AC_MATRIX), (
        f"棘輪列了不存在的 AC ID：{sorted(_AC_TARGET_PENDING - frozenset(AC_MATRIX))}"
    )
    assert len(_AC_TARGET_PENDING) <= _AC_TARGET_PENDING_CEILING, (
        f"_AC_TARGET_PENDING 有 {len(_AC_TARGET_PENDING)} 筆、超過 shrink-only 天花板 "
        f"{_AC_TARGET_PENDING_CEILING}——欠債只准變少。真的要加大，"
        f"請在同一個 commit 顯式上修 _AC_TARGET_PENDING_CEILING 並在 PR 說明理由"
    )
    actual = _pending_targets()
    if actual == set(_AC_TARGET_PENDING):
        return
    cleared = sorted(set(_AC_TARGET_PENDING) - actual)
    added = sorted(actual - set(_AC_TARGET_PENDING))
    fix = []
    if cleared:
        fix.append(
            f"已補上 target 檔：{cleared} ⇒ 請把它們自 _AC_TARGET_PENDING 移除，"
            f"並把 _AC_TARGET_PENDING_CEILING 一起下修為 {len(actual)}"
            f"（天花板不跟著下修＝把剛還掉的欠債額度留著，日後可無聲用回去）"
        )
    if added:
        fix.append(
            f"新增了指不到檔的 AC：{added} ⇒ 正解是把 target 檔建起來；"
            f"真的要記成欠債，必須同時上修 _AC_TARGET_PENDING_CEILING（見該常數 WHY）"
        )
    raise AssertionError(
        f"AC target 指標實測 {sorted(actual)}／棘輪 {sorted(_AC_TARGET_PENDING)}。" + "；".join(fix)
    )


@pytest.mark.parametrize(
    "ac_id,meta",
    list(AC_MATRIX.items()),
    ids=list(AC_MATRIX.keys()),
)
def test_ac_scaffolding_placeholder(ac_id: str, meta: dict[str, str]) -> None:
    """每條 AC 的**指標完整性**：真斷言住 `target_test_file`，本 case 只驗它還在。

    兩種顏色，各自有明確語意：
      · **passed** ＝ 指標解析得到（那個 Wave 的真斷言有落點）。刪掉／改名該檔會
        當場紅——這是本檔在本輪之前完全不存在的鑑別力。
      · **skipped** ＝ 該 AC 的 target 檔尚未建立。reason 內寫得出「該建哪個檔、
        屬哪個 Wave」，所以 skip 明細本身就是那份 backlog，不需要另外一本。
    """
    target = meta["target_test_file"]
    if not (_AC_ROOT / target).exists():
        pytest.skip(
            f"[DEBT] AC {ac_id}（{meta['topic']}，{meta['wave']}）的真斷言落點尚未建立："
            f"AutoClaude/{target}。門檻＝{meta['threshold']}。承接輪次 R82。"
            f"建好該檔後本 case 自動轉綠，並依 test_pending_targets_match_the_ratchet "
            f"的訊息下修 _AC_TARGET_PENDING／_AC_TARGET_PENDING_CEILING"
        )
    assert (_AC_ROOT / target).exists()
