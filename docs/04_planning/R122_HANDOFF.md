# R122 交棒書（技術債總清償循環令第五投；精準修復輪）

- **輪籤**：R122
- **主線**：掌舵者裁「全力降帳本至 0」＋純結案輪三訣竅。起手分診後**前提被事實推翻**
  （帳本 44 筆無一可在不動程式碼下結案），依循環令「先自行分析、做當下最佳判斷推進」轉為
  **精準修復輪**：挑方向已定、鎖持有面互不重疊的三筆逐筆修掉。
- **帳本**：未結列 **44 → 41**（三筆皆 `fixed`，非 `closed-by-decision`）。
- **護欄層**：<!-- guard-total:R122 --> 行數 `91793→91668`（淨額 −125）⇒ 款(11) 連續上升
  streak 歸零。逐列與逐檔清單＝`docs/06_quality/CrossPlatform_R122_Scan_Findings.md` §1。

## 本輪已落地

1. **DEF-200-169 fixed**：扇出視窗剩餘秒數三層落地（取數 `quota_ledger.oldest_dispatch`
   → 邏輯 `quota_gate.fanout_window_left` → 渲染 `quota_messages.fanout_window_line`），
   已接進 `--pace`。四個邊界態彼此不同形（空帳／超期／原語不可達皆不說「剩 0 秒」）。
   順帶複核出帳本所記卡點「`quota_gate.py` 500／500 餘裕 0」已過期，實測 391／500。
2. **DEF-200-170 fixed**：`MIN_TESTS` 保鮮判準改綁零相依沙箱餘裕軸（判準本體抽
   `tools/lib/min_tests_margin.py`）。**驗收核心是行為**——本輪全套實跑中該判準第一次真的
   先開口並直接帶出目標值，主控依其逐字指示重釘 `MIN_TESTS` 3767 → 3895。
3. **DEF-200-222 fixed**：①commit 期阻斷面縮到「staged 真的觸及帳本族」，取不到 staged 時
   維持阻斷＋fail-loud、不放行；②`--apply` 序列化走 `tools/lib/apply_lock.py` 的
   `O_CREAT`＋`O_EXCL` 目錄項鎖（避開本 repo 有實測前科的 `O_APPEND`／`msvcrt.locking`），
   上鎖入口＝`tools/archive_apply_locked.py`。併發以真執行緒＋barrier 驗、非 `Pool.map`。
4. **護欄層散文搬遷抵銷**：八支鎖檔的歷史沿革段落逐塊逐字保全搬至
   `docs/06_quality/CrossPlatform_R122_Guard_Prose_Migration.md`，換出款(10)(11) 所需額度。
5. **三筆同輪到期義務兌現**：`_REPIN_NET_CAP_SCHEDULE` 追加 `(122, 559)`／
   `_PHASE2_REVIEW_LOG` 追加 `[維持觀察]` 列／`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND`
   具名展延（理由逐字寫在該常數旁，判準明令不得靜默沿用）。

## 已驗證

- 帳本三支文件閘門：`check_defect_log_crossref.py` rc=0、`check_archive_required.py` rc=0、
  `check_handoff_carriers.py` rc=0。未結列數現查
  `python tools/check_defect_log_crossref.py --unresolved-count`。
- 守衛線 `--print-guard-lines`：淨額 `91668→91668 (+0)`、逐檔漂移 0 支（收斂）。
- `sync_onboarding_baselines.py --write` rc=0，回填 `{'tests': 3895}`。
- 全套 `run_root_unittests.py`：本輪第二次實跑 `Ran 3895 tests`，當時 4 個 FAIL 全屬守衛線
  棘輪待重釘；重釘後的最終全套結論見本檔〈還沒做〉節或收輪報表。
- 三個實作包各自的突變驗紅與針對測試綠＝`[他包回報]`，逐筆轉錄在
  `docs/06_quality/CrossPlatform_R122_Debt_Closure.md`。

## 還沒做（不塗綠）

1. **四方定點複審尚未執行**（循環令 §5 要求實作項過四方）
   <!-- absent-if: CrossPlatform_R122_Review -->——證偽錨＝四方複審結論的轉錄檔名（同
   R79／R80／R81 同名檔的既有體例）：那個字面一旦在任何 tracked 檔裡搜得到，本條宣稱即為
   假並當場轉紅。依成熟度判準 M3「作者自證不計分」，本輪全部改動屬自證，`MIN_TESTS` 3895
   亦屬中途值。現查本輪落地了哪幾個 commit：`git log --oneline -5`。
2. **帳本未結列仍未降到目標**：本輪 44→41，尚未接近循環令 §8 的 ≤30。分診判
   `needs-dev` 與 `needs-adjudication` 兩類的逐筆結論＝
   `docs/06_quality/CrossPlatform_R122_Debt_Closure.md` §0。現查現值：
   `python tools/check_defect_log_crossref.py --unresolved-count`。
3. **上一輪呈報單的降幅上界已測定為 0**：`AutoSDD_Adjudication_Packet_R121.md` 即使全數
   落款，主帳本未結列數也不會下降；該建議已撤回。現查那份呈報單今天的狀態字：
   `Select-String -Path docs/04_planning/AutoSDD_Adjudication_Packet_R121.md -Pattern "Status"`。
4. **搬遷面仍缺兩支最肥鎖檔的額度**：兩者因是別的機械物的逐字比對面而整檔排除，理由與
   逐筆 rejected 清單＝`docs/06_quality/CrossPlatform_R122_Guard_Prose_Migration.md`。
   現查今天還有多少額度：`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`。
5. **F1 途中發現尚未入帳本**：Stop 稽核器把 hook 的 non-blocking 提醒誤判為「載具失敗」，
   全文＝`docs/06_quality/CrossPlatform_R122_Scan_Findings.md` §2。入帳與否留給下一個
   結案窗口判斷。現查它有沒有被立列：
   `Select-String -Path docs/06_quality/AutoSDD_Defect_Log.md -Pattern "non-blocking"`。

## 下一步（下一個窗口二選一，掌舵者指定）

- **續降帳本（精準修復輪再一棒）**：讀 `docs/04_planning/AutoSDD_TechDebt_Paydown_Playbook.md`
  §A.1，挑標 `dev｜M｜高信心` 且鎖持有面互不重疊的下一批。🔴 **派工前必先為守衛線淨額做
  預算**——本輪的教訓是「加測試碼會撞款(10)(11)」，抵銷搬遷要與修復同批規劃，不是事後補。
- **補跑四方定點複審**：對本輪三筆修復＋搬遷做一審全查、二審驗修復；收斂標準＝四方無新
  blocking。

## 禁止事項

- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、push 不帶 `AUTOSDD_NET_RATCHET_OFF`。
- 不准為了讓護欄層轉綠而調高 `_REPIN_NET_CAP_SCHEDULE` 或
  `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`（兩者只准下修，調高是砸溫度計）。
- 不准自行加註 `_REPIN_APPROVED_ROUND_OVERAGE`（判準明令須四方複審核准）。
- 搬遷散文時不准動：豁免 token 行、docstring 摘要行、任何常數值與字串字面、任何自稱
  SSOT／唯一真相源的段落。判準與已驗證的安全邊界＝
  `docs/06_quality/CrossPlatform_R122_Guard_Prose_Migration.md` 檔頭。
- 結案 `closed-by-decision` 前必查「是否令他處前瞻交棒行失承接目標」（DEF-200-213 教訓）。
