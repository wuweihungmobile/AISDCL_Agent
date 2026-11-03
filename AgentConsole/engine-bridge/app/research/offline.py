"""研究 stage 前置抓取的離線夾具（D-78、INT-06；TCS §5.3 hermetic：任何驗收都不被連線）。

為什麼：`mode=mock-only`（Bridge 找不到 `claude`，例如 Docker 全棧）與替身 claude 的劇本模式
（`MOCK_CLAUDE_RESEARCH_SCRIPT` 有設）只跑 mock 驗收，但 `_prefetch` 原本照樣對 arXiv／Semantic
Scholar／GitHub 發真請求：離線或被限流時 E2E 必紅（`no_evidence`），限流還多耗十幾秒，也違反
零外部依賴的本意。這個模組讓那兩種情境**一律不連網**：

  · `offline_reason`：判斷是否離線（`script`＝劇本模式、`mock-only`＝capabilities 的模式）；`None`
    ＝本機模式，才走真抓取（`fetch/`，唯一可出網的套件）；
  · `fixture_file`／`load_batch`：讀劇本宣告的抓取夾具，組成與真抓取同形的 `FetchBatch`
    （`FetchRecord` 與 `SourceBundle`），由 orchestrator 走**同一條**入庫路徑——原文落地、
    `research_fetches` 列、`prefetch_index.json`、`no_evidence` 判定都與真抓取共用同一份碼。
    沒有夾具＝空批次（`no_sources`，stage 以 `no_evidence` 失敗）但**不外呼**。

夾具由劇本 JSON 的頂層選填鍵 `prefetch` 指向（路徑相對劇本所在目錄，不得是絕對路徑或含 `..`；格式見
`app/mock_claude.py` 檔頭與 `engine-bridge/README.md`）：

  {"schema": 1,
   "fetches": [{"id": "a1", "layer": "ACADEMIC", "url": "https://…", "query": "…",
                "http_status": 200, "text": "<原文>"}],
   "sources": [{"fetch": "a1", "layer": "ACADEMIC", "tier": "T1", "verification": "V2",
                "anchor_kind": "URL", "url": "https://…", "title": "…", …}]}

抓取紀錄一律是 `outcome=OK`、`fetch_method=API`、`observed_by=BRIDGE`、`duration_ms=0`（DDL 的
outcome 列舉沒有 MOCK，不新增值）；`url` 用夾具內真實形狀的 https 字串但從不連線。本模組不
import 任何網路庫、不寫檔（能力登記＝ro）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..mock_claude import RESEARCH_SCRIPT_ENV, ScriptError, load_research_script, safe_relative
from ..settings import Settings
from .fetch import FetchBatch, FetchRecord, FetchTask, SourceBundle
from .settings import research_info

SCHEMA = 1
LAYERS = ("ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY")
#: 候選來源必備的欄位（其餘欄位依真抓取的觀測形態：缺值由使用者寫 `未見` 或省略）。
SOURCE_REQUIRED = ("layer", "tier", "verification", "anchor_kind", "url", "title")
_HOST_RE = re.compile(r"^https://([A-Za-z0-9.-]{1,253})(?::\d+)?(?:[/?#]|$)")


class OfflineFixtureError(ValueError):
    """夾具壞掉或劇本宣告了讀不到的夾具：stage 以 `prefetch_fixture_invalid` 失敗（fail-loud，不靜默
    退回空批次，否則壞夾具會被讀成「沒有來源」）。"""


def offline_reason(cfg: Settings, environ: Mapping[str, str] | None = None) -> str | None:
    """前置抓取不得連網的理由：`script`（劇本模式）｜`mock-only`（capabilities 的模式）｜`None`
    （本機模式：可真抓取）。劇本模式優先：開發機有 `claude` 但跑的是替身劇本時一樣不出網。"""
    env = os.environ if environ is None else environ
    if env.get(RESEARCH_SCRIPT_ENV, "").strip():
        return "script"
    if research_info(cfg)["mode"] == "mock-only":
        return "mock-only"
    return None


def fixture_file(environ: Mapping[str, str] | None = None) -> Path | None:
    """劇本宣告的抓取夾具檔路徑；沒有劇本或劇本沒宣告＝None。劇本讀不動或宣告的路徑不合規＝
    `OfflineFixtureError`。"""
    env = os.environ if environ is None else environ
    script = env.get(RESEARCH_SCRIPT_ENV, "").strip()
    if not script:
        return None
    try:
        doc, script_dir = load_research_script(script)
        declared = doc.get("prefetch")
        if declared is None:
            return None
        return script_dir.joinpath(*safe_relative(declared, "prefetch").parts)
    except ScriptError as exc:
        raise OfflineFixtureError(str(exc)) from exc


def _host_of(url: str) -> str:
    found = _HOST_RE.match(url)
    if found is None:
        raise OfflineFixtureError(f"夾具的網址必須是 https：{url[:80]!r}")
    return found.group(1).lower()


def _string(entry: Mapping[str, Any], key: str, where: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise OfflineFixtureError(f"{where} 的 {key} 必須是非空字串")
    return value


def _record(entry: Mapping[str, Any], index: int) -> FetchRecord:
    where = f"fetches[{index}]"
    layer = _string(entry, "layer", where)
    if layer not in LAYERS:
        raise OfflineFixtureError(f"{where} 的 layer 須為 {'、'.join(LAYERS)}：{layer!r}")
    url, text = _string(entry, "url", where), _string(entry, "text", where)
    status = entry.get("http_status", 200)
    if isinstance(status, bool) or not isinstance(status, int):
        raise OfflineFixtureError(f"{where} 的 http_status 必須是整數")
    query = entry.get("query")
    if query is not None and not isinstance(query, str):
        raise OfflineFixtureError(f"{where} 的 query 必須是字串")
    encoded = text.encode("utf-8")
    return FetchRecord(layer, url, _host_of(url), "OK", http_status=status, raw_text=text,
                       raw_sha256=hashlib.sha256(encoded).hexdigest(), raw_bytes=len(encoded),
                       duration_ms=0, query_text=query)


def load_batch(path: Path | None) -> FetchBatch:
    """夾具 → `FetchBatch`。`path=None`（沒有夾具）＝空批次（`no_sources`；不外呼）。"""
    if path is None:
        return FetchBatch(planned=0)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise OfflineFixtureError(f"讀不到抓取夾具 {path.name}（{type(exc).__name__}）") from exc
    except ValueError as exc:
        raise OfflineFixtureError(f"抓取夾具不是 JSON：{path.name}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise OfflineFixtureError(
            f"抓取夾具格式錯誤：須為 {{\"schema\": {SCHEMA}, …}}（{path.name}）")
    fetches, sources = doc.get("fetches", []), doc.get("sources", [])
    if not isinstance(fetches, list) or not isinstance(sources, list) or not all(
            isinstance(item, dict) for item in [*fetches, *sources]):
        raise OfflineFixtureError("fetches 與 sources 必須是物件清單")
    records: dict[str, FetchRecord] = {}
    for index, entry in enumerate(fetches):
        key = _string(entry, "id", f"fetches[{index}]")
        if key in records:
            raise OfflineFixtureError(f"fetches 的 id 重複：{key}")
        records[key] = _record(entry, index)
    batch = FetchBatch(planned=len(records), records=list(records.values()))
    for index, entry in enumerate(sources):
        where = f"sources[{index}]"
        record = records.get(_string(entry, "fetch", where))
        if record is None:
            raise OfflineFixtureError(f"{where} 的 fetch 指向不存在的抓取紀錄")
        row = {key: value for key, value in entry.items() if key != "fetch"}
        for key in SOURCE_REQUIRED:
            _string(row, key, where)
        if not str(row["url"]).startswith("https://"):
            raise OfflineFixtureError(f"{where} 的 url 必須是 https（research_sources 的 CHECK）")
        task = FetchTask("fixture", record.layer, record.url, record.query_text)
        batch.sources.append(SourceBundle(row, [record], task))
    return batch
