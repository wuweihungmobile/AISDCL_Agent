#!/usr/bin/env python3
"""PRD §11.1 零 token 遙測驗證（模擬法，驗收補件）：模擬時鐘 6 小時，真巡邏路徑、假端點。"""
# WHY 用模擬法、以及它證明什麼：回溯法（`zero_token_telemetry_window.py`）在本機找不到「有人在量、
# 卻沒人花 token」的 ≥6h 區間；本檔改以**模擬時鐘**把 6 小時壓成毫秒——真的程式、假的世界。
#   · 真路徑（不重寫第二份判準）：`session_resume_planner._sentinel_tick`（巡邏間隔取
#     `SENTINEL_INTERVAL_SECONDS`）、`quota_gate.refresh_quota_blocking`／`read_quota`／
#     `endpoint_probe_verdict`、`quota_meter.measure_detail`／`fetch_usage`（取數＋降級）。
#   · 替身（全在行程內，絕不真掛排程、絕不打真端點）：`urllib.request.urlopen`（假端點，階段表
#     決定 200／404／逾時，逐筆記帳）、`subprocess.*`（只記帳不執行）、`schedule_backend.select`
#     （記憶體排程器）、`datetime`（模擬時鐘）、OAuth 憑證查詢、桌面告警；暫存／痕跡／快取目錄
#     全導到一次性沙箱。
# 🔴 誠實劃界（讀數字前先讀）：
#   · **這是模擬時鐘，不是真的 6 小時牆鐘**。它證明「在這組輸入下，真程式碼的行為符合 §11.1」，
#     不證明真機 6 小時（睡眠／網路抖動／OAuth token 4 小時到期都不在模擬內）。
#   · 本 repo 沒有名為 `DRY_RUN=true` 的純遙測 Daemon。對應物＝哨兵巡邏（零 token）＋取數路徑
#     （每 TTL 至多一次 HTTP GET）；巡邏**不刷新快取**，快取由取數路徑刷新（hook 走
#     `refresh_quota_blocking`、`--pace` 走同組 `measure_detail`＋`write_cache`）。本檔以「每 60 秒
#     輪詢的消費者」驅動它，輪詢先過生產原語 `quota_ledger.claim_once`（TTL 名額；它讀名額檔
#     mtime，放行後把 mtime 設成模擬時刻）⇒「≤ 6h÷TTL」由生產名額邏輯保證。未走 `claim_refresh_slot`
#     本體（內含真牆鐘等待）。
#   · 「權威用量讀數」＝假端點自己的伺服器側帳（只有付費探針會讓它上升），不是真伺服器；其
#     `resets_at` 恆為取數時刻 +4h，避開窗翻頁（翻頁是 §11.8 的事）。
#   · 哨兵自我解除門檻 `SENTINEL_IDLE_SECONDS`＝6h，恰等於本窗長：純閒置 session 的第 24 拍
#     （6h 整）依設計 `disarm`——前 23 拍必須 `patrol`，這是設計而非失效。
# PRD §11.1 句 ↔ 斷言：方法句（連跑 6 小時、不派任何工）→ p、a；判準句一（U5h 相對權威讀數
# 增量 0）→ e；判準句二（逐字稿 token 加總無新增）→ b；端點降級句（關閉端點後自動降級且不中斷）
# → d（＋c：唯讀 GET、次數有上界、巡邏零 HTTP）。控制組＝刻意注入缺陷，驗斷言會紅。
# 用法：python tools/probe/zero_token_patrol_sim.py --selftest（斷言＋控制組）｜--run（＋逐拍表）
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import endurance_env  # noqa: E402
import quota_gate  # noqa: E402
import quota_ledger  # noqa: E402
import quota_meter  # noqa: E402
import quota_policy  # noqa: E402
import schedule_backend  # noqa: E402

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）
import session_resume_planner as planner  # noqa: E402

T0 = datetime(2026, 1, 1, tzinfo=UTC)          # 模擬起點（固定 ⇒ 可重跑）
HORIZON = 6 * 3600                             # §11.1：連續運行 6 小時
POLL = quota_gate.QUOTA_CACHE_TTL_SECONDS      # 快取 TTL＝每個 TTL 窗只放行一次取數（SSOT）
CONSUMER = 60                                  # 消費者輪詢間隔（≪TTL：多餘的輪詢該被名額擋下）
TICK = planner.SENTINEL_INTERVAL_SECONDS       # 巡邏間隔（SSOT，不寫死）
U5H, U7D = 12.5, 31.0                          # 假伺服器的固定水位（不派工 ⇒ 不動）
PROBE_PP = 0.4                                 # 控制組用：一次付費探針讓權威讀數 +0.4pp（模擬值）
#: (起點秒, 端點模式)：第 3 小時起關閉端點（先 404，再逾時），第 5 小時恢復。
PHASES = ((0, "ok"), (3 * 3600, "404"), (4 * 3600, "timeout"), (5 * 3600, "ok"))
OUT_LO, OUT_HI = 3 * 3600, 5 * 3600            # 關閉區間；判讀自 OUT_LO+TTL 起（舊快取仍在 TTL 內）
PROBE_AT = {"spawn-claude": 4, "late-probe": HORIZON // TICK - 1}  # 注入付費探針的巡邏拍序


class SimClock:
    """模擬時鐘（不是牆鐘）：只有 `advance_to` 會讓它前進。"""

    now = T0

    def advance_to(self, seconds: int) -> None:
        self.now = T0 + timedelta(seconds=seconds)


def sim_datetime(clock: SimClock) -> type:
    """`datetime` 的替身類別：`now()` 回模擬時刻，其餘行為（解析／算術）照舊。"""

    class _Sim(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001, ANN206
            return clock.now.astimezone(tz) if tz else clock.now.astimezone().replace(tzinfo=None)

    return _Sim


class _Response:
    status, headers = 200, {"anthropic-organization-id": "org-sim"}

    def __init__(self, body: dict) -> None:
        self.read = lambda: json.dumps(body).encode("utf-8")

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


class FakeEndpoint:
    """`urllib.request.urlopen` 的替身＝假 usage 端點；每次呼叫逐筆記帳。"""

    def __init__(self, clock: SimClock, phases: tuple) -> None:
        self.clock, self.phases, self.calls, self.extra_pp = clock, phases, [], 0.0

    def mode(self) -> str:
        elapsed = int((self.clock.now - T0).total_seconds())
        return [mode for start, mode in self.phases if start <= elapsed][-1]

    def authoritative_u5h(self) -> float:
        return U5H + self.extra_pp          # 伺服器側帳：只有付費探針會讓它動

    def __call__(self, req: urllib.request.Request, timeout: float | None = None) -> _Response:
        mode = self.mode()
        self.calls.append({"at": self.clock.now, "method": req.get_method(),
                           "url": req.full_url, "body": req.data is not None, "mode": mode})
        if mode == "404":
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
        if mode == "timeout":
            raise TimeoutError("simulated timeout")
        reset = (self.clock.now + timedelta(hours=4)).isoformat()
        five = {"utilization": self.authoritative_u5h(), "resets_at": reset}
        return _Response({"five_hour": five, "seven_day": {"utilization": U7D, "resets_at": reset}})


class FakeBackend:
    """記憶體排程器：`schedule_backend.select()` 的替身（絕不碰 launchd／schtasks）。"""

    name, credential_key = "sim", schedule_backend.CRED_KEY_SCHTASKS

    def __init__(self) -> None:
        self.jobs: set[str] = set()
        self.arms: list[tuple] = []

    def arm(self, plan_path, task_name, at_expr, tick, at=None):  # noqa: ANN001, ANN201
        self.jobs.add(task_name)
        self.arms.append((tick, at))
        return 0, f"cred-sim-{len(self.arms)}"

    def disarm(self, task_name: str) -> int:
        self.jobs.discard(task_name)
        return 0

    def list_jobs(self, prefix: str) -> list[str]:
        return sorted(job for job in self.jobs if job.startswith(prefix))


def transcript_facts(root: Path) -> dict:
    """逐字稿根底下所有 `.jsonl`：token 加總（message.usage 四欄）、內容雜湊、檔數、mtime。"""
    total, digest, mtimes = 0, hashlib.sha256(), []
    files = sorted(root.rglob("*.jsonl"), key=lambda p: p.as_posix())
    for path in files:
        data = path.read_bytes()
        digest.update(path.name.encode("utf-8") + data)
        mtimes.append(path.stat().st_mtime)
        for line in data.decode("utf-8").splitlines():
            usage = (json.loads(line).get("message") or {}).get("usage") or {}
            total += sum(v for v in usage.values() if isinstance(v, int))
    return {"tokens": total, "sha": digest.hexdigest(), "files": len(files), "mtimes": mtimes}


def read_jsonl(path: Path) -> list[dict]:
    """痕跡檔（每行一筆 JSON）；檔不存在＝沒有痕跡＝空清單。"""
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    return [json.loads(line) for line in lines]


def write_transcript(root: Path) -> Path:
    """一份假逐字稿（5 筆 assistant、帶 usage）；最後活動＝T0−1 分（最後一筆的 timestamp）。"""
    rows = [{"type": "assistant", "timestamp": (T0 - timedelta(minutes=5 - i)).isoformat()
             .replace("+00:00", "Z"), "message": {"model": "claude-sim-1", "usage": {
                 "input_tokens": 1000 + i, "output_tokens": 200 + i,
                 "cache_creation_input_tokens": 50, "cache_read_input_tokens": 4000}}}
            for i in range(5)]
    path = root / "sim-patrol-session.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8", newline="\n")
    os.utime(path, (T0.timestamp(), T0.timestamp()))
    return path


@contextlib.contextmanager
def sandbox(box: Path, clock: SimClock, endpoint: FakeEndpoint, backend: FakeBackend, spawns: list):
    """把真程式碼的所有外部接縫換成替身；沙箱＝`box` 底下的 tmp／traces／quota。"""
    def spawn_stub(argv, *_a, **_k):  # noqa: ANN001, ANN202 — 只記帳不執行
        spawns.append([str(x) for x in argv] if isinstance(argv, (list, tuple)) else [str(argv)])
        endpoint.extra_pp += PROBE_PP * Path(spawns[-1][0]).name.startswith("claude")
        return subprocess.CompletedProcess(spawns[-1], 127, "", "sim: spawn blocked")

    saved_tempdir, sim_dt = tempfile.tempdir, sim_datetime(clock)
    tempfile.tempdir = str(box / "tmp")
    try:
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.dict(os.environ, {
                endurance_env.TRACE_DIR_ENV: str(box / "traces"),
                quota_meter.CACHE_DIR_ENV: str(box / "quota")}))
            for mod in (planner, quota_meter, quota_gate):
                stack.enter_context(mock.patch.object(mod, "datetime", sim_dt))
            for mod, attr, repl in (
                    (quota_meter, "token_detail", lambda *a, **k: ("sim-token", "ok")),
                    (quota_gate, "policy_env", lambda root=None: {}),   # 不讀本機 .env
                    (quota_gate, "emit_to_model", lambda *a, **k: True),
                    (schedule_backend, "select", lambda *a, **k: backend),
                    (planner.escalation, "alert", lambda *a, **k: {})):
                stack.enter_context(mock.patch.object(mod, attr, repl))
            stack.enter_context(mock.patch("urllib.request.urlopen", endpoint))
            for name in ("run", "Popen", "call", "check_call", "check_output"):
                stack.enter_context(mock.patch.object(subprocess, name, spawn_stub))
            yield
    finally:
        tempfile.tempdir = saved_tempdir


def telemetry_poll(clock: SimClock, *, gated: bool = True) -> dict:
    """消費者的一拍：搶 TTL 名額（生產原語）⇒ 搶到才取數寫快取（生產函式）⇒ 重讀 ⇒ 零成本判決。"""
    now, won, fetched = clock.now.timestamp(), True, None
    if gated:
        stamp = quota_gate.refresh_stamp_path()
        won = quota_ledger.claim_once(stamp, POLL, now)
        if won:
            os.utime(stamp, (now, now))                 # 名額讀 mtime（牆鐘域）⇒ 換成模擬時刻
    if won:
        noise = io.StringIO()
        with contextlib.redirect_stdout(noise), contextlib.redirect_stderr(noise):
            fetched = quota_gate.refresh_quota_blocking()
    state = quota_gate.read_quota(clock.now)
    verdict = quota_gate.endpoint_probe_verdict(clock.now, read=quota_gate.read_quota,
                                                refresh=lambda: False)
    u5h = next((a.pct for a in state.axes if a.kind == "five_hour"), None)
    policy = quota_policy.load_policy({})[0]
    cap = quota_policy.decide(state, clock.now, policy).cap
    return {"won": won, "fetched": fetched, "usable": state.usable(), "source": state.source,
            "u5h": u5h, "verdict_open": verdict is not None, "cap": cap,
            "degraded_cap": policy.degraded_cap}


def run_scenario(mutate: str | None = None) -> dict:
    """跑一次模擬，回原始痕跡（斷言只讀它，見 `judge`）。`mutate`＝控制組要注入的缺陷。"""
    clock = SimClock()
    phases = PHASES[:2] if mutate == "never-recover" else PHASES
    endpoint, backend, spawns = FakeEndpoint(clock, phases), FakeBackend(), []
    every = 30 if mutate == "fast-poll" else CONSUMER
    with tempfile.TemporaryDirectory(prefix="patrol_sim_") as raw:
        box = Path(raw)
        for sub in ("tmp", "traces", "quota", "projects"):
            (box / sub).mkdir()
        transcript = write_transcript(box / "projects")
        sid = "sim-patrol-session"
        plan = box / "tmp" / f"autosdd_resume_plan_{sid}.md"
        with sandbox(box, clock, endpoint, backend, spawns):
            task = planner.sentinel_task_name(sid, planner.DEFAULT_TASK_NAME)
            args = planner.build_parser().parse_args(
                ["--sentinel-tick", "--plan", str(plan), "--task-name", task])
            state = planner._base_state(sid, plan, args, "sentinel", task)  # noqa: SLF001
            state.update(transcript=str(transcript), handled_through="",
                         **{backend.credential_key: "cred-sim-0"})
            plan.write_text("# 模擬任務書\n", encoding="utf-8", newline="\n")
            planner.write_relay(plan, state)
            backend.jobs.add(task)                      # 初始武裝（真 --arm-sentinel 的結果）
            before = transcript_facts(box / "projects")
            polls, ticks = [], []
            skew = {4 * TICK: CONSUMER} if mutate == "jitter-tick" else {}  # 第 4 拍晚到、件數不變
            events = sorted([(t, 0) for t in range(0, HORIZON, every)]
                            + [(t + skew.get(t, 0), 1) for t in range(TICK, HORIZON + 1, TICK)])
            for sec, kind in events:                    # 同一刻：先取數、後巡邏（快取才新鮮）
                clock.advance_to(sec)
                if kind == 0:
                    polls.append({"t": sec, **telemetry_poll(clock, gated=mutate != "fast-poll")})
                    if mutate == "post" and len(polls) == 10:
                        urllib.request.urlopen(urllib.request.Request(
                            quota_meter.USAGE_URL, data=b"{}", method="POST"))
                    continue
                if PROBE_AT.get(mutate) == len(ticks):
                    subprocess.run(["claude", "-p", "ping"], capture_output=True,
                                   encoding="utf-8", errors="replace", check=False)
                if mutate == "append-transcript" and len(ticks) == 6:
                    with transcript.open("a", encoding="utf-8", newline="\n") as handle:
                        stamp = clock.now.isoformat().replace("+00:00", "Z")
                        row = {"type": "assistant", "timestamp": stamp, "message": {
                            "model": "claude-sim-1", "usage": {"output_tokens": 9}}}
                        handle.write(json.dumps(row) + "\n")
                    os.utime(transcript, (clock.now.timestamp(), clock.now.timestamp()))
                seen = len(endpoint.calls)
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = planner._sentinel_tick(args)   # noqa: SLF001 — 真巡邏路徑
                ticks.append({"t": sec, "rc": rc, "http": len(endpoint.calls) - seen})
            after = transcript_facts(box / "projects")
            log = read_jsonl(Path(state["log_path"]))
            trace = read_jsonl(box / "tmp" / quota_gate.QUOTA_TRACE_NAME)
    decided = [row for row in log if row["event"] == "sentinel_decided"]
    for tick, row in zip(ticks, decided, strict=False):
        tick.update(action=row["action"], band=row.get("quota_band"), reason=row["reason"])
    return {"polls": polls, "ticks": ticks, "calls": endpoint.calls, "spawns": spawns,
            "before": before, "after": after, "degraded_rows": trace,
            "server_u5h": endpoint.authoritative_u5h(), "rearms": backend.arms,
            "log_events": [row["event"] for row in log]}


def judge(trace: dict) -> list[tuple[str, str, bool, str]]:
    """痕跡 ⇒ `[(id, 標題, 通過?, 實測細節)]`。"""
    polls, ticks, calls, arms = trace["polls"], trace["ticks"], trace["calls"], trace["rearms"]
    bound, measured = HORIZON // POLL, [p for p in polls if p["usable"]]
    actions = [t.get("action") for t in ticks]
    gaps = {(b[1] - a[1]).total_seconds() for a, b in zip(arms, arms[1:], strict=False)}
    claude = [s for s in trace["spawns"] if Path(s[0]).name.startswith("claude")]
    reasons = sorted({row["source"] for row in trace["degraded_rows"]})
    outage = [p for p in polls if OUT_LO + POLL < p["t"] < OUT_HI]
    tail = [p for p in polls if p["t"] >= OUT_HI]
    bands = {t.get("band") for t in ticks if OUT_LO + POLL < t["t"] < OUT_HI}
    delta, http = trace["server_u5h"] - U5H, sum(t["http"] for t in ticks)
    before, after = trace["before"], trace["after"]
    return [
        ("p", "巡邏連續 6 小時（真 _sentinel_tick）：前 23 拍 patrol、末拍（6h 整）依設計 disarm",
         len(ticks) == HORIZON // TICK and actions[:-1] == ["patrol"] * (len(ticks) - 1)
         and actions[-1] == "disarm" and all(t["rc"] == 0 for t in ticks)
         and len(arms) == len(ticks) - 1 and gaps == {float(TICK)}
         and trace["log_events"].count("sentinel_woken") == len(ticks),
         f"{len(ticks)} 拍、patrol {actions.count('patrol')}、末拍 "
         f"{actions[-1] if actions else None}、重排 {len(arms)} 次、間隔 {sorted(gaps)} 秒、"
         f"每拍皆留 sentinel_woken 痕跡 {trace['log_events'].count('sentinel_woken')} 筆"),
        ("a", "不派任何工：claude 探針子行程 0 次（且經 subprocess 的子行程總數 0）",
         not claude and not trace["spawns"],
         f"claude {len(claude)} 次、子行程共 {len(trace['spawns'])} 次"),
        ("e", "U5h 相對權威讀數增量 0：伺服器側帳不動、量到的值逐拍等於它",
         delta == 0 and bool(measured) and all(p["u5h"] == U5H for p in measured),
         f"權威 {U5H}→{trace['server_u5h']}（Δ={delta:+.1f}pp）、{len(measured)} 拍量到值皆等於它"),
        ("b", "本機逐字稿 token 加總無新增（內容雜湊、檔數、mtime 全不動）",
         before == after, f"token {before['tokens']}→{after['tokens']}、檔 {before['files']}→"
         f"{after['files']}、雜湊{'相同' if before['sha'] == after['sha'] else '不同'}"),
        ("c", f"端點只被唯讀 GET 打、≤{bound} 次（6h÷TTL {POLL}s；名額擋下多餘輪詢）、巡邏零 HTTP",
         len(calls) <= bound < len(polls) and not http and all(
             c["method"] == "GET" and not c["body"] and c["url"] == quota_meter.USAGE_URL
             for c in calls),
         f"輪詢 {len(polls)} 次 ⇒ 端點 {len(calls)} 次（{sorted({c['method'] for c in calls})}）、"
         f"巡邏期間 {http} 次"),
        ("d", "關閉端點（404→逾時）自動降級不中斷：量不到、留理由、cap=degraded_cap；恢復後回量到",
         bool(outage) and all(not p["usable"] and not p["verdict_open"]
                              and p["cap"] == p["degraded_cap"] for p in outage)
         and {"http-404", "meter-unreachable"} <= set(reasons) and bands == {"unmeasured"}
         and bool(tail) and all(p["usable"] and p["source"] == "cache" for p in tail),
         f"降級 {len(outage)} 拍（cap={outage[0]['cap'] if outage else None}）、理由 {reasons}、"
         f"巡邏觀測帶 {sorted(map(str, bands))}、恢復後 {sum(p['usable'] for p in tail)}"
         f"/{len(tail)} 拍量到"),
    ]


# 控制組：刻意注入缺陷 ⇒ 對應斷言**必須**轉紅（缺了它斷言可能只是裝飾）。逐字稿被寫＝工作發生
# ⇒ 除了 b，哨兵也不再閒置（p 的「第 24 拍 disarm」不成立）；DEF-200-560：存活判準是對話記錄
# 的 timestamp（不是 mtime），故注入的 assistant 記錄帶模擬時刻的 timestamp。late-probe：探針花
# 在末拍（最後一次取數之後，快取讀數看不見）⇒ e 只剩伺服器帳增量 `delta` 能轉紅；jitter-tick：
# 件數不變、僅某一拍晚到 60 秒 ⇒ p 只剩重排間隔 `gaps` 能轉紅——各讓一個子句單獨有鑑別力。
CONTROLS = {"spawn-claude": {"a", "e"}, "append-transcript": {"b", "p"}, "post": {"c"},
            "fast-poll": {"c"}, "never-recover": {"d"}, "late-probe": {"a", "e"},
            "jitter-tick": {"p"}}


def print_table(trace: dict) -> None:
    """逐巡邏拍一列：同一刻的取數結果、巡邏判定、本拍 HTTP 次數與端點累計次數。"""
    print("t(h:mm) | 取數：來源／可用／U5h／cap | 巡邏：判定／帶／本拍HTTP／端點累計")
    polls = {p["t"]: p for p in trace["polls"]}      # 6h 整點那拍沒有取數（迴圈到 6h 前為止）
    for tick in trace["ticks"]:
        sec, poll = tick["t"], polls.get(tick["t"], {})
        sofar = sum(1 for c in trace["calls"] if (c["at"] - T0).total_seconds() <= sec)
        print(f"{sec // 3600}:{sec % 3600 // 60:02d} | {poll.get('source', '-')}／"
              f"{poll.get('usable', '-')}／{poll.get('u5h', '-')}／{poll.get('cap', '-')} | "
              f"{tick['action']}／{tick['band']}／{tick['http']}／{sofar}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--selftest", action="store_true", help="斷言 ＋ 控制組（刻意注入缺陷）")
    parser.add_argument("--run", action="store_true", help="斷言 ＋ 逐拍表")
    args = parser.parse_args(argv)
    if not (args.selftest or args.run):
        parser.print_usage(sys.stderr)
        return 2
    trace = run_scenario()
    if args.run:
        print_table(trace)
    print("（模擬時鐘 6 小時，不是真牆鐘；真巡邏程式碼＋假端點／假排程器）")
    verdicts = judge(trace)
    for ident, title, ok, detail in verdicts:
        print(f"{'PASS' if ok else 'FAIL'} ({ident}) {title} — {detail}")
    failed = sum(not ok for _i, _t, ok, _d in verdicts)
    if args.selftest:
        for name, expect in CONTROLS.items():
            red = {i for i, _t, ok, _d in judge(run_scenario(name)) if not ok}
            good = red == expect
            failed += not good
            print(f"{'PASS' if good else 'FAIL'} (控制組 {name}) 預期轉紅 {sorted(expect)}、"
                  f"實際轉紅 {sorted(red)}")
    print(f"合計：{'全數符合' if not failed else f'{failed} 項不符'}（斷言 {len(verdicts)} 項"
          f"{'＋控制組 ' + str(len(CONTROLS)) + ' 組' if args.selftest else ''}）")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
