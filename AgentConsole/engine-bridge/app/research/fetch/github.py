"""GitHub：請求網址與 repo 解析器（開源層；ADR-003 D7；PRD AC-R2P-04-6）。

`/search/repositories` 的每個 item 是一個候選 repo；每列含 stars、最近 push 時間、授權 SPDX（取
不到＝`未見`；GitHub 回 `NOASSERTION` 視為取不到並在 `license_note` 說明）、預設分支，以及（有取到
`/repos/{full}/branches/{branch}` 時）預設分支 HEAD 的 commit sha——它是定位符之一
（`anchor_kind=COMMIT`，查證層級 V3）；沒有 commit sha 時以 repo 網址為錨、層級 V2。

「stars 與活躍」門檻是可參數化的常數（`GITHUB_MIN_STARS`、`GITHUB_ACTIVE_DAYS`；**初值未校準**）：
解析器不丟棄不達標的 repo，而是在每列標 `qualifies`（星數達標、最近 push 在活躍天數內、未封存），
由呼叫端決定取捨。節流與權杖見 `allowlist.builtin_floor` 與 `http.FetchClient`。
缺欄寫 `未見`；壞格式（不是 JSON、既非搜尋回應也非單一 repo 物件）＝`PARSE_ERROR`，不產生來源列。
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlencode

from .http import MISSING, ParseResult, clean_text, iso_date

LAYER = "OSS"
HOST = "api.github.com"
#: 活躍判準的初值（未校準；AC-R2P-04-6：stars 與活躍門檻參數化）。
GITHUB_MIN_STARS = 50
GITHUB_ACTIVE_DAYS = 365
MAX_QUERY_WORDS = 8
_FULL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9._-]+$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_NO_LICENSE = "NOASSERTION"


def search_url(query: str, *, per_page: int) -> str:
    """repo 搜尋網址（關鍵詞、依 stars 降冪；沒有可用的詞丟 `ValueError`）。路徑以 `/search/` 起頭，
    節流下限是搜尋端點的值。"""
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_.-]*", query)[:MAX_QUERY_WORDS]
    if not words:
        raise ValueError("GitHub 查詢需要至少一個 ASCII 詞")
    params = {"q": " ".join(words), "sort": "stars", "order": "desc", "per_page": per_page}
    return f"https://{HOST}/search/repositories?{urlencode(params)}"


def head_url(full_name: str, branch: str) -> str:
    """預設分支 HEAD 的查詢網址（取 commit sha）。`full_name` 須是 `owner/repo`。"""
    if not _FULL_NAME_RE.match(full_name) or not branch.strip():
        raise ValueError(f"不是合法的 repo 全名或分支：{full_name!r} {branch!r}")
    return f"https://{HOST}/repos/{full_name}/branches/{quote(branch, safe='')}"


def parse_head(text: str) -> str | None:
    """`/branches/{branch}` 的回應 → 40 位小寫十六進位 commit sha；取不到回 None。"""
    try:
        doc = json.loads(text)
    except ValueError:
        return None
    commit = doc.get("commit") if isinstance(doc, dict) else None
    sha = commit.get("sha") if isinstance(commit, dict) else None
    return sha if isinstance(sha, str) and _SHA_RE.match(sha) else None


def _pushed(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _license(item: dict[str, Any]) -> tuple[str, str]:
    lic = item.get("license")
    if not isinstance(lic, dict):
        return MISSING, MISSING
    spdx, name = clean_text(lic.get("spdx_id")), clean_text(lic.get("name"))
    if spdx == MISSING or spdx == _NO_LICENSE:
        return MISSING, (f"GitHub 無法辨識授權（{_NO_LICENSE}）：{name}" if name != MISSING
                         else f"GitHub 無法辨識授權（{_NO_LICENSE}）")
    return spdx, name


def _row(item: dict[str, Any], head: str | None, now: datetime, min_stars: int,
         active_days: int) -> dict[str, Any] | None:
    full_name = item.get("full_name")
    if not isinstance(full_name, str) or not _FULL_NAME_RE.match(full_name):
        return None
    html_url = item.get("html_url")
    url = html_url.strip() if isinstance(html_url, str) and html_url.startswith(
        "https://") else f"https://github.com/{full_name}"
    stars = item.get("stargazers_count")
    stars = stars if isinstance(stars, int) and not isinstance(stars, bool) else MISSING
    pushed_raw = item.get("pushed_at")
    pushed = _pushed(pushed_raw)
    owner = item.get("owner")
    spdx, note = _license(item)
    archived = item.get("archived") is True
    qualifies = (isinstance(stars, int) and stars >= min_stars and pushed is not None
                 and (now - pushed).days <= active_days and not archived)
    return {
        "layer": LAYER, "tier": "T1", "verification": "V3" if head else "V2",
        "anchor_kind": "COMMIT" if head else "URL", "url": url, "doi": None,
        "git_commit": head or MISSING, "title": full_name,
        "authors_org": clean_text(owner.get("login")) if isinstance(owner, dict) else MISSING,
        "published_at": iso_date(pushed_raw), "source_type": "REPO", "license_spdx": spdx,
        "license_note": note, "clue_only": False, "external_id": full_name, "stars": stars,
        "pushed_at": pushed_raw if pushed is not None and isinstance(pushed_raw, str) else MISSING,
        "default_branch": clean_text(item.get("default_branch")), "qualifies": qualifies,
        "archived": archived, "fork": item.get("fork") is True}


def parse(text: str, *, heads: Mapping[str, str] | None = None, now: datetime | None = None,
          min_stars: int = GITHUB_MIN_STARS,
          active_days: int = GITHUB_ACTIVE_DAYS) -> ParseResult:
    """搜尋回應（`items[]`）或單一 repo 物件 → 來源列。`heads` 是 `full_name → /branches 回應文字`
    的對照（沒有或解析不出 sha 的 repo，`git_commit` 為 `未見`）；`now` 供活躍判準（預設現在）。"""
    try:
        doc = json.loads(text)
    except ValueError as exc:
        return ParseResult.error(f"不是合法的 JSON：{exc}")
    if isinstance(doc, dict) and isinstance(doc.get("items"), list):
        items = doc["items"]
    elif isinstance(doc, dict) and "full_name" in doc:
        items = [doc]
    else:
        return ParseResult.error("既不是搜尋回應（items 陣列）也不是單一 repo 物件")
    moment = now or datetime.now(UTC)
    rows = [_row(it, parse_head((heads or {}).get(str(it.get("full_name")), "")), moment,
                 min_stars, active_days) if isinstance(it, dict) else None for it in items]
    kept = tuple(r for r in rows if r is not None)
    skipped = len(rows) - len(kept)
    return ParseResult(True, kept, f"略過 {skipped} 筆缺 full_name 的項目" if skipped else "")
