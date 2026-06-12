# Migration 技術棧遷移 SOP

**版本**: v0.01 | **最後更新**: 2026-03-26
> 📝 **關於範例連結說明**:
> 本 SOP 中部分連結為示例性質，實際使用時請根據您的專案結構調整路徑。

## 🎯 情境概述

**適用場景**：全技術棧遷移（前端/後端/DB 框架替換）、資料庫平台遷移、系統現代化（含新平台擴展）

**與 Refactoring 的區別**：
| 維度 | Refactoring | Migration |
|------|------------|-----------|
| **代碼變更** | 改善既有代碼結構 | 用新技術棧重寫 |
| **行為** | 功能不變 (Preserve Behavior) | 功能對等 + 可新增功能 |
| **技術棧** | 不變 | 全面替換 |
| **資料庫** | 通常不變 | 可能遷移 |
| **平台** | 不變 | 可能擴展新平台 |

**預計時間**:
- 📋 **AISDLC 規劃階段**: 4-8 小時
- 🔨 **實際執行階段**:
  - 小規模遷移（單層遷移，如僅 DB）: 2-4 週
  - 中規模遷移（雙層遷移，如前端+後端）: 4-8 週
  - 大規模遷移（全棧+新平台）: 8-20 週

**涉及角色**：SD, SA, Code-Analyzer, Dev-Senior, QA, Dev, BA, PM/PO, DevOps

**最終產出**：遷移映射報告 + 資料庫遷移計畫 + 遷移實作指引 + 驗證測試計畫 + 並行運行方案 + 前後對比報告

---

## 🤝 協作模式 (Phase 2: v0.03)

### 主要協作模式

#### 1. Lead-Support (主導-支援)
- **主導 Agent**: SD-Architect (遷移架構設計)
- **支援 Agents**: SA (需求重新分析), Code-Analyzer (影響評估), Dev-Senior (技術決策)
- **使用階段**: 遷移策略設計、架構映射、技術選型
- **模式說明**: SD 主導遷移架構，SA 確保業務邏輯完整，Code-Analyzer 評估遷移影響

#### 2. Sequential-Handoff (順序交接)
- **流程**: SA 需求分析 → SD 架構設計 → Dev 實作 → QA 驗證
- **使用階段**: 完整遷移生命週期
- **模式說明**: 嚴格順序交接確保每層遷移的品質

#### 3. Parallel-Execution (平行執行)
- **流程**: 前端遷移 ∥ 後端遷移 ∥ DB 遷移（在架構確認後可平行）
- **使用階段**: 多層同步遷移
- **模式說明**: 各層有獨立的介面契約，可平行開發

### 次要協作模式

#### 4. Peer-Review (同儕審查)
- **使用階段**: Code-Analyzer ↔ Dev-Senior 遷移方案審查
- **模式說明**: 確保遷移方案的技術可行性和風險可控

---

## 🔒 Layer 0: Security Baseline（強制前置）

> **🔴 v0.01 CI/CD 強化**: 所有 CI/CD Pipeline 建置**必須先完成 Layer 0 安全基線**，再進入後續階段。
> Layer 0 是跨所有情境的強制安全基線，包含 Secret Detection、SCA、License Compliance。

**執行步驟**: 參考 [devops-setup-flow.md 步驟 0](../../workflow/scenario-specific/devops-setup-flow.md)
**配置範本**: [Layer0_Security_Baseline_Template.md](../../docs_template/scenario_specific/devops/Layer0_Security_Baseline_Template.md)
**CI 範本**: [GitHub Actions](../../docs_template/scenario_specific/devops/github-actions/security-baseline.yml) | [GitLab CI](../../docs_template/scenario_specific/devops/gitlab-ci/security-baseline-template.yml)

---

## 🔨 Layer 1: Build & Verify（強制建置驗證）

> **🔴 v0.01 CI/CD 強化**: Layer 0 通過後，**必須完成 Layer 1 建置驗證**。
> Migration 情境覆蓋率閾值 **70%**（新棧），舊棧需維持既有覆蓋率水準。

**執行步驟**: 參考 [devops-setup-flow.md 步驟 0.5](../../workflow/scenario-specific/devops-setup-flow.md)
**配置範本**: [Layer1_Build_Verify_Template.md](../../docs_template/scenario_specific/devops/Layer1_Build_Verify_Template.md)
**CI 範本**: [GitHub Actions](../../docs_template/scenario_specific/devops/github-actions/build-verify.yml) | [GitLab CI](../../docs_template/scenario_specific/devops/gitlab-ci/build-verify-template.yml)

---

## 🔄 Migration 專屬 Pipeline（Layer 2 + Layer 3）

> **🔴 最高風險情境**: Migration 需要額外的 Layer 2 (Contract Test) + Layer 3 (Canary Deploy + Rollback Gate)。
> 這些是 Migration 情境的強制 Pipeline 階段，確保技術棧遷移的安全性。

**Pipeline 架構**:
```
L0 Security → L1 Build → L2 Dual-Build + Contract Test → L3 Canary + Rollback Gate
```

**配置範本**: [Migration_Pipeline_Template.md](../../docs_template/scenario_specific/devops/Migration_Pipeline_Template.md)
**CI 範本**: [GitHub Actions](../../docs_template/scenario_specific/devops/github-actions/migration-pipeline.yml) | [GitLab CI](../../docs_template/scenario_specific/devops/gitlab-ci/migration-pipeline-template.yml)

---

## 🛡️ 增強安全掃描: SAST + Container Scan（Advanced 等級）

> **Migration 情境安全等級: Advanced** (L0 + L1 + SAST + Container Scan)
> 新舊棧都要掃描，確保遷移過程不引入安全漏洞。

| 掃描類型 | 工具 | 阻塞策略 | 說明 |
|---------|------|---------|------|
| **SAST** | Semgrep / CodeQL | 🔴 Critical/High 阻塞 | 新舊棧程式碼都要掃描 |
| **Container Scan** | Trivy / Grype | 🔴 有 Docker 時強制 | 新舊映像都要掃描 |
| **DAST** | OWASP ZAP | ⚠️ 選配 | Staging 部署後動態測試 |

**配置範本**: [Security_Scan_Integration_Template.md](../../docs_template/scenario_specific/devops/Security_Scan_Integration_Template.md)
**CI 範本**: [GitHub Actions](../../docs_template/scenario_specific/devops/github-actions/security-scan-enhanced.yml) | [GitLab CI](../../docs_template/scenario_specific/devops/gitlab-ci/security-scan-enhanced-template.yml)

### ⚡ Performance Benchmark Gate（⚠️ 選配 Micro + 新舊棧比對）

> Migration 情境可選配 Micro-Benchmark 偵測遷移後效能退化，Nightly 可做新舊棧效能比對。

| 層級 | 觸發時機 | 阻塞策略 | 說明 |
|------|---------|---------|------|
| **Micro-Benchmark** | 每次 PR | 🔴 退化 > 10% 阻塞 | 新棧效能退化偵測 |
| **Full Load Test** | Nightly | ⚠️ 僅警告 | 新舊棧效能比對 |

📖 **配置範本**: [Performance_Benchmark_Gate_Template.md](../../docs_template/scenario_specific/devops/Performance_Benchmark_Gate_Template.md)
🔧 **建置流程**: [devops-setup-flow 步驟 0.8](../../workflow/scenario-specific/devops-setup-flow.md)

### 📝 Documentation Pipeline（⚠️ 選配）

> Migration 情境可選配 Doc Lint + Link Check，確保遷移文檔品質。

📖 **配置範本**: [Documentation_Pipeline_Template.md](../../docs_template/scenario_specific/devops/Documentation_Pipeline_Template.md)
🔧 **建置流程**: [devops-setup-flow 步驟 0.9](../../workflow/scenario-specific/devops-setup-flow.md)

### 🔔 Event-Driven Agent Notification（🔴 強制）

> Migration 情境為最高風險情境，PR 事件通知 + Canary 部署進度通知 + 回滾警報均為**強制**。
> 情境專屬觸發：dual-build 結果、contract-test 結果、canary 每階段進度、rollback gate 觸發。

📖 **配置範本**: [Event_Driven_Agent_Notification_Template.md](../../docs_template/scenario_specific/devops/Event_Driven_Agent_Notification_Template.md)
🔧 **建置流程**: [devops-setup-flow 步驟 0.10](../../workflow/scenario-specific/devops-setup-flow.md)

---

## 📋 前置準備檢查清單

### 必要材料
- [ ] 舊系統完整代碼庫存取權限
- [ ] 舊系統技術棧清單（框架/版本/依賴）
- [ ] 新技術棧選型確認
- [ ] 現有資料庫 Schema（DDL 匯出）
- [ ] API 文檔或端點清單
- [ ] 業務邏輯文檔（如有）
- [ ] 遷移時間預算與團隊資源

### 選擇性材料
- [ ] 代碼品質報告
- [ ] 效能基準數據
- [ ] 測試覆蓋率報告
- [ ] 架構圖
- [ ] 第三方服務清單（API Key/帳號）

---

## 🎯 Claude Code Skills 整合指引

| 階段 | 建議 Skill | 觸發時機 |
|------|-----------|---------|
| 階段 1 現況分析 | `/brownfield-analysis` | 舊系統代碼品質與架構分析 |
| 階段 1 現況分析 | `/sa-analyst` | 需求重新分析、業務邏輯提取 |
| 階段 1 現況分析 | `/ba-analyst` | 業務邏輯完整性驗證（多業務域融合時必觸發） |
| 階段 2 遷移設計 | `/sd-architect` | 新架構設計、技術棧映射、並行運行設計 |
| 階段 2 遷移設計 | `/pm-planning` | 遷移優先級與 ROI 決策（X-Large 規模時） |
| 階段 3 DB 遷移 | `/database-migration` | 資料庫遷移規劃（Schema/SQL/SP 轉換） |
| 階段 3 DB 遷移 | `/integration-database` | 新 DB 整合方案（ORM/連線池/交易管理） |
| 階段 4 API 設計 | `/integration-api-client` | API 契約設計（新舊 API 對照） |
| 階段 5 前端遷移 | `/dev-review` | 遷移代碼審查 |
| 階段 6 行動端 | `/mobile-development` | Android/macOS 行動端開發規劃 |
| 階段 7 測試 | `/qa-testing` | 測試策略與驗收測試 |
| 階段 7 測試 | `/testing-strategy` | 跨系統對比測試（新舊系統行為等價驗證） |
| 階段 8 部署 | `/devops-github-actions` | CI/CD 4 層 Pipeline 建立 |
| 階段 8 部署 | `/release-management` | Canary 發布與回滾管理 |
| 全程 | `/security-audit` | 安全審計（新舊棧都要掃描） |
| 全程 | `/performance-optimization` | 效能基準線建立（Stage 1）與基準對比（Stage 7） |
| 全程 | `/compliance-audit` | 合規審查（電商支付 PCI-DSS / 個資 GDPR 時觸發） |
| 階段 3-5 | `/code-review` | 遷移代碼品質審查 |
| 階段 3-6 | `/sprint-planning` | 大規模遷移的 Phase 拆分與迭代規劃 |

---

## 🔄 開發-編譯-測試循環 (AISDLC 強制規則)

> **🔴 CRITICAL**：遷移實作階段必須嚴格遵守。

```
遷移 1 個模組/功能
    ↓
立即編譯 → 編譯失敗？ → 🔴 停止修復
    ↓
執行單元測試 → 失敗？ → 🔴 停止修復
    ↓
執行新舊系統對比測試 → 結果不一致？ → 🔴 停止修復
    ↓
全部通過 ✅ → Commit → 繼續下一個
```

---

## 🚀 完整執行流程

> **📋 Workflow 對應**：本 SOP 對應 [migration-planning-flow](../../workflow/scenario-specific/migration-planning-flow.md)，
> 載入 AISDLC_INIT.md 後會自動啟動該 Workflow，引導以下 9 個階段。

### 階段 1：現況分析與需求提取 (1-2 小時)

**載入 Agents**: SA (Primary), Code-Analyzer (Primary), SD (Primary), BA (Supporting - 業務邏輯完整性驗證), Performance-Engineer (Optional - 舊系統效能基準線建立)

#### 步驟 1.1：載入 AISDLC 框架
```
「請載入 AISDLC_SDD_INIT.md (v0.01)，我要進行技術棧遷移」
```

#### 步驟 1.2：情境識別問答

系統詢問：
- 遷移範圍（僅前端/僅後端/僅 DB/全棧/全棧+新平台）
- 舊技術棧（前端框架/後端框架/DB/語言）
- 新技術棧（前端框架/後端框架/DB/語言）
- 是否為生產系統？（影響並行運行策略）
- 是否涉及資料庫遷移？
- 是否需要新平台？（Android/iOS/macOS/Desktop）
- 是否涉及硬體整合？（無/掃碼槍/條碼掃描(手機相機)/NFC/藍牙印表機/其他）
- 是否涉及支付/個資/合規需求？（無/支付處理(PCI-DSS)/個人資料(GDPR)/醫療資料(HIPAA)/其他）
- 業務持續性要求（可停機/不可停機/可降級服務）
- 遷移時間預算

> **⚠️ 情境觸發指引**：
> - 若涉及硬體整合（掃碼/NFC 等），將載入 Integration-Specialist Agent
> - 若涉及支付/個資/合規需求，將額外觸發 `/compliance-audit` 和載入 Compliance-Officer Agent
> - 若涉及新平台且包含 macOS，需同時載入 SD-Architect（桌面端主導）+ SD-Mobile-Architect（Apple 生態經驗）

#### 步驟 1.3：舊系統全面掃描 (Code-Analyzer + SA)

**前端分析**：
- [ ] 頁面/元件清單與數量統計
- [ ] 路由結構映射
- [ ] 狀態管理結構（Store/State）
- [ ] 第三方 UI 元件庫清單

**後端分析**：
- [ ] API 端點清單與參數定義
- [ ] Service 層業務邏輯清單
- [ ] 中介層/Middleware 清單
- [ ] 排程任務清單

**資料庫分析**：
- [ ] Schema 完整匯出（表/欄位/型別/約束/索引）
- [ ] Stored Procedure / Function / Trigger 清單
- [ ] View / Materialized View 清單
- [ ] 資料量統計（各表行數/總大小）
- [ ] 平台特有功能使用清單

**業務邏輯提取**：
- [ ] 逐模組列出所有計算邏輯
- [ ] 逐模組列出所有驗證規則
- [ ] 逐模組列出所有狀態流轉

> 🔴 **人機協作點：現況分析確認**
> - ✅ 分析結果是否完整準確
> - ✅ 業務邏輯提取是否有遺漏
> - ✅ 補充 AI 無法識別的隱含邏輯

---

### 階段 2：遷移架構設計 (1-1.5 小時)

**載入 Agents**: SD (Lead), Dev-Senior, PM/PO (ROI 決策), Security-Engineer (Optional - 安全敏感模組評估)

#### 步驟 2.1：技術棧映射表

| 維度 | 舊技術 | 新技術 | 映射策略 |
|------|--------|--------|---------|
| 前端框架 | [舊] | [新] | 元件逐一對應 |
| 狀態管理 | [舊] | [新] | Store 結構映射 |
| 路由 | [舊] | [新] | 路由表映射 |
| UI 元件庫 | [舊] | [新] | 替代方案表 |
| 後端框架 | [舊] | [新] | API 對應 |
| ORM | [舊] | [新] | Model 映射 |
| 認證 | [舊] | [新] | Auth 方案 |
| DB | [舊] | [新] | Schema 轉換 |

#### 步驟 2.2：遷移策略選擇

**推薦策略：分層漸進遷移 (Layered Progressive Migration)**

```
Phase 1: DB 層遷移 → Schema + 資料 + SP 轉換
    ↓
Phase 2: 後端層遷移 → API 重新實作 + 對比驗證
    ↓
Phase 3: 前端層遷移 → 逐模組重寫 + 功能對等測試
    ↓
Phase 4: 新平台開發 → API 穩定後啟動行動端
    ↓
Phase 5: 並行運行 → 雙系統驗證 + 漸進切換
    ↓
Phase 6: 舊系統退役
```

#### 步驟 2.3：並行運行設計

```
                    ┌─ 新前端 (React/Next.js)
用戶 → Load Balancer ┤
                    └─ 舊前端 (Vue 3)
                            │
                    ┌─ 新後端 (Spring Boot)
        API Gateway ┤
                    └─ 舊後端 (Python)
                            │
                    ┌─ 新 DB (PostgreSQL) ←── CDC 同步
                    └─ 舊 DB (Oracle)
```

#### 步驟 2.4：🆕 多業務域 DDD Bounded Context 分析（融合多業務域時必須執行）

> **⚠️ 觸發條件**：系統融合 2 個以上不同業務領域時（如電商+民宿+CMS+知識管理），必須執行此步驟。
> 遷移是重新設計架構的最佳時機，應同步進行 Bounded Context 劃分。

| 分析步驟 | 分析內容 | 產出 |
|---------|---------|------|
| **業務域識別** | 識別系統中各個 Bounded Context<br>每個 Context 有獨立的業務語言和邊界 | Bounded Context 地圖 |
| **Context 邊界劃定** | 確認各 Context 的資料歸屬<br>識別跨 Context 共用資料（如 User 跨所有 Context）<br>設計 Context Mapping（Shared Kernel / ACL） | Context Mapping 圖 |
| **共用模組識別** | 跨域共用模組：Auth, User, Notification, File<br>設計共用模組 API 合約（禁止直接 DB 共享） | 共用模組清單與 API 合約 |
| **遷移優先順序** | 按業務重要性與依賴關係排序 Context 遷移順序<br>建議：先遷移邊緣 Context，最後遷移核心 Context | 分層遷移計畫 |

> **💡 常見多業務域 Context 建議**：
> - **電商**：OrderCtx, ProductCtx, PaymentCtx, CartCtx
> - **民宿管理**：PropertyCtx, BookingCtx, PricingCtx, HousekeepingCtx
> - **內容發布**：ContentCtx, PublishCtx, MediaCtx
> - **知識管理**：KnowledgeCtx, CategoryCtx, SearchCtx
> - **跨域共用**：UserCtx（認證/授權）, NotificationCtx, FileCtx

> 🔴 **人機協作點：遷移架構確認**
> - ✅ 技術棧映射是否準確
> - ✅ 遷移策略是否合適
> - ✅ 並行運行方案是否可行
> - ✅ 預估時程是否合理
> - ✅ **（多業務域時）** Bounded Context 劃分是否符合實際業務邊界
> - ✅ **（多業務域時）** 共用模組 API 合約是否合理

---

### 階段 3：資料庫遷移 (0.5-1 小時規劃 / 2-4 週執行)

**載入 Agents**: SD (Lead), Dev-Senior, Dev (Supporting - 遷移實作)

#### 步驟 3.1：Schema 轉換

**資料型別映射表**（以 Oracle→PostgreSQL 為例）：

| Oracle | PostgreSQL | 注意事項 |
|--------|-----------|---------|
| NUMBER(p,s) | NUMERIC(p,s) | 精度一致 |
| VARCHAR2(n) | VARCHAR(n) | 語義相同 |
| CLOB | TEXT | 無長度限制 |
| BLOB | BYTEA | 二進位存儲 |
| DATE | TIMESTAMP | Oracle DATE 含時間 |
| SYSDATE | NOW() | 函式替換 |
| SEQUENCE | SERIAL / SEQUENCE | 兩種方式 |

#### 步驟 3.2：SQL 語法轉換

| Oracle 語法 | PostgreSQL 等價 |
|------------|----------------|
| NVL(a, b) | COALESCE(a, b) |
| DECODE(a,b,c,d) | CASE WHEN a=b THEN c ELSE d END |
| ROWNUM | LIMIT / ROW_NUMBER() |
| CONNECT BY | WITH RECURSIVE |
| (+) outer join | LEFT/RIGHT JOIN |
| DUAL | 直接 SELECT |
| DBMS_OUTPUT | RAISE NOTICE |

#### 步驟 3.3：Stored Procedure 遷移策略

| 策略 | 適用情境 | 優缺點 |
|------|---------|--------|
| **轉為應用層** | 業務邏輯 SP | ✅ 可測試、可維護 / ❌ 需重寫 |
| **轉為 PL/pgSQL** | 資料處理 SP | ✅ 改動小 / ❌ 仍耦合 DB |
| **移除** | 不再需要的 SP | ✅ 減少複雜度 |

#### 步驟 3.4：資料遷移計畫

```
1. Schema 建立（DDL 轉換）
2. 靜態資料遷移（主檔/參數檔）
3. 動態資料遷移（交易資料）
4. 資料驗證（行數/加總/抽樣比對）
5. 增量同步方案（CDC / 雙寫）
6. 切換演練
```

**推薦工具**：ora2pg, pgloader, AWS DMS, Flyway (Schema Versioning)

**多表關聯回滾注意事項**：

> ⚠️ 若遷移涉及多表（外鍵關聯），回滾順序必須是遷移順序的**反向**。

```
遷移順序: 父表 → 子表 → 關聯表
回滾順序: 關聯表 → 子表 → 父表
```

> 🔴 **人機協作點：DB 遷移計畫確認**

---

### 階段 4：後端遷移設計 (30-40 分鐘規劃)

**載入 Agents**: SD + Dev-Senior + Dev (Supporting - 遷移實作) + QA

#### 步驟 4.1：API 契約定義

- [ ] RESTful API 端點映射（舊→新）
- [ ] Request/Response 格式對齊
- [ ] 認證/授權機制遷移
- [ ] 錯誤碼統一

#### 步驟 4.2：功能替換映射

| 舊技術 | 新技術等價方案 |
|--------|-------------|
| Python decorator | Spring AOP / @Annotation |
| Flask middleware | Spring Filter / Interceptor |
| Celery task | @Scheduled / Spring Batch |
| SQLAlchemy ORM | JPA / Hibernate |

> **⚠️ Python→Java 動態→靜態型別系統遷移注意事項**：
>
> | 遷移挑戰 | Python 做法 | Spring Boot 做法 | 遷移要點 |
> |---------|------------|-----------------|---------|
> | **API Request/Response** | dict / Pydantic model（鬆散） | 強型別 DTO（@RequestBody/@ResponseBody） | 必須為每個 API 端點明確定義 Java DTO 類別 |
> | **DB Entity** | SQLAlchemy Model（動態欄位） | JPA @Entity（嚴格型別） | 必須明確定義每個欄位的 Java 型別與 JPA 映射 |
> | **Optional 欄位** | Python `Optional[str]` / `None` | Java `Optional<String>` / `@Nullable` | 空值處理邏輯需顯式重寫 |
> | **型別轉換** | Python 自動轉換（`"1" == 1` 可能隱式） | Java 嚴格型別（需明確 cast） | 需全面檢查舊 API 的隱式型別轉換邏輯 |
> | **JSON 序列化** | Python dict 自動序列化 | Jackson 注解控制（`@JsonProperty`） | 欄位命名、日期格式、null 處理需顯式配置 |
>
> **建議**：建立「Python API → Java DTO 映射表」，逐端點確認型別完整性，避免隱式轉換遺漏。

> 🔴 **人機協作點：API 契約確認**

---

### 階段 5：前端遷移設計 (30-40 分鐘規劃)

#### 步驟 5.1：元件映射

| 舊元件 | 新元件 | 備註 |
|--------|--------|------|
| Vue SFC (.vue) | React Component (.tsx) | 模板→JSX |
| Pinia Store | Zustand / Redux | 狀態管理 |
| Vue Router | Next.js App Router | 路由系統 |
| Vuetify / Element Plus | MUI / Ant Design | UI 庫 |
| Composables | Custom Hooks | 邏輯復用 |

> **⚠️ CSR→SSR 認證策略遷移注意事項**（Vue3+Vite CSR → Next.js SSR）：
>
> | 問題面向 | Vue3 CSR 做法 | Next.js SSR 做法 | 遷移要點 |
> |---------|--------------|-----------------|---------|
> | **Token 儲存** | localStorage / sessionStorage JWT | httpOnly Cookie | Server Components 無法存取 localStorage，需改為 Cookie |
> | **Auth 框架** | 前端自建 auth store | next-auth / 自建 server session | 推薦使用 next-auth 統一管理 |
> | **資料取得** | Client-side axios fetch + store | RSC 直接 fetch / React Query（Client 元件） | Server Components 可直接呼叫 Service，不需 API 中轉 |
> | **路由守衛** | Vue Router Navigation Guard | Next.js Middleware (`middleware.ts`) | 伺服器端驗證，更安全 |
> | **Session 狀態** | Pinia store 保存用戶狀態 | Server Session Cookie + JWT | SSR 初始化時直接注入，減少 Client 請求 |

#### 步驟 5.2：頁面遷移順序

建議按業務優先級排序：
1. 核心頁面（進貨/銷貨/庫存查詢）
2. 報表頁面
3. 系統管理頁面
4. 其他次要頁面

> 🔴 **人機協作點：前端遷移計畫確認**

---

### 階段 6：新平台開發設計 (僅涉及新平台時, 20-30 分鐘)

**載入 Agents**: SD-Mobile-Architect, Integration-Specialist, Dev (Supporting - 行動端實作), QA-Mobile-Tester (Optional - 行動端測試)

- [ ] 行動端架構設計（原生 vs 跨平台）
- [ ] 共用 API 設計
- [ ] 離線支援策略
- [ ] 掃碼/硬體功能設計
- [ ] 推播通知設計

**macOS Desktop 特性考量**（涉及 macOS 時）：

> **⚠️ macOS 平台注意事項**：macOS 雖為 Apple 生態，但屬於**桌面平台**，與行動端 (iOS/Android) 的 UX 模式不同。

| 考量維度 | 設計要點 |
|---------|---------|
| **視窗管理** | 多視窗/分割視圖、拖放操作、右鍵選單 |
| **鍵盤導航** | 快捷鍵、Tab 導航、Touch Bar（如適用） |
| **大螢幕佈局** | 自適應佈局、側邊欄導航、Master-Detail 模式 |
| **系統整合** | 選單列整合、Dock 互動、Spotlight 搜尋、通知中心 |
| **技術選型** | Catalyst (iPad→Mac) / 原生 SwiftUI / Electron / Tauri |
| **掃碼方案** | 外接掃碼槍 (USB/藍牙 HID) 或 Continuity Camera (iPhone 充當掃描器) |

> 🔴 **人機協作點：行動端方案確認**

---

### 階段 7：驗證與測試規劃 (30-40 分鐘)

**載入 Agents**: QA (Lead), Code-Analyzer, Performance-Engineer (Optional - 效能基準對比驗證), QA-Mobile-Tester (Optional - 行動端測試)

#### 多維度驗證

**資料庫遷移驗證**：
- [ ] Schema 對齊（表/欄位/約束/索引）
- [ ] 資料完整性（逐表行數、主鍵、金額加總）
- [ ] SP 邏輯等價（同輸入→同輸出）

**跨系統一致性驗證**：
- [ ] API 響應比對（同請求→同回傳）
- [ ] 業務計算比對（進貨/銷貨/庫存結餘）
- [ ] 報表數據比對

**行動端驗證**（涉及新平台時）：
- [ ] 多裝置/多版本測試
- [ ] 掃碼功能各格式測試
- [ ] 離線/弱網路測試

**部署驗證**：
- [ ] 藍綠/金絲雀發布驗證
- [ ] 回滾機制測試
- [ ] 監控告警測試

> 🔴 **人機協作點：測試計畫確認**

---

### 階段 8：部署與切換 (20-30 分鐘規劃)

**載入 Agents**: DevOps, SD
**建議 Skill**: `/devops-github-actions`、`/release-management`

#### 步驟 8.1：CI/CD Pipeline 建立

> **🔴 v0.01 CI/CD 強化**: Migration 情境需要完整的 4 層 Pipeline（L0+L1+L2+L3）。

- [ ] Layer 0 Security Baseline 已配置（參考上方前置區段）
- [ ] Layer 1 Build & Verify 已配置（新棧 + 舊棧都要通過）
- [ ] Layer 2 Migration QA 已配置:
  - [ ] Dual-Build（舊棧 + 新棧平行建置）
  - [ ] Contract Test（API 相容性驗證，推薦 Pact）
  - [ ] Performance Comparison（新舊系統效能比對）
- [ ] Layer 3 Migration Deploy 已配置:
  - [ ] DB Migration Dry-Run + Rollback Script 驗證
  - [ ] Canary Deploy（5% → 25% → 50% → 100%）
  - [ ] Rollback Gate（錯誤率 > 1% 自動回滾）
  - [ ] Smoke + E2E 驗證

**配置範本**: [Migration_Pipeline_Template.md](../../docs_template/scenario_specific/devops/Migration_Pipeline_Template.md)

#### 步驟 8.2：Canary 部署與流量切換

- [ ] Canary 配置檔建立（`deploy/canary-config.yaml`）
- [ ] Rollback 腳本建立（`deploy/rollback.sh`）— **每個 Migration PR 必須附帶**
- [ ] DB Rollback SQL 建立（如適用）
- [ ] 漸進式流量切換計畫（含觀察時間和回滾閾值）
- [ ] 並行運行啟動（雙寫驗證機制）

**RTO/RPO 參考值**：

| 系統類型 | RTO (恢復時間目標) | RPO (恢復點目標) | 回滾策略 |
|---------|------------------|-----------------|---------|
| 電商核心（訂單/支付） | ≤ 15 分鐘 | ≤ 0（零資料損失） | 即時回切舊系統 + DB 雙寫 |
| 庫存管理 | ≤ 30 分鐘 | ≤ 5 分鐘 | Canary 回滾 + 最近快照 |
| 報表/分析 | ≤ 2 小時 | ≤ 1 小時 | 舊系統接管 |
| 民宿預約 | ≤ 30 分鐘 | ≤ 0（零資料損失） | 即時回切 + 訂單補償 |

#### 步驟 8.3：監控與退役

- [ ] 監控告警設定（錯誤率、延遲 P99、成功率）
- [ ] 雙寫資料一致性校驗排程
- [ ] 舊系統退役計畫（Contract Phase 時程）
- [ ] Expand-Contract Pattern DB Schema 變更驗證

> 🔴 **人機協作點：部署方案確認**
> - ✅ Canary 階段設計是否合理
> - ✅ Rollback 機制是否可靠
> - ✅ 雙寫驗證是否到位
> - ✅ 舊系統退役時程是否安全

---

### 階段 9：知識沉澱 (20 分鐘)

**載入 Agents**: Technical-Writer (Supporting - 文檔撰寫)

- [ ] 遷移映射手冊（前端/後端/DB 對照表）
- [ ] 架構決策記錄 (ADR)
- [ ] 經驗教訓文檔
- [ ] 新技術棧開發規範

**知識傳承方式（依團隊規模適配）**：

| 團隊規模 | 知識傳承方式 |
|---------|------------|
| **2 人團隊** | Pair Programming + 共同撰寫 ADR + Git 提交訊息詳述決策原因 |
| **3-5 人團隊** | 文檔導讀 + Code Walkthrough（非正式，30 分鐘） |
| **6+ 人團隊** | 正式遷移分享會 + 錄影 + Wiki 知識庫 |

> ⚠️ v0.01 為 2 人團隊設計，知識沉澱以「文檔+Git 歷史」為主，不需要正式會議。

---

## 🎯 成功標準

- [ ] 所有業務功能 100% 對等
- [ ] 資料遷移 100% 完整準確
- [ ] 測試覆蓋率 ≥80%
- [ ] 效能無退化（或有改善）
- [ ] 並行運行期間零資料不一致
- [ ] 成功切換且舊系統安全退役

---

## 📊 時間分配參考

| 階段 | 規劃時間 | 執行時間（中規模） |
|------|---------|----------------|
| 現況分析與需求提取 | 1-2 小時 | - |
| 遷移架構設計 | 1-1.5 小時 | - |
| 資料庫遷移 | 0.5-1 小時 | 2-4 週 |
| 後端遷移 | 30-40 分鐘 | 4-6 週 |
| 前端遷移 | 30-40 分鐘 | 6-8 週 |
| 新平台開發 | 20-30 分鐘 | 4-6 週 |
| 驗證與測試 | 30-40 分鐘 | 2-3 週 |
| 部署與切換 | 20-30 分鐘 | 1-2 週 |
| 知識沉澱 | 20 分鐘 | 2-3 天 |
| **規劃總計** | **4-8 小時** | |
| **執行總計** | | **8-20 週** |

---

## 📖 深度技術參考

> **技術棧遷移深度指南**：完整的資料型別映射、SQL 語法轉換、SP 遷移細節、
> 前端框架映射等技術細節，請參閱 [Refactoring SOP_DeepDive Part 11](../refactoring/SOP_DeepDive.md)。
> Part 11 同時適用於 Migration SOP（全棧遷移）和 Refactoring SOP（部分替換）。

---

## 📚 參考資源

### 相關文檔
- [Migration QuickRef](./SOP_QuickRef.md)
- [Migration 快速啟動指令集](../../prompts/scenario-prompts/migration-prompts.md)
- [Refactoring DeepDive Part 11 - 技術棧遷移深度指南](../refactoring/SOP_DeepDive.md)
- [AISDLC_INIT.md](../../AISDLC_INIT.md)

### 相關 Skills
- `/database-migration` - 資料庫遷移
- `/mobile-development` - 行動端開發
- `/integration-database` - DB 整合方案
- `/integration-api-client` - API 契約設計
- `/performance-optimization` - 效能基準對比
- `/security-audit` - 安全審計
- `/compliance-audit` - 合規審查（電商/支付/個資）
- `/code-review` - 遷移代碼審查
- `/sprint-planning` - 迭代規劃

### 文檔範本
- [Migration_Mapping_Report_Template.md](../../docs_template/scenario_specific/migration/Migration_Mapping_Report_Template.md)
- [DB_Migration_Plan_Template.md](../../docs_template/scenario_specific/migration/DB_Migration_Plan_Template.md)
- [Migration_Verification_Report_Template.md](../../docs_template/scenario_specific/migration/Migration_Verification_Report_Template.md)

---

**文檔版本: v0.01
**最後更新**: 2026-03-26
**基於**: AISDLC-SDD v0.01 Migration 情境模擬測試改善（含 StayShop Pro 全棧遷移模擬）
