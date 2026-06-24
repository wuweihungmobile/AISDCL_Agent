# Phase 2 規劃：CLAUDE.md Rule 9 裁剪（FF-2 收尾）

**狀態**：規劃中（尚未動 CLAUDE.md）｜**分支**：`feat-claude-md-trim-phase2`｜**日期**：2026-06-02
**前置**：Phase 1 已完成（22 條 Rule 9.x 全抽進 `governance/rules/R-*.yaml`，`d3b819c`）

---

## 1. 目標

把 CLAUDE.md `## 🔴 Rule 9` 從 **≈18.1 頁 eager-load** 裁剪為 **≤1 頁憲法摘要 + registry 指標**，
真正實現「每 session 必載指令」的 token 節省，且**不**削弱守門強制力與 Claude 的狀態感知。

## 2. 為什麼現在還不能直接裁（關鍵風險）

調查確認：**`rule_loader` 完全沒有接進 `.claude/hooks/`**（grep 0 命中）。
漸進式揭露機制存在，但 session 生命週期從未呼叫 `load_for_state()`。
⇒ 若現在直接裁掉 CLAUDE.md 的 Rule 9 細節，Claude 將**失去規則可見性而無自動替代**。
**必須先把 lazy-surface 路徑接上，才能安全裁剪。**

## 3. 三層安全網（裁剪為何安全）

| 層 | 機制 | 受 Phase 2 影響？ |
|----|------|------------------|
| L1 Runtime 強制 | `.claude/settings.json` + hooks 以 `permissionDecision: deny` 攔截（FSM 阻塞態、docs/01~03 寫保護、token 95%）。**不讀 CLAUDE.md** | ❌ 不受影響（裁剪不削弱強制） |
| L2 Lazy 逐態揭露（**新增，前置**） | `session_start.py` 呼叫 `rule_loader.load_for_state(current_state)`，把當前狀態命中的 R-*.yaml 注入 additionalContext | ✅ 新增 → 取代 eager-load |
| L3 憲法摘要（保留於 CLAUDE.md） | ≤1 頁「絕對禁令」bullet（最關鍵 ~12 條），即使零 hook 也永遠可見 | ✅ 保留精煉版 |

## 4. 分步序列（每步獨立 gate + 可回溯）

### 2a — 接線：rule_loader → session_start（純加法，低風險）
- 在 `session_start.py` `_build_context()` 的 warnings 後，新增區塊：
  ```python
  try:
      from tools.fsm_runtime import rule_loader
      rules = rule_loader.load_for_state(rt.state.current)
      if rules:
          lines.append("")
          lines.append(f"[SDD-RULES] 當前狀態 {rt.state.current} 命中 {len(rules)} 條治理規則：")
          for r in rules:
              lines.append(f"  - [{r.id}] {r.title}（{r.severity}）")
          lines.append("  細節見 governance/rules/；完整地圖 governance/RULES_INDEX.md")
  except Exception:
      pass  # never block session start
  ```
- **驗收**：新增 `test_session_start_injects_rules`（mock state → 斷言 additionalContext 含 R-9.x）；pytest 綠。
- **Blast radius**：僅 session_start.py + 1 測試。**Rollback**：還原該區塊。

### 2b — FF-5：CLAUDE.md §9 頁數守門（advisory→strict）
- arch_fitness 新增 FF-5：量測 CLAUDE.md `## 🔴 Rule 9` 區塊頁數；> 1 頁 → WARN（裁剪前），裁剪後轉 INFO。
- 兼測「憲法摘要仍涵蓋 N 條絕對禁令」「每條摘要可對應到一個 R-9.x」，防裁過頭漏掉 guardrail。
- **驗收**：FF-5 落地，裁剪前顯示 WARN（≈18 頁）。

### 2c — 裁剪 CLAUDE.md §9（高風險，最後做，附 before/after diff 預覽）
- 用 §5 的憲法摘要骨架取代 9.1~9.22 全部散文。
- Rules 1~8 完全不動。
- **驗收**：FF-5 INFO（≤1 頁）、FF-2 維持 INFO、`test_rules_index_sync.test_all_claude_rule9_sections_extracted` 改為比對「摘要引用的 R-9.x ⊆ registry」；pytest 綠；人工確認憲法摘要無遺漏關鍵禁令。
- **Rollback**：`git revert` 該 commit（R-*.yaml 為權威副本，零資料遺失）。

## 5. 裁剪後 §9 骨架（憲法摘要，提案）

```markdown
## 🔴 Rule 9：自動化閉環防護（憲法摘要）

完整規則已結構化於 `governance/rules/R-*.yaml`，由 `rule_loader.load_for_state()`
依當前 FSM 狀態 lazy-load；session_start hook 會注入命中規則。完整地圖見
`governance/RULES_INDEX.md`。以下為**永遠生效的絕對禁令**（違反即停機）：

1. 繞過 FSMRuntime 直接讀寫 FSM-STATE-*.yaml（R-9.6）
2. 停用 / 刪除 .claude Phase D·E hooks（R-9.6）
3. IMPLEMENTATION 期間 Write/Edit docs/01~03 規格文件（R-9.6）
4. SCG/PR/RTM retry 超上限仍重試、不進 ESCALATION（R-9.1）
5. Token ≥95% 仍工作、不產 Context Snapshot（R-9.2）
6. 進入 ESCALATION / ESCALATION_FINAL 後自動恢復（R-9.5 / R-9.14）
7. 改 _HAPPY_PATH 不同步 SDD_FSM.tla（R-9.18.1）
8. 把觀測態放入 Terminals 集合（R-9.18.4）
9. 對 structural ESCALATION 強行 auto-recovery（R-9.14.3）
10. 讓 proposed / external 規則阻塞 SCG（R-9.11.3）
11. 自動退役 active 規則而不經 set_maturity(reviewed_by=)（R-9.20.5）
12. 自動套用 spec patch 改 FRD/AC 而不經 HUMAN_PENDING（R-9.22.5）

> 各 Phase 的詳細子規則、ACT 對照、相關文件、驗收憑證 — 一律見對應 R-*.yaml。
```

## 6. Before / After 樣本（單一規則示意）

**Before**（CLAUDE.md 現況，節錄 9.1，約 12 行表格 + 散文）：
```
### 9.1 FSM Retry Budget（重試上限）
| 情境 | 最大重試次數 | 超限後行動 |
| SCG 驗證失敗 | 3 次 | 進入 ESCALATION |
| PR Review 失敗 | 5 次 | 進入 ESCALATION |
| ... 共 ~12 行 ...
```
**After**（CLAUDE.md 僅留憲法摘要第 4 條）：
```
4. SCG/PR/RTM retry 超上限仍重試、不進 ESCALATION（R-9.1）
```
細節（3/5/2 次、同 pattern×3→SPEC_AUDIT）→ 已在 `R-9.1-fsm-retry-budget.yaml`，
由 session_start 在 SCG_VALIDATION/PR_REVIEW/RTM_VERIFY 狀態時注入。

## 7. 預估效益
- CLAUDE.md Rule 9 區塊：≈18 頁 → ≤1 頁（每 session 省下對應 token；呼應 R-9.2 自身的預算精神）。
- 規則細節改為「按當前狀態」精準注入，雜訊更低、相關性更高。

## 8. 風險登記
| 風險 | 等級 | 緩解 |
|------|------|------|
| 裁剪後 Claude 失去規則可見性 | 高 | 2a 先接 lazy-surface；L3 憲法摘要永久內嵌 |
| 憲法摘要漏掉關鍵禁令 | 中 | FF-5 斷言摘要條目對應 R-9.x；人工 review |
| 下游採用者無 root CLAUDE.md | 低 | FF-2/FF-5 對缺檔已 graceful skip |
| hook 失敗時規則不可見 | 低 | L1 強制不依賴可見性；L3 摘要恆在 |

## 9. 建議執行順序
2a（接線）→ 2b（FF-5 守門）→ **🔴 人工核可 before/after diff** → 2c（裁剪）。
每步 pytest + arch_fitness 維持綠；2c 前必出完整 diff 供核可。
