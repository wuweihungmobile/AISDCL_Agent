"""Plugin walk-through contract tests — SD_07 W5 T5-5.

對應：
  - SD_Improving_07.md §4 W5 T5-5（≥ 12 case：每 Plugin 一條 isolation 檢查）
  - SD07_Plugin_Audit_Report.md §3 §4 §5 §6（公開 API + import 隔離 + DI 注入 + coverage）

驗證內容（每 Plugin 一條 case）：
  1. Plugin class 可從 `autoclaude.plugins` 公開 entry import
  2. Plugin 不直接 import 其他 plugin 模組（plugin-to-plugin isolation）
  3. Plugin 不直接 import infra 層（必須透過 constructor 注入）

importlinter `plugin-isolation` / `core-purity` / `runner-no-checkpoint-logic`
契約由 lint-imports 全局驗證；本檔提供程式化、可獨立執行的 per-plugin 檢查，
作為退化保護網（CI 中先於 lint-imports 跑，更早暴露違規）。
"""
from __future__ import annotations

import ast
import importlib
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLUGINS_DIR = PROJECT_ROOT / "autoclaude" / "plugins"


# ── 公開 entry 對照表 ────────────────────────────────────────────────
# 17 個 Plugin（SD_06 W6 12 + SD_05 W4 補 2 + AutoSDD_improving_01 W6 補 1
#   + Improving_012 Phase 1 補 2：PreferenceMemory / GoalProgress）
# — 對應 autoclaude/plugins/__init__.py
PLUGIN_REGISTRY: dict[str, dict] = {
    "PreRunValidatorPlugin": {
        "module": "autoclaude.plugins.pre_run_validator_plugin", "priority": 5},
    "HotkeyPlugin": {
        "module": "autoclaude.plugins.hotkey_plugin", "priority": 10},
    "CrossStepValidatorPlugin": {
        "module": "autoclaude.plugins.cross_step_validator_plugin", "priority": 15},
    "TokenGuardPlugin": {
        "module": "autoclaude.plugins.token_guard_plugin", "priority": 30},
    "GlobalGoalAnchorPlugin": {
        "module": "autoclaude.plugins.global_goal_anchor_plugin", "priority": 35},
    "PlaybookPersistencePlugin": {
        "module": "autoclaude.plugins.playbook_persistence_plugin", "priority": 40},
    "SddGovernancePlugin": {
        "module": "autoclaude.plugins.sdd_governance_plugin", "priority": 45},
    "FastPathPlugin": {
        "module": "autoclaude.plugins.fast_path_plugin", "priority": 50},
    "NotificationPlugin": {
        "module": "autoclaude.plugins.notification_plugin", "priority": 50},
    "KnowledgeBasePlugin": {
        "module": "autoclaude.plugins.knowledge_base_plugin", "priority": 50},
    "PreferenceMemoryPlugin": {
        "module": "autoclaude.plugins.preference_memory_plugin", "priority": 50},
    "GoalSynthesisPlugin": {
        "module": "autoclaude.plugins.goal_synthesis_plugin", "priority": 50},
    "GoalProgressPlugin": {
        "module": "autoclaude.plugins.goal_progress_plugin", "priority": 50},
    "ConvergencePlugin": {
        "module": "autoclaude.plugins.convergence_plugin", "priority": 65},
    "EvolutionPlugin": {
        "module": "autoclaude.plugins.evolution_plugin", "priority": 70},
    "GotoCounterPlugin": {
        "module": "autoclaude.plugins.goto_counter_plugin", "priority": 85},
    "CheckpointPlugin": {
        "module": "autoclaude.plugins.checkpoint_plugin", "priority": 90},
}


# ── helpers ─────────────────────────────────────────────────────────


def _resolve_source(module_path: str) -> Path:
    """解析 plugin module 對應的實際 .py 檔案路徑。

    - 若 `<stem>_plugin.py` 為 shim re-export（內容極短），且同名 stem 套件存在
      （如 `checkpoint/plugin.py`、`token_guard/policy.py`），則回傳套件的 entry。
    - 偵測規則：對 `*_plugin.py` shim，若 stem 去掉 `_plugin` 後對應目錄存在，
      則優先回傳該目錄下的 `plugin.py`（checkpoint）或 `policy.py`（token_guard）。
    """
    rel = module_path.replace("autoclaude.", "autoclaude/").replace(".", "/") + ".py"
    p = PROJECT_ROOT / rel
    # 偵測 shim：檔名為 *_plugin.py 且對應 package 存在
    if p.exists() and p.name.endswith("_plugin.py"):
        stem = p.stem[: -len("_plugin")]  # checkpoint_plugin → checkpoint
        package_dir = p.parent / stem
        if package_dir.is_dir():
            for entry_name in ("plugin.py", "policy.py"):
                candidate = package_dir / entry_name
                if candidate.exists():
                    return candidate
    return p


def _ast_imports(path: Path) -> list[str]:
    """parse 檔案 AST，回傳所有 `from X import Y` 與 `import X` 的 X 字串清單。"""
    if not path.exists():
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            out.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                out.append(alias.name)
    return out


# ── case 1：14 Plugin 公開 entry import OK ──────────────────────────


@pytest.mark.parametrize("plugin_name", list(PLUGIN_REGISTRY.keys()))
def test_plugin_public_entry_importable(plugin_name: str):
    """每個 Plugin 必須可從 `autoclaude.plugins` 公開 entry import。"""
    plugins_pkg = importlib.import_module("autoclaude.plugins")
    assert hasattr(plugins_pkg, plugin_name), (
        f"{plugin_name} 必須在 autoclaude/plugins/__init__.py 公開 export"
    )
    assert plugin_name in plugins_pkg.__all__, (
        f"{plugin_name} 必須出現在 __all__"
    )


# ── case 2：plugin-to-plugin import 隔離（per Plugin）────────────────


@pytest.mark.parametrize("plugin_name,info", list(PLUGIN_REGISTRY.items()))
def test_plugin_does_not_import_other_plugins(plugin_name: str, info: dict):
    """每個 Plugin 模組（含 package plugin.py）不可直接 import 其他 plugin。

    協作必須走 EventBus（HookSpec phases）— importlinter `plugin-isolation`
    全局驗證；本 case 提供 per-plugin、可獨立執行的早期偵測。
    """
    src = _resolve_source(info["module"])
    assert src.exists(), f"source file not found: {src}"
    imports = _ast_imports(src)
    plugin_imports = [
        m for m in imports
        if m.startswith("autoclaude.plugins.") and not m.startswith(info["module"])
    ]
    # 允許自己 package 內的子模組（如 checkpoint package 內 _phase_handlers）
    own_package = info["module"].rsplit(".", 1)[0]
    plugin_imports = [
        m for m in plugin_imports
        if not m.startswith(own_package + ".")
        and m != own_package
    ]
    assert plugin_imports == [], (
        f"{plugin_name} 不可直接 import 其他 plugin（請改走 EventBus）；"
        f"違規 import: {plugin_imports}"
    )


# ── case 3：直接 import infra 隔離（per Plugin）─────────────────────


@pytest.mark.parametrize("plugin_name,info", list(PLUGIN_REGISTRY.items()))
def test_plugin_does_not_import_infra_directly(plugin_name: str, info: dict):
    """每個 Plugin 不可直接 import `autoclaude.infra.*`（必須走 constructor DI）。

    infra 依賴須由 `autoclaude/core/wiring.py` 集中組裝注入。
    """
    src = _resolve_source(info["module"])
    imports = _ast_imports(src)
    infra_imports = [m for m in imports if m.startswith("autoclaude.infra")]
    assert infra_imports == [], (
        f"{plugin_name} 不可直接 import autoclaude.infra（請改走 constructor 注入）；"
        f"違規 import: {infra_imports}"
    )


# ── case 4：PRIORITY 常數存在且為 int（wiring 排序需要）─────────────


@pytest.mark.parametrize("plugin_name,info", list(PLUGIN_REGISTRY.items()))
def test_plugin_priority_constant_matches_audit_report(plugin_name: str, info: dict):
    """PRIORITY 常數須為 int 且與 SD07_Plugin_Audit_Report.md §3 表格一致。"""
    src = _resolve_source(info["module"])
    text = src.read_text(encoding="utf-8")
    match = re.search(r"^\s*PRIORITY\s*=\s*(\d+)", text, re.MULTILINE)
    assert match, f"{plugin_name} 未定義 PRIORITY 常數於 {src.name}"
    actual = int(match.group(1))
    assert actual == info["priority"], (
        f"{plugin_name} PRIORITY={actual}，與 audit report §3 不一致（期望 {info['priority']}）"
    )


# ── case 5：wiring `_REGISTER_ORDER` 涵蓋 13 個 non-optional plugin ─


def test_wiring_register_order_covers_all_non_optional_plugins():
    """`wiring._REGISTER_ORDER` 必須涵蓋 17 個 plugin（hotkey optional 含在內）。"""
    wiring = importlib.import_module("autoclaude.core.wiring")
    order = wiring._REGISTER_ORDER
    assert len(order) >= 17, f"_REGISTER_ORDER 應涵蓋全部 17 plugin，實際 {len(order)}"
    # hotkey 為 optional（hotkey_handler=None 時跳過）— 但仍應在 order 中
    expected = {
        "pre_run_validator", "hotkey", "cross_step_validator", "token_guard",
        "global_goal_anchor", "playbook_persistence", "sdd_governance",
        "fast_path", "notification",
        "knowledge_base", "preference_memory", "goal_synthesis", "goal_progress",
        "convergence", "evolution",
        "goto_counter", "checkpoint",
    }
    assert set(order) == expected, (
        f"_REGISTER_ORDER 與 audit 不一致；缺 {expected - set(order)} / 多 {set(order) - expected}"
    )


# ── case 6：tie-breaker 順序（priority=50 的 4 plugin）─────────────


def test_priority_50_tie_breaker_order_preserved():
    """fast_path 必須早於 notification / knowledge_base / goal_synthesis 註冊
    （priority=50 tie-breaker；wiring.py docstring 明確規範）。"""
    wiring = importlib.import_module("autoclaude.core.wiring")
    order = wiring._REGISTER_ORDER
    fast_path_idx = order.index("fast_path")
    for sibling in ("notification", "knowledge_base", "goal_synthesis"):
        assert fast_path_idx < order.index(sibling), (
            f"fast_path 必須早於 {sibling}（priority=50 tie-breaker）"
        )


# ── case 7：runner-no-checkpoint-logic contract 旁證（直接掃 source）──


def test_runner_does_not_import_checkpoint_internals():
    """SD_07 W5 T5-2：playbook_runner 與 strategy 模組不可直接 import
    `autoclaude.plugins.checkpoint._*` 內部模組（importlinter Rule 6 旁證）。
    """
    forbidden_internals = {
        "autoclaude.plugins.checkpoint._phase_handlers",
        "autoclaude.plugins.checkpoint._token_halt",
        "autoclaude.plugins.checkpoint._builder",
        "autoclaude.plugins.checkpoint._escalation",
        "autoclaude.plugins.checkpoint._interrupt",
        "autoclaude.plugins.checkpoint._evolution",
    }
    runner_sources = [
        PROJECT_ROOT / "autoclaude" / "execution" / "playbook_runner.py",
        PROJECT_ROOT / "autoclaude" / "execution" / "boot_helper.py",
        PROJECT_ROOT / "autoclaude" / "execution" / "prompt_dispatcher.py",
        PROJECT_ROOT / "autoclaude" / "execution" / "escalation_dumper.py",
    ]
    for src in runner_sources:
        if not src.exists():
            continue
        imports = set(_ast_imports(src))
        violations = imports & forbidden_internals
        assert not violations, (
            f"{src.relative_to(PROJECT_ROOT)} 不可直接 import checkpoint 內部模組；"
            f"違規: {violations}"
            "（請改用 `from autoclaude.plugins.checkpoint import CheckpointPlugin`）"
        )
