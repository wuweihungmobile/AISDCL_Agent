"""SelfImproving P6 測試夾具（TCS-SelfImproving-P6 §3；`px` 建構器）與共享附錄常數。

附錄 A、B、C、D 的文字逐字取自 `docs/03_testing/contracts/TCS-SelfImproving-P6-20261110.md`
（唯一本文），各以位元組 sha256 常數釘住（附錄 E）；改表而不改常數＝測試紅。
"""

from __future__ import annotations

APPX_A_PARTS = (
    '8.8.8.8\tT\n',
    '1.1.1.1\tT\n',
    '2606:4700:4700::1111\tT\n',
    '2001:4860:4860::8888\tT\n',
    '::ffff:8.8.8.8\tT\n',
    '1.2.3.4%eth0\tT\n',
    '127.0.0.1\tF\n',
    '127.255.255.254\tF\n',
    '10.0.0.1\tF\n',
    '172.16.0.1\tF\n',
    '172.31.255.255\tF\n',
    '192.168.1.1\tF\n',
    '169.254.169.254\tF\n',
    '100.64.0.1\tF\n',
    '0.0.0.0\tF\n',
    '255.255.255.255\tF\n',
    '224.0.0.1\tF\n',
    '240.0.0.1\tF\n',
    '198.51.100.1\tF\n',
    '192.0.2.1\tF\n',
    '::1\tF\n',
    '::\tF\n',
    'fe80::1\tF\n',
    'fe80::1%eth0\tF\n',
    'fc00::1\tF\n',
    'fd00::1\tF\n',
    'ff02::1\tF\n',
    'fec0::1\tF\n',
    '::ffff:127.0.0.1\tF\n',
    '::ffff:10.0.0.1\tF\n',
    'not-an-ip\tF\n',
    '\tF\n',
    '999.1.1.1\tF\n',
    '1.2.3\tF\n',
)
APPX_A = "".join(APPX_A_PARTS)

APPX_B_PARTS = (
    '{\n',
    '  "hosts": [\n',
    '    {\n',
    '      "host": "export.arxiv.org",\n',
    '      "layer": null,\n',
    '      "list_kind": "FETCH",\n',
    '      "min_interval_seconds": 3,\n',
    '      "source": "ENV"\n',
    '    },\n',
    '    {\n',
    '      "host": "www.anthropic.com",\n',
    '      "layer": "INDUSTRY",\n',
    '      "list_kind": "FETCH",\n',
    '      "min_interval_seconds": 5,\n',
    '      "source": "ADMIN"\n',
    '    }\n',
    '  ],\n',
    '  "schema_rev": 1,\n',
    '  "watch": [\n',
    '    {\n',
    '      "added_at": "2026-11-10T00:00:00+00:00",\n',
    '      "added_by": "migration:V24（SI research_sources.json 匯入）"'
    ',\n',
    '      "disabled_at": "2026-11-10T00:00:00+00:00",\n',
    '      "disabled_by": "migration:V24（以 anthropic-research 取代）"'
    ',\n',
    '      "enabled": false,\n',
    '      "expand": null,\n',
    '      "extract": "最新 5 篇文章的標題與日期（逐字）",\n',
    '      "id": "anthropic-engineering",\n',
    '      "kind": "blog",\n',
    '      "layer": "INDUSTRY",\n',
    '      "url": "https://www.anthropic.com/engineering"\n',
    '    },\n',
    '    {\n',
    '      "added_at": "2026-11-10T00:00:00+00:00",\n',
    '      "added_by": "migration:V24（研究來源單一化種子）",\n',
    '      "disabled_at": null,\n',
    '      "disabled_by": null,\n',
    '      "enabled": true,\n',
    '      "expand": {\n',
    '        "max": 3,\n',
    '        "mode": "sitemap",\n',
    '        "prefix": "/research/"\n',
    '      },\n',
    '      "extract": "最新 3 篇研究文章的全文（逐字）",\n',
    '      "id": "anthropic-research",\n',
    '      "kind": "sitemap",\n',
    '      "layer": "INDUSTRY",\n',
    '      "url": "https://www.anthropic.com/sitemap.xml"\n',
    '    },\n',
    '    {\n',
    '      "added_at": "2026-11-10T00:00:00+00:00",\n',
    '      "added_by": "migration:V24（研究來源單一化種子）",\n',
    '      "disabled_at": null,\n',
    '      "disabled_by": null,\n',
    '      "enabled": true,\n',
    '      "expand": null,\n',
    '      "extract": "最新 10 篇論文的標題、作者、日期與摘要首句（逐字'
    '）",\n',
    '      "id": "arxiv-agents",\n',
    '      "kind": "search",\n',
    '      "layer": "ACADEMIC",\n',
    '      "url": "https://export.arxiv.org/api/query?search_query=%28a'
    'bs:%22self-improving%22+OR+abs:%22self-evolving%22+OR+abs:%22agent'
    '+memory%22%29+AND+%28cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.SE%29&sortBy'
    '=submittedDate&sortOrder=descending&max_results=10"\n',
    '    }\n',
    '  ]\n',
    '}\n',
)
APPX_B = "".join(APPX_B_PARTS)

APPX_C_PARTS = (
    'G-S1 稽核檔產生規則（本文即位元組表；LF；UTF-8 無 BOM）\n',
    'key = si-test-key-g-s1-0123456789abcdef\n',
    'key_id = sha256(key 的 UTF-8 位元組) 十六進位前 8 碼\n',
    'audit_ref = 00000000-0000-4000-8000-0000000000a1\n',
    'user = admin\n',
    'role = ADMIN\n',
    'time = 2026-11-10T09:00:00+08:00\n',
    'kind = src-registry\n',
    'registry_text = 附錄 B golden 的位元組（UTF-8 解碼成字串）\n',
    'registry_sha256 = "sha256:" + 附錄 B golden 的 sha256 十六進位\n',
    'body = json.dumps({"schema_rev":1,"audit_ref":audit_ref,"kind":"sr'
    'c-registry","user":user,"role":"ADMIN","time":time,"registry_text"'
    ':registry_text,"registry_sha256":registry_sha256}, ensure_ascii=Fa'
    'lse, separators=(",",":"))\n',
    'body 鍵序即上式順序，不 sort_keys；緊湊（無空白）；非 ASCII 原樣；'
    '"/" 不跳脫；控制字元與引號依 JSON 標準跳脫（\\n、\\"、\\\\、其餘 \\u00x'
    'x 小寫十六進位）\n',
    'mac = HMAC-SHA256(key 的位元組, body 字串的 UTF-8 位元組) 小寫十六'
    '進位 64 碼\n',
    '外層檔 = json.dumps({"schema_rev":1,"kind":"src-registry","audit_r'
    'ef":audit_ref,"subject":null,"body":body,"key_id":key_id,"mac":mac'
    '}, ensure_ascii=False, separators=(",",":")) + 恰一個 LF\n',
    '外層鍵序即上式順序；subject 恆 null；SI 驗證不依賴排列（解析後對 b'
    'ody 字串驗 HMAC），本表只為 Console 與根層位元組逐位相等\n',
    '大小：registry_text <= 24576 bytes；外層檔 <= 65536 bytes\n',
    '黃金檔：tools/tests/fixtures/selfimproving/G-S1.audit.json（根層實'
    '作輪先產出並提交；產出後回填其 sha256，勘誤單獨 commit）\n',
    'Console 副本：AgentConsole/backend/src/test/resources/si/G-S1.audi'
    't.json（由主控原樣複製；與根層檔逐位元組相同）\n',
)
APPX_C = "".join(APPX_C_PARTS)

APPX_D_PARTS = (
    'https://xn--e1afmkfd.xn--p1ai/\tF\tF\n',
    'https://sub.xn--x.example.org/\tF\tF\n',
    'https://XN--abc.example/\tF\tF\n',
    'https://例え.jp/\tF\tF\n',
    'https://１２７.0.0.1/x\tF\tF\n',
    'https://example。org/x\tF\tF\n',
    'https://93.184.216.34/x\tT\tF\n',
    'https://127.0.0.1/x\tF\tF\n',
    'https://10.0.0.1/x\tF\tF\n',
    'https://[2606:4700:4700::1111]/x\tT\tF\n',
    'https://[::1]/x\tF\tF\n',
    'https://[::ffff:127.0.0.1]/x\tF\tF\n',
    'https://localhost/x\tF\tF\n',
    'https://app.localhost/x\tF\tF\n',
    'https://u:p@example.org/x\tF\tF\n',
    'https://example.org:8443/x\tF\tF\n',
    'https://example.org:80/x\tF\tF\n',
    'https://example.org:443/x\tT\tF\n',
    'https://example.org./x\tF\tF\n',
    'http://example.org/x\tF\tF\n',
    'https://EXAMPLE.ORG/x\tT\tF\n',
    'https://example.org/x#frag\tF\tF\n',
    'https://example.org\tT\tT\n',
    'https://example.org/a b\tF\tF\n',
    'https://example.org/x?q=1&r=%28a%29\tT\tT\n',
    'https://www.anthropic.com/engineering\tT\tT\n',
    'https://github.com/anthropics/anthropic-sdk-python/releases.atom\tT'
    '\tT\n',
    'https://raw.githubusercontent.com/anthropics/claude-code/main/CHAN'
    'GELOG.md\tT\tT\n',
    'https://code.claude.com/docs/en/hooks-guide\tT\tT\n',
    'https://code.claude.com/docs/en/hooks-guide.md\tT\tT\n',
    'https://code.claude.com/docs/llms.txt\tT\tT\n',
    'https://code.claude.com/docs/en/memory\tT\tT\n',
    'https://code.claude.com/docs/en/memory.md\tT\tT\n',
    'https://code.claude.com/docs/en/skills\tT\tT\n',
    'https://code.claude.com/docs/en/skills.md\tT\tT\n',
    'https://github.com/anthropics/claude-code/releases.atom\tT\tT\n',
    'https://github.com/openai/openai-agents-python/releases.atom\tT\tT\n',
    'https://github.com/openai/openai-agents-python/tags.atom\tT\tT\n',
    'https://platform.openai.com/docs/changelog\tT\tT\n',
    'https://developers.openai.com/api/docs/changelog.md\tT\tT\n',
    'https://www.anthropic.com/sitemap.xml\tT\tT\n',
    'https://export.arxiv.org/api/query?search_query=%28abs:%22self-imp'
    'roving%22+OR+abs:%22self-evolving%22+OR+abs:%22agent+memory%22%29+'
    'AND+%28cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.SE%29&sortBy=submittedDate'
    '&sortOrder=descending&max_results=10\tT\tT\n',
)
APPX_D = "".join(APPX_D_PARTS)

APPX_SHA = {
    "A": "3101fd6aaebaf80e51d5161b3dee4ea87e8c9b15d2ac1a09f7c58ce55f230afd",
    "B": "147fccd6a1b9efb61423579e26fbbc7437366a937806e239c69f334732aff0e8",
    "C": "91f137380530a5959138597add7b145ab7760611a7cca0ac1d7861062d321d87",
    "D": "25fd334dc97b8d135393849851962abfb54a621f11f9f0b1ba80eb27f4de1e89",
}

# --------------------------------------------------------------------------- px 建構器（TCS-P6 §3）
import contextlib  # noqa: E402
import hashlib  # noqa: E402
import hmac  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import socket  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import uuid  # noqa: E402
from pathlib import Path  # noqa: E402
from unittest import mock  # noqa: E402

import _selfimproving_fixtures as fx  # noqa: E402

from lib.selfimproving import fetch as si_fetch  # noqa: E402

KEY = "si-test-key-g-s1-0123456789abcdef"
REF = "00000000-0000-4000-8000-0000000000a1"
TIME = "2026-11-10T09:00:00+08:00"
MIRROR_REL = "docs/06_quality/SelfImproving_Protocol/research_registry.json"
G_S1_REL = "tools/tests/fixtures/selfimproving/G-S1.audit.json"
PUBLIC_IP = "93.184.216.34"


def registry_text(hosts, watch) -> str:
    """依 §9.2 規則序列化（`json.dumps(ensure_ascii=False, indent=2, sort_keys=True)+"\n"`）。"""
    obj = {"schema_rev": 1, "hosts": hosts, "watch": watch}
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha_of(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def golden_obj() -> dict:
    return json.loads(APPX_B)


def mutate(fn) -> str:
    """golden 的變體：`fn(obj)` 就地改，回正規化序列化文字。"""
    obj = golden_obj()
    fn(obj)
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def audit_bytes(*, kind="src-registry", text=None, ref=REF, user="admin", role="ADMIN",
                when=TIME, key=KEY, sha=None, body_extra=None, body_drop=(), mac=None,
                outer=None) -> bytes:
    """稽核檔位元組（附錄 C 規則：body 與外層鍵序固定、緊湊、非 ASCII 原樣、結尾一個 LF）。"""
    text = APPX_B if text is None else text
    reg_sha = sha or "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    body = {"schema_rev": 1, "audit_ref": ref, "kind": kind, "user": user, "role": role,
            "time": when, "registry_text": text, "registry_sha256": reg_sha}
    body.update(body_extra or {})
    for k in body_drop:
        body.pop(k, None)
    body_s = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    kb = key.encode("utf-8")
    outer_obj = {"schema_rev": 1, "kind": kind, "audit_ref": ref, "subject": None, "body": body_s,
                 "key_id": hashlib.sha256(kb).hexdigest()[:8],
                 "mac": mac or hmac.new(kb, body_s.encode("utf-8"), hashlib.sha256).hexdigest()}
    outer_obj.update(outer or {})
    return (json.dumps(outer_obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def g_s1_bytes() -> bytes:
    return audit_bytes()


def write_audit(home: Path, **kw) -> str:
    """寫 `<home>/console_audit/<ref>.json`；回 audit_ref。"""
    raw = audit_bytes(**kw)
    ref = kw.get("ref", REF)
    path = home / "console_audit" / f"{ref}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return ref


def new_ref() -> str:
    return str(uuid.uuid4())


def reg_event(text: str = None, *, ref=REF, when=TIME, seq_kw=None, **kw) -> dict:
    """手寫的 `research.registry` 事件（鍵序＝入帳事件）。"""
    text = APPX_B if text is None else text
    obj = json.loads(text)
    ev = {"kind": "research.registry", "by": "patrol", "audit_ref": ref,
          "audit_sha256": "sha256:" + "a" * 64,
          "key_id": hashlib.sha256(KEY.encode()).hexdigest()[:8],
          "decider": "admin", "carrier": "console", "audit_time": when,
          "registry_sha256": sha_of(text.encode("utf-8")), "hosts_n": len(obj["hosts"]),
          "watch_n": len(obj["watch"]), "watch_on": sum(1 for w in obj["watch"] if w["enabled"]),
          "changed": True}
    ev.update(kw)
    return ev


def set_params(r: Path, **kw) -> None:
    """改沙盒的 params.json，供 tools/lib/selfimproving/registry.py 讀取。"""
    p = r / "docs/06_quality/SelfImproving_Protocol/params.json"
    obj = json.loads(p.read_text(encoding="utf-8"))
    obj.update(kw)
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    p.write_text(text, encoding="utf-8", newline="\n")


def repo(*, mirror="golden", bound=True, run_open=True, extra=()) -> Path:
    """合成 repo：`fx.p1_base()`＋可選鏡像＋對應 `research.registry` 事件＋已開運轉。"""
    r = fx.p1_base()
    set_params(r, research_fetch_max=10)  # 真協定 params.json 的值（基線夾具的舊值是 8）
    text = APPX_B if mirror == "golden" else mirror
    events = []
    if text is not None:
        fx.putb(r, MIRROR_REL, text.encode("utf-8"))
        if bound:
            events.append(reg_event(text))
    if run_open:
        events.append(fx.run_open_ev(1))
    fx.write_events(r, [*events, *extra])
    return r


def response(status=200, headers=None, body=b"", ctype="text/plain; charset=utf-8") -> dict:
    return {"status": status, "headers": dict(headers or {}), "body": body, "ctype": ctype}


class _Conn:
    """假連線：只有 `settimeout`／`recv_into`／`sendall`／`close`（讀取層若改呼叫別的方法即紅）。"""

    def __init__(self, net, ip, port, sni) -> None:
        self.net, self.info, self.buf = net, (ip, port, sni), b""

    def settimeout(self, value) -> None:
        pass

    def sendall(self, data: bytes) -> None:
        head = data.decode("ascii").split("\r\n")
        path = head[0].split(" ")[1]
        host = next(h.split(": ", 1)[1] for h in head if h.lower().startswith("host:"))
        self.net.requests.append({"host": host, "path": path, "head": head, "conn": self.info})
        spec = self.net.responses(host, path)
        hdr = {"Content-Type": spec["ctype"], "Content-Length": str(len(spec["body"])),
               "Connection": "close", **spec["headers"]}
        hdr = {k: v for k, v in hdr.items() if v is not None}
        lines = [f"HTTP/1.1 {spec['status']} X"] + [f"{k}: {v}" for k, v in hdr.items()]
        self.buf = ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + spec["body"]

    def recv_into(self, buf) -> int:
        n = min(len(buf), len(self.buf))
        buf[:n], self.buf = self.buf[:n], self.buf[n:]
        return n

    def close(self) -> None:
        pass


class Net:
    """`px.net`：注入 `fetch.RESOLVER`／`CONNECTOR` 的兩個縫並記錄每次呼叫；測試不得真連網。"""

    def __init__(self, table=None, *, addrs=None, on_connect=None, errors=None) -> None:
        self.table, self.addrs, self.on_connect = table or {}, addrs or {}, on_connect
        self.errors = errors or {}
        self.resolved: list[str] = []
        self.connects: list[tuple] = []
        self.requests: list[dict] = []

    def responses(self, host, path) -> dict:
        got = self.table.get((host, path))
        got = got(host, path) if callable(got) else got
        return got or response(404, body=b"")

    def resolve(self, host: str) -> list[str]:
        self.resolved.append(host)
        got = self.addrs.get(host, [PUBLIC_IP])
        if isinstance(got, Exception):
            raise got
        if got and isinstance(got[0], list):  # 逐次呼叫的答案序列（DNS 答案會變）
            return got[min(len(self.resolved) - 1, len(got) - 1)]
        return got

    def connect(self, ip, port, server_hostname, deadline):
        self.connects.append((ip, port, server_hostname))
        if server_hostname in self.errors:
            raise self.errors[server_hostname]
        if self.on_connect:
            self.on_connect()
        return _Conn(self, ip, port, server_hostname)


@contextlib.contextmanager
def net(table=None, **kw):
    n = Net(table, **kw)

    def refuse(*_a, **_k):
        raise AssertionError("測試不得真連網")
    with (mock.patch.object(si_fetch, "RESOLVER", n.resolve),
          mock.patch.object(si_fetch, "CONNECTOR", n.connect),
          mock.patch.object(socket.socket, "connect", refuse)):
        yield n


def watch_entry(ident, url, *, expand_=None, kind="docs", enabled=True) -> dict:
    return {"added_at": "2026-11-10T00:00:00+00:00", "added_by": "t", "disabled_at": None,
            "disabled_by": None, "enabled": enabled, "expand": expand_, "extract": "x",
            "id": ident, "kind": kind, "layer": "INDUSTRY", "url": url}


def mirror_of(*watches) -> str:
    """以 `watch_entry` 的列組成合格鏡像（hosts 取自各 url 的主機）。"""
    hosts = sorted({w["url"].split("/")[2] for w in watches})
    rows = [{"host": h, "layer": "INDUSTRY", "list_kind": "FETCH", "min_interval_seconds": 5,
             "source": "ADMIN"} for h in hosts]
    return registry_text(rows, sorted(watches, key=lambda w: w["id"]))


# 舊（loopback＋舊表）P1 抓取 AT → 取代它的 P6 AT（TCS-SelfImproving-P6 §2、AC-SI-45-6）；
# 對照亦見 test_selfimproving_research_scan.py 檔頂。元 AT 判準據此豁免舊 id、並要求取代者存在。
SUPERSEDED_P1 = {
    "AT-130-2-1": "AT-630-2-E-2", "AT-130-2-E-1": "AT-645-1-2", "AT-130-2-E-2": "AT-645-6-3",
    "AT-130-2-E-3": "AT-630-7-E-3", "AT-130-2-E-4": "AT-645-6-4", "AT-130-2-E-5": "AT-630-7-E-1",
    "AT-130-2-E-6": "AT-630-7-E-1", "AT-130-2-E-7": "AT-645-1-6", "AT-130-2-E-8": "AT-645-1-6",
    "AT-130-2-E-9": "AT-645-1-7", "AT-130-3-1": "AT-630-3-1", "AT-130-3-E-1": "AT-630-3-E-1",
    "AT-130-3-E-2": "AT-630-3-E-5", "AT-130-3-E-3": "AT-630-3-E-6",
    "AT-130-3-E-4": "AT-630-2-E-1", "AT-130-5-1": "AT-630-5-1", "AT-130-5-E-1": "AT-630-3-E-1",
    "AT-130-5-E-2": "AT-630-3-E-2", "AT-130-5-E-3": "AT-630-3-E-4",
}


# ----------------------------------------------------------------- 回測夾具（TCS-P6 §3：BT 半）
SOP_REL = "docs/05_development/SelfImproving_Operations_SOP.md"
BT_DIR = "docs/06_quality/SelfImproving_Backtest"
BT_RESULTS = BT_DIR + "/results.jsonl"
_BT_DEF_HDR = fx.DEF_HDR
_BT_OBS_COORD = "`python tools/selfimproving.py check` rc=1"


def commit(repo: Path, files: dict, msg: str) -> str:
    """寫入（值為 None＝刪除）並提交；回 40 碼 commit（時間固定，相同輸入得相同 sha）。"""
    for rel, data in files.items():
        if data is None:
            (repo / rel).unlink(missing_ok=True)
        else:
            fx.putb(repo, rel, data if isinstance(data, bytes) else data.encode("utf-8"))
    return fx.commit_all(repo, msg)


def merge_commit(repo: Path, side_files: dict, msg: str) -> str:
    """從目前分支分出側枝提交 `side_files`、主線再前進一步、`--no-ff` 合併；回合併 commit。"""
    cur = fx.git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    fx.git(repo, "checkout", "-q", "-b", "side")
    commit(repo, side_files, "side")
    fx.git(repo, "checkout", "-q", cur)
    commit(repo, {"main_advance.txt": "x\n"}, "main-advance")
    fx.git(repo, "merge", "-q", "--no-ff", "-m", msg, "side")
    return fx.head(repo)


def _src(name: str, v: int) -> str:
    return f"# {name}\nVALUE = {v}\n"


def _obs_row(n: int, symptom: str, sha: str) -> list[str]:
    return [fx.obs_id(n), "2026-10-19 01:00", f"回測夾具 {n:03d}", symptom, _BT_OBS_COORD,
            "tooling", "P3", f"fixed@{sha[:12]}", "面=流程;來源=人;回報者=掌舵者"]


def bt_sop_section() -> str:
    """真 SOP 的〈反事實回測〉節（至下一個二級標題）：夾具 repo 的 SOP 只放它，避免整份 SOP 內的
    歷史 OBS 號在夾具帳本中懸空（`OBS-REF-DANGLING`）。"""
    text = (fx.ROOT / SOP_REL).read_bytes().decode("utf-8").replace("\r\n", "\n")
    m = re.search(r"(?ms)^## 反事實回測.*?(?=^## 無人運轉任務書範本)", text)
    if m is None:
        raise AssertionError("真 SOP 缺〈反事實回測〉節")
    return m.group(0)


def bt_repo(*, matrix: bool = True) -> tuple[Path, dict]:
    """真 git 的回測夾具 repo（`fx.p1_base()` 之上多個 commit）；回（repo, 各 commit 與案例對照）。

    `matrix=True`：另含各種排除原因的修復 commit（OBS 11 起）；`matrix=False`：只含合格案例，
    使 `check` 可全綠（含偽造 sha 的列會使 `FIXED-SHA-UNRESOLVED`）。回傳的 `info["obs"]`／
    `info["def"]` 為 id → 期望原因（`None`＝合格）。"""
    r = fx.p1_base()
    fx.put(r, SOP_REL, bt_sop_section())
    base = {f"src/{n}.py": _src(n, 1) for n in "abcde"}
    base.update({f"src/m{i}.py": _src(f"m{i}", 1) for i in range(1, 10)})
    base.update({"tests/test_a.py": "t\n", "docs/y.md": "y\n", "src/d.py": _src("d", 1)})
    commit(r, base, "base code")
    info: dict = {"obs": {}, "def": {}}
    f1 = commit(r, {"src/a.py": _src("a", 2), "tests/test_a2.py": "t\n", "docs/y.md": "z\n"}, "f1")
    f2 = commit(r, {"src/b.py": _src("b", 2), "src/c.py": _src("c", 2)}, "f2")
    fd = commit(r, {"src/e.py": _src("e", 2)}, "fd")
    info.update(f1=f1, f2=f2, fd=fd)
    obs = [(11, "回測症狀一：計數偏差", f1, None), (12, "回測症狀二：兩處同時錯", f2, None)]
    if matrix:
        info["nocode"] = commit(r, {"docs/y.md": "q\n", "tests/test_a.py": "t2\n"}, "nocode")
        info["newonly"] = commit(r, {"src/new.py": "x\n"}, "newonly")
        info["over"] = commit(r, {f"src/m{i}.py": "# changed\n" for i in range(1, 10)}, "over")
        info["named"] = commit(r, {"src/d.py": _src("d", 2)}, "named")
        info["merge"] = merge_commit(r, {"src/side.py": "s\n"}, "merge")
        sha_sym = "回測症狀：fix 於 {sha7} 之後"
        obs += [(13, "回測症狀：只動文件", info["nocode"], "no-code-file"),
                (14, "回測症狀：只新增檔", info["newonly"], "no-code-file"),
                (15, "回測症狀：改了九個檔", info["over"], "files-over"),
                (16, "回測症狀：壞在 src/d.py 附近", info["named"], "symptom-names-file"),
                (17, "回測症狀：合併修復", info["merge"], "merge"),
                (18, sha_sym.format(sha7=info["f2"][:7]), info["f2"], "symptom-has-sha"),
                (19, "回測症狀：假 commit", "deadbeefcafe0000", "commit-missing"),
                (20, "", info["f1"], "symptom-empty")]
    rows = [list(x) for x in fx.base_rows()]
    root_commit = fx.git(r, "rev-list", "--max-parents=0", "HEAD").split()[0]
    rows[1][7] = f"fixed@{root_commit[:12]}"  # 基線列 002 指向根 commit（無 first parent）
    info["obs"][fx.obs_id(2)] = "commit-missing"
    for n, sym, sha, why in obs:
        rows.append(_obs_row(n, sym, sha))
        info["obs"][fx.obs_id(n)] = why
    fx.put(r, fx.LEDGER, fx.render_ledger(rows))
    defrows = [[fx.def_id(1), "2026-09-01", "夾具", "tools/lib/si_demo.py:12", "P2", "-",
                "fixed@abc1234"],
               [fx.def_id(2), "2026-09-02", "夾具", "回測症狀 DEF：另一個計數現象", "P2", "-",
                "fixed@" + fd[:12]]]
    fx.put(r, fx.DEFLOG, "\n".join([_BT_DEF_HDR, "|---|---|---|---|---|---|---|",
                                    *[fx.line(x) for x in defrows]]) + "\n")
    info["def"] = {fx.def_id(1): "commit-missing", fx.def_id(2): None}
    info["head"] = fx.commit_all(r, "ledgers")
    return r, info


def write_cases(repo: Path, cases: list[dict], version: int = 1) -> Path:
    """把 `cases` 以正規化序列化寫成 `cases-v<version>.json`（不 commit）。"""
    obj = {"schema_rev": 1, "version": version, "generated_at": "2026-11-10T09:00:00+08:00",
           "head_sha": "0" * 40, "ledgers": {"obs_sha256": "sha256:" + "0" * 64,
                                             "def_sha256": "sha256:" + "0" * 64},
           "cases": sorted(cases, key=lambda c: c["id"]), "excluded": []}
    path = repo / BT_DIR / f"cases-v{version}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
                      + "\n").encode("utf-8"))
    return path


def synthetic_cases(repo: Path, n: int) -> list[dict]:
    """`n` 個合成案例：每案一個真 commit 當 `pre_commit`（供 `prepare` 建快照）。"""
    out = []
    for i in range(1, n + 1):
        pre = commit(repo, {f"src/s{i}.py": _src(f"s{i}", 1)}, f"pre{i}")
        fix = commit(repo, {f"src/s{i}.py": _src(f"s{i}", 2)}, f"fix{i}")
        out.append({"id": fx.obs_id(900 + i), "source": "OBS", "symptom": f"合成症狀 {i}",
                    "fix_commit": fix, "pre_commit": pre, "changed_files": [f"src/s{i}.py"]})
    return out


def line(kind: str, text: str = "", *, name: str = "", input_: dict | None = None,
         cwd: str | None = None, ts: str = "2026-11-10T09:00:00.000Z") -> dict:
    """子代理逐字稿的一行（只造結構，不抄真實內容）：`user`／`tool`（assistant 的 tool_use）／
    `say`（assistant 的 text 區塊）。"""
    if kind == "user":
        out = {"type": "user", "message": {"role": "user", "content": text}}
    elif kind == "tool":
        out = {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_x", "name": name, "input": input_ or {}}]}}
    else:
        out = {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": text}]}}
    out["timestamp"] = ts
    if cwd is not None:
        out["cwd"] = cwd
    return out


def clean_lines(nonce: str, snap: Path, answer: str = "{}") -> list[dict]:
    """合規的子代理逐字稿：user 行含 nonce、Read 與 Grep 都在快照內、末行為含 text 的 assistant。"""
    return [line("user", f"任務碼：{nonce}"),
            line("tool", name="Read", input_={"file_path": str(snap / "src" / "a.py")}),
            line("tool", name="Grep", input_={"path": str(snap), "pattern": "VALUE"}),
            line("say", answer)]


@contextlib.contextmanager
def claude_home(repo: Path, sid: str, agents: dict, *, model: str | None = "sonnet",
                folder: str = "subagents"):
    """暫存 `claude_home()`（`CLAUDE_CONFIG_DIR`）下造
    `projects/<slug>/<sid>/<folder>/agent-<id>.jsonl`；
    `agents`＝{agent_id: [line…]}。測試不讀真實家目錄。"""
    root = Path(tempfile.mkdtemp(prefix="si_ch_"))
    base = root / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(repo.resolve())) / sid / folder
    base.mkdir(parents=True)
    for aid, lines in agents.items():
        raw = "".join(json.dumps({"agentId": aid, "sessionId": sid, "isSidechain": True,
                                  "cwd": str(repo), **ln}, ensure_ascii=False) + "\n"
                      for ln in lines)
        (base / f"agent-{aid}.jsonl").write_bytes(raw.encode("utf-8"))
        if model:
            (base / f"agent-{aid}.meta.json").write_bytes(
                json.dumps({"agentType": "general-purpose", "model": model}).encode("utf-8"))
    try:
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(root)}):
            yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ----------------------------------------------------------------- 範圍守衛（有明確基準才啟用）
def scope_base() -> str | None:
    """範圍守衛的基準 commit：`SI_SCOPE_BASE`（相容舊名 `SI_P4_BASE_SHA`）；未設＝None＝守衛不啟用。

    WHY：舊寫法以 `HEAD~1` 對整個工作樹比對，只要最新 commit 或工作樹碰到 `AgentConsole/**` 就紅
    ——守衛本意是「該鍵的實作 commit 不越界」，常駐執行等於對所有後續工作下隱形限制。"""
    return os.environ.get("SI_SCOPE_BASE") or os.environ.get("SI_P4_BASE_SHA") or None


def scope_tip() -> str:
    """範圍守衛的終點 commit：`SI_SCOPE_TIP`（預設 `HEAD`）；兩把鍵的 commit 交錯時，QA 可只對
    單一 commit 驗（例 `SI_SCOPE_BASE=<sha>^`、`SI_SCOPE_TIP=<sha>`）。"""
    return os.environ.get("SI_SCOPE_TIP") or "HEAD"


def committed_names(root: Path, base: str, tip: str | None = None) -> set[str]:
    """`<base>..<tip>`（`tip` 缺省＝`scope_tip()`）的**已提交**差異路徑（不含工作樹與未追蹤檔）；
    `base` 或 `tip` 解不開＝拋 AssertionError。"""
    tip = tip or scope_tip()
    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(root), "-c", "core.quotepath=false", *args],
                              capture_output=True, encoding="utf-8", errors="replace",
                              check=False)
    for label, rev in (("基準", base), ("終點", tip)):
        if run("rev-parse", "--verify", "--quiet", rev + "^{commit}").returncode != 0:
            raise AssertionError(f"範圍守衛{label} {rev!r} 不是可解析的 commit")
    cp = run("diff", "--name-only", base, tip)
    if cp.returncode != 0:
        raise AssertionError(f"git diff 失敗：{cp.stderr}")
    return {n for n in cp.stdout.splitlines() if n.strip()}


def scope_verdict(names: set[str], allowed, frozen=(), exempt=()
                  ) -> tuple[bool, list[str], list[str]]:
    """（是否觸及允許集合, 允許集合之外的路徑, 落在凍結前綴的路徑）；未觸及＝守衛不觸發。"""
    touched = any(rx.match(n) for n in names for rx in allowed)
    outside = sorted(n for n in names if not any(rx.match(n) for rx in allowed))
    frozen_hits = sorted(n for n in names if n.startswith(tuple(frozen))
                         and not n.startswith(tuple(exempt)))
    return touched, outside, frozen_hits


def scope_fixture(base_files: dict, head_files: dict, later_files: dict | None = None
                  ) -> tuple[Path, str]:
    """暫存 git repo：基準 commit 後再提交 `head_files`，可再提交 `later_files`（使 HEAD 晚於
    `HEAD~1`，驗終點早於 HEAD）；回（repo, 基準 sha）。呼叫端負責清理。"""
    root = Path(tempfile.mkdtemp(prefix="si_scope_"))
    cfg = root / "gitconfig"
    cfg.write_bytes(b"[gc]\n\tauto=0\n")
    env = {**os.environ, "GIT_CONFIG_GLOBAL": str(cfg), "GIT_CONFIG_NOSYSTEM": "1"}
    repo = root / "r"
    repo.mkdir()

    def git(*args: str) -> str:
        cp = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c",
                             "user.email=t@example.com", "-c", "commit.gpgsign=false", "-c",
                             "core.autocrlf=false", *args], capture_output=True, encoding="utf-8",
                            errors="replace", env=env, check=True)
        return cp.stdout.strip()

    git("init", "-q")
    for step, files in enumerate((base_files, head_files, *([later_files] if later_files else []))):
        for rel, text in files.items():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_bytes(text.encode("utf-8"))
        git("add", "-A")
        git("commit", "-q", "--allow-empty", "-m", f"step{step}")
        if step == 0:
            base = git("rev-parse", "HEAD")
    return repo, base
