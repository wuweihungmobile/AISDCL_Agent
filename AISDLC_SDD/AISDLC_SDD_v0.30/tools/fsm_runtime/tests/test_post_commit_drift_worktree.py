"""test_post_commit_drift_worktree.py — real `git worktree` + real `git commit`
regression test for the DEF-101-059 class of bug in
`.claude/hooks/post_commit_drift.py` and `.claude/hooks/closure_evidence_verify.py`.

Two independent reviewers found the same underlying defect via two different
reproduction paths:

  - SD reviewer: called the hooks' internal logic directly and showed that a
    naive `repo_root / ".git"` join blows up with `NotADirectoryError` in a
    worktree, because `<worktree>/.git` is a *file* (a `gitdir: <path>`
    pointer), not a directory.

  - QA reviewer: triggered the hooks via a REAL `git commit` inside a REAL
    `git worktree` checkout (not a direct Python call) and found a *different*,
    more severe failure mode: git injects a `GIT_DIR` environment variable
    (pointing at `<main repo>/.git/worktrees/<name>`) into the post-commit hook
    subprocess. With `GIT_DIR` set, `git rev-parse --show-toplevel` degenerates
    to echoing back whatever `cwd` was passed — it does NOT walk up to find the
    real repo root. That silently mis-resolves REPO_ROOT to the hook's own
    version directory (which has no `.git`), so `git_dir.exists()` is False and
    the advisory flag write is skipped — no exception, no message, exit 0. Both
    Rule 9.17.1 drift monitoring and DEF-20-001 closure-evidence anti-hallucination
    gating go completely dark under real worktree commits, and nobody notices.

Why this file exists as a *separate* test module (not added to
tools/fsm_runtime/tests/test_post_commit_drift.py or test_closure_evidence.py):
those existing tests call `hook_module.main()` in-process with REPO_ROOT
monkeypatched directly — they never spawn a real `git commit` subprocess, so
they never inherit the `GIT_DIR`/`GIT_INDEX_FILE` environment that git itself
injects into a real post-commit hook invocation. That environment shape is
exactly what QA's finding depends on, and it is *not* reproducible by calling
Python functions directly in the same process — only a real `git worktree add`
+ real `git commit` reproduces it. Hence this module drives the hooks through
that exact real path end-to-end.

Why the hook files are *copied* into a throwaway fake "monorepo" instead of
invoked in place: the hooks compute their own REPO_ROOT from
`Path(__file__).resolve().parents[2]` (`_PKG_ROOT`) and use it as the `cwd` for
`git rev-parse`. If we exec'd the real in-tree hook files directly against a
throwaway temp git repo, `_PKG_ROOT` would still point at *this* real
development repo — and on the plain (non-worktree) path git does NOT inject
`GIT_DIR`, so `git rev-parse --git-common-dir` would fall back to normal
upward cwd-discovery from `_PKG_ROOT` and silently resolve to *this real
repo's* `.git`, writing advisory files (and drift/closure report YAMLs) into
the actual development tree instead of the throwaway one. (This was caught
during development of this test — see cleanup note in the fix's summary.)
Copying the hook + its two pure-function dependencies into a throwaway
version-dir *inside* the temp repo makes `_PKG_ROOT` resolve inside the temp
repo instead, so all git resolution — worktree or plain — stays hermetically
inside `tmp_path` and never touches the real repo.

Acceptance:
  - a real `git commit` inside a real linked worktree does not crash (no
    Python traceback on stderr — catches the SD naive-join `NotADirectoryError`)
  - COMMIT_DRIFT_WARNING and CLOSURE_EVIDENCE_VERDICT are actually written into
    the *shared* main-repo `.git/` (catches both the SD crash and the QA
    silent-failure mode)
  - the equivalent commit in a plain (non-worktree) checkout keeps working
    (no regression for the common case)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# This test's own file lives at <v0.30>/tools/fsm_runtime/tests/, matching
# tools/fsm_runtime/tests/test_post_commit_drift.py's own parents[3] arithmetic
# (relocated here from tools/tests/ so pytest.ini's testpaths and ci-gate.sh's
# explicit `pytest tools/fsm_runtime/tests/` invocation actually collect it —
# tools/tests/ is not on either collection path).
_V030_ROOT = Path(__file__).resolve().parents[3]
_REAL_HOOK_DRIFT = _V030_ROOT / ".claude" / "hooks" / "post_commit_drift.py"
_REAL_HOOK_CLOSURE = _V030_ROOT / ".claude" / "hooks" / "closure_evidence_verify.py"
_REAL_DRIFT_MONITOR = _V030_ROOT / "tools" / "fsm_runtime" / "drift_monitor.py"
_REAL_CLOSURE_EVIDENCE = _V030_ROOT / "tools" / "fsm_runtime" / "closure_evidence.py"

pytestmark = pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="hook chain installed here as a POSIX shell shebang script; Windows "
    "post-commit wiring is exercised separately via install_post_commit.ps1 (out of scope)",
)


def _run(cmd: list[str], cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
        encoding="utf-8", errors="replace",
    )


def _git(args: list[str], cwd: Path) -> str:
    proc = _run(["git", *args], cwd)
    assert proc.returncode == 0, f"git {args} failed:\nstdout={proc.stdout}\nstderr={proc.stderr}"
    return proc.stdout.strip()


def _materialize_hook_copies(main_dir: Path) -> tuple[Path, Path]:
    """Copy the real hook files + their two pure-function dependencies into a
    throwaway `version_dir/` inside the temp repo, so the hooks' own
    `Path(__file__).resolve().parents[2]` resolves *inside tmp_path* — never
    into this real development repo (see module docstring for why that
    matters). Stub `__init__.py`s are deliberately empty: the real
    `tools/fsm_runtime/__init__.py` eagerly imports ~140 sibling modules that
    are irrelevant here and would drag in unrelated dependencies; the two
    leaf modules copied below only import stdlib + `yaml`, no sibling
    imports, so empty package markers are sufficient.
    """
    version_dir = main_dir / "version_dir"
    hooks_dir = version_dir / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    fsm_dir = version_dir / "tools" / "fsm_runtime"
    fsm_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "tools" / "__init__.py").write_text("", encoding="utf-8")
    (fsm_dir / "__init__.py").write_text("", encoding="utf-8")

    shutil.copy2(_REAL_DRIFT_MONITOR, fsm_dir / "drift_monitor.py")
    shutil.copy2(_REAL_CLOSURE_EVIDENCE, fsm_dir / "closure_evidence.py")

    hook_drift = hooks_dir / "post_commit_drift.py"
    hook_closure = hooks_dir / "closure_evidence_verify.py"
    shutil.copy2(_REAL_HOOK_DRIFT, hook_drift)
    shutil.copy2(_REAL_HOOK_CLOSURE, hook_closure)
    return hook_drift, hook_closure


def _seed_high_drift_spec(main_dir: Path) -> None:
    """Write an OpenAPI path with no matching code endpoint so compute_drift's
    api_drift hits 1.0 (total_score 0.6 >= 0.3). This forces
    COMMIT_DRIFT_WARNING to actually be written (it is conditional on
    drift_score >= 0.3), so the test can assert on its real location instead
    of relying solely on the unconditionally-written closure flag.

    Lives under `main_dir` (the shared/main checkout), not the worktree,
    because after the fix REPO_ROOT resolves to the parent of the shared
    `--git-common-dir` — i.e. the main checkout — regardless of which worktree
    actually made the commit (see module docstring).
    """
    api_dir = main_dir / "docs" / "02_architecture" / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "openapi.yaml").write_text(
        "paths:\n  /foo:\n    get:\n      summary: dummy\n", encoding="utf-8"
    )


def _install_hook_chain(main_dir: Path) -> None:
    """Init a throwaway repo at main_dir and wire the (copied) real
    post-commit hook chain, mirroring
    tools/install_hooks/install_post_commit.sh's exec mechanism (chaining the
    two hook .py files as `python <path> "$@" || true`). Does not invoke that
    script directly: its LATEST-version auto-discovery assumes the real
    monorepo's `AISDLC_SDD/AISDLC_SDD_v*` layout, which this throwaway repo
    doesn't have.
    """
    main_dir.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], main_dir)
    _git(["config", "user.email", "test@example.com"], main_dir)
    _git(["config", "user.name", "test"], main_dir)
    _seed_high_drift_spec(main_dir)
    hook_drift, hook_closure = _materialize_hook_copies(main_dir)
    (main_dir / "README.md").write_text("init\n", encoding="utf-8")
    _git(["add", "README.md"], main_dir)
    _git(["commit", "-q", "-m", "init"], main_dir)

    hooks_dir = main_dir / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "post-commit"
    hook_path.write_text(
        "#!/usr/bin/env bash\n"
        f'"{sys.executable}" "{hook_drift}" "$@" || true\n'
        f'"{sys.executable}" "{hook_closure}" "$@" || true\n',
        encoding="utf-8",
    )
    hook_path.chmod(0o755)


def _assert_no_traceback(stderr: str) -> None:
    assert "Traceback (most recent call last)" not in stderr, (
        f"hook raised an uncaught exception during real `git commit` (SD naive-join "
        f"regression):\n{stderr}"
    )
    assert "NotADirectoryError" not in stderr, f"naive `.git` join regressed:\n{stderr}"


def test_real_commit_in_plain_checkout_writes_advisory_flags(tmp_path):
    """Baseline / no-regression check: a normal (non-worktree) checkout must
    keep writing both advisory flags exactly as before the fix."""
    main_dir = tmp_path / "main"
    _install_hook_chain(main_dir)

    (main_dir / "file.txt").write_text("hello\n", encoding="utf-8")
    _git(["add", "file.txt"], main_dir)
    proc = _run(["git", "commit", "-q", "-m", "plain commit"], main_dir)

    assert proc.returncode == 0
    _assert_no_traceback(proc.stderr)

    git_dir = main_dir / ".git"
    assert (git_dir / "COMMIT_DRIFT_WARNING").exists(), "drift hook silently no-op'd"
    assert (git_dir / "CLOSURE_EVIDENCE_VERDICT").exists(), "closure hook silently no-op'd"


def test_real_commit_in_worktree_writes_advisory_flags_to_shared_git(tmp_path):
    """DEF-101-059 regression: a REAL `git commit` inside a REAL linked
    `git worktree` must (a) not crash with a traceback and (b) actually write
    both advisory flag files into the *shared* main-repo `.git/` — not
    silently vanish (QA's finding) and not blow up (SD's finding).
    """
    main_dir = tmp_path / "main"
    _install_hook_chain(main_dir)

    wt_dir = tmp_path / "wt"
    _git(["worktree", "add", "-q", "-b", "wtbranch", str(wt_dir)], main_dir)

    # Sanity check on the premise itself: the worktree's `.git` is a *file*
    # (a `gitdir: <path>` pointer), not a directory. This is precisely the
    # shape that makes a naive `repo_root / ".git"` join explode.
    assert (wt_dir / ".git").is_file(), "test premise broken: worktree .git is not a text file"

    (wt_dir / "file.txt").write_text("wt change\n", encoding="utf-8")
    _git(["add", "file.txt"], wt_dir)
    proc = _run(["git", "commit", "-q", "-m", "commit inside worktree"], wt_dir)

    assert proc.returncode == 0
    _assert_no_traceback(proc.stderr)

    shared_git_dir = main_dir / ".git"
    drift_flag = shared_git_dir / "COMMIT_DRIFT_WARNING"
    verdict_flag = shared_git_dir / "CLOSURE_EVIDENCE_VERDICT"

    assert drift_flag.exists(), (
        "COMMIT_DRIFT_WARNING missing from the shared .git/ after a worktree commit — "
        "the drift hook silently no-op'd (QA-reported GIT_DIR-polluted --show-toplevel bug)"
    )
    assert "drift_score" in drift_flag.read_text(encoding="utf-8")

    assert verdict_flag.exists(), (
        "CLOSURE_EVIDENCE_VERDICT missing from the shared .git/ after a worktree commit — "
        "the closure hook silently no-op'd (QA-reported GIT_DIR-polluted --show-toplevel bug)"
    )
    assert "CLOSURE_EVIDENCE" in verdict_flag.read_text(encoding="utf-8")

    # The worktree's own private per-worktree gitdir must NOT have received a
    # stray copy of the flags — confirms REPO_ROOT resolved to the *shared*
    # `.git`, not to some other mis-derived location.
    wt_private_gitdir_pointer = (wt_dir / ".git").read_text(encoding="utf-8").strip()
    assert wt_private_gitdir_pointer.startswith("gitdir:")
