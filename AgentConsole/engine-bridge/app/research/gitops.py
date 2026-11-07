"""git／gh 子行程的**唯一出口**（ADR-003 D16＋D-99、D-128；TCS AC-961-8）。

研究面其餘模組一律不得出現 `git`／`gh` 的 argv 字面（能力登記鎖 `vcs` 類別只有本檔）；要動版控只
准經本檔的 `Gitops.git`／`Gitops.gh`。三道牆，**順序不可換**：

  1. **允許集合（預設拒絕）**：`parse_git`／`parse_gh` 以表驅動逐形態比對 argv，不在表內的一律
     `GitopsDenied`，且**在 spawn 之前**拒絕（子行程啟動計數為 0）。P1 允許集合＝ADR-003 D16 加
     D-99 補列：`status --porcelain`、`rev-parse`、`diff --name-only`、`ls-files`、
     `branch --list`、`worktree list --porcelain`、`-c core.longpaths=true worktree add -b`、
     `init -b main`、`add -A`（僅新專案根）、`add -- <明列路徑…>`（逐路徑 `check_path`、須在
     worktree 內）、`commit -m <模板訊息>`、`remote add origin <url>`、`push -u origin <分支>`；
     gh：`auth status`、`repo create <owner>/<repo> --private|--public --source . --push`。
     P2 動詞（`tag`、`pr create`、`release create`）不在 P1 表內（⚖P1-10）。強推、硬重設、`clean`、
     `stash`、`checkout -- <path>`、`restore <path>`、`switch -f`、全域與系統層 config 皆無對應
     形態，天然被拒（根 `CLAUDE.md` 鐵律五的列舉形態逐項有負控）。
  2. **使用者片段先過列舉或正規式**：分支、基底 ref、庫名、owner、可見性、路徑都在這裡驗，以 `-`
     起頭、含 shell 元字元、空白、控制字元一律拒（選項注入）。
  3. **環境重建**：`BRIDGE_*`、`SDD_*`、`PYTHONPATH`、`GH_TOKEN` 與全部 `GIT_*` 先移除再加固定
     集合（`GIT_TERMINAL_PROMPT=0`、`GCM_INTERACTIVE=never`、`GIT_AUTHOR_*`／`GIT_COMMITTER_*`、
     `GIT_CONFIG_GLOBAL`／`GIT_CONFIG_SYSTEM` 指向空檔，使結果與使用者機器的 git 設定無關；唯讀呼叫
     另帶 `GIT_OPTIONAL_LOCKS=0`，D-128）；`GH_TOKEN` 只傳給 gh 子行程。

token 零外洩（AC-961-6）：argv、回傳的 stdout／stderr、記錄的 argv 一律先過 `redact`（token 樣式加
呼叫端給的秘密值，含被換行切開與 URL 編碼形態）再截尾 2000 字元；token 不入 argv（只走環境）。
子行程一律 argv 陣列、`shell=False`、`**procutil.popen_platform_kwargs()`。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from .. import procutil
from ..security import is_within

# ── 值域常數（TCS §5.1；route.py 轉出同名常數，測試與產品碼共用同一份）──────────────────────────
BRANCH_PATTERN = r"^feature/[a-z0-9-]{1,40}$"
REPO_NAME_PATTERN = r"^[a-z][a-z0-9-]{1,38}$"
OWNER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}$"
VISIBILITIES = ("PRIVATE", "PUBLIC")
TAIL_CHARS = 2000
DEFAULT_TIMEOUT_SECONDS = 120.0
MASK = "***"

_BRANCH_RE = re.compile(BRANCH_PATTERN)
_REPO_RE = re.compile(REPO_NAME_PATTERN)
_OWNER_RE = re.compile(OWNER_PATTERN)
#: git ref 的保守子集：英數起頭，其後英數與 `._/-`；不含 `..`、`@{`、`//`、結尾 `/`、`.`、`.lock`。
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
_SHA_PREFIX_RE = re.compile(r"[0-9a-f]{12}")
_RP_NO_RE = re.compile(r"RP-[0-9]{4,}")
_REMOTE_URL_RE = re.compile(r"^https://github\.com/[A-Za-z0-9][A-Za-z0-9-]{0,38}/"
                            r"[a-z][a-z0-9-]{1,38}(\.git)?$")
#: token 樣式（GitHub PAT 與 OAuth／App token）。
_TOKEN_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{16,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{16,}"),
)
READONLY_GIT_VERBS = frozenset({"status", "rev-parse", "diff", "ls-files", "branch"})
#: 只加在環境、不加在 argv 的固定身分（commit 作者；不寫任何 git config 檔）。
DEFAULT_IDENTITY = ("AISDLC Console Bridge", "console-bridge@users.noreply.invalid")


class GitopsDenied(Exception):
    """argv 不在允許集合內、或使用者片段不合規；一律在 spawn 之前拒絕。"""

    def __init__(self, verb: str, message: str = "") -> None:
        super().__init__(f"gitops denied: {verb}" + (f"（{message}）" if message else ""))
        self.verb = verb


class GitResult(NamedTuple):
    """一次 git／gh 呼叫的結果；`stdout`／`stderr` 已去敏並截為尾端 2000 字元。"""

    argv_redacted: str
    returncode: int | None
    stdout: str
    stderr: str


# ── 脫敏與截尾 ──────────────────────────────────────────────────────────────────────────────
def _percent_encode(text: str) -> str:
    return "".join(c if (c.isalnum() and c.isascii()) or c in "-._~" else f"%{ord(c):02X}"
                   for c in text)


def redact(text: str, secrets: Sequence[str] = ()) -> str:
    """把 token 樣式與 `secrets` 內的每個秘密值（含被空白或換行切開、百分號編碼，以及長度足夠時的
    前 8 字元）換成 `***`。先脫敏、後截尾（見 `tail`），所以截尾不會留下可還原的半截 token。"""
    out = text
    for pattern in _TOKEN_PATTERNS:
        out = pattern.sub(MASK, out)
    for secret in sorted({s for s in secrets if s}, key=len, reverse=True):
        forms = {secret, _percent_encode(secret)}
        for form in forms:
            spaced = r"\s*".join(re.escape(ch) for ch in form)
            out = re.sub(spaced, MASK, out)
        if len(secret) >= 16:
            out = out.replace(secret[:8], MASK)
    return out


def tail(text: str, limit: int = TAIL_CHARS) -> str:
    return text if len(text) <= limit else text[-limit:]


# ── 使用者片段驗證 ─────────────────────────────────────────────────────────────────────────
def valid_ref(name: str) -> bool:
    """git ref（分支或基底）：保守子集＋git 的禁用形態；不以 `-` 起頭（選項注入）。"""
    if not isinstance(name, str) or not _REF_RE.fullmatch(name):
        return False
    return not (".." in name or "@{" in name or "//" in name or name.endswith(("/", ".", ".lock"))
                or "/." in name or ".lock/" in name)


def valid_branch(name: str) -> bool:
    return isinstance(name, str) and _BRANCH_RE.fullmatch(name) is not None and valid_ref(name)


def valid_owner(name: str) -> bool:
    return isinstance(name, str) and _OWNER_RE.fullmatch(name) is not None


def valid_repo_name(name: str) -> bool:
    return isinstance(name, str) and _REPO_RE.fullmatch(name) is not None


def check_path(path: str | Path, root: Path, *, cwd: Path | None = None) -> Path:
    """路徑（相對 `cwd`〔省略＝`root`〕或絕對）解析後須在 `root` 之下（擋 `..`、絕對路徑與符號連結
    逃逸）；否則 `GitopsDenied`。回解析後的絕對路徑。"""
    text = str(path)
    if not text or "\x00" in text or text.startswith("-"):
        raise GitopsDenied("path", "路徑為空、含 NUL 或以 - 起頭")
    base = root if cwd is None else cwd
    target = Path(text) if Path(text).is_absolute() else base / text
    if not is_within(target, root):
        raise GitopsDenied("path", "路徑不在允許的根之下")
    return target.resolve()


def commit_message(kind: str, rp_no: str, sha12: str | None = None) -> str:
    """commit 訊息一律取自這裡的模板常數（繁體中文；不含使用者原文）。"""
    if not _RP_NO_RE.fullmatch(rp_no):
        raise GitopsDenied("commit", "rp_no 格式不合")
    if kind == "publish":
        if sha12 is None or not _SHA_PREFIX_RE.fullmatch(sha12):
            raise GitopsDenied("commit", "sha12 格式不合")
        return f"docs: 發佈 {rp_no} PRD 與落點提示（sha256 {sha12}）"
    if kind == "scaffold":
        return f"chore: 由 ResearchToPRD 建立 {rp_no} 專案骨架"
    raise GitopsDenied("commit", f"未知的訊息模板 {kind!r}")


_MESSAGE_RES = (
    re.compile(r"^docs: 發佈 RP-[0-9]{4,} PRD 與落點提示（sha256 [0-9a-f]{12}）$"),
    re.compile(r"^chore: 由 ResearchToPRD 建立 RP-[0-9]{4,} 專案骨架$"),
)


# ── argv 解析（允許集合；預設拒絕）──────────────────────────────────────────────────────────
def parse_git(tokens: Sequence[str], *, cwd: Path | None = None,
              scaffold_root: Path | None = None,
              worktree_root: Path | None = None) -> list[str]:
    """`git` 之後的 token（可含最前面的 `-c core.longpaths=true`）→ 完整 argv（首元素 `git`）。
    不在允許集合＝`GitopsDenied`。"""
    toks = [str(t) for t in tokens]
    if not toks:
        raise GitopsDenied("", "空的 git 呼叫")
    config: list[str] = []
    if toks[0] == "-c":
        if len(toks) < 3 or toks[1] != "core.longpaths=true":
            raise GitopsDenied("-c", "-c 只准 core.longpaths=true")
        config = ["-c", "core.longpaths=true"]
        toks = toks[2:]
    verb, args = toks[0], toks[1:]
    argv = ["git", *config]
    if config and not (verb == "worktree" and args[:1] == ["add"]):
        raise GitopsDenied("-c", "-c core.longpaths=true 只用於 worktree add")
    if verb == "status":
        if args != ["--porcelain"]:
            raise GitopsDenied(verb, "只准 status --porcelain")
        return [*argv, verb, "--porcelain"]
    if verb == "rev-parse":
        if args and args[0] == "--verify" and len(args) == 2 and valid_ref(args[1]):
            return [*argv, verb, "--verify", args[1]]
        if args in (["HEAD"], ["--show-toplevel"], ["--is-inside-work-tree"],
                    ["--verify", "HEAD"]):
            return [*argv, verb, *args]
        raise GitopsDenied(verb, "rev-parse 的引數不在允許形態")
    if verb == "diff":
        if len(args) == 2 and args[0] == "--name-only" and (
                _valid_range(args[1])):
            return [*argv, verb, "--name-only", args[1]]
        raise GitopsDenied(verb, "只准 diff --name-only <a>..<b>")
    if verb == "ls-files":
        if args in ([], ["-s"]):
            return [*argv, verb, *args]
        raise GitopsDenied(verb, "只准 ls-files 或 ls-files -s")
    if verb == "branch":
        if args == ["--list"]:
            return [*argv, verb, "--list"]
        if len(args) == 2 and args[0] == "--list" and valid_ref(args[1]):
            return [*argv, verb, "--list", args[1]]
        raise GitopsDenied(verb, "只准 branch --list [<ref>]")
    if verb == "worktree":
        return [*argv, *_parse_worktree(args, config, worktree_root)]
    if verb == "init":
        if args == ["-b", "main"]:
            return [*argv, verb, "-b", "main"]
        raise GitopsDenied(verb, "只准 init -b main")
    if verb == "add":
        return [*argv, *_parse_add(args, cwd, scaffold_root, worktree_root)]
    if verb == "commit":
        if len(args) == 2 and args[0] == "-m" and any(r.fullmatch(args[1]) for r in _MESSAGE_RES):
            return [*argv, verb, "-m", args[1]]
        raise GitopsDenied(verb, "commit 訊息只准取自模板常數（commit_message）")
    if verb == "remote":
        if len(args) == 3 and args[:2] == ["add", "origin"] and _REMOTE_URL_RE.fullmatch(args[2]):
            return [*argv, verb, "add", "origin", args[2]]
        raise GitopsDenied(verb, "只准 remote add origin <https://github.com/…>")
    if verb == "push":
        if len(args) == 3 and args[0] == "-u" and args[1] == "origin" and valid_ref(args[2]):
            return [*argv, verb, "-u", "origin", args[2]]
        raise GitopsDenied(verb, "只准 push -u origin <已驗證分支>")
    raise GitopsDenied(verb, "不在 P1 允許集合內")


def _valid_range(text: str) -> bool:
    parts = text.split("..")
    return len(parts) == 2 and all(valid_ref(p) for p in parts)


def _parse_worktree(args: Sequence[str], config: Sequence[str],
                    worktree_root: Path | None) -> list[str]:
    if list(args) == ["list", "--porcelain"]:
        return ["worktree", "list", "--porcelain"]
    if len(args) == 5 and args[0] == "add" and args[1] == "-b":
        _, _, branch, path, base_ref = args
        if not valid_branch(branch):
            raise GitopsDenied("worktree", "分支名不合規")
        if not valid_ref(base_ref):
            raise GitopsDenied("worktree", "基底 ref 不合規")
        if worktree_root is None or not Path(path).is_absolute() or not is_within(
                Path(path), worktree_root):
            raise GitopsDenied("worktree", "worktree 路徑須是 BRIDGE_WORKTREE_ROOT 之下的絕對路徑")
        if config and list(config) != ["-c", "core.longpaths=true"]:
            raise GitopsDenied("worktree", "-c 只准 core.longpaths=true")
        return ["worktree", "add", "-b", branch, path, base_ref]
    raise GitopsDenied("worktree", "只准 worktree list --porcelain 與 worktree add -b")


def _parse_add(args: Sequence[str], cwd: Path | None, scaffold_root: Path | None,
               worktree_root: Path | None) -> list[str]:
    if list(args) == ["-A"]:
        # `add -A` 只准在新專案根（軌道 B）之內；軌道 A 的 worktree 內一律禁（AC-12-6）。
        if cwd is None or scaffold_root is None or not is_within(cwd, scaffold_root) or (
                worktree_root is not None and is_within(cwd, worktree_root)):
            raise GitopsDenied("add", "add -A 只准在 BRIDGE_SCAFFOLD_ROOT 之下的新專案根")
        return ["add", "-A"]
    if len(args) >= 2 and args[0] == "--":
        if cwd is None:
            raise GitopsDenied("add", "add -- 需要指定 worktree 作為 cwd")
        paths = []
        for raw in args[1:]:
            if raw.startswith("-"):
                raise GitopsDenied("add", "路徑不得以 - 起頭")
            check_path(raw, cwd, cwd=cwd)
            paths.append(raw)
        return ["add", "--", *paths]
    raise GitopsDenied("add", "只准 add -A（新專案根）或 add -- <明列路徑…>")


def parse_gh(args: Sequence[str]) -> list[str]:
    """`gh` 之後的 token → 完整 argv（首元素 `gh`）；P1 只有 `auth status` 與 `repo create`。"""
    toks = [str(t) for t in args]
    if toks == ["auth", "status"]:
        return ["gh", "auth", "status"]
    if len(toks) == 7 and toks[:2] == ["repo", "create"] and toks[3] in ("--private", "--public"):
        slug, _vis, source, dot, push = toks[2], toks[3], toks[4], toks[5], toks[6]
        owner, _, repo = slug.partition("/")
        if valid_owner(owner) and valid_repo_name(repo) and (source, dot, push) == (
                "--source", ".", "--push"):
            return ["gh", "repo", "create", slug, toks[3], "--source", ".", "--push"]
    raise GitopsDenied("gh", "P1 只准 auth status 與 repo create <owner>/<repo> --private|--public "
                             "--source . --push")


def build_argv(verb: str, args: Sequence[str] = (), *, cwd: Path | None = None,
               scaffold_root: Path | None = None,
               worktree_root: Path | None = None) -> list[str]:
    """`verb`（git 子命令，或 `gh`）加其引數 → argv 列表；表外一律 `GitopsDenied`。`verb` 以 `-`
    起頭視為 `-c …` 前綴形態，交 `parse_git` 判。純函式、不起子行程。"""
    if verb == "gh":
        return parse_gh(args)
    return parse_git([verb, *args], cwd=cwd, scaffold_root=scaffold_root,
                     worktree_root=worktree_root)


# ── 子行程環境 ─────────────────────────────────────────────────────────────────────────────
_STRIP_EXACT = frozenset({"PYTHONPATH", "GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN",
                          "GH_HOST"})


def child_env(tool: str, *, readonly: bool = False, token: str | None = None,
              identity: tuple[str, str] = DEFAULT_IDENTITY,
              base: Mapping[str, str] | None = None) -> dict[str, str]:
    """子行程環境：先移除 `BRIDGE_*`、`SDD_*`、`PYTHONPATH`、token 類與全部 `GIT_*`，再加固定集合。
    `GH_TOKEN` 只在 `tool == "gh"` 且給了 token 時加入。"""
    source = os.environ if base is None else base
    env = {k: v for k, v in source.items()
           if not k.startswith(("BRIDGE_", "SDD_", "GIT_")) and k not in _STRIP_EXACT}
    name, email = identity
    env.update({
        "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never",
        "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
        "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
    })
    if readonly:
        env["GIT_OPTIONAL_LOCKS"] = "0"
    if tool == "gh" and token:
        env["GH_TOKEN"] = token
    return env


# ── 執行 ───────────────────────────────────────────────────────────────────────────────────
def _spawn(argv: Sequence[str], cwd: Path, env: Mapping[str, str],
           timeout: float) -> tuple[int | None, str, str]:
    """唯一的 `Popen` 呼叫點（測試以 monkeypatch 換成計數器或注入故障）。找不到執行檔回
    `(127, "", "<tool>_not_found")`；逾時殺掉行程並回 `(None, "", "timeout")`。"""
    exe = shutil.which(argv[0], path=env.get("PATH"))
    if exe is None:
        return 127, "", f"{argv[0]}_not_found"
    cmd = [exe, *argv[1:]]
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(cwd), env=dict(env), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=False, **procutil.popen_platform_kwargs())
    except OSError as exc:
        return 127, "", f"{argv[0]}_not_found: {type(exc).__name__}"
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        procutil.force_kill(procutil.begin_terminate(proc.pid))
        proc.communicate()
        return None, "", "timeout"
    return (proc.returncode, out.decode("utf-8", errors="replace"),
            err.decode("utf-8", errors="replace"))


@dataclass(frozen=True)
class CallRecord:
    """一次呼叫的紀錄（argv 已去敏；`env_keys` 只有鍵名、不含值）。測試以 `OBSERVERS` 取得。"""

    argv: tuple[str, ...]
    cwd: str
    env_keys: tuple[str, ...]
    readonly: bool
    has_gh_token: bool


#: 呼叫觀察者（測試用）：每次**放行並 spawn 前**呼叫一次；拒絕的呼叫不會出現（零 spawn）。
OBSERVERS: list[Callable[[CallRecord], None]] = []


@dataclass
class Gitops:
    """一個分流請求的 git／gh 執行脈絡。`secrets` 是要從輸出遮罩的值（請求中的 token）。"""

    scaffold_root: Path | None = None
    worktree_root: Path | None = None
    identity: tuple[str, str] = DEFAULT_IDENTITY
    secrets: tuple[str, ...] = ()
    token: str | None = field(default=None, repr=False)
    timeout: float = DEFAULT_TIMEOUT_SECONDS

    def _run(self, argv: list[str], *, tool: str, cwd: Path, readonly: bool) -> GitResult:
        env = child_env(tool, readonly=readonly, token=self.token if tool == "gh" else None,
                        identity=self.identity)
        shown = redact(" ".join(argv), self.secrets)
        record = CallRecord(tuple(shown.split(" ")), str(cwd), tuple(sorted(env)), readonly,
                            "GH_TOKEN" in env)
        for observer in list(OBSERVERS):
            observer(record)
        rc, out, err = _spawn(argv, cwd, env, self.timeout)
        return GitResult(shown, rc, tail(redact(out, self.secrets)),
                         tail(redact(err, self.secrets)))

    def git(self, tokens: Sequence[str], *, cwd: Path) -> GitResult:
        """`tokens`＝`git` 之後的 token（例 `["status", "--porcelain"]`）。不在允許集合＝
        `GitopsDenied`（不 spawn）。"""
        argv = parse_git(tokens, cwd=cwd, scaffold_root=self.scaffold_root,
                         worktree_root=self.worktree_root)
        verb = next((t for t in argv[1:] if t not in ("-c", "core.longpaths=true")), "")
        readonly = verb in READONLY_GIT_VERBS or (
            verb == "worktree" and argv[-2:] == ["list", "--porcelain"])
        return self._run(argv, tool="git", cwd=cwd, readonly=readonly)

    def gh(self, args: Sequence[str], *, cwd: Path) -> GitResult:
        return self._run(parse_gh(args), tool="gh", cwd=cwd, readonly=False)
