#!/usr/bin/env python3
"""職責⑤：**runtime skip 數**的分群天花板（R79／D-skipped #2、掌舵者系統問題 S3）。

🔴 缺陷本體（R79 當回合逐項實查）：全 repo 對「這次真的 skip 了幾支」零管轄。
`PG_CONTRACT_MAX_SKIPPED` 是唯一一道天花板、只覆蓋 `pg-contract` 一個 CI job；
`AutoClaude/tools/local_ci_gate.py` 對 `skipped` 零字樣；根層 `run_root_unittests.py`
只**印**不判（實測 `OK (skipped=43)` rc=0）；ONBOARDING §7 自陳 `skipped=N` 刻意不在鎖內。
於是掌舵者問的那個數字可以無聲上升，而上升的樣子在摘要裡長得像「乾淨」。逐支消除治不了
復發——R76 把 224 壓到 158 之後，R77／R78 又各自新增 skip 站點，靠的全是人記得。

為何獨立成第⑤個模組而不是塞進 `skip_tag_policy`（職責①）：那支加完本段後 `count_loc`
達 428 > `guardrail_lib` tier 的 400（落地當回合被 `check_loc_budget.py` 當場擋下）。
分級判準想說的正是「一支超過 400 行的共用模組按定義已不只做一件事」，而事實也是如此：
①管的是**標籤字面與靜態站點**的政策，本檔管的是**一次執行的 skip 數**——兩者的量測母體
不同（原始碼站點 vs 這次跑出來的測試支數），常數也不共用。抽共用模組是本 repo 對這種
情形的既定處置（先例逐字寫在 `check_loc_budget.ROOT_TOOLS_TIERS` 的 override_reason 裡）。

標籤字面本身仍住 `skip_tag_policy`（唯一真相源），本檔只 import 不複製。
"""
from __future__ import annotations

import re
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skip_tag_policy import (  # noqa: E402
    _EXEMPT_HANDOVER_RE,
    DEBT_SKIP_TAG,
    ENV_DISABLED_SKIP_TAG,
    MAC_NATIVE_SKIP_TAG,
    POSIX_NATIVE_SKIP_TAG,
    STRUCTURAL_PAIR_SKIP_TAG,
    TOOL_ABSENCE_SKIP_TAG,
    WINDOWS_NATIVE_SKIP_TAG,
)

# ── 分群 ────────────────────────────────────────────────────────────────────────
#
# 為何是「分群天花板」而不是「總數天花板」：各群的**應然值完全不同**。
# `env-disabled` 應該清到 0（R79 證明：這台機器一件缺件都沒有，設三個環境變數就消 92 支），
# `structural-pair` 結構上不可能是 0，`platform` 跨平台不對稱（Windows 上 POSIX-only 全
# skip、mac 上反過來）。壓成一個總數就沒有任何一格說得出「這一格該不該是 0」。
SKIP_GROUP_PLATFORM = "platform"
SKIP_GROUP_TOOL_ABSENCE = "tool-absence"
SKIP_GROUP_ENV_DISABLED = "env-disabled"
SKIP_GROUP_STRUCTURAL = "structural-pair"
SKIP_GROUP_DEBT = "debt"
SKIP_GROUP_UNTAGGED = "untagged"
SKIP_GROUPS: tuple[str, ...] = (
    SKIP_GROUP_PLATFORM, SKIP_GROUP_TOOL_ABSENCE, SKIP_GROUP_ENV_DISABLED,
    SKIP_GROUP_STRUCTURAL, SKIP_GROUP_DEBT, SKIP_GROUP_UNTAGGED,
)

_TAG_GROUP: dict[str, str] = {
    WINDOWS_NATIVE_SKIP_TAG: SKIP_GROUP_PLATFORM,
    POSIX_NATIVE_SKIP_TAG: SKIP_GROUP_PLATFORM,
    MAC_NATIVE_SKIP_TAG: SKIP_GROUP_PLATFORM,
    TOOL_ABSENCE_SKIP_TAG: SKIP_GROUP_TOOL_ABSENCE,
    ENV_DISABLED_SKIP_TAG: SKIP_GROUP_ENV_DISABLED,
    STRUCTURAL_PAIR_SKIP_TAG: SKIP_GROUP_STRUCTURAL,
    DEBT_SKIP_TAG: SKIP_GROUP_DEBT,
}


def skip_group(reason: str) -> str:
    """純函式：一句 skip reason 屬於哪一群（判**開頭**的標籤，同 `_TAG_PREFIX_RE` 契約）。

    未登記的標籤字面（例：`[TOOL-MISSING]`）一律落進 `untagged`——**這是刻意的**：
    發明一個新標籤不得換到「看起來已分類」的待遇，否則分群本身就會變成繞道。
    """
    stripped = reason.lstrip()
    for tag, group in _TAG_GROUP.items():
        if stripped.startswith(tag):
            return group
    return SKIP_GROUP_UNTAGGED


def skip_group_census(reasons: Iterable[str]) -> dict[str, int]:
    """純函式：一批 reason 的分群計數。每一群都出現、值為 0 也在表上——
    不列出來的群等於沒人在看它。"""
    census = dict.fromkeys(SKIP_GROUPS, 0)
    for reason in reasons:
        census[skip_group(reason)] += 1
    return census


# ── 應然值（目標）：「歸零」的正確定義 ────────────────────────────────────────────
#
# 🔴 R80 包 A（掌舵者驗收問題②「歸零可不可能」）：**skip 總數歸零在單一平台上結構性
# 不可能**——`platform` 群的意思正是「這支測試在**別的**平台才有驗證價值」，在 Windows
# 上把它跑起來不是覆蓋變好、是斷言變假（R72 判過的「守衛 `if on_windows: return []`」
# 就是那個錯誤的極端形）。所以「skipped=0」是一個**永遠達不到、且不該達到**的目標，
# 而一個達不到的目標與沒有目標等價：它不會出現在任何判準裡，於是實務上沒有人在瞄準它。
#
# 正確的目標必須把「結構性不可跑」與「還沒有人去修」分開，本表就是那條線：
#   · ZERO 群（tool-absence／env-disabled／debt／untagged）＝**欠債**，可歸零且應歸零。
#     R79 已實證 `env-disabled` 的可歸零性：那台機器一件缺件都沒有，設三個環境變數就
#     消掉 92 支。`untagged` 更是定義上可歸零——它只代表「這支 skip 還沒人說得出它屬於
#     哪一類」，補一句標籤就結案。
#   · STRUCTURAL 群（platform／structural-pair）＝**結構性**，目標**不是** 0，而是
#     「互補剖面上有人真的跑到它」：一支 `[POSIX-NATIVE-ONLY]` 在 win32 剖面 skip 是
#     對的，但如果 linux 剖面根本沒有人量過，那它就是**全世界都沒跑過**——那才是缺陷，
#     而它跟「skip 數是多少」完全無關，量 skip 數永遠看不到它。
#
# ⇒ 可被機械檢核的目標＝ `open_debt(census)`（ZERO 群之和）只准降、目標值 0；
#    加上 `skip_target_report()` 把 STRUCTURAL 群的互補剖面缺口逐條列出來。
SKIP_TARGET_ZERO = "zero"
SKIP_TARGET_STRUCTURAL = "structural"
_SKIP_GROUP_TARGET: dict[str, str] = {
    SKIP_GROUP_PLATFORM: SKIP_TARGET_STRUCTURAL,
    SKIP_GROUP_STRUCTURAL: SKIP_TARGET_STRUCTURAL,
    SKIP_GROUP_TOOL_ABSENCE: SKIP_TARGET_ZERO,
    SKIP_GROUP_ENV_DISABLED: SKIP_TARGET_ZERO,
    SKIP_GROUP_DEBT: SKIP_TARGET_ZERO,
    SKIP_GROUP_UNTAGGED: SKIP_TARGET_ZERO,
}
#: 目標為 0 的群（＝真正的「欠債」面）。順序沿用 `SKIP_GROUPS` 以利輸出穩定。
ZERO_TARGET_GROUPS: tuple[str, ...] = tuple(
    g for g in SKIP_GROUPS if _SKIP_GROUP_TARGET[g] == SKIP_TARGET_ZERO
)


def open_debt(census: Mapping[str, int]) -> int:
    """純函式：這次執行的**欠債型** skip 支數（ZERO 群之和）——即「歸零」的標的。

    刻意不是 `len(reasons)`：把結構性不可跑的那一群算進去，會讓這個數字永遠不可能到 0，
    而永遠到不了的目標等於沒有目標。
    """
    return sum(census.get(g, 0) for g in ZERO_TARGET_GROUPS)


# ── 量測面：`-rs` 區塊的解析 ＋ **量測完整性** ─────────────────────────────────
#
# 🔴 為何這兩件事住在政策模組而不是消費端（R79 收輪／QA blocking）：解析器與判準本來
# 分居兩地（regex 在 `AutoClaude/tools/local_ci_gate.py`、天花板在本檔），而 QA 當回合
# 實測到的缺陷正好長在兩者之間——把空字串、沒有 `-rs` 區塊的 `-q` 摘要、以及 SKIPPED
# 前綴變動三種輸入餵進去，三次都印「共 0 支：…untagged=0」並回 **rc=0**：**天花板只對
# 「數字變多」那一向說話，量測本身塌掉時它是綠的**，而失效方向正是 R76 記過的
# 「看起來變乾淨」。這不是假想：`-rs` 在這個 repo 真的靜默消失過（R59；始末逐字記在
# `AutoClaude/tools/local_ci_gate.py` 檔頭第 23~29 行），而同一輪的
# `context_budget_guard.used_of()` 才剛為「量不到 ≠ 量到零」寫了整段 WHY。
#
# 判準本體只有一句話：**pytest 自己在摘要行宣告的 `N skipped` 是權威值，`-rs` 區塊解析
# 出的支數必須等於它**。兩個方向都會說話——
#   · 連摘要行都找不到（pytest 沒跑完／輸出擷取壞掉／根本不是 pytest 輸出）⇒ 紅。
#     此時「共 0 支 skip」是**量不到**，不是量到零，回綠等於把塌掉當健康。
#   · 摘要說有、`-rs` 解析不出來 ⇒ `-rs` 從呼叫端消失，或 SKIPPED 行格式改變 ⇒ 紅。
#
#: `-rs` 區塊的一行＝`SKIPPED [n] <路徑>:<行號>: <理由>`。
#: 🔴 位置前綴刻意用**第二個** regex 剝掉，不寫成第一個 regex 裡的 `[^:]*`——
#: Windows 路徑與行號本身就含 `:`（`tests\x.py:321:`），寫成那樣會讓 136 支只認出 2 支
#: （R79 落地當回合實測，不是假想；那 2 支剛好是沒有位置前綴的形態，所以看起來還「有在動」）。
#: 沒有位置前綴的行（無條件 skip）也要吃得下，故 `sub(count=1)` 而不是要求它一定存在。
_SKIPPED_LINE_RE = re.compile(r"^SKIPPED \[(\d+)\] (.*)$", re.MULTILINE)
#: 兩種位置形態都要剝：`<檔>.py:<行號>: `（一般）與 `<檔>.py: `（模組層／conftest 層，
#: 沒有行號——實測 `test_pgvector_real_recall.py` 那 2 支就是這一種，不處理的話理由會
#: 帶著路徑前綴，標籤判定（標籤必須在**最前面**）當場失效）。
_SKIP_LOCATION_RE = re.compile(r"^.*?\.py:(?:\d+:)? ")

#: pytest 的**摘要行**（`-q` 與非 `-q` 皆為同一形態的超集合）：至少一個 `N <結果詞>`
#: 或 `no tests ran`，且尾巴帶 ` in <秒數>s`。刻意不比對整行開頭的 `=` 裝飾——`-q` 沒有。
_SUMMARY_LINE_RE = re.compile(
    r"^.*?(?:\d+ (?:passed|failed|errors?|skipped|xfailed|xpassed|deselected|warnings?)"
    r"|no tests ran)\b.*? in \d+(?:\.\d+)?s.*$",
    re.MULTILINE,
)
_SUMMARY_SKIPPED_RE = re.compile(r"(\d+) skipped\b")


def skipped_reasons(pytest_output: str) -> list[str]:
    """從 `-rs` 區塊抽出每一支 skip 的理由（`SKIPPED [n]` 的 n 代表 n 支，逐支展開）。"""
    out: list[str] = []
    for count, rest in _SKIPPED_LINE_RE.findall(pytest_output or ""):
        reason = _SKIP_LOCATION_RE.sub("", rest, count=1).strip()
        out.extend([reason] * int(count))
    return out


def declared_skipped(pytest_output: str) -> int | None:
    """pytest 摘要行**自己宣告**的 skip 支數。

    🔴 找不到摘要行時回 `None` 而不是 `0`——這正是本函式存在的理由：「量不到」與
    「量到零」在型別上就必須分得開，否則呼叫端只要少寫一個 `is None` 判斷，塌掉的量測
    就會被當成健康值。摘要行存在但沒有 `skipped` 字樣則確實是 0（pytest 為零時不印該詞）。
    """
    lines = _SUMMARY_LINE_RE.findall(pytest_output or "")
    if not lines:
        return None
    found = _SUMMARY_SKIPPED_RE.search(lines[-1])
    return int(found.group(1)) if found else 0


def _tail(text: str, lines: int = 3) -> str:
    """給人看的「實際收到了什麼」——訊息只說「量測塌掉」而不附證據，等於要人重跑一次。"""
    kept = [ln for ln in (text or "").splitlines() if ln.strip()][-lines:]
    return " ⏎ ".join(kept) if kept else "(輸出為空)"


def skip_measurement_problems(pytest_output: str, parsed_skips: int) -> list[str]:
    """量測完整性的判準（純函式）。回空 list ＝這份輸出真的量得到 skip 數。

    呼叫端**必須在天花板之前**跑這一道：天花板拿 `parsed_skips` 與上限比大小，而塌掉的
    量測給出的 0 永遠小於任何上限 ⇒ 先比天花板等於先給自己蓋一個綠章。
    """
    declared = declared_skipped(pytest_output)
    if declared is None:
        return [
            "[量測塌掉] 找不到 pytest 摘要行（形如 `N passed, M skipped … in T.TTs`）"
            "——pytest 沒跑完／輸出沒有被擷取到／這根本不是 pytest 的輸出。此時「共 0 支"
            " skip」是**量不到**而不是量到零，一律判紅（回綠等於把塌掉的量測當成健康）。"
            f"實際收到的尾段：{_tail(pytest_output)}"
        ]
    if declared != parsed_skips:
        return [
            f"[量測塌掉] pytest 摘要行宣告 {declared} 支 skip，`-rs` 區塊卻只解析出 "
            f"{parsed_skips} 支——兩者必須相等。最可能的兩個原因：①呼叫端掉了 `-rs`"
            "（R59 在這個 repo 真的發生過，見 local_ci_gate 檔頭）；②SKIPPED 行的格式"
            "變了（pytest 升版／輸出被某層重寫）。在修好之前，分群普查的每一格都不可信。"
            f"實際收到的尾段：{_tail(pytest_output)}"
        ]
    return []


# ── 天花板 ──────────────────────────────────────────────────────────────────────
#
# 🔴 判準形狀＝雙單邊（照 `TestR74IronLawMechanismAccounting` 的既有設計）：
#   · **天花板只准降**（由 `_RUNTIME_SKIP_CEILING_MAX` 守；上修必須同時顯式改兩個常數，
#     那是會出現在 diff 裡、需要在 PR 說明的決定，不是照著失敗訊息把數字改大就沒事）；
#   · **群數只准增**（census 出現未登記的群 ⇒ 紅；而「誠實登記一個新群」＝兩表各加一列，
#     當場是綠的）。沒有這一邊，最省力的滿足方式會變成「不要記錄新發現」——R72~R76 五類
#     新危害一項都沒進表，就是被單邊判準逼出來的。
#
#: 🔴 R80 包 A（S3-09）：剖面鍵**必須編碼「巢狀 Claude Code session」這個維度**。
#: 缺陷本體（當回合實查）：`AutoClaude/tests` 有一族 skip 的述詞是
#: `shutil.which("claude") is None or os.environ.get("CLAUDECODE") == "1"`
#: （`tests/test_gap014_020.py`／`tests/test_gap039_049.py`，本次實測 11 支），於是
#: 「在 Claude Code session 裡跑」與「schtasks nightly 跑」是**兩個不同的母體**，同一棵樹
#: 的健康值天生差一整族。剖面鍵不編碼它，天花板就在比不同的東西——而差異的方向是
#: 巢狀時 skip 較多，也就是「拿寬鬆的上限去管嚴格的環境」，失效方向仍是看起來很健康。
#: 對照組（誠實劃界）：`tools/tests` 那一棵**不受**這個維度影響——當回合以 Grep 對
#: `tools/tests` 全樹搜 `CLAUDECODE` 命中 0 ⇒ 該剖面鍵刻意不帶這一段，不是漏寫。
#:
#: 🔴 R90 包 C 訂正上一段的**現行蘊含**（原文在 R80 當時為真，故不刪除；過期的是它今天
#: 還在暗示的那件事）：那「一族 11 支」已經**不存在了**——R90／DEF-200-127 把
#: `test_gap014_020.py`／`test_gap039_049.py` 的 `requires_claude_cli` 述詞整個拿掉，
#: 11 支改掛 `@hermetic_runner`（patch 掉 `playbook_runner.PtyWrapper`）後在兩平台都真的跑。
#: 當回合實查：`AutoClaude/tests` 全樹搜 `CLAUDECODE` 只剩註解／docstring 命中，
#: **runtime 述詞 0 個** ⇒ `+nested` 這一段在今天的 `AutoClaude/tests` 上**鑑別力為 0**
#: （巢狀與非巢狀跑出來的 census 已經一樣）。
#: **本輪刻意不動剖面鍵**，兩個理由：① 拿掉 `+nested` 會改變 `_RUNTIME_SKIP_CEILING`／
#: `_RUNTIME_SKIP_CEILING_MAX` 的字典鍵，是 re-key 不是改數字，屬另案；② 鑑別力為 0
#: **不等於**應該拿掉——它是「這棵樹目前沒有巢狀專屬 skip」的記錄點，下一支寫出
#: `CLAUDECODE` 述詞的測試會讓它立刻恢復意義。承接：若連續數輪維持 0，再決定是否 re-key。
#:
#: 剖面鍵 ＝ `<樹>@<平台>+<能力>`。剖面是必要的：同一棵樹在「本機 PG 可用」與「沒有 PG」
#: 兩種狀態下的健康值差 92 支，用同一個數字管必然一邊沒有鑑別力、另一邊恆假紅；平台同理。
#: 剖面由呼叫端**實測**決定（local_ci_gate 探測完 PG 才知道自己在哪一格），不是由人宣告。
#:
#: R79 落地實測（Windows 11 Pro 26200、repo `.venv`、`AutoClaude` cwd、
#: `python -m pytest tests/ -q -rs --tb=line -p no:randomly`）：
#:   · `win32+nopg`（未設任何 DSN）＝136 支：platform 17／env-disabled 1／untagged 118
#:   · `win32+pg`（三個環境變數就位）＝44 支：platform 17／env-disabled 1／untagged 26
#: 兩次量測相隔數分鐘、同一棵樹，差別只有環境變數 ⇒ **92 支的差額全部是 `[ENV-DISABLED]`
#: 語意**，而它們今天多數還沒帶標籤（站點分佈在多個包的檔案裡，見 `untagged` 那一格）。
#:
#: 🔴 只登記 `win32` 兩個剖面是**誠實劃界**，不是遺漏：mac／Linux 的健康值本輪沒有量過，
#: 憑空填一個數字就是憑空造出一個沒有鑑別力的門檻。那兩個平台第一次跑到這裡時，判準會
#: 逐字報「剖面未登記（實測 {...}）」並要求以**當場實測值**入表——那正是它該有的行為。
#:
#: 🔴 `untagged` 這一格是本鎖唯一真正有牙的地方，也是它最脆弱的地方：R79 有六個包並行改樹
#: （量測期間樹已由 135 長到 136 支 skip），**收輪者必須以停工後的單人窗口重跑一次並重釘**。
_RUNTIME_SKIP_CEILING: dict[str, dict[str, int]] = {
    "AutoClaude/tests@win32+nopg+nested": {
        SKIP_GROUP_PLATFORM: 17,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 1,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 118,
    },
    # 🔴 R81 包 F（掌舵者訴求 S3「徹底解決 skipped」）重釘：44 → 37，`untagged` 23 → **0**。
    # 位移的部分是補標籤（env-disabled 1→12／structural-pair 0→1／debt 0→7），
    # 真正消掉的 7 支是**變成真的會跑**：sdk extra 裝起來（3）、sqlalchemy 缺件路徑改 patch
    # 模組旗標（1）、symlink fixture 在 Windows 改用複本（1）、pg_real 隨 PG autodetect
    # 一併自動啟用且語料改為就地 seed（2）。
    # 🔴 R82 包 A2 重釘：37 → 24。`platform` 17 → **5**（CARRIER-01：12 支
    # `[POSIX-NATIVE-ONLY]` 其實是載具解錯，換 Git Bash 絕對路徑後在 Windows 上 25 支全綠）、
    # `debt` 7 → **6**（DEBT-01：AC2-2 的門檻早就滿足，補上 `tests/contract/test_w6_deletion.py`
    # 即轉綠）。`env-disabled` 維持 12——本輪一度把 `PG_REAL_ENABLED` 接進 conftest 自動打開，
    # 實跑 `p95=51.703ms ≥ 50ms` 後判定那會製造 flaky 閘門，故回退為 opt-in（見該檔 reason）。
    # 值取自當回合 `pytest tests/ -q -rs` 實跑後對其 `skipped_reasons()` 逐支分群所得、
    # 非推算。🔴 該次的全套計數刻意不在此重述——基線數字唯一出處＝ONBOARDING.md §7
    # （本列六格之和即該次量到的 skip 總數，不需要第二個家）。
    "AutoClaude/tests@win32+pg+nested": {
        SKIP_GROUP_PLATFORM: 5,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 12,
        SKIP_GROUP_STRUCTURAL: 1,
        SKIP_GROUP_DEBT: 6,
        SKIP_GROUP_UNTAGGED: 0,
    },
    # 🔴 R84 包 W5（QA-03／QA-11）新登記：**mac 側的 AutoClaude 樹**此前一格判準都沒有
    # ——它既不在本表、也不在 `_FULL_SUITE_RUNNERS` 這個分母裡 ⇒ `ci_platform_coverage_
    # problems()` 對這一路回 `[]`（零問題）而不是回一筆缺口，也就是 mac 上這棵樹的 skip
    # 可以無聲從現值長到任意數字而所有閘門全綠（R79 立這道棘輪時寫的原話）。
    #
    # 🔴 值的取得方式（兩步，缺第二步時失敗表徵與「完全沒起 PG」逐字相同——見
    # `local_ci_gate.PG_UNMIGRATED_HINT` 與該檔剎車④）：
    #   ① `docker compose -f AutoClaude/docker-compose.ci.yml up -d`
    #   ② `cd AutoClaude && python -m alembic upgrade head`（rc=0）
    #   ③ `python -m pytest tests -q -rs` → 全套通過數見 ONBOARDING.md §7（SSOT，本檔
    #      刻意不複寫），skip 由 169 降為 73——差額 96 支全部是 PG 那一族，一支都沒掉
    #   ④ 值逐格照抄 `local_ci_gate.py --census-only` 當場印出的 `[skip census]` 那一行。
    #
    # 六格形狀本身就是 QA-11（「徹底解決 skipped」）的答案：`platform` 53 支全部是
    # `[WINDOWS-NATIVE-ONLY]`（mac 上沒有標的）；`env-disabled` 12 支裡有 11 支的述詞是
    # 「非巢狀 session」⇒ 它們在 mac 上**有**標的，只是要在 `+solo` 剖面才跑得到（那個剖面
    # 尚未量測，見 `_UNMEASURED_RUNNER_PROFILES`）；`tool-absence` 3 與 `structural-pair` 1
    # 是選配 extra（`[sdk]`／`pgvector`）未裝，裝了就會跑——刻意**不在本輪裝**：那會就地改掉
    # 本機 `.venv` 的母體，使這六格再也沒有人重量得出來（ONBOARDING 基線要求出廠環境）。
    # `debt` 3 全部指名承接 R84 且需要真實 BGE-M3 語料，不是設一個旗標就能還。
    #
    # 🔴 R90 補洞包 F 重釘：73 → 62（`env-disabled` 12 → **2**、`untagged` 1 → **0**，其餘四格
    # 逐格不變）。上一段那句「`env-disabled` 12 支裡有 11 支的述詞是『非巢狀 session』」**今天
    # 已為假**：R90 包 C（DEF-200-127）把 `test_gap014_020.py`／`test_gap039_049.py` 的
    # `requires_claude_cli` 述詞整個拿掉，那 11 支改掛 `@hermetic_runner` 後在本剖面真的會跑。
    # 🔴 為什麼這不是「順手整理」而是必修：包 C 讓 11 支變成真的會跑（＝真實成果），而天花板
    # 判準是 `實測 ≤ 上限` ⇒ `2 ≤ 12` **恆綠**，沒有任何機械物會為這 11 格轉紅 ⇒ 它們變成
    # 「日後可無聲加回去」的隱形額度，與本表下方 `_RUNTIME_SKIP_CEILING_MAX` 那句「天花板不
    # 跟著降＝把剛還掉的欠債額度留著，日後可無聲用回去」是同一句話、同一個病。
    # 值逐格照抄載具當場印出的那一行、零加減推算（本表既有紀律），原始整行：
    #   `[skip census] AutoClaude/tests@darwin+pg+nested 共 62 支：platform=53／tool-absence=3
    #    ／env-disabled=2／structural-pair=1／debt=3／untagged=0／欠債型 8 支（目標 0）`
    # 載具＝`python tools/local_ci_gate.py --census-only <log>`（rc=0），log 產自同一輪
    # `python -m pytest tests/ -q -rs --tb=line -p no:randomly`（rc=0；剖面標記逐字
    # `AUTOCLAUDE-PG-DSN-IN-EFFECT=1 AUTOCLAUDE-NESTED-SESSION=1`）。全套計數的唯一出處＝
    # ONBOARDING.md §7，本表不複寫。**只動 darwin 剖面**：win32 各剖面在 mac 上量不到，
    # 憑空改它就是憑空捏造（同本表「憑空填數字」那條紀律的反向）。
    "AutoClaude/tests@darwin+pg+nested": {
        SKIP_GROUP_PLATFORM: 53, SKIP_GROUP_TOOL_ABSENCE: 3,
        SKIP_GROUP_ENV_DISABLED: 2, SKIP_GROUP_STRUCTURAL: 1,
        SKIP_GROUP_DEBT: 3, SKIP_GROUP_UNTAGGED: 0,
    },
    # 🔴 R80 包 A（S3-04）：根層 `tools/tests` 那一棵此前**完全不在任何天花板管轄內**
    # （43 支 skip，`run_root_unittests.py` 只印不判、rc 與它無關）。本列即那道管轄的入表。
    # 值＝R80 當回合以 `python tools/run_root_unittests.py` 實跑後、由本模組對其
    # `all_skips()` 逐支分群所得（取得方式見 run_root_unittests.report_skip_census）。
    # 🔴 R81 包 F 重釘：43 → 41，`untagged` 5 → **0**。消掉的 2 支是
    # `TestRealSubMinInterpreterPrelude`——它的 skip 理由「找不到 < 3.11 的直譯器」是**假診斷**
    # （本機 pyenv 有 3.10.11，壞的是 pyenv-win 的 `.BAT` shim 且 rc!=0 被靜默 `continue` 吞掉），
    # 修好發現路徑後兩支都真的跑起來了。其餘為位移：zsh 兩支補 `[MAC-NATIVE-ONLY]`
    # （platform 38→40）、symlink 一支補 `[ENV-DISABLED]`（0→1）。
    # 🔴 R82 包 A2（CARRIER-02）重釘：41 → 38，`platform` 40 → **37**。消掉的 3 支是
    # `TestDevStartShShellCarrier` 的 bash 三支——它們的 skip 理由（`[POSIX-NATIVE-ONLY]`
    # 「不在 Windows 上驗證非目標平台的殼」）被實測推翻：Windows 上的 Git Bash 是真 bash，
    # 那七項契約走的就是 `.sh` 那條程式碼路徑。只把載具由 `shutil.which("bash")`
    # （回 System32 的 WSL 佔位版）換成 `usable_bash_for_fixture()` 就真的跑起來了。
    # 當回合實測：`[skip census] tools/tests@win32 共 38 支：platform=37／env-disabled=1
    # ／其餘 0／欠債型 1 支`。
    # 🔴 R96（Windows 側自 R82 以來首次重跑）**上修**：38 → 42，`platform` 37 → **41**。
    # 依本表上方那條規則，上修必須「同時顯式改兩個常數」＋在此寫明理由，故逐項交代：
    #   · 多出來的 4 支**全部**是 `test_dev_start.TestMacNightlyMachineStateCapabilities`
    #     （`test_a_mac_with_no_power_schedule_at_all_flags_both_rows`／
    #      `test_a_machine_without_pmset_is_reported_distinctly`／
    #      `test_a_one_shot_wake_event_does_not_count_as_the_daily_repeat`／
    #      `test_a_one_shot_wakeorpoweron_is_not_mistaken_for_the_daily_repeat`）。
    #   · 🔴 R96 二審訂正：第 4 支原本寫成「第 4 支同類」＝不具名。本表的整段紀律是「值逐格
    #     照抄載具當場印出的那一行、零加減推算」「代填＝假 provenance」，留一支不具名就違反
    #     它自己——而那個名字用 AST 對 `tools/tests/test_dev_start.py` 的
    #     `TestMacNightlyMachineStateCapabilities` 列舉 `test_` 開頭方法即得（本輪實跑列舉，
    #     四支逐字如上；Architect 與 SD 二審各自獨立查到同一個名字）。
    #   · 來源已查到 commit：`git log -S TestMacNightlyMachineStateCapabilities` → **`bc024e3`
    #     （R83，mac 真機首輪）**。那一輪在 mac 上它們是**真的跑**的；在 Windows 上必然 skip。
    #   · **為什麼不走「讓它們真的會跑」那條合法出口**（本表偏好的那一條）：這一類繼承
    #     `MacNightlyStatusTestCase`，受測對象是 `tools/install_mac_nightly.sh`，而該檔對
    #     非 Darwin **直接 fail-loud**（`uname != Darwin` guard），且本組的自變數是 `pmset`
    #     排程、`plutil` 輸出與 BSD `date -v` 語意。要在 Windows 上跑起來等於偽造整個 BSD
    #     userland ⇒ 測到的是我們自己造的假環境，不是那支腳本的真實行為（該群 skip 理由
    #     逐字寫的「非 macOS 上執行本身即為無意義假訊號」正是這件事）。⇒ 結構上跑不到。
    #     對照組：R82 那次之所以能把 3 支從 skip 救回來，是因為 Windows 上的 Git Bash **是真
    #     bash**；本輪這 4 支沒有對等的「真 pmset／真 plutil」，兩者不同構。
    # 🔴 這筆紅的形態值得單獨記下來，因為它**不是缺陷、是本判準的結構性後果**：mac 輪合法
    # 新增 mac-only 測試 ⇒ Windows 側 `platform` 群必然上升；而本表下方 darwin 那幾列的註解
    # 逐字寫著「**只動 darwin 剖面**：win32 各剖面在 mac 上量不到」（代填就是假 provenance）
    # ⇒ 兩邊都做對事，這一格仍然會在**下一次 Windows 開工時**變紅，反方向（Windows 輪新增
    # `[WINDOWS-NATIVE-ONLY]` ⇒ mac 側必紅）完全同構。R83→R96 之間隔了 13 輪、期間 4 支
    # 累積在暗處，沒有任何機械物會提前說話。⇒ 判準形狀本身有改善空間（把「總量計數」換成
    # 「test-id 集合」，先例＝R86 把 M6 判準粒度升為 test-id 集合），但那會同時改動 mac 側的
    # 判定、且無法在本平台驗，故本輪只誠實上修並留下這段診斷，不擅自改判準形狀。
    # 🔴 R100（DEF-200-228）：`env-disabled` 1 → **2**——本輪在
    # `tools/tests/test_context_budget_guard.py:3108` 新增第二個具名 `[ENV-DISABLED]`
    # 站點（`ConsoleFreeSpawnTest`：本機 codepage 已是 UTF-8 時的 skip 分支），與既有
    # `tools/tests/_platform_helpers.py:258`（R81，`create_symlink_or_skip`）同群但條件
    # 互不相依。🔴 誠實劃界：本輪**沒有**真 Windows CI 跑出新的 census 逐格照填（不像
    # R100 linux 表那樣）——這裡是**站點盤點式**上修：兩個具名站點各自成立即代表這一群
    # 至少會有 2，不是從聚合 census 推算。下次 windows-compat-ci 真跑時仍須覆核實測值，
    # 若兩支同時觸發以外的組合出現（例如只觸發一支），本格會偏保守（上限給多了不會判紅，
    # 只有反向才會）。
    "tools/tests@win32": {
        SKIP_GROUP_PLATFORM: 41,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 2,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 0,
    },
    # 🔴 R80 包 C（QA-R80-01）：Linux 剖面的**實測值今天有了**——`act` 在 Linux 容器實跑
    # root-infra 那支 job，`run_root_unittests.py` 自己印出
    # `[skip census] tools/tests@linux 共 72 支：platform=63／untagged=9／欠債型 9 支（目標 0）`
    # 並附「⚠️ 剖面未登記——量測正常，但這個平台從來沒有人量過健康值」。工具訊息逐字寫著
    # 「把上面那行實測值填進 skip_group_policy 兩張表即升級為阻斷」，本列就是照做。
    # 值是**量出來的**不是推算的（上方 win32 兩列的同一條紀律）；未列出的群實測即 0。
    # 🔴 R83（mac 真機首輪）新登記：`tools/tests@darwin` 此前只在 `_UNMEASURED_RUNNER_PROFILES`
    # 內，而那一格的註解逐字寫著「本輪沒有 mac 真機，macOS CI 又是 `steps=0` ⇒ 健康值今天
    # 無論如何取不到。憑空填數字＝憑空造出一個沒有鑑別力的門檻，故只登記缺口」。
    # **今天取得到了**：本輪在 macOS 真機上跑完 `python tools/run_root_unittests.py`，值取自
    # 它當場印出的 `[skip census] tools/tests@darwin` 那一行、逐格照填、零加減推算。
    # 🔴 這一筆使 darwin 的 skip 剖面由 **advisory 升為阻斷**——升級前 runner 對這棵樹印的是
    # 「⚠️ 剖面未登記——量測正常，但這個平台從來沒有人量過健康值，沒有天花板可比」，
    # 也就是 darwin 上的 skip 可以無聲從現值長到任意數字而所有閘門全綠。
    # 六格的形狀本身就是本輪主結論的證據：`platform` 獨大而其餘五格皆 0 ⇒ mac 側的 skip
    # **全部**是「在這個平台沒有標的」（`schtasks`／具名 Mutex／PS 5.1 原生 argv 語意…），
    # 零欠債、零未標籤 ⇒ 單機零 skip 結構上不可能，可達成的是**兩平台聯集**零 skip。
    # 🔴 R100（三方 CI 全紅收尾）：本輪在 mac 真機上重跑 `python3 tools/run_root_unittests.py`
    # 驗證 darwin 值——實測 `[skip census] tools/tests@darwin 共 44 支：platform=44／
    # tool-absence=0／env-disabled=0／structural-pair=0／debt=0／untagged=0`，逐格與現值
    # 相同（含 `untagged` 本就是 0，證實 darwin 這棵樹的 9 支 CI-only untagged 純粹是雲端
    # `actions/checkout@v5` 預設 `fetch-depth: 1` 淺層 clone 造成，真機全歷史 checkout 下
    # 結構上不會重現）⇒ **本表本輪不動**，只留此註記佐證。
    "tools/tests@darwin": {
        SKIP_GROUP_PLATFORM: 44,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 0,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 0,
    },
    # 🔴 R100（root-infra-ci／macos-compat-ci／windows-compat-ci 三方 CI 全紅收尾）上修：
    # 63→**77**、`untagged` 9→**0**、`tool-absence` 0→**2**。取得方式＝本機 `act`（重建
    # `aisdcl-act/ubuntu:act-latest` 為 **linux/amd64**——舊映像是本機 Apple Silicon 原生
    # arm64 build，與 `.actrc` 釘的 `--container-architecture linux/amd64` 不符，pull 會
    # 401；`docker build --platform linux/amd64 …` 重建後才真的跑得動）真跑
    # `root-infra-ci.yml` 的 `root-infra` job（`.github/workflows/root-infra-ci.yml` 同輪已
    # 補 `actions/checkout@v5` 的 `fetch-depth: 0`），`run_root_unittests.py` 當場印出：
    #   `[skip census] tools/tests@linux 共 79 支：platform=77／tool-absence=2／
    #    env-disabled=0／structural-pair=0／debt=0／untagged=0／欠債型 2 支（目標 0）`
    # 逐格照填、零加減推算（本表既有紀律）。
    # ① `untagged` 9→0：這 9 支正是 `test_sanitize_component_frozen_sdd_versions_lock.py`
    #    的 7 支 ＋ `test_doc_loc_baseline_freshness_r60.TestR74CloudCiStatusIsRecorded` 的
    #    2 支——它們的 skip 理由都寫著「可能是淺層 clone 缺歷史」（判準讀
    #    `git rev-parse --is-shallow-repository`），而 `fetch-depth: 0` 讓歷史變完整後這 9
    #    支全部真的跑了，不再落 untagged。
    # ② `platform` 63→77（+14）：**合法新增，非 regression**——`git log -S` 逐一查證，14 支
    #    全部是既有 mac-only（`[MAC-NATIVE-ONLY]`）／win-only（`[WINDOWS-NATIVE-ONLY]`）測試
    #    在 linux 剖面的必然互補結果，其中 4 支（`TestMacNightlyMachineStateCapabilities`）
    #    正是 R96 已經讓 win32 的 `platform` 37→41 上修過的同一批——**linux 表自 R80 登記後
    #    未跟著同步重測**，這次補齊差額，不是本輪新長出的測試。
    # ③ `tool-absence` 0→2：`TestRealSubMinInterpreterPrelude.test_dev_start_prelude_loads_
    #    and_gate_fires_friendly` ／ `.test_documented_bootstrap_remediation_actually_loads`
    #    ——`root-infra-ci.yml` 的 `root-infra` job 只用 `setup-python` 裝單一 3.11，
    #    PATH 上找不到 < 3.11 的直譯器（無 pyenv、無 `py` launcher、無 python3.7~3.10）。
    #    真實環境缺件，不是判準誤判；`SKIP_TARGET_ZERO` 群理論上可歸零（CI job 多裝一支
    #    舊直譯器即可），本輪未動 workflow，故如實登記為現況而非上修判準去遷就它。
    # 🔴 誠實劃界：本次 `act` 用 Docker Desktop 的 Rosetta amd64 加速（非純 QEMU），跑出
    # `FAILED (failures=1, skipped=79)`——那 1 支失敗
    # （`test_context_budget_guard.PlannerCliTest.test_check_prints_usage_and_writes_
    # nothing`）斷言一個隔離 HOME 底下的目錄樹在 CLI no-op 呼叫後保持不變，而 Rosetta 在
    # 該 HOME 底下生出 `home/.cache/rosetta` 快取目錄，是**本機 Docker Desktop Rosetta
    # 轉譯層的副作用**、與被測程式碼邏輯無關、真 GitHub ubuntu-latest runner（原生 amd64，
    # 無 Rosetta）不會重現——故本輪未動該測試，也未把它算進上面的 skip census（它是
    # failure 不是 skip）。
    "tools/tests@linux": {
        SKIP_GROUP_PLATFORM: 77,
        SKIP_GROUP_TOOL_ABSENCE: 2,
        SKIP_GROUP_ENV_DISABLED: 0,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 0,
    },
}

#: 上表各格的 shrink-only 天花板（理由與 `_POSIX_TAG_RATCHET_CEILING` 完全相同：
#: 沒有它，「把上限改大」就是零阻力的合法出口，欠債可以無聲增長且看起來像在維護基線）。
#: 🔴 數值刻意**逐格寫死**，不得寫成 `{p: dict(g) for …}` 之類由上表推導的形式：那樣兩張表
#: 恆等，「上限高於天花板」這一向結構上永遠不可能觸發＝又一道沒有鑑別力的鎖（第一版就是
#: 那樣寫的，當回合自查發現）。兩張表必須是兩份獨立的字面值，diff 才看得見有人在加大額度。
#: 🔴 **逐格共用的三條規則收在這裡（本輪收斂：原本每一格各抄一份，同一份知識住三個家）**：
#: ①新登記的剖面天花板**不留餘裕**（留餘裕＝一上線就給它一個可以無聲成長的窗口）；②下修時
#: 兩張表同鍵**一起**改成新實測值，只調本表＝把已還掉的欠債額度重新開回去；③代價要寫清楚
#: 否則下一個人會照失敗訊息把 MAX 調大——新增任何一支 `[WINDOWS-NATIVE-ONLY]` 根層測試會讓
#: 根層閘門當場紅（R84／QA-04 就地確認零餘裕是刻意的，實測兩張表同鍵 headroom 皆 0）。
_RUNTIME_SKIP_CEILING_MAX: dict[str, dict[str, int]] = {
    "AutoClaude/tests@win32+nopg+nested": {
        SKIP_GROUP_PLATFORM: 17,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 1,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 118,
    },
    # 🔴 R82：連同基線一起下修（platform 17→5、debt 7→6；理由見 _RUNTIME_SKIP_CEILING）。
    "AutoClaude/tests@win32+pg+nested": {
        SKIP_GROUP_PLATFORM: 5,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 12,
        SKIP_GROUP_STRUCTURAL: 1,
        SKIP_GROUP_DEBT: 6,
        SKIP_GROUP_UNTAGGED: 0,
    },
    # 🔴 R90 補洞包 F：連同基線一起下修（`env-disabled` 12 → 2、`untagged` 1 → 0；理由與
    # census 原始整行見 `_RUNTIME_SKIP_CEILING` 同鍵那一段。同輪改兩表、無餘裕＝本表紀律②③）。
    "AutoClaude/tests@darwin+pg+nested": {
        SKIP_GROUP_PLATFORM: 53, SKIP_GROUP_TOOL_ABSENCE: 3,
        SKIP_GROUP_ENV_DISABLED: 2, SKIP_GROUP_STRUCTURAL: 1,
        SKIP_GROUP_DEBT: 3, SKIP_GROUP_UNTAGGED: 0,
    },
    # 🔴 R82（CARRIER-02）：連同基線一起下修 40 → 37（天花板不跟著降＝把剛還掉的
    # 欠債額度留著，日後可無聲用回去——這句話是本表自己的既有紀律）。
    # 🔴 R96：`platform` 37 → **41**，與 `_RUNTIME_SKIP_CEILING` 同鍵**同一個 commit** 一起上修
    # （本表上方那條規則要的就是這個「兩個常數都得動、會出現在 diff 裡」）。完整理由、來源
    # commit（`bc024e3`／R83）、以及「為什麼這 4 支不走『讓它們真的會跑』那條出口」逐項寫在
    # `_RUNTIME_SKIP_CEILING` 同鍵那一段，此處不複寫第二份（同一份知識只准一個家）。
    # 🔴 R100（DEF-200-228）：`env-disabled` 1 → **2**，與 `_RUNTIME_SKIP_CEILING` 同鍵
    # 同一個 commit 一起上修；理由（站點盤點式、非聚合 census）見同鍵那一段。
    "tools/tests@win32": {
        SKIP_GROUP_PLATFORM: 41,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 2,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 0,
    },
    "tools/tests@darwin": {
        SKIP_GROUP_PLATFORM: 44,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 0,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 0,
    },
    # 🔴 R100：連同基線一起上修 63→77／`untagged` 9→0／`tool-absence` 0→2——理由、
    # provenance、逐項交代皆見 `_RUNTIME_SKIP_CEILING` 同鍵那一段，此處不複寫第二份。
    "tools/tests@linux": {
        SKIP_GROUP_PLATFORM: 77,
        SKIP_GROUP_TOOL_ABSENCE: 2,
        SKIP_GROUP_ENV_DISABLED: 0,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 0,
    },
}

# ── S3-02 ／🔴 QA-R80-01：分母是**執行者剖面**，不是平台 ────────────────────────
#
# 原始缺陷（S3-02）：唯一會跑整套 AutoClaude/tests 的 CI job 在 ubuntu，而天花板表一個
# linux 剖面都沒有 ⇒ 那道棘輪**在雲端零阻斷力**（`--census-only` 對未登記剖面回 advisory）。
#
# 🔴 R80 包 C（QA-R80-01）把分母由「平台」換成「剖面」，因為 R80 自己給剖面鍵加了第三個
# 維度（`+nested`／`+solo`）之後，平台粒度就不再等於「一個會真的跑完整棵樹的執行者」：
# `AutoClaude/tests@win32+nopg+nested`（pre-push，在 Claude Code session 內）已登記，但
# **同一棵樹、同一個平台**的 `…+solo`（nightly／schtasks）從來沒有人量過；平台層的判準看到
# 「win32 已登記」就整格放行 ⇒ nightly 那一路的天花板由「有牙」退化成 advisory
# （`profile_registered()` 為 False ⇒ 消費端只印不判）。R79 立這道棘輪的理由逐字是
# 「skip 可以無聲從 43 長到 143 而閘門全綠」——nightly 今天正好回到那個狀態，而缺口帳
# 只記平台 ⇒ 這件事既不會被修，也不會被想起來（本 repo 判過的第 10 號形態：劃界不等於防護，
# 所以它**不能**只寫成一句註解）。
#
# 判準形狀＝雙單邊（同 `TestR74IronLawMechanismAccounting`），刻意**不是** shrink-only 上限：
#   · 分母 `_FULL_SUITE_RUNNERS` 只准增（少一列＝有人把一個執行者從帳上抹掉）；
#   · 分子「已登記天花板的執行者數」只准增；
#   · 未量測數＝分母−分子，**刻意不設上限**——舊版的 `_UNMEASURED_CI_PLATFORMS_MAX = 1`
#     正是「誠實登記一個新缺口要付代價」的那個代價：本輪誠實補上 nightly solo 就會當場撞
#     線，而最省力的滿足方式會變成不要登記（R74 已為同一個病寫過整段判詞）。
#   · 代價由另一邊補回來：每一筆未量測**必須具名寫出承接輪次**（大寫 R 加輪號），否則紅。
_FULL_SUITE_RUNNERS: dict[str, str] = {
    "AutoClaude/tests@linux+nopg+solo": "autoclaude-ci.yml 的 test job（ubuntu-latest）",
    "AutoClaude/tests@win32+nopg+nested": "pre-push 的 AutoClaude leg（在 CC session 內）",
    # 🔴 R82 包 A2（RUNNER-01）改鍵：`+nopg+solo` → `+pg+solo`。舊鍵**結構上永遠量不到**
    # ——PG 容器長駐（`docker ps` → `autoclaude_pg | Up | pgvector/pgvector:pg18`），而
    # `tests/conftest.py::pytest_configure` 在收集之前就 autodetect 並注入 DSN ⇒ nightly
    # 一定落在 `+pg+solo`。實證：`AutoClaude/logs/nightly_latest.log` 第 173~175 行逐字印著
    # `[skip census] AutoClaude/tests@win32+pg+solo …` ＋「⚠️ 剖面未登記」。也就是說帳上
    # 那個「已登記的執行者」指的是一個不存在的執行者，而每天真的在跑的那一個一格判準都沒有
    # ——這正是 R79 立這道棘輪時寫的「skip 可以無聲從 43 長到 143 而閘門全綠」。
    "AutoClaude/tests@win32+pg+solo": "run_local_nightly.ps1／schtasks nightly（非巢狀）",
    # 🔴 R84 包 W5（QA-03）新登記：mac 真機上的 pre-push AutoClaude leg。此前**平台層與剖面層
    # 都沒有它**——`_platform_of` 的派生視圖裡 darwin 已被 `tools/tests@darwin` 佔位，於是平台
    # 那一向也看不到缺口 ⇒ 這一路是「回 [] 而不是回一筆缺口」，比未量測更難發現。
    # 本列與天花板同輪入表（分母升、分子亦升，兩者都是只准增的方向）。
    "AutoClaude/tests@darwin+pg+nested": "pre-push 的 AutoClaude leg（mac 真機，在 CC session 內）",
    # 🔴 R82 包 A2（MAC-01）新登記：`macos-compat-ci.yml` 的 macOS smoke job 逐字
    # `run: python3 tools/run_root_unittests.py`＝一個貨真價實的 full-suite darwin 執行者，
    # 卻從來不在這張分母表裡 ⇒ 26 支 `[MAC-NATIVE-ONLY]` 的互補剖面連「有沒有人量過」
    # 都問不出來。誠實登記＝分母升、分子不動，本判準刻意不因此轉紅（雙單邊設計）。
    "tools/tests@darwin": "macos-compat-ci.yml 的 macOS smoke job（run_root_unittests.py）",
    "tools/tests@linux": "root-infra-ci.yml（ubuntu-latest）＋本機 act 跑的同一支 job",
    "tools/tests@win32": "pre-push 的 root leg／直跑 tools/run_root_unittests.py",
    # 🔴 R82 包 A2（SDD-01）新登記：第三棵樹此前**完全不在 skip 治理射程內**。
    # 實測 `AISDLC_SDD_v0.30` 下 `pytest tools/fsm_runtime/tests -m "not chaos"` 的
    # skip 共 6 支（該樹的全套計數見 ONBOARDING.md §7 表②，此處不重述一份基線數字），
    # 而 `AISDLC_SDD/scripts/ci-gate.sh` 全檔對 census 零命中、
    # 上面五個鍵沒有一個屬於這棵樹 ⇒ 它的 skip 可以無聲從 6 長到 60 而所有閘門全綠
    # （R79 立這道棘輪時寫的原話）。誠實登記＝分母升、分子不動。
    "AISDLC_SDD/fsm_runtime@win32": "AISDLC_SDD/scripts/ci-gate.sh（LATEST 版 fsm_runtime 全套）",
}
#
# 🔴 每一列的值＝「怎麼把它量出來」的可貼指令 ＋ 帳本列。散文寫在**註解**裡（註解不計
# `count_loc`，而本檔已貼著 guardrail_lib 的 400 行分級——把 WHY 塞進字串會直接撞線）。
#
# · `AutoClaude/tests@linux+nopg+solo`：R80 原理由逐字是「本機沒有 Linux runner」，R82 訂正
#   ——本機**有**，`docker images` 內的 `aisdcl-act/ubuntu:act-latest` 就是 root-infra-ci／
#   autoclaude-ci 用的同一顆映像（R82 已用它實跑 `73 passed, 1 skipped`）。雲端那條路今天走
#   不通（macOS/ubuntu job 自 2026-08-05 起 8 連跑 `steps=0`＝帳務未付、一個 step 都沒開始）。
# · `AutoClaude/tests@win32+pg+solo`：nightly（非巢狀）與 pre-push 是兩個母體——一族 skip 的
#   述詞含 `CLAUDECODE == '1'`，巢狀多 skip ⇒ 拿 nested 的上限管 solo 是拿寬鬆的管嚴格的。
#   本輪只改了鍵（`+nopg` → 實際量得到的 `+pg`），值刻意**不填**：nightly log 現有那組數字取
#   自 R82 補標籤之前的樹，照抄會把已經還掉的欠債重新寫成合法額度。
# · `tools/tests@darwin`：🔴 **R83 已畢業、不再是本表成員**（R82 的「沒有 mac 真機 ⇒ 健康值
#   取不到，只登記缺口」在當時為真；R83 有真機後值已逐格照填並移入兩張天花板表）。這一族散文
#   **沒有任何機械物在守**，所以它在同一個變更內被自己的改動證偽時是靜默的。
# · `AISDLC_SDD/fsm_runtime@win32`：本輪首次進帳（6 支 skip 已全數補標），但 census 還沒接上
#   它的閘門 ⇒ 數字量得到、卻沒有任何東西在讀。🔴 先接閘門再入表，順序不可顛倒——先填數字
#   只會得到一個沒有消費者的常數。
_UNMEASURED_RUNNER_PROFILES: dict[str, str] = {
    "AutoClaude/tests@linux+nopg+solo":
        "取得＝act 映像跑 pytest，輸出餵 `local_ci_gate.py --census-only`。DEF-101-960",
    "AutoClaude/tests@win32+pg+solo":
        "取得＝跑 run_local_nightly.ps1 後抄 nightly_latest.log 的 `[skip census]`。DEF-101-960",
    "AISDLC_SDD/fsm_runtime@win32": "取得＝ci-gate.sh 接 `--census-only` census。DEF-101-960",
}
#: 雙單邊的兩個**下限**（取代舊的 shrink-only 上限，理由見上方）：分母與分子都只准增。
#: 🔴 **分子上修的唯一合法條件（三次上修共用同一條，本輪收斂成一份）：那個剖面「真的被量到」
#: ——值逐格照抄載具當場印出的 `[skip census]`、零加減推算，且同輪寫進 `_RUNTIME_SKIP_CEILING`
#: 與 `_RUNTIME_SKIP_CEILING_MAX`（無餘裕）。只登記缺口而沒量到時，分子必須不動**，否則就是
#: 鼓勵「憑空填數字」；方向相反的兩件事共用一個數字，那個數字就不再有語意。沿革（分母／分子）：
#: R82 5→7／3 不動（兩筆都只是登記缺口）；R83 7 不動／3→4（`tools/tests@darwin`，首個 mac 真機
#: 輪）；R84 7→8／4→5（`AutoClaude/tests@darwin+pg+nested` 同輪量到）。前兩次的「分子不動 vs
#: 下一行已是 4」自相矛盾由獨立驗證者點名，不是自己發現的——這一族散文零機械物在守。
_FULL_SUITE_RUNNERS_MIN = 8
_MEASURED_RUNNERS_MIN = 5
#: 未量測列必須指名一個**帳本列**當承接處。刻意要 DEF-ID 而不是「R<下一輪>」字面：後者
#: 是在程式碼裡宣稱一個還沒發生的輪號（本 repo 另有一道全樹掃描在擋這件事），而承接輪次
#: 本來就該只有帳本一個家——註解裡寫「還沒量」則是判過的第 10 號形態（劃界不等於防護）。
_HANDOVER_POINTER_RE = re.compile(r"DEF-\d+-\d+")

#: 平台層是由上面兩張表**派生**的視圖，不是第二個家——保留這兩個名字是因為既有消費端與
#: 既有回歸鎖讀的是它們（`AutoClaude/tests/tools/test_local_ci_gate.py`）。派生規則：一個
#: 平台上任一執行者未量測，該平台即算「未量測」。
def _platform_of(profile: str) -> str:
    return profile.split("@", 1)[1].split("+", 1)[0]


_CI_FULL_SUITE_PLATFORMS: dict[str, str] = {
    _platform_of(p): w for p, w in _FULL_SUITE_RUNNERS.items()}
_UNMEASURED_CI_PLATFORMS: dict[str, str] = {
    _platform_of(p): w for p, w in _UNMEASURED_RUNNER_PROFILES.items()}


# 純函式：會跑整棵樹、卻沒有登記健康值的**執行者剖面**。回空 list ＝帳算得清。
#
# 五向：①分母縮水 ②分子縮水 ③未登記又未具名豁免 ④已登記卻還掛在豁免表（把有人守的
# 寫成沒人守，與反向同樣是假事實）⑤具名豁免卻沒指名承接帳本列（＝沒有承接者的永久缺口）。
# 另保留平台層那一向：一個**整個平台**都沒有任何執行者入帳時仍要紅（例：日後新增 macOS
# full-suite job），那是派生視圖唯一還有鑑別力的地方。
#
def ci_platform_coverage_problems() -> list[str]:
    problems: list[str] = []
    measured = [p for p in _FULL_SUITE_RUNNERS if profile_registered(p)]
    if len(_FULL_SUITE_RUNNERS) < _FULL_SUITE_RUNNERS_MIN:
        problems.append(
            f"會跑整棵樹的執行者只剩 {len(_FULL_SUITE_RUNNERS)} 筆 < 下限 "
            f"{_FULL_SUITE_RUNNERS_MIN}——這張表是**分母**，只准增。少一列代表有人把一個"
            "執行者從帳上抹掉，而缺口會跟著從視野裡消失")
    if len(measured) < _MEASURED_RUNNERS_MIN:
        problems.append(
            f"已量測的執行者只剩 {len(measured)} 筆 < 下限 {_MEASURED_RUNNERS_MIN}"
            "——這是**分子**，只准增。拆掉一個已登記的剖面就是把它退回 advisory")
    for profile, where in _FULL_SUITE_RUNNERS.items():
        exempt = _UNMEASURED_RUNNER_PROFILES.get(profile)
        if profile_registered(profile):
            if exempt is not None:
                problems.append(
                    f"執行者 `{profile}` 已經登記天花板了，卻還留在 _UNMEASURED_RUNNER_"
                    "PROFILES 裡——把已經有人守的東西寫成沒人守，與反向一樣是假事實，請刪掉")
        elif exempt is None:
            problems.append(
                f"執行者 `{profile}`（{where}）會跑完整棵樹，但 _RUNTIME_SKIP_CEILING 沒有"
                "它的剖面、_UNMEASURED_RUNNER_PROFILES 也沒有具名豁免 ⇒ 這道棘輪在那一路"
                "上零阻斷力（消費端只印不判），而且沒有任何地方登記過這件事")
        elif not _HANDOVER_POINTER_RE.search(exempt):
            problems.append(
                f"執行者 `{profile}` 具名豁免了，但豁免理由沒有指名承接的帳本列（形態 "
                "`DEF-x-y`）——沒有承接者的缺口就是永久缺口，而它今天長得像已經登記好了")
    accounted = {_platform_of(p) for p in _FULL_SUITE_RUNNERS}
    for platform in _CI_FULL_SUITE_PLATFORMS:
        if platform not in accounted:
            problems.append(
                f"平台 `{platform}` 上有 job 會跑整棵樹，但 _FULL_SUITE_RUNNERS 一個執行者"
                "剖面都沒有 ⇒ 它連分母都沒進去，上面每一向都判不到它")
    return problems


# 🔴 存在理由（R79 收輪）：「剖面未登記」與「天花板被突破」在 `skip_group_census_problems`
# 裡是同一種回傳值，但它們對呼叫端是**兩件不同的事**——前者代表這台機器／這個平台從來
# 沒有人量過（mac、Linux runner 第一次跑到這裡就是這一格），後者代表 skip 真的變多了。
# push 通道要能擋住後者、又不能因為前者就把一個沒人量過的平台整個擋在門外（那是誤擋，
# 不是鑑別力）。分開才有辦法讓兩者各自對應到正確的處置，而不是二選一。
#
# 🔴 R83／G2：本段由 docstring 改為 `#` 註解，**一字未刪、語意零變更**。理由是
# `check_loc_budget.py` 自己印的指引逐字寫著「說明文字請寫成 `#` 註解而非 docstring
# ——docstring 行會被 count_loc 計入」；本檔在 R83 登記 `tools/tests@darwin` 兩張天花板
# 之後 count_loc 由 400 漲到 415，破了 `guardrail_lib<=400`（同輪先例：
# `AutoClaude/autoclaude/plugins/token_guard/policy.py` R82 同款處置）。
# 🔴 **本檔多處說明皆為此形態（一字未刪、語意零變更），各站點不再逐一複述這段理由**
# （本輪收斂：同一份 provenance 原本住七個家，而它們沒有一個會因彼此不一致而轉紅）。
def profile_registered(profile: str) -> bool:
    """這個剖面有沒有登記過天花板。"""
    return profile in _RUNTIME_SKIP_CEILING and profile in _RUNTIME_SKIP_CEILING_MAX


# 🔴 R80 包 A（S3-03）存在理由——舊判準的形狀是錯的，而且錯在它自己宣傳的出口上：
# 舊訊息逐字寫著「合法出口只有『把那些測試變成真的會跑』或『**補上正確的分群標籤**』」，
# 但「補標籤」做的事就是把一支 skip 從 `untagged` 搬進某個具名群，那一群的計數必然 +1
# ⇒ 該群當場超過上限 ⇒ **照著失敗訊息做，就會被同一道判準判紅**。
# 當回合注入實測（三組，逐字見包 A 回報）：
#   · untagged 118→0、env-disabled 1→119（純補標籤，總量一支沒變）⇒ 舊判準回 1 筆問題；
#   · untagged 118→112、platform 17→20（總量 136→133，**樹變健康了**）⇒ 舊判準回 1 筆問題；
#   · untagged 118→115（單純變少）⇒ 綠。
# 也就是說：**唯一不會被罰的改善方式是「skip 憑空消失」**，而那正是本 repo 最不該鼓勵的
# 那一種（R76 記過的「看起來變乾淨」）。分群天花板必須對「群間位移」保持中立，
# 只對「總量上升」與「未分類的欠債上升」說話。
# 純函式：這次執行從 `untagged` **搬出去**了幾支（＝補標籤的額度）。
def retag_budget(profile: str, census: Mapping[str, int]) -> int:
    ceilings = _RUNTIME_SKIP_CEILING.get(profile) or {}
    return max(0, ceilings.get(SKIP_GROUP_UNTAGGED, 0)
               - census.get(SKIP_GROUP_UNTAGGED, 0))


# 分群天花板的判準（純函式）。回空 list ＝合格。
#
# 六向：①剖面未登記 ②**總量**超過上限 ③某群超過「上限＋補標籤額度」 ④上限高於
# shrink-only 天花板 ⑤census 出現未登記的群 ⑥`[DEBT]` 的 reason 沒寫承接輪次。
#
# ②③ 的分工就是 S3-03 的修法：總量那一道是真正有牙的（skip 變多一定紅），分群那一道
# 只在「這一群變多、而且**不是**從 untagged 搬過來的」時候才紅。誠實劃界：兩支 untagged
# 被修好、同時新增兩支 env-disabled，在本判準下是綠的（總量不變、額度剛好抵銷）——
# 要抓那一種，靠的是 `skip_tag_policy` 的靜態站點面，不是這裡的計數面。
#
def skip_group_census_problems(
    profile: str,
    census: Mapping[str, int],
    *,
    reasons: Iterable[str] = (),
) -> list[str]:
    problems: list[str] = []
    ceilings = _RUNTIME_SKIP_CEILING.get(profile)
    ceiling_max = _RUNTIME_SKIP_CEILING_MAX.get(profile)
    if ceilings is None or ceiling_max is None:
        return [
            f"剖面 `{profile}` 未登記於 skip_group_policy._RUNTIME_SKIP_CEILING"
            f"／_RUNTIME_SKIP_CEILING_MAX（實測 {dict(census)}）——新剖面必須顯式入表，"
            "否則它的 skip 數靜默不受管轄"
        ]
    budget = retag_budget(profile, census)
    total_got = sum(census.get(g, 0) for g in set(census) | set(ceilings))
    total_cap = sum(ceilings.values())
    if total_got > total_cap:
        problems.append(
            f"{profile}／**總量**：實測 {total_got} 支 > 上限 {total_cap}——skip 真的變多了。"
            "🔴 合法出口只有「把那些測試變成真的會跑」，不是把上限調大"
        )
    for group in sorted(set(census) | set(ceilings) | set(ceiling_max)):
        got = census.get(group)
        ceiling = ceilings.get(group)
        cap = ceiling_max.get(group)
        if ceiling is None or cap is None:
            problems.append(
                f"{profile}／群 `{group}`：實測 {got} 支，但這一群不在天花板表內"
                "——新的 skip 語意群必須顯式登記（兩張表各補一列即為合格；"
                "分群只准變多，這一向刻意不會因為「誠實登記新發現」而轉紅）"
            )
            continue
        if ceiling > cap:
            problems.append(
                f"{profile}／群 `{group}`：上限 {ceiling} 高於 shrink-only 天花板 {cap}"
                "——skip 額度只准變少。要真的加大，必須在同一個 commit 顯式上修 "
                f"skip_group_policy._RUNTIME_SKIP_CEILING_MAX['{profile}']['{group}'] 並說明理由"
            )
        # `untagged` 不吃額度（額度就是它自己讓出來的），其餘各群可吃。
        allowance = ceiling if group == SKIP_GROUP_UNTAGGED else ceiling + budget
        if got is not None and got > allowance:
            problems.append(
                f"{profile}／群 `{group}`：實測 {got} 支 > 上限 {ceiling}"
                f"（本次補標籤額度 {budget}，可用 {allowance}）——這一群多出來的 skip"
                "**不是**從 untagged 搬過來的，是真的新增。🔴 合法出口只有「把那些測試"
                "變成真的會跑」，不是把上限調大（見本表上方的雙單邊設計）"
            )
    for reason in reasons:
        if (skip_group(reason) == SKIP_GROUP_DEBT
                and not _EXEMPT_HANDOVER_RE.search(reason)):
            problems.append(
                f"{DEBT_SKIP_TAG} 的理由沒有寫承接輪次（形態：大寫 R 加輪號）"
                f"——沒有承接者的欠債就是永久欠債：{reason[:120]}"
            )
    return problems


# ── 目標報告（掌舵者驗收問題②的可機械檢核形式）────────────────────────────────
#
#: 每個剖面的**互補剖面**：`platform` 群那些「在這裡 skip 是對的」的測試，究竟在哪個
#: 剖面上真的被跑到。宣告成資料而不是散文，才有辦法被查——R80 之前這件事零機械證明
#: （S3-08），手驗過但那個過程不可重跑，於是等同沒驗。
#:
#: 🔴 R82 包 A2（MAC-01）：值由 `str` 改成 `tuple[str, ...]`，判準由「有沒有互補剖面」
#: 改成「**每一個**互補剖面都要有人量過」。
#:
#: 缺陷本體（當回合實測）：`platform` 這一群在 win32 上其實是**兩個互斥子母體**——
#: `[POSIX-NATIVE-ONLY]`（linux 跑得到）與 `[MAC-NATIVE-ONLY]`（只有 darwin 跑得到，
#: 本輪 census 實測 26 支）。舊表是 1:1，只要 linux 那一格登記了，整組判準就短路 ⇒
#: `skip_target_report('tools/tests@win32', …)` 實測只印欠債那一行，**結構性缺口那一行
#: 一次都沒印過**，帳面讀起來像「已覆蓋」。而 linux 結構上跑不到那 26 支：
#: `install_mac_nightly.sh` 自帶 `uname != Darwin` fail-loud，act 映像內 `which zsh` 也回空。
#: ⇒ 1:1 的形狀本身就是那個假綠的來源，不是資料填錯。
#
# 🔴 R83 四方複審收斂（SA-02 blocking／SA falsified #1）：**「已登記」不等於「跑得到」**，
# 而 R82 之後的判準只問前者 ⇒ 同一個假綠換方向復發。R83 把 darwin 的互補剖面宣告成
# `tools/tests@linux`，註解逐字寫「由 linux 承接」；但 mac 上被 skip 的那一族**全部**是
# `[WINDOWS-NATIVE-ONLY]`（本輪實測 44/44：`pytest` 對含該標籤的 12 支檔實跑得到
# 讀數見 ONBOARDING.md §7 表②（此處不複寫）；44 行 SKIPPED 理由無一例外，逐檔 dev_start 12／
# context_budget_guard 8／check_hooks_liveness 5／install_windows_nightly 5／
# bash_probe_spec_contract 4／ps51_compat 3／windows_forbidden_filename_parity 3／
# bootstrap_ps1 2／nightly_interpreter_determinism 1／windowsapps_guard 1），其述詞是
# `os.name != "nt"`（實測站點 test_context_budget_guard.py:1629/1647/1662/1675/2150 等）
# ⇒ linux 上 `os.name == "posix"`，**一樣 skip**。宣告的承接者結構上一支都跑不到，而
# `skip_target_report('tools/tests@darwin', …)` 因此回**空 list＝已達標**——唯一能為
# 「兩平台聯集才是零」作證的報告者，被這一筆登記親手關掉（複審者實測）。
#
# 🔴 修法刻意不只是「把資料改對」（下一輪照樣可以再填錯一次，而且填錯一樣是靜默的）：
# 標籤字面本身已經指名了唯一跑得到它的平台，所以「平台 X 上的 `platform` 群需要哪些平台
# 才承接得住」＝**那些「家」不含 X 的標籤，其家的聯集**——可由標籤 SSOT 推導，不需要任何
# 人手寫。手寫的那張表從此只負責「該平台上的哪一個**具體剖面鍵**」（`+pg+nested` 這種帶
# 能力維度的鍵無從推導），並被推導出來的需求逐格對帳：宣告的承接者若在**平台層**根本不
# 可能跑到，`skip_target_report` 當場說話而不是回空。
#
# 🔴 誠實劃界（本檔的粒度是**剖面／計數**，這是刻意的分工，不再是缺口）：本檔證明得了
# 「這個剖面有人量過健康值、且沒有退步」，證明不了「那 44 支逐一在互補剖面真的執行過」
# ——計數粒度對「換掉一支 test-id 而計數不變」結構上恆綠。**M6 那一問已移交
# `skip_runtime_report.m6_id_set_problems`**（id 集合面，判準是集合關係而非大小比較，
# 落款＝`docs/06_quality/skip_id_ledger.json`）。本檔刻意不複製 id 集合：兩個粒度各有
# 各的用途（本檔擋退步、那邊答覆蓋），但同一份 id 不得住兩個家。
# 形狀＝`dict[str, tuple[str, ...]]`：標籤字面 → 唯一跑得到它的平台（標籤語意的直接編碼）。
# 刻意寫成兩行而非逐條一行：本檔緊貼 `guardrail_lib<=400`，而註解不計 `count_loc`。
_TAG_HOME_PLATFORMS = {WINDOWS_NATIVE_SKIP_TAG: ("win32",), MAC_NATIVE_SKIP_TAG: ("darwin",),
                       POSIX_NATIVE_SKIP_TAG: ("darwin", "linux")}


# 純函式：`platform` 上的 `platform` 群 skip，需要哪些平台才承接得住（由標籤語意推導）。
# 例：darwin ⇒ {win32}（mac-only／POSIX-generic 在 mac 上本來就會跑，不需要別人承接）；
# win32 ⇒ {darwin, linux}；linux ⇒ {win32, darwin}。
# 🔴 兩件事的精度不同，別把回傳值當同一種答案用（R83 獨立驗證輪補記）：
#   · 拿它做**成員判定**（「平台 P 對剖面 X 有沒有用」）是**充要**的——P ∈ 回傳集合
#     ⟺ 存在某標籤在 X 上會 skip、在 P 上跑得到。`test_local_ci_gate.py` 的
#     `_counterparts_that_cannot_run_them()` 用的正是這一向。
#   · 拿它做**覆蓋判定**（下方 `homeless` 的差集）則是**偏嚴**的：`[POSIX-NATIVE-ONLY]`
#     的家是 (darwin, linux)＝「兩者任一即可跑到」，而集合聯集會把兩者都列成需求。
#     今天兩者都已宣告 ⇒ 差集為空、無影響；日後若 linux 執行者退場，win32 那一列會多印
#     一個其實已被 darwin 覆蓋的平台。方向是**多報而非漏報**（本函式只餵 advisory 訊息、
#     不接任何閘門的 rc），故本輪刻意不為此加一層 per-tag 的「任一即可」邏輯——那要把
#     差集改成「逐標籤各自求交集是否非空」，成本落在本檔僅剩 1 行的 tier 餘裕上。
#     要做的判準：`homeless` 改為「對每一個在 X 上會 skip 的標籤，其家與已宣告平台的交集
#     為空者，才回報該標籤的家」，並在測試側補一組「linux 退場後 win32 不得多報」的注入。
def required_home_platforms(platform: str) -> set[str]:
    return {h for hs in _TAG_HOME_PLATFORMS.values() if platform not in hs for h in hs}


_COMPLEMENTARY_PROFILE: dict[str, tuple[str, ...]] = {
    "AutoClaude/tests@win32+nopg+nested": ("AutoClaude/tests@linux+nopg+solo",),
    "AutoClaude/tests@win32+pg+nested": ("AutoClaude/tests@linux+pg+solo",),
    # 🔴 R84 包 W5：反方向（同 `tools/tests@darwin` 那一列的判準）。mac 上被 skip 的
    # `platform` 群實測 53 支**全部**是 `[WINDOWS-NATIVE-ONLY]`（本輪逐支讀 reason 分群，
    # 零 `[POSIX-NATIVE-ONLY]`／零 `[MAC-NATIVE-ONLY]`）⇒ 唯一承接得住的是真 Windows 剖面，
    # 而 `AutoClaude/tests@win32+pg+nested` 已量測入表。不填這一列時判準走 `not counterparts`
    # 那一支、印「（平台 win32 未宣告承接剖面）」＝把「有著落」誤報成「全世界都沒跑過」。
    "AutoClaude/tests@darwin+pg+nested": ("AutoClaude/tests@win32+pg+nested",),
    # POSIX-generic 那一半的家是 linux，mac-only 那一半的家只有 darwin——兩個都要。
    "tools/tests@win32": ("tools/tests@linux", "tools/tests@darwin"),
    # 🔴 反方向（R83 收斂訂正）：darwin 上 skip 掉的那 44 支**全部**是
    # `[WINDOWS-NATIVE-ONLY]` ⇒ 唯一承接得住的是**真 Windows** 剖面 `tools/tests@win32`
    # （R82 已量測入表）。linux 承接不了任何一支（`os.name != "nt"` 在那裡同樣成立），
    # 故已自本列移除——它在 R83 原版是這一格的唯一值，也就是本列當時整格是假的。
    "tools/tests@darwin": ("tools/tests@win32",),
    # 🔴 R83 收斂新增（此前整列缺席 ⇒ 判準走 `not counterparts` 那一支、印「（未宣告）」）：
    # linux 上被 skip 的 `platform` 群＝`[WINDOWS-NATIVE-ONLY]`（家＝win32）＋
    # `[MAC-NATIVE-ONLY]`（家＝darwin），兩個家都已量測入表 ⇒ 這一列補上之後這個剖面的
    # 結構性缺口才是**算得出來**的 0，而不是「沒人填過所以不知道」。
    "tools/tests@linux": ("tools/tests@win32", "tools/tests@darwin"),
}


# 純函式：某剖面宣告的互補剖面。存在理由＝id 集合面（`skip_runtime_report`）要問同一件事，
# 而「哪個剖面承接誰」只能有一個家；讓消費端讀 `_COMPLEMENTARY_PROFILE` 等於開第二個。
def complementary_profiles(profile: str) -> tuple[str, ...]:
    return _COMPLEMENTARY_PROFILE.get(profile, ())


# 與 `skip_group_census_problems` 刻意分開、且刻意**不接任何閘門的 rc**：
#   · 天花板判準回答「有沒有退步」——它必須能擋 push，所以只能問已經量得到的事；
#   · 本函式回答「還差多少才到位」——它問的是**還沒量過**的事（互補剖面），
#     今天必然有缺口，把它接上 rc 只會製造一個所有人都學會忽略的常紅。
# 兩者混在一起，就會變成「為了讓閘門綠而把目標訂低」，那正是 S3-03 的病根。
# 純函式：這個剖面**距離目標還有多遠**（不是「有沒有違規」）。回空 list ＝已達標。
def skip_target_report(profile: str, census: Mapping[str, int]) -> list[str]:
    out: list[str] = []
    debt = open_debt(census)
    if debt:
        detail = "／".join(f"{g}={census.get(g, 0)}" for g in ZERO_TARGET_GROUPS)
        out.append(
            f"{profile}：欠債型 skip 還有 {debt} 支（目標 0）——{detail}。"
            "這四群是**可歸零**的那一半：untagged 補一句標籤就結案、env-disabled 設環境"
            "變數就會跑（R79 實證一次消 92 支）、tool-absence 裝上該裝的東西、debt 有承接輪次"
        )
    structural = sum(census.get(g, 0) for g in SKIP_GROUPS
                     if _SKIP_GROUP_TARGET[g] == SKIP_TARGET_STRUCTURAL)
    counterparts = _COMPLEMENTARY_PROFILE.get(profile, ())
    # 🔴 R82（MAC-01）：`any` → `all`。舊寫法是「宣告了一個互補剖面且它已登記 ⇒ 收工」，
    # 而 `platform` 群在 win32 上是兩個互斥子母體（POSIX-generic vs mac-only），
    # 只要其中一個的家登記了，另一個（26 支只有 darwin 跑得到）就整組被短路掉。
    missing = [c for c in counterparts if not profile_registered(c)]
    # 🔴 R83 收斂（SA-02）：第二向——**宣告的承接者可能結構上跑不到**，而上一行只問「量過
    # 沒有」。把 darwin 的家填成 linux（那裡 `os.name != "nt"` 同樣成立、44 支一支都跑不到）
    # 時整組回空＝已達標。這一行改由標籤語意算出「非得有哪些平台」，再減掉這一列**真的宣告
    # 到**的平台；差集非空 ⇒ 該平台連一個候選都沒被宣告 ⇒ 照樣要說話。刻意減「宣告到的」而
    # 不是「已量測的」：後者會讓同一個平台同時以兩種措辭出現兩次（宣告了但未量＝上一行已經
    # 指名它了），而重複的清單會讓人以為是兩個不同的缺口。
    # 🔴 這個差集只抓「**少**宣告」，結構上抓不到「**多**宣告」——把 linux 與 win32 並列
    # （SA-02 原本開的處方）差集是空的，於是那句今天為假的話可以住回表裡而本函式回空。
    # 那一向的判準是**資料表的不變量**、不需要在執行期存在，且本函式刻意不接任何閘門的 rc
    # （加在這裡只會多印一行 advisory、不會紅），故落在
    # `AutoClaude/tests/tools/test_local_ci_gate.py::test_a_counterpart_that_cannot_run_them
    # _may_not_sit_in_the_table_either`（含並列版與自我承接兩種紅向自證）。
    homeless = sorted(required_home_platforms(_platform_of(profile))
                      - {_platform_of(c) for c in counterparts})
    if structural and (missing or homeless or not counterparts):
        # 🔴 兩種缺口刻意用不同措辭（R83）：「宣告了但沒人量」與「這個平台上一個候選都沒宣告」
        # 是兩件不同的事，混成一句「至今沒有人量過」會對後者說出假事實——被點名的平台可能
        # 明明有人量過，只是這一列沒宣告到它（linux 那一列在本輪補上之前正是這個形態）。
        where = "／".join([f"`{c}`（未量測）" for c in missing]
                         + [f"（平台 {p} 未宣告承接剖面）" for p in homeless]) or "（未宣告）"
        out.append(
            f"{profile}：結構性 skip {structural} 支，它們的目標**不是** 0，而是"
            f"「在互補剖面上真的被跑到」——而 {where} ⇒ 這些測試"
            "目前**沒有任何機械證據**顯示它們在世界上任何一處跑過。這是量 skip 數永遠看不見"
            "的那一半缺口（S3-08）。🔴 互補剖面是**多對一**：一個剖面登記了不代表整群有著落"
            "（R82／MAC-01：linux 結構上跑不到 mac-only 那 26 支）；且**登記≠跑得到**"
            "（R83／SA-02：linux 也跑不到 mac 上那 44 支 `[WINDOWS-NATIVE-ONLY]`）"
        )
    return out
