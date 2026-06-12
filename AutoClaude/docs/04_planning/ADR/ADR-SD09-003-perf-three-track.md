# ADR-SD09-003 — perf 雙軌轉三軌（CI + perf machine + 開發機驗證）

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.0（PM 形式核准 2026-05-20）** |
| 建立日期 | 2026-05-19 |
| 最後更新 | **2026-05-20**（T0-7 PM 形式核准）（二輪四方審查修復：marker 配置改 pyproject.toml + 候選方案對照 SD_09 §6 #3）|
| 狀態 | **ACCEPTED — PM 形式核准 2026-05-20（場景 A dev 自核）** |
| 對應 Sprint | SD_Improving_09 議題 D（perf machine 採購 + 啟用）|
| 前置 | [ADR-SD08-003](ADR-SD08-003-perf-regression-policy.md) v1.0 |

---

## §1. 背景

SD_08 W5 落地 perf 雙軌（CI nightly + 季度 perf machine 計畫）+ 3 場景 baseline；pgvector 場景強制 SKIP 延 perf machine（R-SD08-G-1）。

SD_09 W2 採購評估 + W4 啟用後，升級為 **三軌**：CI nightly + perf machine 季度 + **開發機驗證**（新增）。

---

## §2. 決策

### §2.1 三軌定義

| 軌道 | 用途 | 場景 | 頻率 |
|------|------|------|------|
| **CI nightly**（ubuntu-latest） | 回歸偵測 | dry_run / TokenHalt / decide_correction（CPU-bound） | 每 nightly |
| **perf machine 季度** | pgvector p95 baseline | pgvector_recall_perf（IO + GPU） | 每季首週末 |
| **開發機驗證**（新增） | 開發者本地預檢 | 全 4 場景（pgvector marker 由開發者決定） | 開發者 ad-hoc |

### §2.2 marker 重構

`tests/perf/test_pgvector_recall_perf.py` 改用：
- `@pytest.mark.perf_machine_only`（取代既有 `PG_REAL_ENABLED` env gate）
- **配置位置（SD-M3 修復）**：`pyproject.toml [tool.pytest.ini_options]`（**非 pytest.ini，該檔不存在**）
  - W2 T2-D 補 marker 註冊：在 `markers = [...]` 段補入 `"perf_machine_only: 僅 perf machine 跑（ADR-SD09-003 §2.2）"`
  - 既有 markers：`pg_real`, `perf`, `benchmark`（不變動）
  - **新增 `addopts`**：`addopts = "-m 'not perf_machine_only'"`（目前 `[tool.pytest.ini_options]` 無 `addopts` 配置，本變更為**新增**）
  - 評估與既有 `pg_real` skip 行為的相互作用（不衝突；`pg_real` 仍走 fixture-level skip）
- perf machine 跑時 `pytest -m perf_machine_only` 顯式啟用

### §2.3 季度校準

- 排程：每季首週末（GitHub Actions schedule）
- 連跑 7 次取中位數 + p95
- 寫入 `.perf_baseline.toml` pgvector_recall_perf 段
- 若連跑變異 > ±30% → 告警 + Tech Lead 介入

### §2.4 三軌 drift 處理

若三軌數據 drift > 15%：
- CI vs 開發機：開發者本地環境變異，不告警
- CI vs perf machine：場景不同（CPU vs IO），不告警
- perf machine vs 季度上次：**告警** + 觸發 perf 回歸調查（ADR-SD08-003 §3 三級告警）

---

## §3. PM 預算簽核流程（紅線 ❌22）

W2 上半必確認 perf machine 採購預算：
- **commit signed-off 或 GPG 簽核**（**非僅 grep 字串**）
- 寫入 `docs/06_quality/SD09_Perf_Machine_Procurement_Eval.md` 末段
- 驗證：`git log --show-signature -1 -- docs/06_quality/SD09_Perf_Machine_Procurement_Eval.md`
- 違反觸發紅線 ❌22 → `git revert HEAD`

候選方案（**Arch-m2 修復：對應 SD_09.md §6 #3 三選項**）：
- (a) GPU 一次性 ≤ $5K — 對應 SD_09.md §6 #3 (a)
- (b) CPU bare metal 一次性 ≤ $3K — 對應 SD_09.md §6 #3 子選項（PM 可拍板 (b) 視為 $3K 對應 (a) ≤ $5K 同類，**不對應 (b) $200/月**）
- (c) 雲端 GPU instance ≤ $200/月租用 — 對應 SD_09.md §6 #3 (b)
- (d) 延 SD_10 採購 — 對應 SD_09.md §6 #3 (c)

---

## §4. 緊急路徑（SD C4 修復）

**若 W2 採購未簽核 / W4 上架失敗**：
- 議題群 D 整體延 SD_10，W4 G4 不阻塞其他項目
- `tests/perf/test_pgvector_recall_perf.py` 維持 SKIP（`@pytest.mark.perf_machine_only` deselect）
- `.perf_baseline.toml` pgvector_recall_perf 段為空（不寫入）
- 不視為 Sprint 失敗

---

## §5. 對應參考

- [SD_Improving_09.md](../SD_Improving_09.md) §1.4 議題 D
- [SD09_Execution_Guide.md](../../05_development/SD09_Execution_Guide.md) W2/W4
- [ADR-SD08-003](ADR-SD08-003-perf-regression-policy.md) v1.0

---

**簽核**：✅ ACCEPTED — 2026-05-21（SD_09 W0 T0-7 PM 形式核准；場景 A 個人開發 dev 自核 commit）
