# AISDLC-SDD Performance 指令集

**情境**: Performance — PBS SLO 驅動的效能調優
**版本**: v0.01（SDD 版）
**最後更新**: 2026-04-15

---

## 🚀 標準啟動

```
我需要進行效能調優，使用 SDD Performance 情境（PBS SLO 驅動）。

載入：AISDLC_SDD_v0.01/scenarios/performance/SDD_PERFORMANCE_ENHANCEMENT.md

效能需求：
- 系統：[名稱]
- 主要問題：[描述瓶頸：API 慢 / 資料庫慢 / 高記憶體 / 其他]
- 當前指標：[測量值]

SDD 原則：PBS SLO 必須先定義，才能執行 Benchmark 和調優。
```

## 📊 階段推進

### PBS SLO 定義（必須先於 Benchmark）
```
請定義效能基準規格（PBS - Performance Baseline Specification）。

系統：[名稱]
目標場景：[API 回應時間 / 並發處理量 / 資源使用率]

SLO 定義：
- 回應時間：P50 < Xms, P95 < Xms, P99 < Xms
- 吞吐量：[X] RPS（Requests Per Second）
- 錯誤率：< X%
- 資源使用：CPU < X%, Memory < X%

SLO 凍結後才執行 Benchmark。
```

### 效能 Benchmark
```
PBS SLO 已定義，請執行效能 Benchmark。

測試工具：[k6 / Gatling / JMeter / wrk]
測試場景：[列出]
負載模型：[逐步增加 / 峰值衝擊 / 持續壓力]

記錄：當前指標 vs SLO 目標，識別差距。
```

### 效能瓶頸分析
```
Benchmark 顯示以下問題，請分析原因。

瓶頸指標：[具體數值]
可疑原因：
- [ ] N+1 查詢問題
- [ ] 缺少 Index
- [ ] 無快取
- [ ] 阻塞式操作
- [ ] 記憶體洩漏
- [ ] 其他

請分析根本原因並排序優先修復項目。
```

### 優化規格設計
```
瓶頸已確認，請設計優化規格。

瓶頸：[描述]
優化策略：
- [策略 1：例如增加 Redis 快取]
- [策略 2：例如優化 SQL Index]
- [策略 3：例如引入讀寫分離]

請為每個策略生成 ADR，記錄決策理由。
```

### SCG-6 PBS Gate 驗證
```
優化完成，請執行 SCG-6 PBS Gate 驗證。

PBS SLO 文件：[路徑]
優化後 Benchmark 結果：[數值]

驗證：
- P95 回應時間是否達標？
- 吞吐量是否達標？
- 錯誤率是否在容忍範圍？

全部通過後才可關閉此效能任務。
```

## 🔄 常見變體

### 資料庫慢查詢優化
```
資料庫查詢太慢，請幫我分析和優化。

慢查詢 SQL：[貼上 SQL]
執行計劃：[EXPLAIN 輸出（若有）]
資料量：[估計行數]

請分析問題並提供：
1. 優化後的 SQL
2. 建議的 Index
3. 是否需要重新設計資料模型？
```

### API 回應時間優化
```
以下 API 回應時間過長，請調優。

API：[端點]
當前 P95：[Xms]
目標 P95：[Xms]

請分析：
- API 內部哪個步驟最耗時？
- 是否有可快取的部分？
- 是否有不必要的串行操作可以並行？
```
