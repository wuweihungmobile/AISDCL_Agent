#!/usr/bin/env python3
"""`MIN_TESTS` 重釘提醒的判準——量的是**零相依沙箱收集數 − `MIN_TESTS`** 的餘裕（DEF-200-170）。

WHY 本模組存在（修的是判準本身，不是重構）：
`run_root_unittests` 原本的兩層人工 ratchet 比的是「相依齊備環境下的收集數 ÷ `MIN_TESTS`」
——`RATCHET_WARN_RATIO`（1.10，只印不擋）與 `RATCHET_STALE_RATIO`（1.25，會紅）。
DEF-200-170 逐次驗算五輪同型復發（R82 2574→2795 線 2831／R83 2795→3052 線 3074／
R84 3095→3279 線 3404／R96 3284→3462 線 3612／R96-D2 補登），那段 [1.10, 1.25] 的緩衝帶
**一次都沒有被跨過**：每一次先炸的都是
`tools/tests/test_run_root_unittests.py::ZeroDepEnvironmentDiscriminationTest`，
而它的紅字逐字是「`環境問題` not found in `❌ discovery 佔位測試 4 筆…`」
⇒ 讀者被指往「相依沒裝齊」，沒有人會想到真正該做的事是「把 `MIN_TESTS` 重釘」。

**那段緩衝帶在物理上到不了**，而且證明是算術、不是觀感：
零相依沙箱（＝三支 CI 的等價環境）會把每一支需要第三方相依的測試模組整份覆蓋
塌成一支佔位測試，故它的收集數恆為 `count - loss`（`loss` 見 `collapse_loss`）。
本下限一旦不再高於那個數（`count - loss >= min_tests`，即 `count >= min_tests + loss`），
零相依鑑別力就沒了；而舊 WARN 要等到 `count > min_tests * 1.10`。
只要 `loss < 0.10 * min_tests`，環境判準**必然**先炸——本 repo 落地當回合實測
`loss = 178` vs `0.10 * 3767 = 376.7`，差了一倍以上，所以舊 WARN 層是結構性死判準。

修法＝換分母：把提醒綁到「零相依沙箱還剩幾支餘裕」上。那是**與失效同一根軸**的量，
於是門檻帶必然落在餘裕歸零之前（可達性由 `first_speaking_count()` 與
`discrimination_lost_count()` 的大小關係機械自證，見
`tools/tests/test_run_root_unittests.py::MinTestsMarginCriterionTest`）。

🔴 為何本模組沒有引進第二個會腐化的釘選數字（這一點是本修法能不能算數的關鍵）：
這裡**不**釘 `loss`，只釘「哪幾支模組會塌」這個**集合**（`PREREQ_DEPENDENT_MODULES`）；
支數一律由呼叫端當回合實測的 `suite_modules()` 現算。集合面比計數面穩定得多
（那是「這支測試要不要 import autoclaude」這種結構事實，不是每輪都在動的量測值），
且它的保鮮由真的零相依探針看守——探針實測到的佔位模組集合必須逐字等於本集合，
不等即紅並印出差集。

誠實劃界：`loss` 為 0 時本判準一個字都不說（回 `None`）。那不是放行，是**不適用**
——沙箱裡一支模組都不塌 ⇒ 零相依收集數等於相依齊備收集數 ⇒ 沒有「零相依鑑別力」
這回事可以保護。合成樹（單元測試餵給 `run_with_floor` 的那些）與探針子行程內部
都落在這一支，於是它們不會被本判準製造噪音。此時外層後備仍是那兩個比例常數。
"""
from __future__ import annotations

import math
from collections.abc import Mapping

#: 零相依沙箱裡會整份塌成佔位測試的測試模組（＝`run_root_unittests._THIRD_PARTY_PREREQS`
#: 宣告的那幾個相依的真實消費者）。刻意釘**集合**而非支數，理由見檔頭。
#: 保鮮看守＝`tools/tests/test_run_root_unittests.py::MinTestsMarginCriterionTest`
#: `::test_the_declared_collapsing_set_matches_the_real_sandbox`（真探針，非第二份猜測）。
PREREQ_DEPENDENT_MODULES: frozenset[str] = frozenset(
    {
        "test_gha_action_versions",
        "test_ntfs_trailing_space_device_name",
        "test_windows_forbidden_filename_parity",
        "test_windowsapps_guard_cross_consistency",
    }
)

#: 兩層門檻，單位是「餘裕佔滿格的比例」。滿格＝剛重釘完的那一刻（餘裕恰為 `loss`）。
#: 🔴 為何是比例而不是絕對支數：滿格值本身會隨那幾支模組的大小變動，絕對支數會在
#: 滿格縮小時悄悄變成「一落地就紅」或「永遠不紅」。比例讓兩層的相對位置不隨滿格漂移。
#: 🔴 為何 WARN 訂在一半：本 repo 單輪成長實測可達 167 支（R96→R100），已與滿格
#: 同量級 ⇒ 一輪就可能吃掉整個預算。提醒必須在還剩一半時就出聲，否則沒有前置時間。
HEADROOM_WARN_FRACTION = 0.50
HEADROOM_STALE_FRACTION = 0.25


def collapse_loss(
    module_counts: Mapping[str, int],
    dependent: frozenset[str] = PREREQ_DEPENDENT_MODULES,
) -> int:
    """零相依沙箱會蒸發掉的測試支數＝Σ(那幾支模組的收集數) − 模組數。

    減掉模組數是因為它們不是消失、是**塌成一支佔位測試**（`_FailedTest`），
    所以每一支模組在沙箱裡仍貢獻 1。純函式，值全部來自呼叫端當回合的實測。
    """
    present = [n for name, n in module_counts.items() if name in dependent]
    return sum(present) - len(present)


def zero_dep_headroom(count: int, min_tests: int, loss: int) -> int:
    """`min_tests − 零相依沙箱收集數`，即「本下限還能撐幾支成長」。

    恆等式：零相依收集數＝`count - loss` ⇒ 餘裕＝`loss - (count - min_tests)`。
    正值＝鑑別力還在；歸零或轉負＝下限對零相依沙箱已完全失效。
    """
    return loss - (count - min_tests)


def headroom_threshold(loss: int, fraction: float) -> int:
    """某一層的餘裕門檻（支）。`floor` 而非 `round`：門檻寧可略嚴，不可略鬆。"""
    return math.floor(loss * fraction)


def first_speaking_count(min_tests: int, loss: int, fraction: float) -> int:
    """該層第一次說話時的收集數——`headroom <= threshold` 的最小 `count`。"""
    return min_tests + loss - headroom_threshold(loss, fraction)


def discrimination_lost_count(min_tests: int, loss: int) -> int:
    """零相依鑑別力歸零時的收集數——`ZeroDepEnvironmentDiscriminationTest` 由此開始
    印出那句誤導性的紅字。本判準的每一層都必須嚴格小於這個數才算「先說話」。"""
    return min_tests + loss


def headroom_message(
    count: int,
    min_tests: int,
    module_counts: Mapping[str, int],
    fraction: float = HEADROOM_WARN_FRACTION,
) -> str | None:
    """餘裕跌破該層門檻時回傳可直接印的提醒；否則 `None`（純函式、無 I/O）。

    `fraction` 參數化讓兩層共用同一段判定與訊息（比照被它取代的
    `run_root_unittests.ratchet_drift_message` 的既有體例）：runner 傳 WARN 比例只印，
    紅線層傳 `HEADROOM_STALE_FRACTION` 讓閘門變紅。
    """
    loss = collapse_loss(module_counts)
    if loss <= 0:
        return None  # 不適用（見檔頭〈誠實劃界〉），不是放行
    headroom = zero_dep_headroom(count, min_tests, loss)
    threshold = headroom_threshold(loss, fraction)
    if headroom > threshold:
        return None
    state = f"只剩 {headroom}" if headroom > 0 else f"已經用完（{headroom}）"
    return (
        f"⚠️  MIN_TESTS 該重釘了（DEF-200-170）：零相依沙箱的鑑別力餘裕{state}／{loss} 支"
        f"（本層門檻 {threshold}）。餘裕歸零那一刻，先說話的會是"
        f" ZeroDepEnvironmentDiscriminationTest，而它的紅字講的是「相依裝齊了沒」"
        f"——指的方向不是這裡，五輪同型復發都是這樣被歸錯因的。"
        f"請把 tools/run_root_unittests.py 的 MIN_TESTS 重釘為 {count}"
    )
