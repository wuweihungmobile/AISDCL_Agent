# Improving012 Phase 2 複審 + Phase 3 規格草擬後 Next Action

**日期**: 2026-06-13 | **狀態**: Phase 0/1/2 ✅（zero-trust 複審 PASS）；Phase 3 規格草案就緒（**待 SCG-1/SCG-2 🔴**，未實作）
**權威計畫**: [AutoClaude_Improving_012.md](../04_planning/AutoClaude_Improving_012.md)（SCG-0 凍結）

## 本輪結果摘要

### 1. Phase 0/1/2 zero-trust 複審（三方並行 Architect·SD / QA / SA·RTM·nightly）
- **結論**：OVERALL PASS，**P0=0 / P1=0**，僅 **5 條 P2（皆文件層）**。Phase 1/2 架構與功能正確、**修復方向正確**、nightly 程式正確。
- **親跑複核（主 agent，紀律 #17）**：full pytest **3,020 passed / 122 skipped**（92.71s，與聲稱基線一致）；importlinter 8 kept；LOC violations=0；snapshot OK；驗證鏡子測試 137 passed；nightly forensic log（run_id=040216）5 stage 全綠可引行號。
- **攔截點實證**：`_impl.py:297`（escalate 唯一 call site）/ `:368`（max_retries）親查確認。

### 2. P2 文件修復（已全修，純文件、零程式碼變更）
| 修復 | 內容 |
|------|------|
| SRD/ADR 行號漂移 ×6 | `_impl.py:278→297`、`:338→368`、ErrorBudget `:299-324→327-329`、`_loop_state.py:53-61→77-78`（alert_ladder resume）、`pg_state_repository.py:463→482`（load）、ADR-AGT-004 §2.1 攔截點 `:278→297` |
| 撤銷誤報 | Arch P2-1「byte-level 用詞」實已限定「控制流」（SRD:71/config.py:126），精確無需改；Arch P2-2「GoalProgressLedger 是 port」文件未如此宣稱 → 皆 agent 行號記憶誤差，撤銷 |
- **QA 複審修復**：純行號訂正未觸碰程式碼，pytest 3,020/122 不受影響、無破壞收斂閉環、原設計功能完整 → PASS。

### 3. Phase 3 規格草案（**DRAFT，待 🔴**）
- SCG-1：[SRD_AGT_Phase3_Autonomy.md](../02_architecture/SRD_AGT_Phase3_Autonomy.md)（F-A2 ToolInvocationPort + allowlist / F-A1 GoalDecomposer）
- SCG-2：[ADR-AGT-001](../04_planning/ADR/ADR-AGT-001-tool-invocation-security-gate.md)（工具安全閘）/ [ADR-AGT-002](../04_planning/ADR/ADR-AGT-002-decomposition-boundedness.md)（拆解有界性）
- 重要精化：Port 12→**13**（僅新增 `IToolInvocation`；`PreferenceStorePort` 已於 Phase 1 交付，凍結計畫 §2「10→12」描述須以實況校正）；`IBrain` 新增 `decide_decomposition`（capability 守門）；send_message 經 EventBus 委派既有 notification plugin。

## 進度更新（2026-06-13 開發輪）

- **🔴 SCG-1 + SCG-2 已簽署**（koalawu 2026-06-13，AskUserQuestion 互動核准後回填文件）：SRD_AGT_Phase3 v1.0 凍結、ADR-AGT-001/002 轉 ACCEPTED。
- **F-A2 ✅ 已交付**（tag v2026.06.13-05，commit cbb846d）：`IToolInvocation` port（ports 12→13）+ `ToolInvocationAdapter`（預設 deny + allowlist domain/子域比對 + 全程審計 log via IObservabilityPort + send_message 委派 `utils.notifier.notify`）+ `ToolInvocationConfig`（flag off）。閘門：full pytest **3,035/122**（+15 零回歸）、新模組 coverage **100%**、importlinter 8 kept、LOC=0、新檔 ruff 零違規。
- **實作精化留證**（SRD §0）：send_message 改委派 notifier（非裸 EventBus，因 EventBus 為 phase-based 非通用匯流排）；F-A2 adapter 尚未 wiring 接線（無消費者，避免 dead code），待 F-A1 GoalDecomposer 注入消費。

## Next Action（依凍結計畫順序）

1. **F-A1 GoalDecomposer**（Phase 3 收尾）：`IBrain.decide_decomposition`（+ capability flag 守門）→ `execution/goal_decomposer.py`（≤24 步硬上限 + DAG 無環 + 非空 prompt）→ 產 Playbook 草稿 → **🔴 人工 signoff** 後才交 PlaybookRunner；同時把 F-A2 adapter 經 wiring 注入。驗收：拆解超限/含環被拒、signoff 前零執行、不支援 decomposition 的 brain 被拒。
2. **SCG-4/5（F-A1 PR）**：pytest 全綠 + lint-imports + LOC + coverage ≥90% + RTM US-AGT-001~002 → TC。
3. **SCG-6（Phase 2 殘留）**：F-B1 `alert_ladder.enabled` nightly **連 7 天綠**後轉預設 on（觀察期；本輪未到期）。

## Audit / 觀察 backlog（沿用、未阻斷）
| 項目 | 說明 |
|------|------|
| ruff 鎖版 + 全量清理 | ~1,330 errors；ci.yml 不跑 ruff；本輪僅守新增檔零違規 |
| 新模組 mutation 強度 | alert_ladder/correction_verifier 僅行覆蓋 100%，待 Phase 3 搭 nightly mutation 擴範圍 |
| PG pg_real e2e | counters/preference adapter 有 mock 防線，真 PG e2e 待 `SD07_REAL_PG_E2E_ENABLED` |
| perf 載具偽陽性 | agent PowerShell 載具 CPU 膨脹（穩定模式）；建議 perf stage BLOCK 時自動 Bash 對照重測 |

## AISDLC_SDD_v0.01 開發流程問題記錄（下輪改善，依使用者指示）

| # | 問題 | 證據（本輪實證） | 建議改善 |
|---|------|----------------|---------|
| 8 | **SRD/ADR 引用之源碼 `檔案:行號` 於 LANDED 後隨源碼演進漂移，無機械校驗** | 本輪三方 audit 揪出 6 處行號漂移（`_impl.py:278` 實為 :297 等）；功能/測試全正確，純文件行號失準，違背 SRD §0「附 檔案:行號 且已驗證觸發」承諾與 nightly 紀律 #15 | 二擇一機械化：(a) SCG-4 交付時對文件內所有 `xxx.py:NN` 引用做靜態校驗（grep 該行內容是否仍含宣稱符號，漂移即 fail）；(b) **SRD/ADR 一律引用穩定的函式/類別名錨點，避免裸行號**（本輪 Phase 3 草案已採此法，延伸流程改善 #6/#7 的機械校驗精神） |

---
**產出**: 主 agent（Claude Code）依 AISDLC_SDD SCG 流程執行；audit 取證見三方 agent 報告（行號/數字均經主 agent 親跑複核）。
