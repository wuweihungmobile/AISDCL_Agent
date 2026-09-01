#!/usr/bin/env python3
"""護欄層「守誰」分桶政策 ＋ **分桶棘輪**的唯一真相源（立案：`DEF-200-103`）。

WHY 本檔住 `tools/lib/` 而不住 `tools/tests/`
---------------------------------------------
兩個各自成立的理由：

① **消費端不只一個**：普查 probe（`tools/probe/guard_layer_bucket_census.py`）與棘輪
   （`tools/tests/test_adr_xplat001_c1c2_lock.py` 的分桶那一族）讀的必須是**同一份**桶
   定義。桶定義若各留一份，兩邊會各自漂移，而那時「probe 印的比例」與「棘輪判的比例」
   是兩個數——那正是本 repo 反覆判過的「同一份知識住兩個家、只有一個家被改」。
   體例逐字沿用上一輪已落地的同型處置：`tools/tests/test_schedule_capability_parity.py`
   的 `_SCAN_FLOOR` 取消第二個家、直接 import `tools/lib/skip_tag_policy.py` 的 SSOT。

② **`tools/tests/*.py` 就是被量的那個面**。分桶棘輪的常數（凍結桶表）與判準若寫在
   `tools/tests/` 內，本機制**每長一行就把自己要管的分子做大一行**——而它管的正是
   「守自己」那一桶，於是新機制會被自己判紅。這不是省行數的技巧，是避免量測器住進量測面。
   🔴 誠實劃界：`tools/lib/` 不在行數棘輪的量測面內，但**它在 wide 面內**（見
   `WIDE_SURFACE_SPEC`）⇒ 把行搬到這裡會讓棘輪的數字變好、wide 面的數字一動不動。
   本檔因此**不是**達成「淨額 ≤ 0」的正當手段，任何靠搬家達標的輪次都必須在交件回報
   明說「這是量測面內的減法，不是總量的減法」。

分桶棘輪與總量棘輪的關係：**額外加嚴，不取代**
----------------------------------------------
掌舵者裁決逐字：總量棘輪（`_FROZEN_GUARD_LINES` ＋ 逐輪淨額 ≤ 0 的到期義務）一個字都不
准改、不准放寬、不准加延期參數；分桶棘輪是**新增的第二道判準**。⇒ 淨效果只能是更嚴：

    通過 = 總量棘輪通過 **且** 每一個 shrink-only 桶都沒有上升

上一輪 Architect 的結論是「單一總量棘輪讓最便宜的那一桶（守散文）永遠贏」——因為
「加一支守散文的鎖」與「加一支守生產碼的鎖」在單一總量下付**一樣**的代價。分桶棘輪讓
這兩件事付不同的代價：守生產碼／守根層基礎設施／守 SDD 可以長，守散文與守自己不行。

🔴 為什麼歸屬用 `exclusive`（下界）而不是 `dominant`／`firstmatch`
----------------------------------------------------------------
棘輪吃的是**單邊**判準，所以歸屬的偏誤方向必須與判準方向相反，否則會製造假紅：

  · shrink-only 桶用**下界**（`exclusive`：該檔只參照這一棵樹）⇒ 一支同時守散文與守生產碼
    的檔**不計入**散文桶 ⇒ 混合檔成長不會誤觸 shrink-only。假紅的代價不是「比較嚴格」：
    repo 已判過「擋到讓人無法工作的守衛會被整個關掉，而被關掉的守衛比沒有守衛更糟」。
  · `dominant` 對「多寫幾句註解提到某棵樹」敏感 ⇒ 一支檔的桶會在行數沒變時翻掉，而那會
    讓兩個桶同時跳動。用它當棘輪的歸屬等於引進一個與行數無關的紅燈來源。

代價（誠實劃界）：`exclusive` 對混合檔整片失明 ⇒ **把新增的守散文判準塞進一支已經同時
參照生產碼的既有巨檔，可以合法繞過本棘輪**。這個縫由總量棘輪（那一道不看桶）接住——
兩道判準的失明面刻意不同，這是它們一起裝的理由。
"""
from __future__ import annotations

import ast
import collections
import re
from typing import NamedTuple

# --------------------------------------------------------------------- 掃描面（兩個 scope）
#: 行數棘輪真正管的那個面：`_GUARD_DIR_REL` / `_GUARD_LINE_PATTERN` 的鏡像。
GUARD_SURFACE_REL = "tools/tests"
GUARD_LINE_GLOB = "*.py"

#: 上一輪 Architect 那個 113,084 的 wide 面，實查其組成：(相對路徑, 是否遞迴)。
#: 🔴 逐字照原定義，**不擅自補上** `tools/probe`／`tools/git-hooks`／`tools/act`——
#: 補了就不是同一個量，而那個量已經被引用在交棒書裡。定義外的部分由 probe 的
#: `excluded_from_wide` 另外印，讓「定義外還有多少」可見而不是被吸收進來。
WIDE_SURFACE_SPEC: tuple[tuple[str, bool], ...] = (
    ("tools/tests", True),
    ("tools/lib", True),
    ("tools", False),
    (".claude/hooks", True),
)

# --------------------------------------------------------------------- 桶定義
#: 每一桶認哪些樹。判準＝在**原始文字**（含 docstring 與 `#` 註解）內出現的路徑樣 token。
BUCKET_TREES: dict[str, tuple[str, ...]] = {
    # 生產碼：AutoClaude 的套件本體。
    "production": ("AutoClaude/autoclaude/", "autoclaude/"),
    # 根層基礎設施**程式碼**（不是散文）：安裝器、政策模組、hook、CI workflow。
    # 🔴 上一輪的桶集**沒有這一桶**，於是「守 `tools/lib/quota_policy.py` 的鎖」無處可歸，
    # 只能掉進「無檔案參照／自足」或（若它也提到 docs）被算進散文桶 ⇒ 散文桶被高報。
    # 這一桶守的是真程式碼，與 production 同列為「允許成長」。
    "root_infra": (
        "tools/lib/", "tools/probe/", "tools/git-hooks/", "tools/act/",
        "tools/bootstrap", "tools/install_", "tools/run_", "tools/check_",
        "tools/session_resume_planner", "tools/snapshot_sync", "tools/sync_",
        ".claude/hooks/", ".claude/settings.json", ".github/workflows/",
        "AutoClaude/tools/", "AutoClaude/pyproject.toml", "AutoClaude/.importlinter",
    ),
    # 方法論框架（~85% Markdown ＋ FSM runtime）。
    "sdd": ("AISDLC_SDD/",),
    # 散文：會漂移的事實住在文件裡，鎖去守它。
    "prose": ("docs/", "CLAUDE.md", "ONBOARDING.md", "README.md", "FRAMEWORK_STATUS.md"),
    # 護欄層自己（含 AutoClaude 的測試樹）。
    "guard_self": ("tools/tests/", "AutoClaude/tests/"),
}

#: first-match 的優先序。🔴 **刻意把「允許成長」的三桶排在前面**：本檔的 first-match 只
#: 作為與上一輪可比對的點估計而存在（上一輪的優先序是 production 第一），而棘輪吃的是
#: `exclusive`，不吃這個序。優先序在前者被高報、在後者被低報——這個偏誤方向是確定的，
#: 讀數時必須連方向一起讀。
BUCKET_PRIORITY: tuple[str, ...] = ("production", "root_infra", "sdd", "prose", "guard_self")

#: 允許成長的桶（守真程式碼）。其餘桶一律 shrink-only。
GROWTH_ALLOWED_BUCKETS: frozenset[str] = frozenset({"production", "root_infra", "sdd"})

#: shrink-only 的桶——**淨額只准 ≤ 0**。逐字照掌舵者裁決：守散文／守自己這兩桶。
#:
#: 🔴 `selfcontained`（一塊都沒寫出任何路徑 token）**刻意不列入**，儘管它是最大的一桶
#: （占比現查 probe 的 `selfcontained` 列）。理由是它不是一個守備標的，是**未歸屬殘差**：把它判成
#: shrink-only 會讓「新增一個守生產碼的判準、但它的 WHY 沒寫出路徑字面」轉紅，那是與
#: 散文完全無關的紅燈來源。⇒ 分桶棘輪只咬得到約一半的面，這是它的**已知射程上限**，
#: 由總量棘輪（不看桶）接住另一半。
SHRINK_ONLY_BUCKETS: tuple[str, ...] = ("prose", "guard_self")

#: 🔴 開頭那個 `\.?` **不是可有可無的**：少了它，`.claude/hooks/`／`.github/workflows/`
#: 這類**以點開頭**的樹前綴在結構上永遠抓不到（token 會從 `claude/…` 開始，而它不以
#: `.claude/` 起頭）⇒ 那兩筆登記是**死條目**，`root_infra` 桶被系統性低報，而落在那一族的
#: 鎖檔會被誤丟進 `prose`／`selfcontained`。本輪實測命中：宣稱判準鎖的模組層敘事被判成
#: **純散文 60 行**，而它的第一句話就指名 `.claude/hooks/check_claim_provenance.py`。
#: 失明是靜默的——掃描器照跑、照回數字，只是那一族從來不在分母裡（同 R81 `ctypes` 判例）。
#: 這個縫現在有機械物看著：`dead_tree_prefixes()`。
_TOKEN_RE = re.compile(
    r"\.?[A-Za-z0-9_][A-Za-z0-9_./\-]*\.[A-Za-z0-9_]+"
    r"|\.?[A-Za-z0-9_][A-Za-z0-9_./\-]*/")


class Verdict(NamedTuple):
    """一支檔在四個估計量下各自的歸屬。"""

    exclusive: str      # 只參照一棵樹時的桶名；否則 "mixed"（不進任何 shrink-only 判準）
    firstmatch: str     # 上一輪的啟發式
    dominant: str       # 依參照次數
    any_of: tuple[str, ...]  # 所有被參照到的桶（上界估計用）


def reference_counts(text: str, self_name: str = "") -> collections.Counter:
    """`{桶名: 該桶樹前綴在本文中出現的次數}`。

    `self_name` 是本檔自己的檔名，出現處**不計**——否則 `guard_self` 桶會因為每支檔都
    寫得出自己的名字而變成恆真（那樣的桶沒有鑑別力）。
    """
    if self_name:
        text = text.replace(self_name, "\x00")
    counts: collections.Counter = collections.Counter()
    for token in _TOKEN_RE.findall(text):
        for bucket, trees in BUCKET_TREES.items():
            if any(token.startswith(t) or token == t for t in trees):
                counts[bucket] += 1
                break
    return counts


class Chunk(NamedTuple):
    """一支檔內的一塊「守備單元」：標籤、行數、自己的原始文字。"""

    label: str
    lines: int
    text: str


def split_chunks(text: str, fallback_label: str = "<module>") -> list[Chunk]:
    """把一支鎖檔切成**頂層 AST 塊**（每個 class／def 一塊 ＋ 其餘歸「模組序言」）。

    🔴 為何非切不可（本檔最重要的一個設計決定，立案有實測）：檔級歸屬在這一層**結構上
    是失效的**——本層的鎖檔絕大多數同時參照 `root_infra`、`guard_self` 與 `prose` 三者
    （逐桶比例一律現查 `guard_layer_bucket_census.py --grain file` 的 `any` 欄），於是
    「只參照一棵樹」的 `exclusive` 歸屬對 `prose` 桶回**零行**，shrink-only 判準因此
    **恆真、零鑑別力**。成因不是判準寫壞了，是**粒度不對**：
    本層的檔是動輒數千行的 mega-file，一支檔同時守散文、守 `tools/lib/` 常數、守自己。

    而這正是上一輪 Architect 診斷的下游後果——它自己也記載了「增量被擠進少數 mega-file」
    （檔數棘輪把病換了個地方長）。⇒ 要看見「哪一桶在長」，量測粒度必須小於一支檔。
    切到頂層 class／def 之後，一個測試類別通常只守一件事，`exclusive` 才恢復鑑別力。

    誠實劃界：① 語法錯誤的檔退回整檔一塊（不讓 probe 因為別人的壞檔而崩）；
    ② decorator 行歸屬於它所裝飾的那一塊；③ 塊與塊之間的空白行歸「模組序言」，
    所以各塊行數之和恆等於檔案行數（本性質由呼叫端斷言，不靠這裡的敘述）。
    """
    total = len(text.splitlines())
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [Chunk(fallback_label, total, text)]
    lines = text.splitlines()
    chunks: list[Chunk] = []
    covered: set[int] = set()
    for node in tree.body:
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        start = min([node.lineno] + [d.lineno for d in node.decorator_list]) - 1
        end = node.end_lineno or node.lineno
        span = range(start, end)
        covered.update(span)
        chunks.append(Chunk(node.name, end - start, "\n".join(lines[start:end])))
    rest = [i for i in range(total) if i not in covered]
    if rest:
        chunks.append(Chunk(fallback_label, len(rest),
                            "\n".join(lines[i] for i in rest)))
    return chunks or [Chunk(fallback_label, total, text)]


def dead_tree_prefixes() -> list[str]:
    """登記在 `BUCKET_TREES` 卻**永遠抓不到**的樹前綴（正常為空清單）。

    WHY 這個後設檢查非有不可：桶定義與 token 抽取器是兩個各自可改的東西，而它們不相容時
    的表徵是**靜默低報**——掃描器照跑、照回一個看起來合理的比例，只是那一棵樹從來不在
    分母裡。本輪實測到的正是這件事（見 `_TOKEN_RE` 上方）。判準用抽取器自己去抽一段
    「只含該前綴」的合成文字：抽不到就是死條目。
    """
    dead: list[str] = []
    for bucket, trees in BUCKET_TREES.items():
        for tree in trees:
            probe = f"見 {tree}x.py 這一行"
            if not any(t.startswith(tree) or t == tree for t in _TOKEN_RE.findall(probe)):
                dead.append(f"{bucket}:{tree}")
    return dead


def classify(counts: collections.Counter) -> Verdict:
    """把參照計數轉成四個估計量。零參照 ⇒ 四者皆 `selfcontained`。"""
    hit = [b for b in BUCKET_PRIORITY if counts.get(b)]
    if not hit:
        return Verdict("selfcontained", "selfcontained", "selfcontained", ("selfcontained",))
    first = hit[0]
    dom = max(hit, key=lambda b: (counts[b], -BUCKET_PRIORITY.index(b)))
    return Verdict(first if len(hit) == 1 else "mixed", first, dom, tuple(hit))


# --------------------------------------------------------------------- 量測（棘輪與 probe 共用）
#: 列舉時要跳過的快取目錄（口徑同 `_CACHE_DIR_NAMES`）。
CACHE_PARTS: frozenset[str] = frozenset(
    {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"})


def guard_surface_files(root) -> list:
    """棘輪真正管的那個面：**非遞迴** `tools/tests/*.py`（含未追蹤檔）。"""
    return sorted((root / GUARD_SURFACE_REL).glob(GUARD_LINE_GLOB))


def classify_units(root, paths, grain: str = "chunk") -> list[dict]:
    """逐**守備單元**分類。`grain="file"` 是與上一輪可比對的粒度，`"chunk"` 是棘輪的粒度。

    🔴 本函式是量測的**唯一實作**：棘輪（`tools/tests/`）與普查 probe（`tools/probe/`）
    都消費它。兩邊各寫一份的話，「probe 印的比例」與「棘輪判的比例」會是兩個數而沒有人
    知道差在哪——那正是本 repo 反覆判過的「同一份知識住兩個家」。
    """
    units: list[dict] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(root).as_posix()
        want = len(text.splitlines())
        chunks = [Chunk(rel, want, text)] if grain == "file" else split_chunks(text)
        # 🔴 切塊不得增減行（fail-loud，不靜默吸收）：各塊之和必須逐字等於檔案行數，
        # 否則本量測的總量會與棘輪總量對不起來而沒有人知道差在哪。
        got = sum(c.lines for c in chunks)
        if got != want:
            raise AssertionError(f"[切塊漏行] {rel}: 各塊合計 {got} != 檔案行數 {want}")
        for chunk in chunks:
            counts = reference_counts(chunk.text, self_name=path.name)
            verdict = classify(counts)
            units.append({
                "file": rel, "unit": chunk.label, "lines": chunk.lines,
                "refs": dict(sorted(counts.items())),
                "exclusive": verdict.exclusive, "firstmatch": verdict.firstmatch,
                "dominant": verdict.dominant, "any_of": list(verdict.any_of),
            })
    return units


def bucket_lines(units: list[dict], estimator: str = "exclusive") -> collections.Counter:
    """`{桶名: 行數}`。`estimator="any"` 是上界（一單元計入多桶，總和 > 面的行數）。"""
    tally: collections.Counter = collections.Counter()
    for unit in units:
        for bucket in (unit["any_of"] if estimator == "any" else [unit[estimator]]):
            tally[bucket] += unit["lines"]
    return tally


def measure_shrink_only(root) -> dict[str, int]:
    """棘輪的量測入口：以 `GUARD_BUCKET_RATCHET_BASIS` 的粒度／估計量量 shrink-only 那幾桶。"""
    grain, estimator = GUARD_BUCKET_RATCHET_BASIS
    tally = bucket_lines(classify_units(root, guard_surface_files(root), grain), estimator)
    return {b: tally.get(b, 0) for b in SHRINK_ONLY_BUCKETS}


# --------------------------------------------------------------------- 分桶棘輪
#: 各 shrink-only 桶的**凍結基準**（`exclusive` 歸屬下的行數）。
#: 取值紀律同 `_FROZEN_GUARD_LINES`／`_TIER_BASELINE`：**當回合實測直接填入、零加減推算、
#: 不留成長緩衝**。合法縮小後必須同步下修（否則餘裕就是日後無聲加回去的破口）。
#: 現查／重釘用：`python tools/probe/guard_layer_bucket_census.py --json`
#: 🔴 歸屬基準是 **chunk 粒度的 `exclusive`**（見 `GUARD_BUCKET_RATCHET_BASIS`），不是檔級。
_FROZEN_SHRINK_ONLY_BUCKET_LINES: dict[str, int] = {
    # 🔴 這兩個值是**抽取器修正後**重取的（見 `_TOKEN_RE` 上方那段：以點開頭的樹前綴原本
    # 是死條目）。修正前 prose 量到 4464、guard_self 3566；修正後兩者**都更低**，因為原先
    # 被誤丟進散文桶的 `.claude/hooks/` 一族回到了 `root_infra`。⇒ 重釘方向是**下修＝判準
    # 更嚴**，不是為了讓紅變綠而放寬（放寬會是把值往上調）。
    # 🔴 DEF-200-208（R101，四方複審核准一次性例外，同批護欄層重釘，round-label-ok）：prose 桶 4119→4182  # noqa: E501
    # （+63）——真實成長，非本輪造成（`tools/tests/` 逐檔漂移的散文比例本就隨判準擴充
    # 自然增加，多輪未覆核）；guard_self 實測降到 3494（低於基準 3545 但仍在
    # `BUCKET_STALE_SLACK` 容忍帶內，未觸發 `[分桶基準過時]`，故本列保留不動）。現查／重釘
    # 指令：`python tools/probe/guard_layer_bucket_census.py --json`。
    # 🔴 R118 round-label-ok 收尾單人窗口：guard_self 3545→3246（DEF-200-212 P1-5 史料搬遷抵銷批，
    # test_check_defect_log_crossref.py 十七支 class-level docstring 搬離 tools/tests/
    # 使該桶實測明顯低於基準，觸發 `[分桶基準過時]`，依判準第三向要求重釘為實測值；
    # 這是判準設計的正常收斂動作，非放寬）。
    "prose": 4182,
    "guard_self": 3246,
}

#: 棘輪吃的粒度與估計量。寫成常數而不是散文，是為了讓 probe 與棘輪不可能各讀一種
#: （probe 的預設 `--grain` 必須等於這裡的粒度，由消費端測試雙向釘住）。
GUARD_BUCKET_RATCHET_BASIS = ("chunk", "exclusive")

#: 允許成長那三桶的**當輪實測快照**（同一粒度／估計量）——刻意**不當判準**，只做對照，
#: 讓 diff 上看得出成長跑到哪一桶去了。判準只在 shrink-only 那兩桶。
_GROWTH_BUCKET_SNAPSHOT: dict[str, int] = {
    "production": 33,
    "root_infra": 10025,
    "sdd": 1084,
}

#: 縮小後未重釘的容忍帶。形狀與理由逐字對齊 `_GUARD_LINE_STALE_SLACK`：單邊棘輪只會腐化，
#: 縮下來卻不重釘的話，餘裕就是日後無聲加回去的破口。
BUCKET_STALE_SLACK = 0.05


def bucket_ratchet_problems(
    measured: dict[str, int],
    frozen: dict[str, int] | None = None,
    slack: float = BUCKET_STALE_SLACK,
) -> list[str]:
    """分桶棘輪的判準。回空清單＝通過。

    三向（前兩向是主牙，第三向防腐，形狀照抄本 repo 既有的雙邊帶慣例）：
      (1) `[分桶成長]` shrink-only 桶的實測 > 凍結基準 ⇒ 紅。**這一向是本機制存在的理由**：
          它讓「加一支守散文的鎖」不再與「加一支守生產碼的鎖」付一樣的代價。
      (2) `[分桶缺席]` 凍結表少了某個 shrink-only 桶 ⇒ 紅。少一列就等於那一桶不受判準，
          而「桶被靜默拿掉」與「那一桶沒成長」在單邊計數下長得一模一樣。
      (3) `[分桶基準過時]` 實測明顯低於基準（差幅 > `slack`）⇒ 紅，要求重釘為實測值。
    """
    frozen = _FROZEN_SHRINK_ONLY_BUCKET_LINES if frozen is None else frozen
    problems: list[str] = []
    for bucket in SHRINK_ONLY_BUCKETS:
        if bucket not in frozen:
            problems.append(
                f"[分桶缺席] shrink-only 桶 `{bucket}` 不在 _FROZEN_SHRINK_ONLY_BUCKET_LINES"
                "——少一列即那一桶不受判準，而它與「沒成長」在單邊計數下無法區分"
            )
            continue
        base, now = frozen[bucket], measured.get(bucket, 0)
        if now > base:
            problems.append(
                f"[分桶成長] shrink-only 桶 `{bucket}`：{base} → {now}（+{now - base}）"
                "——這一桶只准往下。守散文／守自己的鎖要長，先問「該被守的事實能不能移出"
                "散文」（棘輪自己列的第三條出口）；真的必須長，請帶四方複審裁決重釘。"
            )
        elif now < int(base * (1 - slack)):
            problems.append(
                f"[分桶基準過時] shrink-only 桶 `{bucket}`：基準 {base}、實測 {now}"
                f"（低於基準的 {1 - slack:.0%}）——請重釘為 {now}，否則這段餘裕就是日後"
                "無聲加回去的破口"
            )
    return problems
