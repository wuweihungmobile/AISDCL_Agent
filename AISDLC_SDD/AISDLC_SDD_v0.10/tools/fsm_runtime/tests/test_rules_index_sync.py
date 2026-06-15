"""RULES_INDEX.md ↔ governance/rules/R-*.yaml 雙向同步守則。

落實 CLAUDE.md / RULES_INDEX.md 承諾但先前不存在的「test_rule_loader 同步守則」：
每抽一條規則就必須同步 registry，反之亦然。防止 governance 遷移再次漂移。
對應 arch_fitness FF-2（覆蓋率量測）。
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from tools.fsm_runtime import rule_loader

FRAMEWORK_ROOT = Path(__file__).resolve().parents[3]
RULES_INDEX = FRAMEWORK_ROOT / "governance" / "RULES_INDEX.md"
RULES_DIR = FRAMEWORK_ROOT / "governance" / "rules"

_ROW = re.compile(r"^\|\s*(R-[\w.\-]+)\s*\|")


def _parse_index_rows():
    """回傳 {rule_id: filename}（解析 RULES_INDEX.md 表格資料列）。"""
    rows = {}
    for line in RULES_INDEX.read_text(encoding="utf-8").splitlines():
        if not _ROW.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rule_id, filename = cells[0], cells[-1]
        rows[rule_id] = filename
    return rows


def test_every_rule_file_has_index_row():
    index = _parse_index_rows()
    for p in sorted(RULES_DIR.glob("R-*.yaml")):
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        rid = data["id"]
        assert rid in index, f"{p.name} 的 id={rid} 未列入 RULES_INDEX.md"
        assert index[rid] == p.name, (
            f"RULES_INDEX 中 {rid} 指向 {index[rid]}，實際檔名 {p.name}"
        )


def test_every_index_row_has_rule_file():
    index = _parse_index_rows()
    for rid, filename in index.items():
        path = RULES_DIR / filename
        assert path.exists(), f"RULES_INDEX 列 {rid} 指向不存在的檔 {filename}"


def test_all_rules_parse_and_well_formed():
    rules = rule_loader.load_all()
    assert len(rules) >= 23, f"規則數異常少：{len(rules)}"
    for r in rules:
        assert r.id, "規則缺 id"
        assert r.title, f"{r.id} 缺 title"
        assert r.trigger_states, f"{r.id} 缺 trigger_states"
        assert r.severity in ("critical", "high", "medium", "low"), f"{r.id} severity 異常"
        assert r.maturity in rule_loader.MATURITY_LEVELS, f"{r.id} maturity 異常"


def test_rule_count_matches_index():
    index = _parse_index_rows()
    files = list(RULES_DIR.glob("R-*.yaml"))
    assert len(index) == len(files), (
        f"RULES_INDEX 列數({len(index)}) 與 R-*.yaml 檔數({len(files)}) 不一致"
    )


def test_all_claude_rule9_sections_extracted():
    """CLAUDE.md 每條 `### 9.x` 都應有對應 R-9.x.yaml（Phase 1 抽取完整性）。"""
    claude_md = FRAMEWORK_ROOT.parent / "CLAUDE.md"
    if not claude_md.exists():
        return  # 下游採用情境無 root CLAUDE.md，略過
    sections = set(re.findall(r"^###\s+9\.(\d+)\b", claude_md.read_text(encoding="utf-8"),
                              re.MULTILINE))
    extracted_ids = {r.id for r in rule_loader.load_all()}
    missing = [f"9.{n}" for n in sorted(sections, key=int)
               if f"R-9.{n}" not in extracted_ids]
    assert not missing, f"CLAUDE.md 這些 Rule 9.x 尚未抽出對應 R-*.yaml：{missing}"
