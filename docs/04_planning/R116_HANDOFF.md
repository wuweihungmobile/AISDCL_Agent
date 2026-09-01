# R116 交棒書（P1-1 單一實作包；ADR-XPLAT-013 Phase2 (b)(c) 分軌計價，DEF-200-211）

> 輪次性質：單人窗口實作批，承接裁決 `AutoSDD_Adjudication_Record_R110.md` §1.4
> D-1~D-6。**本檔只涵蓋本包（P1-1）交件範圍，不宣稱本輪已收輪／已 push**（收尾
> commit 與跨包整合由主控做）。逐檔清單與異動明細見
> `docs/06_quality/CrossPlatform_R116_Scan_Findings.md`（本輪唯一逐字證據載體）。

## 一、已驗證什麼（附實測）

1. **D-1（S-2）回歸鎖軌／功能軌分軌計價落地**：新平行表 `_REGRESSION_LANE_LOG`
   （空表起始）、`lane_split_problems()` 六款、`repin_growth_problems()` 擴
   `regression_lane` 參數並已接進生產閘門（`test_the_repin_log_accounts_for_
   the_frozen_table`）。`python -m pytest tools/tests/test_adr_xplat001_c1c2_
   lock.py -k TestRegressionLaneSplit -q`：**24 passed**（QA 鏡終驗值，含四方複審
   承接後補的款 3 淨減法輪邊界等測試；原交件時點快照 18 已被超越——Q-1 勘誤）。
2. **D-2 M1 拆雙指標**：`CrossPlatform_Maturity_Criteria.md` 訂正段落地，既有
   門檻文字未動——`python -m pytest tools/tests/test_maturity_criteria_r79.py
   -k TestM1 -q`：5 passed, 4 subtests passed。
3. **D-3 ruff S102**：`tools/ruff.toml`／`AutoClaude/pyproject.toml` 同步加選；
   `ruff check tools/ .claude/hooks/` 與 `ruff check --select S102 AutoClaude`
   皆 `All checks passed!`（rc=0）；`TestRootToolsLintPolicy` 8 passed。
4. **D-4 (c) 降級為觀測欄**：`guard_line_composition()` 落地，只印不擋；
   `TestObservationColumnsAreDisplayOnly` 三格皆綠。
5. **D-5**：U6 現值門檻核准存證；U7 方針定案（逐一改寫，25 站點僅 2 列已改，
   23 個未做）；U9 到期輪常數落地（`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND=121`，
   四支 `[ROOT-TOOLS]` 檔真拆本身未做，over_by 現查 187）。
6. **D-6**：`_REGRESSION_LANE_ROUND_CAP=309`，取值基準＝`_regression_lane_cap_
   basis()` 對 `_GUARD_LINES_REPIN_LOG` 現查可導出，非憑空取數。
7. **守衛線淨額** <!-- guard-total:R116 --> **90344 → 90921（+577）**，貼齊但未超
   當輪上限 577（`net_cap_for_round(116)`；含 Architect 鏡一審承接補釘 +4）；
   `_GUARD_LINES_REPIN_LOG` 兩列（落地批＋補釘批）與 `_FROZEN_PREFIX_REWRITE_LEDGER`
   兩列、`_REPIN_LOG_FROZEN_PREFIX_LEN` 88→90、sha 接鏈
   9316ce4e91ed→1bd8f0d4e396→a08e0c7043be 皆已落地。

## 一之一、P1-2/P1-3 喚醒鏈批（同 session 第二批，守衛線輪籤 R117）

巡邏 tick「主控死亡但 tasks/ 有活體」分支（`_orphan_watch()` 族，DEF-200-234 驗收）＋
持久 notify_queue（TTL＋delivered 憑證＋巡邏重投，DEF-200-236 驗收，含 notify_rc=-2
活體重演轉綠）。<!-- guard-total:R117 --> **守衛線累積淨額＝90921 → 91210（+289）**：
驗收回歸鎖 238 行申報回歸鎖軌（`_REGRESSION_LANE_LOG` 首列＝分軌機制第一次實戰消費，
`_REGRESSION_LANE_SINCE=117` 故本批掛 R117 輪籤）；功能軌淨額＝稽核與儀式行＋複審
承接（A-2 unmeasurable 保標記、SD-1 節流專屬常數等測試）自身 +51 ≤ cap(117)=570；
同輪兌現款(12)＝`(117, 570)` 並重新武裝 119/564（步伐 6<7）。

## 一之二、四方定點複審（2026-09-01 收斂）

Architect：REJECT（流程性＝審查窗口內工作樹被主控寫入；設計面承接 A-1 E501 棘輪真紅／
A-2 到期輪可被靜默推遠／N-1 裸 StopIteration）→修復後由後三鏡逐項 konfirm。
SA：AWC（S-1 帳本 211 列 fixed 宣稱過寬／S-2 ADR U5 過期字面，皆已修；N-2/N-3 已修）。
SD：AWC（SD-1 款 3 對淨減法輪誤判＝blocking，已修並真突變驗紅；其建議修法一
`max(main_delta, 0)` 經主控親算證僞、採「母項 ≤0 跳過」形態）。
QA（末棒）：AWC 零新 blocking＋全套親跑 `Ran 3821 tests`／`OK (skipped=42)` rc=0
⇒ **四方收斂成立**。Q-1/Q-2 文件勘誤同批訂正；未修項 N-4/SD-2~SD-5 經 QA 逐筆
判定同意延後（掛帳見〈二〉）。

## 二、還沒做什麼

1. U7：25 個自陳站點中 23 個尚未逐一改寫；現查
   `git grep -n "落地未完成" docs/04_planning/ADR/ADR-XPLAT-013-loc-pricing-assertion-only.md`
   （有命中＝仍未完成；清單住該 ADR §8）。
2. U9：四支 `[ROOT-TOOLS]` 檔真拆到舊尺不破線（目標 −187 行，到期輪 R121）。
3. U1~U4：Architect/SA/SD/QA 獨立審查尚未進行（`ADR-XPLAT-013` 轉 Accepted 前置）；現查
   `git grep -n "☐ 未進行" docs/04_planning/ADR/ADR-XPLAT-013-loc-pricing-assertion-only.md`
   （U1~U4 四列有命中＝仍未進行）。
4. 候選 2（C1~C4）全自動分類器對真實 diff 的假紅普查（提案 §4 item 2 已誠實登記
   為射程外，非本包漏做）。
5. 全套根層 `python tools/run_root_unittests.py`：已由主控（`Ran 3820` rc=0）與
   QA 鏡（`Ran 3821` rc=0，含 SD-1 新測試）各跑一次，皆綠——本項結案。
6. SD-2（QA 判定掛帳）：`_REGRESSION_LANE_APPROVED_OVERAGE_MAX_ENTRIES` 零消費端——
   名冊首次啟用前須比照 `_REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES` 的姊妹測試補
   上限斷言；現查
   `git grep -n "_REGRESSION_LANE_APPROVED_OVERAGE_MAX_ENTRIES" tools/tests/`
   （僅定義行命中＝仍未接電）。
7. 🔴 **無主模式「處置面」未落地**（P1-2/P1-3 批 Architect A-1＋SA S-1 承接掛號；
   偵測面＝tick 分支＋loud＋落痕跡已落地）。缺兩件：(a) cap 收斂——v2.1.12 §5-1 逐字
   「cap 收斂到 cap_prepare 語意以下」，`--pace`／quota_gate 消費端未接；現查
   `git grep -n "cap_prepare" tools/lib/quota_escalation.py`（零命中＝仍未接）。
   <!-- absent-if: def test_orphan_cap_clamp -->（落地驗收測試名指定＝`test_orphan_cap_clamp*`，
   出現即證偽本項「處置面未落地」宣稱）
   (b) alert 任務書接線——`LIMIT_SESSION`＋`arm_reset`/`probe`（最常見情境）下無主分支
   只發 toast，不寫 `AUTOSDD_ATTENTION.md`、不含 `claude -r` 接回指令與具體無主
   run/agent 清單（`_agents_liveness()` 算出的清單被塌成單一字串丟棄）；唯一端到端
   測試用 SPEND 語料未蓋此情境；現查
   `git grep -n "alert(" tools/lib/quota_escalation.py`（`_orphan_watch` 體內零命中＝仍未接）。
8. P1-2/P1-3 批三筆未修觀察項（QA 鏡 Q-1 要求逐項掛號）：
   (a) Architect N-4＝`alert()` 首次投遞失敗只落 `notify_rc`、未附 `delivered` 布林鍵
   （語意等價 PRD §3-4 字面、用詞收斂級）；現查
   `git grep -n "delivered" tools/lib/quota_escalation.py`（alert 段零命中＝仍未收斂）。
   (b) N-SA-1＝`_idle_prepare_watch()` 預警失投未接 `queue_notify()`（檔頭 WHY 已同批
   劃界訂正為「範圍＝alert/_orphan_watch 兩處」）；現查
   `git grep -n "queue_notify" tools/lib/quota_escalation.py`（`_idle_prepare_watch`
   體內零命中＝仍未接）。
   (c) SD-2＝`_save_queue` 沿用既有 `_write()` 非原子寫入（腰斬時 `_load_queue` 回空
   不出聲）；既有慣例延伸、`with_lock()` 已序列化多行程；現查
   `git grep -n "_write(" tools/lib/quota_escalation.py`。
9. P1-1 批 N-4／SD-5（QA 同意延後）：`_regression_lane_cap_basis()` None 分支與
   `regression_lane_round_nets()` 同輪合併分支各缺一支合成注入測試（守衛線 cap
   貼線 577/577 故延後）；現查
   `git grep -n "N-4（SA 鏡登記，未修）" tools/tests/test_adr_xplat001_c1c2_lock.py`。

## 三、下一步的確切指令

```powershell
& "d:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe" -m pytest `
  "d:\CursorProject\AISDCL_Agent\tools\tests\test_adr_xplat001_c1c2_lock.py" -q
python d:\CursorProject\AISDCL_Agent\tools\run_root_unittests.py
```

## 四、禁止事項

- 不准調高 `_REGRESSION_LANE_ROUND_CAP`／`_REPIN_ROUND_NET_CAP`（cap 類＝只准調小）。
- `_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 展延只准走具名複審且不得超過
  「現查輪＋`_ROOT_TOOLS_DEBT_DUE_MAX_LOOKAHEAD`」界（A-2 後設鎖），不得靜默推遠。
- 不准把 `_REGRESSION_LANE_SINCE` 調小（追溯放寬，見 `[減免軌被追溯]`）。
- 不准為了讓 U9 的到期輪判準轉綠而把 `_ROOT_TOOLS_OLD_SCALE_DEBT_RESOLVED`
  改 True，除非四支 `[ROOT-TOOLS]` 檔已真的拆到舊尺不破線。
