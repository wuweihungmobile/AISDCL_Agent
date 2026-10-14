# ADR-002：前端設計系統落地、四區塊版面與圖表 spike（Frontend Design System）

| 項目 | 內容 |
|------|------|
| 狀態 | **ACCEPTED v1.0**（W3-A 前端首波；變更須新增 ADR-00N 並引用本檔） |
| 建立日期 | 2026-10-15 |
| 決策者 | 掌舵者（主控）拍板設計系統與路由、四區塊版面；W3-A 前端開發者落地並記錄實測結果 |
| 適用範圍 | `AgentConsole/frontend/`（console-web） |
| 上位文件 | [ADR-001](ADR-001-TechStack-Lock.md)（D2、D3、D11）、設計稿 `docs/01_requirements/01.UI_Design/Design_ConsoleUI/README.md`、PRD §4.2／§5.1／§8、[Architecture.md](Architecture.md) §5 |
| 相關文件 | [RTM.md](../06_quality/RTM.md)（UI-／US-P／US-G／US-T 列）、[frontend/README.md](../../frontend/README.md)、[tests/e2e/README.md](../../frontend/tests/e2e/README.md) |

---

## 1. Context

ADR-001 D11 已拍板「視覺以設計稿為準」，D3 要求圖表 spike 並把結果寫進本檔。W3-A 要在零前端程式碼的狀態下做出：骨架、設計系統、**四區塊共用版面**、登入、Dashboard（部分）、專案／目標／任務三層頁面與對話框、Markdown 編輯器；匯入／執行／監控／設定四頁只放路由殼。本檔記錄落地時做的決定、實測結果與偏離。

## 2. 決策總表

| 編號 | 決定 | 偏離？ |
|------|------|--------|
| D1 | 設計系統採 water_green：token 逐字入庫，Tailwind 以 `wg-*` 別名使用；只有淺色、無陰影、Lucide stroke 1.5、2px 焦點環 | 偏離 PRD §8.2（沿 ADR-001 D11） |
| D2 | shadcn/ui 用法：CLI 4.21.5（radix-nova，Radix 基底）產生後**重寫為設計系統版**；toast 自行實作 | 補充 |
| D3 | 路由照 PRD §4.2 巢狀；`app/layout.tsx` 是四區塊唯一組裝處，頁面一律薄薄一層 | 與設計稿 README 建議的扁平路由不同（掌舵者已拍板） |
| D4 | 資料存取全 client-side（TanStack Query）；`lib/api/client.ts` 單一 fetch 包裝；token 存 sessionStorage | 無 |
| D5 | Next 16.4：`output: standalone`；**關閉** `cacheComponents`／`partialPrefetching`（create-next-app 預設為開） | 偏離 create-next-app 預設 |
| D6 | 圖表：Tremor Raw AreaChart **spike 成功**，採用；須 `overrides.react-is`＝19.3.0 | 偏離 PRD §3.1 的 Tremor 3.x 套件，改 Tremor Raw 原始碼（沿 ADR-001 D3） |
| D7 | Markdown：`@uiw/react-md-editor`（編輯）＋ react-markdown／remark-gfm／rehype-highlight（渲染） | 無 |
| D8 | 型別由後端 `/v3/api-docs` 經 `openapi-typescript` 產生並入庫；端點函式一一對應 PRD §7.1 | 無 |
| D9 | 字型自託管（`@fontsource-variable/*`），不依賴 Google Fonts CDN | 偏離設計稿 `tokens/fonts.css` 的 CDN `@import`（設計稿 README〈Assets〉明載上線請自託管） |
| D10 | Dockerfile 照 PRD §11.4.1，僅兩處必要修正（`npm ci`、HEALTHCHECK 用 wget） | 偏離 PRD 逐字版 |

## 3. 逐項決策

### D1　設計系統落地

- **token 逐字**：`styles/tokens.css` ＝ 設計稿 `_ds/…/tokens/` 的 colors→typography→spacing→radius→base 五檔逐字串接（以程式比對每個來源檔都是該檔的子字串）；不含 `fonts.css`。設計稿 README 列出但 `_ds` 沒定義的固定色（終端機面板 `#1c241a`／`#d7e4cd`、草案警示 `#fdeee9`／`#f3c7bb`、告警 `#fef7ea`／`#f5e2bd`、連線點 `#9fe08a`、捲軸、遮罩）放 `styles/tokens.console.css`，不污染逐字檔。
- **進 `@layer base`**：`@import "../styles/tokens.css" layer(base)`。設計稿 `base.css` 有 `h1…h6 { font-size }`、`body` 等元素規則；若不分層，unlayered 規則會壓過所有 Tailwind utilities（`text-[30px]` 失效）。
- **Tailwind 別名 `wg-*`**（`@theme inline`）：`bg-wg-primary`、`text-wg-muted`、`border-wg-line`…直接內嵌 `var(--color-…)`。刻意加前綴：shadcn 的 `accent`／`muted` 概念與設計系統的 `--color-accent`（警示橘紅）**不同義**，同名會讓人誤用；Console 自己的元件只用 `wg-*`，shadcn 語意名（`--primary`、`--border`…）只留給 shadcn 原生元件並在 `:root` 別名到設計 token。
- **只有淺色**：沒有 `.dark` 區塊；`@custom-variant dark (&:is(.dark *))` 讓任何殘留的 `dark:` 永遠不觸發（預設會吃 `prefers-color-scheme`）。移植 Tremor Raw 時把所有 `dark:` 類別剝掉。
- **扁平**：元件無 `shadow-*`；hover 只改顏色／透明度；無 translate／縮放。Dialog 只用設計稿的 `wg-fade`（入場位移）。
- **焦點環**：沿用 `base.css` 的 `:focus-visible { outline: 2px solid primary; offset 2px }`，元件不寫 `outline-none`；input／select 另有 `focus:border-wg-primary`。
- **Lucide**：`lucide-react` 1.57.0；`svg.lucide { stroke-width: 1.5 }`（CSS 屬性蓋過元件預設的 2）。設計稿的 emoji 一律不用。
- **狀態 enum**：`lib/domain/status.ts` 單一出處；顏色寫成 `var(--color-…)`，`status.test.ts` 解析 `tokens.css` 後逐項核對成設計稿色碼。
- **尺寸取自設計系統元件原始碼**（`_ds_bundle.js`）：Button sm／md／lg＝padding 6/16、8/20、12/28，圖示 16／18／20px；hint-size 欄位只是設計工具的占位，不採用。

### D2　shadcn/ui 的實際用法

- `npx shadcn@latest init -t next -b radix -p nova`（4.21.5；新版 CLI 需指定 base 與 preset，`-d` 預設會落到 Base UI）→ `radix-ui` 1.8.1、`cn` 0.4.0（shadcn 官方的 clsx＋tailwind-merge 替代，維護者為 shadcn）。
- 產出的 nova 元件視覺（`ring-3`、`rounded-lg`、`dark:` 類別…）與設計系統不合，**已逐一重寫**（保留 Radix 原語與 `data-slot`）：Button、IconButton、Card、Input、Textarea、Select（原生 `<select>`，設計稿 `.wg-sel`；不用 Radix Select）、Badge、Progress、Skeleton、Checkbox、Dialog。
- 任務書清單中**未採用**：`tabs`（狀態篩選是 `aria-pressed` 按鈕群，不是分頁）、`table`、`sheet`（<768 是底部 Tab，不是抽屜）、`dropdown-menu`、`tooltip`（用 `title`／`aria-label`）、`select`（見上）。**`toast`**：CLI 回報「僅限 Base UI 基底」，且 sonner 視覺與設計稿不同 ⇒ 自行實作（`components/ui/toast.tsx`：底部置中深底、一次一則、aria-live），宿主在 BottomRegion。

### D3　路由與四區塊版面

- 路由樹照 PRD §4.2／Architecture §5.1：含 `new`／`edit`／`goals`／`tasks` 列表路由；`new`／`edit` 與 Dialog 共用同一個 `EntityEditor`。
- **唯一組裝處**：`app/layout.tsx` 只組裝 `TopRegion`／`ToolsRegion`／`ContentRegion`／`BottomRegion`（外加 Providers 與跳到主要內容連結）；頁面檔不得提到四個名稱。機械檢查三層：grep 閘門、`layout.test.tsx` 的靜態掃描（含 components／hooks／lib 不得 import 區塊）、渲染測試（每個 `data-region` 恰好一份）。突變實驗：在 `app/import/page.tsx` 加入 `TopRegion` 的 import，唯一性測試轉紅並點名該檔；還原後轉綠。
- 容器：本體 `max-w-[var(--container-max)]`（token 1440）、內距 24、左右欄 gap 32，**外框在 layout、捲動在 ContentRegion**（右欄獨立捲動，整體 100vh 不捲）。
- **登入頁在同一個 layout 內**：區塊依登入狀態自我調整（`/login` 只顯示品牌列、無側欄／搜尋／動作），而不是另開第二個 layout——否則就有兩處組裝。
- 響應式（PRD §8.3）都在區塊內以 Tailwind 斷點切換：≥1280 側欄 240px；768～1279 側欄 64px 只留圖示（`aria-label`／`title` 保留）；<768 `flex-col-reverse` 把 Tools 排到內容下方成為底部 Tab。（踩坑：同時加 `order-last` 會與 `column-reverse` 互相抵銷，E2E 以 bounding box 抓到。）
- 「執行中心／監控中心」需要 projectId：網址中的專案 → 最近造訪（sessionStorage，以 `useSyncExternalStore` 避免水合不一致）→ 專案列表第一筆 → 都沒有退回 `/projects`。
- Bridge 連線狀態：目前沒有任何對瀏覽器開放的來源（後端 health 為 `show-details: never`），誠實顯示「Engine Bridge · 待接線」，不假裝已連線；接線只需改 `hooks/useServiceStatus.ts`。console-api 狀態沿用專案列表輪詢（30 秒）的結果。

### D4　資料存取

- `lib/api/client.ts`：Bearer；401 → 以 refresh token 換新（同時多個 401 只換一次）→ 重送一次；換不到清 session 並導向 `/login?next=`（`next` 只接受站內路徑）；解 PRD §7.2 封包；錯誤一律 `ApiError`（`errors[]`、`reason`、`details`、`traceId`，traceId 缺席時退回 `X-Trace-Id` 標頭）；登入／換新端點用 `auth:false` 不遞迴。
- TanStack Query：任何寫入成功就把 projects／goals／tasks 三層快取全標過期（計數互相牽動，資料量小，換「不顯示過期計數」）；4xx 不重試。
- token 存 `sessionStorage`（關分頁即失效，ADR-001 D4）；auth store 提供引用穩定的快照給 `useSyncExternalStore`，AuthProvider 沒有任何 effect 內 setState。
- **待人工審批佇列**（頂列徽章與 Dashboard 共用）：`signedOff=false` 的專案，加上這些草案專案底下 `signedOff=false` 的目標。**已知限制**：已簽核專案底下以 `draft:true` 建立的目標／任務不在佇列；後端 `GET /notifications/summary` 落地後可改吃計數端點。
- 後端 400 的 `errors[]` 對應到欄位（`applyServerErrors`）；依賴成環把 UUID 換成目標名稱顯示；任務驗證命令的禁用字元前端先擋（NFR-SEC-03，後端仍二次校驗）。

### D5　Next 16.4 設定

- `create-next-app` 16.4.0 的預設會開 `cacheComponents: true`／`partialPrefetching: true`（官方文件：下個主版本會全面啟用並移除選項）。本專案**關閉**：資料全在 client（TanStack Query），沒有伺服端資料可快取；開啟後所有讀 `params`／`searchParams` 的路由都要包 Suspense、且禁用 route segment config，成本無對應收益。**重新評估條件**：改成伺服端取資料，或 Next 移除該選項時。
- `output: "standalone"`＋`outputFileTracingRoot: process.cwd()`：monorepo 內建置時產物仍是 `.next/standalone/server.js`。`scripts/start-standalone.mjs` 跨平台補複製 `.next/static` 與 `public` 後啟動。
- Tailwind 4.3.3 以 `@tailwindcss/turbopack`（16.4 範本預設）整合；`TopRegion` 等區塊需讀 `useSearchParams` 的頁面（`/login`、`/projects`）在頁面層包 Suspense。
- `AGENTS.md`（create-next-app 16.4 產物，`next dev` 會自動重建）保留原樣，不納入本專案文件體系。

### D6　圖表 spike 結果（回填 ADR-001 §6 E-3）

| 項目 | 結果 |
|------|------|
| 方案 | **Tremor Raw**（`tremorlabs/tremor` main 的 `src/components/AreaChart`＋`utils`，copy-paste 元件）＋ recharts 2.15.4 |
| 結論 | **成功（採用）**；耗時約 5 分鐘（限時 30 分鐘） |
| 驗證 | `npm run build` 綠；Playwright 實測面積線 `stroke` 解析為 `rgb(73, 132, 40)`（＝`--color-primary`）、Y 軸有刻度、附 `role="img"` 文字替代說明（`tests/e2e/chart.spec.ts`） |
| 版本 | Tailwind 4.3.3／React 19.3.0／Next 16.4.0／recharts 2.15.4；Tremor Raw 倉庫自身即為 Tailwind ^4.1.3 |
| 本專案對 Tremor Raw 的改動 | `chartColors.ts` 色票改設計 token（`wg-*`）、`cx` 改沿用 `cn`、remixicon→lucide、剝除 `dark:`、灰階改 token、tooltip 的 `shadow-md` 移除（設計系統無陰影，由 `tests/design-rules.test.ts` 守住）；元件邏輯未改（僅在該檔停用上游 ScrollButton 觸犯的 `react-hooks/set-state-in-effect` 一條 lint 規則）；使用時 `fill="solid"`（設計系統禁用漸層） |
| 🔴 陷阱 | recharts 2.x 依賴 react-is 18，與 React 19 並用時 **Area／YAxis 靜默不渲染**（沒有任何錯誤，只畫出格線與 X 軸）。以 `package.json` 的 `overrides: { "react-is": "19.3.0" }` 修正；`lib/deps.test.ts` 守住（突變實驗：移除 overrides 後該測試報 `expected '18' to be '19'`，還原後轉綠） |
| 沒採用 shadcn chart | spike 成功，不需備援；若日後 recharts 3 與 Tremor Raw 相容，可拿掉 overrides 並升級 |

### D7　Markdown 編輯器（PRD §5.1.4 八項）

`@uiw/react-md-editor` 4.1.2（`preview="live"`）＋渲染端 `react-markdown` 10.1.0／`remark-gfm` 4.0.1／`rehype-highlight` 7.0.2。編輯器以 `next/dynamic`（ssr:false）載入。八項逐項對應與測試（`components/markdown/markdown.test.tsx`）：

| RTM | 功能 | 實作 |
|-----|------|------|
| UI-MD-01 | 即時預覽（Split View） | `preview="live"`，輸入後預覽即時渲染 |
| UI-MD-02 | 語法高亮 | 編輯區 Markdown 原始碼著色（`.token.title`／`.token.bold`） |
| UI-MD-03 | 工具列 | 預設工具列（粗體、斜體、標題、清單、表格、程式碼區塊、核取清單…）；點粗體會插入語法 |
| UI-MD-04 | GFM 表格 | 預覽與 `MarkdownView` 皆渲染 `<table>` |
| UI-MD-05 | 程式碼區塊＋語言高亮 | `language-ts` 的 `.hljs-keyword`；token 色引用設計 token |
| UI-MD-06 | Checklist | `- [ ]`／`- [x]` → 18px 唯讀方塊，`aria-checked` 正確 |
| UI-MD-07 | 匯入 .md | 檔案選擇（.md／.markdown／.txt、≤1 MB）→ 覆蓋欄位內容 |
| UI-MD-08 | 匯出 .md | Blob 下載，檔名經 `safeFileName` 消毒 |

Dialog 為 560px，Split View 只有約 250px 一欄；工具列右側有全螢幕鈕可放大，整頁 new／edit 路由則有完整寬度。

### D8　型別與端點

`node scripts/gen-api.mjs [位址]`（`npm run gen:api`）→ `lib/api/schema.d.ts`（入庫，建置不依賴後端）。`lib/api/endpoints.ts` 的 22 個函式與 PRD §7.1 一一對應，`endpoints.test.ts` 釘住「函式集合恰為這 22 個」與每個的方法／路徑／body。

### D9　字型

`@fontsource-variable/inter`／`noto-sans-tc`／`jetbrains-mono`（`.next/static/media` 實測 4.6 MB、122 個檔，含各 unicode-range 分片；瀏覽器只下載用到的分片）。`styles/fonts.css` 覆寫 `--font-sans`／`--font-base` 並新增 `--font-mono`（fontsource 的家族名帶 `Variable` 後綴）。

### D10　Dockerfile（回填 INF-DKR-01）

照 PRD §11.4.1 三階段；兩處必要修正：(1) `npm ci --frozen-lockfile` → `npm ci`（前者是 yarn 旗標，npm ci 本來就嚴格依 lockfile）；(2) HEALTHCHECK 由 `curl` 改 busybox `wget`、位址 127.0.0.1（`node:22-alpine` 沒有 curl，PRD 版會永遠 unhealthy；`localhost` 在 alpine 可能先解析成 `::1`）。另加 `.dockerignore`（沒有它 `COPY . .` 會把本機 `node_modules` 蓋掉 deps 階段在 Linux 上裝好的）。實測見 §5。

## 4. 與設計稿的已知差異

| # | 差異 | 原因 |
|---|------|------|
| 1 | 登入頁、底部狀態列、公告列的「登出」、搜尋條件 chip、目標拖曳把手、日誌搜尋框 | 設計稿沒有；功能必要（任務書／PRD 要求），風格依 token |
| 2 | Dashboard KPI 改為 活躍專案數／待審批草案數／本週完成任務數（—）／執行中 run 數（—）；多一張「專案狀態分佈」圖卡 | 任務書指定（後兩張待 Phase 5 監控 API） |
| 3 | 專案列表排序第三項「任務數」→「最近建立」 | 後端 sort 欄位白名單只有 name／status／createdAt／updatedAt |
| 4 | 專案／目標／任務詳情底部多「刪除」；任務詳情沒有 PRD wireframe 的「暫停／取消」 | 任務書要求刪除確認；暫停／取消屬 Phase 4 執行控制，設計稿底部也只有 重試／編輯 |
| 5 | 建立／編輯 Dialog 的說明與通過標準用 Markdown 編輯器（設計稿為 textarea）；目標多「前置依賴」多選、任務多 evaluator 欄位 | PRD §5.1.4／任務書 |
| 6 | 「Engine Bridge · 待接線」而非「已連線」 | 設計稿的連線狀態是寫死的 mock；沒有真實來源前不假裝 |
| 7 | 響應式三形態；設計稿只有桌面 | PRD §8.3 |
| 8 | 字型自託管 | 設計稿 README〈Assets〉 |
| 9 | 公告列高 34px（取設計稿 README；`--topbar-height` token 為 32px） | 設計稿兩處數值不一致，取像素級定稿的 34 |

## 5. 驗證證據

| 編號 | 項目 | 指令／方法 | 逐字輸出（W3-A 實測，2026-10-15） |
|------|------|-----------|----------------------------------|
| E-2 | Next.js／Tailwind 實際版本 | `npm view next dist-tags --json`；`npm ls --depth=0` | `"latest": "16.4.0"`；`next@16.4.0`、`react@19.3.0`、`tailwindcss@4.3.3`、`@tailwindcss/turbopack@4.3.3`、`typescript@5.9.3` |
| E-3 | 圖表 spike | 見 §3 D6 | 成功（Tremor Raw AreaChart＋recharts 2.15.4）；react-is 需 override |
| E-6 | 前端映像 | `docker build -t aisdlc-frontend:dev .`、`docker run`、`docker inspect` | build rc=0；容器 uid 1001；`GET /api/health` → `{"status":"ok"}`；`Health.Status`＝`healthy` |

lint／tsc／build／vitest／Playwright 的逐字輸出見 W3-A 交卷與 `docs/04_planning/Implementation_Plan.md` §5.1 的 W3-A 列。

## 6. 後果與風險

- 設計系統只有一個真相源（`styles/tokens.css`）；換主題＝換 token 檔，元件不動。
- `wg-*` 別名多一層命名，換來「不會把 shadcn 的 accent 當成警示橘紅」。
- 關閉 Cache Components 是刻意的相容性選擇；Next 日後移除選項時須重新評估（見 D5）。
- Tremor Raw 是複製進 repo 的原始碼（Apache-2.0），升級要手動比對上游。
- **Windows 尚未驗證的點**見 W3-A 交卷〈Windows 接續注意〉：`npm ci`、`next dev`／`build`、Playwright 瀏覽器安裝與整套 E2E、`scripts/start-standalone.mjs`、Docker build。
