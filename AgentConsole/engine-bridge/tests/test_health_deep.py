"""GET /health/deep（契約 v1.2 §3.1.1；QA DEF-AC-003）：200／503 的形狀與四項檢查各自的失敗路徑。

為什麼這支測試重要：DEF-AC-003 的本質是「映像缺 git，/health 卻永遠 200」——本機（有 git）、mock、
pytest 全綠，只有全棧真跑才現形。深度探針必須在 git 不在時回 503，且頂層 `reason` 與失敗項的
`reason` 都要讀得出是哪一項壞了；測試以 monkeypatch 讓 git 不存在，鎖住這條 fail-loud 路徑。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import replace
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


def test_all_checks_pass_returns_200_with_the_contract_shape(
        bridge, monkeypatch: pytest.MonkeyPatch) -> None:
    import autoclaude

    seen = _fake_git(monkeypatch, stdout="git version 2.39.5\n")
    resp = bridge.client.get("/health/deep")
    assert resp.status_code == 200
    assert resp.json() == {
        "status": "ok",
        "checks": {
            "git": {"ok": True, "version": "git version 2.39.5"},
            "autoclaude": {"ok": True, "version": autoclaude.__version__},
            "workspace": {"ok": True},
            "db": {"ok": None},         # 沒設 BRIDGE_DB_DSN ＝ 不做、不算失敗
        },
    }
    assert seen["argv"] == ["git", "--version"]
    assert seen["timeout"] == 5, "契約：git --version 逾時 5 秒"


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
    """`/health` 的形狀不動（console-api 的探測環吃它）；兩個端點都免認證。"""
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
