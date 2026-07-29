#!/usr/bin/env python3
"""NTFS 敵意檔名 CI 閘 — tools/git-hooks/pre-commit「NTFS 敵意檔名防護閘（A3）」的 CI 對等。

為何需要：A3 閘只活在本機 pre-commit，`git commit --no-verify`、GitHub web 編輯、
未裝 hooks 的 clone 都可繞過；敵意檔名一旦入庫，所有 Windows(NTFS) checkout 直接
炸掉（無法建檔）或靜默大小寫碰撞覆蓋。本腳本供 root-infra-ci 在雲端複核。

範圍差異（by design）：hook 版只掃「本次 commit 新增（A/C）」路徑；本 CI 版掃
`git ls-files` **全量 tracked 路徑**——已入庫的違規也要現形。

檢查邏輯與 hook 版一致（tools/git-hooks/pre-commit `_ntfs_seg_bad` + 大小寫碰撞 + 長度閘）：
  1. 路徑含控制字元（C locale [:cntrl:]＝0x00-0x1F + 0x7F），或任一路徑段含
     Windows 不允許字元 < > : " | ? * \\，或以空白/句點結尾（NTFS 不允許）
  2. 任一段去（第一個點起的）副檔名、再剝除尾隨空白後（不分大小寫）為 Windows 保留裝置名
     CON / PRN / AUX / NUL / COM0~9 / LPT0~9 / CONIN$ / CONOUT$
     （R60 訂正：本行原稱「COM0/LPT0 非 Microsoft 官方保留名，但比照
     sindresorhus/filename-reserved-regex 等業界防禦性實作採保守納入」——實測 git
     for Windows 對兩者的裁決並不相同：`git -c core.protectNTFS=true update-index
     --add --cacheinfo` 對 `LPT0` 回 `error: Invalid path`、對 `COM0` 則 ACCEPT。
     即 LPT0 是**必須**擋（否則 Windows checkout 整棵樹開不出來），只有 COM0 才是
     純保守納入。CONIN$／CONOUT$ 見 `_RESERVED_RE` 上方註解）
  3. 大小寫碰撞：兩 tracked 路徑 lowercase 後相同但原字串不同
     （NTFS 大小寫不敏感 → checkout 時互相覆蓋）
  4. MAX_PATH 保守長度閘（DEF-101-039）：Windows 未開 core.longpaths 時絕對路徑上限
     MAX_PATH=260 UTF-16 單位（含結尾 NUL，可用 259）；預留 clone 前綴 59 字元＋NUL
     （C:\\Users\\<user>\\...\\<repo>\\，259−200＝59）→ repo 相對路徑 >200 字元 fail、
     >180 字元 warn（不影響退出碼）。長度＝Unicode code point 數（len()；BMP 字元＝
     1 UTF-16 單位；hook 版以「刪 UTF-8 連續位元組計數」達成同語意且 locale 無關；
     astral 字元低估 1 單位屬可忽略邊角）。

已知侷限：大小寫折疊用 str.lower()（hook 的 grep -iFx 在 UTF-8 locale 亦
fold 非 ASCII 字母，方向一致）。檔名內嵌換行/控制字元非缺口：git 對含控制字元
路徑恆 C-quote（不受 core.quotepath=false 影響），hook 逐行讀所見之引號化表徵
含 " 與 \\ 觸發第 1 項攔截；本腳本 -z 讀原始路徑由控制字元檢查攔截——兩側皆
封閉（第五輪 SD/QA 雙實證）。`_tracked_files()` 對 `git ls-files` 輸出以
`errors="replace"` 解碼：tracked 路徑若真含非法 UTF-8 位元組序列，違規清單印出的
檔名會混入 U+FFFD 替代字元、人類辨識度打折，但偵測本身不受影響（違規仍會被列出、
exit 1 仍正確觸發，R25 複審確認）。

使用：
  python3 tools/check_ntfs_paths.py   # 於 repo 內任意 cwd；違規印明細並 exit 1
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌/⚠) 防崩潰保護

_REPO_ROOT = Path(__file__).resolve().parents[1]

_FORBIDDEN_CHARS = set('<>:"|?*\\')
# R60（DEF-101-B-refuter-1）：補上 `CONIN$`／`CONOUT$`。權威模型＝git for Windows 的
# `core.protectNTFS`（Windows 預設 true），因為真正炸掉的環節不是 Win32 建檔而是 git
# 簽出。本機實測（Win 11 Pro 26200 / Git Bash 5.2.37，拋棄式 repo、不碰本 repo）：
#   git -c core.protectNTFS=true update-index --add --cacheinfo …
#     REJECT: CONIN$.log / CONOUT$.txt / CONIN$ / conin$.log / CONIN$.tar.gz /
#             CONIN$ .log / CONOUT$   .txt（大小寫、多重副檔名、尾隨空白皆不影響）
#     ACCEPT: CLOCK$.txt / CLOCK$ .txt（故**刻意不納入** CLOCK$，見下方 benign 樣本）
#             CONIN.log / CONIN（少了 `$` 就不是裝置名，故正則要求完整 token）
#   實害：以 protectNTFS=false 把 'CONIN$.log' 提交後，用預設設定 clone →
#         `error: invalid path 'CONIN$.log'` + `fatal: unable to checkout working tree`、
#         rc=128、工作樹**全空**（連無關的 plain.txt 也沒有）。與 R57 已修的
#         「保留名 + 尾隨空白」（DEF-101-478）破壞同級：不是單檔失敗，是整個 clone 不可用。
#   繞過管道＝本檔檔頭已列的三條（--no-verify／GitHub web／未裝 hooks），加上
#   `core.protectNTFS` 在非 Windows 平台預設不啟用 → mac/Linux 側可入庫。
#
# **前導空白刻意不處理**（R60，四處實作統一決策）：「保留名 + **前導**空白」（' CON.txt'／
# '  COM1.log'／' NUL .log'／' CON .txt'）看似 R57 尾隨空白形態的鏡像，實測**不是**缺口：
#   · git（protectNTFS=true）對上述全部形態 ACCEPT——git 只在路徑段**起頭**比對保留名，
#     前導空白使比對失配；含前導形態的 repo clone 實測 rc=0、工作樹有檔、
#     `git status --porcelain` 空、內容讀回正確 payload。
#   · Win32 只吞**尾隨**空白/句點，不吞前導：本機實測 ' CON.txt'／' CON'／'CON.txt'／
#     ' CON .txt' 四者可同時共存於同一目錄（os.listdir 全部列出、各 10 bytes 可讀回）。
#   故在本檔（validator）加擋前導空白＝**純新增偽陽性**（擋下 git 與 Windows 都接受的
#   檔名），零實害可擋。此決策由 tools/tests/test_windows_forbidden_filename_parity.py
#   的 `LEADING_SPACE_RESERVED_SEGMENTS` 樣本電池機械釘住（validator 側必須放行），
#   下輪掃描者若再把它當鏡像缺口回報，請先讀該樣本清單與本段實測。
#
# 🔴 交替分支順序有意義，勿「整理」：四個基本裝置名（CON、PRN、AUX、NUL）必須**相鄰**，
# 新裝置名一律加在清單**尾端**。
# `tools/tests/test_windows_forbidden_filename_parity.py::_RESERVED_LIST_ANCHOR` 這道
# repo-wide 前瞻掃描鎖（抓「新增第 5 份獨立重寫」）要求四者依序出現且間隙 ≤5 字元。
# R60 初版把 CONIN／CONOUT 兩支插在 CON 與 PRN 之間，實測使本檔、pre-commit、logger.py
# 三處**同時**掉出錨①（間隙 17 字元），只靠錨②（禁用字元集合）苟活——註冊表等值斷言
# 照樣全綠，degradation 完全無訊號。改置於清單尾端後三處回歸命中。
# 對正則語意零影響（`^(...)$` 完全錨定，交替順序不改變匹配集合）。
_RESERVED_RE = re.compile(r"^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]|CONIN\$|CONOUT\$)$")

# MAX_PATH 保守長度閘（DEF-101-039）：
# 可用 259（260 含 NUL）− 59（clone 前綴預留）＝ 200 fail；180 warn
_LEN_FAIL = 200
_LEN_WARN = 180


def _length_level(path: str) -> str | None:
    """路徑長度分級：>200 → "fail"、>180 → "warn"、其餘 → None（單位＝code point）。"""
    n = len(path)
    if n > _LEN_FAIL:
        return "fail"
    if n > _LEN_WARN:
        return "warn"
    return None


def _ntfs_seg_bad(path: str) -> str | None:
    """路徑有 NTFS 相容性問題 → 回傳原因字串；乾淨 → None（對齊 hook 版同名函式）。"""
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in path):
        return "含控制字元"
    for seg in path.split("/"):
        bad = _FORBIDDEN_CHARS.intersection(seg)
        if bad:
            return f'路徑段「{seg}」含 Windows 不允許字元（< > : " | ? * \\）'
        if seg.endswith((" ", ".")):
            return f"路徑段「{seg}」以空白或句點結尾（NTFS 不允許）"
        # R57 修正（DEF-101-B1）：base 需先剝除尾隨空白再比對保留名。原本
        # `seg.split(".", 1)[0]` 對 `CON .txt` 得到 `"CON "`，`^(CON|...)$` 不匹配
        # 而放行；L77 的「整段以空白/句點結尾」也不成立（結尾是 t）→ 完全逃逸。
        # Win32 解析裝置名時會忽略基底名後的尾隨空白，故此形態在 Windows 上仍會
        # 撞到裝置名。剝除後 `" .txt"` 這類純空白 base 退化為空字串，
        # `^(CON|...)$` 不匹配空字串，不會誤判。（僅剝空白：base 已在第一個點處
        # 切斷故不含句點；tab 等其他空白屬控制字元，已由 L71 攔下。）
        base = seg.split(".", 1)[0].rstrip(" ")  # 去（第一個點起的）副檔名；CON.txt 一樣是保留名
        if _RESERVED_RE.match(base.upper()):
            return f"路徑段「{seg}」為 Windows 保留裝置名（{base.upper()}）"
    return None


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout
    return [p for p in out.split("\0") if p]


def main() -> int:
    files = _tracked_files()
    violations: list[str] = []
    warnings: list[str] = []

    for f in files:
        reason = _ntfs_seg_bad(f)
        if reason:
            violations.append(f"NTFS 不相容檔名：{f} — {reason}")
        level = _length_level(f)
        if level == "fail":
            violations.append(
                f"路徑過長：{f}（{len(f)} > {_LEN_FAIL} 字元；"
                f"Windows MAX_PATH=260 扣除 clone 前綴預留後超限）"
            )
        elif level == "warn":
            warnings.append(f"路徑偏長：{f}（{len(f)} > {_LEN_WARN} 字元，>{_LEN_FAIL} 將擋下）")

    # 大小寫碰撞：全量 tracked 路徑 lowercase 分組，同組 >1 即互撞
    by_lower: dict[str, list[str]] = {}
    for f in files:
        by_lower.setdefault(f.lower(), []).append(f)
    for group in by_lower.values():
        if len(group) > 1:
            joined = "」「".join(sorted(group))
            violations.append(f"NTFS 大小寫碰撞：「{joined}」僅大小寫不同（checkout 互相覆蓋）")

    for w in warnings:
        print(f"⚠ {w}", file=sys.stderr)

    if violations:
        for v in violations:
            print(f"❌ {v}", file=sys.stderr)
        print(
            f"\n共 {len(violations)} 筆違規 — 修法：改名後重新提交"
            "（對齊 tools/git-hooks/pre-commit A3 閘）",
            file=sys.stderr,
        )
        return 1

    max_len = max((len(f) for f in files), default=0)
    print(
        f"✅ NTFS 檔名檢查通過（{len(files)} 個 tracked 路徑，0 違規；"
        f"最長 {max_len} 字元，warn>{_LEN_WARN}/fail>{_LEN_FAIL}）"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
