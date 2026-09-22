#!/usr/bin/env python3
"""dev_platform_provenance — 最近 commit 在哪個平台做的（git 端 provenance，DEF-200-358）。

為何存在：`tools/dev_start.py` [1/7] 的「上次開發平台」讀的是 gitignored 的本機狀態檔
`.dev_env_state.json`，它只記「這台機器上次跑 dev_start 時的平台」。雙機各自 clone
（mac 一台、Windows 一台，互相 push／pull）時它恆等於 Now——dev_start 檔頭也自陳
「切換恆不觸發」。機械效果（清本機快取、換 venv 形狀）是對的，但被當成「專案上次在哪
開發」回報給人就錯了（2026-09-22 掌舵者：「上次是在 mac 執行，你在 git 上分辨不出來嗎」）。
唯一能跨機器的載體是 git 歷史本身，所以本模組提供兩端：

  1. 寫端 `--apply-trailers <訊息檔>`：把 `Dev-Platform: <label>` 與 `Dev-Host: <hostname>` 兩行
     寫進 commit 訊息（`--trailers` 只印兩行供除錯）。由 `tools/git-hooks/prepare-commit-msg`
     （非互動式 -m／-F）與 `commit-msg`（互動式：編輯器關閉後）呼叫——provenance 註記，永不
     阻斷 commit。label 與 `platform_utils.os_label()` 同源（windows／mac／linux）。
  2. 讀端 `infer_recent_platform()`：從前沿 rev（fetch 後本機落後時＝origin/<branch>，否則
     HEAD）沿 first-parent 往回掃有限個 commit——先認 trailer（決定性）；沒有 trailer 的舊
     commit 退到內容啟發式：該 commit 的 diff 新增行動到 ONBOARDING §7 表② 的哪一條
     `snapshot-fingerprints-<darwin|win32>` 錨、或 `AutoClaude/.perf_baseline.toml` 寫入的
     `environment = "<sys.platform>-local"`（兩者都只會在該平台真機上改動）。訊號互相矛盾或
     都沒有 ⇒ 誠實回 unknown，不猜。前沿由 `resolve_frontier()` 判定（DEF-200-360）：
     `report_env_detection(..., fetch=True)` 才會真的打一次網路 fetch，`dev_start.py` [2/7]
     `step_sync` 經 `fetch_or_reuse()` 沿用同一份結果、不重複 fetch；`fetch=False`（預設、
     CLI、`--no-sync`）則零 subprocess，只讀本機 HEAD。

刻意只依賴 stdlib。平台字面只住 `_SYS_PLATFORM_TO_LABEL` 一處，並由測試釘住與
`platform_utils.os_label()` 同構（鐵律三：mac 上 sys.platform=darwin、ONBOARDING 錨鍵=darwin、
perf environment=darwin-local，三者都映到同一個 label "mac"）。
"""
from __future__ import annotations

import argparse
import json
import platform as _platform
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_utils  # noqa: E402

TRAILER_PLATFORM = "Dev-Platform"
TRAILER_HOST = "Dev-Host"
KNOWN_LABELS: tuple[str, ...] = ("windows", "mac", "linux")
#: sys.platform 原值 → os_label；未列者一律 linux（與 platform_utils.os_label() 的分支同構）。
_SYS_PLATFORM_TO_LABEL: dict[str, str] = {"win32": "windows", "darwin": "mac"}
#: 啟發式訊號來源（相對 repo 根）；只掃這兩個檔，避免對任意 diff 亂猜。
HEURISTIC_PATHS: tuple[str, ...] = ("ONBOARDING.md", "AutoClaude/.perf_baseline.toml")
_ANCHOR_RE = re.compile(r"snapshot-fingerprints-(win32|darwin):")
_PERF_ENV_RE = re.compile(r'environment\s*=\s*"(win32|darwin|linux)-local"')
DEFAULT_MAX_COMMITS = 20
_GIT_TIMEOUT_S = 20
#: resolve_frontier／fetch_or_reuse 的 fetch timeout 預設值（DEF-200-362 A1；
#: dev_start.py [2/7] 呼叫 fetch_or_reuse 時傳的字面 120 與本常數同值，但該檔凍結不引用本常數）。
FETCH_TIMEOUT_S = 120


def label_for_sys_platform(sys_platform: str) -> str:
    """sys.platform 原值（win32／darwin／linux…）→ os_label 三態字面。"""
    return _SYS_PLATFORM_TO_LABEL.get(sys_platform, "linux")


def current_label() -> str:
    return platform_utils.os_label()


def current_host() -> str:
    host = (_platform.node() or "").strip().replace("\n", " ").replace("\r", " ")
    return host or "unknown"


def trailer_lines(label: str | None = None, host: str | None = None) -> list[str]:
    """prepare-commit-msg 要補進 commit 訊息尾端的兩行 trailer。"""
    return [
        f"{TRAILER_PLATFORM}: {label or current_label()}",
        f"{TRAILER_HOST}: {host or current_host()}",
    ]


def _run_git(repo_root: Path, *args: str) -> str | None:
    """跑 `git -C <repo_root> <args>`；rc≠0 或任何例外一律回 None（呼叫端據此走 unknown）。

    encoding 必須顯式指定：`text=True` 無 encoding 在無 PYTHONUTF8 的 Windows 終端走 locale
    （zh-TW＝cp950），commit 訊息／路徑的 UTF-8 中文會 UnicodeDecodeError（本 repo 既有實證）。
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=_GIT_TIMEOUT_S, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _run_git_raw(repo_root: Path, *args: str, timeout_s: int) -> subprocess.CompletedProcess:
    """跑 `git -C <repo_root> <args>`，原樣交回 `CompletedProcess`（rc／stdout／stderr）。

    逐字比照 `dev_start._git()` 的例外語意（DEF-200-360）：呼叫端（`step_sync` 的離線訊息）
    需要真實 rc／stderr 才能組出人讀的失敗原因，不可像 `_run_git()` 那樣把失敗吞成 None。
    """
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout_s, check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(args=args, returncode=127,
                                           stdout="", stderr="git not found")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=args, returncode=124,
            stdout="", stderr=f"git {' '.join(args)} 逾時（>{timeout_s}s）")


#: [1/7]／[2/7] 共用同一次 `git fetch` 的結果（key＝`repo_root.resolve()`）；一次性——
#: `fetch_or_reuse()` 讀到就 pop 掉，避免同一份結果被誤用第二次。
_PREFETCH: dict[Path, subprocess.CompletedProcess] = {}


def fetch_or_reuse(
    repo_root: Path, *, timeout_s: int = FETCH_TIMEOUT_S
) -> subprocess.CompletedProcess:
    """`dev_start.py` [2/7] `step_sync` 的 fetch 入口：[1/7] 已 fetch 過就沿用那次結果，
    否則自己補做一次——兩種呼叫順序（先 [1/7] 再 [2/7]，或單獨呼叫）皆只打一次網路。"""
    key = repo_root.resolve()
    if key in _PREFETCH:
        return _PREFETCH.pop(key)
    return _run_git_raw(repo_root, "fetch", "origin", "--prune", timeout_s=timeout_s)


def consume_prefetch(repo_root: Path) -> subprocess.CompletedProcess | None:
    """測試用：清掉尚未被消費的快取（`addCleanup` 避免污染下一個測試）。"""
    return _PREFETCH.pop(repo_root.resolve(), None)


@dataclass(frozen=True)
class Verdict:
    """`infer_recent_platform()` 的判定結果。

    label：windows／mac／linux，判不出來＝None。
    method：trailer（決定性）／heuristic（內容啟發式）／unknown。
    commit：判定所依據的 commit 短 sha（unknown 時＝掃描起點）。
    depth：該 commit 是從 rev 往回第幾個（1＝rev 本身）。
    host：trailer 帶的 Dev-Host（啟發式沒有這一項）。
    evidence：人可讀的依據，第一筆是主因。
    """

    label: str | None
    method: str
    commit: str
    depth: int
    commits_scanned: int
    host: str | None = None
    evidence: list[str] = field(default_factory=list)

    @property
    def method_zh(self) -> str:
        return {"trailer": "trailer", "heuristic": "內容啟發式", "unknown": "無法判定"}[self.method]


@dataclass(frozen=True)
class Frontier:
    """`resolve_frontier()` 的判定結果：`infer_recent_platform()` 該從哪個 rev 掃。

    rev：傳給 `infer_recent_platform(rev=...)` 的值——"HEAD" 或 "origin/<branch>"。
    other_rev：只在本機與 origin 分叉時有值（＝remote_ref），供呼叫端另外判一次遠端側。
    fetched：本次是否真的打了網路且成功（`fetch=False`／無 origin／fetch 失敗皆為 False）。
    compared：是否真的算出了 ahead/behind（僅 g～j 四個分支為 True）；`fetched=True` 但
        `compared=False` 代表 fetch 成功卻沒能與 origin 比對（detached HEAD／origin/<branch>
        不存在／計數失敗），此時摘要仍要提醒「只反映本機 HEAD」（DEF-200-360 四方複審 SA P2）。
    note：人讀附註，進 [1/7] 第三行的括號。
    """

    rev: str
    branch: str | None = None
    remote_ref: str | None = None
    ahead: int = 0
    behind: int = 0
    fetched: bool = False
    compared: bool = False
    note: str = ""
    other_rev: str | None = None


def _trailer_values(repo_root: Path, sha: str, key: str) -> list[str]:
    """該 commit 的 `key` trailer 全部值（依出現順序）；讀不到＝空 list。"""
    out = _run_git(repo_root, "log", "-1", f"--format=%(trailers:key={key},valueonly)", sha)
    if out is None:
        return []
    return [v.strip() for v in out.splitlines() if v.strip()]


_TRAILER_LINE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*: \S")
_OWN_TRAILER_RE = re.compile(rf"^({TRAILER_PLATFORM}|{TRAILER_HOST}):")


def apply_trailers(msg_path: Path, *, defer_if_blank: bool = False,
                   label: str | None = None, host: str | None = None) -> str:
    """把兩行 trailer 寫進 commit 訊息檔；回 applied／deferred／blank。

    自己寫而不用 `git interpret-trailers`：後者對「編輯器尚未開、subject 仍是空白佔位」的樣板
    會把 trailer 直接接在空白 subject 後面——使用者填完 subject 兩者同段落，git 不認作 trailer
    （四方複審沙盒實測）；且 `--if-exists replace` 對同鍵多列只換最後一列。規則：
      · 尾端的 `#` 註解區塊（git 樣板）原樣保留在 trailer 之後；
      · 既有 Dev-Platform／Dev-Host 列不論位置一律剝除再重寫（同鍵永遠只有一組）；
      · 本體（去註解、去尾端空白）為空 ⇒ 不寫（只有 trailer 的訊息不成段落）：
        defer_if_blank 回 deferred（留給 commit-msg 階段），否則回 blank；
      · 本體最後一段全為 trailer 形態（如 Co-Authored-By）且不是 subject ⇒ 併入同一段。
    """
    lines = msg_path.read_text(encoding="utf-8", errors="replace").splitlines()
    cut = len(lines)
    while cut > 0 and (lines[cut - 1].startswith("#") or not lines[cut - 1].strip()):
        cut -= 1
    body = [ln for ln in lines[:cut] if not _OWN_TRAILER_RE.match(ln)]
    tail = lines[cut:]
    while tail and not tail[0].strip():
        tail.pop(0)
    while body and not body[-1].strip():
        body.pop()
    if not body:
        return "deferred" if defer_if_blank else "blank"
    para = len(body)
    while para > 0 and body[para - 1].strip():
        para -= 1
    join_block = para > 0 and all(_TRAILER_LINE_RE.match(ln) for ln in body[para:])
    new = body + ([] if join_block else [""]) + trailer_lines(label, host)
    if tail:
        new += [""] + tail
    msg_path.write_text("\n".join(new) + "\n", encoding="utf-8", newline="\n")
    return "applied"


def heuristic_labels_from_diff(diff_text: str) -> tuple[set[str], list[str]]:
    """從 `git show --unified=0` 的輸出（只看 `+` 新增行）抽平台訊號。回 (labels, evidence)。"""
    labels: set[str] = set()
    evidence: list[str] = []
    for line in diff_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        m = _ANCHOR_RE.search(line)
        if m:
            labels.add(label_for_sys_platform(m.group(1)))
            evidence.append(f"ONBOARDING snapshot-fingerprints-{m.group(1)} 錨變動")
            continue
        m = _PERF_ENV_RE.search(line)
        if m:
            labels.add(label_for_sys_platform(m.group(1)))
            evidence.append(f'perf baseline environment="{m.group(1)}-local"')
    return labels, evidence


def infer_recent_platform(
    repo_root: Path, *, rev: str = "HEAD", max_commits: int = DEFAULT_MAX_COMMITS
) -> Verdict:
    """從 `rev` 沿 first-parent 往回掃，回傳第一個判得出平台的 commit 的 Verdict。"""
    listing = _run_git(repo_root, "rev-list", "--first-parent", f"--max-count={max_commits}", rev)
    shas = [s.strip() for s in (listing or "").splitlines() if s.strip()]
    if not shas:
        return Verdict(None, "unknown", rev, 0, 0, evidence=["git rev-list 失敗或沒有任何 commit"])
    notes: list[str] = []
    for depth, sha in enumerate(shas, start=1):
        short = sha[:7]
        values = _trailer_values(repo_root, sha, TRAILER_PLATFORM)
        if values:
            value = values[-1]  # hook 以最後一列為本機值（replace 只換最後一列，舊列可能殘留）
            if len(values) > 1:
                notes.append(f"{short} 有多列 {TRAILER_PLATFORM}（{values}），取最後一列")
            if value in KNOWN_LABELS:
                hosts = _trailer_values(repo_root, sha, TRAILER_HOST)
                return Verdict(value, "trailer", short, depth, depth,
                               host=hosts[-1] if hosts else None,
                               evidence=[f"{TRAILER_PLATFORM} trailer={value}", *notes])
            notes.append(f"{short} 的 {TRAILER_PLATFORM} trailer 值不在 {KNOWN_LABELS}：{value!r}")
        diff = _run_git(repo_root, "show", "--format=", "--unified=0", "--no-color", sha,
                        "--", *HEURISTIC_PATHS)
        labels, evidence = heuristic_labels_from_diff(diff or "")
        if len(labels) == 1:
            label = next(iter(labels))
            return Verdict(label, "heuristic", short, depth, depth,
                           evidence=[evidence[0], *notes])
        if len(labels) > 1:
            notes.append(f"{short} 同時帶 {sorted(labels)} 訊號（矛盾，略過）")
    reason = f"{len(shas)} 個 commit 皆無 {TRAILER_PLATFORM} trailer 且無內容線索"
    return Verdict(None, "unknown", shas[0][:7], 0, len(shas), evidence=[reason, *notes])


def resolve_frontier(repo_root: Path, *, fetch: bool, timeout_s: int = FETCH_TIMEOUT_S) -> Frontier:
    """判定 [1/7] 該從哪個 rev 掃 provenance（DEF-200-360：fetch-aware 前沿）。

    `fetch=False`（`--no-sync`／CLI 預設）：本函式零 subprocess（`infer_recent_platform` 仍會跑
    本機唯讀 git，只是不打網路），只回本機 HEAD——剛從另一台機器切換過來時這一行可能過時，
    但代價是不打網路。`fetch=True`：真的 `git fetch origin
    --prune` 一次（結果進 `_PREFETCH`，供 `fetch_or_reuse()` 沿用，[2/7] 不重複打網路），
    本機落後 origin 時前沿改成 `origin/<branch>`（讀的是對面機器剛 push 的 commit）；
    本機領先或同步則仍用本機 HEAD；分叉則兩側都要看，`other_rev` 交回遠端側供呼叫端另判。
    任何一步失敗（無 origin／fetch 失敗／detached HEAD／無 origin/<branch>／計數失敗）一律
    誠實退回本機 HEAD，`note` 說明原因——不可猜。

    `timeout_s` 只約束 fetch 本身；其餘本機唯讀查詢（remote get-url／rev-parse／rev-list）
    固定 `_GIT_TIMEOUT_S`（20 秒），不受 `timeout_s` 影響。
    """
    if not fetch:
        return Frontier(rev="HEAD", note="未 fetch（--no-sync）：只反映本機 HEAD"
                        "——剛從另一台機器切換過來時這一行可能過時")
    if _run_git(repo_root, "remote", "get-url", "origin") is None:
        return Frontier(rev="HEAD", note="無 origin remote：只反映本機 HEAD")

    key = repo_root.resolve()
    fp = _run_git_raw(repo_root, "fetch", "origin", "--prune", timeout_s=timeout_s)
    _PREFETCH[key] = fp
    if fp.returncode != 0:
        lines = [ln.strip() for ln in (fp.stderr or "").splitlines() if ln.strip()]
        detail = lines[0] if lines else f"rc={fp.returncode}"
        return Frontier(rev="HEAD", note=f"fetch 失敗（{detail}）：只反映本機 HEAD")

    branch = (_run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD") or "").strip()
    if not branch or branch == "HEAD":
        return Frontier(rev="HEAD", fetched=True, note="detached HEAD：只反映本機 HEAD")
    remote_ref = f"origin/{branch}"
    if _run_git(repo_root, "rev-parse", "--verify", "--quiet", remote_ref) is None:
        return Frontier(rev="HEAD", branch=branch, fetched=True,
                        note=f"{remote_ref} 不存在：只反映本機 HEAD")

    def _count(spec: str) -> int | None:
        out = _run_git(repo_root, "rev-list", "--count", spec)
        if out is None:
            return None
        try:
            return int(out.strip())
        except ValueError:
            return None

    behind = _count(f"HEAD..{remote_ref}")
    ahead = _count(f"{remote_ref}..HEAD")
    if behind is None or ahead is None:
        return Frontier(rev="HEAD", branch=branch, remote_ref=remote_ref, fetched=True,
                        note="rev-list 計數失敗：只反映本機 HEAD")
    common = {"branch": branch, "remote_ref": remote_ref, "ahead": ahead, "behind": behind,
              "fetched": True, "compared": True}
    if behind > 0 and ahead == 0:
        return Frontier(rev=remote_ref, note=f"已 fetch；本機 HEAD 落後 {remote_ref} {behind} "
                        f"commit，判定取 {remote_ref} 最新 commit", **common)
    if behind == 0 and ahead == 0:
        return Frontier(rev="HEAD", note=f"已 fetch；本機 HEAD 與 {remote_ref} 同步", **common)
    if behind == 0 and ahead > 0:
        return Frontier(rev="HEAD", note=f"已 fetch；本機領先 {remote_ref} {ahead} commit"
                        f"（未 push），判定取本機 HEAD", **common)
    return Frontier(rev="HEAD", other_rev=remote_ref,
                    note=f"已 fetch；與 {remote_ref} 分叉（本地 +{ahead}／遠端 +{behind}），"
                    f"兩側各判", **common)


def _via(verdict: Verdict) -> str:
    """組「依據哪個 commit 的什麼證據」的人讀片段，第三行與「遠端側」行共用。"""
    via = f"{verdict.commit} 的 {verdict.evidence[0]}"
    if verdict.method == "heuristic" and verdict.depth > 1:
        via += f"，往回第 {verdict.depth} 個 commit（其間 {verdict.depth - 1} 個無訊號）"
    if verdict.host:
        via += f"，主機 {verdict.host}"
    return via


def _note_unfetched(summary: str, fr: Frontier | None) -> str:
    """未 fetch，或 fetch 成功卻沒能與 origin 比對時，在摘要右括號內補一句提醒（DEF-200-360
    四方複審 SA P2：detached HEAD／origin/<branch> 不存在／計數失敗三種「fetch 成功但沒比對」
    的情境，摘要也要帶警語，不能只看 `fetched`）。"""
    if fr is None:
        return summary
    if not fr.fetched:
        warning = "未 fetch，只反映本機 HEAD"
    elif not fr.compared:
        warning = "未與 origin 比對，只反映本機 HEAD"
    else:
        return summary
    if summary.endswith("）"):
        return summary[:-1] + "；" + warning + "）"
    return summary + "（" + warning + "）"


def report_env_detection(
    repo_root: Path, *, now: str, developing: str | None, host: str, is_repo: bool,
    print_fn=print, warn=None, fetch: bool = False,
) -> str:
    """dev_start [1/7] 的三行報告；回傳要寫進 SUMMARY["env"] 的一句話。

    只負責「印」與「摘要」：本機切換（developing≠now）驅動 [3/7]／[4/7] 的旗標仍由
    dev_start 自己算、自己消費——那兩步的正確判準是本機記憶，不是 git。
    `fetch`：是否先做一次 `git fetch`、本機落後 origin 時改讀對面機器剛 push 的 commit
    （DEF-200-360 前沿判定，見 `resolve_frontier()`）；`False`＝只讀本機 HEAD，零 subprocess。
    """
    print_fn(f"    Now（當前平台）        ：{now}（host: {host}）")
    print_fn(f"    本機上次平台（狀態檔）  ：{developing or '（無紀錄，首次執行）'}"
             "——.dev_env_state.json 只記這台機器；"
             "雙 clone 拓撲下恆等於 Now，不代表專案上次在哪開發")
    local_switch = developing is not None and developing != now
    if local_switch:
        print_fn(f"    → 本機跨平台切換（共用工作目錄拓撲）：{developing} → {now}，將執行切換程序")
    verdict: Verdict | None = None
    other: Verdict | None = None
    fr: Frontier | None = None
    if not is_repo:
        print_fn("    最近 commit 開發平台    ：（非 git repo，略）")
    else:
        if fetch:
            print_fn(f"    git fetch origin --prune …（前沿判定用；最長 {FETCH_TIMEOUT_S} 秒，"
                     "離線可加 --no-sync 略過）")
        fr = resolve_frontier(repo_root, fetch=fetch)
        verdict = infer_recent_platform(repo_root, rev=fr.rev)
        other = infer_recent_platform(repo_root, rev=fr.other_rev) if fr.other_rev else None
        if verdict.label is None:
            msg = (f"無法從 git 判定最近 commit 的開發平台（{verdict.evidence[0]}）"
                   f"——請自行判讀 [2/7] 拉進的 commit 來自哪台機器；{fr.note}")
            (warn or print_fn)(msg)
        else:
            print_fn(f"    最近 commit 開發平台    ：{verdict.label}"
                     f"（git {verdict.method_zh}：{_via(verdict)}；{fr.note}）")
            if verdict.label != now:
                print_fn(f"    → 跨機切換（依 git）：{verdict.label} → {now}"
                         "——本機快取／venv 不需動作；依賴 hash 由 [4/7]、"
                         "§7 表② 指紋由 [6/7] 各自判定")
        if fr.other_rev:
            if other and other.label:
                other_txt = f"{other.label}（git {other.method_zh}：{_via(other)}）"
            else:
                reason = other.evidence[0] if other and other.evidence else "無訊號"
                other_txt = f"無法判定（{reason}）"
            print_fn(f"    遠端側 {fr.remote_ref} 最近 commit 開發平台：{other_txt}")
            if other and other.label and other.label != now:
                print_fn(f"    → 跨機切換（依 git，{fr.remote_ref} 側）：{other.label} → {now}"
                         "——本機快取／venv 不需動作；依賴 hash 由 [4/7]、"
                         "§7 表② 指紋由 [6/7] 各自判定")
    git_label = verdict.label if verdict else None
    if local_switch:
        summary = f"{developing} → {now}（本機已切換）"
    elif git_label and git_label != now:
        take = f"，取 {fr.rev}" if fr and fr.rev != "HEAD" else ""
        summary = _note_unfetched(f"{git_label} → {now}（跨機切換，git 判定{take}）", fr)
    elif fr and fr.other_rev and other and other.label and other.label != now:
        undeterminable = "；本機側無法判定" if git_label is None else ""
        summary = _note_unfetched(
            f"{other.label}（{fr.remote_ref} 側）→ {now}"
            f"（跨機切換，git 判定，分叉{undeterminable}）", fr)
    elif git_label:
        summary = _note_unfetched(f"{now}（無切換；git 最近 commit 亦為 {git_label}）", fr)
    elif verdict is not None:
        summary = _note_unfetched(f"{now}（無本機切換；git 無法判定最近 commit 平台）", fr)
    else:
        summary = f"{now}（無切換）" if developing else f"{now}（首次紀錄）"
    if developing is None and "首次" not in summary:
        summary += "（首次紀錄）"
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--trailers", action="store_true",
        help="印出本機的 Dev-Platform／Dev-Host 兩行 trailer（除錯用）")
    parser.add_argument(
        "--apply-trailers", type=Path, metavar="MSG_FILE",
        help="把兩行 trailer 寫進該 commit 訊息檔（prepare-commit-msg／commit-msg 呼叫）")
    parser.add_argument(
        "--defer-if-blank", action="store_true",
        help="搭配 --apply-trailers：訊息本體仍空白（互動式樣板）時不寫，留給 commit-msg")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--rev", default="HEAD")
    parser.add_argument("--max-commits", type=int, default=DEFAULT_MAX_COMMITS)
    parser.add_argument("--json", action="store_true", help="以 JSON 印 Verdict")
    args = parser.parse_args(argv)
    if args.trailers:
        print("\n".join(trailer_lines()))
        return 0
    if args.apply_trailers is not None:
        print(apply_trailers(args.apply_trailers, defer_if_blank=args.defer_if_blank))
        return 0
    verdict = infer_recent_platform(args.repo_root, rev=args.rev, max_commits=args.max_commits)
    if args.json:
        print(json.dumps(asdict(verdict), ensure_ascii=False))
    else:
        print(f"label={verdict.label} method={verdict.method} commit={verdict.commit} "
              f"depth={verdict.depth} host={verdict.host}")
        for line in verdict.evidence:
            print(f"  - {line}")
    return 0 if verdict.label else 1


if __name__ == "__main__":
    sys.exit(main())
