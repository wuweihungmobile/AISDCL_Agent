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
import hashlib
import json
import platform as _platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / ".dev_env_state.json"
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


def _stream(cmd: list[str]) -> int:
    """即時輸出地執行外部指令（bootstrap / pull / hooks 安裝）。

    flush：stdout 為 pipe（CI log）時 Python 端有緩衝，不 flush 會讓子行程
    輸出插隊到步驟標頭之前，破壞取證順序。
    刻意不設 timeout：pull/bootstrap 屬互動長工（合法耗時數分鐘），任意上限
    會誤殺；掛住時使用者可 Ctrl-C，且發生於 state 寫回之前（重入安全）。
    """
    print(f"    $ {' '.join(cmd)}", flush=True)
    try:
        return subprocess.run(cmd, cwd=str(ROOT)).returncode
    except FileNotFoundError:
        print(f"    ❌ 找不到指令：{cmd[0]}", file=sys.stderr)
        return 127


def _now_label() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def _flavor(label: str) -> str:
    """venv 目錄形狀：windows=Scripts\\python.exe；mac/linux 同為 posix=bin/python。"""
    return "windows" if label == "windows" else "posix"


def _venv_python_at(base: Path, flavor: str) -> Path:
    return base / ("Scripts/python.exe" if flavor == "windows" else "bin/python")


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
    except OSError:
        pass
    return None


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
    if not STATE_FILE.is_file():
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


_TOML_SECTION_RE = re.compile(r"^\[([\w.\-]+)\]\s*$")
_TOML_DEPS_SECTIONS = {"project", "project.optional-dependencies"}
_TOML_NON_DEPS_KEY_RE = re.compile(r"^\s*(name|version|description|requires-python)\s*=")


def _deps_relevant_lines(text: str, scoped: bool) -> list[str]:
    """過濾出與依賴宣告直接相關的行（P2：縮小 _deps_hash 誤觸發面）。

    整檔位元組雜湊對註解/版本字串/[tool.ruff] 等無關編輯過度敏感，觸發不
    必要的整包重裝。scoped=True（如 pyproject.toml）時只保留 [project] /
    [project.optional-dependencies] 區段內容，並剔除該區段內與依賴無關的
    純中繼資料鍵（name/version/description/requires-python）；scoped=False
    （如純 requirements.txt）整檔皆視為依賴宣告。兩種情形皆濾掉註解/空白行。
    """
    section: str | None = None
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if scoped:
            m = _TOML_SECTION_RE.match(line)
            if m:
                section = m.group(1)
                continue
            if section not in _TOML_DEPS_SECTIONS or _TOML_NON_DEPS_KEY_RE.match(line):
                continue
        out.append(line)
    return out


def _deps_hash() -> str:
    h = hashlib.sha256()
    for f in DEPS_FILES:
        h.update(f.name.encode("utf-8"))
        if not f.is_file():
            h.update(b"<missing>")
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for line in _deps_relevant_lines(text, scoped=(f.suffix == ".toml")):
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
    dirty = bool(_git("status", "--porcelain", "--untracked-files=no").stdout.strip())

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
            if p.is_symlink():
                # rmtree(ignore_errors) 對 symlink 靜默拒刪 → 明確 unlink 只斷連結不動目標
                try:
                    p.unlink()
                except OSError:
                    pass
            elif p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                continue
            rel = str(p.relative_to(ROOT))
            # 事後驗證實刪，不做未經查證的「已清除」宣稱
            if p.exists() or p.is_symlink():
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
    if venv.is_symlink() and not _safe_exists(venv):
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
                    try:
                        if any(cache_other.iterdir()):
                            _warn(f"{cache_other.name}/ 已有內容 — 換手保留即將覆蓋（不可逆）；"
                                  f"若該內容仍需要請先手動備份")
                    except OSError:
                        pass  # 列不出內容不影響後續判斷，仍嘗試 rmtree
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
                if venv.is_symlink():
                    venv.unlink()
                else:
                    shutil.rmtree(venv)
                print("    偵測到壞損 .venv（兩平台直譯器皆缺）→ 已移除，將重建")
            except OSError as e:
                _warn(f"壞損 .venv 移除失敗（{e}）— 請手動刪除 .venv 後重跑")

    if not _safe_exists(venv):
        cache_mine = ROOT / f".venv-cache-{flavor}"
        if cache_mine.is_symlink():
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


def _run_bootstrap(now: str, reason: str) -> bool:
    print(f"    需要 bootstrap：{reason}")
    if _flavor(now) == "windows":
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File",
               str(ROOT / "tools" / "bootstrap.ps1")]
    else:
        cmd = ["bash", str(ROOT / "tools" / "bootstrap.sh")]
    rc = _stream(cmd)
    if rc != 0:
        print(f"    ❌ bootstrap 失敗（rc={rc}）— 請依上方輸出排除後重跑", file=sys.stderr)
        return False
    return True


def step_venv(now: str, state: dict, force: bool, cross_same_flavor: bool = False) -> bool:
    _hr(4, "venv／依賴整備")
    shape = _ensure_venv_shape(now)
    flavor = _flavor(now)
    prev = state.get("deps_hash", {}).get(flavor)
    cur = _deps_hash()

    if force:
        ok = _run_bootstrap(now, "--force-bootstrap 指定")
    elif cross_same_flavor:
        # mac⇄linux 同為 posix 形狀：形狀檢查與 per-flavor hash 都分不出跨 OS，
        # 但 venv 二進位跨 OS 不相容 → 先移除既有 .venv 再 bootstrap（不移除的話
        # bootstrap 的「既有 .venv 沿用」分支會以跨 OS 直譯器跑 pip 而失敗）
        venv = ROOT / ".venv"
        if venv.exists() or venv.is_symlink():
            try:
                if venv.is_symlink():
                    venv.unlink()
                else:
                    shutil.rmtree(venv)
                print("    跨 OS 同 flavor：既有 .venv 已移除（避免 bootstrap 沿用跨 OS 二進位）")
            except OSError as e:
                _warn(f"移除跨 OS .venv 失敗（{e}）— bootstrap 可能沿用後失敗，屆時請手動刪除 .venv 重跑")
        ok = _run_bootstrap(now, "跨 OS 同 flavor 切換（如 mac⇄linux）— venv 二進位不相容需重建")
    elif shape == "missing":
        ok = _run_bootstrap(now, "本平台無可用 .venv（首次／跨平台切換且無快取／換手失敗殘留）")
    elif prev is None:
        # 既有 .venv 但無狀態紀錄：視為已由 bootstrap 建好，只記基準、不重裝
        print("    既有 .venv 沿用；首次記錄依賴基準（如疑不完整可 --force-bootstrap）")
        SUMMARY["venv"] = "沿用既有 .venv（首次記錄依賴基準）"
        ok = True
    elif prev != cur:
        ok = _run_bootstrap(now, "依賴檔變動（pyproject.toml / requirements-ci.txt hash 不符）")
    else:
        msg = "快取秒級換回，依賴新鮮" if shape == "restored" else "依賴新鮮（hash 未變）"
        print(f"    ✅ {msg} — 跳過重裝")
        SUMMARY["venv"] = msg
        ok = True

    if ok and not _venv_python(flavor).exists():
        print("    ❌ 整備後仍找不到 venv 直譯器 — 請檢查 bootstrap 輸出", file=sys.stderr)
        ok = False
    if ok:
        SUMMARY.setdefault("venv", "bootstrap 完成（依賴已安裝）")
        # 記錄「這份 .venv 內容是本平台建的」，供下次跨機換手判斷可信度（P1-1）
        _write_origin_marker(ROOT / ".venv", now)
    else:
        SUMMARY["venv"] = "❌ 失敗（見上方錯誤）"
    return ok


def step_hooks(now: str, is_repo: bool) -> None:
    _hr(5, "git hooks 檢核（根層 dispatcher）")
    if not is_repo:
        _warn("非 git repo — 跳過 hooks 檢核")
        SUMMARY["hooks"] = "跳過（非 git repo）"
        return
    # linked worktree：core.hooksPath 屬主 checkout 管轄（絕對路徑指向主 checkout 的
    # dispatcher，對本 worktree 的 commit/push 仍生效）；在此重設會被安裝腳本的
    # worktree 防護擋下且誤報「閘門未生效」→ 如實跳過（Architect 審查 P2）
    gd = _git("rev-parse", "--git-dir").stdout.strip()
    gcd = _git("rev-parse", "--git-common-dir").stdout.strip()
    if gd and gcd:
        try:
            if Path(gd).resolve() != Path(gcd).resolve():
                print("    linked worktree — 跳過（hooksPath 屬主 checkout 管轄，對本 worktree 仍生效）")
                SUMMARY["hooks"] = "跳過（linked worktree，主 checkout 管轄）"
                return
        except OSError:
            pass
    cur = _git("config", "--get", "core.hooksPath").stdout.strip()
    hooks_ok = False
    if cur:
        try:
            # ROOT 為基準展開（若 cur 本身已是絕對路徑，ROOT / cur 仍等同 Path(cur)——
            # pathlib 的 / 對絕對右運算元會直接取代左邊）；否則相對路徑會誤依「執行時
            # cwd」而非 repo ROOT 展開，造成假性漂移判定（Architect 審查 P2）
            same = (ROOT / cur).resolve() == HOOKS_DIR.resolve()
        except OSError:
            same = False
        hooks_ok = same and all(
            (HOOKS_DIR / h).is_file() for h in ("pre-commit", "pre-push", "post-commit"))
    if hooks_ok:
        print("    ✅ core.hooksPath 指向根層 dispatcher，三支 hook 齊備")
        SUMMARY["hooks"] = "正常"
        return
    reason = "未設定" if not cur else f"漂移（目前={cur}）"
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
    SUMMARY["platform"] = "；".join(notes) if notes else "無需調整"


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
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    print(f"    已寫回 {STATE_FILE.name}（developing={now}）")


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
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass

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

    step_sync(args.no_sync, is_repo)
    step_switch(env_changed)
    ok = step_venv(now, state, args.force_bootstrap, cross_same_flavor)
    if ok:
        step_hooks(now, is_repo)
        step_platform(now, is_repo)
        step_finalize(now, state, is_repo)

    _print_summary(ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
