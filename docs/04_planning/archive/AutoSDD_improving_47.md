# AutoSDD_improving_47 — SDD `.claude` hooks/skills 第五輪四鏡複審（B 軌 dogfooding）

> **軌道定位**：軌道① 整合迭代 **B 軌（手腳 AISLDC_SDD 自我迭代 / Dogfooding）**。本輪標的＝對最新框架版 **`AISDLC_SDD_v0.19/.claude/`（5 hooks + 42 skills + settings.json）** 做「內容是否符合 SDD 與整體系統架構」之 zero-trust 全面複審。下一份候選＝`AutoSDD_improving_48.md`。
> **觸發**：使用者再次請求「`AISDLC_SDD_v0.xx/.claude` 所有 hooks 與 skills 是否符合 SDD 與整體系統架構？完整徹底驗證並修復，派 Architect/SA/SD/QA 全能專家」。
> **與前四輪關係**：DEF-CLDREV-001~019 已全閉（improving_44/45/46）。本輪為第五輪，揪出 DEF-CLDREV-020~023 並全 fixed@v0.19。

---

## 1. 階段一：現況重偵察（Zero-Trust Re-Audit）

| 項目 | 命令 | 實測結果 |
|------|------|---------|
| AISDLC_SDD ci-gate 基線 | `bash scripts/ci-gate.sh` | **exit 0**；逐軌 v0.01:1478 / v0.19:1629 / scripts/tests:123 |
| .claude 結構 | `find .claude -type f` | 5 hooks（session_start/context_ledger_pre/context_ledger_post/post_commit_drift/closure_evidence_verify）+ settings.json + 42 skills（含 spec-logical-validator 14 SLV-*.yaml） |
| 最新版確認 | `ls -d AISDLC_SDD_v0.*` | LATEST = **v0.19**（演化版，非凍結基線 v0.01） |
| 根 router 機制 | 親讀 `sdd_hook_router.py` | 透過 subprocess 轉發到 `v{ver}/.claude/hooks/<script>`（`:154,:176`）；根層**無**獨立 hook 副本 → 修 v0.19 hook 一處即生效兩路徑 |
| 工作樹 | `git status --porcelain` | 乾淨（標的為 tracked 檔 → DEF-24-001 主樹派發判準） |

**硬閘**：基線 0 failed、≥ 上輪 passed → 通過，准進階段二。

## 2. 階段二：本輪增量設計（四鏡 zero-trust 複審 + 缺陷修復）

派 Architect / SA / SD / QA 四鏡主樹並行獨立複審（各鏡不同視角，最大化新缺陷發現、避免冗餘）：

- **Architect 鏡（架構面）**：FSM 三層治理閉環 / hooks 版本中性 / 根 router 三層子命令對應 / 三支柱 SCG 分類 / by-design 解耦 → **OVERALL PASS，0 新缺陷**。
- **SA 鏡（安全/輸入域）**：26 畸形輸入案例親測 → 揪 **DEF-CLDREV-020**（非字串 subagent_type crash）。
- **SD 鏡（內容一致性）**：42 skill 調用名/死鏈/SLV/版本戳 → 揪 **DEF-CLDREV-021/022/023**。
- **QA 鏡（驗證/誠實性）**：帳本抽查 6 筆 + 2 突變實證 + 數字 collect → **OVERALL PASS，帳本誠實、測試非空殼**。

### 本輪 W 項（≤3 項原則 → 實為 4 條 surgical 缺陷，全當場清償非延後）

| W | 缺陷 | 類型 | LOC/檔案影響 | .importlinter 影響 |
|---|------|------|-------------|-------------------|
| W1 | DEF-CLDREV-020 | hook 程式（輸入域防護） | `context_ledger_pre.py` ±5 行（type-guard）+ 測試 +2 | 無（hook 非受 contract 約束的 autoclaude 模組） |
| W2 | DEF-CLDREV-021 | skill 文件一致性 | `spec-logical-validator/SKILL.md` 3 處（表/CLI/filter） | 無 |
| W3 | DEF-CLDREV-022 | skill 版本戳 | `test-failure-analyzer/SKILL.md` footer +1 行 | 無 |
| W4 | DEF-CLDREV-023 | README 版本錨點 | `README.md:248` 1 處 | 無 |

> **B 軌紅線遵循**：v0.19＝LATEST 演化版（非凍結基線 v0.01），掌舵者既定政策「就地修 v0.19」（前四輪一致）；FSM/`*.tla` 零變更 → 不觸發五軌 TLC；🔴 人工確認閘門無涉。

## 3. <Architecture_Design_Review>（寫 hook 程式前自我驗證）

1. **架構純潔性**：DEF-CLDREV-020 修復僅在 `_build_subagent_notice()` 取值處加 `isinstance` 型別防護，無新增 God-object、無改變 hook 與 FSMRuntime 的單向依賴；Thin Facade 不受影響。
2. **持久化相容**：未觸 PlaybookCheckpoint / DAL；hook 為 CC 進程外腳本，無持久化欄位變更。
3. **安全防護網**：本修復**強化**輸入域防護（非字串 → graceful），與 CONDITIONAL 白名單正交；屬 DEF-CLDREV-012（非數字 SDD_MAX_CONTEXT）同類的「輸入域 graceful」家族，補齊一致性。
4. **對外 I/O 安全**：本輪未新增 `ToolInvocationPort` 外呼路徑；hook 不發網路 I/O。allowlist/SSRF 不涉。

## 4. 階段三：實作與雙重驗證

- W1：`context_ledger_pre.py` type-guard → 立即 `pytest test_context_ledger_pre_hook.py` = **14 passed**（原 12 +2）；受控突變（退回 `(_raw_agent or "").strip()`）→ `NonStringSubagentTypeTests` 2 紅 AttributeError、還原 2 passed＝**非空殼**。
- W2/W3/W4：純文件 surgical；改後 `sync_exposed_skills.py --write` 重生父層鏡像 59 檔。

## 5. 階段四：CI 平價收斂（零退化驗證矩陣）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | **exit 0** ✅ |
| 逐軌計數 | （ci-gate 末行） | ≥ floor、0 failed | v0.01:1478 / v0.19:**1631**（floor 1629+2）/ scripts:123 ✅ |
| Skill 版本戳 SSOT | `skill_header_sync.py --check` | 全對齊 v0.19 | OK ✅ |
| 曝光 skills SSOT | `sync_exposed_skills.py --check` | 父層==LATEST 59 檔 | OK ✅ |
| FRAMEWORK_STATUS 新鮮 | `framework_status_snapshot.py --check` | fresh（42 skill） | fresh ✅ |
| Router hook 覆蓋 | （ci-gate 內 lint） | 三 event 全可達 | ✅ |
| 五軌 TLC | — | 僅 FSM 變更時 | 本輪零 FSM/`*.tla` 變更 → 不觸發 |

> AutoClaude（A/C 軌）pytest 本輪**未涉**（標的純 AISDLC_SDD `.claude`），無需重跑；零退化以 AISDLC_SDD ci-gate exit 0 為據。

## 6. RTM（需求→修復→驗證 追溯）

| 需求 | 缺陷 | 修復構件 | 驗證證據 |
|------|------|---------|---------|
| hooks 符 SDD/架構、輸入域 graceful | DEF-CLDREV-020 | `context_ledger_pre.py` type-guard + `NonStringSubagentTypeTests` | 親測 exit=1→修後 graceful；突變 2 紅→還原綠；ci-gate 1631 |
| skill 文件內容一致 | DEF-CLDREV-021 | `spec-logical-validator/SKILL.md` 表/CLI/filter | 全 14 列 Scope 欄==yaml；ci-gate 綠 |
| skill 版本戳全覆蓋 | DEF-CLDREV-022 | `test-failure-analyzer/SKILL.md` footer | grep 42/42 有戳；skill_header `--check` OK |
| README 版本錨點不誤導 | DEF-CLDREV-023 | `README.md:248` | 章節標題明示引入版+沿用版 |

## 7. 結論

四鏡 OVERALL PASS（Architect/QA 零新缺陷、SA/SD 揪 4 條真缺陷全 fixed@v0.19）。**v0.19 的 `.claude` hooks/skills 符合 SDD 三支柱與微核心整體架構**：FSM 三層治理閉環完整、hooks 版本中性、根 router 一一對應、42 skill SCG 分類無錯置、無架構紅線違反。本輪屬「修一個缺陷（DEF-CLDREV-017 啟用 Task matcher）暴露其下游輸入域缺陷（DEF-CLDREV-020）」的正常連鎖收斂，非退化。零退化（ci-gate exit 0、1631≥floor 1629）。**無需結構性架構調整**——僅輸入域防護 + 文件一致性 surgical 清償。
