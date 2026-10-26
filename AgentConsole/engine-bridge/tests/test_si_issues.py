"""議題中心的 Bridge 測試（TCS-IssueCenter-20261027：AT-IC-06-1-2、AT-IC-07-1-1、AT-IC-07-1-E-1、
AT-IC-07-2-1、AT-IC-07-2-E-1、AT-IC-07-3-1、AT-IC-07-3-E-1、AT-IC-12-3-2；R-IC-45～R-IC-48）。

兩個唯讀 GET：`/si/issues`（清單，收 `since`、`limit`、`status`、`source`）與 `/si/issues/{id}`
（單筆，不收任何查詢參數）。分兩類夾具：
  · **真 CLI**（`make_si_repo` 的複本倉；差分基準＝同一時刻直接以 `sys.executable` 跑
    `export --json --kind issues`）：證明回應＝根層輸出，不證明議題歸類正確（那是根層 TCS 的事）；
  · **假 CLI**（tests/fake_si.py）：斷言 argv 形態、輸入驗證在子行程之前、404／503 的對映，不依賴
    根層。
全程 hermetic：tmp 倉、tmp 家目錄、loopback 上的 uvicorn；真帳本、真事件帳本一律不碰。AT 內不
引用其他 AT 的 ID。
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

#: 夾具倉（狀態 A）內真有的議題；`DEF-999-001` 是合成測試保留族（夾具倉沒有缺陷主檔，必查無）。
OBS_ID, PROP_ID, MISSING_ID = "OBS-SI-001", "PROP-SI-004", "DEF-999-001"
LIST_PATH, SINGLE_PATH = "/si/issues", f"/si/issues/{OBS_ID}"
TAIL_START = 6          # argv：[py, script, export, --json, --kind, <kind>, …旗標…]


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    return make_fake_si(tmp_path)


def start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings, make_bridge: Any,
          state: str = "A") -> tuple[Path, Any, Path]:
    """（複本倉根, 活的 Bridge, tmp 家目錄）：Bridge 的 `si_root` 指向複本倉。"""
    home = sup.isolate_home(monkeypatch, tmp_path)
    root = sup.make_si_repo(tmp_path, state)
    return root, make_bridge(replace(settings, si_root=root)), home


def sans_generated_at(obj: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in obj.items() if k != "generated_at"}


def key_orders(obj: Any, path: str = "$") -> dict[str, list[str]]:
    """每個物件層級的鍵序列（保序解析後逐層比對；值不看）。"""
    out: dict[str, list[str]] = {}
    if isinstance(obj, dict):
        out[path] = list(obj)
        for key, value in obj.items():
            out.update(key_orders(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            out.update(key_orders(value, f"{path}[{index}]"))
    return out


def rules_of(body: dict[str, Any], field: str) -> list[str]:
    return [v["rule"] for v in body["violations"] if v["field"] == field]


# ── AT-IC-07-1-1：兩個路由逐值等於真 CLI；每請求恰一次子行程；其他方法 405 ────────────────────
def test_AT_IC_07_1_1_responses_equal_the_real_cli_export_and_only_get_is_served(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings,
        make_bridge: Any) -> None:
    root, live, _home = start(tmp_path, monkeypatch, settings, make_bridge)
    spawned = sup.record_si_popen(monkeypatch)
    cases: list[tuple[str, dict[str, Any], tuple[str, ...], list[str]]] = [
        # (路徑, 查詢參數, 基準 CLI 的額外旗標, 預期 Bridge 子行程 argv 的旗標尾段)
        (LIST_PATH, {}, (), []),
        (LIST_PATH, {"limit": 4}, ("--limit", "4"), ["--limit", "4"]),
        (LIST_PATH, {"since": 3, "limit": 4}, ("--since", "3", "--limit", "4"),
         ["--since", "3", "--limit", "4"]),
        (LIST_PATH, {"status": "待處理"}, ("--status=待處理",), ["--status=待處理"]),
        (LIST_PATH, {"source": "系統改善"}, ("--source=系統改善",), ["--source=系統改善"]),
        (SINGLE_PATH, {}, ("--id", OBS_ID), ["--id", OBS_ID]),
        (f"/si/issues/{PROP_ID}", {}, ("--id", PROP_ID), ["--id", PROP_ID]),
    ]
    for path, params, flags, _tail in cases:
        resp = live.client.get(path, params=params)
        assert resp.status_code == 200, f"{path} {params}：{resp.status_code} {resp.text[:300]}"
        baseline = sup.cli_export(root, "issues", *flags)
        label = f"{path} {params}"
        assert sans_generated_at(resp.json()) == sans_generated_at(baseline), \
            f"{label}：回應與真 CLI 的輸出不逐值相等"
        assert key_orders(resp.json()) == key_orders(baseline), f"{label}：各層鍵序必須保留"
        assert "\\u" not in resp.text, f"{label}：非 ASCII 必須以原字元出現、不跳脫"
        body = resp.json()
        assert body["kind"] == "issues", label
        if path == LIST_PATH:
            assert "legend" in body and "summary" in body, f"{label}：清單必帶 legend、summary"
        else:
            assert len(body["items"]) == 1, f"{label}：單筆 items 恰一筆"
            assert "legend" not in body and "summary" not in body, f"{label}：單筆沒有這兩個鍵"
    assert len(spawned) == len(cases), "每個請求恰啟動一次子行程"
    for argv, (_path, _params, _flags, tail) in zip(spawned, cases, strict=True):
        assert argv[2:TAIL_START] == ["export", "--json", "--kind", "issues"], argv
        assert argv[TAIL_START:] == tail, argv
    filtered = live.client.get(LIST_PATH, params={"status": "待處理"}).json()["items"]
    everything = live.client.get(LIST_PATH).json()["items"]
    assert 0 < len(filtered) < len(everything), "篩選必須真的縮小結果（否則這組差分是空轉）"
    before = len(spawned)
    for path in (LIST_PATH, SINGLE_PATH):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            code = live.client.request(method, path, json={}).status_code
            assert code == 405, f"{method} {path}：{code}"
    assert len(spawned) == before, "405 不得啟動子行程"


# ── AT-IC-07-1-E-1：未知參數、近似 ID 在子行程之前 422；合法而查無 404 ────────────────────────
def test_AT_IC_07_1_E_1_bad_input_is_rejected_before_any_subprocess_and_missing_is_404(
        fake: Path, settings: Settings, make_bridge: Any) -> None:
    set_control(fake, by_id={OBS_ID: [{"id": OBS_ID}]})
    live = make_bridge(replace(settings, si_root=fake))
    client = live.client
    for url, field in [(f"{LIST_PATH}?foo=1", "foo"), (f"{SINGLE_PATH}?since=1", "since"),
                       (f"{SINGLE_PATH}?status=x", "status"), (f"{SINGLE_PATH}?limit=1", "limit")]:
        resp = client.get(url)
        body = resp.json()
        assert resp.status_code == 422, f"{url}：{resp.status_code}"
        assert body["reason"] == "invalid_request", url
        assert rules_of(body, field) == ["unknown_parameter"], f"{url}：{body['violations']}"
    # 近似編號於執行期組字：R18 (a) 會把整串的 OBS 編號字面（帳本沒有的）判成懸空引用
    near_misses = ["obs-si-001", "OBS" + "-SI-12", "PROP-SI-4", "DEF-x-y", "OBS-SI-001x",
                   "OBS-SI-００１", "OBS-SI-001\n", "DEF-1-", "DEF--1", "def-1-1", "PROP-SI-"]
    for ident in near_misses:
        resp = client.get("/si/issues/" + quote(ident, safe=""))
        body = resp.json()
        assert resp.status_code == 422, f"{ident!r}：{resp.status_code} {resp.text[:120]}"
        assert body["reason"] == "invalid_request", ident
        assert rules_of(body, "id") == ["invalid_format"], f"{ident!r}：{body['violations']}"
    both = client.get("/si/issues/obs-si-001?since=1").json()
    assert sorted(v["rule"] for v in both["violations"]) == [
        "invalid_format", "unknown_parameter"], "多個違規一次列全"
    assert read_calls(fake) == [], "所有被擋下的請求都不得啟動子行程"
    for ident in (OBS_ID, PROP_ID, "DEF-999-002"):
        before = len(read_calls(fake))
        resp = client.get("/si/issues/" + ident)
        assert resp.status_code in (200, 404), f"{ident}：{resp.status_code}"
        assert len(read_calls(fake)) == before + 1, f"{ident}：合法格式恰啟動一次子行程"
    missing = client.get(f"/si/issues/{MISSING_ID}")
    body = missing.json()
    assert missing.status_code == 404
    assert set(body) == {"code", "reason", "id"} and body["reason"] == "si_not_found", body
    assert body["id"] == MISSING_ID and "cause" not in body
    assert read_calls(fake)[-1]["args"][-2:] == ["--id", MISSING_ID]


# ── AT-IC-07-2-1：篩選值以單一 argv 元素傳入；真 CLI 端到端不亂碼、不 500 ────────────────────
def test_AT_IC_07_2_1_filters_are_single_argv_elements_after_limit_and_before_id(
        fake: Path, settings: Settings, make_bridge: Any) -> None:
    live = make_bridge(replace(settings, si_root=fake))
    resp = live.client.get(LIST_PATH, params={
        "since": 3, "limit": 2, "status": "待解,延後", "source": "系統 缺陷"})
    assert resp.status_code == 200, resp.text[:300]
    call = read_calls(fake)[-1]
    assert call["args"] == ["export", "--json", "--kind", "issues", "--since", "3", "--limit", "2",
                            "--status=待解,延後", "--source=系統 缺陷"], call["args"]
    assert {"legend", "summary"} <= set(resp.json()), "假 CLI 的清單罐頭帶 legend、summary"
    # 值內的 `=`、空白、非 ASCII 控制類字元（U+0085、U+009F）都原樣在同一個 argv 元素內
    for value in ("a=b", "x y", "x\u0085y\u009fz", "待" * 64):
        resp = live.client.get(LIST_PATH, params={"status": value})
        assert resp.status_code == 200, f"{value!r}：{resp.status_code} {resp.text[:200]}"
        assert read_calls(fake)[-1]["args"][-1] == f"--status={value}"
        assert len(read_calls(fake)[-1]["args"]) == 5, "值不得被拆成多個 argv 元素"


def test_AT_IC_07_2_1_chinese_filters_reach_the_real_cli_and_come_back_unmangled(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings,
        make_bridge: Any) -> None:
    root, live, _home = start(tmp_path, monkeypatch, settings, make_bridge)
    spawned = sup.record_si_popen(monkeypatch)
    resp = live.client.get(LIST_PATH, params={"status": "待處理"})
    assert resp.status_code == 200, resp.text[:300]
    assert "\\u" not in resp.text and "�" not in resp.text, "不得亂碼"
    baseline = sup.cli_export(root, "issues", "--status=待處理")
    assert sans_generated_at(resp.json()) == sans_generated_at(baseline)
    assert {i["status"] for i in resp.json()["items"]} <= {"待解", "進行中", "觀察中"}
    assert 0 < len(baseline["items"]) < len(sup.cli_export(root, "issues")["items"]), \
        "篩選必須真的縮小結果"
    assert spawned[0][TAIL_START:] == ["--status=待處理"]
    # CLI 不認得的值（含空白、`=`、64 字元、C1 控制字元）：照樣通過驗證並啟動子行程，argv 為單一
    # 元素；下游 CLI rc 3 → 503（`nonzero_rc`），不是 422、不是 500
    odd = [("source", "a b"), ("status", "a=b"), ("status", "待" * 64),
           ("status", "x\u0085y\u009fz")]
    for field, value in odd:
        resp = live.client.get(LIST_PATH, params={field: value})
        body = resp.json()
        assert resp.status_code == 503, f"{field}={value!r}：{resp.status_code} {resp.text[:200]}"
        assert (body["reason"], body["cause"]) == ("si_unavailable", "nonzero_rc"), body
        assert body["detail"].startswith("rc=3; stderr="), body["detail"]
        assert spawned[-1][TAIL_START:] == [f"--{field}={value}"], spawned[-1]
    assert len(spawned) == 1 + len(odd)


# ── AT-IC-07-2-E-1：衛生擋在子行程之前（422），規則各自獨立、一次列全 ──────────────────────────
HYGIENE_CASES: list[tuple[str, str, str]] = [        # (參數名, 原始查詢值, 預期 rule)
    ("status", "-x", "leading_dash"), ("source", "-x", "leading_dash"),
    ("status", "-", "leading_dash"),
    ("status", "a" * 65, "too_long"), ("source", "a" * 65, "too_long"),
    ("status", quote("待" * 65), "too_long"),
    ("status", "%00", "control_char"), ("status", "%0A", "control_char"),
    ("status", "%7F", "control_char"), ("source", "%00", "control_char"),
    ("source", "%0A", "control_char"), ("source", "%7F", "control_char"),
    ("status", "a%1Fb", "control_char"), ("status", "%0D", "control_char"),
]


def test_AT_IC_07_2_E_1_hygiene_rejects_before_spawn(
        fake: Path, settings: Settings, make_bridge: Any) -> None:
    live = make_bridge(replace(settings, si_root=fake))
    for name, raw, rule in HYGIENE_CASES:
        resp = live.client.get(f"{LIST_PATH}?{name}={raw}")
        body = resp.json()
        assert resp.status_code == 422, f"{name}={raw}：{resp.status_code} {resp.text[:200]}"
        assert body["reason"] == "invalid_request", f"{name}={raw}"
        assert rule in rules_of(body, name), f"{name}={raw}：{body['violations']}"
    assert read_calls(fake) == [], "被擋下的請求都不得啟動子行程（不是 500）"
    combined = live.client.get(f"{LIST_PATH}?status=-{'a' * 70}%00&source=-y&foo=1").json()
    got = sorted((v["field"], v["rule"]) for v in combined["violations"])
    assert got == [("foo", "unknown_parameter"), ("source", "leading_dash"),
                   ("status", "control_char"), ("status", "leading_dash"),
                   ("status", "too_long")], "一個值同時違反多條規則、多個參數一起違規：一次列全"
    # 邊界：恰 64 字元、U+0080 以上的控制類字元、值中間的 `-`、空字串都不在拒絕範圍
    for value in ("a" * 64, "a\u0080b", "a-b", ""):
        resp = live.client.get(LIST_PATH, params={"status": value})
        assert resp.status_code == 200, f"{value!r}：{resp.status_code} {resp.text[:200]}"
    assert len(read_calls(fake)) == 4, "四個合法值各啟動一次子行程"
    assert read_calls(fake)[-1]["args"][-1] == "--status=", "空字串不特判：原樣成為單一 argv 元素"


# ── AT-IC-07-3-1：CLI rc≠0（含未知篩選值 rc 3）→ 503；issues 不新增 cause ─────────────────────
def test_AT_IC_07_3_1_cli_rc_3_and_an_over_limit_page_are_503_nonzero_rc(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings,
        make_bridge: Any) -> None:
    root, live, _home = start(tmp_path, monkeypatch, settings, make_bridge)
    for query in ({"status": "不存在的狀態"}, {"source": "不存在的來源"}):
        resp = live.client.get(LIST_PATH, params=query)
        body = resp.json()
        assert resp.status_code == 503, f"{query}：{resp.status_code} {resp.text[:200]}"
        assert (body["code"], body["reason"], body["cause"]) == (503, "si_unavailable",
                                                                  "nonzero_rc"), body
        assert body["detail"].startswith("rc=3; stderr=") and len(body["detail"]) > 20, body
        assert "items" not in body, "失敗回應不得帶空表"
    cap = json.loads((root / sup.PARAMS_SRC).read_text(encoding="utf-8"))["export_limit_max"]
    at_cap = live.client.get(LIST_PATH, params={"limit": cap})
    assert at_cap.status_code == 200, at_cap.text[:300]
    over = live.client.get(LIST_PATH, params={"limit": cap + 1})
    over_body = over.json()
    assert over.status_code == 503 and over_body["cause"] == "nonzero_rc", over_body
    assert over_body["detail"].startswith("rc=3; stderr="), over_body["detail"]


@pytest.mark.parametrize("path", [LIST_PATH, SINGLE_PATH])
def test_AT_IC_07_3_1_output_cap_and_timeout_keep_the_existing_causes(
        path: str, fake: Path, settings: Settings, make_bridge: Any,
        monkeypatch: pytest.MonkeyPatch) -> None:
    live = make_bridge(replace(settings, si_root=fake))
    set_control(fake, huge=True)
    monkeypatch.setattr(si_cli, "SI_STDOUT_MAX_BYTES", 2048)
    resp = live.client.get(path)
    body = resp.json()
    assert resp.status_code == 503 and body["reason"] == "si_unavailable", body
    assert body["cause"] == "stdout_too_large", body
    set_control(fake, sleep=30)
    monkeypatch.setattr(si_cli, "SI_CLI_TIMEOUT_SECONDS", 0.5)
    resp = live.client.get(path)
    body = resp.json()
    assert resp.status_code == 503 and body["cause"] == "timeout", body
    assert "items" not in body and "id" not in body


# ── AT-IC-07-3-E-1：空字串 status= 不特判，照傳給 CLI（rc 3）→ 503 ─────────────────────────────
def test_AT_IC_07_3_E_1_an_empty_filter_is_forwarded_and_the_cli_answer_is_503(
        fake: Path, settings: Settings, make_bridge: Any) -> None:
    set_control(fake, rc=3, stderr="selfimproving: 篩選值不合")
    live = make_bridge(replace(settings, si_root=fake))
    for name in ("status", "source"):
        resp = live.client.get(f"{LIST_PATH}?{name}=")
        body = resp.json()
        assert resp.status_code == 503, f"{name}=：{resp.status_code} {resp.text[:200]}"
        assert (body["reason"], body["cause"]) == ("si_unavailable", "nonzero_rc"), body
        assert body["detail"] == "rc=3; stderr=selfimproving: 篩選值不合", body["detail"]
        assert read_calls(fake)[-1]["args"][-1] == f"--{name}=", "空字串原樣成為單一 argv 元素"


def test_AT_IC_07_3_E_1_the_real_cli_rejects_the_empty_filter_with_rc_3(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings,
        make_bridge: Any) -> None:
    _root, live, _home = start(tmp_path, monkeypatch, settings, make_bridge)
    spawned = sup.record_si_popen(monkeypatch)
    resp = live.client.get(f"{LIST_PATH}?status=")
    body = resp.json()
    assert resp.status_code == 503, f"{resp.status_code} {resp.text[:200]}"
    assert (body["reason"], body["cause"]) == ("si_unavailable", "nonzero_rc"), body
    assert body["detail"].startswith("rc=3; stderr="), body["detail"]
    assert spawned[0][TAIL_START:] == ["--status="]


# ── AT-IC-06-1-2：兩個路由讀完之後，複本倉與家目錄零變動 ─────────────────────────────────────
def test_AT_IC_06_1_2_the_issue_routes_leave_the_repo_and_the_home_directory_untouched(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings,
        make_bridge: Any) -> None:
    root, live, home = start(tmp_path, monkeypatch, settings, make_bridge)
    before = sup.repo_snapshot(root)
    home_before = sup.tree_listing(home)
    assert before["status"] == "" and home_before == []
    queries: list[tuple[str, dict[str, Any]]] = [
        (LIST_PATH, {}), (LIST_PATH, {"since": 0, "limit": 3}), (LIST_PATH, {"status": "待處理"}),
        (LIST_PATH, {"source": "系統改善"}), (SINGLE_PATH, {}), (f"/si/issues/{PROP_ID}", {})]
    for _ in range(2):
        for path, params in queries:
            resp = live.client.get(path, params=params)
            assert resp.status_code == 200, f"{path} {params}：{resp.status_code} {resp.text[:200]}"
    after = sup.repo_snapshot(root)
    assert after == before, [k for k in before if before[k] != after[k]]
    assert sup.tree_listing(home) == home_before == [], "家目錄不得有任何新項目"
    assert [p for p in root.rglob("__pycache__")] == [], "子行程不得在 repo 內留下 __pycache__"


# ── AT-IC-12-3-2：Bridge 不快取，兩次 GET 之間帳本改變，第二次回應反映新內容 ────────────────────
def test_AT_IC_12_3_2_a_ledger_change_between_two_gets_shows_up_in_the_second(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: Settings,
        make_bridge: Any) -> None:
    root, live, _home = start(tmp_path, monkeypatch, settings, make_bridge)
    spawned = sup.record_si_popen(monkeypatch)
    first = live.client.get(LIST_PATH).json()
    sup.advance_to_b(root)
    second = live.client.get(LIST_PATH).json()
    assert len(spawned) == 2, "兩個請求各啟動一次子行程（無快取）"
    ids_first = [i["id"] for i in first["items"]]
    ids_second = [i["id"] for i in second["items"]]
    assert "OBS-SI-013" not in ids_first and "OBS-SI-013" in ids_second
    assert sorted(ids_second) == sorted([*ids_first, "OBS-SI-013"])
    assert second["summary"]["total"] == first["summary"]["total"] + 1
    assert second["head_sha"] != first["head_sha"], "頂層 head_sha 要隨提交改變"
    fresh = sup.cli_export(root, "issues")
    assert sans_generated_at(second) == sans_generated_at(fresh), "第二次回應＝當下真 CLI 的輸出"
