#!/usr/bin/env python3
"""測試樹原始碼「Windows 磁碟機假路徑」自我檢測（R11 A1c；R11 複審 SD-2/ARCH-2 補強；
R12 ARCH-R12-4 掃描面擴大至四個測試樹）.

WHY：R11 真 Mac 首跑實證——測試裡把 D:/repo 這種磁碟機假路徑字串塞給 Path()，
它只在 Windows 是絕對路徑；POSIX 上 `repo_root / 絕對路徑` 的 pathlib join 會退化
成串接（D:/repo/D:/repo/…）、resolve 後恆不相等 → Windows 全綠、Mac/Linux 假紅
（test_check_hooks_liveness.py TestIsHooksEffective 兩案例實際紅過）。修法是改用
_platform_helpers.ABS_FAKE_REPO 平台中立常數；本測試機械掃描測試樹原始碼，
防未來有人複製舊 pattern 再踩一次。

R11 四方複審補強（SD-2/ARCH-2）：原 regex 只抓「Path( 後緊接引號＋大寫磁碟機
＋正斜線」單一形態——漏抓 r/f 等字串前綴變體、反斜線形態 X:\\、小寫磁碟機，
以及**裸字串**磁碟機路徑常數（原病灶正是不經 Path( 直呼的裸字串）。改為抓
「任意字串字面值以磁碟機路徑開頭」（引號後緊接單一字母＋冒號＋斜線或反斜線；
匹配起點是引號本身，故 r/f/b 前綴一律涵蓋）。並：
  (a) 每行先剝 `#` 註解尾再掃（註解舉例不誤報；heuristic 不解析字串內的 #，
      字串內含 # 且其後才出現磁碟機路徑的極端形態會漏掃，屬可接受取捨）；
  (b) 豁免顯式平台語意 PureWindowsPath(/PurePosixPath(（該行本來就是在寫
      特定平台路徑）與逐檔豁免清單 _ALLOWED（附 WHY）；
  (c) 支援行尾 `# platform-ok: <理由>` 豁免標記（合法命中須逐行附理由明示處置）。

R12 掃描面（ARCH-R12-4；DEF-101-149 病灶類別在其他測試樹此前零守門）：
  1. tools/tests/（本目錄，非遞迴——維持 R11 現狀）
  2. AISDLC_SDD/scripts/tests/（非遞迴）
  3. AutoClaude/tests/（**遞迴**，含 plugins/core/contract/… 子樹）
  4. LATEST 版 tools/fsm_runtime/tests/（遞迴；LATEST 以 scripts/sdd_version.py
     SSOT subprocess 解析——手法對齊 check_script_parity；解析失敗 fail-loud，
     不得靜默縮小掃描邊界。凍結版 v0.01~v0.2X 依鐵律不掃、也不可修）
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]
# 任意字串字面值以「單一字母磁碟機 + 冒號 + / 或 \」開頭即命中；
# 匹配起點為引號本身，r/f/b 等前綴與 Path( 包裹與否皆無關（裸字串同樣命中）。
_DRIVE_STR_RE = re.compile(r"""["'][A-Za-z]:[/\\]""")
# 逐檔豁免（repo 相對路徑 → WHY）。豁免檔案消失時 fail-loud（防清單腐化）。
_ALLOWED: dict[str, str] = {
    "tools/tests/_platform_helpers.py": (
        "平台中立常數的單一定義點（win32 分支本來就該寫磁碟機路徑）"
    ),
    "AutoClaude/tests/test_perception.py": (
        "Windows 專屬 perception/cmd-shim 的 mock 回傳值與純字串斷言，"
        "無 pathlib join 語意（R12 親讀 20 筆命中逐一核可，非 DEF-101-149 病灶）"
    ),
}
_OK_MARKER = "platform-ok:"
_EXPLICIT_PLATFORM = ("PureWindowsPath(", "PurePosixPath(")


def _latest_fsm_tests_dir() -> Path:
    """LATEST 版 fsm_runtime/tests（sdd_version.py SSOT；解析失敗即 AssertionError）。"""
    sdd_root = _REPO_ROOT / "AISDLC_SDD"
    resolver = sdd_root / "scripts" / "sdd_version.py"
    proc = subprocess.run(
        [sys.executable, str(resolver), "--sdd-root", str(sdd_root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    name = proc.stdout.strip()
    if proc.returncode != 0 or not name:
        raise AssertionError(
            f"LATEST 解析失敗（sdd_version.py rc={proc.returncode}；stderr="
            f"{proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
        )
    return sdd_root / name / "tools" / "fsm_runtime" / "tests"


def _scan_roots() -> list[tuple[Path, bool, int]]:
    """（掃描根, 是否遞迴, 該樹檔數下限）清單；根缺席或低於下限由測試 fail-loud。

    per-tree 下限（R12 SD 一審 SD-3）：全域總數下限對「單樹靜默縮面」不敏感
    （如 LATEST 樹 rglob 被改 glob，總數 377→303 仍過全域 200）；逐樹釘選使任一
    樹縮面必紅。下限＝2026-07-18 實測實掃數（13/19/271/74；AutoClaude 樹總檔 272
    扣除 _ALLOWED 豁免 1 檔——斷言對象為排除豁免後的實掃數）打八折取整，隨基線上修。"""
    return [
        (_TESTS_DIR, False, 10),
        (_REPO_ROOT / "AISDLC_SDD" / "scripts" / "tests", False, 15),
        (_REPO_ROOT / "AutoClaude" / "tests", True, 217),
        (_latest_fsm_tests_dir(), True, 59),
    ]


def _scan_file(py: Path) -> list[str]:
    offenders: list[str] = []
    rel = py.relative_to(_REPO_ROOT).as_posix()
    for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), start=1):
        if _OK_MARKER in line:  # (c) 行尾豁免標記（附理由）
            continue
        code = line.split("#", 1)[0]  # (a) 剝註解尾（heuristic，見 docstring）
        if any(tok in code for tok in _EXPLICIT_PLATFORM):  # (b) 顯式平台語意
            continue
        if _DRIVE_STR_RE.search(code):
            offenders.append(f"{rel}:{lineno}: {line.strip()}")
    return offenders


class TestPlatformNeutralPaths(unittest.TestCase):
    def test_no_windows_drive_fake_paths(self) -> None:
        offenders: list[str] = []
        for root, recursive, floor in _scan_roots():
            self.assertTrue(root.is_dir(), f"掃描根缺席：{root}（邊界不得靜默縮小）")
            files = root.rglob("*.py") if recursive else root.glob("*.py")
            tree_scanned = 0
            for py in sorted(files):
                if py.relative_to(_REPO_ROOT).as_posix() in _ALLOWED:
                    continue
                offenders.extend(_scan_file(py))
                tree_scanned += 1
            # per-tree 下限釘選（SD-3）：單樹縮面必紅，不被他樹總量掩蓋
            self.assertGreaterEqual(
                tree_scanned, floor,
                f"{root} 掃描檔數 {tree_scanned} < 下限 {floor}——該樹掃描面疑似縮小",
            )
        self.assertEqual(
            offenders,
            [],
            "發現 Windows 磁碟機假路徑字面值（POSIX 上非絕對路徑 → join 語意分歧假紅）"
            "——請改用 tools/tests/_platform_helpers.ABS_FAKE_REPO；確屬合法用法時，"
            "改寫為顯式 PureWindowsPath(…) 或行尾加 `# platform-ok: <理由>` 豁免：\n"
            + "\n".join(offenders),
        )

    def test_allowed_exemptions_not_stale(self) -> None:
        """豁免清單防腐化：登記的檔案消失即紅（比照 parity 清單 stale 檢查）。"""
        for rel, why in _ALLOWED.items():
            self.assertTrue(
                (_REPO_ROOT / rel).is_file(),
                f"_ALLOWED 豁免 stale：{rel} 已不存在（WHY={why}）——請自清單移除",
            )


if __name__ == "__main__":
    unittest.main()
