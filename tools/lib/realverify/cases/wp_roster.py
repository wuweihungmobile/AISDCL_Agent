# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""workprogress 家族（名冊真行程）：RV-T4（E2E-WP-07 真逐字稿重放：被 TaskStop 的代理不列）、
RV-T5（E2E-WP-08 真 `claude -p` 長工具回合：擁有者以登記檔判活、結束後不再判活）。"""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

from ..driver import EnvMissing
from ..sandbox import REPO, claude_home, projects_dir, slug_of
from . import CaseContext, case
from .prd_px_lib import ev
from .sessionctl_park import PY, run

OWNER = "05d1b770-4eee-4c44-9f39-a9ae3c37f50d"
KILLED_AGENT = "ab573c773ef06f035"
_DRV = r'''
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/tools")
from lib.sessionctl import roster
snap = roster.snapshot(sys.argv[3] or None, projects_dir=Path(sys.argv[2]))
print("R=" + json.dumps([a["id"] for a in snap["agents"]]))
'''
_ALIVE = r'''
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/tools")
from lib.sessionctl import procstop
procs = procstop.list_processes()
print("A=" + json.dumps(sorted(procstop.alive_sids(procs or ()))))
'''


def _real_owner_dir() -> Path | None:
    base = projects_dir()
    for d in base.glob("*"):
        if (d / f"{OWNER}.jsonl").is_file():
            return d
    return None


def _ids(sb, projects: Path, owner: str) -> list[str]:
    p = sb.write_file("roster_drv.py", _DRV)
    # 交接包目錄指沙盒：真機上該 owner 已被交棒（~/.autosdd/handoff），會讓 quiet 代理降殘局而被隱藏，污染對照組
    env = {**sb.env(), "AUTOSDD_HANDOFF_DIR": str(sb.root / "handoff_empty")}
    out = run([PY, str(p), str(REPO), str(projects), owner], cwd=sb.root, env=env, timeout=120)
    m = re.search(r"^R=(.*)$", out.stdout, re.M)
    if out.returncode != 0 or not m:
        raise AssertionError(f"roster 子行程失敗 rc={out.returncode}\n{out.stdout[-300:]}{out.stderr[-500:]}")
    return json.loads(m.group(1))


@case("RV-T4", "workprogress", refs=("E2E-WP-07", "REQ-WP-40", "REQ-WP-01"))
def rv_t4(ctx: CaseContext) -> None:
    """真逐字稿重放：把本機真逐字稿 05d1b770 的主檔與其代理檔（含被 TaskStop 的 ab573c773ef06f035）複本放沙盒
    projects 目錄，真呼叫 `roster.snapshot`：被 TaskStop 的代理不列（killed 通知在主逐字稿、被擠出尾端也要認）；對照組
    移除主逐字稿複本 ⇒ 同一代理會被列出（證明排除靠的是主逐字稿裡的 killed 通知，不是別的原因）。"""
    src = _real_owner_dir()
    if src is None or not (src / OWNER / "subagents" / f"agent-{KILLED_AGENT}.jsonl").is_file():
        raise EnvMissing(f"本機沒有真逐字稿 {OWNER}／代理 {KILLED_AGENT}（重放母體缺件，非綠）")
    sb = ctx.sandbox(probe_hooks=False)
    proj = sb.root / "projects" / slug_of(sb.root)
    (proj / OWNER / "subagents").mkdir(parents=True)
    shutil.copy2(src / f"{OWNER}.jsonl", proj / f"{OWNER}.jsonl")
    for f in (src / OWNER / "subagents").glob(f"agent-{KILLED_AGENT}.*"):
        shutil.copy2(f, proj / OWNER / "subagents" / f.name)
    ids = _ids(sb, sb.root / "projects", OWNER)
    ctx.check(KILLED_AGENT not in ids, f"被 TaskStop 的代理不該列出：{ids}")
    (proj / f"{OWNER}.jsonl").unlink()
    ids2 = _ids(sb, sb.root / "projects", OWNER)
    ctx.check(KILLED_AGENT in ids2, f"對照組（無主逐字稿）應列出該代理，否則排除不是靠 killed 通知：{ids2}")
    ev(ctx, "killed_not_listed", f"{KILLED_AGENT} 有主逐字稿＝不列；移除主逐字稿＝列出（{ids2}）")


@case("RV-T5", "workprogress", refs=("E2E-WP-08", "REQ-WP-41", "REQ-WP-42"))
def rv_t5(ctx: CaseContext) -> None:
    """沙盒起真 `claude -p --model haiku`（提示要求以工具執行約 45 秒等待使行程存活）；在跑時以真 `procstop.alive_sids`
    判活：該行程的 sid（由 `~/.claude/sessions/<pid>.json` 登記檔取得，`kind=interactive`、`entrypoint=sdk-cli`、
    cwd＝沙盒）在 alive 內；行程結束後同一 sid 不再判活。"""
    import subprocess

    from ..driver import find_claude

    sb = ctx.sandbox(probe_hooks=False)
    exe = find_claude()
    prompt = "Use the PowerShell tool exactly once to run: Start-Sleep -Seconds 45 . Then reply DONE."
    proc = subprocess.Popen([exe, "-p", "--model", "haiku", "--session-id", sb.sid, "--allowedTools=PowerShell,Bash", prompt], cwd=str(sb.root), env=sb.env(),  # noqa: S603
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    sb.procs.append(proc)
    reg = claude_home() / "sessions"
    row = None
    t0 = time.monotonic()
    while time.monotonic() - t0 < 90 and row is None and proc.poll() is None:
        for p in reg.glob("*.json"):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if d.get("sessionId") == sb.sid:
                row = d
        time.sleep(1)
    ctx.check(row is not None, "沒有在登記檔找到本次真行程的 sessionId")
    ctx.check(row.get("entrypoint") == "sdk-cli" and Path(row.get("cwd", "")).resolve() == sb.root.resolve(), f"登記檔欄位不符：{ {k: row.get(k) for k in ('kind', 'entrypoint', 'cwd')} }")  # noqa: E501
    p = sb.write_file("alive_drv.py", _ALIVE)
    live = run([PY, str(p), str(REPO)], cwd=sb.root, env=sb.env(), timeout=120)
    m = re.search(r"^A=(.*)$", live.stdout, re.M)
    ctx.check(bool(m) and sb.sid in json.loads(m.group(1)), f"行程存活時該 sid 應在 alive 內：{live.stdout[-300:]}{live.stderr[-300:]}")
    proc.wait(timeout=150)
    time.sleep(2)
    done = run([PY, str(p), str(REPO)], cwd=sb.root, env=sb.env(), timeout=120)
    m2 = re.search(r"^A=(.*)$", done.stdout, re.M)
    ctx.check(bool(m2) and sb.sid not in json.loads(m2.group(1)), f"行程結束後該 sid 不該再判活：{done.stdout[-300:]}")
    ev(ctx, "alive_by_registry", f"行程存活時 sid {sb.sid[:8]} 在 alive（登記檔 kind={row.get('kind')} entrypoint={row.get('entrypoint')}）；結束後不在")
