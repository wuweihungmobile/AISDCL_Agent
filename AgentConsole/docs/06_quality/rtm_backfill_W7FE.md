# RTM 回填：W7-FE（D-13：NFR-9.1-05 Markdown 預覽 20KB 追到 < 100ms）

> 日期 2026-10-16｜依據：`docs/04_planning/agent_briefs/W7_OVERVIEW.md` §3.3（D-13）。
> 本檔**不改 RTM.md**，由 W7-QA 單線合併；路徑相對 `AgentConsole/`；自動測試以 `檔案::describe 區塊`（vitest）表示。儲存格內不含管線字元。
> 結論：**達標**。同一把尺（p9 的 `NFR-9.1-05` 量法）、同一時段修前修後交錯各量 35 次樣本：20KB 預覽更新中位數 **129ms → 58ms**，5KB 24ms → 19ms，1KB 12ms → 9ms。
> 這是 FE 自量（mock 後端、production 建置）；QA 以 p9 同法在自己的環境重量之後才能升 `✅ 已驗證`。

## 一、RTM 列

| ID | 實作檔 | 自動測試 | E2E 驗證 | 建議狀態 |
|----|--------|----------|----------|----------|
| NFR-9.1-05 | frontend/components/markdown/rehypePrismLinear.ts（新增：rehype-prism-plus 的行為等價、線性時間版）、frontend/next.config.ts（`turbopack.resolveAlias` 把裸名稱 `rehype-prism-plus` 指到上檔；左欄原始碼著色與預覽的程式碼區塊兩個匯入者一起生效）、frontend/components/markdown/MarkdownEditorImpl.tsx（`shouldDeferPreview`：批次變更不排程、連續打字才排程；`DEFER_ABOVE_CHARS` 註解換成新實測值）、frontend/package.json 與 package-lock.json（新增直接依賴 parse-numeric-range、refractor；devDependencies 新增 rehype、rehype-prism-plus 釘 2.0.2） | frontend/components/markdown/rehypePrismLinear.test.ts（與上游逐位相等：左欄形態、各語言、邊角內容、選項、meta、diff、錯誤行為、300 份隨機文件；複雜度線性；next.config.ts 別名與匯入者普查；兩個匯入者解析到的版本就是 2.0.2）、frontend/components/markdown/markdown.test.tsx::預覽窗：大文件（超過 DEFER_ABOVE_CHARS 才分開排程）也要正確跟上輸入（新增批次貼入一案）、frontend/components/markdown/markdown.test.tsx::預覽何時排到輸入之後（NFR-9.1-05：shouldDeferPreview）；突變驗證見〈七〉 | 待 QA 以 `p9-w5-ui-evidence.spec.ts::NFR-9.1-05` 對真後端重量（1KB／5KB／20KB 各 7 次取中位數）。FE 自量見〈三〉：20KB 中位數 58ms（修前 129ms，與 W5-QA 的 131ms 同量級），5 輪逐輪中位數 54～60ms | ✅ 實作+測試（20KB 自量 58ms 達標；QA 同法重量 < 100ms 後可升 ✅ 已驗證） |

## 二、量法與環境（同一把尺）

- 量測段**逐字**取自 `frontend/tests/e2e/p9-w5-ui-evidence.spec.ts` 的 `NFR-9.1-05` 區塊：`MutationObserver` 觀察 `.w-md-editor-preview`（`childList／subtree／characterData／attributes`），從「寫入編輯器值並送出 `input`」到預覽區最後一次 DOM 變動，之後 150ms 無變動視為穩定；內容樣板、`fill("")` 後等 400ms、每種大小 7 次取中位數都相同。
- 載具不同：用 Playwright 函式庫直接開 Chromium（headless shell，與 test runner 預設相同；Playwright 1.64.1），登入改寫 sessionStorage，API 一律 route mock（`/projects/new` 只需要專案列表與通知摘要兩個端點）。**沒有碰真後端 spec，也沒有後端。**
- 建置：Next 16.4.0 Turbopack production（`npm run build` → `node scripts/start-standalone.mjs`）。修後在埠 3100；修前是以 HEAD `ac9272da` 的建置另存一份 standalone 快照在埠 3101。修前修後**同一時段交錯**（各一輪、輪流五輪）以抵銷機器負載漂移；整機 CPU 使用率 5～8%（其他棒也在這台機器工作）。
- 機器：Windows 11、20 個邏輯核心、Node v22.23.3。

## 三、修前／修後三種大小各 7 次樣本與中位數（ms；同一時段交錯，五輪）

### 1KB

| 輪 | 修前（7 次樣本） | 中位 | 修後（7 次樣本） | 中位 |
|----|------------------|------|------------------|------|
| 1 | 29, 15, 12, 10, 7, 11, 11 | 11 | 32, 9, 13, 12, 8, 7, 9 | 9 |
| 2 | 33, 11, 14, 13, 6, 12, 11 | 12 | 33, 9, 14, 6, 6, 12, 10 | 10 |
| 3 | 32, 16, 18, 12, 8, 10, 9 | 12 | 32, 13, 12, 8, 9, 8, 7 | 9 |
| 4 | 31, 12, 15, 9, 7, 11, 8 | 11 | 29, 17, 12, 7, 12, 6, 9 | 12 |
| 5 | 36, 14, 12, 8, 7, 10, 12 | 12 | 33, 16, 9, 7, 11, 7, 9 | 9 |

### 5KB

| 輪 | 修前（7 次樣本） | 中位 | 修後（7 次樣本） | 中位 |
|----|------------------|------|------------------|------|
| 1 | 26, 26, 21, 21, 22, 23, 32 | 23 | 18, 26, 24, 16, 15, 23, 15 | 18 |
| 2 | 24, 40, 21, 27, 23, 20, 28 | 24 | 24, 27, 25, 22, 17, 21, 16 | 22 |
| 3 | 24, 27, 29, 26, 24, 23, 30 | 26 | 21, 22, 23, 19, 17, 16, 15 | 19 |
| 4 | 28, 34, 21, 20, 22, 22, 27 | 22 | 22, 28, 18, 21, 20, 16, 15 | 20 |
| 5 | 24, 29, 29, 24, 20, 25, 28 | 25 | 18, 25, 20, 16, 15, 17, 16 | 17 |

### 20KB（約 14,000 字）

| 輪 | 修前（7 次樣本） | 中位 | 修後（7 次樣本） | 中位 |
|----|------------------|------|------------------|------|
| 1 | 131, 126, 123, 133, 125, 126, 123 | 126 | 60, 61, 55, 55, 63, 65, 58 | 60 |
| 2 | 129, 129, 132, 132, 119, 128, 125 | 129 | 67, 58, 59, 63, 58, 56, 51 | 58 |
| 3 | 132, 132, 130, 129, 127, 124, 132 | 130 | 66, 54, 68, 68, 54, 53, 54 | 54 |
| 4 | 133, 148, 135, 132, 123, 128, 130 | 132 | 69, 57, 54, 64, 56, 55, 57 | 57 |
| 5 | 128, 157, 124, 131, 146, 123, 120 | 128 | 70, 57, 59, 63, 53, 58, 57 | 58 |

| 大小 | 修前（35 個樣本的中位數／最大） | 修後（35 個樣本的中位數／最大） | 變化 |
|------|--------------------------------|--------------------------------|------|
| 1KB | 12ms／36ms | 9ms／33ms | 約 -25% |
| 5KB | 24ms／40ms | 19ms／28ms | 約 -21% |
| 20KB | **129ms**／157ms | **58ms**／70ms | **約 -55%**（< 100ms 達標，餘裕 42ms） |

- 最終程式碼的建置（與交卷版只差最後兩處註解文字）再交錯量三輪：20KB 修前 126、127、126ms，修後 60、63、60ms，與上表一致。
- 第一次重現基線（機器較忙、尚未交錯）：1KB 9／10／13ms、5KB 28／28／29ms、20KB 158／172／173ms 三輪中位數；W5-QA 在自己的環境量到 10／23／131ms，W5-FE 自報 12／30／149ms。量到的絕對值隨機器負載漂移 ±20%，所以**判斷一律看同一時段交錯的修前修後比**。

## 四、四個待驗假設的結論（用 CPU profile、trace 與 Node 逐外掛計時證實或推翻）

| 假設 | 結論 | 證據 |
|------|------|------|
| (a) 預設鏈的 rehype-prism-plus 與專案另加的 rehype-highlight 對程式碼區塊**重複高亮** | **成立，但成本小，保留** | 順序是預設鏈 → 使用者外掛（含 rehype-highlight）→ 鏈尾的 rehype-prism-plus；prism 以 `toString(code)` 重新斷詞、整個換掉 children，所以 rehype-highlight 產生的 `hljs-*` 節點在輸出 DOM 裡一個不剩，只留下 `hljs` class（DOM 實測：`code.hljs.language-ts.code-highlight` 底下全是 `.token`）。編輯器預覽沒有任何 `.hljs-*` 的 CSS（`styles/markdown.css` 的規則都在 `.md-view` 底下，那是唯讀 MarkdownView）。成本：Node 逐外掛計時 20KB 約 4.5ms（整條管線約 70ms）；瀏覽器 A/B（線性化與批次修好之後）拿掉它 73 → 69ms，在雜訊內。`pluginsFilter` 確實拿得掉預設鏈任何一個外掛（實驗用過）。**不拿掉的理由**：真後端 `markdown-editor.spec.ts` 與 `markdown.test.tsx` 斷言 `hljs` class，拿掉要補一個只為保留 class 的外掛、或動被斷言的 DOM，換不到可量測的收益 |
| (b) `useDeferredValue` 對單次大貼入多出一個畫面 | **成立，是第二大塊** | trace（貼入 20KB 的單次）：急件任務 78ms（`EventDispatch`）、**中間一個畫面 51ms**（`Layout` 31.6ms＋`UpdateLayoutTree` 12.9ms＋`PrePaint` 3.9ms＋Paint）、延後任務 44.5ms。瀏覽器得先為左欄原始碼著色（20KB 約 1,070 行、4,300 個 span）重算版面，才輪到預覽。A/B：不排程 113ms 對排程 184ms（-71ms，左欄修好之前）；左欄修好之後 76ms 對 107ms（-31ms）。**但排程對連續打字有用**（〈六〉：輸入延遲 p50 104ms → 40ms）。修法：只有批次變更（預覽落後 > 1,000 字）不排程 |
| (c) `rehypeTaskLabels`／`remark-gfm` 的成本 | **不成立（不是瓶頸）** | `rehypeTaskLabels` 20KB 約 0.1ms。`remark-gfm`：remark 階段（parse＋mdast→hast）無 gfm 14.1ms、有 gfm 25.5ms，GFM 約占 10ms（管線的 15%），但 GFM 表格與核取清單是 PRD §5.1.4 第 4、6 項，且 MarkdownView 用同一套，必須保留。**沒有跑兩次**：專案的 `remarkPlugins: [remarkGfm]` 與 preview.js 預設的 `gfm` 是同一個函式身分，unified 以身分去重（`micromarkExtensions` 掛兩次與掛一次都是 1 筆，實測） |
| (d) 預覽端還掛著不需要的外掛（rehype-raw／rehype-slug／autolink 等） | **成立（8 個預設外掛都在），但各有可見行為，不動** | 預設鏈：reservedMeta、rehype-raw、retrieveMeta、rehype-slug、rehype-autolink-headings、rehype-ignore、rehype-rewrite、rehype-attr。Node 逐外掛 20KB：raw 3.5、attr 2.4、retrieveMeta 2.4、rewrite 2.2、reservedMeta 2.1、autolink 2.0、slug 1.8、ignore 1.8ms，合計約 18ms。瀏覽器 A/B（線性化＋批次之後，5 輪）：全拿掉 73 → 51ms（-22ms）；拿 raw＋meta 就 -10ms。**各自的行為**：raw＝Markdown 內嵌 HTML 變成真元素（見〈九〉）；slug＋autolink＋rewrite＝標題錨點與程式碼區塊複製鈕（全拿掉後 `h2 a.anchor` 與 `div.copied` 變 0）；reservedMeta／retrieveMeta 從外掛順序看是為 raw 服務（raw 之前把 `data.meta` 存進屬性、之後還原；沒驗證 raw 是否真的丟 `data`）。目標已達成，不為剩下的 ~10ms 換行為，數字留給主控裁決 |
| (e)（待驗假設之外找到的）**真正的根因：左欄原始碼著色的逐行拆分是 O(行數 × 節點數)** | **成立，最大一塊** | 見〈五〉 |

## 五、根因與修法

**根因**（CPU profile 取樣 100µs＋Chrome trace，貼入 20KB 的單次；profile 內 self time 最高的函式是 rehype-prism-plus 的逐行過濾）：`@uiw/react-md-editor` 的左欄疊層（`TextArea/Markdown.tsx`）把**整份** Markdown 當成**一個** `language-markdown` 程式碼區塊交給 `rehype-prism-plus`；該外掛對每一行都用 `unist-util-filter` 把整棵高亮樹過濾一遍。20KB 的文件是 1,073 行、4,288 個 token，約 460 萬次節點走訪，自身時間約 51ms（`filter` 39.8ms＋述詞閉包 11.2ms），占急件任務（78ms）的大半，也決定了「中間那個畫面」要重算的版面有多大。同一個外掛也用在預覽的程式碼區塊：大區塊在預覽裡一樣二次方（Node 實測 python 2,000 行 653ms、8,000 行 11,193ms）。

**修法（4 件）**：

1. **`components/markdown/rehypePrismLinear.ts`**（新增）：rehype-prism-plus 2.0.2 預設匯出的行為等價改寫，只改逐行拆分——每個節點走訪一次、依涵蓋的行放進各行（單行節點整棵沿用不複製、多行元素才逐行淺拷貝）⇒ O(節點數＋輸出大小)。其餘（語言判定、`{1,3-5}`／`showLineNumbers` meta、diff 的 deleted／inserted、結尾空行、「以換行結尾的 token 會在下一行留下空殼」的上游細節）逐項照搬。Node 對照左欄路徑：20KB 上游 42.3ms → 線性 13.9ms。MIT 授權全文附在檔尾。
2. **`next.config.ts` 的 `turbopack.resolveAlias`** 把裸名稱 `rehype-prism-plus` 指到上檔。兩個匯入者（`@uiw/react-markdown-preview` 的 index 與 `@uiw/react-md-editor` 的 `TextArea/Markdown`）都是 `import rehypePrism from 'rehype-prism-plus'`，所以左欄著色與預覽的程式碼區塊一起換掉；子路徑（`/common`、`/all`）不受影響，測試拿 `/all` 當上游。左欄疊層在瀏覽器裡的完成時間 57～71ms → 18～24ms。
3. **`MarkdownEditorImpl.tsx` 的 `shouldDeferPreview`**：文件 ≤ 8,000 字不排程（同前）；連續打字（預覽只落後幾個字）排程（同前）；**批次變更**（預覽落後 > `BULK_EDIT_CHARS`＝1,000 字，貼上、匯入 .md、清空、復原）且文件 ≤ `SYNC_RENDER_MAX_CHARS`＝30,000 字（約 20KB 文件的兩倍）時一次渲染到位，不再中間插一個畫面；超過 30,000 字的批次仍排程，免得整頁卡住。只比字數：同長度的整份替換會當成打字處理，結果仍正確，只是多一個畫面。
4. **`package.json`／`package-lock.json`**：直接依賴新增 `parse-numeric-range`、`refractor`（新模組匯入它們，原本只是傳遞依賴），devDependencies 新增 `rehype`、`rehype-prism-plus`（釘 2.0.2：測試拿它當「上游」，也是這份改寫所本的版本）。四者在 node_modules 與 lock 裡早就是同版本；離線 `npm install --package-lock-only` 在暫存副本上跑完，lock 逐位不變，證明手改的根條目與 npm 一致。

**各步驟對 20KB 的貢獻**（同一個建置、旋鈕切換、各變體交錯；全部樣本中位數，ms；絕對值比〈三〉高是因為那一時段機器較忙，只看相對）：

| 變體 | 預覽更新 |
|------|----------|
| 修前（上游 prism＋排程） | 157～184（兩次不同時段的 A/B） |
| 只做批次一次渲染（上游 prism） | 122～138 |
| 只做線性化（排程不動） | 107 |
| **線性化＋批次一次渲染（最終方案）** | **73～85** |
| 對照：線性化＋完全不排程 | 76 |
| 對照：上游 prism＋完全不排程 | 113 |
| 對照：關掉左欄著色（下限；會退化功能）＋排程 | 79 |
| 對照：關掉左欄著色＋批次一次渲染（下限；會退化功能） | 54～60 |
| 最終方案再拿掉全部預設外掛（會退化功能） | 51 |

## 六、連續打字不退化（輸入延遲）

20KB 文件、在文末每隔 50ms 打一個字、共 24 個字、5 輪取中位數；Event Timing（`type=event`、`durationThreshold=16`）取 `input` 事件到下一次繪製的時間（精度 8ms），另取 longtask。

| 變體 | input 延遲 p50 | p95 | longtask 累計 | 最長單一 |
|------|----------------|-----|---------------|----------|
| 舊（上游 prism＋排程，修前行為） | 96ms | 136ms | 2,625ms | 131ms |
| **新（線性 prism＋批次一次渲染＋排程）** | **40ms** | **72ms** | **958ms** | **79ms** |
| 對照：線性 prism、不排程 | 104ms | 144ms | 2,317ms | 137ms |
| 對照：上游 prism、不排程 | 144ms | 200ms | 3,582ms | 196ms |

- 打字比修前快 58%（p50 96 → 40ms）：左欄著色每個字都要重做一次，線性化讓每個字少花約 56ms（p50 差）；排程仍然有用（不排程 104ms 對排程 40ms），所以只讓批次變更繞過它。
- W5-FE 當時的同法數字是 136 → 80ms（排程對不排程），本次舊行為 144 → 96ms，同量級。

## 七、等價性與回歸證據

- **逐位相等（單元）**：`rehypePrismLinear.test.ts` 同一輸入餵上游 `rehype-prism-plus/all` 與本檔，比對 hast 結構（含每個節點的 `position`，以 JSON 比）與 HTML 字串。涵蓋：左欄形態（1／5／60 節文件）、13 組語言樣本（含未註冊的 foobar 與無語言）、邊角內容（空、只有換行、CRLF、tab、5,000 字單行、emoji 與 CJK）、選項（`showLineNumbers` 真／指定語言／假、`defaultLanguage`）、meta 八種（`data.meta` 與 `metastring` 兩種來源）、diff 與 diff-js、className 的各種既有形態、錯誤行為一致、固定種子的 300 份隨機文件。
- **突變驗證**（確認這些測試會紅）：(1) 讓多行元素不拆行 → 五支相等性測試紅；(2) 把逐行分配改回二次方（行為不變、只變慢）→ 相等性測試仍綠、**複雜度測試紅**（耗時比 23，線性 4.4～5.0、上游同輸入 17、界線 10）。
- **逐位相等（瀏覽器）**：修前（3101）與修後（3100）兩個 production 伺服器，同一份文件貼進編輯器，比對預覽區與左欄著色的 `innerHTML`：功能雜燴（setext 標題、GitHub 提示區塊、巢狀清單與核取清單、表格對齊、刪除線與自動連結、腳註、內嵌 HTML、`{1,3-4} showLineNumbers` meta、diff、未註冊語言、無語言、縮排程式碼、圖片與 `javascript:` 連結）、p9 的 1KB／5KB／20KB、功能雜燴 30 倍（約 20KB，批次路徑）——**五份全部逐位相同**（預覽與左欄各一，最長約 30 萬字元）。
- **別名確實生效**：production 的 chunk 掃描——上游逐行過濾的特徵 `position.end.line>=` 修前出現 1 次、修後 0 次；`next dev`（Turbopack dev）的 chunk 含 `rehypePrismLinear` 模組路徑（左欄套件與預覽套件的兩個 chunk 都引用）。`next.config.ts` 別名與兩個匯入者的普查、兩個匯入者解析到的版本，由 `rehypePrismLinear.test.ts::接線` 守住（上游升版或有人改走 `/common` 入口就紅）。
- **批次一次渲染到位的直接證據**：最終方案貼入 20KB 時，左欄著色與預覽的末次 DOM 變動時間讀數一致（5 輪逐輪中位數兩個 observer 都是 71、73、77、83、73ms），也就是同一次提交；修前左欄在 57～79ms、預覽在 157～184ms，兩者之間隔著那一個畫面。
- **bundle 沒有變大**：`.next/static/chunks` 總量 3,116,935 → 3,113,612 bytes（-3.3KB）。
- 預覽功能不退化：GFM 表格、程式碼語言高亮（`.token`）、核取清單名稱、鍵盤可達 region、匯入匯出、axe 全由既有測試涵蓋並通過（〈八〉）；DOM 與修前逐位相同是更強的保證。

## 八、驗證摘要（本棒實跑；指令與 rc）

在 `frontend/` 下（Windows PowerShell，`Push-Location`／`Pop-Location` 同呼叫成對）：

| 指令 | rc | 結果 |
|------|----|------|
| `npm run lint`（ESLint＋Prettier 檢查） | 0 | 無輸出、All matched files use Prettier code style |
| `npx tsc --noEmit` | 0 | 無輸出 |
| `npm run build` | 0 | 20 個路由 |
| `npx vitest run` | 0 | 51 個測試檔、745 支通過（本棒新增 1 個檔、20 支：rehypePrismLinear.test.ts 15 支、markdown.test.tsx 5 支；修前基準推算為 50 個檔、725 支＝W5-FE 的 697 加 W6 的 28） |
| `npx vitest run --coverage` | 0 | Statements 95.6%、Branches 89.65%、Functions 97.41%、Lines 97.12%（W5-FE 為 95.58／89.63／97.4／97.11，沒有下降） |
| `npx playwright test <八支 *.mock.spec.ts> --output=<暫存目錄>`（`E2E_MODE=standalone`，對 production 建置，埠見下） | 0 | 53 支通過（含 23 處 axe 掃描全部零違規） |
| 同上，改用 `next dev` 跑 `a11y.mock.spec.ts` 與 `import.mock.spec.ts`（含 Markdown 編輯器的兩個檔） | 0 | 11 支通過（確認別名在 dev 也生效） |
| 四區塊只在 `app/layout.tsx` 組裝的掃描（`frontend/README.md` 的 PowerShell 形態：列出 `app` 底下排除 `layout.tsx` 的 `*.tsx`，找 TopRegion、ToolsRegion、BottomRegion） | — | 無輸出 |

- 埠：production 建置的 `E2E_WEB_PORT` 為 3100（Playwright 沿用已在該埠的伺服器），dev 為 3200；修前快照在 3101。
- 目錄裡沒有 `--project=mock`：`playwright.config.ts` 只有一個 `chromium` project，mock spec 以檔名清單執行（見 `tests/e2e/README.md`）。
- 跑 mock spec 會重寫 `tests/e2e/__screenshots__/` 的已追蹤 PNG（本棒沒有 UI 變動）；已依 HEAD 內容逐檔還原，截圖目錄在 `git status` 無差異。
- 重量指令（QA 或主控自行複驗；bash 與 PowerShell 並列）。p9 這支 spec 的 `beforeAll` 會建夾具，`-g` 只挑情境、不省環境，所以需要完整的真後端環境（見 `tests/e2e/README.md`〈W5 複驗〉）：

```bash
(cd AgentConsole/frontend && npm run build && E2E_ROOT=<ABS_PATH_TO_EMPTY_DIR> E2E_API_URL=http://localhost:18080 E2E_WEB_PORT=3000 E2E_MODE=standalone npx playwright test tests/e2e/p9-w5-ui-evidence.spec.ts -g "NFR-9.1-05" --output=<自己的暫存目錄>)
```

```powershell
Push-Location AgentConsole\frontend; npm run build; $env:E2E_ROOT = "<ABS_PATH_TO_EMPTY_DIR>"; $env:E2E_API_URL = "http://localhost:18080"; $env:E2E_WEB_PORT = "3000"; $env:E2E_MODE = "standalone"; npx playwright test tests/e2e/p9-w5-ui-evidence.spec.ts -g "NFR-9.1-05" "--output=<自己的暫存目錄>"; Pop-Location
```

## 九、偏離、限制與發現（供主控與 QA）

1. **沒有拿掉 rehype-highlight 與其他預設外掛**：理由與數字見〈四〉(a)(d)。目標已達成（58ms），再拿會改 E2E 斷言的 DOM 或砍掉可見功能（標題錨點、程式碼複製鈕、內嵌 HTML）。若日後要再省 ~10ms：先放寬 `hljs` class 斷言再拿 rehype-highlight（-4ms）；raw＋meta（-10ms）屬行為變更，見第 3 點。
2. **不改真後端 spec**（持有面）：`p9-w5-ui-evidence.spec.ts` 的 `NFR-9.1-05` 標題仍寫「W4：112ms、W5-FE 去抖後：149ms」，20KB 只斷言 `< 400` 並註明「目標 100ms 未達屬已知 🟡」。**QA 請把 20KB 的上限收緊成 `< 100`、更新標題與註解**，這才是守住 NFR 的那一道。
3. **發現（本棒沒動，預覽與詳情頁不一致）**：編輯器預覽走套件預設鏈的 rehype-raw，Markdown 內嵌的 HTML 會變成真元素（實測 `<b>`、`<kbd>`、`<br/>`、`<details>` 各 1 個，修前修後相同）；詳情頁的 `MarkdownView` 不渲染 HTML（既有單元測試斷言）。所以「預覽看到的」與「存檔後詳情頁看到的」對內嵌 HTML 不同；而且匯入的 .md 若含 HTML 會在預覽端被當成元素建出來。本棒沒有驗證腳本類元素的處置，**建議另案評估**（拿掉 raw 另可省 ~10ms，一舉兩得）。
4. **限制**：Prism 的 markdown 文法本身在大文件上超線性（`refractor.highlight` 的 markdown 在 1,000 行 39ms、4,000 行 641ms），所以左欄著色在遠大於 20KB 的文件（約 4,000 行以上）仍會變慢；這是 Prism 文法的特性，不是這份改寫的問題，也不在 20KB 的目標內。超過 30,000 字的批次貼入維持舊行為（排程）。
5. **別名是對相依套件內部的 bundler 層替換**（不是 patch-package）：升級 `@uiw/react-md-editor`／`@uiw/react-markdown-preview` 或 `rehype-prism-plus` 時，`rehypePrismLinear.test.ts` 的逐位比對與普查會紅，提醒回頭檢視。
6. 本棒全程在 Windows 11＋PowerShell 完成；Turbopack 別名與測試內的路徑處理沒有平台相依，但**沒在 macOS 實跑**。

## 十、給 QA 的提醒

- 重量 `NFR-9.1-05`：用 production 建置（`E2E_MODE=standalone`）跑 p9 同一支 spec 的 `NFR-9.1-05` 區塊；預期 20KB 中位數落在 50～70ms，1KB、5KB 與修前同量級。若你的環境量到 ≥ 100ms，請同時量左欄疊層的完成時間（本棒用第二個 observer 觀察 `.w-md-editor-text`，正常應在 20ms 上下）以區分別名失效與機器過慢。
- RTM 該改的列：`NFR-9.1-05`（本檔〈一〉四格）。其餘 UI-MD-01～08 與 UI-A11Y 各列不需改：預覽與左欄 DOM 逐位相同，`markdown-editor.spec.ts` 對 `hljs` class 與 `.token.keyword`、`.token.number` 的斷言維持成立。
- 新增依賴：`npm ci` 即可（lock 已同步）；Docker 映像下次重建才會帶入。全棧 E2E 不受影響。
- ADR-001 §4 的 NFR-9.1-05 條目（SA 持有面）：建議改寫為「20KB 中位數 129ms → 58ms，根因＝左欄原始碼著色的逐行拆分二次方＋延後渲染多一個畫面；以別名換行為等價的線性版、批次不排程」，數字見〈三〉。

---

# 第二批：D-12 資源使用、D-11 引擎能力晶片、D-01 DAG 全螢幕（契約 v1.3 與 v1.4）

> 日期 2026-10-16｜依據：`docs/04_planning/agent_briefs/W7_OVERVIEW.md`（D-01、D-11、D-12）與 `docs/02_architecture/API_Contract_P3-6.md` 的 §1.2.3、§3.1.2、§3.4.2、§4.2 E-21 與 E-22、§4.3 M-19、§4.4 S-13、E2E-14 第 8～9 列。
> 本節同樣**不改 RTM.md**，由 W7-QA 單線合併；格式同〈一〉；測試計數寫中文，行內不放四位數字。
> 結論：三項的前端部分皆**實作與測試完成**；與真後端的欄位對接（E2E-14）和 RTM 狀態升級由 QA 依當回合證據判定。

## 十一、第二批 RTM 列

| ID | 實作檔 | 自動測試 | E2E 驗證 | 建議狀態 |
|----|--------|----------|----------|----------|
| US-M-10（前端部分：資源使用情況，D-12） | frontend/components/domain/monitor/AgentCard.tsx（第二列整列的「資源使用」格 `agent-resources`，格式 `CPU 12.3%・記憶體 345 MB・3 行程`，取樣時間放 tooltip；`resourceView`：`bridge.resources` 為 null 或缺席、`bridge.connected=false`、批次終態、批次暫停一律單一「—」；`agent-note` 只留 Bridge 實例，v1.2 的「目前沒有提供這項資料」整句已刪）、frontend/lib/format.ts（`formatResourceUsage`：CPU 一位小數、記憶體 MB 取整數、達 1,024 MB 改以 GB、不足 1 MB 寫 `<1 MB`）、frontend/lib/api/schema-p3-6.d.ts 與 frontend/lib/api/types.ts（重產型別，新增 `ResourceUsage` 別名） | frontend/lib/format.test.ts::資源使用（契約 §4.3 M-19；US-M-10）（7 支）、frontend/components/domain/monitor/MonitorView.test.tsx::監控頁：Agent 即時狀態的資源使用（契約 §4.3 M-19，D-12；US-M-10）（有資源與 tooltip、第二列整列且既有四格順序不變、七種沒有資料的情形、沒有任何批次）、frontend/components/domain/monitor/MonitorView.test.tsx::監控頁：批次比較與 Agent 狀態（US-M-06、M-10）（舊說明句移除、Bridge 實例）；突變驗證見〈十三〉 | frontend/tests/e2e/monitor.mock.spec.ts::Agent 即時狀態的資源使用（契約 §4.3 M-19，D-12…）（有取樣顯示契約格式、tooltip 取樣時間、既有四格同一列而資源使用在第二列、切到已完成與失敗批次為「—」、回到進行中批次數字回來、axe 零違規）、同檔::資源使用：引擎行程樹沒有取樣…（null 為「—」）、同檔::批次比較、事件時間軸、Agent 即時狀態…（舊說明句斷言改為新行為）。與真後端對接＝契約 E2E-14 第 8～9 列，待 QA | ✅ 前端實作＋測試；RTM `US-M-10` 由 QA 依 E2E-14 第 8～9 列的當回合證據自 🟡 升級（契約 §4.6 G-M3） |
| API-AUT-06（前端顯示部分：引擎能力晶片、設定頁標籤、自治等級說明，D-11） | frontend/components/domain/execute/parts.tsx（`EngineCapabilityChips`：「自動突變」「自演化」兩枚晶片，各三態＝已啟用、關閉、無金鑰不可用，`data-capability`／`data-state`／`title`；欄位缺席或 null 整列不顯示）、frontend/components/domain/execute/ProgressCard.tsx（標題列下方顯示晶片列）、frontend/lib/domain/status.ts（字典 `engineCapabilityView`／`ENGINE_CAPABILITY_KEYS`；`autonomyHint` 的 Level 6 至 10 改寫為審核閘同 Level 5、另要求自動突變與自演化、結果看晶片）、frontend/lib/api/types.ts（`EngineCapabilities`、`EngineCapabilityState` 別名）；設定頁（S-13）程式碼不用改：`SettingRow.tsx` 只對 `STORED_ONLY` 與 `UNVERIFIED` 加小標籤，`ENGINE` 與 `CONSOLE` 不加 | frontend/lib/domain/status.test.ts::引擎能力晶片字典與自治等級說明（契約 §1.2.1、§3.4.2、§3.6.1、§4.2 E-21；v1.3 D-11）（6 支）、frontend/components/domain/execute/ExecuteView.test.tsx::執行頁：引擎能力晶片「自動突變」「自演化」（契約 §4.2 E-21，v1.3 D-11）（逐格六態的文字與 tooltip、固定順序與群組名稱、自演化「僅提案」、三態外觀互異、缺席與 null、未知狀態值、切換批次取各自的值）、frontend/components/domain/execute/ExecuteView.test.tsx::執行頁：版面與鎖定（設計稿畫面 7）（等級 6 至 10 的說明）、frontend/components/domain/settings/SettingsView.test.tsx::版面與分類 tab（US-S-01）（`agent.enableAutoMutation` 無標籤且說明寫 Brain 逐步校正、`agent.enableSelfEvolution` 加「僅儲存、不影響引擎」、`sdd.specFormat` 仍是「尚未驗證對映」） | frontend/tests/e2e/execute.mock.spec.ts::引擎能力晶片…（四支：有金鑰從 UI 以 Level 7 啟動、有金鑰 Level 4 與 Level 7 切批次、沒有金鑰兩種等級、V10 之前的批次缺席）、frontend/tests/e2e/settings.mock.spec.ts::Agent tab 的兩個引擎旗標（契約 v1.3，D-11；S-13）…；假引擎 execFixture.ts 依契約 §3.4.2 決策表（兩個旗標皆為預設的假）由等級與金鑰推出 `engineCapabilities`。與真後端對接＝契約 E2E-14 第 4、6 列，待 QA | ✅ 前端顯示部分實作＋測試；RTM `API-AUT-06` 由 QA 依 E2E-14 的當回合證據升級 |
| US-E-09（DAG 全螢幕，D-01，契約 §4.2 E-22；缺口 G-E4） | frontend/components/domain/execute/DagCard.tsx（標題列「全螢幕」鈕；覆蓋層＝共用層 `Dialog` 鋪滿視窗，不用瀏覽器 Fullscreen API；層內「結束全螢幕」鈕帶 `aria-pressed`、Esc 同樣結束；結束後焦點回「全螢幕」鈕，沿用 frontend/components/ui/dialog.tsx 的歸還機制；圖形只掛一份，全螢幕時卡內換成等高空位；全螢幕內的圖形捲動區有名稱與 tabindex；展開與收合狀態進出全螢幕都保留） | frontend/components/domain/execute/DagCard.test.tsx（新增檔，17 支：切換鈕、進入、層內鈕狀態、類別覆寫確實換掉白卡、圖形只掛一份、捲動區名稱、Esc 與標題列關閉鈕與結束鈕三種離開方式的焦點歸還、可重複進出、層內展開收合、狀態保留、SSE 疊加更新、圖形資料消失、載入失敗） | frontend/tests/e2e/execute.mock.spec.ts::DAG 全螢幕（契約 E-22，v1.4 D-20）…（覆蓋層 bounding box 等於視窗且等於 `window.innerWidth` 與 `innerHeight`、`document.fullscreenElement` 為 null、SSE 節點更新在層內照常、層內收合後結束仍是收合、Esc 與結束鈕離開後焦點回「全螢幕」鈕、axe 零違規） | ✅ 前端實作＋測試（E-22 驗收＝前端單元測試加一支 e2e 尺寸斷言，皆已備）；`US-E-09` 的 RTM 狀態由 QA 合併時判定 |

## 十二、第二批驗證摘要（本棒實跑；指令與 rc）

在 `frontend/` 下（Windows PowerShell，`Push-Location`／`Pop-Location` 同呼叫成對）：

| 指令 | rc | 結果 |
|------|----|------|
| `npm run gen:api-p36` | 0 | 型別重產；重產前（HEAD 版）與重產後的 SHA256 見下方；來源 yaml 已是 v1.4（含 `/engines/sdd`、`/signoffs/pending`、`/auth/logout`），新增型別第三批才使用；重產後 `npx tsc --noEmit` 無破壞性變動 |
| `npm run lint`（ESLint＋Prettier 檢查） | 0 | 無輸出、All matched files use Prettier code style |
| `npx tsc --noEmit` | 0 | 無輸出 |
| `npm run build` | 0 | 20 個路由 |
| `npx vitest run` | 0 | 52 個測試檔、799 支通過（第一批結束時為 51 個檔、745 支；本批新增 DagCard.test.tsx 一個檔與 54 支） |
| `npx vitest run --coverage` | 0 | Statements 95.65%、Branches 89.75%、Functions 97.43%、Lines 97.16%（門檻 70／60／70／70，沒有下降） |
| `npx playwright test <八支 *.mock.spec.ts> --output=<暫存目錄>`（`E2E_MODE=standalone`，對 production 建置；分三次執行） | 0 | 合計 61 支通過（第一批結束時 53 支；本批新增 8 支：settings 1、monitor 2、execute 5）；axe 掃描全部零違規 |
| 四區塊只在 `app/layout.tsx` 組裝的掃描 | — | 無輸出 |

- 型別重產：`lib/api/schema-p3-6.d.ts` 重產前（HEAD 版）SHA256 `135486DBD5B3BC895A8183F9AAB848C545FEFB5BB12A3D84D0DC9ABFD0197D13`（178,436 bytes）→ 重產後 `6F2DFDF78F543053E874E0E39BC4E1C966E9F80BA6B0A346331FDB7DD8A0B43B`（204,652 bytes）；來源 `docs/02_architecture/openapi-p3-6.yaml` 以 HEAD（`10033d5d`）為準，SHA256 `D29F9958CF23CEBBAEE5754ECCCE846EEEE68DB43121D1C3C128C3ECD7BD4432`（工作樹與 HEAD 相同）。SA 在本批進行中改過這份 yaml（第一次重產之後它又變過）；交卷前對 HEAD 版再重產一次（rc=0），d.ts 與前兩次逐位相同。第三批動工前建議再跑一次。
- 跑 mock spec 會重寫 `tests/e2e/__screenshots__/` 的已追蹤 PNG；本批已依 HEAD 內容逐檔還原，截圖目錄在 `git status` 無差異。**本批 UI 有變動**（07-execute-* 多一列晶片與一顆「全螢幕」鈕、08-monitor-* 的 Agent 卡多一列資源使用），這些設計證據圖尚未更新，需要時請主控或 QA 重拍。
- 重現指令（bash 與 PowerShell 並列；需先以 `PORT=3100` 起 production 伺服器 `node scripts/start-standalone.mjs`，用完停掉，見 `tests/e2e/README.md`）：

```bash
(cd AgentConsole/frontend && npx vitest run lib/format.test.ts lib/domain/status.test.ts components/domain/execute components/domain/monitor components/domain/settings)
(cd AgentConsole/frontend && E2E_MODE=standalone E2E_WEB_PORT=3100 npx playwright test tests/e2e/execute.mock.spec.ts tests/e2e/monitor.mock.spec.ts tests/e2e/settings.mock.spec.ts --output=<自己的暫存目錄>)
```

```powershell
Push-Location AgentConsole\frontend; npx vitest run lib/format.test.ts lib/domain/status.test.ts components/domain/execute components/domain/monitor components/domain/settings; Pop-Location
Push-Location AgentConsole\frontend; $env:E2E_MODE = "standalone"; $env:E2E_WEB_PORT = "3100"; npx playwright test tests/e2e/execute.mock.spec.ts tests/e2e/monitor.mock.spec.ts tests/e2e/settings.mock.spec.ts "--output=<自己的暫存目錄>"; Pop-Location
```

## 十三、突變驗證（確認新測試會紅）

- 拿掉 `AgentCard.tsx` 的 `run.status === "PAUSED"` 判斷 → `MonitorView.test.tsx` 的「批次暫停」那一格紅（其餘六格仍綠，因為終態與未連線有各自的判斷）。
- 拿掉 `DagCard.tsx` 覆蓋層類別裡的 `inset-0` → `DagCard.test.tsx::覆蓋層鋪滿視窗…` 紅。
- 兩處都已改回，之後全套重跑為綠。

## 十四、偏離、限制與發現（供主控與 QA）

1. **暫停中的批次也顯示「—」**：契約 M-19 只列 null 或缺席、`bridge.connected=false`、批次終態三種。這裡多加 `PAUSED`，理由是 §3.1.2（pause 會終止整棵引擎行程樹，伺服器回 null）與 E2E-14 第 9 列（PAUSED 的批次卡片顯示「—」）；SSE 先把快取改成 PAUSED、REST 重抓要等去抖週期，這段空檔不能繼續顯示暫停前的舊數字。
2. **記憶體單位的門檻比未四捨五入的位元組數**：差 1 byte 的 1 GiB 仍寫 `1024 MB`，與「不足 1 MB 寫 `<1 MB`」同一把尺。若 QA 要改成以四捨五入後的值判斷，只需改 `lib/format.ts` 的 `formatMemory` 一處。
3. **任務清單之外的修正（同屬 API-AUT-06 前端顯示）**：`autonomyHint` 對 Level 6 至 10 的舊句「目前不另傳給引擎（對映尚未驗證）」已被契約 v1.3（§3.6.1）推翻，一併改寫；對應的舊斷言（`ExecuteView.test.tsx`）已更新。
4. **設定頁用字與晶片用字不同，未統一**：`components/domain/settings/labels.ts` 的「啟用自動變異」「啟用自我演化」（設計稿原文）對晶片的「自動突變」「自演化」（契約 E-21）。本批沒動設定頁標籤，請主控裁決是否統一。
5. **假引擎預設帶 `engineCapabilities`**（預設有金鑰；等級 4 為自動突變關閉、自演化已啟用），所以既有 execute mock 情境與截圖都會多出晶片列；`legacyRuns` 選項模擬 V10 之前的批次（缺席）。
6. **覆蓋層標題與卡片標題同名**（「DAG 依賴視覺化」）：全螢幕開著時卡片標題仍在 DOM（被 `aria-hidden` 隔開）；e2e 請用 testid 或 `getByRole("dialog", { name })` 取覆蓋層，不要用 `getByText`。
7. **Docker 全棧的已知低估**（契約 §3.4.2 誠實劃界 1）：Bridge 環境本身有金鑰、Console 沒有時，晶片顯示「無金鑰不可用」；前端如實顯示契約值，不推測。
8. **`tests/e2e/README.md` 第 23 行的情境數量說明**（execute 15 個、monitor 9 個）在本批之前就已與實際不符，本批未動。
9. 未驗證：全程在 Windows 11 與 PowerShell 完成，**沒在 macOS 實跑**；本批沒有平台相依的程式碼（覆蓋層是頁面內的 CSS 與 Radix Dialog）。

## 十五、給 QA 的提醒（第二批）

- 取元素用的 testid：`agent-resources`（值；欄位標籤是它的前一個兄弟，文字「資源使用」）、`agent-note`；`engine-capabilities`（`role=group`、名稱「引擎能力」）、`engine-capability`（`data-capability`＝autoMutation 或 selfEvolution、`data-state`＝三態值、`title`＝說明）；`dag-fullscreen-open`（卡片上的「全螢幕」鈕）、`dag-fullscreen`（覆蓋層，`role=dialog`）、`dag-fullscreen-exit`（「結束全螢幕」）、`dag-fs-toggle`（覆蓋層內的展開與收合）、`dag-placeholder`（全螢幕時卡內的空位）。
- 對真後端驗 E2E-14 第 8 列時：Windows 的 venv 啟動器多一層殼，行程數不可斷言精確值（契約已註明）；卡片數字最舊約 20 秒（詳情輪詢 15 秒加取樣 5 秒）。
- 對真後端驗 E2E-14 第 9 列時：終態、PAUSED、Bridge 停掉三種都應顯示單一「—」且沒有「目前沒有提供這項資料」字樣；`US-M-10` 升級以那一列的當回合證據為準。
- 全螢幕 e2e（E-22）：本棒的 mock 版已量到覆蓋層 bounding box 等於視窗；真瀏覽器全棧版可沿用同一組 testid。
- RTM 該改的列：`US-M-10`、`API-AUT-06`、`US-E-09`（本檔〈十一〉三列）。真後端 spec（p3 至 p9、signoff、crud-flow、task-retry、markdown-editor）本批沒動（持有面）。
