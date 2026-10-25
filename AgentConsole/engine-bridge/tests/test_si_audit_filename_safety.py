"""稽核檔的檔名安全（TCS-SelfImprovingDecide-P2b：AT-950-1-E-3；W2、W3）。

檔名只源自「已驗過的 `audit_ref`」：整串為小寫正規 UUID，其餘（路徑穿越、斜線、NUL、大寫、結尾
換行或空白、`.json` 尾綴、全形數字、Windows 保留名…）一律拒收——函式層 `ValueError`、HTTP 層 422
`invalid_request`，且稽核目錄與其上層目錄都不留任何檔。AT 內不引用其他 AT 的 ID。
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from app import si_audit
from app.settings import Settings
from tests import si_repo_support as sup
from tests.fake_si import make_fake_si

T0 = sup.T0
GOOD = "d0000000-0000-4000-8000-000000000001"
FULLWIDTH = str.maketrans("0123456789", "０１２３４５６７８９")
ILLEGAL_REFS: dict[str, str] = {
    "empty": "", "dot-dot": "..", "traversal": "../x", "forward-slash": "a/b",
    "backslash": "a\\b", "nul-byte": "d0000000-0000-4000-8000-0000000000\x0001",
    "uppercase-uuid": GOOD.upper(), "uuid-then-dot-json": GOOD + ".json",
    "leading-space": " " + GOOD, "trailing-space": GOOD + " ", "trailing-newline": GOOD + "\n",
    "36-chars-not-a-uuid": "x" * 36, "fullwidth-digits": GOOD.translate(FULLWIDTH),
    "windows-reserved-name": "con", "braces-and-urn": "urn:uuid:" + GOOD,
    "no-hyphens": GOOD.replace("-", ""),
}
ENDPOINTS = {
    "decide": ("/si/proposals/PROP-SI-004:decide", "decide", "PROP-SI-004"),
    "obs-add": ("/si/observations", "obs-add", None),
    "obs-close": ("/si/observations/OBS-SI-005:close", "obs-close", "OBS-SI-005"),
}


def listing(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir())


def outer_with(kind: str, subject: str | None, ref: str) -> bytes:
    obj = {"schema_rev": 1, "kind": kind, "audit_ref": ref, "subject": subject, "body": "b",
           "key_id": sup.K0_ID, "mac": "0" * 64}
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@pytest.fixture
def audit_dir(tmp_path: Path) -> Path:
    path = tmp_path / "audit-bind-7f3a"
    path.mkdir()
    return path


@pytest.mark.parametrize("name", list(ILLEGAL_REFS))
def test_AT_950_1_E_3_an_illegal_audit_ref_is_a_value_error_and_leaves_no_file(
        audit_dir: Path, name: str) -> None:
    value = ILLEGAL_REFS[name]
    parent_before, dir_before = listing(audit_dir.parent), listing(audit_dir)
    with pytest.raises(ValueError):
        si_audit.store_audit(audit_dir, value, b"raw")
    assert listing(audit_dir) == dir_before == [], f"{name}：稽核目錄不得有任何檔"
    assert listing(audit_dir.parent) == parent_before, f"{name}：上層目錄不得多出任何檔"
    assert si_audit.is_audit_ref(value) is False


def test_AT_950_1_E_3_the_http_endpoints_reject_the_same_refs_with_422(
        make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
        audit_dir: Path) -> None:
    live = make_bridge(replace(settings, si_root=make_fake_si(tmp_path), si_write_token=T0,
                               si_audit_dir=audit_dir))
    parent_before, dir_before = listing(audit_dir.parent), listing(audit_dir)
    for name, value in ILLEGAL_REFS.items():
        for endpoint, (path, kind, subject) in ENDPOINTS.items():
            resp = live.client.post(
                path, content=outer_with(kind, subject, value),
                headers={"Content-Type": "application/json", "X-Bridge-Token": T0})
            label = f"{name} @ {endpoint}"
            assert resp.status_code == 422, f"{label}：{resp.status_code} {resp.text[:200]}"
            body = resp.json()
            assert body["reason"] == "invalid_request", label
            assert any(v["field"] == "audit_ref" for v in body["violations"]), \
                f"{label}：{body['violations']}"
    assert listing(audit_dir) == dir_before == []
    assert listing(audit_dir.parent) == parent_before


def test_AT_950_1_E_3_a_lowercase_canonical_uuid_is_the_control_that_succeeds(
        make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
        audit_dir: Path) -> None:
    assert si_audit.is_audit_ref(GOOD) is True
    si_audit.store_audit(audit_dir, GOOD, b"raw")
    assert listing(audit_dir) == [f"{GOOD}.json"]
    live = make_bridge(replace(settings, si_root=make_fake_si(tmp_path), si_write_token=T0,
                               si_audit_dir=audit_dir))
    good2 = "d0000000-0000-4000-8000-000000000002"
    resp = live.client.post(
        ENDPOINTS["decide"][0], content=outer_with("decide", "PROP-SI-004", good2),
        headers={"Content-Type": "application/json", "X-Bridge-Token": T0})
    assert resp.status_code == 201, resp.text
    assert listing(audit_dir) == [f"{GOOD}.json", f"{good2}.json"]
