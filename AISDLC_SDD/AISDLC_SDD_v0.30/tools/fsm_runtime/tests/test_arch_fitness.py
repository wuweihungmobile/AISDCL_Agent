"""arch_fitness 適應度函式 + state_loader 根因消毒 回歸測試。

對應 workflow/sdd-self-evolution/SDD_SELF_EVOLUTION.md。
"""
from __future__ import annotations

import pytest

from tools.arch_fitness import arch_fitness as af
from tools.fsm_runtime import state_loader
from tools.fsm_runtime import transition_rules as tr


# ---------------------------------------------------------------------------
# FF-1：FSM 三源狀態宇宙一致性
# ---------------------------------------------------------------------------
def test_ff1_state_universe_is_consistent():
    """現有 repo 必須通過 FF-1（雙源一致性回歸守門）。"""
    report = af.run_fitness(only=["FF-1"])
    fails = [f for f in report.findings if f.severity == af.SEVERITY_FAIL]
    assert not fails, f"FF-1 應通過，卻有：{[f.title for f in fails]}"
    assert any(f.fingerprint == "ff1-ok" for f in report.findings)


def test_parse_tla_set_extracts_terminals():
    sets = af._tla_state_universe(af.TLA_PATH.read_text(encoding="utf-8"))
    assert "RELEASE" in sets["Terminals"]
    assert "ESCALATION_FINAL" in sets["Terminals"]
    assert "IMPLEMENTATION" in sets["HappyStates"]


def test_ff1_python_universe_equals_tla():
    py = set(tr._HAPPY_PATH.keys()) | set(tr._EMERGENCY_TARGETS)
    sets = af._tla_state_universe(af.TLA_PATH.read_text(encoding="utf-8"))
    tla = set().union(*sets.values())
    assert py == tla, f"only_py={py - tla} only_tla={tla - py}"


# ---------------------------------------------------------------------------
# FF-1 R2：真三源（+ SDD_FSM_ENGINE.md 第三源），複用 fsm_md_parser
# ---------------------------------------------------------------------------
def test_ff1_real_repo_is_tri_source_clean():
    """現有 repo 必須三源一致：ff1-ok 且 title 提及 MD，無任何 fail。"""
    report = af.run_fitness(only=["FF-1"])
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]
    ok = [f for f in report.findings if f.fingerprint == "ff1-ok"]
    assert ok and "MD" in ok[0].title


def test_fsm_md_parser_is_single_source_and_clean():
    """共用 parser：MD 轉換表來源欄 + 宇宙皆 ⊆ Python（無 stale token）。"""
    from tools.fsm_runtime import fsm_md_parser as mp
    py = set(tr._HAPPY_PATH) | set(tr._EMERGENCY_TARGETS)
    assert mp.md_source_states() <= py
    assert mp.md_state_universe() <= py


def test_ff1_md_undocumented_state_fails(tmp_path, monkeypatch):
    """MD 缺漏 canonical 狀態 → structural fail（三源破口）。"""
    md = tmp_path / "SDD_FSM_ENGINE.md"
    md.write_text(
        "# x\n\n## 狀態轉換表\n\n"
        "| 來源 | 條件 | 目標 |\n|---|---|---|\n"
        "| INIT | x | SCENARIO_DETECT |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(af, "FSM_MD_PATH", md)
    report = af.FitnessReport()
    af.check_ff1_fsm_state_universe(report)
    assert any(f.fingerprint == "ff1-md-undocumented" and f.severity == af.SEVERITY_FAIL
               for f in report.findings)
    assert not any(f.fingerprint == "ff1-ok" for f in report.findings)


def test_ff1_md_stale_source_warns(tmp_path, monkeypatch):
    """MD 來源欄出現非真實狀態 → advisory warn（但全狀態有文字提及故不觸發未記載）。"""
    all_real = " ".join(sorted(set(tr._HAPPY_PATH) | set(tr._EMERGENCY_TARGETS)))
    md = tmp_path / "SDD_FSM_ENGINE.md"
    md.write_text(
        f"# x\n\n全狀態提及：{all_real}\n\n"
        "## 狀態轉換表\n\n"
        "| 來源 | 條件 | 目標 |\n|---|---|---|\n"
        "| BOGUS_GHOST_STATE | x | INIT |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(af, "FSM_MD_PATH", md)
    report = af.FitnessReport()
    af.check_ff1_fsm_state_universe(report)
    assert any(f.fingerprint == "ff1-md-stale-source" and f.severity == af.SEVERITY_WARN
               for f in report.findings)


def test_ff1_no_md_degrades_to_warn(tmp_path, monkeypatch):
    """MD 不存在 → 降級為雙源，warn 而非崩潰。"""
    monkeypatch.setattr(af, "FSM_MD_PATH", tmp_path / "missing.md")
    report = af.FitnessReport()
    af.check_ff1_fsm_state_universe(report)
    assert any(f.fingerprint == "ff1-no-md" and f.severity == af.SEVERITY_WARN
               for f in report.findings)


# ---------------------------------------------------------------------------
# FF-3：孤兒 / 巢狀垃圾偵測（以暫存目錄隔離）
# ---------------------------------------------------------------------------
def test_ff3_detects_orphan_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(af, "FSM_STATE_DIR", tmp_path)
    (tmp_path / "FSM-STATE-AISDLC_SDD.yaml.tmp").write_text("garbage", encoding="utf-8")
    report = af.FitnessReport()
    af.check_ff3_orphan_state_files(report)
    assert any(f.fingerprint == "ff3-orphan-tmp" and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff3_detects_nested_path_garbage(tmp_path, monkeypatch):
    monkeypatch.setattr(af, "FSM_STATE_DIR", tmp_path)
    nested = tmp_path / "FSM-STATE-build" / "reports" / "fsm"
    nested.mkdir(parents=True)
    (nested / "FSM-STATE-AISDLC_SDD.yaml.yaml.tmp").write_text("x", encoding="utf-8")
    report = af.FitnessReport()
    af.check_ff3_orphan_state_files(report)
    fps = {f.fingerprint for f in report.findings}
    assert "ff3-orphan-tmp" in fps or "ff3-nested-path" in fps


def test_ff3_clean_dir_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(af, "FSM_STATE_DIR", tmp_path)
    report = af.FitnessReport()
    af.check_ff3_orphan_state_files(report)
    assert any(f.fingerprint == "ff3-ok" for f in report.findings)


# ---------------------------------------------------------------------------
# FF-4：觀測態與 Terminal/Emergency 互斥（Rule 9.18.4 鏡像）
# ---------------------------------------------------------------------------
def test_ff4_observation_disjoint_from_terminals():
    sets = af._tla_state_universe(af.TLA_PATH.read_text(encoding="utf-8"))
    py_obs = set(tr.OBSERVATION_STATES)
    assert py_obs & sets["Terminals"] == set()
    assert py_obs & set(tr._EMERGENCY_TARGETS) == set()


def test_ff4_no_structural_fail_in_repo():
    report = af.run_fitness(only=["FF-4"])
    assert not [f for f in report.findings
                if f.severity == af.SEVERITY_FAIL]


# ---------------------------------------------------------------------------
# 分數模型（收斂閘以此單調遞減判定）
# ---------------------------------------------------------------------------
def test_score_weighting():
    r = af.FitnessReport()
    r.add(af.Finding(ff="X", severity=af.SEVERITY_FAIL, fingerprint="a", title="", detail=""))
    r.add(af.Finding(ff="Y", severity=af.SEVERITY_WARN, fingerprint="b", title="", detail=""))
    r.add(af.Finding(ff="Z", severity=af.SEVERITY_INFO, fingerprint="c", title="", detail=""))
    assert r.score() == 11  # 10*1 + 1*1


# ---------------------------------------------------------------------------
# 根因修復：_default_state_path / track_state_path 消毒路徑分隔符
# （防 FF-3 巢狀 .tmp 孤兒再生）
# ---------------------------------------------------------------------------
def test_default_state_path_defangs_separators():
    bad = "build/reports/fsm/FSM-STATE-AISDLC_SDD.yaml"
    p = state_loader._default_state_path(bad)
    assert "/" not in p.name and "\\" not in p.name
    # 巢狀垃圾的特徵不應出現在父目錄結構（檔名被攤平）
    assert p.parent == state_loader.DEFAULT_STATE_DIR


def test_track_state_path_defangs_separators():
    p = state_loader.track_state_path("proj", track_id="a/b\\c")
    assert p.name == "FSM-STATE-proj-a_b_c.yaml"


def test_sanitize_component_idempotent_for_clean_name():
    assert state_loader._sanitize_component("AISDLC_SDD") == "AISDLC_SDD"


# ---------------------------------------------------------------------------
# FF-5：CLAUDE.md §9 頁數守門 + 引用完整性（Phase 2 2b，以合成輸入測試，
# 不耦合 repo 當前是否已裁剪）
# ---------------------------------------------------------------------------
def _write_claudemd(tmp_path, rule9_body: str):
    md = tmp_path / "CLAUDE.md"
    md.write_text(
        "# CLAUDE.md\n\n## Rule 8\n前略\n\n"
        f"## 🔴 Rule 9：自動化閉環防護\n\n{rule9_body}\n\n## 下一節\n後略\n",
        encoding="utf-8",
    )
    return md


def test_ff5_oversize_warns(tmp_path, monkeypatch):
    monkeypatch.setattr(af, "PROJECT_ROOT", tmp_path)
    _write_claudemd(tmp_path, "x" * 4000)  # >1.2 頁
    report = af.FitnessReport()
    af.check_ff5_claudemd_rule9_size(report)
    assert any(f.fingerprint == "ff5-oversize" and f.severity == af.SEVERITY_WARN
               for f in report.findings)


def test_ff5_ok_when_small_with_valid_refs(tmp_path, monkeypatch):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "R-9.1-x.yaml").write_text("id: R-9.1\n", encoding="utf-8")
    monkeypatch.setattr(af, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(af, "GOV_RULES_DIR", rules_dir)
    _write_claudemd(tmp_path, "絕對禁令：retry 超限不停（R-9.1）")
    report = af.FitnessReport()
    af.check_ff5_claudemd_rule9_size(report)
    assert any(f.fingerprint == "ff5-ok" for f in report.findings)
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]


def test_ff5_dangling_ref_fails(tmp_path, monkeypatch):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    monkeypatch.setattr(af, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(af, "GOV_RULES_DIR", rules_dir)
    _write_claudemd(tmp_path, "引用不存在的 R-9.99")
    report = af.FitnessReport()
    af.check_ff5_claudemd_rule9_size(report)
    assert any(f.fingerprint == "ff5-dangling-ref" and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_rule9_block_extraction():
    text = "## A\naaa\n## Rule 9：x\nBODY9\n## B\nbbb\n"
    block = af._rule9_block(text)
    assert "BODY9" in block and "bbb" not in block


# ---------------------------------------------------------------------------
# FF-6：文件相對連結完整性（roadmap R3）—— 兩層分離（樞紐硬訊號 + 內容軟訊號）
# ---------------------------------------------------------------------------
def _fw(tmp_path, monkeypatch):
    """把 FRAMEWORK_ROOT 指向隔離 tmp，建構合成框架樹。"""
    monkeypatch.setattr(af, "FRAMEWORK_ROOT", tmp_path)
    return tmp_path


def test_strip_code_fences_removes_indented_fences():
    text = "keep1\n   ```markdown\n[x](./gone.md)\n   ```\nkeep2\n"
    out = af._strip_code_fences(text)
    assert "gone.md" not in out
    assert "keep1" in out and "keep2" in out


def test_ff6_hub_dead_link_warns(tmp_path, monkeypatch):
    root = _fw(tmp_path, monkeypatch)
    (root / "agent" / "core").mkdir(parents=True)
    (root / "agent" / "core" / "x.yaml").write_text("ok", encoding="utf-8")
    (root / "AISDLC_SDD_INIT.md").write_text(
        "good [a](agent/core/x.yaml) bad [b](agent/core/missing.yaml)\n", encoding="utf-8")
    report = af.FitnessReport()
    af.check_ff6_doc_link_integrity(report)
    warns = [f for f in report.findings if f.severity == af.SEVERITY_WARN]
    assert any(f.fingerprint.startswith("ff6-hub-") and "missing.yaml" in f.title
               for f in warns)


def test_ff6_workflow_linkrot_aggregates_to_one(tmp_path, monkeypatch):
    root = _fw(tmp_path, monkeypatch)
    (root / "AISDLC_SDD_INIT.md").write_text("hub 無連結\n", encoding="utf-8")
    wf = root / "workflow" / "core"
    wf.mkdir(parents=True)
    (wf / "a.md").write_text("[x](./nope1.md) [y](./nope2.md)\n", encoding="utf-8")
    report = af.FitnessReport()
    af.check_ff6_doc_link_integrity(report)
    agg = [f for f in report.findings if f.fingerprint == "ff6-workflow-linkrot"]
    assert len(agg) == 1 and agg[0].severity == af.SEVERITY_WARN
    assert "2 條" in agg[0].title
    # 樞紐乾淨 → ff6-hub-ok info（且不得有 ff6-hub-* warn）
    assert any(f.fingerprint == "ff6-hub-ok" for f in report.findings)
    assert not any(f.fingerprint.startswith("ff6-hub-") and f.severity == af.SEVERITY_WARN
                   for f in report.findings)


def test_ff6_ignores_links_in_code_fences(tmp_path, monkeypatch):
    root = _fw(tmp_path, monkeypatch)
    (root / "AISDLC_SDD_INIT.md").write_text(
        "純文字無連結\n```markdown\n[ex](./does-not-exist.md)\n```\n", encoding="utf-8")
    report = af.FitnessReport()
    af.check_ff6_doc_link_integrity(report)
    assert any(f.fingerprint == "ff6-ok" for f in report.findings)
    assert not [f for f in report.findings if f.severity == af.SEVERITY_WARN]


def test_ff6_skips_external_anchor_template(tmp_path, monkeypatch):
    root = _fw(tmp_path, monkeypatch)
    (root / "AISDLC_SDD_INIT.md").write_text(
        "[a](https://x.y) [b](#sec) [c](dir/{N}.md) [d](mailto:a@b.c)\n", encoding="utf-8")
    report = af.FitnessReport()
    af.check_ff6_doc_link_integrity(report)
    assert any(f.fingerprint == "ff6-ok" for f in report.findings)


# ---------------------------------------------------------------------------
# FF-7：Agent↔Workflow↔Skill 引用健康度
# ---------------------------------------------------------------------------
def test_ff7_specialized_count_drift_warns(tmp_path, monkeypatch):
    root = _fw(tmp_path, monkeypatch)
    sp = root / "agent" / "specialized"
    sp.mkdir(parents=True)
    for n in "abc":
        (sp / f"{n}-zh.yaml").write_text("x", encoding="utf-8")
    (root / "AISDLC_SDD_INIT.md").write_text("### Specialized Agents（14 個）\n", encoding="utf-8")
    report = af.FitnessReport()
    af.check_ff7_agent_workflow_skill_refs(report)
    assert any(f.fingerprint == "ff7-count-specialized-agents"
               and f.severity == af.SEVERITY_WARN for f in report.findings)


def test_ff7_broken_config_ref_warns(tmp_path, monkeypatch):
    root = _fw(tmp_path, monkeypatch)
    (root / "AISDLC_SDD_INIT.md").write_text(
        '      - path: "agent/core/missing.yaml"\n', encoding="utf-8")
    report = af.FitnessReport()
    af.check_ff7_agent_workflow_skill_refs(report)
    assert any(f.fingerprint.startswith("ff7-ref-")
               and f.severity == af.SEVERITY_WARN for f in report.findings)


def test_ff7_clean_passes(tmp_path, monkeypatch):
    root = _fw(tmp_path, monkeypatch)
    (root / "AISDLC_SDD_INIT.md").write_text("無宣稱無路徑\n", encoding="utf-8")
    report = af.FitnessReport()
    af.check_ff7_agent_workflow_skill_refs(report)
    assert any(f.fingerprint == "ff7-ok" for f in report.findings)


# ---------------------------------------------------------------------------
# R4：趨勢記錄（唯一有副作用的函式）
# ---------------------------------------------------------------------------
def test_write_trend_appends_yaml(tmp_path):
    import yaml
    r = af.FitnessReport()
    r.add(af.Finding(ff="FF-6", severity=af.SEVERITY_WARN,
                     fingerprint="ff6-x", title="t", detail="d"))
    path = tmp_path / "TREND.yaml"
    af.write_trend(r, path)
    af.write_trend(r, path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 2
    assert data[0]["score"] == 1 and "ff6-x" in data[0]["fingerprints"]


# ---------------------------------------------------------------------------
# FF-8：Governance 規則 → 強制執行測試 可追溯性（roadmap R7）
# ---------------------------------------------------------------------------
def _rule(tmp_path, monkeypatch, body: str, fname: str = "R-9.1-x.yaml"):
    """於隔離 tmp 建構 GOV_RULES_DIR + FRAMEWORK_ROOT，寫一條合成規則。"""
    rules = tmp_path / "governance" / "rules"
    rules.mkdir(parents=True, exist_ok=True)
    (rules / fname).write_text(body, encoding="utf-8")
    monkeypatch.setattr(af, "GOV_RULES_DIR", rules)
    monkeypatch.setattr(af, "FRAMEWORK_ROOT", tmp_path)
    return tmp_path


def _make_test_file(root, rel: str, with_test_fn=True, mentions: str = ""):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if mentions:
        lines.append(f"# enforces: {mentions}")
    lines.append("def test_x():\n    assert True\n" if with_test_fn else "x = 1\n")
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def test_ff8_missing_testref_fails(tmp_path, monkeypatch):
    _rule(tmp_path, monkeypatch, "id: R-9.1\nmaturity: active\n")
    report = af.FitnessReport()
    af.check_ff8_rule_enforcement_traceability(report)
    assert any(f.fingerprint == "ff8-missing-testref" and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff8_dangling_testref_fails(tmp_path, monkeypatch):
    _rule(tmp_path, monkeypatch,
          "id: R-9.1\nmaturity: active\ntest_ref: tools/fsm_runtime/tests/gone.py\n")
    report = af.FitnessReport()
    af.check_ff8_rule_enforcement_traceability(report)
    assert any(f.fingerprint.startswith("ff8-dangling-") and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff8_no_test_function_fails(tmp_path, monkeypatch):
    root = _rule(tmp_path, monkeypatch,
                 "id: R-9.1\nmaturity: active\ntest_ref: t/stub.py\n")
    _make_test_file(root, "t/stub.py", with_test_fn=False)
    report = af.FitnessReport()
    af.check_ff8_rule_enforcement_traceability(report)
    assert any(f.fingerprint.startswith("ff8-no-testfn-") and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff8_weak_backref_warns(tmp_path, monkeypatch):
    root = _rule(tmp_path, monkeypatch,
                 "id: R-9.1\nmaturity: active\ntest_ref: t/test_a.py\n")
    _make_test_file(root, "t/test_a.py", mentions="")  # 不提及 R-9.1
    report = af.FitnessReport()
    af.check_ff8_rule_enforcement_traceability(report)
    assert any(f.fingerprint == "ff8-weak-backref" and f.severity == af.SEVERITY_WARN
               for f in report.findings)


def test_ff8_deprecated_rule_exempt(tmp_path, monkeypatch):
    """非 active（退役/audit-only）規則不要求強制測試，不報任何 fail。"""
    _rule(tmp_path, monkeypatch, "id: R-9.1\nmaturity: deprecated\n")
    report = af.FitnessReport()
    af.check_ff8_rule_enforcement_traceability(report)
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]


def test_ff8_clean_passes(tmp_path, monkeypatch):
    root = _rule(tmp_path, monkeypatch,
                 "id: R-9.1\nmaturity: active\ntest_ref: t/test_a.py\n")
    _make_test_file(root, "t/test_a.py", mentions="R-9.1")
    report = af.FitnessReport()
    af.check_ff8_rule_enforcement_traceability(report)
    assert any(f.fingerprint == "ff8-ok" for f in report.findings)
    assert not [f for f in report.findings if f.severity != af.SEVERITY_INFO]


# ---------------------------------------------------------------------------
# Repo 回歸：新 FF 為 advisory-only，且 INIT.md 導覽樞紐必須全綠
# ---------------------------------------------------------------------------
def test_ff6_ff7_advisory_only_and_hub_clean_in_repo():
    report = af.run_fitness(only=["FF-6", "FF-7"])
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]
    fps = {f.fingerprint for f in report.findings}
    # INIT.md 樞紐 0 死連結（ff6-ok 或 ff6-hub-ok 其一），且無任何 ff6-hub-* warn
    assert "ff6-ok" in fps or "ff6-hub-ok" in fps
    assert not any(f.fingerprint.startswith("ff6-hub-") and f.severity == af.SEVERITY_WARN
                   for f in report.findings)


def test_ff8_repo_has_no_structural_fail():
    """現有 repo 的每條 active 規則都必須接上存在且含 def test_ 的 test_ref（硬不變量）。

    這是 FF-8 三道 structural 不變量的回歸守門：日後任何測試被改名/刪除而未同步
    規則 test_ref，或新增規則漏填 test_ref，此測試即紅，將 governance theater 擋在 CI。
    """
    report = af.run_fitness(only=["FF-8"])
    fails = [f for f in report.findings if f.severity == af.SEVERITY_FAIL]
    assert not fails, f"FF-8 structural 不變量破損：{[f.title for f in fails]}"


def test_ff8_repo_backref_converged():
    """R7 收斂後：現有 repo 全部 active 規則的強制測試均反向引用規則 id（ff8-ok）。"""
    report = af.run_fitness(only=["FF-8"])
    assert any(f.fingerprint == "ff8-ok" for f in report.findings), \
        "FF-8 反向引用未收斂；新增/修改規則時請於其 test_ref 測試加 `# enforces: <rule-id>`"


# ---------------------------------------------------------------------------
# FF-10：Governance 規則 trigger_states 可達性（死規則偵測，roadmap R8）
# ---------------------------------------------------------------------------
def _rules_dir(tmp_path, monkeypatch, *files):
    """於隔離 tmp 建構 GOV_RULES_DIR，寫入 (檔名, 內文) 規則。"""
    rules = tmp_path / "governance" / "rules"
    rules.mkdir(parents=True, exist_ok=True)
    for name, body in files:
        (rules / name).write_text(body, encoding="utf-8")
    monkeypatch.setattr(af, "GOV_RULES_DIR", rules)
    return rules


def test_ff10_ghost_trigger_fails(tmp_path, monkeypatch):
    """trigger 指向不存在於 FSM 宇宙的幽靈狀態 → structural fail（死規則）。"""
    _rules_dir(tmp_path, monkeypatch,
               ("R-X.yaml", "id: R-X\nmaturity: active\n"
                            "trigger_states:\n  - GHOST_NONEXISTENT_STATE\n"))
    report = af.FitnessReport()
    af.check_ff10_rule_trigger_reachability(report)
    assert any(f.fingerprint.startswith("ff10-ghost-") and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff10_empty_trigger_fails(tmp_path, monkeypatch):
    """trigger_states 為空 → structural fail（永不觸發）。"""
    _rules_dir(tmp_path, monkeypatch,
               ("R-Y.yaml", "id: R-Y\nmaturity: active\ntrigger_states: []\n"))
    report = af.FitnessReport()
    af.check_ff10_rule_trigger_reachability(report)
    assert any(f.fingerprint.startswith("ff10-empty-") and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff10_wildcard_and_real_states_pass(tmp_path, monkeypatch):
    """* 萬用 + 真實 canonical 狀態 → ff10-ok，無 fail。"""
    _rules_dir(tmp_path, monkeypatch,
               ("R-A.yaml", "id: R-A\nmaturity: active\ntrigger_states:\n  - '*'\n"),
               ("R-B.yaml", "id: R-B\nmaturity: active\n"
                            "trigger_states:\n  - IMPLEMENTATION\n  - PR_REVIEW\n"))
    report = af.FitnessReport()
    af.check_ff10_rule_trigger_reachability(report)
    assert any(f.fingerprint == "ff10-ok" for f in report.findings)
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]


def test_ff10_deprecated_rule_with_ghost_exempt(tmp_path, monkeypatch):
    """非 active 規則即使 trigger 含幽靈狀態也不報 fail（maturity 豁免）。"""
    _rules_dir(tmp_path, monkeypatch,
               ("R-Z.yaml", "id: R-Z\nmaturity: deprecated\n"
                            "trigger_states:\n  - GHOST_NONEXISTENT_STATE\n"))
    report = af.FitnessReport()
    af.check_ff10_rule_trigger_reachability(report)
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]


def test_ff10_repo_has_no_dead_rule():
    """現有 repo 全部 active 規則 trigger ⊆ FSM 宇宙（死規則回歸守門）。

    日後任何狀態被改名/移除而規則 trigger 未同步、或新增規則 trigger 打錯字，此測試即紅。
    """
    report = af.run_fitness(only=["FF-10"])
    fails = [f for f in report.findings if f.severity == af.SEVERITY_FAIL]
    assert not fails, f"FF-10 偵測到死規則：{[f.title for f in fails]}"
    assert any(f.fingerprint == "ff10-ok" for f in report.findings)


# ---------------------------------------------------------------------------
# FF-11：Skill frontmatter 結構完整性（roadmap R9）
# ---------------------------------------------------------------------------
def _skill(tmp_path, monkeypatch, name: str, skill_md: str | None):
    """於隔離 tmp 建一個 skill 目錄；skill_md=None 表示不建 SKILL.md。"""
    sk = tmp_path / ".claude" / "skills"
    d = sk / name
    d.mkdir(parents=True, exist_ok=True)
    if skill_md is not None:
        (d / "SKILL.md").write_text(skill_md, encoding="utf-8")
    monkeypatch.setattr(af, "SKILLS_DIR", sk)
    return sk


_GOOD_FM = "---\nname: foo\ndescription: 一個合法 skill\n---\n\n# Foo\n"


def test_ff11_missing_md_fails(tmp_path, monkeypatch):
    _skill(tmp_path, monkeypatch, "bar", None)
    report = af.FitnessReport()
    af.check_ff11_skill_frontmatter(report)
    assert any(f.fingerprint == "ff11-missing-md" and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff11_no_frontmatter_fails(tmp_path, monkeypatch):
    _skill(tmp_path, monkeypatch, "baz", "# baz Skill\n\n無 frontmatter 的純 markdown\n")
    report = af.FitnessReport()
    af.check_ff11_skill_frontmatter(report)
    assert any(f.fingerprint == "ff11-no-frontmatter" and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff11_missing_name_or_desc_fails(tmp_path, monkeypatch):
    _skill(tmp_path, monkeypatch, "qux", "---\ndescription: 有描述但無 name\n---\n")
    report = af.FitnessReport()
    af.check_ff11_skill_frontmatter(report)
    assert any(f.fingerprint == "ff11-no-name" and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff11_alias_name_not_flagged(tmp_path, monkeypatch):
    """name≠目錄名（刻意短別名）只要 frontmatter 完整就不得報 fail（防 12 假陽性回歸）。"""
    _skill(tmp_path, monkeypatch, "ba-analyst",
           "---\nname: ba-validate\ndescription: 短別名但結構完整\n---\n")
    report = af.FitnessReport()
    af.check_ff11_skill_frontmatter(report)
    assert any(f.fingerprint == "ff11-ok" for f in report.findings)
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]


def test_ff11_clean_passes(tmp_path, monkeypatch):
    _skill(tmp_path, monkeypatch, "foo", _GOOD_FM)
    report = af.FitnessReport()
    af.check_ff11_skill_frontmatter(report)
    assert any(f.fingerprint == "ff11-ok" for f in report.findings)


def test_ff11_repo_skill_frontmatter_intact():
    """R9 收斂後：現有 repo 全部 skill frontmatter 結構完整（ff11-ok，無 fail）。"""
    report = af.run_fitness(only=["FF-11"])
    fails = [f for f in report.findings if f.severity == af.SEVERITY_FAIL]
    assert not fails, f"FF-11 偵測到 skill frontmatter 缺陷：{[f.title for f in fails]}"
    assert any(f.fingerprint == "ff11-ok" for f in report.findings)


# ---------------------------------------------------------------------------
# FF-12：critical 規則治理錯置（severity↔trigger，roadmap R10）
# ---------------------------------------------------------------------------
def test_ff12_critical_observation_only_fails(tmp_path, monkeypatch):
    """critical 規則 trigger 全為觀測態 → structural fail（治理錯置）。"""
    obs = sorted(tr.OBSERVATION_STATES)
    _rules_dir(tmp_path, monkeypatch,
               ("R-M.yaml", f"id: R-M\nmaturity: active\nseverity: critical\n"
                            f"trigger_states:\n  - {obs[0]}\n"))
    report = af.FitnessReport()
    af.check_ff12_severity_placement(report)
    assert any(f.fingerprint.startswith("ff12-misplaced-") and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff12_critical_with_blocking_state_passes(tmp_path, monkeypatch):
    """critical 規則含一個非觀測（阻塞）狀態 → ff12-ok，無 fail。"""
    _rules_dir(tmp_path, monkeypatch,
               ("R-N.yaml", "id: R-N\nmaturity: active\nseverity: critical\n"
                            "trigger_states:\n  - ESCALATION\n"))
    report = af.FitnessReport()
    af.check_ff12_severity_placement(report)
    assert any(f.fingerprint == "ff12-ok" for f in report.findings)
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]


def test_ff12_critical_wildcard_passes(tmp_path, monkeypatch):
    """critical 規則用 * 萬用 → 可達阻塞點，不錯置。"""
    _rules_dir(tmp_path, monkeypatch,
               ("R-O.yaml", "id: R-O\nmaturity: active\nseverity: critical\n"
                            "trigger_states:\n  - '*'\n"))
    report = af.FitnessReport()
    af.check_ff12_severity_placement(report)
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]


def test_ff12_high_observation_only_not_flagged(tmp_path, monkeypatch):
    """非 critical（high）規則即使 observation-only 也不報——FF-12 只管 critical。"""
    obs = sorted(tr.OBSERVATION_STATES)
    _rules_dir(tmp_path, monkeypatch,
               ("R-P.yaml", f"id: R-P\nmaturity: active\nseverity: high\n"
                            f"trigger_states:\n  - {obs[0]}\n"))
    report = af.FitnessReport()
    af.check_ff12_severity_placement(report)
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]


def test_ff12_repo_no_misplaced_critical():
    """現有 repo 全部 critical 規則 trigger 落點正確（ff12-ok，無 fail）。"""
    report = af.run_fitness(only=["FF-12"])
    fails = [f for f in report.findings if f.severity == af.SEVERITY_FAIL]
    assert not fails, f"FF-12 偵測到 critical 規則錯置：{[f.title for f in fails]}"
    assert any(f.fingerprint == "ff12-ok" for f in report.findings)


# ---------------------------------------------------------------------------
# FF-13：Agent YAML schema 完整性（roadmap R11，advisory）
# ---------------------------------------------------------------------------
def _agent(tmp_path, monkeypatch, name: str, content: str):
    ad = tmp_path / "agent" / "core"
    ad.mkdir(parents=True, exist_ok=True)
    (ad / name).write_text(content, encoding="utf-8")
    monkeypatch.setattr(af, "AGENT_DIR", tmp_path / "agent")
    monkeypatch.setattr(af, "FRAMEWORK_ROOT", tmp_path)
    return tmp_path


def test_ff13_invalid_yaml_warns(tmp_path, monkeypatch):
    """非嚴格合法 YAML（mapping 內混入 sequence）→ advisory warn。"""
    _agent(tmp_path, monkeypatch, "bad-zh.yaml", "agent:\n  a: 1\n  - item\n")
    report = af.FitnessReport()
    af.check_ff13_agent_yaml_schema(report)
    assert any(f.fingerprint == "ff13-yaml-invalid" and f.severity == af.SEVERITY_WARN
               for f in report.findings)
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]


def test_ff13_missing_agent_key_warns(tmp_path, monkeypatch):
    """可解析但缺頂層 agent 鍵 → advisory warn。"""
    _agent(tmp_path, monkeypatch, "nokey-zh.yaml", "foo: bar\nbaz: 1\n")
    report = af.FitnessReport()
    af.check_ff13_agent_yaml_schema(report)
    assert any(f.fingerprint == "ff13-missing-agent-key" and f.severity == af.SEVERITY_WARN
               for f in report.findings)


def test_ff13_clean_passes(tmp_path, monkeypatch):
    _agent(tmp_path, monkeypatch, "ok-zh.yaml", "agent:\n  name: x\n  persona: y\n")
    report = af.FitnessReport()
    af.check_ff13_agent_yaml_schema(report)
    assert any(f.fingerprint == "ff13-ok" for f in report.findings)


def test_ff13_repo_advisory_only():
    """FF-13 在現有 repo 為 advisory-only：絕不產生 structural fail（設計不變量）。"""
    report = af.run_fitness(only=["FF-13"])
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]


# ---------------------------------------------------------------------------
# FF-9：Scaffold-ROI 代謝（roadmap R14）
# ---------------------------------------------------------------------------
_ROI0 = "scaffold_roi:\n  fire_count: 0\n  catch_count: 0\n  false_positive_count: 0\n"


def test_ff9_missing_roi_fails(tmp_path, monkeypatch):
    _rules_dir(tmp_path, monkeypatch, ("R-A.yaml", "id: R-A\nmaturity: active\n"))
    report = af.FitnessReport()
    af.check_ff9_scaffold_roi(report)
    assert any(f.fingerprint == "ff9-missing-roi" and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff9_malformed_roi_fails(tmp_path, monkeypatch):
    _rules_dir(tmp_path, monkeypatch,
               ("R-B.yaml", "id: R-B\nmaturity: active\nscaffold_roi:\n  fire_count: oops\n"
                            "  catch_count: 0\n  false_positive_count: 0\n"))
    report = af.FitnessReport()
    af.check_ff9_scaffold_roi(report)
    assert any(f.fingerprint == "ff9-malformed-roi" and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff9_stale_gate_closed_when_no_data(tmp_path, monkeypatch):
    """aggregate fire=0 < 門檻 → gate 關閉，0-fire 不報 stale，ff9-ok。"""
    _rules_dir(tmp_path, monkeypatch, ("R-C.yaml", "id: R-C\nmaturity: active\n" + _ROI0))
    report = af.FitnessReport()
    af.check_ff9_scaffold_roi(report)
    assert any(f.fingerprint == "ff9-ok" for f in report.findings)
    assert not [f for f in report.findings if f.severity != af.SEVERITY_INFO]


def test_ff9_stale_detected_when_gate_open(tmp_path, monkeypatch):
    """aggregate fire 達門檻時，0-fire 規則被標為過時鷹架候選（advisory）。"""
    monkeypatch.setattr(af, "FF9_STALE_MIN_AGGREGATE", 1)
    _rules_dir(tmp_path, monkeypatch,
               ("R-HOT.yaml", "id: R-HOT\nmaturity: active\nscaffold_roi:\n  fire_count: 5\n"
                              "  catch_count: 5\n  false_positive_count: 0\n"),
               ("R-COLD.yaml", "id: R-COLD\nmaturity: active\n" + _ROI0))
    report = af.FitnessReport()
    af.check_ff9_scaffold_roi(report)
    stale = [f for f in report.findings if f.fingerprint == "ff9-stale-scaffold"]
    assert stale and stale[0].severity == af.SEVERITY_WARN
    assert "R-COLD" in stale[0].evidence


def test_ff9_repo_no_structural_fail():
    """現有 repo 全部 active 規則 scaffold_roi 基座完整（ff9-ok，無 fail）。"""
    report = af.run_fitness(only=["FF-9"])
    fails = [f for f in report.findings if f.severity == af.SEVERITY_FAIL]
    assert not fails, f"FF-9 偵測到 scaffold_roi 基座問題：{[f.title for f in fails]}"
    assert any(f.fingerprint == "ff9-ok" for f in report.findings)


# ---------------------------------------------------------------------------
# FF-14：CI workflow → 工具模組引用一致性（roadmap R13）
# ---------------------------------------------------------------------------
def _workflows(tmp_path, monkeypatch, name: str, content: str):
    wd = tmp_path / ".github" / "workflows"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / name).write_text(content, encoding="utf-8")
    monkeypatch.setattr(af, "WORKFLOW_DIRS", [wd])
    monkeypatch.setattr(af, "FRAMEWORK_ROOT", tmp_path)
    return tmp_path


def test_ff14_missing_module_fails(tmp_path, monkeypatch):
    _workflows(tmp_path, monkeypatch, "ci.yml",
               "run: python -m tools.ghost_module --x\n")
    report = af.FitnessReport()
    af.check_ff14_workflow_module_refs(report)
    assert any(f.fingerprint.startswith("ff14-missing-") and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff14_external_tools_ignored(tmp_path, monkeypatch):
    """python -m pip / pytest 等外部工具不在 tools.* 命名空間 → 不檢查、不誤報。"""
    _workflows(tmp_path, monkeypatch, "ci.yml",
               "run: |\n  python -m pip install x\n  python -m pytest -q\n")
    report = af.FitnessReport()
    af.check_ff14_workflow_module_refs(report)
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]
    assert any(f.fingerprint == "ff14-no-refs" for f in report.findings)


def test_ff14_valid_module_passes(tmp_path, monkeypatch):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "foo.py").write_text("x = 1\n", encoding="utf-8")
    _workflows(tmp_path, monkeypatch, "ci.yml", "run: python -m tools.foo\n")
    report = af.FitnessReport()
    af.check_ff14_workflow_module_refs(report)
    assert any(f.fingerprint == "ff14-ok" for f in report.findings)
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]


def test_ff14_repo_refs_resolve():
    """現有 repo 的 CI workflow python -m tools.* 引用皆可解析（無 fail）。"""
    report = af.run_fitness(only=["FF-14"])
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]


# ---------------------------------------------------------------------------
# FF-15：docs_template 索引 ↔ 磁碟一致性（roadmap R15）
# ---------------------------------------------------------------------------
def _tpl(tmp_path, monkeypatch, claimed: int, rows, disk_files):
    """於隔離 tmp 建構 INIT.md「SDD 模板索引（claimed 個）」+ docs_template/sdd/ 磁碟樹。

    rows：[(category, filename), ...] 寫入索引表（反引號包裹檔名）。
    disk_files：[相對 sdd/ 的路徑, ...] 實際在磁碟建立的模板檔。
    """
    monkeypatch.setattr(af, "FRAMEWORK_ROOT", tmp_path)
    table = "\n".join(f"| **{c}** | `{fn}` | 用途 | All |" for c, fn in rows)
    (tmp_path / "AISDLC_SDD_INIT.md").write_text(
        f"# INIT\n\n## SDD 模板索引（{claimed} 個）\n\n"
        "### 完整模板清單\n\n| 分類 | 模板檔案 | 用途 | 適用場景 |\n|---|---|---|---|\n"
        f"{table}\n\n---\n\n## 下一節\n後略\n",
        encoding="utf-8",
    )
    sdd = tmp_path / "docs_template" / "sdd"
    for rel in disk_files:
        p = sdd / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# tpl\n", encoding="utf-8")
    monkeypatch.setattr(af, "DOCS_TEMPLATE_SDD_DIR", sdd)
    return tmp_path


def test_ff15_dangling_index_fails(tmp_path, monkeypatch):
    """索引引用磁碟不存在的模板 → structural fail（dangling = 場景複製靜默失敗）。"""
    _tpl(tmp_path, monkeypatch, claimed=1,
         rows=[("requirements", "GHOST-TEMPLATE.md")],
         disk_files=["requirements/REAL-TEMPLATE.md"])
    report = af.FitnessReport()
    af.check_ff15_docs_template_index(report)
    assert any(f.fingerprint == "ff15-dangling-index" and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff15_unindexed_drift_warns(tmp_path, monkeypatch):
    """磁碟有模板未被索引（且宣稱數 ≠ 磁碟）→ advisory warn，無 fail。"""
    _tpl(tmp_path, monkeypatch, claimed=1,
         rows=[("requirements", "A-TEMPLATE.md")],
         disk_files=["requirements/A-TEMPLATE.md", "testing/B-TEMPLATE.md"])
    report = af.FitnessReport()
    af.check_ff15_docs_template_index(report)
    drift = [f for f in report.findings if f.fingerprint == "ff15-index-drift"]
    assert drift and drift[0].severity == af.SEVERITY_WARN
    assert "B-TEMPLATE.md" in drift[0].evidence
    assert not [f for f in report.findings if f.severity == af.SEVERITY_FAIL]


def test_ff15_clean_passes(tmp_path, monkeypatch):
    """索引宣稱數 == 磁碟、全索引、全可解析 → ff15-ok，無任何非 info。"""
    _tpl(tmp_path, monkeypatch, claimed=2,
         rows=[("requirements", "A-TEMPLATE.md"), ("api", "C-TEMPLATE.yaml")],
         disk_files=["requirements/A-TEMPLATE.md", "api/C-TEMPLATE.yaml"])
    report = af.FitnessReport()
    af.check_ff15_docs_template_index(report)
    assert any(f.fingerprint == "ff15-ok" for f in report.findings)
    assert not [f for f in report.findings if f.severity != af.SEVERITY_INFO]


def test_ff15_section_bounded_by_next_level2_heading(tmp_path, monkeypatch):
    """section 邊界正確：下一個 level-2 標題後的反引號檔名不得被誤計入索引集合。"""
    monkeypatch.setattr(af, "FRAMEWORK_ROOT", tmp_path)
    (tmp_path / "AISDLC_SDD_INIT.md").write_text(
        "# INIT\n\n## SDD 模板索引（1 個）\n\n"
        "| 分類 | 模板檔案 |\n|---|---|\n| **requirements** | `A-TEMPLATE.md` |\n\n"
        "## 別節\n\n這裡有 `OUTSIDE-TEMPLATE.md` 不該被算進索引\n",
        encoding="utf-8",
    )
    sdd = tmp_path / "docs_template" / "sdd"
    (sdd / "requirements").mkdir(parents=True)
    (sdd / "requirements" / "A-TEMPLATE.md").write_text("# t\n", encoding="utf-8")
    monkeypatch.setattr(af, "DOCS_TEMPLATE_SDD_DIR", sdd)
    report = af.FitnessReport()
    af.check_ff15_docs_template_index(report)
    # OUTSIDE-TEMPLATE.md 在 section 外、也不在磁碟 → 不得觸發 dangling
    assert not any(f.fingerprint == "ff15-dangling-index" for f in report.findings)
    assert any(f.fingerprint == "ff15-ok" for f in report.findings)


def test_ff15_repo_no_dangling_index():
    """現有 repo 索引引用全部解析至磁碟（structural 回歸守門）。

    日後任何模板被改名/刪除而 INIT 索引未同步、或索引打錯字，此測試即紅。
    """
    report = af.run_fitness(only=["FF-15"])
    fails = [f for f in report.findings if f.severity == af.SEVERITY_FAIL]
    assert not fails, f"FF-15 偵測到 dangling 索引：{[f.title for f in fails]}"


def test_ff15_repo_index_converged():
    """R15 收斂後：現有 repo 模板索引與磁碟一致（ff15-ok）。

    新增/刪除 docs_template/sdd/ 模板時，請同步更新 INIT.md「SDD 模板索引（NN 個）」表與計數。
    """
    report = af.run_fitness(only=["FF-15"])
    assert any(f.fingerprint == "ff15-ok" for f in report.findings), \
        "FF-15 索引未收斂；請同步 INIT.md SDD 模板索引表與宣稱數至 docs_template/sdd/ 實況"


# ---------------------------------------------------------------------------
# FF-16：具身評估器 & 鷹架代謝工具鏈接地完整性（Phase X / roadmap R16）
# ---------------------------------------------------------------------------
def test_ff16_repo_structural_passes():
    """現有 repo：具身/代謝 agent 宣告的 runtime 模組 + FSM 狀態皆解析（綠燈鎖，無 fail）。

    日後 sandbox_runner / observability_query / output_quality_scorer / scaffold_gc 被改名/移除，
    或 EXECUTION_EVALUATION / SCAFFOLD_GC 從 transition_rules 消失而 agent 宣告未同步，此測試即紅。
    """
    report = af.run_fitness(only=["FF-16"])
    fails = [f for f in report.findings if f.severity == af.SEVERITY_FAIL]
    assert not fails, f"FF-16 偵測到具身/代謝工具鏈接地斷裂：{[f.title for f in fails]}"
    assert any(f.fingerprint == "ff16-ok" for f in report.findings)


def test_ff16_dangling_module_fails(monkeypatch):
    """agent 宣告不存在的 runtime 模組 → structural fail（governance-theater）。"""
    monkeypatch.setattr(af, "EMBODIED_AGENT_SPECS", (
        ("agent/specialized/sdd-evaluator-zh.yaml",
         ["tools.fsm_runtime.does_not_exist_xyz"], "EXECUTION_EVALUATION"),
    ))
    report = af.FitnessReport()
    af.check_ff16_embodied_evaluator_grounding(report)
    assert any(f.fingerprint.startswith("ff16-module-missing-") and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff16_missing_state_fails(monkeypatch):
    """agent 綁定的 FSM 狀態不存在於 canonical 宇宙 → structural fail。"""
    monkeypatch.setattr(af, "EMBODIED_AGENT_SPECS", (
        ("agent/specialized/sdd-evaluator-zh.yaml", [], "GHOST_STATE_XYZ"),
    ))
    report = af.FitnessReport()
    af.check_ff16_embodied_evaluator_grounding(report)
    assert any(f.fingerprint.startswith("ff16-state-missing-") and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff16_missing_agent_fails(monkeypatch):
    """宣告具身能力的 agent 檔缺失 → structural fail（能力無載入入口）。"""
    monkeypatch.setattr(af, "EMBODIED_AGENT_SPECS", (
        ("agent/specialized/nonexistent-agent-xyz.yaml", [], "EXECUTION_EVALUATION"),
    ))
    report = af.FitnessReport()
    af.check_ff16_embodied_evaluator_grounding(report)
    assert any(f.fingerprint.startswith("ff16-agent-missing-") and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff16_meta_loop_ungrounded_advisory(tmp_path, monkeypatch):
    """元迴圈生成器零引用具身工具鏈 → advisory warn（GAP-X1 未接地），無 fail 升級。"""
    monkeypatch.setattr(af, "FRAMEWORK_ROOT", tmp_path)
    (tmp_path / "gen.py").write_text("x = 1  # 純合成算子代數，無具身引用\n", encoding="utf-8")
    monkeypatch.setattr(af, "META_LOOP_GENERATOR_RELPATHS", ("gen.py",))
    report = af.FitnessReport()
    af.check_ff16_embodied_evaluator_grounding(report)
    ungrounded = [f for f in report.findings if f.fingerprint == "ff16-meta-loop-ungrounded"]
    assert ungrounded and ungrounded[0].severity == af.SEVERITY_WARN


def test_ff16_grounded_meta_loop_no_advisory(tmp_path, monkeypatch):
    """元迴圈生成器引用具身工具鏈 + GC 已產提案 → (B) 兩條 advisory 皆不 surface（乾淨案例）。

    亦守住「註解剝除」：comment-only 提及不算接地，真 import 才算。
    """
    monkeypatch.setattr(af, "FRAMEWORK_ROOT", tmp_path)
    (tmp_path / "gen.py").write_text(
        "from tools.fsm_runtime import sandbox_runner  # 已接地具身評估器\n", encoding="utf-8")
    monkeypatch.setattr(af, "META_LOOP_GENERATOR_RELPATHS", ("gen.py",))
    gc = tmp_path / "gc"
    gc.mkdir()
    (gc / "SCAFFOLD-ROI-2026-06-05.md").write_text("# 退役提案\n", encoding="utf-8")
    monkeypatch.setattr(af, "GC_REPORTS_DIR", gc)
    report = af.FitnessReport()
    af.check_ff16_embodied_evaluator_grounding(report)
    assert not any(f.fingerprint == "ff16-meta-loop-ungrounded" for f in report.findings)
    assert not any(f.fingerprint == "ff16-gc-never-fired" for f in report.findings)


def test_ff16_comment_only_reference_not_grounded(tmp_path, monkeypatch):
    """只在註解提及具身工具鏈（無真 import）→ 仍判未接地（防假陰性，QA MINOR 強化）。"""
    monkeypatch.setattr(af, "FRAMEWORK_ROOT", tmp_path)
    (tmp_path / "gen.py").write_text(
        "x = 1  # TODO: 未來或許接 sandbox_runner / observability_query\n", encoding="utf-8")
    monkeypatch.setattr(af, "META_LOOP_GENERATOR_RELPATHS", ("gen.py",))
    report = af.FitnessReport()
    af.check_ff16_embodied_evaluator_grounding(report)
    assert any(f.fingerprint == "ff16-meta-loop-ungrounded" for f in report.findings)


def test_ff16_gc_fired_no_advisory(tmp_path, monkeypatch):
    """build/reports/gc/ 有 SCAFFOLD-ROI 退役提案 → 不再 surface GC-never-fired advisory。"""
    gc = tmp_path / "gc"
    gc.mkdir()
    (gc / "SCAFFOLD-ROI-2026-06-05.md").write_text("# 退役提案\n", encoding="utf-8")
    monkeypatch.setattr(af, "GC_REPORTS_DIR", gc)
    report = af.FitnessReport()
    af.check_ff16_embodied_evaluator_grounding(report)
    assert not any(f.fingerprint == "ff16-gc-never-fired" for f in report.findings)


# ── FF-17：Copy-on-Evolve 演化版必納官方閘門（DEF-10-002b 固化）──────────────
# 雙軌 ci-gate 動態最新版偵測慣用語（DEF-03-001 修復落地碼的最小代表片段）。
_FF17_DUAL_TRACK_GATE = (
    'FROZEN_BASELINE="AISDLC_SDD_v0.01"\n'
    'LATEST="$(cd "${REPO_ROOT}" && ls -d AISDLC_SDD_v0.0* | sort -V | tail -1)"\n'
    'FW_VERSIONS=("${FROZEN_BASELINE}")\n'
    'FW_VERSIONS+=("${LATEST}")\n'
)


def _ff17_setup(tmp_path, monkeypatch, gate_text, versions=("AISDLC_SDD_v0.04",
                                                            "AISDLC_SDD_v0.05")):
    """佈署假 PROJECT_ROOT：版本目錄 + scripts/ci-gate.sh。"""
    for v in versions:
        (tmp_path / v).mkdir()
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    gate = scripts / "ci-gate.sh"
    if gate_text is not None:
        gate.write_text(gate_text, encoding="utf-8")
    monkeypatch.setattr(af, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(af, "CI_GATE_PATH", gate)


def test_ff17_real_repo_gate_covers_latest():
    """真 repo：官方 ci-gate.sh 雙軌動態涵蓋最新演化版 → 無 structural fail。"""
    report = af.run_fitness(only=["FF-17"])
    assert not report.fails, [f.title for f in report.fails]
    assert any(f.fingerprint == "ff17-ok" for f in report.findings)


def test_ff17_dual_track_passes(tmp_path, monkeypatch):
    """合成雙軌閘門（含四錨點）→ PASS，evidence 標出磁碟最新版。"""
    _ff17_setup(tmp_path, monkeypatch, _FF17_DUAL_TRACK_GATE)
    report = af.FitnessReport()
    af.check_ff17_evolution_version_gate_coverage(report)
    assert not report.fails
    ok = [f for f in report.findings if f.fingerprint == "ff17-ok"]
    assert ok and "AISDLC_SDD_v0.05" in ok[0].title  # 取磁碟語意最高版


# R10 DEF-101-133：LATEST 解析 SSOT 化（scripts/sdd_version.py）後的新慣用語。
# 真 repo 的 ci-gate.sh 已改走 SSOT——舊 glob 三錨點消失是刻意遷移非 DEF-03-001
# 回歸；checker 以 OR 語意同時接受兩種機制（舊 glob 保留給 downstream 舊拷貝）。
_FF17_SSOT_GATE = (
    'FROZEN_BASELINE="AISDLC_SDD_v0.01"\n'
    'LATEST="$(python "${REPO_ROOT}/scripts/sdd_version.py" || true)"\n'
    'FW_VERSIONS=("${FROZEN_BASELINE}")\n'
    'FW_VERSIONS+=("${LATEST}")\n'
)


def test_ff17_ssot_resolver_passes(tmp_path, monkeypatch):
    """R10：合成 SSOT 閘門（sdd_version.py 慣用語，無舊 glob 三錨點）→ PASS。

    WHY：ci-gate.sh 的 LATEST 解析已收斂至 scripts/sdd_version.py 單一真相源；
    若 checker 仍只認舊 glob，SSOT 遷移會被誤判為「退回靜態寫死」假紅
    （R10 ci-gate 首跑實證此假紅），意圖鎖必須隨機制升級。"""
    _ff17_setup(tmp_path, monkeypatch, _FF17_SSOT_GATE)
    report = af.FitnessReport()
    af.check_ff17_evolution_version_gate_coverage(report)
    assert not report.fails, [f.title for f in report.fails]
    ok = [f for f in report.findings if f.fingerprint == "ff17-ok"]
    assert ok and "AISDLC_SDD_v0.05" in ok[0].title


def test_ff17_ssot_without_append_still_fails(tmp_path, monkeypatch):
    """R10 反向鎖：有 SSOT 解析但缺 FW_VERSIONS 併入錨點 → 仍 structural fail
    （動態偵測與併入是兩個獨立必要條件，OR 只作用於偵測機制）。"""
    gate = (
        'FROZEN_BASELINE="AISDLC_SDD_v0.01"\n'
        'LATEST="$(python "${REPO_ROOT}/scripts/sdd_version.py" || true)"\n'
        'FW_VERSIONS=("${FROZEN_BASELINE}")\n'
    )
    _ff17_setup(tmp_path, monkeypatch, gate)
    report = af.FitnessReport()
    af.check_ff17_evolution_version_gate_coverage(report)
    assert any(f.fingerprint == "ff17-static-pin" for f in report.fails)


def test_ff17_hardcoded_single_version_fails(tmp_path, monkeypatch):
    """DEF-03-001 回歸：FW_DIR 寫死單版、無動態偵測 → structural fail（測試會紅）。"""
    _ff17_setup(tmp_path, monkeypatch,
                'FW_DIR="${REPO_ROOT}/AISDLC_SDD_v0.01"\n')  # 寫死，缺四錨點
    report = af.FitnessReport()
    af.check_ff17_evolution_version_gate_coverage(report)
    assert any(f.fingerprint == "ff17-static-pin" and f.severity == af.SEVERITY_FAIL
               for f in report.findings)


def test_ff17_missing_append_latest_fails(tmp_path, monkeypatch):
    """偵測到最新版卻未併入版本陣列（漏 FW_VERSIONS+=…LATEST）→ structural fail。"""
    partial = ('LATEST="$(ls -d AISDLC_SDD_v0.0* | sort -V | tail -1)"\n'
               'FW_VERSIONS=("AISDLC_SDD_v0.01")\n')  # 偵測到但未 append
    _ff17_setup(tmp_path, monkeypatch, partial)
    report = af.FitnessReport()
    af.check_ff17_evolution_version_gate_coverage(report)
    fail = [f for f in report.findings if f.fingerprint == "ff17-static-pin"]
    assert fail and any("FW_VERSIONS" in e for e in fail[0].evidence)


def test_ff17_no_gate_script_skips(tmp_path, monkeypatch):
    """官方閘門腳本不存在 → INFO 略過（非 fail，鏡像 FF-14 no-refs）。"""
    _ff17_setup(tmp_path, monkeypatch, gate_text=None)
    report = af.FitnessReport()
    af.check_ff17_evolution_version_gate_coverage(report)
    assert not report.fails
    assert any(f.fingerprint == "ff17-no-gate" for f in report.findings)


# ── W-20-2（DEF-19-002 通則化）：FF-17 接受去耦合的通則 glob，不再綁死 v0.0* 子串 ──
@pytest.mark.parametrize("glob_form", [
    "AISDLC_SDD_v0.0*",      # 原寫死形式（向後相容仍 PASS）
    "AISDLC_SDD_v0.[0-9]*",  # 去耦合通則：任一數字開頭
    "AISDLC_SDD_v0.[1-9]*",  # 去耦合通則：v0.10+ 十位數
    "AISDLC_SDD_v0.*",       # 去耦合通則：最寬
])
def test_ff17_accepts_generalized_glob(tmp_path, monkeypatch, glob_form):
    """improving_20 W-20-2：_CI_GATE_LATEST_GLOB_RE 由寫死 `v0.0*` 放寬為通則
    （v0.<glob>），使 ci-gate.sh 可清掉 `v0.0*` 子串改用 v0.[0-9]* / v0.* 仍通過 FF-17
    動態偵測守門——解除 DEF-19-002 揭露的子串耦合異味（improving_19 雙 glob 修復正是被此
    耦合逼著保留子串）。四種 glob 形式皆須命中（首字元 ∈ 數字 / `[` / `*`）。"""
    gate = (
        'FROZEN_BASELINE="AISDLC_SDD_v0.01"\n'
        f'LATEST="$(cd "${{REPO_ROOT}}" && ls -d {glob_form} | sort -V | tail -1)"\n'
        'FW_VERSIONS=("${FROZEN_BASELINE}")\n'
        'FW_VERSIONS+=("${LATEST}")\n'
    )
    _ff17_setup(tmp_path, monkeypatch, gate)
    report = af.FitnessReport()
    af.check_ff17_evolution_version_gate_coverage(report)
    assert not report.fails, [f.title for f in report.fails]
    assert any(f.fingerprint == "ff17-ok" for f in report.findings)
