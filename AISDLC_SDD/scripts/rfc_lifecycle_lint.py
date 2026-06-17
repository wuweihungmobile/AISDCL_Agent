"""RFC 生命週期 lint：偵測「已決 RFC 滯留 active/」的機械強制（DEF-23-005）.

共享 CI infra：位於 ``AISDLC_SDD/scripts/``（versioned 目錄之外，非任一
``AISDLC_SDD_v0.0X`` 凍結本體，免 Copy-on-Evolve；與 DEF-02-001 ``cross_version_guard.py``
／ DEF-03-001 ``ci-gate.sh`` 同精神）。

問題（DEF-23-005）：框架明定 RFC 生命週期「active=待決 / archive=已決」，但**無任何
hook/lint/CI 自動強制**——已決 RFC（_26/_27）曾滯留 active/ 直到人工 zero-trust 盤點才揪出
（實證：v0.12/v0.13 的 ``build/planning/active/`` 至今仍凍結著 _26/_27）。

機械強制（read-only 純觀察者，不寫 FSM-STATE、不影響 churn/meta-loop）：掃描**最新演化版**
的 ``build/planning/active/`` —— 舊凍結版的 active/ 是 Copy-on-Evolve 歷史快照，不可掃（會誤報）。
對每個 RFC 以「最低誤報」雙信號判已決：
  (a) 宣告 ``落地版本：AISDLC_SDD_vX`` 且該版**目錄已存在於磁碟**（已落地＝已決、已凍結）；
  (b) 顯式結案狀態行 ``狀態：已決/結案/archived/closed``。
genuinely-proposed RFC 兩者皆無（其用 前置基線/目標版本），故近零誤報。
"""
from __future__ import annotations

import os
import re
import sys

VERSION_RE = re.compile(r"AISDLC_SDD_v0\.\d+")
# 「落地版本」欄：擷取同行所有版本片段。錨定行首 header 欄位式（``^\s*\**落地版本\**[:：]``）：
# 容忍 markdown 粗體（真實格式 ``**落地版本**：``）與縮排，但**不**誤配 inline-code 範例 / 句中
# 提及（如本 lint 的 RFC 文件本身為說明規則而引用這些 token —— dogfooding 當場揭露之誤報源）。
_LANDED_LINE_RE = re.compile(r"^\s*\**落地版本\**[:：][^\n]*", re.MULTILINE)
# 顯式結案狀態行（同錨定行首，避免 meta 文件誤報）
_CLOSED_STATUS_RE = re.compile(
    r"^\s*\**狀態\**[:：]\s*(已決|結案|archived|closed)", re.MULTILINE | re.IGNORECASE
)


def discover_frozen_versions(repo_root: str) -> set[str]:
    """列舉 repo_root 下所有 ``AISDLC_SDD_v0.0X`` 版本目錄。"""
    found: set[str] = set()
    if os.path.isdir(repo_root):
        for name in os.listdir(repo_root):
            if VERSION_RE.fullmatch(name) and os.path.isdir(os.path.join(repo_root, name)):
                found.add(name)
    return found


def latest_version(versions: set[str]) -> str | None:
    """以語意版本（major, minor 數值）取最高者，對齊 ci-gate.sh 的 ``sort -V | tail -1``。"""
    def key(v: str) -> tuple[int, int]:
        m = re.search(r"v0\.(\d+)", v)
        return (0, int(m.group(1))) if m else (0, -1)

    return max(versions, key=key) if versions else None


def decided_reason(text: str, frozen_versions: set[str]) -> str | None:
    """判定單一 RFC 文字是否已決；回傳違規理由（已決卻在 active/），否則 None。"""
    for line in _LANDED_LINE_RE.findall(text):
        landed = [v for v in VERSION_RE.findall(line) if v in frozen_versions]
        if landed:
            return f"已宣告落地版本 {sorted(set(landed))} 且該版目錄已存在（已決），不應滯留 active/"
    if _CLOSED_STATUS_RE.search(text):
        return "含顯式結案狀態（狀態：已決/結案/archived/closed），不應滯留 active/"
    return None


def find_decided_rfcs_in_active(active_dir: str, frozen_versions: set[str]) -> list[tuple[str, str]]:
    """掃描 active_dir 下所有 ``*.md``，回傳 [(檔名, 違規理由)]（已決卻滯留 active/）。"""
    violations: list[tuple[str, str]] = []
    if not os.path.isdir(active_dir):
        return violations
    for name in sorted(os.listdir(active_dir)):
        if not name.endswith(".md"):  # 略過 .gitkeep 等非 RFC 檔
            continue
        with open(os.path.join(active_dir, name), encoding="utf-8") as f:
            reason = decided_reason(f.read(), frozen_versions)
        if reason:
            violations.append((name, reason))
    return violations


def lint(repo_root: str) -> list[tuple[str, str]]:
    """解析最新演化版，掃其 ``build/planning/active/``，回傳違規清單。"""
    frozen = discover_frozen_versions(repo_root)
    latest = latest_version(frozen)
    if latest is None:
        return []
    active_dir = os.path.join(repo_root, latest, "build", "planning", "active")
    return find_decided_rfcs_in_active(active_dir, frozen)


def main(argv: list[str] | None = None) -> int:
    # Windows 主控台預設 cp950/cp1252 無法輸出 emoji / 中文 — 強制 UTF-8（對齊 arch_fitness）。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - 舊版 / 非 TextIO
            pass
    argv = sys.argv[1:] if argv is None else argv
    repo_root = argv[0] if argv else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    violations = lint(repo_root)
    if not violations:
        print("✅ RFC 生命週期 lint：最新版 active/ 無已決 RFC 滯留")
        return 0
    print("::error:: RFC 生命週期 lint 偵測已決 RFC 滯留 active/（DEF-23-005）：")
    for name, reason in violations:
        print(f"  - {name}：{reason}")
    print("  修復：git mv 該 RFC 至 build/planning/archive/（已決 RFC 應入 archive）")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
