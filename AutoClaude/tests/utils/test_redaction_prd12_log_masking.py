"""PRD §12「日誌」：`REDACT_SECRETS_IN_LOGS`——對常見金鑰樣式做遮蔽的全域開關。

立案（PRD §16.2「§12 日誌遮蔽」那一列）：此前只有 PG 狀態庫自己有 `_redact`，logging 路徑沒有任何
遮蔽，也沒有開關；再開症狀＝一次日誌檔中發現憑證字串。本檔守四件事會不會**回來**：

  (a) 樣式表只有一個家（`utils/redaction.py`），PG 端與日誌端共用同一份、PG 行為逐字不變；
  (b) 日誌端涵蓋 PRD 點名的五類（password=／sk-ant-／Bearer／DSN 密碼段／AUTOCLAUDE_DB_DSN 值），
      且不誤傷引擎自己依賴的 marker（TOKEN_HALT 等）與一般敘述；
  (c) 開關：出廠 on，只有 0／false／off／no 關；關掉時原樣；
  (d) `setup_logger` 把過濾器掛到 `autoclaude` logger 的**每個** handler（含既有的），不重複掛。
"""
from __future__ import annotations

import ast
import io
import logging
import sys
from pathlib import Path

import pytest

from autoclaude.infra.repositories import factory, pg_state_repository
from autoclaude.utils import logger as logger_mod
from autoclaude.utils import redaction as R

_PKG = Path(R.__file__).resolve().parents[1]
_ENV = "REDACT_SECRETS_IN_LOGS"

# 假秘密：形狀對、值是編的（沒有任何真實憑證）。
_FAKE_KEY = "sk-ant-api03-" + "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789" * 2
_SECRETS = {
    "password-eq": ("login failed password=hunter2 for user", "hunter2"),
    "password-colon-quoted": ('cfg {"password": "p4ss w0rd"} loaded', "p4ss w0rd"),
    "db-password-key": ("DB_PASSWORD=s3cr3tvalue boot", "s3cr3tvalue"),
    "api-key-kv": ("api_key=abc123def456 set", "abc123def456"),
    "sk-ant-long": (f"key {_FAKE_KEY} used", _FAKE_KEY),
    "sk-ant-short-fake": ("key sk-ant-FAKE123 used", "FAKE123"),
    "bearer": ("header Bearer fakeBearerToken123.part2-sig_x= sent", "fakeBearerToken123"),
    "authorization-basic": ("Authorization: Basic ZmFrZTpmYWtl sent", "ZmFrZTpmYWtl"),
    "dsn-password": ("connect postgresql+asyncpg://app:Sup3rS3cret@db.internal:5432/x",  # noqa: E501  # secret-scan-ok: 合成假密碼（遮蔽器測試輸入）
                     "Sup3rS3cret"),
    "autoclaude-db-dsn-value": ("env AUTOCLAUDE_DB_DSN=postgresql://u:pw123@h.internal/prod ok",  # noqa: E501  # secret-scan-ok: 合成假密碼（遮蔽器測試輸入）
                                "h.internal/prod"),
    "autoclaude-pg-dsn-value": ("env AUTOCLAUDE_PG_DSN=postgresql://u:pw123@h2.internal/p ok",  # noqa: E501  # secret-scan-ok: 合成假密碼（遮蔽器測試輸入）
                                "h2.internal"),
}


# ══════════════════════════════════════════════════════════════════════════════
# (a)(b) 樣式表
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("text, secret", list(_SECRETS.values()), ids=list(_SECRETS))
def test_every_named_secret_shape_is_masked(text, secret):
    out = R.redact_secrets(text)
    assert secret not in out, out
    assert "[REDACTED]" in out or "***" in out, out


@pytest.mark.parametrize("text", [
    "=== STATE: TOKEN_HALT | [T01] context 95% >= halt 門檻 ===",
    "=== STEP_TOKEN_PEAK | step=T01 pct=0.9500 ===",
    "Token usage: 100 tokens / max 200",
    "token_pct=95 quota_pct=71.5 band=prepare",
    "step_id=password_reset attempt=2",
    "Playbook 啟動 | 專案: demo | 步驟: 3 | fresh=False | path=a/b.yaml",
    "AutoResumeService | 需外部續跑：需等 900s（續跑時刻 2026-10-13T08:00:00+08:00）",
    "",
])
def test_markers_and_ordinary_prose_are_left_byte_identical(text):
    """被遮蔽的是秘密，不是引擎自己依賴的 marker（A/B 載具依它計數）與一般敘述。"""
    assert R.redact_secrets(text) == text


def test_masking_is_idempotent():
    for text, _ in _SECRETS.values():
        once = R.redact_secrets(text)
        assert R.redact_secrets(once) == once


def test_a_non_string_is_returned_untouched():
    assert R.redact_secrets(None) is None       # type: ignore[arg-type]
    assert R.redact_secrets(123) == 123         # type: ignore[arg-type]


def test_a_dsn_value_is_masked_whole_not_just_its_password():
    """`AUTOCLAUDE_DB_DSN` 的值連主機與庫名都不外洩（內網主機名不是公開資訊）。"""
    out = R.redact_secrets("AUTOCLAUDE_DB_DSN=postgresql://u:pw@10.1.2.3:5432/prod?sslmode=require")  # noqa: E501  # secret-scan-ok: 合成假密碼（遮蔽器測試輸入）
    assert out == "AUTOCLAUDE_DB_DSN=[REDACTED]"


# ── PG 端：同一份表、行為逐字不變 ─────────────────────────────────────────────
@pytest.mark.parametrize("name", ["_redact", "_scrub_sensitive"])
def test_the_pg_side_imports_the_shared_functions_it_does_not_own_a_copy(name):
    shared = {"_redact": R.redact_dsn, "_scrub_sensitive": R.scrub_sensitive}[name]
    assert getattr(pg_state_repository, name) is shared
    if name == "_redact":
        assert factory._redact is shared      # 第三份複本也一併收進同一個家


def test_no_module_other_than_the_redaction_home_defines_the_dsn_pattern():
    """樣式表只有一個家：把正則抄回 PG／factory 任一檔，這裡轉紅。"""
    needle = "(://[^:/@]+:)"
    homes = [p.relative_to(_PKG).as_posix() for p in _PKG.rglob("*.py")
             if needle in p.read_text(encoding="utf-8")]
    assert homes == ["utils/redaction.py"], homes


def test_pg_behaviour_is_pinned_byte_for_byte():
    assert pg_state_repository._redact("x postgresql://u:secret@h/db y") == \
        "x postgresql://u:***@h/db y"
    assert pg_state_repository._redact("no dsn here") == "no dsn here"
    assert pg_state_repository._scrub_sensitive("a Bearer abc.def b") == "a [REDACTED] b"
    assert pg_state_repository._scrub_sensitive("k sk-" + "A" * 24 + " k") == "k [REDACTED] k"
    assert pg_state_repository._scrub_sensitive("Authorization: tok") == "[REDACTED]"
    assert pg_state_repository._scrub_sensitive("") == ""
    # 日誌端才有的補充樣式不得滲進 PG 路徑（那會改變狀態庫既有輸出）：
    assert pg_state_repository._scrub_sensitive("password=hunter2") == "password=hunter2"


def test_everything_the_pg_table_masks_is_also_masked_in_logs():
    """日誌端是 PG 表的**超集**：同一份樣式表加補充，不是另寫一份。"""
    cases = [("a Bearer abc.def b", "abc.def"), ("k sk-" + "B" * 24 + " k", "B" * 24),
             ("Authorization: tok", "tok"), ("x postgresql://u:secret@h/db y", "secret")]
    for text, secret in cases:
        assert secret not in R.scrub_sensitive(R.redact_dsn(text)), "前提：PG 表自己確實遮了它"
        assert secret not in R.redact_secrets(text), text


# ══════════════════════════════════════════════════════════════════════════════
# (c) 開關
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("value", ["0", "false", "False", "FALSE", "off", "OFF", " off ", "no"])
def test_only_the_documented_off_spellings_turn_it_off(value):
    assert R.secrets_redaction_enabled({_ENV: value}) is False


@pytest.mark.parametrize("value", [None, "", "1", "true", "on", "yes", "garbage", "treu", "2"])
def test_everything_else_including_typos_stays_on(value):
    """fail-closed：打錯字不得變成關閉（那會讓「設了卻沒生效」的方向是漏秘密）。"""
    env = {} if value is None else {_ENV: value}
    assert R.secrets_redaction_enabled(env) is True


def _logger_with_stream(name: str) -> tuple[logging.Logger, io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(logger_mod.RedactSecretsFilter())
    log = logging.getLogger(name)
    log.handlers = [handler]
    log.propagate = False
    log.setLevel(logging.DEBUG)
    return log, stream


# ══════════════════════════════════════════════════════════════════════════════
# 過濾器本體
# ══════════════════════════════════════════════════════════════════════════════
def test_a_fake_token_in_a_message_is_replaced_with_the_marker(monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)
    log, stream = _logger_with_stream("test.redaction.msg")
    log.warning("calling with key %s", _FAKE_KEY)           # %-args 也要被看見
    out = stream.getvalue()
    assert _FAKE_KEY not in out and "AbCdEfGh" not in out
    assert "calling with key [REDACTED]" in out


def test_with_the_switch_off_the_message_passes_through_verbatim(monkeypatch):
    monkeypatch.setenv(_ENV, "off")
    log, stream = _logger_with_stream("test.redaction.off")
    log.warning("password=hunter2 key %s", _FAKE_KEY)
    assert stream.getvalue() == f"password=hunter2 key {_FAKE_KEY}\n"


def test_the_switch_is_read_per_record_not_frozen_at_import(monkeypatch):
    log, stream = _logger_with_stream("test.redaction.live")
    monkeypatch.setenv(_ENV, "false")
    log.info("password=one")
    monkeypatch.setenv(_ENV, "true")
    log.info("password=two")
    assert stream.getvalue().splitlines() == ["password=one", "password=[REDACTED]"]


def test_a_traceback_that_carries_a_secret_is_masked_too(monkeypatch):
    """`logger.exception()` 的 traceback 是繞過 `getMessage()` 最常見的洩漏面。"""
    monkeypatch.delenv(_ENV, raising=False)
    log, stream = _logger_with_stream("test.redaction.exc")
    try:
        raise RuntimeError("upstream said password=hunter2 is wrong")
    except RuntimeError:
        log.exception("boom")
    out = stream.getvalue()
    assert "hunter2" not in out
    assert "RuntimeError" in out and "boom" in out, "遮蔽不得吞掉 traceback 本身"


def test_a_record_with_nothing_to_hide_keeps_its_structured_args(monkeypatch):
    """只在真的有東西要遮時才改寫 record：否則下游依賴 `record.args` 的消費者會被無謂破壞。"""
    monkeypatch.delenv(_ENV, raising=False)
    record = logging.LogRecord("n", logging.INFO, __file__, 1, "a %s %d", ("x", 2), None)
    assert logger_mod.RedactSecretsFilter().filter(record) is True
    assert record.msg == "a %s %d" and record.args == ("x", 2)


def test_a_malformed_record_is_left_for_the_handler_to_report_not_raised_here(monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)
    record = logging.LogRecord("n", logging.INFO, __file__, 1, "needs %d", ("not-int",), None)
    assert logger_mod.RedactSecretsFilter().filter(record) is True


def test_an_unformattable_traceback_does_not_turn_a_log_call_into_an_exception(monkeypatch):
    """過濾器跑在呼叫端的 `logger.xxx()` 裡：它自己拋例外就等於讓一筆 log 搞垮引擎。"""
    monkeypatch.delenv(_ENV, raising=False)

    def _boom(self, ei):
        raise RuntimeError("cannot format")
    monkeypatch.setattr(logging.Formatter, "formatException", _boom)
    try:
        raise ValueError("x")
    except ValueError:
        exc = sys.exc_info()
    record = logging.LogRecord("n", logging.ERROR, __file__, 1, "password=x", (), exc)
    assert logger_mod.RedactSecretsFilter().filter(record) is True
    assert record.getMessage() == "password=[REDACTED]"


def test_the_filter_never_drops_a_record(monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)
    record = logging.LogRecord("n", logging.INFO, __file__, 1, "password=x", (), None)
    assert logger_mod.RedactSecretsFilter().filter(record) is True


# ══════════════════════════════════════════════════════════════════════════════
# (d) setup_logger 接線
# ══════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def clean_autoclaude_logger():
    log = logging.getLogger("autoclaude")
    saved = (list(log.handlers), log.level, log.propagate)
    log.handlers = []
    try:
        yield log
    finally:
        for handler in list(log.handlers):
            handler.close()
        log.handlers, log.level, log.propagate = saved[0], saved[1], saved[2]


def _filters(handler) -> list:
    return [f for f in handler.filters if isinstance(f, logger_mod.RedactSecretsFilter)]


def test_setup_logger_attaches_the_filter_to_every_handler_exactly_once(
        tmp_path, clean_autoclaude_logger):
    root = logger_mod.setup_logger(str(tmp_path / "logs"))
    assert len(root.handlers) == 2, "出廠＝檔案＋console 兩個 handler"
    assert all(len(_filters(h)) == 1 for h in root.handlers)
    logger_mod.setup_logger(str(tmp_path / "logs"))       # 第二次呼叫（early-return 路徑）
    assert all(len(_filters(h)) == 1 for h in root.handlers), "重複呼叫不得重複掛"


def test_a_handler_that_was_already_there_gets_the_filter_on_the_early_return_path(
        tmp_path, clean_autoclaude_logger):
    foreign = logging.StreamHandler(io.StringIO())
    clean_autoclaude_logger.addHandler(foreign)
    logger_mod.setup_logger(str(tmp_path / "logs"))
    assert len(_filters(foreign)) == 1


def test_end_to_end_the_log_file_never_holds_the_secret(
        tmp_path, clean_autoclaude_logger, monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)
    root = logger_mod.setup_logger(str(tmp_path / "logs"))
    logging.getLogger("autoclaude.some.module").info("login password=hunter2 key=%s", _FAKE_KEY)
    for handler in root.handlers:
        handler.flush()
    body = (tmp_path / "logs" / "autoclaude.log").read_text(encoding="utf-8")
    assert "hunter2" not in body and "AbCdEfGh" not in body
    assert "login password=[REDACTED]" in body


def test_setup_logger_source_still_attaches_through_one_named_helper():
    """接線鎖：拿掉 setup_logger 對過濾器的掛接，上面三格會紅；這格再守『掛的是同一個類別』。"""
    tree = ast.parse((_PKG / "utils" / "logger.py").read_text(encoding="utf-8"))
    calls = {n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "addFilter" in calls
