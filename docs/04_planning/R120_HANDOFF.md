# R120 收尾單人窗口交棒書

- **輪籤**：R120（技術債總清償循環令第三投；收尾單人窗口）
- **範圍**：P1-7（SD-4／SD-8）落地 ＋ SA-4 實彈取證 ＋ P1-5/DEF-200-212 結案批（D8 裁決）
  ＋ P1-8 案檔盤點注與 R110 另案立列 ＋ 守衛線重釘。詳
  `docs/06_quality/CrossPlatform_R120_Debt_Closure.md`。
- **會話狀態**：撞額度 band=prepare（five_hour/session 90%，reset≈2026-09-02T04:09:59Z）。
  本交棒書即 prepare 帶要求的磁碟可重啟點。**session ID＝569b1d4c-512a-4933-9eab-628cd13d7b91**
  （reset 後 `claude -r 569b1d4c-512a-4933-9eab-628cd13d7b91` 續跑）。

## 本輪已落地（工作樹狀態見下方「重啟後第一件事」）

1. **P1-7 SD-4／SD-8**（`tools/lib/relay_machine.py`＋`tools/tests/test_context_budget_guard.py`）：
   實作棒自驗 12＋7 針對測試綠、整支 533 passed、六突變逐一驗紅後還原、ruff/LOC 綠。
2. **SA-4 實彈取證**：headless 窗口正面（`git status`／`Get-Date` 放行）＋負面（Write 攻 L3
   檔被拒、檔案零改動）；揪出 6 條 Write/NotebookEdit deny 死規則＝DEF-200-245。
3. **DEF-200-212 結案（D8）**：`_CARRIER_DOC_EXEMPTIONS` 上限 3→5＋2 筆豁免鍵；212→
   `fixed@R120`；根因立 DEF-200-241（承接 R121）。存證 `AutoSDD_Adjudication_Record_R120.md`。
4. **P1-8**：兩案檔盤點注＋Playbook Q3 同步＋R110 另案三筆立列（DEF-200-242/243/244）。
5. **守衛線重釘**：`test_context_budget_guard.py` 9645→9775（P1-7 +126、va3 +4）、
   本表自身三列合計 +21（sha 鏈 `_FROZEN_PREFIX_REWRITE_LEDGER` 追加 R120 列＋稽核）；
   `--print-guard-lines` 淨額 +0 逐檔漂移 0；sha 重釘 `31861e...`。款(11)：R120＝第 2
   連升（合規），**`R121` 必須 ≤0**。

<!-- guard-total:R120 --> **守衛線追記：護欄層累積淨額＝ 91646 → 91793（+147）** ——
逐項見 `docs/06_quality/CrossPlatform_R120_Debt_Closure.md` §5。

## 已驗證（主控親跑，非轉述）

- `check_handoff_carriers.py` rc=0；`--self-test` rc=0（27 行）。
- `check_defect_log_crossref.py` 帶 `AUTOSDD_NET_RATCHET_OFF=1` ⇒ rc=0（本輪＝P1 落地輪＋
  發現，D6 明文不計淨減；push 無需帶 env——淨額比 `git show HEAD` vs 工作樹，commit 後歸零）。
- `check_archive_required.py` rc=0。
- 帳本六列 byte 皆 ≤700（212=692／241=623／242=507／243=382／244=462／245=631）。
- `--print-guard-lines` 淨額 91785→91785（+0）、逐檔漂移 0。
- 全套 `run_root_unittests.py`：**背景跑中**（log＝scratchpad/r120_fullsuite.log），
  結果重啟後必須現查。

## 還沒做的（不塗綠）

1. **四方複審仍未進行**——被額度 band=prepare／halt 擋下（扇出工具不執行）；改逐個
   Agent 派或 reset 後補，收輪必要關卡（指令第 6 節）。現查
   `python tools/session_resume_planner.py --pace`（band 回 free 才並行派）。
2. **DEF-200-241 治本仍未著手**（時鐘前進機制／祖父化改讀結案事實，二擇一，過四方前不動碼）。
   現查 `git grep -n "DEF-200-241" docs/06_quality/AutoSDD_Defect_Log.md`（狀態欄 open＝根因仍在）。
3. **DEF-200-242／243／244（P1-8 R110 另案三列）仍未著手**。現查
   `git grep -n "DEF-200-242" docs/06_quality/AutoSDD_Defect_Log.md`（狀態欄 open）。

## 重啟後第一件事（zero-trust，不採信上方任何「已通過」宣稱）

1. 現查全套結論：`Get-Content <scratchpad>\r120_fullsuite.log -Tail 30`（找 `run_root rc=`）。
   若非 0：先修紅再往下。守衛線 3 筆鎖（`test_adr_xplat001_c1c2_lock.py`）若紅，多半是行數
   又漂了，重跑 `--print-guard-lines` 對帳。
2. 現查工作樹：`git status --short`。本輪改動檔（全部未 commit）：
   `tools/lib/relay_machine.py`、`tools/tests/test_context_budget_guard.py`、
   `tools/check_handoff_carriers.py`、`tools/tests/test_check_defect_log_crossref.py`、
   `.claude/settings.unattended.json`、`tools/tests/test_adr_xplat001_c1c2_lock.py`、
   `docs/06_quality/AutoSDD_Defect_Log.md`、`docs/04_planning/AutoSDD_Adjudication_Record_R120.md`（新）、
   `docs/06_quality/CrossPlatform_R120_Debt_Closure.md`（新）、
   `docs/04_planning/PRD_Amendment_R108_Pacing.md`、`..._BurnDown_Addendum.md`、
   `docs/04_planning/AutoSDD_TechDebt_Paydown_Playbook.md`、
   `docs/04_planning/PRD_Amendment_R113_WakeChain_LastMile.md`、本交棒書。
3. 派四方複審（逐個 Agent，cap 現查 `python tools/session_resume_planner.py --pace`）。
4. 複審收斂→commit（可單批或分批）→push（**不帶** env）→等雲端四支 completed。

## 下一步的確切指令（複審收斂後）

```
# commit（HEAD 前進即讓 pre-push 淨額棘輪自然綠）
git add -A
git commit   # 訊息含：P1-7 SD-4/SD-8、212 結案 D8、SA-4、P1-8、守衛線 R120 +N
# push（pre-push 會跑 crossref＋全套，>10 分鐘用背景）
git push origin main   # 逾時先 fetch 比對 rev-parse 再決定是否重推
```

## 禁止事項

- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`。
- push **不准**帶 `AUTOSDD_NET_RATCHET_OFF`（會洩入 pre-push 的全套測試＝R114 教訓）；
  該 env 只在 commit 前的本機 crossref 單獨驗證時掛。
- 守衛線 cap：**不准調高**任何 cap／天花板常數；`R121` 淨額必須 ≤0（款(11) 第 2 連升後義務）。
- 複審唯讀期間不動工作樹；複審未收斂前不得宣告收輪。
- DEF-200-241 的治本（時鐘前進／祖父化改讀結案）過四方複審前不動碼；D8 豁免已耗用不得援引。
