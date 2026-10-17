"""SDD 寫入面權杖（ADR-XPLAT-016 §9；G-09；契約 v1.5 §3.1.4 共通規則 2）：設定、入口檢查、環境剝除
的名單。

權杖是「Bridge 無認證」的既有缺口（Architecture §12 L-6）上，新增 FSM 寫入面時唯一的守門員，
所以每一格（未設／缺／錯／對／非 ASCII／太短／佔位）都要有案例，且任何回應與稽核都不得帶權杖值。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import security
from app.errors import ApiError
from app.security import AuditLog, require_sdd_write_token, validate_env
from app.settings import SettingsError, load_settings

TOKEN = "k" * 32 + "-sdd-write-token"
ALLOW = ("localhost",)
PLACEHOLDER = "<YOUR_BRIDGE_SDD_WRITE_TOKEN_MIN_32_CHARS>"


# ── 設定：未設／夠長／太短／佔位 ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("raw", [None, "", "   "])
def test_an_unset_or_blank_token_means_the_write_surface_is_disabled(
        raw: str | None, tmp_path: Path) -> None:
    env = {"ENGINE_WORKSPACE": str(tmp_path)}
    if raw is not None:
        env["BRIDGE_SDD_WRITE_TOKEN"] = raw
    assert load_settings(env).sdd_write_token is None


def test_a_token_of_at_least_32_characters_is_accepted_and_stripped(tmp_path: Path) -> None:
    env = {"ENGINE_WORKSPACE": str(tmp_path), "BRIDGE_SDD_WRITE_TOKEN": f"  {TOKEN}  "}
    assert load_settings(env).sdd_write_token == TOKEN
    exactly_32 = {"ENGINE_WORKSPACE": str(tmp_path), "BRIDGE_SDD_WRITE_TOKEN": "z" * 32}
    assert load_settings(exactly_32).sdd_write_token == "z" * 32


@pytest.mark.parametrize("raw", ["z" * 31, "short", "a b"])
def test_a_token_shorter_than_32_characters_fails_startup_loudly(
        raw: str, tmp_path: Path) -> None:
    with pytest.raises(SettingsError) as caught:
        load_settings({"ENGINE_WORKSPACE": str(tmp_path), "BRIDGE_SDD_WRITE_TOKEN": raw})
    assert "BRIDGE_SDD_WRITE_TOKEN" in str(caught.value)
    assert raw not in str(caught.value), "錯誤訊息不得把值寫進日誌"


@pytest.mark.parametrize("raw", [
    PLACEHOLDER, "<anything-at-all-that-is-long-enough-to-pass-length>",
    "prefix-<YOUR_TOKEN>-suffix-" + "x" * 20])
def test_a_placeholder_token_fails_startup_loudly_even_when_long_enough(
        raw: str, tmp_path: Path) -> None:
    """佔位當真值＝公開密鑰：`.env.example` 的 `<YOUR_…>` 抄進 .env 沒改，一定要在啟動時被抓到。"""
    assert len(PLACEHOLDER) >= 32, "對照：佔位本身夠長，所以不能只靠長度判斷"
    with pytest.raises(SettingsError):
        load_settings({"ENGINE_WORKSPACE": str(tmp_path), "BRIDGE_SDD_WRITE_TOKEN": raw})


def test_the_token_never_appears_in_the_settings_repr(tmp_path: Path) -> None:
    settings = load_settings({"ENGINE_WORKSPACE": str(tmp_path), "BRIDGE_SDD_WRITE_TOKEN": TOKEN})
    assert TOKEN not in repr(settings) and TOKEN not in str(settings)


# ── 入口檢查矩陣（503／403／通過）──────────────────────────────────────────────────────────
def _check(configured: str | None, provided: str | None, audit: AuditLog | None = None) -> ApiError:
    with pytest.raises(ApiError) as caught:
        require_sdd_write_token(configured, provided, audit=audit, verb="freeze",
                                project="alpha", approver="op")
    return caught.value


def test_bridge_without_a_token_refuses_every_write_with_503_regardless_of_the_header() -> None:
    for provided in (None, "", "anything", TOKEN):
        err = _check(None, provided)
        assert (err.status_code, err.body["reason"]) == (503, "sdd_write_disabled")
    assert _check("", TOKEN).status_code == 503, "空字串設定值等同未設"


@pytest.mark.parametrize("provided", [None, "", "wrong", TOKEN[:-1], TOKEN + "x", TOKEN.upper(),
                                      "權杖" * 20, "\x00" + TOKEN])
def test_a_missing_or_wrong_token_is_403_with_one_reason_for_both(provided: str | None) -> None:
    err = _check(TOKEN, provided)
    assert (err.status_code, err.body) == (403, {"code": 403, "reason": "sdd_write_forbidden"})


def test_the_right_token_passes_and_non_ascii_tokens_compare_without_raising() -> None:
    require_sdd_write_token(TOKEN, TOKEN, audit=None, verb="freeze")
    unicode_token = "權杖-" * 12
    require_sdd_write_token(unicode_token, unicode_token, audit=None, verb="freeze")
    assert _check(unicode_token, "權杖-" * 11).status_code == 403


def test_the_comparison_is_constant_time_hmac_compare_digest(
        monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[bytes, bytes]] = []
    real = security.hmac.compare_digest

    def spy(a: bytes, b: bytes) -> bool:
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr(security.hmac, "compare_digest", spy)
    _check(TOKEN, "nope")
    require_sdd_write_token(TOKEN, TOKEN, audit=None, verb="freeze")
    assert len(calls) == 2 and all(isinstance(a, bytes) and isinstance(b, bytes) for a, b in calls)


def test_rejections_are_audited_as_decisions_without_any_token_value(tmp_path: Path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    _check(None, "attacker-guess-1", audit)
    _check(TOKEN, "attacker-guess-2", audit)
    raw = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    entries = [json.loads(line) for line in raw.splitlines()]
    assert [e["result"] for e in entries] == ["rejected:sdd_write_disabled",
                                              "rejected:sdd_write_forbidden"]
    assert all(e["event"] == "sdd_write" and e["verb"] == "freeze" and e["project"] == "alpha"
               and e["approver"] == "op" and "trace_id" in e for e in entries)
    for secret in (TOKEN, "attacker-guess-1", "attacker-guess-2"):
        assert secret not in raw, "稽核記決策，不記權杖（連被拒的那個值也不記）"


# ── 環境：請求層 env 不得設定這三個名字（§9「剝除」列）─────────────────────────────────────────
@pytest.mark.parametrize("name", ["BRIDGE_SDD_WRITE_TOKEN", "SDD_PROJECT", "SDD_STATE_DIR",
                                  "sdd_project", "Sdd_State_Dir", "bridge_sdd_write_token"])
def test_request_env_may_not_set_the_sdd_names_422_forbidden_name(name: str) -> None:
    violations = validate_env({name: "x"}, ALLOW)
    assert [v["rule"] for v in violations] == ["forbidden_name"], name
    assert violations[0]["field"] == f"env.{name}"


def test_other_sdd_looking_names_are_not_blocked_by_this_rule() -> None:
    """只擋 ADR §9 列的三個名字：精準是設計約束（擋太寬會讓合法的 env 被整批拒）。"""
    assert validate_env({"SDD_SOMETHING_ELSE": "x", "MY_SDD_PROJECT": "y"}, ALLOW) == []
