"""秘密遮蔽樣式表的唯一的家（PRD §12「日誌」：`REDACT_SECRETS_IN_LOGS`）。

兩個消費者、同一份樣式表：
  · 狀態庫（`infra/repositories/pg_state_repository.py`、`factory.py`）：`redact_dsn`／
    `scrub_sensitive`，輸出逐字不變——它們原本各自住在那兩個檔裡，本檔只是把表搬來唯一的家；
  · 日誌（`utils/logger.py` 的 `RedactSecretsFilter`）：`redact_secrets` ＝ 上面兩者再加補充樣式。

誠實劃界（不是「已全面涵蓋」）：
  · 只遮 `logging` 路徑。`RawStreamLogger` 寫的是 PTY 原始位元組串流（非 logging、可能把一個
    token 切在兩個 chunk 之間），不在本檔射程；
  · 樣式是啟發式：只認有形狀的秘密（鍵值形、`sk-`／`Bearer`／DSN 密碼段）。一個沒有任何前後文的
    隨機字串認不出來；寧可多遮（`password: see docs` 的 `see` 會被遮）也不漏遮。
"""
from __future__ import annotations

import os
import re
from collections.abc import Mapping

REDACTED = "[REDACTED]"
ENV_SWITCH = "REDACT_SECRETS_IN_LOGS"
_OFF_SPELLINGS = frozenset({"0", "false", "off", "no"})

# ── 既有樣式表（原住 pg_state_repository／factory；逐字搬入，行為不變）──────────
DSN_PASSWORD_RE = re.compile(r"(://[^:/@]+:)([^@]+)(@)")
SENSITIVE_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*"),   # Bearer tokens
    re.compile(r"sk-[A-Za-z0-9\-_]{20,}"),                   # Anthropic / OpenAI API keys
    re.compile(r"(?i)authorization:\s*\S+"),                  # Authorization headers
)


def redact_dsn(msg: str) -> str:
    """從訊息中移除 DSN 密碼欄位（Security review 要求）。"""
    return DSN_PASSWORD_RE.sub(r"\1***\3", msg)


def scrub_sensitive(text: str) -> str:
    """移除 Bearer token／API key／Authorization 標頭等敏感資訊。"""
    if not text:
        return text
    for pat in SENSITIVE_PATTERNS:
        text = pat.sub(REDACTED, text)
    return text


# ── 日誌端的補充樣式（只用於日誌；PG 路徑不套用，所以 PG 既有輸出不變）──────────
# 鍵值形的值：已遮過的標記（原子值，讓遮蔽冪等——不吃掉標記後面的 `}`／`)`）、引號包住的整段
# （可含空白）或到下一個空白為止。鍵前以「非英數」收尾而不用 `\b`，
# 是為了讓 `DB_PASSWORD=`／`client_secret=` 這種帶底線前綴的鍵也命中（`_` 是 word 字元，
# `\b` 切不開）；鍵後必須緊接 `=`／`:`（可夾引號與空白），於是 `password_reset=`、
# `secretary=` 不會命中。
_VALUE = r"(?:\[REDACTED\]|\"[^\"]*\"|'[^']*'|\S+)"
_KEY_START = r"(?<![A-Za-z0-9])"
_ASSIGN = r"[\"']?\s*[=:]\s*"
_KEEP_KEY = rf"\1{REDACTED}"
_LOG_EXTRA_PATTERNS = (
    # AUTOCLAUDE_DB_DSN／AUTOCLAUDE_PG_DSN 的整個值（連主機、庫名一起遮，內網主機名不公開）
    (re.compile(rf"(?i)({_KEY_START}AUTOCLAUDE_(?:DB|PG)_DSN{_ASSIGN}){_VALUE}"), _KEEP_KEY),
    # password=／passwd=／secret=／api_key=／access_token=／client_secret= …
    (re.compile(
        rf"(?i)({_KEY_START}(?:password|passwd|secret|api[_-]?key|(?:access|auth|refresh)[_-]?token)"
        rf"{_ASSIGN}){_VALUE}"), _KEEP_KEY),
    # Authorization 標頭連 scheme 一起遮：`Authorization: Basic <b64>`（既有那條只吃到 scheme 字）
    (re.compile(
        rf"(?i)({_KEY_START}authorization\s*:\s*)(?:(?:bearer|basic|digest|token|negotiate)\s+)?{_VALUE}"),
     _KEEP_KEY),
    # `sk-ant-`：不論長度（真金鑰很長；被截斷或編造的也不該留）
    (re.compile(r"sk-ant-[A-Za-z0-9\-_]+"), REDACTED),
)


def redact_secrets(text: str) -> str:
    """日誌用的完整遮蔽：補充樣式（較具體、先跑）→ DSN 密碼段 → 既有敏感樣式。
    冪等；非字串（與空字串）原樣回傳。"""
    if not isinstance(text, str) or not text:
        return text
    for pat, repl in _LOG_EXTRA_PATTERNS:
        text = pat.sub(repl, text)
    return scrub_sensitive(redact_dsn(text))


def secrets_redaction_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """`REDACT_SECRETS_IN_LOGS`：出廠 on；只有 0／false／off／no（不分大小寫、去空白）才關。

    🔴 fail-closed：打錯字（`treu`）算開——設了卻沒生效的方向是漏秘密，不是少遮一點。
    """
    env = os.environ if environ is None else environ
    return (env.get(ENV_SWITCH) or "").strip().lower() not in _OFF_SPELLINGS
