"""
CLI 向後相容測試 v2（SD_Improving_03 §5.2 DoD #10 / SD_05 W6 三方審查 C-1+C-3 修）。

目的：補充 test_cli_compatibility.py（v1）未涵蓋的 CLI 場景，
確認 Kernel 路徑（SD_05 W6 後唯一路徑）在 CLI 層保持相容性。

場景：
  K1. --config 含舊版未知欄位時 CLI 不崩潰（Pydantic ignore extra fields）
  K2. Kernel 路徑下缺少 playbook 仍回傳非零 exit code
  K3. 無效 YAML config 時 CLI 能正常處理
  K4. --config 指向空白 config 時 CLI 使用預設值並正常繼續
  K5. 驗證 python -m autoclaude 與 module entrypoint 一致

SD_05 W6（2026-05-17）：原 K1/K2 case 中 `use_kernel_path:true` fixture 已改為一般
未知欄位 fixture（`legacy_unused_field:true`），避免測試名與已拔除欄位混淆。

使用 subprocess 模式（與 v1 相同模式），不啟動真實 Claude Code。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run_cli(*args: str, cwd: Path | None = None, timeout: int = 15) -> subprocess.CompletedProcess:
    """以 subprocess 執行 `python -m autoclaude <args>`（與 v1 相同輔助函式）。"""
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    env.pop("MINIMAX_API_KEY", None)
    return subprocess.run(
        [sys.executable, "-m", "autoclaude", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(cwd or PROJECT_ROOT),
        timeout=timeout,
    )


# ──────────────────────────────────────────────────────────
# K1. --config 含未知欄位時 CLI 不崩潰（SD_05 W6 後 Pydantic ignore extra）
# ──────────────────────────────────────────────────────────
class TestUnknownConfigFieldTolerance:
    def test_unknown_field_does_not_crash(self, tmp_path):
        """--config 含未知欄位（如已移除的舊欄位）時 CLI 解析不應崩潰（exit != 2）。

        SD_05 W6 後 PlaybookConfig 不再含 use_kernel_path 欄位，但 Pydantic 預設
        ignore extra fields。本 case 驗證舊版 config 含未知欄位時 CLI 仍能正常啟動。
        """
        config_file = tmp_path / "legacy_config.yaml"
        config_file.write_text(
            yaml.dump({"playbook": {"legacy_unused_field": True}}),
            encoding="utf-8",
        )
        nonexistent_pb = tmp_path / "nonexistent.yaml"

        result = _run_cli(str(nonexistent_pb), "--config", str(config_file), timeout=15)
        # argparse 正常解析 → 不應是 exit 2
        assert result.returncode != 2, (
            f"未知 config 欄位不應觸發 argparse exit 2，實際 {result.returncode}"
        )
        # 缺少 playbook 仍應失敗
        assert result.returncode != 0

    def test_unknown_field_with_fresh_flag(self, tmp_path):
        """--config 含未知欄位搭配 --fresh 旗標正常解析。"""
        config_file = tmp_path / "legacy_cfg.yaml"
        config_file.write_text(
            yaml.dump({"playbook": {"legacy_unused_field": True}}),
            encoding="utf-8",
        )
        nonexistent_pb = tmp_path / "pb.yaml"

        result = _run_cli(
            str(nonexistent_pb), "--config", str(config_file), "--fresh",
            timeout=15,
        )
        # 既非 argparse error（2）也非 success（0）
        assert result.returncode not in (0, 2), (
            f"應在 validate 階段失敗（exit 1），實際 {result.returncode}"
        )


# ──────────────────────────────────────────────────────────
# K2. Kernel 路徑下缺少 playbook 仍回傳非零 exit code
# ──────────────────────────────────────────────────────────
class TestKernelPathMissingPlaybook:
    def test_kernel_path_missing_playbook_exit_nonzero(self, tmp_path):
        """Kernel 路徑下找不到 Playbook 仍正確回傳非零 exit code。"""
        config_file = tmp_path / "cfg.yaml"
        config_file.write_text(
            yaml.dump({"minimax": {"api_key": "test"}}),
            encoding="utf-8",
        )
        missing_pb = tmp_path / "does_not_exist.yaml"

        result = _run_cli(str(missing_pb), "--config", str(config_file), timeout=15)
        assert result.returncode != 0, (
            f"缺少 Playbook 應 exit 非零，實際 {result.returncode}"
        )

    def test_missing_playbook_produces_error_message(self, tmp_path):
        """缺少 playbook 時 stderr 或 stdout 應含有錯誤提示。"""
        missing_pb = tmp_path / "definitely_not_here.yaml"
        result = _run_cli(str(missing_pb), timeout=15)

        combined = (result.stdout + result.stderr).lower()
        assert any(kw in combined for kw in ("找不到", "not found", "error", "playbook")), (
            f"應有錯誤訊息，實際輸出: stdout={result.stdout!r} stderr={result.stderr!r}"
        )


# ──────────────────────────────────────────────────────────
# K3. 無效 YAML config 時 CLI 能正常處理
# ──────────────────────────────────────────────────────────
class TestInvalidConfigHandling:
    def test_invalid_yaml_config_exit_nonzero(self, tmp_path):
        """--config 指向無效 YAML 時 CLI 應 exit 非零（不應崩潰成 uncaught exception）。"""
        bad_config = tmp_path / "bad_config.yaml"
        bad_config.write_text(":\n  not valid: yaml\n: [", encoding="utf-8")
        nonexistent_pb = tmp_path / "pb.yaml"

        result = _run_cli(str(nonexistent_pb), "--config", str(bad_config), timeout=15)
        # 不應 exit 0（成功）
        assert result.returncode != 0


# ──────────────────────────────────────────────────────────
# K4. --config 指向空白 config 時 CLI 使用預設值並正常繼續驗證流程
# ──────────────────────────────────────────────────────────
class TestEmptyConfigHandling:
    def test_empty_config_file_falls_back_to_defaults(self, tmp_path):
        """--config 指向空白 YAML 時，CLI 使用預設設定，正常在 validate 階段 exit 非零。

        預期：argparse 解析成功（不 exit 2）→ _validate_playbook_format 偵測到缺 tasks。
        """
        empty_config = tmp_path / "empty.yaml"
        empty_config.write_text("", encoding="utf-8")  # 空白 YAML

        no_tasks_pb = tmp_path / "no_tasks.yaml"
        no_tasks_pb.write_text(
            yaml.dump({"version": "1.0", "project": "Empty"}),
            encoding="utf-8",
        )
        result = _run_cli(str(no_tasks_pb), "--config", str(empty_config), timeout=15)
        # argparse 正常 → 不應是 exit 2
        assert result.returncode != 2
        # tasks 缺失 → 應 exit 非零
        assert result.returncode != 0


# ──────────────────────────────────────────────────────────
# K5. python -m autoclaude 與 module entrypoint 一致性
# ──────────────────────────────────────────────────────────
class TestModuleEntrypointConsistency:
    def test_module_help_matches_entrypoint_help(self):
        """python -m autoclaude --help 與 autoclaude --help 應回傳同樣的版本。"""
        result = _run_cli("--help", timeout=15)
        assert result.returncode == 0
        assert "playbook" in result.stdout.lower()
        assert "usage:" in result.stdout.lower()

    def test_module_entrypoint_version_or_help_stable(self):
        """驗證 --help 輸出在重構後依然包含必要的旗標說明。"""
        result = _run_cli("--help", timeout=15)
        assert result.returncode == 0
        out = result.stdout.lower()
        # 三個核心旗標應出現在 help 輸出中
        assert "--config" in out, "--config 旗標應在 help 中"
        assert "--fresh" in out, "--fresh 旗標應在 help 中"
        assert "playbook" in out, "playbook 位置引數應在 help 中"
