"""研究抓取的獨立 allowlist 與 URL 檢查（ADR-003 D7；D-35、D-62(3)、D-66；PRD NFR-R2P-03）。

三件事，全部是純函式或不可變資料（沒有網路、沒有檔案）：
  1. `check_research_url`：**包裝**既有 `app/security.py::check_outbound_url`（不修改它）。先呼叫它
     取兩個 URL 解析器的 host 一致性、userinfo／反斜線／控制字元拒絕與清單的精確比對；再加它刻意
     不管的四件事——僅 https、僅埠 443、拒尾點 host、解析後只要有一個位址不是全域公網位址就拒絕
     （DNS rebinding 防線的第一半；第二半是 `http.py` 以驗證過的位址連線，全程只解析一次）。
     `check_outbound_url` 接受 http、任意埠與尾點（`security.py:275-303`），所以不能原樣重用。
  2. `EffectiveAllowlist`：有效清單＝部署基底 ∪ 啟用中的 ADMIN 條目；每個 host 的有效節流間隔＝
     max(內建下限, ADMIN 條目值)（條目值只准把間隔拉長，NFR-R2P-03-6；AC-R2P-04-12）。
  3. 內建節流下限表 `ENV_MIN_INTERVALS` 與 GitHub 的分端點下限（V-R9 的主控現查值）。這張表原本暫
     放 `routers/research.py`（BR-A 為了輸出 allowlist 清單），自 BR-B 起以本檔為**唯一定義**，
     路由只 import（TCS §5.1：測試與產品碼共用同一份常數）。

模型端點清單（`BRIDGE_OUTBOUND_ALLOWLIST`）與本清單互不污染：這裡的函式只吃呼叫端傳進來的主機清單，
從不讀 `Settings.outbound_allowlist`。
"""
from __future__ import annotations

import ipaddress
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any
from urllib.parse import urlsplit

from ...security import check_outbound_url

#: 解析不出 host 的被拒外呼寫進 `research_fetches.host` 的保留字（D-66）：10 個字元、非空、不是合法
#: 主機名，所以 DDL 的 host 非空 CHECK 放行；測試與產品碼共用這一個常數。
UNPARSED_HOST = "(unparsed)"
#: 被拒外呼留存的 url 長度上界（D-66 對解析不出 host 者明定取前 500 字元；對可解析者同樣套用，免得
#: 攻擊者控制的重導目標把任意長字串寫進稽核帳）。
URL_STORE_MAX = 500
#: `research_fetches.host` 欄寬（VARCHAR(255)）；超過就改記保留字，不讓畸形輸入撞出 `22001`。
HOST_STORE_MAX = 255
HTTPS_PORT = 443
#: `research_fetches.layer`／`research_sources.layer` 的列舉（V17 的 CHECK）。
LAYERS = ("ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY")

#: `research_fetches.outcome` 的兩個拒絕碼與 DNS 失敗（沒有獨立列舉值，歸 HTTP_ERROR）。
DENIED_ALLOWLIST = "DENIED_ALLOWLIST"
DENIED_PRIVATE_IP = "DENIED_PRIVATE_IP"
HTTP_ERROR = "HTTP_ERROR"

#: 部署基底主機的內建節流下限（秒；TCS §5.1、PRD NFR-R2P-03-6，V-R9 官方頁現查值）。
#: `api.github.com` 取「未帶權杖的一般端點」60 秒（路由輸出 allowlist 清單用；實際間隔看端點與
#: 權杖，見 `builtin_floor`）。Stack Exchange 的 3 秒是**保守初值、非事實宣稱**（官方頁無法
#: 現查，V-R9 殘項）。
ENV_MIN_INTERVALS: Mapping[str, int] = MappingProxyType({
    "export.arxiv.org": 3, "arxiv.org": 3, "api.semanticscholar.org": 3, "api.github.com": 60,
    "api.stackexchange.com": 3})
#: 不在上表的 host（環境基底加了別的主機、或 ADMIN 條目）的內建下限。
DEFAULT_ENV_MIN_INTERVAL = 3

GITHUB_HOST = "api.github.com"
#: arXiv 的兩個 host 同屬一個操作者：限制「適用於同一操作者控制的全部機器」且「同時僅單一連線」，
#: 所以兩個 host 共用一個節流群組（同一條時間線、同一把互斥鎖）。
_ARXIV_HOSTS = frozenset({"export.arxiv.org", "arxiv.org"})
_ARXIV_GROUP = "arxiv"

#: 無法解析的位址一律當成非公網（保守）。
Resolver = Callable[[str], Sequence[str]]


def throttle_group(host: str) -> str:
    """節流群組：arXiv 兩個 host 共用 `arxiv`，其餘各自一組。"""
    return _ARXIV_GROUP if host in _ARXIV_HOSTS else host


def builtin_floor(host: str, path: str = "/", *, authenticated: bool = False) -> int:
    """內建節流下限（秒；V-R9）。GitHub 依端點與權杖分：一般端點未帶權杖 60、帶權杖 1；搜尋端點
    （路徑以 `/search/` 起頭）未帶權杖 6、帶權杖 2；code search（`/search/code`）6。Semantic Scholar
    P0 不使用金鑰（F-R2P-105），未帶金鑰 3 秒。其餘 host 取 `ENV_MIN_INTERVALS`，表外取預設。"""
    if host == GITHUB_HOST:
        if path == "/search/code" or path.startswith("/search/code/"):
            return 6
        if path.startswith("/search/"):
            return 2 if authenticated else 6
        return 1 if authenticated else 60
    return ENV_MIN_INTERVALS.get(host, DEFAULT_ENV_MIN_INTERVAL)


# ── 位址與紀錄欄位的消毒 ─────────────────────────────────────────────────────────────────────
def is_public_ip(address: str) -> bool:
    """是否為全域公網單播位址。`ip.is_global` 排除私網、loopback、link-local、未指定、文件用與
    CGNAT（`100.64.0.0/10`）等非全域範圍，但**不**排除多播與已廢棄的 site-local（`fec0::/10`）——這兩
    類另外擋（實測 Python 3.11 的 `224.0.0.1`、`ff02::1`、`fec0::1` 的 `is_global` 皆為真）。
    IPv4-mapped IPv6（`::ffff:127.0.0.1`）先還原成 IPv4 再判；解析不了的字串（含 scope id 以外的任何
    怪形態）一律視為非公網。"""
    try:
        parsed = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    ip = getattr(parsed, "ipv4_mapped", None) or parsed
    return bool(ip.is_global and not ip.is_multicast and not ip.is_reserved
                and not getattr(ip, "is_site_local", False))


def db_safe_text(text: str) -> str:
    """能安全寫進 PostgreSQL TEXT 的字串：NUL 改成字面 `\\x00`、孤立 surrogate 改成反斜線跳脫。"""
    return text.replace("\x00", "\\x00").encode("utf-8", "backslashreplace").decode("utf-8")


def record_host(host: object) -> str:
    """寫進 `research_fetches.host` 的值：非空、含可印字元、不超過欄寬才原樣用，否則記保留字。"""
    if not isinstance(host, str) or not host or len(host) > HOST_STORE_MAX:
        return UNPARSED_HOST
    if any(ord(ch) <= 0x20 or ord(ch) == 0x7F for ch in host):
        return UNPARSED_HOST
    return host


def stored_url(url: object) -> str:
    """被拒外呼寫進 `research_fetches.url` 的值：原字串（NUL 與孤立 surrogate 先消毒）的前 500
    字元；非字串記空字串（不是 NULL：非 WEB_SEARCH 列的 url 必填）。"""
    return db_safe_text(url)[:URL_STORE_MAX] if isinstance(url, str) else ""


# ── URL 檢查 ────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class UrlCheck:
    """`check_research_url` 的判定。`host` 已是可直接入庫的值（解析不出＝`UNPARSED_HOST`）；放行時
    `addresses` 是**已驗證**的公網位址（連線只准用它們）；拒絕時 `outcome` 是入庫的 outcome。"""

    ok: bool
    host: str
    reason: str
    outcome: str | None
    addresses: tuple[str, ...] = ()
    detail: str = ""


def check_research_url(url: Any, allowlist: Iterable[str], resolver: Resolver) -> UrlCheck:
    """研究抓取的 URL 閘（D-62(3)）。順序：`check_outbound_url`（解析器一致性、userinfo、精確 host
    比對）→ https → 埠 443 → 尾點 → 解析 → 全部位址皆公網。每一關都不做正規化放行（埠與尾點不
    被「修正」成可通過的形態）。"""
    ok, host, reason = check_outbound_url(url, tuple(allowlist))
    shown = record_host(host)
    if not ok:
        return UrlCheck(False, shown, reason, DENIED_ALLOWLIST)
    parts = urlsplit(url)
    if parts.scheme != "https":
        return UrlCheck(False, shown, "scheme_not_https", DENIED_ALLOWLIST)
    if parts.port not in (None, HTTPS_PORT):
        return UrlCheck(False, shown, "port_not_443", DENIED_ALLOWLIST)
    if (parts.hostname or "").endswith("."):
        return UrlCheck(False, shown, "trailing_dot", DENIED_ALLOWLIST)
    try:
        resolved = [str(a) for a in resolver(host)]
    except OSError as exc:                 # socket.gaierror 等：解析失敗不是安全拒絕，記 HTTP_ERROR
        return UrlCheck(False, shown, "dns_failure", HTTP_ERROR, detail=type(exc).__name__)
    if not resolved:
        return UrlCheck(False, shown, "dns_failure", HTTP_ERROR, detail="no address")
    bad = [a for a in resolved if not is_public_ip(a)]
    if bad:       # 任何一個非公網位址就整個 host 拒絕（混合答案是 rebinding 的常見形態）
        return UrlCheck(False, shown, "private_ip", DENIED_PRIVATE_IP,
                        detail=f"解析到非公網位址：{', '.join(bad)}")
    return UrlCheck(True, host, "ok", None, tuple(dict.fromkeys(resolved)))


# ── 有效清單 ────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class AllowEntry:
    """有效清單的一筆：`source` 為 `ENV`（部署基底）或 `ADMIN`（`research_allowlist_entries`）。"""

    host: str
    source: str
    min_interval_seconds: int
    layer: str | None = None


@dataclass(frozen=True)
class EffectiveAllowlist:
    """抓取層看到的有效清單（FETCH 類）。同一 host 可同時有 ENV 與 ADMIN 條目：節流間隔取各條目與
    內建下限的最大值。"""

    entries: tuple[AllowEntry, ...]

    @property
    def hosts(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(e.host for e in self.entries))

    def interval(self, host: str, path: str = "/", *, authenticated: bool = False) -> int:
        """有效 `min_interval_seconds`＝max(內建下限, ADMIN 條目值)：條目低於下限者仍取下限（只准
        拉長）。部署基底（ENV）條目沒有自己的值——它的 `min_interval_seconds` 只是
        `ENV_MIN_INTERVALS` 的顯示值，內建下限已經涵蓋（GitHub 的下限還看端點與權杖，不能被那個
        顯示值蓋過）。"""
        values = [e.min_interval_seconds for e in self.entries
                  if e.host == host and e.source == "ADMIN"]
        return max([builtin_floor(host, path, authenticated=authenticated), *values])

    def snapshot(self) -> list[dict[str, Any]]:
        """寫進 `research_stage_runs.allowlist_snapshot` 的形態（事後可稽核「當時允許了什麼」）。"""
        return [{"host": e.host, "list_kind": "FETCH", "source": e.source, "layer": e.layer,
                 "min_interval_seconds": self.interval(e.host)} for e in self.entries]


_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$")


def build_effective_allowlist(env_hosts: Iterable[str],
                              admin_entries: Iterable[Mapping[str, Any]] = ()
                              ) -> EffectiveAllowlist:
    """有效清單＝部署基底（`BRIDGE_RESEARCH_FETCH_ALLOWLIST`）∪ 啟用中的 FETCH 類 ADMIN 條目
    （`ResearchDb.list_allowlist()` 的列）。順序＝基底在前、ADMIN 在後（與路由輸出的
    `effective.FETCH` 同序）；Reddit 預設不在任何清單（沒有人加就沒有）。"""
    entries: list[AllowEntry] = []
    for raw in env_hosts:
        host = raw.strip().lower().rstrip(".")
        if _HOST_RE.match(host):
            entries.append(AllowEntry(host, "ENV", ENV_MIN_INTERVALS.get(
                host, DEFAULT_ENV_MIN_INTERVAL)))
    for row in admin_entries:
        if row.get("list_kind") == "FETCH" and row.get("enabled"):
            host = str(row["host"]).strip().lower().rstrip(".")
            if _HOST_RE.match(host):
                entries.append(AllowEntry(host, "ADMIN", int(row["min_interval_seconds"]),
                                          row.get("layer")))
    return EffectiveAllowlist(tuple(entries))
