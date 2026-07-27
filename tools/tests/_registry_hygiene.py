#!/usr/bin/env python3
"""路徑為鍵的**豁免／登記名冊**衛生判準 SSOT（R58 round 5 ARCH-R58R5 P3 ④ 收斂）。

## 為什麼有這支模組

本 repo 的機械鎖普遍配一張「附理由的豁免名冊」，而名冊本身會腐化，故每張表都要驗兩件事：
①鍵指向的檔案還在嗎（否則名冊變成無人維護的死清單）②理由是空白嗎（防「先加豁免再補理由」
變成永久 TODO）。判準只有這兩條，但**實作曾經有兩份**：

  * `test_platform_guard_availability.py` 抽成純函式 `stale_problems()`，並配了鑑別力自驗
    `test_stale_detector_has_discrimination`（餵合成輸入，因為現況名冊小到讓就地檢查恆綠）。
  * `test_behavioural_lock_required.py` 就地手寫同兩條 invariant，**沒有**自驗。

round 4 修 ARCH-R58R4-01 時，我把 `_GROWTH_EXEMPT` 加進**手寫那一份**而不是改成委派共享
純函式——也就是在「消滅同一行為的多份複本」這個立案主題上，自己又生出一份複本。round 5
Architect 抓到（按既有判例評 P3、不阻擋），此處收斂。

**為什麼另開模組、不放進 `_platform_helpers.py`**：Architect 建議的共享家是 `_platform_helpers.py`，
但該檔契約明文是**單一類**——「只收對開發者本機作業系統／環境有隱性假設、且只有真的在目標
OS 上跑一次才會顯形的測試 fixture 輔助」。名冊衛生與作業系統無關，塞進去就是重演該檔 docstring
自己記載的那個錯（R57 因 `strip_ps_comments` 寄居而被迫把契約改成「兩類收納物」，該檔稱之為
「**契約被內容反向牽著改就是雜物抽屜的早期訊號**」，R58 才拆出 `_ps_source.py` 把契約收回單一類）。
故沿用 R58 既有作法：一個判準、一支聚焦模組（同 `_repo_scan.py`／`_ps_source.py`／`_sdd_versions.py`）。

**已實測涵蓋**：以 repo 相對路徑為鍵、以理由字串為值的 `dict[str, str]` 名冊。
**已實測不涵蓋**：鍵不是路徑者（如能力名稱 `_CAPABILITY_PROVENANCE`）只適用
`empty_reason_keys()`，不適用 `stale_problems()` 的檔案存在性那一半。**未窮舉**。
"""
from __future__ import annotations

from pathlib import Path


def empty_reason_keys(registry: dict[str, str]) -> list[str]:
    """說明／理由為空（或純空白）的條目 key。

    抽成純函式而非就地寫在斷言裡：現況名冊的說明全部非空，就地比對**在現況下不可能失敗**
    ——零鑑別力的自檢與沒有自檢等價（QA-R58R1-03）。名冊本身刻意維持現狀（不為了製造
    鑑別力而塞假條目），鑑別力改由自驗測試餵合成輸入提供。
    """
    return sorted(k for k, v in registry.items() if not v.strip())


def stale_problems(
    registry: dict[str, str], repo_root: Path, label: str = ""
) -> list[str]:
    """路徑為鍵的豁免名冊的腐化問題清單（空清單＝健康）。

    兩類問題：①鍵指向的檔案已不存在 ②理由為空白。與 `empty_reason_keys` 同一個抽純函式的
    理由：現況名冊小到讓就地檢查恆綠，鑑別力必須由合成輸入提供。

    `label`＝表名前綴。同一支測試驗多張表時，訊息若不具名就無法分辨是哪張表腐化
    （round 5 SD 實測確認具名訊息有價值：`_GROWTH_EXEMPT 豁免項未附理由：…`）；
    留空則沿用單表呼叫端的既有訊息字面，故此次收斂**不改任何現有訊息**。
    """
    prefix = f"{label} " if label else ""
    problems = [
        f"{prefix}豁免項已不存在：{rel}"
        for rel in registry
        if not (repo_root / rel).is_file()
    ]
    problems += [f"{prefix}豁免項未附理由：{rel}" for rel in empty_reason_keys(registry)]
    return problems
