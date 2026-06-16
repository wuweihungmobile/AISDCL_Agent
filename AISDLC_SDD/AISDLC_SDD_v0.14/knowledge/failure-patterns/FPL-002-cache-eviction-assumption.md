# FPL-002：快取永遠命中假設（未定義 miss 回退）

**狀態**: active
**建立日期**: 2026-04-19
**建立人**: SDD 閉環分析（Phase D 藍圖）
**SLV 補強建議**: SLV-008 候選

## 摘要

AC 描述效能／一致性／延遲指標時隱含「快取永遠命中」，未定義 cache miss、TTL 過期、
分散式 invalidation 時的回退行為，導致實作必須自己猜、QA 無法寫穩定 test。

## 偵測時機

- AC 中出現「< X ms」「即時」「立即」等效能詞，但上下文未提及快取策略。
- SLV-001/005 判 PASS（詞彙完整且可達），但 cache miss path 未覆蓋。

## 典型反例

```text
AC-022-1: 使用者查看商品詳情時，回應延遲 < 20ms。
```

## 為何有問題

- **隱含假設**：20ms 的數量級只能在 in-memory 快取命中時達到；任何 DB/外部服務回源必然超過。
- **測試後果**：QA 首跑（冷快取）全數 FAIL，熱跑才 PASS；CI 結果取決於 runner 狀態。
- **FSM 後果**：IMPLEMENTATION 階段 test_fail_without_spec_change 累積快速，觸發 SPEC_AUDIT。

## 歷史案例

| 專案 | 日期 | AC_id | FSM 觸發 | 結局 |
|------|------|-------|---------|------|
| 預留 | — | — | — | — |

## 建議 SLV 規則（草案）

```yaml
slv_008_candidate:
  pattern:
    keywords_latency: ["ms", "毫秒", "即時", "立即", "< [0-9]"]
    without_keywords: ["快取", "cache", "cold", "warm", "TTL", "invalidation", "未命中"]
  required_qualifier:
    - "快取命中／未命中各自的延遲上限"
    - "TTL / invalidation 策略（時間或事件）"
    - "冷啟動首次是否納入 SLO"
  failure_example: "使用者查看商品詳情時，回應延遲 < 20ms。"
  pass_example: |
    商品詳情查詢：快取命中 P95 < 20ms；未命中（回源 DB）P95 < 150ms；
    TTL = 60s 或產品資料更新事件觸發 invalidation；冷啟動首次回應不納入 SLO 計算。
```

## 修正範本

```text
[修正前]
使用者查看商品詳情時，回應延遲 < 20ms。

[修正後]
商品詳情 API：
- 快取命中：P95 < 20ms（樣本 ≥ 100）
- 快取未命中（cache miss，回源 DB）：P95 < 150ms
- 快取 TTL = 60 秒；收到 `product.updated` 事件立即 invalidate
- 冷啟動首次回應不納入 SLO 計算
```

## 相關

- FPL-001（時序語義矛盾）常與 cache 假設並存
- SLV-001 / SLV-005
