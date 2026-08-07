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
_HEALTHY_LOG = (
    "SKIPPED [2] tests\\a.py:10: [POSIX-NATIVE-ONLY] 只在 POSIX 上有意義\n"
    "SKIPPED [1] tests\\b.py: [ENV-DISABLED] 沒設 DSN\n"
    "AUTOCLAUDE-PG-DSN-IN-EFFECT=0\n"
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


def test_profile_key_follows_the_dsn_not_the_injection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """剖面取決於「DSN 在不在」，不是「是不是我注入的」。

    WHY（R79 收輪訂正的實際缺陷）：剖面原本取自 `pg_autodetect()` 的回傳值，於是
    「使用者自己 export 過 DSN」那條路上它回 False、剖面判成 nopg——測試明明跑在有
    PG 的條件下（44 支），卻拿 nopg 的 118 上限去比，永遠通過。那不是紅，是沒有
    鑑別力，而且方向是「看起來很健康」。
    """
    for key in m._PG_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    assert m.pg_dsn_in_effect() is False
    monkeypatch.setenv("AUTOCLAUDE_TEST_PG_DSN", "postgresql://x/y")
    assert m.pg_dsn_in_effect() is True
    assert m._skip_profile(m.pg_dsn_in_effect()).endswith("+pg")


def test_pg_profile_marker_round_trips_and_absence_is_not_false() -> None:
    """標記缺席必須回 `None`（＝量不到），不得回 False（＝量到「沒有 PG」）。"""
    assert m.pg_in_effect_from_log("noise\n" + m.pg_marker_line(True)) is True
    assert m.pg_in_effect_from_log("noise\n" + m.pg_marker_line(False)) is False
    assert m.pg_in_effect_from_log("完全沒有標記的一份輸出") is None


def _clear_brakes(monkeypatch: pytest.MonkeyPatch) -> None:
    """把四條剎車全部放開。`AUTOCLAUDE_ALLOW_INSECURE_DB` 一併經 monkeypatch 走一遍：
    `pg_autodetect` 會 `setdefault` 它，沒登記還原點的話這幾支測試會把它留給整個
    session（測試不得改寫別人看得到的狀態）。"""
    for key in ("CI", m._AUTODETECT_OPT_OUT, "PYTEST_CURRENT_TEST",
                "AUTOCLAUDE_ALLOW_INSECURE_DB", *m._PG_ENV_KEYS):
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
    collapsed = "AUTOCLAUDE-PG-DSN-IN-EFFECT=0\n12 passed, 136 skipped in 9.0s\n"
    assert m.main(["--census-only", _write_log(tmp_path, collapsed)]) == m.CENSUS_FAIL
    no_marker = _HEALTHY_LOG.replace("AUTOCLAUDE-PG-DSN-IN-EFFECT=0\n", "")
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
    invocations = [
        ln for ln in _uncommented(leg)
        if "--census-only" in ln and "python" in ln and "echo" not in ln
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
