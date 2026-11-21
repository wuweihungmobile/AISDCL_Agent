"""RV-PX 家族共用 helper（不登記案例）：載具 X（沙盒 `claude` 替身 shim）＋真 `python -m autoclaude` 引擎行程。

shim 只決定「CLI 輸出什麼」；被驗的引擎行程、設定載入、開機自檢、log、checkpoint 都是真的。
shim 與引擎設定、log、checkpoint 全放沙盒；PATH 不動，shim 以絕對路徑寫進沙盒 config 的 `claude.command`。"""  # noqa: E501

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..driver import EnvMissing
from ..sandbox import REPO, Sandbox

PLAYBOOK = 'version: "1.0"\nproject: "rv"\ntasks:\n  - step_id: "T01"\n    name: "n"\n    prompt: "hi"\n    expected_output_regex: "\\\\[DONE\\\\]"\n'  # noqa: E501


REAL_PLAYBOOK = ('version: "1.0"\nproject: "rv"\ntasks:\n  - step_id: "T01"\n    name: "n"\n    prompt: "Reply with exactly the text [DONE] and nothing else."\n'  # noqa: E501
                 '    expected_output_regex: "\\\\[DONE\\\\]"\n')  # noqa: E501
REAL_EXTRA_ARGS = '["--model", "haiku"]'


def real_claude() -> str:
    """沙盒外的真 `claude` CLI 路徑（找不到 ⇒ EnvMissing）。
    真 CLI 的 `--version` 不打 API、不花額度；引擎若還要跑步驟，
    則以 `REAL_PLAYBOOK`＋`REAL_EXTRA_ARGS`（haiku、一句話）走真推論。"""
    exe = shutil.which("claude")
    if not exe:
        raise EnvMissing("找不到真 claude CLI")
    return exe


@dataclass
class EngineRun:
    rc: int
    stdout: str
    stderr: str
    log: str
    seconds: float

    @property
    def text(self) -> str:
        return self.stdout + "\n" + self.stderr + "\n" + self.log


def write_shim(sb: Sandbox, version: str = "2.1.295", body: str = "echo [DONE]", name: str = "claude.cmd") -> Path:  # noqa: E501
    """Windows `.cmd` shim：`--version` 印 `<version> (Claude Code)`，其餘印 `body`。"""
    if not (REPO / ".venv" / "Scripts" / "python.exe").is_file():
        raise EnvMissing("找不到 repo .venv python（引擎載具需要）")
    shim = sb.root / "bin" / name
    shim.parent.mkdir(exist_ok=True)
    shim.write_text(f'@echo off\r\nif "%1"=="--version" (echo {version} ^(Claude Code^)) else ({body})\r\n',  # noqa: E501
                    encoding="utf-8", newline="")
    return shim


def run_engine(sb: Sandbox, *, command: str, extra_cfg: str = "", env_extra: dict | None = None,
               playbook: str = PLAYBOOK, extra_args: str = "[]", timeout: int = 180,
               claude_extra: str = "", pre=None) -> EngineRun:
    """在沙盒跑一次真引擎：`.gitignore` 先放 ckpt/logs（不變式 9）、log／checkpoint 全在沙盒。"""
    import time  # noqa: PLC0415

    sb.write_file(".gitignore", "ckpt/\nlogs/\n")
    sb.write_file("pb.yaml", playbook)
    cmd = command.replace("\\", "/")
    sb.write_file("cfg.yaml", (
        f'claude:\n  command: "{cmd}"\n  extra_args: {extra_args}\n{claude_extra}'
        f'log_dir: "{(sb.root / "logs").as_posix()}"\ncheckpoint_dir: "{(sb.root / "ckpt").as_posix()}"\n'  # noqa: E501
        "notification:\n  enabled: false\ntoken_guard:\n  auto_resume: false\n" + extra_cfg))
    if pre is not None:
        pre(sb)  # 設定檔都寫好、引擎還沒起：案例在此做基線 commit／製造髒污
    env = sb.env({"AUTOSDD_QUOTA_CACHE_DIR": str(sb.root / "qcache"), **(env_extra or {})})
    env["PYTHONPATH"] = str(REPO / "AutoClaude")
    env.pop("MINIMAX_API_KEY", None)
    t0 = time.monotonic()
    r = subprocess.run(  # noqa: S603
        [str(REPO / ".venv" / "Scripts" / "python.exe"), "-m", "autoclaude", "pb.yaml", "--config", "cfg.yaml"],  # noqa: E501
        cwd=str(sb.root), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",  # noqa: E501
        timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    logf = sb.root / "logs" / "autoclaude.log"
    log = logf.read_text(encoding="utf-8", errors="replace") if logf.is_file() else ""
    return EngineRun(r.returncode, r.stdout, r.stderr, log, time.monotonic() - t0)


PY_SHIM_SRC = r"""
import json, os, sys, time
d = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
if args[:1] == ["--version"]:
    print(open(os.path.join(d, "version.txt"), encoding="utf-8").read().strip() + " (Claude Code)")
    sys.exit(0)
cp = os.path.join(d, "calls.jsonl")
n = sum(1 for ln in open(cp, encoding="utf-8") if '"t0"' in ln) if os.path.exists(cp) else 0
script = json.load(open(os.path.join(d, "script.json"), encoding="utf-8"))
step = script[min(n, len(script) - 1)]
t0 = time.time()
with open(cp, "a", encoding="utf-8") as f:
    f.write(json.dumps({"n": n, "t0": t0, "argv": args}, ensure_ascii=False) + "\n")
if step.get("real"):
    import subprocess
    r = subprocess.run([step["real"]] + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    sys.stdout.write(r.stdout)
    sys.stdout.flush()
    with open(cp, "a", encoding="utf-8") as f:
        f.write(json.dumps({"n": n, "t1": time.time(), "real_rc": r.returncode}) + "\n")
    sys.exit(r.returncode)
if step.get("sleep"):
    time.sleep(step["sleep"])
sys.stdout.write(step.get("stdout", "[DONE]") + "\n")
sys.stdout.flush()
with open(cp, "a", encoding="utf-8") as f:
    f.write(json.dumps({"n": n, "t1": time.time()}) + "\n")
sys.exit(step.get("rc", 0))
"""


def pct_json(pct: float, result: str = "[DONE]") -> str:
    """shim 輸出：`claude -p --output-format json` 形狀，引擎由 usage÷contextWindow 推得 context%＝`pct`。"""  # noqa: E501
    used = int(pct * 10)
    usage = {"input_tokens": used, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    mu = {"m": {"contextWindow": 1000}}
    return json.dumps({"result": result, "usage": usage, "modelUsage": mu})


def write_py_shim(sb: Sandbox, script: list[dict], version: str = "2.1.295") -> Path:
    """可程式化 shim（載具 X）：`script[i]`＝第 i 次非 `--version` 呼叫的行為
    {stdout, sleep, rc}（最後一筆重複）；每次呼叫把 argv 與起訖時間記進 `bin/calls.jsonl`
    （案例據此判「呼叫幾次、間隔多久」）。"""
    if not (REPO / ".venv" / "Scripts" / "python.exe").is_file():
        raise EnvMissing("找不到 repo .venv python（引擎載具需要）")
    b = sb.root / "bin"
    b.mkdir(exist_ok=True)
    (b / "shim.py").write_text(PY_SHIM_SRC, encoding="utf-8")
    (b / "version.txt").write_text(version, encoding="utf-8")
    (b / "script.json").write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
    py = REPO / ".venv" / "Scripts" / "python.exe"
    cmd = b / "claude.cmd"
    cmd.write_text(f'@echo off\r\n"{py}" "{b / "shim.py"}" %*\r\n', encoding="utf-8", newline="")
    return cmd


def git_commit_all(sb: Sandbox, msg: str = "base") -> str:
    """沙盒 git：全部 add＋commit，回短 sha（只動沙盒 repo）。"""
    nw = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    for args in (["add", "-A"], ["commit", "-q", "-m", msg]):
        subprocess.run(["git", *args], cwd=str(sb.root), check=True, capture_output=True, creationflags=nw)  # noqa: S603,S607,E501
    out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(sb.root), capture_output=True,  # noqa: S603,S607,E501
                         text=True, encoding="utf-8", errors="replace", creationflags=nw)
    return out.stdout.strip()


def git_porcelain(sb: Sandbox) -> str:
    out = subprocess.run(["git", "status", "--porcelain"], cwd=str(sb.root), capture_output=True,  # noqa: S603,S607
                         text=True, encoding="utf-8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))  # noqa: E501
    return out.stdout


def shim_calls(sb: Sandbox) -> list[dict]:
    """`calls.jsonl` 合併成每次呼叫一筆 {n, t0, t1, argv}。"""
    p = sb.root / "bin" / "calls.jsonl"
    if not p.is_file():
        return []
    rows: dict[int, dict] = {}
    for ln in p.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            rows.setdefault(r["n"], {}).update(r)
    return [rows[k] for k in sorted(rows)]


def seed_queue(sb: Sandbox, items: list[dict], env_extra: dict | None = None) -> None:
    """用產品自己的 FileStateRepository API 把 `integration_queue` 寫進既有 checkpoint（checksum 由產品重算），並清掉 `scheduled_resume_at`
    （否則下一次引擎行程會真的等 30 分鐘到喚醒時刻）。"""  # noqa: E501
    code = (
        "import sys; sys.path.insert(0, r'{ac}')\n"
        "import autoclaude.infra.repositories.file_state_repository as m\n"
        "import autoclaude.infra.repositories.factory as fa\n"
        "F, C = m.FileStateRepository, fa.canonical_playbook_id\n"
        "pid = C('pb.yaml', mode='yaml_only')\nr = F(r'{ck}')\n"
        "cp = r.load_latest_by_playbook(pid)\n"
        "assert cp is not None, 'no checkpoint'\ncp.integration_queue = {q!r}\ncp.scheduled_resume_at = None\nr.save_checkpoint(pid, cp)\n"  # noqa: E501
    ).format(ac=REPO / "AutoClaude", ck=sb.root / "ckpt", q=items)
    r = subprocess.run([str(REPO / ".venv" / "Scripts" / "python.exe"), "-c", code], cwd=str(sb.root),  # noqa: S603,E501
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                       env=sb.env(env_extra))
    if r.returncode != 0:
        raise AssertionError(f"seed_queue 失敗：{r.stderr[-400:]}")
