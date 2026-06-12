---
name: integration-openai
description: 整合 OpenAI API，包含 Chat、Embeddings、Function Calling
user-invocable: true
disable-model-invocation: false
argument-hint: "[feature: 功能 (chat/embeddings/assistants/images)] [model: 模型 (gpt-4/gpt-3.5-turbo)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Integration OpenAI Skill

整合 OpenAI API 實現 AI 功能。

---

## 觸發方式

```bash
/integration-openai              # 基本 Chat 整合
/integration-openai embeddings   # 向量嵌入
/integration-openai assistants   # Assistants API
```

---

## 執行流程

### 階段 1: OpenAI 設定 🔴

**確認項目**:
- [ ] OpenAI API Key 已取得
- [ ] 使用的模型和用途
- [ ] 預算和限制
- [ ] 錯誤處理策略

**環境變數**:
```env
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...  # 可選
```

🔴 **確認點**: 確認 OpenAI 配置

---

### 階段 2: OpenAI 客戶端

```typescript
// src/lib/openai/client.ts
import OpenAI from 'openai';

export const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  organization: process.env.OPENAI_ORG_ID,
});

// 預設配置
export const DEFAULT_MODEL = 'gpt-4-turbo-preview';
export const DEFAULT_EMBEDDING_MODEL = 'text-embedding-3-small';
```

---

### 階段 3: Chat Completion 服務

```typescript
// src/lib/openai/chat.ts
import { openai, DEFAULT_MODEL } from './client';
import { ChatCompletionMessageParam } from 'openai/resources/chat';

interface ChatOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  systemPrompt?: string;
}

interface ChatResponse {
  content: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export const chatService = {
  // 單次對話
  async complete(
    prompt: string,
    options: ChatOptions = {}
  ): Promise<ChatResponse> {
    const messages: ChatCompletionMessageParam[] = [];

    if (options.systemPrompt) {
      messages.push({ role: 'system', content: options.systemPrompt });
    }
    messages.push({ role: 'user', content: prompt });

    const response = await openai.chat.completions.create({
      model: options.model || DEFAULT_MODEL,
      messages,
      temperature: options.temperature ?? 0.7,
      max_tokens: options.maxTokens,
    });

    return {
      content: response.choices[0]?.message?.content || '',
      usage: {
        promptTokens: response.usage?.prompt_tokens || 0,
        completionTokens: response.usage?.completion_tokens || 0,
        totalTokens: response.usage?.total_tokens || 0,
      },
    };
  },

  // 多輪對話
  async chat(
    messages: ChatCompletionMessageParam[],
    options: ChatOptions = {}
  ): Promise<ChatResponse> {
    const allMessages = options.systemPrompt
      ? [{ role: 'system' as const, content: options.systemPrompt }, ...messages]
      : messages;

    const response = await openai.chat.completions.create({
      model: options.model || DEFAULT_MODEL,
      messages: allMessages,
      temperature: options.temperature ?? 0.7,
      max_tokens: options.maxTokens,
    });

    return {
      content: response.choices[0]?.message?.content || '',
      usage: {
        promptTokens: response.usage?.prompt_tokens || 0,
        completionTokens: response.usage?.completion_tokens || 0,
        totalTokens: response.usage?.total_tokens || 0,
      },
    };
  },

  // 串流對話
  async *stream(
    messages: ChatCompletionMessageParam[],
    options: ChatOptions = {}
  ): AsyncGenerator<string> {
    const stream = await openai.chat.completions.create({
      model: options.model || DEFAULT_MODEL,
      messages,
      temperature: options.temperature ?? 0.7,
      stream: true,
    });

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content;
      if (content) {
        yield content;
      }
    }
  },
};
```

---

### 階段 4: Function Calling

```typescript
// src/lib/openai/functions.ts
import { openai, DEFAULT_MODEL } from './client';
import { ChatCompletionTool } from 'openai/resources/chat';

// 定義可用函數
const tools: ChatCompletionTool[] = [
  {
    type: 'function',
    function: {
      name: 'get_weather',
      description: '取得指定城市的天氣資訊',
      parameters: {
        type: 'object',
        properties: {
          city: {
            type: 'string',
            description: '城市名稱',
          },
          unit: {
            type: 'string',
            enum: ['celsius', 'fahrenheit'],
            description: '溫度單位',
          },
        },
        required: ['city'],
      },
    },
  },
  {
    type: 'function',
    function: {
      name: 'search_products',
      description: '搜尋產品',
      parameters: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: '搜尋關鍵字',
          },
          category: {
            type: 'string',
            description: '產品分類',
          },
          maxPrice: {
            type: 'number',
            description: '最高價格',
          },
        },
        required: ['query'],
      },
    },
  },
];

// 函數實作
const functionHandlers: Record<string, (args: unknown) => Promise<unknown>> = {
  get_weather: async (args: { city: string; unit?: string }) => {
    // 實際實作會呼叫天氣 API
    return { city: args.city, temperature: 25, condition: 'sunny' };
  },
  search_products: async (args: { query: string; category?: string }) => {
    // 實際實作會查詢資料庫
    return [{ id: '1', name: 'Product 1', price: 100 }];
  },
};

export const functionCallingService = {
  async execute(prompt: string) {
    const messages = [{ role: 'user' as const, content: prompt }];

    const response = await openai.chat.completions.create({
      model: DEFAULT_MODEL,
      messages,
      tools,
      tool_choice: 'auto',
    });

    const message = response.choices[0]?.message;

    // 如果有函數呼叫
    if (message?.tool_calls) {
      const toolResults = await Promise.all(
        message.tool_calls.map(async (toolCall) => {
          const handler = functionHandlers[toolCall.function.name];
          const args = JSON.parse(toolCall.function.arguments);
          const result = await handler(args);

          return {
            tool_call_id: toolCall.id,
            role: 'tool' as const,
            content: JSON.stringify(result),
          };
        })
      );

      // 用函數結果繼續對話
      const finalResponse = await openai.chat.completions.create({
        model: DEFAULT_MODEL,
        messages: [...messages, message, ...toolResults],
      });

      return finalResponse.choices[0]?.message?.content;
    }

    return message?.content;
  },
};
```

---

### 階段 5: Embeddings 服務

```typescript
// src/lib/openai/embeddings.ts
import { openai, DEFAULT_EMBEDDING_MODEL } from './client';

export const embeddingService = {
  // 產生單一向量
  async embed(text: string): Promise<number[]> {
    const response = await openai.embeddings.create({
      model: DEFAULT_EMBEDDING_MODEL,
      input: text,
    });
    return response.data[0].embedding;
  },

  // 批量產生向量
  async embedBatch(texts: string[]): Promise<number[][]> {
    const response = await openai.embeddings.create({
      model: DEFAULT_EMBEDDING_MODEL,
      input: texts,
    });
    return response.data.map((d) => d.embedding);
  },

  // 計算相似度
  cosineSimilarity(a: number[], b: number[]): number {
    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
  },
};
```

---

### 階段 6: API Route 範例

```typescript
// app/api/chat/route.ts
import { NextResponse } from 'next/server';
import { chatService } from '@/lib/openai/chat';

export async function POST(req: Request) {
  try {
    const { messages, systemPrompt } = await req.json();

    const response = await chatService.chat(messages, {
      systemPrompt,
      temperature: 0.7,
    });

    return NextResponse.json(response);
  } catch (error) {
    console.error('Chat error:', error);
    return NextResponse.json(
      { error: 'Failed to process chat' },
      { status: 500 }
    );
  }
}
```

---

### 階段 7: 驗證 🔴

**驗證清單**:
- [ ] Chat Completion 正常
- [ ] 串流回應正常
- [ ] Function Calling 正確
- [ ] Embeddings 產生正常
- [ ] 錯誤處理正確
- [ ] Token 用量合理

🔴 **確認點**: 確認 OpenAI 整合正常

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| OpenAI 客戶端 | `src/lib/openai/client.ts` |
| Chat 服務 | `src/lib/openai/chat.ts` |
| Function Calling | `src/lib/openai/functions.ts` |
| Embeddings 服務 | `src/lib/openai/embeddings.ts` |

---

## 相關 Skill

- `/integration-api-client` - API 客戶端
- `/performance` - 效能優化 (Token 管理)

---


## 相關檔案

- SOP 參考: `scenarios/integration/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Integration 情境
