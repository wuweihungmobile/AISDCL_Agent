"""`drive`：替 auto／observe 項目掛上驅動器（DES §5；REQ-WP-10／17／19）。

憑證判準（根 CLAUDE.md〈反「事後諸葛」取證規則〉）：註冊後**回讀排程器自己報的憑證**，
拿不到（空字串）⇒ 撤掉剛建的工作、**不寫** `drive` 事件、rc≠0（`DriveFailed`）。
整件事在 OIR 寫入鎖內做：選時槽
（錯開，§5.4-3）→註冊→回讀→追加事件，所以兩個行程不會同時搶到同一個時槽。
也放 `stale-pass`（REQ-WP-17，DEF 防永動規則）與案例中繼資料 `case_info`（牆鐘上限、soak 通道）。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from lib import git_paths, win_spawn

from . import evidence, schedcache, throttle
from . import ledger as oi_ledger
from . import params as oi_params
from .fold import fold

_TOOLS = Path(__file__).resolve().parents[2]
# `sched_isolation`／`endurance_env` 以頂層名 import 同層模組（planner 同款）：先把 tools/lib 放進
# sys.path；`apply_job_env`（入口）也要靠它 import `sandbox_scope`。
if str(_TOOLS / "lib") not in sys.path:
    sys.path.insert(0, str(_TOOLS / "lib"))
import sched_isolation  # noqa: E402  # RealVerify 副作用隔離（DES S3）：登記首判／job 環境搬運／OS 自毀

#: 案例沒宣告牆鐘時的預設（分鐘）：一般案例、long 案例（TCS AT-WP-29 的 180 分即 long 預設）。
#: 這是**預設值**不是案例的真實上限；案例模組宣告 `MIN_WALL_SECONDS`／
#: `DESIGNED_WAIT_SECONDS`／`WALL_SECONDS` 時一律以宣告為準（REQ-WP-99：E1 強制 long／soak）。
DEFAULT_WALL_MINUTES = {"normal": 60, "long": 180}
SOAK_DEFAULT_WALL_MINUTES = 25 * 60
DRIVE_LEAD_MINUTES = 2  # 排程器要未來的分鐘；期望時刻預設＝現在＋2 分


class DriveFailed(Exception):
    """排程沒有成立（載具缺、註冊失敗、憑證空）；帳本未變動。"""


class DriveRefused(DriveFailed):
    """副作用隔離的登記首判拒絕（沙盒租約／主人／存在性不成立，或 job 環境值不合法）。

    `rc` 是 `sched_isolation.register_gate` 的 rc（4 判準拒絕、2 job 環境值不合法）；理由已落
    痕跡與 stderr。"""

    def __init__(self, rc: int) -> None:
        super().__init__(f"副作用隔離拒絕登記（rc={rc}）")
        self.rc = rc


@dataclass(frozen=True)
class CaseInfo:
    family: str = ""
    long: bool = False
    kind: str = "normal"  # normal｜soak（模組常數 KIND）
    wall_minutes: int = DEFAULT_WALL_MINUTES["normal"]
    sources: tuple[str, ...] = ()


def case_info(case_id: str | None, registry: dict | None = None) -> CaseInfo:
    """RealVerify 案例的中繼資料；案例不存在或沒宣告者以預設補（不猜成別的案例）。"""
    if not case_id:
        return CaseInfo()
    if registry is None:
        from lib.realverify.cases import discover  # noqa: PLC0415 — 匯入全部案例模組，只在需要時付
        registry = discover()
    case = registry.get(case_id)
    if case is None:
        return CaseInfo()
    mod = sys.modules.get(getattr(case.fn, "__module__", ""))
    kind = getattr(mod, "KIND", "normal") if mod else "normal"
    names = ("WALL_SECONDS", "MIN_WALL_SECONDS", "DESIGNED_WAIT_SECONDS")
    declared = [getattr(mod, k) for k in names
                if mod and isinstance(getattr(mod, k, None), int)]
    default = (SOAK_DEFAULT_WALL_MINUTES if kind == "soak"
              else DEFAULT_WALL_MINUTES["long" if case.long else "normal"])
    wall = -(-max(declared) // 60) if declared else default
    return CaseInfo(case.family, bool(case.long), kind, wall,
                    tuple(getattr(mod, "SOURCES", ()) if mod else ()))


def case_of(item: dict) -> str | None:
    check = item.get("check")
    return check.get("realverify") if isinstance(check, dict) else None


def budget_minutes(item: dict, info: CaseInfo, params: dict) -> int:
    """`start.budget_minutes`：observe＝`observe_timeout_minutes`；auto＝案例牆鐘上限＋margin。"""
    if item["kind"] == "observe":
        return params["observe_timeout_minutes"]
    return info.wall_minutes + params["run_budget_margin_minutes"]


def _round_up_minute(moment: datetime) -> datetime:
    floor = moment.replace(second=0, microsecond=0)
    return floor if floor == moment else floor + timedelta(minutes=1)


def action_argv(root: Path, item_id: str, task: str) -> list[str]:
    """排程要跑的指令；居所與行為開關經 `--job-env` 帶進引數（排程行程不繼承我們的環境；DES S3
    取代舊的 `--trace-dir`，入口仍相容舊旗標一版）。正式且無顯式 env ⇒ 沒有任何 `--job-env`。"""
    argv = [win_spawn.quiet_python(), str(_TOOLS / "openitems.py"), "--root", str(root)]
    return [*argv, *sched_isolation.job_env_pairs(root, os.environ), "run-driver", item_id,
            "--task", task]


def task_name(params: dict, item_id: str, at: datetime) -> str:
    return f"{params['task_prefix']}{item_id}_{at.astimezone().strftime('%Y%m%d%H%M')}"


def drive_item(root: Path, params: dict, item_id: str, *, backend, now: datetime, by: str,
               at: datetime | None = None) -> dict:
    """掛上（或重掛）驅動器，回寫入的 `drive` 事件；失敗拋 `Reject`（不該掛）或 `DriveFailed`。"""
    if backend is None:
        raise DriveFailed("此平台沒有排程載具（只支援 Windows schtasks／macOS launchd）")
    registered: list[str] = []

    def make(events: list[dict]) -> list[dict]:
        folded = fold(events, params, now)
        item = folded.items.get(item_id)
        if item is None:
            raise oi_ledger.Reject([f"找不到 {item_id}"])
        if item["state"] in ("closed", "retired", "escalated", "listed") or item["kind"] not in (
                "auto", "observe"):
            raise oi_ledger.Reject([f"{item_id} 是 {item['state']}／{item['kind']}，不掛驅動器"])
        want = at
        if want is None:
            due = oi_ledger.parse_ts(item["due"]) if item["kind"] == "observe" else None
            soonest = now + timedelta(minutes=DRIVE_LEAD_MINUTES)
            want = max(due, soonest) if due is not None else soonest
        others = throttle.taken_slots(folded.items, item_id)
        slot = throttle.pick_slot(_round_up_minute(want), others, params["stagger_minutes"])
        task = task_name(params, item_id, slot)
        # DES S3 REQ-SE-12／18：登記前先判目標；拒絕＝不登記、帳本不變（沙盒才帶 OS 自毀）
        if (denied := sched_isolation.register_gate(root, os.environ, slot,
                                                    sched_isolation.jsonl_trace(),
                                                    "openitems.drive")):
            raise DriveRefused(denied)
        expire = sched_isolation.expire_for(root, now)
        credential = backend.register(task, slot, action_argv(root, item_id, task), str(root),
                                      **({"expire_at": expire} if expire is not None else {}))
        registered.append(task)
        if not credential:
            raise DriveFailed(f"排程已送出但回讀不到憑證（NextRunTime 空）：{task}")
        return [{"ev": "drive", "id": item_id, "by": by, "ts": now.isoformat(timespec="seconds"),
                 "task": task, "credential": credential,
                 "at": slot.isoformat(timespec="seconds")}]

    try:
        events, _bad = oi_ledger.read_events(oi_params.ledger_path(root))
        prior = (fold(events, params, now).items.get(item_id) or {}).get("drive")
        written = oi_ledger.append(root, make)
    except (DriveFailed, oi_ledger.Reject):
        for task in registered:  # 憑證回讀失敗或帳本拒收：撤掉剛建的工作，不留孤兒排程
            backend.unregister(task)
        raise
    dropped = None
    if prior and prior.get("task") not in (None, written[0]["task"]):
        # 重掛：舊工作作廢（best effort，殘留也只是 stale 排程）
        dropped = prior["task"] if backend.unregister(prior["task"]) else None
    # 寫入排程的這一方同步快取：否則 TTL 內的舊快取（登記前拍的）會讓新排程被完成閘判成不存在
    schedcache.note(params, backend, now, add={written[0]["task"]: written[0]["at"]}, drop=dropped)
    return written[0]


def _git_time(root: Path, sources: list[str]) -> datetime | None:
    proc = git_paths.run(root, "log", "-1", "--format=%cI", "--", *sources)
    return oi_ledger.parse_ts(proc.stdout.strip()) if proc.returncode == 0 else None


def _family_last_pass(root: Path, family: str, case_ids: set[str]) -> datetime | None:
    try:
        text = (Path(root) / evidence.RV_LEDGER_REL).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    best = None
    for raw in text.splitlines():
        cells = [c.strip() for c in raw.strip().strip("|").split("|")]
        if len(cells) < 7 or cells[2] != "pass" or (stamp := oi_ledger.parse_ts(cells[0])) is None:
            continue
        sel = re.sub(r"\s*\+long$", "", cells[1])
        ran = {x for x in re.split(r"[,，、\s]+", cells[7]) if x} if len(cells) >= 8 else set()
        if sel == f"family={family}" or sel in case_ids or ran & case_ids:
            best = stamp if best is None or stamp > best else best
    return best


def stale_pass(root: Path, params: dict, now: datetime, *, registry: dict | None = None,
               git_time=_git_time) -> list[str]:
    """家族原始檔（案例模組 `SOURCES`）最後 commit 晚於該家族最後一筆 pass 帳列 ⇒ 開 auto 列
    （DES §8-4；防永動：同家族已有 open／driven 列不重開；有 escalated／listed／retired 時
    `T_src` 必須晚於最晚的 escalate／retire／human 化 convert 才開）。
    回新開的 id；一次 append、整批原子。"""
    if registry is None:
        from lib.realverify.cases import discover  # noqa: PLC0415
        registry = discover()
    families: dict[str, dict] = {}
    for cid, case in registry.items():
        info = case_info(cid, registry)
        fam = families.setdefault(case.family, {"ids": set(), "sources": set()})
        fam["ids"].add(cid)
        fam["sources"].update(info.sources)
    opened: list[str] = []

    def make(events: list[dict]) -> list[dict]:
        folded = fold(events, params, now)
        out: list[dict] = []
        for family, fam in sorted(families.items()):
            if not fam["sources"]:
                continue
            t_src = git_time(root, sorted(fam["sources"]))
            last = _family_last_pass(root, family, fam["ids"])
            if t_src is None or (last is not None and t_src <= last):
                continue
            scope = f"realverify-family:{family}"
            rows = [i for i in folded.items.values() if i["scope"] == scope]
            if any(i["state"] in ("open", "driven") for i in rows):
                continue
            ids = {i["id"] for i in rows}
            gate = [oi_ledger.parse_ts(e["ts"]) for e in events if e["id"] in ids and (
                e["ev"] in ("escalate", "retire") or (e["ev"] == "convert" and e.get("kind") in (
                    "human", "k1")))]
            if gate and t_src <= max(gate):
                continue
            out.append({"ev": "open", "id": oi_ledger.next_id(events + out),
                        "by": "driver:stale-pass",
                        "title": f"stale-pass：{family} 家族原始檔晚於最後一筆 pass",
                        "source": "docs/06_quality/RealVerify_Protocol/cases.json", "scope": scope,
                        "kind": "auto", "check": {"argv": ["python", "tools/realverify.py", "run",
                                                           "--family", family], "pass": "rc0"}})
        opened.extend(e["id"] for e in out)
        return out

    oi_ledger.append(root, make)
    return opened


def console_run(argv: list[str], timeout_s: float, env: dict, cwd: Path) -> tuple[int, str]:
    """驅動器執行 check 的預設 runner：`python` 一律換成當前直譯器（排程行程的 PATH 沒有 venv）。"""
    argv = [throttle.console_python() if argv[0] in ("python", "python3") else argv[0], *argv[1:]]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout_s, env=env, cwd=str(cwd),
                              check=False,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, exc.__class__.__name__
    return proc.returncode, proc.stdout or ""
