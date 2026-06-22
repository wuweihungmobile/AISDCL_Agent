#!/usr/bin/env python3
"""framework_status_snapshot — 框架版本/計數的唯一真相源（SSOT）生成 + 新鮮度機械閘門.

【為何存在】版本（Copy-on-Evolve）會不斷累積，過去把「最新版本號 + 各類資產計數」
硬寫散落在 root/子 CLAUDE.md、INIT.md、RULES_INDEX.md… 任一處變動其餘副本即 stale，
版本越多副本越多 → 必然遺漏（實證：governance 規則由 34/35 漂到 38/39 無人察覺）。

【根本解】單一真相源 + 機械閘門 + version-agnostic：
  * 本腳本掃「磁碟 + 既有權威文件」算出計數，``--write`` 生成唯一檔 ``FRAMEWORK_STATUS.md``；
  * CLAUDE.md 一律 version-agnostic（指「最新演化版＝ci-gate LATEST」不寫死版本號），
    並指向 ``FRAMEWORK_STATUS.md``，不再重複數字；
  * ci-gate ``--check`` 重生並比對，stale 即 CI 紅 → 「人去記得改多處」這件事從流程消失。

版本探測複用 ``rfc_lifecycle_lint``（``discover_frozen_versions`` + ``latest_version``，
對齊 ci-gate.sh ``sort -V | tail -1``），是版本無關 shared infra，不隨 Copy-on-Evolve。

用法：
  python scripts/framework_status_snapshot.py --write   # 重生 SSOT 檔（改框架資產後跑）
  python scripts/framework_status_snapshot.py --check    # 比對是否 stale（ci-gate 硬閘；預設）
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rfc_lifecycle_lint import discover_frozen_versions, latest_version  # noqa: E402

# Windows 主控台 cp950 無法輸出 ✅/中文 → 對齊 sibling 腳本強制 utf-8（CI Linux 已 utf-8）。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

STATUS_FILENAME = "FRAMEWORK_STATUS.md"
_WORKFLOW_TOTAL_RE = re.compile(r"共\s*(\d+)\s*個工作流")


def _baseline_version(versions: set[str]) -> str | None:
    """凍結基線＝最低語意版本（對齊 ci-gate.sh 的 FROZEN_BASELINE=v0.01，但動態取最低不寫死）。"""
    def key(v: str) -> int:
        m = re.search(r"v0\.(\d+)", v)
        return int(m.group(1)) if m else 1 << 30

    return min(versions, key=key) if versions else None


def _count_subdirs(path: str) -> int:
    if not os.path.isdir(path):
        return 0
    return sum(1 for n in os.listdir(path) if os.path.isdir(os.path.join(path, n)))


def _workflows_declared(version_path: str) -> int | None:
    """workflow/README.md 是工作流總數的權威源（23＝1 Gate+8 core+13 scenario+1 ADR 為 curated 數，非檔數）。"""
    readme = os.path.join(version_path, "workflow", "README.md")
    if not os.path.isfile(readme):
        return None
    with open(readme, encoding="utf-8") as f:
        m = _WORKFLOW_TOTAL_RE.search(f.read())
    return int(m.group(1)) if m else None


def count_metrics(version_path: str) -> dict[str, int | None]:
    """單一版本目錄的資產計數。乾淨可數者直接掃磁碟（地面真相）；workflow 取 README 宣稱數。"""
    def g(pattern: str) -> int:
        return len(glob.glob(os.path.join(version_path, pattern)))

    core = g("agent/core/*.yaml")
    specialized = g("agent/specialized/*.yaml")
    tmpl_md = len(glob.glob(os.path.join(version_path, "docs_template/sdd/**/*.md"), recursive=True))
    tmpl_yaml = len(glob.glob(os.path.join(version_path, "docs_template/sdd/**/*.yaml"), recursive=True))
    return {
        "agents_core": core,
        "agents_specialized": specialized,
        "agents_total": core + specialized,
        "agents_runtime": g("agent/specialized/sdd-*.yaml"),
        "scenarios": _count_subdirs(os.path.join(version_path, "scenarios")),
        "workflows": _workflows_declared(version_path),
        "templates_md": tmpl_md,
        "templates_yaml": tmpl_yaml,
        "templates_total": tmpl_md + tmpl_yaml,
        "skills": _count_subdirs(os.path.join(version_path, ".claude/skills")),
        "governance_rules": g("governance/rules/R-*.yaml"),
    }


def _row(label: str, b: int | None, l: int | None) -> str:
    fmt = lambda x: "—（無）" if x is None else str(x)  # noqa: E731
    return f"| {label} | {fmt(b)} | {fmt(l)} |"


def render(repo_root: str) -> str:
    versions = discover_frozen_versions(repo_root)
    baseline = _baseline_version(versions)
    latest = latest_version(versions)
    if baseline is None or latest is None:
        return "（找不到任何 AISDLC_SDD_v0.* 版本目錄）\n"

    mb = count_metrics(os.path.join(repo_root, baseline))
    ml = count_metrics(os.path.join(repo_root, latest))

    lines = [
        "# FRAMEWORK_STATUS — AISDLC-SDD 框架版本/計數唯一真相源（SSOT）",
        "",
        "> **🔴 自動生成，勿手動編輯。** 由 `scripts/framework_status_snapshot.py --write` 產生，",
        "> ci-gate `--check` 機械守新鮮（stale 即 CI 紅）。改動框架資產（agent/規則/模板/skills…）後重生即可。",
        "> CLAUDE.md 等文件一律 **version-agnostic** 並指向本檔，不重複數字——版本累積亦不再多檔漂移。",
        "",
        f"- **凍結基線（ci-gate FROZEN_BASELINE，恆測防回歸）**：`{baseline}`",
        f"- **最新演化版（ci-gate LATEST＝`sort -V | tail -1` 動態取最高，可修改/承載演化）**：`{latest}`",
        "- 各版目錄結構同構；框架改動走 Copy-on-Evolve（複製 LATEST → 新版後於新版修改，不原地改凍結版）。",
        "",
        f"| 指標 | 凍結基線 `{baseline}` | 最新演化版 `{latest}` |",
        "|------|------|------|",
        _row("Agents 總數", mb["agents_total"], ml["agents_total"]),
        _row("— core / specialized",
             f"{mb['agents_core']} / {mb['agents_specialized']}",  # type: ignore[arg-type]
             f"{ml['agents_core']} / {ml['agents_specialized']}"),  # type: ignore[arg-type]
        _row("— 其中 runtime（specialized/sdd-*）", mb["agents_runtime"], ml["agents_runtime"]),
        _row("Scenarios", mb["scenarios"], ml["scenarios"]),
        _row("Workflows（workflow/README.md 宣稱）", mb["workflows"], ml["workflows"]),
        _row("docs_template/sdd 模板（md + yaml）",
             f"{mb['templates_total']}（{mb['templates_md']} md + {mb['templates_yaml']} yaml）",  # type: ignore[arg-type]
             f"{ml['templates_total']}（{ml['templates_md']} md + {ml['templates_yaml']} yaml）"),  # type: ignore[arg-type]
        _row(".claude/skills", mb["skills"], ml["skills"]),
        _row("governance R-*.yaml", mb["governance_rules"], ml["governance_rules"]),
        "",
        "> 數字來源：agents/scenarios/skills/templates/governance＝對應目錄磁碟實掃；",
        "> workflows＝workflow/README.md 宣稱（curated 數＝1 Gate+8 core+13 scenario+1 ADR，非檔數）。",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="重生 SSOT 檔")
    parser.add_argument("--check", action="store_true", help="比對是否 stale（預設；ci-gate 硬閘）")
    parser.add_argument("--repo-root", default=None, help="版本目錄所在（預設＝腳本上兩層＝AISDLC_SDD/）")
    args = parser.parse_args(argv)

    repo_root = args.repo_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    status_path = os.path.join(repo_root, STATUS_FILENAME)
    fresh = render(repo_root)

    if args.write:
        with open(status_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(fresh)
        print(f"✅ 已重生 {STATUS_FILENAME}")
        return 0

    # 預設 / --check
    if not os.path.isfile(status_path):
        print(f"::error:: {STATUS_FILENAME} 不存在——請先跑 `--write` 生成 SSOT", file=sys.stderr)
        return 1
    with open(status_path, encoding="utf-8") as f:
        current = f.read()
    if current != fresh:
        print(
            f"::error:: {STATUS_FILENAME} 已 stale（與磁碟/權威源不符）——"
            "框架資產有變卻未重生。請跑 `python scripts/framework_status_snapshot.py --write` 後 commit。",
            file=sys.stderr,
        )
        return 1
    print(f"✅ {STATUS_FILENAME} 新鮮（與磁碟/權威源一致）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
