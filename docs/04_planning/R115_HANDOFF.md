# R115 交棒書（技術債結案輪；Windows 11）

> 輪次性質：結案輪（R114 交棒書指定 G1~G4 實作批四方複審最優先）。
> 證據檔＝`docs/06_quality/CrossPlatform_R115_Debt_Closure.md`（本輪唯一逐字證據載體）。
> 開場量測：未結 55／168、歸檔 rc=0、守衛線 90351（+0）、pace band=free。

## 一、已驗證什麼（附實測）

1. **G1~G4 實作批過四方**：一審 Architect REJECT／SA AWC／SD AWC／QA REJECT＝19 blocking
   去重 9 收斂項（舵手親驗 3 個關鍵爭點屬實）→ 修復波（三棒串行＋治理批＋收斂棒，全
   sonnet 載具、逐項突變驗紅）→ 二審 QA AWC／Architect AWC／SA AWC／SD APPROVE＝
   **零新程式 blocking**。逐項＝證據檔 §1~§3。
2. **總閥已開＋實彈演練全鏈通過**：`AUTOSDD_RESUME_OFF`（User 層）1→空；合成撞線→
   真喚醒→真 spawn headless→handback 四節寫齊→NO_PROGRESS_STOP＋loud→哨兵重掛
   **NextRunTime=2026/9/1 上午 06:56:10 值憑證**。附帶實彈證據：unattended settings 的
   deny 規則真擋下 headless 試寫 L3 鎖檔（`resumed.err` 逐字）；`notify_rc=-2` 活體重現
   236 的投遞不重投。證據檔 §4。
3. **帳本結案 3 列**：DEF-200-238（`_fold_gov_path()` 大小寫正規化＋`_GOV_EXACT` 納管
   二檔）、DEF-200-239（`_StatefulFakeSchedulerBackend` 注入＋回歸鎖；全套後
   `Get-ScheduledTask -TaskName 'T-r95'` 現查為空）、DEF-200-235（解鎖條件全兌現）。
   未結 **55→52**（淨減 3、新增 0）。
4. **守衛線款(11)款(12) 同輪兌現**：史料搬遷 -930 ⇒ R115 淨額 **-11**（90351→90340，
   連升 streak 終止）；到期義務 `(115, 577)` 兌現＋重新武裝 117/570；sha 接鏈
   ea038ea6→4e5f1156；overage 名冊零改動。
5. **呈報單第 2 件執行**：v0.02~v0.04 十二支假 SHA drift 檔 `git rm`（掌舵者 2026-09-01
   核准；存證＝`AISDLC_SDD/AISDLC_SDD_v0.30/EVOLUTION_LOG.md` 新節，比照 R107 八欄）。
6. **舵手親踩親修**：根 CLAUDE.md 鐵律一 `.sh` 執行教學形態原帶 bash `-n`（noexec＝
   rc=0 假綠），7 站點修復＋受影響測試 192 passed rc=0。證據檔 §5。
7. 長債軌 14 天複查完成（7 筆全數未達解鎖、複查日 2026-09-01；886 條件改寫＝原路徑
   已被 ADR-XPLAT-006 §7 否決）。
8. 收尾閘門：crossref rc=0（未結 52／168、時鐘 R100）；archive rc=0；carriers rc=0
   （111 份載體）。全套與雲端結論見〈附件一〉。

## 二、還沒做什麼（每項附載體與現查指令）

- **DEF-200-234／236 維持 open**（234 餘 ADR-XPLAT-014 §4 巡邏分支、236 餘 R112 §3-4
  補投佇列——兩者皆 Proposed 零實作）；現查
  `python tools/check_defect_log_crossref.py --unresolved-count`（兩列仍列未結）。
- **SA-4 條件**：unattended settings 的 allow `PowerShell(...)` 前綴語意仍待 runtime 驗證
  （deny 語法已實彈驗證有效）；載體＝證據檔 §4；現查＝下次無頭窗口的 resume log
  `Select-String -Path <log> -Pattern 'Permission'` 或 headless 窗口內實跑 allow 清單指令。
- **handback 未讀出聲半格**：實彈演練的 handback 檔刻意留存
  `C:\Users\wuwei\.autosdd\handback\74403d0c-0c20-4b1e-ae36-da690dc062b7.md`——下個互動
  session 開場 SessionStart 應出聲一次（G2 SessionStart 面自然驗證），看到即結；現查
  `Get-ChildItem $env:USERPROFILE\.autosdd\handback`（`.ack` 落地後轉安靜）。
- **SD-4／SD-8 advisory 未修**（RELAY_NEXT 排程失敗無 fallback 重掛＝
  `tools/lib/relay_machine.py` `settle_window` 的 RELAY_NEXT 分支；settle_window 無外圈
  例外保護＝planner resume 分支呼叫端）；二審 SD 確認座標未位移；現查
  `git grep -n "_register_and_record" tools/lib/relay_machine.py`。
- **淨減 3 ＜ 目標 7**：本輪主力被交棒書指定的最優先三件（複審→開閥→演練）佔用；
  231／232 經查解鎖條件未熟不硬湊。下輪結案輪繼續；現查
  `python tools/check_defect_log_crossref.py --unresolved-count`（現值 52）。
- **v2.1.10／v2.1.11／v2.1.12 三批修憲維持 Proposed**（沿 R114 未動）；現查
  `git grep -n "Status：Proposed" docs/04_planning/PRD_Amendment_R112_WakeChain.md`。
- **DEF-200-211／212① 沿 R114 未動**；現查 `python AutoClaude/tools/check_loc_budget.py --json`
  與 `python tools/check_handoff_carriers.py --self-test`。
- **DEF-101-693 bootstrap／integration 實跑紀錄沿 R114 未補**（外部軌）；現查
  `python tools/check_defect_log_crossref.py`（外部軌逐字列出 693）。

## 三、下一步確切指令（下輪開場）

```powershell
# 1. 開場量測四件套（缺一不動工）
python tools/check_defect_log_crossref.py --unresolved-count
python tools/check_archive_required.py
python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
python tools/session_resume_planner.py --pace
# 2. 開場會看到 SessionStart 的 handback 未讀出聲（74403d0c…）＝G2 半格自然驗證，確認後即結
# 3. 結案輪續攻未結列（52，單線逐筆；候選挑驗證型/P2）；234/236 依賴 ADR-XPLAT-014 與
#    R112 §3-4 落地（屬設計批，先呈掌舵者排程）
# 4. 呈報單兩件（見下）取得裁決後執行
```

## 四、禁止事項

不准 `--no-verify`；不准 `AUTOCLAUDE_SKIP_HOOKS=1`；不准調高任何棘輪常數換綠（R115 淨額
-11 已終止連升 streak，R116 若正淨額即重新起算、連兩輪後 R118 又須 ≤0）；Windows 側禁用
Bash 工具（鐵律一；`.sh` 執行形態禁帶 bash `-n`——noexec 假綠，見證據檔 §5）；
`AUTOSDD_RESUME_OFF` 已開閥，重新關閉須掌舵者裁決；逃生口環境變數只掛單一指令。

## 附件一：收尾閘門與帳本前後量測

- 開場（2026-09-01 01:02）：未結 **55**／168，外部軌 6、長債軌 7；守衛線 90351。
- 收尾：未結 **52**／168（結 3＝238/239/235、新增 0；淨 **-3**）；外部軌 6、長債軌 7
  （複查日全更新）；守衛線 **90340**（R115 淨額 -11）。
- <!-- guard-total:R115 --> **守衛線追記（R115 修復波＋治理批＋收斂棒史料搬遷）：護欄層累積淨額＝ 90351 → 90340（**-11**）** —— 修復波 +807 以史料搬遷 -930 抵銷（款(11) 連升 streak 終止＋款(12) 到期兌現 `(115, 577)`＋重新武裝 117/570）；逐檔清單見 `docs/06_quality/CrossPlatform_R106_Scan_Findings.md` 的 R115 標記行。
- 文件閘門：crossref rc=0／archive rc=0／carriers rc=0（帳本編修後實跑）。
- 全套根層 unittest：修復波後 `Ran 3789 tests` rc=0（收輪窗口於交棒書落檔後重跑最終次，
  結果補記於 commit 訊息）。
- 額度（收尾時點）：session/five_hour ~20%（prepare 帶）、weekly_scoped 72%（converge）、
  weekly_all 41%。

## 呈報單（需掌舵者本人核准）

1. **DEF-101-886 三形態裁決**：工作樹序列化原解鎖路徑已被 ADR-XPLAT-006 §7 明文否決；
   請就 Paydown Playbook :346 三形態擇一具名裁決——(a) 強制 worktree、(b) 收輪鎖、
   (c) 檢查表、(d) 維持現狀不機械化（選 (d) 則該列 closed-by-decision 移出長債軌）。
2. **R113/R114 守衛線分掛追認**（二審 Architect 條件）：G1/G2 批 +318 掛 R113「同輪追加」、
   G3+G4 批 +441 掛 R114「執行時點」——兩套歸屬理論並用、且唯一同時過 cap 的組合恰是
   被選中的那個（動機＝cap 餘裕，全程逐字揭露於稽核列非隱匿；成長本體＝落款 PRD 指定
   驗收測試非灌水）。請追認或指示重掛標號（後者代價＝凍結前綴改寫儀式）。
