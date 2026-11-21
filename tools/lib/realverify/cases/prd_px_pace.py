"""prd_px 家族（載具 P＋E 的 `--pace` 面）：RV-PX01／04／05／14／22／24／25／28。

依據 TCS-WorkProgress-20261119 §10.3 附錄逐列的載具、輸入、斷言鍵；每案經真 `session_resume_planner.py --pace`
行程＋載具 E（本機 TLS 代理替身，見 `prd_px_lib`）。證據一律 `ev(ctx, 鍵, 實測值)`；`px()` 裝飾器在案例回 pass 前
檢查附錄斷言鍵全數有非空證據（缺鍵 ⇒ fail `assert_missing:<鍵>`）。"""  # noqa: E501

from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path

from ..sandbox import REPO, Sandbox
from . import CaseContext
from .prd_px_lib import (
    FAKE_TOKEN,
    ORG_HEADERS,
    ev,
    ok_responder,
    px,
    reset_iso,
    t5,
    t5_sandbox_env,
    usage_payload,
)
from .sessionctl_park import PY, run

PLANNER = str(REPO / "tools" / "session_resume_planner.py")
POLICY = str(REPO / "tools" / "lib" / "quota_policy.py")


def pace(sb: Sandbox, env: dict, model: str = "sonnet"):
    return run([PY, PLANNER, "--pace", "--model", model], cwd=sb.root, env=env, timeout=120)


def env_default(key: str, ctx_sb: Sandbox) -> str:
    """`--print-env-example` 現查某鍵的出廠／共享值（不寫死數字）。"""
    r = run([PY, POLICY, "--print-env-example"], cwd=REPO, env=ctx_sb.env(), timeout=60)
    m = re.search(rf"^{key}=(\S*)", r.stdout, re.M)
    if not m:
        raise AssertionError(f"--print-env-example 查不到 {key}")
    return m.group(1)


def scan_files(root: Path, needle: str, skip: tuple[str, ...] = ("claude_home", "t5stub", ".git")) -> list[str]:  # noqa: E501
    hits = []
    for p in root.rglob("*"):
        if not p.is_file() or any(s in p.parts for s in skip):
            continue
        try:
            if needle.encode() in p.read_bytes():
                hits.append(str(p.relative_to(root)))
        except OSError:
            pass
    return hits


def halt_markers(sb: Sandbox) -> list[str]:
    return [p.name for p in (sb.root / "traces").glob("halt_*.json")] if (sb.root / "traces").is_dir() else []  # noqa: E501


@px("RV-PX01", "P＋E", ("t5_get_once", "ttl_cached", "token_absent"), refs=("§4.1.1-T5",))
def px01(ctx: CaseContext) -> None:
    """§4.1.1-T5：T5 唯讀主源（只 GET）、同 TTL 內第二次不再打、假 token 不落痕跡。"""
    sb = ctx.sandbox(probe_hooks=False)
    with t5(sb, ok_responder(lambda: usage_payload(five_hour=(42, 200), seven_day=(20, 5000)))) as stub:  # noqa: E501
        env = t5_sandbox_env(sb, stub)
        a = pace(sb, env)
        ctx.check(a.returncode == 0, f"第一次 --pace rc={a.returncode}\n{a.stderr[-300:]}")
        n1, methods = stub.count(), sorted({r["method"] for r in stub.requests})
        ctx.check(n1 == 1 and methods == ["GET"], f"替身應恰收 1 筆 GET：n={n1} methods={methods}")
        ev(ctx, "t5_get_once", f"requests={n1} method={methods[0]} has_auth={stub.requests[0]['has_auth']}")  # noqa: E501
        b = pace(sb, env)
        ctx.check(b.returncode == 0, f"第二次 --pace rc={b.returncode}")
        extra = stub.count() - n1
        ctx.check(extra == 0, f"TTL 內第二次不得新請求：多了 {extra} 筆")
        ev(ctx, "ttl_cached", f"second_run_new_requests={extra}")
    hits = scan_files(sb.root, FAKE_TOKEN)
    hits += [s for s, t in (("stdout", a.stdout + b.stdout), ("stderr", a.stderr + b.stderr)) if FAKE_TOKEN in t]  # noqa: E501
    ctx.check(not hits, f"假 token 出現在痕跡／輸出：{hits}")
    ev(ctx, "token_absent", f"token_hits={len(hits)}")


@px("RV-PX04", "P", ("unmeasured", "cap_le_prepare", "no_halt"), refs=("§4.1.5",))
def px04(ctx: CaseContext) -> None:
    """§4.1.5：遙測全失效（沙盒 HOME 無憑證）⇒ 判量不到、cap ≤ prepare cap、不 halt。"""
    sb = ctx.sandbox(probe_hooks=False)
    out = pace(sb, t5_sandbox_env(sb, None, creds=False))
    ctx.check(out.returncode == 0, f"--pace rc={out.returncode}\n{out.stderr[-300:]}")
    ctx.check("band=unmeasured" in out.stdout, f"應判量不到：\n{out.stdout[:600]}")
    ev(ctx, "unmeasured", "band=unmeasured（量不到任何一軸）")
    cap = int(re.search(r"cap=(\d+)", out.stdout).group(1))
    prepare = int(env_default("AUTOSDD_QUOTA_CAP_PREPARE", sb))
    ctx.check(cap <= prepare, f"量不到的 cap={cap} 不得大於 prepare cap={prepare}")
    ev(ctx, "cap_le_prepare", f"cap={cap}<=prepare_cap={prepare}")
    ctx.check(not halt_markers(sb), f"量不到不得產生 halt 標記：{halt_markers(sb)}")
    ev(ctx, "no_halt", f"halt_markers={len(halt_markers(sb))}")


@px("RV-PX05", "P＋E", ("veto_first", "cap_from_gate"), refs=("§4.2.3a",))
def px05(ctx: CaseContext) -> None:
    """§4.2.3a：model-scoped 軸達 halt、主軸 20% ⇒ 該否決軸為 binding、cap 來自閘本身。"""
    sb = ctx.sandbox(probe_hooks=False)
    scoped = {"limits": [{"kind": "weekly_scoped", "percent": 100, "resets_at": reset_iso(100),
                          "scope": {"model": {"display_name": "Sonnet"}}}],
              "five_hour": {"utilization": 20, "resets_at": reset_iso(200)},
              "seven_day": {"utilization": 20, "resets_at": reset_iso(5000)}}
    with t5(sb, ok_responder(scoped)) as stub:
        out = pace(sb, t5_sandbox_env(sb, stub))
    ctx.check(out.returncode == 0, f"--pace rc={out.returncode}")
    m = re.search(r"cap=(\S+) recommended=(\d+) band=(\w+) binding=(\w+) reason=(\S+)", out.stdout)
    ctx.check(bool(m), f"找不到判決行：\n{out.stdout[:800]}")
    cap, rec, band, binding, _reason = m.groups()
    ctx.check(band == "halt" and binding == "weekly_scoped", f"否決軸應 halt 並為 binding：{m.group(0)}")  # noqa: E501
    # 配速段未參與＝閘值直接當 cap（halt ⇒ 0、建議扇出 0），不被配速乘數（near 2.0／far 0.5）再乘出非 0 值。  # noqa: E501
    # 解讀註記（回報主控）：逐軸 note 仍會帶 burn-ahead（那是該軸的資訊註記，不進 cap），故不以 note 字樣判。  # noqa: E501
    ctx.check(cap == "0" and rec == "0", f"halt 帶 cap／建議扇出應皆為閘值 0：cap={cap} rec={rec}")
    ev(ctx, "veto_first", f"binding={binding} band={band} recommended={rec}（配速乘數不改變閘值）")
    ev(ctx, "cap_from_gate", f"cap={cap} band={band}")


@px("RV-PX14", "P＋E", ("reason_429", "no_halt", "retry_after_shown", "cache_kept"), refs=("§8-1b",))  # noqa: E501
def px14(ctx: CaseContext) -> None:
    """§8-1b：遙測端點回 429＋Retry-After ⇒ 量不到、永不 halt、畫面帶恢復時刻、既有快取位元組不動。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    qdir = sb.root / "qcache"
    qdir.mkdir(exist_ok=True)
    old = (qdir / "autosdd_quota.json")
    from datetime import datetime, timedelta  # noqa: PLC0415
    stale = (datetime.now().astimezone() - timedelta(minutes=30)).isoformat(timespec="seconds")
    old.write_text(json.dumps({"schema": "autosdd.quota/2", "source": "endpoint", "http_status": 200,  # noqa: E501
                               "measured_at": stale, "axes": [{"kind": "five_hour", "pct": 10, "resets_at": reset_iso(200)}]}),  # noqa: E501
                   encoding="utf-8")
    before = old.read_bytes()
    with t5(sb, lambda n, r: (429, {"Retry-After": "120", **ORG_HEADERS}, None)) as stub:
        out = pace(sb, t5_sandbox_env(sb, stub))
        ctx.check(stub.count() >= 1, "429 替身沒有被打到（載具失效）")
        meter = run([PY, str(REPO / "tools" / "lib" / "quota_meter.py")], cwd=sb.root,
                    env=t5_sandbox_env(sb, stub), timeout=60)
    ctx.check(out.returncode == 0, f"--pace rc={out.returncode}")
    m429 = re.search(r"reason=(\S+?)）", meter.stderr)
    ctx.check(bool(m429) and m429.group(1) == "http-429-unmeasured", f"取數器理由應為 http-429-unmeasured：{meter.stderr[-300:]}")  # noqa: E501
    sidefile = qdir / "autosdd_quota_retry.json"
    ctx.check(sidefile.is_file(), "429 應落 Retry-After 旁檔")
    hint = json.loads(sidefile.read_text(encoding="utf-8")).get("retry_after", "")
    ctx.check("限流" in out.stdout, "--pace 畫面應說遙測通道被限流")
    ev(ctx, "reason_429", f"meter_reason={m429.group(1)} pace_says_ratelimited=True")
    band = re.search(r"band=(\w+)", out.stdout).group(1)
    ctx.check(not halt_markers(sb) and band != "halt", "429 不得 halt")
    ev(ctx, "no_halt", f"halt_markers={len(halt_markers(sb))} band={band}")
    ctx.check(hint and hint[:16] in out.stdout, f"輸出應含恢復時刻 {hint}：\n{out.stdout[:900]}")
    ev(ctx, "retry_after_shown", f"retry_after={hint}")
    ctx.check(old.read_bytes() == before, "429 後既有快取檔位元組被改動")
    ev(ctx, "cache_kept", f"bytes={len(before)} unchanged=True")


@px("RV-PX22", "P＋E", ("probe_rate", "single_account"), refs=("§13-禁令",))
def px22(ctx: CaseContext) -> None:
    """§13-禁令：10 秒內連跑 `--pace` 20 次 ⇒ 替身請求數 ≤ ceil(經過秒數÷TTL)、帳號帳本鍵恰 1 個。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    ttl = 180
    with t5(sb, ok_responder(lambda: usage_payload(five_hour=(30, 200), seven_day=(20, 5000)))) as stub:  # noqa: E501
        env = t5_sandbox_env(sb, stub)
        t0 = time.monotonic()
        for _ in range(20):
            r = pace(sb, env)
            ctx.check(r.returncode == 0, f"--pace rc={r.returncode}")
        elapsed = time.monotonic() - t0
        n = stub.count()
    allowed = math.ceil(elapsed / ttl)
    ctx.check(n <= allowed, f"20 次 --pace 在 {elapsed:.0f}s 內送了 {n} 筆，上限 {allowed}")
    ev(ctx, "probe_rate", f"runs=20 elapsed={elapsed:.0f}s requests={n}<=ceil({elapsed:.0f}/{ttl})={allowed}")  # noqa: E501
    rows = [json.loads(ln) for ln in (sb.root / "traces" / "quota_burn.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]  # noqa: E501
    keys = {f for row in rows for f in row.get("fp", []) if str(f).startswith("account=")}
    ctx.check(len(keys) == 1, f"帳本帳號鍵應恰 1 個：{keys}")
    ev(ctx, "single_account", f"account_keys={sorted(keys)}")


@px("RV-PX24", "P＋E", ("row_resets_at", "cap_mult_clamped", "retry_after_sidefile"), refs=("施工圖 A1",))  # noqa: E501
def px24(ctx: CaseContext) -> None:
    """施工圖 A1：三變體——讀數列帶 resets_at；配速乘數 >1 ⇒ 輸出「等同無節流」且乘數 ≤1.0；429＋Retry-After ⇒ 旁檔。"""  # noqa: E501
    # 變體 1：讀數帶 resets_at
    sb = ctx.sandbox(probe_hooks=False)
    at = reset_iso(200)
    with t5(sb, ok_responder({"five_hour": {"utilization": 30, "resets_at": at}, "seven_day": {"utilization": 20, "resets_at": reset_iso(5000)}})) as stub:  # noqa: E501
        pace(sb, t5_sandbox_env(sb, stub))
    rows = [json.loads(ln) for ln in (sb.root / "traces" / "quota_burn.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]  # noqa: E501
    got = rows[-1]["resets_at"].get("five_hour")
    ctx.check(got == at, f"列的 resets_at 應等於替身值：{got} vs {at}")
    ev(ctx, "row_resets_at", f"row={got} stub={at}")
    # 變體 2：配速（減速）乘數 >1（FAR=3，上界應被夾回 1.0）⇒ cap 等於 base cap＝max_fanout ⇒「等同無節流」  # noqa: E501
    sb2 = ctx.sandbox(probe_hooks=False)
    with t5(sb2, ok_responder({"five_hour": {"utilization": 52, "resets_at": reset_iso(150)}, "seven_day": {"utilization": 20, "resets_at": reset_iso(5000)}})) as stub:  # noqa: E501
        out = pace(sb2, t5_sandbox_env(sb2, stub, AUTOSDD_QUOTA_PACE_FAR="3", AUTOSDD_QUOTA_MAX_FANOUT="4"))  # noqa: E501
    warn = re.search(r"AUTOSDD_QUOTA_PACE_FAR='3' 高於上界 ([\d.]+) ⇒ 採用預設 ([\d.]+)", out.stdout + out.stderr)  # noqa: E501
    ctx.check(bool(warn) and float(warn.group(1)) <= 1.0, f"乘數 >1 應出聲夾回上界 ≤1.0：\n{(out.stdout + out.stderr)[-700:]}")  # noqa: E501
    ctx.check("等同無節流" in out.stdout, f"cap 達 max_fanout 時應印「等同無節流」：\n{out.stdout[:900]}")  # noqa: E501
    cap_line = re.search(r"cap=(\d+)", out.stdout)
    ev(ctx, "cap_mult_clamped", f"phrase=等同無節流 {cap_line.group(0)} max_fanout=4 FAR=3⇒上界{warn.group(1)}採用{warn.group(2)}")  # noqa: E501
    # 變體 3：429＋Retry-After
    sb3 = ctx.sandbox(probe_hooks=False)
    with t5(sb3, lambda n, r: (429, {"Retry-After": "90", **ORG_HEADERS}, None)) as stub:
        pace(sb3, t5_sandbox_env(sb3, stub))
    side = sb3.root / "qcache" / "autosdd_quota_retry.json"
    ctx.check(side.is_file(), "429 旁檔不存在")
    ev(ctx, "retry_after_sidefile", json.loads(side.read_text(encoding="utf-8"))["retry_after"])


@px("RV-PX25", "P＋E", ("rec_of_gate",), refs=("施工圖 A2",))
def px25(ctx: CaseContext) -> None:
    """施工圖 A2：`--pace`「現在可派」＝案例以同讀數呼叫 `quota_policy.decide()` 回傳的 rec。"""
    sb = ctx.sandbox(probe_hooks=False)
    with t5(sb, ok_responder(lambda: usage_payload(five_hour=(75, 120), seven_day=(40, 5000)))) as stub:  # noqa: E501
        out = pace(sb, t5_sandbox_env(sb, stub))
    shown = int(re.search(r"現在可派 (\d+) 個", out.stdout).group(1))
    script = (
        "import sys, json\nfrom datetime import datetime\nsys.path.insert(0, r'{}')\n"
        "from pathlib import Path\nimport quota_gate, quota_policy\n"
        "now = datetime.now().astimezone()\n"
        "st = quota_gate.read_quota(now, Path(r'{}'))\n"
        "p = quota_policy.load_policy(quota_gate.policy_env())[0]\n"
        "d = quota_policy.decide(st, now, p, pace_floor=False)\n"
        "print(d.recommended_fanout)\n"
    ).format(REPO / "tools" / "lib", sb.root / "qcache" / "autosdd_quota.json")
    sf = sb.write_file("decide_probe.py", script)
    r = run([PY, str(sf)], cwd=sb.root, env=t5_sandbox_env(sb, None), timeout=60)
    ctx.check(r.returncode == 0, f"decide 探針失敗：{r.stderr[-400:]}")
    want = int(r.stdout.strip().splitlines()[-1])
    ctx.check(shown == want, f"--pace 可派 {shown} ≠ decide().recommended_fanout {want}")
    ev(ctx, "rec_of_gate", f"pace_shown={shown} decide_rec={want}")


@px("RV-PX28", "P＋E", ("gate_excluded_printed",), refs=("施工圖 A8",))
def px28(ctx: CaseContext) -> None:
    """施工圖 A8：替身回別家模型的 model-scoped 軸 ⇒ 輸出含 `gate_excluded=` 並列出該軸。"""
    sb = ctx.sandbox(probe_hooks=False)
    pay = {"limits": [{"kind": "weekly_scoped", "percent": 60, "resets_at": reset_iso(3000),
                       "scope": {"model": {"display_name": "Opus"}}}],
           "five_hour": {"utilization": 20, "resets_at": reset_iso(200)},
           "seven_day": {"utilization": 20, "resets_at": reset_iso(5000)}}
    with t5(sb, ok_responder(pay)) as stub:
        out = pace(sb, t5_sandbox_env(sb, stub), model="sonnet")
    m = re.search(r"gate_excluded=(\S+)", out.stdout)
    ctx.check(bool(m) and "weekly_scoped" in m.group(1), f"應列出被排除的軸：\n{out.stdout[:900]}")
    ev(ctx, "gate_excluded_printed", f"gate_excluded={m.group(1)}")
