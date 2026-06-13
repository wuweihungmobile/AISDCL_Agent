# Performance Optimization - 快速參考指南
# Quick Reference Guide

**版本**: v0.01
**閱讀時間**: 5 分鐘
**適用情境**: 系統效能優化、瓶頸排查、效能測試

---

## 🎯 一頁總覽

### 適用場景
✅ 系統回應緩慢
✅ 高負載下效能下降
✅ 需要優化查詢速度
✅ 資源使用率過高（CPU/Memory）

### 不適用場景
❌ 功能開發（請用 Greenfield）
❌ Bug 修復（請用 Brownfield）
❌ 架構重構（請用 Refactoring）

---

## 📋 5 階段快速流程（簡化版）

> 💡 **對應說明**: QuickRef 將完整 SOP 的 7 階段簡化為 5 階段：
> - 階段 1 ≈ SOP 階段 1（啟動）+ 階段 2（基準測試）
> - 階段 2 ≈ SOP 階段 3（瓶頸分析）
> - 階段 3 ≈ SOP 階段 4（優化策略）
> - 階段 4 ≈ SOP 階段 5（優化實施）
> - 階段 5 ≈ SOP 階段 6（驗證）+ 階段 7（監控）
>
> 完整 7 階段流程請參考 [SOP 完整版](./SOP.md)。

```
總時間: 1-2 天

┌─────────────────────────────────────────────┐
│ 階段 1: 效能基準測量 (2-3 小時) 🔴           │
│ └─ 當前效能指標 → 設定目標 → 確認            │
├─────────────────────────────────────────────┤
│ 階段 2: 瓶頸分析 (3-4 小時) 🔴               │
│ └─ Profiling → 熱點識別 → 根因分析          │
├─────────────────────────────────────────────┤
│ 階段 3: 優化策略 (2-3 小時) 🔴               │
│ └─ 方案設計 → 優先級排序 → 風險評估         │
├─────────────────────────────────────────────┤
│ 階段 4: 實施優化 (4-6 小時) 🟡               │
│ └─ 程式碼優化 → 資料庫調整 → 快取策略       │
├─────────────────────────────────────────────┤
│ 階段 5: 驗證與監控 (2-3 小時) 🔴             │
│ └─ 效能測試 → 對比分析 → 持續監控           │
└─────────────────────────────────────────────┘

🔴 Critical: 必須人類確認
🟡 Recommended: 建議確認
✅ Automated: 自動驗證
```

---

## 🚀 快速啟動

### Step 1: 載入框架
```
提示詞:
「請載入 AISDLC-SDD v0.01，我需要效能優化」

或具體描述:
「網站首頁載入慢，需要優化」
「API 回應時間 > 2 秒，需加速」
「資料庫查詢效能問題」
```

### Step 2: 提供效能數據
```
必須提供:
□ 當前效能指標（回應時間/吞吐量/錯誤率）
□ 問題描述（何時變慢？哪個功能？）

建議提供:
□ Profiling 報告
□ 日誌檔案
□ 監控截圖（Grafana/New Relic）
□ 資料庫慢查詢 log
```

---

## 🎯 常見效能問題速查表

### 問題類型快速診斷

| 症狀 | 可能原因 | 快速檢查 | 優先優化 |
|------|---------|---------|---------|
| **首次載入慢** | 資源過大 | Chrome DevTools Network | 壓縮/CDN/Code Splitting |
| **API 回應慢** | 資料庫查詢 | Slow Query Log | 加索引/優化 SQL |
| **高併發崩潰** | 資源不足 | CPU/Memory 使用率 | 橫向擴展/負載均衡 |
| **記憶體洩漏** | 未釋放資源 | Heap Snapshot | 修復記憶體洩漏 |
| **資料庫慢** | 缺索引/N+1 | EXPLAIN 分析 | 加索引/批次查詢 |

---

## ⚡ 快速優化技巧

### 前端優化（立即見效）

```yaml
1. 圖片優化:
   - 使用 WebP 格式（減少 30-50% 大小）
   - 實施 Lazy Loading
   - 使用 CDN

2. JavaScript 優化:
   - Code Splitting（按路由分割）
   - Tree Shaking（移除未使用程式碼）
   - 壓縮 bundle (Terser/UglifyJS)

3. 快取策略:
   - 設定 Cache-Control headers
   - 使用 Service Worker
   - 實施 HTTP/2 Server Push

快速勝利 (Quick Win):
npm run build --analyze  # 分析 bundle 大小
# 找出最大的模組並優化
```

### 後端優化（立即見效）

```yaml
1. 資料庫優化:
   - 加索引（WHERE, JOIN, ORDER BY 欄位）
   - 使用連接池
   - 批次查詢（避免 N+1）

2. API 優化:
   - 實施快取（Redis/Memcached）
   - 壓縮回應（gzip/brotli）
   - 分頁 + 限制回傳欄位

3. 架構優化:
   - 非同步處理（Queue）
   - 負載均衡
   - CDN for static assets

快速勝利 (Quick Win):
# 檢查慢查詢
SELECT * FROM slow_query_log ORDER BY query_time DESC LIMIT 10;

# 檢查缺少的索引
EXPLAIN ANALYZE SELECT ...
```

---

## 📊 效能目標參考

### Web 應用標準

```yaml
頁面載入:
- FCP (First Contentful Paint): < 1.8s  ⭐ Good
- LCP (Largest Contentful Paint): < 2.5s ⭐ Good
- TTI (Time to Interactive): < 3.8s     ⭐ Good
- CLS (Cumulative Layout Shift): < 0.1  ⭐ Good

API 回應:
- P50: < 100ms   (一半請求)
- P95: < 500ms   (95% 請求)
- P99: < 1s      (99% 請求)

資料庫查詢:
- 簡單查詢: < 10ms
- 複雜查詢: < 100ms
- 分析查詢: < 1s
```

### Mobile App 標準

```yaml
啟動時間:
- Cold Start: < 3s
- Warm Start: < 1.5s
- Hot Start: < 0.5s

畫面渲染:
- 60 FPS（16.67ms per frame）
- Jank < 5% frames

網路請求:
- 4G: < 500ms
- 3G: < 2s
```

---

## 🔍 Profiling 工具快速指南

### 前端 Profiling

```bash
# Chrome DevTools
1. 開啟 DevTools (F12)
2. Performance tab → 錄製
3. 操作頁面
4. 停止錄製
5. 分析火焰圖（找最長的 bars）

# Lighthouse (效能評分)
npx lighthouse https://your-site.com --view

# Bundle 分析
npm install -g webpack-bundle-analyzer
webpack-bundle-analyzer dist/stats.json
```

### 後端 Profiling

```bash
# Node.js
node --prof app.js  # 產生 v8.log
node --prof-process isolate-*.log > processed.txt

# 使用 Clinic.js (推薦)
npm install -g clinic
clinic doctor -- node app.js  # 整體診斷
clinic flame -- node app.js   # 火焰圖

# Python
python -m cProfile -o output.prof app.py
snakeviz output.prof  # 視覺化

# Database
# MySQL
SET profiling = 1;
SELECT ...;
SHOW PROFILES;
SHOW PROFILE FOR QUERY 1;

# PostgreSQL
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;
```

---

## ⚠️ 優化陷阱

### ❌ 避免這些錯誤

**1. 過早優化**
```
錯誤: 未測量就開始優化

正確: 先 Profile → 找瓶頸 → 優化 → 驗證
```

**2. 盲目優化**
```
錯誤: 優化非瓶頸部分（浪費時間）

正確: 使用 80/20 法則，優化前 20% 熱點
```

**3. 犧牲可讀性**
```
錯誤: 為了 1% 效能提升寫難懂的程式碼

正確: 效能提升 > 20% 才值得犧牲少量可讀性
```

**4. 未驗證效果**
```
錯誤: 優化後未測量（不知道是否有效）

正確: Before/After 對比測試，量化改善
```

---

## 📈 效能優化優先級

### P0: 立即處理（影響使用者體驗）

```
- 頁面載入 > 5 秒
- API 錯誤率 > 1%
- 資料庫連接耗盡
- 記憶體洩漏（OOM crashes）
```

### P1: 儘快處理（影響商業指標）

```
- 頁面載入 3-5 秒
- API P95 > 2 秒
- 資料庫慢查詢 > 1 秒
- CPU 使用率 > 80%
```

### P2: 計劃處理（優化空間）

```
- 頁面載入 2-3 秒
- API P95 1-2 秒
- 可優化的快取策略
- Code duplication
```

---

## 🎯 成功指標

### 優化完成檢查

```yaml
效能提升:
□ 關鍵指標改善 > 30%
□ P95 延遲降低顯著
□ 錯誤率未上升
□ 資源使用率合理

程式碼品質:
□ 無破壞性變更
□ 測試全部通過
□ Code Review 通過
□ 文檔已更新

監控就緒:
□ 關鍵指標已監控
□ 告警規則已設定
□ Dashboard 已建立
□ Runbook 已準備
```

---

## 📞 需要幫助？

### 常見問題解決

**Q: 不知道從哪開始優化？**
```
A: 使用 Pareto 原則
1. Profiling 找出前 3 個瓶頸
2. 優化最大瓶頸
3. 測量改善
4. 重複
```

**Q: 優化後沒效果？**
```
A: 檢查是否優化了瓶頸
1. 再次 Profile
2. 確認瓶頸已改變
3. 檢查是否有新瓶頸
```

**Q: 優化導致 Bug？**
```
A: 增量優化 + 充分測試
1. 小步快跑（一次改一個）
2. 每次優化後測試
3. 使用 Feature Flag
4. 保留 rollback 方案
```

---

## 🛠️ 可用 Skills 快速參考

### 核心 Skills（所有效能優化皆適用）
| Skill | 用途 | 觸發時機 |
|-------|------|---------|
| `/performance-optimization` | 效能優化情境啟動、前後對比分析 | 階段 1（啟動）、階段 6（驗證） |
| `/brownfield-analysis` | 現有系統效能瓶頸全面分析 | 階段 3 |
| `/dev-review` | 代碼層級效能審查（N+1、演算法） | 階段 3、階段 5 |
| `/sd-architect` | 架構級優化方案（快取層、非同步架構） | 階段 4 |
| `/integration-database` | DB 架構優化（索引、連線池、讀寫分離） | 階段 4 |
| `/integration-redis` | Redis 快取整合（API 快取、Session 快取） | 階段 5 |
| `/qa-testing` | 效能測試策略與回歸測試 | 階段 2、階段 6 |
| `/devops-monitoring` | Prometheus + Grafana 監控告警設定 | 階段 7 |
| `/devops-github-actions` | CI/CD 效能測試整合（Benchmark Gate） | 階段 7 |

### 條件觸發 Skills
| Skill | 觸發條件 | 觸發時機 |
|-------|---------|---------|
| `/mobile-development` | 涉及 Android/macOS 行動端效能優化 | 階段 2（基準）、階段 5（優化） |
| `/security-audit` | 涉及支付流程/加密/TLS 安全敏感效能場景 | 階段 3-5 |
| `/sprint-planning` | 大規模效能優化需迭代規劃時 | 階段 4 |

---

## ⚡ 技術棧特定優化要點（Next.js + Spring Boot + PostgreSQL）

### Next.js SSR 常見效能問題
```yaml
- TTFB > 200ms：檢查 RSC 是否有過多 DB/API 呼叫
- LCP > 2.5s：使用 next/image 優化、啟用 Streaming SSR
- JS Bundle > 250KB：啟用 Dynamic Import + Tree Shaking
- 每次請求重複計算：使用 React cache() 或 unstable_cache
```

### Spring Boot JVM 常見效能問題
```yaml
- 冷啟動慢：考慮 GraalVM Native Image 或 JVM Warm-up Probe
- GC Pause > 100ms：調整 G1GC 參數或升級至 ZGC/Shenandoah
- HikariCP 連線耗盡：調整 maximumPoolSize（建議 = CPU 核心 × 2 + 有效磁碟數）
- Hibernate N+1：使用 @EntityGraph 或 JOIN FETCH 明確載入關聯
```

### PostgreSQL 常見效能問題
```yaml
- Seq Scan：執行 EXPLAIN ANALYZE 確認，補充 B-tree 索引
- 多業務域共用 DB 鎖競爭：使用 pg_locks 監控，考慮 Schema 隔離
- 連線數過多：使用 PgBouncer 連線池代理
- Vacuum 延遲：調整 autovacuum_cost_delay
```

---

## 🔗 延伸閱讀

- [Performance SOP 完整版](./SOP.md)
- [Performance DeepDive 深度指南](./SOP_DeepDive.md)
- [Performance 快速啟動指令集](../../prompts/scenario-prompts/performance-prompts.md)
- [performance-optimization-flow Workflow](../../workflow/scenario-specific/performance-optimization-flow.md)
- [AISDLC_INIT.md](../../AISDLC_INIT.md)

### 相關 Agents
- [performance-engineer-zh.yaml](../../agent/specialized/performance-engineer-zh.yaml) - Performance Engineer（主導）
- [sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（架構優化）
- [dev-senior-zh.yaml](../../agent/specialized/dev-senior-zh.yaml) - Senior Developer（代碼優化）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps Engineer（基礎設施與監控）
- [qa-automation-zh.yaml](../../agent/specialized/qa-automation-zh.yaml) - QA Automation（效能測試）
- [code-analyzer-zh.yaml](../../agent/specialized/code-analyzer-zh.yaml) - CodeX（代碼效能分析，選用）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（安全敏感區域優化，選用）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（行動端架構優化，選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（行動端效能測試，選用）

---

**提示**:
- 80% 的效能問題源於 20% 的程式碼
- 先測量，再優化，後驗證
- 關注使用者體驗指標（不只技術指標）

---

**文檔版本: v0.01
**最後更新**: 2026-02-17

---

## AutoClaude 自動化執行（Phase Z / v0.02 新增）

規格凍結（SPEC_FROZEN）→ `python -m autoclaude.tools.sdd_compile` 編譯 playbook → 人工 review YAML → `python -m autoclaude playbooks/sdd_bridge.yaml` 執行（🔴 人工閘門不可跳過）。
全文見：`workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`。
