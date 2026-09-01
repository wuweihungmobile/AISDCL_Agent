# CrossPlatform R116 落地紀錄 — ADR-XPLAT-013 Phase 2 (b)(c) 分軌計價（DEF-200-211）

> 本輪＝單人窗口實作批，承接裁決 `AutoSDD_Adjudication_Record_R110.md` §1.4
> D-1~D-6（`ADR-XPLAT-013_Phase2_Proposal_R108.md` 的六題需裁決項）。本檔是
> 護欄層重釘稽核痕跡（`_GUARD_LINES_REPIN_LOG` "R116" 那一列）指名的逐檔清單家，
> 也是四方複審交件的索引。

## 逐檔行數異動

<!-- guard-total:R116 --> **護欄層累積淨額（`--print-guard-lines` 現查）：90344 → 90921（+577，含 Architect 鏡一審承接補釘 +4＝A-1 三行 E501 縮短、A-2 到期輪 lookahead 後設鎖、N-1 cap_basis 失蹤兜底，散文壓縮抵銷後貼 cap(116)=577）**

<!-- guard-total:R117 --> **P1-2/P1-3 喚醒鏈批（同 session 第二批）：90921 → 91210（+289）**——`test_context_budget_guard.py` 9371→9645（+274＝落款驗收回歸鎖 238〔申報 `_REGRESSION_LANE_LOG` 回歸鎖軌＝分軌第一次實戰消費〕＋複審承接測試 36〔Architect A-2 unmeasurable 保標記＋SD-1 節流專屬常數多巡驗證〕）＋`test_adr_xplat001_c1c2_lock.py` 7064→7079（+15，稽核列與儀式行自身）；功能軌合計 +51 ≤ cap(117)=570；同輪兌現款(12)＝`(117, 570)`＋重新武裝 119/564。

| 檔案 | 落地前 | 落地後 | 淨額 | 內容 |
|---|---:|---:|---:|---|
| `tools/tests/test_adr_xplat001_c1c2_lock.py` | 6490 | 7064 | +574 | 本輪全部新增判準本體（見下方逐項）＋本稽核列自身＋四方複審承接補釘 +4（A-2 lookahead 後設鎖／SD-1 款 3 邊界測試等，散文壓縮抵銷後淨 +4——Q-2 勘誤：原 7060 為補釘前快照） |
| `tools/tests/test_archive_defect_log.py` | 3986 | 3989 | +3 | D-3：既有 3 處 `exec(compile(...))` 慣用句補 `# noqa: S102` 理由註解（DEF-200-217 E2） |

合法出口逐條實查：刪死碼不適用（新增皆為此前不存在的判準面，無等量舊邏輯可退場）；
抽共用層不適用（(b)(c) 各自只有一個消費端）；散文搬遷不適用（新增全是判準本體、常數與
注入語料，本輪未新增可搬遷的存量史料段落）。

## D-1（S-2）：回歸鎖軌／功能軌分軌計價

- 新平行表 `_REGRESSION_LANE_LOG`（空表起始，`_REGRESSION_LANE_SINCE=117`，不追溯）。
- `lane_split_problems()` 六款（§5.1 五款＋延伸款 `[生效前宣告]`，見該函式 docstring）。
- `repin_growth_problems()` 擴 `regression_lane`／`regression_lane_since` 兩個可注入
  參數：傳空／不傳時行為與分軌前逐字相同（§5.2 機械自證）；傳入時款(10)(11) 判的淨額
  改為「主表淨額 − 同輪回歸鎖軌淨額（僅 `no >= regression_lane_since`）」。
- 生產閘門 `test_the_repin_log_accounts_for_the_frozen_table` 已改傳
  `regression_lane=_REGRESSION_LANE_LOG`，使分軌機制真的接上生產判準，不是裝飾函式。
- `TestRegressionLaneSplit`：六款逐款突變驗紅＋復原轉綠、§5.2 三支機械自證測試
  （不放寬功能軌／落地輪不得自我豁免／cap 來自實測）、四支對抗性探針（含探針②
  `exec(__doc__)` 誠實記為已知缺口，非通過項）。

## D-2：M1 拆雙指標

- `docs/06_quality/CrossPlatform_Maturity_Criteria.md` M1 討論段新增 R116 訂正段：
  既有門檻（總量連續三輪不上升）**一字不動**；另增觀察用第二指標——功能軌淨額連續
  三輪不上升，現查載具＝`repin_growth_problems(_GUARD_LINES_REPIN_LOG,
  regression_lane=_REGRESSION_LANE_LOG)` 的 `[只升不降]` 款。
- `TestM1ThresholdIsAConjunction` 全數複跑仍綠，證明既有門檻文字未被改動。

## D-3：ruff S102 接 `.claude/hooks/`／`tools/`／`AutoClaude/`

- `tools/ruff.toml`、`AutoClaude/pyproject.toml` 同步加選 `S102`（只選這一條字面，不選
  整個 `S` 家族）。落地前現查：`ruff check --extend-select S102 tools/ .claude/hooks/`
  三筆命中皆在 `test_archive_defect_log.py`（既有 compile+exec 慣用句，已補
  `# noqa: S102`）；`AutoClaude/` 側 `ruff check --select S102 .` 零命中。
- `DEF-200-209`（U5）與 `DEF-200-217` E2 兩軸皆已收（帳本已更新）。

## D-4：(c) 降級為觀測欄

- 新函式 `guard_line_composition()`（AST 掃 `def test*` 函式數／assert 呼叫數，逐檔
  回傳），`_print_guard_lines()` 追加一行 `[觀測欄][D-4]` 印總計，**只印不擋**。
- `TestObservationColumnsAreDisplayOnly` 反 vacuity：AST 掃全檔，任何 `*_problems()`
  判準函式原始碼皆不得引用 `guard_line_composition`。
- `_PHASE2_REVIEW_LOG` 追加 `(116, "[落地]", ...)`，`_PHASE2_DUE_ROUND` 重新武裝至 121。

## D-5：U6／U7／U9

- **U6（已收）**：三個 `*_WARN_MARGIN` 門檻（10/6/5）核准維持現值，母體實測
  `tier_warn_band=0`／`special_warn_band=7`／`root_tools_warn_band=2` 筆。
- **U7（方針已定，落地未完成）**：§8 交棒清單處置方針改為「逐一改寫」（推翻原「刻意
  不逐一改寫」）。25 個自陳站點中僅原有 2 列已訂正，其餘 23 個**本輪未做**，交下一
  收尾單人窗口。
- **U9（到期輪常數已落地，真拆未做）**：新常數 `_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND
  =121` ＋ `_ROOT_TOOLS_OLD_SCALE_DEBT_RESOLVED=False` ＋ `root_tools_debt_due_
  problems()`（`TestRootToolsOldScaleDebtDueRound` 四格）。R116 現查舊尺 over_by
  合計 **187**（`quota_meter.py` 67／`session_resume_planner.py` 45／
  `hook_wiring.py` 28／`quota_gate.py` 47），四支檔本輪**一行未動**。

## D-6：回歸鎖軌上限實測取值

- `_REGRESSION_LANE_ROUND_CAP = 309`（＝`_FROZEN_REGRESSION_LANE_ROUND_CAP`，落地輪
  凍結基準與現值相等），取值基準＝`_regression_lane_cap_basis()` 回傳的 R97 那一列
  （+309，逐項算術驗證：`worktree_paths.py +103 + failure_log_rotation.py +81 +
  skip_ceiling_ratchet_direction.py +107 + block_destructive_git_r83.py +18 = 309`）。
  禁沿用 R108 提案的舊快照 287。

## 未做事項（誠實列出，交下一收尾單人窗口）

1. U7：25 個自陳站點中 23 個尚未逐一改寫。
2. U9：四支 `[ROOT-TOOLS]` 檔真拆到舊尺不破線（目標 −187 行，到期輪 R121）。
3. U1~U4：Architect/SA/SD/QA 獨立審查尚未進行（ADR 轉 Accepted 的前置）。
4. 候選 2（C1~C4）全自動分類器的真實 diff 假紅普查（ADR-XPLAT-013_Phase2_Proposal_
   R108.md §4 item 2 已誠實登記為射程外）。
