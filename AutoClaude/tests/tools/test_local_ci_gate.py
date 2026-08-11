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
    (h) `-h/--help` 不得靜默跑完整套閘門
    (i) R79 收輪：skip 分群普查 —— **量測塌掉必須 fail-loud**（QA-R79 blocking）、
        三態離開碼、剖面取自 DSN 而非「是不是我注入的」、PG 自動偵測四條剎車
    (j) `--census-only` CLI（push 通道與 CI 的共同入口；含 stdin 形態）
    (k) 接線鎖：census 有沒有真的掛在會擋的通道上（pre-push／push CI），
        以及自動偵測有沒有掛在 pytest 一定會載的那一層（conftest）
"""
from __future__ import annotations

import io
import os
import re
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


def _pin_registered_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """把剖面釘在**已登記**的那一格（`_skip_profile` 讀 `sys.platform`）。

    WHY：`_RUNTIME_SKIP_CEILING` 目前只登記 `win32` 兩個剖面（刻意的誠實劃界——
    mac／Linux 的健康值沒人量過）。不釘的話，「健康量測 ⇒ CENSUS_OK」這組斷言在
    Windows 上綠、在 Linux runner 上得到 `CENSUS_PROFILE_UNREGISTERED`（3）而紅
    ——本輪由 act（ubuntu 容器）實跑抓到。釘住剖面才問得到本組真正要問的那件事。
    """
    monkeypatch.setattr(m.sys, "platform", "win32")
    # R80 包 A（S3-09）：剖面多了「巢狀 session」這一維，同樣要釘——否則本組斷言的
    # 綠紅會跟著「跑測試的人剛好在不在 Claude Code session 裡」翻面，那是最難查的假紅。
    monkeypatch.setattr(m, "nested_session", lambda: True)


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


# =====================================================================
# (i) R79 收輪：skip 分群普查（S3）
#
# WHY 這一整組非補不可（QA-R79 逐字）：R79 落地的三個新機制（分群天花板／PG 自動偵測／
# f-string 標籤抽取）在全庫 `test_*.py` 裡**零引用**，注入證明只活在會被丟掉的 scratchpad
# ⇒ 下次有人改壞不會有任何東西轉紅。落點刻意選這一支既有檔（DEF-101-561③ 禁止新增鎖檔；
# 且本檔不在根層護欄層的行數棘輪掃描面內）。
# =====================================================================

#: 合成語料的摘要尾行。🔴 passed 數刻意用兩位數而不是真實基線值：本 repo 的
#: `tools/check_pytest_baseline_sites.py` 把「四位數 ＋ passed/skipped 同行」判為基線
#: 數字站點（棘輪只准下修），而基線數字的 SSOT 是 ONBOARDING.md §7——測試 fixture 沒有
#: 理由在別處再開一個「看起來像基線」的家（落地當回合被那道守門當場擋下，非假想）。
_HEALTHY_TAIL = "12 passed, 3 skipped, 1 warning in 91.39s (0:01:31)"
#: 剖面標記行。R80 起兩個維度同住一行（PG × 巢狀 session）——少任一維，`--census-only`
#: 都會 fail-loud，理由相同：剖面量不到時任何天花板比較都沒有意義。
_MARKER_LINE = "AUTOCLAUDE-PG-DSN-IN-EFFECT=0 AUTOCLAUDE-NESTED-SESSION=1"
_HEALTHY_LOG = (
    "SKIPPED [2] tests\\a.py:10: [POSIX-NATIVE-ONLY] 只在 POSIX 上有意義\n"
    "SKIPPED [1] tests\\b.py: [ENV-DISABLED] 沒設 DSN\n"
    + _MARKER_LINE + "\n"
    + _HEALTHY_TAIL + "\n"
)


def test_skipped_reasons_handles_both_location_forms_and_counts() -> None:
    """`SKIPPED [n]` 的 n 代表 n 支；兩種位置前綴（有／無行號）都要剝乾淨。

    WHY：標籤的契約是「寫在 reason 的最前面」，位置前綴沒剝掉時分群會整批落進
    `untagged`——落地當回合實測過 136 支只認出 2 支的形態。
    """
    assert m.skipped_reasons(_HEALTHY_LOG) == [
        "[POSIX-NATIVE-ONLY] 只在 POSIX 上有意義",
        "[POSIX-NATIVE-ONLY] 只在 POSIX 上有意義",
        "[ENV-DISABLED] 沒設 DSN",
    ]


def test_census_is_green_on_a_healthy_measurement(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    _pin_registered_profile(monkeypatch)
    assert m.check_skip_census(_HEALTHY_LOG, pg=False) == 0
    assert "共 3 支" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("label", "output"),
    [
        ("空輸出", ""),
        ("有 skipped 但整段 -rs 消失", "....s\n12 passed, 136 skipped in 91.39s"),
        ("SKIPPED 前綴漂移", "SKIP [2] tests\\a.py:10: x\n10 passed, 2 skipped in 1.00s"),
        ("只有 -rs 沒有摘要行", "SKIPPED [1] tests\\a.py:10: x\n"),
    ],
)
def test_census_fails_loud_when_the_measurement_itself_collapses(
    label: str, output: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """🔴 本鎖是 QA-R79 那一筆 blocking 的回歸鎖，也是本組最重要的一支。

    修前實測：這四種輸入全部印「共 0 支：…untagged=0」並回 **rc=0**——天花板只對
    「數字變多」那一向說話，量測本身塌掉時它是綠的，而失效方向正是「看起來變乾淨」。
    而 `-rs` 在這個 repo 真的靜默消失過（R59）。判準必須讓「量不到」與「量到零」
    有不同的答案，否則整條 S3 的鑑別力建在流沙上。
    """
    assert m.check_skip_census(output, pg=False) == 1, label
    assert "量測塌掉" in capsys.readouterr().out, label


def test_unregistered_profile_is_advisory_for_the_cli_but_red_for_the_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """三態離開碼的分野：未登記剖面 ≠ 天花板被突破。

    WHY：兩者壓成同一個 rc 時，push 通道只能二選一——要嘛誤擋一個從來沒人量過的
    平台（mac／Linux 的第一次 push），要嘛整條放行。而手動閘門要的是相反的答案：
    人就在現場，該當場把實測值入表。故 `census_verdict` 分三態、兩個入口各取所需。
    """
    monkeypatch.setattr(m.sys, "platform", "linux")
    rc, lines = m.census_verdict(_HEALTHY_LOG, pg=False)
    assert rc == m.CENSUS_PROFILE_UNREGISTERED
    assert "剖面未登記" in "\n".join(lines)
    assert m.check_skip_census(_HEALTHY_LOG, pg=False) == 1  # 同一份輸入，閘門入口判紅


def test_profile_key_follows_real_effectiveness_not_who_set_the_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """剖面取決於「這次真的有一顆用得動的 PG」，既不是「是不是我注入的」，也不是
    「有沒有人設過那個字串」。

    WHY ①（R79 收輪訂正的實際缺陷，保留）：剖面原本取自 `pg_autodetect()` 的回傳值，於是
    「使用者自己 export 過 DSN」那條路上它回 False、剖面判成 nopg——測試明明跑在有 PG 的
    條件下，卻拿 nopg 的寬鬆上限去比，永遠通過。那不是紅，是沒有鑑別力。

    WHY ②（🔴 R84／QA-02，本支要守的新語意）：R79 的修法把判準寫成 `any(os.environ.get(k))`
    ＝「這個行程裡有沒有人設過這個字串」，於是**任何**寫進 env 的字串都會讓剖面翻成 `+pg`
    ——包含測試汙染（同檔 `_clear_brakes` 那個缺陷）與指向一顆沒 migrate 過的 DB。實測後果是
    同一份 log 裡剖面標記與 autodetect 理由互斥，而 census 的天花板會照著假標記挑錯剖面。
    ⇒ 判準改問真實生效性。本支的三段就是這個語意的邊界：**設了但用不動＝nopg**（第 2 段）
    才是這次真正加上的鑑別力，把它改回舊寫法時第 2 段會紅。
    """
    for key in m._PG_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    assert m.pg_dsn_in_effect() is False
    # ② DSN 在、但那顆 DB 用不動（剎車④ 的世界）⇒ PG 那一族照樣 skip ⇒ 剖面必須是 nopg
    monkeypatch.setenv("AUTOCLAUDE_TEST_PG_DSN", "postgresql://x/y")
    monkeypatch.setattr(m, "_pg_migrated", lambda dsn: "alembic_version 是空的")
    assert m.pg_dsn_in_effect() is False, (
        "DSN 設了卻用不動時剖面必須是 nopg——census 形狀就是 nopg，拿 pg 的緊上限去比是假紅，"
        "而反過來（標成 pg）會讓下游拿錯天花板"
    )
    assert m._skip_profile(m.pg_dsn_in_effect(), nested=True).endswith("+nopg+nested")
    # ③ DSN 在、DB 用得動 ⇒ +pg，且**不問是誰設的**（這裡沒有經過 pg_autodetect）
    monkeypatch.setattr(m, "_pg_migrated", lambda dsn: None)
    assert m.pg_dsn_in_effect() is True
    assert m._skip_profile(m.pg_dsn_in_effect(), nested=True).endswith("+pg+nested")


def test_pg_profile_marker_round_trips_and_absence_is_not_false() -> None:
    """標記缺席必須回 `None`（＝量不到），不得回 False（＝量到「沒有 PG」）。"""
    assert m.pg_in_effect_from_log("noise\n" + m.pg_marker_line(True)) is True
    assert m.pg_in_effect_from_log("noise\n" + m.pg_marker_line(False)) is False
    assert m.pg_in_effect_from_log("完全沒有標記的一份輸出") is None


def _clear_brakes(monkeypatch: pytest.MonkeyPatch) -> None:
    """把四條剎車全部放開。`AUTOCLAUDE_ALLOW_INSECURE_DB` 一併經 monkeypatch 走一遍：
    `pg_autodetect` 會 `setdefault` 它，沒登記還原點的話這幾支測試會把它留給整個
    session（測試不得改寫別人看得到的狀態）。

    🔴 R84 包 W5（QA-02）修這個 helper 自己的缺陷：`monkeypatch.delenv(k, raising=False)`
    對一個**原本就不存在**的 key **不會登記還原點**（沒有東西需要還原）——而本函式放開剎車
    之後，被測的 `pg_autodetect()` 會 `os.environ[...] = dsn` 把真 DSN 寫進真 env，那個寫入
    因此**活過整個 session**，一路活到 `pytest_terminal_summary` 印剖面標記。實測後果：
    同一份 log 第 117 行 `AUTOCLAUDE-PG-DSN-IN-EFFECT=1`、第 118 行「拒絕注入」，互斥；
    而 census 形狀（untagged=97）站在第 118 行那一邊 ⇒ 那一整輪的剖面鍵是假的。
    「守『只在 migrate 過才注入』的那支測試自己製造了未 migrate 卻回報 in-effect」——
    修法是先 `setenv(k, "")` 強迫 monkeypatch 記下「原本不存在」這件事，再 `delenv`。
    """
    for key in ("CI", m._AUTODETECT_OPT_OUT, "PYTEST_CURRENT_TEST",
                "AUTOCLAUDE_ALLOW_INSECURE_DB", *m._PG_ENV_KEYS):
        monkeypatch.setenv(key, "")     # ← 登記還原點（原本不存在 ⇒ undo 時會刪掉）
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize(
    ("brake", "value"),
    [("CI", "true"), ("AUTOCLAUDE_NO_PG_AUTODETECT", "1"),
     ("PYTEST_CURRENT_TEST", "x"), ("AUTOCLAUDE_DB_DSN", "postgresql://a/b")],
)
def test_each_autodetect_brake_prevents_injection(
    brake: str, value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """四條剎車逐條驗。WHY：自動偵測掛到 conftest 之後它對**每一次** pytest 都生效，
    任何一條剎車失效都不是「少了一個便利功能」，而是無聲改寫別人的測試環境。"""
    _clear_brakes(monkeypatch)
    monkeypatch.setenv(brake, value)
    monkeypatch.setattr(m, "_pg_reachable", lambda *a, **k: True)
    monkeypatch.setattr(m, "_pg_migrated", lambda dsn: None)
    injected, why = m.pg_autodetect()
    assert injected is False, why
    if brake not in m._PG_ENV_KEYS:
        assert m.os.environ.get("AUTOCLAUDE_TEST_PG_DSN") is None


def test_autodetect_injects_only_when_the_db_is_actually_migrated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """④「DB 必須真的被 migrate 過」——沒有這一條，注入只是把 92 支 skip 換成 92 支
    `UndefinedTable`，也就是把訊號換成雜訊。"""
    _clear_brakes(monkeypatch)
    monkeypatch.setattr(m, "_pg_reachable", lambda *a, **k: True)
    monkeypatch.setattr(m, "_pg_migrated", lambda dsn: "alembic_version 是空的")
    assert m.pg_autodetect()[0] is False
    assert m.os.environ.get("AUTOCLAUDE_DB_DSN") is None
    monkeypatch.setattr(m, "_pg_migrated", lambda dsn: None)
    injected, why = m.pg_autodetect()
    assert injected is True, why
    assert m.os.environ["AUTOCLAUDE_DB_DSN"].startswith("postgresql+asyncpg://")


def test_autodetect_is_silent_when_nothing_is_listening(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """沒有 PG 的機器必須**靜默不注入**，不得因此多一個紅字或例外。"""
    _clear_brakes(monkeypatch)
    monkeypatch.setattr(m, "_pg_reachable", lambda *a, **k: False)
    injected, why = m.pg_autodetect()
    assert injected is False and "沒有在聽" in why


def test_brake_four_says_how_to_fix_it_and_stays_distinguishable_from_no_pg_at_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """🔴 R84 包 W5（QA-01）：剎車④ 的理由必須帶**可貼的修法**，且與「完全沒起 PG」可區分。

    WHY（本支要在什麼語意變動時紅）：R83 交棒書把「起 PG」當成最便宜的一塊，而本輪實測那樣
    做削掉 **0 支** skip——容器 healthy、套件全裝，缺的只是 `alembic upgrade head`。使用者眼裡
    兩種失敗長得一樣（skip 都沒少），差別**只**寫在這一行理由裡；而原句只解釋了「為什麼不注入」
    （會變成 UndefinedTable），沒有說「怎麼讓它能注入」。⇒ 判準有兩向：
      ① 剎車④ 的理由必須逐字含 alembic 那條指令（照著訊息做就會好）；
      ② 「沒有在聽」那條路**不得**帶這句修法——貼錯修法比不貼更糟（會叫人去 migrate 一顆
         根本不存在的 DB），所以修法判準刻意只認 `alembic_version` 這個字。
    """
    _clear_brakes(monkeypatch)
    monkeypatch.setattr(m, "_pg_reachable", lambda *a, **k: True)
    monkeypatch.setattr(
        m, "_pg_migrated",
        lambda dsn: 'relation "alembic_version" does not exist',
    )
    injected, why = m.pg_autodetect()
    assert injected is False
    assert "alembic upgrade head" in why, f"剎車④ 沒有給出可貼的修法：{why}"
    assert m.pg_repair_hint(why)

    # ② 對照組：三種**不是**這條修法能治的理由，一律不得掛上它
    for other in ("localhost:5432 沒有在聽 ⇒ 不注入（PG 相關測試維持 skip）",
                  "psycopg2 未安裝（`uv pip install -e '.[postgres]'`）",
                  "connection to server at \"localhost\" failed: FATAL: password authentication"):
        assert m.pg_repair_hint(other) == "", f"對不該給修法的理由給了修法：{other}"


def test_the_profile_marker_may_not_contradict_the_autodetect_note() -> None:
    """🔴 R84 包 W5（QA-02）：標記說 `+pg`、理由說「拒絕注入」，兩者不可同時出現。

    WHY：QA 實測到的那份 log 第 117 行是 `AUTOCLAUDE-PG-DSN-IN-EFFECT=1`、第 118 行是
    「偵測到 PG 但拒絕注入」。剎車④ 只在「我們要用的那顆 DB 用不動」時觸發 ⇒ 兩件事同時為真
    在邏輯上不可能，而當時**沒有任何東西**會因此出聲，於是那份 log 被當成 `+pg` 剖面讀了一輪
    （census 的分群天花板因此拿錯剖面比對）。本支釘住那道判準的兩向鑑別力。
    """
    refused = m.BRAKE4_REFUSED + "（alembic_version 是空的）"
    assert m.profile_marker_contradiction(True, refused)          # 紅向：互斥
    assert m.profile_marker_contradiction(False, refused) == ""   # 標記說 nopg ⇒ 一致，不出聲
    # 其餘剎車 ＋ in_effect=True 都是**合法**組合，判它們就是製造假紅：
    for legit in ("跳過：AUTOCLAUDE_DB_DSN 已由使用者顯式設定（顯式優先）",
                  "跳過：CI 環境（雲端 job 自己在 env: 區塊宣告 DSN）",
                  "localhost:5432 沒有在聽 ⇒ 不注入（PG 相關測試維持 skip）",
                  None, ""):
        assert m.profile_marker_contradiction(True, legit) == "", legit


def test_clearing_the_brakes_leaves_no_dsn_behind_after_undo() -> None:
    """🔴 R84 包 W5（QA-02）：`_clear_brakes` 之後被測碼寫進 env 的 DSN 必須隨 undo 消失。

    WHY（這是 QA-02 的**根因**那一半，與上一支的「標記說謊」是同一個缺陷的兩端）：
    `monkeypatch.delenv(k, raising=False)` 對一個原本不存在的 key **不登記還原點**，而
    `_clear_brakes` 放開剎車後 `pg_autodetect()` 會 `os.environ[...] = dsn` ⇒ 那個寫入活過
    整個 session。本支用一個獨立的 `MonkeyPatch` 上下文把「還原之後」這件事變成可斷言的：
    把 helper 改回舊寫法（只 delenv）時它會紅。
    """
    before = {k: os.environ.get(k) for k in m._PG_ENV_KEYS}
    with pytest.MonkeyPatch.context() as mp:
        _clear_brakes(mp)
        mp.setattr(m, "_pg_reachable", lambda *a, **k: True)
        mp.setattr(m, "_pg_migrated", lambda dsn: None)
        assert m.pg_autodetect()[0] is True          # 真的寫進了 env（前提成立才有得還原）
        assert os.environ.get("AUTOCLAUDE_DB_DSN")
    assert {k: os.environ.get(k) for k in m._PG_ENV_KEYS} == before, (
        "測試把 DSN 留給了整個 session ⇒ pytest_terminal_summary 的剖面標記會說謊"
    )


# --- (j) `--census-only` CLI：push 通道與 CI 的共同入口 ---

def _write_log(tmp_path: Path, text: str) -> str:
    path = tmp_path / "pytest.log"
    path.write_text(text, encoding="utf-8", newline="\n")
    return str(path)


def test_census_only_returns_three_states_and_runs_no_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """健康→0、量測塌掉→1、找不到剖面標記→1、讀不到檔→1；且**一道 gate 都不准跑**。

    WHY 要一併斷言「零 gate」：這個入口掛在 push 通道上，若它會順手跑起整套閘門，
    每次 push 就多付一次分鐘級成本——那正是開發者改用 `--no-verify` 的起點。
    """
    ran: list[str] = []
    for name in _ALL_GATE_FUNCS:
        monkeypatch.setattr(m, name, lambda *a, _n=name: ran.append(_n) or 0)
    _silence_liveness(monkeypatch)
    _pin_registered_profile(monkeypatch)

    assert m.main(["--census-only", _write_log(tmp_path, _HEALTHY_LOG)]) == m.CENSUS_OK
    collapsed = _MARKER_LINE + "\n12 passed, 136 skipped in 9.0s\n"
    assert m.main(["--census-only", _write_log(tmp_path, collapsed)]) == m.CENSUS_FAIL
    no_marker = _HEALTHY_LOG.replace(_MARKER_LINE + "\n", "")
    assert m.main(["--census-only", _write_log(tmp_path, no_marker)]) == m.CENSUS_FAIL
    assert "剖面標記" in capsys.readouterr().out
    assert m.main(["--census-only", str(tmp_path / "nope.log")]) == m.CENSUS_FAIL
    # 參數形狀不對一律 fail-loud，**不得**退回「當成 pytest 參數」——那條路會跑完整套
    # 閘門（分鐘級）再把字串丟給 pytest，使用者只是想要幾毫秒的普查。
    assert m.main(["--census-only"]) == m.CENSUS_FAIL
    assert m.main(["--census-only", "a", "b"]) == m.CENSUS_FAIL
    assert m.main(["--pg", "--census-only", "a"]) == m.CENSUS_FAIL
    capsys.readouterr()
    assert ran == [], f"--census-only 竟然執行了 gate：{ran}"


def test_census_only_reads_stdin_when_path_is_dash(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`-` ＝讀 stdin。push 通道走這一條的理由：`mktemp` 給的是 POSIX 路徑，而
    Windows 側 python 是原生 exe，路徑會過 MSYS 參數轉換——shell 重導向繞開那一層。"""
    _pin_registered_profile(monkeypatch)
    monkeypatch.setattr(m.sys, "stdin", io.StringIO(_HEALTHY_LOG))
    assert m.census_only("-") == m.CENSUS_OK
    assert "共 3 支" in capsys.readouterr().out


# --- (k) 接線鎖：判準有沒有真的掛在會擋的通道上 ---
#
# WHY 這兩支存在（SA-R79／QA-R79）：R79 的天花板「不在任何阻斷閘門上」——這件事沒有
# 任何機械物看得見，是複審者逐檔讀出來的。接線被刪掉時要有東西轉紅，否則本輪修的只是
# 「這一次有接上」。誠實劃界：以文字判準認定，看不到「接線還在但被上游改成永遠不執行」
# 那種形態（那由本檔上方的行為鎖與收輪的端到端注入負責）。

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _uncommented(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]


def test_pre_push_dispatcher_actually_invokes_the_census() -> None:
    """根層 dispatcher 的 AutoClaude leg 必須**執行**（非 echo）census，並且三態都接上。"""
    dispatcher = _REPO_ROOT / "tools" / "git-hooks" / "pre-push"
    assert dispatcher.is_file(), dispatcher
    text = dispatcher.read_text(encoding="utf-8")
    leg = text.split('if [ "$run_autoclaude" -eq 1 ]')[1].split('if [ "$run_sdd" -eq 1 ]')[0]
    # 🔴 R80 包 A 訂正判準的比較對象：原判準要求該行**字面**出現 `python`，於是 R80 另一包
    # 把 dispatcher 裡寫死的直譯器改成 `"$PY"` 變數（一個純粹正確的重構）之後，這道鎖當場
    # 轉紅——它其實在守「直譯器怎麼拼」，而它宣稱要守的是「census 有沒有真的被執行」。
    # 改成認 `local_ci_gate`：那才是這道鎖真正的標的，而且比原判準更精確（原判準對
    # 「用 python 跑了別的東西」是放行的）。同 R75 頭號教訓：判準的比較對象不得隨
    # 「被它所判的動作」而改變。
    invocations = [
        ln for ln in _uncommented(leg)
        if "--census-only" in ln and "local_ci_gate" in ln and "echo" not in ln
    ]
    assert invocations, (
        "pre-push 的 AutoClaude leg 找不到**執行** `--census-only` 的語句（註解與 echo "
        "訊息不算）——skip 分群天花板會退回「只有人工跑 local_ci_gate 才會說話」，"
        "而那正是 SA-R79／QA-R79 這一輪要修掉的東西"
    )
    assert "-eq 3" in leg, "advisory（剖面未登記）那一支被拿掉了＝沒量過的平台會被誤擋"
    assert "rc=1" in leg, "census 判紅時沒有把 rc 接出來＝印了紅字卻照樣放行（fail-open）"
    assert (_REPO_ROOT / "AutoClaude" / "tools" / "local_ci_gate.py").is_file()


def test_push_ci_test_job_consumes_the_census_and_perf_step_counts_skips() -> None:
    """`autoclaude-ci.yml`：test job（push 硬閘）接 census；perf 步驟不得對 skip 回綠。"""
    workflow = (_REPO_ROOT / ".github" / "workflows" / "autoclaude-ci.yml").read_text(
        encoding="utf-8")
    body = "\n".join(_uncommented(workflow))
    assert "--census-only autoclaude-pytest.log" in body, (
        "push 硬閘的 test job 沒有消費 skip 普查——它本來就跑全套 pytest，只差把輸出餵一次"
    )
    # B06：perf 步驟原本只有一行裸 pytest ⇒ 「SLA 量過且達標」與「這支又沒跑」共用一個綠。
    assert "PGVECTOR-PERF-CENSUS" in body and "pgvector-perf.log" in body
    assert body.count("set -o pipefail") >= 3, (
        "少了 `set -o pipefail`：GHA 預設 `bash -e`（無 pipefail），接 `| tee` 之後"
        "管線 rc 取最後一個元素（tee，恆 0）⇒ pytest 的真 rc 被整個吞掉"
    )


def _loaded_conftest():
    """本次 session 真的載進來的 `AutoClaude/tests/conftest.py` 模組物件。

    以 `__file__` 反查而不是 `import conftest`：conftest 的模組名取決於 rootdir 與有無
    `__init__.py`，寫死名字會在別人調整佈局時變成假綠（找不到就跳過＝沒有人在守）。
    """
    target = (_REPO_ROOT / "AutoClaude" / "tests" / "conftest.py").resolve()
    for module in list(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if path and Path(path).resolve() == target:
            return module
    return None


def test_conftest_is_where_the_autodetect_is_wired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """🔴 掌舵者 S3 的核心：自動偵測必須掛在 **pytest 一定會載** 的那一層。

    WHY（QA-R79 當回合實測）：R79 落地時它只有 `local_ci_gate` 一個呼叫端，而本機預設
    路徑（`python -m pytest tests/ -q`）根本不經過它 ⇒ 那個數字仍是 136 skipped，一支
    都沒少。機制是好的、掛錯入口——對使用者而言與沒做是同一件事。接上 conftest 之後
    同一條指令實測 136 → 44。本鎖釘的就是「還掛在那裡」。
    """
    conftest = _loaded_conftest()
    assert conftest is not None, "找不到已載入的 AutoClaude/tests/conftest.py"
    assert conftest._local_ci_gate() is m, (
        "conftest 載到的不是本 session 這一份 local_ci_gate ⇒ 兩份副本各有一份模組級"
        "狀態，剖面標記與判準會各說各話"
    )
    assert callable(conftest.pytest_configure)
    saved = conftest._PG_AUTODETECT_NOTE
    # 剎車① `CI` 排在剎車③ 之前，CI runner 上會先命中它、note 裡沒有 `pytest` 字樣
    # ⇒ 本鎖在雲端／act 容器內恆紅（本輪由 act 實跑抓到）。拿掉它才問得到剎車③。
    monkeypatch.delenv("CI", raising=False)
    try:
        conftest.pytest_configure(None)   # 本行程是 pytest ⇒ 剎車③ 生效，不污染 env
        assert "pytest" in (conftest._PG_AUTODETECT_NOTE or ""), conftest._PG_AUTODETECT_NOTE
    finally:
        # 還原：那個字串會被印進本次 session 的終端摘要，測試改寫它等於讓摘要說謊
        conftest._PG_AUTODETECT_NOTE = saved


def test_conftest_terminal_summary_emits_the_profile_marker() -> None:
    """剖面標記必須真的被印出來——`--census-only` 找不到它就會 fail-loud（設計如此），
    所以拿掉這一段等於讓 push 通道與 CI 的普查整條轉紅。本鎖讓那件事在單元層先紅。"""
    conftest = _loaded_conftest()
    assert conftest is not None
    written: list[str] = []
    reporter = SimpleNamespace(
        stats={}, write_sep=lambda *a, **k: None, write_line=written.append)
    conftest.pytest_terminal_summary(reporter, 0, None)
    markers = [ln for ln in written if ln.startswith(m.PG_PROFILE_MARKER)]
    assert len(markers) == 1, written
    assert m.pg_in_effect_from_log("\n".join(written)) is m.pg_dsn_in_effect()
    # R80 包 A（S3-09）：第二維也必須被印出來，否則 `--census-only` 同樣 fail-loud。
    assert m.nested_from_log("\n".join(written)) is m.nested_session()


# =====================================================================
# (l) R80 包 A：skip 天花板的**判準形狀**（S3-03）、剖面第三維（S3-09）、
#     CI 平台涵蓋帳（S3-02）、DSN 形態驗證（S3-06）
# =====================================================================

_POLICY_ROOT = Path(__file__).resolve().parents[3] / "tools" / "lib"
if str(_POLICY_ROOT) not in sys.path:
    sys.path.insert(0, str(_POLICY_ROOT))
import skip_group_policy as P  # noqa: E402

_PROF = "AutoClaude/tests@win32+nopg+nested"


def _base_census() -> dict[str, int]:
    return dict(P._RUNTIME_SKIP_CEILING[_PROF])


def test_retagging_is_not_punished_by_the_group_ceiling() -> None:
    """🔴 本組是 S3-03 的回歸鎖，也是本包最重要的一支。

    修前實測（注入，逐字見包 A 回報）：舊判準的失敗訊息逐字寫著「合法出口只有
    『把那些測試變成真的會跑』或『**補上正確的分群標籤**』」，而**照著第二個出口做就會
    被同一道判準判紅**——補標籤必然讓某個具名群 +1。一道判準宣傳的出口自己是違規，
    等於它其實只接受一種改善方式（skip 憑空消失），而那正是本 repo 記過的
    「看起來變乾淨」那一種。

    這裡的 census：118 支 untagged 全部補上 `[ENV-DISABLED]` 標籤，總量一支沒變。
    """
    retagged = _base_census()
    retagged[P.SKIP_GROUP_UNTAGGED] = 0
    retagged[P.SKIP_GROUP_ENV_DISABLED] += 118
    assert sum(retagged.values()) == sum(_base_census().values())  # 總量真的沒變
    assert P.skip_group_census_problems(_PROF, retagged) == []


def test_a_healthier_tree_is_not_red_even_when_a_group_grew() -> None:
    """總量**下降**（樹變健康）卻有一群上升 ⇒ 必須綠。

    修前實測：untagged 118→112、platform 17→20（總量 136→133）舊判準回 1 筆問題。
    「skip 少 3 支反而判不合格」是判準形狀錯誤，不是嚴格。
    """
    healthier = _base_census()
    healthier[P.SKIP_GROUP_UNTAGGED] -= 6
    healthier[P.SKIP_GROUP_PLATFORM] += 3
    assert sum(healthier.values()) < sum(_base_census().values())
    assert P.skip_group_census_problems(_PROF, healthier) == []


def test_a_real_regression_is_still_red() -> None:
    """反向鑑別力：沒有從 untagged 搬出任何一支、卻多出 skip ⇒ 兩道都要說話。

    沒有這一支，上面兩支「放寬」的修改就可能把整道判準改成永遠綠——本 repo 對
    「鎖還在但沒有鑑別力」已有多次判例，放寬與鑑別力必須同一個 commit 內一起驗。
    """
    worse = _base_census()
    worse[P.SKIP_GROUP_PLATFORM] += 1
    problems = P.skip_group_census_problems(_PROF, worse)
    assert any("總量" in p for p in problems), problems
    assert any("群 `platform`" in p for p in problems), problems


def test_open_debt_is_the_zeroable_half_and_platform_is_not_in_it() -> None:
    """「歸零」的標的＝欠債型 skip，**不含** platform。

    WHY（掌舵者驗收問題②）：skip 總數在單一平台上結構性不可能歸零——`platform` 群的
    意思正是「這支在別的平台才有驗證價值」。把它算進目標，目標就永遠達不到，而永遠
    達不到的目標不會出現在任何判準裡。分開之後「歸零」變成一個真的可以瞄準的數字。
    """
    census = _base_census()
    assert P.open_debt(census) == sum(
        census[g] for g in (P.SKIP_GROUP_TOOL_ABSENCE, P.SKIP_GROUP_ENV_DISABLED,
                            P.SKIP_GROUP_DEBT, P.SKIP_GROUP_UNTAGGED))
    assert P.SKIP_GROUP_PLATFORM not in P.ZERO_TARGET_GROUPS
    # 欠債歸零、只剩結構性 skip ⇒ 目標報告不再抱怨欠債（但仍會點出互補剖面缺口）
    cleared = dict.fromkeys(P.SKIP_GROUPS, 0)
    cleared[P.SKIP_GROUP_PLATFORM] = census[P.SKIP_GROUP_PLATFORM]
    assert not any("欠債型" in line for line in P.skip_target_report(_PROF, cleared))


def test_platform_skips_have_no_mechanical_proof_of_the_other_half_today() -> None:
    """S3-08：`platform` 群的正確目標是「互補剖面上真的有人跑到」，而今天沒有。

    這一支**刻意斷言缺口存在**：互補剖面（linux）至今沒人量過，所以那些測試目前沒有
    任何機械證據顯示它們在世界上任何一處跑過。等有人把 linux 剖面量出來入表，本支會
    紅——那正是它該有的行為（提醒把這句話改掉），而不是靜默通過。
    """
    lines = P.skip_target_report(_PROF, _base_census())
    assert any("互補剖面" in line for line in lines), lines
    # 🔴 R82（MAC-01）：值已由單一字串改成 tuple——互補剖面是**多對一**。
    assert not all(P.profile_registered(c) for c in P._COMPLEMENTARY_PROFILE[_PROF])


def _structural_only_census() -> dict[str, int]:
    """只有結構性 skip、零欠債的 census：讓 `skip_target_report` 只可能吐互補剖面那一行。"""
    census = dict.fromkeys(P.SKIP_GROUPS, 0)
    census[P.SKIP_GROUP_PLATFORM] = 40
    return census


def _complementary_gap_lines(profile: str) -> list[str]:
    return [ln for ln in P.skip_target_report(profile, _structural_only_census())
            if "互補剖面" in ln]


def test_the_complementary_gap_names_exactly_the_unmeasured_counterparts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """🔴 R82（MAC-01）的判準本體，R83 改寫成不會隨磁碟狀態過期的形狀。

    WHY（Rule 9）：`platform` 群在 win32 上是兩個互斥子母體——`[POSIX-NATIVE-ONLY]`
    的家是 linux，`[MAC-NATIVE-ONLY]`（R82 census 實測 26 支）的家只有 darwin，而
    linux 結構上跑不到它們（`install_mac_nightly.sh` 自帶 `uname != Darwin` fail-loud、
    act 映像內 `which zsh` 回空）。舊判準是 1:1 且用「有沒有登記」**短路**（`any`），於是
    `tools/tests@win32` 的結構性缺口那一行**一次都沒印過**——帳面讀起來像已覆蓋。

    🔴 **為什麼要改寫（R83）**：本支 R82 版把「`tools/tests@win32` 的互補集合**現在**
    一半登記一半沒有」當成注入基底，而那是一個**磁碟狀態**、不是一條性質。R83 於 mac
    真機量出 `tools/tests@darwin` 並入 `_RUNTIME_SKIP_CEILING{,_MAX}` 之後，該集合變成
    全登記 ⇒ 本支自己轉紅（它的訊息當初就寫了「若 darwin 已經量出來入表了，請改寫本支」）。
    **判準沒壞，是它抓著的語料被正常的進度改掉了**——那就是 R82 自己在
    `test_ci_platform_coverage_is_red_when…` 命名過的「注入基底腐化」，只是這次輪到它。

    改寫後守的性質（都與哪一個剖面今天量到了無關）：
      ① **真表 iff（漂移免疫）**：對 `_COMPLEMENTARY_PROFILE` 的**每一列**，缺口行
         出現 ⟺ 該列至少有一個互補剖面沒人量過；出現時必須**恰好**指名沒量到的那些、
         且**不得**把已量到的寫進缺口（反向假事實與漏報同樣貴）。
         量化在整張表上 ⇒ 任一列畢業／新登記都不會讓本支過期。
      ② **≥2 半登記那一支（合成語料）**：MAC-01 的病灶形態（多對一集合裡只有一半有家）
         今天在磁碟上**已不存在**（唯一的 ≥2 集合 `tools/tests@win32` 兩格皆已登記）⇒
         ①的「缺口出現」分支只被 1:1 的列走到，`all`→`any` 迴歸**測不出來**。故本支
         合成一列來走那個分支。
         🔴 為什麼合成不算脫離現實：受測物是**真的** `skip_target_report`／
         `profile_registered`，登記狀態也是真的走那兩張天花板表決定的（`measured` 那一格
         是真的被 setitem 進兩張表才算已登記）；合成的只有「剖面叫什麼名字、跟誰配對」
         這兩格，而要鎖的是**判準的形狀**（`all` 不是 `any`）——那是程式碼的性質，不是
         資料的性質。反過來說：把這一對繫回磁碟上「今天誰已量／誰未量」，就是 R82 版
         之所以在這裡轉紅的原因（R83 獨立驗證輪實測：繫回去的版本等 linux 兩列畢業後
         會以無訊息的 `StopIteration` 轉紅，比舊版更難接手，詳見 ② 段落內註解）。
      ③ 真表**仍必須存在**一個 ≥2 的互補集合——MAC-01 的缺陷本體是「表是 1:1」，
         退回 1:1（或值退回單一字串）會讓 mac-only 那一族再次失去家，這條沒有過期。
    """
    # ── ③ 缺陷本體之鎖：多對一的形狀不准退回 1:1 ────────────────────────────
    multi = {p: cps for p, cps in P._COMPLEMENTARY_PROFILE.items() if len(cps) >= 2}
    assert multi, (
        "`_COMPLEMENTARY_PROFILE` 一個多對一集合都不剩 ⇒ MAC-01 缺陷本體迴歸："
        f"mac-only 那一族又只能靠 linux 那一格短路放行。實得：{P._COMPLEMENTARY_PROFILE}"
    )

    # ── ① 真表 iff：對每一列，缺口行的有無與內容都必須與登記狀態逐格對上 ──────
    # 🔴 R83 複審收斂（SA-02）：判準加上**第二種**成因後，本層的 iff 也必須跟著加寬。
    # 原本的等式是「缺口行 ⟺ 有互補剖面未量測」，而 SA-02 證出的病灶是另一向：**宣告的
    # 承接者已量測、卻在平台語意上一支都跑不到**（darwin 的家填成 linux）。那一向在舊等式
    # 下會被判成「全量測卻仍報＝假缺口」——**一個真紅被這支鎖的訊息說成假紅**，而下一個人
    # 最省力的處置就是把新判準拆掉。故等式改為「缺口行 ⟺ 有未量測 **或** 有某個非得有的
    # 平台在這一列裡連候選都沒宣告」。
    for prof, counterparts in P._COMPLEMENTARY_PROFILE.items():
        registered = [c for c in counterparts if P.profile_registered(c)]
        unregistered = [c for c in counterparts if not P.profile_registered(c)]
        homeless = sorted(P.required_home_platforms(P._platform_of(prof))
                          - {P._platform_of(c) for c in counterparts})
        gap = _complementary_gap_lines(prof)
        assert bool(gap) == bool(unregistered or homeless), (
            f"{prof}：缺口行的有無與登記狀態不一致——unregistered={unregistered}、"
            f"homeless={homeless}、gap={gap}。有未量測卻不報＝MAC-01 短路迴歸；"
            "有平台完全未宣告卻不報＝SA-02 假綠迴歸；兩者皆無卻仍報＝假缺口"
        )
        for c in unregistered:
            assert any(c in ln for ln in gap), (
                f"{prof}：缺口行沒指名 `{c}`——只說「有缺口」而指不出要去量什麼，"
                f"就沒有人接得住這個交棒。實得：{gap}"
            )
        for platform in homeless:
            assert any(platform in ln for ln in gap), (
                f"{prof}：缺口行沒指名平台 `{platform}`——它是標籤語意算出來「非得有人"
                f"承接」的那一個，指不出來就沒有人接得住這個交棒。實得：{gap}"
            )
        for c in registered:
            assert not any(c in ln for ln in gap), (
                f"{prof}：已登記的 `{c}` 被列進缺口清單 ⇒ 反向假事實。實得：{gap}"
            )

    # ── ② 合成一列走「≥2 且半登記」那個分支（真表今天走不到它）────────────────
    # 🔴 R83 獨立驗證輪加固：這一對互補剖面的**名字與登記狀態也是合成的**。
    # 前一版是從真表裡 `next()` 挑「一個真的已量、一個真的未量」——理由是「不脫離現實」，
    # 但那讓本層又繫回磁碟狀態：等 `AutoClaude/tests@linux+*` 那兩列被量出來（豁免表逐字
    # 寫著取得配方＝act 映像跑 pytest，是排程中的下一步），表裡就再也挑不出「未量」的那一個，
    # `next()` 直接拋 StopIteration ⇒ 本支轉紅**且訊息是空的**（實測逐字只有 `StopIteration`）。
    # 那正是本支這一輪被改寫的原因（測試釘住磁碟狀態、過期時指不出路），不可以在修它的
    # 同一支裡復發——尤其這一次連「請改寫本支」那句話都不會印出來。
    # 受測物仍然是真的 `skip_target_report`／`profile_registered`：後者讀的就是下面被
    # monkeypatch 的那兩張天花板表（與本檔 darwin 那一支的降級注入分支同一個手法），
    # 合成的只有「剖面叫什麼名字」這一格，而判準的形狀（`all` 不是 `any`）與名字無關。
    measured = "tools/tests@synth-with-ceiling"
    unmeasured = "tools/tests@synth-without-ceiling"
    zero_ceiling = dict.fromkeys(P.SKIP_GROUPS, 0)
    monkeypatch.setitem(P._RUNTIME_SKIP_CEILING, measured, zero_ceiling)
    monkeypatch.setitem(P._RUNTIME_SKIP_CEILING_MAX, measured, zero_ceiling)
    assert P.profile_registered(measured), "合成基底壞了：`measured` 那一格應該算已登記"
    assert not P.profile_registered(unmeasured), (
        "合成基底壞了：`unmeasured` 那一格應該算未登記"
    )
    synthetic = "tools/tests@freebsd"   # 刻意不在真表裡：不動任何現存列的語意
    assert synthetic not in P._COMPLEMENTARY_PROFILE
    monkeypatch.setitem(P._COMPLEMENTARY_PROFILE, synthetic, (measured, unmeasured))
    gap = _complementary_gap_lines(synthetic)
    assert gap, (
        f"半登記的多對一集合（已量 `{measured}` ／未量 `{unmeasured}`）整組被放行 ⇒ "
        "MAC-01 迴歸（判準退回 `any` 短路）"
    )
    assert any(unmeasured in ln for ln in gap), gap
    assert not any(measured in ln for ln in gap), (
        f"已登記的 `{measured}` 被列進缺口清單 ⇒ 反向假事實：{gap}"
    )


def test_a_measured_counterpart_that_cannot_run_them_is_still_a_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """🔴 R83 四方複審（SA-02／SA falsified #1）的缺陷本體之鎖：**「已登記」≠「跑得到」**。

    WHY（Rule 9：這一支要在什麼商業語意變動時紅）：R82／MAC-01 把判準從「有沒有宣告互補
    剖面」改成「**每一個**宣告的互補剖面都有人量過」，於是判準只剩下**量測**這一個維度。
    R83 在 mac 真機首次量到 `tools/tests@darwin` 並把它的互補剖面宣告成 `tools/tests@linux`
    ——而 mac 上被 skip 的那 44 支**全部**是 `[WINDOWS-NATIVE-ONLY]`（本輪 12 支檔實跑
    （讀數見 ONBOARDING.md §7 表②），述詞是 `os.name != "nt"`，linux 上
    `os.name == "posix"` ⇒ **linux 一支都跑不到**。因為 linux 剖面「已登記」，
    `skip_target_report('tools/tests@darwin', …)` 回空 list＝已達標 ⇒ 唯一能為「兩平台
    聯集才是零」作證的報告者被那一筆登記親手關掉（與 MAC-01 修掉的短路同型、方向相反）。

    修法不是把資料改對就算——下一輪照樣可以再填錯一次，而且填錯是靜默的。判準改為由
    **標籤語意**（`_TAG_HOME_PLATFORMS`：`[WINDOWS-NATIVE-ONLY]` 的家只有 win32、
    `[MAC-NATIVE-ONLY]` 只有 darwin、`[POSIX-NATIVE-ONLY]` 是 darwin 或 linux）算出
    「這個平台非得有哪些平台來承接」，再與手寫表宣告到的平台對帳。本支釘住三件事：
      ① 推導本身有鑑別力（三個平台各自算出來的需求不同，且不是空集合也不是全集）；
      ② 今天 `tools/tests@darwin` 的答案是**真的且可稽核的**（宣告到 win32、該剖面已量測
         ⇒ 回空 list 才是誠實的「已達標」，不是短路）；
      ③ **注入 R83 原版的錯誤宣告（只有 linux）必須紅**——沒有這一半，判準是綠的還是沒有
         鑑別力就分不出來（本 repo 對「鎖還在但恆綠」已有大量判例）。
    """
    # ── ① 推導的鑑別力：三個平台各自的需求都不同，且都不是 trivial 的空集合／全集 ──
    assert P.required_home_platforms("darwin") == {"win32"}, (
        "mac 上被 skip 的 platform 群只可能是 `[WINDOWS-NATIVE-ONLY]`（mac-only 與 "
        "POSIX-generic 在 mac 上本來就會跑）⇒ 唯一承接得住的是真 Windows。"
        f"實得：{P.required_home_platforms('darwin')}"
    )
    assert P.required_home_platforms("win32") == {"darwin", "linux"}
    assert P.required_home_platforms("linux") == {"win32", "darwin"}

    # ── ② 今天的答案為真且可稽核：darwin 宣告到一個**平台為 win32 且已量測**的剖面 ──
    homes = P._COMPLEMENTARY_PROFILE["tools/tests@darwin"]
    assert [c for c in homes if P._platform_of(c) == "win32" and P.profile_registered(c)], (
        "`tools/tests@darwin` 的互補剖面裡沒有任何**已量測的 win32 剖面** ⇒ 那 44 支 "
        f"`[WINDOWS-NATIVE-ONLY]` 今天沒有人承接，判準不得回空當已達標。實得：{homes}"
    )
    assert not _complementary_gap_lines("tools/tests@darwin"), (
        "宣告已覆蓋 win32 且該剖面已量測，卻仍報缺口 ⇒ 假缺口（反向假事實一樣貴）"
    )

    # ── ③ 反向鑑別力：注入 R83 原版的錯誤宣告 ⇒ 必須紅，且必須指名缺的是 win32 ────
    monkeypatch.setitem(P._COMPLEMENTARY_PROFILE, "tools/tests@darwin",
                        ("tools/tests@linux",))
    gap = _complementary_gap_lines("tools/tests@darwin")
    assert gap, (
        "把 darwin 的家填回 `tools/tests@linux`（已量測、但 `os.name != \"nt\"` 在那裡"
        "同樣成立、44 支一支都跑不到）之後判準仍然回空 ⇒ SA-02 假綠迴歸：判準又只在問"
        "「量過沒有」而不問「跑得到沒有」"
    )
    assert any("win32" in ln for ln in gap), (
        f"缺口行沒指名 win32——指不出「該去哪裡承接」就沒有人接得住這個交棒。實得：{gap}"
    )


#: 「宣告的承接者在平台層根本跑不到」的機械形態。判準是**充要**的而不是保守估計：
#: 互補剖面 `c` 對剖面 `prof` 有用 ⟺ 存在某個標籤，它的家不含 `prof` 的平台（所以在
#: `prof` 上會被 skip）、卻含 `c` 的平台（所以在 `c` 上跑得到）⟺
#: `_platform_of(c) ∈ required_home_platforms(_platform_of(prof))`。落在外面的那一格就是
#: 一筆**今天為假的資料**，不是「多寫一格比較保險」。
def _counterparts_that_cannot_run_them() -> list[str]:
    """純函式：表裡有哪幾格宣告了跑不到的平台。回空 list ＝整張表的每一格今天都為真。"""
    bad: list[str] = []
    for prof, counterparts in P._COMPLEMENTARY_PROFILE.items():
        needed = P.required_home_platforms(P._platform_of(prof))
        bad += [f"{prof} → `{c}`（平台 {P._platform_of(c)} 不在需求 {sorted(needed)} 內）"
                for c in counterparts if P._platform_of(c) not in needed]
    return bad


def test_a_counterpart_that_cannot_run_them_may_not_sit_in_the_table_either(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """🔴 R83 獨立驗證輪補洞：SA-02 的收斂版只抓「少宣告」，抓不到「多宣告」。

    WHY（Rule 9：這一支要在什麼語意變動時紅）：SA-02 的缺陷本體是**表裡有一句今天為假的
    話**——darwin 上那 44 支 `[WINDOWS-NATIVE-ONLY]` 被宣告成「由 linux 承接」，而
    `os.name != "nt"` 在 linux 同樣成立、一支都跑不到；假話造成了假綠。收斂版把判準改成
    「需求平台 − **已宣告**平台」的差集，於是把 win32 **替換**成 linux 會紅
    （`test_a_measured_counterpart_that_cannot_run_them_is_still_a_gap` ③ 釘住那一向）。

    但 SA 原本開的處方是**並列**（`("tools/tests@linux", "tools/tests@win32")`），差集在那個
    狀態下是空的。本輪實測：並列版 `skip_target_report('tools/tests@darwin', census44)`
    回 `[]` ⇒ **那句假話可以原封不動住回表裡而沒有任何東西轉紅**。這正是該模組自己的判例
    逐字寫著的形態（「反向假事實與漏報同樣貴」），也正是收斂者用來駁回 SA 處方的那個理由
    ——判準必須真的守得住那個理由，否則駁回的依據只存在於散文裡。

    為什麼判準住在測試、不住在 `skip_target_report`：後者刻意**不接任何閘門的 rc**
    （模組註解逐字：「今天必然有缺口，把它接上 rc 只會製造一個所有人都學會忽略的常紅」），
    加在那裡只會多印一行 advisory、不會紅。另一半理由是這條規則是**資料表的不變量**、
    不需要在執行期存在；而 `tools/lib/skip_group_policy.py` 現值 399／上限 400（餘裕 1 行），
    把它塞進去會逼著再壓縮一次那個檔（本輪已因同一條線把 4 個 docstring 改成 `#`）。
    """
    assert _counterparts_that_cannot_run_them() == [], _counterparts_that_cannot_run_them()

    # ── 紅向自證 (a)：SA 原處方（linux 與 win32 並列）——差集判準對它結構上失明 ─────
    with monkeypatch.context() as mp:
        mp.setitem(P._COMPLEMENTARY_PROFILE, "tools/tests@darwin",
                   ("tools/tests@linux", "tools/tests@win32"))
        assert not _complementary_gap_lines("tools/tests@darwin"), (
            "本支存在的前提是「差集判準對並列版失明」。若它現在自己會報缺口，說明 "
            "`skip_target_report` 已涵蓋這一向 ⇒ 請把本支併回去，不要讓同一件事有兩個家"
        )
        assert any("→ `tools/tests@linux`" in b for b in _counterparts_that_cannot_run_them()), (
            "把 `tools/tests@linux` 並列進 darwin 的承接者，卻沒有任何東西轉紅 ⇒ 表裡可以"
            f"住一句今天為假的話。實得：{_counterparts_that_cannot_run_them()}"
        )
    # ── 紅向自證 (b)：把剖面自己列為自己的承接者（`platform` 群在那裡本來就會 skip）──
    with monkeypatch.context() as mp:
        mp.setitem(P._COMPLEMENTARY_PROFILE, "tools/tests@win32",
                   ("tools/tests@linux", "tools/tests@darwin", "tools/tests@win32"))
        assert any("→ `tools/tests@win32`" in b for b in _counterparts_that_cannot_run_them()), (
            "自我承接（`X` 的互補剖面填了 `X` 自己）是這一族最省力的假綠寫法，必須被抓到。"
            f"實得：{_counterparts_that_cannot_run_them()}"
        )


def test_every_platform_group_tag_has_a_home_platform() -> None:
    """🔴 R83 獨立驗證輪補洞：推導的**分母是手寫的**，而漏一個標籤是靜默的。

    WHY（Rule 9）：SA-02 的收斂把「誰承接得住」從手寫改成由 `_TAG_HOME_PLATFORMS` 推導，
    這是對的方向——但那張表的**鍵**仍然完全手寫，而 `platform` 群的權威成員住在
    `_TAG_GROUP`（值＝`SKIP_GROUP_PLATFORM`）。兩邊不一致時**沒有任何東西會說話**：
    `required_home_platforms()` 只是少算一族需求 ⇒ `homeless` 差集變小 ⇒ 缺口行少印一個
    平台，而判準照樣回綠。這正是本 repo 一路在治的「分母是手寫清單、失明是靜默的」形態
    （R71 起的判例：鎖還在、判準還在、測試全綠）。

    判準取**相等**而不是包含，兩個方向各有代價：
      · 少一個鍵 ⇒ 新增的平台族（日後若有 `[BSD-NATIVE-ONLY]` 之類）整片失明；
      · 多一個鍵 ⇒ 把不屬於 `platform` 群的標籤（`[DEBT]`／`[ENV-DISABLED]` 這種**可歸零**
        的）算成「非得由別的平台承接」，會憑空造出假需求、逼出永遠關不掉的假缺口。
    """
    platform_tags = {t for t, g in P._TAG_GROUP.items() if g == P.SKIP_GROUP_PLATFORM}
    assert set(P._TAG_HOME_PLATFORMS) == platform_tags, (
        "`_TAG_HOME_PLATFORMS` 的鍵與 `platform` 群的權威成員（`_TAG_GROUP`）不一致 ⇒ "
        "`required_home_platforms()` 算出來的需求集合是錯的，而它錯的時候不會有人說話。"
        f"缺：{platform_tags - set(P._TAG_HOME_PLATFORMS)}"
        f"／多：{set(P._TAG_HOME_PLATFORMS) - platform_tags}"
    )
    # 每一個「家」都必須是真的有執行者的平台，否則「非得由它承接」是一句接不住的空話
    accounted = {P._platform_of(p) for p in P._FULL_SUITE_RUNNERS}
    for tag, homes in P._TAG_HOME_PLATFORMS.items():
        assert homes, (
            f"{tag} 一個家都沒有 ⇒ 它在每個平台上都會被 skip、卻永遠不會被任何一列要求承接"
        )
        assert set(homes) <= accounted, (
            f"{tag} 的家 {homes} 含不在 `_FULL_SUITE_RUNNERS` 平台集合 {sorted(accounted)} "
            "內的平台——推導出來的需求會指向一個沒有任何執行者的平台，那是接不住的交棒"
        )


def test_ci_platform_coverage_is_accounted_for() -> None:
    """S3-02：唯一跑整棵樹的 CI job 在 ubuntu，而剖面表一個 linux 都沒有。

    這件事此前零登記 ⇒ 既不會被修也不會被想起來。帳算得清（登記或具名豁免）才算合格；
    豁免表另有 shrink-only 上限，加一個「跑得到卻沒人量」的平台必須顯式上修常數。
    """
    assert P.ci_platform_coverage_problems() == []
    assert "linux" in P._UNMEASURED_CI_PLATFORMS  # 缺口是**被登記**的，不是被消滅的


def test_ci_platform_coverage_is_red_when_a_platform_is_neither_measured_nor_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """反向鑑別力：新增一個會跑整棵樹的 CI 平台、又不具名豁免 ⇒ 紅。

    🔴 R82：注入的平台由 `darwin` 換成 `freebsd`——darwin 已經**真的**進了
    `_FULL_SUITE_RUNNERS`（MAC-01），拿它當注入標的會讓本支恆綠（分母裡已經有它）。
    這正是「注入基底腐化」的典型：判準沒壞，但它注入的東西不再是缺口。
    """
    monkeypatch.setitem(P._CI_FULL_SUITE_PLATFORMS, "freebsd", "假想的 FreeBSD full-suite job")
    problems = P.ci_platform_coverage_problems()
    assert any("freebsd" in p for p in problems), problems


def test_the_nightly_runner_profile_is_the_one_that_can_actually_be_measured() -> None:
    """🔴 R82（RUNNER-01）：nightly 那一路登記的剖面鍵必須是**量得到**的那一個。

    WHY（Rule 9）：舊鍵 `AutoClaude/tests@win32+nopg+solo` 結構上永遠量不到——PG 容器
    長駐，而 `tests/conftest.py::pytest_configure` 在收集前就 autodetect 注入 DSN ⇒
    nightly 必然落在 `+pg+solo`。帳上寫著「已登記一個執行者」，指的卻是一個不存在的
    執行者；每天真的在跑的那一個一格判準都沒有（實測 nightly log 逐字印
    `⚠️ 剖面未登記`）。這種失效不會有紅燈，只會有一行 advisory。
    """
    assert "AutoClaude/tests@win32+pg+solo" in P._FULL_SUITE_RUNNERS
    assert "AutoClaude/tests@win32+nopg+solo" not in P._FULL_SUITE_RUNNERS, (
        "量不到的舊鍵又回來了——它會讓 nightly 那一路的天花板永遠停在 advisory"
    )
    # 豁免理由必須指名承接帳本列（既有判準），且必須寫得出「怎麼量」——否則交棒等於沒交
    exempt = P._UNMEASURED_RUNNER_PROFILES["AutoClaude/tests@win32+pg+solo"]
    assert "nightly_latest.log" in exempt, f"豁免理由沒寫出取得管道：{exempt!r}"


#: 「可跑的配方」的機械形態：至少指名一支真的跑得起來的載具／可抄的產物。
#: 只認這四種副檔名是刻意的——`_HANDOVER_POINTER_RE` 已經在管「有沒有承接帳本列」，
#: 這裡管的是另一件事：**那一列到底要下什麼指令**。散文式的「以後再量」兩者都滿足不了。
_RECIPE_ARTIFACT_RE = re.compile(r"[\w./-]+\.(?:py|ps1|sh|log)\b")


def _recipeless_exemptions() -> list[str]:
    """純函式：`_UNMEASURED_RUNNER_PROFILES` 裡哪幾列的豁免理由**不構成可跑的配方**。

    回空 list ＝每一個還沒量到的剖面都寫出了「跑哪一支」＋「census 怎麼接」。
    """
    bad: list[str] = []
    for profile, why in P._UNMEASURED_RUNNER_PROFILES.items():
        if not _RECIPE_ARTIFACT_RE.search(why):
            bad.append(f"{profile}：沒指名任何可跑的載具／可抄的產物 → {why!r}")
        elif "census" not in why:
            bad.append(f"{profile}：沒寫出量到之後 census 怎麼接 → {why!r}")
    return bad


def test_the_darwin_runner_graduated_and_every_remaining_gap_still_has_a_recipe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """🔴 R82（MAC-01）立案、R83 畢業：darwin 已由「登記的缺口」轉成「量到的天花板」。

    R82 的原始缺陷：`macos-compat-ci.yml` 的 macOS smoke job 逐字
    `run: python3 tools/run_root_unittests.py`＝一個貨真價實的 full-suite darwin 執行者，
    卻不在 `_FULL_SUITE_RUNNERS` 裡 ⇒ 26 支 `[MAC-NATIVE-ONLY]` 連「有沒有人量過」都
    問不出來。R82 只做到誠實登記（分母升、分子不動）；R83 在 mac 真機跑完
    `python tools/run_root_unittests.py`、把它印出的 `[skip census]` 逐格填進
    `_RUNTIME_SKIP_CEILING{,_MAX}`，darwin 自此**有阻斷式天花板**。

    🔴 **為什麼要改寫（誠實劃界）**：本支 R82 版斷言的是 `tools/tests@darwin`
    **在** `_UNMEASURED_RUNNER_PROFILES` 裡＝「darwin 還沒人量過」，那是**狀態**而非性質，
    量到了就必然為假（它的訊息也已預告：「darwin 進了分母卻沒有具名豁免 ⇒ 會紅」）。
    原始意圖「未量測的剖面不得只是一個空缺口，必須有具名配方」**沒有過期**——它只是
    不再屬於 darwin，而該落到 `_UNMEASURED_RUNNER_PROFILES` 剩下的每一列身上。故改寫成：

      ① **畢業是完整的、而且被棘輪扣住**：darwin 仍在分母、兩張天花板表都有它、
         且**已從豁免表移除**（留著就是把有人守的寫成沒人守——`ci_platform_coverage_problems`
         第④向管的正是這個反向假事實）。降級（拔掉天花板）必須當場紅，
         這由本支的注入分支現地證明，不靠 `_MEASURED_RUNNERS_MIN` 這個常數被人記得改。
      ② **配方規則量化到整張豁免表**（原意圖的新家）：每一列都要寫出「跑哪一支」
         （可跑的 `.py`／`.ps1`／`.sh`／可抄的 `.log`）＋「census 怎麼接」。
         🔴 刻意**不**斷言豁免表非空——全部畢業是好事，而「誠實登記缺口不得有代價」
         的對偶是「把缺口清空也不得有代價」。表空掉時①與注入分支仍有鑑別力。
      ③ 豁免表不得留下**不在分母裡**的殘列：`ci_platform_coverage_problems()` 是以分母
         為迴圈的，一列豁免掛在沒人跑的剖面上會被它整格略過，於是那句「還沒量」永遠
         沒有人來還——與 R82 抓到的 `+nopg+solo`（帳上有、世界上沒有）同型。
    """
    darwin = "tools/tests@darwin"
    # ① 畢業完整性
    assert darwin in P._FULL_SUITE_RUNNERS, (
        "darwin 又從分母裡消失了——它消失時不會有任何紅燈（分母沒了，缺口也跟著看不見）"
    )
    assert darwin in P._RUNTIME_SKIP_CEILING, f"{darwin} 沒有基線天花板"
    assert darwin in P._RUNTIME_SKIP_CEILING_MAX, (
        f"{darwin} 只進了基線表、沒進 MAX 表 ⇒ `profile_registered()` 仍為 False，"
        "天花板實際上停在 advisory。半套畢業不算畢業"
    )
    assert P.profile_registered(darwin)
    assert darwin not in P._UNMEASURED_RUNNER_PROFILES, (
        "darwin 已經量到天花板了，卻還掛在未量測豁免表裡——把有人守的寫成沒人守，"
        "與反向一樣是假事實（`ci_platform_coverage_problems()` 第④向）"
    )
    # ② 配方規則的新家＝整張豁免表
    assert _recipeless_exemptions() == [], _recipeless_exemptions()
    # ③ 豁免表不得有不在分母裡的殘列
    orphans = set(P._UNMEASURED_RUNNER_PROFILES) - set(P._FULL_SUITE_RUNNERS)
    assert orphans == set(), (
        "豁免表有剖面不在 `_FULL_SUITE_RUNNERS` 裡 ⇒ 以分母為迴圈的涵蓋帳會整格略過它，"
        f"那句「還沒量」自此無人承接。殘列：{orphans}"
    )

    # ── 紅向自證（三種退步，每一種都必須當場被抓到）──────────────────────────
    # (a) 把 darwin 的天花板拔掉（＝退回 advisory）：涵蓋帳必須紅，不能靜默降級
    with monkeypatch.context() as mp:
        mp.delitem(P._RUNTIME_SKIP_CEILING, darwin)
        mp.delitem(P._RUNTIME_SKIP_CEILING_MAX, darwin)
        assert not P.profile_registered(darwin)
        assert any(darwin in prob for prob in P.ci_platform_coverage_problems()), (
            "拔掉 darwin 的天花板卻沒有任何東西轉紅 ⇒ 這道棘輪對「悄悄降級」失明"
        )
    # (b) 只拔 MAX 表（半套降級，最像沒事的那一種）
    with monkeypatch.context() as mp:
        mp.delitem(P._RUNTIME_SKIP_CEILING_MAX, darwin)
        assert any(darwin in prob for prob in P.ci_platform_coverage_problems())
    # (c) 豁免理由退化成散文（沒有可跑的載具）：配方判準必須抓到
    with monkeypatch.context() as mp:
        mp.setitem(P._UNMEASURED_RUNNER_PROFILES, darwin, "以後再量。DEF-101-960")
        assert any(darwin in b for b in _recipeless_exemptions()), _recipeless_exemptions()


def test_the_third_tree_is_inside_the_skip_governance_frame() -> None:
    """🔴 R82（SDD-01）：`AISDLC_SDD` 那一棵樹必須在分母裡。

    WHY：本 repo 有三棵測試樹，而 skip 治理此前只看兩棵——`AISDLC_SDD/scripts/ci-gate.sh`
    全檔對 census 零命中，`_FULL_SUITE_RUNNERS` 五個鍵沒有一個屬於它。實測那棵樹的
    skip 共 6 支（該樹的全套計數刻意不在此重述一份——基線數字唯一出處＝ONBOARDING.md
    §7 表②，同本檔 `_HEALTHY_TAIL` 上方的理由），六支**一支都沒有標籤** ⇒ 它的 skip
    可以無聲從 6 長到 60 而所有閘門全綠（R79 立這道棘輪時寫的原話，只是當時沒有人把
    第三棵樹算進來）。

    誠實劃界：本輪只做到「進帳 ＋ 補標籤」，census **還沒有**接上它的閘門——所以它是
    具名豁免而不是已量測；豁免理由必須寫出接線順序（先接閘門再入表）。
    """
    key = "AISDLC_SDD/fsm_runtime@win32"
    assert key in P._FULL_SUITE_RUNNERS, (
        "第三棵樹又從分母裡消失了——它消失的時候不會有任何紅燈，那正是本支存在的理由"
    )
    assert key in P._UNMEASURED_RUNNER_PROFILES
    exempt = P._UNMEASURED_RUNNER_PROFILES[key]
    assert "ci-gate.sh" in exempt, f"豁免理由沒寫出該改哪一支閘門：{exempt!r}"
    assert "--census-only" in exempt, f"豁免理由沒寫出接法：{exempt!r}"


def test_profile_key_encodes_the_nested_session_dimension() -> None:
    """S3-09：同一棵樹在巢狀 session 內外是兩個母體（本次實測差一整族），
    剖面鍵不編碼它，天花板就永遠在比不同的東西。"""
    assert m._skip_profile(True, nested=True) != m._skip_profile(True, nested=False)
    assert m._skip_profile(True, nested=False).endswith("+solo")
    assert m.nested_from_log(m.pg_marker_line(True, nested=False)) is False
    assert m.nested_from_log("完全沒有標記的一份輸出") is None


def test_census_only_is_red_when_the_nested_marker_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """只有 PG 標記、沒有巢狀標記 ⇒ 剖面量不到 ⇒ fail-loud（同「量不到 ≠ 量到零」）。"""
    _pin_registered_profile(monkeypatch)
    half = _HEALTHY_LOG.replace(_MARKER_LINE, "AUTOCLAUDE-PG-DSN-IN-EFFECT=0")
    assert m.census_only(_write_log(tmp_path, half)) == m.CENSUS_FAIL
    assert "AUTOCLAUDE-NESTED-SESSION" in capsys.readouterr().out


def test_pg_dsn_shape_is_validated_with_a_message_that_points_at_this_repo() -> None:
    """S3-06：`AUTOCLAUDE_TEST_PG_DSN` 有兩類驅動需求互斥的消費端，卻零驗證。

    修前實測：照文件以外的**合法** DSN 形態（`postgresql://…`，psycopg2 吃得下）設值，
    非同步端那一批會在 fixture setup 硬炸，訊息由 SQLAlchemy 發出、指向 driver 選型，
    完全不提這個環境變數也不提這個 repo。判準要把那個反推變成一句話 ＋ 一條可貼上的指令。
    """
    conftest = _loaded_conftest()
    assert conftest is not None
    assert conftest.pg_dsn_problems(None) == []
    assert conftest.pg_dsn_problems("postgresql+asyncpg://a:b@h/db") == []
    problems = conftest.pg_dsn_problems("postgresql://a:b@h/db")
    assert len(problems) == 1
    assert "postgresql+asyncpg://a:b@h/db" in problems[0]  # 可直接複製的修法
    # `AUTOCLAUDE_DB_DSN` 的消費端全部自己 strip driver ⇒ 對它要求 async 是誤擋
    assert conftest.pg_dsn_problems("postgresql://a:b@h/db", require_async=False) == []


# =====================================================================
# (m) R82 包 A2（ENV-01）：延遲 SLA 不得被自動打開——這是本輪**做了才量出來**的反例
# =====================================================================
#
# 🔴 事情的經過（三步，缺任一步結論就會相反）：
#   ① 掃描結論：`tests/perf/test_pgvector_recall_perf.py` 的 reason 逐字寫「僅在 perf
#      machine 跑」，而實測「只設 `PG_REAL_ENABLED=1`、一個檔都沒改」即 `1 passed in
#      5.12s` ⇒ 看起來是**欠債型**（沒人記得設旗標），該接進 conftest 自動打開。
#   ② 本輪照做並實跑：第一次確實綠。
#   ③ 同一支在機器同時跑別的東西時實測
#      `AssertionError: pgvector recall p95=51.703ms ≥ 50.0ms`——同一份語料、同一顆 PG，
#      只差機器忙不忙。它量的是**延遲**，而延遲對負載敏感。
#
# ⇒ 自動打開會用一個**真缺陷**（每個開發者的預設迴圈多一支 flaky 閘門）換掉一個**假缺陷**
# （誤導文案）。正解是措辭訂正 ＋ 維持 opt-in。本組把這個結論釘住，讓下一個人照著同一份
# 掃描結論再做一次時當場紅——「照掃描建議做」與「做了之後量一次」是兩件事。

_PG_AUTO_FLAGS = ("SD07_REAL_PG_E2E_ENABLED", "PG_REAL_ENABLED")


def _run_autoenable(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> dict[str, str]:
    """在乾淨環境上跑一次 `_autoenable_real_pg_e2e()`，回傳它動過的旗標。"""
    conftest = _loaded_conftest()
    assert conftest is not None, "載不到 AutoClaude/tests/conftest.py——本鎖失效"
    for key in (*_PG_AUTO_FLAGS, "AUTOCLAUDE_TEST_PG_DSN", "AUTOCLAUDE_DB_DSN"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    conftest._autoenable_real_pg_e2e()
    return {k: conftest.os.environ.get(k) for k in _PG_AUTO_FLAGS}


def test_the_correctness_flag_opens_but_the_latency_flag_stays_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DSN 就位 ⇒ 只開**正確性**那一個旗標，`PG_REAL_ENABLED`（延遲 SLA）維持關閉。

    意圖（Rule 9）：這條分界不是潔癖，是量出來的——`SD07_REAL_PG_E2E_ENABLED` 管的是
    「這顆 PG 上跑得起來嗎」（確定性，有 PG 就該跑），`PG_REAL_ENABLED` 管的是
    「p95 有沒有低於 50ms」（對機器負載敏感，R82 實測同一支在忙碌時 51.703ms）。
    把後者接上自動偵測 ⇒ 每個開發者的預設迴圈多一支會隨鄰居行為翻紅的測試。
    """
    got = _run_autoenable(
        monkeypatch, {"AUTOCLAUDE_DB_DSN": "postgresql+asyncpg://a:b@h/db"})
    assert got["SD07_REAL_PG_E2E_ENABLED"] == "true", got
    assert got["PG_REAL_ENABLED"] is None, (
        f"延遲 SLA 旗標被自動打開了：{got}——R82 實測那會讓 "
        "`tests/perf/test_pgvector_recall_perf.py` 在機器忙碌時翻紅（p95=51.703ms ≥ 50ms）。"
        "reason 的措辭可以訂正，但 opt-in 這件事本身是對的"
    )


def test_no_dsn_means_no_flag_is_opened(monkeypatch: pytest.MonkeyPatch) -> None:
    """沒有 DSN ⇒ 一個旗標都不開（開了只是把 skip 換成一句更深的缺件訊息）。"""
    got = _run_autoenable(monkeypatch, {})
    assert got == {"SD07_REAL_PG_E2E_ENABLED": None, "PG_REAL_ENABLED": None}, got


def test_an_explicit_setting_is_never_overwritten(monkeypatch: pytest.MonkeyPatch) -> None:
    """顯式關掉是一個**決定**（CI 要隔離），自動偵測不得覆寫它。

    沒有這一支，最省力的實作是無條件 `os.environ[...] = ...`，那會在刻意設
    `SD07_REAL_PG_E2E_ENABLED=false` 的環境上跑出一批沒有人要求的 e2e。
    """
    got = _run_autoenable(monkeypatch, {
        "AUTOCLAUDE_DB_DSN": "postgresql+asyncpg://a:b@h/db",
        "SD07_REAL_PG_E2E_ENABLED": "false",
    })
    assert got["SD07_REAL_PG_E2E_ENABLED"] == "false", f"顯式值被覆寫了：{got}"


def test_the_perf_skip_reason_states_the_measured_reason_for_staying_opt_in() -> None:
    """reason 必須把「為什麼還是 opt-in」寫成**量到的數字**，不是「需要 perf machine」。

    修前那句話讓分流者以為要準備一台專用機器（實測不必：5.12s 就跑完）；但反過來寫成
    「其實隨時可以跑」也是假的（忙碌時 51.703ms）。兩種錯法都會讓下一輪做出錯的決定，
    所以判準同時擋住兩邊。
    """
    src = (
        Path(__file__).resolve().parents[1] / "perf" / "test_pgvector_recall_perf.py"
    ).read_text(encoding="utf-8")
    reason_start = src.index('reason="[ENV-DISABLED]')
    reason = src[reason_start:src.index("\n)", reason_start)]
    assert "僅在 perf machine 跑" not in reason, (
        f"又寫回「僅在 perf machine 跑」：{reason!r}——本機實測 5.12s 就跑完，那是假門檻"
    )
    assert "51.703ms" in reason, (
        f"reason 沒有寫出「維持 opt-in」的量測依據：{reason!r}"
        "——沒有數字的理由，下一輪會被當成可以拿掉的保守作風"
    )
    assert "PG_REAL_ENABLED" in reason, f"reason 沒有給出可貼的啟用配方：{reason!r}"
