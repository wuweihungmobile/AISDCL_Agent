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


#: 🔴 **存量債棘輪**：`target_test_file` 尚未在磁碟上存在的 AC 條目。
#: （筆數刻意不寫在散文裡——那是會漂移的量測值，唯一量測入口是 `_pending_targets()`，
#: 由 `test_pending_targets_match_the_ratchet` 逐筆比對；沿革見下方各輪註記。）
#:
#: 判準是**等值**而非「不得增加」，理由同 `tools/lib/skip_tag_policy.py` 各棘輪：只擋
#: 一個方向的表會就地腐化（`MIN_TESTS` 腐化 11 輪是本 repo 已付過的學費）。等值判準的
#: 代價是「清掉一筆時也會紅一次」——本輪刻意接受這個代價，但把訊息寫成**逐字說出要改
#: 哪一個常數、改成什麼值**：有路可走的紅與死路一條的紅是兩件事，後者才是自鎖。
#: 🔴 R82 包 A2（DEBT-01）：4 → 3。AC2-2 已清——它的門檻逐字是
#: 「`_runner_internals.py` / `_runner_compat.py` 皆不存在」，而那兩支檔早在 SD_06 W6
#: （2026-05-18）就物理刪除了 ⇒ **受測條件多輪前就滿足，缺的只有那支斷言檔**。
#: 建 `tests/contract/test_w6_deletion.py` 即轉綠，零風險。
#:
#: 🔴 本輪（承接輪次到期的那一輪）：3 → **0**，走的是出口①「把 target 檔建起來」，
#: 不是出口②「再推一輪」。三筆各自的門檻在落地時都已經有可量測的受測對象，缺的同樣
#: 只是那支斷言檔：
#:   · AC3-4（5 run × abort 互不影響）→ `tests/integration/test_concurrent_runs.py`。
#:     受測對象＝File 後端（`storage.mode` 預設值）的併發落盤與 abort 隔離。
#:     既有的 `test_multi_run_resume_e2e.py::TestConcurrentRuns` 循序跑 InMemory 後端，
#:     **結構上**表現不出這條 AC 要防的失效（互相覆寫／abort 後讀到別人的列）。
#:   · AC5-4（≤ 2s 寫入完成）→ `tests/integration/test_sigint_checkpoint.py`。
#:     受測對象＝真實 signal handler 內的持久化寫入。既有那支量的是 InMemory 的一次
#:     dict 賦值 ⇒ 任何退化下都不可能超過 2s，那個「2s」是裝飾數字。
#:   · AC6-3（openapi == 3.1.0 + ≥ 15 欄位）→ `tests/integration/test_config_schema_api.py`。
#:     受測對象＝`ConfigResolver.openapi_schema()`（該端點的 HTTP 層尚不存在，
#:     劃界寫在該檔檔頭，刻意不包成 skip——skip 只是把同一筆欠債換個地方掛著）。
_AC_TARGET_PENDING: frozenset[str] = frozenset()

#: 上表的 **shrink-only 天花板**（同 `_POSIX_TAG_RATCHET_CEILING` 的既有慣例）。
#: 沒有它，等值判準的合法出口之一就是「把新的欠債加進上表」——鎖當場全綠，而欠債
#: 悄悄變大且看起來像在維護基線。要真的加大欠債，必須在**同一個 commit** 顯式上修
#: 本常數並在 PR 說明理由；那是一個會出現在 diff 裡、可被複審點名的決定。
#: 🔴 R82：4 → 3（跟著上表一起下修——天花板不跟著降＝把剛還掉的欠債額度留著，
#: 日後可無聲用回去；這句話是本檔 `test_pending_targets_match_the_ratchet` 自己寫的）。
#: 🔴 本輪：3 → **0**（同上，跟著上表一起下修）。天花板落到 0 之後，「新增一條指不到
#: 檔的 AC」再也沒有任何額度可以無聲吸收——那正是 shrink-only 的終點狀態。
_AC_TARGET_PENDING_CEILING = 0

#: 🔴 AC target `[DEBT]` 的**承接輪次**單一真相源（R82 包 A2／DEBT-01 立案；當時的分母是
#: 剩下那三筆欠債，今天分母是 0——見本段末的本輪註記）。
#:
#: 缺陷本體（R82 掃描實測）：那三筆的 skip reason 逐字寫著「承接輪次 R82」——而 R82
#: 就是**現在**。一個承接輪次寫著本輪的欠債，讀起來像「有人負責」，實際上沒有任何東西
#: 會在那一輪到來時說話：`_EXEMPT_HANDOVER_RE`（`R\d{2,}`）只問「有沒有寫輪號」，
#: 對「那個輪號已經過期了」結構上失明。於是它可以永遠寫著同一個數字。
#:
#: 修法是把輪號抽成常數，並由 `test_the_debt_handover_round_is_still_in_the_future`
#: 拿帳本推得的**當前輪次**去比：承接輪一旦追平當前輪，這支就紅，逼出一個顯式決定
#: （做掉它，或在 diff 裡把承接輪往後推並說明理由）。兩者都是決定，而現況兩者皆非。
#:
#: 🔴 本輪把型別放寬成 `int | None`，並把「沒有欠債時必須是 `None`」做成**判準的第二個
#: 方向**（不是豁免，見下）。理由是實測出來的：本輪走出口①把 `_AC_TARGET_PENDING`
#: 清成 0 之後，這個常數的分母消失了，而原判準是無條件比較 ⇒ 只剩兩條路：
#:   · 留一個數字在這裡 ⇒ 它管不到任何欠債，且**每一輪都會再度追平當前輪**，
#:     於是每輪都要為零欠債做一次無意義的上修——那正是本常數 WHY 裡點名的
#:     「裝飾字串」，只是換成由鎖每輪逼著人親手貼上去；
#:   · 寫 `None`＝逐字說出「今天沒有任何 AC 欠債等人承接」。
#: 後者才是真話，所以判準改成雙向：**有欠債 ⇒ 必須是還沒到的輪次（原斷言逐字保留）；
#: 沒欠債 ⇒ 必須是 `None`**。同時多守住一個此前不存在的方向：新增一筆欠債卻沒有人
#: 指定承接輪次（`None` ＋ 非空 pending）當場紅。三個方向都有紅綠自證，見該支 docstring。
_AC_DEBT_HANDOVER_ROUND: int | None = None


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
        handover = (
            f"承接輪次 R{_AC_DEBT_HANDOVER_ROUND}"
            if _AC_DEBT_HANDOVER_ROUND is not None
            else "承接輪次**尚未指定**（_AC_DEBT_HANDOVER_ROUND is None）"
        )
        pytest.skip(
            f"[DEBT] AC {ac_id}（{meta['topic']}，{meta['wave']}）的真斷言落點尚未建立："
            f"AutoClaude/{target}。門檻＝{meta['threshold']}。"
            f"{handover}（帳本 DEF-101-960；輪號由本檔常數 "
            f"_AC_DEBT_HANDOVER_ROUND 統一供給，追平當前輪或欠債無人承接即由 "
            f"test_the_debt_handover_round_is_still_in_the_future 轉紅）。"
            f"建好該檔後本 case 自動轉綠，並依 test_pending_targets_match_the_ratchet "
            f"的訊息下修 _AC_TARGET_PENDING／_AC_TARGET_PENDING_CEILING"
        )
    assert (_AC_ROOT / target).exists()


def test_the_debt_handover_round_is_still_in_the_future() -> None:
    """🔴 R82 包 A2（DEBT-01）：承接輪次不得是**已經到了**的那一輪。

    WHY（Rule 9 — 這條規則要守的不是格式，是「有沒有人真的會接手」）：
    修前三筆 `[DEBT]` 的 reason 逐字寫著「承接輪次 R82」，而 R82 就是本輪。
    既有的格式判準 `skip_tag_policy._EXEMPT_HANDOVER_RE`（`R\\d{2,}`）只問「有沒有
    寫輪號」，對「這個輪號已經到了、而且什麼都沒發生」結構上失明 ⇒ 同一個數字可以
    掛在那裡無限久，而每一輪讀到它的人都會以為下一輪有人負責。

    判準（本輪起**三個方向**，分母一律是 `_pending_targets()` 的磁碟實測，不是常數）：
      ① 有欠債 ＋ 有指定輪號 ⇒ `_AC_DEBT_HANDOVER_ROUND` 必須 **>** 帳本推得的當前輪次
         （`tools/check_defect_log_crossref.current_round()`，本 repo 對「現在是第幾輪」
         的既有唯一真相源——刻意不寫死另一個常數，那正是它在治的病）。追平的那一輪
         本支轉紅，逼出一個顯式決定：做掉它，或在 diff 裡把輪號往後推。**這一條的
         斷言逐字未動**，它就是本支被寫下來的理由。
      ② 有欠債 ＋ 輪號是 `None` ⇒ 紅。「有欠債而沒有人承接」此前結構上無人看得見
         （原判準只比大小，`None` 這個狀態根本不存在），本輪連同 ③ 一起補上。
      ③ **沒有欠債 ⇒ 輪號必須是 `None`**。這一條不是豁免而是收緊：欠債清空後，任何
         留在這裡的數字都管不到任何東西，而且會**每一輪**再度追平當前輪 ⇒ 逼著人每輪
         為零欠債做一次無意義的上修，那就是本檔一直在點名的「裝飾字串」，只是改成由
         鎖親自逼著人貼上去。寫 `None` 是唯一的真話，而 ② 保證它不會被當成後門
         （欠債一回來、沒人指定輪號就紅）。

    誠實劃界：帳本推不出輪次時（欄位改名／檔案搬走）本支 **skip 而非放行**——
    「量不到」不等於「量到合格」，但也不該在別人改帳本格式時假紅。方向 ②／③ 不需要
    帳本就判得出來，故刻意排在取帳本之前：載具壞掉時仍保有那兩個方向的鑑別力。
    """
    import sys  # noqa: PLC0415 — 只有本支需要動 sys.path

    pending = _pending_targets()
    if not pending:
        assert _AC_DEBT_HANDOVER_ROUND is None, (
            f"AC target 欠債實測為 0 筆，承接輪次卻還掛著 R{_AC_DEBT_HANDOVER_ROUND}"
            "——沒有分母的輪號管不到任何東西，且每一輪都會再度追平當前輪，"
            "於是每輪都得為零欠債做一次無意義的上修（＝本常數 WHY 點名的裝飾字串）。"
            "正解：把 _AC_DEBT_HANDOVER_ROUND 設為 None，逐字說出「今天沒有欠債等人承接」。"
            "欠債一旦回來，本支下面那個方向會要求你重新指定一個還沒到的輪次"
        )
        return

    tools_dir = _AC_ROOT.parent / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    import check_defect_log_crossref as crossref  # noqa: PLC0415

    ledger = _AC_ROOT.parent / "docs" / "06_quality" / "AutoSDD_Defect_Log.md"
    if not ledger.is_file():
        pytest.skip(f"[TOOL-ABSENCE] 缺陷帳本不存在：{ledger}——當前輪次量不到")
    now = crossref.current_round(ledger.read_text(encoding="utf-8"))
    if now is None:
        pytest.skip(
            "[TOOL-ABSENCE] 從缺陷帳本推不出當前輪次（「發現情境」欄格式已變？）"
            "——量不到 ≠ 量到合格，本支不在此情形下放行"
        )
    assert _AC_DEBT_HANDOVER_ROUND is not None, (
        f"AC target 欠債實測 {sorted(pending)} 筆，卻沒有任何人指定承接輪次"
        "（_AC_DEBT_HANDOVER_ROUND is None）——「有欠債而沒有人承接」比"
        "「承接輪次過期」更難看見：連一個會過期的數字都沒有。"
        "正解：把它設成一個**還沒到**的輪次（當前輪 R"
        f"{now}），並在同一個 commit 說明那筆欠債為什麼要留到那一輪"
    )
    assert _AC_DEBT_HANDOVER_ROUND > now, (
        f"`[DEBT]` 的承接輪次 R{_AC_DEBT_HANDOVER_ROUND} 已經追平／落後於當前輪 R{now}"
        "——承接輪次到了卻什麼都沒發生，就是「有人負責」的假象。"
        f"兩條合法出口：①把剩下的 target 檔建起來（{sorted(pending)}，"
        "門檻寫在 AC_MATRIX 的 threshold 欄）；②在同一個 commit 顯式上修 "
        "_AC_DEBT_HANDOVER_ROUND 並在 PR 說明為什麼又推遲一輪。"
        "🔴 不接受的第三條：把本支刪掉或改成不比較——那會讓輪號退回一個裝飾字串"
    )
