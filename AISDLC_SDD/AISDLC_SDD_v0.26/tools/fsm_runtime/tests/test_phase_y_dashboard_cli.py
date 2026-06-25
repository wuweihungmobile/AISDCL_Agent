"""Phase Y / improving_66 W-66-2 — 舵手可審批儀表板 CLI 回歸鎖（render_topology_dashboard）.

對應藍圖：docs/04_planning/AutoSDD_improving_66.md（GAP-Y2 closure，掌舵者 2026-06-25 signoff）
對應規則：CLAUDE.md Rule 9.37（VisualizationBounded / read-only 純觀察者 / 對抗分離）

涵蓋（W-66-2 DoD）：
  - happy path：proposed 互遞迴算子 → CLI 印三視圖儀表板（拓樸/終止/接地）且過 guard、exit 0。
  - 受控突變（**真實 guard 觸發，非空殼**）：render budget 逃逸（char_budget=1000）→ CLI 非零 exit
    + 不印儀表板（fail-closed，絕不 false-green）；guard 被 monkeypatch raise → CLI 同樣 fail-loud。
  - fail-loud：ledger 缺檔 / 無 recursion_inventions 段 / rule-id 不存在 → 明確訊息 + 非零 exit
    （絕不靜默空輸出）。
  - 紅線守恆：CLI 為 read-only（跑後 ledger byte-identical）；源碼零 import 任何 generator（對抗分離）。
"""
from __future__ import annotations

import ast
from pathlib import Path

import yaml

from tools.fsm_runtime import render_topology_dashboard as CLI
from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
from tools.fsm_runtime.operator_recursion_genesis import RecursiveOperator
from tools.fsm_runtime.operator_genesis import GenesisOperator

CLI_SRC = Path(CLI.__file__)


def _fan_op():
    return RecursiveOperator.fan(GenesisOperator.of("sum", "sq"), 3, combine="mul")


def _write_ledger(tmp_path: Path, op_dict, *, signoff="pending") -> Path:
    """寫一份含 recursion_inventions[].selected[].operator 的 ledger（鏡像 genesis.record_round）。"""
    led = {
        "schema_version": 1,
        "recursion_inventions": [{
            "ts": "2026-06-25T00:00:00+00:00", "k": 1,
            "selected": [{"operator": op_dict,
                          "fingerprint": op_dict["fingerprint"],
                          "maturity": "proposed"}],
            "deferred": [], "n_accepted": 1, "signoff": signoff,
        }],
    }
    p = tmp_path / "value-dimension-ledger.yaml"
    p.write_text(yaml.safe_dump(led, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p


def _rule_id(op_dict) -> str:
    return "RCR-" + op_dict["fingerprint"].replace(":", "-")


# ---------------------------------------------------------------------------
# happy path：proposed 算子 → 三視圖儀表板 + 過 guard + exit 0
# ---------------------------------------------------------------------------
def test_cli_happy_path_renders_dashboard_exit0(tmp_path, capsys):
    od = _fan_op().to_dict()
    p = _write_ledger(tmp_path, od)
    rc = CLI.main(["--ledger", str(p)])
    out = capsys.readouterr().out
    assert rc == 0
    # 三視圖 + read-only 純觀察者宣告（舵手不讀程式碼即可看圖）。
    assert "Recursion Topology Dashboard" in out
    assert "read-only" in out
    assert "```mermaid" in out and "flowchart TD" in out   # ① 拓樸視圖（Mermaid）
    assert "fuel" in out                                    # ② 終止/fuel 階梯
    assert "Δrank" in out                                   # 每邊良基遞減標註


def test_cli_rule_id_hit_and_json(tmp_path, capsys):
    od = _fan_op().to_dict()
    p = _write_ledger(tmp_path, od)
    rc = CLI.main(["--ledger", str(p), "--rule-id", _rule_id(od)])
    out = capsys.readouterr().out
    assert rc == 0 and "Recursion Topology Dashboard" in out
    rc_json = CLI.main(["--ledger", str(p), "--json"])
    out_json = capsys.readouterr().out
    assert rc_json == 0 and '"nodes"' in out_json


# ---------------------------------------------------------------------------
# 受控突變（真實 guard 觸發，非空殼）：render budget 逃逸 → fail-closed
# ---------------------------------------------------------------------------
def test_cli_budget_escape_blocks_no_false_green(tmp_path, capsys, monkeypatch):
    """char_budget 壓到 clamp 下限 1000 → fan op 儀表板（~1.6k 字）逃逸 char_budget →
    guard_visualization_bounded raise → CLI 非零 exit + stdout 不印儀表板（絕不 false-green）。
    這是**真實 guard 觸發**（非 monkeypatch），證 guard 在 CLI 路徑有效、非空殼。"""
    od = _fan_op().to_dict()
    p = _write_ledger(tmp_path, od)
    monkeypatch.setenv("SDD_VIZ_CHAR_BUDGET", "1000")
    rc = CLI.main(["--ledger", str(p)])
    cap = capsys.readouterr()
    assert rc == 3                                   # fail-closed exit（≠0）
    assert cap.out == ""                             # stdout 無儀表板（不 false-green）
    assert "BLOCKED" in cap.err and "VisualizationBounded" in cap.err


def test_cli_guard_is_wired_not_shell(tmp_path, capsys, monkeypatch):
    """monkeypatch guard 直接 raise VisualizationViolation → CLI 必 fail-closed（exit 3、stdout 空）。
    證 CLI 確實呼叫 guard 並在違反時 fail-loud（非「印了再說」的空殼）。"""
    od = _fan_op().to_dict()
    p = _write_ledger(tmp_path, od)

    def _boom(view, op_dict):
        raise MM.VisualizationViolation("受控突變：拓樸防偽攔截（測試注入）")
    monkeypatch.setattr(MM, "guard_visualization_bounded", _boom)
    rc = CLI.main(["--ledger", str(p)])
    cap = capsys.readouterr()
    assert rc == 3 and cap.out == "" and "BLOCKED" in cap.err


# ---------------------------------------------------------------------------
# fail-loud：缺檔 / 缺段 / rule-id 不存在 → 非零 exit + 明確訊息（不靜默）
# ---------------------------------------------------------------------------
def test_cli_missing_ledger_fail_loud(tmp_path, capsys):
    rc = CLI.main(["--ledger", str(tmp_path / "nope.yaml")])
    cap = capsys.readouterr()
    assert rc == 2 and cap.out == "" and "FAIL" in cap.err


def test_cli_empty_inventions_fail_loud(tmp_path, capsys):
    p = tmp_path / "value-dimension-ledger.yaml"
    p.write_text(yaml.safe_dump({"schema_version": 1}, allow_unicode=True), encoding="utf-8")
    rc = CLI.main(["--ledger", str(p)])
    cap = capsys.readouterr()
    assert rc == 2 and "recursion_inventions" in cap.err


def test_cli_rule_id_not_found_fail_loud(tmp_path, capsys):
    od = _fan_op().to_dict()
    p = _write_ledger(tmp_path, od)
    rc = CLI.main(["--ledger", str(p), "--rule-id", "RCR-does-not-exist"])
    cap = capsys.readouterr()
    assert rc == 2 and cap.out == "" and "rule-id" in cap.err


# ---------------------------------------------------------------------------
# 紅線守恆（Rule 9.37.4）：read-only + 對抗分離
# ---------------------------------------------------------------------------
def test_cli_is_read_only_ledger_unchanged(tmp_path):
    od = _fan_op().to_dict()
    p = _write_ledger(tmp_path, od)
    before = p.read_bytes()
    CLI.main(["--ledger", str(p)])
    assert p.read_bytes() == before          # read-only：ledger byte-identical（不寫回）


def test_cli_source_imports_no_generator():
    """對抗分離（Rule 9.37.4）：CLI 源碼**真實 import 節點**不得引入任何 generator
    （operator_*_genesis / dimension_semantics_synthesizer / vocabulary_genesis /
    embodied_grounding_oracle）。以 AST 解析，故 docstring 內的「禁止清單」說明文字不誤判。"""
    tree = ast.parse(CLI_SRC.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            imported.append(base)
            imported += [f"{base}.{a.name}" for a in node.names]
    forbidden = ("genesis", "dimension_semantics_synthesizer",
                 "vocabulary_genesis", "embodied_grounding_oracle")
    hits = [m for m in imported if any(f in m for f in forbidden)]
    assert not hits, f"CLI 違反對抗分離（Rule 9.37.4）：import 了 generator → {hits}"
