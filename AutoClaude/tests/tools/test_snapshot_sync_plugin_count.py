"""tools/snapshot_sync.py — count_active_plugins() 跨環境決定性單元測試。

對應 SD_09 R56 zero-trust audit 揪修：
  CI claude-md-budget job 僅 setup-python（不 pip install autoclaude 相依）→
  `from autoclaude.core.wiring import _build_plugin_set` 拋例外 → 走 fallback。
  修復前 fallback 回 len(_REGISTER_ORDER)（含條件式 hotkey），但本地有相依的
  import-path 少 1 → snapshot --check 在 Linux 報 DRIFT、Windows 報 OK（平台漂移）。

  修復後 fallback 排除 _CONDITIONAL_PLUGINS（hotkey）→ 兩路徑數字一致，snapshot 可重現。

紀律 #4（驗證鏡子自身要被驗證）：本測試含「強制走 fallback」與「adversarial 未排除
條件式則多 1」兩面，確保排除邏輯真實有效。

計數基線（AutoSDD_improving_01 W7 翻牌）：sdd_governance plugin（PRIORITY=45）加入
_REGISTER_ORDER → 靜態 15（含 hotkey）/ active 14（不含條件式 hotkey）。
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import snapshot_sync  # noqa: E402

# 單一 pin 點：新增/移除 plugin 時只改這兩個常數（與 wiring._REGISTER_ORDER 同步）
_STATIC_COUNT = 19   # len(_REGISTER_ORDER)，含條件式 hotkey（AutoSDD_improving_60 +1：translation_learner）
_ACTIVE_COUNT = 18   # 排除 _CONDITIONAL_PLUGINS（hotkey）


class TestCountActivePluginsDeterminism:
    """count_active_plugins() 必須跨「有/無相依」環境回相同 active 數。"""

    def test_import_path_returns_active_count(self) -> None:
        """本地測試環境有 autoclaude 相依 → import-path 動態計算（不含條件式 hotkey）。"""
        assert snapshot_sync.count_active_plugins() == _ACTIVE_COUNT

    def test_fallback_path_matches_import_path(self, monkeypatch) -> None:
        """強制 import 失敗（模擬 CI 無相依 lint job）→ fallback 必須回相同數。"""
        # sys.modules[name] = None 使 `import autoclaude.core.wiring` 拋 ImportError
        monkeypatch.setitem(sys.modules, "autoclaude.core.wiring", None)
        assert snapshot_sync.count_active_plugins() == _ACTIVE_COUNT

    def test_fallback_excludes_conditional_plugins(self) -> None:
        """fallback 排除 _CONDITIONAL_PLUGINS（hotkey）；靜態 _REGISTER_ORDER 全量。"""
        static = snapshot_sync.extract_register_order()
        assert len(static) == _STATIC_COUNT, (
            f"靜態 _REGISTER_ORDER 應含 {_STATIC_COUNT} 項（含 hotkey）")
        assert "hotkey" in static
        assert "sdd_governance" in static  # AutoSDD W7 新增
        fallback = sum(1 for n in static if n not in snapshot_sync._CONDITIONAL_PLUGINS)
        assert fallback == _ACTIVE_COUNT

    def test_adversarial_without_exclusion_would_drift(self) -> None:
        """反例：若 fallback 不排除條件式 plugin → 多 1 → 必觸發 DRIFT（證排除有必要）。"""
        static = snapshot_sync.extract_register_order()
        naive = len(static)  # 修復前的錯誤算法
        assert naive == _STATIC_COUNT
        assert naive != snapshot_sync.count_active_plugins(), (
            f"未排除條件式 hotkey 的 naive 算法（{_STATIC_COUNT}）必須 ≠ 真實 active"
            f"（{_ACTIVE_COUNT}），否則本測試無法證明排除邏輯有效"
        )
