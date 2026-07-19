"""Router hook 覆蓋 lint：偵測「最新演化版宣告的 CC hook event 未被根 router 涵蓋」（DEF-43-008 / DEF-B）.

共享 CI infra：位於 ``AISDLC_SDD/scripts/``（versioned 目錄之外，非任一 ``AISDLC_SDD_v0.0X``
凍結本體，免 Copy-on-Evolve；與 ``rfc_lifecycle_lint`` / ``gitignore_coverage_lint`` /
``collaboration_symmetry_lint`` 同精神）。

問題（DEF-43-008 / Architect 複核 DEF-B）：Claude Code 的 hooks 只從「啟動專案根
``.claude/settings.json``」載入、不遞迴子目錄，故 monorepo 根 session 下各版 ``.claude/hooks``
須經根層守衛式 router（``<monorepo>/.claude/hooks/sdd_hook_router.py``）橋接，且根
``.claude/settings.json`` 須把該 router wire 到對應 CC hook event。router 的 ``_HOOK_MAP``
與根 settings 的 ``hooks`` event 集合**全靠人工同步**：若未來某版的 ``.claude/settings.json``
新增第 4 種 CC hook event（如 ``Stop`` / ``UserPromptSubmit`` / ``SessionEnd``），而 router
``_HOOK_MAP`` 或根 settings 未同步加上，該版治理 hook 在 monorepo 根 session 下會**靜默失效**
（無機械守護＝maintainability 破口）。

機械強制（read-only 純觀察者，不寫 FSM-STATE、不影響 churn/meta-loop）：偵測磁碟**最新演化版**
（``discover_frozen_versions`` + ``latest_version``，複用 ``rfc_lifecycle_lint``，對齊
``scripts/sdd_version.py`` SSOT 的 LATEST 語意；沿用磁碟掃描之 WHY 見該檔豁免註記）
的 ``.claude/settings.json`` 宣告的 CC hook event，斷言其**子集**於
「router ``_HOOK_MAP`` 涵蓋 ∩ 根 settings wire」之 event 集合。任一 event 不可達即**非零硬閘**
擋下（與 gitignore advisory 不同——不可達治理 hook 是真正的正確性破口，須 fail-loud，Rule 12）。

repo_root 語意同 sibling lint：ci-gate 以 ``AISDLC_SDD/`` 為 repo_root 傳入（版本目錄之父）；
本 lint 另需 monorepo 根（含根 ``.claude/``）＝ repo_root 之父（fallback：repo_root 自身）。
"""
from __future__ import annotations

import ast
import json
import os
import sys

from rfc_lifecycle_lint import discover_frozen_versions, latest_version

# DEF-43-012：根 settings 某 event 須真 wire 到此 router basename 才算「經 router 可達」，
# 防「event 宣告卻 wire 到別的腳本」之假綠（僅取 hooks keys 不驗 command 指向的韌性縫）。
_ROUTER_BASENAME = "sdd_hook_router.py"


# ── 純邏輯（可測，不碰 IO）─────────────────────────────────────────────────
def unreachable_events(
    version_events: set[str], router_events: set[str], root_settings_events: set[str]
) -> list[str]:
    """回「版本宣告卻不可達」的 CC hook event（排序）。

    可達 = 同時被 router ``_HOOK_MAP`` 涵蓋 **且** 被根 settings wire；二者缺一即不可達。
    """
    reachable = router_events & root_settings_events
    return sorted(version_events - reachable)


# ── IO 解析 ─────────────────────────────────────────────────────────────
def settings_hook_events(settings_path: str) -> set[str]:
    """讀 ``.claude/settings.json``，回 ``hooks`` 下宣告的 event 名集合（無檔/無 hooks → 空集）。

    用於**版本側**（該版宣告「需被治理」的 event）——只看宣告，不問 command 指向誰。
    """
    if not os.path.isfile(settings_path):
        return set()
    with open(settings_path, encoding="utf-8") as f:
        data = json.load(f)
    return set((data.get("hooks") or {}).keys())


def router_wired_events(settings_path: str) -> set[str]:
    """讀 ``.claude/settings.json``，回「至少一個 hook command 真指向 router」的 event 名集合。

    用於**根側**：比 ``settings_hook_events`` 嚴——event 僅宣告 key 不夠，其下至少一個 hook 的
    ``command`` 須含 ``sdd_hook_router.py`` 才算「經 router 可達」（DEF-43-012）。防假綠：根 settings
    宣告了某 event 卻把它 wire 到別的腳本（非 router）時，舊版 ``settings_hook_events`` 仍會誤判可達。
    結構：``hooks[event] = [ {"hooks": [ {"command": ...}, ... ]}, ... ]``；全程防呆，無檔/畸形 → 空集。
    """
    if not os.path.isfile(settings_path):
        return set()
    with open(settings_path, encoding="utf-8") as f:
        data = json.load(f)
    out: set[str] = set()
    for event, groups in (data.get("hooks") or {}).items():
        for group in groups or []:
            if not isinstance(group, dict):
                continue
            if any(
                isinstance(h, dict) and _ROUTER_BASENAME in (h.get("command") or "")
                for h in (group.get("hooks") or [])
            ):
                out.add(event)
                break
    return out


def router_mapped_events(router_path: str) -> set[str]:
    """ast 解析 router 的 ``_HOOK_MAP``，回其映射到的 CC hook event 名集合。

    ``_HOOK_MAP`` 形如 ``{"session_start": ("session_start.py", "SessionStart"), ...}``——
    取每個 value tuple 的第 2 元素（event 名）。以 ``ast.literal_eval`` 安全求值，不執行 router。
    """
    if not os.path.isfile(router_path):
        return set()
    with open(router_path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "_HOOK_MAP":
                    mapping = ast.literal_eval(node.value)
                    return {v[1] for v in mapping.values()}
    return set()


def _monorepo_root(repo_root: str) -> str | None:
    """定位含根 ``.claude/hooks/sdd_hook_router.py`` 的 monorepo 根。

    repo_root 通常為 ``AISDLC_SDD/`` → monorepo 根為其父；fallback 檢 repo_root 自身。
    """
    for cand in (os.path.dirname(os.path.abspath(repo_root)), os.path.abspath(repo_root)):
        if os.path.isfile(os.path.join(cand, ".claude", "hooks", "sdd_hook_router.py")):
            return cand
    return None


def analyze(repo_root: str) -> dict:
    """彙整檢查所需事實。回 dict（latest=None 表無版本；error 表無法定位 router）。"""
    latest = latest_version(discover_frozen_versions(repo_root))
    if latest is None:
        return {"latest": None}
    monorepo = _monorepo_root(repo_root)
    if monorepo is None:
        return {"latest": latest, "error": "找不到根 .claude/hooks/sdd_hook_router.py"}
    router = os.path.join(monorepo, ".claude", "hooks", "sdd_hook_router.py")
    root_settings = os.path.join(monorepo, ".claude", "settings.json")
    version_settings = os.path.join(repo_root, latest, ".claude", "settings.json")
    ver_events = settings_hook_events(version_settings)
    rtr_events = router_mapped_events(router)
    # DEF-43-012：根側用 router_wired_events（驗 command 真指向 router），非僅取 keys。
    root_events = router_wired_events(root_settings)
    return {
        "latest": latest,
        "version_events": ver_events,
        "router_events": rtr_events,
        "root_settings_events": root_events,
        "unreachable": unreachable_events(ver_events, rtr_events, root_events),
    }


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - 舊版 / 非 TextIO
            pass
    argv = sys.argv[1:] if argv is None else argv
    repo_root = argv[0] if argv else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    res = analyze(repo_root)
    if res["latest"] is None:
        print("✅ router hook 覆蓋 lint：無演化版目錄，略過")
        return 0
    if res.get("error"):
        print(f"::error:: router hook 覆蓋 lint：{res['error']}", file=sys.stderr)
        return 1
    latest = res["latest"]
    if not res["unreachable"]:
        print(
            f"✅ router hook 覆蓋 lint：最新版 {latest} 宣告之 CC hook event "
            f"{sorted(res['version_events'])} 全部可達（router ∩ 根 settings）"
        )
        return 0
    print(
        f"::error:: 最新演化版 {latest} 的 .claude/settings.json 宣告了不可達的 CC hook event："
        f"{res['unreachable']}（DEF-43-008）。這些 hook 在 monorepo 根 session 下會靜默失效。",
        file=sys.stderr,
    )
    print(
        f"  router _HOOK_MAP 涵蓋={sorted(res['router_events'])}；"
        f"根 settings wire={sorted(res['root_settings_events'])}。",
        file=sys.stderr,
    )
    print(
        "  修復：於 <monorepo>/.claude/hooks/sdd_hook_router.py 的 _HOOK_MAP 加映射，"
        "並於 <monorepo>/.claude/settings.json 為該 event wire router。",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
