"""sessionctl_watch 家族：監督閘（RV-S1／S2）與 `sessionctl watch` 六種判決（RV-W1～W6）。

全部用真 `claude -p --model haiku`（沙盒掛 repo 真守衛 `sessionctl_guard.py`）＋真 `tools/sessionctl.py
watch` 子行程＋真逐字稿／真名冊檔。時間類條件只做兩件事：以參數／env 下修門檻（`--wall-min`、
`--ctx-max`、`AUTOSDD_QUOTA_PREPARE_PCT`），或把**沙盒自己的**代理逐字稿「複製一份並改寫時間戳」餵給
`--projects-dir`（RV-W3 停滯，因 `--stall-min` 有 11 分下限）；不改守衛判準、不 monkeypatch 被測模組。

本檔同時是 `sessionctl_gates.py`／`pending_handoff.py` 的共用輔助來源（私有 `_` 函式、不進核心）。
"""  # noqa: E501

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from ..driver import EnvMissing, RunResult, run_claude
from ..sandbox import REPO, Sandbox, projects_dir
from ..transcript import Transcript
from . import CaseContext, case

SESSIONCTL = REPO / "tools" / "sessionctl.py"
GUARD = ".claude/hooks/sessionctl_guard.py"
GUARD_PRE_MATCHER = "SendMessage|Agent|Task|Workflow"
# 沙盒的 -p 預設拒絕代理的 shell 工具（實測 2026-11-18：「Its Bash tool was denied」）⇒ 要讓代理真的
# 停留一陣子，沙盒（repo 外的拋棄式目錄）一律以 bypassPermissions 跑。
BYPASS = ("--permission-mode", "bypassPermissions")
# 非量額度的案例把 prepare 門檻拉到 99（halt 100），免得本機當下的真實額度讀數搶先成立 quota 判決而污染判定。  # noqa: E501
NO_QUOTA = {"AUTOSDD_QUOTA_PREPARE_PCT": "99", "AUTOSDD_QUOTA_HALT_PCT": "100"}  # 門檻階梯須嚴格遞增，prepare 不能 ≥ halt  # noqa: E501


# W5 專用：四個錨點須嚴格遞增且 compact 邊際 < prepare−converge，所以整組下修（env 只准下修方向的合法組合）。  # noqa: E501
_LOW_QUOTA = {"AUTOSDD_QUOTA_NOTICE_PCT": "20", "AUTOSDD_QUOTA_CONVERGE_PCT": "30", "AUTOSDD_QUOTA_PREPARE_PCT": "40"}  # noqa: E501


# ───────────────────────────── 共用輔助 ─────────────────────────────
def _install_guard(sb: Sandbox) -> None:
    """沙盒掛 repo 真的 sessionctl 守衛：Stop＋PreToolUse（派工／SendMessage）。"""
    sb.add_repo_hook("Stop", GUARD)
    sb.add_repo_hook("PreToolUse", GUARD, matcher=GUARD_PRE_MATCHER)


def _install_watch_guard(sb: Sandbox) -> None:
    """監督閘／watch 判決案例專用：守衛＋關掉保溫閘（`AUTOSDD_KEEPWARM_OFF`，經沙盒 settings.json 的 env，
    hook 與工具 shell 都繼承）。WHY：R216 的保溫閘在「無任何在飛背景工作、上下文 ≥ 3 萬 token」的 Stop 推回，
    haiku 的第一回合上下文就在門檻附近 ⇒ 時有時無；推回後 haiku 乖乖掛 45 分鐘的 keepwarm，
    `claude -p` 被它拖到逾時（RV-S2／RV-W4 真機實證 2026-11-19）。本家族測的是監督閘與 watch 判決，
    保溫閘由 sessionctl_keepwarm 家族獨立驗，這裡必須讓它確定性不介入，而不是賭上下文大小。"""  # noqa: E501
    _install_guard(sb)
    sb.settings["env"] = {**sb.settings.get("env", {}), "AUTOSDD_KEEPWARM_OFF": "1"}
    sb.write_settings()


def _bg_agent_prompt(sleep_s: int, *, background: bool = True) -> str:
    bg = "true" if background else "false"
    return (
        f"Use the Agent tool exactly once with run_in_background={bg}, subagent_type general-purpose, "  # noqa: E501
        "model haiku, description 'rv sleeper', prompt: \"Run exactly this one command with the "
        "PowerShell tool in the foreground (no run_in_background, timeout 300000; do NOT use "
        f"Start-Sleep, it is blocked): & '{sys.executable}' -c 'import time; time.sleep({sleep_s})' "  # noqa: E501
        "and when it returns reply with the single word DONE\". After launching, end your turn "
        "immediately with the single word LAUNCHED. Do not wait for the agent."
    )


def _subagent_files(sb: Sandbox) -> list[Path]:
    out: list[Path] = []
    for d in sb.transcript_dirs():
        out += sorted((d / sb.sid / "subagents").glob("agent-*.jsonl"))
    return out


def _meta_of(agent_jsonl: Path) -> dict:
    try:
        return json.loads(agent_jsonl.with_name(agent_jsonl.stem + ".meta.json").read_text(encoding="utf-8"))  # noqa: E501
    except (OSError, ValueError):
        return {}


def _agent_id(path: Path) -> str:
    return path.stem.removeprefix("agent-")


class _Bg:
    """背景跑一次 `claude -p`（讓測試行程在代理還活著時去跑 watch／讀名冊）。"""

    def __init__(self, sb: Sandbox, prompt: str, **kw):
        self.res: RunResult | None = None
        self.exc: BaseException | None = None
        self._t = threading.Thread(target=self._run, args=(sb, prompt, kw), daemon=True)
        self._t.start()

    def _run(self, sb, prompt, kw):
        try:
            self.res = run_claude(sb, prompt, **kw)
        except BaseException as exc:  # noqa: BLE001 — 轉給主執行緒
            self.exc = exc

    def done(self) -> bool:
        return not self._t.is_alive()

    def join(self, timeout: float) -> RunResult:
        self._t.join(timeout)
        if self._t.is_alive():
            raise AssertionError(f"背景 claude -p 逾時未結束（{timeout:.0f}s）")
        if self.exc is not None:
            raise self.exc
        assert self.res is not None
        return self.res


def _wait_running_agent(ctx: CaseContext, sb: Sandbox, bg: _Bg, timeout_s: float = 150) -> Path:
    """等沙盒出現一支「未交卷」的代理逐字稿並回其路徑；claude 先死／逾時 ⇒ fail。"""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        for p in _subagent_files(sb):
            if _meta_of(p).get("finished") is not True:
                # 等代理至少有一筆 assistant usage（上下文量得到），才算「真的在跑」
                txt = p.read_text(encoding="utf-8", errors="replace")
                if '"usage"' in txt and re.search(r'"stop_reason":\s*"tool_use"', txt):
                    return p
        if bg.done():
            r = bg.join(1)
            ctx.check(False, f"claude 已結束（rc={r.rc}）仍沒出現未交卷代理：{r.stdout[:200]!r} {r.stderr[:200]!r}")  # noqa: E501
        time.sleep(1.0)
    ctx.check(False, f"{timeout_s:.0f}s 內沒出現未交卷代理逐字稿")
    raise AssertionError  # pragma: no cover


def _watch(sb: Sandbox, *args: str, env_extra: dict | None = None, timeout_s: float = 240):
    """真 `python tools/sessionctl.py watch --sid <沙盒 sid> …`；回 (rc, stdout＋stderr, 末行判決)。"""  # noqa: E501
    argv = [sys.executable, str(SESSIONCTL), "watch", "--sid", sb.sid, *args]
    proc = subprocess.Popen(  # noqa: S603
        argv, cwd=str(sb.root), env=sb.env({**NO_QUOTA, **(env_extra or {})}),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    sb.procs.append(proc)
    try:
        out, _ = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        return -9, out.decode("utf-8", errors="replace"), ""
    text = out.decode("utf-8", errors="replace")
    verdicts = [ln for ln in text.splitlines() if ln.startswith("WATCH_VERDICT=")]
    return proc.returncode, text, (verdicts[-1] if verdicts else "")


def _check_verdict(ctx: CaseContext, got, want_event: str, label: str) -> str:
    """判決一律 rc 0（DEF-200-622：harness 把非 0 背景指令顯示成 failed），事件只看末行。"""
    rc, text, last = got
    ctx.check(rc == 0, f"{label}：watch rc={rc}（要 0；判決只看末行）；輸出：{text[-400:]!r}")
    ctx.check(last.startswith(f"WATCH_VERDICT={want_event} "), f"{label}：末行判決={last!r}（要 {want_event}）")  # noqa: E501
    ctx.check("rc=" not in last, f"{label}：判決行不該再帶 rc 欄：{last!r}")
    return last


def _tool_result_texts(tr: Transcript) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for r in tr.recs:
        msg = r.data.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        for c in content if isinstance(content, list) else ():
            if isinstance(c, dict) and c.get("type") == "tool_result":
                body = c.get("content")
                if isinstance(body, list):
                    body = " ".join(str(x.get("text", "")) for x in body if isinstance(x, dict))
                out.append((r.line, str(body)))
    return out


# ───────────────────────────── RV-S1／S2：監督閘 ─────────────────────────────
@case("RV-S1", "sessionctl_watch", refs=("V-W2",))
def rv_s1(ctx: CaseContext) -> None:
    """有在飛背景子代理、沒掛 watch ⇒ 真 Stop 守衛推回（逐字稿 hook_blocking_error 帶 watch 指路）；
    第二次 Stop（stop_hook_active）放行。"""
    sb = ctx.sandbox()
    _install_watch_guard(sb)
    r = ctx.run_claude(sb, _bg_agent_prompt(20), extra_args=BYPASS, timeout_s=300)
    ctx.check(r.rc == 0 and not r.timed_out, f"claude -p rc={r.rc} {r.stderr[:200]}")
    tr = ctx.transcript(sb)
    be = tr.hook_blocking_errors("Stop", "sessionctl.py watch")
    ctx.check(bool(be), "逐字稿沒有 Stop hook_blocking_error（含 `sessionctl.py watch` 指路）")
    ctx.check("監督閘" in str(be[0].data["attachment"]), "推回理由不是監督閘（sessionctl_guard supervise 分支）")  # noqa: E501
    stops = [e for e in sb.events() if e["ev"] == "Stop"]
    first = stops[0]["payload"]
    tasks = first.get("background_tasks") or []
    ctx.check(any(t.get("type") == "subagent" and t.get("status") == "running" for t in tasks),
              f"第一次 Stop payload 沒有在飛的子代理（推回前提不成立）：{tasks}")
    ctx.check(len(tr.hook_blocking_errors("Stop", "監督閘")) == 1, "監督閘推回次數不是恰好 1（迴圈煞車失效？）")  # noqa: E501
    ctx.check(any(e["payload"].get("stop_hook_active") for e in stops[1:]),
              "推回後沒有出現 stop_hook_active=True 的第二次 Stop（無法證明放行）")
    ctx.evidence(f"RV-S1 {tr.coords(be[0])} 監督閘推回；Stop payload 在飛子代理 {tasks[0].get('id')}")  # noqa: E501


@case("RV-S2", "sessionctl_watch", refs=("V-W2",))
def rv_s2(ctx: CaseContext) -> None:
    """同一情境但掛了真 `sessionctl watch` 背景 shell ⇒ Stop 不推回，改出 systemMessage「看管中」。"""  # noqa: E501
    sb = ctx.sandbox()
    _install_watch_guard(sb)
    # 命令內自帶 env：harness 的工具 shell 不一定繼承 claude 行程的自訂變數
    watch_cmd = (f"$env:AUTOSDD_QUOTA_PREPARE_PCT='99'; $env:AUTOSDD_QUOTA_HALT_PCT='100'; & '{sys.executable}' '{SESSIONCTL}' watch --sid {sb.sid} --stall-min 20 "  # noqa: E501
                 "--poll-sec 3 --grace-sec 90")
    prompt = (
        "Make exactly these two tool calls in ONE assistant message, in parallel. "
        f"CALL 1: the PowerShell tool with run_in_background=true and this exact command: {watch_cmd}\n"  # noqa: E501
        f"CALL 2: {_bg_agent_prompt(60).split('After launching')[0]}\n"
        "After both calls return, end your turn immediately with the single word LAUNCHED. "
        "Never start any other command, even if a hook objects.")
    r = ctx.run_claude(sb, prompt, extra_args=BYPASS, timeout_s=420,
                       env_extra={**NO_QUOTA})
    ctx.check(r.rc == 0 and not r.timed_out, f"claude -p rc={r.rc} {r.stderr[:200]}")
    tr = ctx.transcript(sb)
    stops = [e for e in sb.events() if e["ev"] == "Stop"]
    first = stops[0]["payload"]
    tasks = first.get("background_tasks") or []
    ctx.check(any(t.get("type") == "subagent" and t.get("status") == "running" for t in tasks)
              and any(t.get("type") == "shell" and re.search(r"sessionctl\.py[\"']?\s+watch", str(t.get("command"))) for t in tasks),  # noqa: E501
              f"第一次 Stop 缺在飛子代理或 watch shell：{tasks}")
    ctx.check(not tr.hook_blocking_errors("Stop", "監督閘"), "掛了 watch 仍被監督閘推回（憑證判準壞了）")  # noqa: E501
    sm = tr.system_messages("Stop", "看管中")
    ctx.check(bool(sm), "逐字稿沒有 Stop hook_system_message 含「看管中」")
    ctx.evidence(f"RV-S2 {tr.coords(sm[0])} {sm[0].data['attachment'].get('content')}")


# ───────────────────────────── RV-W1～W5：watch 判決 ─────────────────────────────
@case("RV-W1", "sessionctl_watch", refs=("V-W4",))
def rv_w1(ctx: CaseContext) -> None:
    """真背景代理交卷 ⇒ watch 末行 all_done（一律 rc 0）；記錄 `meta.finished` 實值（V-W4），斷言 all_done 不提早成立。"""  # noqa: E501
    sb = ctx.sandbox()
    _install_watch_guard(sb)
    bg = _Bg(sb, _bg_agent_prompt(30), extra_args=BYPASS, timeout_s=420)
    agent = _wait_running_agent(ctx, sb, bg)
    before = _meta_of(agent).get("finished")
    ctx.check(before is not True, f"watch 啟動前代理 meta.finished 已是 True：{before!r}")
    t0 = time.monotonic()
    # --grace-sec 600：寬限期後備援不可能成立 ⇒ all_done 只能走「看過代理、現在全交卷」那條
    got = _watch(sb, "--poll-sec", "2", "--grace-sec", "600", "--stall-min", "20")
    elapsed = time.monotonic() - t0
    last = _check_verdict(ctx, got, "all_done", "RV-W1")
    after = _meta_of(agent).get("finished")
    ctx.check(after is True, f"all_done 成立時代理 meta.finished={after!r}（提早成立）")
    ctx.check(elapsed >= 3, f"watch 只跑了 {elapsed:.1f}s，疑似未等代理交卷")
    r = bg.join(300)
    ctx.check(r.rc == 0, f"背景 claude rc={r.rc}")
    ctx.evidence(f"RV-W1 {last}；meta.finished 前={before!r} 後={after!r}；watch 等了 {elapsed:.0f}s")  # noqa: E501


@case("RV-W2", "sessionctl_watch")
def rv_w2(ctx: CaseContext) -> None:
    """單支逾時門檻調低（--wall-min 0.2＝12 秒）而代理還在跑 ⇒ overrun（rc 0）。"""
    sb = ctx.sandbox()
    _install_watch_guard(sb)
    bg = _Bg(sb, _bg_agent_prompt(60), extra_args=BYPASS, timeout_s=420)
    agent = _wait_running_agent(ctx, sb, bg)
    got = _watch(sb, "--poll-sec", "2", "--grace-sec", "600", "--stall-min", "20", "--wall-min", "0.2")  # noqa: E501
    last = _check_verdict(ctx, got, "overrun", "RV-W2")
    ctx.check(_agent_id(agent)[:10] in got[1], "overrun 明細沒有列出該代理")
    ctx.check(_meta_of(agent).get("finished") is not True, "overrun 成立時代理其實已交卷（不是在跑時判逾時）")  # noqa: E501
    bg.join(300)
    ctx.evidence(f"RV-W2 {last}；代理 {_agent_id(agent)[:10]}")


@case("RV-W3", "sessionctl_watch")
def rv_w3(ctx: CaseContext) -> None:
    """代理停住（最後一筆是 tool_use、靜默 ≥ 門檻）⇒ stall（rc 0）。

    `--stall-min` 下限 11 分鐘（低於即退回 15），真等不划算 ⇒ 把**沙盒自己的**真代理逐字稿截到
    「發出工具呼叫、尚無結果」並整份時間戳往前推 40 分鐘，複製到 `--projects-dir`（不動原檔）。"""
    sb = ctx.sandbox()
    _install_watch_guard(sb)
    bg = _Bg(sb, _bg_agent_prompt(40), extra_args=BYPASS, timeout_s=420)
    agent = _wait_running_agent(ctx, sb, bg)
    tmp = Path(tempfile.mkdtemp(prefix="AutoSDD_RV_w3_"))
    try:
        sub = tmp / "slug" / sb.sid / "subagents"
        sub.mkdir(parents=True)
        lines = [json.loads(ln) for ln in agent.read_text(encoding="utf-8").splitlines() if ln.strip()]  # noqa: E501
        cut = [i for i, d in enumerate(lines)
               if d.get("type") == "assistant" and any(c.get("type") == "tool_use" for c in (d.get("message") or {}).get("content", []) if isinstance(c, dict))]  # noqa: E501
        ctx.check(bool(cut), "代理逐字稿沒有任何工具呼叫記錄（無法造停住態）")
        kept = lines[: cut[0] + 1]
        shift = timedelta(minutes=40)
        for d in kept:
            if d.get("timestamp"):
                t = datetime.fromisoformat(str(d["timestamp"]).replace("Z", "+00:00")) - shift
                d["timestamp"] = t.isoformat().replace("+00:00", "Z")
        (sub / agent.name).write_text("\n".join(json.dumps(d, ensure_ascii=False) for d in kept) + "\n", encoding="utf-8")  # noqa: E501
        meta = _meta_of(agent)
        meta.pop("finished", None)
        (sub / agent.with_name(agent.stem + ".meta.json").name).write_text(json.dumps(meta), encoding="utf-8")  # noqa: E501
        got = _watch(sb, "--projects-dir", str(tmp), "--stall-min", "11", "--poll-sec", "1",
                     "--grace-sec", "600")
        last = _check_verdict(ctx, got, "stall", "RV-W3")
        ctx.check("靜默" in got[1], "stall 明細沒有靜默分鐘數")
        # 反向：同一份資料若最後一筆是 assistant end_turn（代理在等自己的背景 shell）不該判 stall
        # ——由單元測試守，這裡不重造；本案例只證明「真代理逐字稿格式」被真 watch 判成 stall。
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bg.join(300)
    ctx.evidence(f"RV-W3 {last}；原檔 {_agent_id(agent)[:10]} 未動（複本時間戳 -40 分、截在第一個 tool_use）")  # noqa: E501


@case("RV-W4", "sessionctl_watch")
def rv_w4(ctx: CaseContext) -> None:
    """代理上下文 ≥ 門檻（--ctx-max 1，只准下修）⇒ budget（rc 0）。"""
    sb = ctx.sandbox()
    _install_watch_guard(sb)
    bg = _Bg(sb, _bg_agent_prompt(40), extra_args=BYPASS, timeout_s=420)
    agent = _wait_running_agent(ctx, sb, bg)
    got = _watch(sb, "--poll-sec", "2", "--grace-sec", "600", "--stall-min", "20", "--ctx-max", "1")
    last = _check_verdict(ctx, got, "budget", "RV-W4")
    ctx.check("token" in got[1], "budget 明細沒有上下文 token 數")
    bg.join(300)
    ctx.evidence(f"RV-W4 {last}；代理 {_agent_id(agent)[:10]}")


@case("RV-W5", "sessionctl_watch")
def rv_w5(ctx: CaseContext) -> None:
    """短窗額度原始讀數 ≥ prepare 門檻 ⇒ quota（rc 0）。

    讀數＝**沙盒專屬**額度快取（`AUTOSDD_QUOTA_CACHE_DIR` 指向沙盒，絕不碰主控的真快取）：session 軸 50pp、
    reset 在 2 小時後；prepare 門檻合法下修到 40（env 只准下修）。本機真實讀數通常遠低於門檻（2026-11-19
    實測 7pp），拿它當輸入案例就不可自驗；watch 讀快取的程式路徑與真機完全相同、不 monkeypatch。"""  # noqa: E501
    from .sessionctl_park import axis, write_quota  # noqa: PLC0415 — 沙盒快取寫入輔助（同一 SSOT）

    sb = ctx.sandbox()
    _install_watch_guard(sb)
    write_quota(sb, [axis("session", 50.0, 120), axis("weekly_all", 10.0, 6000)])
    bg = _Bg(sb, _bg_agent_prompt(30), extra_args=BYPASS, timeout_s=420)
    _wait_running_agent(ctx, sb, bg)
    got = _watch(sb, "--poll-sec", "2", "--grace-sec", "600", "--stall-min", "20",
                 env_extra={**_LOW_QUOTA, "AUTOSDD_QUOTA_CACHE_DIR": str(sb.root / "qcache")})
    _rc, text, last = got
    if last.startswith("WATCH_VERDICT=") and "quota" not in last:
        # 本機量不到短窗軸（或 reset 不在未來）⇒ 是環境缺件，不是被測物壞掉；不得當綠
        bg.join(300)
        raise EnvMissing(f"本機量不到短窗額度讀數，無法觸發 quota 判決：{last}")
    _check_verdict(ctx, got, "quota", "RV-W5")
    ctx.check("prepare" in text, "quota 明細沒有 prepare 門檻字樣")
    bg.join(300)
    ctx.evidence(f"RV-W5 {last}")


# ───────────────────────────── RV-W6：保溫點（長案）─────────────────────────────
@case("RV-W6", "sessionctl_watch", refs=("V-W3", "DEF-200-597"), long=True)
def rv_w6(ctx: CaseContext) -> None:
    """V-W3：沒有任何事件時 watch 在保溫點（主控最後一筆帶 usage 的 assistant 記錄＋45 分鐘；R216 起不再是
    watch 啟動＋50 分）才結束＝keepwarm（rc 0）；保溫之前主控沒有 compact_boundary；叫醒後 `-r` 的第一個回合
    cache_read ≥ 0.95×前一回合上下文。"""  # noqa: E501
    sb = ctx.sandbox()
    r1 = ctx.run_claude(sb, "Reply with exactly: ok")
    ctx.check(r1.rc == 0, f"第一回合 rc={r1.rc} {r1.stderr[:200]}")
    anchor = max(datetime.fromisoformat(r.ts.replace("Z", "+00:00")).timestamp() for r in ctx.transcript(sb).recs  # noqa: E501
                 if r.data.get("type") == "assistant" and isinstance((r.data.get("message") or {}).get("usage"), dict) and r.ts)  # noqa: E501
    t0 = time.monotonic()
    proc_env = sb.env(NO_QUOTA)
    proc = subprocess.Popen(  # noqa: S603
        [sys.executable, str(SESSIONCTL), "watch", "--sid", sb.sid, "--poll-sec", "30", "--grace-sec", "99999"],  # noqa: E501
        cwd=str(sb.root), env=proc_env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    sb.procs.append(proc)
    time.sleep(70)
    hb = _heartbeat(sb)
    ctx.check(hb is not None, "watch 跑了 70 秒仍沒有心跳檔（trace_dir/watch/<sid>.json）")
    kw_at = datetime.fromisoformat(hb["keepwarm_at"])
    ctx.check(abs(kw_at.timestamp() - (anchor + 45 * 60)) < 5, f"心跳 keepwarm_at 不是主控最後記錄＋45 分：{hb}")  # noqa: E501
    out, _ = proc.communicate(timeout=60 * 60)
    elapsed = time.monotonic() - t0
    text = out.decode("utf-8", errors="replace")
    last = [ln for ln in text.splitlines() if ln.startswith("WATCH_VERDICT=")][-1:]
    ctx.check(proc.returncode == 0 and last and last[0].startswith("WATCH_VERDICT=keepwarm"),
              f"watch rc={proc.returncode} 末行={last}：{text[-300:]!r}")
    ctx.check(time.time() >= anchor + 45 * 60 - 3, f"keepwarm 只等了 {elapsed / 60:.1f} 分（早於主控最後記錄＋45 分的保溫點）")  # noqa: E501
    tr = ctx.transcript(sb)
    ctx.check(not tr.compact_boundaries(), "保溫點之前主控逐字稿已有 compact_boundary（閒置壓縮早於保溫）")  # noqa: E501
    r2 = ctx.run_claude(sb, "Reply with exactly: ok2")
    ctx.check(r2.rc == 0, f"叫醒後回合 rc={r2.rc}")
    tr = ctx.transcript(sb)
    usages = [(r.line, (r.data.get("message") or {}).get("usage")) for r in tr.recs
              if r.data.get("type") == "assistant" and isinstance((r.data.get("message") or {}).get("usage"), dict)]  # noqa: E501
    ctx.check(len(usages) >= 2, "逐字稿 assistant usage 不足兩筆")
    (_, prev), (ln, cur) = usages[-2], usages[-1]
    prev_ctx = sum(int(prev.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))  # noqa: E501
    got = int(cur.get("cache_read_input_tokens") or 0)
    ctx.check(got >= 0.95 * prev_ctx, f"叫醒後第一回合 cache_read={got} < 0.95×前一回合上下文 {prev_ctx}（快取已冷）")  # noqa: E501
    ctx.evidence(f"RV-W6 {last[0]}；等 {elapsed / 60:.1f} 分；{sb.sid[:8]}:{ln} cache_read={got}／前回合 {prev_ctx}")  # noqa: E501


def _heartbeat(sb: Sandbox) -> dict | None:
    p = sb.root / "traces" / "watch" / f"{sb.sid}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


_ = (re, projects_dir)  # 保留給兄弟案例檔 import 的共用符號
