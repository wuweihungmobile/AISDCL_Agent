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
  2. 讀端 `infer_recent_platform()`：從 HEAD 沿 first-parent 往回掃有限個 commit——先認
     trailer（決定性）；沒有 trailer 的舊 commit 退到內容啟發式：該 commit 的 diff 新增行動到
     ONBOARDING §7 表② 的哪一條 `snapshot-fingerprints-<darwin|win32>` 錨、或
     `AutoClaude/.perf_baseline.toml` 寫入的 `environment = "<sys.platform>-local"`（兩者都只會
     在該平台真機上改動）。訊號互相矛盾或都沒有 ⇒ 誠實回 unknown，不猜。

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


def report_env_detection(
    repo_root: Path, *, now: str, developing: str | None, host: str, is_repo: bool,
    print_fn=print, warn=None,
) -> str:
    """dev_start [1/7] 的三行報告；回傳要寫進 SUMMARY["env"] 的一句話。

    只負責「印」與「摘要」：本機切換（developing≠now）驅動 [3/7]／[4/7] 的旗標仍由
    dev_start 自己算、自己消費——那兩步的正確判準是本機記憶，不是 git。
    """
    print_fn(f"    Now（當前平台）        ：{now}（host: {host}）")
    print_fn(f"    本機上次平台（狀態檔）  ：{developing or '（無紀錄，首次執行）'}"
             "——.dev_env_state.json 只記這台機器；"
             "雙 clone 拓撲下恆等於 Now，不代表專案上次在哪開發")
    local_switch = developing is not None and developing != now
    if local_switch:
        print_fn(f"    → 本機跨平台切換（共用工作目錄拓撲）：{developing} → {now}，將執行切換程序")
    verdict: Verdict | None = None
    if not is_repo:
        print_fn("    最近 commit 開發平台    ：（非 git repo，略）")
    else:
        verdict = infer_recent_platform(repo_root)
        if verdict.label is None:
            msg = (f"無法從 git 判定最近 commit 的開發平台（{verdict.evidence[0]}）"
                   "——請自行判讀 [2/7] 拉進的 commit 來自哪台機器")
            (warn or print_fn)(msg)
        else:
            via = f"{verdict.commit} 的 {verdict.evidence[0]}"
            if verdict.method == "heuristic" and verdict.depth > 1:
                via += f"，往回第 {verdict.depth} 個 commit（其間 {verdict.depth - 1} 個無訊號）"
            if verdict.host:
                via += f"，主機 {verdict.host}"
            print_fn(f"    最近 commit 開發平台    ：{verdict.label}"
                     f"（git {verdict.method_zh}：{via}）")
            if verdict.label != now:
                print_fn(f"    → 跨機切換（依 git）：{verdict.label} → {now}"
                         "——本機快取／venv 不需動作；依賴 hash 由 [4/7]、"
                         "§7 表② 指紋由 [6/7] 各自判定")
    git_label = verdict.label if verdict else None
    if local_switch:
        summary = f"{developing} → {now}（本機已切換）"
    elif git_label and git_label != now:
        summary = f"{git_label} → {now}（跨機切換，git 判定）"
    elif git_label:
        summary = f"{now}（無切換；git 最近 commit 亦為 {git_label}）"
    elif verdict is not None:
        summary = f"{now}（無本機切換；git 無法判定最近 commit 平台）"
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
