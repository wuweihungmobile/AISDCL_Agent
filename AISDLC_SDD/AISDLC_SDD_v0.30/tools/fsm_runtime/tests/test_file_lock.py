"""Tests for file_lock advisory lock (M2 QA Round-2 P1-1)."""
from __future__ import annotations

import contextlib
import multiprocessing as mp
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import file_lock as fl_mod  # noqa: E402
from tools.fsm_runtime.file_lock import _try_unlink, file_lock  # noqa: E402


def _worker_increment(lock_path: str, counter_path: str, hold_ms: int) -> None:
    """Acquire lock, read counter, sleep, increment, write — simulates the
    read-modify-write pattern of the CONTEXT-LEDGER hooks."""
    lock_p = Path(lock_path)
    counter_p = Path(counter_path)
    with file_lock(lock_p, timeout=30.0):
        value = int(counter_p.read_text(encoding="utf-8") or "0")
        time.sleep(hold_ms / 1000.0)
        counter_p.write_text(str(value + 1), encoding="utf-8")


class FileLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_parallel_writes_do_not_lose_increments(self) -> None:
        """4 processes each +1 on a shared counter — final must equal 4."""
        counter = self.root / "counter.txt"
        counter.write_text("0", encoding="utf-8")
        lock_path = self.root / "counter.lock"
        procs = []
        for _ in range(4):
            p = mp.Process(
                target=_worker_increment,
                args=(str(lock_path), str(counter), 50),
            )
            p.start()
            procs.append(p)
        for p in procs:
            p.join(timeout=30)
            self.assertFalse(p.is_alive(), "worker hung")
            self.assertEqual(p.exitcode, 0, "worker errored")
        self.assertEqual(int(counter.read_text(encoding="utf-8")), 4)

    def test_stale_lock_auto_cleared(self) -> None:
        """Sentinel older than 30s must be treated as abandoned and reclaimed."""
        lock_path = self.root / "resource.lock"
        lock_path.write_text("pid=99999 stale", encoding="utf-8")
        # Backdate mtime by 60 seconds so the guard treats it as stale.
        old_mtime = time.time() - 60
        import os as _os
        _os.utime(lock_path, (old_mtime, old_mtime))
        # Acquisition should succeed within timeout despite the stale sentinel.
        with file_lock(lock_path, timeout=2.0):
            self.assertTrue(lock_path.exists())
        # After release the sentinel must be gone.
        self.assertFalse(lock_path.exists())

    def test_timeout_raises_when_held(self) -> None:
        """If another holder is active, acquisition must TimeoutError."""
        lock_path = self.root / "busy.lock"
        # Manually place a FRESH sentinel (mtime = now, so not stale).
        lock_path.write_text("pid=12345 fresh", encoding="utf-8")
        start = time.time()
        with self.assertRaises(TimeoutError):
            with file_lock(lock_path, timeout=0.3):
                self.fail("should not acquire")  # pragma: no cover
        elapsed = time.time() - start
        # Timeout must be ≥ configured (with small slack) and < stale threshold.
        self.assertGreaterEqual(elapsed, 0.25)
        self.assertLess(elapsed, 5.0)
        # Cleanup — sentinel remains (not ours to remove).
        lock_path.unlink()


class UnremovableSentinelTests(unittest.TestCase):
    """R60 A-02 回歸鎖：sentinel 刪不掉時的兩條路徑都不得逸出 ``OSError``。

    WHY：兩處移除 sentinel 的 ``unlink`` 原本只捕 ``FileNotFoundError``。Windows 上
    只要有第三方持著該 sentinel 的 handle（防毒掃描、搜尋索引器、備份代理，或本模組
    docstring 自己邀請的 post-mortem 讀取者），``unlink`` 就丟 ``PermissionError``
    ([WinError 32])——本機實測會**逸出 context manager**（呼叫端的例外契約裡沒有這個
    型別）且 sentinel 洩漏。修法沿用 ``tools/dev_start.py::_release_bootstrap_lock``
    的 ``except OSError: pass`` 慣例。

    第二個鎖（``..._times_out_instead_of_spinning``）守的是修法本身的陷阱：陳舊回收
    分支原本無條件 ``continue``，那會**跳過 deadline 檢查與 sleep**——單純把窄捕放寬成
    ``except OSError: pass`` 會把「刪不掉的陳舊 sentinel」變成 100% CPU 的無窮忙迴圈
    （比原缺陷更糟）。故該分支必須「刪不掉就落回 deadline/sleep」。
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    @staticmethod
    def _deny_unlink(_self, *_a, **_kw):
        raise PermissionError(
            32, "程序無法存取檔案，因為檔案正由另一個程序使用。（注入）"
        )

    def test_release_does_not_raise_when_sentinel_cannot_be_removed(self) -> None:
        """平台中立載具：注入 ``PermissionError`` 於 finally 的 unlink。"""
        lock_path = self.root / "ledger.lock"
        with mock.patch.object(Path, "unlink", self._deny_unlink):
            with file_lock(lock_path, timeout=2.0):
                pass   # 正常離開 → finally 走 unlink → 注入的 PermissionError
        self.assertTrue(
            lock_path.exists(),
            "載具失效：注入未生效（sentinel 竟被刪掉），本測試對本缺陷無鑑別力",
        )
        lock_path.unlink()

    @unittest.skipUnless(
        sys.platform == "win32",
        "[WINDOWS-NATIVE-ONLY] 真 handle 佔用語意只在 Windows 成立（POSIX unlink 允許刪除"
        "已開啟檔案）——R67-F27 補標籤，供版本樹 conftest 的 terminal summary 彙整可見度",
    )
    def test_release_survives_real_open_handle_on_windows(self) -> None:
        """原生 Windows 載具：不注入例外，用真的 open handle 觸發 [WinError 32]。"""
        lock_path = self.root / "held.lock"
        held = None
        try:
            with file_lock(lock_path, timeout=2.0):
                held = open(lock_path, "rb")   # 第三方持 handle（AV／索引器語意）
        finally:
            if held is not None:
                held.close()
        self.assertTrue(lock_path.exists(), "載具失效：Windows 竟刪得掉被開啟的檔案")
        lock_path.unlink()

    def test_try_unlink_retries_transient_permission_denied(self) -> None:
        """D31-4：windows-compat-ci #220／#221 同型回歸鎖——瞬時 PermissionError 2 次後第 3 次成功，
        `_try_unlink` 必須回 True（不得在第一次失敗就放棄回 False，逼下一位等滿 30s 陳舊門檻）。"""
        target = self.root / "retry.lock"
        target.write_text("pid=1 fresh", encoding="utf-8")
        orig_unlink = Path.unlink
        calls = {"n": 0}

        def flaky_unlink(self, *a, **kw):
            if self == target and calls["n"] < 2:
                calls["n"] += 1
                raise PermissionError(32, "程序無法存取檔案（模擬瞬時佔用）")
            return orig_unlink(self, *a, **kw)

        with mock.patch.object(Path, "unlink", flaky_unlink), \
             mock.patch("tools.fsm_runtime.file_lock.time.sleep", return_value=None):
            self.assertTrue(_try_unlink(target))
        self.assertEqual(calls["n"], 2, "應在重試預算內於第 3 次成功，不多不少")
        self.assertFalse(target.exists())

    def test_unremovable_stale_sentinel_times_out_instead_of_spinning(self) -> None:
        lock_path = self.root / "stale_held.lock"
        lock_path.write_text("pid=99999 stale", encoding="utf-8")
        old = time.time() - 60          # 遠超 _STALE_AFTER_SEC=30 → 判定陳舊
        os.utime(lock_path, (old, old))

        outcome: list[object] = []

        def attempt() -> None:
            try:
                with file_lock(lock_path, timeout=0.3):
                    outcome.append("acquired")
            except BaseException as exc:  # noqa: BLE001
                outcome.append(exc)

        with mock.patch.object(Path, "unlink", self._deny_unlink):
            worker = threading.Thread(target=attempt, daemon=True)
            start = time.time()
            worker.start()
            worker.join(timeout=5.0)
            elapsed = time.time() - start

        self.assertFalse(
            worker.is_alive(),
            "陳舊 sentinel 刪不掉時 file_lock 沒有在 5s 內收場——無窮忙迴圈復發"
            "（陳舊回收分支的 continue 跳過了 deadline 檢查）",
        )
        self.assertEqual(len(outcome), 1)
        self.assertIsInstance(
            outcome[0], TimeoutError,
            f"應以 TimeoutError 收場（呼叫端已有降級路徑），實際為 {outcome[0]!r}",
        )
        self.assertLess(elapsed, 5.0)
        lock_path.unlink()


class AcquireTransientPermissionErrorTests(unittest.TestCase):
    """R158 P1 回歸鎖（windows-compat-ci #250，run 35452796159）：``_write_sentinel`` 的 round-label-ok
    ``os.open(O_CREAT|O_EXCL|O_WRONLY)`` 在 Windows delete-pending 態下丟 ``PermissionError``
    （非 ``FileExistsError``），逸出 acquire 迴圈原本只接 ``FileExistsError`` 的 ``except``，
    炸穿 ``file_lock()`` 的 context manager（同批次唯一一份 traceback 精確釘在此處，非
    ``_try_unlink`` 也非 ``counter.txt`` 的寫入）。修法只加寬 acquire 迴圈的例外類型，且**只在
    Windows**（模組常數 ``_ACQUIRE_TRANSIENT_ERRORS``）——POSIX 上 ``O_EXCL`` 的
    ``PermissionError`` 幾乎必是真正的權限問題（沒有 delete-pending 語意），吞掉會掩蓋根因
    （鐵律三）。三支測試皆顯式 patch ``_ACQUIRE_TRANSIENT_ERRORS``，不依賴實際跑測試的主機
    平台（``os.name``）——同一份測試在 mac 開發機與 Windows CI 上斷言的是同一套邏輯分支。
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_transient_permission_error_on_acquire_is_retried_like_file_exists(self) -> None:
        """常數含 PermissionError（模擬 Windows）＋ os.open 第一次丟 PermissionError、第二次
        放行 ⇒ 視為暫時佔用，重試後正常取得鎖，不逸出。"""
        lock_path = self.root / "counter.lock"
        real_open = os.open
        calls = {"n": 0}

        def flaky_open(path, flags, *a, **kw):
            if calls["n"] == 0 and path == str(lock_path):
                calls["n"] += 1
                raise PermissionError(
                    13,
                    "程序無法存取檔案（模擬 Windows delete-pending CreateFile ACCESS_DENIED）",
                )
            return real_open(path, flags, *a, **kw)

        with mock.patch.object(
            fl_mod, "_ACQUIRE_TRANSIENT_ERRORS", (FileExistsError, PermissionError)
        ), mock.patch.object(fl_mod.os, "open", flaky_open):
            with file_lock(lock_path, timeout=2.0):
                self.assertTrue(lock_path.exists())
        self.assertEqual(
            calls["n"], 1, "應在第 1 次瞬時 PermissionError 後、第 2 次成功取得鎖"
        )
        self.assertFalse(lock_path.exists())

    def test_posix_default_lets_permission_error_escape_on_acquire(self) -> None:
        """守鐵律三：常數不含 PermissionError（POSIX 現況）時，真正的權限問題必須原樣逸出，
        不得被誤判成鎖競爭而吞掉／轉型成別的例外型別。"""
        lock_path = self.root / "denied.lock"
        real_open = os.open

        def always_denied(path, flags, *a, **kw):
            if path == str(lock_path):
                raise PermissionError(13, "程序無法存取檔案（模擬真正的權限問題，非鎖競爭）")
            return real_open(path, flags, *a, **kw)

        with mock.patch.object(fl_mod, "_ACQUIRE_TRANSIENT_ERRORS", (FileExistsError,)), \
             mock.patch.object(fl_mod.os, "open", always_denied):
            with self.assertRaises(PermissionError):
                with file_lock(lock_path, timeout=2.0):
                    self.fail("should not acquire")  # pragma: no cover
        self.assertFalse(lock_path.exists())

    def test_permanent_permission_error_is_bounded_by_timeout_when_treated_as_transient(
        self,
    ) -> None:
        """邊界檢查（QA T2 風險提醒）：常數含 PermissionError 時，若 PermissionError 其實是
        永久性的（非鎖競爭，例如目錄唯讀），行為從『立即拋出 PermissionError』變成『等滿
        timeout 才拋 TimeoutError』——這是加寬 except 的已知代價（掩蓋根因型別），但必須仍在
        `timeout` 內收場，不得無界等待。"""
        lock_path = self.root / "stuck.lock"
        real_open = os.open

        def always_denied(path, flags, *a, **kw):
            if path == str(lock_path):
                raise PermissionError(13, "永久性權限錯誤（模擬目錄唯讀，非鎖競爭）")
            return real_open(path, flags, *a, **kw)

        with mock.patch.object(
            fl_mod, "_ACQUIRE_TRANSIENT_ERRORS", (FileExistsError, PermissionError)
        ), mock.patch.object(fl_mod.os, "open", always_denied):
            start = time.time()
            with self.assertRaises(TimeoutError):
                with file_lock(lock_path, timeout=0.3):
                    self.fail("should not acquire")  # pragma: no cover
            elapsed = time.time() - start
        self.assertGreaterEqual(elapsed, 0.25)
        self.assertLess(elapsed, 5.0)
        self.assertFalse(lock_path.exists())


class StatTransientPermissionErrorTests(unittest.TestCase):
    """R158 P1 追加（主控親驗）：接住 acquire 迴圈 ``os.open`` 的 ``PermissionError`` 後， round-label-ok
    ``file_lock()`` 緊接著呼叫 ``_is_stale(lock_path)``，其內部 ``path.stat()`` 在同一個
    Windows delete-pending 態下同樣會丟 ``PermissionError``（``_is_stale`` 本體只接
    ``FileNotFoundError``，本輪不改）——逃逸點只是從 ``os.open`` 搬到 ``stat``。修法只在
    ``file_lock()`` 呼叫 ``_is_stale`` 那一行窄窄地吞掉 ``_STAT_TRANSIENT_ERRORS``（Windows 才
    非空），視為「本輪還不知道是否陳舊」而非「必是死鎖」，POSIX 上（空 tuple）逐字不變。兩支
    測試皆顯式 patch ``_ACQUIRE_TRANSIENT_ERRORS``／``_STAT_TRANSIENT_ERRORS``，不依賴主機平台。

    🔴 2026-09-28 R181 訂正（DEF-200-341）：本 class 的「``path.stat()`` 同樣會丟 round-label-ok
    ``PermissionError``」前提在 Windows 11 26200／Python 3.11.9 真 delete-pending 態下實測**不
    成立**（``os.stat()`` 回 OK）；本 class 兩支測試皆為 mock 注入，保留作為「常數已加寬時的行為
    契約」回歸鎖，不代表已觀測到真實逃逸點。真機確定性重現見 ``RealDeletePendingTests``。
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_transient_stat_permission_error_after_acquire_retry_is_tolerated_on_windows(
        self,
    ) -> None:
        """兩常數皆含 PermissionError（模擬 Windows）＋ os.open 與 Path.stat 第一次都丟
        PermissionError、之後放行 ⇒ 視為『本輪還不知道是否陳舊』重試，最終正常取得鎖，不逸出。"""
        lock_path = self.root / "counter.lock"
        real_open = os.open
        real_stat = Path.stat
        open_calls = {"n": 0}
        stat_calls = {"n": 0}

        def flaky_open(path, flags, *a, **kw):
            if open_calls["n"] == 0 and path == str(lock_path):
                open_calls["n"] += 1
                raise PermissionError(
                    13,
                    "程序無法存取檔案（模擬 Windows delete-pending CreateFile ACCESS_DENIED）",
                )
            return real_open(path, flags, *a, **kw)

        def flaky_stat(self_path, *a, **kw):
            if self_path == lock_path and stat_calls["n"] == 0:
                stat_calls["n"] += 1
                raise PermissionError(13, "程序無法存取檔案（模擬同一個 delete-pending 態）")
            return real_stat(self_path, *a, **kw)

        with mock.patch.object(
            fl_mod, "_ACQUIRE_TRANSIENT_ERRORS", (FileExistsError, PermissionError)
        ), mock.patch.object(
            fl_mod, "_STAT_TRANSIENT_ERRORS", (PermissionError,)
        ), mock.patch.object(
            fl_mod.os, "open", flaky_open
        ), mock.patch.object(Path, "stat", flaky_stat):
            with file_lock(lock_path, timeout=2.0):
                self.assertTrue(lock_path.exists())
        self.assertEqual(open_calls["n"], 1, "os.open 應恰好瞬時失敗 1 次後成功")
        self.assertEqual(stat_calls["n"], 1, "Path.stat 應恰好瞬時失敗 1 次（被本修法吞掉）")
        self.assertFalse(lock_path.exists())

    def test_posix_default_lets_stat_permission_error_escape(self) -> None:
        """守鐵律三：``_STAT_TRANSIENT_ERRORS`` 為空 tuple（POSIX 現況）時，即使 acquire 層已
        把 PermissionError 當暫時佔用重試，``_is_stale`` 的 ``stat()`` 撞到的 PermissionError
        仍必須原樣逸出，不得被吞成『非陳舊』。"""
        lock_path = self.root / "denied.lock"
        real_open = os.open
        real_stat = Path.stat

        def flaky_open(path, flags, *a, **kw):
            if path == str(lock_path):
                raise PermissionError(
                    13, "程序無法存取檔案（模擬 delete-pending CreateFile ACCESS_DENIED）"
                )
            return real_open(path, flags, *a, **kw)

        def denied_stat(self_path, *a, **kw):
            if self_path == lock_path:
                raise PermissionError(13, "程序無法存取檔案（模擬真正的權限問題，非鎖競爭）")
            return real_stat(self_path, *a, **kw)

        with mock.patch.object(
            fl_mod, "_ACQUIRE_TRANSIENT_ERRORS", (FileExistsError, PermissionError)
        ), mock.patch.object(
            fl_mod, "_STAT_TRANSIENT_ERRORS", ()
        ), mock.patch.object(
            fl_mod.os, "open", flaky_open
        ), mock.patch.object(Path, "stat", denied_stat):
            with self.assertRaises(PermissionError):
                with file_lock(lock_path, timeout=2.0):
                    self.fail("should not acquire")  # pragma: no cover
        self.assertFalse(lock_path.exists())


@contextlib.contextmanager
def _real_delete_pending(path: Path):
    """R181 helper（DEF-200-341）：用 ctypes legacy ``FileDispositionInfo`` 對 ``path`` 製造 round-label-ok
    Windows 真正的 delete-pending 態（非 mock 注入）——建檔→以 ``FILE_SHARE_DELETE`` 開 handle→
    設 disposition（DeleteFile=TRUE）→yield handle→finally ``CloseHandle``（此時作業系統才真的
    刪除該名稱）。``ctypes.wintypes`` 依賴 ``ctypes.WinDLL``，在 POSIX 上不存在會於 import 當下
    炸例外，故本函式把 ``import ctypes`` / ``import ctypes.wintypes`` 放在函式本體內（呼叫時才
    執行），module 收集期在任何平台都不會觸發；呼叫端 ``RealDeletePendingTests`` 整個 class 已
    用 ``@unittest.skipUnless(sys.platform == "win32", ...)`` 圍住，非 Windows 上測試方法本身
    不會被執行。本體另以 ``if sys.platform == "win32":`` 作用域內守衛包住全部 Windows 專屬
    API（鐵律三：根層 ``tools/tests/test_platform_neutral_paths.py`` 的
    ``TestForeignPlatformApiIsGuarded`` 掃到本檔，decorator 不算作用域內守衛）。
    """
    if sys.platform == "win32":
        import ctypes
        import ctypes.wintypes as wt

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        generic_read = 0x80000000
        delete_access = 0x00010000
        file_share_read = 1
        file_share_write = 2
        file_share_delete = 4
        open_existing = 3
        file_attribute_normal = 0x80
        invalid_handle_value = ctypes.c_void_p(-1).value
        file_disposition_info_class = 4

        class _FileDispositionInfo(ctypes.Structure):
            # Win32 ``BOOLEAN`` 是 unsigned char；只寫 0/1，用 ``c_ubyte`` 貼近原型（複審 should-fix）
            _fields_ = [("DeleteFile", ctypes.c_ubyte)]

        k32.CreateFileW.restype = wt.HANDLE
        k32.CreateFileW.argtypes = [
            wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE,
        ]
        k32.SetFileInformationByHandle.restype = wt.BOOL
        k32.SetFileInformationByHandle.argtypes = [
            wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD,
        ]
        k32.CloseHandle.argtypes = [wt.HANDLE]

        path.write_text(f"pid={os.getpid()} real-delete-pending\n", encoding="utf-8")
        handle = k32.CreateFileW(
            str(path),
            generic_read | delete_access,
            file_share_read | file_share_write | file_share_delete,
            None,
            open_existing,
            file_attribute_normal,
            None,
        )
        if handle == invalid_handle_value:
            raise OSError(f"CreateFileW failed, GetLastError={ctypes.get_last_error()}")
        try:
            info = _FileDispositionInfo(1)
            ok = k32.SetFileInformationByHandle(
                handle, file_disposition_info_class, ctypes.byref(info), ctypes.sizeof(info)
            )
            if not ok:
                raise OSError(
                    f"SetFileInformationByHandle failed, GetLastError={ctypes.get_last_error()}"
                )
            yield handle
        finally:
            k32.CloseHandle(handle)
    else:  # pragma: no cover — 呼叫端 class 已 skipUnless(win32)，此分支只為守衛完整
        raise unittest.SkipTest("[WINDOWS-NATIVE-ONLY] 真 delete-pending 態只在 Windows 可製造")


@unittest.skipUnless(
    sys.platform == "win32",
    "[WINDOWS-NATIVE-ONLY] 真 delete-pending 態只能用 Windows FileDispositionInfo 製造"
    "（POSIX 無此語意）——標籤供版本樹 conftest terminal summary 彙整",
)
class RealDeletePendingTests(unittest.TestCase):
    """R181 真機驗證鎖（2026-09-28，DEF-200-341）：帳本原文宣稱 ``_is_stale()`` 的 ``stat()`` round-label-ok
    在 Windows delete-pending 態會丟 ``PermissionError``——主控親測（ctypes legacy
    ``FileDispositionInfo``）證實這個前提不成立：``os.stat()`` 在該態下回 OK，真正丟
    ``PermissionError`` 的只有 ``os.open(O_CREAT|O_EXCL)``。本 class 用真態（非 mock）補上
    ``StatTransientPermissionErrorTests``／``AcquireTransientPermissionErrorTests`` 注入式
    契約測試缺的那一半（兩者保留），把「本機 141 次全綠」背後的結構性原因（``os.unlink`` 走
    POSIX 立即刪除語意、從未真的進入 delete-pending 視窗）與「加寬 ``_ACQUIRE_TRANSIENT_ERRORS``
    確實接得住真態逃逸點」兩件事一起釘死，不再只靠 mock 佈置的信念。已知殘餘風險：本 class
    依賴 CPython 把 ERROR_ACCESS_DENIED 映成 ``PermissionError``，未來版本若改映射本 class 會
    轉紅——那正是要被看見的訊號，不是要繞過的假紅。
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_acquire_survives_real_delete_pending_sentinel(self) -> None:
        """WHY：這是本包的核心正面案例——真 delete-pending 視窗期間，加寬後的
        ``file_lock()`` 必須真的等過去而不是巧合地繞過。用 ``threading.Event`` 確保主執行緒
        在背景執行緒把 disposition 設好之後才開始取鎖（避免時序競態讓測試偶然對到「還沒進入
        delete-pending」的窗口，那樣通過就對缺陷沒有鑑別力）。elapsed >= 0.2s 證明真的等過
        背景持有的 0.3s 視窗，不是第一次嘗試就矇對。"""
        lock_path = self.root / "sentinel.lock"
        ready_event = threading.Event()

        def _hold() -> None:
            with _real_delete_pending(lock_path):
                ready_event.set()
                time.sleep(0.3)
            # 離開 with 區塊呼叫 CloseHandle，作業系統在此刻才真的刪除該名稱。

        thread = threading.Thread(target=_hold)
        thread.start()
        self.assertTrue(
            ready_event.wait(timeout=5.0),
            "背景執行緒未能在期限內完成 disposition 設定，測試佈置本身有問題",
        )
        start = time.time()
        with file_lock(lock_path, timeout=2.0) as acquired_path:
            elapsed = time.time() - start
            self.assertTrue(acquired_path.exists())
        thread.join(timeout=5.0)
        self.assertFalse(thread.is_alive(), "背景持有執行緒未能如期結束")
        self.assertGreaterEqual(
            elapsed, 0.2, "elapsed 太短，疑似沒有真的等過 delete-pending 視窗"
        )
        self.assertLess(elapsed, 2.0, "elapsed 逼近或超過 timeout，取鎖不應該這麼慢")
        self.assertFalse(lock_path.exists())

    def test_is_stale_and_o_excl_shapes_under_real_delete_pending(self) -> None:
        """WHY：把 CI #250 的形態（``os.open(O_CREAT|O_EXCL)`` 丟 PermissionError）與 R181 訂正 round-label-ok
        的事實（``_is_stale()`` 的 ``stat()`` 在同一個真態下不丟例外、回傳 False）一起釘住——
        這兩件事合起來才是「為何只需要加寬 acquire 迴圈、不需要動 ``_is_stale`` 本體」的完整
        證據，缺一都會讓 file_lock.py 模組 docstring 裡的訂正段落淪為未驗證的宣稱。"""
        lock_path = self.root / "shape.lock"
        with _real_delete_pending(lock_path):
            self.assertFalse(
                fl_mod._is_stale(lock_path),
                "真 delete-pending 態下 stat() 應回 OK 且 mtime 新鮮（不應被誤判陳舊）",
            )
            with self.assertRaises(PermissionError):
                os.close(
                    os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                )

    def test_without_windows_widening_the_real_delete_pending_escapes(self) -> None:
        """WHY：紅端鎖——證明本 class 有鑑別力。把 ``_ACQUIRE_TRANSIENT_ERRORS`` patch 回 POSIX
        形狀（不含 PermissionError）後，同一個真態下 ``file_lock()`` 必須讓 PermissionError
        原樣逸出，而不是被吞成鎖競爭重試。這格證明「加寬」修法本身正是讓
        ``test_acquire_survives_real_delete_pending_sentinel`` 變綠的原因，不是環境偶然。"""
        lock_path = self.root / "posix_shape.lock"
        ready_event = threading.Event()

        def _hold() -> None:
            with _real_delete_pending(lock_path):
                ready_event.set()
                time.sleep(0.3)

        thread = threading.Thread(target=_hold)
        thread.start()
        self.assertTrue(
            ready_event.wait(timeout=5.0),
            "背景執行緒未能在期限內完成 disposition 設定，測試佈置本身有問題",
        )
        with mock.patch.object(fl_mod, "_ACQUIRE_TRANSIENT_ERRORS", (FileExistsError,)):
            with self.assertRaises(PermissionError):
                with file_lock(lock_path, timeout=2.0):
                    self.fail("should not acquire")  # pragma: no cover
        thread.join(timeout=5.0)
        self.assertFalse(thread.is_alive(), "背景持有執行緒未能如期結束")


if __name__ == "__main__":
    unittest.main()
