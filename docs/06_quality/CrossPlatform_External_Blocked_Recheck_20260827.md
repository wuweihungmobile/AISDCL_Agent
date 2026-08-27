# CrossPlatform External Blocked Recheck — 2026-08-27

本檔承載 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-185 列的完整取證原文（該列已依
`ROW_MAX_BYTES`＝700 bytes 上限瘦身成索引，本檔是**唯一還能重驗**該筆結案是否為真的地方，
資格同既有同類治理文件如 `CrossPlatform_R99_Ledger_Closure.md`）。逐字保全，未刪減任何
查證內容，僅搬遷位置。

## DEF-200-185

- **發現情境**：外部阻塞軌複查（repo 轉 Public 後 GitHub Actions 帳務阻塞解除，拆自
  `DEF-101-755` 條件 (b)，原文見 `AutoSDD_Defect_Log_archive_67.md`）
- **嚴重度**：P2（同 `DEF-101-755`）
- **分流去向**：`tools/tests/test_dev_start.py::TestGetPythonGeMinPowerShell`
- **狀態**：fixed（本輪自 `AutoSDD_External_Blocked_Log.md` 移除，見該檔異動）：
  `DEF-101-755` 條件 (a)(b) 皆達成，母缺陷全結

### 現象與證據（逐字保全原文）

條件 (b)：一次 Windows CI（`windows-compat-ci.yml` 的 `windows-smoke` job）實跑並附
「`TestGetPythonGeMinPowerShell` 不再出現在 skip 明細」的取證。**本輪機械複驗達成**：
真實 push 觸發的 run `33041308203`（2026-08-27T05:03:41Z，job `98415310692`，30 steps
實跑非帳務阻塞的空轉）印出的 pytest skip 明細（`ℹ️ 本次 skip 明細（共 42 支...)`，
`tools/tests@win32` census）逐一列舉 42 支 skip，全文檢索 `GetPythonGeMin` 於整份 job
log 0 命中——`TestGetPythonGeMinPowerShell` 不在其中，代表其
`@unittest.skipUnless(_ps_any_engine(), ...)` 守門在該 Windows runner 上如預期判為
False（pwsh 存在），未被 skip。
