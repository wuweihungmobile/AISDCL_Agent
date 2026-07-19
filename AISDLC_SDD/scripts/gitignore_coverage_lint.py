"""Copy-on-Evolve `.gitignore` 覆蓋 lint：偵測「最新演化版缺 runtime 產物排除 block」（DEF-37-001）.

共享 CI infra：位於 ``AISDLC_SDD/scripts/``（versioned 目錄之外，非任一
``AISDLC_SDD_v0.0X`` 凍結本體，免 Copy-on-Evolve；與 DEF-02-001 ``cross_version_guard.py``
／ DEF-03-001 ``ci-gate.sh`` ／ DEF-23-005 ``rfc_lifecycle_lint.py`` 同精神）。

問題（DEF-37-001）：每輪 Copy-on-Evolve 建新版後，跑 ci-gate（pytest + arch_fitness）會在
新版內生成 runtime 取證產物（``<ver>/build/reports/*``、``<ver>/arch-fitness.json``、
``<ver>/chaos-report.json``）。這些「輸出非輸入」須由 ``AISDLC_SDD/.gitignore`` 的 per-version
排除 block 攔下，否則 ``git add -A`` 夾帶 cruft 污染 commit（DEF-11-001 實證 v0.05 曾 would-add
1013 檔含 174 runtime 產物）。但**新版 block 全靠人工手補、無任何自動偵測** —— improving_37
階段四即因 v0.15 block 未補而 would-add 夾帶 11 筆 cruft（手補後才潔淨），屬 DEF-23-005 結案時
明文 deferred 的「新版 gitignore block 缺漏偵測」部分之具體復發（與 DEF-11-002/DEF-23-003 同家族）。

機械強制（read-only 純觀察者，不寫 FSM-STATE、不影響 churn/meta-loop）：偵測**磁碟最新演化版**
（``discover_frozen_versions`` + ``latest_version``，複用 ``rfc_lifecycle_lint``，對齊
``scripts/sdd_version.py`` SSOT 的 LATEST 語意；沿用磁碟掃描之 WHY 見該檔豁免註記），
檢 ``.gitignore`` 是否對該版三類 runtime 產物各有
排除行。**缺即 advisory warn**（P3，不阻擋、不改 ci-gate exit 語意；對齊 DEF-37-001 routed
「缺即 warn」定性），與 ``rfc_lifecycle_lint`` 的 ``missing_status`` advisory 同範式。

判定採子串命中（最低誤報）：對每類產物，token = ``<latest>/<artifact>``；只要 ``.gitignore``
任一**非註解**規則行含該 token 即視為已覆蓋。此設計同時相容兩種既有 idiom：
  - v0.13+ 整樹排除 ``AISDLC_SDD_v0.17/build/reports/``（含 token ``…/build/reports``）；
  - v0.05~v0.12 negate idiom ``AISDLC_SDD_v0.05/build/reports/*``（亦含同 token）。
過濾 ``#`` 開頭註解行：避免註解文字（如 v0.13 block 註解提及 ``build/reports/``）造成偽命中。
"""
from __future__ import annotations

import os
import sys

from rfc_lifecycle_lint import discover_frozen_versions, latest_version

# 每版 Copy-on-Evolve 後須排除的三類 runtime 取證產物（與 .gitignore per-version block 一致）。
RUNTIME_ARTIFACTS = ("build/reports", "arch-fitness.json", "chaos-report.json")


def gitignore_rule_lines(repo_root: str) -> list[str]:
    """讀 ``<repo_root>/.gitignore``，回非空非註解（去 ``#`` 開頭）的規則行。"""
    path = os.path.join(repo_root, ".gitignore")
    if not os.path.isfile(path):
        return []
    lines: list[str] = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(stripped)
    return lines


def missing_artifact_tokens(repo_root: str) -> tuple[str | None, list[str]]:
    """回 (最新演化版, 該版缺排除行的 ``<ver>/<artifact>`` token 清單)。

    無版本目錄 → (None, [])；最新版三類產物皆有排除行 → (latest, [])。
    """
    latest = latest_version(discover_frozen_versions(repo_root))
    if latest is None:
        return None, []
    rules = gitignore_rule_lines(repo_root)
    missing = [
        f"{latest}/{art}"
        for art in RUNTIME_ARTIFACTS
        if not any(f"{latest}/{art}" in line for line in rules)
    ]
    return latest, missing


def main(argv: list[str] | None = None) -> int:
    # Windows 主控台預設 cp950/cp1252 無法輸出 emoji / 中文 — 強制 UTF-8（對齊 rfc_lifecycle_lint）。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - 舊版 / 非 TextIO
            pass
    argv = sys.argv[1:] if argv is None else argv
    repo_root = argv[0] if argv else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    latest, missing = missing_artifact_tokens(repo_root)
    if latest is None:
        print("✅ gitignore 覆蓋 lint：無演化版目錄，略過")
        return 0
    if not missing:
        print(f"✅ gitignore 覆蓋 lint：最新版 {latest} runtime 產物排除 block 齊備")
        return 0
    # advisory：缺 block 僅 warn，不改 exit code（DEF-37-001 P3 不阻擋）。
    print(
        f"::warning:: 最新演化版 {latest} 缺 .gitignore runtime 產物排除行（DEF-37-001）："
        f"{missing}"
    )
    print(
        f"  修復：於 AISDLC_SDD/.gitignore 補 {latest} block —— "
        f"`{latest}/build/reports/` + `{latest}/arch-fitness.json` + `{latest}/chaos-report.json`"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
