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

總量 cap：total LOC ≤ baseline × 1.20（防爆漲）。R56 訂正：此 cap 與 tier/absolute
違規**同級阻塞**（見下方 has_violation），非舊述的「sanity check」——宣稱與行為不一致
曾導致兩輪把它誤當軟性提示。baseline 重新校準須走 ADR-SD07-001 §6.3 正式程序
（先刪死碼／收斂重複實作，最後才調 baseline；Architect + SD 雙簽）。
R56 round 5 增訂：`total ≥ cap − TOTAL_WARN_MARGIN` 但尚未破線時印 **非阻塞** [WARN]
（rc 不變、不進 has_violation），把 §6.3 觸發條件 ② 的偵測從人眼改為機械。

R60 增訂（承接 DEF-101-526 明文交棒的 R60 候選）：**單檔** tier 餘裕 ≤
`TIER_WARN_MARGIN` 時印 **非阻塞** [TIER-WARN]（rc 不變、不進 has_violation），
把「LOC tier 滿載檔 × lint 斷行互斥」這個治理衝突從「只有踩到才會發現」改為事先告知。
刻意用 `[TIER-WARN]` 而非沿用 `[WARN]` 標籤：後者已被
tests/contract/test_loc_budget_tiered.py::test_warn_band_boundary_and_rc_invariant
以 `("[WARN]" in out) is expect_warn` 精確釘選為「總量預警帶專屬訊號」，共用標籤會讓
那道鎖在 repo 現況（預警帶非空）下恆真而失效。R71 訂正：此處原寫「3 支滿載檔」，
該數字已隨「刪死碼／收斂重複」輪失真——**現況不寫死於此**，現查＝
`python tools/check_loc_budget.py --json` 的 `tier_warn_band`。

使用：
  python tools/check_loc_budget.py            # 檢查（CI gate）
  python tools/check_loc_budget.py --update   # 更新 baseline；R56 註記：刻意不接線任何
                                              # 閘門，僅供 ADR §6.3 核准後人工執行
  python tools/check_loc_budget.py --json     # 輸出 JSON 報表
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

# 強制 stdout/stderr 為 UTF-8 的唯一實作住 monorepo 根層 `tools/lib/`（見該檔
# `init_utf8_streams` 上方的 SSOT 說明）；取用方式同 `AutoClaude/tools/snapshot_sync.py`。
sys.path.insert(0, str(PROJECT_ROOT.parent / "tools" / "lib"))
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
# R56 round 5 修正：ADR-SD07-001 §6.3 觸發條件 ② 是「連續 2 輪 total ≥ cap − 10」，
# 但本工具此前只在 total > cap 才有訊號 —— 落在預警帶時輸出與正常態一字不差，
# 該 ADR 自己的「緣起」段記載 R53(=cap)／R55(=cap−1) 兩次都是靠審查員逐字讀輸出
# 才發現。在一個把「9 支 vs 15 支」人工計數都機械化的 repo 裡，新訂程序不該只靠人眼。
# 本常數即該條的機械化。
# R56 round 5 補鎖（四方複核指出本訊號自身零回歸保護、且與 ADR 兩站點硬編互稱同步）：
#   - 本常數 ↔ ADR §6.3 ② 的「cap − 10」由 tests/contract/test_loc_budget_tiered.py::
#     test_total_warn_margin_matches_adr_sd07_001_section_6_3 自 ADR 正文抽數字比對，
#     機械鎖定而非人工宣稱；改任一站點未同步即翻紅。
#   - 下方預警帶四態邊界（>= 下緣／total==cap／破線）與「WARN 非阻塞、rc 不得改變」
#     由同檔 test_warn_band_boundary_and_rc_invariant 釘住；JSON 兩欄由
#     test_warn_band_json_payload_matches_text_mode 釘住。
TOTAL_WARN_MARGIN = 10

# R60（DEF-101-526 交棒的 R60 候選）：單檔 tier 餘裕預警帶。餘裕 ≤ 本值即印
# **非阻塞** [TIER-WARN]，不改 rc、不進 has_violation——刻意不改成 fail，那會當場
# 擋住現有的**合法**滿載檔。R71 訂正：原文在此寫死三支檔名與各自行數
# （pg_state_repository.py 400/400 等），已隨「刪死碼／收斂重複」輪全數失真；
# 現況一律現查 `python tools/check_loc_budget.py --json` 的 `tier_warn_band`。
#
# 為什麼是 6，而不是交棒文字裡舉例的 3（刻意上調，理由留痕）：
#   ① DEF-101-526 原文寫「如 `check_loc_budget` 對餘裕 ≤ 3 行的檔印 warning」——
#      「如」是舉例而非規格。
#   ② **同一列自己的實測數字反而否證 3**：該輪在滿載的 adapter 檔上修 4 處 E501，
#      斷行後實測 `406 > 400 (+6)`——+5 來自 4 處斷行（呼叫 +2、字典 +2、格式字串 +1）、
#      +1 來自 ruff I001 自動修復把 `import os, warnings` 拆兩行。也就是「一次 lint
#      修復」的實測代價是 6 行；門檻取 3 會讓餘裕 4~6 的檔照樣被咬、卻拿不到預警。
#   ③ 偽陽性成本實測（本輪 201 支計入檔）：餘裕 ≤3 命中 3 支、≤6 命中 5 支
#      （多出 evolution_plugin.py 245/250、core/ports/rtm_feedback.py 144/150）；
#      代價＝多印 2 行非阻塞提示，而這 2 支正是「一次 lint 斷行就會破線」的檔。
#   ④ 與既有 TOTAL_WARN_MARGIN=10 同形（近上限帶、只 WARN、rc 不變、JSON 亦曝露），
#      不新增第二種機制語意。
# 本值 ↔ 上述判準由 AutoClaude/tests/tools/test_check_loc_budget_tier_headroom_warn.py
# 釘選（含 bug-injection 驗紅）。
# R76 增訂：本常數同時是**根層 tools/ 分級**（`ROOT_TOOLS_TIERS`）的預警門檻——那一層
# 與 AutoClaude tier 是同一種度量（`count_loc` × tier 預算），沿用同一個數字才不會憑空
# 生出第三種「近上限」語意；`SPECIAL_FILES` 是 raw-line 棘輪、度量面不同，另立
# `SPECIAL_WARN_MARGIN`（見該常數上方）。
TIER_WARN_MARGIN = 6

# R76（R76-16）：`SPECIAL_FILES` raw-line 棘輪的預警帶門檻。**非阻塞**（不進
# has_violation、不改 rc），理由同 TIER_WARN_MARGIN——現況那批檔餘裕 0~2 全是**合法**
# 狀態（門檻依 R69 P3 慣例＝納管當下的實際行數，本來就是零餘裕設計），改 fail 會當場
# 擋住 repo。
#
# 為什麼另立一個數字、而不是沿用 TIER_WARN_MARGIN：兩者度量面不同。tier 量 `count_loc`
# （排除空行與純註解），SPECIAL_FILES 量 raw line（空行、註解、Markdown 全算）。
#
# 為什麼是 5：
#   ① 這批檔的最小合法增量不是「一行程式」，而是「一筆具名登記」或「一段訂正註記」。
#      R76-00 實測到的死結正是這個形狀：工具訊息教人往 `_GOVERNANCE_DOCS` 補一筆
#      ＝+1 行，而 `check_defect_log_crossref.py` 當時 1474/1474 餘裕 0 ⇒ **A 鎖要求的
#      補救動作正好是 B 鎖的違規**。第一個訊號就是紅，中間沒有任何預警。
#   ② 一段照本 repo 體例寫的訂正註記（WHY ＋ 實測 ＋ 邊界）實測約 4~5 行，取 5 剛好
#      覆蓋「照規矩留痕」這個最常見的增量形態。
#   ③ 不取更大：raw line 連空行都算，門檻愈大愈接近「常駐全亮」，而常駐全亮的燈等於
#      沒有燈。超過 5 就不是「快滿了」而是「一直都很滿」，那是棘輪本身該被重新談的事。
# 落地當下即有五支落在帶內（餘裕 0~2）——那正是 R76-16 要曝光的事實本身，不是雜訊；
# 現值一律現查 `python tools/check_loc_budget.py --json` 的 `special_warn_band`。
SPECIAL_WARN_MARGIN = 5

# 🔴 R84（ARCH-05）：`SPECIAL_FILES` raw-line 棘輪的**下界**咬人判準（阻塞）。
# 缺陷本體：這批門檻自陳「＝納管當下實際行數，只准往下改」，買到的東西是「再往裡塞就
# 會紅」——而 R84 逐鍵實測發現有列的門檻**遠高於現值**（`../.claude/hooks/
# context_budget_guard.py` cap 1451 / raw 1089 ⇒ 陳舊餘裕 **362 行**），也就是那 362 行
# 可以無聲地長回去而**沒有任何訊號**。上界（`SPECIAL_WARN_MARGIN`）與破線段都看不到這一側：
# 它們量的是「快滿了」，這一格量的是「門檻自己過期了」。
#
# 體例照 repo 既有的同型判例（`tools/tests/test_adr_xplat001_c1c2_lock.py` 的
# `_GUARD_LINE_STALE_SLACK` 雙邊帶，該檔逐字寫：「單邊棘輪只會腐化，縮下來卻不重釘的話，
# 餘裕就是日後無聲加回去的破口」）——那一族是淨行數、這一族是 raw line，兩個度量面，
# 故另立常數而不共用數字。
#
# 為什麼是 32（三個邊界各自可查，故這個數字不是載重件）：
#   ① **下界**：必須 > `SPECIAL_WARN_MARGIN`(5)，否則「快滿了」與「太鬆了」兩個帶相鄰／
#      重疊 ⇒ 每一列永遠落在其中一帶，常駐全亮的燈等於沒有燈。更硬的一條：
#      `tools/tests/test_check_defect_log_crossref.py::TestActionableMessagesHaveLocHeadroom`
#      要求「訊息教人加一筆的那些檔」餘裕 **≥ 5**（`_MIN_DIRECTIVE_HEADROOM`）⇒ K ≤ 5 會
#      讓那道鎖與本判準**互相矛盾而無法同時滿足**（實測那兩支現值 22／6，皆落在 5..32 內）。
#   ② **上界**：本輪實測，受本判準管的 7 列裡「例行縮小」那一群的陳舊餘裕是
#      1／2／6／18／22／25，真正陳舊的那一列是 **362**——兩群之間差一個量級（362 ≈ 11×32），
#      門檻落在空隙上而不是密集區 ⇒ 32 上下浮動不會改變任何一列的判定，不會製造邊界抖動。
#   ③ **方向鎖**：只准調小（收緊），由鎖檔 `assertLessEqual` 釘住；調大＝把「預先發放的
#      成長額度」再發回去，那正是本判準的立案理由。
# **為什麼是阻塞而不是預警**：這一族已經有一個非阻塞預警帶（上界那個），而 R84 之所以要
# 建這道鎖，就是因為「有訊號但沒人動作」在這一族已經是實況（那 362 行陳舊餘裕存在多輪、
# 每次 `--json` 都印得出來卻沒有任何東西會紅）。修法是**重釘為現值**（一行 diff），
# 不是調高——所以它擋得起。
SPECIAL_STALE_SLACK = 32

# ADR-SD08-001 §3.1：CLAUDE.md 文件治理（≤ 400 行強制）
# SPECIAL_FILES 採 raw line count（wc -l 等價，含空行/註解，因 CLAUDE.md 為 Markdown）
SPECIAL_FILES: dict[str, int] = {
    "CLAUDE.md": 400,  # ADR-SD08-001 §2.1：CLAUDE.md ≤ 400 + Snapshot SSOT
    # SD_09 Pre-W0 audit P0-06：補長文件預算（Migration SOP / Sprint history）
    "docs/08_deployment/Production_Migration_SOP.md": 800,
    "docs/05_development/sprint_history.md": 2000,
    # 🔴 R68：DEF-101-271／274 訂了「monorepo 根 tools/dev_start.py > 2000 行即升級為
    # 該輪必修」，但**從來沒有量測者**——實測該檔已自帳本三度記載的 1772 行漂到 1918
    # 行、距門檻僅 82 行且無人察覺（帳本同時還在寫「零成長／餘裕 228 行」）。本列即該
    # 門檻的機械量測者：路徑刻意以 `../` 越出 AutoClaude（唯一的 dev_start.py 在
    # monorepo 根 tools/，SCAN_ROOT="autoclaude" 掃不到它）。**棘輪：只准往下改**，
    # 要往上調必須在缺陷帳本具名理由（同 _FROZEN_GUARD_LINES 的重釘慣例）。
    # 現值不寫死在此（會過期）：`python tools/check_loc_budget.py --json` 現查。
    "../tools/dev_start.py": 2000,
    # 🔴 R69 P3：上一列（R68 落地）**只守 `dev_start.py` 一支**，而根層 `tools/` 是一整層
    # 逾兩萬行的護欄層。同一輪（R68）就有另外兩支在無人看守下大幅膨脹——
    # `check_defect_log_crossref.py` 漲到四位數行、`archive_defect_log.py` 亦然——證明
    # 「只釘一支」不是取捨而是缺口：守的是**檔名**，不是**那一層的成長**。
    # 本批把根層 tools/ 所有 700 行以上的 .py 全數納管，門檻一律取**納管當下的實際行數**
    # （不預留餘裕：預留多少都是憑空猜測，而 shrink-only 棘輪的價值就在「下一行就會響」）。
    # **棘輪：只准往下改。** 要往上調＝先刪死碼／抽共用模組（先例：R68 把 CI 逐軌活性偵測
    # 抽到 `tools/lib/ci_liveness.py`），確認為不可壓縮的真實功能後才在缺陷帳本具名理由。
    # 各檔現值不寫死在此（會過期）：`python tools/check_loc_budget.py --json` 現查。
    "../tools/check_script_parity.py": 1618,
    "../tools/archive_defect_log.py": 1507,
    "../tools/check_defect_log_crossref.py": 1474,
    # 🔴 R70 具名調高 1451 → 1499（`DEF-101-756`／`DEF-101-757`，依本棘輪自訂的解鎖程序）：
    # 調高**前**已先走完「抽共用模組」那一步——基線三態語意（`unrecorded` 二義性根治）與
    # nightly 落地產物探針共約 180 行已抽到 `tools/lib/baseline_origin.py`（先例：
    # `tools/lib/ci_liveness.py`）。留在本檔的殘餘是**不可壓縮的接線**：三態判準要吃
    # `_SLOW_SPECS`／`platform_cell_index()` 這些只有本檔有的表格解析器，搬出去等於把
    # 解析器一起搬（那會製造第二份表格語意＝本檔一直在治的病）。
    "../tools/sync_onboarding_baselines.py": 1499,
    "../tools/run_root_unittests.py": 754,
    # 🔴 R81（Architect-B3）：`.claude/hooks/` 納入治理面（見 `ROOT_GUARD_ROOTS` 的 WHY）。
    # 這一支超過 tier 的 750，走與上面那批同一條路：門檻＝**納管當下的實際 raw 行數**、
    # 只准往下改。納管當下＝1,634（見下方 `ROOT_GUARD_ROOTS` 那段的立案量測）。
    # 🔴 R81 收尾包**下釘**：額度撞線判讀整個主題已搬進 `tools/lib/quota_limits.py`，
    # 該檔實測降到 1,451 ⇒ 依本表「合法縮小後必須同步下修」的紀律把門檻跟著往下走。
    # 不下修的話那 183 行餘裕就是日後無聲加回去的破口（零餘裕是本棘輪的設計，不是意外）。
    # 🔴 R84（ARCH-05）**再下釘 1451 → 1089**（當回合實測 raw＝1089，直接填入、零加減推算）：
    # 上一行自己寫著「餘裕就是日後無聲加回去的破口」，而 R81~R83 之間該檔又縮了 362 行、
    # 門檻沒有跟著走 ⇒ 那句話在同一份檔案裡被自己違反了三輪，因為**沒有任何東西在量它**。
    # 本輪同時補上量測者（`SPECIAL_STALE_SLACK` ＋ `special_stale_reports()`，阻塞），
    # 所以這次的下釘不是靠下一個人記得。
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
# 根層 `tools/`**，而那是一整層兩萬行以上的護欄程式碼。R68／R69 P3 已察覺一半，處置是
# 把當時 ≥700 行的 6 支具名檔掛上 `SPECIAL_FILES` 的 raw-line 棘輪——但那是**一次性快照**：
#   ① 當時 <700 行、後來長大的檔完全無人看守。R75 實測 `tools/lib/windows_skip_tags.py`
#      在 R74 一輪內 +385 行、達 508 code／727 raw，**零訊號**（`tools/lib/` 整個目錄
#      先前一支都沒納管）。
#   ② 「守的是檔名，不是那一層的成長」——這正是 R69 P3 自己寫下的教訓，卻只修了一半。
#
# 本節把既有載具（`count_loc`／`FileReport`／`_matches_pattern`／同一套報表與 rc 收斂）
# 延伸到根層 `tools/`，**不另造第二套 LOC 檢查器**（那會重演「同一份知識兩個家」）。
#
# 三個判準決定，逐條寫下理由（免得下一輪把它讀成任意數字）：
#   · **預算沿用既有數字，不發明新的**：`guardrail_cli` ＝ `ABSOLUTE_LIMIT`(750)，即
#     ADR-SD07-001 的全域絕對紅線原封不動；`guardrail_lib` ＝ 400，取既有
#     `adapter`／`contract` tier 的值——`tools/lib/` 是**共用函式庫層**，與 adapter 同性質，
#     且一支超過 400 行的共用模組按定義已不只做一件事（`windows_skip_tags.py` 就是實例）。
#   · **`tools/tests/` 不納管**：與 AutoClaude 側 `SCAN_ROOT="autoclaude"`（不含
#     `AutoClaude/tests/`）**對稱**。這是政策一致，不是為了讓現況通過——根層測試樹
#     另有 `tools/tests/` 專屬的 E501 存量債棘輪，以及
#     `tools/tests/test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet` 的
#     **逐檔行數棘輪**（`_FROZEN_GUARD_LINES`，淨行數只准往下）在管。
#     🔴 **R78 ARCH-03 訂正**：本列原本把這層豁免的正當性掛在 R77 已刪除的那個**檔數**
#     棘輪常數上（全庫零定義）——也就是說一整層數萬行護欄碼的 LOC 豁免，有一段時間是
#     掛在一個**不存在的符號**上。接手者見上。此處刻意不逐字引述那個已死的常數名：
#     訂正註記引述假話等於製造新假話，而下一個人 grep 到它會以為那是現行說法。
#   · **已在 `SPECIAL_FILES` 的檔排除在 tier 檢查外**：同一支檔不受兩種度量（raw line
#     vs count_loc）雙重審判；那 5~6 支 1000 行級的護欄 CLI 沿用 R69 P3 立的 raw-line
#     棘輪即可。反過來說，**沒被 `SPECIAL_FILES` 收錄又超過 tier 預算的檔一律紅** ⇒
#     這道機制會自己補完收錄面（要嘛瘦身、要嘛具名入表附理由），不再是一次性快照。
ROOT_TOOLS_ROOT = PROJECT_ROOT.parent / "tools"
#: 🔴 R81（Architect-B3）：`.claude/hooks/` 也是 monorepo 根層護欄層，卻**不在任何 LOC
#: 治理面內**——`SCAN_ROOT = "autoclaude"` 掃不到它，`ROOT_TOOLS_ROOT` 只有 `tools/`，
#: 而且**沒有任何一行明文豁免**（⇒ 這不是取捨，是缺口）。代價是量出來的：納管當下
#: `context_budget_guard.py` ＝ 1,634 raw 行，是絕對紅線 750 的 **2.18 倍**；而 R81 那一輪
#: +421 行全部灌進這一支，同一套 LOC 政策卻正是該輪**新開兩支檔**的立案理由
#: ⇒ **壓力只作用在已經被量的那一層**，於是新檔被推出去、真正在長的巨檔繼續長。
#: 🔴 **誠實：納管當下不會讓任何東西變小。** 門檻取納管當下的實際行數（見 `SPECIAL_FILES`
#: 那一列），買到的是「下一個人再往裡面塞就會紅」。這不是減法，別包裝成減法；把那 1,634
#: 行拆開是另一件事，本輪未做。
ROOT_GUARD_ROOTS: tuple[Path, ...] = (
    ROOT_TOOLS_ROOT, PROJECT_ROOT.parent / ".claude" / "hooks")
#: 🔴 R84（ARCH-04）：`guardrail_lib` 把 `tools/lib/` **整層**當成同一種東西，而那一層裡
#: 有兩種形狀：**leaf helper**（只被人叫、自己幾乎不叫別人）與 **hub**（把同族的 leaf 組起來
#: 對外只露一個決策面）。R84 實測 `tools/lib/quota_gate.py` ＝ `count_loc` **400／budget 400
#: ／餘裕 0**，而它 fan-out 到 **5 支**同層 lib（`quota_ledger`／`quota_limits`／`quota_meter`
#: ／`quota_policy`／`schedule_backend`），對外 production 消費者只有 1 支
#: （`.claude/hooks/context_budget_guard.py`）⇒ 這是**分類錯誤**，不是「該檔太胖」：
#: 一支組合 5 個下游的合成面，天生比 leaf helper 需要更多接線行，而
#: `guardrail_lib=400` 的立案理由逐字寫的是「一支超過 400 行的**共用模組**按定義已不只
#: 做一件事」——那句話對 leaf 成立，對合成面不成立（它做的**就是**「把 5 件事接起來」）。
#:
#: 三個判準，逐條寫下理由（免得下一輪把它讀成「開了一個誰都能進的後門」）：
#:   · **預算不發明新數字，且刻意取 `service`(500) 而不是 `ABSOLUTE_LIMIT`(750)**：
#:     hub 的語意就是 ADR-SD07-001 `service` tier（「把下游組起來的協調面」），直接**引用**
#:     那一格的值而非複寫字面，改 SSOT 會同步跟著動。取 750 的話 `guardrail_hub` 與
#:     `guardrail_cli` 逐字同值 ⇒ **一個等於絕對紅線的 tier 不是 tier**，等於只剩絕對紅線
#:     在守；本輪刻意選最小的放寬幅度（+100 行），真的還不夠時的下一步是既有的合法出口
#:     （拆職責／抽共用模組，不可壓縮才具名進 `SPECIAL_FILES` 的 raw-line 棘輪），不是再調高本格。
#:   · **patterns 只收明文列舉的單檔，不得用寬 glob**：`tools/lib/*_gate.py` 這種寫法會讓
#:     下一支取同樣名字的檔自動繼承 +100 行，而那正是「後門」的形狀。
#:   · **代價：成員清單只准縮不准長，且每一支成員都要能被機械驗證是 hub**。
#:     `ROOT_TOOLS_HUB_MEMBER_CAP`（成員數上界，只准調小）＋
#:     `ROOT_TOOLS_HUB_MIN_FANOUT`（fan-out 下界）＋逐支 `override_reason`
#:     由 `AutoClaude/tests/tools/test_check_loc_budget_hub_tier_and_special_stale.py` 釘住：
#:     成員數變多、成員不存在、成員 fan-out 不足、預算不是既有數字、pattern 出現 glob，
#:     任一項即紅。**「是不是 hub」由 AST 現查 fan-out 決定，不是靠自稱。**
#:
#: 🔴 誠實劃界（R84 現查，免得下一輪誤以為本格解了整層的問題）：同族 `skip_*` 六支裡
#: **沒有一支**符合本格判準——`skip_group_policy.py` 實測 399／400（餘裕 1）但 fan-out 只有
#: **1**（`skip_tag_policy`），它是被 3 個消費者叫的政策 leaf，不是合成面；該族真正的 hub 是
#: `windows_skip_tags.py`（fan-out 4，實測 356／400 餘裕 44，**不需要**本格的放寬，故刻意
#: 不收進成員清單——收一支不需要的進來只會稀釋這個 tier 的語意）。⇒ `skip_group_policy`
#: 貼牆這件事**本格沒有解**，它的正解仍是既有那條路（六支收斂成三支），見缺陷帳本 ARCH-09。
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
    "guardrail_cli": {"budget": ABSOLUTE_LIMIT, "patterns": ["tools/", ".claude/hooks/"]},
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


def count_loc(path: Path) -> int:
    """計算實際程式碼行數（排除空行與純註解行）。"""
    if not path.exists():
        return 0
    n = 0
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            n += 1
    return n


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


def iter_source_files() -> Iterable[Path]:
    for p in (PROJECT_ROOT / SCAN_ROOT).rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


def iter_root_tools_files() -> Iterable[Path]:
    """monorepo 根層護欄層納管的 `.py`：`tools/` ＋ `.claude/hooks/`（見 `ROOT_GUARD_ROOTS`）。

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


def check(update_baseline: bool = False, as_json: bool = False) -> int:
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
        baseline = total
        print(f"[baseline] 已寫入 .loc_baseline = {total}")
    cap = int(baseline * TOTAL_INCREASE_LIMIT)
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
            "policy_version": "v2-tiered+sd08-special",
            "absolute_limit": ABSOLUTE_LIMIT,
            "special_files": SPECIAL_FILES,
        }
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
                f"baseline({baseline}) x {TOTAL_INCREASE_LIMIT} = {cap}"
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
                "\n       說明文字請寫成 `#` 註解而非 docstring——docstring 行會被 "
                "count_loc 計入，寫進 docstring 等於再吃掉預算。"
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
    as_json = "--json" in sys.argv
    return check(update_baseline=update, as_json=as_json)


if __name__ == "__main__":
    sys.exit(main())
