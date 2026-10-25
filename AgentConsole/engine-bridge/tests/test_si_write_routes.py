"""Bridge 的 SI 寫入面：稽核檔落地、三個寫入端點、唯讀預檢（TCS-SelfImprovingDecide-P2b：
AT-950-1-1、AT-950-1-2、AT-950-1-E-1、AT-950-1-E-2、AT-935-3-E-2、AT-950-2-1、AT-950-2-2、
AT-950-2-3、AT-950-2-E-1～E-4、AT-950-3-2、AT-950-3-E-2）。

斷言重點：寫入面啟用要權杖與稽核目錄兩者皆有設；`store_audit` 獨佔建檔、不覆寫、位元組原樣、
失敗不洩漏路徑且不留半成品；三個寫入端點的閘門序（停用→權杖→本文大小與 JSON→外層形態→落檔）；
Bridge 不解內層 body、不驗簽；DELETE／PUT／PATCH 對全部 `/si/` 路徑一律 405；validate 不需權杖、
rc 0 與 1 皆 200、違規請求不啟動子行程。全部用假 CLI 樹與 tmp 稽核目錄，不碰真帳本。
AT 內不引用其他 AT 的 ID。
"""
from __future__ import annotations

import errno
import hashlib
import hmac
import json
import os
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from app import security, si_audit
from app.errors import ApiError
from app.settings import Settings, SettingsError, load_settings
from tests import si_repo_support as sup
from tests.fake_si import make_fake_si, read_calls, set_control

T0 = sup.T0
#: 格式邊界用的 PROP 號：刻意在執行期組字串、不寫成字面值（它們不是真帳本上的號；根層 ref.obs 判準
#: 與本 Feature 的夾具規則只准真號出現在原始碼字面中）。
SHORT_PROP = "PROP-SI-" + "04"           # 少於三位數字：格式不合
FOUR_DIGIT_PROP = "PROP-SI-" + "1234"    # 四位數字：格式合格
DECIDE = "/si/proposals/PROP-SI-004:decide"
OBS_ADD = "/si/observations"
OBS_CLOSE = "/si/observations/OBS-SI-005:close"
VALIDATE = "/si/observations:validate"
#: 端點表：名稱 → (路徑, 外層 kind, 外層 subject)。
ENDPOINTS: dict[str, tuple[str, str, str | None]] = {
    "decide": (DECIDE, "decide", "PROP-SI-004"),
    "obs-add": (OBS_ADD, "obs-add", None),
    "obs-close": (OBS_CLOSE, "obs-close", "OBS-SI-005"),
}


def ref_of(n: int) -> str:
    return f"c0000000-0000-4000-8000-{n:012d}"


def outer_dict(kind: str, subject: str | None, ref: str, body: str = "未解析的 body 文字") -> dict[
        str, Any]:
    return {"schema_rev": 1, "kind": kind, "audit_ref": ref, "subject": subject, "body": body,
            "key_id": sup.K0_ID, "mac": "0" * 64}


def dump(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def valid_outer(name: str, n: int, **over: Any) -> bytes:
    """端點 `name` 的合法外層位元組（ref 取 `ref_of(n)`）；`over` 的值為 `...` 表示刪掉該鍵。"""
    _path, kind, subject = ENDPOINTS[name]
    obj = outer_dict(kind, subject, ref_of(n))
    for key, value in over.items():
        if value is ...:
            obj.pop(key, None)
        else:
            obj[key] = value
    return dump(obj)


def listing(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir())


def under(path: Any, directory: Path) -> bool:
    """`path`（str／Path）的父目錄是否為 `directory`；其他型別（bytes、fd）一律 False，
    讓測試替身只影響稽核目錄內的檔案。"""
    try:
        return Path(os.fspath(path)).parent == directory
    except TypeError:
        return False


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    return make_fake_si(tmp_path)


@pytest.fixture
def audit_dir(tmp_path: Path) -> Path:
    path = tmp_path / "audit-bind-7f3a"      # 名稱獨特：斷言「不洩漏路徑」時不會與一般用語相撞
    path.mkdir()
    return path


@pytest.fixture
def live(make_bridge: Callable[..., Any], settings: Settings, fake: Path, audit_dir: Path) -> Any:
    """寫入面啟用的活 Bridge（`BR-LIVE`）：假 CLI 樹、權杖 `T0`、稽核目錄 `AD`。"""
    return make_bridge(replace(settings, si_root=fake, si_write_token=T0, si_audit_dir=audit_dir))


def post(live_bridge: Any, path: str, raw: bytes, token: str | bytes | None = T0) -> Any:
    """帶 `X-Bridge-Token`（`bytes` 值可送非 ASCII 位元組：httpx 對 str 標頭值只收 ASCII）。"""
    headers: dict[str, str | bytes] = {"Content-Type": "application/json"}
    if token is not None:
        headers["X-Bridge-Token"] = token
    return live_bridge.client.post(path, content=raw, headers=headers)


# ── AT-950-1-1：設定解析與寫入面啟用條件 ────────────────────────────────────────────────────────
def test_AT_950_1_1_settings_resolve_the_write_token_and_the_audit_dir(
        tmp_path: Path) -> None:
    workspace = tmp_path / "ws"

    def load(env: dict[str, str]) -> Settings:
        return load_settings({"ENGINE_WORKSPACE": str(workspace), **env})

    secret31, secret32 = "s" * 31, "k" * 32
    ok_audit = tmp_path / "audit-dir"
    # 權杖：未設、全空白＝None；32 字元通過
    assert load({}).si_write_token is None
    assert load({"BRIDGE_SI_WRITE_TOKEN": "   "}).si_write_token is None
    assert load({"BRIDGE_SI_WRITE_TOKEN": secret32}).si_write_token == secret32
    # 權杖：31 字元、佔位、含 `<YOUR_`（不分大小寫）＝SettingsError，訊息不含值本身
    bad_tokens = {"31-chars": secret31, "placeholder": "<YOUR_SI_TOKEN>",
                  "contains-your": "x" * 40 + "<your_secret>" + "y" * 5}
    for name, value in bad_tokens.items():
        with pytest.raises(SettingsError) as caught:
            load({"BRIDGE_SI_WRITE_TOKEN": value})
        text = str(caught.value)
        assert "BRIDGE_SI_WRITE_TOKEN" in text, name
        assert value not in text, f"{name}：錯誤訊息不得帶權杖值"
    # 稽核目錄：未設、空白＝None；檔案系統根＝SettingsError；相對與絕對路徑 resolve 為絕對路徑
    assert load({}).si_audit_dir is None
    assert load({"BRIDGE_SI_AUDIT_DIR": "   "}).si_audit_dir is None
    with pytest.raises(SettingsError) as caught:
        load({"BRIDGE_SI_AUDIT_DIR": str(Path(tmp_path.anchor))})
    assert "BRIDGE_SI_AUDIT_DIR" in str(caught.value)
    relative = load({"BRIDGE_SI_AUDIT_DIR": os.path.join("some", "..", "rel-audit")})
    assert relative.si_audit_dir == Path(os.path.join("some", "..", "rel-audit")).resolve()
    assert relative.si_audit_dir is not None and relative.si_audit_dir.is_absolute()
    absolute = load({"BRIDGE_SI_AUDIT_DIR": str(ok_audit)})
    assert absolute.si_audit_dir == ok_audit.resolve(), "不檢查存在性（目錄尚未建立也通過）"
    assert not ok_audit.exists(), "設定解析不得建立目錄"
    # 不進白名單根：預設與明列兩種都不含
    pinned = load({"BRIDGE_SI_AUDIT_DIR": str(ok_audit),
                   "BRIDGE_ALLOWED_PATH_ROOTS": str(workspace)})
    assert pinned.allowed_path_roots == (workspace.resolve(),)
    assert ok_audit.resolve() not in absolute.allowed_path_roots
    # repr 不含權杖
    cfg = load({"BRIDGE_SI_WRITE_TOKEN": secret32, "BRIDGE_SI_AUDIT_DIR": str(ok_audit)})
    assert secret32 not in repr(cfg) and "si_write_token" not in repr(cfg)
    # 寫入面啟用＝兩者皆非 None（四種組合）
    matrix = {(False, False): {}, (True, False): {"BRIDGE_SI_WRITE_TOKEN": secret32},
              (False, True): {"BRIDGE_SI_AUDIT_DIR": str(ok_audit)},
              (True, True): {"BRIDGE_SI_WRITE_TOKEN": secret32,
                             "BRIDGE_SI_AUDIT_DIR": str(ok_audit)}}
    for (has_token, has_dir), env in matrix.items():
        got = load(env)
        assert (got.si_write_token is not None, got.si_audit_dir is not None) == (
            has_token, has_dir)
        assert got.si_write_enabled is (has_token and has_dir), env


# ── AT-950-1-2：`store_audit` 原樣寫入 ─────────────────────────────────────────────────────────
def test_AT_950_1_2_store_audit_writes_the_bytes_verbatim(
        audit_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    g3 = sup.read_audit_golden("G3")
    variants = [g3, g3 + b"\n", g3 + b"\r\n"]
    seen: list[int] = []
    # 稽核檔 fd 的生命週期事件 (動作, fd, 當下檔案大小)。fsync 是「落檔即持久」的承諾（主機端 CLI
    # 隨後才讀），所以鎖住它：被呼叫、恰一次、寫完全部位元組之後、關閉之前。spy 內讀 fstat：
    # 大小等於 raw 長度＝全部位元組已寫入；fstat 能成功＝fd 此刻仍開著。
    events: list[tuple[str, int, int]] = []
    opened: dict[str, int] = {}
    audit_fds: set[int] = set()
    real_open, real_fsync, real_close = os.open, os.fsync, os.close

    def recorder(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        fd = real_open(path, flags, *args, **kwargs)
        if under(path, audit_dir):
            seen.append(flags)
            opened[Path(os.fspath(path)).name] = fd
            audit_fds.add(fd)
        return fd

    def fsync_spy(fd: int) -> None:
        if fd in audit_fds:
            events.append(("fsync", fd, os.fstat(fd).st_size))
        real_fsync(fd)

    def close_spy(fd: int) -> None:
        if fd in audit_fds:
            events.append(("close", fd, os.fstat(fd).st_size))
            audit_fds.discard(fd)
        real_close(fd)

    monkeypatch.setattr(os, "open", recorder)
    monkeypatch.setattr(os, "fsync", fsync_spy)
    monkeypatch.setattr(os, "close", close_spy)
    for i, raw in enumerate(variants, start=1):
        ref = ref_of(i)
        events.clear()
        assert si_audit.store_audit(audit_dir, ref, raw) is None, "函式不回傳路徑"
        fd = opened[f"{ref}.json"]
        assert events == [("fsync", fd, len(raw)), ("close", fd, len(raw))], (
            "稽核檔 fd 的順序須是：fsync 恰一次（此刻檔案大小＝raw 長度）→ 關閉："
            f"{events}")
        written = (audit_dir / f"{ref}.json").read_bytes()
        assert hashlib.sha256(written).digest() == hashlib.sha256(raw).digest()
        assert written == raw
        assert len(listing(audit_dir)) == i, "目錄內檔案數等於呼叫次數（無暫存檔）"
    assert listing(audit_dir) == sorted(f"{ref_of(i)}.json" for i in (1, 2, 3))
    assert len(seen) == 3
    for flags in seen:
        assert flags & os.O_CREAT and flags & os.O_EXCL and flags & os.O_WRONLY
        assert flags & getattr(os, "O_BINARY", 0) == getattr(os, "O_BINARY", 0)


# ── AT-950-1-E-1：同名不覆寫、八執行緒搶同名恰一成功 ────────────────────────────────────────────
def test_AT_950_1_E_1_an_existing_audit_file_is_never_overwritten(audit_dir: Path) -> None:
    ref = ref_of(1)
    si_audit.store_audit(audit_dir, ref, b"raw-one")
    with pytest.raises(ApiError) as caught:
        si_audit.store_audit(audit_dir, ref, b"raw-two")
    assert (caught.value.status_code, caught.value.body["reason"]) == (409, "si_audit_exists")
    assert (audit_dir / f"{ref}.json").read_bytes() == b"raw-one"
    assert listing(audit_dir) == [f"{ref}.json"]


def test_AT_950_1_E_1_eight_threads_racing_for_one_name_produce_exactly_one_winner(
        audit_dir: Path) -> None:
    ref = ref_of(2)
    barrier = threading.Barrier(8)

    def attempt(i: int) -> tuple[int, int]:
        barrier.wait(timeout=30)
        try:
            si_audit.store_audit(audit_dir, ref, f"raw-from-thread-{i}".encode())
        except ApiError as exc:
            return i, exc.status_code
        return i, 200

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = [f.result() for f in [pool.submit(attempt, i) for i in range(8)]]
    winners = [i for i, status in results if status == 200]
    assert len(winners) == 1, f"恰一個成功：{results}"
    assert sorted(status for _i, status in results) == [200] + [409] * 7
    assert (audit_dir / f"{ref}.json").read_bytes() == f"raw-from-thread-{winners[0]}".encode()
    assert listing(audit_dir) == [f"{ref}.json"]


# ── AT-950-1-E-2：I/O 失敗的 503 帶 errno、不洩漏路徑、半成品被清除 ───────────────────────────────
def assert_write_failed(err: ApiError, errno_value: int, class_name: str, *paths: Path) -> None:
    assert (err.status_code, err.body["reason"]) == (503, "si_unavailable")
    assert err.body["cause"] == "audit_write_failed"
    assert set(err.body) == {"code", "reason", "cause", "detail"}
    assert err.body["detail"] == f"errno={errno_value}; {class_name}", err.body["detail"]
    blob = json.dumps(err.body, ensure_ascii=False)
    for path in paths:
        assert str(path) not in blob and path.name not in blob, "detail 不得含任何路徑"


def test_AT_950_1_E_2_a_missing_directory_is_503_and_is_not_created(tmp_path: Path) -> None:
    missing = tmp_path / "no-such-dir" / "deeper"
    with pytest.raises(ApiError) as caught:
        si_audit.store_audit(missing, ref_of(1), b"raw")
    assert_write_failed(caught.value, errno.ENOENT, "FileNotFoundError", missing, tmp_path)
    assert not missing.exists() and not missing.parent.exists(), "不得建立稽核目錄"


def test_AT_950_1_E_2_open_denied_and_disk_full_leave_nothing_behind(
        audit_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_open, real_write = os.open, os.write
    audit_fds: list[int] = []

    def deny(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if under(path, audit_dir):
            raise OSError(errno.EACCES, "denied by the test", str(path))
        return real_open(path, flags, *args, **kwargs)

    with monkeypatch.context() as mp:
        mp.setattr(os, "open", deny)
        with pytest.raises(ApiError) as caught:
            si_audit.store_audit(audit_dir, ref_of(1), b"raw")
    assert_write_failed(caught.value, errno.EACCES, "PermissionError", audit_dir)
    assert listing(audit_dir) == []

    def tracking_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        fd = real_open(path, flags, *args, **kwargs)
        if under(path, audit_dir):
            audit_fds.append(fd)
        return fd

    def half_then_full(fd: int, data: Any) -> int:
        if fd not in audit_fds:
            return real_write(fd, data)
        real_write(fd, bytes(data)[: len(data) // 2])        # 先真的寫進一半
        raise OSError(errno.ENOSPC, "No space left on device")

    with monkeypatch.context() as mp:
        mp.setattr(os, "open", tracking_open)
        mp.setattr(os, "write", half_then_full)
        with pytest.raises(ApiError) as caught:
            si_audit.store_audit(audit_dir, ref_of(2), b"a-body-long-enough-to-be-split" * 4)
    assert audit_fds, "測試替身必須真的攔到稽核檔的 fd"
    assert_write_failed(caught.value, errno.ENOSPC, "OSError", audit_dir)
    assert listing(audit_dir) == [], "寫到一半失敗必須刪除半成品"


def test_AT_950_1_E_2_a_missing_audit_dir_answers_503_over_http_too(
        make_bridge: Callable[..., Any], settings: Settings, fake: Path, tmp_path: Path) -> None:
    gone = tmp_path / "never-created"
    live = make_bridge(replace(settings, si_root=fake, si_write_token=T0, si_audit_dir=gone))
    resp = post(live, DECIDE, valid_outer("decide", 1))
    body = resp.json()
    assert resp.status_code == 503, resp.text
    assert (body["reason"], body["cause"]) == ("si_unavailable", "audit_write_failed")
    assert str(tmp_path) not in resp.text and not gone.exists()


# ── AT-935-3-E-2：DELETE、PUT、PATCH 對全部 `/si/` 路徑一律 405 ────────────────────────────────
NINE_PATHS = ["/si/status", OBS_ADD, "/si/events", "/si/proposals", "/si/proposals/PROP-SI-004",
              "/si/runs", DECIDE, OBS_CLOSE, VALIDATE]


def test_AT_935_3_E_2_delete_put_and_patch_are_405_on_every_si_path(
        live: Any, fake: Path, audit_dir: Path) -> None:
    wrong = []
    for path in NINE_PATHS:
        for method in ("DELETE", "PUT", "PATCH"):
            resp = live.client.request(method, path, headers={"X-Bridge-Token": T0}, content=b"{}")
            if resp.status_code != 405:
                wrong.append((method, path, resp.status_code))
    assert wrong == [], f"九路徑乘三種非 POST／GET 方法必須全是 405：{wrong}"
    assert len(NINE_PATHS) * 3 == 27
    assert listing(audit_dir) == [], "405 不得落任何檔"
    assert read_calls(fake) == [], "405 不得啟動任何子行程"


# ── AT-950-2-1：三個寫入端點的成功路徑 ─────────────────────────────────────────────────────────
def test_AT_950_2_1_the_three_write_endpoints_store_the_request_bytes_verbatim(
        live: Any, audit_dir: Path, fake: Path) -> None:
    cases = [(DECIDE, sup.read_audit_golden("G1")), (OBS_ADD, sup.read_audit_golden("G3")),
             (OBS_CLOSE, sup.read_audit_golden("G5"))]
    names = []
    for path, raw in cases:
        ref = json.loads(raw.decode("utf-8"))["audit_ref"]
        resp = post(live, path, raw)
        assert resp.status_code == 201, f"{path}：{resp.status_code} {resp.text}"
        assert list(resp.json()) == ["audit_ref", "stored"], "鍵序固定"
        assert resp.json() == {"audit_ref": ref, "stored": True}
        assert resp.text == f'{{"audit_ref":"{ref}","stored":true}}', "本文不含路徑與其他鍵"
        assert (audit_dir / f"{ref}.json").read_bytes() == raw, f"{path}：落檔位元組須等於請求"
        names.append(f"{ref}.json")
    assert listing(audit_dir) == sorted(names), "AD 內恰三檔、無其他檔"
    assert read_calls(fake) == [], "寫入端點不啟動任何子行程（Bridge 不呼叫寫入型 CLI）"


# ── AT-950-2-2：不解 body、不驗簽；稽核記錄只含決策 ────────────────────────────────────────────
def test_AT_950_2_2_the_bridge_does_not_parse_the_body_and_its_audit_has_no_secrets(
        live: Any, audit_dir: Path, caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch) -> None:
    compared: list[tuple[type, type]] = []
    real_compare = hmac.compare_digest

    def recorder(a: Any, b: Any) -> bool:
        compared.append((type(a), type(b)))
        return real_compare(a, b)

    monkeypatch.setattr(security.hmac, "compare_digest", recorder)
    caplog.set_level("WARNING", logger="bridge.audit")
    raw = valid_outer("decide", 1, body="not json")
    resp = post(live, DECIDE, raw)
    assert resp.status_code == 201, resp.text
    assert (audit_dir / f"{ref_of(1)}.json").read_bytes() == raw
    assert compared == [(bytes, bytes)], "權杖須以 hmac.compare_digest 比對兩個 bytes"
    log_path = live.settings.engine_workspace / "_audit.jsonl"
    entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    mine = [e for e in entries if e["event"] == "si_write"]
    assert len(mine) == 1
    assert (mine[0]["verb"], mine[0]["result"], mine[0]["subject"]) == (
        "decide", "ok", "PROP-SI-004")
    secrets = [T0, "0" * 64, "not json", sup.K0_ID]
    blob = log_path.read_text(encoding="utf-8") + caplog.text
    assert "si_write" in blob
    for secret in secrets:
        assert secret not in blob, f"稽核記錄不得含 {secret[:12]!r}…"
    # 被拒的請求也記稽核，同樣不含權杖值（含被拒的那個）
    wrong = "w" * len(T0)
    assert post(live, DECIDE, valid_outer("decide", 2), token=wrong).status_code == 403
    after = log_path.read_text(encoding="utf-8")
    assert "rejected:si_write_forbidden" in after and wrong not in after and T0 not in after


# ── AT-950-2-3：合格形態皆放行 ─────────────────────────────────────────────────────────────────
def test_AT_950_2_3_every_qualifying_id_and_subject_shape_is_accepted(live: Any) -> None:
    forms: list[tuple[str, str, bytes]] = [
        ("decide-prop", DECIDE, valid_outer("decide", 1)),
        ("decide-run", "/si/proposals/RUN-SI-001:decide",
         dump(outer_dict("decide", "RUN-SI-001", ref_of(2)))),
        ("decide-four-digits", f"/si/proposals/{FOUR_DIGIT_PROP}:decide",
         dump(outer_dict("decide", FOUR_DIGIT_PROP, ref_of(3)))),
        ("close", OBS_CLOSE, valid_outer("obs-close", 4)),
        ("obs-add-null-subject", OBS_ADD, valid_outer("obs-add", 5)),
    ]
    for name, path, raw in forms:
        resp = post(live, path, raw)
        assert resp.status_code == 201, f"{name}：{resp.status_code} {resp.text}"
    assert json.loads(valid_outer("obs-add", 5).decode("utf-8"))["subject"] is None


# ── AT-950-2-E-1：寫入面停用矩陣 ───────────────────────────────────────────────────────────────
GARBAGE = b"\xff\xfe this is not json at all"


def test_AT_950_2_E_1_the_write_surface_is_off_unless_token_and_audit_dir_are_both_set(
        make_bridge: Callable[..., Any], settings: Settings, fake: Path, tmp_path: Path) -> None:
    audit = tmp_path / "audit-e1"
    audit.mkdir()
    configs = {"neither": {}, "token-only": {"si_write_token": T0},
               "dir-only": {"si_audit_dir": audit},
               "both": {"si_write_token": T0, "si_audit_dir": audit}}
    for name, over in configs.items():
        live = make_bridge(replace(
            settings, si_root=fake, **{"si_write_token": None, "si_audit_dir": None, **over}))
        for endpoint, (path, _kind, _subject) in ENDPOINTS.items():
            for token in (None, T0, "wrong"):
                resp = post(live, path, GARBAGE, token=token)
                label = f"{name} {endpoint} token={token!r}"
                if name == "both" and token == T0:
                    assert resp.status_code == 422, f"{label}：停用解除後垃圾本文得 422，不是 503"
                    assert resp.json()["reason"] == "invalid_request", label
                elif name == "both":
                    assert resp.status_code == 403, label
                else:
                    assert resp.status_code == 503, f"{label}：{resp.status_code} {resp.text[:200]}"
                    body = resp.json()
                    assert body["reason"] == "si_write_disabled", label
                    assert set(body) == {"code", "reason", "detail"}, label
                    assert T0 not in resp.text, label
        assert listing(audit) == [], f"{name}：不得落任何檔"
        assert live.client.get("/si/observations").status_code == 200, f"{name}：GET 不受影響"
        good = live.client.post(VALIDATE, json={"k": "v"})
        assert good.status_code == 200, f"{name}：validate 不受影響（{good.status_code}）"
    assert len(configs) == 4
    # 假 CLI 只被 GET 與 validate 啟動（每個設定各一次 GET 一次 validate），寫入端點零次
    verbs = [c["args"][0] for c in read_calls(fake)]
    assert sorted(verbs) == sorted(["export", "obs-add"] * 4)


# ── AT-950-2-E-2：權杖矩陣 ─────────────────────────────────────────────────────────────────────
def test_AT_950_2_E_2_every_wrong_token_form_gets_the_identical_403(
        live: Any, audit_dir: Path, fake: Path) -> None:
    wrong_forms: dict[str, str | bytes | None] = {
        "missing": None, "empty": "", "one-short": T0[:-1], "one-longer": T0 + "x",
        "case-changed": T0.swapcase(), "non-ascii": "é".encode() + T0[1:].encode()}
    bodies: dict[str, set[bytes]] = {}
    for endpoint, (path, _kind, _subject) in ENDPOINTS.items():
        for name, token in wrong_forms.items():
            resp = post(live, path, valid_outer(endpoint, 1), token=token)
            assert resp.status_code == 403, f"{endpoint} {name}：{resp.status_code} {resp.text}"
            assert resp.json() == {"code": 403, "reason": "si_write_forbidden"}
            bodies.setdefault(endpoint, set()).add(resp.content)
    assert len({b for forms in bodies.values() for b in forms}) == 1, \
        "缺與錯（含各端點）的 403 回應本文必須逐位元組相同"
    assert listing(audit_dir) == [] and read_calls(fake) == [], "被拒請求不落檔、不啟子行程"
    for n, (endpoint, (path, _kind, _subject)) in enumerate(ENDPOINTS.items(), start=1):
        assert post(live, path, valid_outer(endpoint, n), token=T0).status_code == 201, endpoint
    assert len(listing(audit_dir)) == 3


# ── AT-950-2-E-3：形態違規一律 422 ─────────────────────────────────────────────────────────────
def padded_request(size: int) -> bytes:
    """恰 `size` 位元組的合法外層（decide）：以 body 字串補長。"""
    base = valid_outer("decide", 1, body="")
    pad = size - len(base)
    assert pad >= 0
    raw = valid_outer("decide", 1, body="p" * pad)
    assert len(raw) == size
    return raw


def shape_cases() -> list[tuple[str, bytes, str, str]]:
    """(名稱, 本文, 期望 field, 期望 rule)。"""
    ok = json.loads(valid_outer("decide", 1).decode("utf-8"))

    def mutate(**over: Any) -> bytes:
        obj = dict(ok)
        for key, value in over.items():
            if value is ...:
                obj.pop(key)
            else:
                obj[key] = value
        return dump(obj)

    return [
        ("not-json", b"not json", "$", "not_json"),
        ("array", b"[]", "$", "not_object"), ("number", b"42", "$", "not_object"),
        ("string", b'"s"', "$", "not_object"), ("null", b"null", "$", "not_object"),
        ("json-then-garbage", valid_outer("decide", 1) + b" trailing", "$", "not_json"),
        ("not-utf8", b"\xff\xfe\x00\x00", "$", "not_utf8"),
        ("empty-body", b"", "$", "not_json"),
        ("over-65536", padded_request(65537), "$", "too_large"),
        ("missing-mac", mutate(mac=...), "mac", "required"),
        ("missing-subject", mutate(subject=...), "subject", "required"),
        ("extra-key", mutate(extra="x"), "extra", "unknown_key"),
        ("schema-rev-2", mutate(schema_rev=2), "schema_rev", "must_be_1"),
        ("schema-rev-string", mutate(schema_rev="1"), "schema_rev", "must_be_1"),
        ("schema-rev-true", mutate(schema_rev=True), "schema_rev", "must_be_1"),
        ("schema-rev-float", mutate(schema_rev=1.0), "schema_rev", "must_be_1"),
        ("kind-mismatch", mutate(kind="obs-add"), "kind", "kind_mismatch"),
        ("audit-ref-uppercase", mutate(audit_ref=ref_of(1).upper()), "audit_ref", "invalid_format"),
        ("subject-number", mutate(subject=123), "subject", "subject_mismatch"),
        ("body-not-string", mutate(body={"a": 1}), "body", "must_be_string"),
        ("key-id-not-string", mutate(key_id=5), "key_id", "must_be_string"),
        ("mac-not-string", mutate(mac=None), "mac", "must_be_string"),
    ]


@pytest.mark.parametrize("name,raw,field,rule", shape_cases(),
                         ids=[c[0] for c in shape_cases()])
def test_AT_950_2_E_3_malformed_requests_are_422_and_leave_no_file(
        live: Any, audit_dir: Path, name: str, raw: bytes, field: str, rule: str) -> None:
    resp = post(live, DECIDE, raw)
    assert resp.status_code == 422, f"{name}：{resp.status_code} {resp.text[:300]}"
    body = resp.json()
    assert body["reason"] == "invalid_request", name
    hits = [v for v in body["violations"] if v["field"] == field and v["rule"] == rule]
    assert hits, f"{name}：violations 須含 field={field} rule={rule}：{body['violations']}"
    assert set(hits[0]) == {"field", "rule", "message"}
    assert listing(audit_dir) == [], f"{name}：不得落檔"


def test_AT_950_2_E_3_exactly_65536_bytes_is_accepted(live: Any, audit_dir: Path) -> None:
    resp = post(live, DECIDE, padded_request(65536))
    assert resp.status_code == 201, resp.text[:300]
    assert len((audit_dir / f"{ref_of(1)}.json").read_bytes()) == 65536
    assert post(live, DECIDE, padded_request(65537)).status_code == 422


# ── AT-950-2-E-4：{id} 與 subject 不符、重送 ──────────────────────────────────────────────────
def test_AT_950_2_E_4_id_and_subject_must_agree_and_a_resent_ref_is_409(
        live: Any, audit_dir: Path) -> None:
    ok_decide = valid_outer("decide", 1)
    bad: list[tuple[str, str, bytes, str]] = [
        ("subject-differs-from-path", DECIDE, valid_outer("decide", 2, subject="RUN-SI-001"),
         "subject"),
        ("lowercase-prefix", "/si/proposals/prop-si-004:decide", ok_decide, "id"),
        ("too-few-digits", f"/si/proposals/{SHORT_PROP}:decide",
         dump(outer_dict("decide", SHORT_PROP, ref_of(3))), "id"),
        ("obs-id-on-decide-path", "/si/proposals/OBS-SI-005:decide",
         dump(outer_dict("decide", "OBS-SI-005", ref_of(4))), "id"),
        ("prop-id-on-close-path", "/si/observations/PROP-SI-004:close",
         dump(outer_dict("obs-close", "PROP-SI-004", ref_of(5))), "id"),
        ("trailing-newline-in-id", "/si/proposals/PROP-SI-004%0A:decide",
         dump(outer_dict("decide", "PROP-SI-004\n", ref_of(6))), "id"),
        ("obs-add-subject-not-null", OBS_ADD, valid_outer("obs-add", 7, subject="OBS-SI-001"),
         "subject"),
    ]
    for name, path, raw, field in bad:
        resp = post(live, path, raw)
        assert resp.status_code == 422, f"{name}：{resp.status_code} {resp.text[:200]}"
        assert resp.json()["reason"] == "invalid_request", name
        assert any(v["field"] == field for v in resp.json()["violations"]), \
            f"{name}：{resp.json()['violations']}"
    assert listing(audit_dir) == [], "違規請求不得落檔"
    first = post(live, DECIDE, ok_decide)
    assert first.status_code == 201
    second_raw = valid_outer("decide", 1, body="第二次的本文不同")
    second = post(live, DECIDE, second_raw)
    assert (second.status_code, second.json()["reason"]) == (409, "si_audit_exists")
    assert (audit_dir / f"{ref_of(1)}.json").read_bytes() == ok_decide, "檔案仍為第一次的位元組"
    assert listing(audit_dir) == [f"{ref_of(1)}.json"]


# ── AT-950-3-2：validate 路由 ──────────────────────────────────────────────────────────────────
def test_AT_950_3_2_validate_needs_no_token_and_passes_both_rc_values_through(
        make_bridge: Callable[..., Any], settings: Settings, fake: Path, audit_dir: Path) -> None:
    live = make_bridge(replace(settings, si_root=fake, si_write_token=None, si_audit_dir=None))
    ok_obj = {"ok": True, "row": "| fake preview row |", "row_bytes": 20, "row_max_bytes": 700,
              "findings": []}
    reject_obj = {"ok": False, "row": "", "row_bytes": 0, "row_max_bytes": None,
                  "findings": [{"code": "PIPE-IN-FIELD", "detail": "字串欄含 |"},
                               {"code": "COORD-NONE", "detail": "證據缺座標"}]}
    def tree() -> list[str]:        # 假 CLI 自己的紀錄與旋鈕檔不算「新檔」
        return sorted(p.relative_to(fake).as_posix() for p in fake.rglob("*")
                      if p.name not in ("fake_calls.jsonl", "fake_control.json"))

    before = tree()
    for rc, obj in ((0, ok_obj), (1, reject_obj)):
        set_control(fake, dry_run=obj, rc=rc)
        resp = live.client.post(VALIDATE, json={"user": "admin"})
        assert resp.status_code == 200, f"rc={rc}：{resp.status_code} {resp.text}"
        assert resp.json() == obj
        assert list(resp.json()) == list(obj), "鍵序保留"
    assert listing(audit_dir) == []
    calls = read_calls(fake)
    assert len(calls) == 2 and all(c["args"][:2] == ["obs-add", "--dry-run"] for c in calls)
    assert tree() == before, "repo（假 CLI 樹）不得多出任何新檔"


# ── AT-950-3-E-2：validate 請求違規＝422 且不啟動子行程 ─────────────────────────────────────────
def test_AT_950_3_E_2_a_malformed_validate_request_never_starts_the_subprocess(
        live: Any, fake: Path) -> None:
    padded = dump({"pad": "x" * (65536 - len(dump({"pad": ""})))})
    assert len(padded) == 65536
    bad = {"not-json": b"nope", "array": b"[]", "scalar": b"1", "empty": b"",
           "over-65536": padded + b" ", "not-utf8": b"\xff\xfe"}
    for name, raw in bad.items():
        resp = live.client.post(VALIDATE, content=raw, headers={"Content-Type": "application/json"})
        assert resp.status_code == 422, f"{name}：{resp.status_code} {resp.text[:200]}"
        assert resp.json()["reason"] == "invalid_request", name
    assert read_calls(fake) == [], "違規請求不得啟動子行程"
    ok = live.client.post(VALIDATE, content=padded, headers={"Content-Type": "application/json"})
    assert ok.status_code == 200, f"恰 65536 位元組的合法物件得 200：{ok.status_code}"
    assert len(read_calls(fake)) == 1
