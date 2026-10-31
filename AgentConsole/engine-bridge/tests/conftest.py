"""共用夾具：隔離環境、活的 Bridge（uvicorn 執行緒＋真 HTTP）、mock claude 與 playbook 工廠。

為什麼用真的 uvicorn 而不是 TestClient：SSE 是長連線；Starlette 的 TestClient／httpx 的
ASGITransport 會等整個回應結束才回傳，無法測「讀到一半斷線、帶游標重連」。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import time
import uuid
import zlib
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest
import uvicorn

from app.logsetup import teardown_logging
from app.main import create_app
from app.settings import Settings, load_settings
from tests.fake_sdd import make_fake_sdd
from tests.sdd_run_support import TOKEN as SDD_TOKEN
from tests.sdd_run_support import make_project
from tests.timing import STALL_TIMEOUT, WAIT_CAP

TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}


def find_mock_claude() -> str:
    """安裝在目前 venv 的 console script（POSIX＝bin/、Windows＝Scripts\\*.exe）。"""
    found = shutil.which("aisdlc-mock-claude", path=str(Path(sys.executable).parent))
    assert found, "找不到 aisdlc-mock-claude：先在 engine-bridge 執行 `uv pip install -e .`"
    return found


@pytest.fixture(scope="session")
def mock_claude_cmd() -> str:
    return find_mock_claude()


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """開發者本機的 AUTOSDD_／AUTOCLAUDE_／MINIMAX_ 變數不得滲進引擎（否則結果因人而異）。
    額度快取指向空目錄：引擎讀不到就走『量不到』保守路徑，不會因開發者帳號的真實用量而 halt。"""
    for name in list(os.environ):
        if name.startswith(("AUTOSDD_", "AUTOCLAUDE_", "MINIMAX_", "MOCK_CLAUDE_", "BRIDGE_")):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CLAUDECODE", raising=False)
    quota = tmp_path / "quota-cache"
    quota.mkdir()
    monkeypatch.setenv("AUTOSDD_QUOTA_CACHE_DIR", str(quota))


@pytest.fixture(autouse=True)
def clean_logging() -> Iterator[None]:
    """Bridge 的 lifespan 啟動時會裝日誌 handler（可能含 BRIDGE_LOG_DIR 的檔案 handler）；
    每個測試結束後拆掉，免得跨測試殘留，也免得 Windows 上仍開著的 bridge.log 擋住 tmp 目錄清理。
    autouse 夾具最先建立、最後拆除，所以拆除時各個 LiveBridge 都已停止。"""
    yield
    teardown_logging()


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    path = tmp_path / "projects" / "demo"
    path.mkdir(parents=True)
    return path


@pytest.fixture
def settings(tmp_path: Path, project_dir: Path) -> Settings:
    workspace = tmp_path / "workspace"
    return load_settings({
        "ENGINE_WORKSPACE": str(workspace),
        "BRIDGE_ALLOWED_PATH_ROOTS": os.pathsep.join([str(workspace), str(tmp_path / "projects")]),
        "BRIDGE_STOP_GRACE_SECONDS": "3",
        "BRIDGE_INSTANCE": "test-bridge",
    })


class LiveBridge:
    """跑在背景執行緒的真 uvicorn；`client` 是指向它的 httpx.Client。"""

    def __init__(self, app: Any, settings: Settings, *, log_level: str = "warning"):
        self.app = app
        self.settings = settings
        config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level=log_level,
                                timeout_graceful_shutdown=2)
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True, name="test-bridge")
        self.client: httpx.Client | None = None
        self.base_url = ""

    def start(self) -> LiveBridge:
        self.thread.start()
        deadline = time.monotonic() + 20
        while not self.server.started:
            assert time.monotonic() < deadline, "uvicorn 20 秒內沒有起來"
            assert self.thread.is_alive(), "uvicorn 執行緒提前結束"
            time.sleep(0.02)
        port = self.server.servers[0].sockets[0].getsockname()[1]
        self.base_url = f"http://127.0.0.1:{port}"
        self.client = httpx.Client(base_url=self.base_url, timeout=30)
        return self

    def stop(self) -> None:
        if self.client is not None:
            self.client.close()
        self.server.should_exit = True
        self.thread.join(timeout=30)

    # ── 便利方法 ─────────────────────────────────────────────────────────────
    def post_run(self, body: dict[str, Any]) -> httpx.Response:
        assert self.client is not None
        return self.client.post("/autoclaude/runs", json=body)

    def post_on_fresh_connection(self, path: str, **kwargs: Any) -> httpx.Response:
        """用一次性的連線送出請求。會讓伺服器拋出「未處理例外」的請求（回 500）之後，
        uvicorn 會把那條連線關掉；共用的長連線若被拿去打下一個請求，就會撞上剛被關掉的
        連線（Windows 上是 WinError 10053）。"""
        with httpx.Client(base_url=self.base_url, timeout=30) as one_shot:
            return one_shot.post(path, **kwargs)

    def get_run(self, run_id: str) -> dict[str, Any]:
        assert self.client is not None
        resp = self.client.get(f"/autoclaude/runs/{run_id}")
        assert resp.status_code == 200, resp.text
        return resp.json()

    def wait_status(self, run_id: str, statuses: set[str], timeout: float = STALL_TIMEOUT,
                    cap: float = WAIT_CAP) -> dict[str, Any]:
        """等 run 進入 `statuses` 之一。`timeout` 是**停滯**上限（status 與事件序號都沒動的秒
        數），不是牆鐘：引擎行程樹的啟動成本隨機器負載膨脹 10～30 倍（數字見 tests/timing.py），
        固定牆鐘在超載時只會把「慢」誤判成「壞」。`cap` 是總上限，擋活鎖。
        已經是**別的**終態（想等 COMPLETED 卻 FAILED）就立刻失敗並帶出原因，不再空等到逾時。"""
        began = moved_at = time.monotonic()
        mark: tuple[Any, Any] | None = None
        while True:
            last = self.get_run(run_id)
            if last["status"] in statuses:
                return last
            if last["status"] in TERMINAL:
                raise AssertionError(
                    f"run 結束 {last['status']}（想等 {sorted(statuses)}）：{last.get('reason')}；"
                    f"最後狀態：{last}")
            now = time.monotonic()
            if (last["status"], last["last_event_seq"]) != mark:
                mark, moved_at = (last["status"], last["last_event_seq"]), now
            if now - moved_at > timeout or now - began > cap:
                raise AssertionError(
                    f"停滯 {now - moved_at:g}s（總計 {now - began:g}s）仍沒有到達 "
                    f"{sorted(statuses)}；最後狀態：{last}")
            time.sleep(0.05)

    def events(self, run_id: str, after: int = 0) -> list[dict[str, Any]]:
        assert self.client is not None
        resp = self.client.get(f"/autoclaude/runs/{run_id}/events",
                               params={"after": after, "limit": 5000})
        assert resp.status_code == 200, resp.text
        return resp.json()

    def sse(self, run_id: str, *, after: int | None = None, last_event_id: int | None = None,
            stop_after: int | None = None) -> list[dict[str, Any]]:
        """讀 SSE；`stop_after`＝收到這麼多則事件後主動斷線。回傳 [{id,event,data}]。"""
        headers = {"Last-Event-ID": str(last_event_id)} if last_event_id is not None else {}
        params = {"after": after} if after is not None else {}
        out: list[dict[str, Any]] = []
        cur: dict[str, Any] = {}
        with httpx.stream("GET", f"{self.base_url}/autoclaude/runs/{run_id}/stream",
                          params=params, headers=headers, timeout=STALL_TIMEOUT) as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            for line in resp.iter_lines():
                if line.startswith("id:"):
                    cur["id"] = int(line[3:].strip())
                elif line.startswith("event:"):
                    cur["event"] = line[6:].strip()
                elif line.startswith("data:"):
                    cur["data"] = json.loads(line[5:].strip())
                elif line == "" and cur:
                    out.append(cur)
                    cur = {}
                    if stop_after is not None and len(out) >= stop_after:
                        break
        return out


@pytest.fixture
def make_bridge(settings: Settings) -> Iterator[Callable[..., LiveBridge]]:
    started: list[LiveBridge] = []

    def factory(custom: Settings | None = None, **app_kwargs: Any) -> LiveBridge:
        cfg = custom or settings
        live = LiveBridge(create_app(cfg, **app_kwargs), cfg).start()
        started.append(live)
        return live

    yield factory
    for live in reversed(started):
        live.stop()


@pytest.fixture
def bridge(make_bridge: Callable[..., LiveBridge]) -> LiveBridge:
    return make_bridge()


def mock_playbook(project: str = "MockDemo", *, retries: int = 1) -> dict[str, Any]:
    """對應 AutoClaude 的 mock_playbook.yaml 三步劇本（含 command 欄位、global_goal）。"""
    return {
        "version": "1.0", "project": project, "global_goal": "Bridge E2E：三步 mock 劇本",
        "global_invariants": {"max_retries_per_step": retries, "auto_compact_interval": 0},
        "tasks": [
            {"step_id": "T01", "name": "初始化確認 (INIT_DONE)", "command": "step1",
             "prompt": "請執行初始化步驟並確認完成，完成後輸出 [INIT_DONE]",
             "expected_output_regex": "\\[INIT_DONE\\]"},
            {"step_id": "T02", "name": "測試建立確認 (TEST_CREATED)", "command": "step2",
             "prompt": "請建立測試案例並確認完成，完成後輸出 [TEST_CREATED]",
             "expected_output_regex": "\\[TEST_CREATED\\]"},
            {"step_id": "T03", "name": "Ping 測試 (PONG)", "command": "ping",
             "prompt": "請執行 ping 測試，完成後輸出 [PONG]",
             "expected_output_regex": "\\[PONG\\]"},
        ],
    }


@pytest.fixture
def run_body(project_dir: Path, mock_claude_cmd: str) -> Callable[..., dict[str, Any]]:
    def build(*, delay: str = "0.3", playbook: dict[str, Any] | None = None,
              trace: Path | None = None, env: dict[str, str] | None = None,
              overrides: dict[str, Any] | None = None, execution_path: Path | None = None,
              project: str = "mock-proj", run_id: str | None = None) -> dict[str, Any]:
        merged_env = {"MOCK_CLAUDE_DELAY": delay, **(env or {})}
        if trace is not None:
            merged_env["MOCK_CLAUDE_TRACE"] = str(trace)
        config = {"claude": {"command": mock_claude_cmd}, "playbook": {"step_timeout_seconds": 30},
                  "token_guard": {"auto_resume": False}}
        config.update(overrides or {})
        return {"run_id": run_id or str(uuid.uuid4()), "project": project,
                "execution_path": str(execution_path or project_dir),
                "playbook": playbook or mock_playbook(), "config_overrides": config,
                "env": merged_env, "fresh": False}

    return build


# ── SDD 批次（ADR-XPLAT-016）：假 SDD 樹、專案根、帶寫入權杖的 Bridge ────────────────────
@pytest.fixture
def sdd_fake(tmp_path: Path) -> Path:
    """暫存目錄內的假 SDD 版本目錄（只回放 ADR §4 契約的假 FSMRuntime CLI；見
    tests/fake_sdd.py）。"""
    return make_fake_sdd(tmp_path / "sdd")


@pytest.fixture
def sdd_proj(tmp_path: Path) -> Path:
    """專案根（allowed roots 之下）：`docs/03_testing/contracts/` 放一份 TCS；FSM 狀態由各測試自己
    seed。"""
    return make_project(tmp_path / "projects")


@pytest.fixture
def sdd_live(make_bridge: Callable[..., Any], settings: Settings, sdd_fake: Path) -> Any:
    """SDD 寫入面啟用的 Bridge：`sdd_root` 指向假 SDD 樹、設了寫入權杖
    （`tests.sdd_run_support.TOKEN`）。"""
    return make_bridge(replace(settings, sdd_root=sdd_fake, sdd_write_token=SDD_TOKEN))


def read_trace(path: Path) -> list[dict[str, Any]]:
    """mock claude 的呼叫紀錄（只含 `-p` 呼叫；`--version` 探測不記）。"""
    if not path.is_file():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


# ── 假 PG（只模擬 AdvisoryLock 用到的那一小塊語意）──────────────────────────────────
# 鎖的 bug 只在 DB 模式現形，而沒設 BRIDGE_TEST_DSN 時整組真 PG 測試都會跳過——預設的 `pytest -q`
# 因此看不見它們。有了這個替身，同一條邏輯在沒有 PG 的環境也受守（真 PG 版見 test_db_integration）。
class FakeConn:
    def __init__(self, pg: FakePg) -> None:
        self._pg = pg
        self.closed = False
        self._row: tuple[Any, ...] = ()

    def execute(self, query: str, params: tuple[str, ...]) -> FakeConn:
        key = params[0]
        if "pg_try_advisory_lock" in query:
            owner = self._pg.owners.setdefault(key, self)
            self._row = (owner is self, zlib.crc32(key.encode("utf-8")) & 0x7FFFFFFF)
        elif "pg_advisory_unlock" in query:
            if self._pg.owners.get(key) is self:
                del self._pg.owners[key]
            self._row = (True,)
        return self

    def fetchone(self) -> tuple[Any, ...]:
        return self._row

    def close(self) -> None:
        self.closed = True
        for key in [k for k, owner in self._pg.owners.items() if owner is self]:
            del self._pg.owners[key]


class FakePg:
    """session 級 advisory lock 屬於「連線」：同一條連線重取一定成功；別條連線在持有者還活著時
    取不到（回 False）；連線關閉即釋放。`down=True`＝連不上（psycopg.OperationalError）。"""

    def __init__(self) -> None:
        self.owners: dict[str, FakeConn] = {}
        self.connections: list[FakeConn] = []
        self.down = False

    def connect(self, dsn: str, **kwargs: Any) -> FakeConn:
        if self.down:
            raise psycopg.OperationalError("fake：連不上")
        conn = FakeConn(self)
        self.connections.append(conn)
        return conn

    def live_connections(self) -> int:
        return sum(1 for conn in self.connections if not conn.closed)


@pytest.fixture
def fake_pg(monkeypatch: pytest.MonkeyPatch) -> FakePg:
    pg = FakePg()
    monkeypatch.setattr(psycopg, "connect", pg.connect)
    return pg
