# AutoSDD External Blocked Log — 外部阻塞軌

> 機械物②（R99「帳本減半」，PRD 掌舵者裁決）。本表登記**真的卡在外部世界、我們自己
> 這一刻機械上做不了任何事**的缺陷（E 類），與主帳本
> [`AutoSDD_Defect_Log.md`](AutoSDD_Defect_Log.md) 的「我們自己欠的債」（A 類，可修）
> 分軌，讓主帳本的未結列數（`--unresolved-count` 的 warn/fail 分母）量到的是真正能被
> 修復速度影響的量，不被外部世界的節奏稀釋或膨脹。
>
> 🔴 **本表不是規避未結列警戒線的後門**：判準與稽核見
> `tools/lib/ledger_closing_guards.py`（`external_blocked_log_problems()`）——
> - **具名阻塞源限枚舉**（唯一機械物，防止把 A 類偽裝成 E 類）：合法值只有
>   `GitHub Actions 帳務`／`Windows 實機`／`上游套件`／`其他-<具體理由>` 四種形態，
>   自由文字一律 fail。
> - **交叉鎖**：同一 DEF-ID 不得同時出現在本表與主帳本未結列。列進本表前，主帳本該列
>   應收斂為指向本表的索引（而不是仍以未結狀態留在主帳本自我複製一份）。
> - **複查逾期**（14 天未更新「最近複查日」）只 warn 不 fail：外部阻塞源本來就不是
>   我們能控制的節奏，但沒人回頭看就會變成永久垃圾桶，故仍要有人定期複查是否還成立。
> - `python tools/check_defect_log_crossref.py --unresolved-count` 會印出本表筆數
>   （不計入主帳本 warn/fail 分母，但**永遠可見**，不得悄悄消失）。
> - 本表只收「阻塞源真的在外部世界」者；跨輪工程／內部授權型結構債走姊妹軌 AutoSDD_Structural_Debt_Log.md（判準同源、枚舉互斥）。
>
> 資料列由書記／收尾窗口逐筆登記；本檔本輪僅落地表頭與格式定義，空表即合規。

## 格式定義

| 欄位 | 說明 |
|---|---|
| `DEF-ID` | 對應主帳本原本的缺陷編號 |
| `具名阻塞源` | 合法值：`GitHub Actions 帳務`／`Windows 實機`／`上游套件`／`其他-<具體理由>`（`其他-` 後必須緊接非空白的具體理由，不得裸寫「其他」當萬用桶） |
| `阻塞起始日` | ISO 日期（`YYYY-MM-DD`），本缺陷轉入外部阻塞軌的日期 |
| `解鎖條件（可機械查）` | 描述何種可觀測事件發生後應該重新評估（例如：「GitHub Actions 免費額度重置」「Windows 實機到位可跑 `tools/check_hooks_liveness.py`」），愈可機械驗證愈好 |
| `最近複查日` | ISO 日期，最近一次確認阻塞仍成立的日期；逾 14 天未更新會被 warn |

## 缺陷總表

| DEF-ID | 具名阻塞源 | 阻塞起始日 | 解鎖條件（可機械查） | 最近複查日 |
|---|---|---|---|---|
| DEF-101-518 | GitHub Actions 帳務 | 2026-08-21 | 帳務恢復後一次真實 `windows-latest` run 觀測到 bootstrap 之後步驟確實用到 `.venv` 的 python（`gh run list --workflow=windows-compat-ci.yml` 見 `conclusion=success` 且 `steps>0`） | 2026-08-27 |
| DEF-101-693 | Windows 實機 | 2026-08-21 | 下一個 Windows 真機輪逐列覆核 windows-smoke 22 步（`tools/tests/test_smoke_ci_sync.py::test_registered_smoke_groups_exist_in_that_script` 先行，另需真機執行紀錄） | 2026-08-31 |
| DEF-101-703 | GitHub Actions 帳務 | 2026-08-21 | `*-nightly-full`（windows-compat-ci.yml／macos-compat-ci.yml）至少一次排程視窗成功（`gh run list --workflow=windows-compat-ci.yml --event schedule` 見 `conclusion=success` 且 `steps>0`），之後移除 `WAIVER_UNTIL` | 2026-08-27 |
| DEF-200-186 | GitHub Actions 帳務 | 2026-08-21 | 拆自 `DEF-101-866` 條件 (b)：`gh workflow run windows-compat-ci.yml --ref main` 確認 nightly-full job 真的有 `steps`，端到端全綠 | 2026-08-27 |
| DEF-200-174 | GitHub Actions 帳務 | 2026-08-21 | 帳號所有者查 GitHub Billing 頁面確認 spend limit 已調高或 runner 計費已恢復，`gh api repos/.../actions/runs` 觀測對應 job 的 `runner_id≠0` | 2026-08-27 |
| DEF-200-075 | 其他-macOS實機（darwin執行面量測值，Windows結構上量不到也修不了） | 2026-08-27 | 回 mac 真機後第一動作＝重量 AutoClaude 樹 skip census（量測入口見主帳本該列配方）；macos-compat-ci 長期紅不可依賴 | 2026-08-27 |

## 複查記錄

> 「最近複查日」欄僅存放純 ISO 日期；完整複查敘事（機械取證細節）逐字搬遷至本節，
> 依 DEF-ID 分節保全，不刪減任何已驗證內容，僅搬遷位置。

### DEF-200-063（複查 2026-08-31＝解鎖條件達成，列已移出本表）

R114 Windows 真機取證：`claude -p --model haiku --debug hooks --debug-file h.log "ok"` 取得逐字
`Hook SessionStart:startup (SessionStart) success:`＋`provided additionalContext (191 chars)`；
`pythonw.exe` 載具 `Test-Path`＝True；同 log 兩筆 `EFTYPE` 屬雙載具佈線之異平台條目設計性失敗
（`tools/lib/hook_wiring.py:149/:166` 記載），非缺陷；哨兵 schtasks `LastTaskResult=0`、
`NextRunTime=2026/8/31 14:23:02`（15 分鐘巡邏靜默運行＝彈窗表徵消失的機械旁證）；
`-WindowStyle Hidden` 機械物實機重跑 `test_check_hooks_liveness.py`＝170 passed＋132 subtests。
逐字證據＝`CrossPlatform_R114_WakeChain_Review.md` §3.1。

### DEF-200-147（複查 2026-08-31＝解鎖條件達成，列已移出本表）

R114 Windows 真機取證三項全達成：①12 列 rc 矩陣
`TestGovernanceFilesAreReadOnlyWhenUnattended`＝12 passed＋24 subtests passed；
②NTFS 大小寫繞行探針＝已存在檔變體全數命中（`.ENV`→`.env` 等）——原始疑慮解除；
探針同時揭露「尚不存在的保護面目標」兩形態繞過＝新缺口另立 `DEF-200-238`（主帳本）；
③schtasks 取證＝哨兵 `NextRunTime` 值憑證到手，halt 多軸武裝 argv 由
`test_context_budget_guard.py` SentinelWiring 實機 12 passed 釘住（真 halt 本窗未發生，誠實留白）。
逐字證據＝`CrossPlatform_R114_WakeChain_Review.md` §3.2。

### DEF-101-693（複查 2026-08-31）

複查：R114 真機已跑先行判準（sync 測試 1 passed）＋`windows_smoke_local.ps1` 原生 PS 5.1 載具
實跑 PASS=12 FAIL=0 rc=0（本地可化步驟全綠）；但 CI windows-smoke 22 步中 bootstrap 往返、
dev_start、AutoClaude 子集／integration_gate、SDD ci-gate 雙軌數列本輪無獨立實跑紀錄 ⇒
「逐列覆核」未完成，阻塞仍成立、列保留。證據＝`CrossPlatform_R114_WakeChain_Review.md` §3.3。

### DEF-101-518（複查 2026-08-27）

複查：repo 已轉 Public、帳務阻塞已解除〔run `33041308203` 30 steps 實跑〕，但
windows-smoke job 仍 `conclusion=failure`〔真缺陷，非帳務〕，`conclusion=success`
這半條件尚未達成，故仍留本表。

### DEF-101-703（複查 2026-08-27）

複查：最近一次 `--event schedule` run 為 `32700687523`／`32704389767`
（2026-08-24），彼時兩者仍 `steps=0`〔帳務阻塞〕；帳務今日已確認解除，但下一個
排程視窗尚未發生，無法用 `workflow_dispatch` 頂替（條件明寫 `event schedule`），
故仍留本表待下次排程觀測。

### DEF-200-186（複查 2026-08-27）

複查：`gh workflow run` 手動觸發 run `33044520102` 已完成，`conclusion=failure`。
「有 steps」這半條件已達成（windows-smoke 30 steps／nightly-full 11 steps，皆非
帳務空轉），證實帳務阻塞確已解除；但「端到端全綠」未達成——windows-smoke 與
nightly-full 兩 job 皆 `conclusion=failure`（真缺陷，非帳務），故仍留本表。

### DEF-200-174（複查 2026-08-27）

複查：`runner_id≠0` 這半條件已機械確認〔run `33041308203` job `98415310692`：
`runner_id=1000003749`〕；repo 已轉 Public 佐證帳務面已解除，但「帳號所有者查
Billing 頁面」是條件明文要求的人工動作，代理無 `user` billing scope
（`gh api users/.../settings/billing/actions` 回 404 + 提示需
`gh auth refresh -s user`），無法獨立機械代查，故仍留本表待帳號所有者親自確認後
移除。
