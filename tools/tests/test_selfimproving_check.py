"""SelfImproving P0 `check` 的驗收測試（TCS-SelfImproving-P0 的 AT 全集）。

方法名含 AT 底線形，`pytest -k AT_001_1_E_1` 可單跑。夾具全用 tmp 目錄內的合成帳本與合成
git repo（hermetic 環境，不碰真帳本、不上網）；只唯讀存取真 repo 的 params／metrics／SOP／PRD。
合成編號於執行期組出，使本檔原始碼不含不存在於真帳本的字面 OBS 或 DEF 編號。
"""

from __future__ import annotations

import ast
import contextlib
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
import unittest
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import selfimproving  # noqa: E402
from lib.selfimproving import params as si_params  # noqa: E402

_STRIP = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)
_TMP: Path  # setUpModule 建、tearDownModule 清；單獨 import 本模組（如探針）不會在 %TEMP% 留目錄
_GCONF: Path
_COUNTER = [0]
HDR = "| ID | 時間 | 情境 | 症狀 | 證據座標 | 分類 | 嚴重度 | 處置 | 標記 |"
SEP = "|---|---|---|---|---|---|---|---|---|"
COLS = ["ID", "時間", "情境", "症狀", "證據座標", "分類", "嚴重度", "處置", "標記"]
KEYS23 = [
    "row_max_bytes",
    "w_n",
    "w_min",
    "w_evt",
    "w_opp",
    "max_proposals_per_run",
    "max_revisions",
    "churn_max",
    "min_heldout",
    "max_touch_ratio",
    "max_new_entries",
    "stop_after_bad",
    "cap_frac",
    "max_archive_entries_per_card",
    "card_line_max",
    "event_max_bytes",
    "metrics_rev",
    "min_obs_rows",
    "ledger_warn_bytes",
    "ledger_fail_bytes",
    "migration_base_sha",
    "spec_body_globs",
    "non_evolvable_globs",
]
ITEMS21 = [
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
LEDGER = "docs/06_quality/SelfImproving_Observation_Ledger.md"
PARAMS = "docs/06_quality/SelfImproving_Protocol/params.json"
NOTES = "docs/05_development/SelfImproving_Observation_Ledger_notes.md"
REAL_SOP = ROOT / "docs/05_development/SelfImproving_Operations_SOP.md"
REAL_PARAMS = ROOT / PARAMS
REAL_METRICS = ROOT / "docs/06_quality/SelfImproving_Protocol/metrics.md"
UUID = "0a1b2c3d-4e5f-4a6b-8c7d-9e8f0a1b2c3d"


def _rmtree(path: Path) -> None:
    def fix(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    shutil.rmtree(path, onerror=fix)


def setUpModule() -> None:
    global _TMP, _GCONF
    _TMP = Path(tempfile.mkdtemp(prefix="si_check_"))
    _GCONF = _TMP / "gitconfig"
    _GCONF.write_bytes(b"[gc]\n\tauto=0\n[maintenance]\n\tauto=false\n")  # no bg gc
    _COUNTER[0] = 0
    _BASE.clear()  # 快取的基線 repo 住在 _TMP 之下，換目錄就必須一併作廢
    _CHAIN.clear()


def tearDownModule() -> None:
    _rmtree(_TMP)


def new_dir(name: str = "r") -> Path:
    _COUNTER[0] += 1
    return _TMP / f"{name}{_COUNTER[0]}"


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


def genv() -> dict:
    env = {k: v for k, v in os.environ.items() if k not in _STRIP}
    env.update(hermetic())
    return env


def git(repo: Path, *args: str) -> str:
    cp = subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=genv(),
        check=False,
    )
    if cp.returncode != 0:
        raise AssertionError(f"git {args} rc={cp.returncode}: {cp.stderr}")
    return cp.stdout.strip()


def git_in(repo: Path, stdin: str, *args: str) -> str:
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=stdin,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=genv(),
        check=True,
    )
    return cp.stdout.strip()


def put(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))


def commit_all(repo: Path, msg: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


def def_id(n: int) -> str:
    return "DEF" + f"-200-{9000 + n}"


def obs_id(n: int) -> str:
    return "OBS" + f"-SI-{n}"


PROP = "PROP" + "-SI-" + "123"
OBS_ARCH = obs_id(901)


def line(cells) -> str:
    return "| " + " | ".join(cells) + " |"


def render_ledger(rows, tz=True) -> str:
    head = ["# 合成帳本", "前言第二行"] + (["<!-- si-ledger: tz=+08:00 -->"] if tz else [])
    return "\n".join(head + ["", HDR, SEP] + [line(r) for r in rows]) + "\n"


def base_rows(c1: str | None = None) -> list[list[str]]:
    t = "2026-10-19 01:00"
    p = lambda n: f"OBS-SI-{n:03d}"  # noqa: E731
    d2 = "open" if c1 is None else f"fixed@{c1}"
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
        (t, "doc", "P4", "merged@OBS-SI-001", "abcdef0123", "面=文件;來源=代理;回報者=SD"),
        (t, "process", "P3", f"proposed@{PROP}", "PRD §9.3", "面=產品;來源=代理;回報者=SA"),
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
        [p(i), s[0], f"基線列 {i:03d}", f"基線症狀 {i:03d}", s[4], s[1], s[2], s[3], s[5]]
        for i, s in enumerate(spec, start=1)
    ]


def params_dict() -> dict:
    prm = {
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
        "research_fetch_max": 8,  # P1 新增五鍵（TCS-P1 R67）：與 PARAM_SPECS 同步
        "research_bytes_max": 262144,
        "research_timeout_seconds": 20,
        "min_events": 1,
        "export_limit_max": 500,
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
        "non_evolvable_globs": [
            "**/CLAUDE.md",
            "A/*/b.yaml",
            "**/.claude/**",
            "tools/x.py",
            "docs/q/**",
            "docs/r.md",
            "tools/lib/aa.py",
            "tools/lib/bb.py",
            "tools/lib/cc.py",
        ],
    }
    return prm


MINI_PRD = (
    "# 迷你 PRD\n\n"
    "- **實體 glob**：(i) `**/CLAUDE.md`；`A/*/b.yaml` 中**既有且 `maturity: active`** 者"
    "（新增的 `trust_level: proposed` 不在此列）；"
    "(ii) `**/.claude/**`、根 `CLAUDE.md`〈守衛面准入〉"
    "所列 `tools/lib/` 檔、`tools/x.py`；"
    "(iii) `docs/q/**`、`docs/r.md`（以 `python tools/y.py` 現查）。\n"
)
MINI_CLAUDE = (
    "# 迷你 CLAUDE\n\n"
    "- 守衛面＝`.claude/hooks/**`、`tools/lib/{aa,bb,cc}.py`、`tools/x.py`。其餘文字\n"
)


def dump_params(prm: dict) -> str:
    keys = sorted(prm, key=lambda k: k.encode("utf-8"))
    return json.dumps({k: prm[k] for k in keys}, ensure_ascii=False, indent=2) + "\n"


def common_files(repo: Path, prm: dict) -> None:
    """寫入 tools/lib/selfimproving/ 的 check 所需共用合成檔（params、metrics、PRD、各帳本）。"""
    put(repo, PARAMS, dump_params(prm))
    put(repo, "docs/06_quality/SelfImproving_Protocol/metrics.md", "metrics\n")
    put(repo, "docs/01_requirements/SelfImproving_PRD.md", MINI_PRD)
    put(repo, "CLAUDE.md", MINI_CLAUDE)
    logs = [
        "AutoSDD_Defect_Log.md",
        "AutoSDD_Defect_Log_archive_01.md",
        "AutoSDD_External_Blocked_Log.md",
        "AutoSDD_Structural_Debt_Log.md",
    ]
    for n, name in enumerate(logs, start=1):
        put(repo, f"docs/06_quality/{name}", f"| ID | x |\n|---|---|\n| {def_id(n)} | y |\n")
    put(
        repo,
        "docs/06_quality/SelfImproving_Observation_Ledger_archive_01.md",
        f"| ID | x |\n|---|---|\n| {OBS_ARCH} | y |\n",
    )


def init_repo(repo: Path) -> None:
    repo.mkdir(parents=True)
    git(repo, "init", "-q")


def make_valid_repo(dest: Path, rows: int = 10, mutate=None, late_ledger: bool = False) -> Path:
    """建立 tools/lib/selfimproving/ 的 check 合法基準 repo：合成帳本與參數，C1、C2 兩個 commit。"""
    ctx = SimpleNamespace(rows=base_rows(), params=params_dict())
    if mutate:
        mutate(ctx)
    init_repo(dest)
    common_files(dest, ctx.params)
    if not late_ledger:
        put(dest, LEDGER, render_ledger(ctx.rows[:rows]))
    c1 = commit_all(dest, "C1")
    if late_ledger or rows < 2:
        put(dest, "docs/06_quality/SelfImproving_Protocol/metrics.md", "metrics 2\n")
    else:
        ctx2 = base_rows(c1[:12])
        for i in range(min(rows, 10)):
            ctx.rows[i][7] = ctx2[i][7] if i == 1 else ctx.rows[i][7]
        put(dest, LEDGER, render_ledger(ctx.rows[:rows]))
    commit_all(dest, "C2")
    if late_ledger:
        ctx.rows[1][7] = f"fixed@{c1[:12]}"
        put(dest, LEDGER, render_ledger(ctx.rows))
    return dest


_BASE: list[Path] = []


def baseline(name: str = "v") -> Path:
    if not _BASE:
        _BASE.append(make_valid_repo(_TMP / "baseline"))
    dest = new_dir(name)
    shutil.copytree(_BASE[0], dest)
    return dest


LONG = "原文段落" * 40


def _crow(n, sym, disp, marks, coord=None):
    return [
        f"OBS-SI-{n:03d}",
        "2026-10-18 21:20",
        f"情境{n}",
        sym,
        coord or f"tools/a{n}.py:{n}",
        "process",
        "P3",
        disp,
        marks,
    ]


def confirm_row(m_sha: str, c0_sha: str, mode: str) -> list[str]:
    sha = c0_sha if mode == "wrong-sha" else m_sha
    parts = []
    if mode != "no-sha":
        parts.append(f"commit {sha[:12]}")
    if mode != "no-sid":
        parts.append("sid 00000000-0000-4000-8000-000000000001")
    if mode != "no-line":
        parts.append("line 2581")
    disp = "deferred；掌舵者預先授權" if mode == "not-decided" else "decided：掌舵者預先授權"
    quote = "完全不是掌舵者說過的話" if mode == "wrong-quote" else "了解，凍結後接著開 P0 實作"
    return [
        "OBS-SI-005",
        "2026-10-19 12:00 +08:00",
        "主控視窗",
        f"掌舵者原句：「{quote}」",
        "、".join(parts),
        "decision",
        "P3",
        disp,
        "面=流程;來源=人;回報者=主控",
    ]


def make_migration_chain(dest: Path, confirm: str = "valid") -> SimpleNamespace:
    init_repo(dest)
    prm = params_dict()
    prm["min_obs_rows"] = 3
    common_files(dest, prm)
    c0_rows = [
        [
            "OBS-SI-001",
            "2026-10-18 21:20",
            "情境1",
            "症狀1",
            "tools/a1.py:1",
            "process",
            "P3",
            "open",
        ],
        [
            "OBS-SI-002",
            "2026-10-18 21:20",
            "情境2",
            "症狀2",
            "tools/a2.py:2",
            "process",
            "P3",
            "裁決：採方案甲，已回報掌舵者",
        ],
        [
            "OBS-SI-003",
            "2026-10-18 21:20",
            "情境3",
            "症狀3",
            "tools/a3.py:3",
            "process",
            "P3",
            "延後；再開症狀：同一症狀第二次出現",
        ],
        [
            "OBS-SI-004",
            "2026-10-18 21:20",
            "情境4",
            "症狀4",
            "tools/a4.py:4",
            "process",
            "P3",
            LONG,
        ],
    ]
    old = [
        "# 舊版帳本",
        "",
        "| ID | 時間 | 情境 | 症狀 | 證據座標 | 分類 | 嚴重度 | 處置 |",
        "|---|---|---|---|---|---|---|---|",
    ] + [line(r) for r in c0_rows]
    put(dest, LEDGER, "\n".join(old) + "\n")
    c0 = commit_all(dest, "C0")
    anchor = f"@{NOTES}#OBS-SI-004"
    m_rows = [
        _crow(1, "症狀1", "open", "面=流程;來源=代理;回報者=SA"),
        _crow(
            2,
            "症狀2",
            "decided：採方案甲",
            '面=流程;來源=代理;回報者=SA;orig="裁決：採方案甲，已回報掌舵者"',
        ),
        _crow(
            3,
            "症狀3",
            "deferred；再開症狀：同一症狀第二次出現",
            '面=流程;來源=代理;回報者=SA;orig="延後；再開症狀：同一症狀第二次出現"',
        ),
        _crow(4, "症狀4", "decided：已處理", f"面=流程;來源=代理;回報者=SA;orig={anchor}"),
    ]
    put(dest, LEDGER, render_ledger(m_rows))
    put(dest, NOTES, f"# 附註\n\n## OBS-SI-004\n\n{LONG}\n")
    m = commit_all(dest, "M")
    prm["migration_base_sha"] = m
    put(dest, PARAMS, dump_params(prm))
    rows = m_rows + ([] if confirm == "no-decided" else [confirm_row(m, c0, confirm)])
    put(dest, LEDGER, render_ledger(rows))
    n = commit_all(dest, "N")
    return SimpleNamespace(repo=dest, c0=c0, m=m, n=n, params=prm)


_CHAIN: list[SimpleNamespace] = []


def chain(name: str = "c", confirm: str = "valid") -> SimpleNamespace:
    if confirm != "valid":
        return make_migration_chain(new_dir(name), confirm)
    if not _CHAIN:
        _CHAIN.append(make_migration_chain(_TMP / "chain"))
    dest = new_dir(name)
    shutil.copytree(_CHAIN[0].repo, dest)
    return SimpleNamespace(**{**vars(_CHAIN[0]), "repo": dest})


def read(repo: Path, rel: str) -> str:
    return (repo / rel).read_bytes().decode("utf-8")


def set_cell(repo: Path, n: int, col: str, value: str, rel: str = LEDGER) -> None:
    text, ci = read(repo, rel), COLS.index(col)
    out = []
    for ln in text.split("\n"):
        if ln.startswith(f"| OBS-SI-{n:03d} |"):
            cells = ln[2:-2].split(" | ")
            cells[ci] = value
            ln = line(cells)
        out.append(ln)
    put(repo, rel, "\n".join(out))


def get_cell(repo: Path, n: int, col: str) -> str:
    for ln in read(repo, LEDGER).split("\n"):
        if ln.startswith(f"| OBS-SI-{n:03d} |"):
            return ln[2:-2].split(" | ")[COLS.index(col)]
    raise AssertionError(n)


def add_mark(repo: Path, n: int, extra: str) -> None:
    cur = get_cell(repo, n, "標記")
    set_cell(repo, n, "標記", f"{cur};{extra}" if cur else extra)


def set_params(repo: Path, **kw) -> None:
    prm = json.loads(read(repo, PARAMS))
    for k, v in kw.items():
        if v is KeyError:
            prm.pop(k, None)
        else:
            prm[k] = v
    put(repo, PARAMS, dump_params(prm))


def append_row(repo: Path, cells: list[str]) -> None:
    put(repo, LEDGER, read(repo, LEDGER).rstrip("\n") + "\n" + line(cells) + "\n")


class SiCase(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.dict(os.environ, hermetic())
        patcher.start()
        self.addCleanup(patcher.stop)
        for k in _STRIP:
            os.environ.pop(k, None)

    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = selfimproving.main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def check(self, repo: Path, *extra: str) -> dict:
        rc, out, err = self.run_main(["check", "--repo", str(repo), "--json", *extra])
        self.assertIn(rc, (0, 1, 2), err)
        res = json.loads(out)
        res["_item"] = {i["id"]: i for i in res["items"]}
        return res

    def S(self, res: dict, item: str) -> str:
        return res["_item"][item]["status"]

    def F(self, res: dict, item: str) -> set:
        return {(f["subject"], f["code"]) for f in res["_item"][item]["findings"]}

    def codes(self, res: dict, item: str) -> list:
        return [(f["subject"], f["code"]) for f in res["_item"][item]["findings"]]


def row_ids(*ns: int) -> set:
    return {f"OBS-SI-{n:03d}" for n in ns}


def sop_section(text: str, key: str) -> str:
    parts = re.split(r"(?m)^(?=## )", text.replace("\r\n", "\n"))
    return next((p for p in parts if p.startswith("## ") and key in p.split("\n", 1)[0]), "")


def has_line(text: str, *needles: str) -> bool:
    return any(all(n in ln for n in needles) for ln in text.split("\n"))


def sop_roles_problems(text: str) -> list[str]:
    out = [
        f"缺角色節 {r}"
        for r in ("擷取者", "歸因者", "提案者", "審查者", "凍結者")
        if not sop_section(text, r)
    ]
    cap = sop_section(text, "擷取者")
    need = [
        "HEAD=<sha>",
        "文字交卷",
        "流程摩擦",
        "python tools/session_resume_planner.py --pace",
        "Omitted",
        "OBS-SI-033",
        "OBS-SI-038",
        "python tools/selfimproving.py check",
        "來源",
        "回報者",
    ]
    out += [f"擷取者節缺 {n}" for n in need if n not in cap]
    if not has_line(cap, "外部衍生=是", "不得單獨"):
        out.append("缺外部衍生條文")
    return out


def sop_startup_problems(text: str) -> list[str]:
    sec = sop_section(text, "啟動條件")
    out, pos = [], 0
    marks = ["(a)", "(b)", "(c)", "(d)", "(e)"]
    idx = []
    for m in marks:
        i = sec.find(m, pos)
        if i < 0:
            return [f"缺標籤 {m}"]
        idx.append(i)
        pos = i + 3
    need = ["掌舵者指令", "第二次", "P≤2", "再開症狀"]
    for k, needle in enumerate(need):
        if needle not in sec[idx[k] : idx[k + 1]]:
            out.append(f"{marks[k]} 段缺 {needle}")
    if "容量事件" not in sec[idx[4] :].split("\n", 1)[0]:
        out.append("(e) 同行缺容量事件")
    if not has_line(sec, "日曆", "版本號", "覆蓋度", "每 N 輪"):
        out.append("缺否定句")
    if "si status" not in sec or "視窗開場" not in sec or "收尾" not in sec:
        out.append("缺 si status／視窗開場／收尾")
    return out


LINE_RULES = {
    "r3": ("無事件", "通過"),
    "r4": ("產出數量", "T1"),
    "r5": ("DEF-<id>", "真缺陷"),
    "r7": ("loop-self", "轉交", "T1"),
}


def sop_line_problems(text: str, rule: str) -> list[str]:
    return [] if has_line(text, *LINE_RULES[rule]) else [f"缺 {rule}"]


def sop_r8_problems(text: str) -> list[str]:
    cap = sop_section(text, "擷取者")
    return [] if has_line(cap, "流程摩擦", "OBS-SI-004") else ["缺流程摩擦入口"]


def sop_r9_problems(text: str) -> list[str]:
    cap = sop_section(text, "擷取者")
    return (
        [] if has_line(cap, "追加", "rel=corrects:", "ROW-MUTATED", "open", "終值") else ["缺 r9"]
    )


def drop_lines(text: str, *needles: str) -> str:
    return "\n".join(ln for ln in text.split("\n") if not all(n in ln for n in needles))


def sop_text() -> str:
    return REAL_SOP.read_bytes().decode("utf-8").replace("\r\n", "\n")


def si_sources() -> list[Path]:
    """靜態掃描的受測原始碼：入口 tools/selfimproving.py＋套件 tools/lib/selfimproving/*.py。"""
    return [TOOLS / "selfimproving.py", *sorted((TOOLS / "lib" / "selfimproving").glob("*.py"))]


class TestLedgerRowRules(SiCase):
    def test_AT_001_1_1_baseline_is_green(self):
        repo = baseline()
        res = self.check(repo)
        self.assertEqual((res["rc"], res["overall"], res["rows"]), (0, "PASS", 10))
        ids = [i["id"] for i in res["items"]]
        self.assertEqual((ids[:21], len(ids)), (ITEMS21, 28))  # P1：前 21 項不變、其後追加 7 項
        for item in ITEMS21:
            if item == "ref.carrier_families":
                self.assertEqual(self.S(res, item), "NE")
                self.assertFalse(res["_item"][item]["blocking"])
                self.assertEqual({c for _, c in self.F(res, item)}, {"CARRIER-NOT-ESTABLISHED"})
            else:
                self.assertEqual(
                    (item, self.S(res, item), self.codes(res, item)), (item, "PASS", [])
                )
        self.assertEqual(res["_item"]["history.migration"]["detail"], "claim=none")
        rc, text, _ = self.run_main(["check", "--repo", str(repo)])
        self.assertEqual(rc, 0)
        lines = text.split("\n")
        self.assertEqual(lines[0], "si-check rows=10 items=28")
        last = [ln for ln in lines if ln.strip()][-1]
        self.assertRegex(last, r"^overall=PASS rc=0 fingerprint=sha256:[0-9a-f]{64}$")
        self.assertNotIn("obs-draft:", text)
        self.assertIsNone(res["obs_draft"])
        for item in ITEMS21:
            self.assertTrue(any(ln.split(" ")[1:2] == [item] for ln in lines), item)

    def test_AT_001_1_E_1_time_and_tz(self):
        self.assertEqual(self.S(self.check(baseline()), "ledger.time_tz"), "PASS")
        decl = "<!-- si-ledger: tz=+08:00 -->"
        no_tz = {f"OBS-SI-{n:03d}" for n in (1, 2, 3, 4, 5, 6, 7, 8, 10)}
        cases = {}
        cases["one"] = lambda r: put(r, LEDGER, read(r, LEDGER).replace(decl + "\n", ""))
        cases["two"] = lambda r: put(
            r, LEDGER, read(r, LEDGER).replace(decl, "<!-- si-ledger: tz=+8:00 -->")
        )
        cases["three"] = lambda r: put(r, LEDGER, read(r, LEDGER).replace(decl, decl + "\n" + decl))
        for name, fn in cases.items():
            with self.subTest(case=name):
                repo = baseline()
                fn(repo)
                res = self.check(repo)
                got = self.F(res, "ledger.time_tz")
                if name == "one":
                    self.assertEqual(got, {(s, "TIME-NO-TZ") for s in no_tz})
                else:
                    self.assertIn(("-", "TZ-HEADER-MALFORMED"), got)
                    self.assertEqual({s for s, c in got if c == "TIME-NO-TZ"}, no_tz)
        with self.subTest(case="four"):
            repo = baseline()
            for n, v in (
                (3, "2026/10/19 02:30"),
                (4, "2026-02-30 10:00"),
                (5, "2026-10-19 24:00"),
                (6, "2026-10-19 02:30 +25:00"),
                (7, "2026-10-18 22:47～"),
            ):
                set_cell(repo, n, "時間", v)
            res = self.check(repo)
            self.assertEqual(
                self.F(res, "ledger.time_tz"), {(s, "TIME-FORMAT") for s in row_ids(3, 4, 5, 6, 7)}
            )

    def test_AT_001_1_E_2_required_fields_and_coordinates(self):
        for col in ("時間", "情境", "症狀", "證據座標", "分類", "嚴重度", "處置"):
            with self.subTest(col=col):
                repo = baseline()
                set_cell(repo, 3, col, "")
                res = self.check(repo)
                self.assertEqual(self.F(res, "row.required"), {("OBS-SI-003", "FIELD-EMPTY")})
                self.assertIn(col, res["_item"]["row.required"]["findings"][0]["detail"])
                for item in ("ledger.time_tz", "row.enums", "row.coordinates"):
                    self.assertNotIn("OBS-SI-003", {s for s, _ in self.F(res, item)}, item)
        with self.subTest(case="placeholders"):
            repo = baseline()
            for n, col, v in (
                (4, "症狀", "-"),
                (5, "情境", "—"),
                (6, "症狀", "TBD"),
                (7, "情境", "n/a"),
            ):
                set_cell(repo, n, col, v)
            res = self.check(repo)
            self.assertEqual(
                self.F(res, "row.required"), {(s, "FIELD-EMPTY") for s in row_ids(4, 5, 6, 7)}
            )
        with self.subTest(case="coords"):
            repo = baseline()
            for n, v in (
                (4, "本檔時間欄"),
                (5, "SD 第一支普查腳本實踩"),
                (6, "PRD 行數"),
                (7, "Claude Code 2.1.283；e.g. 見前述"),
                (8, UUID),
            ):
                set_cell(repo, n, "證據座標", v)
            res = self.check(repo)
            self.assertEqual(self.S(res, "row.coordinates"), "FAIL")
            self.assertEqual(
                self.F(res, "row.coordinates"), {(s, "COORD-NONE") for s in row_ids(4, 5, 6, 7, 8)}
            )
        with self.subTest(case="sid forms"):
            repo = baseline()
            set_cell(repo, 9, "證據座標", f"sid {UUID} line=12")
            set_cell(repo, 10, "證據座標", f"sid {UUID} seq: 3")
            res = self.check(repo)
            self.assertEqual(
                (self.S(res, "row.coordinates"), self.codes(res, "row.coordinates")), ("PASS", [])
            )

    def test_AT_001_1_E_3_enums(self):
        def run(edits):
            repo = baseline()
            for n, col, v in edits:
                set_cell(repo, n, col, v)
            return self.check(repo)

        res = run([(3, "分類", "Process"), (4, "分類", "other")])
        self.assertEqual(self.F(res, "row.enums"), {(s, "ENUM-CATEGORY") for s in row_ids(3, 4)})
        res = run(
            [(5, "嚴重度", "P0"), (6, "嚴重度", "p1"), (7, "嚴重度", "P5"), (8, "嚴重度", "高")]
        )
        self.assertEqual(
            self.F(res, "row.enums"), {(s, "ENUM-SEVERITY") for s in row_ids(5, 6, 7, 8)}
        )
        bad = ["TODO", "fixed", "fixed@", "fixed@xyz1234", "DEF-", "merged@OBS-SI", "Open"]
        res = run([(4 + i, "處置", v) for i, v in enumerate(bad)])
        self.assertEqual(
            self.F(res, "row.enums"), {(s, "DISP-ENUM") for s in row_ids(4, 5, 6, 7, 8, 9, 10)}
        )
        res = run(
            [
                (4, "處置", "deferred"),
                (5, "處置", "retired；沒有座標的依據"),
                (6, "處置", "decided"),
            ]
        )
        self.assertEqual(
            self.F(res, "row.enums"), {(s, "DISP-TEXT-MISSING") for s in row_ids(4, 5, 6)}
        )
        res = run([(3, "處置", "deferred；之後再看"), (4, "處置", "open；之後再看")])
        self.assertEqual(self.F(res, "row.enums"), {(s, "DISP-DEFER-LATER") for s in row_ids(3, 4)})
        self.assertEqual(self.S(self.check(baseline()), "row.enums"), "PASS")

    def test_AT_001_1_E_4_structure(self):
        with self.subTest(case="arity"):
            repo = baseline()
            cells3 = get_cell(repo, 3, "標記")
            set_cell(repo, 3, "標記", cells3)
            text = read(repo, LEDGER).split("\n")
            for i, ln in enumerate(text):
                if ln.startswith("| OBS-SI-003 |"):
                    text[i] = ln.rsplit(" | ", 1)[0] + " |"
                if ln.startswith("| OBS-SI-004 |"):
                    text[i] = ln + " extra |"
            put(repo, LEDGER, "\n".join(text))
            res = self.check(repo)
            self.assertEqual(
                self.F(res, "ledger.structure"), {(s, "ROW-ARITY") for s in row_ids(3, 4)}
            )
        with self.subTest(case="header"):
            repo = baseline()
            put(repo, LEDGER, read(repo, LEDGER).replace(" | 標記 |", " |", 1))
            res = self.check(repo)
            self.assertEqual(self.F(res, "ledger.structure"), {("-", "HEADER-COLS")})
        with self.subTest(case="id format"):
            repo = baseline()
            bad5, bad7 = "OBS-SI-" + "12", "OBS-SI-" + "0O7"
            text = read(repo, LEDGER)
            text = text.replace("| OBS-SI-005 |", f"| {bad5} |").replace(
                "| OBS-SI-007 |", f"| {bad7} |"
            )
            lines = text.split("\n")
            at = next(i for i, ln in enumerate(lines) if ln.startswith("| OBS-SI-006 |")) + 1
            lines.insert(at, line([""] * 8 + ["面=流程"]))
            put(repo, LEDGER, "\n".join(lines))
            res = self.check(repo)
            self.assertEqual(
                self.F(res, "ledger.structure"),
                {(bad5, "ROW-ID-FORMAT"), (bad7, "ROW-ID-FORMAT"), (f"L{at + 1}", "ROW-ID-FORMAT")},
            )
        with self.subTest(case="dup and order"):
            repo = baseline()
            text = read(repo, LEDGER).replace("| OBS-SI-008 |", "| OBS-SI-002 |")
            lines = text.split("\n")
            i9 = next(i for i, ln in enumerate(lines) if ln.startswith("| OBS-SI-009 |"))
            lines[i9], lines[i9 + 1] = lines[i9 + 1], lines[i9]
            put(repo, LEDGER, "\n".join(lines))
            res = self.check(repo)
            self.assertEqual(
                self.F(res, "ledger.structure"),
                {("OBS-SI-002", "ROW-ID-DUP"), ("OBS-SI-009", "ROW-ID-ORDER")},
            )
        with self.subTest(case="escaped pipe"):
            repo = baseline()
            set_cell(repo, 4, "症狀", r"基線\|症狀")
            set_cell(repo, 5, "症狀", "基線 `a|b` 症狀")
            res = self.check(repo)
            self.assertEqual(self.F(res, "ledger.structure"), {("OBS-SI-005", "ROW-ARITY")})
        with self.subTest(case="bom and header first"):
            repo = baseline()
            lines = read(repo, LEDGER).split("\n")
            hi = lines.index(HDR)
            rows_end = max(i for i, ln in enumerate(lines) if ln.startswith("| OBS-SI-"))
            new = lines[hi : rows_end + 1] + [""] + lines[: hi - 1]
            put(repo, LEDGER, "\ufeff" + "\n".join(new) + "\n")
            res = self.check(repo)
            self.assertEqual(
                (self.S(res, "ledger.structure"), self.S(res, "ledger.time_tz"), res["rows"]),
                ("PASS", "PASS", 10),
            )
        self.assertEqual(self.S(self.check(baseline()), "ledger.structure"), "PASS")

    def test_AT_001_1_E_5_bytes_ctrl_crlf_volume(self):
        def padded(n_bytes):
            repo = baseline()
            cur = next(
                ln for ln in read(repo, LEDGER).split("\n") if ln.startswith("| OBS-SI-003 |")
            )
            pad = n_bytes - len(cur.encode("utf-8"))
            set_cell(repo, 3, "症狀", get_cell(repo, 3, "症狀") + "x" * pad)
            return repo

        self.assertEqual(self.S(self.check(padded(700)), "row.bytes"), "PASS")
        self.assertEqual(
            self.F(self.check(padded(701)), "row.bytes"), {("OBS-SI-003", "ROW-BYTES-OVER")}
        )
        repo = baseline()
        set_cell(repo, 4, "症狀", "字" * 300)
        self.assertEqual(self.F(self.check(repo), "row.bytes"), {("OBS-SI-004", "ROW-BYTES-OVER")})
        repo = padded(701)
        set_params(repo, row_max_bytes=800)
        self.assertEqual(self.S(self.check(repo), "row.bytes"), "PASS")
        repo = baseline()
        for n, ch in ((5, "\t"), (6, "\x00"), (7, "\x1b"), (8, "\x7f")):
            set_cell(repo, n, "症狀", "基線" + ch + "症狀")
        set_cell(repo, 9, "症狀", "基線\r症狀")
        res = self.check(repo)
        self.assertEqual(self.S(res, "row.control_chars"), "FAIL")
        self.assertEqual(
            self.F(res, "row.control_chars"), {(s, "CTRL-CHAR") for s in row_ids(5, 6, 7, 8, 9)}
        )
        base = {i["id"]: i["status"] for i in self.check(baseline())["items"]}
        repo = baseline()
        text = read(repo, LEDGER)
        (repo / LEDGER).write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
        crlf = {i["id"]: i["status"] for i in self.check(repo)["items"]}
        self.assertEqual(crlf, base)
        size = len((baseline() / LEDGER).read_bytes())
        repo = baseline()
        size = len((repo / LEDGER).read_bytes())
        set_params(repo, ledger_warn_bytes=size, ledger_fail_bytes=size + 1)
        res = self.check(repo)
        self.assertEqual(
            (self.S(res, "ledger.volume"), self.codes(res, "ledger.volume")),
            ("PASS", [("-", "VOLUME-WARN")]),
        )
        warn = res["_item"]["ledger.volume"]["findings"][0]
        self.assertEqual(warn["level"], "warn")
        self.assertTrue(warn["detail"].startswith("[warn]"), warn["detail"])
        self.assertIn("\n  - VOLUME-WARN [warn] ", self.run_main(["check", "--repo", str(repo)])[1])
        set_params(repo, ledger_fail_bytes=size, ledger_warn_bytes=size - 1)
        res = self.check(repo)
        self.assertEqual(
            (self.S(res, "ledger.volume"), self.codes(res, "ledger.volume")),
            ("FAIL", [("-", "VOLUME-FAIL")]),
        )
        res = self.check(baseline())
        self.assertEqual(
            (self.S(res, "ledger.volume"), self.codes(res, "ledger.volume")), ("PASS", [])
        )

    def test_AT_001_1_E_6_fixed_sha(self):
        repo = baseline()
        self.assertEqual(self.S(self.check(repo), "row.fixed_sha"), "PASS")
        set_cell(repo, 4, "處置", "fixed@deadbee")
        res = self.check(repo)
        self.assertEqual(
            (self.S(res, "row.fixed_sha"), self.F(res, "row.fixed_sha")),
            ("FAIL", {("OBS-SI-004", "FIXED-SHA-UNRESOLVED")}),
        )
        repo = baseline()
        set_cell(
            repo, 5, "處置", "fixed@" + git_in(repo, "blob text", "hash-object", "-w", "--stdin")
        )
        self.assertEqual(
            self.F(self.check(repo), "row.fixed_sha"), {("OBS-SI-005", "FIXED-SHA-UNRESOLVED")}
        )
        repo = baseline()
        set_cell(repo, 6, "處置", "fixed@ABCDEF1")
        set_cell(repo, 7, "處置", "fixed@abc")
        res = self.check(repo)
        self.assertEqual(self.F(res, "row.enums"), {(s, "DISP-ENUM") for s in row_ids(6, 7)})
        self.assertEqual(self.S(res, "row.fixed_sha"), "PASS")
        repo = baseline()
        plain = new_dir("nogit")
        shutil.copytree(repo, plain, ignore=shutil.ignore_patterns(".git"))
        res = self.check(plain)
        ne = {i["id"] for i in res["items"] if i["status"] == "NE" and i["blocking"]}
        self.assertEqual(
            ne, {"row.fixed_sha", "ref.obs", "ref.carrier_families", "history.row_mutated"}
        )
        for item in ne:
            self.assertEqual({c for _, c in self.F(res, item)}, {"GIT-UNAVAILABLE"})
        self.assertEqual([i["id"] for i in res["items"] if i["status"] == "PASS"].__len__(), 17)
        self.assertEqual((res["overall"], res["rc"]), ("NE", 2))

    def test_AT_001_2_1_guard_face_exposure(self):
        repo = baseline()
        set_cell(repo, 3, "標記", "面=守衛;暴露=無;來源=工具;回報者=QA")
        set_cell(repo, 3, "嚴重度", "P1")
        set_cell(repo, 4, "標記", "面=守衛;來源=逐字稿;回報者=主控")
        set_cell(repo, 4, "嚴重度", "P2")
        set_cell(repo, 5, "標記", "面=守衛;暴露=無;來源=帳本;回報者=主控")
        set_cell(repo, 5, "嚴重度", "P3")
        set_cell(repo, 6, "標記", "面=產品;來源=人;回報者=掌舵者")
        set_cell(repo, 6, "嚴重度", "P1")
        res = self.check(repo)
        self.assertEqual(
            self.F(res, "row.markers"),
            {("OBS-SI-003", "GUARD-P12-NO-EXPOSURE"), ("OBS-SI-004", "GUARD-NO-EXPOSURE")},
        )
        self.assertEqual(self.S(res, "row.coordinates"), "PASS")
        with self.subTest("P2＋暴露=無"):
            repo = baseline()
            set_cell(repo, 9, "標記", "面=守衛;暴露=無;來源=代理;回報者=QA")
            self.assertEqual(
                self.F(self.check(repo), "row.markers"), {("OBS-SI-009", "GUARD-P12-NO-EXPOSURE")}
            )
        repo = baseline()
        set_cell(repo, 7, "標記", "來源=代理;回報者=SD")
        set_cell(repo, 8, "標記", "面=其他;來源=代理;回報者=SA")
        set_cell(repo, 3, "標記", "面=文件;暴露=d;來源=工具;回報者=QA")
        res = self.check(repo)
        self.assertEqual(
            self.F(res, "row.markers"),
            {
                ("OBS-SI-007", "MARK-FACE-MISSING"),
                ("OBS-SI-008", "MARK-VALUE"),
                ("OBS-SI-003", "MARK-VALUE"),
            },
        )
        self.assertEqual(self.S(self.check(baseline()), "row.markers"), "PASS")


class TestMigration(SiCase):
    def test_AT_001_3_1_chain_is_exempt(self):
        c = chain()
        res = self.check(c.repo)
        self.assertEqual((res["rc"], res["overall"]), (0, "PASS"))
        self.assertEqual(res["_item"]["history.migration"]["detail"], "claim=valid")
        for item in (
            "history.migration",
            "history.row_mutated",
            "ref.orig_notes",
            "row.enums",
            "row.markers",
            "row.provenance",
            "row.coordinates",
            "row.bytes",
        ):
            self.assertEqual(self.S(res, item), "PASS", item)
        m = re.search(r"orig=(@\S+)#(OBS-SI-\d+)", get_cell(c.repo, 4, "標記"))
        self.assertEqual(m.group(2), "OBS-SI-004")
        notes = read(c.repo, m.group(1)[1:]).split("## OBS-SI-004\n", 1)[1]
        old = git(c.repo, "show", f"{c.c0}:{LEDGER}")
        orig = next(ln for ln in old.split("\n") if ln.startswith("| OBS-SI-004 |"))[2:-2].split(
            " | "
        )[7]
        self.assertEqual(notes.strip(), orig)
        self.assertEqual(
            set(git(c.repo, "show", "--name-only", "--format=", c.m).split()), {LEDGER, NOTES}
        )
        self.assertEqual(
            set(git(c.repo, "show", "--name-only", "--format=", c.n).split()), {LEDGER, PARAMS}
        )
        self.assertNotEqual(c.m, c.n)
        self.assertIn(c.m[:7], read(c.repo, LEDGER))

    def test_AT_001_3_E_1_no_sha_not_exempt(self):
        c = chain()
        set_params(c.repo, migration_base_sha=None)
        commit_all(c.repo, "reset")
        variants = [c.repo]
        c2 = chain()
        set_params(c2.repo, migration_base_sha=KeyError)
        commit_all(c2.repo, "drop key")
        variants.append(c2.repo)
        for repo in variants:
            with self.subTest(repo=repo.name):
                res = self.check(repo)
                self.assertEqual(
                    (self.S(res, "history.migration"), res["_item"]["history.migration"]["detail"]),
                    ("PASS", "claim=none"),
                )
                self.assertEqual(self.S(res, "history.row_mutated"), "FAIL")
                self.assertEqual(
                    self.F(res, "history.row_mutated"),
                    {(s, "ROW-MUTATED") for s in row_ids(1, 2, 3, 4)},
                )
                for f in res["_item"]["history.row_mutated"]["findings"]:
                    self.assertIn("掌舵者", f["detail"])
                    self.assertIn("cause=changed", f["detail"])
                    self.assertIn(f"commit={c.m[:7]}", f["detail"])
                self.assertEqual((res["overall"], res["rc"]), ("FAIL", 1))

    def test_AT_001_3_E_2_confirm_row_variants(self):
        for mode in (
            "no-decided",
            "no-sha",
            "no-sid",
            "no-line",
            "wrong-sha",
            "not-decided",
            "valid",
            "wrong-quote",
        ):
            with self.subTest(mode=mode):
                c = chain("cf", mode)
                res = self.check(c.repo)
                if mode in ("valid", "wrong-quote"):  # 後者＝引言故意寫錯：P0 只驗存在與格式
                    self.assertEqual(
                        (self.S(res, "history.migration"), self.S(res, "history.row_mutated")),
                        ("PASS", "PASS"),
                    )
                    self.assertEqual(res["_item"]["history.migration"]["detail"], "claim=valid")
                    continue
                self.assertEqual(self.S(res, "history.migration"), "FAIL")
                self.assertEqual(self.F(res, "history.migration"), {("-", "MIG-CONFIRM-MISSING")})
                self.assertEqual(self.S(res, "history.row_mutated"), "FAIL")
                self.assertTrue(
                    row_ids(1, 2, 3, 4) <= {s for s, _ in self.F(res, "history.row_mutated")}
                )

    def test_AT_001_3_E_3_invalid_sha(self):
        cases = [
            ("zzzz", "MIG-SHA-FORMAT"),
            ("short", "MIG-SHA-FORMAT"),
            ("nosuch", "MIG-SHA-UNRESOLVED"),
            ("blob", "MIG-SHA-UNRESOLVED"),
            ("orphan", "MIG-SHA-NOT-ANCESTOR"),
            ("upper", "MIG-SHA-FORMAT"),
        ]
        for kind, code in cases:
            with self.subTest(code=code, kind=kind):
                c = chain()
                if kind == "short":
                    value = c.m[:12]
                elif kind == "upper":
                    value = c.m.upper()
                elif kind == "blob":
                    value = git_in(c.repo, "b", "hash-object", "-w", "--stdin")
                elif kind == "orphan":
                    tree = git_in(c.repo, "", "mktree")
                    value = git(c.repo, "commit-tree", "-m", "orphan", tree)
                elif kind == "nosuch":
                    value = "a" * 40
                else:
                    value = kind
                set_params(c.repo, migration_base_sha=value)
                res = self.check(c.repo)
                self.assertEqual(self.S(res, "history.migration"), "FAIL")
                self.assertEqual(self.F(res, "history.migration"), {("migration_base_sha", code)})
                self.assertEqual(self.S(res, "history.row_mutated"), "FAIL")
                self.assertTrue(
                    row_ids(1, 2, 3, 4) <= {s for s, _ in self.F(res, "history.row_mutated")}
                )
                self.assertEqual((res["overall"], res["rc"]), ("FAIL", 1))

    def test_AT_001_3_E_4_orig_rules(self):
        c = chain()
        (c.repo / NOTES).unlink()
        res = self.check(c.repo)
        self.assertEqual(
            (self.S(res, "ref.orig_notes"), self.F(res, "ref.orig_notes")),
            ("FAIL", {("OBS-SI-004", "ORIG-NOTES-MISSING")}),
        )
        c = chain()
        put(c.repo, NOTES, read(c.repo, NOTES).replace("## OBS-SI-004", "## " + obs_id(2)))
        self.assertEqual(
            self.F(self.check(c.repo), "ref.orig_notes"), {("OBS-SI-004", "ORIG-NOTES-ANCHOR")}
        )
        c = chain()
        set_cell(c.repo, 4, "標記", "面=流程;來源=代理;回報者=SA;orig=@" + NOTES + "#OBS-SI-003")
        self.assertEqual(
            self.F(self.check(c.repo), "ref.orig_notes"), {("OBS-SI-004", "ORIG-NOTES-ANCHOR")}
        )
        # R18 (c)：逃出 repo 的路徑視同不存在。誘餌檔真的放在逃出後會解析到的地方，
        # 判準一旦放行就會 PASS（只斷言「不存在的路徑報不存在」鑑別不出任何一條）。
        c = chain()
        outside = c.repo.parent / "orig_outside.md"
        for decoy in (outside, c.repo / "orig_inside.md"):
            decoy.write_bytes(b"## OBS-SI-004\n")
        drive = PureWindowsPath("C:/orig_outside.md").as_posix()  # 受測的就是磁碟機代號形態
        if os.name == "posix":  # POSIX 上 `C:/x` 是 repo 內的相對路徑；同一帳本兩平台判決須相同
            put(c.repo, drive, "## OBS-SI-004\n")
        absolute = outside.as_posix()
        rooted = absolute[len(outside.drive) :]
        paths = {
            "dotdot": "../orig_outside.md",
            "absolute": absolute,
            "rooted": rooted,
            "rooted-backslash": rooted.replace("/", "\\"),
            "drive-letter": drive,
            "inside": "orig_inside.md",
        }
        for name, rel in paths.items():
            with self.subTest(orig=name):
                self.assertNotRegex(rel, r"[\s#]")
                set_cell(c.repo, 4, "標記", f"面=流程;來源=代理;回報者=SA;orig=@{rel}#OBS-SI-004")
                res = self.check(c.repo)
                miss = {("OBS-SI-004", "ORIG-NOTES-MISSING")}
                want = ("PASS", set()) if name == "inside" else ("FAIL", miss)
                self.assertEqual(
                    (self.S(res, "ref.orig_notes"), self.F(res, "ref.orig_notes")), want
                )
        c = chain()
        new = _crow(6, "症狀6", "open", '面=流程;來源=代理;回報者=SA;orig="x"')
        append_row(c.repo, new)
        commit_all(c.repo, "late orig")
        res = self.check(c.repo)
        self.assertEqual(
            (self.S(res, "history.migration"), self.F(res, "history.migration")),
            ("FAIL", {("OBS-SI-006", "ORIG-OUTSIDE-MIGRATION")}),
        )
        c = chain()
        set_cell(c.repo, 2, "標記", "面=流程;來源=代理;回報者=SA;orig=自由文字")
        res = self.check(c.repo)
        self.assertEqual(
            (self.S(res, "row.markers"), self.F(res, "row.markers")),
            ("FAIL", {("OBS-SI-002", "MARK-ORIG-FORMAT")}),
        )
        c = chain()
        set_cell(c.repo, 3, "標記", r'面=流程;來源=代理;回報者=SA;orig="a \"q\" b \\"')
        self.assertEqual(self.S(self.check(c.repo), "row.markers"), "PASS")


class TestMarksAndProvenance(SiCase):
    """AT-002：標記與出處判準（tools/lib/selfimproving/rows.py 的 row.markers、row.provenance）。"""

    def test_AT_002_1_1_marks(self):
        edits = {
            "a": (3, lambda m: m + ";外部衍生=否", "MARK-VALUE"),
            "b": (4, lambda m: m + ";外部衍生=", "MARK-SYNTAX"),
            "c": (5, lambda m: m + ";foo=1", "MARK-UNKNOWN-KEY"),
            "d": (6, lambda m: m + ";面=產品", "MARK-SYNTAX"),
            "e": (7, lambda m: m + ";守衛", "MARK-SYNTAX"),
            "f": (8, lambda m: m.replace("回報者=SA", "回報者=SA;SD"), "MARK-SYNTAX"),
        }
        repo = baseline()
        want = set()
        for n, fn, code in edits.values():
            set_cell(repo, n, "標記", fn(get_cell(repo, n, "標記")))
            want.add((f"OBS-SI-{n:03d}", code))
        self.assertEqual(self.F(self.check(repo), "row.markers"), want)
        repo = baseline()
        set_cell(repo, 9, "標記", "")
        res = self.check(repo)
        self.assertEqual(self.F(res, "row.markers"), {("OBS-SI-009", "MARK-FACE-MISSING")})
        self.assertEqual(
            self.F(res, "row.provenance"),
            {("OBS-SI-009", "SOURCE-MISSING"), ("OBS-SI-009", "REPORTER-MISSING")},
        )
        repo = baseline()
        add_mark(repo, 3, "orig=自由文字")
        add_mark(repo, 4, r'orig="a \"q\" b \\"')
        add_mark(repo, 5, "orig=@docs/x.md#OBS-SI-001")
        self.assertEqual(
            self.F(self.check(repo), "row.markers"), {("OBS-SI-003", "MARK-ORIG-FORMAT")}
        )
        self.assertEqual(self.S(self.check(baseline()), "row.markers"), "PASS")

    def test_AT_002_2_1_provenance(self):
        def strip(n, key):
            repo = repos[n]
            marks = [p for p in get_cell(repo, n, "標記").split(";") if not p.startswith(key + "=")]
            set_cell(repo, n, "標記", ";".join(marks))

        repos = {n: baseline() for n in (3, 4)}
        strip(3, "來源")
        self.assertEqual(
            self.F(self.check(repos[3]), "row.provenance"), {("OBS-SI-003", "SOURCE-MISSING")}
        )
        strip(4, "回報者")
        self.assertEqual(
            self.F(self.check(repos[4]), "row.provenance"), {("OBS-SI-004", "REPORTER-MISSING")}
        )
        repo = baseline()
        set_cell(repo, 5, "標記", "面=產品;來源=;回報者=SA")
        res = self.check(repo)
        self.assertEqual(self.F(res, "row.provenance"), {("OBS-SI-005", "SOURCE-MISSING")})
        self.assertIn(("OBS-SI-005", "MARK-SYNTAX"), self.F(res, "row.markers"))
        repo = baseline()
        set_cell(repo, 6, "標記", "面=產品;來源=代理;回報者=")
        res = self.check(repo)
        self.assertEqual(self.F(res, "row.provenance"), {("OBS-SI-006", "REPORTER-MISSING")})
        self.assertIn(("OBS-SI-006", "MARK-SYNTAX"), self.F(res, "row.markers"))
        repo = baseline()
        set_cell(repo, 7, "標記", "面=產品;來源=網路;回報者=SA")
        self.assertEqual(
            self.F(self.check(repo), "row.provenance"), {("OBS-SI-007", "SOURCE-VALUE")}
        )
        for src in ("人", "代理", "工具", "逐字稿", "帳本"):
            with self.subTest(source=src):
                repo = baseline()
                set_cell(repo, 8, "標記", f"面=產品;來源={src};回報者=SA")
                self.assertEqual(self.S(self.check(repo), "row.provenance"), "PASS")
        self.assertEqual(self.S(self.check(baseline()), "row.provenance"), "PASS")


class TestScopeAndSop(SiCase):
    def test_AT_003_1_1_no_resident_mechanism(self):
        forbidden = [
            r"schtasks",
            r"launchctl",
            r"crontab",
            r"ScheduleWakeup",
            r"CronCreate",
            r"Register-ScheduledTask",
            r"apscheduler",
            r"threading\.Timer",
            r"sched\.scheduler",
            r"time\.sleep",
            r"while\s+True",
            r"daemon\s*=\s*True",
            r"os\.fork",
            r"signal\.alarm",
        ]

        def hits(text):
            return [p for p in forbidden if re.search(p, text)]

        samples = [
            "x schtasks y",
            "launchctl",
            "crontab -l",
            "ScheduleWakeup(",
            "CronCreate",
            "Register-ScheduledTask",
            "apscheduler",
            "threading.Timer(1)",
            "sched.scheduler()",
            "time.sleep(1)",
            "while  True:",
            "daemon = True",
            "os.fork()",
            "signal.alarm(1)",
        ]
        for s, p in zip(samples, forbidden):
            self.assertEqual(hits(s)[:1], [p], s)
        self.assertEqual(hits("print('clean')"), [])
        for src in si_sources():
            self.assertEqual(hits(src.read_bytes().decode("utf-8")), [], src.name)
        for verb in ("decide", "promote"):  # P1 已實作 status／prop-new，改選仍未實作的動詞
            rc, out, _ = self.run_main([verb])
            self.assertEqual((rc, out), (3, ""))
        settings = (ROOT / ".claude/settings.json").read_bytes().decode("utf-8")
        self.assertNotIn("selfimproving", settings.lower())
        sop = sop_text()
        self.assertEqual(sop_startup_problems(sop), [])
        for key in ("掌舵者指令", "第二次", "P≤2", "再開症狀", "容量事件"):
            self.assertNotEqual(sop_startup_problems(sop.replace(key, "")), [], key)
        for label in ("(a)", "(b)", "(c)", "(d)", "(e)"):
            self.assertNotEqual(sop_startup_problems(sop.replace(label, "")), [], label)
        for needles in (("日曆", "版本號", "覆蓋度", "每 N 輪"), ("si status",)):
            self.assertNotEqual(sop_startup_problems(drop_lines(sop, *needles)), [], needles)
        for frag in ("視窗開場", "收尾"):
            self.assertNotEqual(sop_startup_problems(sop.replace(frag, "")), [], frag)

    def test_AT_003_2_1_below_floor_is_ne(self):
        def at(rows, min_rows=10):
            def mut(ctx):
                ctx.params["min_obs_rows"] = min_rows

            return make_valid_repo(new_dir("fl"), rows=rows, mutate=mut)

        res = self.check(at(9))
        self.assertEqual(
            (self.S(res, "ledger.vacuity"), res["_item"]["ledger.vacuity"]["blocking"]),
            ("NE", True),
        )
        self.assertEqual(self.F(res, "ledger.vacuity"), {("-", "LEDGER-BELOW-FLOOR")})
        self.assertEqual((res["overall"], res["rc"]), ("NE", 2))
        res = self.check(at(0))
        self.assertEqual((res["rows"], res["overall"], res["rc"]), (0, "NE", 2))
        self.assertEqual(self.F(res, "ledger.vacuity"), {("-", "LEDGER-BELOW-FLOOR")})
        self.assertEqual(self.S(self.check(at(9, 9)), "ledger.vacuity"), "PASS")
        res = self.check(at(10))
        self.assertEqual((self.S(res, "ledger.vacuity"), res["rc"]), ("PASS", 0))
        sop = sop_text()
        self.assertEqual(sop_line_problems(sop, "r3"), [])
        self.assertNotEqual(sop_line_problems(drop_lines(sop, "無事件", "通過"), "r3"), [])

    def test_AT_003_3_1_output_count_not_a_reason(self):
        sop = sop_text()
        self.assertEqual(sop_line_problems(sop, "r4"), [])
        self.assertNotEqual(sop_line_problems(drop_lines(sop, "產出數量", "T1"), "r4"), [])
        rc, out, _ = self.run_main(["check", "--help"])
        self.assertEqual(rc, 0)
        self.assertEqual(
            set(re.findall(r"--[a-z][a-z-]*", out)),
            {"--repo", "--ledger", "--params", "--json", "--help"},
        )

    def test_AT_004_2_1_real_defect_is_def(self):
        sop = sop_text()
        self.assertEqual(sop_line_problems(sop, "r5"), [])
        self.assertNotEqual(sop_line_problems(drop_lines(sop, "DEF-<id>", "真缺陷"), "r5"), [])

    def test_AT_029_1_1_friction_entry(self):
        sop = sop_text()
        self.assertEqual(sop_roles_problems(sop), [])
        self.assertEqual(sop_r8_problems(sop), [])
        cap = sop_section(sop, "擷取者")
        for frag in ("文字交卷", "流程摩擦"):
            self.assertNotEqual(sop_roles_problems(sop.replace(frag, "")), [], frag)
        self.assertIn("文字交卷", cap)
        self.assertNotEqual(sop_r8_problems(drop_lines(sop, "流程摩擦", "OBS-SI-004")), [])

    def test_AT_029_2_1_loop_self(self):
        sop = sop_text()
        self.assertEqual(sop_line_problems(sop, "r7"), [])
        self.assertNotEqual(sop_line_problems(drop_lines(sop, "loop-self", "轉交", "T1"), "r7"), [])
        globs = json.loads(REAL_PARAMS.read_bytes().decode("utf-8"))["non_evolvable_globs"]
        for g in (
            "docs/06_quality/SelfImproving_Protocol/**",
            "docs/01_requirements/SelfImproving_PRD.md",
            "tools/selfimproving.py",
            "tools/lib/selfimproving/**",
        ):
            self.assertIn(g, globs)

    def test_AT_032_1_1_sop_skeleton(self):
        sop = sop_text()
        self.assertEqual(sop_roles_problems(sop), [])
        cap = sop_section(sop, "擷取者")
        self.assertTrue(has_line(cap, "外部衍生=是", "不得單獨"))
        for role in ("歸因者", "提案者", "審查者", "凍結者"):
            self.assertIn("P1 定稿", sop_section(sop, role))
        frags = [
            "HEAD=<sha>",
            "文字交卷",
            "流程摩擦",
            "python tools/session_resume_planner.py --pace",
            "Omitted",
            "OBS-SI-033",
            "OBS-SI-038",
            "python tools/selfimproving.py check",
            "來源",
            "回報者",
        ]
        for frag in frags:
            self.assertNotEqual(sop_roles_problems(sop.replace(frag, "")), [], frag)
        self.assertNotEqual(sop_roles_problems(drop_lines(sop, "外部衍生=是", "不得單獨")), [])
        self.assertNotEqual(sop_roles_problems(sop.replace("## 凍結者", "## 其他")), [])


class TestReferences(SiCase):
    """AT-004-1：引用判準（tools/lib/selfimproving/refs.py 的 ref.* 各項）。"""

    def test_AT_004_1_1_existing_references(self):
        repo = baseline()
        set_cell(repo, 4, "處置", def_id(2))
        set_cell(repo, 5, "處置", def_id(3))
        set_cell(repo, 6, "處置", def_id(4))
        add_mark(repo, 8, f"rel={OBS_ARCH}")
        put(repo, "docs/notes/refs.md", "提及 OBS-SI-001 與 OBS-SI-005\n")
        res = self.check(repo)
        for item in ("ref.def", "ref.obs", "ref.orig_notes"):
            self.assertEqual((self.S(res, item), self.codes(res, item)), ("PASS", []), item)

    def test_AT_004_1_E_1_dangling_obs(self):
        x, y = obs_id(801), obs_id(802)

        def case(fn):
            repo = baseline()
            fn(repo)
            return self.check(repo)

        singles = {
            "disp": lambda r: set_cell(r, 3, "處置", f"merged@{x}"),
            "symptom": lambda r: set_cell(r, 4, "症狀", f"提及 {x}"),
            "other file": lambda r: put(r, "docs/notes/readme.md", f"{x} 與 OBS-SI-001\n"),
            "notes heading": lambda r: put(r, NOTES, f"# n\n\n## {x}\n"),
            "rel": lambda r: add_mark(r, 5, f"rel={x}"),
        }
        for name, fn in singles.items():
            with self.subTest(case=name):
                res = case(fn)
                self.assertEqual(
                    (self.S(res, "ref.obs"), self.F(res, "ref.obs")),
                    ("FAIL", {(x, "OBS-REF-DANGLING")}),
                )
                self.assertRegex(res["_item"]["ref.obs"]["findings"][0]["detail"], r"[\w./-]+:\d+")

        def both(r):
            set_cell(r, 4, "症狀", f"提及 {x} 與 {y}")
            put(r, "docs/notes/readme.md", f"{x}\n")

        res = case(both)
        self.assertEqual(self.F(res, "ref.obs"), {(x, "OBS-REF-DANGLING"), (y, "OBS-REF-DANGLING")})
        detail = next(f["detail"] for f in res["_item"]["ref.obs"]["findings"] if f["subject"] == x)
        self.assertEqual(len(re.findall(r"[\w./-]+:\d+", detail)), 2)

        def seven(r):
            set_cell(r, 4, "症狀", f"提及 {x}")
            for i in range(1, 7):
                put(r, f"docs/notes/m{i}.md", f"{x}\n")

        res = case(seven)
        self.assertEqual(self.codes(res, "ref.obs"), [(x, "OBS-REF-DANGLING")])
        detail = res["_item"]["ref.obs"]["findings"][0]["detail"]
        self.assertEqual(len(re.findall(r"[\w./-]+:\d+", detail)), 5)
        self.assertIn("…+2", detail)

    def test_AT_004_1_E_2_dangling_def(self):
        repo = baseline()
        set_cell(repo, 4, "處置", def_id(77))
        for n, k in ((5, 1), (6, 2), (7, 3), (8, 4)):
            set_cell(repo, n, "處置", def_id(k))
        res = self.check(repo)
        self.assertEqual(
            (self.S(res, "ref.def"), self.F(res, "ref.def")),
            ("FAIL", {("OBS-SI-004", "DEF-REF-DANGLING")}),
        )
        repo = baseline()
        for p in (repo / "docs/06_quality").glob("AutoSDD_*.md"):
            p.unlink()
        res = self.check(repo)
        self.assertEqual(
            (self.S(res, "ref.def"), res["_item"]["ref.def"]["blocking"]), ("NE", True)
        )
        self.assertEqual({c for _, c in self.F(res, "ref.def")}, {"SOURCE-UNAVAILABLE"})
        self.assertEqual(self.S(self.check(baseline()), "ref.def"), "PASS")

    def test_AT_004_1_E_3_carriers_not_established(self):
        res = self.check(baseline())
        item = res["_item"]["ref.carrier_families"]
        self.assertEqual((item["status"], item["blocking"]), ("NE", False))
        self.assertEqual({f["code"] for f in item["findings"]}, {"CARRIER-NOT-ESTABLISHED"})
        self.assertIn("families=PROP-SI", item["findings"][0]["detail"])
        self.assertIn("count=1", item["findings"][0]["detail"])
        self.assertEqual(res["rc"], 0)
        repo = baseline()
        fams = ("ATT", "DEC", "APP", "MEA", "RUN")
        put(repo, "docs/notes/x.md", "\n".join(f"{f}-SI-" + "456" for f in fams) + "\n")
        res = self.check(repo)
        detail = res["_item"]["ref.carrier_families"]["findings"][0]["detail"]
        self.assertIn("families=APP-SI,ATT-SI,DEC-SI,MEA-SI,PROP-SI,RUN-SI", detail)
        self.assertIn("count=6", detail)
        self.assertEqual(res["rc"], 0)
        self.assertFalse([f for i in res["items"] for f in i["findings"] if f["level"] == "fail"])
        repo = baseline()
        set_cell(repo, 8, "處置", "open")
        self.assertEqual(self.S(self.check(repo), "ref.carrier_families"), "PASS")


class TestHistory(SiCase):
    """AT-004-3：歷史判準（tools/lib/selfimproving/history.py 的 history.* 各項）。"""

    def test_AT_004_3_1_legal_evolution(self):
        c = chain()
        repo = c.repo
        set_cell(repo, 1, "處置", "deferred；再開症狀：同一症狀第二次出現")
        commit_all(repo, "K1")
        k1 = git(repo, "rev-parse", "HEAD")
        append_row(repo, _crow(6, "症狀6", "open", "面=流程;來源=代理;回報者=SA"))
        commit_all(repo, "K2")
        k2 = git(repo, "rev-parse", "HEAD")
        append_row(
            repo, _crow(7, "症狀7", "open", "面=流程;來源=代理;回報者=SA;rel=corrects:OBS-SI-002")
        )
        commit_all(repo, "K3")
        k3 = git(repo, "rev-parse", "HEAD")
        for sha in (k1, k2, k3):
            self.assertEqual(git(repo, "show", "--name-only", "--format=", sha), LEDGER)
        text = read(repo, LEDGER).replace(" | ", "  |  ")
        (repo / LEDGER).write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
        res = self.check(repo)
        self.assertEqual(
            (self.S(res, "history.row_mutated"), self.codes(res, "history.row_mutated")),
            ("PASS", []),
        )
        self.assertEqual((res["overall"], res["rc"]), ("PASS", 0))
        sop = sop_text()
        self.assertEqual(sop_r9_problems(sop), [])
        self.assertNotEqual(
            sop_r9_problems(drop_lines(sop, "追加", "rel=corrects:", "ROW-MUTATED")), []
        )
        self.assertNotEqual(sop_r9_problems(sop.replace("終值", "")), [])

    def test_AT_004_3_E_1_in_place_rewrites(self):
        c = chain()
        repo = c.repo
        shorts = []

        def step(msg):
            commit_all(repo, msg)
            shorts.append(git(repo, "rev-parse", "HEAD")[:7])

        set_cell(repo, 2, "症狀", "症狀2 改")
        step("D1")
        set_cell(repo, 3, "處置", "retired；依據 docs/c.md:3")
        step("D2")
        put(
            repo,
            LEDGER,
            "\n".join(
                ln for ln in read(repo, LEDGER).split("\n") if not ln.startswith("| OBS-SI-004 |")
            ),
        )
        step("D3")
        put(repo, LEDGER, read(repo, LEDGER).replace("| OBS-SI-005 |", "| OBS-SI-009 |"))
        step("D4")
        set_cell(repo, 1, "處置", "decided：已處理")
        set_cell(repo, 1, "情境", "情境1 改")
        step("D5")
        res = self.check(repo)
        found = res["_item"]["history.row_mutated"]["findings"]
        self.assertEqual(self.S(res, "history.row_mutated"), "FAIL")
        self.assertEqual(
            [f["subject"] for f in found],
            [f"OBS-SI-{n:03d}" for n in (2, 3, 4, 5, 1)],
        )
        causes = ["changed", "changed", "deleted", "deleted", "changed"]
        for f, cause, short in zip(found, causes, shorts):
            self.assertIn(f"cause={cause}", f["detail"])
            self.assertIn(f"commit={short}", f["detail"])
            self.assertIn("掌舵者", f["detail"])
        self.assertNotIn("OBS-SI-009", {f["subject"] for f in found})
        self.assertEqual(self.S(res, "history.migration"), "PASS")
        self.assertEqual((res["overall"], res["rc"]), ("FAIL", 1))

    def test_AT_004_3_E_2_worktree_rewrites(self):
        repo = chain().repo
        set_cell(repo, 2, "症狀", "症狀2 改")
        res = self.check(repo)
        self.assertEqual(self.F(res, "history.row_mutated"), {("OBS-SI-002", "ROW-MUTATED")})
        self.assertIn(
            "commit=WORKTREE", res["_item"]["history.row_mutated"]["findings"][0]["detail"]
        )
        repo = chain().repo
        set_cell(repo, 1, "處置", "deferred；再開症狀：甲")
        self.assertEqual(self.S(self.check(repo), "history.row_mutated"), "PASS")
        set_cell(repo, 1, "處置", "retired；依據 docs/c.md:3")
        self.assertEqual(self.S(self.check(repo), "history.row_mutated"), "PASS")
        repo = chain().repo
        put(
            repo,
            LEDGER,
            "\n".join(
                ln for ln in read(repo, LEDGER).split("\n") if not ln.startswith("| OBS-SI-003 |")
            ),
        )
        res = self.check(repo)
        self.assertEqual(self.F(res, "history.row_mutated"), {("OBS-SI-003", "ROW-MUTATED")})
        self.assertIn("cause=deleted", res["_item"]["history.row_mutated"]["findings"][0]["detail"])

    def test_AT_004_3_E_3_no_history_and_outside(self):
        repo = make_valid_repo(new_dir("late"), late_ledger=True)
        res = self.check(repo)
        item = res["_item"]["history.row_mutated"]
        self.assertEqual(
            (item["status"], item["detail"], item["findings"]), ("PASS", "no-history", [])
        )
        self.assertEqual(res["_item"]["history.migration"]["detail"], "claim=none")
        self.assertEqual(res["rc"], 0)
        repo = baseline()
        outside = new_dir("out")
        outside.mkdir()
        (outside / "ledger.md").write_bytes((repo / LEDGER).read_bytes())
        res = self.check(repo, "--ledger", str(outside / "ledger.md"))
        item = res["_item"]["history.row_mutated"]
        self.assertEqual((item["status"], item["blocking"]), ("NE", True))
        self.assertEqual(self.F(res, "history.row_mutated"), {("-", "SOURCE-UNAVAILABLE")})
        self.assertEqual((res["rows"], self.S(res, "row.enums")), (10, "PASS"))
        self.assertEqual((res["overall"], res["rc"]), ("NE", 2))


def fingerprint_of(repo: Path, prm: dict) -> tuple[str, dict]:
    """獨立重算 tools/lib/selfimproving/params.py 的 fingerprint（協定目錄雜湊），作為測試預言。"""
    pdir = repo / "docs/06_quality/SelfImproving_Protocol"
    man = sorted(
        (
            p.relative_to(pdir).as_posix(),
            hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        )
        for p in pdir.rglob("*")
        if p.is_file() and not p.name.startswith(".")
    )
    manifest = hashlib.sha256(json.dumps(man, ensure_ascii=False).encode("utf-8")).hexdigest()
    parts = {
        "check_rules_rev": prm["check_rules_rev"],
        "manifest": manifest,
        "metrics_rev": prm["metrics_rev"],
    }
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest(), parts


class TestCli(SiCase):
    """AT-030：命令列契約（tools/selfimproving.py 經 tools/lib/selfimproving/check.py 輸出）。"""

    def _red(self) -> Path:
        repo = baseline()
        set_cell(repo, 3, "分類", "Process")
        return repo

    ITEM_RE = re.compile(
        r"^(PASS|FAIL|NE) ([a-z_]+\.[a-z_]+)(?: (blocking|nonblocking))?(?: # (.*))?$"
    )
    FINDING_RE = re.compile(r"^  (\S+) ([A-Z][A-Z0-9-]+)(?: (.*))?$")

    def assert_text_matches_json(self, repo: Path) -> None:
        """R3 行文法逐行解析文字形態，並與 `--json` 逐項相等：rc、各項 status、NE 項的
        blocking／nonblocking 字樣、各項 finding 的 (subject, code) 集合（含縮排的 finding 行）。"""
        rc, text, _ = self.run_main(["check", "--repo", str(repo)])
        res = self.check(repo)
        lines = text.split("\n")
        self.assertEqual(lines.pop(), "", "文字形態以 LF 結尾")
        self.assertEqual(lines[0], f"si-check rows={res['rows']} items={len(res['items'])}")
        at = next(i for i, ln in enumerate(lines) if ln.startswith("overall="))
        self.assertEqual(
            lines[at], f"overall={res['overall']} rc={res['rc']} fingerprint={res['fingerprint']}"
        )
        self.assertEqual((rc, len(lines[at + 1 :])), (res["rc"], 2 if rc else 0))
        got = []
        for ln in lines[1:at]:
            found = self.FINDING_RE.match(ln)
            if found:
                self.assertTrue(got, ln)
                got[-1][3].add(found.groups()[:2])
                continue
            m = self.ITEM_RE.match(ln)
            self.assertTrue(m, ln)
            got.append((m.group(1), m.group(2), m.group(3), set()))
        want = [
            (
                it["status"],
                it["id"],
                ("blocking" if it["blocking"] else "nonblocking") if it["status"] == "NE" else None,
                {(f["subject"], f["code"]) for f in it["findings"]},
            )
            for it in res["items"]
        ]
        self.assertEqual(got, want)

    def test_AT_030_1_1_output_contract(self):
        green, red = baseline(), self._red()
        rc_g, text_g, _ = self.run_main(["check", "--repo", str(green)])
        rc_r, text_r, _ = self.run_main(["check", "--repo", str(red)])
        self.assertEqual((rc_g, rc_r), (0, 1))
        res = self.check(red)
        self.assertEqual((res["overall"], res["rc"]), ("FAIL", 1))
        tail = text_r.split("\n")
        at = next(i for i, ln in enumerate(tail) if ln.startswith("overall="))
        self.assertEqual(tail[at + 1], "obs-draft:")
        self.assertTrue(tail[at + 2].startswith("| OBS-SI-"))
        self.assertEqual(len([ln for ln in tail if ln.startswith("| OBS-SI-")]), 1)
        plain = new_dir("nogit")
        shutil.copytree(green, plain, ignore=shutil.ignore_patterns(".git"))
        for name, repo in (("green", green), ("red", red), ("no-git", plain)):
            with self.subTest(text_form=name):
                self.assert_text_matches_json(repo)
        self.assertNotIn("\x1b", text_r)
        self.assertEqual(self.F(res, "row.enums"), {("OBS-SI-003", "ENUM-CATEGORY")})
        self.assertIn("分類", res["_item"]["row.enums"]["findings"][0]["detail"])
        decoy = new_dir("decoy")
        (decoy / "docs/06_quality/SelfImproving_Protocol").mkdir(parents=True)
        put(decoy, LEDGER, HDR + "\n" + SEP + "\n")
        put(decoy, PARAMS, "{}\n")
        env = genv()
        env["PYTHONIOENCODING"] = "cp950"
        script = str(TOOLS / "selfimproving.py")
        cp = subprocess.run(
            [sys.executable, script, "check", "--repo", str(red), "--json"],
            cwd=decoy,
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(cp.returncode, 1)
        sub = json.loads(cp.stdout.decode("utf-8"))
        detail = next(i for i in sub["items"] if i["id"] == "row.enums")["findings"][0]["detail"]
        self.assertIn("分類", detail)
        self.assertNotIn(b"Traceback", cp.stderr)
        cp = subprocess.run(
            [
                sys.executable,
                script,
                "check",
                "--repo",
                str(green),
                "--ledger",
                LEDGER,
                "--params",
                PARAMS,
                "--json",
            ],
            cwd=decoy,
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(cp.returncode, 0)
        self.assertEqual(json.loads(cp.stdout.decode("utf-8"))["rows"], 10)
        pairs = json.loads(cp.stdout.decode("utf-8"), object_pairs_hook=list)
        self.assertEqual(
            [k for k, _ in pairs],
            ["overall", "rc", "fingerprint", "fingerprint_parts", "rows", "items", "obs_draft"],
        )
        top = dict(pairs)
        self.assertEqual(
            [k for k, _ in top["fingerprint_parts"]], ["manifest", "metrics_rev", "check_rules_rev"]
        )
        self.assertEqual(
            [k for k, _ in top["items"][0]], ["id", "status", "blocking", "detail", "findings"]
        )
        raw = self.run_main(["check", "--repo", str(red), "--json"])[1]
        obj = json.loads(raw, object_pairs_hook=list)
        finding = next(dict(i)["findings"][0] for i in dict(obj)["items"] if dict(i)["findings"])
        self.assertEqual([k for k, _ in finding], ["subject", "code", "level", "detail"])

    def test_AT_030_1_E_1_usage_errors(self):
        repo = baseline()
        tmp = new_dir("e")
        tmp.mkdir()
        afile = tmp / "a_file"
        afile.write_bytes(b"x")
        bad_ledger, bad_json, bad_arr = tmp / "l.md", tmp / "p1.json", tmp / "p2.json"
        bad_ledger.write_bytes(b"\xff\xfe")
        bad_json.write_bytes(b"not json")
        bad_arr.write_bytes(b"[]")
        calls = [
            [],
            ["decide"],
            ["check", "--bogus"],
            ["check", "--repo", str(tmp / "missing")],
            ["check", "--repo", str(afile)],
            ["check", "--repo", str(repo), "--ledger", "no/such.md"],
            ["check", "--repo", str(repo), "--params", "no/such.json"],
            ["check", "--repo", str(repo), "--ledger", str(bad_ledger)],
            ["check", "--repo", str(repo), "--params", str(bad_json)],
            ["check", "--repo", str(repo), "--params", str(bad_arr)],
            ["check", "--repo", str(repo), "--ledger", str(tmp)],
        ]
        for argv in calls:
            with self.subTest(argv=argv[2:]):
                rc, out, err = self.run_main(argv)
                self.assertEqual((rc, out), (3, ""))
                self.assertTrue(err.strip())
        for argv in (["--help"], ["check", "--help"]):
            rc, out, _ = self.run_main(argv)
            self.assertEqual(rc, 0)
            self.assertIn("check", out)
        rc, out, _ = self.run_main(["check", "--help"])
        for flag in ("--repo", "--ledger", "--params", "--json"):
            self.assertIn(flag, out)

    def test_AT_030_2_1_purity(self):
        green = baseline()
        red = baseline()
        set_cell(red, 4, "症狀", f"提及 {obs_id(801)}")
        put(red, LEDGER, read(red, LEDGER).replace("<!-- si-ledger: tz=+08:00 -->\n", ""))

        def digest(repo):
            return {
                p.relative_to(repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(repo.rglob("*"))
                if p.is_file() and ".git" not in p.relative_to(repo).parts
            }

        def porcelain(repo):
            return git(repo, "status", "--porcelain")

        before = {r: (digest(r), porcelain(r)) for r in (green, red)}
        calls, popens, shells = [], [], []
        real_run, real_popen = subprocess.run, subprocess.Popen

        def rec_run(*a, **k):
            calls.append((a, k))
            return real_run(*a, **k)

        def rec_popen(*a, **k):
            popens.append(1)
            return real_popen(*a, **k)

        def rec_shell(*a, **k):  # os.system／os.popen 繞過 subprocess，記錄器看不到，須另行攔截
            shells.append(a)
            raise OSError("check 不得經 os.system／os.popen 起行程")

        other = new_dir("other")
        init_repo(other)
        results = {}
        for polluted in (False, True):
            env = (
                {"GIT_DIR": str(other / ".git"), "GIT_INDEX_FILE": str(other / "nope")}
                if polluted
                else {}
            )
            for name, repo in (("green", green), ("red", red)):
                with (
                    mock.patch.dict(os.environ, env),
                    mock.patch.object(subprocess, "run", rec_run),
                    mock.patch.object(subprocess, "Popen", rec_popen),
                    mock.patch.object(os, "system", rec_shell),
                    mock.patch.object(os, "popen", rec_shell),
                ):
                    for extra in ((), ("--json",)):
                        rc, out, _ = self.run_main(["check", "--repo", str(repo), *extra])
                        txt = (
                            re.sub(r"obs-draft:\n.*\n", "", out)
                            if not extra
                            else re.sub(r'"obs_draft": ".*?"}', '"obs_draft": null}', out)
                        )
                        results[(polluted, name, extra)] = (
                            rc,
                            txt
                            if not extra
                            else re.sub(r"\d{4}-\d\d-\d\d \d\d:\d\d [+-]\d\d:\d\d", "T", out),
                        )
        self.assertEqual(shells, [])
        for key, val in results.items():
            if key[0]:
                self.assertEqual(val, results[(False, *key[1:])], key)
        for repo in (green, red):
            self.assertEqual((digest(repo), porcelain(repo)), before[repo])
        self.assertTrue(calls)
        self.assertEqual(len(popens), len(calls))
        for a, k in calls:
            argv = a[0]
            self.assertEqual(Path(argv[0]).stem.lower(), "git")
            self.assertEqual(argv[1], "-C")
            self.assertIn(Path(argv[2]).resolve(), (green.resolve(), red.resolve()))
            self.assertFalse(k.get("shell"))
            self.assertGreater(k["timeout"], 0)
            self.assertEqual((k["encoding"], k["errors"]), ("utf-8", "replace"))
            env = k["env"]
            self.assertIsInstance(env, dict)
            self.assertEqual(set(_STRIP) & set(env), set())
            self.assertEqual(env["GIT_OPTIONAL_LOCKS"], "0")
        banned = {"socket", "urllib", "http", "requests", "ftplib", "smtplib", "asyncio"}
        write_re = re.compile(
            r"write_text|write_bytes|\.mkdir\(|os\.remove|os\.unlink|os\.rename|os\.replace"
            r"|shutil\.|open\([^)]*['\"][wax]b?\+?['\"]"
        )
        self.assertTrue(write_re.search("p.write_text(x)") and write_re.search("open(f, 'w')"))
        self.assertIsNone(write_re.search("print('x')"))
        shell_re = re.compile(r"os\.(?:system|popen)\b")
        self.assertTrue(shell_re.search("os.system('x')") and shell_re.search("os.popen(c)"))
        self.assertIsNone(shell_re.search("print('x')"))
        from test_selfimproving_capability import CAPABILITY  # P1：靜態段只掃入口加登記為 ro 的檔

        ro_files = sorted(n for n, kind in CAPABILITY.items() if kind == "ro")
        entry_and_ro = [TOOLS / "selfimproving.py", *(TOOLS / "lib" / "selfimproving" / n
                                                       for n in ro_files)]
        for src in entry_and_ro:
            text = src.read_bytes().decode("utf-8")
            self.assertIsNone(write_re.search(text), src.name)
            self.assertIsNone(shell_re.search(text), src.name)
            for node in ast.walk(ast.parse(text)):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    mods = [node.module.split(".")[0]]  # 相對 import（level>0）是套件內部，不在此列
                for mod in mods:
                    ok = mod in sys.stdlib_module_names or mod in ("_stdio_utf8", "lib")
                    self.assertTrue(ok, f"{src.name} imports {mod}")
                    self.assertNotIn(mod, banned)

    def test_AT_030_3_1_fingerprint(self):
        repo = baseline()
        r1 = self.run_main(["check", "--repo", str(repo), "--json"])[1]
        r2 = self.run_main(["check", "--repo", str(repo), "--json"])[1]
        self.assertEqual(r1, r2)
        base = json.loads(r1)
        self.assertRegex(base["fingerprint"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(
            set(base["fingerprint_parts"]), {"manifest", "metrics_rev", "check_rules_rev"}
        )
        self.assertGreaterEqual(base["fingerprint_parts"]["check_rules_rev"], 1)
        prm = {"check_rules_rev": base["fingerprint_parts"]["check_rules_rev"], "metrics_rev": 1}
        fp, parts = fingerprint_of(repo, prm)
        self.assertEqual(fp, base["fingerprint"])
        self.assertEqual(parts["manifest"], base["fingerprint_parts"]["manifest"])

        def fp_after(fn):
            r = baseline()
            fn(r)
            return self.check(r)

        crlf = fp_after(
            lambda r: [
                (r / rel).write_bytes((r / rel).read_bytes().replace(b"\n", b"\r\n"))
                for rel in (PARAMS, "docs/06_quality/SelfImproving_Protocol/metrics.md")
            ]
        )
        self.assertEqual(crlf["fingerprint"], base["fingerprint"])
        changed = [
            fp_after(lambda r: set_params(r, w_evt=3)),
            fp_after(lambda r: set_params(r, metrics_rev=2)),
            fp_after(lambda r: put(r, "docs/06_quality/SelfImproving_Protocol/extra.md", "x\n")),
        ]
        fps = {c["fingerprint"] for c in changed} | {base["fingerprint"]}
        self.assertEqual(len(fps), 4)
        self.assertEqual(changed[1]["fingerprint_parts"]["metrics_rev"], 2)
        same = fp_after(lambda r: set_cell(r, 3, "症狀", "基線症狀 改"))
        self.assertEqual(same["fingerprint"], base["fingerprint"])

    def test_AT_030_3_2_obs_draft(self):
        repo = baseline()
        set_cell(repo, 3, "分類", "Process")
        set_cell(repo, 4, "處置", "TODO")
        res = self.check(repo)
        self.assertEqual(res["rc"], 1)
        draft = res["obs_draft"]
        self.assertEqual(len(draft.split("\n")), 1)
        cells = [c.strip() for c in draft.strip()[1:-1].split("|")]
        self.assertEqual(len(cells), 9)
        self.assertEqual(cells[0], "OBS-SI-011")
        self.assertRegex(cells[1], r"^\d{4}-\d\d-\d\d \d\d:\d\d [+-]\d\d:\d\d$")
        self.assertEqual(
            (cells[2], cells[5], cells[6], cells[7], cells[8]),
            ("si check（自動草稿）", "bug", "P3", "open", "面=流程;來源=工具;回報者=si-check"),
        )
        self.assertIn("rc=1", cells[3])
        self.assertIn("row.enums", cells[3])
        self.assertIn("`python tools/selfimproving.py check`", cells[4])
        self.assertIn("判準指紋 sha256:", cells[4])
        text_form = self.run_main(["check", "--repo", str(repo)])[1]
        text_draft = text_form.split("obs-draft:\n", 1)[1].strip()
        strip_t = lambda s: re.sub(r"\d{4}-\d\d-\d\d \d\d:\d\d [+-]\d\d:\d\d", "T", s)  # noqa: E731
        self.assertEqual(strip_t(text_draft), strip_t(draft))
        (repo / LEDGER).write_bytes(
            (read(repo, LEDGER).rstrip("\n") + "\n" + draft + "\n").encode("utf-8")
        )
        after = self.check(repo)
        subjects = {f["subject"] for i in after["items"] for f in i["findings"]}
        self.assertNotIn("OBS-SI-011", subjects)
        self.assertIn(("OBS-SI-003", "ENUM-CATEGORY"), self.F(after, "row.enums"))
        self.assertIn(("OBS-SI-004", "DISP-ENUM"), self.F(after, "row.enums"))
        many = baseline()
        set_cell(many, 3, "時間", "bad")
        set_cell(many, 4, "處置", "TODO")
        set_cell(many, 5, "證據座標", "無座標")
        set_cell(many, 6, "症狀", "x" * 800)
        set_cell(many, 7, "症狀", "基線\t症狀")
        set_cell(many, 8, "症狀", f"提及 {obs_id(801)}")
        res = self.check(many)
        bad = [i["id"] for i in res["items"] if i["status"] != "PASS"]
        self.assertGreaterEqual(len(bad), 6)
        d2 = res["obs_draft"]
        self.assertLessEqual(len(d2.encode("utf-8")), 700)
        self.assertIn(f"…等 {len(bad)} 項", d2)
        self.assertIn("、".join(bad[:5]), d2)
        self.assertNotIn(bad[5], d2.split("…等")[0])
        green = self.run_main(["check", "--repo", str(baseline())])
        self.assertNotIn("obs-draft:", green[1])


class TestParams(SiCase):
    """AT-031：協定參數判準（tools/lib/selfimproving/params.py 的 params.* 各項）。"""

    def test_AT_031_1_1_real_params(self):
        raw = REAL_PARAMS.read_bytes()
        self.assertEqual(si_params.params_file_problems(raw), [])
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r", raw)
        self.assertTrue(raw.endswith(b"\n"))
        prm = json.loads(raw.decode("utf-8"))
        self.assertEqual(list(prm), sorted(prm, key=lambda k: k.encode("utf-8")))
        self.assertTrue(set(KEYS23) <= set(prm))
        for k in KEYS23:
            v = prm[k]
            if k in ("max_touch_ratio", "cap_frac"):
                self.assertTrue(0 < v <= 1, k)
            elif k == "migration_base_sha":
                self.assertTrue(v is None or re.fullmatch(r"[0-9a-f]{40}", v))
            elif k.endswith("_globs"):
                self.assertTrue(v and all(isinstance(x, str) for x in v), k)
            else:
                self.assertTrue(isinstance(v, int) and not isinstance(v, bool) and v >= 1, k)
        repo = baseline()
        put(repo, PARAMS, raw.decode("utf-8"))
        put(
            repo,
            "docs/01_requirements/SelfImproving_PRD.md",
            (ROOT / "docs/01_requirements/SelfImproving_PRD.md").read_bytes().decode("utf-8"),
        )
        put(repo, "CLAUDE.md", (ROOT / "CLAUDE.md").read_bytes().decode("utf-8"))
        res = self.check(repo)
        for item in ("params.keys", "params.globs", "params.coupling"):
            self.assertEqual((item, self.S(res, item), self.codes(res, item)), (item, "PASS", []))

    def test_AT_031_1_E_1_missing_keys(self):
        ne_map = {
            "row_max_bytes": ["row.bytes"],
            "min_obs_rows": ["ledger.vacuity"],
            "ledger_warn_bytes": ["ledger.volume", "params.coupling"],
            "ledger_fail_bytes": ["ledger.volume", "params.coupling"],
            "w_opp": ["params.coupling"],
            "w_min": ["params.coupling"],
            "non_evolvable_globs": ["params.globs"],
        }
        base = {i["id"]: i["status"] for i in self.check(baseline())["items"]}
        for key in KEYS23:
            with self.subTest(key=key):
                repo = baseline()
                set_params(repo, **{key: KeyError})
                res = self.check(repo)
                self.assertEqual(
                    (self.S(res, "params.keys"), self.F(res, "params.keys")),
                    ("FAIL", {(key, "PARAM-MISSING")}),
                )
                for item in ne_map.get(key, []):
                    self.assertEqual(self.S(res, item), "NE", item)
                    self.assertTrue(res["_item"][item]["blocking"])
                    self.assertEqual({c for _, c in self.F(res, item)}, {"SOURCE-UNAVAILABLE"})
                if key == "migration_base_sha":
                    self.assertEqual(
                        (
                            self.S(res, "history.migration"),
                            res["_item"]["history.migration"]["detail"],
                        ),
                        ("PASS", "claim=none"),
                    )
                skip = {"params.keys", *ne_map.get(key, [])}
                for item in ITEMS21:
                    if item not in skip:
                        self.assertEqual(self.S(res, item), base[item], item)

    def test_AT_031_1_E_2_glob_consistency(self):
        def run(fn):
            repo = baseline()
            fn(repo)
            return self.check(repo)

        def globs(repo):
            return json.loads(read(repo, PARAMS))["non_evolvable_globs"]

        mismatch = {
            "missing": lambda r: set_params(r, non_evolvable_globs=globs(r)[1:]),
            "extra": lambda r: set_params(r, non_evolvable_globs=globs(r) + ["zzz/**"]),
            "dup": lambda r: set_params(r, non_evolvable_globs=globs(r) + [globs(r)[0]]),
            "claude shrink": lambda r: put(
                r, "CLAUDE.md", MINI_CLAUDE.replace("{aa,bb,cc}", "{aa,bb}")
            ),
            "prd swap": lambda r: put(
                r,
                "docs/01_requirements/SelfImproving_PRD.md",
                MINI_PRD.replace("`docs/r.md`", "`docs/s.md`"),
            ),
        }
        for name, fn in mismatch.items():
            with self.subTest(case=name):
                res = run(fn)
                self.assertEqual(
                    (self.S(res, "params.globs"), self.F(res, "params.globs")),
                    ("FAIL", {("non_evolvable_globs", "GLOBS-SET-MISMATCH")}),
                )
        self.assertEqual(
            self.S(
                run(lambda r: set_params(r, non_evolvable_globs=globs(r)[::-1])), "params.globs"
            ),
            "PASS",
        )
        gone = {
            "prd line": lambda r: put(r, "docs/01_requirements/SelfImproving_PRD.md", "# x\n"),
            "claude": lambda r: (r / "CLAUDE.md").unlink(),
        }
        for name, fn in gone.items():
            with self.subTest(case=name):
                res = run(fn)
                self.assertEqual(
                    (self.S(res, "params.globs"), res["_item"]["params.globs"]["blocking"]),
                    ("NE", True),
                )
                self.assertEqual(
                    {c for _, c in self.F(res, "params.globs")}, {"SOURCE-UNAVAILABLE"}
                )
        self.assertEqual(self.S(self.check(baseline()), "params.globs"), "PASS")

    def test_AT_031_1_E_3_coupling(self):
        def run(**kw):
            repo = baseline()
            set_params(repo, **kw)
            return self.check(repo)

        res = run(w_opp=4, w_min=5)
        self.assertEqual(
            (self.S(res, "params.coupling"), self.F(res, "params.coupling")),
            ("FAIL", {("w_opp", "COUPLING-W-OPP-LT-W-MIN")}),
        )
        for kw in ({"w_opp": 5, "w_min": 5}, {"w_opp": 6, "w_min": 5}):
            self.assertNotIn(
                ("w_opp", "COUPLING-W-OPP-LT-W-MIN"), self.F(run(**kw), "params.coupling")
            )
        for kw in (
            {"ledger_warn_bytes": 262144, "ledger_fail_bytes": 262144},
            {"ledger_warn_bytes": 300000, "ledger_fail_bytes": 262144},
        ):
            self.assertEqual(
                self.F(run(**kw), "params.coupling"),
                {("ledger_warn_bytes", "COUPLING-WARN-GE-FAIL")},
            )
        self.assertNotIn(
            ("ledger_warn_bytes", "COUPLING-WARN-GE-FAIL"),
            self.F(run(ledger_warn_bytes=100, ledger_fail_bytes=101), "params.coupling"),
        )
        res = run(w_opp="5")
        self.assertEqual(self.S(res, "params.keys"), "FAIL")
        self.assertEqual(
            (self.S(res, "params.coupling"), res["_item"]["params.coupling"]["blocking"]),
            ("NE", True),
        )
        self.assertEqual({c for _, c in self.F(res, "params.coupling")}, {"SOURCE-UNAVAILABLE"})
        self.assertEqual(self.S(self.check(baseline()), "params.coupling"), "PASS")

    def test_AT_031_1_E_4_types(self):
        repo = baseline()
        bad = {
            "w_evt": "2",
            "w_n": 20.5,
            "w_min": True,
            "migration_base_sha": 123,
            "non_evolvable_globs": "x",
            "spec_body_globs": ["a", 1],
        }
        set_params(repo, **bad)
        res = self.check(repo)
        self.assertEqual(self.S(res, "params.keys"), "FAIL")
        self.assertEqual(self.F(res, "params.keys"), {(k, "PARAM-TYPE") for k in bad})
        self.assertEqual(len(res["_item"]["params.keys"]["findings"]), 6)
        repo = baseline()
        set_params(repo, foo="bar")
        res = self.check(repo)
        self.assertEqual((self.S(res, "params.keys"), self.codes(res, "params.keys")), ("PASS", []))

    def test_AT_031_1_E_5_ranges(self):
        repo = baseline()
        bad = {
            "max_touch_ratio": 2,
            "cap_frac": 0,
            "row_max_bytes": 0,
            "metrics_rev": 0,
            "spec_body_globs": [],
            "non_evolvable_globs": [],
        }
        set_params(repo, **bad)
        res = self.check(repo)
        self.assertEqual(self.F(res, "params.keys"), {(k, "PARAM-RANGE") for k in bad})
        self.assertEqual(len(res["_item"]["params.keys"]["findings"]), 6)
        repo = baseline()
        set_params(repo, max_touch_ratio=1, cap_frac=0.01, row_max_bytes=1, metrics_rev=1)
        self.assertEqual(self.S(self.check(repo), "params.keys"), "PASS")

    def test_AT_031_2_1_metrics_verbatim(self):
        prd = (
            (ROOT / "docs/01_requirements/SelfImproving_PRD.md")
            .read_bytes()
            .decode("utf-8")
            .replace("\r\n", "\n")
        )
        met = REAL_METRICS.read_bytes().decode("utf-8").replace("\r\n", "\n")
        self.assertEqual(si_params.metrics_problems(prd, met), [])
        row_re = re.compile(r"^\| \*\*(?:結果指標|資訊欄)\*\*[^|]* \| \*\*M([1-5]) ")
        rows = [(m.group(1), ln) for ln in prd.split("\n") if (m := row_re.match(ln))]
        self.assertEqual([r[0] for r in rows], list("12345"))
        lines = met.split("\n")
        pos = [lines.index(ln) for _, ln in rows]
        self.assertEqual(pos, sorted(pos))
        m3 = rows[2][1]
        self.assertNotEqual(
            si_params.metrics_problems(prd, met.replace(m3, m3.replace("M3", "M9", 1))), []
        )
        swapped = list(lines)
        i2, i4 = lines.index(rows[1][1]), lines.index(rows[3][1])
        swapped[i2], swapped[i4] = swapped[i4], swapped[i2]
        self.assertNotEqual(si_params.metrics_problems(prd, "\n".join(swapped)), [])
        start = next(i for i, ln in enumerate(lines) if ln.strip().startswith("**M1 判定細則**"))
        self.assertNotEqual(
            si_params.metrics_problems(prd, "\n".join(lines[: start + 1] + lines[start + 2 :])), []
        )


if __name__ == "__main__":
    unittest.main()
