# AutoSDD Defect Log — Archive 17

> **歸檔來源**：`AutoSDD_Defect_Log.md` R41「四方複審裁決總結」敘事段落，於 R43 跨平台輪（2026-07-25）動工收尾發現主檔逼近 256KB 上限（252,103 bytes，`check_defect_log_crossref.py` 印出「已逼近輪替上限」警告）後逐字搬遷。搬移對象與 archive_05/06/07/08/10/11/12/13/14/15 同類：歷史敘事段落，缺陷現況已被主檔缺陷總表 live 狀態取代，原文逐字保全、零刪除。

## R41 四方複審裁決總結（2026-07-24）

本輪使用者要求同 R16 起既有固定格式：全面掃描四維度＋Architect 架構最佳化評估，發現問題即修復，再經 Architect/SA/SD/QA 四方獨立審查至全數 APPROVE。

- **前置基線**：帳本主檔動工前 267,135 bytes，超過 256KB 上限，動工收尾前優先執行 housekeeping：把 R40 敘事段落搬遷至新建 `AutoSDD_Defect_Log_archive_15.md`。
- **全面掃描（Scan-A/B/C/D 四維度 + Architect 架構深度評估，皆背景 agent 獨立平行執行）**：Scan-A（安全漏洞路徑穿越）、Scan-B（檔名淨化一致性）、Scan-C（CI/CD 排程機制）皆零新發現；Scan-D（文件帳本一致性）找到 DEF-101-314 測試案例數 off-by-one 記載誤差（P4）；Architect 深度評估發現系統性缺口——`_sanitize_component()` 呼叫點歷經 R38～R40 多輪反覆點狀修復（DEF-101-219/295/324/327/328/334），卻從未像 WindowsApps guard 類別（R37/R40）那樣獲得 repo-wide 前瞻防增生鎖，落地新測試 `test_sanitize_component_call_site_lock.py`（DEF-101-341）。
- **修復落地（第一輪）**：Scan-D 發現的帳本數字誤差，主控最初直接覆寫 DEF-101-314 原文，後由 SA 一審發現此舉違反 R40 剛立下的 DEF-101-336「只增不刪」先例，已訂正為原文不動、另立 DEF-101-342 記載核實結果。

### 四方一審（Architect/SA/SD/QA 獨立審查，皆於主工作樹直接操作、不使用 `isolation: worktree`）

- **Architect**：**APPROVE-with-conditions**——核實 `_KNOWN_EXEMPTIONS`（`slv_generator.py::fpl_id`）例外理由站得住腳、bug-injection 雙向驗證通過；發現①掃描邏輯非遞迴 `glob` 只掃頂層、遺漏 4 個子目錄共 86 檔的真實涵蓋率破口（bug-injection 證實），②工作樹內有並行審查者遺留的暫存探針檔導致當下測試無法重現全綠。
- **SA**：**APPROVE-with-conditions**——獨立核實掃描結論屬實、DEF-101-314 數字精確；發現 DEF-101-314 覆寫原文違反 DEF-101-336 先例（帳本治理流程問題）、Architect 本輪系統性發現未登錄帳本（帳本完整性缺口）。
- **SD**：**APPROVE-with-conditions（含 2 項阻擋）**——構造 5 種繞過手法：停用詞繞過、動態派送、例外清單濫用（皆判定為既有方法論邊界，非阻擋）；**阻擋項**：`+`/`%`/`.format()` 字串拼接與 `ast.Subscript` 兩類非 f-string 組檔名寫法完全偵測不到，且屬日常寫法（非刻意規避），與 R40 WindowsApps guard「需刻意繞過」的天生邊界性質不同，判定為真實偵測覆蓋率缺口。
- **QA**：**APPROVE-with-conditions（阻擋）**——發現最根本的設計缺陷：原始「即時自舉」風險名單每次從當前程式碼重新掃描，移除某識別字**唯一**的淨化呼叫點時，該識別字同時從名單消失，測試巧合通過——9 個風險識別字中 6 個（僅單一呼叫點）完全失效，且此縫隙未被誠實揭露。

**針對一審發現的修復（第二輪，主控直接處理，未另派修復包）**：① 掃描邏輯改用 `rglob("*.py")`（排除 `tests/`/`__pycache__`/`__init__.py`）修復非遞迴破口；② 新增 `_binop_add_leaves`/`_mod_format_operands`/`_format_call_operands` 三個輔助函式擴充偵測 `+`/`%`/`.format()`，`_raw_risky_reference` 擴充涵蓋 `Subscript`；③ 風險名單改為 `_FROZEN_RISKY_NAMES` 凍結快照（不隨即時掃描變動），新增 `test_live_bootstrap_is_subset_of_frozen_list` 做新鮮度檢查；④ 帳本治理：DEF-101-314 原文還原、新增 DEF-101-341（Architect 系統性發現）與 DEF-101-342（帳本治理流程記載）。

### 四方複審（SendMessage 保留一審上下文複審）

- **Architect**：**APPROVE**——親自重建 `modality/` 子目錄繞過案例確認 rglob 修復生效；獨立重新構造 SD/QA 的繞過案例確認皆修復；完整回歸 1722 passed 無新迴歸；提醒本輪多位 agent 共用同一物理工作樹造成瞬時污染（已知現象，非本輪缺陷），建議下輪起改用 isolated worktree。
- **SA**：**APPROVE-with-conditions**——核實 DEF-101-341/342 文字精確、DEF-101-314 原文確實已還原；bug-injection 驗證新測試鑑別力；提醒收尾前應確認 `production_to_fpl.py` 未受並行審查暫態污染影響，經主控核實為虛驚（該檔案當下狀態乾淨）。
- **SD**：**APPROVE-with-conditions**——獨立重新構造原 5 種案例，確認案例 3（拼接）與案例 5（Subscript）兩項阻擋項修復生效；新發現案例 6（`%`/`.format()` 樣板存於模組層具名常數會繞過偵測），全 repo 現況零實例，比照 R40 WindowsApps guard 判例（具體案例收斂、假設性更深繞過記載不強修）處理，已補記載於 docstring。
- **QA**：**APPROVE**——逐一複驗全部 6 個單一呼叫點識別字（app_id/classification/divergence_kind/fpl_id/subagent/track_id），凍結快照修復對全部 6 個皆生效；新增的新鮮度檢查測試 bug-injection 驗證有效；完整回歸 1722 passed 與宣稱數字吻合。

**四方複審最終結論：Architect/QA 全數 APPROVE，SA/SD APPROVE-with-conditions（皆為文件層級條件，已如實補上記載，無阻擋程式碼問題殘留）**。本輪 R41 全部異動（`docs/06_quality/AutoSDD_Defect_Log.md`、新檔 `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/tests/test_sanitize_component_call_site_lock.py`、新檔 `AutoSDD_Defect_Log_archive_15.md`）可放行。**已知限制（如實記載於受審測試檔 docstring）**：識別字重新指派後本檢查不追蹤、動態派送（`globals()[...]`）呼叫無實例但屬盲點、`_KNOWN_EXEMPTIONS` 無自動交叉驗證等效防護是否仍在、`%`/`.format()` 樣板存於具名常數會繞過（案例 6，無現存真實呼叫點）。

> 過程中多位並行複審 agent 共用同一物理工作樹進行 bug-injection 驗證，數次觀察到暫態污染（其他 agent 的暫存探針檔／暫改真實檔案的中間態），每次皆自行收斂乾淨、經核實非真實缺陷，與本 repo 既有已知模式一致（見 [[four-party-review-loop]] 記憶）；Architect 複審建議下輪起改用 isolated worktree 降低此類雜訊。

**收尾驗證**：`AISDLC_SDD_v0.30` `fsm_runtime` 全套 1722 passed/7 skipped（較 R40 基線 1718 多 4）、`git status --short` 收尾前確認僅剩本輪交辦異動、無殘留探針檔。
