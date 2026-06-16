"""post_commit_drift.py — Phase G M4 / ACT-039 Git PostCommit Drift Hook

Triggered by git native post-commit hook. Advisory only — never blocks commit
(Rule 9.17.1). Budget: < 2s; on timeout, write warning and skip.

Install: tools/install_post_commit_hook.sh / .ps1 (opt-in, not enforced via
.claude/settings.json — per OPEN-G.4 decoupled from Claude Code session).
"""
from __future__ import annotations

import signal
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUDGET_SEC = 2

sys.path.insert(0, str(REPO_ROOT))

from tools.fsm_runtime.drift_monitor import (  # noqa: E402
    check_consecutive_drift,
    compute_drift,
    write_commit_report,
)


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


def main() -> int:
    sha = _current_sha()
    # SIGALRM only on POSIX; Windows installs use plain run + thread guard
    has_alarm = hasattr(signal, "SIGALRM")
    if has_alarm:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(BUDGET_SEC)
    try:
        report = compute_drift(
            sha,
            openapi_path=REPO_ROOT / "docs" / "02_architecture" / "api" / "openapi.yaml",
            frd_dir=REPO_ROOT / "docs" / "01_requirements",
            code_dir=REPO_ROOT / "src",
        )
    except _Timeout:
        _write_warning(f"drift hook timeout > {BUDGET_SEC}s for commit {sha[:12]} — skipped (Rule 9.17.1)")
        return 0
    except Exception as exc:
        _write_warning(f"drift hook error for commit {sha[:12]}: {exc} — advisory")
        return 0
    finally:
        if has_alarm:
            signal.alarm(0)

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
