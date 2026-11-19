"""sessionctl_longwait 家族：子代理長等待 runlong／waitfor＋長前景閘（R216 WP-D；TCS-SessionSwitch-CostModel
E2E-SS-07／08、REQ-SS-10～12）。

- RV-LW1：真子行程 `sessionctl.py runlong`＋`waitfor`：pending → done 兩段判決、`.done` 內容、尾端輸出（不開 claude）。
- RV-LW2：真 hook 行程＋真實形狀 payload（取自 2026-11-19 真 `claude -p` 傾印：子代理的 PowerShell 呼叫帶 `agent_id`／
  `agent_type`、`tool_input.timeout` 單位毫秒、`run_in_background` 只在設了才出現）跑長前景閘判準矩陣。
- RV-LW3（長案）：真 `claude -p --model haiku` 主控＋前景子代理用 runlong＋waitfor 等一支 > 5 分鐘的指令；從子代理真逐字稿斷言
  相鄰記錄間隔 < 300 秒、等待後下一回合 `cache_read ≥ 0.9×前一回合上下文`、`.done` rc 0。
- RV-LW4：真 `claude -p` 子代理前景 PowerShell timeout 300000 被真 hook 擋下、同樣的主控呼叫不被擋。

RV-LW2／LW4 要求 `.claude/hooks/sessionctl_guard.py` 已含長前景閘分支；未套用 ⇒ `EnvMissing`（rc 2，不是綠）。
不 monkeypatch 被測物、不開測試用環境變數；子代理的 shell 工具在沙盒（repo 外拋棄式目錄）以 bypassPermissions 跑。
單案 token 預估：LW3 約 5 萬、LW4 約 2 萬（haiku）。
"""  # noqa: E501

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from ..driver import EnvMissing
from ..sandbox import REPO, Sandbox
from . import CaseContext, case
from .sessionctl_watch import BYPASS, NO_QUOTA, SESSIONCTL, _subagent_files

HOOK = REPO / ".claude" / "hooks" / "sessionctl_guard.py"
GATE_MATCHER = "PowerShell|Bash"
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SLEEP_S = 420  # > 5 分鐘（子代理快取壽命）：兩段 waitfor（240＋~180）才等得完


def _hook_has_gate() -> bool:
    try:
        return "longwait" in HOOK.read_text(encoding="utf-8")
    except OSError:
        return False


def _need_gate() -> None:
    if not _hook_has_gate():
        raise EnvMissing(f"{HOOK} 還沒有長前景閘分支（守衛面 diff 待主控套用）")


def _py(*argv: str, env: dict, timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SESSIONCTL), *argv], capture_output=True, encoding="utf-8",  # noqa: E501
                          errors="replace", timeout=timeout, env=env, check=False, creationflags=NOWIN)  # noqa: E501


def _last(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return lines[-1] if lines else ""


# ───────────────────────────── RV-LW1：runlong＋waitfor 真跑 ─────────────────────────────
@case("RV-LW1", "sessionctl_longwait", refs=("AT-SS-30", "AT-SS-31"))
def rv_lw1(ctx: CaseContext) -> None:
    """真跑：被等的指令睡 8 秒。waitfor --max-sec 2 ⇒ rc 0（DEF-200-622：「還沒好」是正常結果）＋`WAITFOR_VERDICT=pending`、`.done` 尚不存在；
    再 waitfor --max-sec 30 ⇒ rc 0＋尾端含子行程輸出（UTF-8 中文）＋`WAITFOR_VERDICT=done rc=0`；`.done` 內容 rc 0；runlong 自身 rc 0。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    out, done = sb.root / "long.txt", sb.root / "long.txt.done"
    code = "import time;print('開始',flush=True);time.sleep(8);print('結束')"
    proc = subprocess.Popen(  # noqa: S603
        [sys.executable, str(SESSIONCTL), "runlong", "--out", str(out), "--", sys.executable, "-c", code],  # noqa: E501
        env=sb.env(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NOWIN)  # noqa: E501
    sb.procs.append(proc)
    t0 = time.time()
    first = _py("waitfor", "--done", str(done), "--max-sec", "2", env=sb.env())
    ctx.check(first.returncode == 0 and _last(first.stdout).startswith("WAITFOR_VERDICT=pending"),
              f"第一段 waitfor rc={first.returncode} 末行={_last(first.stdout)!r} stderr={first.stderr[:200]!r}")  # noqa: E501
    ctx.check(not done.exists(), "子行程還在跑，`.done` 卻已存在")
    second = _py("waitfor", "--done", str(done), "--max-sec", "30", env=sb.env())
    elapsed = time.time() - t0
    ctx.check(second.returncode == 0 and _last(second.stdout) == "WAITFOR_VERDICT=done rc=0",
              f"第二段 waitfor rc={second.returncode} 末行={_last(second.stdout)!r} stderr={second.stderr[:200]!r}")  # noqa: E501
    ctx.check("開始" in second.stdout and "結束" in second.stdout, f"尾端沒有子行程輸出：{second.stdout[:300]!r}")  # noqa: E501
    row = json.loads(done.read_text(encoding="utf-8"))
    ctx.check(row.get("rc") == 0 and row.get("schema") == "autosdd.runlong/1" and row.get("ended"), f".done 內容不符：{row}")  # noqa: E501
    ctx.check(proc.wait(timeout=15) == 0, f"runlong 自身 rc={proc.returncode}")
    ctx.check(elapsed >= 7, f"總耗時 {elapsed:.1f}s < 子行程睡眠 8s：waitfor 沒真的等")
    ctx.evidence(f"RV-LW1 pending={_last(first.stdout)!r}；done={_last(second.stdout)!r}；.done={row}；總 {elapsed:.1f}s")  # noqa: E501


# ───────────────────────────── RV-LW2：真 hook 行程＋真實形狀 payload ─────────────────────────────
def _payload(tool: str = "PowerShell", *, agent: str | None = "ae69f50e699e37cc2", timeout: int | None = 300_000, **tin) -> dict:  # noqa: E501
    ti = {"command": "Write-Output hi", "description": "d", **tin}
    if timeout is not None:
        ti["timeout"] = timeout
    pl = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti, "session_id": "rv-lw2",  # noqa: E501
          "permission_mode": "default", "tool_use_id": "toolu_rv"}
    if agent:
        pl.update(agent_id=agent, agent_type="general-purpose")
    return pl


@case("RV-LW2", "sessionctl_longwait", refs=("AT-SS-33", "AT-SS-34", "AT-SS-35"))
def rv_lw2(ctx: CaseContext) -> None:
    """真 `sessionctl_guard.py` 行程吃真實形狀 PreToolUse payload：子代理＋前景＋timeout 300000 ⇒ rc 2（訊息含 runlong／waitfor）；
    邊界 270000／背景／主控／Read 工具／行內豁免 ⇒ rc 0；`AUTOSDD_UNATTENDED=1` 下豁免無效 ⇒ rc 2；壞 JSON ⇒ rc 0。"""  # noqa: E501
    _need_gate()
    sb = ctx.sandbox(probe_hooks=False)
    exempt = "big  # keepwarm-ok: 一次性下載大檔無法分段"

    def run(payload, extra=None, raw: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(HOOK)], input=raw if raw is not None else json.dumps(payload),  # noqa: E501
                              capture_output=True, encoding="utf-8", errors="replace", timeout=60, check=False,  # noqa: E501
                              cwd=str(sb.root), env=sb.env({**NO_QUOTA, **(extra or {})}), creationflags=NOWIN)  # noqa: E501

    cases = [
        ("子代理 PowerShell 300000 ⇒ 擋", _payload(), None, 2),
        ("子代理 Bash 300000 ⇒ 擋", _payload("Bash"), None, 2),
        ("邊界 270001 ⇒ 擋", _payload(timeout=270_001), None, 2),
        ("邊界 270000 ⇒ 放行", _payload(timeout=270_000), None, 0),
        ("背景呼叫 ⇒ 放行", _payload(run_in_background=True), None, 0),
        ("主控（無 agent_id）⇒ 放行", _payload(agent=None), None, 0),
        ("沒設 timeout（預設 120 秒）⇒ 放行", _payload(timeout=None), None, 0),
        ("Read 工具 ⇒ 放行", _payload("Read"), None, 0),
        ("行內豁免 ⇒ 放行", _payload(command=exempt), None, 0),
        ("無人窗口豁免無效 ⇒ 擋", _payload(command=exempt), {"AUTOSDD_UNATTENDED": "1"}, 2),
    ]
    rows = []
    for label, payload, extra, want in cases:
        got = run(payload, extra)
        ctx.check(got.returncode == want, f"{label}：rc={got.returncode}（要 {want}）stderr={got.stderr[:200]!r}")  # noqa: E501
        if want == 2:
            ctx.check("runlong" in got.stderr and "waitfor" in got.stderr, f"{label}：訊息缺 runlong／waitfor：{got.stderr[:200]!r}")  # noqa: E501
        rows.append(f"{label}→{got.returncode}")
    broken = run(None, raw="{{not json")
    ctx.check(broken.returncode == 0, f"壞 JSON rc={broken.returncode}（要 0：fail-open）")
    ctx.evidence("RV-LW2 " + "；".join(rows) + "；壞 JSON→0")


# ───────────────────────────── 逐字稿輔助（LW3／LW4）─────────────────────────────
def _jsonl(path: Path) -> list[dict]:
    out = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(ln)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _epoch(stamp: str) -> float:
    from datetime import datetime  # noqa: PLC0415

    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


def _ctx_of(usage: dict) -> int:
    return sum(int(usage.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))  # noqa: E501


def _turns(recs: list[dict]) -> list[dict]:
    """依 message.id 去重的 assistant 回合（取第一筆記錄的時刻、最後一筆的 usage），依檔內順序。"""
    seen: dict[str, dict] = {}
    order: list[str] = []
    for r in recs:
        msg = r.get("message")
        if r.get("type") != "assistant" or not isinstance(msg, dict) or not isinstance(msg.get("usage"), dict) or msg.get("model") == "<synthetic>":  # noqa: E501
            continue
        mid = str(msg.get("id") or r.get("uuid"))
        if mid not in seen:
            seen[mid] = {"id": mid, "at": _epoch(str(r.get("timestamp"))), "usage": msg["usage"], "tool_ids": []}  # noqa: E501
            order.append(mid)
        seen[mid]["usage"] = msg["usage"]
        for blk in msg.get("content") or []:
            if isinstance(blk, dict) and blk.get("type") == "tool_use":
                seen[mid]["tool_ids"].append((blk.get("id"), blk.get("name"), json.dumps(blk.get("input"), ensure_ascii=False)))  # noqa: E501
    return [seen[m] for m in order]


def _tool_results(recs: list[dict]) -> list[tuple[str, str, bool]]:
    """`(工具名, 結果文字, is_error)`：用 tool_use id 把結果接回工具名。"""
    names = {}
    for r in recs:
        msg = r.get("message")
        for blk in (msg.get("content") if isinstance(msg, dict) and isinstance(msg.get("content"), list) else []):  # noqa: E501
            if isinstance(blk, dict) and blk.get("type") == "tool_use":
                names[blk.get("id")] = blk.get("name")
    out = []
    for r in recs:
        msg = r.get("message")
        for blk in (msg.get("content") if isinstance(msg, dict) and isinstance(msg.get("content"), list) else []):  # noqa: E501
            if isinstance(blk, dict) and blk.get("type") == "tool_result":
                body = blk.get("content")
                text = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
                out.append((str(names.get(blk.get("tool_use_id"))), text, bool(blk.get("is_error"))))  # noqa: E501
    return out


def _kill_leftovers(sb: Sandbox) -> None:
    """失敗路徑的善後：子代理起的 runlong／被等行程不在 `sb.procs`；以沙盒路徑為記號找出並結束（只動命令列含本沙盒根者）。"""  # noqa: E501
    if os.name != "nt":
        return
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.Contains('"  # noqa: E501
          + str(sb.root).replace("'", "''") + "') -and $_.ProcessId -ne $PID } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }")  # noqa: E501
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, timeout=60, check=False, creationflags=NOWIN)  # noqa: E501


# ───────────────────────────── RV-LW3：子代理分段等待的快取命中 ─────────────────────────────
@case("RV-LW3", "sessionctl_longwait", refs=("V-SS2",), long=True)
def rv_lw3(ctx: CaseContext) -> None:
    """真 `claude -p --model haiku` 主控派一支前景子代理（haiku）：背景 runlong 一支睡 420 秒的指令，並以前景 waitfor（--max-sec 240、
    timeout 270000）迴圈等到 done。從子代理真逐字稿斷言：① 沒有任何前景 PowerShell 的 timeout > 270000；② 相鄰 assistant 回合時間間隔
    < 300 秒（沒給 5 分鐘快取過期的機會）；③ 每個 waitfor 之後的第一個回合 `cache_read ≥ 0.9×前一回合上下文`（至少 2 個這樣的回合）；
    ④ `.done` rc 0。載具＝子代理逐字稿（`claude -p` 主控自己的快取壽命另算，與本案證據無關）。"""  # noqa: E501
    sb = ctx.sandbox()
    sb.add_hook("PreToolUse", sb.root / ".claude" / "rv_probe_hook.py", matcher=GATE_MATCHER)  # 記錄子代理呼叫的真 payload  # noqa: E501
    if _hook_has_gate():
        sb.add_hook("PreToolUse", HOOK, matcher=GATE_MATCHER)  # 套用後同場證明：waitfor 自己不被長前景閘擋  # noqa: E501
    out = sb.root / "long420.txt"
    py = sys.executable
    run_cmd = f"& '{py}' '{SESSIONCTL}' runlong --out '{out}' -- '{py}' -c 'import time; time.sleep({SLEEP_S}); print(\"slept\")'"  # noqa: E501
    wait_cmd = f"& '{py}' '{SESSIONCTL}' waitfor --done '{out}.done' --max-sec 240"
    prompt = (
        "Use the Agent tool exactly once, in the FOREGROUND (do not set run_in_background), subagent_type general-purpose, model haiku, "  # noqa: E501
        "description 'rv waiter', with this prompt: \"Follow these steps exactly, using only the PowerShell tool. "  # noqa: E501
        f"Step 1: run this command with run_in_background=true: {run_cmd} . "
        f"Step 2: run this command in the FOREGROUND with timeout 270000 (never background, never any other timeout): {wait_cmd} . "  # noqa: E501
        "If its last output line starts with WAITFOR_VERDICT=pending, run the identical command again; repeat until the last line "  # noqa: E501
        "starts with WAITFOR_VERDICT=done. Do not run any other waiting or sleeping command. Then reply with the single word DONE.\" "  # noqa: E501
        "After the agent returns, reply with the single word FINISHED."
    )
    try:
        res = ctx.run_claude(sb, prompt, extra_args=BYPASS, env_extra=NO_QUOTA, timeout_s=660)
        ctx.check(res.rc == 0 and not res.timed_out, f"claude -p rc={res.rc} timed_out={res.timed_out} {res.stderr[:300]}")  # noqa: E501
        files = _subagent_files(sb)
        ctx.check(bool(files), "沒有任何子代理逐字稿（主控沒派出子代理？）")
        recs = max((_jsonl(f) for f in files), key=len)
        turns = _turns(recs)
        results = _tool_results(recs)
        wait_ids = {tid for t in turns for tid, name, inp in t["tool_ids"] if name == "PowerShell" and "waitfor" in inp}  # noqa: E501
        ctx.check(len(wait_ids) >= 2, f"子代理只呼叫了 {len(wait_ids)} 次 waitfor（要 ≥ 2 段才有「等待後回合」可驗）")  # noqa: E501
        for t in turns:
            for _tid, name, inp in t["tool_ids"]:
                if name == "PowerShell":
                    tmo = json.loads(inp).get("timeout")
                    ctx.check(tmo is None or tmo <= 270_000, f"子代理前景 PowerShell timeout={tmo} > 270000")  # noqa: E501
        gaps = [(b["at"] - a["at"]) for a, b in zip(turns, turns[1:], strict=False)]
        ctx.check(max(gaps) < 300, f"相鄰回合最大間隔 {max(gaps):.0f}s ≥ 300（5 分鐘快取壽命）：{[round(g) for g in gaps]}")  # noqa: E501
        # 每個 waitfor tool_use 所在回合的「下一個回合」：cache_read 要吃到前一回合的上下文
        checked = []
        for i, t in enumerate(turns[:-1]):
            if any(tid in wait_ids for tid, _n, _i in t["tool_ids"]):
                prev_ctx, nxt = _ctx_of(t["usage"]), turns[i + 1]
                cr = int(nxt["usage"].get("cache_read_input_tokens") or 0)
                ctx.check(cr >= 0.9 * prev_ctx, f"waitfor 之後的回合 cache_read={cr:,} < 0.9×前一回合上下文 {prev_ctx:,}")  # noqa: E501
                checked.append((cr, prev_ctx))
        ctx.check(len(checked) >= 2, f"只驗到 {len(checked)} 個等待後回合（要 ≥ 2）")
        ctx.check(any("WAITFOR_VERDICT=pending" in text for name, text, _e in results if name == "PowerShell"),  # noqa: E501
                  "子代理沒有看到任何 pending 判決（兩段式等待沒發生）")
        ctx.check(any("WAITFOR_VERDICT=done rc=0" in text for name, text, _e in results if name == "PowerShell"),  # noqa: E501
                  "子代理沒有看到 done rc=0 判決")
        row = json.loads((sb.root / "long420.txt.done").read_text(encoding="utf-8"))
        ctx.check(row.get("rc") == 0, f".done rc={row}")
        pre = [e["payload"] for e in sb.events() if e["ev"] == "PreToolUse" and e["payload"].get("tool_name") == "PowerShell"]  # noqa: E501
        ctx.check(any(p.get("agent_id") for p in pre), "探針沒有記到帶 agent_id 的 PowerShell payload（hook 沒跑或 payload 無該欄）")  # noqa: E501
        ctx.evidence(f"RV-LW3 {sb.sid[:8]} 子代理回合 {len(turns)}、最大間隔 {max(gaps):.0f}s；等待後回合 cache_read/前一回合上下文＝"  # noqa: E501
                     f"{[(f'{c:,}', f'{p:,}') for c, p in checked]}；.done={row}")
    finally:
        _kill_leftovers(sb)


# ───────────────────────────── RV-LW4：真 harness 下閘擋子代理、不擋主控 ─────────────────────────────  # noqa: E501
@case("RV-LW4", "sessionctl_longwait", refs=("AT-SS-33", "AT-SS-34"))
def rv_lw4(ctx: CaseContext) -> None:
    """真 `claude -p`＋真 hook（PreToolUse matcher PowerShell|Bash）：子代理前景 PowerShell timeout 300000 ⇒ 被擋（子代理逐字稿的工具結果
    含「長前景閘」、探針記到帶 agent_id 的 payload）；同樣參數的主控 PowerShell 呼叫不被擋（主控逐字稿的該工具結果是 main）。"""  # noqa: E501
    _need_gate()
    sb = ctx.sandbox()
    sb.add_hook("PreToolUse", sb.root / ".claude" / "rv_probe_hook.py", matcher=GATE_MATCHER)
    sb.add_hook("PreToolUse", HOOK, matcher=GATE_MATCHER)
    prompt = (
        "First, use the PowerShell tool yourself, in the foreground, with timeout 300000, to run exactly: Write-Output main . "  # noqa: E501
        "Then use the Agent tool exactly once, in the foreground, subagent_type general-purpose, model haiku, description 'rv gate', with "  # noqa: E501
        "this prompt: \"Use the PowerShell tool in the foreground with timeout 300000 to run exactly: Write-Output sub . If the call is "  # noqa: E501
        "blocked or refused, quote the refusal text verbatim in your reply, then retry the same command with timeout 60000. Reply with the "  # noqa: E501
        "outcomes.\" After the agent returns, reply with the single word FINISHED."
    )
    res = ctx.run_claude(sb, prompt, extra_args=BYPASS, env_extra=NO_QUOTA, timeout_s=240)
    ctx.check(res.rc == 0 and not res.timed_out, f"claude -p rc={res.rc} timed_out={res.timed_out} {res.stderr[:300]}")  # noqa: E501
    pre = [e["payload"] for e in sb.events() if e["ev"] == "PreToolUse" and e["payload"].get("tool_name") == "PowerShell"]  # noqa: E501
    sub_calls = [p for p in pre if p.get("agent_id")]
    main_calls = [p for p in pre if not p.get("agent_id")]
    ctx.check(any(p["tool_input"].get("timeout") == 300_000 for p in sub_calls), f"探針沒有子代理 timeout=300000 的 PowerShell payload：{[p.get('tool_input') for p in sub_calls]}")  # noqa: E501
    ctx.check(any(p["tool_input"].get("timeout") == 300_000 for p in main_calls), "探針沒有主控 timeout=300000 的 PowerShell payload")  # noqa: E501
    files = _subagent_files(sb)
    ctx.check(bool(files), "沒有子代理逐字稿")
    sub_results = [r for f in files for r in _tool_results(_jsonl(f))]
    ctx.check(any(name == "PowerShell" and "長前景閘" in text for name, text, _e in sub_results),
              f"子代理的 PowerShell 結果沒有「長前景閘」：{[(n, t[:80]) for n, t, _e in sub_results]}")  # noqa: E501
    main_results = _tool_results(_jsonl(ctx.transcript(sb).path))
    mine = [t for n, t, _e in main_results if n == "PowerShell"]
    ctx.check(bool(mine) and all("長前景閘" not in t for t in mine) and any("main" in t for t in mine), f"主控 PowerShell 結果異常（被擋或沒跑）：{mine}")  # noqa: E501
    ctx.evidence(f"RV-LW4 {sb.sid[:8]} 子代理 payload keys={sorted(sub_calls[0])}；子代理被擋；主控 PowerShell 結果={mine[0][:40]!r}")  # noqa: E501
