"""租約帳的發現式掃描（未登記殘留）與拒跑出口（DES RealVerify_SideEffect_Isolation §5.3，REQ-SE-32／37）。

帳只涵蓋載具自己做的事；產品被測時自己登記的排程、開的視窗、建的目錄，載具事先並不知道名字。
所以另有一層「依特徵掃」：Action／路徑含載具前綴而**無可驗證存活的主人**者＝孤兒。判準的唯一硬約束是
**主人可驗證存活 ⇒ 一律不動**（別的 realverify 視窗正在跑的長案例，D-16）。撤銷動作：排程走
`leases.revoke_sched`（排程撤銷全套件唯一家）、目錄走 `leases_undo.revoke_path`。
`scan` 只讀不動（`sweep --dry-run`／`snapshot` 共用）；`apply` 才撤。
"""  # noqa: E501

from __future__ import annotations

import os
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from lib import sandbox_scope

from . import leases, leases_undo, sched
from .sandbox import slug_of

SBX = sandbox_scope.SBX_PREFIX
PROD = "AutoSDD_RVprod_"
_SBX_ROOT_RE = re.compile(r"[^\s\"']*" + re.escape(SBX) + r"[A-Za-z0-9]+", re.I)
_PROD_RUN_RE = re.compile(re.escape(PROD) + r"(\d{8}T\d{6}-\d+-[0-9a-f]{6})", re.I)
_PROD_SLUG_RE = re.compile(r"AutoSDD-RVprod-(\d{8}T\d{6}-\d+-[0-9a-f]{6})", re.I)


@dataclass(frozen=True)
class Finding:
    kind: str        # sched／dir／project
    ident: str       # 工作名或路徑
    why: str
    action: str = "revoke"   # revoke／note（abandoned 之下：只記，不計入 unrevoked）


def _under_abandoned(ident: str, abandoned: set[str]) -> bool:
    try:
        norm = os.path.normcase(str(Path(ident).resolve()))
    except OSError:
        return False
    return any(norm == a or norm.startswith(a.rstrip(os.sep) + os.sep) for a in abandoned)


def _read_identity_row(home: Path) -> dict | None:
    try:
        ident = sandbox_scope._read_identity(home)  # noqa: SLF001 — 同一份身分檔解析，不另寫第二份
    except Exception:  # noqa: BLE001 — 讀不懂＝視同無身分檔
        return None
    return {"owner_pid": ident["owner_pid"], "owner_started": ident.get("owner_started") or None,
            "expires_at": ident.get("allow_until") or ident.get("created_at")}


def _home_state(root: Path, now: datetime) -> str:
    """沙盒家目錄 → `live`／`dead`。有身分檔：以主人存活判；無身分檔：mtime 超過 `LEASE_CAP` 才算 dead。"""  # noqa: E501
    row = _read_identity_row(root) if root.is_dir() else None
    if row is not None:
        verdict = leases.owner_verdict(row, now)
        if verdict == "alive":
            return "live"
        if verdict == "dead":
            return "dead"
        created = row.get("expires_at")
        try:
            return "dead" if created and datetime.fromisoformat(created).timestamp() \
                + sandbox_scope.LEASE_CAP * 60 < now.timestamp() else "live"
        except ValueError:
            return "dead"
    if not root.is_dir():
        return "dead"
    try:
        age_min = (time.time() - root.stat().st_mtime) / 60
    except OSError:
        return "dead"
    return "dead" if age_min > sandbox_scope.LEASE_CAP else "live"


def _prod_dead(run_id: str, now: datetime) -> bool:
    return leases.account_state(run_id, now) != "live"


def _scan_sched(now: datetime) -> list[Finding]:
    out: list[Finding] = []
    keep = leases.live_idents(now)
    for name, action in sorted(sched.list_actions("AutoSDD_*").items()):
        if name.startswith(sched.PREFIX):                    # 舊規則：RV 前綴排程不在存活帳內＝殘留
            if name not in keep:
                out.append(Finding("sched", name, "RV 排程不在任何主人存活的帳內"))
            continue
        roots = _SBX_ROOT_RE.findall(action)
        if roots:
            dead = [r for r in roots if _home_state(Path(sandbox_scope.sandbox_home(r) or r), now) == "dead"]  # noqa: E501
            if dead:
                out.append(Finding("sched", name, f"Action 含沙盒根而其主人已死：{dead[0]}"))
            continue
        prod = _PROD_RUN_RE.search(action)
        if prod and _prod_dead(prod.group(1), now):
            out.append(Finding("sched", name, f"Action 含 {PROD}{prod.group(1)} 而該 run 帳非存活"))
    return out


def _scan_dirs(now: datetime, tmp_root: Path) -> list[Finding]:
    out: list[Finding] = []
    for d in sorted(tmp_root.glob(f"{SBX}*")):
        if d.is_dir() and _home_state(d, now) == "dead":
            out.append(Finding("dir", str(d), "沙盒家目錄的主人已死（或無身分檔且逾 LEASE_CAP）"))
    for d in sorted(tmp_root.glob(f"{PROD}*")):
        m = _PROD_RUN_RE.search(d.name)
        if d.is_dir() and m and _prod_dead(m.group(1), now):
            out.append(Finding("dir", str(d), "RVprod 目錄的 run 帳非存活"))
    return out


def classify_projects(now: datetime, projects: Path, sessions: Path | None,
                      tmp_root: Path) -> list[tuple[Path, bool, str]]:
    """`~/.claude/projects` 下載具相關目錄的判決：`(目錄, 是否刪, 原因)`。沙盒目錄：家目錄（或其 worktree
    外層）仍在 ⇒ 留；`~/.claude/sessions` 有活 cwd 指向 ⇒ 留；否則刪。RVprod：run 帳非存活才刪。"""  # noqa: E501
    from lib.sessionctl import procstop  # noqa: PLC0415 — lazy：避免載入時的套件相依
    out: list[tuple[Path, bool, str]] = []
    if not projects.is_dir():
        return out
    live_roots = {slug_of(p) for p in tmp_root.glob(f"{SBX}*") if p.is_dir()}
    cwd_slugs = {slug_of(r["cwd"]) for r in procstop.registry_rows(sessions) if isinstance(r.get("cwd"), str)}  # noqa: E501
    mark = slug_of(SBX)
    for folder in sorted(projects.iterdir()):
        if not folder.is_dir():
            continue
        busy = any(s == folder.name or s.startswith(folder.name + "-") for s in cwd_slugs)
        if mark in folder.name:
            held = any(folder.name == s or folder.name.startswith(s + "-") for s in live_roots)
            if held:
                out.append((folder, False, "沙盒根仍存在"))
            elif busy:
                out.append((folder, False, "登記檔 cwd 指向它（有行程在用）"))
            else:
                out.append((folder, True, "沙盒家已不在且沒有行程在用"))
        else:
            m = _PROD_SLUG_RE.search(folder.name)
            if m:
                dead = _prod_dead(m.group(1), now)
                out.append((folder, dead and not busy,
                            "RVprod 專案目錄的 run 帳非存活" if dead and not busy else "RVprod 仍有主人或行程在用"))  # noqa: E501
    return out


def _scan_projects(now: datetime, projects: Path, sessions: Path | None, tmp_root: Path) -> list[Finding]:  # noqa: E501
    return [Finding("project", str(f), why) for f, drop, why in classify_projects(now, projects, sessions, tmp_root)  # noqa: E501
            if drop]


def sweep_projects(*, projects: Path | None = None, sessions: Path | None = None,
                   tmp_root: Path | None = None, dry_run: bool = False) -> dict:
    """`sandbox.sweep_orphans` 的本體：回 `{removed: [名], kept: [(名, 原因)]}`；`dry_run` 只列不刪。
    只動 `projects` 下名稱符合載具前綴者——別的專案絕不碰。"""  # noqa: E501
    from .sandbox import _remove_tree, projects_dir  # noqa: PLC0415 — lazy（與 scan 同理由）
    base = Path(projects) if projects is not None else projects_dir()
    tmp = Path(tmp_root) if tmp_root is not None else Path(tempfile.gettempdir())
    out: dict = {"removed": [], "kept": []}
    for folder, drop, why in classify_projects(datetime.now().astimezone(), base, sessions, tmp):
        if not drop:
            out["kept"].append((folder.name, why))
        elif dry_run or not _remove_tree(folder, "orphan"):
            out["removed"].append(folder.name)
        else:
            out["kept"].append((folder.name, "刪除失敗（RESIDUE）"))
    return out


def scan(now: datetime | None = None, *, tmp_root: Path | None = None, projects: Path | None = None,
         sessions: Path | None = None) -> list[Finding]:
    """唯讀：列出發現式掃描會處置的項目；abandoned 之下者降為 `note`（D-11）。"""
    from .sandbox import projects_dir  # noqa: PLC0415 — lazy：sandbox 頂層 import leases
    t = now or datetime.now().astimezone()
    tmp = Path(tmp_root) if tmp_root is not None else Path(tempfile.gettempdir())
    found = (_scan_sched(t) + _scan_dirs(t, tmp)
             + _scan_projects(t, Path(projects) if projects is not None else projects_dir(), sessions, tmp))  # noqa: E501
    abandoned = leases.abandoned_paths()
    return [f if f.kind == "sched" or not _under_abandoned(f.ident, abandoned)
            else Finding(f.kind, f.ident, f.why, "note") for f in found]


def apply(findings: list[Finding]) -> tuple[list[str], dict[str, str]]:
    """撤銷 `revoke` 項；回 `(已撤 ident 清單, {撤不掉的 ident: 原因})`。`note` 項不動、也不計入撤不掉。"""  # noqa: E501
    done: list[str] = []
    stuck: dict[str, str] = {}
    for f in findings:
        if f.action != "revoke":
            continue
        try:
            if f.kind == "sched":
                ok, why = leases.revoke_sched(f.ident), "回讀仍在"
            else:
                ok, why = leases_undo.revoke_path("orphan-" + f.kind, f.ident)
        except Exception as exc:  # noqa: BLE001 — 撤不掉就是撤不掉，不假裝結清
            ok, why = False, f"{type(exc).__name__}: {exc}"
        if ok:
            done.append(f.ident)
        else:
            stuck[f.ident] = f"{f.why}；{why}"
    return done, stuck


def preflight() -> tuple[list[str], dict[str, str]]:
    """`run` 開頭：重放租約帳＋發現式掃描。回 `(要印的行, {撤不掉的 ident: 原因})`（不含 abandoned 之下者，
    那些只記 note，D-11）。主人可驗證存活者一律不動（D-16）。"""  # noqa: E501
    rep = leases.replay_report()
    lines = [f"↩ 重放租約帳：已撤孤兒 {r}" for r in rep.revoked]
    stuck = dict(rep.info)
    found = scan()
    done, bad = apply(found)
    lines += [f"↩ 發現式掃描：已撤殘留 {i}" for i in done]
    lines += [f"note: {f.ident} 位於已放棄（abandoned）的 ident 之下，只記錄不處置（{f.why}）"
              for f in found if f.action == "note"]
    stuck.update(bad)
    return lines, stuck


# ── 拒跑出口（REQ-SE-37）──────────────────────────────────────────────────────────────────

def refusal_handback(run_id: str, items: dict[str, str], *, now: float | None = None) -> Path | None:  # noqa: E501
    """`run` 因撤不掉的孤兒拒跑時：寫 handback（居所＝`endurance_env` 的 handback 居所，預設真
    `~/.autosdd/handback`；列每項 ident、原因、`--abandon` 指令）並依 `quota_escalation` 既有語意入通知佇列
    （通知開關關閉時照其規則不入列）。回 handback 路徑（寫不進回 None，不以例外打斷拒跑判決）。"""  # noqa: E501
    from lib import endurance_env, quota_escalation  # noqa: PLC0415 — lazy：重模組只在拒跑時才載入
    lines = [f"# realverify 拒跑：有撤不掉的孤兒（run {run_id}）", ""]
    lines += [f"- `{ident}` — {why}" for ident, why in items.items()]
    lines += ["", "人工出口（只把帳記為 abandoned，不砍行程、不刪檔）：", "",
              "    python tools/realverify.py sweep --abandon <帳 run_id> --why \"<至少 8 字的理由>\""]  # noqa: E501
    body = "\n".join(lines) + "\n"
    try:
        target = endurance_env.handback_dir_status()[0] / f"realverify_orphans_{run_id}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8", newline="\n")
    except OSError:
        target = None
    title = "realverify 拒跑：有撤不掉的孤兒"
    rc = quota_escalation.notify(title, f"{len(items)} 項；見 handback realverify_orphans_{run_id}.md")  # noqa: E501
    quota_escalation.queue_notify(title, body[:300], rc, time.time() if now is None else now)
    return target
