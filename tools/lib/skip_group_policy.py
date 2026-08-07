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
    "AutoClaude/tests@win32+nopg": {
        SKIP_GROUP_PLATFORM: 17,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 1,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 118,
    },
    "AutoClaude/tests@win32+pg": {
        SKIP_GROUP_PLATFORM: 17,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 1,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 26,
    },
}

#: 上表各格的 shrink-only 天花板（理由與 `_POSIX_TAG_RATCHET_CEILING` 完全相同：
#: 沒有它，「把上限改大」就是零阻力的合法出口，欠債可以無聲增長且看起來像在維護基線）。
#: 🔴 數值刻意**逐格寫死**，不得寫成 `{p: dict(g) for …}` 之類由上表推導的形式：那樣兩張表
#: 恆等，「上限高於天花板」這一向結構上永遠不可能觸發＝又一道沒有鑑別力的鎖（第一版就是
#: 那樣寫的，當回合自查發現）。兩張表必須是兩份獨立的字面值，diff 才看得見有人在加大額度。
_RUNTIME_SKIP_CEILING_MAX: dict[str, dict[str, int]] = {
    "AutoClaude/tests@win32+nopg": {
        SKIP_GROUP_PLATFORM: 17,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 1,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 118,
    },
    "AutoClaude/tests@win32+pg": {
        SKIP_GROUP_PLATFORM: 17,
        SKIP_GROUP_TOOL_ABSENCE: 0,
        SKIP_GROUP_ENV_DISABLED: 1,
        SKIP_GROUP_STRUCTURAL: 0,
        SKIP_GROUP_DEBT: 0,
        SKIP_GROUP_UNTAGGED: 26,
    },
}


def profile_registered(profile: str) -> bool:
    """這個剖面有沒有登記過天花板。

    🔴 存在理由（R79 收輪）：「剖面未登記」與「天花板被突破」在 `skip_group_census_problems`
    裡是同一種回傳值，但它們對呼叫端是**兩件不同的事**——前者代表這台機器／這個平台從來
    沒有人量過（mac、Linux runner 第一次跑到這裡就是這一格），後者代表 skip 真的變多了。
    push 通道要能擋住後者、又不能因為前者就把一個沒人量過的平台整個擋在門外（那是誤擋，
    不是鑑別力）。分開才有辦法讓兩者各自對應到正確的處置，而不是二選一。
    """
    return profile in _RUNTIME_SKIP_CEILING and profile in _RUNTIME_SKIP_CEILING_MAX


def skip_group_census_problems(
    profile: str,
    census: Mapping[str, int],
    *,
    reasons: Iterable[str] = (),
) -> list[str]:
    """分群天花板的判準（純函式）。回空 list ＝合格。

    五向：①剖面未登記 ②某群超過上限 ③上限高於 shrink-only 天花板 ④census 出現未登記
    的群 ⑤`[DEBT]` 的 reason 沒寫承接輪次（沒有承接者的欠債＝永久欠債）。
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
        if got is not None and got > ceiling:
            problems.append(
                f"{profile}／群 `{group}`：實測 {got} 支 > 上限 {ceiling}——"
                "這一群的 skip 變多了。🔴 合法出口只有「把那些測試變成真的會跑」或"
                "「補上正確的分群標籤」，**不是**把上限調大（見本表上方的雙單邊設計）"
            )
    for reason in reasons:
        if (skip_group(reason) == SKIP_GROUP_DEBT
                and not _EXEMPT_HANDOVER_RE.search(reason)):
            problems.append(
                f"{DEBT_SKIP_TAG} 的理由沒有寫承接輪次（形態：大寫 R 加輪號）"
                f"——沒有承接者的欠債就是永久欠債：{reason[:120]}"
            )
    return problems
