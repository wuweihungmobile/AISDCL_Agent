#!/usr/bin/env python3
"""交接項的「機械承接載體」閘門（立案＝缺陷帳本 `DEF-200-188`~`DEF-200-190`）。

## 立案取證（不是推測，是落地當回合實查）

上一輪收輪時把六項工作宣告延後，載體是 commit `f5607fa` 訊息的〈未達成（不塗綠）〉段
（另一筆同型載體＝`772e28b`）。其中「B8 額度術語機械化」被同時宣告「規格已完成」。
逐面實查結果：

  · `grep -rn --include='*.md' -E "額度術語|術語機械化|terminology|glossary" docs/`
    → **rc=1、0 命中**
  · `git log --all --oneline -S "額度術語"` → **0 個 commit**（從未進入任何 tracked 檔）
  · `docs/` 內 `B8` 僅 4 命中，全屬另一套編號體系（`T1-B8`，`improving_35`，2026-06）
  · 帳本家族內指向那一輪的承接列：**0 列**（`_handover_rounds()` 全表統計）

⇒ 那份「已完成的規格」只存在於背景 Workflow 的逐字稿裡（該包刻意唯讀不改檔，以免作廢
   收尾窗口的快照回填），而逐字稿不是 tracked 檔、不進任何閘門的輸入面。

## 為什麼既有機械物守不到（判讀已複驗，非轉述）

`check_defect_log_crossref.orphan_backlog_problems()` 的硬規則② 只走 `_ROW_RE`
（`^\\|\\s*DEF-\\d+-\\d+\\s*\\|`）＝**帳本內的列**。一件只寫在交接散文裡、連 DEF-ID 都沒有
的事，在它的輸入面上結構性不存在。`_CROSSREF_TARGETS` 那一半也接不到：`_scan_target()`
的 `_CLAIM_RE` 只認「DEF-ID 緊接括號」，沒有 ID 就沒有宣稱可比。⇒ 缺的那一格＝**宣稱在
帳本之外、而帳本裡沒有對應承接載體**。

## 兩道判準（都是硬擋，且都**永遠可修**）

**判準①（提交訊息 → 帳本）**：commit 訊息宣告「延後到 R<N>」且 `N ≥ 當前輪` 時，帳本
家族必須有至少一列**未結案**且承接輪次 ≥ N。
  🔴 為何拿 commit 訊息當載體：實測它是那六項**唯一留下的持久痕跡**。`R*_HANDOFF.md`
     這個載體形態只存在於 R74~R90，之後靜默消失了 ⇒ 對那一輪而言，任何只掃 `.md` 的
     判準都會**結構性全綠**，那正是「分母是空的、綠側恆綠」。
  🔴 為何不會永紅（commit 訊息不可改）：本判準要求的**不是改訊息**，而是「帳本裡要有
     承接載體」——寫一列即綠，而寫那一列正是我們想要的動作。不可變的載體 ＋ 可變的解法。
  🔴 誠實劃界：這是**存在性**判準，不是逐項對帳。散文裡的「B8 額度術語機械化」與帳本某
     一列之間沒有可機讀的鍵，逐項比對只能靠語意猜測。它保證「宣告延後 ⇒ 帳本裡至少有
     一個承接載體」，不保證每一項都有自己的列。差別很實在：立案當下是 **0 個**。

**判準②（tracked 交接載體 → 帳本 DEF-ID）**：註冊 glob 內的交接文件，若某一行帶「延後
到 R<N>」（`N ≥ 當前輪`），該行必須指名一個帳本家族內**存在**的 `DEF-\\d+-\\d+`。

**判準③（普查，只出聲）**：印出掃到幾份載體、幾筆前瞻宣稱、`git log` 深度。**「零命中」
必須是可見事件而不是靜默通過**——CI 的 `actions/checkout` 預設 `fetch-depth: 1`，判準①
在淺 clone 上分母會塌成 1 個 commit，那件事必須自己說出來（本地 pre-push 是全深度）。

## 詞彙沿用，不另造

「延後宣稱」的樣式以 `check_defect_log_crossref._HANDOVER_ROUND_RES` 為 SSOT 原樣消費
（含它那個 `(?<![本該此上前系])列` 的敘事引述負向回顧），本檔只**加**三族它沒有的措辭。
反向濾網見 `_narrative_hit()`——存量假紅是量測出來的，不是想像的。

## 自動祖父化的射程邊界（DEF-200-212 訂正；DEF-200-241 治本）

射程判準是「宣告的目標輪 ≥ 當前輪」，前提是**當前輪會隨輪次前進**。本節原自陳
「不需要任何 grandfather 清單、也不會隨輪次腐敗」；實測 `gate.current_round()` 讀的
是帳本「發現情境」欄的最大 `R\\d+`，而本 repo 後續紀律是該欄零輪號（時鐘凍結），
實測凍結在 **R100**——當前輪不再前進，「≥ 當前輪」不會因時間流逝而讓歷史前瞻行
自動出局。strict 路徑（`unresolved_only=True`）接線後，三筆歷史交接文件的前瞻行卡
在假陽性：目標輪（R101／R108，引述既有歷史事件非自稱輪號 round-label-ok）早已過去、
指名的 DEF-ID 也已在後續輪次結案，但時鐘沒有前進，判準本身看不到這件事。

DEF-200-212 時期的過渡解＝**具名豁免面**（掌舵者裁決 D4／D8）：把假陽性逐筆登記進
`_CARRIER_DOC_EXEMPTIONS`（鍵＝`(檔案相對路徑, 指名的 DEF-ID)`，shrink-only），
不改寫歷史文件本身；表一度長到 5 筆、天花板被明文「不得再調高」，於是結案任何被前瞻行
指名的列都會再生同型假陽性（`DEF-200-213` 實質已解卻結不了案＝DEF-200-241 的死結）。

**治本（DEF-200-241 方向 B，R121 裁決卡 round-label-ok）：祖父化改讀「帳本結案事實」而非時鐘。**
`carrier_doc_problems()` 多吃一個 `done_ids`＝帳本家族內狀態欄首詞分類 ∉
`gate._UNRESOLVED_CLASSES` 的 DEF-ID（fixed／closed-by-decision／wontfix／no_action_needed
…）。前瞻行指名的 DEF-ID 若已結 ⇒ 那件事真的做完了 ⇒ 出局，不比較輪號、不依賴任何時鐘；
仍未結 ⇒ 照舊要求承接載體。判準只讀狀態欄首詞分類、不讀其他欄位（防「寫帳本改變閘門
輸入」型迴圈：結案只會讓 problem 變少；把已結列改回 open 會讓前瞻行重新要求承接——那是
正確語意）。五筆豁免登記的 DEF-ID 全屬已結 ⇒ 全數 no-op ⇒ 表清空、天花板降為 0
（機制與注入口保留，供 self-test 與回歸鎖以合成表驗證；生產表為空＝不再核准新的歷史
假陽性豁免）。存量普查實數見 `--census`。

使用：
  python3 tools/check_handoff_carriers.py            # 不合規印清單並 exit 1
  python3 tools/check_handoff_carriers.py --census    # 只印普查（永遠 rc=0）
  python3 tools/check_handoff_carriers.py --self-test # 紅綠自證（合成注入）
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import git_paths  # noqa: E402  # git 路徑列舉 SSOT（quotepath 安全；DEF-200-212②）

import _cli_flags  # noqa: E402
import _stdio_utf8  # noqa: E402,F401  # 非 UTF-8 終端 print(✅/❌) 防崩潰
import check_defect_log_crossref as gate  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[1]

#: 註冊的 tracked 交接載體 glob。**用 glob 不逐支具名**：具名清單必漏掉下一支新載體，
#: 而漏掉即零訊號＝本檔要治的病本身（同 `gate._ADR_GLOB` 的理由）。
_CARRIER_GLOBS: tuple[str, ...] = (
    "docs/04_planning/R*_HANDOFF.md",
    "docs/04_planning/AutoSDD_improving_*.md",
    "docs/06_quality/CrossPlatform_R*.md",
)

#: 判準① 與 ② 共用的「延後宣稱」樣式。前半段原樣消費帳本 SSOT（不複製、不改寫），
#: 後半段是本檔實測補上的三族——每一族都附一個真實命中的出處，避免無根據擴表：
#:   · `留 R…`     ← `f5607fa`／`772e28b` 訊息裡「…皆留」＋輪號那個句型
#:   · `延後至 R…` ← 同義動詞族，與上一族同形（收斂措辭差異，非新語意）
#:   · `交給 R…`   ← `R80_HANDOFF.md`「§4 交給 R81 的待辦」（`交棒`族沒有「交給」）
_DEFER_RES: tuple[tuple[str, re.Pattern[str]], ...] = gate._HANDOVER_ROUND_RES + (
    ("留 R…", re.compile(r"(?:皆|均|一律|確定|全部)?留(?:給|到|至|待)?"
                         + gate._HANDOVER_DECOR + r"R(\d+)")),
    ("延後至 R…", re.compile(r"(?:延後|順延|推遲|遞延)(?:到|至|給)?"
                            + gate._HANDOVER_DECOR + r"R(\d+)")),
    ("交給 R…", re.compile(r"交給" + gate._HANDOVER_DECOR + r"R(\d+)")),
)

#: 敘事引述的負向濾網。**存量假紅是量測出來的**：本檔落地前拿全部註冊載體（85 份）跑
#: 一次未加濾網的判準，3 筆命中裡有 2 筆是同一形態的假紅——本輪掃描發現檔的 `:9` 與
#: `:46` 都在寫「`_GUARD_LINES_REPIN_LOG` 那**兩列**」，是在講
#: 帳本裡那兩列，不是在交派工作。帳本 SSOT 的 `(?<![本該此上前系])列` 回顧擋得住「本列
#: ＋輪號」，擋不住**量詞開頭**的「兩列 ＋ 輪號」——因為帳本自己的列裡不會出現那種寫法。
#: 本濾網只補這一格（量詞／數字 ＋ `列`），刻意不擴大：擴大就要為每一筆辯護，那種鎖活
#: 不過一輪。
_QUANTIFIED_ROW_RE = re.compile(r"[0-9一二三四五六七八九十兩數幾多]\s*列$")
#: HTML 註解行（`<!-- guard-total:... -->` 這類機讀錨點）不是交接散文。
_HTML_COMMENT_RE = re.compile(r"^\s*<!--.*-->\s*$")
_DEF_ID_RE = re.compile(r"DEF-\d+-\d+")

#: DEF-200-212 授權的豁免面（掌舵者裁決 D4／D8）：strict 路徑對歷史交接文件的假陽性具名
#: 登記——鍵＝`(檔案相對 posix 路徑, 指名的 DEF-ID)`（**不是**行號：行號隨編輯漂移，寫死
#: 行號的豁免會靜默失效），且只在該行確實命中該 DEF-ID 時生效（`carrier_doc_problems()`
#: 取交集判定），同檔其他未登記前瞻行照判——不是整檔放行。
#:
#: 🔴 DEF-200-241 治本後**表為空**：五筆登記（R102_HANDOFF／DEF-200-204、 round-label-ok
#: R100_Scan_Findings／DEF-200-208、R107_Ledger_Closure／DEF-101-559、R113_HANDOFF 與 round-label-ok
#: R113_Ledger_Closure／DEF-200-212）指名的 ID 全屬已結列，`done_ids` 讓它們自然 round-label-ok
#: 出局，逐筆理由原文逐字保全於 CrossPlatform_R126_Debt_Closure.md §DEF-200-241。機制與
#: `exemptions=` 注入口保留：`--self-test` 與回歸鎖以**合成表**驗證「豁免只精確命中、理由
#: 太短視同未登記、不整檔放行」三條性質，生產表則不再承載任何一筆。
_CARRIER_DOC_EXEMPTIONS: dict[tuple[str, str], str] = {}
#: 一次性豁免的天花板，**只准調小**：D8 一次性核准 3→5（存證 AutoSDD_Adjudication_Record_R120.md，
#: 例外已耗用），DEF-200-241 治本後降為 **0**＝不再核准任何新的歷史假陽性豁免——歷史前瞻行
#: 指名的 DEF-ID 一旦結案即自動出局，豁免面沒有存在理由。
_CARRIER_DOC_EXEMPTIONS_MAX_ENTRIES = 0
#: 核准理由的最短長度（同 `_REPIN_APPROVED_ROUND_OVERAGE_MIN_REASON_LEN` 款式：
#: 兩個字的「核准」不算數，理由太短視同未登記——見 `_exemption_covers()`）。
_CARRIER_DOC_EXEMPTIONS_MIN_REASON_LEN = 20


def _exemption_covers(rel: str, def_id: str,
                      exemptions: dict[tuple[str, str], str]) -> bool:
    """`(rel, def_id)` 是否被具名豁免涵蓋（理由太短視同未登記，同 DEF-200-208 款式）。"""
    reason = exemptions.get((rel, def_id))
    return reason is not None and len(reason.strip()) >= _CARRIER_DOC_EXEMPTIONS_MIN_REASON_LEN


#: 本工具接受的旗標。接 `tools/_cli_flags` 的 SSOT 而非手搓 `in argv`：後者讓打錯的旗標
#: 靜默掉進預設分支並 rc=0（R67-D20 的假綠形態），且 `test_check_wrapper_thinness.py::
#: TestRootGateToolsRejectUnknownFlags` 會對任何忘了接的新守門工具當場翻紅。
_KNOWN_ARGV: tuple[str, ...] = ("--census", "--self-test")


def _narrative_hit(text: str, start: int) -> bool:
    """`text[start:]` 這個命中是否落在敘事引述上（True＝不算交派工作）。

    只判一件事：命中位置之前緊接著「量詞／數字 ＋ 列」。WHY 見 `_QUANTIFIED_ROW_RE`。

    🔴 視窗刻意含 `start` 這一格（`start + 1`）：`列 R…` 那一族的**命中本身以「列」開頭**
    （`(?<![本該此上前系])列` 是 match 的第一個字元，不是 lookbehind），只看 `[:start]`
    會拿到「兩」而拿不到「兩列」⇒ 濾網對它恆假。落地當回合的 self-test 就是這樣紅的。
    """
    return bool(_QUANTIFIED_ROW_RE.search(text[max(0, start - 10):start + 1]))


def defer_rounds(text: str) -> list[tuple[str, int, str]]:
    """抽出一段文字裡所有「延後到 R<N>」宣稱 `(樣式名, 輪號, 原文片段)`。

    先遮 markdown 行內 code span（反引號內是逐字引述，沿用帳本同一個 `_CODE_SPAN_RE`
    物件），再逐族比對，最後套 `_narrative_hit()` 濾網。純函式，紅綠由 `--self-test` 自證。
    """
    bare = gate._CODE_SPAN_RE.sub("", text)
    found: list[tuple[str, int, str]] = []
    for label, pat in _DEFER_RES:
        for m in pat.finditer(bare):
            if _narrative_hit(bare, m.start()):
                continue
            snippet = bare[max(0, m.start() - 26): m.end() + 16].replace("\n", " ")
            found.append((label, int(m.group(1)), snippet))
    return found


def ledger_carrier_rounds(ledger_text: str) -> set[int]:
    """帳本**未結案**列所承接到的輪號集合（＝可用的承接載體）。

    刻意只收未結案列：一列 `fixed` 的歷史列即使字面寫著一個未來輪號，它不承接任何未來
    工作，拿它去滿足「有人接手」是假綠。已結列的殘留待辦本身是另一筆帳（`DEF-101-736`）。

    刻意**不**把字面「未指派」算成承接輪號：那是硬規則② 二擇一的**另一支**（無輪號分支），
    語意上不能滿足「延後到 R<N>」這種**指名輪次**的宣稱。
    """
    layout = gate._table_layout(ledger_text)
    if layout is None:
        return set()
    ncols, _id_idx, status_idx = layout
    rounds: set[int] = set()
    for line in ledger_text.splitlines():
        if not gate._ROW_RE.match(line):
            continue
        cells = gate._row_cells(line)
        if len(cells) != ncols:
            continue
        if gate._classify(cells[status_idx]) not in gate._UNRESOLVED_CLASSES:
            continue
        for _lb, n, _sn in gate._handover_rounds(line):
            rounds.add(n)
    return rounds


def ledger_def_ids(ledger_text: str, archive_texts: list[str], *,
                   unresolved_only: bool = False,
                   resolved_only: bool = False) -> set[str]:
    """帳本家族（主檔 ∪ archive）內**真的有列**的 DEF-ID 集合。

    走 `_ROW_RE` 而不是全文 `_ID_RE`：散文裡提到一個 ID 不等於它有列，而「有沒有一列」
    才是本檔要問的（`DEF-200-015` 已記在案：引用一個不存在的 ID 沒有任何東西轉紅）。

    🔴 DEF-200-212①：`unresolved_only=True` 時**未結列才算承接載體**——本函式要證明的
    是「有未結承接單位」，一列 `fixed` 的歷史列不承接任何未來工作，拿它滿足判準② 是
    假綠（與同檔 `ledger_carrier_rounds()` 同一個過濾，先前一個有濾一個沒濾）。
    🔴 DEF-200-241：`resolved_only=True` 取**已結列**（狀態欄首詞分類 ∉
    `gate._UNRESOLVED_CLASSES`）——那是 `carrier_doc_problems()` 的 `done_ids`：前瞻行
    指名的事若已在帳本結案，該行即出局（治本，取代具名豁免面；沿革見模組 docstring
    〈自動祖父化的射程邊界〉）。兩個旗標互斥；版面解析不到（`layout is None`）的檔案
    一律**不猜狀態**：兩條過濾路徑都把它整份排除（只有 `layout` 解析得到的家族成員才
    貢獻 ID）。紅綠由 `--self-test` 與 `tools/tests/test_check_defect_log_crossref.py`
    的 DEF-200-212／241 系列自證。
    """
    if unresolved_only and resolved_only:
        raise ValueError("unresolved_only 與 resolved_only 互斥")
    ids: set[str] = set()
    for text in [ledger_text, *archive_texts]:
        layout = gate._table_layout(text)
        if layout is None and (unresolved_only or resolved_only):
            continue
        for line in text.splitlines():
            if not gate._ROW_RE.match(line):
                continue
            cells = gate._row_cells(line)
            if layout is not None and len(cells) != layout[0]:
                continue
            if layout is not None and (unresolved_only or resolved_only):
                unresolved = gate._classify(cells[layout[2]]) in gate._UNRESOLVED_CLASSES
                if unresolved_only and not unresolved:
                    continue
                if resolved_only and unresolved:
                    continue
            m = _DEF_ID_RE.search(cells[1] if len(cells) > 1 else line)
            if m:
                ids.add(m.group(0))
    return ids


def commit_messages(limit: int = 4000) -> list[tuple[str, str]]:
    """`(短 sha, 訊息全文)`；取不到 git 歷史時回空清單（由判準③ 出聲，不假裝成綠）。"""
    try:
        out = subprocess.run(
            ["git", "log", f"-n{limit}", "--format=%h%x00%B%x01"],
            cwd=_REPO_ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False)
    except OSError:
        return []
    if out.returncode != 0:
        return []
    msgs: list[tuple[str, str]] = []
    for raw in out.stdout.split("\x01"):
        if not raw.strip():
            continue
        sha, _, body = raw.strip().partition("\x00")
        msgs.append((sha, body))
    return msgs


_PARAGRAPH_RE = re.compile(r"\n\s*\n")


def commit_carrier_problems(msgs: list[tuple[str, str]], cur: int | None,
                            carriers: set[int], *,
                            done_ids: set[str] | None = None) -> list[str]:
    """判準①：commit 訊息宣告延後到 R<N>（N ≥ cur）⇒ 帳本須有未結列承接 ≥ N。純函式。

    🔴 DEF-200-241 同一原則套到本判準：宣告所在的**段落**（空行分隔）若指名一個帳本已結
    的 DEF-ID（`done_ids`），那件被延後的事已在帳本結案 ⇒ 出局。立案實例＝commit `0398226`
    的「已列 R118 交棒書呈報裁決」段落指名 `DEF-200-212`；212／241 結案後 round-label-ok
    帳本裡再也沒有承接輪次 ≥ R118 的未結列（時鐘凍結在 R100，`n < cur` 永不祖父化）， round-label-ok
    判準① 就因「把事情做完」而轉紅——正是 241 要治的迴圈。以段落而非整則訊息為粒度，避免一則訊息
    裡一個已結 ID 替所有無關延後背書。
    """
    if cur is None:
        return []
    done = done_ids or set()
    problems: list[str] = []
    for sha, body in msgs:
        for para in _PARAGRAPH_RE.split(body):
            if {m.group(0) for m in _DEF_ID_RE.finditer(para)} & done:
                continue
            problems.extend(_commit_para_problems(sha, para, cur, carriers))
    return problems


def _commit_para_problems(sha: str, para: str, cur: int,
                          carriers: set[int]) -> list[str]:
    """判準① 對單一段落的本體（拆出來只為了讓段落過濾與訊息組字各自可讀）。"""
    problems: list[str] = []
    for label, n, snippet in defer_rounds(para):
        if n < cur:
            continue
        if any(r >= n for r in carriers):
            continue
        problems.append(
                f"commit {sha}：訊息宣告把工作延後到 **R{n}**（[{label}] …{snippet.strip()}…），"
                f"但帳本家族內**沒有任何未結案列**的承接輪次 ≥ R{n}"
                f"（現有未結承接輪號＝{sorted(carriers) or '空'}）⇒ 這一項只活在交接散文裡，"
                f"沒有機械承接載體，下一輪沒做也不會有任何東西轉紅（`DEF-200-188` 立案形態）。"
                f"🔴 出口**不是**改 commit 訊息（不可改，且不該改）：在 "
                f"`docs/06_quality/AutoSDD_Defect_Log.md` 補一列，狀態欄寫 "
                f"`open（承接輪次：**R{n}**）` 或更後面的輪次即綠；若該段落指名的 DEF-ID "
                f"已在帳本結案，本判準會自動放行（DEF-200-241）")
    return problems


def _tracked_hits(hits: set[Path], tracked: set[str] | None) -> tuple[list[Path], bool]:
    """glob 命中 ∩ tracked 集合（repo 相對 posix 鍵）。純函式，供 `--self-test` 注入。

    `tracked=None`＝取數管道壞掉 ⇒ 退回 glob 並回報 `fallback=True`（fail-loud not
    fail-closed，同檔 `commit_messages()` 既有姿態：由判準③ 出聲，不假裝成綠）。
    """
    if tracked is None:
        return sorted(hits), True
    return (sorted(h for h in hits
                   if h.relative_to(_REPO_ROOT).as_posix() in tracked), False)


def carrier_files() -> tuple[list[Path], bool]:
    """註冊 glob 命中 ∩ git tracked 的交接載體（排序、去重）＋是否退回純 glob。

    🔴 DEF-200-212②：先前只走 `_REPO_ROOT.glob()`（檔案系統）卻自稱 tracked ⇒ 未追蹤
    檔被計為 tracked（實證：未追蹤的 `R100_HANDOFF.md` 使普查 85→86 並通過驗證）。
    保留 pathlib glob 語意（避免 git pathspec 的 `**` 歧義），tracked 集合走 SSOT
    `git_paths.ls_files()`（quotepath 安全）後取交集。
    """
    hits: set[Path] = set()
    for g in _CARRIER_GLOBS:
        hits.update(_REPO_ROOT.glob(g))
    try:
        listed = git_paths.ls_files(_REPO_ROOT, "docs")
    except OSError:
        listed = []
    return _tracked_hits(hits, set(listed) if listed else None)


def carrier_doc_problems(paths: list[Path], cur: int | None,
                         known_ids: set[str], *,
                         exemptions: dict[tuple[str, str], str] | None = None,
                         done_ids: set[str] | None = None) -> list[str]:
    """判準②：交接載體內的前瞻延後行必須指名帳本家族內**未結**的 DEF-ID，**或**
    指名一個**已結**的 DEF-ID（＝那件事真的做完了，DEF-200-241 治本）。

    `known_ids`＝未結列 ID（承接載體）；`done_ids`＝已結列 ID（`ledger_def_ids(...,
    resolved_only=True)`）。祖父化讀的是**結案事實**，不是輪號、不是時鐘。
    `exemptions`（預設 `_CARRIER_DOC_EXEMPTIONS`，治本後為空）＝DEF-200-212 具名豁免面：
    `(檔案相對路徑, DEF-ID)` 精確相符且理由夠長時不算 problem；刻意可傳供 `--self-test`
    與回歸鎖以合成表注入。
    """
    if cur is None:
        return []
    exempt = _CARRIER_DOC_EXEMPTIONS if exemptions is None else exemptions
    done = done_ids or set()
    problems: list[str] = []
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fence = False
        rel = p.relative_to(_REPO_ROOT).as_posix()
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                fence = not fence
                continue
            if fence or _HTML_COMMENT_RE.match(line):
                continue
            fwd = [(lb, n, sn) for lb, n, sn in defer_rounds(line) if n >= cur]
            if not fwd:
                continue
            named = {m.group(0) for m in _DEF_ID_RE.finditer(line)}
            if named & known_ids:
                continue
            # DEF-200-241：指名的事已在帳本結案 ⇒ 那件交接真的做完了 ⇒ 出局（不比輪號）。
            if named & done:
                continue
            if any(_exemption_covers(rel, def_id, exempt) for def_id in named):
                continue
            detail = "；".join(f"[{lb}] R{n}" for lb, n, _ in fwd)
            extra = (f"（本行提到的 {sorted(named)} 在帳本家族內查無列）" if named else
                     "（本行完全沒有 DEF-ID）")
            problems.append(
                f"{rel}:{lineno} 這一行把工作延後到未來輪（{detail}），卻沒有帳本承接列"
                f"{extra} ⇒ 交接項無機械承接載體。出口：補一列帳本並在本行指名該 DEF-ID"
                f"（射程判準＝目標輪 ≥ 當前輪 R{cur}）；該列日後結案時本行自動出局"
                f"（DEF-200-241：祖父化讀帳本結案事實，不讀時鐘——帳本『發現情境』欄輪次"
                f"時鐘已凍結，見模組 docstring〈自動祖父化的射程邊界〉）。🔴 引用一個帳本"
                f"家族內查無列的 DEF-ID 不算承接（引用 ≠ 有列）")
    return problems


def census_notes(msgs: list[tuple[str, str]], paths: list[Path],
                 cur: int | None, carriers: set[int],
                 glob_fallback: bool = False) -> list[str]:
    """判準③：把分母印出來。**「零命中」必須可見**，理由見模組 docstring。"""
    fwd_docs = sum(
        1 for p in paths
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines()
        for lb, n, _ in defer_rounds(line) if cur is not None and n >= cur
    )
    fwd_commits = sum(
        1 for _sha, body in msgs
        for _lb, n, _sn in defer_rounds(body) if cur is not None and n >= cur
    )
    notes = [
        f"當前輪＝R{cur}（帳本「{gate._CONTEXT_HEADER}」欄現查；"
        f"未結承接輪號＝{sorted(carriers) or '空'}）",
        f"tracked 交接載體＝{len(paths)} 份（glob {list(_CARRIER_GLOBS)}）；"
        f"其中前瞻延後行 {fwd_docs} 筆",
        f"commit 訊息＝{len(msgs)} 則；其中含前瞻延後宣告 {fwd_commits} 筆",
    ]
    if glob_fallback:
        notes.append(
            "🔴 [tracked 取數退化] `git ls-files` 取不到 tracked 集合 ⇒ 載體面退回檔案"
            "系統 glob（未追蹤檔會被計入，上一行的「tracked」此刻不成立；DEF-200-212②）")
    if len(msgs) <= 1:
        notes.append(
            "🔴 [淺 clone] `git log` 只回到 "
            f"{len(msgs)} 則訊息 ⇒ 判準① 的分母已塌掉，此處的綠**不構成任何保證**"
            "（CI `actions/checkout` 預設 fetch-depth=1；判準① 的有效執行面是本地 "
            "pre-push 與開發機的全深度 clone）")
    return notes


def _load() -> tuple[str, list[str]]:
    ledger = gate._DEFECT_LOG.read_text(encoding="utf-8")
    arch = [p.read_text(encoding="utf-8", errors="replace") for p in gate.archive_files()]
    return ledger, arch


# ── self-test 的合成語料。抽成常數而不是內嵌在 assert 行裡，是為了讓每一行都放得下
#    `round-label-ok` 具名豁免又不破 100 字元（本檔的輪號全是**引述史料**，不是自稱本批
#    輪號；那道鎖＝`test_check_defect_log_crossref.py::TestR71CodeRoundLabels...`）。
_SYN_CUR = 98
_SYN_FUTURE = 100  # round-label-ok：合成語料的目標輪，非本批自稱輪號
_SYN_LATER = 101  # round-label-ok：同上
_SYN_PAST = 75
_SYN_MSG = f"feat: x\n\n未達成（不塗綠）：Phase 2、B8 額度術語機械化皆留 R{_SYN_FUTURE}。\n"
_SYN_QUOTE = f"`_GUARD_LINES_REPIN_LOG` 兩列 R{_SYN_FUTURE} 逐字指名"
# DEF-200-015：`_REF_RE`（tools/tests/test_defect_id_reference_integrity.py）擴大納管
# 200 家族後，本行原本寫死的合成 ID 字面會被當成懸空引用抓到——同檔自己的
# `_syn()` 早就用「執行期組字」避開這個坑（101 家族），這裡比照辦理，連本註解都不
# 能留完整字面（第一次修法把字面寫進註解裡，被同一道鎖原地抓到，故訂正於此）。
_SYN_ID = "DEF-200-" + "999"


def _self_test() -> int:
    """合成注入紅綠自證（純函式，不碰磁碟上的任何真檔）。"""
    fails: list[str] = []

    def expect(cond: bool, what: str) -> None:
        print(f"  {'PASS' if cond else 'FAIL'}  {what}")
        if not cond:
            fails.append(what)

    print("[self-test] 判準① 提交訊息 → 帳本承接列")
    msg = [("deadbee", _SYN_MSG)]
    expect(len(commit_carrier_problems(msg, _SYN_CUR, set())) == 1,
           "宣告延後到未來輪、帳本零承接 ⇒ 紅")
    expect(commit_carrier_problems(msg, _SYN_CUR, {_SYN_LATER}) == [],
           "帳本有未結列承接更後面的輪次 ⇒ 綠")
    expect(commit_carrier_problems(msg, _SYN_CUR, {_SYN_FUTURE - 1}) != [],
           "承接輪號比宣告目標小一輪 ⇒ 不足以接手 ⇒ 紅")
    expect(commit_carrier_problems([("c", f"交給 R{_SYN_PAST} 的待辦")], _SYN_CUR, set()) == [],
           "歷史宣告的目標輪 < 當前輪 ⇒ 自動出局（無需豁免名單）")
    para_msg = [("d", f"feat: y\n\n- {_SYN_ID} 結案受阻，已列 R{_SYN_FUTURE} 交棒書。\n\n"
                      f"- 另一件事皆留 R{_SYN_FUTURE}。\n")]
    expect(len(commit_carrier_problems(para_msg, _SYN_CUR, set(), done_ids={_SYN_ID})) == 1,
           "段落指名的 DEF-ID 已結 ⇒ 該段落出局；另一段落沒指名 ⇒ 仍紅（粒度＝段落，非整則）")
    expect(len(commit_carrier_problems(para_msg, _SYN_CUR, set())) == 2,
           "done_ids 為空 ⇒ 兩段皆紅（判準① 的 done 判準真的在承重）")

    print("[self-test] `defer_rounds()` 樣式與敘事濾網")
    expect([n for _, n, _ in defer_rounds(f"皆留 R{_SYN_FUTURE}。")] == [_SYN_FUTURE],
           "「皆留 ＋ 輪號」命中")
    expect([n for _, n, _ in defer_rounds("§4 交給 R81 的待辦")] == [81], "「交給 R81」命中")
    expect(defer_rounds(_SYN_QUOTE) == [], "「兩列 ＋ 輪號」＝敘事引述 ⇒ 不命中（實測假紅）")
    expect(defer_rounds("本列 R14 快照所稱") == [], "「本列 R14」＝帳本 SSOT 負向回顧仍生效")
    expect(defer_rounds(f"見 `皆留 R{_SYN_FUTURE}`") == [], "code span 內逐字引述 ⇒ 不命中")

    print("[self-test] 判準② 交接載體 → 帳本 DEF-ID")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "docs" / "04_planning"
        d.mkdir(parents=True)
        f = d / "R999_HANDOFF.md"  # round-label-ok：合成檔名
        f.write_text(f"- 這件事交給 R{_SYN_LATER} 處理\n", encoding="utf-8")
        global _REPO_ROOT  # noqa: PLW0603
        keep, _REPO_ROOT = _REPO_ROOT, Path(td)
        try:
            expect(len(carrier_doc_problems([f], _SYN_CUR, set())) == 1,
                   "延後行無 DEF-ID ⇒ 紅")
            f.write_text(f"- 這件事交給 R{_SYN_LATER} 處理（{_SYN_ID}）\n", encoding="utf-8")
            expect(carrier_doc_problems([f], _SYN_CUR, {_SYN_ID}) == [],
                   "延後行指名帳本內存在的 DEF-ID ⇒ 綠")
            expect(carrier_doc_problems([f], _SYN_CUR, set()) != [],
                   "指名一個帳本裡查無列的 DEF-ID ⇒ 仍紅（引用 ≠ 有列）")
        finally:
            _REPO_ROOT = keep

    print("[self-test] 判準② 取數面兩假綠（DEF-200-212；strict 路徑，main() 已接線）")
    syn_fixed = f"| ID | 狀態 |\n|----|------|\n| {_SYN_ID} | fixed@R{_SYN_CUR} |\n"
    expect(_SYN_ID not in ledger_def_ids(syn_fixed, [], unresolved_only=True),
           "已結（fixed）列的 ID 不算承接載體（改前本注入為綠＝假綠重演）")
    syn_open = (f"| ID | 狀態 |\n|----|------|\n"
                f"| {_SYN_ID} | open（承接輪次：**R{_SYN_LATER}**） |\n")
    expect(_SYN_ID in ledger_def_ids(syn_open, [], unresolved_only=True),
           "未結列的 ID 仍是承接載體（對照組）")
    syn_hits = {_REPO_ROOT / "docs" / "04_planning" / "R997_HANDOFF.md",  # round-label-ok：合成檔名
                _REPO_ROOT / "docs" / "04_planning" / "R996_HANDOFF.md"}  # round-label-ok：合成檔名
    got, fell_back = _tracked_hits(syn_hits, {"docs/04_planning/R997_HANDOFF.md"})
    expect([p.name for p in got] == ["R997_HANDOFF.md"] and not fell_back,
           "glob 命中 ∩ tracked：未追蹤路徑被剔除（tracked 語意補真）")
    got_all, fell_back_all = _tracked_hits(syn_hits, None)
    expect(len(got_all) == 2 and fell_back_all,
           "tracked 取不到 ⇒ 退回 glob 並標記 fallback（fail-loud，判準③ 出聲）")

    print("[self-test] 判準② 祖父化改讀帳本結案事實（DEF-200-241 治本）")
    syn_done = (f"| ID | 狀態 |\n|----|------|\n"
                f"| {_SYN_ID} | closed-by-decision（合成）；2026-01-01 |\n")
    expect(_SYN_ID in ledger_def_ids(syn_done, [], resolved_only=True),
           "已結列的 ID 進 done_ids（closed-by-decision）")
    expect(_SYN_ID not in ledger_def_ids(syn_done, [], unresolved_only=True),
           "同一列不會同時進 known_ids（兩個集合互補）")
    expect(_SYN_ID not in ledger_def_ids(syn_open, [], resolved_only=True),
           "未結列的 ID 不進 done_ids（partial／open 仍算未結）")
    expect(_SYN_ID not in ledger_def_ids("沒有表格的散文提到 " + _SYN_ID, [],
                                         resolved_only=True),
           "版面解析不到的檔不猜狀態 ⇒ 一個 ID 都不貢獻給 done_ids")
    done_td = tempfile.TemporaryDirectory(prefix="handoff_done_")
    keep, _REPO_ROOT = _REPO_ROOT, Path(done_td.name)
    try:
        d2 = _REPO_ROOT / "docs" / "06_quality"
        d2.mkdir(parents=True)
        f2 = d2 / "CrossPlatform_R998_Scan_Findings.md"  # round-label-ok：合成檔名
        f2.write_text(f"- 這件事交給 R{_SYN_LATER} 處理（{_SYN_ID}）\n", encoding="utf-8")
        expect(len(carrier_doc_problems([f2], _SYN_CUR, set())) == 1,
               "指名的 ID 既非未結亦非已結 ⇒ 紅（對照組）")
        expect(carrier_doc_problems([f2], _SYN_CUR, set(), done_ids={_SYN_ID}) == [],
               "指名的 ID 已結案 ⇒ 那件事做完了 ⇒ 出局、綠（不比輪號）")
        expect(len(carrier_doc_problems([f2], _SYN_CUR, set(), done_ids=set())) == 1,
               "done_ids 為空 ⇒ 判準退回原行為、仍紅（新判準真的在承重）")
    finally:
        _REPO_ROOT = keep
        done_td.cleanup()

    print("[self-test] 判準② 具名豁免機制（合成表；生產表治本後為空，天花板 0）")
    expect(_CARRIER_DOC_EXEMPTIONS == {} and _CARRIER_DOC_EXEMPTIONS_MAX_ENTRIES == 0,
           "生產豁免表為空、天花板 0（DEF-200-241 治本後不再核准歷史假陽性豁免）")
    syn_exempt = {("docs/04_planning/R997_HANDOFF.md", _SYN_ID):  # round-label-ok：合成鍵
                  "合成豁免：理由長度須達門檻才算登記，本句刻意寫滿二十字以上。"}
    exempt_td = tempfile.TemporaryDirectory(prefix="handoff_exempt_")
    keep, _REPO_ROOT = _REPO_ROOT, Path(exempt_td.name)
    try:
        rel, def_id = next(iter(syn_exempt))
        fp = _REPO_ROOT / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(f"- 交給 R{_SYN_LATER} 處理（{def_id}）\n", encoding="utf-8")
        expect(carrier_doc_problems([fp], _SYN_CUR, set(), exemptions=syn_exempt) == [],
               "登記豁免命中（路徑＋DEF-ID 精確相符）⇒ 不算 problem")
        fp.write_text(fp.read_text(encoding="utf-8")
                      + f"- 另一件不相干的事交給 R{_SYN_LATER} 處理\n", encoding="utf-8")
        expect(len(carrier_doc_problems([fp], _SYN_CUR, set(), exemptions=syn_exempt)) == 1,
               "同一份文件裡一個未登記的同型前瞻行 ⇒ 仍紅（防整檔放行、防 vacuous）")
        other = "DEF-200-" + "998"
        fp.write_text(f"- 交給 R{_SYN_LATER} 處理（{other}）\n", encoding="utf-8")
        expect(len(carrier_doc_problems([fp], _SYN_CUR, set(), exemptions=syn_exempt)) == 1,
               "豁免鍵指向的 DEF-ID 與該行實際指名的不符 ⇒ 不豁免、仍紅")
        fp.write_text(f"- 交給 R{_SYN_LATER} 處理（{def_id}）\n", encoding="utf-8")
        expect(len(carrier_doc_problems([fp], _SYN_CUR, set(),
                                        exemptions={(rel, def_id): "太短"})) == 1,
               "理由太短視同未登記 ⇒ 即使 key 對得上也不豁免（防空話核准）")
    finally:
        _REPO_ROOT = keep
        exempt_td.cleanup()

    print(f"\n[self-test] {'❌ ' + str(len(fails)) + ' 項失敗' if fails else '✅ 全部通過'}")
    return 1 if fails else 0


def cli(argv: list[str]) -> int:
    """旗標分派。**刻意不寫進 `main()`**：`main()` 一碰 `sys.argv`，直接呼叫它的測試就會
    把 unittest 自己的參數當成本工具的旗標而 rc=2 假紅。接線紀律（`cli` 分層 ＋ `__main__`
    只留一行）的權威記載＝`tools/_cli_flags.py` 檔頭〈接線紀律〉，先例＝
    `tools/run_root_unittests.py`；機械物＝`tools/tests/test_check_wrapper_thinness.py::
    TestRootGateToolsRejectUnknownFlags`。
    """
    rc = _cli_flags.reject_unknown_argv("check_handoff_carriers.py", argv, _KNOWN_ARGV)
    if rc is not None:
        return rc
    return main(argv)


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if "--self-test" in args:
        return _self_test()
    ledger, arch = _load()
    cur = gate.current_round(ledger)
    carriers = ledger_carrier_rounds(ledger)
    msgs = commit_messages()
    paths, glob_fallback = carrier_files()
    for note in census_notes(msgs, paths, cur, carriers, glob_fallback):
        print(f"[census] {note}")
    if "--census" in args:
        return 0
    # 🔴 順序有鎖：`unresolved_only=True` 那一次呼叫必須是 main() 裡文字面上的第一次
    # （`TestDef200212StrictIsWiredIntoMain` 讀第一個呼叫行的三行視窗）。
    known_ids = ledger_def_ids(ledger, arch, unresolved_only=True)
    done_ids = ledger_def_ids(ledger, arch, resolved_only=True)  # DEF-200-241
    problems = commit_carrier_problems(msgs, cur, carriers, done_ids=done_ids)
    problems += carrier_doc_problems(paths, cur, known_ids, done_ids=done_ids)
    if problems:
        print(f"\n❌ 交接項無機械承接載體：{len(problems)} 筆", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("\n✅ 每一筆前瞻延後宣稱都有帳本承接載體")
    return 0


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
