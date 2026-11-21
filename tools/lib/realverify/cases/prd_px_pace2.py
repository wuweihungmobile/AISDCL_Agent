"""prd_px 家族（載具 P＋E 的 `--pace` 面，第二批）：RV-PX07。

依據 TCS-WorkProgress-20261119 §10.3 附錄；證據一律 `ev(ctx, 鍵, 實測值)`。"""

from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..sandbox import REPO
from . import CaseContext
from .prd_px_lib import ev as ev
from .prd_px_lib import ok_responder, px, t5, t5_sandbox_env, usage_payload
from .prd_px_lib import reset_iso as reset_iso
from .prd_px_pace import pace
from .sessionctl_park import PY, run

BURNDOWN = str(REPO / "tools" / "lib" / "quota_burndown.py")
_VERDICT = re.compile(r"cap=(\S+) recommended=(\d+) band=(\w+) binding=(\w+)")


@px("RV-PX45", "P＋E", ("issue_status_rc0", "cap_raised", "revoke_restores", "kill_switch"), refs=("施工圖 A4",))  # noqa: E501
def px45(ctx: CaseContext) -> None:
    """施工圖 A4：真跑 `quota_burndown.py` 的 `--issue`／`--status`／`--revoke`。

    落款後 --pace 放寬、撤銷還原、OFF 不放寬。
    讀數落在週軸 converge 帶、遠期，`--pace` 的 cap 為數字；授權後 cap 必須上升（TCS:629 `cap_raised`）。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    # 讀數落在週軸 converge 帶且遠期（75%，far 減速×0.5 讓 cap 為數字；BD-1 收回減速）⇒ 有數字 cap（TCS:629 未規定讀數，故改讀數、不改判準）  # noqa: E501
    pay = {"limits": [{"kind": "weekly_all", "percent": 75, "resets_at": reset_iso(9500)}],
           "five_hour": {"utilization": 35, "resets_at": reset_iso(100)},
           "seven_day": {"utilization": 75, "resets_at": reset_iso(9500)}}

    def verdict(o) -> tuple[int, int]:
        m = _VERDICT.search(o.stdout)
        ctx.check(bool(m), f"找不到判決行：\n{o.stdout[:500]}")
        ctx.check(m.group(1).isdigit(), f"cap 應為數字（讀數須落在有數字 cap 的帶）：{m.group(0)}")
        return int(m.group(1)), int(m.group(2))

    with t5(sb, ok_responder(pay)) as stub:
        env = t5_sandbox_env(sb, stub, AUTOSDD_QUOTA_MIN_DWELL_SECONDS="0")  # 免 300 s 停留（K 載具）  # noqa: E501
        cap0, rec0 = verdict(pace(sb, env))
        a = run([PY, BURNDOWN, "--issue", "weekly_all", "--directive", "R217 E2E 清倉授權測試"],
                cwd=sb.root, env=env, timeout=60)
        ctx.check(a.returncode == 0, f"--issue rc={a.returncode}\n{a.stdout[-300:]}{a.stderr[-300:]}")  # noqa: E501
        st = run([PY, BURNDOWN, "--status"], cwd=sb.root, env=env, timeout=60)
        ctx.check(st.returncode == 0 and "清倉模式生效中" in st.stdout, f"--status rc={st.returncode}\n{st.stdout[:500]}")  # noqa: E501
        ev(ctx, "issue_status_rc0", f"issue_rc={a.returncode} status_rc={st.returncode} 生效中=True")  # noqa: E501
        cap1, rec1 = verdict(pace(sb, env))
        ctx.check(cap1 > cap0, f"落款後 cap 應上升：{cap0}→{cap1}")
        ev(ctx, "cap_raised", f"cap {cap0}→{cap1}（recommended {rec0}→{rec1}）")
        rv = run([PY, BURNDOWN, "--revoke"], cwd=sb.root, env=env, timeout=60)
        ctx.check(rv.returncode == 0, f"--revoke rc={rv.returncode}")
        cap2, rec2 = verdict(pace(sb, env))
        ctx.check((cap2, rec2) == (cap0, rec0), f"撤銷後應回原值：{(cap0, rec0)}→{(cap2, rec2)}")
        ev(ctx, "revoke_restores", f"after_revoke=({cap2},{rec2}) original=({cap0},{rec0})")
        run([PY, BURNDOWN, "--issue", "weekly_all", "--directive", "R217 E2E 清倉授權測試（kill-switch）"],  # noqa: E501
            cwd=sb.root, env=env, timeout=60)
        env_off = dict(env, AUTOSDD_QUOTA_BURNDOWN_OFF="1")
        cap3, rec3 = verdict(pace(sb, env_off))
        ctx.check((cap3, rec3) == (cap0, rec0), f"OFF 時不得放寬：{(cap3, rec3)} vs {(cap0, rec0)}")
        ev(ctx, "kill_switch", f"落款在場但 OFF=1 ⇒ ({cap3},{rec3}) 等於原值 ({cap0},{rec0})")


@px("RV-PX41", "P＋R", ("selftest_rc0", "h1_open_lt_close", "h1_trace_copied"), refs=("§11.2",))
def px41(ctx: CaseContext) -> None:
    """§11.2：真跑離線模擬器 `--selftest`，以本機真 H1 痕跡（先複製進沙盒；讀不到即 fail）重建 H1。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    sim = str(REPO / "tools" / "probe" / "pacing_simulator.py")
    code = ("import sys; sys.path.insert(0, r'%s'); import quota_gate as g; "
            "print(g.burn_ledger_path()); print(g.quota_trace_path())") % (REPO / "tools" / "lib")
    genv = {k: v for k, v in sb.env().items() if k != "AUTOSDD_TRACE_DIR"}  # 生產（本機真）痕跡路徑
    paths = run([PY, "-c", code], cwd=REPO, env=genv, timeout=60).stdout.strip().splitlines()
    ctx.check(len(paths) == 2, f"取不到生產痕跡路徑：{paths}")
    copied = []
    for src, name in ((paths[0], "burn.jsonl"), (paths[1], "degraded.jsonl")):
        ctx.check(Path(src).is_file() and Path(src).stat().st_size > 0, f"H1 痕跡讀不到（不得以不可得通過）：{src}")  # noqa: E501
        dst = sb.root / name
        shutil.copy2(src, dst)
        copied.append(f"{name}={dst.stat().st_size}B")
    ev(ctx, "h1_trace_copied", " ".join(copied))
    r = run([PY, sim, "--selftest", "--burn-ledger", str(sb.root / "burn.jsonl"),
             "--degraded-trace", str(sb.root / "degraded.jsonl")], cwd=sb.root, env=sb.env(), timeout=200)  # noqa: E501
    ctx.check(r.returncode == 0, f"--selftest rc={r.returncode}\n{r.stdout[-800:]}")
    ev(ctx, "selftest_rc0", "rc=0 " + r.stdout.strip().splitlines()[-1])
    m = re.search(r"PASS \(e\) .*cap 變動 關遲滯=(\d+) 開遲滯=(\d+)", r.stdout)
    ctx.check(bool(m) and int(m.group(2)) < int(m.group(1)), f"H1 (e) 未 PASS 或母體不可得：\n{r.stdout[-900:]}")  # noqa: E501
    ev(ctx, "h1_open_lt_close", f"open={m.group(2)}<close={m.group(1)}")


@px("RV-PX07", "P＋E", ("pace_index_value",), refs=("§4.2.8",))
def px07(ctx: CaseContext) -> None:
    """§4.2.8：預放兩筆 burn 歷史讓攤提行成立，`--pace` 印出的 pace_index 與 PRD 公式手算差 <0.01。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    pct, mins = 55.0, 100.0
    with t5(sb, ok_responder(lambda: usage_payload(five_hour=(pct, mins), seven_day=(40, 5000)))) as stub:  # noqa: E501
        env = t5_sandbox_env(sb, stub)
        first = pace(sb, env)
        ctx.check(first.returncode == 0, f"第一次 --pace rc={first.returncode}")
        bp = sb.root / "traces" / "quota_burn.jsonl"
        cur = json.loads(bp.read_text(encoding="utf-8").splitlines()[-1])
        now = datetime.now().astimezone()
        rows = []
        for hours, (short, long_) in ((4, (5, 20)), (3, (30, 30))):
            row = dict(cur)
            row["ts"] = (now - timedelta(hours=hours)).isoformat(timespec="seconds")
            row["pct"] = {"five_hour": short, "seven_day": long_}
            rows.append(row)
        bp.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in rows + [cur]), encoding="utf-8")  # noqa: E501
        t_before = datetime.now(UTC)
        out = pace(sb, env)
        t_after = datetime.now(UTC)
    ctx.check(out.returncode == 0, f"第二次 --pace rc={out.returncode}")
    m = re.search(r"pace_index=([\d.]+)", out.stdout)
    ctx.check(bool(m), f"攤提行沒有 pace_index：\n{out.stdout[:900]}")
    shown = float(m.group(1))
    reset = datetime.fromisoformat(cur["resets_at"]["five_hour"])
    # PRD §4.2.8：pace_index ＝ utilization ÷ max(ε, 窗已流逝比例)；取跑 --pace 期間兩端的平均剩餘分鐘  # noqa: E501
    left = ((reset - t_before).total_seconds() + (reset - t_after).total_seconds()) / 120.0
    elapsed = min(1.0, max(0.0, 1.0 - left / 300.0))
    want = pct / (100.0 * max(elapsed, 0.01))
    ctx.check(abs(shown - want) < 0.01, f"pace_index 印 {shown}，手算 {want:.4f}")
    ev(ctx, "pace_index_value", f"shown={shown} hand={want:.4f} diff={abs(shown - want):.4f}<0.01")
