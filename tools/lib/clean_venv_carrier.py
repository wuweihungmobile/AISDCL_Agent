#!/usr/bin/env python3
"""§7 回填用「乾淨 venv」一條龍載具（DEF-200-306）。

背景：`useMacWin.md` B 段第 3 步的乾淨 venv 是**人手**建／裝／探針／回填／刪
（一支 bash 區塊＋一支 PowerShell 區塊，逐步照抄）。上一輪三份 `%TEMP%\\
autoclaude_cleanvenv_*` 殘留正是「人手最後一步忘了刪」的直接後果——本模組把
同一條 SOP 程式化：建（樹外 TEMP）→ 裝依賴 → 探針 psycopg2／sqlalchemy 必
ABSENT → 跑 `tools/sync_onboarding_baselines.py --write --with-slow` →
**必刪**（`finally`，即使中途失敗也刪；除非 `--keep`）。

與既有工具的分工：
    - `tools/bootstrap_core.py` 建的是**本機開發用** `.venv`（挑最新可用版、
      裝好全部 extras）；本模組建的是**§7 回填驗證用**乾淨 venv（刻意不裝
      pg extras，重現 CI 最低語意），兩者目的相反，故不重用其版本挑選邏輯。
    - `tools/lib/stray_venv.py` 只負責**唯讀掃描**殘留（純讀、零刪）；本模組
      是**產生**這類目錄的那一端，兩者以「cleanvenv」命名子字串互相認得
      （`find_temp_cleanvenvs()` 按名稱掃描，不看 `pyvenv.cfg`）。
    - `tools/sync_onboarding_baselines.py --write --with-slow` 本身已有一道
      `pgextras=present` 拒跑（`--allow-pg-extras` 可繞過）；本模組在呼叫它
      之前**另加一道**獨立探針且不提供任何繞過旗標——乾淨 venv 的存在意義
      就是「沒裝 pg extras」，開後門等於讓這支工具形同虛設。

刻意只依賴 stdlib；平台分支只呼叫既有 SSOT（`platform_utils.is_windows()`／
`venv_python_path()`），本檔自身不寫 `sys.platform`／`os.name` 分支（鐵律三）。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_utils  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROBE_MODULES: tuple[str, ...] = ("psycopg2", "sqlalchemy")


class CleanVenvContaminatedError(RuntimeError):
    """乾淨 venv 探測到 pg extras（psycopg2／sqlalchemy）已存在——拒絕跑回填。

    刻意不提供 `--allow-pg-extras` 這類旗標（設計上不可繞過，見檔頭說明）。
    """


def _utc_timestamp() -> str:
    return _dt.datetime.now(tz=_dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def _base_interpreter() -> str:
    """基底直譯器：優先用 `sys._base_executable`（venv 的 `pyvenv.cfg` home，
    即出廠同版直譯器、不含目前這顆 venv 裝的任何套件）；非 venv 環境或該屬性
    不存在則退 `sys.executable`。

    刻意不用「現正跑這支工具的 venv 本身」當基底——那顆 venv 幾乎必然已裝過
    pg extras（本工具很可能就是從已裝好選配的開發 venv 呼叫的），會讓乾淨
    venv 從一開始就不乾淨。
    """
    return getattr(sys, "_base_executable", None) or sys.executable


def _assert_base_interpreter_version_ok(base: str) -> None:
    """`-c` 探針確認基底直譯器版本 ≥ 3.11；不足即 fail-loud（不可靜默降級）。"""
    probe = subprocess.run(
        [base, "-c", "import sys; sys.exit(0 if sys.version_info[:2] >= (3, 11) else 1)"],
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if probe.returncode != 0:
        raise RuntimeError(f"基底直譯器版本 < 3.11（{base}），無法建立乾淨 venv。")


def create_clean_venv(base_temp_dir: Path | None = None) -> Path:
    """在樹外 TEMP 建立乾淨 venv，回傳其目錄（不含 python 路徑）。

    目錄名含 `cleanvenv` 子字串，與 `tools/lib/stray_venv.find_temp_cleanvenvs()`
    的既有命名約定相容。用 stdlib `venv`（本身含 pip）建，刻意不用 `uv venv`——
    uv 建出的 venv 內沒有 pip 模組，後續 `install_deps()` 的 `-m pip install`
    會直接失敗。
    """
    base = _base_interpreter()
    _assert_base_interpreter_version_ok(base)
    root = base_temp_dir if base_temp_dir is not None else Path(tempfile.gettempdir())
    target = root / f"autoclaude_cleanvenv_{_utc_timestamp()}"
    print(f"      指令：{base} -m venv {target}")
    subprocess.run(
        [base, "-m", "venv", str(target)], encoding="utf-8", errors="replace", check=True
    )
    return target


def install_deps(venv_python: Path, repo_root: Path) -> subprocess.CompletedProcess:
    """裝 §7 回填所需依賴：AutoClaude extras + AISDLC_SDD CI 依賴鎖版檔。"""
    argv = [
        str(venv_python),
        "-m",
        "pip",
        "install",
        "-e",
        "AutoClaude/.[dev,notifications,lint]",
        "-r",
        "AISDLC_SDD/AISDLC_SDD_v0.01/requirements-ci.txt",
    ]
    print(f"      指令：{' '.join(argv)}（cwd={repo_root}）")
    return subprocess.run(argv, cwd=repo_root, encoding="utf-8", errors="replace", check=False)


def probe_pg_extras(venv_python: Path) -> str:
    """跑 psycopg2／sqlalchemy 存在性探針，回傳其 stdout 原文
    （每行 `<module> PRESENT/ABSENT`）。"""
    probe_src = (
        "import importlib.util as u; "
        "[print(m, 'PRESENT' if u.find_spec(m) else 'ABSENT') "
        f"for m in {_PROBE_MODULES!r}]"
    )
    result = subprocess.run(
        [str(venv_python), "-c", probe_src],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout or ""


def assert_pg_extras_absent(venv_python: Path) -> None:
    """探針任一模組 PRESENT 即 fail-loud（不跑回填）。"""
    output = probe_pg_extras(venv_python)
    print(f"      探針輸出：{output.strip() or '(空)'}")
    if "PRESENT" in output:
        raise CleanVenvContaminatedError(
            f"乾淨 venv 探測到 pg extras 已存在，拒絕跑回填：\n{output}"
        )


def run_onboarding_sync(venv_python: Path, repo_root: Path) -> int:
    """跑 §7 回填：`tools/sync_onboarding_baselines.py --write --with-slow`。"""
    argv = [str(venv_python), "tools/sync_onboarding_baselines.py", "--write", "--with-slow"]
    print(f"      指令：{' '.join(argv)}（cwd={repo_root}）")
    result = subprocess.run(argv, cwd=repo_root, encoding="utf-8", errors="replace", check=False)
    return result.returncode


def _delete_command(venv_dir: Path, *, is_windows: bool) -> str:
    return f'Remove-Item -Recurse -Force "{venv_dir}"' if is_windows else f'rm -rf "{venv_dir}"'


def cleanup(venv_dir: Path, *, is_windows: bool) -> bool:
    """必刪：`shutil.rmtree`；Windows 唯讀檔補 chmod 再刪一次。刪不掉時印出可
    複製的刪除指令並回 `False`（呼叫端據此讓整體 rc 非零——刪不掉必須
    fail-loud，不能靜默留殘，重演上一輪三份殘留的事故）。
    """
    import shutil

    if not venv_dir.exists():
        return True

    def _onerror(func, path, exc_info):  # shutil.rmtree 回呼簽名固定，型別不可自訂
        import os
        import stat

        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except OSError:
            raise

    try:
        shutil.rmtree(venv_dir, onerror=_onerror)
    except OSError as exc:
        cmd = _delete_command(venv_dir, is_windows=is_windows)
        print(
            f"[ERROR] 無法刪除乾淨 venv：{venv_dir}（{exc}）\n請手動執行：{cmd}",
            file=sys.stderr,
        )
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="§7 回填用乾淨 venv 一條龍：建→裝→探針→跑→必刪（DEF-200-306）"
    )
    parser.add_argument("--dry-run", action="store_true", help="只印步驟，不實際執行")
    parser.add_argument("--keep", action="store_true", help="回填完不自動刪除乾淨 venv")
    parser.add_argument(
        "--repo-root", type=Path, default=_REPO_ROOT, help="repo 根目錄（預設自動偵測）"
    )
    args = parser.parse_args(argv)

    # 本檔進度訊息含中文（印到 stdout）：Windows cp950 console 直接 print 會
    # UnicodeEncodeError 中斷（DEF-82-001／DEF-101-070 家族慣例）。走 SSOT
    # （`platform_utils.init_utf8_streams` → `tools/_stdio_utf8.py`）而不是就地
    # reconfigure：R75 去重後「強制 stdio-UTF-8」只准有一份實作（per-tree 棘輪
    # `test_platform_utils_dedup.py::TestR75StdioUtf8HasOneImplementation` 釘住，
    # 就地寫第二份當場紅）；對測試替身 `io.StringIO` 是安全 no-op，測試內呼叫
    # main() 不會污染 stdout 擷取。
    platform_utils.init_utf8_streams()

    is_win = platform_utils.is_windows()
    repo_root = args.repo_root

    steps = [
        "[1/5] 建立乾淨 venv（樹外 TEMP，stdlib venv，不裝任何套件）",
        "[2/5] 安裝依賴（AutoClaude extras + AISDLC_SDD requirements-ci.txt）",
        "[3/5] 探針 psycopg2／sqlalchemy 必須 ABSENT（PRESENT 即中止，不跑回填）",
        "[4/5] 跑 tools/sync_onboarding_baselines.py --write --with-slow",
        "[5/5] 必刪乾淨 venv（--keep 時改為保留並印出事後刪除指令）",
    ]
    if args.dry_run:
        print("[DRY-RUN] 以下步驟不會實際執行：")
        for step in steps:
            print(f"  {step}")
        return 0

    venv_dir: Path | None = None
    rc = 1
    cleanup_ok = True
    try:
        print(steps[0])
        venv_dir = create_clean_venv()
        venv_python = platform_utils.venv_python_path(venv_dir, is_windows=is_win)
        print(f"      -> {venv_dir}")

        print(steps[1])
        install_result = install_deps(venv_python, repo_root)
        print(f"      -> pip install rc={install_result.returncode}")
        if install_result.returncode != 0:
            raise RuntimeError(f"pip install 失敗，rc={install_result.returncode}")

        print(steps[2])
        assert_pg_extras_absent(venv_python)

        print(steps[3])
        rc = run_onboarding_sync(venv_python, repo_root)
        print(f"      -> rc={rc}")
    except (RuntimeError, CleanVenvContaminatedError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        rc = 1
    finally:
        if venv_dir is not None:
            if args.keep:
                cmd = _delete_command(venv_dir, is_windows=is_win)
                print(f"[KEEP] 未刪除，保留於 {venv_dir}；事後請自行刪除：{cmd}")
            else:
                print(steps[4])
                cleanup_ok = cleanup(venv_dir, is_windows=is_win)

    if not cleanup_ok:
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
