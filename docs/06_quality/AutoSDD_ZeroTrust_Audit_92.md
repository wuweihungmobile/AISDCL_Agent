# AutoSDD_ZeroTrust_Audit_92 — bge-m3 本地 TEI 非機密設定收進 config.yaml（方案 B 收尾，C 軌）

> 對應計畫書：[docs/04_planning/AutoSDD_improving_92.md](../04_planning/AutoSDD_improving_92.md)。本輪審計＝三鏡（Architect / SA-SD / QA）對「文件 vs 系統現況」zero-trust 比對 + QA P2 當場修復證據。

## §0 審計結論摘要

| 鏡 | 結論 | P0 | P1 | P2 |
|----|------|----|----|----|
| Architect | **OVERALL PASS** | 0 | 0 | 0 |
| SA-SD | **OVERALL PASS** | 0 | 0 | 0 |
| QA | **OVERALL PASS**（P2 已當場修） | 0 | 0 | 1（已修） |

**派發隔離**：主樹並行派發（本輪含 untracked 計畫書 `AutoSDD_improving_92.md` + tracked 未 commit 的測試/源碼改動 → 依 DEF-24-001「審查 untracked 新檔一律主樹、禁 worktree」）。無並行就地突變（MUT-92-1/2 已於實作階段序列化完成並還原）。分工避 cache 互踩（[[parallel-mutation-audit-collision]]）：僅 SA-SD 跑全套清 cache，Architect 跑 lint/LOC + 架構審查、QA 唯讀測試品質分析（針對性子集不清 cache）。

---

## §1 階段一基線（Zero-Trust Re-Audit，2026-06-27 實測）

| 項目 | 命令 | 實測 |
|------|------|------|
| AutoClaude 全套 pytest | `rm -rf .pytest_cache && python -m pytest tests/ -q` | **3544 passed / 0 failed / 122 skipped**（71.19s） |
| lint-imports | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** |

**硬閘**：基線 3544 passed / 0 failed，= improving_91 結案 floor、無退化 → 通過。

---

## §2 Architect 鏡（架構純潔性 + 設定治理一致性）

**OVERALL PASS（P0=0/P1=0/P2=0）**。重點：
- **lint-imports 8 kept / 0 broken**：`bgem3_local.py:25` 新增 `from ...utils.config import EmbedderConfig`（adapter→utils.config）與 `minimax_embedder.py:24` 同前例；.importlinter 8 規則皆涉 plugin/core/runner/brain，adapter import utils.config 完全合法、未破任何契約。
- **LOC violations=0**：config.py（utils/ 預設 tier ≤750）、bgem3_local.py（adapter ≤400）皆未超；total=19885 / cap=20438。
- **微核心純潔**：EmbedderConfig additive 加 4 個 `bge_m3_*` 欄位（與既有 Minimax 欄位同構、互不干擾）；playbook_runner（Thin Facade）git diff 零碰；無 God-object。
- **機密邊界**：bge-m3 正確判定為「全非機密」（TEI 本地容器、無 api_key/帳號識別）；EmbedderConfig **未為 bge-m3 新增任何機密欄位**；`config_resolver.py:47-51` `_PROTECTED_FIELDS` 維持原 3 欄（minimax.api_key / embedder.api_key / storage.db_dsn）不變、未誤加 TEI 欄位。
- **additive 零退化**：四層兜底鏈 config=None + 無 env 時塌回硬編（byte-level）；簽章預設改 None 向後相容。
- **與 improving_91 治理一致**：同樣四層兜底鏈（建構參數 > env > config > 硬編），對比 minimax_embedder.py:46-85 行為一致。
- **計畫書 §3.1 四點 <Architecture_Design_Review> 宣稱**逐項與程式碼相符。

---

## §3 SA-SD 鏡（唯一全套 pytest + git 鐵證 + 設定零漂移）

**OVERALL PASS（P0=0/P1=0）**。重點：
- **親跑全套（清 cache）：3552 passed / 0 failed / 122 skipped**（複核屬實；floor 3544 +8 新測，精確零退化）。lint 8 kept、LOC violations=0、snapshot OK。
- **DEF-92-001/002 git 鐵證**：`git show HEAD:AutoClaude/autoclaude/infra/adapters/bgem3_local.py` 確認修改前 `model_id` 簽章硬編 `"BAAI/bge-m3"`、`dimension` 硬編 `_DEFAULT_DIM`，`__init__` 確實只讀 `TEI_URL`、不讀 `TEI_MODEL_ID`/`TEI_EMBED_DIMENSIONS`（坐實缺陷真實存在、非虛報）；對照 HEAD 版 `.env.example` 確實宣告了這兩個 env。
- **計畫書宣稱 vs 程式碼逐項一致**：§4 實作描述、§5 矩陣數字（3552 / 8 kept / violations=0）、RTM-92-1~5 對應測試皆真存在且真通過。
- **四處設定零漂移**：EmbedderConfig 預設（config.py）、config.yaml embedder.bge_m3_*、bgem3_local.py 硬編兜底、.env.example 註解——四處 bge-m3 預設值（localhost:8080 / BAAI/bge-m3 / 1024）一致無漂移。

---

## §4 QA 鏡（測試品質 + 回歸防護）+ P2 當場修復

**OVERALL PASS（P2=1，已當場修）**。重點：
- **8 新測逐一審查**：全為真回歸鎖（business logic 改了會 fail），無恆真/恆假假測試；6 個 contract 測試 hermetic（monkeypatch.delenv/setenv）；RTM-92-1~5 全覆蓋；DEF-92-001（test_bge_model_from_env）/ DEF-92-002（test_bge_dimension_from_env）各有防復活鎖。
- **MUT-92-1/2 驗牙邏輯成立**：拔 env 讀取那行/分支，對應測試必然轉紅（實作階段已實證雙雙轉紅 → Edit 還原 → 復綠）。

### P2 發現與修復（DEF-92-002 副作用：既有測試 env 隱患）
- **發現**：本輪讓 BGEM3LocalAdapter 開始讀 `TEI_EMBED_DIMENSIONS` env 後，3 個**既有** bge 測試（`test_bge_dimension_default_1024` / `test_bge_embed_preserves_order_and_count` / `test_bge_dim_mismatch_raises`）未清該 env——開發者 shell 若 export `TEI_EMBED_DIMENSIONS=512`，這些既有測試會變 flaky（偽 fail / DID NOT RAISE）。屬本輪改動暴露的既有隱患（CI 清淨環境不複現），P2。
- **修復（當場、不延後，遵 [[no-defer-unless-justified]]；屬「清自己改動造成的 mess」）**：對 3 個既有測試各補 `monkeypatch.delenv("TEI_EMBED_DIMENSIONS", raising=False)` + 簽章加 `monkeypatch` 參數 + hermetic 說明 docstring。adapter 邏輯零改。
- **修復實證**：`TEI_EMBED_DIMENSIONS=512 python -m pytest -k "bge_dimension_default or bge_embed_preserves or bge_dim_mismatch"` → 修前會 fail、**修後 3 passed**；P2 修復未動搖數字（純加 monkeypatch 參數，3552 不變）。

---

## §5 結案零退化矩陣（複核）

| 檢查 | 實測 | 通過 |
|------|------|------|
| AutoClaude 全套 pytest（清 cache fresh，P2 修後複跑） | 3552 passed / 0 failed / 122 skipped（70.26s） | ✅ |
| 架構契約 lint-imports | 8 kept / 0 broken | ✅ |
| LOC 分級 | violations=0（total=19885 / cap=20438） | ✅ |
| Snapshot | OK | ✅ |
| AISDLC_SDD ci-gate | N/A 類型①（git status 鐵證零碰 AISLDC_SDD/、*.tla） | ✅ |
| DAL 等價 | N/A 類型②（tests/equivalence/ 隨全套通過、零 DAL/checkpoint 改動） | ✅ |
| 五軌 TLC | N/A 類型①（零碰 *.tla/FSM/_HAPPY_PATH） | ✅ |

**全鏡 PASS → 准結案。**
