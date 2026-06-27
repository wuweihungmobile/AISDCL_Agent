"""ACT / Rule(R-9.x) 編號分配權威 — 徹底解決編號徵用衝突.

單一真實來源：governance/ID_REGISTRY.yaml。本模組提供：
  - next_act() / next_rule()：分配前查「下一個可用號」（取代人工散記）。
  - validate()：偵測重疊/跳號/前緣不一致/保留號被誤建檔/停滯分支持有號。
  - CLI：python -m tools.fsm_runtime.id_registry {next-act|next-rule|validate|list}

機器守門由 tools/fsm_runtime/tests/test_id_registry.py 在每次 pytest/CI 強制執行，
任何撞號（如兩分支都認領 ACT-081）在 PR 階段即 fail，永不再漂移。
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = FRAMEWORK_ROOT / "governance" / "ID_REGISTRY.yaml"
RULES_DIR = FRAMEWORK_ROOT / "governance" / "rules"


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def next_act(reg: dict | None = None) -> int:
    reg = reg or load_registry()
    return int(reg["next_free"]["act"])


def next_rule(reg: dict | None = None) -> str:
    reg = reg or load_registry()
    return str(reg["next_free"]["rule"])


def _rule_minor(rid: str) -> int | None:
    """R-9.23 / 9.23 -> 23；非數字（R-SELF-STRIDE）-> None。"""
    s = rid[2:] if rid.startswith("R-") else rid
    if not s.startswith("9."):
        return None
    try:
        return int(s.split(".")[-1])
    except ValueError:
        return None


def _on_disk_rule_minors() -> set[int]:
    minors = set()
    for p in RULES_DIR.glob("R-9.*.yaml"):
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        m = _rule_minor(str(data.get("id", "")))
        if m is not None:
            minors.add(m)
    return minors


def validate(reg: dict | None = None) -> list[str]:
    """回傳違規清單；空清單 = 一致。"""
    reg = reg or load_registry()
    violations: list[str] = []

    # --- ACT：contiguous from 1、不重疊、不跳號，next_free = 末端+1 ---
    allocs = sorted(reg["act_allocations"], key=lambda a: a["range"][0])
    expected_start = 1
    for a in allocs:
        start, end = a["range"]
        if start != expected_start:
            violations.append(
                f"ACT 範圍不連續/重疊：{a['phase']} 起點 {start}，預期 {expected_start}"
            )
        if end < start:
            violations.append(f"ACT 範圍反向：{a['phase']} {a['range']}")
        expected_start = end + 1
    nf_act = int(reg["next_free"]["act"])
    if nf_act != expected_start:
        violations.append(f"next_free.act={nf_act}，預期 {expected_start}（末端+1）")

    # --- Rule：磁碟 active + reserved 不重疊；reserved 尚無檔；next_free 為前緣+1 ---
    on_disk = _on_disk_rule_minors()
    reserved = reg.get("rule_allocations", {}).get("reserved", []) or []
    reserved_minors = set()
    for r in reserved:
        m = _rule_minor(str(r["id"]))
        if m is None:
            continue
        reserved_minors.add(m)
        if m in on_disk:
            violations.append(
                f"保留號 {r['id']} 已存在磁碟檔，應將 registry 改為 active"
            )
        fe = r.get("file_expected")
        if fe and (RULES_DIR / fe).exists():
            violations.append(
                f"保留號 {r['id']} 的預期檔 {fe} 已建立，應改為 active"
            )
    overlap = on_disk & reserved_minors
    if overlap:
        violations.append(f"Rule 號 active 與 reserved 重疊：9.{sorted(overlap)}")
    frontier = max(on_disk | reserved_minors) if (on_disk or reserved_minors) else 0
    nf_rule_m = _rule_minor(str(reg["next_free"]["rule"]))
    if nf_rule_m != frontier + 1:
        violations.append(
            f"next_free.rule=9.{nf_rule_m}，預期 9.{frontier + 1}（前緣+1）"
        )

    # --- 停滯/備援分支不得持有任何號 ---
    for pk in reg.get("parked", []) or []:
        if pk.get("act_range") is not None or pk.get("rule") is not None:
            violations.append(
                f"停滯分支『{pk.get('name')}』持有號（act_range/rule 應為 null）"
            )

    return violations


def _list(reg: dict) -> str:
    lines = ["ACT 分配："]
    for a in sorted(reg["act_allocations"], key=lambda a: a["range"][0]):
        lines.append(f"  ACT-{a['range'][0]:03d}~{a['range'][1]:03d}  [{a['status']:8}] {a['phase']}")
    lines.append(f"  → next_free.act = {reg['next_free']['act']}")
    lines.append("Rule 保留：")
    for r in reg.get("rule_allocations", {}).get("reserved", []) or []:
        lines.append(f"  {r['id']}  [{r['status']}] {r['phase']}")
    lines.append(f"  → next_free.rule = {reg['next_free']['rule']}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "validate"
    reg = load_registry()
    if cmd == "next-act":
        print(f"ACT-{next_act(reg):03d}")
    elif cmd == "next-rule":
        print(f"R-{next_rule(reg)}")
    elif cmd == "list":
        print(_list(reg))
    elif cmd == "validate":
        v = validate(reg)
        if v:
            print("[FAIL] ID_REGISTRY 不一致：")
            for x in v:
                print(f"  - {x}")
            return 1
        print("[OK] ID_REGISTRY 一致（無撞號/跳號/前緣漂移）")
    else:
        print(f"未知指令：{cmd}（可用：next-act|next-rule|validate|list）")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
