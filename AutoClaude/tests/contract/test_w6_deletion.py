"""AC2-2（W6「mixin 物理刪除」）的**真斷言落點**——R82 包 A2（DEBT-01）建立。

# 為何本檔在 R82 才出現，而它守的事實 2026-05-18 就成立了

`tests/contract/test_ac_matrix_scaffolding.py` 的 AC Matrix 對 AC2-2 登記的
`target_test_file` 是本檔，門檻逐字是「`_runner_internals.py` / `_runner_compat.py`
皆不存在」。R82 掃描實查：那兩支檔**確實都不存在**（SD_06 W6 物理刪除），也就是說
**受測條件早就滿足了，缺的只有這支斷言檔**——於是 AC2-2 連續多輪掛著一句
`[DEBT] … 承接輪次 R82` 的 skip，而它其實是本輪四筆 DEBT 裡唯一「零風險即可轉綠」的。

# 這支測試守的是什麼（Rule 9：鎖意圖，不只鎖行為）

「檔案不存在」聽起來不像一個需要測試的東西，但它在本 repo 是一份**契約**：
`docs/06_quality/Runner_Internals_Anti_Resurrection_Guard.md` §1.2 第 4 點逐字寫著
「檔案不存在的事實本身就是『契約』」。那份文件同時記載三層既有防護
（importlinter Rule 3／Rule 6／`test_runner_no_checkpoint_logic.py` 的 grep 掃描），
而三層**沒有一層**會因為「有人把 `_runner_internals.py` 建回來」而轉紅：

  · Rule 3／Rule 6 是 **forbidden import** 契約——只有在**有人 import 它**時才說話。
    重建一支沒有任何消費者的 `_runner_internals.py`（god-class 復活的第一步通常正是
    如此：先把檔案搬回來、之後再慢慢接線）不會違反任何一條 import 契約。
  · `test_runner_no_checkpoint_logic.py` 掃的是 `_save_.*_checkpoint` 這個**字樣**，
    對「檔案本身回來了、但暫時還沒帶 checkpoint 邏輯」同樣結構上失明。

⇒ 本檔補的是那三層都看不到的第四面：**存在性本身**。這不是重複覆蓋，是三層鎖的
共同盲區。

# 誠實劃界

本檔只斷言「這兩支檔不在 `autoclaude/execution/` 底下」。它抓不到「換一個名字把同一
個 god-class 搬回來」——那件事由 LOC 分級政策（`tools/check_loc_budget.py`）與
importlinter 的 layer 契約承接，不在本檔射程內。
"""
from __future__ import annotations

from pathlib import Path

#: `AutoClaude/`（本檔的上上層）。
_AUTOCLAUDE_ROOT = Path(__file__).resolve().parents[2]
_EXECUTION = _AUTOCLAUDE_ROOT / "autoclaude" / "execution"

#: AC2-2 門檻逐字指名的兩支檔（相對 `autoclaude/execution/`）。
_DELETED_MIXINS = ("_runner_internals.py", "_runner_compat.py")


def test_the_execution_package_exists_so_the_assertion_is_not_vacuous() -> None:
    """正控：受測目錄必須真的在。

    少了這一支，把 `_EXECUTION` 寫成任何一個不存在的路徑都能讓下面全綠——那正是
    「掃描面塌成空集合」的假綠（本 repo 對每一道存量掃描都要求的下限釘選）。
    """
    assert _EXECUTION.is_dir(), (
        f"execution 套件目錄不存在：{_EXECUTION}——路徑寫錯的話，下面的"
        "「檔案不存在」斷言會恆真而失去全部鑑別力"
    )
    modules = sorted(p.name for p in _EXECUTION.glob("*.py"))
    assert len(modules) >= 10, (
        f"execution 底下只掃到 {len(modules)} 支模組（{modules}）——"
        "W6 之後這一層是 17 個薄 facade 模組接管，數量塌了代表掃描面或佈局出了事"
    )


def test_the_two_god_class_mixins_stay_physically_deleted() -> None:
    """AC2-2 本體：兩支 mixin 容器不得以任何形式回到 `autoclaude/execution/`。

    背景（`Runner_Internals_Anti_Resurrection_Guard.md` §1.1）：
    `_runner_internals.py` 曾膨脹到 **1,694 LOC**（god-object，承擔 checkpoint／boot／
    strategy／prompt 四種職責），`_runner_compat.py` 238 LOC，兩者於 SD_06 W6
    （2026-05-18）物理刪除。復活的代價不是風格問題——它會同時打破 ADR-SD07-001 的
    service tier ≤ 500 與 execution 層的職責邊界。
    """
    resurrected = [name for name in _DELETED_MIXINS if (_EXECUTION / name).exists()]
    assert resurrected == [], (
        f"god-class mixin 容器復活了：{resurrected}（於 {_EXECUTION}）。"
        "這兩支檔於 SD_06 W6 物理刪除，'檔案不存在' 本身就是契約——"
        "見 docs/06_quality/Runner_Internals_Anti_Resurrection_Guard.md §1.2。"
        "既有三層防護（importlinter Rule 3／Rule 6／test_runner_no_checkpoint_logic.py）"
        "都只在『有人 import 它』或『它帶了 checkpoint 字樣』時才說話，對『檔案回來了但"
        "還沒接線』結構上失明——本支就是那一面"
    )


def test_no_module_anywhere_declares_these_as_a_package_module() -> None:
    """第二面：即使不放在 `execution/`，也不得有人在別處建同名模組再轉接。

    誠實劃界：這一支掃的是**檔名**，掃描面限定在 `autoclaude/` 生產碼樹內（測試與
    文件當然可以提到這兩個名字——`Runner_Internals_Anti_Resurrection_Guard.md`
    與本檔自己就在提）。它抓不到改名復活，那由 LOC 分級與 layer 契約承接。
    """
    package = _AUTOCLAUDE_ROOT / "autoclaude"
    assert package.is_dir(), f"生產碼套件目錄不存在：{package}"
    offenders = [
        str(path.relative_to(_AUTOCLAUDE_ROOT).as_posix())
        for name in _DELETED_MIXINS
        for path in package.rglob(name)
    ]
    assert offenders == [], (
        f"在生產碼樹內找到已刪除的 mixin 容器：{offenders}——"
        "換一個目錄放回來與放回原處是同一件事"
    )
