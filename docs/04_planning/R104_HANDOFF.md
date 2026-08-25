# R104 交接書 — BURSTING 判準 + EWMA 診斷值（設計完成，尚未實作）

> 本檔案由舵手在 context 水位 94.8%（撞硬線）當下寫入，作為安全暫停點的任務書。
> 🔴 重啟後第一件事＝重驗，不採信本檔任何「已驗證」宣稱本身的正確性——本檔只記錄
> 「當時做過什麼指令、印出什麼」，不代表結論在重啟當下仍然成立。

## 0. 本輪範圍決策（掌舵者已拍板，互動問題已問過，勿重問）

開工前用 `AskUserQuestion` 問過掌舵者「PRD v2.1 還缺好幾組功能，這輪要優先做哪一組」，
三選一，掌舵者選：**「遙測與動態派遣強化」**（對應 PRD §4.1.1／§4.2.1／§4.2.5／§9）。

舵手依現有程式碼實測，把這個大範圍收斂為：

- **本輪主功能** ＝ PRD §4.2.5 BURSTING 突刺判準（完全未實作，真缺口）。
- **本輪次功能** ＝ PRD §4.2.1 EWMA 燃燒率，但**僅做成不影響決策的診斷值**——
  因為 PRD §4.2.8 原文自己講「建議實作採用 `pace_index` 為主控訊號，`V_eff` 僅作為
  輔助診斷指標」（此句經設計 agent 二次核實：`pace_index` 目前**不是**主控訊號，
  真正主控訊號是 `lead_pp`，但兩者同屬「pace 家族」，EWMA 屬於完全不同的「瞬時燃燒率
  家族」，PRD 明講後者只當診斷用——見下方 §1 設計文件 A 節）。
- **明確不做**（已知缺口，非本輪目標）＝ §4.1.1 遙測多管道（T1~T4）、§4.2.3 任務類別
  過濾、§9 Prometheus/OTel 可觀測性。已在 R103 交接書登記過，不重複展開。

## 1. 已驗證什麼（本輪實測，附指令與輸出）

### 1.1 帳本與環境現況（開工前查核，`2026-08-25`）

```
$ python3 tools/check_defect_log_crossref.py
未結存量逼近列數上限：未結列 91 筆 …距 fail 線 98（距 7 筆）
已結列殘留待辦 7 筆（不是掌舵者記憶中的舊數字 18——那是 R100 時代快照，R103 已清 11 筆）
✅ 缺陷帳本跨文件狀態一致

$ python3 tools/check_archive_required.py
✅ 未觸發歸檔強制門檻

$ which act && act --version   → /opt/homebrew/bin/act, act version 0.2.89
$ which docker && docker --version → /usr/local/bin/docker, Docker version 29.6.1

$ python3 tools/session_resume_planner.py --pace
現在可派 4 個 agent（硬上限 cap=不設限）｜band=free｜session 4%／週軸 32%，額度充裕
```

**結論**：帳本未撞線、額度充裕、本機驗證工具(act+Docker)就緒，可以放心規劃派工。

### 1.2 PRD 原文核對（設計 agent 實讀，行號已核實）

`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`：
§4.2.1(432行)／§4.2.5(678行)／§4.2.6參考實作(693行)／§4.2.7情境表(910行)／
§4.2.8(926行，講「pace_index為主控訊號」)。

### 1.3 現有程式碼盤點（設計 agent 實讀+實跑指令核實）

- `tools/lib/quota_pace.py`(570行)：`pace_index()`[213行]、`lead_pp()`[202行]、
  `burn_step()`[230行]、`segments()`[480行，已有 reset 偵測]、`estimate_ratio()`[504行]
  皆已存在。**grep 全庫 `ewma|EWMA|burn_rate|BURST` 零命中**——EWMA/BURSTING 完全未做。
- 決策鏈實際主控訊號＝`lead_pp()`（差值形式），不是 `pace_index()`（比值形式，目前只是
  人讀診斷輸出）——這點糾正了舵手開工前的誤判，已寫入下方設計文件 A 節。
- **額外發現**（非本輪待辦，但四方複審裁決 BURSTING 是否接線時必須知情）：既有
  `pace_near`（近 reset 加速 2 倍）是**無條件**的，不檢查 U5h/U7d/佇列——若 BURSTING
  接線，會與這條既有機制產生語意重疊，需另外定調，本輪不修 `pace_near` 本身。
- LOC 治理實測：`python AutoClaude/tools/check_loc_budget.py --json` 顯示
  `quota_pace.py` 餘裕 140 行、`quota_policy.py` 餘裕 139 行、`quota_policy_env.py`
  餘裕 244 行——三檔皆不在任何 tier 預警帶，本輪新增函式不會撞 LOC 上限。

### 1.4 🔴 關鍵阻塞風險（設計 agent 發現，舵手實測二次核實）

```
$ grep -n '"test_quota_policy.py"' tools/tests/test_adr_xplat001_c1c2_lock.py
743:    "test_quota_policy.py": 2993,
$ wc -l tools/tests/test_quota_policy.py
2993 tools/tests/test_quota_policy.py     ← 與登記值吻合，目前無漂移

$ grep -n "_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS\|_REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES" \
    tools/tests/test_adr_xplat001_c1c2_lock.py
1166:_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2
1213:_REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES = 1
```

`tools/tests/` 整體語料的行數棘輪：R102(+661)、R103(+129) 已**連續 2 輪淨增**，
剛好頂到 `_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2` 的上限（尚未違規）。
一次性豁免名額（`_REPIN_APPROVED_ROUND_OVERAGE`，上限 1 筆）**已被 R101 用掉**。

⇒ **R104 若對 `tools/tests/` 整體語料造成淨行數增加（哪怕只多 1 行），且無等量抵銷，
會觸發連續第 3 輪違規，且沒有豁免名額可用** ——`test_the_real_repin_log_stays_inside_
the_cost_envelope` 會轉紅（該測試會被 pre-push 與 root-infra CI 收集執行）。

**這不是本輪不能做的理由，是本輪必須同步做「新增測試的同時，在 `tools/tests/` 語料
內找等量或更多既有可搬遷散文段落抵銷」的理由**（既有慣例：搬史料進證據檔，只搬散文
不動判準本身，同型先例見 R103 的 `check_loc_budget.py` 事故史料搬遷）。

**上述數字是快照，實作前必須重新現查一次**（其他並行包若也在動 `tools/tests/`，
會共用同一份淨額預算——CLAUDE.md 鐵律七）。

### 1.5 設計文件全文（general-purpose agent，effort=inherit，唯讀分析，未動任何檔案）

完整設計文件（A~F 節 + 涉及檔案清單）已於本 session 產出，**全文見本輪對話紀錄
（agentId: a6d843df891b69c58）**，重點摘要：

- **B 節**：新函式 `bursting_ok()`（六條件短路判定，放 `tools/lib/quota_pace.py`，
  keyword-only 參數＋保守缺省值）與 `ewma_burn_rate()`（重用 `segments()` 斷點邏輯對
  目前分段做 fold，取代 PRD 的 `ControllerState` 物件遞迴），皆給出具體簽章與判定順序表、
  8+ 個測試案例（含邊界值 T_rem=30.0 恰好通過、`None` 一律 fail-closed、佇列參數
  不傳時預設不放寬）。
- **C 節**：BURSTING 若要接線的建議落點（`quota_gate.py::pace_report()` 用 `replace()`
  覆寫 `decision.cap`，仿現有 `quota_availability`/`quota_stability` 的既有覆寫先例，
  **不要**改 `_cap_for()` 內部）。**本輪建議選項一：只算、不接線**（風險說明見設計文件
  C.1，四方複審裁決是否升級為選項二）。
- **C.2 節**：`ENABLE_BURSTING` 建議用 `int`(0/1) 借用既有 `ENV_SPEC` 數值管線，
  不新增 bool 解析路徑（零管線變更）。
- **F 節**：本輪明確不做——「T_rem≤預估Step執行時間」子判準（唯一可用數字是已知假的
  `STEP_MEDIAN_WALL_SECONDS_PLACEHOLDER`，不用假數字做真安全網）、`pace_near`
  整併、EWMA 接入決策鏈、`burn_ratio()` 簽章擴充。

## 2. 還沒做什麼

- [x] `bursting_ok()` / `ewma_burn_rate()` 已落地（見下方 §6 追記），當時撞線設計
  agent 只讀不寫、已用 `git status --short` 確認工作樹乾淨的狀態不再成立。
- [x] 已補 14+ 個測試案例，見 §6：`python3 -m unittest test_quota_policy
  .TestR104BurstingOkAndEwmaBurnRate -v` 全綠。
- [ ] `act`/Docker 完整 CI 對等容器尚未實際跑過這個功能，維持未做；本機驗證僅
  執行過 `python tools/run_root_unittests.py`（見 §6，rc=0／3687 tests／
  failures=0，量測時間見交件回報）。
- [ ] 無四方複審（Architect/SA/SD/QA）。
- [ ] 無 commit、無 push。
- [x] `tools/tests/` 語料淨行數抵銷方案已執行完畢，見 §6 與
  `docs/06_quality/CrossPlatform_R104_Scan_Findings.md`：實測用
  `python3 -m unittest test_adr_xplat001_c1c2_lock` 全綠，
  `repin_cost_ratchet_problems()` 回傳空 list。

## 3. 下一步的確切指令（重啟後照此執行，不要重新設計）

1. 重新用 `python3 tools/check_defect_log_crossref.py`、`python3
   tools/check_archive_required.py`、`grep -n '"test_quota_policy.py"'
   tools/tests/test_adr_xplat001_c1c2_lock.py` 重新核實 §1.1/§1.4 的數字（可能已因
   其他 session 改動而漂移，不得沿用本檔數字）。
2. 用 `Agent` 工具（`subagent_type: general-purpose`）或 `Workflow` 工具，把上方
   §1.5 摘要的設計內容（含六條件判定順序表、8+測試案例、C.1/C.2 節的裁決建議）餵給
   一個 SD 實作 agent，要求：
   - 先 Read `tools/lib/quota_pace.py`、`tools/lib/quota_policy_env.py` 全檔，
     確認上方摘要仍與現況相符（不符則以現況為準，回報差異）。
   - 實作 `bursting_ok()`＋`ewma_burn_rate()`＋新常數登記進 `ENV_SPEC`。
   - 同步處理 §1.4 的行數棘輪抵銷（新增測試同時搬遷等量散文，更新
     `_FROZEN_GUARD_LINES`／`_GUARD_LINES_REPIN_LOG`）。
   - 立即跑 `python tools/run_root_unittests.py` 全套（不是
     `python -m unittest discover`，DEF-200-215 教訓），逐字回報 rc 與 pass/fail 數。
   - **禁止 commit/push/add**，變更留在工作樹。
3. 實作完成後，派 4 個獨立 review agent（Architect/SA/SD/QA 人設），各自親自跑
   `git diff` 核實實際改動（不得信任實作 agent 的自我陳述），依上方設計文件的判斷
   點（尤其 C.1 是否接線、C.2 型別選擇）給 APPROVE/REJECT + 具體發現。
4. 若有 REJECT，派 1 個 fix agent 修復，重跑測試，再次 4 方複審，最多 2 輪收斂。
5. 全數 APPROVE 或收斂後，**由舵手本人**（不是 agent）跑 `git add` + `git commit`
   + `git push`，比照 R103 慣例單一 commit 涵蓋整輪變更。
6. 收尾：更新本檔或另立 `R104_HANDOFF.md` 收尾版，附最終帳本數（未結列變化）、
   PRD v2.1 尚未完成功能清單（沿用 R103 版本更新）。

## 4. 禁止事項

- 不准重新問掌舵者「這輪要做哪個」——已經問過，答案是「遙測與動態派遣強化」，已收斂
  為 BURSTING+EWMA診斷（見 §0）。
- 不准讓實作 agent 自己決定「BURSTING 要不要接線生效」——這是設計文件明確列為
  「交四方複審裁決」的項目，不是實作者可以自行拍板的範圍。
- 不准用 `python -m unittest discover -s tools/tests`（本 repo 結構上跑不起來，
  DEF-200-215）。
- 不准對 `tools/tests/` 語料做淨增而不同步處理 §1.4 的棘輪抵銷。
- 不准派子 agent 做長時間驗證後自己架 Monitor 就交卷——上一輪（R103）才發生過這個
  問題（75 次工具呼叫後說「架好在等」就結束，沒人被叫醒），本輪要同步等到底或用
  `run_in_background` 搭配會被通知的機制。
- 不准用 `git stash`（除 `git stash create`）、`git reset --hard`、
  `git checkout -- <path>` 等破壞性指令。
- 不准在任何宣稱旁邊少貼實測輸出（rc、pass/fail 數字），"應該"/"大致"一律視為未驗證。

## 5. Session 續接資訊

- session id：`78010d39-0b55-4fdd-bacb-a22c41857e68`（撞線當下實測，`ls -t
  ~/.claude/projects/-Users-wuweihong-Antigravity-AISDCL-Agent/*.jsonl` 取最新一份）。
- 續接指令：`claude -r 78010d39-0b55-4fdd-bacb-a22c41857e68`。
- 撞線當下 context 水位：94.8%（189,671 / 200,000 推斷值）。
- 工作樹狀態：乾淨（`git status --short` 零輸出），HEAD＝`af4f8a1`（R103 收尾）。

## 6. 實作後追記（SD 實作 agent，本欄不覆寫上方交接書當時的原始記錄）

`bursting_ok()`／`ewma_burn_rate()` 已落地於 `tools/lib/quota_pace.py`（只算不接
線，未進 `quota_gate.py` 決策鏈）；`tools/tests/test_quota_policy.py` 新增
`TestR104BurstingOkAndEwmaBurnRate` 回歸測試。§1.4 所述的 `tools/tests/` 語料棘輪
風險已處理：搬遷 `_platform_helpers.py` 三段 forensic 沿革（見
`docs/06_quality/CrossPlatform_R104_Scan_Findings.md`）抵銷新增測試行數，總淨額
為負，連續上升 streak（R102/R103）於本輪歸零。四方複審（是否升級為「接線生效」）
與 commit/push 仍待舵手安排，未在本 agent 職權範圍內執行。

<!-- guard-total:R104 --> **本輪護欄層累積淨額（稽核痕跡合計）＝ 88574 → 88556（-18）**
——逐檔清單與三段搬遷散文全文見 `docs/06_quality/CrossPlatform_R104_Scan_Findings.md`。
