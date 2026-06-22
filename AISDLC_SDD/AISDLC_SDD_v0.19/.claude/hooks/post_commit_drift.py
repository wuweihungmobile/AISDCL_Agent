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
# _PKG_ROOT 供 import；REPO_ROOT 改以 git toplevel 定位真實 monorepo 根（fallback _PKG_ROOT）。
_PKG_ROOT = Path(__file__).resolve().parents[2]
BUDGET_SEC = 2

sys.path.insert(0, str(_PKG_ROOT))

from tools.fsm_runtime.drift_monitor import (  # noqa: E402
    check_consecutive_drift,
    compute_drift,
    write_commit_report,
)


def _repo_root() -> Path:
    """以 git toplevel 定位 monorepo 根（hook 在版本目錄但 commit 在根）；fallback _PKG_ROOT。"""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=_PKG_ROOT, stderr=subprocess.DEVNULL
        )
        top = out.decode().strip()
        if top:
            return Path(top)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return _PKG_ROOT


REPO_ROOT = _repo_root()


def _current_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, stderr=subprocess.DEVNULL
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
