"""SelfImproving 推送守門與巡邏提交的共用判準（TCS-SelfImproving-P7 AC-SI-49-2～49-5）。

能力類別 `ro`：只讀 git、事件帳本與 `<si>/push/`，不寫任何檔、不呼叫 git 的寫入動詞。本檔是兩件事
的**單一來源**（R-25、R-28、R-31）：①「哪些路徑可進巡邏提交」`commit_allow`；②「這份差分合不合帳
本規則」`ledger_rule_problems`。`patrolrun._commit` 於 `git add` 前、`evaluate` 對每個領先提交，都呼
叫同一組函式，全套件沒有第二份實作。

`evaluate` 的前置序（與附錄 A.4b 的碼序一致）：`PUSH-OFF`→`PUSH-NOT-MAIN`→`PUSH-NOT-AHEAD`→
`PUSH-RUNNING`→`PUSH-DIRTY-TREE`→逐提交判準（最早的不符者定案；同一提交取碼序最前者）：
`PUSH-FOREIGN-COMMITS`→`PUSH-NOT-RECORDED`→`PUSH-RECORD-MISMATCH`→`PUSH-APP-KIND-INVALID`→
`PUSH-APP-REUSED`→`PUSH-PATH-OUTSIDE`→`PUSH-LEDGER-RULE`→`PUSH-CONTENT-MISMATCH`。git 不可用、逾
時或讀不到必要物件一律 `PUSH-GIT-UNAVAILABLE`（fail-closed，不拋例外、不放行）。

誠實劃界：git 輸出經 `git.Git` 以文字模式解碼（CRLF 換成 LF、非 UTF-8 位元組被替換）。帳本與提案檔
皆 LF 文字，前綴與 manifest 比對不受影響；touched 檔為非 UTF-8 時 `post_sha256` 對不上，守門判
`PUSH-CONTENT-MISMATCH`（安全側）。
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from . import check as si_check
from . import events as si_events
from . import evspec, manifest, nextstep, sched
from . import paths as si_paths
from .git import Git
from .ledger import parse_ledger, split_lines

CALL_TIMEOUT = 20  # 單一 git 呼叫的牆鐘上限（秒）
TOTAL_BUDGET = 60  # 一次 `evaluate` 的總牆鐘上限（秒；不拖慢心跳）
TRAILER_APP, TRAILER_PROP = "SI-Patrol-App", "SI-Patrol-Prop"
REMOTE = "origin/main"
_TRAILER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*): (\S.*)$")
_PARA_RE = re.compile(r"\n[ \t]*\n")
_CELL_RE = re.compile(r"(?<!\\)\|")
_KINDS = ("app.promote", "app.rollback")
_LEDGERS = (si_events.LEDGER_REL, si_check.LEDGER_REL)


class _GitFail(Exception):
    """git 不可用、逾時或讀不到必要物件（對外一律轉成 `PUSH-GIT-UNAVAILABLE`）。"""


# ── 單一來源一：可進提交的路徑 ────────────────────────────────────────────────────────
def si_own_allow(prop: str) -> list[str]:
    """SI 自有的明確清單（不是前綴泛稱）：事件帳本、OBS 帳本、該 PROP 的提案目錄（尾端 `/`）。"""
    return [*_LEDGERS, f"{si_events.PROPOSALS_REL}/{prop}/"]


def _in_repo(rel: str) -> bool:
    parts = rel.split("/")
    absolute = rel.startswith(("/", "\\")) or ":" in parts[0]
    return bool(rel) and not absolute and ".." not in parts


def commit_allow(prop: str, touched, cls: str) -> list[str]:
    """巡邏提交的允許清單（`patrolrun._commit` 與 `evaluate` 共用）：`si_own_allow(prop)`；非 M 類另
    加該 PROP 的 `touched` 中位於 repo 內者。M 類的 `touched` 是記憶目錄的邏輯路徑（`memory/…`），
    不在 repo 內，一律不收。"""
    mine = [] if cls == "M" else [t for t in touched if _in_repo(t)]
    return list(dict.fromkeys([*si_own_allow(prop), *mine]))


def commit_message(verb: str, pid: str, dec: str, app: str) -> str:
    """巡邏提交訊息：首行、一段說明、末段恰兩個 trailer（`SI-Patrol-App`、`SI-Patrol-Prop`）；
    `parse_trailers` 是它的反函式。"""
    return (f"chore(selfimproving): {verb} {pid}（{dec}、{app}）\n\n"
            "巡邏器依人的決定機械推進後的本機 commit。\n\n"
            f"{TRAILER_APP}: {app}\n{TRAILER_PROP}: {pid}")


def covered(path: str, allow) -> bool:
    """`path` 是否落在允許清單：檔案精確相等，或在以 `/` 結尾的目錄項之下。"""
    return any(path == a or (a.endswith("/") and path.startswith(a)) for a in allow)


def pending(git: Git, allow) -> tuple[list[tuple[str, str]], list[str]]:
    """`git status` 一次取全部改動：回（允許清單內的 [(路徑, 狀態 A／M／D)]，清單外的路徑）。含已
    暫存、未追蹤；改名兩端皆算（新端 A、舊端 D）；git 不可用＝回 ([], [])（視為沒有改動）。"""
    cp = git.run("-c", "core.quotepath=false", "status", "--porcelain", "-z",
                 "--untracked-files=all")
    toks = cp.stdout.split("\0") if cp and cp.returncode == 0 else []
    i, mine, left = 0, [], []
    while i < len(toks):
        tok, i = toks[i], i + 1
        if len(tok) < 4:
            continue
        xy, path = tok[:2], tok[3:]
        moved = "R" in xy or "C" in xy
        ents = [(path, "A" if moved or xy == "??" or "A" in xy else "D" if "D" in xy else "M")]
        if moved:
            if "R" in xy and i < len(toks):
                ents.append((toks[i], "D"))  # 改名的舊端
            i += 1
        for p, st in ents:
            if covered(p, allow):
                mine.append((p, st))
            else:
                left.append(p)
    return mine, left


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


def ledger_rule_problems(prop: str, changes) -> str | None:
    """帳本差分規則（R-26 b、R-31）：`changes`＝[(路徑, 狀態 A／M／D, 舊內容或 None, 新內容或
    None)]（內容為 LF 正規化文字；只有兩份帳本需要內容）。事件帳本只准尾端追加（舊內容為新內容的
    前綴）；OBS 帳本見 `_obs_problem`；該 PROP 的提案目錄只准新增檔。合規回 None，否則回一句違規
    描述。"""
    pdir = f"{si_events.PROPOSALS_REL}/{prop}/"
    for path, status, old, new in changes:
        if path in _LEDGERS:
            name = "事件帳本" if path == si_events.LEDGER_REL else "OBS 帳本"
            if status not in ("A", "M") or (status == "M" and (old is None or new is None)):
                return f"{name}被刪除或無法比對"
            if status == "M" and path == si_events.LEDGER_REL and not new.startswith(old):
                return "事件帳本既有內容被改動（只准尾端追加）"
            problem = _obs_problem(old, new) if status == "M" and path == _LEDGERS[1] else None
            if problem:
                return problem
        elif path.startswith(pdir) and status != "A":
            what = "刪除" if status == "D" else "修改"
            return f"提案檔 {path[len(pdir):]} 被{what}（只准新增檔）"
    return None


def rule_problem(git: Git, repo: Path, prop: str, changes) -> str | None:
    """`_commit` 用：對「將要提交的差分」（HEAD 內容 vs 工作樹內容）跑 `ledger_rule_problems`；
    `changes`＝`pending` 回的（路徑, 狀態）清單。"""
    rows = []
    for path, status in changes:
        old = new = None
        if path in _LEDGERS:
            head = git.show("HEAD", path) if status != "A" else None
            old = None if head is None else _norm(head.encode("utf-8"))
            try:
                new = _norm((repo / path).read_bytes()) if status != "D" else None
            except OSError:
                new = None
        rows.append((path, status, old, new))
    return ledger_rule_problems(prop, rows)


# ── 守門 ──────────────────────────────────────────────────────────────────────────────
def _t(value) -> datetime | None:
    try:
        out = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return out if out.tzinfo is not None else None


def _read_json(path: Path) -> dict | None:
    try:
        obj = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def _running(cur: dict | None, now: datetime, alive) -> bool:
    """`push/current.json` 存在、牆鐘未到，且（有注入時）行程存活；欄位缺損視為沒在推。"""
    wall = _t(cur.get("wall_due_at")) if cur else None
    if wall is None or now >= wall:
        return False
    try:
        return alive is None or bool(alive(cur["pid"], cur["started_at"]))
    except (KeyError, TypeError, ValueError):
        return False


def running(si: Path, now: datetime, alive) -> bool:
    """推送工作是否存活（`push/current.json` 牆鐘未到且行程存活）；巡邏器據以記
    `PUSH-IN-PROGRESS`。"""
    return _running(_read_json(si / "push" / "current.json"), now, alive)


# ── 結果分類、遮罩與重試判準（AC-SI-49-7、49-8；純函式，`patrolpush` 與守門共用）────────
HOOK_MARK = "[pre-push dispatcher]"
NEVER_RETRY = ("PUSH-HOOK-FAILED", "PUSH-REJECTED", "PUSH-AUTH")
RETRYABLE = ("PUSH-WALL-EXCEEDED", "PUSH-FAILED")
TEXT_MAX = 160
_AUTH_RE = re.compile(r"Authentication failed|could not read Username|terminal prompts disabled"
                      r"|Permission denied \(publickey\)|returned error: 40[13]", re.I)
_REJECT_RE = re.compile(r"! \[(?:remote )?rejected\]|non-fast-forward|fetch first"
                        r"|Updates were rejected|protected branch", re.I)
_NET_RE = re.compile(r"Could not resolve host|Connection (?:timed out|refused)|unable to access"
                     r"|early EOF|RPC failed", re.I)
_MASKS = ((re.compile(r"://[^/\s]*@"), "://***@"),
          (re.compile(r"(?i)\b(token|password|passwd|secret|key)(\s*[=:]\s*)\S+"), r"\1\2***"),
          (re.compile(r"(?i)\b(bearer)\s+\S+"), r"\1 ***"))
_WAIT_TEXT = {"PUSH-RETRY-WAIT": "上一次推送失敗，還沒到重試時間",
              "PUSH-ATTEMPTS-EXHAUSTED": "同一個提交的自動推送次數已用盡，請由人推送"}


def classify(rc, timed_out: bool, output: str) -> str:
    """`git push` 結果碼：先 timed_out、再 rc 0、再看 hook 標記後的尾段（hook 日誌內的認證／網路字樣
    不得誤判，R-13），無標記則對全部輸出依 AUTH→REJECTED→網路→其餘判。"""
    if timed_out:
        return "PUSH-WALL-EXCEEDED"
    if rc == 0:
        return "PUSH-OK"
    text = output or ""
    cut = text.rfind(HOOK_MARK)
    hooked = cut >= 0
    if hooked:
        text = text[text.index("\n", cut) + 1:] if "\n" in text[cut:] else ""
    for rx, code in ((_AUTH_RE, "PUSH-AUTH"), (_REJECT_RE, "PUSH-REJECTED")):
        if rx.search(text):
            return code
    if _NET_RE.search(text) or not hooked:
        return "PUSH-FAILED"
    return "PUSH-HOOK-FAILED"


def mask(text: str) -> str:
    """URL userinfo 整段、`token|password|secret|key` 之值、Bearer 值遮為 `***`。"""
    for rx, repl in _MASKS:
        text = rx.sub(repl, text)
    return text


def last_line(output: str, limit: int = TEXT_MAX) -> str:
    """輸出最後一個非空行（遮罩後、≤`limit` 字元）；全空＝空字串。"""
    rows = [ln.strip() for ln in (output or "").splitlines() if ln.strip()]
    return mask(rows[-1])[:limit] if rows else ""


def result_of(si: Path, sha: str) -> dict | None:
    """`<si>/push/results/<sha12>.json`（該 sha 最近一次推送結果）；缺檔或損壞＝None。"""
    return _read_json(si / "push" / "results" / f"{sha[:12]}.json")


def retry_verdict(prev: dict | None, params: dict, now: datetime) -> str | None:
    """同 sha 已有失敗結果時：不可重試碼或次數用盡＝`PUSH-ATTEMPTS-EXHAUSTED`；可重試碼未到間隔＝
    `PUSH-RETRY-WAIT`；其餘（無結果、已成功、可重試）＝None。"""
    code = (prev or {}).get("code")
    if code in NEVER_RETRY:
        return "PUSH-ATTEMPTS-EXHAUSTED"
    if code not in RETRYABLE:
        return None
    if int(prev.get("attempts") or 0) >= params["sched_push_attempts_max"]:
        return "PUSH-ATTEMPTS-EXHAUSTED"
    fin = _t(prev.get("finished_at"))
    gap = timedelta(minutes=params["sched_push_retry_minutes"])
    return "PUSH-RETRY-WAIT" if fin is not None and now - fin < gap else None


def parse_trailers(message: str) -> tuple[str, str] | None:
    """末段（最後一個空行之後）恰為 `SI-Patrol-App`、`SI-Patrol-Prop` 兩個 trailer 行才回
    （APP, PROP）；首段（標題）本身不算 trailer 區；其餘（缺、多、重複、夾在本文中段）一律 None。"""
    paras = _PARA_RE.split(message.strip("\n"))
    if len(paras) < 2:
        return None
    got = [_TRAILER_RE.match(ln) for ln in paras[-1].split("\n")]
    if len(got) != 2 or not all(got):
        return None
    pairs = {m.group(1): m.group(2).strip() for m in got}
    if set(pairs) != {TRAILER_APP, TRAILER_PROP}:
        return None
    app, prop = pairs[TRAILER_APP], pairs[TRAILER_PROP]
    if not evspec.APP_RE.match(app) or not si_events.PROP_RE.match(prop):
        return None
    return app, prop


def _records(si: Path) -> dict[str, list[dict]]:
    """`<si>/push/commits.jsonl`：sha→紀錄清單（依檔內順序）；缺檔、損壞行、非物件不算紀錄。"""
    out: dict[str, list[dict]] = {}
    try:
        raw = (si / "push" / "commits.jsonl").read_bytes().decode("utf-8", "replace")
    except OSError:
        return out
    for ln in raw.split("\n"):
        try:
            rec = json.loads(ln)
        except ValueError:
            continue
        if isinstance(rec, dict) and isinstance(rec.get("sha"), str):
            out.setdefault(rec["sha"], []).append(rec)
    return out


def _app_line(line: str, app_ev: dict) -> bool:
    try:
        obj = json.loads(line)
    except ValueError:
        return False
    return (isinstance(obj, dict) and obj.get("id") == app_ev.get("id")
            and obj.get("kind") == app_ev["kind"])


class _Judge:
    """單次 `evaluate` 的 git 讀取面（帶總牆鐘預算）與逐提交判準。"""

    def __init__(self, repo: Path, si: Path, events: list[dict]) -> None:
        self.g, self.si, self.events = Git(repo), si, events
        self.t0, self.records = time.monotonic(), _records(si)
        self.seen: set[str] = set()

    def run(self, *args: str):
        if time.monotonic() - self.t0 > TOTAL_BUDGET:
            raise _GitFail
        cp = self.g.run(*args, timeout=CALL_TIMEOUT)
        if cp is None:
            raise _GitFail
        return cp

    def maybe_blob(self, rev: str, path: str) -> str | None:
        cp = self.run("show", f"{rev}:{path}")
        return None if cp.returncode != 0 else _norm(cp.stdout.encode("utf-8"))

    def blob(self, rev: str, path: str) -> str:
        text = self.maybe_blob(rev, path)
        if text is None:
            raise _GitFail
        return text

    def diff(self, sha: str, parents: list[str]) -> list[tuple[str, str]]:
        root = () if parents else ("--root",)
        cp = self.run("-c", "core.quotepath=false", "diff-tree", "--no-commit-id",
                      "--name-status", "-r", "-z", "--no-renames", *root, sha)
        if cp.returncode != 0:
            raise _GitFail
        toks = cp.stdout.split("\0")
        return [(toks[i + 1], toks[i]) for i in range(0, len(toks) - 1, 2) if toks[i]]

    def remote_has(self, app: str) -> bool:
        cp = self.run("log", REMOTE, "-n", "1", "--format=%H", "-F",
                      f"--grep={TRAILER_APP}: {app}")
        if cp.returncode != 0:
            raise _GitFail
        return bool(cp.stdout.strip())

    def judge(self, sha: str, parents: list[str]) -> tuple[str, str] | None:
        """一個提交的第一個不符（碼, 卡在哪的片段）；None＝合。片段依 TCS-P7 E-9：路徑、規則描述、
        APP id＋kind、APP id；整個提交即單位的碼（FOREIGN／NOT-RECORDED／RECORD-MISMATCH）為空。"""
        msg = self.run("show", "-s", "--format=%B", sha)
        if msg.returncode != 0:
            raise _GitFail
        tr = None if len(parents) > 1 else parse_trailers(msg.stdout)
        app_ev = None if tr is None else next(
            (e for e in self.events if e["kind"].startswith("app.") and e.get("id") == tr[0]),
            None)
        if tr is None or app_ev is None or app_ev.get("prop") != tr[1]:
            return "PUSH-FOREIGN-COMMITS", ""
        app, prop = tr
        recs = self.records.get(sha)
        if not recs:
            return "PUSH-NOT-RECORDED", ""
        if (recs[-1].get("app"), recs[-1].get("prop")) != (app, prop):
            return "PUSH-RECORD-MISMATCH", ""
        if app_ev["kind"] not in _KINDS:
            return "PUSH-APP-KIND-INVALID", f"{app} {app_ev['kind']}"
        reused = app in self.seen or self.remote_has(app)
        self.seen.add(app)
        if reused:
            return "PUSH-APP-REUSED", app
        changes = self.diff(sha, parents)
        pev = next((e for e in reversed(self.events) if e["kind"] == "prop" and e["id"] == prop
                    and e.get("rev") == app_ev.get("rev")), None)
        if pev is None:
            return "PUSH-FOREIGN-COMMITS", ""
        patch = self.blob(sha, f"{si_events.PROPOSALS_REL}/{prop}/r{pev['rev']}.patch")
        touched = si_paths.touched_of(patch.encode("utf-8"))
        allow = commit_allow(prop, touched, pev.get("cls", ""))
        outside = next((path for path, _ in changes if not covered(path, allow)), None)
        if outside is not None:
            return "PUSH-PATH-OUTSIDE", outside
        rows = []
        for path, status in changes:
            old = new = None
            if path in _LEDGERS:
                old = self.maybe_blob(parents[0], path) if parents and status != "A" else None
                new = self.blob(sha, path) if status != "D" else None
            rows.append((path, status, old, new))
        broken = ledger_rule_problems(prop, rows)
        if broken:
            return "PUSH-LEDGER-RULE", broken
        why = self.content_problem(sha, app_ev, pev, touched, rows)
        return ("PUSH-CONTENT-MISMATCH", why) if why else None

    def content_problem(self, sha: str, app_ev: dict, pev: dict, touched: list[str],
                        rows) -> str | None:
        """內容綁定（vi）：事件帳本新增了該 APP 的事件行；P 類另須 touched 的 manifest 等於
        `post_sha256`。合規回 None，否則回固定二句之一（TCS-P7 附錄 A.4b）。"""
        led = next((r for r in rows if r[0] == si_events.LEDGER_REL), None)
        if led is None or led[3] is None or not any(
                _app_line(ln, app_ev) for ln in led[3][len(led[2] or ""):].split("\n")):
            return "事件帳本沒有該 APP 的事件行"
        if pev.get("cls") == "M":
            return None
        pairs = []
        for rel in touched:
            text = self.maybe_blob(sha, rel)
            pairs.append((rel, "absent" if text is None
                          else hashlib.sha256(text.encode("utf-8")).hexdigest()))
        same = manifest._digest(pairs) == app_ev.get("post_sha256")  # noqa: SLF001  # 同一個公式
        return None if same else "觸及檔內容與 post_sha256 不符"


def _result(code: str | None, detail=None, *, ahead: int = 0, head: str | None = None) -> dict:
    """守門結果（`ok` 只在 `code is None`）；`text`＝經 `nextstep.reason` 的白話。"""
    text = _WAIT_TEXT.get(code) or (nextstep.reason(code, detail).text if code else "")
    return {"ok": code is None, "code": code, "detail": detail, "text": text, "ahead": ahead,
            "head": head, "sha": head if code is None else None}


def evaluate(repo: Path, params: dict, si: Path, now: datetime, *, alive=None,
             events: list[dict] | None = None, gate_retry: bool = False) -> dict:
    """每心跳一次的守門：回 `{ok, code, detail, text, ahead, head, sha}`（放行＝`ok` 真且 `sha`＝
    HEAD 全 40 碼）。`alive(pid, started_at)` 注入（缺省＝只看 `current.json` 的牆鐘是否未到）；
    `now` 須帶 offset（缺＝`ValueError`）；其餘一切失敗都不拋例外。`gate_retry`（只有 `push-run`
    傳真）另依同 sha 的結果檔判 `PUSH-ATTEMPTS-EXHAUSTED`／`PUSH-RETRY-WAIT`；快照的呼叫不傳，
    這兩碼是 push-run 的輸出碼、不單獨成快照態（附錄 A.4）。"""
    sched.aware(now)
    if params.get("sched_auto_push") is not True:
        return _result("PUSH-OFF")
    ahead, head = 0, None
    try:
        loaded = events if events is not None else (
            si_events.load_sound_events(repo / si_events.LEDGER_REL) or [])
        j = _Judge(repo, si, loaded)
        if not j.g.available:
            raise _GitFail
        head = j.g.head()
        cp = j.run("rev-list", "--count", f"{REMOTE}..HEAD")
        ahead = int(cp.stdout.strip()) if cp.returncode == 0 and cp.stdout.strip().isdigit() else 0
        branch = j.run("symbolic-ref", "--short", "-q", "HEAD")
        upstream = j.run("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        if (branch.stdout.strip(), upstream.stdout.strip()) != ("main", REMOTE):
            return _result("PUSH-NOT-MAIN", ahead=ahead, head=head)
        if head is None or cp.returncode != 0:
            raise _GitFail
        if ahead == 0:
            return _result("PUSH-NOT-AHEAD", head=head)
        if _running(_read_json(si / "push" / "current.json"), now, alive):
            return _result("PUSH-RUNNING", ahead=ahead, head=head)
        if sched.dirty_paths(repo):
            return _result("PUSH-DIRTY-TREE", ahead=ahead, head=head)
        lines = j.run("rev-list", "--reverse", "--parents", f"{REMOTE}..HEAD")
        if lines.returncode != 0:
            raise _GitFail
        for ln in lines.stdout.split("\n"):
            parts = ln.split()
            if parts and (hit := j.judge(parts[0], parts[1:])):
                detail = f"{parts[0][:8]} {hit[1]}".strip()  # sha8＋卡在哪（TCS-P7 E-9）
                return _result(hit[0], detail, ahead=ahead, head=head)
    except (_GitFail, OSError, ValueError, TypeError, KeyError):
        return _result("PUSH-GIT-UNAVAILABLE", ahead=ahead, head=head)
    wait = retry_verdict(result_of(si, head), params, now) if gate_retry else None
    return _result(wait, ahead=ahead, head=head)


__all__ = ["CALL_TIMEOUT", "TOTAL_BUDGET", "TRAILER_APP", "TRAILER_PROP", "si_own_allow",
           "commit_allow", "commit_message", "covered", "pending", "ledger_rule_problems",
           "rule_problem", "parse_trailers", "evaluate", "running", "classify", "mask",
           "last_line", "result_of", "retry_verdict", "NEVER_RETRY", "RETRYABLE", "HOOK_MARK"]
