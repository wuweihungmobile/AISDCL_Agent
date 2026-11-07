"""交付（ResearchToPRD P2；TCS AC-962-17、18、20、26；IFACE §6）：追溯表、Release Tag、PR。

本模組**零 FSM 寫入、零子行程**：版控只經注入的 `Gitops`（唯一出口），RELEASE 轉態由路由層呼叫
`inner_gates.release_transition`。三件事：

  · `build_traceability`：一列＝凍結 PRD 的一個 AC（集合相等、無遺漏無多餘）。`unitStatus` 由 R8
    `covers_ac` 對映的 Console 任務終態導出（沒有逐 AC 的機器來源就如實標 `NONE`／`NOT_RUN`）；
    `totals` 的 `uncovered`＝`unitStatus` 不為 PASS 的列數（零測試不是通過）、另帶 `frTotal`。
  · `create_tag`：驗證→冪等探測→取 commit→快照→`tag -a`（訊息只取模板，使用者文字不進 argv）→
    （`push` 且有 origin）推送（絕不強推）→單一 DB 交易入庫（列＋事件）。失敗不補償（刪 tag／刪遠端
    ref 皆屬毀滅性動作），只留可重送的冪等路徑。
  · `create_pr`：標題與內文全由資料欄位確定性拼裝（不帶使用者自由文字）；失敗不寫 FAILED 列，只發
    失敗事件。
"""
from __future__ import annotations

import json
import re
import shutil
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import fsutil
from ..errors import ApiError, unprocessable
from . import decompose_plan, gitops, healing, layout
from . import scr as scr_mod
from . import settings as settings_mod
from .db import ResearchDb, utc_now
from .outbox import DurableWriter, Op

TRACE_REL = "03_execution/traceability_matrix.json"
GHERKIN_MAX = 120
DETAIL_MAX = 2000
PR_BODY_MAX = 4000
PR_TITLE_CHARS = 60
STDERR_TAIL = 500
UNIT_STATUSES = ("PASS", "FAIL", "NOT_RUN", "NONE")
FAILURE_STEPS = ("push", "pr_create", "fsm_release", "tag")
PR_TITLE_TEMPLATE = "feat: {rp_no} {title}（{fr} FR／{ac} AC）"
#: 時鐘注入縫（測試固定時間戳）。
NOW: Callable[[], Any] = utc_now
_SEG_RE = re.compile(r"\b(Given|When|Then)\b")
_HTML_RE = re.compile(r"<[^>]*>")
_AC_HEAD_RE = re.compile(r"^#{2,6}\s+(AC-[0-9][0-9A-Za-z-]*)\s*(.*)$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


@dataclass
class DeliveryEnv:
    """交付需要的部署事實與注入點：`git`＝唯一的版控出口、`rtm_report(run_id)` 取 RTM 報告。"""

    cfg: Any
    db: ResearchDb
    writer: DurableWriter
    git: gitops.Gitops
    rtm_report: Callable[[str], Mapping[str, Any]] | None = None


# ══ 追溯表 ═══════════════════════════════════════════════════════════════════════════════════
def _clip(text: str, limit: int = GHERKIN_MAX) -> str:
    plain = " ".join(_HTML_RE.sub("", text).split())
    return plain if len(plain) <= limit else plain[:limit - 1].rstrip() + "…"


def gherkin_summary(body: str) -> dict[str, str]:
    """Given／When／Then 各段摘要（純文字、每段至多 120 字；超過者以省略號結尾）。"""
    parts = _SEG_RE.split(body)
    out = {"given": "", "when": "", "then": ""}
    for keyword, text in zip(parts[1::2], parts[2::2], strict=False):
        out[keyword.lower()] = _clip(text)
    return out


def ac_blocks(prd_text: str) -> dict[str, tuple[str, str]]:
    """`#### AC-…` 標題 → `(標題, 內文)`；內文到下一個標題為止。"""
    lines = prd_text.splitlines()
    out: dict[str, tuple[str, str]] = {}
    for index, line in enumerate(lines):
        match = _AC_HEAD_RE.match(line)
        if match:
            end = next((j for j in range(index + 1, len(lines)) if lines[j].startswith("#")),
                       len(lines))
            out[match.group(1)] = (match.group(2).strip(), "\n".join(lines[index + 1:end]))
    return out


def unit_status(covering: Sequence[Mapping[str, Any]]) -> str:
    if not covering:
        return "NONE"
    states = [str(t["status"]) for t in covering]
    if any(s in ("FAILED", "ESCALATED") for s in states):
        return "FAIL"
    return "PASS" if all(s == "COMPLETED" for s in states) else "NOT_RUN"


def e2e_status(decisions: Sequence[Mapping[str, Any]]) -> str:
    """僅當存在 SCG5 APPROVED 且其後（SCG4／5／6）無 REJECTED 才 PASS；否則 NOT_RUN。
    `decisions` 依決定時間由舊到新。"""
    last_ok = max((i for i, d in enumerate(decisions)
                   if d["gate"] == "SCG5" and d["decision"] == "APPROVED"), default=None)
    if last_ok is None:
        return "NOT_RUN"
    later = decisions[last_ok + 1:]
    return "NOT_RUN" if any(d["decision"] == "REJECTED" for d in later) else "PASS"


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def build_traceability(prd_text: str, *, decomposed: bool, tasks: Sequence[Mapping[str, Any]],
                       decisions: Sequence[Mapping[str, Any]], impl_key: str = ""
                       ) -> dict[str, Any]:
    """純函式。`decomposed` 為假（拆解缺席或 stale）時所有列 `unitStatus` 為 NONE。`tasks` 每筆
    `{task_id, status, completed_at, covers_ac[]}`。"""
    frozen = scr_mod.parse_frozen_prd(prd_text)
    prd = decompose_plan.parse_prd(prd_text)
    blocks = ac_blocks(prd_text)
    story_of = {ac: s for s in prd.stories for ac in s.acs}
    e2e = e2e_status(decisions)
    rows: list[dict[str, Any]] = []
    for ac in sorted(frozen.acs):
        covering = [t for t in tasks if decomposed and ac in (t.get("covers_ac") or [])]
        status = unit_status(covering)
        finished = [t["completed_at"] for t in covering if t.get("completed_at") is not None]
        story = story_of.get(ac)
        source = [f"task:{t['task_id']}" for t in covering]
        if covering:
            source.append(f"RTM-COVERAGE-{impl_key}.yaml")
        rows.append({
            "ac": ac, "userStory": f"{story.us_id} {story.title}".strip() if story else "",
            "gherkinSummary": gherkin_summary(blocks.get(ac, ("", ""))[1]),
            "unitStatus": status, "e2eStatus": e2e,
            "lastRunAt": _iso(max(finished)) if finished else None, "source": source})
    covered = sum(1 for r in rows if r["unitStatus"] == "PASS")
    return {"rows": rows, "totals": {"acTotal": len(rows), "covered": covered,
                                     "uncovered": len(rows) - covered,
                                     "frTotal": len(frozen.frs)}}


@dataclass(frozen=True)
class TraceContext:
    prd_text: str
    ref: decompose_plan.FrozenRef
    trace: dict[str, Any]


def _unmet(*names: str) -> ApiError:
    return ApiError(409, "fsm_state_conflict", details={"unmet": list(names)})


def load_trace(env: DeliveryEnv, row: Mapping[str, Any], impl_key: str = "") -> TraceContext:
    """讀凍結 PRD、拆解、任務與決定列後建追溯表；凍結 PRD 讀不到＝409 `unmet:[prd_not_frozen]`。"""
    rid = str(row["id"])
    ref = decompose_plan.frozen_prd(env.db, rid)
    if ref is None:
        raise _unmet("prd_not_frozen")
    try:
        text = layout.safe_join(Path(row["workspace_path"]), ref.rel).read_text(encoding="utf-8")
    except (OSError, ApiError):
        raise _unmet("prd_not_frozen") from None
    decomp = env.db.latest_decomposition(rid)
    decomposed = (decomp is not None and decomp["status"] == "SIGNED_OFF"
                  and not decompose_plan.is_stale(decomp, ref.sha256))
    console = row.get("console_project_id")
    tasks = env.db.list_task_states(console) if console else []
    return TraceContext(text, ref, build_traceability(
        text, decomposed=decomposed, tasks=tasks, decisions=env.db.list_gate_decisions(rid),
        impl_key=impl_key))


def rtm_summary(env: DeliveryEnv, run_id: str | None) -> dict[str, Any] | None:
    if env.rtm_report is None or not run_id:
        return None
    try:
        report = env.rtm_report(run_id)
    except ApiError:
        return None
    return {"runId": run_id, "fullyCovered": bool(report.get("fully_covered")),
            "acPct": (report.get("ac") or {}).get("pct"), "advisory": True}


def preview(env: DeliveryEnv, row: Mapping[str, Any], *, impl_key: str = "",
            run_id: str | None = None) -> dict[str, Any]:
    """`:traceability-preview`：零副作用（只讀）。"""
    ctx = load_trace(env, row, impl_key)
    return {"rows": ctx.trace["rows"], "totals": ctx.trace["totals"],
            "rtm": rtm_summary(env, run_id), "generatedAt": NOW().isoformat()}


def tag_unmet(state: str | None, trace: Mapping[str, Any]) -> list[str]:
    """`:tag` 的前置缺項（依序）：現態非 RELEASE_READY、追溯未全覆蓋（`scr_open` 由呼叫端另判）。"""
    unmet: list[str] = []
    if state != "RELEASE_READY":
        unmet.append("not_release_ready")
    if int(trace["totals"]["uncovered"]) > 0:
        unmet.append("rtm_below_100")
    return unmet


# ══ 事件與入庫 ═══════════════════════════════════════════════════════════════════════════════
def delivery_event(kind: str, status: str, *, ref: str | None, digest: str | None = None,
                   reason: str = "", failure_step: str | None = None) -> dict[str, Any]:
    """`research.delivery` 的固定六鍵；成功＝`ref` 非 null、`failure_step` null；失敗相反。"""
    if status == "CREATED":
        if ref is None or failure_step is not None:
            raise ValueError("成功事件須有 ref、不得有 failure_step")
    elif ref is not None or failure_step not in FAILURE_STEPS:
        raise ValueError("失敗事件 ref 須為 null、failure_step 須在四值內")
    return {"kind": kind, "ref": ref, "status": status, "digest": digest,
            "reason": reason[:300], "failure_step": failure_step}


def _record(env: DeliveryEnv, rid: str, *, actor: str, event: Mapping[str, Any],
            row: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"research_id": rid, "actor": actor[:100], "event": dict(event),
                               "event_ref": str(uuid.uuid4())}
    if row is not None:
        payload["row"] = dict(row)
    return env.writer.persist(Op("delivery.record", rid, payload))


def fail(env: DeliveryEnv, rid: str, kind: str, step: str, *, actor: str, reason: str,
         stderr_tail: str = "") -> ApiError:
    """發失敗事件（不寫列）並回 502 `delivery_step_failed`。"""
    _record(env, rid, actor=actor, event=delivery_event(
        kind, "FAILED", ref=None, reason=reason, failure_step=step))
    return ApiError(502, "delivery_step_failed", details={
        "failure_step": step, "stderr_tail": gitops.tail(healing.mask(stderr_tail), STDERR_TAIL)})


def _git_ok(result: gitops.GitResult) -> bool:
    return result.returncode == 0


def _origin(env: DeliveryEnv, cwd: Path) -> str:
    result = env.git.git(["remote", "get-url", "origin"], cwd=cwd)
    return result.stdout.strip() if _git_ok(result) else ""


# ══ Release Tag ══════════════════════════════════════════════════════════════════════════════
def snapshot_document(row: Mapping[str, Any], ctx: TraceContext, *, tag_name: str,
                      commit_sha: str, frozen_digests: Mapping[str, str]) -> str:
    """快照 JSON 文字（鍵序固定、`ensure_ascii=False`、LF 結尾）。"""
    doc = {"research_id": str(row["id"]), "rp_no": str(row["rp_no"]), "tag_name": tag_name,
           "commit_sha": commit_sha, "prd_sha256": ctx.ref.sha256,
           "frozen_digests": dict(frozen_digests), "generated_at": NOW().isoformat(),
           "rows": ctx.trace["rows"], "totals": ctx.trace["totals"]}
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def _resumable(ws: Path, tag_name: str, commit_sha: str) -> str | None:
    """前一次嘗試（tag 已建、推送失敗）留下的快照檔：記載同一 tag 與同一 commit 才算「我們的」，回其
    文字；否則 None（同名 tag 是別人的）。"""
    try:
        text = layout.safe_join(ws, TRACE_REL).read_text(encoding="utf-8")
        doc = json.loads(text)
    except (OSError, ValueError, ApiError):
        return None
    ok = isinstance(doc, dict) and doc.get("tag_name") == tag_name and doc.get(
        "commit_sha") == commit_sha
    return text if ok else None


def _remote_commit(listing: str, tag_name: str) -> str | None:
    """`ls-remote --tags` 輸出中該 tag 指向的 commit（附註 tag 取 `^{}` 行；輕量 tag 取本行）。"""
    plain = peeled = None
    for line in listing.splitlines():
        sha, _, ref = line.partition("\t")
        if ref == f"refs/tags/{tag_name}":
            plain = sha
        elif ref == f"refs/tags/{tag_name}^{{}}":
            peeled = sha
    return peeled or plain


def create_tag(env: DeliveryEnv, row: Mapping[str, Any], route: Mapping[str, Any], *,
               tag_name: str, message: str, push: bool, approver: str, fsm_state: str,
               rtm_run_id: str | None = None, trace: TraceContext | None = None
               ) -> dict[str, Any]:
    """步驟 1～7（零 FSM）。回 `{resumed, delivery, snapshot: {relPath, sha256}}`。"""
    rid, ws, cwd = str(row["id"]), Path(row["workspace_path"]), Path(route["target_path"])
    if not gitops.valid_semver(tag_name):
        raise unprocessable([{"field": "tagName", "rule": "not_semver",
                              "message": "tagName 須為 semver（至多 64 字）"}], "invalid_request")
    created = next((d for d in env.db.list_deliveries(rid)
                    if d["kind"] == "RELEASE_TAG" and d["ref"] == tag_name
                    and d["status"] == "CREATED"), None)
    if created is not None:                       # 續跑：列已存在，後續（FSM）由路由層補
        return {"resumed": True, "delivery": created, "snapshot": {
            "relPath": TRACE_REL, "sha256": str(created["snapshot_sha256"]).strip()}}
    ctx = trace or load_trace(env, row, str(route.get("impl_fsm_project") or ""))
    probe = env.git.git(["tag", "--list", tag_name], cwd=cwd)
    if not _git_ok(probe):
        raise fail(env, rid, "RELEASE_TAG", "tag", actor=approver, reason="tag --list 失敗",
                   stderr_tail=probe.stderr)
    exists = probe.stdout.strip() == tag_name
    head = env.git.git(["rev-parse", "--verify", "HEAD"], cwd=cwd)
    commit_sha = head.stdout.strip()
    if not _git_ok(head) or not _HEX40.fullmatch(commit_sha):
        raise fail(env, rid, "RELEASE_TAG", "tag", actor=approver, reason="取不到 HEAD commit",
                   stderr_tail=head.stderr)
    snapshot = _resumable(ws, tag_name, commit_sha) if exists else None
    if exists and snapshot is None:
        raise ApiError(409, "tag_exists", details={"tag": tag_name})
    if snapshot is None:
        snapshot = snapshot_document(row, ctx, tag_name=tag_name, commit_sha=commit_sha,
                                     frozen_digests=env.db.gate0_digests(rid) or {})
        fsutil.write_text_atomic(layout.safe_join(ws, TRACE_REL), snapshot)
    sha256 = layout.sha256_text(snapshot)
    if not exists:
        template = gitops.release_message(tag_name, str(row["rp_no"]), sha256[:12])
        made = env.git.git(["tag", "-a", tag_name, "-m", template], cwd=cwd)
        if not _git_ok(made):
            raise fail(env, rid, "RELEASE_TAG", "tag", actor=approver, reason="tag -a 失敗",
                       stderr_tail=made.stderr)
    if push and _origin(env, cwd):
        listing = env.git.git(["ls-remote", "--tags", "origin", tag_name], cwd=cwd)
        if not _git_ok(listing):
            raise fail(env, rid, "RELEASE_TAG", "push", actor=approver,
                       reason="ls-remote 失敗", stderr_tail=listing.stderr)
        remote = _remote_commit(listing.stdout, tag_name)
        if remote is not None and remote != commit_sha:
            raise unprocessable([{"field": "tagName", "rule": "remote_tag_diverged",
                                  "message": "遠端已有同名 tag 且指向不同 commit"}],
                                "invalid_request")
        if remote is None:
            pushed = env.git.git(["push", "origin", tag_name], cwd=cwd)
            if not _git_ok(pushed):
                raise fail(env, rid, "RELEASE_TAG", "push", actor=approver,
                           reason="push 失敗", stderr_tail=pushed.stderr)
    delivery_row = {
        "kind": "RELEASE_TAG", "ref": tag_name, "commit_sha": commit_sha, "url": None,
        "rtm_run_id": rtm_run_id, "rtm_report_ref": TRACE_REL, "snapshot_sha256": sha256,
        "fsm_state_after": fsm_state, "status": "CREATED",
        "detail": healing.mask(message)[:DETAIL_MAX], "created_by": approver}
    _record(env, rid, actor=approver, row=delivery_row, event=delivery_event(
        "RELEASE_TAG", "CREATED", ref=tag_name, digest=sha256))
    return {"resumed": False, "delivery": delivery_row,
            "snapshot": {"relPath": TRACE_REL, "sha256": sha256}}


# ══ Pull Request ═════════════════════════════════════════════════════════════════════════════
def pr_title(rp_no: str, title: str, fr: int, ac: int) -> str:
    return PR_TITLE_TEMPLATE.format(rp_no=rp_no, title=str(title)[:PR_TITLE_CHARS], fr=fr, ac=ac)


def clip_body(sections: Sequence[str], limit: int = PR_BODY_MAX) -> str:
    """段落以空行相接；超過上限時截於段落邊界（連第一段都放不下才硬切）。"""
    full = "\n\n".join(sections)
    if len(full) <= limit:
        return full
    kept: list[str] = []
    for section in sections:
        if len("\n\n".join([*kept, section])) > limit:
            break
        kept.append(section)
    return "\n\n".join(kept) if kept else full[:limit]


def pr_body(row: Mapping[str, Any], ctx: TraceContext) -> str:
    totals = ctx.trace["totals"]
    sections = [
        f"## 摘要\n- 研究專案：{row['rp_no']}（{row['id']}）\n- PRD：{ctx.ref.semver}"
        f"（sha256 {ctx.ref.sha256[:12]}）\n- 規模：{totals['frTotal']} FR／{totals['acTotal']} AC",
        f"## 追溯表摘要\n- AC 總數：{totals['acTotal']}；已覆蓋：{totals['covered']}；"
        f"未覆蓋：{totals['uncovered']}",
        f"## 規格依據\n- 凍結 PRD：{ctx.ref.rel}",
        "## 確認\n合併與雲端 CI 綠由人確認。"]
    return clip_body(sections)


def pr_request_violations(body: Mapping[str, Any], expected_title: str | None
                          ) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    if body.get("body_preview_ack") is not True:
        found.append({"field": "body_preview_ack", "rule": "preview_ack_required",
                      "message": "須勾選已預覽 PR 內文（body_preview_ack 為 true）"})
    title = body.get("title")
    if title is not None and expected_title is not None and title != expected_title:
        found.append({"field": "title", "rule": "title_not_template",
                      "message": "title 只作預覽，須等於模板輸出"})
    branch = body.get("branch")
    if branch is not None and not (isinstance(branch, str) and gitops.valid_ref(branch)):
        found.append({"field": "branch", "rule": "invalid_ref",
                      "message": "branch 不合 git ref 規則"})
    return found


def pr_missing(env: DeliveryEnv, route: Mapping[str, Any], cwd: Path) -> list[dict[str, str]]:
    """PR 前置缺項（依項名字母序）：`gh`、`gh_auth`、`origin`、`repo_writable`。"""
    missing: list[dict[str, str]] = []

    def add(item: str, why: str) -> None:
        missing.append({"item": item, "reason": why})

    if shutil.which("gh") is None:
        add("gh", "PATH 上找不到 gh")
    elif env.git.gh(["auth", "status"], cwd=cwd).returncode != 0:
        add("gh_auth", "gh 尚未登入")
    if not _origin(env, cwd):
        add("origin", "此倉沒有 origin 遠端")
    if route.get("track") == "A" and not settings_mod.repo_writable(env.cfg):
        add("repo_writable", "此部署無法寫入 monorepo（容器模式請改用本機模式）")
    return sorted(missing, key=lambda m: m["item"])


def _pr_number(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1][:200]


def create_pr(env: DeliveryEnv, row: Mapping[str, Any], route: Mapping[str, Any], *,
              branch: str | None, approver: str, fsm_state: str, ctx: TraceContext
              ) -> tuple[dict[str, Any], bool]:
    """回 `(交付列, created)`；已有 PR（DB 列或 `pr list` 非空）＝`created=False`。"""
    rid, cwd = str(row["id"]), Path(route["target_path"])
    existing = next((d for d in env.db.list_deliveries(rid) if d["kind"] == "PULL_REQUEST"), None)
    if existing is not None:
        return dict(existing), False
    head = branch or str(route.get("git_branch") or "")
    if not gitops.valid_ref(head):
        raise unprocessable([{"field": "branch", "rule": "invalid_ref",
                              "message": "branch 不合 git ref 規則"}], "invalid_request")
    listed = env.git.gh(["pr", "list", "--head", head, "--json", "url"], cwd=cwd)
    urls: list[str] = []
    if listed.returncode == 0:
        try:
            urls = [str(i["url"]) for i in json.loads(listed.stdout or "[]") if i.get("url")]
        except (ValueError, TypeError, KeyError):
            urls = []
    kind = "PULL_REQUEST"
    if not urls:
        pushed = env.git.git(["push", "-u", "origin", head], cwd=cwd)
        if pushed.returncode != 0:
            raise fail(env, rid, kind, "push", actor=approver, reason="push 失敗",
                       stderr_tail=pushed.stderr)
        base = str(route.get("base_ref") or "main")
        title = pr_title(str(row["rp_no"]), str(row["title"]), int(ctx.trace["totals"]["frTotal"]),
                         int(ctx.trace["totals"]["acTotal"]))
        made = env.git.gh(["pr", "create", "--title", gitops.redact(title), "--body",
                           gitops.redact(pr_body(row, ctx)), "--base", base, "--head", head],
                          cwd=cwd)
        if made.returncode != 0:
            raise fail(env, rid, kind, "pr_create", actor=approver, reason="gh pr create 失敗",
                       stderr_tail=made.stderr)
        urls = [made.stdout.strip().splitlines()[-1].strip()] if made.stdout.strip() else []
        created = True
    else:
        created = False
    if not urls:
        raise fail(env, rid, kind, "pr_create", actor=approver, reason="gh 未回 PR URL")
    url = urls[0][:500]
    delivery_row = {"kind": kind, "ref": _pr_number(url), "commit_sha": None, "url": url,
                    "rtm_run_id": None, "rtm_report_ref": None, "snapshot_sha256": None,
                    "fsm_state_after": fsm_state, "status": "CREATED", "detail": "",
                    "created_by": approver}
    _record(env, rid, actor=approver, row=delivery_row, event=delivery_event(
        kind, "CREATED", ref=delivery_row["ref"]))
    return delivery_row, created
