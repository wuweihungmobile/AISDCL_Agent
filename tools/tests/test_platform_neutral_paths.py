#!/usr/bin/env python3
"""tools/tests 原始碼「Windows 磁碟機假路徑」自我檢測（R11 A1c；R11 複審 SD-2/ARCH-2 補強）.

WHY：R11 真 Mac 首跑實證——測試裡把 D:/repo 這種磁碟機假路徑字串塞給 Path()，
它只在 Windows 是絕對路徑；POSIX 上 `repo_root / 絕對路徑` 的 pathlib join 會退化
成串接（D:/repo/D:/repo/…）、resolve 後恆不相等 → Windows 全綠、Mac/Linux 假紅
（test_check_hooks_liveness.py TestIsHooksEffective 兩案例實際紅過）。修法是改用
_platform_helpers.ABS_FAKE_REPO 平台中立常數；本測試機械掃描 tools/tests/*.py
原始碼，防未來有人複製舊 pattern 再踩一次。

R11 四方複審補強（SD-2/ARCH-2）：原 regex 只抓「Path( 後緊接引號＋大寫磁碟機
＋正斜線」單一形態——漏抓 r/f 等字串前綴變體、反斜線形態 X:\\、小寫磁碟機，
以及**裸字串**磁碟機路徑常數（原病灶正是不經 Path( 直呼的裸字串）。改為抓
「任意字串字面值以磁碟機路徑開頭」（引號後緊接單一字母＋冒號＋斜線或反斜線；
匹配起點是引號本身，故 r/f/b 前綴一律涵蓋）。並：
  (a) 每行先剝 `#` 註解尾再掃（註解舉例不誤報；heuristic 不解析字串內的 #，
      字串內含 # 且其後才出現磁碟機路徑的極端形態會漏掃，屬可接受取捨）；
  (b) 豁免顯式平台語意 PureWindowsPath(/PurePosixPath(（該行本來就是在寫
      特定平台路徑）與 _platform_helpers.py（win32 分支的單一合法定義點）；
  (c) 支援行尾 `# platform-ok: <理由>` 豁免標記（合法命中須逐行附理由明示處置）。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
# 任意字串字面值以「單一字母磁碟機 + 冒號 + / 或 \」開頭即命中；
# 匹配起點為引號本身，r/f/b 等前綴與 Path( 包裹與否皆無關（裸字串同樣命中）。
_DRIVE_STR_RE = re.compile(r"""["'][A-Za-z]:[/\\]""")
# 唯一整檔豁免：平台中立常數的單一定義點（win32 分支本來就該寫磁碟機路徑）。
_ALLOWED = {"_platform_helpers.py"}
_OK_MARKER = "platform-ok:"
_EXPLICIT_PLATFORM = ("PureWindowsPath(", "PurePosixPath(")


def _scan_file(py: Path) -> list[str]:
    offenders: list[str] = []
    for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), start=1):
        if _OK_MARKER in line:  # (c) 行尾豁免標記（附理由）
            continue
        code = line.split("#", 1)[0]  # (a) 剝註解尾（heuristic，見 docstring）
        if any(tok in code for tok in _EXPLICIT_PLATFORM):  # (b) 顯式平台語意
            continue
        if _DRIVE_STR_RE.search(code):
            offenders.append(f"{py.name}:{lineno}: {line.strip()}")
    return offenders


class TestPlatformNeutralPaths(unittest.TestCase):
    def test_no_windows_drive_fake_paths(self) -> None:
        offenders: list[str] = []
        for py in sorted(_TESTS_DIR.glob("*.py")):
            if py.name in _ALLOWED:
                continue
            offenders.extend(_scan_file(py))
        self.assertEqual(
            offenders,
            [],
            "發現 Windows 磁碟機假路徑字面值（POSIX 上非絕對路徑 → join 語意分歧假紅）"
            "——請改用 _platform_helpers.ABS_FAKE_REPO；確屬合法用法時，改寫為顯式 "
            "PureWindowsPath(…) 或行尾加 `# platform-ok: <理由>` 豁免：\n"
            + "\n".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
