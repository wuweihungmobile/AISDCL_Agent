# enforces (governance rules): R-9.6
"""ADR-XPLAT-016 §3「跨專案環境契約」的守護測試（體檢 G-02／S-05 的 SDD 側）。

為什麼這組測試存在：Console／Bridge 要讓 SDD 的狀態住在**外部專案**（`SDD_STATE_DIR`），前提是
「狀態目錄只有一個解析點」——只要還有一個站點直接寫 `build/reports/fsm`，外部專案模式下就會
分裂成兩份狀態（狀態檔在外部、帳本與報告留在框架樹）。本檔逐項鎖住：

  · §3.2 解析優先序：`SDD_STATE_DIR`（絕對路徑）＞ 模組常數 `DEFAULT_STATE_DIR`（**呼叫時才讀**，
    既有測試以 monkeypatch 改它）；相對路徑 ⇒ `ValueError`（不是悄悄當成 cwd 相對）；
  · §3.4 七個目錄站點 A1～A7 全部跟隨同一個解析點；
  · §3.3／A8 外部專案模式（`SDD_STATE_DIR` 非空白）遙測回寫預設關——否則外部專案的每次轉態都會
    弄髒**版本目錄內被 git 追蹤的** `governance/rules/*.yaml`；顯式 `0／1` 仍優先；
  · hook 是 fail-open 載具：`SDD_STATE_DIR` 寫錯時退回預設目錄並出一行 ASCII 警告，不得崩潰。

反向對照（拿掉修法必須變紅）逐案寫在各 docstring：把 `state_dir()` 改回常數、拿掉 A8 分支、
hook 不包 try／except，各有一案會紅。
"""
from __future__ import annotations

import datetime as _dt
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

_V_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_V_ROOT))

from tools.fsm_runtime import fsm_runtime as fsm_mod  # noqa: E402
from tools.fsm_runtime import rule_loader, spec_monitor  # noqa: E402
from tools.fsm_runtime import state_loader as sl  # noqa: E402

_ENV = "SDD_STATE_DIR"
_HOOKS_DIR = _V_ROOT / ".claude" / "hooks"
_REAL_DEFAULT = _V_ROOT / "build" / "reports" / "fsm"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """本檔每案從「兩個環境變數都未設」起算（conftest 的沙盒已清過，這裡再明示一次）。"""
    monkeypatch.delenv(_ENV, raising=False)
    monkeypatch.delenv("SDD_PROJECT", raising=False)


# ───────────────────────────── §3.4 測試沙盒（S-09／G-17）仍然有效 ─────────────────────────────
def test_the_session_sandbox_is_active_so_tests_cannot_write_the_real_build_reports() -> None:
    """守住沙盒本身不被靜默拆掉：fixture 被改名／刪除／改成非 autouse 時，整套測試會**悄悄**回到寫真實的
    `build/reports/`（體檢實測跑完多出 9 個檔、7 支 `FSM-STATE-test-*` 假專案），而每一支測試照樣綠。
    本案直接量沙盒的**現況**：預設目錄不是真實目錄、仍是 `build/reports/fsm` 的形狀（既有
    `.name == "fsm"` 斷言不破）、各個載入時求值的常數都被導向同一處。（兩個環境變數的清除與「測試不得洩漏
    它們」由 conftest 的函式級 autouse 守衛 `_no_test_leaks_the_state_env` 在每支測試的 teardown 判定。）"""
    from tools.fsm_runtime import production_monitor, snapshot, subagent_contract

    sandbox = sl.DEFAULT_STATE_DIR
    assert sandbox != _REAL_DEFAULT and _V_ROOT not in sandbox.parents, f"沙盒失效：{sandbox}"
    assert sandbox.parts[-3:] == ("build", "reports", "fsm")
    assert sandbox.is_dir()
    assert production_monitor.DEFAULT_DRIFT_LOG_DIR == sandbox
    assert subagent_contract.BYPASS_LOG_DIR == sandbox
    for outside_fsm in (snapshot.SNAPSHOT_DIR, subagent_contract.DISPATCH_LOG_DIR):
        assert _V_ROOT not in outside_fsm.parents, f"abort／test-analysis 目錄沒被導向沙盒：{outside_fsm}"


# ───────────────────────────── §3.2 解析優先序 ─────────────────────────────
def test_unset_returns_the_module_constant_and_binds_late(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """未設環境變數 ⇒ 回 `DEFAULT_STATE_DIR`，且是**呼叫時才讀**（晚綁定）。

    既有測試（test_path_cost／test_phase_i_m5 等）靠 monkeypatch 改這個常數。反向對照：把
    `state_dir()` 改成回「匯入時抓住的值」，下面第二個斷言會紅。
    """
    assert sl.state_dir() == sl.DEFAULT_STATE_DIR
    patched = tmp_path / "patched-default"
    monkeypatch.setattr(sl, "DEFAULT_STATE_DIR", patched)
    assert sl.state_dir() == patched
    assert sl._default_state_path("p").parent == patched
    assert sl.track_state_path("p", track_id="t").parent == patched


@pytest.mark.parametrize("blank", ["", " ", "   ", "\t"])
def test_blank_env_is_treated_as_unset(blank: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_ENV, blank)
    assert sl.state_dir() == sl.DEFAULT_STATE_DIR


def test_absolute_env_wins_over_the_module_constant_and_is_not_resolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sl, "DEFAULT_STATE_DIR", tmp_path / "default")
    raw = str(tmp_path / "a" / ".." / "ext")  # 含 `..`：原樣回傳＝沒有 resolve()／normpath
    monkeypatch.setenv(_ENV, raw)
    assert sl.state_dir() == Path(raw)
    assert ".." in sl.state_dir().parts


def test_env_value_is_stripped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_ENV, f"  {tmp_path}  ")
    assert sl.state_dir() == Path(str(tmp_path))


@pytest.mark.parametrize("relative", ["relative/dir", "x", ".", "..", "./x", "../x", "相對/路徑"])
def test_relative_env_is_rejected_and_names_the_variable(
    relative: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """相對路徑一律 ValueError：Bridge 的 cwd 是 SDD 版本目錄、hook 的 cwd 是專案根、人的 cwd 任意，
    同一個變數會在三處指向不同目錄＝靜默的檔案分裂。訊息必須指名該變數、且純 ASCII（CLI 入口無
    UTF-8 stdio 保護，錯誤會原樣印到 stderr）。"""
    monkeypatch.setenv(_ENV, relative)
    with pytest.raises(ValueError) as err:
        sl.state_dir()
    message = str(err.value)
    assert _ENV in message
    message.encode("ascii")  # 非 ASCII 的路徑以跳脫形式出現，不得讓 stderr 在 cp950 下炸掉


def test_rooted_path_without_drive_follows_platform_semantics(monkeypatch: pytest.MonkeyPatch) -> None:
    """鐵律三自問：`/data/state` 在另一個平台是什麼值？POSIX＝絕對路徑；Windows＝沒有磁碟機代號的
    路徑**不是**絕對路徑（pathlib 的定義），要拒絕。兩個平台各有確定答案，不 skip。"""
    monkeypatch.setenv(_ENV, "/data/state")
    if sys.platform == "win32":
        with pytest.raises(ValueError):
            sl.state_dir()
    else:
        assert sl.state_dir() == Path("/data/state")


def test_state_files_follow_the_env_but_an_explicit_path_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ext = tmp_path / "ext"
    monkeypatch.setenv(_ENV, str(ext))
    assert sl.track_state_path("proj") == ext / "FSM-STATE-proj.yaml"
    assert sl.track_state_path("proj", track_id="t1") == ext / "FSM-STATE-proj-t1.yaml"
    state = sl.load_state("proj")  # 缺檔 ⇒ 由模板建在外部目錄
    assert state.path == ext / "FSM-STATE-proj.yaml" and state.path.is_file()
    other = tmp_path / "explicit" / "FSM-STATE-x.yaml"
    explicit = sl.load_state("proj2", path=other)  # 優先序 1：呼叫端顯式 path 不經解析點
    assert explicit.path == other and other.is_file()
    assert not (ext / "FSM-STATE-proj2.yaml").exists()


def test_bootstrap_reads_project_and_dir_from_the_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(_ENV, str(tmp_path / "ext"))
    monkeypatch.setenv("SDD_PROJECT", "console-proj")
    runtime = fsm_mod.FSMRuntime.bootstrap()
    assert runtime.state.path == tmp_path / "ext" / "FSM-STATE-console-proj.yaml"


@pytest.mark.parametrize("blank", ["", "  ", "\t"])
def test_blank_project_env_is_treated_as_unset(blank: str, monkeypatch: pytest.MonkeyPatch) -> None:
    unset = sl.project_from_env()
    monkeypatch.setenv("SDD_PROJECT", blank)
    assert sl.project_from_env() == unset
    monkeypatch.setenv("SDD_PROJECT", "named")
    assert sl.project_from_env() == "named"


# ───────────────────────── §3.4 站點 A2～A7 跟隨同一個解析點 ─────────────────────────
def _ledger_file(directory: Path) -> Path:
    return directory / f"CONTEXT-LEDGER-{_dt.date.today().isoformat()}.yaml"


def _write_ledger(directory: Path, cumulative: int) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = _ledger_file(directory)
    path.write_text(
        yaml.safe_dump({"date": "d", "cumulative_tokens": cumulative, "entries": [{"tokens": cumulative}]}),
        encoding="utf-8",
    )
    return path


def test_a2_reset_today_ledger_resets_the_ledger_under_the_env_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A2：`complete-auto-compact` 歸零的必須是 hook 實際寫的那本帳（同一個解析點）。反向對照：
    改回 `REPO_ROOT/build/reports/fsm`，本案找不到外部目錄的帳本 ⇒ `reset=False` ⇒ 紅。"""
    ext = tmp_path / "ext"
    ledger = _write_ledger(ext, 777)
    monkeypatch.setenv(_ENV, str(ext))
    result = fsm_mod._reset_today_ledger()
    assert result["reset"] is True and result["previous_cumulative"] == 777
    assert Path(result["path"]) == ledger
    assert yaml.safe_load(ledger.read_text(encoding="utf-8"))["cumulative_tokens"] == 0


def test_a2_without_env_the_default_dir_is_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    default = tmp_path / "default"
    ledger = _write_ledger(default, 5)
    monkeypatch.setattr(sl, "DEFAULT_STATE_DIR", default)
    assert fsm_mod._reset_today_ledger()["path"] == str(ledger)


def _load_hook(script: str, tag: str):
    spec = importlib.util.spec_from_file_location(f"_sdd_state_dir_probe_{tag}", _HOOKS_DIR / script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("script", ["context_ledger_pre.py", "context_ledger_post.py"])
def test_a3_a4_hook_ledger_dir_follows_the_resolution_point(
    script: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ext = tmp_path / "ext"
    monkeypatch.setenv(_ENV, str(ext))
    assert _load_hook(script, "env").LEDGER_DIR == ext
    monkeypatch.delenv(_ENV)
    assert _load_hook(script, "default").LEDGER_DIR == sl.DEFAULT_STATE_DIR


@pytest.mark.parametrize("script", ["context_ledger_pre.py", "context_ledger_post.py"])
def test_a3_a4_hook_fails_open_on_a_relative_env(
    script: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """hook 是 fail-open 載具：`SDD_STATE_DIR` 寫成相對路徑時，匯入不得拋例外（否則每次工具呼叫的
    hook 都崩潰、守門整個失效）；退回**真正的預設目錄**並在 stderr 出一行 ASCII 警告。
    反向對照：拿掉 try／except，`exec_module` 會直接拋 ValueError ⇒ 紅。"""
    monkeypatch.setenv(_ENV, "relative/dir")
    module = _load_hook(script, "relative")
    assert module.LEDGER_DIR == _REAL_DEFAULT
    err_lines = [ln for ln in capsys.readouterr().err.splitlines() if ln.strip()]
    assert len(err_lines) == 1, err_lines
    assert err_lines[0].startswith("[SDD-HOOK]") and _ENV in err_lines[0]
    err_lines[0].encode("ascii")


def test_a5_spec_monitor_violation_report_follows_the_env_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = spec_monitor.MonitorResult(ok=False, violations=["TypeOK: probe"])
    ext = tmp_path / "ext"
    monkeypatch.setenv(_ENV, str(ext))
    written = Path(spec_monitor.write_violation_report(result, state_name="X"))
    assert written.parent == ext and written.is_file()
    monkeypatch.delenv(_ENV)
    monkeypatch.setattr(sl, "DEFAULT_STATE_DIR", tmp_path / "default")
    assert Path(spec_monitor.write_violation_report(result, state_name="X")).parent == tmp_path / "default"


_PRINT_LOAD_TIME_DIRS = (
    "import sys; sys.path.insert(0, sys.argv[1]);"
    "import tools.fsm_runtime.production_monitor as pm;"
    "import tools.fsm_runtime.subagent_contract as sc;"
    "print(pm.DEFAULT_DRIFT_LOG_DIR); print(sc.BYPASS_LOG_DIR)"
)


def _child_dirs(env_extra: dict) -> list[str]:
    env = {k: v for k, v in os.environ.items() if k not in (_ENV, "SDD_PROJECT")}
    env.update({"PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, "-c", _PRINT_LOAD_TIME_DIRS, str(_V_ROOT)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=60,
        cwd=str(_V_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip().splitlines()


def test_a6_a7_load_time_dirs_follow_the_env_in_a_fresh_process(tmp_path: Path) -> None:
    """A6（PBS-DRIFT 滾動檔）與 A7（旁路日誌）是**載入時求值**的模組常數：要在乾淨行程裡看，
    不能靠本行程已被 conftest 沙盒改寫過的值。"""
    ext = tmp_path / "ext"
    assert _child_dirs({_ENV: str(ext)}) == [str(ext), str(ext)]


def test_default_dirs_are_unchanged_when_the_env_is_unset() -> None:
    """「未設＝行為逐字不變」的**真值**：乾淨行程裡預設就是版本目錄的 build/reports/fsm。"""
    assert _child_dirs({}) == [str(_REAL_DEFAULT), str(_REAL_DEFAULT)]


# ───────────────────── §3.3／A8 外部專案模式：遙測回寫預設關 ─────────────────────
_FIRE = "SDD_ENABLE_RULE_FIRE_TELEMETRY"
_CATCH = "SDD_ENABLE_RULE_CATCH_TELEMETRY"
_REQUIRES_HOOK = "SDD_TELEMETRY_WRITEBACK_REQUIRES_HOOK"


@pytest.fixture()
def _telemetry_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """起算＝兩個遙測旗標與 hook 身分旗標都未設（conftest 預設把遙測旗標設成 "0"，這裡覆寫回 unset），
    並重置 D28 的「同行程只出聲一次」旗標，讓「不出聲」的斷言不被前一案影響。"""
    for name in (_FIRE, _CATCH, _REQUIRES_HOOK, "SDD_FSM_HOOK_ENTRY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(fsm_mod, "_telemetry_writeback_skip_warned", False)
    return monkeypatch


def test_a8_truth_table(
    tmp_path: Path, _telemetry_env: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    allowed = fsm_mod._telemetry_writeback_allowed
    env = _telemetry_env
    assert allowed(_FIRE) is True, "未設任何旗標＝v0.24 預設 ON（不得被 A8 連帶翻掉）"
    env.setenv(_ENV, "   ")
    assert allowed(_FIRE) is True, "純空白視同未設，不算外部專案模式"
    env.setenv(_ENV, str(tmp_path / "ext-state"))
    assert allowed(_FIRE) is False and allowed(_CATCH) is False, "外部專案模式預設關"
    env.setenv(_FIRE, "1")
    assert allowed(_FIRE) is True, "顯式值永遠優先（既有契約不變）"
    env.setenv(_FIRE, "0")
    assert allowed(_FIRE) is False
    env.delenv(_FIRE)
    capsys.readouterr()
    env.setenv(_REQUIRES_HOOK, "1")  # session 要求 hook 身分、本行程不是 hook ⇒ D28 本會出聲
    assert allowed(_FIRE) is False
    assert capsys.readouterr().err == "", "外部專案模式的關閉不出聲：它不是『漏加前綴的探針』（A8 排在 D28 之前）"


@pytest.fixture()
def _isolated_rules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """把 `rule_loader.RULES_DIR` 導向 tmp 的合成規則（絕不碰版本目錄內被追蹤的真規則）。"""
    rules = tmp_path / "rules"
    rules.mkdir()
    payload = {
        "id": "R-glob", "title": "synthetic", "trigger_states": ["*"], "severity": "medium",
        "maturity": "active", "spec": "synthetic", "test_ref": "",
        "scaffold_roi": {"fire_count": 0, "catch_count": 0, "false_positive_count": 0},
        "failure_mode": "synthetic failure mode",
    }
    (rules / "R-glob.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(rule_loader, "RULES_DIR", rules)
    return rules


def _roi(rules: Path) -> dict:
    return yaml.safe_load((rules / "R-glob.yaml").read_text(encoding="utf-8"))["scaffold_roi"]


def _runtime(tmp_path: Path) -> "fsm_mod.FSMRuntime":
    state = sl.load_state("a8", path=tmp_path / "FSM-STATE-a8.yaml")
    return fsm_mod.FSMRuntime(state)


def test_a8_external_mode_transition_writes_no_rule_telemetry(
    tmp_path: Path, _isolated_rules: Path, _telemetry_env: pytest.MonkeyPatch
) -> None:
    """外部專案模式下一次 `transition` 不得改動規則檔。反向對照（同一個夾具）：未設 `SDD_STATE_DIR`
    時同樣的 transition 會把 fire_count 寫成 1——所以「沒變」不是夾具失明，是 A8 分支真的擋下。
    拿掉 A8 分支，第一個斷言紅。"""
    before = (_isolated_rules / "R-glob.yaml").read_bytes()
    _telemetry_env.setenv(_ENV, str(tmp_path / "ext-state"))
    _runtime(tmp_path).transition("SCENARIO_DETECT", reason="external mode")
    assert (_isolated_rules / "R-glob.yaml").read_bytes() == before
    assert _roi(_isolated_rules)["fire_count"] == 0

    _telemetry_env.delenv(_ENV)
    _runtime(tmp_path).transition("AGENT_LOAD", reason="control group")
    assert _roi(_isolated_rules)["fire_count"] == 1, "對照組：未設 SDD_STATE_DIR 時預設 ON，必須記到 fire"


def test_a8_explicit_flag_still_wins_in_external_mode(
    tmp_path: Path, _isolated_rules: Path, _telemetry_env: pytest.MonkeyPatch
) -> None:
    _telemetry_env.setenv(_ENV, str(tmp_path / "ext-state"))
    _telemetry_env.setenv(_FIRE, "1")
    _runtime(tmp_path).transition("SCENARIO_DETECT", reason="explicit on")
    assert _roi(_isolated_rules)["fire_count"] == 1


def test_a8_external_mode_does_not_record_catches_either(
    tmp_path: Path, _isolated_rules: Path, _telemetry_env: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    _telemetry_env.setenv(_ENV, str(tmp_path / "ext-state"))
    runtime._record_escalation_catches(["R-glob"])
    assert _roi(_isolated_rules)["catch_count"] == 0
    _telemetry_env.delenv(_ENV)
    runtime._record_escalation_catches(["R-glob"])
    assert _roi(_isolated_rules)["catch_count"] == 1, "對照組：未設 SDD_STATE_DIR 時 catch 側同樣預設 ON"
