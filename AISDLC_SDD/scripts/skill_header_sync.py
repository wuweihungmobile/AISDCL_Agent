"""Skill 版本戳記 SSOT 守新鮮（DEF-CLDREV-007 系統性根除）。

問題
----
每個版本目錄 `AISDLC_SDD_v0.0X/.claude/skills/**/SKILL.md` 末尾都有一行框架版本戳：

    **基於**: AISDLC-SDD v0.01[（後綴）]

`skills/README.md` 與 `SKILL_DEVELOPMENT_PLAN.md` 開頭另有 skill 套件版本戳：

    **版本**: v0.02-SDD

這些戳記**應對齊其所在版本目錄**（v0.19 目錄內應寫 v0.19），但全靠人工在每輪
Copy-on-Evolve（複製 LATEST → 新版）時手改 → 系統性漏改：v0.19 內 42 個 footer
仍寫死 v0.01、README/PLAN 仍停在 v0.02-SDD（DEF-CLDREV-007 實證）。這是「每輪都會
人工漏改」的摩擦，過去無任何機制偵測。

SSOT 決策
---------
skill 版本戳的唯一真相源 = **其所在版本目錄名**。本 lint 只校 ci-gate LATEST
（`sort -V | tail -1`，複用 rfc_lifecycle_lint，對齊既有「最新演化版＝LATEST」原則）；
凍結基線（v0.01）的戳記本就對齊自身目錄（實證 v0.01 footer 即 v0.01），不需也不會被
本 lint 重寫。Copy-on-Evolve 產生新 LATEST 後，舊版戳記仍 stale → `--check` 立即在
CI 紅，強制 `--write` 同步 → 「人去記得改」從流程消失。

只重寫**框架版本戳**兩種精確樣式，不碰：
  - provenance（`source: "builtin (AISDLC-SDD v0.01 Phase A)"`，規則出生版本，應保留）
  - 歷史事實（`SDD 專屬家族 (6個，AISDLC-SDD v0.01 新增)`）
  - 模板佔位版本（`**版本**: {N}.{N}` / `1.0`，輸出文件版本，非框架版本）
  前綴不同 → regex 天然不匹配。

用法
----
  python scripts/skill_header_sync.py            # --check（預設；ci-gate 硬閘，stale 即 exit 1）
  python scripts/skill_header_sync.py --check
  python scripts/skill_header_sync.py --write     # 將 LATEST 內全部框架版本戳同步至 LATEST 版本

合規
----
本腳本在版本目錄**之上**（AISDLC_SDD/ 層），屬「shared infra，不隨 Copy-on-Evolve」
（同 framework_status_snapshot.py / sync_exposed_skills.py / rfc_lifecycle_lint.py）。
`--write` 只改 LATEST（可演化版）內的 .md，不觸碰凍結本體。

注意：`--write` 後須一併重生父層曝光鏡像（`sync_exposed_skills.py --write`），否則
sync_exposed_skills `--check` 會偵測父層漂移而紅（ci-gate 內兩 lint 先後守門）。
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rfc_lifecycle_lint import discover_frozen_versions, latest_version  # noqa: E402

# Windows 主控台 cp950 無法輸出中文 → 對齊 sibling 腳本強制 utf-8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# 框架版本戳兩種精確樣式（version token 在中間，前後綴保留）：
#   A. footer：**基於**: AISDLC-SDD v0.01[（後綴）]
#   B. 套件版本：**版本**: v0.02-SDD[...]
# 兩者 version token 皆 `v<major>.<minor>`。前綴鎖死故 provenance / 歷史 / 模板佔位不誤觸。
_STAMP_RES = (
    re.compile(r"^(?P<pre>\*\*基於\*\*:\s*AISDLC-SDD\s+)v\d+\.\d+(?P<suf>.*)$"),
    re.compile(r"^(?P<pre>\*\*版本\*\*:\s*)v\d+\.\d+(?P<suf>-SDD.*)$"),
)
_VER_TOKEN_RE = re.compile(r"v\d+\.\d+")
_EXCLUDE_DIRS = {"__pycache__"}


def _version_token(latest_dirname: str) -> str | None:
    """由版本目錄名擷取戳記用 token：``AISDLC_SDD_v0.19`` → ``v0.19``。"""
    m = _VER_TOKEN_RE.search(latest_dirname)
    return m.group(0) if m else None


def _md_files(skills_root: str) -> list[str]:
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(skills_root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS]
        for fn in filenames:
            if fn.endswith(".md"):
                out.append(os.path.join(dirpath, fn))
    return out


def _stale_lines(text: str, want_token: str) -> list[tuple[int, str, str]]:
    """回傳 [(行號, 原行, 新行)]：戳記 version token 不等於 want_token 者。"""
    stale: list[tuple[int, str, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        for rx in _STAMP_RES:
            m = rx.match(line)
            if not m:
                continue
            cur = _VER_TOKEN_RE.search(line).group(0)  # type: ignore[union-attr]
            if cur != want_token:
                new = f"{m.group('pre')}{want_token}{m.group('suf')}"
                stale.append((i, line, new))
            break  # 一行至多匹配一種樣式
    return stale


def _resolve(repo_root: str) -> tuple[str, str, str] | None:
    versions = discover_frozen_versions(repo_root)
    latest = latest_version(versions)
    if latest is None:
        return None
    token = _version_token(latest)
    if token is None:
        return None
    skills_root = os.path.join(repo_root, latest, ".claude", "skills")
    return latest, token, skills_root


def check(repo_root: str) -> int:
    resolved = _resolve(repo_root)
    if resolved is None:
        print("[skill-header] 找不到任何 AISDLC_SDD_v0.* 版本目錄", file=sys.stderr)
        return 1
    latest, token, skills_root = resolved
    if not os.path.isdir(skills_root):
        print(f"[skill-header] LATEST({latest}) 無 .claude/skills", file=sys.stderr)
        return 1

    findings: list[tuple[str, int, str]] = []
    for path in _md_files(skills_root):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        rel = os.path.relpath(path, skills_root).replace(os.sep, "/")
        for lineno, _old, _new in _stale_lines(text, token):
            findings.append((rel, lineno, _old.strip()))

    if not findings:
        print(f"[skill-header] OK：LATEST({latest}) 框架版本戳全對齊 {token}")
        return 0

    print(
        f"[skill-header] STALE：LATEST({latest}) 有 {len(findings)} 處框架版本戳 != {token}",
        file=sys.stderr,
    )
    for rel, lineno, old in findings:
        print(f"  - {rel}:{lineno}  {old}", file=sys.stderr)
    print("  修復：python scripts/skill_header_sync.py --write", file=sys.stderr)
    return 1


def write(repo_root: str) -> int:
    resolved = _resolve(repo_root)
    if resolved is None:
        print("[skill-header] 找不到任何 AISDLC_SDD_v0.* 版本目錄", file=sys.stderr)
        return 1
    latest, token, skills_root = resolved
    if not os.path.isdir(skills_root):
        print(f"[skill-header] LATEST({latest}) 無 .claude/skills", file=sys.stderr)
        return 1

    changed = 0
    for path in _md_files(skills_root):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        stale = _stale_lines(text, token)
        if not stale:
            continue
        lines = text.splitlines(keepends=True)
        for lineno, _old, new in stale:
            # 保留原行的換行符（splitlines(keepends) 與 splitlines() 行號對齊）。
            nl = "\n" if lines[lineno - 1].endswith("\n") else ""
            lines[lineno - 1] = new + nl
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("".join(lines))
        changed += 1
    print(f"[skill-header] 已同步 LATEST({latest}) 框架版本戳至 {token}（{changed} 檔變更）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="比對戳記是否 stale（預設；ci-gate 硬閘）")
    parser.add_argument("--write", action="store_true", help="將 LATEST 框架版本戳同步至所在版本")
    parser.add_argument(
        "--repo-root",
        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        help="AISDLC_SDD/ 目錄（含各版本子目錄）",
    )
    args = parser.parse_args(argv)
    if args.write:
        return write(args.repo_root)
    return check(args.repo_root)


if __name__ == "__main__":
    sys.exit(main())
