"""/sdd/*：版本、FSM 狀態、規格編譯（唯讀；絕不寫進 AISDLC_SDD 樹）。

v1.5（BR-29）：`/sdd/compile` 的 `spec_file`／`fsm_project` 請求欄與 `spec_file`／`fsm_project`／
`frozen_digest`／`unmapped_at_ids`／`warnings` 回應欄、例外→HTTP 對映、`state_dir_not_ignored`。
呼叫約定（顯式傳 `fsm_project`、含空字串；`spec_file` 以絕對路徑傳入）用**替身 adapter** 斷言——
那是 Bridge 這一側的契約，不取決於 AutoClaude 的 adapter 長什麼樣；adapter 本身的行為
（選檔、摘要比對、unmapped）由 AutoClaude 的測試與 test_sdd_integration_parity.py 的整合測試守。
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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


# ── v1.5：`/sdd/compile` 的呼叫約定、回應欄、錯誤對映（以替身 adapter 斷言 Bridge 這一側） ──────
class FakeAdapter:
    """記錄建構與 `load_spec` 的呼叫；行為由類別屬性決定（回 spec 或丟例外）。"""

    instances: list[FakeAdapter] = []
    behavior: Any = None
    state_check_calls: int = 0

    def __init__(self, observability=None, *, fsm_state_path=None, test_path="tests",
                 fsm_project=None):
        self.fsm_project = fsm_project
        self.loads: list[tuple[str, str | None]] = []
        FakeAdapter.instances.append(self)

    def load_spec(self, spec_dir: str, spec_file: str | None = None):
        self.loads.append((spec_dir, spec_file))
        behavior = FakeAdapter.behavior
        if isinstance(behavior, Exception):
            raise behavior
        return behavior(spec_dir, spec_file) if callable(behavior) else behavior

    def compile_tasks(self, spec):
        return []


def _fake_spec(spec_path: Path, **over: Any) -> SimpleNamespace:
    fields: dict[str, Any] = {
        "spec_path": str(spec_path), "digest": "sha256:" + "a" * 64, "scenario": "greenfield",
        "contracts": (), "spec_format_version": "1.0", "fsm_project": "alpha",
        "frozen_digest_status": "verified", "unmapped_at_ids": ()}
    fields.update(over)
    return SimpleNamespace(**fields)


@pytest.fixture
def fake_adapter(monkeypatch: pytest.MonkeyPatch):
    FakeAdapter.instances = []
    FakeAdapter.behavior = None
    monkeypatch.setattr(
        "autoclaude.infra.adapters.sdd_to_playbook_adapter.SddToPlaybookAdapter", FakeAdapter)
    return FakeAdapter


@pytest.fixture
def spec_root(tmp_path: Path) -> Path:
    """`projects/specproj`：docs/contracts 下兩份 .md、build/reports/fsm 目錄（compile 靠它找專案
    根）。"""
    root = tmp_path / "projects" / "specproj"
    contracts = root / "docs" / "contracts"
    contracts.mkdir(parents=True)
    (contracts / "TCS-One.md").write_text("# one\n", encoding="utf-8")
    (contracts / "TCS-Two.md").write_text("# two\n", encoding="utf-8")
    (contracts / "notes.txt").write_text("not markdown\n", encoding="utf-8")
    (root / "build" / "reports" / "fsm").mkdir(parents=True)
    return root


def _compile(bridge, spec_root: Path, **body: Any):
    return bridge.client.post(
        "/sdd/compile", json={"spec_dir": str(spec_root / "docs" / "contracts"), **body})


def test_compile_always_passes_fsm_project_explicitly_even_when_the_request_omits_it(
        bridge, spec_root: Path, fake_adapter, monkeypatch: pytest.MonkeyPatch) -> None:
    """開發機匯出 SDD_PROJECT 是常態：Bridge 行程內呼叫 adapter 不得讓它讀到那個環境值——
    省略＝傳空字串（明確「不指定、不讀環境」），不是 None（None＝讀環境）。"""
    monkeypatch.setenv("SDD_PROJECT", "leaked-from-the-bridge-environment")
    fake_adapter.behavior = _fake_spec(spec_root / "docs" / "contracts" / "TCS-One.md")
    assert _compile(bridge, spec_root).status_code == 200
    assert fake_adapter.instances[-1].fsm_project == ""
    assert _compile(bridge, spec_root, fsm_project=None).status_code == 200
    assert fake_adapter.instances[-1].fsm_project == ""


def test_compile_sanitizes_the_requested_fsm_project_before_the_adapter_sees_it(
        bridge, spec_root: Path, fake_adapter) -> None:
    fake_adapter.behavior = _fake_spec(spec_root / "docs" / "contracts" / "TCS-One.md")
    for requested, key in (("Order: Sys", "Order_ Sys"), ("訂單系統 v2", "訂單系統 v2"),
                           ("alpha", "alpha"), ("a/b", "a_b"), ("..", "untitled")):
        assert _compile(bridge, spec_root, fsm_project=requested).status_code == 200
        assert fake_adapter.instances[-1].fsm_project == key, requested


def test_a_blank_fsm_project_is_refused_not_turned_into_untitled(
        bridge, spec_root: Path, fake_adapter) -> None:
    for blank in ("", "   "):
        resp = _compile(bridge, spec_root, fsm_project=blank)
        assert (resp.status_code, resp.json()["reason"]) == (422, "sanitization_failed")
        violation = resp.json()["violations"][0]
        assert violation == {"field": "fsm_project", "rule": "empty",
                             "message": violation["message"]}
    assert fake_adapter.instances == []


def test_compile_hands_the_adapter_an_absolute_spec_file_and_reports_it_relative(
        bridge, spec_root: Path, fake_adapter) -> None:
    contracts = (spec_root / "docs" / "contracts").resolve()
    picked = contracts / "TCS-Two.md"
    fake_adapter.behavior = _fake_spec(picked)
    resp = _compile(bridge, spec_root, spec_file="TCS-Two.md")
    assert resp.status_code == 200, resp.text
    assert fake_adapter.instances[-1].loads == [(str(contracts), str(picked))]
    assert resp.json()["spec_file"] == "TCS-Two.md", \
        "相對 spec_dir 的 POSIX 路徑（路徑 A 回填 sddSpecFile）"
    absolute = _compile(bridge, spec_root, spec_file=str(picked))
    assert absolute.status_code == 200 and fake_adapter.instances[-1].loads[0][1] == str(picked)
    assert _compile(bridge, spec_root).status_code == 200
    assert fake_adapter.instances[-1].loads[0][1] is None, "沒給 spec_file＝adapter 自己選檔"


@pytest.mark.parametrize(("spec_file", "status", "reason", "rule"), [
    ("../escape.md", 422, "sanitization_failed", "contains_dotdot"),
    ("sub/../../x.md", 422, "sanitization_failed", "contains_dotdot"),
    ("notes.txt", 422, "sanitization_failed", "not_markdown"),
    ("nope.md", 422, "spec_not_found", None),
    ("", 422, "sanitization_failed", "empty"),
])
def test_a_bad_spec_file_is_refused_before_any_adapter_call(
        spec_file: str, status: int, reason: str, rule: str | None, bridge, spec_root: Path,
        fake_adapter) -> None:
    resp = _compile(bridge, spec_root, spec_file=spec_file)
    assert (resp.status_code, resp.json()["reason"]) == (status, reason)
    if rule:
        violation = resp.json()["violations"][0]
        assert (violation["field"], violation["rule"]) == ("spec_file", rule)
    assert fake_adapter.instances == []


def test_an_absolute_spec_file_outside_spec_dir_is_refused(
        bridge, spec_root: Path, fake_adapter, tmp_path: Path) -> None:
    outside = tmp_path / "projects" / "other.md"
    outside.write_text("# other\n", encoding="utf-8")
    resp = _compile(bridge, spec_root, spec_file=str(outside))
    assert resp.json()["violations"][0]["rule"] == "outside_spec_dir"
    sibling = spec_root / "docs" / "elsewhere.md"                  # spec_dir 的兄弟目錄也不行
    sibling.write_text("# sibling\n", encoding="utf-8")
    assert _compile(bridge, spec_root, spec_file=str(sibling)).json()["violations"][0][
        "rule"] == "outside_spec_dir"
    assert fake_adapter.instances == []


def test_a_spec_file_symlink_that_points_outside_spec_dir_is_refused(
        bridge, spec_root: Path, fake_adapter, tmp_path: Path) -> None:
    outside = tmp_path / "projects" / "other.md"
    outside.write_text("# other\n", encoding="utf-8")
    link = spec_root / "docs" / "contracts" / "link.md"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("此環境無法建立 symlink（Windows 需開發人員模式或系統管理員）")
    resp = _compile(bridge, spec_root, spec_file="link.md")
    assert resp.json()["violations"][0]["rule"] == "outside_spec_dir"
    assert fake_adapter.instances == []


def test_the_response_carries_the_v15_binding_and_warning_fields(
        bridge, spec_root: Path, fake_adapter) -> None:
    picked = (spec_root / "docs" / "contracts" / "TCS-One.md").resolve()
    fake_adapter.behavior = _fake_spec(picked, unmapped_at_ids=("AT-009-1-1", "AT-14-1-1"),
                                       frozen_digest_status="absent", fsm_project="alpha")
    body = _compile(bridge, spec_root, fsm_project="alpha").json()
    assert body["spec_file"] == "TCS-One.md" and body["fsm_project"] == "alpha"
    assert body["frozen_digest"] == "absent"
    assert body["unmapped_at_ids"] == ["AT-009-1-1", "AT-14-1-1"], \
        "未編成的 AT 出聲：回 200、不是錯誤"
    assert body["spec_format_version"] == "1.0" and body["digest"].startswith("sha256:")
    assert isinstance(body["warnings"], list)
    assert body["tasks"] == [] and body["spec_path"] == str(picked)


def test_the_unmapped_list_is_always_present_and_empty_when_everything_compiled(
        bridge, spec_root: Path, fake_adapter) -> None:
    fake_adapter.behavior = _fake_spec(spec_root / "docs" / "contracts" / "TCS-One.md")
    body = _compile(bridge, spec_root).json()
    assert body["unmapped_at_ids"] == [] and body["frozen_digest"] == "verified"


def test_an_adapter_that_does_not_report_the_new_fields_degrades_safely(
        bridge, spec_root: Path, fake_adapter) -> None:
    """防禦性：adapter 回的 spec 缺新欄（比 ADR §11.1 舊的 adapter）：不宣稱已驗證（frozen_digest＝
    absent）、unmapped 為空、fsm_project 退回請求值——保守，不憑空捏造。"""
    old = _fake_spec(spec_root / "docs" / "contracts" / "TCS-One.md")
    for name in ("fsm_project", "frozen_digest_status", "unmapped_at_ids"):
        delattr(old, name)
    fake_adapter.behavior = old
    body = _compile(bridge, spec_root, fsm_project="Alpha Project").json()
    assert (body["frozen_digest"], body["unmapped_at_ids"], body["fsm_project"]) == (
        "absent", [], "Alpha Project")
    assert _compile(bridge, spec_root).json()["fsm_project"] is None


def _error_cases() -> list[tuple[Exception, int, str]]:
    from autoclaude.core.ports.spec_source import (
        SpecDigestMismatchError,
        SpecFormatVersionError,
        SpecNotFrozenError,
        SpecTaintedError,
    )

    return [
        (SpecDigestMismatchError("凍結後內容已變更"), 409, "spec_digest_changed"),
        (SpecNotFrozenError("未凍結"), 422, "spec_not_frozen"),
        (SpecTaintedError("汙染"), 422, "spec_tainted"),
        (SpecFormatVersionError("版本"), 422, "spec_format_version_unsupported"),
        (FileNotFoundError("找不到"), 422, "spec_not_found"),
        (ValueError("不唯一"), 422, "spec_ambiguous"),
    ]


@pytest.mark.parametrize("case", _error_cases(), ids=lambda c: type(c[0]).__name__)
def test_adapter_exceptions_map_to_the_documented_http_errors(
        case: tuple[Exception, int, str], bridge, spec_root: Path, fake_adapter) -> None:
    exc, status, reason = case
    fake_adapter.behavior = exc
    resp = _compile(bridge, spec_root)
    assert (resp.status_code, resp.json()["reason"]) == (status, reason)
    if status == 409:
        body = resp.json()
        assert body["pair"] == "frozen_vs_file" and body["detail"]["pair"] == "frozen_vs_file"
        assert "凍結後內容已變更" in body["detail"]["message"]
    else:
        assert str(exc) in resp.json()["detail"]


def test_a_digest_mismatch_is_409_and_never_the_422_of_an_unfrozen_spec(
        bridge, spec_root: Path, fake_adapter) -> None:
    """S7：同一個原因在三個預檢點用同一個 reason——「內容與凍結時不同」一律 409，不是 422。
    子類必須先接：`SpecDigestMismatchError` 是 `SpecNotFrozenError` 的子類。"""
    from autoclaude.core.ports.spec_source import SpecDigestMismatchError, SpecNotFrozenError

    assert issubclass(SpecDigestMismatchError, SpecNotFrozenError)
    fake_adapter.behavior = SpecDigestMismatchError("digest 不符")
    assert _compile(bridge, spec_root).status_code == 409
    fake_adapter.behavior = SpecNotFrozenError("狀態檔不唯一")
    assert _compile(bridge, spec_root).status_code == 422


def test_a_non_adapter_exception_is_not_swallowed(bridge, spec_root: Path, fake_adapter) -> None:
    fake_adapter.behavior = RuntimeError("some unrelated bug")
    resp = bridge.post_on_fresh_connection(
        "/sdd/compile", json={"spec_dir": str(spec_root / "docs" / "contracts")})
    assert resp.status_code == 500, "未知例外是 Bridge／adapter 的 bug，不能被包成合法的 422"


# ── state_dir_not_ignored（ADR §7.2 末列）：專案根是 git 工作樹而狀態目錄沒被忽略 ────────────────
def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.mark.skipif(shutil.which("git") is None, reason="需要 git")
def test_compile_warns_when_the_state_directory_is_not_git_ignored(
        bridge, spec_root: Path, fake_adapter) -> None:
    fake_adapter.behavior = _fake_spec(spec_root / "docs" / "contracts" / "TCS-One.md")
    assert _compile(bridge, spec_root).json()["warnings"] == [], \
        "不是 git 工作樹：只警告不擋，也不出聲"
    _git(spec_root, "init", "-q")
    warnings = _compile(bridge, spec_root).json()["warnings"]
    assert [w["code"] for w in warnings] == ["state_dir_not_ignored"]
    assert "build/reports/fsm" in warnings[0]["detail"]
    (spec_root / ".gitignore").write_text("build/reports/\n", encoding="utf-8")
    assert _compile(bridge, spec_root).json()["warnings"] == [], "已被忽略就不警告"


def test_a_missing_git_executable_just_skips_the_warning(
        bridge, spec_root: Path, fake_adapter, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_adapter.behavior = _fake_spec(spec_root / "docs" / "contracts" / "TCS-One.md")

    def no_git(*_a, **_k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", no_git)
    assert _compile(bridge, spec_root).json()["warnings"] == []
