"""推送後等 GitHub CI：阻塞到那個提交的 workflow 全部跑完，並以**四種互不相同的結束碼**回報。

立案事故（掌舵者真機回報，sid 680d8411-58ac-4adb-9e23-521f6a7bb557，
2026-11-14 20:52～22:10 +08:00）：主控手寫背景輪詢 `do { sleep; gh run list --commit <短 SHA>
… } while (未完成數 -gt 0 -or 筆數 -lt 6)`；
`gh run list --commit <短 SHA>` 回 `[]` 且 rc=0（要完整 40 碼才列得出），所以結束條件永遠不成立，
CI 約 20 分鐘全綠卻沒被偵測到，主控閒置 78 分鐘。根因兩層：
① 結束條件分不出「還沒跑完」與「查詢本身查不到東西」——憑證該是**值**（有幾支 run、各自什麼狀態），
不是 rc；② 手寫迴圈沒有自己的截止時間。本工具把兩件事做成契約：先把 rev 解成完整 SHA 才查、
並核對每筆的 headSha；查到 0 支超過寬限就大聲失敗；自帶硬截止時間。

結束碼（`CI_WAIT_VERDICT=` 行與之一一對應）：
  0 pass     全部 completed，conclusion 皆 success／skipped／neutral
             （GitHub 把 skipped、neutral 當通過；required check 同此語意）
  1 fail     有 workflow 失敗、被取消、逾時、需動作等（列名稱與 `gh run view <id> --log-failed`）
  2 timeout  到截止時間仍有未完成（列出還在跑的）
  3 no-runs  查不到 run、查詢持續失敗、gh 缺席、SHA 解不出

所有外部依賴（執行外部指令、時鐘、睡眠、輸出）皆可注入，測試不外呼、不真睡。
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

EXIT_PASS, EXIT_FAIL, EXIT_TIMEOUT, EXIT_NO_RUNS = 0, 1, 2, 3
VERDICTS = {EXIT_PASS: "pass", EXIT_FAIL: "fail", EXIT_TIMEOUT: "timeout", EXIT_NO_RUNS: "no-runs"}

#: GitHub 把這三種 conclusion 當通過（skipped／neutral 不擋 required check）。
PASS_CONCLUSIONS = frozenset({"success", "skipped", "neutral"})
#: 連續幾次查詢失敗就放棄。WHY：偶發網路抖動要容忍，但 gh 未登入／無權限是永久性的，
#: 無限重試會重演事故的「結束條件永不成立」；5 次 × 預設 60 秒＝最多 5 分鐘內大聲失敗。
MAX_CONSECUTIVE_QUERY_FAILURES = 5
#: 單次外部指令的牆鐘上限（秒）；卡住的 gh 不得吃掉整個截止時間。
CALL_TIMEOUT_SEC = 60
_SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_JSON_FIELDS = "databaseId,workflowName,status,conclusion,headSha,attempt"

#: 排隊逾時自動重跑（APD §6，REQ-AP-CI-01）：同一 SHA 至多重跑幾輪。
#: WHY：外部現象（GitHub macOS runner 排隊 15 分即取消）重跑通常一次就拿到 runner；
#: 超過 2 輪仍中＝不是偶發，要大聲失敗而非無限重跑。
QUEUE_RERUN_MAX = 2
#: 排隊逾時的時間窗（分鐘）：GitHub 在排隊恰 15 分鐘取消零步驟 job；
#: 上下界各留 0.5～1 分鐘量測誤差，不含這個窗的取消（如 14 分、16.5 分）不是同一現象，不重跑。
QUEUE_WINDOW_MIN = (14.5, 16.0)

#: runner 契約：argv → (rc, stdout, stderr)；執行檔不存在時 raise FileNotFoundError。
Runner = Callable[[list[str]], tuple[int, str, str]]


def default_runner(argv: list[str]) -> tuple[int, str, str]:
    """真執行外部指令。argv 為 list、UTF-8 解碼、Windows 上不另開 console 視窗。"""
    r = subprocess.run(
        argv, capture_output=True, encoding="utf-8", errors="replace", shell=False,
        timeout=CALL_TIMEOUT_SEC, check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return r.returncode, r.stdout or "", r.stderr or ""


def resolve_sha(rev: str, run: Runner) -> tuple[str | None, str]:
    """rev → 完整 SHA。`gh run list --commit` 只認完整 SHA（短 SHA 回 `[]` 且 rc=0），
    所以任何查詢之前都必須先走這一步。回 (sha, 錯誤說明)。"""
    if not rev or rev.startswith("-"):
        return None, f"rev 不合法：{rev!r}"
    try:
        rc, out, err = run(["git", "rev-parse", "--verify", f"{rev}^{{commit}}"])
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"無法執行 git：{exc}"
    sha = out.strip().lower()
    if rc != 0 or not _SHA_RE.match(sha):
        return None, f"解不出提交 {rev!r}（git rc={rc}）：{err.strip() or out.strip()}"
    return sha, ""


def query_runs(sha: str, run: Runner) -> tuple[list[dict] | None, str, bool]:
    """查該提交的 workflow run。回 (runs, 錯誤, fatal)；fatal＝重試也不會好（gh 缺席）。

    不相信 gh 的過濾：每筆都核對 headSha 等於完整 SHA，不符一律丟掉。"""
    argv = ["gh", "run", "list", "--commit", sha, "--json", _JSON_FIELDS, "--limit", "100"]
    try:
        rc, out, err = run(argv)
    except FileNotFoundError:
        return None, "找不到 gh 執行檔（未安裝或不在 PATH）", True
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"gh 執行失敗：{exc}", False
    if rc != 0:
        return None, f"gh rc={rc}（未登入、無權限或網路問題）：{err.strip()}", False
    try:
        data = json.loads(out)
    except ValueError:
        return None, f"gh 輸出不是 JSON：{out[:120]!r}", False
    if not isinstance(data, list):
        return None, f"gh 輸出不是陣列：{out[:120]!r}", False
    return [d for d in data if isinstance(d, dict) and d.get("headSha") == sha], "", False


def latest_per_workflow(runs: list[dict]) -> dict[str, dict]:
    """同一 workflow 對同一 SHA 有多筆（重跑）時取最新一筆（databaseId 最大）。"""
    best: dict[str, dict] = {}
    for r in runs:
        name = str(r.get("workflowName", "?"))
        rid = int(r.get("databaseId") or 0)
        if name not in best or rid > int(best[name].get("databaseId") or 0):
            best[name] = r
    return best


def _ts(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _gh_json(argv: list[str], run: Runner) -> object | None:
    """唯讀 gh 查詢；任何失敗回 None（呼叫端一律往保守＝不重跑、照舊判 fail）。"""
    try:
        rc, out, _err = run(argv)
        return json.loads(out) if rc == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def queue_job(jobs_json: object) -> tuple[dict, float] | None:
    """attempt 的 jobs JSON 中第一支符合排隊逾時形態的 job（回 job 與排隊分鐘），否則 None。
    形態＝`conclusion=cancelled ∧ steps==[] ∧ runner_name 空 ∧ 14.5～16 分取消`（缺欄位不命中）。"""
    jobs = jobs_json.get("jobs") if isinstance(jobs_json, dict) else jobs_json
    for job in jobs if isinstance(jobs, list) else []:
        if not isinstance(job, dict) or job.get("conclusion") != "cancelled":
            continue
        if job.get("steps") != [] or job.get("runner_name") != "":
            continue
        start, end = _ts(job.get("created_at")), _ts(job.get("completed_at"))
        if start is None or end is None:
            continue
        minutes = (end - start).total_seconds() / 60
        if QUEUE_WINDOW_MIN[0] <= minutes <= QUEUE_WINDOW_MIN[1]:
            return job, minutes
    return None


def classify_attempt(jobs_json: object, newer_run: bool = False) -> str:
    """`queue_timeout`＝排隊逾時零步驟取消；其餘 `other`。
    `newer_run`＝同 ref 在該 job 存活期間有更新的 run（那是 concurrency 自取消，不是排隊逾時）。"""
    return "queue_timeout" if queue_job(jobs_json) and not newer_run else "other"


def has_newer_run(job: dict, run: Runner) -> bool:
    """同 ref 在 job 存活區間 `[created_at, completed_at]` 內是否有不同 SHA 的 run 被建立。
    查不到＝當作有（保守：寧可判 fail，不把真取消吸收成重跑）。"""
    branch = job.get("head_branch")
    data = _gh_json(["gh", "run", "list", "--branch", str(branch), "--json",
                     "databaseId,headSha,createdAt", "--limit", "50"], run) if branch else None
    if not isinstance(data, list):
        return True
    start, end = _ts(job.get("created_at")), _ts(job.get("completed_at"))
    for item in data:
        made = _ts(item.get("createdAt")) if isinstance(item, dict) else None
        if made and start and end and start <= made <= end \
                and item.get("headSha") != job.get("head_sha"):
            return True
    return False


def _run_key(r: dict) -> tuple[int, int]:
    """(run id, attempt)；`gh run list` 的 `attempt` 缺席時當 1。"""
    return int(r.get("databaseId") or 0), int(r.get("attempt") or 1)


def queue_timeout_minutes(r: dict, run: Runner) -> float | None:
    """該 run 是否為排隊逾時取消：是回排隊分鐘，否 None。只對 `conclusion=cancelled` 才呼叫 gh。"""
    if r.get("conclusion") != "cancelled":
        return None
    rid, att = _run_key(r)
    path = f"repos/{{owner}}/{{repo}}/actions/runs/{rid}/attempts/{att}/jobs"
    data = _gh_json(["gh", "api", f"{path}?per_page=100"], run)
    hit = queue_job(data)
    if hit is None or has_newer_run(hit[0], run):
        return None
    return hit[1]


def _trace_default(row: dict) -> None:
    """落持久痕跡 `autosdd_ci_queue.jsonl`（退役判準「連續 7 天零命中」的取數面）；不拋。"""
    try:
        import endurance_env  # tools/lib 已由套件 __init__ 補進 sys.path
        target = endurance_env.trace_dir() / "autosdd_ci_queue.jsonl"
        with target.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    except (OSError, ImportError):
        pass


@dataclass
class Options:
    sha: str
    timeout_min: float = 40.0
    interval_sec: float = 60.0
    grace_min: float = 5.0
    expect: int = 0
    workflows: tuple[str, ...] = ()


def _summary(cur: dict[str, dict]) -> str:
    return "、".join(f"{n}={r.get('conclusion') or r.get('status')}"
                    for n, r in sorted(cur.items()))


def wait(opts: Options, *, run: Runner = default_runner,
         now: Callable[[], datetime] = lambda: datetime.now().astimezone(),
         sleep: Callable[[float], None] | None = None,
         emit: Callable[[str], None] = print,
         trace: Callable[[dict], None] = _trace_default) -> int:
    """阻塞到 CI 跑完或到截止時間；回結束碼（最後一行印 `CI_WAIT_VERDICT=…`）。

    排隊逾時（APD §6）：全部完成且失敗者**全部**是排隊逾時零步驟取消 ⇒ `gh run rerun <id> --failed`
    並繼續等（同 SHA 至多 `QUEUE_RERUN_MAX` 輪）；只要有一支是別的失敗就照舊判 fail、不重跑。"""
    import time as _time
    sleep = sleep or _time.sleep
    start = now()
    deadline = timedelta(minutes=opts.timeout_min)
    grace = timedelta(minutes=opts.grace_min)
    failures, seen_any = 0, False
    cur: dict[str, dict] = {}
    reruns = 0
    rerun_done: set[tuple[int, int]] = set()  # (run id, attempt)：已重跑、等 GitHub 把狀態翻起來

    def say(msg: str) -> None:
        stamp = now().astimezone(UTC).isoformat(timespec="seconds")
        emit(f"[{stamp}] ci_wait sha={opts.sha[:12]} {msg}")

    def finish(rc: int, msg: str, reason: str = "") -> int:
        say(msg)
        extra = (f" reason={reason}" if reason else "") + (
            f" rerun=queue_timeout×{reruns}" if reruns and not reason else "")
        emit(f"CI_WAIT_VERDICT={VERDICTS[rc]}{extra} sha={opts.sha} runs={len(cur)}")
        return rc

    def queue_rerun(bad: dict[str, dict]) -> str:
        """回 `rerun`（已重跑或等翻轉，繼續等）｜`exhausted`｜`other`（含重跑失敗，照舊 fail）。"""
        nonlocal reruns
        fresh: dict[str, tuple[dict, float]] = {}
        for n, r in bad.items():
            if _run_key(r) in rerun_done:
                continue
            minutes = queue_timeout_minutes(r, run)
            if minutes is None:
                return "other"
            fresh[n] = (r, minutes)
        if not fresh:
            say("排隊逾時已重跑，等 GitHub 更新 run 狀態")
            return "rerun"
        if reruns >= QUEUE_RERUN_MAX:
            return "exhausted"
        for n, (r, minutes) in sorted(fresh.items()):
            rid, att = _run_key(r)
            try:
                rc, _out, err = run(["gh", "run", "rerun", str(rid), "--failed"])
            except (OSError, subprocess.SubprocessError) as exc:
                rc, err = 1, str(exc)
            if rc != 0:
                say(f"排隊逾時重跑失敗 run={rid}：{err.strip()}")
                return "other"
            rerun_done.add((rid, att))
            trace({"event": "ci_queue_timeout", "run": rid, "attempt": att,
                   "minutes": round(minutes, 2), "workflow": n, "sha": opts.sha,
                   "at": now().astimezone(UTC).isoformat(timespec="seconds")})
            say(f"ci_queue_timeout run={rid} attempt={att} minutes={minutes:.1f}"
                " ⇒ gh run rerun --failed")
        reruns += 1
        return "rerun"

    while True:
        runs, err, fatal = query_runs(opts.sha, run)
        elapsed = now() - start
        if runs is None:
            failures += 1
            if fatal or failures >= MAX_CONSECUTIVE_QUERY_FAILURES:
                return finish(EXIT_NO_RUNS, f"查詢失敗且不再重試（連續 {failures} 次）：{err}")
            say(f"查詢失敗（連續 {failures}/{MAX_CONSECUTIVE_QUERY_FAILURES}）：{err}")
        else:
            failures = 0
            cur = latest_per_workflow(runs)
            if opts.workflows:
                missing = [w for w in opts.workflows if w not in cur]
                cur = {n: r for n, r in cur.items() if n in opts.workflows}
            else:
                missing = []
            short = max(0, opts.expect - len(cur)) if opts.expect else 0
            seen_any = seen_any or bool(cur)
            pending = {n: r for n, r in cur.items() if r.get("status") != "completed"}
            done = len(cur) - len(pending)
            say(f"完成 {done}/{len(cur)}：{_summary(cur) or '（尚無 run）'}")
            incomplete = bool(missing) or short > 0 or not cur
            if incomplete and elapsed >= grace:
                why = (f"缺少指定 workflow：{'、'.join(missing)}" if missing
                       else f"只有 {len(cur)} 支，少於 --expect {opts.expect}" if short
                       else "查不到任何 run：可能這個提交沒有觸發 workflow、SHA 不對、或 gh 未登入")
                return finish(EXIT_NO_RUNS, f"超過寬限 {opts.grace_min:g} 分鐘仍不齊：{why}")
            if not incomplete and not pending:
                bad = {n: r for n, r in cur.items() if r.get("conclusion") not in PASS_CONCLUSIONS}
                if not bad:
                    return finish(EXIT_PASS, f"全部通過（{len(cur)} 支）")
                verdict = queue_rerun(bad)
                if verdict != "rerun":
                    hint = "；".join(
                        f"{n}={r.get('conclusion')}"
                        f"（gh run view {r.get('databaseId')} --log-failed）"
                        for n, r in sorted(bad.items()))
                    return finish(EXIT_FAIL, f"有 workflow 未通過：{hint}",
                                  "queue_timeout_exhausted" if verdict == "exhausted" else "")
        if elapsed >= deadline:
            if not seen_any:
                return finish(EXIT_NO_RUNS, f"到截止時間 {opts.timeout_min:g} 分鐘仍沒看到任何 run")
            running = "、".join(sorted(n for n, r in cur.items() if r.get("status") != "completed"))
            left = running or "（指定的 workflow 未齊）"
            return finish(EXIT_TIMEOUT, f"到截止時間 {opts.timeout_min:g} 分鐘仍有未完成：{left}")
        sleep(min(opts.interval_sec, (deadline - elapsed).total_seconds()))
