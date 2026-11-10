"""Bridge `POST /si/registry:sync`：登記同步稽核檔落地（AT-965-6-6；契約 §5A.4）。

沿既有三個寫入端點的檢查序（停用→權杖→本文大小與 JSON→外層形態→落檔）；Bridge 不解內層 `body`、
不驗簽；`kind` 須為 `src-registry`、`subject` 須為 null。全部用假 CLI 樹與 tmp 稽核目錄。
"""
from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from app.settings import Settings
from tests import si_repo_support as sup
from tests.fake_si import make_fake_si, read_calls
from tests.test_si_write_routes import dump, listing, outer_dict, post, ref_of

PATH = "/si/registry:sync"
T0 = sup.T0


@pytest.fixture
def audit_dir(tmp_path: Path) -> Path:
    path = tmp_path / "audit-bind-9c1e"
    path.mkdir()
    return path


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    return make_fake_si(tmp_path)


@pytest.fixture
def live(make_bridge: Callable[..., Any], settings: Settings, fake: Path, audit_dir: Path) -> Any:
    return make_bridge(replace(settings, si_root=fake, si_write_token=T0, si_audit_dir=audit_dir))


def valid(n: int, **over: Any) -> bytes:
    obj = outer_dict("src-registry", None, ref_of(n))
    for key, value in over.items():
        if value is ...:
            obj.pop(key, None)
        else:
            obj[key] = value
    return dump(obj)


def test_AT_965_6_6_the_bridge_stores_a_registry_sync_audit_file_verbatim(
        live: Any, audit_dir: Path, fake: Path) -> None:
    # body 內放非 JSON 字串：Bridge 不解讀 body，仍收下
    raw = valid(1, body="not json {registry_text 在這裡}")
    resp = post(live, PATH, raw)
    assert resp.status_code == 201, resp.text
    assert resp.json() == {"audit_ref": ref_of(1), "stored": True}
    stored = audit_dir / f"{ref_of(1)}.json"
    assert stored.read_bytes() == raw, "落檔位元組須等於請求本文"
    obs = post(live, "/si/observations", dump(outer_dict("obs-add", None, ref_of(2))))
    assert obs.status_code == 201
    if os.name != "nt":                      # Windows 行為＝權限位元不是 POSIX 語意，只比較同型檔
        assert stat.S_IMODE(stored.stat().st_mode) == stat.S_IMODE(
            (audit_dir / f"{ref_of(2)}.json").stat().st_mode)
    assert listing(audit_dir) == sorted([f"{ref_of(1)}.json", f"{ref_of(2)}.json"])
    assert read_calls(fake) == [], "不啟動任何子行程（Bridge 不呼叫寫入型 CLI）"
    log = live.settings.engine_workspace / "_audit.jsonl"
    mine = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()
            if '"si_write"' in x]
    assert [(m["verb"], m["result"]) for m in mine if m["verb"] == "registry-sync"] == [
        ("registry-sync", "ok")]
    assert T0 not in log.read_text(encoding="utf-8")


@pytest.mark.parametrize("label, raw, rule", [
    ("kind-decide", valid(10, kind="decide"), "kind_mismatch"),
    ("kind-sched", valid(11, kind="sched-set"), "kind_mismatch"),
    ("subject-set", valid(12, subject="x"), "must_be_null"),
    ("missing-key", valid(13, mac=...), "required"),
    ("extra-key", valid(14, extra=1), "unknown_key"),
    ("ref-upper", valid(15, audit_ref=ref_of(15).upper()), "invalid_format"),
])
def test_AT_965_6_6_a_malformed_outer_is_422_and_nothing_is_stored(
        live: Any, audit_dir: Path, label: str, raw: bytes, rule: str) -> None:
    resp = post(live, PATH, raw)
    assert resp.status_code == 422, f"{label}：{resp.text}"
    assert resp.json()["reason"] == "invalid_request"
    assert rule in {v["rule"] for v in resp.json()["violations"]}, label
    assert listing(audit_dir) == []


def test_AT_965_6_6_oversize_non_json_and_the_token_gates(
        live: Any, audit_dir: Path, make_bridge: Callable[..., Any], settings: Settings,
        fake: Path) -> None:
    big = post(live, PATH, b"x" * 65537)
    assert big.status_code == 422 and big.json()["violations"][0]["rule"] == "too_large"
    junk = post(live, PATH, b"not json")
    assert junk.status_code == 422 and junk.json()["violations"][0]["rule"] == "not_json"
    for label, token in (("none", None), ("wrong", "w" * len(T0))):
        resp = post(live, PATH, valid(20), token=token)
        assert (resp.status_code, resp.json()["reason"]) == (403, "si_write_forbidden"), label
    off = make_bridge(replace(settings, si_root=fake, si_write_token=None, si_audit_dir=None))
    resp = post(off, PATH, valid(21))
    assert (resp.status_code, resp.json()["reason"]) == (503, "si_write_disabled")
    assert listing(audit_dir) == []
