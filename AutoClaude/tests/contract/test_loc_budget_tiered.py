"""LOC budget tiered policy contract tests — SD_07 W0 T0-5.

ADR-SD07-001 v1.0 §4.2 / §5 / §6：驗證分級制 budget 表生效、絕對紅線 750
不可突破、override 機制可控管。
"""
from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

clb = importlib.import_module("tools.check_loc_budget")


# ── 分級表結構驗證 ───────────────────────────────────────────


def test_loc_tiers_table_matches_adr_sd07_001():
    """ADR-SD07-001 §4.2 表格七層：data / plugin_entry / strategy /
    adapter / contract / service + absolute_limit。"""
    expected = {
        "data": 150,
        "plugin_entry": 250,
        "strategy": 300,
        "adapter": 400,
        "contract": 400,
        "service": 500,
    }
    for tier, budget in expected.items():
        assert tier in clb.LOC_TIERS, f"tier '{tier}' missing"
        assert clb.LOC_TIERS[tier]["budget"] == budget, (
            f"tier '{tier}' budget should be {budget}"
        )
    assert clb.ABSOLUTE_LIMIT == 750


# ── 分級判定（classify_file）─────────────────────────────────


@pytest.mark.parametrize(
    "rel_path,expected_tier,expected_budget",
    [
        ("autoclaude/models/playbook.py", "data", 150),
        ("autoclaude/core/ports/brain.py", "data", 150),
        ("autoclaude/plugins/notification_plugin.py", "plugin_entry", 250),
        ("autoclaude/plugins/checkpoint/plugin.py", "plugin_entry", 250),
        ("autoclaude/core/services/mutation/revise_current.py", "strategy", 300),
        ("autoclaude/infra/adapters/minimax_brain.py", "adapter", 400),
        ("autoclaude/infra/repositories/pg_state_repository.py", "adapter", 400),
        ("autoclaude/core/hookspec.py", "contract", 400),
        ("autoclaude/core/wiring.py", "contract", 400),
        ("autoclaude/execution/types.py", "contract", 400),
        ("autoclaude/core/services/auto_resume.py", "service", 500),
        ("autoclaude/execution/playbook_runner.py", "service", 500),
        ("autoclaude/execution/steps_orchestrator/_impl.py", "service", 500),
    ],
)
def test_classify_file_matches_tier(rel_path, expected_tier, expected_budget):
    tier, budget = clb.classify_file(Path(rel_path))
    assert tier == expected_tier, f"{rel_path} should be tier '{expected_tier}', got '{tier}'"
    assert budget == expected_budget


def test_unclassified_file_defaults_to_absolute_limit():
    """未匹配任何 tier 的檔案以 absolute_limit (750) 為預設 budget。"""
    tier, budget = clb.classify_file(Path("autoclaude/some_new_subsystem/foo.py"))
    assert tier == "unclassified"
    assert budget == clb.ABSOLUTE_LIMIT


# ── 各分級邊界（≥ 6 case 對齊執行指南 G0 驗證）──────────────


def test_data_tier_budget_enforced():
    assert clb.LOC_TIERS["data"]["budget"] == 150


def test_plugin_entry_tier_budget_enforced():
    """Plugin 公開 API ≤ 250；SD_06 W3 落地 12/12 plugin 全合規。"""
    assert clb.LOC_TIERS["plugin_entry"]["budget"] == 250


def test_strategy_tier_budget_enforced():
    assert clb.LOC_TIERS["strategy"]["budget"] == 300


def test_adapter_tier_budget_enforced():
    assert clb.LOC_TIERS["adapter"]["budget"] == 400


def test_contract_tier_budget_enforced():
    assert clb.LOC_TIERS["contract"]["budget"] == 400


def test_service_tier_budget_enforced():
    assert clb.LOC_TIERS["service"]["budget"] == 500


def test_absolute_limit_750_enforced():
    """ADR §4.2 #7 全域絕對紅線。"""
    assert clb.ABSOLUTE_LIMIT == 750


# ── override 機制 ────────────────────────────────────────────


def test_override_file_loads_when_present():
    """`.loc-budget.toml` 存在時可被解析。"""
    overrides = clb.load_overrides()
    assert isinstance(overrides, dict)
    # 規劃階段已豁免 prompt_builder.py（純函式集中）
    assert "autoclaude/decision/prompt_builder.py" in overrides
    entry = overrides["autoclaude/decision/prompt_builder.py"]
    assert entry["tier"] == "service"
    assert "reason" in entry and len(entry["reason"]) > 0


def test_override_applied_in_build_reports():
    """override 應將檔案 tier 與 budget 升級至指定層級。"""
    overrides = clb.load_overrides()
    reports = clb.build_reports(overrides)
    pb = next(
        r for r in reports if r.rel_path == "autoclaude/decision/prompt_builder.py"
    )
    assert pb.tier == "service"
    assert pb.budget == 500
    assert pb.override_reason is not None


# ── 絕對紅線真實掃描 ────────────────────────────────────────


def test_no_file_exceeds_absolute_limit_750():
    """任何層級不得超 750 LOC（紅線 ❌14 + ❌16 防 god-class 復活）。"""
    overrides = clb.load_overrides()
    reports = clb.build_reports(overrides)
    over = [r for r in reports if r.loc > clb.ABSOLUTE_LIMIT]
    assert not over, (
        "absolute red line breach (> 750 LOC):\n"
        + "\n".join(f"  {r.rel_path}: {r.loc}" for r in over)
    )


# ── 政策版本標記 ────────────────────────────────────────────


def test_policy_version_marker_present_in_env_example():
    """`.env.example` 必含 LOC_BUDGET_POLICY_VERSION=v2 以追蹤政策落地版本。"""
    env_path = PROJECT_ROOT / ".env.example"
    text = env_path.read_text(encoding="utf-8")
    assert "LOC_BUDGET_POLICY_VERSION=v2" in text


# ── 總量 cap 預警帶（ADR-SD07-001 §6.3 觸發條件 ②）───────────
#
# R56 round 5 修正：同輪新增的 TOTAL_WARN_MARGIN / total_warn_band 當時零測試覆蓋，
# 且常數 10 與 ADR §6.3 正文的「cap − 10」是兩處硬編、僅靠 ADR 那句「須與本節同步」
# 的人工宣稱維繫。四方複核判此與本輪 [B]「凡兩份硬編實作互稱鏡射，本 repo 一律建鎖」
# 同形（且該訊號存在的理由正是「把 §6.3 觸發條件 ② 從人眼改為機械」，它自己卻沒有
# 機械保護），故補下列三支鎖：SSOT 對齊、邊界＋rc 不變性、JSON/文字兩模式一致。

_ADR_LOC_POLICY = PROJECT_ROOT / "docs" / "04_planning" / "ADR" / "ADR-SD07-001-loc-policy.md"


def test_total_warn_margin_matches_adr_sd07_001_section_6_3():
    """`TOTAL_WARN_MARGIN` 必須等於 ADR §6.3 觸發條件 ② 的 `cap − N`。

    刻意**從 ADR 正文以正則抽數字**而非再寫死一份 expected —— 後者只會變成第三個
    硬編站點（正是本測試要消滅的形狀）。同時鎖住 §6.3 內覆述那句「＝上式的 N」，
    使該句自稱的同步義務本身也有機械保證：任一站點被單獨改動即翻紅。
    形狀比照同檔 test_loc_tiers_table_matches_adr_sd07_001 的常數釘選慣例。
    """
    text = _ADR_LOC_POLICY.read_text(encoding="utf-8")

    trigger = re.findall(r"total\s*≥\s*cap\s*−\s*(\d+)", text)
    assert len(trigger) == 1, (
        f"ADR §6.3 觸發條件 ② 的 `total ≥ cap − N` 應恰好一處（本鎖賴其唯一性），實得 {trigger}"
    )
    assert int(trigger[0]) == clb.TOTAL_WARN_MARGIN, (
        f"ADR §6.3 觸發條件 ② 寫 cap − {trigger[0]}，但 "
        f"check_loc_budget.TOTAL_WARN_MARGIN = {clb.TOTAL_WARN_MARGIN}；兩站點必須一致"
    )

    restated = re.findall(r"＝上式的\s*(\d+)", text)
    assert len(restated) == 1, (
        f"ADR §6.3 覆述句「（＝上式的 N…）」應恰好一處，實得 {restated}"
    )
    assert int(restated[0]) == clb.TOTAL_WARN_MARGIN, (
        f"ADR §6.3 覆述句寫「＝上式的 {restated[0]}」，與 TOTAL_WARN_MARGIN "
        f"= {clb.TOTAL_WARN_MARGIN} 不符"
    )


@pytest.fixture
def frozen_cap(monkeypatch):
    """回傳 `set_cap(cap)`：把總量 cap 固定為指定值，且**絕不觸碰 .loc_baseline**。

    做法是讓 read_baseline 直接回傳目標 cap，並把 TOTAL_INCREASE_LIMIT 暫設 1.0
    （`cap = int(baseline × limit)`）。**刻意不採**「反推一個 baseline 使
    `int(baseline × 1.20) == 目標 cap`」——1.20 的步進讓約 1/6 的整數 cap 根本無解
    （實測 cap=20363／20369／20375 皆無 baseline 可達），而目標 cap 是由真實 total
    位移而來、會隨程式碼演進漂移，總有一天湊不出來而**假紅**。
    write_baseline 一併換成會炸的 stub，讓「測試不得改寫 repo 的 baseline 檔」
    這條前提也是機械保證，而非撰寫者自律。
    """

    def _boom(value: int) -> None:  # pragma: no cover - 觸發即代表測試設計錯誤
        raise AssertionError(f"本測試不得寫入 .loc_baseline（嘗試寫入 {value}）")

    monkeypatch.setattr(clb, "write_baseline", _boom)
    monkeypatch.setattr(clb, "TOTAL_INCREASE_LIMIT", 1.0)

    def set_cap(cap: int) -> None:
        monkeypatch.setattr(clb, "read_baseline", lambda: cap)

    return set_cap


def _real_total() -> int:
    return sum(r.loc for r in clb.build_reports(clb.load_overrides()))


@pytest.mark.parametrize(
    "cap_offset,expect_warn,expect_rc",
    [
        # cap = total + margin + 1 → 餘裕比預警帶多 1 行，仍在帶外
        (clb.TOTAL_WARN_MARGIN + 1, False, 0),
        # cap = total + margin → total == cap − margin，`>=` 的下緣必須亮
        (clb.TOTAL_WARN_MARGIN, True, 0),
        # cap == total → 貼齊但未破線（R53 實際發生過的狀態）
        (0, True, 0),
        # cap = total − 1 → 破線，改由 [TOTAL] 阻塞訊息接手，不得同時印 [WARN]
        (-1, False, 1),
    ],
)
def test_warn_band_boundary_and_rc_invariant(
    cap_offset, expect_warn, expect_rc, capsys, frozen_cap
):
    """預警帶的四態邊界，以及「WARN 非阻塞 → rc 不得改變」這條不變式。

    WHY：這個訊號的唯一用途是把 ADR §6.3 觸發條件 ② 從人眼改為機械。若日後有人
    (a) 把 `>=` 改成 `>`（下緣靜默失效）、(b) 刪掉 WARN 分支、或 (c) 把
    total_warn_band 併進 has_violation（預警帶變成硬阻塞，CI 無故翻紅），
    在沒有本測試時 pytest 全綠、rc 不變、零訊號。
    """
    total = _real_total()
    frozen_cap(total + cap_offset)

    rc = clb.check()
    out = capsys.readouterr().out

    assert ("[WARN]" in out) is expect_warn, (
        f"cap = total{cap_offset:+d} 時 [WARN] 應{'出現' if expect_warn else '不出現'}；"
        f"實際輸出：\n{out}"
    )
    assert ("[TOTAL]" in out) is (expect_rc == 1), (
        f"cap = total{cap_offset:+d} 時 [TOTAL] 應{'出現' if expect_rc == 1 else '不出現'}；"
        f"實際輸出：\n{out}"
    )
    assert rc == expect_rc, (
        f"cap = total{cap_offset:+d} 時 rc 應為 {expect_rc}（預警帶必須非阻塞）；"
        f"實得 {rc}。若非破線態卻得 rc=1，請先確認 repo 是否另有 tier/absolute/special 違規"
    )


@pytest.mark.parametrize(
    "cap_offset,expect_warn,expect_violation",
    [
        (clb.TOTAL_WARN_MARGIN, True, False),
        (-1, False, True),
    ],
)
def test_warn_band_json_payload_matches_text_mode(
    cap_offset, expect_warn, expect_violation, capsys, frozen_cap
):
    """--json 報表的 total_warn_band / total_warn_margin 必須與文字模式一致。

    WHY：ADR §6.3「必要證據」指定 `--json` 報表，走正規 baseline 校準程序的人
    只看 JSON；若哪天 JSON 欄位被漏改或漏出，該程序的人就看不到觸發條件 ②。
    本測試**真的把同一 cap 下的兩種輸出對跑並互比**（而非各自對著寫死的期望值斷言）
    —— 後者會讓方法名「matches_text_mode」名實不符，正是本輪 [E] 的失效形狀。
    """
    total = _real_total()
    frozen_cap(total + cap_offset)

    rc_text = clb.check()
    text_out = capsys.readouterr().out
    rc_json = clb.check(as_json=True)
    payload = json.loads(capsys.readouterr().out)

    assert payload["total_warn_band"] is ("[WARN]" in text_out), (
        f"--json 的 total_warn_band={payload['total_warn_band']} 與文字模式不一致；"
        f"文字輸出：\n{text_out}"
    )
    assert payload["total_violation"] is ("[TOTAL]" in text_out)
    assert rc_json == rc_text

    assert payload["total_warn_band"] is expect_warn
    assert payload["total_violation"] is expect_violation
    assert payload["total_warn_margin"] == clb.TOTAL_WARN_MARGIN
    assert rc_json == (1 if expect_violation else 0)
