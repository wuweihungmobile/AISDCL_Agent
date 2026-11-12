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
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from . import events as si_events
from . import evspec, manifest, nextstep, pushcontent, sched
from . import paths as si_paths
from .git import PIN_ARGS, SECRET_PATTERNS, Git, armed_pins, mask, resolve_git  # 單一實作住 git.py
from .pushcontent import (  # noqa: F401  # 內容判準自 pushcontent 拆出，對外名稱不變
    _KINDS,
    _LEDGERS,
    CODE_CONFIG,
    CODE_DIVERGED,
    CODE_MODE,
    CODE_PROPOSAL,
    CODE_SECRET,
    CODE_URL,
    PROPOSAL_FILE_MAX_BYTES,
    _norm,
    added_text,
    content_problems,
    events_of,
    ledger_rule_problems,
    mode_verdict,
    rule_problem,
)

CALL_TIMEOUT = 20  # 單一 git 呼叫的牆鐘上限（秒）
TOTAL_BUDGET = 60  # 一次 `evaluate` 的總牆鐘上限（秒；不拖慢心跳）
TRAILER_APP, TRAILER_PROP = "SI-Patrol-App", "SI-Patrol-Prop"
REMOTE = "refs/remotes/origin/main"  # 完整名稱（`origin/main` 會被同名 tag／分支搶先解析）
BRANCH_REF = "refs/heads/main"
CODE_REMOTE_DRIFT = "PUSH-REMOTE-DRIFT"  # 遠端 main 與守門固定的追蹤參照不同（審查 F-01）
CODE_HEAD_MOVED = "PUSH-HEAD-MOVED"  # 判定之後 HEAD 或分支被移動（審查 F-02）
_TRAILER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*): (\S.*)$")
_PARA_RE = re.compile(r"\n[ \t]*\n")
#: 寫 `push/blocked.json` 的碼（網路前置與提案雜湊不符之外的守門碼不在此；E-45：全套件單一來源）
BLOCK_CODES = ("PUSH-REMOTE-DRIFT", "PUSH-REMOTE-DIVERGED", "PUSH-PROPOSAL-MISMATCH")
RECORD_SLACK_SECONDS = 600  # 判活窗口＝記錄自己的牆鐘長度加這個寬限（E-34）


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
        return alive is None or bool(alive(cur["pid"], cur["started_at"],
                                           cur.get("process_started_utc"),
                                           record_window(cur["started_at"], cur["wall_due_at"])))
    except (KeyError, TypeError, ValueError):
        return False


def record_window(started_at, wall_due_at) -> float | None:
    """記錄自己的牆鐘長度加 `RECORD_SLACK_SECONDS`＝無建立時間時的判活窗口上界（秒）；兩個時刻有
    一個不是帶 offset 的 ISO＝None（呼叫端據此得到 `unverified`，不寫死任何窗口；E-34）。"""
    a, b = _t(started_at), _t(wall_due_at)
    return None if a is None or b is None else (b - a).total_seconds() + RECORD_SLACK_SECONDS


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
_REJECT_RE = re.compile(r"! \[(?:remote )?rejected\]|non-fast-forward|fetch first|stale info"
                        r"|Updates were rejected|protected branch", re.I)
_NET_RE = re.compile(r"Could not resolve host|Connection (?:timed out|refused)|unable to access"
                     r"|early EOF|RPC failed", re.I)
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
    # 恰兩行且兩把鍵都取得到＝鍵集合恰為這兩把（`.get`：缺鍵一律 None，不拋例外）
    app, prop = pairs.get(TRAILER_APP), pairs.get(TRAILER_PROP)
    if not app or not prop or not evspec.APP_RE.match(app) or not si_events.PROP_RE.match(prop):
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
            and obj.get("kind") == app_ev.get("kind"))


class _Judge:
    """單次 `evaluate` 的 git 讀取面（帶總牆鐘預算）與逐提交判準。"""

    def __init__(self, repo: Path, si: Path, events: list[dict], exe: str | None = None,
                 pin: tuple[str, ...] = ()) -> None:
        """`exe`＝git 絕對路徑、`pin`＝`PIN_ARGS`：除 `run_plain`（設定檢查，不帶任何 `-c`）外，
        每個 git 呼叫都以 `exe` 為 argv[0] 並在子命令之前帶 `pin`（E-29、E-33）。"""
        self.g, self.si, self.events = Git(repo, exe, pin), si, events
        self.plain = Git(repo, exe)
        self.t0, self.records = time.monotonic(), _records(si)
        self.seen: set[str] = set()
        self.base: str | None = None  # `evaluate` 固定下來的追蹤參照 sha（`remote_has` 用）
        self.row_max = None  # `row_max_bytes` 參數（OBS 新列的位元組驗證）

    def run(self, *args: str):
        if time.monotonic() - self.t0 > TOTAL_BUDGET:
            raise _GitFail
        cp = self.g.run(*args, timeout=CALL_TIMEOUT)
        if cp is None:
            raise _GitFail
        return cp

    def run_plain(self, *args: str):
        """設定檢查專用：不帶釘定覆寫（檢查要看見真實設定）；仍受總預算與逾時約束。"""
        if time.monotonic() - self.t0 > TOTAL_BUDGET:
            raise _GitFail
        cp = self.plain.run(*args, timeout=CALL_TIMEOUT)
        if cp is None:
            raise _GitFail
        return cp

    def raw_blob(self, rev: str, path: str) -> bytes | None:
        """`git cat-file blob` 的位元組（不經文字解碼，也不經 textconv；審查 F-08）；
        沒有該物件＝None。"""
        if time.monotonic() - self.t0 > TOTAL_BUDGET:
            raise _GitFail
        cp = self.g.run_bytes("cat-file", "blob", f"{rev}:{path}", timeout=CALL_TIMEOUT)
        if cp is None:
            raise _GitFail
        return None if cp.returncode != 0 else cp.stdout

    def maybe_blob(self, rev: str, path: str) -> str | None:
        raw = self.raw_blob(rev, path)
        return None if raw is None else _norm(raw)

    def blob(self, rev: str, path: str) -> str:
        text = self.maybe_blob(rev, path)
        if text is None:
            raise _GitFail
        return text

    def diff(self, sha: str, parents: list[str]) -> list[tuple[str, str, str, str]]:
        """（路徑, 狀態, 新模式, 舊模式）；`diff-tree --raw -z` 取模式（審查 F-03／F-08）。"""
        root = () if parents else ("--root",)
        cp = self.run("-c", "core.quotepath=false", "diff-tree", "--no-commit-id", "--raw", "-r",
                      "-z", "--no-renames", *root, sha)
        if cp.returncode != 0:
            raise _GitFail
        toks, out, i = cp.stdout.split("\0"), [], 0
        while i < len(toks) - 1:
            if toks[i].startswith(":"):
                m = toks[i][1:].split()
                out.append((toks[i + 1], m[4][0], m[1], m[0]))
                i += 2
            else:
                i += 1
        return out

    def remote_has(self, app: str) -> bool:
        cp = self.run("log", self.base, "-n", "1", "--format=%H", "-F",
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
            (e for e in self.events if str(e.get("kind", "")).startswith("app.")
             and e.get("id") == tr[0]), None)
        if tr is None or app_ev is None or app_ev.get("prop") != tr[1]:
            return "PUSH-FOREIGN-COMMITS", ""
        app, prop = tr
        recs = self.records.get(sha)
        if not recs:
            return "PUSH-NOT-RECORDED", ""
        if (recs[-1].get("app"), recs[-1].get("prop")) != (app, prop):
            return "PUSH-RECORD-MISMATCH", ""
        if app_ev.get("kind") not in _KINDS:
            return "PUSH-APP-KIND-INVALID", f"{app} {app_ev.get('kind')}"
        reused = app in self.seen or self.remote_has(app)
        self.seen.add(app)
        if reused:
            return "PUSH-APP-REUSED", app
        changes = self.diff(sha, parents)
        pev = next((e for e in reversed(self.events) if e.get("kind") == "prop"
                    and e.get("id") == prop and e.get("rev") == app_ev.get("rev")), None)
        if pev is None:
            return "PUSH-FOREIGN-COMMITS", ""
        patch = self.blob(sha, f"{si_events.PROPOSALS_REL}/{prop}/r{pev['rev']}.patch")
        touched = si_paths.touched_of(patch.encode("utf-8"))
        allow = commit_allow(prop, touched, pev.get("cls", ""))
        outside = next((c[0] for c in changes if not covered(c[0], allow)), None)
        if outside is not None:
            return "PUSH-PATH-OUTSIDE", outside
        items = []
        for path, status, nmode, omode in changes:
            keep = mode_verdict(status, omode, nmode)  # 與提交端同一個模式判準（E-36）
            raw = self.raw_blob(sha, path) if status != "D" and keep else None
            old = new = None
            if path in _LEDGERS or (status == "M" and raw is not None):  # 既有檔：掃新增行用
                old = self.maybe_blob(parents[0], path) if parents and status != "A" else None
                new = None if raw is None else _norm(raw)
            items.append((path, status, nmode, keep, old, new, raw))
        rows = [(p, s, o, n) for p, s, _m, _ok, o, n, _r in items]
        hit = content_problems(prop, items, self.row_max,
                               events_of(self.maybe_blob(sha, si_events.LEDGER_REL)))
        if hit:
            return hit
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
        for rel in touched:  # 與 `manifest.paths_manifest(lf=True)` 同規則：位元組、只換 CRLF
            raw = self.raw_blob(sha, rel)
            pairs.append((rel, "absent" if raw is None
                          else hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()))
        same = manifest._digest(pairs) == app_ev.get("post_sha256")  # noqa: SLF001  # 同一個公式
        return None if same else "觸及檔內容與 post_sha256 不符"


def config_recheck(repo: Path, si: Path, exe: str) -> tuple[str, str] | None:
    """送出前的設定再驗（E-29）：同 `evaluate` 的設定檢查；不合回（碼, 說明），讀取失敗回
    `PUSH-GIT-UNAVAILABLE`，合規 None。"""
    try:
        return pushcontent.config_problem(_Judge(repo, si, [], exe),
                                          _read_json(si / "push" / "armed.json"))
    except (_GitFail, OSError):
        return "PUSH-GIT-UNAVAILABLE", "git 設定讀取失敗"


def _result(code: str | None, detail=None, *, ahead: int = 0, head: str | None = None,
            base: str | None = None) -> dict:
    """守門結果（`ok` 只在 `code is None`）；`text`＝經 `nextstep.reason` 的白話。`base`＝判定時
    固定下來的 `refs/remotes/origin/main` 的 sha（推送前據以核對遠端實值）。"""
    text = _WAIT_TEXT.get(code) or (nextstep.reason(code, detail).text if code else "")
    return {"ok": code is None, "code": code, "detail": detail, "text": text, "ahead": ahead,
            "head": head, "sha": head if code is None else None, "base": base}


def _sha_of(cp) -> str | None:
    out = cp.stdout.strip() if cp.returncode == 0 else ""
    return out if re.fullmatch(r"[0-9a-f]{40}", out) else None


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
        exe = resolve_git(os.environ)  # 守門與推送共用同一個絕對路徑（E-33）；解析不到：fail-closed
        if exe is None:
            raise _GitFail
        armed = _read_json(si / "push" / "armed.json")
        recorded = (armed or {}).get("git")  # 沒有 armed.json／沒記 git：交由網址檢查回「未記錄」
        if isinstance(recorded, str) and os.path.normcase(os.path.normpath(recorded)) != \
                os.path.normcase(os.path.normpath(exe)):
            return _result("PUSH-GIT-UNAVAILABLE", "git 路徑與安裝時記錄不同")
        j = _Judge(repo, si, loaded, exe, tuple(PIN_ARGS(repo, armed_pins(armed))))
        j.row_max = params.get("row_max_bytes")
        if (bad := pushcontent.config_problem(j, armed)):  # 設定檢查最先（在任何其他 git 呼叫之前）
            return _result(bad[0], bad[1])
        inside = j.run("rev-parse", "--is-inside-work-tree")  # 與其餘呼叫同走總預算
        if inside.returncode != 0 or inside.stdout.strip() != "true":
            raise _GitFail
        # HEAD 與遠端追蹤參照各只解析一次、固定成 sha；之後所有查詢都用這兩個 sha，不再用符號
        # `HEAD`／`origin/main`（審查 F-01／F-02：符號參照在判定途中被移動，守門就判到別的範圍）
        head = _sha_of(j.run("rev-parse", "HEAD"))
        base = _sha_of(j.run("rev-parse", "--verify", "-q", f"{REMOTE}^{{commit}}"))
        j.base = base
        rng = f"{base}..{head}" if base and head else None
        cp = j.run("rev-list", "--count", rng) if rng else None
        cnt = cp.stdout.strip() if cp and cp.returncode == 0 else ""
        ahead = int(cnt) if cnt.isdigit() else 0
        branch = j.run("symbolic-ref", "-q", "HEAD")  # 完整名稱：tag／同名分支不得頂替
        upstream = j.run("rev-parse", "--symbolic-full-name", "@{u}")
        if base is None or (branch.stdout.strip(), upstream.stdout.strip()) != (BRANCH_REF, REMOTE):
            return _result("PUSH-NOT-MAIN", ahead=ahead, head=head, base=base)
        if head is None or cp is None or cp.returncode != 0:
            raise _GitFail
        if ahead == 0:
            return _result("PUSH-NOT-AHEAD", head=head, base=base)
        if _running(_read_json(si / "push" / "current.json"), now, alive):
            return _result("PUSH-RUNNING", ahead=ahead, head=head, base=base)
        if sched.dirty_paths(repo, j.g):
            return _result("PUSH-DIRTY-TREE", ahead=ahead, head=head, base=base)
        lines = j.run("rev-list", "--reverse", "--parents", rng)
        if lines.returncode != 0:
            raise _GitFail
        for ln in lines.stdout.split("\n"):
            parts = ln.split()
            if parts and (hit := j.judge(parts[0], parts[1:])):
                detail = f"{parts[0][:8]} {hit[1]}".strip()  # sha8＋卡在哪（TCS-P7 E-9）
                return _result(hit[0], detail, ahead=ahead, head=head, base=base)
    except (_GitFail, OSError, ValueError, TypeError, KeyError):
        return _result("PUSH-GIT-UNAVAILABLE", ahead=ahead, head=head)
    wait = retry_verdict(result_of(si, head), params, now) if gate_retry else None
    return _result(wait, ahead=ahead, head=head, base=base)


__all__ = ["CALL_TIMEOUT", "TOTAL_BUDGET", "TRAILER_APP", "TRAILER_PROP", "si_own_allow",
           "commit_allow", "commit_message", "covered", "pending", "ledger_rule_problems",
           "rule_problem", "parse_trailers", "evaluate", "running", "classify", "mask",
           "last_line", "result_of", "retry_verdict", "NEVER_RETRY", "RETRYABLE", "HOOK_MARK",
           "SECRET_PATTERNS"]
