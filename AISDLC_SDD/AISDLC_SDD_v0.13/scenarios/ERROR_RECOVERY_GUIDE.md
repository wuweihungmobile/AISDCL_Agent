# 錯誤恢復機制指南（SDD 版）
# Error Recovery Guide — SDD Edition

**框架版本**: AISDLC-SDD v0.01
**基於**: AISDLC-SDD v0.01 ERROR_RECOVERY_GUIDE
**最後更新**: 2026-04-15
**文檔目的**: 定義 SDD 十大情境中常見錯誤場景（含 SCG 閘門失敗）的檢測與恢復機制

---

## 錯誤恢復原則

1. **及早檢測** — SCG 閘門是第一道防線，在錯誤擴散前發現
2. **快速隔離** — SCG 未通過時立即停止，不允許進入下一階段
3. **系統性恢復** — 依 SDD 規格補充缺失文件，重新通過閘門
4. **記錄與學習** — 記錄錯誤原因（ADR 形式），避免重複

---

## 錯誤分類體系

### 按嚴重程度

| 等級 | 名稱 | 影響 | 恢復時效 | SDD 對應 |
|-----|------|------|---------|---------|
| **P0** | 阻斷性 | 完全無法繼續 | 立即處理 | SCG 硬閘門失敗、關鍵規格缺失 |
| **P1** | 嚴重 | 嚴重影響進度 | 4 小時內 | SCG 軟閘門失敗、規格內容錯誤 |
| **P2** | 中等 | 需修正但可繼續 | 1 天內 | 規格格式錯誤、RTM 覆蓋不足 |
| **P3** | 輕微 | 影響品質但不阻斷 | 1 週內 | 文檔細節缺失、命名不一致 |

### 按錯誤類型

#### A. SDD 規格類錯誤（新增）
- **SG1**: SCG 閘門未通過（規格文件缺失或不完整）
- **SG2**: 規格凍結後擅自修改（需走 Change Management）
- **SG3**: 實作與規格不一致（SCG-4 PR Review 失敗）
- **SG4**: RTM 覆蓋率不足（SCG-5 失敗）
- **SG5**: Business Invariants 被破壞（Refactoring 場景）
- **SG6**: Contract 未凍結就開始實作（SCG-3 違規）

#### B. 文檔類錯誤
- **D1**: 關鍵文檔遺失（PRD/FRD/SRD/ADR/RTM）
- **D2**: 文檔內容錯誤或自相矛盾
- **D3**: 文檔版本混亂
- **D4**: 規格追蹤鏈斷裂（RTM → 需求 → 測試）

#### C. 需求類錯誤
- **R1**: 需求理解錯誤（Invariants 未提取）
- **R2**: 需求變更未走 SCG Change Management
- **R3**: 需求範圍蔓延（Scope Creep）

#### D. 設計類錯誤
- **S1**: 架構設計缺陷（C4 圖不準確）
- **S2**: API Contract 不一致（OpenAPI 規格錯誤）
- **S3**: ADR 缺失（技術決策未記錄）

#### E. 流程類錯誤
- **P1**: 跳過 SCG 閘門 🔴（嚴重違規）
- **P2**: 情境轉換前未確認 SCG 通過
- **P3**: 並行情境規格衝突

---

## SCG 閘門失敗恢復流程（SDD 核心）

### SCG-0 失敗（需求凍結失敗）

```
症狀: PRD 或 FRD 完整性不足，SCG-0 未通過

恢復步驟:
1. sa-analyst 執行 spec-compliance-check，列出缺失項目
2. pm-po + sa-analyst 補充缺失需求
3. 重新執行 sdd-gate 驗證 SCG-0
4. 🔴 人工確認後凍結

禁止: 在 SCG-0 未通過時繼續進行 SRD 設計
```

### SCG-1/SCG-2 失敗（設計/架構凍結失敗）

```
症狀: SRD 缺失 C4 圖、ADR 不完整

恢復步驟:
1. sd-architect 補充 C4 Model（使用 adr-generate）
2. 補充缺失的 ADR 文件
3. 重新執行 sdd-gate 驗證
4. 🔴 人工確認架構決策

禁止: 在 SCG-2 未通過時凍結 OpenAPI
```

### SCG-3 失敗（Contract 凍結失敗）

```
症狀: OpenAPI 3.1 規格不完整，或 Consumer Contract 未建立

恢復步驟:
1. sd-architect / integration-specialist 使用 contract-generate 補充
2. 確認所有端點已定義（含錯誤碼）
3. 重新執行 sdd-gate 驗證 SCG-3
4. 🔴 人工確認 Contract 凍結

禁止: Contract 未凍結就開始後端實作
```

### SCG-4 失敗（PR Review — 實作與規格不一致）

```
症狀: 實作行為與 API Contract / SRD 規格不符

恢復步驟:
1. 執行 spec-compliance-check 列出差異點
2. 判斷: 是實作錯誤 or 規格需更新?
   - 實作錯誤: 修正實作 → 重新 PR
   - 規格更新: 走 Change Management → 重新凍結 → 修正實作
3. 不允許「先合併、後補規格」

禁止: 跳過 SCG-4 直接合併
```

### SCG-5 失敗（RTM 覆蓋率不足）

```
症狀: RTM 顯示需求覆蓋率 < 100%

恢復步驟:
1. qa-lead 使用 rtm-generate 識別未覆蓋需求
2. 補充對應測試案例
3. 重新執行 sdd-gate 驗證 SCG-5

禁止: 覆蓋率不足時進行發布
```

### INV Gate 失敗（Refactoring — Invariants 被破壞）

```
症狀: 重構後 Invariant Test Contract 測試失敗

恢復步驟:
1. dev-senior 識別哪個 Invariant 被破壞（INV-XXX）
2. 回滾相關變更
3. 重新設計重構方案，確保 Invariants 保護
4. 🔴 sa-analyst 確認 Invariants 仍完整
```

---

## 通用錯誤檢測機制

### 自動檢測點

每個情境 SOP 的每個階段入口執行：
```yaml
階段入口檢查:
  - 前一階段必要文件完整性（spec-compliance-check）
  - SCG 閘門狀態（sdd-gate）
  - 規格版本一致性
  - RTM 追蹤鏈完整（rtm-generate 驗證）
```

### 人機確認點 🔴

SDD 強制確認點（不可跳過）：
- SCG 閘門通過確認
- Business Invariants 清單確認（Refactoring）
- API Contract 凍結確認（SCG-3）
- 規格文件凍結確認（SCG-0/1/2）

---

## 各情境常見錯誤快速參考

| 情境 | 高頻錯誤 | 預防措施 |
|------|---------|---------|
| Greenfield | SCG-0 PRD 不完整 | 使用 spec-compliance-check 提前驗證 |
| Brownfield | As-Is SRD 逆向不完整 | sa-analyst 逐步確認每個模組 |
| Refactoring | Invariants 未完整提取 | INV Gate 前 sa-analyst 全面審查 |
| Migration | Contract Map 缺失 | sd-architect 使用 contract-generate |
| Performance | SLO 未定義就開始優化 | PBS Gate 強制前置 |
| Integration | Consumer Contract 不完整 | SCG-3 強制 Contract 凍結 |
| DevOps | Pipeline 與 Spec 不一致 | SCG-4 PR Review 逐項比對 |
| Testing | RTM 覆蓋率計算錯誤 | rtm-generate 自動統計 |
| Documentation | 文檔與實作脫節 | SCG-4 強制同步更新 |
| Security | STRIDE 分析不完整 | security-engineer 逐威脅類別確認 |

---

## 緊急修復程序

當已發布的規格需緊急更新時：

```
1. 建立緊急 ADR（記錄為何需要緊急變更）
2. 通知所有相關 Agent 和 Stakeholder
3. 更新規格文件（版本號 +0.0.1）
4. 重新執行受影響的 SCG 閘門
5. 🔴 人工確認新規格凍結
6. 修正實作並執行 SCG-4 PR Review
```

---

## 相關文檔

- `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` — SCG 閘門執行規範
- `workflow/core/change-management.md` — 規格變更管理流程
- `.claude/skills/sdd-gate/SKILL.md` — sdd-gate 技能使用說明
- `.claude/skills/spec-compliance-check/SKILL.md` — 規格合規檢查使用說明

---

**維護者**: AISDLC-SDD Framework Team
**SDD 版本**: v0.01
**最後更新**: 2026-04-15
