"""單筆提案 `items[0].detail` 的透傳與白名單過濾（TCS-SiFlowVisibility-20261111：AT-966-4-1、4-2、
4-6、4-E-1；backend 的 4-3～4-5 在 `SiProposalDetailApiIT`）。

路由對假 CLI 樹（tests/fake_si.py）真起子行程。重點：契約列出的鍵位元組級透傳（含鍵序）、清單端點
不含 `detail`、argv 不變、主機多帶的鍵（評估集內容的金絲雀）在回應任何位置都不存在。黃金樣本複本
（`tests/fixtures/si_report/detail.golden.json`，內容是整個 `items[0]`）由主控複製，
測試先比對它與根層檔逐位元組相等。AT 內不引用其他 AT 的 ID。
"""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from app import si_cli
from app.settings import Settings
from tests import si_repo_support as sup
from tests.fake_si import detail_full, make_fake_si, proposal_item, read_calls, set_control

SINGLE = "/si/proposals/PROP-SI-901"
ROOT_GOLDEN = (sup.MONOREPO / "tools" / "tests" / "fixtures" / "selfimproving" / "p7"
               / "detail.golden.json")
LOCAL_GOLDEN = Path(__file__).resolve().parent / "fixtures" / "si_report" / "detail.golden.json"
CANARIES = ("CANARY-TOP", "CANARY-CASE", "CANARY-RAW", "CANARY-PROBE", "CANARY-FILE",
            "CANARY-LOG", "CANARY-SECRET", "CANARY-TRACE", "CANARY-INTERNAL", "CANARY-PID")
NE_NEW_CODE = {"field": "patch", "reason": "PATCH-UNREADABLE", "text": "提案修補檔讀不到，請看主機"}


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    return make_fake_si(tmp_path)


def export_object(items: list[Any], **over: Any) -> dict[str, Any]:
    obj: dict[str, Any] = {
        "schema_rev": 1, "kind": "proposals", "generated_at": "2026-11-11T14:00:00+08:00",
        "head_sha": "abc1234", "items": items, "next_since": None, "truncated": False,
        "ne": [], "problems": []}
    obj.update(over)
    return obj


def wire_bytes(obj: Any) -> bytes:
    """Bridge 的 JSONResponse 編碼形態（緊湊、非 ASCII 不跳脫）。"""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def live_with(make_bridge: Any, settings: Settings, root: Path) -> Any:
    return make_bridge(replace(settings, si_root=root))


def golden_item() -> dict[str, Any]:
    assert LOCAL_GOLDEN.read_bytes() == ROOT_GOLDEN.read_bytes(), \
        "複本與根層黃金樣本必須逐位元組相等（任一方改動即紅）"
    return json.loads(LOCAL_GOLDEN.read_text(encoding="utf-8"))


# ── AT-966-4-1：Bridge 對 detail 位元組級透傳 ───────────────────────────────────────────────
@pytest.mark.parametrize("source", ["synthetic", "golden"])
def test_AT_966_4_1_detail_passes_through_byte_for_byte(
        source: str, fake: Path, settings: Settings, make_bridge: Any) -> None:
    item = golden_item() if source == "golden" else proposal_item()
    ne = [NE_NEW_CODE] if source == "synthetic" else []
    export = export_object([item], ne=ne)
    set_control(fake, export=export)
    resp = live_with(make_bridge, settings, fake).client.get(SINGLE)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["detail"] == item["detail"], "detail 逐值等於 FAKE_CLI 輸出"
    assert list(body) == list(export), "其餘頂層鍵不增不減、鍵序同"
    assert resp.content == wire_bytes(export), "整份回應位元組級相同（含鍵序、含 ne 新碼項的 text）"
    patch = item["detail"].get("patch")
    if source == "synthetic":
        assert patch is not None
        assert body["items"][0]["detail"]["patch"]["text"].encode("utf-8") == \
            patch["text"].encode("utf-8")
        assert "\r\n" in patch["text"] and "\t" in patch["text"] and " " in patch["text"]
        assert "\U0001F600" in patch["text"] and "\n+++ b/x" in patch["text"]
        assert not patch["text"].endswith("\n"), "結尾無換行的夾具"
        assert body["ne"] == [NE_NEW_CODE]


# ── AT-966-4-2：清單端點不含 detail、argv 不變 ──────────────────────────────────────────────
def test_AT_966_4_2_list_has_no_detail_and_argv_is_unchanged(
        fake: Path, settings: Settings, make_bridge: Any) -> None:
    list_item = proposal_item(with_detail=False)
    set_control(fake, by_id={"PROP-SI-901": [proposal_item()]}, items=[list_item])
    live = live_with(make_bridge, settings, fake)
    listing = live.client.get("/si/proposals?limit=5")
    single = live.client.get(SINGLE)
    assert listing.status_code == 200 and single.status_code == 200
    assert all("detail" not in item for item in listing.json()["items"]), "清單項目不含 detail"
    assert "detail" in single.json()["items"][0]
    calls = read_calls(fake)
    assert len(calls) == 2
    single_args = calls[1]["args"]
    assert single_args == ["export", "--json", "--kind", "proposals", "--id", "PROP-SI-901"] == \
        si_cli.build_argv(fake, "proposals", ident="PROP-SI-901")[2:], \
        "單筆 argv 與修改前逐字相同（沿 si_cli.build_argv 現行形態）"
    assert "--detail" not in single_args and not any("detail" in arg for arg in single_args)
    assert calls[0]["args"] == si_cli.build_argv(fake, "proposals", limit=5)[2:]


# ── AT-966-4-6：Bridge 對 detail 只放行契約列出的鍵 ─────────────────────────────────────────
def dirty_detail() -> dict[str, Any]:
    """`detail_full()` 加上各層合成的未列鍵（評估集內容的金絲雀；有的放在鍵序最前、有的在中間）。"""
    clean = detail_full()
    dirty = copy.deepcopy(clean)
    dirty = {"evalset": "CANARY-TOP", **dirty}
    dirty["heldout"] = {"cases": ["CANARY-CASE"], **dirty["heldout"], "probes": ["CANARY-PROBE"],
                        "files": {"x": "CANARY-FILE"}}
    dirty["patch"] = {**dirty["patch"], "raw": "CANARY-RAW"}
    dirty["sandbox"] = {**dirty["sandbox"], "log": "CANARY-LOG"}
    dirty["verify"] = {**dirty["verify"], "secret": "CANARY-SECRET"}
    dirty["verify"]["reasons"] = [{**r, "trace": "CANARY-TRACE"}
                                  for r in dirty["verify"]["reasons"]]
    dirty["sourceObs"] = [{**o, "internal": "CANARY-INTERNAL"} for o in dirty["sourceObs"]]
    dirty["timeline"] = [{**t, "pid": "CANARY-PID"} for t in dirty["timeline"]]
    return dirty


def test_AT_966_4_6_detail_is_whitelisted_to_the_contract_keys(
        fake: Path, settings: Settings, make_bridge: Any) -> None:
    live = live_with(make_bridge, settings, fake)
    clean = detail_full()
    dirty = dirty_detail()
    assert all(c in json.dumps(dirty) for c in CANARIES), "夾具必須真的帶著全部金絲雀"

    def fetch(item: dict[str, Any]) -> Any:
        set_control(fake, export=export_object([item], ne=[NE_NEW_CODE]))
        return live.client.get(SINGLE)

    resp = fetch(proposal_item(dirty))
    assert resp.status_code == 200, resp.text
    assert not any(c in resp.text for c in CANARIES), "多帶的鍵在回應任何位置都不得存在"
    got = resp.json()["items"][0]
    assert json.dumps(got["detail"], ensure_ascii=False) == json.dumps(clean, ensure_ascii=False), \
        "契約列出的鍵與值逐值不變且鍵序保留"
    heldout = got["detail"]["heldout"]
    assert heldout["digest8"] == "0a1b2c3d" and "neNote" in heldout
    assert got["detail"]["sandbox"]["failText"], "failText 不得被削掉"
    for key in ("id", "state", "rev", "lastSeq", "sources", "card"):
        assert got[key] == proposal_item()[key], f"items[0].{key} 不受影響"
    assert resp.json()["ne"] == [NE_NEW_CODE] and resp.json()["problems"] == []

    # detail 為字串、陣列、null：items[0] 沒有 detail 鍵
    for name, bad in {"string": "CANARY-STR", "array": ["CANARY-ARR"], "null": None}.items():
        item = proposal_item(bad)
        resp = fetch(item)
        assert resp.status_code == 200, name
        assert "detail" not in resp.json()["items"][0], f"{name}：detail 不是物件須視為缺席"
        assert "CANARY" not in resp.text, name
        assert {k: v for k, v in resp.json()["items"][0].items()} == {
            k: v for k, v in item.items() if k != "detail"}, f"{name}：其他鍵不受影響"

    # sourceObs 缺列形態 {id, missing} 原樣保留（不被削成 {id}）
    missing = proposal_item(detail_full(sourceObs=[{"id": "OBS-SI-002", "missing": True}]))
    got = fetch(missing).json()["items"][0]["detail"]["sourceObs"]
    assert got == [{"id": "OBS-SI-002", "missing": True}]

    # 只含契約鍵的完整形態（含黃金樣本）：與未過濾時逐位元組相同（白名單不誤傷契約鍵）
    plain = export_object([proposal_item(clean)], ne=[NE_NEW_CODE])
    set_control(fake, export=plain)
    assert live.client.get(SINGLE).content == wire_bytes(plain)
    item = golden_item()
    plain = export_object([item])
    set_control(fake, export=plain)
    assert live.client.get(SINGLE).content == wire_bytes(plain), "黃金樣本不得被白名單誤傷"

    # 形狀不符的內層區塊 fail-closed：純量鍵放容器、區塊型別不符皆丟棄，不夾帶
    weird = detail_full(heldout="CANARY-STR", next={"code": {"x": "CANARY-NESTED"}, "who": "掌舵者",
                                                     "text": "t"}, timeline="CANARY-STR2")
    text = fetch(proposal_item(weird)).text
    assert "CANARY" not in text

    # 形狀不符的各種 Given：區塊型別不符、純量鍵放容器、陣列內非物件元素，一律丟棄且不外洩
    shapes = {
        "block-is-a-string": detail_full(sandbox="CANARY-SHAPE-A"),
        "block-is-an-array": detail_full(verify=["CANARY-SHAPE-B"]),
        "scalar-key-holds-an-object": detail_full(
            sandbox={**detail_full()["sandbox"], "failText": {"x": "CANARY-SHAPE-C"}}),
        "scalar-key-holds-an-array": detail_full(
            heldout={**detail_full()["heldout"], "neNote": ["CANARY-SHAPE-D"]}),
        "list-holds-non-objects": detail_full(timeline=["CANARY-SHAPE-E", 7, None]),
        "reasons-is-an-object": detail_full(
            verify={**detail_full()["verify"], "reasons": {"code": "CANARY-SHAPE-F"}}),
    }
    for name, bad in shapes.items():
        resp = fetch(proposal_item(bad))
        assert resp.status_code == 200, name
        assert "CANARY" not in resp.text, f"{name}：形狀不符的內容不得外送"
    got = fetch(proposal_item(shapes["list-holds-non-objects"])).json()["items"][0]["detail"]
    assert got["timeline"] == [], "陣列內非物件元素逐一丟棄"
    got = fetch(proposal_item(shapes["block-is-a-string"])).json()["items"][0]["detail"]
    assert "sandbox" not in got and got["patch"] == detail_full()["patch"], \
        "形狀不符的區塊整塊丟棄、其他區塊不受影響"

    # snake_case 鍵到達：Bridge 只認 camelCase，snake 鍵一律丟棄（不轉換、不外洩）
    snake = {
        "patch": detail_full()["patch"],
        "source_obs": [{"id": "CANARY-SNAKE-A"}],
        "heldout": {"below_min": True, "frozen_by": "CANARY-SNAKE-B", "seq": 60},
        "sandbox": {"touched_ok": True, "rollback_ok": True, "fail_code": "CANARY-SNAKE-C"},
        "verify": {"baseline_red": True, "probes_n": 6, "verdict": "PASS",
                   "reasons": [{"code": "VERIFY-OK", "text": "ok"}]},
    }
    resp = fetch(proposal_item(snake))
    assert resp.status_code == 200
    assert "CANARY" not in resp.text, "snake_case 鍵不得外送"
    got = resp.json()["items"][0]["detail"]
    assert "source_obs" not in got and "sourceObs" not in got
    assert got["heldout"] == {"seq": 60}, "只有單字鍵（兩種風格相同）的 seq 存活"
    assert got["sandbox"] == {} and got["verify"] == {
        "verdict": "PASS", "reasons": [{"code": "VERIFY-OK", "text": "ok"}]}
    assert got["patch"] == detail_full()["patch"]


def test_AT_966_4_6_the_whitelist_function_is_pure_and_total() -> None:
    from app.si_detail import filter_detail, sanitize_single_proposal

    dirty = dirty_detail()
    snapshot = copy.deepcopy(dirty)
    out = filter_detail(dirty)
    assert dirty == snapshot, "輸入不得被改動"
    assert out == detail_full()
    assert filter_detail(None) is None and filter_detail("x") is None and filter_detail([]) is None
    assert filter_detail({}) == {}
    no_detail = export_object([proposal_item(with_detail=False)])
    assert sanitize_single_proposal(copy.deepcopy(no_detail)) == no_detail, "缺席者原樣缺席"
    assert sanitize_single_proposal({"items": []}) == {"items": []}


# ── AT-966-4-E-1：上限內的大 patch 與錯誤路徑不變 ───────────────────────────────────────────
def big_text(size: int) -> str:
    unit = "ab中\n"            # 2 + 3 + 1 = 6 位元組
    reps, rest = divmod(size, len(unit.encode("utf-8")))
    text = unit * reps + "x" * rest
    assert len(text.encode("utf-8")) == size
    return text


def test_AT_966_4_E_1_big_patch_within_limit_and_error_paths_are_unchanged(
        fake: Path, settings: Settings, make_bridge: Any) -> None:
    live = live_with(make_bridge, settings, fake)
    size = 262144
    patch_text, body_text = big_text(size), big_text(size)[::-1]
    detail = detail_full(
        patch={"rel": "p.patch", "bytes": size, "text": patch_text, "truncated": True},
        body={"rel": "b.md", "bytes": size, "text": body_text, "truncated": True})
    set_control(fake, export=export_object([proposal_item(detail)]))
    resp = live.client.get(SINGLE)
    assert resp.status_code == 200, resp.status_code
    got = resp.json()["items"][0]["detail"]
    assert got["patch"]["text"].encode("utf-8") == patch_text.encode("utf-8")
    assert got["body"]["text"].encode("utf-8") == body_text.encode("utf-8")
    assert len(resp.content) < si_cli.SI_STDOUT_MAX_BYTES
    # 超過 8 MiB 上限＝503 stdout_too_large（既有行為）
    set_control(fake, huge=True)
    over = live.client.get(SINGLE)
    assert over.status_code == 503 and over.json()["cause"] == "stdout_too_large", over.text
    # 查無＝404 si_not_found；格式不符＝422 invalid_request（rule=invalid_format）
    set_control(fake, export=export_object([]))
    missing = live.client.get("/si/proposals/PROP-SI-999")
    assert missing.status_code == 404 and missing.json()["reason"] == "si_not_found"
    bad = live.client.get("/si/proposals/bad-id")
    assert bad.status_code == 422 and bad.json()["reason"] == "invalid_request"
    assert bad.json()["violations"][0]["rule"] == "invalid_format"
