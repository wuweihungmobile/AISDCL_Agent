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
  (b) 顯式結案狀態行 ``狀態：已決/decided/結案/archived/closed``。
genuinely-proposed RFC 兩者皆無（其用 前置基線/目標版本），故近零誤報。

**RFC 狀態欄標準慣例（improving_33 W-33-2 / DEF-30-001，本 lint 即 SSOT）**：
每個 RFC 應於開頭以行首欄位宣告 ``**狀態**：proposed``（提案中／待決）或
``**狀態**：decided``（已決／已落地，亦可用 ``已決``）。DEF-30-001 揭露：現有 RFC 狀態標記
不統一（``已歸檔``／``EXECUTED``／無），致雙信號 lint 無法覆蓋所有已決 RFC。標準化後：
  - active/ RFC **缺**標準 ``狀態`` 欄 → advisory **warn**（不阻擋；強制慣例被遵循）；
  - 已決 RFC 滯留 active/ 必帶 ``狀態：decided`` → 被既有 decided 偵測攔下（覆蓋缺口閉合）。
"""
from __future__ import annotations

import os
import re
import sys

# DEF-43-003：major 不再硬寫死 0（原 ``v0\.`` 致一旦升 v1.00 整個版本解析家族
# 集體無視新 major 版、LATEST 退回 v0.x）。放寬為 ``v<major>.<minor>`` 雙數值。
VERSION_RE = re.compile(r"AISDLC_SDD_v\d+\.\d+")
# 「落地版本」欄：擷取同行所有版本片段。錨定行首 header 欄位式（``^\s*\**落地版本\**[:：]``）：
# 容忍 markdown 粗體（真實格式 ``**落地版本**：``）與縮排，但**不**誤配 inline-code 範例 / 句中
# 提及（如本 lint 的 RFC 文件本身為說明規則而引用這些 token —— dogfooding 當場揭露之誤報源）。
_LANDED_LINE_RE = re.compile(r"^\s*\**落地版本\**[:：][^\n]*", re.MULTILINE)
# 顯式結案狀態行（同錨定行首，避免 meta 文件誤報）。W-33-2：加標準英文 token ``decided``
# （補 ``已決``），使標準 ``**狀態**：decided`` 被識別為已決（DEF-30-001 標準化）。
_CLOSED_STATUS_RE = re.compile(
    r"^\s*\**狀態\**[:：]\s*(已決|decided|結案|archived|closed)",
    re.MULTILINE | re.IGNORECASE,
)
# W-33-2（DEF-30-001）：任一行首 ``**狀態**：`` 欄位是否存在（標準慣例強制；缺即 advisory warn）。
_STATUS_FIELD_RE = re.compile(r"^\s*\**狀態\**[:：]", re.MULTILINE)


def discover_frozen_versions(repo_root: str) -> set[str]:
    """列舉 repo_root 下所有 ``AISDLC_SDD_v0.0X`` 版本目錄。"""
    found: set[str] = set()
    if os.path.isdir(repo_root):
        for name in os.listdir(repo_root):
            if VERSION_RE.fullmatch(name) and os.path.isdir(os.path.join(repo_root, name)):
                found.add(name)
    return found


def latest_version(versions: set[str]) -> str | None:
    """以語意版本（major, minor 數值）取最高者（磁碟掃描語意；排序與 ``scripts/sdd_version.py``
    SSOT 一致，沿用磁碟掃描之 WHY 見該檔豁免註記）。"""
    def key(v: str) -> tuple[int, int]:
        # DEF-43-003：擷取真正的 (major, minor)，不再硬寫死 major=0（否則 v1.00 被當 minor=-1）。
        m = re.search(r"v(\d+)\.(\d+)", v)
        return (int(m.group(1)), int(m.group(2))) if m else (-1, -1)

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


def find_active_rfcs_missing_status(active_dir: str) -> list[str]:
    """掃描 active_dir 下所有 ``*.md``，回傳缺標準行首 ``**狀態**：`` 欄的檔名清單.

    W-33-2（DEF-30-001）：advisory — 缺欄不阻擋（exit 不受影響），僅 warn 促慣例採納。
    """
    missing: list[str] = []
    if not os.path.isdir(active_dir):
        return missing
    for name in sorted(os.listdir(active_dir)):
        if not name.endswith(".md"):  # 略過 .gitkeep 等非 RFC 檔
            continue
        with open(os.path.join(active_dir, name), encoding="utf-8") as f:
            if not _STATUS_FIELD_RE.search(f.read()):
                missing.append(name)
    return missing


def _latest_active_dir(repo_root: str) -> str | None:
    """回傳最新演化版的 ``build/planning/active/`` 路徑（無版本則 None）。"""
    latest = latest_version(discover_frozen_versions(repo_root))
    if latest is None:
        return None
    return os.path.join(repo_root, latest, "build", "planning", "active")


def lint(repo_root: str) -> list[tuple[str, str]]:
    """解析最新演化版，掃其 ``build/planning/active/``，回傳違規清單（已決 RFC 滯留）。"""
    active_dir = _latest_active_dir(repo_root)
    if active_dir is None:
        return []
    return find_decided_rfcs_in_active(active_dir, discover_frozen_versions(repo_root))


def missing_status(repo_root: str) -> list[str]:
    """解析最新演化版，掃其 active/，回傳缺標準 ``**狀態**：`` 欄的檔名（advisory）。"""
    active_dir = _latest_active_dir(repo_root)
    if active_dir is None:
        return []
    return find_active_rfcs_missing_status(active_dir)


def force_utf8_stdio() -> None:
    """島內（`AISDLC_SDD/scripts/`）強制 stdio 為 UTF-8 的**共用入口**。

    Windows 主控台預設 cp950/cp1252 無法輸出 emoji / 中文（對齊 arch_fitness）。
    本島搆不到根層 `tools/_stdio_utf8.py`（跨子專案 import 隔離），故島內自留一份；
    但**只留這一份**——島內姊妹模組一律 `from rfc_lifecycle_lint import
    force_utf8_stdio` 呼叫它，不得再各自寫一次行內 `reconfigure`
    （`tools/tests/test_platform_utils_dedup.py` 的 per-tree shrink-only 棘輪）。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - 舊版 / 非 TextIO
            pass


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    argv = sys.argv[1:] if argv is None else argv
    repo_root = argv[0] if argv else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 🔴 AGT-12（R85）fail-closed：本檔原本沒有這一段，於是 `_latest_active_dir()` 回 None 時
    # `lint()` 回空 list，main 直接印「✅ 最新版 active/ 無已決 RFC 滯留」並回 0——
    # 對一個它**從未找到、更未掃過**的目錄做正面斷言（四支 fail-open 中最嚴重的一種：
    # 其餘三支至少講了「略過」，這支連略過都沒說）。無版本目錄與無違規在 rc 上必須分得開。
    if _latest_active_dir(repo_root) is None:
        print(
            "::error:: RFC 生命週期 lint：找不到任何演化版目錄"
            f"（repo_root={repo_root!r}）——輸入不可信，一律 fail-closed，"
            "不得對未掃過的 active/ 做「無滯留」的正面宣稱",
            file=sys.stderr,
        )
        return 1
    violations = lint(repo_root)
    # W-33-2（DEF-30-001）：advisory 缺標準狀態欄 warn（不影響 exit code，僅促慣例採納）。
    for name in missing_status(repo_root):
        print(f"::warning:: RFC 缺標準 **狀態** 欄（建議 proposed/decided，DEF-30-001）：{name}")
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
