---
name: integration-api
description: 建立通用 API 客戶端，包含錯誤處理、重試機制、型別安全，支援 TypeScript/Python/Java
user-invocable: true
disable-model-invocation: false
argument-hint: "[api_type: API 類型 (rest/graphql)] [framework: 框架 (axios/fetch/ky/httpx/requests/webclient/resttemplate)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Integration API Client Skill

建立企業級 API 客戶端架構。

---

## 觸發方式

```bash
/integration-api-client              # 預設 REST + Axios
/integration-api-client graphql      # GraphQL 客戶端
/integration-api-client --framework=ky
```

---

## 執行流程

### 階段 1: 需求確認 🔴

**確認項目**:
- [ ] API 類型 (REST/GraphQL)
- [ ] 認證方式 (JWT/API Key/OAuth)
- [ ] 錯誤處理策略
- [ ] 重試機制需求
- [ ] 快取策略

🔴 **確認點**: 確認 API 客戶端需求

---

### 階段 2: 基礎架構

```typescript
// src/lib/api/client.ts
import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';

interface ApiClientConfig {
  baseURL: string;
  timeout?: number;
  headers?: Record<string, string>;
}

interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

export class ApiClient {
  private client: AxiosInstance;
  private retryCount = 3;
  private retryDelay = 1000;

  constructor(config: ApiClientConfig) {
    this.client = axios.create({
      baseURL: config.baseURL,
      timeout: config.timeout ?? 30000,
      headers: {
        'Content-Type': 'application/json',
        ...config.headers,
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        return this.handleError(error);
      }
    );
  }

  private getToken(): string | null {
    // 從 localStorage 或其他來源取得 token
    return typeof window !== 'undefined'
      ? localStorage.getItem('auth_token')
      : null;
  }

  private async handleError(error: AxiosError): Promise<never> {
    const apiError: ApiError = {
      code: 'UNKNOWN_ERROR',
      message: 'An unexpected error occurred',
    };

    if (error.response) {
      const { status, data } = error.response;

      switch (status) {
        case 401:
          apiError.code = 'UNAUTHORIZED';
          apiError.message = 'Authentication required';
          // 可以在這裡處理 token 刷新
          break;
        case 403:
          apiError.code = 'FORBIDDEN';
          apiError.message = 'Access denied';
          break;
        case 404:
          apiError.code = 'NOT_FOUND';
          apiError.message = 'Resource not found';
          break;
        case 422:
          apiError.code = 'VALIDATION_ERROR';
          apiError.message = 'Validation failed';
          apiError.details = data;
          break;
        case 429:
          apiError.code = 'RATE_LIMITED';
          apiError.message = 'Too many requests';
          break;
        case 500:
          apiError.code = 'SERVER_ERROR';
          apiError.message = 'Internal server error';
          break;
      }
    } else if (error.request) {
      apiError.code = 'NETWORK_ERROR';
      apiError.message = 'Network error occurred';
    }

    throw apiError;
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.client.get<T>(url, config);
    return { data: response.data, status: response.status };
  }

  async post<T, D = unknown>(url: string, data?: D, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.client.post<T>(url, data, config);
    return { data: response.data, status: response.status };
  }

  async put<T, D = unknown>(url: string, data?: D, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.client.put<T>(url, data, config);
    return { data: response.data, status: response.status };
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.client.delete<T>(url, config);
    return { data: response.data, status: response.status };
  }
}

// 單例導出
export const apiClient = new ApiClient({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001/api',
});
```

---

### 階段 3: 重試機制

```typescript
// src/lib/api/retry.ts
interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  retryCondition?: (error: unknown) => boolean;
}

const defaultRetryConfig: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  retryCondition: (error: unknown) => {
    if (error && typeof error === 'object' && 'code' in error) {
      const code = (error as { code: string }).code;
      return ['NETWORK_ERROR', 'RATE_LIMITED', 'SERVER_ERROR'].includes(code);
    }
    return false;
  },
};

export async function withRetry<T>(
  fn: () => Promise<T>,
  config: Partial<RetryConfig> = {}
): Promise<T> {
  const { maxRetries, baseDelay, maxDelay, retryCondition } = {
    ...defaultRetryConfig,
    ...config,
  };

  let lastError: unknown;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (attempt === maxRetries || !retryCondition?.(error)) {
        throw error;
      }

      // Exponential backoff with jitter
      const delay = Math.min(
        baseDelay * Math.pow(2, attempt) + Math.random() * 1000,
        maxDelay
      );

      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}
```

---

### 階段 4: 型別安全的 API 服務

```typescript
// src/api/users.ts
import { apiClient } from '@/lib/api/client';
import { withRetry } from '@/lib/api/retry';

// 型別定義
export interface User {
  id: string;
  email: string;
  name: string;
  createdAt: string;
}

export interface CreateUserDto {
  email: string;
  name: string;
  password: string;
}

export interface UpdateUserDto {
  name?: string;
  email?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

// API 服務
export const usersApi = {
  async getAll(params?: { page?: number; limit?: number }) {
    return withRetry(() =>
      apiClient.get<PaginatedResponse<User>>('/users', { params })
    );
  },

  async getById(id: string) {
    return withRetry(() => apiClient.get<User>(`/users/${id}`));
  },

  async create(data: CreateUserDto) {
    return apiClient.post<User>('/users', data);
  },

  async update(id: string, data: UpdateUserDto) {
    return apiClient.put<User>(`/users/${id}`, data);
  },

  async delete(id: string) {
    return apiClient.delete<void>(`/users/${id}`);
  },
};
```

---

### 階段 5: React Query 整合

```typescript
// src/hooks/useUsers.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { usersApi, CreateUserDto, UpdateUserDto } from '@/api/users';

export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (params: { page?: number }) => [...userKeys.lists(), params] as const,
  details: () => [...userKeys.all, 'detail'] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
};

export function useUsers(params?: { page?: number; limit?: number }) {
  return useQuery({
    queryKey: userKeys.list(params ?? {}),
    queryFn: () => usersApi.getAll(params),
  });
}

export function useUser(id: string) {
  return useQuery({
    queryKey: userKeys.detail(id),
    queryFn: () => usersApi.getById(id),
    enabled: !!id,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateUserDto) => usersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateUserDto }) =>
      usersApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: userKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: userKeys.lists() });
    },
  });
}
```

---

### 階段 5B: Python API 客戶端 (httpx/requests)

> 當 framework 為 `httpx` 或 `requests` 時使用

```python
# src/api/client.py
import httpx
from typing import TypeVar, Generic, Optional, Any
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class ApiResponse(Generic[T]):
    data: T
    status: int
    message: Optional[str] = None

class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 0, details: Any = None):
        self.code = code
        self.message = message
        self.status = status
        self.details = details
        super().__init__(message)

class ApiClient:
    def __init__(self, base_url: str, timeout: float = 30.0, api_key: Optional[str] = None):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
            },
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
    )
    async def get(self, url: str, params: Optional[dict] = None) -> ApiResponse:
        response = await self.client.get(url, params=params)
        return self._handle_response(response)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
    )
    async def post(self, url: str, data: Optional[dict] = None) -> ApiResponse:
        response = await self.client.post(url, json=data)
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> ApiResponse:
        if response.status_code >= 400:
            error_map = {
                401: ("UNAUTHORIZED", "Authentication required"),
                403: ("FORBIDDEN", "Access denied"),
                404: ("NOT_FOUND", "Resource not found"),
                429: ("RATE_LIMITED", "Too many requests"),
            }
            code, msg = error_map.get(response.status_code, ("SERVER_ERROR", "Server error"))
            raise ApiError(code=code, message=msg, status=response.status_code, details=response.json())
        return ApiResponse(data=response.json(), status=response.status_code)

    async def close(self):
        await self.client.aclose()
```

---

### 階段 5C: Java/Spring Boot API 客戶端 (WebClient)

> 當 framework 為 `webclient` 或 `resttemplate` 時使用

```java
// src/main/java/com/example/integration/ApiClient.java
@Component
public class ApiClient {

    private final WebClient webClient;

    public ApiClient(
            @Value("${integration.api.base-url}") String baseUrl,
            @Value("${integration.api.timeout:30}") int timeoutSeconds) {
        this.webClient = WebClient.builder()
                .baseUrl(baseUrl)
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .filter(retryFilter())
                .build();
    }

    private ExchangeFilterFunction retryFilter() {
        return (request, next) -> next.exchange(request)
                .retryWhen(Retry.backoff(3, Duration.ofSeconds(1))
                        .filter(ex -> ex instanceof WebClientResponseException.ServiceUnavailable
                                || ex instanceof ConnectException));
    }

    public <T> Mono<T> get(String uri, Class<T> responseType) {
        return webClient.get()
                .uri(uri)
                .retrieve()
                .onStatus(HttpStatusCode::is4xxClientError, this::handleClientError)
                .onStatus(HttpStatusCode::is5xxServerError, this::handleServerError)
                .bodyToMono(responseType);
    }

    public <T, R> Mono<T> post(String uri, R body, Class<T> responseType) {
        return webClient.post()
                .uri(uri)
                .bodyValue(body)
                .retrieve()
                .onStatus(HttpStatusCode::is4xxClientError, this::handleClientError)
                .onStatus(HttpStatusCode::is5xxServerError, this::handleServerError)
                .bodyToMono(responseType);
    }

    private Mono<? extends Throwable> handleClientError(ClientResponse response) {
        return response.bodyToMono(String.class)
                .map(body -> new ApiException("CLIENT_ERROR", body, response.statusCode().value()));
    }

    private Mono<? extends Throwable> handleServerError(ClientResponse response) {
        return Mono.error(new ApiException("SERVER_ERROR", "Internal server error", response.statusCode().value()));
    }
}
```

```java
// src/main/java/com/example/integration/ApiException.java
public class ApiException extends RuntimeException {
    private final String code;
    private final int status;

    public ApiException(String code, String message, int status) {
        super(message);
        this.code = code;
        this.status = status;
    }

    public String getCode() { return code; }
    public int getStatus() { return status; }
}
```

---

### 階段 6: 驗證 🔴

**驗證清單**:
- [ ] API 請求正常發送
- [ ] 錯誤處理正確
- [ ] 重試機制運作
- [ ] 型別安全性

🔴 **確認點**: 確認 API 客戶端運作正常

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| API Client | `src/lib/api/client.ts` |
| 重試機制 | `src/lib/api/retry.ts` |
| API 服務 | `src/api/*.ts` |
| React Hooks | `src/hooks/use*.ts` |

---

## 相關 Skill

- `/integration-oauth` - 認證整合
- `/integration-webhook` - Webhook 處理

---


## 相關檔案

- SOP 參考: `scenarios/integration/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Integration 情境
