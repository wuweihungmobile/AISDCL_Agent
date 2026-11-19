"""sessionctl_keepwarm 家族：主控快取保溫（R216；TCS-SessionSwitch-CostModel E2E-SS-03／06／09）。

全部用真 `claude -p --model haiku`（沙盒、repo 外）產生真逐字稿，再真跑 `python tools/sessionctl.py
keepwarm`／`watch` 子行程與 repo 真的 `sessionctl_guard.py` Stop hook；不 monkeypatch 被測物、不開測試用
環境變數：時間類條件只用正式參數（`keepwarm --min`）與 ENV_SPEC 已登記的 env 下修
（`AUTOSDD_KEEPWARM_MIN_CTX_TOKENS`、`AUTOSDD_QUOTA_*_PCT`）。每個案例的 `claude -p` 回合都極小（haiku，
單案 ≤ 約 3 萬 token）。

未涵蓋（誠實劃界）：E2E-SS-04（真 `claude -p` 閒置 45～100 分鐘後第三回合 cache_read ≥ 0.9×前一回合上下文）
與 V-SS1（互動主控閒置 3 小時）是長案／真機，不在本家族；它們是「保溫真的擋得住快取過期」的最終證據，
未跑之前該項計未結。
"""  # noqa: E501

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from ..driver import EnvMissing
from ..sandbox import Sandbox
from ..transcript import Transcript
from . import CaseContext, case
from .sessionctl_watch import (  # noqa: E501
    BYPASS,
    GUARD,
    NO_QUOTA,
    SESSIONCTL,
    _check_verdict,
    _install_guard,
    _watch,
)

# 沙盒小上下文也要能 ping：把「太小不保溫」門檻下修到 1（ENV_SPEC 已登記、只是不掛的情形之一）
LOW_CTX = {"AUTOSDD_KEEPWARM_MIN_CTX_TOKENS": "1"}
# 額度整組下修（四錨點須嚴格遞增、compact 邊際 3 < prepare−converge）：真實短窗讀數 ≥ 6 ⇒ prepare 帶
LOW_PREPARE = {"AUTOSDD_QUOTA_NOTICE_PCT": "1", "AUTOSDD_QUOTA_CONVERGE_PCT": "2", "AUTOSDD_QUOTA_PREPARE_PCT": "6",  # noqa: E501
               "AUTOSDD_QUOTA_HALT_PCT": "100"}
LOW_HALT = {**LOW_PREPARE, "AUTOSDD_QUOTA_HALT_PCT": "7"}  # 讀數 ≥ 7 ⇒ halt 帶


def _epoch(stamp: str) -> float:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()


def _last_usage_at(tr: Transcript) -> float:
    """逐字稿最後一筆帶 usage 的 assistant 記錄時刻（與 `keepwarm.anchor` 同定義，由測試端獨立重算）。"""  # noqa: E501
    best = None
    for r in tr.recs:
        msg = r.data.get("message")
        if r.data.get("type") == "assistant" and isinstance(msg, dict) and isinstance(msg.get("usage"), dict) \
                and msg.get("model") != "<synthetic>" and r.ts:  # noqa: E501
            best = _epoch(r.ts)
    if best is None:
        raise AssertionError("真逐字稿沒有任何帶 usage 的 assistant 記錄")
    return best


def _start_keepwarm(sb: Sandbox, transcript: Path, minutes: int, env_extra: dict | None = None) -> subprocess.Popen:  # noqa: E501
    argv = [sys.executable, str(SESSIONCTL), "keepwarm", "--sid", sb.sid, "--projects-dir", str(transcript.parent),  # noqa: E501
            "--min", str(minutes), "--poll-sec", "5"]
    proc = subprocess.Popen(  # noqa: S603
        argv, cwd=str(sb.root), env=sb.env({**NO_QUOTA, **LOW_CTX, **(env_extra or {})}), stdin=subprocess.DEVNULL,  # noqa: E501
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))  # noqa: E501
    sb.procs.append(proc)
    return proc


def _finish(proc: subprocess.Popen, timeout_s: float) -> tuple[int, str, str, float]:
    """等 keepwarm 結束；回 (rc, 全文, 末行判決, 結束時刻 epoch)。"""
    try:
        out, _ = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        return -9, out.decode("utf-8", errors="replace"), "", time.time()
    ended = time.time()
    text = out.decode("utf-8", errors="replace")
    verdicts = [ln for ln in text.splitlines() if ln.startswith("KEEPWARM_VERDICT=")]
    return proc.returncode, text, (verdicts[-1] if verdicts else ""), ended


def _ledger(sb: Sandbox) -> dict:
    return json.loads((sb.root / "traces" / "keepwarm" / f"{sb.sid}.json").read_text(encoding="utf-8"))  # noqa: E501


@case("RV-KW1", "sessionctl_keepwarm", refs=("V-SS1",))
def rv_kw1(ctx: CaseContext) -> None:
    """真 `claude -p` 建 session → 真跑 `sessionctl.py keepwarm --min 1`：截止＝最後一筆 assistant 記錄＋1 分
    （不是指令啟動後 1 分）⇒ rc 0（DEF-200-622：判決不靠 rc）、末行 `KEEPWARM_VERDICT=ping`；保溫帳 pings＝1、n* 與判決行一致。"""  # noqa: E501
    sb = ctx.sandbox()
    r1 = ctx.run_claude(sb, "Reply with exactly: ok")
    ctx.check(r1.rc == 0, f"第一回合 rc={r1.rc} {r1.stderr[:200]}")
    tr = ctx.transcript(sb)
    anchor = _last_usage_at(tr)
    started = time.time()
    rc, text, last, ended = _finish(_start_keepwarm(sb, tr.path, 1), 150)
    ctx.check(rc == 0 and last.startswith("KEEPWARM_VERDICT=ping k=1 n=") and "rc=" not in last, f"keepwarm rc={rc} 末行={last!r}：{text[-300:]!r}")  # noqa: E501
    ctx.check(anchor + 60 - 3 <= ended <= anchor + 60 + 30, f"結束時刻 {ended - anchor:.1f}s（要落在最後記錄＋60s 附近，不是啟動後 60s；啟動晚了 {started - anchor:.1f}s）")  # noqa: E501
    row = _ledger(sb)
    ctx.check(row["pings"] == 1 and f"n={row['n_star']}" in last,f"保溫帳與判決行不符：{row} vs {last}")  # noqa: E501
    ctx.evidence(f"RV-KW1 {sb.sid[:8]} {last}；錨點→結束 {ended - anchor:.1f}s；帳 {row}")


@case("RV-KW2", "sessionctl_keepwarm", refs=("V-SS1",))
def rv_kw2(ctx: CaseContext) -> None:
    """keepwarm 執行中，同一 session 又有真的新回合（真 `claude -p -r`）⇒ 截止往後延到新記錄＋2 分，而不是在原截止叫醒
    （人回來工作＝快取剛續命，不該白付一次保溫價）。"""  # noqa: E501
    sb = ctx.sandbox()
    r1 = ctx.run_claude(sb, "Reply with exactly: ok")
    ctx.check(r1.rc == 0, f"第一回合 rc={r1.rc} {r1.stderr[:200]}")
    tr = ctx.transcript(sb)
    a1 = _last_usage_at(tr)
    proc = _start_keepwarm(sb, tr.path, 2)
    time.sleep(max(0.0, a1 + 70 - time.time()))
    ctx.check(proc.poll() is None, "keepwarm 在原截止之前就結束了")
    r2 = ctx.run_claude(sb, "Reply with exactly: ok2")
    ctx.check(r2.rc == 0, f"第二回合 rc={r2.rc} {r2.stderr[:200]}")
    a2 = _last_usage_at(ctx.transcript(sb))
    ctx.check(a2 > a1 + 60, f"第二回合記錄 {a2 - a1:.0f}s 後才出現（要在原截止 a1+120 之前）")
    rc, text, last, ended = _finish(proc, 240)
    ctx.check(rc == 0 and last.startswith("KEEPWARM_VERDICT=ping"), f"keepwarm rc={rc} 末行={last!r}：{text[-300:]!r}")  # noqa: E501
    ctx.check(ended >= a2 + 120 - 3, f"在新記錄＋120s 之前就叫醒了（{ended - a2:.1f}s）")
    ctx.check(ended >= a1 + 120 + 15, f"沒有延後：結束於原截止後 {ended - (a1 + 120):.1f}s")
    ctx.evidence(f"RV-KW2 {sb.sid[:8]} 原截止 a1+120；新記錄 a1+{a2 - a1:.0f}s；結束 a2+{ended - a2:.0f}s；{last}")  # noqa: E501


def _quota_prepare_or_missing(got, label: str) -> None:
    _rc, _text, last = got
    if last.startswith("WATCH_VERDICT=") and "quota" not in last:
        raise EnvMissing(f"{label}：本機量不到達標的短窗額度讀數，無法觸發 quota 判決：{last}")


@case("RV-KW3", "sessionctl_keepwarm", refs=("V-SS3",))
def rv_kw3(ctx: CaseContext) -> None:
    """真 `sessionctl.py watch` ×2：prepare 帶（env 整組下修；讀數取自本機真實額度快取）第一次 quota 判決、**重掛不再觸發**
    （同 reset 窗同帶）；第二次改由寬限期後的 all_done 結束，痕跡有 `watch_quota_latched`。真機缺陷回歸：
    2026-11-18 21:26 主控 watch 一掛即 rc 5、重掛照樣觸發。"""  # noqa: E501
    sb = ctx.sandbox()
    args = ("--poll-sec", "1", "--grace-sec", "4", "--stall-min", "20")
    first = _watch(sb, *args, env_extra=LOW_PREPARE)
    _quota_prepare_or_missing(first, "RV-KW3")
    _check_verdict(ctx, first, "quota", "RV-KW3 第一次")
    second = _watch(sb, *args, env_extra=LOW_PREPARE)
    _check_verdict(ctx, second, "all_done", "RV-KW3 重掛")
    rows = [json.loads(x) for x in (sb.root / "traces" / "autosdd_session_switch.jsonl").read_text(encoding="utf-8").splitlines()]  # noqa: E501
    ctx.check(any(x.get("event") == "watch_quota_latched" for x in rows), f"沒有 watch_quota_latched 痕跡（事件={[x.get('event') for x in rows]}）")  # noqa: E501
    latch = json.loads((sb.root / "traces" / "watch" / f"{sb.sid}.quota.json").read_text(encoding="utf-8"))  # noqa: E501
    ctx.check(latch.get("band") == "prepare", f"閂鎖帶級不是 prepare：{latch}")
    ctx.evidence(f"RV-KW3 {sb.sid[:8]} 第一次 {first[2]}；重掛 {second[2]}；閂鎖 {latch}")


@case("RV-KW4", "sessionctl_keepwarm", refs=("V-SS3",))
def rv_kw4(ctx: CaseContext) -> None:
    """帶升級再觸發：prepare 帶觸發並閂住後，同一 reset 窗、同一份真實讀數改把 halt 門檻下修到讀數之下 ⇒ 帶級變 halt，
    閂鎖放行再判 quota；之後同 halt 再重掛又被閂住（改判 all_done）。"""  # noqa: E501
    sb = ctx.sandbox()
    args = ("--poll-sec", "1", "--grace-sec", "4", "--stall-min", "20")
    first = _watch(sb, *args, env_extra=LOW_PREPARE)
    _quota_prepare_or_missing(first, "RV-KW4")
    _check_verdict(ctx, first, "quota", "RV-KW4 prepare")
    up = _watch(sb, *args, env_extra=LOW_HALT)
    if not up[2].startswith("WATCH_VERDICT=quota"):
        raise EnvMissing(f"本機短窗讀數 < 7%，無法造出 halt 帶：{up[2]}")
    ctx.check(up[0] == 0, f"帶升級那次 rc={up[0]}（判決一律 rc 0）")
    latch = json.loads((sb.root / "traces" / "watch" / f"{sb.sid}.quota.json").read_text(encoding="utf-8"))  # noqa: E501
    ctx.check(latch.get("band") == "halt", f"帶升級後閂鎖沒有記成 halt：{latch}")
    again = _watch(sb, *args, env_extra=LOW_HALT)
    _check_verdict(ctx, again, "all_done", "RV-KW4 halt 重掛")
    ctx.evidence(f"RV-KW4 {sb.sid[:8]} prepare {first[2]}；升 halt {up[2]}；halt 重掛 {again[2]}；閂鎖 {latch}")  # noqa: E501


_WARNING_WORDS = ("背景任務在跑", "TaskStop", "擁有者")  # 舊 Stop 警告語（DEF-200-623 之前）


def _bg_supervision_run(ctx: CaseContext, kind: str):
    """真 `claude -p`（沙盒＋repo 真 Stop 守衛）在背景掛真的 `sessionctl.py <kind>`（keepwarm 或 watch）；
    回 (sb, 逐字稿, RunResult, 第一次 Stop 的 background_tasks)。

    WHY 命令內自帶 env：工具 shell 不一定繼承 claude 行程的自訂變數（同 RV-S2）；沙盒 settings 的
    `AUTOSDD_KEEPWARM_OFF` 只讓 hook 側保溫閘不介入，命令內把它清成空字串（falsy）才讓被測的 keepwarm 真的
    保溫而非 skip。`--min 1`／`--grace-sec 20` 讓它在一分鐘內自己結束，`claude -p` 才收得了尾。"""  # noqa: E501
    sb = ctx.sandbox()
    r1 = ctx.run_claude(sb, "Reply with exactly: ok")
    ctx.check(r1.rc == 0, f"第一回合 rc={r1.rc} {r1.stderr[:200]}")
    tr1 = ctx.transcript(sb)
    _install_guard(sb)
    sb.settings["env"] = {**sb.settings.get("env", {}), "AUTOSDD_KEEPWARM_OFF": "1"}
    sb.write_settings()
    env = ("$env:AUTOSDD_KEEPWARM_OFF=''; $env:AUTOSDD_KEEPWARM_MIN_CTX_TOKENS='1'; "
           "$env:AUTOSDD_QUOTA_PREPARE_PCT='99'; $env:AUTOSDD_QUOTA_HALT_PCT='100'; ")
    tail = (f"keepwarm --sid {sb.sid} --projects-dir '{tr1.path.parent}' --min 1 --poll-sec 3"
            if kind == "keepwarm" else f"watch --sid {sb.sid} --stall-min 20 --poll-sec 3 --grace-sec 20")  # noqa: E501
    cmd = f"{env}& '{sys.executable}' '{SESSIONCTL}' {tail}"
    prompt = ("Make exactly one tool call: the PowerShell tool with run_in_background=true and "
              f"this exact command: {cmd}\nAfter it returns, end your turn immediately with the "
              "single word LAUNCHED. Never start any other command, even if a hook objects; "
              "when the background command later finishes, just reply with the single word DONE.")
    r = ctx.run_claude(sb, prompt, extra_args=BYPASS, timeout_s=420,
                       env_extra={**NO_QUOTA, **LOW_CTX})
    ctx.check(r.rc == 0 and not r.timed_out, f"claude -p rc={r.rc} timed_out={r.timed_out} {r.stderr[:200]}")  # noqa: E501
    tr = ctx.transcript(sb)
    stops = [e for e in sb.events() if e["ev"] == "Stop"]
    tasks = (stops[1]["payload"] if len(stops) > 1 else {}).get("background_tasks") or []
    return sb, tr, r, tasks


def _assert_no_failed_wording(ctx: CaseContext, sb, tr, tasks, kind: str, label: str) -> str:
    """共同斷言：Stop 當下真的只有該監督 shell 在跑（前提）、真 Stop hook 沒有出警告語、背景指令真的結束，
    且 harness 的完成通知是 `completed (exit code 0)`、沒有 failed。回被測行程寫進痕跡的判決名
    （逐字稿只收完成通知，不收背景指令的輸出，判決名取自 `traces/autosdd_session_switch.jsonl`）。"""  # noqa: E501
    shells = [t for t in tasks if t.get("type") == "shell" and t.get("status") == "running"]
    ctx.check(len(shells) == 1 and re.search(rf"sessionctl\.py[\"']?\s+{kind}", str(shells[0].get("command"))),  # noqa: E501
              f"{label}：Stop payload 沒有恰好一個 running 的 {kind} shell（前提不成立，斷言會恆真）：{tasks}")  # noqa: E501
    ctx.check(len(tr.stop_hook_summaries()) >= 1, f"{label}：Stop hook 沒跑（斷言恆真）")
    bad = [m for w in _WARNING_WORDS for m in tr.system_messages("Stop", w)]
    ctx.check(not bad, f"{label}：真 Stop hook 仍對依設計掛著的 {kind} shell 出警告語：{[str(b.data['attachment'].get('content'))[:160] for b in bad]}")  # noqa: E501
    raw = tr.path.read_text(encoding="utf-8", errors="replace")
    notes = re.findall(r"<status>(\w+)</status>\\n<summary>([^<]*)</summary>", raw)
    ctx.check(bool(notes), f"{label}：逐字稿沒有背景指令的完成通知（行程沒結束？）")
    ctx.check(all(s == "completed" and "exit code 0" in m and "failed" not in m for s, m in notes),
              f"{label}：harness 把監督判決標成非 completed／非 exit code 0（被畫面讀成錯誤）：{notes}")  # noqa: E501
    rows = [json.loads(x) for x in (sb.root / "traces" / "autosdd_session_switch.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]  # noqa: E501
    got = [x["verdict"] for x in rows if x.get("event") == f"{kind}_verdict"]
    ctx.check(len(got) == 1, f"{label}：痕跡裡的 {kind}_verdict 不是恰好 1 筆：{rows}")
    return got[0]


@case("RV-KW6", "sessionctl_keepwarm", refs=("DEF-200-622", "DEF-200-623"))
def rv_kw6(ctx: CaseContext) -> None:
    """正常的保溫叫醒不得被畫面呈現成錯誤（掌舵者 2026-11-19 真機回報）：真 `claude -p`＋repo 真 Stop 守衛，
    背景掛真 `keepwarm --min 1`；keepwarm 結束（ping，rc 0）、harness 沒有標 failed、Stop 當下只有 keepwarm
    shell 時真 hook 沒有「仍有背景任務在跑…TaskStop」警告語。"""  # noqa: E501
    sb, tr, _r, tasks = _bg_supervision_run(ctx, "keepwarm")
    last = _assert_no_failed_wording(ctx, sb, tr, tasks, "keepwarm", "RV-KW6")
    ctx.check(last == "ping", f"keepwarm 判決不是 ping：{last!r}")
    ctx.evidence(f"RV-KW6 {sb.sid[:8]} KEEPWARM_VERDICT={last}；完成通知 completed (exit code 0)；Stop 當下 background_tasks 只有 keepwarm shell，無警告語；無 failed 字樣")  # noqa: E501


@case("RV-KW7", "sessionctl_keepwarm", refs=("DEF-200-622", "DEF-200-623"))
def rv_kw7(ctx: CaseContext) -> None:
    """同上，被掛的是真 `watch`（無代理、寬限 20 秒後 all_done）：判決一律 rc 0、不被標 failed，Stop 當下只有
    watch shell 時真 hook 同樣不出警告語。"""  # noqa: E501
    sb, tr, _r, tasks = _bg_supervision_run(ctx, "watch")
    last = _assert_no_failed_wording(ctx, sb, tr, tasks, "watch", "RV-KW7")
    ctx.check(last == "all_done", f"watch 判決不是 all_done：{last!r}")
    ctx.evidence(f"RV-KW7 {sb.sid[:8]} WATCH_VERDICT={last}；完成通知 completed (exit code 0)；Stop 當下 background_tasks 只有 watch shell，無警告語；無 failed 字樣")  # noqa: E501


@case("RV-KW5", "sessionctl_keepwarm", refs=("V-SS4",))
def rv_kw5(ctx: CaseContext) -> None:
    """真 `claude -p` ＋ repo 真 `sessionctl_guard.py` Stop hook：回合結束時沒有任何背景任務、上下文超過保溫門檻 ⇒
    推回一次（逐字稿 hook_blocking_error 含「保溫閘」與 `sessionctl.py keepwarm --sid`）；推回後的第二次 Stop
    （stop_hook_active）放行。證明真 harness 的 Stop payload 有 `background_tasks` 欄（缺欄則閘不判、這裡就不會推回）。"""  # noqa: E501
    sb = ctx.sandbox()
    # 第一回合不掛守衛：先讓逐字稿有帶 usage 的記錄。Stop hook 觸發時最後一筆 assistant 記錄可能還沒寫進  # noqa: E501
    # 檔案（實測：單回合新 session 偶發量不到上下文 ⇒ 保溫閘依 fail-open 不判）；真實主控有歷史，不受影響。  # noqa: E501
    r1 = ctx.run_claude(sb, "Reply with exactly: ok")
    ctx.check(r1.rc == 0, f"第一回合 rc={r1.rc} {r1.stderr[:200]}")
    sb.add_repo_hook("Stop", GUARD)
    prompt = ("Reply with exactly the single word: ok2. If any hook asks you to start a background command, "  # noqa: E501
              "do NOT start it — just end your turn with the single word DONE.")
    r = ctx.run_claude(sb, prompt, env_extra={**NO_QUOTA, **LOW_CTX, "AUTOSDD_PARK_GUARD_OFF": "1"})
    ctx.check(r.rc == 0 and not r.timed_out, f"claude -p rc={r.rc} {r.stderr[:200]}")
    tr = ctx.transcript(sb)
    be = tr.hook_blocking_errors("Stop", "保溫閘")
    ctx.check(bool(be), "逐字稿沒有 Stop hook_blocking_error 含「保溫閘」（保溫閘沒推回，或真 payload 缺 background_tasks 欄）")  # noqa: E501
    text = str(be[0].data["attachment"])
    ctx.check("sessionctl.py keepwarm" in text and f"--sid {sb.sid}" in text, f"推回理由缺指令或 sid：{text[:300]}")  # noqa: E501
    ctx.check(len(be) == 1, f"保溫閘推回次數={len(be)}（要恰好 1：迴圈煞車）")
    stops = [e for e in sb.events() if e["ev"] == "Stop"]  # stops[0]＝第一回合（無守衛）
    ctx.check(any(e["payload"].get("stop_hook_active") for e in stops[2:]), "推回後沒有 stop_hook_active=True 的第二次 Stop")  # noqa: E501
    ctx.evidence(f"RV-KW5 {tr.coords(be[0])} 保溫閘推回；Stop payload background_tasks={stops[1]['payload'].get('background_tasks')!r}")  # noqa: E501
