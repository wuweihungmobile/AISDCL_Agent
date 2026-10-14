"""/sdd/*：版本、FSM 狀態、規格編譯（唯讀；絕不寫進 AISDLC_SDD 樹）。"""
from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from app import security
from app.models import PlaybookIn
from app.settings import REPO_ROOT, discover_sdd_root

_SPEC_MD = """# Test Contract Specification — Demo

場景：brownfield 既有系統改進

## 1. AC → AT 映射表

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-001-1 | 登入成功 | AT-001-1-1 | 正常登入 | ✅ | Unit | □ |
| AC-001-1 | 登入成功 | AT-001-1-2 | 錯誤密碼 | ✅ | Integration | □ |
| AC-002-1 | 餘額警示 | AT-002-1-1 | 餘額不足提示 | ✅ | E2E | □ |

## 2. AT 格式

```gherkin
# AT-001-1-1
Scenario: 正常登入
  Given 使用者在登入頁面
  When 輸入正確帳密
  Then 回傳 201 Created
```

```gherkin
# AT-001-1-2
Scenario: 錯誤密碼
  Given 使用者在登入頁面
  When 輸入錯誤密碼
  Then 顯示錯誤訊息「餘額不足」
```

```gherkin
# AT-002-1-1
Scenario: 回應時間
  Given 系統在尖峰負載
  When 查詢餘額
  Then 回應時間 < 200ms
```
"""


def _numeric_latest(parent: Path) -> str:
    """獨立於產品碼的對照組：版本目錄名稱中的數字比大小。"""
    names = [p.name for p in parent.iterdir() if re.fullmatch(r"AISDLC_SDD_v\d+\.\d+", p.name)]
    return max(names, key=lambda n: tuple(int(x) for x in re.findall(r"\d+", n)))


def _write_fsm(root: Path, project: str = "demo", state: str = "IMPLEMENTATION",
               trace_len: int = 8, frozen: bool = True) -> Path:
    fsm_dir = root / "build" / "reports" / "fsm"
    fsm_dir.mkdir(parents=True, exist_ok=True)
    doc = {"fsm_state": {
        "project": project, "session_id": "sid-1", "current_state": state, "current_sprint": 2,
        "updated_at": "2026-10-14T00:00:00+00:00",
        "frozen_stages": [{"stage": "SCG-0"}] if frozen else [],
        "decision_trace": [{"ts": f"t{i}", "from": f"S{i}", "to": f"S{i + 1}", "reason": f"r{i}"}
                           for i in range(trace_len)]}}
    path = fsm_dir / f"FSM-STATE-{project}.yaml"
    path.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    return path


def _write_spec(root: Path, text: str = _SPEC_MD) -> Path:
    docs = root / "docs" / "03_testing" / "contracts"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "TEST-CONTRACT-SPEC-Demo.md").write_text(text, encoding="utf-8")
    return root / "docs"


def test_version_is_the_numerically_newest_directory_of_the_real_repo(bridge) -> None:
    resp = bridge.client.get("/sdd/version")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert re.fullmatch(r"AISDLC_SDD_v\d+\.\d+", body["latest"])
    assert body["latest"] == _numeric_latest(REPO_ROOT / "AISDLC_SDD")
    assert Path(body["root"]).is_absolute()
    assert Path(body["root"]).name == body["latest"]


def test_discovery_compares_version_numbers_not_strings(tmp_path: Path) -> None:
    for name in ("AISDLC_SDD_v0.9", "AISDLC_SDD_v0.30", "AISDLC_SDD_v0.29", "AISDLC_SDD_v0.100",
                 "AISDLC_SDD_notaversion", "other"):
        (tmp_path / name).mkdir()
    (tmp_path / "AISDLC_SDD_v9.99").write_text("file, not dir", encoding="utf-8")
    assert discover_sdd_root(tmp_path).name == "AISDLC_SDD_v0.100"
    assert discover_sdd_root(tmp_path / "missing") is None


def test_fsm_state_returns_current_state_and_the_last_five_decisions(
        make_bridge, settings, tmp_path) -> None:
    sdd = tmp_path / "AISDLC_SDD_v9.99"
    _write_fsm(sdd, trace_len=8)
    live = make_bridge(replace(settings, sdd_root=sdd))
    resp = live.client.get("/sdd/fsm/demo")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["current_state"] == "IMPLEMENTATION"
    assert [d["ts"] for d in body["decision_trace"]] == ["t3", "t4", "t5", "t6", "t7"]
    assert (body["project"], body["session_id"], body["current_sprint"]) == ("demo", "sid-1", 2)
    assert live.client.get("/sdd/version").json()["latest"] == "AISDLC_SDD_v9.99"


def test_unknown_or_malicious_project_names_are_404(make_bridge, settings, tmp_path) -> None:
    sdd = tmp_path / "AISDLC_SDD_v9.99"
    _write_fsm(sdd)
    live = make_bridge(replace(settings, sdd_root=sdd))
    for name in ("不存在", "nope", "..", "a%2Fb", "demo%00", "x" * 200):
        resp = live.client.get(f"/sdd/fsm/{name}")
        assert resp.status_code == 404, name
    assert live.client.get("/sdd/fsm/不存在").json()["reason"] == "fsm_not_found"


def test_a_symlinked_state_file_that_points_outside_is_not_served(
        make_bridge, settings, tmp_path) -> None:
    sdd = tmp_path / "AISDLC_SDD_v9.99"
    _write_fsm(sdd)
    secret = tmp_path / "elsewhere"
    secret.mkdir()
    (secret / "real.yaml").write_text("fsm_state: {current_state: LEAKED}", encoding="utf-8")
    link = sdd / "build" / "reports" / "fsm" / "FSM-STATE-evil.yaml"
    try:
        link.symlink_to(secret / "real.yaml")
    except (OSError, NotImplementedError):
        pytest.skip("此環境無法建立 symlink（Windows 需開發人員模式或系統管理員）")
    live = make_bridge(replace(settings, sdd_root=sdd))
    assert live.client.get("/sdd/fsm/evil").status_code == 404


def test_a_malformed_state_file_is_422_not_500(make_bridge, settings, tmp_path) -> None:
    sdd = tmp_path / "AISDLC_SDD_v9.99"
    path = _write_fsm(sdd)
    path.write_text("this: [is: not valid yaml", encoding="utf-8")
    live = make_bridge(replace(settings, sdd_root=sdd))
    assert live.client.get("/sdd/fsm/demo").status_code == 422


def test_without_an_sdd_tree_version_and_fsm_say_503_and_health_says_not_ok(
        make_bridge, settings, tmp_path) -> None:
    live = make_bridge(replace(settings, sdd_root=None))
    for url in ("/sdd/version", "/sdd/fsm/demo"):
        assert live.client.get(url).status_code == 503
    health = live.client.get("/health").json()
    assert health["status"] == "ok", "Bridge 本身活著；引擎狀態看 engines.*.ok"
    assert health["engines"]["sdd"]["ok"] is False
    # 規格編譯用的是 AutoClaude 的 adapter，不讀 SDD 目錄：沒有 SDD_ROOT 時照常運作。
    root = tmp_path / "projects" / "nosdd"
    root.mkdir()
    spec_dir = _write_spec(root)
    _write_fsm(root)
    assert live.client.post("/sdd/compile", json={"spec_dir": str(spec_dir)}).status_code == 200


def test_compile_turns_a_frozen_spec_into_playbook_tasks(
        bridge, tmp_path, project_dir) -> None:
    root = tmp_path / "projects" / "frozen"
    root.mkdir()
    spec_dir = _write_spec(root)
    _write_fsm(root)
    resp = bridge.client.post("/sdd/compile", json={"spec_dir": str(spec_dir)})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["scenario"] == "brownfield"
    assert [t["step_id"] for t in body["tasks"]] == [
        "sdd-brownfield-at-001-1-1", "sdd-brownfield-at-001-1-2", "sdd-brownfield-at-002-1-1"]
    assert [c["at_id"] for c in body["contracts"]] == ["AT-001-1-1", "AT-001-1-2", "AT-002-1-1"]
    assert body["digest"].startswith("sha256:")
    # 編譯結果必須能原樣餵回 POST /runs，且 adapter 產生的指令要通過 Bridge 自己的消毒閘。
    playbook = PlaybookIn.model_validate({"project": "sdd-demo", "tasks": body["tasks"]})
    assert security.validate_playbook(playbook) == []
    assert all(t["evaluator_command"].startswith("pytest ") for t in body["tasks"])


def test_compile_refuses_unfrozen_specs_and_bad_inputs(bridge, tmp_path) -> None:
    root = tmp_path / "projects" / "drafting"
    root.mkdir()
    spec_dir = _write_spec(root)
    _write_fsm(root, state="SPEC_DRAFTING", frozen=False)
    unfrozen = bridge.client.post("/sdd/compile", json={"spec_dir": str(spec_dir)})
    assert (unfrozen.status_code, unfrozen.json()["reason"]) == (422, "spec_not_frozen")

    no_fsm = tmp_path / "projects" / "nofsm"
    no_fsm.mkdir()
    resp = bridge.client.post("/sdd/compile", json={"spec_dir": str(_write_spec(no_fsm))})
    assert resp.json()["reason"] == "spec_not_frozen"

    empty = tmp_path / "projects" / "empty"
    empty.mkdir()
    missing = bridge.client.post("/sdd/compile", json={"spec_dir": str(empty)})
    assert (missing.status_code, missing.json()["reason"]) == (422, "spec_not_found")

    outside = bridge.client.post("/sdd/compile", json={"spec_dir": str(tmp_path)})
    assert outside.status_code == 422
    assert outside.json()["violations"][0]["rule"] == "outside_allowed_roots"
    relative = bridge.client.post("/sdd/compile", json={"spec_dir": "docs"})
    assert relative.json()["violations"][0]["rule"] == "not_absolute"


def test_compile_refuses_an_unsupported_spec_format_version(bridge, tmp_path) -> None:
    root = tmp_path / "projects" / "future"
    root.mkdir()
    spec_dir = _write_spec(root, _SPEC_MD + "\nspec-format-version: 9.9\n")
    _write_fsm(root)
    resp = bridge.client.post("/sdd/compile", json={"spec_dir": str(spec_dir)})
    assert (resp.status_code, resp.json()["reason"]) == (422, "spec_format_version_unsupported")


def test_the_sdd_endpoints_never_write_into_the_sdd_tree(bridge, tmp_path) -> None:
    root = Path(bridge.client.get("/sdd/version").json()["root"])
    before = {p: p.stat().st_mtime_ns for p in (root / "build" / "reports" / "fsm").glob("*.yaml")}
    bridge.client.get("/sdd/fsm/AISDLC_SDD")
    bridge.client.get("/sdd/fsm/不存在")
    after = {p: p.stat().st_mtime_ns for p in (root / "build" / "reports" / "fsm").glob("*.yaml")}
    assert before == after
