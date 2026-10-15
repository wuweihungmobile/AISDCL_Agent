"""traceId 貫穿 Bridge（契約 v1.2 §3.1.1；NFR-9.4-04、QA O-11）與 BRIDGE_LOG_DIR 滾動日誌（C-16）。

要鎖住的行為（呼叫端是 console-api，驗收是 E2E-13）：
  ① 請求帶 `X-Trace-Id` → 回應回帶同值；缺漏或格式不合 → Bridge 自產 uuid4（SSE、500 也一樣）。
  ② 每一行日誌都有 `trace_id=…`：請求內是該請求的值、沒有請求上下文是 `-`；traceback 也不拆成沒有
     trace_id 的續行；uvicorn 的存取日誌（`POST /autoclaude/runs … 201`）同樣帶。
  ③ run 監督執行緒沿用「啟動它的那個請求」的 trace id（不然引擎出事時的日誌就串不回使用者操作）。
  ④ BRIDGE_LOG_DIR 沒設＝不寫檔；設了＝每日切檔、保留 7 份；寫不進去不得讓 Bridge 起不來。
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import re
import subprocess
import sys
import threading
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest

import app.runner as runner_module
from app.main import create_app
from app.settings import BRIDGE_DIR, Settings
from app.tracing import NO_TRACE, normalize_trace_id, trace_id_var
from tests.conftest import TERMINAL, LiveBridge

_LINE_RE = re.compile(
    r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z [A-Z]+\s+\[[\w.]+\] trace_id=(\S+) ")


def _is_uuid4(value: str) -> bool:
    try:
        return uuid.UUID(value).version == 4 and str(uuid.UUID(value)) == value
    except ValueError:
        return False


def _log_lines(log_dir: Path) -> list[str]:
    return [line for line in (log_dir / "bridge.log").read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _trace_of(line: str) -> str:
    match = _LINE_RE.match(line)
    assert match, f"日誌行不合格式（時間戳／等級／logger／trace_id）：{line!r}"
    return match.group(1)


@pytest.fixture
def logging_settings(settings: Settings, tmp_path: Path) -> Settings:
    return replace(settings, log_dir=tmp_path / "logs")


# ── ① 標頭：回帶、自產、拒收不合格值 ─────────────────────────────────────────────
def test_a_request_trace_id_is_echoed_on_the_response(bridge: LiveBridge) -> None:
    resp = bridge.client.get("/health", headers={"X-Trace-Id": "5f0e8e2a-trace-1"})
    assert resp.status_code == 200
    assert resp.headers["X-Trace-Id"] == "5f0e8e2a-trace-1"


def test_a_missing_trace_id_is_generated_as_a_uuid4(bridge: LiveBridge) -> None:
    first = bridge.client.get("/health").headers["X-Trace-Id"]
    second = bridge.client.get("/health").headers["X-Trace-Id"]
    assert _is_uuid4(first) and _is_uuid4(second)
    assert first != second, "每個沒帶標頭的請求各自一個新值（不是行程內共用同一個）"


@pytest.mark.parametrize("sent", ["has space", "a;b", "x" * 65, "-leading-dash", "_under", "a/b"])
def test_an_unusable_trace_id_is_replaced_never_echoed(bridge: LiveBridge, sent: str) -> None:
    """值會原樣進每一行日誌：空白、控制字元、過長一律不收，否則呼叫端能偽造整行日誌。"""
    got = bridge.client.get("/health", headers={"X-Trace-Id": sent}).headers["X-Trace-Id"]
    assert got != sent and _is_uuid4(got)


# 參數必須是固定值（不可 uuid4()）：xdist 要求各 worker 收集到完全相同的測試 id。
@pytest.mark.parametrize("sent", [
    "a", "A.b_c-1", "0" * 64, "6f1c2d3e-4a5b-4c6d-8e7f-0a1b2c3d4e5f"])
def test_well_formed_trace_ids_are_kept_verbatim(bridge: LiveBridge, sent: str) -> None:
    assert bridge.client.get("/health", headers={"X-Trace-Id": sent}).headers["X-Trace-Id"] == sent


@pytest.mark.parametrize(("raw", "kept"), [
    ("abc", True), ("  abc  ", True), ("a" * 64, True), ("a" * 65, False), ("", False),
    (None, False), ("-a", False), (".a", False), ("a b", False), ("a\nb", False), ("é", False),
])
def test_normalize_trace_id_boundaries(raw: str | None, kept: bool) -> None:
    got = normalize_trace_id(raw)
    if kept:
        assert got == (raw or "").strip()
    else:
        assert _is_uuid4(got)


def test_error_responses_carry_the_header_too(bridge: LiveBridge) -> None:
    missing = bridge.client.get("/autoclaude/runs/no-such-run", headers={"X-Trace-Id": "t-404"})
    assert missing.status_code == 404 and missing.headers["X-Trace-Id"] == "t-404"
    invalid = bridge.client.get("/autoclaude/runs/x/events", params={"after": -1},
                                headers={"X-Trace-Id": "t-422"})
    assert invalid.status_code == 422 and invalid.headers["X-Trace-Id"] == "t-422"


def test_the_sse_stream_response_carries_the_header(bridge: LiveBridge, run_body) -> None:
    """事件串流是 StreamingResponse：標頭在 response.start 就要加上，串流也不能被中介層緩衝。"""
    rid = bridge.post_run(run_body(delay="0.2")).json()["run_id"]
    bridge.wait_status(rid, {"COMPLETED"})
    with httpx.stream("GET", f"{bridge.base_url}/autoclaude/runs/{rid}/stream",
                      headers={"X-Trace-Id": "t-sse-1"}) as resp:
        assert resp.headers["x-trace-id"] == "t-sse-1"
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert next(resp.iter_lines()) == "retry: 3000"


def test_an_unhandled_500_still_carries_the_header(settings: Settings) -> None:
    """500 是 ServerErrorMiddleware 送的：traceId 中介層必須包在它外面才管得到（BridgeApp）。"""
    app = create_app(settings)

    @app.get("/_boom")
    def boom() -> None:
        raise ZeroDivisionError("boom")

    live = LiveBridge(app, settings).start()
    try:
        with httpx.Client(base_url=live.base_url, timeout=30) as one_shot:     # 500 後連線會被關掉
            resp = one_shot.get("/_boom", headers={"X-Trace-Id": "t-500"})
        assert resp.status_code == 500
        assert resp.headers["X-Trace-Id"] == "t-500"
    finally:
        live.stop()


# ── ② 每一行日誌都有 trace_id ─────────────────────────────────────────────────────
def test_every_log_line_carries_the_trace_id_and_none_is_split_by_a_traceback(
        logging_settings: Settings) -> None:
    app = create_app(logging_settings)
    log = logging.getLogger("bridge.test")

    @app.get("/_log")
    def emit() -> dict[str, str]:
        assert trace_id_var.get() != NO_TRACE            # 同步路由跑在執行緒池，context 被複製進來
        log.warning("hello from a request")
        try:
            raise ZeroDivisionError("kaboom")
        except ZeroDivisionError:
            log.exception("multi\nline failure")
        return {"seen": trace_id_var.get()}

    live = LiveBridge(app, logging_settings).start()
    try:
        mine = live.client.get("/_log", headers={"X-Trace-Id": "t-log-1"})
        theirs = live.client.get("/_log")                 # 沒帶標頭：Bridge 自產
        worker = threading.Thread(
            target=lambda: log.warning("no request here"), name="no-request-context")
        worker.start()
        worker.join()
        assert mine.json() == {"seen": "t-log-1"}
        generated = theirs.json()["seen"]
        assert _is_uuid4(generated) and generated == theirs.headers["X-Trace-Id"]
    finally:
        live.stop()

    lines = _log_lines(logging_settings.log_dir)
    assert lines, "BRIDGE_LOG_DIR 有值，bridge.log 必須有內容"
    assert all("trace_id=" in line for line in lines), f"有行沒有 trace_id：{lines}"
    for line in lines:
        _trace_of(line)                    # 時間戳為 UTC＋Z、等級、logger 名、trace_id 欄位都對

    hello = [line for line in lines if "hello from a request" in line]
    assert [_trace_of(line) for line in hello] == ["t-log-1", generated]
    boom = [line for line in lines if "multi\\nline failure" in line]
    assert len(boom) == 2 and all(
        "Traceback" in line and "ZeroDivisionError: kaboom" in line for line in boom), (
        "traceback 的換行要寫成字面 \\n，同一筆日誌恆為一行")
    assert [_trace_of(line) for line in boom] == ["t-log-1", generated]
    background = [line for line in lines if "no request here" in line]
    assert [_trace_of(line) for line in background] == [NO_TRACE], "沒有請求上下文的行是 `-`"


def test_uvicorn_access_lines_carry_the_trace_id_of_their_request(
        logging_settings: Settings, run_body) -> None:
    """E2E-13 的「POST /autoclaude/runs 那一行」：uvicorn 的存取日誌也要走同一套格式與 trace_id。"""
    live = LiveBridge(create_app(logging_settings), logging_settings, log_level="info").start()
    try:
        resp = live.client.post("/autoclaude/runs", json=run_body(delay="0.2"),
                                headers={"X-Trace-Id": "t-access-1"})
        assert resp.status_code == 201
        live.wait_status(resp.json()["run_id"], {"COMPLETED"})
    finally:
        live.stop()

    access = [line for line in _log_lines(logging_settings.log_dir)
              if '"POST /autoclaude/runs HTTP/1.1" 201' in line]
    assert len(access) == 1, access
    assert "[uvicorn.access]" in access[0]
    assert _trace_of(access[0]) == "t-access-1"


def test_import_time_warnings_from_autoclaude_also_carry_a_trace_id() -> None:
    """AutoClaude 匯入時就會用 logger 印警告（沒裝 keyboard／wexpect）。app.main 必須先裝好日誌格式
    再匯入它，否則 docker logs 的前幾行會是沒有 trace_id 的裸訊息。以子行程重現（強制那兩個套件
    匯入失敗，與機器上實際有沒有裝無關）。"""
    code = ("import sys; sys.modules['keyboard'] = None; sys.modules['wexpect'] = None; "
            "import app.main")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("BRIDGE_", "AUTOSDD_", "AUTOCLAUDE_"))}
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    proc = subprocess.run([sys.executable, "-c", code], cwd=BRIDGE_DIR, env=env,
                          capture_output=True, encoding="utf-8", errors="replace",
                          timeout=120, check=False)
    assert proc.returncode == 0, proc.stderr
    lines = [line for line in proc.stderr.splitlines() if line.strip()]
    assert any("keyboard 未安裝" in line for line in lines), proc.stderr
    assert any("wexpect 未安裝" in line for line in lines), proc.stderr
    assert all("trace_id=-" in line for line in lines), f"有裸訊息（沒有 trace_id）：{lines}"


# ── ③ 監督執行緒沿用起始請求的 trace id ─────────────────────────────────────────
def test_the_run_supervisor_keeps_the_trace_id_of_the_request_that_started_it(
        logging_settings: Settings, run_body, monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(self: Any, parsed: Any) -> None:
        raise RuntimeError("dispatch boom")

    monkeypatch.setattr(runner_module.RunHandle, "_dispatch", explode)
    live = LiveBridge(create_app(logging_settings), logging_settings).start()
    try:
        resp = live.client.post("/autoclaude/runs", json=run_body(delay="0.2"),
                                headers={"X-Trace-Id": "t-run-1"})
        assert resp.status_code == 201
        live.wait_status(resp.json()["run_id"], TERMINAL)
    finally:
        live.stop()

    failures = [line for line in _log_lines(logging_settings.log_dir)
                if "處理引擎輸出行失敗" in line]
    assert failures, "監督執行緒內 _dispatch 例外必須被記成日誌"
    assert {_trace_of(line) for line in failures} == {"t-run-1"}
    assert all("[bridge.runner]" in line for line in failures)


# ── ④ BRIDGE_LOG_DIR ─────────────────────────────────────────────────────────────
def _bridge_file_handlers() -> list[logging.Handler]:
    """本模組裝的檔案 handler（pytest 也會在 root 掛一個指向 os.devnull 的 FileHandler，不算）。"""
    return [h for h in logging.getLogger().handlers
            if getattr(h, "_bridge_log_handler", False) and isinstance(h, logging.FileHandler)]


def test_without_a_log_dir_nothing_is_written_to_disk(bridge: LiveBridge, tmp_path: Path) -> None:
    assert bridge.client.get("/health").status_code == 200
    assert _bridge_file_handlers() == []
    assert list(tmp_path.rglob("bridge.log")) == []


def test_the_rolling_file_policy_is_daily_in_utc_and_keeps_seven(
        make_bridge, logging_settings: Settings) -> None:
    make_bridge(logging_settings)
    handlers = [h for h in logging.getLogger().handlers
                if isinstance(h, logging.handlers.TimedRotatingFileHandler)]
    assert len(handlers) == 1
    handler = handlers[0]
    assert handler.baseFilename == str((logging_settings.log_dir / "bridge.log").resolve())
    assert (handler.when, handler.utc, handler.backupCount) == ("MIDNIGHT", True, 7)
    assert handler.encoding == "utf-8"


def test_a_log_dir_that_cannot_be_created_does_not_stop_the_bridge(
        settings: Settings, tmp_path: Path, make_bridge,
        capsys: pytest.CaptureFixture[str]) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("我是檔案，不是目錄", encoding="utf-8")
    live = make_bridge(replace(settings, log_dir=blocker / "logs"))
    assert live.client.get("/health").status_code == 200, "日誌檔不是服務可用性的前提"
    err = capsys.readouterr().err
    assert "BRIDGE_LOG_DIR" in err and "沒有檔案日誌" in err
    assert "trace_id=-" in err, "連這則警告也要走同一套格式"
    assert _bridge_file_handlers() == []


def test_setup_is_idempotent_across_restarts(make_bridge, logging_settings: Settings) -> None:
    """每次 lifespan 啟動都重裝一套；兩個實例先後起來也不會讓日誌被寫兩次。"""
    make_bridge(logging_settings)
    make_bridge(logging_settings)
    installed = [h for h in logging.getLogger().handlers
                 if getattr(h, "_bridge_log_handler", False)]
    assert len(installed) == 2, "一個 stderr＋一個檔案 handler，不是各兩個"
