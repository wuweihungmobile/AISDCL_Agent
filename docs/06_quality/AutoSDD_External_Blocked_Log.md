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
| DEF-101-693 | Windows 實機 | 2026-08-21 | 下一個 Windows 真機輪逐列覆核 windows-smoke 22 步（`tools/tests/test_smoke_ci_sync.py::test_registered_smoke_groups_exist_in_that_script` 先行，另需真機執行紀錄） | 2026-08-21 |
| DEF-101-703 | GitHub Actions 帳務 | 2026-08-21 | `*-nightly-full`（windows-compat-ci.yml／macos-compat-ci.yml）至少一次排程視窗成功（`gh run list --workflow=windows-compat-ci.yml --event schedule` 見 `conclusion=success` 且 `steps>0`），之後移除 `WAIVER_UNTIL` | 2026-08-27 |
| DEF-200-186 | GitHub Actions 帳務 | 2026-08-21 | 拆自 `DEF-101-866` 條件 (b)：`gh workflow run windows-compat-ci.yml --ref main` 確認 nightly-full job 真的有 `steps`，端到端全綠 | 2026-08-27 |
| DEF-200-063 | Windows 實機 | 2026-08-21 | Windows 真機執行 `claude -p --debug hooks` 取得 `Hook SessionStart.*success`，同時檢查負面表徵（彈窗真的停止、`pythonw.exe` 載具解析成功、`-WindowStyle Hidden` 實效） | 2026-08-21 |
| DEF-200-147 | Windows 實機 | 2026-08-21 | Windows 真機重跑 govwrite 九格 rc 矩陣＋NTFS 大小寫繞行探針（`.ENV` 等形態）＋修3/修4 的 schtasks 取證（`NextRunTime` 值憑證）三項 | 2026-08-21 |
| DEF-200-174 | GitHub Actions 帳務 | 2026-08-21 | 帳號所有者查 GitHub Billing 頁面確認 spend limit 已調高或 runner 計費已恢復，`gh api repos/.../actions/runs` 觀測對應 job 的 `runner_id≠0` | 2026-08-27 |

## 複查記錄

> 「最近複查日」欄僅存放純 ISO 日期；完整複查敘事（機械取證細節）逐字搬遷至本節，
> 依 DEF-ID 分節保全，不刪減任何已驗證內容，僅搬遷位置。

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
