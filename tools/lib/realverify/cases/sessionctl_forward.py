"""sessionctl_forward 家族：RV-F1（冷窗轉送，備援路徑）、RV-F2（已交棒告知）、RV-F3（`留：` 放行）。

三案共用一個場景（`_scenario`，只開**一個**真視窗，由 F1 的轉送自己開出；F2 需要「已交棒＋新視窗
行程仍活著」的真前提，正好沿用它）：先跑到的案例負責執行並收窗，其餘案例只重放各自那段結論。
限制（掌舵者 2026-11-18 指示）：新沙盒目錄的互動 claude 會卡在資料夾信任對話框，不改使用者層
設定繞過 ⇒ 轉送成功的憑證是「視窗行程以含交接包路徑與原文檔路徑的命令列被開出」，不等新逐字稿。
視窗在場景 finally 依 pid＋命令列（含沙盒 sid）驗身分後立即收掉。
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from pathlib import Path

from ..sandbox import Sandbox
from . import CaseContext, case
from .sessionctl_handoff import (
    CLOSE_HINT,
    backdate_transcript,
    blocking_texts,  # noqa: F401
    cmdline_of,
    kill_verified,
    pid_alive,
    run_cli,
    sc_env,
    seal_session,
    set_ctx,
    spawn_trace,
)

BODY_MARK = "<!-- forward-body -->\n"
_CACHE: dict[str, dict] = {}


def _forward_files(sb: Sandbox, pkg: Path) -> list[Path]:
    return sorted(pkg.parent.glob(f"{pkg.stem}.forward-*.md"))


def _body_of(p: Path) -> str:
    return p.read_text(encoding="utf-8").split(BODY_MARK, 1)[1]


def _traces(sb: Sandbox, event: str, **eq) -> list[dict]:
    return [r for r in spawn_trace(sb, event) if all(r.get(k) == v for k, v in eq.items())]


def _blocked(ctx: CaseContext, sb: Sandbox, contains: str) -> list:
    return ctx.transcript(sb).blocked_user_prompts(contains)


def _append_compact_boundary(path: Path, sid: str) -> None:
    now = datetime.now().astimezone().isoformat().replace("+00:00", "Z")
    rec = {"type": "system", "subtype": "compact_boundary", "content": "Conversation compacted",
           "level": "info", "timestamp": now, "sessionId": sid, "uuid": str(uuid.uuid4()),
           "isSidechain": False, "parentUuid": None}
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _phase(res: dict, key: str, fn) -> None:
    """跑一段；失敗只記到該案例的結論（其餘案例不受拖累），不中斷整個場景。"""
    try:
        fn()
        res.setdefault(key, None)
    except AssertionError as exc:
        res[key] = str(exc)[:500]


def _scenario(ctx: CaseContext) -> dict:
    if "res" in _CACHE:
        return _CACHE["res"]
    res: dict = {"F1": None, "F1b": None, "F2": None, "F3": None, "evidence": [], "pids": []}
    _CACHE["res"] = res
    sb = ctx.sandbox()
    pkg = seal_session(ctx, sb)
    env = sc_env(sb)
    tpath = ctx.transcript(sb).path
    try:
        # ── F1 反向變體：快取冷了，但壓縮剛發生（D-1）⇒ 不轉送
        def f1b() -> None:
            backdate_transcript(tpath, 3)
            _append_compact_boundary(tpath, sb.sid)
            r = ctx.run_claude(sb, "RV_F1B_PROMPT Reply with exactly: RV_F1B_OK", env_extra=env)
            ctx.check(r.rc == 0, f"壓縮變體 rc={r.rc} {r.stderr[:200]}")
            ctx.check(not _blocked(ctx, sb, "已轉到新 session"), "剛壓縮過卻被轉送（D-1 回歸）")
            ctx.check(any("RV_F1B_OK" in t for t in ctx.transcript(sb).assistant_texts()),
                      "壓縮變體 assistant 沒有回覆（提示被吞？）")
            ctx.check(bool(_traces(sb, "forward_pass", cond=5)), "壓縮變體沒有 forward_pass cond=5（快取熱）痕跡")  # noqa: E501
            ctx.check(not _traces(sb, "session_switch_spawned"), "壓縮變體不該開視窗")
        _phase(res, "F1b", f1b)
        # ── F1：封存未 spawn、快取冷（逐字稿時間戳往前推 3h）⇒ 擋下、原文落檔、開新視窗
        orig = "RV_F1_ORIGINAL 這是掌舵者原文，要逐字轉送 ok"
        win = {"pid": None}

        def f1() -> None:
            # R216 F4：快取冷時只有上下文夠大（> 480,000）才轉送；沙盒真上下文約 2 萬，這裡只改沙盒自己  # noqa: E501
            # 逐字稿的 usage 數字成 60 萬（小上下文冷窗不轉送由 RV-CM4 驗）
            set_ctx(tpath, 600_000)
            backdate_transcript(tpath, 3)
            r = ctx.run_claude(sb, orig, env_extra=env, timeout_s=150)
            ctx.check(r.rc == 0 and not r.timed_out, f"冷窗提示 rc={r.rc} timed_out={r.timed_out}")
            rows = _traces(sb, "session_switch_spawned")
            if rows:
                win["pid"] = rows[-1].get("pid")
            blk = _blocked(ctx, sb, "已轉到新 session")
            ctx.check(bool(blk), "冷窗提示沒被擋下轉送；forward 痕跡="
                      f"{[(x.get('event'), x.get('cond')) for x in spawn_trace(sb, 'forward_pass')]}"  # noqa: E501
                      f"／{[x.get('detail') for x in spawn_trace(sb, 'forward_spawn_failed')]}")
            files = _forward_files(sb, pkg)
            ctx.check(len(files) == 1 and _body_of(files[0]) == orig, "原文沒有逐字落檔")
            ctx.check(bool(_traces(sb, "forward_spawned")), "沒有 forward_spawned 痕跡")
            ctx.check(isinstance(win["pid"], int), f"沒有視窗 pid：{rows}")
            cl = cmdline_of(win["pid"])
            ctx.check(bool(cl) and str(pkg) in cl and str(files[0]) in cl,
                      f"視窗命令列不含交接包／原文檔路徑：{cl[:240]!r}")
            res["evidence"].append(f"F1 {ctx.transcript(sb).coords(blk[0])} pid={win['pid']}")
        _phase(res, "F1", f1)
        # ── F2：已 ack（已交棒）且新視窗行程仍活著 ⇒ 擋下告知、原文落檔
        def f2() -> None:
            ctx.check(isinstance(win["pid"], int) and pid_alive(win["pid"]), "前提：F1 開出的視窗行程不在")  # noqa: E501
            rc, out, err = run_cli(sb, "handoff", "--ack", str(pkg))
            ctx.check(rc == 0 and CLOSE_HINT in out, f"ack rc={rc} {out[:100]!r}")
            text2 = "RV_F2_ORIGINAL 已交棒後又打的一句"
            r = ctx.run_claude(sb, text2, env_extra=env, timeout_s=90)
            ctx.check(r.rc == 0, f"F2 rc={r.rc}")
            blk = _blocked(ctx, sb, "本視窗已交棒")
            ctx.check(bool(blk), "已交棒舊視窗收到提示沒被擋下告知")
            ctx.check(any(_body_of(p) == text2 for p in _forward_files(sb, pkg)), "F2 原文沒落檔")
            ctx.check(bool(_traces(sb, "forward_handed_over", outcome="block")), "沒有 handed_over block 痕跡")  # noqa: E501
            res["evidence"].append(f"F2 {ctx.transcript(sb).coords(blk[-1])}")
        _phase(res, "F2", f2)
        # ── F3：同前提，提示以 `留：` 開頭 ⇒ 放行（有 assistant 回覆、沒有擋下記錄）
        def f3() -> None:
            n_blk = len(_blocked(ctx, sb, ""))
            r = ctx.run_claude(sb, "留：Reply with exactly: RV_F3_OK", env_extra=env, timeout_s=90)
            ctx.check(r.rc == 0, f"F3 rc={r.rc}")
            tr = ctx.transcript(sb)
            ctx.check(len(tr.blocked_user_prompts("")) == n_blk, "`留：` 提示仍被擋下")
            ctx.check(any("RV_F3_OK" in t for t in tr.assistant_texts()), "`留：` 提示沒有 assistant 回覆")  # noqa: E501
            ctx.check(bool(_traces(sb, "forward_pass", cond=3)), "沒有 forward_pass cond=3 痕跡")
            res["evidence"].append("F3 留：放行")
        _phase(res, "F3", f3)
    finally:
        for row in spawn_trace(sb, "session_switch_spawned"):
            if isinstance(row.get("pid"), int):
                res["pids"].append(row["pid"])
                kill_verified(row["pid"], sb.sid)
        time.sleep(2)
    left = [p for p in res["pids"] if pid_alive(p)]
    res["left"] = left
    return res


def _verdict(ctx: CaseContext, keys: tuple[str, ...]) -> None:
    res = _scenario(ctx)
    ctx.check(not res.get("left"), f"開出的視窗沒收乾淨：{res.get('left')}")
    for k in keys:
        ctx.check(res.get(k) is None, f"{k}：{res.get(k)}")
    for e in res["evidence"]:
        if e.split()[0] in {k[:2] for k in keys}:
            ctx.evidence("RV-" + e)


@case("RV-F1", "sessionctl_forward", refs=("V-F1", "DEF-200-609"))
def rv_f1(ctx: CaseContext) -> None:
    """冷窗轉送（備援路徑）：快取冷 ⇒ 擋下、原文逐字落檔、視窗以含交接包路徑的命令列開出並被收掉；
    剛壓縮過 ⇒ 不轉送（D-1）。視窗受信任對話框限制，不等新逐字稿。"""
    _verdict(ctx, ("F1b", "F1"))


@case("RV-F2", "sessionctl_forward", refs=("V-F2",))
def rv_f2(ctx: CaseContext) -> None:
    """已交棒舊視窗：新視窗行程仍活著 ⇒ 擋下告知「本視窗已交棒」、原文落檔。"""
    _verdict(ctx, ("F2",))


@case("RV-F3", "sessionctl_forward", refs=("V-F2",))
def rv_f3(ctx: CaseContext) -> None:
    """`留：` 前綴：已交棒前提下仍放行（assistant 有回覆、無擋下記錄）。"""
    _verdict(ctx, ("F3",))
