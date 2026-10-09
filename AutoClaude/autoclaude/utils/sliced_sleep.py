"""分片休眠（PRD §4.5.2）：把一次長 sleep 切成短片，每片之間檢查中斷與時鐘跳躍。"""
# 為什麼不是單次 `time.sleep(wait)`（improving_113）：單次長睡有三個失效方向——
#   ① 機器睡著（依文件，macOS 的 mach_absolute_time、Linux 的 CLOCK_MONOTONIC 皆不計系統睡眠
#      時間；未在本機實際讓機器睡眠驗證）：醒來後還要把剩下的單調鐘時間睡完，實際醒來時刻比
#      絕對目標（scheduled_resume_at／額度 resets_at）晚了整段睡眠時間；
#   ② 睡著期間沒有任何檢查點：呼叫端注入的中斷（stop）無處可收。本函式只提供「片與片之間」的檢查
#      點；中斷事件由呼叫端注入，入口目前是否註冊了全域 hotkey 不在本函式射程內；
#   ③ 睡多久都沒有任何可偵測的痕跡。
# 純函式、零 I/O：時鐘與 sleep 全由呼叫端注入（測試用假時鐘、不真睡）。
#
# 🔴 計入量＝max(請求的片長, 單調鐘增量[, 牆鐘增量 若偵測到跳躍])：
#   · 下限取「請求的片長」＝信任 sleep 契約，同時保證**任何 sleep 替身下必然終止**——
#     既有測試以 `patch("...time.sleep")` 換成立即返回的替身，若只靠量測時鐘，單調鐘一圈
#     只前進數微秒、300 秒的等待要轉極大量圈數＝測試實質掛死；
#   · 取單調鐘增量＝sleep 實際睡過頭（SIGSTOP／Ctrl-Z）時照實扣；
#   · 跳躍時取牆鐘增量＝等待目標是**絕對牆鐘時刻**，機器睡著期間牆鐘照走；向後撥（NTP 校時）
#     不延長等待——早醒的代價是再 halt 一次，多睡的代價是真實閒置時間。
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import NamedTuple

logger = logging.getLogger("autoclaude.utils.sliced_sleep")

__all__ = ["SleepOutcome", "sliced_sleep"]


class SleepOutcome(NamedTuple):
    slept_seconds: float        # 計入的等待秒數（時鐘跳躍的那一片以牆鐘為準，可大於原 wait）
    interrupted: bool           # stop() 為真而提早結束（睡滿則恆為 False）
    clock_jump_detected: bool   # 曾偵測到牆鐘與單調鐘的增量差超過容忍
    remaining_seconds: float    # 未等完的秒數（睡滿或被跳躍吃光＝0.0）


def sliced_sleep(
    wait_seconds: float, slice_seconds: float, clock_jump_tolerance_seconds: float, *,
    wall: Callable[[], float], mono: Callable[[], float],
    sleep: Callable[[float], object], stop: Callable[[], bool],
) -> SleepOutcome:
    """等待 `wait_seconds` 秒；每片最長 `slice_seconds`，片與片之間檢查 `stop()`。"""
    if slice_seconds <= 0:
        raise ValueError(f"slice_seconds 必須 > 0（收到 {slice_seconds!r}）：0 會原地空轉")
    remaining, slept, jumped = max(0.0, float(wait_seconds)), 0.0, False
    while remaining > 0 and not stop():
        chunk = min(slice_seconds, remaining)
        w0, m0 = wall(), mono()
        sleep(chunk)
        dw, dm = wall() - w0, mono() - m0
        jump = abs(dw - dm) > clock_jump_tolerance_seconds
        if jump:
            # 訊息須與下一行 step 的動作一致：牆鐘倒退＝忽略牆鐘，只有多走才以牆鐘重算
            logger.warning("sliced_sleep | 偵測到時鐘跳躍（牆鐘 %+.1fs／單調鐘 %+.1fs，容忍 %.1fs）"
                           "⇒ %s", dw, dm, clock_jump_tolerance_seconds,
                           "忽略牆鐘倒退、以單調鐘續睡" if dw < dm else "剩餘改以牆鐘重算")
        step = max(chunk, dm, dw if jump else 0.0)
        slept, remaining, jumped = slept + step, remaining - step, jumped or jump
    return SleepOutcome(slept, remaining > 0, jumped, max(0.0, remaining))
