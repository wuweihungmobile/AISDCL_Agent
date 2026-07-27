"""R57 回歸鎖：`sanitize_component()` 對「保留名 + 尾隨空白 + 副檔名」不得放行.

為何重要（Rule 12 fail-loud）：`sanitize_component()` 的職責之一是讓輸出檔名在
Windows checkout 上可建立。Windows 保留裝置名（CON/PRN/AUX/NUL/COM[0-9]/LPT[0-9]）
一旦成為檔名基底即無法建檔，故本函式對其加 `_` 前綴。但判定順序有缺口：

    sanitized = sanitized.rstrip(" .")      # 作用於「整串」
    stem = sanitized.split(".", 1)[0]       # 才取基底

`"CON .txt"` 整串結尾是 `t`，`rstrip(" .")` 不觸發；取 stem 後得到 `"CON "`——
帶尾隨空白，`^(CON|...)$` 不匹配 → **整組逃逸**（R57 實測：`'CON .txt'`、
`'NUL .log'`、`'LPT1 .yaml'` 修復前皆原樣輸出，未加前綴；對照 `'CON.txt'` 則正確
輸出 `'_CON.txt'`）。

**R58 訂正（DEF-101-B13）：上段原本接著寫「Win32 解析裝置名時會忽略基底名後的尾隨
空白，故這類檔名在 Windows 上仍會撞到裝置」——已被實測證偽**（原生 Windows 11 +
git 2.51.0.windows.1，raw Win32 ctypes CreateFileW + GetFileType）：`<dir>\\CON .txt`
是 FILE_TYPE_DISK 的**普通檔案**、listdir 看得到，沒有撞到任何裝置；尾隨空白/句點
也不是被拒絕，而是被 Win32 **靜默剝除改名**（`'trail_space '` 落地成 `trail_space`）。
會在比對 DOS 裝置名前忽略尾隨空白的是 **Git for Windows** 的 `is_valid_win32_path()`
／`mingw_open()`：`git add "<dir>/CON .txt"` 實測 rc=128（`open(...): No such file or
directory` + `unable to index file`），檔案建得起來卻永遠進不了 index。
本函式的行為完全不變（危害真實存在），只訂正理由。誤植的機制已造成實害——清單照
「Win32 裝置名解析」推導，於是漏掉真正會讓 git 失效的 `CONIN$`／`CONOUT$`
（DEF-101-B3，R58 同輪修復，見下方 `CONSOLE_HANDLE_RESERVED`）。完整量測、三段式
涵蓋面宣稱與可覆核的量測指令收斂在根層 `tools/check_ntfs_paths.py` 檔頭
〈實測機制〉一節（本檔不重抄，免多處漂移）。

四處同因實作（R57 全 repo 掃描確認恰四處，皆已修）：
1. `tools/check_ntfs_paths.py::_ntfs_seg_bad`
2. `tools/git-hooks/pre-commit::_ntfs_seg_bad`
   ——上兩處的行為對等鎖見根層 `tools/tests/test_ntfs_trailing_space_device_name.py`
3. `AutoClaude/autoclaude/utils/logger.py::_sanitize_log_filename`
   ——鎖見根層 `tools/tests/test_windows_forbidden_filename_parity.py`
     `::TestTrailingSpaceReservedNameCrossConsistency`
4. 本檔鎖住的 `AISDLC_SDD/scripts/component_sanitizer.py::sanitize_component`

樣本清單刻意與上述三處**同一組形態**，但因子專案邊界不可跨界 import 根層測試模組，
故在此重新列出——這是明文承認的重複，替代方案（把樣本抽成 monorepo 共用資料檔）
會讓 AISDLC_SDD 反向依賴根層 `tools/`，違反本子專案可獨立 checkout 的既有前提。

**R57 round 1 Architect 打臉紀錄（本段原文的自述代價當輪即兌現）**：本檔誕生時，
上段原本只承認「代價是四處樣本可能各自演化」就收手，結果**同一輪就已經演化了**——
SDD 側 benign 清單漏抄根層的 `" .txt"`（4 筆 vs 5 筆），而該樣本正是最貼近本次修法
風險的一格；同段 docstring 還逐字宣稱「以及**五個**必須放行的良性樣本」，自稱五個、
實為四個。教訓：**「明文承認代價」不等於「處理了代價」**，承認而不設鎖等於放任。
故 R57 round 1 收尾補上機械鎖——根層
`tools/tests/test_windows_forbidden_filename_parity.py::TestCrossSubprojectSampleParity`
以**純文字/AST 讀取本檔**（只讀檔、不 import 生產程式碼，不違反「子專案邊界不可跨界
import」的既有裁定）斷言兩份 reserved/benign 清單逐字相同。實作四份為必要重複，
但**樣本資料沒有理由分歧**——這是正確的切法。改動本檔任一清單時，根層那支鎖會紅。

修復刻意只 `rstrip(" ")` 不含 `"."`：改成 `rstrip(" .")` 會讓純句點片段（`".."`／
`"."`）的 stem 被吃空成 `""`，破壞既有「路徑穿越退化為 untitled」的防禦——本檔
`test_path_traversal_defence_not_broken` 即為此設鎖。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from component_sanitizer import sanitize_component  # noqa: E402

# 保留名 + 尾隨空白 + 副檔名：必須加 `_` 前綴
RESERVED_TRAILING_SPACE = [
    "CON .txt",
    "NUL .log",
    "LPT1 .yaml",
    "con .txt",  # 大小寫不敏感
    "COM9   .md",  # 多個尾隨空白
    "AUX .tar.gz",  # 多重副檔名疊加尾隨空白
    "CONIN$ .txt",  # R58：console handle 名疊加尾隨空白（實測 git add rc=128）
]

# 剝除尾隨空白後不得誤判成保留名（防修復引入偽陽性）
BENIGN_TRAILING_SPACE = [
    " .txt",  # 純空白 base → 剝完是空字串，不可匹配任何保留名（R57 round 1 Architect
    #            指出本樣本原本缺席——而它正是最貼近本次修法風險的一格：修復註解自述
    #            「只 rstrip(' ') 不含 '.'，否則 stem 會被吃空」，這個樣本就是「吃空」的邊界）
    "   .gitignore",
    "CONSOLE .txt",  # 非保留名
    "COM10 .txt",  # COM10 不在 COM[0-9] 內
    "my con file.txt",  # 保留名出現在中段，非 base
    "CONERR$ .txt",  # R58 證偽樣本：git 實測接受 CONERR$（rc=0），不得因形似而誤擋
]

# R58（DEF-101-B3）：console handle 保留名的**無尾隨空白**基本形態。與上兩組分開列，
# 因為缺陷成因不同——上兩組是「判定順序缺口」（rstrip 作用於整串），本組是「清單本身
# 缺項」（四處都只收 CON/PRN/AUX/NUL/COM[0-9]/LPT[0-9]，照 Win32 裝置名解析推導而漏掉
# git 黑名單獨有的兩個帶 `$` 名）。本組同樣受根層
# `TestCrossSubprojectSampleParity` 鎖住與根層逐字相同。
CONSOLE_HANDLE_RESERVED = [
    "CONIN$",
    "CONOUT$",
    "conin$",  # 大小寫不敏感（實測 git 對小寫同樣 rc=128）
    "CONIN$.txt",  # 帶副檔名（實測 git 同樣 rc=128）
    "CONOUT$.tar.gz",  # 多重副檔名
]

# 形似但實測 git 接受（rc=0、成功入 index）→ 四處皆不得誤擋
CONSOLE_HANDLE_BENIGN = [
    "CONERR$",  # 裸名實測 FILE_TYPE_DISK＝根本不是裝置；掃描員原提案含它，經實測證偽
    "CONPRN$",  # 同上（不在 Git for Windows 黑名單內）
    "CONIN",  # 少了 `$` 即非保留名
    "CONOUT",
    "CONINX",  # `$` 位置換成其他字元
]


class TestReservedNameWithTrailingSpace(unittest.TestCase):
    def test_flags_reserved_name_with_trailing_space_before_extension(self) -> None:
        for name in RESERVED_TRAILING_SPACE:
            with self.subTest(name=name):
                out = sanitize_component(name)
                self.assertTrue(
                    out.startswith("_"),
                    f"未攔下尾隨空白保留裝置名 {name!r}：{out!r}",
                )

    def test_does_not_flag_benign_trailing_space_names(self) -> None:
        for name in BENIGN_TRAILING_SPACE:
            with self.subTest(name=name):
                out = sanitize_component(name)
                self.assertFalse(
                    out.startswith("_"),
                    f"誤攔非保留裝置名 {name!r}：{out!r}",
                )

    def test_existing_reserved_forms_unchanged(self) -> None:
        """R57 修復不得改變修復前已正確處理的既有形態（零回歸）。"""
        for name, expected in [
            ("CON.txt", "_CON.txt"),
            ("CON  ", "_CON"),  # 尾隨空白被整串 rstrip 吃掉，本就正確
            ("lpt5.tar.gz", "_lpt5.tar.gz"),  # DEF-101-295 多重副檔名
        ]:
            with self.subTest(name=name):
                self.assertEqual(sanitize_component(name), expected)

    def test_path_traversal_defence_not_broken(self) -> None:
        """純句點片段仍須退化為 untitled——證明修復只剝空白、沒有連句點一起剝。"""
        for name in ("..", ".", "...."):
            with self.subTest(name=name):
                self.assertEqual(sanitize_component(name), "untitled")


class TestConsoleHandleReservedNames(unittest.TestCase):
    """R58（DEF-101-B3）：`CONIN$`／`CONOUT$` 必須加 `_` 前綴；`CONERR$` 等不得誤擋。

    為何重要（Rule 9 — 測意圖）：本函式的職責之一是讓輸出檔名在 Windows checkout 上
    **可被 git 追蹤**。`CONIN$`／`CONOUT$` 的失效形態不是 open() 拋錯，而是「檔案建得
    起來、git 說不存在」——實測（原生 Windows 11 + git 2.51.0.windows.1）
    `os.path.isfile()` 為 True 但 `git add` rc=128（`open(...): No such file or
    directory` + `unable to index file`）。FSM state 檔一旦命中這格就永遠無法提交，
    且以 git 為載具的 CI／dogfooding 取證會得到極難診斷的失效。

    負樣本同等重要：R58 掃描員原提案要把 `CONERR$` 與另兩者並列封鎖，經實測證偽
    （裸名為 FILE_TYPE_DISK 普通檔案、`git add` rc=0 成功入 index）。把證偽結論也
    釘死，避免下一輪有人憑形似加回去——`CONIN$` 當初之所以會漏，正是因為清單是照
    「Win32 裝置名解析」推導而非量測 git 行為得來的。
    """

    def test_flags_console_handle_reserved_names(self) -> None:
        for name in CONSOLE_HANDLE_RESERVED:
            with self.subTest(name=name):
                out = sanitize_component(name)
                self.assertTrue(
                    out.startswith("_"),
                    f"未攔下 console handle 保留名 {name!r}：{out!r}",
                )

    def test_does_not_flag_benign_lookalikes(self) -> None:
        for name in CONSOLE_HANDLE_BENIGN:
            with self.subTest(name=name):
                out = sanitize_component(name)
                self.assertFalse(
                    out.startswith("_"),
                    f"誤擋 git 實測接受的名字 {name!r}：{out!r}",
                )


class TestReservedPrefixDoesNotBreakLengthCap(unittest.TestCase):
    """`_` 前綴在截斷之後才加，故加完可能超出 `_MAX_COMPONENT_LEN`（R57 round 2 QA）。

    此為**既有**缺陷（`'CON.' + 'z'*100` 在 R57 之前就已回傳 81 字元）；R57 為修
    DEF-101-478 加的 `.rstrip(" ")` 只是把「保留名 + 尾隨空白」也納入會觸發的輸入
    集合，擴大了暴露面。上限存在的理由見模組常數註解：`_MAX_COMPONENT_LEN = 80`
    遠低於 NTFS 單檔名 255 上限，是為前後綴（`FSM-STATE-…-{track}.yaml`）留餘裕——
    溢出 1 字元本身不會立刻炸，但會侵蝕該餘裕，且違反本函式對呼叫端的長度承諾。
    """

    def test_output_never_exceeds_cap_even_when_prefixed(self) -> None:
        from component_sanitizer import _MAX_COMPONENT_LEN

        for name in (
            "CON" + " " * 3 + "." + "x" * 100,  # R57 新納入的觸發集合（尾隨空白）
            "CON." + "z" * 100,  # R57 之前就會觸發的既有形態
            "lpt9" + " " * 5 + "." + "w" * 200,
        ):
            with self.subTest(name=name[:20]):
                out = sanitize_component(name)
                self.assertTrue(out.startswith("_"), f"保留名未被前綴：{out[:30]!r}")
                self.assertLessEqual(
                    len(out), _MAX_COMPONENT_LEN,
                    f"輸出 {len(out)} 字元 > 上限 {_MAX_COMPONENT_LEN}：{out[:40]!r}",
                )

    def test_retruncation_does_not_reintroduce_ntfs_violations(self) -> None:
        """重新截斷後不得以空白/句點結尾（NTFS 禁止），也不得退回成保留名。"""
        from component_sanitizer import _WIN_RESERVED_NAME_RE

        for name in ("CON" + " " * 78 + ".txt", "AUX." + " ." * 60, "NUL" + "." * 200):
            with self.subTest(name=name[:20]):
                out = sanitize_component(name)
                self.assertFalse(out.endswith((" ", ".")), f"以空白/句點結尾：{out!r}")
                self.assertIsNone(
                    _WIN_RESERVED_NAME_RE.match(out.split(".", 1)[0].rstrip(" ")),
                    f"截斷後 stem 退回成保留裝置名：{out!r}",
                )


if __name__ == "__main__":
    unittest.main()
