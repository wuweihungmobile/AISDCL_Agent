#!/usr/bin/env python3
"""AISDLC_SDD LATEST 版本解析單一真相源（SSOT）— R10 拍板案(b) 落地（DEF-101-133）。

背景（R10 Architect ARCH-3，scratch 實測重現）：LATEST 解析曾散落 8+ 站點、3 種語言，
語意分歧已被實證——bash 端 `ls -d AISDLC_SDD_v0.[1-9]*` 三重 glob 尾端未錨定，
`AISDLC_SDD_v0.30.bak` / `AISDLC_SDD_v0.30 - Copy`（Windows 檔總管複製品）會被
`sort -V | tail -1` 選中；Python / pwsh 端則錨定 fullmatch。且全部站點掃磁碟而非
git tracked——未 commit 的手動複製目錄即可汙染閘門選版（閘門綠燈實為測錯樹）。

語意定案（本檔為權威，呼叫端不得再自行實作 LATEST 解析）：

  LATEST ≝ git tracked（含 index，`git add` 後即生效）且目錄名完整匹配
           ``^AISDLC_SDD_v\\d+\\.\\d+$`` 的版本目錄中 (major, minor) 數值最大者。

  - tracked 過濾根除「未 commit 複製品汙染」整類問題；
  - 磁碟存在「名字合法但未 tracked」的版本目錄時印 stderr 警告——Copy-on-Evolve
    新版在首次 `git add` 前不會被 LATEST 選中屬**刻意設計**（要納入閘門請先
    `git add`；debug 仍可用 `SDD_FW_VERSION` 覆寫單版）；
  - git 不可用／非 repo（tarball 場景）→ fallback 錨定磁碟掃描並印 stderr 警告。

呼叫端（migration 完成清單）：
  bash  ：scripts/ci-gate.sh、根層 tools/macos_smoke_local.sh
  pwsh  ：根層 .github/workflows/root-infra-ci.yml、windows-compat-ci.yml
  python：根層 tools/check_script_parity.py（subprocess 呼叫）

註：scripts/rfc_lifecycle_lint.py 的 discover_frozen_versions / latest_version 服務
「既存版本集合」語意（RFC 落地版存在性檢查，磁碟存在即算），非 LATEST 閘門選版，
維持既有實作不遷移（見該檔 docstring）。

CLI：python scripts/sdd_version.py [--sdd-root PATH] → stdout 印 LATEST 目錄名；
     找不到任何版本目錄時 stderr 報錯並 exit 1。
測試：scripts/tests/test_sdd_version.py（對抗性 fixture：.bak / " - Copy" /
     未 tracked 合法名 / 檔案非目錄 / v0.9→v0.10 / v1.0 邊界）。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

VERSION_DIR_RE = re.compile(r"^AISDLC_SDD_v(\d+)\.(\d+)$")


def _version_key(name: str) -> tuple[int, int]:
    m = VERSION_DIR_RE.fullmatch(name)
    if not m:
        raise ValueError(f"非合法版本目錄名：{name!r}")
    return (int(m.group(1)), int(m.group(2)))


def tracked_version_dirs(sdd_root: Path) -> set[str] | None:
    """git tracked（含 index）的版本目錄名集合；git 不可用／非 repo 回傳 None。

    以 ``git ls-files -- 'AISDLC_SDD_v*'`` 列 tracked 檔，取路徑第一段並以
    fullmatch 過濾——路徑不含 ``/`` 者為 sdd_root 直下的「檔案」而非目錄
    （例如誤放的 ``AISDLC_SDD_v9.99`` 純檔案），明確排除。
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(sdd_root), "ls-files", "--", "AISDLC_SDD_v*"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    names: set[str] = set()
    for line in proc.stdout.splitlines():
        if "/" not in line:
            continue  # sdd_root 直下的純檔案，非版本目錄
        top = line.split("/", 1)[0]
        if VERSION_DIR_RE.fullmatch(top):
            names.add(top)
    return names


def disk_version_dirs(sdd_root: Path) -> set[str]:
    """磁碟上（不論 tracked 與否）錨定匹配的版本目錄名集合。"""
    if not sdd_root.is_dir():
        return set()
    return {
        child.name
        for child in sdd_root.iterdir()
        if child.is_dir() and VERSION_DIR_RE.fullmatch(child.name)
    }


def latest_version_name(sdd_root: Path, *, warn=None) -> str | None:
    """回傳 LATEST 版本目錄名（語意見模組 docstring）；找不到回傳 None。"""
    if warn is None:
        warn = lambda msg: print(msg, file=sys.stderr)  # noqa: E731
    disk = disk_version_dirs(sdd_root)
    tracked = tracked_version_dirs(sdd_root)
    if tracked is None:
        warn(
            "[sdd_version] ⚠ git 不可用或非 repo → fallback 磁碟掃描"
            "（無 tracked 過濾，請留意未 commit 複製目錄）"
        )
        pool = disk
    else:
        pool = tracked
        untracked = sorted(disk - tracked)
        if untracked:
            warn(
                f"[sdd_version] ⚠ 偵測到未 tracked 版本目錄 {untracked} — "
                f"不納入 LATEST（Copy-on-Evolve 新版請先 git add 才進閘門）"
            )
    if not pool:
        return None
    return max(pool, key=_version_key)


def main(argv: list[str] | None = None) -> int:
    # Windows 主控台預設 cp950/cp1252 無法輸出 emoji / 中文 — 強制 UTF-8（對齊
    # gitignore_coverage_lint / rfc_lifecycle_lint；否則錯誤分支的 ❌ 會反以
    # UnicodeEncodeError 掩蓋真錯誤）。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - 舊版 / 非 TextIO
            pass
    parser = argparse.ArgumentParser(description="AISDLC_SDD LATEST 版本解析 SSOT")
    parser.add_argument(
        "--sdd-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="AISDLC_SDD 目錄（預設：本檔所在 scripts/ 的上層）",
    )
    args = parser.parse_args(argv)
    latest = latest_version_name(Path(args.sdd_root))
    if latest is None:
        print(f"[sdd_version] ❌ 於 {args.sdd_root} 找不到任何版本目錄", file=sys.stderr)
        return 1
    print(latest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
