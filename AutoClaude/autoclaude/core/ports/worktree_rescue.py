# IWorktreeRescue — 「凍結前保全髒污工作樹」的 Port（PRD §4.5.9；立案＝DEF-200-205）。
#
# 立案：`infra/adapters/dirty_worktree_rescue.py` 把 R-4.5.9 整條救援序列都實作完了，
# 卻**零生產呼叫端**——機制蓋好沒接電。要接電就得跨一條架構邊界：唯一語意正確的呼叫端是
# `core/services/auto_resume.py`（它是「halt ⇒ 等待 ⇒ 續跑」那條路的持有者），而 core/
# 依 `.importlinter` core-purity contract **不得 import infra**。⇒ 本 Port 就是那條縫：
# 消費端只認這裡的抽象，實作由 `core/wiring.py::build_worktree_rescue` 注入。
#
# 🔴 為什麼狀態字面（`SAVED`／`DIRTY_UNSAVED`）住這裡而不是留在 adapter：消費端要拿
#    `outcome.status` 去比對才知道「敢不敢睡」，而它讀不到 adapter。字面若兩邊各留一份，
#    漂移方向是**消費端那份沒跟著改**，失效形態＝比不中 ⇒ 一律當成救援成功（fail-open），
#    正是 R-4.5.9-4 逐字禁止的那一件事。所以字面一個家：adapter 從這裡 import 回去用。
#
# 🔴 為什麼 `RescueOutcome` 是 Protocol 而不是另一個 dataclass：那四個可重驗值
#    （patch 路徑／期望 checksum／實測 checksum／位元組數）已經有一個家了
#    （`dirty_worktree_rescue.RescueResult`）。再宣一個 frozen dataclass 就得寫一層
#    對映，而對映漏欄位的失效形態是靜默的（欄位變 0／空字串，剛好長得像「沒發生」）。
#    結構型別讓 adapter 那份 dataclass 直接算是實作，零對映層。
from __future__ import annotations

from typing import Protocol, runtime_checkable

# R-4.5.9-4 的兩個終態。
SAVED = "SAVED"
DIRTY_UNSAVED = "DIRTY_UNSAVED"
# 🔴 第三個字面**不在** PRD 條文內，是本 Port 為了讓「不必救援」與「救援失敗」分得開而加的：
#    R-4.5.9 的進入條件是「worktree 有未提交變更」，於是乾淨工作樹本來就不該進救援序列。
#    若把它硬送進去，patch 會是 0 bytes ⇒ 被 (c) 斷言判成 DIRTY_UNSAVED ⇒ 每一次「工作樹
#    很乾淨」的 halt 都會被讀成「工作沒保全、禁止自動喚醒」＝假紅，而假紅會讓整道判準被
#    關掉（本 repo 已有判例）。`CLEAN` 由 adapter 的前置守衛產出，不由救援序列本身產出。
CLEAN = "CLEAN"

#: 唯一會讓消費端拒絕轉入等待／自動喚醒的狀態集合。判準一個家：消費端不得自己再寫一次
#: `status == "DIRTY_UNSAVED"`（那樣新增終態時漏改的方向又是 fail-open）。
UNSAFE_TO_FREEZE = (DIRTY_UNSAVED,)


class RescueOutcome(Protocol):
    """救援結果的結構型別。欄位＝R-4.5.9-4 第 1 點逐字要求進 state.json 的可重驗值。

    只寫「救援失敗」等於把下一輪的診斷成本推給人 ⇒ 這些欄位是規範性的，不是選配。
    """

    status: str
    patch_path: str
    expected_checksum: str
    actual_checksum: str
    bytes_written: int
    bytes_read_back: int
    attempts: int
    reason: str


@runtime_checkable
class IWorktreeRescue(Protocol):
    """凍結前保全髒污工作樹（PRD §4.5.9）。

    契約（消費端可以依賴的三件事）：
      1. **絕不 fail-open**：救援沒有成功時 `status` 不得是 `SAVED`。呼叫端因此得以
         用「status ∈ UNSAFE_TO_FREEZE」當作「不得轉入 WAITING_RESET／LONG_HIBERNATE」。
      2. **不改動工作樹**：救援後 `git status --porcelain` 逐字不變（R-4.5.9 D1）。
      3. **乾淨工作樹回 `CLEAN`**，不回 `DIRTY_UNSAVED`（理由見上方 CLEAN 註解）。

    刻意零參數：patch 要落哪、retries 幾次、agent_id 是什麼、通知走哪個通道，全都是
    **組裝期**的知識，屬 wiring；讓消費端傳等於要求 core/ 知道 patch 目錄長什麼樣。
    """

    def rescue(self) -> RescueOutcome:
        """執行一次救援；回 status ∈ {SAVED, DIRTY_UNSAVED, CLEAN} 的結果。"""


__all__ = [
    "CLEAN",
    "DIRTY_UNSAVED",
    "SAVED",
    "UNSAFE_TO_FREEZE",
    "IWorktreeRescue",
    "RescueOutcome",
]
