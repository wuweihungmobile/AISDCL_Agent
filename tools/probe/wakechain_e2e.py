#!/usr/bin/env python3
"""喚醒鏈 mac 真機 E2E 驅動器（跑法④）：手寫 halt 標記 → 哨兵 → 真 claude -p -r 窗。

結構根因＝喚醒鏈接縫（launchd × 真 claude × 窗內 hook）從未在真後端跑過，離線測試全綠仍可能
斷線。證據檔 docs/06_quality/CrossPlatform_R212_E2E_Run4_Evidence.md〈二〉＝2026-10-12 真跑紀錄。
🔴 --run 只被 mock 驗過、未在真機整段跑過（那次真 launchd 驗收＝主控以手動 RUNBOOK＋judge4.py
親跑）；覆蓋面僅 NO_PROGRESS_STOP＋S14 早退（17 項）：DONE 尾段與 calendar 延後重載的重驗件未入庫，
handback「下一步指令」為空會走 DONE ⇒ 本驅動器紅但不指因。

  --selftest  離線自測（CI 可跑、零 token、不碰 launchd）：罐頭＝本輪真痕跡縮小版；嚴格與事後判決
              須 PASS，負對照 bypass（526 早退被繞過）須紅在 S2／S3／S5a／S5b。
  --judge SID --since ISO  判決既有痕跡＝S14-core 9 項＋tail 8 項（judge4 的 C5／C6 由 Z 的基線核對
              取代、M2／M2b／M3 屬模型診斷，未移植）；事後模式下暫存物（任務書／紙條）已清者降 WARN
  --run [--out DIR]  真機整段（約 40 分、約 $0.03 haiku，用 run_in_background；每步 rc 落
              <out>/steps.log；各段與清理順序見 s0～s4／z）。非 darwin、CI／GITHUB_ACTIONS
              有設 ⇒ rc=2；NO-GO 檢查之外請自行避開額度 5 小時視窗 reset ±5 分。需 Python>=3.11。
Exit：0 全綠；1 有 FAIL；2 用法／環境不允許（含 NO-GO）；3 找不到主痕跡（resume log）。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）

LBL, MARK, RUNNING = "AutoSDD_Sentinel_", "E2E4-S14", "該 job 正在跑"
RL, STOP = "autosdd_resume_log_autosdd_resume_plan_{}.jsonl", "接力已連續無新進度達停止門檻"
GIT3 = ("git status --short", "git log --oneline -1", "git diff --stat")
HB = ("## 做了什麼", "## 驗了什麼", "## 卡在哪", "## 下一步指令")
BODY = ("E2E4 小 session 被喚醒，唯讀執行三條 git。", "三條指令各以單獨一次 Bash 呼叫執行：", "無",
        "再跑一次 `git status --short` 並回報結果。")
SEQ = ("sentinel_woken", "sentinel_decided", "sentinel_rearmed", "sentinel_woken",
       "sentinel_decided", "woken", "probed", "route_chosen", "relay_snapshot_before",
       "sentinel_armed", "resumed", "relay_stopped", "sentinel_armed", "relay_rearmed")
BAD = frozenset(  # 出現任一＝走錯路（relay_done＝誤走 DONE、relay_spawned＝RELAY_NEXT）
    "sentinel_single_owner_deferred relay_settle_crashed arm_failed relay_rearm_failed"
    " handback_missing resume_authz_preflight_failed resume_spawn_failed aborted stopped"
    " sentinel_aborted patrol_handback heal_failed sentinel_heal_failed selfhealed"
    " sentinel_selfhealed sentinel_escalate sentinel_disarm resume_tick_early relay_spawned"
    " relay_done".split())
_EPOCH, _FAR = datetime.min.replace(tzinfo=UTC), datetime.max.replace(tzinfo=UTC)
_SK = timedelta(seconds=2)


def ts(s):  # ISO（含 Z／+0800；naive＝本地）→ aware datetime；解不出回 None
    try:
        d = datetime.fromisoformat(str(s or "").strip())
    except ValueError:
        return None
    return d if d.tzinfo else d.astimezone()


def _js(line):
    try:
        d = json.loads(line)
    except ValueError:
        return {}
    return d if isinstance(d, dict) else {}


def _text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def jl(path, since=_EPOCH, key="at"):  # JSONL → dict 清單，只留 key 欄時間 >= since 的列
    rows = map(_js, _text(path).splitlines())
    return [d for d in rows if d and (ts(d.get(key)) or _EPOCH) >= since]


def _world(sid, since, model="haiku"):
    home = Path.home()
    return SimpleNamespace(
        sid=sid, since=since, model=model, tmp=Path(tempfile.gettempdir()),
        traces=Path(os.environ.get("AUTOSDD_TRACE_DIR") or home / ".autosdd" / "traces"),
        plan=home / ".autosdd" / "plans" / f"autosdd_resume_plan_{sid}.md")


def judge(w, strict=False):
    """判決一份痕跡 → [(群組, 項目, 狀態, 說明)]。strict：暫存物缺席即 FAIL，否則降 WARN。"""
    sid, lbl, tr = w.sid, LBL + w.sid, w.traces
    rl = sorted(jl(w.tmp / RL.format(sid), w.since), key=lambda r: ts(r.get("at")))
    ev, last, when = [r.get("event") for r in rl], {}, {}
    for r in rl:
        last[r.get("event")], when[r.get("event")] = r, ts(r.get("at"))
    w0, w1 = when.get("relay_snapshot_before"), when.get("resumed")
    w1 = w1 if w0 and w1 and w1 >= w0 else None

    def inwin(t, slack=_SK):  # S5a／S5b 傳 0：窗後尾段的合法重載常與 resumed 同一秒
        return bool(t and w0 and w0 - _SK <= t < (w1 + slack if w1 else _FAR))
    hook = [r for r in rl if r.get("event") == "sentinel_armed" and inwin(ts(r.get("at")))
            and RUNNING in str(r.get("credential"))]
    bol = _text(tr / f"autosdd_sentinel_bootout_{lbl}.log").splitlines()
    skip = [d for d in map(_js, bol) if d.get("event") == "arm_skipped_inside_job"
            and d.get("label") == lbl and inwin(ts(d.get("at")))]
    arm = [d for d in jl(tr / f"autosdd_sentinel_events_{sid}.jsonl", key="armed_at")
           if inwin(ts(d.get("armed_at")))][-1:] or [{}]
    gone = [x for x in bol if x.startswith("parent-gone")
            and inwin(ts(x.rsplit(" at ", 1)[-1]), timedelta(0))]
    unl = [d for d in jl(tr / "autosdd_sentinel_unloads.jsonl", key="ts")
           if d.get("label") == lbl and d.get("op") in ("bootout", "deferred-bootout")
           and inwin(ts(d.get("ts")), timedelta(0))]
    chk = (("sentinel_decided", "action", "probe"), ("probed", "quota_open", True),
           ("route_chosen", "strategy", "SESSION_RESUME"), ("resumed", "rc", 0),
           ("resumed", "handback_written", True), ("relay_stopped", "why", "no_progress"),
           ("relay_rearmed", "rearmed_inplace", True),
           ("relay_rearmed", "next_state", "NO_PROGRESS_STOP"))
    first = next((r for r in rl if r.get("event") == "sentinel_decided"), {})
    st, it = last.get("relay_stopped", {}), iter(ev)
    rr = next((r for r in rl if r.get("event") == "sentinel_rearmed"
               and r.get("action") == "arm_reset"), {})
    fx = (ts(rr.get("fire_at")) or _EPOCH) + timedelta(seconds=59)  # 只往後取整
    cal = f"StartCalendarInterval = Month={fx.month}-Day={fx.day}-Hour={fx.hour}-Minute={fx.minute}"
    mine = [d for d in jl(tr / "autosdd_unattended_outcome.jsonl", w.since)
            if d.get("session") == sid]
    note = _text(st.get("note") or w.tmp / "AUTOSDD_ATTENTION.md")
    cost = [d for d in jl(tr / "autosdd_resume_cost.jsonl", w.since, "recorded_at")
            if d.get("session_id") == sid]
    c0 = (cost or [{}])[-1]
    launchd_log = _text(tr / f"autosdd_sentinel_launchd_{lbl}.log")
    core, tail = "S14-core", "tail"
    rows = (
        (core, "S1", w0 and w1, "窗開（relay_snapshot_before）且窗收（resumed）"),
        (core, "S2", hook, "窗內 hook 派生 arm-sentinel，憑證自述「該 job 正在跑」"),
        (core, "S3", skip, "bootout log 有窗內 arm_skipped_inside_job（526 早退）"),
        (core, "S4", (arm[0].get("turns") or 0) >= 24 and (arm[0].get("span_seconds") or 0) >= 600,
         "should_arm 窗內通過（events 檔 turns>=24、span>=600）"),
        (core, "S5a", not gone, "窗內無 parent-gone（沒人在窗內排延後 bootout 重載）"),
        (core, "S5b", not unl, "unload 帳窗內對本 label 無 bootout／deferred-bootout"),
        (core, "S5c", w1, "tick 活到 resumed"),
        (core, "S5d", "Traceback" not in launchd_log, "launchd log 無 Traceback"),
        (core, "S6b", MARK in _text(w.plan), f"活任務書第 3 節仍含 {MARK}", not w.plan.is_file()),
        (tail, "C1", all(n in it for n in SEQ), "事件依序：…resumed→relay_stopped→…→relay_rearmed"),
        (tail, "C2", first.get("action") == "arm_reset"
         and all(last.get(e, {}).get(k, "<缺>") == v for e, k, v in chk), "事件欄位斷言"),
        (tail, "C2b", st.get("note_written") is True and st.get("notify_rc") == -2
         and st.get("notify_queued") is False, "alert：紙條已寫、無桌面通知（notify_rc=-2）"),
        (tail, "C3", not BAD & set(ev), f"禁止事件皆未出現（{sorted(BAD & set(ev))}）"),
        (tail, "C4", cal in str(rr.get("credential")), f"arm_reset 憑證帶 {cal}（fire_at 推導）"),
        (tail, "C7", len(mine) == 1 and mine[0].get("reason") == "no_progress"
         and str(mine[0].get("handback")).endswith(f"{sid}.md"), "結局檔 +1 列（no_progress）"),
        (tail, "C8", sid in note and STOP in note, "alert 紙條存在且載本 SID 與停止原因", 1),
        (tail, "M1", c0.get("measured") is True and not c0.get("reason")
         and w.model in str(c0.get("model")), f"成本帳 measured=true、model 含 {w.model}"))
    return [(g, c, "PASS" if ok else "WARN" if any(soft) and not strict else "FAIL", t)
            for g, c, ok, t, *soft in rows]


def report(rows):  # 印判決表與摘要；回 (FAIL 項目清單, 全文)
    fails = [r[1] for r in rows if r[2] == "FAIL"]
    cnt = {g: [r[2] for r in rows if r[0] == g and r[2] != "WARN"] for g in ("S14-core", "tail")}
    lines = [f"{s:<5} [{g}] {c:<3} {t}" for g, c, s, t in rows]
    lines += ["｜".join(f"{g}: {'FAIL' if 'FAIL' in v else 'PASS'}（{v.count('PASS')}/{len(v)}）"
                       for g, v in cnt.items()) + f"｜WARN {sum(r[2] == 'WARN' for r in rows)}",
              f"WAKECHAIN-E2E rc={1 if fails else 0}" + (f" FAIL={fails}" if fails else "")]
    print("\n".join(lines))
    return fails, "\n".join(lines)


# ── --selftest：本輪（2026-10-12）真痕跡的縮小版罐頭，不讀任何外部檔；時間皆相對 T0 ──────
T0 = datetime(2026, 10, 12, 13, 37, 54, tzinfo=timezone(timedelta(hours=8)))
SID, CAL = "aaaaaaaa-1111-4222-8333-bbbbbbbbbbbb", "Month=10-Day=12-Hour=13-Minute=55"
RL_ROWS = (  # (相對 T0 秒數, 事件, 欄位)
    (0, "sentinel_woken", {}), (0, "sentinel_decided", {"action": "arm_reset"}),
    (0, "sentinel_rearmed", {"action": "arm_reset", "credential": f"StartCalendarInterval = {CAL}",
                             "fire_at": (T0 + timedelta(seconds=1020)).isoformat()}),
    (1026, "sentinel_woken", {}), (1026, "sentinel_decided", {"action": "probe"}),
    (1026, "woken", {}), (1026, "probed", {"quota_open": True}),
    (1026, "route_chosen", {"strategy": "SESSION_RESUME"}), (1026, "relay_snapshot_before", {}),
    (1029, "sentinel_armed", {"credential": "launchd｜state = running｜🔴 該 job 正在跑（pid=1）"}),
    (1043, "resumed", {"rc": 0, "handback_written": True}),
    (1043, "relay_stopped", {"why": "no_progress", "note_written": True, "notify_rc": -2,
                             "notify_queued": False}),
    (1043, "sentinel_armed", {"credential": "launchd｜StartCalendarInterval = (無)"}),
    (1043, "relay_rearmed", {"rc": 0, "next_state": "NO_PROGRESS_STOP", "rearmed_inplace": True}))


def _T(sec, kind="iso"):
    d = T0 + timedelta(seconds=sec)
    if kind == "z":
        return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    d = d.astimezone().replace(tzinfo=None) if kind == "loc" else d
    return d.isoformat(timespec="seconds")


def _put(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rows if isinstance(rows, str) else "\n".join(map(json.dumps, rows)),
                    encoding="utf-8")


def build(root, bypass=False):
    """罐頭世界。bypass＝526 早退被繞過：job 在窗內被延後 bootout、hook 派生者沒走到早退。"""
    tr, tm, lbl = root / "traces", root / "tmp", LBL + SID
    dead = {"credential": "launchd｜state = not running"}
    rows = [(o, e, {**f, **dead} if bypass and o == 1029 else f) for o, e, f in RL_ROWS]
    _put(tm / RL.format(SID), [{**f, "event": e, "at": _T(o)} for o, e, f in rows])
    gone = [f"parent-gone waited=1s at {_T(s, 'z')}" for s in (1, 1031 if bypass else 1044)]
    skip = {"event": "arm_skipped_inside_job", "label": lbl,
            "at": _T(1029)}
    _put(tr / f"autosdd_sentinel_bootout_{lbl}.log",
         "\n".join([gone[0], *([] if bypass else [json.dumps(skip)]), gone[1]]))
    secs = (1, 1043) + (1031,) * bypass
    _put(tr / "autosdd_sentinel_unloads.jsonl",
         [{"ts": _T(s), "op": "deferred-bootout", "label": lbl} for s in secs])
    _put(tr / f"autosdd_sentinel_events_{SID}.jsonl", [{
        "event": "sentinel_armed", "turns": 38, "armed_at": _T(1029, "loc"), "span_seconds": 2319}])
    _put(tr / "autosdd_resume_cost.jsonl", [{"session_id": SID, "measured": True,
                                            "model": "claude-haiku-5-5", "recorded_at": _T(1043)}])
    _put(tr / "autosdd_unattended_outcome.jsonl", [{
        "session": SID, "reason": "no_progress", "handback": f"/x/{SID}.md", "at": _T(1043)}])
    _put(tm / "AUTOSDD_ATTENTION.md", f"- 原因：{STOP}\n- session：`{SID}`\n")
    _put(root / "plan.md", f"## 3. 下一步\n{MARK}\n")
    return SimpleNamespace(sid=SID, since=T0, traces=tr, tmp=tm, plan=root / "plan.md",
                           model="haiku")


def selftest():
    ok_all = True
    with tempfile.TemporaryDirectory(prefix="wakechain_selftest_") as td:
        for name, bypass, strict, want in (("strict-pass", False, True, ()),
                                           ("post-hoc", False, False, ()),
                                           ("bypass", True, True, ("S2", "S3", "S5a", "S5b"))):
            w = build(Path(td) / name, bypass)
            if name == "post-hoc":
                w.plan.unlink()
                (w.tmp / "AUTOSDD_ATTENTION.md").unlink()
            rows = judge(w, strict)
            red = sorted(r[1] for r in rows if r[2] == "FAIL")
            warn = sum(r[2] == "WARN" for r in rows)
            ok = set(want) <= set(red) if want else not red and (warn == 2) == (name == "post-hoc")
            ok_all &= ok
            print(f"{'OK ' if ok else 'BAD'} {name:<11} FAIL={red} WARN={warn}")
    print(f"SELFTEST rc={0 if ok_all else 1}（bypass 為負對照，必須紅在 S2／S3／S5a／S5b）")
    return 0 if ok_all else 1


SEC3 = "\n".join((
    "## 3. 下一步的確切指令",
    f"🔴 {MARK} 驗收小 session：本窗只做下面四步後立刻收窗；其餘各節的 `TODO:` 是佔位、不是指令。",
    "🔴 零檔案改動：不改、不建、不刪 repo 內任何檔，唯一的寫入是第 4 步的 handback；不呼叫 Task／",
    "Agent／Workflow。每條 Bash 都單獨呼叫（不加管線、分號、&&、重導向；複合指令會被權限層擋下）。",
    *(f"{i}. 用 Bash 執行 `{c}`。" for i, c in enumerate(GIT3, 1)),
    "4. 用 Write 把兩條分隔線之間的內容寫到 prompt 注入的「handback 檔路徑」（標題一字不改；",
    "   「驗了什麼」末尾接上實際結果；🔴「下一步指令」必須非空，那一行一字不改、本窗不要執行它）。",
    "----- 內容開始 -----", *(f"{h}\n{b}" for h, b in zip(HB, BODY)), "----- 內容結束 -----",
    "寫完後最後一句話只回 `E2E4-OK`，不要再呼叫任何工具。", ""))
ENV_LINE = b"AUTOSDD_MODEL_HELMSMAN=haiku  # override-ok: E2E-WAKECHAIN temp (wakechain_e2e.py)\n"


def _gui_domain() -> str:
    # 鐵律三：Windows 沒有 os.getuid（本探針 darwin only，main 已先擋）；不呼叫
    # 後端的 launchd 專屬網域方法（豁免面；外部一旦消費，後端對稱鎖就會判紅）。
    if not hasattr(os, "getuid"):
        raise SystemExit(2)
    return f"gui/{os.getuid()}"


def _sh(argv, env=None, secs=1800):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL, cwd=_REPO, timeout=secs,
                           env={**os.environ, "PYTHONUTF8": "1", **(env or {})})
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    return p.returncode, p.stdout + p.stderr


def _wait(pred, secs, every=2.0):
    end = time.monotonic() + secs
    while not pred() and time.monotonic() < end:
        time.sleep(every)
    return pred()


def _env_add():
    p = _REPO / ".env"
    old = p.read_bytes() if p.is_file() else None
    blk = (b"\n" if old and not old.endswith(b"\n") else b"") + ENV_LINE
    p.write_bytes((old or b"") + blk)
    return old, blk


def _env_restore(tok):
    """只拿掉本檔追加的那一段並驗 sha256；回 False＝還原後與原值不符（請人工檢查）。"""
    old, blk = tok
    p = _REPO / ".env"
    new = (p.read_bytes() if p.is_file() else b"").replace(blk, b"", 1)
    if old is None and not new:
        p.unlink(missing_ok=True)
    else:
        p.write_bytes(new)
    return hashlib.sha256(new).hexdigest() == hashlib.sha256(old or b"").hexdigest()


def run_e2e(a):
    if sys.platform != "darwin" or {"CI", "GITHUB_ACTIONS"} & os.environ.keys():
        print("❌ --run 只在 darwin 本機跑（非 CI）；Windows 待驗項見",
              "docs/06_quality/CrossPlatform_R212_WakeChain_EnvLayer_Evidence.md〈八-4〉",
              file=sys.stderr)
        return 2
    sys.path[:0] = [str(_REPO / "tools" / "lib"), str(_REPO / ".claude" / "hooks")]
    m = SimpleNamespace(**{n: importlib.import_module(n) for n in (
        "quota_gate", "quota_messages", "quota_meter", "schedule_backend", "sentinel_lifecycle",
        "sentinel_lifecycle_arm", "endurance_env")})
    out, home = Path(a.out or tempfile.mkdtemp(prefix="wakechain_e2e_")), Path.home()
    be, planner = m.schedule_backend.select(), str(_REPO / "tools" / "session_resume_planner.py")
    s = SimpleNamespace(sid="", lbl="", env=None, base=set(), note0=None, armed=False,
                        marker=False, fire=_EPOCH, tr=None, w=None)
    note, hbd = Path(tempfile.gettempdir()) / "AUTOSDD_ATTENTION.md", home / ".autosdd" / "handback"
    out.mkdir(parents=True, exist_ok=True)
    print(f"輸出目錄：{out}")
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))

    def evs():
        return {r.get("event") for r in jl(s.w.tmp / RL.format(s.sid), s.w.since)}
    def s0():
        jobs, gc = be.list_jobs("AutoSDD_"), m.sentinel_lifecycle.gc(keep=("0" * 8,))
        unread = [p for p in hbd.glob("*.md") if not p.with_suffix(".ack").exists()]
        no = [t for ok, t in (
            (jobs is not None and gc is not None, "launchd 列舉量不到"),
            (not [j for j in jobs or () if "SessionResume" in j], "有 SessionResume job"),
            (not [r for r in gc or () if r["reap"] or (r["idle_hours"] or 0) >= 5],
             "GC 會收／閒置 >=5h"),
            (not unread, "有未讀 handback")) if not ok]
        s.base, s.note0 = set(jobs or ()), (note.read_bytes() if note.is_file() else None)
        return (2, "NO-GO：" + "；".join(no)) if no else (0, f"基線 {len(s.base)} 個 AutoSDD_* job")
    def s1():
        files = sorted((_REPO / "tools" / "lib").glob("*.py"))[:16]
        pump = ("E2E 小 session：同一則回覆平行發出下列 16 個 Read（limit=1），回來後只回 PUMP-OK、"
                "不用其他工具：\n" + "\n".join(f"{i}. {f}" for i, f in enumerate(files, 1)))
        s.sid, turns = str(uuid.uuid4()), 0
        for i in range(4):
            rc, res = _sh(["claude", "-p", pump, "--model", "haiku", "-r" if i else "--session-id",
                           s.sid, "--output-format", "json", "--max-budget-usd", "0.40"],
                          {"AUTOSDD_SENTINEL_OFF": "1"}, 600)
            (out / f"boost{i + 1}.json").write_text(res, encoding="utf-8")
            s.tr = next(home.glob(f".claude/projects/*/{s.sid}.jsonl"), None)
            turns = m.sentinel_lifecycle_arm.session_evidence(s.tr)[0] if s.tr else 0
            if rc == 0 and turns >= 27:
                return 0, f"turns={turns}（boost {i + 1} 次）"
        return 1, f"turns={turns} 仍不足"
    def s2():
        s.lbl, s.armed, s.w = LBL + s.sid, True, _world(s.sid, _EPOCH)
        rc, res = _sh([sys.executable, planner, "--transcript", str(s.tr), "--arm-sentinel",
                       "--out", str(s.w.plan)])
        (out / "arm.txt").write_text(res, encoding="utf-8")
        ln = _text(s.w.plan).split("\n")
        i, j = (next((k for k, x in enumerate(ln) if x.startswith(h)), None)
                for h in ("## 3.", "## 4."))
        if rc or i is None or j is None:
            return 1, f"arm rc={rc}，或骨架缺 ## 3./## 4. 標題"
        s.w.plan.write_text("\n".join(ln[:i] + SEC3.split("\n") + ln[j:]), encoding="utf-8",
                            newline="\n")
        s.env = _env_add()
        return 0, f"{s.lbl} 已武裝、第 3 節已換、.env 暫寫 haiku"
    def s3():
        now = datetime.now().astimezone().replace(microsecond=0)
        reset, s.marker, s.w.since = now + timedelta(minutes=15), True, now
        m.quota_gate.write_halt_marker(s.sid, {
            "sid": s.sid, "band": "halt", "binding": "five_hour", "at": now.isoformat(),
            "reset_at": reset.isoformat(), "transcript": str(s.tr), "resolved_source": "payload"})
        s.fire = reset + timedelta(seconds=m.quota_messages.HALT_RESET_SKEW_SECONDS)
        rc, _ = _sh(["launchctl", "kickstart", f"{_gui_domain()}/{s.lbl}"])
        ok = _wait(lambda: "sentinel_rearmed" in evs(), 150)
        return (0, "arm_reset 已落地（calendar 由判決 C4 驗）") if ok and not rc else (
            1, f"kickstart rc={rc}；arm_reset={ok}")
    def s4():
        _wait(lambda: time.time() >= s.fire.timestamp() - 90, 1200, 5)
        m.quota_meter.refresh()
        _wait(lambda: "relay_snapshot_before" in evs(), 420)
        _wait(lambda: bool(evs() & (BAD | {"relay_rearmed"})), 300, 3)
        s.env = None if _env_restore(s.env) else s.env
        fails, txt = report(judge(s.w, True))
        (out / "verdict.txt").write_text(txt, encoding="utf-8")
        return (1 if fails else 0), f"FAIL={fails}"
    def z():  # 每步獨立 try：一步炸了不擋其他步；.env 還原排第一，雙重故障也不留 haiku 行
        bad = []

        def go(name, fn, *a):
            try:
                return fn(*a)
            except Exception as exc:  # noqa: BLE001
                bad.append(name)
                print(f"Z.{name} 失敗：{type(exc).__name__}: {exc}", file=sys.stderr)
        ok = go(".env", lambda: _env_restore(s.env) if s.env else True)
        if s.armed and s.lbl not in s.base:
            go("remove", _sh, [sys.executable, planner, "--remove-schtasks", "--task-name", s.lbl])
        if s.marker:
            go("marker", lambda: m.quota_gate.halt_marker_path(s.sid).unlink(missing_ok=True))
        for p in ((s.w.plan, hbd / f"{s.sid}.md", hbd / f"{s.sid}.ack") if s.w else ()):
            go("unlink", p.unlink, True)
        if s.note0 is not None or s.sid:
            go("note", lambda: note.write_bytes(s.note0) if s.note0 is not None
               else note.unlink(missing_ok=True))
        if s.armed:  # 消費結局警語（否則下次 --pace 印假的「上次無人續跑」）並落檔
            go("banner", lambda: (out / "banner.txt").write_text(
                m.endurance_env.unattended_outcome_banner(), encoding="utf-8"))
        shutil.rmtree(note.parent / f"autosdd_ctxguard_{s.sid}.latches.d", ignore_errors=True)
        lost = go("jobs", lambda: sorted(s.base - set(be.list_jobs("AutoSDD_") or ()))) or []
        return (0 if ok and not (bad or lost) else 1), (
            f".env 還原 {'符' if ok else '不符'}；失敗步驟 {bad}；基線遺失 {lost}")
    rc, log = 1, []
    try:  # 例外照常往外傳（rc=1＋traceback），finally 一定清理
        for name, fn in (("S0", s0), ("S1", s1), ("S2", s2), ("S3", s3), ("S4", s4)):
            rc, why = fn()
            log.append(f"{datetime.now().astimezone():%H:%M:%S} {name} rc={rc} {why}")
            print(log[-1])
            if rc:
                break
    finally:
        zrc, why = z()
        log.append(f"Z rc={zrc} {why}")
        print(log[-1])
        (out / "steps.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    return rc or zrc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--selftest", action="store_true", help="離線自測（零 token、不碰 launchd）")
    g.add_argument("--judge", metavar="SID", help="判決既有痕跡（需 --since）")
    g.add_argument("--run", action="store_true", help="真機整段（darwin；約 40 分）")
    ap.add_argument("--since", help="--judge 的起算時刻（ISO，例 2026-10-12T13:37:54+08:00）")
    ap.add_argument("--out", help="--run 的輸出目錄（預設新建暫存目錄）")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.run:
        return run_e2e(a)
    w = _world(a.judge, ts(a.since) or ap.error("--judge 需要合法的 --since ISO 時刻"))
    if not (w.tmp / RL.format(a.judge)).is_file():
        print(f"❌ 找不到 resume log：{w.tmp / RL.format(a.judge)}（重開機後 $TMPDIR 會清空）",
              file=sys.stderr)
        return 3
    return 1 if report(judge(w))[0] else 0


if __name__ == "__main__":
    sys.exit(main())
