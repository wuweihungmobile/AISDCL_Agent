"""install_post_commit.sh 的 WindowsApps 空殼 python 排除 guard 回歸鎖
（R43 Architect 一審複查追加，DEF-101-353）。

背景：R38 已把 `.ps1` 側（`install_post_commit.ps1`）收斂為 dot-source
`tools/lib/WindowsAppsGuard.ps1`（見 `test_install_post_commit_windowsapps_guard.py`），
但姊妹 `.sh` 版（無 macOS-only 限制，可由 Git Bash on Windows 呼叫；且其產出的
`.git/hooks/post-commit` 會在裝機當下的平台上實際執行）當時未一併收斂，兩處裸
`command -v python`/`command -v python3` 判斷（安裝器本體＋heredoc 產出的 hook
內容）皆未排除 Windows Store WindowsApps 空殼——R43 Scan-B 掃描漏收此檔，
Architect 一審 bug-injection 複查揪出後補齊。本檔鎖住：
  1. 安裝器與其產出的 hook 皆改用共用函式 `is_real_python_candidate`。
  2. 端到端功能驗證：WindowsApps 空殼排在 PATH 最前面時，安裝出來的 hook
     真的會跳過它、改用後面的真直譯器（而非誤判可用或誤判完全找不到）。

執行：python -m pytest AISDLC_SDD/scripts/tests/test_install_post_commit_sh_windowsapps_guard.py -v
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

# scripts/tests/ → scripts/ → AISDLC_SDD（REPO_ROOT）
REPO_ROOT = Path(__file__).resolve().parents[2]
MONOREPO_ROOT = REPO_ROOT.parent
_GUARD_SH = MONOREPO_ROOT / "tools" / "lib" / "windowsapps_guard.sh"
_BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(_BASH is None, reason="本機找不到 bash，略過")


def _latest_installer() -> Path:
    proc = subprocess.run(
        ["python", str(REPO_ROOT / "scripts" / "sdd_version.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    assert proc.returncode == 0 and proc.stdout.strip(), (
        f"LATEST 解析失敗：rc={proc.returncode} stderr={proc.stderr!r}"
    )
    return (
        REPO_ROOT / proc.stdout.strip() / "tools" / "install_hooks"
        / "install_post_commit.sh"
    )


def _build_fake_repo(repo: Path) -> None:
    (repo / "tools" / "lib").mkdir(parents=True)
    shutil.copy2(_GUARD_SH, repo / "tools" / "lib" / "windowsapps_guard.sh")

    (repo / "AISDLC_SDD" / "scripts").mkdir(parents=True)
    shutil.copy2(
        REPO_ROOT / "scripts" / "sdd_version.py",
        repo / "AISDLC_SDD" / "scripts" / "sdd_version.py",
    )

    installer = _latest_installer()
    assert installer.is_file(), f"安裝器缺席：{installer}"
    latest_name = installer.parents[2].name  # .../<LATEST>/tools/install_hooks/xxx.sh
    hooks_src = repo / "AISDLC_SDD" / latest_name / ".claude" / "hooks"
    hooks_src.mkdir(parents=True)
    for stub in ("post_commit_drift.py", "closure_evidence_verify.py"):
        (hooks_src / stub).write_text("# stub\n", encoding="utf-8")

    installer_dst = repo / "AISDLC_SDD" / latest_name / "tools" / "install_hooks"
    installer_dst.mkdir(parents=True)
    shutil.copy2(installer, installer_dst / "install_post_commit.sh")

    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True, timeout=30)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t.com"],
                   check=True, capture_output=True, timeout=30)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"],
                   check=True, capture_output=True, timeout=30)
    subprocess.run(["git", "-C", str(repo), "config", "commit.gpgsign", "false"],
                   check=True, capture_output=True, timeout=30)
    subprocess.run(["git", "-C", str(repo), "add", "-A"],
                   check=True, capture_output=True, timeout=30)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"],
                   check=True, capture_output=True, timeout=30)


def test_installer_and_generated_hook_use_shared_guard() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        _build_fake_repo(repo)
        installer_path = repo / "AISDLC_SDD"
        installer_path = next(installer_path.glob("*/tools/install_hooks/install_post_commit.sh"))
        proc = subprocess.run(
            [_BASH, str(installer_path)],
            cwd=str(repo),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        assert proc.returncode == 0, f"安裝器非零退出：{proc.stdout!r} {proc.stderr!r}"
        hook = repo / ".git" / "hooks" / "post-commit"
        assert hook.is_file(), f"hook 未產出：{proc.stdout!r}"
        text = hook.read_text(encoding="utf-8")
        assert "windowsapps_guard.sh" in text, "產出的 hook 未 source 共用 guard"
        assert "is_real_python_candidate" in text, "產出的 hook 未改用共用函式判斷"
        # 裸 `command -v python` fallback 分支是刻意保留（guard 檔缺席時降級，不
        # 阻擋安裝），故不斷言其完全消失，改由下一測試做端到端行為驗證。


def test_windowsapps_stub_first_falls_through_to_real_python3() -> None:
    """端到端功能驗證：WindowsApps 空殼排 PATH 最前面時，安裝出的 hook 正確跳過它、
    改執行後面真正的 python3（而非誤判可用執行空殼、也非誤判完全找不到）。"""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        repo = tmp / "repo"
        _build_fake_repo(repo)
        installer_path = next(repo.glob("AISDLC_SDD/*/tools/install_hooks/install_post_commit.sh"))
        proc = subprocess.run(
            [_BASH, str(installer_path)],
            cwd=str(repo),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        assert proc.returncode == 0, f"安裝器非零退出：{proc.stdout!r} {proc.stderr!r}"
        hook = repo / ".git" / "hooks" / "post-commit"

        stub_dir = tmp / "WindowsApps"
        stub_dir.mkdir()
        stub = stub_dir / "python"
        stub.write_text("#!/usr/bin/env bash\necho STUB_SHOULD_NOT_RUN\n", encoding="utf-8")
        stub.chmod(0o755)

        real_dir = tmp / "real"
        real_dir.mkdir()
        real = real_dir / "python3"
        real.write_text(
            "#!/usr/bin/env bash\necho REAL_PYTHON3_RAN\n", encoding="utf-8",
        )
        real.chmod(0o755)

        env = dict(os.environ)
        env["PATH"] = f"{stub_dir}{os.pathsep}{real_dir}{os.pathsep}{env.get('PATH', '')}"
        result = subprocess.run(
            [_BASH, str(hook)],
            cwd=str(repo),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30, env=env,
        )
        combined = result.stdout + result.stderr
        assert "STUB_SHOULD_NOT_RUN" not in combined, (
            f"WindowsApps 空殼未被排除、被誤執行：{combined!r}"
        )
        assert "REAL_PYTHON3_RAN" in combined, (
            f"guard 未正確 fall through 到後面的真 python3：{combined!r}"
        )
