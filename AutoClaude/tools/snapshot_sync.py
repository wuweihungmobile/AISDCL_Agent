#!/usr/bin/env python
"""snapshot_sync — 從程式碼自動回填 CLAUDE.md `[Architecture Snapshot]` 區段。

對應 ADR-SD08-001 §3.2 + §2.2：
  - 讀取 autoclaude/core/wiring.py 的 `_REGISTER_ORDER`（Plugin 列表）
  - 讀取 autoclaude/core/ports/ 目錄（Port 列表）
  - 讀取 autoclaude/infra/repositories/factory.py 的 mode 矩陣
  - 讀取 .importlinter 的 contract 名稱
  - 讀取 tools/check_loc_budget.py 的 LOC_TIERS

使用：
  python tools/snapshot_sync.py            # 寫回 CLAUDE.md（in-place）
  python tools/snapshot_sync.py --check    # 僅檢查是否漂移（CI 用，exit 1 表示漂移）
  python tools/snapshot_sync.py --print    # 印出生成內容（不寫檔）
"""
from __future__ import annotations

import ast
import io
import re
import sys
from pathlib import Path

def _init_utf8_streams() -> None:
    """Windows console UTF-8；只在 __main__ 觸發，避免污染 pytest stdout/stderr。"""
    if sys.platform != "win32":
        return
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WIRING_FILE = PROJECT_ROOT / "autoclaude" / "core" / "wiring.py"
PORTS_DIR = PROJECT_ROOT / "autoclaude" / "core" / "ports"
FACTORY_FILE = PROJECT_ROOT / "autoclaude" / "infra" / "repositories" / "factory.py"
IMPORTLINTER_FILE = PROJECT_ROOT / ".importlinter"
LOC_TOOL_FILE = PROJECT_ROOT / "tools" / "check_loc_budget.py"
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
SPRINT_HISTORY = PROJECT_ROOT / "docs" / "05_development" / "sprint_history.md"

SNAPSHOT_BEGIN = "<!-- ARCH_SNAPSHOT_BEGIN -->"
SNAPSHOT_END = "<!-- ARCH_SNAPSHOT_END -->"

# 條件式註冊的 plugin（caller 傳入才啟用；預設組態不啟用）。
# 用於 count_active_plugins() 的 fallback path，確保「無 autoclaude 相依」的 CI lint job
# （claude-md-budget 僅 setup-python、不 pip install）與「有相依」的本地環境產出一致的
# active 數，避免 snapshot --check 平台漂移（SD_09 R56 audit：CI 報 DRIFT 14 vs 本地 13）。
_CONDITIONAL_PLUGINS = frozenset({"hotkey"})

# ADR-SD08-001 v1.1 §9 — W 期間骨架先行 SOP 對齊驗證
CLAUDE_MD_SPRINT_H3 = re.compile(r"^### SD_Improving_(\d+)")
SPRINT_HISTORY_H3 = re.compile(r"^### 1\.\d+ SD_Improving_(\d+)")


def extract_register_order() -> list[str]:
    """從 wiring.py 解析 `_REGISTER_ORDER` tuple（含 AnnAssign 帶型別註解）。

    注意：此函式僅讀靜態 tuple 內容；HotkeyPlugin 是條件式註冊（caller 傳入
    hotkey 才會啟用），靜態 tuple 含 "hotkey" 故長度恆 = 14。真實 runtime 數量
    請用 count_active_plugins() 取得（SD_09 Pre-W0 audit P0-07）。
    """
    src = WIRING_FILE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        target_name = None
        value = None
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "_REGISTER_ORDER":
                    target_name = tgt.id
                    value = node.value
                    break
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "_REGISTER_ORDER":
                target_name = node.target.id
                value = node.value
        if target_name and isinstance(value, ast.Tuple):
            return [
                elt.value
                for elt in value.elts
                if isinstance(elt, ast.Constant)
            ]
    return []


def count_active_plugins() -> int:
    """SD_09 Pre-W0 audit P0-07：動態計算實際 plugin 註冊數。

    呼叫 `_build_plugin_set(default_config)` 取得真實 dict 並排除非 register 項
    （mutation_service）。`hotkey` 依 caller 傳入決定；預設組態不啟用 →
    回傳數量 = 13（不含 HotkeyPlugin；HotkeyPlugin 條件式註冊）。

    若 import 失敗（如循環 import / 測試環境）→ fallback 用 _REGISTER_ORDER 長度
    （= 14，含靜態 "hotkey" 條目，與靜態 snapshot 結果一致）。
    """
    try:
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from autoclaude.core.wiring import _build_plugin_set  # noqa: PLC0415
        from autoclaude.utils.config import AppConfig  # noqa: PLC0415

        cfg = AppConfig()
        plugins = _build_plugin_set(cfg)
        # 排除非註冊項（mutation_service 不過 EventBus register）
        return sum(1 for name in plugins if name != "mutation_service")
    except Exception:
        # fallback（SD_09 R56 audit 修復）：靜態 _REGISTER_ORDER 排除「條件式 plugin」。
        # 預設組態 _build_plugin_set 不啟用 hotkey → active=13；fallback 須同樣排除 hotkey
        # 才能與 import-path 一致（= 13），否則無相依的 CI lint job 會回 14 → snapshot DRIFT。
        return sum(
            1 for name in extract_register_order() if name not in _CONDITIONAL_PLUGINS
        )


def extract_ports() -> list[str]:
    """列出 autoclaude/core/ports/*.py（排除 __init__.py）。"""
    if not PORTS_DIR.exists():
        return []
    ports = sorted(
        p.stem for p in PORTS_DIR.glob("*.py") if p.stem != "__init__"
    )
    return ports


def extract_storage_modes() -> list[tuple[str, str]]:
    """從 factory.py 解析 storage.mode 矩陣（硬編碼三選項）。"""
    return [
        ("yaml_only", "FileStateRepository（單一；零 PG 依賴）"),
        ("both", "DualStateRepository（File 主寫 + PG 影子；fail_loud/yaml_wins/db_wins）"),
        ("db_only", "PgStateRepository（單一；YAML 僅供匯入）"),
    ]


def extract_importlinter_rules() -> list[str]:
    """從 .importlinter 抓 `name = ...` 條目。"""
    if not IMPORTLINTER_FILE.exists():
        return []
    text = IMPORTLINTER_FILE.read_text(encoding="utf-8")
    return re.findall(r"^name\s*=\s*(.+?)$", text, flags=re.MULTILINE)


def extract_loc_tiers() -> list[tuple[str, int]]:
    """從 tools/check_loc_budget.py LOC_TIERS dict 抽 (tier, budget)。"""
    src = LOC_TOOL_FILE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    tiers: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "LOC_TIERS":
                if isinstance(node.value, ast.Dict):
                    for k, v in zip(node.value.keys, node.value.values, strict=False):
                        if not isinstance(k, ast.Constant):
                            continue
                        if isinstance(v, ast.Dict):
                            for sk, sv in zip(v.keys, v.values, strict=False):
                                if (
                                    isinstance(sk, ast.Constant)
                                    and sk.value == "budget"
                                    and isinstance(sv, ast.Constant)
                                ):
                                    tiers.append((k.value, sv.value))
    return tiers


def build_snapshot() -> str:
    """生成 [Architecture Snapshot] 區段內容。

    注意（P0-D1 修復）：標題不再硬編碼日期，避免每次跑 --check 都因日期不同而漂移。
    區段最後更新時間可由 git log 取得：`git log -1 --format=%cs CLAUDE.md`。
    """
    register_order = extract_register_order()
    ports = extract_ports()
    storage_modes = extract_storage_modes()
    rules = extract_importlinter_rules()
    tiers = extract_loc_tiers()

    parts: list[str] = []
    parts.append(SNAPSHOT_BEGIN)
    parts.append(
        "## [Architecture Snapshot] — 由 tools/snapshot_sync.py 自動生成"
        "（請勿手動編輯本區段；以 `python tools/snapshot_sync.py` 重新生成）"
    )
    parts.append("")
    parts.append("### LOC Tiers（ADR-SD07-001 + ADR-SD08-001）")
    parts.append("| Tier | Budget | 對應路徑 |")
    parts.append("|------|--------|---------|")
    for tier_name, budget in tiers:
        parts.append(f"| {tier_name} | ≤ {budget} | （見 tools/check_loc_budget.py）|")
    parts.append("| absolute_limit | ≤ 750 | 全域絕對紅線（任何層級不得超）|")
    parts.append("| special: CLAUDE.md | ≤ 400 | ADR-SD08-001 文件治理 |")
    parts.append("")
    parts.append(f"### importlinter Rules（目前 {len(rules)} kept）")
    for idx, r in enumerate(rules, 1):
        parts.append(f"{idx}. {r}")
    parts.append("")
    # P0-07：plugin count 採真實動態值（涵蓋條件式 HotkeyPlugin）
    # 列表內容仍由靜態 _REGISTER_ORDER 提供（保留 priority / tie-breaker 排序語意）
    active_count = count_active_plugins()
    parts.append(
        f"### Plugin 列表（{active_count} 個 active / {len(register_order)} 個靜態，"
        f"按 wiring._REGISTER_ORDER）"
    )
    for idx, name in enumerate(register_order, 1):
        parts.append(f"{idx}. {name}")
    parts.append("")
    parts.append(f"### Port 列表（{len(ports)} 個，autoclaude/core/ports/）")
    for p in ports:
        parts.append(f"- {p}")
    parts.append("")
    parts.append("### DAL 三後端 storage.mode 矩陣（autoclaude/infra/repositories/factory.py）")
    parts.append("| Mode | 行為 |")
    parts.append("|------|------|")
    for mode, behavior in storage_modes:
        parts.append(f"| `{mode}` | {behavior} |")
    parts.append("")
    parts.append(SNAPSHOT_END)
    return "\n".join(parts)


def check_sprint_skeleton_alignment() -> list[str]:
    """ADR-SD08-001 v1.1 §9 — CLAUDE.md sprint H3 vs sprint_history.md §1.X 骨架對齊。

    回傳缺漏訊息 list（空 = 無漂移）。涵蓋三種漂移：
      1. CLAUDE.md 含 ### SD_Improving_NN 但 sprint_history.md 缺 ### 1.X SD_Improving_NN 骨架
      2. CLAUDE.md 有重複 ### SD_Improving_NN H3（R23 audit P2-4 修復；set 去重會吃掉重複）
      3. sprint_history.md 有重複 §1.X SD_Improving_NN 段
    """
    from collections import Counter

    issues: list[str] = []
    if not CLAUDE_MD.exists() or not SPRINT_HISTORY.exists():
        return issues  # fail-open
    claude_nn_list: list[str] = []
    for line in CLAUDE_MD.read_text(encoding="utf-8").splitlines():
        m = CLAUDE_MD_SPRINT_H3.match(line)
        if m:
            claude_nn_list.append(m.group(1))
    history_nn_list: list[str] = []
    for line in SPRINT_HISTORY.read_text(encoding="utf-8").splitlines():
        m = SPRINT_HISTORY_H3.match(line)
        if m:
            history_nn_list.append(m.group(1))

    claude_counts = Counter(claude_nn_list)
    history_counts = Counter(history_nn_list)
    claude_nns = set(claude_nn_list)
    history_nns = set(history_nn_list)

    # 漂移 1：CLAUDE.md NN 缺對應 history 段
    missing = sorted(claude_nns - history_nns)
    for nn in missing:
        issues.append(
            f"CLAUDE.md 含 ### SD_Improving_{nn} 但 sprint_history.md 缺對應 ### 1.X SD_Improving_{nn} 骨架；"
            f"請跑 `python tools/scaffold_sprint_section.py --sprint {nn} --title <主軸>`"
        )

    # 漂移 2：CLAUDE.md 重複 H3
    for nn, c in sorted(claude_counts.items()):
        if c > 1:
            issues.append(
                f"CLAUDE.md 含重複 ### SD_Improving_{nn} H3（出現 {c} 次）；"
                f"set 去重會吃掉重複導致 alignment 誤判通過。請刪除重複段。"
            )

    # 漂移 3：sprint_history.md 重複段
    for nn, c in sorted(history_counts.items()):
        if c > 1:
            issues.append(
                f"sprint_history.md 含重複 ### 1.X SD_Improving_{nn} 段（出現 {c} 次）；"
                f"請合併或刪除。"
            )

    return issues


def sync(check_only: bool = False, print_only: bool = False) -> int:
    new_block = build_snapshot()
    if print_only:
        print(new_block)
        return 0

    if not CLAUDE_MD.exists():
        print(f"[snapshot_sync] CLAUDE.md 不存在: {CLAUDE_MD}", file=sys.stderr)
        return 1

    current = CLAUDE_MD.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(SNAPSHOT_BEGIN) + r".*?" + re.escape(SNAPSHOT_END),
        re.DOTALL,
    )

    if pattern.search(current):
        updated = pattern.sub(new_block, current)
    else:
        # 首次安裝：附加在文件末尾
        updated = current.rstrip() + "\n\n" + new_block + "\n"

    if check_only:
        rc = 0
        if updated != current:
            print(
                "[snapshot_sync] DRIFT — CLAUDE.md [Architecture Snapshot] "
                "與真實程式碼漂移；請執行 `python tools/snapshot_sync.py`",
                file=sys.stderr,
            )
            rc = 1
        # ADR-SD08-001 v1.1 §9：sprint 骨架對齊驗證
        sprint_issues = check_sprint_skeleton_alignment()
        if sprint_issues:
            for msg in sprint_issues:
                print(f"[snapshot_sync] SPRINT_SKELETON_MISSING — {msg}", file=sys.stderr)
            rc = 1
        if rc == 0:
            print("[snapshot_sync] OK — Snapshot 區段 + sprint 骨架對齊一致")
        return rc

    if updated == current:
        print("[snapshot_sync] no change")
        return 0
    CLAUDE_MD.write_text(updated, encoding="utf-8")
    print(f"[snapshot_sync] CLAUDE.md updated（{len(new_block)} chars）")
    return 0


def main() -> int:
    check = "--check" in sys.argv
    print_only = "--print" in sys.argv
    return sync(check_only=check, print_only=print_only)


if __name__ == "__main__":
    _init_utf8_streams()
    sys.exit(main())
