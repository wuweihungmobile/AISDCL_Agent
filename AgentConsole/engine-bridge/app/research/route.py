"""分流（ADR-003 D5、D8、D14～D16；API 契約 §2.2；TCS AC-961-2～5、7）：預演與執行共用同一份計畫。

結構（由下而上）：
  · 常數與驗證：`validate_request`（純函式；全部違規一次列出）、`PLACEMENT_TARGETS`、
    `RouteRequest`；
  · 計畫：`build_plan`（純函式；軌道 A 七步、B 八步〔含選用的 `GH_REPO_CREATE`〕；SKIPPED
    步驟不產生列）——預演回傳它、執行逐項照做，**步驟序只有這一份**（AT-961-3-E-1）；
  · 預演：零副作用（不寫任何表、不建任何目錄、不 spawn 寫入型 git；`create_github` 時只起
    唯讀的 `gh auth status`；組裝在 `routers/research_route.py`）；
  · 執行：`execute`（逐步先寫 `RUNNING` 列、副作用做完再改 `OK`／`FAILED`；任一步失敗即停、
    後續步驟不產生列；全部成功才寫 `02_governance/route_decision.json` 與 artifact 並把游標推到
    `build／ROUTED`）、`reap_route_orphans`（Bridge 重啟時把卡在進行中的分流列標 `FAILED`）。

DB 先於副作用（W-P2）：所有寫入走 `DurableWriter.persist(Op(…))`（檔→outbox→DB 交易→標完成）；
git／gh 只經 `gitops.Gitops`；FSM 只經 `adopt`（→`fsm_ops`→`sdd_cli`）。失敗**不補償到破壞態**：
Bridge 不 `git clean`／`stash`／刪目錄／刪分支，已建的 worktree 與分支原地保留（AC-11-8），
補償只由 console-api 標專案列後呼叫 `:route-compensated`。

重試（同一 `route_id`；IFACE §4.4）：輸入雜湊相等才續跑；已 `OK` 的步驟不重做；`FAILED` 的步驟沿用
同一列重跑。雜湊記在 `VALIDATE_TARGET` 步驟列的 `argv_redacted`（`inputs_sha256=<hex>`）——因為失敗時
`route_decision.json` 尚不存在（成功才寫）。
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from autoclaude.utils.shell_deny_chars import BASE_DENY_CHARS

from .. import sdd_cli
from ..errors import ApiError
from ..security import is_within
from ..settings import Settings, discover_sdd_root
from . import adopt, gitops, layout, scaffold
from .db import ROUTE_STEP_NAMES, ResearchDb
from .gitops import (  # noqa: F401 — 轉出供測試取單一來源常數
    BRANCH_PATTERN,
    OWNER_PATTERN,
    REPO_NAME_PATTERN,
    GitopsDenied,
)
from .orchestrator import BASELINE_REL
from .outbox import DurableWriter, FileRef, FileWrite, Op
from .scaffold import TEMPLATE_VAR_PATTERN, ScaffoldError  # noqa: F401
from .settings import repo_writable

# ── 值域常數（TCS §5.1；測試與產品碼共用）──────────────────────────────────────────────────────
TRACKS = ("A", "B")
PROJECT_NAME_PATTERN = r"^[a-z][a-z0-9-]{1,61}$"
INNER_KEY_PATTERN = r"^[a-z][a-z0-9-]{1,99}$"
SCOPE_REASON_MAX = 200
SCR_REASON_MAX = 500
WAIVER_REASON_MAX = 500
COMPENSATE_REASON_MAX = 500
DEFAULT_BASE_REF = "main"
DEFAULT_TEMPLATE_VISIBILITY = "PRIVATE"
ROUTE_DECISION_REL = "02_governance/route_decision.json"
#: 分流的四個結果欄位於 R7 JSON 的根鍵（對帳規則見交卷：比對 `inputs_sha256`、`plan` 步驟名序列與
#: `results.published_docs` 的 sha256）。
ROUTE_DECISION_KEYS = ("route_id", "research_id", "track", "request", "inputs_sha256", "plan",
                       "steps", "results", "decided_by", "decided_at", "overridden_default")
#: 「消毒類」違規規則（對外 reason 為 `sanitization_failed`）；其餘為 `invalid_request`。
SANITIZATION_RULES = frozenset({"deny_chars", "path_traversal", "path_separator", "git_ref",
                                "retired_field"})
_PROJECT_RE = re.compile(PROJECT_NAME_PATTERN)
_INNER_KEY_RE = re.compile(INNER_KEY_PATTERN)
_REPO_RE = re.compile(REPO_NAME_PATTERN)
_OWNER_RE = re.compile(OWNER_PATTERN)
_BRANCH_RE = re.compile(BRANCH_PATTERN)
_INPUT_HASH_RE = re.compile(r"inputs_sha256=([0-9a-f]{64})")
#: 場景欄位順序（`violations[]` 依此排序；契約 §1.2 的請求欄位序）。
FIELD_ORDER = ("track", "target_module", "branch_name", "base_ref", "project_name",
               "stack_template", "repo_name", "owner", "visibility", "confirm_repo_name",
               "create_github", "ci", "docker_compose", "scope_differs_reason", "target_path")
_SCOPE_FOR_TRACK = {"A": "AISDLC_MODULE", "B": "STANDALONE_PROJECT"}
#: 步驟序（軌道 A／B；V19 十一個步驟名的兩個子序列；`GH_REPO_CREATE` 只在 B 且 `create_github`）。
TRACK_A_STEPS = ("VALIDATE_TARGET", "GIT_SWITCH", "PUBLISH_DOCS", "REGISTER_STUB", "GIT_COMMIT",
                 "IMPL_KEY_INIT", "BASELINE_ADOPT")
TRACK_B_STEPS = ("VALIDATE_TARGET", "SCAFFOLD_FILES", "COPY_WORKSPACE", "GIT_INIT", "GIT_COMMIT",
                 "GH_REPO_CREATE", "IMPL_KEY_INIT", "BASELINE_ADOPT")
assert set(TRACK_A_STEPS) | set(TRACK_B_STEPS) | {"REGISTER_STUB"} <= set(ROUTE_STEP_NAMES)

#: 牆鐘（測試以 monkeypatch 換成假時鐘；D-105）與步驟鉤子（測試在副作用前後注入中斷或故障）。
CLOCK: Callable[[], float] = time.monotonic
STEP_HOOK: Callable[[str, str], None] | None = None


@dataclass(frozen=True)
class Placement:
    """落點目標（D-100：P1 固定四值；擴充＝改 SSOT 與 V19 CHECK〔V20〕）。"""

    module: str
    rule_source: str        # 一句出處（`Root_Layout_and_Module_Placement.md` §2）
    subdir: str             # 相對 monorepo 根；"." 表根；`AISDLC_SDD` 另加 LATEST 版本目錄


_SSOT = "docs/02_architecture/Root_Layout_and_Module_Placement.md"
PLACEMENT_TARGETS: dict[str, Placement] = {
    "autoclaude": Placement(
        "autoclaude", f"AutoClaude 的 plugin 與引擎模組落 AutoClaude/，走該專案的新增 Plugin SOP"
                      f"（{_SSOT} §2）", "AutoClaude"),
    "agentconsole": Placement(
        "agentconsole", f"AgentConsole 的 UI、console-api 與 engine-bridge 模組落 AgentConsole/，"
                        f"子專案內的模組不往根層放（{_SSOT} §2）", "AgentConsole"),
    "sdd": Placement(
        "sdd", f"AISDLC_SDD 的流程、agent 與模板資產只改 LATEST 版本目錄，走該框架的目錄規則"
               f"（{_SSOT} §2）", "AISDLC_SDD"),
    "monorepo": Placement(
        "monorepo", f"只有跨專案治理工具才落根層（tools/lib/<module>/、docs/06_quality/"
                    f"<Module>_Protocol/ 等；{_SSOT} §2）", "."),
}
_PLACEMENT_KEYWORDS = (("AgentConsole", "agentconsole"), ("AutoClaude", "autoclaude"),
                       ("AISDLC_SDD", "sdd"), ("monorepo", "monorepo"), ("根層", "monorepo"))


class RouteViolation(Exception):
    """請求不合規：`violations` 逐筆 `{field, rule, message}`；`reason` 為對外錯誤碼。"""

    def __init__(self, violations: list[dict[str, str]]) -> None:
        super().__init__(f"{len(violations)} violations")
        self.violations = violations
        self.reason = violation_reason(violations)


def violation_reason(violations: Sequence[Mapping[str, str]]) -> str:
    rules = {v["rule"] for v in violations}
    if rules & SANITIZATION_RULES:
        return "sanitization_failed"
    if rules == {"public_confirmation_required"}:
        return "public_confirmation_required"
    return "invalid_request"


@dataclass(frozen=True)
class RouteCaps:
    """驗證與計畫需要的部署事實快照（純資料，所以兩者是純函式）。"""

    templates: tuple[str, ...]
    worktree_root: Path
    scaffold_root: Path | None
    repo_root: Path
    rp_no: str                      # `RP-0007`
    slug: str
    sdd_subdir: str | None = None   # `AISDLC_SDD/AISDLC_SDD_v0.30`（目標模組 sdd 才用到）


@dataclass(frozen=True)
class RouteRequest:
    track: str
    target_module: str | None
    branch_name: str | None
    base_ref: str | None
    project_name: str | None
    stack_template: str | None
    repo_name: str | None
    owner: str | None
    visibility: str
    confirm_repo_name: str | None
    create_github: bool
    ci: bool
    docker_compose: bool
    scope_differs_reason: str | None
    console_project_id: str | None = None
    overridden_default: bool = False

    def canonical(self) -> dict[str, Any]:
        """輸入雜湊的來源（不含 approver、token、retry；那些不是「分流的輸入」）。"""
        return {k: getattr(self, k) for k in (
            "track", "target_module", "branch_name", "base_ref", "project_name", "stack_template",
            "repo_name", "owner", "visibility", "confirm_repo_name", "create_github", "ci",
            "docker_compose", "scope_differs_reason", "console_project_id")}

    def inputs_sha256(self) -> str:
        text = json.dumps(self.canonical(), ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── 落點與預設 ─────────────────────────────────────────────────────────────────────────────
def default_target_module(workspace: Path) -> str | None:
    """PRD「模組落點表」解析出的預設落點目標（取表內最先出現的已知模組名）；找不到＝None。"""
    prd = workspace / BASELINE_REL
    try:
        lines = prd.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    table: list[str] = []
    inside = False
    for line in lines:
        if line.lstrip().startswith("#"):
            inside = "模組落點表" in line
            continue
        if inside or "模組落點表" in line:
            table.append(line)
    text = "\n".join(table)
    hits = [(text.find(word), module) for word, module in _PLACEMENT_KEYWORDS if word in text]
    return min(hits)[1] if hits else None


def placement_list(default: str | None) -> list[dict[str, Any]]:
    return [{"module": p.module, "rule_source": p.rule_source, "default": p.module == default}
            for p in PLACEMENT_TARGETS.values()]


def subproject_rel(module: str, caps: RouteCaps) -> str:
    """目標子專案根（相對 monorepo／worktree 根的 POSIX 路徑；`.`＝根）。"""
    base = PLACEMENT_TARGETS[module].subdir
    if module == "sdd":
        return caps.sdd_subdir or base
    return base


def sdd_subdir_of(repo_root: Path) -> str | None:
    found = discover_sdd_root(repo_root / "AISDLC_SDD")
    return None if found is None else f"AISDLC_SDD/{found.name}"


# ── 驗證（純函式）──────────────────────────────────────────────────────────────────────────
def _v(field_name: str, rule: str, message: str) -> dict[str, str]:
    return {"field": field_name, "rule": rule, "message": message}


def _text_problems(name: str, value: str, *, separators: bool) -> list[dict[str, str]]:
    out = []
    bad = sorted(set(value) & BASE_DENY_CHARS)
    if bad:
        out.append(_v(name, "deny_chars", f"{name} 含不允許的字元"))
    if ".." in value:
        out.append(_v(name, "path_traversal", f"{name} 不得含 .."))
    if separators and ("/" in value or "\\" in value):
        out.append(_v(name, "path_separator", f"{name} 不得含路徑分隔符"))
    return out


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def validate_request(body: Mapping[str, Any], caps: RouteCaps,
                     research: Mapping[str, Any]) -> list[dict[str, str]]:
    """分流請求的欄位驗證（預演與確認共用的**唯一**驗證函式）；回違規清單（空＝合格），依
    `FIELD_ORDER` 排序、每個違規一筆。`research` 取 `target_scope`、`default_target_module`。"""
    found: dict[str, list[dict[str, str]]] = {name: [] for name in FIELD_ORDER}
    track = body.get("track")
    if track is None:
        found["track"].append(_v("track", "required", "track 必填（A 或 B）"))
    elif track not in TRACKS:
        found["track"].append(_v("track", "invalid_track", "track 只准 A 或 B"))
    if "target_path" in body:
        found["target_path"].append(_v("target_path", "retired_field",
                                       "target_path 已退役：路徑由 Bridge 導出（D-106）"))
    if track == "A":
        _validate_a(body, found, research)
    elif track == "B":
        _validate_b(body, caps, found)
    visibility = body.get("visibility", DEFAULT_TEMPLATE_VISIBILITY)
    if visibility not in gitops.VISIBILITIES:
        found["visibility"].append(_v("visibility", "invalid_visibility",
                                      "visibility 只准 PRIVATE 或 PUBLIC"))
    elif visibility == "PUBLIC" and track == "A":
        found["visibility"].append(_v("visibility", "public_requires_track_b",
                                      "軌道 A 不接受 PUBLIC"))
    for flag in ("create_github", "ci", "docker_compose"):
        if flag in body and not _is_bool(body[flag]):
            found[flag].append(_v(flag, "invalid_type", f"{flag} 須為布林"))
    _validate_scope_reason(body, track, found, research)
    return [v for name in FIELD_ORDER for v in found[name]]


def _validate_a(body: Mapping[str, Any], found: dict[str, list[dict[str, str]]],
                research: Mapping[str, Any]) -> None:
    module = body.get("target_module", research.get("default_target_module"))
    if module is None:
        found["target_module"].append(_v("target_module", "required", "target_module 必填"))
    elif not isinstance(module, str) or module not in PLACEMENT_TARGETS:
        found["target_module"].append(_v("target_module", "unknown_target_module",
                                         "target_module 只准落點目標清單內的值"))
    branch = body.get("branch_name")
    if branch is not None:
        if not isinstance(branch, str) or not _BRANCH_RE.fullmatch(branch):
            found["branch_name"].append(_v("branch_name", "branch_name_pattern",
                                           "branch_name 須符合 ^feature/[a-z0-9-]{1,40}$"))
        if isinstance(branch, str):
            found["branch_name"] += _text_problems("branch_name", branch, separators=False)
            if not gitops.valid_ref(branch):
                found["branch_name"].append(_v("branch_name", "git_ref", "不合 git ref 規則"))
    base = body.get("base_ref")
    if base is not None:
        if not isinstance(base, str) or not gitops.valid_ref(base):
            found["base_ref"].append(_v("base_ref", "git_ref", "base_ref 不合 git ref 規則"))
        if isinstance(base, str):
            found["base_ref"] += _text_problems("base_ref", base, separators=False)


def _validate_b(body: Mapping[str, Any], caps: RouteCaps,
                found: dict[str, list[dict[str, str]]]) -> None:
    name = body.get("project_name")
    if name is None:
        found["project_name"].append(_v("project_name", "required", "project_name 必填"))
    elif not isinstance(name, str) or not _PROJECT_RE.fullmatch(name):
        found["project_name"].append(_v("project_name", "project_name_pattern",
                                        "project_name 須符合 ^[a-z][a-z0-9-]{1,61}$"))
    if isinstance(name, str):
        found["project_name"] += _text_problems("project_name", name, separators=True)
        if sdd_cli.is_outer_key(name):
            found["project_name"].append(_v("project_name", "reserved_prefix",
                                            "project_name 不得是外環鍵形態（research-…）"))
    template = body.get("stack_template")
    if not isinstance(template, str) or template not in caps.templates:
        found["stack_template"].append(_v("stack_template", "unknown_template",
                                          "stack_template 不在登記的範本清單"))
    if isinstance(template, str):
        found["stack_template"] += _text_problems("stack_template", template, separators=True)
    repo = body.get("repo_name", name if isinstance(name, str) else None)
    if "repo_name" in body and (not isinstance(repo, str) or not _REPO_RE.fullmatch(repo)):
        found["repo_name"].append(_v("repo_name", "repo_name_pattern",
                                     "repo_name 須符合 ^[a-z][a-z0-9-]{1,38}$"))
    elif ("repo_name" not in body and isinstance(repo, str) and _PROJECT_RE.fullmatch(repo)
          and not _REPO_RE.fullmatch(repo)):
        found["repo_name"].append(_v("repo_name", "repo_name_pattern",
                                     "預設的 repo_name（取 project_name）超出 2～39 字元"))
    if isinstance(body.get("repo_name"), str):
        found["repo_name"] += _text_problems("repo_name", body["repo_name"], separators=True)
    owner = body.get("owner")
    if owner is None:
        if body.get("create_github") is True:
            found["owner"].append(_v("owner", "required", "建立 GitHub 遠端時 owner 必填"))
    else:
        if not isinstance(owner, str) or not _OWNER_RE.fullmatch(owner):
            found["owner"].append(_v("owner", "owner_pattern",
                                     "owner 須符合 ^[A-Za-z0-9][A-Za-z0-9-]{0,38}$"))
        if isinstance(owner, str):
            found["owner"] += _text_problems("owner", owner, separators=True)
    if body.get("visibility") == "PUBLIC":
        confirm = body.get("confirm_repo_name")
        if confirm != repo:
            found["confirm_repo_name"].append(_v(
                "confirm_repo_name", "public_confirmation_required",
                "PUBLIC 須輸入與 repo_name 完全相同的庫名確認"))


def _validate_scope_reason(body: Mapping[str, Any], track: Any,
                           found: dict[str, list[dict[str, str]]],
                           research: Mapping[str, Any]) -> None:
    expected = research.get("target_scope")
    differs = track in TRACKS and expected in _SCOPE_FOR_TRACK.values() and (
        _SCOPE_FOR_TRACK[track] != expected)
    reason = body.get("scope_differs_reason")
    if reason is not None and not isinstance(reason, str):
        found["scope_differs_reason"].append(_v("scope_differs_reason", "invalid_type",
                                                "scope_differs_reason 須為字串"))
        return
    text = (reason or "").strip()
    if differs and not text:
        found["scope_differs_reason"].append(_v(
            "scope_differs_reason", "scope_differs_reason_required",
            "分流與 PRD 的 target_scope 不同，須填 1～200 字理由"))
    elif reason is not None and len(reason) > SCOPE_REASON_MAX:
        found["scope_differs_reason"].append(_v(
            "scope_differs_reason", "scope_differs_reason_max",
            f"scope_differs_reason 至多 {SCOPE_REASON_MAX} 字"))


def scope_differs(track: str, research: Mapping[str, Any]) -> bool:
    expected = research.get("target_scope")
    return expected in _SCOPE_FOR_TRACK.values() and _SCOPE_FOR_TRACK[track] != expected


def normalize_request(body: Mapping[str, Any], caps: RouteCaps,
                      research: Mapping[str, Any]) -> RouteRequest:
    """驗證通過後的正規化（預設值補齊）；驗證不過拋 `RouteViolation`。"""
    violations = validate_request(body, caps, research)
    if violations:
        raise RouteViolation(violations)
    track = body["track"]
    if track == "A":
        default = research.get("default_target_module")
        module = body.get("target_module", default)
        number = caps.rp_no.removeprefix("RP-")
        return RouteRequest(
            track="A", target_module=module,
            branch_name=body.get("branch_name") or f"feature/issue-{number}",
            base_ref=body.get("base_ref") or DEFAULT_BASE_REF, project_name=None,
            stack_template=None, repo_name=None, owner=None, visibility="PRIVATE",
            confirm_repo_name=None, create_github=False, ci=False, docker_compose=False,
            scope_differs_reason=(body.get("scope_differs_reason") or None),
            console_project_id=body.get("console_project_id"),
            overridden_default=bool(default is not None and module != default))
    return RouteRequest(
        track="B", target_module=None, branch_name=None, base_ref=None,
        project_name=body["project_name"], stack_template=body["stack_template"],
        repo_name=body.get("repo_name") or body["project_name"], owner=body.get("owner"),
        visibility=body.get("visibility", DEFAULT_TEMPLATE_VISIBILITY),
        confirm_repo_name=body.get("confirm_repo_name"),
        create_github=bool(body.get("create_github", False)), ci=bool(body.get("ci", True)),
        docker_compose=bool(body.get("docker_compose", True)),
        scope_differs_reason=(body.get("scope_differs_reason") or None),
        console_project_id=body.get("console_project_id"))


# ── 推導路徑與計畫 ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Derived:
    """由請求與部署事實推導出的路徑與鍵（預演與執行共用）。"""

    execution_path: Path            # A：worktree 內的目標子專案根；B：新專案根
    state_dir: Path                 # 內環鍵的狀態目錄（`<execution_path>/build/reports/fsm`）
    impl_key: str
    worktree: Path | None           # A
    sub_rel: str | None             # A：子專案根相對 worktree 的路徑
    prd_rel: str | None             # A：發佈的 PRD（相對 execution_path）
    stub_rel: str | None            # A：落點 stub（相對 execution_path）
    new_root: Path | None           # B
    adopt_prd_rel: str              # 採納用的 PRD（相對 execution_path；POSIX）


def derive(req: RouteRequest, caps: RouteCaps) -> Derived:
    if req.track == "A":
        assert req.target_module and req.branch_name
        sub = subproject_rel(req.target_module, caps)
        tail = req.branch_name.removeprefix("feature/")
        worktree = caps.worktree_root / f"{caps.rp_no.lower()}-{tail}"
        exec_path = worktree if sub == "." else worktree.joinpath(*sub.split("/"))
        key = f"{req.target_module}-{caps.slug}"
        prd_rel = f"docs/01_requirements/{caps.slug}_PRD.md"
        stub_rel = f"docs/02_architecture/Module_Placement_Stub_{caps.slug}.md"
        return Derived(exec_path, exec_path / "build" / "reports" / "fsm", key, worktree, sub,
                       prd_rel, stub_rel, None, prd_rel)
    assert caps.scaffold_root is not None and req.project_name
    root = caps.scaffold_root / req.project_name
    return Derived(root, root / "build" / "reports" / "fsm", req.project_name, None, None, None,
                   None, root, f"{scaffold.WORKSPACE_COPY_ROOT}/{caps.slug}/{BASELINE_REL}")


def _action(seq: int, action: str, step: str, target: str, detail: str, *,
            external: bool = False) -> dict[str, Any]:
    return {"seq": seq, "action": action, "step": step, "target": target,
            "touches_external": external, "detail": detail}


def build_plan(req: RouteRequest, caps: RouteCaps) -> list[dict[str, Any]]:
    """動作清單（純函式）。預演原樣回傳、執行逐項照做；元素形狀見 IFACE §4.1。"""
    d = derive(req, caps)
    if req.track == "A":
        assert req.branch_name and req.base_ref and d.worktree and d.prd_rel and d.stub_rel
        steps = [
            ("validate_target", "VALIDATE_TARGET", req.target_module or "",
             f"驗證輸入與落點目標；分支 {req.branch_name} 尚不存在"),
            ("worktree_add", "GIT_SWITCH", f"{req.branch_name} @ {req.base_ref} → {d.worktree}",
             "在獨立 worktree 建立 feature 分支（主工作樹零擾動）"),
            ("publish_prd", "PUBLISH_DOCS", d.prd_rel,
             "把凍結的 PRD 複本（位元組相同）發佈到目標模組 docs/"),
            ("register_stub", "REGISTER_STUB", d.stub_rel, "寫落點提示 stub（不碰落點 SSOT）"),
            ("git_commit", "GIT_COMMIT", f"add -- {d.prd_rel} {d.stub_rel}; commit",
             "只 add 明列的兩個路徑並 commit（繁體中文訊息）"),
            ("impl_key_init", "IMPL_KEY_INIT", d.impl_key, "在目標根建立內環 FSM 鍵"),
            ("baseline_adopt", "BASELINE_ADOPT", d.impl_key,
             "採納基線：五次 transition 並凍結 Stage-1")]
        return [_action(i, *s) for i, s in enumerate(steps, 1)]
    plan = [
        ("validate_target", "VALIDATE_TARGET", str(d.execution_path),
         "驗證輸入、範本與目標目錄", False),
        ("expand_template", "SCAFFOLD_FILES", str(d.execution_path),
         f"以範本 {req.stack_template} 確定性展開專案骨架（含 CI 與 compose 選項）", False),
        ("copy_workspace", "COPY_WORKSPACE",
         f"{d.execution_path}/{scaffold.WORKSPACE_COPY_ROOT}/{caps.slug}",
         "複製研究工作區並逐檔 sha256 驗證", False),
        ("git_init", "GIT_INIT", str(d.execution_path), "git init -b main", False),
        ("git_commit", "GIT_COMMIT", str(d.execution_path),
         "add -A（受 .gitignore）並 commit 初始版本", False)]
    if req.create_github:
        plan.append(("gh_repo_create", "GH_REPO_CREATE", f"{req.owner}/{req.repo_name}",
                     f"gh repo create（{req.visibility}）：新增 remote origin 並推送", True))
    plan += [("impl_key_init", "IMPL_KEY_INIT", d.impl_key, "在新專案根建立內環 FSM 鍵", False),
             ("baseline_adopt", "BASELINE_ADOPT", d.impl_key,
              "採納基線：五次 transition 並凍結 Stage-1", False)]
    return [_action(i, a, s, t, detail, external=ext)
            for i, (a, s, t, detail, ext) in enumerate(plan, 1)]


def plan_steps(req: RouteRequest, caps: RouteCaps) -> list[str]:
    return [item["step"] for item in build_plan(req, caps)]


def warnings_for(req: RouteRequest) -> list[dict[str, str]]:
    out = []
    if req.track == "B" and req.visibility == "PUBLIC":
        out.append({"code": "public_repo_warning", "message": "PRD 與證據矩陣將公開"})
    return out


def expected_tracked(req: RouteRequest, caps: RouteCaps, workspace: Path) -> list[str]:
    """軌道 B 初始 commit 預期追蹤的檔案（預演的 `expected_tracked_files`；與 `ls-files` 對拍）。"""
    assert req.track == "B" and req.project_name and req.stack_template
    variables = template_variables(req, caps)
    tpl = [p.rel for p in scaffold.plan_files(req.stack_template, variables, ci=req.ci,
                                              docker_compose=req.docker_compose)]
    return scaffold.tracked_files(tpl, caps.slug, scaffold.workspace_files(workspace))


def template_variables(req: RouteRequest, caps: RouteCaps) -> dict[str, str]:
    return {"project_name": req.project_name or "", "slug": caps.slug,
            "repo_name": req.repo_name or req.project_name or "", "owner": req.owner or "owner"}


# ── 部署支援檢查（預演與確認共用；零副作用）───────────────────────────────────────────────────
def _root_problem(root: Path, allowed: Sequence[Path]) -> str | None:
    resolved = root.resolve()
    if not any(is_within(resolved, a) for a in allowed):
        return "根目錄解析後不在 BRIDGE_ALLOWED_PATH_ROOTS 之下"
    return None


def _existing_dir(*candidates: Path | None) -> Path:
    return next((p for p in candidates if p is not None and p.is_dir()), Path.cwd())


def deployment_missing(cfg: Settings, req: RouteRequest, git: gitops.Gitops,
                       caps: RouteCaps) -> list[dict[str, str]]:
    """不支援的部署缺項（依項名字母序；`item` 見 TCS §5.1 預演缺項）。"""
    missing: list[dict[str, str]] = []

    def add(item: str, reason: str) -> None:
        missing.append({"item": item, "reason": reason})

    if shutil.which("git") is None:
        add("git", "PATH 上找不到 git")
    if req.track == "A":
        if not repo_writable(cfg):
            add("repo_writable", "此部署無法寫入 monorepo（容器模式請改用本機模式）")
        problem = _root_problem(cfg.worktree_root, cfg.allowed_path_roots)
        if problem:
            add("worktree_root", problem)
    else:
        if cfg.research_scaffold_root is None:
            add("scaffold_root", "未設定 BRIDGE_SCAFFOLD_ROOT：軌道 B 停用")
        else:
            problem = _root_problem(cfg.research_scaffold_root, cfg.allowed_path_roots)
            if problem:
                add("scaffold_root", problem)
            elif not caps.templates:
                add("scaffold_templates", "範本目錄為空")
        if req.create_github:
            if shutil.which("gh") is None:
                add("gh", "PATH 上找不到 gh")
            else:
                probe = git.gh(["auth", "status"],
                               cwd=_existing_dir(cfg.research_scaffold_root, cfg.research_root))
                if probe.returncode != 0:
                    add("gh_auth", "gh 尚未登入（gh auth status 非 0）")
    return sorted(missing, key=lambda m: m["item"])


# ── 步驟執行 ───────────────────────────────────────────────────────────────────────────────
class StepFailed(Exception):
    """某步驟失敗：`cause` 是人可讀的原因碼（進 `stderr_tail`）；`exit_code` 為結束碼或 None。"""

    def __init__(self, cause: str, *, exit_code: int | None = None, stdout: str = "",
                 stderr: str = "", argv: str = "") -> None:
        super().__init__(cause)
        self.cause = cause
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.argv = argv


@dataclass
class StepOutcome:
    argv: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""


@dataclass
class RouteRun:
    """一次分流的執行脈絡。"""

    cfg: Settings
    db: ResearchDb
    writer: DurableWriter
    git: gitops.Gitops
    req: RouteRequest
    caps: RouteCaps
    project: Mapping[str, Any]
    route_id: str
    approver: str
    audit: Any = None
    results: dict[str, Any] = field(default_factory=dict)

    @property
    def rid(self) -> str:
        return str(self.project["id"])

    @property
    def workspace(self) -> Path:
        return Path(self.project["workspace_path"])

    @property
    def derived(self) -> Derived:
        return derive(self.req, self.caps)


def _git(run: RouteRun, tokens: Sequence[str], cwd: Path) -> gitops.GitResult:
    return run.git.git(tokens, cwd=cwd)


def _check_git(result: gitops.GitResult, cause: str) -> gitops.GitResult:
    if result.returncode != 0:
        raise StepFailed(cause, exit_code=result.returncode, stdout=result.stdout,
                         stderr=result.stderr, argv=result.argv_redacted)
    return result


def _outcome(result: gitops.GitResult) -> StepOutcome:
    return StepOutcome(result.argv_redacted, result.returncode, result.stdout, result.stderr)


def _prd_digest(run: RouteRun) -> str:
    digests = run.db.gate0_digests(run.rid) or {}
    sha = digests.get(BASELINE_REL)
    if not sha:
        raise StepFailed("gate0_digest_missing", stderr="找不到 Gate 0 凍結的 PRD 摘要")
    return sha


def _step_validate(run: RouteRun) -> StepOutcome:
    note = f"validate_target inputs_sha256={run.req.inputs_sha256()}"
    if run.req.track == "A":
        result = _check_git(_git(run, ["rev-parse", "--show-toplevel"], run.cfg.repo_root),
                            "not_a_git_repository")
        return StepOutcome(f"{note}; {result.argv_redacted}", result.returncode)
    return StepOutcome(note)


def _step_git_switch(run: RouteRun) -> StepOutcome:
    d, req = run.derived, run.req
    assert d.worktree and req.branch_name and req.base_ref
    root = run.cfg.repo_root
    listed = _git(run, ["branch", "--list", req.branch_name], root)
    attached = _git(run, ["worktree", "list", "--porcelain"], root)
    if (listed.returncode == 0 and listed.stdout.strip() and attached.returncode == 0
            and f"refs/heads/{req.branch_name}" in attached.stdout
            and d.worktree.name in attached.stdout.replace("\\", "/")):
        return StepOutcome("worktree_add (already exists)", 0, "already_exists", "")
    d.worktree.parent.mkdir(parents=True, exist_ok=True)
    result = _check_git(_git(run, ["-c", "core.longpaths=true", "worktree", "add", "-b",
                                   req.branch_name, str(d.worktree), req.base_ref], root),
                        "worktree_add_failed")
    return _outcome(result)


def _step_publish(run: RouteRun) -> StepOutcome:
    d = run.derived
    assert d.prd_rel
    sha = _prd_digest(run)
    source = layout.safe_join(run.workspace, BASELINE_REL)
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        raise StepFailed("prd_digest_mismatch", stderr="工作區 PRD 與 Gate 0 凍結摘要不符")
    from .. import fsutil

    target = d.execution_path / d.prd_rel
    fsutil.write_text_atomic(target, data.decode("utf-8"))
    if hashlib.sha256(target.read_bytes()).hexdigest() != sha:
        raise StepFailed("prd_publish_mismatch", stderr="發佈後的 PRD 位元組與凍結摘要不符")
    run.results.setdefault("published_docs", {})[d.prd_rel] = sha
    return StepOutcome(f"publish_prd {d.prd_rel}", None, f"sha256={sha}")


def stub_text(run: RouteRun, sha: str) -> str:
    module = run.req.target_module or ""
    return (
        f"<!-- 由 ResearchToPRD 產生，非落點 SSOT -->\n"
        f"# 模組落點提示：{run.caps.slug}\n\n"
        f"> 由 ResearchToPRD 產生，非落點 SSOT；本檔只是提示，沒有編修任何落點規範。\n\n"
        f"- 研究專案 id：{run.rid}（{run.caps.rp_no}）\n"
        f"- PRD sha256：{sha}\n"
        f"- 模組名：{module}\n\n"
        f"請依 Root_Layout §2、§3 手動登記。\n")


def _step_stub(run: RouteRun) -> StepOutcome:
    from .. import fsutil

    d = run.derived
    assert d.stub_rel
    text = stub_text(run, _prd_digest(run))
    fsutil.write_text_atomic(d.execution_path / d.stub_rel, text)
    run.results.setdefault("published_docs", {})[d.stub_rel] = layout.sha256_text(text)
    return StepOutcome(f"register_stub {d.stub_rel}", None, "")


def _step_commit_a(run: RouteRun) -> StepOutcome:
    d = run.derived
    assert d.worktree and d.sub_rel and d.prd_rel and d.stub_rel
    rels = [str((d.execution_path / r).relative_to(d.worktree)).replace("\\", "/")
            for r in (d.prd_rel, d.stub_rel)]
    _check_git(_git(run, ["add", "--", *rels], d.worktree), "git_add_failed")
    if not _git(run, ["status", "--porcelain"], d.worktree).stdout.strip():
        return StepOutcome("git commit (already committed)", 0, "already_committed")
    message = gitops.commit_message("publish", run.caps.rp_no, _prd_digest(run)[:12])
    return _outcome(_check_git(_git(run, ["commit", "-m", message], d.worktree),
                               "git_commit_failed"))


def _step_scaffold(run: RouteRun) -> StepOutcome:
    d, req = run.derived, run.req
    assert d.new_root and req.stack_template
    files = scaffold.expand(req.stack_template, template_variables(req, run.caps), d.new_root,
                            ci=req.ci, docker_compose=req.docker_compose)
    return StepOutcome(f"expand_template {req.stack_template}", None, f"{len(files)} files")


def _step_copy(run: RouteRun) -> StepOutcome:
    d = run.derived
    assert d.new_root
    dest = d.new_root / scaffold.WORKSPACE_COPY_ROOT / run.caps.slug
    copied = scaffold.copy_workspace(run.workspace, dest)
    return StepOutcome("copy_workspace", None, f"{len(copied)} files verified")


def _step_git_init(run: RouteRun) -> StepOutcome:
    d = run.derived
    assert d.new_root
    return _outcome(_check_git(_git(run, ["init", "-b", "main"], d.new_root), "git_init_failed"))


def _step_commit_b(run: RouteRun) -> StepOutcome:
    d, req = run.derived, run.req
    assert d.new_root and req.stack_template
    head = _git(run, ["rev-parse", "--verify", "HEAD"], d.new_root)
    if head.returncode == 0 and not _git(run, ["status", "--porcelain"], d.new_root).stdout.strip():
        return StepOutcome("git commit (already committed)", 0, "already_committed")
    _check_git(_git(run, ["add", "-A"], d.new_root), "git_add_failed")
    tracked = sorted(line for line in _git(run, ["ls-files"], d.new_root).stdout.splitlines()
                     if line.strip())
    expected = expected_tracked(req, run.caps, run.workspace)
    if tracked != expected:
        extra, lacking = sorted(set(tracked) - set(expected)), sorted(set(expected) - set(tracked))
        raise StepFailed("tracked_files_mismatch", argv="git ls-files",
                         stderr=f"多出 {extra[:5]}；缺少 {lacking[:5]}")
    message = gitops.commit_message("scaffold", run.caps.rp_no)
    return _outcome(_check_git(_git(run, ["commit", "-m", message], d.new_root),
                               "git_commit_failed"))


def _step_gh(run: RouteRun) -> StepOutcome:
    d, req = run.derived, run.req
    assert d.new_root and req.owner and req.repo_name
    auth = run.git.gh(["auth", "status"], cwd=d.new_root)
    if auth.returncode != 0:
        cause = ("gh_not_found" if auth.returncode == 127 else
                 "github_token_missing" if not run.git.token else "gh_auth_failed")
        raise StepFailed(cause, exit_code=auth.returncode, stdout=auth.stdout, stderr=auth.stderr,
                         argv=auth.argv_redacted)
    flag = "--public" if req.visibility == "PUBLIC" else "--private"
    created = run.git.gh(["repo", "create", f"{req.owner}/{req.repo_name}", flag, "--source", ".",
                          "--push"], cwd=d.new_root)
    if created.returncode != 0:
        cause = "gh_not_found" if created.returncode == 127 else "gh_permission_denied"
        raise StepFailed(cause, exit_code=created.returncode, stdout=created.stdout,
                         stderr=created.stderr, argv=created.argv_redacted)
    run.results["repo_url"] = f"https://github.com/{req.owner}/{req.repo_name}"
    return _outcome(created)


def adopt_ctx(run: RouteRun, sha: str) -> adopt.AdoptCtx:
    d = run.derived
    return adopt.AdoptCtx(
        sdd_root=run.cfg.sdd_root, state_dir=d.state_dir, key=d.impl_key, root=d.execution_path,
        prd_rel=d.adopt_prd_rel, outer_key=str(run.project["fsm_project"]),
        gate_decision_id=run.db.gate0_decision_id(run.rid) or "", prd_sha256=sha,
        approver=run.approver, allowed_roots=run.cfg.allowed_path_roots, audit=run.audit)


def _step_key_init(run: RouteRun) -> StepOutcome:
    try:
        result = adopt.adopt_baseline(adopt_ctx(run, _prd_digest(run)), stage="init")
    except ApiError as exc:
        raise StepFailed(str(exc.body.get("reason")), stderr=json.dumps(
            exc.body, ensure_ascii=False)[:1500]) from exc
    run.writer.persist(Op("route.bind_impl", run.rid, {
        "route_id": run.route_id, "impl_fsm_project": run.derived.impl_key,
        "impl_state_dir": str(run.derived.state_dir)}))
    return StepOutcome(f"show --project {run.derived.impl_key}", 0,
                       f"state={result.get('state')} created={result.get('created')}")


def _step_adopt(run: RouteRun) -> StepOutcome:
    try:
        result = adopt.adopt_baseline(adopt_ctx(run, _prd_digest(run)), stage="adopt")
    except ApiError as exc:
        raise StepFailed(str(exc.body.get("reason")), stderr=json.dumps(
            exc.body, ensure_ascii=False)[:1500]) from exc
    return StepOutcome("baseline_adopt Stage-1", 0, json.dumps(
        {"state": result.get("state"), "transitions": result.get("transitions")},
        ensure_ascii=False))


EXECUTORS: dict[str, Callable[[RouteRun], StepOutcome]] = {
    "VALIDATE_TARGET": _step_validate, "GIT_SWITCH": _step_git_switch,
    "PUBLISH_DOCS": _step_publish, "REGISTER_STUB": _step_stub, "SCAFFOLD_FILES": _step_scaffold,
    "COPY_WORKSPACE": _step_copy, "GIT_INIT": _step_git_init, "GH_REPO_CREATE": _step_gh,
    "IMPL_KEY_INIT": _step_key_init, "BASELINE_ADOPT": _step_adopt,
}
#: 兩個軌道的 `GIT_COMMIT` 實作不同（A：明列路徑；B：add -A 並與預測對拍）。
def _executor(run: RouteRun, step: str) -> Callable[[RouteRun], StepOutcome]:
    if step == "GIT_COMMIT":
        return _step_commit_a if run.req.track == "A" else _step_commit_b
    return EXECUTORS[step]


def _hook(phase: str, step: str) -> None:
    if STEP_HOOK is not None:
        STEP_HOOK(phase, step)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


_now = now_iso


def _persist_step(run: RouteRun, step_no: int, step: str, status: str, out: StepOutcome,
                  *, started: str, finished: str | None) -> None:
    run.writer.persist(Op("route.step", run.rid, {
        "research_id": run.rid, "route_id": run.route_id, "step_no": step_no, "step": step,
        "status": status, "argv_redacted": gitops.redact(out.argv, run.git.secrets),
        "exit_code": out.exit_code, "stdout_tail": gitops.tail(gitops.redact(
            out.stdout, run.git.secrets)), "stderr_tail": gitops.tail(gitops.redact(
                out.stderr, run.git.secrets)),
        "started_at": started, "finished_at": finished, "actor": run.approver}))


@dataclass
class RouteResult:
    status: str                      # SUCCEEDED｜FAILED
    steps: list[dict[str, Any]]
    failure_step: str | None = None
    reason: str | None = None
    published_docs: dict[str, str] = field(default_factory=dict)


def step_rows(db: ResearchDb, route_id: str) -> list[dict[str, Any]]:
    return [{"step_no": r["step_no"], "step": r["step"], "status": r["status"],
             "exit_code": r["exit_code"], "argv_redacted": r["argv_redacted"],
             "stderr_tail": r["stderr_tail"]} for r in db.route_steps(route_id)]


def execute(run: RouteRun) -> RouteResult:
    """逐步執行（同步）。呼叫前路由列已存在（`PENDING` 或要重試的 `FAILED`）。"""
    run.writer.persist(Op("route.start", run.rid, {
        "research_id": run.rid, "route_id": run.route_id, "actor": run.approver,
        "occurred_at": _now()}))
    plan = build_plan(run.req, run.caps)
    done = {int(r["step_no"]) for r in run.db.route_steps(run.route_id) if r["status"] == "OK"}
    deadline = CLOCK() + run.cfg.research_route_timeout_seconds
    for item in plan:
        number, step = int(item["seq"]), str(item["step"])
        if number in done:
            continue
        started = _now()
        if CLOCK() >= deadline:
            _persist_step(run, number, step, "FAILED",
                          StepOutcome(f"{item['action']} (timeout)", None, "", "route_timeout"),
                          started=started, finished=_now())
            return _fail(run, step, reason="route_timeout")
        _persist_step(run, number, step, "RUNNING", StepOutcome(
            f"{item['action']} {item['target']}"[:500] if step != "VALIDATE_TARGET"
            else f"validate_target inputs_sha256={run.req.inputs_sha256()}"),
            started=started, finished=None)
        try:
            _hook("before", step)
            out = _executor(run, step)(run)
            _hook("after", step)
        except StepFailed as exc:
            _persist_step(run, number, step, "FAILED", StepOutcome(
                exc.argv or str(item["action"]), exc.exit_code, exc.stdout,
                f"{exc.cause}: {exc.stderr}".strip(": ")), started=started, finished=_now())
            return _fail(run, step, reason=exc.cause)
        except (OSError, ScaffoldError, GitopsDenied) as exc:
            rule = getattr(exc, "rule", None) or getattr(exc, "verb", None) or type(exc).__name__
            _persist_step(run, number, step, "FAILED", StepOutcome(
                str(item["action"]), None, "", f"{rule}: {exc}"[:1500]),
                started=started, finished=_now())
            return _fail(run, step, reason=str(rule))
        if step == "VALIDATE_TARGET":              # 雜湊要留在步驟列（重試時比對）
            out.argv = f"validate_target inputs_sha256={run.req.inputs_sha256()}; {out.argv}"
        _persist_step(run, number, step, "OK", out, started=started, finished=_now())
    return _succeed(run, plan)


def _fail(run: RouteRun, step: str, *, reason: str) -> RouteResult:
    run.writer.persist(Op("route.finish", run.rid, {
        "research_id": run.rid, "route_id": run.route_id, "status": "FAILED",
        "failure_step": step, "finished_at": _now(), "actor": run.approver,
        "occurred_at": _now()}))
    return RouteResult("FAILED", step_rows(run.db, run.route_id), failure_step=step, reason=reason)


def _succeed(run: RouteRun, plan: list[dict[str, Any]]) -> RouteResult:
    d = run.derived
    decided = _now()
    steps = step_rows(run.db, run.route_id)
    doc = {
        "route_id": run.route_id, "research_id": run.rid, "track": run.req.track,
        "request": run.req.canonical(), "inputs_sha256": run.req.inputs_sha256(), "plan": plan,
        "steps": [{k: s[k] for k in ("step_no", "step", "status", "exit_code")} for s in steps],
        "results": {"published_docs": run.results.get("published_docs", {}),
                    "impl_fsm_project": d.impl_key, "impl_state_dir": str(d.state_dir),
                    "execution_path": str(d.execution_path),
                    "repo_url": run.results.get("repo_url")},
        "decided_by": run.approver, "decided_at": decided,
        "overridden_default": run.req.overridden_default}
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    sha = layout.sha256_text(text)
    version = run.db.latest_artifact_version(run.rid, "ROUTE_DECISION") + 1
    run.writer.persist(Op("artifact.insert", run.rid, {
        "research_id": run.rid, "kind": "ROUTE_DECISION", "version": version,
        "rel_path": ROUTE_DECISION_REL, "sha256": sha, "bytes": len(text.encode("utf-8")),
        "origin": "BRIDGE", "content": text, "created_by": "bridge"},
        files=(FileRef(str(run.workspace), ROUTE_DECISION_REL, sha),)),
        writes=[FileWrite(run.workspace, ROUTE_DECISION_REL, text)])
    published = dict(run.results.get("published_docs", {}))
    run.writer.persist(Op("route.finish", run.rid, {
        "research_id": run.rid, "route_id": run.route_id, "status": "SUCCEEDED",
        "published_docs": published, "repo_url": run.results.get("repo_url"),
        "console_project_id": run.req.console_project_id, "finished_at": decided,
        "actor": run.approver, "occurred_at": decided}))
    return RouteResult("SUCCEEDED", steps, published_docs=published)


def stored_inputs_hash(db: ResearchDb, route_id: str) -> str | None:
    """失敗的分流列當初的輸入雜湊（記在 `VALIDATE_TARGET` 步驟列）；沒有該列＝None。"""
    for row in db.route_steps(route_id):
        found = _INPUT_HASH_RE.search(str(row["argv_redacted"]))
        if row["step"] == "VALIDATE_TARGET" and found:
            return found.group(1)
    return None


# ── 孤兒回收（BR-D2 於 `routers/research.py::_build_context` 接線）──────────────────────────────
def reap_route_orphans(db: ResearchDb, writer: DurableWriter, *, actor: str = "bridge"
                       ) -> list[str]:
    """把卡在 `PENDING`／`RUNNING` 的分流列標 `FAILED`（進行中的步驟列標 `FAILED`、`stderr_tail`
    為 `interrupted`；游標 `route／ROUTING／FAILED`）。回被回收的 route_id 清單。Bridge 重啟時呼叫
    （上一個行程已不在，所以這些列不可能仍在執行）；DB 不可用時照常拋 `ResearchDbError`。"""
    reaped: list[str] = []
    for row in db.unfinished_routes():
        result = writer.persist(Op("route.reap", str(row["research_id"]), {
            "research_id": str(row["research_id"]), "route_id": str(row["id"]), "actor": actor}))
        if result.get("applied"):
            reaped.append(str(row["id"]))
    return reaped


def check_approver(raw: object) -> str:
    """核准人驗證（保留字、長度、字元集；不合＝422 `invalid_request`）。"""
    return sdd_cli.validate_research_approver(raw)


def new_route_id() -> str:
    return str(uuid.uuid4())


__all__ = ["BRANCH_PATTERN", "PLACEMENT_TARGETS", "RouteCaps", "RouteRequest",
           "RouteRun", "build_plan", "execute", "normalize_request", "reap_route_orphans",
           "validate_request"]
