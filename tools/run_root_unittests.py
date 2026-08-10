#!/usr/bin/env python3
"""tools/tests 全套 unittest 執行器（含測試數量下限釘選）— R10 QA-2（DEF-101-127）。

為何存在：`python -m unittest discover` 對「發現 0 個測試」回 rc=0
（`Ran 0 tests ... OK`，Python 3.11 實測）。tools/tests/ 目錄改名、測試檔改名
不符 `test_*.py`、或 `-s` 路徑打錯 → 全部回歸鎖同時靜默消失，而四處 gate
（pre-push root-infra leg、root-infra-ci step 8、windows/macos smoke）依然全綠、
無任何 diff 訊號。R9 已給 parity 抽取加 `_MIN_EXTRACT_COUNTS` 下限釘選，同構
風險在 unittest 這裡原本沒有對等防護。

行為：discover 後先斷言 countTestCases() >= MIN_TESTS 再執行；低於下限 exit 1
（測試根本不跑——數量崩塌本身就是失敗）。刻意刪減測試時須同步下修 MIN_TESTS
（比照 check_script_parity._MIN_EXTRACT_COUNTS 的紅燈指路慣例）。

R60 Pkg-P8 補三層——因為「下限」語意只擋得住「掉太多」，擋不住「悄悄少幾支而總數
仍在下限之上」（實測當時 916 支 vs 下限 845 ⇒ 可靜默蒸發 71 支仍印 ✅）：
  ① `inventory_fingerprint`：把「這個數字是哪一份磁碟狀態產生的」一起印出來，
     讓兩次數字不同時能當場分辨「樹變了」還是「同一棵樹量到不同數字」。
  ② `collection_gaps`：斷言磁碟上每支 test_*.py 都至少貢獻一支測試（集合比對，
     不是總數比大小），並把 discovery 佔位測試（`_FailedTest`／`ModuleSkipped`）
     點名成硬失敗——後者原本 rc 仍為 0，是真的 fail-open。
  ③ `report_execution_gap`：比較**收集數**與**實際執行數**。`setUpClass` 拋
     SkipTest 會讓整個類別一支都不跑而 `countTestCases()` 完全不變，下限守門
     結構性看不到（實測：收集 11／執行 2／rc=0）。

R68 補第四層 `_THIRD_PARTY_PREREQS`——前三層都預設「環境是完整的」，而三個 CI 平台
上的實況正是環境**不**完整：缺第三方相依 ⇒ 模組 import 失敗 ⇒ 整份覆蓋塌成一支
`_FailedTest` 佔位測試 ⇒ 收集數低於下限，而下限失敗訊息卻只會說「測試疑似大規模
靜默消失（目錄改名/pattern 不符/路徑錯）」，把讀者指往三條全錯的路。詳見該常數。

呼叫端（取代裸 `python -m unittest discover -s tools/tests`）：
  tools/git-hooks/pre-push（root-infra leg ②）、.github/workflows/root-infra-ci.yml
  step 8、windows-compat-ci.yml、macos-compat-ci.yml 對應 step。

使用：python tools/run_root_unittests.py（repo 內任意 cwd；路徑以本檔自身定位）
CLI 契約：**零旗標**——任何引數一律 rc=2 fail-loud（見 `cli()` 的 WHY）。
測試：tools/tests/test_run_root_unittests.py（未知引數那一層在
      tools/tests/test_check_wrapper_thinness.py 的 `TestRootGateToolsRejectUnknownFlags`）
"""
from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cli_flags  # noqa: E402  # 未知旗標 rc=2 fail-loud 的 SSOT（見該檔檔頭 WHY）
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

_TESTS_DIR = Path(__file__).resolve().parent / "tests"

# 下限釘選：低於此數＝測試大規模靜默消失（目錄/pattern/路徑壞掉），紅燈。
# 刻意刪減測試時同步下修；新增測試在 `RATCHET_STALE_RATIO` 倍以內不需動（下限
# 語意），超過即**必須**重釘，否則保鮮期斷言會讓閘門變紅（見下方兩層設計說明）。
MIN_TESTS = 3095  # 🔴 **R83 收輪二次重釘（舵手親自，於全部 13 個 workflow 停工後的單人窗口實跑本 runner，取其印出的計數直接填入、零加減推算）**：前一次 R83 值 3052 是本輪**中段**（四方複審之前）量的，其後四方複審 55 筆 findings 的收斂波（W10~W12）與 mac 喚醒鏈 P0（W11）又淨增測試 ⇒ 3052 對收輪實況的鑑別力已衰減。**方向是收緊**（下限往上釘＝讓「靜默蒸發若干支測試仍然全綠」的窗口變小）。🔴 **本輪這一次終於滿足了本行自己的判準的大半**：四方複審**已執行**（Architect／SA／SD／QA 全數 APPROVE_WITH_CONDITIONS、無人 REJECT），其 blocking 由 W10~W12 逐筆收斂 ⇒ 本值不再是 R74／R77／R78／R81／R82 那種「複審根本沒跑」的中途值。**仍未滿足的那一半照實寫**：複審後的收斂包（W10~W12）與本次重釘**沒有再被第三方看過** ⇒ 依成熟度判準 M3「作者自證不計分」，那一段仍是自證。**同步站點**：`ONBOARDING.md` §7 表① 的 `rootunit-baseline-live:` 格與本常數由 `test_root_unittest_cell_agrees_with_min_tests_ssot` 綁死，本次以 `python tools/sync_onboarding_baselines.py --write` 在**同一次變更內**回填。前值 3052 為 R83 中段值。以下為 R83 中段沿革：🔴 **R83（mac 真機首輪）收尾重釘（舵手親自，於全部 agent 停工後的單人窗口實跑本 runner，取其印出的計數直接填入、零加減推算）**：量測前後各取一次含內容的工作樹指紋並確認相同。🔴 **本次重釘的觸發與 R82 那次逐字同型，且本行下方 R74／R69 的預告再次應驗**：`tools/tests/test_run_root_unittests.py::ZeroDepEnvironmentDiscriminationTest::test_zero_dep_message_says_environment_not_disappearance` 當回合 FAIL，訊息逐字是「`環境問題` not found in `❌ discovery 佔位測試 4 筆…`」——舊下限已低於零相依沙箱的收集數，於是走「下限通過」那一支、印佔位測試清單並把整棵樹再跑一次，而不是走 `report_floor_failure` 印出環境歸因。⇒ 這支鎖量的是「本下限對零相依環境還有沒有鑑別力」，它一紅就代表下限舊到讓自己的看守者失效。**方向是收緊**（下限往上釘＝讓「靜默蒸發若干支測試仍然全綠」的窗口變小），與「不准為了讓數字好看而調高門檻」那條禁令方向相反。🔴 **本值依本行自己的判準屬中途值，照實記**：本行明訂「真正的解法是把重釘綁到四方複審全數 APPROVE 之後」，而**四方複審在本值落地時尚未執行**——配額五小時桶觸及收斂帶，依 `quota_policy` 的節流演算法延到 reset 後（外部資源限制，不是疏漏）⇒ 依成熟度判準 M3「作者自證不計分」，本值與 R74／R77／R78／R81／R82 那幾次同型，複審收斂後必須再釘一次。🔴 **本輪另記一筆與本行相關的實測**：本輪成長主要來自 mac 真機第一次看得見的判準（逐檔清單見 `docs/06_quality/CrossPlatform_R83_Scan_Findings.md` §B），其中三支新鎖檔曾有 3 個類別繼承本地共用夾具而非直接繼承 `TestCase`，被 `test_schedule_capability_parity` 判為「unittest 不收」——實測那三類**其實收得到**（貢獻 16 支真的在跑的測試），故該判準本輪已補上「同檔內基底鏈解析」以消掉那個假陽性；若當時照假紅去攤平類別階層，會換來三份手抄夾具。**同步站點**：`ONBOARDING.md` §7 表① 的 `rootunit-baseline-live:` 格與本常數由 `test_root_unittest_cell_agrees_with_min_tests_ssot` 綁死，本次以 `python tools/sync_onboarding_baselines.py --write` 在**同一次變更內**回填。前值 2795 為 R82 值。以下為 R82 沿革：🔴 **R82 收尾重釘（本輪最後一個修復者親自，取 runner 當場印出的計數直接填入、零加減推算）**：量測於本輪所有並行包停工後的**單人窗口**內取得——本包動工到量測之間沒有其他 agent 在改樹，且本包自己的改動只碰註解／散文與本常數，不新增也不刪除任何測試（收集面盤存的檔數與指紋在改動前後相同，值本身不寫在這裡，見本 runner 當場輸出）。🔴 **本次重釘不是例行保養，是為了修一支已經在紅的鎖**：`tools/tests/test_run_root_unittests.py::ZeroDepEnvironmentDiscriminationTest::test_zero_dep_message_says_environment_not_disappearance` 當回合 FAIL——舊下限已經**低於零相依沙箱的收集數**（宣告相依被擋掉時只有 4 支模組塌成佔位測試，其餘照收），於是 `run_with_floor` 走的是「下限通過」那一支、印出 discovery 佔位測試的清單並**把整棵樹再跑一次**，而不是走 `report_floor_failure` 印出「環境問題」的歸因。⇒ 這支鎖量的其實是「本下限對零相依環境還有沒有鑑別力」，它一紅就代表下限已經舊到讓自己的看守者失效。🔴 **方向與連鎖代價的釐清（免得下一輪誤讀本行下方 R74／R69 的警語而不敢重釘）**：那兩段警語講的失效模式正是**下限太舊**——探針不再提前判紅、改為實跑整棵樹，牆鐘因此暴衝甚至撞逾時。把下限往上釘＝**收緊**，恰好把那條放大路徑關掉，**不是**觸發它；本次重釘後零相依探針在下限層即判紅，不再進入整棵樹的執行面。與「不准為了讓數字好看而調高門檻／棘輪」那條禁令方向相反——那條禁的是**放寬**。🔴 **本值依本行自己的判準仍屬中途值，照實記**：本行明訂「真正的解法是把重釘綁到四方複審全數 APPROVE 之後」，而**針對本包這幾筆修復的第三方複審並未執行**（本包在額度節流下不派任何子 agent）⇒ 依成熟度判準 M3「作者自證不計分」，本值與 R74／R77／R78／R81 那幾次同型，下一輪複審收斂後必須再釘一次。**同步站點**：`ONBOARDING.md` §7 表① 的 `rootunit-baseline-live:` 格與本常數由 `test_root_unittest_cell_agrees_with_min_tests_ssot` 綁死，本次以 `python tools/sync_onboarding_baselines.py --write` 在**同一次變更內**回填。前值 2574 為 R81 值。以下為 R81 沿革：🔴 **R81 收尾重釘（收尾者親自，取 runner 當場印出的計數直接填入、零加減推算）**：量測在 11 個並行包全部停工後的**單人窗口**內取得，量測前後工作樹未再變動。🔴 **本次另加一項前幾輪沒做的交叉驗證**：同一棵樹分別以本機 `.venv`（裝了 PG extras 與 sdk extra）與**出廠乾淨 venv**（兩者皆無、與 ONBOARDING §7 表② Windows 欄同一支直譯器）各跑一次，兩邊收集數**相同**且皆 rc=0 ⇒ 這個下限不是某一種環境的偶然值。做這件事的理由是本行下方已記載的失效模式：下限一旦低於**零相依環境**的收集數，零相依探針就不再提前判紅而是實跑整棵樹並撞逾時（`DEF-101-803`）——只在裝滿 extras 的環境量一次，恰好看不見那個環境。🔴 **方向是收緊、不是放寬**（本常數是下限，往上釘＝讓「靜默蒸發若干支測試仍然全綠」的窗口變小），與「不准為了讓數字好看而調高門檻／棘輪」那條禁令方向相反。🔴 **本值依本行自己的判準仍屬中途值，照實記**：本行明訂「真正的解法是把重釘綁到四方複審全數 APPROVE 之後」，而 R81 的四方複審**尚未執行** ⇒ 依成熟度判準 M3「作者自證不計分」，本輪 11 包與本收尾包的改動全屬作者自證，下一輪複審收斂後必須再釘一次（承接載體＝帳本 `DEF-101-876`，輪號寫在帳本那一列、不寫在本行）。**同步站點**：`ONBOARDING.md` §7 表① 的 `rootunit-baseline-live:` 格與本常數由 `test_root_unittest_cell_agrees_with_min_tests_ssot` 綁死，本次以 `python tools/sync_onboarding_baselines.py --write` 在**同一次變更內**回填。前值 2466 為 R80 值。以下為 R80 沿革：🔴 **R80 收尾重釘（收尾包親自，取 runner 當場印出的計數直接填入、零加減推算）**：本值在 R80 push 前的**單人窗口**內量得——量測時無任何並行 agent，量測前後工作樹未再變動。🔴 **方向是收緊、不是放寬**：本常數是**下限**，往上釘＝讓「靜默蒸發若干支測試仍然全綠」的窗口變小；前值對當時實況的鑑別力已明顯衰減（差額就是可靜默蒸發的支數，runner 每次執行都會把當下的兩個值印在終端，故此處不寫死）。與「不准為了讓數字好看而調高門檻／棘輪」那條禁令**方向相反**——那條禁的是**放寬**。🔴 **本行自己的判準仍有一半未滿足，照實記**：R80 四方複審跑了兩審、blocking 全收斂，但二審收斂包與本收尾包其後落地的改動**沒有再被第三方看過**（含本包為解開 ONBOARDING §7 表② 回填所修掉的 ci-gate 真紅：五支 `tools/lib/` 共用層未列入三支 workflow 的 paths，被 `test_ci_paths_cover_root_consumers.py` 當場攔下）⇒ 依成熟度判準 M3「作者自證不計分」，那一段仍是自證。**同步站點**：`ONBOARDING.md` §7 表① 的 `rootunit-baseline-live:` 格與本常數由 `test_root_unittest_cell_agrees_with_min_tests_ssot` 綁死，本次以 `python tools/sync_onboarding_baselines.py --write` 在**同一次變更內**回填。前值 2341 為 R79 值。以下為 R79 沿革：🔴 **R79 複審後重釘（複審後修復包親自，取 runner 當場印出的計數直接填入、零加減推算）**：重釘在四個複審後修復包全部停工後的**單人窗口**內執行——沿用 R78 已取證的機械事實：多包共用一棵工作樹時本 runner 的 rc 是「別人鍵盤的函數」，故量測窗口必須是單人的。🔴 **本行的判準第一次真的被滿足，但只滿足了大半，照實記**：本行明訂「真正的解法是把重釘綁到四方複審全數 APPROVE 之後」——R79 的四方（Architect／SA／SD／QA）**已跑，且四方全部 APPROVE_WITH_CONDITIONS**，其 blocking 條件由複審後修復包逐筆收斂，故本值不再是 R74／R77／R78／R79 前次那種「複審根本沒跑」的中途值。**仍未滿足的那一半照實寫**：複審審的是**被送審的那批修復**，而為了收斂那些條件在其後新落地的判準（含本包自己的改動）**沒有再被第三方看過** ⇒ 依成熟度判準 M3「作者自證不計分」，那一段仍是自證，其強度上限是「作者自己跑的注入紅綠」。🔴 **方向說明（免得下輪誤讀）**：本常數是**下限**，往上釘＝**收緊**（讓「靜默蒸發若干支測試仍然全綠」的窗口變小），與「不准為了讓數字好看而調高門檻／棘輪」那條禁令方向相反——那條禁的是**放寬**。前值 2284 為 R79 複審**前**的中途值、2201 為 R78 中途值。以下為 R78 沿革：🔴 **R78 收尾重釘（收尾者親自，取 runner 當場印出的計數直接填入、零加減推算）**：重釘在所有修復包與所有獨立 agent 停工後的窗口內執行，量測前後各取一次含內容的工作樹指紋（`git status --porcelain` ＋ `git diff HEAD`）並確認相同。🔴 **本值依本行自己的判準仍屬中途值，照實記**：本行明訂「真正的解法是把重釘綁到四方複審全數 APPROVE 之後」，而 R78 的四方複審審的是**上一輪 R77**（30 findings／9 blocking，逐筆見 `docs/06_quality/CrossPlatform_R78_Review.md`）——**針對本輪五個修復包本身的第三方複審並未執行** ⇒ 依成熟度判準 M3「作者自證不計分」，本值與 R74／R77 那兩次同型，下一輪對本輪修復複審收斂後必須再釘一次。🔴 **R78 另記一筆本行未涵蓋的失效面**：本輪實測到「多 agent 共用單一工作樹」會讓本 runner 的 rc 成為**別人鍵盤的函數**（同指令相隔數分鐘一紅一綠，成因見 `DEF-101-886`）⇒ 本行要求的「量測窗口前後工作樹指紋相同」在該作業型態下**結構上不成立**，本輪的處置是紀律（收輪閘門一律在所有 agent 停工後取得）而非機械物，缺口仍在。前值 2105 為 R77 中途值。以下為 R77 沿革：**本輪收尾重釘（收尾者親自）**：所有修復包停工後於最終工作樹實跑本 runner，取其印出的計數直接填入、零加減推算；量測窗口前後各取一次含內容的工作樹指紋並確認相同。🔴 **本值的取得條件有一項未滿足，照實記**：重釘時修復包確已停工，但**四方複審本輪未執行**——被月度支出上限擋住 agent 派工（外部資源限制，不是疏漏也不是判斷失誤），而本行判準明訂「真正的解法是把重釘綁到四方複審全數 APPROVE 之後」⇒ **本值依本行自己的判準屬中途值**，下一輪四方複審收斂後必須再釘一次。這與 R74 那次同型（該次亦因額度而未跑複審），逐字記錄以免下輪誤認為新發現。前值 1979 為 R76 值。以下為 R76 沿革：（R76 收尾包重釘，該輪四方複審已全跑並收斂 ⇒ 該值不再是 R74 那種「中途值」）：由收尾包在所有修復包與四方複審 agent 全部停工後，於最終工作樹實跑本 runner、取其印出的計數**直接填入、零加減推算**；量測窗口前後各取一次**含內容**的工作樹指紋並確認相同（`git status --porcelain` ＋ `git diff HEAD` ＋ untracked 檔內容雜湊）。🔴 **方向說明（免得下一輪誤以為這是「調高門檻」）**：本常數是**下限**，往上釘＝**收緊**——它讓「靜默蒸發 N 支測試仍然全綠」的窗口變小，與「不准為了讓數字好看而調高門檻／棘輪」那條禁令方向相反（那條禁的是**放寬**）；真正「只准變小」的是 shrink-only 棘輪那一族（`SPECIAL_FILES` raw-line 上限），兩者不是同一種東西，別混為一談。🔴 **不重釘的代價不只是鑑別力衰減**：本值同時是零相依探針的**鑑別門檻**，一旦低於零相依環境的收集數，探針就不再提前判紅而是實跑整棵樹並撞逾時（`DEF-101-803` 實測事故），所以「維持現狀」在這裡**不是中立選項**。🔴 **仍未機械化的那一半，照實記**：指紋比對只能證明「量測期間沒有人在動樹」，證明不了「之後不會再有一波」——後者由「四方複審已收斂 ＋ 本包是本輪最後一個工作者」承擔，**零機械物看守**（＝`DEF-101-701` 所述結構衝突仍未解）。前值 1819 為 R74 中途值。以下為 R74 沿革：R74 **收尾者於最終工作樹重釘，取 runner 當場印出的計數直接填入、未做任何加減推算**（🔴 **本次重釘的觸發正是本行下方 R69 已逐字預告過的失效模式**：陳舊下限低於零相依環境的收集數 ⇒ 零相依探針不再提前判紅而是實跑整棵樹，兩支測試由秒級轉為撞逾時；本輪實測到的是它的**第二形態**——探針還會遞迴 spawn 孫探針，見 `DEF-101-803`。⇒ 該段預告在本輪應驗，此處逐字回指以免下一輪又當成新發現。🔴 **本值的取得條件有一項未滿足，照實記**：重釘時所有修復包確已停工，但**四方複審本輪未執行**（`DEF-101-801`），而本行判準明訂「真正的解法是把重釘綁到四方複審全數 APPROVE 之後」⇒ **本值依本行自己的判準屬中途值**，下一輪四方複審收斂後必須再釘一次（承接載體＝`DEF-101-801`，輪號寫在帳本那一列、不寫在本行——本行寫死未來輪號會被輪號鎖判紅，本輪實際踩過一次）。前值 1663 為 R71 值）。以下為 R71 沿革：**收官前最後一包停工後重釘（該值＝R71 最終值：四方複審 R1 18 筆→R2 6 筆全數修畢、收官聚焦複審抓出的第三代缺陷 2 筆亦修畢、環境相依紅燈 DEF-101-618(a) 殘留修畢之後才量；量測前後各取一次含內容的工作樹指紋並確認相同）**（🔴 **前綴自己就復發過兩次，逐字記錄**：本前綴在 R69 第二次重釘時仍寫著 R67 的說法、被四方終審 R3 點名為「值是 R69、標籤寫 R67」；訂正後又在第三次重釘時寫成「第三波修復後」而內文已是第四波，被終審 R4 再度點名。**同一行同時裝「值」與「這個值是哪一波量的」兩件會各自變動的事，就是本註記通篇在治的那個病的最小實例**——真正的解是把波次沿革移出本行，本輪未做，見 `DEF-101-701`。**前綴沿革**：本行在 R67 round 3 曾釘 1362 並在此寫「本輪第三次；動工前為 R60 round 3 釘的 1069」，R69 兩度重釘時未同步改寫這個前綴，被四方終審點名為「值是 R69 的、標籤卻寫 R67」的自我矛盾——同一行同時裝兩輪的說法，正是本註記通篇在治的病，故就地訂正）。🔴 **「一輪三釘」本身是本 repo 的結構性缺陷，逐字記錄比修好它更要緊（`DEF-101-701`）**：本輪序列＝1069 → round 1 釘 1318 → round 2 釘 1343 → round 3 本次。1318 那次的取證被四方三向交叉命中為不實（SA-R67-02／SD-R67-01／QA-R67-01：註記寫死的收集面指紋與兩處計數，在最終工作樹一個都複現不出來；同一 commit 內 DEF-101-677 自己記的又是第三個數字，正是 R60 SA-R60-01／ARCH-R60-03 判過的「同一份 repo 對同一個數字兩種說法」原型復發）。1343 那次同樣逐字宣稱「全部修復包停工後」，其後 SC 鎖包（`DEF-101-699`）又淨增測試 ⇒ 同一句話**再度**在一天內轉假。**根因不是粗心，是兩條規則的結構衝突**：重釘判準要「取當下實測」，而本 repo 的收輪是**多波次**（修復包 → 四方複審 → 再一波修復包 → 收尾包），任何一包寫下「已停工」時都只對**當下**為真；round 2 為此加訂的 (a) 仍靠**人自己判斷自己是不是最後一個**，零機械物看守 ⇒ 同型復發已可列舉：R60 留下 756／845／994／1063 四個中途值，R67 留下 1318／1343。**故 R67 round 2 加訂、round 3 沿用並補一小步**：(a) 重釘必須發生在**最後一波**修復收斂之後、由當輪唯一仍在工作的包執行，且該包必須先實查工作樹已停止變動——round 3 的實查手法＝**重釘量測前後各取一次工作樹內容指紋並確認相同**，指紋須**含內容**——`{ git status --porcelain; git diff HEAD; git ls-files -o --exclude-standard -z | xargs -0 shasum; } | shasum`；🔴 **只雜湊 `git status --porcelain` 是不夠的**（本包第一版就是這樣寫的，當場自查抓到）：該輸出只有狀態字母與路徑、**不含內容**，於是「對一支已在清單內的檔再改一次」對它完全不可見，正是本檔多處在治的 fail-open。這是唯一被機械化的一小步；「誰是最後一個工作者」本身仍無判準，未修的那一半見 `DEF-101-701`；(b) 🔴 **本註記內一律不得寫死「當場即可現查」的量測 token**（收集面指紋、`Ran <數字> tests`、`發現 <數字> 個測試`）——本 runner 每次執行都會把當下的值印在終端，寫進註記等於憑空製造一個沒有任何機械物看守的 stale 站點（同 `ADR-XPLAT-002` §8 表頭規則 3「完成判準欄禁止寫死量測常數」）。(b) 已由 `min_tests_note_stale_tokens()` 機械強制：違反即 rc=1，訊息直接指路。本值＝在 R69 收輪 push **成功後、雲端 windows-compat-ci 抓到 WSL bash 劫持（`DEF-101-753`）的修復包**停工後，由收尾者於最終工作樹實跑（🔴 **1588 那次的教訓再進一階**：pre-push 阻斷事件補上了 untracked 盲區之後，push 成功、本機十道閘門全綠、四方四輪複審全過——然後**雲端真 Windows runner** 抓到一支本機結構上不可能重現的紅：裸名 `bash` 在 Windows 上因 `CreateProcess` 把 System32 排在 PATH 之前而必定命中 WSL 啟動器。⇒ 「本機全綠」與「掃描面無盲區」都還不夠，**「只在某平台才成立」的判斷必須有本機可重現該平台語意的回歸路徑**，否則唯一的發現通道就是雲端真機）（🔴 **1581 那次的教訓比前幾次都重要**：當時四方終審 R4 已判 0 筆擋收輪，收尾者據此宣稱「不會再有下一波」這件事**首次有外部憑證**——結果 `git add` 的那一刻就冒出一道真紅。原因不是四方失職，而是那道鎖的掃描面用 `git ls-files`、對 untracked 檔天然隱形，而本輪新增的 `AutoClaude/autoclaude/utils/platform_caps.py` 全程未被 add ⇒ **四輪四方複審與收尾者歷次全套實跑，全都在一個看不見該檔的掃描面上取得「全綠」**。`DEF-101-751`／`DEF-101-752`。⇒ 「不會再有下一波」連外部憑證都還不夠，還要求**該憑證的取得面本身沒有盲區**） `python tools/run_root_unittests.py`，取其印出的計數直接填入，未做任何加減推算；重釘前後各取一次含內容的工作樹指紋並確認相同。🔴 **R69 本身貢獻了兩個中途值 1526 與 1557，逐字記錄**：收尾者在「修復波九包停工後」釘了 1526 並逐字寫下「九包全部停工後」——其後四方複審 R2 判出 12 筆確認發現，觸發第三波修復五包再度淨增測試，該句在同一輪內轉假；收尾者接著在「第三波五包停工後」釘了 1557 並寫下同型句子，其後四方**終審 R3** 又判出兩筆擋收輪 P1，觸發第四波修復四包，**同一句話在同一輪內第二次轉假**。這是 `DEF-101-701` 所述結構衝突的**第三次**實例（R60 留下 756／845／994／1063，R67 留下 1318／1343，R69 留下 1526／1557／1580／1581／1588，R70 留下 1592／1594），根因不變：判準要「取當下實測」，而收輪是**多波次且波數事前未知**（修復波 → 四方複審 → 再修復波 → …），任何一包寫下「已停工」時都只對當下為真。工作樹指紋實查只能證明「量測前後沒人在動」，**證明不了「之後不會再有一波」**——後者要等四方複審判 APPROVE 才成立，故真正的解法是把重釘綁到**四方複審全數 APPROVE 之後**而非「修復包停工後」。🔴 **R69 新增的第三個失效證據（本輪實際事故，比前兩次更嚴重）**：R67 釘的 1362 落後測試樹後，並非只是「鑑別力衰減」這種慢性病——`tools/tests/test_run_root_unittests.py::ZeroDepEnvironmentDiscriminationTest` 的零相依探針以 `run_with_floor` 判紅，下限一旦低於零相依環境的收集數，探針就不再提前判紅而是**實跑整棵樹**，於是那兩支測試由秒級轉為撞 300s `TimeoutExpired` ⇒ **陳舊的下限會讓看守它的那道鎖自己壞掉**（R69 實測：全套耗時由分鐘級膨脹到十二分鐘級並 rc=1）。換言之 `MIN_TESTS` 不只是下限，它同時是零相依探針的**鑑別門檻**，兩個角色共用一個常數＝本檔尚未修掉的耦合，見 `DEF-101-701`。歷史值序列：R15 為 290、R57 為 616、R59 為 661、R60 round 3 為 1069、R67 round 1 為 1318、R67 round 2 為 1343（後兩者皆中途值，見上）、R67 round 3 為 1362、R69 修復波後為 1526、R69 第三波後為 1557、R69 第四波後為 1580、R69 收輪前最後一包後為 1581、R69 push 阻斷修復後為 1588、R70 WSL bash 劫持修復後為 1592、R70 stub 可執行性修復後為 1594（七者皆中途值，見上）；R60 中途曾釘 756、845、994、1063——994 是 round 3 修復波開跑前的值，1063 是 Pkg-F 交件時的值而 Pkg-H 之後又淨增 6 支，兩者都在「還有包在跑」的時點量測，故皆非最終值。R58 整輪作廢故無 R58 值；R57 收尾重釘時，動工前的 R15 值 290 對當時實況 530 已鑑別力失效 45%＝可靜默蒸發 240 支仍綠——與本輪同款腐化，故重釘節奏訂為「每輪收尾必做」。**重釘判準（R57 訂立，R67 round 2 補上 (a)(b)，round 3 補上工作樹指紋實查）**：本值一律由收尾者在**所有並行修復包與四方複審 agent 全部停工後**，於最終工作樹實跑 `python tools/run_root_unittests.py`，取其印出的計數直接填入，不做任何加減推算——R57 過程中兩度用算式推得 552／558，兩次都當場就與實況不符（SD-R57-01／QA-R57-07 抓出），故本行的重釘判準明定為「填實測值」

# R57 修正：「人工 ratchet」本身就是缺陷來源——R15 釘完後連續 11 輪沒人重釘，
# 下限與實況愈拉愈開、鑑別力單調衰減，而且**沒有任何訊號**提醒該重釘（下限語意
# 天生只在往下掉時說話）。故設**兩層**、且刻意用**不同**門檻：
#   ① WARN 層（本檔 `warn_ratchet_drift`，只印不擋）：實況 > 下限 × 1.10 即在
#      終端印一行「該重釘了」。這一層才是真正的「只 WARN 不 fail」。
#   ② 保鮮期層（`tools/tests/test_run_root_unittests.py::
#      test_current_pin_is_not_already_stale`，會讓閘門變紅）：實況 > 下限 ×
#      1.25 即 FAIL。純 WARN 擋不住「11 輪沒人重釘」的心理機制（常亮的警告＝
#      背景噪音），必須有一道會紅的線。
# 兩層門檻必須不同，否則 WARN 一響就等於閘門已紅，①的存在毫無意義——R57
# round 1（ARCH-06）實測 `ratchet_drift_message(698, 558)` 非 None ⇒ 當時單一
# 1.25 門檻下「只 WARN 不 fail」的註解與行為互相打臉。現行設計給的是 [1.10,
# 1.25] 這段緩衝：先被提醒、還沒被擋，收輪時順手重釘即可。
# 代價（明說）：累積新增超過 MIN_TESTS × 0.25 支測試就**必須**重釘，這是刻意
# 承受的維護負擔，換到的是下限不會再腐化 11 輪。
RATCHET_WARN_RATIO = 1.10
RATCHET_STALE_RATIO = 1.25

# `tools/tests/` 的第三方相依宣告（SSOT）——`(import 名, pip 名)`。
#
# WHY（R68；本 repo 三支 CI 自 2026-07-14 起連續全紅、無人察覺的根因）：本目錄名義上
# 是「純 stdlib、零安裝」的根層基建測試（`root-infra-ci.yml` 檔頭與其 unittest step
# 的註解皆如此自陳），但其中三支 Windows 交叉一致性測試必須 import `autoclaude.*` 的
# **真實函式物件**，與 bash／PowerShell 側的平行實作逐輸入比對裁決是否一致——那正是
# 它們的全部價值，不能改寫成字面比對。而 `autoclaude/utils/__init__.py` 與
# `autoclaude/execution/__init__.py` 是 eager import：只要碰其中任一支子模組，整棵
# AutoClaude runtime 相依樹（yaml → pydantic → httpx）就被一併拉進來。
#
# 於是「零安裝」的自陳與實況矛盾，而代價**不是**測試變慢、是測試**消失**：缺相依時
# `unittest` discovery 把該模組整份覆蓋塌成一支 `_FailedTest` 佔位測試，收集數靜默
# 少掉 N-1 支。三個 CI 平台（ubuntu／macOS／Windows runner）實測收集數完全一致，
# 且與本機「stdlib-only venv」實測值一致——那是環境維度差異，不是平台維度差異。
#
# 🔴 判準：**`MIN_TESTS` 只有一個值**，即相依齊備環境下的實測值。刻意**不**做成
# 「環境感知的雙下限」——那等於把一個壞掉的環境升格成合法的第二種環境，並讓 CI 在
# 122 支 Windows 迴歸鎖一支都沒跑的狀態下印綠燈，正是本檔其餘四層都在治的
# fail-open。本清單因此是「`MIN_TESTS` 得以成立的前提」，由三道機械物看守：
#   ① `main()` 開場 fail-fast，訊息直接指路（0.5 秒，不必等 110 秒跑完才誤診）；
#   ② `run_with_floor` 的下限失敗訊息會歸因到 import 失敗的模組（見
#      `report_floor_failure`）——把「環境不完整」與「測試真的消失」分開講；
#   ③ `tools/tests/test_run_root_unittests.py::CiPrereqInstallLockTest`：凡在 CI
#      裡跑本 runner 的 job，都必須在同一個 job 內、該 step **之前**安裝本清單的
#      每一個 pip 名，否則紅。這道才是防「下次再加一個相依就重演」的那道。
#
# 維護契約：新增任何會拉進第三方相依的測試時，把該相依加進本清單並同步 CI 安裝
# 步驟；漏加時 ③ 會紅，漏裝時 ①② 會紅並點名。
_THIRD_PARTY_PREREQS: tuple[tuple[str, str], ...] = (
    ("yaml", "pyyaml"),
    ("pydantic", "pydantic"),
    ("httpx", "httpx"),
)

# `[WINDOWS-NATIVE-ONLY]` skip 標籤家族（R43／R67-F11／R72）已於 R72 整組抽進
# `tools/lib/windows_skip_tags.py`（先例＝`tools/lib/ci_liveness.py`），WHY 見該檔頭：
# 內聚（runtime 面與靜態面共用同一份標籤／關鍵詞／述詞常數，放一起才不會各自漂移）
# ＋ 本檔受 `AutoClaude/tools/check_loc_budget.py` SPECIAL_FILES 棘輪管制且動工前恰好
# 卡滿，該棘輪 override_reason 逐字指示「先刪死碼／抽共用模組」。
# 此處**再匯出**而非改所有呼叫端：`run_root_unittests.WINDOWS_NATIVE_SKIP_TAG` 這類
# 引用散落在測試與文件裡，改名的成本遠大於收益（Rule 3）；再匯出的是**同一個物件**，
# 故既有 `mock.patch.dict(run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT, …)` 照常生效。
# 逐名 `noqa: F401`＝**再匯出**的意思（本檔不用它們，外部靠本檔的名字取用）；不寫的話
# `ruff check tools/`（pre-push 快層第 ④ 段 ＋ root-infra-ci 第 16 道）會判 F401 並紅。
from lib.windows_skip_tags import (  # noqa: E402, I001
    WINDOWS_NATIVE_SKIP_TAG,  # noqa: F401
    _WINDOWS_LIKE_SKIP_HINTS,  # noqa: F401
    _WINDOWS_SKIP_TAG_EXEMPT,  # noqa: F401
    all_skips,  # noqa: F401
    report_all_skips,
    report_untagged_windows_like_skips,
    report_untagged_windows_skip_decorators,
    report_windows_native_skips,
    report_windows_skip_tag_exemption_problems,
    untagged_windows_like_skips,  # noqa: F401
    windows_native_skips,  # noqa: F401
)

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import skip_group_policy  # noqa: E402  ← R80 包 A（S3-04）：skip 分群天花板的政策 SSOT

_PATTERN = "test_*.py"

# discovery 佔位測試（`_FailedTest`／`ModuleSkipped`）都是在 `unittest.loader`
# 裡動態造出來的類別，用 `__module__` 即可與真實測試模組區分。
_PLACEHOLDER_MODULE = "unittest.loader"

# 具名例外：磁碟上符合 `_PATTERN` 但**合法**不貢獻任何測試的檔案。
# 現況為空集合（R60 實測 53 支 `test_*.py` 每支都至少貢獻 1 支測試）。刻意保留這個
# 空常數而非省略：例外必須**逐檔具名並附理由**，不接受「整批略過」的通用開關——
# 那等於把缺口洗掉。註：helper 檔（`_platform_helpers.py`／`_ps_engine.py`）不符
# `test_*.py`，本來就不在收集面內，無需列名。
_COLLECTION_EXEMPT: frozenset[str] = frozenset()


def discover_suite(start_dir: Path) -> unittest.TestSuite:
    # 每次新建 TestLoader：defaultTestLoader 有狀態（_top_level_dir 殘留），
    # 同進程第二次對不同目錄 discover 會炸 "Start directory is not importable"。
    return unittest.TestLoader().discover(str(start_dir), pattern=_PATTERN)


def inventory_fingerprint(start_dir: Path, pattern: str = _PATTERN) -> tuple[int, str]:
    """回傳 `(檔數, 指紋)`；指紋＝`(檔名, 位元組大小)` 排序後 sha256 前 12 碼。

    WHY（R60 Pkg-P8 主修，對症的是**真正**的根因）：本 runner 印出的「發現 N 個
    測試」過去是**不可跨次比較**的裸數字——它沒有記錄「這個 N 是由哪一份磁碟狀態
    產生的」。R60 並行修復期間三次量測分別得到 894／906／916，被當成「並行負載下
    收集數不決定性」立案追查；實際上三者是 865 ＋ {29, 41, 51}——865 是另外 52 支
    檔的固定貢獻，{29, 41, 51} 則是**同一支** `test_check_defect_log_crossref.py`
    被另一個並行包從 29 支逐步擴充到 51 支的三個時間切片（29 支＝該檔
    `git show HEAD:` 版本實測值）。沒有任何一次是 race，缺的 12 支從來不存在。
    印出指紋後，兩次數字不同時可**當場**分辨「樹變了」與「同一棵樹量到不同數字」
    ——只有後者才是真的非決定性、才值得追。成本＝一行輸出。
    """
    rows = sorted((p.name, p.stat().st_size) for p in start_dir.glob(pattern))
    blob = "\n".join(f"{name}:{size}" for name, size in rows)
    return len(rows), hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def _flatten(suite: unittest.TestSuite) -> list[unittest.TestCase]:
    out: list[unittest.TestCase] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            out.extend(_flatten(item))
        else:
            out.append(item)
    return out


def _module_of(test: unittest.TestCase) -> str:
    cls = type(test)
    if cls.__module__ == _PLACEHOLDER_MODULE:
        # 佔位測試把「原本該被載入的模組名」放在方法名上（`_FailedTest(name, …)`）。
        return str(getattr(test, "_testMethodName", ""))
    return str(cls.__module__)


def suite_modules(suite: unittest.TestSuite) -> dict[str, int]:
    """純函式（無 I/O 副作用）：回傳 `模組名 -> 該模組被收集到的測試數`。"""
    counts: dict[str, int] = {}
    for test in _flatten(suite):
        name = _module_of(test)
        counts[name] = counts.get(name, 0) + 1
    return counts


def collection_gaps(
    suite: unittest.TestSuite,
    start_dir: Path,
    pattern: str = _PATTERN,
    exempt: frozenset[str] = _COLLECTION_EXEMPT,
) -> list[str]:
    """純函式：磁碟上符合 `pattern` 卻**一支測試都沒被收集到**的檔名（去 exempt）。

    WHY：`MIN_TESTS` 是**下限**語意，只擋「掉太多」，擋不住「悄悄少收幾支而總數
    仍在下限之上」——R60 當下實況 916 支 vs 下限 845 ⇒ **可靜默蒸發 71 支仍印 ✅**，
    且沒被收集的測試不會出現在 `skipped=N`、不會出現在 `report_all_skips` 明細、
    不會出現在任何一行輸出裡（它從來沒被 loader 交給 runner）。

    而 `unittest` discovery 確實有一條**完全靜默**的丟檔路徑（Python 3.11.9 實查
    `unittest/loader.py::TestLoader._find_test_path`）：`os.path.isfile()` 與
    `os.path.isdir()` 皆為 False 時走結尾的 `else: return None, False`——不拋例外、
    不進 `loader.errors`、不印任何東西。而 `os.path.isfile()` 內部
    `except (OSError, ValueError): return False` 會把 stat 失敗吞成「不是檔案」；
    `_find_tests()` 又只在開頭做一次 `sorted(os.listdir())` 之後才逐檔 import，
    故「listdir 已看到、輪到它時檔案不在了」的窗口 ≈ 整段 discovery 時長。
    （本包實測**排除**兩個曾被懷疑的觸發條件：另一行程持 exclusive handle
    `dwShareMode=0`、以及 delete-pending `FILE_FLAG_DELETE_ON_CLOSE`，兩者
    `os.path.isfile()` 皆仍回 True——Windows 對 `FILE_READ_ATTRIBUTES` 永不衝突。
    只有「該瞬間檔案真的不在」才會觸發。）

    故本層改成**集合比對**「磁碟每支 test_*.py 是否都至少貢獻一支測試」，抓的是
    「有檔沒被收到」而非「總數掉太多」，鑑別力與 `MIN_TESTS` 正交。
    """
    on_disk = {p.stem for p in start_dir.glob(pattern)}
    return sorted(on_disk - set(suite_modules(suite)) - exempt)


def discovery_placeholders(suite: unittest.TestSuite) -> list[tuple[str, str]]:
    """純函式：回傳 `(模組名, 佔位類別名)`——被 discovery 換成佔位測試的模組。

    兩種佔位都會讓「一支檔的 N 支測試塌成 1 支」，計數靜默 -(N-1)：
      `_FailedTest`（import 失敗）——執行時必紅，但**計數**的塌陷無聲；
      `ModuleSkipped`（模組層 `raise SkipTest`）——**rc 仍為 0**，該模組整份覆蓋
      無聲消失，是真正的 fail-open。
    兩者都不該混在總數裡看不見，故一律點名並讓 rc 為 1。
    """
    out = [
        (_module_of(t), type(t).__name__)
        for t in _flatten(suite)
        if type(t).__module__ == _PLACEHOLDER_MODULE
    ]
    return sorted(out)


def fixture_level_entries(result: unittest.TestResult) -> list[str]:
    """純函式：回傳 class／module 層 fixture（`setUpClass`／`setUpModule`）產生的條目。

    `unittest` 用 `_ErrorHolder` 承載這類條目，而它**不是** `TestCase` 子類，故以
    `isinstance(..., unittest.TestCase)` 為 False 即可辨識，無需 import 私有名稱。
    """
    out: list[str] = []
    for bucket in (result.skipped, result.errors, result.failures):
        for entry in bucket:
            test = entry[0]
            if not isinstance(test, unittest.TestCase):
                out.append(str(getattr(test, "description", test)))
    return sorted(out)


def report_execution_gap(collected: int, result: unittest.TestResult) -> int:
    """印出「收集到」與「真正執行」的差額；回傳差額（為 0 時完全靜音）。

    WHY（R60 Pkg-P8，本包最重的發現）：`MIN_TESTS`／ratchet 守的是
    `countTestCases()`＝**收集數**，但真正跑了幾支是 `result.testsRun`，而
    **這兩個數字可以差很多，且原本沒有任何一處比較它們**。

    機制（Python 3.11.9 實查 `unittest/suite.py::TestSuite.run`）：`setUpClass`／
    `setUpModule` 失敗或 `raise SkipTest` 時，`_handleClassSetUp` 設下
    `_classSetupFailed`／`_moduleSetUpFailed`，接著 `run` 對該類別每一支測試走
    `continue`——`test(result)` **根本沒被呼叫**，故 `testsRun` 完全不增加，而
    `countTestCases()` 早在 discovery 時就把它們算進去了。

    實測（沙箱，9 支方法 + setUpClass 拋 SkipTest）：收集 11／執行 2／未執行 9，
    `result.skipped` 只多**一筆** `setUpClass (…)`，`wasSuccessful()` 仍為 True
    ⇒ **rc=0**。也就是說整個類別的覆蓋可以無聲消失，而下限守門結構性看不到
    （它守的數字沒變），`skipped=N` 也只多 1、完全不提「這一筆吃掉了 9 支」。
    對照：方法層 skip（`@skipUnless`）**會**計入 `testsRun`（`TestCase.run` 先
    `startTest()` 才判 skip），所以只有 fixture 層會造成這個差額。
    本 repo 現正使用該模式（`test_macos_smoke_skip_honesty.TestSummaryTailRealRun.
    setUpClass` 在找不到 bash 時 `raise SkipTest`），故這不是理論風險。

    設計取捨：**不**把差額一律判紅——上述環境條件式整類 skip 是本 repo 刻意採用的
    合法模式，一律判紅會在缺工具的機器上製造假紅。改為「差額必須被點名、且必須有
    fixture 層條目可歸因」，把判斷交給讀者；無法歸因的差額（例如 `result.stop()`
    中途中止）才判紅。這與 DEF-101-510「不得只印計數」同一精神，只是把它從 skip
    維度延伸到**執行**維度。
    """
    gap = collected - result.testsRun
    if gap > 0:
        print(
            f"⚠️  收集 {collected} 支、實際執行 {result.testsRun} 支——有 {gap} 支"
            f"**從未被執行**（下限守門看的是收集數，結構性抓不到這件事）。"
            f"可歸因的 class／module 層 fixture 條目："
        )
        for description in fixture_level_entries(result) or ["（無——差額無法歸因）"]:
            print(f"   - {description}")
    return gap


def skip_census_profile() -> str:
    """本棵樹的剖面鍵。刻意**不**帶 `AutoClaude/tests` 那邊的 `+nested` 維度：
    當回合以 Grep 對 `tools/tests` 全樹搜 `CLAUDECODE` 命中 0 ⇒ 這棵樹的 skip 集合
    不隨「是否巢狀 Claude Code session」改變（誠實劃界，不是漏寫）。"""
    return f"tools/tests@{sys.platform}"


def report_skip_census(result: unittest.TestResult) -> int:
    """印 skip 分群普查並判天花板；回 0／1（呼叫端併進 rc）。

    🔴 R80 包 A（S3-04）為何非有不可：本 runner 此前對 43 支 skip **只印不判**——
    `report_all_skips` 把每一支的理由都印出來了（本輪實測確認：理由**印得出來**，
    掃描員原判「verbosity=1 使理由結構上永遠印不出來」與磁碟不符），但那些行不進入
    任何判準，rc 與它們完全無關。⇒ 這一棵樹的 skip 可以無聲從 43 長到 143 而閘門全綠，
    而 pytest 那一棵（AutoClaude）自 R79 起已經有天花板在管。同一個 repo 對同一件事
    兩種待遇，缺的那一邊當然是先失守的那一邊。

    未登記的剖面（mac／Linux runner 第一次跑到這裡）**只印不判**：在那裡擋下一個
    從來沒人量過的平台是誤擋而不是嚴格（沿用 `local_ci_gate.census_only` 已付過學費
    的判斷，同一份理由不另寫一套）。
    """
    profile = skip_census_profile()
    reasons = [reason for _, reason in all_skips(result)]
    census = skip_group_policy.skip_group_census(reasons)
    print(f"[skip census] {profile} 共 {len(reasons)} 支："
          + "／".join(f"{g}={n}" for g, n in census.items())
          + f"／欠債型 {skip_group_policy.open_debt(census)} 支（目標 0）")
    problems = skip_group_policy.skip_group_census_problems(
        profile, census, reasons=reasons)
    if not problems:
        for line in skip_group_policy.skip_target_report(profile, census):
            print(f"ℹ️  [skip target] {line}")
        return 0
    if not skip_group_policy.profile_registered(profile):
        print("⚠️  剖面未登記——量測正常，但這個平台從來沒有人量過健康值，沒有天花板可比"
              "（advisory；把上面那行實測值填進 skip_group_policy 兩張表即升級為阻斷）")
        return 0
    print("❌ skip 分群天花板不合格（S3：skipped 數必須有人管）：", file=sys.stderr)
    for msg in problems:
        print(f"   - {msg}", file=sys.stderr)
    return 1


def report_collection_gaps(gaps: list[str], start_dir: Path) -> None:
    if gaps:
        print(
            f"❌ 收集面完整性失敗：{start_dir} 底下有 {len(gaps)} 支 {_PATTERN} "
            f"檔案一支測試都沒被收集到——這類「有檔沒被收到」不會出現在總數下限、"
            f"不會出現在 skipped 明細、不會出現在任何輸出裡（見 collection_gaps "
            f"docstring 的 stdlib 靜默丟檔路徑）：",
            file=sys.stderr,
        )
        for name in gaps:
            print(f"   - {name}.py", file=sys.stderr)
        print(
            "   若某支檔案確實刻意不含任何測試，請把它**具名**加入 "
            "run_root_unittests._COLLECTION_EXEMPT 並註明理由。",
            file=sys.stderr,
        )


def report_discovery_placeholders(suite: unittest.TestSuite) -> list[tuple[str, str]]:
    placeholders = discovery_placeholders(suite)
    if placeholders:
        print(
            f"❌ discovery 佔位測試 {len(placeholders)} 筆：下列模組的測試**沒有**"
            f"被真正載入，整份覆蓋塌成一支佔位測試（計數靜默減少）：",
            file=sys.stderr,
        )
        for module, kind in placeholders:
            print(f"   - {module}（{kind}）", file=sys.stderr)
    return placeholders


def missing_third_party_prereqs(
    prereqs: tuple[tuple[str, str], ...] = _THIRD_PARTY_PREREQS,
) -> list[tuple[str, str]]:
    """純函式（無 I/O 副作用，比照本檔 `windows_native_skips` 慣例）：回傳當前環境
    **找不到**的宣告相依 `(import 名, pip 名)`。

    刻意用 `importlib.util.find_spec` 而非 `try: import`：只問「找不找得到」，不執行
    模組頂層副作用，也不把模組留在 `sys.modules` 影響隨後的 discovery。找不到時
    stdlib 會拋 `ModuleNotFoundError`（`ImportError` 子類），一併接住。
    """
    out: list[tuple[str, str]] = []
    for import_name, pip_name in prereqs:
        try:
            found = importlib.util.find_spec(import_name) is not None
        except (ImportError, ValueError):
            found = False
        if not found:
            out.append((import_name, pip_name))
    return out


def install_hint(missing: list[tuple[str, str]]) -> str:
    """組出可直接複製貼上的安裝指令。

    每個套件名**各自**加單引號：本 repo 對 macOS zsh 的既定紀律（DEF-101-479／507／
    508，機械守門見 `tools/tests/test_extras_quoting_zsh_safety.py`）。此處的名字雖
    都不含 `[extras]`、當下不會觸發 zsh 的 filename generation，仍照同一形態寫——
    紀律的價值在於不必每次重新判斷「這個 target 到底會不會被 glob」。
    """
    return "python -m pip install " + " ".join(f"'{pip}'" for _, pip in missing)


def report_missing_third_party_prereqs(
    missing: list[tuple[str, str]] | None = None,
) -> list[tuple[str, str]]:
    """印出缺漏的前置相依並回傳清單（非空 ⇒ 呼叫端須讓 rc 為 1，見 `main`）。"""
    if missing is None:
        missing = missing_third_party_prereqs()
    if missing:
        print(
            f"❌ 環境缺少 {len(missing)} 個 tools/tests 的第三方相依："
            f"{'、'.join(imp for imp, _ in missing)}。\n"
            f"   🔴 這不是「測試消失」，是「環境不完整」——缺相依時 unittest discovery "
            f"會把 import 失敗的模組整份覆蓋塌成一支佔位測試，收集數因而低於 MIN_TESTS。"
            f"MIN_TESTS 只有一個值（相依齊備環境下的實測值），不是「環境感知的雙下限」。\n"
            f"   修法：{install_hint(missing)}\n"
            f"   若在 CI 撞到：跑本 runner 的 job 少了相依安裝 step——該綁定由 "
            f"tools/tests/test_run_root_unittests.py::CiPrereqInstallLockTest 機械看守，"
            f"請一併檢查它為何沒紅。",
            file=sys.stderr,
        )
    return missing


def report_floor_failure(
    start_dir: Path,
    count: int,
    min_tests: int,
    placeholders: list[tuple[str, str]],
    missing: list[tuple[str, str]],
) -> None:
    """下限失敗時的**歸因**輸出：把「環境不完整」與「測試真的消失」分開講。

    WHY（R68）：原訊息只有一種說法——「測試疑似大規模靜默消失（目錄改名/pattern
    不符/路徑錯）」。但三個 CI 平台實際撞上的是第四種原因（環境缺第三方相依），
    於是那行紅字把每一位讀者都指往三條全錯的路；而唯一正確的線索（`_FailedTest`
    佔位測試清單）在原流程裡要等下限守門**放行後**才印得出來——下限沒放行，線索
    就永遠印不出來。故本函式在判決的同一則訊息裡就把歸因給完。
    """
    print(
        f"❌ unittest 數量下限釘選失敗：{start_dir} 只發現 {count} 個測試 < 下限 {min_tests}",
        file=sys.stderr,
    )
    if not placeholders:
        print(
            "   歸因：本次**沒有**任何模組載入失敗 ⇒ 這是真的大規模消失"
            "（目錄改名／pattern 不符／路徑錯）；若為刻意刪減請同步下修 MIN_TESTS。",
            file=sys.stderr,
        )
        return
    print(
        f"   歸因：本次有 {len(placeholders)} 個模組**沒有被真正載入**，每個都塌成一支"
        f"佔位測試 ⇒ 收集數已被污染、與下限不可比。這是**環境問題**，不是測試消失：",
        file=sys.stderr,
    )
    for module, kind in placeholders:
        print(f"   - {module}（{kind}）", file=sys.stderr)
    if missing:
        print(
            f"   直接原因：宣告的第三方相依缺 "
            f"{'、'.join(imp for imp, _ in missing)}。修法：{install_hint(missing)}",
            file=sys.stderr,
        )
    else:
        print(
            "   宣告的第三方相依（run_root_unittests._THIRD_PARTY_PREREQS）都在，"
            "故失敗另有原因：若是**新增**的第三方相依，請把它加入該清單並同步 CI "
            "安裝步驟；否則請看上列模組的 import traceback。",
            file=sys.stderr,
        )


def run_with_floor(start_dir: Path, min_tests: int) -> int:
    """discover → 數量下限守門 → 收集面完整性守門 → 執行；回傳 exit code。"""
    suite = discover_suite(start_dir)
    count = suite.countTestCases()
    if count < min_tests:
        # 歸因線索（佔位測試／缺漏相依）必須與判決**同時**印出，見 report_floor_failure。
        report_floor_failure(
            start_dir, count, min_tests,
            discovery_placeholders(suite), missing_third_party_prereqs(),
        )
        return 1
    print(f"✅ unittest 數量下限釘選通過：發現 {count} 個測試（下限 {min_tests}）")
    nfiles, fingerprint = inventory_fingerprint(start_dir)
    print(
        f"🧾 收集面盤存：{nfiles} 支 {_PATTERN} 檔／指紋 {fingerprint}"
        f"（跨次數字可比較用，見 inventory_fingerprint docstring）"
    )
    gaps = collection_gaps(suite, start_dir)
    if gaps:
        report_collection_gaps(gaps, start_dir)
        return 1  # 量測本身已不可信，fail-closed：不放行、也不假裝跑完
    placeholders = report_discovery_placeholders(suite)
    warn_ratchet_drift(count, min_tests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    report_windows_native_skips(result)
    report_all_skips(result)
    # R67-F11：標籤漏標＝上面那行標題低報 ⇒ fail-closed。與收集面缺口（見
    # `report_collection_gaps`）同一精神：量測本身已不可信時不放行。
    untagged = report_untagged_windows_like_skips(result)
    # 本輪：具名豁免表的 stale／格式自檢。刻意**不**提早 return——早退會遮蔽下面
    # 的執行落差與失敗明細，而遮蔽的方向是「看起來變乾淨」（Scan-H⑦）。
    exempt_problems = report_windows_skip_tag_exemption_problems(result)
    # R80 包 A（S3-04）：把這 43 支 skip 納入天花板管轄。同樣刻意不提早 return。
    census_rc = report_skip_census(result)
    # 無法歸因的「收集了卻沒執行」＝量測不完整（例如 result.stop() 中途中止）。
    # 可歸因者（fixture 層 skip／error）只點名不判紅，理由見 report_execution_gap。
    unexplained_gap = report_execution_gap(count, result) > 0 and not fixture_level_entries(result)
    if not result.wasSuccessful():
        dump_failure_detail(result)
    # 佔位測試刻意**不**提早 return：讓 suite 照跑，`_FailedTest` 才會把真正的
    # ImportError traceback 交給 `dump_failure_detail` 落檔（提早 return 會丟掉
    # 唯一的診斷資訊）；rc 則在此與 `wasSuccessful()` 一起收斂。
    return (
        0
        if (result.wasSuccessful() and not placeholders and not unexplained_gap
            and not untagged and not exempt_problems and not census_rc)
        else 1
    )


def ratchet_drift_message(
    count: int, min_tests: int, ratio: float = RATCHET_WARN_RATIO
) -> str | None:
    """純函式（無 I/O 副作用，比照 `windows_native_skips` 慣例）：實況相對下限
    漂移超過 `ratio` 倍時回傳提醒字串，否則 None。R57 新增，WHY 見
    `RATCHET_WARN_RATIO`。`ratio` 參數化是為了讓兩層共用同一段判定與訊息：
    runner 用預設的 WARN 倍數，保鮮期斷言傳 `RATCHET_STALE_RATIO`。"""
    if count <= min_tests * ratio:
        return None
    return (
        f"⚠️  測試數量下限已過期：實況 {count} 個 > 下限 {min_tests} × "
        f"{ratio}——下限的鑑別力只剩「可靜默蒸發 {count - min_tests} "
        f"個測試仍不紅」，請把 tools/run_root_unittests.py 的 MIN_TESTS 重釘為 {count}"
    )


def warn_ratchet_drift(count: int, min_tests: int) -> str | None:
    msg = ratchet_drift_message(count, min_tests)
    if msg is not None:
        print(msg)
    return msg


# R57 round 3 ARCH-R57R3-03：Architect 獨立重跑本 runner 14 次，其中 **1 次**出現
# `Ran 610 tests / FAILED (failures=4, skipped=4)`，其餘 13 次全綠；三種針對性重現
# （連跑 6 次／兩實例並行／8 顆 CPU 燒滿）皆未重現，而**本 runner 不保留失敗細節**，
# 該次的失敗測試名隨 process 消失，故無法歸因。方向為 fail-closed（假紅、不放行缺陷），
# 但「下次再發生仍然無法診斷」本身是可以現在就消除的缺口。
# 落檔而非改判邏輯：不動 rc、不動任何斷言，只在已經要回 1 的路徑上多寫一份明細。
_FAILURE_LOG = Path(__file__).resolve().parent / ".last_failure.log"


def dump_failure_detail(result: unittest.TestResult, path: Path | None = None) -> Path:
    """把失敗/錯誤的 test id 與 traceback 落檔，供下次非決定性翻紅時定位。

    只在 `wasSuccessful()` 為 False 時被呼叫。回傳寫入的路徑（測試用）。
    寫檔失敗不得影響 runner 的 rc——診斷輔助不應反過來變成新的失敗來源。
    """
    target = path or _FAILURE_LOG
    # R57 round 4 SA-R57R4-01：`wasSuccessful()` 在 `unexpectedSuccesses` 非空時
    # 也回 False，原版只讀 failures/errors ⇒ 該模式下 rc=1 卻落一份**不指名任何
    # 測試的空明細**，正是本機制立意要消除的「無法歸因」狀態（實測產出僅 60 bytes
    # 的 `（0 failures / 0 errors）` 標頭）。三個 bucket 一併納入。
    unexpected = list(getattr(result, "unexpectedSuccesses", ()) or ())
    lines = [f"# run_root_unittests 失敗明細（{len(result.failures)} failures / "
             f"{len(result.errors)} errors / {len(unexpected)} unexpected successes）"]
    for label, bucket in (("FAIL", result.failures), ("ERROR", result.errors)):
        for test, tb in bucket:
            lines.append(f"\n===== {label}: {test.id()} =====\n{tb}")
    for test in unexpected:
        # unexpectedSuccesses 沒有 traceback，只有測試本身（標了 expectedFailure 卻通過）
        tid = test.id() if hasattr(test, "id") else str(test)
        lines.append(f"\n===== UNEXPECTED SUCCESS: {tid} =====\n"
                     "（標記 expectedFailure 但實際通過——該缺陷可能已修好，請移除標記）")
    return _write_failure_log(target, "\n".join(lines))


def _write_failure_log(target: Path, body: str) -> Path:
    """落檔並回報。與 `dump_failure_detail` 分離＝比照本檔 `windows_native_skips`／
    `report_windows_native_skips` 的既有慣例（R57 round 4 SA-R57R4-02／QA-R57R4-02：
    print 副作用寫在被單元測試直接呼叫的函式內，會讓每次**全綠**執行的終端輸出混入
    fixture 產生的落檔訊息與 ⚠️ 警告，混淆複審者對「本次是否真有失敗」的判讀——與
    R43 二審 SA 對 `windows_native_skips` 揪出的問題同型）。"""
    try:
        target.write_text(body, encoding="utf-8")
        print(f"🔍 失敗明細已落檔：{target}（供非決定性翻紅時定位，見 DEF-101-499）")
    except OSError as exc:  # 診斷輔助失敗不得升級為 runner 失敗
        print(f"⚠️  失敗明細落檔失敗（{exc}）——不影響 rc", file=sys.stderr)
    return target


# R67 round 2（SA-R67-02／SD-R67-01／QA-R67-01 三方交叉命中）：`MIN_TESTS` 的 WHY
# 註記裡不得寫死「當場即可現查」的量測 token。三種形態各對應一次已發生的事故：
#   `指紋 <12 碼 hex>`   ——每輪必變，寫下的那一刻起就無人能複現（本輪實際發生）；
#   `Ran <數字> tests`   ——同上，且它是「跑完的結論」，寫在常數註記裡等於假造結論；
#   `發現 <數字> 個測試` ——runner 每次執行都會印當下值，重複寫一份只是多一個 stale 站點。
# 判準邊界（誠實劃界）：本鎖只看 `MIN_TESTS = ` 那一行的註記，抓的是**形態**不是
# 語意——換個寫法（「一三四三支」「fingerprint abc…」）一樣抓不到，那半邊仍是人審
# 責任。它擋的是本輪真正發生過的那一種復發，不宣稱涵蓋全部。
_LIVE_MEASUREMENT_TOKENS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("收集面指紋", re.compile(r"指紋\s*[0-9a-f]{12}")),
    ("Ran <數字> tests", re.compile(r"Ran\s+\d+\s+tests")),
    ("發現 <數字> 個測試", re.compile(r"發現\s*\d+\s*個測試")),
)


def min_tests_note_stale_tokens(source: str | None = None) -> list[tuple[str, str]]:
    """純函式（無 I/O 副作用，比照本檔 `windows_native_skips` 慣例）：回傳
    `MIN_TESTS` 註記內違規的 `(形態名, 逐字命中)`；全乾淨時回空 list。

    `source` 參數化僅供注入測試；預設讀本檔自身。刻意**只**取
    `MIN_TESTS = ` 那一行的 `#` 之後——射程精確到「被守護的那段散文」，
    不會誤傷本檔其他地方合法出現的量測字樣（例如 `run_with_floor` 的
    f-string、以及本註記自己列舉的三種形態說明）。

    兩條 fail-open 已封（本鎖自己也是量測載具，載具必須被驗證）：
    找不到 `MIN_TESTS = ` 行、或該行沒有註記，都當成違規回報——否則
    「把註記整段刪掉」會讓本鎖靜默通過，那正是它要防的失效模式的極端形。
    """
    if source is None:
        source = Path(__file__).resolve().read_text(encoding="utf-8")
    for line in source.splitlines():
        if line.startswith("MIN_TESTS = "):
            note = line.split("#", 1)[1] if "#" in line else ""
            break
    else:
        return [("取值面消失", "找不到 `MIN_TESTS = ` 起始的那一行——本自檢無從取值")]
    if not note.strip():
        return [("註記消失", "`MIN_TESTS` 那一行沒有 WHY 註記——重釘沿革與判準是本鎖的守護標的")]
    return sorted(
        (label, match.group(0))
        for label, pattern in _LIVE_MEASUREMENT_TOKENS
        for match in pattern.finditer(note)
    )


def report_min_tests_note_stale_tokens() -> list[tuple[str, str]]:
    """印出違規並回傳清單（非空 ⇒ 呼叫端須讓 rc 為 1，見 `main`）。"""
    offenders = min_tests_note_stale_tokens()
    if offenders:
        print(
            f"❌ MIN_TESTS 的 WHY 註記寫死了 {len(offenders)} 個「當場即可現查」的量測 "
            f"token——它們每輪必變、寫下後無人能複現，而本 runner 每次執行都會把當下值"
            f"印在終端（R67 實際事故：註記宣稱的指紋與計數在最終工作樹上全部複現不出來，"
            f"SA-R67-02／SD-R67-01／QA-R67-01）：",
            file=sys.stderr,
        )
        for label, hit in offenders:
            print(f"   - {label}：{hit!r}", file=sys.stderr)
        print(
            "   修法：把該 token 從註記中刪除，改寫成「見本 runner 當場輸出」；"
            "確實要留沿革時只寫**釘選值**（那個值本身受 tools/sync_onboarding_baselines.py "
            "的 rootunit-baseline-live 鎖與本檔保鮮期斷言雙重看守），不要抄一份量測結論。",
            file=sys.stderr,
        )
    return offenders


def main() -> int:
    if not _TESTS_DIR.is_dir():
        print(f"❌ 測試目錄不存在：{_TESTS_DIR}", file=sys.stderr)
        return 1
    # 先於 110 秒的全套執行做這道自檢：釘選值的**取證敘述**若已失實，後面印出的
    # ✅ 只會替一個假前提背書；fail-fast 也讓注入實測不必等一整輪。
    if report_min_tests_note_stale_tokens():
        return 1
    # 同理先於全套執行：相依不齊時收集數必然低於下限，讓它照跑只是把一個**環境
    # 問題**包裝成一則看起來像「測試消失」的紅字（R68：三支 CI 連續多輪的實況）。
    if report_missing_third_party_prereqs():
        return 1
    # R72：**不分平台**的靜態標籤掃描。刻意放在這裡而非 `run_with_floor` 內：
    #   ① `run_with_floor` 會被單元測試餵各種合成樹呼叫，把 repo 專屬的掃描綁進去
    #      會讓那些合成樹莫名其妙地受本判準管轄；
    #   ② 這道掃描是純靜態、~0.1 秒，fail-fast 讓漏標不必等全套跑完才看到；
    #   ③ 🔴 rc 必須真的被消費——「可重跑但沒有任何閘門看它的 rc」與「不可重跑」是
    #      同一個病（Scan-H 判準⑤）。本行的 return 1 即是那個消費者，經由
    #      `python tools/run_root_unittests.py` 傳到 pre-push root-infra leg 與三支 CI。
    if report_untagged_windows_skip_decorators(_TESTS_DIR, _PATTERN):
        return 1
    return run_with_floor(_TESTS_DIR, MIN_TESTS)


#: 本 runner 的 CLI 契約＝**零旗標**（呼叫端實查：`tools/git-hooks/pre-push` root-infra
#: leg ②、`root-infra-ci.yml` step 8、`windows-compat-ci.yml`、`macos-compat-ci.yml`
#: 四處全都是裸呼叫、一個引數都沒傳）。空 tuple 讓 `_cli_flags` 印「本工具不接受任何旗標」。
_KNOWN_ARGV: tuple[str, ...] = ()


def cli(argv: list[str]) -> int:
    """CLI 入口：未知引數一律 rc=2 fail-loud，全合法才委派 `main()`。

    WHY 本層存在（R74 SD 獨立複審抓到的射程缺口）：本檔修前全檔 grep
    `argv|argparse|_cli_flags` **零命中** ⇒ 帶未知旗標時直接跑預設路徑、跑完整棵樹
    （逾 120 秒），最終 rc 反映的是「套件結果」而不是「旗標被拒收」。而本檔正是
    pre-push root-infra leg ＋ 三支 CI 真正執行的那一支——後果最大的工具，逃掉
    R67-D20 那道紀律的唯一原因是**檔名不叫 `check_*`**（該鎖以檔名 glob 劃界）。

    🔴 為何拒收寫在這裡、而**不是**寫進 `main()`（同 `tools/check_defect_log_crossref.py`
    已付過學費的判斷，逐字沿用它的理由）：`main()` 有既有的**程式化呼叫端**——
    `tools/tests/test_run_root_unittests.py` 的零相依探針在子行程內叩 `R.main()`，
    而那個子行程的 `sys.argv` 帶的是**探針自己**的三個參數（blocked JSON／mode／
    tools_dir）。若在 `main()` 內讀 `sys.argv`，那三個參數會被當成本 runner 的旗標
    ⇒ 探針 `main` 模式回 rc=2 而不是它斷言的 rc=1，一道真鎖當場變假紅。
    同一個誤傷面本輪另有實例（本機實測、HEAD 既存）：
    `python -m unittest tools.tests.test_gha_action_versions` 3 支假紅，
    因為 `main(argv=None)` 讀到的是 unittest 放進 `sys.argv` 的模組名。
    ⇒ 判準：**「讀 `sys.argv`」只能發生在只有真 CLI 才會走的這一層**，
    `main()` 一律只吃顯式引數。機械看守見
    `tools/tests/test_check_wrapper_thinness.py::TestRootGateToolsRejectUnknownFlags`。
    """
    rc = _cli_flags.reject_unknown_argv("run_root_unittests.py", argv, _KNOWN_ARGV)
    return main() if rc is None else rc


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
