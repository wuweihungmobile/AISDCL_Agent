"""R57 回歸鎖：Windows 保留裝置名「保留名 + 尾隨空白 + 副檔名」形態不得逃逸。

缺陷（R57 掃描 B1）：`tools/check_ntfs_paths.py` 與 `tools/git-hooks/pre-commit`
的 `_ntfs_seg_bad()` 都以「切到第一個點」取 base 後直接比對保留名清單——
`CON .txt` 的 base 是 `"CON "`（帶尾隨空白），`^(CON|...)$` / case pattern `CON`
皆不匹配；而「整段以空白或句點結尾」那一條只看整段（`CON .txt` 結尾是 `t`）也
不成立 → 兩道判準之間漏出一個縫，`CON .txt`／`NUL .log`／`LPT1 .yaml` 全數放行。

**R58 訂正（DEF-101-B13）：本檔原本寫「Windows 實情：Win32 解析裝置名時會忽略基底名
後的尾隨空白，此形態在 Windows checkout 仍會撞到裝置名」——已被實測證偽。** 量測環境
＝原生 Windows 11 Pro + git 2.51.0.windows.1；手法＝raw Win32（ctypes `CreateFileW`
+ `GetFileType`，**`restype` 必須顯式設成 `wintypes.HANDLE`**，否則 64-bit handle 被
ctypes 預設的 `c_int` 截斷，CreateFileW 失敗會被誤讀成 `FILE_TYPE_UNKNOWN`——本輪第一
次量測即踩到此坑）＋ 在系統暫存目錄建一次性 git repo（刻意不在工作樹跑 git 寫指令）：

  - 帶目錄前綴的 `CON`／`AUX`／`PRN`／`COM1`／`LPT1`／`CONIN$`／`CON .txt`／`NUL .log`
    一律被 Win32 建成**普通檔案**（FILE_TYPE_DISK、listdir 看得到），**沒有**撞到裝置。
    唯一例外是 `NUL`：帶目錄前綴仍是裝置（`<dir>\\NUL` → FILE_TYPE_CHAR、無此檔）。
  - 尾隨空白／句點**不是「不允許」而是被靜默剝除改名**：`'trail_space '` 落地成
    `trail_space`、`'dots...'` → `dots`（CreateFileW 皆成功）。
  - 真正拒絕的層是 **Git for Windows**（`is_valid_win32_path()`／`mingw_open()` 的
    DOS 裝置名黑名單）：`git add` 對上述路徑實測 rc=128
    （`open(...): No such file or directory` + `unable to index file`）；尾隨空白路徑
    連 `git update-index --add --cacheinfo` 都 rc=128 `error: Invalid path 'trailing '`。

兩處實作的攔截行為完全不變（危害真實存在，只是層別不同），只訂正理由。誤植的機制已
造成實害——清單照「Win32 裝置名解析」推導，於是漏掉真正會讓 git 失效的 `CONIN$`／
`CONOUT$`（DEF-101-B3，R58 同輪修復）。完整量測（含 COM/LPT 數字全掃、`CONERR$` 證偽）、
三段式涵蓋面宣稱與可覆核的量測指令收斂在 `tools/check_ntfs_paths.py` 檔頭
〈實測機制〉一節（本檔不重抄，免多處漂移）。

本檔只鎖 monorepo 根層兩處實作（Python CI 版 + bash hook 版）的**行為對等**。
同一缺陷形態另存在於兩處，**R57 主控收尾時已一併修復並各自設鎖**：
`AutoClaude/autoclaude/utils/logger.py._sanitize_log_filename`（第三方，鎖在
`test_windows_forbidden_filename_parity.py::TestTrailingSpaceReservedNameCrossConsistency`）
與 `AISDLC_SDD/scripts/component_sanitizer.py.sanitize_component`（第四處，屬子專案
邊界不可跨界 import，鎖在 `AISDLC_SDD/scripts/tests/
test_component_sanitizer_reserved_trailing_space.py`）。四處成因相同：都是
`rstrip(" .")` 作用於整串、之後才 `split(".", 1)[0]`，故 `CON .txt` 的 stem 皆為 `"CON "`。
"""

import unittest

# 共用「pre-commit `_ntfs_seg_bad()` 動態抽取 + bash 可用性探測」的既有實作，
# 不再照抄一份（照抄正是本 repo 反覆修同一缺陷多處的根因）。
import test_windows_forbidden_filename_parity as _parity  # noqa: E402

check_ntfs_paths = _parity.check_ntfs_paths

# R57 收尾：兩份樣本清單已上移至 `test_windows_forbidden_filename_parity.py` 作為
# SSOT（該檔同時承載 logger 側第三方鎖，樣本必須同一份才叫「交叉一致」），本檔
# 改為 import 取用。方向單向（parity 檔不 import 本檔）以免循環 import。
RESERVED_TRAILING_SPACE_SEGMENTS = _parity.RESERVED_TRAILING_SPACE_SEGMENTS
BENIGN_TRAILING_SPACE_SEGMENTS = _parity.BENIGN_TRAILING_SPACE_SEGMENTS


class TestPythonCiChecker(unittest.TestCase):
    """`tools/check_ntfs_paths.py::_ntfs_seg_bad()`（CI 全量 tracked 掃描版）。"""

    def test_flags_reserved_name_with_trailing_space_before_extension(self) -> None:
        for seg in RESERVED_TRAILING_SPACE_SEGMENTS:
            with self.subTest(seg=seg):
                reason = check_ntfs_paths._ntfs_seg_bad(f"docs/{seg}")
                self.assertIsNotNone(reason, f"未攔下保留裝置名形態 {seg!r}")
                self.assertIn("保留裝置名", reason)

    def test_does_not_flag_benign_trailing_space_segments(self) -> None:
        for seg in BENIGN_TRAILING_SPACE_SEGMENTS:
            with self.subTest(seg=seg):
                reason = check_ntfs_paths._ntfs_seg_bad(f"docs/{seg}")
                self.assertIsNone(reason, f"誤判良性路徑段 {seg!r}：{reason}")


@unittest.skipIf(_parity._BASH is None, _parity._SKIP_REASON)
class TestBashHookChecker(unittest.TestCase):
    """`tools/git-hooks/pre-commit::_ntfs_seg_bad()`（本機 commit 閘版）——
    動態抽取真實函式原始碼執行，非靜態文字比對。"""

    def test_flags_reserved_name_with_trailing_space_before_extension(self) -> None:
        for seg in RESERVED_TRAILING_SPACE_SEGMENTS:
            with self.subTest(seg=seg):
                rc, out = _parity._run_bash_seg_check(f"docs/{seg}")
                self.assertEqual(rc, 0, f"bash 版未攔下保留裝置名形態 {seg!r}（rc={rc}）")
                self.assertIn("保留裝置名", out)

    def test_does_not_flag_benign_trailing_space_segments(self) -> None:
        for seg in BENIGN_TRAILING_SPACE_SEGMENTS:
            with self.subTest(seg=seg):
                rc, out = _parity._run_bash_seg_check(f"docs/{seg}")
                self.assertEqual(rc, 1, f"bash 版誤判良性路徑段 {seg!r}：{out.strip()}")


if __name__ == "__main__":
    unittest.main()
