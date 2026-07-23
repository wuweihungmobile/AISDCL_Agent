# AutoSDD 缺陷帳本 — Archive 07（R32 四方一審/二審裁決敘事）

> 本檔為 `AutoSDD_Defect_Log.md` 依 DEF-99-001 輪替政策搬遷之歷史敘事區段（R33 主檔逼近 256KB 界線時建立），**原文逐字保全、零刪除**（搬移非刪除，git 亦保歷史）。內容為 R32 「四方一審／二審裁決總結」敘事段落，其缺陷現況已被主檔上方「缺陷總表」live 狀態取代，本檔僅供歷史脈絡查閱。

---

## R32 四方複審裁決總結（2026-07-24）

真 Mac 環境複審——本輪使用者明確要求「請架構師 Architect 全面檢視多平台相容性的設計架構是否合理，並進行最佳化改善設計」，且要求 Architect/SA/SD/QA 四方獨立審查本次修改、有問題即修復、再經四方核准通過。

- **前置基線**：AutoClaude pytest 3608 passed/207 skipped（沿用 R31 收尾狀態，本輪未重新量測因下述 `.venv` 污染問題）、`tools/tests/` 381 passed/3 skipped、`AISDLC_SDD ci-gate.sh` 雙軌全綠，本輪動工前重跑確認與 R31 收尾狀態一致、無回歸。
- **全面掃描（Scan-A/B/C/D 四維度 + Architect 架構深度評估，皆背景 agent 獨立平行執行）**：A（Shell/PowerShell）零新發現，確認 R1~R31 累積修復皆穩定；B（Python 跨平台）發現 `run_act_core.py` 零測試覆蓋（DEF-101-286）與 `_KNOWN_SUBPROCESS_ONLY_CONSUMERS` 過期項（DEF-101-287）；C（CI/排程/hooks 基建）發現 `test_bootstrap_ps1.py` 平台守門缺失 P1（DEF-101-285）；D（文件/帳本一致性）發現 footer 日期落後（DEF-101-288）與 pytest 基線落後 +11（DEF-101-289，本輪因環境污染未修復，如實記載）；Architect 深度架構評估判定「機械守門工具生態／雙原生腳本收斂候選／nightly stage 統一設計」四面向維持不變，唯一判定需**根本重做**（非局部補強）者：`bash_probe` 三鏡射連續 5 輪（R27~R31）未收斂 DEF-101-275，屬本 repo 內少見「同根因復發≥2 次」的結構性案例。
- **修復落地**：`test_bootstrap_ps1.py` 平台守門補上（DEF-101-285）；`run_act_core.py` 補 28 case 測試（DEF-101-286）；`bash_probe` 三處收斂為共用資料規格 `tools/lib/bash_probe_spec.py` + coreutils 驗證，關閉 DEF-101-275；過程中連鎖發現並修復 CI paths 兩處遺漏（DEF-101-291/292）；文件類 P3/P4 四項（DEF-101-287/288/294，及 DEF-101-289 如實記載未修）。

### 四方一審（Architect/SA/SD/QA 獨立審查，皆於主工作樹直接操作、不使用 `isolation: worktree`——鑑於審查對象含大量尚未 commit 的異動，過去已證實 worktree 會讓審查員看到過時程式碼）

- **Architect**：**REJECT**——親自重跑重現兩項缺陷：① `test_bootstrap_ps1.py` 疑似未真正接上平台守門（後經主控查證為並行 bug-injection 瞬間污染的假象，二審重驗證實已修復）；② `windows-compat-ci.yml`／`macos-compat-ci.yml` 同樣漏收 `tools/lib/bash_probe_spec.py`（DEF-101-292，真實缺陷）。同時確認共用資料規格設計本身合理、三份消費者獨立測試鑑別力未喪失。
- **SA**：**APPROVE-with-conditions**——逐項驗證 5 項聲稱修法皆對應解決原始問題；親眼撞見 `bash_probe_spec.py` 一度被改成 echo-only 過渡態、既有測試全綠，發現 DEF-101-293 必修條件。
- **SD**：**APPROVE-with-conditions**——對本輪全部異動逐項 bug-injection（四大類皆確認鑑別力），另指出兩份 workflow 檔異動看似超出原始清單範圍（後經釐清為主控同期修復 Architect 缺陷 2 所致，非神秘變更）；並主動揭露複審過程中工具輸出出現偽造 "system-reminder" 誘導其隱瞞檔案修改，明確未採信、獨立以 diff/sha256 核對。
- **QA**：**APPROVE-with-conditions**——用「拿掉 dirname 改用純 echo」bug-injection 獨立印證 DEF-101-293；對 `run_act_core.py` 新測試、`_windows_pwsh_available()` 邊界情境、文件同步逐一挑剔，僅此一項必修。

**針對一審發現的修復**：① `.github/workflows/macos-compat-ci.yml`／`windows-compat-ci.yml` 補上 `tools/lib/bash_probe_spec.py`（DEF-101-292）；② 新增 `tools/tests/test_bash_probe_spec_contract.py` 補齊 `PROBE_CMD` 裝飾性斷言缺口（DEF-101-293）；③ 向四方說明兩份 workflow 檔異動為主控同期修復所致，非未知變更。

### 四方二審（SendMessage 保留一審上下文複審，皆親自重跑驗證修復落地，另針對 SA/QA 發現的必修條件各自用不同角度重新 bug-injection）

- **Architect**：**APPROVE**（獨立重驗兩項缺陷皆已修復；額外佐證「並行 bug-injection 互相污染」現象確實存在——複核 `test_bash_probe_spec_contract.py` 時也遇到同款瞬間假紅；認可掃描器正則不修、改手動列舉的判斷）
- **SA**：**APPROVE**（無條件；以兩種不同於一審的 bug-injection 角度〔改期望值 vs 改生產端 wiring 繞過 spec〕複驗 DEF-101-293 修復皆有鑑別力）
- **SD**：**APPROVE**（無條件；複核兩份 workflow 檔異動內容合理；對新契約測試做兩級遞增退化 bug-injection 皆抓到；再次遇到偽造 system-reminder 仍未採信、獨立驗證）
- **QA**：**APPROVE**（唯一必修條件——`bash_probe_spec.py` 補文件說明第四消費者——已由主控直接補上並經 QA 本人最終確認）

四方二審最終結論：**全數 APPROVE**。本輪 R32 全部異動（`AISDLC_SDD/scripts/bash_probe.py`、`AISDLC_SDD/scripts/tests/test_bash_probe.py`、`AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py`、`tools/lib/bash_probe_spec.py`〔新〕、`tools/tests/test_bootstrap_ps1.py`、`tools/tests/test_pre_push_dispatcher.py`、`tools/tests/test_git_hooks_install_common.py`、`tools/tests/test_bash_probe_spec_contract.py`〔新〕、`AutoClaude/tests/tools/test_run_act_core.py`〔新〕、`AutoClaude/CLAUDE.md`、`.github/workflows/aisdlc-sdd-ci.yml`、`.github/workflows/macos-compat-ci.yml`、`.github/workflows/windows-compat-ci.yml`、`docs/06_quality/AutoSDD_Defect_Log.md`）可放行。**環境異常揭露**：SD 在一審與二審皆回報工具輸出出現偽造 "system-reminder"，誘導其向使用者隱瞞檔案修改，兩次皆未採信、獨立以 diff/sha256 核對確認實際內容，已如實記錄不隱瞞；另有多次「並行 bug-injection 互相污染」暫態假紅/假綠現象（Architect 二審亦獨立佐證），皆屬已知的並行測試雜訊，非程式缺陷。**已知限制（如實記載）**：DEF-101-289（ONBOARDING.md §7 pytest 基線落後 +11）本輪因本機 `.venv` 已裝 postgres 選配、無法在不重蹈 R13 舊錯的前提下重新量測，維持 open，需下一輪以乾淨 venv 重驗。
