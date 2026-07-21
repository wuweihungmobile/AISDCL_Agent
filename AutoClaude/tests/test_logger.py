"""DEF-87-002：production logger Windows cp950 編碼容錯（improving_89）。

驗證 `_EncodingSafeStreamHandler` 在任何 console 編碼下都不丟 UnicodeEncodeError，
同時 utf-8 環境位元級零退化。以 io.TextIOWrapper(BytesIO, encoding="cp950") 在 utf-8
平台重現 Windows cp950 行為——故本檔可在 Linux CI 跑。
"""
import io
import logging
from unittest import mock

import pytest

from autoclaude.utils.logger import (
    RawStreamLogger,
    _EncodingSafeStreamHandler,
    _sanitize_log_filename,
    setup_logger,
)

# step_log repr 內實際出現、cp950 無法編碼的字元（DEF-87-002 原始崩潰元兇）
_CHECK = "✓"  # ✓


def _make_stream(encoding: str):
    """回傳 (text_stream, raw_bytesio)；raw 供測試後取回實際寫入的 bytes。

    TextIOWrapper 預設 errors='strict' → 寫入不可編碼字元會丟 UnicodeEncodeError，
    正是 Windows cp950 console 的行為。
    """
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding=encoding, newline="")
    return stream, raw


def _make_record(msg: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="autoclaude", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=(), exc_info=None,
    )


def test_rtm_89_1_cp950_stream_no_raise():
    """RTM-89-1：cp950 stream 下 emit 含 ✓ 不丟例外、不觸發 handleError
    （消除 DEF-87-002 非致命噪音的核心保證）。"""
    stream, _ = _make_stream("cp950")
    handler = _EncodingSafeStreamHandler(stream)
    handler.handleError = mock.Mock()  # 若進 except 兜底會被呼叫

    # 不可拋例外
    handler.emit(_make_record(f"Playbook 結束 | step_log={_CHECK}"))

    handler.handleError.assert_not_called()


def test_rtm_89_2_cp950_backslash_escaped_not_dropped():
    """RTM-89-2：cp950 環境下不可編碼字元轉 backslash escape 寫出、整行不遺失。"""
    stream, raw = _make_stream("cp950")
    handler = _EncodingSafeStreamHandler(stream)

    handler.emit(_make_record(f"結束 {_CHECK} done"))

    written = raw.getvalue().decode("cp950")
    assert "\\u2713" in written           # ✓ 轉成 backslash escape
    assert _CHECK not in written          # 原字元未直接寫入（cp950 無法編碼）
    assert "done" in written              # 整行尾段保留、未遺失
    assert "結束" in written              # 行首段保留


def test_rtm_89_3_utf8_lossless():
    """RTM-89-3：utf-8 環境零退化——✓ 原樣寫出（含 U+2713，位元級無損）。"""
    stream, raw = _make_stream("utf-8")
    handler = _EncodingSafeStreamHandler(stream)

    handler.emit(_make_record(f"Playbook 結束 | {_CHECK}"))

    written = raw.getvalue().decode("utf-8")
    assert _CHECK in written              # 真正的 ✓ 原樣保留
    assert "\\u2713" not in written       # 未被誤 escape


def test_rtm_89_4_cp950_encodable_cjk_preserved():
    """RTM-89-4：cp950 可編碼的中文（如「結束」）不被誤 escape，只 escape 真正不可編碼者。"""
    stream, raw = _make_stream("cp950")
    handler = _EncodingSafeStreamHandler(stream)

    handler.emit(_make_record(f"結束{_CHECK}"))

    written = raw.getvalue().decode("cp950")
    assert "結束" in written              # cp950 可編碼 → 原字保留
    assert "\\u2713" in written           # 僅 ✓ 被 escape


def test_rtm_89_5_setup_logger_uses_safe_handler_idempotent(tmp_path):
    """RTM-89-5：setup_logger 的 console handler 為 _EncodingSafeStreamHandler，
    且重複呼叫去重註冊行為保持（冪等）。"""
    lg = logging.getLogger("autoclaude")
    saved = lg.handlers[:]
    lg.handlers.clear()
    try:
        root = setup_logger(log_dir=str(tmp_path / "logs"))
        console = [h for h in root.handlers if isinstance(h, _EncodingSafeStreamHandler)]
        assert len(console) == 1          # 確實使用安全 handler

        n_before = len(root.handlers)
        again = setup_logger(log_dir=str(tmp_path / "logs"))
        assert again is root
        assert len(root.handlers) == n_before  # 去重註冊冪等，不重複加 handler
    finally:
        lg.handlers.clear()
        lg.handlers.extend(saved)


def test_def_87_002_handleerror_fallback_on_broken_stream():
    """補測 except 兜底：stream.write 自身崩潰時仍走 handleError，不向上拋
    （沿用父類 StreamHandler 容錯語意，確保 logging 永不打斷主流程）。"""
    class _BrokenStream:
        encoding = "utf-8"

        def write(self, _):
            raise OSError("broken pipe")

        def flush(self):  # pragma: no cover - 不會被觸達
            pass

    handler = _EncodingSafeStreamHandler(_BrokenStream())
    handler.handleError = mock.Mock()

    handler.emit(_make_record("anything"))  # 不可向上拋

    handler.handleError.assert_called_once()


def test_recursionerror_propagates_not_swallowed():
    """RecursionError 須上拋（鏡像 CPython StreamHandler.emit 防無限遞迴語意），
    不可被 handleError 吞掉——否則遞迴爆掉時 logging 會自我遞迴。"""
    class _RecursionStream:
        encoding = "utf-8"

        def write(self, _):
            raise RecursionError("stack overflow")

        def flush(self):  # pragma: no cover - 不會被觸達
            pass

    handler = _EncodingSafeStreamHandler(_RecursionStream())
    handler.handleError = mock.Mock()

    with pytest.raises(RecursionError):
        handler.emit(_make_record("anything"))

    handler.handleError.assert_not_called()


# --- DEF-101（Mac/Windows 相容性 R16）：raw log 檔名淨化 + RawStreamLogger 崩潰防護 ---
#
# 根因：raw log 檔名由 playbook 作者自訂的 task.step_id 組成（見
# infra/adapters/pty_executor.py、execution/prompt_dispatcher.py），像
# `step_id: "Step 1: Setup"` 這種很自然的寫法在 macOS/Linux 上完全合法（檔名規則
# 寬鬆，僅 / 與 NUL 不合法），但同一字串在 Windows(NTFS) 上因含冒號會讓
# RawStreamLogger.__init__ 的 open() 拋出未捕捉的 OSError，導致該 step 每次重試
# 都對同一個壞檔名再炸一次——且此問題在 Mac/Linux 開發與 CI 上完全隱形。
# 以下測試不需要真的在 Windows 上跑：直接對 sanitize 函式套用 Windows 禁用字元集合
# 驗證輸出、並用「目標目錄不存在」構造一個跨平台皆會讓 open() 失敗的情境驗證 fallback。


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Step 1: Setup", "Step 1_ Setup"),      # 冒號（P1 案例的真實觸發字元）
        ("a<b", "a_b"),
        ('a"b|c?d*e', "a_b_c_d_e"),
        (r"C:\Users\dev", "C__Users_dev"),  # 反斜線冒號需淨化 # platform-ok: 字面值非路徑 join
        ("trailing dot.", "trailing dot"),        # NTFS 不允許以句點結尾
        ("trailing space ", "trailing space"),    # NTFS 不允許以空白結尾
    ],
)
def test_sanitize_log_filename_strips_windows_forbidden_chars(raw, expected):
    """驗證 Windows 禁用字元（< > : " | ? * \\）被取代、結尾空白/句點被剝除——
    這是 P1 修復的核心保證：淨化後的檔名在任何平台都能安全 open()。"""
    assert _sanitize_log_filename(raw) == expected


@pytest.mark.parametrize("reserved", ["CON", "con", "PRN", "NUL", "COM1", "LPT9"])
def test_sanitize_log_filename_guards_windows_reserved_device_names(reserved):
    """CON/PRN/AUX/NUL/COM1-9/LPT1-9（大小寫不敏感）為 Windows 保留裝置名，
    即使不含禁用字元也必須被改名，否則 Windows 上 open() 會開到裝置而非檔案。"""
    result = _sanitize_log_filename(reserved)
    assert result != reserved
    assert result == f"_{reserved}"


def test_raw_stream_logger_survives_windows_forbidden_step_id(tmp_path):
    """端對端：step_id 含 Windows 禁用字元時，RawStreamLogger 仍能成功開檔寫入，
    不再讓整個 playbook 執行因未捕捉的 OSError 而崩潰（P1 根因情境重現）。"""
    log_path = tmp_path / 'playbook_Step 1: Setup.log'

    rl = RawStreamLogger(log_path)
    try:
        rl.write(b"hello\n")
    finally:
        rl.close()

    written = [p for p in tmp_path.iterdir() if p.is_file()]
    assert len(written) == 1
    assert ":" not in written[0].name
    assert written[0].read_bytes() == b"hello\n"


def test_raw_stream_logger_falls_back_when_open_fails(tmp_path, caplog):
    """open() 因非檔名成因失敗時（此處以不存在且不自動建立的目錄模擬，跨平台皆會
    觸發 FileNotFoundError），RawStreamLogger 必須 fallback 到暫存目錄而非向上拋例外
    ——驗證 try/except 縱深防禦確實生效，而非只靠淨化這一層。"""
    missing_dir_path = tmp_path / "does_not_exist" / "playbook_T01.log"

    with caplog.at_level(logging.WARNING, logger="autoclaude.utils.logger"):
        rl = RawStreamLogger(missing_dir_path)
    try:
        rl.write(b"fallback-data\n")
    finally:
        rl.close()

    assert any("開啟 log 檔" in r.message for r in caplog.records)
    assert not missing_dir_path.exists()
