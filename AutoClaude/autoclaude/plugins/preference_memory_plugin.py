"""PreferenceMemoryPlugin — 使用者偏好注入 correction prompt（F-C1 / ADR-AGT-003 L3）。

訂閱 phase：
  - PRE_CORRECTION → 回傳 PromptInjectionResult（`## 使用者偏好` 區段），
    由 Kernel 收集後以 preferences_section 傳入 IBrain.decide_correction。

偏好為唯讀注入（Brain 輸出不得自動回寫 L3，ADR-AGT-003 §2 原則 3）；
區段上限 10 鍵（ADR-AGT-003 §4 風險緩解，防 prompt 膨脹）。

IPreferenceStore 實例由 wiring 注入（plugin 不直接 import infra）。
"""
from __future__ import annotations

from typing import Any

from ..core.hookspec import HookContext, KernelPhase, PromptInjectionResult
from ..core.ports.preference_store import IPreferenceStore

_MAX_KEYS = 10


class PreferenceMemoryPlugin:
    """L3 偏好記憶 Plugin（US-AGT-003）。"""

    PRIORITY = 50

    def __init__(self, preference_store: IPreferenceStore | None = None):
        self._store = preference_store

    def name(self) -> str:
        return "preference_memory"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [KernelPhase.PRE_CORRECTION]

    def on_event(self, ctx: HookContext) -> Any | None:
        if ctx.phase != KernelPhase.PRE_CORRECTION or self._store is None:
            return None
        section = self._build_section(ctx)
        if not section:
            return None
        return PromptInjectionResult(
            contributor=self.name(), prefix=section, position="top",
        )

    # ──────────────────────────────────────────────
    def _build_section(self, ctx: HookContext) -> str:
        """global + 該 playbook scope 合併（playbook 覆寫），上限 10 鍵。"""
        try:
            prefs = dict(self._store.list("global"))
            project = getattr(ctx.playbook, "project", None)
            if project:
                prefs.update(self._store.list(f"playbook:{project}"))
        except Exception:
            return ""  # 偏好讀取失敗不阻斷 correction 主流程
        if not prefs:
            return ""
        # 超過上限取最後 N 鍵（insertion order，後寫入者較新）
        items = list(prefs.items())[-_MAX_KEYS:]
        lines = "\n".join(f"- {k}: {v}" for k, v in items)
        return f"## 使用者偏好\n{lines}\n\n"


__all__ = ["PreferenceMemoryPlugin"]
