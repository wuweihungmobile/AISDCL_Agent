"""沙盒專案：repo 外的唯一暫存目錄＋git init＋`.claude/settings.json`＋清理。

CLAUDE_PROJECT_DIR 的語意（實測 2026-11-18）：在沙盒裡開的 claude，CC 會把它設成**沙盒根**。
repo 的 `_hook_launcher.py` 靠它找目標腳本（`<root>/.claude/hooks/x.py`）⇒ 在沙盒中缺檔
＝**fail-open exit 0，永遠假綠**。所以沙盒的 hook 條目一律「venv 直譯器＋repo
腳本絕對路徑」直接 spawn，
不經啟動器（repo 的守衛腳本以 `__file__` 找 repo，不依賴 CLAUDE_PROJECT_DIR）。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SANDBOX_PREFIX = "AutoSDD_RV_sbx_"
PROBE_HOOK_REL = ".claude/rv_probe_hook.py"
PROC_EXIT_WAIT_S = 5.0  # cleanup 砍樹後等行程真的退出的上限（DEF-03）

# 沙盒專用探針 hook（放沙盒裡、不進 repo `.claude/`）：每次觸發把 payload 追加進
# hook_events.jsonl（證明真的跑過）；Stop 在 stop_hook_active 為假時 decision:block 一次；
# UserPromptSubmit 在 prompt 含 RV_BLOCK_PROMPT 時擋下。
PROBE_HOOK_SRC = '''\
import json, os, sys, time
p = json.load(sys.stdin)
ev = p.get("hook_event_name")
d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(d, "hook_events.jsonl"), "a", encoding="utf-8") as f:
    f.write(json.dumps({"ev": ev, "t": time.time(), "keys": sorted(p), "payload": p},
    ensure_ascii=False) + "\\n")
if ev == "Stop" and os.environ.get("RV_STOP_BLOCK") and not p.get("stop_hook_active"):
    print(json.dumps({"decision": "block", "reason": "RV_STOP_BLOCK_REASON"}))
elif ev == "UserPromptSubmit" and "RV_BLOCK_PROMPT" in str(p.get("prompt", "")):
    print(json.dumps({"decision": "block", "reason": "RV_UPS_BLOCK_REASON"}))
sys.exit(0)
'''

# 逃生變數：沙盒子行程不得繼承會污染判定的父視窗狀態
_DROP_ENV = ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_PROJECT_DIR", "AUTOSDD_UNATTENDED")


def venv_python() -> str:
    """hook 載具：Windows 用 pythonw（與根 settings 同形，零視窗），POSIX 用 .venv/bin/python。"""
    cand = REPO / ".venv" / "Scripts" / "pythonw.exe" if os.name == "nt" else REPO / ".venv" / "bin" / "python"  # noqa: E501
    return str(cand)


def slug_of(path: Path | str) -> str:
    """Claude Code 的專案目錄 slug：非英數字元一律轉 `-`。"""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def projects_dir() -> Path:
    return Path.home() / ".claude" / "projects"


def kept_dir() -> Path:
    """失敗證據保留根目錄（持久，不在沙盒內；`Sandbox.preserve` 的去處）。"""
    return Path.home() / ".autosdd" / "realverify_kept"


def main_checkout_root(repo: Path = REPO) -> Path:
    """主工作樹根：`repo` 是 git worktree 時回主 checkout（經 `--git-common-dir`），否則回 `repo`。

    WHY（R216 複審 RV-C3）：真逐字稿住 `~/.claude/projects/<主 checkout 路徑 slug>`，worktree 路徑的
    slug 對不上 ⇒ 事故重放找不到母體而判紅，是載具問題不是被測物問題。"""
    out = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    common = out.stdout.strip()
    if out.returncode != 0 or not common:
        return repo
    return Path(common).resolve().parent


def handoff_dir() -> Path:
    """真交接包目錄（§6b-2：不加 env 出口；沙盒 sid 天生唯一，只刪自己 sid 開頭的檔）。"""
    return Path.home() / ".autosdd" / "handoff"


def cleanup_handoff_for(sid: str, base: Path | None = None) -> list[str]:
    """刪 `<base>/<sid>*`（只刪檔名以該 sid 開頭者）；回刪掉的檔名。sid 必須是完整 UUID，防誤刪別人的。"""  # noqa: E501
    if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", sid or ""):
        raise ValueError(f"sid 非完整 UUID，拒絕清理交接包：{sid!r}")
    root = base if base is not None else handoff_dir()
    gone: list[str] = []
    if not root.is_dir():
        return gone
    for p in root.iterdir():
        if p.is_file() and p.name.startswith(sid):
            try:
                p.unlink()
                gone.append(p.name)
            except OSError:
                pass
    return gone


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(  # noqa: S603
        ["git", *args], cwd=str(cwd), check=True, capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


@dataclass
class Sandbox:
    root: Path
    sid: str = field(default_factory=lambda: str(uuid.uuid4()))
    settings: dict = field(default_factory=lambda: {"hooks": {}})
    procs: list = field(default_factory=list)  # 只殺自己 spawn 的 Popen
    used_resume: bool = False

    # ---- 建立 ----
    @classmethod
    def create(cls, probe_hook: bool = True) -> Sandbox:
        root = Path(tempfile.mkdtemp(prefix=SANDBOX_PREFIX)).resolve()
        sb = cls(root=root)
        (root / ".claude").mkdir()
        _git(["init", "-q"], root)
        _git(["config", "user.email", "rv@example.invalid"], root)
        _git(["config", "user.name", "realverify"], root)
        if probe_hook:
            sb.write_file(PROBE_HOOK_REL, PROBE_HOOK_SRC)
        sb.write_settings()
        return sb

    # ---- 檔案／設定 ----
    def write_file(self, rel: str, text: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
        return p

    def hook_entry(self, script: Path | str, *args: str, timeout: int = 20) -> dict:
        return {"type": "command", "command": venv_python(),
                "args": [str(script), *args], "timeout": timeout}

    def add_hook(self, event: str, script: Path | str, *args: str, matcher: str | None = None, timeout: int = 20) -> None:  # noqa: E501
        group: dict = {"hooks": [self.hook_entry(script, *args, timeout=timeout)]}
        if matcher:
            group["matcher"] = matcher
        self.settings.setdefault("hooks", {}).setdefault(event, []).append(group)
        self.write_settings()

    def add_probe_hooks(self, events: tuple[str, ...] = ("SessionStart", "UserPromptSubmit", "Stop")) -> None:  # noqa: E501
        for ev in events:
            self.add_hook(ev, self.root / PROBE_HOOK_REL)

    def add_repo_hook(self, event: str, rel: str, *, matcher: str | None = None, timeout: int = 20) -> None:  # noqa: E501
        """掛 repo 的守衛腳本（絕對路徑直接 spawn，不經 `_hook_launcher`，理由見模組 docstring）。"""  # noqa: E501
        script = REPO / rel
        if not script.is_file():
            raise FileNotFoundError(f"repo hook 不存在：{script}")
        self.add_hook(event, script, matcher=matcher, timeout=timeout)

    def write_settings(self) -> None:
        self.write_file(".claude/settings.json", json.dumps(self.settings, indent=2, ensure_ascii=False))  # noqa: E501

    # ---- 子行程環境 ----
    def env(self, extra: dict | None = None) -> dict:
        e = {k: v for k, v in os.environ.items() if k not in _DROP_ENV}
        e["PYTHONUTF8"] = "1"
        e["AUTOSDD_TRACE_DIR"] = str(self.root / "traces")
        e["AUTOSDD_SENTINEL_OFF"] = "1"  # 沙盒預設不武裝哨兵，免得漏排程；需要的案例自己覆寫
        e.update(extra or {})
        return e

    def events(self) -> list[dict]:
        """探針 hook 的觸發記錄（空＝hook 根本沒跑＝假綠警訊）。"""
        p = self.root / "hook_events.jsonl"
        if not p.is_file():
            return []
        return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]

    # ---- 失敗保留 ----
    def preserve(self, dest: Path) -> list[str]:
        """把判失敗所需的證據複製到 `dest`（沙盒清理前呼叫）：逐字稿目錄、探針 hook 觸發記錄、
        `claude --debug hooks` 日誌、沙盒內 traces（守衛痕跡）。回複製成功的項目名；缺的略過。

        WHY（R216 複審 P3-c）：RV-C4 低頻逾時 291 秒，因沙盒逐字稿隨清理一起刪掉，根因再也查不到。
        證據只在**失敗**時留（過案例照舊清乾淨，不累積殘留）。"""
        got: list[str] = []
        dest.mkdir(parents=True, exist_ok=True)
        for d in self.transcript_dirs():
            shutil.copytree(d, dest / "transcripts", dirs_exist_ok=True)
            got.append("transcripts")
        for name in ("hook_events.jsonl",):
            if (self.root / name).is_file():
                shutil.copy2(self.root / name, dest / name)
                got.append(name)
        for dbg in sorted(self.root.glob("debug_*.log")):
            shutil.copy2(dbg, dest / dbg.name)
            got.append(dbg.name)
        if (self.root / "traces").is_dir():
            shutil.copytree(self.root / "traces", dest / "traces", dirs_exist_ok=True)
            got.append("traces")
        return got

    # ---- 舊視窗關閉（oldwin）的沙盒前綴 ----
    def oldwin_prefix(self) -> str:
        """沙盒專屬的重試排程前綴 `AutoSDD_OldWinCloseSbx_<沙盒根 8 碼>_`，寫進沙盒自己的
        `traces/oldwin/task_prefix`（資料檔；`oldwin_sched.task_prefix` 讀它，不開環境變數鉤）。
        沙盒的 trace_dir 本來就與真機分開，所以不會與真的 `AutoSDD_OldWinClose_*` 混在一起。"""
        prefix = f"AutoSDD_OldWinCloseSbx_{uuid.uuid5(uuid.NAMESPACE_URL, str(self.root)).hex[:8]}_"
        self.write_file("traces/oldwin/task_prefix", prefix + "\n")
        return prefix

    def _disarm_oldwin_tasks(self) -> list[str]:
        """沙盒若登記過舊窗重試排程（有 `task_prefix` 檔），cleanup 時全數撤掉並回報剩餘。"""
        marker = self.root / "traces" / "oldwin" / "task_prefix"
        if not marker.is_file():
            return []
        prefix = marker.read_text(encoding="utf-8").strip()
        try:
            import schedule_backend  # noqa: PLC0415 — lazy
            backend = schedule_backend.select()
            for name in backend.list_jobs(prefix) or []:
                backend.disarm(name)
            left = backend.list_jobs(prefix) or []
        except Exception as exc:  # noqa: BLE001 — 查不到不能假裝乾淨
            return [f"RESIDUE oldwin-tasks 量不到：{type(exc).__name__}: {exc}"]
        return [f"RESIDUE oldwin-tasks {left}"] if left else []

    # ---- 清理 ----
    def transcript_dirs(self) -> list[Path]:
        """只認 slug 與沙盒根吻合的專案目錄（絕不碰別的專案）。"""
        base = projects_dir()
        want = slug_of(self.root)
        return [d for d in (base / want,) if d.is_dir()]

    def cleanup(self) -> list[str]:
        """行程樹先結束、等行程真的退出，才刪目錄；刪不掉**回報 RESIDUE**（不吞錯，案例判 fail）。

        WHY（R217 DEF-03；ARC E4c／SA §4.3 實證本機殘留 5 個孤兒逐字稿目錄）：舊版只 `proc.kill()`
        本體、`rmtree(ignore_errors=True)` 吞掉一切錯誤，目錄 mtime 還晚於案例結束時間——claude 的
        子孫行程在 cleanup 之後仍在寫逐字稿。所以順序是：①連子孫一起砍（`kill_tree`）②等行程退出
        （≤ 5 秒）③才 rmtree，且逐字稿目錄與沙盒根一樣要驗證確實不在了。"""
        notes: list[str] = []
        for pr in self.procs:
            try:
                if pr.poll() is None:
                    kill_tree(pr)
                    notes.append(f"killed pid {pr.pid}")
            except OSError:
                pass
        deadline = time.monotonic() + PROC_EXIT_WAIT_S
        for pr in self.procs:
            try:
                pr.wait(timeout=max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                notes.append(f"RESIDUE process pid {pr.pid} still alive")
        try:
            gone = cleanup_handoff_for(self.sid)
            if gone:
                notes.append(f"handoff removed {len(gone)}")
        except ValueError:
            pass
        notes += self._disarm_oldwin_tasks()
        for d in self.transcript_dirs():
            notes += _remove_tree(d, "transcript-dir")
        return notes + _remove_tree(self.root, "sandbox")


def _writable_then_retry(func, path, _exc_info) -> None:
    """`rmtree` 的錯誤處理：唯讀檔（git 物件）先去唯讀再重試；仍失敗就把錯誤往外拋。"""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _remove_tree(path: Path, kind: str, attempts: int = 5) -> list[str]:
    """刪目錄並**驗證**它真的不在；刪不掉回 `RESIDUE <kind> <path>: <最後的錯誤>`（絕不吞錯）。"""
    last = ""
    for _ in range(attempts):
        try:
            kwarg = "onexc" if sys.version_info >= (3, 12) else "onerror"  # onerror 自 3.12 棄用
            shutil.rmtree(path, **{kwarg: _writable_then_retry})
        except OSError as exc:
            last = f"{type(exc).__name__}: {exc}"
        if not path.exists():
            return []
        time.sleep(0.4)
    return [f"RESIDUE {kind} {path}" + (f": {last}" if last else "")]


def kill_tree(proc: subprocess.Popen) -> None:
    """連同子行程樹一起砍（只砍我們自己 spawn 的這個 pid 的樹）。Windows 用 `taskkill /T /F`；
    POSIX 砍行程群組（`driver.run_claude` 以 `start_new_session` 開，群組＝它的樹）。"""
    if os.name == "nt":
        subprocess.run(  # noqa: S603
            ["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True,  # noqa: S607
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
    else:
        try:
            if os.getpgid(proc.pid) == proc.pid:  # 只在它是群組領頭時砍群組（否則會砍到呼叫者）
                os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
    try:
        proc.kill()
    except OSError:
        pass


def sweep_orphans(*, projects: Path | None = None, sessions: Path | None = None,
                  tmp_root: Path | None = None, dry_run: bool = False) -> dict:
    """清孤兒沙盒逐字稿目錄（DES §7 DEF-03；`realverify sweep`）。目錄名含 `AutoSDD-RV-sbx-`（沙盒根
    前綴的 slug）∧ 對應沙盒根已不存在 ∧ `~/.claude/sessions/*.json` 沒有任何 `cwd` 指向它 ⇒ 刪；任一
    不成立 ⇒ 留。回 `{removed: [名], kept: [(名, 原因)]}`；`dry_run` 只列不刪。只動 `projects` 下
    名稱符合前綴者——別的專案絕不碰。"""
    from lib.sessionctl import procstop  # noqa: PLC0415 — lazy：避免載入時的套件相依

    base = Path(projects) if projects is not None else projects_dir()
    tmp = Path(tmp_root) if tmp_root is not None else Path(tempfile.gettempdir())
    mark = slug_of(SANDBOX_PREFIX)
    live_roots = {slug_of(p) for p in tmp.glob(f"{SANDBOX_PREFIX}*") if p.is_dir()}
    cwd_slugs = {slug_of(row["cwd"]) for row in procstop.registry_rows(sessions)
                 if isinstance(row.get("cwd"), str)}
    out: dict = {"removed": [], "kept": []}
    for folder in sorted(base.glob("*")) if base.is_dir() else []:
        if not folder.is_dir() or mark not in folder.name:
            continue
        if folder.name in live_roots:
            out["kept"].append((folder.name, "沙盒根仍存在"))
        elif any(s == folder.name or s.startswith(folder.name + "-") for s in cwd_slugs):
            out["kept"].append((folder.name, "登記檔 cwd 指向它（有行程在用）"))
        elif dry_run:
            out["removed"].append(folder.name)
        elif not _remove_tree(folder, "orphan"):
            out["removed"].append(folder.name)
        else:
            out["kept"].append((folder.name, "刪除失敗（RESIDUE）"))
    return out
