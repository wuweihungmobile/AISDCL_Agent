"""研究來源單一化的 Bridge 測試支援（TCS-ResearchRegistry §5：`RDB`、`ENV`、共享附錄複本）。

- `make_registry_db(seed=…)`：拋棄式庫套 V1～V23 後，再套 V24（`seed=False` 時只套「表與守衛」，在
  追蹤來源種子標記之前截斷——表不可 DELETE，所以空登記只能這樣建）與 V25。
- `fixture_bytes(name)`：讀共享附錄／黃金檔複本，**先驗位元組 sha256**（不符＝夾具漂移，立即失敗）。
- `Rig`：活 Bridge＋DB 的小封裝（GET／POST／PATCH 帶寫入權杖）。
"""
from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import httpx

from app.research.db import ResearchDb
from app.settings import Settings
from tests.research_pg_support import MIGRATION_DIR, ThrowawayDb, make_research_db

TOKEN = "t0ken-" + "r" * 40
HEAD = {"X-Bridge-Token": TOKEN}
ADMIN = "admin"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "research_registry"
#: 追蹤來源種子在 V24 內的起點標記（其前是表、守衛函式與觸發器）。
SEED_MARK = "-- 追蹤來源種子"

#: 共享附錄與黃金檔複本的位元組 sha256（根層 TCS 附錄 E、契約 §5A.3）。
SHA = {
    "appendix-a.txt": "3101fd6aaebaf80e51d5161b3dee4ea87e8c9b15d2ac1a09f7c58ce55f230afd",
    "appendix-b.json": "147fccd6a1b9efb61423579e26fbbc7437366a937806e239c69f334732aff0e8",
    "appendix-d.txt": "25fd334dc97b8d135393849851962abfb54a621f11f9f0b1ba80eb27f4de1e89",
    "golden-r1.json": "73123a2bf0275448928199a72895297c77d6af8773ffa14b7cf453d19dc393a3",
    "seed_si_sources.json": "6201d066799e7f13c18053f3474f6883fddd8091baf0ab24e3a4b1c0d348e26f",
}
SIZES = {"appendix-a.txt": 441, "appendix-b.json": 2039, "appendix-d.txt": 1797,
         "golden-r1.json": 205}


def fixture_bytes(name: str) -> bytes:
    raw = (FIXTURES / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA[name], f"夾具 {name} 的 sha256 不符（夾具漂移）"
    if name in SIZES:
        assert len(raw) == SIZES[name], f"夾具 {name} 的位元組數不符"
    return raw


def make_registry_db(*, seed: bool) -> ThrowawayDb:
    db = make_research_db(last=23)
    v24 = (MIGRATION_DIR / "V24__research_watch_sources.sql").read_text(encoding="utf-8")
    v25 = (MIGRATION_DIR / "V25__si_console_writes_kind_src_registry.sql").read_text(
        encoding="utf-8")
    if not seed:
        assert SEED_MARK in v24, "V24 的種子標記不見了：空登記夾具無法截斷"
        v24 = v24[:v24.index(SEED_MARK)]
    try:
        with db.connect() as conn:
            conn.execute("SET search_path TO console")
            conn.execute(v24)
            conn.execute(v25)
    except BaseException:
        db.drop()
        raise
    return db


@dataclass
class Rig:
    live: Any
    settings: Settings
    rdb: ThrowawayDb

    @property
    def client(self) -> httpx.Client:
        return self.live.client

    def get(self, path: str, **kw: Any) -> httpx.Response:
        return self.client.get(path, **kw)

    def post(self, path: str, body: Any = None, *, headers: dict[str, str] | None = HEAD
             ) -> httpx.Response:
        return self.client.post(path, json=body, headers=headers)

    def patch(self, path: str, body: Any = None) -> httpx.Response:
        return self.client.patch(path, json=body, headers=HEAD)

    @property
    def db(self) -> ResearchDb:
        return ResearchDb(self.rdb.dsn)

    def audit_lines(self) -> list[dict[str, Any]]:
        path = self.settings.engine_workspace / "_audit.jsonl"
        lines = path.read_text("utf-8").splitlines() if path.is_file() else []
        return [json.loads(x) for x in lines if '"research_write"' in x]

    def add_host(self, host: str, *, kind: str = "FETCH", layer: str = "INDUSTRY",
                 interval: int = 3) -> dict[str, Any]:
        resp = self.post("/research/allowlist", {
            "list_kind": kind, "host": host, "layer": layer, "min_interval_seconds": interval,
            "added_by": ADMIN})
        assert resp.status_code == 201, resp.text
        return resp.json()


def build_rig(make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
              rdb: ThrowawayDb | None, **over: Any) -> Rig:
    root = tmp_path / "workspace" / f"ws-{secrets.token_hex(3)}"
    fields: dict[str, Any] = {"db_dsn": rdb.dsn if rdb else None, "research_root": root,
                              "research_write_token": TOKEN}
    fields.update(over)
    cfg = replace(settings, **fields)
    return Rig(live=make_bridge(cfg), settings=cfg, rdb=rdb)  # type: ignore[arg-type]


def watch_body(slug: str = "t-new-1", **over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "slug": slug, "url": "https://www.anthropic.com/news", "kind": "blog",
        "extract": "最新 3 篇標題", "layer": "INDUSTRY", "added_by": ADMIN,
        "expand": {"mode": "links", "prefix": "/news/", "max": 2}}
    body.update(over)
    return body


def appendix_d_rows() -> list[tuple[str, bool, bool]]:
    """附錄 D 的 (URL, SI, CON)；格式 `URL<TAB>SI<TAB>CON`。"""
    rows = []
    for line in fixture_bytes("appendix-d.txt").decode("utf-8").split("\n"):
        if line:
            url, si, con = line.split("\t")
            rows.append((url, si == "T", con == "T"))
    return rows
