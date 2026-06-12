"""
AutoClaude 入口點。

用法：
  python -m autoclaude <playbook.yaml> [--config config.yaml] [--fresh]

  --fresh：忽略現有 checkpoint，從第一個步驟重新開始
  --config：指定設定檔（預設 config.yaml；個人化路徑建議用 config.local.yaml）

僅支援 Playbook 模式（YAML 須包含 `tasks:` 陣列）。
"""
from __future__ import annotations
import argparse
import os
import sys
import logging

# SD_Improving_06 W6（T6-6）：_runner_compat.py 已物理刪除，DeprecationWarning
# filter 一併拔除（不再有下游間接 import 觸發噪音）。
# 詳見 docs/08_deployment/SD06_Migration_Guide.md。

import yaml

from .utils.config import load_config
from .utils.logger import setup_logger
from .perception.hotkey_handler import HotkeyHandler
from .decision.minimax_client import MinimaxClient, MinimaxError
from .core.wiring import build_kernel
from .core.services.auto_resume import AutoResumeService
from .infra.adapters.pty_executor import PtyExecutor
from .infra.adapters.shell_evaluator import ShellEvaluator
from .infra.repositories import build_state_repository


def _validate_playbook_format(path: str) -> None:
    """驗證 YAML 是否為合法的 Playbook 格式（含 tasks: 陣列）。"""
    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        raise SystemExit(f"❌ 找不到 Playbook 檔案：{path}")
    except yaml.YAMLError as exc:
        raise SystemExit(f"❌ Playbook YAML 解析失敗：{exc}")

    if not isinstance(raw, dict):
        raise SystemExit(f"❌ Playbook 格式錯誤：根節點必須是物件（dict），實際為 {type(raw).__name__}")
    if "tasks" not in raw:
        raise SystemExit(
            f"❌ {path} 不是合法的 Playbook（缺少 `tasks:` 欄位）。\n"
            "   AutoClaude 0.2+ 已僅支援 Playbook 多步驟模式，請參考 scripts/example_playbook.yaml。"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="AutoClaude — Claude Code Playbook 自動執行引擎")
    parser.add_argument("playbook", help="Playbook YAML 路徑（須含 tasks: 陣列）")
    parser.add_argument("--config", default="config.yaml", help="設定檔路徑 (預設: config.yaml)")
    parser.add_argument(
        "--fresh",
        action="store_true",
        default=False,
        help="忽略現有 checkpoint，從頭開始執行 Playbook",
    )
    args = parser.parse_args()

    _validate_playbook_format(args.playbook)

    cfg = load_config(args.config)
    setup_logger(cfg.log_dir)
    logger = logging.getLogger("autoclaude")

    api_key = os.environ.get("MINIMAX_API_KEY") or cfg.minimax.api_key
    # env 覆蓋（讓本機可把 Brain 指向 localhost OpenAI 相容端點：mock_brain_server / vLLM）
    # 對齊 .env.example 既有的 MINIMAX_BASE_URL / MINIMAX_MODEL 文件（先前僅 config.yaml 生效）。
    base_url = os.environ.get("MINIMAX_BASE_URL") or cfg.minimax.base_url
    model = os.environ.get("MINIMAX_MODEL") or cfg.minimax.model

    try:
        minimax = MinimaxClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=cfg.minimax.timeout_seconds,
        )
    except MinimaxError as exc:
        logger.error("初始化失敗: %s", exc)
        return 1

    hotkey = HotkeyHandler()
    logger.info("Playbook 模式啟動 (fresh=%s) | %s", args.fresh, args.playbook)

    # SD_Improving_05 W6：雙路徑已移除；Kernel 路徑為唯一正式路徑。
    # 舊 PlaybookRunner 直連模式已於 W6 拔除（DeprecationWarning 期已結束）。
    executor = PtyExecutor(cfg)
    evaluator = ShellEvaluator(cfg.playbook)
    state_repo = build_state_repository(cfg.checkpoint_dir, cfg.storage)
    kernel = build_kernel(cfg, executor=executor, evaluator=evaluator,
                          hotkey=hotkey, minimax_client=minimax,
                          state_repository=state_repo)
    service = AutoResumeService(kernel, cfg, state_repository=state_repo)
    result = service.run(args.playbook, fresh=args.fresh)

    logger.info("Playbook 結束 | %s", result)
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
