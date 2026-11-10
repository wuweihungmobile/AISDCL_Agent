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
import socket  # noqa: E402
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
