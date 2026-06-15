# Incident Response Specification — Template
# 事件回應規格模板
# Phase 05 — Security 情境 SDD 強化（Stage 6）

**文件類型**: Incident Response Specification (IRS)
**SDD 原則**: 事件回應流程必須先規格化，不可臨場即興
**存放位置**: `docs/06_quality/security/INCIDENT-RESPONSE-SPEC-{system}-{date}.md`

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **系統名稱** | {SystemName} |
| **建立日期** | {YYYY-MM-DD} |
| **負責人** | {Security Engineer + DevOps Lead} |
| **前置文件** | STRIDE-THREAT-MODEL, SAD, SECURITY-MONITORING-SPEC |
| **法規要求** | GDPR Art.33（72h 通報）/ PCI-DSS Req.12 |

---

## 1. 事件分類與嚴重度

### 1.1 安全事件分類

| 分類 | 說明 | 典型場景 |
|------|------|---------|
| P0 - Critical | 正在發生的攻擊，資料洩露確認或高度疑似 | APT 攻擊、大量 PII 洩露、勒索軟體 |
| P1 - High | 高風險異常，可能造成安全違規 | 帳號入侵、未授權管理員存取、SQL Injection 成功 |
| P2 - Medium | 可疑行為，需要調查評估 | 暴力破解嘗試、異常 API 呼叫模式 |
| P3 - Low | 輕微異常，定期審查 | 單次異常登入、低風險漏洞 |

### 1.2 資料洩露嚴重度分級

| 等級 | 定義 | 法規通報要求 |
|------|------|------------|
| Tier 1 | 確認 PII/PCI 資料外洩 | GDPR 72h 通報 DPA + 通知當事人 |
| Tier 2 | 疑似資料洩露，尚未確認 | 72h 內調查完成，確認後通報 |
| Tier 3 | 系統入侵但無確認資料洩露 | 記錄並評估，30 天內完成報告 |

---

## 2. 事件回應流程（IRP）

### 2.1 標準事件回應階段

```
階段 1：識別（Identification）
  ├── 事件來源：安全監控告警 / 使用者回報 / 自動偵測
  ├── 初步分類：P0-P3 嚴重度評估
  ├── 建立事件票（Incident Ticket）
  └── 目標時間：P0 < 5 分鐘 / P1 < 15 分鐘

階段 2：抑制（Containment）
  ├── 短期抑制：隔離受影響系統/帳號/端點
  ├── 長期抑制：補丁、規則更新、存取撤銷
  ├── 證據保存：日誌快照、記憶體 Dump
  └── 目標時間：P0 < 30 分鐘 / P1 < 2 小時

階段 3：根本原因分析（Investigation）
  ├── 攻擊路徑重建（Attack Timeline）
  ├── 影響範圍評估（Blast Radius Assessment）
  ├── IoC（Indicators of Compromise）識別
  └── 目標時間：P0 < 4 小時 / P1 < 24 小時

階段 4：根除（Eradication）
  ├── 移除惡意程式碼/後門
  ├── 修補漏洞（臨時 + 永久）
  ├── 憑證輪換（所有受影響帳號/金鑰）
  └── 強化安全控制

階段 5：恢復（Recovery）
  ├── 系統恢復驗證（Integrity Check）
  ├── 服務恢復（分階段）
  ├── 增強監控（30 天）
  └── 恢復後安全驗證

階段 6：事後學習（Lessons Learned）
  ├── 事件報告撰寫（72 小時內完成）
  ├── 根本原因分析（Root Cause Analysis）
  ├── 安全控制改善計畫
  └── 回歸測試更新（SECURITY-TEST-SPEC）
```

### 2.2 P0 事件快速回應流程（15 分鐘決策樹）

```
P0 告警觸發
  │
  ├── [0-5 min] On-Call Engineer 確認告警真實性
  │     ├── 誤報 → 關閉告警，記錄原因
  │     └── 真實事件 → 繼續
  │
  ├── [5-10 min] 初步抑制
  │     ├── 封鎖來源 IP/帳號
  │     ├── 啟動 War Room（Slack #incident-response）
  │     └── 通知 Security Lead + CTO
  │
  ├── [10-15 min] 影響評估
  │     ├── 受影響系統/資料範圍
  │     ├── 是否涉及 PII/PCI 資料？
  │     │     ├── 是 → 啟動 GDPR Art.33 計時器（72h）
  │     │     └── 否 → 繼續標準流程
  │     └── 決定是否需要服務停機
  │
  └── [15 min+] 根據 Runbook 繼續執行
```

---

## 3. 通報與通知規格

### 3.1 內部通報矩陣

| 事件等級 | 立即通知 | 1 小時內通知 | 24 小時內通知 |
|---------|---------|------------|------------|
| P0 | On-Call + Security Lead + CTO | 全體安全團隊 + 法務 + 合規 | 董事會（視情況） |
| P1 | On-Call + Security Lead | 安全團隊 + 相關部門主管 | 高層管理 |
| P2 | On-Call | 安全團隊 | — |
| P3 | 記錄至工單 | — | 週報整合 |

### 3.2 外部法規通報規格

| 法規 | 觸發條件 | 通報期限 | 通報對象 | 通報方式 |
|------|---------|---------|---------|---------|
| GDPR Art.33 | 確認 EU 公民個資洩露 | 72 小時 | 主管機關（DPA） | 書面通報 |
| GDPR Art.34 | 高風險個資洩露 | 盡快（無特定期限） | 資料主體（當事人） | 直接通知 |
| PCI-DSS | 持卡人資料洩露 | 立即 | Card Brands + Acquirer | 書面通報 |
| {其他法規} | {觸發條件} | {期限} | {對象} | {方式} |

### 3.3 GDPR Art.33 通報模板

```
通報內容必須包含：
1. 事件性質說明（洩露類型）
2. 相關資料主體類別和近似人數
3. 個人資料記錄類別和近似數量
4. 資料保護官（DPO）聯絡資訊
5. 事件可能造成的後果描述
6. 已採取或建議採取的補救措施

自動生成 Checklist：
  □ 事件識別時間記錄
  □ 初步影響評估完成
  □ 法律/合規團隊知悉
  □ 通報文件草稿（T+24h）
  □ 最終通報提交（T+72h）
```

---

## 4. 事件回應 Runbook

### 4.1 帳號入侵 Runbook（IRS-RB-001）

```
觸發：SEC-ALERT-AUTH-001/002/003

Step 1 — 確認（5 分鐘）
  □ 確認是否為測試/滲透測試活動
  □ 識別受影響帳號
  □ 確認最後合法登入時間

Step 2 — 抑制（10 分鐘）
  □ 強制登出所有 Session
  □ 暫停帳號（不刪除，保留證據）
  □ 封鎖來源 IP（臨時）
  □ 通知帳號擁有者

Step 3 — 調查（1 小時）
  □ 審查登入日誌（24-72 小時）
  □ 識別所有異常活動
  □ 確認資料存取範圍
  □ 查找橫向移動跡象

Step 4 — 根除
  □ 重置密碼（強制）
  □ 強制 MFA 重新設定
  □ 審查帳號權限（最小化）
  □ 更新異常行為偵測規則

Step 5 — 恢復與記錄
  □ 帳號恢復並加強監控
  □ 完成事件報告
  □ 更新 SECURITY-MONITORING-SPEC（如需）
```

### 4.2 資料洩露 Runbook（IRS-RB-002）

```
觸發：SEC-ALERT-INFO-001/002/003 或 外部通報

Step 1 — 立即抑制（15 分鐘）
  □ 識別洩露資料類型和範圍
  □ 封鎖資料洩露路徑
  □ 啟動法律/合規通知
  □ 開始 GDPR 72h 計時（如適用）

Step 2 — 取證（2 小時）
  □ 保全相關日誌（防止覆蓋）
  □ 記錄受影響資料主體清單
  □ 攻擊向量分析
  □ 資料外洩量估算

Step 3 — 通報準備
  □ 草擬 GDPR Art.33 通報（如適用）
  □ 法律審查
  □ T+72h 前提交監管機關

Step 4 — 補救
  □ 修補漏洞
  □ 加密所有靜態 PII
  □ 存取控制審查
  □ 通知受影響使用者（如要求）
```

### 4.3 DDoS 攻擊 Runbook（IRS-RB-003）

```
觸發：SEC-ALERT-DOS-001

Step 1 — 立即回應（5 分鐘）
  □ 確認是否為合法流量激增 vs 攻擊
  □ 啟用 CDN/WAF DDoS 防護模式
  □ 通知 Cloud Provider Support

Step 2 — 緩解（15 分鐘）
  □ 啟用速率限制（降低閾值）
  □ 封鎖惡意 IP 範圍
  □ 評估是否需要臨時停機保護後端
  □ 啟動 Auto-Scaling

Step 3 — 監控與恢復
  □ 監控流量直至正常
  □ 逐步放寬限制
  □ 記錄攻擊特徵（IoA）
  □ 更新 WAF 規則

Step 4 — 事後
  □ 攻擊規模分析報告
  □ 評估 DDoS 防護策略調整
  □ 更新 SECURITY-MONITORING-SPEC
```

---

## 5. 事件溝通規格

### 5.1 War Room 設定

| 項目 | 規格 |
|------|------|
| 溝通管道 | {Slack #incident-response / Teams 頻道} |
| 橋接電話 | {電話會議連結} |
| 文件空間 | {Confluence / Google Drive 事件資料夾} |
| 工單系統 | {Jira / ServiceNow 事件工單} |
| 角色分配 | Incident Commander / Tech Lead / Comms Lead |

### 5.2 狀態更新頻率

| 事件等級 | 更新頻率 | 更新對象 |
|---------|---------|---------|
| P0 | 每 15 分鐘 | 全指揮鏈 |
| P1 | 每 30 分鐘 | 安全 + 管理層 |
| P2 | 每 2 小時 | 安全團隊 |
| P3 | 每日 | 工單記錄 |

---

## 6. 事件後報告規格

### 6.1 報告結構（72 小時內完成）

```
事件報告 — 必含以下章節：

1. 執行摘要
   - 事件 ID、時間線、影響範圍、根本原因（一段摘要）

2. 事件時間線
   - 發現時間、抑制時間、根除時間、恢復時間

3. 根本原因分析（5 Whys）
   - 直接原因 → 深層原因 → 系統性原因

4. 影響評估
   - 受影響系統/資料/使用者
   - 業務影響（停機時間/資料洩露量）

5. 採取的回應行動
   - 時間線對應的行動清單

6. 補救措施（已完成 + 計畫中）
   - 短期修復 + 長期改善

7. 回歸測試新增
   - 新增至 SECURITY-TEST-SPEC 的測試案例

8. 流程改進建議
   - 預防類似事件的建議
```

### 6.2 事件指標記錄

| 指標 | 說明 |
|------|------|
| MTTD（平均偵測時間） | 事件發生到偵測的時間 |
| MTTI（平均識別時間） | 告警到確認為真實事件的時間 |
| MTTR（平均回應時間） | 識別到事件抑制的時間 |
| MTTRS（平均恢復時間） | 抑制到完全恢復的時間 |

---

## 7. 聯絡清單（On-Call Roster）

| 角色 | 姓名 | 主要聯絡 | 備用聯絡 | 備份 |
|------|------|---------|---------|------|
| Security Lead | {name} | {phone} | {email} | {backup} |
| DevOps On-Call | {name} | {phone} | {email} | {backup} |
| DBA On-Call | {name} | {phone} | {email} | {backup} |
| Legal/Compliance | {name} | {phone} | {email} | {backup} |
| CTO/管理層 | {name} | {phone} | {email} | {backup} |
| Cloud Provider Support | {support_line} | — | — | — |

---

> **參考文件**:
> - 安全監控規格: SECURITY-MONITORING-SPEC-{system}.md
> - STRIDE 威脅模型: STRIDE-THREAT-MODEL-{system}.md
> - 安全測試規格: SECURITY-TEST-SPEC-{system}.md
