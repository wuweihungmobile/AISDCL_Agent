---
name: integration-aws
description: 整合 AWS 服務，包含 S3、SES、SNS、Lambda
user-invocable: true
disable-model-invocation: false
argument-hint: "<service: AWS 服務 (s3/ses/sns/lambda/sqs)> [framework: 框架 (nextjs/express/nestjs)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Integration AWS Skill

整合 AWS 雲端服務。

---

## 觸發方式

```bash
/integration-aws s3              # S3 檔案存儲
/integration-aws ses             # SES 郵件服務
/integration-aws sqs nextjs      # SQS 訊息佇列
```

---

## 執行流程

### 階段 1: AWS 設定確認 🔴

**確認項目**:
- [ ] AWS 帳戶和 Region
- [ ] IAM 權限配置
- [ ] 需要的 AWS 服務
- [ ] 環境變數設定

**環境變數**:
```env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-northeast-1
AWS_S3_BUCKET=my-bucket
```

🔴 **確認點**: 確認 AWS 憑證和權限

---

### 階段 2: S3 檔案存儲

```typescript
// src/lib/aws/s3.ts
import {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
  DeleteObjectCommand,
  ListObjectsV2Command,
} from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

const s3Client = new S3Client({
  region: process.env.AWS_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
  },
});

const BUCKET = process.env.AWS_S3_BUCKET!;

export const s3Service = {
  // 上傳檔案
  async upload(key: string, body: Buffer, contentType: string) {
    await s3Client.send(
      new PutObjectCommand({
        Bucket: BUCKET,
        Key: key,
        Body: body,
        ContentType: contentType,
      })
    );
    return `https://${BUCKET}.s3.${process.env.AWS_REGION}.amazonaws.com/${key}`;
  },

  // 取得預簽名上傳 URL
  async getUploadUrl(key: string, contentType: string, expiresIn = 3600) {
    const command = new PutObjectCommand({
      Bucket: BUCKET,
      Key: key,
      ContentType: contentType,
    });
    return getSignedUrl(s3Client, command, { expiresIn });
  },

  // 取得預簽名下載 URL
  async getDownloadUrl(key: string, expiresIn = 3600) {
    const command = new GetObjectCommand({
      Bucket: BUCKET,
      Key: key,
    });
    return getSignedUrl(s3Client, command, { expiresIn });
  },

  // 刪除檔案
  async delete(key: string) {
    await s3Client.send(
      new DeleteObjectCommand({
        Bucket: BUCKET,
        Key: key,
      })
    );
  },

  // 列出檔案
  async list(prefix: string) {
    const result = await s3Client.send(
      new ListObjectsV2Command({
        Bucket: BUCKET,
        Prefix: prefix,
      })
    );
    return result.Contents || [];
  },
};
```

---

### 階段 3: SES 郵件服務

```typescript
// src/lib/aws/ses.ts
import { SESClient, SendEmailCommand, SendTemplatedEmailCommand } from '@aws-sdk/client-ses';

const sesClient = new SESClient({
  region: process.env.AWS_REGION,
});

interface EmailParams {
  to: string | string[];
  subject: string;
  html: string;
  text?: string;
  from?: string;
}

interface TemplateEmailParams {
  to: string | string[];
  template: string;
  templateData: Record<string, string>;
  from?: string;
}

export const sesService = {
  // 發送郵件
  async send({ to, subject, html, text, from }: EmailParams) {
    const toAddresses = Array.isArray(to) ? to : [to];

    await sesClient.send(
      new SendEmailCommand({
        Source: from || process.env.SES_FROM_EMAIL,
        Destination: {
          ToAddresses: toAddresses,
        },
        Message: {
          Subject: { Data: subject },
          Body: {
            Html: { Data: html },
            Text: text ? { Data: text } : undefined,
          },
        },
      })
    );
  },

  // 使用模板發送
  async sendTemplate({ to, template, templateData, from }: TemplateEmailParams) {
    const toAddresses = Array.isArray(to) ? to : [to];

    await sesClient.send(
      new SendTemplatedEmailCommand({
        Source: from || process.env.SES_FROM_EMAIL,
        Destination: {
          ToAddresses: toAddresses,
        },
        Template: template,
        TemplateData: JSON.stringify(templateData),
      })
    );
  },
};
```

---

### 階段 4: SQS 訊息佇列

```typescript
// src/lib/aws/sqs.ts
import {
  SQSClient,
  SendMessageCommand,
  ReceiveMessageCommand,
  DeleteMessageCommand,
} from '@aws-sdk/client-sqs';

const sqsClient = new SQSClient({
  region: process.env.AWS_REGION,
});

interface QueueMessage<T = unknown> {
  type: string;
  data: T;
  timestamp: number;
}

export const sqsService = {
  // 發送訊息
  async send<T>(queueUrl: string, message: QueueMessage<T>) {
    await sqsClient.send(
      new SendMessageCommand({
        QueueUrl: queueUrl,
        MessageBody: JSON.stringify(message),
        MessageAttributes: {
          Type: {
            DataType: 'String',
            StringValue: message.type,
          },
        },
      })
    );
  },

  // 接收訊息
  async receive(queueUrl: string, maxMessages = 10) {
    const result = await sqsClient.send(
      new ReceiveMessageCommand({
        QueueUrl: queueUrl,
        MaxNumberOfMessages: maxMessages,
        WaitTimeSeconds: 20, // Long polling
        MessageAttributeNames: ['All'],
      })
    );
    return result.Messages || [];
  },

  // 刪除訊息
  async delete(queueUrl: string, receiptHandle: string) {
    await sqsClient.send(
      new DeleteMessageCommand({
        QueueUrl: queueUrl,
        ReceiptHandle: receiptHandle,
      })
    );
  },
};

// Worker 範例
export async function processQueue(queueUrl: string) {
  while (true) {
    const messages = await sqsService.receive(queueUrl);

    for (const message of messages) {
      try {
        const body = JSON.parse(message.Body || '{}');
        console.log('Processing:', body);

        // 處理訊息...

        await sqsService.delete(queueUrl, message.ReceiptHandle!);
      } catch (error) {
        console.error('Error processing message:', error);
      }
    }
  }
}
```

---

### 階段 5: SNS 推送通知

```typescript
// src/lib/aws/sns.ts
import { SNSClient, PublishCommand, SubscribeCommand } from '@aws-sdk/client-sns';

const snsClient = new SNSClient({
  region: process.env.AWS_REGION,
});

export const snsService = {
  // 發布訊息
  async publish(topicArn: string, message: string, subject?: string) {
    await snsClient.send(
      new PublishCommand({
        TopicArn: topicArn,
        Message: message,
        Subject: subject,
      })
    );
  },

  // 發布 JSON 訊息
  async publishJson(topicArn: string, message: Record<string, unknown>) {
    await snsClient.send(
      new PublishCommand({
        TopicArn: topicArn,
        Message: JSON.stringify(message),
        MessageStructure: 'json',
      })
    );
  },

  // 訂閱
  async subscribe(topicArn: string, protocol: string, endpoint: string) {
    await snsClient.send(
      new SubscribeCommand({
        TopicArn: topicArn,
        Protocol: protocol,
        Endpoint: endpoint,
      })
    );
  },
};
```

---

### 階段 6: 驗證 🔴

**驗證清單**:
- [ ] S3 上傳/下載正常
- [ ] SES 郵件發送成功
- [ ] SQS 訊息處理正常
- [ ] SNS 推送正常
- [ ] 錯誤處理正確

🔴 **確認點**: 確認 AWS 服務整合正常

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| S3 服務 | `src/lib/aws/s3.ts` |
| SES 服務 | `src/lib/aws/ses.ts` |
| SQS 服務 | `src/lib/aws/sqs.ts` |
| SNS 服務 | `src/lib/aws/sns.ts` |

---

## 相關 Skill

- `/integration-api-client` - API 客戶端
- `/devops-monitoring` - 監控告警

---


## 相關檔案

- SOP 參考: `scenarios/integration/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Integration 情境
