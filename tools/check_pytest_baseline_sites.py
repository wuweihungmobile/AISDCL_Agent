#!/usr/bin/env python3
"""pytest 基線數字「多站點漂移」機械鎖（R13 ARCH-R13-1 落地）。

為何需要（WHY）：AutoClaude full pytest 基線數字（如 3,566 passed / 196 skipped）
長期散落多份文件（根層 CLAUDE.md／ONBOARDING.md／useMacWin.md／AutoClaude/CLAUDE.md
／AutoClaude/README.md），靠人工同步已**三度實際漂移**：
  - DEF-101-045：多站點基線數字各說各話（含誤用已裝 [postgres] 選配 venv 量測的
    3,664/132 虛高值混入部分站點）；
  - ARCH-R12-7：R12 複審再度發現站點間 passed/skipped 不一致；
  - R13 README 漂移實證：AutoClaude/README.md 宣稱 3,567/195（含 badge），與
    ONBOARDING.md 的 3,566/196 並立，無任何機械訊號。
本工具把「數字只准住一個家」升為機械鎖：SSOT＝**ONBOARDING.md §7**（該節同時
載明出廠環境定義、巢狀 session 變因、選配差異），其餘掃描檔出現基線數字即紅，
只能改為指向 SSOT 或以行內豁免標記放行。

🔴 判準邊界（誠實劃界，比照 check_defect_log_crossref.py docstring 風格）：
  命中＝同一行**同時**滿足兩件事：
    1. 含子字串 `passed` 或 `skipped`（不分大小寫；注意 substring 比對，
       `bypassed`/`surpassed` 也會算——寧可誤殺由豁免放行，不可漏放）；
    2. 含「千分位數字」（如 3,566）或「≥4 位連續整數」（如 3567；badge 的
       URL-encoded 形態 `tests-3567%20passed` 亦天然命中；年份 2026 等 4 位數
       與 passed 同行時同樣命中，屬刻意保守）。
  規則：
    - 非 SSOT 掃描檔命中 → 紅（列 檔:行）。
    - SSOT 檔命中數 <1 → 紅（anchor 自檢：防 SSOT 自己被刪成零訊號後，
      本守門對全掃描面「零命中」空轉假綠）。
    - 掃描檔缺席 → 紅（fail-loud：檔案改名/搬移必須同步 _SCAN_FILES，
      防守門範圍靜默失守；_SCAN_FILES 清單本體另由
      tools/tests/test_check_pytest_baseline_sites.py 的真實清單釘選測試鎖住，
      防「刪清單一行」的縮面繞法——ARCH-R13-REV-1/QA-R13-2）。
    - 守門粒度＝**檔案級**：SSOT 判定以整檔為單位，「§7」是約定俗成的節位置——
      數字寫進 ONBOARDING 其他節不會紅、§7 搬空只要他節有 anchor 也不會紅，
      節級歸屬靠人審（ARCH-R13-REV-4/SA-R13-3 誠實劃界）。
  豁免語法：行內含 `baseline-ok: WHY`（建議 HTML 註解 `<!-- baseline-ok: WHY -->`，
  行尾註記亦可——實作抓子字串）。**WHY 必填**：空 WHY 不具豁免力、照列違規
  （比照 encoding-ok 紀律，QA-R13-1/SD-R13-2）。所有「實際生效」的豁免行於每次
  執行時逐行列印 檔:行 與 WHY 供稽核，防豁免標記濫用；豁免為行內式、隨行
  共生共滅，零豁免命中亦屬正常，不設 stale 表。

使用：
  python3 tools/check_pytest_baseline_sites.py   # 於 repo 內任意 cwd；違規印清單並 exit 1
測試：tools/tests/test_check_pytest_baseline_sites.py（fixture 注入，不依賴真實文件現況）
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌/⚠) 防崩潰保護

_REPO_ROOT = Path(__file__).resolve().parents[1]

# 掃描面（相對 repo 根）：pytest 基線數字歷史上實際漂移過的高風險文件。
# 擴大範圍時加入本清單即可，核心判定邏輯（scan）不需改動。
_SCAN_FILES = [
    "CLAUDE.md",
    "ONBOARDING.md",
    "useMacWin.md",
    "AutoClaude/CLAUDE.md",
    "AutoClaude/README.md",
]
# 唯一准許載有基線數字的檔（SSOT＝ONBOARDING.md §7〈常用驗證指令〉附註）。
_SSOT_FILE = "ONBOARDING.md"

_EXEMPT_MARK = "baseline-ok:"

_KEYWORD_RE = re.compile(r"passed|skipped", re.IGNORECASE)
# 千分位（1,234 / 12,345,678）或 ≥4 位連續整數（3567、20260713…）
_NUMBER_RE = re.compile(r"\d{1,3}(?:,\d{3})+|\d{4,}")


def _line_is_claim(line: str) -> bool:
    """行是否構成「pytest 基線數字宣稱」命中（判準見模組 docstring）。"""
    return bool(_KEYWORD_RE.search(line) and _NUMBER_RE.search(line))


def _display(path: Path) -> str:
    """repo 內檔案印相對路徑，repo 外（測試 fixture）退回檔名。"""
    try:
        return path.resolve().relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def _raw_why(line: str) -> str:
    """抽出 `baseline-ok:` 後的 WHY 原文（截去 HTML 註解收尾與前後空白；可為空）。"""
    why = line.split(_EXEMPT_MARK, 1)[1]
    return why.split("-->", 1)[0].strip()


def _exemption_why(line: str) -> str:
    """WHY 顯示文字（空 WHY 以占位字樣呈現——僅供稽核列印；豁免力判定用 _raw_why）。"""
    return _raw_why(line) or "（未填 WHY）"


def audit_exemptions(file_paths: list[Path]) -> list[str]:
    """列出所有「實際生效」的豁免行（命中判準且帶 baseline-ok: 標記），供稽核。

    缺席檔在此靜默略過——缺席本身由 scan() 負責 fail-loud，避免雙重回報。
    """
    records: list[str] = []
    for path in file_paths:
        path = Path(path)
        if not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if _line_is_claim(line) and _EXEMPT_MARK in line:
                records.append(f"{_display(path)}:{lineno} — WHY: {_exemption_why(line)}")
    return records


def scan(file_paths: list[Path], ssot_path: Path) -> list[str]:
    """核心純函式：回傳違規訊息清單（空清單＝通過）。

    規則：非 SSOT 檔命中且無豁免標記 → 違規；SSOT 檔命中數 <1 → 違規（anchor
    自檢）；掃描檔缺席 → 違規（fail-loud）。SSOT 檔的命中不論有無豁免標記皆
    計入 anchor 計數（SSOT 本就准許載數字）。
    """
    problems: list[str] = []
    ssot_resolved = Path(ssot_path).resolve()
    ssot_hits = 0
    ssot_seen_in_list = False

    for path in file_paths:
        path = Path(path)
        if not path.is_file():
            problems.append(
                f"找不到掃描目標：{path}——檔案改名/搬移必須同步 _SCAN_FILES"
                f"（缺席即紅，防守門範圍靜默失守）"
            )
            continue
        is_ssot = path.resolve() == ssot_resolved
        if is_ssot:
            ssot_seen_in_list = True
        for lineno, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not _line_is_claim(line):
                continue
            if is_ssot:
                ssot_hits += 1
                continue
            if _EXEMPT_MARK in line:
                if _raw_why(line):
                    continue  # 行內豁免（稽核列印由 audit_exemptions 負責）
                problems.append(
                    f"{_display(path)}:{lineno}：`{_EXEMPT_MARK}` 標記未填 WHY——空 WHY"
                    f"不具豁免力（比照 encoding-ok 紀律，QA-R13-1/SD-R13-2）"
                    f"｜行文：{line.strip()[:100]}"
                )
                continue
            problems.append(
                f"{_display(path)}:{lineno}：非 SSOT 檔出現 pytest 基線數字宣稱"
                f"（數字唯一出處＝{_SSOT_FILE} §7；改為指向 SSOT，或歷史紀錄性數字"
                f"以行內 `<!-- {_EXEMPT_MARK} WHY -->` 豁免）｜行文：{line.strip()[:100]}"
            )

    if ssot_seen_in_list:
        if ssot_hits < 1:
            problems.append(
                f"SSOT anchor 自檢失敗：{_display(ssot_resolved)} 全檔找不到任何基線數字行"
                f"（命中數 {ssot_hits} <1）——SSOT 被刪成零訊號時本守門會對全面「零命中」"
                f"空轉假綠，故 anchor 消失即紅"
            )
    elif ssot_resolved.is_file():
        # ssot_path 不在 file_paths 內時仍獨立做 anchor 自檢（防呼叫端漏列）
        ssot_hits = sum(
            1 for line in ssot_resolved.read_text(encoding="utf-8-sig").splitlines()
            if _line_is_claim(line)
        )
        if ssot_hits < 1:
            problems.append(
                f"SSOT anchor 自檢失敗：{_display(ssot_resolved)} 全檔找不到任何基線數字行"
                f"（命中數 {ssot_hits} <1）"
            )
    else:
        problems.append(f"找不到 SSOT 檔：{ssot_resolved}（anchor 自檢無從執行，fail-loud）")

    return problems


def main() -> int:
    files = [_REPO_ROOT / rel for rel in _SCAN_FILES]
    ssot = _REPO_ROOT / _SSOT_FILE

    exemptions = audit_exemptions(files)
    for rec in exemptions:
        print(f"⚠️  豁免行稽核（{_EXEMPT_MARK}）：{rec}", file=sys.stderr)

    problems = scan(files, ssot)
    if problems:
        print(f"❌ pytest 基線站點守門失敗（{len(problems)} 筆）：", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            f"修法：基線數字只寫在 {_SSOT_FILE} §7（SSOT），其他文件改為指向該節；"
            f"歷史紀錄性數字可於行內加 `<!-- {_EXEMPT_MARK} WHY -->` 豁免"
            f"（豁免行每次執行都會列印稽核）",
            file=sys.stderr,
        )
        return 1

    exempt_note = f"（另 {len(exemptions)} 筆豁免行，見 warning）" if exemptions else ""
    print(
        f"✅ pytest 基線站點守門通過：{len(_SCAN_FILES)} 份掃描檔中僅 SSOT"
        f"（{_SSOT_FILE}）載有基線數字{exempt_note}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
