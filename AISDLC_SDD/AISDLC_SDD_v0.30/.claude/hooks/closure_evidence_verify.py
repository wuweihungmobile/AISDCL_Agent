"""closure_evidence_verify.py — improving_21 / DEF-20-001 結案證據強制重推導 hook

Triggered by git native post-commit hook. Advisory only — never blocks commit
(同 post_commit_drift.py / Rule 9.17.1 精神)。Budget: < 2s；逾時/例外寫 flag 即跳過。

把反幻覺紀律落為框架機械閘門：結案 commit 時就 repo 真實狀態重推導 docs/04_planning/
AutoSDD_improving_NN.md 內 closure-evidence 契約宣稱的關鍵數字（commit/tag 廉價層 fail-
closed；pytest passed / ci-gate floors 昂貴層驗綁定 HEAD 之 rederive 證書，否則 inconclusive）。
落差寫 .git/CLOSURE_EVIDENCE_VERDICT（advisory flag，供 CI / 人複核消費），不阻擋 commit。

Install: tools/install_hooks/install_post_commit.sh / .ps1（opt-in，與 post_commit_drift 串接；
不經 .claude/settings.json deny 層，與 Claude Code session 解耦）。
"""
from __future__ import annotations

import concurrent.futures
import signal
import subprocess
import sys
from pathlib import Path

# 純函式邏輯模組（同 post_commit_drift → drift_monitor 慣例）
_PKG_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PKG_ROOT))

from tools.fsm_runtime.closure_evidence import (  # noqa: E402
    evaluate_closure,
    write_verdict_report,
)

BUDGET_SEC = 2


class _Timeout(Exception):
    pass


def _timeout_handler(signum, frame):  # pragma: no cover - signal callback
    raise _Timeout()


def repo_root_from() -> Path:
    """以 `--git-common-dir` 的父目錄定位 monorepo 根（hook 在版本目錄但 commit 在根）；
    fallback `_PKG_ROOT`。

    DEF-101-059：舊版委派 `tools.fsm_runtime.closure_evidence.repo_root_from()`
    （內部用 `git rev-parse --show-toplevel`）定位 repo_root，再天真拼接
    `repo_root / ".git"`。在 git worktree 情境下真的用 `git commit` 觸發本 hook
    時，git 會替 post-commit 子行程注入 `GIT_DIR`（指向
    `<主repo>/.git/worktrees/<name>`）。實測證實：只要繼承到 `GIT_DIR`，
    `--show-toplevel` 無論 `cwd` 為何一律退化成直接回顯 `cwd` 本身（不再向上
    尋根），導致 repo_root 誤算成版本目錄（`.../AISDLC_SDD_v0.30`）——這個路徑
    本無 `.git`，`_write_flag` 的 `git_dir.exists()` 恆 False，
    CLOSURE_EVIDENCE_VERDICT 靜默蒸發（DEF-20-001 反幻覺閘門在 worktree 下真實
    失效，且完全不報錯，使用者無感）。`--git-common-dir` 不受此汙染：不論有無
    `GIT_DIR`、不論 `cwd` 落在主 repo 或 worktree，皆正確解回真正共用的 `.git`
    （與 install_post_commit.sh/.ps1 同手法）。取其父目錄即為主 repo 根——一旦
    repo_root 正確落在主 repo（其 `.git` 恆為真實目錄，不是 worktree 那種指標
    檔），下游 `_write_flag` 沿用 `repo_root / ".git"` 天真拼接就重新變安全，SD
    發現的 naive join 問題隨之消除（根因是 repo_root 算錯，不是拼接手法本身）。

    本函式改為本檔自帶實作（不再 import 共用模組同名函式），刻意保留
    `repo_root_from` 這個名稱與零參數簽名，讓既有測試
    （tools/fsm_runtime/tests/test_closure_evidence.py 的
    `patch.object(closure_hook, "repo_root_from", ...)`）不需改動即可繼續運作。
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


def _write_flag(repo_root: Path, msg: str) -> None:
    git_dir = repo_root / ".git"
    if git_dir.exists():
        (git_dir / "CLOSURE_EVIDENCE_VERDICT").write_text(msg + "\n", encoding="utf-8")


def main() -> int:
    repo_root = repo_root_from()
    # SIGALRM only on POSIX; Windows has no SIGALRM, so the < 2s budget there is
    # enforced via a ThreadPoolExecutor + future.result(timeout=...) guard
    # (DEF-CLDREV-001). Both paths converge on the same fail-soft contract:
    # advisory only, write a flag and never block the commit (Rule 9.17.1 精神)。
    has_alarm = hasattr(signal, "SIGALRM")
    if has_alarm:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(BUDGET_SEC)
        try:
            verdict = evaluate_closure(repo_root)
        except _Timeout:
            _write_flag(repo_root, f"closure hook timeout > {BUDGET_SEC}s — skipped (advisory)")
            return 0
        except Exception as exc:  # fail-soft，絕不阻擋 commit
            _write_flag(repo_root, f"closure hook error: {exc} — advisory")
            return 0
        finally:
            signal.alarm(0)
    else:
        # Windows thread-guard path: bound the wait to BUDGET_SEC. On timeout we
        # cannot truly kill the worker thread, but the hook returns immediately
        # (advisory, never-block); avoid the `with` block's implicit
        # shutdown(wait=True) so a slow evaluate can never overrun the budget.
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(evaluate_closure, repo_root)
        try:
            verdict = future.result(timeout=BUDGET_SEC)
        except concurrent.futures.TimeoutError:
            _write_flag(repo_root, f"closure hook timeout > {BUDGET_SEC}s — skipped (advisory)")
            pool.shutdown(wait=False, cancel_futures=True)
            return 0
        except Exception as exc:  # fail-soft，絕不阻擋 commit
            _write_flag(repo_root, f"closure hook error: {exc} — advisory")
            pool.shutdown(wait=False, cancel_futures=True)
            return 0
        pool.shutdown(wait=False)

    try:
        write_verdict_report(verdict, repo_root)
    except OSError:
        pass

    if verdict.verdict == "FAIL":
        bad = [f"{f.kind}:{f.target[:12]}({f.detail})" for f in verdict.facts if f.status == "FAIL"]
        bad += [f"{c.key}({c.detail})" for c in verdict.claims if c.status == "FAIL"]
        _write_flag(
            repo_root,
            "❌ CLOSURE_EVIDENCE FAIL — 結案宣稱與 repo 真實狀態不符（疑幻覺/造假，DEF-20-001）："
            + "; ".join(bad),
        )
    elif verdict.verdict == "INCONCLUSIVE":
        if not verdict.facts and not verdict.claims:
            _write_flag(
                repo_root,
                "⚠️ CLOSURE_EVIDENCE INCONCLUSIVE — 未找到 closure-evidence 契約（最新 improving_NN.md "
                "末尾缺真實 ```yaml closure-evidence 區塊）— advisory",
            )
        else:
            _write_flag(
                repo_root,
                "⚠️ CLOSURE_EVIDENCE INCONCLUSIVE — git 事實已驗，昂貴項待 rederive 證書綁定當前 HEAD "
                "（跑 python -m tools.fsm_runtime.closure_evidence --rederive）— advisory",
            )
    else:  # VERIFIED
        _write_flag(repo_root, "✅ CLOSURE_EVIDENCE VERIFIED — 結案宣稱經 repo 真實狀態重推導通過")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
