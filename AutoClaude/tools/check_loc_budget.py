#!/usr/bin/env python
"""LOC budget checker — tiered policy (ADR-SD07-001 v1.0, SD_07 W0).

分級政策（取代 SD_02/05/06 250 LOC 一刀切）：

  | tier           | budget | 對應目錄 / 識別                              |
  |----------------|--------|---------------------------------------------|
  | data           | 150    | autoclaude/models/, autoclaude/core/ports/  |
  | plugin_entry   | 250    | autoclaude/plugins/*_plugin.py, */plugin.py |
  | strategy       | 300    | autoclaude/core/services/mutation/, prompt_builder |
  | adapter        | 400    | autoclaude/infra/adapters/, infra/repositories/ |
  | service        | 500    | autoclaude/core/services/, steps_orchestrator/, playbook_runner.py |
  | contract       | 400    | autoclaude/core/hookspec.py, wiring.py, execution/types.py |
  | absolute_limit | 750    | 全域絕對紅線（任何層級不得超）              |

per-file overrides 由 .loc-budget.toml 提供（需 Architect / SD 雙簽核 +
PR description 書面理由，ADR §6.2）。

總量 cap：total LOC ≤ baseline × 1.20（防爆漲，與 tier/absolute 違規**同級阻塞**，
見下方 has_violation）。單檔 tier 餘裕過低時印非阻塞 [TIER-WARN]；total 逼近 cap
時印非阻塞 [WARN]——兩者皆 rc 不變、不進 has_violation。沿革（R56/R60/R71 訂正
歷程與回歸鎖清單）搬至
docs/06_quality/LOC_Budget_Ratchet_History.md〈總量 cap 與預警帶沿革〉節。

使用：
  python tools/check_loc_budget.py             # 檢查（CI gate）
  python tools/check_loc_budget.py --update    # 重釘 baseline；R56 註記：刻意不接線任何
                                               # 閘門，僅供 ADR §6.3 核准後人工執行。
                                               # 🔴 ADR-XPLAT-013 條文五（E4）：本旗標**不再**
                                               # 連動 20% 緩衝（cap）——見 --repin-cap。
  python tools/check_loc_budget.py --repin-cap # 獨立重釘 cap 基準（ADR-XPLAT-013 條文五）；
                                               # 與 --update 刻意分開兩支旗標，僅供 Architect+SD
                                               # 雙簽核准後人工執行，不得同批呼叫互相取代
  python tools/check_loc_budget.py --json      # 輸出 JSON 報表
"""
from __future__ import annotations

import fnmatch
import json
import sys
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = PROJECT_ROOT / ".loc_baseline"
OVERRIDE_FILE = PROJECT_ROOT / ".loc-budget.toml"
#: ADR-XPLAT-013 條文五（E4）：cap 的獨立審核基準，刻意是**另一個檔**而非
#: `.loc_baseline` 的第二個欄位——兩個檔各自被哪支函式讀寫，一眼就能稽核。
CAP_BASIS_FILE = PROJECT_ROOT / ".loc_cap_basis"
#: DEF-200-208：`.loc_baseline` 是用**哪一把尺**（`POLICY_VERSION`）釘的，同樣是
#: **另一個檔**而非 `.loc_baseline` 的第二個欄位（理由同 `CAP_BASIS_FILE`）。非有
#: 不可的理由見 `pricing_exemption_problems()` 的 WHY：「baseline 比 total 大/小」
#: 這個不等式在計價規則變了之後**結構上恆假地被拿來同時代表兩件相反的事**
#: （已重釘 vs. total 長過陳舊 baseline），因為兩者用的是不同的尺，magnitude
#: 比較本身就沒有意義（見 `POLICY_VERSION` 上方〈通約規則〉①）。判準改成**問
#: 「這份 baseline 是不是現在這把尺釘的」**（provenance），不再從數字大小反推狀態。
BASELINE_POLICY_FILE = PROJECT_ROOT / ".loc_baseline_policy_version"

# 強制 stdout/stderr 為 UTF-8 的唯一實作、與 ADR-XPLAT-012 條文五 §2 Phase 1 觀察模式
# 分類器（敘事／斷言／空白）皆住 monorepo 根層 `tools/lib/`（見 `init_utf8_streams`
# 上方的 SSOT 說明；取用方式同 `AutoClaude/tools/snapshot_sync.py`）。
sys.path.insert(0, str(PROJECT_ROOT.parent / "tools" / "lib"))
from guard_line_taxonomy import (  # noqa: E402
    classify_file as _classify_guard_line_taxonomy,  # type: ignore[import-not-found]
)
from platform_utils import (  # noqa: E402
    init_utf8_streams as _init_utf8_streams,  # type: ignore[import-not-found]
)

# ADR-SD07-001 §4.2 分級表（順序敏感：上方 tier 優先匹配）
LOC_TIERS: dict[str, dict] = {
    "data": {
        "budget": 150,
        "patterns": [
            "autoclaude/models/",
            "autoclaude/core/ports/",
        ],
    },
    "plugin_entry": {
        "budget": 250,
        "patterns": [
            "autoclaude/plugins/*_plugin.py",
            "autoclaude/plugins/*/plugin.py",
        ],
    },
    "strategy": {
        "budget": 300,
        "patterns": [
            "autoclaude/core/services/mutation/",
            "autoclaude/decision/prompt_builder.py",
            # F-A1 / ADR-AGT-002 §2 + SRD_AGT_Phase3 §2.3：GoalDecomposer 設計屬
            # strategy tier ≤300，機械錨定使設計宣稱可被 CI 強制（流程改善 #8）
            "autoclaude/execution/goal_decomposer.py",
        ],
    },
    "adapter": {
        "budget": 400,
        "patterns": [
            "autoclaude/infra/adapters/",
            "autoclaude/infra/repositories/",
        ],
    },
    "contract": {
        "budget": 400,
        "patterns": [
            "autoclaude/core/hookspec.py",
            "autoclaude/core/wiring.py",
            "autoclaude/execution/types.py",
        ],
    },
    "service": {
        "budget": 500,
        "patterns": [
            "autoclaude/core/services/",
            "autoclaude/execution/steps_orchestrator/",
            "autoclaude/execution/playbook_runner.py",
        ],
    },
}
ABSOLUTE_LIMIT = 750
SCAN_ROOT = "autoclaude"
TOTAL_INCREASE_LIMIT = 1.20

#: 政策版本標記（ADR-XPLAT-013 條文六）：`count_loc()` 的計價規則本身改變時（門檻
#: 數字變動不算）才遞增——標記「這個 `.loc_baseline`／`total` 是用哪一把尺量出來的」。
#: provenance 追蹤機制、通約規則、磁碟既有 `.loc_baseline` 的已知缺口全文搬至
#: docs/06_quality/LOC_Budget_Ratchet_History.md〈POLICY_VERSION 通約規則〉節。
POLICY_VERSION = "v3-assertion-only+sd08-special"
# 總量預警帶門檻（ADR-SD07-001 §6.3 觸發條件 ② 的機械化；R56 round 5）：
# `total ≥ cap − TOTAL_WARN_MARGIN` 時印非阻塞 [WARN]。沿革與回歸鎖清單搬至
# docs/06_quality/LOC_Budget_Ratchet_History.md〈TOTAL_WARN_MARGIN 沿革〉節。
TOTAL_WARN_MARGIN = 10

# 單檔 tier 餘裕預警帶門檻（R60，DEF-101-526 交棒候選；非阻塞，不改 rc）。同時是
# ROOT_TOOLS_TIERS 的預警門檻（R76：與 AutoClaude tier 同一種度量，沿用同一數字）；
# `SPECIAL_FILES` 是 raw-line 棘輪、度量面不同，另立 `SPECIAL_WARN_MARGIN`。
# 「為什麼是 6」的實測依據、偽陽性成本分析、回歸鎖清單搬至
# docs/06_quality/LOC_Budget_Ratchet_History.md〈TIER_WARN_MARGIN 沿革〉節。
TIER_WARN_MARGIN = 6

# SPECIAL_FILES raw-line 棘輪的預警帶門檻（R76-16，非阻塞，不改 rc）。與
# TIER_WARN_MARGIN 分開立數：tier 量 `count_loc`（排除空行與純註解），SPECIAL_FILES
# 量 raw line（空行、註解、Markdown 全算），兩者度量面不同。「為什麼是 5」的實測
# 依據（R76-00 死結實例）搬至
# docs/06_quality/LOC_Budget_Ratchet_History.md〈SPECIAL_WARN_MARGIN 沿革〉節。
SPECIAL_WARN_MARGIN = 5

# 🔴 SPECIAL_FILES raw-line 棘輪的「門檻自己過期了」判準（R84／ARCH-05；阻塞——這一族
# 已有非阻塞預警帶卻多輪未被行動，故此側改阻塞）。門檻高於現值超過本值即紅，修法＝
# 重釘為現值（一行 diff），**禁止調大本常數來讓紅字消失**（方向鎖只准調小）。
# 三個邊界（下界 > SPECIAL_WARN_MARGIN／上界落在空隙上／方向鎖）的實測依據搬至
# docs/06_quality/LOC_Budget_Ratchet_History.md〈SPECIAL_STALE_SLACK 沿革〉節。
SPECIAL_STALE_SLACK = 32

# ADR-SD08-001 §3.1：CLAUDE.md 文件治理（≤ 400 行強制）
# SPECIAL_FILES 採 raw line count（wc -l 等價，含空行/註解，因 CLAUDE.md 為 Markdown）
#
# 根層 tools/ 逐檔棘輪（R68/R69 P3 起）：門檻＝納管當下實際行數，只准往下改；
# 要往上調必須先拆職責／抽共用模組，確認不可壓縮後才在缺陷帳本具名調高（同
# `_FROZEN_GUARD_LINES` 的重釘慣例）。逐檔調高沿革（R68/R69/R70/DEF-101-758/
# DEF-200-162/DEF-200-163/R81/R84 各檔具名理由）全文搬至
# docs/06_quality/LOC_Budget_Ratchet_History.md〈SPECIAL_FILES 逐列棘輪沿革〉節。
# 各檔現值不寫死在此（會過期）：`python tools/check_loc_budget.py --json` 現查。
SPECIAL_FILES: dict[str, int] = {
    "CLAUDE.md": 400,  # ADR-SD08-001 §2.1：CLAUDE.md ≤ 400 + Snapshot SSOT
    # SD_09 Pre-W0 audit P0-06：補長文件預算（Migration SOP / Sprint history）
    "docs/08_deployment/Production_Migration_SOP.md": 800,
    "docs/05_development/sprint_history.md": 2000,
    "../tools/dev_start.py": 1952,
    "../tools/check_script_parity.py": 1618,
    "../tools/archive_defect_log.py": 1507,
    "../tools/check_defect_log_crossref.py": 1479,
    "../tools/sync_onboarding_baselines.py": 1430,
    "../tools/run_root_unittests.py": 759,
    "../.claude/hooks/context_budget_guard.py": 1089,
}

#: 上面那批根層 tools/ 棘輪的共同違規理由（`_SPECIAL_REASONS` 逐檔複寫一份就是複本型缺陷）。
_ROOT_TOOLS_RATCHET_REASON = (
    "R69 P3 根層護欄層行數棘輪：門檻＝納管當下實際行數，只准往下改——"
    "先刪死碼／抽共用模組（先例：tools/lib/ci_liveness.py），"
    "確認為不可壓縮的真實功能後才在缺陷帳本具名調高本棘輪"
)

# SPECIAL_FILES 逐列的違規理由（未列者沿用 ADR-SD08-001 文件治理）。
_SPECIAL_REASONS: dict[str, str] = {
    "../tools/dev_start.py": (
        "DEF-101-271／274：>2000 行即升級為該輪必修——先刪死碼／抽共用模組"
        "（先例：R68 把 CI 逐軌活性偵測抽到 tools/lib/ci_liveness.py），"
        "確認為不可壓縮的真實功能後才在缺陷帳本具名調高本棘輪"
    ),
    **{
        rel: _ROOT_TOOLS_RATCHET_REASON
        for rel in SPECIAL_FILES
        if rel.startswith(("../tools/", "../.claude/hooks/"))
        and rel != "../tools/dev_start.py"
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# R75：monorepo **根層 `tools/`**（跨子專案護欄層）的 LOC 分級
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 缺陷本體：`SCAN_ROOT = "autoclaude"` ⇒ 分級政策（tier ＋ 絕對紅線）**一行都照不到
# 根層 `tools/`**，而那是一整層兩萬行以上的護欄程式碼（R68／R69 P3 只補了一半：
# 一次性快照，見下方 `SPECIAL_FILES`）。本節把既有載具（`count_loc`／`FileReport`／
# `_matches_pattern`／同一套報表與 rc 收斂）延伸到根層 `tools/`，**不另造第二套
# LOC 檢查器**。三個判準決定（預算沿用既有數字／`tools/tests/` 不納管／已入
# `SPECIAL_FILES` 的檔排除在 tier 檢查外）的立案缺陷與逐條理由全文搬至
# docs/06_quality/LOC_Budget_Ratchet_History.md〈根層 tools/ LOC 分級立案（R75）〉節。
ROOT_TOOLS_ROOT = PROJECT_ROOT.parent / "tools"
#: R81（Architect-B3）：`.claude/hooks/` 也是 monorepo 根層護欄層，此前**不在任何 LOC
#: 治理面內**——代價是量出來的（納管當下 `context_budget_guard.py` 為絕對紅線的 2.18
#: 倍）。立案缺陷與納管當下量測全文搬至
#: docs/06_quality/LOC_Budget_Ratchet_History.md〈ROOT_GUARD_ROOTS 立案（R81／Architect-B3）〉節。
#: 本次修法新增第三個掃描根 `PROJECT_ROOT / "tools"`（`AutoClaude/tools/`）：把
#: `check_loc_budget.py` 自身（連同 `AutoClaude/tools/` 其餘檔案）併入本機制自治，
#: 見 docs/06_quality/LOC_Budget_Ratchet_History.md〈AutoClaude/tools/ 自治納管〉節。
ROOT_GUARD_ROOTS: tuple[Path, ...] = (
    ROOT_TOOLS_ROOT,
    PROJECT_ROOT.parent / ".claude" / "hooks",
    PROJECT_ROOT / "tools",
)
#: R84（ARCH-04）：`guardrail_lib` 把 `tools/lib/` 整層當成同一種東西，而
#: `tools/lib/quota_gate.py` 是把 5 支同層 lib 組起來的**合成面**（fan-out 5），不是
#: leaf helper——這是分類錯誤，不是「該檔太胖」。三個判準（預算引用 `service` tier／
#: patterns 只收單檔不得用 glob／成員清單只准縮）與誠實劃界（`skip_group_policy.py`
#: 等未收錄成員的理由）全文搬至
#: docs/06_quality/LOC_Budget_Ratchet_History.md〈ROOT_TOOLS_HUB_TIER 立案（R84／ARCH-04）〉節。
ROOT_TOOLS_HUB_TIER = "guardrail_hub"
#: 成員數**上界**（只准調小）。今天 1 支：`quota_gate.py`。要加第二支＝先改這個數字，
#: 那一行 diff 就是「有人在放寬單檔上限」的可見痕跡（同 `SPECIAL_FILES` 的解鎖紀律：
#: 先拆職責／抽共用模組，確認不可壓縮後才具名調整並在缺陷帳本寫理由）。
ROOT_TOOLS_HUB_MEMBER_CAP = 1
#: fan-out 下界：至少 import 這麼多支**同層** `tools/lib/*.py` 才算 hub。取 3 的理由是
#: 判別力：`tools/lib/` 現況逐支 AST 實查，fan-out ≥3 的只有 `quota_gate`(5) 與
#: `windows_skip_tags`(4)，而 leaf 族全部是 0~1 ⇒ 門檻落在兩個族群之間的空隙上，
#: 不是落在密集區（改成 2 會把 leaf 族的上緣掃進來，改成 5 則只剩今天這一支＝寫死現況）。
ROOT_TOOLS_HUB_MIN_FANOUT = 3
ROOT_TOOLS_TIERS: dict[str, dict] = {
    # 順序敏感：hub 的單檔 pattern 必須排在 `tools/lib/` 目錄 pattern 之前。
    ROOT_TOOLS_HUB_TIER: {
        "budget": LOC_TIERS["service"]["budget"],
        "patterns": ["tools/lib/quota_gate.py"],
    },
    "guardrail_lib": {"budget": 400, "patterns": ["tools/lib/"]},
    # "AutoClaude/tools/"：本次修法新增，見 ROOT_GUARD_ROOTS 旁的說明與
    # docs/06_quality/LOC_Budget_Ratchet_History.md〈AutoClaude/tools/ 自治納管〉節。
    "guardrail_cli": {
        "budget": ABSOLUTE_LIMIT,
        "patterns": ["tools/", ".claude/hooks/", "AutoClaude/tools/"],
    },
}
#: 逐 tier 的違規理由（未列者沿用下方 `root_tools_reports()` 的通用字串）。hub 那一格的
#: 理由刻意寫成「本格是分類修正、不是額度」，因為看到紅字最省事的做法就是把自己加進
#: 成員清單——訊息必須先擋住那個出口。
_ROOT_TOOLS_TIER_REASONS: dict[str, str] = {
    ROOT_TOOLS_HUB_TIER: (
        "R84／ARCH-04 guardrail_hub：本 tier 是**分類修正**（合成面 ≠ leaf helper），"
        "不是可申請的額度。破線後不是把自己加進成員清單、也不是調高本格——"
        "先拆職責／抽共用模組（先例：tools/lib/ci_liveness.py），"
        "確認為不可壓縮的真實接線後才具名加進 SPECIAL_FILES 的 raw-line 棘輪並在缺陷帳本寫理由"
    ),
}
#: 不納管的子目錄（相對 `tools/`）——理由見上方第二條判準。
ROOT_TOOLS_EXCLUDED_DIRS: frozenset[str] = frozenset({"tests"})


@dataclass(frozen=True)
class FileReport:
    rel_path: str
    loc: int
    tier: str
    budget: int
    over_by: int
    override_reason: str | None


class UnparseableSourceError(ValueError):
    """`count_loc()` 對解析不出來的 `.py` 的**明確錯誤態**（ADR-XPLAT-013 條文二）。

    刻意是例外而不是「回 0」：計價器回 0 會讓「語法錯誤」變成**零成本**，那是本 ADR
    要關掉的套利門的鏡像版本（把整檔弄壞比刪行更省預算）。呼叫端要嘛修檔、要嘛在自己
    的迴圈裡把它翻譯成一筆違規——兩條路都會留下痕跡，回 0 不會。
    """


def count_loc(path: Path) -> int:
    """計價＝**只算斷言行**（ADR-XPLAT-013 條文一；改前為「排除空行與純註解行」）。

    判準本體不住本檔——委派 `tools/lib/guard_line_taxonomy.classify_file()` 的
    `.assertion` 桶（敘事＝docstring／裸字串 ∪ tokenize 判定的整行 `#`；空白免費）。
    一份判準一個家：本檔自己再實作一次同一個分類，兩份必然漂移。

    改動沿革（為何從「排除空行與純註解」改成「只算斷言」、`""; x = 1` 裸字串前綴
    套利門的發現與封堵、shebang/PEP 263 強制歸斷言的母體限定實測）全文搬至
    docs/06_quality/LOC_Budget_Ratchet_History.md〈count_loc() 計價規則沿革
    （ADR-XPLAT-013）〉節。回歸鎖：
    `AutoClaude/tests/contract/test_loc_budget_tiered.py::
    test_narrative_carrier_swap_is_priced_identically`／
    `test_a_bare_string_prefix_cannot_buy_a_free_line`。
    """
    if not path.exists():
        return 0
    t = _classify_guard_line_taxonomy(path)
    if t.unparseable:
        raise UnparseableSourceError(
            f"{path}: 分類器解析不出來（讀檔失敗或 SyntaxError）⇒ 計價器拒絕給行數。"
            "回 0 會讓語法錯誤變成零成本的預算優惠，那個失效方向比破線更糟。")
    return t.assertion


def count_raw_lines(path: Path) -> int:
    """計算原始行數（wc -l 等價，用於 Markdown 等非程式碼檔案）。"""
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def warn_band(reports: Iterable[FileReport], margin: int) -> list[FileReport]:
    """近上限但**尚未破線**的檔（餘裕 ≤ margin），以餘裕升冪排序（最緊的排最前）。

    R76：三層預警帶（AutoClaude tier／SPECIAL_FILES／根層 tools tier）共用這一個判準。
    刻意做成單一實作而非各層各寫一次——「同一份知識三個家」正是本檔一路在治的病，
    且已破線的檔一律排除（`over_by == 0`）由各自的阻塞段接手，免得同一件事印兩段。
    """
    return sorted(
        (r for r in reports if r.over_by == 0 and r.budget - r.loc <= margin),
        key=lambda r: (r.budget - r.loc, r.rel_path),
    )


def special_file_reports() -> list[FileReport]:
    """SPECIAL_FILES 的逐檔 raw-line 報表（**含未違規者**）。

    違規清單與預警帶共用**同一次掃描**：兩者若各走各的迴圈，判準就有兩個家。
    """
    reports: list[FileReport] = []
    for file_path, max_lines in SPECIAL_FILES.items():
        f = PROJECT_ROOT / file_path
        if not f.exists():
            continue
        actual = count_raw_lines(f)
        reports.append(
            FileReport(
                rel_path=file_path,
                loc=actual,
                tier="special",
                budget=max_lines,
                over_by=max(0, actual - max_lines),
                override_reason=_SPECIAL_REASONS.get(
                    file_path, "ADR-SD08-001 CLAUDE.md 文件治理"),
            )
        )
    return reports


def check_special_files() -> list[FileReport]:
    """ADR-SD08-001 §3.1：SPECIAL_FILES 的 raw line count **違規**清單。

    回傳型別刻意維持 `list[FileReport]`（不改成 `(violations, warn_band)` 二元組）：
    `AutoClaude/tests/tools/test_check_loc_budget_tier_headroom_warn.py` 以
    `monkeypatch.setattr(clb, "check_special_files", lambda: [])` 隔離本函式，改簽章
    會讓那道鎖在解包時 ValueError——修法不得把既有的鎖打紅。預警帶另由
    `special_file_reports()` ＋ `warn_band()` 取得，兩者共用同一次掃描。
    """
    return [r for r in special_file_reports() if r.over_by > 0]


def special_stale_reports() -> list[FileReport]:
    """門檻**明顯高於現值**的 raw-line 棘輪列（＝預先發放的成長額度，R84／ARCH-05）。

    射程刻意只有「有登記棘輪理由」的那些列（`_SPECIAL_REASONS`），**不含**
    `CLAUDE.md`／`docs/**` 那三列——後者是**政策預算**（ADR-SD08-001 文件治理、
    SD_09 Pre-W0 audit P0-06 的長文件預算），語意是「這份文件最多可以長到 N 行」，
    留餘裕正是它的設計；`sprint_history.md` 更是滾動窗口文件（設計上就要被 append）。
    把政策預算重釘成現值會與 ADR-SD08-001 的滾動窗口設計直接對撞，且下一次 sprint
    收錄就必紅——那不是治本，是把一道對的閘門改成錯的。
    判準取「provenance」而非路徑前綴：新加的棘輪列只要照體例寫上 `_SPECIAL_REASONS`
    就自動被本判準覆蓋；反過來，想靠「不寫理由」逃出射程的話，豁免列數會超過鎖檔
    釘住的上界而轉紅。
    """
    return sorted(
        (
            r
            for r in special_file_reports()
            if r.rel_path in _SPECIAL_REASONS
            and r.over_by == 0
            and r.budget - r.loc > SPECIAL_STALE_SLACK
        ),
        key=lambda r: (-(r.budget - r.loc), r.rel_path),
    )


def collect_total_loc(root: Path) -> int:
    return sum(count_loc(p) for p in root.rglob("*.py"))


def _matches_pattern(rel_posix: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        return rel_posix.startswith(pattern)
    return fnmatch.fnmatchcase(rel_posix, pattern)


def classify_file(rel_path: Path) -> tuple[str, int]:
    """依 LOC_TIERS 順序匹配，回傳 (tier_name, budget)。

    未匹配任何 tier → 預設使用 absolute_limit（750）以避免新檔案無 budget。
    """
    rel_posix = rel_path.as_posix()
    for tier_name, spec in LOC_TIERS.items():
        for pat in spec["patterns"]:
            if _matches_pattern(rel_posix, pat):
                return tier_name, spec["budget"]
    return "unclassified", ABSOLUTE_LIMIT


def load_overrides() -> dict[str, dict]:
    """讀 .loc-budget.toml [overrides]；不存在則回空 dict。"""
    if not OVERRIDE_FILE.exists():
        return {}
    with OVERRIDE_FILE.open("rb") as f:
        data = tomllib.load(f)
    return data.get("overrides", {})


def read_baseline() -> int | None:
    if not BASELINE_FILE.exists():
        return None
    try:
        return int(BASELINE_FILE.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def write_baseline(value: int) -> None:
    BASELINE_FILE.write_text(f"{value}\n", encoding="utf-8")


def read_baseline_policy_version() -> str | None:
    """`.loc_baseline` 是用哪一把尺（`POLICY_VERSION`）釘的（DEF-200-208）。

    回傳 `None` 表示**尚未有人在本機制落地後跑過 `--update`**——現況磁碟上的
    `.loc_baseline`（17032）最後一次寫入是 2026-06-13（`git log -- .loc_baseline`
    可查），早於 `POLICY_VERSION` 這個符號存在的時間點，此時「它是哪一版尺釘的」
    只能誠實回答「不可考」，**不得**猜成目前的 `POLICY_VERSION`（那會把一份用舊尺
    量的數字偽裝成用新尺量的，比缺記錄更糟——同 `tools/lib/baseline_origin.py`
    「猜的指紋比誠實的空值更危險」那條原則）。呼叫端（`pricing_exemption_problems()`）
    對 `None` 的處置是「視為尚未用目前的尺重釘」，即安全預設，而非放行。
    """
    if not BASELINE_POLICY_FILE.exists():
        return None
    try:
        return BASELINE_POLICY_FILE.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def write_baseline_policy_version(value: str) -> None:
    """`write_baseline()` 的 provenance 搭檔——刻意兩支函式各寫各的檔（同
    `write_cap_basis()` 旁的設計說明），讓「重釘 baseline 數值」與「記下釘它的尺」
    在呼叫端是兩個可以各自被稽核、卻又總是成對出現在 `check()` 裡的動作。
    """
    BASELINE_POLICY_FILE.write_text(f"{value}\n", encoding="utf-8")


def read_cap_basis() -> int | None:
    """`cap` 的**獨立**審核基準（ADR-XPLAT-013 條文五；R100 §E-4 的修憲項）。

    🔴 為什麼非有不可：改前 `cap = int(baseline * TOTAL_INCREASE_LIMIT)` 一路都是
    **即時**從 `baseline` 算出來、從未獨立持久化過——於是每一次 `--update`（不論是
    ADR-SD07-001 §6.3 的核准成長、還是本 ADR 條文四的計價規則變更豁免出口）都會
    **順帶**把 cap 一起抬高，而後者的立案理由逐字是「不必重釘 baseline」，從未打算
    核准任何新增額度。R100 §E-4 實測：`--update` 把 baseline 17032→17079 的同時，
    cap 20438→20494（**+56**，語意反轉——條文四把它描述成「沒收陳舊餘裕的出口」，
    實際是加碼）。

    回傳 `None` 表示**尚未有人跑過** `--repin-cap`：此時 `check()` 的呼叫端會退回
    沿用 `baseline` 當 cap 基準（維持本輪落地當下的既有行為與既有回歸測試逐字不變，
    見 `AutoClaude/tests/contract/test_loc_budget_tiered.py::frozen_cap`），**這個
    退回狀態下 `--update` 仍會間接移動 cap**——真正的解耦要等第一次 `--repin-cap`
    落地才生效。本輪只落地機制本身，尚未執行那一次獨立審核（見 ADR §9 WHY）。
    """
    if not CAP_BASIS_FILE.exists():
        return None
    try:
        return int(CAP_BASIS_FILE.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def write_cap_basis(value: int) -> None:
    """`--repin-cap` 專用寫入口——刻意與 `write_baseline()` 是兩支不同函式、寫兩個不同
    檔案，讓「重釘 baseline」與「重釘 cap 基準」在程式碼層面就是兩個不能被同一個呼叫
    誤觸的動作（同 ADR-XPLAT-013 條文五的旗標分離設計）。
    """
    CAP_BASIS_FILE.write_text(f"{value}\n", encoding="utf-8")


def iter_source_files() -> Iterable[Path]:
    for p in (PROJECT_ROOT / SCAN_ROOT).rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


def iter_root_tools_files() -> Iterable[Path]:
    """跨子專案護欄層納管的 `.py`：monorepo 根層 `tools/` ＋ `.claude/hooks/` ＋
    `AutoClaude/tools/`（見 `ROOT_GUARD_ROOTS`）。

    排除 `tests/` 與快取目錄。射程刻意**只有根層那一份** `.claude/hooks/`：
    `AutoClaude/.claude/hooks/` 由該子專案自己的閘門管，`AISDLC_SDD/**` 各版依
    Copy-on-Evolve 凍結不動。
    """
    for root in ROOT_GUARD_ROOTS:
        if not root.is_dir():  # pragma: no cover - 非 monorepo checkout
            continue
        for p in root.rglob("*.py"):
            parts = set(p.relative_to(root).parts[:-1])
            if "__pycache__" in parts or parts & ROOT_TOOLS_EXCLUDED_DIRS:
                continue
            yield p


def classify_root_tools_file(rel_posix: str) -> tuple[str, int]:
    """依 `ROOT_TOOLS_TIERS` 順序匹配（順序敏感：`tools/lib/` 必須排在 `tools/` 之前）。"""
    for tier_name, spec in ROOT_TOOLS_TIERS.items():
        for pat in spec["patterns"]:
            if _matches_pattern(rel_posix, pat):
                return tier_name, spec["budget"]
    return "unclassified", ABSOLUTE_LIMIT  # pragma: no cover - `tools/` 樣式已涵蓋全樹


def root_tools_reports() -> list[FileReport]:
    """根層 `tools/` 的逐檔報表（**含未違規者**）。

    R76 訂正：本函式原本只回違規（`build_root_tools_reports()`），理由寫的是「本層
    不參與 `total`／baseline cap 的計算，故沒有全表的消費者」——那句話在**預警帶**
    出現之前成立。預警帶正是「未違規但快滿了」的消費者，只回違規等於結構上看不到它。
    """
    reports: list[FileReport] = []
    for p in iter_root_tools_files():
        rel_posix = p.relative_to(ROOT_TOOLS_ROOT.parent).as_posix()
        # 已由 SPECIAL_FILES 的 raw-line 棘輪管的檔不重複審判（見上方第三條判準）。
        if f"../{rel_posix}" in SPECIAL_FILES:
            continue
        loc = count_loc(p)
        tier_name, budget = classify_root_tools_file(rel_posix)
        reports.append(
            FileReport(
                rel_path=rel_posix,
                loc=loc,
                tier=tier_name,
                budget=budget,
                over_by=max(0, loc - budget),
                override_reason=_ROOT_TOOLS_TIER_REASONS.get(
                    tier_name,
                    "R75 根層護欄層 LOC 分級：先拆職責／抽共用模組"
                    "（先例：tools/lib/ci_liveness.py），確認為不可壓縮的真實功能後，"
                    "才把該檔具名加進 check_loc_budget.SPECIAL_FILES 的 raw-line 棘輪"
                    "並在缺陷帳本寫明理由",
                ),
            )
        )
    return reports


def build_root_tools_reports() -> list[FileReport]:
    """根層 `tools/` 的**違規**清單（破線最多的排最前）。"""
    return sorted(
        (r for r in root_tools_reports() if r.over_by > 0),
        key=lambda r: (-r.over_by, r.rel_path),
    )


def guard_taxonomy_reports() -> list[dict]:
    """ADR-XPLAT-012 條文五 §2／§7：Phase 1 觀察模式——逐檔敘事／斷言／空白／
    unparseable 快照，**只回報、不參與 rc／violations**（該 ADR 條文五 §1）。

    掃描面＝條文五 §5 SSOT 公式 `root_tools_reports() ∪ special_file_reports()`：
    兩個來源集合已由 `root_tools_reports()` 自身排除已入 `SPECIAL_FILES` 的檔
    （見該函式 docstring），故互斥、直接串接即可、不需額外去重。
    """
    reports: list[dict] = []
    for rel_path, base in (
        *((r.rel_path, PROJECT_ROOT.parent) for r in root_tools_reports()),
        *((r.rel_path, PROJECT_ROOT) for r in special_file_reports()),
    ):
        t = _classify_guard_line_taxonomy(base / rel_path)
        reports.append({
            "rel_path": rel_path,
            "narrative": t.narrative,
            "assertion": t.assertion,
            "blank": t.blank,
            "unparseable": t.unparseable,
        })
    return reports


def build_reports(overrides: dict[str, dict]) -> list[FileReport]:
    reports: list[FileReport] = []
    for p in iter_source_files():
        rel = p.relative_to(PROJECT_ROOT)
        loc = count_loc(p)
        tier_name, budget = classify_file(rel)
        override_reason = None
        rel_posix = rel.as_posix()
        if rel_posix in overrides:
            ov = overrides[rel_posix]
            tier_name = ov.get("tier", tier_name)
            override_reason = ov.get("reason", "(no reason given)")
            budget = LOC_TIERS.get(tier_name, {}).get("budget", ABSOLUTE_LIMIT)
        reports.append(
            FileReport(
                rel_path=rel_posix,
                loc=loc,
                tier=tier_name,
                budget=budget,
                over_by=max(0, loc - budget),
                override_reason=override_reason,
            )
        )
    return reports


def check(
    update_baseline: bool = False, repin_cap: bool = False, as_json: bool = False
) -> int:
    overrides = load_overrides()
    reports = build_reports(overrides)

    tier_violations: list[FileReport] = []
    absolute_violations: list[FileReport] = []
    for r in reports:
        if r.loc > ABSOLUTE_LIMIT:
            absolute_violations.append(r)
        if r.over_by > 0:
            tier_violations.append(r)

    # ADR-SD08-001 §3.1：CLAUDE.md ≤ 400 強制
    special_violations = check_special_files()
    # R75：monorepo 根層 tools/ 的分級（獨立帳，不進 total／baseline cap）
    root_tools_violations = build_root_tools_reports()
    # R76（R76-16）：上面兩層各自的**非阻塞**預警帶。刻意各自重掃一次而非把違規與
    # 預警帶一起回傳：`check_special_files()` 被既有鎖以 monkeypatch 抽換，改簽章會讓
    # 那道鎖解包 ValueError；重掃的成本是幾十次 `count_loc`，換掉一次打紅既有鎖。
    special_warn = warn_band(special_file_reports(), SPECIAL_WARN_MARGIN)
    root_tools_warn = warn_band(root_tools_reports(), TIER_WARN_MARGIN)
    # R84（ARCH-05）：棘輪門檻自己過期的那一側。**阻塞**（見 SPECIAL_STALE_SLACK 的 WHY）。
    special_stale = special_stale_reports()

    total = sum(r.loc for r in reports)
    baseline = read_baseline()
    if update_baseline or baseline is None:
        write_baseline(total)
        # DEF-200-208：每一次重釘 baseline 數值，同一時間就把「用哪一把尺釘的」
        # 寫下來——provenance 與數值同一次寫入，不留「先有數字、後補尺別」的空窗。
        write_baseline_policy_version(POLICY_VERSION)
        baseline = total
        print(f"[baseline] 已寫入 .loc_baseline = {total}（policy_version={POLICY_VERSION}）")

    # ADR-XPLAT-013 條文五（E4）：cap 基準與 baseline 重釘解耦。`cap_basis_pinned`
    # 為 False 時（尚未有人跑過 `--repin-cap`）沿用 `baseline` 當**啟動預設**——這一步
    # 刻意保留，讓落地當下（`.loc_cap_basis` 不存在）的 cap 數值與改前逐字相同、
    # 零回歸；`read_cap_basis()` docstring 記載了這個退回狀態下 `--update` 仍間接連動
    # cap 的已知殘留，尚待獨立那一次審核執行。
    cap_basis = read_cap_basis()
    cap_basis_pinned = cap_basis is not None
    if repin_cap:
        write_cap_basis(baseline)
        cap_basis = baseline
        cap_basis_pinned = True
        print(f"[cap-basis] 已寫入 .loc_cap_basis = {baseline}（獨立審核步驟；"
              "此後 --update 不再連動 cap，需再次執行 --repin-cap 才會調整）")
    if cap_basis is None:
        cap_basis = baseline
    cap = int(cap_basis * TOTAL_INCREASE_LIMIT)
    total_violation = total > cap
    # 預警帶：已進 ADR §6.3 ② 的「餘裕耗盡」區間但尚未破線。**非阻塞**（不進
    # has_violation、不影響 rc），僅提示；破線後改由下方 [TOTAL] 阻塞訊息接手，
    # 故此處刻意排除 total_violation 以免同一件事印兩段。
    total_warn_band = (not total_violation) and total >= cap - TOTAL_WARN_MARGIN

    # R60（DEF-101-526）：單檔 tier 餘裕預警帶。排除已違規檔（由 [TIER] 阻塞段接手，
    # 免得同一件事印兩段）；以餘裕升冪排序，最緊的排最前面。
    # R76：判準本體上移為共用的 `warn_band()`（三層同一份實作）。
    tier_warn_band = warn_band(reports, TIER_WARN_MARGIN)

    if as_json:
        payload = {
            "total": total,
            "baseline": baseline,
            "cap": cap,
            "total_violation": total_violation,
            # ADR §6.3 的「必要證據」指定 --json 報表，故預警帶亦須在 JSON 可機讀，
            # 否則走正規程序的人反而看不到觸發條件 ②。
            "total_warn_band": total_warn_band,
            "total_warn_margin": TOTAL_WARN_MARGIN,
            # R60（DEF-101-526）：單檔 tier 餘裕預警帶亦須機讀——只印文字的話，
            # 以 --json 取證的自動化（含 nightly 報表）看不到這個治理衝突訊號。
            "tier_warn_margin": TIER_WARN_MARGIN,
            "tier_warn_band": [
                {**r.__dict__, "headroom": r.budget - r.loc} for r in tier_warn_band
            ],
            "absolute_violations": [r.__dict__ for r in absolute_violations],
            "tier_violations": [r.__dict__ for r in tier_violations],
            "special_violations": [r.__dict__ for r in special_violations],
            # R76（R76-16）：SPECIAL_FILES 與根層 tools 兩層的預警帶亦須機讀——只印
            # 文字的話，以 --json 取證的自動化（含 nightly 報表、sync_onboarding_baselines）
            # 結構上看不到「還剩幾行」，而那正是這兩層唯一的事前訊號。
            "special_warn_margin": SPECIAL_WARN_MARGIN,
            "special_warn_band": [
                {**r.__dict__, "headroom": r.budget - r.loc} for r in special_warn
            ],
            # R84（ARCH-05）：棘輪門檻過期側亦須機讀——`sync_onboarding_baselines` 這類
            # 以 `--json` 取證的自動化只看 JSON，只印文字等於對它們不存在。
            "special_stale_slack": SPECIAL_STALE_SLACK,
            "special_stale": [
                {**r.__dict__, "headroom": r.budget - r.loc} for r in special_stale
            ],
            # R75：根層護欄層獨立一欄（不併進 tier_violations——兩者度量面不同：那邊是
            # `autoclaude/`＋baseline cap，這邊是跨子專案護欄層、無 cap）。
            "root_tools_violations": [r.__dict__ for r in root_tools_violations],
            # 根層 tools 與 AutoClaude tier 同度量，故共用 tier_warn_margin，不另立欄位。
            "root_tools_warn_band": [
                {**r.__dict__, "headroom": r.budget - r.loc} for r in root_tools_warn
            ],
            "root_tools_tiers": {k: v["budget"] for k, v in ROOT_TOOLS_TIERS.items()},
            "policy_version": POLICY_VERSION,
            "absolute_limit": ABSOLUTE_LIMIT,
            "special_files": SPECIAL_FILES,
            # ADR-XPLAT-013 條文五（E4）：cap 的獨立審核基準——`cap_basis_pinned=False`
            # 時 `cap_basis` 只是沿用 `baseline` 的**啟動預設**（尚未有人跑過
            # `--repin-cap`），此時 `--update` 仍會間接移動 cap（見該常數旁的
            # docstring）；`True` 之後 `--update` 才真正不再連動 cap。
            "cap_basis": cap_basis,
            "cap_basis_pinned": cap_basis_pinned,
            # DEF-200-208：baseline 的 provenance——`None` 代表磁碟上的 `.loc_baseline`
            # 是在本機制落地前釘的（不可考，非「目前這把尺」），詳見
            # `read_baseline_policy_version()` docstring。
            "baseline_policy_version": read_baseline_policy_version(),
        }
        # ADR-XPLAT-012 條文五 §2：Phase 1 觀察模式並存欄位——只加欄位，不動上面
        # 任何既有鍵、不影響 `has_violation`／rc（見本函式末尾組裝式，taxonomy 未入內）。
        guard_taxonomy = guard_taxonomy_reports()
        payload["guard_taxonomy"] = guard_taxonomy
        payload["narrative_total"] = sum(r["narrative"] for r in guard_taxonomy)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        violations_count = (
            len(absolute_violations)
            + len(tier_violations)
            + len(special_violations)
            + len(special_stale)
            + len(root_tools_violations)
            + (1 if total_violation else 0)
        )
        print(
            f"[check_loc_budget v2-tiered] total={total} baseline={baseline} "
            f"cap={cap} violations={violations_count} "
            f"(absolute={len(absolute_violations)} tier={len(tier_violations)} "
            f"special={len(special_violations)} "
            f"special_stale={len(special_stale)} "
            f"root_tools={len(root_tools_violations)} "
            f"total={'1' if total_violation else '0'})"
        )
        if absolute_violations:
            print(f"\n[ABSOLUTE] absolute red line violations (limit {ABSOLUTE_LIMIT} LOC):")
            for r in absolute_violations:
                print(f"  [{r.tier}] {r.rel_path}: {r.loc} > {ABSOLUTE_LIMIT}")
        if tier_violations:
            print("\n[TIER] tiered budget violations:")
            for r in tier_violations:
                tag = f" (override: {r.override_reason})" if r.override_reason else ""
                print(
                    f"  [{r.tier}<={r.budget}] {r.rel_path}: {r.loc} > {r.budget} "
                    f"(+{r.over_by}){tag}"
                )
        if total_violation:
            print(
                f"\n[TOTAL] total LOC cap violation: {SCAN_ROOT}/: {total} > "
                f"cap_basis({cap_basis}) x {TOTAL_INCREASE_LIMIT} = {cap}"
                + ("" if cap_basis_pinned else "（cap_basis 尚未獨立重釘，沿用 baseline）")
            )
        if total_warn_band:
            print(
                f"\n[WARN] total LOC 已進預警帶（非阻塞，rc 不變）：{total} ≥ "
                f"cap({cap}) − {TOTAL_WARN_MARGIN}，餘裕僅剩 {cap - total} 行。"
                "\n       連續 2 輪落在本帶即滿足 ADR-SD07-001 §6.3 觸發條件 ②"
                "（baseline 重新校準程序）。"
                "\n       先減後調：①刪死碼／收斂重複實作 ②零／負增行手法 "
                "③確認為不可壓縮的真實功能後才調 baseline（Architect + SD 雙簽）。"
                "\n       見 docs/04_planning/ADR/ADR-SD07-001-loc-policy.md §6.3。"
            )
        if tier_warn_band:
            print(
                f"\n[TIER-WARN] {len(tier_warn_band)} 支檔案 tier 餘裕 ≤ "
                f"{TIER_WARN_MARGIN} 行（非阻塞，rc 不變）——**動這些檔前先讀這段**："
            )
            for r in tier_warn_band:
                print(
                    f"  [{r.tier}<={r.budget}] {r.rel_path}: {r.loc} "
                    f"（餘裕 {r.budget - r.loc} 行）"
                )
            print(
                "       在這些檔上「修 lint」與「守 LOC 預算」互斥，且兩者都是硬閘"
                "（DEF-101-526 實測：4 處 E501 斷行 → +6 行 → LOC 閘門紅）。"
                "\n       修 E501 請用**行內 noqa**（0 行成本）而非斷行；勿加 "
                "per-file-ignores（會讓整檔永久失去該規則保護）。"
                "\n       🔴 這裡曾經教人「說明文字寫成 `#` 而非 docstring」——那句話已由 "
                "ADR-XPLAT-013 刪除：`count_loc` 現在只算斷言行，兩種敘事載體同價，"
                "換載體省不到一行。要省預算只有一條路：**少寫斷言**（拆職責／抽共用模組）。"
            )
        if special_violations:
            print("\n[SPECIAL] ADR-SD08-001 SPECIAL_FILES line-count violations:")
            for r in special_violations:
                print(
                    f"  [{r.tier}<={r.budget}] {r.rel_path}: {r.loc} > {r.budget} "
                    f"(+{r.over_by}) — {r.override_reason}"
                )
        if special_stale:
            print(
                f"\n[SPECIAL-STALE] {len(special_stale)} 支 SPECIAL_FILES raw-line 棘輪的"
                f"**門檻自己過期了**（陳舊餘裕 > {SPECIAL_STALE_SLACK} 行；阻塞）："
            )
            for r in special_stale:
                print(
                    f"  [{r.tier}<={r.budget}] {r.rel_path}: 現值 {r.loc} "
                    f"⇒ 陳舊餘裕 {r.budget - r.loc} 行"
                )
            print(
                "       這批門檻的語意是「＝納管當下實際行數，只准往下改」，買到的東西是"
                "「再往裡塞就會紅」。"
                "\n       門檻高於現值 ⇒ 那段差額可以無聲地長回去，該保證今天不成立。"
                "\n       修法＝**把上面每一支的門檻重釘為現值**（一行 diff；"
                "合法縮小後必須同步下修，這是本棘輪的維護紀律，不是新規定）。"
                "\n       🔴 反向出口已封：不得改大 SPECIAL_STALE_SLACK 來讓紅字消失"
                "（那等於把預先發放的成長額度再發回去，鎖檔的方向鎖只准調小）。"
            )
        if special_warn:
            print(
                f"\n[SPECIAL-WARN] {len(special_warn)} 支 SPECIAL_FILES raw-line 棘輪"
                f"餘裕 ≤ {SPECIAL_WARN_MARGIN} 行（非阻塞，rc 不變）——**動這些檔前先讀這段**："
            )
            for r in special_warn:
                print(f"  [{r.tier}<={r.budget}] {r.rel_path}: {r.loc} "
                      f"（餘裕 {r.budget - r.loc} 行）")
            print(
                "       這批門檻是 shrink-only 棘輪（R69 P3：門檻＝納管當下實際行數），"
                "**不得為了讓修改通過而調高**。"
                "\n       餘裕 0 時「補一筆具名登記」這種一行修法本身就會破線"
                "（R76-00 實測：A 鎖要求 +1 行、B 鎖禁止那一行）。"
                "\n       正解順序：①刪死碼／抽共用模組（先例 tools/lib/ci_liveness.py）"
                " ②確認為不可壓縮的真實功能後，才在缺陷帳本具名理由調高。"
            )
        if root_tools_warn:
            print(
                f"\n[ROOT-TOOLS-WARN] {len(root_tools_warn)} 支根層 tools/ 檔案 tier 餘裕"
                f" ≤ {TIER_WARN_MARGIN} 行（非阻塞，rc 不變）："
            )
            for r in root_tools_warn:
                print(f"  [{r.tier}<={r.budget}] {r.rel_path}: {r.loc} "
                      f"（餘裕 {r.budget - r.loc} 行）")
            print(
                "       破線後不是「調高預算」而是拆職責／抽共用模組；真的不可壓縮才"
                "具名加進 SPECIAL_FILES 的 raw-line 棘輪並在缺陷帳本寫明理由。"
            )
        if root_tools_violations:
            # R84：分級清單改由 `ROOT_TOOLS_TIERS` 現查（原本逐格寫死兩個 tier 名，新增
            # `guardrail_hub` 之後那份複本就會靜默漏報一格——同一份知識兩個家的最小實例）。
            _tier_list = " / ".join(
                f"{k}<={v['budget']}" for k, v in ROOT_TOOLS_TIERS.items())
            print(f"\n[ROOT-TOOLS] monorepo 根層 tools/ 分級違規（R75；{_tier_list}）：")
            for r in root_tools_violations:
                print(
                    f"  [{r.tier}<={r.budget}] {r.rel_path}: {r.loc} > {r.budget} "
                    f"(+{r.over_by}) — {r.override_reason}"
                )

    has_violation = (
        bool(absolute_violations)
        or bool(tier_violations)
        or bool(special_violations)
        # R84（ARCH-05）：門檻過期側與破線側**同級阻塞**——理由見 SPECIAL_STALE_SLACK 那段
        # 的「為什麼是阻塞而不是預警」（這一族已經有非阻塞訊號，而它多輪未被行動）。
        or bool(special_stale)
        or bool(root_tools_violations)
        or total_violation
    )
    return 1 if has_violation else 0


def main() -> int:
    # DEF-82-001/DEF-101-070 家族慣例：報表含中文/→ 等非 ASCII，Windows cp950 console
    # 直接 print 會 UnicodeEncodeError 中斷；stdout + stderr 皆強制 utf-8。
    # 🔴 R75：此處原本自帶一份「迴圈走 std 兩串流、逐一就地改編碼」的行內複本，而且它
    # 連 errors 參數都沒帶（stderr 預設 backslashreplace ⇒ 中文在非 CJK codepage 降解成
    # 反斜線逃逸字面，正是 R74 P0 的形態）。改為呼叫唯一實作
    # （`tools/lib/platform_utils.init_utf8_streams`，同 `snapshot_sync.py` 既有作法）。
    # ⚠️ 本註解刻意**不逐字引述**原本那段程式碼：`tools/tests/test_platform_utils_dedup.py`
    # 的寬判準是原始碼文字掃描，逐字引述會讓這支檔案照樣被算成一處複本（R73 教訓
    # 「訂正註記逐字引述＝製造新事實」的機械版）。
    _init_utf8_streams()
    update = "--update" in sys.argv
    repin_cap = "--repin-cap" in sys.argv
    as_json = "--json" in sys.argv
    return check(update_baseline=update, repin_cap=repin_cap, as_json=as_json)


if __name__ == "__main__":
    sys.exit(main())
