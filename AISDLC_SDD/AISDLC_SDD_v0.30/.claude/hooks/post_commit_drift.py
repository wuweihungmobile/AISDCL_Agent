"""post_commit_drift.py — Phase G M4 / ACT-039 Git PostCommit Drift Hook

Triggered by git native post-commit hook. Advisory only — never blocks commit
(Rule 9.17.1). Budget: < 2s; on timeout, write warning and skip.

Install: tools/install_post_commit_hook.sh / .ps1 (opt-in, not enforced via
.claude/settings.json — per OPEN-G.4 decoupled from Claude Code session).
"""
from __future__ import annotations

import concurrent.futures
import signal
import subprocess
import sys
from pathlib import Path

# DEF-43-008（improving_44）：parents[2]＝版本目錄，僅作 sys.path import 根（tools.fsm_runtime
# 是以版本目錄為根的 namespace package）。但 monorepo 收斂（2026-06-13 移除巢狀 .git）後，
# 版本目錄已無 .git → 若拿它當 repo 根，_write_warning 的 git_dir.exists() 恆 False、drift 告警
# 靜默蒸發，且 compute_drift 掃錯目錄。對稱於 closure_evidence.repo_root_from()，分離兩者：
# _PKG_ROOT 供 import；REPO_ROOT 改以 git-common-dir 定位真實 monorepo 根（fallback _PKG_ROOT）。
_PKG_ROOT = Path(__file__).resolve().parents[2]
BUDGET_SEC = 2

sys.path.insert(0, str(_PKG_ROOT))

from tools.fsm_runtime.drift_monitor import (  # noqa: E402
    check_consecutive_drift,
    compute_drift,
    write_commit_report,
)


def _repo_root() -> Path:
    """以 `--git-common-dir` 的父目錄定位 monorepo 根（hook 在版本目錄但 commit 在根）；
    fallback `_PKG_ROOT`。

    DEF-101-059：舊版用 `git rev-parse --show-toplevel` 定位 monorepo 根，
    在一般 checkout 下沒問題，但在 git worktree 情境下真的用 `git commit` 觸發
    本 hook 時，git 會替 post-commit 子行程注入 `GIT_DIR`（指向
    `<主repo>/.git/worktrees/<name>`）。實測證實：只要繼承到 `GIT_DIR`，
    `--show-toplevel` 無論 `cwd` 為何一律退化成直接回顯 `cwd` 本身（不再向上
    尋根），導致 REPO_ROOT 誤算成版本目錄（`.../AISDLC_SDD_v0.30`）——這個路徑
    本無 `.git`，`_write_warning` 的 `git_dir.exists()` 恆 False，drift 告警
    靜默蒸發（Rule 9.17.1 在 worktree 下真實失效，且完全不報錯，使用者無感）。
    `--git-common-dir` 不受此汙染：不論有無 `GIT_DIR`、不論 `cwd` 落在主 repo
    或 worktree，皆正確解回真正共用的 `.git`（與 install_post_commit.sh/.ps1
    同手法）。取其父目錄即為主 repo 根——一旦 REPO_ROOT 正確落在主 repo（其
    `.git` 恆為真實目錄，不是 worktree 那種指標檔），下游 `_write_warning` 沿用
    `REPO_ROOT / ".git"` 天真拼接就重新變安全，SD 發現的 naive join 問題隨之
    消除（根因是 REPO_ROOT 算錯，不是拼接手法本身）。
    """
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=_PKG_ROOT,
            stderr=subprocess.DEVNULL,
            # 🔴 R88／DEF-200-104：`creationflags` 非有不可——hook 載具在 Windows 是
            # `pythonw.exe`（GUI 子系統、無 console），OS 會替這個 child **另配一個新
            # console 視窗** ⇒ 每次觸發就閃一次。平台中立：POSIX 上 `getattr` 兜底成 0。
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        s = out.decode().strip()
        if s:
            return Path(s).parent
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    return _PKG_ROOT


REPO_ROOT = _repo_root()


def _current_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
            # 🔴 R88／DEF-200-104：`creationflags` 非有不可——hook 載具在 Windows 是
            # `pythonw.exe`（GUI 子系統、無 console），OS 會替這個 child **另配一個新
            # console 視窗** ⇒ 每次觸發就閃一次。平台中立：POSIX 上 `getattr` 兜底成 0。
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return out.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _write_warning(msg: str) -> None:
    git_dir = REPO_ROOT / ".git"
    if git_dir.exists():
        (git_dir / "COMMIT_DRIFT_WARNING").write_text(msg + "\n", encoding="utf-8")


class _Timeout(Exception):
    pass


def _timeout_handler(signum, frame):  # pragma: no cover - signal callback
    raise _Timeout()


def _compute_drift_for_head(sha: str):
    return compute_drift(
        sha,
        openapi_path=REPO_ROOT / "docs" / "02_architecture" / "api" / "openapi.yaml",
        frd_dir=REPO_ROOT / "docs" / "01_requirements",
        code_dir=REPO_ROOT / "src",
    )


def main() -> int:
    sha = _current_sha()
    # SIGALRM only on POSIX; Windows has no SIGALRM, so the budget there is
    # enforced via a ThreadPoolExecutor + future.result(timeout=...) guard
    # (DEF-CLDREV-001). Both paths converge on the same fail-soft contract:
    # advisory only, never block the commit (Rule 9.17.1).
    has_alarm = hasattr(signal, "SIGALRM")
    if has_alarm:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(BUDGET_SEC)
        try:
            report = _compute_drift_for_head(sha)
        except _Timeout:
            _write_warning(
                f"drift hook timeout > {BUDGET_SEC}s for commit {sha[:12]} — skipped (Rule 9.17.1)"
            )
            return 0
        except Exception as exc:
            _write_warning(f"drift hook error for commit {sha[:12]}: {exc} — advisory")
            return 0
        finally:
            signal.alarm(0)
    else:
        # Windows thread-guard path: run compute_drift in a worker thread and
        # bound the wait to BUDGET_SEC. On timeout we cannot truly kill the
        # thread, but the hook returns immediately (advisory, never-block); we
        # deliberately avoid the `with` block's implicit shutdown(wait=True) so
        # a slow compute can never make the hook overrun its budget.
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(_compute_drift_for_head, sha)
        try:
            report = future.result(timeout=BUDGET_SEC)
        except concurrent.futures.TimeoutError:
            _write_warning(
                f"drift hook timeout > {BUDGET_SEC}s for commit {sha[:12]} — skipped (Rule 9.17.1)"
            )
            pool.shutdown(wait=False, cancel_futures=True)
            return 0
        except Exception as exc:
            _write_warning(f"drift hook error for commit {sha[:12]}: {exc} — advisory")
            pool.shutdown(wait=False, cancel_futures=True)
            return 0
        pool.shutdown(wait=False)

    write_commit_report(report, repo_root=REPO_ROOT)
    if report.total_score >= 0.3:
        _write_warning(
            f"drift_score {report.total_score:.3f} ≥ 0.3 for commit {sha[:12]} — advisory; "
            "next PR_REVIEW will require extra audit (Rule 9.17.2)"
        )
        # advisory check — does NOT block commit, just stamps a marker
        escalate, shas = check_consecutive_drift(repo_root=REPO_ROOT)
        if escalate:
            _write_warning(
                f"consecutive drift detected over {len(shas)} commits — SPEC_AUDIT required "
                "(Rule 9.17.3)"
            )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
