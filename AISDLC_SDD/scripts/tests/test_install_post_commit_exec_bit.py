"""install_post_commit.ps1 於 pwsh-on-POSIX 載體下的 exec bit 回歸鎖（R14 QA-R14-REV-3）。

WHY（測意圖非僅行為，Rule 9）：
DEF-101-189 = `.ps1` 安裝器以 `WriteAllText` 寫出 hook 後不設 exec bit——pwsh on
macOS/Linux 載體（R11 BYTE_IDENTICAL 取證即實際走過）下 git 直呼僅印 hint 後忽略、
根層 dispatcher 的 `[ -x ]` 判 false 後零告警跳過＝advisory hook 靜默失效。R14 修復
補 `chmod +x`（Unix 分支）。修復當輪僅有人工實測，本測試把該載體行為自動化：
`.ps1` 若回退（chmod 行被刪）即紅。Windows 上 Unix 分支不可達、無 pwsh 環境無載體，
兩者皆 skip（非 xfail——缺載體屬環境事實，不偽裝成已驗）。
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
# AISDLC_SDD 的父目錄 = monorepo 根（R38 改 dot-source 後，安裝器需要
# monorepo 根層 tools/lib/WindowsAppsGuard.ps1 存在，fake repo 需一併備妥）。
MONOREPO_ROOT = REPO_ROOT.parent
_PWSH = shutil.which("pwsh")

pytestmark = [
    pytest.mark.skipif(os.name == "nt", reason="Unix chmod 分支在 Windows 不可達"),
    pytest.mark.skipif(_PWSH is None, reason="無 pwsh 載體可實跑 .ps1 安裝器"),
]


def _latest_installer() -> Path:
    proc = subprocess.run(
        ["python3", str(REPO_ROOT / "scripts" / "sdd_version.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    assert proc.returncode == 0 and proc.stdout.strip(), (
        f"LATEST 解析失敗：rc={proc.returncode} stderr={proc.stderr!r}"
    )
    return (
        REPO_ROOT / proc.stdout.strip() / "tools" / "install_hooks"
        / "install_post_commit.ps1"
    )


def test_ps1_installer_sets_exec_bit_on_posix() -> None:
    installer = _latest_installer()
    assert installer.is_file(), f"安裝器缺席：{installer}"
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        # 安裝器以 cwd 的 git 根反推 monorepo 結構解析 LATEST（sdd_version.py SSOT
        # ＝git tracked），故 fake repo 需最小 monorepo 骨架＋commit 使其 tracked。
        (repo / "AISDLC_SDD" / "scripts").mkdir(parents=True)
        shutil.copy2(
            REPO_ROOT / "scripts" / "sdd_version.py",
            repo / "AISDLC_SDD" / "scripts" / "sdd_version.py",
        )
        # R38 改 dot-source 共用函式 Test-IsRealPython 後，安裝器前置檢查要求
        # monorepo 根層 tools/lib/WindowsAppsGuard.ps1 存在，fake repo 需一併備妥。
        (repo / "tools" / "lib").mkdir(parents=True)
        shutil.copy2(
            MONOREPO_ROOT / "tools" / "lib" / "WindowsAppsGuard.ps1",
            repo / "tools" / "lib" / "WindowsAppsGuard.ps1",
        )
        hooks_src = repo / "AISDLC_SDD" / "AISDLC_SDD_v0.01" / ".claude" / "hooks"
        hooks_src.mkdir(parents=True)
        for stub in ("post_commit_drift.py", "closure_evidence_verify.py"):
            (hooks_src / stub).write_text("# stub\n", encoding="utf-8")
        subprocess.run(
            ["git", "init", "-q", str(repo)],
            check=True, capture_output=True, timeout=30,
        )
        git_env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        }
        subprocess.run(["git", "-C", str(repo), "add", "-A"],
                       check=True, capture_output=True, timeout=30)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"],
                       check=True, capture_output=True, timeout=30, env=git_env)
        proc = subprocess.run(
            [_PWSH, "-NoProfile", "-File", str(installer)],
            cwd=str(repo),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120,
        )
        assert proc.returncode == 0, (
            f"安裝器非零退出 rc={proc.returncode}\n"
            f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
        )
        hook = repo / ".git" / "hooks" / "post-commit"
        assert hook.is_file(), f"hook 未產出：{hook}\nstdout={proc.stdout!r}"
        assert os.access(hook, os.X_OK), (
            "hook 無 exec bit——DEF-101-189 回歸（git 會靜默忽略、dispatcher [ -x ] "
            "零告警跳過）；檢查 .ps1 的 Unix chmod 分支是否被移除"
        )
