# R118 收尾單人窗口交棒書

- **輪籤**：R118（收尾單人窗口，四方複審已收，其他包全部停工）
- **範圍**：接手 P1-5（DEF-200-212）已落地未 commit 的工作樹，收斂四方複審 C1/C2/C3，
  完成守衛線重釘。詳見 `docs/06_quality/CrossPlatform_R118_Debt_Closure.md`。

## 本輪摘要

1. **C1**：`check_handoff_carriers.py:387` 出口散文訂正（生產檔，不進守衛線）。
2. **C2**：`test_doc_loc_baseline_freshness_r60.py` 補回歸鎖
   `test_a_term_present_only_outside_the_section_is_still_red`（突變注入驗紅、Edit 改回）。
3. **C3**：exemption 守欄不變式兩支測試（16 行）歸回歸鎖軌。
4. 史料搬遷抵銷：`test_check_defect_log_crossref.py` 十七支 class-level docstring
   分四批搬至 `CrossPlatform_Guard_Line_History.md`。
5. **DEF-200-212 帳本結案被擋（新發現，交主控裁決）**：程式碼已完工，但把狀態欄改
   `fixed` 會讓 `R113_HANDOFF.md`／`CrossPlatform_R113_Ledger_Closure.md` 四行舊「交由
   R114」引用變成新的假陽性，而登記豁免需調高 `_CARRIER_DOC_EXEMPTIONS_MAX_ENTRIES`
   3→5，牴觸本輪明文禁令。故保留 `open（承接輪次：R119）`。詳見 §4b。

<!-- guard-total:R118 --> **守衛線追記：護欄層累積淨額＝ 91253 → 91247（-6）** ——
raw 主表淨額已 ≤0（十七支 docstring 分四批搬遷抵銷 -184，超過落地新增量），兌現款(11)
（終止 R116/R117 連兩輪上升）；另 16 行守欄不變式測試記帳歸回歸鎖軌（記帳誠實度）。
逐項見 `docs/06_quality/CrossPlatform_R118_Debt_Closure.md`。

## 已驗證（主控親跑，非轉述）

- 全套根層：`python tools/run_root_unittests.py` ⇒ `Ran 3849 tests in 695.742s`／
  `OK (skipped=42)`／rc=0。
- 三支文件閘門各自 rc=0：`check_defect_log_crossref.py`／`check_archive_required.py`／
  `check_handoff_carriers.py`。
- 守衛線：`test_adr_xplat001_c1c2_lock.py --print-guard-lines` ⇒ 淨額 91247→91247（+0）、
  逐檔漂移 0 支。
- 行數量法訂正（本輪踩過的坑）：`Measure-Object -Line` **不計空行**，量真行數要用
  `(Get-Content).Count`。`check_handoff_carriers.py` 真值＝HEAD 480 → 工作樹 591
  （`git diff --numstat` 127/16 對帳成立）；實作包交件所報的 369 經核算證偽，勿引用。

## 還沒做的（不塗綠）

1. **DEF-200-212 仍未結案**——本輪唯一未達成的目標。程式碼全部完工，卡在帳本結案這個
   動作本身：主控純函式探針實測，把該列狀態欄換成結案字面後，判準② 新增 **4 行**假陽性
   （`R113_HANDOFF.md` 兩行、`CrossPlatform_R113_Ledger_Closure.md` 兩行，皆指名
   `DEF-200-212` 自己）⇒ 需 2 筆新豁免鍵，而 `_CARRIER_DOC_EXEMPTIONS_MAX_ENTRIES`
   滿載於 3 且裁決 D4 明令 shrink-only。現查
   `git grep -n "DEF-200-212" docs/06_quality/AutoSDD_Defect_Log.md`
   （狀態欄仍是未結字面＝仍未結案）。
2. **P1-6 尚未實作**（本輪改為規格形式交下一投續作，見下節）。現查
   `git grep -rn "skip_id_ledger" tools/tests/`（零命中＝共同變更鎖仍未落地）。
   <!-- absent-if: def test_skip_ledger_co_change -->
3. **P1-7 的 SD-4 面仍未接線**（無主模式處置面 cap 收斂）。現查
   `git grep -n "cap_prepare" tools/lib/quota_escalation.py`（零命中＝仍未接）。
4. **P1-8 盤點仍未進行**（Pacing／BurnDown 落款後與現行實作的逐條差異）。現查
   `git grep -n "已由實作超越" docs/04_planning/PRD_Amendment_R108_Pacing.md`
   （零命中＝仍未盤點）。

## 下一投的起點：P1-6（規格已備，勿重新偵察）

P1-6 原字面「四層登記收斂為單一 SSOT 派生」**經查證否決**——`test_skip_ceiling_ratchet_
direction.py` 檔頭載明 DEF-200-160 二審：層③ 一旦從層② 派生就與現值恆等，方向鎖
structurally 不可能觸發（當時 QA 把某格改成 999 重跑，全數通過）。同理 `skip_group_
policy.py:501-503` 自陳層② 也不得由層① 推導。四層座標與可行形態評估：

| 層 | 位置 | 語意 |
|---|---|---|
| ① census 主表 | `tools/lib/skip_group_policy.py` `_RUNTIME_SKIP_CEILING` | 剖面→分群→**上限**（非等值落款） |
| ② MAX 表 | 同檔 `_RUNTIME_SKIP_CEILING_MAX` | 天花板（只准降） |
| ③ 凍結快照 | `tools/tests/test_skip_ceiling_ratchet_direction.py` `_FROZEN_CEILING_MAX` | 層② 的方向鎖 |
| ④ M6 落款 | `docs/06_quality/skip_id_ledger.json` | test-id **集合**，與①②③ 正交 |

- 已否決形態：任何派生方案（重演 DEF-200-160）；「① 總和 vs ④ 列表長度」靜態互查
  （主控實測：判準是 `total_got > total_cap` 的上限語意，漏補只會讓 ④ 更小 ⇒ 對目標
  痛點**恆綠**）。
- 建議形態＝**共同變更鎖**：本次變更動了層① 的某剖面鍵值時，`skip_id_ledger.json`
  對應 profile 也必須在同一次變更中被動過。誠實劃界：擋不到「兩邊都改了但④改錯」。
  動工前必做的證偽：以 commit `7f8c96a` 的工作樹狀態重演，該鎖必須紅——不做這一步
  就不知道它有沒有牙。
- 另註：新增**全新平台標籤類別**還有第五、六座標（`skip_tag_policy.py` 標籤常數、
  `skip_group_policy.py` `_TAG_HOME_PLATFORMS` 映射）；現行標籤只有 Windows／POSIX／MAC
  三種，無 linux 專屬（主控現查）。

## 呈報主控／掌舵者的裁決件

DEF-200-212 結案死結（見〈沒做到的〉第 1 項）。根因是兩條各自正確的紀律相乘：
帳本時鐘凍結（`AutoSDD_Adjudication_Record_R110.md` 第 3 節：「提前寫入未來輪號會移動
全帳本的判準基準」）使祖父化永不觸發 ⇒ 歷史前瞻行只能逐筆進豁免表；而 D4 的
shrink-only 禁止豁免表增長。三個候選：①一次性核准上限 3→5 並同步立案根因；
②接受暫留 open（則該列在時鐘解凍前結構上不可結案）；③改判準語意以區分
「已完成」與「無人接手」（主控分析：此路等同退回 lenient，會使 DEF-200-212 的原始
立案失效，不建議）。
