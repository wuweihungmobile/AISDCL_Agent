"""notifier 三層 fallback 單元測試（P2 macOS 靜默降級修復）。

WHY：ESCALATION 桌面通知是引擎核心行為。macOS 上 plyer 缺 pyobjus 必然失敗，
若無 darwin 分支會無聲降級為 log-only；本檔驗證 osascript fallback 真的承接、
注入安全（argv 參數化、不做字串插值），且 osascript 失敗時仍守住 log 最後手段。
"""
from __future__ import annotations

import logging
import subprocess
from unittest.mock import patch

from autoclaude.utils import notifier
from autoclaude.utils.notifier import _try_osascript, notify

_MOD = "autoclaude.utils.notifier"


class TestNotifyDisabled:
    @patch(f"{_MOD}._try_plyer")
    def test_disabled_skips_all_backends(self, mock_plyer):
        notify("T", "M", enabled=False)
        mock_plyer.assert_not_called()


class TestDarwinOsascriptFallback:
    @patch(f"{_MOD}.subprocess.run")
    @patch(f"{_MOD}._try_win10toast")
    @patch(f"{_MOD}._try_plyer", return_value=False)
    @patch(f"{_MOD}.sys.platform", "darwin")
    def test_plyer_fail_falls_to_osascript(self, mock_plyer, mock_toast, mock_run):
        """darwin 上 plyer 失敗（缺 pyobjus）→ osascript 承接，不再往 win10toast 走。"""
        notify("標題", "訊息")
        assert mock_run.called
        mock_toast.assert_not_called()

    @patch(f"{_MOD}.subprocess.run")
    @patch(f"{_MOD}._try_plyer", return_value=False)
    @patch(f"{_MOD}.sys.platform", "darwin")
    def test_osascript_args_are_parameterized(self, mock_plyer, mock_run):
        """注入安全：title/message 以 argv 獨立參數傳入，不插值進 AppleScript 字串。"""
        evil = "x\" & do shell script \"rm -rf ~\" -- '"
        notify("T'itle", evil)
        argv = mock_run.call_args.args[0]
        assert argv[:2] == ["osascript", "-e"]
        # 腳本本體為固定常數（on run argv 參數化），不含使用者輸入
        assert argv[2] == notifier._OSASCRIPT_NOTIFY
        assert evil not in argv[2]
        # message / title 為獨立 process 參數（item 1 / item 2 of argv）
        assert argv[3] == evil
        assert argv[4] == "T'itle"

    @patch(f"{_MOD}.subprocess.run")
    @patch(f"{_MOD}._try_plyer", return_value=False)
    @patch(f"{_MOD}.sys.platform", "linux")
    def test_non_darwin_skips_osascript(self, mock_plyer, mock_run):
        notify("T", "M")
        mock_run.assert_not_called()


class TestOsascriptFailureDowngradesToLog:
    @patch(f"{_MOD}._try_win10toast", return_value=False)
    @patch(f"{_MOD}._try_plyer", return_value=False)
    @patch(f"{_MOD}.sys.platform", "darwin")
    def test_osascript_error_falls_to_log(self, mock_plyer, mock_toast, caplog):
        """osascript 非零退出 → 降級 log 最後手段（不拋例外、不吞掉通知內容）。"""
        err = subprocess.CalledProcessError(1, "osascript")
        with patch(f"{_MOD}.subprocess.run", side_effect=err):
            with caplog.at_level(logging.INFO, logger=_MOD):
                notify("T", "M")
        assert any("[NOTIFY]" in r.message for r in caplog.records)

    def test_try_osascript_returns_false_when_binary_missing(self):
        with patch(f"{_MOD}.subprocess.run", side_effect=FileNotFoundError("osascript")):
            assert _try_osascript("T", "M") is False

    def test_try_osascript_returns_false_on_timeout(self):
        err = subprocess.TimeoutExpired(cmd="osascript", timeout=10)
        with patch(f"{_MOD}.subprocess.run", side_effect=err):
            assert _try_osascript("T", "M") is False

    def test_try_osascript_returns_true_on_success(self):
        with patch(f"{_MOD}.subprocess.run") as mock_run:
            assert _try_osascript("T", "M") is True
            kwargs = mock_run.call_args.kwargs
            assert kwargs.get("check") is True
            assert kwargs.get("timeout") == 10
