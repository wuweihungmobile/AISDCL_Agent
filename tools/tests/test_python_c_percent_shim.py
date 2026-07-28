#!/usr/bin/env python3
"""`.ps1` 內 `python -c` 一行式禁用 %-formatting 的機械守門（DEF-101-503，2026-07-27）。

WHY（真實事故，非假想風險）：`AutoClaude/tools/run_local_nightly.ps1` 的
sdd-fsm-chaos stage 用一行式印 bounded 摘要取證：

    & $script:PyExe -c "... print('bounded=%s/%s' % (d['a'], d['b'])) ..."

該檔 `$script:PyExe` 解析到的 `python`，在裝了 pyenv-win 的機器上是 **python.bat**
shim（不是 python.exe）。batch 會先對命令列做百分號展開，把 `%s` 這種未定義的
`%x` 序列直接吃掉，送到 Python 手上時 `'...%s...' % (...)` 已變成 `'...'(...)`
＝字串後面直接接括號 → `SyntaxWarning: 'str' object is not callable` +
`TypeError`，rc=1。

危害不是「少印一行摘要」而是**訊號污染**：chaos 測試本身 34 支全過
（pytest_rc=0 sweep_rc=0），卻因 parse_rc=1 讓整個 stage 判 fail、nightly
exit=1；隔天早上 `tools/dev_start.py` 的心跳哨兵便報「上一輪 nightly 有失敗」，
把使用者導去追一個不存在的迴歸，真失敗反而被淹沒在常亮紅燈裡。

判準：`.ps1` 全檔掃描（**不排除 AISDLC_SDD 凍結版本**——R44/R45/R46 三輪連續
事故的結構性根因正是「新規則預設排除凍結版本」，故本檔一視同仁；落地當下實測
全 repo 零命中，不需任何豁免）。命中條件＝同一行內先出現 python 直譯器 token，
其後有 `-c "…"` 且雙引號內容含 `%`。

不掃 `.sh`／`.yml` 是刻意的邊界（非疏漏）：本 bug 的成因是 **batch shim 的百分號
展開**，只在 Windows 載具成立。`.github/workflows/aisdlc-sdd-fsm-chaos-nightly.yml`
就有一處 `python -c "...strftime('%Y%m%d')..."` 跑在 ubuntu `shell: bash` 的真
python.exe 上，完全正確——把它一起掃會製造假紅。

修法：一律改 `.format()` 或 f-string（不含 `%`），真 python.exe 與 .bat shim 皆正確。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

# 掃描檔數下限釘選（比照 tools/run_root_unittests.py MIN_TESTS 慣例）：低於此數
# ＝glob 壞掉/目錄搬家導致掃描器變空殼，本檔會靜默恆綠。2026-07-27 實測 137 支
# （已排除 venv）。刻意大量刪 .ps1 時同步下修。
_MIN_PS1_FILES = 120

# 邊界（R59 SD-R59-03 實測補記，本檔此前缺三段式宣稱，與同輪另兩道鎖不對稱）：
#   【已實測涵蓋】`-c "…"` 雙引號形態（PowerShell 內最常見的寫法）。
#   【已實測不涵蓋】`-c '…'` **單引號**形態——PowerShell 單引號字串同樣把 `%` 原樣交給
#     batch shim，bug 一模一樣，但本正則只認雙引號故回空。實測全 repo 137 支 `.ps1`
#     目前**零**此形態，故無活體漏測；一旦有人改寫成單引號即成盲區。
#   【未窮舉】本清單非窮舉，不主張殘餘風險僅此一項。
_MINUS_C = re.compile(r'-c\s+"(?P<body>[^"]*)"')
# 直譯器 token：裸 python / python3.11 / PowerShell 變數（$script:PyExe、$PyExe…）
_PY_TOKEN = re.compile(r'(?i)\bpython[0-9.]*\b|PyExe|PY_EXE|PYTHON_EXE')


def _iter_ps1_files() -> list[Path]:
    return sorted(
        p for p in _ROOT.rglob("*.ps1")
        if ".venv" not in p.parts and ".git" not in p.parts
    )


def find_percent_hits(text: str) -> list[tuple[int, str]]:
    """回傳 [(行號, 該行), …]；抽成模組級函式是為了讓偵測器自身可被測試。"""
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in _MINUS_C.finditer(line):
            if "%" not in m.group("body"):
                continue
            if _PY_TOKEN.search(line[: m.start()]):
                hits.append((lineno, line.strip()))
                break
    return hits


class TestDetectorItself(unittest.TestCase):
    """紀律「驗證鏡子自身要被驗證」：偵測器不可因 regex 寫壞而變成恆綠空殼。"""

    def test_detects_the_real_regression_line(self):
        bad = """& $script:PyExe -c "import json; print('a=%s' % (1,))" """
        self.assertEqual(len(find_percent_hits(bad)), 1)

    def test_detects_bare_python_invocation(self):
        self.assertEqual(len(find_percent_hits('python -c "print(\'%d\' % 1)"')), 1)

    def test_format_version_is_not_flagged(self):
        ok = """& $script:PyExe -c "print('a={}'.format(1))" """
        self.assertEqual(find_percent_hits(ok), [])

    def test_percent_outside_python_c_is_not_flagged(self):
        """PowerShell 自己的 `%`（ForEach-Object 別名）與非 -c 字串不該誤報。"""
        self.assertEqual(find_percent_hits('Get-ChildItem | % { $_.Name }'), [])
        self.assertEqual(find_percent_hits('Write-Host "進度 50%"'), [])


class TestNoPercentFormattingInPs1(unittest.TestCase):
    def test_scan_coverage_floor(self):
        files = _iter_ps1_files()
        self.assertGreaterEqual(
            len(files), _MIN_PS1_FILES,
            f"只掃到 {len(files)} 支 .ps1（下限 {_MIN_PS1_FILES}）——掃描器可能已變空殼，"
            f"請確認 glob 與目錄結構，或刻意刪檔後同步下修 _MIN_PS1_FILES")

    def test_no_percent_formatting_in_python_c_oneliners(self):
        offenders: list[str] = []
        for path in _iter_ps1_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in find_percent_hits(text):
                rel = path.relative_to(_ROOT).as_posix()
                offenders.append(f"{rel}:{lineno}: {line[:120]}")
        self.assertEqual(
            offenders, [],
            "以下 `python -c` 一行式含 %-formatting：pyenv-win 的 python.bat shim 會吃掉 "
            "`%`，Python 收到的是壞掉的源碼（TypeError: 'str' object is not callable）。"
            "改用 .format() 或 f-string：\n  " + "\n  ".join(offenders))


if __name__ == "__main__":
    unittest.main()
