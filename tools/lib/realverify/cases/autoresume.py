# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""autoresume 家族：RV-A1（AutoResumeService 經真 engine 真跑出結果）。

第一波 WP-7 只驗到排程觸發與自拆（engine 用壞 yaml 免耗 token）。本案例補另一半：
真 `python -m autoclaude`（Kernel＋AutoResumeService＋PtyExecutor）→ 真 `claude -p --model haiku`，
一步 playbook 跑完 rc 0、步驟輸出命中 expected_output_regex、成功收尾後 checkpoint 已清（DEF-200-510）；
反向：壞 yaml 一律 rc≠0（零 token）。
"""  # noqa: E501

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

from ..driver import EnvMissing, find_claude
from ..sandbox import REPO, venv_python
from . import CaseContext, case

_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_AC = REPO / "AutoClaude"

_CONFIG = """\
claude:
  command: claude
  extra_args: ["--model", "haiku"]
minimax:
  enable_kernel_brain: false
executor:
  backend: pty
storage:
  mode: yaml_only
playbook:
  goal_synthesis_enabled: false
token_guard:
  enabled: true
  auto_resume: false
notification:
  enabled: false
log_dir: {run}/logs
checkpoint_dir: {run}/checkpoints
"""

_PLAYBOOK = """\
version: "1.0"
project: "rv_a1"
global_goal: "realverify A1"
tasks:
  - step_id: "T01"
    name: "echo"
    prompt: |
      Reply with exactly this keyword and nothing else: [RVA1_DONE]
    expected_output_regex: "\\\\[RVA1_DONE\\\\]"
    max_retries: 1
"""


_PLAYBOOK2 = """\
version: "1.0"
project: "rv_a1_two"
global_goal: "realverify A1 resume"
tasks:
  - step_id: "T01"
    name: "one"
    prompt: |
      Reply with exactly this keyword and nothing else: [RVA1_ONE]
    expected_output_regex: "\\\\[RVA1_ONE\\\\]"
    max_retries: 1
  - step_id: "T02"
    name: "two"
    prompt: |
      Reply with exactly this keyword and nothing else: [RVA1_TWO]
    expected_output_regex: "\\\\[RVA1_TWO\\\\]"
    max_retries: 1
"""
_USAGE = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def _find_transcript(sb) -> Path:
    from ..transcript import find_transcript
    p = find_transcript(sb.sid)
    if p is None:
        raise FileNotFoundError(f"沙盒 sid {sb.sid} 沒有逐字稿")
    return p


def _first_assistant_midpoint(tpath: Path) -> str:
    """reset_at＝第一筆 assistant 與第二筆 assistant 之間的時刻（讓錨點＝第一筆、首個請求＝第二筆）。"""  # noqa: E501
    ts = []
    for ln in tpath.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if d.get("type") == "assistant" and isinstance(d.get("timestamp"), str):
            ts.append(datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")))
    if len(ts) < 2:
        raise AssertionError(f"沙盒逐字稿 assistant 記錄不足 2 筆：{len(ts)}")
    return (ts[0] + (ts[1] - ts[0]) / 2).isoformat()


def _run_py(code: str, *args: str, env: dict) -> dict:
    r = subprocess.run([venv_python(), "-I", "-c", code, *args], env=env, capture_output=True,  # noqa: S603
                       creationflags=_NOWIN, encoding="utf-8", errors="replace", timeout=60)
    if r.returncode != 0:
        raise AssertionError(f"被測函式子行程 rc={r.returncode}：{r.stderr[-400:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def _engine(sb, cfg: str, pb: str, timeout: int) -> subprocess.CompletedProcess:
    env = sb.env()
    env.pop("AUTOSDD_UNATTENDED", None)
    return subprocess.run([venv_python(), "-m", "autoclaude", pb, "--config", cfg], cwd=str(sb.root),  # noqa: E501, S603
                          env=env, capture_output=True, timeout=timeout, creationflags=_NOWIN,
                          encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)


@case("RV-A1", "autoresume", refs=("DEF-200-510", "PRD-4.5.5"))
def rv_a1(ctx: CaseContext) -> None:
    """真 engine（AutoResumeService.run）＋真 `claude -p`：一步 playbook rc 0、輸出命中 regex、checkpoint 清空；
    壞 yaml ⇒ rc≠0（反向）。"""  # noqa: E501
    if not (_AC / "autoclaude" / "main.py").is_file():
        raise EnvMissing(f"找不到 AutoClaude 引擎：{_AC}")
    sb = ctx.sandbox(probe_hooks=False)
    run_dir = sb.root / "run"
    (run_dir / "checkpoints").mkdir(parents=True)
    sb.write_file(".gitignore", "run/\n")  # 開機自檢不變式 9：檢查點目錄在 git 樹內就必須被 ignore
    cfg = sb.write_file("config.yaml", _CONFIG.format(run=run_dir.as_posix()))
    pb = sb.write_file("playbook.yaml", _PLAYBOOK)
    bad = sb.write_file("bad.yaml", "version: '1.0'\nproject: x\n")  # 缺 tasks：_validate_playbook_format 必拒  # noqa: E501

    rb = _engine(sb, str(cfg), str(bad), 120)
    ctx.check(rb.returncode != 0, f"壞 playbook 應 rc≠0，實得 {rb.returncode}")

    r = _engine(sb, str(cfg), str(pb), 600)
    tail = f"stdout={r.stdout[-700:]!r} stderr={r.stderr[-900:]!r}"
    if r.returncode != 0 and re.search(r"claude.*(not found|找不到)|No such file", tail, re.I):
        raise EnvMissing(f"claude 執行檔不可用：{tail}")
    ctx.check(r.returncode == 0, f"engine rc={r.returncode}（預期 0）：{tail}")
    logs = sorted((run_dir / "logs").glob("*")) if (run_dir / "logs").is_dir() else []
    blob = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in logs if p.is_file())
    ctx.check("RVA1_DONE" in blob or "RVA1_DONE" in r.stdout, "引擎 log／stdout 都沒有步驟輸出 RVA1_DONE（沒真的跑出結果）")  # noqa: E501
    left = [p.name for p in (run_dir / "checkpoints").rglob("*.json") if p.is_file()]  # .jsonl 是 KB／進度指標，不是 checkpoint  # noqa: E501
    ctx.check(not left, f"成功收尾後 checkpoint 應已清除（DEF-200-510），殘留：{left}")
    ctx.evidence(f"RV-A1 engine rc=0；log 檔 {len(logs)} 個含 RVA1_DONE；checkpoint 殘留 0；壞 yaml rc={rb.returncode}")  # noqa: E501

    # ── PRD §11.3 ①：真 halt → 重啟接續「正確的中斷步驟」 ──
    run2 = sb.root / "run2"
    (run2 / "checkpoints").mkdir(parents=True)
    sb.write_file(".gitignore", "run/\nrun2/\n")
    halt_cfg = sb.write_file("config_halt.yaml", _CONFIG.format(run=run2.as_posix()).replace(
        "  auto_resume: false", "  auto_resume: false\n  resume_delay_minutes: 0\n  compact_threshold_pct: 0.5\n  halt_threshold_pct: 1.0"))  # noqa: E501
    ok_cfg = sb.write_file("config_ok.yaml", _CONFIG.format(run=run2.as_posix()))
    pb2 = sb.write_file("playbook2.yaml", _PLAYBOOK2)
    h = _engine(sb, str(halt_cfg), str(pb2), 600)
    hb = f"rc={h.returncode} stdout={h.stdout[-500:]!r}"
    cks = [p for p in (run2 / "checkpoints").rglob("*.json") if p.is_file()]
    ctx.check(h.returncode != 0 and bool(cks), f"極低 halt 門檻應使引擎 halt（rc≠0）並留下 checkpoint：{hb} cks={cks}")  # noqa: E501
    ck = json.loads(cks[0].read_text(encoding="utf-8"))
    step_idx = ck.get("step_idx")
    ctx.check(isinstance(step_idx, int) and step_idx >= 0, f"checkpoint 沒有 step_idx：{ck}")
    logs2 = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (run2 / "logs").glob("*") if p.is_file())  # noqa: E501
    done_before = {k for k in ("RVA1_ONE", "RVA1_TWO") if k in logs2}
    r2 = _engine(sb, str(ok_cfg), str(pb2), 600)
    ctx.check(r2.returncode == 0, f"重啟（正常門檻）應 rc 0：rc={r2.returncode} {r2.stdout[-500:]!r}")  # noqa: E501
    # 中斷點之前的步驟不得重跑：checkpoint 記的 step_idx＝0 時 T01 才允許重跑
    log_all = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (run2 / "logs").glob("*") if p.is_file())  # noqa: E501
    ctx.check("RVA1_TWO" in log_all, "重啟後最後一步 T02 沒有跑出結果")
    if step_idx >= 1:
        ctx.check(log_all.count("Reply with exactly this keyword and nothing else: [RVA1_ONE]") <= 1,  # noqa: E501
                  f"checkpoint step_idx={step_idx} 但 T01 被重跑")
    ctx.evidence(f"RV-A1 §11.3① halt rc={h.returncode} checkpoint step_idx={step_idx} 先前已出現={sorted(done_before)}；重啟 rc=0 且 T02 跑完")  # noqa: E501

    # ── PRD §11.3 ②：喚醒成本落帳（真逐字稿；量不到＝measured:false＋null，不是 0）──
    rr = ctx.run_claude(sb, "Reply with exactly: ok")
    ctx.check(rr.rc == 0, f"沙盒 claude -p rc={rr.rc}")
    rr2 = ctx.run_claude(sb, "Reply with exactly: again")
    ctx.check(rr2.rc == 0, f"沙盒 claude -p -r rc={rr2.rc}")
    tpath = _find_transcript(sb)
    rec_path = sb.root / "traces" / "resume_cost.jsonl"
    code = ("import sys,json;sys.path.insert(0,sys.argv[1]);import resume_cost as rc;from pathlib import Path;"  # noqa: E501
            "s=json.loads(sys.argv[2]);print(json.dumps(rc.record_window(s,Path(sys.argv[3]))))")
    state = {"session_id": sb.sid, "relay_seq": 0, "transcript": str(tpath), "reset_at": _first_assistant_midpoint(tpath)}  # noqa: E501
    good = _run_py(code, str(REPO / "tools" / "lib"), json.dumps(state), str(rec_path), env=sb.env())  # noqa: E501
    ctx.check(good.get("measured") is True and all(type(good[k]) is int for k in _USAGE) and isinstance(good.get("model"), str),  # noqa: E501
              f"真逐字稿應量到首請求 usage（int）與 model：{good}")
    miss = _run_py(code, str(REPO / "tools" / "lib"), json.dumps({**state, "transcript": str(sb.root / "nope.jsonl")}), str(rec_path), env=sb.env())  # noqa: E501
    ctx.check(miss.get("measured") is False and all(miss[k] is None for k in _USAGE) and miss.get("reason") == "transcript-missing",  # noqa: E501
              f"量不到必須 measured:false 且數值欄 null（不得 0）：{miss}")
    lines = [json.loads(x) for x in rec_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    ctx.check(len(lines) == 2, f"落帳應兩行，實得 {len(lines)}")
    ctx.evidence(f"RV-A1 §11.3② measured={good['model']} cache_creation={good['cache_creation_input_tokens']}；缺逐字稿＝measured:false＋null")  # noqa: E501

    # ── PRD §11.3 ③：SESSION_RESUME 不可用（逐字稿被刪）⇒ 自動降級 FRESH_SESSION_WITH_STATE 並完成任務 ──  # noqa: E501
    plan = sb.write_file(f"{sb.sid}_plan.md", "# 任務書\n## 3. 做這件事\n在目前工作目錄建立檔案 fresh_ok.txt，內容為 FRESH_OK。完成後寫 handback。\n")  # noqa: E501
    tpath.unlink()
    rcode = ("import sys,json;sys.path.insert(0,sys.argv[1]);import os;from pathlib import Path;"
             "from sessionctl import switch;r=switch.choose_resume_route(sys.argv[2],sys.argv[3],Path(sys.argv[4]),sys.argv[5]);"  # noqa: E501
             "print(json.dumps(r))")
    route = _run_py(rcode, str(REPO / "tools" / "lib"), find_claude(), sb.sid, str(tpath), str(plan), env=sb.env())  # noqa: E501
    ctx.check(route.get("strategy") == "FRESH_SESSION_WITH_STATE" and "-r" not in (route.get("argv") or []),  # noqa: E501
              f"逐字稿缺席應降級 FRESH 且 argv 不帶 -r：{route.get('strategy')} {route.get('reason')}")  # noqa: E501
    argv = [route["argv"][0], "--model", "haiku", *route["argv"][1:]]
    fr = subprocess.run(argv, cwd=str(sb.root), env=sb.env(), capture_output=True, timeout=420,  # noqa: S603
                        creationflags=_NOWIN, stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")  # noqa: E501
    ok = (sb.root / "fresh_ok.txt")
    ctx.check(fr.returncode == 0 and ok.is_file() and "FRESH_OK" in ok.read_text(encoding="utf-8"),
              f"FRESH 路沒有完成任務：rc={fr.returncode} 檔存在={ok.is_file()} out={fr.stdout[-300:]!r}{fr.stderr[-200:]!r}")  # noqa: E501
    hbdir = Path(str(route.get("handback") or "")).parent
    for f in (hbdir.glob(f"{sb.sid}*") if hbdir.is_dir() else []):
        f.unlink(missing_ok=True)
    ctx.evidence(f"RV-A1 §11.3③ 降級={route['strategy']}（{route['reason'][:60]}）；fresh_ok.txt 已建")  # noqa: E501
