"""prd_px 家族（真排程 S＋真行程 P＋T5 替身 E）：RV-PX08／23。

工具副本沙盒（見 `sessionctl_park` 模組 docstring）：被測的是沙盒內逐位元相同的
`session_resume_planner.py`。
先 `--pace`（T5 替身餵讀數、寫沙盒額度快取），再 `--register-schtasks` 真註冊排程並以排程器回讀
NextRunTime 作憑證；案例結束依名字精確撤銷（排程只註冊、不會在案例生命週期內觸發）。"""

from __future__ import annotations

import time
from datetime import datetime, timedelta

from . import CaseContext
from .prd_px_lib import ev, ok_responder, px, t5, t5_sandbox_env
from .sentinel import planner
from .sessionctl_park import get_task, install_tools, remove_tasks_like, seed_session

SKEW = 120  # session_resume_planner.RESET_SKEW_SECONDS


def _axes(**spec: tuple[float, datetime]) -> dict:
    return {k: {"utilization": pct, "resets_at": at.isoformat(timespec="seconds")}
            for k, (pct, at) in spec.items()}


def _arm(ctx: CaseContext, payload: dict, tag: str) -> tuple[dict, float, str]:
    """沙盒＋替身讀數 ⇒ `--pace`（暖快取）→ `--register-schtasks`；回 (排程器回讀, planner 牆鐘秒, 任務名)。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    install_tools(sb)
    name = f"AutoSDD_RV_{tag}_{sb.sid[:8]}"
    ctx.sched_names.append(name)  # runner 收尾時 sched.remove(name)；下方 finally 也精確移除
    try:
        tp = seed_session(ctx, sb)
        with t5(sb, ok_responder(payload)) as stub:
            e = t5_sandbox_env(sb, stub)
            keys = ("HTTPS_PROXY", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CLAUDE_CONFIG_DIR", "TEMP", "TMP")  # noqa: E501
            extra = {k: e[k] for k in keys} | {"AUTOSDD_QUOTA_CACHE_DIR": str(sb.root / "qcache")}
            p = planner(sb, "--pace", **extra)
            ctx.check(p.returncode == 0, f"--pace rc={p.returncode} {p.stderr[-300:]}")
            t0 = time.monotonic()
            r = planner(sb, "--register-schtasks", "--session-id", sb.sid, "--transcript", str(tp),
                        "--task-name", name, **extra)
            wall = time.monotonic() - t0
        ctx.check(r.returncode == 0, f"--register-schtasks rc={r.returncode}\n{r.stdout[-500:]}{r.stderr[-400:]}")  # noqa: E501
        t = get_task(name)
        ctx.check(t is not None and bool(t["next_run_time"]), f"排程器查不到 {name} 或無 NextRunTime：{t}")  # noqa: E501
        return t, wall, name
    finally:
        remove_tasks_like(name)
        remove_tasks_like(f"AutoSDD_Sentinel_{sb.sid}")


@px("RV-PX08", "S＋P＋E", ("endurance_armed", "no_inprocess_sleep"), refs=("§4.5.5",), sched=True)
def px08(ctx: CaseContext) -> None:
    """§4.5.5：替身回短窗 ≥ halt、`resets_at`＝now＋6 小時 ⇒ 沙盒前綴排程存在且
    NextRunTime 與 reset＋skew 相差 ≤60 s；planner 行程 30 s 內結束（不在行程內睡等）。"""
    reset = datetime.now().astimezone() + timedelta(hours=6)
    t, wall, name = _arm(ctx, _axes(five_hour=(97, reset), seven_day=(40, reset + timedelta(days=3))), "px08")  # noqa: E501
    nrt = datetime.fromisoformat(t["next_run_time"])
    diff = (nrt - (reset + timedelta(seconds=SKEW))).total_seconds()
    ctx.check(abs(diff) <= 60, f"NextRunTime 與 reset＋skew 相差 {diff:.0f}s（>60）")
    ev(ctx, "endurance_armed", f"{name} NextRunTime={t['next_run_time']} reset+{SKEW}s 差={diff:+.0f}s（≤60）")  # noqa: E501
    ctx.check(wall < 30, f"planner 用了 {wall:.1f}s（應 <30 s，不得行程內睡等）")
    ev(ctx, "no_inprocess_sleep", f"--register-schtasks 牆鐘={wall:.1f}s <30")


@px("RV-PX23", "S＋P＋E", ("armed_earliest_reset", "cred_nonempty"), refs=("§11.4",), sched=True)
def px23(ctx: CaseContext) -> None:
    """§11.4：週軸 ≥ halt（reset＝now＋3 天）、短窗 ≥ halt（reset＝now＋2 小時）
    ⇒ 排程依「最早可 reset 軸」武裝＝短窗 reset＋skew（不是 3 天後）。
    PRD R-4.5.6-5：取其他 ≥halt 且有 reset 的軸之最早者。"""
    now = datetime.now().astimezone()
    short, week = now + timedelta(hours=2), now + timedelta(days=3)
    t, _wall, name = _arm(ctx, _axes(five_hour=(97, short), seven_day=(97, week)), "px23")
    nrt = datetime.fromisoformat(t["next_run_time"])
    diff = (nrt - (short + timedelta(seconds=SKEW))).total_seconds()
    ctx.check(abs(diff) <= 60, f"應依最早 reset 軸（短窗）武裝：NextRunTime={nrt} 與短窗 reset＋skew 差 {diff:.0f}s")  # noqa: E501
    ev(ctx, "armed_earliest_reset", f"NextRunTime={t['next_run_time']} 短窗 reset+{SKEW}s 差={diff:+.0f}s；"  # noqa: E501
                                    "週軸 reset 在 +3 天（未採用）")
    ev(ctx, "cred_nonempty", f"{name} NextRunTime={t['next_run_time']}（排程器自報，非空）")
