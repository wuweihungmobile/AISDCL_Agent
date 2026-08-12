# CrossPlatform_R86_Scan_Findings — 本輪掃描發現（護欄層分桶包）

> 🔴 **本檔目前只含 Arch/分桶 包的發現**。它是本輪 `CrossPlatform_R*_Scan_Findings.md` 這個
> 慣例位置的第一個寫入者；其他包的發現請**附加**，不要覆寫。建立它的直接理由是機械的：
> `doc_guard_total_problems()` 款(1) 要求本輪累積淨額在**兩個**站點寫得出來
> （掃描面＝`AutoSDD_improving_*.md`／`CrossPlatform_R*_Scan_Findings.md`／`R*_HANDOFF.md`），
> 而本輪交棒書尚未產出。
> 🔴 **曾經走過的另一條路與它的代價（誠實記錄）**：我第一版把第二個站點放在自建的
> `R86_HANDOFF.md` 種子檔，實測**當場多兩筆紅**——`TestR78HandoffClaimsCarryLiveCommands`
> 的兩向（「最新一份交棒書必須收得到 stale 宣稱」「必須帶自己的下限」）對一份只有護欄層
> 一節的種子檔零射程。⇒ 半成品交棒書比沒有交棒書更糟：它會讓一批只有收輪者滿足得了的鎖
> 提早生效。該檔已刪除，第二個站點改回本檔這個慣例位置。

---

## F-1 護欄層累積淨額（訴求 2 的到期義務）

<!-- guard-total:R86 --> **本輪護欄層累積淨額＝ 83475 → 83470（−5）** —— 🔴 **`_NET_SUBTRACTION_DUE_ROUND` 的到期輪，也是 `_GUARD_LINES_REPIN_LOG` 歷來第一個淨額 < 0 的輪次**（R77~R85 每一列都是上升）。手段是棘輪 `[歷史變短]` 那一款自己指定的出口：史前列（R77~R80 全段）整列搬出、R81~R85 各列理由欄壓成索引、宣稱判準鎖的模組層立案敘事搬出；原文逐字全數落在 `docs/06_quality/CrossPlatform_R86_Guard_Repin_Evidence.md` §A/§B/§C，一字未刪。🔴 **誠實劃界：這是量測面內的減法，不是總量的減法**——行從 `tools/tests/*.py`（棘輪的量測面）搬到 `docs/`，棘輪的數字變好而「護欄層＋文件」的總體積一行都沒有少。`[收尾單人窗口、全包停工後當回合實測；憑證＝tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines 印 (+0) 且逐檔漂移 0 支]`

逐項出口與行數見 `docs/06_quality/CrossPlatform_R86_Guard_Repin_Evidence.md`。

## F-2 上一輪「分桶比例」的結論不可複現（駁回 R85 交棒書自稱的最有價值洞見）

以上一輪的桶集重跑（無 `root_infra` 桶、production 優先）得 production 24.5%／sdd 43.2%／
prose 23.0%／guard_self 7.1%——**與它自報的那組沒有一格對得上**，且該輪未留判準 ⇒
「同樣的方法」結構上無從複製（同 `DEF-200-046` 判例）。而**只要補上一個合法缺席的桶**
（`root_infra`＝守根層基礎設施**程式碼**的鎖），prose 的 first-match 佔比就由 23.0% 掉到
0.7%（檔級）／6.1%（chunk 級）⇒ 「48.2% 的護欄層在守散文與守自己」是桶集缺一格加上
first-match 優先序造成的假象，**不得再引用**。可重跑載具＝`tools/probe/guard_layer_bucket_census.py`。

## F-3 檔級歸屬在護欄層結構上失效（分桶棘輪為何必須切到 chunk 粒度）

本層鎖檔絕大多數同時參照 `root_infra`、`guard_self`、`prose` 三棵樹 ⇒ 「只參照一棵樹」的
`exclusive` 歸屬在**檔級**對 prose 桶回零行，任何檔級 shrink-only 判準都會是恆真的裝飾。
⇒ 棘輪吃的是**頂層 class／def 逐塊**的粒度（`GUARD_BUCKET_RATCHET_BASIS`），
且 probe 的預設粒度由消費端測試與它雙向釘住。

## F-4 分桶抽取器曾有**死條目**：以點開頭的樹前綴永遠抓不到

`BUCKET_TREES` 登記了 `.claude/hooks/`／`.claude/settings.json`／`.github/workflows/`，
而 token 抽取器要求 token 以英數起頭 ⇒ 那三筆**結構上永遠不命中**，`root_infra` 桶被系統性
低報，落在該族的鎖檔被誤丟進 `prose`／`selfcontained`。實測命中：宣稱判準鎖的模組層敘事
被判成**純散文 60 行**，而它第一句就指名 `.claude/hooks/check_claim_provenance.py`。
🔴 **這個缺陷是被分桶棘輪自己抓出來的**——它對本輪的搬家動作報了一筆 `[分桶成長] prose +60`，
逐單元追查才發現成因不是真的長了散文，是分類器瞎了一族。修正後 prose 由 4464 降到 4119、
`root_infra` 由 8308 升到 10025。缺口已上機械物：`dead_tree_prefixes()`（登記卻抓不到即紅）。

## F-5 `_bail` 第二個家：本輪**實測後刻意不併**

`tools/run_root_unittests.py::_bail` 與 `tools/check_defect_log_crossref.py::_bail` 同名同意圖、
簽章與語意不同（前者說「一支測試都沒執行」、後者說「還有哪幾道沒跑」）。併家的實測阻礙：
① `check_loc_budget --json` 實測 `run_root_unittests.py` loc=754／budget=754／**餘裕 0**、
`check_defect_log_crossref.py` loc=1469／budget=1474／**餘裕 5**——共用家與登記表都加不下；
② 既有鎖 `TestEarlyExitAnnouncesUnrunChecks` 的**自陳射程**逐字寫著「只管
`check_defect_log_crossref.py` 這一支工具的檢查序…那需要一套跨工具的檢查序模型，本鎖不假裝有」；
③ `_bail_headers_in_main_order()`／`_main_source()` 硬綁單一模組 ⇒ 擴面＝在 `tools/tests/`
**淨增**。⇒ 依「若併家反而要新增鎖就不要做」的判準，本輪不做，具名交棒 R87。
