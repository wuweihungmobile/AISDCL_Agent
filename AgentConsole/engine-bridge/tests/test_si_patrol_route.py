"""`GET /si/patrol`（巡邏快照唯讀讀取）的測試（TCS-SiFlowVisibility-20261111：AT-966-1-1～1-7、
1-E-1、1-E-2；唯讀鎖的普查 AT-966-1-8 在 test_si_readonly_lock.py）。

快照目錄 `RD` 是暫存目錄（絕不碰真 SI 家目錄）；路由對真 uvicorn 跑真 HTTP。斷言重點：只讀、驗形狀
與大小、四個原因碼各自成立、讀端永遠讀到完整檔。黃金樣本（根層 `tools/tests/fixtures/selfimproving/
p7/patrol.golden.json`）由主控複製到 `tests/fixtures/si_report/`。AT 內不引用其他 AT 的 ID。
"""
from __future__ import annotations

import builtins
import json
import os
import subprocess
import threading
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from app import si_report
from app.settings import Settings
from app.si_report import PATROL_REPORT_MAX_BYTES, resolve_report_path
from tests import si_repo_support as sup
from tests.fake_si import patrol_report

ROOT_GOLDEN = (sup.MONOREPO / "tools" / "tests" / "fixtures" / "selfimproving" / "p7"
               / "patrol.golden.json")
LOCAL_GOLDEN = Path(__file__).resolve().parent / "fixtures" / "si_report" / "patrol.golden.json"
CAUSES = ("report_dir_unset", "report_missing", "report_unreadable", "report_invalid")


def write_report(report_dir: Path, report: dict[str, Any] | None = None) -> Path:
    """依 AT 規格把快照以 `json.dumps(ensure_ascii=False)` 寫成 `patrol.json`（LF、UTF-8）。"""
    target = report_dir / "patrol.json"
    text = json.dumps(patrol_report() if report is None else report, ensure_ascii=False)
    target.write_bytes(text.encode("utf-8"))
    return target


@pytest.fixture
def rd(tmp_path: Path) -> Path:
    path = tmp_path / "console_report"
    path.mkdir()
    return path


def live_with(make_bridge: Any, settings: Settings, report_dir: Path | None) -> Any:
    return make_bridge(replace(settings, si_report_dir=report_dir))


class OpenSpy:
    """取代 `app.si_report.open`（模組全域遮蔽內建）：記錄每次開檔的模式與實際讀入位元組數。"""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.read_bytes = 0

    def __call__(self, path: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        self.calls.append(mode)
        spy = self
        handle = builtins.open(path, mode, *args, **kwargs)

        class Wrapped:
            def __enter__(self) -> Wrapped:
                return self

            def __exit__(self, *exc: Any) -> None:
                handle.close()

            def read(self, size: int = -1) -> bytes:
                data = handle.read(size)
                spy.read_bytes += len(data)
                return data

        return Wrapped()


# ── AT-966-1-1：成功回應形狀、逐值透傳與黃金樣本 ────────────────────────────────────────────
@pytest.mark.parametrize("source", ["synthetic", "golden"])
def test_AT_966_1_1_success_shape_and_value_for_value_passthrough(
        source: str, rd: Path, settings: Settings, make_bridge: Any) -> None:
    if source == "golden":
        assert LOCAL_GOLDEN.read_bytes() == ROOT_GOLDEN.read_bytes(), \
            "複本與根層黃金樣本必須逐位元組相等（任一方改動即紅）"
        target = rd / "patrol.json"
        target.write_bytes(LOCAL_GOLDEN.read_bytes())
    else:
        target = write_report(rd, patrol_report(note="中文備註：巡邏心跳正常"))
    expected = json.loads(target.read_bytes().decode("utf-8"))
    live = live_with(make_bridge, settings, rd)
    resp = live.client.get("/si/patrol")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].split(";")[0] == "application/json"
    body = resp.json()
    assert list(body) == ["schema_rev", "kind", "read_at", "report"]
    assert body["schema_rev"] == 1 and type(body["schema_rev"]) is int
    assert body["kind"] == "patrol"
    stamp = datetime.fromisoformat(body["read_at"])
    assert stamp.tzinfo is not None and stamp.utcoffset() is not None, "read_at 必須帶 offset"
    assert body["report"] == expected, "report 逐值等於檔案解析結果"
    assert list(body["report"]) == list(expected), "report 鍵序同檔"
    if source == "synthetic":
        assert list(expected).index("generated_at") > list(expected).index("schema_rev")
        assert "中文備註：巡邏心跳正常".encode() in resp.content, "非 ASCII 不得被跳脫"
    assert b"\\u" not in resp.content, "回應原始位元組不得含 \\u 跳脫"


# ── AT-966-1-2：目錄未設、缺檔、不可讀三種原因碼 ────────────────────────────────────────────
def assert_503(resp: Any, cause: str) -> None:
    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert body["code"] == 503 and body["reason"] == "si_unavailable", body
    assert body["cause"] == cause, body
    assert "report" not in body


def test_AT_966_1_2_unset_missing_and_unreadable_have_three_distinct_causes(
        tmp_path: Path, rd: Path, settings: Settings, make_bridge: Any,
        monkeypatch: pytest.MonkeyPatch) -> None:
    # (a) 未設：零檔案系統存取（open、路徑判準、os.stat 對 patrol 路徑的呼叫次數皆為 0）
    opened = OpenSpy()
    resolved: list[Path] = []
    stat_args: list[str] = []
    real_stat = os.stat

    def stat_spy(path: Any, *args: Any, **kwargs: Any) -> Any:
        stat_args.append(str(path))
        return real_stat(path, *args, **kwargs)

    live = live_with(make_bridge, settings, None)
    with monkeypatch.context() as scoped:
        scoped.setattr(si_report, "open", opened, raising=False)
        scoped.setattr(si_report, "resolve_report_path",
                       lambda *a, **k: resolved.append(a) or (None, "不該被呼叫"))
        scoped.setattr(os, "stat", stat_spy)
        resp_a = live.client.get("/si/patrol")
    assert_503(resp_a, "report_dir_unset")
    assert opened.calls == [] and resolved == [], "未設時不得有任何檔案系統存取"
    assert not [s for s in stat_args if "patrol" in s], stat_args
    # (b) 目錄存在但無 patrol.json
    assert_503(live_with(make_bridge, settings, rd).client.get("/si/patrol"), "report_missing")
    # (c) patrol.json 是一個目錄（跨平台可造的不可讀）
    (rd / "patrol.json").mkdir()
    assert_503(live_with(make_bridge, settings, rd).client.get("/si/patrol"), "report_unreadable")
    # 目錄本身不存在也是缺檔（不是不可讀）
    gone = tmp_path / "never-created"
    assert_503(live_with(make_bridge, settings, gone).client.get("/si/patrol"), "report_missing")


# ── AT-966-1-3：壞檔十三個子情境皆 report_invalid ───────────────────────────────────────────
GOOD_STAMP = "2026-11-11T14:00:00+08:00"
BAD_FILES: dict[str, bytes] = {
    "empty-file": b"",
    "not-json-text": b"this is not json",
    "json-array": b"[]",
    "json-scalar": b"1",
    "utf8-bom-prefixed": b"\xef\xbb\xbf" + json.dumps(
        {"schema_rev": 1, "generated_at": GOOD_STAMP}).encode("utf-8"),
    "non-utf8-bytes": b"\xff\xfe{}",
    "empty-object": b"{}",
    "schema-rev-2": json.dumps({"schema_rev": 2, "generated_at": GOOD_STAMP}).encode("utf-8"),
    "schema-rev-string": json.dumps(
        {"schema_rev": "1", "generated_at": GOOD_STAMP}).encode("utf-8"),
    "schema-rev-bool": json.dumps({"schema_rev": True, "generated_at": GOOD_STAMP}).encode("utf-8"),
    "missing-generated-at": json.dumps({"schema_rev": 1}).encode("utf-8"),
    "generated-at-without-offset": json.dumps(
        {"schema_rev": 1, "generated_at": "2026-11-11T14:00:00"}).encode("utf-8"),
    "generated-at-not-a-date": json.dumps(
        {"schema_rev": 1, "generated_at": "not a date"}).encode("utf-8"),
}


def test_AT_966_1_3_thirteen_broken_files_are_all_report_invalid(
        rd: Path, settings: Settings, make_bridge: Any) -> None:
    assert len(BAD_FILES) == 13
    live = live_with(make_bridge, settings, rd)
    for name, raw in BAD_FILES.items():
        (rd / "patrol.json").write_bytes(raw)
        resp = live.client.get("/si/patrol")
        assert resp.status_code == 503, f"{name}：{resp.status_code} {resp.text}"
        body = resp.json()
        assert body["reason"] == "si_unavailable" and body["cause"] == "report_invalid", \
            f"{name}：{body}"
        assert "report" not in body, f"{name}：不得回傳部分內容"
    # 對照組：Bridge 只要求兩個鍵，其餘鍵缺席仍是 200
    minimal = {"schema_rev": 1, "generated_at": GOOD_STAMP}
    (rd / "patrol.json").write_bytes(json.dumps(minimal).encode("utf-8"))
    resp = live.client.get("/si/patrol")
    assert resp.status_code == 200 and resp.json()["report"] == minimal, resp.text
    # NaN 不是合法 JSON，也不得讓回應序列化失敗成 500
    (rd / "patrol.json").write_bytes(
        b'{"schema_rev": 1, "generated_at": "' + GOOD_STAMP.encode() + b'", "x": NaN}')
    assert_503(live.client.get("/si/patrol"), "report_invalid")


# ── AT-966-1-4：大小邊界 ────────────────────────────────────────────────────────────────────
def padded_to(size: int) -> bytes:
    head = b'{"schema_rev":1,"generated_at":"' + GOOD_STAMP.encode() + b'","pad":"'
    tail = b'"}'
    raw = head + b"x" * (size - len(head) - len(tail)) + tail
    assert len(raw) == size
    return raw


def test_AT_966_1_4_size_boundary_at_one_mebibyte(
        rd: Path, settings: Settings, make_bridge: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    assert PATROL_REPORT_MAX_BYTES == 1048576, "常數唯一定義處的值不得被悄悄改動"
    live = live_with(make_bridge, settings, rd)
    for size, status in ((PATROL_REPORT_MAX_BYTES, 200), (PATROL_REPORT_MAX_BYTES + 1, 503)):
        (rd / "patrol.json").write_bytes(padded_to(size))
        spy = OpenSpy()
        with monkeypatch.context() as scoped:
            scoped.setattr(si_report, "open", spy, raising=False)
            resp = live.client.get("/si/patrol")
        assert resp.status_code == status, f"{size} 位元組：{resp.status_code}"
        if status == 503:
            assert resp.json()["cause"] == "report_invalid"
        assert spy.read_bytes <= PATROL_REPORT_MAX_BYTES + 1, \
            f"{size} 位元組：實際讀入 {spy.read_bytes}，不得超過上限加一"


# ── AT-966-1-5：任何查詢參數 422 ────────────────────────────────────────────────────────────
def test_AT_966_1_5_any_query_parameter_is_422(
        rd: Path, settings: Settings, make_bridge: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    write_report(rd)
    live = live_with(make_bridge, settings, rd)
    spy = OpenSpy()
    with monkeypatch.context() as scoped:
        scoped.setattr(si_report, "open", spy, raising=False)
        for query in ("x=1", "since=1", "limit=1", "read_at=x"):
            resp = live.client.get(f"/si/patrol?{query}")
            field = query.split("=")[0]
            assert resp.status_code == 422, f"{query}：{resp.status_code}"
            body = resp.json()
            assert body["reason"] == "invalid_request", body
            assert body["violations"] == [{"field": field, "rule": "unknown_parameter",
                                           "message": f"不收查詢參數 {field!r}"}], body
        resp = live.client.get("/si/patrol?x=1&y=2")
        assert [v["field"] for v in resp.json()["violations"]] == ["x", "y"], "每個未知參數一筆"
    assert spy.calls == [], "被擋下的請求零檔案系統存取"


# ── AT-966-1-6：零寫入、零子行程、目錄不變 ──────────────────────────────────────────────────
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND


def snapshot_dir(path: Path) -> dict[str, tuple[bytes, int]]:
    return {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in sorted(path.iterdir())}


def test_AT_966_1_6_zero_writes_zero_subprocesses_and_directory_unchanged(
        rd: Path, settings: Settings, make_bridge: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    write_report(rd)
    (rd / "unrelated.txt").write_bytes(b"unrelated")
    live = live_with(make_bridge, settings, rd)
    before = snapshot_dir(rd)
    popen_calls: list[Any] = []
    write_opens: list[int] = []
    real_os_open = os.open
    spy = OpenSpy()

    def popen_spy(*args: Any, **kwargs: Any) -> Any:
        popen_calls.append(args)
        raise AssertionError("讀快照不得啟動子行程")

    def os_open_spy(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if flags & WRITE_FLAGS:
            write_opens.append(flags)
        return real_os_open(path, flags, *args, **kwargs)

    reports = []
    with monkeypatch.context() as scoped:
        scoped.setattr(subprocess, "Popen", popen_spy)
        scoped.setattr(os, "open", os_open_spy)
        scoped.setattr(si_report, "open", spy, raising=False)
        for _ in range(20):
            resp = live.client.get("/si/patrol")
            assert resp.status_code == 200, resp.text
            reports.append(resp.json()["report"])
    assert popen_calls == [] and write_opens == []
    assert all(mode == "rb" for mode in spy.calls) and len(spy.calls) == 20
    assert snapshot_dir(rd) == before, "目錄清單、位元組與 mtime 全不變"
    assert all(r == reports[0] for r in reports), "二十次回應的 report 皆相同"


# ── AT-966-1-7：路徑含於目錄（逃逸判準純函式）──────────────────────────────────────────────
def test_AT_966_1_7_report_path_must_be_contained_in_the_directory(tmp_path: Path) -> None:
    base = tmp_path / "si-report"
    inside = base / "patrol.json"
    outside = tmp_path / "elsewhere" / "patrol.json"
    evil_sibling = tmp_path / "si-report-evil" / "patrol.json"
    dotdot = base / ".." / "other" / "patrol.json"

    def resolver_for(answer: Path) -> Any:
        return lambda p: p if p == base else answer

    cases = {
        "inside": (inside, True), "symlink-escape-outside": (outside, False),
        "the-directory-itself": (base, False), "dot-dot": (dotdot, False),
        "prefix-lookalike-sibling": (evil_sibling, False),
    }
    for name, (answer, ok) in cases.items():
        path, problem = resolve_report_path(base, resolver_for(answer))
        if ok:
            assert path == answer and problem is None, f"{name}：{problem}"
        else:
            assert path is None and problem, f"{name}：應被指出，卻通過了 {path}"
    # Windows 行為＝路徑不分大小寫、分隔符等價（以 os.path.normcase 比對）；POSIX 大小寫敏感，
    # 不同大小寫是不同目錄，必須被指出
    variant = Path(str(inside).swapcase())
    path, problem = resolve_report_path(base, lambda p: p if p == base else variant)
    case_insensitive = os.path.normcase("A") == os.path.normcase("a")
    assert (path is not None) is case_insensitive, (path, problem)
    # 預設解析器：真的目錄通過，且回傳解析後的路徑
    base.mkdir()
    real, problem = resolve_report_path(base)
    assert problem is None and real == (base / "patrol.json").resolve()


# ── AT-966-1-E-1：寫入端 replace 交替時，讀端永遠讀到完整檔 ─────────────────────────────────
def test_AT_966_1_E_1_reader_never_sees_a_half_written_file_while_replace_alternates(
        rd: Path, settings: Settings, make_bridge: Any) -> None:
    filler = "巡邏" * 2000
    first = patrol_report(generated_at="2026-11-11T14:00:00+08:00", filler=filler)
    second = patrol_report(generated_at="2026-11-11T14:01:00+08:00", filler=filler + "二")
    write_report(rd, first)
    live = live_with(make_bridge, settings, rd)
    retries = {"count": 0}
    writer_error: list[BaseException] = []
    stop = threading.Event()

    def writer() -> None:
        try:
            for i in range(300):
                report = first if i % 2 else second
                tmp = rd / "patrol.json.tmp"
                tmp.write_bytes(json.dumps(report, ensure_ascii=False).encode("utf-8"))
                for _ in range(500):
                    try:
                        os.replace(tmp, rd / "patrol.json")
                        break
                    except OSError:       # Windows：目的檔被讀端開著時拒絕存取，重試
                        retries["count"] += 1
                        stop.wait(0.001)
                else:
                    raise RuntimeError("os.replace 重試 500 次仍失敗")
        except BaseException as exc:  # noqa: BLE001 - 帶回主執行緒斷言
            writer_error.append(exc)

    thread = threading.Thread(target=writer, name="patrol-writer")
    thread.start()
    bad: list[str] = []
    try:
        for i in range(300):
            resp = live.client.get("/si/patrol")
            if resp.status_code != 200:
                bad.append(f"#{i} {resp.status_code} {resp.text[:120]}")
            elif resp.json()["report"] not in (first, second):
                bad.append(f"#{i} report 不等於任何一份完整快照")
    finally:
        thread.join(timeout=120)
    print(f"AT_966_1_E_1 writer os.replace retries={retries['count']}")
    assert writer_error == [], writer_error
    assert bad == [], bad[:5]


# ── AT-966-1-E-2：殘留 .tmp 與其他檔名不被讀 ────────────────────────────────────────────────
def test_AT_966_1_E_2_leftover_tmp_and_other_names_are_never_read(
        rd: Path, settings: Settings, make_bridge: Any) -> None:
    stale = patrol_report(generated_at="2026-11-10T00:00:00+08:00")
    (rd / "patrol.json.tmp").write_bytes(json.dumps(stale).encode("utf-8"))
    (rd / "patrol.json.bak").write_bytes(json.dumps(stale).encode("utf-8"))
    live = live_with(make_bridge, settings, rd)
    assert_503(live.client.get("/si/patrol"), "report_missing")
    real = patrol_report(generated_at="2026-11-11T14:00:00+08:00")
    write_report(rd, real)
    resp = live.client.get("/si/patrol")
    assert resp.status_code == 200 and resp.json()["report"] == real, "不得讀 .tmp 或 .bak"
