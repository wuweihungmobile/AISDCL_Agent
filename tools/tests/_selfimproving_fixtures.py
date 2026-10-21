"""SelfImproving P1 測試共用夾具（TCS-SelfImproving-P1 §5；底線開頭、不被收集）。

自行定義與 P0 測試檔等價的純函式（不 import 依賴 `setUpModule` 全域的 P0 函式）；各 P1 測試檔的
`setUpModule` 呼叫 `setup()`、`tearDownModule` 呼叫 `teardown()`。
合成編號一律於執行期以字串相加組出，測試原始碼不含不存在於真帳本的字面 OBS／DEF 編號（NFR-P1-7）。
"""

from __future__ import annotations

import contextlib
import difflib
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import selfimproving  # noqa: E402
from lib.selfimproving import sources as si_sources  # noqa: E402

_STRIP = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)
FIXED_DATE = "1700000000 +0000"  # 基線 commit 的固定時間（相同輸入建出的 repo 其 HEAD 相同）
HDR = "| ID | 時間 | 情境 | 症狀 | 證據座標 | 分類 | 嚴重度 | 處置 | 標記 |"
SEP = "|---|---|---|---|---|---|---|---|---|"
COLS = ["ID", "時間", "情境", "症狀", "證據座標", "分類", "嚴重度", "處置", "標記"]
P0_ITEMS21 = [
    "ledger.structure",
    "ledger.time_tz",
    "row.required",
    "row.enums",
    "row.markers",
    "row.provenance",
    "row.coordinates",
    "row.bytes",
    "row.control_chars",
    "row.fixed_sha",
    "ref.def",
    "ref.obs",
    "ref.orig_notes",
    "ref.carrier_families",
    "history.migration",
    "history.row_mutated",
    "params.keys",
    "params.globs",
    "params.coupling",
    "ledger.volume",
    "ledger.vacuity",
]
P1_ITEMS7 = [
    "events.structure",
    "events.transitions",
    "events.mutated",
    "events.vacuity",
    "events.prop_files",
    "events.research",
    "research.sources",
]
P2_ITEMS4 = ["events.dec_quote", "events.dec_console", "events.verdict", "obs.console_audit"]
LEDGER = "docs/06_quality/SelfImproving_Observation_Ledger.md"
PARAMS = "docs/06_quality/SelfImproving_Protocol/params.json"
EVL = "docs/06_quality/SelfImproving_Event_Ledger.jsonl"
SRC_REL = "docs/06_quality/SelfImproving_Protocol/research_sources.json"
PROPS_REL = "docs/06_quality/SelfImproving_Proposals"
DEFLOG = "docs/06_quality/AutoSDD_Defect_Log.md"
REAL_PARAMS = ROOT / PARAMS
REAL_SOP = ROOT / "docs/05_development/SelfImproving_Operations_SOP.md"
REAL_PRD = ROOT / "docs/01_requirements/SelfImproving_PRD.md"
UUID = "0a1b2c3d-4e5f-4a6b-8c7d-9e8f0a1b2c3d"
UUID2 = "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
LONG_ID = "0000"

TMP: Path
_GCONF: Path
_COUNTER = [0]
_CACHE: dict = {}


def _rmtree(path: Path) -> None:
    def fix(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    shutil.rmtree(path, onerror=fix)


def setup(prefix: str = "si_p1_") -> None:
    global TMP, _GCONF
    TMP = Path(tempfile.mkdtemp(prefix=prefix))
    _GCONF = TMP / "gitconfig"
    _GCONF.write_bytes(b"[gc]\n\tauto=0\n[maintenance]\n\tauto=false\n")
    _COUNTER[0] = 0
    _CACHE.clear()


def teardown() -> None:
    _rmtree(TMP)


def new_dir(name: str = "r") -> Path:
    _COUNTER[0] += 1
    return TMP / f"{name}{_COUNTER[0]}"


def hermetic() -> dict:
    return {
        "GIT_CONFIG_GLOBAL": str(_GCONF),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
        "GIT_TERMINAL_PROMPT": "0",
    }


def genv(when: str | None = None) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in _STRIP}
    env.update(hermetic())
    stamp = when or FIXED_DATE
    env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = stamp
    return env


def git(repo: Path, *args: str, when: str | None = None) -> str:
    cp = subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=genv(when),
        check=False,
    )
    if cp.returncode != 0:
        raise AssertionError(f"git {args} rc={cp.returncode}: {cp.stderr}")
    return cp.stdout.strip()


def put(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))


def putb(repo: Path, rel: str, data: bytes) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def read(repo: Path, rel: str) -> str:
    return (repo / rel).read_bytes().decode("utf-8")


def to_git_date(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    off = dt.strftime("%z")
    return f"{int(dt.timestamp())} {off}"


def commit_all(repo: Path, msg: str, when: str | None = None) -> str:
    stamp = to_git_date(when) if when and "T" in when else when
    git(repo, "add", "-A", when=stamp)
    git(repo, "commit", "-q", "--allow-empty", "-m", msg, when=stamp)
    return git(repo, "rev-parse", "HEAD")


def head(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD")


# --------------------------------------------------------------------------- 編號
def def_id(n: int) -> str:
    return "DEF" + f"-200-{9000 + n}"


def obs_id(n: int) -> str:
    return "OBS" + f"-SI-{n:03d}"


def rid(n: int) -> str:
    return "RUN" + f"-SI-{n:03d}"


def aid(n: int) -> str:
    return "ATT" + f"-SI-{n:03d}"


def pid(n: int) -> str:
    return "PROP" + f"-SI-{n:03d}"


def H(n: int) -> str:
    return "sha256:" + format(n, "064x")


def sha(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


# --------------------------------------------------------------------------- 帳本與 params
def line(cells) -> str:
    return "| " + " | ".join(cells) + " |"


def render_ledger(rows, tz=True) -> str:
    head_lines = ["# 合成帳本", "前言第二行"] + (["<!-- si-ledger: tz=+08:00 -->"] if tz else [])
    return "\n".join(head_lines + ["", HDR, SEP] + [line(r) for r in rows]) + "\n"


def base_rows(c1: str | None = None) -> list[list[str]]:
    t = "2026-10-19 01:00"
    d2 = "open" if c1 is None else f"fixed@{c1}"
    prop123 = "PROP" + "-SI-" + "123"
    spec = [
        (t, "process", "P3", "open", "tools/lib/si_demo.py:12–15", "面=產品;來源=代理;回報者=SA"),
        (
            t,
            "tooling",
            "P3",
            d2,
            "`python tools/selfimproving.py check` rc=1",
            "面=流程;來源=人;回報者=掌舵者",
        ),
        (t, "doc", "P2", def_id(1), def_id(1), "面=文件;來源=工具;回報者=QA"),
        (
            t,
            "bug",
            "P3",
            "deferred；再開症狀：同一症狀第二次出現",
            "CLAUDE.md:12",
            "面=產品;來源=逐字稿;回報者=主控",
        ),
        (
            t,
            "decision",
            "P4",
            "retired；依據 docs/06_quality/notes.md:3",
            "docs/06_quality/",
            "面=流程;來源=帳本;回報者=主控",
        ),
        (
            t,
            "decision",
            "P3",
            "decided：掌舵者裁決採方案甲",
            "sid 00000000-0000-4000-8000-000000000006 line 7",
            "面=流程;來源=人;回報者=掌舵者",
        ),
        (t, "doc", "P4", "merged@" + obs_id(1), "abcdef0123", "面=文件;來源=代理;回報者=SD"),
        (t, "process", "P3", f"proposed@{prop123}", "PRD §9.3", "面=產品;來源=代理;回報者=SA"),
        (
            "2026-10-19 01:00 +09:00",
            "tooling",
            "P2",
            "open",
            "commit 1234567",
            "面=守衛;暴露=a;來源=代理;回報者=QA",
        ),
        (
            "2026-10-19 01:00～10-19 02:00",
            "tooling",
            "P4",
            "open",
            "`python tools/selfimproving.py check` tools/lib/selfimproving/check.py:3",
            "面=守衛;暴露=無;外部衍生=是;來源=工具;回報者=si-check",
        ),
    ]
    return [
        [obs_id(i), s[0], f"基線列 {i:03d}", f"基線症狀 {i:03d}", s[4], s[1], s[2], s[3], s[5]]
        for i, s in enumerate(spec, start=1)
    ]


NON_EVOLVABLE = [
    "**/.claude/**",
    "**/CLAUDE.md",
    "**/docs_template/**",
    "AISDLC_SDD/*/governance/rules/R-*.yaml",
    "AISDLC_SDD/AISDLC_SDD_v*/**",
    "docs/01_requirements/SelfImproving_PRD.md",
    "docs/05_development/SelfImproving_*.md",
    "docs/06_quality/SelfImproving_Event_Ledger.jsonl",
    "docs/06_quality/SelfImproving_Observation_Ledger.md",
    "docs/06_quality/SelfImproving_Proposals/**",
    "docs/06_quality/SelfImproving_Protocol/**",
    "tools/guard.py",
    "tools/lib/aa.py",
    "tools/lib/bb.py",
    "tools/lib/cc.py",
    "tools/lib/selfimproving/**",
    "tools/probe/selfimproving_measure.py",
    "tools/selfimproving.py",
]


def params_dict() -> dict:
    """`tools/lib/selfimproving/params.py` 讀的參數表（P0 鍵＋P1 五鍵）。"""
    return {
        "row_max_bytes": 700,
        "w_n": 20,
        "w_min": 5,
        "w_evt": 2,
        "w_opp": 5,
        "max_proposals_per_run": 3,
        "max_revisions": 2,
        "churn_max": 2,
        "min_heldout": 5,
        "max_touch_ratio": 0.2,
        "max_new_entries": 3,
        "stop_after_bad": 2,
        "cap_frac": 0.9,
        "max_archive_entries_per_card": 50,
        "card_line_max": 100,
        "event_max_bytes": 2000,
        "metrics_rev": 1,
        "min_obs_rows": 10,
        "ledger_warn_bytes": 245760,
        "ledger_fail_bytes": 262144,
        "migration_base_sha": None,
        "spec_body_globs": [
            "**/docs/01_requirements/**",
            "**/docs/02_architecture/**",
            "**/docs/03_testing/**",
        ],
        "non_evolvable_globs": list(NON_EVOLVABLE),
        "research_fetch_max": 8,
        "research_bytes_max": 262144,
        "research_timeout_seconds": 20,
        "min_events": 1,
        "export_limit_max": 500,
        "probe_timeout_seconds": 600,
        "verify_runs_max": 2,
    }


def dump_params(prm: dict) -> str:
    keys = sorted(prm, key=lambda k: k.encode("utf-8"))
    return json.dumps({k: prm[k] for k in keys}, ensure_ascii=False, indent=2) + "\n"


def set_params(repo: Path, **kw) -> None:
    prm = json.loads(read(repo, PARAMS))
    for k, v in kw.items():
        if v is KeyError:
            prm.pop(k, None)
        else:
            prm[k] = v
    put(repo, PARAMS, dump_params(prm))


MINI_PRD = (
    "# 迷你 PRD\n\n"
    "- **實體 glob**：(i) `**/CLAUDE.md`；`AISDLC_SDD/*/governance/rules/R-*.yaml` 中**既有且 "
    "`maturity: active`** 者（新增的 `trust_level: proposed` 不在此列）；"
    "(ii) `**/.claude/**`、根 `CLAUDE.md`〈守衛面准入〉所列 `tools/lib/` 檔、`tools/guard.py`；"
    "(iii) `docs/06_quality/SelfImproving_Protocol/**`、`tools/probe/selfimproving_measure.py`；"
    "(iv) `docs/01_requirements/SelfImproving_PRD.md`、`docs/05_development/SelfImproving_*.md`、"
    "`docs/06_quality/SelfImproving_Observation_Ledger.md`、"
    "`docs/06_quality/SelfImproving_Event_Ledger.jsonl`、"
    "`docs/06_quality/SelfImproving_Proposals/**`、`tools/selfimproving.py`、"
    "`tools/lib/selfimproving/**`；(v) `AISDLC_SDD/AISDLC_SDD_v*/**` 去掉 LATEST（`python "
    "AISDLC_SDD/scripts/sdd_version.py` 現查）、`**/docs_template/**`。\n"
)
MINI_CLAUDE = (
    "# 迷你 CLAUDE\n\n"
    "- 守衛面＝`.claude/hooks/**`、`tools/lib/{aa,bb,cc}.py`、`tools/guard.py`。其餘文字\n"
)
VOLD, VNEW = "AISDLC_SDD_v0.20", "AISDLC_SDD_v0.30"
DEF_HDR = "| ID | 發現日期 | 發現情境 | 現象與證據（file:line） | 嚴重度 | 分流去向 | 狀態 |"


def _file_lines(n: int, fmt: str) -> str:
    return "".join(fmt.format(i) + "\n" for i in range(1, n + 1))


def fixture_files() -> dict[str, str]:
    """C3 的工作樹夾具檔（路徑 → 內容）；`patch_for` 以其已知內容算出正確 hunk。"""
    files = {
        "playbooks/demo.yaml": _file_lines(40, "step_{0:02d}: value {0:02d}"),
        "docs/notes/demo.md": _file_lines(100, "line {0:03d}"),
        "docs/notes/other.md": _file_lines(50, "line {0:02d}"),
        "docs/notes/tiny.md": _file_lines(3, "tiny {0}"),
        "build/reports/pytest.log": "ok\n",
        "docs/06_quality/misstep_attribution_demo.jsonl": "{}\n",
        ".gitignore": "ignored/\n",
        f"AISDLC_SDD/{VOLD}/README.md": "old\n",
        f"AISDLC_SDD/{VNEW}/README.md": "new\n",
        f"AISDLC_SDD/{VNEW}/governance/rules/R-9.1.yaml": "id: R-9.1\nmaturity: active\n",
        f"AISDLC_SDD/{VNEW}/governance/rules/R-9.2.yaml": "id: R-9.2\nmaturity: proposed\n",
        f"AISDLC_SDD/{VNEW}/governance/rules/R-9.3.yaml": "id: R-9.3\nname: x\n",
    }
    for i in range(1, 10):
        files[f"docs/notes/f{i}.md"] = _file_lines(50, "line {0:02d}")
    return files


def defect_log(extra=()) -> str:
    row = [def_id(1), "2026-09-01", "夾具", "tools/lib/si_demo.py:12", "P2", "-", "fixed@abc1234"]
    rows = [row, *extra]
    return "\n".join([DEF_HDR, "|---|---|---|---|---|---|---|", *[line(r) for r in rows]]) + "\n"


def _common_p0(repo: Path, prm: dict) -> None:
    """鋪 `tools/lib/selfimproving/check.py` 需要的 P0 最小樹（參數／指標／PRD／CLAUDE.md）。"""
    put(repo, PARAMS, dump_params(prm))
    put(repo, "docs/06_quality/SelfImproving_Protocol/metrics.md", "metrics\n")
    put(repo, "docs/01_requirements/SelfImproving_PRD.md", MINI_PRD)
    put(repo, "CLAUDE.md", MINI_CLAUDE)
    for n, name in enumerate(
        [
            "AutoSDD_Defect_Log.md",
            "AutoSDD_Defect_Log_archive_01.md",
            "AutoSDD_External_Blocked_Log.md",
            "AutoSDD_Structural_Debt_Log.md",
        ],
        start=1,
    ):
        put(repo, f"docs/06_quality/{name}", f"| ID | x |\n|---|---|\n| {def_id(n)} | y |\n")
    put(
        repo,
        "docs/06_quality/SelfImproving_Observation_Ledger_archive_01.md",
        f"| ID | x |\n|---|---|\n| {obs_id(901)} | y |\n",
    )


def make_p1_repo(
    dest: Path,
    *,
    events=None,
    sources=None,
    extra_obs=(),
    defs=(),
    prm=None,
    rows: int = 10,
    commit: bool = True,
) -> Path:
    """tmp 內的 git repo：C1、C2＝P0 基線（OBS 001～010、列 002 於 C2 由 open 轉 fixed@C1）、
    C3＝P1 新增與覆寫（一個 commit；commit=False 則 C3 內容留在工作樹）。"""
    dest.mkdir(parents=True)
    git(dest, "init", "-q")
    params = params_dict()
    _common_p0(dest, params)
    rows_ = base_rows()
    put(dest, LEDGER, render_ledger(rows_[:rows]))
    c1 = commit_all(dest, "C1")
    c2_rows = base_rows(c1[:12])
    rows_[1][7] = c2_rows[1][7]
    put(dest, LEDGER, render_ledger(rows_[:rows]))
    commit_all(dest, "C2")
    params.update(prm or {})
    put(dest, PARAMS, dump_params(params))
    for rel, text in fixture_files().items():
        put(dest, rel, text)
    # defs 的每個元素為（DEF 號, 發現日期, 嚴重度, 狀態, 證據）
    put(dest, DEFLOG, defect_log([[d[0], d[1], "夾具", d[4], d[2], "-", d[3]] for d in defs]))
    shutil.copyfile(
        ROOT / "AISDLC_SDD/scripts/sdd_version.py",
        _mkparent(dest / "AISDLC_SDD/scripts/sdd_version.py"),
    )
    if extra_obs:
        put(dest, LEDGER, render_ledger(rows_[:rows] + [list(r) for r in extra_obs]))
    if sources is not None:
        put(dest, SRC_REL, sources if isinstance(sources, str) else json.dumps(sources))
    if events is not None:
        write_events(dest, events)
    if commit:
        commit_all(dest, "C3")
    return dest


def _mkparent(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def p1_base() -> Path:
    """已建好的基線 repo 的複本（每個測試檔的快取只建一次）。"""
    if "base" not in _CACHE:
        _CACHE["base"] = make_p1_repo(TMP / "baseline")
    dest = new_dir("v")
    shutil.copytree(_CACHE["base"], dest)
    return dest


# --------------------------------------------------------------------------- 事件帳本夾具
_ORDER = {
    "run.open": ["run", "trigger", "coords", "head_sha"],
    "run.close": ["run", "outcomes", "no_event"],
    "research.scan": ["run", "sources", "sources_sha256", "fetched_at"],
    "research.skip": ["run", "reason", "note", "band", "sid", "line"],
    "attr": ["id", "type", "obs", "items", "root_cause", "from", "reopens"],
    "attr.confirm": ["att"],
    "attr.reject": ["att", "note"],
    "prop": [
        "id",
        "rev",
        "run",
        "base",
        "cls",
        "action",
        "route",
        "target",
        "touched_count",
        "touched_sha256",
        "patch_sha256",
        "body_sha256",
        "digest",
        "sources",
        "proposer",
        "reviewer",
        "preimage",
    ],
    "card": ["prop", "rev", "digest", "card_sha256"],
    "dec": [
        "id", "prop", "run", "dkind", "digest", "reason", "reason_class", "flags", "carrier",
        "quote", "sid", "line", "card_seq", "audit_ref", "audit_sha256", "key_id", "decider",
        "decided_at",
    ],
    "heldout.freeze": ["prop", "digest", "n", "frozen_by"],
    "app.sandbox": ["id", "prop", "rev", "base", "sandbox_sha256", "applied", "touched_ok",
                    "rollback_ok", "fail_code"],
    "app.verify": ["id", "prop", "rev", "verdict", "baseline_red", "patched_green", "mutated_red",
                   "carrier_proof", "probes_n", "verify_sha256", "heldout_digest", "reasons"],
    "app.promote": ["id", "prop", "rev", "head_sha", "pre_sha256", "post_sha256",
                    "unverified_ack"],
    "app.rollback": ["id", "prop", "rev", "pre_sha256", "post_sha256"],
}
_WITH_DIGEST = ("approve", "reject", "return", "promote", "decline-promote", "ack-handoff")
_WITH_REASON = ("reject", "decline-promote", "return", "rollback", "resume")
_WITH_CLASS = ("reject", "decline-promote", "return")


def std_quote(dkind: str, target: str, flags=()) -> str:
    """決定行的標準引言（`dec` 夾具預設；`target` 為 PROP 號，`resume` 為 RUN 號）。"""
    verb = {"approve": "核准", "reject": "否決", "decline-promote": "否決", "return": "退回",
            "promote": "晉升", "ack-handoff": "轉交", "rollback": "回滾", "unblock": "解除",
            "resume": "恢復"}.get(str(dkind), "核准")
    tail = " 夾具理由" if dkind in _WITH_REASON else (" 未驗採納" if flags else "")
    return f"{verb} {target}{tail}"


def _dec_defaults(e: dict, seq: int, t: str) -> dict:
    dk, car = e.get("dkind"), e.get("carrier", "transcript")
    out: dict = {"id": f"DEC-SI-{seq:03d}", "decided_at": t}
    if car == "console":
        out.update(decider="ops_admin", audit_ref=UUID2, audit_sha256=H(6), key_id="00000000")
    else:
        target = e.get("run") if dk == "resume" else e.get("prop")
        out.update(decider="掌舵者", quote=std_quote(dk, str(target), e.get("flags") or ()),
                   sid=UUID, line=1)
        if dk != "resume":
            out["card_seq"] = 1
    if dk in _WITH_DIGEST:
        out["digest"] = H(4)
    if dk in _WITH_REASON:
        out["reason"] = "夾具理由"
    if dk in _WITH_CLASS:
        out["reason_class"] = "未說明"
    return out


def _sandbox_defaults(e: dict, seq: int, head_sha: str) -> dict:
    failed = e.get("applied") is False
    out = {"id": f"APP-SI-{seq:03d}", "rev": 1, "base": head_sha, "applied": True,
           "sandbox_sha256": H(8), "touched_ok": True, "rollback_ok": True, "fail_code": None}
    if failed:
        out.update(touched_ok=None, rollback_ok=None)
    if e.get("fail_code") == "SANDBOX-EXPORT-FAILED":
        out["sandbox_sha256"] = None
    return out


def _verify_defaults(e: dict, seq: int) -> dict:
    verdict = e.get("verdict", "PASS")
    out = {"id": f"APP-SI-{seq:03d}", "rev": 1}
    if verdict == "NE":
        return {**out, "probes_n": 0, "baseline_red": None, "patched_green": None,
                "mutated_red": None, "carrier_proof": None, "verify_sha256": None,
                "heldout_digest": None, "reasons": ["NO-PROBES"]}
    return {**out, "probes_n": 1, "baseline_red": True, "patched_green": verdict == "PASS",
            "mutated_red": True, "carrier_proof": True, "verify_sha256": H(9),
            "heldout_digest": H(7),
            "reasons": [] if verdict == "PASS" else ["PATCHED-NOT-GREEN"]}


def _p2_defaults(e: dict, seq: int, t: str, head_sha: str) -> dict:
    """九種 P2 kind 的確定性預設（R107 (a)；呼叫端明示的鍵優先、逐位元保留）。"""
    kind = e["kind"]
    app = f"APP-SI-{seq:03d}"
    return {
        "card": {"rev": 1, "digest": H(4), "card_sha256": H(5)},
        "heldout.freeze": {"digest": H(7), "n": 5, "frozen_by": "FZ"},
        "app.promote": {"id": app, "rev": 1, "head_sha": head_sha, "pre_sha256": H(10),
                        "post_sha256": H(11), "unverified_ack": False},
        "app.rollback": {"id": app, "rev": 1, "pre_sha256": H(11), "post_sha256": H(10)},
        "obs.add": {"obs": obs_id(1), "audit_ref": UUID2, "audit_sha256": H(6),
                    "key_id": "00000000", "decider": "ops_admin", "carrier": "console"},
        "obs.close": {"obs": obs_id(1), "audit_ref": UUID2, "audit_sha256": H(6),
                      "key_id": "00000000", "decider": "ops_admin", "carrier": "console",
                      "disposition": "decided：夾具"},
    }.get(kind) or {
        "dec": lambda: _dec_defaults(e, seq, t),
        "app.sandbox": lambda: _sandbox_defaults(e, seq, head_sha),
        "app.verify": lambda: _verify_defaults(e, seq),
    }.get(kind, lambda: {})()


def T0() -> datetime:
    """事件預設時間錨（現在減 2 日）；同一測試檔內固定，使整檔重寫不改動較早的行。"""
    if "t0" not in _CACHE:
        _CACHE["t0"] = (datetime.now().astimezone() - timedelta(days=2)).replace(microsecond=0)
    return _CACHE["t0"]


def ev(kind: str, by: str = "main", **fields) -> dict:
    return {"kind": kind, "by": by, **fields}


def _defaults(kind: str, head_sha: str) -> dict:
    return {
        "run.open": {"trigger": "a", "coords": ["tools/a.py:1"], "head_sha": head_sha},
        "research.skip": {"reason": "offline", "note": "夾具"},
        "prop": {
            "rev": 1,
            "base": head_sha,
            "action": "modify",
            "route": "loop",
            "touched_count": 1,
            "touched_sha256": H(1),
            "patch_sha256": H(2),
            "body_sha256": H(3),
            "digest": H(4),
            "proposer": "SA",
            "reviewer": None,
        },
    }.get(kind, {})


def compose(events, repo_head: str, seqs=None, t0: datetime | None = None) -> list[dict]:
    t0 = t0 or T0()
    out = []
    for i, e in enumerate(events):
        seq = seqs[i] if seqs else i + 1
        t = e.get("t") or (t0 + timedelta(minutes=seq)).isoformat(timespec="seconds")
        body = {
            **_defaults(e["kind"], repo_head),
            **_p2_defaults(e, seq, t, repo_head),
            **{k: v for k, v in e.items() if k not in ("kind", "by", "t")},
        }
        order = _ORDER.get(e["kind"], [])
        keys = [k for k in order if k in body] + [k for k in body if k not in order]
        obj = {
            "seq": seq,
            "t": t,
            "kind": e["kind"],
            "by": e["by"],
        }
        obj.update({k: body[k] for k in keys})
        out.append(obj)
    return out


P2_FULL_KINDS = ("card", "dec", "heldout.freeze", "app.sandbox", "app.verify", "app.promote",
                 "app.rollback", "obs.add", "obs.close")


def fill_p2(kind: str, by: str, body: dict, seq: int = 6) -> dict:
    """手寫損壞事件的 P2 完整欄位補齊：只補呼叫端沒給的必備鍵，明示的（含錯誤的）值逐位元保留，
    使「只有那一個鍵壞」的損壞案例在完整欄位表下仍只觸發那一個碼（R107 (a)）。"""
    if kind not in P2_FULL_KINDS:
        return body
    obj = compose([{"kind": kind, "by": by, **body}], "0" * 40, [seq])[0]
    return {k: v for k, v in obj.items() if k not in ("seq", "t", "kind", "by")}


def dumps_line(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def write_events(repo: Path, events, *, commit: bool = False, seqs=None, t0=None) -> list[dict]:
    try:
        h = head(repo)
    except AssertionError:
        h = "0" * 40
    objs = compose(events, h, seqs, t0)
    put(repo, EVL, "".join(dumps_line(o) + "\n" for o in objs))
    if commit:
        commit_all(repo, "events")
    return objs


def append_events(repo: Path, events) -> list[dict]:
    """在既有事件帳本之後追加手寫事件（`seq` 接續末行；測試用，CLI 寫不出的 kind）。"""
    cur = EV(repo)
    seq0 = cur[-1]["seq"] if cur else 0
    objs = compose(events, head(repo), [seq0 + i + 1 for i in range(len(events))])
    with (repo / EVL).open("ab") as fh:
        fh.write("".join(dumps_line(o) + "\n" for o in objs).encode("utf-8"))
    return objs


def EV(repo: Path) -> list[dict]:
    p = repo / EVL
    if not p.is_file():
        return []
    return [json.loads(ln) for ln in p.read_bytes().decode("utf-8").split("\n") if ln.strip()]


def run_open_ev(n: int, **kw) -> dict:
    return ev("run.open", run=rid(n), **kw)


def skip_ev(n: int, **kw) -> dict:
    return ev("research.skip", run=rid(n), **kw)


def prop_ev(n: int, run: int = 1, **kw) -> dict:
    """`prop` 事件（`tools/lib/selfimproving/events.py` 的事件列形狀）。"""
    d = {
        "id": pid(n),
        "run": rid(run),
        "cls": "D",
        "target": [f"docs/notes/p{n}.md"],
        "sources": [obs_id(1)],
    }
    d.update(kw)
    return ev("prop", d.pop("by", "SA"), **d)


def dec_ev(n: int, dkind: str, **kw) -> dict:
    return ev("dec", "掌舵者", prop=pid(n), dkind=dkind, **kw)


def card_ev(n: int, **kw) -> dict:
    return ev("card", "main", prop=pid(n), **kw)


def freeze_ev(n: int, **kw) -> dict:
    return ev("heldout.freeze", kw.pop("by", "FZ"), prop=pid(n), **kw)


def sandbox_ev(n: int, **kw) -> dict:
    return ev("app.sandbox", "main", prop=pid(n), **kw)


def verify_ev(n: int, verdict: str = "PASS", **kw) -> dict:
    return ev("app.verify", "main", prop=pid(n), verdict=verdict, **kw)


def promote_ev(n: int, **kw) -> dict:
    return ev("app.promote", "main", prop=pid(n), **kw)


def rollback_ev(n: int, **kw) -> dict:
    return ev("app.rollback", "main", prop=pid(n), **kw)


def obs_add_ev(**kw) -> dict:
    return ev("obs.add", "main", **kw)


def obs_close_ev(**kw) -> dict:
    return ev("obs.close", "main", **kw)


def sc_close() -> list[dict]:
    """事件情境：run 2 關閉前一核一拒——`tools/lib/selfimproving/fold.py` 的重放輸入。"""
    return [
        run_open_ev(1),
        run_open_ev(2),
        skip_ev(2),
        prop_ev(124, 2, cls="P", target=["playbooks/demo.yaml"]),
        dec_ev(124, "approve"),
        prop_ev(125, 2, cls="D", target=["docs/notes/demo.md"]),
        dec_ev(125, "reject"),
    ]


def sc_seq() -> tuple[list[dict], list[int]]:
    """事件情境：run 7 的 attr→prop 鏈——`tools/lib/selfimproving/fold.py` 的重放輸入。"""
    return (
        [
            run_open_ev(7),
            skip_ev(7),
            ev(
                "attr",
                "SA",
                id=aid(12),
                type="root",
                obs=[obs_id(1)],
                items=[["DOC", "docs/06_quality/"]],
                root_cause="docs/stale-note",
            ),
            prop_ev(130, 7, target=["docs/notes/demo.md"], sources=[obs_id(2)]),
        ],
        [5, 6, 9, 10],
    )


def _chain(n: int, steps: list, **kw) -> list[dict]:
    """單一提案的事件鏈（prop→決定…）——`tools/lib/selfimproving/fold.py` 的重放輸入。"""
    out = [prop_ev(n, 1, target=[f"docs/notes/n{n}.md"], **kw)]
    for s in steps:
        out.append(s if isinstance(s, dict) else dec_ev(n, s))
    return out


def _verify(n: int, verdict: str) -> list:
    return [
        dec_ev(n, "approve"),
        ev("heldout.freeze", "FZ", prop=pid(n)),
        ev("app.sandbox", "main", prop=pid(n)),
        ev("app.verify", "main", prop=pid(n), verdict=verdict),
    ]


def sc_legal() -> list[dict]:
    """事件情境：合法轉移全集——`tools/lib/selfimproving/fold.py`／`evcheck.py` 的重放輸入。"""
    e = [run_open_ev(1), skip_ev(1)]
    full = [
        *_verify(124, "PASS"),
        dec_ev(124, "promote"),
        ev("app.promote", "main", prop=pid(124)),
        ev("mea.open", "main", prop=pid(124)),
        ev("mea.close", "main", prop=pid(124), result="clean"),
    ]
    e += _chain(124, full)
    e += _chain(125, ["return"]) + [
        prop_ev(125, 1, rev=2, target=["docs/notes/n125.md"]),
        dec_ev(125, "reject"),
        dec_ev(125, "unblock"),
    ]
    e += _chain(126, ["ack-handoff"], route="handoff:R")
    e += _chain(
        127,
        [
            *_verify(127, "NE"),
            dec_ev(127, "promote", flags=["unverified_ack"]),
            ev("app.promote", "main", prop=pid(127), unverified_ack=True),
        ],
    )
    e += _chain(128, [*_verify(128, "FAIL"), "return"]) + [
        prop_ev(128, 1, rev=2, target=["docs/notes/n128.md"])
    ]
    e += _chain(129, [])
    e += _chain(130, ["approve"])
    e += _chain(131, _verify(131, "PASS"))
    e += _chain(132, _verify(132, "FAIL"))
    e += _chain(133, _verify(133, "NE"))
    e += _chain(134, [], route="handoff:T1")
    e += _chain(135, ["return"])
    e += _chain(136, [*_verify(136, "PASS"), "decline-promote"])
    e += _chain(
        137,
        [
            *_verify(137, "PASS"),
            dec_ev(137, "promote"),
            ev("app.promote", "main", prop=pid(137)),
            ev("mea.open", "main", prop=pid(137)),
        ],
    )
    n = len(e)
    e += [
        ev("mea.close", "main", prop=pid(137), result="pending"),
        ev("mea.amend", "main", prop=pid(137), window=n + 1, **{"from": "pending", "to": "clean"}),
        ev("mea.report", "main", prop=pid(137)),
        ev("card", "main", prop=pid(137)),
        dec_ev(137, "rollback"),
        ev("app.rollback", "main", prop=pid(137)),
    ]
    return e


def sc_rev() -> list[dict]:
    """事件情境：rev 修訂鏈（return→rev 2／3）——`tools/lib/selfimproving/fold.py` 的重放輸入。"""
    e = [run_open_ev(1), skip_ev(1)]
    e += _chain(124, [])
    e += _chain(125, ["approve"])
    e += _chain(126, ["reject"])
    e += _chain(127, ["ack-handoff"], route="handoff:DEF")
    e += _chain(128, ["return"])
    for rev in (2, 3):
        e += [prop_ev(128, 1, rev=rev, target=["docs/notes/n128.md"]), dec_ev(128, "return")]
    return e


def sc_susp() -> list[dict]:
    e = [run_open_ev(1), skip_ev(1)]
    for n, res in ((124, "recurred"), (125, "rolled-back")):
        e += _chain(
            n,
            [
                *_verify(n, "PASS"),
                dec_ev(n, "promote"),
                ev("app.promote", "main", prop=pid(n)),
                ev("mea.open", "main", prop=pid(n)),
                ev("mea.close", "main", prop=pid(n), result=res),
            ],
        )
    e += [
        ev("run.close", "main", run=rid(1), outcomes={pid(124): "closed", pid(125): "closed"}),
        run_open_ev(2),
        run_open_ev(3),
        skip_ev(3),
    ]
    return e


# --------------------------------------------------------------------------- patch 與本文建構器
def _q(path: str, quote: bool) -> str:
    if not quote:
        return path
    out = []
    for b in path.encode("utf-8"):
        c = chr(b)
        out.append(f"\\{b:03o}" if b >= 0x80 or b < 0x20 else ('\\"' if c == '"' else c))
    return '"' + "".join(out) + '"'


def _hdr(a: str, b: str, quote: bool) -> str:
    return f"diff --git {_q('a/' + a, quote)} {_q('b/' + b, quote)}\n"


def patch_mod(
    path: str,
    edits: dict[int, str],
    *,
    old: str | None = None,
    quote=False,
    tab_suffix: str | None = None,
) -> bytes:
    old_text = old if old is not None else fixture_files()[path]
    old_lines = old_text.splitlines(keepends=True)
    new_lines = list(old_lines)
    for n, text in edits.items():
        new_lines[n - 1] = text + "\n"
    suffix = f"\t{tab_suffix}" if tab_suffix else ""
    body = "".join(
        difflib.unified_diff(old_lines, new_lines, f"a/{path}{suffix}", f"b/{path}{suffix}", n=3)
    )
    if quote:
        body = body.replace(f"a/{path}", _q("a/" + path, True), 1).replace(
            f"b/{path}", _q("b/" + path, True), 1
        )
    return (_hdr(path, path, quote) + body).encode("utf-8")


def patch_diff(path: str, old_text: str, new_text: str) -> bytes:
    """任意前後內容的 unified diff（插入、刪除、取代皆可）；標頭帶 diff --git。"""
    body = "".join(
        difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            f"a/{path}",
            f"b/{path}",
            n=3,
        )
    )
    return (_hdr(path, path, False) + body).encode("utf-8")


def patch_insert(path: str, after: int, lines: list[str], *, old: str | None = None) -> bytes:
    """在第 after 行之後插入 lines（零刪除行，觸及比例為 0）。"""
    old_text = old if old is not None else fixture_files()[path]
    old_lines = old_text.splitlines(keepends=True)
    if old_lines and not old_lines[-1].endswith("\n"):
        old_lines[-1] += "\n"
    new_lines = old_lines[:after] + [x + "\n" for x in lines] + old_lines[after:]
    return patch_diff(path, "".join(old_lines), "".join(new_lines))


def patch_add(path: str, lines: list[str], *, quote=False) -> bytes:
    body = "".join(f"+{x}\n" for x in lines)
    return (
        _hdr(path, path, quote) + "new file mode 100644\n--- /dev/null\n"
        f"+++ {_q('b/' + path, quote)}\n@@ -0,0 +1,{len(lines)} @@\n" + body
    ).encode("utf-8")


def patch_del(path: str, *, old: str | None = None) -> bytes:
    old_lines = (old if old is not None else fixture_files()[path]).splitlines()
    body = "".join(f"-{x}\n" for x in old_lines)
    return (
        _hdr(path, path, False) + "deleted file mode 100644\n"
        f"--- a/{path}\n+++ /dev/null\n@@ -1,{len(old_lines)} +0,0 @@\n" + body
    ).encode("utf-8")


def patch_rename(old: str, new: str, edits: dict[int, str] | None = None) -> bytes:
    head_ = (
        _hdr(old, new, False) + "similarity index 100%\n"
        if not edits
        else _hdr(old, new, False) + "similarity index 90%\n"
    )
    head_ += f"rename from {old}\nrename to {new}\n"
    if not edits:
        return head_.encode("utf-8")
    old_lines = fixture_files()[old].splitlines(keepends=True)
    new_lines = list(old_lines)
    for n, text in edits.items():
        new_lines[n - 1] = text + "\n"
    body = "".join(difflib.unified_diff(old_lines, new_lines, f"a/{old}", f"b/{new}", n=3))
    return (head_ + body).encode("utf-8")


def patch_copy(src: str, dst: str) -> bytes:
    return (
        _hdr(src, dst, False) + f"similarity index 100%\ncopy from {src}\ncopy to {dst}\n"
    ).encode("utf-8")


def patch_join(*patches: bytes) -> bytes:
    return b"".join(patches)


BODY_HEADS = ["反例證據", "Before", "After", "影響面", "欄位"]


def body_md(cls: str = "P", *, drop=(), skeleton_drop=(), extra_heads=False, **fields) -> str:
    vals = {
        "symptom": "卡面症狀一句",
        "risk": "風險一句",
        "rollback": "git revert 該 patch",
        "budget": "1 次子代理、約 3000 token",
        "result_label": "失敗",
        "scope": "夾具範圍",
    }
    if cls == "M":
        vals.update(source_obs=obs_id(1), retire_when="該症狀不再出現")
    vals.update(fields)
    for k in drop:
        vals.pop(k, None)
    rows = "\n".join(f"| {k} | {v} |" for k, v in vals.items())
    sections = {
        "反例證據": "證據一句。",
        "Before": "舊。",
        "After": "新。",
        "影響面": "小。",
        "欄位": f"| 欄位 | 內容 |\n|---|---|\n{rows}",
    }
    out = [f"## {h}\n\n{sections[h]}\n" for h in BODY_HEADS if h not in skeleton_drop]
    return "\n".join(out)


def memory_dir(tmp: Path) -> Path:
    d = tmp / "memory"
    d.mkdir(parents=True)
    idx = "".join(f"- [條目 {i:03d}](m_{i:03d}.md) — 一句說明 {i:03d}\n" for i in range(1, 121))
    arc = "".join(f"- [條目 {i:03d}](m_{i:03d}.md) — 一句說明 {i:03d}\n" for i in range(1, 31))
    (d / "MEMORY.md").write_bytes(idx.encode("utf-8"))
    (d / "archive-index-old.md").write_bytes(arc.encode("utf-8"))
    (d / "demo.md").write_bytes("".join(f"note {i:02d}\n" for i in range(1, 21)).encode("utf-8"))
    return d


def mem_patch_archive(d: Path, k: int, pointers: int = 1) -> bytes:
    idx = (d / "MEMORY.md").read_text(encoding="utf-8").splitlines(keepends=True)
    arc = (d / "archive-index-old.md").read_text(encoding="utf-8").splitlines(keepends=True)
    moved = idx[:k]
    new_idx = [f"- [指標 {i}](archive-index-old.md) — 指標行\n" for i in range(pointers)] + idx[k:]
    new_arc = arc + moved
    a = "".join(difflib.unified_diff(idx, new_idx, "a/memory/MEMORY.md", "b/memory/MEMORY.md", n=1))
    b = "".join(
        difflib.unified_diff(
            arc, new_arc, "a/memory/archive-index-old.md", "b/memory/archive-index-old.md", n=1
        )
    )
    return (
        _hdr("memory/MEMORY.md", "memory/MEMORY.md", False)
        + a
        + _hdr("memory/archive-index-old.md", "memory/archive-index-old.md", False)
        + b
    ).encode("utf-8")


def default_target(cls: str) -> str:
    return {
        "R": f"AISDLC_SDD/{VNEW}/governance/rules/R-9.9.yaml",
        "M": "memory/demo.md",
        "D": "docs/notes/demo.md",
    }.get(cls, "playbooks/demo.yaml")


def default_patch(cls: str, md_dir: Path | None = None) -> tuple[bytes, str]:
    """各類別的預設 patch 與 target。"""
    target = default_target(cls)
    if cls == "R":
        return patch_add(target, ["id: R-9.9", "trust_level: proposed"]), target
    if cls == "M":
        return patch_mod(
            target, {3: "改過三", 4: "改過四"}, old=(md_dir / "demo.md").read_text(encoding="utf-8")
        ), target
    return patch_mod(target, {3: "改過三", 4: "改過四"}), target


def good_prop_args(repo: Path, cls: str = "P", **over) -> list[str]:
    tmp = new_dir("pa")
    tmp.mkdir()
    md_dir = over.get("memory_dir") or (memory_dir(tmp / "mem") if cls == "M" else None)
    base_cls = "P" if cls in ("evaluator-change", "loop-self") else cls
    target = default_target(base_cls)
    patch = over["patch"] if "patch" in over else default_patch(base_cls, md_dir)[0]
    body_cls = "M" if cls == "M" else "P"
    body = over.get("body", body_md(body_cls))
    pf, bf = tmp / "x.patch", tmp / "x.md"
    pf.write_bytes(patch)
    bf.write_bytes(body.encode("utf-8") if isinstance(body, str) else body)
    targets = over.get("target", [target])
    action = over.get("action", "add" if cls == "R" else "modify")
    args = ["--cls", cls, "--action", action]
    for t in targets if isinstance(targets, list) else [targets]:
        args += ["--target", t]
    for s in over.get("sources", [obs_id(1), obs_id(2)]):
        args += ["--source", s]
    args += [
        "--patch-file",
        str(pf),
        "--body-file",
        str(bf),
        "--proposer",
        over.get("proposer", "SA"),
    ]
    if over.get("reviewer"):
        args += ["--reviewer", over["reviewer"]]
    if over.get("handoff"):
        args += ["--handoff", over["handoff"]]
    if md_dir is not None:
        args += ["--memory-dir", str(md_dir)]
    return args


def revise_args(repo: Path, cls: str = "P", **over) -> list[str]:
    """`prop-revise` 的旗標：只留 patch、本文、提案者（與可選的審查者、通道、記憶目錄）。"""
    a, out, i = good_prop_args(repo, cls, **over), [], 0
    while i < len(a):
        if a[i] in ("--cls", "--action", "--target", "--source"):
            i += 2
            continue
        out.append(a[i])
        i += 1
    return out


# --------------------------------------------------------------------------- 測試基底與輔助
def snap(repo: Path):
    files = {}
    for p in sorted(repo.rglob("*")):
        rel = p.relative_to(repo).as_posix()
        if rel == ".git" or rel.startswith(".git/") or not p.is_file():
            continue
        files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return files, git(repo, "status", "--porcelain")


def tree_files(path: Path) -> list[str]:
    return sorted(p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file())


def codes_of(out: str) -> set[str]:
    return set(re.findall(r"(?m)^  ([A-Z][A-Z0-9-]+) ", out))


class SiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.home = new_dir("home")
        self.home.mkdir()
        env = {**hermetic(), "AUTOSDD_SI_DIR": str(self.home)}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        for k in _STRIP:
            os.environ.pop(k, None)

    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = selfimproving.main([str(a) for a in argv])
        return rc, out.getvalue(), err.getvalue()

    def M(self, repo: Path, *argv, repo_flag: bool = True):
        return self.run_main([*argv, *(["--repo", str(repo)] if repo_flag else [])])

    def MJ(self, repo: Path, *argv):
        rc, out, err = self.M(repo, *argv, "--json")
        self.assertIn(rc, (0, 1, 2), err)
        return json.loads(out)

    def check(self, repo: Path, *extra: str) -> dict:
        rc, out, err = self.run_main(["check", "--repo", str(repo), "--json", *extra])
        self.assertIn(rc, (0, 1, 2), err)
        res = json.loads(out)
        res["_item"] = {i["id"]: i for i in res["items"]}
        res["_rc"] = rc
        return res

    def S(self, res, item):
        return res["_item"][item]["status"]

    def F(self, res, item):
        return {(f["subject"], f["code"]) for f in res["_item"][item]["findings"]}

    def usage_error(self, rc, out, err, msg=""):
        self.assertEqual((rc, out), (3, ""), msg)
        self.assertTrue(err.startswith("selfimproving:"), f"{msg} stderr={err!r}")

    def rejected(self, rc, out, expect_codes=None, msg=""):
        self.assertEqual(rc, 1, f"{msg} out={out}")
        lines = out.split("\n")
        self.assertTrue(lines[0].startswith("reject "), msg)
        self.assertIn("obs-draft:", lines, msg)
        if expect_codes is not None:
            self.assertEqual(codes_of(out), set(expect_codes), f"{msg} out={out}")

    def draft_ok(self, repo: Path, out: str, msg: str = "") -> None:
        lines = out.split("\n")
        rows = lines[lines.index("obs-draft:") + 1 :]
        rows = [r for r in rows if r.startswith("| OBS")]
        self.assertTrue(rows, f"{msg} 沒有草稿列")
        for row in rows:
            copy = new_dir("dr")
            shutil.copytree(repo, copy)
            put(copy, LEDGER, read(copy, LEDGER).rstrip("\n") + "\n" + row + "\n")
            res = self.check(copy)
            rid_ = row.split("|")[1].strip()
            bad = [
                (i["id"], f["code"])
                for i in res["items"]
                for f in i["findings"]
                if f["subject"] == rid_
            ]
            self.assertEqual(bad, [], f"{msg} 草稿列 {row}")
            _rmtree(copy)

    def cli_ok(self, repo, *argv):
        rc, out, err = self.M(repo, *argv)
        self.assertEqual(rc, 0, f"{argv} -> {out}{err}")
        return out

    def open_run(self, repo: Path, n: int | None = None) -> str:
        """`run-open` 加 `research --skip --reason offline`；回運轉號。"""
        out = self.cli_ok(
            repo, "run-open", "--trigger", "a", "--coord", "tools/a.py:1", "--by", "main"
        )
        run = re.search(r"id=(\S+)", out).group(1)
        self.cli_ok(
            repo, "research", "--skip", "--run", run, "--reason", "offline", "--note", "離線驗證"
        )
        return run

    def fresh_run_repo(self) -> tuple[Path, str]:
        """已 open_run 的基線複本（每個測試檔快取樣板，避免重複建 repo）。"""
        key = "run_template"
        if key not in _CACHE:
            tpl = p1_base()
            self.open_run(tpl)
            commit_all(tpl, "run")
            _CACHE[key] = tpl
            _CACHE["tpl_home"] = None
        dest = new_dir("fr")
        shutil.copytree(_CACHE[key], dest)
        return dest, rid(1)

    def prop(self, repo, run, cls="P", *extra, **over):
        return self.M(repo, "prop-new", "--run", run, *good_prop_args(repo, cls, **over), *extra)


# --------------------------------------------------------------------------- 本機 HTTP 夾具
class Srv:
    def __init__(self, routes: dict) -> None:
        self.routes = routes
        self.requests: list[dict] = []
        self.max_inflight = 0
        self._inflight = 0
        self._lock = threading.Lock()
        self._arrived: dict[str, threading.Event] = {}
        self.closing = threading.Event()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # noqa: D401
                return

            def do_GET(self):
                outer._handle(self)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def arrived(self, path: str) -> threading.Event:
        return self._arrived.setdefault(path, threading.Event())

    def _handle(self, h: BaseHTTPRequestHandler) -> None:
        with self._lock:
            self._inflight += 1
            self.max_inflight = max(self.max_inflight, self._inflight)
            self.requests.append(
                {"path": h.path, "headers": {k.lower(): v for k, v in h.headers.items()}}
            )
        try:
            self.arrived(h.path).set()
            route = self.routes.get(h.path)
            if route is None:
                h.send_response(404)
                h.send_header("Content-Length", "0")
                h.end_headers()
                return
            status, headers, body = route[:3]
            opts = route[3] if len(route) > 3 else {}
            if opts.get("hold") is not None:
                opts["hold"].wait(30)
            if opts.get("delay"):
                threading.Event().wait(opts["delay"])
            if opts.get("raw") is not None:  # 狀態列、標頭、本文全由 raw 逐項寫出；close 可打斷停頓
                for chunk, pause in opts["raw"]():
                    h.wfile.write(chunk)
                    h.wfile.flush()
                    if pause and self.closing.wait(pause):
                        break
                return
            h.send_response(status)
            for k, v in headers.items():
                h.send_header(k, v)
            if "Content-Length" not in headers:
                h.send_header("Content-Length", str(len(body)))
            h.end_headers()
            if opts.get("stall"):  # 送完標頭後不送本文，等伺服器關閉
                self.closing.wait(30)
            elif opts.get("drip"):  # 每 0.5 秒滴 1 個位元組，直到本文送完或伺服器關閉
                for i in range(len(body)):
                    h.wfile.write(body[i:i + 1])
                    h.wfile.flush()
                    if self.closing.wait(0.5):
                        break
            else:
                h.wfile.write(body)
        except OSError:  # 含 BrokenPipe／ConnectionReset／ConnectionAborted：客戶端先走了
            pass
        finally:
            with self._lock:
                self._inflight -= 1

    def close(self) -> None:
        self.closing.set()
        for r in self.routes.values():
            if len(r) > 3 and r[3].get("hold") is not None:
                r[3]["hold"].set()
        self.httpd.shutdown()
        self.httpd.server_close()


def serve(routes: dict) -> Srv:
    return Srv(routes)


def _byte_drip(piece: bytes, count: int, pause: float = 0.5):
    return [(piece, pause)] * count


_CHUNKED_HEAD = (
    b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n"
    b"Transfer-Encoding: chunked\r\nConnection: close\r\n\r\n"
)


def raw_routes() -> dict:
    """TCS §5.4 `RAW-ROUTES`：回應框架各階段慢滴的五條負控路由（總時長 8 至 8.5 秒、皆有限）
    與一條正常分塊對照路由 `/chunked-ok`。"""
    status = b"HTTP/1.0 200 OK\r\n"
    seqs = {
        "/status-drip": lambda: [*((status[i:i + 1], 0.5) for i in range(len(status))),
                                 (b"Content-Type: text/plain\r\n\r\nhello", 0)],
        "/hdr-drip": lambda: [
            (b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nX-Slow: ", 0),
            *_byte_drip(b"a", 16), (b"\r\n\r\nhello", 0)],
        "/hdr-many-lines": lambda: [
            (b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n", 0),
            *((f"X-H{n}: v\r\n".encode(), 0.5) for n in range(16)), (b"\r\nhello", 0)],
        "/chunk-size-drip": lambda: [(_CHUNKED_HEAD, 0), *_byte_drip(b"0", 16)],
        "/trailer-drip": lambda: [(_CHUNKED_HEAD + b"3\r\nabc\r\n0\r\nX-T: ", 0),
                                  *_byte_drip(b"a", 16)],
        "/chunked-ok": lambda: [(_CHUNKED_HEAD + b"3\r\nabc\r\n2\r\nde\r\n0\r\nX-T: v\r\n\r\n", 0)],
    }
    return {path: (200, {}, b"", {"raw": fn}) for path, fn in seqs.items()}


def table_bytes(srv: Srv, entries, retired=()) -> bytes:
    sources = []
    for ident, path in sorted(entries, key=lambda e: e[0].encode("utf-8")):
        e = {
            "id": ident,
            "url": srv.url(path),
            "kind": "docs",
            "extract": "讀標題",
            "added_by": "夾具",
        }
        if ident in retired:
            e["retired"] = True
        sources.append(e)
    return (
        json.dumps({"schema_rev": 1, "sources": sources}, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def write_table(
    repo: Path, srv: Srv, entries, *, retired=(), commit: bool = True, when: str | None = None
) -> bytes:
    raw = table_bytes(srv, entries, retired)
    putb(repo, SRC_REL, raw)
    if commit:
        commit_all(repo, "sources", when=when)
    return raw


@contextlib.contextmanager
def relaxed():
    policy = si_sources.Policy(allow_http=True, allow_loopback=True)
    with mock.patch.object(si_sources, "DEFAULT_POLICY", policy):
        yield


# --------------------------------------------------------------------------- SOP 判準夾具
def sop_sections(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"(?m)^(?=## )", text.replace("\r\n", "\n"))
    return [(p.split("\n", 1)[0][3:].strip(), p) for p in parts if p.startswith("## ")]


def sop_section(text: str, key: str) -> str:
    return next((body for title, body in sop_sections(text) if key in title), "")


def lines_outside_fences(section: str) -> list[str]:
    out, fenced = [], False
    for ln in section.split("\n"):
        if ln.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(ln)
    return out


def line_has_all(section: str, *fragments: str) -> list[str]:
    return [ln for ln in lines_outside_fences(section) if all(f in ln for f in fragments)]


def prd_entry_fragments(prd_text: str) -> list[str]:
    rows, found = [], False
    for ln in prd_text.replace("\r\n", "\n").split("\n"):
        if ln.startswith("| 模組桶 | 先讀（權威指引）"):
            found = True
            continue
        if found:
            if not ln.startswith("|"):
                break
            if set(ln.replace("|", "").strip()) <= set("-: "):
                continue
            rows.append(ln)
    frags: list[str] = []
    for r in rows:
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        frags += re.findall(r"`([^`]+)`", cells[1]) if len(cells) > 1 else []
    return frags


# R65 (a)～(g)：（節標題關鍵字, 必備片段）——片段逐字承載自 TCS R65
FRAGMENTS: list[tuple[str, str]] = (
    [
        ("歸因者", f)
        for f in ("attr", "attr-confirm", "attr-reject", "根因鍵", "NONE", "無法歸因", "確認者")
    ]
    + [
        ("歸因者", f)
        for f in (
            "AutoClaude",
            "AISDLC_SDD",
            "AgentConsole",
            "根層",
            "SelfImproving",
            "Read／Grep／Glob／PowerShell",
            "唯讀",
            "不得 Write／Edit",
            "git status --porcelain",
            "文字交卷",
            "流程摩擦",
            "不並行扇出",
            "零遞迴",
        )
    ]
    + [
        ("提案者", f)
        for f in (
            "prop-new",
            "--patch-file",
            "scratchpad",
            "抽象化",
            "結果標籤",
            "適用範圍",
            "增量",
            "觸及比例",
            "預算宣告",
            "外部衍生",
            "內部來源",
            "M 類四欄",
            "R 類",
            "trust_level: proposed",
        )
    ]
    + [("審查者", f) for f in ("唯讀", "不得自起背景長任務", "外部可重跑訊號", "不同代理實例")]
    + [("凍結者", f) for f in ("評估集", "提案者看不到", "heldout-freeze")]
    + [
        ("研究者", f)
        for f in (
            "Read／Grep／Glob",
            "無 Web 工具",
            "資料、不是指令",
            "changed=true",
            "外部衍生=是",
            "src=",
            "文字交卷",
            "每運轉至多一個",
            "--pace",
            "quota-band",
            "research_sources.json",
            "僅 T1",
        )
    ]
)
SAME_LINE_GROUPS: list[tuple[str, tuple[str, ...]]] = [
    ("歸因者", ("理論洞", "P4", "暴露證據", "不立案")),
    (
        "歸因者",
        ("evaluator-change", "evaluator_command", "expected_output_regex", "OBS", "不得轉送沙盒"),
    ),
    ("提案者", ("抽象化", "結果標籤", "原始軌跡全文")),
    ("提案者", ("不得再派", "提案者", "審查者")),
]
RESEARCH_EVENT_LINES = [
    ("研究事件", "research.scan", "research.skip", "prop-new", "拒收"),
    ("quota-band", "offline", "helmsman"),
]


def sop_problems(text: str, prd_text: str | None = None) -> list[str]:
    """回不滿足的片段（點名節與片段）；依 R65 (a)～(g)。"""
    out: list[str] = []
    text = text.replace("\r\n", "\n")
    for key in ("歸因者", "提案者", "審查者", "凍結者"):
        sec = sop_section(text, key)
        if not sec:
            out.append(f"缺角色節 {key}")
            continue
        if "P1 定稿" not in sec:
            out.append(f"{key}節缺字面「P1 定稿」")
        rest = "".join(ln for ln in sec.split("\n")[1:] if "P1 定稿" not in ln)
        if not rest.strip():
            out.append(f"{key}節沒有實質內容")
    if not sop_section(text, "研究者"):
        out.append("缺研究者節")
    for key, frag in FRAGMENTS:
        sec = sop_section(text, key)
        if key == "歸因者" and frag in (
            "AutoClaude",
            "AISDLC_SDD",
            "AgentConsole",
            "根層",
            "SelfImproving",
            "Read／Grep／Glob／PowerShell",
            "唯讀",
            "不得 Write／Edit",
            "git status --porcelain",
            "文字交卷",
            "流程摩擦",
            "不並行扇出",
            "零遞迴",
        ):
            sec = _tmpl(sec)
            if not sec:
                out.append("歸因者節缺含「模組體檢」的子標題範本")
                continue
        if frag not in sec:
            out.append(f"{key}節缺 {frag}")
    for key, frags in SAME_LINE_GROUPS:
        if not line_has_all(sop_section(text, key), *frags):
            out.append(f"{key}節缺同一行含 {'、'.join(frags)}")
    for frags in RESEARCH_EVENT_LINES:
        if not line_has_all(text, *frags):
            out.append(f"全文缺同一行含 {'、'.join(frags)}")
    if prd_text is not None:
        tmpl = _tmpl(sop_section(text, "歸因者"))
        out += [
            f"體檢範本缺 PRD 入口表片段 {f}" for f in prd_entry_fragments(prd_text) if f not in tmpl
        ]
    return out


def _tmpl(section: str) -> str:
    """歸因者節內標題含「模組體檢」的子節文字（`###` 以下）。"""
    parts = re.split(r"(?m)^(?=#{3,6} )", section)
    return next(
        (p for p in parts if re.match(r"#{3,6} ", p) and "模組體檢" in p.split("\n", 1)[0]), ""
    )


# --------------------------------------------------------------------------- SOP 變異副本輔助
def section_bounds(text: str, key: str, sub: str | None = None) -> tuple[int, int]:
    """節（標題含 key 的 `## `）在全文中的區間；sub 給定時縮到其中標題含 sub 的 `### ` 子節。"""
    m = re.search(rf"(?m)^## [^\n]*{re.escape(key)}[^\n]*\n", text)
    start = m.start()
    nxt = re.search(r"(?m)^## ", text[m.end() :])
    end = m.end() + nxt.start() if nxt else len(text)
    if sub is None:
        return start, end
    s = re.search(rf"(?m)^#{{3,6}} [^\n]*{re.escape(sub)}[^\n]*\n", text[start:end])
    n2 = re.search(r"(?m)^#{3,6} ", text[start + s.end() : end])
    return start + s.start(), start + s.end() + (n2.start() if n2 else end - start - s.end())


def remove_in_section(text: str, key: str, frag: str, sub: str | None = None) -> str:
    """把片段在其所屬節（或模組體檢子節）的**全部**出現處刪去（片段可為他片段的子字串，
    例如 `attr` 之於 `attr-confirm`，只刪首次出現不足以使判準回報）。"""
    a, b = section_bounds(text, key, sub)
    assert frag in text[a:b], frag
    return text[:a] + text[a:b].replace(frag, "") + text[b:]


def same_line(text: str, key: str, frags) -> tuple[int, int]:
    """區間內第一個同時含全部片段（且不在圍欄內）的行的 (起, 迄) 字元位置。"""
    a, b = section_bounds(text, key)
    pos = a
    for ln in text[a:b].split("\n"):
        if all(x in ln for x in frags):
            return pos, pos + len(ln)
        pos += len(ln) + 1
    raise AssertionError(f"{key} 節沒有同一行含 {frags}")


def split_last_to_next_line(text: str, key: str, frags) -> str:
    s, e = same_line(text, key, frags)
    ln = text[s:e]
    last = frags[-1]  # 把組內最後一個片段（全部出現處）搬到下一行，使同行條件被拆開
    return text[:s] + ln.replace(last, "") + "\n" + last + text[e:]


def move_line(text: str, key_from: str, frags, key_to: str) -> str:
    s, e = same_line(text, key_from, frags)
    ln = text[s:e]
    cut = text[:s] + text[e + 1 :]
    a, b = section_bounds(cut, key_to)
    return cut[:b] + ln + "\n" + cut[b:]


def tree_state(repo: Path):
    return git(repo, "status", "--porcelain"), git(repo, "rev-parse", "HEAD")
