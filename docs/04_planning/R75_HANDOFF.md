# R75 交棒任務書（跨平台相容性輪）

> **產出**：`21354c9`（主體，59 檔）→ `a61bf0c`（修雲端三支紅）→ `93e945f`（回填雲端錨）。
> **平台**：Windows 11 真機（PowerShell 5.1 ＋ 7.6.4）。
> **本檔用途**：讓 R76 不必採信任何宣稱就能接手。凡「已通過」一律附當回合可重跑的指令。

---

## 1. 收輪時的實測狀態（R76 開場請自己重跑，不要採信本表）

| 閘門 | 指令 | R75 收輪實測 |
|------|------|--------------|
| 根層 unittest | `python tools/run_root_unittests.py` | 1902 tests / OK / skipped=43 / rc=0 |
| AutoClaude pytest | `cd AutoClaude; python -m pytest tests/ -q` | 3900 passed / 224 skipped / rc=0 |
| LOC budget（含新增的根層 `tools/` 分級） | `python AutoClaude/tools/check_loc_budget.py` | 四類 violations 全空 / rc=0 |
| import-linter | `$env:PYTHONUTF8=1; lint-imports`（cwd=AutoClaude） | 8 kept / 0 broken |
| ruff | `ruff check tools .claude/hooks` | rc=0 |
| 缺陷帳本一致性 | `python tools/check_defect_log_crossref.py` | rc=0 |
| 帳本保全稽核 | `python tools/archive_defect_log.py --check` | rc=0 |
| ONBOARDING 基線 | `python tools/sync_onboarding_baselines.py --check` | rc=0 |
| ONBOARDING 指紋 | `… --check-snapshot` | rc=0（Windows 欄相符） |
| 雲端 push 軌 | 見 §2 | 六支最近一次 push run 全 success |

帳本體積：主檔 250,390 bytes（warn 245,760／fail 262,144，餘裕約 11.7KB）。未結列 **82**（warn 86／fail 98）。

---

## 2. 雲端狀態與一個結構性的誠實邊界

逐 workflow 現查（`gh run list --workflow <wf> --event push --limit 1`）：

| workflow | 結論 | 那次 run 的 commit |
|---|---|---|
| `root-infra-ci.yml` | success | `93e945f` |
| `windows-compat-ci.yml` | success | `93e945f` |
| `macos-compat-ci.yml` | success | `93e945f` |
| `autoclaude-ci.yml` | success | `21354c9`（此後未觸發） |
| `aisdlc-sdd-ci.yml` | success | `21354c9`（此後未觸發） |
| `autoclaude-mutation-on-change.yml` | success | `0b6468b`（源碼變動軌） |

🔴 **不要把上表讀成「五支都為 HEAD 跑過」**：後三支未為 HEAD 觸發（`paths:` 過濾）。
「沒觸發」與「跑過且綠」在 GitHub UI 上長得一模一樣——ONBOARDING 表③ 既有註記，本輪再次生效。

### 錨的誠實邊界（R76 請理解這一點，不要當成缺失去「修」）

ONBOARDING 表③ 的錨目前 `head-sha=a61bf0c…`、無 `pending` 欄，而 HEAD 是 `93e945f`。
`93e945f` 是**只改文件的回填 commit**，它自己的三支 run 也已實測 success（見上表）。

之所以停在這裡而不是再回填一次：**這是自我指涉紀錄的結構終點**。
每一次「回填錨」本身都是一個新 commit，而新 commit 又不在錨的覆蓋範圍內 ⇒ 追下去是無窮回歸。
判準已刻意設計成容許這個狀態（`head-sha` 只要求是 HEAD 或其祖先），
而「錨有沒有覆蓋最新一次 push」歸 pre-push／收輪清單（見 ONBOARDING 該段的表格與殘留缺口揭露）。

**R76 若要收緊**：正解是把該項接進 `tools/sync_onboarding_baselines.py` 的 pre-push leg
（那個時點 `origin/main` 尚未前進，比較才有意義）。🔴 **絕不可**做成 CI 判準——
理由見下方 §4 的一般化規則，R75 已用 main 上三支全紅付過學費。

---

## 3. 本輪做了什麼（詳情一律見具名證據檔，本檔不重複）

- **四方複審全部執行**（R74 交棒第一項）：Architect／SA／QA `APPROVE-WITH-CONDITIONS`、SD **`REJECT`**，
  blocking 共 12 筆全部收斂。詳見 `docs/06_quality/CrossPlatform_R75_Review_Evidence.md`。
- **缺陷列**：`DEF-101-804` ~ `DEF-101-831`（含兩筆未結：`810`／`811`，皆承接 R76）。
- **技術債**：未結列 97 → 82，25 筆逐筆查證後誠實結案（每筆附當回合複驗指令與 rc）。
- **排程 Job 生命週期裁決**：`docs/06_quality/Scheduled_Jobs_Lifecycle_Review_R75.md`。

**12 筆 blocking 裡有 8 筆是「閘門自己沒有鑑別力或射程失明」**——這類缺陷不可能由跑閘門發現。
這反證了 `DEF-101-801` 那條「不得以閘門全綠替代四方複審」的禁令是對的，該列已據此結案。

---

## 4. 本輪最重要的一條規則（已升為機械物）

> **判準的比較對象若會隨「被該判準所判的那個動作」本身而改變，這個判準結構上不可滿足。**

R75 第一版把雲端錨判準寫成「必須覆蓋 `git rev-parse origin/main`」。而 `origin/main` 正好在
push 的那一瞬間前進：本機 pre-push 時它還指上一個 commit（綠、放行），CI 在 push 之後跑，
那時它已等於被測 commit 自己 ⇒ 要讓 commit X 通過，X 的內容必須寫進 X 自己的 sha。
**實測代價：main 上三支 workflow 全紅，且每一次 push 都會紅。**

機械物：`tools/tests/test_doc_loc_baseline_freshness_r60.py::TestR75CloudCriteriaAreSatisfiableAtAnyCommit`
——讀 `cloud_*` 判準家族的**執行碼**（以 AST 剝掉 docstring 與註解，教訓可以寫在散文裡但不得寫進判準），
出現任何 remote-tracking 參照（`origin/`／`@{u}`／`ls-remote`／`--remotes`／`for-each-ref`）即當場判紅。

**遇到這類問題的處置**：把判準拆成「內部一致性／非假性」（可住 repo 內、CI 會跑）與
「與外部世界對帳」（只能住在動作發生的那個時點）兩半。

---

## 5. 交給 R76 的事（依優先序）

### 5-1 🔴 需掌舵者提權（R75 無法代做，已連續兩輪卡住）
🔴 **R76 回執：本項已完成**——掌舵者提權套用後，`python tools/check_scheduled_task_drift.py`
當回合實測 `status=ok`／**rc=0**（兩支任務各 7 項全符），`run_local_nightly.ps1` 的
`status=drift` 具名豁免亦已於 R76 移除（白名單只剩 `ok`／`skip`）。以下為 R75 當時的原文，
逐字保留為時代快照，**不要照著再跑一次**（無害但無事可做）。

排程漂移偵測器 `python tools/check_scheduled_task_drift.py` 回 rc=1、5 項漂移。
其中兩項（`ExecutionTimeLimit=PT72H` 應為 `PT4H`、`MultipleInstances=IgnoreNew` 應為 `StopExisting`）
**已實際造成一整天的觀察期進帳消失**（08-01 那輪跑了 35.6 小時，UTC 08-02 三軌零進帳）。

```powershell
# 以系統管理員身分開 PowerShell
powershell -ExecutionPolicy Bypass -File <repo 根>\tools\install_windows_nightly.ps1
# 🔴 不帶參數會把 smoke 從 23:30 移到 21:30（有 active 機械鎖要求 smoke < nightly）
#    要維持現況須顯式宣告違反：-NightlyAt 22:30 -SmokeAt 23:30 -AllowSmokeAfterNightly
```
套用後 `check_scheduled_task_drift.py` 應回 rc=0（`status=ok`），
且 `AutoClaude/tools/run_local_nightly.ps1` 內對 `status=drift` 的具名豁免**應改回硬失敗**
（該處已寫下可判定的解除條件並會在 `status=ok` 出現時主動印出提示，不靠任何人記得）。

### 5-2 觀察期收尾（不需 code，只需拍板）

> 🔴 **R76 回執（2026-08-05）— 本節下方原文的四軌狀態已被 R76 自己推翻，先讀這裡**：
> R76 PKG-D 依 R76-13 **收緊了兩支 GA 判準**（新增 staleness ＋ 窗內連續性：last-30 筆的
> 日曆跨度必須 ≤ 40 天）。方向正確、**不得放寬**——原判準只數筆數，於是「44 筆散在 58 個
> 日曆天、中間有 12 天全黑」也算達標，那不是觀察期要證明的事。代價是狀態翻轉：
>
> | 軌 | R75 原文 | **R76 現查（當回合實跑 `--json`）** | rc |
> |---|---|---|---|
> | mutation | ✅ | ✅（`locked=true`，源碼未動） | 0 |
> | AC4 | ✅ | ✅ | 0 |
> | obs GA | ✅ 達標 | ❌ `status=sparse green_streak=44/30 span=58/40 max_gap=12d` | **1** |
> | drift GA | ⏳ 差 2 筆 | ❌ `status=sparse green_streak=28/30 span=65/40 max_gap=12d` | **1** |
>
> **新的可判定終點**：綁住兩軌的不再是 `green_streak` 而是 **span**，所以「再等兩天」
> 這個心智模型整個作廢（drift 補滿那 2 筆之後 span 仍約 63 天）。以兩支工具的判準公式
> 對現有帳本日期逐日試算：**obs 需再連續進帳 17 晚（最早 2026-08-21）／drift 18 晚
> （最早 2026-08-22）**，前提是每晚 22:30 排程不漏跑——**中間漏一晚就往後推**，因為
> 連續性本身現在就是判準。
>
> **拍板時點因此順延**，且在兩軌轉綠之前**不得降頻**（每週採集結構上永遠滿足不了
> span ≤ 40 天這一條）。⚠️ `AutoClaude/.g0_readiness.json` 是每晚重生的量測檔，可能
> **早於**本次判準變更 —— 讀它之前先看 `generated_at`；今晚 nightly 跑完它會自己把
> obs 翻成 `pass=false`，不必手改。詳見
> `docs/06_quality/Scheduled_Jobs_Lifecycle_Review_R75.md` §0 的 R76 全域訂正塊。

以下為 R75 當時的原文，逐字保留為時代快照：

G0 四軌：mutation ✅／AC4 ✅／obs GA ✅／**drift GA 差 2 筆**（一天最多入帳 1 筆，同 UTC 日去重）。
機器可讀憑證：`AutoClaude/.g0_readiness.json`（本輪起，已 gitignored ⇒ 只存在於產出它的機器）。
四軌全綠後由 PM 拍板；建議**降頻而非移除**——AC4 有 `STALENESS_MAX_DAYS=30`，
停止採集 30 天後會自己翻回未達標、W1 入場憑證跟著失效。

### 5-3 帳本兩筆未結（皆承接 R76）
- `DEF-101-810`：`run_local_nightly.ps1` 無頂層 `param()`／`-Help`，`--help` 會直接開跑 7 stage nightly。
- `DEF-101-811`：`archive_defect_log.py --apply` 對可搬清單全有全無、無排除入口
  （`--ack-handoff` 只能加入不能排除）⇒ 每輪都要手工把本輪列還原回主檔。建議加 `--keep`／`--only`。

### 5-4 近期必修（不修會卡住下一個動這支檔的人）
`tools/check_script_parity.py` 卡在 1618 行 shrink-only 棘輪、實測 **1617**，**只剩 1 行餘裕**。
加一行就破閘，而棘輪的解鎖程序要求先抽共用模組＋在缺陷帳本具名。建議主動瘦身或抽模組。

### 5-5 已知缺口（誠實劃界，非遺漏）
- **65 筆 `tool-absence` 站點未補標籤**：`untagged_tool_absence_sites()` 已提供清單但刻意不接 rc
  （存量橫跨三棵樹、一上線判紅會與並行包互踩）。「不隱形」已由普查棘輪保證（`unclassified=0`）。
- **AISDLC_SDD 凍結版 36 筆 stdio 行內複本**：Copy-on-Evolve 不可改，已單獨成一格，
  讓「不可修的存量」與「可修的存量」在基線表上分得開。
- **鐵律三 8 項觸發清單仍有 4 項無掃描器**（根 `CLAUDE.md` 該表為 shrink-only 棘輪，只准變少）。

---

## 6. 禁止事項（R76 動工前先讀）

1. ❌ 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、不准跳過或註解掉失敗測試。
2. ❌ 不准為了讓數字好看而調高任何門檻／棘輪／體積上限（砸溫度計）。棘輪一律只准變少。
3. ❌ 不准把「尚未查核」寫成「已查核」——雲端結論、觀察期達標、平台覆蓋皆同。
   `pending` 這類誠實宣告存在的理由就是讓「還沒做」有合法的表達方式。
4. ❌ **Windows 上禁用 Bash 工具**（根 `.claude/settings.json` 已註冊 PreToolUse 阻斷）；
   禁裸 `cd`；算行數／搜尋一律用 Read／Grep 不經 shell。
   R75 實證：手動餵 pre-push payload 時用 PowerShell 管線導致 CRLF，
   讓 `remote_sha` 尾帶 `\r`、`merge-base` 失敗 ⇒ **載具給了假訊號**，一度誤判成 force-push 被擋。
5. ❌ 不准在訂正註記裡逐字抄錄被訂正的假話（樹裡不留假句子，有鎖在抓）。
   同理：**不要在錨那一行的散文裡寫任何 `欄位=值` 形態的字樣**——解析取最後一個，散文會靜默覆蓋真欄位值。
   本輪此坑復發兩次，第二次已被 fail-loud 判準當回合攔下。
6. ⚠️ 多 agent 同樹作業時，看到與自己改動無關的紅先 `git status` 核對歸屬，
   不要算成自己的、也不要去修別人的檔（本 repo「並行突變互踩假紅」已重演三次以上）。

---

## 7. R75 自身的失誤紀錄（供 R76 對照，不隱藏）

1. **我把帳本列寫得太詳細**，吃掉剛騰出的 21KB 餘裕、逼近硬閘，只好再派人做兩層化。
   教訓：帳本列是索引不是報告，詳情一開始就該進具名證據檔。
2. **我為了防「本機綠雲端紅」而加的判準，自己造成了一次「本機綠雲端紅」**（見 §4）。
2 筆都不是模型能力問題，是**沒有先問「這個判準在最壞情況下會不會不可滿足」**。
3. **我在缺陷列裡寫了半形 `|`**（在反引號內列舉副檔名），把表格欄位切壞、兩道閘門轉紅。
4. **我一度把判準的出處講錯**（說是本輪新加的，實際是 R74 既有判準第一次被觸發），由執行者訂正。
