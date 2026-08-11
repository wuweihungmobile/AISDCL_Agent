# FRAMEWORK_STATUS — AISDLC-SDD 框架版本/計數唯一真相源（SSOT）

> **🔴 自動生成，勿手動編輯。** 由 `scripts/framework_status_snapshot.py --write` 產生，
> ci-gate `--check` 機械守新鮮（stale 即 CI 紅）。改動框架資產（agent/規則/模板/skills…）後重生即可。
> CLAUDE.md 等文件一律 **version-agnostic** 並指向本檔，不重複數字——版本累積亦不再多檔漂移。

- **凍結基線（ci-gate FROZEN_BASELINE，恆測防回歸）**：`AISDLC_SDD_v0.01`
- **最新演化版（ci-gate LATEST，語意由 `scripts/sdd_version.py` SSOT 定案：git tracked＋錨定 fullmatch＋數值排序取最高；可修改/承載演化）**：`AISDLC_SDD_v0.30`
- 各版目錄結構同構。**凍結基線與中間歷史版一律不可原地改；LATEST 可原地改（＝日常演化路徑）**。Copy-on-Evolve（`scripts/copy_on_evolve.sh`）只在需要保留可回歸對照快照時開新版（發布／破壞性重構／需逐版比對），不是每次改動都要開新版。邊界見 `CLAUDE.md`〈版本狀態〉。

| 指標 | 凍結基線 `AISDLC_SDD_v0.01` | 最新演化版 `AISDLC_SDD_v0.30` |
|------|------|------|
| Agents 總數 | 25 | 28 |
| — core / specialized | 7 / 18 | 7 / 21 |
| — 其中 runtime（specialized/sdd-*） | 4 | 7 |
| Scenarios | 10 | 10 |
| Workflows（workflow/README.md 宣稱） | 23 | 23 |
| docs_template/sdd 模板（md + yaml） | 59（56 md + 3 yaml） | 59（56 md + 3 yaml） |
| .claude/skills | 42 | 42 |
| governance R-*.yaml | 38 | 39 |

> 數字來源：agents/scenarios/skills/templates/governance＝對應目錄磁碟實掃；
> workflows＝workflow/README.md 宣稱（curated 數＝1 Gate+8 core+13 scenario+1 ADR，非檔數）。
