# R118 收尾單人窗口 — 護欄層淨額收斂證據檔

- **輪籤**：R118（收尾單人窗口，唯一在工作的包；四方複審已收，其他包全部停工）
- **範圍**：接手 P1-5（DEF-200-212 `check_handoff_carriers.py` strict 接線＋具名豁免）
  已落地未 commit 的工作樹，逐項收斂四方複審 blocking（C1/C2/C3）並完成本輪守衛線重釘。

## §1 交付逐項

### C1（Architect blocking）：`check_handoff_carriers.py:387` 出口散文訂正

`carrier_doc_problems()` 印給操作者看的出口指引原文只講「補一列帳本，不需豁免名單」，
而該函式現在正靠 `_CARRIER_DOC_EXEMPTIONS`（DEF-200-212 D4 裁決）運作，會誤導維護者。
訂正為兩條出口並點出時鐘凍結前提：①補帳本列指名 DEF-ID（射程判準＝目標輪 ≥ 當前輪）；
②若目標輪與 DEF-ID 已是塵封史料，依 D4 裁決登記進 `_CARRIER_DOC_EXEMPTIONS`（shrink-only，
不改寫歷史文件）。實測：`--self-test` 21 項全 PASS、rc=0；LOC 閘門 rc=0。生產檔，不進
守衛線淨額。

### C2（SD blocking，Architect 獨立命中同一筆）：檢查表節內判準的 vacuous 回歸缺口

`tools/tests/test_doc_loc_baseline_freshness_r60.py` 的 `dispatch_checklist_problems()`
現行邏輯正確（先切〈並行派工防互踩檢查表〉節、再逐詞驗證節內），但既有三支回歸測試對
「退化回全檔字串搜尋」（＝首版 vacuous bug）全部恆綠：
`test_the_real_claude_md_carries_the_checklist` 真 CLAUDE.md 節外也有四個詞、
`test_a_missing_section_is_red` 語料連標題都沒有、`test_a_missing_term_is_red_and_names_the_term`
節外完全沒有文字可撿。三者都測不出「切節有沒有真的生效」。

補一支 `test_a_term_present_only_outside_the_section_is_still_red`：語料把「收尾單人窗口」
只放在節**外**（節內只留另外三個詞），退化版必須仍判紅。

**突變驗紅**（把 `dispatch_checklist_problems()` 的 `section = tail.split(...)` 暫改成
`section = claude_md_text`，退化成全檔搜尋）：

```
test_a_term_present_only_outside_the_section_is_still_red ... FAIL
AssertionError: False is not true : []
Ran 4 tests in 0.002s
FAILED (failures=1)
```

只有新測試失敗，另外三支既有測試依然 `ok`——證實它們對這個退化恆綠、新測試是唯一有
鑑別力的一支。用 Edit 改回原判準（`section = tail.split("\n#", 1)[0]`）後複跑：

```
Ran 4 tests in 0.000s
OK
```

### C3（記帳誠實度，SA 棒建議，主控採納）：exemption 守欄測試歸軌

`test_the_exemption_registry_stays_within_its_shrink_only_cap`（9 行）驗的是掌舵者 D4
裁決逐字指定的「shrink-only」要件；`test_every_exemption_reason_meets_the_minimum_length`
（7 行）同樣驗證同一守欄機制（理由長度門檻）的既有不變式，非新增使用者可見能力。兩者
合計 16 行，主控裁決一併歸回歸鎖軌（`_REGRESSION_LANE_LOG` 追加 R118 列）。

## §2 史料搬遷抵銷（步驟 2 的減法）

`tools/tests/test_check_defect_log_crossref.py` 九支 class-level docstring（皆為 Rule 9
「意圖」敘事，非判準邏輯本體；判準邏輯留在方法層 docstring 與程式碼本身未動）原文一字
不漏搬至 `docs/06_quality/CrossPlatform_Guard_Line_History.md`〈test_check_defect_log_
crossref.py 類級 docstring 沿革搬遷（R118）〉節，測試檔原處只留兩行指標：

| 類別 | 原文行數 |
|---|---|
| `TestArchiveRequiredProblems` | 25 |
| `TestR82SealedHistoryPrefix` | 20 |
| `TestStatusFirstWordProblems` | 19 |
| `TestR82ComplexReviewSealTableIntegrity` | 19 |
| `TestAdrClosureClaimsAreMechanicallyChecked` | 14 |
| `TestUnpinnedHandoverAndStaleGrandfather` | 13 |
| `TestRowArityAndHeaderAnchoredStatusColumn` | 12 |
| `TestR82RatchetDirectionLock` | 12 |
| `TestGovernanceDocOversizeGuard` | 9 |
| `TestEveryLegalFirstWordIsClassifiable` | 12 |
| `TestVagueBucketCountingStillWorksWhenReached` | 8 |
| `TestClosingRoundProblemsWiring` | 12 |
| `TestSpecDocShellCommandsAreZshSafe` | 8 |
| `TestR79RowByteCeiling` | 8 |
| `TestFamilyHeaderUniformity` | 9 |
| `TestEvidenceFamilyPointersResolve` | 9 |
| `TestCrossRowReassignMustAlsoNameAFreshRound` | 9 |

（十七支合計，分四批搬遷：批① 9 支 -125／批② 3 支 -26／批③ 2 支 -12／批④ 3 支 -21，
合計 -184。分批理由＝守衛線本身也是自我指涉棘輪，每批搬完都要覆核 `--print-guard-lines`
現況才知道還差多少，而非一次到位算好。）

搬遷紀律：只搬史料（Rule 9 意圖敘事、當年怎麼發現的），不搬判準；原處留的兩行指標寫得出
「去哪裡看」；未動任何仍在承重的斷言。移除只涉及 docstring 文字，未觸及任何測試方法、
斷言或程式邏輯——複跑該檔全套（538 tests，含 `test_doc_loc_baseline_freshness_r60.py`
同批）rc=0、`Ran 538 tests ... OK` 為證。

## §3 淨額記帳（`--print-guard-lines` 逐次覆核，最終收斂 0 drift）

主表 `_GUARD_LINES_REPIN_LOG` 本輪七列（`("R118", …)`：落地列＋本表自身編修列＋四批
搬遷列），累積：

```
91253 → 91247（-6）
```

逐檔漂移最終覆核（0 drift）：

```
# 淨額 91247→91247 (+0)
# 逐檔漂移 0 支
```

- `test_check_defect_log_crossref.py`：3906 → 3851（P1-5 落地 +129、十七支 docstring
  搬遷 -184，淨 -55）
- `test_doc_loc_baseline_freshness_r60.py`：7114 → 7126（+12，C2 回歸鎖落地）
- `test_adr_xplat001_c1c2_lock.py`：7085 → 7122→7119（本表自身重釘儀式，多輪「同輪
  追加」收斂：七列稽核痕跡 ＋ `_REGRESSION_LANE_LOG` 一列 ＋ `_FROZEN_PREFIX_REWRITE_
  LEDGER` 一列 ＋ 凍結表／prefix_len／sha 值更新）

回歸鎖軌 `_REGRESSION_LANE_LOG` 本輪申報 **16**（C3 兩支守欄不變式測試的完整誠實值：
`test_the_exemption_registry_stays_within_its_shrink_only_cap` 9 行 ＋
`test_every_exemption_reason_meets_the_minimum_length` 7 行）。

**主表淨額 raw 已是 -6（≤0），本輪功能軌與回歸鎖軌的算術關係不再是決定性因素**——
`repin_growth_problems(_GUARD_LINES_REPIN_LOG)`（不帶 `regression_lane` 參數，真倉庫
綠側對照組）與 `repin_log_problems(..., regression_lane=_REGRESSION_LANE_LOG)`（帶
lane 的完整判準）兩條路徑皆已對真表覆核 rc=0。兌現款(11)（`_REPIN_MAX_CONSECUTIVE_
RISING_ROUNDS=2`：R116(+573+4)／R117(+289+43) 兩輪皆正，R118 raw -6 終止連續上升）。

## §4 真因鏈（DEF-200-212 結案的真因，非表面症狀）

1. `check_defect_log_crossref.current_round()` 讀帳本「發現情境」欄的最大 `R\d+` 值。
2. 該欄的紀律是**零輪號**（時鐘凍結），實測凍結在 **R100**。
3. `carrier_doc_problems()` 的判準射程是「目標輪 ≥ 當前輪 ⇒ 未出局」，前提是當前輪會
   隨真實輪次前進；時鐘凍結後這個前提不成立，「自動祖父化」永不發生。
4. 三筆歷史交接文件（`R102_HANDOFF.md`／`CrossPlatform_R100_Scan_Findings.md`／
   `CrossPlatform_R107_Ledger_Closure.md`）的前瞻交棒行因此永遠卡在假陽性，儘管其
   目標輪與指名 DEF-ID 皆早已在後續輪次結案。
5. 掌舵者 D4 裁決：改走**具名豁免面工程解**——`_CARRIER_DOC_EXEMPTIONS`（鍵＝(檔案相對
   路徑, DEF-ID)，shrink-only，MAX_ENTRIES=3），不改寫歷史文件本身，豁免只在精確相符
   時生效（同檔其他未登記前瞻行仍照判，非整檔放行）。
6. P1-5 落地：strict 路徑（`unresolved_only=True`）已接進 `main()`；三筆歷史假陽性由
   具名豁免面歸零；`--self-test` 與 `TestDef200212*` 系列紅綠自證。

## §4b 帳本結案本身被同型衝突擋下（誠實記錄，未結案，交主控裁決）

🔴 原步驟 5 指示把 DEF-200-212 列狀態欄改為結案（`fixed@R118`）。實作後親跑 `python
tools/check_handoff_carriers.py` 發現：把該列改為 `fixed` 會讓它離開 `ledger_def_ids
(unresolved_only=True)` 的未結集合，而 `docs/04_planning/R113_HANDOFF.md`（:8、:18）與
`docs/06_quality/CrossPlatform_R113_Ledger_Closure.md`（:44、:116）四行舊文件皆以「交由
R114」句型指名 DEF-200-212——這四行立刻變成與 §4 描述的三筆歷史假陽性**同型**的第四、
第五筆假陽性（(檔案, DEF-ID) 唯一鍵僅 2 筆：R113_HANDOFF.md 與 CrossPlatform_R113_
Ledger_Closure.md 各自涵蓋自己的兩行）。

修法本應是依 D4 裁決模式登記進 `_CARRIER_DOC_EXEMPTIONS`，但主控任務書步驟 4 明文：
「🔴 禁止調高任何 cap 類常數（…／`_CARRIER_DOC_EXEMPTIONS_MAX_ENTRIES` 一律只准調小）」
——現值 3、已滿載，登記 2 筆新豁免需要調高至 5，直接牴觸此明文禁令。改寫 R113 兩份歷史
文件本身則牴觸 D4 機制「不改寫歷史文件」的設計原則。三條路都走不通，故**不強行結案**：
DEF-200-212 保留 `open（承接輪次：R119）`，狀態欄如實記錄「程式碼已完工、結案被擋」，
三支文件閘門複跑皆 rc=0（見 §6）。這是需要主控／掌舵者裁決的新發現（暫稱候選 D5）：
①明確核准調高 `_CARRIER_DOC_EXEMPTIONS_MAX_ENTRIES` 3→5 並登記兩筆新豁免；或
②接受 DEF-200-212 暫留 open 直到帳本時鐘前進；或③另尋主控指定的第三案。

## §5 誠實紀錄的量測錯誤（本 repo 誠實紀律，逐筆記載）

- **實作包（P1-5 交件）宣稱**：`check_handoff_carriers.py` 行數「369→512」。經 SA 棒複審
  核算證偽：512 是用 `Measure-Object -Line`（不計空行）量出的數字；369 對不上任何量法。
  真值（`Get-Content .Count`，計入空行，與 `_FROZEN_GUARD_LINES` 的量法一致）＝
  HEAD 480 行 → 工作樹 591 行（`git diff --numstat` = `127 16`；480+127−16=591 對帳成立）。
  該檔是生產檔，不進守衛線淨額，本節僅記載量測錯誤本身以資誠實。
- **主控（本輪收尾窗口）自身的量測錯誤**：重釘儀式屬自我指涉棘輪（`test_adr_xplat001_
  c1c2_lock.py` 本身也在 `_FROZEN_GUARD_LINES` 掃描面內），每次編修這張表都會讓表自己
  的行數再長一點，需要多輪「同輪追加」才能收斂到 0 drift（本輪七列稽核痕跡即為此過程
  的逐步痕跡，非規劃失誤，是這道棘輪的結構性特徵——見 `_GUARD_LINES_REPIN_LOG` 既有
  R95~R117 諸列同型「[同輪追加]」體例）。

## §6 三支文件閘門與全套測試

見交件回報本文（`docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-212 列與收尾回報）逐項
rc；本檔僅承載逐檔清單與必要性辯護，量化判決數字以當回合實跑輸出為準，不在此複寫。
