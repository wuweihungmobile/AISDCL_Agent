# SD09 Perf Machine 採購評估（軸 D #4 預研骨架 v0.1）

| 項目 | 內容 |
|------|------|
| 文件狀態 | **v0.1 SKELETON（軸 D 預研，非 W2 最終交付）** — W2 T2-D1 填實 + PM 預算簽核後升 v1.0 |
| 對應 Wave / 任務 | W2 T2-D1 / T2-D2 / T2-D3（[SD09_Execution_Guide.md §W2](../05_development/SD09_Execution_Guide.md)）|
| 對應 ADR | [ADR-SD09-003 perf 三軌制](../04_planning/ADR/ADR-SD09-003-perf-regression-policy.md) §2.2 / §3 |
| 紅線 | ❌22 — perf machine 採購未經 PM 預算簽核（commit signed-off / GPG，非僅 grep）|
| 建立日期 | 2026-05-28（R41 軸 D 預研）|

> **預研定位**：本文件為採購方案三選一的結構骨架與評估維度，供 W2 PM 預算決策前快速收斂。**不含實際報價與 PM 簽核**（屬 W2 正式交付）。

---

## 1. 背景與需求

`tests/perf/test_pgvector_recall_perf.py` 目前以 `@pytest.mark.perf_machine_only`（W4 T4-D2 規劃）deselect，因 CI runner 與一般開發機 CPU/IO 抖動過大，無法穩定鎖定 pgvector HNSW recall p95 baseline（ADR-SD09-003 §2.2「perf machine 專軌」）。

**核心需求**：
- pgvector HNSW（m=16, ef_construction=64）≥ 1M 向量 recall@10 + p95 latency 穩定量測
- 連續 7 次跑樣本 σ 足夠低以鎖定 `.perf_baseline.toml` pgvector_recall_perf（採樣統計：samples ≥ 20）
- 季度校準排程（GitHub Actions schedule 每季首週末）

---

## 2. 三方案比較骨架

| 維度 | (A) 自建 GPU 工作站 | (B) CPU bare metal 專機 | (C) 雲端 GPU instance |
|------|---------------------|--------------------------|------------------------|
| 一次性成本 | 高（GPU + 主機）| 中（伺服器級 CPU + NVMe）| 0（無 capex）|
| 月度成本 | 低（電費）| 低（電費 / 機房）| 中~高（按時計費）|
| pgvector 適配 | GPU 對 HNSW CPU-bound 查詢**助益有限**（pgvector 0.x 主為 CPU SIMD）| **最契合**（HNSW query 為 CPU + memory bandwidth bound）| 視 instance 規格 |
| 抖動控制 | 佳（獨佔）| **最佳**（獨佔 + 無虛擬化 noisy neighbor）| 中（雲端共享底層，需固定 instance type）|
| 維運負擔 | 高（自管硬體）| 中（自管硬體）| 低（雲商代管）|
| self-hosted runner 可行性 | ✅ | ✅ | ✅（需常駐成本）|
| ssh 手動跑 pytest 副選項 | ✅ | ✅ | ✅ |
| 季度校準排程契合 | 需常開機 | 需常開機 | **按需開機最省**（每季首週末啟動）|

> **預研初判（待 W2 PM 確認）**：pgvector HNSW 查詢主為 **CPU + memory bandwidth bound**，GPU 助益有限 → **(B) CPU bare metal 專機** 或 **(C) 雲端 CPU/GPU 按需 instance（季度校準場景）** 為主候選；(A) 自建 GPU 工作站性價比最低，除非 SD_10+ 引入 GPU 向量索引（如 GPU faiss）才重評。

---

## 3. 預算評估維度（W2 填實）

```
[ ] 一次性 capex（硬體 / instance reserved）：____
[ ] 月度 opex（電費 / 機房 / 雲端按時）：____
[ ] 季度校準單次成本（4 次/年）：____
[ ] 12 個月 TCO 對比（A vs B vs C）：____
[ ] PM 預算上限：____
```

---

## 4. 上線時程（對齊 ADR-SD09-003 §3）

| 里程碑 | 時點 | 動作 |
|--------|------|------|
| 預算確認 | W2 上半 | PM 預算簽核（紅線 ❌22；commit signed-off / GPG）|
| 下訂 / instance reserve | W2 下半 | 採購排程確認（self-hosted runner vs ssh 手動，T2-D3 副選項）|
| 上架 + 配置 | W4 T4-D1 | perf machine 上架 + pytest 環境 |
| baseline 鎖定 | W4 T4-D3 | 首次跑 7 次連續 → 鎖定 `.perf_baseline.toml` pgvector_recall_perf |
| 季度校準排程 | W4 T4-D4 | GitHub Actions schedule 每季首週末 |

---

## 5. 緊急路徑（ADR-SD09-003 §3 / Execution Guide T2-D1）

採購未簽核或 perf machine 未到位 → **議題群 D 整體延 SD_10，W4 G4 不阻塞其他項目**；`tests/perf/test_pgvector_recall_perf.py` 維持 `@pytest.mark.perf_machine_only` deselect，pgvector p95 baseline 延 SD_10。

---

## 6. W2 turnkey 待辦（本骨架 → v1.0 升版檢核）

```
[ ] §3 預算維度填實際報價（3 方案 12 月 TCO）
[ ] §2 初判結論經 Architect/SD 覆核確認主候選
[ ] PM 預算簽核 commit（git log --show-signature 驗證）
[ ] T2-D3 採購排程確認（self-hosted runner OR ssh 手動）
[ ] 升版 v1.0 並更新 Execution Guide G2 驗證指向本文件
```

---

**文檔元數據**：v0.1 SKELETON | 建立 2026-05-28（R41 軸 D #4 預研）| 維護者：Tech Lead + PM | W2 PM 簽核後升 v1.0
