# ADR-SD09-008 — AC4 觀察期 #2 雙軌 p95（嚴格 50ms + 寬鬆 60ms 觀察用）

| 項目 | 內容 |
|------|------|
| 編號 | ADR-SD09-008 |
| 狀態 | **ACCEPTED v0.4 — PM 拍板選項 (a) tolerant 60ms 升級門檻（2026-05-25 SD_09 W3 軸 C 拍板）；v0.4 取證更正下游 ADR 引用錯位（Round 12 P0-R12-2 修復）** |
| 提出者 | Architect（SD_09 W3 Round 3 zero-trust audit fix agent）|
| 拍板者 | PM/PO（2026-05-25，基於 4 筆 nightly jsonl + Round 9~11 共 7 筆 p95 觀測樣本）|
| 提出日期 | 2026-05-24 |
| 拍板日期 | 2026-05-25（cut-off 2026-05-31 提前 6 天）|
| 對應議題 | SD_Improving_09 §觀察期 #2 AC4 14 天升級條件 — p95 數學上不可達標 |
| 相依 ADR | [ADR-SD08-003](ADR-SD08-003-perf-regression-policy.md)（perf 三態 / 採集 vs 升級分軌；場景 #4 pgvector p95 < 50ms 為 IO-bound 不同議題，無交叉影響）/ [ADR-SD09-001](ADR-SD09-001-pg-db-only-cutover.md)（PG db_only cutover 雙條件 — 條件 1b 為 KB metric 與本 ADR 無交集；本 ADR 不影響 ADR-SD09-001 文字）|
| CLAUDE.md 紀律 | #6（採集寬鬆 vs 升級嚴格必須分軌）|

---

## 1. 背景

SD_08 W2 PM #2 拍板 AC4 升級門檻 `p95 < 50ms`，作為 PG db_only cutover (1b) 條件之一。SD_09 W0 nightly 採集啟動後，連續 4 筆 jsonl + 3 筆 audit 觀測 p95（合計 7 筆樣本）：

| 來源 | 日期 | run_id | p95 (ms) | recall@10 | cb_open | status |
|------|------|--------|---------|-----------|---------|--------|
| jsonl | 2026-05-20 | local | **52.49** | 0.999 | 0 | pass |
| jsonl | 2026-05-21 | local | **51.07** | 0.999 | 0 | pass |
| jsonl | 2026-05-24 | local | **51.22** | 0.999 | 0 | pass |
| jsonl | 2026-05-25 | local | **51.54** | 0.999 | 0 | pass |
| audit Round 9 | 2026-05-25 | 122635 | 51.78 | 0.999 | 0 | pass |
| audit Round 10 | 2026-05-25 | 140645 | 53.21 | 0.999 | 0 | pass |
| audit Round 11 | 2026-05-25 | 151624 | 51.54 | 0.999 | 0 | pass |

**統計**：平均 51.84ms / max 53.21ms / min 51.07ms / σ ≈ 0.73ms（極穩定）。所有 7 筆樣本 **p95 ∈ [51.07, 53.21]**，落入 `[50, 60]` neutral 區。`tools/ac4_progress_check.py` 設計：
- `< 50ms` → 綠
- `50 ~ 60ms` → **neutral**（雙軌設計觀察等待；不算綠也不算 fail）
- `> 60ms` → fail

→ 結果：`green_streak` 數學上**永遠 0/14**，觀察期 #2 升級條件**永遠不可能達標**。

---

## 2. 問題本質

紀律 #6「採集寬鬆 vs 升級嚴格必須分軌」的設計是把採集（status=pass，寬鬆 80ms）與升級判定（嚴格 50ms）分開，**但**：

1. **採集寬鬆並無實際效用** — 真實 p95 51–53 並非偶發高峰，而是機器穩定 baseline；採集端 status=pass 進入 history 後，升級端嚴格判定一致拒絕。
2. **neutral 區並非「觀察等待」** — neutral 區設計假設 p95 偶爾在 50~60，多數時間 < 50；但真實情況是 p95 恆常 51–53 → neutral 變「永久等待」。
3. **升級條件設計與真實機器 baseline 不對齊** — PM #2 拍板的 50ms 是依據 SD_08 perf machine 樣本（採樣 7 點，σ 偏大）；該樣本未涵蓋真實 nightly 機器（Windows 11 Pro 開發機 vs Linux Docker container 不同）。

---

## 3. 決議方向（三選一） — **PM 拍板：選項 (a)**（見 §3.4）

### 3.1 選項 (a)：放寬 strict 至 60ms（**✅ PM 採納 2026-05-25**）

| 項目 | 內容 |
|------|------|
| 變更 | `tools/ac4_progress_check.py` `P95_MAX_MS = 60.0`；`ac4_nightly_collector.py` 寬鬆門檻同步升至 70~80ms |
| 優點 | 與真實機器 baseline 對齊；觀察期 #2 立即可進入累計；ready_for_labeled_pr 可在 14 天後達標 |
| 缺點 | 違反 SD_08 PM #2 拍板，需 PM 重新簽核；對外 (1b) 條件數字變更 |
| 風險 | 寬鬆後若上線後 p95 飄至 65ms，將假象綠燈 |
| 紅線 | **不可**單方放寬；需 PM 拍板（v0.4 取證更正：ADR-SD08-003 §AC4 章節**並不存在**，原描述為 v0.1 PROPOSED 階段假設；實際 ADR-SD08-003 §2.2 #4 line 37 為 pgvector IO-bound 與 AC4 nightly 無關）|

### 3.2 選項 (b)：保留 strict 50ms，重新 baseline 機器（性能調校）

| 項目 | 內容 |
|------|------|
| 變更 | 分析 ac4 場景效能瓶頸（pgvector HNSW ef_search？connection pool？）；調校至 p95 < 50ms |
| 優點 | 維持 PM #2 拍板紅線；真正逼近 production-grade 性能 |
| 缺點 | 工作量大（可能需重 tune ef / m / 改 connection pool / 升 hardware）；無 SLA 保證能 < 50ms |
| 風險 | 觀察期 #2 延誤 2~4 週；W5 cutover 排程連動推遲 |
| 紅線 | 必須有性能調校 spike report 證明可達標 |

### 3.3 選項 (c)：維持 strict 50ms，觀察期 #2 延 SD_10

| 項目 | 內容 |
|------|------|
| 變更 | SD_09 W5 cutover 條件改為 (1a) 30 天 obs 全綠 + (1b) AC4 strict P-R-O-O-F 採用 50ms 嚴格；AC4 達標延 SD_10 |
| 優點 | 紅線維持；不必匆促變更 |
| 缺點 | SD_09 W5 cutover **不會發生**；SD_09 退化為觀察採集週期 |
| 紅線 | PM 必須形式接受 W5 滑出 |

### 3.4 PM 拍板決定書（2026-05-25）

**拍板結論**：採納 **選項 (a) 升 tolerant 60ms 為升級門檻**，原 strict 50ms 軌降為「觀察品質指標」（持續採集、不阻塞升級）。

#### 3.4.1 三選項客觀比較（PM 評估矩陣）

| 維度 | (a) 升 60ms | (b) 性能調校 | (c) 延 SD_10 |
|------|------------|--------------|--------------|
| **觀察期 #2 達標日** | 2026-06-08（PM 拍板 +14 天）| 2~4 週 spike + 14 天 → **≥ 2026-07-15** | **無限期延後**（SD_10 起算） |
| **SD_09 W5 cutover 影響** | 無 — 對齊原排程 | 推遲 2~4 週，W5 G5 風險 | **W5 cutover 不會發生**，SD_09 退化為純觀察期 |
| **工程工作量** | 0.5 PD（門檻調整 + 測試 + ADR 更新） | 5~10 PD（pgvector ef tuning / connection pool / 可能升 hardware） | 0 PD，但 SD_09 範圍縮減 |
| **真實性能依據** | 7 筆樣本 max 53.21ms，距 60ms 緩衝 **6.79ms（12.8%）** | 無 SLA 保證 50ms 可達；過往未做 baseline | — |
| **數學可達性** | ✅ 可達（max 53.21 < 60）| ⚠️ 不保證（無 spike 證明）| ❌ 永不達標（strict 50） |
| **PM #2 拍板紅線** | 需本 ADR 形式核准（v0.4 取證更正：原宣稱「更新 ADR-SD08-003 §AC4」不成立，該章節並不存在）| 不變更紅線 | 不變更紅線 |
| **可觀測性損失** | strict 軌降為觀察指標但仍採集 — 0 損失 | 0 損失 | 0 損失但無數據累積 |
| **下游 ADR 影響** | **無下游 ADR 文字需改**（取證 2026-05-25：ADR-SD09-001 §2 (1b) 為 KB metric / ADR-SD08-005 §2.2 為「可觀測性 GA + 30 天零 drift」/ ADR-SD08-003 §2.2 #4 為 pgvector IO-bound 場景，三者均不含 AC4 50ms 陳述）；本 ADR 為 AC4 50→60ms 唯一權威 ADR，下游僅補 footnote cross-link | 無 | 同 (a)：下游無 ADR 文字需改 |

#### 3.4.2 推薦理由（基於數據而非直覺）

1. **真實 baseline 證據強烈**：7 筆樣本 σ ≈ 0.73ms 證明 p95 在當前機器（Windows 11 Pro + Docker Desktop + pgvector HNSW m=16/ef=64）為**穩定常數約 51.84ms**，非偶發高峰。
2. **60ms 緩衝合理**：max 53.21 → 60ms 緩衝 12.8%，足以吸收偶發 GC / IO / connection pool 抖動；歷史 0 筆樣本超 60ms。
3. **PM #2 原意保留**：PM #2 拍板 50ms 是基於 SD_08 perf machine 樣本（7 點，σ 偏大），並未針對 Windows 開發機 baseline 拍板；實質為「採樣 vs 升級口徑錯位」非「紅線降低」。
4. **strict 50ms 軌保留為觀察指標**：未來換 Linux production hardware 若達 < 50ms，自動成為升級依據（向上相容）。
5. **時程關鍵**：選 (b) 推遲 W5 cutover 2~4 週，違反 SD_09 v1.0 主規劃 G5 排程；選 (c) 等同 SD_09 W5 取消，PM 不接受。
6. **工作量 ROI 最高**：0.5 PD 解決 vs 5~10 PD spike 無 SLA 保證。

#### 3.4.3 實作落地細項（W3 軸 C 拍板後 ≤ 3 PD 完成）

| # | 動作 | 負責 | 時程 |
|---|------|------|------|
| 1 | [tools/ac4_progress_check.py](../../../tools/ac4_progress_check.py) `_resolve_strict_p95_threshold()` 預設 60.0（**升級門檻**）+ 新增 `_resolve_observation_p95_threshold()` = 50ms 與 `P95_OBSERVATION_MS` | Architect | **✅ IMPLEMENTED 2026-05-25**（Round 12 同 PR 落地）|
| 2 | 新增 `observation_streak`（< 50ms）作為觀察指標寫入 jsonl summary；`green_streak` / `tolerant_streak` / `ready_for_labeled_pr` 由 60ms 升級門檻控制；保留 `strict_streak` 別名向下相容 | Architect | **✅ IMPLEMENTED 2026-05-25**（Round 12 同 PR 落地）|
| 3 | [tests/tools/test_ac4_progress_check.py](../../../tests/tools/test_ac4_progress_check.py) 11 → 16 case（+5）+ [tests/tools/test_ac4_nightly_alert_parser.py](../../../tests/tools/test_ac4_nightly_alert_parser.py) 17 → 19 case（+2）+ [tests/contract/test_ac4_progress_check.py](../../../tests/contract/test_ac4_progress_check.py) 重寫 3 case；pytest 2,532 → 2,538 passed | QA | **✅ IMPLEMENTED 2026-05-25**（Round 12 同 PR 落地）|
| 4 | **取證更正（Round 12 P0-R12-2 修復 2026-05-25）**：ADR-SD08-003 §2.2 場景 #4 line 37 `p95 < 50ms` 為 **pgvector recall@10 IO-bound 場景**（perf machine 季度），**非** AC4 nightly 場景 → 本 ADR 與其無交叉影響；§AC4 章節在 ADR-SD08-003 並不存在，原 v0.3 #4 動作取消 | — | 已取消 |
| 5 | **取證更正（Round 12 P0-R12-2 修復 2026-05-25）**：ADR-SD09-001 §2 雙條件 (1b) 為 **KB metric 觀察**，**完全不含 AC4 50ms 陳述** → 原 v0.3 #5「更新 ADR-SD09-001 §2 (1b) AC4 50→60ms」為**引用錯位**，本動作取消；改於本 ADR header 相依 ADR 列已備註 | — | 已取消 |
| 6 | [docs/05_development/SD09_Execution_Guide.md](../../05_development/SD09_Execution_Guide.md) §0.1 觀察期 #2 + §3.0.2 軸 C 拍板說明同步 + [tools/run_local_nightly.ps1](../../../tools/run_local_nightly.ps1) L256-265 env 升 60 + L448-455 F2 文案改雙欄位 + [tools/ac4_nightly_alert_parser.py](../../../tools/ac4_nightly_alert_parser.py) L100-138 SSOT 同步 | PM | **✅ IMPLEMENTED 2026-05-25**（Round 12 同 PR 落地）|
| 7 | [.ac4_history.jsonl](../../../.ac4_history.jsonl) **不**重寫（紅線 §5.3）；下次 nightly 起算 14 天累計（T+1 = 2026-05-26 首筆 60ms 軌 jsonl；T+14 = 2026-06-08 達標窗口）| — | **✅ 設計就位 2026-05-25**（schema 已 backward-compatible，舊 record 缺欄位寬鬆通過）|

#### 3.4.4 觀察期 #2 校準後達標時程

> ⚠️ **ADR-SD09-012（2026-08-03 ACCEPTED）supersede 本節「連續 14 天」的「日曆連續」語意**：改採 obs／drift 兩軌線上同款的 **gap-tolerant green_streak**（漏跑一天不歸零、只有真紅才打斷），**門檻 14 與 p95 60ms／recall 0.95／σ 0.02 數值全部不變**。🔴 **判準 code 尚未落地** — `tools/ac4_progress_check.py` 至今一行未改（`evaluate()` 的 `n < OBSERVATION_DAYS` 分支仍在），**現行工具仍走本節的舊日曆語意**；落地清單（含 L-7 證據新鮮度 staleness 判準）見 ADR-SD09-012 §7.1。

| 階段 | 日期 | 事件 |
|------|------|------|
| T0 | 2026-05-25 | PM 拍板 + Guide 同步 |
| T+1 | 2026-05-26 | 實作落地 (#1-#5) + 首筆 60ms 軌 jsonl |
| T+14 | 2026-06-08 | 觀察期 #2 達標窗口（若連續 14 天 60ms 全綠 → ready_for_labeled_pr=true）|
| T+15~T+30 | 2026-06-09 ~ 2026-06-24 | 與觀察期 #3（drift 30 天）對齊；G0 啟動窗口 2026-06-25 |

---

## 4. 過渡實作（不破壞 strict 紅線）

無論 PM 選 (a)/(b)/(c)，本 ADR 落地後**立即實作**雙軌觀察工具，提供 PM 拍板資料：

### 4.1 `tools/ac4_progress_check.py` 雙軌 evaluate

新增 `--tolerant-p95-ms 60` CLI 參數：
- 提供時：額外計算 `tolerant_streak`（同 strict 計法，僅 p95 門檻換為 60ms）
- **不**修改 `ready_for_labeled_pr`（仍由 strict 控制）
- 印出兩條 streak 供 PM 觀察

### 4.2 行為示意

```bash
$ python tools/ac4_progress_check.py --tolerant-p95-ms 60
[AC4 progress] status=observing
  observation_days=3/14
  strict_streak=0 (p95 < 50ms)
  tolerant_streak=3 (p95 < 60ms; PM 觀察用，不影響 ready)
  ready_for_labeled_pr=False
  reasons:
    - p95 卡嚴格門檻 50ms~60ms neutral 區（雙軌設計觀察等待）
```

→ PM 看 `tolerant_streak=3` 對比 `strict_streak=0`，可決定走 (a) (b) (c) 哪條路徑。

---

## 5. 紅線（不可違反）

1. ~~**PM 拍板前 `ready_for_labeled_pr` 不放寬**~~ — **2026-05-25 PM 拍板選 (a) 後解除**；升級門檻正式改為 60ms tolerant（見 §3.4）；strict 50ms 降為觀察指標 `strict_streak`。
2. **不再單方變更升級門檻** — 60ms 為本 ADR v0.3 ACCEPTED 拍板；任何後續變更（如 production hardware 切換後改回 50ms）必須由 PM 新拍板（簽 ADR 補丁或新 ADR）。
3. **history jsonl 不重寫** — 過往採集紀錄 p95 真實值保留，不可 backfill / 修改；觀察期 #2 14 天累計**從拍板日 2026-05-26 首筆新口徑 jsonl 起算**（不溯及既往）。
4. **strict 軌不可刪除** — `strict_streak` 必須持續採集寫入 jsonl summary，作為未來 production hardware 切換的升級依據（向上相容）。

---

## 6. 採納路徑

| 階段 | 動作 | 負責 | 完成日 |
|------|------|------|--------|
| **PROPOSED v0.1** | 本 ADR 落地 + 雙軌工具實作 | Architect | 2026-05-24 ✅ |
| **PROPOSED v0.2** | §6.1 強制週報 + cut-off 逾期自動降級「過渡寬限」 | Architect | 2026-05-25 ✅ |
| **REVIEW** | PM 看雙軌資料、3 選項決議 | PM | 2026-05-25 ✅（cut-off 2026-05-31 提前 6 天）|
| **ACCEPTED v0.3** | PM 拍板 **選項 (a)** 60ms tolerant 升級 → 補對應實作（§3.4.3 七項，原宣稱「更新 ADR-SD08-003 §AC4 + ADR-SD09-001 §2 (1b)」於 v0.4 取證後取消）| PM + Architect | 2026-05-25 ✅ |
| **ACCEPTED v0.4** | Round 12 P0-R12-2 取證更正：ADR-SD09-001 §2 (1b) 為 KB metric / ADR-SD08-005 §2.2 為「可觀測性 GA + 30 天零 drift」/ ADR-SD08-003 §2.2 #4 為 pgvector IO-bound，**三者均不含 AC4 50ms 陳述** → §3.4.3 #4/#5 動作取消；本 ADR 為 AC4 50→60ms **唯一權威 ADR** | Architect | 2026-05-25 ✅（本版本）|
| **IMPLEMENTED** | §3.4.3 #1-#3 落地 + 測試通過 + nightly 首筆新口徑 jsonl（#4/#5 已取消）| Architect + QA | 2026-05-26（預計）|
| **OBSOLETED** | 觀察期 #2 達標 ready=True 後（最早 2026-06-08）| — | — |

### 6.1 PROPOSED 階段強制週報（SD_09 W3 Round 4 audit P2-AUDIT-R3-1 修復）

**問題**：原採納路徑無強制 cut-off；PROPOSED 可能無限延期 → 觀察期 #2 達標日 2026-06-02 與 PM 拍板日 2026-05-31 僅差 2 天，即使選 (a) 從 0 累計到 14 也需 2026-06-14 才達標。

**修復**：

1. **強制週報**：PROPOSED 階段每 7 天由 Tech Lead 主動 ping PM（5/24 起：5/31、6/7、6/14）
2. **逾期降級**：cut-off 2026-05-31 PM 未拍板 → **自動進入「過渡寬限」**：
   - 不放寬 `ready_for_labeled_pr`（仍由 strict 控制紅線 ❌1）
   - 但 SD_09 W5 cutover 規劃自動更新觀察期 #2 達標日 = `max(2026-06-02, PM_cutoff_date + 14)`
   - sprint_history.md 主規劃 §觀察期 #2 自動標 `🟡 延期 — PM 拍板未完成`
3. **觀察期 #2 達標日重新校準**（依 §6.1.2）：

   | PM 拍板路徑 | 達標日（最早） |
   |-----------|--------------|
   | (a) 放寬 60ms | PM_cutoff_date + 14 天（路徑切換後從 0 累計）|
   | (b) 性能調校 | 等性能調校 spike 完成 + 後續 14 天 nightly green |
   | (c) 延 SD_10 | 觀察期 #2 完成日改為 SD_10 起算 |

---

## 7. 相關修復取證

- 修改檔：[`tools/ac4_progress_check.py`](../../../tools/ac4_progress_check.py)（+ `_is_green_tolerant` / evaluate `tolerant_p95_ms` 參數 / main `--tolerant-p95-ms` flag）
- 測試檔：[`tests/tools/test_ac4_progress_check.py`](../../../tests/tools/test_ac4_progress_check.py)（10 case，含雙軌 strict pass / tolerant pass / 兩者皆 fail）
- 採證紀錄：`.ac4_history.jsonl` 3 筆 2026-05-20 ~ 2026-05-24 真實 p95 = 52.49 / 51.07 / 53.21

---

**版本紀錄**：
- v0.1（PROPOSED）2026-05-24 初版 — SD_09 W3 Round 3 audit P0-1 修復項
- v0.2（PROPOSED）2026-05-25 — SD_09 W3 Round 4 audit P2-AUDIT-R3-1 修復 — §6.1 加入強制週報 + cut-off 逾期自動降級「過渡寬限」
- **v0.3（ACCEPTED）2026-05-25 — SD_09 W3 軸 C PM 拍板選項 (a)**：升級門檻 50ms → 60ms tolerant；strict 50ms 降為觀察指標；觀察期 #2 從 2026-05-26 新口徑首筆 jsonl 起算 14 天，最早達標 2026-06-08。基於 7 筆樣本（avg 51.84ms / σ 0.73ms / max 53.21ms）的真實機器 baseline 證據（§3.4.2）。v0.3 原宣稱「下游 ADR-SD08-003 §AC4 + ADR-SD09-001 §2 (1b) 同步更新」於 v0.4 取證後取消。
- **v0.4（ACCEPTED）2026-05-25 — SD_09 W3 Round 12 zero-trust audit P0-R12-2 + P1-R12-1 修復**（minor revision，僅交叉引用更正不改決議實質）：
  1. **取證結論**：ADR-SD09-001 §2 (1b) 為 **KB metric 觀察**（不含 50ms / AC4 / tolerant 字眼）；ADR-SD08-003 §2.2 #4 line 37 `p95 < 50ms` 為 **pgvector recall@10 IO-bound 場景**（perf machine 季度），與 AC4 nightly（CPU-bound）為不同議題；ADR-SD08-005 §2.2 雙條件為「可觀測性 GA + 30 天零 drift」（不含 50ms / AC4 字眼）— **三個下游 ADR 均不含 AC4 50ms 陳述**。
  2. **修正項**：
     - header 相依 ADR 列補上「條件 1b 為 KB metric 與本 ADR 無交集」澄清
     - §3.4.1 「下游 ADR 影響」一列改為「無下游 ADR 文字需改」
     - §3.4.3 #4/#5 動作取消（原引用錯位）+ 改為「取證更正紀錄」
     - §6 採納路徑補 ACCEPTED v0.4 一行
  3. **P1-R12-1 退化為 P2**：下游 ADR 均不含 50ms 陳述 → 無需 footnote cross-link；本 ADR 為 AC4 50→60ms **唯一權威 ADR**。
  4. **不影響項**：PM 拍板決議實質（60ms tolerant 升級門檻 + strict 50ms 降為觀察指標）/ tools/ac4_progress_check.py / tests / .ac4_history.jsonl / 14 天累計起算日（2026-05-26）。

**風險與緩解**：
- R-SD09-008-1：60ms tolerant 後 production hardware 切換可能仍 < 50ms → **緩解**：strict 軌持續採集（紅線 ❌4），切換後可由 PM 拍板回升 50ms。
- R-SD09-008-2：未來 ef_search/ef_construction tune up 可能讓 p95 退化逼近 60ms → **緩解**：保留 60ms 為**升級門檻**而非「常態 SLA」；任何 p95 > 55ms 在 ac4_nightly_collector 印 WARN（後續 PR 補實作）。
- R-SD09-008-3：14 天起算日 2026-05-26 與觀察期 #3（drift 30 天，2026-06-17 達標）時序錯位 → **緩解**：W5 G5 雙條件原本就需 max(觀察期 #2, #3)；觀察期 #2 早 9 天達標，由 #3 控制 W5 啟動日（無影響）。
