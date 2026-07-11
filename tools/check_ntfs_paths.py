#!/usr/bin/env python3
"""NTFS 敵意檔名 CI 閘 — tools/git-hooks/pre-commit「NTFS 敵意檔名防護閘（A3）」的 CI 對等。

為何需要：A3 閘只活在本機 pre-commit，`git commit --no-verify`、GitHub web 編輯、
未裝 hooks 的 clone 都可繞過；敵意檔名一旦入庫，所有 Windows(NTFS) checkout 直接
炸掉（無法建檔）或靜默大小寫碰撞覆蓋。本腳本供 root-infra-ci 在雲端複核。

範圍差異（by design）：hook 版只掃「本次 commit 新增（A/C）」路徑；本 CI 版掃
`git ls-files` **全量 tracked 路徑**——已入庫的違規也要現形。

檢查邏輯與 hook 版一致（tools/git-hooks/pre-commit `_ntfs_seg_bad` + 大小寫碰撞）：
  1. 路徑含控制字元（C locale [:cntrl:]＝0x00-0x1F + 0x7F），或任一路徑段含
     Windows 不允許字元 < > : " | ? * \\，或以空白/句點結尾（NTFS 不允許）
  2. 任一段去（第一個點起的）副檔名後（不分大小寫）為 Windows 保留裝置名
     CON / PRN / AUX / NUL / COM1~9 / LPT1~9
  3. 大小寫碰撞：兩 tracked 路徑 lowercase 後相同但原字串不同
     （NTFS 大小寫不敏感 → checkout 時互相覆蓋）

已知侷限（與 hook 版對齊，不另增檢查）：hook 版無路徑長度（MAX_PATH=260）檢查，
本腳本維持一致；大小寫折疊用 str.lower()（hook 的 grep -iFx 在 UTF-8 locale 亦
fold 非 ASCII 字母，方向一致）。

使用：
  python3 tools/check_ntfs_paths.py   # 於 repo 內任意 cwd；違規印明細並 exit 1
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

_FORBIDDEN_CHARS = set('<>:"|?*\\')
_RESERVED_RE = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$")


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
        base = seg.split(".", 1)[0]  # 去（第一個點起的）副檔名；CON.txt 一樣是保留名
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
        check=True,
    ).stdout
    return [p for p in out.split("\0") if p]


def main() -> int:
    files = _tracked_files()
    violations: list[str] = []

    for f in files:
        reason = _ntfs_seg_bad(f)
        if reason:
            violations.append(f"NTFS 不相容檔名：{f} — {reason}")

    # 大小寫碰撞：全量 tracked 路徑 lowercase 分組，同組 >1 即互撞
    by_lower: dict[str, list[str]] = {}
    for f in files:
        by_lower.setdefault(f.lower(), []).append(f)
    for group in by_lower.values():
        if len(group) > 1:
            joined = "」「".join(sorted(group))
            violations.append(f"NTFS 大小寫碰撞：「{joined}」僅大小寫不同（checkout 互相覆蓋）")

    if violations:
        for v in violations:
            print(f"❌ {v}", file=sys.stderr)
        print(
            f"\n共 {len(violations)} 筆違規 — 修法：改名後重新提交"
            "（對齊 tools/git-hooks/pre-commit A3 閘）",
            file=sys.stderr,
        )
        return 1

    print(f"✅ NTFS 檔名檢查通過（{len(files)} 個 tracked 路徑，0 違規）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
