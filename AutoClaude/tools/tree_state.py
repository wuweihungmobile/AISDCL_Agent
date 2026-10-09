"""tools/tree_state.py — nightly 觀察樣本的「工作樹狀態」戳記（DEF-101-887）。

WHY：三本觀察期帳本（`.observability_history.jsonl`／`.drift_log_history.jsonl`／
`.ac4_history.jsonl`，皆 gitignore 的本機 SSOT）的樣本原本**不記任何工作樹狀態**。
收輪作業進行中被排程打到的「中間態」樣本，量到的是一棵從未存在於版本史上的半成品樹，
事後既無法與乾淨樣本區分、也就無法剔除；run_local_nightly.ps1 的 SAMPLE VALIDITY 區塊
只把這件事寫進 per-run log，帳本本身沒有。

本模組補兩半：collector 在**採樣當下**記 `tree` 欄（`capture()`）；判準端在算 streak 前
剔除 `tree.valid is False` 的樣本並回報剔除數（`exclude_invalid()`）。

`valid` 三態（unknown 不冤枉也不背書）：
  False  確定是中間態：採樣當下髒、起跑時髒、或這輪中途 HEAD 變了
  True   確定乾淨：採樣當下乾淨、起跑態乾淨（或無起跑態）、HEAD 沒變
  None   量不出來（git 失敗／逾時／起跑態 unknown）⇒ 判準端照常採計
舊樣本沒有 `tree` 欄 ⇒ 視為有效、**不追溯作廢**（沒有證據就不能改判；回溯不可判定）。

stdlib only、永不 raise：量測工具壞掉不得讓 nightly 採集跟著壞（採集比標記重要）。

起跑態（`START_ENV`）由 ps1 呼叫 `python tools/tree_state.py --start-token` 產出，與
`capture()` 共用同一套 dirty 判定（含下方自寫檔排除）——「什麼算髒」只有一個家。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

#: run_local_nightly.ps1 起跑時匯出的起跑態；格式 `<head>|<clean|dirty|unknown>`。
#: 由本檔 `--start-token` 產出時 head 是完整 sha；舊形態可能是 `--short` 縮寫，
#: 所以比對一律走前綴（見 `_same_commit`）。
START_ENV = "AUTOCLAUDE_NIGHTLY_TREE_START"
_STATES = ("clean", "dirty", "unknown")
_GIT_TIMEOUT_SECONDS = 60
#: nightly 自己會回寫的 tracked 檔：採樣時它們的差異不是「半成品樹」。perf-baseline 階段的
#: perf_baseline_lock.py 幾乎每晚重寫 AutoClaude/.perf_baseline.toml，而 drift／obs 兩個
#: collector 排在它後面（run_local_nightly.ps1 的 stage 順序；R210 QA 以真實語料 18 個
#: commit＋真程式碼端到端重現）。`top` 魔術字讓 repo_dir 為子目錄時 pathspec 也對。
_SELF_WRITTEN_PATHSPECS = (":(top,exclude)AutoClaude/.perf_baseline.toml",)
_HEX_RE = re.compile(r"[0-9a-fA-F]{4,64}")

# 預設在 monorepo 根下問 git：本檔住 AutoClaude/tools/，parents[2] 是 AutoClaude/ 的上一層。
# 理由：不帶 pathspec 的 `git status` 看的是**整個工作樹**，ps1 起跑時的 SAMPLE VALIDITY
# 區塊同口徑（在 AutoClaude/ 下跑一樣回整個 monorepo）；兩端口徑一致，起跑態與採樣態才可比。
_DEFAULT_REPO_DIR = Path(__file__).resolve().parents[2]


def _git(repo_dir: Path, *args: str) -> str | None:
    """跑一條唯讀 git；rc≠0／找不到 git／逾時／任何例外一律回 None（呼叫端判 unknown）。"""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            # 唯讀取樣不得搶 index.lock：nightly 長跑期間人或 agent 可能正在 git add／commit，
            # 而 status 預設會順手刷新 index、與對方爭鎖（⇒ 對方的 git 操作失敗）。
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except Exception:
        return None
    return proc.stdout if proc.returncode == 0 else None


def _parse_start(raw: str | None) -> tuple[str | None, str | None]:
    """`<head>|<state>` → (start_head, start_state)；缺值／格式不符＝(None, None)。

    head 可空（ps1 取不到 sha 時），此時只剩 state 可用；state 不在 clean／dirty／unknown
    之內＝整串視為垃圾、不採信任何一半（半截的起跑態比沒有更糟）。
    """
    head, sep, state = (raw or "").strip().partition("|")
    state = state.strip().lower()
    if not sep or state not in _STATES:
        return None, None
    head = head.strip()
    return (head if _HEX_RE.fullmatch(head) else None), state


def _same_commit(a: str, b: str) -> bool:
    """兩個 commit 名是否同一個；任一邊可能是 `--short` 縮寫，故比前綴（不分大小寫）。"""
    a, b = a.lower(), b.lower()
    return a.startswith(b) or b.startswith(a)


def capture(
    repo_dir: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """量當下工作樹，連同 ps1 匯出的起跑態合成一筆 `tree` 欄。永不 raise。

    回傳 schema 固定七鍵：head／state／dirty_entries／start_head／start_state／
    changed_during_run／valid（語意見模組 docstring）。`environ` 只用來讀起跑態，
    預設 `os.environ`；測試注入它就不必動行程環境。
    """
    repo = repo_dir if repo_dir is not None else _DEFAULT_REPO_DIR
    env = os.environ if environ is None else environ

    head_out = _git(repo, "rev-parse", "HEAD")
    head = head_out.strip() if head_out is not None else None
    head = head if head and _HEX_RE.fullmatch(head) else None

    porcelain = _git(repo, "-c", "core.quotepath=false", "status", "--porcelain", "--",
                     *_SELF_WRITTEN_PATHSPECS)
    dirty_entries: int | None = None
    state = "unknown"
    if porcelain is not None:
        dirty_entries = sum(1 for line in porcelain.splitlines() if line.strip())
        state = "dirty" if dirty_entries else "clean"

    start_head, start_state = _parse_start(env.get(START_ENV))
    changed: bool | None = None
    if start_head is not None and head is not None:
        changed = not _same_commit(start_head, head)

    valid: bool | None = None
    if state == "dirty" or start_state == "dirty" or changed is True:
        valid = False
    elif state == "clean" and start_state in (None, "clean"):
        valid = True

    return {
        "head": head,
        "state": state,
        "dirty_entries": dirty_entries,
        "start_head": start_head,
        "start_state": start_state,
        "changed_during_run": changed,
        "valid": valid,
    }


def is_invalid_sample(record: Mapping[str, Any]) -> bool:
    """這筆樣本是否被確認為中間態（`tree.valid is False`）。

    缺 `tree` 欄、`tree` 不是物件、`valid` 為 None 一律 False：舊樣本與量不出來的樣本
    都不追溯作廢（只有「有證據是髒的」才剔除，不確定時不冤枉）。
    """
    tree = record.get("tree")
    return isinstance(tree, Mapping) and tree.get("valid") is False


def exclude_invalid(
    records: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """剔除中間態樣本，回（保留列, 剔除數）；保留列維持原順序。"""
    kept: list[dict[str, Any]] = []
    excluded = 0
    for record in records:
        if is_invalid_sample(record):
            excluded += 1
        else:
            kept.append(record)
    return kept, excluded


def start_token(repo_dir: Path | None = None) -> str:
    """ps1 起跑時匯出的 `<head>|<state>`；規則與 `capture()` 同源（含自寫檔排除）。

    head 取不到時留空（只剩 state 可用）；git 整個失敗時回 `|unknown`——下游
    `_parse_start` 會把 unknown 當「不背書也不冤枉」。
    """
    snap = capture(repo_dir, environ={})
    return f"{snap['head'] or ''}|{snap['state']}"


def main(argv: list[str] | None = None) -> int:
    """CLI：`--start-token` 印起跑態（供 ps1 匯成 START_ENV）；無旗標印 `capture()` JSON。"""
    parser = argparse.ArgumentParser(description="nightly 觀察樣本的工作樹狀態戳記（DEF-101-887）")
    parser.add_argument("--start-token", action="store_true",
                        help="印 `<head>|<state>` 供 run_local_nightly.ps1 匯成起跑態")
    parser.add_argument("--repo-dir", type=Path, default=None, help="預設＝monorepo 根")
    args = parser.parse_args(argv)
    if args.start_token:
        print(start_token(args.repo_dir))
        return 0
    print(json.dumps(capture(args.repo_dir), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
