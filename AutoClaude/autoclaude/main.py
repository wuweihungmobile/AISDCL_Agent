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
import logging
import os
import sys

# SD_Improving_06 W6（T6-6）：_runner_compat.py 已物理刪除，DeprecationWarning
# filter 一併拔除（不再有下游間接 import 觸發噪音）。
# 詳見 docs/08_deployment/SD06_Migration_Guide.md。
import yaml

from .core.services.auto_resume import AutoResumeService
from .core.wiring import build_kernel, build_quota_meter
from .decision.minimax_client import MinimaxClient, MinimaxError
from .infra.adapters.minimax_brain import MinimaxBrainAdapter
from .infra.adapters.pty_executor import PtyExecutor
from .infra.adapters.shell_evaluator import ShellEvaluator
from .infra.repositories import build_state_repository
from .perception.hotkey_handler import HotkeyHandler
from .utils.config import load_config
from .utils.logger import setup_logger


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
        raise SystemExit(f"❌ Playbook 格式錯誤：根節點必須是物件（dict），實際為 {type(raw).__name__}")  # noqa: E501
    if "tasks" not in raw:
        raise SystemExit(
            f"❌ {path} 不是合法的 Playbook（缺少 `tasks:` 欄位）。\n"
            "   AutoClaude 0.2+ 已僅支援 Playbook 多步驟模式，請參考 scripts/example_playbook.yaml。"  # noqa: E501
        )


def build_executor(cfg, hotkey=None, logger=None):
    """依 cfg.executor.backend 建構執行器（pty 預設 / sdk opt-in）。

    improving_71 DEF-71-001：原 main() 內 `PtyExecutor(cfg)` 接線錯誤——PtyExecutor 簽章
    為 (claude_cfg, loop_cfg, log_dir, hotkey)，傳整個 AppConfig 當 claude_cfg 又缺 loop_cfg
    → 預設 pty 經 CLI 必崩（TypeError）；因 executor 建構未被任何測試覆蓋而長期潛伏（測試
    皆直接 `PtyExecutor(ClaudeConfig(), LoopConfig())`）。抽為可測單元並接線正確，由
    tests/test_main_build_executor.py 守門。
    """
    if cfg.executor.backend == "sdk":
        from .infra.adapters.sdk_executor_adapter import (
            SdkExecutorAdapter,
            build_tool_allowlist_predicate,
        )

        # improving_69 W-69-2：can_use_tool production 接線（None→permission_mode 守門）。
        allowlist = cfg.executor.sdk_tool_allowlist
        predicate = (
            build_tool_allowlist_predicate(allowlist) if allowlist is not None else None
        )
        if logger is not None:
            logger.info(
                "執行器後端：Claude Agent SDK（permission_mode=%s, tool_allowlist=%s）",
                cfg.executor.permission_mode,
                "None(permission_mode 守門)" if allowlist is None else allowlist,
            )
        return SdkExecutorAdapter(cfg, can_use_tool=predicate)
    return PtyExecutor(cfg.claude, cfg.loop, log_dir=cfg.log_dir, hotkey=hotkey)


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

    # R85 AC-(b)：Brain 是**選配**能力，缺金鑰不得阻斷整支 playbook。
    # 舊行為無條件建 MinimaxClient，空金鑰即 raise → 沒有 Minimax 帳號的人一步都跑不了
    # 任何 playbook（連 enable_kernel_brain=False 這個「本來就不用 Brain」的預設組態也一樣）。
    # 新行為分兩路，且**顯式要求 Brain 時仍 fail-closed**（不靜默降級）：
    #   有金鑰            → 照舊建 client
    #   無金鑰 + 要 Brain → rc=1 停機（要什麼就必須拿到什麼）
    #   無金鑰 + 不要 Brain → minimax=None，warn 一次後照常跑
    # 下游三個消費者皆已具 None 守衛：GoalSynthesisPlugin（:55/:157）、
    # EvolutionPlugin（:213）、wiring 簽名本身即 `Any | None = None`。
    minimax = None
    if api_key:
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
    elif cfg.minimax.enable_kernel_brain:
        logger.error(
            "初始化失敗: enable_kernel_brain=True 但未設定 MINIMAX_API_KEY／config.minimax.api_key"
        )
        return 1
    else:
        logger.warning(
            "未設定 MINIMAX_API_KEY：Brain 相關能力（步驟 correction／goal synthesis／"
            "自演化提案）本次停用，playbook 仍會照常執行"
        )

    hotkey = HotkeyHandler()
    logger.info("Playbook 模式啟動 (fresh=%s) | %s", args.fresh, args.playbook)

    # SD_Improving_05 W6：雙路徑已移除；Kernel 路徑為唯一正式路徑。
    # 舊 PlaybookRunner 直連模式已於 W6 拔除（DeprecationWarning 期已結束）。
    # improving_68 W-68-3：執行器後端可切換（預設 pty → 零行為變更；sdk 為 opt-in）。
    # improving_71 DEF-71-001：建構抽至可測的 build_executor()（修 PtyExecutor 接線崩潰）。
    executor = build_executor(cfg, hotkey=hotkey, logger=logger)
    evaluator = ShellEvaluator(cfg.playbook)
    state_repo = build_state_repository(cfg.checkpoint_dir, cfg.storage)
    # DEF-01-008：flag-gated brain 注入。預設 enable_kernel_brain=False → brain=None，
    # 維持既有 production 行為（無 Minimax 逐步 correction、SddGovernance escalation 諮詢
    # 不啟用），零退化。顯式啟用後死碼轉為可達能力（行為差異見 improving_03 §2.1）。
    brain = MinimaxBrainAdapter(minimax) if cfg.minimax.enable_kernel_brain else None
    kernel = build_kernel(cfg, executor=executor, evaluator=evaluator,
                          hotkey=hotkey, minimax_client=minimax, brain=brain,
                          state_repository=state_repo)
    # R82（ACQ-05）：注入額度水位量測器，讓 halt 後的等待時間由**觀測到的 resets_at** 決定，
    # 而不是寫死的 resume_delay_minutes（實測額度視窗 min 0.5 分／max 253 分，30 分沒有一段對）。
    service = AutoResumeService(kernel, cfg, state_repository=state_repo,
                                quota_meter=build_quota_meter())
    result = service.run(args.playbook, fresh=args.fresh)

    logger.info("Playbook 結束 | %s", result)
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
