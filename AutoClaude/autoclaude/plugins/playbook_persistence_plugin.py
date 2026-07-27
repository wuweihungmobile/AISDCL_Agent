"""PlaybookPersistencePlugin — Gap-013-C：動態突變後持久化（ON_EVOLUTION_APPLY phase）。

SD_Improving_05 W4-3：從 `_runner_internals._persist_mutated_playbook` +
`playbook_runner.py` 的 `.mutated.yaml` 載入清理邏輯搬移。

職責：
  - **公開 API**：
    - ``persist_mutated_playbook(playbook, playbook_path)``：寫入 .mutated.yaml
    - ``load_mutated_if_exists(playbook_path, checkpoint_exists=True)``：恢復突變狀態
    - ``cleanup_mutated_for_paths(paths)``：成功後清除 .mutated.yaml
  - **phase 訂閱**：訂閱 ``ON_EVOLUTION_APPLY`` 作為 W4 過渡訂閱位
    - 目前為 NO-OP（logger.info audit），保留 phase 訂閱以便 W6 完整下沉

設計原則：
  - 不依賴 infra 層；I/O 透過 `pathlib` + `yaml`（標準函式庫）
  - 失敗（OSError / yaml dump 失敗）僅 logger.warning，不拋例外
  - LOC 預算 ≤ 130 行
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from pathlib import Path

import yaml

from ..core.hookspec import (
    HookContext,
    KernelPhase,
    PersistenceResult,
)
from ..models.playbook import Playbook
from ..utils.logger import _sanitize_log_filename

logger = logging.getLogger(__name__)


class PlaybookPersistencePlugin:
    """SD_05 W4-3：突變後 Playbook 持久化 + .mutated.yaml 生命週期管理。"""

    PRIORITY = 40

    def __init__(
        self,
        checkpoint_dir: str | Callable[[], str] = "checkpoints",
    ):
        """checkpoint_dir 可為 str 或 callable resolver。

        SD_05 W4 三方審查修復：runner 注入時可傳 ``lambda: self._cfg.checkpoint_dir``，
        確保 cfg.checkpoint_dir 動態變動（測試 / 熱重載）時 plugin 同步生效。
        """
        if callable(checkpoint_dir):
            self._dir_resolver: Callable[[], str] = checkpoint_dir
        else:
            _dir_value = checkpoint_dir
            self._dir_resolver = lambda: _dir_value

    @property
    def _checkpoint_dir(self) -> Path:
        return Path(self._dir_resolver())

    def name(self) -> str:
        return "playbook_persistence"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [KernelPhase.ON_EVOLUTION_APPLY]

    def on_event(self, ctx: HookContext) -> PersistenceResult | None:
        """ON_EVOLUTION_APPLY NO-OP 過渡訂閱位（W4 過渡；W6 完整下沉）。

        SD_05 W4 三方審查 SA-M4 / Arch-M2 修復：為對齊 PHASE_RESULT_CONTRACT
        （ON_EVOLUTION_APPLY 要 {MutationApplyResult, PersistenceResult}），
        本訂閱位回傳 ``PersistenceResult(succeeded=True, kind="no_op")``，
        與 W3 EvolutionPlugin 過渡訂閱位風格一致（noop sentinel）。

        非訂閱 phase 直接 return None（短路守衛，對齊 fast_path 風格 SD-m8）。
        """
        if ctx.phase is not KernelPhase.ON_EVOLUTION_APPLY:
            return None
        logger.info(
            "PlaybookPersistencePlugin | ON_EVOLUTION_APPLY 訂閱位（W4 過渡；"
            "W6 將下沉 _persist_mutated_playbook）",
        )
        return PersistenceResult(
            contributor=self.name(), path="", succeeded=True, kind="no_op",
        )

    # ──────────────────────────────────────────────────────────────────
    # 公開 API（mixin / orchestrator 呼叫；W6 拔除後直接由 phase payload 觸發）
    # ──────────────────────────────────────────────────────────────────

    def _mutated_path_for(self, playbook_path: str) -> Path:
        # R56 修正（DEF-101-442）：本方法是 checkpoint_dir 檔名家族第三個 sibling，
        # 另兩個已收斂淨化（file_state_repository._path() DEF-101-384 / R47、
        # checkpoint_manager.checkpoint_path() DEF-101-390 / R48），本支此前裸用
        # Path().stem。playbook_path 是使用者提供的自由格式路徑，stem 可能是 Windows
        # 保留裝置名（CON/AUX/NUL…，帶副檔名同樣保留）或含 <>:"|?* 禁用字元／尾隨空白
        # 與句點 → Windows 上 open("w") 直接 OSError，而 persist_mutated_playbook() 的
        # except 只 logger.warning 不拋，突變後 playbook 會靜默遺失（演化狀態不可復原）。
        # 委派 SSOT `_sanitize_log_filename`，讀（load）／寫（persist）／清（cleanup）
        # 三路皆經本方法，故單點修改即三處一致，不會產生新的讀寫檔名分歧。
        stem = _sanitize_log_filename(Path(playbook_path).stem)
        return self._checkpoint_dir / f"{stem}.mutated.yaml"

    def persist_mutated_playbook(
        self, playbook: Playbook, playbook_path: str,
    ) -> Path | None:
        """寫入 ``<stem>.mutated.yaml``。回傳寫入路徑；失敗回 None。"""
        mutated_path = self._mutated_path_for(playbook_path)
        try:
            mutated_path.parent.mkdir(parents=True, exist_ok=True)
            with mutated_path.open("w", encoding="utf-8") as f:
                yaml.dump(
                    playbook.model_dump(exclude_none=True),
                    f, allow_unicode=True, default_flow_style=False,
                )
            logger.debug("Gap-013-C | 突變後持久化: %s", mutated_path)
            return mutated_path
        except Exception as exc:
            logger.warning("Gap-013-C | 突變持久化失敗: %s", exc)
            return None

    def load_mutated_if_exists(
        self, playbook_path: str, *, checkpoint_exists: bool = True,
    ) -> Path | None:
        """偵測 ``<stem>.mutated.yaml``；若存在且有 checkpoint，回傳路徑。

        若 ``checkpoint_exists`` 為 False（fresh 模式或未排程 resume），即使
        ``mutated.yaml`` 存在也回傳 None（避免誤用過期突變狀態）。
        """
        mutated_path = self._mutated_path_for(playbook_path)
        if not mutated_path.exists():
            return None
        if not checkpoint_exists:
            return None
        logger.info("Gap-013-C | 偵測到 .mutated.yaml: %s", mutated_path)
        return mutated_path

    def cleanup_mutated_for_paths(
        self, paths: Iterable[str | None],
    ) -> list[Path]:
        """對提供的每個 playbook_path，移除其對應 ``.mutated.yaml``（若存在）。

        回傳實際移除的檔案路徑清單。OSError 視為靜默通過（與原 mixin 行為一致）。
        """
        removed: list[Path] = []
        for p in paths:
            if not p:
                continue
            mutated_path = self._mutated_path_for(p)
            if not mutated_path.exists():
                continue
            try:
                mutated_path.unlink()
                removed.append(mutated_path)
                logger.debug("Gap-013-C | 清理 .mutated.yaml: %s", mutated_path)
            except OSError as exc:
                logger.debug("Gap-013-C | 清理失敗（忽略）: %s err=%s", mutated_path, exc)
        return removed
