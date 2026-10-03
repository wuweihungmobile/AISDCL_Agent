#!/usr/bin/env python3
r"""Session 守門的單一指令驗收：唯讀蒐集既有狀態，印一份 JSON 並落到 `trace_dir()`。

用途：Q4′（每個平台至少一筆「statusLine 已安裝且相符、簡報給安全形態」的證據）原本要掌舵者
手動跑十餘項清單；本檔收成一條指令，整份輸出貼回即可由別台機器讀檔判定。零 subprocess、
不呼叫 `--pace`、不碰額度路徑；唯一的檔案寫入是 `trace_dir()` 下的
`session_gate_acceptance_<host>.json`（另有 planner `--check` 推進「未讀結局」游標的
副作用，見下段）。

Windows 執行形態（不用 cd）：
& (Join-Path $repo '.venv\Scripts\python.exe') (Join-Path $repo 'tools\session_gate_acceptance.py')

Q4′ 機械判式（讀 JSON 即判，缺一格即不通過）：
  platform=="win32" ∧ statusline.installed ∧ statusline.matches_current_checkout
  ∧ hook_carrier.exists ∧ verify_hint.default_push_location ∧ verify_hint.default_lastexitcode
  ∧ check.rc==0 ∧ generated_at 距今 ≤14 天 ∧ repo_head 為本 repo HEAD 的祖先。

誠實劃界：量不到的格寫 null 或 `{"error": <類名>}`，絕不寫成通過；輸出含 host 與絕對路徑
（trace_dir／fsm_line），貼進公開位置前先去識別化。`check` 是 planner 的 `--check` 在行程內
跑一次：它會把 `.env` 預設填進環境（結束即還原），也會推進「未讀結局」游標（橫幅留在
`check.banner`，不吞）。
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import platform
import re
import sys
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

import endurance_env  # noqa: E402 — 落檔目錄 SSOT（tools/lib）
import platform_utils  # noqa: E402 — 平台標籤 SSOT（tools/lib）

import _stdio_utf8  # noqa: E402,F401 — 根層 tools/ 慣例：Windows 非 UTF-8 終端印中文不崩潰
from _cli_flags import reject_unknown_argv  # noqa: E402 — 同目錄 SSOT：未知引數秒回 rc=2

SCHEMA = "session_gate_acceptance/1"
#: hook 載具字面（Windows 是真檔、Mac 上是指向 `../bin/python` 的 symlink；兩平台同名）。
_CARRIER = (".venv", "Scripts", "pythonw.exe")  # platform-ok: hook 載具字面，不是可攜路徑
_TAIL_BYTES = 256 * 1024  # 逐字稿尾段讀取量：夠涵蓋最後幾十筆記錄，又不必整檔讀入


def _try(fn, *args):
    """單格 fail-open：例外 ⇒ `{"error": <類名>}`——量不到要看得見，不能崩潰，也不能靜默。"""
    try:
        return fn(*args)
    except Exception as exc:  # noqa: BLE001 — 證據蒐集：壞一格不得讓整份報告消失
        return {"error": type(exc).__name__}


def repo_head(repo: Path) -> str | None:
    """直讀 `.git`（零 subprocess）：HEAD → 鬆散 ref → `packed-refs`；detached 直接是 sha。"""
    git = repo / ".git"
    head = (git / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return head or None
    ref = head[5:]
    if (loose := git / ref).is_file():
        return loose.read_text(encoding="utf-8").strip() or None
    packed = git / "packed-refs"
    for line in packed.read_text(encoding="utf-8").splitlines() if packed.is_file() else []:
        if line.endswith(" " + ref):
            return line.split()[0]
    return None


def hook_carrier(repo: Path) -> dict:
    carrier = repo.joinpath(*_CARRIER)
    return {"path": "/".join(_CARRIER), "exists": carrier.exists(),
            "is_symlink": carrier.is_symlink()}


def last_version(path: Path) -> str | None:
    """逐字稿尾段由後往前找第一筆帶 `version` 的記錄（壞行／半截行直接跳過）；沒有回 None。"""
    with path.open("rb") as fh:
        fh.seek(0, os.SEEK_END)
        fh.seek(max(0, fh.tell() - _TAIL_BYTES))
        tail = fh.read().decode("utf-8", errors="replace")
    for line in reversed(tail.splitlines()):
        try:
            version = json.loads(line).get("version")
        except (ValueError, AttributeError):
            continue
        if isinstance(version, str) and version:
            return version
    return None


def cc_version(repo: Path) -> str | None:
    """本專案最新逐字稿裡最後一筆帶版本的記錄＝Claude Code 版本；量不到回 None。"""
    import harness_feed  # noqa: PLC0415 — 延遲 import：壞了只壞這一格（以下各 collector 同）

    from probe.audit_session import project_transcript_dir  # noqa: PLC0415

    found, _why = harness_feed.pick_transcript(project_transcript_dir(repo), None, os.environ)
    return last_version(found) if found else None


def statusline() -> dict:
    import install_statusline  # noqa: PLC0415

    got = install_statusline.status()
    return {k: got.get(k) for k in (
        "installed", "matches_current_checkout", "python_basis", "settings_file_exists")}


def hint_cells() -> dict:
    import session_brief  # noqa: PLC0415

    default = session_brief.verify_hint(windows=None)
    windows = session_brief.verify_hint(windows=True)
    return {"default_push_location": "Push-Location" in default,
            "default_lastexitcode": "LASTEXITCODE" in default,
            "windows_variant_both": "Push-Location" in windows and "LASTEXITCODE" in windows}


def _fsm_line() -> str:
    import session_brief  # noqa: PLC0415

    return session_brief.sdd_fsm_line()


def _trace_dir() -> str:
    return str(endurance_env.trace_dir())


def check() -> dict:
    """planner `--check` 在行程內跑一次（輸出被攔下，不污染本工具的 stdout）。副作用誠實處理：
    planner 的 `main()` 會把 `.env` 預設填進 `os.environ` ⇒ 結束即還原；它的未讀結局橫幅會順手
    推進已讀游標 ⇒ 橫幅文字留在 `banner`，不吞。例外（含 `SystemExit`）⇒ `rc` 為 null 加類名。"""
    saved, out, err = dict(os.environ), io.StringIO(), io.StringIO()
    try:
        import session_resume_planner as planner  # noqa: PLC0415

        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = planner.main(["--check"])
    except (Exception, SystemExit) as exc:  # noqa: BLE001 — 見 docstring：fail-open
        return {"rc": None, "error": type(exc).__name__}
    finally:
        os.environ.clear()
        os.environ.update(saved)
    text = out.getvalue()
    lines = text.splitlines()
    return {"rc": rc,
            "diff_line": next((ln for ln in lines if ln.startswith("harness used=")), None),
            "lines": len(lines),
            "banner": text.split("session 來源", 1)[0].strip() or None,
            "stderr": err.getvalue().strip()[:200] or None}


def collect() -> dict:
    trace = _try(_trace_dir)  # 先於 check()：planner 會動環境變數
    fsm = _try(_fsm_line)
    state = re.search(r"current_state=([A-Za-z0-9_]+)", fsm) if isinstance(fsm, str) else None
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "platform": sys.platform,
        "os_label": _try(platform_utils.os_label),
        "host": platform.node(),
        "python_version": platform.python_version(),
        "cc_version": _try(cc_version, _REPO),
        "repo_head": _try(repo_head, _REPO),
        "statusline": _try(statusline),
        "hook_carrier": _try(hook_carrier, _REPO),
        "verify_hint": _try(hint_cells),
        "fsm_current_state": state.group(1) if state else None,
        "fsm_line": fsm,
        "check": _try(check),
        "trace_dir": trace,
    }


def main() -> int:
    report = collect()
    text = json.dumps(report, indent=2)  # ensure_ascii 預設開：重導向編碼（UTF-16／CP950）弄不壞它
    print(text)
    if isinstance(report["trace_dir"], str):
        host = re.sub(r"[^\w.-]", "_", report["host"])
        try:
            (Path(report["trace_dir"]) / f"session_gate_acceptance_{host}.json").write_text(
                text + "\n", encoding="utf-8", newline="\n")
        except OSError as exc:
            print(f"WARN: evidence file not written ({type(exc).__name__})", file=sys.stderr)
    return 0


def cli(argv: list[str]) -> int:
    rc = reject_unknown_argv("session_gate_acceptance.py", argv, ())
    return main() if rc is None else rc


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
