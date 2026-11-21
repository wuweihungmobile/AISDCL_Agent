"""RV-PX 家族共用 helper（不登記案例）：載具 E（T5 端點替身＝本機 TLS CONNECT 代理）與沙盒環境組裝。

載具 E 的結構（TCS-WorkProgress §10.3「載具」表）：被測行程（`session_resume_planner.py --pace`）以
`urllib.request.urlopen` 打 `https://api.anthropic.com/api/oauth/usage`；預設 opener 讀 `HTTPS_PROXY`，
預設 SSL context 讀 `SSL_CERT_FILE`。本替身是一個 CONNECT 代理：回 200 後以自簽 CA 簽發的
`api.anthropic.com` 葉憑證做伺服端 TLS 交握，逐筆記錄請求（方法、路徑、時間、是否帶 Authorization），
回應由案例給的腳本決定。CA 與假憑證檔只放沙盒；`HTTPS_PROXY`／`SSL_CERT_FILE`／`CLAUDE_CONFIG_DIR`
只注入沙盒子行程環境，真 token 永不送出（沙盒 HOME 放的是假 token）。
"""  # noqa: E501

from __future__ import annotations

import contextlib
import json
import socket
import ssl
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..sandbox import Sandbox
from . import CaseContext

FAKE_TOKEN = "sk-ant-oat01-RVFAKE-0123456789abcdefghijklmnopqrstuvwxyz"
HOST = "api.anthropic.com"


def ev(ctx: CaseContext, key: str, value: object) -> None:
    """斷言鍵證據：`鍵=值`（空值不寫，讓執行器的 `assert_missing` 判準成立）。"""
    text = str(value).strip()
    if not text:
        raise AssertionError(f"斷言鍵 {key} 沒有可觀測值（空值不得入帳）")
    ctx.evidence(f"{key}={text}")


def reset_iso(minutes_left: float) -> str:
    return (datetime.now(UTC) + timedelta(minutes=minutes_left)).isoformat(timespec="seconds")


def usage_payload(**axes: tuple[float, float]) -> dict:
    """`{five_hour: (pct, 距 reset 分鐘), …}` → 端點 JSON（頂層桶形：`utilization`＋`resets_at`）。"""  # noqa: E501
    return {k: {"utilization": pct, "resets_at": reset_iso(mins)} for k, (pct, mins) in axes.items()}  # noqa: E501


# ───────────────────────────────────────────────────────────────── 憑證與 CA
def _make_pki(d: Path) -> tuple[Path, Path, Path]:
    from cryptography import x509  # noqa: PLC0415
    from cryptography.hazmat.primitives import hashes, serialization  # noqa: PLC0415
    from cryptography.hazmat.primitives.asymmetric import ec  # noqa: PLC0415
    from cryptography.x509.oid import NameOID  # noqa: PLC0415

    now = datetime.now(UTC)

    def name(cn: str) -> x509.Name:
        return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])

    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca = (x509.CertificateBuilder().subject_name(name("RealVerify Test CA")).issuer_name(name("RealVerify Test CA"))  # noqa: E501
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=2))
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
          .add_extension(x509.KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True, content_commitment=False,  # noqa: E501
                                       key_encipherment=False, data_encipherment=False, key_agreement=False,  # noqa: E501
                                       encipher_only=False, decipher_only=False), critical=True)
          .sign(ca_key, hashes.SHA256()))
    leaf_key = ec.generate_private_key(ec.SECP256R1())
    leaf = (x509.CertificateBuilder().subject_name(name(HOST)).issuer_name(ca.subject)
            .public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=2))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(HOST)]), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(ca_key, hashes.SHA256()))
    ca_pem, cert_pem, key_pem = d / "ca.pem", d / "leaf.pem", d / "leaf.key"
    ca_pem.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert_pem.write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    key_pem.write_bytes(leaf_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,  # noqa: E501
                                               serialization.NoEncryption()))
    return ca_pem, cert_pem, key_pem


Responder = Callable[[int, dict], tuple[int, dict, object]]


class T5Stub:
    """T5 端點替身。`responder(第幾筆請求(0 起), 請求 dict)` → `(status, headers, json body 或 None)`。"""  # noqa: E501

    def __init__(self, root: Path, responder: Responder):
        self.root = root
        self.responder = responder
        self.requests: list[dict] = []  # {n, method, path, t, has_auth, raw_len}
        self.connects: list[float] = []
        self._lock = threading.Lock()
        self._stop = False
        d = root / "t5stub"
        d.mkdir(parents=True, exist_ok=True)
        self.ca_pem, cert, key = _make_pki(d)
        self._ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self._ctx.load_cert_chain(str(cert), str(key))
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("127.0.0.1", 0))
        self._srv.listen(16)
        self.port = self._srv.getsockname()[1]
        self._th = threading.Thread(target=self._accept, daemon=True)
        self._th.start()

    # -- 伺服端 --
    def _accept(self) -> None:
        while not self._stop:
            try:
                conn, _ = self._srv.accept()
            except OSError:
                return
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    @staticmethod
    def _read_head(sock) -> bytes:
        buf = b""
        while b"\r\n\r\n" not in buf and len(buf) < 65536:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        return buf

    def _serve(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(15)
            head = self._read_head(conn)
            first = head.split(b"\r\n", 1)[0].decode("latin-1")
            if not first.startswith("CONNECT "):
                conn.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n")
                return
            with self._lock:
                self.connects.append(time.time())
            conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            tls = self._ctx.wrap_socket(conn, server_side=True)
            req = self._read_head(tls)
            line = req.split(b"\r\n", 1)[0].decode("latin-1").split(" ")
            headers = req.decode("latin-1").lower()
            with self._lock:
                n = len(self.requests)
                rec = {"n": n, "method": line[0], "path": line[1] if len(line) > 1 else "", "t": time.time(),  # noqa: E501
                       "has_auth": "authorization: bearer" in headers, "raw_len": len(req)}
                self.requests.append(rec)
            status, hdrs, body = self.responder(n, rec)
            raw = json.dumps(body).encode() if body is not None else b""
            lines = [f"HTTP/1.1 {status} X", f"Content-Length: {len(raw)}", "Connection: close",
                     "Content-Type: application/json"] + [f"{k}: {v}" for k, v in hdrs.items()]
            tls.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + raw)
            tls.close()
        except (OSError, ssl.SSLError):
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def stop(self) -> None:
        self._stop = True
        try:
            self._srv.close()
        except OSError:
            pass

    # -- 觀測 --
    def count(self, method: str | None = None) -> int:
        with self._lock:
            return len([r for r in self.requests if method is None or r["method"] == method])


def t5_sandbox_env(sb: Sandbox, stub: T5Stub | None, *, creds: bool = True, **extra) -> dict:
    """沙盒子行程環境：假憑證放 `CLAUDE_CONFIG_DIR`、代理／CA 只在此注入；快取與痕跡全在沙盒。"""
    home = sb.root / "claude_home"
    home.mkdir(exist_ok=True)
    # WHY：真機憑證住 ~/.claude（不在專案工作樹）；沙盒為免殘留放在沙盒根內，所以要讓 git 忽略它，
    # 否則引擎的「髒工作樹搶救」會把未追蹤的憑證檔內容寫進 checkpoint 的 patch（沙盒才有的假象）。
    excl = sb.root / ".git" / "info" / "exclude"
    if excl.parent.is_dir() and "claude_home/" not in (excl.read_text(encoding="utf-8") if excl.is_file() else ""):  # noqa: E501
        excl.write_text((excl.read_text(encoding="utf-8") if excl.is_file() else "") + "\nclaude_home/\nt5stub/\n", encoding="utf-8")  # noqa: E501
    if creds:
        (home / ".credentials.json").write_text(
            json.dumps({"claudeAiOauth": {"accessToken": FAKE_TOKEN, "refreshToken": "rv-fake-refresh",  # noqa: E501
                                          "expiresAt": 4102444800000}}), encoding="utf-8")
    tmp = sb.root / "tmp"
    tmp.mkdir(exist_ok=True)
    e = sb.env()
    e.pop("AUTOSDD_UNATTENDED", None)
    for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "NO_PROXY", "no_proxy"):  # noqa: E501
        e.pop(k, None)
    e.update({"CLAUDE_CONFIG_DIR": str(home), "AUTOSDD_QUOTA_CACHE_DIR": str(sb.root / "qcache"),
              "TEMP": str(tmp), "TMP": str(tmp), "PYTHONDONTWRITEBYTECODE": "1"})
    if stub is not None:
        e.update({"HTTPS_PROXY": f"http://127.0.0.1:{stub.port}", "SSL_CERT_FILE": str(stub.ca_pem),
                  "REQUESTS_CA_BUNDLE": str(stub.ca_pem)})
    e.update(extra)
    return e


ORG_HEADERS = {"anthropic-organization-id": "rv-org-1", "anthropic-workspace-id": "rv-ws-1"}


@contextlib.contextmanager
def t5(sb: Sandbox, responder: Responder):
    """載具 E 的生命週期：案例內 `with t5(sb, responder) as stub:`，離開時關閉替身。"""
    stub = T5Stub(sb.root, responder)
    try:
        yield stub
    finally:
        stub.stop()


def ok_responder(payload: dict | Callable[[], dict], headers: dict | None = None) -> Responder:
    """每筆都回 200＋`payload`（可為 callable，每筆現算 `resets_at`）。"""
    return lambda n, r: (200, dict(headers or ORG_HEADERS), payload() if callable(payload) else payload)  # noqa: E501


# ───────────────────────────────────────────────────────────────── 案例登記（附錄逐列宣告）
_CASE_META: dict[str, tuple[str, tuple[str, ...], int | None]] = {}


def px(case_id: str, carrier: str, asserts: tuple[str, ...], *, refs: tuple[str, ...] = (),
       long: bool = False, sched: bool = False, min_wall: int | None = None):
    """登記 RV-PX 案例並把 TCS §10.3 附錄的 `CARRIER`／`ASSERTS` 掛在函式上。

XX已以 `ev()` 寫出非空 `鍵=值` 證據，缺任何一鍵 ⇒ 判 fail。"""
    from . import case  # noqa: PLC0415

    def deco(fn):
        def wrapped(ctx: CaseContext) -> None:
            fn(ctx)
            have = {e.split("=", 1)[0] for e in ctx.evidences if "=" in e}
            missing = [k for k in asserts if k not in have]
            if missing:
                raise AssertionError(f"assert_missing:{','.join(missing)}")
        wrapped.__name__ = fn.__name__
        wrapped.__doc__ = fn.__doc__
        wrapped.CARRIER = carrier
        wrapped.ASSERTS = asserts
        wrapped.MIN_WALL_SECONDS = min_wall
        _CASE_META[case_id] = (carrier, asserts, min_wall)
        return case(case_id, "prd_px", refs=refs, long=long, sched=sched)(wrapped)
    return deco
