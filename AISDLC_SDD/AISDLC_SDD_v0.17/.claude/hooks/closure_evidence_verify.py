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

import signal
import sys
from pathlib import Path

# 純函式邏輯模組（同 post_commit_drift → drift_monitor 慣例）
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.fsm_runtime.closure_evidence import (  # noqa: E402
    evaluate_closure,
    repo_root_from,
    write_verdict_report,
)

BUDGET_SEC = 2


class _Timeout(Exception):
    pass


def _timeout_handler(signum, frame):  # pragma: no cover - signal callback
    raise _Timeout()


def _write_flag(repo_root: Path, msg: str) -> None:
    git_dir = repo_root / ".git"
    if git_dir.exists():
        (git_dir / "CLOSURE_EVIDENCE_VERDICT").write_text(msg + "\n", encoding="utf-8")


def main() -> int:
    repo_root = repo_root_from()
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
        if has_alarm:
            signal.alarm(0)

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
