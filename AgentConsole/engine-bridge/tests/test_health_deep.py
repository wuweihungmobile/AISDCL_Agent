"""GET /health/deep（契約 v1.2 §3.1.1；QA DEF-AC-003）：200／503 的形狀與各項檢查（git、autoclaude、
workspace、db 決定 200／503；W7 D-17 加的 sdd 只當資訊、不影響判定）各自的失敗路徑。

為什麼這支測試重要：DEF-AC-003 的本質是「映像缺 git，/health 卻永遠 200」——本機（有 git）、mock、
pytest 全綠，只有全棧真跑才現形。深度探針必須在 git 不在時回 503，且頂層 `reason` 與失敗項的
`reason` 都要讀得出是哪一項壞了；測試以 monkeypatch 讓 git 不存在，鎖住這條 fail-loud 路徑。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

import app.health as health


class FakeDb:
    """只實作 `ping()`（/health/deep 對 DB 唯一的要求）。"""

    def __init__(self, result: bool | Exception) -> None:
        self._result = result

    def ping(self) -> bool:
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def _fake_git(monkeypatch: pytest.MonkeyPatch, *, stdout: str = "git version 9.9.9\n",
              stderr: str = "", rc: int = 0, exc: Exception | None = None) -> dict[str, Any]:
    """換掉 `subprocess.run`（只在這支測試的期間）；回傳被呼叫時看到的 argv／kwargs。"""
    seen: dict[str, Any] = {}

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen["argv"] = argv
        seen.update(kwargs)
        if exc is not None:
            raise exc
        return subprocess.CompletedProcess(argv, rc, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(health.subprocess, "run", fake_run)
    return seen


def _sdd_tree(parent: Path, name: str = "AISDLC_SDD_v9.99", *, fsm_dir: bool = False,
              marker: bool = False) -> Path:
    root = parent / name
    root.mkdir(parents=True)
    if fsm_dir:
        (root / "build" / "reports" / "fsm").mkdir(parents=True)
    if marker:
        (root / "AISDLC_SDD_INIT.md").write_text("# 框架入口\n", encoding="utf-8")
    return root


def test_all_checks_pass_returns_200_with_the_contract_shape(
        make_bridge, settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import autoclaude

    # 用合成的 SDD 樹：預設設定會去找 monorepo 裡真的那一份，期望值就會隨機器而異。
    sdd = _sdd_tree(tmp_path, fsm_dir=True)
    live = make_bridge(replace(settings, sdd_root=sdd))
    seen = _fake_git(monkeypatch, stdout="git version 2.39.5\n")
    resp = live.client.get("/health/deep")
    assert resp.status_code == 200
    assert resp.json() == {
        "status": "ok",
        "checks": {
            "git": {"ok": True, "version": "git version 2.39.5"},
            "autoclaude": {"ok": True, "version": autoclaude.__version__},
            "workspace": {"ok": True},
            "db": {"ok": None},         # 沒設 BRIDGE_DB_DSN ＝ 不做、不算失敗
            "sdd": {"ok": True, "latest": "AISDLC_SDD_v9.99"},
        },
    }
    assert seen["argv"] == ["git", "--version"]
    assert seen["timeout"] == 5, "契約：git --version 逾時 5 秒"


# ── D-17：sdd 檢查（三態：沒設＝null、有效＝true、無效＝false；只當資訊，不影響 200／503）──
def test_an_unset_sdd_root_is_null_and_does_not_fail_the_probe(
        make_bridge, settings, monkeypatch: pytest.MonkeyPatch) -> None:
    live = make_bridge(replace(settings, sdd_root=None))
    _fake_git(monkeypatch)
    resp = live.client.get("/health/deep")
    assert resp.status_code == 200, "沒有 SDD 目錄不算失敗：Bridge 照樣能跑 AutoClaude 的批次"
    body = resp.json()
    assert body["status"] == "ok"
    sdd = body["checks"]["sdd"]
    assert (sdd["ok"], sdd["latest"]) == (None, None)
    assert "SDD_ROOT" in sdd["reason"]


def test_a_valid_sdd_tree_reports_ok_with_the_directory_name(
        make_bridge, settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_git(monkeypatch)
    sdd = _sdd_tree(tmp_path, "AISDLC_SDD_v1.23", fsm_dir=True, marker=True)
    live = make_bridge(replace(settings, sdd_root=sdd))
    resp = live.client.get("/health/deep")
    assert resp.status_code == 200
    assert resp.json()["checks"]["sdd"] == {"ok": True, "latest": "AISDLC_SDD_v1.23"}


def test_a_fresh_clone_has_no_fsm_directory_but_the_entry_document_proves_the_tree(
        make_bridge, settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """build/reports/ 被 git 忽略，全新 clone 沒有 fsm 目錄：入口文件才是「樹有沒有掛上」的證據。
    判 false 的話，Console 的 SDD 卡會對一份完好的全新 clone 顯示失敗。"""
    _fake_git(monkeypatch)
    sdd = _sdd_tree(tmp_path, marker=True)
    live = make_bridge(replace(settings, sdd_root=sdd))
    resp = live.client.get("/health/deep")
    assert resp.status_code == 200, resp.text
    assert resp.json()["checks"]["sdd"] == {"ok": True, "latest": "AISDLC_SDD_v9.99"}


@pytest.fixture
def bad_sdd_roots(tmp_path: Path) -> dict[str, Path]:
    """三種 `sdd.ok` 為 false 的情形：不存在、是檔案、空目錄（compose 的唯讀掛載沒掛到東西時
    Docker 會替不存在的 bind 來源建一個空目錄，目錄名是掛載點的 `sdd`）。"""
    a_file = tmp_path / "AISDLC_SDD_v9.97"
    a_file.write_text("not a directory", encoding="utf-8")
    return {"missing": tmp_path / "AISDLC_SDD_v0.0-missing", "file": a_file,
            "empty": _sdd_tree(tmp_path, "sdd")}


@pytest.mark.parametrize("kind", ["missing", "file", "empty"])
def test_sdd_false_alone_keeps_the_overall_verdict_ok(
        kind: str, bad_sdd_roots: dict[str, Path], make_bridge, settings,
        monkeypatch: pytest.MonkeyPatch) -> None:
    """契約 v1.4 §3.1.1（主控裁定）：`sdd` 只當資訊。SDD 是選用引擎，它壞了要顯示在 Console 的
    SDD 卡，不該讓整體 503——console-api 的探測環與 compose 的 healthcheck 都打這一支，503 會被
    當成 Bridge／Agent 不可用（可用率下降、誤報 AGENT_UNRESPONSIVE）。"""
    _fake_git(monkeypatch)
    live = make_bridge(replace(settings, sdd_root=bad_sdd_roots[kind]))
    live.app.state.db = FakeDb(True)                       # 其餘四項全都健康，包括有設 DB
    resp = live.client.get("/health/deep")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok" and "reason" not in body
    assert body["checks"]["sdd"]["ok"] is False, "失敗照樣如實回報在 checks.sdd"
    assert [body["checks"][name]["ok"] for name in ("git", "autoclaude", "workspace", "db")] \
        == [True, True, True, True]


def test_a_false_sdd_check_says_what_is_wrong(
        bad_sdd_roots: dict[str, Path], make_bridge, settings,
        monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_git(monkeypatch)

    def sdd_of(kind: str) -> dict[str, Any]:
        live = make_bridge(replace(settings, sdd_root=bad_sdd_roots[kind]))
        return live.client.get("/health/deep").json()["checks"]["sdd"]

    for kind in ("missing", "file"):
        assert sdd_of(kind) == {"ok": False, "latest": None,
                                "reason": f"SDD_ROOT 不是目錄：{bad_sdd_roots[kind].name}"}
    empty = sdd_of("empty")
    assert (empty["ok"], empty["latest"]) == (False, "sdd")
    assert "AISDLC_SDD_INIT.md" in empty["reason"] and "build/reports/fsm" in empty["reason"]


def test_a_false_sdd_check_never_enters_the_503_reason_of_another_failure(
        bad_sdd_roots: dict[str, Path], make_bridge, settings,
        monkeypatch: pytest.MonkeyPatch) -> None:
    """判定與頂層 `reason` 只看前四項：git 與 db 壞了仍是 503，`reason` 只列這兩項，不夾帶 sdd。"""
    _fake_git(monkeypatch, exc=FileNotFoundError("git"))
    live = make_bridge(replace(settings, sdd_root=bad_sdd_roots["empty"]))
    live.app.state.db = FakeDb(False)
    resp = live.client.get("/health/deep")
    assert resp.status_code == 503
    body = resp.json()
    assert body["reason"] == "git: 找不到 git 執行檔；db: DB 無法連線（SELECT 1 失敗）"
    assert "sdd" not in body["reason"]
    failed = [name for name, check in body["checks"].items() if check["ok"] is False]
    assert failed == ["git", "db", "sdd"], "sdd 的失敗仍如實列在 checks 裡"


@pytest.mark.skipif(shutil.which("git") is None, reason="這台機器的 PATH 上沒有 git")
def test_the_real_git_subprocess_runs_on_this_platform(bridge) -> None:
    """不換掉 subprocess：真的 spawn 一次 git（含 Windows 的 creationflags 路徑）。"""
    resp = bridge.client.get("/health/deep")
    assert resp.status_code == 200, resp.text
    git = resp.json()["checks"]["git"]
    assert git["ok"] is True and git["version"].startswith("git version ")


def test_missing_git_degrades_to_503_and_names_the_failing_check(
        bridge, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_git(monkeypatch, exc=FileNotFoundError(2, "No such file or directory: 'git'"))
    resp = bridge.client.get("/health/deep")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["reason"] == "git: 找不到 git 執行檔"
    assert body["checks"]["git"] == {"ok": False, "reason": "找不到 git 執行檔"}
    # 其餘項目照常回報（失敗不遮蔽其他項目的真實狀態）
    assert body["checks"]["autoclaude"]["ok"] is True
    assert body["checks"]["workspace"] == {"ok": True}
    assert body["checks"]["db"] == {"ok": None}


def test_a_hanging_git_is_reported_as_a_timeout(
        bridge, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_git(monkeypatch, exc=subprocess.TimeoutExpired(cmd="git", timeout=5))
    resp = bridge.client.get("/health/deep")
    assert resp.status_code == 503
    assert resp.json()["checks"]["git"] == {"ok": False, "reason": "git --version 逾時（5 秒）"}


def test_a_git_that_exits_nonzero_degrades(bridge, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_git(monkeypatch, stdout="", stderr="fatal: bad things", rc=128)
    resp = bridge.client.get("/health/deep")
    assert resp.status_code == 503
    reason = resp.json()["checks"]["git"]["reason"]
    assert "128" in reason and "fatal: bad things" in reason


def test_a_git_that_prints_nothing_degrades_even_with_exit_zero(
        bridge, monkeypatch: pytest.MonkeyPatch) -> None:
    """沒有版本字串＝這不是一個能用的 git（例如被換成空殼）：不能因為 rc=0 就放行。"""
    _fake_git(monkeypatch, stdout="  \n", rc=0)
    assert bridge.client.get("/health/deep").status_code == 503


def test_an_unwritable_workspace_degrades(
        make_bridge, settings, monkeypatch: pytest.MonkeyPatch) -> None:
    """工作區在啟動後消失（卷被卸掉、磁碟換新）→ 引擎寫不出檔，必須在探針就現形。"""
    live = make_bridge()
    _fake_git(monkeypatch)
    shutil.rmtree(settings.engine_workspace)
    resp = live.client.get("/health/deep")
    assert resp.status_code == 503
    body = resp.json()
    assert body["checks"]["workspace"]["ok"] is False
    assert body["reason"].startswith("workspace: 工作區不可寫")


def test_an_engine_that_cannot_be_imported_degrades(
        bridge, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_git(monkeypatch)
    monkeypatch.setitem(sys.modules, "autoclaude", None)     # 令 `import autoclaude` 拋 ImportError
    resp = bridge.client.get("/health/deep")
    assert resp.status_code == 503
    check = resp.json()["checks"]["autoclaude"]
    assert check["ok"] is False and check["reason"].startswith("無法匯入 autoclaude")


def test_the_db_check_pings_only_when_a_dsn_is_configured(
        bridge, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_git(monkeypatch)
    bridge.app.state.db = FakeDb(True)            # 模擬 DB 模式（app.state.db 有值＝設了 DSN）
    ok = bridge.client.get("/health/deep")
    assert ok.status_code == 200 and ok.json()["checks"]["db"] == {"ok": True}

    bridge.app.state.db = FakeDb(False)
    down = bridge.client.get("/health/deep")
    assert down.status_code == 503
    assert down.json()["reason"] == "db: DB 無法連線（SELECT 1 失敗）"
    assert down.json()["checks"]["db"]["ok"] is False

    bridge.app.state.db = FakeDb(RuntimeError("boom"))
    broken = bridge.client.get("/health/deep")
    assert broken.status_code == 503, "探針自己不得拋例外（那會變 500，編排層看不出是哪一項）"
    assert "boom" in broken.json()["checks"]["db"]["reason"]


def test_an_unreachable_database_degrades_through_the_real_ping(
        make_bridge, settings, monkeypatch: pytest.MonkeyPatch) -> None:
    """不換掉 BridgeDb：DSN 指向沒人聽的埠，走真實的連線池與 ping（約 3 秒逾時）。"""
    _fake_git(monkeypatch)
    live = make_bridge(replace(settings, db_dsn="postgresql://nobody@127.0.0.1:1/none"))
    resp = live.client.get("/health/deep")
    assert resp.status_code == 503
    body = resp.json()
    assert body["checks"]["db"] == {"ok": False, "reason": "DB 無法連線（SELECT 1 失敗）"}
    assert body["reason"] == "db: DB 無法連線（SELECT 1 失敗）"
    assert body["checks"]["git"]["ok"] is True and body["checks"]["workspace"] == {"ok": True}


def test_several_failures_are_joined_with_a_fullwidth_semicolon(
        bridge, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_git(monkeypatch, exc=FileNotFoundError("git"))
    bridge.app.state.db = FakeDb(False)
    resp = bridge.client.get("/health/deep")
    assert resp.status_code == 503
    body = resp.json()
    assert body["reason"] == "git: 找不到 git 執行檔；db: DB 無法連線（SELECT 1 失敗）"
    failed = [name for name, check in body["checks"].items() if check["ok"] is False]
    assert failed == ["git", "db"]
    assert all("reason" in body["checks"][name] for name in failed), "失敗項各自附 reason"


def test_the_shallow_health_endpoint_is_unchanged_and_the_deep_one_needs_no_auth(
        bridge, monkeypatch: pytest.MonkeyPatch) -> None:
    """`/health` 的形狀不動（淺探測仍是 `healthCheckPath` 的合法設定值）；兩個端點都免認證。"""
    _fake_git(monkeypatch, exc=FileNotFoundError("git"))
    shallow = bridge.client.get("/health")
    assert shallow.status_code == 200, "git 不在時淺探測仍 200——這正是深度探針存在的理由"
    assert set(shallow.json()) == {"status", "bridge_instance", "engines", "db", "workspace"}
    assert bridge.client.get("/health/deep").status_code == 503


def test_workspace_probe_leaves_no_temp_file_behind(
        bridge, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_git(monkeypatch)
    for _ in range(3):
        assert bridge.client.get("/health/deep").status_code == 200
    leftovers = [p.name for p in bridge.settings.engine_workspace.iterdir()
                 if p.name.startswith(".health-")]
    assert leftovers == [], "建立後必須刪除，否則每 15 秒一次的 healthcheck 會把工作區塞滿"
