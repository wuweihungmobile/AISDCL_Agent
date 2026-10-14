# frontend（console-web）

Next.js 16（App Router）／TypeScript 5 strict／Tailwind 4／shadcn/ui 的 Agent Console 前端。視覺以設計稿 water_green 為準（淺色、扁平、無陰影）。
負責人：W3 前端開發者（P1＋P2＋四區塊版面），W4 補匯入／執行／監控／設定頁。決策與偏離清單見 [ADR-002](../docs/02_architecture/ADR-002-Frontend-Design-System.md)。

## 結構

| 位置 | 內容 |
|------|------|
| `app/layout.tsx` | **唯一**組裝處：Top／Tools／Content／Bottom 四區塊；頁面不得 import 或自帶（`components/layout/layout.test.tsx` 機械檢查） |
| `app/**/page.tsx` | 薄薄一層（伺服端靜態殼），內容由 `components/domain/views/*` 的 client 視圖負責；路由照 PRD §4.2 巢狀 |
| `components/{layout,ui,domain,markdown,charts}` | 四區塊／設計系統原子（shadcn 風格、只引用 token）／領域元件與表單／Markdown 編輯與渲染／Tremor Raw 圖表 |
| `lib/api` | `client.ts`（封包、401 換新、traceId）、`endpoints.ts`（端點函式）、`queries.ts`（TanStack Query）、`schema.d.ts`（OpenAPI 型別，入庫） |
| `lib/domain/status.ts` | 專案 6／目標 5／任務 11 個狀態的中文標籤與顏色（單一出處） |
| `styles/` | `tokens.css`（設計 token 逐字）、`tokens.console.css`（延伸 token）、`fonts.css`（字型自託管）、`markdown.css` |
| `tests/e2e` | Playwright（對真後端），說明見 [tests/e2e/README.md](tests/e2e/README.md) |

## 常用指令（工作目錄＝monorepo 根）

```bash
(cd AgentConsole/frontend && npm ci)
(cd AgentConsole/frontend && cp .env.example .env.local && npm run dev)   # http://localhost:3000，後端預設 http://localhost:8080
(cd AgentConsole/frontend && npm run lint && npx tsc --noEmit && npm run build)
(cd AgentConsole/frontend && npx vitest run)                                     # 加 --coverage 看覆蓋率
(cd AgentConsole/frontend && npm run gen:api)                                    # 後端在線時重新產生 lib/api/schema.d.ts
```

```powershell
Push-Location AgentConsole\frontend; npm ci; Pop-Location
Push-Location AgentConsole\frontend; Copy-Item .env.example .env.local; npm run dev; Pop-Location
Push-Location AgentConsole\frontend; npm run lint; npx tsc --noEmit; npm run build; Pop-Location
Push-Location AgentConsole\frontend; npx vitest run; Pop-Location
Push-Location AgentConsole\frontend; npm run gen:api; Pop-Location
```

四區塊唯一性的機械檢查（期望輸出為空；zsh 的 `--include` 要加引號）：

```bash
grep -rnE "TopRegion|ToolsRegion|BottomRegion" AgentConsole/frontend/app --include='*.tsx' | grep -v 'app/layout.tsx'
```

```powershell
Get-ChildItem AgentConsole\frontend\app -Recurse -Filter *.tsx | Where-Object { $_.FullName -notlike '*\app\layout.tsx' } | Select-String -Pattern 'TopRegion|ToolsRegion|BottomRegion'
```

## Docker

```bash
docker build -t aisdlc-frontend:dev --build-arg NEXT_PUBLIC_API_URL= AgentConsole/frontend   # 全棧同源（經 nginx）留空
docker run --rm -p 3000:3000 aisdlc-frontend:dev                                              # curl http://localhost:3000/api/health
```

```powershell
docker build -t aisdlc-frontend:dev --build-arg NEXT_PUBLIC_API_URL= AgentConsole\frontend
docker run --rm -p 3000:3000 aisdlc-frontend:dev
```

## 環境變數

| 變數 | 說明 |
|------|------|
| `NEXT_PUBLIC_API_URL` | 後端 origin（不含 `/api/v1`）；全棧同源為空。**建置時內嵌**，改值要重新 build（Docker 用 build-arg） |

## 設計系統落地重點

- 色彩／間距／圓角／字級一律引用 `styles/tokens.css` 的 CSS 變數（Tailwind 以 `wg-*` 別名使用，例如 `bg-wg-primary`）；元件內不寫死色碼。
- 只有淺色；沒有 box-shadow；hover 只改顏色或透明度；圖示只用 Lucide（stroke 1.5）；鍵盤焦點環 2px 主色。
- 開發 `NEXT_PUBLIC_API_URL`、帳號與 CORS 的後端設定見 [backend/README.md](../backend/README.md)。
