# AutoSDD_improving_111（R88）— 單人收斂輪：紅基線治本 ＋ 額度架構缺口立案

> **軌道①**（AISDLC-SDD × AutoClaude 深度整合）。本輪三柱分佈：
> **C 柱（指揮官 AutoClaude）** 為主（8 支紅治本、測試密封性、pgvector 自動通道）、
> **B 柱（手腳 AISDLC_SDD）** 一項（LATEST hook 的 console spawn）、**A 柱** 無。
>
> 🔴 **本輪形狀由額度決定，不是由規劃決定**：`--pace` 回 `cap=0 band=halt`，
> 扇出在 PreToolUse 被擋 ⇒ 8 個實作包與四方複審**結構上派不出去**。
> 本檔記錄的是單人窗口做得完的那一部分，以及做不到的那一部分為什麼做不到。

## §0 立案：R87 交出的是紅基線

R87 交棒書宣稱基線綠。R88 開場重驗（`cd AutoClaude && python -m pytest tests/ -q -rs`）：

```
8 failed, 4578 passed, 73 skipped in 95.08s
```

四族根因，其中兩族病因同型——**護欄層／執行環境的真實狀態洩漏進與它無關的測試**：

| 族 | 支數 | 根因 |
|---|---|---|
| A | 5 | R87 為訴求 6c 在 `tools/lib/quota_gate.py` 加 24 行 ⇒ **524 > 500**（`guardrail_hub` tier）。那 5 支斷言的是「tier 預警帶必須非阻塞（rc==0）」，被檔案層真違規染紅 ⇒ **測試名稱與失敗原因無關** |
| B | 1 | 3 筆 pgvector `[DEBT]` 承接輪次第 5 次到期；reason 自己寫著「掌舵者未拍板前不得再改輪號」⇒ 唯一出路是取得拍板 |
| C | 1 | 合成 pace 契約測試讀到**真實**額度快取 ⇒ `cap` 落 0 |
| D | 1 | 引擎測試讀開發機**活體**額度快取：帳號撞月度上限 ⇒ `extra_usage 100` ⇒ TokenGuard 每步 HALT；失敗訊息 `assert False` 一字不提額度 |

## §1 處置與憑證（當回合實測）

| 項 | 處置 | 憑證 |
|---|---|---|
| A | 依 `check_loc_budget` override_reason 指定的出口**拆職責**（不調門檻）：人話面 7 支函式＋3 支期程 helper＋4 個常數抽出 `tools/lib/quota_messages.py`（leaf，≤400），`quota_gate` re-export ⇒ 4 個消費端零改動 | `check_loc_budget --json` ⇒ `root_tools_violations: []` |
| A′ | 順手拔掉 `quota_gate` 內已成死碼的 `import schedule_backend`——留著就是同一份參照兩個家，而且是**會靜默騙人**的那種（測試 patch 這一份、真正被呼叫的是另一份）。這不是假想：搬移第一版就被兩支既有測試當場抓到 | `test_context_budget_guard.py` ⇒ **349 passed, 8 skipped** |
| B | 取得掌舵者拍板「保留＋同輪建自動通道」並履行 | 見 §2 |
| C+D | `AutoClaude/tests/conftest.py` autouse fixture，只換 `FileQuotaMeterAdapter` 的**預設**路徑 | `pytest tests/ -q` ⇒ **4586 passed, 73 skipped**, rc=0 |
| B 柱 | SDD LATEST 的 3 個 hook git spawn 補 `CREATE_NO_WINDOW`，並把該樹納為 console-spawn 的**第三個掃描面**（LATEST 走 SSOT 現查、不寫版號） | `test_check_hooks_liveness.py -k "ConsoleFree or sdd"` ⇒ 6 passed |

<!-- guard-total:R88 --> **本輪護欄層累積淨額＝ 83610 → 83670（+60）**。
成長 3 支：`test_check_hooks_liveness.py` +51（第三個掃描面，該面此前一個觀測者都沒有，
沒有等量舊判準可退場去換）、`test_adr_xplat001_c1c2_lock.py` +6（重釘紀錄自身）、
`test_context_budget_guard.py` +3。逐筆＝`docs/06_quality/CrossPlatform_R88_Closure_Evidence.md`。

## §2 掌舵者拍板（本輪唯一需要人的決定）

pgvector 三支 `[DEBT]` 第 5 次到期。裁決：**保留並本輪建自動通道**。

通道＝`AutoClaude/tools/run_local_nightly.ps1` 的 pg-e2e stage 對
`test_pgvector_hnsw_recall.py` 獨立呼叫。**刻意不帶 `-m pg_real`**——接線憑證：

```
不帶 marker  ⇒ 5 passed, 2 skipped     ← 真的會跑到
-m pg_real   ⇒ 7 deselected（零執行）  ← 「假接線」的長相
```

🔴 掌舵者補充的關鍵事實：**PG17+pgvector staging（≥1k 列真實 BGE-M3 向量）只有 Windows 11 環境有**。
⇒ 剩餘阻塞是**平台綁定**而非時間綁定，mac 輪跑到它一律 skip＝正確結果。

## §3 未做（誠實劃界）

**四方複審一次都沒跑**——本輪所有結論皆為自證。訴求 1／3／6b 程式化／6g、
系統問題 1（skipped 只做分類未殲滅）／3、SDD Agents、Archive、Docker 全數未動。
逐項現查指令見 `docs/04_planning/R88_HANDOFF.md` §5。

## §4 最重要的未結列：`DEF-200-112`

halt 判準**不分「有 reset 可以等」與「沒有 reset 只能等人」**。後果有二：
①續航哨兵對 `resets_at=null` 那一型結構上等不到 reset ⇒ **訴求 6e 對它無法兌現**；
②整個月度週期內派不出任何 agent，而訂閱窗當時只用 31%。

建議形狀＝`halt_wait`／`halt_human` 分類（**cap 兩者皆 0，只加資訊、不放寬任何一軸**）。
🔴 **本輪刻意不動**：R87 的教訓是「不得以模型判斷推翻機械守衛」，這道改動需要第三方複審，
而本輪結構上沒有第三方。
