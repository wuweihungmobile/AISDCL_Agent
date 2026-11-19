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
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SANDBOX_PREFIX = "AutoSDD_RV_sbx_"
PROBE_HOOK_REL = ".claude/rv_probe_hook.py"

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

    # ---- 清理 ----
    def transcript_dirs(self) -> list[Path]:
        """只認 slug 與沙盒根吻合的專案目錄（絕不碰別的專案）。"""
        base = projects_dir()
        want = slug_of(self.root)
        return [d for d in (base / want,) if d.is_dir()]

    def cleanup(self) -> list[str]:
        notes: list[str] = []
        for pr in self.procs:
            try:
                if pr.poll() is None:
                    pr.kill()
                    notes.append(f"killed pid {pr.pid}")
            except OSError:
                pass
        try:
            gone = cleanup_handoff_for(self.sid)
            if gone:
                notes.append(f"handoff removed {len(gone)}")
        except ValueError:
            pass
        for d in self.transcript_dirs():
            shutil.rmtree(d, ignore_errors=True)
        for _ in range(5):
            shutil.rmtree(self.root, ignore_errors=True)
            if not self.root.exists():
                break
            time.sleep(0.4)
        if self.root.exists():
            notes.append(f"RESIDUE sandbox {self.root}")
        return notes
