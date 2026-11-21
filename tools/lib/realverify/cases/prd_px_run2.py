"""prd_px 家族（真引擎＋可程式化 shim 第二批）：RV-PX35／40／43／46。

shim 只決定 `claude -p` 的輸出與等待；引擎行程、設定載入、退避／遮蔽／逾時／log 全是真的。
RV-PX46 的第一步是真 `claude -p --model haiku`（shim 的 `real` 直通），第二步才是 sleep。"""

from __future__ import annotations

import re
from datetime import datetime

from ..sandbox import REPO
from . import CaseContext
from .prd_px_engine import (
    REAL_EXTRA_ARGS,
    pct_json,
    real_claude,
    run_engine,
    shim_calls,
    write_py_shim,
)
from .prd_px_lib import ev, px
from .prd_px_run import playbook
from .sessionctl_park import PY, run

LIMIT = "API Error: 429 rate limit exceeded. Retry-After: {n}"


@px("RV-PX35", "P＋X", ("retried_same_attempt", "waited", "over_cap_halts"), refs=("§8 列 1",))
def px35(ctx: CaseContext) -> None:
    """§8 列 1：推論端 429 有界退避。shim 第一次輸出限流字樣＋`Retry-After: 3`、第二次正常 ⇒ 同 attempt 重跑一次且成功、
    兩次呼叫間隔 ≥3 s 且 ≤ 3 s＋jitter 上限（min(cap,10·2^0)＝10 s）；變體 `Retry-After: 900`（>300）⇒ 走 halt。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    script = [{"stdout": LIMIT.format(n=3), "rc": 1}, {"stdout": pct_json(10)}]
    r = run_engine(sb, command=str(write_py_shim(sb, script)), playbook=playbook(1))
    calls = shim_calls(sb)
    ctx.check(r.rc == 0 and len(calls) == 2, f"應重跑同 attempt 共 2 次呼叫且成功：rc={r.rc} calls={len(calls)}\n{r.text[-700:]}")  # noqa: E501
    ctx.check("LIMIT_RETRY" in r.log and "attempt 1" in r.log, f"log 應有 LIMIT_RETRY 且成功落在 attempt 1：\n{r.log[-900:]}")  # noqa: E501
    ev(ctx, "retried_same_attempt", f"shim_calls={len(calls)} LIMIT_RETRY=True step 成功於 attempt 1（未消耗 attempt）")  # noqa: E501
    gap = calls[1]["t0"] - calls[0]["t1"]
    ctx.check(3.0 <= gap <= 13.5, f"兩次呼叫間隔 {gap:.2f}s 不在 [3,13]（3＋jitter≤10）")
    ev(ctx, "waited", f"gap={gap:.2f}s in [3, 3+10]")
    sb2 = ctx.sandbox(probe_hooks=False)
    r2 = run_engine(sb2, command=str(write_py_shim(sb2, [{"stdout": LIMIT.format(n=900), "rc": 1}])),  # noqa: E501
                    playbook=playbook(1))
    c2 = shim_calls(sb2)
    ctx.check(r2.rc != 0 and "LIMIT_RETRY" not in r2.log and "額度軸 halt" in r2.log,
              f"Retry-After=900 超過上限應 halt、不退避：rc={r2.rc}\n{r2.log[-900:]}")
    ev(ctx, "over_cap_halts", f"Retry-After=900>300 ⇒ 額度軸 halt（reason=halted）、無 LIMIT_RETRY、shim_calls={len(c2)}")  # noqa: E501


SECRETS = (
    "sk-ant-api03-RVSECRET0123456789abcdefghijklmnop",  # secret-scan-ok: RV-PX40 遮蔽測試的假金鑰夾具
    "password=hunter2RVsecret",
)


@px("RV-PX40", "P＋X", ("secret_absent", "redacted_marker"), refs=("§12 日誌遮蔽",))
def px40(ctx: CaseContext) -> None:
    """§12 日誌遮蔽：shim 輸出含假金鑰樣式字串（步驟失敗 ⇒ 引擎把輸出寫進 log／escalation）⇒ 引擎 log 目錄
    命中 0、log 含 `[REDACTED]`。log 目錄＝cfg.log_dir 全部檔案（含 PTY 原始串流 `playbook_*.log`）。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    out = "failing run with " + " ".join(SECRETS)
    r = run_engine(sb, command=str(write_py_shim(sb, [{"stdout": out}])), playbook=playbook(1))
    ctx.check(r.rc != 0, f"步驟應失敗（輸出無 [DONE]）：rc={r.rc}")
    hits = []
    for p in sorted((sb.root / "logs").rglob("*")):
        if p.is_file():
            body = p.read_text(encoding="utf-8", errors="replace")
            hits += [f"{p.name}:{s[:16]}" for s in SECRETS if s in body]
    ctx.check(not hits, f"log 目錄出現未遮蔽的假金鑰：{hits}")
    ev(ctx, "secret_absent", f"log_files={len(list((sb.root / 'logs').glob('*')))} secret_hits=0")
    # WHY：autoclaude.log 不寫步驟輸出；步驟輸出只進 PTY 串流 playbook_*.log（F1 修復後遮蔽）。
    pb_logs = sorted((sb.root / "logs").rglob("playbook_*.log"))
    ctx.check(bool(pb_logs), "log 目錄沒有 playbook_*.log（PTY 串流）")
    n_red = sum(p.read_text(encoding="utf-8", errors="replace").count("[REDACTED]")
                for p in pb_logs)
    ctx.check(n_red >= 1, f"playbook_*.log 應至少一處 [REDACTED]：{[p.name for p in pb_logs]}")
    ev(ctx, "redacted_marker", f"playbook_logs={len(pb_logs)} [REDACTED] count={n_red}")


@px("RV-PX43", "P", ("sum_le_cap", "rounds"), refs=("§11.7",))
def px43(ctx: CaseContext) -> None:
    """§11.7：兩個行程對同一派發帳連搶 30 回合，每回合成功總和恆 ≤ cap
    （真跑 two_project_fanout_probe，沙盒 cwd；探針自帶對照組自證能抓競態）。"""
    sb = ctx.sandbox(probe_hooks=False)
    probe = str(REPO / "tools" / "probe" / "two_project_fanout_probe.py")
    r = run([PY, probe, "--cap", "2", "--attempts", "50", "--rounds", "30"], cwd=sb.root, env=sb.env(),  # noqa: E501
            timeout=200)
    ctx.check(r.returncode == 0, f"探針 rc={r.returncode}\n{r.stdout[-900:]}")
    m = re.search(r"PASS 兩行程成功總和 ≤ cap=(\d+)（(\d+) 回合）", r.stdout)
    ctx.check(bool(m) and m.group(2) == "30", f"應 PASS 且 30 回合：\n{r.stdout[-900:]}")
    tot = re.search(r"每回合合計 (.*)", r.stdout)
    ev(ctx, "sum_le_cap", f"cap={m.group(1)} {tot.group(1)[:80] if tot else ''}")
    ev(ctx, "rounds", f"rounds={m.group(2)} probe_rc=0")


@px("RV-PX46", "P＋C", ("max_turns_argv", "step_timeout"), refs=("§4.4.3",))
def px46(ctx: CaseContext) -> None:
    """§4.4.3：真引擎設 `claude.max_turns_per_step`＝3、`playbook.step_timeout_seconds`＝20。
    第一步是**真** `claude -p --model haiku`（shim 的 real 直通，argv 由引擎組出）
    ⇒ 命令列含 `--max-turns 3`；第二步 shim sleep 60 ⇒ 引擎在 20 s＋寬限內終止並記 timeout。"""
    sb = ctx.sandbox(probe_hooks=False)
    real = real_claude()
    pb = ('version: "1.0"\nproject: "rv"\ntasks:\n'
          '  - step_id: "T01"\n    name: "n"\n    prompt: "Reply with exactly the text [DONE] and nothing else."\n'  # noqa: E501
          '    max_retries: 0\n    expected_output_regex: "\\\\[DONE\\\\]"\n'
          '  - step_id: "T02"\n    name: "n"\n    prompt: "sleep"\n    max_retries: 0\n'
          '    expected_output_regex: "\\\\[DONE\\\\]"\n')
    script = [{"real": real}, {"sleep": 60, "stdout": "[DONE]"}]
    t_start = datetime.now()
    r = run_engine(sb, command=str(write_py_shim(sb, script)), playbook=pb, extra_args=REAL_EXTRA_ARGS,  # noqa: E501
                   claude_extra="  max_turns_per_step: 3\n", extra_cfg="playbook:\n  step_timeout_seconds: 20\n",  # noqa: E501
                   timeout=240)
    calls = shim_calls(sb)
    ctx.check(len(calls) >= 1, f"shim 沒被呼叫：{r.text[-600:]}")
    argv0 = " ".join(calls[0]["argv"])
    ctx.check("--max-turns 3" in argv0, f"命令列缺 --max-turns 3：{argv0}")
    ctx.check(calls[0].get("real_rc") == 0 and "[T01] n ✓" in r.log, f"第一步（真 haiku）應成功：\n{r.log[-900:]}")  # noqa: E501
    ev(ctx, "max_turns_argv", f"real_claude_argv={argv0[:120]} real_rc=0")
    # 第二步：引擎記 timeout 並在 20 s＋寬限內放手
    mm = re.findall(r"(\d{2}:\d{2}:\d{2}) .*?subprocess 模式啟動", r.log)
    ctx.check(len(mm) >= 2, f"應有兩次 spawn：{mm}")
    fmt = "%H:%M:%S"
    spawn2 = datetime.strptime(mm[1], fmt)
    fin = re.findall(r"(\d{2}:\d{2}:\d{2}) .*?(?:ESCALATION|Playbook 結束)", r.log)
    ctx.check(bool(fin), "找不到 T02 結束時間")
    dur = (datetime.strptime(fin[-1], fmt) - spawn2).total_seconds()
    ctx.check(dur <= 20 + 15, f"第二步用了 {dur:.0f}s，超過 20 s＋寬限 15 s（sleep 是 60 s）")
    ctx.check("逾時" in r.log or "timeout" in r.log.lower() or "未符合期望" in r.log, f"應記逾時／失敗：\n{r.log[-700:]}")  # noqa: E501
    ev(ctx, "step_timeout", f"T02 sleep=60 timeout=20 ⇒ 引擎在 {dur:.0f}s 放手（≤35）t_start={t_start:%H:%M:%S}")  # noqa: E501
