# Handoff：AISDLC Agent Console（自治開發 Agent 控制台）

## Overview / 概述

這是一個面向 **AISDLC 自治開發 Agent** 的網頁控制台（Agent Control Panel）。
掌舵者（人類操作員）透過此控制台管理 AI Agent 的整個開發生命週期：

- 匯入 BRD / PRD 需求文件，由 AI 自動拆解成 **專案 → 目標 → 任務（Project → Goal → Task）** 三層結構
- 對 AI 產生的草案執行 **人工 signoff 硬閘（hard gate）** 審批
- 啟動、暫停、續行 Agent 的執行，含 DAG 依賴排程、斷點續行、Token 預算控管
- 監控執行指標、日誌、告警
- 設定模型 / Agent / 執行 / 監控等系統參數

整個介面為**繁體中文（Taiwan market）**，採用 **意象若水 water_green** 設計系統（綠色主調、扁平無陰影風格）。

---

## About the Design Files / 關於設計檔案

⚠️ **本套件中的檔案是用 HTML 製作的「設計參考稿」（design reference / prototype）**，用來展示介面的**外觀與互動行為**，**不是**可直接複製進產品的程式碼。

你的任務是：在**目標程式碼庫的既有技術環境**（依需求文件描述，生產目標為 **Next.js 16 App Router + Tailwind 4 + shadcn/ui + Tremor 圖表**）中，用其既有模式與元件庫，**重新實作（recreate）**這些 HTML 設計稿；若目前尚無前端環境，則選擇最合適的框架建立並實作。

請勿直接出貨這個 HTML 檔。它使用了一套內部的模板執行階段（`support.js` + `.dc.html` 自訂格式），那只是設計工具的產物，與生產無關。

### 如何開啟設計稿預覽
在瀏覽器直接開啟 `Agent Console.dc.html` 即可看到完整可互動的原型（所有導航、表單、執行模擬、toast 都可操作）。

### 畫面截圖（`screenshots/`）
各主畫面的完整截圖（每張為單一畫面的整頁，已縮放至完整可見）：

| 檔案 | 畫面 |
|---|---|
| `01-dashboard.png` | 總覽儀表板 |
| `02-projects.png` | 專案管理（清單 + 工具列 + 分頁） |
| `03-project-detail.png` | 專案詳情 |
| `04-goal-detail.png` | 目標詳情 |
| `05-task-detail.png` | 任務詳情（含執行日誌） |
| `06-import.png` | BRD / PRD 智能匯入 |
| `07-execute.png` | 專案執行（控制 + DAG + 即時日誌 + 待審核） |
| `08-monitor.png` | 專案監控（指標 + 趨勢圖 + 告警） |
| `09-settings.png` | 系統參數設定 |

---

## Fidelity / 保真度

**High-fidelity（hifi）** — 像素級定稿：顏色、字體、間距、圓角、互動狀態都已最終確定。
開發者應依本文件與設計系統 token，用程式碼庫既有的元件庫**像素級重建** UI。所有色票、字級、間距皆對應下方「Design Tokens」清單與 `_ds/` 內的 CSS 變數。

---

## 全域版面結構（Global Layout）

固定高度的三段式直向版面（`height:100vh; overflow:hidden`），由上而下：

1. **Topbar（公告列）** — 高 34px，深綠 `#336A29`，白字，字級 12px。左側：說明文件 / 下載 CLI / GitHub / `Engine Bridge · 已連線`（含綠點 `#9fe08a`）。右側：通知總覽 / 幫助中心 / 繁體中文 / 使用者徽章（白底圓形 18px，綠字「K」+ `koala005`）。分隔線為 `opacity:.35` 的 `|`。
2. **Masthead（主導覽列）** — 較淺綠 `#498428`，內距 `18px 24px 16px`，三欄 flex（`gap:32px`）：
   - **Logo**：白底 46×46 圓角 12px 方塊內含 `bot` 圖示（綠 `#498428`），右側兩行文字「AISDLC Console」（21px/700）+「AGENT CONTROL PANEL」（11px、`letter-spacing:2px`、`opacity:.85`）。點擊回到 dashboard。
   - **SearchBar**：白底圓角 8px、高 46px。左為 input（placeholder「搜尋專案、目標、任務…」），右為綠色搜尋按鈕（`search` 圖示）。下方一排 recent chips（透明按鈕、12px 白字）。
   - **Actions**：通知鈴（44px 圓鈕，右上紅色 `#E55B3C` badge「3」）＋ signoff 佇列按鈕（52px 半透明白底圓鈕 `rgba(255,255,255,.14)`，`clipboard-check` 圖示，紅 badge 顯示 `draftCount`）。
3. **Body** — 置中、`max-width:1440px`，內距 24px，左右兩欄 `gap:32px`：
   - **Sidebar（左欄）**：寬 240px，**透明背景無卡片無邊框**（blends into page floor）。頂部「導航」標題（含 `layout-grid` 圖示）+ 1px 分隔線，下接 nav 項目按鈕清單；再下方「我的專案」rail（可由 `showProjectRail` 開關）。
   - **Main（右欄）**：`flex:1`，可垂直捲動，依 `view` 狀態切換顯示九種畫面之一。

頁面底色 `#F5F7F2`，卡片白底 `#FFFFFF`、圓角 12px、`1px solid #DCE3D6` 邊框、**無陰影**（depth 僅靠邊框與底色階差）。預設字體 `var(--font-sans)`（Inter + Noto Sans TC）。

### Sidebar nav 項目
每項：整寬按鈕，`padding:11px 12px`，左側 4px 色條（`border-left`，active 時為主色），16px/500 文字＋ 18px 圖示。hover 背景 `var(--color-tertiary)` `#E4EFD9`。導航項目（推測）：總覽儀表板、專案管理、匯入、執行、監控、設定。

「我的專案」rail 每項：左側 8px 狀態圓點（顏色依狀態）＋ 專案名（單行省略）。

---

## Screens / Views（九種主畫面，由 `view` state 控制）

狀態值：`dashboard` · `projects` · `projectDetail` · `goalDetail` · `taskDetail` · `import` · `execute` · `monitor` · `settings`。

### 1. Dashboard（總覽儀表板，`dashboard`）
- **標題列**：H2「總覽儀表板」30px/700 + 副標 15px muted；右側主色按鈕「匯入 BRD / PRD」（`upload` 圖示）。
- **KPI 卡 ×4**（grid `repeat(4,1fr)`，gap 24px）：每卡白底圓角 12px，內距 20px。頂部 label（14px muted）＋右上 34px 圓角方塊（`#E4EFD9` 底，主色圖示，依序 `circle-check-big` / `list-checks` / `flame` / `clipboard-check`）。中間數值 32px/700。底部 delta（13px，顏色依正負）。
- **下半部**（grid `1.6fr 1fr`，gap 24px）：
  - **進行中的執行** 卡：標題 + 「查看全部專案 →」連結。每列：專案名（可點）＋狀態（含 `wg-blink` 閃爍圓點）＋ 8px 進度條（主色填充）＋ 進度文字與百分比。
  - **待人工審批** 卡：標題 + 紅色計數 badge（`draftCount`）。說明「AI 草案 signoff 硬閘 — 未審批禁止執行」。每列：草案名 + meta + ghost「審批」按鈕。

### 2. Projects（專案管理，`projects`）
- 標題「專案管理」+ 副標「Project → Goal → Task 三層管理 · 共 N 筆」；右側「匯入」(ghost) + 「新建專案」(solid, `plus`)。
- **Toolbar**（白底圓角 8px，`padding:10px 14px`，flex）— 仿 storefront 控制列：
  - 「篩選」標籤（`sliders-horizontal` 圖示）｜分隔線｜狀態 tab 群（每 tab `padding:7px 16px` 圓角 8px，active 主色底白字，非 active 白底）｜彈性間隔｜排序 `<select>`（`.wg-sel` 自訂下拉箭頭）｜分隔線｜mini 分頁器（`page / totalPages` + 左右 IconButton）。
  - 狀態 tab：全部 / 草稿 / 就緒 / 執行中 / 完成 / 失敗（對應 PS 狀態）。
- **專案卡清單**（flex column，gap 16px）：每卡白底，含 48px 圓角方塊（`folder` 圖示）＋ 專案名（可點）＋狀態圓點與文字 ＋「未審批」紅標籤（草案時，`#fdeee9` 底）＋ meta 行（`Lv.N 自治`、`目標 N`、`任務 done/total`、`更新 日期`、等寬字體執行路徑）＋ 右側 4 個 ghost 按鈕：查看 / 編輯 / 執行 / 監控。
- **底部分頁器**：44px 方鈕，左右箭頭 + 頁碼（active 主色底白字）。

### 3. Project Detail（專案詳情，`projectDetail`）
- 返回連結（`arrow-left`「返回專案列表」）。
- 標題列：48px 方塊（`folder`）＋專案名 28px/700＋狀態。下方 meta 行（自治等級、目標·任務數、更新、建立者），左縮排 62px。
- **Signoff 警示橫幅**（草案時顯示）：`#fdeee9` 底、`#f3c7bb` 邊框、`shield-alert` 圖示（accent 色）＋「AI 草案 — 待人工 signoff 硬閘」說明 ＋「審批 signoff」按鈕。
- **兩欄卡**（grid `1fr 1fr`）：左「基本資訊」（執行路徑等寬字體框 + 通過標準 `<ul>`）；右「專案說明」（段落，`line-height:1.7`）。
- **目標清單卡**：標題「目標清單 (N)」+「新增目標」ghost 按鈕。每列：狀態圓點 + 目標名（可點）+ 狀態 + 進度條（max-width 320px）+ `done/total` + 「查看」。
- **底部行動**：執行專案（`play`）／查看監控（`activity`）／編輯專案（`pencil`），後兩者 ghost。

### 4. Goal Detail（目標詳情，`goalDetail`）
- 返回連結（「返回專案」）。標題：44px 方塊（`target`）＋目標名 26px/700＋狀態。meta：所屬專案 / 進度 / 前置依賴。
- 草案警示橫幅（同上，精簡版）。
- 兩欄卡：「目標說明」段落 ／「通過標準」（每項 18px checkbox 方塊，完成時主色底白勾 `check`）。
- 「任務清單 (N)」卡 +「新增任務」；每列：狀態圓點 + 任務名 + 狀態 + 「重試 x/y」+ 「詳情」。
- 底部「編輯目標」ghost。

### 5. Task Detail（任務詳情，`taskDetail`）
- 返回連結（「返回目標」）。標題：44px 方塊（`file-text`）＋任務名 26px/700＋狀態。meta：麵包屑 · 重試 · Agent。
- **指標卡 ×3**（grid，每卡含圖示 label + 等寬字體 24px/700 值）：開始時間（`clock`）／Token 消耗（`flame`）／重試次數（`repeat`）。
- 兩欄卡：「任務說明」／「通過標準」（同 goal）。
- **執行日誌卡**：深色終端機面板 `background:#1c241a`、圓角 8px、等寬字體 13px、文字色 `#d7e4cd`、`max-height:260px` 捲動。
- 底部：重試（`rotate-ccw`）／編輯（`pencil`，ghost）。

### 6. Import（BRD / PRD 智能匯入，`import`）
- `max-width:960px`。標題「BRD / PRD 智能匯入」+ 副標含 🔴（注意：原文用了紅色圓 emoji 字元，實作時改用設計系統圖示或 accent 色點）。
- **步驟 1 卡「輸入來源」**：步驟徽章（綠圓 26px 白字「1」）。來源 tab 群（檔案上傳 / 貼上文字 / URL 之類，每 tab 含圖示）。**拖放區**：`2px dashed` 邊框、圓角 12px、`padding:38px`、置中、`upload-cloud` 圖示 40px（`#80B155`）＋「拖曳檔案至此，或點擊選擇」＋格式說明（.md/.pdf/.docx，10MB）。下方 grid（200px + 1fr）：自治等級 `<select>` + 執行路徑 input。補充說明 `<textarea>`。右下「開始解析」按鈕（`sparkles`，高 44px）。
- **解析中**（`importParsing`）：白卡置中 spinner（`wg-spin`）+ 說明「AI 解析中…（套用有界閘：步驟 ≤24 / Kahn 無環 / prompt 非空）」。
- **步驟 2 卡「結構預覽與編輯」**（`importParsed`）：步驟徽章「2」。樹狀結構預覽（`#F5F7F2` 底框）：專案 → 目標 → 任務縮排，各帶 `folder`/`target`/`file-text` 圖示。底部 signoff 警示橫幅（含 `signed_off=false` code），未簽核時顯示「signoff 審批」按鈕，已簽核顯示綠勾「已 signoff」。底部「放棄」(ghost) +「確認匯入」(`check`)。

### 7. Execute（專案執行，`execute`）
- 返回連結。標題「專案執行：{名稱}」（`play` 圖示）+ 副標「漸進式自治 · DAG 排程 · 斷點續行」。
- **執行鎖定橫幅**（`execSignoffBlocked`）：`lock` 圖示，「執行已鎖定 — 草案未 signoff，啟動回 409 Conflict」+「前往審批」。
- **上半兩欄**（grid `1fr 1.2fr`）：
  - 左「執行控制」卡：自治等級 `<select>` + Token 預算（等寬 20px/700）；「執行範圍」checkbox 清單（自訂 20px 方塊，勾選主色底）；按鈕列依狀態切換：啟動執行 / 暫停 / 恢復 + 取消（`square`）+ 從斷點恢復（`history`），皆 ghost 除主動作外。
  - 右欄上下兩卡：「執行進度」（Run #3 + 狀態閃點 + 任務進度條 + Token 進度條，超閾值變色）；「DAG 依賴視覺化」（橫向 G1→G2→G3 節點，完成=主色實底、進行中=tertiary 底主色邊、待處理=灰底，節點間 `───` 連線，可橫向捲動）。
- **即時日誌卡**：深色終端機 `#1c241a`、高 240px、自動捲到底（`exec-log` id）、標頭含「SSE 串流」狀態點。
- **待審核項目卡**：標題 + accent 計數 badge。每列：`alert-triangle`（`#F5A623`）+ 標題 + 四按鈕：通過(solid) / 重試 / 跳過 / 拒絕（後三 ghost）。無項目時顯示空狀態文字。

### 8. Monitor（專案監控，`monitor`）
- 返回連結。標題「專案監控：{名稱}」（`activity` 圖示）+ 右側時間範圍 `<select>`（預設 24h）。
- **指標卡 ×4**：完成率 34.8%（↑綠）／任務成功率 92.3%（↓ error 紅）／重試率 7.7%（↑ accent）／Token 消耗 45,230（↑ accent）。數值 30px/700。
- **Token 使用趨勢卡**：內嵌 `<svg viewBox="0 0 720 200">` 折線圖 — 虛線預算線（`#DCE3D6`）、主色 polyline（`#498428`，stroke 2.5）、`opacity:.08` 填充面積、軸標籤（`#7A8775` 11px）。
- **兩欄**：「任務狀態分佈」（水平條 bar：完成 #498428 / 執行中 #80B155 / 失敗 #D35B58 / 待處理 #A6B0A1）；「執行時間分佈」（垂直柱狀，最高值用主色其餘 secondary）。
- **執行日誌查詢卡**：右上 level `<select>`（全部/INFO/WARN/ERROR）；`#F5F7F2` 底等寬日誌，每列：時間 muted + level（顏色依等級，寬 48px）+ 訊息。
- **告警卡**：每列 `#fef7ea` 底 `#f5e2bd` 邊、`alert-triangle`（#F5A623）+ 時間 + 訊息 + 「已確認」或「確認」ghost 按鈕。

### 9. Settings（系統參數設定，`settings`）
- 標題「系統參數設定」（`settings` 圖示）+ 右側「匯出設定」「匯入設定」(ghost)。
- **設定分類 tab 群**：模型 / Agent / 執行 / 監控 / AutoClaude / SDD（每 tab 含圖示，active 主色）。
- **參數卡**：每參數一列 grid（220px label/desc + 1fr 控制項）。控制項依 `type` 渲染：
  - `text` / `number` → `.wg-input`（高 44px、圓角 8px）
  - `password` → input + 顯示/隱藏切換按鈕（`onToggleApiKey`，文字 `eyeLabel`）
  - `enum` → `.wg-sel` `<select>`
  - `bool` → 自訂 toggle 開關（46×26px 圓角膠囊，knob 20px，開啟主色底）
  - 每列尾端「重置」IconButton（`rotate-ccw`）；驗證錯誤以 error 紅字顯示。
- 模型 tab 額外有「測試連線」按鈕（`plug`），測試中/成功（綠勾「連線成功（延遲 230ms）」）狀態。
- **修改歷史卡**：等寬字體列出 `時間 / 參數 / 舊值 → 新值 / @使用者`。
- 底部：「儲存變更」(`check`) +「全部重置為預設值」(ghost)。

### 全域覆蓋層
- **Dialog（建立 / 編輯 modal）**：`rgba(42,54,38,.32)` 遮罩，白卡寬 560px、圓角 12px、`max-height:88vh` 捲動。頭部標題 + 關閉 IconButton；身體：名稱 input + （專案才有）執行路徑 input + 說明描述 textarea (Markdown) + 通過標準 textarea (Markdown) + （條件）數值 input（自治等級 / 最大重試）；底部 取消(ghost) + 儲存(`check`)。點遮罩關閉，點卡片 `stopPropagation`。
- **Toast**：底部置中，`var(--color-text-main)` 深底白字，圓角 8px，`check-circle` 綠勾（`#9fe08a`）+ 訊息。
- **載入 spinner**（`notReady`，等待 `window.lucide`）：全螢幕置中 `wg-spin` 轉圈。

---

## Interactions & Behavior / 互動與行為

- **導航**：`nav(view, patch)` 切換 `view` state，並把 `main` 捲回頂部。sidebar、卡片標題、麵包屑返回鍵都觸發導航。
- **搜尋**：受控 input，Enter 或點按鈕送出（`onSearchSubmit`），recent chips 點擊填入。
- **分頁**：projects 清單前端分頁（`page` / `totalPages` / `pagedProjects`），mini 與底部 pager 共用 `onPrevMini`/`onNextMini`/頁碼。
- **篩選與排序**：狀態 tab 切換過濾 + `<select>` 排序，`resultCount` 反映結果數。
- **Signoff 硬閘（核心業務規則）**：`signedOff=false` 的專案 / 目標為「草案」。
  - 啟動執行前檢查：`startExec()` 若 `!p.signedOff` → `flash('草案未經人工審批，禁止執行 (409)')` 並中止。
  - 審批動作把 `signedOff` 設為 true 並 toast。匯入流程須先 signoff 才能「確認匯入」。
- **匯入解析模擬**：`doParse()` 設 `importParsing=true`，1600ms 後 `importParsed=true`。`confirmImport()` 要求 `importSignedOff` 為真。
- **執行模擬**：`startExec()` 啟動 `setInterval`（Run #3），逐步推進進度 / Token / 附加日誌行；`componentDidUpdate` 在 execute 視圖時把 `exec-log` 捲到底。暫停 / 恢復 / 取消 控制 `exec.running`/`paused`。
- **Dialog**：`openDialog(mode, entity, id)`，edit 時預填來源資料；`saveDialog()` 驗證名稱非空（否則 `flash('名稱不能為空')`），寫回 state。
- **Toast**：`flash(msg)` 顯示 toast，`setTimeout` 後自動消失（`this._toast`）。
- **設定**：參數受控編輯，`isModelTab` 顯示測試連線；API Key 顯示切換。
- **計時器清理**：`componentWillUnmount` 清掉所有 interval/timeout（`_li`/`_lf`/`_run`/`_toast`/`_pt`）。

### Motion / 動效（設計系統規範）
- 全域 `transition: all 0.2s ease-out`。
- hover **僅**改變顏色 / 透明度（`opacity .85` 或 ±5% 亮度）；**禁止** translateY 位移、陰影浮起、按壓縮放。
- 自訂 keyframes：`wg-blink`（狀態點呼吸，1.4s）、`wg-fade`、`wg-spin`（loading 0.8s linear）。
- 進度條 / Token 條 `transition: width .4s`。

### Focus / 鍵盤可及性
- 強制鍵盤焦點環：`outline: 2px solid var(--color-primary); outline-offset: 2px`。input/textarea/select focus 同時把邊框轉主色。**禁止** `outline:none` 不補替代。

---

## State Management / 狀態

主要由單一元件的 `this.state` 持有（生產應拆成適當的 store / context / server state）：

- `view` — 當前畫面（九種之一）
- `appReady` / `notReady` — 圖示庫（lucide）是否就緒
- `projects[]` / `goals[]` / `tasks[]` — 三層領域資料（含 `signedOff`、`status`、`autonomyLevel`、`retryCount/maxRetries`、`descParas[]`、`passList[]`、`log[]` 等）
- `projectId` / `goalId` / `taskId` — 當前選取
- `search` / `page` / `sort` / 狀態篩選 — 清單檢視狀態
- `exec` — 執行狀態（`running`、`paused`、`logs[]`、進度、token）
- `import*` — 匯入流程（`importParsing`、`importParsed`、`importSignedOff`、`importAutonomy`、`importPath`、`importPrompt`）
- `dialog` — modal 狀態（`open`、`mode`、`entity`、`form{name,path,desc,pass,num}`）
- `toast` — 當前 toast 訊息
- `configs` — 六大類系統參數（見下方資料模型）
- `settingsTab` / API Key 顯示 / 連線測試 等 UI 旗標

### 資料模型（領域）
**Project → Goal → Task** 三層，外加 status enum 與 config：

- **Project**：`{id, name, status, autonomyLevel(1-10), executionPath, goalsCount, tasksCount, tasksDone, updatedAt, signedOff, createdBy, descParas[], passList[]}`
- **Goal**：`{id, projectId, name, status, sortOrder, signedOff, dependsOn[], descParas[], passList[{t,done}]}`
- **Task**：`{id, goalId, name, status, sortOrder, signedOff, retryCount, maxRetries, assignedAgent?, actualTokens?, startedAt?, descParas[], passList[{t,done}], log[]}`

**狀態 enum（值 → [中文標籤, 顏色]）**：
- Project（PS）：`DRAFT`草稿`#7A8775` · `READY`就緒`#80B155` · `EXECUTING`執行中`#498428` · `COMPLETED`完成`#498428` · `FAILED`失敗`#D35B58` · `ARCHIVED`封存`#A6B0A1`
- Goal（GS）：`PENDING`待處理`#A6B0A1` · `IN_PROGRESS`進行中`#498428` · `COMPLETED`完成`#498428` · `FAILED`失敗`#D35B58` · `SKIPPED`跳過`#A6B0A1`
- Task（TS）：`PENDING`待處理 · `QUEUED`排程中`#80B155` · `BLOCKED`阻塞`#F5A623` · `RUNNING`執行中`#498428` · `VALIDATING`驗證中`#80B155` · `COMPLETED`完成 · `FAILED`失敗`#D35B58` · `ESCALATED`待人工`#E55B3C` · `PAUSED`暫停`#7A8775` · `SKIPPED`跳過 · `CANCELLED`取消

**系統設定（configs）六大類**（每項 `{key, label, type, value, opts?, desc}`，type ∈ text/number/password/enum/bool）：
- `model.*`：provider(enum)、apiUrl、apiKey(password)、name、maxTokensPerRequest、temperature、topP、timeout、rateLimitPerMinute
- `agent.*`：defaultAutonomyLevel、maxConcurrentTasks、taskTimeout、maxRetries、retryBackoffMs、retryBackoffMultiplier、checkpointInterval、enableAutoMutation(bool, Lv6+)、enableSelfEvolution(bool, Lv7+)
- `execution.*`：globalTokenBudget、tokenBudgetWarningThreshold、maxParallelGoals、dagSchedulerStrategy(enum)、enableRollback(bool)、logRetentionDays、compactThresholdPct、haltThresholdPct（SEC-05：halt 必須 > compact）
- `monitor.*`：refreshIntervalMs、alertConsecutiveFailures、alertAgentTimeoutSec、alertTaskDurationMultiplier、enableEmailNotification(bool)、notificationEmail
- `autoclaude.*`：engineUrl、healthCheckPath、eventBusType(enum)、dalBackend(enum)、playbookPath
- `sdd.*`：engineUrl、specFormat(enum)、workflowEngine(enum)、validationLevel(enum)

> 註：原型中資料為前端寫死的 mock。生產應接後端 REST + SSE（需求描述為 Engine Bridge 旁車 `:8081`，`/autoclaude` 與 `/sdd` 路徑前綴）。

---

## Design Tokens / 設計 token

完整定義在 `_ds/.../tokens/*.css`（以 CSS 變數提供）。重點值：

### Colors（顏色）
| Token | Hex | 用途 |
|---|---|---|
| `--color-primary` | `#498428` | CTA、active 區塊、進度條、焦點環、價格 |
| `--color-secondary` | `#80B155` | 次要、hover 對比、柱狀圖 |
| `--color-tertiary` | `#E4EFD9` | sidebar-active 底、輕量標籤底、圖示方塊底 |
| `--color-accent` | `#E55B3C` | 折扣/注意/告警、cart-badge、升級人工 |
| `--color-bg-base` | `#F5F7F2` | 頁面底色 |
| `--color-bg-surface` | `#FFFFFF` | 卡片/面板 |
| `--color-topbar-bg` | `#336A29` | 公告列（較深、退後） |
| `--color-header-bg` | `#498428` | 主導覽列（較淺、前進） |
| `--color-text-main` | `#2A3626` | 主文字 |
| `--color-text-muted` | `#7A8775` | 次要文字 |
| `--color-border` | `#DCE3D6` | 1px 邊框/分隔線 |
| `--color-success` | `#498428` | 成功 |
| `--color-warning` | `#F5A623` | 警告/低庫存/星級 |
| `--color-error` | `#D35B58` | 驗證/失敗 |
| `--color-disabled-bg` / `-text` | `#E8EBE5` / `#A6B0A1` | 停用 |
| `--color-primary-strong` | `#336A29` | solid 按鈕 hover |
| `--color-accent-strong` | `#C9492B` | accent hover |
| 終端機面板底 | `#1c241a` | 日誌深色面板 |
| 終端機文字 | `#d7e4cd` | 日誌文字 |
| 草案警示底 / 邊 | `#fdeee9` / `#f3c7bb` | signoff 警示橫幅 |
| 告警底 / 邊 | `#fef7ea` / `#f5e2bd` | monitor 告警 |

### Typography（字體）
- 字族：**Inter + Noto Sans TC**（`--font-sans`）；數字/Latin 用 Inter；等寬用 **JetBrains Mono / monospace**（路徑、Token、日誌、指標值）。
- 標題 600/700，line-height ~1.35（緊湊 CJK）；內文 16px / 400 / 1.65；介面標籤 14–16px / 500。
- 觀察到的字級：H2 標題 28–30px/700、卡片 H3 18px/600、KPI 數值 32px/700、監控指標 30px/700、指標值 24px/700、內文 15px、meta/說明 13–14px、topbar 12px、caption 11–12px。
- 文字測量寬上限 ~800px。

### Spacing & Layout（間距與版面）
- 嚴格 8pt grid：4/8/16/24 · 32/48/64 · 80/120/160。
- 容器 max 1440px；左欄固定 240px，與內容間距 32px；卡片內距常見 20–22px。
- **反疊加規則**：列出的值即最終視覺間距，不要 parent gap 再加 child margin。

### Radius（圓角）
- 4px：active 小 chip、checkbox 方塊
- 8px：按鈕 / input / select / 控制列 / 終端機面板
- 10–12px：卡片、圖示方塊、產品圖、modal
- full（9999px）：頭像、狀態圓點、通知 badge、toggle 膠囊
- **禁止** 對按鈕 / 卡片用 full-round。

### Elevation（立體感）
- **完全扁平**：無 box-shadow、無 drop-shadow、無漸層、無 3D。
- 深度只靠：`1px solid var(--color-border)` ＋ bg-base/bg-surface 色階 ＋ 8pt 留白。

---

## Iconography / 圖示

- **單一來源：Lucide line icons**。規格：`viewBox 0 0 24 24`、`stroke-width 1.5`、`stroke-linecap/linejoin: round`、`fill:none`。**禁止** solid/filled、禁止手寫 SVG path。
- 原型用一個自包含的 `WgIcon.js`（內嵌全套所用 Lucide path 資料，可離線渲染真實 SVG，CDN 在線時改用其權威資料）。**生產請直接用 `lucide-react`**（`import { ShoppingCart } from 'lucide-react'`）。
- 本控制台用到的圖示（glyph 名稱）：`bot`、`search`、`bell`、`circle-help`、`globe`、`clipboard-check`、`layout-grid`、`upload`、`circle-check-big`、`list-checks`、`flame`、`folder`、`sliders-horizontal`、`chevron-left/right`、`plus`、`arrow-left`、`target`、`file-text`、`shield-alert`、`check`、`check-circle`、`play`、`pause`、`square`、`history`、`activity`、`pencil`、`clock`、`repeat`、`rotate-ccw`、`upload-cloud`、`sparkles`、`lock`、`alert-triangle`、`settings`、`download`、`plug`、`x`。
- **Emoji / unicode 圖示：原則上不使用**（設計系統規範）。原型中匯入頁副標與部分日誌行出現了 emoji（🔴🚀✅❌🔄🛑⚙️📋），實作時建議改用 Lucide 圖示或 accent 色點以符合規範。

---

## Components（設計系統元件，須對應到目標環境的元件庫）

原型直接使用 water_green 設計系統元件（透過全域 namespace `WaterGreenDesignSystem_32a61f` 掛載）。生產請以程式碼庫中**對等的 shadcn/ui 元件**重建：

- **Button** — 扁平品牌按鈕。`variant="solid"`（CTA / active）或 `"ghost"`（低強調）；`size="sm"`；`iconLeft="<lucide>"`。
- **IconButton** — 純圖示按鈕。`icon`、`label`（無障礙）、`variant`（ghost/solid/circular）、`size`。
- **Dropdown** — open-to-activate 的排序/單選。
- **Badge** — cart / 通知計數（`count`、`floating`）。
- **Tag** — 扁平標籤 chip（promo / logistics / feature / rating）。
- **Input** — 文字欄位，8px 圓角、muted placeholder、平滑狀態轉場。
- **Avatar** — 圓形、白底、主色字首/圖示。
- **Pagination** — 超大扁平底部分頁器。
- **SidebarItem** — 左側分類列項（透明容器，無卡無邊框）。
- **Divider / Skeleton / Icon** — 1px 分隔線 / 扁平灰 placeholder（僅 opacity pulse）/ Lucide 圖示渲染器。

> 完整元件 props 與用法見設計系統來源 `/projects/32a61f8d-c43f-4714-bd5c-1f00791c0297/components/`。

---

## Assets / 資產

- **`_ds/`**：water_green 設計系統的 token CSS（`tokens/*.css`）、`styles.css`、與 `_ds_bundle.js`（元件 bundle）。生產應改用程式碼庫既有的設計系統，不要照搬此 bundle。
- **`WgIcon.js`**：原型用的 Lucide 圖示元件，**內嵌 path 資料、可離線渲染**（無需 fetch / CDN）。生產改用 `lucide-react`。
- **`support.js`**：設計工具的模板執行階段，**與生產無關**，僅供原型在瀏覽器開啟用。
- **字體**：Inter + Noto Sans TC 由 Google Fonts CDN 載入；上線請自託管以離線。
- **無真實品牌 logo**：原型用 `bot` 圖示 + 文字鎖定當 placeholder。
- 無真實產品圖片（此為內部工具，非電商）。

---

## Files / 檔案清單

- `Agent Console.dc.html` — 完整設計原型（在瀏覽器直接開啟可預覽全部畫面與互動）。所有畫面、版面、資料 mock、互動邏輯都在此單檔內。
- `WgIcon.js` — Lucide 圖示元件（自包含、可離線，參考用）。
- `_ds/` — 設計系統 token 與 bundle（顏色/字體/間距/圓角的權威來源）。
- `support.js` — 設計工具執行階段（僅供預覽，勿移植）。
- `screenshots/` — 九張主畫面整頁截圖（見上方對照表）。
- `README.md` — 本文件。

---

## 實作建議（給開發者）

1. **資料層**：把三層領域模型（Project/Goal/Task）與 status enum 落為型別/schema；接後端 REST + SSE（Engine Bridge `:8081`）。前端 mock 僅供參考形狀。
2. **路由**：九個主畫面對應 App Router 路由（如 `/`, `/projects`, `/projects/[id]`, `/goals/[id]`, `/tasks/[id]`, `/import`, `/projects/[id]/execute`, `/projects/[id]/monitor`, `/settings`）。
3. **signoff 硬閘**：前端阻擋僅為體驗，**後端必須二次校驗**（未簽核啟動回 409）。
4. **即時性**：執行日誌與監控指標走 SSE；原型用 setInterval 模擬，請替換為真實串流。
5. **圖表**：監控頁的趨勢/分佈圖原型用手繪 SVG，生產建議用 Tremor（需驗證與 Tailwind 4 相容性）。
6. **設計系統**：嚴格遵循扁平無陰影、綠色主調、8pt grid、Lucide 圖示、強制焦點環；用 shadcn/ui 視覺覆寫對齊本 token 表。
