"""SelfImproving `check` 的引用完整性與 `fixed@` 解析（TCS-SelfImproving-P0 R17、R18）。"""

from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath

from lib.si_git import Git
from lib.si_ledger import Finding, Ledger, split_lines
from lib.si_rows import DEF_ID_RE, FIXED_SHA_RE, ORIG_AT_RE, disp_token, row_marks

_KEY_RE = re.compile(r"^\|\s*(OBS-SI-\d+)\s*\|")
_DEF_KEY_RE = re.compile(r"^\s*\|\s*(DEF-\d+-\d+)\s*\|")
_FAMILY_RE = re.compile(r"^(ATT|PROP|DEC|APP|MEA|RUN)-SI-")
_GREP_PATTERN = r"(OBS|ATT|PROP|DEC|APP|MEA|RUN)-SI-[0-9]+"
_QUALITY = "docs/06_quality"
_MAX_LOCS = 5


def git_ne(detail: str = "git 不可用，無法判定") -> Finding:
    return Finding("-", "GIT-UNAVAILABLE", "info", detail)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def fixed_sha_findings(led: Ledger, git: Git) -> list[Finding]:
    rows = []
    for row in led.rows:
        tok = disp_token(row.cells[7]) if row.nine else None
        if tok and FIXED_SHA_RE.match(tok):
            rows.append((row, tok[len("fixed@"):]))
    if not rows:
        return []
    if not git.available:
        return [git_ne()]
    return [Finding(r.subject, "FIXED-SHA-UNRESOLVED", "fail", f"欄「處置」的 sha {sha} 非 commit")
            for r, sha in rows if not git.is_commit(sha)]


def def_findings(led: Ledger, repo: Path) -> list[Finding]:
    refs = []
    for row in led.rows:
        tok = disp_token(row.cells[7]) if row.nine else None
        if tok and DEF_ID_RE.match(tok):
            refs.append((row, tok))
    if not refs:
        return []
    qdir = repo / _QUALITY
    files = sorted(qdir.glob("AutoSDD_Defect_Log*.md")) if qdir.is_dir() else []
    sisters = ("AutoSDD_External_Blocked_Log.md", "AutoSDD_Structural_Debt_Log.md")
    files += [qdir / n for n in sisters if (qdir / n).is_file()]
    if not files:
        return [Finding("-", "SOURCE-UNAVAILABLE", "info", "缺陷帳本家族檔案全缺")]
    known: set[str] = set()
    for f in files:
        for ln in split_lines(_read(f)):
            m = _DEF_KEY_RE.match(ln)
            if m:
                known.add(m.group(1))
    return [Finding(r.subject, "DEF-REF-DANGLING", "fail", f"欄「處置」的 {tok} 不在缺陷帳本家族")
            for r, tok in refs if tok not in known]


def _definitions(text: str, rel: str | None, keys: set[str],
                 defs: dict[tuple[str, int], str]) -> None:
    for i, ln in enumerate(split_lines(text), start=1):
        m = _KEY_RE.match(ln)
        if m:
            keys.add(m.group(1))
            if rel is not None:
                defs[(rel, i)] = m.group(1)


def obs_findings(ledger_text: str, ledger_rel: str | None, repo: Path, git: Git
                 ) -> tuple[list[Finding], list[Finding]]:
    """回（ref.obs 的 findings, ref.carrier_families 的 findings）。"""
    if not git.available:
        return [git_ne()], [git_ne()]
    keys: set[str] = set()
    defs: dict[tuple[str, int], str] = {}
    _definitions(ledger_text, ledger_rel, keys, defs)
    qdir = repo / _QUALITY
    if qdir.is_dir():
        for f in sorted(qdir.glob("SelfImproving_Observation_Ledger_archive*.md")):
            _definitions(_read(f), f"{_QUALITY}/{f.name}", keys, defs)
    hits = git.grep_only(_GREP_PATTERN)
    if hits is None:
        return [git_ne()], [git_ne()]
    mentions: dict[str, list[str]] = {}
    fam_count, fams = 0, set()
    consumed: set[tuple[str, int]] = set()
    for path, line, token in hits:
        if token.startswith("OBS-SI-"):
            if defs.get((path, line)) == token and (path, line) not in consumed:
                consumed.add((path, line))
                continue
            loc = f"{path}:{line}"
            if token not in keys and loc not in mentions.setdefault(token, []):
                mentions[token].append(loc)
        elif _FAMILY_RE.match(token):
            fam_count += 1
            fams.add(token.rsplit("-", 1)[0])
    obs = []
    for ident, locs in mentions.items():
        shown = ", ".join(locs[:_MAX_LOCS])
        more = f" …+{len(locs) - _MAX_LOCS}" if len(locs) > _MAX_LOCS else ""
        obs.append(Finding(ident, "OBS-REF-DANGLING", "fail", f"引用處 {shown}{more}"))
    carriers = []
    if fam_count:
        carriers.append(Finding("-", "CARRIER-NOT-ESTABLISHED", "info",
                                f"families={','.join(sorted(fams))} count={fam_count}"))
    return obs, carriers


def _escapes_repo(rel: str) -> bool:
    """R18 (c)：絕對路徑、rooted 路徑、含磁碟機代號或含 `..` 者視同逃出 repo（一律當不存在）。

    跨平台自問（鐵律三）：同一份帳本在 Windows 與 POSIX 必須得同一個判決，而 `Path.is_absolute()`
    依平台而異——Windows 上 `/x`、`\\x`（有根、無磁碟機代號）不算絕對，接到 repo 之下卻解析到
    磁碟機根（逃出）；POSIX 上 `C:/x` 只是名為 `C:` 的相對目錄、`\\` 不是分隔符。故不用平台的
    `is_absolute()`，改以 Windows 語法（`/`、`\\` 皆分隔符）一律判：開頭 `/`、`\\`（含 UNC）、
    有磁碟機代號、任一段是 `..`。
    """
    win = PureWindowsPath(rel)
    return rel.startswith(("/", "\\")) or bool(win.drive) or ".." in win.parts


def orig_findings(led: Ledger, repo: Path) -> list[Finding]:
    out = []
    for row in led.rows:
        orig = row_marks(row).get("orig")
        if not orig or orig[1] or not ORIG_AT_RE.match(orig[0]):
            continue
        rel, anchor = orig[0][1:].split("#", 1)
        target = None if _escapes_repo(rel) else repo / rel
        if target is None or not target.is_file():
            out.append(Finding(row.subject, "ORIG-NOTES-MISSING", "fail", f"附註檔不存在 {rel}"))
            continue
        heading = re.compile(rf"^#{{2,6}}\s+{re.escape(anchor)}\b", re.M)
        if anchor != row.ident or not heading.search(_read(target).replace("\r\n", "\n")):
            out.append(Finding(row.subject, "ORIG-NOTES-ANCHOR", "fail", f"附註檔無錨點 {anchor}"))
    return out
