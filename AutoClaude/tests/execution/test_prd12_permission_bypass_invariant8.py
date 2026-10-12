"""PRD §6.1 不變式 8／§12 權限旗標：完全跳過權限只准「容器＋ALLOW_PERMISSION_BYPASS=true」。

立案（T4）：PRD §16.2「§12 權限旗標」那一列寫的再開症狀——「引擎於非容器環境以
bypassPermissions 跑了一次」——在 F-SBR-001 真跑（SddBridge_RealRun_Evidence_20261011.md）字面
成立。本檔把症狀本身釘成回歸：舊 fixture 的 config 必被拒、新 fixture 的 config 必放行，
判決表每一格各有一支紅綠。

四層判準，各守一個失效方向：
  (a) 偵測：容器訊號各自單獨成立；主機（含 macOS 上被偽造的訊號）一律不成立。
  (b) 設定面：兩條路（SDK 的 permission_mode、PTY 的 extra_args）都被看見，且不誤傷相似字面。
  (c) 判決表：「旗標明確為真」與「偵測到容器」兩個要件缺一不可。
  (d) 入口：`main()` 在任何 step 之前以 rc=1 拒絕；真實的 F-SBR-001 範本照常放行。
"""
from __future__ import annotations

import inspect
import json
import logging
import re
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from autoclaude import main as main_mod
from autoclaude.core.kernel_state import KernelResult
from autoclaude.execution import boot_self_check as B
from autoclaude.utils import platform_caps
from autoclaude.utils.config import load_config

_AUTOCLAUDE = Path(__file__).resolve().parents[2]
_TEMPLATE = _AUTOCLAUDE / "scripts" / "bridge_e2e" / "wordcount" / "config.template.yaml"
_PLAYBOOK = _AUTOCLAUDE / "scripts" / "example_playbook.yaml"
_HOST = B.IsolationEvidence()                       # 一般主機：沒有任何容器證據
_BOX = B.IsolationEvidence(sources=("dockerenv",))  # 容器：有證據


# ══════════════════════════════════════════════════════════════════════════════
# (a) 偵測：路徑／env／平台全部注入，測試絕不讀真實 /proc、也不看真實環境
# ══════════════════════════════════════════════════════════════════════════════
def _probe(tmp_path: Path, *, dockerenv: bool = False, cgroup: str | None = None,
           env: dict[str, str] | None = None,
           on_linux: bool = True) -> B.IsolationEvidence:
    marker = tmp_path / "dockerenv"
    if dockerenv:
        marker.write_text("", encoding="utf-8")
    cg = tmp_path / "cgroup"
    if cgroup is not None:
        cg.write_text(cgroup, encoding="utf-8")
    return B.detect_isolation_env(environ=env or {}, on_linux=on_linux,
                                  dockerenv=marker, cgroup=cg)


_EVERY_SIGNAL = {"dockerenv": True, "cgroup": "12:cpuset:/docker/ab12\n",
                 "env": {"container": "podman", "KUBERNETES_SERVICE_HOST": "10.0.0.1"}}


@pytest.mark.parametrize("kwargs, source", [
    pytest.param({"dockerenv": True}, "dockerenv", id="dockerenv-file"),
    pytest.param({"cgroup": "12:cpuset:/docker/ab12\n"}, "cgroup:docker", id="cgroup-docker"),
    pytest.param({"cgroup": "1:name=systemd:/system.slice/containerd.service\n"},
                 "cgroup:containerd", id="cgroup-containerd"),
    pytest.param({"cgroup": "4:cpu:/kubepods/burstable/pod1\n"},
                 "cgroup:kubepods", id="cgroup-kubepods"),
    pytest.param({"cgroup": "3:memory:/LXC/c1\n"}, "cgroup:lxc", id="cgroup-lxc-any-case"),
    pytest.param({"env": {"container": "podman"}}, "env:container=podman", id="env-container"),
    pytest.param({"env": {"KUBERNETES_SERVICE_HOST": "10.0.0.1"}},
                 "env:KUBERNETES_SERVICE_HOST", id="env-kubernetes"),
])
def test_each_container_signal_alone_is_enough_on_linux(tmp_path, kwargs, source):
    """每個訊號各自單獨成立：容器執行階段的標記互不相同，只認其中一種就會漏掉另外幾種。"""
    ev = _probe(tmp_path, **kwargs)
    assert ev.detected is True
    assert source in ev.sources


def test_a_bare_linux_host_is_not_isolated(tmp_path):
    """對照組：沒有任何訊號、或 PID 1 的 cgroup 只是主機的 init，不得被讀成容器。"""
    assert _probe(tmp_path).detected is False
    assert _probe(tmp_path, cgroup="0::/init.scope\n").detected is False
    assert _probe(tmp_path, cgroup="12:cpuset:/user.slice/session-3.scope\n").sources == ()


def test_no_signal_counts_outside_linux_even_when_all_are_present(tmp_path):
    """macOS 行程不可能在 Linux 容器內（Docker Desktop 的容器跑在它自己的 Linux VM 裡），
    所以非 Linux 上的 `container=`／KUBERNETES_* 只會是雜訊或偽造，不得因此放行 bypass。

    正向對照放在同一支測試裡：同一組訊號在 linux 上必須成立，否則下面的「不成立」是空轉。
    """
    assert _probe(tmp_path, on_linux=True, **_EVERY_SIGNAL).detected is True
    ev = _probe(tmp_path, on_linux=False, **_EVERY_SIGNAL)
    assert ev.detected is False
    assert ev.sources == ()


@pytest.mark.parametrize("plat, expected", [
    ("linux", True), ("darwin", False), ("win32", False), ("freebsd14", False)])
def test_the_default_platform_probe_goes_through_platform_caps(tmp_path, plat, expected):
    """生產路徑不注入 on_linux：平台判斷必須走 `platform_caps`（架構鎖：全樹平台判斷只住那一處）。
    以既有慣例 patch `platform_caps.sys.platform` 驗；mac 上偽造的容器訊號因此一律失效。"""
    marker, cg = tmp_path / "dockerenv", tmp_path / "cgroup"
    marker.write_text("", encoding="utf-8")
    cg.write_text("12:cpuset:/docker/ab12\n", encoding="utf-8")
    with patch("autoclaude.utils.platform_caps.sys.platform", plat):
        ev = B.detect_isolation_env(environ={"container": "podman"}, dockerenv=marker, cgroup=cg)
    assert ev.detected is expected


@pytest.mark.parametrize("plat, expected", [
    ("linux", True), ("linux2", True), ("darwin", False), ("win32", False), ("cygwin", False)])
def test_is_linux_only_accepts_linux(plat, expected):
    with patch("autoclaude.utils.platform_caps.sys.platform", plat):
        assert platform_caps.is_linux() is expected


def test_blank_env_values_are_not_evidence(tmp_path):
    env = {"container": "   ", "KUBERNETES_SERVICE_HOST": ""}
    assert _probe(tmp_path, env=env).detected is False


class _Denied:
    """權限／I/O 讀不到的標記檔：`exists()`／`read_text()` 都丟 OSError。"""

    def exists(self) -> bool:
        raise PermissionError("denied")

    def read_text(self, *args, **kwargs) -> str:
        raise PermissionError("denied")


def test_an_unreadable_marker_is_no_evidence_not_a_crash():
    """守門不能因為讀不到標記檔就讓整個啟動崩潰（那會把「偵測失敗」變成「不能啟動任何東西」）；
    讀不到＝沒有證據，結果是保守的『不是容器』。"""
    ev = B.detect_isolation_env(environ={}, on_linux=True,
                                dockerenv=_Denied(), cgroup=_Denied())
    assert ev.detected is False


def test_the_default_probe_paths_are_the_conventional_markers():
    """預設路徑就是容器執行階段的慣例標記；字面寫錯時，生產環境的偵測會靜默變成『永遠不是容器』，
    而所有注入路徑的測試照樣全綠——這一支是它們唯一碰不到的那一格。"""
    params = inspect.signature(B.detect_isolation_env).parameters
    assert params["dockerenv"].default.name == ".dockerenv"
    assert params["cgroup"].default.as_posix().endswith("proc/1/cgroup")


# ══════════════════════════════════════════════════════════════════════════════
# (b) 設定面：兩條路都看得見、相似字面不誤傷
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("mode", ["default", "acceptEdits", "plan", "dontAsk", "auto", "", None])
def test_non_bypass_permission_modes_are_not_a_request(mode):
    assert B.permission_bypass_requests(mode, []) == ()


def test_the_sdk_path_permission_mode_is_a_request():
    """SDK 後端讀 executor.permission_mode——ExecutorConfig 的 Literal 本來就允許這個值。"""
    assert B.permission_bypass_requests("bypassPermissions") == (
        "executor.permission_mode=bypassPermissions",)


@pytest.mark.parametrize("extra_args", [
    pytest.param(["--permission-mode", "bypassPermissions", "--model", "haiku"],
                 id="the-f-sbr-001-historical-config"),
    pytest.param(["--model", "haiku", "--permission-mode=bypassPermissions"], id="equals-form"),
    pytest.param(["--dangerously-skip-permissions"], id="dangerously-skip"),
    pytest.param(["--permission-mode", "BypassPermissions"], id="case-insensitive-fail-closed"),
])
def test_the_pty_path_extra_args_are_a_request(extra_args):
    """PTY／subprocess 後端是出廠預設，F-SBR-001 實際走的就是這一條——只守 SDK 那條會整條漏掉。"""
    got = B.permission_bypass_requests("default", extra_args)
    assert len(got) == 1 and got[0].startswith("claude.extra_args")


def test_both_paths_are_listed_and_a_repeated_flag_is_reported_once():
    got = B.permission_bypass_requests(
        "bypassPermissions",
        ["--dangerously-skip-permissions", "--dangerously-skip-permissions"])
    assert len(got) == 2


@pytest.mark.parametrize("extra_args", [
    pytest.param(["--permission-mode", "acceptEdits"], id="accept-edits"),
    pytest.param(["--allow-dangerously-skip-permissions"], id="allow-option-only"),
    pytest.param(["--allowedTools", "Bash(echo bypassPermissions)"], id="word-inside-a-value"),
    pytest.param(["--permission-mode"], id="dangling-flag"),
    pytest.param(["--append-system-prompt", "never use --dangerously-skip-permissions"],
                 id="flag-quoted-inside-a-prompt"),
    pytest.param([1, None], id="non-string-items"),
])
def test_look_alikes_are_not_a_request(extra_args):
    """判準是「真的把 bypass 打開的 argv 位置」，不是子字串搜尋：
    `--allow-dangerously-skip-permissions` 只是允許日後切過去的選項、本身不跳過任何檢查。
    把這條邊界釘住，後人把判準放寬成子字串比對時才會有一支測試出聲。"""
    assert B.permission_bypass_requests("default", extra_args) == ()


# ══════════════════════════════════════════════════════════════════════════════
# 旗標讀取：fail-closed
# ══════════════════════════════════════════════════════════════════════════════
def test_the_env_name_is_the_prd_literal_not_an_autoclaude_alias():
    """PRD §6 區塊 13 的字面就是 `ALLOW_PERMISSION_BYPASS`；改名要走修憲，不是改常數。"""
    assert B.ALLOW_BYPASS_ENV == "ALLOW_PERMISSION_BYPASS"


@pytest.mark.parametrize("raw", ["true", "TRUE", " True ", "1", "yes", "on"])
def test_only_explicit_truthy_literals_open_the_flag(raw):
    assert B.permission_bypass_allowed_from_env({B.ALLOW_BYPASS_ENV: raw}) == (True, raw.strip())


@pytest.mark.parametrize("raw", ["", "false", "0", "no", "off", "treu", "enabled", "2"])
def test_everything_else_is_closed_and_the_raw_text_is_kept(raw):
    """打錯字（`treu`）算關——bypass 這種安全閘不猜使用者的意思；原始字面回給呼叫端放進拒絕
    訊息，讓「設了卻沒生效」看得見。"""
    assert B.permission_bypass_allowed_from_env({B.ALLOW_BYPASS_ENV: raw}) == (False, raw.strip())


def test_the_flag_defaults_to_closed_and_reads_the_process_environment(monkeypatch):
    monkeypatch.delenv(B.ALLOW_BYPASS_ENV, raising=False)
    assert B.permission_bypass_allowed_from_env() == (False, "")
    monkeypatch.setenv(B.ALLOW_BYPASS_ENV, "true")
    assert B.permission_bypass_allowed_from_env() == (True, "true")


# ══════════════════════════════════════════════════════════════════════════════
# (c) 判決表：旗標與容器缺一不可
# ══════════════════════════════════════════════════════════════════════════════
_ASK = ("claude.extra_args 的 --permission-mode bypassPermissions",)


def _verdict(requested, flag, iso, raw=None):
    return B.permission_bypass_verdict(
        requested, allow_flag=flag, flag_raw=raw if raw is not None else ("true" if flag else ""),
        isolation=iso)


@pytest.mark.parametrize("iso", [_HOST, _BOX], ids=["host", "container"])
def test_cell_nobody_asks_and_the_flag_is_closed_is_not_our_business(iso):
    out = _verdict((), False, iso)
    assert out.problems == () and out.lines == ()


def test_cell_flag_open_inside_a_container_with_no_bypass_asked_is_harmless():
    out = _verdict((), True, _BOX)
    assert out.problems == () and out.lines == ()


def test_cell_flag_open_on_a_host_is_refused_even_when_nothing_asks_for_bypass():
    """PRD §6.1 不變式 8 的字面：`ALLOW_PERMISSION_BYPASS=true → 必須偵測到容器/VM，否則拒絕啟動`
    ——條文的前件是旗標，不是『設定有沒有要求 bypass』；旗標只准在隔離環境內開。"""
    out = _verdict((), True, _HOST)
    assert len(out.problems) == 1 and out.lines == ()
    msg = out.problems[0]
    assert "不變式 8" in msg and "容器" in msg and B.ALLOW_BYPASS_ENV in msg


@pytest.mark.parametrize("iso", [_HOST, _BOX], ids=["host", "container"])
def test_cell_bypass_asked_without_the_flag_is_refused_even_inside_a_container(iso):
    """PRD §4.5.4：容器「且使用者明確設定」兩個要件——只有容器、沒有旗標，一樣不准。"""
    out = _verdict(_ASK, False, iso)
    assert len(out.problems) == 1 and out.lines == ()
    msg = out.problems[0]
    assert _ASK[0] in msg                                   # 說出是哪個設定要的
    assert "acceptEdits" in msg and "--allowedTools" in msg  # 說出怎麼改
    assert f"{B.ALLOW_BYPASS_ENV}=true" in msg              # 說出另一條出路


def test_cell_mac_host_with_the_flag_still_refuses():
    """T4 症狀本身：旗標開了、但行程在主機（macOS）上——旗標不是通行證，容器證據才是。"""
    out = _verdict(_ASK, True, _HOST)
    assert len(out.problems) == 1 and out.lines == ()
    msg = out.problems[0]
    assert _ASK[0] in msg and "未偵測到容器" in msg and "macOS" in msg and "不變式 8" in msg


def test_cell_flag_plus_container_allows_and_logs_the_isolation_evidence():
    out = _verdict(_ASK, True, B.IsolationEvidence(sources=("dockerenv", "cgroup:docker")))
    assert out.problems == ()
    assert len(out.lines) == 1
    line = out.lines[0]
    assert "bypass 已顯式允許" in line and "隔離證據＝dockerenv、cgroup:docker" in line


def test_a_mistyped_flag_is_echoed_back_in_the_refusal():
    out = _verdict(_ASK, False, _BOX, raw="treu")
    assert "treu" in out.problems[0]


# ══════════════════════════════════════════════════════════════════════════════
# boot_self_check 整合：不變式 8 進得了 BootReport，且惰性
# ══════════════════════════════════════════════════════════════════════════════
def _runner(argv):
    return 0, "2.1.295 (Claude Code)"


def test_boot_report_carries_the_refusal_and_the_other_invariants_still_run():
    report = B.boot_self_check(permission_mode="bypassPermissions", environ={},
                               isolation=_HOST, cli_runner=_runner)
    assert report.ok is False
    assert len(report.problems) == 1 and "拒絕啟動" in report.problems[0]
    assert any("CLI" in ln for ln in report.lines), "其餘不變式被短路了：一次要列出全部問題"


def test_boot_report_passes_and_logs_when_flag_and_container_are_both_present():
    report = B.boot_self_check(extra_args=["--dangerously-skip-permissions"],
                               environ={B.ALLOW_BYPASS_ENV: "true"},
                               isolation=_BOX, cli_runner=_runner)
    assert report.ok is True
    assert any("bypass 已顯式允許" in ln for ln in report.lines)


def test_the_isolation_probe_is_lazy_so_ordinary_runs_never_touch_it(monkeypatch):
    """沒人要 bypass、旗標也沒開時，每次啟動多讀一個 /proc 檔只會換來跨平台的新變因、
    換不到任何判決。探針被呼叫＝這條惰性被破壞。"""
    def _boom(**kwargs):
        raise AssertionError("沒人要求 bypass，卻去探測隔離環境")
    monkeypatch.setattr(B, "detect_isolation_env", _boom)
    report = B.boot_self_check(permission_mode="acceptEdits",
                               extra_args=["--model", "haiku"], environ={}, cli_runner=_runner)
    assert report.ok is True


def test_the_probe_runs_exactly_when_someone_asks_and_gets_the_injected_environ(monkeypatch):
    seen: list[dict] = []

    def _spy(**kwargs):
        seen.append(kwargs)
        return _BOX
    monkeypatch.setattr(B, "detect_isolation_env", _spy)
    env = {B.ALLOW_BYPASS_ENV: "true"}
    report = B.boot_self_check(permission_mode="bypassPermissions", environ=env,
                               cli_runner=_runner)
    assert report.ok is True and len(seen) == 1
    assert seen[0]["environ"] is env, "探測沒吃到注入的 environ ⇒ 測試會讀到真實環境"


def test_callers_that_predate_the_new_arguments_are_unaffected(monkeypatch):
    monkeypatch.delenv(B.ALLOW_BYPASS_ENV, raising=False)
    report = B.boot_self_check(cli_runner=_runner)
    assert report.ok is True


# ══════════════════════════════════════════════════════════════════════════════
# (d) 入口：真 main() 在任何 step 之前拒絕；真實的 F-SBR-001 範本照常放行
# ══════════════════════════════════════════════════════════════════════════════
class _FakeService:
    """替身 AutoResumeService：只記「有沒有被組出來」——被組出來＝已經進了執行階段。"""

    built = False

    def __init__(self, kernel, cfg, **kwargs):
        type(self).built = True

    def run(self, path, fresh=False):
        return KernelResult(success=True, completed_steps=0, total_steps=0, reason="fake")


def _release_autoclaude_log_handles() -> None:
    """`main()` 建的 RotatingFileHandler 握著 tmp 下的 log；不放掉會漏到同 worker 的下一支測試。"""
    log = logging.getLogger("autoclaude")
    for handler in list(log.handlers):
        handler.close()
        log.removeHandler(handler)


def _synthetic_config(tmp_path: Path, claude_extra: str = "[]",
                      executor_yaml: str = "  backend: pty\n") -> str:
    return (f"claude:\n  extra_args: {claude_extra}\n"
            f"executor:\n{executor_yaml}"
            f"log_dir: {tmp_path.as_posix()}/logs\n"
            f"checkpoint_dir: {tmp_path.as_posix()}/ckpt\n")


def _boot(tmp_path, monkeypatch, config_text: str, *, env=None, isolation=None) -> int:
    """在 tmp 裡以真 `main()` 跑啟動流程（執行器與服務是替身；真 claude 一個都不 spawn）。"""
    (tmp_path / "scripts").mkdir()
    shutil.copy(_PLAYBOOK, tmp_path / "scripts" / "example_playbook.yaml")
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(config_text, encoding="utf-8", newline="\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["autoclaude", "scripts/example_playbook.yaml",
                                      "--config", str(cfg_path), "--fresh"])
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv(B.ALLOW_BYPASS_ENV, raising=False)
    for key, value in (env or {}).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(main_mod, "build_executor", lambda *a, **k: object())
    monkeypatch.setattr(main_mod, "AutoResumeService", _FakeService)
    monkeypatch.setattr(main_mod, "read_cli_version", lambda *a, **k: "2.1.295")
    monkeypatch.setattr(main_mod, "estimate_freeze_bytes", lambda *a, **k: 0)
    if isolation is not None:
        monkeypatch.setattr(B, "detect_isolation_env", lambda **kwargs: isolation)
    _FakeService.built = False
    try:
        return main_mod.main()
    finally:
        _release_autoclaude_log_handles()


def test_t4_symptom_the_historical_f_sbr_001_config_is_refused_before_any_step(
        tmp_path, monkeypatch, caplog):
    """PRD §16.2 該列的再開症狀本身：非容器環境＋`--permission-mode bypassPermissions`。
    修前：rc=0 照跑巢狀 claude；修後：開機自檢 rc=1，service 根本不會被組出來。"""
    cfg = _synthetic_config(
        tmp_path, '["--permission-mode", "bypassPermissions", "--model", "haiku"]')
    with caplog.at_level(logging.INFO, logger="autoclaude"):
        rc = _boot(tmp_path, monkeypatch, cfg, isolation=_HOST)
    assert rc == 1
    assert _FakeService.built is False, "已拒絕卻仍進了執行階段"
    assert "開機自檢未過" in caplog.text and "拒絕啟動" in caplog.text
    assert B.ALLOW_BYPASS_ENV in caplog.text and "acceptEdits" in caplog.text


@pytest.mark.parametrize("claude_extra, executor_yaml", [
    pytest.param('["--dangerously-skip-permissions"]', "  backend: pty\n",
                 id="pty-dangerously-skip"),
    pytest.param("[]", "  backend: sdk\n  permission_mode: bypassPermissions\n",
                 id="sdk-permission-mode"),
])
def test_both_config_paths_reach_the_gate(tmp_path, monkeypatch, claude_extra, executor_yaml):
    """守門要接在設定面的**兩條**路上：只餵一條，另一條就是完整的旁路。"""
    cfg = _synthetic_config(tmp_path, claude_extra, executor_yaml)
    rc = _boot(tmp_path, monkeypatch, cfg, isolation=_HOST)
    assert rc == 1 and _FakeService.built is False


def test_flag_plus_container_boots_and_leaves_the_isolation_evidence_in_the_log(
        tmp_path, monkeypatch, caplog):
    cfg = _synthetic_config(tmp_path, '["--permission-mode", "bypassPermissions"]')
    with caplog.at_level(logging.INFO, logger="autoclaude"):
        rc = _boot(tmp_path, monkeypatch, cfg, env={B.ALLOW_BYPASS_ENV: "true"}, isolation=_BOX)
    assert rc == 0 and _FakeService.built is True
    assert "bypass 已顯式允許" in caplog.text and "隔離證據＝dockerenv" in caplog.text


def test_flag_alone_on_a_host_stops_the_start_even_with_an_ordinary_config(
        tmp_path, monkeypatch):
    rc = _boot(tmp_path, monkeypatch, _synthetic_config(tmp_path),
               env={B.ALLOW_BYPASS_ENV: "true"}, isolation=_HOST)
    assert rc == 1 and _FakeService.built is False


def test_the_real_f_sbr_001_template_boots_on_a_plain_host_without_probing(
        tmp_path, monkeypatch):
    """正向對照：入庫範本走 PRD 正道，在非容器主機上照常放行——否則上面全部拒絕案例分不出
    「有牙齒」與「咬所有人」。探針被呼叫＝範本又長出了要 bypass 的設定。"""
    def _boom(**kwargs):
        raise AssertionError("範本不該要求 bypass，卻去探測了隔離環境")
    monkeypatch.setattr(B, "detect_isolation_env", _boom)
    text = _TEMPLATE.read_text(encoding="utf-8").replace("__RUN_DIR__", tmp_path.as_posix())
    assert _boot(tmp_path, monkeypatch, text) == 0
    assert _FakeService.built is True


# ══════════════════════════════════════════════════════════════════════════════
# F-SBR-001 fixture：走 PRD 正道，且白名單不得退化成全開
# ══════════════════════════════════════════════════════════════════════════════
def _template_config(tmp_path: Path):
    text = _TEMPLATE.read_text(encoding="utf-8").replace("__RUN_DIR__", tmp_path.as_posix())
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(text, encoding="utf-8", newline="\n")
    return text, load_config(str(cfg_path))   # 檔不存在時 load_config 靜默回預設，下面逐值斷言


def test_the_template_asks_for_accept_edits_plus_a_whitelist_never_bypass(tmp_path):
    text, cfg = _template_config(tmp_path)
    args = cfg.claude.extra_args
    assert args[args.index("--permission-mode") + 1] == "acceptEdits"
    assert "--allowedTools" in args
    assert B.permission_bypass_requests(cfg.executor.permission_mode, args) == ()
    assert "bypassPermissions" not in json.dumps(yaml.safe_load(text))


def test_the_template_whitelist_does_not_degrade_into_allow_everything(tmp_path):
    """白名單的意義是『白名單外全拒』：裸 `Bash` 或 `Bash(*)` 會把它變回全開，等於換個寫法的
    bypass，而且不會被不變式 8 看見（它只認 bypass 字面）——所以由這支測試守。"""
    _, cfg = _template_config(tmp_path)
    args = cfg.claude.extra_args
    tools = args[args.index("--allowedTools") + 1].split(",")
    shell_rules = [t for t in tools if t == "Bash" or t.startswith("Bash(")]
    assert shell_rules, "巢狀 claude 要跑 pytest 驗收閘：白名單至少要有一條 Bash 規則"
    assert all(re.fullmatch(r"Bash\(pytest[: ][^)]*\)", t) for t in shell_rules), shell_rules
    assert set(tools) - set(shell_rules) <= {"Read", "Edit", "Write", "Glob", "Grep"}


# ══════════════════════════════════════════════════════════════════════════════
# scripts/ab_configs：舊 A/B／demo config 一併走 PRD 正道
# ══════════════════════════════════════════════════════════════════════════════
_AB_CONFIGS = sorted((_AUTOCLAUDE / "scripts" / "ab_configs").glob("*.yaml"))


def test_the_ab_config_scan_is_not_silently_empty():
    """下面的參數化在 import 期展開：目錄搬走或改名時，整組測試會『不存在』而不是『失敗』，
    所以先把分母釘住。"""
    assert len(_AB_CONFIGS) >= 6


@pytest.mark.parametrize("path", _AB_CONFIGS, ids=lambda p: p.name)
def test_every_shipped_ab_config_goes_the_prd_road(path):
    """這些 config 的消費者（ab_compare_backends／correction_loop_verify／…）都以子行程跑
    `python -m autoclaude`，走同一個開機自檢；舊版全是 bypassPermissions，在非容器主機上會被
    不變式 8 拒絕。改回 bypass、或把 pty 側白名單放寬成裸 `Bash`（＝換個寫法的全開），這裡轉紅。
    SDK 側的白名單只到工具名粒度（引擎限制），所以只要求它明示、不要求指令級。"""
    cfg = load_config(str(path))
    assert B.permission_bypass_requests(cfg.executor.permission_mode, cfg.claude.extra_args) == ()
    if cfg.executor.backend == "sdk":
        assert cfg.executor.permission_mode == "acceptEdits"
        assert cfg.executor.sdk_tool_allowlist, "SDK 側須明示白名單，不交給預設 None"
        return
    args = cfg.claude.extra_args
    assert args[args.index("--permission-mode") + 1] == "acceptEdits"
    tools = args[args.index("--allowedTools") + 1].split(",")
    assert all(t in {"Read", "Edit", "Write", "Glob", "Grep"}
               or re.fullmatch(r"Bash\(pytest[: ][^)]*\)", t) for t in tools), tools


def test_the_env_example_documents_the_flag_but_never_ships_it_open():
    """`.env.example` 是使用者 `cp` 後的起點：它必須寫明這個鍵的意義與預設（關），
    且不得有任何一行把它設成真值——範本裡的 true 會被原樣複製進容器之外的環境。"""
    text = (_AUTOCLAUDE / ".env.example").read_text(encoding="utf-8")
    assert B.ALLOW_BYPASS_ENV in text
    active = re.findall(rf"^{B.ALLOW_BYPASS_ENV}=(\S*)", text, re.MULTILINE)
    assert all(v.lower() not in {"1", "true", "yes", "on"} for v in active), active
