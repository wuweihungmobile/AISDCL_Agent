# 可用空間閘（PRD §6.2 R-6.2-3 ／ §6.1 不變式 13）。
#
# 🔴 為什麼是 bytes 對 bytes、不是百分比（PRD R-6.2-3 ② 逐字）：百分比門檻在小容量磁碟上
#    太鬆（500GB 碟的 1% 是 5GB、64GB 碟的 1% 是 640MB，同一個「1%」兩個意思），在大容量
#    碟上又太緊。要比的是「本次凍結預估要寫多少 bytes」對「現在還有多少 bytes」。
#
# 🔴 為什麼這一支住 utils/ 而不是跟自檢或救援其中一邊同居：它有**兩個**呼叫端——開機自檢
#    那一次，與寫 patch 前那一次（PRD R-6.2-3 ①：順序錯了，這道檢查在它唯一要治的情境下
#    根本不會被跑到）。放進其中一邊就等於另一邊得再寫一份。
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("autoclaude.utils.disk_space")

# 常數餘裕（PRD R-6.2-3 ②「＋一個常數餘裕」）。8 MiB：一次凍結除了 patch 還會寫
# state.json ＋ 側檔 ＋ log；餘裕小於這些的總和時，「剛好夠」與「剛好不夠」無法分辨。
DEFAULT_MARGIN_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class SpaceVerdict:
    ok: bool
    free_bytes: int
    required_bytes: int          # estimate + margin
    estimate_bytes: int
    margin_bytes: int

    @property
    def shortfall_bytes(self) -> int:
        return max(0, self.required_bytes - self.free_bytes)


class InsufficientSpaceError(OSError):
    """可用空間不足以完成本次寫入。刻意繼承 OSError——它就是一種 I/O 條件。"""


def free_bytes(target: str | Path) -> int:
    # 量的是「target 所在的那個檔案系統」。target 還不存在時往上找第一個存在的祖先：
    # `shutil.disk_usage` 對不存在的路徑會 FileNotFoundError，而「目錄還沒建」在
    # 啟動自檢那一刻是**正常**狀態，不該被讀成「量不到」。
    p = Path(target).resolve()
    while not p.exists() and p != p.parent:
        p = p.parent
    return shutil.disk_usage(str(p)).free


def check_space(target: str | Path, estimate_bytes: int, *,
                margin_bytes: int = DEFAULT_MARGIN_BYTES) -> SpaceVerdict:
    # 只回判決、不拋、不動作。要 fail-loud 的呼叫端自己 raise（見 require_space）。
    free = free_bytes(target)
    required = max(0, int(estimate_bytes)) + max(0, int(margin_bytes))
    return SpaceVerdict(ok=free >= required, free_bytes=free,
                        required_bytes=required,
                        estimate_bytes=max(0, int(estimate_bytes)),
                        margin_bytes=max(0, int(margin_bytes)))


def require_space(target: str | Path, estimate_bytes: int, *,
                  margin_bytes: int = DEFAULT_MARGIN_BYTES) -> SpaceVerdict:
    v = check_space(target, estimate_bytes, margin_bytes=margin_bytes)
    if not v.ok:
        raise InsufficientSpaceError(
            f"可用空間不足：{target} 所在檔案系統剩 {v.free_bytes} bytes，"
            f"本次需要 {v.required_bytes} bytes"
            f"（預估 {v.estimate_bytes} ＋ 餘裕 {v.margin_bytes}），"
            f"缺 {v.shortfall_bytes} bytes")
    logger.debug("可用空間檢查通過：free=%d required=%d", v.free_bytes, v.required_bytes)
    return v
