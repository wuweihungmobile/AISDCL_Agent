#!/usr/bin/env python
"""Windows status line 安裝器（R158 P5，主控裁決 DECISION.md〈P5〉）。 round-label-ok

WHY
---
`tools/statusline_context_feed.py::settings_snippet()` 只能印出一份 JSON 片段，
要真的生效仍要人手動貼進 `~/.claude/settings.json`；Windows 端目前完全沒人裝過
（FACTS.md F4：Q4「Windows 沒有 ctx 行」根因＝從未安裝，而非缺陷）。本檔補上
「一鍵安裝／解除／查現況」，並把 `command` 組字統一交給
`statusline_context_feed.build_command()`（避免兩份各自維護的字串邏輯）。

四模式（比照 `tools/install_mac_nightly.sh`／`tools/install_windows_nightly.ps1`
的既有慣例）：
  · 預設（無旗標）＝安裝：把本 checkout 的 `statusLine` 區塊寫進使用者的
    `~/.claude/settings.json`，**只 touch 這一個鍵**，其餘鍵逐字保留。
  · `--uninstall`＝移除該鍵，其餘鍵逐字保留。
  · `--status`＝唯讀查現況，不動任何檔案；rc=0 僅在「已安裝且與本 checkout
    的期望值一致」，否則 rc=1（供腳本化檢查用）。
  · `--dry-run`＝配合安裝／解除使用，只印出將要做的動作，不寫檔（不建立備份）。
  · `--print-command`＝只印出 `statusLine.command` 字串本身，方便手動核對或貼進
    其他工具（例如 D2 驗證指令段落）。

安全性：寫入前一律先把既有檔案原樣備份成
`settings.json.bak-<UTC YYYYmmddTHHMMSSZ>`（僅在檔案原本存在、且本次真的要寫入
時才建立；已是期望值的安裝視為冪等 no-op，不建立備份也不改動檔案）。HOME 目錄
一律經 `Path.home()` 取得，但 `CLAUDE_CONFIG_DIR`（Claude Code 官方環境變數）
設定時優先於 `Path.home()`（DEF-200-415，見 `settings_path()`）——測試以環境
變數／monkeypatch 覆寫即可注入 tempdir，不需要另開一條「測試專用路徑」參數污染
正式介面（各函式仍接受顯式 `home` 參數供測試直接呼叫，CLI 層一律用預設值）。

誠實劃界（待 Windows 親驗，見 R158 analysis_docs.md G2／analysis_sd.md D2／ round-label-ok
refute_q3q4ci.md 3(a)）：
  · statusLine 的 `command` 官方規格上恆為 shell form（無 `args` 陣列可跳過
    殼），本檔管不到 Claude Code 呼叫外層殼那一步是否會閃過一瞬間的視窗；
    `build_command()` 換用同目錄 `pythonw.exe`（若存在）只能保證 `pythonw.exe`
    自己不額外開視窗，不能保證外層殼本身無視窗。
  · 安裝成功後印出的親驗清單只是提醒動作，本檔無法自動確認畫面上有沒有
    `ctx` 字樣、有沒有閃窗——那是純運行時的視覺現象。

stdlib-only（同 `statusline_context_feed.py` 的既有紀律：不保證第三方套件在
目標機器的 PATH 上）。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import _stdio_utf8  # noqa: E402,F401 — 根層 tools/ 慣例：stdout/stderr 強制 UTF-8
import statusline_context_feed as _feed  # noqa: E402 — 同目錄：共用 command 組字函式
from _cli_flags import reject_unknown_argv  # noqa: E402 — 同目錄 SSOT，未知引數秒回拒收

#: 本安裝器唯一會動的 `~/.claude/settings.json` 頂層鍵；其餘鍵一律逐字保留。
STATUS_LINE_KEY = "statusLine"

#: `main()` 接受的旗標集合（SSOT＝`tools/_cli_flags.py::reject_unknown_argv`）。
_KNOWN_FLAGS = ("--uninstall", "--status", "--dry-run", "--print-command")


def settings_path(home: Path | None = None) -> Path:
    """`~/.claude/settings.json` 的絕對路徑。`home` 覆寫供測試以 tempdir 注入；
    CLI 層一律用預設值（`Path.home()`，於 POSIX 上尊重 `$HOME` 環境變數）。

    DEF-200-415：`home` 未顯式指定時，Claude Code 官方環境變數
    `CLAUDE_CONFIG_DIR`（兩平台語意相同：設了即整個 `~/.claude` 設定目錄被該
    目錄取代）優先於 `Path.home()`——設了該變數卻仍固定寫 `~/.claude` 會裝到
    Claude Code 根本不讀的檔，且本檔 `install()`/`status()` 皆會一致誤判成
    「假的已安裝」。空字串／純空白視同未設。"""
    if home is not None:
        return home / ".claude" / "settings.json"
    override = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    if override:
        return Path(override) / "settings.json"
    return Path.home() / ".claude" / "settings.json"


def _utc_stamp() -> str:
    """UTC 時間戳，供備份檔名使用（帶時區的 `strftime`，非 naive `isoformat()`，
    不落入根 CLAUDE.md 鐵律三「naive 本地時間戳」那一類站點）。"""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def backup_path(path: Path) -> Path:
    """對應 `path` 的備份檔路徑：`<原檔名>.bak-<UTC 時間戳>`。"""
    return path.with_name(f"{path.name}.bak-{_utc_stamp()}")


def load_settings(path: Path) -> dict:
    """讀現有 settings.json；不存在或內容空白回空字典。頂層不是 JSON 物件、或
    JSON 本身壞掉一律 raise——安裝器不吞使用者既有設定檔的損壞去靜默清空其他鍵。
    """
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path} 頂層不是 JSON 物件，安裝器拒絕動它")
    return data


def write_settings(path: Path, data: dict) -> None:
    """整份 settings.json 寫回（呼叫端已負責保留其餘鍵）。原子寫＋Windows 檔案鎖重試，
    重用 `statusline_context_feed.atomic_write_json()`，避免第二份複本。"""
    _feed.atomic_write_json(path, data, indent=2)


def desired_status_line() -> dict:
    """本 checkout 要寫入的 `statusLine` 值——直接復用
    `statusline_context_feed.settings_snippet()`，不重複組字邏輯。"""
    return _feed.settings_snippet()[STATUS_LINE_KEY]


def install(home: Path | None = None, *, dry_run: bool = False) -> dict:
    """安裝：只寫 `statusLine` 鍵，其餘鍵原樣保留。冪等：已是期望值即回 `noop`，
    不建立備份也不改動檔案。`dry_run` 時只回報將要做的動作，不寫檔、不備份。
    """
    path = settings_path(home)
    current = load_settings(path)
    desired = desired_status_line()
    if current.get(STATUS_LINE_KEY) == desired:
        return {
            "action": "noop", "path": str(path),
            "reason": "已安裝且與本 checkout 一致（冪等，未改動任何檔案）",
        }
    if dry_run:
        return {"action": "would-install", "path": str(path), "statusLine": desired}
    backup = None
    if path.is_file():
        backup = backup_path(path)
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    updated = dict(current)
    updated[STATUS_LINE_KEY] = desired
    write_settings(path, updated)
    return {
        "action": "installed", "path": str(path),
        "backup": str(backup) if backup else None, "statusLine": desired,
    }


def uninstall(home: Path | None = None, *, dry_run: bool = False) -> dict:
    """解除安裝：移除 `statusLine` 鍵，其餘鍵原樣保留。冪等：本來就沒裝即回
    `noop`。`dry_run` 時只回報，不寫檔、不備份。"""
    path = settings_path(home)
    current = load_settings(path)
    if STATUS_LINE_KEY not in current:
        return {"action": "noop", "path": str(path), "reason": "尚未安裝（冪等，未改動任何檔案）"}
    if dry_run:
        return {"action": "would-uninstall", "path": str(path)}
    backup = backup_path(path)
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    updated = dict(current)
    del updated[STATUS_LINE_KEY]
    write_settings(path, updated)
    return {"action": "uninstalled", "path": str(path), "backup": str(backup)}


def status(home: Path | None = None) -> dict:
    """唯讀查現況，不動任何檔案。`python_basis` 轉述
    `statusline_context_feed.settings_snippet()` 的同名鍵（DEF-200-411：
    `"repo-venv"` 或 `"sys.executable"`），讓「退回 `sys.executable`」這件事在
    `--status` 報告裡可被看見，不靜默。"""
    path = settings_path(home)
    current = load_settings(path)
    installed_value = current.get(STATUS_LINE_KEY)
    snippet = _feed.settings_snippet()
    desired = snippet[STATUS_LINE_KEY]
    return {
        "path": str(path),
        "settings_file_exists": path.is_file(),
        "installed": installed_value is not None,
        "matches_current_checkout": installed_value == desired,
        "statusLine": installed_value,
        "python_basis": snippet.get("_python_basis"),
    }


def _print_verification_checklist() -> None:
    """安裝成功後的親驗提醒（本檔無法自動確認，見檔頭〈誠實劃界〉）。"""
    print(
        "安裝完成——以下需要你親眼確認（本安裝器無法自動驗證這幾項）：\n"
        "  1. 開一個全新的 claude 終端視窗\n"
        "  2. 觀察畫面最下方狀態列是否出現 `ctx ...%` 字樣\n"
        "  3. 觀察開啟過程有沒有一閃而過的主控台/命令提示字元視窗\n"
        "  4. 若有閃窗，或狀態列沒出現，執行："
        "`python tools/install_statusline.py --uninstall`"
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    # 未知引數秒回拒收（根層守門工具契約，SSOT＝tools/_cli_flags.py）
    rc = reject_unknown_argv("install_statusline.py", args, known=_KNOWN_FLAGS)
    if rc is not None:
        return rc

    if "--print-command" in args:
        print(desired_status_line()["command"])
        return 0

    dry_run = "--dry-run" in args

    if "--status" in args:
        report = status()
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0 if report["installed"] and report["matches_current_checkout"] else 1

    if "--uninstall" in args:
        report = uninstall(dry_run=dry_run)
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0

    report = install(dry_run=dry_run)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if report["action"] == "installed":
        _print_verification_checklist()
    return 0


if __name__ == "__main__":
    sys.exit(main())
