"""tests/tools/test_local_ci_gate.py — 本機 CI 閘門 Python 核心單元測試。

R12 ARCH-R12-1（DEF-101-070 ② 收斂案）配套：local_ci_gate.{sh,ps1} 雙實作收斂為
「Python 單核心 + 兩支薄殼」後，gate 語意的回歸鎖住在本檔（薄殼另由 monorepo 根
tools/check_wrapper_thinness.py hash 釘選守門）。

涵蓋 case（全程 mock 子行程，不真跑任何 gate）：
    (a) gate 清單與順序為凍結介面（含 --pg / --act 附加順序：PG 先於 act）
    (b) 任一 gate 失敗 → main rc=1 + 總結列 FAIL + ❌ 字樣
    (c) 位置參數整批取代預設 pytest 參數（--act/--pg 旗標可混雜任意位置）
    (d) --act 平台分派（POSIX bash 載具 vs Windows PowerShell 載具 -File）
    (e) --pg：alembic 失敗 → 清理容器（down -v）+ gate FAIL；compose up 失敗不跑 alembic
    (f) hooks liveness advisory 失敗（rc!=0 / 例外）不影響閘門結果
    (g) gate 執行拋例外（FileNotFoundError 等）→ 判 FAIL 不炸（對齊 .ps1 try/catch）
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import local_ci_gate as m  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_process_state():
    """main() 會 os.chdir(REPO_ROOT) 並設 PYTHONUTF8 且不還原（載具行程生命週期短，
    設計如此）；測試層快照還原，防自 monorepo 根聚合收集時的 cwd/env 汙染
    （R12 QA 一審 QA-3 附帶／SD 一審 SD-5）。"""
    prev_cwd = os.getcwd()
    prev_utf8 = os.environ.get("PYTHONUTF8")
    yield
    os.chdir(prev_cwd)
    if prev_utf8 is None:
        os.environ.pop("PYTHONUTF8", None)
    else:
        os.environ["PYTHONUTF8"] = prev_utf8

# 凍結的 gate 名稱與順序（呼叫端 / smoke / 文件比對這些字樣——改名即破壞相容）
_BASE_GATES = [
    "editable sentinel",
    "LOC budget",
    "CLAUDE.md <=400",
    "CLAUDE.md line<=800",
    "snapshot --check",
    "import-linter",
    "pytest",
]

_ALL_GATE_FUNCS = (
    "gate_editable",
    "gate_loc",
    "gate_claudemd",
    "gate_claudemd_line",
    "gate_snapshot",
    "gate_importlinter",
    "gate_pytest",
    "gate_pg",
    "gate_act",
)


def _mock_all_gates(monkeypatch: pytest.MonkeyPatch, rc: int = 0, **overrides) -> None:
    """把所有 gate 換成固定 rc 的假實作（gate_pytest 帶參數，簽名對齊）。"""
    for name in _ALL_GATE_FUNCS:
        target_rc = overrides.get(name, rc)
        if name == "gate_pytest":
            monkeypatch.setattr(m, name, lambda _args, _rc=target_rc: _rc)
        else:
            monkeypatch.setattr(m, name, lambda _rc=target_rc: _rc)


def _silence_liveness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(m, "_hooks_liveness_advisory", lambda: None)


# --- (a) gate 清單與順序 ---

def test_gate_list_and_order_frozen() -> None:
    names = [name for name, _ in m.build_gates(False, False, list(m.DEFAULT_PYTEST_ARGS))]
    assert names == _BASE_GATES


def test_optional_gates_appended_pg_before_act() -> None:
    names = [name for name, _ in m.build_gates(True, True, [])]
    assert names == _BASE_GATES + ["PG contract (pg17)", "act CI (Linux test job)"]


def test_pg_only_appends_single_gate() -> None:
    names = [name for name, _ in m.build_gates(False, True, [])]
    assert names == _BASE_GATES + ["PG contract (pg17)"]


# --- (b) 任一 gate 失敗 → exit 1 + 總結列 FAIL ---

def test_single_gate_failure_yields_rc1_and_fail_row(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _mock_all_gates(monkeypatch, rc=0, gate_snapshot=1)
    _silence_liveness(monkeypatch)
    rc = m.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "========== 本機 CI 閘門總結 ==========" in out
    assert f"  {'snapshot --check':<22} FAIL" in out
    assert f"  {'pytest':<22} PASS" in out
    assert "❌ 1 項失敗 — 請於本機修復後再 push。" in out


def test_all_green_yields_rc0_and_push_ok(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _mock_all_gates(monkeypatch, rc=0)
    _silence_liveness(monkeypatch)
    rc = m.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "✅ 全部通過 — 可安全 push。" in out
    # 每個 gate 都有執行標頭與 PASS 行（rc 字樣照收斂前格式）
    for name in _BASE_GATES:
        assert f"===== [{name}] =====" in out
        assert f"[{name}] PASS (rc=0)" in out


# --- (c) 位置參數取代語意 ---

def test_default_pytest_args() -> None:
    do_act, do_pg, args = m.parse_args([])
    assert (do_act, do_pg) == (False, False)
    # R59 ARCH-R59-01：新增 `-rs`（印 skip 理由）。本斷言是 DEFAULT_PYTEST_ARGS 的釘選鎖，
    # 改預設值必須同步改這裡——它在本輪確實當場翻紅並逼我同步，鎖有效。
    assert args == ["tests/", "-q", "-rs", "--tb=short"]


def test_positional_args_replace_defaults_entirely() -> None:
    _, _, args = m.parse_args(["-k", "test_foo", "-v"])
    assert args == ["-k", "test_foo", "-v"]  # 整批取代，不是附加


def test_flags_mixed_anywhere_with_positionals() -> None:
    do_act, do_pg, args = m.parse_args(["-k", "foo", "--act", "-v", "--pg"])
    assert (do_act, do_pg) == (True, True)
    assert args == ["-k", "foo", "-v"]  # 旗標任意位置皆可，且不進 pytest 參數


def test_flags_only_keep_default_pytest_args() -> None:
    do_act, do_pg, args = m.parse_args(["--act", "--pg"])
    assert (do_act, do_pg) == (True, True)
    # R59 ARCH-R59-01：新增 `-rs`（印 skip 理由）。本斷言是 DEFAULT_PYTEST_ARGS 的釘選鎖，
    # 改預設值必須同步改這裡——它在本輪確實當場翻紅並逼我同步，鎖有效。
    assert args == ["tests/", "-q", "-rs", "--tb=short"]


def test_pytest_gate_receives_overridden_args(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[list[str]] = []
    _mock_all_gates(monkeypatch, rc=0)
    monkeypatch.setattr(m, "gate_pytest", lambda args: received.append(list(args)) or 0)
    _silence_liveness(monkeypatch)
    assert m.main(["-k", "test_bar"]) == 0
    assert received == [["-k", "test_bar"]]


# --- (d) --act 平台分派 ---

def test_gate_act_posix_uses_bash_run_act_sh(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(m, "_stream", lambda cmd: calls.append(list(cmd)) or 0)
    monkeypatch.setattr(m.platform_utils, "is_windows", lambda: False)
    assert m.gate_act() == 0
    assert calls == [["bash", str(m.REPO_ROOT / "tools" / "run_act.sh"), "--job", "test"]]


def test_gate_editable_green_when_pkg_under_repo_top(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """editable 哨兵綠路徑（R12 QA 一審 QA-3：哨兵本體原零覆蓋，`ok=…` 突變恆
    True 時無機械訊號）：套件位於 git toplevel 之下 → rc=0。"""
    fake = SimpleNamespace(__file__=str(m.REPO_ROOT / "autoclaude" / "__init__.py"))
    monkeypatch.setitem(sys.modules, "autoclaude", fake)
    monkeypatch.setattr(
        m.subprocess, "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=f"{m.MONO_ROOT}\n"),
    )
    assert m.gate_editable() == 0


def test_gate_editable_red_when_pkg_outside_repo_top(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """editable 哨兵紅路徑：套件指向 repo 外（舊 editable .pth 殘留 shadow 場景，
    取證紀律 #19）→ rc=1。"""
    fake = SimpleNamespace(
        __file__=str(tmp_path / "site-packages" / "autoclaude" / "__init__.py")
    )
    monkeypatch.setitem(sys.modules, "autoclaude", fake)
    monkeypatch.setattr(
        m.subprocess, "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=f"{m.MONO_ROOT}\n"),
    )
    assert m.gate_editable() == 1


def test_gate_act_windows_uses_powershell_file_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(m, "_stream", lambda cmd: calls.append(list(cmd)) or 0)
    monkeypatch.setattr(m.platform_utils, "is_windows", lambda: True)
    monkeypatch.setattr(
        m.shutil, "which",
        # mock which() 回傳值＋下方純字串斷言，無 pathlib join 語意：
        lambda name: (
            r"C:\WINDOWS\powershell.exe" if name == "powershell" else None  # platform-ok: mock
        ),
    )
    assert m.gate_act() == 0
    (cmd,) = calls
    assert cmd[0] == r"C:\WINDOWS\powershell.exe"  # platform-ok: 純字串斷言（同上）
    # -File 呼叫（勿 -Command 包裹，會吞 exit code 假綠）+ run_act.ps1 -Job test
    assert "-File" in cmd and "-Command" not in cmd
    assert cmd[cmd.index("-File") + 1] == str(m.REPO_ROOT / "tools" / "run_act.ps1")
    assert cmd[-2:] == ["-Job", "test"]


def test_gate_act_windows_falls_back_to_pwsh(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(m, "_stream", lambda cmd: calls.append(list(cmd)) or 0)
    monkeypatch.setattr(m.platform_utils, "is_windows", lambda: True)
    monkeypatch.setattr(
        m.shutil, "which", lambda name: "/usr/bin/pwsh" if name == "pwsh" else None
    )
    assert m.gate_act() == 0
    assert calls[0][0] == "/usr/bin/pwsh"


def test_gate_act_windows_no_powershell_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(m.platform_utils, "is_windows", lambda: True)
    monkeypatch.setattr(m.shutil, "which", lambda name: None)
    assert m.gate_act() == 1
    assert "找不到 PowerShell" in capsys.readouterr().out


# --- (e) --pg：alembic 失敗清理容器並 FAIL ---

def _pg_call_recorder(monkeypatch: pytest.MonkeyPatch, alembic_rc: int, up_rc: int = 0):
    stream_calls: list[list[str]] = []
    quiet_calls: list[list[str]] = []

    # gate_pg 直接寫 os.environ（對齊 .sh export 語意）——先以 monkeypatch 登記
    # 還原點，避免 DSN env 洩漏到 pytest session 其他測試（DAL DSN 解析優先級最高）
    for var in ("AUTOCLAUDE_DB_DSN", "AUTOCLAUDE_TEST_PG_DSN", "AUTOCLAUDE_ALLOW_INSECURE_DB"):
        monkeypatch.setenv(var, os.environ.get(var, ""))

    def fake_stream(cmd: list[str]) -> int:
        stream_calls.append(list(cmd))
        if cmd[:2] == ["docker", "compose"] and "up" in cmd:
            return up_rc
        if cmd[1:3] == ["-m", "alembic"]:
            return alembic_rc
        return 0

    monkeypatch.setattr(m, "_stream", fake_stream)
    monkeypatch.setattr(m, "_run_quiet", lambda cmd: quiet_calls.append(list(cmd)) or 0)
    return stream_calls, quiet_calls


def test_gate_pg_alembic_failure_tears_down_and_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stream_calls, quiet_calls = _pg_call_recorder(monkeypatch, alembic_rc=1)
    assert m.gate_pg() == 1
    assert "alembic upgrade head 失敗" in capsys.readouterr().out
    # 清理容器（down -v）必須執行
    assert quiet_calls == [["docker", "compose", "-f", "docker-compose.ci.yml", "down", "-v"]]
    # alembic 失敗後不得續跑 contract pytest（rc 防吞）
    assert not any("pytest" in c for cmd in stream_calls for c in cmd)


def test_gate_pg_compose_up_failure_skips_alembic(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stream_calls, quiet_calls = _pg_call_recorder(monkeypatch, alembic_rc=0, up_rc=1)
    assert m.gate_pg() == 1
    assert "docker compose up --wait 失敗" in capsys.readouterr().out
    assert not any("alembic" in c for cmd in stream_calls for c in cmd)
    assert quiet_calls == []  # 容器沒起來，無需清理


def test_gate_pg_success_returns_pytest_rc_and_tears_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream_calls, quiet_calls = _pg_call_recorder(monkeypatch, alembic_rc=0)
    assert m.gate_pg() == 0
    assert any("test_pg_state_repository_contract.py" in c for cmd in stream_calls for c in cmd)
    assert quiet_calls == [["docker", "compose", "-f", "docker-compose.ci.yml", "down", "-v"]]
    # DSN env 對齊 CI（asyncpg；alembic/env.py 自動 strip）
    assert m.os.environ["AUTOCLAUDE_DB_DSN"].startswith("postgresql+asyncpg://")
    assert m.os.environ["AUTOCLAUDE_ALLOW_INSECURE_DB"] == "1"


# --- (f) liveness advisory 失敗不影響閘門結果 ---

def test_liveness_nonzero_rc_does_not_gate(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(
        m.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=1)
    )
    _mock_all_gates(monkeypatch, rc=0)
    assert m.main([]) == 0
    assert "✅ 全部通過" in capsys.readouterr().out


def test_liveness_oserror_does_not_gate(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(*_a, **_kw):
        raise OSError("no interpreter")

    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(m.subprocess, "run", boom)
    _mock_all_gates(monkeypatch, rc=0)
    assert m.main([]) == 0
    assert "✅ 全部通過" in capsys.readouterr().out


def test_liveness_skipped_in_ci_env(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[bool] = []
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(
        m.subprocess, "run", lambda *a, **kw: ran.append(True) or SimpleNamespace(returncode=0)
    )
    m._hooks_liveness_advisory()
    assert ran == []  # CI 環境跳過（GitHub/act 無 hooks 屬正常）


# --- (g) gate 拋例外 → 判 FAIL 不炸 ---

def test_gate_exception_counts_as_fail(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom() -> int:
        raise FileNotFoundError("docker")

    _mock_all_gates(monkeypatch, rc=0)
    monkeypatch.setattr(m, "gate_loc", boom)
    _silence_liveness(monkeypatch)
    rc = m.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "[LOC budget] 例外：docker" in out
    assert "[LOC budget] FAIL (rc=1)" in out
    assert f"  {'LOC budget':<22} FAIL" in out


# --- (h) R69（DEF-101-702／R68-19）：`-h/--help` 不得靜默跑完整套閘門 ---

def test_help_prints_usage_and_runs_no_gate(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """WHY：修前 `--help` 會被當成「首個非旗標參數」而整批取代 pytest 預設參數 ⇒ 使用者
    想看用法，實際得到的是 ruff/lint-imports/… 前四道閘門真的跑完。同族入口
    （bootstrap_core／integration_gate_core）都已 fail-loud，本檔是最後一個沒跟上的。
    本鎖同時斷言「零 gate 被執行」——只驗 rc=0 會被「跑完整套剛好全綠」蒙混過去。
    """
    ran: list[str] = []
    _mock_all_gates(monkeypatch, rc=0)
    for name in _ALL_GATE_FUNCS:
        orig = getattr(m, name)
        monkeypatch.setattr(m, name, lambda *a, _n=name, _o=orig: (ran.append(_n), _o(*a))[1])
    _silence_liveness(monkeypatch)
    for flag in ("--help", "-h"):
        ran.clear()
        rc = m.main([flag])
        out = capsys.readouterr().out
        assert rc == 0
        assert ran == [], f"{flag} 竟然執行了 gate：{ran}"
        assert "用法" in out and "--act" in out
        assert "本機 CI 閘門總結" not in out


def test_help_flag_anywhere_in_argv_is_honoured(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--act --help` 這種順序也必須只印用法——旗標位置無關是本檔既有的 CLI 語意。"""
    ran: list[str] = []
    _mock_all_gates(monkeypatch, rc=0)
    for name in _ALL_GATE_FUNCS:
        orig = getattr(m, name)
        monkeypatch.setattr(m, name, lambda *a, _n=name, _o=orig: (ran.append(_n), _o(*a))[1])
    _silence_liveness(monkeypatch)
    assert m.main(["--act", "--help"]) == 0
    capsys.readouterr()
    assert ran == []
