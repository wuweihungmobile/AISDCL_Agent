"""SelfImproving `check` 的歷史比對：遷移豁免與 ROW-MUTATED（TCS-SelfImproving-P0 R19、R20）。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lib.si_git import Git
from lib.si_ledger import Finding, parse_ledger
from lib.si_refs import git_ne
from lib.si_rows import disp_token, row_marks

_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_SID_RE = re.compile(r"sid\s*[:=]?\s*[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", re.I)
_LINE_RE = re.compile(r"line\s*[:=]?\s*\d+", re.I)


@dataclass
class Migration:
    status: str = "none"  # none｜valid｜invalid｜unavailable
    sha: str | None = None
    detail: str = "claim=none"
    findings: list[Finding] = field(default_factory=list)


def _fail(code: str, subject: str, detail: str) -> Migration:
    return Migration("invalid", None, "claim=invalid", [Finding(subject, code, "fail", detail)])


def evaluate_migration(claim, led, git: Git, ledger_rel: str | None) -> Migration:
    """R19：(a) 格式 (b) 解析成 commit (c) 是 HEAD 祖先 (d) 有掌舵者確認列；
    (e) orig 只准出現在遷移當下已存在的列。"""
    if claim is None:
        return Migration()
    sub = "migration_base_sha"
    if not isinstance(claim, str) or not _SHA40_RE.match(claim):
        return _fail("MIG-SHA-FORMAT", sub, "migration_base_sha 須為 40 位小寫 hex")
    if not git.available:
        return Migration("unavailable", None, "claim=unavailable", [git_ne()])
    if not git.is_commit(claim):
        return _fail("MIG-SHA-UNRESOLVED", sub, "migration_base_sha 解析不到 commit")
    if not git.is_ancestor(claim):
        return _fail("MIG-SHA-NOT-ANCESTOR", sub, "migration_base_sha 不是 HEAD 的祖先")
    if not any(_is_confirm(r, claim) for r in led.rows):
        return _fail("MIG-CONFIRM-MISSING", "-", "缺掌舵者確認列（decided＋sha＋sid＋line）")
    out = Migration("valid", claim, "claim=valid")
    base_ids = _ids_at(git, claim, ledger_rel)
    for row in led.rows:
        if row.nine and "orig" in row_marks(row) and row.ident not in base_ids:
            out.findings.append(Finding(row.subject, "ORIG-OUTSIDE-MIGRATION", "fail",
                                        "orig 只准出現在遷移當下已存在的列"))
    return out


def _is_confirm(row, sha: str) -> bool:
    if not row.nine or disp_token(row.cells[7]) != "decided":
        return False
    return sha[:7].lower() in row.raw.lower() and bool(_SID_RE.search(row.raw)) \
        and bool(_LINE_RE.search(row.raw))


def _ids_at(git: Git, commit: str, rel: str | None) -> set[str]:
    text = git.show(commit, rel) if rel else None
    return {r.ident for r in parse_ledger(text).rows} if text else set()


def _cells_by_id(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for row in parse_ledger(text.replace("\r\n", "\n")).rows:
        if row.cells is not None and row.ident:
            out.setdefault(row.ident, row.cells)
    return out


def _allowed(prev: list[str], nxt: list[str]) -> bool:
    if len(prev) != len(nxt) or len(prev) < 8:
        return False
    return disp_token(prev[7]) == "open" and disp_token(nxt[7]) != "open" \
        and all(a == b for i, (a, b) in enumerate(zip(prev, nxt)) if i != 7)


def evaluate_mutations(git: Git, ledger_rel: str | None, ledger_text: str,
                       migration: Migration) -> tuple[list[Finding], str]:
    """回（findings, 項目層 detail）。findings 內 level 為 info 者表 NE。"""
    if ledger_rel is None:
        return [Finding("-", "SOURCE-UNAVAILABLE", "info", "帳本不在 repo 內，無歷史可比")], ""
    if not git.available:
        return [git_ne()], ""
    if migration.status == "valid":
        base = migration.sha
    else:
        log = git.log_first_parent(ledger_rel)
        if not log:
            return [], "no-history"
        base = log[0]
    versions: list[tuple[str, str]] = []
    first = git.show(base, ledger_rel)
    versions.append((base[:7], first or ""))
    for commit in git.log_first_parent(ledger_rel, f"{base}..HEAD") or []:
        versions.append((commit[:7], git.show(commit, ledger_rel) or ""))
    work = ledger_text.replace("\r\n", "\n")
    if work != versions[-1][1].replace("\r\n", "\n"):
        versions.append(("WORKTREE", work))
    findings: list[Finding] = []
    for (_, old), (label, new) in zip(versions, versions[1:]):
        before, after = _cells_by_id(old), _cells_by_id(new)
        for ident, cells in before.items():
            if ident not in after:
                cause = "deleted"
            elif after[ident] != cells and not _allowed(cells, after[ident]):
                cause = "changed"
            else:
                continue
            findings.append(Finding(ident, "ROW-MUTATED", "fail",
                                    f"commit={label} cause={cause} 列被原地改寫，請掌舵者過目"))
    return findings, ""
