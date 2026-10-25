"""Bridge 對根層 SelfImproving CLI 的**唯一**子行程通道：唯讀 `export`
（TCS-SelfImprovingMirror-P1b R2～R4、R6；ADR-SI-12 選項 A）與唯讀預檢 `obs-add --dry-run`
（TCS-SelfImprovingDecide-P2b W4）。

Console 是顯示面、不是資料來源：頁面資料＝`export --json` 的輸出，Bridge 不重算、不快取、
不寫任何檔。
  · export 的 argv 恆為 `[sys.executable, <si_root>/tools/<CLI 腳本>, "export", "--json", "--kind",
    <kind>]`，之後依序可接 `--since`、`--limit`、`--id`；validate 的 argv 恆為
    `[sys.executable, <si_root>/tools/<CLI 腳本>, "obs-add", "--dry-run", "--body-file", "-",
    "--json"]`（本文走 stdin）。**不帶 `--repo`**（預設值＝腳本所在 repo＝`si_root`）、
    **不帶 `-I`／`-P`**（3.11 起 `-I` 蘊含 `-P`，腳本目錄不進 `sys.path`，CLI 自己的相對匯入會失
    敗）。組 argv 的函式只有 `build_argv`（動詞 `export`）與 `build_validate_argv`（動詞 `obs-add`
    接 `--dry-run`）兩個，`Popen` 呼叫只有 `_execute` 的一處、其 argv 引數只來自這兩個函式——
    tests/test_si_readonly_lock.py 的 AST 鎖鎖的就是這些形狀。Bridge **永遠不**組出會寫帳本的 CLI
    動詞（decide、obs-add 的入帳、obs-close）：那些只在主機端由人跑。
    整個 `app/` 只有本檔出現 CLI 腳本的檔名字面。
  · 環境＝白名單＋固定鍵（`build_env`）：機密（`BRIDGE_*`、`MINIMAX_API_KEY`、`AUTOSDD_*`…）
    一律不繼承。
  · 失敗一律 `ApiError(503, "si_unavailable", cause=<九值之一>,
    detail="rc=<n|none>; stderr=<尾段>")`；**合法輸出不是錯誤**（空 `items`、非空 `ne`／
    `problems`、stderr 雜訊、未知鍵皆原樣回傳；validate 的 `ok=false`〔rc 1〕同樣是合法輸出）。

跨平台：子行程旗標走 `procutil.popen_platform_kwargs()`；逾時與超量以行程樹終止
（`procutil.begin_terminate`／`force_kill`，不直接 `os.kill`）。Windows 行為＝venv 的 `python.exe`
是啟動器、真正的直譯器是它的子行程，所以必須殺整棵樹；stdout／stderr 以位元組讀取、UTF-8 解碼。
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import procutil
from .errors import ApiError

logger = logging.getLogger("bridge.si_cli")

#: 以下常數都在「呼叫時」才讀（測試可 monkeypatch，不必等 15 秒或吃 8 MiB）。
#: 子行程逾時（秒）。必須小於 backend 的讀取逾時 20 秒（NFR-P1b-2），否則 Bridge 的 503 會被
#: backend 的 504 蓋掉。
SI_CLI_TIMEOUT_SECONDS = 15.0
SI_EXPORT_SCHEMA_REV = 1
SI_STDOUT_MAX_BYTES = 8 * 1024 * 1024
SI_STDERR_TAIL_CHARS = 1000
#: 封閉集合：路由只能傳這五值。
SI_KINDS = ("observations", "events", "proposals", "runs", "status")

#: CLI 腳本相對 `si_root` 的路徑。
_SCRIPT_REL = Path("tools") / "selfimproving.py"
#: 環境白名單（名稱不分大小寫比對；值取自 Bridge 自己的環境，缺者不補）。
_ENV_ALLOWLIST = frozenset({"PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG",
                            "LC_ALL"})
#: 殺行程樹之後等它退出的寬限；仍不退就強殺。
_REAP_GRACE_SECONDS = 3.0
#: 管道讀取執行緒的收尾寬限（行程已死，管道正常會立刻 EOF）。
_PUMP_JOIN_SECONDS = 2.0
_CHUNK_BYTES = 65536
#: stderr 只留尾端這麼多位元組：UTF-8 一個字元至多 4 位元組，所以「最後 N 個字元」必在其中。
_STDERR_KEEP_BYTES = 4 * SI_STDERR_TAIL_CHARS + 4


def build_env(source: Mapping[str, str], si_root: Path) -> dict[str, str]:
    """子行程環境（純函式）：白名單名稱（不分大小寫）原樣保留鍵與值，加固定鍵；其餘一律丟棄。
    `safe.directory` 只放行 `si_root` 這一條路徑（不用 `*`），且走環境變數、不寫 `.gitconfig`。"""
    env = {k: v for k, v in source.items() if k.upper() in _ENV_ALLOWLIST}
    env.update({
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "safe.directory",
        "GIT_CONFIG_VALUE_0": str(si_root),
    })
    return env


def build_argv(si_root: Path, kind: str, *, since: int | None = None, limit: int | None = None,
               ident: str | None = None) -> list[str]:
    """`export` 的子行程 argv。**唯二**組 argv 的函式之一（AST 鎖：唯一的 `return` 是列表字面值，
    索引 2 為動詞常數 `export`）。"""
    return [sys.executable, str(si_root / _SCRIPT_REL), "export", "--json", "--kind", kind,
            *(["--since", str(since)] if since is not None else []),
            *(["--limit", str(limit)] if limit is not None else []),
            *(["--id", ident] if ident is not None else [])]


def build_validate_argv(si_root: Path) -> list[str]:
    """`obs-add --dry-run` 預檢的子行程 argv（TCS-P2b W4）。**唯二**組 argv 的函式之一（AST 鎖：唯一
    的 `return` 是列表字面值，索引 2 起為動詞配對 `obs-add`＋`--dry-run`）。本文走 stdin（`-`）。"""
    return [sys.executable, str(si_root / _SCRIPT_REL), "obs-add", "--dry-run", "--body-file", "-",
            "--json"]


def _fail(kind: str, cause: str, rc: int | None, stderr: str) -> ApiError:
    """503 `si_unavailable`。日誌只記 kind／cause／rc——不記 stderr，更不記任何環境值。
    `kind` 是 export 的種類或 `validate`。"""
    rc_text = "none" if rc is None else str(rc)
    logger.warning("si cli 失敗：kind=%s cause=%s rc=%s", kind, cause, rc_text)
    return ApiError(503, "si_unavailable", cause=cause, detail=f"rc={rc_text}; stderr={stderr}")


def _pump_stdout(stream: Any, buf: bytearray, limit: int, overflow: threading.Event) -> None:
    """邊讀邊判：累計超過 `limit` 就設旗標並停止讀取（Bridge 不隨輸出無限吃記憶體）。"""
    try:
        while True:
            chunk = stream.read1(_CHUNK_BYTES)
            if not chunk:
                return
            buf += chunk
            if len(buf) > limit:
                overflow.set()
                return
    except (OSError, ValueError):       # 行程樹被終止、管道隨之關閉
        return


def _pump_stderr(stream: Any, tail: bytearray) -> None:
    """只留尾端 `_STDERR_KEEP_BYTES`（攤銷裁剪：超過兩倍才裁，記憶體有界）。"""
    try:
        while True:
            chunk = stream.read1(_CHUNK_BYTES)
            if not chunk:
                return
            tail += chunk
            if len(tail) > 2 * _STDERR_KEEP_BYTES:
                del tail[:-_STDERR_KEEP_BYTES]
    except (OSError, ValueError):
        return


def _terminate_tree(proc: subprocess.Popen[bytes]) -> None:
    """逾時／超量：先快照再終止整棵行程樹，寬限內不退才強殺，最後收掉本體（避免殭屍）。"""
    victims = procutil.begin_terminate(proc.pid)
    try:
        proc.wait(timeout=_REAP_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    procutil.force_kill(procutil.survivors(victims, exclude_pid=proc.pid))
    try:
        proc.wait(timeout=_REAP_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        logger.warning("si cli 子行程在強殺後仍未退出（pid=%s）", proc.pid)


def _tail(tail: bytearray) -> str:
    text = bytes(tail[-_STDERR_KEEP_BYTES:]).decode("utf-8", errors="replace")
    return text[-SI_STDERR_TAIL_CHARS:]


def _parse_export(kind: str, stdout: bytes, stderr: str) -> dict[str, Any]:
    """R4 順序 7～9：恰一份 JSON 物件；`schema_rev` 為整數且等於 `SI_EXPORT_SCHEMA_REV`；`kind` 與
    請求相同、`items` 為陣列。"""
    try:
        # 去尾端空白後須是「恰好一份」JSON 文件（兩份相連、垃圾、空輸出都會拋）。
        obj = json.loads(stdout.decode("utf-8").rstrip())
    except (UnicodeDecodeError, ValueError):
        raise _fail(kind, "bad_json", 0, stderr) from None
    if not isinstance(obj, dict):
        raise _fail(kind, "bad_json", 0, stderr)
    rev = obj.get("schema_rev")
    if type(rev) is not int or rev != SI_EXPORT_SCHEMA_REV:      # bool 是 int 的子類：用 type 判
        raise _fail(kind, "schema_rev_mismatch", 0, stderr)
    if obj.get("kind") != kind or not isinstance(obj.get("items"), list):
        raise _fail(kind, "bad_shape", 0, stderr)
    return obj


def _parse_validate(stdout: bytes, rc: int, stderr: str) -> dict[str, Any]:
    """W4：rc 0 或 1 時 stdout 須是單一 JSON 物件（否則 `bad_json`），且含 `ok`（布林）、`row`
    （字串）、`row_bytes`（整數）、`row_max_bytes`（整數或 null）、`findings`（陣列）（否則
    `bad_shape`）；通過＝逐值透傳（`ok=false` 仍是合法輸出）。"""
    label = "validate"
    try:
        obj = json.loads(stdout.decode("utf-8").rstrip())
    except (UnicodeDecodeError, ValueError):
        raise _fail(label, "bad_json", rc, stderr) from None
    if not isinstance(obj, dict):
        raise _fail(label, "bad_json", rc, stderr)
    ok_shape = (isinstance(obj.get("ok"), bool) and isinstance(obj.get("row"), str)
                and type(obj.get("row_bytes")) is int       # bool 是 int 的子類：用 type 判
                and "row_max_bytes" in obj                  # 鍵必須在；值為整數或 null
                and (obj["row_max_bytes"] is None or type(obj["row_max_bytes"]) is int)
                and isinstance(obj.get("findings"), list))
    if not ok_shape:
        raise _fail(label, "bad_shape", rc, stderr)
    return obj


def _require_script_root(si_root: Path | None, label: str) -> Path:
    """`si_root` 未設＝`si_root_unset`；不是目錄或其下沒有 CLI 腳本＝`si_script_missing`。"""
    if si_root is None:
        raise _fail(label, "si_root_unset", None,
                    "SI_ROOT 未設定（容器內必須設環境變數 SI_ROOT；本機直跑須在 monorepo 內）")
    root = Path(si_root)
    if not root.is_dir() or not (root / _SCRIPT_REL).is_file():
        raise _fail(label, "si_script_missing", None,
                    f"SI_ROOT 不是目錄，或其下沒有 CLI 腳本（SI_ROOT={root}）")
    return root


def _feed_stdin(stream: Any, data: bytes) -> None:
    """把本文餵進子行程的 stdin 後關閉（獨立執行緒：子行程不讀 stdin 或被殺時，寫入會卡住或拋
    `BrokenPipeError`，不能拖住主流程的逾時判斷）。"""
    try:
        stream.write(data)
    except (OSError, ValueError):       # 子行程提前結束或行程樹被終止
        pass
    finally:
        try:
            stream.close()
        except (OSError, ValueError):
            pass


def _execute(argv: list[str], root: Path, label: str,
             stdin_bytes: bytes | None) -> tuple[int, bytes, str]:
    """**整個 `app/` 唯一**的 `Popen` 呼叫：跑 `argv`（只可能來自 `build_argv` 或
    `build_validate_argv`），回傳 `(rc, stdout 位元組, stderr 尾段)`。

    `stdin_bytes` 為 None＝stdin 接 DEVNULL（export）；否則本文以獨立執行緒餵進 stdin（validate）。
    逾時與超量＝終止整棵行程樹並拋 `timeout`／`stdout_too_large`；無法啟動＝`spawn_failed`。
    不解讀 rc、不解析輸出（由呼叫端依各自的判定表處理）。"""
    env = build_env(os.environ, root)
    timeout = SI_CLI_TIMEOUT_SECONDS
    max_bytes = SI_STDOUT_MAX_BYTES
    try:
        proc = subprocess.Popen(
            argv, cwd=str(root), env=env,
            stdin=subprocess.DEVNULL if stdin_bytes is None else subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **procutil.popen_platform_kwargs())
    except OSError as exc:
        raise _fail(label, "spawn_failed", None,
                    f"無法啟動 SelfImproving CLI 子行程（SI_ROOT；{type(exc).__name__}）") from exc

    out_buf, err_tail, overflow = bytearray(), bytearray(), threading.Event()
    pumps = [
        threading.Thread(target=_pump_stdout, args=(proc.stdout, out_buf, max_bytes, overflow),
                         daemon=True, name="si-stdout"),
        threading.Thread(target=_pump_stderr, args=(proc.stderr, err_tail),
                         daemon=True, name="si-stderr")]
    if stdin_bytes is not None:
        pumps.append(threading.Thread(target=_feed_stdin, args=(proc.stdin, stdin_bytes),
                                      daemon=True, name="si-stdin"))
    for pump in pumps:
        pump.start()
    deadline = time.monotonic() + timeout
    killed: str | None = None            # 被 Bridge 終止的原因：timeout｜stdout_too_large
    try:
        pumps[0].join(max(0.0, deadline - time.monotonic()))     # stdout 讀完（EOF）或超量即返回
        if pumps[0].is_alive():
            killed = "timeout"
        elif overflow.is_set():
            killed = "stdout_too_large"
        else:
            try:
                proc.wait(timeout=max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                killed = "timeout"
            else:
                pumps[1].join(max(0.0, deadline - time.monotonic()))
                if pumps[1].is_alive():
                    killed = "timeout"
        if killed is not None:
            _terminate_tree(proc)
    finally:
        for pump in pumps:
            pump.join(_PUMP_JOIN_SECONDS)
        if not any(pump.is_alive() for pump in pumps):          # 還有讀取者時關管道會卡住
            for stream in (proc.stdout, proc.stderr):
                if stream is not None:
                    stream.close()
    stderr = _tail(err_tail)
    if killed is not None:
        raise _fail(label, killed, None, stderr)
    return proc.returncode, bytes(out_buf), stderr


def run_export(si_root: Path | None, kind: str, *, since: int | None = None,
               limit: int | None = None, ident: str | None = None) -> dict[str, Any]:
    """跑一次 `export` 並回傳解析後的 export 物件（逐值透傳，不增刪改任何鍵）。

    失敗一律拋 `ApiError(503, "si_unavailable", cause=…, detail=…)`；不寫任何檔、不快取。
    `kind` 不在 `SI_KINDS`、`ident` 為空或以 `-` 起頭＝呼叫端（Bridge 自己）的 bug，拋 `ValueError`
    （`ident` 若以 `-` 起頭會被 argparse 當成旗標）。
    """
    if kind not in SI_KINDS:
        raise ValueError(f"kind 不在封閉集合 SI_KINDS：{kind!r}")
    if ident is not None and (not ident or ident.startswith("-")):
        raise ValueError(f"ident 不合法：{ident!r}")
    root = _require_script_root(si_root, kind)
    argv = build_argv(root, kind, since=since, limit=limit, ident=ident)
    rc, stdout, stderr = _execute(argv, root, kind, None)
    if rc != 0:
        raise _fail(kind, "nonzero_rc", rc, stderr)
    return _parse_export(kind, stdout, stderr)


def run_validate(si_root: Path | None, raw: bytes) -> dict[str, Any]:
    """`obs-add --dry-run` 預檢（W4）：`raw` 是 UTF-8 JSON 物件的原始位元組（走 stdin），回傳預覽
    物件（`ok`、`row`、`row_bytes`、`row_max_bytes`、`findings`，逐值透傳）。

    唯讀：不寫任何檔、不入帳。rc 為 0（`ok` 為 true）或 1（`ok` 為 false，列規則不合）都是合法輸出；
    其他 rc（含 3＝非 JSON 的輸入）＝`nonzero_rc`。其餘失敗形態同 `run_export` 的判定表。"""
    root = _require_script_root(si_root, "validate")
    rc, stdout, stderr = _execute(build_validate_argv(root), root, "validate", raw)
    if rc not in (0, 1):
        raise _fail("validate", "nonzero_rc", rc, stderr)
    return _parse_validate(stdout, rc, stderr)
