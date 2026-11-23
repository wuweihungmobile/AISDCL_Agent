"""L1 產品面拒絕判準：目標是不是「驗證沙盒」、租約與主人還在不在（DES §3）。"""
# 立案：2026-11-20 幽靈 session 57d0ccad（DEF-200-632）。產品面此前只問「有沒有人在動」，從不問
# 「這個目標是不是一個驗證沙盒、它的主人還在不在」；排程 job 以登入者真環境執行，行程環境變數一個都
# 帶不過去 ⇒ 判準只能吃**目標自帶的資料**（沙盒身分檔＋租約，D-1／D-2），不讀任何環境變數（D-4）、
# 不開任何行程（D-4：git 根以「往上找 `.git`」解析）。讀不懂一律拒絕（fail-closed）。
# 本檔是單檔共用工具（D-3）：呼叫者橫跨 sessionctl 套件、openitems 套件與扁平的 planner／
# quota_escalation，套件間不得互 import，故只在此放純函式與常數；站點接線屬 S2／S3。
# 🔴 守衛面（根 CLAUDE.md〈守衛面准入〉）：改本檔須有暴露證據（DES §1 已列）。
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple

SCHEMA = 1
IDENTITY_NAME = ".autosdd_sandbox.json"
SBX_PREFIX = "AutoSDD_RV_sbx_"          # 路徑段（家目錄名）
SLUG_FRAGMENT = "AutoSDD-RV-sbx-"       # ~/.claude/projects 的 slug 段
LEASE_MAX = 30                           # 分；`grant` 預設上限（程式常數，不開 env，D-2）
LEASE_CAP = 300                          # 分；案例宣告 `lease_minutes` 的絕對上限
#: spawn 站點被 L1 拒絕的專屬 rc（D-24）；與 CLI 既有拒絕碼＝4、spawn 失敗 1、
#: `endurance_env.RC_RESIDENCE_MISSING`＝9 皆不相等（AT-SE-48 以 AST 鎖互異）。
RC_SIDEEFFECT_REFUSED = 10
#: 交接包檔頭「repo 根」行的標籤（格式 SSOT＝`sessionctl/handoff_build.py` 產出的
#: `- repo 根：<路徑>`；
#: 該檔由 S2 改為 import 本常數，兩處不得各寫一份）。
PKG_REPO_LABEL = "repo 根："
_OWNER_START_TOLERANCE_SEC = 2.0
_FILETIME_EPOCH_100NS = 116444736000000000


class Verdict(NamedTuple):
    allow: bool
    reason: str
    roots: tuple[str, ...] = ()


class Site(NamedTuple):
    """`SITES` 的列：呼叫判準的站點。類別 ∈ spawn／register／fire／tick／notify／headless。"""
    module: str
    function: str
    kind: str


#: 站點登記表（AST 鎖用，AT-SE-17）。S2／S3／QW Q3 在寫出站點的同一 commit 加列。
#: planner 站點（DES S2）：接點在 `sched_isolation`（register_gate／tick_gate），呼叫在下列函式內。
SITES: tuple[Site, ...] = (
    Site("session_resume_planner", "_register_and_record", "register"),
    Site("session_resume_planner", "_sentinel_tick", "tick"),
    Site("session_resume_planner", "_resume_tick", "tick"),
    Site("session_resume_planner", "main", "headless"),  # `--probe-quota` 動詞
    # 非 sessionctl 站點（DES S3；模組名＝`tools/` 起算的匯入路徑；哨兵武裝走 planner
    # `_register_and_record`，已在上列）
    Site("lib.engine_resume_job", "arm", "register"),
    Site("lib.engine_resume_job", "run_job", "tick"),
    Site("lib.openitems.drive", "drive_item", "register"),
    Site("lib.openitems.verbs", "_do_run_driver", "fire"),
    Site("lib.selfimproving.schedarm", "arm", "register"),
    Site("lib.selfimproving.patrolrun", "launch", "headless"),
    Site("selfimproving", "_patrol", "fire"),
    Site("lib.quota_escalation", "patrol_housekeeping", "notify"),
    Site("lib.quota_escalation", "alert", "notify"),
    # sessionctl 站點（DES S2；模組名＝`tools/` 起算的匯入路徑）
    Site("lib.sessionctl.park_cli", "_cmd_fire", "fire"),
    Site("lib.sessionctl.park_cli", "spawn_resume", "spawn"),
    Site("lib.sessionctl.handoff", "spawn", "spawn"),
    Site("lib.sessionctl.park_cli", "_cmd_park", "register"),
    Site("lib.sessionctl.oldwin_sched", "schedule_retry", "register"),
    Site("lib.sessionctl.oldwin_park", "_rearm", "register"),
    # QuotaWall Q3（DES §7.5／§7.6；SE §10.2 第 2、7、8 項）：失敗終局的通知與哨兵接手
    Site("lib.sessionctl.park_announce", "announce", "notify"),
    Site("lib.sessionctl.park_takeover", "on_patrol", "tick"),
)


def _norm(path) -> str:
    return os.path.normcase(str(Path(path).resolve()))


def _segments(path) -> list[str]:
    return [os.path.normcase(part) for part in Path(path).parts]


def _has_identity(folder: Path) -> bool:
    try:
        return (folder / IDENTITY_NAME).is_file()
    except OSError:
        return False


def sandbox_home(path) -> Path | None:
    """本層或上一層有身分檔者；否則依路徑段 `AutoSDD_RV_sbx_*` 取該段為家；都無 ⇒ None。"""
    here = Path(path)
    for folder in (here, here.parent):
        if _has_identity(folder):
            return Path(_norm(folder))
    prefix = os.path.normcase(SBX_PREFIX)
    parts = here.parts
    for index, part in enumerate(parts):
        if os.path.normcase(part).startswith(prefix):
            return Path(_norm(Path(*parts[: index + 1])))
    return None


def is_sandbox(path) -> bool:
    if sandbox_home(path) is not None:
        return True
    return any(os.path.normcase(SLUG_FRAGMENT) in seg for seg in _segments(path))


def git_root(path) -> Path:
    """往上找 `.git`（目錄或檔案皆可）；找不到回原路徑。回傳前 resolve＋normcase。"""
    start = Path(path).resolve()
    for folder in (start, *start.parents):
        if (folder / ".git").exists():
            return Path(os.path.normcase(str(folder)))
    return Path(os.path.normcase(str(start)))


def pkg_root(pkg) -> Path | None:
    """讀交接包檔頭 `repo 根：` 一行；讀不到 ⇒ None。"""
    try:
        with open(pkg, encoding="utf-8", errors="replace") as handle:
            for _ in range(80):
                line = handle.readline()
                if not line:
                    break
                head = line.lstrip("-* ")
                if head.startswith(PKG_REPO_LABEL):
                    value = head[len(PKG_REPO_LABEL):].strip()
                    return Path(value) if value else None
    except OSError:
        return None
    return None


def exe_in_home(exe, home) -> bool:
    """`exe` 經 resolve＋normcase 後位於 `home` 之下；裸名（無目錄成分）一律 False；不查 PATH。"""
    text = str(exe or "")
    if not text or Path(text).parent == Path("."):
        return False
    base, target = _norm(home), _norm(text)
    return target != base and target.startswith(base.rstrip(os.sep) + os.sep)


# ── 主人存活（seam：測試以 mock.patch.object 換掉；預設不開行程）──────────────────────────────

def _filetime_iso(ticks: int) -> str:
    epoch = (ticks - _FILETIME_EPOCH_100NS) / 1e7
    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds")


def proc_probe(pid) -> tuple[bool, str | None]:
    """`(存活, 建立時間 ISO+offset 或 None)`。Windows 以 GetProcessTimes（無子行程）；其他平台
    `os.kill(pid, 0)` 且建立時間取不到 ⇒ None（呼叫端「可得時」才比對）。"""
    if not isinstance(pid, int) or pid <= 0:
        return False, None
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False, None
        except OSError:
            return True, None
        return True, None
    import ctypes  # noqa: PLC0415 — Windows 專屬
    from ctypes import wintypes  # noqa: PLC0415

    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = wintypes.HANDLE
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False, None
    try:
        code = ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:
            return False, None
        made, gone, sys_t, user_t = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, ctypes.byref(made), ctypes.byref(gone),
                                      ctypes.byref(sys_t), ctypes.byref(user_t)):
            return True, None
        return True, _filetime_iso((made.dwHighDateTime << 32) | made.dwLowDateTime)
    finally:
        kernel.CloseHandle(handle)


# ── 身分檔與租約 ─────────────────────────────────────────────────────────────────────────

def _write_json(path: Path, payload: dict) -> None:
    """同目錄暫存檔再覆寫（讀者不會看到半截檔）；被別人開著覆寫不了時退回直接寫（身分檔很小）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    temp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    try:
        os.replace(temp, path)
    except PermissionError:
        path.write_text(text, encoding="utf-8", newline="\n")
        temp.unlink(missing_ok=True)


def write_identity(home, *, run_id: str, sid: str, owner_pid: int, now: datetime,
                   window: bool = False) -> Path:
    """寫沙盒身分檔（`allow_until=null`＝預設拒絕）；回路徑。"""
    started = proc_probe(owner_pid)[1]
    path = Path(home) / IDENTITY_NAME
    _write_json(path, {"schema": SCHEMA, "run_id": run_id, "sid": sid, "owner_pid": owner_pid,
                       "owner_started": started or "",
                       "created_at": now.isoformat(timespec="seconds"),
                       "allow_until": None, "window": bool(window)})
    return path


class IdentityUnreadable(Exception):
    """身分檔缺席、亂碼或 schema 不符（⇒ `sandbox_unreadable`）。權限類例外不包在這裡。"""


def _read_identity(home) -> dict:
    try:
        data = json.loads((Path(home) / IDENTITY_NAME).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError) as exc:  # Unicode／JSON 解碼錯誤皆為 ValueError
        raise IdentityUnreadable(str(exc)) from exc
    if (not isinstance(data, dict) or data.get("schema") != SCHEMA
            or type(data.get("owner_pid")) is not int):
        raise IdentityUnreadable("schema")
    return data


def grant(home, *, until: datetime, now: datetime, max_minutes: int = LEASE_MAX,
          window: bool = False) -> datetime:
    """寫 `allow_until`＝`min(until, now+min(max_minutes, LEASE_CAP))`；再呼叫即續租（D-15）。"""
    identity = _read_identity(home)
    stored = min(until, now + timedelta(minutes=min(max_minutes, LEASE_CAP)))
    identity["allow_until"] = stored.isoformat(timespec="seconds")
    if window:
        identity["window"] = True
    _write_json(Path(home) / IDENTITY_NAME, identity)
    return stored


def revoke(home) -> None:
    identity = _read_identity(home)
    identity["allow_until"] = None
    _write_json(Path(home) / IDENTITY_NAME, identity)


def _lease(identity: dict, now: datetime) -> tuple[str, datetime | None]:
    """`(原因, allow_until)`；原因空字串＝租約有效（含主人存活判定）。"""
    raw = identity.get("allow_until")
    if raw is None:
        return "sandbox_no_lease", None
    until = datetime.fromisoformat(raw)
    if now >= until:
        return "sandbox_lease_expired", until
    alive, started = proc_probe(identity["owner_pid"])
    recorded = identity.get("owner_started") or ""
    if not alive:
        return "sandbox_owner_dead", until
    if started and recorded:
        seen, kept = datetime.fromisoformat(started), datetime.fromisoformat(recorded)
        gap = abs((seen - kept).total_seconds())
        if gap > _OWNER_START_TOLERANCE_SEC:
            return "sandbox_owner_dead", until
    return "", until


# ── 判準 ─────────────────────────────────────────────────────────────────────────────────

def _evaluate(cwd, pkg, transcript, exe, now) -> tuple[Verdict, datetime | None]:
    cwd_root = git_root(cwd) if cwd is not None else None
    pkg_path = Path(pkg) if pkg is not None else None
    pkg_repo = pkg_root(pkg_path) if pkg_path is not None else None
    pkg_repo_n = git_root(pkg_repo) if pkg_repo is not None else None
    roots = tuple(str(r) for r in (cwd_root, pkg_repo_n) if r is not None)
    flagged = [p for p in (cwd_root, pkg_path, pkg_repo_n,
                           Path(transcript).parent if transcript is not None else None)
               if p is not None and is_sandbox(p)]
    homes = list(dict.fromkeys(h for h in (sandbox_home(p) for p in flagged) if h is not None))
    if flagged:
        entities = [p for p in (pkg_path, pkg_repo_n, cwd_root, *homes) if p is not None]
        if any(not Path(p).exists() for p in entities):
            return Verdict(False, "target_missing", roots), None
    if cwd_root is not None and pkg_repo_n is not None and _norm(cwd_root) != _norm(pkg_repo_n):
        return Verdict(False, "root_mismatch", roots), None
    if not flagged:
        return Verdict(True, "production", roots), None
    if not homes:
        return Verdict(False, "sandbox_unreadable", roots), None
    soonest: datetime | None = None
    for home in homes:
        try:
            identity = _read_identity(home)
        except IdentityUnreadable:
            return Verdict(False, "sandbox_unreadable", roots), None
        why, until = _lease(identity, now)
        if why:
            return Verdict(False, why, roots), None
        if exe is not None and not exe_in_home(exe, home) and identity.get("window") is not True:
            return Verdict(False, "sandbox_real_exe", roots), None
        soonest = until if soonest is None or until < soonest else soonest
    return Verdict(True, "sandbox_lease", roots), soonest


def target_verdict(*, cwd, pkg=None, transcript=None, exe=None, now: datetime) -> Verdict:
    """`exe`＝本次要用的 `claude` 執行檔（spawn／tick／headless 站點必傳，未給時傳 `"claude"`；
    其餘站點傳 None）。任何例外 ⇒ `Verdict(False, "error:<類名>")`（fail-closed）。"""
    try:
        return _evaluate(cwd, pkg, transcript, exe, now)[0]
    except Exception as exc:  # noqa: BLE001 — 判準自己出錯一律拒絕，呼叫端另落痕跡
        return Verdict(False, f"error:{type(exc).__name__}", ())


def register_verdict(*, cwd, pkg=None, fire_at: datetime, now: datetime) -> Verdict:
    """登記站點用：沙盒放行時 `fire_at > allow_until` ⇒ `lease_shorter_than_fire`（D-15）。"""
    try:
        verdict, until = _evaluate(cwd, pkg, None, None, now)
        if verdict.allow and until is not None and fire_at > until:
            return Verdict(False, "lease_shorter_than_fire", verdict.roots)
        return verdict
    except Exception as exc:  # noqa: BLE001
        return Verdict(False, f"error:{type(exc).__name__}", ())


def job_expiry(home, now: datetime) -> datetime | None:
    """排程自毀時刻：正式目標（`home` 為 None）⇒ None；沙盒且租約有效 ⇒ `allow_until`。"""
    if home is None:
        return None
    try:
        why, until = _lease(_read_identity(home), now)
    except Exception:  # noqa: BLE001 — 讀不懂＝不替它加自毀（登記站點的判準另會拒絕）
        return None
    return until if not why else None
