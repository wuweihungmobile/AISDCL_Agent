# AISDLC-SDD v0.01 教學模式
# Tutorial Mode

**框架版本**: v0.01
**建立日期**: 2025-11-03（更新至 v0.01）
**最後更新**: 2026-06-06
**用途**: Learning-by-Doing 互動式教學，降低學習曲線

---

## 🎯 設計目標

```yaml
goals:
  - 新手 30 分鐘內上手
  - 邊做邊學，無風險實驗
  - 漸進式揭露複雜度
  - 即時反饋與糾正

learning_outcomes:
  - 理解 AISDLC 核心流程
  - 掌握各情境適用場景
  - 學會使用 Agents 協作
  - 能獨立完成標準專案
```

---

## 1. Tutorial Mode 架構

### 1.1 三級漸進式學習

```yaml
level_1_essentials:
  name: 基礎入門 (30 分鐘)
  target: 完全新手
  coverage: 核心 5 步驟
  practice_project: Todo App (最簡單)
  learning_goals:
    - 理解 AISDLC 基本流程
    - 學會啟動和執行
    - 產出第一個 PRD

level_2_standard:
  name: 標準流程 (2 小時)
  target: 已完成 Level 1
  coverage: 完整流程 (8-10 步驟)
  practice_project: Blog Platform (中等複雜度)
  learning_goals:
    - 掌握完整文檔產出流程
    - 理解 Agent 協作模式
    - 學會使用 Smart Defaults

level_3_advanced:
  name: 進階技巧 (4 小時)
  target: 已完成 Level 2
  coverage: 所有選項和客製化
  practice_project: E-commerce Platform (複雜)
  learning_goals:
    - 掌握所有 10 個情境
    - 學會客製化配置
    - 理解錯誤預防和恢復
    - 使用 Checkpoint 和分支

progressive_disclosure:
  principle: 不一次性展示所有複雜度
  strategy: |
    Level 1: 只教核心流程，隱藏進階選項
    Level 2: 展示完整流程，提及進階功能
    Level 3: 開放所有功能，教授最佳實踐
```

---

## 2. Tutorial 啟動方式

### 2.1 啟動指令

```yaml
activation:
  command_format: AISDLC tutorial [scenario] [level]

  examples:
    - AISDLC tutorial greenfield
    - AISDLC tutorial greenfield level1
    - AISDLC tutorial integration level2
    - AISDLC tutorial (顯示 Tutorial 選單)

  automatic_detection:
    description: 新使用者首次使用時自動推薦
    prompt: |
      👋 歡迎使用 AISDLC-SDD v0.01!

      檢測到您是首次使用。

      建議:
      [1] 開始 30 分鐘互動教學 (推薦給新手)
      [2] 查看快速入門指南
      [3] 直接開始使用 (熟悉類似工具)

      您的選擇:
```

---

### 2.2 Tutorial 選單

```yaml
tutorial_menu:
  display: |
    🎓 AISDLC Tutorial Mode

    請選擇您想學習的情境:

    **入門級 (30 分鐘)**:
    [1] Greenfield - 新專案開發 ⭐ 推薦新手
    [2] Integration - 第三方 API 整合

    **進階級 (1-2 小時)**:
    [3] Brownfield - 既有專案維護
    [4] Performance - 效能優化
    [5] Refactoring - 系統重構

    **專家級 (2-4 小時)**:
    [6] 完整流程 - E-commerce 專案 (涵蓋多個情境)

    **其他**:
    [7] 查看我的學習進度
    [8] 繼續上次未完成的 Tutorial
    [9] 返回主選單

    您的選擇:

  smart_recommendation:
    based_on:
      - 使用者背景 (如有提供)
      - 已完成的 Tutorials
      - 當前專案需求

    example: |
      根據您的背景 (前端開發者，React 經驗)，
      建議從以下 Tutorial 開始:

      ⭐ Greenfield Web - 新專案開發 (最相關)
      ⭐ Integration - API 整合 (常用技能)
```

---

## 3. Level 1: 基礎入門教學

### 3.1 Tutorial 專案: Todo App

```yaml
project_overview:
  name: Todo App
  description: 簡單的待辦事項應用
  features:
    - 新增待辦事項
    - 標記完成/未完成
    - 刪除待辦事項
  tech_stack:
    frontend: React (預設)
    backend: Node.js Express (預設)
    database: SQLite (最簡單)
  estimated_time: 30 分鐘
  complexity: ⭐ (1/5)

tutorial_flow:
  step_1_welcome:
    duration: 2 分鐘
    content: |
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      🎓 Tutorial 1/5: 歡迎來到 AISDLC
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      您將學會:
      ✅ 使用 AISDLC 規劃一個 Todo App
      ✅ 產出第一份 PRD (產品需求文檔)
      ✅ 理解 AI Agents 如何協助您

      專案簡介:
      我們要做一個簡單的 Todo App (待辦事項應用)。
      功能包含: 新增、完成、刪除待辦事項。

      ⏱️ 預估時間: 30 分鐘
      💡 隨時可以暫停或重來

      [開始 Tutorial] [返回選單]

  step_2_scenario_selection:
    duration: 3 分鐘
    content: |
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      🎓 Tutorial 2/5: 情境識別
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      📚 知識點:
      AISDLC 支援 10 種開發情境。
      不同情境有不同的流程和文檔。

      對於「從零開始的新專案」，我們使用:
      ✅ Greenfield 情境

      其他常見情境:
      - Brownfield: 修改既有系統
      - Integration: 整合第三方 API
      - Performance: 優化效能

      🎯 您的任務:
      Todo App 是新專案，應該選擇哪個情境?

      [1] Greenfield (新專案開發) ← 正確答案
      [2] Brownfield (既有專案維護)
      [3] Integration (第三方整合)
      [?] 我不確定

    feedback_correct: |
      ✅ 正確! Greenfield 用於從零開始的新專案。

      AI 已自動載入:
      - pm-po-agent (Victoria): 產品經理
      - sa-analyst (Amanda): 系統分析師

      他們會協助您分析需求和產出文檔。

      [繼續下一步]

    feedback_wrong: |
      ❌ 不太對喔!

      提示:
      - Brownfield: 用於「既有系統」修改
      - Integration: 用於「第三方 API」整合
      - Greenfield: 用於「全新專案」開發

      Todo App 是從零開始的新專案，所以應該選擇...?

      [重新選擇] [查看說明]

  step_3_requirements_analysis:
    duration: 8 分鐘
    content: |
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      🎓 Tutorial 3/5: 需求分析
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      📚 知識點:
      需求分析是專案的第一步。
      我們會由 PM/PO 和 SA 協作，從業務需求轉化為技術需求。

      🤖 AI Agents 協作:
      - Victoria (PM): 確保符合使用者需求
      - Amanda (SA): 分析技術可行性

      ✍️ 您的任務:
      描述 Todo App 的需求。可以很簡單!

      提示: 想想使用者需要做什麼?
      範例: "使用者可以新增待辦事項、標記完成、刪除"

      請輸入您的需求描述:
      > [使用者輸入]

    ai_analysis_example: |
      使用者輸入: "可以新增、完成、刪除待辦事項"

      🤖 Victoria (PM) 分析:
      「理解了! 我識別到 3 個核心功能:
      1. 新增待辦事項
      2. 標記完成/未完成
      3. 刪除待辦事項

      建議補充:
      - 是否需要「編輯」待辦事項?
      - 是否需要「優先級」或「標籤」?」

      🤖 Amanda (SA) 分析:
      「從技術角度，這是標準的 CRUD 操作:
      - Create: 新增
      - Read: 列表顯示
      - Update: 標記完成
      - Delete: 刪除」

      ✅ 需求已確認!

      [繼續下一步] [修改需求]

  step_4_prd_generation:
    duration: 10 分鐘
    content: |
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      🎓 Tutorial 4/5: 產出 PRD
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      📚 知識點:
      PRD (Product Requirements Document) 是產品需求文檔。
      記錄「要做什麼」，但不是「怎麼做」。

      🤖 AI 會自動產出 PRD，包含:
      - 專案概述
      - 使用者畫像
      - 核心功能
      - 驗收標準

      🔄 正在產出 PRD...

      [3 秒後顯示 PRD 摘要]

      ✅ PRD 已產出!

      # PRD - Todo App

      ## 1. 專案概述
      Todo App 是一個簡單的待辦事項管理應用...

      ## 2. 使用者畫像
      - 一般使用者: 需要記錄日常待辦事項

      ## 3. 核心功能
      - F1: 新增待辦事項
      - F2: 標記完成狀態
      - F3: 刪除待辦事項

      ## 4. 驗收標準
      - 使用者可以成功新增待辦事項
      - 使用者可以切換完成/未完成狀態
      - 使用者可以刪除待辦事項

      [查看完整 PRD] [繼續下一步]

    interactive_element: |
      💡 互動練習:

      PRD 中哪一項描述是「非功能性需求」?

      [1] 使用者可以新增待辦事項
      [2] 應用需在 2 秒內載入
      [3] 使用者可以刪除待辦事項

      您的答案: [?]

      [提示]: 非功能性需求描述「品質屬性」(效能、安全性等)
               而非具體功能。

  step_5_next_steps:
    duration: 5 分鐘
    content: |
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      🎓 Tutorial 5/5: 後續步驟
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

      🎉 恭喜! 您已完成基礎教學!

      您學會了:
      ✅ 選擇適合的情境 (Greenfield)
      ✅ 描述專案需求
      ✅ AI Agents 如何協作分析
      ✅ 產出第一份 PRD

      📊 學習進度:
      Level 1 (基礎): ████████████ 100%
      Level 2 (標準): ░░░░░░░░░░░░ 0%
      Level 3 (進階): ░░░░░░░░░░░░ 0%

      🎯 下一步:

      選項 A: 繼續 Level 2 (標準流程)
        - 學習完整的文檔產出流程 (FRD, SRD, API)
        - 專案: Blog Platform (1-2 小時)

      選項 B: 實際專案練習
        - 使用剛學的知識開始您的專案
        - AI 會在旁邊引導您

      選項 C: 複習 Level 1
        - 重新學習一次，加深印象

      選項 D: 嘗試其他情境 Tutorial
        - Integration Tutorial (API 整合)
        - Performance Tutorial (效能優化)

      您想要: [A/B/C/D]

  completion_badge:
    earned: |
      🏆 獲得成就徽章!

      ✨ AISDLC 新手
      完成 Level 1 基礎教學

      已解鎖:
      - Level 2 標準流程 Tutorial
      - Greenfield 情境完整功能
      - 實際專案執行模式

      [查看所有徽章] [分享成就]
```

---

## 4. Level 2: 標準流程教學

### 4.1 Tutorial 專案: Blog Platform

```yaml
project_overview:
  name: Blog Platform
  description: 部落格平台,支援文章發布和評論
  features:
    - 使用者註冊登入
    - 發布文章 (Markdown 支援)
    - 文章分類和標籤
    - 評論系統
    - 文章搜尋
  tech_stack:
    frontend: React + TypeScript
    backend: Node.js + Express
    database: PostgreSQL
  estimated_time: 1.5-2 小時
  complexity: ⭐⭐⭐ (3/5)

tutorial_structure:
  phase_1_requirements:
    steps:
      - 情境識別與 Agents 載入
      - 需求收集與分析
      - PRD 產出與確認
    duration: 30 分鐘
    learning_focus:
      - 複雜需求的拆解
      - 使用者畫像建立
      - MVP 範圍定義

  phase_2_functional_design:
    steps:
      - User Stories 撰寫
      - Acceptance Criteria 定義
      - FRD 產出
    duration: 40 分鐘
    learning_focus:
      - User Story 格式 (As a... I want... So that...)
      - GIVEN-WHEN-THEN AC 格式
      - 功能優先級排序

  phase_3_technical_design:
    steps:
      - 技術棧選型
      - 架構設計
      - SRD 產出
      - API 規格產出
    duration: 50 分鐘
    learning_focus:
      - 技術決策理由
      - 架構圖繪製 (Mermaid)
      - API 設計最佳實踐
      - Database Schema 設計

key_learning_points:
  user_stories:
    example: |
      ❌ 錯誤範例:
      US-001: 使用者登入

      ✅ 正確範例:
      US-001: 作為部落格訪客，我想要使用 Email 和密碼註冊帳號，
      以便能夠發布文章和留言。

      💡 差異:
      - 明確角色 (部落格訪客)
      - 清楚動作 (Email + 密碼註冊)
      - 說明價值 (發布文章和留言)

    practice: |
      ✍️ 練習: 為「發布文章」功能撰寫 User Story

      提示:
      - 誰會使用這個功能? (角色)
      - 他想做什麼? (動作)
      - 為什麼需要? (價值)

      您的 User Story:
      > [使用者輸入]

      [檢查答案] [查看範例] [需要幫助]

  acceptance_criteria:
    example: |
      ❌ 錯誤範例:
      - 可以登入

      ✅ 正確範例 (GIVEN-WHEN-THEN):
      GIVEN 我是已註冊的使用者
      WHEN 我輸入正確的 Email 和密碼
      THEN 系統應登入成功並跳轉到首頁

      GIVEN 我輸入錯誤的密碼
      WHEN 我點擊登入
      THEN 系統應顯示「密碼錯誤」訊息

      💡 優點:
      - 明確的前置條件 (GIVEN)
      - 清楚的操作 (WHEN)
      - 可測試的結果 (THEN)

  tech_stack_decision:
    example: |
      🤖 sd-architect (Marcus):
      「技術棧推薦:

      Frontend: React + TypeScript
      理由:
      - 生態系完整
      - TypeScript 提供型別安全
      - 適合中大型專案

      Backend: Node.js + Express
      理由:
      - 與前端統一語言 (JavaScript/TypeScript)
      - 非同步 I/O 適合 I/O 密集型應用

      Database: PostgreSQL
      理由:
      - 支援全文搜尋 (文章搜尋功能)
      - JSONB 型別 (靈活的文章內容儲存)
      - 成熟穩定」

      是否接受此推薦?
      [Yes/提出其他選項/了解更多]
```

---

## 5. Level 3: 進階技巧教學

### 5.1 Tutorial 專案: E-commerce Platform

```yaml
project_overview:
  name: E-commerce Platform
  description: 完整電商平台 (跨多個情境)
  scenarios_covered:
    - Greenfield: 核心電商功能
    - Integration: Stripe 支付整合
    - Performance: 產品列表效能優化
    - Security: 支付安全與資料保護
  estimated_time: 4-6 小時
  complexity: ⭐⭐⭐⭐⭐ (5/5)

advanced_topics:
  topic_1_multi_scenario:
    description: 一個專案結合多個情境
    example: |
      專案分階段:
      Phase 1 (Week 1-8): Greenfield 開發核心功能
      Phase 2 (Week 9-10): Integration 整合支付
      Phase 3 (Week 11): Performance 效能優化
      Phase 4 (Week 12): Security 安全強化

      學習: 如何在不同階段切換情境

  topic_2_customization:
    description: 客製化 Smart Defaults
    example: |
      覆寫預設技術棧:
      「改用 Vue.js 而非 React」

      自訂確認點模式:
      「使用 Quick Mode 但保留關鍵確認點」

      建立專案配置檔:
      .aisdlc/config.yaml

  topic_3_checkpoint_branching:
    description: 使用 Checkpoint 和分支實驗
    example: |
      實驗不同架構:
      - Main Branch: Monolithic
      - Experiment Branch: Microservices

      對比後做決策

  topic_4_error_recovery:
    description: 錯誤預防和恢復
    scenarios:
      - Token 超限恢復
      - 文檔追蹤鏈修復
      - Agent 協作衝突解決

  topic_5_team_collaboration:
    description: 團隊協作功能
    practices:
      - Checkpoint 分享
      - Review Pack 產出
      - 協作衝突處理
```

---

## 6. Tutorial Projects 資料集

### 6.1 預設 Tutorial 專案

```yaml
beginner_projects:
  todo_app:
    complexity: ⭐
    duration: 30 min
    scenarios: [greenfield]
    features: [CRUD]
    reference_solution: tutorial_projects/todo_app/

  calculator_app:
    complexity: ⭐
    duration: 30 min
    scenarios: [greenfield]
    features: [基本運算]
    reference_solution: tutorial_projects/calculator/

intermediate_projects:
  blog_platform:
    complexity: ⭐⭐⭐
    duration: 2 hours
    scenarios: [greenfield]
    features: [使用者系統, 文章管理, 評論]
    reference_solution: tutorial_projects/blog/

  api_integration_stripe:
    complexity: ⭐⭐
    duration: 1 hour
    scenarios: [integration]
    features: [支付整合]
    reference_solution: tutorial_projects/stripe_integration/

advanced_projects:
  ecommerce_platform:
    complexity: ⭐⭐⭐⭐⭐
    duration: 6 hours
    scenarios: [greenfield, integration, performance, security]
    features: [完整電商]
    reference_solution: tutorial_projects/ecommerce/

  social_media_app:
    complexity: ⭐⭐⭐⭐
    duration: 4 hours
    scenarios: [greenfield, performance]
    features: [社交網路]
    reference_solution: tutorial_projects/social_media/

reference_solution_structure:
  each_project_contains:
    - README.md (專案說明)
    - PRD_Reference.md (參考 PRD)
    - FRD_Reference.md (參考 FRD)
    - SRD_Reference.md (參考 SRD)
    - common_mistakes.md (常見錯誤)
    - grading_rubric.md (評分標準)
```

---

## 7. 互動式元素

### 7.1 即時反饋

```yaml
feedback_types:
  correct_answer:
    display: |
      ✅ 正確!

      [簡短解釋為什麼正確]

      [繼續下一步]

  wrong_answer:
    display: |
      ❌ 不太對喔!

      [解釋為什麼錯誤]

      💡 提示: [給予提示]

      [重試] [查看答案] [跳過]

  partial_correct:
    display: |
      🟡 部分正確!

      做得好:
      ✅ [正確的部分]

      可以改進:
      🔸 [需改進的部分]

      [查看範例] [修改答案]

practice_exercises:
  scenario_selection:
    question: |
      以下專案應該選擇哪個情境?

      專案: 「將網站登入改用 Google OAuth」

      [1] Greenfield
      [2] Brownfield
      [3] Integration
      [4] Refactoring

    answer: 3
    explanation: |
      正確答案是 Integration (整合)。

      理由:
      - 涉及第三方服務 (Google OAuth)
      - 是「增加」整合，非「從零開發」
      - Integration 情境專注於 API 整合流程

      如果是「從零開發整個登入系統」→ Greenfield
      如果是「重構現有登入代碼」→ Refactoring

  user_story_writing:
    question: |
      為「產品搜尋」功能撰寫 User Story。

      要求:
      - 包含角色、動作、價值
      - 使用 "作為...我想要...以便..." 格式

      您的 User Story:
      > [使用者輸入]

    good_example: |
      作為電商網站訪客，我想要使用關鍵字搜尋產品，
      以便快速找到我需要的商品。

    common_mistakes:
      - 缺少角色: "我想要搜尋產品" (誰?)
      - 缺少價值: "作為使用者，我想要搜尋" (為什麼?)
      - 太技術化: "作為使用者，我想要 Elasticsearch 全文搜尋"
```

---

### 7.2 Progress Tracking

```yaml
progress_display:
  during_tutorial: |
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    🎓 Tutorial 進度: Blog Platform (Level 2)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    整體進度: ████████░░░░ 65% (當前: 步驟 6/10)

    已完成:
    ✅ 情境識別
    ✅ 需求分析
    ✅ PRD 產出
    ✅ User Stories 撰寫
    ✅ FRD 產出
    ✅ 技術棧選型

    進行中:
    🔄 SRD 產出

    待完成:
    ⏳ API 規格產出
    ⏳ 測試計畫
    ⏳ 總結與複習

    預估剩餘時間: 35 分鐘

    [繼續] [暫停Tutorial] [返回選單]

completion_summary:
  display: |
    🎉 Tutorial 完成!

    📊 您的表現:

    準確度: ████████░░ 85%
    - 正確回答: 17/20 題
    - 第一次答對: 14/20 題

    完成時間: 1 小時 45 分鐘
    - 預估時間: 2 小時
    - 效率: 👍 Good

    學習成效:
    - 情境識別: ⭐⭐⭐⭐⭐
    - User Stories: ⭐⭐⭐⭐
    - 技術設計: ⭐⭐⭐

    🏆 獲得徽章:
    ✨ AISDLC 實踐者 (Level 2)

    💾 Tutorial 專案已儲存
    路徑: tutorials/blog_platform_20251024/

    您可以:
    [查看完整專案] [進入 Level 3] [開始實際專案]
```

---

## 8. Tutorial Mode 特色功能

### 8.1 Safe Sandbox

```yaml
sandbox_features:
  no_real_impact:
    description: Tutorial 中的所有操作不影響實際專案
    implementation: |
      Tutorial 專案存在獨立目錄:
      tutorials/[project_name]_[timestamp]/

      與實際專案完全隔離

  unlimited_retry:
    description: 可無限次重試，無懲罰
    example: |
      答錯了? 沒關係!
      - 可以重新回答
      - 查看正確答案
      - 了解為什麼錯誤

  experiment_freely:
    description: 鼓勵實驗不同選項
    example: |
      「想試試看選擇 Vue 而非 React? 試試看!」
      「想看看 Microservices 架構? 建立分支實驗!」
```

---

### 8.2 Context-sensitive Help

```yaml
help_system:
  always_available:
    command: 「幫助」 or 「?」
    response: |
      💡 需要幫助嗎?

      當前步驟: User Story 撰寫

      可用幫助:
      [1] 什麼是 User Story?
      [2] User Story 格式範例
      [3] 常見錯誤
      [4] 查看參考答案
      [5] 跳過此步驟
      [6] 暫停 Tutorial

  contextual_hints:
    trigger: 使用者停留超過 2 分鐘未輸入
    display: |
      💡 提示

      看起來您卡住了? 可以:
      - 輸入「提示」獲得線索
      - 輸入「範例」查看範例
      - 輸入「跳過」跳過此題

  progressive_hints:
    level_1: |
      💡 提示 1: User Story 應包含「角色」、「動作」、「價值」三要素

    level_2: |
      💡 提示 2: 格式是「作為[角色]，我想要[動作]，以便[價值]」

    level_3: |
      💡 提示 3: 範例 - "作為部落格作者，我想要發布文章，以便分享我的想法"

    level_4_answer: |
      💡 參考答案:

      US-002: 作為部落格訪客，我想要搜尋文章，
      以便快速找到我感興趣的內容。
```

---

### 8.3 Gamification Elements

```yaml
achievements:
  badges:
    - name: AISDLC 新手
      requirement: 完成 Level 1
      icon: 🌱

    - name: AISDLC 實踐者
      requirement: 完成 Level 2
      icon: 🎯

    - name: AISDLC 專家
      requirement: 完成 Level 3
      icon: 🏆

    - name: 情境大師
      requirement: 完成所有 10 個情境 Tutorial
      icon: 🌟

    - name: 完美主義者
      requirement: 所有題目第一次答對
      icon: 💎

    - name: 速度狂
      requirement: 在預估時間 50% 內完成
      icon: ⚡

  leaderboard:
    display: |
      🏆 Tutorial 排行榜 (本週)

      1. user@example.com - 3 個 Tutorials, 95% 準確度
      2. developer@example.com - 2 個 Tutorials, 90% 準確度
      3. you@example.com - 1 個 Tutorial, 85% 準確度 ⭐ 你

      [查看完整排行榜] [隱藏排行榜]

  points_system:
    earning: |
      獲得積分:
      - 完成 Tutorial: 100 分
      - 第一次答對: +10 分/題
      - 在時間內完成: +50 分
      - 幫助其他使用者: +25 分

    display: |
      🎯 您的積分: 385 分

      排名: #3 / 50 位使用者
      下一等級: Expert (還需 115 分)

      [查看如何獲得更多積分]
```

---

## 9. Tutorial 最佳實踐

### 9.1 使用時機

```yaml
recommended_for:
  - 完全新手 (必做 Level 1)
  - 切換到新情境 (做該情境 Tutorial)
  - 學習進階功能 (做 Level 3)
  - 團隊培訓 (統一學習路徑)

not_necessary_for:
  - 已熟悉類似工具
  - 時間緊迫的實際專案
  - 只需要查詢特定功能
```

---

### 9.2 Tutorial 後續

```yaml
after_completion:
  apply_knowledge:
    - 立即開始實際專案 (趁記憶猶新)
    - 使用剛學的技能
    - AI 仍會在旁引導

  review_materials:
    - Tutorial 專案保留在 tutorials/ 目錄
    - 可隨時查看參考答案
    - 對比自己的實作與標準答案

  continue_learning:
    - 完成下一個 Level
    - 嘗試其他情境 Tutorial
    - 挑戰進階專案
```

---

## 📚 相關文檔

- [AISDLC_SDD_INIT.md](../../../AISDLC_SDD_INIT.md) - 框架初始化
- [QUICK_START_TEMPLATES.md](QUICK_START_TEMPLATES.md) - 快速啟動範本
- [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) - 快速上手指南
- [scenarios/*/SOP_QuickRef.md](../../../scenarios/) - 情境快速參考

---

**文檔版本**: v0.01
**最後更新**: 2026-06-06
**維護者**: AISDLC-SDD Framework Team
