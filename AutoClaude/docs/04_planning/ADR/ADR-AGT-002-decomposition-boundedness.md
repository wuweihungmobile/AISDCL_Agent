# ADR-AGT-002 — 自主任務拆解的有界性：GoalDecomposer

| 項目 | 內容 |
|------|------|
| 編號 | ADR-AGT-002 |
| 狀態 | **DRAFT / PROPOSED（待 SCG-2 🔴 確認）** |
| 落地狀態 | **PLANNED**（Phase 3 F-A1；尚未實作，依序於 F-A2 之後） |
| 提出者 | sd-architect（Improving_012 Phase 3） |
| 提出日期 | 2026-06-13 |
| 對應計畫 | [AutoClaude_Improving_012.md](../AutoClaude_Improving_012.md) §1 F-A1 / §4 風險（SCG-0 已凍結） |
| 相依 ADR | ADR-AGT-001（工具可用性，拆解步驟需工具）/ 姊妹框架 R-9.23（意圖分解有界拆解） |

> ⚠️ **草案**：本輪僅供審查，未凍結、未實作。

## 1. 背景

A 能力「任務拆解」缺口：無「高階 goal → 完整步驟 DAG」之一次性自主拆解。讓 AI 生成步驟為**高風險**（無限步驟 / 自我放大，凍結計畫 §4）。需在引入自主拆解的同時，以機械手段保證有界與人工棘輪。

## 2. 決策

1. **GoalDecomposer**（`execution/goal_decomposer.py`，strategy tier ≤300）：呼叫 `IBrain.decide_decomposition` 一次取得候選 DAG，**本地驗證**後產出 Playbook 草稿。
2. **三道機械有界閘**（任一不過即拒絕、**不重試、不截斷**）：
   - 步驟數 ≤ `MAX_DECOMPOSITION_STEPS`（**硬上限 24**，config 可下調不可上調）；
   - DAG 無環（拓撲排序）；
   - 每節點具非空可執行 prompt。
3. **不自我放大**：每 run 拆解僅 1 次，拆解結果不可再觸發拆解（非遞迴）。
4. **🔴 人工 signoff 硬閘**：拆解草稿須人工 signoff 後才交既有 PlaybookRunner 執行；signoff 前零步驟執行；signoff 記錄（人/日期/goal hash）入審計。
5. **capability 守門**：`IBrain.decide_decomposition` 受 `BrainCapabilities.supports_decomposition` 守門；不支援之 brain → 拒絕拆解（不靜默降級）。
6. **Token 有界**：拆解 1 次 Brain 呼叫；驗證走本地拓撲排序（不呼叫 Brain，遵守「code 能答就 code 答」）。

## 3. 後果

- **正面**：自主拆解失控風險以機械上限 + 無環 + 人工棘輪三重緩解（對齊 R-9.23 / Rule 8）；產出沿用既有 Playbook schema，不新增執行路徑。
- **負面/成本**：新增 1 execution 元件 + 1 Brain 方法 + capability flag；MinimaxBrain 須實作 decomposition prompt。
- **與 F-A2 順序**：F-A2（工具）先行，因拆解出的步驟可能需工具可用。

## 4. 替代方案

| 方案 | 否決理由 |
|------|---------|
| 拆解超限即截斷至 24 步 | 截斷可能破壞 DAG 完整性、產出不可執行草稿；拒絕 + 重新 goal 更安全 |
| 無人工 signoff、自動執行 | 違反 Rule 8 人工棘輪與 §4 高風險緩解 |
| 遞迴拆解子步驟 | 自我放大風險；違反有界性 |
| 拆解結果直接執行不產草稿 | 無法人工審閱 DAG，signoff 無對象 |

## 5. SCG-2 🔴 確認（pending）

- [ ] 三道機械有界閘（≤24 + 無環 + 非空 prompt）接受
- [ ] 🔴 signoff 硬閘 + 不遞迴 接受
- [ ] capability 守門（不支援即拒絕）接受
- [ ] F-A2 先於 F-A1 之順序接受

**確認人**: ____（待 koalawu 🔴）　**日期**: ____　**方式**: ____
