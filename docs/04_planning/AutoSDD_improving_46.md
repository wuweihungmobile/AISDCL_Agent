# AutoSDD improving_46 — B 軌 Dogfooding：`.claude` hooks/skills 第四輪四鏡全面複審 + 3 P3 就地清償

> **輪次**：improving_46（接續 improving_45＝DEF-CLDREV-001~016 三輪；LATEST 框架版＝`AISDLC_SDD_v0.19`）
> **柱別**：**B 軌（手腳框架自我迭代 / Dogfooding）**——標的＝`AISDLC_SDD_v0.19/.claude`（5 hooks + 42 skills + settings.json）+ 根 router settings + shared infra `AISDLC_SDD/scripts/`
> **下一份**：improving_47（候選見文末）
> **日期**：2026-06-23　**掌舵者**：Dr. Alan（L10 自治系統與微核心架構總監）

---

## 0. 本輪緣起與目標

使用者第四次請求「全面確認 `AISDLC_SDD_v0.xx/.claude` 所有 hooks 與 skills 是否符合 SDD 與整體系統架構？完整徹底驗證，不符則提架構調整並派 Architect/SA/SD/QA 全能專家檢視與修復」。前三輪（DEF-CLDREV-001~016，improving_45 三個 追記 區塊）已全閉。本輪＝**真正全新第四輪 zero-trust 複審**，禁援引前輪結論當事實。

**成功判準（Rule 4）**：(1) 四鏡獨立 zero-trust 全面比對「文件 vs 系統現況」；(2) 真缺陷全入帳完成分流、無漏記/虛報；(3) 零退化（ci-gate EXIT=0、v0.19 passed ≥ floor 1629、0 failed）；(4) 四鏡複核全 PASS。

---

## 1. 階段一：現況重偵察（Zero-Trust，實測）

| 項目 | 實測結果 |
|------|---------|
| (a) 基線 ci-gate | `bash scripts/ci-gate.sh` **EXIT=0**；逐軌 **v0.01:1478 / v0.19:1629 / scripts/tests:121**（＝上輪結案值，**floor 成立**） |
| (b) hooks 親讀 | 5 hooks 全親讀：session_start / context_ledger_pre / context_ledger_post / closure_evidence_verify / post_commit_drift — 皆 never-raise/fail-soft、版本中性 `parents[2]` 自定位、Windows thread-guard timeout |
| (c) settings 親讀 | 根 router settings.json + v0.19 settings.json：PreToolUse/PostToolUse matcher 皆 `Write\|Edit\|Read\|Bash\|NotebookEdit`（**缺 Task**——見 DEF-CLDREV-017） |
| (d) skills 計數 | 磁碟 v0.19/.claude/skills = 42 SKILL.md，與 FRAMEWORK_STATUS.md SSOT、父層鏡像（59 檔）三方對齊 |

**硬閘**：基線無 failed、達上輪 passed 1629 → 通過，准進階段二。

---

## 2. 階段二：增量設計

### <Architecture_Design_Review>
1. **架構純潔性**：本輪僅修 2 處 settings.json matcher（wiring 設定）+ 1 hook docstring（純註解同步）+ 文件數字/調用名訂正 + 1 新測試。**無新 Python 業務邏輯、無 God-object、Thin Facade 不受影響**。
2. **持久化相容**：不涉 PlaybookCheckpoint / DAL。
3. **安全防護網**：未動 CONDITIONAL 三層防禦；matcher 補 Task 僅擴大 PreToolUse hook 觸發面（FSM guardrail + advisory 注入），不弱化任何消毒。
4. **對外 I/O 安全**：無新增 `ToolInvocationPort` 外呼路徑。
5. **Copy-on-Evolve 邊界**：依掌舵者既定政策「就地修 v0.19（LATEST，可演化版），非遞版」；凍結基線 v0.01 不動（v0.01~v0.18 matcher 維持原樣＝歷史/凍結，僅 LATEST + 根 router 修）。

### 本輪 W 項（3 條 P3，四鏡交叉揪出）
- **W-46-1（DEF-CLDREV-017，Architect 鏡，掌舵者裁定啟用）**：PreToolUse matcher 補 `Task`（根 + v0.19）+ docstring 同步 + 機械回歸鎖。
- **W-46-2（DEF-CLDREV-018，SD 鏡）**：`SKILL_DEVELOPMENT_PLAN.md:83` `/doc-api`→`/documentation-api`。
- **W-46-3（DEF-CLDREV-019，QA 鏡）**：improving_45:90 + Defect_Log:502 SLV 測試數 `39`→`35`（DEF-016 漏改補齊）。

---

## 3. 階段三：實作與雙重驗證

- **DEF-CLDREV-017**：根 `.claude/settings.json:18` + `v0.19/.claude/settings.json:23` PreToolUse matcher `→ Write|Edit|Read|Bash|NotebookEdit|Task`（PostToolUse 維持不動，ACT-020 注入僅 PreToolUse）；`v0.19/context_ledger_pre.py:6` docstring wiring 範例同步補 Task；新增 `scripts/tests/test_pretooluse_matcher_task.py`（2 測試守根 + 最新版 matcher 必含 Task）。突變實證（暫退 Task → `test_latest_version_...` 轉紅）非空殼。
- **DEF-CLDREV-018**：PLAN:83 正名；父層 SSOT 鏡像 `sync_exposed_skills --write` 重生 59 檔；grep `/doc-api` 殘留 0。
- **DEF-CLDREV-019**：improving_45:90、Defect_Log:502 兩處 `39`→`35`（後者附訂正註記）。

---

## 4. 階段四：CI 平價收斂（零退化矩陣 — 最終態實測 2026-06-23）

| 檢查 | 命令 | 通過條件 | 結果 |
|------|------|---------|------|
| AISDLC 全套 | `bash scripts/ci-gate.sh` | EXIT=0、v0.19 ≥ floor 1629、0 failed | ✅ **EXIT=0**；v0.01:1478 / v0.19:**1629**（==floor、0 failed） |
| scripts/tests 全套 | `pytest scripts/tests/ -q` | 通過 | ✅ **123 passed**（floor 121 + 2 回歸鎖；突變實證非空殼） |
| Skill 版本戳 lint | `skill_header_sync.py --check` | 全對齊 LATEST | ✅ OK（全對齊 v0.19） |
| 曝光 skills 鏡像 lint | `sync_exposed_skills.py --check` | 父層==LATEST | ✅ 59 檔一致（B 修復已重生） |
| Router hook 覆蓋 lint | （ci-gate 內） | event 全可達 | ✅ PreToolUse/PostToolUse/SessionStart 全可達 |
| 框架版本/計數 SSOT | `framework_status_snapshot.py --check` | fresh | ✅ fresh（skills 仍 42） |
| 五軌 TLC | （僅 FSM/*.tla 變更時） | — | **不觸發**（本輪 FSM/*.tla 零變更） |

---

## 5. RTM（需求→實作→驗證追溯）

| 需求 | 實作 | 驗證 | 狀態 |
|------|------|------|------|
| DEF-CLDREV-017 matcher 補 Task（啟用 ACT-020） | 根 + v0.19 matcher `\|Task` + docstring 同步 + 回歸鎖 | 2 新測試 passed + 突變紅 + ci-gate EXIT=0 | ✅ fixed@v0.19 |
| DEF-CLDREV-018 死調用名正名 | PLAN:83 `/documentation-api` + 鏡像重生 | grep 殘留 0 + skills-ssot 59 檔一致 | ✅ fixed@v0.19 |
| DEF-CLDREV-019 SLV 測試數訂正 | improving_45:90 + Defect_Log:502 `39→35` | test_slv_generator 實測 35 對齊 | ✅ fixed@v0.19 |
| 零退化 | — | ci-gate EXIT=0、v0.19:1629==floor、scripts:123、0 failed | ✅ |

---

## 6. 結案與下輪候選

- **B 軌結案條件達成**：本輪 3 新缺陷全入帳完成分流（皆就地 fixed@v0.19）；前輪 DEF-CLDREV-001~016 經四鏡逐筆親驗修復真實、無虛報；FSM decision_trace 不適用（本輪未跑 FSM session，純 wiring/文件修）。臨時審查塊 DEF-CLDREV-017~019 全閉、零 routed 殘留。
- **誠實揭露（Rule 12）**：DEF-CLDREV-017 的 matcher 補 Task 已單元驗證「hook 收到 Task payload 會注入」，但**此環境無法 E2E 驗證 Claude Code 是否確對 Task 工具傳遞 PreToolUse 事件與 `subagent_type` 欄位**；E2E 行為待真實 session 觀察確認。
- **improving_47 候選**：
  1. C 軌 SD_09 W1（待 06-26 G0 觀察期閘門）。
  2. B 軌既有 open：DEF-37-001 / DEF-42-001。
  3. DEF-CLDREV-017 E2E 觀察：真實 session 確認 Task 注入生效後，評估是否將 subagent 結果大小納入 PostToolUse ledger（budget 精度增強）。
  4. A 軌續偵察 adapter 保真度。
