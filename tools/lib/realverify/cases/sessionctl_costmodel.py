"""sessionctl_costmodel 家族：拿掉 25 萬換窗、改硬線＋按帳選路（R216；TCS-SessionSwitch-CostModel
E2E-SS-11／12／13 的硬線與 F4 部分）。

掌舵者 2026-11-18：「專注在不要讓 Cache 過期！25 萬就切換是自我閹割功能」；裁決只留硬線 850,000，
換 session 只剩兩種情況——快取已冷且按帳換新較便宜（F4）、上下文到硬線。

載具：沙盒（repo 外）＋真 `claude -p --model haiku` 產真逐字稿＋真 `sessionctl_guard.py` hook 行程／
真 `session_resume_planner.choose_resume_route` 行程（不 spawn）。

為什麼上下文要「改寫沙盒逐字稿的 usage 數字」而不是真長出 30 萬／85 萬：haiku 的視窗只有
20 萬 token，真實長不到；且 `claude -p -r` 回合結束後 Stop hook 讀到的是剛寫入的真記錄（小上下文）。
所以 Stop／PreToolUse／選路的判準用「真 hook 行程＋沙盒自己的真逐字稿（只改 usage 數字與時間戳）」
驗；真 harness 的接線另由 RV-C1（`claude -p` ＋ Stop hook，硬線下修）與 RV-M2（`claude -p` ＋ Agent
派工閘）負責。只改**沙盒自己**的逐字稿，不碰任何非沙盒 sid，不改被測碼，不開測試用環境變數鉤。

單案 token：每個真 `claude -p` 回合都極小（haiku、一句回覆；單案 ≤ 約 3 萬）。

未涵蓋（誠實劃界）：真 `claude -p` 的上下文真的長到 85 萬再被擋（haiku 視窗不足）；規格
E2E-SS-13 所指 planner「預演旗標」不存在，依 TCS 不得新增測試專用旗標，所以改呼叫 planner 的
正式選路入口 `choose_resume_route`（`_run_resume` 呼叫的同一函式；不經它的 spawn），仍是真行程
＋真逐字稿。
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from ..sandbox import REPO, Sandbox, venv_python
from . import CaseContext, case
from .sessionctl_handoff import (
    backdate_transcript,
    blocking_texts,
    install_sessionctl,
    sc_env,
    seal_session,
    set_ctx,
    spawn_trace,
)

HARD = 850_000
_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
#: 隔離封存閘／收斂閘本身：保溫閘（另一個 Stop 閘）在大上下文又無背景任務時也會推回，與本家族要驗的無關。  # noqa: E501
_ONLY_SEAL = {"AUTOSDD_KEEPWARM_OFF": "1"}


def _hook(sb: Sandbox, payload: dict, **env_extra: str) -> tuple[int, str, str]:
    """真跑沙盒內安裝的 `sessionctl_guard.py`（與 repo 原檔逐位元組相同，install 時已驗）：stdin 餵 payload。"""  # noqa: E501
    env = sb.env(sc_env(sb, **env_extra))
    env.pop("AUTOSDD_UNATTENDED", None)
    r = subprocess.run([venv_python(), str(sb.root / ".claude" / "hooks" / "sessionctl_guard.py")],  # noqa: S603
                       input=json.dumps(payload), cwd=str(sb.root), env=env, capture_output=True, text=True,  # noqa: E501
                       encoding="utf-8", errors="replace", timeout=60, creationflags=_NOWIN)
    return r.returncode, r.stdout, r.stderr


def _stop(sb: Sandbox, tpath: Path, **extra) -> dict:
    return {"hook_event_name": "Stop", "session_id": sb.sid, "transcript_path": str(tpath),
            "stop_hook_active": False, "background_tasks": [], "cwd": str(sb.root), **extra}


def _pre(sb: Sandbox, tpath: Path, tool: str) -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {}, "session_id": sb.sid,  # noqa: E501
            "transcript_path": str(tpath), "cwd": str(sb.root)}


def _seal_block(stdout: str) -> str:
    """Stop 輸出裡的封存閘推回理由；沒有推回 ⇒ ""。"""
    try:
        doc = json.loads(stdout) if stdout.strip() else {}
    except ValueError:
        return ""
    why = str(doc.get("reason") or "") if doc.get("decision") == "block" else ""
    return why if "封存閘" in why else ""


def _warm_session(ctx: CaseContext) -> tuple[Sandbox, Path]:
    """裝 sessionctl 的沙盒＋兩個真 `claude -p` 回合（第一回合暖身：單回合新 session 偶發量不到
    上下文，真主控都有前文）；回 (沙盒, 真逐字稿路徑)。"""
    sb = ctx.sandbox()
    install_sessionctl(sb)
    for i in (1, 2):
        r = ctx.run_claude(sb, f"Reply with exactly: RV_CM_WARM{i}", env_extra=sc_env(sb, **_ONLY_SEAL))  # noqa: E501
        ctx.check(r.rc == 0 and not r.timed_out, f"暖身回合 {i} rc={r.rc} {r.stderr[:200]}")
    tpath = ctx.transcript(sb).path
    ctx.check(tpath.is_file(), "沒有沙盒逐字稿")
    return sb, tpath


@case("RV-CM1", "sessionctl_costmodel", refs=("AT-SS-40", "AT-SS-42", "MU-17", "E2E-SS-06"))
def rv_cm1(ctx: CaseContext) -> None:
    """封存閘只認硬線：沙盒真逐字稿的上下文改成 25 萬／30 萬／534,000／849,999 ⇒ 真 Stop hook
    **不推回**；850,000 ⇒ 推回一次（含 `--finalize`、`硬線 850,000`）；`stop_hook_active` 為真 ⇒
    放行。另：舊 R1 鍵設成 1000 也不生效（退役不是改名）。真 `claude -p` 在出廠門檻下的小上下文
    回合同樣不被推回。"""
    sb, tpath = _warm_session(ctx)
    tr = ctx.transcript(sb)
    ctx.check(not [t for t in blocking_texts(tr, "Stop") if "封存閘" in t], "出廠門檻下真 `claude -p` 回合被封存閘推回")  # noqa: E501
    for used in (250_000, 300_000, 534_000, HARD - 1):
        ctx.check(set_ctx(tpath, used) >= 1, "逐字稿沒有帶 usage 的 assistant 記錄可改")
        rc, out, err = _hook(sb, _stop(sb, tpath), **_ONLY_SEAL)
        ctx.check(rc == 0 and not _seal_block(out), f"ctx={used:,} 被封存閘推回（25 萬換窗沒拿乾淨）：rc={rc} {out[:200]!r} {err[:200]!r}")  # noqa: E501
    rc, out, _ = _hook(sb, _stop(sb, tpath), AUTOSDD_SWITCH_R1_CTX_TOKENS="1000", **_ONLY_SEAL)
    ctx.check(rc == 0 and not _seal_block(out), f"已退役的 R1=1000 仍讓 ctx={HARD - 1:,} 被推回：{out[:200]!r}")  # noqa: E501
    set_ctx(tpath, HARD)
    rc, out, err = _hook(sb, _stop(sb, tpath), **_ONLY_SEAL)
    why = _seal_block(out)
    ctx.check(rc == 0 and bool(why), f"ctx={HARD:,} 沒有被封存閘推回：rc={rc} {out[:200]!r} {err[:200]!r}")  # noqa: E501
    ctx.check("--finalize" in why and "硬線 850,000" in why, f"推回內容缺 --finalize／硬線 850,000：{why[:240]!r}")  # noqa: E501
    rc, out, _ = _hook(sb, _stop(sb, tpath, stop_hook_active=True), **_ONLY_SEAL)
    ctx.check(rc == 0 and not _seal_block(out), "stop_hook_active 為真仍推回（迴圈煞車失效）")
    rows = spawn_trace(sb, "seal_stop_block")
    ctx.check(len(rows) == 1 and rows[0].get("hard") == HARD and rows[0].get("ctx") == HARD,
              f"seal_stop_block 痕跡應恰一筆且 ctx＝hard＝{HARD:,}：{rows}")
    ctx.evidence(f"RV-CM1 {sb.sid[:8]} 25 萬／30 萬／534,000／849,999 不推回；850,000 推回一次；R1 鍵無效")  # noqa: E501


@case("RV-CM2", "sessionctl_costmodel", refs=("AT-SS-43", "MU-19", "E2E-SS-11"))
def rv_cm2(ctx: CaseContext) -> None:
    """收斂閘只認硬線、不要求出聲：沙盒沒有任何 `<sid>.advised`，真 PreToolUse hook 對
    Agent／Task／Workflow 在 850,000 ⇒ rc 2（含 `收斂閘`、三條出口）、849,999 ⇒ rc 0；30 萬 ⇒ rc 0；
    Read 在 850,000 仍 rc 0。"""
    sb, tpath = _warm_session(ctx)
    adv = list((sb.root / "handoff").glob(f"{sb.sid}*.advised")) if (sb.root / "handoff").is_dir() else []  # noqa: E501
    ctx.check(not adv, f"前提：沙盒不該有出聲閂鎖：{adv}")
    for used, want in ((300_000, 0), (HARD - 1, 0), (HARD, 2)):
        set_ctx(tpath, used)
        for tool in ("Agent", "Task", "Workflow"):
            rc, out, err = _hook(sb, _pre(sb, tpath, tool), **_ONLY_SEAL)
            ctx.check(rc == want, f"{tool} ctx={used:,} rc={rc}（要 {want}）：{err[:200]!r}")
            if want == 2:
                ctx.check("收斂閘" in err and "硬線 850,000" in err and "handoff --finalize" in err, f"阻斷訊息缺字：{err[:300]!r}")  # noqa: E501
    rc, out, err = _hook(sb, _pre(sb, tpath, "Read"), **_ONLY_SEAL)
    ctx.check(rc == 0 and not err.strip(), f"Read 不該被擋：rc={rc} {err[:200]!r}")
    ctx.evidence(f"RV-CM2 {sb.sid[:8]} 無 .advised：Agent／Task／Workflow 849,999 放行、850,000 rc 2；30 萬放行")  # noqa: E501


_ROUTE = (
    "import json,sys,os;sys.path[:0]=[sys.argv[1]+'/tools',sys.argv[1]+'/tools/lib'];"
    "import session_resume_planner as p;from pathlib import Path;"
    "r=p.choose_resume_route('claude',sys.argv[2],Path(sys.argv[3]),sys.argv[4]);"
    "print(json.dumps({'strategy':r['strategy'],'reason':r['reason'],'dash_r':'-r' in (r.get('argv') or [])},ensure_ascii=False))"  # noqa: E501
)


def _route(sb: Sandbox, tpath: Path, **env_extra: str) -> dict:
    """真行程跑 planner 的正式選路入口（`_run_resume` 呼叫的同一函式；回字典、不 spawn）。"""
    plan = sb.write_file("plan.md", "# 任務書\n")
    env = sb.env(sc_env(sb, AUTOSDD_HANDBACK_DIR=str(sb.root / "hb"), **env_extra))
    env.pop("AUTOSDD_UNATTENDED", None)
    r = subprocess.run([venv_python(), "-c", _ROUTE, str(REPO), sb.sid, str(tpath), str(plan)],  # noqa: S603
                       cwd=str(sb.root), env=env, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120, creationflags=_NOWIN)
    if r.returncode != 0:
        raise AssertionError(f"選路行程 rc={r.returncode}：{r.stderr[-300:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


@case("RV-CM3", "sessionctl_costmodel", refs=("AT-SS-46", "AT-SS-47", "MU-20", "MU-21", "E2E-SS-13"))  # noqa: E501
def rv_cm3(ctx: CaseContext) -> None:
    """無人續跑選路按帳：快取冷（逐字稿時間戳往前 3 小時）＋真小上下文 ⇒ RESUME（帶 `-r`）；
    冷＋改寫成 25 萬 ⇒ 仍 RESUME（舊 R1 判 FRESH）；冷＋480,000 ⇒ RESUME、480,001 ⇒ FRESH（理由含
    F4）；熱＋80 萬 ⇒ RESUME；冷＋兩個 compact_boundary ⇒ FRESH（理由含 R2，與成本無關）；R3 鍵設了
    也不生效。"""
    sb, tpath = _warm_session(ctx)
    backdate_transcript(tpath, 3)
    real = _route(sb, tpath)
    ctx.check(real["strategy"] == "SESSION_RESUME" and real["dash_r"], f"冷＋真小上下文應 RESUME：{real}")  # noqa: E501
    for used, want_fresh in ((250_000, False), (480_000, False), (480_001, True), (HARD, True)):
        set_ctx(tpath, used)
        got = _route(sb, tpath, AUTOSDD_SWITCH_R3_CACHE_CREATION_TOKENS="1")
        fresh = got["strategy"] == "FRESH_SESSION_WITH_STATE"
        ctx.check(fresh == want_fresh and (not fresh or "F4" in got["reason"]) and fresh != got["dash_r"],  # noqa: E501
                  f"冷 ctx={used:,} 選路不符（要 {'FRESH' if want_fresh else 'RESUME'}）：{got}")
    # 熱：把時間戳推回現在（再往後推 3 小時抵銷先前的回推），大上下文也不判 F4
    backdate_transcript(tpath, -3)
    set_ctx(tpath, 800_000)
    hot = _route(sb, tpath)
    ctx.check(hot["strategy"] == "SESSION_RESUME" and hot["dash_r"], f"熱快取＋80 萬應 RESUME（F4 只在已冷後才判）：{hot}")  # noqa: E501
    # R2：兩個 compact_boundary（品質訊號），熱也要 FRESH
    stamp = datetime.now().astimezone().isoformat()
    with tpath.open("a", encoding="utf-8", newline="\n") as f:
        for _ in range(2):
            f.write(json.dumps({"type": "system", "subtype": "compact_boundary", "content": "Conversation compacted",  # noqa: E501
                                "level": "info", "timestamp": stamp, "sessionId": sb.sid}) + "\n")
    r2 = _route(sb, tpath)
    ctx.check(r2["strategy"] == "FRESH_SESSION_WITH_STATE" and "R2" in r2["reason"] and not r2["dash_r"], f"兩次壓縮應 FRESH（R2）：{r2}")  # noqa: E501
    ctx.evidence(f"RV-CM3 {sb.sid[:8]} 冷小→RESUME、冷 480,000→RESUME／480,001→FRESH(F4)、熱 80 萬→RESUME、R2→FRESH")  # noqa: E501


@case("RV-CM4", "sessionctl_costmodel", refs=("AT-SS-48", "MU-22", "E2E-SS-12"))
def rv_cm4(ctx: CaseContext) -> None:
    """轉送加 F4（真 `claude -p` ＋真 UserPromptSubmit hook）：已封存、快取冷（逐字稿時間戳往前
    3 小時）、上下文改寫成 40 萬 ⇒ 提示**照常送進本視窗**（assistant 有回覆、沒有「已轉到新
    session」、沒開視窗），痕跡 `forward_pass cond=10`；同樣情境上下文改 60 萬的轉送（會真開窗）由
    RV-F1 負責（它已改寫成 60 萬）。"""
    sb = ctx.sandbox()
    seal_session(ctx, sb)
    tpath = ctx.transcript(sb).path
    set_ctx(tpath, 400_000)
    backdate_transcript(tpath, 3)
    r = ctx.run_claude(sb, "RV_CM4_PROMPT Reply with exactly: RV_CM4_OK", env_extra=sc_env(sb, **_ONLY_SEAL), timeout_s=150)  # noqa: E501
    ctx.check(r.rc == 0 and not r.timed_out, f"冷窗小上下文提示 rc={r.rc} timed_out={r.timed_out} {r.stderr[:200]}")  # noqa: E501
    tr = ctx.transcript(sb)
    ctx.check(not tr.blocked_user_prompts("已轉到新 session"), "快取冷但續跑較便宜，卻被轉送到新 session（F4 沒擋）")  # noqa: E501
    ctx.check(any("RV_CM4_OK" in t for t in tr.assistant_texts()), "提示沒有 assistant 回覆（被吞？）")  # noqa: E501
    passes = [x for x in spawn_trace(sb, "forward_pass") if x.get("cond") == 10]
    ctx.check(bool(passes), f"沒有 forward_pass cond=10 痕跡：{[(x.get('cond'), x.get('why')) for x in spawn_trace(sb, 'forward_pass')]}")  # noqa: E501
    ctx.check(not spawn_trace(sb, "session_switch_spawned"), "不該開任何視窗")
    ctx.evidence(f"RV-CM4 {sb.sid[:8]} 冷＋40 萬：留在原視窗，forward_pass cond=10；ctx={passes[-1].get('ctx')}")  # noqa: E501

