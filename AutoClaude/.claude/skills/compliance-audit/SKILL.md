---
name: compliance-audit
description: 執行合規審查，涵蓋 GDPR、HIPAA、PCI-DSS、SOC 2、ISO 27001 等標準
user-invocable: true
disable-model-invocation: false
argument-hint: "<standard: 合規標準 (gdpr/hipaa/pci-dss/soc2/iso27001/all)> [scope: 審查範圍 (full/data/access/privacy)]"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Compliance Audit Skill

基於 AISDLC Compliance Officer Agent 的合規審查技能，支援多種國際合規標準。

---

## 觸發方式

```bash
/compliance-audit gdpr              # GDPR 合規審查
/compliance-audit hipaa             # HIPAA 合規審查
/compliance-audit pci-dss           # PCI-DSS 合規審查
/compliance-audit soc2              # SOC 2 準備度檢查
/compliance-audit iso27001          # ISO 27001 準備度檢查
/compliance-audit all               # 全面合規審查
/compliance-audit gdpr privacy      # GDPR 隱私專項
```

---

## 執行流程

### 階段 1: 範圍確定 🔴

**任務清單**:
1. 識別適用法規：
   - 業務所在地域（EU → GDPR、US Healthcare → HIPAA）
   - 資料類型（個人資料、健康資訊、支付卡資料）
   - 行業要求（金融、醫療、電商）

2. 定義評估範圍：
   - 涵蓋的系統和應用
   - 資料流和處理活動
   - 地理覆蓋範圍

3. 🔴 **確認點**: 向使用者確認：
   - 適用的合規標準正確嗎？
   - 評估範圍是否完整？
   - 是否有即將到來的稽核時程？

---

### 階段 2: 自動化掃描

**依賴和配置檢查**:
```bash
# 檢查敏感資料處理
grep -r "password\|secret\|api.key\|token" --include="*.ts" --include="*.js" .

# 檢查加密配置
grep -r "AES\|RSA\|bcrypt\|argon2\|crypto" --include="*.ts" --include="*.js" .

# 檢查日誌是否包含敏感資料
grep -r "console\.log.*password\|console\.log.*token" --include="*.ts" --include="*.js" .
```

**環境變數安全**:
```bash
# 檢查 .env 是否被 git 追蹤
git ls-files | grep -E "\.env$|\.env\."

# 檢查硬編碼的密鑰
grep -r "sk_live\|pk_live\|AKIA" --include="*.ts" --include="*.js" --include="*.json" .
```

---

### 階段 3: GDPR 檢查清單

#### 資料主體權利實現

- [ ] **存取權 (Art. 15)** - 使用者可匯出個人資料
- [ ] **更正權 (Art. 16)** - 使用者可更新個人資料
- [ ] **刪除權 (Art. 17)** - 帳戶刪除功能
- [ ] **資料可攜權 (Art. 20)** - JSON/CSV 匯出
- [ ] **反對權 (Art. 21)** - 行銷退出機制

**實作範例**:
```typescript
// ✅ DSAR API 端點
app.get('/api/user/data-export', auth, async (req, res) => {
  const userData = await collectAllUserData(req.user.id);
  res.json({
    format: 'GDPR_EXPORT',
    generatedAt: new Date().toISOString(),
    data: userData
  });
});

// ✅ 帳戶刪除
app.delete('/api/user/account', auth, async (req, res) => {
  await scheduleAccountDeletion(req.user.id, 30); // 30天寬限期
  res.json({ message: 'Account scheduled for deletion' });
});
```

#### 同意管理

- [ ] 明確同意機制（非預勾選）
- [ ] 同意記錄保存
- [ ] 撤回同意功能
- [ ] Cookie 同意橫幅

#### 資料保護

- [ ] 傳輸加密 (TLS 1.2+)
- [ ] 儲存加密
- [ ] 最小化資料收集
- [ ] 資料保留政策

---

### 階段 4: HIPAA 檢查清單

#### Administrative Safeguards

- [ ] 指定隱私專員 (Privacy Officer)
- [ ] 指定安全專員 (Security Officer)
- [ ] 員工培訓記錄
- [ ] 業務夥伴協議 (BAA)
- [ ] 風險評估文件

#### Technical Safeguards

- [ ] 唯一使用者識別
- [ ] 自動登出機制
- [ ] 稽核控制 (Audit Logs)
- [ ] ePHI 加密
- [ ] 完整性控制

**稽核日誌範例**:
```typescript
// ✅ PHI 存取日誌
const auditLog = {
  timestamp: new Date().toISOString(),
  userId: user.id,
  action: 'VIEW_PHI',
  resourceType: 'PatientRecord',
  resourceId: patientId,
  ipAddress: req.ip,
  outcome: 'SUCCESS'
};
await saveAuditLog(auditLog);
```

#### Physical Safeguards

- [ ] 設施存取控制
- [ ] 工作站安全政策
- [ ] 裝置媒體控制

---

### 階段 5: PCI-DSS 檢查清單

#### 網路安全

- [ ] 防火牆配置
- [ ] 網路區隔 (CDE 隔離)
- [ ] 變更預設密碼

#### 持卡人資料保護

- [ ] PAN 不明文儲存
- [ ] 使用加密或 Token 化
- [ ] 傳輸加密 (TLS 1.2+)

**Token 化範例**:
```typescript
// ❌ 不合規 - 儲存完整 PAN
await db.save({ cardNumber: '4111111111111111' });

// ✅ 合規 - 使用 Stripe Token
const token = await stripe.tokens.create({ card: cardDetails });
await db.save({ stripeTokenId: token.id, last4: '1111' });
```

#### 存取控制

- [ ] 最小權限原則
- [ ] 唯一使用者 ID
- [ ] MFA 實施

#### 監控與測試

- [ ] 稽核軌跡
- [ ] 日誌集中管理
- [ ] 每季漏洞掃描
- [ ] 每年滲透測試

---

### 階段 6: SOC 2 / ISO 27001 準備度

#### 信任服務準則 (SOC 2)

| 準則 | 狀態 | 證據 |
|------|------|------|
| Security | ⬜ | 存取控制、加密、監控 |
| Availability | ⬜ | SLA、備援、災復 |
| Processing Integrity | ⬜ | 輸入驗證、錯誤處理 |
| Confidentiality | ⬜ | 資料分類、加密 |
| Privacy | ⬜ | 隱私政策、同意 |

#### ISO 27001 ISMS

- [ ] 資訊安全政策
- [ ] 風險評估文件
- [ ] 適用性聲明 (SoA)
- [ ] 內部稽核計畫
- [ ] 管理審查記錄

---

### 階段 7: 缺口分析報告 🔴

**報告結構**:
```markdown
## 合規審查報告

### 執行摘要
- 審查日期: YYYY-MM-DD
- 審查標準: [標準清單]
- 整體合規狀態: X%

### 缺口摘要

#### 🔴 P0 - 關鍵缺口 (需立即處理)
| 法規 | 要求 | 現狀 | 缺口 | 補救措施 | 估計工時 |
|------|------|------|------|----------|---------|
| GDPR Art.17 | 刪除權 | 無 | 完全缺失 | 實作帳戶刪除 API | 16h |

#### 🟡 P1 - 高優先級 (1-3個月)
...

#### ⚪ P2 - 中優先級 (6個月)
...

### 補救路線圖
1. Week 1-2: 處理 P0 缺口
2. Month 1-3: 處理 P1 缺口
3. Month 3-6: 處理 P2 缺口

### 下次稽核準備建議
```

🔴 **確認點**: 與使用者確認缺口優先級排序

---

## 產出物

| 產出物 | 說明 |
|--------|------|
| 合規缺口分析報告 | 完整缺口清單與補救計畫 |
| 合規檢查清單 | 依標準分類的檢查項目 |
| 補救路線圖 | 時程與責任分配 |
| 隱私政策草稿 | GDPR 合規的隱私政策 (如需要) |
| 稽核證據清單 | 已收集的合規證據 |

---

## 相關 Skill

- `/security` - 安全審計（技術層面）
- `/integration-oauth` - 認證合規
- `/documentation-api` - API 文檔合規

---

## 相關檔案

- Agent 參考: `agent/specialized/compliance-officer-zh.yaml`
- SOP 參考: `scenarios/security/SOP_QuickRef.md`

---

## 支援標準摘要

| 標準 | 全名 | 適用情境 |
|------|------|---------|
| GDPR | General Data Protection Regulation | 處理 EU 居民個人資料 |
| HIPAA | Health Insurance Portability and Accountability Act | 美國醫療資料 |
| PCI-DSS | Payment Card Industry Data Security Standard | 支付卡資料處理 |
| SOC 2 | System and Organization Controls | SaaS 服務供應商 |
| ISO 27001 | Information Security Management System | 資訊安全認證 |

---

**基於**: AISDLC v0.09 Compliance Officer Agent
**維護者**: AISDLC Framework Team
