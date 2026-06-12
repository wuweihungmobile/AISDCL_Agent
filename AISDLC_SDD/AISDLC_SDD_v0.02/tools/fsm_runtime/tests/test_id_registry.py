"""ID 分配登記簿守門 — 永久防止 ACT/Rule 編號徵用衝突.

governance/ID_REGISTRY.yaml 為 ACT/Rule 編號的單一真實來源；本測試在每次 pytest/CI
強制檢查其一致性。任何撞號（兩分支認領同一 ACT）、跳號、前緣漂移、保留號被偷建檔、
停滯分支持有號，皆在 PR 階段即 fail。對應使用者「徹底解決、以後不再煩惱」需求。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from tools.fsm_runtime import id_registry

FRAMEWORK_ROOT = Path(__file__).resolve().parents[3]
RULES_DIR = FRAMEWORK_ROOT / "governance" / "rules"


def test_registry_is_self_consistent():
    """無重疊/跳號/前緣漂移/保留號誤建檔/停滯分支持號。"""
    violations = id_registry.validate()
    assert not violations, "ID_REGISTRY 不一致：\n" + "\n".join(violations)


def test_next_free_is_frontier():
    """next_free 為唯一分配前緣（Phase Z 執行後：ACT-172 / R-9.39）。"""
    assert id_registry.next_act() == 172
    assert id_registry.next_rule() == "9.39"


def test_phase_l_owns_its_range():
    """Phase L 執行憑證：持有 ACT-089~096；R-9.24 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    pl = [a for a in reg["act_allocations"] if a["range"] == [89, 96]]
    assert pl and "Phase L" in pl[0]["phase"], "ACT-089~096 必須屬 Phase L"
    assert (RULES_DIR / "R-9.24-meta-halting-offline-experiment-phase-l.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.24" not in reserved_ids, "R-9.24 已 active，不應再列 reserved"


def test_phase_m_owns_its_range():
    """Phase M 執行憑證：持有 ACT-097~104；R-9.25 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    pm = [a for a in reg["act_allocations"] if a["range"] == [97, 104]]
    assert pm and "Phase M" in pm[0]["phase"], "ACT-097~104 必須屬 Phase M"
    assert (RULES_DIR / "R-9.25-composition-autonomy-progress-monitoring-phase-m.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.25" not in reserved_ids, "R-9.25 已 active，不應再列 reserved"


def test_phase_n_owns_its_range():
    """Phase N 執行憑證：持有 ACT-105~110；R-9.26 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    pn = [a for a in reg["act_allocations"] if a["range"] == [105, 110]]
    assert pn and "Phase N" in pn[0]["phase"], "ACT-105~110 必須屬 Phase N"
    assert (RULES_DIR / "R-9.26-global-composition-optimization-phase-n.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.26" not in reserved_ids, "R-9.26 已 active，不應再列 reserved"


def test_phase_o_owns_its_range():
    """Phase O 執行憑證：持有 ACT-111~116；R-9.27 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    po = [a for a in reg["act_allocations"] if a["range"] == [111, 116]]
    assert po and "Phase O" in po[0]["phase"], "ACT-111~116 必須屬 Phase O"
    assert (RULES_DIR / "R-9.27-meta-optimization-self-tuning-phase-o.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.27" not in reserved_ids, "R-9.27 已 active，不應再列 reserved"


def test_phase_p_owns_its_range():
    """Phase P 執行憑證：持有 ACT-117~122；R-9.28 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    pp = [a for a in reg["act_allocations"] if a["range"] == [117, 122]]
    assert pp and "Phase P" in pp[0]["phase"], "ACT-117~122 必須屬 Phase P"
    assert (RULES_DIR / "R-9.28-unified-scorer-calibration-phase-p.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.28" not in reserved_ids, "R-9.28 已 active，不應再列 reserved"


def test_phase_q_owns_its_range():
    """Phase Q 執行憑證：持有 ACT-123~128；R-9.29 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    pq = [a for a in reg["act_allocations"] if a["range"] == [123, 128]]
    assert pq and "Phase Q" in pq[0]["phase"], "ACT-123~128 必須屬 Phase Q"
    assert (RULES_DIR / "R-9.29-self-expanding-value-dimensions-phase-q.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.29" not in reserved_ids, "R-9.29 已 active，不應再列 reserved"


def test_phase_r_owns_its_range():
    """Phase R 執行憑證：持有 ACT-129~134；R-9.30 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    pr = [a for a in reg["act_allocations"] if a["range"] == [129, 134]]
    assert pr and "Phase R" in pr[0]["phase"], "ACT-129~134 必須屬 Phase R"
    assert (RULES_DIR / "R-9.30-self-inventing-value-dimensions-phase-r.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.30" not in reserved_ids, "R-9.30 已 active，不應再列 reserved"


def test_phase_s_owns_its_range():
    """Phase S 執行憑證：持有 ACT-135~140；R-9.31 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    ps = [a for a in reg["act_allocations"] if a["range"] == [135, 140]]
    assert ps and "Phase S" in ps[0]["phase"], "ACT-135~140 必須屬 Phase S"
    assert (RULES_DIR / "R-9.31-self-expanding-vocabulary-batch-retirement-phase-s.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.31" not in reserved_ids, "R-9.31 已 active，不應再列 reserved"


def test_phase_t_owns_its_range():
    """Phase T 執行憑證：持有 ACT-141~146；R-9.32 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    pt = [a for a in reg["act_allocations"] if a["range"] == [141, 146]]
    assert pt and "Phase T" in pt[0]["phase"], "ACT-141~146 必須屬 Phase T"
    assert (RULES_DIR / "R-9.32-self-expanding-operator-grammar-phase-t.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.32" not in reserved_ids, "R-9.32 已 active，不應再列 reserved"


def test_phase_u_owns_its_range():
    """Phase U 執行憑證：持有 ACT-147~149；R-9.33 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    pu = [a for a in reg["act_allocations"] if a["range"] == [147, 149]]
    assert pu and "Phase U" in pu[0]["phase"], "ACT-147~149 必須屬 Phase U"
    assert (RULES_DIR / "R-9.33-self-expanding-operator-alphabet-phase-u.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.33" not in reserved_ids, "R-9.33 已 active，不應再列 reserved"


def test_phase_v_owns_its_range():
    """Phase V 執行憑證：持有 ACT-150~152；R-9.34 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    pv = [a for a in reg["act_allocations"] if a["range"] == [150, 152]]
    assert pv and "Phase V" in pv[0]["phase"], "ACT-150~152 必須屬 Phase V"
    assert (RULES_DIR / "R-9.34-self-expanding-operator-depth-phase-v.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.34" not in reserved_ids, "R-9.34 已 active，不應再列 reserved"


def test_phase_w_owns_its_range():
    """Phase W 執行憑證：持有 ACT-153~155；R-9.35 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    pw = [a for a in reg["act_allocations"] if a["range"] == [153, 155]]
    assert pw and "Phase W" in pw[0]["phase"], "ACT-153~155 必須屬 Phase W"
    assert (RULES_DIR / "R-9.35-self-expanding-operator-recursion-phase-w.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.35" not in reserved_ids, "R-9.35 已 active，不應再列 reserved"


def test_phase_y_owns_its_range():
    """Phase Y 執行憑證：持有 ACT-159~161；R-9.37 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    py = [a for a in reg["act_allocations"] if a["range"] == [159, 161]]
    assert py and "Phase Y" in py[0]["phase"], "ACT-159~161 必須屬 Phase Y"
    assert (RULES_DIR / "R-9.37-recursion-topology-visualization-phase-y.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.37" not in reserved_ids, "R-9.37 已 active，不應再列 reserved"


def test_phase_k_owns_disputed_range():
    """衝突解決憑證：Phase K 持有 ACT-081~088；R-9.23 已落地為 active（不再 reserved）。"""
    reg = id_registry.load_registry()
    pk = [a for a in reg["act_allocations"] if a["range"] == [81, 88]]
    assert pk and "Phase K" in pk[0]["phase"], "ACT-081~088 必須屬 Phase K"
    # Phase K 執行完成後，R-9.23 從 reserved 落地為 on-disk active
    assert (RULES_DIR / "R-9.23-intent-planning-dialectic-phase-k.yaml").exists()
    reserved_ids = {r["id"] for r in reg["rule_allocations"].get("reserved", []) or []}
    assert "R-9.23" not in reserved_ids, "R-9.23 已 active，不應再列 reserved"


def test_parked_branch_holds_no_number():
    """M3 Hook Health（停滯）不得持有任何號——這正是舊衝突根因。"""
    reg = id_registry.load_registry()
    for pk in reg.get("parked", []):
        assert pk.get("act_range") is None, f"{pk['name']} 不得持有 act_range"
        assert pk.get("rule") is None, f"{pk['name']} 不得持有 rule"


def test_every_on_disk_rule_is_active_not_reserved():
    """磁碟上每個 R-9.*.yaml 都不得落在『保留』號上（否則代表 registry 漏更新）。"""
    reg = id_registry.load_registry()
    reserved_ids = {r["id"] for r in reg["rule_allocations"]["reserved"]}
    for p in RULES_DIR.glob("R-9.*.yaml"):
        rid = yaml.safe_load(p.read_text(encoding="utf-8"))["id"]
        assert rid not in reserved_ids, (
            f"{p.name}(id={rid}) 已落地卻仍標 reserved，請在 ID_REGISTRY 改為 active 並推進 next_free"
        )
