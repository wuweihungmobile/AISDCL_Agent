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
# R69：平台判斷收斂至 utils/platform_caps.py，故平台模擬改 patch 該處
# （`patch("<mod>.sys.platform", ...)` 本來就是在改全域 sys 模組的屬性，
# 只是掛載點換成唯一的決策點；模擬語意不變）。
_PLATFORM_MOD = "autoclaude.utils.platform_caps"


class TestNotifyDisabled:
    @patch(f"{_MOD}._try_plyer")
    def test_disabled_skips_all_backends(self, mock_plyer):
        notify("T", "M", enabled=False)
        mock_plyer.assert_not_called()


class TestDarwinOsascriptFallback:
    @patch(f"{_MOD}.subprocess.run")
    @patch(f"{_MOD}._try_win10toast")
    @patch(f"{_MOD}._try_plyer", return_value=False)
    @patch(_PLATFORM_MOD + ".sys.platform", "darwin")
    def test_plyer_fail_falls_to_osascript(self, mock_plyer, mock_toast, mock_run):
        """darwin 上 plyer 失敗（缺 pyobjus）→ osascript 承接，不再往 win10toast 走。"""
        notify("標題", "訊息")
        assert mock_run.called
        mock_toast.assert_not_called()

    @patch(f"{_MOD}.subprocess.run")
    @patch(f"{_MOD}._try_plyer", return_value=False)
    @patch(_PLATFORM_MOD + ".sys.platform", "darwin")
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
    @patch(f"{_MOD}._try_win10toast", return_value=False)
    @patch(f"{_MOD}._try_plyer", return_value=False)
    @patch(_PLATFORM_MOD + ".sys.platform", "linux")
    def test_non_darwin_non_windows_skips_both_platform_backends(
        self, mock_plyer, mock_toast, mock_run,
    ):
        """linux 上兩條平台專屬後端都不該被叫到，只降級為 log。

        🔴 R82（ACC-01）本測試**期望值翻面**，原因是被測行為被修正了，不是判準放鬆：
        本測試的 R4 版逐字記載「`notify()` 對 `_try_win10toast()` 的呼叫本身沒有平台
        守門…在裝有 win10toast 的機器上會彈出一個 threaded=True 的背景視窗訊息迴圈
        執行緒…是真實副作用洩漏」——也就是它當時**斷言的正是那個缺陷**（缺守門 ⇒ 非
        Windows 也照呼叫，只靠 import 失敗兜底）。R82 在 notifier.notify() 補上
        `is_windows()` 守門後，正確行為就是這裡的 `assert_not_called()`。
        """
        notify("T", "M")
        mock_run.assert_not_called()
        mock_toast.assert_not_called()

    @patch(f"{_MOD}.subprocess.run")
    @patch(f"{_MOD}._try_win10toast", return_value=False)
    @patch(f"{_MOD}._try_plyer", return_value=False)
    @patch(_PLATFORM_MOD + ".sys.platform", "win32")
    def test_windows_still_reaches_win10toast(self, mock_plyer, mock_toast, mock_run):
        """反向對照：守門不得把 Windows 上該走的 fallback 也一併擋掉。

        只斷言「非 Windows 不呼叫」的鎖沒有鑑別力——把 `_try_win10toast` 整支刪掉也會綠。
        """
        notify("T", "M")
        mock_run.assert_not_called()
        mock_toast.assert_called_once()


class TestOsascriptFailureDowngradesToLog:
    @patch(f"{_MOD}._try_win10toast", return_value=False)
    @patch(f"{_MOD}._try_plyer", return_value=False)
    @patch(_PLATFORM_MOD + ".sys.platform", "darwin")
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
