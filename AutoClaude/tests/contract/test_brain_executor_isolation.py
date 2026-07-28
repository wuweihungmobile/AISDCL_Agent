"""tests/contract/test_brain_executor_isolation.py — AC0-4（SD_Improving_06 W1 T1-10）。

驗證 importlinter `brain-executor-isolation` + `executor-brain-isolation` 雙向
forbidden contract 不被破壞（ADR-SD06-001 R3）。

策略：
  1. 解析 .importlinter 確認兩條 contract 存在
  2. 以 ast 解析來源檔，斷言 brain 模組沒有 import executor 模組（且反之亦然）
  3. 跑 lint-imports 確認 0 broken（subprocess；CI fail-fast 保險）

對應：
  - ADR-SD06-001 §2 R3：Brain ↔ Executor 互通必須走 EventBus
  - SD_06_Execution_Guide.md G1 驗證：4-5 kept / 0 broken
"""
from __future__ import annotations

import ast
import configparser
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_IMPORTLINTER = _ROOT / ".importlinter"


# ──────────────────────────────────────────────────────────────
# .importlinter 設定檔驗證
# ──────────────────────────────────────────────────────────────
class TestImportLinterConfig:
    def test_importlinter_config_exists(self):
        assert _IMPORTLINTER.exists(), "未找到 .importlinter；無法驗證 contract"

    def test_brain_executor_isolation_contract_defined(self):
        """雙向 forbidden contract 應同時存在。"""
        cfg = configparser.ConfigParser()
        cfg.read(_IMPORTLINTER, encoding="utf-8")
        section_names = cfg.sections()
        assert "importlinter:contract:brain-executor-isolation" in section_names
        assert "importlinter:contract:executor-brain-isolation" in section_names

    def test_brain_to_executor_contract_lists_correct_modules(self):
        cfg = configparser.ConfigParser()
        cfg.read(_IMPORTLINTER, encoding="utf-8")
        sec = cfg["importlinter:contract:brain-executor-isolation"]
        assert sec.get("type", "").strip() == "forbidden"
        sources = sec.get("source_modules", "")
        forbidden = sec.get("forbidden_modules", "")
        assert "autoclaude.core.ports.brain" in sources
        assert "autoclaude.infra.adapters.minimax_brain" in sources
        assert "autoclaude.core.ports.executor" in forbidden
        assert "autoclaude.infra.adapters.pty_executor" in forbidden

    def test_executor_to_brain_contract_lists_correct_modules(self):
        cfg = configparser.ConfigParser()
        cfg.read(_IMPORTLINTER, encoding="utf-8")
        sec = cfg["importlinter:contract:executor-brain-isolation"]
        assert sec.get("type", "").strip() == "forbidden"
        sources = sec.get("source_modules", "")
        forbidden = sec.get("forbidden_modules", "")
        assert "autoclaude.core.ports.executor" in sources
        assert "autoclaude.infra.adapters.pty_executor" in sources
        assert "autoclaude.core.ports.brain" in forbidden
        assert "autoclaude.infra.adapters.minimax_brain" in forbidden


# ──────────────────────────────────────────────────────────────
# AST 層級靜態驗證（不依賴 lint-imports CLI）
# ──────────────────────────────────────────────────────────────
def _collect_imports(path: Path) -> set[str]:
    """以 ast 解析檔案抽出所有 import 的 fully qualified module path。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


_BRAIN_MODULES = (
    "autoclaude/core/ports/brain.py",
    "autoclaude/infra/adapters/minimax_brain.py",
)
_EXECUTOR_MODULES = (
    "autoclaude/core/ports/executor.py",
    "autoclaude/infra/adapters/pty_executor.py",
    "autoclaude/infra/adapters/dry_run_executor.py",
    # improving_68 W-68-2：新執行器後端納入隔離靜態驗證
    "autoclaude/infra/adapters/sdk_executor_adapter.py",
)
_BRAIN_NAMES = {
    "autoclaude.core.ports.brain",
    "autoclaude.infra.adapters.minimax_brain",
}
_EXECUTOR_NAMES = {
    "autoclaude.core.ports.executor",
    "autoclaude.infra.adapters.pty_executor",
    "autoclaude.infra.adapters.dry_run_executor",
    "autoclaude.infra.adapters.sdk_executor_adapter",
}


class TestStaticImportIsolation:
    @pytest.mark.parametrize("rel_path", _BRAIN_MODULES)
    def test_brain_module_does_not_import_executor(self, rel_path: str):
        """Brain 系列檔案不可 import Executor 系列。"""
        imports = _collect_imports(_ROOT / rel_path)
        violating = imports & _EXECUTOR_NAMES
        assert not violating, (
            f"{rel_path} 違反 ADR R3 — 不可 import Executor 模組: {violating}"
        )

    @pytest.mark.parametrize("rel_path", _EXECUTOR_MODULES)
    def test_executor_module_does_not_import_brain(self, rel_path: str):
        """Executor 系列檔案不可 import Brain 系列。"""
        imports = _collect_imports(_ROOT / rel_path)
        violating = imports & _BRAIN_NAMES
        assert not violating, (
            f"{rel_path} 違反 ADR R3 — 不可 import Brain 模組: {violating}"
        )


# ──────────────────────────────────────────────────────────────
# lint-imports CLI 端對端驗證（CI fail-fast 保險）
# ──────────────────────────────────────────────────────────────
class TestImportLinterCLI:
    def test_lint_imports_passes(self):
        """執行 lint-imports CLI 確認 0 broken。"""
        # 不用 shutil.which() 預判是否「已安裝」——Windows 上 shutil.which 會依 PATHEXT
        # 找到 PATH 上任何同名 .bat/.cmd（例如與本 repo 無關的 pyenv-win shim），
        # 但緊接著 subprocess.run(shell=False) 對純 .bat 直接執行會拋 FileNotFoundError，
        # 造成「判定已安裝、卻執行失敗」的不一致。改為直接嘗試執行，
        # 找不到可執行檔（包含上述情境）一律視為未安裝並 skip。
        try:
            result = subprocess.run(
                ["lint-imports", "--config", ".importlinter"],
                cwd=str(_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env={**dict(__import__("os").environ), "PYTHONUTF8": "1"},
            )
        except FileNotFoundError:
            pytest.skip("lint-imports CLI 未安裝（pip install 'autoclaude[lint]'）")
        # 兩條 brain-executor contract 名稱必須出現在 KEPT 中
        assert "brain-executor-isolation" in result.stdout.lower() or \
               "Brain modules must not import Executor modules" in result.stdout, \
            f"brain-executor contract 未出現於 lint-imports 輸出：\n{result.stdout}"
        assert "0 broken" in result.stdout, \
            f"lint-imports 有 broken contract：\n{result.stdout}"
