# Sprint Round 紀錄 SOP（W 期間骨架先行）

**對應**：[ADR-SD08-001-claude-md-budget.md](../04_planning/ADR/ADR-SD08-001-claude-md-budget.md) v1.1 §9
**適用**：SD_10 及之後所有 Sprint
**建立**：2026-05-26（SD_09 W3 R22 結構性收尾）
**維護者**：每 Sprint W0 第一步由 dev / Tech Lead 執行

---

## 1. 核心原則

**Sprint W 期間的 Round / audit 累積敘事一律直接寫入 `docs/05_development/sprint_history.md §1.N`，不寫入 CLAUDE.md。**

CLAUDE.md 該 sprint H3 段永遠保持「摘要 + 連結」≤ 15 行（contract test 強制）。

---

## 2. SD_10 Sprint 啟動流程（W0 第一步）

### 2.1 建立 sprint_history.md §1.N 骨架（一次性 CLI）

```powershell
# Sprint 編號為 10，主軸為「示例主軸」
python tools/scaffold_sprint_section.py --sprint 10 --title "示例主軸"
```

CLI 會自動：
1. 在 `sprint_history.md` 主目錄末尾追加 `### 1.N SD_Improving_NN（<title>）— 🟡 W0 啟動 YYYY-MM-DD` H3 段
2. 預留 `#### 1.N.1 W0` ~ `#### 1.N.6 G0 啟動條件` 六個 H4 子段
3. 預留 `#### 1.N.3 W3 zero-trust audit Round 累積區` 子段（仿 SD_09 §1.7.3）
4. 更新 `sprint_history.md` 頂部 `滾動窗口 N=2` 行（CLAUDE.md 切換為「最近 2 sprint」）

### 2.2 CLAUDE.md sprint H3 摘要建立（≤ 15 行）

於 CLAUDE.md `## 📜 Phase 0~6 微核心化重構歷程` H2 段末，新增 H3：

```markdown
### SD_Improving_NN（<title>）— 🟡 W0 啟動 YYYY-MM-DD

**主軸**：<1-2 句>。詳見 [SD_Improving_NN.md](docs/04_planning/SD_Improving_NN.md) v1.0 + [sprint_history.md §1.N](docs/05_development/sprint_history.md#1n-sd_improving_NN<title-anchor>)。

**最新狀態（YYYY-MM-DD）**：<最新 Round / 觀察期狀態 1-2 句>。pytest **<N> passed**；觀察期 #1=X/Y、#2=X/Y、#3=X/Y。
```

**強制規範**（contract test 守護）：
- ≤ 15 行（含空行）
- 單行 ≤ 800 字元
- 必含 `sprint_history.md` link（test_claude_md_sprint_anchor.py 雙向驗證）

### 2.3 滾出最舊 sprint（N=2 維持）

當 SD_10 啟動 → CLAUDE.md 應保留 **SD_09 + SD_10**，移除 SD_08：
- SD_08 H3 段已於 SD_09 W6 滾出（依 v1.0 §3.1 模式 B）
- SD_09 H3 段依「摘要 + 連結」格式保留（內容指向 sprint_history.md §1.7）

---

## 3. W 期間 Round / audit 紀錄寫法

### 3.1 ✅ 正確做法（W 期間骨架先行）

進行中 sprint（如 SD_10 W3 zero-trust audit Round 5）：

```markdown
# 在 sprint_history.md §1.N.3 W3 zero-trust audit Round 累積區
**W3 Round 5 zero-trust audit（YYYY-MM-DD，nightly 第 N 跑）**：派 PM+Architect/SA/SD/QA 全能 audit ...
```

**只更新 CLAUDE.md 該 sprint H3「最新狀態」一行**，例：

```markdown
**最新狀態（YYYY-MM-DD）**：W3 R5 zero-trust audit PASS（0 P0），pytest 2,615 passed；詳見 [sprint_history.md §1.N.3](...)
```

### 3.2 ❌ 錯誤做法（W 期間累積至 CLAUDE.md → 反模式）

```markdown
# 在 CLAUDE.md sprint H3 段內
**最新狀態（R5，YYYY-MM-DD）**：...（多輪 audit 接續寫成單行 2,000+ 字元）
**W3 Round 6（YYYY-MM-DD）**：...
**W3 Round 7（YYYY-MM-DD）**：...
```

**為何錯**：違反 §9.1 雙模式並行決議；觸發 5 層抗膨脹保險（≤ 400 行 / H3 ≤ 15 行 / 單行 ≤ 800）；歷史案例：SD_09 W3 R11~R18 在 CLAUDE.md line 198 累積成 2,397 字元怪物段。

---

## 4. G6 末 N=2 滾動下沉檢核

每 Sprint G6 通過時，W6 收尾任務（依 sprint_history.md §3.1 模式 B）：

- [ ] 確認最舊 sprint 的 CLAUDE.md H3 段（已是「摘要 + 連結」格式）
- [ ] 替換為一行 link，例：`### SD_Improving_XX 詳見 [sprint_history.md §1.X](...)`（H3 段壓縮至 2-3 行）
- [ ] 更新 sprint_history.md §2 議題索引表 reverse-link
- [ ] 跑 `python tools/snapshot_sync.py` 確認 Snapshot 區段同步
- [ ] 跑 `pytest tests/contract/test_claude_md_*.py` 驗證 5 層保險全綠

---

## 5. 相關檔案

- [ADR-SD08-001](../04_planning/ADR/ADR-SD08-001-claude-md-budget.md) v1.1 §9 — 結構性決議
- [sprint_history.md §3.1 + §3.5](sprint_history.md) — 維護指引雙模式
- [tools/scaffold_sprint_section.py](../../tools/scaffold_sprint_section.py) — W0 骨架自動生成 CLI
- [tools/snapshot_sync.py](../../tools/snapshot_sync.py) `--check` — sprint H3 vs §1.N 對齊驗證
- [tests/contract/test_claude_md_sprint_anchor.py](../../tests/contract/test_claude_md_sprint_anchor.py) — 雙向 link 一致性
