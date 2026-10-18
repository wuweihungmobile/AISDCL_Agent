"""
TCS-WebhookSender-20261018 的 Unit 測試（F-001 send_webhook）。

只用 httpx.MockTransport 發送，不碰網路、不真的睡眠。
"""
import dataclasses
import json
import logging
from datetime import datetime, timedelta
from unittest.mock import patch

import httpx
import pytest

from autoclaude.utils.config import AppConfig
from autoclaude.utils.notifier import notify_escalation
from autoclaude.utils.webhook_sender import WebhookResult, send_webhook

URL = "https://hooks.example.com/escalation"
PAYLOAD = {"title": "T", "message": "M"}


def test_AT_001_1_1_success_posts_json():
    # WHY：AC-001-1 要求 2xx 即成功、請求是 POST 加 JSON 本文，且結果物件不可變；
    # 三個 2xx 狀態碼都必須被視為成功，不能只認 200。
    received = []

    def handler_for(status):
        def handler(request):
            received.append(request)
            return httpx.Response(status)

        return handler

    for status in (200, 201, 204):
        received.clear()
        result = send_webhook(URL, PAYLOAD, transport=httpx.MockTransport(handler_for(status)))
        assert result == WebhookResult(ok=True, status=status, attempts=1, error=None)
        assert len(received) == 1
        request = received[0]
        assert request.method == "POST"
        assert str(request.url) == URL
        assert json.loads(request.content) == PAYLOAD
        assert "application/json" in request.headers["content-type"]

    # WHY：timeout_s 必須真的傳進 httpx，否則呼叫端設定的逾時形同虛設。
    timeouts = []

    def timed_handler(request):
        timeouts.append(request.extensions["timeout"])
        return httpx.Response(200)

    result = send_webhook(
        URL, PAYLOAD, timeout_s=2.5, transport=httpx.MockTransport(timed_handler)
    )
    assert result.ok is True
    assert len(timeouts) == 1
    assert timeouts[0]["read"] == 2.5
    assert timeouts[0] == {"connect": 2.5, "read": 2.5, "write": 2.5, "pool": 2.5}

    # WHY：整數 timeout_s 也是合法的 number，不得被當成壞參數。
    result = send_webhook(URL, PAYLOAD, timeout_s=3, transport=httpx.MockTransport(timed_handler))
    assert result.ok is True
    assert timeouts[1] == {"connect": 3, "read": 3, "write": 3, "pool": 3}

    # WHY：欄位順序是公開契約的一部分（位置參數建構與序列化依賴）。
    assert [f.name for f in dataclasses.fields(WebhookResult)] == [
        "ok",
        "status",
        "attempts",
        "error",
    ]

    # WHY：結果是 frozen dataclass，呼叫端拿到之後不能被就地改寫。
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.ok = False


def test_AT_001_2_1_non_https_urls_are_never_sent():
    # WHY：AC-001-2 要求只有 https 位址會發送；其餘位址（含 urlsplit 拋 ValueError 的）
    # 必須在到達 httpx 之前就被擋下，且不得讓例外外洩給呼叫端。
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200)

    bad_urls = [
        "http://hooks.example.com/x",
        "ftp://hooks.example.com/x",
        "hooks.example.com/x",
        "https://",
        "https:///path",
        "https://[::1",
        "",
        "   ",
        None,
        123,
        b"https://hooks.example.com/x",
        ["https://hooks.example.com/x"],
    ]
    for url in bad_urls:
        result = send_webhook(url, {"k": "v"}, transport=httpx.MockTransport(handler))
        assert result == WebhookResult(ok=False, status=None, attempts=0, error="invalid_url")

    # WHY：handler 一次都不能被呼叫；只要有一次被呼叫，就代表位址驗證形同虛設。
    assert calls == []


def test_AT_001_3_1_retries_then_succeeds_with_backoff():
    # WHY：AC-001-3 要求 5xx 與網路錯誤才重試，且退避 0.5 起倍增；
    # 兩種可重試失敗（5xx、ConnectError）都必須能恢復成功，且退避序列只由已失敗次數決定。
    sleeps = []

    responses = iter([503, 503, 200])
    calls = []

    def status_handler(request):
        calls.append(request)
        return httpx.Response(next(responses))

    result = send_webhook(
        URL, PAYLOAD, transport=httpx.MockTransport(status_handler), sleep=sleeps.append
    )
    assert result == WebhookResult(ok=True, status=200, attempts=3, error=None)
    assert len(calls) == 3
    assert sleeps == [0.5, 1.0]

    sleeps.clear()
    calls.clear()

    def flaky_handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200)

    result = send_webhook(
        URL, PAYLOAD, transport=httpx.MockTransport(flaky_handler), sleep=sleeps.append
    )
    assert result == WebhookResult(ok=True, status=200, attempts=2, error=None)
    assert len(calls) == 2
    assert sleeps == [0.5]


def test_AT_001_3_2_exhausts_attempts_and_reports_last_result():
    # WHY：AC-001-3 要求重試用盡後以「最後一次嘗試」為終局結果，不殘留較早嘗試的 status 或 error；
    # 退避序列封頂 8 秒，且最後一次嘗試之後不睡眠（否則呼叫端白白多等一段時間）。
    def run(handler, **kwargs):
        sleeps = []
        calls = []

        def counting(request):
            calls.append(request)
            return handler(len(calls))

        result = send_webhook(
            URL, PAYLOAD, transport=httpx.MockTransport(counting), sleep=sleeps.append, **kwargs
        )
        return result, len(calls), sleeps

    def always_503(_):
        return httpx.Response(503)

    def always_read_timeout(_):
        raise httpx.ReadTimeout("slow")

    def always_500(_):
        return httpx.Response(500)

    def seq(*steps):
        def handler(n):
            step = steps[n - 1]
            if isinstance(step, Exception):
                raise step
            return httpx.Response(step)

        return handler

    # 情境一：永遠 503，預設 3 次。
    result, n_calls, sleeps = run(always_503)
    assert result == WebhookResult(ok=False, status=503, attempts=3, error="http_503")
    assert n_calls == 3
    assert sleeps == [0.5, 1.0]

    # 情境二：永遠 ReadTimeout，預設 3 次。
    result, n_calls, sleeps = run(always_read_timeout)
    assert result == WebhookResult(ok=False, status=None, attempts=3, error="ReadTimeout")
    assert n_calls == 3
    assert sleeps == [0.5, 1.0]

    # 情境三：永遠 500，max_attempts=7；退避在 8 秒封頂。
    result, n_calls, sleeps = run(always_500, max_attempts=7)
    assert result == WebhookResult(ok=False, status=500, attempts=7, error="http_500")
    assert n_calls == 7
    assert sleeps == [0.5, 1.0, 2.0, 4.0, 8.0, 8.0]

    # 情境四：503、ConnectError、502；終局是最後一次的 502，不殘留 ConnectError。
    result, n_calls, sleeps = run(seq(503, httpx.ConnectError("x"), 502))
    assert result == WebhookResult(ok=False, status=502, attempts=3, error="http_502")
    assert n_calls == 3
    assert sleeps == [0.5, 1.0]

    # 情境五：502、503、ReadTimeout；終局是最後一次的 ReadTimeout，status 不殘留 503。
    result, n_calls, sleeps = run(seq(502, 503, httpx.ReadTimeout("x")))
    assert result == WebhookResult(ok=False, status=None, attempts=3, error="ReadTimeout")
    assert n_calls == 3
    assert sleeps == [0.5, 1.0]


def test_AT_001_3_E_1_non_retryable_statuses_stop_after_one_attempt():
    # WHY：AC-001-3 只允許 5xx 與網路錯誤重試；3xx（含不跟隨的重導）與 4xx（含 429）
    # 一次即止。另 max_attempts=1 時連 503 也只發一次（max_attempts 含第一次嘗試）。
    # 若誤跟隨重導，請求會送到 other.example.com，這裡以收到的主機逐次斷言。
    sleeps = []

    def one_shot(status, headers=None):
        hosts = []
        calls = []

        def handler(request):
            calls.append(request)
            hosts.append(request.url.host)
            return httpx.Response(status, headers=headers)

        return handler, calls, hosts

    cases = [
        (302, {"Location": "https://other.example.com/next"}),
        (400, None),
        (401, None),
        (404, None),
        (429, None),
    ]
    for status, headers in cases:
        handler, calls, hosts = one_shot(status, headers)
        result = send_webhook(
            URL, PAYLOAD, transport=httpx.MockTransport(handler), sleep=sleeps.append
        )
        assert result == WebhookResult(ok=False, status=status, attempts=1, error=f"http_{status}")
        assert len(calls) == 1
        if status == 302:
            # WHY：不跟隨重導；只有原主機收到請求。
            assert hosts == ["hooks.example.com"]

    handler, calls, _ = one_shot(503)
    result = send_webhook(
        URL, PAYLOAD, max_attempts=1, transport=httpx.MockTransport(handler), sleep=sleeps.append
    )
    assert result == WebhookResult(ok=False, status=503, attempts=1, error="http_503")
    assert len(calls) == 1

    # WHY：六次呼叫皆不得睡眠；任何一次睡眠都代表錯誤地把不可重試的結果當成可重試。
    assert sleeps == []


def test_AT_001_4_E_1_never_raises_on_bad_input():
    # WHY：AC-001-4 要求 send_webhook 對任何輸入都回傳結果、不外洩例外，否則呼叫端的
    # ESCALATION 流程會被 webhook 拖垮；只有 BaseException（如 KeyboardInterrupt）可穿透。
    # 驗證順序 R1 → R2 → R3 固定，壞 payload 與壞參數都必須在到達 transport 之前擋下。
    sleeps = []

    # 情境一：非預期的 RuntimeError 不重試、不睡眠，只算一次嘗試。
    calls = []

    def raising(request):
        calls.append(request)
        raise RuntimeError("boom")

    result = send_webhook(URL, PAYLOAD, transport=httpx.MockTransport(raising), sleep=sleeps.append)
    assert result == WebhookResult(ok=False, status=None, attempts=1, error="RuntimeError")
    assert len(calls) == 1
    assert sleeps == []

    # 情境二：不合法 payload（不可序列化、集合、NaN、非 dict）一律 invalid_payload，不呼叫 handler。
    calls.clear()

    def never_called(request):
        calls.append(request)
        return httpx.Response(200)

    bad_payloads = [
        {"x": object()},
        {"x": {1, 2}},
        {"x": float("nan")},
        None,
        "text",
        [1],
    ]
    for payload in bad_payloads:
        result = send_webhook(
            URL, payload, transport=httpx.MockTransport(never_called), sleep=sleeps.append
        )
        assert result == WebhookResult(ok=False, status=None, attempts=0, error="invalid_payload")
    assert calls == []

    # 情境三：不合法參數一律 invalid_argument；bool 不算 int／number，None 不算 number。
    bad_arguments = [
        {"max_attempts": 0},
        {"max_attempts": -1},
        {"max_attempts": True},
        {"max_attempts": "3"},
        {"max_attempts": 2.5},
        {"timeout_s": 0},
        {"timeout_s": -1},
        {"timeout_s": True},
        {"timeout_s": "5"},
        {"timeout_s": None},
    ]
    for kwargs in bad_arguments:
        result = send_webhook(
            URL, PAYLOAD, transport=httpx.MockTransport(never_called), sleep=sleeps.append, **kwargs
        )
        assert result == WebhookResult(ok=False, status=None, attempts=0, error="invalid_argument")
    assert calls == []

    # 情境三之二：組合壞輸入的驗證順序——位址先於 payload，payload 先於參數。
    result = send_webhook(
        "http://hooks.example.com/x",
        None,
        transport=httpx.MockTransport(never_called),
        sleep=sleeps.append,
    )
    assert result == WebhookResult(ok=False, status=None, attempts=0, error="invalid_url")
    result = send_webhook(
        URL,
        None,
        max_attempts=0,
        transport=httpx.MockTransport(never_called),
        sleep=sleeps.append,
    )
    assert result == WebhookResult(ok=False, status=None, attempts=0, error="invalid_payload")
    assert calls == []

    # 情境四：BaseException 不被攔截，原樣拋到呼叫端；只發一次、不睡眠。
    class _Stop(BaseException):
        pass

    stop_calls = []

    def stopping(request):
        stop_calls.append(request)
        raise _Stop()

    with pytest.raises(_Stop):
        send_webhook(URL, PAYLOAD, transport=httpx.MockTransport(stopping), sleep=sleeps.append)
    assert len(stop_calls) == 1
    assert sleeps == []


def test_AT_001_5_1_logs_only_the_masked_url(caplog):
    # WHY：AC-001-5 要求日誌與 error 都不含 userinfo、port、path、query、fragment 與 payload 內容；
    # 遮罩後只剩 scheme 加 hostname。驗證失敗路徑也只能記 error 代碼。
    # 只篩本模組 logger：httpx 自己的 INFO 日誌帶完整 URL，不屬本模組。
    logger_name = "autoclaude.utils.webhook_sender"
    secret_url = "https://u5er:p4ss@hooks.example.com:8443/s3cret/path?tok=t0k3n#frag"  # noqa: E501  # secret-scan-ok: 合成假值（遮蔽器測試輸入）
    http_url = "http://u5er:p4ss@hooks.example.com:8443/s3cret/path?tok=t0k3n#frag"  # noqa: E501  # secret-scan-ok: 合成假值（遮蔽器測試輸入）
    leaked_markers = ["u5er", "p4ss", "8443", "s3cret", "t0k3n", "frag", "leak-me-42"]
    sleeps = []
    all_texts = []
    all_errors = []

    def module_records():
        return [r for r in caplog.records if r.name == logger_name]

    caplog.set_level(logging.DEBUG, logger=logger_name)

    # 第一次：503 後 200，成功路徑只有兩筆 DEBUG、沒有任何 WARNING。
    responses = iter([503, 200])
    caplog.clear()
    result = send_webhook(
        secret_url,
        {"title": "T", "message": "leak-me-42"},
        transport=httpx.MockTransport(lambda request: httpx.Response(next(responses))),
        sleep=sleeps.append,
    )
    records = module_records()
    all_texts += [r.getMessage() for r in records]
    all_errors.append(result.error)
    assert result == WebhookResult(ok=True, status=200, attempts=2, error=None)
    assert len(records) == 2
    debug = [r for r in records if r.levelno == logging.DEBUG]
    assert len(debug) == 2
    assert "attempt=1/3" in debug[0].getMessage()
    assert "attempt=2/3" in debug[1].getMessage()
    assert all("https://hooks.example.com" in r.getMessage() for r in debug)

    # 第二次：永遠 500，預設 3 次；每次嘗試各一筆 DEBUG，終局一筆 WARNING。
    caplog.clear()
    result = send_webhook(
        secret_url,
        {"title": "T", "message": "leak-me-42"},
        transport=httpx.MockTransport(lambda request: httpx.Response(500)),
        sleep=sleeps.append,
    )
    records = module_records()
    all_texts += [r.getMessage() for r in records]
    all_errors.append(result.error)
    assert result == WebhookResult(ok=False, status=500, attempts=3, error="http_500")
    warnings = [r for r in records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "https://hooks.example.com" in warnings[0].getMessage()
    assert "http_500" in warnings[0].getMessage()
    assert "attempts=3" in warnings[0].getMessage()

    # 第三次：http（違反 R1），只能記一筆含 invalid_url 的 WARNING；handler 不被呼叫。
    calls = []

    def counting(request):
        calls.append(request)
        return httpx.Response(200)

    caplog.clear()
    result = send_webhook(
        http_url,
        {"title": "T", "message": "leak-me-42"},
        transport=httpx.MockTransport(counting),
        sleep=sleeps.append,
    )
    records = module_records()
    all_texts += [r.getMessage() for r in records]
    all_errors.append(result.error)
    assert result == WebhookResult(ok=False, status=None, attempts=0, error="invalid_url")
    assert len(calls) == 0
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    assert "invalid_url" in records[0].getMessage()

    # 第四次：合法位址但 payload 不可序列化（違反 R2），只能記一筆含 invalid_payload 的 WARNING。
    caplog.clear()
    result = send_webhook(
        secret_url,
        {"x": object(), "leak-me-42": 1},
        transport=httpx.MockTransport(counting),
        sleep=sleeps.append,
    )
    records = module_records()
    all_texts += [r.getMessage() for r in records]
    all_errors.append(result.error)
    assert result == WebhookResult(ok=False, status=None, attempts=0, error="invalid_payload")
    assert len(calls) == 0
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    assert "invalid_payload" in records[0].getMessage()

    # 第五次：合法位址、合法 payload、不合法參數（R3），只能記一筆含 invalid_argument 的 WARNING。
    caplog.clear()
    result = send_webhook(
        secret_url,
        {"title": "T", "message": "leak-me-42"},
        max_attempts=0,
        transport=httpx.MockTransport(counting),
        sleep=sleeps.append,
    )
    records = module_records()
    all_texts += [r.getMessage() for r in records]
    all_errors.append(result.error)
    assert result == WebhookResult(ok=False, status=None, attempts=0, error="invalid_argument")
    assert len(calls) == 0
    warnings = [r for r in records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "invalid_argument" in warnings[0].getMessage()

    # WHY：五次呼叫的日誌全文與 error 欄位都不得含 userinfo、port、path、query、fragment、payload。
    for marker in leaked_markers:
        assert not any(marker in text for text in all_texts), marker
        assert not any(marker in error for error in all_errors if error), marker


def test_AT_001_6_1_notify_escalation_posts_via_send_webhook(tmp_path, caplog):
    # WHY：AC-001-6 要求 webhook_url 有值時 notify_escalation 以固定四鍵 payload 呼叫
    # send_webhook 恰一次，且結果只進日誌；日誌不得洩漏 webhook_url（可能夾帶 token）。
    url = "https://hooks.example.com/escalation"
    cfg = AppConfig()
    cfg.checkpoint_dir = str(tmp_path)
    cfg.notification.enabled = False
    cfg.notification.webhook_url = url
    dump_path = str(tmp_path / "dump.md")
    outcomes = [
        WebhookResult(ok=True, status=200, attempts=1, error=None),
        WebhookResult(ok=False, status=503, attempts=3, error="http_503"),
    ]
    expected = [
        (logging.INFO, "status=200", "attempts=1"),
        (logging.WARNING, "error=http_503", "attempts=3"),
    ]
    caplog.set_level(logging.INFO, logger="autoclaude.utils.notifier")

    alert_log = tmp_path / "escalation_alert.log"
    results = iter(outcomes)

    def fake_send(*args, **kwargs):
        # WHY：先落 escalation_alert.log、後呼叫 webhook；呼叫當下本輪那一行必須已寫入。
        assert alert_log.exists()
        assert len(alert_log.read_text(encoding="utf-8").splitlines()) == len(seen_calls) + 1
        seen_calls.append(args)
        return next(results)

    seen_calls = []
    with patch("autoclaude.utils.notifier.send_webhook", side_effect=fake_send) as mock_send:
        for round_no, (level, frag_a, frag_b) in enumerate(expected, start=1):
            caplog.clear()
            notify_escalation("ESC", "step failed", dump_path, cfg)

            # WHY：每輪恰呼叫一次，位置參數為 (url, payload)，不帶關鍵字參數。
            assert mock_send.call_count == round_no
            call = mock_send.call_args_list[-1]
            assert call.args[0] == url
            assert call.kwargs == {}
            payload = call.args[1]
            assert set(payload) == {"title", "message", "dump_path", "timestamp"}
            assert payload["title"] == "ESC"
            assert payload["message"] == "step failed"
            assert payload["dump_path"] == dump_path
            # WHY：timestamp 必須是帶時區的 ISO 8601，否則跨時區事件無法排序。
            assert datetime.fromisoformat(payload["timestamp"]).tzinfo is not None
            # WHY：R 條文要求 UTC（offset 為 0），不是任意本地時區。
            assert datetime.fromisoformat(payload["timestamp"]).utcoffset() == timedelta(0)

            webhook_records = [
                r
                for r in caplog.records
                if r.name == "autoclaude.utils.notifier" and "Webhook" in r.getMessage()
            ]
            assert len(webhook_records) == 1
            assert webhook_records[0].levelno == level
            assert frag_a in webhook_records[0].getMessage()
            assert frag_b in webhook_records[0].getMessage()

            # WHY：不得殘留舊的「尚未實作」警告，也不得把 webhook_url 寫進日誌。
            all_texts = [r.getMessage() for r in caplog.records]
            assert not any("尚未實作" in text for text in all_texts)
            assert not any("hooks.example.com" in text for text in all_texts)

            # WHY：既有的 escalation_alert.log 落檔行為不因接線而改變。
            assert (tmp_path / "escalation_alert.log").exists()


def test_AT_001_6_2_no_webhook_url_keeps_behaviour_unchanged(tmp_path, caplog):
    # WHY：AC-001-6／R12 要求 webhook_url 為 None 或空字串時完全不走 Webhook 路徑：
    # 不呼叫 send_webhook、不留任何 Webhook 日誌，且 escalation_alert.log 的既有格式逐字不變。
    # 其中行首 naive 本地時間戳不得被改成帶時區，否則根層平台鎖會變紅（見 R12 末句）。
    cfg = AppConfig()
    cfg.checkpoint_dir = str(tmp_path)
    cfg.notification.enabled = False
    dump_path = str(tmp_path / "dump.md")
    caplog.set_level(logging.DEBUG, logger="autoclaude.utils.notifier")

    with patch("autoclaude.utils.notifier.send_webhook") as mock_send:
        for empty_url in (None, ""):
            cfg.notification.webhook_url = empty_url
            notify_escalation("ESC", "step failed", dump_path, cfg)

    # WHY：無位址時 send_webhook 一次都不能被呼叫，否則空設定會變成對空位址發送。
    mock_send.assert_not_called()
    # WHY：無位址時不得產生任何含 Webhook 字樣的日誌（R12）。
    assert not any("Webhook" in r.getMessage() for r in caplog.records)

    alert_log = tmp_path / "escalation_alert.log"
    assert alert_log.exists()
    lines = alert_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    for line in lines:
        assert line.endswith(f" | ESC | step failed | dump={dump_path}")
        stamp = line.split(" | ", 1)[0]
        # WHY：既有 naive 本地時間戳必須維持原樣（tzinfo 為 None），R12 的鎖依賴此事實。
        assert datetime.fromisoformat(stamp).tzinfo is None
