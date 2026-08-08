"""排程恢復倒數的唯一時鐘（R81／HLM-S1-02）。"""
# 為什麼要有這個模組：`scheduled_resume_at` 的倒數邏輯原本有**三個家**——
#   · core/services/auto_resume.py::seconds_until_resume（Kernel 路徑真正在用的那個）
#   · infra/repositories/file_state_repository.py::FileStateRepository.seconds_until_resume
#   · utils/checkpoint_manager.py::CheckpointManager.seconds_until_resume（boot_helper 在用）
# 三份都寫死 `resume_at - datetime.now()`（naive now），而**產出端不是同一種時間**：
#   · FileStateRepository / InMemoryStateRepository → `datetime.now()`（naive）
#   · PgStateRepository                            → `datetime.now(UTC)`（aware）
# ⇒ 切到 Pg 後端時，aware − naive 直接拋 TypeError，被消費端的 `except` 吞掉、
#   回退 0.0。`token_guard.resume_delay_minutes: 30` 於是變成 **0 秒**：
#   撞到 90% → 立刻原地重試 → 再撞 → …，`max_auto_resumes` 有幾次就連燒幾次。
#
# 失效方向是最壞的那一邊（不是「不續跑」，是「不等就續跑」），而且完全靜默：
# 只有一行 warning，rc 全綠。當回合實測（Process A 存、Process B 全新行程讀）：
#   · File 形態 `2026-08-08T21:51:00`        → 1799.5
#   · Pg   形態 `2026-08-08T13:51:00+00:00`  → 0.0
#
# 修的是消費端不是產出端：產出端帶 tzinfo 才是對的（跨 DST／跨機器都無歧義）。
# 判準是「跟著輸入走」——輸入 aware 就用 aware 的 now、輸入 naive 就用 naive 的
# now，兩種形態都算得出正確秒數，也不會逼任何一個後端改變已落盤的字串格式。
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger("autoclaude.utils.resume_clock")

__all__ = ["seconds_until"]


def seconds_until(scheduled_resume_at: object | None) -> float:
    """距 `scheduled_resume_at` 的剩餘秒數；未設定／已過期／無法解析皆回 0.0。"""
    if not scheduled_resume_at:
        return 0.0
    try:
        resume_at = datetime.fromisoformat(scheduled_resume_at)  # type: ignore[arg-type]
        # tzinfo 為 None 時 `datetime.now(None)` 等同 `datetime.now()`（naive），
        # 所以這一行同時涵蓋兩種形態，不需要分支。
        return max(0.0, (resume_at - datetime.now(resume_at.tzinfo)).total_seconds())
    except (ValueError, TypeError) as exc:
        logger.warning(
            "seconds_until | 無法解析 scheduled_resume_at=%r: %s",
            scheduled_resume_at, exc,
        )
        return 0.0
