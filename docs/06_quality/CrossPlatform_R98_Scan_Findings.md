# R98 — 護欄層行數棘輪重釘證據

- **日期**：2026-08-21
- **建立者**：R98 收尾單人窗口（多包並行收尾後的單人重跑窗口）

<!-- guard-total:R98 --> **本輪護欄層累積淨額＝ 85687 → 85248（-439）** —— 兩次收斂
合計（含本檔＝`test_adr_xplat001_c1c2_lock.py`自身編修的逐輪追加共 +10 行），
逐檔漂移詳見下方〈逐檔漂移〉表與〈第二次收斂〉節；本輪淨額為負，未打破
`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`（R96 +407／R97 +881 已連兩輪為正，R98 需 ≤0
才不觸發 `[只升不降]`，本輪 -439 已滿足）。

## 觸發原因

LOC 拆分包解除 `tools/lib` 三支頂格檔（`quota_policy.py`／`schedule_backend.py`／
`sentinel_lifecycle.py`）解除 `guardrail_lib` LOC 分級頂格，各拆出一個子模組
（`quota_policy_env.py`／`schedule_backend_calendar.py`／`sentinel_lifecycle_arm.py`）。
`tools/lib` 掃描檔數由 40 升為 43，越過 `TestScanRootFloorBand` 的腐化上界 40（原下限
30 只還守得住 70% 掃描面），觸發 7 支測試紅（`test_no_unguarded_foreign_executable` 等）。

修法：`tools/tests/test_platform_neutral_paths.py::_scan_roots()` 的 `tools/lib` 下限
由 30 重釘為 41。

## 逐檔漂移（本輪）

| 檔案 | 舊值 | 新值 | 淨額 | 原因 |
|---|---|---|---|---|
| `test_bash32_compat.py` | 946 | 947 | +1 | DEF-101-941 修復把合併行拆回兩行以符合 `tools/tests/` 的 E501 存量債棘輪（`_E501_DEBT_CEILING=139`） |
| `test_platform_neutral_paths.py` | 6200 | 6196 | −4 | 新增 `tools/lib` 重釘註解 +11 行、同時壓縮 `_scan_roots()` 內 `tools`／`tools/lib` 兩段已過期的 R81/R85 逐輪史料註解 −15 行（僅壓縮陳述、未刪任何仍在生效的事實：R81/R85 的舊值與觸發原因保留在壓縮後的單行摘要內） |

淨額合計：−3。本檔（`test_adr_xplat001_c1c2_lock.py`）自身編修（新增本輪稽核列＋文件
指針）另佔 +3 行，與上列 −3 相抵，本輪第一次收斂淨額為 **0**（見下方〈第二次收斂〉節
——第二次收斂發生前，`_GUARD_LINES_REPIN_LOG` 表尾與 `_FROZEN_GUARD_LINES` 一度定格
於此，本檔刻意不重複複寫會過期的數字）。

## 第二次收斂——結構性減法（治本，非壓線湊零）

**觸發**：第一次收斂（上方）落地後，DEF-101-160 假鎖修復、DEF-200-160/148/163、
PRD 4.5.7/4.5.8 等後續修復陸續進場，其中一支 BSD regex 修復
（DEF-101-941：修正 `-w` 正則涵蓋 `-w0`／`--wrap`，並補 `_BAN_TOKEN_SAMPLES` 新樣本）
讓 `test_bash32_compat.py` 再增 +23 行（947→970）。這是本輪**第四次**功能性修復
撞上護欄層行數棘輪——前三次的處理方式都是在 `test_platform_neutral_paths.py::_scan_roots()`
附近找一行可壓縮的史料註解勉強打平淨額到 0（本檔上方〈逐檔漂移〉一列即為其中一次）。
Architect 三審精準點名這是結構性問題：「逐輪重釘的敘事不該住在被棘輪管轄的測試檔
本身……測試檔只留現值與一行指標，避免下一次真正的程式碼變更又得靠壓文件湊數」。

**修法**：不再壓縮單行文字湊零，改做真正的護欄層程式碼瘦身——把
`test_platform_neutral_paths.py` 內 **20 段**逐輪判準歷史敘事（`_scan_roots()` 的
三處修正 docstring，以及 R60/R69×3/R74/R76×2/R79×3/R80×2/R81/R82×3/naive-TS/
PowerShell 站點級／雙向注入矩陣／鐵律三證偽判準等各段「缺陷本體／判準設計取捨／
誠實劃界」中文散文）**原文一字不漏**搬到獨立證據文件
`docs/06_quality/CrossPlatform_Guard_Line_History.md`（純 Markdown，不在
`tools/tests/*.py` 護欄層行數棘輪的掃描面內）。測試檔本身只留：判準邏輯
（regex／AST／常數）＋一行指向該文件對應章節的指標。

**淨額**：`test_platform_neutral_paths.py` 6196→5724（**-472** 行，史料原文完整保存於
`CrossPlatform_Guard_Line_History.md`，只是換位置不是刪減）；`test_bash32_compat.py`
947→970（**+23**，DEF-101-941 的功能性修復，未動此檔一行）；`test_adr_xplat001_c1c2_lock.py`
5353→5363（**+10**，本檔自身為記錄這兩列重釘稽核痕跡而增加，同 R95～R97 既有的
「同輪追加」自我記帳體例，見 `_GUARD_LINES_REPIN_LOG` 表尾兩列）。三者相抵，本輪
總淨額 **-439**（85687→85248），是本輪第一次真正的「實質餘裕」而非壓線打平——足以
吸收未來數輪同等規模的功能性修復而不必再靠壓縮文字過關。

<!-- guard-total:R98 --> 護欄層累積總量現值 **85687 → 85248（-439）**；逐檔清單見
上方〈逐檔漂移〉表（第一次收斂）與本節（第二次收斂：`test_platform_neutral_paths.py`
-472／`test_bash32_compat.py` +23／`test_adr_xplat001_c1c2_lock.py` 自身追加 +10）。

## 為何選擇「壓縮舊史料」而非只承受淨增（第一次收斂的既有理由，仍成立）

`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2`：R96（+407）／R97（+881）已連兩輪淨額為正，
R98 若再正即觸發 `[只升不降]`（`repin_growth_problems()`）。合法出口是本輪淨額 ≤ 0，
而 `_scan_roots()` 內兩段歷史重釘的逐輪敘事（R81／R85）在 R98 重釘落地後已是可壓縮的
史料——目前值與觸發原因仍完整保留，只是不再用原本的多行敘事體，故第一次收斂選擇
壓縮既有文字換取淨額。第二次收斂（上方）把同一個原則做得更徹底：不只壓縮兩段，
而是把整檔可搬遷的敘事一次搬完，換取遠大於單輪需求的餘裕。
