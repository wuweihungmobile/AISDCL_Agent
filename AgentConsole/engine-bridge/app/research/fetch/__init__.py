"""Bridge 原生抓取器（只有這個套件可以出網；ADR-003 D7；TCS D3、AC-960-8）。

模組分工：
  allowlist        獨立 allowlist 與 `check_research_url`（https／443／尾點／解析後私網拒絕）、
                   有效清單、內建節流下限表 `ENV_MIN_INTERVALS`（唯一定義）
  http             `FetchClient`：釘 IP＋SNI、逐跳重驗、有界讀取、節流與限流訊號；
                   `FetchRecord`（＝`research_fetches` 一列）、`ParseResult`
  arxiv／semantic_scholar／github／stackexchange
                   四個來源的請求網址與純函式解析器（輸出 `research_sources` 形狀的來源列）
  本檔             深度上界與排程（`plan_fetches`）、`run_prefetch`（排程→抓取→解析→必要時以
                   arXiv HTML 升到 V3、以 GitHub 預設分支 HEAD 取 commit sha）、原文落地
                   （`land_raw`）

給 PKG-BR-C（orchestrator）的接口——本套件**不寫資料庫、不發事件、不碰 FSM**，只回傳資料；全部是
同步呼叫且**會阻塞**（含節流睡眠：GitHub 未帶權杖的一般端點每次相隔 60 秒），在 asyncio 路徑內要用
`asyncio.to_thread` 或專屬執行緒：
  · `FetchClient.from_settings(cfg, allowlist=build_effective_allowlist(...), github_token=…)`；
  · `run_prefetch(client, tasks, depth_level=…)` → `FetchBatch`：`records`（每筆一個
    `FetchRecord`，含被拒者與重導的每一跳；`.to_db()` 即 `ResearchDb.insert_fetch(fetch=…)` 的
    引數）、`sources`（`SourceBundle`：觀測形態的來源列＋證據它的抓取紀錄）、`skipped`
    （`skipped:over_limit`，進事件 payload、不佔 `research_fetches.outcome`）、`failures`、
    `no_sources`／`all_failed`／`exit_reason`；
  · 落地順序由呼叫端依持久化協定走（寫檔→outbox→DB）：`FetchRecord.raw_text` 與
    `raw_rel_path` 即要寫的檔；`land_raw` 是直接落地的簡便函式；來源列入庫前以
    `to_db_source_row` 轉換（`未見`→NULL）；
  · 入庫次序：先 `insert_source(source={**to_db_source_row(bundle.source), "id": bundle.id,
    "source_no": …})`，再 `insert_fetch(fetch=record.to_db())`——升級抓取紀錄的 `source_id` 指向
    該來源列（外鍵要求來源先入庫），列表型回應的紀錄 `source_id` 為空（一筆紀錄對多個來源）；
  · `FetchRecord.detail`（失敗原因）DDL 沒有對應欄位、不入庫，要給使用者看就放進事件 payload。
"""
from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from dataclasses import replace as _clone
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .. import layout
from . import arxiv, github, semantic_scholar, stackexchange
from .allowlist import (
    DEFAULT_ENV_MIN_INTERVAL,
    ENV_MIN_INTERVALS,
    UNPARSED_HOST,
    EffectiveAllowlist,
    UrlCheck,
    build_effective_allowlist,
    builtin_floor,
    check_research_url,
    stored_url,
)
from .http import (
    MISSING,
    OUTCOMES,
    PARSE_ERROR,
    PIN_MODE,
    FetchClient,
    FetchRecord,
    FetchResult,
    HostThrottle,
    ParseResult,
    system_resolver,
    to_db_source_row,
)

__all__ = [
    "DEFAULT_ENV_MIN_INTERVAL", "DEPTH_LIMITS", "ENV_MIN_INTERVALS", "MISSING", "OUTCOMES",
    "PIN_MODE", "UNPARSED_HOST", "DepthLimits", "EffectiveAllowlist", "FetchBatch", "FetchClient",
    "FetchPlan", "FetchRecord", "FetchResult", "FetchTask", "HostThrottle", "ParseResult",
    "SkippedFetch", "SourceBundle", "UrlCheck", "build_effective_allowlist", "builtin_floor",
    "check_research_url", "effective_limits", "land_raw", "plan_fetches", "run_prefetch",
    "system_resolver", "task_for", "to_db_source_row",
]

SKIPPED_OVER_LIMIT = "skipped:over_limit"


# ── 深度上界（NFR-R2P-02；初值未校準）──────────────────────────────────────────────────────────
@dataclass(frozen=True)
class DepthLimits:
    """每層來源數與全 run 抓取次數的上界。"""

    per_layer: int
    total: int


#: `depth_level` → 上界（每層來源數 5／10／20、全 run 抓取次數 15／30／60）。
DEPTH_LIMITS: Mapping[str, DepthLimits] = MappingProxyType({
    "QUICK": DepthLimits(5, 15), "STANDARD": DepthLimits(10, 30), "DEEP": DepthLimits(20, 60)})


def _clamp(requested: int | None, hard: int, name: str) -> int:
    if requested is None:
        return hard
    if isinstance(requested, bool) or not isinstance(requested, int) or requested < 0:
        raise ValueError(f"{name} 須為非負整數：{requested!r}")
    return min(requested, hard)


def effective_limits(depth_level: str, requested_per_layer: int | None = None,
                     requested_total: int | None = None) -> DepthLimits:
    """依 `depth_level` 取硬上限；UI 請求值只能下調、高於硬上限者夾到硬上限（NFR-R2P-02：「UI 只能
    下調上列上限，不得超過 Bridge 的硬上限」）。"""
    hard = DEPTH_LIMITS.get(depth_level)
    if hard is None:
        raise ValueError(f"depth_level 須為 {'、'.join(DEPTH_LIMITS)}：{depth_level!r}")
    return DepthLimits(_clamp(requested_per_layer, hard.per_layer, "每層來源數"),
                       _clamp(requested_total, hard.total, "全 run 抓取次數"))


# ── 排程 ────────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class FetchTask:
    """一個要抓的網址：`kind` 決定用哪個解析器（`arxiv`｜`semantic_scholar`｜`github`｜
    `stackexchange`）；`query` 記進 `research_fetches.query_text`。"""

    kind: str
    layer: str
    url: str
    query: str | None = None


@dataclass(frozen=True)
class SkippedFetch:
    """超出上界而不抓取的候選（`skipped:over_limit`）。`limit` 是撞到哪一道上界：`per_layer`
    或 `total`。落在事件 payload（`to_payload`），不佔 `research_fetches` 的 outcome 列舉。"""

    layer: str
    kind: str
    url: str
    limit: str

    def to_payload(self) -> dict[str, str]:
        return {"reason": SKIPPED_OVER_LIMIT, "layer": self.layer, "kind": self.kind,
                "url": stored_url(self.url), "limit": self.limit}


@dataclass(frozen=True)
class FetchPlan:
    accepted: tuple[FetchTask, ...]
    skipped: tuple[SkippedFetch, ...]


def plan_fetches(tasks: Iterable[FetchTask], limits: DepthLimits) -> FetchPlan:
    """依序排程：每層至多 `per_layer` 個、全部至多 `total` 個；超出的不抓取、不截斷，各留一筆
    `SkippedFetch`（先判每層上界、再判全域上界）。"""
    per_layer: dict[str, int] = {}
    accepted: list[FetchTask] = []
    skipped: list[SkippedFetch] = []
    for task in tasks:
        if per_layer.get(task.layer, 0) >= limits.per_layer:
            skipped.append(SkippedFetch(task.layer, task.kind, task.url, "per_layer"))
        elif len(accepted) >= limits.total:
            skipped.append(SkippedFetch(task.layer, task.kind, task.url, "total"))
        else:
            per_layer[task.layer] = per_layer.get(task.layer, 0) + 1
            accepted.append(task)
    return FetchPlan(tuple(accepted), tuple(skipped))


def task_for(kind: str, query: str, *, limit: int) -> FetchTask:
    """某個來源的搜尋任務（網址由該來源模組組成；`limit` 是回傳筆數）。"""
    if kind == "arxiv":
        return FetchTask(kind, arxiv.LAYER, arxiv.search_url(query, max_results=limit), query)
    if kind == "semantic_scholar":
        return FetchTask(kind, semantic_scholar.LAYER,
                         semantic_scholar.search_url(query, limit=limit), query)
    if kind == "github":
        return FetchTask(kind, github.LAYER, github.search_url(query, per_page=limit), query)
    if kind == "stackexchange":
        return FetchTask(kind, stackexchange.LAYER,
                         stackexchange.search_url(query, pagesize=limit), query)
    raise ValueError(f"不認得的來源種類：{kind!r}")


# ── 抓取＋解析＋升級 ────────────────────────────────────────────────────────────────────────
@dataclass
class SourceBundle:
    """一個成功解析出的候選來源：觀測形態的來源列、證據它的抓取紀錄（列表型 API 回應的終態紀錄；
    升級用的抓取成功時再加一筆）、來自哪個任務。`id` 預先配好，供升級抓取紀錄的 `source_id`
    參照。"""

    source: dict[str, Any]
    records: list[FetchRecord]
    task: FetchTask
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class FetchBatch:
    """`run_prefetch` 的結果。`records` 含每個被排程的任務與升級抓取的全部紀錄（被拒者、重導的每一跳
    都在）；`failures` 是終態非 OK 的任務終態紀錄（那個來源不入證據矩陣）。"""

    planned: int
    skipped: list[SkippedFetch] = field(default_factory=list)
    records: list[FetchRecord] = field(default_factory=list)
    sources: list[SourceBundle] = field(default_factory=list)
    failures: list[FetchRecord] = field(default_factory=list)

    @property
    def all_failed(self) -> bool:
        """每個被排程的任務都失敗（且至少排了一個）。"""
        return self.planned > 0 and len(self.failures) == self.planned

    @property
    def no_sources(self) -> bool:
        """沒有任何可用的候選來源（全失敗、或成功但零筆）。"""
        return not self.sources

    @property
    def exit_reason(self) -> str | None:
        """Bridge 原生抓取沒有證據可用時建議的 stage `exit_reason`；有來源回 None。"""
        return "no_evidence" if self.no_sources else None


def _parse(task: FetchTask, text: str, now: datetime | None) -> ParseResult:
    if task.kind == "arxiv":
        return arxiv.parse(text)
    if task.kind == "semantic_scholar":
        return semantic_scholar.parse(text)
    if task.kind == "github":
        return github.parse(text, now=now)
    if task.kind == "stackexchange":
        return stackexchange.parse(text)
    return ParseResult.error(f"不認得的來源種類：{task.kind!r}")


def _run_task(client: FetchClient, task: FetchTask,
              parse: Callable[[str], ParseResult]) -> tuple[list[FetchRecord], ParseResult | None]:
    """抓一個任務並解析。抓取成功但格式壞＝終態紀錄改記 `PARSE_ERROR`（原文仍落地供稽核）。"""
    result = client.fetch(task.url, layer=task.layer, query_text=task.query)
    records = list(result.records)
    if not result.ok or result.text is None:
        return records, None
    parsed = parse(result.text)
    if not parsed.ok:
        records[-1] = _clone(records[-1], outcome=PARSE_ERROR, detail=parsed.detail)
    return records, parsed


def _follow_up(bundle: SourceBundle) -> FetchTask | None:
    """升級用的第二次抓取：arXiv 的 HTML 全文（V3）、GitHub 達標 repo 預設分支的 HEAD
    （commit sha）。"""
    row = bundle.source
    if bundle.task.kind == "arxiv" and row.get("external_id") not in (None, MISSING):
        return FetchTask("arxiv_html", arxiv.LAYER, arxiv.html_url(str(row["external_id"])))
    branch = row.get("default_branch")
    if (bundle.task.kind == "github" and row.get("qualifies") and branch not in (None, MISSING)
            and row.get("git_commit") == MISSING):
        return FetchTask("github_head", github.LAYER,
                         github.head_url(str(row["external_id"]), str(branch)))
    return None


def _apply_upgrade(bundle: SourceBundle, task: FetchTask, records: list[FetchRecord],
                   text: str | None) -> list[FetchRecord]:
    """升級抓取成功時改寫來源列並讓該筆紀錄帶 `source_id`；回傳（可能被改寫過的）紀錄。"""
    if text is None:
        return records
    terminal = records[-1]
    if task.kind == "arxiv_html":
        bundle.source["verification"] = "V3"
    else:
        sha = github.parse_head(text)
        if sha is None:
            return [*records[:-1], _clone(terminal, outcome=PARSE_ERROR,
                                          detail="分支回應沒有可用的 commit sha")]
        bundle.source.update(git_commit=sha, anchor_kind="COMMIT", verification="V3")
    linked = _clone(terminal, source_id=bundle.id)
    bundle.records.append(linked)
    return [*records[:-1], linked]


def run_prefetch(client: FetchClient, tasks: Iterable[FetchTask], *, depth_level: str,
                 requested_per_layer: int | None = None, requested_total: int | None = None,
                 now: datetime | None = None, enrich: bool = True) -> FetchBatch:
    """排程（深度上界）→ 逐一抓取並解析（單一任務失敗只記失敗、其餘續跑）→ 對候選做升級抓取（用掉
    上界剩下的抓取次數）。每層保留的來源數也受 `per_layer` 限制，超出的候選留 `skipped:over_limit`。
    不寫資料庫、不落地檔案；網路與格式的失敗不丟例外（每種失敗都是一筆紀錄），只有呼叫端的程式錯誤
    （不認得的 `depth_level`、不在列舉內的 `layer`）丟 `ValueError`。"""
    limits = effective_limits(depth_level, requested_per_layer, requested_total)
    plan = plan_fetches(tasks, limits)
    batch = FetchBatch(planned=len(plan.accepted), skipped=list(plan.skipped))
    kept_per_layer: dict[str, int] = {}
    for task in plan.accepted:
        records, parsed = _run_task(client, task, lambda text, t=task: _parse(t, text, now))
        batch.records += records
        if parsed is None or not parsed.ok:
            batch.failures.append(records[-1])
            continue
        for row in parsed.sources:
            if kept_per_layer.get(task.layer, 0) >= limits.per_layer:
                batch.skipped.append(SkippedFetch(task.layer, task.kind, row["url"], "per_layer"))
                continue
            kept_per_layer[task.layer] = kept_per_layer.get(task.layer, 0) + 1
            batch.sources.append(SourceBundle(row, [records[-1]], task))
    if enrich:
        used = len(plan.accepted)
        for bundle in batch.sources:
            follow = _follow_up(bundle)
            if follow is None:
                continue
            if used >= limits.total:
                batch.skipped.append(SkippedFetch(follow.layer, follow.kind, follow.url, "total"))
                continue
            used += 1
            result = client.fetch(follow.url, layer=follow.layer, query_text=follow.query)
            records = _apply_upgrade(bundle, follow, list(result.records), result.text)
            batch.records += records
    return batch


# ── 原文落地 ────────────────────────────────────────────────────────────────────────────────
def land_raw(workspace: Path, record: FetchRecord) -> layout.WrittenFile | None:
    """把 OK 紀錄的原文落地成 `00_research/raw/<sha12>.txt`（純文字；檔案位元組＝`raw_text` 的
    UTF-8，所以 sha256 與位元組數恰等於紀錄的 `raw_sha256`／`raw_bytes`）。內容以雜湊定址，已存在
    就不重寫。沒有原文（被拒、失敗）回 None。持久化協定下的正式落地走 outbox 的 `FileWrite`，
    這是簡便版。"""
    if record.raw_text is None or record.raw_rel_path is None:
        return None
    return layout.write_workspace_file(workspace, record.raw_rel_path, record.raw_text,
                                       overwrite=False)
