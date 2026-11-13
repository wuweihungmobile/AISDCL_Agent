"""SelfImproving 推送守門的「內容與設定」判準（TCS-SelfImproving-P7 AC-SI-49-2～49-5；自
`pushguard` 拆出以守 LOC 分級，行為不變）。

能力類別 `ro`：只讀 git、事件帳本與 `<si>/push/`，不寫任何檔。兩件事的**單一來源**：
①「這份差分合不合帳本規則、檔案模式、大小與機密樣式」`content_problems`（`patrolrun._commit`
經 `rule_problem`、`evaluate` 經 `_Judge.judge`，全套件沒有第二份實作）；②「本機 git 設定與
遠端位置能不能放行」`config_problem`。
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import sys
from collections import Counter
from pathlib import Path

from . import check as si_check
from . import events as si_events
from . import git as si_git
from . import rows as ledger_rows
from .git import ENV_RULES, Git, config_rule_hit, scan_names
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
CODE_PROPOSAL = "PUSH-PROPOSAL-MISMATCH"  # 提案目錄新檔內容與帳本雜湊不符（E-30）
CODE_CONFIG = "PUSH-GIT-CONFIG-UNSAFE"  # 本機 git 設定含不允許的鍵（審查 F-04）
_LOCAL_SCOPES = si_git.LOCAL_LAYERS
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
    # 被改動的既有列（處置欄由 open 轉終值）也要過同一套列驗證，違反詞表＝處置欄不合（E-31）
    changed = {b.subject: b.lineno for a, b in zip(parse_ledger(old).rows, led.rows[:first],
                                                   strict=False) if a.raw != b.raw}
    fresh.update(changed)
    for f in structure_findings(led):  # 欄數、ID 形、重複與遞增（與 `check` 的結構判準同一函式）
        if f.level == "fail" and f.subject in fresh:
            return f"OBS 帳本 第 {fresh[f.subject]} 行 {f.code}"
    for item, found in ledger_rows.evaluate_rows(led, row_max).items():
        for f in found:
            if f.level == "fail" and f.subject in fresh:
                where = f"{f.subject} 處置欄" if f.subject in changed else ""
                text = f"OBS 帳本 第 {fresh[f.subject]} 行 {where} {item} {f.code}"
                return text.replace("  ", " ")
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
    """這次提交「新增」的文字（供機密掃描）：事件帳本只取追加的部分；OBS 帳本取新增列加「被改動的
    既有列」（處置欄也要掃，E-31）；既有檔的修改只取新增的行；其他檔取全文。"""
    if path == si_events.LEDGER_REL and new is not None:
        return new[len(old or ""):]
    if path == _LEDGERS[1] and new is not None:
        before, after = parse_ledger(old or "").rows, parse_ledger(new).rows
        changed = [b.raw for a, b in zip(before, after, strict=False) if a.raw != b.raw]
        return "\n".join([*changed, *(r.raw for r in after[len(before):])])
    if old is not None and new is not None:  # 既有檔的修改：只掃新增的行（舊行有同樣字樣不算）
        left, fresh = Counter(old.split("\n")), []
        for line in new.split("\n"):
            if left[line] > 0:
                left[line] -= 1
            else:
                fresh.append(line)
        return "\n".join(fresh)
    return (raw or b"").decode("utf-8", "replace")


def events_of(text: str | None) -> list[dict]:
    """事件帳本文字中解得出的事件物件（壞行略過；內容規則已另判格式）。"""
    if not text:
        return []
    return [ln.obj for ln in si_events.read_lines(text.encode("utf-8")) if ln.obj is not None]


def _sha(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _proposal_problem(prop: str, items, events) -> str | None:
    """提案目錄每個**新增**檔的位元組雜湊必須等於帳本事件記的值（E-30）：`r<N>.patch`＝`rev==N` 的
    `prop` 事件 `patch_sha256`、`r<N>.md`（CRLF 先正規化）＝`body_sha256`、`verify<N>.json`＝該 PROP
    第 N 筆 `app.verify` 的 `verify_sha256`。回 `<檔名> no-event` 或 `<檔名> sha-mismatch`。"""
    pdir = f"{si_events.PROPOSALS_REL}/{prop}/"
    props = [e for e in events if e.get("kind") == "prop" and e.get("id") == prop]
    verifies = [e for e in events if e.get("kind") == "app.verify" and e.get("prop") == prop]
    for path, status, *_mid, raw in items:
        if status != "A" or not path.startswith(pdir):
            continue
        name = path[len(pdir):]
        m = re.fullmatch(r"r(\d+)\.(patch|md)", name)
        v = re.fullmatch(r"verify(\d+)\.json", name)
        if m:
            ev = next((e for e in props if e.get("rev") == int(m.group(1))), None)
            want = (ev or {}).get("patch_sha256" if m.group(2) == "patch" else "body_sha256")
        elif v:
            k = int(v.group(1))
            ev = verifies[k - 1] if 1 <= k <= len(verifies) else None
            want = (ev or {}).get("verify_sha256")
        else:
            continue  # 檔名不合另由帳本規則擋下
        if ev is None or want is None:
            return f"{name} no-event"
        data = raw or b""
        if m and m.group(2) == "md":
            data = data.replace(b"\r\n", b"\n")
        if _sha(data) != want:
            return f"{name} sha-mismatch"
    return None


def mode_verdict(status: str, old_mode: str | None, new_mode: str | None) -> bool:
    """檔案模式的**單一判準**（`rule_problem` 與 `judge` 共用；E-36）：`D` 恆合；新模式須 `100644`；
    唯一例外＝`M` 且舊新模式皆 `100755`（既有可執行檔只改內容）。"""
    if status == "D" or new_mode == "100644":
        return True
    return status == "M" and old_mode == new_mode == "100755"


def content_problems(prop: str, items, row_max=None, events=None) -> tuple[str, str] | None:
    """內容規則的**單一函式**（`_commit`（經 `rule_problem`）與守門 `judge` 共用；TCS-P7 E-20）：
    `items`＝[(路徑, 狀態, 新模式, 模式合規, 舊內容或 None, 新內容或 None, 新位元組或 None)]（帳本的
    內容為 LF 正規化文字；「模式合規」由呼叫端以 `mode_verdict` 算好——兩個呼叫端各自取得舊模式的
    方式不同，判準本身只有一份）；`events`＝該提交的事件帳本事件。依序判：檔案模式
    （`PUSH-FILE-MODE-INVALID`，描述 `<路徑> <新模式>`）→帳本與提案目錄規則（`PUSH-LEDGER-RULE`）
    →提案檔雜湊綁定（`PUSH-PROPOSAL-MISMATCH`）→所有非刪除路徑須可 UTF-8 解碼且無 NUL、新增內容
    不含機密樣式（`PUSH-SECRET-PATTERN`，描述 `<路徑> <樣式名>`、不含值）。回（碼, 描述）。"""
    for path, _status, nmode, mode_ok, *_rest in items:  # `mode_ok`＝呼叫端以 `mode_verdict` 算好
        if not mode_ok:
            return CODE_MODE, f"{path} {nmode}"
    changes = [(p, s, o, n) for p, s, _m, _ok, o, n, _r in items]
    broken = ledger_rule_problems(prop, changes, row_max)
    if broken:
        return "PUSH-LEDGER-RULE", broken
    pdir = f"{si_events.PROPOSALS_REL}/{prop}/"
    for path, status, *_mid, raw in items:
        if status != "D" and path.startswith(pdir) and len(raw or b"") > PROPOSAL_FILE_MAX_BYTES:
            return "PUSH-LEDGER-RULE", f"提案檔 {path[len(pdir):]} 超過大小上限"
    bound = _proposal_problem(prop, items, events or [])
    if bound:
        return CODE_PROPOSAL, bound
    for path, status, _nm, _om, old, new, raw in items:
        if status == "D":
            continue
        if raw is None or b"\x00" in raw:  # 讀不到、二進位：fail-closed（含 touched，E-31）
            return CODE_SECRET, f"{path} undecodable"
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            return CODE_SECRET, f"{path} undecodable"
        names = scan_names(added_text(path, old, new, raw))
        if names:
            return CODE_SECRET, f"{path} {names[0]}"
    return None


_lstat = os.lstat  # 測試縫：符號連結判準在 Windows 也要能被驗（E-41）
_REPARSE = 0x400  # FILE_ATTRIBUTE_REPARSE_POINT


def _wt_mode(path: Path, old_mode: str | None = None) -> str | None:
    """工作樹檔的 git 模式：符號連結（`S_ISLNK`，Windows 另判 reparse point）120000、目錄（子模組）
    160000；常規檔 POSIX 取 `st_mode&0o111`，Windows 沒有可執行位、取 HEAD 的舊模式（無則 100644）；
    不存在＝None。"""
    try:
        st = _lstat(str(path))
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(st.st_mode) or getattr(st, "st_file_attributes", 0) & _REPARSE:
        return "120000"
    if stat.S_ISDIR(st.st_mode):
        return "160000"
    if sys.platform == "win32":
        return old_mode or "100644"
    return "100755" if st.st_mode & 0o111 else "100644"


def _head_mode(git: Git, path: str) -> str | None:
    """HEAD 樹中該路徑的模式（`git ls-tree HEAD -- <path>`）；沒有＝None。"""
    cp = git.run("ls-tree", "HEAD", "--", path)
    ok = cp is not None and cp.returncode == 0 and cp.stdout
    first = cp.stdout.split(None, 1)[0] if ok else ""
    return first if re.fullmatch(r"\d{6}", first) else None


def rule_problem(git: Git, repo: Path, prop: str, changes) -> str | None:
    """`_commit` 用：對「將要提交的差分」（HEAD 內容 vs 工作樹內容）跑 `content_problems`；
    `changes`＝`pending` 回的（路徑, 狀態）清單。回第一句違規描述。"""
    items, events = [], []
    for path, status in changes:
        old = new = raw = None
        try:
            raw = (repo / path).read_bytes() if status != "D" and (repo / path).is_file() else None
        except OSError:
            raw = None
        omode = None if status == "A" else _head_mode(git, path)
        if path in _LEDGERS or (status == "M" and raw is not None):
            head = git.show("HEAD", path) if status != "A" else None
            old = None if head is None else _norm(head.encode("utf-8"))
            new = None if raw is None else _norm(raw)
        if path == si_events.LEDGER_REL:
            events = events_of(new)
        nmode = _wt_mode(repo / path, omode)
        items.append((path, status, nmode, mode_verdict(status, omode, nmode), old, new, raw))
    if not events:  # 本次沒有動事件帳本：事件取工作樹現況
        try:
            events = events_of((repo / si_events.LEDGER_REL).read_text(encoding="utf-8"))
        except OSError:
            events = []
    hit = content_problems(prop, items, events=events)
    return hit[1] if hit else None


def _norm_hooks(path: str) -> str:
    out = path.strip().replace("\\", "/")
    while out.startswith("./"):
        out = out[2:]
    return out.rstrip("/")


def _same_dir(configured: str, expected: Path) -> bool:
    """絕對路徑的 `core.hooksPath` 與既定 hooks 目錄是不是同一個實體目錄（經符號連結正規化後
    相等；macOS 的 `/var`→`/private/var`、使用者把 repo 放在符號連結路徑下都屬此類）。相對路徑與
    解析失敗一律不等。"""
    text = configured.strip()
    if re.match(r"^[\\/]{2}\?[\\/][A-Za-z]:", text):  # Windows 擴充長度前綴 `\\?\C:\…`（不含 UNC）
        text = text[4:]
    path = Path(text)
    if not path.is_absolute():
        return False
    try:
        return path.resolve() == expected.resolve()
    except OSError:
        return False


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


parse_config_list = si_git.parse_config_list  # 單一家在 git.py（`sched arm` 與守門共用）


CODE_REPO_STATE = "PUSH-REPO-STATE-UNSAFE"  # 物件庫狀態會改變守門所見內容（E-53）


def repo_state_problem(j) -> tuple[str, str] | None:
    """repo 狀態檢查（E-53、E-56、E-65；在設定檢查之後、任何 `rev-list`／`show`／`cat-file` 之前，
    送出推送前再跑一次）：`refs/replace/` 非空、`info/grafts` 存在、`shallow` 存在、
    `info/attributes` 含 `filter=`、hooks 目錄有被隱藏的已追蹤檔或未追蹤檔任一 ⇒（碼,
    `refs/replace`／`info/grafts`／`shallow`／`info/attributes`／`hooks`）；git 讀取失敗拋
    `OSError`（呼叫端 fail-closed）。"""
    cp = j.run("for-each-ref", "--format=%(refname)", "refs/replace/")
    if cp.returncode != 0:
        raise OSError("for-each-ref 失敗")
    if cp.stdout.strip():
        return CODE_REPO_STATE, "refs/replace"
    # 一次 spawn。grafts 位置由共用目錄自己拼：`--git-path info/grafts` 會被子行程環境的
    # `GIT_GRAFT_FILE`（固定指向不存在的路徑，E-66）改寫成那個路徑、永遠偵測不到
    gp = j.run("rev-parse", "--git-common-dir", "--git-path", "shallow",
               "--git-path", "info/attributes")
    rels = gp.stdout.splitlines()
    if gp.returncode != 0 or len(rels) != 3 or not all(r.strip() for r in rels):
        raise OSError("rev-parse --git-path 失敗")
    for rel, found in (("info/grafts", f"{rels[0].strip()}/info/grafts"), ("shallow", rels[1])):
        if (j.g.repo / found.strip()).exists():
            return CODE_REPO_STATE, rel
    attr = j.g.repo / rels[2].strip()
    try:
        lines = attr.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        lines = []
    if any(re.search(r"(?:^|\s)filter=", ln) for ln in lines if not ln.lstrip().startswith("#")):
        return CODE_REPO_STATE, "info/attributes"
    # hooks 目錄（E-65）：一次 `ls-files -v`——被標 skip-worktree（S）或 assume-unchanged（小寫）的已
    # 追蹤檔、或目錄內任何未追蹤檔（?，含被忽略者）＝工作樹上的 hook 內容可能與 HEAD 不同
    hl = j.run("ls-files", "-v", "-c", "-o", "--", si_git.EXPECTED_HOOKS)
    if hl.returncode != 0:
        raise OSError("ls-files 失敗")
    for ln in hl.stdout.splitlines():
        if ln[:1] and (ln[0] in "S?" or ln[0].islower()):
            return CODE_REPO_STATE, "hooks"
    return None


def config_problem(j, armed_doc: dict | None, env=None) -> tuple[str, str] | None:
    """推送前的 git 設定與遠端網址檢查（審查 F-04；E-29）：行程環境含 `GIT_CONFIG_*` 注入、任一層
    （system／global／local／worktree／command，含 `--includes` 展開）的設定依 `git.CONFIG_RULES`
    不合、或遠端網址與 `sched arm` 記錄（`push/armed.json`）不同，一律不放行。詳述不含值，只列鍵名
    （子區段以 `*`）、`env:<變數名>` 或主機名。設定檢查那一次不帶任何 `-c` 覆寫。"""
    for name in sorted(os.environ if env is None else env):
        if ENV_RULES.match(name):
            return CODE_CONFIG, f"env:{name}"
    cp = j.run_plain("config", "--list", "--show-scope", "--includes", "-z")
    if cp is None or cp.returncode not in (0, 1):
        raise OSError("git config 讀取失敗")
    bad, hooks = [], []
    entries = parse_config_list(cp.stdout)
    bad += si_git.recorded_problems(entries, armed_doc)  # 乙類鍵：現值須等於 arm 時記錄
    for scope, key, val in entries:
        if key == "core.hookspath" and scope in _LOCAL_SCOPES:
            hooks.append(_norm_hooks(val))
        elif (shown := config_rule_hit(scope, key, val)) is not None:
            bad.append(shown)
    want = _norm_hooks(si_git.EXPECTED_HOOKS)
    absolute = _norm_hooks(str(j.g.repo / si_git.EXPECTED_HOOKS))  # 安裝腳本寫的是絕對路徑
    if len(hooks) != 1 or not (hooks[0].lower() in (want.lower(), absolute.lower())
                               or _same_dir(hooks[0], j.g.repo / si_git.EXPECTED_HOOKS)):
        bad.append("core.hookspath")  # 不存在、重複或不等於既定目錄，一律不合
    if bad:
        return CODE_CONFIG, " ".join(sorted(set(bad))[:3])
    url = j.run_plain("config", "--get", "remote.origin.url")
    now_url = url.stdout.strip() if url is not None and url.returncode == 0 else ""
    armed = (armed_doc or {}).get("remote_url")
    if not isinstance(armed, str) or _norm_url(armed) != _norm_url(now_url):
        old = _host_of(armed) if isinstance(armed, str) else "未記錄"
        return CODE_URL, f"{old} {_host_of(now_url)}"
    return None
