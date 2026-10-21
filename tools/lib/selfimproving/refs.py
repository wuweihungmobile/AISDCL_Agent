"""SelfImproving `check` 的引用完整性與 `fixed@` 解析（TCS-SelfImproving-P0 R17、R18）。"""

from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath

from . import events as si_events
from .defs import CLOSED_CLASSES, load_rows
from .git import Git
from .ledger import Finding, Ledger, Row, parse_ledger, split_lines
from .rows import DEF_ID_RE, FIXED_SHA_RE, ORIG_AT_RE, disp_token, path_set, row_marks

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


def obs_findings(ledger_text: str, ledger_rel: str | None, repo: Path, git: Git,
                 established: bool = False) -> tuple[list[Finding], list[Finding]]:
    """回（ref.obs 的 findings, ref.carrier_families 的 findings）。`established`＝事件帳本在場：
    ATT、PROP、RUN 三族改由指標存在性判（R104），不再印 CARRIER-NOT-ESTABLISHED。"""
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
            if established and token.startswith(_ESTABLISHED_FAMILIES):
                continue
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


_ESTABLISHED_FAMILIES = ("ATT-SI-", "PROP-SI-", "RUN-SI-")
_POINTERS = {  # 事件 kind → (ID 型欄位, 指向的族)
    "dec": (("prop", "PROP"), ("run", "RUN")), "card": (("prop", "PROP"),),
    "heldout.freeze": (("prop", "PROP"),), "app.sandbox": (("prop", "PROP"),),
    "app.verify": (("prop", "PROP"),), "app.promote": (("prop", "PROP"),),
    "app.rollback": (("prop", "PROP"),), "mea.open": (("prop", "PROP"),),
    "mea.close": (("prop", "PROP"),), "mea.amend": (("prop", "PROP"),),
    "mea.report": (("prop", "PROP"),), "attr.confirm": (("att", "ATT"),),
    "attr.reject": (("att", "ATT"),), "research.scan": (("run", "RUN"),),
    "research.skip": (("run", "RUN"),), "run.close": (("run", "RUN"),),
    "prop": (("run", "RUN"),),
}
_PROPOSED_REF_RE = re.compile(r"^proposed@(PROP-SI-\d{3,})")


def event_ledger(repo: Path) -> list[dict] | None:
    """事件帳本在場（檔存在且可解析至少一行事件）時回其通過單事件判準的事件，否則 None。"""
    loaded = si_events.load_events(repo / si_events.LEDGER_REL)
    return si_events.sound(loaded) if loaded else None


def family_findings(repo: Path, events: list[dict], obs_texts: list[str]) -> list[Finding]:
    """R104 (b)：ATT、PROP、RUN 三族的指標形態引用存在性判。事件帳本內與提案目錄的懸空指標＝FAIL；
    OBS 列處置的懸空 `proposed@PROP-SI-N`＝warn（歷史列與夾具的合成指標不致使項目轉紅）。
    散文提及、規格與報告類文件不判。"""
    ids = {"PROP": {e["id"] for e in events if e["kind"] == "prop"},
           "RUN": {e["run"] for e in events if e["kind"] == "run.open"},
           "ATT": {e["id"] for e in events if e["kind"] == "attr"}}
    out = []
    for e in events:
        for key, fam in _POINTERS.get(e["kind"], ()):
            if key in e and e[key] not in ids[fam]:
                out.append(Finding(f"seq={e['seq']}", "FAMILY-REF-DANGLING", "fail",
                                   f"{e['kind']}.{key}={e[key]} 不在事件帳本內"))
    pdir = repo / si_events.PROPOSALS_REL
    if pdir.is_dir():
        out += [Finding(d.name, "PROP-DIR-ORPHAN", "fail", "提案目錄沒有對應的 prop 事件")
                for d in sorted(pdir.iterdir())
                if d.is_dir() and si_events.PROP_RE.match(d.name) and d.name not in ids["PROP"]]
    for text in obs_texts:
        for row in parse_ledger(text).rows:
            m = _PROPOSED_REF_RE.match(row.cells[7]) if row.nine else None
            if m and m.group(1) not in ids["PROP"]:
                out.append(Finding(row.ident, "FAMILY-REF-DANGLING", "warn",
                                   f"[warn] 處置 {m.group(1)} 不在事件帳本內"))
    return out


def archive_texts(repo: Path) -> list[str]:
    qdir = repo / _QUALITY
    return [_read(f) for f in sorted(qdir.glob("SelfImproving_Observation_Ledger_archive*.md"))
            ] if qdir.is_dir() else []


def obs_ledger_text(repo: Path) -> str | None:
    p = repo / "docs/06_quality/SelfImproving_Observation_Ledger.md"
    return _read(p) if p.is_file() else None


def obs_rows(repo: Path) -> dict[str, Row]:
    """OBS 帳本（含 `…_archive*.md`）的合法列：ID → 列。"""
    out: dict[str, Row] = {}
    qdir = repo / _QUALITY
    files = [qdir / "SelfImproving_Observation_Ledger.md"]
    files += sorted(qdir.glob("SelfImproving_Observation_Ledger_archive*.md")) if qdir.is_dir() \
        else []
    for f in files:
        if f.is_file():
            for row in parse_ledger(_read(f)).rows:
                if row.nine and row.kind == 1:
                    out.setdefault(row.ident, row)
    return out


def def_ids(repo: Path) -> set[str]:
    """缺陷帳本家族（P0 R18 (b) 所列各檔）的全部 DEF 號。"""
    qdir = repo / _QUALITY
    files = sorted(qdir.glob("AutoSDD_Defect_Log*.md")) if qdir.is_dir() else []
    files += [qdir / n for n in ("AutoSDD_External_Blocked_Log.md",
                                 "AutoSDD_Structural_Debt_Log.md") if (qdir / n).is_file()]
    return {m.group(1) for f in files for ln in split_lines(_read(f))
            if (m := _DEF_KEY_RE.match(ln))}


def def_evidence(repo: Path) -> dict[str, str]:
    """缺陷帳本家族各 DEF 列的「現象與證據」欄文字（同冷卻的證據座標來源，R82 (c)）。"""
    qdir = repo / _QUALITY
    files = sorted(qdir.glob("AutoSDD_Defect_Log*.md")) if qdir.is_dir() else []
    files += [qdir / n for n in ("AutoSDD_External_Blocked_Log.md",
                                 "AutoSDD_Structural_Debt_Log.md") if (qdir / n).is_file()]
    return {r.ident: r.evidence for f in files for r in load_rows(f)}


_CLOSED_OBS = ("fixed@", "DEF-", "merged@")


def _closed_obs_paths(text: str, out: dict[str, set[str]]) -> None:
    for row in parse_ledger(text).rows:
        tok = disp_token(row.cells[7]) if row.nine else None
        if tok and (tok.startswith(_CLOSED_OBS) or tok in ("retired", "decided")):
            out.setdefault(row.ident, set()).update(path_set(row.cells[4]))


def closed_rows(repo: Path, obs_text: str) -> dict[str, set[str]]:
    """已結列（ID → 證據路徑集合）：OBS 帳本含 archive 的已結處置，與缺陷帳本家族中分類為
    fixed／wontfix／closed-by-decision／routed 的 DEF 列（R45）。"""
    out: dict[str, set[str]] = {}
    _closed_obs_paths(obs_text, out)
    qdir = repo / _QUALITY
    for f in sorted(qdir.glob("SelfImproving_Observation_Ledger_archive*.md")) if qdir.is_dir() \
            else []:
        _closed_obs_paths(_read(f), out)
    files = sorted(qdir.glob("AutoSDD_Defect_Log*.md")) if qdir.is_dir() else []
    files += [qdir / n for n in ("AutoSDD_External_Blocked_Log.md",
                                 "AutoSDD_Structural_Debt_Log.md") if (qdir / n).is_file()]
    for f in files:
        for r in load_rows(f):
            if r.status in CLOSED_CLASSES:
                out.setdefault(r.ident, set()).update(path_set(r.evidence))
    return out


def _deferred_obs_paths(text: str, out: dict[str, set[str]]) -> None:
    for row in parse_ledger(text).rows:
        if row.nine and disp_token(row.cells[7]) == "deferred":
            out.setdefault(row.ident, set()).update(path_set(row.cells[4]))


def reopenable_rows(repo: Path, obs_text: str) -> dict[str, set[str]]:
    """`attr --type link --reopens` 的目標（R110）：已結列（`closed_rows`）加處置首詞為 `deferred`
    的 OBS 列（含封存檔；`deferred` 必附再開症狀、被再開即其語意）。`closed_rows` 與 R45 復發候選
    提示判準不變（`deferred` 的再開由立案者明示連結，不是路徑相交的推測）。"""
    out = closed_rows(repo, obs_text)
    _deferred_obs_paths(obs_text, out)
    qdir = repo / _QUALITY
    for f in sorted(qdir.glob("SelfImproving_Observation_Ledger_archive*.md")) if qdir.is_dir() \
            else []:
        _deferred_obs_paths(_read(f), out)
    return out


def reopen_findings(repo: Path, ledger_rel: str | None, led: Ledger, obs_text: str,
                    git: Git) -> list[Finding]:
    """R45：對新列（不在 HEAD 版、處置 open、無 reopens 標記）列出同證據路徑的已結列（warn）。"""
    if ledger_rel is None or not git.available:
        return []
    head = git.show("HEAD", ledger_rel)
    known = {r.ident for r in parse_ledger(head).rows} if head else set()
    closed = closed_rows(repo, obs_text)
    out = []
    for row in led.rows:
        if not row.nine or row.ident in known or disp_token(row.cells[7]) != "open" \
                or "reopens" in row_marks(row):
            continue
        mine = path_set(row.cells[4])
        hits = sorted((i for i, ps in closed.items() if i != row.ident and ps & mine),
                      key=lambda s: s.encode("utf-8"))
        if hits:
            more = f" …+{len(hits) - _MAX_LOCS}" if len(hits) > _MAX_LOCS else ""
            out.append(Finding(row.ident, "REOPEN-CANDIDATE", "warn",
                               f"[warn] 同證據路徑的已結列：{', '.join(hits[:_MAX_LOCS])}{more}"))
    return out


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
