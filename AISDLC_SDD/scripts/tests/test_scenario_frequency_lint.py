"""Agent scenario_usage frequency SSOT 一致性 lint 意圖鎖（DEF-AGTREV-015）.

每個 case 編碼「為何此行為重要」（Rule 9）：本 lint 的價值＝讓「agent 的
frequency 分子與權威統計段 SSOT 漂移、或與自列場景數內部矛盾」這件事被機械擋下
——第四輪重審揭露 6 個 agent 系統性 off-by-one + integration「1/10 vs 自列 4」內部矛盾，
全因無此守門。故覆蓋：
  (1) 分子=統計段=清單數三者一致 → 0；
  (2) 分子 ≠ 統計段 SSOT → 非零（跨源漂移）；
  (3) 分子 ≠ 自列場景數 → 非零（內部矛盾，重現 integration 1/10 vs 4）；
  (4) 統計段未列之 agent 僅受內部一致約束、不受 SSOT 約束 → 一致即 0；
  (5) runtime agent（無 scenario_usage）豁免 → 0；
  (6) 突變實證：先一致（0）再改壞分子即轉紅。
任一退化都會讓 frequency 漂移/內部矛盾死灰復燃。
"""
from __future__ import annotations

import os

import yaml

from scripts import scenario_frequency_lint as sfl

_VER = "AISDLC_SDD_v0.18"


def _write_mapping(repo: str, stats: dict[str, int], ver: str = _VER) -> None:
    """寫最小 SCENARIO_AGENT_MAPPING.md，含頻率統計段（SSOT 來源）。"""
    base = os.path.join(repo, ver, "scenarios")
    os.makedirs(base, exist_ok=True)
    lines = ["# mapping", "", "## 📊 Agent 使用頻率統計（SDD 版）", "", "```yaml"]
    for k, v in stats.items():
        lines.append(f"{k}:  {v}/10（測試）")
    lines += ["```", "", "### SDD Skills 使用對應", "```yaml", "sdd-gate: 所有情境", "```"]
    with open(os.path.join(base, "SCENARIO_AGENT_MAPPING.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _scn(*names: str) -> list[dict]:
    return [{"scenario": n, "role": "x"} for n in names]


def _write_agent(repo: str, fname: str, num: int, primary: list[str],
                 supporting: list[str], ver: str = _VER, where: str = "core") -> None:
    base = os.path.join(repo, ver, "agent", where)
    os.makedirs(base, exist_ok=True)
    su = {"frequency": f"Medium ({num}/10 scenarios)", "primary_scenarios": _scn(*primary)}
    if supporting:
        su["supporting_scenarios"] = _scn(*supporting)
    doc = {"agent": {"id": fname.replace("-zh.yaml", "")}, "scenario_usage": su}
    with open(os.path.join(base, fname), "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True)


# ── (1) 三者一致 → 0 ─────────────────────────────────────────────────────────

def test_all_consistent_passes(tmp_path):
    repo = str(tmp_path)
    _write_mapping(repo, {"sd-architect": 2})
    _write_agent(repo, "sd-architect-zh.yaml", 2, ["Greenfield"], ["Migration"])
    assert sfl.main([repo]) == 0


# ── (2) 分子 ≠ 統計段 SSOT → 非零 ─────────────────────────────────────────────

def test_ssot_drift_fails(tmp_path):
    """yaml 分子 3、清單 3（內部自洽）但統計段 SSOT=2 → 跨源漂移必須非零。"""
    repo = str(tmp_path)
    _write_mapping(repo, {"sd-architect": 2})
    _write_agent(repo, "sd-architect-zh.yaml", 3, ["Greenfield", "Refactoring"], ["Migration"])
    assert sfl.main([repo]) == 1


# ── (3) 分子 ≠ 自列場景數 → 非零（重現 integration 1/10 vs 4）─────────────────

def test_internal_contradiction_fails(tmp_path):
    """frequency 1 但自列 4 場景（無對應統計段 key）→ 內部矛盾必須非零。"""
    repo = str(tmp_path)
    _write_mapping(repo, {"sd-architect": 9})  # 與待測 agent 無關之 SSOT
    _write_agent(repo, "integration-specialist-zh.yaml", 1, ["Integration"],
                 ["Greenfield", "Brownfield", "Migration"], where="specialized")
    assert sfl.main([repo]) == 1


# ── (4) 統計段未列之 agent 僅受內部一致約束 → 一致即 0 ────────────────────────

def test_agent_absent_from_stats_only_internal(tmp_path):
    """pm-po 不在統計段 → 不受 SSOT 約束；分子=清單數即通過。"""
    repo = str(tmp_path)
    _write_mapping(repo, {"sd-architect": 9})
    _write_agent(repo, "03.pm-po-agent-zh.yaml", 5, ["Greenfield"],
                 ["Brownfield", "Integration", "Testing", "Documentation"])
    assert sfl.main([repo]) == 0


# ── (5) runtime agent（無 scenario_usage）豁免 → 0 ───────────────────────────

def test_runtime_agent_without_scenario_usage_exempt(tmp_path):
    repo = str(tmp_path)
    _write_mapping(repo, {"sd-architect": 9})
    base = os.path.join(repo, _VER, "agent", "specialized")
    os.makedirs(base, exist_ok=True)
    with open(os.path.join(base, "sdd-orchestrator-zh.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump({"agent": {"id": "sdd-orchestrator"}, "responsibilities": ["x"]},
                       f, allow_unicode=True)
    assert sfl.main([repo]) == 0


# ── (6) 突變實證：先一致再改壞分子即轉紅 ─────────────────────────────────────

def test_consistent_then_break_detects_regression(tmp_path):
    repo = str(tmp_path)
    _write_mapping(repo, {"sd-architect": 2})
    _write_agent(repo, "sd-architect-zh.yaml", 2, ["Greenfield"], ["Migration"])
    assert sfl.main([repo]) == 0
    # 突變：分子改 5（既不符 SSOT 2、也不符清單 2）
    _write_agent(repo, "sd-architect-zh.yaml", 5, ["Greenfield"], ["Migration"])
    assert sfl.main([repo]) == 1


# ── (7) DEF-AGTREV-017：README 摘要表分子須等於 yaml 分子（第三來源盲區）─────────

def _write_readme(repo: str, rows: list[tuple[str, int]], ver: str = _VER) -> None:
    """寫最小 agent/README.md 核心表；rows=[(檔名, 表列分子)]。"""
    base = os.path.join(repo, ver, "agent")
    os.makedirs(base, exist_ok=True)
    lines = ["# agent", "", "| # | 檔案 | 名 | 角色 | 頻率 | 不可替代性 |",
             "|---|------|----|------|------|-----------|"]
    for i, (fname, num) in enumerate(rows, 1):
        lines.append(f"| {i} | {fname} | N | R | High ({num}/10) | ⭐ |")
    with open(os.path.join(base, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def test_readme_table_matches_yaml_passes(tmp_path):
    """README 表列分子 == yaml 分子 → 0（重現修復後狀態）。"""
    repo = str(tmp_path)
    _write_mapping(repo, {"sd-architect": 2})
    _write_agent(repo, "05.sd-architect-zh.yaml", 2, ["Greenfield"], ["Migration"])
    _write_readme(repo, [("05.sd-architect-zh.yaml", 2)])
    assert sfl.main([repo]) == 0


def test_readme_table_drift_fails(tmp_path):
    """yaml 已對齊 SSOT（2）但 README 表列滯留舊值（7）→ 必須非零
    （重現 DEF-AGTREV-017：dev README 7 vs yaml 4 的第三來源漂移）。"""
    repo = str(tmp_path)
    _write_mapping(repo, {"sd-architect": 2})
    _write_agent(repo, "05.sd-architect-zh.yaml", 2, ["Greenfield"], ["Migration"])
    _write_readme(repo, [("05.sd-architect-zh.yaml", 7)])
    assert sfl.main([repo]) == 1
