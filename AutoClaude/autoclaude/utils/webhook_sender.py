"""
Webhook 發送（TD-1）：以 httpx 對 ESCALATION 位址發 POST JSON。

目前實作 AT-001-1-1 的成功路徑（FRD-lite R4 的 timeout_s 傳遞、R5 的 2xx、R7）、
AT-001-2-1 的位址驗證（R1）、AT-001-3-1 的重試退避（R5 的可重試失敗、R6）、
AT-001-4-E-1 的 payload／參數驗證（R2、R3）與永不拋例外（R5 的其他例外、R8）、
AT-001-5-1 的日誌遮罩（R9）。
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

# R6：第 n 次失敗後睡 min(0.5 * 2 ** (n - 1), 8.0) 秒；序列 0.5、1.0、2.0、4.0、8.0、8.0…
_BACKOFF_BASE_S = 0.5
_BACKOFF_CAP_S = 8.0


@dataclass(frozen=True)
class WebhookResult:
    ok: bool
    status: int | None
    attempts: int
    error: str | None


def _masked_url(url: str) -> str:
    # R9：只留 scheme 加 hostname；userinfo、port、path、query、fragment 一律丟棄。
    # WHY：webhook 位址常夾帶帳密（userinfo）或 token（path／query），日誌不得成為外洩管道。
    # 只在 _is_https_url 通過後呼叫，因此 hostname 必定存在。
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.hostname}"


def _is_https_url(url) -> bool:
    # R1：非字串、urlsplit 拋 ValueError（例 IPv6 方括號沒閉合）、scheme 非 https、無主機都不合格。
    # WHY：不合格的位址絕不能送到 httpx，否則 transport 會被呼叫、違反 AC-001-2。
    if not isinstance(url, str):
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme.lower() == "https" and bool(parts.hostname)


def _is_sendable_payload(payload) -> bool:
    # R2：必須是 dict，且能以 allow_nan=False 序列化。
    # WHY：預設 json.dumps 放行 NaN／Infinity，但 httpx 的 json= 編碼會對它們拋 ValueError，
    # 必須在發送前就擋下，否則 transport 之前就失敗、變成不可預期的例外。
    if not isinstance(payload, dict):
        return False
    try:
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def _is_valid_int(value) -> bool:
    # R3：bool 是 int 的子類別，必須明確排除。
    return isinstance(value, int) and not isinstance(value, bool)


def _is_valid_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _give_up(masked: str, status, error: str, attempts: int) -> WebhookResult:
    # R9：終局失敗記一筆 WARNING；位址只用遮罩後的形式。
    logger.warning("Webhook failed url=%s error=%s attempts=%d", masked, error, attempts)
    return WebhookResult(ok=False, status=status, attempts=attempts, error=error)


def send_webhook(
    url,
    payload,
    *,
    timeout_s=5.0,
    max_attempts=3,
    transport=None,
    sleep=None,
) -> WebhookResult:
    # R1 → R2 → R3 固定順序；先命中者勝。
    # R9：驗證失敗只記一筆只含 error 代碼的 WARNING，絕不帶原始 URL 或 payload。
    if not _is_https_url(url):
        logger.warning("Webhook rejected: error=invalid_url")
        return WebhookResult(ok=False, status=None, attempts=0, error="invalid_url")
    if not _is_sendable_payload(payload):
        logger.warning("Webhook rejected: error=invalid_payload")
        return WebhookResult(ok=False, status=None, attempts=0, error="invalid_payload")
    if not (_is_valid_int(max_attempts) and max_attempts >= 1) or not (
        _is_valid_number(timeout_s) and timeout_s > 0
    ):
        logger.warning("Webhook rejected: error=invalid_argument")
        return WebhookResult(ok=False, status=None, attempts=0, error="invalid_argument")
    if sleep is None:
        sleep = time.sleep
    masked = _masked_url(url)
    attempts = 0
    while True:
        attempts += 1
        logger.debug("Webhook attempt=%d/%d url=%s", attempts, max_attempts, masked)
        # timeout_s 由 httpx 套到 connect／read／write／pool 四個階段（R4）。
        # follow_redirects=False：3xx 不跟隨，屬 R5 的不重試失敗。
        try:
            with httpx.Client(
                transport=transport, timeout=timeout_s, follow_redirects=False
            ) as client:
                response = client.post(url, json=payload)
        except httpx.TransportError as exc:
            # R5：網路層錯誤（含逾時）可重試；error 只放例外類別名稱。
            status, error, retryable = None, type(exc).__name__, True
        except Exception as exc:
            # R5／R8：其他例外不重試、不外洩；只攔 Exception，BaseException 照常上拋。
            return _give_up(masked, None, type(exc).__name__, attempts)
        else:
            status = response.status_code
            if 200 <= status < 300:
                return WebhookResult(ok=True, status=status, attempts=attempts, error=None)
            # R5：只有 5xx 可重試；3xx／4xx（含 429）不重試。
            error = f"http_{status}"
            retryable = 500 <= status < 600
        # R7：終局只看最後一次嘗試；最後一次之後不睡眠。
        if not retryable or attempts >= max_attempts:
            return _give_up(masked, status, error, attempts)
        # R6：退避秒數只由「已失敗次數」決定，sleep 可注入以免測試真的睡眠。
        sleep(min(_BACKOFF_BASE_S * 2 ** (attempts - 1), _BACKOFF_CAP_S))
