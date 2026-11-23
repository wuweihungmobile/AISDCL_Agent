"""沙盒專案：repo 外的唯一暫存目錄＋身分檔＋git init＋`.claude/settings.json`＋清理。

CLAUDE_PROJECT_DIR 的語意（實測 2026-11-18）：在沙盒裡開的 claude，CC 會把它設成**沙盒根**。
repo 的 `_hook_launcher.py` 靠它找目標腳本（`<root>/.claude/hooks/x.py`）⇒ 在沙盒中缺檔
＝**fail-open exit 0，永遠假綠**。所以沙盒的 hook 條目一律「venv 直譯器＋repo
腳本絕對路徑」直接 spawn，
不經啟動器（repo 的守衛腳本以 `__file__` 找 repo，不依賴 CLAUDE_PROJECT_DIR）。

副作用隔離（RealVerify_SideEffect_Isolation DES §3.1／§4.3／§5.2，REQ-SE-01／23）：沙盒**先登記帳列、
後建目錄**；建好第一個動作就是寫身分檔（L1 判準只吃目標自帶的資料）；`env()` 把 7 個居所鍵全指到家目錄
之下、通知關、哨兵關，案例不得再有「指回真居所」的出口（`real_traces` 已撤）。
"""  # noqa: E501

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
from datetime import datetime
from pathlib import Path

from lib import sandbox_scope

from . import leases

REPO = Path(__file__).resolve().parents[3]
SANDBOX_PREFIX = sandbox_scope.SBX_PREFIX
PROBE_HOOK_REL = ".claude/rv_probe_hook.py"
PROC_EXIT_WAIT_S = 5.0  # cleanup 砍樹後等行程真的退出的上限（DEF-03）

#: 7 個居所鍵 → 家目錄下的目錄名（**單一表**：`Sandbox.env()` 與 `LOCAL_EXCLUDES` 都由它推得，不手抄；  # noqa: E501
#: 鍵集合與 `endurance_env.RESIDENCE_KEYS` 相等由測試核對，D-23）。
RESIDENCE_DIRS: dict[str, str] = {
    "AUTOSDD_TRACE_DIR": "traces", "AUTOSDD_HANDOFF_DIR": "handoff", "AUTOSDD_HANDBACK_DIR": "handback",  # noqa: E501
    "AUTOSDD_PLAN_DIR": "plans", "AUTOSDD_QUOTA_CACHE_DIR": "qcache",
    "AUTOSDD_CONTEXT_FEED_DIR": "context_feed", "AUTOSDD_SI_DIR": "selfimproving",
}
#: 沙盒 git 的 `info/exclude`（一次寫入，D-23）：身分檔、7 個居所、替身 `bin/` 與其設定檔。沙盒建好後  # noqa: E501
#: 工作樹恆為乾淨，`park` 的 `spawn_preflight` 與 `handoff._refusals` 才會放行。
LOCAL_EXCLUDES: tuple[str, ...] = (
    "/" + sandbox_scope.IDENTITY_NAME, *(f"/{name}/" for name in RESIDENCE_DIRS.values()),
    "/bin/", "/fakeclaude.*",
)
#: 案例 env 輔助函式可設、但**不屬 job 環境允許表**的鍵（鍵→WHY）。AST 鎖（`test_realverify_se_locks`）：  # noqa: E501
#: `Sandbox.env()` 與案例 env 輔助函式設定的每一鍵 ⊆ `endurance_env.JOB_ENV_KEYS` ∪ 本表；新鍵未分類即紅。  # noqa: E501
SANDBOX_LOCAL_ONLY: dict[str, str] = {
    "PYTHONUTF8": "只影響案例子行程的輸出編碼", "PYTHONDONTWRITEBYTECODE": "免得沙盒工作樹被 .pyc 弄髒",  # noqa: E501
    "TEMP": "把暫存目錄導到沙盒（只影響被測行程）", "TMP": "同 TEMP",
    "USERPROFILE": "沙盒家目錄（只影響被測行程）", "HOME": "同 USERPROFILE",
    "CLAUDE_CODE_SESSION_ID": "讓被測行程認得自己的沙盒 sid", "CLAUDE_CONFIG_DIR": "沙盒內的假憑證家",  # noqa: E501
    "HTTPS_PROXY": "把額度取數導到本機替身", "SSL_CERT_FILE": "替身 CA", "AUTOSDD_UNATTENDED": "模擬無人窗口",  # noqa: E501
    "AUTOSDD_QUOTA_MIN_DWELL_SECONDS": "免 300 s 停留", "AUTOSDD_QUOTA_PACE_FAR": "配速床參數（行程內）",  # noqa: E501
    "AUTOSDD_QUOTA_MAX_FANOUT": "配速床參數（行程內）", "RV_SHIM_LOG": "替身記錄檔", "RV_STOP_BLOCK": "探針 hook 開關",  # noqa: E501
    "REQUESTS_CA_BUNDLE": "替身 CA（requests 系）", "ANTHROPIC_MODEL": "沙盒被測行程的模型選擇",
    "AUTOSDD_PARK_GUARD_OFF": "只關額度停工推回（Stop hook 面，行程內）",
}

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


# ── 真環境位置的**唯讀**入口：realverify 內 `Path.home()`／`".autosdd"` 字面只准住這幾個檔（鎖＝
# `test_realverify_se_locks`）。想讀真痕跡做比對的案例一律經這裡，不得自己拼路徑（REQ-SE-23）。
def real_home() -> Path:
    return Path.home()


def real_autosdd(*parts: str) -> Path:
    """真 `~/.autosdd`（**只准讀**：比對真機痕跡、快照用；沙盒案例的寫入一律走 `Sandbox.env()` 的居所）。"""  # noqa: E501
    return real_home().joinpath(".autosdd", *parts)


def claude_home() -> Path:
    return real_home() / ".claude"


def projects_dir() -> Path:
    return claude_home() / "projects"


def kept_dir() -> Path:
    """失敗證據保留根目錄（持久，不在沙盒內；`Sandbox.preserve` 的去處）。"""
    return real_autosdd("realverify_kept")


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


def cleanup_handoff_for(sid: str, base: Path) -> list[str]:
    """刪 `<base>/<sid>*`（只刪檔名以該 sid 開頭者）；回刪掉的檔名。sid 必須是完整 UUID，防誤刪別人的。
    `base` 必填：交接包居所現在一律是沙盒自己的 `handoff/`（REQ-SE-23 撤掉真目錄預設）。"""  # noqa: E501
    if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", sid or ""):
        raise ValueError(f"sid 非完整 UUID，拒絕清理交接包：{sid!r}")
    gone: list[str] = []
    if not base.is_dir():
        return gone
    for p in base.iterdir():
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


def write_excludes(repo_root: Path, lines: tuple[str, ...] = LOCAL_EXCLUDES) -> None:
    """把樣式追加進 `<根>/.git/info/exclude`（冪等；D-23 單一輔助函式，正式目標替身 repo 也用它）。"""  # noqa: E501
    path = Path(repo_root) / ".git" / "info" / "exclude"
    path.parent.mkdir(parents=True, exist_ok=True)
    have = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    fresh = [ln for ln in lines if ln not in have.splitlines()]
    if fresh:
        path.write_text(have + ("" if have.endswith("\n") or not have else "\n") + "\n".join(fresh) + "\n",  # noqa: E501
                        encoding="utf-8", newline="\n")


def reserve_home(sid: str, *, prefix: str = SANDBOX_PREFIX, now: datetime | None = None) -> Path:
    """沙盒家目錄：**先登記帳列（intent）後 mkdir**，建好第一個動作寫身分檔（D-1；mkdtemp 無法先登記，
    所以自己決定名字）。同時登記逐字稿目錄與「命令列含 sid／根的行程」兩列（被測產品做的事以它們涵蓋）。"""  # noqa: E501
    tmp = Path(tempfile.gettempdir()).resolve()
    for _ in range(8):
        home = tmp / f"{prefix}{uuid.uuid4().hex[:8]}"
        leases.track_kind("sandbox_root", home)
        leases.track_kind("transcript_dir", projects_dir() / slug_of(home))
        leases.track_process([sid, str(home)])
        try:
            home.mkdir()
        except FileExistsError:  # 8 碼撞名幾乎不可能；真撞到就把剛登記的列結掉再換一個
            for kind, ident in (("sandbox_root", home), ("transcript_dir", projects_dir() / slug_of(home)),  # noqa: E501
                                ("process", f"sid:{sid}")):
                leases.settle(kind, ident)
            continue
        sandbox_scope.write_identity(home, run_id=leases.current_run_id(), sid=sid, owner_pid=os.getpid(),  # noqa: E501
                                     now=now or datetime.now().astimezone())
        leases.made("sandbox_root", home)
        return home
    raise FileExistsError("連續 8 次建不出不撞名的沙盒目錄")


@dataclass
class Sandbox:
    root: Path
    sid: str = field(default_factory=lambda: str(uuid.uuid4()))
    settings: dict = field(default_factory=lambda: {"hooks": {}})
    procs: list = field(default_factory=list)  # 只殺自己 spawn 的 Popen
    used_resume: bool = False

    @property
    def home(self) -> Path:
        """家目錄：身分檔與 7 個居所所在處（一般沙盒＝根；worktree 沙盒＝外層，見 `interactive`）。"""  # noqa: E501
        return self.root

    # ---- 建立 ----
    @classmethod
    def create(cls, probe_hook: bool = True) -> Sandbox:
        sid = str(uuid.uuid4())
        root = reserve_home(sid).resolve()
        sb = cls(root=root, sid=sid)
        (root / ".claude").mkdir()
        _git(["init", "-q"], root)
        write_excludes(root)
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
        """7 居所鍵全指家目錄之下、通知關、哨兵關（REQ-SE-23）。要開哨兵／通知的案例自己 `extra` 覆寫，
        且那是 job 環境允許表之外的行為——登記排程時會被 `job_env_argv` 擋下（只准關閉值，D-20）。"""  # noqa: E501
        e = {k: v for k, v in os.environ.items() if k not in _DROP_ENV}
        e["PYTHONUTF8"] = "1"
        for key, name in RESIDENCE_DIRS.items():
            e[key] = str(self.home / name)
        e["AUTOSDD_DESKTOP_NOTIFY"] = ""
        e["AUTOSDD_SENTINEL_OFF"] = "1"
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
        if (self.home / "traces").is_dir():
            shutil.copytree(self.home / "traces", dest / "traces", dirs_exist_ok=True)
            got.append("traces")
        return got

    # ---- 舊視窗關閉（oldwin）的沙盒前綴 ----
    def oldwin_prefix(self) -> str:
        """沙盒專屬的重試排程前綴 `AutoSDD_OldWinCloseSbx_<沙盒根 8 碼>_`，寫進沙盒自己的
        `traces/oldwin/task_prefix`（資料檔；`oldwin_sched.task_prefix` 讀它，不開環境變數鉤）。
        沙盒的 trace_dir 本來就與真機分開，所以不會與真的 `AutoSDD_OldWinClose_*` 混在一起。"""
        prefix = f"AutoSDD_OldWinCloseSbx_{uuid.uuid5(uuid.NAMESPACE_URL, str(self.root)).hex[:8]}_"
        marker = self.home / "traces" / "oldwin" / "task_prefix"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(prefix + "\n", encoding="utf-8", newline="\n")
        return prefix

    def _disarm_oldwin_tasks(self) -> list[str]:
        """薄殼（REQ-SE-34）：沙盒登記過舊窗重試排程（有 `task_prefix` 檔）就委派 `leases.revoke_oldwin`
        全數撤掉並回報剩餘。"""  # noqa: E501
        marker = self.home / "traces" / "oldwin" / "task_prefix"
        if not marker.is_file():
            return []
        try:
            left = leases.revoke_oldwin(marker.read_text(encoding="utf-8").strip())
        except Exception as exc:  # noqa: BLE001 — 查不到不能假裝乾淨
            return [f"RESIDUE oldwin-tasks 量不到：{type(exc).__name__}: {exc}"]
        return [f"RESIDUE oldwin-tasks {left}"] if left else []

    # ---- 清理 ----
    def _drop_dead_registry_rows(self) -> list[str]:
        return _drop_dead_registry_rows_in(claude_home() / "sessions", [self.root, self.home])

    def transcript_dirs(self) -> list[Path]:
        """只認 slug 與沙盒根吻合的專案目錄（絕不碰別的專案）。"""
        base = projects_dir()
        want = slug_of(self.root)
        return [d for d in (base / want,) if d.is_dir()]

    def cleanup(self) -> list[str]:
        """第一步撤租約（拆到一半時到點的 job 必被 L1 拒，D-2）；行程樹先結束、等行程真的退出，才刪目錄；
        刪不掉**回報 RESIDUE**（不吞錯，案例判 fail）。刪乾淨的項目在帳上結帳，RESIDUE 者留給下次重放。

        WHY（R217 DEF-03；ARC E4c／SA §4.3 實證本機殘留 5 個孤兒逐字稿目錄）：舊版只 `proc.kill()`
        本體、`rmtree(ignore_errors=True)` 吞掉一切錯誤，目錄 mtime 還晚於案例結束時間——claude 的
        子孫行程在 cleanup 之後仍在寫逐字稿。所以順序是：①連子孫一起砍（`kill_tree`）②等行程退出
        （≤ 5 秒）③才 rmtree，且逐字稿目錄與沙盒根一樣要驗證確實不在了。"""  # noqa: E501
        notes: list[str] = []
        try:
            sandbox_scope.revoke(self.home)
        except Exception:  # noqa: BLE001 — 身分檔已不在／讀不懂＝本來就沒有租約可撤
            pass
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
        left = leases.revoke_items([("process", f"sid:{self.sid}")])  # 產品自己開的視窗／行程（D-8）  # noqa: E501
        notes += [f"RESIDUE process {i}" for i in left]
        notes += self._disarm_oldwin_tasks()
        notes += self._drop_dead_registry_rows()
        for d in self.transcript_dirs():
            notes += _remove_tree(d, "transcript-dir")
        for base in dict.fromkeys((self.root, self.home)):  # worktree 沙盒另有外層的 slug 列
            slug_dir = projects_dir() / slug_of(base)
            if not slug_dir.exists():
                leases.settle("transcript_dir", slug_dir)
        notes += _remove_tree(self.root, "sandbox")
        if self.home != self.root:
            notes += _remove_tree(self.home, "sandbox-home")
        if not self.home.exists():
            leases.settle("sandbox_root", self.home)
        return notes


def _drop_dead_registry_rows_in(
    folder: Path, bases: list[Path], *, wait_s: float = 3.0
) -> list[str]:
    """刪 `folder`（harness 行程登記目錄）下 cwd 落在沙盒內、行程已不在的 `<pid>.json`。

    WHY（RV-SE11／sessionctl_watch 的 SIDE-EFFECT LEAK）：被我們強殺（`taskkill /F`）的 claude
    沒機會自己撤登記檔，快照在 cleanup 之後量到「sessions 多一檔、字樣含沙盒」；檔案要等下一次
    別的 claude 啟動才被清掉＝洩漏判定取決於時序。登記檔是我們殺掉的行程的殘留，由我們收。
    活著的行程一律不動。"""  # noqa: E501
    keys = [os.path.normcase(str(b)) for b in bases]
    notes: list[str] = []
    deadline = time.monotonic() + wait_s
    while True:
        pending = False
        try:
            files = sorted(folder.glob("*.json"))
        except OSError:
            return notes
        for p in files:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            cwd = data.get("cwd") if isinstance(data, dict) else None
            norm = os.path.normcase(cwd) if isinstance(cwd, str) else ""
            if not any(norm == k or norm.startswith(k.rstrip(os.sep) + os.sep) for k in keys):
                continue
            raw = data.get("pid")
            pid = raw if isinstance(raw, int) else (int(p.stem) if p.stem.isdigit() else None)
            if pid is not None and sandbox_scope.proc_probe(pid)[0]:
                pending = True
                continue
            try:
                p.unlink(missing_ok=True)
            except OSError as exc:
                notes.append(f"RESIDUE registry-row {p}: {type(exc).__name__}: {exc}")
        if not pending or time.monotonic() >= deadline:
            return notes
        time.sleep(0.3)


def _writable_then_retry(func, path, _exc_info) -> None:
    """`rmtree` 的錯誤處理：唯讀檔（git 物件）先去唯讀再重試；仍失敗就把錯誤往外拋。"""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _remove_tree(path: Path, kind: str, attempts: int = 5) -> list[str]:
    """刪目錄並**驗證**它真的不在；刪不掉回 `RESIDUE <kind> <path>: <最後的錯誤>`（絕不吞錯）。"""
    last = ""
    identity = _read_identity_bytes(path)
    for _ in range(attempts):
        try:
            kwarg = "onexc" if sys.version_info >= (3, 12) else "onerror"  # onerror 自 3.12 棄用
            shutil.rmtree(path, **{kwarg: _writable_then_retry})
        except OSError as exc:
            last = f"{type(exc).__name__}: {exc}"
        if not path.exists():
            return []
        time.sleep(0.4)
    _restore_identity(path, identity)
    return [f"RESIDUE {kind} {path}" + (f": {last}" if last else "")]


def _read_identity_bytes(path: Path) -> bytes | None:
    try:
        return (path / sandbox_scope.IDENTITY_NAME).read_bytes()
    except OSError:
        return None


def _restore_identity(path: Path, identity: bytes | None) -> None:
    """刪不掉根（例：行程 cwd 卡住）時，`rmtree` 已先清空內容、連身分檔一起沒了：把身分檔寫回。

    WHY（E2E-SE-18）：無身分檔的殘留目錄在發現式掃描只剩 mtime 判準（< `LEASE_CAP` 一律 live），
    主人已死的孤兒因此變成「查無主人、看似活著」，之後 sweep 永遠不處置。
    身分檔留著＝主人可驗證已死，行程放開 cwd 後下一次 sweep 即可刪。"""
    if identity is None or not path.is_dir() or (path / sandbox_scope.IDENTITY_NAME).exists():
        return
    try:
        (path / sandbox_scope.IDENTITY_NAME).write_bytes(identity)
    except OSError:
        pass


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
    """薄殼（REQ-SE-34）：清孤兒沙盒逐字稿目錄（`realverify sweep`）——判準與刪除都在
    `leases_discover.sweep_projects`。回 `{removed: [名], kept: [(名, 原因)]}`。"""
    from . import leases_discover  # noqa: PLC0415 — lazy：leases_discover 頂層 import 本檔
    return leases_discover.sweep_projects(projects=projects, sessions=sessions, tmp_root=tmp_root,
                                          dry_run=dry_run)
