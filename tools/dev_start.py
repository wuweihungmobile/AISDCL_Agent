#!/usr/bin/env python3
"""dev_start.py — 跨平台（macOS ⇄ Windows）自動偵測啟動程序（單一邏輯核心）。

為何存在：同一份工作目錄（外接碟/同步資料夾）或雙機各自 clone 在 macOS 與
Windows 之間切換時，過去需手動做四件事：刪重建錯平台形狀的 .venv、重跑
bootstrap、重設 core.hooksPath（絕對路徑跨機必漂移，ONBOARDING §6「搬移後
hooks 靜默全滅」）、git pull。本腳本把「偵測 → 切換 → 同步 → 整備」收斂成
一個指令，兩平台皆可無腦執行。入口 wrapper：tools/dev_start.sh /
tools/dev_start.ps1 —— 皆為薄殼，邏輯集中本檔，無 .sh/.ps1 雙維護漂移面
（有別於 check_script_parity.py 守護的三對真雙實作腳本）。

七步驟：
  [1/7] 環境偵測    — 讀 .dev_env_state.json 的 Developing（上次開發平台）vs Now
  [2/7] GitHub 同步 — fetch + ff-only pull；髒工作樹/分叉/離線 → 明示不硬做
  [3/7] 平台切換    — Developing≠Now 時清除含絕對路徑的 .pytest_cache/.ruff_cache
  [4/7] venv/依賴   — 錯平台形狀 .venv 換手保留至 .venv-cache-<flavor>（本平台
                      快取存在則秒級換回）；缺 .venv 或依賴檔 hash 變 → 自動跑
                      tools/bootstrap.{sh,ps1}（重用既有腳本，不重複其邏輯）
  [5/7] git hooks   — core.hooksPath 缺失/漂移 → 重跑 install_git_hooks 安裝腳本
  [6/7] 平台健檢    — Windows：自動設 core.longpaths=true（MAX_PATH 護欄）
  [7/7] 狀態寫回    — Developing=Now + per-platform 依賴 hash + 摘要

設計取捨（fail loud，絕不靜默硬做）：
  - 髒工作樹不自動 stash、分叉不自動 rebase、領先不自動 push —— 只明示指令。
  - 離線（fetch 失敗/逾時）→ 警告後繼續，本機整備照常完成。
  - 狀態檔 .dev_env_state.json 為 gitignored：共用工作目錄時隨磁碟跨機
    （Developing≠Now 可偵測），雙 clone 時各機獨立（切換恆不觸發、由同步
    ＋依賴 hash 承擔跨機一致性）—— 兩種拓撲皆正確。

用法：
  source tools/dev_start.sh              # macOS/Linux（結尾自動啟用 .venv）
  . tools\\dev_start.ps1                  # Windows PowerShell（dot-source 同上）
  python tools/dev_start.py [--no-sync] [--force-bootstrap]
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform as _platform
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / ".dev_env_state.json"
LOCK_FILE = ROOT / ".dev_start.lock"
HOOKS_DIR = ROOT / "tools" / "git-hooks"
DEPS_FILES = (
    ROOT / "AutoClaude" / "pyproject.toml",
    ROOT / "AISDLC_SDD" / "AISDLC_SDD_v0.01" / "requirements-ci.txt",
)
# 跨平台切換時要清除的快取（內嵌絕對路徑，換平台後無效且會誤導）
_CACHE_DIRS = (".pytest_cache", ".ruff_cache")
_CACHE_BASES = (ROOT, ROOT / "AutoClaude", ROOT / "AISDLC_SDD")

_TOTAL = 7
WARNINGS: list[str] = []
SUMMARY: dict[str, str] = {}

# R3 四方複審 QA 發現：tools/tests/ 先前從未在真實 Windows 上執行過，本輪首次
# 真實執行後，_warn()/_hr() 的 print() 在 Windows 非 UTF-8 終端（如 zh-TW 預設
# cp1252 codepage、或任何非互動/被導向的 stdout）下對 ⚠️/✅ 等符號直接
# UnicodeEncodeError 崩潰——先前只有 main()（CLI 入口）內重設編碼，測試套件與
# 任何未經 main() 直接呼叫模組內部函式的呼叫端（未來的 import 使用者）不會套用
# 到這道保護。改在模組載入當下就重設，涵蓋所有呼叫路徑，且與 main() 原本的保護
# 邏輯等價。R4 複審 S7 發現：此保護抽成 tools/_stdio_utf8.py 共用 helper（避免
# check_ntfs_paths.py / check_script_parity.py 各自複製貼上第三份同款程式碼）。
import _stdio_utf8  # noqa: E402,F401
# step_hooks() 與 tools/check_hooks_liveness.py 共用同一份判定邏輯（S22，見該函式註解）。
import check_hooks_liveness  # noqa: E402

# platform_utils 位於 tools/lib/ 子目錄（非本檔同層），需顯式插入 sys.path 才能
# import——手法對齊本輪其他核心檔案（AutoClaude/tools/scaffold_sprint_section.py 等）
# 既有慣例（R17 DEF-101-231 觀察點 1+2：收斂 is_windows/os_label/venv_python_path
# 平台判斷邏輯的第二次重複）。
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import platform_utils  # noqa: E402


def _hr(n: int, title: str) -> None:
    print(f"\n[{n}/{_TOTAL}] {title}")


def _warn(msg: str) -> None:
    WARNINGS.append(msg)
    print(f"    ⚠️  {msg}")


def _git(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(args=args, returncode=127,
                                           stdout="", stderr="git not found")
    except subprocess.TimeoutExpired:
        # 本地 git 指令逾時極罕見，但裸 traceback 不是好介面 → 統一化為 rc=124
        return subprocess.CompletedProcess(
            args=args, returncode=124,
            stdout="", stderr=f"git {' '.join(args)} 逾時（>{timeout}s）")


def _stream(cmd: list[str], on_start: Callable[[int], None] | None = None,
            new_process_group: bool = False) -> int:
    """即時輸出地執行外部指令（bootstrap / pull / hooks 安裝）。

    flush：stdout 為 pipe（CI log）時 Python 端有緩衝，不 flush 會讓子行程
    輸出插隊到步驟標頭之前，破壞取證順序。
    刻意不設 timeout：pull/bootstrap 屬互動長工（合法耗時數分鐘），任意上限
    會誤殺；掛住時使用者可 Ctrl-C（見 `_forward_signal_to_bootstrap_group`
    對 `new_process_group=True` 呼叫的訊號轉發配套），且發生於 state 寫回之前
    （重入安全）。
    改用 Popen（而非 subprocess.run）：on_start 讓呼叫端在子行程一建立就能拿到
    其「真實」PID（Architect + SA 複審 P1：venv bootstrap 互斥鎖過去只記錄
    orchestrator 自己的 PID，orchestrator 被 SIGKILL 後子行程變孤兒仍會繼續寫
    .venv，鎖對孤兒毫無防護——鎖真正該追蹤的存活對象是實際執行 bootstrap 的
    子行程，而不是呼叫它的 dev_start.py 本體）。

    `new_process_group`（MUST FIX A，Architect 第三輪複審用真實驗證證明「事後
    ppid 回溯」在因果上必然太晚後的根本重做）：僅 POSIX 生效（`os.name != "nt"`
    時傳遞 `start_new_session=True`，令子行程呼叫 `setsid()` 成為新 session 的
    group leader，其自身 PID 同時即為 process group id）。之後不論該子行程
    fork 出多少層、多少個孫行程，只要仍有任一成員存活，`os.killpg(pgid, 0)`
    就會成功——不受「父行程死亡時子行程 ppid 被核心過繼給 subreaper」影響
    （過繼只改變 ppid，不改變 process group membership）。Windows 不支援
    `start_new_session`（Python `subprocess` 文件明載此參數為 POSIX-only，
    Windows 上傳入非假值會拋 `ValueError`），故明確以 `os.name` 守門，不可
    無條件傳遞。呼叫端須自行處理 Ctrl-C 轉發配套（見模組層級
    `_ACTIVE_BOOTSTRAP_PGID` / `_forward_signal_to_bootstrap_group`）——
    `start_new_session=True` 會讓子行程脫離終端機 foreground process group，
    否則 Ctrl-C（SIGINT 只送到 foreground process group）不會再傳到它。
    """
    print(f"    $ {' '.join(cmd)}", flush=True)
    popen_kwargs: dict = {"cwd": str(ROOT)}
    if new_process_group and not platform_utils.is_windows():
        popen_kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen(cmd, **popen_kwargs)
    except FileNotFoundError:
        print(f"    ❌ 找不到指令：{cmd[0]}", file=sys.stderr)
        return 127
    except OSError as e:
        # P2（SA 複審發現）：FileNotFoundError 只涵蓋「指令不存在」。當
        # new_process_group=True 且執行環境限制 setsid()（如受限 seccomp/
        # 沙盒設定拒絕該系統呼叫）時，Popen(..., start_new_session=True) 會在
        # 子行程端呼叫失敗、經內部 pipe 回報，父行程端拋出 PermissionError
        # （OSError 子類別，非 FileNotFoundError）——若不接住會直接向上傳播，
        # 讓 _run_bootstrap()/step_venv()/main() 裸崩潰。FileNotFoundError 本身
        # 也是 OSError 子類別，但因已在上一個 except 分支處理，Python 依例外
        # 子句宣告順序比對、先到者優先匹配，不會落到這裡。
        print(f"    ❌ 執行指令失敗（{cmd[0]}）：{e}", file=sys.stderr)
        return 126
    if on_start is not None:
        on_start(proc.pid)
    return proc.wait()


_ACTIVE_BOOTSTRAP_PGID: int | None = None


def _set_active_bootstrap_pgid(pgid: int | None) -> None:
    """記錄目前是否有正在執行的 bootstrap process group（MUST FIX A 配套：
    Ctrl-C 訊號轉發）。呼叫端須在 bootstrap 子行程啟動當下設定，並在
    `_run_bootstrap()` 返回（不論成功/失敗/例外）後立刻清除，`try/finally`
    包住，避免遺留一個「其實已死」的 pgid 讓下次無關的 Ctrl-C 誤轉發。"""
    global _ACTIVE_BOOTSTRAP_PGID
    _ACTIVE_BOOTSTRAP_PGID = pgid


def _forward_signal_to_bootstrap_group(signum: int, frame) -> None:
    """SIGINT/SIGTERM handler（MUST FIX A 必要配套，POSIX only）。

    背景：`_run_bootstrap()` 對 bootstrap 直接子行程呼叫
    `Popen(..., start_new_session=True)`，使其（連同所有孫行程）脫離
    dev_start.py 所在終端機的 foreground process group——SIGINT 只送到
    foreground process group，使用者按 Ctrl-C 將不再自然傳到 bootstrap 樹，
    可能讓它在背景孤兒繼續跑而使用者誤以為已中止。

    本 handler 在 dev_start.py 自己收到訊號時：若目前有進行中的 bootstrap
    process group（`_ACTIVE_BOOTSTRAP_PGID` 非 None），主動 `os.killpg()`
    轉發 SIGTERM 給整個 group，給一段緩衝時間輪詢其是否已終止，逾時仍未終止
    才升級 SIGKILL——之後直接 return（不拋例外）：`_stream()` 內
    `proc.wait()` 底層的 `os.waitpid()` 依 PEP 475 在被訊號中斷、handler
    未拋例外時會自動重試，此時直接子行程已因剛才的轉發而終止（或即將終止），
    `wait()` 很快就會以「被訊號終止」的負值 rc 正常返回——不需要額外拋例外
    打斷呼叫堆疊，既有的 rc!=0 失敗處理（哨兵/警告/摘要）可原樣沿用。

    沒有進行中的 bootstrap 時，回退為 Python 的預設行為：SIGINT 呼叫
    `signal.default_int_handler()`（即拋出 `KeyboardInterrupt`，與未安裝本
    handler 時完全一致，不影響 step_sync/step_hooks 等其他步驟原有的 Ctrl-C
    行為——那些步驟的子行程未使用 `start_new_session`，仍與 dev_start.py
    同處一個 foreground process group，終端機 Ctrl-C 本就會直接送達，不需要
    本 handler 介入）；SIGTERM 則暫時恢復預設處置（終止行程）後對自己重新
    送出同一訊號，比照「未安裝本 handler 時的預設行為」，不擅自改變語意。
    """
    if _ACTIVE_BOOTSTRAP_PGID is None:
        if signum == signal.SIGINT:
            signal.default_int_handler(signum, frame)
            return
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGTERM)
        return

    pgid = _ACTIVE_BOOTSTRAP_PGID
    try:
        signame = signal.Signals(signum).name
    except ValueError:
        signame = str(signum)
    print(f"\n    ⚠️  收到中止訊號（{signame}）— 轉發至 bootstrap process group"
          f"（pgid={pgid}），避免其在背景孤兒繼續執行 …", file=sys.stderr)
    try:
        os.killpg(pgid, signal.SIGTERM)
    except OSError:
        pass
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except OSError:
            return  # 已全數終止（ProcessLookupError）或無法判斷，不再升級
        time.sleep(0.2)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except OSError:
        pass


def _now_label() -> str:
    return platform_utils.os_label()


def _flavor(label: str) -> str:
    """venv 目錄形狀：windows=Scripts\\python.exe；mac/linux 同為 posix=bin/python。"""
    return "windows" if label == "windows" else "posix"


def _venv_python_at(base: Path, flavor: str) -> Path:
    return platform_utils.venv_python_path(base, is_windows=(flavor == "windows"))


def _venv_python(flavor: str) -> Path:
    return _venv_python_at(ROOT / ".venv", flavor)


def _safe_exists(p: Path) -> bool:
    """`.exists()` 但吞 OSError（P1-3：快取目錄 chmod 000 時純讀取探測不可裸崩）。"""
    try:
        return p.exists()
    except OSError as e:
        _warn(f"無法讀取 {p}（{e}）— 視為不存在")
        return False


def _safe_is_dir(p: Path) -> bool:
    """`.is_dir()` 但吞 OSError（同上，P1-3）。"""
    try:
        return p.is_dir()
    except OSError as e:
        _warn(f"無法讀取 {p}（{e}）— 視為不是目錄")
        return False


def _safe_is_file(p: Path) -> bool:
    """`.is_file()` 但吞 OSError（同上，P1-3）。"""
    try:
        return p.is_file()
    except OSError as e:
        _warn(f"無法讀取 {p}（{e}）— 視為不存在")
        return False


def _safe_is_symlink(p: Path) -> bool:
    """`.is_symlink()` 但吞 OSError（同上，P1-3）。"""
    try:
        return p.is_symlink()
    except OSError as e:
        _warn(f"無法讀取 {p}（{e}）— 視為不是符號連結")
        return False


_VENV_ORIGIN_MARKER = ".dev_venv_origin"


def _write_origin_marker(venv_dir: Path, label: str) -> None:
    """記錄「這份 venv 內容實際是哪個平台建的」（P1-1 根本解①）。

    寫在 venv 目錄內部（而非快取目錄層級），這樣不管內容目前叫 .venv 還是
    .venv-cache-<flavor>，換手 rename 時標記都隨內容一起搬動，不需要在每個
    rename 點手動同步。flavor 只分兩桶（windows/posix）分不出 mac vs
    linux，本標記記錄 _now_label() 的三分類，足以識別。
    """
    try:
        (venv_dir / _VENV_ORIGIN_MARKER).write_text(label, encoding="utf-8")
    except OSError as e:
        _warn(f"寫入 {venv_dir.name}/{_VENV_ORIGIN_MARKER} 失敗（{e}）— 不影響本次整備，"
              f"但下次跨機判斷可能失準")


def _read_origin_marker(venv_dir: Path) -> str | None:
    p = venv_dir / _VENV_ORIGIN_MARKER
    try:
        if p.is_file():
            text = p.read_text(encoding="utf-8", errors="replace").strip()
            return text or None
    except OSError as e:
        _warn(f"無法讀取 {p}（{e}）— 將僅依賴直譯器健檢判斷可信度")
    return None


_BOOTSTRAP_INCOMPLETE_MARKER = ".dev_venv_bootstrap_incomplete"


def _mark_bootstrap_incomplete(venv_dir: Path) -> None:
    """標記「這份 .venv 的 bootstrap 尚未完整成功」（P1，四方複審共同發現）。

    背景：tools/bootstrap.sh 用 `set -euo pipefail`，`python -m venv .venv` 與
    `pip install` 是獨立步驟——venv 建立成功但 pip install 失敗（常見失敗模式：
    網路中斷）時，整體 bootstrap 回傳非 0，但 .venv 內已有一顆可執行的
    python。下次執行若落入「既有 .venv、無狀態紀錄」分支，過去只做
    `_venv_healthy()`（僅驗證 python --version 能跑，完全不驗證套件是否真的
    裝好）就會把這份「其實半殘」的 venv 誤判為完整、印出「✅ 成功」，並用
    `_write_origin_marker()` 標記為本平台正常建置，連帶污染未來的跨機信任判斷。
    """
    try:
        (venv_dir / _BOOTSTRAP_INCOMPLETE_MARKER).write_text("incomplete", encoding="utf-8")
    except OSError as e:
        _warn(f"寫入 bootstrap 未完成哨兵失敗（{e}）— 下次可能誤判此 .venv 為完整")


def _clear_bootstrap_incomplete(venv_dir: Path) -> None:
    try:
        (venv_dir / _BOOTSTRAP_INCOMPLETE_MARKER).unlink()
    except OSError:
        pass  # 不存在或刪除失敗皆不影響：本次已成功，下次判斷改看 _venv_healthy()


def _bootstrap_incomplete_marker_present(venv_dir: Path) -> bool:
    return _safe_is_file(venv_dir / _BOOTSTRAP_INCOMPLETE_MARKER)


def _root_bootstrap_incomplete_marker() -> Path:
    """ROOT 層級（與 LOCK_FILE / STATE_FILE 同一層級）哨兵路徑（MUST FIX #4，
    Architect 複審發現）。刻意用函式而非模組層級凍結常數：`ROOT` 本身可能被
    測試 monkeypatch（`mock.patch.object(dev_start, "ROOT", ...)`），用函式讓
    每次呼叫都重新讀取當下的 ROOT，測試沙盒化才能正確生效、不誤寫真實 repo。
    """
    return ROOT / _BOOTSTRAP_INCOMPLETE_MARKER


def _mark_root_bootstrap_incomplete() -> None:
    """在 ROOT 層級無條件標記「本次 bootstrap 尚未完整成功」（MUST FIX #4，
    Architect 用真實 SIGINT 實驗發現）。

    背景：`_mark_bootstrap_incomplete(venv_dir)` 只在 `.venv` 目錄「已存在」時
    才會於呼叫 bootstrap 前先寫入，對「首次建置、.venv 完全不存在」這個情境
    完全沒有防護——首次建置期間使用者按下最普通的 Ctrl-C，SIGINT 會送到整個
    前景 process group，同時打中 dev_start.py 本體與 bootstrap 子行程，
    dev_start.py 幾乎與 bootstrap 同時死亡：`_run_bootstrap()` 內
    `rc = _stream(...)` 之後的「rc!=0 補寫哨兵」程式碼永遠執行不到。使用者
    原地重跑：`.venv/bin/python` 已存在（bootstrap 死前建好的）、無任何哨兵、
    `state={}` → 落入 `prev is None` 分支 → 健檢通過（直譯器能跑，只是套件
    沒裝完）→ 誤判「沿用既有 .venv」、回報虛假成功。

    本函式必須在 `_run_bootstrap()` 呼叫 `_stream()` 之前、不受 `.venv` 是否
    已存在限制、無條件呼叫，才能在行程被訊號中止的情況下仍留下紀錄——不依賴
    任何「_stream() 之後」才執行到的程式碼。
    """
    try:
        _root_bootstrap_incomplete_marker().write_text("incomplete", encoding="utf-8")
    except OSError as e:
        _warn(f"寫入 ROOT 層級 bootstrap 未完成哨兵失敗（{e}）— 下次可能誤判本次整備已完整")


def _clear_root_bootstrap_incomplete() -> None:
    try:
        _root_bootstrap_incomplete_marker().unlink()
    except OSError:
        pass  # 不存在或刪除失敗皆不影響：本次已成功，下次判斷改看 _venv_healthy()


def _root_bootstrap_incomplete_marker_present() -> bool:
    return _safe_is_file(_root_bootstrap_incomplete_marker())


def _venv_healthy(py: Path) -> tuple[bool, str]:
    """對候選直譯器做可執行性健檢（P1-1 根本解②：即使標記機制失準仍能兜底）。

    catch 例外/非零 rc——包含二進位格式不相容（如 macOS Mach-O 拿到 Linux
    上跑會是 OSError: Exec format error）與檔案根本不可執行等情況。
    """
    try:
        r = subprocess.run([str(py), "--version"], capture_output=True, timeout=15)
    except OSError as e:
        return False, str(e)
    except subprocess.TimeoutExpired:
        return False, "執行逾時（>15s）"
    if r.returncode != 0:
        return False, f"rc={r.returncode}"
    return True, "ok"


def _python_version_target() -> str | None:
    """讀 ROOT/.python-version 的目標版本，截為 major.minor（DEF-101-207）。

    截斷語意對齊 tools/bootstrap.sh 的 `cut -d. -f1,2`（三段版號如 3.11.9 截為
    3.11——「python3.11.9」命名的直譯器不存在、uv --python 也以 major.minor
    解析）。缺檔/不可讀回 None 靜默：pin 不存在是合法狀態，不是缺陷。
    """
    try:
        raw = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    return ".".join(raw.split(".")[:2])


def _venv_python_minor(py: Path) -> str | None:
    """實測 venv 直譯器的 major.minor 版本；任何失敗回 None（DEF-101-207）。

    防護樣式參考 _venv_healthy()：catch OSError（二進位不相容/不可執行）與
    逾時，非零 rc 同樣視為查不到——本哨兵是 advisory，查不到就靜默。
    """
    try:
        r = subprocess.run(
            [str(py), "-c", "import sys;print('%d.%d'%sys.version_info[:2])"],
            timeout=15, capture_output=True, encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    out = (r.stdout or "").strip()
    return out or None


def _cache_restore_trust(cache_dir: Path, flavor: str, now: str) -> tuple[bool, str]:
    """單一權威判斷：cache_dir 內容是否可信任還原為本平台 .venv（P1-1）。

    Architect 審查指出平台判斷散落在多個呼叫點，是三機輪替快取誤還原 bug
    的結構性根因——本函式把「這次換手是否可信任」收斂成單一判斷點，取代
    原本單靠 flavor 兩桶（windows/posix，分不出 mac vs linux）決定是否還原
    的邏輯。兩道防線都要過：①origin marker 比對 now（根本解，但舊快取/
    未來漏洞可能沒有或繞過標記）；②不論①結果一律對候選直譯器健檢（兜底，
    對「binary 格式不相容」這類 marker 機制以外的失效模式仍能攔下）。
    """
    py = _venv_python_at(cache_dir, flavor)
    if not _safe_exists(py):
        return False, "候選目錄內無可用直譯器"
    origin = _read_origin_marker(cache_dir)
    marker_ok = origin is None or origin == now
    healthy, detail = _venv_healthy(py)
    if not healthy:
        extra = f"；標記建於 {origin}，與目前平台 {now} 不符" if not marker_ok else ""
        return False, f"直譯器健檢失敗（{detail}）{extra}"
    if not marker_ok:
        return False, f"標記建於 {origin}，與目前平台 {now} 不符"
    return True, "ok"


def _load_state() -> dict:
    if not _safe_is_file(STATE_FILE):
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        if not isinstance(data.get("deps_hash"), dict):
            data.pop("deps_hash", None)  # schema 層損毀只棄該欄，不 crash
        return data
    except (OSError, ValueError):
        _warn(f"{STATE_FILE.name} 損毀 — 視為首次執行")
        return {}


def _toml_deps_snapshot(text: str, source: Path) -> str:
    """解析 pyproject.toml，只萃取與依賴安裝直接相關的結構化內容並序列化為
    穩定字串，取代先前手寫正則逐行掃描（P1：QA 用實際函式呼叫重現三個正則
    邊角案例——①表頭後接行內註解（如 `[project]  # comment`）時，正則要求
    整行精確符合 `[section]` 結尾只能是空白，不匹配時 section 沿用前一個值，
    導致 [project] 底下真正的依賴宣告被完全排除在 hash 之外且零警告；
    ②`[[table.array]]` 巢狀陣列表同樣不匹配表頭正則，內容被誤判歸入前一個
    區段；③多行三引號字串（如 description 欄位用三個雙引號包住的多行文字）
    的續行內容會被當成一般內容誤納入 hash，純文案異動誤觸發重裝。tomllib 是標準庫的正確
    TOML parser，天生不受這三者影響，故直接取代手寫正則掃描。

    只保留 project.dependencies／project.optional-dependencies／build-system
    三塊與依賴安裝直接相關的內容（其餘如 name/version/description/
    requires-python 等中繼資料、[tool.*] 等一律不納入，改用白名單精確萃取，
    不再依賴黑名單排除法——不會漏未來新增的中繼資料 key）。
    解析失敗（語法錯誤）時退回「整檔視為相關」並警告：寧可誤觸發重裝，也
    不可像正則方案一樣悄悄漏掉真正的依賴變動（fail loud 優先於 fail silent）。
    """
    # MUST FIX #1（SD 複審發現的 P1 迴歸）：先前只把 tomllib.loads() 包在
    # try/except 裡，但後面的 project.get(...) 與 json.dumps(...) 完全沒有例外
    # 防護。以下兩種語法合法（tomllib 不會拋 TOMLDecodeError）的內容會讓整支
    # 工具裸崩潰：①依賴欄位誤填 TOML 原生日期型別（如 `dependencies =
    # [2024-01-01]`），tomllib 解析成 datetime.date，json.dumps 無法序列化
    # （TypeError）；②[project] 誤寫成純量賦值（如 `project = "x"`），
    # data.get("project", {}) 拿到字串而非 dict，project.get(...) 裸拋
    # AttributeError。故把 tomllib.loads() 到 json.dumps() 全部收攏進同一個
    # try 區塊，任何解析/結構/序列化錯誤都同樣退回 <invalid-toml> 並警告
    # （fail loud 優先於 fail silent，與既有 TOMLDecodeError 分支一致）。
    try:
        data = tomllib.loads(text)
        project = data.get("project", {})
        extracted = {
            "project.dependencies": project.get("dependencies"),
            "project.optional-dependencies": project.get("optional-dependencies"),
            "build-system": data.get("build-system"),
        }
        return json.dumps(extracted, sort_keys=True, ensure_ascii=False)
    except tomllib.TOMLDecodeError as e:
        _warn(f"{source.name} 非合法 TOML（{e}）— 依賴 hash 改用整檔內容，"
              f"可能誤觸發重裝，請修正語法")
        return f"<invalid-toml>{text}"
    except (TypeError, AttributeError) as e:
        _warn(f"{source.name} TOML 內容形狀不符預期（{e}）— 依賴 hash 改用整檔內容，"
              f"可能誤觸發重裝，請修正語法")
        return f"<invalid-toml>{text}"


def _plain_relevant_lines(text: str) -> list[str]:
    """純 requirements.txt 類檔案（非 TOML）：整檔皆視為依賴宣告，只濾掉
    註解/空白行。"""
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def _deps_hash() -> str:
    h = hashlib.sha256()
    for f in DEPS_FILES:
        h.update(f.name.encode("utf-8"))
        if not _safe_is_file(f):
            h.update(b"<missing>")
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            _warn(f"無法讀取 {f}（{e}）— 依賴 hash 略過此檔（可能誤判為未變動）")
            h.update(b"<unreadable>")
            continue
        if f.suffix == ".toml":
            h.update(_toml_deps_snapshot(text, f).encode("utf-8"))
        else:
            for line in _plain_relevant_lines(text):
                h.update(line.encode("utf-8"))
                h.update(b"\n")
    return h.hexdigest()


def step_sync(no_sync: bool, is_repo: bool) -> None:
    _hr(2, "GitHub 同步")
    if no_sync:
        print("    --no-sync 指定 — 跳過")
        SUMMARY["sync"] = "跳過（--no-sync）"
        return
    if not is_repo:
        _warn("非 git repo — 跳過同步")
        SUMMARY["sync"] = "跳過（非 git repo）"
        return
    if _git("remote", "get-url", "origin").returncode != 0:
        _warn("未設定 origin remote — 跳過同步")
        SUMMARY["sync"] = "跳過（無 origin）"
        return
    print("    git fetch origin --prune …")
    fetch = _git("fetch", "origin", "--prune", timeout=120)  # 逾時由 _git 化為 rc=124
    if fetch.returncode != 0:
        # 取第一行非空錯誤（git 多行錯誤的首行才是 fatal: 主因；取末行會得到斷句）
        lines = [ln.strip() for ln in (fetch.stderr or "").splitlines() if ln.strip()]
        detail = lines[0] if lines else f"rc={fetch.returncode}"
        _warn(f"git fetch 失敗（{detail}）— 視為離線，跳過同步")
        SUMMARY["sync"] = "離線（fetch 失敗）"
        return

    branch = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if not branch or branch == "HEAD":
        _warn("detached HEAD — 跳過 pull")
        SUMMARY["sync"] = "跳過（detached HEAD）"
        return
    if _git("rev-parse", "--verify", "--quiet", f"origin/{branch}").returncode != 0:
        _warn(f"origin/{branch} 不存在（本地新分支？）— 跳過 pull")
        SUMMARY["sync"] = f"跳過（origin/{branch} 不存在）"
        return

    def _count(spec: str) -> int:
        r = _git("rev-list", "--count", spec)
        return int(r.stdout.strip()) if r.returncode == 0 else -1

    behind = _count(f"HEAD..origin/{branch}")
    ahead = _count(f"origin/{branch}..HEAD")
    if behind < 0 or ahead < 0:
        # 計數失敗不可呈現為「已是最新」（假綠）；也不冒險 pull
        _warn("rev-list 計數失敗 — 無法判定同步狀態，跳過 pull（可稍後手動 git pull --ff-only）")
        SUMMARY["sync"] = "跳過（計數失敗）"
        return
    # 只看已追蹤檔的修改：未追蹤檔不擋同步（ff pull 對未追蹤檔安全，git 會自我保護）
    status_r = _git("status", "--porcelain", "--untracked-files=no")
    if status_r.returncode != 0:
        # 空 stdout 不可等同「乾淨」——returncode 非零時無法判定，不冒險 pull
        _warn("git status 失敗 — 無法判定工作樹是否乾淨，跳過 pull（可稍後手動 git pull --ff-only）")
        SUMMARY["sync"] = "跳過（git status 失敗）"
        return
    dirty = bool(status_r.stdout.strip())

    if behind == 0:
        msg = f"已是最新（origin/{branch}）"
        print(f"    ✅ {msg}")
        SUMMARY["sync"] = msg
        if ahead > 0:
            _warn(f"本地領先 origin/{branch} {ahead} commit — 開發完請 git push（不自動 push）")
        return
    if dirty:
        _warn(f"工作樹有未提交變更且落後 origin/{branch} {behind} commit — 不自動 pull/stash；"
              f"請自行 commit 或 stash 後 `git pull --ff-only origin {branch}`")
        SUMMARY["sync"] = f"未同步（髒工作樹，落後 {behind}）"
        return
    if ahead > 0:
        _warn(f"與 origin/{branch} 分叉（本地 +{ahead} / 遠端 +{behind}）— 不自動 rebase；"
              f"請自行處理（例：git pull --rebase origin {branch}）")
        SUMMARY["sync"] = f"未同步（分叉 +{ahead}/+{behind}）"
        return
    rc = _stream(["git", "-C", str(ROOT), "pull", "--ff-only", "origin", branch])
    if rc == 0:
        print(f"    ✅ 已 fast-forward {behind} commit")
        SUMMARY["sync"] = f"已更新（fast-forward {behind} commit）"
    else:
        _warn("git pull --ff-only 失敗 — 請手動處理")
        SUMMARY["sync"] = "未同步（pull 失敗）"


def step_switch(env_changed: bool) -> None:
    _hr(3, "平台切換（跨平台無效快取清理）")
    if not env_changed:
        print("    無跨平台切換 — 跳過")
        return
    removed: list[str] = []
    leftovers: list[str] = []
    for base in _CACHE_BASES:
        for name in _CACHE_DIRS:
            p = base / name
            if _safe_is_symlink(p):
                # rmtree(ignore_errors) 對 symlink 靜默拒刪 → 明確 unlink 只斷連結不動目標
                try:
                    p.unlink()
                except OSError:
                    pass
            elif _safe_is_dir(p):
                shutil.rmtree(p, ignore_errors=True)
            else:
                continue
            rel = str(p.relative_to(ROOT))
            # 事後驗證實刪，不做未經查證的「已清除」宣稱
            if _safe_exists(p) or _safe_is_symlink(p):
                leftovers.append(rel)
            else:
                removed.append(rel)
    if removed:
        print(f"    已清除：{', '.join(removed)}")
    if leftovers:
        _warn(f"快取清理未完全（請手動刪除）：{', '.join(leftovers)}")
    if not removed and not leftovers:
        print("    無快取需清除")


def _ensure_venv_shape(now: str) -> str:
    """確保 .venv 是本平台形狀。回傳 ok / restored / missing。

    錯平台形狀的 .venv 不刪除——換手保留至 .venv-cache-<flavor>（gitignored），
    共用工作目錄來回切換時各平台 venv 皆秒級復用，只有首次才付 bootstrap 成本。
    """
    flavor = _flavor(now)
    other = "windows" if flavor == "posix" else "posix"
    venv = ROOT / ".venv"

    # 斷裂 symlink（目標已消失，如外接碟拔除/同步中斷）：is_dir()/exists() 對此
    # 恆回 False，會整段跳過下面的清理邏輯、直接落到 "missing"，但底層目錄項目
    # 仍留存（lstat 可見），導致下游 bootstrap 的 `python3 -m venv .venv`
    # 撞 Errno 17: File exists（Architect + SD + QA 審查 P1-2）→ 在此提前攔截清除。
    if _safe_is_symlink(venv) and not _safe_exists(venv):
        try:
            venv.unlink()
            _warn("偵測到失效的 .venv 符號連結（可能是外接碟已拔除或同步中斷）— 已清除，將重新建置")
        except OSError as e:
            _warn(f".venv 斷裂符號連結清除失敗（{e}）— 請手動刪除 .venv 後重跑")

    if _safe_is_dir(venv) and not _safe_exists(_venv_python(flavor)):
        if _safe_exists(_venv_python_at(venv, other)):
            # 確為另一平台形狀才換手保留；不驗形狀就 park 會讓「同平台壞損 venv」
            # 先摧毀真正的對方快取、再錯標入快取且永不自癒（Architect 審查 P1）
            cache_other = ROOT / f".venv-cache-{other}"
            cache_other_ready = True
            try:
                if _safe_exists(cache_other):
                    has_content = False
                    try:
                        has_content = any(cache_other.iterdir())
                    except OSError:
                        pass  # 列不出內容不影響後續判斷，仍嘗試處理
                    if has_content:
                        # QA 審查指出：先前訊息宣稱「請先手動備份」卻在同一次呼叫立即
                        # rmtree，使用者讀到警告時已來不及——改為改名為時間戳記備份，
                        # 讓「不可逆」的宣稱名副其實（非阻塞覆蓋，事後仍可自行檢視/刪除）
                        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                        backup = ROOT / f".venv-cache-{other}.bak-{ts}"
                        cache_other.rename(backup)
                        _warn(f"{cache_other.name}/ 已有內容 — 換手保留前已改名為 {backup.name}/"
                              f"（未覆蓋；確認不需要可自行刪除該備份目錄）")
                    else:
                        shutil.rmtree(cache_other)
            except OSError as e:
                # 卡住的資源是 cache_other，不是 .venv——訊息須指名真正病灶（Architect 審查 P2）
                _warn(f"清除既有 {cache_other.name}/ 失敗（{e}）— 請先手動處理該目錄後重跑")
                cache_other_ready = False
            if cache_other_ready:
                try:
                    venv.rename(cache_other)
                    print(f"    偵測到另一平台形狀的 .venv → 換手保留為 {cache_other.name}/")
                except OSError as e:
                    _warn(f".venv 換手失敗（改名為 {cache_other.name}/ 時發生 {e}）— 請手動刪除 .venv 後重跑")
        else:
            # 兩平台直譯器皆缺＝壞損 venv（如 symlink 斷裂）→ 移除重建，不動任何快取
            try:
                if _safe_is_symlink(venv):
                    venv.unlink()
                else:
                    shutil.rmtree(venv)
                print("    偵測到壞損 .venv（兩平台直譯器皆缺）→ 已移除，將重建")
            except OSError as e:
                _warn(f"壞損 .venv 移除失敗（{e}）— 請手動刪除 .venv 後重跑")

    if not _safe_exists(venv):
        cache_mine = ROOT / f".venv-cache-{flavor}"
        if _safe_is_symlink(cache_mine):
            # symlink 快取換回會讓 .venv 指向外部目錄、後續 bootstrap 污染目標 → 拒用
            _warn(f"{cache_mine.name} 是 symlink — 不換回（避免寫入外部目標），改重建 .venv")
        elif _safe_exists(cache_mine):
            trustworthy, reason = _cache_restore_trust(cache_mine, flavor, now)
            if trustworthy:
                try:
                    cache_mine.rename(venv)
                    print(f"    自 {cache_mine.name}/ 秒級換回本平台 .venv")
                    return "restored"
                except OSError as e:
                    _warn(f"venv 快取換回失敗（{e}）")
            else:
                # 不得靜默 return "missing" 放著壞快取佔磁碟不聲不響（Architect 審查 P1-1 / P2）
                _warn(f"偵測到 {cache_mine.name}/ 內容無效（{reason}）— 已略過（不會自動清除，"
                      f"避免誤刪使用者手動放的東西；可手動檢視/清除該目錄），將視為 missing 重新整備")
    return "ok" if _safe_exists(_venv_python(flavor)) else "missing"


def _run_bootstrap(now: str, reason: str, on_start: Callable[[int], None] | None = None) -> bool:
    print(f"    需要 bootstrap：{reason}")
    venv_dir = ROOT / ".venv"
    if _flavor(now) == "windows":
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File",
               str(ROOT / "tools" / "bootstrap.ps1")]
    else:
        cmd = ["bash", str(ROOT / "tools" / "bootstrap.sh")]
    # P1（四方複審共同發現）：既有 .venv 上重跑 bootstrap（如依賴變動／
    # --force-bootstrap／健檢失敗）前先寫哨兵——涵蓋「dev_start.py 本體被強制
    # 中止」這類比乾淨失敗（rc!=0）更難事後補救的情況。純首次建置（.venv 尚
    # 不存在）則留待失敗後再補寫：提前在此建立 .venv 只為了放哨兵，會讓
    # bootstrap.sh 自身「既有 .venv 但缺 bin/python」防呆條件成立而整段失敗
    # （bootstrap.sh 對「目錄已存在」與「目錄內已有完整直譯器」不做區分）。
    if _safe_is_dir(venv_dir):
        _mark_bootstrap_incomplete(venv_dir)
    # MUST FIX #4（Architect 用真實 SIGINT 實驗發現）：上面這份哨兵只在 .venv
    # 已存在時才會落地，對「首次建置、.venv 完全不存在」時使用者按下最普通的
    # Ctrl-C（訊號同時打中 dev_start.py 本體與 bootstrap 子行程，dev_start.py
    # 死亡後 rc!=0 補寫哨兵永遠執行不到）完全沒有防護。ROOT 層級哨兵不受
    # .venv 是否存在限制，無條件於呼叫 _stream() 之前落地。
    _mark_root_bootstrap_incomplete()
    # new_process_group=True（MUST FIX A）：僅 POSIX 生效（_stream 內以 os.name
    # 守門），讓 bootstrap 子行程獨立成新 process group，供 step_venv() 改用
    # os.killpg 判斷整個行程樹（含孫行程）是否仍存活；Windows 無此參數，維持
    # 既有 _DescendantWatcher／ppid 回溯設計不變（見 step_venv 內對應分支與
    # docstring 說明的技術依據）。
    rc = _stream(cmd, on_start=on_start, new_process_group=True)
    if rc != 0:
        print(f"    ❌ bootstrap 失敗（rc={rc}）— 請依上方輸出排除後重跑", file=sys.stderr)
        if _safe_is_dir(venv_dir):
            # venv 建立成功但後段（如 pip install）失敗：留下哨兵，避免下次
            # 沿用時被誤判為「完整可用」而靜默漂白成功。
            _mark_bootstrap_incomplete(venv_dir)
        return False
    if _safe_is_dir(venv_dir):
        _clear_bootstrap_incomplete(venv_dir)
    _clear_root_bootstrap_incomplete()
    return True


def _pid_alive(pid: int) -> bool:
    """判斷 PID 是否仍存活（P1-3：venv bootstrap 互斥鎖用來辨識陳舊鎖）。

    POSIX：`os.kill(pid, 0)` 送訊號 0 不會真的送出訊號，只探測目標是否存在／
    呼叫者是否有權限對其送訊號。ProcessLookupError＝PID 不存在（真的已死，
    陳舊鎖可安全清除）；PermissionError＝PID 存在但呼叫者無權限對它送訊號
    （常見於不同使用者擁有的行程）——這種情況代表行程仍存活，不可誤判為
    陳舊鎖去清除別人正在使用的鎖，兩者語意相反、必須分開處理。
    Windows：os.kill 不支援訊號 0 的存活探測語意，改以 OpenProcess 是否能
    成功開啟該 PID 判斷；開啟失敗時再以 GetLastError()==ERROR_ACCESS_DENIED(5)
    區分「行程存在但無權限探測」（視為存活，比照 POSIX PermissionError 分支）
    與其他失敗（如 ERROR_INVALID_PARAMETER，行程真的已死）——P2（Architect/
    SA/QA 三方複審交叉印證）：過去把任何 OpenProcess 失敗都當作「已死」，
    未區分這兩種語意相反的情況。
    """
    if platform_utils.is_windows():
        try:
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        except OSError:
            return False
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        err = ctypes.windll.kernel32.GetLastError()
        return err == 5  # ERROR_ACCESS_DENIED：行程存在但無權限探測，視為存活
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _lock_target_alive(x: int) -> bool:
    """判斷鎖檔中記錄的識別碼是否仍有人存活（MUST FIX A：POSIX 改用 process
    group 追蹤後，鎖檔內同一個整數欄位隨情境橫跨兩種語意，本函式統一判斷）。

    鎖檔內容橫跨本工具生命週期兩種不同語意，且無法單從數字本身分辨是哪一種：
    ①`_acquire_bootstrap_lock()` 剛取得鎖、尚未決定是否需要 bootstrap 時，
    寫入的是 orchestrator（dev_start.py 自己）的一般 PID——這不是它自己的
    process group id（實測：一般由 shell job control 啟動的行程，pid 與自身
    pgid 通常不同），只能用 `_pid_alive()` 判斷；②POSIX 上一旦真的開始執行
    bootstrap，`step_venv()` 記錄的是其直接子行程 PID——因
    `_stream(..., new_process_group=True)` 對其呼叫 `start_new_session=True`
    （`setsid()`），此 PID 同時也是該 process group 的 pgid，直接子行程死亡
    後仍可能有孫行程存活，只有 `os.killpg()` 才能正確判斷（`_pid_alive()` 對
    已死的直接子行程只會回報 False，正是本輪要修的舊 bug）。

    做法：先用 `_pid_alive()` 檢查（涵蓋①，也涵蓋②『直接子行程本身尚存活』
    的情況）；仍判定為死時，POSIX 上再用 `os.killpg()` 補check 一次（涵蓋②
    『直接子行程已死但 process group 內仍有孫行程存活』）。兩者任一回報存活
    即視為存活——寧可保守誤判仍忙碌，也不可誤判陳舊而讓另一個 dev_start 搶
    進場競態寫入，與本工具一貫的 fail-loud 安全哲學一致。
    """
    if _pid_alive(x):
        return True
    if platform_utils.is_windows():
        return False
    try:
        os.killpg(x, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _list_pid_ppid_pairs_windows() -> list[tuple[int, int]] | None:
    """列舉 Windows 系統目前所有行程的 (pid, ppid) 對照（同上，P1）。

    比照 _pid_alive() 現有的 ctypes + kernel32 風格：不新增外部依賴、不 shell
    out 到 wmic/PowerShell，改用 CreateToolhelp32Snapshot + Process32First/Next
    列舉全系統行程建立對照表。
    """
    th32cs_snapprocess = 0x00000002

    class _PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.c_uint32),
            ("cntUsage", ctypes.c_uint32),
            ("th32ProcessID", ctypes.c_uint32),
            ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", ctypes.c_uint32),
            ("cntThreads", ctypes.c_uint32),
            ("th32ParentProcessID", ctypes.c_uint32),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.c_uint32),
            ("szExeFile", ctypes.c_char * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    try:
        snapshot = kernel32.CreateToolhelp32Snapshot(th32cs_snapprocess, 0)
    except OSError:
        return None
    if not snapshot or snapshot == -1:
        return None
    pairs: list[tuple[int, int]] = []
    try:
        entry = _PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(_PROCESSENTRY32)
        if kernel32.Process32First(snapshot, ctypes.pointer(entry)):
            while True:
                pairs.append((entry.th32ProcessID, entry.th32ParentProcessID))
                if not kernel32.Process32Next(snapshot, ctypes.pointer(entry)):
                    break
    finally:
        kernel32.CloseHandle(snapshot)
    return pairs


def _collect_descendant_pids(root_pid: int, pairs: list[tuple[int, int]]) -> set[int]:
    """從 (pid, ppid) 對照表遞迴算出 root_pid 的所有後代 PID（不含自己）。"""
    children_of: dict[int, list[int]] = {}
    for pid, ppid in pairs:
        children_of.setdefault(ppid, []).append(pid)
    descendants: set[int] = set()
    frontier = [root_pid]
    while frontier:
        current = frontier.pop()
        for child in children_of.get(current, []):
            if child not in descendants:
                descendants.add(child)
                frontier.append(child)
    return descendants


class _DescendantWatcher:
    """背景輪詢並累積目標行程存活期間出現過的後代 PID（P1：孫行程孤兒防護）。

    MUST FIX A（Architect 第三輪複審後改版）：**本機制自本輪起僅供 Windows
    使用**（`step_venv()` 只在 `os.name == "nt"` 分支建構本類別）。POSIX 已改
    用 `_stream(new_process_group=True)` + `os.killpg()`（見 `_lock_target_alive`
    docstring）——Architect 用真實 subprocess + SIGKILL 實驗證實：POSIX 行程
    死亡時，其子行程會被核心立即過繼給 subreaper（PID 1），ppid 連結在死亡
    當下就已斷裂；事後才用「目前 ps 快照」回溯死亡行程的後代注定撲空。這正是
    本類別存在的理由（存活期間持續採樣，而非事後回溯），但 process group 語意
    讓 POSIX 不再需要「持續採樣＋事後回溯」這整套機制——`os.killpg()` 天生就
    不受 ppid 過繼影響，一次查詢即可涵蓋任意深度的孫行程。

    Windows 維持本機制不變：實測查證（見 dev_start.py 模組頂層設計說明／
    最終報告）顯示 Windows 的 `th32ParentProcessID` 只是行程建立當下的靜態
    快照，父行程死亡時系統不會重寫它（不像 POSIX 的 ppid 會被動態過繼）——
    故「事後回溯行程樹」在 Windows 上不像在 POSIX 上那樣『因果上必然太晚』，
    背景輪詢＋事後補採樣的既有設計繼續有效，不隨本輪 POSIX 重做而變動。
    """

    def __init__(self, pid: int, poll_interval: float = 0.3) -> None:
        self._pid = pid
        self._poll_interval = poll_interval
        self._seen: set[int] = set()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        while True:
            pairs = _list_pid_ppid_pairs_windows()
            if pairs is not None:
                self._seen |= _collect_descendant_pids(self._pid, pairs)
            if self._stop.wait(self._poll_interval):
                return

    def stop_and_collect(self) -> set[int]:
        """停止輪詢並回傳存活期間觀察到的後代 PID 聯集（呼叫端仍須自行以
        _pid_alive() 檢查其中哪些現在仍存活——本函式只負責『曾經看過誰』）。

        MUST FIX #3（SA + Architect 各自獨立重現的 P2，Windows 適用）：`_run()`
        迴圈是「採樣 → wait(poll_interval)」，過去 `stop_and_collect()` 只 set
        stop event 讓 wait() 提前醒來、不會在醒來時多做最後一次採樣——從
        「最後一次排定採樣」到「本函式被呼叫」之間，有最多一個 poll_interval
        長的空窗，若孫行程恰好在這個空窗內誕生且仍存活，會被完全漏記。這裡在
        背景執行緒停止後，自己再同步做一次採樣並 union 進 `_seen`，用一次廉價
        的同步呼叫換掉這個結構性空窗（而非單純縮小 poll_interval——那只降低
        機率、不消除本質問題）。
        """
        self._stop.set()
        self._thread.join(timeout=12)  # 對齊單次 Toolhelp32 逾時(10s)+緩衝
        pairs = _list_pid_ppid_pairs_windows()
        if pairs is not None:
            self._seen |= _collect_descendant_pids(self._pid, pairs)
        return set(self._seen)


def _acquire_bootstrap_lock() -> int | None:
    """嘗試取得 venv bootstrap 互斥鎖（P1-3）。

    背景（SA 審查以真實並行執行 + kill 重跑實測證實）：兩個並行 dev_start
    呼叫、或 bootstrap 執行到一半被 SIGKILL 後使用者本能重跑，都會讓兩個
    bootstrap 行程競態寫入同一個 .venv，且雙方都回報「✅ 完成」——其中一方
    的環境其實已被覆蓋。以 O_CREAT|O_EXCL 原子建立鎖檔＋寫入自身 PID；鎖檔
    已存在時讀出其中 PID 判斷是否仍存活：存活 → 回傳 None（拿不到鎖，呼叫端
    須中止，不可靜默略過，否則使用者會誤以為環境是新的）；已死（陳舊鎖，
    如上次執行被 SIGKILL）→ 清除後重試一次。

    MUST FIX #2（SA + QA 各自獨立重現的 P1）：鎖檔可能記錄多個 PID（JSON
    陣列，見 `_parse_lock_pids`）——只要其中「任一」PID 仍存活就視為忙碌；
    必須「全部」PID 皆已死透，才視為真正陳舊、可安全清除重試。

    MUST FIX A：存活判斷改用 `_lock_target_alive()` 而非單純 `_pid_alive()`——
    鎖檔內容可能是 orchestrator 自己的一般 PID，也可能是 POSIX 上 bootstrap
    直接子行程的 pgid（其死亡不代表 process group 內孫行程也死了），見該函式
    docstring。
    回傳值為鎖檔 fd，呼叫端須以 try/finally 搭配 _release_bootstrap_lock 釋放。
    """
    for _attempt in range(2):
        try:
            fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                text = LOCK_FILE.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                _warn(f"venv bootstrap 鎖檔（{LOCK_FILE.name}）內容無法辨識（{e}）— "
                      f"為安全起見視為仍被持有，本次中止；請確認無其他 dev_start 執行中"
                      f"後手動刪除該檔")
                return None
            pids = _parse_lock_pids(text)
            if pids is None:
                _warn(f"venv bootstrap 鎖檔（{LOCK_FILE.name}）內容無法辨識（非合法 PID/PID"
                      f"清單）— 為安全起見視為仍被持有，本次中止；請確認無其他 dev_start "
                      f"執行中後手動刪除該檔")
                return None
            alive = [p for p in pids if _lock_target_alive(p)]
            if alive:
                _warn(f"偵測到另一個 dev_start 正在整備 venv（PID {sorted(alive)}），"
                      f"本次中止以避免競態寫入，請稍後重試")
                return None
            try:
                LOCK_FILE.unlink()
            except OSError as e:
                _warn(f"清除陳舊 venv bootstrap 鎖檔失敗（{e}）— 本次中止，"
                      f"請手動刪除 {LOCK_FILE.name}")
                return None
            continue
        except OSError as e:
            _warn(f"建立 venv bootstrap 鎖檔失敗（{e}）— 本次中止")
            return None
        try:
            os.write(fd, str(os.getpid()).encode("utf-8"))
        except OSError:
            pass  # 互斥語意已靠 O_EXCL 原子建立達成，寫入 PID 失敗不影響本次持鎖
        return fd
    return None


def _release_bootstrap_lock(fd: int) -> None:
    """釋放 venv bootstrap 互斥鎖（P1-3）；釋放失敗不該讓整體流程失敗，故吞 OSError。"""
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        LOCK_FILE.unlink()
    except OSError:
        pass


def _parse_lock_pids(text: str) -> list[int] | None:
    """解析鎖檔內容為 PID 清單（MUST FIX #2：SA + QA 各自獨立重現的 P1 ——多孫
    行程同時存活時，鎖檔若只記錄單一 PID，其中一個死亡就會讓整把鎖被誤判陳舊，
    即使其他孫行程仍存活繼續寫 .venv）。

    鎖檔格式改為 JSON 陣列（如 `[123, 456]`），取代先前的單一整數純文字。純
    整數本身即合法 JSON scalar，故舊格式（單一 PID 純文字，如首次
    `_acquire_bootstrap_lock()` 寫入 orchestrator PID 時）天然可被本函式解析
    為單元素清單，不需要額外的雙格式分支。解析失敗或內容並非 int / int 陣列
    時回傳 None，呼叫端須視為「無法辨識」（比照修復前對非數字內容的處理，不
    可裸崩潰也不可誤判為可清除）。
    """
    try:
        data = json.loads(text.strip())
    except (ValueError, AttributeError):
        return None
    if isinstance(data, bool):
        return None  # bool 是 int 子類別，明確排除避免誤判
    if isinstance(data, int):
        return [data]
    if isinstance(data, list) and all(
            isinstance(x, int) and not isinstance(x, bool) for x in data):
        return data
    return None


def _record_lock_pids(fd: int, pids: list[int]) -> None:
    """bootstrap 子行程啟動後（或偵測到存活孫行程後），把鎖檔內容改寫成目前
    需要追蹤存活的 PID 清單（MUST FIX #2）。

    背景：先前 `_record_lock_pid(fd, pid)` 只能記錄單一 PID——orchestrator
    被 SIGKILL 後子行程變孤兒仍會寫入 .venv 是前一輪修的問題；本輪 SA/QA 各自
    重現的是「直接子行程一次 fork 出多個孫行程（如真實 uv 內部平行化下載/
    建置），只記錄 min(live) 其中一個」——短命的那個一死，鎖就被誤判全數陳舊。
    改為記錄完整清單，任一仍存活都要能被 `_peek_bootstrap_lock()` /
    `_acquire_bootstrap_lock()` 偵測為忙碌。
    """
    try:
        payload = json.dumps(sorted(pids)).encode("utf-8")
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, payload)
    except OSError:
        pass  # 寫入失敗最壞情況退回記錄先前內容，不影響鎖的原子建立語意


def _peek_bootstrap_lock() -> int | None:
    """非破壞性檢查：鎖是否被目前仍存活的行程持有（不嘗試取鎖/不清理陳舊鎖，
    純讀取判斷）。回傳其中一個存活 PID（供警告訊息沿用既有格式）或 None。

    P1（Architect + SA 複審實測重現）：`_acquire_bootstrap_lock()` 只在
    `reason is not None`（需要跑 bootstrap）時才會被呼叫，但 `prev is None`
    （既有 .venv 沿用、只記首次依賴基準）分支完全不設 reason、也就完全不會
    取鎖——orchestrator 被 SIGKILL 後孤兒子行程仍在寫 .venv，使用者重跑若
    恰好落入這個分支，鎖形同虛設。本函式在 step_venv() 最開頭無條件檢查，
    不論後續走哪個分支都能攔下。

    MUST FIX #2：鎖檔內容改為 PID 清單，只要其中任一 PID 仍存活就視為忙碌，
    不可只看清單中的某一個。

    MUST FIX A：存活判斷改用 `_lock_target_alive()`（見該函式 docstring）——
    POSIX 上鎖檔可能記錄的是一個 process group id（直接子行程已死但孫行程
    仍存活時，單純 `_pid_alive()` 會誤判為陳舊）。
    """
    try:
        text = LOCK_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    pids = _parse_lock_pids(text)
    if pids is None:
        return None
    alive = sorted(p for p in pids if _lock_target_alive(p))
    return alive[0] if alive else None


def step_venv(now: str, state: dict, force: bool, cross_same_flavor: bool = False) -> bool:
    _hr(4, "venv／依賴整備")
    busy_pid = _peek_bootstrap_lock()
    if busy_pid is not None:
        print(f"    ❌ 偵測到另一個 dev_start 正在整備 venv（PID {busy_pid}）— "
              f"本次中止以避免競態寫入，請稍後重試", file=sys.stderr)
        SUMMARY["venv"] = "❌ 失敗（另一個 dev_start 執行中，見上方警告）"
        return False

    # P2（SA 審查）：鎖的取得點提前到 _ensure_venv_shape() 呼叫之前，涵蓋整個
    # step_venv() 從換手判斷到 bootstrap 執行的全程——過去鎖只包住 _run_bootstrap()，
    # 兩個「鎖檔都還不存在、幾乎同時起跑」的 dev_start 呼叫，_ensure_venv_shape()
    # 的換手 rename 邏輯完全不受保護（僅靠 Path.rename()/os.replace() 對目的地
    # 已存在天生失敗僥倖沒有資料損毀，不是設計出來的保證）。
    lock_fd = _acquire_bootstrap_lock()
    if lock_fd is None:
        print("    ❌ 無法取得 venv bootstrap 互斥鎖 — 本次中止（見上方警告），請稍後重試",
              file=sys.stderr)
        SUMMARY["venv"] = "❌ 失敗（bootstrap 鎖被佔用，見上方警告）"
        return False

    release_lock = True
    try:
        shape = _ensure_venv_shape(now)
        flavor = _flavor(now)
        prev = state.get("deps_hash", {}).get(flavor)
        cur = _deps_hash()

        if cross_same_flavor:
            # mac⇄linux 同為 posix 形狀：形狀檢查與 per-flavor hash 都分不出跨 OS，
            # 但 venv 二進位跨 OS 不相容 → 先移除既有 .venv 再 bootstrap（不移除的話
            # bootstrap 的「既有 .venv 沿用」分支會以跨 OS 直譯器跑 pip 而失敗）。
            # 獨立於 force 判斷之外執行（SD 審查 P1）：先前寫在 elif 鏈裡，
            # `--force-bootstrap` 與跨 OS 切換同時發生時會整段跳過本清理，讓
            # force 這個「救援旗標」在最需要救援時反而失敗。
            venv = ROOT / ".venv"
            if _safe_exists(venv) or _safe_is_symlink(venv):
                try:
                    if venv.is_symlink():
                        venv.unlink()
                    else:
                        shutil.rmtree(venv)
                    print("    跨 OS 同 flavor：既有 .venv 已移除（避免 bootstrap 沿用跨 OS 二進位）")
                except OSError as e:
                    _warn(f"移除跨 OS .venv 失敗（{e}）— bootstrap 可能沿用後失敗，屆時請手動刪除 .venv 重跑")

        reason: str | None = None
        ok = True
        if force:
            reason = "--force-bootstrap 指定"
        elif cross_same_flavor:
            reason = "跨 OS 同 flavor 切換（如 mac⇄linux）— venv 二進位不相容需重建"
        elif shape == "missing":
            reason = "本平台無可用 .venv（首次／跨平台切換且無快取／換手失敗殘留）"
        elif prev is None:
            # 既有 .venv 但無狀態紀錄：過去完全信任現狀、只記基準、不重裝，未做任何
            # 健檢（Architect 建議一併修：這個分支正是 P1 busy-lock 檢查要堵住的
            # 繞過路徑——若不健檢，孤兒行程覆寫過的壞損 .venv 會被靜默沿用）。
            # 健檢通過才維持原行為；健檢失敗視同壞損，改走正常 bootstrap 路徑。
            # 本輪新增：即使健檢通過，也要檢查 bootstrap 未完成哨兵（P1，四方
            # 複審共同發現——venv 建立成功但 pip install 失敗時，健檢只跑得動
            # python --version，完全不驗證套件是否真的裝好，會把「其實半殘」
            # 的 venv 誤判為完整並標記為本平台正常建置）。MUST FIX #4：除了
            # .venv 內部原有哨兵，也要檢查 ROOT 層級哨兵——涵蓋「首次建置期間
            # dev_start.py 本體被 Ctrl-C 打死，.venv 內部哨兵完全沒機會寫入」
            # 這個門檻更低的情境。
            healthy, detail = _venv_healthy(_venv_python(flavor))
            incomplete = (_bootstrap_incomplete_marker_present(ROOT / ".venv")
                          or _root_bootstrap_incomplete_marker_present())
            if healthy and not incomplete:
                print("    既有 .venv 沿用；首次記錄依賴基準（如疑不完整可 --force-bootstrap）")
                SUMMARY["venv"] = "沿用既有 .venv（首次記錄依賴基準）"
            elif not healthy:
                reason = f"既有 .venv 健檢失敗（{detail}）— 視為壞損重新整備"
            else:
                reason = "偵測到上次 bootstrap 未完整結束（哨兵標記殘留）— 視為壞損重新整備"
        elif prev != cur:
            reason = "依賴檔變動（pyproject.toml / requirements-ci.txt hash 不符）"
        else:
            msg = "快取秒級換回，依賴新鮮" if shape == "restored" else "依賴新鮮（hash 未變）"
            print(f"    ✅ {msg} — 跳過重裝")
            SUMMARY["venv"] = msg

        if reason is not None:
            # P1-3：bootstrap 會整包改寫 .venv，兩個並行 dev_start（或執行到一半被
            # SIGKILL 後使用者本能重跑）會競態寫入同一份 .venv，且雙方都回報「✅
            # 完成」——其中一方環境其實已被覆蓋。用 PID lock 互斥，拿不到鎖就中止
            # （fail loud），不可靜默略過讓使用者誤以為環境是新的。
            #
            # MUST FIX A（Architect 第三輪複審用真實驗證證明「事後 ppid 回溯」在
            # 因果上必然太晚後的根本重做）：POSIX 與 Windows 從此分道——
            # POSIX 改用 process group（`_stream(new_process_group=True)` 令
            # 直接子行程 setsid 成為新 session leader，其 PID 即 pgid）+
            # `os.killpg()` 判斷整個行程樹是否仍有成員存活，不再需要背景輪詢
            # 事後回溯（`_DescendantWatcher`）；Windows 維持既有設計不變——
            # 實測查證 Windows 的 `th32ParentProcessID` 是行程建立當下的靜態
            # 快照，父行程死亡不會被系統重寫（不像 POSIX 的 ppid 會被動態過繼
            # 給 subreaper），故「事後回溯」在 Windows 上不像在 POSIX 上那樣
            # 因果必然太晚，沿用原機制是可接受、有明確技術依據的判斷。
            if platform_utils.is_windows():
                watcher_box: dict[str, _DescendantWatcher] = {}

                def _on_bootstrap_start(pid: int) -> None:
                    _record_lock_pids(lock_fd, [pid])
                    watcher = _DescendantWatcher(pid)
                    watcher.start()
                    watcher_box["watcher"] = watcher

                ok = _run_bootstrap(now, reason, on_start=_on_bootstrap_start)

                # P1（SA + QA 各自用真實 subprocess+kill 重現）：鎖過去只追蹤
                # 「直接子行程」PID，精準 kill 掉它後，其前景 fork 出的孫行程
                # （如真實 bootstrap.ps1 呼叫 pip install 內部再開的子行程）
                # 仍存活繼續寫 .venv，若在此無條件釋放鎖，下一輪 dev_start 可
                # 在孫行程還在跑時立即重新取鎖進場，造成競態覆寫。改為檢查
                # 直接子行程存活期間觀察到的所有後代，任一仍存活就不可靜默
                # 釋放——並把鎖檔內容改指向「全部」存活後代（MUST FIX #2：
                # SA + QA 各自重現多孫行程同時存活時，先前只記錄 min(live)
                # 單一 PID，其中壽命較短的一個先死就會讓鎖被誤判全數陳舊，
                # 即使壽命較長的仍存活——沿用既有陳舊鎖偵測機制：全部後代終
                # 將結束，屆時 _acquire_bootstrap_lock() 會自然偵測到「皆已
                # 死」並清除，鎖不會永久卡死，不需要另外設計一套解鎖路徑）。
                watcher = watcher_box.get("watcher")
                observed = watcher.stop_and_collect() if watcher is not None else set()
                live = {p for p in observed if _pid_alive(p)}
                if live:
                    # 短暫寬限重查一次：避免把「剛結束、尚待系統收屍」的良性
                    # 殭屍誤判為孤兒（zombie 對 OpenProcess 而言仍算存活）。
                    time.sleep(0.5)
                    live = {p for p in live if _pid_alive(p)}
                if live:
                    _record_lock_pids(lock_fd, sorted(live))
                    _warn(f"偵測到 bootstrap 遺留的孫行程仍存活（PID {sorted(live)}）— "
                          f"鎖暫不釋放，請確認該行程結束後手動刪除 {LOCK_FILE.name} 或稍後重試"
                          f"（該行程結束後鎖會自動視為陳舊並清除，無需手動處理）")
                    ok = False
                    release_lock = False
            else:
                # POSIX：直接子行程獨立成新 process group（見 _stream 與
                # _run_bootstrap docstring），pgid 恆等於其自身 PID。用
                # os.killpg 判斷整個 group（含任意深度的孫行程）是否仍有成員
                # 存活，取代事後 ppid 回溯——天然涵蓋多孫行程情境，不需要再
                # 追蹤個別 PID 清單，鎖檔內容全程維持最初記錄的這一個 pgid
                # 不變（不需要像 Windows 分支那樣事後改寫成觀察到的後代 PID）。
                pgid_holder: dict[str, int] = {}

                def _on_bootstrap_start(pid: int) -> None:
                    _record_lock_pids(lock_fd, [pid])
                    _set_active_bootstrap_pgid(pid)  # 供 Ctrl-C 訊號轉發使用
                    pgid_holder["pgid"] = pid

                try:
                    ok = _run_bootstrap(now, reason, on_start=_on_bootstrap_start)
                finally:
                    # 無論成功/失敗/例外都要清除，避免遺留一個「其實已死」的
                    # pgid 讓下次無關的 Ctrl-C（如 step_hooks 期間）誤轉發。
                    _set_active_bootstrap_pgid(None)

                pgid = pgid_holder.get("pgid")
                if pgid is not None and _lock_target_alive(pgid):
                    # 短暫寬限重查一次：避免把「剛結束、尚待系統收屍」的良性
                    # 殭屍誤判為孤兒（比照 Windows 分支既有邏輯，見上）。
                    time.sleep(0.5)
                if pgid is not None and _lock_target_alive(pgid):
                    _warn(f"偵測到 bootstrap process group 仍有行程存活（pgid={pgid}）— "
                          f"鎖暫不釋放，請確認相關行程結束後手動刪除 {LOCK_FILE.name} 或"
                          f"稍後重試（該行程結束後鎖會自動視為陳舊並清除，無需手動處理）")
                    ok = False
                    release_lock = False

        if ok and not _safe_exists(_venv_python(flavor)):
            print("    ❌ 整備後仍找不到 venv 直譯器 — 請檢查 bootstrap 輸出", file=sys.stderr)
            ok = False
        if ok:
            SUMMARY.setdefault("venv", "bootstrap 完成（依賴已安裝）")
            # WHY（DEF-101-207）：.python-version 升版後，bootstrap 對「既有 .venv
            # 沿用」路徑不會換直譯器（uv/venv 只在建立當下選版），而 pin 檔不在
            # DEPS_FILES 內、hash 觸發是無效藥——唯一可見點是整備成功後對 venv
            # 直譯器實測版本。放在收尾塊涵蓋沿用/快取換回/hash 未變/bootstrap
            # 完成全部路徑；純 advisory，任一端查不到（None）即靜默。
            target = _python_version_target()
            if target is not None:
                actual = _venv_python_minor(_venv_python(flavor))
                if actual is not None and actual != target:
                    _warn(f"venv Python {actual} 與 .python-version 目標 {target} "
                          f"不一致——bootstrap 沿用既有 venv 不換直譯器（DEF-101-207），"
                          f"需對齊請刪除 .venv 後重跑 dev_start")
            # 記錄「這份 .venv 內容是本平台建的」，供下次跨機換手判斷可信度（P1-1）
            _write_origin_marker(ROOT / ".venv", now)
        else:
            SUMMARY["venv"] = "❌ 失敗（見上方錯誤）"
        return ok
    finally:
        if release_lock:
            _release_bootstrap_lock(lock_fd)


def step_hooks(now: str, is_repo: bool) -> None:
    _hr(5, "git hooks 檢核（根層 dispatcher）")
    if not is_repo:
        _warn("非 git repo — 跳過 hooks 檢核")
        SUMMARY["hooks"] = "跳過（非 git repo）"
        return
    # linked worktree：core.hooksPath 寫在共享 .git/config（無 extensions.worktreeConfig
    # 時對所有 worktree 共用），故仍照常讀取比對——過去版本一偵測到 linked worktree
    # 就直接跳過檢查、斷言「對本 worktree 仍生效」，但從未真的驗證主 checkout 是否
    # 裝過 hooks；若主 checkout 從未安裝，會在零警告下讓 commit/push 閘門形同虛設
    # （Architect 複審 P1，實測重現：全新 clone 後立即建 worktree，hooksPath 未設定
    # 時舊版仍印出「仍生效」）。差異只在於：偵測到未生效時，linked worktree 內
    # 不嘗試自動修（安裝腳本的 worktree 防護會拒絕執行並誤報「安裝失敗」），
    # 而是明確指向主 checkout。
    #
    # 判定演算法（是否為 linked worktree、預期 dispatcher 目錄在哪、core.hooksPath
    # 是否生效）與 tools/check_hooks_liveness.py（供 integration_gate/local_ci_gate
    # 呼叫的 advisory-only 檢查）共用同一份純函式 evaluate()，避免兩處各自重寫一份
    # 同款演算法後行為分歧（四方複審 S22 / DEF-101-068(c)）。本函式只負責「取得輸入」
    # （沿用既有 _git()，固定 -C ROOT、不依賴 cwd）與「拿到結果後要自動修復」；
    # is_file 檢查注入自家的 _safe_is_file（吞外接碟/網路磁碟抖動的 OSError，見
    # TestStepHooksIsFileOSError 迴歸測試），判定邏輯本身不在此重寫。
    gd = _git("rev-parse", "--git-dir").stdout.strip()
    gcd = _git("rev-parse", "--git-common-dir").stdout.strip()
    cur = _git("config", "--get", "core.hooksPath").stdout.strip()
    result = check_hooks_liveness.evaluate(ROOT, gd, gcd, cur, is_file=_safe_is_file)
    if result.ok:
        print("    ✅ core.hooksPath 指向根層 dispatcher，三支 hook 齊備")
        SUMMARY["hooks"] = "正常"
        return
    reason = "未設定" if not cur else f"漂移（目前={cur}）"
    if result.is_linked_worktree:
        _warn(f"linked worktree：core.hooksPath {reason} — 本 worktree 無法自行安裝"
              f"（會被安裝腳本的 worktree 防護拒絕），請至主 checkout 執行任一支 "
              f"install_git_hooks（見 ONBOARDING §6）")
        SUMMARY["hooks"] = f"未生效（linked worktree，{reason}，需至主 checkout 安裝）"
        return
    print(f"    core.hooksPath {reason} → 重跑安裝腳本")
    if _flavor(now) == "windows":
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File",
               str(ROOT / "AutoClaude" / "tools" / "install_git_hooks.ps1")]
    else:
        cmd = ["bash", str(ROOT / "AutoClaude" / "tools" / "install_git_hooks.sh")]
    if _stream(cmd) == 0:
        SUMMARY["hooks"] = "已自動重設"
    else:
        # 設計決策：hooks 失敗不改整體 rc（venv 已可用、四支閘門腳本另有 liveness
        # 偵測兜底；rc 非零會讓 wrapper 拒絕啟用 venv，懲罰過當）——以醒目警告
        # ＋摘要標示＋✅ 行警告計數承擔 fail-loud
        _warn("git hooks 安裝失敗（閘門目前未生效）— 請手動重跑任一支 "
              "install_git_hooks（見 ONBOARDING §6）")
        SUMMARY["hooks"] = "安裝失敗（見警告）"


# nightly 心跳過期門檻（天）：>8 天 = 兩個週末都沒跑過，排程幾乎必已停擺。
_HEARTBEAT_MAX_AGE_DAYS = 8

# launchd 排程 label：與 tools/install_mac_nightly.sh 的 LABEL 同值同語意
# （雙站點由 test_dev_start.py 的跨站字面互鎖機械繫結，ARCH-R15-3）。
_NIGHTLY_LAUNCHD_LABEL = "com.autoclaude.nightly"


def _launchd_nightly_loaded() -> bool | None:
    """launchctl 精確查核 nightly 排程是否已載入（DEF-101-203②，純 advisory）。

    三態：True＝已載入；False＝未載入；None＝查不到（非 darwin／launchctl 失敗
    或逾時）。launchctl list 輸出格式為「PID Status Label」三欄（PID 可為 `-`），
    第 3 欄用精確等值比對——防前綴誤中（如 com.autoclaude.nightly2）。
    """
    if not platform_utils.is_macos():
        return None
    try:
        r = subprocess.run(["launchctl", "list"], timeout=10, capture_output=True,
                           encoding="utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    for line in (r.stdout or "").splitlines():
        cols = line.split()
        if len(cols) >= 3 and cols[2] == _NIGHTLY_LAUNCHD_LABEL:
            return True
    return False


def _heartbeat_fail_count(hb: Path) -> int | None:
    """自心跳檔前 3 行抽取 FAIL 計數（ARCH-R15-1）；讀不到/無錨點回 None。

    FAIL=（heartbeat 時戳行之後的「彙總 PASS=… FAIL=…」行）恆為固定第 2 行契約；
    第 3 行僅 FAIL>0 時才存在（失敗 stage 行）。讀前 3 行足夠涵蓋兩態、且防未來
    檔案膨脹（SA-R15-REV-1 訂正：非「3 行恆存在」，regex 對缺席的第 3 行無害）。
    任何 OSError 靜默跳過——本哨兵是 advisory，絕不影響 dev_start 行為。
    """
    try:
        with hb.open(encoding="utf-8", errors="replace") as f:
            head = "".join(next(f, "") for _ in range(3))
    except OSError:
        return None
    m = re.search(r"FAIL=(\d+)", head)
    return int(m.group(1)) if m else None


def _check_nightly_heartbeat(now: str) -> str:
    """nightly 心跳哨兵（R12 ARCH-R12-2，純 advisory）——回傳 summary 片段。

    WHY：launchd/schtasks 排程是否真的在跑過去零機械查核（DEF-101-164 ARCH-8），
    而 CI 停擺（DEF-101-081）期間本地 nightly 是唯一每日兜底層。nightly 腳本結尾
    寫心跳檔（windows→.ps1 既有 nightly_latest.log；mac/posix→run_local_nightly.sh
    R12 起寫 nightly_mac_latest.log），此處只做純 mtime 三態比對：
      缺席   → 提示行＋summary（不入 WARNINGS——排程未啟用是可接受狀態，但要可見）
      >8 天  → _warn（advisory，不阻擋、不改 exit code）
      新鮮   → 一行 OK
    任何 OSError（外接碟抖動等）都不得讓 dev_start 失敗。"""
    name = "nightly_latest.log" if _flavor(now) == "windows" else "nightly_mac_latest.log"
    hb = ROOT / "AutoClaude" / "logs" / name
    try:
        mtime = hb.stat().st_mtime
    except OSError:  # 缺席或不可讀 → 提示（不入 WARNINGS）
        # R15 DEF-101-203②：mac 側缺席不再停留於「雙可能」猜測——launchctl list
        # 是 read-only 精確查核，三態消歧：已載入尚未首跑＝正常／未載入＝要裝／
        # 查不到（None）＝維持下方既有雙可能文案。長解釋不再造第三份完整三態
        # 措辭，指向 install_mac_nightly.sh --status。Windows 分支完全不動
        # （schtasks 精確查核路由 DEF-101-200 Windows 輪）。
        if _flavor(now) != "windows":
            loaded = _launchd_nightly_loaded()
            if loaded is True:
                print(f"    nightly 心跳未偵測（AutoClaude/logs/{name} 不存在）— "
                      f"launchd 已載入、尚未跑過第一輪（正常；首輪 02:00 後產生心跳，"
                      f"詳見 bash tools/install_mac_nightly.sh --status）")
                return "nightly 心跳未偵測（launchd 已載入，尚未首跑—正常）"
            if loaded is False:
                print(f"    nightly 心跳未偵測（AutoClaude/logs/{name} 不存在）— "
                      f"launchd 未載入——安裝：bash tools/install_mac_nightly.sh"
                      f"（見 ONBOARDING §8）")
                return "nightly 心跳未偵測（launchd 未載入，見 ONBOARDING §8）"
        # R14 OPT-3：補「或已安裝但尚未首跑」——launchd/schtasks 剛安裝、首輪 02:00 未到
        # 前心跳檔必然缺席，舊文案只說「未啟用」會誤導剛裝完的人（文案語意對齊
        # install_mac_nightly.sh --status）。查證指令依 flavor 給對等物（R14 一審
        # SD-R14-REV-4＋ARCH-R14-REV-5：勿讓 Windows 使用者拿到 mac-only 指令）。
        verify_cmd = (
            "schtasks /query /tn AutoClaude_Nightly"
            if _flavor(now) == "windows"
            else "bash tools/install_mac_nightly.sh --status"
        )
        print(f"    nightly 心跳未偵測（AutoClaude/logs/{name} 不存在）— 排程可能未啟用，"
              f"或已安裝但尚未跑過第一輪（查證：{verify_cmd}），設定見 ONBOARDING §8；"
              f"CI 停擺期間本地 nightly 為唯一每日兜底")
        return "nightly 心跳未偵測（排程未啟用？或尚未首跑？見 ONBOARDING §8）"
    age_days = (time.time() - mtime) / 86400.0
    # ARCH-R15-1：mtime 只證明「在跑」不證明「在綠」——CI 停擺期間 nightly 是唯一
    # 每日活體，連續全紅時晨間 dev_start 仍 ✅ 是盲區。心跳存在（新鮮或過期皆檢查）
    # 且非 windows flavor 時讀內容抽 FAIL 計數；Windows 側 nightly_latest.log 是
    # 全量 log 非 3 行心跳契約，明確不讀（路由 DEF-101-200 Windows 輪）。
    fail_note = ""
    if _flavor(now) != "windows":
        fail_n = _heartbeat_fail_count(hb)
        if fail_n is not None and fail_n > 0:
            _warn(f"nightly 最近一輪有 FAIL={fail_n}（AutoClaude/logs/{name}）——"
                  f"排程在跑但驗證未全綠，請查 AutoClaude/logs/ 最新 nightly_mac log"
                  f"（ARCH-R15-1）")
            fail_note = f"；最近一輪 FAIL={fail_n}（見警告）"
    if age_days > _HEARTBEAT_MAX_AGE_DAYS:
        _warn(f"nightly 心跳過期（AutoClaude/logs/{name} 距今 {age_days:.1f} 天 > "
              f"{_HEARTBEAT_MAX_AGE_DAYS} 天）— 排程可能已停擺，請檢查 launchd/schtasks"
              f"（ONBOARDING §8）")
        return f"nightly 心跳過期（{age_days:.1f} 天，見警告）{fail_note}"
    print(f"    ✅ nightly 心跳新鮮（AutoClaude/logs/{name}，距今 {age_days:.1f} 天）")
    return f"nightly 心跳新鮮{fail_note}"


def _check_ci_liveness(is_repo: bool) -> str | None:
    """CI 活性哨兵（DEF-101-208，純 advisory）——回傳 summary 片段，None＝靜默跳過。

    WHY：CI 額度停擺（DEF-101-081）期間 GitHub Actions 可能長期紅/停，push 者
    以為雲端有兜底其實沒有——本哨兵用 gh 的 read-only API（零 Actions 額度）
    查最新 run 結論。三道靜默跳過閘：無 gh／step_sync 已判定離線或跳過（重用
    其判定，不做第二次網路探測）／非 git repo。全函式 try/except 兜底：任何
    例外不得改變 dev_start 行為（同心跳哨兵契約）。

    SD-R15-REV-1 訂正：GitHub Actions API 對尚未跑完的 run（queued/in_progress）
    `conclusion` 恆為 null——若只看 conclusion、剛 push 完就跑本哨兵極易把「還在
    跑」誤判為「帳務停擺/失敗」。故先查 `status`，非 completed 一律視為正常
    （執行中），不落入 `_warn` 異常分支。
    """
    try:
        if shutil.which("gh") is None:
            return None
        sync = SUMMARY.get("sync", "")
        if sync.startswith("離線") or sync.startswith("跳過"):
            return None
        if not is_repo:
            return None
        try:
            r = subprocess.run(
                ["gh", "run", "list", "--limit", "1",
                 "--json", "status,conclusion,updatedAt,workflowName"],
                timeout=15, capture_output=True, encoding="utf-8", errors="replace",
            )
        except (OSError, subprocess.TimeoutExpired):
            r = None
        if r is None or r.returncode != 0:
            # 不入 WARNINGS：gh 未登入/網路抖動是常態，溫和一行即可
            print("    CI 活性未知（gh 不可用或未登入）")
            return "CI 活性未知"
        try:
            runs = json.loads(r.stdout or "")
        except ValueError:
            runs = None
        if not isinstance(runs, list) or not runs or not isinstance(runs[0], dict):
            print("    CI 活性未知（gh 回應無可解析的 run 資料）")
            return "CI 活性未知"
        status = runs[0].get("status")
        conclusion = runs[0].get("conclusion")
        workflow = runs[0].get("workflowName", "?")
        if status != "completed":
            print(f"    CI 活性正常（最新 run：{workflow} 執行中，status={status}）")
            return "CI 活性正常（執行中）"
        if conclusion == "success":
            print(f"    ✅ GitHub CI 活性正常（最新 run：{workflow}=success）")
            return "CI 活性正常"
        _warn(f"GitHub CI 最新 run {workflow}={conclusion}"
              f"（{runs[0].get('updatedAt', '?')}）——帳務停擺/失敗中，"
              f"本地 pre-push＋nightly 為唯一活體驗證（DEF-101-081/208）")
        return f"CI 活性異常（最新 run={conclusion}，見警告）"
    except Exception:
        # 兜底：哨兵絕不可改變 dev_start 的 exit code 或流程
        return None


def step_platform(now: str, is_repo: bool) -> None:
    _hr(6, "平台專屬健檢")
    notes = []
    if _flavor(now) == "windows" and is_repo:
        lp = _git("config", "--get", "core.longpaths").stdout.strip().lower()
        if lp != "true":
            if _git("config", "core.longpaths", "true").returncode == 0:
                notes.append("已設 core.longpaths=true（MAX_PATH=260 護欄，本 repo 路徑警戒 180/200）")
            else:
                _warn("設定 core.longpaths 失敗 — 請手動：git config core.longpaths true")
    for n in notes:
        print(f"    {n}")
    if not notes:
        print("    無需調整")
    hb_note = _check_nightly_heartbeat(now)
    parts = (notes if notes else ["無需調整"]) + [hb_note]
    # R15 DEF-101-208：CI 活性哨兵接在心跳哨兵之後；None＝靜默跳過不入 summary
    ci_note = _check_ci_liveness(is_repo)
    if ci_note is not None:
        parts.append(ci_note)
    SUMMARY["platform"] = "；".join(parts)


def step_finalize(now: str, state: dict, is_repo: bool) -> None:
    _hr(7, "狀態寫回")
    state["developing"] = now
    state.setdefault("deps_hash", {})[_flavor(now)] = _deps_hash()
    state["hostname"] = _platform.node()
    if is_repo:
        head = _git("rev-parse", "--short", "HEAD")
        if head.returncode == 0:
            state["head"] = head.stdout.strip()
    state["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    # temp+replace（原子寫入，per-pid 檔名避免併發 dev_start 互踩）：
    # ①SA 審查 P1——先前直接 write_text 無防護，唯讀外接碟（本功能明文旗艦情境）
    # 會在最後一步、venv/hooks 皆已整備成功後裸崩潰，把已可用的環境誤報為失敗；
    # ②Architect 審查 P2——併發執行下非原子寫入可能讓另一行程讀到截斷/交錯內容
    # （現有 _load_state 已能自癒，但改為 temp+replace 從根本避免這個暫態視窗）。
    # tmp 檔名納入 hostname（P2-3）：本功能明文旗艦情境是外接碟/同步資料夾雙機共用，
    # PID 只在單機內保證唯一——mac 與 windows 兩台機器湊巧同時執行且 PID 相同時，
    # 純 PID 檔名會撞在一起；sanitize 只為防禦 hostname 含檔名不安全字元的低機率邊角。
    host = re.sub(r"[^A-Za-z0-9_.-]", "_", _platform.node()) or "unknown-host"
    tmp = STATE_FILE.with_name(f"{STATE_FILE.name}.tmp-{host}-{os.getpid()}")
    try:
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(STATE_FILE)
        print(f"    已寫回 {STATE_FILE.name}（developing={now}）")
    except OSError as e:
        _warn(f"{STATE_FILE.name} 寫入失敗（{e}）— 本次整備仍已完成，"
              f"但下次執行可能誤判 Developing/依賴基準，請確認 {ROOT} 可寫入")
        try:
            tmp.unlink()
        except OSError:
            pass


def _print_summary(ok: bool) -> None:
    print("\n================ dev_start 摘要 ================")
    for label, key in (("環境", "env"), ("GitHub 同步", "sync"), ("venv／依賴", "venv"),
                       ("git hooks", "hooks"), ("平台健檢", "platform")):
        print(f"  {label}：{SUMMARY.get(key, '（未執行）')}")
    if WARNINGS:
        print(f"  ⚠️  警告 {len(WARNINGS)} 件：")
        for w in WARNINGS:
            print(f"    - {w}")
    if ok:
        note = f"（含 {len(WARNINGS)} 件警告，見上）" if WARNINGS else ""
        print(f"\n✅ 啟動整備完成{note}。下一步：於「已啟用 .venv」的終端機、在 monorepo 根啟動 claude")
        print("   （source tools/dev_start.sh 或 . tools\\dev_start.ps1 會自動啟用 .venv）")
    else:
        print("\n❌ 啟動整備未完成（見上方錯誤）", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    # 編碼重設已於模組載入時處理（見檔案上方），涵蓋含本函式在內的所有呼叫路徑。
    ap = argparse.ArgumentParser(
        description="跨平台自動偵測啟動：環境偵測 → GitHub 同步 → 切換 → venv/hooks 整備")
    ap.add_argument("--no-sync", action="store_true", help="跳過 GitHub 同步（離線）")
    ap.add_argument("--force-bootstrap", action="store_true",
                    help="強制重跑 bootstrap 重裝依賴")
    args = ap.parse_args(argv)

    print("===== AISDCL_Agent dev_start（自動偵測啟動）=====")
    print(f"repo 根：{ROOT}")

    now = _now_label()
    is_repo = _git("rev-parse", "--git-dir").returncode == 0
    state = _load_state()
    developing = state.get("developing")
    env_changed = developing is not None and developing != now
    # 跨 OS 但同 venv flavor（mac⇄linux 皆 posix）：形狀/hash 皆分不出，須強制重裝
    cross_same_flavor = env_changed and _flavor(developing) == _flavor(now)

    _hr(1, "環境偵測（Developing vs Now）")
    print(f"    Now（當前平台）      ：{now}（host: {_platform.node()}）")
    print(f"    Developing（上次開發）：{developing or '（無紀錄，首次執行）'}")
    if env_changed:
        print(f"    → 偵測到跨平台切換：{developing} → {now}，將執行切換程序")
        SUMMARY["env"] = f"{developing} → {now}（已切換）"
    else:
        SUMMARY["env"] = f"{now}（無切換）" if developing else f"{now}（首次紀錄）"

    # MUST FIX A 必要配套：POSIX 上 step_venv() 對 bootstrap 直接子行程呼叫
    # start_new_session=True，使其脫離終端機 foreground process group，Ctrl-C
    # 不會再自然傳到 bootstrap 樹——安裝 SIGINT/SIGTERM handler，於有進行中的
    # bootstrap 時主動轉發訊號給整個 process group（見
    # _forward_signal_to_bootstrap_group docstring）。僅 POSIX 安裝：Windows
    # 分支未使用 start_new_session，既有行為（Ctrl-C 由終端機直接送達整個
    # 前景 process group）不受影響，不需要、也不應額外安裝本 handler。
    # 用 try/finally 確保無論如何結束都還原成呼叫前的 handler，不汙染呼叫端
    # （如測試、或未來把 main() 包進更大程式的情境）。
    old_sigint = old_sigterm = None
    if not platform_utils.is_windows():
        old_sigint = signal.signal(signal.SIGINT, _forward_signal_to_bootstrap_group)
        old_sigterm = signal.signal(signal.SIGTERM, _forward_signal_to_bootstrap_group)
    try:
        step_sync(args.no_sync, is_repo)
        step_switch(env_changed)
        ok = step_venv(now, state, args.force_bootstrap, cross_same_flavor)
        if ok:
            step_hooks(now, is_repo)
            step_platform(now, is_repo)
            step_finalize(now, state, is_repo)
    finally:
        if not platform_utils.is_windows():
            signal.signal(signal.SIGINT, old_sigint)
            signal.signal(signal.SIGTERM, old_sigterm)

    _print_summary(ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
