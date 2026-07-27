"""tests/tools/test_run_act_core.py — 本機 act 重現核心（run_act_core.py）單元測試。

背景（R32 四方審查閉環 Scan-B 缺陷回流）：run_act_core.py 是「Python 核心 + 雙殼薄封裝」
收斂案之一（仿 R12 DEF-101-070 ② local_ci_gate 模式），但收斂後全 repo 從未有任何
自動化測試直接驗證其核心邏輯（尤其 resolve_act() 的 Windows winget 路徑 glob 偵測
分支）——薄殼 .sh/.ps1 僅由 monorepo 根 check_wrapper_thinness.py／check_script_parity.py
做文字 hash 釘選，完全不觸及本檔邏輯本體。本檔補齊該缺口（全程 mock 子行程/檔案系統，
不依賴本機真的裝有 act/Docker/winget/gh）。

涵蓋 case：
    (a) resolve_act()：PATH 命中 → Windows winget glob 命中/排序/未命中 →
        gh-act 退回 → 全數落空回傳 None
    (b) _gh_act_extension_installed()：正向子字串命中 / 負向 / gh 未安裝 OSError 容錯
    (c) ensure_images()：--job 時只查 runner image；無 --job 另查 PG image；
        缺鏡像時觸發 pull；pull 失敗回傳 1
    (d) check_docker() / image_ready()：_run_quiet 對 rc 與 OSError 容錯的轉譯
    (e) run_act()：組裝 act 參數（含/不含 --job、--dry-run）
    (f) main() 六步驟關鍵分支：act 未尋獲 rc=127、Docker 未啟動 rc=1、
        --list 模式分派、鏡像 pull 失敗 rc=1、成功/失敗結案訊息與 rc 透傳
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

import run_act_core as m  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_cwd():
    """main() 會 os.chdir(MONOREPO_ROOT) 且不還原（載具行程生命週期短，設計如此）；
    測試層快照還原，防自 monorepo 根聚合收集時的 cwd 汙染（對齊 test_local_ci_gate.py
    同款隔離 fixture）。"""
    prev_cwd = os.getcwd()
    yield
    os.chdir(prev_cwd)


# --- (a) resolve_act() ---

def test_resolve_act_uses_path_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        m.shutil, "which", lambda name: "/usr/local/bin/act" if name == "act" else None,
    )
    assert m.resolve_act() == ["/usr/local/bin/act"]


def test_resolve_act_path_hit_skips_windows_and_gh_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """PATH 命中時提早 return，不應觸碰 Windows 分支或 gh-act 探測（no-call 斷言）。"""
    monkeypatch.setattr(
        m.shutil, "which", lambda name: "/usr/local/bin/act" if name == "act" else None,
    )
    monkeypatch.setattr(
        m.platform_utils, "is_windows",
        lambda: (_ for _ in ()).throw(AssertionError("不應呼叫 is_windows")),
    )
    monkeypatch.setattr(
        m, "_gh_act_extension_installed",
        lambda: (_ for _ in ()).throw(AssertionError("不應呼叫 _gh_act_extension_installed")),
    )
    assert m.resolve_act() == ["/usr/local/bin/act"]


def test_resolve_act_windows_falls_back_to_winget_glob(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(m.shutil, "which", lambda name: None)
    monkeypatch.setattr(m.platform_utils, "is_windows", lambda: True)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    act_dir = tmp_path / "Microsoft" / "WinGet" / "Packages" / "nektos.act_1.2.3"
    act_dir.mkdir(parents=True)
    act_exe = act_dir / "act.exe"
    act_exe.write_text("", encoding="utf-8")

    assert m.resolve_act() == [str(act_exe)]


def test_resolve_act_windows_winget_glob_picks_sorted_first_match(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(m.shutil, "which", lambda name: None)
    monkeypatch.setattr(m.platform_utils, "is_windows", lambda: True)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    base = tmp_path / "Microsoft" / "WinGet" / "Packages"
    older = base / "nektos.act_1.0.0"
    newer = base / "nektos.act_2.0.0"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    (older / "act.exe").write_text("", encoding="utf-8")
    (newer / "act.exe").write_text("", encoding="utf-8")

    result = m.resolve_act()
    assert result == [str(older / "act.exe")]  # sorted() 排序後取首個（字典序 1.0.0 < 2.0.0）


def test_resolve_act_windows_no_localappdata_env_falls_through_to_gh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(m.shutil, "which", lambda name: None)
    monkeypatch.setattr(m.platform_utils, "is_windows", lambda: True)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(m, "_gh_act_extension_installed", lambda: True)
    assert m.resolve_act() == ["gh", "act"]


def test_resolve_act_windows_glob_no_match_falls_through_to_gh(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(m.shutil, "which", lambda name: None)
    monkeypatch.setattr(m.platform_utils, "is_windows", lambda: True)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))  # 目錄存在但無 nektos.act_* 子目錄
    monkeypatch.setattr(m, "_gh_act_extension_installed", lambda: True)
    assert m.resolve_act() == ["gh", "act"]


def test_resolve_act_non_windows_skips_winget_check_entirely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(m.shutil, "which", lambda name: None)
    monkeypatch.setattr(m.platform_utils, "is_windows", lambda: False)
    monkeypatch.setattr(m, "_gh_act_extension_installed", lambda: True)
    assert m.resolve_act() == ["gh", "act"]


def test_resolve_act_returns_none_when_nothing_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(m.shutil, "which", lambda name: None)
    monkeypatch.setattr(m.platform_utils, "is_windows", lambda: False)
    monkeypatch.setattr(m, "_gh_act_extension_installed", lambda: False)
    assert m.resolve_act() is None


# --- (b) _gh_act_extension_installed() ---

def test_gh_act_extension_installed_true_when_substring_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        m.subprocess, "run",
        lambda *a, **k: SimpleNamespace(stdout="nektos/gh-act\t1.0.0\thttps://...\n"),
    )
    assert m._gh_act_extension_installed() is True


def test_gh_act_extension_installed_false_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        m.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="some/other-ext\t1.0.0\n"),
    )
    assert m._gh_act_extension_installed() is False


def test_gh_act_extension_installed_false_on_oserror_when_gh_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_a, **_k):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(m.subprocess, "run", boom)
    assert m._gh_act_extension_installed() is False


# --- (c) ensure_images() ---

def test_ensure_images_job_specified_only_checks_runner_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked: list[str] = []
    monkeypatch.setattr(m, "image_ready", lambda img: checked.append(img) or True)
    assert m.ensure_images("test") == 0
    assert checked == [m.RUNNER_IMAGE]


def test_ensure_images_no_job_also_checks_pg_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked: list[str] = []
    monkeypatch.setattr(m, "image_ready", lambda img: checked.append(img) or True)
    assert m.ensure_images("") == 0
    assert checked == [m.RUNNER_IMAGE, m.PG_IMAGE]


def test_ensure_images_pulls_missing_image(monkeypatch: pytest.MonkeyPatch) -> None:
    pulled: list[str] = []
    monkeypatch.setattr(m, "image_ready", lambda img: False)
    monkeypatch.setattr(m, "pull_image", lambda img: pulled.append(img) or 0)
    assert m.ensure_images("test") == 0
    assert pulled == [m.RUNNER_IMAGE]


def test_ensure_images_pull_failure_returns_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(m, "image_ready", lambda img: False)
    monkeypatch.setattr(m, "pull_image", lambda img: 1)
    assert m.ensure_images("test") == 1


# --- (d) check_docker() / image_ready()（經 _run_quiet 轉譯） ---

def test_check_docker_true_when_rc_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0))
    assert m.check_docker() is True


def test_check_docker_false_when_rc_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1))
    assert m.check_docker() is False


def test_check_docker_false_on_oserror_when_docker_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_a, **_k):
        raise FileNotFoundError("docker")

    monkeypatch.setattr(m.subprocess, "run", boom)
    assert m.check_docker() is False


def test_image_ready_true_when_rc_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0))
    assert m.image_ready("catthehacker/ubuntu:act-latest") is True


def test_image_ready_false_when_rc_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1))
    assert m.image_ready("catthehacker/ubuntu:act-latest") is False


# --- (e) run_act() ---

def test_run_act_builds_expected_args_with_job_and_dry_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        m.subprocess, "run", lambda cmd: calls.append(list(cmd)) or SimpleNamespace(returncode=0)
    )
    rc = m.run_act(["act"], "test", True, "/tmp/empty.env")
    assert rc == 0
    assert calls == [
        ["act", "push", "-W", m.WORKFLOW, "--pull=false", "--env-file", "/tmp/empty.env",
         "-j", "test", "-n"]
    ]


def test_run_act_without_job_or_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        m.subprocess, "run", lambda cmd: calls.append(list(cmd)) or SimpleNamespace(returncode=3)
    )
    rc = m.run_act(["gh", "act"], "", False, "/tmp/e.env")
    assert rc == 3
    assert calls == [
        ["gh", "act", "push", "-W", m.WORKFLOW, "--pull=false", "--env-file", "/tmp/e.env"]
    ]


# --- (f) main() 六步驟關鍵分支 ---

def test_main_returns_127_when_act_not_found(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(m, "resolve_act", lambda: None)
    rc = m.main([])
    assert rc == 127
    assert "act 未安裝" in capsys.readouterr().err


def test_main_returns_1_when_docker_not_running(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(m, "resolve_act", lambda: ["act"])
    monkeypatch.setattr(m, "check_docker", lambda: False)
    rc = m.main([])
    assert rc == 1
    assert "Docker daemon 未啟動" in capsys.readouterr().err


def test_main_list_mode_dispatches_to_act_l(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(m, "resolve_act", lambda: ["act"])
    monkeypatch.setattr(m, "check_docker", lambda: True)
    calls: list[list[str]] = []
    monkeypatch.setattr(
        m.subprocess, "run", lambda cmd: calls.append(list(cmd)) or SimpleNamespace(returncode=0)
    )
    rc = m.main(["--list"])
    assert rc == 0
    assert calls == [["act", "-l", "-W", m.WORKFLOW]]


def test_main_ensure_images_failure_returns_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(m, "resolve_act", lambda: ["act"])
    monkeypatch.setattr(m, "check_docker", lambda: True)
    monkeypatch.setattr(m, "ensure_images", lambda job: 1)
    assert m.main([]) == 1


def test_main_success_prints_check_and_returns_0(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(m, "resolve_act", lambda: ["act"])
    monkeypatch.setattr(m, "check_docker", lambda: True)
    monkeypatch.setattr(m, "ensure_images", lambda job: 0)
    monkeypatch.setattr(m, "run_act", lambda *a, **k: 0)
    rc = m.main(["--job", "test"])
    assert rc == 0
    assert "本地 CI 通過" in capsys.readouterr().out


def test_main_failure_prints_cross_and_returns_rc(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(m, "resolve_act", lambda: ["act"])
    monkeypatch.setattr(m, "check_docker", lambda: True)
    monkeypatch.setattr(m, "ensure_images", lambda job: 0)
    monkeypatch.setattr(m, "run_act", lambda *a, **k: 3)
    rc = m.main([])
    assert rc == 3
    assert "本地 CI 失敗" in capsys.readouterr().out
