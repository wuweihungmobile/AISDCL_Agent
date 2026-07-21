"""_rmtree_windows_safe() Windows 韌性 rmtree 意圖鎖（R15 ARCH-R15-REV-3）。

WHY：
sync_exposed_skills.py --write 模式的 `_rmtree_windows_safe()`（R15 SCAN-B-2 修復）
在真實 CI/nightly/hook 管線中從未被觸發——`--write` 只由人工手動呼叫，`--check`
（ci-gate 唯一自動路徑）不會走到這支函式；POSIX 上唯讀屬性亦很少真的讓 unlink
失敗（刪除只需父目錄可寫）。故其 chmod-retry 與 TypeError fallback 兩條防禦路徑
零測試覆蓋、零自動化訊號（R15 四方一審 Architect ARCH-R15-REV-3 揭露）。本測試
以 mock 直接驅動 shutil.rmtree 呼叫 onerror callback，模擬 Windows 唯讀/暫鎖
情境，鎖住三態：正常刪除零副作用、chmod-retry 成功、TypeError fallback 回拋
原始錯誤、最終仍失敗時包裝為帶可讀訊息的 RuntimeError。
"""
from __future__ import annotations

from unittest import mock

import pytest

from scripts import sync_exposed_skills


def test_normal_deletion_has_no_side_effect(tmp_path):
    """無錯誤觸發的正常刪除路徑：與裸 shutil.rmtree 行為等價，零副作用。"""
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "file.txt").write_text("data", encoding="utf-8")
    sync_exposed_skills._rmtree_windows_safe(str(victim))
    assert not victim.exists()


def test_chmod_retry_succeeds_after_permission_error(tmp_path):
    """onerror 觸發後 chmod 清唯讀 + func(p) 重試成功 → 正常返回，不拋例外。"""
    target = str(tmp_path / "locked_file.txt")
    retry_func = mock.Mock()  # 呼叫不拋例外＝模擬重試成功

    def fake_rmtree(path, onerror):
        exc_info = (PermissionError, PermissionError("denied"), None)
        onerror(retry_func, target, exc_info)

    with mock.patch.object(sync_exposed_skills.shutil, "rmtree",
                            side_effect=fake_rmtree), \
         mock.patch.object(sync_exposed_skills.os, "chmod") as fake_chmod:
        sync_exposed_skills._rmtree_windows_safe(str(tmp_path))
    fake_chmod.assert_called_once_with(target, sync_exposed_skills.stat.S_IWRITE)
    retry_func.assert_called_once_with(target)


def test_typeerror_from_fd_based_rmtree_reraises_original_error(tmp_path):
    """R15 沙盒煙測實證：Python 3.11 POSIX fd-based rmtree 的 func 可能是
    os.open（簽名不符）→ func(p) 重試拋 TypeError；須回拋「原始」錯誤（非
    TypeError 本身），外層再包裝為可讀 RuntimeError，不洩漏裸 TypeError。
    """
    target = str(tmp_path / "x")

    def retry_func_raises_typeerror(p):
        raise TypeError("os.open() missing required argument: 'flags'")

    def fake_rmtree(path, onerror):
        exc_info = (PermissionError, PermissionError("original failure"), None)
        onerror(retry_func_raises_typeerror, target, exc_info)

    with mock.patch.object(sync_exposed_skills.shutil, "rmtree",
                            side_effect=fake_rmtree), \
         mock.patch.object(sync_exposed_skills.os, "chmod"):
        with pytest.raises(RuntimeError, match="無法刪除舊父層鏡像"):
            sync_exposed_skills._rmtree_windows_safe(str(tmp_path))


def test_persistent_failure_wrapped_with_readable_message(tmp_path):
    """chmod 後重試仍 OSError（檔案遭編輯器/防毒暫鎖）→ 外層包裝為帶路徑與
    可讀提示訊息的 RuntimeError，不留裸 traceback。
    """
    target = str(tmp_path / "still_locked")

    def retry_func_raises_oserror(p):
        raise OSError("still locked by another process")

    def fake_rmtree(path, onerror):
        exc_info = (PermissionError, PermissionError("original"), None)
        onerror(retry_func_raises_oserror, target, exc_info)

    outer_path = str(tmp_path)
    with mock.patch.object(sync_exposed_skills.shutil, "rmtree",
                            side_effect=fake_rmtree), \
         mock.patch.object(sync_exposed_skills.os, "chmod"):
        with pytest.raises(RuntimeError) as exc_info:
            sync_exposed_skills._rmtree_windows_safe(outer_path)
    msg = str(exc_info.value)
    assert "請關閉佔用該目錄的編輯器/防毒後重試" in msg
    # 外層錯誤訊息引用的是 _rmtree_windows_safe 的最外層參數（呼叫者傳入的
    # 鏡像根目錄），不是 onerror 內部觸發失敗的個別檔案路徑（target）。
    assert outer_path in msg
