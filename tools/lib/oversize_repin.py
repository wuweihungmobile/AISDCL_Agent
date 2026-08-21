"""機械物③：帳本逐列超標三常數（`OVERSIZE_ROW_CEILING`／`OVERSIZE_ROW_EXCESS_CEILING`／
`OVERSIZE_ROW_GRANDFATHERED`，皆定義於 `tools/lib/defect_ledger_index.py`）的 shrink-only 自動重釘
（帳本減半收斂期）。

**現況實測會撞到的情境（任務書指名，本檔的第一個消費場景）**：`archive_defect_log.py
--plan` 一旦搬走一批已結列，可能讓其中幾筆原本超標的列跟著離開主檔，`OVERSIZE_ROW_
GRANDFATHERED` 裡對應那幾筆豁免就此過期——`tools/lib/ledger_rotation.
expiring_oversize_waivers()` 早就會**預測**這件事並印在 `--plan`／`--apply` 的輸出裡，
但預測之後「把三個常數真的改掉」一直是人工動作。本檔把「量測 → 判方向 → （安全時）自動
下修」接上去，人工只在**放寬**方向才需要出手。

**為何只做「收緊」的自動寫檔，「放寬」永遠人工**（任務書②③兩向的字面要求）：
① 收緊＝既有豁免變得不再需要，刪它、把天花板調小——這個方向**不可能傷到任何人**，
   因為它只是把一個已經不再成立的許可收回。
② 放寬＝要求系統原諒一筆**更大**的超標——這代表有人明知故犯地讓一列變胖卻沒有走
   「把長文搬進具名證據檔」的合法出口。這個決定**必須**有人具名承擔，故不自動化，
   且下方 `apply_tighten()` 自己也拒絡被拿來做放寬（見該函式的內建方向鎖）。

**本檔刻意不擁有、也不修改** `tools/lib/ledger_rotation.py` **的 `*_HISTORY`／封印**
（那支檔不在本包射程內）。這條耦合是誠實的缺口，不是遺漏：`ratchet_direction_
problems()`（住 `ledger_rotation.py`）另外要求三條史料的**末元素**等於現行常數、且
封印摘要對得上——本檔重釘常數之後，那道鎖會**如期轉紅**直到有人把對應的 `*_HISTORY`
與封印一併更新。這是**設計成如此**：常數本身的持有面在 `defect_ledger_index.py`
（本包射程內），但「重釘史真的被追加」這件事的持有面在別的檔（見 CLAUDE.md 鐵律七
「鎖的持有面」）；一個工具去正確完成另一個持有面的義務，會製造出「一個包的自動化
悄悄改了另一個包才有權責交代的史料」這種更難稽核的耦合。本檔選擇**把要做的事說清楚，
而不是硬做**：`run_repin()` 每次收緊之後都印出一段「還差這一步，且是誰的職責」的提醒
（見 `_HISTORY_HANDOFF_NOTE`）。
"""

from __future__ import annotations

import re

from lib import defect_ledger_index as _idx
from lib import ledger_rotation as _rotation

_HISTORY_HANDOFF_NOTE = (
    "🔴 尚未完成的另一半（不在本工具射程內）：`tools/lib/ledger_rotation.py` 的 "
    "OVERSIZE_ROW_CEILING_HISTORY／OVERSIZE_ROW_EXCESS_CEILING_HISTORY 與封印表"
    "（_SEALED_HISTORY_PREFIXES／_SEAL_TOTAL_MIN_LEN／_SEAL_TABLE_SHA256）尚未同步"
    "追加上面的新值——那支檔的持有面不在本包射程內，`ratchet_direction_problems()` "
    "會在補齊前如期轉紅（這是設計如此，見本模組 docstring）。請由擁有 "
    "ledger_rotation.py 的窗口補上這一步，而不是把本工具的輸出當成「已經做完」"
)


def current_state(ledger_text: str) -> dict:
    """帳本主檔**現況**的超標量測——直接呼叫 `expiring_oversize_waivers([], text)`。

    刻意不重寫量測邏輯：`move_ids=[]` 時該函式的 `remaining == ledger_text`（沒有任何
    行被模擬移除），於是它算出的正是「現在」的超標狀態，與它原本用來算「搬遷後」狀態
    是**同一個算式**。同一個問題只該有一個答案（本 repo 反覆在治的複本型缺陷的反面）。
    """
    return _rotation.expiring_oversize_waivers([], ledger_text)


def direction(state: dict) -> str:
    """三常數當前該往哪個方向動：`"noop"`／`"tighten"`／`"loosen"`（純函式，可構造輸入驗牙）。

    🔴 只要**任一**維度（筆數或超標總量）變大就判定為 `"loosen"`——即使另一維度同時
    變小也一樣：自動化路徑只能在「兩個維度都沒有變糟」時才可以無人核准地動手，任何一個
    維度變糟都必須有人具名承擔（見模組 docstring①②）。
    """
    ceiling_worse = state["new_ceiling"] > _idx.OVERSIZE_ROW_CEILING
    excess_worse = state["new_excess"] > _idx.OVERSIZE_ROW_EXCESS_CEILING
    if ceiling_worse or excess_worse:
        return "loosen"
    if (state["new_ceiling"] < _idx.OVERSIZE_ROW_CEILING
            or state["new_excess"] < _idx.OVERSIZE_ROW_EXCESS_CEILING):
        return "tighten"
    return "noop"


_CEILING_LINE_RE = re.compile(r"^OVERSIZE_ROW_CEILING = \d+$", re.MULTILINE)
_EXCESS_LINE_RE = re.compile(r"^OVERSIZE_ROW_EXCESS_CEILING = \d+$", re.MULTILINE)
_GRANDFATHER_BLOCK_RE = re.compile(
    r'(OVERSIZE_ROW_GRANDFATHERED: frozenset\[str\] = frozenset\(""")'
    r'(.*?)'
    r'("""\.split\(\)\))',
    re.DOTALL,
)
_WRAP_WIDTH = 66  # 沿用原檔既有的大致換行寬度，純美觀、不影響 frozenset("""...""").split() 語意


def _rewrap_ids(ids: list[str]) -> str:
    """把 ID 清單重新換行成固定寬度的多行區塊（純字串排版，不影響 `.split()` 出的集合）。"""
    lines: list[list[str]] = [[]]
    width = 0
    for i in sorted(ids):
        if width + len(i) + 1 > _WRAP_WIDTH and lines[-1]:
            lines.append([])
            width = 0
        lines[-1].append(i)
        width += len(i) + 1
    return "\n" + "\n".join(" ".join(row) for row in lines) + "\n"


def apply_tighten(
    index_text: str, new_ceiling: int, new_excess: int, remove_ids: set[str],
) -> str:
    """對 `defect_ledger_index.py` **原始碼全文**做純文字轉換，回傳新全文（不寫檔）。

    🔴 **方向鎖內建在這個最底層函式本身，不是只在上層的 CLI 分派邏輯**（任務書要求
    「釘住這個不變量不會被自動化路徑繞過」）：無論呼叫端是誰、走哪一條分派路徑，只要
    `new_ceiling` 或 `new_excess` 比現行常數**大**，本函式一律拒絕（`ValueError`）。
    這與只在 CLI 層擋是不同的兩件事——CLI 層的擋法可以被「直接 import 這支函式來用」
    繞過，寫進最底層才是真的擋死。

    純函式（吃字串、吐字串），不觸碰磁碟——寫檔與否是呼叫端的決定，這樣才能用構造輸入
    直接驗证這個轉換本身對不對，不必真的動一份 tracked 檔。
    """
    if new_ceiling > _idx.OVERSIZE_ROW_CEILING or new_excess > _idx.OVERSIZE_ROW_EXCESS_CEILING:
        raise ValueError(
            f"apply_tighten() 拒絕執行：new_ceiling={new_ceiling}／new_excess={new_excess} "
            f"其中至少一項大於現行常數（{_idx.OVERSIZE_ROW_CEILING}／"
            f"{_idx.OVERSIZE_ROW_EXCESS_CEILING}）——這是「放寬」，不是「收緊」。"
            "本函式只做 shrink-only 自動重釘，放寬須經 run_repin() 的顯式旗標路徑"
            "（--repin-oversize-ceiling ＋ --reason），且該路徑同樣不呼叫本函式"
        )
    unknown = remove_ids - _idx.OVERSIZE_ROW_GRANDFATHERED
    if unknown:
        raise ValueError(f"remove_ids 含不在現行豁免清單內的 ID：{sorted(unknown)}")
    text = _CEILING_LINE_RE.sub(f"OVERSIZE_ROW_CEILING = {new_ceiling}", index_text, count=1)
    text = _EXCESS_LINE_RE.sub(
        f"OVERSIZE_ROW_EXCESS_CEILING = {new_excess}", text, count=1)
    remaining = sorted(_idx.OVERSIZE_ROW_GRANDFATHERED - remove_ids)
    m = _GRANDFATHER_BLOCK_RE.search(text)
    if m is None:
        raise ValueError("找不到 OVERSIZE_ROW_GRANDFATHERED 的 frozenset(\"\"\"…\"\"\") 區塊"
                         "——來源檔格式可能已改版，拒絕在猜測的位置寫入")
    text = text[:m.start()] + m.group(1) + _rewrap_ids(remaining) + m.group(3) + text[m.end():]
    return text


def run_repin(ledger_text: str, index_text: str, override_ceiling: int | None,
             reason: str) -> tuple[int, str, str | None]:
    """`--repin-oversize` 的核心決策（不含實際寫檔——由 caller 決定；純函式化到這個程度
    是為了讓「決策對不對」可以用構造輸入驗，不必真的碰一份 tracked 檔）。

    回傳 `(rc, 人類可讀訊息, 新的 defect_ledger_index.py 全文或 None)`：
      · 現測值皆未超過現行常數 ⇒ `(0, "no-op 說明", None)`——**caller 不寫檔**。
      · 需要收緊 ⇒ `(0, 訊息, 新全文)`——caller 把第三項寫回磁碟。
      · 任一維度變糟且未帶 `--repin-oversize-ceiling`＋`--reason` ⇒ `(1, 錯誤說明,
        None)`，不動任何檔案。
      · 任一維度變糟但**已**顯式帶旗標＋理由 ⇒ `(0, 訊息, 新全文)`——這是**人工核准**
        的放寬，不經 `apply_tighten()` 的方向鎖（那把鎖是為自動路徑立的；人工路徑的
        覆寫憑證就是這裡要求的 `reason` 非空字串，且新值一律以人類明確給的
        `override_ceiling` 為準，不悄悄再拿測量值去動 excess）。
    """
    state = current_state(ledger_text)
    d = direction(state)
    if d == "noop":
        return 0, "現測值未超過任一現行常數，無需重釘（no-op）", None
    if d == "loosen" and (override_ceiling is None or not reason.strip()):
        return 1, (
            f"❌ 現測值變糟（筆數 {state['new_ceiling']} vs 現行 "
            f"{_idx.OVERSIZE_ROW_CEILING}／超標總量 {state['new_excess']} vs 現行 "
            f"{_idx.OVERSIZE_ROW_EXCESS_CEILING}），拒絕自動調高。這代表有既有豁免列被"
            "改長，或有新列被就地追加成超標——正解是把長文搬進具名證據檔，而不是調高"
            "天花板。若你已確認調高是必要的（例如硬規則② 的合法出口本身就要佔位元組，"
            "見 defect_ledger_index.py 既有史料的同型案例），請帶 "
            "`--repin-oversize-ceiling <新值> --reason \"<WHY>\"` 顯式核准"
        ), None
    old_c, old_e = _idx.OVERSIZE_ROW_CEILING, _idx.OVERSIZE_ROW_EXCESS_CEILING
    if d == "loosen":
        new_ceiling = override_ceiling
        new_text = _CEILING_LINE_RE.sub(f"OVERSIZE_ROW_CEILING = {new_ceiling}", index_text, 1)
        new_text = _EXCESS_LINE_RE.sub(
            f"OVERSIZE_ROW_EXCESS_CEILING = {state['new_excess']}", new_text, 1)
        msg = (f"⚠️ 人工核准放寬：OVERSIZE_ROW_CEILING {old_c} → {new_ceiling}"
              f"（理由：{reason}）；OVERSIZE_ROW_EXCESS_CEILING {old_e} → "
              f"{state['new_excess']}。\n{_HISTORY_HANDOFF_NOTE}")
        return 0, msg, new_text
    new_text = apply_tighten(
        index_text, state["new_ceiling"], state["new_excess"], set(state["expiring"]))
    msg = (
        f"✅ 自動收緊：OVERSIZE_ROW_CEILING {old_c} → {state['new_ceiling']}；"
        f"OVERSIZE_ROW_EXCESS_CEILING {old_e} → {state['new_excess']}；"
        f"移除過期豁免：{', '.join(state['expiring']) or '（無）'}\n{_HISTORY_HANDOFF_NOTE}"
    )
    return 0, msg, new_text
