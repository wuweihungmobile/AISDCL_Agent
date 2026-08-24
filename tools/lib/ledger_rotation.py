#!/usr/bin/env python3
"""帳本輪替的兩個副作用 ＋ 三條 shrink-only 棘輪的方向鎖（`DEF-101-977`／`676`／`993`）。

**為何獨立成一支檔**：`tools/check_defect_log_crossref.py` 與 `tools/archive_defect_log.py`
兩支的 raw-line 棘輪門檻皆＝「納管當下實際行數」＝餘裕近乎零，而該棘輪的 `override_reason`
逐字把第一順位處置寫成「先刪死碼／抽共用模組（先例 `tools/lib/ci_liveness.py`）」。
本檔就是那個動作，不是為了整齊而拆——三個判準的共通主題是**帳本輪替與棘輪方向**：
輪替會改變下游判準的輸入，而棘輪自己的上限也是一種會被人動的輸入。

全部是**純函式**：不讀磁碟、不看全域狀態，因此每一條都能以構造輸入直接驗牙。
"""
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import date as _date
from pathlib import Path

# 🔴 雙形態 import：本 repo 的 `tools/` 與 `tools/lib/` 都**沒有** `__init__.py`（namespace
# package），而兩種呼叫端都真實存在——閘門與其測試把 `tools/` 放上 sys.path（`from lib …`），
# 由 repo 根跑的 unittest／探針則是 `tools.lib…`。寫死任一種都會讓另一種在 import 期就炸，
# 而那種紅看起來像「模組不存在」而不是「路徑慣例不一致」。
try:
    from lib import defect_ledger_index as _idx
except ImportError:  # pragma: no cover - 另一種 sys.path 形態，兩者擇一必成立
    from tools.lib import defect_ledger_index as _idx

# ---------------------------------------------------------------- 三條棘輪的重釘史
# 🔴 立案（`DEF-101-993`，當回合實測）：`OVERSIZE_ROW_CEILING`／
# `OVERSIZE_ROW_EXCESS_CEILING`／`_UNPINNED_HANDOVER_CEILING` 三者的散文自 R68／R79 起
# 逐輪自稱「只准往下改、零成長容忍」，而那句話**零觀測者**。實測手法與輸出：
#   · 把某一列改長 85 bytes ⇒ `oversize_row_problems()` 紅（判準④ 有牙，這一半是真的）；
#   · **接著把常數調高到新實測值** ⇒ 判準④ 轉綠、回 0 problems，而唯一釘住那些常數的
#     `test_the_real_ledger_baselines_are_exact_not_padded` 是「常數 == 當回合實測」的
#     **相等**斷言 ⇒ 帳本一長，那支測試**要求**你把常數調高。
# ⇒ 相等自檢在這件事上是幫兇不是守衛；缺的不是「常數 vs 實測」，是「常數 vs 它自己的上一個值」。
# 取值紀律：每個元素都是**當時的實測值**，歷史不得回填、不得改寫。
#: 🔴 帳本減半波追加 62：書記收斂波逐筆重寫多支存量列的狀態欄（含結案／移入外部
#: 阻塞軌），存量超標列由 63 → 62（`DEF-101-596` 瘦身後跌破 700 bytes 過期）。
#: 🔴 輪號不寫進本段散文，理由同上方對這條規律的既有交代；錨改用磁碟上查得到的
#: `archive_67`。追加 45：18 筆隨 `archive_67` 搬離主檔過期、`DEF-200-190` 因狀態欄
#: 追加複驗證據新增列入（62−18+1=45，`expiring_oversize_waivers()` 實測值）。
OVERSIZE_ROW_CEILING_HISTORY: tuple[int, ...] = (105, 101, 98, 85, 83, 66, 63, 62, 45)
OVERSIZE_ROW_EXCESS_CEILING_HISTORY: tuple[int, ...] = (
    162282, 147944, 147455, 146210, 143303, 140957, 138938, 138936, 123867,
    121758, 82896, 77186, 75047, 69122, 48864, 40889,
)
# 🔴 誠實劃界：本序列只收錄 `check_defect_log_crossref.py` 註解**自己留下證據**的那幾次
# （34→28 見該檔 R80 包 C 段、17 見「第六次轉動」段、6 為 R82 實測）。第三～第五次轉動的
# 中間值在該檔沒有留下數字，**刻意不回填猜測值**——靠猜的史料會讓方向判準判的是虛構的東西。
#: R84 追加 5：`DEF-101-206` 結為 wontfix ⇒ 白名單 6 → 5，天花板同步下修（收緊方向）。
#: 追加 4：`DEF-101-377` 結為 wontfix（原文逐字保全於
#: `CrossPlatform_R89_Closure_Evidence.md`）⇒ 白名單 5 → 4，天花板同步下修（收緊方向）。
#: 🔴 帳本減半波追加 0：`DEF-101-235`／`DEF-101-324`（唯二兩筆存量豁免）本輪雙雙以
#: `closed-by-decision` 結案，白名單清空 ⇒ 天花板 2 → 0。
UNPINNED_HANDOVER_CEILING_HISTORY: tuple[int, ...] = (34, 28, 17, 6, 5, 4, 2, 0)

# ---------------------------------------------------------------- 史料前綴的封印
# 🔴 立案（`DEF-101-995`，R82 掃描 §F 的四組實跑對照）：上面那條「歷史不得回填、不得
# 改寫」的取值紀律，和它治的那個病**一模一樣**——寫在註解裡、零觀測者。
# `ratchet_history_problems()` 的三向只看「相鄰段不上升」與「末元素 == 現值」，於是：
#   · `REWRITE-last`：把 `(105,101,98,85)` 改成 `(105,101,98,90)` 且現值同步改 90 ⇒ **綠**；
#   · `truncate`：把整段砍成 `(999,)` 且現值 999 ⇒ **綠**（沒有相鄰段，也對得上末元素）。
# ⇒ 那條棘輪能擋的只有「老實追加一個更大的數」這一種寫法。同一輪、同一個主題、第二次。
#
# 封印＝**史料的不可變前綴**，判準是 `history[:len(seal)] == seal`（前綴相等，**不是**
# 相等）。這個形狀是刻意的：
#   · 追加一個新值 ⇒ 封印仍是前綴 ⇒ 綠，**不需要動封印**。所以它不是「與當回合實測相等」
#     的那個幫兇形態（`DEF-101-993`）——那種相等斷言會**要求**你把常數改成新測到的值，
#     封印則相反：它拒絕任何已寫下的值被改。
#   · 改寫前綴內任一元素、或把史料砍短 ⇒ 前綴對不上 ⇒ 紅。
#   · 未封印的尾巴只准剩一個元素（見 `_SEAL_TAIL_MAX`）：不設這條的話，封印只保護
#     落地當下那幾個值，往後每一輪新追加的值又回到無人看守——鎖會隨時間自己失效。
#
# 🔴 **這確實是同一組數字的第二份複本，而那正是它的功能**：判準比的是兩份**彼此**，
# 任一份被單方面改動即紅（雙記帳，不是 SSOT 漂移）。⇒ 看到本判準轉紅時，**改封印讓它
# 變綠就是本判準要擋的那個動作**；紅燈訊息自己會這樣說。
_SEALED_HISTORY_PREFIXES: dict[str, tuple[int, ...]] = {
    # 帳本收斂輪（archive_67）：史料尾端追加 45，故把 62 一併封入（`_SEAL_TAIL_MAX=1` 只准留一個
    # 未封印的尾巴）。封印**只准在尾端延長**，這裡沒有改寫任何已釘過的值。
    "OVERSIZE_ROW_CEILING": (105, 101, 98, 85, 83, 66, 63, 62),
    "OVERSIZE_ROW_EXCESS_CEILING": (
        162282, 147944, 147455, 146210, 143303, 140957, 138938, 138936, 123867,
    121758, 82896, 77186, 75047, 69122, 48864,
    ),
    # 帳本減半波：史料尾端追加 0，故把 2 一併封入（同上，只在尾端延長、零改寫）。
    "_UNPINNED_HANDOVER_CEILING": (34, 28, 17, 6, 5, 4, 2),
}

#: 未封印的尾巴上限。1＝「除了最新追加的那一筆，全部都要封」。取 1 而不是 0：追加與
#: 封印可以是同一次變更的兩個動作，但也可以差一輪（收尾者補封），留一格不必來回。
_SEAL_TAIL_MAX = 1

# ---------------------------------------------------------------- 封印表自己的完整性
# 🔴 立案（`DEF-101-997`，R82 複審 QA B1 當回合以 `mock.patch` 記憶體內注入實測）：
# 上面那組封印只判「封印**比史料長**」（`len(sealed) > len(history)`），對「封印**比上一
# 次短**」零判準，而 `_SEAL_TAIL_MAX = 1` 又剛好讓「砍掉最後一格」之後的尾巴＝1 合法。
# 於是把超長列上限 85 放寬成 90 只要改**兩行**就全綠：
#   · A（只改史料＋常數，封印完整）  → `problems=1` → 紅 ✅（判準本來就抓得到）
#   · B（同時把封印砍成 `(105,101,98)`）→ `problems=0` → **綠** ❌，一行的差別就繞過去了
# 而守它的測試把 `_SEAL = (105, 101, 98, 85)` **硬編成第三份複本**、從不與本表對帳
# ⇒ 封印被改動時那 7 支全過。`sealed_prefix_problems()` 的紅燈訊息逐字寫著「若你正打算改
# `_SEALED_HISTORY_PREFIXES` 讓它變綠：那正是本判準要擋的動作」——**那句話當時零觀測者**，
# 與它所治的 `DEF-101-993` 一模一樣。同一個主題，第三次。
#
# 形狀刻意照抄 repo 內已經付過學費的那一組（`tools/tests/test_adr_xplat001_c1c2_lock.py`
# 的 `_REPIN_LOG_FROZEN_PREFIX_LEN` ＋ `_REPIN_LOG_HISTORY_SHA256`）：**一個只准上升的
# 長度 ＋ 一個內容摘要**。刻意**不**再開第三份數字複本——那只會讓下一輪再問一次「誰守
# 封印的封印」；摘要是單向的，看得出被動過、抄不回去。
#
# 🔴 誠實劃界（這一層買到的是什麼、買不到什麼）：它是 tamper-**evident**，不是
# tamper-proof。同一個 commit 內把封印、長度、摘要三者一起改仍然會綠——而那正是設計：
# 遞迴必須停在某處，本層讓它停在「這個動作不可能是手滑，而且一定會以一行改掉的不透明
# 常數出現在 diff 裡」。**請不要為此再加第四層。**
def seal_table_digest(seals: Mapping[str, tuple[int, ...]]) -> str:
    """封印表的正規化摘要（鍵排序 → 逐字序列化 → sha256 前 16 碼）。純函式。

    鍵排序用的是 `str` 的序，與平台無關（同 `DEF-101-613` 對指紋可攜性的既有紀律）。
    """
    blob = "\n".join(
        f"{k}={','.join(str(v) for v in seals[k])}" for k in sorted(seals))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


#: 封印表的**總長度下限**（＝三條封印的元素數總和）。只准上升：史料長大時封印跟著長，
#: 這個數字就跟著調上去；任何讓它變小的動作都是「把封印砍短」。
#: 🔴 輪號不寫進本段散文，理由同上；錨＝磁碟上查得到的 `archive_67`。重釘 **28 → 30**：
#: `OVERSIZE_ROW_CEILING`／`OVERSIZE_ROW_EXCESS_CEILING` 兩條封印各延長一格
#: （8+15+7=30），當回合實測值直接填入。
_SEAL_TOTAL_MIN_LEN = 30

#: 封印表的內容摘要（`seal_table_digest(_SEALED_HISTORY_PREFIXES)` 的當回合實測值）。
#: 追加新值到某條封印是合法動作，但必須在**同一次變更內**把上面那個長度與這個摘要一起
#: 重釘——不重釘即紅，故「改封印」在結構上不可能是無聲的。
#: 🔴 帳本收斂輪（archive_67）重釘（封印延長導致摘要改變，當回合 `seal_table_digest()` 實測值）。
_SEAL_TABLE_SHA256 = "07d8f299cce96025"


def seal_table_problems(
    seals: Mapping[str, tuple[int, ...]] | None = None,
    *,
    total_min_len: int | None = None,
    digest: str | None = None,
) -> list[str]:
    """封印表自己的完整性（回空＝合規）。純函式，紅綠由構造輸入自證。

    三向：① `[封印變短]` 總長度低於下限——這就是 QA B1 報的那條繞道；
    ② `[基準過時]` 總長度高於下限（封印長大了卻沒把下限一起調上去 ⇒ 那段餘裕就是日後
    無聲砍回去的破口，同 `_SEAL_TAIL_MAX` 的理由）；③ `[封印被改寫]` 內容摘要對不上。

    預設值刻意在**呼叫當下**才讀模組屬性（不是 def 期的預設引數）：`mock.patch.object`
    注入本模組常數時判準必須跟著變，否則注入測試證明的是一份快照而不是活體。
    """
    seals = _SEALED_HISTORY_PREFIXES if seals is None else seals
    total_min_len = _SEAL_TOTAL_MIN_LEN if total_min_len is None else total_min_len
    digest = _SEAL_TABLE_SHA256 if digest is None else digest
    problems: list[str] = []
    total = sum(len(v) for v in seals.values())
    if total < total_min_len:
        problems.append(
            f"[封印變短] 封印表總長度 {total} < 下限 {total_min_len}——有封印被砍短或整筆"
            f"刪掉。現況：{ {k: len(v) for k, v in sorted(seals.items())} }。"
            f"🔴 若你是為了讓 `sealed_prefix_problems()` 變綠而砍它：那正是本判準要擋的"
            f"動作，修法是把**史料**補回去，不是把封印削到對得上")
    elif total > total_min_len:
        problems.append(
            f"[基準過時] 封印表總長度 {total} > 下限 {total_min_len}——封印長大了卻沒把"
            f"下限一起調上去，那段餘裕就是日後把封印無聲砍回去的破口。"
            f"請把 `_SEAL_TOTAL_MIN_LEN` 改成 {total}")
    got = seal_table_digest(seals)
    if got != digest:
        problems.append(
            f"[封印被改寫] 封印表摘要 {got} != 釘住的 {digest}——`_SEALED_HISTORY_PREFIXES`"
            f" 被動過了。**在尾端追加**新值是合法動作，此時請在同一次變更內把"
            f" `_SEAL_TOTAL_MIN_LEN` 與 `_SEAL_TABLE_SHA256` 一起重釘（新值＝{got}）。"
            f"🔴 若你是在**改寫或砍短**已釘過的值：那是本判準存在的唯一理由，"
            f"重釘摘要讓它變綠等於自己把鎖打開，請改回去")
    return problems


def sealed_prefix_problems(
    name: str, sealed: tuple[int, ...], history: tuple[int, ...]
) -> list[str]:
    """史料前綴不可變（回空＝合規）。純函式，紅綠由構造輸入自證。

    三向：① 封印不得比史料長（史料被砍短＝改寫的一種）；② 史料前 `len(sealed)` 項必須
    與封印**逐字相等**；③ 未封印的尾巴不得超過 `_SEAL_TAIL_MAX`（否則封印會隨輪次自己
    失效——它只罩得住落地當下那幾個值）。

    只准延長：`history` 在尾端追加不需要動 `sealed`，故本判準**不會**要求任何人把常數
    改成當回合的實測值（那正是 `DEF-101-993` 記載的幫兇形態）。
    """
    if len(sealed) > len(history):
        return [
            f"{name}_HISTORY 只剩 {len(history)} 項，比封印的 {len(sealed)} 項還短"
            f"——史料被砍短了。封印：{sealed}；現況：{history}。"
            f"🔴 修法是把史料補回去，**不是**把封印砍短"
        ]
    problems = [
        f"{name}_HISTORY 第 {i} 項由封印的 {want} 被改寫成 {got}"
        f"（封印：{sealed}；現況：{history[:len(sealed)]}）"
        f"——已釘過的值不得回填、不得改寫，這條棘輪只准在**尾端**延長。"
        f"🔴 若你正打算改 `_SEALED_HISTORY_PREFIXES` 讓它變綠：那正是本判準要擋的動作"
        for i, (want, got) in enumerate(zip(sealed, history))
        if want != got
    ]
    tail = len(history) - len(sealed)
    if tail > _SEAL_TAIL_MAX:
        problems.append(
            f"{name}_HISTORY 有 {tail} 項未封印（上限 {_SEAL_TAIL_MAX}）："
            f"{history[len(sealed):]}。請把 {history[len(sealed):len(history) - 1]} "
            f"追加進 `_SEALED_HISTORY_PREFIXES[\"{name}\"]`——未封印的值日後可被無聲改寫，"
            f"封印不跟著長就等於它只罩得住落地當下那幾筆")
    return problems


def ratchet_history_problems(
    name: str, history: tuple[int, ...], current: int
) -> list[str]:
    """shrink-only 棘輪的通用觀測者（回空＝合規）。

    三向：① 序列非空（沒有起算錨就無從判方向）；② 單調**不增**（任一段上升即紅，並逐字
    指名是哪一段、升了多少）；③ 末元素 == 現行常數（改了常數卻不追加史料 ⇒ 史料會退化成
    裝飾品，方向判準等於不存在）。

    為何是「不增」而不是「嚴格遞減」：沒動到帳本的一輪，重釘到同一個數是**正確**動作，
    判成紅會逼人去製造假的下降——那比沒有鎖更糟。

    刻意**不留豁免出口**：真的必須讓帳本長大時，合法動作是判準④ 訊息自己寫的那一條
    （同一次變更內把別的列縮回等量以上），而不是把棘輪往上轉。
    """
    if not history:
        return [f"{name}_HISTORY 是空的：shrink-only 棘輪沒有起算錨就無從判方向"]
    problems = [
        f"{name} 的重釘史第 {i} → {i + 1} 段由 {a} **上升**到 {b}（+{b - a}）"
        f"——這條棘輪只准往下改、零成長容忍。合法動作是在同一次變更內把別的列縮回等量"
        f"以上（判準④ 訊息自己指名的出口），不是把上限往上轉。"
        f"🔴 若你是在收拾別人造成的成長：那筆成長本身才是要被擋下的東西，"
        f"把它記在這裡等於讓棘輪替它背書"
        for i, (a, b) in enumerate(zip(history, history[1:]))
        if b > a
    ]
    if history[-1] != current:
        problems.append(
            f"{name} 現值 {current} 與重釘史末元素 {history[-1]} 不符：改了常數就必須把"
            f"**當回合實測值**追加進 {name}_HISTORY，否則那條史料是裝飾品")
    return problems


def ratchet_direction_problems(handover_ceiling: int) -> list[str]:
    """三條棘輪的方向鎖總入口（`DEF-101-993`）。

    刻意**只吃常數、不吃帳本**（理由同 `grandfather_ceiling_problems()`）：這是對原始碼
    常數的斷言，換一本帳本不該能繞過它 ⇒ 呼叫端必須在 `main()` 內**無條件**執行。
    也刻意**不**混進 `oversize_row_problems()`：那支的注入測試會把常數 mock 成別的值，
    混進去等於讓判準的比較對象隨被它所判的動作而變（R75 已立的鐵律）。

    R82（`DEF-101-995`）：每條史料另加一道**前綴封印**（`sealed_prefix_problems`）。
    方向鎖只判「相鄰段不上升 ＋ 末元素對得上現值」，對「史料自己被改寫／被砍短」零判準
    ⇒ 兩者缺一都能被繞過，故一律成對執行。

    R82 複審 QA B1（`DEF-101-997`）：再加第三道 `seal_table_problems()`——前兩道合起來
    仍可被「把封印砍短一格」整個繞過（實測見該函式上方）。三道一律成對執行，且第三道
    刻意**放在迴圈外**：它判的是整張封印表，不是某一條史料。
    """
    histories = (
        ("OVERSIZE_ROW_CEILING", OVERSIZE_ROW_CEILING_HISTORY,
         _idx.OVERSIZE_ROW_CEILING),
        ("OVERSIZE_ROW_EXCESS_CEILING", OVERSIZE_ROW_EXCESS_CEILING_HISTORY,
         _idx.OVERSIZE_ROW_EXCESS_CEILING),
        ("_UNPINNED_HANDOVER_CEILING", UNPINNED_HANDOVER_CEILING_HISTORY,
         handover_ceiling),
    )
    problems: list[str] = []
    for name, history, current in histories:
        problems += ratchet_history_problems(name, history, current)
        problems += sealed_prefix_problems(
            name, _SEALED_HISTORY_PREFIXES.get(name, ()), history)
    return problems + seal_table_problems()


def expiring_oversize_waivers(move_ids: list[str], ledger_text: str) -> dict:
    """本次歸檔會讓哪幾筆**超長列豁免**過期，以及三個常數該下修到多少。

    🔴 立案（`DEF-101-977`，R81 開場實際發生）：`--archive-num 64` 把 3 列搬離主檔，
    `OVERSIZE_ROW_GRANDFATHERED` 的那 3 筆當場過期、判準②轉紅——而歸檔器**既不偵測也不
    提示**，要等下一個人跑 `check_defect_log_crossref.py` 才知道。於是「每輪歸檔都復發、
    每輪都手動修」：一個歸檔器自己造成、卻由別人發現的紅。

    刻意是**純讀計算**：不改任何判準、不寫任何檔，因此不可能製造新的紅；它只是把一個
    今天已經會發生的後果，從「下一個人的意外」提前成「這一個人的預告」。

    回傳鍵：`expiring`（本次會過期的豁免 ID，已排序）、`new_ceiling`／`new_excess`
    （搬後**實測**應下修到的值）。
    """
    moved = set(move_ids)
    remaining = "\n".join(
        ln for ln in ledger_text.split("\n")
        if not any(ln.startswith(f"| {i} |") for i in moved)
    )
    over = {i: n for i, n in _idx.row_bytes(remaining).items()
            if n > _idx.ROW_MAX_BYTES}
    return {
        "expiring": sorted(_idx.OVERSIZE_ROW_GRANDFATHERED - set(over)),
        "new_ceiling": len(over),
        "new_excess": sum(n - _idx.ROW_MAX_BYTES for n in over.values()),
    }


def index_bullet(dest: Path, move_ids: list[str], orig_bytes: int, released: int,
                 archive_bytes: int, needs_ack: list[dict], note: str,
                 excluded: list[dict] = ()) -> str:
    """組出該次歸檔的索引 bullet（體例照 archive_30 那條；R69 起寫進歸檔索引檔）。

    載明：建立時點／筆數／ID 清單／bytes 變化／判準④ 攔下哪幾筆／操作備註。

    🔴 刻意**不寫「搬後主檔 N bytes」**：本 bullet 自己就要寫進主檔，寫上去之前算不出
    搬後實數（循環依賴），而用「先算再插」湊一個數字必然差在 bullet 自身長度上。
    故只寫「搬前」與「釋出」（兩者在此刻皆為確定值），搬後實數指向工具實跑——這與帳本
    「不對餘裕做定性宣稱／不快照可漂移數字」的既有紀律同向（R59 SA-R59-P2-1）。
    """
    held = "、".join(f"`{v['id']}`" for v in needs_ack) or "（無）"
    # DEF-101-811：`--only`／`--keep` 的排除必須**留痕**，否則它就是一個無聲的少搬入口。
    skipped = "、".join(f"`{v['id']}`" for v in excluded) or "（無）"
    return (
        f"> - **`{dest.name}`**（`tools/archive_defect_log.py --apply` 於 "
        f"{_date.today().isoformat()} 建立，{archive_bytes} bytes）："
        f"**{len(move_ids)} 筆已結列**逐字搬移"
        f"（{'／'.join(move_ids)}）。"
        f"**位元組變化**：搬前主檔 {orig_bytes} bytes、本次釋出 {released} bytes"
        f"（搬後實數以 `python tools/check_defect_log_crossref.py` 實跑為權威——本 bullet"
        f"自身的寫入也計入主檔體積，故不在此寫死搬後數字）。"
        f"**判準④ 攔下、刻意未加 `--ack-handoff` 而留在主檔者**：{held}。"
        f"**判準全過但以 `--only`／`--keep` 具名排除、刻意留在主檔者**：{skipped}。"
        f"**本次操作備註**：{note}"
    )


def rotation_effect_report(plan: dict, released: int) -> str:
    """把本次輪替**對下游判準的兩個副作用**組成一段可印的文字（純函式）。

    兩者共通的病：歸檔器改變了下游判準的輸入，卻讓下游的人去發現後果。格式化住這裡而不是
    住 `archive_defect_log.py`，理由同本檔檔頭（那支檔的 raw-line 棘輪餘裕近乎零）。
    """
    x, y, z = net_volume_triple(released, plan["index_bullet_bytes"])
    verdict = ("（主檔淨變化為負＝這一次真的釋出了容量）" if z < 0
               else "（🔴 主檔淨變化**不為負**＝這一次輪替沒有真的釋出容量，"
                    "`DEF-101-676` 講的正是這件事）")
    out = [f"\n📐 輪替淨額（DEF-101-676）：本次釋出 {x} bytes／新增索引 {y} bytes"
           f"／主檔淨變化 {z} bytes{verdict}",
           "   ⚠️ Y 於 `--plan` 為**估算**（archive 檔名與備註尚未定），`--apply` 時以實際"
           "寫入的 bullet 為準；Z=Y−X 的算式關係兩處相同"]
    w = plan["waiver_expiry"]
    if not w["expiring"]:
        out.append("\n📐 超長列豁免（DEF-101-977）：本次歸檔**不會**讓任何一筆豁免過期")
        return "\n".join(out)
    out.append(
        f"\n🔴 超長列豁免過期預告（DEF-101-977）：本次會搬走 {len(w['expiring'])} 筆仍列在"
        f" `OVERSIZE_ROW_GRANDFATHERED` 的 ID ⇒ 搬完之後 `check_defect_log_crossref.py`"
        f" 的判準② **當場轉紅**（不是被本工具弄壞的紅，是本工具造成、卻由下一個人發現的"
        f"紅）。同一次變更內請一併改掉："
        f"\n   · 自 `OVERSIZE_ROW_GRANDFATHERED` 移除：{'、'.join(w['expiring'])}"
        f"\n   · `OVERSIZE_ROW_CEILING` 下修為 {w['new_ceiling']}"
        f"\n   · `OVERSIZE_ROW_EXCESS_CEILING` 下修為 {w['new_excess']}"
        f"\n   · 兩條 `*_HISTORY` 各追加上面那個實測值（方向鎖，只准往下）")
    return "\n".join(out)


def net_volume_triple(released: int, index_bytes: int) -> tuple[int, int, int]:
    """輪替的**淨額**三數字：(X 本次釋出, Y 本次新增索引, Z 主檔淨變化＝**Y−X**)。

    🔴 立案（`DEF-101-676`）：帳本輪替被當成「買到餘裕」的動作，但每次 `--apply` 都會把
    一條索引 bullet 寫回主檔家族 ⇒ 釋出與新增同時發生，而**只有釋出那一半被印出來**。
    該列自己給的務實下一步逐字：「讓 `--plan` 同時印出『本次釋出 X bytes／新增索引
    Y bytes／淨 Z』，**淨值長期為負才是真的解**」。

    🔴 **符號取自那句話，不是取自「先寫的那個減號」**：Z 是**主檔的淨變化**（負＝主檔真的
    變小了），所以是 `Y − X` 而不是 `X − Y`。本函式第一版寫成 `X − Y` 並把 `z < 0` 標成
    「真的釋出了容量」，方向剛好相反——由本檔的注入測試當場抓到（同 R79「量測器指標可能
    符號相反」的形態：算式看起來對稱，只有把它綁回一句**外部的定性宣稱**才判得出方向）。

    本函式只做算式、不做定性宣稱——「這一輪算不算真的解」是讀者看著 Z 的正負自己判斷的事。
    """
    return released, index_bytes, index_bytes - released
