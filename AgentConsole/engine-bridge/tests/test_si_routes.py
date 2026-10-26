"""`/si/*` 路由的測試（TCS-SelfImprovingMirror-P1b：AT-932-2-3、AT-932-3-2、AT-940-9-1、
AT-940-9-E-1）。

路由對假 CLI 樹（tests/fake_si.py）真起子行程；唯一用真 CLI 的是 AT-940-9-E-1 的 limit 上限對照。
斷言重點：只有 GET、輸入在子行程之前驗證（被擋下的請求零子行程）、失敗一律固定形狀的 503、
404 與 503 的語意分離、SI 不可用不影響健康。AT 內不引用其他 AT 的 ID。
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest

from app import si_cli
from app.settings import Settings
from tests import si_repo_support as sup
from tests.fake_si import make_fake_si, read_calls, set_control

SINGLE = "/si/proposals/PROP-SI-004"
#: 路徑表：P1b 的六個讀路徑加議題中心的兩個（名稱沿用「SIX」，只增不改；TCS-IssueCenter-20261027
#: §5.7 的同步鎖）。
SIX_PATHS = ["/si/status", "/si/observations", "/si/events", "/si/proposals", SINGLE, "/si/runs",
             "/si/issues", "/si/issues/OBS-SI-001"]
ONE_ITEM = [{"id": "PROP-SI-004"}]


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    return make_fake_si(tmp_path)


def live_with(make_bridge: Any, settings: Settings, root: Path | None) -> Any:
    return make_bridge(replace(settings, si_root=root))


# ── AT-932-2-3：讀路徑只有 GET；其餘方法 405、未定義路徑 404、不啟動子行程 ────────────────────
# P2b 起 `POST /si/observations` 是寫入端點，故：PUT／PATCH／DELETE 乘全部（現為八個，含議題中心
# 的兩個）讀路徑皆 405；POST 乘其餘（七個）讀路徑皆 405。全部九個 P1b／P2b 的 `/si/` 路徑（含
# `:decide`、`:close`、`:validate`）的三方法矩陣由 test_si_write_routes.py 的 405 矩陣承擔。
READ_PATHS_WITHOUT_POST = [p for p in SIX_PATHS if p != "/si/observations"]


def test_AT_932_2_3_non_get_methods_are_405_and_undefined_paths_are_404(
        fake: Path, settings: Settings, make_bridge: Any) -> None:
    live = live_with(make_bridge, settings, fake)
    wrong = []
    for path in SIX_PATHS:
        for method in ("PUT", "PATCH", "DELETE"):
            resp = live.client.request(method, path, json={})
            if resp.status_code != 405:
                wrong.append((method, path, resp.status_code))
    for path in READ_PATHS_WITHOUT_POST:
        resp = live.client.request("POST", path, json={})
        if resp.status_code != 405:
            wrong.append(("POST", path, resp.status_code))
    assert wrong == [], f"八路徑乘 PUT／PATCH／DELETE 與七路徑乘 POST 必須全是 405：{wrong}"
    assert len(READ_PATHS_WITHOUT_POST) == 7
    undefined = ["/si/nothing", "/si/proposals/PROP-SI-004/extra", "/si/status/x",
                 "/si/observations/OBS-SI-001"]
    codes = {path: live.client.get(path).status_code for path in undefined}
    assert codes == dict.fromkeys(undefined, 404), codes
    assert read_calls(fake) == [], "非 GET 與未定義路徑都不得啟動子行程"


# ── AT-932-3-2：（八個）端點乘六種失敗形態 ───────────────────────────────────────────────
HEAD_MARK, TAIL_MARK = "HEAD-MARK", "TAIL-MARK"
BIG_STDERR = HEAD_MARK + "x" * (5000 - len(HEAD_MARK) - len(TAIL_MARK)) + TAIL_MARK
FAILURES = [
    ("si_root_unset", "si_root_unset"), ("script_missing", "si_script_missing"),
    ("timeout", "timeout"), ("nonzero_rc_big_stderr", "nonzero_rc"),
    ("garbage_stdout", "bad_json"), ("schema_rev_2", "schema_rev_mismatch"),
]


def test_AT_932_3_2_every_endpoint_fails_loudly_with_a_fixed_503_body(
        fake: Path, tmp_path: Path, settings: Settings, make_bridge: Any,
        monkeypatch: pytest.MonkeyPatch) -> None:
    live = live_with(make_bridge, settings, fake)
    base = live.app.state.settings
    emptied = tmp_path / "no-cli"
    emptied.mkdir()
    setups = {
        "si_root_unset": lambda: replace(base, si_root=None),
        "script_missing": lambda: replace(base, si_root=emptied),
        "timeout": lambda: (set_control(fake, sleep=30), base)[1],
        "nonzero_rc_big_stderr": lambda: (set_control(fake, rc=3, stderr=BIG_STDERR), base)[1],
        "garbage_stdout": lambda: (set_control(fake, raw_stdout="垃圾輸出"), base)[1],
        "schema_rev_2": lambda: (set_control(fake, schema_rev=2), base)[1],
    }
    total = 0
    for name, cause in FAILURES:
        set_control(fake)
        # 只有逾時那一輪縮短逾時；其餘維持預設，慢機器上假 CLI 起得慢也不會被誤判成逾時。
        monkeypatch.setattr(si_cli, "SI_CLI_TIMEOUT_SECONDS", 0.5 if name == "timeout" else 15.0)
        live.app.state.settings = setups[name]()
        for path in SIX_PATHS:
            resp = live.client.get(path)
            total += 1
            body = resp.json()
            label = f"{name} {path}"
            assert resp.status_code == 503, f"{label}：{resp.status_code} {resp.text[:200]}"
            assert set(body) == {"code", "reason", "cause", "detail"}, f"{label}：{sorted(body)}"
            assert (body["code"], body["reason"], body["cause"]) == (503, "si_unavailable", cause)
            assert "items" not in body, f"{label}：失敗回應不得帶空表"
            if name == "nonzero_rc_big_stderr":
                prefix = "rc=3; stderr="
                assert len(body["detail"]) == len(prefix) + 1000, label
                assert body["detail"] == prefix + BIG_STDERR[-1000:], label
                assert TAIL_MARK in body["detail"] and HEAD_MARK not in body["detail"], label
        for health in ("/health", "/health/deep"):
            assert live.client.get(health).status_code == 200, f"{name}：{health} 不得受 SI 影響"
    assert total == 48


# ── AT-940-9-1：只收 since、limit 與合格的 id；其餘 422 且不啟動子行程 ──────────────────────────
def test_AT_940_9_1_bad_input_is_rejected_before_any_subprocess(
        fake: Path, settings: Settings, make_bridge: Any) -> None:
    set_control(fake, by_id={"PROP-SI-004": ONE_ITEM})
    live = live_with(make_bridge, settings, fake)
    client = live.client
    unknown: list[tuple[str, str]] = [        # (網址, 被指為未知的參數名)
        ("/si/observations?foo=1", "foo"), ("/si/observations?since=1&bar=2", "bar"),
        ("/si/status?since=1", "since"), ("/si/status?limit=5", "limit"),
        ("/si/status?x=1", "x"), (f"{SINGLE}?since=1", "since")]
    for url, field in unknown:
        resp = client.get(url)
        body = resp.json()
        assert resp.status_code == 422, f"{url}：{resp.status_code}"
        assert body["reason"] == "invalid_request" and body["violations"], url
        assert (body["violations"][0]["rule"], body["violations"][0]["field"]) == (
            "unknown_parameter", field), f"{url}：{body['violations']}"
    wrong_type_or_range = [
        ("/si/observations?since=abc", "since"), ("/si/observations?since=-1", "since"),
        ("/si/observations?limit=0", "limit"), ("/si/observations?limit=abc", "limit")]
    for url, field in wrong_type_or_range:
        resp = client.get(url)
        body = resp.json()
        assert resp.status_code == 422, f"{url}：{resp.status_code}"
        assert body["reason"] == "invalid_request" and body["violations"], url
        assert body["violations"][0]["field"] == field, f"{url}：{body['violations']}"
        assert body["violations"][0]["rule"] != "unknown_parameter", url
    bad_ids = ["prop-si-004", "PROP-SI-04", "PROP-SI-004x", "PROP-SI-", "PROP-SI-00 4",
               "PROP-SI-００４", "PROP-SI-004\n", "..", "PROP-SI-004%2F..", "%2E%2E", "PROP%2FSI"]
    for ident in bad_ids:
        encoded = ident if "%" in ident else quote(ident, safe="")     # 已含 % 者原樣送出
        resp = client.get("/si/proposals/" + encoded)
        assert resp.status_code in (422, 404), f"{ident!r}：{resp.status_code} {resp.text[:120]}"
        if resp.status_code == 422:
            assert resp.json()["reason"] == "invalid_request", ident
    assert read_calls(fake) == [], "所有被擋下的請求都不得啟動子行程"
    for url in ("/si/observations?since=3&limit=2", "/si/runs", SINGLE):
        before = len(read_calls(fake))
        resp = client.get(url)
        assert resp.status_code == 200, f"{url}：{resp.status_code} {resp.text[:200]}"
        assert len(read_calls(fake)) == before + 1, f"{url}：合法請求恰啟動一次子行程"
    calls = read_calls(fake)
    assert calls[0]["args"][-4:] == ["--since", "3", "--limit", "2"]
    assert calls[2]["args"][-2:] == ["--id", "PROP-SI-004"]


# ── AT-940-9-E-1：404 與 503 的語意分離；limit 超限為 503 nonzero_rc ────────────────────────
def test_AT_940_9_E_1_not_found_and_unavailable_are_different_answers(
        fake: Path, tmp_path: Path, settings: Settings, make_bridge: Any,
        monkeypatch: pytest.MonkeyPatch) -> None:
    set_control(fake, by_id={"PROP-SI-004": ONE_ITEM})
    live = live_with(make_bridge, settings, fake)
    client = live.client
    resp = client.get("/si/proposals/PROP-SI-998")
    assert resp.status_code == 404
    body = resp.json()
    assert set(body) == {"code", "reason", "id"} and body["reason"] == "si_not_found"
    assert body["id"] == "PROP-SI-998" and "cause" not in body
    calls = read_calls(fake)
    assert len(calls) == 1 and calls[0]["args"][-2:] == ["--id", "PROP-SI-998"]
    set_control(fake, rc=3, stderr="export 旗標不合：--limit 介於 1 與上限")
    resp = client.get("/si/observations?limit=501")
    body = resp.json()
    assert resp.status_code == 503 and body["cause"] == "nonzero_rc", body
    assert body["detail"].startswith("rc=3; stderr=") and "id" not in body
    set_control(fake, sleep=30)
    monkeypatch.setattr(si_cli, "SI_CLI_TIMEOUT_SECONDS", 0.5)
    resp = client.get("/si/runs")
    body = resp.json()
    assert resp.status_code == 503 and body["cause"] == "timeout" and "id" not in body, body
    monkeypatch.setattr(si_cli, "SI_CLI_TIMEOUT_SECONDS", 15.0)
    # 真 CLI：limit 為上限時 200、上限加一時 503（nonzero_rc，stderr 帶旗標說明）
    sup.isolate_home(monkeypatch, tmp_path)
    real = sup.make_si_repo(tmp_path, "A")
    cap = json.loads((real / sup.PARAMS_SRC).read_text(encoding="utf-8"))["export_limit_max"]
    real_live = make_bridge(replace(settings, si_root=real))
    at_cap = real_live.client.get(f"/si/observations?limit={cap}")
    assert at_cap.status_code == 200, at_cap.text[:300]
    over = real_live.client.get(f"/si/observations?limit={cap + 1}")
    over_body = over.json()
    assert over.status_code == 503 and over_body["cause"] == "nonzero_rc", over_body
    assert "--limit 介於 1 與上限" in over_body["detail"], over_body["detail"]
    assert "id" not in over_body
