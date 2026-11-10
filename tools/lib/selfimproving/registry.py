"""SelfImproving 研究來源登記鏡像：驗證、已知 id、事件綁定（AC-SI-30-2、45-1～45-3；P6）。

能力類別 `ro`：鏡像 `docs/06_quality/SelfImproving_Protocol/research_registry.json` 的位元組恆等於
Console 稽核檔 body 的 `registry_text`（只由 `regwrite.py` 寫入）。`validate` 是 `check` 的
`research.sources` 項、`research --fetch` 預檢與 `registry-ingest` 共用的唯一驗證函式；碼序依
PRD §9.2〈SI 端驗證〉。**刻意不判**：啟用來源的 host 是否在 `hosts` 內（抓取時逐來源判 `blocked`）。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from . import netguard
from . import sources as si_sources
from .evspec import SHA256_RE, SRC_ID_RE

REGISTRY_REL = "docs/06_quality/SelfImproving_Protocol/research_registry.json"
REGISTRY_TEXT_MAX = 24576
AUDIT_FILE_MAX = 65536
WATCH_KINDS = ("changelog", "docs", "release", "blog", "sitemap", "search")
LAYERS = ("ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY")
EXPAND_MODES = ("links", "sitemap")
_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$")
_TIME_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00$")
_HOST_KEYS = {"host", "layer", "list_kind", "min_interval_seconds", "source"}
_WATCH_KEYS = {"id", "url", "kind", "extract", "layer", "expand", "enabled", "added_by", "added_at",
               "disabled_by", "disabled_at"}
Problem = tuple[str, str, str]


def sha_of(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _int(v, lo: int = 0, hi: int | None = None) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= lo and (hi is None or v <= hi)


def _ctrl(text: str) -> bool:
    return any(ord(c) < 32 or ord(c) == 127 for c in text)


def _load(raw: bytes) -> tuple[object, list[Problem]]:
    """①：BOM、CR、結尾無 LF、不是 UTF-8 JSON 物件。"""
    bad: list[Problem] = []
    if raw.startswith(b"\xef\xbb\xbf"):
        bad.append(("REG-FILE-FORMAT", "-", "有 BOM"))
    if b"\r" in raw:
        bad.append(("REG-FILE-FORMAT", "-", "含 CR"))
    if not raw.endswith(b"\n"):
        bad.append(("REG-FILE-FORMAT", "-", "結尾無 LF"))
    try:
        obj = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        return None, bad + [("REG-FILE-FORMAT", "-", "不是 UTF-8 JSON")]
    if not isinstance(obj, dict):
        bad.append(("REG-FILE-FORMAT", "-", "頂層不是 JSON 物件"))
    return obj, bad


def _schema(obj: dict) -> list[Problem]:
    """②：`schema_rev`、頂層鍵、陣列與元素鍵集合。"""
    out: list[Problem] = []
    if obj.get("schema_rev") != 1 or isinstance(obj.get("schema_rev"), bool):
        out.append(("REG-SCHEMA", "-", "schema_rev 須為整數 1"))
    if set(obj) != {"schema_rev", "hosts", "watch"}:
        out.append(("REG-SCHEMA", "-", "頂層鍵集合須恰為 schema_rev、hosts、watch"))
    for name, keys in (("hosts", _HOST_KEYS), ("watch", _WATCH_KEYS)):
        arr = obj.get(name)
        if not isinstance(arr, list):
            out.append(("REG-SCHEMA", name, "須為陣列"))
            continue
        for i, el in enumerate(arr):
            if not isinstance(el, dict) or set(el) != keys:
                out.append(("REG-SCHEMA", f"{name}[{i}]", "元素不是物件或鍵集合不符"))
    return out


def _sub(el: dict, key: str, i: int, prefix: str) -> str:
    v = el.get(key)
    return v if isinstance(v, str) and v else f"{prefix}[{i}]"


def _hosts(arr: list) -> list[Problem]:
    out: list[Problem] = []
    keys: list[tuple[str, str]] = []
    for i, h in enumerate(arr):
        sub = _sub(h, "host", i, "hosts")
        host, lk = h["host"], h["list_kind"]
        ok = (isinstance(host, str) and _HOST_RE.match(host) and lk in ("FETCH", "WEB")
              and h["source"] in ("ENV", "ADMIN") and (h["layer"] is None or h["layer"] in LAYERS)
              and _int(h["min_interval_seconds"], 1))
        if not ok:
            out.append(("REG-HOST-FORMAT", sub, "host／list_kind／source／layer／間隔不合"))
        if isinstance(host, str) and isinstance(lk, str):
            keys.append((host, lk))
    seen: set = set()
    for k in keys:
        if k in seen:
            out.append(("REG-HOST-DUP", k[0], f"(list_kind, host) 重複：{k}"))
        seen.add(k)
    enc = [(a.encode("utf-8"), b.encode("utf-8")) for a, b in keys]
    out += [("REG-HOST-ORDER", keys[i + 1][0], "未依 (host, list_kind) 位元組序遞增")
            for i in range(len(enc) - 1) if enc[i] > enc[i + 1]]
    return out


def _expand_bad(e) -> bool:
    if e is None:
        return False
    if not isinstance(e, dict) or set(e) != {"mode", "prefix", "max"}:
        return True
    p = e["prefix"]
    return not (e["mode"] in EXPAND_MODES and isinstance(p, str) and 1 <= len(p) <= 200
                and p.startswith("/") and not any(c.isspace() for c in p) and not _ctrl(p)
                and _int(e["max"], 1, 3))


def _time_bad(v) -> bool:
    if v is None:
        return False
    if not (isinstance(v, str) and _TIME_RE.match(v)):
        return True
    try:
        datetime.fromisoformat(v)
    except ValueError:
        return True
    return False


def _field_bad(w: dict) -> bool:
    ex, ab = w["extract"], w["added_by"]
    return (not (isinstance(ex, str) and 1 <= len(ex) <= 200 and not _ctrl(ex))
            or w["layer"] not in LAYERS or not isinstance(w["enabled"], bool)
            or not (isinstance(ab, str) and 1 <= len(ab) <= 200)
            or any(w[k] is not None and not isinstance(w[k], str)
                   for k in ("added_at", "disabled_by", "disabled_at")))


def _watch(arr: list) -> list[Problem]:
    out: list[Problem] = []
    ids: list[str] = []
    for i, w in enumerate(arr):
        sub = _sub(w, "id", i, "watch")
        wid = w["id"]
        if not (isinstance(wid, str) and SRC_ID_RE.match(wid)):
            out.append(("REG-WATCH-ID", sub, "id 不合 ^[a-z0-9][a-z0-9-]{0,31}$"))
        else:
            ids.append(wid)
        if w["kind"] not in WATCH_KINDS:
            out.append(("REG-WATCH-KIND", sub, f"kind 不在 {list(WATCH_KINDS)}"))
        url = w["url"]
        if not isinstance(url, str) or netguard.url_shape_problems(url):
            out.append(("REG-WATCH-URL", sub, "url 形態不合（https、無 userinfo、公網 host…）"))
        if _field_bad(w):
            out.append(("REG-WATCH-FIELD", sub, "extract／layer／enabled／added_by 等欄位不合"))
        if _time_bad(w["added_at"]) or _time_bad(w["disabled_at"]):
            out.append(("REG-WATCH-TIME", sub, "added_at／disabled_at 須為 UTC 秒精度"))
        if _expand_bad(w["expand"]):
            out.append(("REG-WATCH-EXPAND", sub, "expand 鍵集合或值域不合"))
    for i, ident in enumerate(ids):
        if ident in ids[:i]:
            out.append(("REG-WATCH-DUP", ident, "id 重複"))
    out += [("REG-WATCH-ORDER", b, f"未依 id 的位元組序遞增（{a} 之後）")
            for a, b in zip(ids, ids[1:]) if a.encode("utf-8") > b.encode("utf-8")]
    return out


def validate(raw: bytes) -> list[Problem]:
    """鏡像驗證：回〔碼, subject, 說明〕串列，空＝合格；①②③任一失敗即不再往下判。"""
    if len(raw) > REGISTRY_TEXT_MAX:
        return [("REGISTRY-TOO-LARGE", "-", f"{len(raw)} 位元組 > {REGISTRY_TEXT_MAX}")]
    obj, bad = _load(raw)
    if bad:
        return bad
    bad = _schema(obj)
    if bad:
        return bad
    again = (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if again != raw:
        return [("REG-NORMAL", "-", "位元組不等於正規化序列化（indent=2、sort_keys、LF）")]
    return _hosts(obj["hosts"]) + _watch(obj["watch"])


def parse(raw: bytes | None) -> dict | None:
    """合格鏡像的物件；缺檔或不合格回 None。"""
    if raw is None or validate(raw):
        return None
    return json.loads(raw.decode("utf-8"))


def read_mirror(repo: Path) -> bytes | None:
    try:
        return (repo / REGISTRY_REL).read_bytes()
    except OSError:
        return None


def mirror_ids(raw: bytes | None) -> set[str] | None:
    """鏡像 `watch[].id` 全列（含停用）；不合格也盡量取（歷史 `src=` 照常解析）；缺檔回 None。"""
    if raw is None:
        return None
    try:
        obj = json.loads(raw.decode("utf-8-sig"))
        return {w["id"] for w in obj["watch"] if isinstance(w.get("id"), str)}
    except (ValueError, UnicodeDecodeError, KeyError, TypeError, AttributeError):
        return None


def known_ids(repo: Path) -> set[str] | None:
    """已知來源 id：鏡像全列 ∪ 凍結舊表全列；兩者都讀不到回 None（沿舊語意＝無從判定）。"""
    old_path = repo / si_sources.SOURCES_REL
    old = si_sources.ids_or_none(old_path.read_bytes() if old_path.is_file() else None)
    new = mirror_ids(read_mirror(repo))
    if old is None and new is None:
        return None
    return (old or set()) | (new or set())


def latest_event(events: list[dict]) -> dict | None:
    regs = [e for e in events if e.get("kind") == "research.registry"]
    return max(regs, key=lambda e: e["seq"]) if regs else None


def mirror_binding(raw: bytes | None, events: list[dict]) -> list[tuple[str, str]]:
    """`REGISTRY-UNBOUND`（鏡像位元組雜湊須等於最新事件的 registry_sha256）；兩者皆無＝
    `CARRIER-NOT-ESTABLISHED`（nonblocking）。回 [(碼, 說明)]。"""
    ev = latest_event(events)
    if raw is None and ev is None:
        return [("CARRIER-NOT-ESTABLISHED", "研究來源登記鏡像與 research.registry 事件皆不存在")]
    if raw is None or ev is None:
        return [("REGISTRY-UNBOUND", "鏡像與 research.registry 事件只有一方存在")]
    if sha_of(raw) != ev.get("registry_sha256"):
        return [("REGISTRY-UNBOUND", "鏡像位元組雜湊不等於最新 research.registry 事件")]
    return []


def scan_problems(events: list[dict], scans: list[dict]) -> list[tuple[str, str]]:
    """新格式 `research.scan`：`registry_seq` 須指向 sha 相同、且 seq 小於自身的 research.registry
    事件，否則 `SCAN-REGISTRY-MISMATCH`。回 [(subject, 說明)]。"""
    by_seq = {e["seq"]: e for e in events if e.get("kind") == "research.registry"}
    out = []
    for ev in scans:
        if "registry_seq" not in ev:
            continue
        tgt = by_seq.get(ev["registry_seq"])
        if tgt is None or tgt.get("registry_sha256") != ev.get("registry_sha256") \
                or ev["registry_seq"] >= ev["seq"]:
            out.append((f"seq={ev['seq']}",
                        "registry_seq／registry_sha256 對不上 research.registry 事件"))
    return out


def body_codes(body: dict) -> list[tuple[str, str]]:
    """稽核檔 body 判準（AC-SI-45-1 ④⑤⑥）：回第一個不符 [(碼, 說明)]，空＝合格。"""
    keys = {"schema_rev", "audit_ref", "kind", "user", "role", "time", "registry_text",
            "registry_sha256"}
    text, sha = body.get("registry_text"), body.get("registry_sha256")
    if set(body) != keys or not (isinstance(text, str) and text) or not (
            isinstance(sha, str) and SHA256_RE.match(sha)):
        return [("AUDIT-BODY-INVALID", "body 鍵集合、registry_text 或 registry_sha256 不合")]
    raw = text.encode("utf-8")
    if len(raw) > REGISTRY_TEXT_MAX:
        return [("REGISTRY-TOO-LARGE", f"registry_text {len(raw)} 位元組 > {REGISTRY_TEXT_MAX}")]
    if sha_of(raw) != sha:
        return [("REGISTRY-SHA-MISMATCH", "registry_sha256 與 registry_text 不符")]
    return []
