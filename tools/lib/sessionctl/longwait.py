"""子代理長等待 `sessionctl runlong`／`waitfor`＋長前景閘（R216 WP-D）。

設計 SessionSwitch_CostModel_Design §3.3 F2、§4.5、§5 D13；
掌舵者 2026-11-18：「專注在不要讓Cache過期!」。

WHY：子代理的提示快取壽命只有 5 分鐘。子代理用前景 PowerShell 等超過 5 分鐘的指令（全套測試、
真機案例）時，下一回合要把整份上下文重寫一次（14 日量測：子代理快取重寫 189 件、8,045 萬 token；
其中長等待 77 件、重放省 85%）。補法＝把「等」切成每段 < 5 分鐘的前景呼叫，每段都讀得到快取、
順便讓快取續命：
  · `runlong --out <檔> -- <argv…>`：子代理以 `run_in_background` 跑；結束時才寫 `<檔>.done`。
  · `waitfor --done <檔>.done --max-sec 240`：前景至多等 `--max-sec` 秒；完成印尾端 40 行與
    `WAITFOR_VERDICT=done rc=<被等指令的 rc>`，未完成印 `WAITFOR_VERDICT=pending`；兩者自身 rc 皆 0
    （DEF-200-622：判決只看末行，不看 rc）。子代理迴圈呼叫它。
  · `pretool_verdict`（D13 長前景閘）：子代理的前景 PowerShell／Bash 呼叫帶 `timeout > 270000`
    ⇒ 擋、指路上兩條。依據：工具預設 timeout 120 秒，要等超過 5 分鐘**必須**顯式設大 timeout
    ⇒ 判準精確、零猜測。
全部純讀 payload／檔案、零 token；時鐘／sleep 以參數注入（不開任何測試用環境變數）。
`.done` 不用 rename／replace（Windows 檔案鎖原語普查）：單次小寫入＋讀端容錯（內容不全當未完成）。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

EV_BLOCK = "longwait_block"
SCHEMA = "autosdd.runlong/1"
#: 前景呼叫 timeout 的擋線（毫秒）：> 這個值就超過 5 分鐘快取壽命扣掉一回合的餘裕。只准下修。
LONG_FG_MS = 270_000
WAIT_DEFAULT_SEC = 240.0
#: `--max-sec` 上限（秒）。必須 < `WAIT_FG_TIMEOUT_MS`/1000：waitfor 自己是前景呼叫，其 timeout
#: 要大於它等的秒數、又不得超過長前景閘的擋線；設計稿寫的 270 與擋線 270000 ms 互相咬死
#: （等 270 秒需要 timeout > 270000 ⇒ 被自己的閘擋），故取 255。只准下修。
WAIT_CEIL_SEC = 255.0
#: waitfor 呼叫的前景 timeout 建議值（毫秒）：須大於 `--max-sec`、不得超過 `LONG_FG_MS`，
#: 否則被閘擋。
WAIT_FG_TIMEOUT_MS = LONG_FG_MS
TAIL_LINES = 40
#: F2 `n_s*＝floor(1.25c/(0.1c+1500))`，c 大時趨近 12；超過仍未完成 ⇒ 不再分段
#: （放冷重寫比續分段便宜）。
N_S_STAR = 12
EXEMPT_RE = re.compile(r"(?:^|\s)#\s*keepwarm-ok:\s*(\S.{3,})$", re.MULTILINE)
POLL_SEC = 0.5
_TOOLS = ("PowerShell", "Bash")


def _warn(msg: str) -> None:
    print(f"⚠️ {msg}", file=sys.stderr)


# ───────────────────────────────────────────────────────────── D13 長前景閘
def _timeout_ms(tool_input: dict):
    raw = tool_input.get("timeout")
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(str(raw).strip()) if isinstance(raw, str) else None
    except ValueError:
        return None


def pretool_verdict(payload: dict, env=None) -> tuple[int, str]:
    """`(0, "")` 放行；`(2, 訊息)` 阻斷。擋 ⇔ 呼叫帶 `agent_id`（子代理；主控不判，其快取 1 小時）
    ∧ 工具 PowerShell／Bash ∧ 非 `run_in_background` ∧ `timeout > 270000`。行內
    `# keepwarm-ok: <WHY>` 豁免（`AUTOSDD_UNATTENDED` 有設時無效）；解析不到一律放行（fail-open）。
    只看 payload，不讀逐字稿。"""
    env = os.environ if env is None else env
    try:
        if not isinstance(payload, dict) or payload.get("tool_name") not in _TOOLS \
                or not payload.get("agent_id"):
            return 0, ""
        tin = payload.get("tool_input")
        if not isinstance(tin, dict) or tin.get("run_in_background"):
            return 0, ""
        ms = _timeout_ms(tin)
        if ms is None or ms <= LONG_FG_MS:
            return 0, ""
        if not env.get("AUTOSDD_UNATTENDED") and EXEMPT_RE.search(str(tin.get("command") or "")):
            return 0, ""
        from . import switch  # noqa: PLC0415 — lazy：多數呼叫走不到這裡

        switch.trace(EV_BLOCK, tool=payload.get("tool_name"), timeout_ms=ms,
                     agent=str(payload.get("agent_id"))[:20])
        return 2, (
            f"🔴 長前景閘：子代理的前景 {payload.get('tool_name')} 呼叫 timeout={int(ms):,} ms，"
            f"超過 {LONG_FG_MS:,} ms。子代理的提示快取只有 5 分鐘，前景等超過它，"
            "下一回合整份上下文要重寫。\n"
            "改成「背景跑＋每段不到 5 分鐘回來看一次」：\n"
            "  ① 背景（run_in_background=true）：\n"
            "     python tools/sessionctl.py runlong --out <輸出檔> -- <原指令 argv…>\n"
            f"  ② 前景（timeout 設 {WAIT_FG_TIMEOUT_MS:,}）：\n"
            "     python tools/sessionctl.py waitfor --done <輸出檔>.done "
            f"--max-sec {WAIT_DEFAULT_SEC:g}\n"
            "     末行 WAITFOR_VERDICT=pending＝還沒好、原樣再呼叫一次；"
            "WAITFOR_VERDICT=done＝完成（印尾端與子行程 rc）。\n"
            "真的無法分段（例：單一阻塞下載）才在指令行尾加 `# keepwarm-ok: <原因>`"
            "（無人窗口無效）。\n")
    except Exception:  # noqa: BLE001 — hook 內任何例外一律放行
        return 0, ""


# ───────────────────────────────────────────────────────────── runlong
def done_path(out: Path) -> Path:
    return out.with_name(out.name + ".done")


def _waits_path(out: Path) -> Path:
    return out.with_name(out.name + ".waits")


def _write_done(out: Path, rc: int) -> None:
    ended = datetime.now().astimezone().isoformat(timespec="seconds")
    row = {"schema": SCHEMA, "rc": rc, "ended": ended}
    done_path(out).write_text(json.dumps(row), encoding="utf-8", newline="\n")


def runlong(out: Path, argv: list[str]) -> int:
    """阻塞到子行程結束；stdout／stderr 導進 `out`（UTF-8），**關檔之後**才寫 `<out>.done`（讀者看到
    `.done` 時輸出必已完整）。自身 rc＝子行程 rc（起不來＝127／126）。"""
    for stale in (done_path(out), _waits_path(out)):
        try:
            stale.unlink(missing_ok=True)
        except OSError as exc:
            _warn(f"清不掉舊檔 {stale}（{type(exc).__name__}）⇒ waitfor 可能誤判完成")
    env = {**os.environ}
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    rc = 127
    try:
        with out.open("wb") as sink:
            try:
                proc = subprocess.Popen(  # noqa: S603
                    argv, stdin=subprocess.DEVNULL, stdout=sink, stderr=subprocess.STDOUT, env=env,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except OSError as exc:
                rc = 126 if isinstance(exc, PermissionError) else 127
                sink.write(f"runlong：起不來 {argv[0]!r}（{type(exc).__name__}: {exc}）\n".encode())
            else:
                try:
                    rc = proc.wait()
                except BaseException:  # noqa: BLE001 — 被中斷：收子行程、仍留 .done（rc=130）
                    rc = 130
                    proc.kill()
                    proc.wait()
                    raise
    finally:
        _write_done(out, rc)  # 輸出檔已關閉（with 結束）才寫 .done
    return rc


# ───────────────────────────────────────────────────────────── waitfor
def _read_done(path: Path):
    """`.done` 內容的 rc；不存在／內容不全／結構不符 ⇒ `None`（當未完成，下一輪再讀）。"""
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return row["rc"] if isinstance(row, dict) and type(row.get("rc")) is int else None


def _tail(out: Path) -> str:
    try:
        lines = out.read_bytes().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return "（輸出檔不存在或讀不動）"
    return "\n".join(lines[-TAIL_LINES:])


def _segment(out: Path) -> int:
    """這是第幾段未完成的等待（寫進 `<out>.waits`）；寫不進就當第 1 段（只影響上限提示）。"""
    path = _waits_path(out)
    try:
        seg = int(path.read_text(encoding="utf-8").strip() or "0") + 1
    except (OSError, ValueError):
        seg = 1
    try:
        path.write_text(str(seg), encoding="utf-8", newline="\n")
    except OSError:
        pass
    return seg


def waitfor(done: Path, max_sec: float, *, now_fn=time.monotonic, sleep_fn=time.sleep,
            out=None) -> int:
    out_stream = out or sys.stdout
    sink = done.with_name(done.name[:-len(".done")])
    end = now_fn() + max_sec
    while True:
        rc = _read_done(done)
        if rc is not None:
            print(_tail(sink), file=out_stream)
            print("處置：完成。依上面輸出與子行程 rc 繼續工作（rc≠0＝被等的指令失敗，照實回報）。",
                  file=out_stream)
            print(f"WAITFOR_VERDICT=done rc={rc}", file=out_stream, flush=True)
            return 0
        left = end - now_fn()
        if left <= 0:
            break
        sleep_fn(min(POLL_SEC, left))
    seg = _segment(sink)
    nxt = (f"已 {seg} 段（約 {seg * WAIT_DEFAULT_SEC / 60:g} 分鐘）仍未完成：不再分段——"
           "續分段的累計成本已超過放冷一次重寫。停止輪詢，向主控回報"
           "「該指令跑逾上限仍未完成」並附輸出檔路徑；要續等由主控決定（背景行程仍在跑）。"
           if seg >= N_S_STAR else
           f"尚未完成：原樣再呼叫同一條 waitfor（前景 timeout 設 {WAIT_FG_TIMEOUT_MS:,}）。")
    print(f"處置：{nxt}", file=out_stream)
    print(f"WAITFOR_VERDICT=pending seg={seg}/{N_S_STAR}", file=out_stream, flush=True)
    return 0  # 「還沒好」是正常結果：判決只看末行（DEF-200-622），非 0 留給真錯誤（參數錯＝2）


# ───────────────────────────────────────────────────────────── CLI
def cli_runlong(argv: list[str]) -> int:
    import argparse  # noqa: PLC0415

    ap = argparse.ArgumentParser(prog="sessionctl runlong",
                                 usage="sessionctl runlong --out <檔> -- <argv…>")
    ap.add_argument("--out", required=True, help="stdout／stderr 的落檔；完成後另寫 <檔>.done")
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    args = ap.parse_args(argv)
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    if not cmd:
        print("sessionctl runlong：缺要跑的指令（用法：runlong --out <檔> -- <argv…>）",
              file=sys.stderr)
        return 2
    return runlong(Path(args.out), cmd)


def cli_waitfor(argv: list[str]) -> int:
    import argparse  # noqa: PLC0415

    ap = argparse.ArgumentParser(
        prog="sessionctl waitfor",
        epilog=f"此指令是前景呼叫：呼叫端 timeout 須大於 --max-sec 且 ≤ {LONG_FG_MS:,} ms"
               f"（建議 {WAIT_FG_TIMEOUT_MS:,}），否則被工具砍掉或被長前景閘擋下。")
    ap.add_argument("--done", required=True, help="runlong 的 <檔>.done")
    ap.add_argument("--max-sec", type=float, default=WAIT_DEFAULT_SEC,
                    help=f"最多等幾秒（預設 {WAIT_DEFAULT_SEC:g}、上限 {WAIT_CEIL_SEC:g}）")
    args = ap.parse_args(argv)
    if not args.done.endswith(".done") or not args.max_sec > 0:
        print("sessionctl waitfor：--done 須是 runlong 的 <檔>.done，且 --max-sec 須為正數",
              file=sys.stderr)
        return 2
    max_sec = args.max_sec
    if max_sec > WAIT_CEIL_SEC:
        _warn(f"--max-sec={max_sec:g} 超過上限 {WAIT_CEIL_SEC:g}（只准下修）"
              f"⇒ 夾到 {WAIT_CEIL_SEC:g}")
        max_sec = WAIT_CEIL_SEC
    return waitfor(Path(args.done), max_sec)
