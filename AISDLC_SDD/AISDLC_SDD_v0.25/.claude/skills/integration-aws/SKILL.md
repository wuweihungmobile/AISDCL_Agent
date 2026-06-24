---
name: integration-aws
description: AWS 服務整合，ADR 記錄服務選型，IAM Policy Spec 定義最小權限，RTM 追蹤雲端 TC
user-invocable: true
disable-model-invocation: false
argument-hint: "<services: s3|sqs|sns|lambda|rds|all> [environment: dev|staging|production]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Integration AWS Skill（SDD 原生）

AWS 整合在 SDD 中屬於「整合設計先行」範疇：AWS 服務選型需有 ADR，IAM Policy 必須在實作前以 Policy Spec 形式凍結（最小權限原則），基礎設施配置需對應 SRD 架構章節。

---

## 觸發方式

```bash
/integration-aws s3
/integration-aws sqs sns
/integration-aws lambda
/integration-aws all production
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-2 通過 | 雲端架構確定 | `docs/02_architecture/SRD-{System}.md` 雲端架構章節 |
| FRD 雲端需求 | 雲端服務需求已定義 | NFR（可用性 / 儲存 / 訊息佇列）|

---

## 執行流程

### 階段 1：AWS 服務選型 ADR（設計先行）🔴

呼叫 `/adr-generate "AWS 服務架構"`：

```markdown
# ADR-{NNN}: AWS 服務選型

## Decision
使用 {S3 / SQS / Lambda / RDS} 組合

## Rationale（對應 NFR）
| 服務 | 用途 | 對應 NFR |
|------|------|---------|
| S3 | 靜態資源 / 備份儲存 | NFR-STO-001（儲存 SLA） |
| SQS | 非同步訊息佇列 | NFR-MSG-001（訊息可靠性） |
| Lambda | 事件驅動處理 | NFR-P003（Serverless 自動擴展）|

## Security 決策
- IAM 最小權限：每個服務使用獨立 IAM Role
- KMS 加密：S3 Bucket / RDS 使用 KMS 加密
- VPC 隔離：RDS 放置 Private Subnet
```

---

### 階段 2：IAM Policy Spec（最小權限定義）

**文件路徑**：`docs/02_architecture/INTEGRATION-SPEC-AWS-IAM-{System}.md`

```markdown
# IAM Policy Spec — {System}

**原則**: 最小權限（Least Privilege）
**對應 STRIDE**: T-006 Elevation of Privilege

## Service Role 清單

### Role: {System}-AppRole（應用程式服務角色）
| 服務 | Action | Resource | 業務理由 |
|------|--------|----------|---------|
| S3 | s3:GetObject, s3:PutObject | {bucket-name}/* | F-FILE-001 |
| SQS | sqs:SendMessage, sqs:ReceiveMessage | {queue-arn} | F-ORDER-002 |

❌ 禁止：`s3:*`, `iam:*`（違反最小權限）
```

---

### 階段 3：Infrastructure as Code（對應 SRD）

IaC 配置必須對應 SRD 架構，不可新增未在 SRD 記錄的資源：

```hcl
# terraform/modules/s3/main.tf
# 對應 SRD 第 8 章：儲存架構
resource "aws_s3_bucket" "app_storage" {
  bucket = "{system}-{env}-storage"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"   # ADR-NNN 決策
      }
    }
  }

  versioning { enabled = true }    # 對應 NFR-STO-001
}

# IAM Policy（對應 IAM Policy Spec）
resource "aws_iam_role_policy" "app_s3_policy" {
  role = aws_iam_role.app_role.id
  policy = jsonencode({
    Statement = [{
      Action   = ["s3:GetObject", "s3:PutObject"]   # 最小權限
      Effect   = "Allow"
      Resource = "${aws_s3_bucket.app_storage.arn}/*"
    }]
  })
}
```

---

### 階段 4：RTM 更新 🔴

```bash
/rtm-generate update    # 更新雲端整合 TC（TC-AWS-XXX）
/spec-compliance-check docs/02_architecture/INTEGRATION-SPEC-AWS-IAM-{System}.md
```

🔴 確認點：IAM Policy Spec 完整覆蓋所有服務存取；無 `*` 寬鬆權限。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| AWS 服務選型 ADR | `docs/02_architecture/adr/ADR-{NNN}-aws-services.md` | SCG-2 |
| IAM Policy Spec | `docs/02_architecture/INTEGRATION-SPEC-AWS-IAM-{System}.md` | SCG-2 |

---

## 後置動作

```
/security-audit            # 審查 IAM Policy（STRIDE T-006）
/devops-monitoring         # 設定 CloudWatch 指標（對應 NFR）
/sdd-gate SCG-4            # 雲端整合 PR Review
```

🔷 **本 Skill 對應 SCG**：SCG-2（雲端架構凍結）、SCG-4（PR Review）

---

## 相關 Skill

- `/adr-generate` — AWS 服務選型 ADR
- `/security-audit` — IAM 最小權限審查
- `/integration-database` — RDS 資料庫整合

---

**基於**: AISDLC-SDD v0.25
**對應情境**: Integration 場景
