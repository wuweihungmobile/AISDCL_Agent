#!/usr/bin/env python3
"""tools/refresh_nightly_anchor.py — ONBOARDING §7 表③ 的 nightly 錨機械回填（DEF-200-506）。

把表③-b（排程軌 job 層結論）與錨的 `nightly-red`／`nightly-run`／`nightly-checked-at`
三欄，從「人每 14 天跑一次回填 SOP」改成「本機 nightly 現查 GitHub、寫回工作樹」。

使用：
  python tools/refresh_nightly_anchor.py               # 唯讀預覽：gh 現查，不落檔
  python tools/refresh_nightly_anchor.py --write       # 寫回 ONBOARDING.md
  python tools/refresh_nightly_anchor.py --check       # 離線：判準驗工作樹
  python tools/refresh_nightly_anchor.py --check-head  # 離線：判準驗 HEAD（pre-push／CI）

三條設計約束，WHY 與否決方案見證據檔：
  CrossPlatform_R208_NightlyAnchor_Mechanical_Backfill_Evidence.md
  1. 輸出是 GitHub 狀態的純函式、零本機時鐘——兩台機器各自回填的結果逐位元相同，
     同內容的 commit 才能乾淨合併。
  2. 取不到證據（gh 缺席／未登入／網路／JSON 形態不符／job 對不到）＝不寫檔、rc=3。
  3. `NIGHTLY_MAX_AGE_DAYS` 與 `cloud_fail_open_jobs()` 的單一居所在本檔；CI 判準 import。
"""
from __future__ import annotations

import datetime
import json
import re
import shutil
import subprocess
import sys
from collections import namedtuple
from collections.abc import Callable, Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cli_flags  # noqa: E402  # 未知旗標 rc=2 fail-loud 的 SSOT
import _stdio_utf8  # noqa: E402,F401  # 非 UTF-8 終端 print(✅/❌) 防崩潰保護
from lib.ci_liveness import JOB_FAIL_OPEN_RE  # noqa: E402  # job 層 fail-open 正則 SSOT

ANCHOR_MARK = "cloud-ci-status:"
FIELD_RED, FIELD_RUN, FIELD_CHECKED = "nightly-red", "nightly-run", "nightly-checked-at"
RED_NONE, RED_SEP = "none", ","
#: 排程軌是週頻（兩支 compat-CI 的 cron）⇒ 14 天＝最多兩個週期沒有 completed run。取更大
#: 會容許「一個月前的證據」還算新鮮；取更小會在正常輪距內製造噪音。
NIGHTLY_MAX_AGE_DAYS = 14
#: 兩個事件都取樣：job 的 `if:` 兩者皆放行，而處置指令 `gh workflow run` 產生的是
#: `workflow_dispatch` run——只查 schedule 會讓處置永遠無效（解不開的死鎖）。
RUN_EVENTS = ("schedule", "workflow_dispatch")
GH_TIMEOUT_S = 30
EXIT_OK, EXIT_RED, EXIT_USAGE, EXIT_EVIDENCE = 0, 1, _cli_flags.UNKNOWN_FLAG_RC, 3
REPO = Path(__file__).resolve().parents[1]
ONBOARDING = REPO / "ONBOARDING.md"
WORKFLOWS_DIR = REPO / ".github" / "workflows"

_MODES = ("--write", "--check", "--check-head")
_KNOWN_ARGV = (*_MODES, "--help", "-h")
_NIGHTLY_KEYS = (FIELD_RED, FIELD_RUN, FIELD_CHECKED)
_RUN_FIELDS = "databaseId,headSha,conclusion,createdAt,event,status"
#: `jobs:` 底下 job id 恰 2 空白縮排、其內文縮排 ≥4；step 層更深，刻意不收。
_JOB_ID_LINE_RE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
_NAME_LINE_RE = re.compile(r"^    name:\s*(.+?)\s*$")
_QUOTED_NAME_RE = re.compile(r"""^(["'])(.*?)\1(?:\s+#.*)?$""")
#: 只認 `'schedule'`：只在 `workflow_dispatch` 放行的 job 沒有 cron，過期帶對它無意義。
_SCHEDULE_IF_RE = re.compile(r"^    if:.*github\.event_name\s*==\s*'schedule'")
_FIELD_RE = re.compile(r"(\w[\w-]*)=([^\s]+)")  # 與 CI 判準同一份欄位文法
_TABLE_HEAD_RE = re.compile(r"^> \| job id \| workflow \|")
_TABLE_ROW_RE = re.compile(
    r"^> \| `([^`]+)` \| ([\w.-]+\.yml) \| ([^|]*) \| `(\d{6,})` ／ `([0-9a-f]{6,})` \|")
ADVICE_COMMIT = (
    "處置：工作樹的 ONBOARDING.md 已是新的（本機 nightly 已回填、只是沒被 commit 帶走）"
    "⇒ `git add ONBOARDING.md` 併入 commit，再 push")
ADVICE_WRITE = (
    "處置：先跑 `python tools/refresh_nightly_anchor.py --write`（需 gh 已登入）；"
    f"若它回報無 completed run 或取樣 run 已逾 {NIGHTLY_MAX_AGE_DAYS} 天＝排程通道停擺，"
    "先 `gh workflow run windows-compat-ci.yml`／`gh workflow run macos-compat-ci.yml` "
    "補跑、等 completed 後再 `--write`；寫好後把 ONBOARDING.md 納入下一個 commit"
    "（`--check-head` 驗的是 HEAD，只改工作樹不夠）")

#: created＝aware UTC datetime；run＝Run；Row＝表③-b 一列的解析結果。
Run = namedtuple("Run", "id created sha conclusion event")
JobResult = namedtuple("JobResult", "name conclusion")
Sample = namedtuple("Sample", "wf job display run job_conclusion")
Anchor = namedtuple("Anchor", "red run checked")
Row = namedtuple("Row", "job wf conclusion run_id")


class EvidenceError(Exception):
    """取不到／讀不懂 GitHub 或 git 的證據 ⇒ rc=3，零寫入。"""


class LayoutError(Exception):
    """ONBOARDING／workflow 版面不符 ⇒ rc=1，點名缺什麼。"""


# ─────────────────────────── 純函式：workflow 掃描 ───────────────────────────
def cloud_fail_open_jobs(workflows_dir: Path) -> list[str]:
    """`<workflow>.yml:<job>` — 帶 **job 層** `continue-on-error: true` 的 job（現查）。

    立案沿革（R76-03）搬至 Guard_Line_History_2.md〈R194 淨減法搬遷〉§91。  round-label-ok

    掃描面現查而非寫死：寫死清單在「某支 workflow 新增一個 fail-open job」那天靜默縮面
    （同 `push_triggered_workflows` 的紀律）。
    """
    found: list[str] = []
    for f in sorted(workflows_dir.glob("*.yml")):
        in_jobs, job = False, None
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("jobs:"):
                in_jobs, job = True, None
                continue
            if line and not line[0].isspace():
                in_jobs, job = False, None
                continue
            if not in_jobs:
                continue
            m = _JOB_ID_LINE_RE.match(line)
            if m:
                job = m.group(1)
            elif job and JOB_FAIL_OPEN_RE.match(line):
                found.append(f"{f.name}:{job}")
    return sorted(set(found))


def job_block(workflow_text: str, job_id: str) -> list[str]:
    """該 job 在 `jobs:` 下的內文行；找不到回 `[]`。純文字掃描、不用 yaml。"""
    out: list[str] = []
    in_jobs = inside = False
    for line in workflow_text.splitlines():
        if line.startswith("jobs:"):
            in_jobs, inside = True, False
        elif line and not line[0].isspace():
            in_jobs = inside = False
        elif in_jobs:
            m = _JOB_ID_LINE_RE.match(line)
            if m:
                inside = m.group(1) == job_id
            elif inside:
                out.append(line)
    return out


def job_display_name(workflow_text: str, job_id: str, wf: str = "workflow") -> str:
    """GitHub 顯示名（`gh run view --json jobs` 的 `.jobs[].name`）；無 `name:` 回 job id。"""
    block = job_block(workflow_text, job_id)
    if not block:
        raise EvidenceError(f"{wf} 找不到 job {job_id}（workflow 檔與 fail-open 掃描不一致？）")
    for line in block:
        m = _NAME_LINE_RE.match(line)
        if not m:
            continue
        q = _QUOTED_NAME_RE.match(m.group(1))
        name = q.group(2) if q else re.sub(r"\s+#.*$", "", m.group(1))
        if "${{" in name:
            raise EvidenceError(
                f"{wf} 的 job {job_id} 的 name 含 ${{{{ }}}} 運算式，無法靜態解出 GitHub 顯示名"
                " ⇒ 本工具只支援字面 name；請改成字面值或擴充 job_display_name")
        return name
    return job_id


def scheduled_fail_open_jobs(workflows_dir: Path) -> list[str]:
    """表③-b 的列集合：fail-open 且 job 層 `if:` 放行 `schedule` 事件者（今日＝兩支）。"""
    out: list[str] = []
    for item in cloud_fail_open_jobs(workflows_dir):
        wf, job = item.split(":", 1)
        text = (workflows_dir / wf).read_text(encoding="utf-8", errors="replace")
        if any(_SCHEDULE_IF_RE.match(ln) for ln in job_block(text, job)):
            out.append(item)
    return out


# ─────────────────────────── 純函式：gh 回應解析 ───────────────────────────
def _load_json(raw: str, what: str) -> object:
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise EvidenceError(f"gh 輸出不是合法 JSON（{what}）：{raw[:80]!r}") from exc


def parse_runs(raw: str) -> list[Run]:
    """`gh run list --json …` 的 stdout → completed 的 Run 列表（縱深防禦：再濾一次）。"""
    data = _load_json(raw, "run list")
    if not isinstance(data, list):
        raise EvidenceError("gh 輸出不是 JSON 陣列（run list）")
    runs: list[Run] = []
    for item in data:
        for key in _RUN_FIELDS.split(","):
            if not isinstance(item, dict) or key not in item:
                raise EvidenceError(f"gh JSON 缺欄位 {key}（run list）")
        if item["status"] != "completed":
            continue
        try:
            made = datetime.datetime.fromisoformat(str(item["createdAt"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise EvidenceError(f"gh JSON 的 createdAt 不是 ISO8601：{item['createdAt']}") from exc
        made = made.replace(tzinfo=datetime.UTC) if made.tzinfo is None else made
        runs.append(Run(int(item["databaseId"]), made.astimezone(datetime.UTC),
                        str(item["headSha"]), str(item["conclusion"] or ""), str(item["event"])))
    return runs


def newest_run(runs: Sequence[Run]) -> Run | None:
    return max(runs, key=lambda r: (r.created, r.id), default=None)


def parse_jobs(raw: str) -> list[JobResult]:
    """`gh run view --json jobs` 的 stdout → `.jobs[]` 的 (name, conclusion)。"""
    data = _load_json(raw, "run view")
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        raise EvidenceError("gh JSON 缺欄位 jobs（run view）")
    out: list[JobResult] = []
    for job in jobs:
        for key in ("name", "conclusion"):
            if not isinstance(job, dict) or key not in job:
                raise EvidenceError(f"gh JSON 缺欄位 {key}（run view）")
        out.append(JobResult(str(job["name"]), str(job["conclusion"] or "unknown")))
    return out


def job_conclusion(jobs: Sequence[JobResult], display: str, run_id: int,
                   wf: str = "<workflow 檔名>") -> str:
    """唯一同名 job 的 conclusion；0 筆或 ≥2 筆一律 fail-loud（不猜）。"""
    hits = [j for j in jobs if j.name == display]
    if len(hits) == 1:
        return hits[0].conclusion
    if hits:
        raise EvidenceError(f"run {run_id} 的 jobs 內有 {len(hits)} 個同名「{display}」⇒ 無法對應")
    names = "／".join(j.name for j in jobs)
    raise EvidenceError(
        f"run {run_id} 的 jobs 內找不到「{display}」（實得：{names}）⇒ workflow 的 job name 與 "
        f"GitHub 顯示名不一致，或該 run 早於這個 job 的新增。處置：`gh workflow run {wf}` 補跑一次")


# ─────────────────────────── 純函式：錨與表③-b ───────────────────────────
def anchor_from(samples: Sequence[Sample]) -> Anchor:
    """錨三欄＝取樣的純函式：零本機時鐘；run／時刻取兩支取樣 run 中**較早**者。"""
    if not samples:
        raise LayoutError("無任何排程 fail-open job 可取樣（workflows 掃描面空？）")
    red = RED_SEP.join(sorted(f"{s.wf}:{s.job}" for s in samples if s.job_conclusion != "success"))
    first = min((s.run for s in samples), key=lambda r: (r.created, r.id))
    return Anchor(red or RED_NONE, first.id, first.created.isoformat())


def render_rows(samples: Sequence[Sample]) -> list[str]:
    """表③-b 資料列：固定句型、零人工散文；格內的 `|` 以全形 `｜` 取代以免破表。"""
    rows: list[str] = []
    for s in sorted(samples, key=lambda x: (x.wf, x.job)):
        verdict = "✅ success" if s.job_conclusion == "success" else f"🔴 {s.job_conclusion}"
        note = (f"{s.run.event} run（建立 {s.run.created.isoformat()}）；"
                f"run 層 {s.run.conclusion or '（無）'}；job 層「{s.display}」{s.job_conclusion}")
        rows.append(f"> | `{s.job}` | {s.wf} | {verdict} | `{s.run.id}` ／ `{s.run.sha[:8]}` "
                    f"| {note.replace('|', '｜')} |")
    return rows


def _table_span(lines: Sequence[str]) -> tuple[int, int]:
    """表③-b 資料列的 `[start, end)`：表頭只認前兩格，其下須是分隔行。"""
    heads = [i for i, ln in enumerate(lines) if _TABLE_HEAD_RE.match(ln)]
    if len(heads) != 1:
        raise LayoutError("找不到表③-b 表頭（> | job id | workflow |）" if not heads
                          else f"表③-b 表頭命中 {len(heads)} 次（須恰 1）")
    start = heads[0] + 2
    if not (start <= len(lines) and lines[start - 1].startswith("> |---")):
        raise LayoutError("表③-b 表頭的下一行不是分隔行（> |---）")
    end = start
    while end < len(lines) and lines[end].startswith("> |"):
        end += 1
    return start, end


def parse_rows(text: str) -> list[Row]:
    """表③-b 資料列 → Row；任何一列不合格式都 fail-loud（不靜默略過一個可能是紅的列）。"""
    lines = text.split("\n")
    start, end = _table_span(lines)
    rows: list[Row] = []
    for ln in lines[start:end]:
        m = _TABLE_ROW_RE.match(ln)
        if not m:
            raise LayoutError(f"表③-b 有一列不合格式：{ln[:60]}")
        rows.append(Row(m[1], m[2], m[3], m[4]))
    return rows


def rewrite_onboarding(text: str, samples: Sequence[Sample]) -> str:
    """只動兩處：錨行三個 nightly 值、表③-b 資料列；其餘每個位元組不動。冪等。"""
    if "\r" in text:
        raise LayoutError("含 CR（政策為 LF，見 .gitattributes）")
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ANCHOR_MARK in ln]
    if len(hits) != 1:
        raise LayoutError(f"`{ANCHOR_MARK}` 錨命中 {len(hits)} 次（須恰 1）")
    anchor = anchor_from(samples)
    head, tail = lines[hits[0]].split(ANCHOR_MARK, 1)
    for key, value in zip(_NIGHTLY_KEYS, (anchor.red, anchor.run, anchor.checked), strict=True):
        tail, n = re.subn(rf"(?<![\w-]){re.escape(key)}=\S+", lambda _m, k=key, v=value: f"{k}={v}",
                          tail)
        if n != 1:
            raise LayoutError(f"錨的 `{key}=` 在錨行出現 {n} 次（須恰 1）")
    lines[hits[0]] = head + ANCHOR_MARK + tail
    start, end = _table_span(lines)
    lines[start:end] = render_rows(samples)
    return "\n".join(lines)


def _anchor_fields(text: str) -> tuple[dict[str, str], list[str]]:
    """錨行的 `{欄位: 值}` 與版面問題；錨命中數 ≠1 時欄位表為空、問題清單非空。"""
    anchors = [ln for ln in text.split("\n") if ANCHOR_MARK in ln]
    if len(anchors) != 1:
        return {}, [f"`{ANCHOR_MARK}` 錨在 ONBOARDING.md 命中 {len(anchors)} 次（須恰 1）"]
    fields: dict[str, str] = {}
    probs: list[str] = []
    for key, value in _FIELD_RE.findall(anchors[0].split(ANCHOR_MARK, 1)[1]):
        if key in _NIGHTLY_KEYS and fields.get(key, value) != value:
            probs.append(f"錨的 `{key}=` 在同一行出現 ≥2 次且值不同"
                         f"（`{fields[key]}` 與 `{value}`）")
        fields.setdefault(key, value)
    return fields, probs


def _stamp_problems(checked: str, now: datetime.datetime) -> list[str]:
    key = f"`{FIELD_CHECKED}={checked}`"
    try:
        stamp = datetime.datetime.fromisoformat(checked)
    except ValueError:
        return [f"{key} 不是合法 ISO8601"]
    if stamp.tzinfo is None:
        return [f"{key} 沒有時區 ⇒ 跨時區讀者對同一字串算出不同年齡"]
    out: list[str] = []
    age = (now - stamp).days
    if age > NIGHTLY_MAX_AGE_DAYS:
        out.append(f"{key} 已是 {age} 天前（上限 {NIGHTLY_MAX_AGE_DAYS} 天）⇒ 任一排程通道已逾 "
                   f"{NIGHTLY_MAX_AGE_DAYS} 天沒有 completed run，或回填沒被 commit 帶走")
    if stamp > now + datetime.timedelta(days=1):
        out.append(f"{key} 在未來 ⇒ 一次沒發生過的查核")
    return out


def _red_problems(red: str, rows: Sequence[Row], scheduled: Sequence[str]) -> list[str]:
    listed = [] if red == RED_NONE else red.split(RED_SEP)
    out: list[str] = []
    unknown = [x for x in listed if x not in scheduled]
    if unknown:
        out.append(f"`{FIELD_RED}={red}` 列了 {unknown}，不在排程 fail-open 集合 {list(scheduled)}")
    expected = sorted(f"{r.wf}:{r.job}" for r in rows if "success" not in r.conclusion)
    if rows and sorted(listed) != expected:
        out.append(f"`{FIELD_RED}={red}` 與表③-b 的非 success 列 {expected} 不一致")
    return out


def anchor_problems(text: str, now: datetime.datetime, scheduled: Sequence[str]) -> list[str]:
    """離線判準（空＝通過）：run id 綁表③-b 資料列、ISO＋時區、≤14 天、非未來、紅集合綁表列。"""
    fields, probs = _anchor_fields(text)
    if not fields and probs:
        return probs
    probs += [f"錨缺 `{k}=`" for k in _NIGHTLY_KEYS if k not in fields]
    try:
        rows = parse_rows(text)
    except LayoutError as exc:
        return [*probs, str(exc)]
    run, red, checked = (fields.get(k, "") for k in (FIELD_RUN, FIELD_RED, FIELD_CHECKED))
    if not rows:
        probs.append("表③-b 沒有任何資料列")
    if run and not re.fullmatch(r"\d{6,}", run):
        probs.append(f"`{FIELD_RUN}={run}` 形態不合法（預期 databaseId 純數字、≥6 位）")
    elif run and rows and run not in {r.run_id for r in rows}:
        probs.append(f"`{FIELD_RUN}={run}` 不在表③-b 任何一列的 run id 欄 ⇒ 錨與表格有一邊沒跟上")
    if checked:
        probs += _stamp_problems(checked, now)
    if red:
        probs += _red_problems(red, rows, scheduled)
    return probs


def head_advice(head_problems: Sequence[str], tree_problems: Sequence[str]) -> str:
    """HEAD 紅時分兩型指路：工作樹已新＝只差 commit；工作樹也舊＝先 `--write`。"""
    if not head_problems:
        return ""
    return ADVICE_WRITE if tree_problems else ADVICE_COMMIT


def usage_text() -> str:
    return (
        "用法：python tools/refresh_nightly_anchor.py [--write | --check | --check-head | --help]\n"
        "\n"
        "  （無旗標）     唯讀預覽：gh 現查兩支排程通道，印將寫入的錨三欄與表③-b 列，不落檔\n"
        "  --write        寫回 ONBOARDING.md（表③-b 列＋錨的 nightly-red／nightly-run／"
        "nightly-checked-at）；\n"
        "                 寫完自我重讀並跑離線判準；內容相同則印「無變更」\n"
        "  --check        離線：判準驗工作樹的 ONBOARDING.md（不打 gh）\n"
        "  --check-head   離線：判準驗 HEAD 的 ONBOARDING.md（pre-push 快層與 root-infra-ci "
        "用；不打 gh）\n"
        "  --help, -h     印本說明\n"
        "\n"
        "rc：0＝通過／無變更／預覽成功；1＝判準紅或 ONBOARDING 版面不符；2＝用法錯誤；"
        "3＝取不到證據（gh／git）")


# ─────────────────────────── I/O 層（皆可注入） ───────────────────────────
def _run_tool(argv: Sequence[str], missing: str, *, which, runner):
    """跑 gh／git：路徑解析、逾時與啟動失敗一律轉 `EvidenceError`；不 `shell=True`、不改 env。"""
    exe = which(argv[0])
    if exe is None:
        raise EvidenceError(missing)
    try:
        return runner([exe, *argv[1:]], cwd=str(REPO), stdin=subprocess.DEVNULL,
                      capture_output=True, text=True, encoding="utf-8", errors="replace",
                      timeout=GH_TIMEOUT_S)
    except subprocess.TimeoutExpired as exc:
        raise EvidenceError(f"{argv[0]} 逾時（>{GH_TIMEOUT_S}s）：{' '.join(argv[:5])}"
                            " ⇒ 處置：檢查網路後重跑") from exc
    except OSError as exc:
        raise EvidenceError(f"無法啟動 {argv[0]}：{exc}") from exc


def _first_line(text: str) -> str:
    return next((ln for ln in (text or "").splitlines() if ln.strip()), "")[:200]


def run_gh(args: Sequence[str], *, which=shutil.which, runner=subprocess.run) -> str:
    """跑一次唯讀 gh 查詢並回 stdout；任何失敗 ⇒ `EvidenceError`（rc=3、零寫入）。"""
    missing = ("找不到 gh（PATH 上沒有）⇒ 無法回填。處置：安裝 GitHub CLI 並執行 "
               "`gh auth login`")
    proc = _run_tool(["gh", *args], missing, which=which, runner=runner)
    if proc.returncode == 4:
        raise EvidenceError("gh 未登入或 token 失效（rc=4）⇒ 處置：`gh auth login`，再以 "
                            "`gh auth status` 確認")
    if proc.returncode != 0:
        raise EvidenceError(f"gh 查詢失敗（rc={proc.returncode}）：{_first_line(proc.stderr)}"
                            "⇒ 處置：確認網路與 `gh auth status` 後重跑")
    return proc.stdout


def git_show_head(*, which=shutil.which, runner=subprocess.run) -> str:
    """`git show HEAD:ONBOARDING.md`：只用 HEAD 這個 commit，不引用任何 remote-tracking ref。"""
    argv = ["git", "-c", "core.quotepath=false", "show", "HEAD:ONBOARDING.md"]
    proc = _run_tool(argv, "找不到 git（PATH 上沒有）⇒ 無法讀取 HEAD",
                     which=which, runner=runner)
    if proc.returncode != 0:
        raise EvidenceError(f"無法讀取 HEAD:ONBOARDING.md（{_first_line(proc.stderr)}）"
                            "⇒ 非 git 工作樹、尚無 commit 或 git 不在 PATH")
    return proc.stdout


def read_onboarding(path: Path) -> str:
    try:
        text = path.read_bytes().decode("utf-8")
    except OSError as exc:
        raise LayoutError(f"讀不到 {path}：{exc}") from exc
    if "\r" in text:
        raise LayoutError("含 CR（政策為 LF，見 .gitattributes）")
    return text


def write_onboarding(path: Path, text: str) -> None:
    """bytes 層 LF 寫入（不經文字模式的換行轉換）；寫後重讀斷言零 CR。"""
    path.write_bytes(text.encode("utf-8"))
    read_onboarding(path)


def fetch_samples(pairs: Sequence[str], workflows_dir: Path,
                  gh: Callable[[Sequence[str]], str]) -> list[Sample]:
    """逐 workflow 查兩個事件各最近一筆 completed run、取較新者，再對 jobs 取各 job 的結論。"""
    by_wf: dict[str, list[str]] = {}
    for item in pairs:
        wf, job = item.split(":", 1)
        by_wf.setdefault(wf, []).append(job)
    samples: list[Sample] = []
    for wf in sorted(by_wf):
        runs: list[Run] = []
        for event in RUN_EVENTS:
            runs += parse_runs(gh(["run", "list", "--workflow", wf, "--event", event,
                                   "--status", "completed", "--limit", "1",
                                   "--json", _RUN_FIELDS]))
        run = newest_run(runs)
        if run is None:
            raise EvidenceError(
                f"{wf} 沒有任何 completed 的 schedule／workflow_dispatch run ⇒ 排程通道從未產出，"
                f"或全部尚在執行。處置：`gh workflow run {wf}`，等它 completed 再重跑本指令")
        jobs = parse_jobs(gh(["run", "view", str(run.id), "--json", "jobs"]))
        text = (workflows_dir / wf).read_text(encoding="utf-8", errors="replace")
        for job in sorted(by_wf[wf]):
            display = job_display_name(text, job, wf)
            samples.append(Sample(wf, job, display, run, job_conclusion(jobs, display, run.id, wf)))
    return samples


# ─────────────────────────── 模式分派 ───────────────────────────
def _green(where: str, text: str, now: datetime.datetime) -> int:
    f, _ = _anchor_fields(text)
    age = (now - datetime.datetime.fromisoformat(f[FIELD_CHECKED])).days
    print(f"✅ nightly 錨判準通過（{where}）：{FIELD_RUN}={f[FIELD_RUN]} "
          f"{FIELD_CHECKED}={f[FIELD_CHECKED]}（{age} 天前，上限 {NIGHTLY_MAX_AGE_DAYS} 天）"
          f"{FIELD_RED}={f[FIELD_RED]}")
    return EXIT_OK


def _red(where: str, problems: Sequence[str], advice: str) -> int:
    print(f"❌ nightly 錨判準不通過（{where}）：", file=sys.stderr)
    for p in problems:
        print(f"  - {p}", file=sys.stderr)
    print(advice, file=sys.stderr)
    return EXIT_RED


def _preview(anchor: Anchor, samples: Sequence[Sample], same: bool) -> int:
    print("ℹ️ 唯讀預覽（未寫檔；加 `--write` 套用）")
    for key, value in zip(_NIGHTLY_KEYS, anchor, strict=True):
        print(f"   {key}={value}")
    rows = render_rows(samples)
    print(f"   表③-b {len(rows)} 列：")
    for row in rows:
        print(f"   {row}")
    print("   與工作樹：一致" if same else
          "   與工作樹：不同——`--write` 會改動錨三欄與表③-b 列")
    return EXIT_OK


def _write(path: Path, text: str, new: str, samples: Sequence[Sample],
           now: datetime.datetime, sched: Sequence[str]) -> int:
    anchor = anchor_from(samples)
    if new == text:
        print(f"✅ 無變更：表③-b 與錨的 nightly 三欄已與 GitHub 現況一致"
              f"（{FIELD_RUN}={anchor.run} {FIELD_CHECKED}={anchor.checked}）")
        return EXIT_OK
    write_onboarding(path, new)
    problems = anchor_problems(read_onboarding(path), now, sched)
    if problems:
        return _red("工作樹（寫後自檢）", problems, ADVICE_WRITE)
    print(f"✅ 已回填 ONBOARDING.md：{FIELD_RUN}={anchor.run} {FIELD_CHECKED}={anchor.checked} "
          f"{FIELD_RED}={anchor.red}（表③-b {len(samples)} 列）")
    print("ℹ️ 工作樹已變更：請把 ONBOARDING.md 隨下一個 commit 一併收（內容只取決於 GitHub "
          "狀態，兩台機器各自回填的結果逐位元相同）")
    return EXIT_OK


def main(argv: Sequence[str], *, gh=run_gh, head_reader=git_show_head,
         now: datetime.datetime | None = None, onboarding: Path = ONBOARDING,
         workflows_dir: Path = WORKFLOWS_DIR) -> int:
    """模式分派與 rc 映射（`EvidenceError`→3、`LayoutError`→1）；**不讀 `sys.argv`**。"""
    modes = sorted({a for a in argv if a in _MODES})
    if len(modes) > 1:
        print(f"❌ 模式旗標互斥，實得 {modes}——請一次只給一個", file=sys.stderr)
        return EXIT_USAGE
    stamp = datetime.datetime.now(datetime.UTC) if now is None else now
    try:
        sched = scheduled_fail_open_jobs(workflows_dir)
        if modes == ["--check-head"]:
            head = head_reader()
            head_problems = anchor_problems(head, stamp, sched)
            if not head_problems:
                return _green("HEAD", head, stamp)
            tree_problems = anchor_problems(read_onboarding(onboarding), stamp, sched)
            return _red("HEAD", head_problems, head_advice(head_problems, tree_problems))
        text = read_onboarding(onboarding)
        if modes == ["--check"]:
            problems = anchor_problems(text, stamp, sched)
            if problems:
                return _red("工作樹", problems, ADVICE_WRITE)
            return _green("工作樹", text, stamp)
        samples = fetch_samples(sched, workflows_dir, gh)
        new = rewrite_onboarding(text, samples)
        if modes == ["--write"]:
            return _write(onboarding, text, new, samples, stamp, sched)
        return _preview(anchor_from(samples), samples, new == text)
    except EvidenceError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return EXIT_EVIDENCE
    except LayoutError as exc:
        print(f"❌ ONBOARDING.md 版面不符：{exc}", file=sys.stderr)
        return EXIT_RED


def cli(argv: Sequence[str]) -> int:
    rc = _cli_flags.reject_unknown_argv("refresh_nightly_anchor.py", argv, _KNOWN_ARGV)
    if rc is not None:
        return rc
    if "--help" in argv or "-h" in argv:
        print(usage_text())
        return EXIT_OK
    return main(argv)


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
