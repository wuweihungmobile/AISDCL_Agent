# R88 交棒書

> 本輪是**單人收斂輪**：額度守衛在 PreToolUse 當場擋下扇出（`band=halt`、`cap=0`），
> 8 個實作包與四方複審**結構上派不出去**。交出的是舵手親做的部分，每一項附當回合實測。
> 重啟後第一件事是重驗，不採信本檔任何「已通過」宣稱。

## 0. 一句話總結

**R87 交出的是紅基線而交棒書寫綠**——本輪開場重驗抓到 AutoClaude **8 支紅**，
逐族治本後 `4586 passed / 73 skipped / rc=0`。四紅之中有兩族的病因同型：
**護欄層的真實狀態（LOC 破線、帳號撞額度上限）洩漏進與它無關的測試**，
於是失敗訊息與被測邏輯完全無關。

<!-- guard-total:R88 --> **本輪護欄層累積淨額＝ 83610 → 83670（+60）** —— 成長 3 支：
`test_check_hooks_liveness.py` +51（DEF-200-104 的第三個掃描面）、
`test_adr_xplat001_c1c2_lock.py` +6（重釘紀錄自身）、`test_context_budget_guard.py` +3。
逐筆立案＝`docs/06_quality/CrossPlatform_R88_Closure_Evidence.md`。
`[收尾單人窗口當回合實測；憑證＝tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines]`

## 1. 派工前置：為什麼沒有並行包

| 項 | 實測 |
|---|---|
| 伺服器現況（HTTP 200，非快取） | `extra_usage: used_credits 610 / monthly_limit 500 · utilization 100 · spend_limit_reached: true · disabled_reason "org_level_disabled_until" · can_purchase_credits false · can_toggle false` |
| 訂閱窗 | `five_hour 31%`（剩 204 分鐘）／`seven_day 14%` ⇒ **有餘裕** |
| 守衛裁決 | `--pace` ⇒ `cap=0 band=halt binding=extra_usage` |
| 實測派 1 個最小 agent | `PreToolUse:Agent hook error` **當場擋下**（模型未繞過、未關逃生口） |
| `--probe-quota` | `quota_open=True rc=0` ⇒ **主 session 通**，但這**不蘊含** subagent 那條路通（R87 墓碑逐字） |

🔴 **掌舵者釐清的語意**（2026-08-14）：「訂閱有額度，額外可能已經超出額度為 0」——
兩者是**兩件事**。這條語意本身正確，但**不足以推翻 halt**：R87 的實證是
「agent 全滅那一刻主力軸只有 1%」，⇒ subagent 路徑不吃訂閱窗。本輪照守衛裁決辦。
架構缺口已立案為 `DEF-200-112`（見 §4）。

## 2. 本輪治好了什麼（8 紅 → 0 紅）

| 族 | 根因 | 處置 | 憑證 |
|---|---|---|---|
| A（5 支 LOC 契約） | R87 加 24 行 ⇒ `quota_gate.py` **524 > 500**（`guardrail_hub`）；那 5 支斷言 `rc==0`，被檔案層真違規染紅 | 依 override_reason 指定出口**拆職責**：人話面整族抽出 `tools/lib/quota_messages.py`（leaf），`quota_gate` re-export ⇒ 消費端零改動 | `check_loc_budget --json` ⇒ `root_tools_violations: []` |
| B（1 支 DEBT 承接） | 3 筆 pgvector `[DEBT]` 承接輪次已第 5 次到期，而 reason 自己寫著「掌舵者未拍板前不得再改輪號」 | 取得拍板（見 §3）並履行其附帶義務 | `test_conftest_windows_native_skip_report.py` ⇒ 8 passed |
| C（1 支 pace 契約） | 合成契約測試讀到真實額度快取 ⇒ `cap` 落 0 | 與 D 同一個修法涵蓋 | `test_r86_pace_contract.py` 綠 |
| D（1 支 escalation） | **引擎測試讀開發機的活體額度快取**：`FileQuotaMeterAdapter` 預設 `tempfile.gettempdir()/autosdd_quota.json`，內含 `extra_usage 100` ⇒ `read_worst_pct()` 取最高軸 ⇒ TokenGuard 每步 HALT。失敗訊息（`assert False`）一字不提額度 | `AutoClaude/tests/conftest.py` autouse fixture 只換**預設**路徑；顯式 `path=` 的契約測試不受影響；**不動** `tempfile.gettempdir`（全域副作用） | `pytest tests/ -q` ⇒ **4586 passed, 73 skipped**, rc=0 |

## 3. 掌舵者拍板（本輪唯一需要人的決定）

**問題**：pgvector 三支 `[DEBT]` 第 5 次到期，repo 規則明文禁止再改輪號；
解除條件三項在 mac 本機一項都不存在。
**裁決**：**保留並本輪建自動通道**（對照選項為顯式廢止）。

義務已於同輪履行：

- 通道＝`AutoClaude/tools/run_local_nightly.ps1` 的 pg-e2e stage，對
  `test_pgvector_hnsw_recall.py` **獨立呼叫**（該檔在 `tools/`、`.github/` 此前**零命中**）。
- 🔴 **刻意不帶 `-m pg_real`**：本檔一個 `pg_real` marker 都沒有。接線憑證（當回合實測）：
  不帶 marker ⇒ **`5 passed, 2 skipped`**；照舊併入 `-m pg_real` ⇒ **`7 deselected`**（零執行）
  ——後者就是「假接線」的長相，而它與「通道建好了」在畫面上無法區分。
- 🔴 **也不寫 `.ac4_junit.xml`**：避免本檔的 skip 污染 AC4 觀察期取證（同 stage 對 contract 測試的既有判決）。
- rc 以 `[ref]` 捕捉並計入 stage fail。

**掌舵者補充的關鍵事實**：PG17+pgvector staging（≥1k 列真實 BGE-M3 向量）**只有 Windows 11 環境有**。
⇒ 這批債的剩餘阻塞是**平台綁定**而非時間綁定；mac 輪跑到它一律 skip，那是正確結果不是欠工。
承接輪次改派 R89 ＝ 複審檢查點，不是交付承諾。

同輪順手訂正一句在寫下當回合就變假的話：`_NO_AUTOMATED_CHANNEL` 逐字寫著
「本 repo 目前沒有任何自動通道會跑這兩支」，而 R88 就是建通道那一輪（立案 `DEF-200-111`）。

## 4. 帳本

| 項 | 值 |
|---|---|
| 結案（皆附當回合實測，證據檔＝`CrossPlatform_R88_Closure_Evidence.md`） | `DEF-200-095`／`100`／`102`／`103`／`104` |
| 新立案 | `DEF-200-109`（R87 紅基線）／`110`（測試不密封）／`111`（散文假話）／`112`（halt 不分兩型）／`113`（批次改派 24 列） |
| 未結 | 90 → **88**（warn 86、fail 98）｜`check_defect_log_crossref.py` **rc=0** |

🔴 **`DEF-200-112` 是本輪最重要的未結列**，且**刻意不在本輪改**：

> halt 判準不分「有 reset 可以等」與「沒有 reset 只能等人」。`extra_usage`／`spend`
> 撞頂後 `resets_at=null` 恆為 halt ⇒ ①續航哨兵結構上等不到 reset，**訴求 6e 對這一型無法兌現**；
> ②整個月度週期內派不出任何 agent，而訂閱窗當時只用 31%。
> 建議形狀＝`halt_wait`／`halt_human` 分類（**cap 兩者皆 0，只加資訊、不放寬任何一軸**）。
> 不在本輪動手的理由：R87 的教訓是「不得以模型判斷推翻機械守衛」，而這道改動需要第三方複審，
> 本輪結構上沒有第三方。

## 5. 還沒做什麼（誠實劃界）

全部因額度 halt 而未執行，現查 `python tools/session_resume_planner.py --pace`：

- **四方複審（Architect／SA／SD／QA）** — 一次都沒跑，本輪所有結論皆為自證。<!-- absent-if: CrossPlatform_R88_Review --> 證偽標的是那個 pattern：四方複審一旦真的跑過，本 repo 的既有體例會產出 `CrossPlatform_R88_Review*` 證據檔，屆時本行當場被打臉。（附帶現查「現在派不派得出去」：`python tools/session_resume_planner.py --pace`，`band=halt` 即結構上派不出任何 agent。）
- 訴求 1／3（跨平台全掃、M5 雙向不落差實跑）
- 訴求 6b 的**程式化**（分母標定公式落到程式；規格見 `R87_RESUME.md` §2b）
- 訴求 6g（`.env.example` → `.env` 實測調參）
- 系統問題 1（skipped 殲滅）：本輪只做了**分類**，未殲滅。母體 73 支，
  現查 `python -m pytest tests/ -q -rs`；分佈：`[WINDOWS-NATIVE-ONLY]` 36／`[ENV-DISABLED]` 13／
  `[DEBT]` 5／`[TOOL-ABSENCE]` 2 ⇒ **36 支是平台性質，在 mac 上結構上殲滅不了**，
  真正可攻的是 ENV-DISABLED 與 DEBT 兩族。
- 系統問題 3（Plugin 架構裁決）／SDD Agents 精進／Archive／Docker housekeeping
- 帳本降到 warn 線下（88 > 86，差 2）

## 6. 下一輪第一件事

```bash
python tools/session_resume_planner.py --pace          # band 仍 halt 就還是單人輪
python tools/run_root_unittests.py                     # 根層全綠才動工
cd AutoClaude && python -m pytest tests/ -q            # 4586 passed 是本輪基線
python tools/check_defect_log_crossref.py              # rc=0；未結 88
```

🔴 **需要掌舵者親自做的**：月度支出上限 `used 610 / limit 500`，
`can_purchase_credits: false`、`can_toggle: false`、`disabled_reason: org_level_disabled_until`
⇒ **沒有 reset 可以等，也不是我能繞過的**。在它解除之前，每一輪都只能是單人輪，
四方複審結構上不存在。→ https://claude.ai/settings/usage
