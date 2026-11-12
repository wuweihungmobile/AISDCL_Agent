"""SelfImproving 推送守門的「內容與設定」判準（TCS-SelfImproving-P7 AC-SI-49-2～49-5；自
`pushguard` 拆出以守 LOC 分級，行為不變）。

能力類別 `ro`：只讀 git、事件帳本與 `<si>/push/`，不寫任何檔。兩件事的**單一來源**：
①「這份差分合不合帳本規則、檔案模式、大小與機密樣式」`content_problems`（`patrolrun._commit`
經 `rule_problem`、`evaluate` 經 `_Judge.judge`，全套件沒有第二份實作）；②「本機 git 設定與
遠端位置能不能放行」`config_problem`。
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

from . import check as si_check
from . import events as si_events
from . import rows as ledger_rows
from .git import Git, scan_names
from .ledger import parse_ledger, split_lines, structure_findings

_CELL_RE = re.compile(r"(?<!\\)\|")
_KINDS = ("app.promote", "app.rollback")
_LEDGERS = (si_events.LEDGER_REL, si_check.LEDGER_REL)


# ── 單一來源二：帳本差分規則 ──────────────────────────────────────────────────────────
def _norm(raw: bytes) -> str:
    return raw.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")


def _obs_problem(old: str, new: str) -> str | None:
    """OBS 帳本：表頭與表外文字不變；舊列依序保留；既有列只准把處置欄由 `open` 轉為終值一次；其
    餘為追加。"""
    lo, ln = parse_ledger(old), parse_ledger(new)
    skeleton = []
    for text, led in ((old, lo), (new, ln)):
        taken = {r.lineno for r in led.rows}
        lines = split_lines(text)
        while lines and not lines[-1].strip():
            lines.pop()
        skeleton.append([x for no, x in enumerate(lines, 1) if no not in taken])
    if skeleton[0] != skeleton[1]:
        return "OBS 帳本的表頭或表外文字被改動"
    if len(ln.rows) < len(lo.rows):
        return "OBS 帳本刪除了既有列"
    for a, b in zip(lo.rows, ln.rows, strict=False):
        if a.raw == b.raw:
            continue
        pa, pb = _CELL_RE.split(a.raw), _CELL_RE.split(b.raw)  # ['', 九欄…, '']；處置欄在索引 8
        same = len(pa) == len(pb) == 11 and pa[:8] == pb[:8] and pa[9:] == pb[9:]
        if not (same and pa[8].strip() == "open" and pb[8].strip() not in ("", "open")):
            return f"OBS 帳本既有列 {a.ident} 被改動（只准處置欄由 open 轉終值一次）"
    return None


#: 提案目錄內允許新增的檔名（SI 動詞會產生的三種；其餘一律不准，審查 F-03）與單檔大小上限（位元組）
_PROP_FILE_RE = re.compile(r"^(?:r\d+\.(?:patch|md)|verify\d+\.json)$")
PROPOSAL_FILE_MAX_BYTES = 1_048_576
CODE_MODE = "PUSH-FILE-MODE-INVALID"  # 提交含符號連結、子模組或檔案模式變更（審查 F-03）
CODE_SECRET = "PUSH-SECRET-PATTERN"  # 提交新增的內容命中機密樣式表（審查 F-03）
CODE_CONFIG = "PUSH-GIT-CONFIG-UNSAFE"  # 本機 git 設定含不允許的鍵（審查 F-04）
CODE_URL = "PUSH-REMOTE-URL-CHANGED"  # 遠端網址與 `sched arm` 記錄的不同（審查 F-04）
CODE_DIVERGED = "PUSH-REMOTE-DIVERGED"  # 遠端 main 不是待推提交的祖先


def _event_lines_problem(old: str, new: str) -> str | None:
    """事件帳本新增的每一行都要是 `events.validate` 通過、`seq` 連續的事件（與 `check` 同一判準）。
    """
    if old and not old.endswith("\n"):
        return "事件帳本既有末行沒有換行就被接續"
    prev = max((ln.obj["seq"] for ln in si_events.read_lines(old.encode("utf-8"))
                if ln.obj is not None and isinstance(ln.obj.get("seq"), int)), default=0)
    base_no = old.count("\n")
    for ln in si_events.read_lines(new[len(old):].encode("utf-8")):
        if ln.obj is None or si_events.validate(ln.obj):
            return f"事件帳本 第 {base_no + ln.no} 行 格式不合（非合格事件）"
        if ln.obj["seq"] != prev + 1:
            return f"事件帳本 第 {base_no + ln.no} 行 seq 不連續"
        prev = ln.obj["seq"]
    return None


def _new_rows_problem(old: str, new: str, row_max) -> str | None:
    """OBS 帳本新增的列要通過 `check` 的列驗證（必填、枚舉、座標、時間、位元組…）。"""
    led, first = parse_ledger(new), len(parse_ledger(old).rows)
    fresh = {r.subject: r.lineno for r in led.rows[first:]}
    for f in structure_findings(led):  # 欄數、ID 形、重複與遞增（與 `check` 的結構判準同一函式）
        if f.level == "fail" and f.subject in fresh:
            return f"OBS 帳本 第 {fresh[f.subject]} 行 {f.code}"
    for item, found in ledger_rows.evaluate_rows(led, row_max).items():
        for f in found:
            if f.level == "fail" and f.subject in fresh:
                return f"OBS 帳本 第 {fresh[f.subject]} 行 {item} {f.code}"
    return None


def ledger_rule_problems(prop: str, changes, row_max=None) -> str | None:
    """帳本差分規則（R-26 b、R-31）：`changes`＝[(路徑, 狀態 A／M／D, 舊內容或 None, 新內容或
    None)]（內容為 LF 正規化文字；只有兩份帳本需要內容）。事件帳本只准尾端追加（舊內容為新內容的
    前綴）且新增行須為合格事件；OBS 帳本見 `_obs_problem`，新列須過列驗證；該 PROP 的提案目錄只准
    新增、檔名限封閉樣式。合規回 None，否則回一句違規描述。"""
    pdir = f"{si_events.PROPOSALS_REL}/{prop}/"
    for path, status, old, new in changes:
        if path in _LEDGERS:
            name = "事件帳本" if path == si_events.LEDGER_REL else "OBS 帳本"
            if status not in ("A", "M") or (status == "M" and (old is None or new is None)):
                return f"{name}被刪除或無法比對"
            if status == "M" and path == si_events.LEDGER_REL and not new.startswith(old):
                return "事件帳本既有內容被改動（只准尾端追加）"
            problem = None
            if status == "M" and path == si_events.LEDGER_REL:
                problem = _event_lines_problem(old, new)
            elif status == "M":
                problem = _obs_problem(old, new) or _new_rows_problem(old, new, row_max)
            if problem:
                return problem
        elif path.startswith(pdir):
            if status != "A":
                what = "刪除" if status == "D" else "修改"
                return f"提案檔 {path[len(pdir):]} 被{what}（只准新增檔）"
            if not _PROP_FILE_RE.fullmatch(path[len(pdir):]):
                return f"提案檔 {path[len(pdir):]} 檔名不在封閉樣式"
    return None


def added_text(path: str, old: str | None, new: str | None, raw: bytes | None) -> str:
    """這次提交「新增」的文字（供機密掃描）：帳本只取追加的部分，其他檔取全文；無法解碼＝空字串。"""
    if path == si_events.LEDGER_REL and new is not None:
        return new[len(old or ""):]
    if path == _LEDGERS[1] and new is not None:
        led = parse_ledger(new)
        return "\n".join(r.raw for r in led.rows[len(parse_ledger(old or "").rows):])
    if old is not None and new is not None:  # 既有檔的修改：只掃新增的行（舊行有同樣字樣不算）
        left, fresh = Counter(old.split("\n")), []
        for line in new.split("\n"):
            if left[line] > 0:
                left[line] -= 1
            else:
                fresh.append(line)
        return "\n".join(fresh)
    try:
        return (raw or b"").decode("utf-8")
    except UnicodeDecodeError:
        return ""


def content_problems(prop: str, items, row_max=None) -> tuple[str, str] | None:
    """內容規則的**單一函式**（`_commit`（經 `rule_problem`）與守門 `judge` 共用；TCS-P7 E-20）：
    `items`＝[(路徑, 狀態, 新模式或 None, 舊內容或 None, 新內容或 None, 新位元組或 None)]（帳本的
    內容為 LF 正規化文字）。依序判：檔案模式（只准 100644，回 `PUSH-FILE-MODE-INVALID`，描述
    `<路徑> <新模式>`）→帳本與提案目錄規則（含檔名、大小、帳本行格式，回 `PUSH-LEDGER-RULE`）→
    新增內容的機密樣式（回 `PUSH-SECRET-PATTERN`，描述 `<路徑> <樣式名>`、不含值）。
    回（碼, 描述）。"""
    for path, status, mode, _old, _new, _raw in items:
        if status != "D" and mode is not None and mode != "100644":
            return CODE_MODE, f"{path} {mode}"
    broken = ledger_rule_problems(prop, [(p, s, o, n) for p, s, _m, o, n, _r in items], row_max)
    if broken:
        return "PUSH-LEDGER-RULE", broken
    pdir = f"{si_events.PROPOSALS_REL}/{prop}/"
    for path, status, _mode, _old, _new, raw in items:
        if status != "D" and path.startswith(pdir) and len(raw or b"") > PROPOSAL_FILE_MAX_BYTES:
            return "PUSH-LEDGER-RULE", f"提案檔 {path[len(pdir):]} 超過大小上限"
    for path, status, _mode, old, new, raw in items:
        if status == "D":
            continue
        if path in _LEDGERS or path.startswith(pdir):  # 文字檔：讀不到或無法解碼＝fail-closed
            try:
                (raw if raw is not None else b"\xff").decode("utf-8")
            except UnicodeDecodeError:
                return CODE_SECRET, f"{path} undecodable"
        names = scan_names(added_text(path, old, new, raw))
        if names:
            return CODE_SECRET, f"{path} {names[0]}"
    return None


def _wt_mode(path: Path) -> str | None:
    """工作樹檔的 git 模式近似值：符號連結 120000、目錄（子模組）160000、POSIX 可執行位元 100755；
    其餘 100644；不存在＝None。"""
    if path.is_symlink():
        return "120000"
    if path.is_dir():
        return "160000"
    if not path.exists():
        return None
    return "100755" if sys.platform != "win32" and path.stat().st_mode & 0o111 else "100644"


def rule_problem(git: Git, repo: Path, prop: str, changes) -> str | None:
    """`_commit` 用：對「將要提交的差分」（HEAD 內容 vs 工作樹內容）跑 `content_problems`；
    `changes`＝`pending` 回的（路徑, 狀態）清單。回第一句違規描述。"""
    items = []
    for path, status in changes:
        old = new = raw = None
        try:
            raw = (repo / path).read_bytes() if status != "D" and (repo / path).is_file() else None
        except OSError:
            raw = None
        if path in _LEDGERS or (status == "M" and raw is not None):
            head = git.show("HEAD", path) if status != "A" else None
            old = None if head is None else _norm(head.encode("utf-8"))
            new = None if raw is None else _norm(raw)
        items.append((path, status, _wt_mode(repo / path), old, new, raw))
    hit = content_problems(prop, items)
    return hit[1] if hit else None


#: repo 既定的 hooks 目錄（`core.hookspath` 須存在且等於它；測試縫：夾具以 mock 替換）
EXPECTED_HOOKS = "tools/git-hooks"
#: 會被 git 當成子命令別名而執行外部程式的子命令（`alias.<子命令>` 命中即不合；TCS-P7 E-21）
ALIAS_GUARDED = frozenset(
    "push status rev-parse rev-list ls-remote diff-tree show cat-file log symbolic-ref "
    "for-each-ref merge-base config add commit diff".split())


def _unsafe_key(key: str, val: str) -> str | None:
    """封閉危險鍵清單（`UNSAFE_KEYS` 的判準函式）：回要顯示的鍵名（子區段以 `*` 代替，避免把網址
    或帳號帶進輸出）；不危險回 None。`key` 已轉小寫（git 對區段與變數名不分大小寫）。"""
    parts = key.split(".")
    sec, name, sub = parts[0], parts[-1], len(parts) > 2
    shown = f"{sec}.*.{name}" if sub else key
    if ((sec == "credential" and name == "helper")
            or (sec == "core" and not sub and name in ("sshcommand", "askpass", "gitproxy"))
            or (sec == "core" and not sub and name == "fsmonitor"
                and val.strip().lower() not in ("false", ""))
            or (sec == "http" and not sub and name == "proxy")
            or (sec == "remote" and sub and name in ("proxy", "pushurl"))
            or (sec == "url" and sub and name in ("insteadof", "pushinsteadof"))
            or (sec == "include" and not sub and name == "path")
            or (sec == "includeif" and sub and name == "path")
            or (sec == "filter" and sub and name in ("clean", "smudge", "process"))
            or (sec == "diff" and ((sub and name == "textconv")
                                   or (not sub and name == "external")))):
        return shown
    if sec == "alias" and key[len("alias."):] in ALIAS_GUARDED:
        return key
    return None


def _norm_hooks(path: str) -> str:
    out = path.strip().replace("\\", "/")
    while out.startswith("./"):
        out = out[2:]
    return out.rstrip("/")


def _norm_url(url: str) -> str:
    """遠端網址正規化：去 userinfo、結尾 `/` 與 `.git`、轉小寫（比對用）。"""
    url = re.sub(r"(://)[^/@\s]*@", r"\1", url.strip())
    return re.sub(r"(\.git)?/*$", "", url).lower()


def _host_of(url: str) -> str:
    """只露 scheme＋主機（已去 userinfo；不含路徑與帳密）；本機路徑沒有主機＝「本機路徑」。"""
    m = re.match(r"^([A-Za-z][A-Za-z0-9+.-]*)://(?:[^/@\s]*@)?([^/\s]*)", url.strip())
    if m:
        return f"{m.group(1).lower()}://{m.group(2)}"[:60]
    scp = re.match(r"^(?:[^/@\s:]+@)?([^/@\s:]+):(?!\\)", url.strip())  # `git@host:路徑`
    return f"ssh://{scp.group(1)}"[:60] if scp and len(scp.group(1)) > 1 else "本機路徑"


def config_problem(j, armed_doc: dict | None) -> tuple[str, str] | None:
    """推送前的 git 設定與遠端網址檢查（審查 F-04）：repo 本機設定含憑證 helper／fsmonitor／
    sshCommand／非預設 hooksPath／pushurl／insteadOf 之一，或遠端網址與 `sched arm` 記錄
    （`push/armed.json` 的內容 `armed_doc`）不同，一律不放行。詳述不含值，只列鍵名或主機名。"""
    cp = j.run("config", "--local", "--list")
    if cp is None or cp.returncode not in (0, 1):
        raise OSError("git config 讀取失敗")
    bad, hooks = [], []
    for ln in cp.stdout.split("\n"):
        key, _, val = ln.strip().partition("=")
        key = key.lower()
        if key == "core.hookspath":
            hooks.append(_norm_hooks(val))
        elif (shown := _unsafe_key(key, val)) is not None:
            bad.append(shown)
    if hooks != [_norm_hooks(EXPECTED_HOOKS)]:  # 不存在、重複或不等於既定目錄，一律不合
        bad.append("core.hookspath")
    if bad:
        return CODE_CONFIG, " ".join(sorted(set(bad))[:3])
    url = j.run("config", "--get", "remote.origin.url")
    now_url = url.stdout.strip() if url is not None and url.returncode == 0 else ""
    armed = (armed_doc or {}).get("remote_url")
    if not isinstance(armed, str) or _norm_url(armed) != _norm_url(now_url):
        old = _host_of(armed) if isinstance(armed, str) else "未記錄"
        return CODE_URL, f"{old} {_host_of(now_url)}"
    return None
