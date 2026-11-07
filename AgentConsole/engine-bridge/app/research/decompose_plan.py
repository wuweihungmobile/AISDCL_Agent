"""拆解橋：凍結 PRD → 逐 US（或逐 Goal）呼叫既有 `DecomposeService` → `task_decomposition.json`
（PRD §5.1.6；FR-R2P-14；D-94／D-110／D-113；TCS AC-961-10）。

不改 `app/decompose.py` 與 AutoClaude：本模組只**呼叫**它。核心紀律是 Rule 5——覆蓋對映是確定性的事，
交給程式碼，不信模型自報：

  · 每次呼叫對應一組確定的 AC（該 US 的 `**對應 AC**` 清單；按 Goal 分批時為該 Feature 底下全部 US
    的 AC 聯集；整份單次時為全部 AC），`covers_ac`／`covers_us` 由**這次呼叫綁定的清單**賦值，模型
    輸出裡的任何 `covers_*` 都會被覆蓋；
  · 三道有界閘（≤24 步、DAG 無環、prompt 非空）沿用既有服務，逾界回 422 結構化錯誤、不截斷，並寫一列
    `REJECTED`（`gate_rejection`）；整份拆解只要有一次呼叫被拒就整份被拒（不留部分結果）；
  · 簽核只由 console-api 先走既有 import／signoff 取得 `import_record_id` 後呼叫回呼寫入（D-113）；
    本模組**沒有**把 `signed_off` 寫成字面真值的路徑——簽核狀態一律由「是否帶有真實的 import 記錄
    id」推得（`signed_off = bool(import_record_id)`）。
"""
from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import sdd_cli
from ..errors import ApiError, unprocessable
from ..models import DecomposeIn
from . import layout
from .db import ResearchDb, utc_now
from .outbox import DurableWriter, FileRef, FileWrite, Op

DECOMPOSITION_REL = "03_execution/task_decomposition.json"
MAX_STEPS = 24
WAIVER_REASON_MAX = 500
#: 既有服務的 `gate` 值（`decompose.py:37-47`）；其餘一律歸 `brain_failed`。
GATES = frozenset({"max_steps", "cycle", "empty_prompt", "brain_failed", "brain_unsupported"})
BY_MODES = ("us", "goal", "all")
_US_HEAD_RE = re.compile(r"^#{2,6}\s+(US-\d{3})\s*(.*)$")
_FEATURE_HEAD_RE = re.compile(r"^#{2,6}\s+(F-\d{3})\s*(.*)$")
_AC_HEAD_RE = re.compile(r"^#{2,6}\s+(AC-\d{3}-\d+)\s*(.*)$")
_AC_ID_RE = re.compile(r"AC-\d{3}-\d+")
_US_ID_RE = re.compile(r"US-\d{3}")
_FROZEN_BASELINE_RE = re.compile(r"^01_specs/PRD-v\d+\.\d+\.\d+\.md$")


# ══ PRD 解析（確定性）═══════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class Story:
    us_id: str
    title: str
    acs: tuple[str, ...]


@dataclass(frozen=True)
class PrdMap:
    stories: tuple[Story, ...]
    ac_titles: Mapping[str, str]
    features: Mapping[str, tuple[str, tuple[str, ...]]]     # F-id → (標題, 其 US 清單)

    @property
    def acs(self) -> tuple[str, ...]:
        """凍結 PRD 的 AC 集合＝`#### AC-` 標題的機械計數（與 QA 維度 `ac_total` 同判準）。"""
        return tuple(sorted(self.ac_titles))


def _field(block: Sequence[str], label: str, id_re: re.Pattern[str]) -> list[str]:
    pattern = re.compile(rf"對應\s*{label}\s*\**\s*[:：](.*)")
    for line in block:
        match = pattern.search(line)
        if match:
            return id_re.findall(match.group(1))
    return []


def parse_prd(text: str) -> PrdMap:
    lines = text.splitlines()
    heads = [(i, line) for i, line in enumerate(lines) if line.startswith("#")]

    def block(index: int) -> list[str]:
        later = [j for j, _ in heads if j > index]
        return lines[index + 1:(later[0] if later else len(lines))]

    stories: list[Story] = []
    ac_titles: dict[str, str] = {}
    features: dict[str, tuple[str, tuple[str, ...]]] = {}
    for index, line in heads:
        if match := _US_HEAD_RE.match(line):
            acs = _field(block(index), "AC", _AC_ID_RE)
            stories.append(Story(match.group(1), match.group(2).strip(),
                                 tuple(dict.fromkeys(acs))))
        elif match := _AC_HEAD_RE.match(line):
            ac_titles[match.group(1)] = match.group(2).strip()
        elif match := _FEATURE_HEAD_RE.match(line):
            features[match.group(1)] = (match.group(2).strip(), tuple(
                dict.fromkeys(_field(block(index), "US", _US_ID_RE))))
    return PrdMap(tuple(stories), ac_titles, features)


@dataclass(frozen=True)
class Batch:
    """一次拆解呼叫的確定性綁定：它對應哪些 US 與 AC。"""

    key: str
    name: str
    us_ids: tuple[str, ...]
    acs: tuple[str, ...]


def plan_batches(prd: PrdMap, by: str = "us", us_ids: Sequence[str] | None = None
                 ) -> list[Batch]:
    """`us`：每個 US 一批；`goal`：每個 Feature 一批（其底下 US 的 AC 聯集；沒有 Feature 的 US
    各自一批）；`all`：整份單次（大型 PRD 會被 24 步閘擋下——這就是要按 Goal 分批的原因）。"""
    if by not in BY_MODES:
        raise ValueError(f"by 須為 {BY_MODES}")
    chosen = [s for s in prd.stories if not us_ids or s.us_id in us_ids]
    if by == "us":
        return [Batch(s.us_id, s.title or s.us_id, (s.us_id,), s.acs) for s in chosen]
    if by == "all":
        return [Batch("ALL", "整份 PRD", tuple(s.us_id for s in chosen), tuple(
            dict.fromkeys(ac for s in chosen for ac in s.acs)))]
    by_id = {s.us_id: s for s in chosen}
    batches: list[Batch] = []
    used: set[str] = set()
    for fid, (title, members) in prd.features.items():
        picked = [by_id[u] for u in members if u in by_id]
        if picked:
            used.update(s.us_id for s in picked)
            batches.append(Batch(fid, title or fid, tuple(s.us_id for s in picked), tuple(
                dict.fromkeys(ac for s in picked for ac in s.acs))))
    batches += [Batch(s.us_id, s.title or s.us_id, (s.us_id,), s.acs)
                for s in chosen if s.us_id not in used]
    return batches


# ══ 覆蓋對映 ═════════════════════════════════════════════════════════════════════════════════
def coverage(prd_acs: Sequence[str], tasks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """`{total, covered, uncovered[], unknown_ac[]}`：未覆蓋與未知 AC 依字母序；重複涵蓋不影響。"""
    wanted = set(prd_acs)
    seen: set[str] = set()
    for task in tasks:
        seen.update(str(a) for a in (task.get("covers_ac") or []))
    return {"total": len(wanted), "covered": len(wanted & seen),
            "uncovered": sorted(wanted - seen), "unknown_ac": sorted(seen - wanted)}


# ══ 拆解 ═════════════════════════════════════════════════════════════════════════════════════
def _context(batch: Batch, prd: PrdMap, sha: str) -> str:
    lines = [f"凍結 PRD sha256 {sha[:12]}；範圍 {batch.key} {batch.name}",
             "驗收標準（AC）：" + "；".join(
                 f"{ac} {prd.ac_titles.get(ac, '')}".strip() for ac in batch.acs)]
    return "\n".join(lines)


def _rejection(exc: ApiError) -> tuple[str, str]:
    body = exc.body or {}
    gate = str(body.get("gate") or "")
    return (gate if gate in GATES else "brain_failed"), str(body.get("detail") or "")[:300]


def build_document(*, research_ref: str, version: int, prd_semver: str, prd_sha256: str,
                   goals: Sequence[Mapping[str, Any]], draft_ids: Sequence[str],
                   coverage: Mapping[str, Any] | None = None,
                   console_project_id: str | None = None) -> dict[str, Any]:
    """PRD §5.1.6 的形狀；`signed_off` 恆為 `False`（簽核只走 `signoff_document`）。"""
    return {"schema_rev": 1, "research_id": research_ref, "version": version,
            "prd_version": prd_semver, "prd_sha256": prd_sha256,
            "generated_by": "GoalDecomposer", "signed_off": False, "signed_off_by": None,
            "signed_off_at": None, "limits": {"max_steps_per_goal": MAX_STEPS},
            "coverage": dict(coverage or {"total": 0, "covered": 0, "uncovered": []}),
            "goals": [dict(g) for g in goals], "waivers": [],
            "console_project_id": console_project_id, "draft_ids": list(draft_ids)}


def all_tasks(doc: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [t for g in (doc.get("goals") or []) for t in (g.get("tasks") or [])
            if isinstance(t, dict)]


def render(doc: Mapping[str, Any]) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


@dataclass(frozen=True)
class FrozenRef:
    rel: str
    sha256: str
    semver: str


def frozen_prd(db: ResearchDb, research_id: str) -> FrozenRef | None:
    """目前有效的凍結 PRD（最近一筆 Gate 0／Gate-0-SCR 核准）：基線檔路徑、凍結摘要、語意版本。"""
    rows = db.query(
        "SELECT frozen_digests FROM {s}.research_gate_decisions WHERE research_id = %s AND "
        "gate = 'GATE0' AND decision = 'APPROVED' ORDER BY decided_at DESC LIMIT 1",
        (research_id,))
    if not rows:
        return None
    for rel, value in (rows[0]["frozen_digests"] or {}).items():
        if _FROZEN_BASELINE_RE.match(str(rel)):
            return FrozenRef(str(rel), str(value).removeprefix("sha256:"),
                             str(rel).removeprefix("01_specs/PRD-").removesuffix(".md"))
    return None


@dataclass
class DecomposeEnv:
    db: ResearchDb
    writer: DurableWriter
    service: Any                      # `DecomposeService`（`app/decompose.py`；不改它）


def decompose(env: DecomposeEnv, row: Mapping[str, Any], *, requested_by: str,
              by: str = "us", us_ids: Sequence[str] | None = None) -> dict[str, Any]:
    """逐批呼叫既有服務、確定性綁定 AC、合併成 `task_decomposition.json`、入庫。任一批被拒＝整份
    422（`violations[].rule`＝閘別）並寫一列 `REJECTED`（不寫檔、不寫 artifact、游標不動）。"""
    rid, ws = str(row["id"]), Path(row["workspace_path"])
    ref = frozen_prd(env.db, rid)
    if ref is None:
        raise ApiError(409, "fsm_state_conflict", details={"cause": "prd_not_frozen"})
    prd = parse_prd(layout.safe_join(ws, ref.rel).read_text(encoding="utf-8"))
    batches = plan_batches(prd, by, us_ids)
    previous = env.db.latest_decomposition(rid)
    goals: list[dict[str, Any]] = []
    draft_ids: list[str] = []
    number = 0
    for g_no, batch in enumerate(batches, start=1):
        try:
            draft = env.service.decompose(DecomposeIn(
                goal=f"實作 {batch.key}：{batch.name}", context=_context(batch, prd, ref.sha256),
                project=f"{row['slug']}-{batch.key}"[:200], max_steps=MAX_STEPS))
        except ApiError as exc:
            gate, detail = _rejection(exc)
            _reject(env, rid, requested_by, ref.sha256, gate)
            raise unprocessable([{"field": "decomposition", "rule": gate, "message": detail,
                                  "detail": detail, "batch": batch.key}],
                                "invalid_request") from exc
        draft_ids.append(str(draft.get("draft_id", "")))
        tasks = []
        for raw in (draft.get("playbook") or {}).get("tasks") or []:
            number += 1
            tasks.append({"task_id": f"T-{number}", "name": str(raw.get("name", "")),
                          "prompt": str(raw.get("prompt", "")), "covers_us": list(batch.us_ids),
                          "covers_ac": list(batch.acs),      # 確定性綁定：不採信模型自報
                          "evaluator_command": raw.get("evaluator_command"),
                          "estimated_tokens": None})
        goals.append({"goal_id": f"G-{g_no}", "name": batch.name,
                      "pass_criteria": "；".join(batch.acs) or batch.name, "depends_on": [],
                      "tasks": tasks})
    version = env.db.latest_artifact_version(rid, "TASK_DECOMPOSITION") + 1
    flat = [t for g in goals for t in g["tasks"]]
    cover = coverage(prd.acs, flat)       # D-133：console-api 優先讀頂層 coverage
    doc = build_document(
        research_ref=str(row["rp_no"]), version=version, prd_semver=ref.semver,
        prd_sha256=ref.sha256, goals=goals, draft_ids=draft_ids,
        coverage={k: cover[k] for k in ("total", "covered", "uncovered")})
    text = render(doc)
    sha = layout.sha256_text(text)
    decomposition_id = str(uuid.uuid4())
    env.writer.persist(Op("decomp.create", rid, {
        "research_id": rid, "decomposition_id": decomposition_id, "draft_id": draft_ids[0][:64]
        if draft_ids and draft_ids[0] else None, "prd_sha256": ref.sha256,
        "tasks_count": len(all_tasks(doc)), "status": "DRAFTED",
        # D-110：重拆新列承接前一列的 TCS 欄
        "tcs_rel_path": previous.get("tcs_rel_path") if previous else None,
        "tcs_sha256": previous.get("tcs_sha256") if previous else None,
        "created_by": requested_by, "created_at": utc_now().isoformat(),
        "artifact": {"version": version, "rel_path": DECOMPOSITION_REL, "sha256": sha,
                     "bytes": len(text.encode("utf-8")), "content": text}},
        files=(FileRef(str(ws), DECOMPOSITION_REL, sha),)),
        writes=[FileWrite(ws, DECOMPOSITION_REL, text)])
    return {"decomposition_id": decomposition_id, "status": "DRAFTED",
            "tasks_count": len(all_tasks(doc)),
            "coverage": coverage(prd.acs, all_tasks(doc))}


def _reject(env: DecomposeEnv, rid: str, requested_by: str, prd_sha: str, gate: str) -> None:
    env.writer.persist(Op("decomp.create", rid, {
        "research_id": rid, "decomposition_id": str(uuid.uuid4()), "prd_sha256": prd_sha,
        "tasks_count": 0, "status": "REJECTED", "gate_rejection": gate,
        "created_by": requested_by, "created_at": utc_now().isoformat()}))


# ══ 簽核（D-113）═════════════════════════════════════════════════════════════════════════════
def _v(field: str, rule: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"field": field, "rule": rule, "message": message, **extra}


def waiver_violations(waivers: Sequence[Any], uncovered: Sequence[str]) -> list[dict[str, Any]]:
    """簽核前置（AC-14-2）：未覆蓋者清零或各有一句人工豁免（1～500 字）；豁免只准對未覆蓋的 AC。"""
    found: list[dict[str, Any]] = []
    waived: set[str] = set()
    for index, item in enumerate(waivers):
        if not isinstance(item, Mapping):
            found.append(_v(f"waivers[{index}]", "waiver_invalid", "豁免須為 {ac, reason}"))
            continue
        ac, reason = item.get("ac"), item.get("reason")
        if ac not in uncovered:
            found.append(_v(f"waivers[{index}].ac", "waiver_ac_invalid",
                            "只能豁免未覆蓋的 AC", ac=ac))
            continue
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= WAIVER_REASON_MAX or (
                len(reason) > WAIVER_REASON_MAX):
            found.append(_v(f"waivers[{index}].reason", "waiver_reason_invalid",
                            f"豁免理由須為 1～{WAIVER_REASON_MAX} 字", ac=ac))
            continue
        waived.add(str(ac))
    found += [_v("coverage", "uncovered_ac", f"{ac} 未被任何 task 涵蓋且無豁免", ac=ac)
              for ac in uncovered if ac not in waived]
    return found


def signoff(env: DecomposeEnv, row: Mapping[str, Any], body: Mapping[str, Any]
            ) -> dict[str, Any]:
    """`:decomposition-signoff`（console-api 先走既有 import／signoff 取得 `import_record_id`）。
    檢查序：approver→列存在與狀態（409）→stale（409）→豁免與覆蓋（422）→同交易寫入。"""
    rid, ws = str(row["id"]), Path(row["workspace_path"])
    approver = sdd_cli.validate_research_approver(body.get("approver"))
    try:
        decomposition_id = str(uuid.UUID(str(body.get("decomposition_id"))))
        import_record_id = str(uuid.UUID(str(body.get("import_record_id"))))
    except ValueError as exc:
        raise unprocessable([_v("decomposition_id", "invalid_uuid",
                                "decomposition_id 與 import_record_id 須為 UUID")],
                            "invalid_request") from exc
    decomposition = env.db.get_decomposition(decomposition_id)
    if decomposition is None or str(decomposition["research_id"]) != rid:
        raise ApiError(404, "research_not_found", decomposition_id=decomposition_id)
    if decomposition["status"] == "SIGNED_OFF" and str(
            decomposition["import_record_id"]) == import_record_id:
        done = env.db.latest_artifact(rid, "TASK_DECOMPOSITION")      # D-133：冪等，不改列不重發
        assert done is not None
        return {"decomposition_id": decomposition_id, "status": "SIGNED_OFF",
                "artifact_sha256": str(done["sha256"]).strip()}
    if decomposition["status"] not in ("DRAFTED", "SCG_PASSED"):
        raise ApiError(409, "fsm_state_conflict", details={"status": decomposition["status"]})
    ref = frozen_prd(env.db, rid)
    if ref is None or decomposition["prd_sha256"] != ref.sha256:
        raise ApiError(409, "decomposition_stale", details={
            "prd_sha256": decomposition["prd_sha256"], "frozen_sha256": None if ref is None
            else ref.sha256})
    art = env.db.latest_artifact(rid, "TASK_DECOMPOSITION")
    if art is None:
        raise ApiError(409, "fsm_state_conflict", details={"cause": "artifact_missing"})
    doc = json.loads(str(art["content"]))
    prd = parse_prd(layout.safe_join(ws, ref.rel).read_text(encoding="utf-8"))
    cover = coverage(prd.acs, all_tasks(doc))
    waivers = body.get("waivers") or []
    if not isinstance(waivers, list):
        raise unprocessable([_v("waivers", "waiver_invalid", "waivers 須為清單")],
                            "invalid_request")
    violations = waiver_violations(waivers, cover["uncovered"])
    if violations:
        raise unprocessable(violations, "invalid_request")
    at = utc_now().isoformat()
    signed = {**doc, "version": int(art["version"]) + 1,
              "signed_off": bool(import_record_id),       # 由真實的 import 記錄 id 推得，不是字面值
              "signed_off_by": approver, "signed_off_at": at,
              "waivers": [{"ac": w["ac"], "reason": w["reason"], "by": approver, "at": at}
                          for w in waivers],
              "console_project_id": str(body.get("console_project_id") or "") or None}
    text = render(signed)
    sha = layout.sha256_text(text)
    env.writer.persist(Op("decomp.signoff", rid, {
        "research_id": rid, "decomposition_id": decomposition_id,
        "import_record_id": import_record_id, "approver": approver,
        "artifact": {"version": signed["version"], "rel_path": DECOMPOSITION_REL, "sha256": sha,
                     "bytes": len(text.encode("utf-8")), "content": text}},
        files=(FileRef(str(ws), DECOMPOSITION_REL, sha),)),
        writes=[FileWrite(ws, DECOMPOSITION_REL, text)])
    return {"decomposition_id": decomposition_id, "status": "SIGNED_OFF", "artifact_sha256": sha}


def mark_stale(env: DecomposeEnv, rid: str) -> int:
    """PRD 凍結摘要改變後把摘要不同的拆解標 STALE（`prd_sha256` 欄與簽核事實不動）。"""
    ref = frozen_prd(env.db, rid)
    if ref is None:
        return 0
    result = env.writer.persist(Op("decomp.stale", rid, {
        "research_id": rid, "prd_sha256": ref.sha256}))
    return int(result.get("staled", 0))


def is_stale(decomposition: Mapping[str, Any], frozen_sha: str | None) -> bool:
    """衍生旗標：已 `STALE`，或 `prd_sha256` 與現凍結摘要不同。"""
    return decomposition["status"] == "STALE" or (
        frozen_sha is not None and decomposition["prd_sha256"] != frozen_sha)
