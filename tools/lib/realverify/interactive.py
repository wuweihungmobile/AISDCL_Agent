"""realverify 唯一的「開沙盒互動視窗」入口（R217 F5）。

事故（2026-11-20 10:4x，掌舵者真機回報）：真機驗證在 `git init` 的新沙盒裡開互動 claude，桌面跳出
「Quick safety check: Is this a project you created or one you trust?」信任對話框。

信任判定（官方文件 permissions.md〈Project allow rules and workspace trust〉、security.md〈Trust
verification〉；2.1.329 實測）：
- 只有互動模式會跳框；`claude -p`／SDK 從不顯示（driver 的 `-p` 案例與此事無關）。
- repo 裡以 **git 根**為鍵；worktree 以**主 checkout 根**為鍵；巢狀 git repo 不吃父目錄信任。
- 信任存 `~/.claude.json` 的 `projects["<鍵>"].hasTrustDialogAccepted`；沒有旗標或環境變數可略過。
⇒ 每個 `git init` 沙盒都是一把新鍵，互動視窗**必跳框**——這是成因，不是偶發。

結構正解：互動沙盒改成**專用宿主 repo（`HOST`）的 worktree**，信任鍵恆為 `HOST`；宿主一次性信任後，
所有互動沙盒都不跳框。開窗前兩道確認，任一不過就拒絕（`NotTrusted`＝`EnvMissing`，runner 判 ENV），
**絕不開出會跳框的視窗**：①唯讀查 `~/.claude.json` 有 `HOST` 的信任鍵；②在沙盒本身以隱藏主控台
（`CREATE_NO_WINDOW`，桌面看不到）起一個不帶提示的互動 claude（零推論 token），debug 日誌出現
`READY_MARK`（REPL 已掛載＝已越過所有啟動畫面）才算數。本模組不寫 `~/.claude.json`。
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .driver import EnvMissing, find_claude
from .sandbox import _DROP_ENV, PROBE_HOOK_REL, PROBE_HOOK_SRC, SANDBOX_PREFIX, Sandbox, kill_tree

HOST = Path.home() / ".autosdd" / "rv_host"
READY_MARK = "[REPL:mount] REPL mounted"  # 越過信任框／onboarding 等全部啟動畫面才會出現
UNTRUSTED_MARK = "not loaded until workspace trust is accepted"
PROBE_TIMEOUT_S = 40.0
_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_NEWCON = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10)
TRUST_HOWTO = (
    "一次性信任宿主（須掌舵者同意；本模組不代寫全域設定）：在 {host} 開一次互動 `claude` 按"
    "「Yes, I trust this folder」，或於 ~/.claude.json 的 projects 加 "
    "\"{key}\": {{\"hasTrustDialogAccepted\": true}}。")

#: 尚未改走本入口、但會開互動視窗的案例（`檔名::函式`）。runner 直接判 ENV、不執行，免得再跳框。
#: 與 `find_bypasses()` 機械比對（InteractiveWindowEntryLockTest）：多列少列都紅。
UNMIGRATED: frozenset[str] = frozenset({"sessionctl_handoff.py::rv_h3"})


class NotTrusted(EnvMissing):
    """確認不了「開窗不會跳信任框」：拒絕開窗，案例判 ENV（不是 skip 成綠）。"""


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,  # noqa: S603,S607
                          encoding="utf-8", errors="replace", creationflags=_NOWIN, timeout=60)


def host_key(host: Path = HOST) -> str:
    """Claude Code 在 Windows 以正斜線寫 git 根鍵（實測 `D:/CursorProject/AISDCL_Agent`）。"""
    return str(Path(host).resolve()).replace("\\", "/")


def _norm(path: str) -> str:
    s = str(path).replace("\\", "/").rstrip("/")
    return s.casefold() if os.name == "nt" else s


def ensure_host(host: Path = HOST) -> Path:
    """宿主 repo 不在就建（git init＋一個空 commit；身分只寫宿主自己的 config）。"""
    host = Path(host)
    if not (host / ".git").exists():
        host.mkdir(parents=True, exist_ok=True)
        for args in (["init", "-q"], ["config", "user.email", "rv@example.invalid"],
                     ["config", "user.name", "realverify"],
                     ["commit", "-q", "--allow-empty", "-m", "realverify interactive host"]):
            r = _git(args, host)
            if r.returncode != 0:
                raise EnvMissing(f"建宿主 repo 失敗（git {args[0]}）：{r.stderr.strip()[:200]}")
    return host


def trusted_in_config(host: Path = HOST, claude_json: Path | None = None) -> bool:
    """唯讀：`~/.claude.json` 有宿主鍵且 `hasTrustDialogAccepted` 為真；讀不到一律 False。"""
    p = claude_json or Path.home() / ".claude.json"
    try:
        projects = json.loads(p.read_text(encoding="utf-8")).get("projects") or {}
    except (OSError, ValueError, AttributeError):
        return False
    want = _norm(host_key(host))
    return any(_norm(k) == want and isinstance(v, dict) and v.get("hasTrustDialogAccepted") is True
               for k, v in projects.items())


def classify_debug(text: str) -> str:
    """debug 日誌 → `ready`／`untrusted`／`unknown`（字樣改版就落 unknown＝拒絕，不會誤放行）。"""
    if READY_MARK in text:
        return "ready"
    return "untrusted" if UNTRUSTED_MARK in text else "unknown"


def probe_ready(cwd: Path, *, timeout_s: float = PROBE_TIMEOUT_S, claude: str | None = None) -> tuple[str, str]:  # noqa: E501
    """隱藏主控台起不帶提示的互動 claude，讀 `--debug-file` 判定；結束連樹砍。回 (判定, 說明)。"""
    if os.name != "nt":
        return "unknown", "非 Windows：沒有已驗證的隱藏主控台載具"
    exe = claude or find_claude()
    dbg = Path(tempfile.gettempdir()) / f"AutoSDD_RV_trustprobe_{uuid.uuid4().hex[:8]}.log"
    env = {k: v for k, v in os.environ.items() if k not in _DROP_ENV}
    env["AUTOSDD_SENTINEL_OFF"] = "1"
    proc = subprocess.Popen(  # noqa: S603
        [exe, "--model", "haiku", "--debug-file", str(dbg)], cwd=str(cwd), env=env,
        creationflags=_NOWIN)
    verdict, t0 = "unknown", time.monotonic()
    try:
        while time.monotonic() - t0 < timeout_s and proc.poll() is None:
            text = dbg.read_text(encoding="utf-8", errors="replace") if dbg.is_file() else ""
            verdict = classify_debug(text)
            if verdict != "unknown":
                break
            time.sleep(0.5)
    finally:
        kill_tree(proc)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        try:
            dbg.unlink()
        except OSError:
            pass
    return verdict, f"{time.monotonic() - t0:.1f}s cwd={cwd}"


@dataclass
class WorktreeSandbox(Sandbox):
    """宿主 repo 的 worktree 沙盒（信任鍵＝宿主）。逐字稿仍落沙盒自己的 slug（2.1.329 實測），
    所以 `Sandbox` 的逐字稿／清理邏輯不變；只多了 worktree 登記的收尾。"""

    host: Path | None = None
    trust_verdict: str = ""

    def cleanup(self) -> list[str]:
        notes = super().cleanup()
        if self.host is None:
            return notes
        _git(["worktree", "prune"], self.host)
        listed = _git(["worktree", "list", "--porcelain"], self.host).stdout
        if _norm(str(self.root)) in _norm(listed.replace("\n", " ")):
            notes.append(f"RESIDUE worktree-registration {self.root}")
        return notes


def trusted_sandbox(ctx=None, *, host: Path = HOST, probe_hooks: bool = True, claude_json: Path | None = None,  # noqa: E501
                    prober=probe_ready) -> WorktreeSandbox:
    """建一個保證不跳信任框的互動沙盒；確認不了就 raise `NotTrusted`（不建、不開窗）。
    `ctx`（CaseContext）有給就登記進 `ctx.sandboxes`，由 runner 的 finally 清理。"""
    host = ensure_host(host)
    if not trusted_in_config(host, claude_json):
        raise NotTrusted(f"互動沙盒宿主 {host} 未受信任，拒絕開窗以免跳信任框。"
                         + TRUST_HOWTO.format(host=host, key=host_key(host)))
    root = Path(tempfile.mkdtemp(prefix=SANDBOX_PREFIX)).resolve()
    sb = WorktreeSandbox(root=root, host=host)
    if ctx is not None:
        ctx.sandboxes.append(sb)
    try:
        r = _git(["worktree", "add", "-q", "--detach", str(root), "HEAD"], host)
        if r.returncode != 0:
            raise EnvMissing(f"worktree add 失敗：{r.stderr.strip()[:200]}")
        verdict, why = prober(root)
        if verdict != "ready":
            raise NotTrusted(f"隱藏探針判 {verdict}（{why}）：開窗會停在啟動畫面，拒絕。"
                             + TRUST_HOWTO.format(host=host, key=host_key(host)))
        sb.trust_verdict = verdict
        (root / ".claude").mkdir(exist_ok=True)
        sb.write_file(PROBE_HOOK_REL, PROBE_HOOK_SRC)
        sb.write_settings()
        if probe_hooks:
            sb.add_probe_hooks()
    except BaseException:
        if ctx is None:
            sb.cleanup()
        raise
    return sb


def assert_trusted(sb: Sandbox) -> None:
    """被測碼自己會開互動視窗（如 `handoff --spawn`）的案例，觸發前先呼叫。"""
    if not isinstance(sb, WorktreeSandbox) or sb.trust_verdict != "ready":
        raise NotTrusted("此沙盒未經 interactive.trusted_sandbox 確認，拒絕觸發開窗。")


def open_window(sb: Sandbox, args: list[str], *, visible: bool = True,
                env_extra: dict | None = None, claude: str | None = None) -> subprocess.Popen:
    """realverify 內唯一允許起互動 claude 的地方；行程記進 `sb.procs`，清理時連樹砍。"""
    assert_trusted(sb)
    if "-p" in args or "--print" in args:
        raise ValueError("`-p` 不是互動視窗，請用 driver.run_claude")
    proc = subprocess.Popen(  # noqa: S603
        [claude or find_claude(), *args], cwd=str(sb.root), env=sb.env(env_extra),
        creationflags=_NEWCON if visible else _NOWIN)
    sb.procs.append(proc)
    return proc


# ───────────────────────────────────────────── 機械防線：找繞過本入口的開窗寫法
_ENTRY_CALLS = {"trusted_sandbox", "assert_trusted", "open_window"}
_CLAUDE_FUNCS = {"find_claude", "real_claude"}
_NON_INTERACTIVE = {"-p", "--print", "--version", "-v"}


def _call_name(node: ast.Call) -> str:
    f = node.func
    return f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")


def _yields_claude(v: ast.AST) -> bool:
    """`find_claude()`／`real_claude()`／`shutil.which("claude")`／字面 `"claude"`。"""
    if isinstance(v, ast.Constant):
        return v.value in {"claude", "claude.exe"}
    if isinstance(v, ast.Call):
        return _call_name(v) in _CLAUDE_FUNCS or (
            _call_name(v) == "which" and bool(v.args) and _yields_claude(v.args[0]))
    return False


def _is_interactive_argv(lst: ast.List, claude_names: set[str]) -> bool:
    has = any(_yields_claude(e) or (isinstance(e, ast.Name) and e.id in claude_names)
              for e in lst.elts)
    flags = {e.value for e in lst.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    return has and not (flags & _NON_INTERACTIVE)


def _is_handoff_spawn(n: ast.Call) -> bool:
    f = n.func
    return (isinstance(f, ast.Attribute) and f.attr == "spawn"
            and getattr(f.value, "id", "") == "handoff")


def spawn_markers(fn: ast.AST) -> list[str]:
    """函式本體裡會開出互動視窗的寫法（紅綠自證見 InteractiveWindowEntryLockTest）。"""
    claude_names = {t.id for n in ast.walk(fn)
                    if isinstance(n, ast.Assign) and _yields_claude(n.value)
                    for t in n.targets if isinstance(t, ast.Name)}
    out: list[str] = []
    for n in ast.walk(fn):
        if (isinstance(n, ast.Attribute) and n.attr == "CREATE_NEW_CONSOLE") or (
                isinstance(n, ast.Constant) and n.value == "CREATE_NEW_CONSOLE") or (
                isinstance(n, ast.Name) and n.id == "CREATE_NEW_CONSOLE"):
            out.append(f"L{n.lineno} CREATE_NEW_CONSOLE")
        elif (isinstance(n, ast.keyword) and n.arg == "creationflags"
              and isinstance(n.value, ast.Constant) and n.value.value == 0x10):
            out.append(f"L{n.value.lineno} creationflags=0x10")
        elif isinstance(n, ast.Call):
            if any(isinstance(a, ast.Constant) and a.value == "--spawn" for a in n.args):
                out.append(f"L{n.lineno} --spawn")
            if _call_name(n) == "spawn_resume" or _is_handoff_spawn(n):
                out.append(f"L{n.lineno} {_call_name(n)}()")
            if n.args and isinstance(n.args[0], ast.List) and _is_interactive_argv(n.args[0], claude_names):  # noqa: E501
                out.append(f"L{n.lineno} 互動 claude argv")
    return out


def _calls(fn: ast.AST) -> set[str]:
    return {_call_name(n) for n in ast.walk(fn) if isinstance(n, ast.Call)}


def find_bypasses(paths: list[Path]) -> dict[str, list[str]]:
    """回 `{檔名::函式: [標記…]}`：有開窗標記、卻沒呼叫本入口的函式；被它們（同檔、一層）呼叫到的
    函式也一併列出——開窗寫在 helper、入口寫在案例本體時，以案例本體有沒有呼叫入口為準。"""
    found: dict[str, list[str]] = {}
    for p in paths:
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        fns = {n.name: n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        calls = {name: _calls(fn) for name, fn in fns.items()}
        for name, fn in fns.items():
            marks = spawn_markers(fn)
            if not marks or calls[name] & _ENTRY_CALLS:
                continue
            callers = [c for c in fns if c != name and name in calls[c]]
            bad = [c for c in callers if not calls[c] & _ENTRY_CALLS]
            if callers and not bad:
                continue  # helper：同檔呼叫者全都先過入口
            found[f"{p.name}::{name}"] = marks
            for c in bad:
                found.setdefault(f"{p.name}::{c}", []).append(f"經 {name}()")
    return found


def realverify_sources(root: Path | None = None) -> list[Path]:
    base = root or Path(__file__).resolve().parent
    return sorted(p for p in base.rglob("*.py")
                  if p.name != "interactive.py" and "__pycache__" not in p.parts)


def status(host: Path = HOST) -> str:
    """給人看的現況：宿主在不在、全域設定有沒有信任鍵（唯讀；不起探針）。"""
    exists = (Path(host) / ".git").exists()
    return (f"host={host} exists={exists} key={host_key(host)} "
            f"trusted_in_config={trusted_in_config(host) if exists else False}")
