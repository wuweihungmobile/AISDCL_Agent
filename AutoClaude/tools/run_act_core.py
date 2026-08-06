#!/usr/bin/env python3
"""run_act_core.py — 在本機 Docker 內以 act 重現 GitHub Actions 單一核心
（macOS/Linux/Windows 共用）。

架構收斂案（仿 R12 DEF-101-070 ② local_ci_gate 模式）：原 tools/run_act.{sh,ps1} 為雙實作
（bash / PowerShell 各長一份業務邏輯，靠人工「對齊 run_act.sh」註解手動同步），本檔將全部
業務邏輯收斂為單一 Python 核心，兩支同名 .sh / .ps1 降為「確認直譯器 → 參數映射 → 轉呼叫
本檔 → 傳遞 exit code」的薄殼。

monorepo 根層接線（2026-07-10）：workflow 已遷至 monorepo 根層
.github/workflows/autoclaude-ci.yml → act 一律於 monorepo 根執行（讀根層 .actrc）。

對應 GitHub push/PR 觸發的 gating jobs（autoclaude-ci.yml）：
  test               pytest + LOC budget + import-linter（主閘門）
  claude-md-budget   CLAUDE.md <= 400 行 + snapshot freshness
  equivalence        equivalence snapshot（needs: test）
  pg-contract        PG 契約測（含 postgres service；CI 標 continue-on-error）

nightly/排程 job（mutation / pg-e2e / perf）以 `if: schedule` 排除，push 事件不會觸發，
本地請改用 tools/run_local_nightly.{sh,ps1}。

🔴 本輪（Windows 真機）落地的三件事，動本檔前務必先讀：

  (1) `--workflow <path>`：本檔原先把 workflow 寫死成模組常數，於是 `--list` 與整個
      執行路徑都只看得到 autoclaude-ci.yml 那一支；monorepo 根層現有 11 支 workflow，
      其餘 10 支（含 root-infra-ci.yml 這支承載根層 16 道守門的）**用本薄殼一個都碰
      不到**。新旗標讓任何一支都指得到；**未指定時的執行標的維持原值**（零行為變更），
      只有 `--list` 會額外印出全庫盤點（見 (2)）。
      薄殼側現況（誠實劃界）：`run_act.sh` 是 `"$@"` 全轉，旗標直接可用；`run_act.ps1`
      是 `[CmdletBinding()]` 顯式 param 映射，補一個參數會改變它的正規化內容 hash，
      而該 hash 釘在 tools/check_wrapper_thinness.py（本輪由另一個修復包擁有）⇒ 在
      薄殼補上參數之前，Windows 側請用環境變數 `RUN_ACT_WORKFLOW`（兩平台皆生效）。

  (2) `--list` 會在 act 自己那張表之後，另印一張**全庫 job 盤點**（本檔自己解析
      .github/workflows/*.yml，不再多開一次 act）。盤點含每個 job 的 runs-on 與
      「本機 act 有無通道」。理由：先前 `-List` 只列 9 個 job，讀者連另外 16 個 job
      的存在都不知道，於是「act ＝ 地端跑真 CI」這句話在文件裡看起來成立。

  (2b) `--event <名稱>`（預設 `push`，維持原值）：本檔原先把事件寫死成 `push`，而根層
      11 支 workflow 裡**有 5 支的 `on:` 完全不含 push**（arch-fitness／artifact-cleanup／
      drift-daily／fsm-chaos-nightly／pg-e2e-on-label）。act 對「事件對不上」的處置是
      **不跑任何 job 然後回 rc=0** ⇒ 那 7 個 job 會給出**零執行的假綠**。本輪實測逐字：
      `-Job pr-advisory` 除了一行 `Using docker host …` 之外零輸出，`ACT_RC=0`。
      這是 (1) 的連帶風險：把 workflow 指得到之後，那 5 支的假綠才第一次變得**碰得到**，
      故兩件事必須同批落地——`preflight()` 現在把事件對不上列為**阻斷**（見 (3)）。

  (3) 開跑前的 preflight（`preflight()`）——把 act **結構上做不到**的事在燒掉幾分鐘
      之前講清楚，且針對的三種失敗方向不同：
        · workflow 的 `on:` 不含本次事件：act **零執行卻回 rc=0**，是最難自己發現的
          假綠（沒有任何紅字，只是什麼都沒發生）⇒ 一律阻斷並指路 `--event`。
        · runs-on 不在 .actrc 的 `-P` 映射內（windows-latest／macos-latest）：act 會
          印一行 info 就**回 rc=0**＝假綠。這個方向必須阻斷（rc=1）。
        · 帶 `services:` 的 job：act 0.2.89 會 panic（nil container 解參考，上游 bug）
          ⇒ 指路 AutoClaude/docker-compose.ci.yml。指名單一 job 時阻斷；跑整份 push
          圖時只警告（其餘 job 的可跑性不由本檔代為裁決）。
        · runner 映像缺件（pwsh／gh／ruff）：act 會**真的紅**，不是假綠，故只警告並
          指路，不阻斷。

依序（7 步；步驟編號與訊息沿用收斂前 .sh/.ps1，第 4 步為本輪新增）：
  1. 定位 act（含 gh-act 退回；Windows 另探測 winget 安裝路徑）
  2. 確認 Docker daemon
  3. List 模式（--list / -List，列出 job ＋ 全庫盤點後結束）
  4. preflight（本機 act 結構上跑不動的先講清楚）
  5. 預先 pull 所需鏡像（繞過 act forcePull 對公開鏡像送無效認證的 401 bug）
  6. 空 .env 覆蓋（安全 + 忠實：GitHub runner 無 .env，避免注入個人憑證/偽 fail）
  7. 組裝並執行 act

  (4) **本機自建 runner 映像**（本輪；`RUNNER_IMAGE` ＋ `tools/act/Dockerfile`）：
      (3) 那條「映像缺件只警告不阻斷」的警語治的是症狀——真正的病是 `.actrc` 釘的
      中型映像**沒有 pwsh**，而 GitHub 的 ubuntu-latest runner 自帶。實測後果：
      root-infra-ci `act -n` rc=0（dry-run 只證明 YAML 寫對），真跑到第 3 個 step
      `exitcode 127`。本輪把 `.actrc` 指向 base ＋ pwsh／gh 的薄映像，於是那一格從
      「🟡 可解析」升級為真的跑得完。版本刻意釘成雲端 runner 當下實際在跑的那一版
      （pwsh 7.6.3／gh 2.96.0，取值方式見 Dockerfile 檔頭）——這是**提高**等價度。

  (5) **`--verify-all`：推 GitHub 前的一鍵本機全驗**（本輪）。它把跑得動的 job 全部
      真跑一次並寫進實跑帳本（`.act-runs/ledger.json`），跑不動的逐個列出替代驗證
      出口，最後印一張不許留白的總表。連帶讓 `--list` 的 ✅ 有了唯一合法來源：
      **那次執行自己留下的紀錄**（見 `record_run()` 上方對「為何只有這個入口能寫」
      的論證）。任何靜態分析都不得把自己升格成 ✅。

用法（一般經薄殼呼叫；直接呼叫亦可）：
  python tools/run_act_core.py --build-image   # 先建本機 runner 映像（可重跑；秒級 cache 命中）
  python tools/run_act_core.py --verify-all    # 🔴 推 GitHub 前的一鍵本機全驗
  python tools/run_act_core.py --job test     # 最快：只跑主測試閘門
  python tools/run_act_core.py                 # 完整：跑 push 全部 job（含 PG 契約）
  python tools/run_act_core.py --list          # 列出 job ＋ 全庫盤點（含實跑帳本）
  python tools/run_act_core.py --dry-run       # 只解析不執行
  python tools/run_act_core.py --workflow .github/workflows/root-infra-ci.yml \
      --job root-infra                         # 指定別的 workflow
  python tools/run_act_core.py --workflow .github/workflows/aisdlc-sdd-drift-daily.yml \
      --event schedule --job daily             # 無 push 觸發的 workflow 需指定事件
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent          # AutoClaude/tools
MONOREPO_ROOT = SCRIPT_DIR.parent.parent               # 本腳本上兩層 = monorepo 根
WORKFLOW = ".github/workflows/autoclaude-ci.yml"
WORKFLOW_DIR = ".github/workflows"
#: `run_act.ps1` 補上 -Workflow 參數之前，Windows 側指定 workflow 的唯一入口（見檔頭 (1)）。
WORKFLOW_ENV = "RUN_ACT_WORKFLOW"
#: act 預設模擬的 GitHub 事件。改預設＝改所有既有呼叫端的行為，故只由 `--event` 覆寫。
DEFAULT_EVENT = "push"
#: `run_act.ps1` 補上 -Event 參數之前，Windows 側指定事件的唯一入口（同 WORKFLOW_ENV）。
#: 少了這一個，Windows 側對「無 push 觸發的那 5 支 workflow」連指都指不到。
EVENT_ENV = "RUN_ACT_EVENT"
#: act 實際會起的 runner 映像＝**本機自建薄映像**（`tools/act/Dockerfile`）。
#: 這個字面值是 `.actrc` 兩行 `-P` 的 SSOT，兩處必須逐字相同
#: （機械鎖＝`tools/tests/test_act_local_runner_image.py`）。
RUNNER_IMAGE = "aisdcl-act/ubuntu:act-latest"
#: 上者的 base——`catthehacker` 的中型映像。它**沒有** pwsh，而 GitHub 的 ubuntu-latest
#: runner 自帶 ⇒ root-infra-ci 的 pwsh 守門 step 在它上面一律 `exitcode 127`。
ACT_BASE_IMAGE = "catthehacker/ubuntu:act-latest"
#: 自建映像的 Dockerfile 與 build context（context 內只有 Dockerfile，刻意極小）。
ACT_DOCKERFILE = "tools/act/Dockerfile"
ACT_BUILD_CONTEXT = "tools/act"
PG_IMAGE = "pgvector/pgvector:pg17"

#: `.actrc` 現釘的 runner 映像缺、而 GitHub 真 ubuntu-latest 有的工具。
#: 🔴 本輪由三支收為一支，兩個方向的訂正各有取證，別讀成「順手縮小了警告面」：
#:   · pwsh／gh 移出＝**缺口已被補上**：自建映像實測 `pwsh 7.6.3`／`gh 2.96.0`
#:     （`docker run --rm <RUNNER_IMAGE> bash -lc 'pwsh --version; gh --version'`），
#:     且版本刻意釘成雲端 runner 當下實際在跑的那一版（見 tools/act/Dockerfile 檔頭）。
#:   · ruff 移出＝**原本的歸類就是錯的**：本清單自陳收「雲端有、地端沒有」的工具，
#:     而實查 actions/runner-images 的 Ubuntu2404-Readme.md，ruff **不在**雲端 runner
#:     的預裝清單裡（同一份 grep 對 `Ruff` 零命中）；root-infra-ci 第 16 道自己
#:     `pip install 'ruff==0.15.21'`。把它留在這裡會讓警告指向一個不存在的落差。
#: 那 ruff 為什麼還在？因為 `command -v ruff` 在映像內仍是 not found，而本清單的**消費
#: 語意**是「job 的 YAML 提到它、映像裡卻沒有 ⇒ 該 step 可能 127」——對 ruff 而言那一步
#: 會不會紅取決於容器有沒有網路裝得下去，仍值得先講一聲。刻意**不**預裝：預裝等於遮蔽
#: 「那行 pip install 壞掉」這個雲端會紅、地端卻綠的差異（見 Dockerfile 檔頭同一段）。
#: 缺件會讓 job 在中途 `exitcode 127`——**真紅不是假綠**，故本清單只驅動警告、不驅動阻斷。
RUNNER_IMAGE_MISSING_TOOLS = ("ruff",)

#: 非 ubuntu runner 的替代驗證出口。**鍵是 runner 標籤（2 筆）而非 job（4 筆）**：
#: 以 job 為鍵的清單每新增一個 macOS/Windows job 就要補一列，而漏補的方向是「留白」
#: ——那正是要治的病。以標籤為鍵時新 job 自動繼承正確的替代出口，沒有會腐化的第二份
#: 逐 job 清單。（`tools/tests/test_smoke_ci_sync.py::_ACT_NO_LOCAL_RUNNER_JOBS` 是**另一
#: 件事**：它鎖的是「零通道 job 有沒有被逐個具名登記」＝登記完整性，本表答的是「那要
#: 改用什麼驗」＝處置指路，粒度刻意不同，不是同一份清單抄兩遍。）
NO_LOCAL_CHANNEL_ALTERNATIVES = {
    "macos-latest": (
        "mac 真機跑 tools/macos_smoke_local.sh（深度回歸＝"
        "AutoClaude/tools/run_local_nightly.sh）。🔴 本機（Windows）對 macOS **零覆蓋**"
    ),
    "windows-latest": (
        "Windows 真機跑 tools/windows_smoke_local.ps1（深度回歸＝"
        "AutoClaude/tools/run_local_nightly.ps1）。🔴 該腳本自帶 PS 5.1 引擎守衛，"
        "須顯式外呼 powershell.exe，不能在 pwsh 7.x 內直接跑"
    ),
}

# job 起始行（workflows 的 job 鍵一律縮排 2 空格）／`runs-on:`／`services:`。
_JOB_RE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$", re.MULTILINE)
_RUNS_ON_RE = re.compile(r"^    runs-on:\s*(\S+)\s*$", re.MULTILINE)
_SERVICES_RE = re.compile(r"^    services:\s*$", re.MULTILINE)
# `.actrc` 的 runner 映射鍵：`-P <label>=<image>`。
_ACTRC_RUNNER_RE = re.compile(r"^-P\s+([^=\s]+)=", re.MULTILINE)
# `on:` 區塊（至下一個頂層鍵為止；`on` 在 YAML 1.1 是布林字面，故亦可能被引號包起來）
# 與其一級子鍵＝觸發事件名。
_ON_BLOCK_RE = re.compile(r"^(?:on|\"on\"|'on'):.*?(?=^\S)", re.MULTILINE | re.DOTALL)
_EVENT_RE = re.compile(r"^  ([a-z_]+):", re.MULTILINE)

# platform_utils 位於 monorepo 根 tools/lib/ 子目錄，本檔在 AutoClaude/tools/ 下，
# 需顯式插入 sys.path 才能 import——手法對齊本輪其他核心檔案既有慣例（R17
# DEF-101-231 觀察點 1+2：收斂 is_windows/os_label/venv_python_path 平台判斷邏輯
# 的第二次重複）。
sys.path.insert(0, str(MONOREPO_ROOT / "tools" / "lib"))
import platform_utils  # noqa: E402


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--job", default="", help="只跑單一 job（例：test）")
    parser.add_argument("--list", action="store_true", help="列出所有 job 後結束")
    parser.add_argument("--dry-run", action="store_true", help="只解析不執行（傳 -n 給 act）")
    parser.add_argument(
        "--workflow",
        default="",
        help=(
            "要跑哪一支 workflow（repo 相對路徑；預設 " + WORKFLOW + "）。"
            "亦可用環境變數 " + WORKFLOW_ENV + " 指定——Windows 薄殼尚未轉這個旗標"
        ),
    )
    parser.add_argument(
        "--event",
        default=DEFAULT_EVENT,
        help=(
            "模擬哪個 GitHub 事件（預設 " + DEFAULT_EVENT + "）。無 push 觸發的 workflow "
            "必須指定，否則 act 零執行卻回 rc=0"
        ),
    )
    parser.add_argument(
        "--build-image", action="store_true",
        help=f"（重）建本機 act runner 映像 {RUNNER_IMAGE}（來源 {ACT_DOCKERFILE}）後結束",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="搭配 --build-image：不吃 docker layer cache（改了 Dockerfile 的 ARG 版本號時必用）",
    )
    parser.add_argument(
        "--verify-all", action="store_true",
        help="一鍵推送前本機全驗：跑得動的 job 全部真跑並記帳，跑不動的逐個列出替代驗證出口",
    )
    return parser.parse_args(argv)


def selected_workflow(args: argparse.Namespace) -> str:
    """使用者**顯式**指定的 workflow；未指定回空字串（＝沿用預設，見 `run_workflow()`）。

    刻意把「顯式指定」與「實際跑哪一支」分成兩個函式：`--list` 未顯式指定時要印全庫
    盤點（顯式指定才縮到那一支），而執行路徑未指定時必須維持原本的預設值不變。
    """
    return (getattr(args, "workflow", "") or os.environ.get(WORKFLOW_ENV, "")).strip()


def run_workflow(args: argparse.Namespace) -> str:
    """實際交給 act 執行的 workflow——未指定即沿用 `WORKFLOW`（零行為變更）。"""
    return selected_workflow(args) or WORKFLOW


def run_event(args: argparse.Namespace) -> str:
    """實際交給 act 的事件——旗標 > 環境變數 > `DEFAULT_EVENT`（零行為變更）。"""
    flag = (getattr(args, "event", "") or "").strip()
    if flag and flag != DEFAULT_EVENT:
        return flag
    return os.environ.get(EVENT_ENV, "").strip() or flag or DEFAULT_EVENT


def workflow_files() -> list[Path]:
    """`.github/workflows/*.yml` 全部（排序後），供全庫盤點與 preflight 共用。"""
    return sorted((MONOREPO_ROOT / WORKFLOW_DIR).glob("*.yml"))


def workflow_jobs(path: Path) -> dict[str, str]:
    """`{job id: 該 job 的 YAML 區塊原文}`。

    只從 `jobs:` 之後開始掃，避免 `on:`／`env:` 區塊裡同縮排的鍵被誤當 job；抓不到
    `jobs:` 時退回整檔（fail-open 但不靜默：呼叫端拿到的 job 集合會明顯異常）。
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    head = text.find("\njobs:\n")
    body = text[head:] if head >= 0 else text
    hits = list(_JOB_RE.finditer(body))
    return {
        m.group(1): body[m.end(): (hits[i + 1].start() if i + 1 < len(hits) else len(body))]
        for i, m in enumerate(hits)
    }


def workflow_events(path: Path) -> set[str]:
    """該 workflow `on:` 區塊的一級鍵＝它接受的觸發事件集合。

    抓不到時回**空集合＝不設限**（fail-open）：本函式唯一的用途是把「事件對不上 ⇒
    零執行假綠」擋下來；解析式漂移時不得反過來把合法的執行擋掉（阻斷級判準的失效
    方向必須是放行，不是把人鎖在門外）。
    """
    m = _ON_BLOCK_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    if m is None:
        return set()
    events = set(_EVENT_RE.findall(m.group(0)))
    if events:
        return events
    # 行內形態：`on: push` ／ `on: [push, pull_request]`
    head = m.group(0).split("\n", 1)[0].split(":", 1)[1]
    return {t.strip(" []'\"") for t in head.split(",") if t.strip(" []'\"")}


def mapped_runners() -> set[str]:
    """`.actrc` 裡 `-P <label>=<image>` 的 label 全集＝本機 act 認得的 runner 標籤。"""
    actrc = MONOREPO_ROOT / ".actrc"
    if not actrc.is_file():
        return set()
    return set(_ACTRC_RUNNER_RE.findall(actrc.read_text(encoding="utf-8", errors="replace")))


def job_inventory() -> list[tuple[str, str, str, bool, bool]]:
    """全庫盤點：`[(workflow 檔名, job id, runs-on, 本機 act 有無 runner, 有無 services)]`。"""
    runners = mapped_runners()
    rows: list[tuple[str, str, str, bool, bool]] = []
    for path in workflow_files():
        for job, block in workflow_jobs(path).items():
            m = _RUNS_ON_RE.search(block)
            label = m.group(1) if m else "?"
            rows.append((path.name, job, label, label in runners, bool(_SERVICES_RE.search(block))))
    return rows


# ── job 分類（`--list` 與 `--verify-all` 的**唯一**判準實作）─────────────────────
# 兩個消費者共用同一支：兩份各自演化的分類邏輯會讓「盤點說可跑、驗證卻跳過」這種
# 自相矛盾變成可能，而它在畫面上看起來完全正常。
CAT_VERIFIED = "verified"        # 本機實跑過且 rc=0，且 workflow 自那次之後沒變
CAT_FAILED = "failed"            # 本機實跑過但 rc!=0
CAT_STALE = "stale"              # 實跑過，但 workflow 已變動 ⇒ 那筆綠不再代表現況
CAT_RUNNABLE = "runnable"        # 結構上跑得起來，但從未實跑過
CAT_NO_RUNNER = "no-runner"      # runs-on 不在 .actrc 映射內（macOS／Windows）
CAT_SERVICES = "services"        # 帶 services: ⇒ act 0.2.89 panic
CAT_WRONG_EVENT = "wrong-event"  # 本次事件不在該 workflow 的 on: 內 ⇒ 零執行假綠

#: 分類 → 顯示徽章。`--verify-all` 的總表與 `--list` 用同一組字面，兩處讀起來一致。
CAT_BADGE = {
    CAT_VERIFIED: "✅ 已實跑通過",
    CAT_FAILED: "❌ 已實跑但失敗",
    CAT_STALE: "🟡 證據過期（實跑後 workflow 已改）",
    CAT_RUNNABLE: "🟡 可解析未實跑",
    CAT_NO_RUNNER: "❌ 結構上無本機通道",
    CAT_SERVICES: "❌ 帶 services: 無本機 act 通道",
    CAT_WRONG_EVENT: "⚠️ 需 --event",
}
#: 「本機 act 跑得起來」的分類集合——`verify_all()` 要跑的就是這幾格。
RUNNABLE_CATS = frozenset({CAT_VERIFIED, CAT_FAILED, CAT_STALE, CAT_RUNNABLE})


def classify_job(
    wf: str, job: str, label: str, has_runner: bool, has_services: bool,
    events: set[str], event: str, ledger: dict[str, dict[str, object]],
) -> tuple[str, list[str]]:
    """回傳 `(分類, 全部障礙／證據說明)`。

    🔴 `notes` 刻意**累加**而非 if/elif 擇一：一個 job 可以同時中兩個障礙（實測：
    pg-e2e-on-label 既無 push 觸發又帶 `services:`）。擇一等於讓先命中的那個把後面的
    蓋掉，使用者排除完第一個才發現還有第二個——Scan-H⑦ 早退遮蔽的同一形態，且遮蔽
    方向是「看起來只有一個問題」。**分類**取最先命中的阻斷原因（要放進哪一格只能有
    一個答案），但**說明**一個都不吞。
    """
    notes: list[str] = []
    if events and event not in events:
        notes.append(
            f"本 workflow 的 on: 是 {','.join(sorted(events))}，不含 `{event}`"
            f"——不加 --event 會零執行卻回 rc=0（假綠）"
        )
    if not has_runner:
        notes.append(
            f"runs-on={label} 不在 .actrc 的 -P 映射內。替代驗證＝"
            + NO_LOCAL_CHANNEL_ALTERNATIVES.get(
                label, "（本表未登記該 runner 的替代出口——請補 NO_LOCAL_CHANNEL_ALTERNATIVES）"
            )
        )
    if has_services:
        notes.append(
            "帶 services:，act 0.2.89 對它 panic（run_context.go 對 nil container 解參考，"
            "上游 bug）。替代驗證＝`docker compose -f AutoClaude/docker-compose.ci.yml up -d`"
            " ＋本機 pytest"
        )
    if not has_runner:
        return CAT_NO_RUNNER, notes
    if has_services:
        return CAT_SERVICES, notes
    if events and event not in events:
        return CAT_WRONG_EVENT, notes
    entry = ledger.get(f"{wf}::{job}")
    if not entry:
        return CAT_RUNNABLE, notes
    at, rc = entry.get("at", "?"), entry.get("rc")
    notes.append(f"最近一次本機實跑：{at} rc={rc}（映像 {entry.get('image', '?')}）")
    if workflow_fingerprint(MONOREPO_ROOT / WORKFLOW_DIR / wf) != entry.get("wf_sha"):
        notes.append("⚠️ 該次實跑之後 workflow 檔已變動 ⇒ 那筆結論不再代表現況，請重驗")
        return CAT_STALE, notes
    return (CAT_VERIFIED if rc == 0 else CAT_FAILED), notes


def classified_inventory(event: str = DEFAULT_EVENT) -> list[tuple[str, str, str, str, list[str]]]:
    """`[(workflow, job, runs-on, 分類, 說明)]`——`--list` 與 `--verify-all` 的共同輸入。"""
    ledger = read_ledger()
    events_by_wf = {p.name: workflow_events(p) for p in workflow_files()}
    return [
        (wf, job, label,
         *classify_job(wf, job, label, has_runner, has_services,
                       events_by_wf.get(wf, set()), event, ledger))
        for wf, job, label, has_runner, has_services in job_inventory()
    ]


def print_job_inventory(event: str = DEFAULT_EVENT) -> None:
    """把每個 job 落在哪一格印在使用者眼前，而不是留白。

    🔴 「🟡 可解析」**不等於「能跑完」**——它判的是三件結構事實（runner／services／
    事件），判不到「映像裡有沒有那支工具」。R77 實測：root-infra dry-run rc=0，真跑到
    第 3 個 step（需要 pwsh）`exitcode 127`。故 ✅ 這一格**只**來自 `verify_all()` 寫下的
    實跑帳本，任何靜態分析都不得把自己升格成 ✅。
    """
    rows = classified_inventory(event)
    print(f"[run_act] 全庫 job 盤點（{WORKFLOW_DIR}/*.yml 共 {len(rows)} 個 job；"
          f"事件＝{event}）：")
    for wf, job, label, cat, notes in rows:
        print(f"  {wf:34s} {job:36s} {label:16s} {CAT_BADGE[cat]}")
        for note in notes:
            print(f"       └─ {note}")
    tally = {cat: sum(1 for r in rows if r[3] == cat) for cat in CAT_BADGE}
    print("[run_act] 小計：" + "／".join(
        f"{CAT_BADGE[c]} {n}" for c, n in tally.items() if n
    ))
    print(
        f"[run_act] 單支執行：--workflow {WORKFLOW_DIR}/<檔名> --job <job>"
        f"（標 ⚠️ 者另需 --event <事件>）。"
        f"一鍵把「跑得動的全部跑一次並記帳」：--verify-all。"
    )
    print(
        "[run_act] 🔴 ✅ 只代表**這台機器**上那一次執行的逐步輸出真的走完了，且 workflow "
        "自那次之後沒改過；它不代表雲端會綠（act 與雲端仍有已知落差：不連 artifact 儲存、"
        "gh API 無 token、`services:` 走 docker compose 替代）。"
    )


def preflight(workflow: str, job: str, event: str = DEFAULT_EVENT) -> tuple[list[str], list[str]]:
    """回傳 `(阻斷級問題, 警告)`——**先收集完再回報**，不在第一筆就 return。

    早退在這裡特別危險：一次只講一個問題會讓使用者修一輪撞一次，而其中「假綠」那兩類
    問題（事件對不上、runs-on 無映射）恰恰是使用者最不會自己發現的——它們沒有任何紅字，
    只是什麼都沒發生然後回 rc=0。
    """
    blockers: list[str] = []
    warnings: list[str] = []
    path = MONOREPO_ROOT / workflow
    if not path.is_file():
        return [f"workflow 不存在：{workflow}（--workflow 請給 repo 相對路徑）"], warnings
    events = workflow_events(path)
    if events and event not in events:
        blockers.append(
            f"{workflow} 的 on: 觸發事件是 {', '.join(sorted(events))}，**不含 `{event}`** "
            f"—— act 對事件對不上的 workflow 是「不跑任何 job 然後回 rc=0」，你會拿到一個"
            f"零執行的假綠（畫面上只有一行 Using docker host）。請加 "
            f"--event {sorted(events)[0]}。"
        )
    jobs = workflow_jobs(path)
    if job and job not in jobs:
        # 刻意 append 而非 return：上面可能已收了「事件對不上」那一筆，早退會把它吞掉
        # ——而被吞掉的正好是使用者最不會自己發現的那一類（Scan-H⑦ 早退遮蔽訊號）。
        blockers.append(f"{workflow} 內沒有 job `{job}`；現有：{', '.join(sorted(jobs))}")
        return blockers, warnings
    selected = {job: jobs[job]} if job else jobs
    runners = mapped_runners()
    for name, block in sorted(selected.items()):
        m = _RUNS_ON_RE.search(block)
        label = m.group(1) if m else ""
        services = bool(_SERVICES_RE.search(block))
        if label and label not in runners:
            msg = (
                f"{name}：runs-on={label} 不在 .actrc 的 -P 映射內 —— act 只會印一行 "
                f"「Skipping unsupported platform」然後**回 rc=0**（假綠）。本機無此 "
                f"runner，這個 job 結構上只能靠雲端或該平台真機。"
            )
            (blockers if job else warnings).append(msg)
        if services:
            msg = (
                f"{name}：帶 services:，act 0.2.89 對它會 panic（run_context.go 對 nil "
                f"container 解參考，上游 bug，repo 內無正確程式修法）—— 請改走 "
                f"`docker compose -f AutoClaude/docker-compose.ci.yml up -d` ＋本機 pytest。"
            )
            (blockers if job else warnings).append(msg)
        missing = [t for t in RUNNER_IMAGE_MISSING_TOOLS if re.search(rf"(?<![\w-]){t}\b", block)]
        if missing:
            warnings.append(
                f"{name}：疑似用到 {'/'.join(missing)}，而 {RUNNER_IMAGE} 沒有這些工具。"
                f"若該 step 直接呼叫它 ⇒ `exitcode 127`（真紅，非假綠）。\n"
                f"    現況（實測，別當成待辦）：本清單只剩 ruff，而 root-infra-ci 第 16 道"
                f"自己會 `pip install 'ruff==0.15.21'`，容器有網路就裝得起來——刻意不預裝，"
                f"預裝會遮蔽「那行 pip install 壞掉」這個雲端會紅、地端卻綠的差異。\n"
                f"    真的需要在映像內補一支工具時：改 {ACT_DOCKERFILE} 後 "
                f"`--build-image --no-cache` 重建（不要改 workflow 去遷就地端——雲端 runner "
                f"本來就有的東西，不該為了地端讓雲端每次 push 多裝一次）。"
            )
    return blockers, warnings


def _gh_act_extension_installed() -> bool:
    """gh extension list 是否含 gh-act（'gh-act' 子字串同時涵蓋 'nektos/gh-act'）。

    gh 未安裝時 subprocess 擲 FileNotFoundError（POSIX）或 OSError（Windows），
    對齊收斂前 .sh 的 `gh extension list 2>/dev/null || true` 容錯語意。
    """
    try:
        proc = subprocess.run(
            ["gh", "extension", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        ext_list = proc.stdout or ""
    except OSError:
        ext_list = ""
    return "gh-act" in ext_list


def resolve_act() -> list[str] | None:
    """定位 act（含 gh-act 退回；Windows 另探測 winget 安裝路徑，對齊收斂前 .ps1）。

    回傳指令前綴（['act'] 或 ['gh', 'act'] 等），未尋獲回傳 None。
    """
    exe = shutil.which("act")
    if exe:
        return [exe]
    if platform_utils.is_windows():
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            glob_pattern = "Microsoft/WinGet/Packages/nektos.act_*/act.exe"
            found = sorted(Path(local_appdata).glob(glob_pattern))
            if found:
                return [str(found[0])]
    if _gh_act_extension_installed():
        return ["gh", "act"]
    return None


def _print_install_hint() -> None:
    print("[run_act] act 未安裝。請擇一安裝：", file=sys.stderr)
    if platform_utils.is_windows():
        print("  winget install --id nektos.act -e", file=sys.stderr)
        print("  scoop install act", file=sys.stderr)
    else:
        print("  brew install act", file=sys.stderr)
    print(
        "  gh extension install https://github.com/nektos/gh-act   # 再以 gh act 呼叫",
        file=sys.stderr,
    )


def _run_quiet(cmd: list[str]) -> int:
    """靜音執行（探測用途）；命令不存在時視為失敗，對齊 shell 端「找不到指令即非 0」語意。"""
    try:
        return subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
    except OSError:
        return 1


def check_docker() -> bool:
    """確認 Docker daemon 是否可連線（`docker info`）。"""
    return _run_quiet(["docker", "info"]) == 0


def image_ready(image: str) -> bool:
    return _run_quiet(["docker", "image", "inspect", image]) == 0


def build_runner_image(no_cache: bool = False) -> int:
    """`docker build` 出 `RUNNER_IMAGE`（tools/act/Dockerfile；WHY 見該檔檔頭）。

    可重跑：docker layer cache 命中時是秒級；改了 Dockerfile 的 `ARG` 版本號後
    **必須**帶 `no_cache=True`，否則 cache 會沿用舊版本的那一層。
    """
    dockerfile = MONOREPO_ROOT / ACT_DOCKERFILE
    if not dockerfile.is_file():
        print(f"[run_act] 找不到 {ACT_DOCKERFILE} —— 自建 runner 映像的唯一來源缺席。",
              file=sys.stderr)
        return 1
    cmd = ["docker", "build", "-f", str(dockerfile), "-t", RUNNER_IMAGE]
    if no_cache:
        cmd.append("--no-cache")
    cmd.append(str(MONOREPO_ROOT / ACT_BUILD_CONTEXT))
    print(f"[run_act] 建置本機 act runner 映像：{' '.join(cmd)}")
    print(f"[run_act] （base＝{ACT_BASE_IMAGE}；補 pwsh／gh 兩支雲端 runner 自帶、"
          f"base 沒有的工具。首次含 base 下載約 2.3GB）")
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        print(f"[run_act] ❌ docker build {RUNNER_IMAGE} 失敗（rc={rc}）。", file=sys.stderr)
    return rc


def pull_image(image: str) -> int:
    """取得本地缺少的鏡像——**`RUNNER_IMAGE` 走 build，其餘走 `docker pull`**。

    🔴 為何是分派而不是兩個各自被呼叫的函式：`ensure_images()` 的職責是「act 開跑前
    本地要有的鏡像都在」，取得方式（pull／build）是實作細節。把分派放在這一層，
    `ensure_images()` 與它的呼叫端一個字都不用改，也不會多出第二條「誰負責確保映像在」
    的路徑——多一條就多一個會腐化的分歧面（本 repo 反覆在收斂的正是這個形態）。
    函式名沿用 `pull_image`：`AutoClaude/tests/tools/test_run_act_core.py` 以這個名字
    monkeypatch 並斷言 `ensure_images()` 對它的呼叫序列，改名會讓那組行為鎖失去對象。
    """
    if image == RUNNER_IMAGE:
        print(f"[run_act] 本地缺鏡像 {image}（本機自建，pull 不到）→ docker build…")
        return build_runner_image()
    print(f"[run_act] 本地缺鏡像 {image} → docker pull（首次約 1~1.5GB）…")
    rc = subprocess.run(["docker", "pull", image]).returncode
    if rc != 0:
        print(f"[run_act] docker pull {image} 失敗。", file=sys.stderr)
    return rc


# ── 實跑帳本（本輪新增）──────────────────────────────────────────────────────
# WHY：`--list` 原本只有「🟡 act 可解析」這一格，而它判的是三件**結構**事實
# （runner／services／事件），判不到「這支到底有沒有真的在本機跑完過」。R77 已用一次
# 實測證明兩者不同：root-infra dry-run rc=0，真跑第 3 步 rc=127。要讓 `--list` 說得出
# 「✅ 已實跑通過」，唯一誠實的來源是**那次執行自己留下的紀錄**，不是任何人寫在文件裡
# 的宣稱——所以本帳本只由 `verify_all()`（唯一以「產生證據」為目的的指令）寫入。
#
# 🔴 為何刻意**不**讓單支 `--job` 執行也寫帳本：`main()` 在
# `AutoClaude/tests/tools/test_run_act_core.py` 裡被呼叫時 `run_act` 是 mock 的
# （`lambda *a, **k: 0`）——那條路徑寫下的 rc=0 會是一筆**從未真的執行過**的 ✅。
# 帳本一旦能被 mock 餵出綠燈，它就從證據退化成裝飾。`verify_all()` 不被任何既有測試
# 呼叫，是目前唯一「寫進去的一定是真跑過」的入口。
#
# 新鮮度：每筆記下當時 workflow 檔的 sha256 前 12 碼。workflow 改過之後那筆證據就過期，
# `--list` 會把它降級回 🟡 而不是繼續顯示 ✅（過期的綠比沒有綠更危險）。
LEDGER_REL = ".act-runs/ledger.json"


def ledger_path() -> Path:
    return MONOREPO_ROOT / LEDGER_REL


def workflow_fingerprint(path: Path) -> str:
    """workflow 檔內容指紋（sha256 前 12 碼）——證據新鮮度的判準。"""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except OSError:
        return ""


def read_ledger() -> dict[str, dict[str, object]]:
    """讀實跑帳本；不存在／壞掉一律回空 dict（＝一筆 ✅ 都不敢宣稱）。

    壞掉時回空而不是 raise：帳本的失效方向必須是「少宣稱」，不是「擋住所有人」。
    """
    try:
        data = json.loads(ledger_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def record_run(wf_name: str, job: str, event: str, rc: int) -> None:
    """把一次**真跑**寫進帳本（唯一寫入者＝`verify_all()`）。"""
    ledger = read_ledger()
    wf_path = MONOREPO_ROOT / WORKFLOW_DIR / wf_name
    ledger[f"{wf_name}::{job}"] = {
        "rc": rc,
        "event": event,
        "image": RUNNER_IMAGE,
        "wf_sha": workflow_fingerprint(wf_path),
        "at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n"：本 repo 對 Python 寫檔的既有紀律（Windows 預設會寫成 CRLF）。
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def ensure_images(job: str) -> int:
    """5. 預先 pull 所需鏡像（繞過 act forcePull 對公開鏡像送無效認證的 401 bug）。"""
    needed = [RUNNER_IMAGE]
    if not job:
        needed.append(PG_IMAGE)
    for image in needed:
        if image_ready(image):
            print(f"[run_act] 鏡像已就緒：{image}")
        else:
            rc = pull_image(image)
            if rc != 0:
                return 1
    return 0


def run_act(
    act_prefix: list[str],
    job: str,
    dry_run: bool,
    empty_env_path: str,
    workflow: str = WORKFLOW,
    event: str = DEFAULT_EVENT,
) -> int:
    """7. 組裝並執行 act。

    `workflow` 與 `event` 刻意放在最後且帶預設值：既有呼叫端（含 AutoClaude/tests/tools/
    test_run_act_core.py 的四位置引數斷言）不必改一個字，未指定就是原本那支／原本那個事件。
    """
    act_args = [event, "-W", workflow, "--pull=false", "--env-file", empty_env_path]
    if job:
        act_args += ["-j", job]
    if dry_run:
        act_args += ["-n"]
    print(f"[run_act] 執行: {' '.join(act_prefix + act_args)}")
    return subprocess.run(act_prefix + act_args).returncode


def verify_all(
    act_prefix: list[str], event: str, empty_env_path: str, workflow_filter: str = "",
) -> int:
    """一鍵「推 GitHub 前的本機全驗」：跑得動的全部真跑一次並記帳，跑不動的逐個講明。

    這一層刻意做得很薄——它不是新框架，只是把既有的 `classified_inventory()`（判準）
    與 `run_act()`（執行）串起來，再加一張**不許留白**的結案總表。設計上守兩條：

      1. **不得靜默略過**：結構上驗不了的 job（macOS／Windows runner、帶 `services:`、
         事件對不上）一樣列進總表並附替代驗證出口。本 repo 最大宗的缺陷形態是「鎖存在
         但沒有鑑別力」與「早退遮蔽訊號」，而「沒被列出來」正是最省力的遮蔽方式。
      2. **rc 語意單一**：只要有任何一支「該跑」的 job 失敗就回非 0；「跑不動」不影響
         rc（那不是本次改動造成的紅，把它算進 rc 只會逼人整條停用本指令）——但它在總表
         上是 ❌，讀者一眼看得到覆蓋面的洞。
    """
    rows = classified_inventory(event)
    if workflow_filter:
        wanted = Path(workflow_filter).name
        rows = [r for r in rows if r[0] == wanted]
        if not rows:
            print(f"[run_act] ❌ --workflow {workflow_filter} 盤不到任何 job", file=sys.stderr)
            return 1
    todo = [r for r in rows if r[3] in RUNNABLE_CATS]
    print(f"[run_act] 一鍵全驗：{len(rows)} 個 job，其中 {len(todo)} 支本機 act 跑得動"
          f"（事件＝{event}）。開跑——")
    failures: list[str] = []
    for i, (wf, job, _label, _cat, _notes) in enumerate(todo, 1):
        print(f"[run_act] ── [{i}/{len(todo)}] {wf}::{job}")
        rc = run_act(act_prefix, job, False, empty_env_path, f"{WORKFLOW_DIR}/{wf}", event)
        record_run(wf, job, event, rc)
        if rc != 0:
            failures.append(f"{wf}::{job}（rc={rc}）")
    # 總表由**剛寫完的帳本**重新分類而來，不是把迴圈內的變數再抄一遍：抄一遍就是第二個
    # 會與帳本分歧的來源，而分歧時畫面上完全看不出來。
    print("[run_act] ════ 本機驗證結案總表 ════")
    print_job_inventory(event)
    if failures:
        print(f"[run_act] ❌ 本機全驗未通過（{len(failures)} 支該跑而失敗）："
              f"{'；'.join(failures)}", file=sys.stderr)
        return 1
    print(f"[run_act] ✅ 本機全驗通過：{len(todo)} 支該跑的 job 全數 rc=0。")
    print("[run_act] 🔴 但這**不等於**雲端會綠——上表 ❌／⚠️ 那幾格結構上沒有本機通道，"
          "各自的替代驗證出口已逐行列在表上，請照著補完再 push。")
    return 0


def main(argv: list[str] | None = None) -> int:
    # 自身 stdout/stderr best-effort UTF-8 + 行緩衝：非 TTY（管線/log 擷取）下 Python 預設
    # 對 stdout 做 full buffering，會讓 stdout 進度訊息與 stderr 錯誤訊息交錯錯亂
    # （對齊 tools/local_ci_gate.py main() 同款收斂）。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        except (AttributeError, OSError, ValueError):
            pass

    args = parse_args(sys.argv[1:] if argv is None else argv)
    os.chdir(MONOREPO_ROOT)

    print("[1/7] 定位 act（含 gh-act 退回）")
    act_prefix = resolve_act()
    if act_prefix is None:
        _print_install_hint()
        return 127
    print(f"[run_act] act = {' '.join(act_prefix)}")

    print("[2/7] 確認 Docker daemon")
    if not check_docker():
        print("[run_act] Docker daemon 未啟動，請先開啟 Docker Desktop。", file=sys.stderr)
        return 1

    explicit = selected_workflow(args)
    workflow = run_workflow(args)
    args.event = run_event(args)

    # `--build-image` 刻意排在 List／preflight 之前並自成終點：它是**準備動作**，
    # 與「跑哪一支 workflow」正交，不該被任何 workflow 層的判準擋住（例如映像還沒建
    # 的時候，preflight 對事件的抱怨與你此刻想做的事無關）。
    if getattr(args, "build_image", False):
        return build_runner_image(no_cache=getattr(args, "no_cache", False))

    print("[3/7] List 模式")
    if args.list:
        # 顯式指定時縮到那一支；未指定時維持原本的 `-W <預設>` 呼叫形態，另由本檔自己
        # 解析出全庫盤點補上缺的 16 個 job（不再多開一次 act 子行程）。
        rc = subprocess.run(act_prefix + ["-l", "-W", workflow]).returncode
        if not explicit:
            print_job_inventory(args.event)
        return rc

    if getattr(args, "verify_all", False):
        print("[4/7] 一鍵全驗（--verify-all）：先備妥鏡像，再逐支真跑")
        if ensure_images("") != 0:
            return 1
        fd, env_path = tempfile.mkstemp(prefix="autoclaude_act_empty_")
        try:
            os.close(fd)
            return verify_all(act_prefix, args.event, env_path, explicit)
        finally:
            try:
                os.remove(env_path)
            except OSError:
                pass

    print("[4/7] preflight（本機 act 結構上跑不動的先講清楚）")
    blockers, warnings = preflight(workflow, args.job, args.event)
    for w in warnings:
        print(f"[run_act] ⚠️ {w}")
    if blockers:
        for b in blockers:
            print(f"[run_act] ❌ {b}", file=sys.stderr)
        # 判決行放最後（F-09 紀律：紅不得以綠行收尾）。**必須與明細同一個串流**：
        # 判決行原本走 stdout、明細走 stderr，兩個串流在管線／終端合流時的先後由
        # 緩衝決定 ⇒ 本輪實測到判決行印在明細**之前**，F-09 想買的「最後一行是紅的」
        # 在最常見的讀法下並不成立。同串流才排得出順序。
        print(
            f"[run_act] ❌ preflight 未通過（{len(blockers)} 項）— act 在本機做不到這件事。",
            file=sys.stderr,
        )
        return 1

    print("[5/7] 預先 pull 鏡像")
    rc = ensure_images(args.job)
    if rc != 0:
        return 1

    print("[6/7] 空 .env 覆蓋")
    # act 預設會把 cwd 的 .env 注入容器。本 repo .env 含真實 MINIMAX_API_KEY / DB 憑證：
    #   (1) 安全：不應把個人憑證注入容器；
    #   (2) 忠實度：GitHub runner 無 .env，注入後會讓「預期 env 未設」的測試偽 fail。
    # 解法：傳一個空的 --env-file 覆蓋預設 .env 載入；tempfile + finally 確保清理不留垃圾。
    fd, empty_env_path = tempfile.mkstemp(prefix="autoclaude_act_empty_")
    try:
        os.close(fd)
        print("[7/7] 組裝並執行")
        rc = run_act(act_prefix, args.job, args.dry_run, empty_env_path, workflow, args.event)
    finally:
        try:
            os.remove(empty_env_path)
        except OSError:
            pass

    if rc == 0:
        print("[run_act] ✅ 本地 CI 通過（act 退出碼 0）— 可安全 push。")
    else:
        print(f"[run_act] ❌ 本地 CI 失敗（act 退出碼 {rc}）— 請於本機修復後再 push。")
    return rc


if __name__ == "__main__":
    sys.exit(main())
