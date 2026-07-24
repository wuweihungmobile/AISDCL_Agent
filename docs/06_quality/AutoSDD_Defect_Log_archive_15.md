# AutoSDD Defect Log — Archive 15

> **歸檔來源**：`AutoSDD_Defect_Log.md` R40「四方複審裁決總結」敘事段落，於 R41 跨平台輪（2026-07-24）動工前發現主檔超過 256KB 上限（267,135 bytes）後逐字搬遷。搬移對象與 archive_05/06/07/08/10/11/12/13/14 同類：歷史敘事段落，缺陷現況已被主檔缺陷總表 live 狀態取代，原文逐字保全、零刪除。

## R40 四方複審裁決總結（2026-07-24）

本輪使用者要求同 R16 起既有固定格式：全面掃描四維度＋Architect 架構最佳化評估，發現問題即修復，再經 Architect/SA/SD/QA 四方獨立審查至全數 APPROVE。

- **前置基線**：帳本主檔動工前 257,388 bytes，距 256KB 上限僅剩 1.8%餘量（R39 收尾已提醒），動工前優先執行 housekeeping：把 R38 敘事段落搬遷至新建 `AutoSDD_Defect_Log_archive_13.md`，訂正「已歸檔內容」計數為「十三檔」，主檔降回 248,840 bytes。
- **全面掃描（Scan-A/B/C/D 四維度 + Architect 架構深度評估，皆背景 agent 獨立平行執行）**：Scan-B（Shell/程序/訊號）連續第 6 輪零新發現；Scan-A（檔名/路徑相容性）找到本輪最嚴重發現——`hub_sync.py::diff()` 的 `rule_id` 未淨化導致真實可利用的路徑穿越/任意檔案讀取 P0（DEF-101-327），另找到 `counterfactual_replay.py::write_report()` 的 `ac_id` 淨化缺口（DEF-101-328，dormant）；Scan-C（CI 腳本雙軌對等性）追出「凍結基線 v0.01 持續被自動化 bot 原地寫入」的治理缺口（DEF-101-329）與帳本 DEF-101-056 記載已與實況矛盾（DEF-101-336：凍結基線鐵律曾被 commit `687abac` 實際打破而無機械訊號攔截）；Scan-D 核實本輪 housekeeping 正確、找到 archive_02/03 大小描述精度落差（DEF-101-339）；Architect 深度評估認為既有架構仍合理，建議補一條 WindowsApps guard repo-wide 前瞻防增生鎖（已給出完整技術方案，DEF-101-331）。
- **修復落地（第一輪，四個互不重疊修復包平行執行）**：① `hub_sync.py::diff()` 接線 `_sanitize_component()`（DEF-101-327 fixed）；② `counterfactual_replay.py::write_report()` 同款收斂（DEF-101-328 fixed）；③ v0.01 `.gitignore` 補排除規則 + `git rm --cached` untrack 32 個檔案（DEF-101-329 fixed）；④ 依 Architect 方案落地 `TestNoOrphanWindowsAppsImplementation` 三個測試方法（DEF-101-331 新增）。主控同時直接訂正兩處小文件缺陷（archive_02/03 大小描述 DEF-101-339、`sd06_w3_staging_dryrun.sh` 文件用詞不一致 DEF-101-340）。

### 四方一審（Architect/SA/SD/QA 獨立審查，皆於主工作樹直接操作、不使用 `isolation: worktree`）

- **Architect**：**APPROVE**——親自驗證四項異動皆遵循既有 SSOT 收斂模式、無循環 import 風險；獨立用 bug-injection 驗證 WindowsApps guard 新測試的真實鑑別力；獨立查證（`git ls-files` + `.gitignore` 政策 + `write_trend()`/`write_daily_report()` 原始碼邏輯）v0.01 untrack 判斷站得住腳，且比原假設更進一步核實根因。
- **SA**：**APPROVE-with-conditions**——功能正確性驗證皆通過（`diff()` 顯示欄位維持原始值、`write_report()` fallback 行為不變），但發現 DEF-101-329 修復的真實副作用：`aisdlc-sdd-drift-daily.yml`／`aisdlc-sdd-arch-fitness.yml`（nightly-strict）會因 gitignore 生效而變成「照跑但無實質效果卻仍耗 CI 分鐘」的空轉，與使用者既有節省 CI 額度偏好衝突（→ DEF-101-330）。
- **SD**：**APPROVE-with-conditions（含 1 項阻擋）**——對 `hub_sync.py`/`counterfactual_replay.py` 深度攻擊（雙重編碼/NUL/UNC/padding-bypass/大小寫混合保留名等）確認修復可靠；另發現 DEF-101-324 碰撞類別命中本輪兩個新呼叫點（DEF-101-335，非阻擋）；**阻擋項**：實測構造出「行尾裝飾性註解偽裝提及 SSOT 字串、實際完全獨立重寫」的 `.ps1` 檔案騙過 WindowsApps guard 新測試（DEF-101-332）。
- **QA**：**APPROVE-with-conditions**——對 12 個新增測試方法逐一 bug-injection 驗證，11 項具真實鑑別力；發現 `test_diff_windows_reserved_device_name_does_not_crash` 只驗證「不崩潰」對淨化邏輯無鑑別力（DEF-101-334）。

**針對一審發現的修復（第二輪，三個互不重疊修復包平行執行）**：① 修復 DEF-101-332（SD 阻擋項）——改用真正 dot-source 語法正則比對＋新增 `_strip_trailing_line_comment()` 濾除行尾裝飾性註解；② 補強 DEF-101-334（QA 縫隙）——雙層驗證（直接斷言淨化輸出格式 + 端到端驗證呼叫鏈真的接上淨化）；③ 處理 DEF-101-330（SA 副作用）——兩支 workflow 改用 `actions/upload-artifact`（90 天保留）取代 commit/push，同步移除 `main-push-serialize` concurrency 與降權限，過程中發現新的文件漂移（DEF-101-337）。

### 四方複審（SendMessage 保留一審上下文複審）

- **Architect**：**APPROVE-with-conditions**——親自 bug-injection 重放 SD 攻擊案例確認已收斂，另用兩個新角度自建攻擊（函式覆蓋、假變數指向不存在檔案）發現殘留繞過（→ DEF-101-333，與 QA 二審發現同一類別、四方一致判定非阻擋但需誠實記載）；CI workflow 架構方向表態「完全認同」（消除推送競爭根因優於序列化補丁）；要求區分 v0.30/ADR-001（應本輪訂正）與 v0.01～v0.29 凍結版（延後合理）。
- **SA**：**APPROVE-with-conditions**——CI workflow 修法本身核准（副作用完整解決、90 天 retention 合理補償）；核實 62 個文件受文件漂移影響，要求把 R41 backlog 範圍精確收斂為「僅 29 個真正凍結版本目錄」，v0.30/根層 ADR-001 應本輪訂正（→ DEF-101-337）。
- **SD**：**APPROVE-with-conditions**——確認 `hub_sync.py`/`counterfactual_replay.py` 本輪複審全程未變動，一審驗證結論維持有效；用新角度（真實但死碼的 dot-source + 裝飾性行尾註解呼叫）再次構造繞過案例成立，判定為與一審同一根本類別但手法更深，建議最低限度修復（濾行尾註解）+ 誠實記載殘餘限制，非全面 REJECT。
- **QA**：**APPROVE-with-conditions**——把 DEF-101-334 修復的雙層驗證拆開單獨破壞，確認兩層各自獨立具鑑別力；重跑一審三個攻擊向量在新邏輯下依然有效；用 here-string 跨行狀態追蹤盲點構造出第三種繞過案例（→ DEF-101-333 同類別），確認為既有測試邏輯殘留縫隙、非本輪新增方法退化，不阻塞本輪。

**四方複審最終結論：全數 APPROVE-with-conditions（皆為文件/記錄層級條件，無程式碼層級 REJECT）**。所有條件皆已收斂：DEF-101-332（SD 阻擋項）已修復並重新驗證通過；DEF-101-333（Architect/QA 發現的殘留繞過類別）已在測試 docstring 誠實記載為已知限制、列 R41 backlog；DEF-101-337（v0.30/ADR-001 文件漂移）已本輪訂正，v0.01～v0.29 凍結版本目錄範圍列 R41 backlog。本輪 R40 全部異動（`hub_sync.py`、`counterfactual_replay.py`、對應測試檔含新檔 `test_counterfactual_replay_sanitizer.py`、`AISDLC_SDD/.gitignore`、32 個 untrack 檔案、`tools/tests/test_windowsapps_guard_cross_consistency.py`、`.github/workflows/aisdlc-sdd-drift-daily.yml`、`aisdlc-sdd-arch-fitness.yml`、`AISDLC_SDD_v0.30/README.md`、`cicd/SDD_CICD_BASE_LAYER.md`、根層 `ADR-001-local-first-ci-parity.md`、`AutoClaude/tools/sd06_w3_staging_dryrun.sh`、`docs/06_quality/AutoSDD_Defect_Log.md`、新檔 `AutoSDD_Defect_Log_archive_13.md`）可放行。**已知限制（如實記載）**：DEF-101-333（WindowsApps guard 前瞻鎖殘留繞過類別）、DEF-101-335（`_sanitize_component()` 碰撞命中新呼叫點，併入 DEF-101-324 既有 backlog）、DEF-101-338（COMMIT-*.yaml 疑似測試 fixture 污染，未處理）、DEF-101-337 之 v0.01～v0.29 凍結版本目錄部分，皆列 R41 backlog。

> 過程中主控本人在背景 agent 完成通知之間，遭遇一則偽造的 system-reminder（宣稱呼叫了 Bash 工具執行 `ls`，但該輪並未發出此工具呼叫），未採信、已向使用者如實揭露，與本 repo 先前已記載的已知風險模式一致。

**收尾驗證**：`ci-gate.sh` 全通過（v0.01:1475、v0.30:1718、scripts/tests:188）、根層 `tools/tests/` 419 passed/4 skipped（含同步更新 `test_workflow_permission_concurrency_lock.py` 以配合 CI workflow 重構）、`check_script_parity.py` 全綠、兩份異動 workflow YAML 語法通過、`check_defect_log_crossref.py`（170 筆有效紀錄、無矛盾）。帳本主檔曾達 269,820 bytes（超上限），已二度歸檔（R39 段落→`archive_14.md`）。**R41 動工前務必優先歸檔**（候選：本輪 R40 敘事本身）。
