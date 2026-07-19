"""對外曝光 skills SSOT 守新鮮（AutoSDD_improving — 方案 C 步驟 ②③）。

問題
----
`AISDLC_SDD/.claude/skills`（版本無關的「對外曝光」skill 集，CC 在 AISDLC_SDD/ 下
工作時以 `AISDLC_SDD:<skill>` 曝光）是早期凍結的舊快照，與最新演化版（ci-gate
LATEST）已漂移：個別 skill 語意落後（如 sdd-gate 缺 retry_count/pattern_detection/
ESCALATION 段）、且缺數個後期新增的 runtime skill。它**不受任何機制治理**——
framework_status_snapshot.py 只計數各「版本目錄」內的 skills，從不檢查這份父層副本。

SSOT 決策
---------
對外曝光 skills 的唯一真相源 = **ci-gate LATEST 版**（複用 rfc_lifecycle_lint 磁碟掃描，
對齊 `scripts/sdd_version.py` SSOT 的 LATEST 語意；沿用磁碟掃描之 WHY——copy_on_evolve.sh
建版後新版尚未 git add 即呼叫本腳本 --write——見該檔豁免註記）。父層副本是 LATEST 的
**機械鏡像**，不手動維護（手動維護正是它今天漂移的原因）。

用法
----
  python scripts/sync_exposed_skills.py            # --check（預設；ci-gate 硬閘，stale 即 exit 1）
  python scripts/sync_exposed_skills.py --check
  python scripts/sync_exposed_skills.py --write     # 由 LATEST 重生父層鏡像（修復漂移）

合規
----
本腳本與父層 `.claude/skills` 皆在版本目錄**之上**（AISDLC_SDD/ 層），不在任何凍結
`v0.0X` 本體內 → 不違反 Copy-on-Evolve；屬「shared infra，不隨 Copy-on-Evolve」
（同 framework_status_snapshot.py / rfc_lifecycle_lint.py）。
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rfc_lifecycle_lint import discover_frozen_versions, latest_version  # noqa: E402

# Windows 主控台 cp950 無法輸出中文 → 對齊 sibling 腳本強制 utf-8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

_EXCLUDE_DIRS = {"__pycache__"}
_EXCLUDE_SUFFIX = (".pyc",)


def _skill_files(root: str) -> dict[str, bytes]:
    """收集 root 下所有檔案：relpath（正規化為 /）→ bytes。排除 __pycache__/.pyc。"""
    out: dict[str, bytes] = {}
    if not os.path.isdir(root):
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS]
        for fn in filenames:
            if fn.endswith(_EXCLUDE_SUFFIX):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            with open(full, "rb") as f:
                out[rel] = f.read()
    return out


def _resolve_paths(repo_root: str) -> tuple[str, str, str] | None:
    versions = discover_frozen_versions(repo_root)
    latest = latest_version(versions)
    if latest is None:
        return None
    latest_skills = os.path.join(repo_root, latest, ".claude", "skills")
    parent_skills = os.path.join(repo_root, ".claude", "skills")
    return latest, latest_skills, parent_skills


def check(repo_root: str) -> int:
    resolved = _resolve_paths(repo_root)
    if resolved is None:
        print("[skills-ssot] 找不到任何 AISDLC_SDD_v0.* 版本目錄", file=sys.stderr)
        return 1
    latest, latest_skills, parent_skills = resolved
    want = _skill_files(latest_skills)
    have = _skill_files(parent_skills)
    if not want:
        print(f"[skills-ssot] LATEST({latest}) 無 .claude/skills 內容，無法比對", file=sys.stderr)
        return 1

    missing = sorted(set(want) - set(have))      # 父層缺（LATEST 有）
    extra = sorted(set(have) - set(want))        # 父層多（LATEST 無）
    drift = sorted(k for k in (set(want) & set(have)) if want[k] != have[k])

    if not missing and not extra and not drift:
        print(f"[skills-ssot] OK：父層 .claude/skills == LATEST({latest})（{len(want)} 檔一致）")
        return 0

    print(f"[skills-ssot] STALE：父層 .claude/skills 與 LATEST({latest}) 不一致", file=sys.stderr)
    for k in missing:
        print(f"  - 缺少（LATEST 有）：{k}", file=sys.stderr)
    for k in extra:
        print(f"  - 多餘（LATEST 無）：{k}", file=sys.stderr)
    for k in drift:
        print(f"  - 內容漂移：{k}", file=sys.stderr)
    print("  修復：python scripts/sync_exposed_skills.py --write", file=sys.stderr)
    return 1


def write(repo_root: str) -> int:
    resolved = _resolve_paths(repo_root)
    if resolved is None:
        print("[skills-ssot] 找不到任何 AISDLC_SDD_v0.* 版本目錄", file=sys.stderr)
        return 1
    latest, latest_skills, parent_skills = resolved
    if not os.path.isdir(latest_skills):
        print(f"[skills-ssot] LATEST({latest}) 無 .claude/skills，無法鏡像", file=sys.stderr)
        return 1
    if os.path.isdir(parent_skills):
        shutil.rmtree(parent_skills)
    shutil.copytree(
        latest_skills,
        parent_skills,
        ignore=shutil.ignore_patterns(*_EXCLUDE_DIRS, "*.pyc"),
    )
    n = len(_skill_files(parent_skills))
    print(f"[skills-ssot] 已由 LATEST({latest}) 重生父層鏡像（{n} 檔）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="比對父層是否 stale（預設；ci-gate 硬閘）")
    parser.add_argument("--write", action="store_true", help="由 LATEST 重生父層鏡像")
    parser.add_argument(
        "--repo-root",
        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        help="AISDLC_SDD/ 目錄（含各版本子目錄與 .claude/skills 父層副本）",
    )
    args = parser.parse_args(argv)
    if args.write:
        return write(args.repo_root)
    return check(args.repo_root)


if __name__ == "__main__":
    sys.exit(main())
