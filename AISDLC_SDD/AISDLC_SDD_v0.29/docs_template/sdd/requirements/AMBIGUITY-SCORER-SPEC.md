# Ambiguity Scorer 評分公式規格（Phase G M3 / ACT-037）

**SCORER_VERSION**: `v1.0`（變更需 bump 並 invalidate 所有快取分數，per Rule 9.16.4）
**對應規則**: CLAUDE.md §9.16
**對應狀態**: SCG-0 ambiguity gate（Rule 9.16.2 阻擋 score ≥ 0.4）

---

## 1. 評分維度（6 dim，總和上限 1.0）

| 維度 | 權重 | 信號 | 加分規則 |
|------|------|------|---------|
| D1 量詞缺失 | 0.25 | 模糊量詞詞典命中（"快速"/"適當"/"盡可能"/"足夠"/"少量"/"大量"/"fast"/"appropriate"/"reasonable"） | 命中 1 次計 0.10、≥ 2 次計滿 0.25 |
| D2 主詞缺失 | 0.20 | passive voice / 無主詞句子比例（中文："應被處理"、"被執行"；英文："is handled"、"shall be processed"） | 句中比例 × 0.20 |
| D3 數字邊界缺 | 0.20 | NFR 句子（含「效能/延遲/吞吐/容量/可用」等關鍵字）但缺數字單位（ms/s/req/MB/GB/%） | NFR 句缺數字 → 0.20；非 NFR → 0 |
| D4 否定條件缺 | 0.15 | AC 僅有 happy path、缺 "若 X 則 Y" / "if/when/unless/否則" / "在...情況下" | 缺失 → 0.15 |
| D5 Anchor 缺失 | 0.10 | UI/API 規格類 AC 但無 `<!-- anchor:<modality>:<id> -->`（呼應 Rule 9.13.1） | 偵測到 UI/API 關鍵字但缺 anchor → 0.10 |
| D6 多義詞 | 0.10 | 指代不清詞典（"如同"、"類似"、"相應"、"相關"、"對應"、"similar"、"corresponding"） | 命中 1 次計 0.05、≥ 2 次計滿 0.10 |

**總分公式**：`score = min(D1 + D2 + D3 + D4 + D5 + D6, 1.0)`

---

## 2. 模糊詞典（v1）

### D1 量詞詞典（中英）
```
zh: 快速, 緩慢, 適當, 適度, 適合, 盡可能, 盡量, 足夠, 少量, 大量, 大部分, 一些, 若干
en: fast, slow, appropriate, reasonable, sufficient, adequate, many, few, some, several, mostly, partial
```

### D2 被動 / 無主詞模式
```
zh regex: 應(被|要被|將被|可被)\S+ | 被\S+(?=$|，|。)
en regex: \b(is|are|shall be|will be|may be|can be)\s+\w+ed\b
```

### D3 NFR 關鍵字
```
zh: 效能, 延遲, 吞吐, 容量, 可用性, 時間, 速度, 響應
en: performance, latency, throughput, capacity, availability, response time, RTO, RPO
```
數字單位 regex: `\d+\s*(ms|s|min|h|req|qps|MB|GB|TB|%|百分|秒|分鐘|小時)`

### D6 多義詞詞典
```
zh: 如同, 類似, 相應, 相關, 對應, 匹配
en: similar to, corresponding, related, matching, alike
```

---

## 3. 快取機制

- 路徑：`build/cache/ambiguity/{SCORER_VERSION}/{frd_sha256}.json`
- 結構：`{ "ac_id": score, ... }` + meta（scorer_version, computed_at, frd_sha）
- 失效：bump SCORER_VERSION 即 invalidate 整個版本目錄；FRD hash 變更亦 invalidate
- 並行寫入：使用 `file_lock.py` 保護（沿用 ACT-024 機制）

---

## 4. SCG-0 整合契約

- 入口：`workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` SCG-0 step 2b
- 阻擋條件：`max(scores.values()) >= 0.4` → SCG-0 fail
- 報告：`build/reports/scg/AMBIGUITY-{date}.yaml`（含每條 AC 的 score + 觸發維度）
- 人工 override：建立 `docs/01_requirements/AMBIGUITY-WAIVER-{AC_ID}.md`（必填 reviewer signoff）

---

## 5. 驗收

- 對 50 fixture（25 模糊 + 25 清晰）分類準確率 ≥ 80%
- 6 維度單元測試（每維度至少 3 案例）
- 快取命中測試（同 hash 不重算）
- SCORER_VERSION bump 觸發 invalidation 測試
