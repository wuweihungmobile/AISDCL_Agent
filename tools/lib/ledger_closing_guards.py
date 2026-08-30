"""帳本收斂期的兩個機械物：淨額棘輪（①）＋外部阻塞軌（②）。

**為何獨立成一支檔而不是寫進 `check_defect_log_crossref.py`（DEF-200 系列）**：
那支檔是 `SPECIAL_FILES` raw-line shrink-only 棘輪、當回合實測餘裕僅個位數行——本檔的
兩個判準各自需要十餘行才寫得完整（git 讀取、逐列比對、外部軌解析），塞不進去。這正是
`AutoClaude/tools/check_loc_budget.py` 自己指定的第一順位處置（先例：`ledger_rotation.py`
／`ledger_staleness.py`）：把新判準抽成獨立的 `tools/lib/` 模組，caller 只留最小接線。

**與 `check_defect_log_crossref.py` 的耦合方式（刻意用依賴注入、不用互相 import）**：
兩個判準都需要「把一段帳本文字解析成 `{DEF-ID: 狀態分類}`」，而那個解析器
（`_table_layout`／`_row_cells`／`_classify`／`_ROW_RE`／`_ID_RE`）是 `check_defect_
log_crossref.py` 的 SSOT、不得另寫第二份（本 repo 反覆在治的複本型缺陷）。若本檔在自己
的模組頂層 `import check_defect_log_crossref`，而該檔又要在自己的模組頂層 import 本檔
——那是真的循環 import。解法是**把解析器當函式參數傳進來**（呼叫端傳自己已有的
`_table_layout`／`_row_cells`／`_classify`／`_ROW_RE`／`_ID_RE`），本檔完全不知道也不需要
知道那些函式從哪個模組來——這樣呼叫端只需要一行 import＋一次呼叫，本檔也不必背負「哪天
gate 模組改了內部實作」的耦合。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

from lib import defect_ledger_index as _idx

# ============================================================== 機械物① 淨額棘輪
# 規則：本輪新增未結列數不得超過本輪結案列數（淨額 <= 0）。
#
# 🔴 **warn 還是 fail：本檔選 fail**（PRD 掌舵者裁決點，理由寫在這裡而非事後才補）。
# 本輪（帳本減半收斂期）的顯式目標就是「淨額必須為負」，若本判準只 warn，它在最需要
# 擋線的這一輪反而不會擋——那正是「帳本能不能一直減下去」這件事的核心賭注。選 fail 不會
# 誤傷本輪：本輪淨額已為負（見任務書），所以上線當場是綠的（不阻塞自己）。真正會被擋的是
# **下一輪若是發現輪**（新缺陷被找出來的速度天然快過修復速度）——這正是它的用意：逼那一輪
# 的操作者**明確**選擇逃生口，而不是讓帳本無聲漲回去。
#
# 逃生口＝環境變數 `AUTOSDD_NET_RATCHET_OFF`（比照 CLAUDE.md 既有 hook 逃生口命名慣例：
# `AUTOSDD_GIT_GUARD_OFF`／`AUTOSDD_CONTEXT_GUARD_OFF`）。**刻意不做「行內 `# xxx-ok:` 註解」
# 那種逃生口**：本判準的判定對象是「一整份帳本這一輪 vs 上一輪 commit」的差集，不是某一行
# 指令字串——沒有「這一行」可以掛註解。環境變數天生可稽核：它必須在啟動當下就設好、會留在
# CI job 設定或 commit 訊息裡，不像行內註解可以事後補一行就讓歷史紀錄看起來合規。
#
# 🔴 **誠實劃界（fail-open 方向）**：`git show HEAD:<path>` 在下列情況下必然取不到
# 上一輪基準，此時本判準**放行**（回空清單），不假造一個「零未結列」的基準去逼出一個
# 假紅：
#   · 淺 clone（`git show` 對歷史深度不足的 commit 可能仍失敗，視 clone 深度而定）；
#   · 全新 repo／該檔案是本次變更才新增進版本控制（`HEAD:<path>` 查無此路徑）；
#   · 非 git 工作樹、或 `git` 執行檔不存在。
# 這些都是「量不到基準」而非「量到基準且它是零」，兩者的正確回應不同——後者才該真的比較。
AUTOSDD_NET_RATCHET_OFF = "AUTOSDD_NET_RATCHET_OFF"


def _git_show_head_text(repo_root: Path, path: Path) -> str | None:
    """`git show HEAD:<path>` 的內容；任何原因讀不到一律回 `None`（fail-open，見上）。

    刻意用 `subprocess.run` 而非 `git show` 的 shell 管線：讀 rc 不接管線是本 repo 的
    既有鐵律（CLAUDE.md 鐵律六），這裡直接讀 `CompletedProcess.returncode`，不經任何殼。
    """
    try:
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"HEAD:{rel}"],
            capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace")
    except OSError:
        return None
    return proc.stdout if proc.returncode == 0 else None


TableLayoutFn = Callable[[str], "tuple[int, int, int] | None"]
RowCellsFn = Callable[[str], list[str]]
ClassifyFn = Callable[[str], "str | None"]


def _warn_fail_open(reason: str) -> None:
    """淨額棘輪 fail-open 時的**永遠可見**警告（收斂波 R-02 修復）。

    修復前：量不到基準（非 git 工作樹／git 不存在／HEAD 查無此路徑…）時本判準
    靜默回空清單，stdout 與 stderr 皆為空——這道棘輪無聲失能且無人知道，與同檔機械物
    ②「外部阻塞筆數永遠可見」（`print_external_blocked_count`）的紀律自相矛盾。
    比照該函式的設計：不阻斷（fail-open 的決策不變），但必須出聲。
    """
    print(f"⚠️  淨額棘輪 fail-open：{reason}", file=sys.stderr)


def _parse_status(
    text: str, table_layout: TableLayoutFn, row_cells: RowCellsFn,
    classify: ClassifyFn, row_re: re.Pattern[str], id_re: re.Pattern[str],
) -> dict[str, str | None] | None:
    """把一段帳本表格文字解析成 `{DEF-ID: 狀態分類}`；查無合格表頭回 `None`。

    演算法逐字比照 `check_defect_log_crossref._load_ledger_status()`（狀態欄由
    **表頭**定位、絕不取 `cells[-1]`），差別只在解析器由呼叫端注入——見模組 docstring
    「與 check_defect_log_crossref.py 的耦合方式」。
    """
    layout = table_layout(text)
    if layout is None:
        return None
    ncols, id_idx, status_idx = layout
    out: dict[str, str | None] = {}
    for line in text.splitlines():
        if not row_re.match(line):
            continue
        cells = row_cells(line)
        if id_idx >= len(cells) or not id_re.fullmatch(cells[id_idx]):
            continue
        out[cells[id_idx]] = classify(cells[status_idx]) if len(cells) == ncols else None
    return out


def net_new_vs_closed_problems(
    repo_root: Path, ledger_path: Path, curr_ledger: dict[str, str | None],
    table_layout: TableLayoutFn, row_cells: RowCellsFn, classify: ClassifyFn,
    row_re: re.Pattern[str], id_re: re.Pattern[str],
) -> list[str]:
    """淨額棘輪：本輪新增未結列數不得超過本輪結案列數（回空＝合規或無法判定，見上）。

    判準＝比對「`git show HEAD` 的帳本未結 ID 集合」與「`curr_ledger`（呼叫端已解析好的
    工作樹現況）」的差集。`curr_ledger` 由呼叫端傳入而不是本函式自己重讀磁碟：呼叫端
    （`check_defect_log_crossref.main()`）已經算過一次，重複解析同一份帳本兩次除了浪費
    也違反「同一件事只該有一個答案」的既有紀律。
    """
    if os.environ.get(AUTOSDD_NET_RATCHET_OFF):
        return []
    prev_text = _git_show_head_text(repo_root, ledger_path)
    if prev_text is None:
        _warn_fail_open(
            f"讀不到 `git show HEAD:{ledger_path.name}`（淺 clone／檔案本次才新增進版控／"
            "非 git 工作樹／git 執行檔不存在，三者皆可能），本輪不判斷淨額棘輪")
        return []
    prev_status = _parse_status(prev_text, table_layout, row_cells, classify, row_re, id_re)
    if prev_status is None:
        _warn_fail_open(f"HEAD 版 {ledger_path.name} 查無合格表頭，本輪不判斷淨額棘輪")
        return []
    unresolved = _idx.UNRESOLVED_CLASSES
    prev_unresolved = {i for i, c in prev_status.items() if c in unresolved}
    curr_unresolved = {i for i, c in curr_ledger.items() if c in unresolved}
    newly_added = sorted(curr_unresolved - prev_unresolved)
    newly_closed = sorted(prev_unresolved - curr_unresolved)
    net = len(newly_added) - len(newly_closed)
    if net <= 0:
        return []
    return [
        f"淨額棘輪違反：本輪新增未結 {len(newly_added)} 筆 > 結案 {len(newly_closed)} 筆"
        f" ⇒ 淨增 {net} 筆（帳本正在變胖，不是變瘦）。"
        f"新增：{'、'.join(newly_added)}；結案：{'、'.join(newly_closed) or '（無）'}。"
        f"合法出口：① 本輪再多結掉 {net} 筆讓淨額 <= 0；② 若本輪本質是「發現輪」"
        f"（新缺陷的發現速度本來就快過修復），顯式設定環境變數 "
        f"`{AUTOSDD_NET_RATCHET_OFF}=1` 並在 commit 訊息／輪次紀錄寫明理由——"
        f"該逃生口刻意用環境變數而非行內註解：本判準比的是整份帳本前後兩輪的差集，"
        f"沒有單一一行可以掛豁免"
    ]


# ============================================================== 機械物② 外部阻塞軌
# 新表：`docs/06_quality/AutoSDD_External_Blocked_Log.md`。存在理由：把「真缺陷、可修」
# （A 類）與「卡在外部世界、機械上暫時做不了任何事」（E 類）分軌，讓主帳本的未結列數
# （`UNRESOLVED_ROWS_WARN`／`FAIL`）量到的是「我們自己欠的債」，不被 E 類稀釋或膨脹。
#
# 🔴 「具名阻塞源限枚舉」是防偽裝的唯一機械物（見任務書）：判準要嚴——自由文字一律 fail，
# 沒有「大致像」這種模糊地帶。`其他-\S+` 允許擴充新的阻塞源類別，但仍要求**具名**
# （`其他` 後必須緊跟一個非空白 token，不能是裸「其他」當萬用桶）。
EXTERNAL_BLOCKED_LOG_NAME = "AutoSDD_External_Blocked_Log.md"
#: 🔴 收斂波 R-01 修復：原正則只錨頭（`^…`）未錨尾，`.match()` 對「合法字首＋任意
#: 自由文字」照樣命中（實測：`上游套件其實是我懶得修這個真缺陷，隨便掰的理由` 全數放行）
#: ——這是「防止把 A 類真缺陷偽裝成 E 類混出警戒線」的唯一機械物，不成立等於防線不存在。
#: 改用 `fullmatch()`（等效於頭尾雙錨）：整個儲存格必須**恰好**是四種合法形態之一。
NAMED_BLOCKER_SOURCE_RE = re.compile(
    r"(GitHub Actions 帳務|Windows 實機|上游套件|其他-\S+)"
)
# ---------------------------------------------- 機械物②-b 結構性長債軌（同判準、scoped 枚舉）
# 掌舵者 2026-08-30 核准分軌（存證＝docs/04_planning/AutoSDD_TechDebt_Paydown_Playbook.md
# §6 第 3 條）：把「跨輪工程／內部授權」型長債自主帳本未結列分軌出去，讓未結列數量到的
# 是「單輪可修的債」。判準**共用** `external_blocked_log_problems()`（依賴注入 log_name／
# source_re），不另寫第二份三向判準——差異只在枚舉值的射程：
# 🔴 **兩軌枚舉刻意互斥**（互為後門是要防的形態）：外部軌四值不匹配 `結構性長債-\S+`、
# 長債 token 也不匹配外部軌四形態，任何一筆想「換一本帳混出警戒線」都會在該軌被 fullmatch 拒絕。
STRUCTURAL_DEBT_LOG_NAME = "AutoSDD_Structural_Debt_Log.md"
STRUCTURAL_DEBT_SOURCE_RE = re.compile(r"結構性長債-\S+")
#: 成長棘輪：長債軌不得成為「比外部軌更好用的後門」。新列必須先有掌舵者具名裁決，
#: 裁決落款後才准把本常數重釘為新值（重釘與新列須在同一次變更內，理由寫在裁決存證處）。
_STRUCTURAL_DEBT_MAX_ROWS = 7
_EXT_ROW_RE = re.compile(r"^\|\s*(DEF-\d+-\d+)\s*\|")
_EXT_CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")
_DEF_ID_RE = re.compile(r"DEF-\d+-\d+")
#: 欄序＝任務書逐字指定：`DEF-ID | 具名阻塞源 | 阻塞起始日 | 解鎖條件（可機械查） | 最近複查日`。
#: 這是**本檔自己定義的新表**（非既有帳本格式），故用固定位置索引而非表頭動態定位——
#: 沒有歷史欄序漂移的包袱，多一層動態定位只是多一份不必要的複雜度（Rule 2）。
_COL_ID, _COL_SOURCE, _COL_START, _COL_UNLOCK, _COL_REVIEW = 1, 2, 3, 4, 5
_EXPECTED_CELLS = 7  # 首尾空片段 + 5 個資料欄

#: 「最近複查日」逾期未更新的警戒天數（**warn，非 fail**——見任務書「防止外部軌變成永久
#: 垃圾桶」，但外部阻塞源本來就是我們不控制的東西，硬擋只會逼人把日期改成今天而不解決
#: 真正的問題）。取 14 天：`git log` 對主帳本的 commit 密度顯示本 repo 幾乎每天都有一輪
#: 整合／收斂動作（見本任務執行當回合實測：近 60 天內僅 4 天無 commit），14 天已是
#: 「連續兩三輪都沒人回頭看一眼」的保守上界，而不是「一週忘了看一次」就緊張兮兮地報警。
STALE_REVIEW_DAYS = 14


def _ext_rows(text: str) -> list[tuple[int, list[str]]]:
    """外部阻塞軌表格的資料列：`(1-based 行號, 全部切片含首尾空片段)`。"""
    out: list[tuple[int, list[str]]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if _EXT_ROW_RE.match(line):
            out.append((lineno, [c.strip() for c in _EXT_CELL_SPLIT_RE.split(line)]))
    return out


def external_blocked_log_problems(
    text: str, main_unresolved_ids: set[str], today: date | None = None, *,
    log_name: str = EXTERNAL_BLOCKED_LOG_NAME,
    source_re: re.Pattern[str] = NAMED_BLOCKER_SOURCE_RE,
) -> tuple[list[str], list[str]]:
    """外部阻塞軌／結構性長債軌共用的三向判準；回傳 `(fail 清單, warn 清單)`（純函式）。

    ① 具名阻塞源限枚舉（`source_re.fullmatch`，R-01 教訓：只錨頭不錨尾＝防線不存在）
       ——防「把 A 類偽裝成 E 類／長債混出警戒線」。枚舉射程由呼叫端注入：外部軌＝
       `NAMED_BLOCKER_SOURCE_RE`（預設），長債軌＝`STRUCTURAL_DEBT_SOURCE_RE`，兩軌互斥。
    ② 交叉鎖——同一 DEF-ID 不得同時出現在主帳本未結列與本表（出現即 fail：那代表這筆
       缺陷「既算我們欠的債、又宣稱不算」，兩本帳各說各話）。
    ③ 「最近複查日」逾期（`STALE_REVIEW_DAYS`）——warn，不 fail（見上）。
    欄數不合（`_EXPECTED_CELLS`）或日期格式無法解析視為資料本身壞掉，一律 fail：
    壞掉的資料沒有「這一列到底過期了沒」的答案，強行判讀等同瞎猜。
    """
    today = today or date.today()
    fails: list[str] = []
    warns: list[str] = []
    for lineno, cells in _ext_rows(text):
        if len(cells) != _EXPECTED_CELLS:
            fails.append(
                f"{log_name}:{lineno}：該列切出 {len(cells)} 個切片 "
                f"≠ 表頭 {_EXPECTED_CELLS} 個（欄位定位失效，本列不判讀）")
            continue
        def_id = cells[_COL_ID]
        source = cells[_COL_SOURCE]
        review = cells[_COL_REVIEW]
        if not source_re.fullmatch(source):
            fails.append(
                f"{log_name}:{lineno} {def_id}：阻塞源 {source!r} 不是"
                f"具名枚舉值（本表合法形態＝fullmatch r'{source_re.pattern}'；"
                "兩軌枚舉刻意互斥，不得拿另一軌的值當後門）——自由文字一律 fail，"
                "這是防止把可修的真缺陷偽裝成阻塞／長債混出未結列警戒線的唯一機械物")
        if def_id in main_unresolved_ids:
            fails.append(
                f"{log_name}:{lineno} {def_id}：同時出現在主帳本"
                f"未結列與本表（{log_name}）——兩本帳對同一筆缺陷各說各話。"
                "若已分軌，主帳本該列應收斂為指向本表的索引，不應仍以未結狀態留在主帳本")
        try:
            days = (today - date.fromisoformat(review)).days
        except ValueError:
            fails.append(
                f"{log_name}:{lineno} {def_id}：「最近複查日」"
                f"{review!r} 不是可解析的 ISO 日期（YYYY-MM-DD）")
            continue
        if days > STALE_REVIEW_DAYS:
            warns.append(
                f"{log_name}:{lineno} {def_id}：最近複查日 {review} "
                f"距今 {days} 天 > {STALE_REVIEW_DAYS} 天，請確認阻塞是否仍成立"
                "（分軌帳本若沒人回頭看，會變成永久垃圾桶）")
    return fails, warns


def structural_debt_growth_problems(
    count: int, ceiling: int = _STRUCTURAL_DEBT_MAX_ROWS,
) -> list[str]:
    """長債軌成長棘輪（純函式；`count > ceiling` 即 fail，回空＝合規）。

    防的形態＝長債軌變成「比外部軌更好用的後門」：外部軌有 14 天複查與枚舉互斥擋著，
    長債軌若可無聲加列，未結列警戒線就多了一個免裁決的洩壓口。
    """
    if count <= ceiling:
        return []
    return [
        f"{STRUCTURAL_DEBT_LOG_NAME}：登記 {count} 筆 > 成長棘輪上限 {ceiling}。"
        "長債軌不是免裁決的洩壓口：新增一列必須先取得**掌舵者具名裁決**"
        "（存證比照 AutoSDD_TechDebt_Paydown_Playbook.md §6 的落款體例），"
        "裁決落款後才准把 _STRUCTURAL_DEBT_MAX_ROWS 重釘為新值（重釘與新列同一次變更）"
    ]


def external_blocked_ids(text: str) -> list[str]:
    """外部阻塞軌目前登記的 DEF-ID 清單（用於 `--unresolved-count` 的「移出去了幾筆」）。

    欄數不合的壞列不計入——那種列連自己是哪個 ID 都定位不到，硬算進去只會製造
    另一個對不上帳的數字。
    """
    return sorted(cells[_COL_ID] for _, cells in _ext_rows(text) if len(cells) == _EXPECTED_CELLS)


def _read_track_log(quality_dir: Path, name: str = EXTERNAL_BLOCKED_LOG_NAME) -> str:
    path = quality_dir / name
    return path.read_text(encoding="utf-8-sig") if path.exists() else ""


def print_external_blocked_count(quality_dir: Path) -> None:
    """`--unresolved-count` 的補充輸出：兩軌筆數必須永遠可見（任務書明講「不可以讓它
    悄悄消失」）——本函式即那句話的機械化，由 caller 在印主帳本未結數的同一個入口呼叫。
    外部軌那一行的字面**逐字不變**（既有測試字面斷言），長債軌比照格式另起一行。
    """
    ids = external_blocked_ids(_read_track_log(quality_dir))
    print(f"外部阻塞軌（{EXTERNAL_BLOCKED_LOG_NAME}，不計入未結列 warn/fail 分母）："
          f"{len(ids)} 筆" + (f"｜{'、'.join(ids)}" if ids else ""))
    sd_ids = external_blocked_ids(_read_track_log(quality_dir, STRUCTURAL_DEBT_LOG_NAME))
    print(f"結構性長債軌（{STRUCTURAL_DEBT_LOG_NAME}，不計入未結列 warn/fail 分母）："
          f"{len(sd_ids)} 筆" + (f"｜{'、'.join(sd_ids)}" if sd_ids else ""))


# ============================================================ 兩個判準的統一入口
def closing_round_problems(
    repo_root: Path, ledger_path: Path, curr_ledger: dict[str, str | None],
    table_layout: TableLayoutFn, row_cells: RowCellsFn, classify: ClassifyFn,
    row_re: re.Pattern[str], id_re: re.Pattern[str],
) -> list[str]:
    """機械物①②的單一呼叫入口（caller 只需一次 import＋一次呼叫，見模組 docstring）。

    ③（外部阻塞軌 warn）在此**直接印出**而不是回傳給 caller 再印：caller
    （`check_defect_log_crossref.py`）的 raw-line 棘輪餘裕已耗盡，多印一個 for 迴圈都嫌貴；
    本函式改為自己 side-effect 印 warning，只把 fail 級問題回傳——這是為了配合 caller 的
    LOC 限制刻意偏離「回傳、由 caller 印」的既有慣例，故在此明講不是隨手為之。
    """
    problems = list(net_new_vs_closed_problems(
        repo_root, ledger_path, curr_ledger, table_layout, row_cells, classify, row_re, id_re))
    ext_text = _read_track_log(ledger_path.parent)
    unresolved = _idx.UNRESOLVED_CLASSES
    main_unresolved = {i for i, c in curr_ledger.items() if c in unresolved}
    fails, warns = external_blocked_log_problems(ext_text, main_unresolved)
    # 長債軌跑**同一支**三向判準（scoped source_re）＋成長棘輪（見機械物②-b 常數區）。
    sd_text = _read_track_log(ledger_path.parent, STRUCTURAL_DEBT_LOG_NAME)
    sd_fails, sd_warns = external_blocked_log_problems(
        sd_text, main_unresolved,
        log_name=STRUCTURAL_DEBT_LOG_NAME, source_re=STRUCTURAL_DEBT_SOURCE_RE)
    sd_fails += structural_debt_growth_problems(len(external_blocked_ids(sd_text)))
    for w in warns + sd_warns:
        print(f"⚠️  {w}", file=sys.stderr)
    problems += fails + sd_fails
    return problems
