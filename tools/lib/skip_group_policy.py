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
    "tools/tests@win32": {
        SKIP_GROUP_PLATFORM: 37,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 1,
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
    "tools/tests@linux": {
        SKIP_GROUP_PLATFORM: 63,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 0,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 9,
    },
}

#: 上表各格的 shrink-only 天花板（理由與 `_POSIX_TAG_RATCHET_CEILING` 完全相同：
#: 沒有它，「把上限改大」就是零阻力的合法出口，欠債可以無聲增長且看起來像在維護基線）。
#: 🔴 數值刻意**逐格寫死**，不得寫成 `{p: dict(g) for …}` 之類由上表推導的形式：那樣兩張表
#: 恆等，「上限高於天花板」這一向結構上永遠不可能觸發＝又一道沒有鑑別力的鎖（第一版就是
#: 那樣寫的，當回合自查發現）。兩張表必須是兩份獨立的字面值，diff 才看得見有人在加大額度。
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
    # 🔴 R82（CARRIER-02）：連同基線一起下修 40 → 37（天花板不跟著降＝把剛還掉的
    # 欠債額度留著，日後可無聲用回去——這句話是本表自己的既有紀律）。
    "tools/tests@win32": {
        SKIP_GROUP_PLATFORM: 37,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 1,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 0,
    },
    "tools/tests@linux": {
        SKIP_GROUP_PLATFORM: 63,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 0,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 9,
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
# · `tools/tests@darwin`：本輪沒有 mac 真機，macOS CI 又是 `steps=0` ⇒ 健康值今天無論如何取
#   不到。憑空填數字＝憑空造出一個沒有鑑別力的門檻，故只登記缺口。
# · `AISDLC_SDD/fsm_runtime@win32`：本輪首次進帳（6 支 skip 已全數補標），但 census 還沒接上
#   它的閘門 ⇒ 數字量得到、卻沒有任何東西在讀。🔴 先接閘門再入表，順序不可顛倒——先填數字
#   只會得到一個沒有消費者的常數。
_UNMEASURED_RUNNER_PROFILES: dict[str, str] = {
    "AutoClaude/tests@linux+nopg+solo":
        "取得＝act 映像跑 pytest，輸出餵 `local_ci_gate.py --census-only`。DEF-101-960",
    "AutoClaude/tests@win32+pg+solo":
        "取得＝跑 run_local_nightly.ps1 後抄 nightly_latest.log 的 `[skip census]`。DEF-101-960",
    "tools/tests@darwin": "取得＝mac 真機跑 run_root_unittests.py 抄 `[skip census]`。DEF-101-960",
    "AISDLC_SDD/fsm_runtime@win32": "取得＝ci-gate.sh 接 `--census-only` census。DEF-101-960",
}
#: 雙單邊的兩個**下限**（取代舊的 shrink-only 上限，理由見上方）：分母與分子都只准增。
#: 🔴 R82：5 → 7（新增 `tools/tests@darwin`＝MAC-01、`AISDLC_SDD/fsm_runtime@win32`＝SDD-01）。
#: 分子（`_MEASURED_RUNNERS_MIN`）不動——這兩筆都是**登記缺口**，不是量到的值；
#: 把分子一起提高就是在鼓勵「憑空填數字」，而那正是這張表存在的理由所反對的事。
_FULL_SUITE_RUNNERS_MIN = 7
_MEASURED_RUNNERS_MIN = 3
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


def ci_platform_coverage_problems() -> list[str]:
    """純函式：會跑整棵樹、卻沒有登記健康值的**執行者剖面**。回空 list ＝帳算得清。

    五向：①分母縮水 ②分子縮水 ③未登記又未具名豁免 ④已登記卻還掛在豁免表（把有人守的
    寫成沒人守，與反向同樣是假事實）⑤具名豁免卻沒指名承接帳本列（＝沒有承接者的永久缺口）。
    另保留平台層那一向：一個**整個平台**都沒有任何執行者入帳時仍要紅（例：日後新增 macOS
    full-suite job），那是派生視圖唯一還有鑑別力的地方。
    """
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


def profile_registered(profile: str) -> bool:
    """這個剖面有沒有登記過天花板。

    🔴 存在理由（R79 收輪）：「剖面未登記」與「天花板被突破」在 `skip_group_census_problems`
    裡是同一種回傳值，但它們對呼叫端是**兩件不同的事**——前者代表這台機器／這個平台從來
    沒有人量過（mac、Linux runner 第一次跑到這裡就是這一格），後者代表 skip 真的變多了。
    push 通道要能擋住後者、又不能因為前者就把一個沒人量過的平台整個擋在門外（那是誤擋，
    不是鑑別力）。分開才有辦法讓兩者各自對應到正確的處置，而不是二選一。
    """
    return profile in _RUNTIME_SKIP_CEILING and profile in _RUNTIME_SKIP_CEILING_MAX


def retag_budget(profile: str, census: Mapping[str, int]) -> int:
    """純函式：這次執行從 `untagged` **搬出去**了幾支（＝補標籤的額度）。

    🔴 R80 包 A（S3-03）存在理由——舊判準的形狀是錯的，而且錯在它自己宣傳的出口上：
    舊訊息逐字寫著「合法出口只有『把那些測試變成真的會跑』或『**補上正確的分群標籤**』」，
    但「補標籤」做的事就是把一支 skip 從 `untagged` 搬進某個具名群，那一群的計數必然 +1
    ⇒ 該群當場超過上限 ⇒ **照著失敗訊息做，就會被同一道判準判紅**。
    當回合注入實測（三組，逐字見包 A 回報）：
      · untagged 118→0、env-disabled 1→119（純補標籤，總量一支沒變）⇒ 舊判準回 1 筆問題；
      · untagged 118→112、platform 17→20（總量 136→133，**樹變健康了**）⇒ 舊判準回 1 筆問題；
      · untagged 118→115（單純變少）⇒ 綠。
    也就是說：**唯一不會被罰的改善方式是「skip 憑空消失」**，而那正是本 repo 最不該鼓勵的
    那一種（R76 記過的「看起來變乾淨」）。分群天花板必須對「群間位移」保持中立，
    只對「總量上升」與「未分類的欠債上升」說話。
    """
    ceilings = _RUNTIME_SKIP_CEILING.get(profile) or {}
    return max(0, ceilings.get(SKIP_GROUP_UNTAGGED, 0)
               - census.get(SKIP_GROUP_UNTAGGED, 0))


def skip_group_census_problems(
    profile: str,
    census: Mapping[str, int],
    *,
    reasons: Iterable[str] = (),
) -> list[str]:
    """分群天花板的判準（純函式）。回空 list ＝合格。

    六向：①剖面未登記 ②**總量**超過上限 ③某群超過「上限＋補標籤額度」 ④上限高於
    shrink-only 天花板 ⑤census 出現未登記的群 ⑥`[DEBT]` 的 reason 沒寫承接輪次。

    ②③ 的分工就是 S3-03 的修法：總量那一道是真正有牙的（skip 變多一定紅），分群那一道
    只在「這一群變多、而且**不是**從 untagged 搬過來的」時候才紅。誠實劃界：兩支 untagged
    被修好、同時新增兩支 env-disabled，在本判準下是綠的（總量不變、額度剛好抵銷）——
    要抓那一種，靠的是 `skip_tag_policy` 的靜態站點面，不是這裡的計數面。
    """
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
_COMPLEMENTARY_PROFILE: dict[str, tuple[str, ...]] = {
    "AutoClaude/tests@win32+nopg+nested": ("AutoClaude/tests@linux+nopg+solo",),
    "AutoClaude/tests@win32+pg+nested": ("AutoClaude/tests@linux+pg+solo",),
    # POSIX-generic 那一半的家是 linux，mac-only 那一半的家只有 darwin——兩個都要。
    "tools/tests@win32": ("tools/tests@linux", "tools/tests@darwin"),
    # 反方向：darwin 上 skip 掉的 `[WINDOWS-NATIVE-ONLY]`／POSIX-generic 由 linux 承接。
    "tools/tests@darwin": ("tools/tests@linux",),
}


def skip_target_report(profile: str, census: Mapping[str, int]) -> list[str]:
    """純函式：這個剖面**距離目標還有多遠**（不是「有沒有違規」）。回空 list ＝已達標。

    與 `skip_group_census_problems` 刻意分開、且刻意**不接任何閘門的 rc**：
      · 天花板判準回答「有沒有退步」——它必須能擋 push，所以只能問已經量得到的事；
      · 本函式回答「還差多少才到位」——它問的是**還沒量過**的事（互補剖面），
        今天必然有缺口，把它接上 rc 只會製造一個所有人都學會忽略的常紅。
    兩者混在一起，就會變成「為了讓閘門綠而把目標訂低」，那正是 S3-03 的病根。
    """
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
    if structural and (missing or not counterparts):
        where = "／".join(f"`{c}`" for c in missing) or "（未宣告）"
        out.append(
            f"{profile}：結構性 skip {structural} 支，它們的目標**不是** 0，而是"
            f"「在互補剖面上真的被跑到」——而 {where} 至今沒有人量過 ⇒ 這些測試"
            "目前**沒有任何機械證據**顯示它們在世界上任何一處跑過。這是量 skip 數永遠看不見"
            "的那一半缺口（S3-08）。🔴 互補剖面是**多對一**：一個剖面登記了不代表整群有著落"
            "（R82／MAC-01：linux 結構上跑不到 mac-only 那 26 支）"
        )
    return out
