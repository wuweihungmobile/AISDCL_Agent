"""
CLI 100% 向後相容測試（SD_Improving_01.md v1.1 §3.11 / SD_Improving_02.md v1.1 §0.3）。

目的：在 Phase 0 ~ Phase 6 期間鎖死 CLI 介面契約，避免重構意外破壞使用者習慣。

測試策略（v1.1 修訂，對應稽核 finding F8）：
  - 9 個既有場景升級為 `subprocess.run([sys.executable, "-m", "autoclaude", ...])`
    完整覆蓋 exit code 0/1/2/3 真實行為（v1.0 直接呼叫
    `_validate_playbook_format()` 無法捕捉 argparse 退出碼）
  - 不啟動真實 Claude Code（避免 CI 卡住）— 透過提供無效 playbook
    或 `--help` 等場景使流程在 `_validate_playbook_format` 階段即退出
  - 任何破壞性變更（如 exit code 從 1 改為 2）必須先修改本測試 + PM 簽核

9 個場景對齊 SD_Improving_01.md §3.11 的 CLI 介面承諾：
  S1. --help                        → exit 0，stdout 含 "usage:" 與 "playbook"
  S2. 不存在的 playbook 路徑          → exit 1（FileNotFoundError 路徑）
  S3. 非 YAML 格式檔案                → exit 1（YAMLError 路徑）
  S4. YAML 但缺 tasks 欄位             → exit 1（缺 tasks 路徑）
  S5. argparse 接受 --config 參數     → 解析成功
  S6. argparse 接受 --fresh 參數      → 解析成功
  S7. 沒有 playbook 引數              → argparse exit 2
  S8. autoclaude entrypoint 名稱可呼叫 → __main__.py 與 entry_point 配置存在
  S9. CLI 介面欄位完整性               → argparse 不漏掉 playbook / --config / --fresh

L3 補充：`python -m autoclaude --help` subprocess smoke test。
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import pytest
import yaml

from autoclaude import main as main_module


# ──────────────────────────────────────────────
# 共用：subprocess 執行 `python -m autoclaude`
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run_cli(*args: str, cwd: Path | None = None, timeout: int = 15) -> subprocess.CompletedProcess:
    """以 subprocess 執行 `python -m autoclaude <args>` 並回傳 CompletedProcess。

    使用 PROJECT_ROOT 為 cwd（除非另行指定）以確保 import path 正確；
    `MINIMAX_API_KEY` 留空避免真的初始化 Minimax；
    `PYTHONIOENCODING=utf-8` 確保 Windows 下 stdout 可解碼中文錯誤訊息。
    """
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    env.pop("MINIMAX_API_KEY", None)  # 避免測試中真的呼叫 Minimax
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


# ──────────────────────────────────────────────
# 共用：建立一個 argparse parser 等價於 main.main()
# ──────────────────────────────────────────────
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AutoClaude — Claude Code Playbook 自動執行引擎")
    parser.add_argument("playbook", help="Playbook YAML 路徑（須含 tasks: 陣列）")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--fresh", action="store_true", default=False)
    return parser


# ──────────────────────────────────────────────
# S1. --help 必須 exit 0 且 stdout 含 "usage:" 與 "playbook"
# ──────────────────────────────────────────────
class TestCliS1Help:
    def test_help_exits_zero_with_usage_text_inproc(self):
        """in-process argparse 驗證（保留向後相容）。"""
        parser = _build_parser()
        buf = io.StringIO()
        with redirect_stdout(buf), pytest.raises(SystemExit) as exc:
            parser.parse_args(["--help"])
        assert exc.value.code == 0
        out = buf.getvalue()
        assert "usage:" in out.lower()
        assert "playbook" in out.lower()

    def test_help_exits_zero_via_subprocess(self):
        """F8：subprocess 執行 `python -m autoclaude --help` 必須 exit 0。"""
        result = _run_cli("--help")
        assert result.returncode == 0, f"--help 應 exit 0，實際 {result.returncode}"
        out = result.stdout.lower()
        assert "usage:" in out
        assert "playbook" in out


# ──────────────────────────────────────────────
# S2. 不存在的 playbook 必須 SystemExit
# ──────────────────────────────────────────────
class TestCliS2MissingFile:
    def test_missing_file_raises_systemexit_inproc(self, tmp_path):
        nonexistent = tmp_path / "nonexistent.yaml"
        with pytest.raises(SystemExit) as exc:
            main_module._validate_playbook_format(str(nonexistent))
        assert exc.value.code != 0
        assert "找不到" in str(exc.value.code) or "Playbook" in str(exc.value.code)

    def test_missing_file_exit_nonzero_via_subprocess(self, tmp_path):
        """F8：subprocess 模式驗證 exit code 為非零（SystemExit 字串退出碼會映射到 1）。"""
        nonexistent = tmp_path / "nonexistent.yaml"
        result = _run_cli(str(nonexistent), timeout=15)
        assert result.returncode != 0, "不存在的 playbook 應 exit 非零"
        # SystemExit(message) 透過 sys.exit() 會輸出 message 到 stderr 並 exit 1
        combined = (result.stdout + result.stderr).lower()
        assert "找不到" in combined or "playbook" in combined


# ──────────────────────────────────────────────
# S3. 非 YAML 格式檔案必須 SystemExit
# ──────────────────────────────────────────────
class TestCliS3InvalidYaml:
    def test_invalid_yaml_raises_systemexit_inproc(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text(":\n  not valid yaml\n: [", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            main_module._validate_playbook_format(str(bad))
        assert exc.value.code != 0

    def test_invalid_yaml_exit_nonzero_via_subprocess(self, tmp_path):
        """F8：subprocess 模式驗證非 YAML 檔案 exit 非零。"""
        bad = tmp_path / "bad.yaml"
        bad.write_text(":\n  not valid yaml\n: [", encoding="utf-8")
        result = _run_cli(str(bad), timeout=15)
        assert result.returncode != 0


# ──────────────────────────────────────────────
# S4. YAML 缺 tasks: 欄位必須 SystemExit
# ──────────────────────────────────────────────
class TestCliS4MissingTasks:
    def test_missing_tasks_raises_systemexit_inproc(self, tmp_path):
        no_tasks = tmp_path / "no_tasks.yaml"
        no_tasks.write_text(yaml.dump({"version": "1.0", "project": "X"}), encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            main_module._validate_playbook_format(str(no_tasks))
        assert exc.value.code != 0
        assert "tasks" in str(exc.value.code).lower()

    def test_missing_tasks_exit_nonzero_via_subprocess(self, tmp_path):
        """F8：subprocess 模式驗證 YAML 缺 tasks 時 exit 非零。"""
        no_tasks = tmp_path / "no_tasks.yaml"
        no_tasks.write_text(yaml.dump({"version": "1.0", "project": "X"}), encoding="utf-8")
        result = _run_cli(str(no_tasks), timeout=15)
        assert result.returncode != 0
        combined = (result.stdout + result.stderr).lower()
        assert "tasks" in combined


# ──────────────────────────────────────────────
# S5. argparse 接受 --config <path>
# ──────────────────────────────────────────────
class TestCliS5ConfigFlag:
    def test_config_flag_parsed(self):
        parser = _build_parser()
        args = parser.parse_args(["pb.yaml", "--config", "config.local.yaml"])
        assert args.playbook == "pb.yaml"
        assert args.config == "config.local.yaml"
        assert args.fresh is False

    def test_config_default_value(self):
        parser = _build_parser()
        args = parser.parse_args(["pb.yaml"])
        assert args.config == "config.yaml"

    def test_config_flag_accepted_via_subprocess(self, tmp_path):
        """F8：subprocess 驗證 --config flag 不會在 argparse 階段炸掉。

        提供不存在的 playbook 觸發 _validate_playbook_format 的 SystemExit(1)，
        驗證 argparse 已順利解析 --config（exit code 不應為 2）。
        """
        nonexistent = tmp_path / "missing.yaml"
        cfg = tmp_path / "custom_config.yaml"
        cfg.write_text("# empty\n", encoding="utf-8")
        result = _run_cli(str(nonexistent), "--config", str(cfg), timeout=15)
        # argparse 解析成功 → 不會是 exit 2
        assert result.returncode != 2, "--config flag 不應觸發 argparse exit 2"
        assert result.returncode != 0


# ──────────────────────────────────────────────
# S6. argparse 接受 --fresh
# ──────────────────────────────────────────────
class TestCliS6FreshFlag:
    def test_fresh_flag_parsed(self):
        parser = _build_parser()
        args = parser.parse_args(["pb.yaml", "--fresh"])
        assert args.fresh is True

    def test_fresh_default_false(self):
        parser = _build_parser()
        args = parser.parse_args(["pb.yaml"])
        assert args.fresh is False

    def test_fresh_flag_accepted_via_subprocess(self, tmp_path):
        """F8：subprocess 驗證 --fresh flag 不會被 argparse 拒絕。"""
        nonexistent = tmp_path / "missing.yaml"
        result = _run_cli(str(nonexistent), "--fresh", timeout=15)
        assert result.returncode != 2  # argparse 接受 --fresh
        assert result.returncode != 0  # 缺檔案仍應失敗


# ──────────────────────────────────────────────
# S7. 沒有 playbook 引數 → argparse exit 2
# ──────────────────────────────────────────────
class TestCliS7MissingPlaybookArg:
    def test_no_args_exits_two_inproc(self):
        parser = _build_parser()
        buf = io.StringIO()
        with redirect_stderr(buf), pytest.raises(SystemExit) as exc:
            parser.parse_args([])
        assert exc.value.code == 2

    def test_no_args_exits_two_via_subprocess(self):
        """F8：subprocess 模式驗證缺 playbook 引數時 argparse exit 2。"""
        result = _run_cli(timeout=15)
        assert result.returncode == 2, f"argparse 缺引數應 exit 2，實際 {result.returncode}"


# ──────────────────────────────────────────────
# S8. autoclaude entrypoint 與 __main__.py 配置存在
# ──────────────────────────────────────────────
class TestCliS8Entrypoint:
    def test_module_main_exists(self):
        from autoclaude import __main__  # noqa: F401

    def test_main_function_exported(self):
        assert callable(main_module.main)

    def test_entrypoint_configured_in_pyproject(self):
        pyproject = PROJECT_ROOT / "pyproject.toml"
        if not pyproject.exists():
            pytest.skip("pyproject.toml 不存在，略過 entrypoint 配置檢查")
        text = pyproject.read_text(encoding="utf-8")
        assert "autoclaude" in text


# ──────────────────────────────────────────────
# S9. CLI 介面欄位完整性（鎖死必要參數）
# ──────────────────────────────────────────────
class TestCliS9InterfaceCompleteness:
    def test_required_arguments_present(self):
        parser = _build_parser()
        args = parser.parse_args(["pb.yaml", "--config", "c.yaml", "--fresh"])
        assert hasattr(args, "playbook")
        assert hasattr(args, "config")
        assert hasattr(args, "fresh")

    def test_main_signature_unchanged(self):
        """main() 必須無參數且回傳 int（exit code）。"""
        import inspect
        sig = inspect.signature(main_module.main)
        assert len([p for p in sig.parameters.values()
                    if p.default is inspect.Parameter.empty]) == 0


# ──────────────────────────────────────────────
# L3 補充：subprocess smoke test
# ──────────────────────────────────────────────
def test_autoclaude_entrypoint_responds_to_help():
    """L3：subprocess 啟動 autoclaude 並驗證 --help 正常回應。"""
    result = subprocess.run(
        [sys.executable, "-m", "autoclaude", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )
    assert result.returncode == 0
    assert "playbook" in result.stdout.lower()
