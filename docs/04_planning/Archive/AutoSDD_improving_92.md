# AutoSDD_improving_92 — bge-m3 本地 TEI 非機密設定收進 config.yaml：方案 B 收尾（C 軌）

> **本輪柱位**：**C 軌（指揮官 AutoClaude 自身能力：LLM/設定來源治理收尾）**。對齊北極星第 1 點——AutoClaude＝以微核心 + DAL 三後端管理的 Playbook 引擎，設定來源治理是其可運維性基座。**90 輪統一 chat（MinimaxBrain）base_url/model 為「非機密預設唯一權威源」（commit 6daa540）；91 輪把同一治理延伸到 Minimax embedder（EmbedderConfig，commit c1ec9b0）；本輪把最後一塊 embedder——bge-m3 本地 TEI——的非機密設定（`TEI_URL`/`TEI_MODEL_ID`/`TEI_EMBED_DIMENSIONS`）一併收進 config.yaml，完成方案 B 收尾。**
> **掌舵者裁示**：2026-06-27「TEI_URL/TEI_MODEL_ID 還是只走 env，等於是方案 B 的收尾 → 請執行」。
> **下一份**：improving_93。
> **框架版**：本輪零碰 AISLDC_SDD 框架本體（生產碼全在 AutoClaude `utils/config.py` + `infra/adapters/bgem3_local.py` + `config.yaml`/`.env.example` 資料檔 + 測試）→ 免 Copy-on-Evolve、維持 v0.27。`L_合體=min(A,B,C)=L5` 不變（設定來源治理＝可運維性加固，非成熟度推進）。

---

## §1 本輪輸入（自上輪繼承）

### 1.1 improving_91 結案狀態（RTM 收尾）
- improving_91＝C 軌「方案 B」首段——Minimax embedder 非機密設定收進 config.yaml（`EmbedderConfig`）+ 修三缺陷（DEF-91-001/002/003），commit c1ec9b0。
- 已完成 W 項：W-91-1（EmbedderConfig + AppConfig + config.yaml embedder 區塊）、W-91-2（minimax_embedder.py 四層兜底鏈 + 補 `MINIMAX_EMBED_MODEL` env 讀取）、W-91-3（DEF-91-001 dataclass 對齊 + .env.example + 9 新測 + MUT-91-1）。未完成 W 項：無。
- 上輪審計三鏡（Architect / SA-SD / QA）全 OVERALL PASS（P0=0/P1=0；3 個 P2 當場修不延後）。
- 上輪明示「**bge-m3 的 TEI 設定亦收進 config.yaml＝方案 B 收尾，improving_92 候選**」（improving_91 §7 結語）。本輪即兌現。

### 1.2 階段一基線（2026-06-27 實測）
- AutoClaude 全套 pytest（清 cache 後 fresh）：**3544 passed / 0 failed / 122 skipped**（71.19s）。floor＝3544（91 輪實測值），新測試只增不減。
- lint-imports：**8 kept / 0 broken**。

### 1.3 缺陷帳本 open / routed（本輪處置計畫）
| 缺陷 | 狀態 | 本輪處置 |
|------|------|---------|
| DEF-01-007（cc-switch GUI P3） | open | 不涉多後端切換 → 維持 |
| DEF-01-009（sdd_governance_plugin LOC watch P3） | open watch | 零碰該檔 → 維持 |
| DEF-19-001（catch 歸因覆蓋面 P3） | routed 漸進中 | 不涉本輪 scope → 維持 |
| DEF-42-001（test_file_lock Windows flaky P3） | routed | 非本輪回歸 → 維持 |
| DEF-62-001（auto_recovery 註解滯後 P3） | open routed | 不涉本輪 scope → 維持 |
| DEF-90-001（stale .pytest_cache 少報 P3 流程） | fixed@90 | 本輪沿用「引用數字前清 cache」紀律 |

### 1.4 本輪新登缺陷（階段一 zero-trust 重偵察揪出，皆有鐵證）
| 缺陷 | 嚴重度 | 一句話 |
|------|--------|--------|
| DEF-92-001 | P3 | `.env.example:73` 宣告 `TEI_MODEL_ID=BAAI/bge-m3`，但 `bgem3_local.py:37` `model_id` 為簽章硬編預設、`__init__` **從未讀取該 env**——文件 vs 實況不符（功能上 BAAI/bge-m3 恰等於範例值故未爆，但宣稱可配置實則不可）。與上輪 DEF-91-002 同類，本輪 W-92-2 修。 |
| DEF-92-002 | P3 | `.env.example:75` 宣告 `TEI_EMBED_DIMENSIONS=1024`，但 `bgem3_local.py:38` `dimension` 為簽章硬編預設、`__init__` **從未讀取該 env**——同類文件 vs 實況不符。本輪 W-92-2 修。 |
| DEF-92-003 | P3 | `bgem3_local.py:44-48` 兜底鏈僅 2 層（建構參數 > env(TEI_URL) > 硬編），**無 config 兜底層**；config.yaml 的 `embedder:` 區塊（91 輪建立）只含 Minimax 欄位、無 bge-m3 欄位——TEI 非機密設定完全游離 config.yaml 之外，與 91 輪治理不一致。本輪 W-92-1 補齊。 |

---

## §2 階段一實測（Zero-Trust Re-Audit）

| 項目 | 命令 | 實測結果 |
|------|------|---------|
| (a) AutoClaude 全套 pytest | `python -m pytest tests/ -q`（清 cache 後 fresh） | **3544 passed / 0 failed / 122 skipped**（71.19s） |
| (b) lint-imports | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** |
| (c) AISDLC_SDD ci-gate | N/A（本輪零碰框架本體，見 §5 矩陣 N/A 標註） | — |
| (d) 上輪構件存在性 | improving_91 `EmbedderConfig`（`utils/config.py:27-45`）、minimax_embedder 四層兜底鏈（`minimax_embedder.py:46-85`）、config.yaml `embedder:` 區塊（:20-31）皆在且被測試覆蓋（`test_embedder_contract.py` + `TestEmbedderConfig`） | ✅ |
| (e) 缺陷帳本 open 項重現 | 見 §1.3（本輪 scope 外者維持） | — |
| (f) 外部工具依賴 | 本輪**不需真跑 TEI 容器**（純設定治理層，新測試以建構參數/env/config 驗優先序 + fake http client，不打真 TEI endpoint）；TEI 為**本地容器端點、全非機密**（無 api_key/帳號識別），無新 headless 自動化假設 | ✅ 無 DEF-10-002a 類風險 |

**硬閘**：(a) 基線 3544 passed / 0 failed，未低於上輪、無 failed → **通過，准進階段二**。

---

## §3 增量設計（階段二）

### §3.0 設計依據實證（zero-trust，不憑記憶斷言）
- **bgem3_local.py 現況兜底鏈**（`bgem3_local.py:44-48`）：
  ```python
  self._base_url = (
      base_url
      or os.environ.get("TEI_URL")
      or "http://localhost:8080"
  ).rstrip("/")
  ```
  → 僅 2 層（參數 > env(TEI_URL) > 硬編），**無 config 層**；`model_id`/`dimension` 為簽章硬編（`model_id: str = "BAAI/bge-m3"`、`dimension: int = _DEFAULT_DIM`），**TEI_MODEL_ID/TEI_EMBED_DIMENSIONS env 從未讀取**（DEF-92-001/002）。
- **對齊範本**＝improving_91 minimax_embedder.py 四層兜底鏈（`minimax_embedder.py:46-85`，建構參數 > env > config 兜底 > 硬編）。
- **EmbedderConfig 現況**（`utils/config.py:27-45`）：flat 結構，現有欄位（base_url/model/dimension/timeout_seconds/api_key）為 Minimax 專用。bge-m3 欄位以 `bge_m3_` 前綴 additive 加入同一 EmbedderConfig（不動既有 Minimax 欄位＝零退化）。
- **TEI 機密性裁定**：`TEI_URL`（本地容器 HTTP 端點）、`TEI_MODEL_ID`（模型名）、`TEI_EMBED_DIMENSIONS`（維度常數）**皆非機密**；TEI 為本地容器、**無 api_key/帳號識別**。故 `config_resolver._PROTECTED_FIELDS` **不需新增** TEI 欄位（與 Minimax embedder.api_key 需 RBAC 保護不同——本輪無 RBAC 變更）。
- **production wiring 現況**：`main.py`/`wiring.py` 皆**未建構/注入** BGEM3LocalAdapter / MinimaxEmbedderAdapter（SD_06 W3 落 adapter+port+contract test，未接 main wiring）——與 91 輪偵察一致。本輪純設定治理層，**不新增 wiring**（維持現況、零退化），僅使「設定如何被讀」對齊 91 輪治理。

### §3.1 <Architecture_Design_Review>（寫任何 Python 前必輸出）
1. **架構純潔性**：是否造 God-object / 破壞 Thin Facade？
   → 否。`EmbedderConfig` additive 加 4 個 `bge_m3_*` flat 欄位（與既有同構）；adapter `__init__` 僅擴充既有兜底鏈（additive `config` 參數），無新類別、無業務邏輯下沉。playbook_runner 零碰。
2. **持久化相容**：新狀態是否 additive 寫入 PlaybookCheckpoint？DAL 三後端零停機？
   → N/A——本輪不碰 checkpoint/DAL/狀態機。`EmbedderConfig` 是啟動期設定，非執行期狀態。新增欄位皆有 default（Pydantic BaseModel 預設值），舊 config.yaml 無 bge-m3 欄位時自動用預設（零退化）。
3. **安全防護網（CONDITIONAL）**：本輪是否新增「從文件生成指令」路徑？
   → 否。bge-m3 欄位是 url/model/dimension/timeout 純資料，不進 shell、不組指令。CONDITIONAL 三層防禦無新攻擊面。
4. **對外 I/O 安全（ToolInvocationPort）**：是否新增外呼路徑？
   → 否。本輪只改 bge-m3 embedder 的「設定如何被讀」，不改其「如何呼叫 TEI」（embed()/health_check() 路徑零碰）。allowlist/SSRF 攻防無新增需求。
   → **機密邊界守則**：TEI 全非機密——**EmbedderConfig 不為 bge-m3 新增任何 api_key/機密欄位**，`_PROTECTED_FIELDS` 維持原 3 欄（minimax.api_key / embedder.api_key / storage.db_dsn）不變。

### §3.2 W 項（本輪 ≤3 項，聚焦）

#### W-92-1：EmbedderConfig 擴充 bge-m3 欄位 + config.yaml + .env.example（修 DEF-92-003）
- **介面 delta**（`utils/config.py` EmbedderConfig）：additive 新增
  ```python
  # bge-m3 本地 TEI（improving_92 W-92-1，方案 B 收尾）：TEI 為本地容器端點、全非機密，
  # 對應 .env.example 的 TEI_URL / TEI_MODEL_ID / TEI_EMBED_DIMENSIONS（後兩者先前 adapter
  # 從未讀取，DEF-92-001/002）。無 api_key/RBAC 需求（與 Minimax embedder 不同）。
  bge_m3_url: str = "http://localhost:8080"
  bge_m3_model: str = "BAAI/bge-m3"
  bge_m3_dimension: int = 1024
  bge_m3_timeout_seconds: float = 30.0
  ```
- **config.yaml** `embedder:` 區塊加 bge-m3 子段（4 非機密欄位 + 治理註解）。
- **.env.example** 校正 TEI 區塊註解（標明 base_url/model/dimension 預設見 config.yaml、env 為覆寫用；DEF-92-001/002 修復說明）。
- **LOC 預算**：config.py 居 utils/（預設 tier ≤750），現 ~241 計 LOC，+4 欄位 ~+10 → 安全；總 cap 餘 578。
- **importlinter 影響**：EmbedderConfig 居 utils/config.py，無新跨層 import → 預期 8 kept 不變。

#### W-92-2：BGEM3LocalAdapter 四層兜底鏈（修 DEF-92-001/002，補 config 層 DEF-92-003）
- **介面 delta**（`bgem3_local.py:33-51`）：`from ...utils.config import EmbedderConfig`（同 minimax_embedder.py:24 既有慣例）；`__init__` 新增 additive `config: Optional[EmbedderConfig] = None`；`model_id`/`dimension`/`timeout_seconds` 簽章預設 → `None`（向後相容：顯式傳值不變）。兜底鏈改「建構參數 > env > config > 硬編」：
  - `model_id = model_id or env(TEI_MODEL_ID) or (config.bge_m3_model if config) or "BAAI/bge-m3"`（**補 env＝修 DEF-92-001**）
  - `base_url = base_url or env(TEI_URL) or (config.bge_m3_url if config) or "http://localhost:8080"`（保留既有 env，補 config 層）
  - `dimension`：參數 > env(TEI_EMBED_DIMENSIONS，`.isdigit()` 檢核) > config.bge_m3_dimension > `_DEFAULT_DIM`（**補 env＝修 DEF-92-002**）
  - `timeout_seconds`：參數 > config.bge_m3_timeout_seconds > 30.0
- **零退化保證**：`config=None` + 無 env 時 byte-level 等同現況（model_id="BAAI/bge-m3"、dimension=1024、base_url 硬編、timeout=30.0）。
- **importlinter 風險點**：adapter import `utils.config.EmbedderConfig` —— minimax_embedder.py:24 已有同前例、lint 8 kept，預期不破契約。階段四 lint-imports 實測決定。
- **LOC 預算**：bgem3_local.py adapter tier（≤400），現 ~110 計 LOC，+~18 → 安全。

#### W-92-3：測試 + MUT 突變驗牙 + .env.example 校正收尾
- **新增測試**（RTM 見 §3.3）：bge-m3 設定優先序（config=None 零退化、config 兜底、env>config、ctor>env>config、TEI_MODEL_ID env、TEI_EMBED_DIMENSIONS env）+ EmbedderConfig bge-m3 預設/載入。
- **MUT-92-1**（DEF-92-001 防復活）：拔 `or os.environ.get("TEI_MODEL_ID")` → 對應測試轉紅 → Edit 還原（非 git checkout，遵紀律）。
- **MUT-92-2**（DEF-92-002 防復活）：拔 `TEI_EMBED_DIMENSIONS` 讀取分支 → 對應測試轉紅 → Edit 還原。

### §3.3 RTM 需求列（SCG-5 對應，實測欄階段三/四回填）
| RTM | 需求 | 驗證測試 | 實測 |
|-----|------|---------|------|
| RTM-92-1 | EmbedderConfig bge-m3 欄位可由 config.yaml 載入、預設正確（修 DEF-92-003） | `test_config_validation.py::TestEmbedderConfig::test_embedder_bge_m3_block_loaded` + `::test_embedder_bge_m3_defaults` | （回填） |
| RTM-92-2 | adapter 優先序：建構參數 > env > config 兜底 > 硬編 | `test_embedder_contract.py::test_bge_config_fallback_when_no_env` + `::test_bge_env_overrides_config` + `::test_bge_ctor_arg_overrides_env_and_config` | （回填） |
| RTM-92-3 | adapter `config=None` + 無 env 時 byte-level 零退化 | `test_embedder_contract.py::test_bge_no_config_backward_compat` | （回填） |
| RTM-92-4 | DEF-92-001：model 由 `TEI_MODEL_ID` env / config 可配置 | `test_embedder_contract.py::test_bge_model_from_env`（+ MUT-92-1 驗牙） | （回填） |
| RTM-92-5 | DEF-92-002：dimension 由 `TEI_EMBED_DIMENSIONS` env / config 可配置 | `test_embedder_contract.py::test_bge_dimension_from_env`（+ MUT-92-2 驗牙） | （回填） |

### §3.4 SCG 進程（B 軌 dogfooding 形式，本輪 C 軌作業）
- SCG-0/1：本計畫書（§1 輸入 + §2 實測 + §3 設計）＝載體。
- SCG-2：§3.2 介面 delta ＝設計。
- SCG-3：無 OpenAPI 契約（純內部設定模組），N/A。
- SCG-4：實作 PR（階段三）。
- SCG-5：§3.3 RTM（階段三/四回填實測）。

---

## §4 實作與雙重驗證（階段三）

### W-92-1：EmbedderConfig bge-m3 欄位 + config.yaml + .env.example（修 DEF-92-003）
- `autoclaude/utils/config.py`：EmbedderConfig additive 加 4 欄（`bge_m3_url`/`bge_m3_model`/`bge_m3_dimension`/`bge_m3_timeout_seconds`，含 TEI 全非機密 docstring；無 api_key、`_PROTECTED_FIELDS` 不變）。
- `config.yaml`：`embedder:` 區塊加 bge-m3 子段（4 非機密欄位 + 治理註解；既有 Minimax 欄位零碰）。
- `.env.example`：TEI 區塊註解校正（TEI_URL/TEI_MODEL_ID/TEI_EMBED_DIMENSIONS 改「覆寫用、預設見 config.yaml」並註解化；標明全非機密、DEF-92-001/002 修復）。
- 驗證（scratchpad/verify_w92_1.py，已跑）：EmbedderConfig 預設正確、config.yaml 載入 bge-m3 四欄正確、Minimax 欄位零干擾。

### W-92-2：BGEM3LocalAdapter 四層兜底鏈（修 DEF-92-001/002，補 config 層 DEF-92-003）
- `autoclaude/infra/adapters/bgem3_local.py`：`from ...utils.config import EmbedderConfig`（同 minimax_embedder.py:24 既有慣例）；`__init__` 加 additive `config` 參數；`model_id`/`dimension`/`timeout_seconds` 簽章預設改 `None`（向後相容）；四欄位兜底鏈改「建構參數 > env > config > 硬編」，**model 補 `TEI_MODEL_ID` env（DEF-92-001）、dimension 補 `TEI_EMBED_DIMENSIONS` env（DEF-92-002，`.isdigit()` 檢核）**。
- 驗證：既有 embedder 42 測 + lint 8 kept（adapter import EmbedderConfig 未破契約，同 minimax 前例）；config=None + 無 env 時 byte-level 零退化。

### W-92-3：測試（8 個）+ MUT 突變驗牙
- `test_embedder_contract.py` +6（RTM-92-2/3/4/5：bge config 兜底、env>config、ctor>env>config、no-config 零退化、TEI_MODEL_ID env、TEI_EMBED_DIMENSIONS env；全 hermetic delenv）。
- `test_config_validation.py::TestEmbedderConfig` +2（RTM-92-1：bge-m3 預設 + config.yaml 載入；含「無 bge_m3_api_key」機密邊界斷言）。

### §4.2 MUT 突變驗牙（DEF-92-001/002 防復活）
- **MUT-92-1**（DEF-92-001）：拔 `bgem3_local.py` 的 `or os.environ.get("TEI_MODEL_ID")` 一行 → `test_bge_model_from_env` + `test_bge_env_overrides_config`（model 段）**雙雙轉紅** → Edit 還原 → 轉綠。
- **MUT-92-2**（DEF-92-002）：拔 `elif dim_env.isdigit(): self.dimension = int(dim_env)` 分支 → `test_bge_dimension_from_env` + `test_bge_env_overrides_config`（dim 段）**雙雙轉紅** → Edit 還原（完整還原分支、無死碼殘留）→ 轉綠。
- 結論：測試對 DEF-92-001/002 有牙（env 讀取一旦被移除即被攔下）。突變序列化執行（不與全套並行，避 parallel-mutation 假紅）；還原後 git diff 即本輪正常改動，無突變殘留。

---

## §5 零退化驗證矩陣（階段四）

| 檢查 | 命令 | 通過條件（floor=91 輪實測） | 實測 |
|------|------|----------------------------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q`（清 cache fresh） | ≥ 3544 passed / 0 failed（新測只增） | ✅ **3552 passed / 0 failed / 122 skipped**（73.67s；基線 3544 +8，精確零退化） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | ✅ **8 kept / 0 broken**（bgem3 import EmbedderConfig 未破契約） |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | ✅ **violations=0**（total=19885 / cap=20438） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ **OK**（Snapshot + sprint 骨架對齊） |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **N/A（種類一）**：本輪零碰 `*.tla`/FSM/框架本體 | ✅ N/A — `git status` 鐵證改動全在 AutoClaude + 根 docs，無 `AISDLC_SDD/` / `*.tla` |
| DAL 等價 | equivalence job | **N/A（種類二）**：`tests/equivalence/` 隨全套通過、本輪無新 DAL/checkpoint 改動 | ✅ N/A — `tests/equivalence/` 隨全套 3552 通過；本輪零碰 DAL/checkpoint |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | **N/A（種類一）**：未碰 `*.tla`/`_HAPPY_PATH` | ✅ N/A — 同上 git status 鐵證；非 pytest 全套、需 Java |

---

## §6 多專家 Zero-Trust 審查

三鏡主樹並行派發（含 untracked 計畫書 → 依 DEF-24-001 主樹禁 worktree；無並行突變；分工避 cache 互踩：僅 SA-SD 跑全套清 cache、Architect lint/LOC/架構、QA 唯讀）。完整證據見 [docs/06_quality/AutoSDD_ZeroTrust_Audit_92.md](../06_quality/AutoSDD_ZeroTrust_Audit_92.md)。

| 鏡 | 結論 | 重點 |
|----|------|------|
| Architect | **OVERALL PASS（P0=0/P1=0/P2=0）** | adapter→utils.config 同 minimax_embedder:24 前例（lint 8 kept）、機密邊界 `_PROTECTED_FIELDS` 3 欄不變（TEI 全非機密無新欄）、additive 零退化、Thin Facade 零碰、§3.1 四點宣稱相符 |
| SA-SD | **OVERALL PASS（P0=0/P1=0）** | 親跑 **3552 passed**（複核屬實）；`git show HEAD` 證 DEF-92-001/002「修復前確無 TEI_MODEL_ID/TEI_EMBED_DIMENSIONS env 讀取」；四處設定（dataclass/config.yaml/adapter 硬編/.env.example）零漂移；計畫書宣稱 vs 程式碼逐項一致 |
| QA | **OVERALL PASS（P0=0/P1=0，P2=1 已修）** | 8 新測皆真回歸鎖、6 contract hermetic、RTM-92-1~5 全覆蓋、DEF-92-001/002 各有防復活鎖、MUT-92-1/2 驗牙邏輯成立 |

**P2 當場修正（不延後，遵 no-defer-unless-justified 紀律）**：
- （QA）本輪讓 adapter 開始讀 `TEI_EMBED_DIMENSIONS` env 後，3 個既有 bge 測試（`test_bge_dimension_default_1024` / `test_bge_embed_preserves_order_and_count` / `test_bge_dim_mismatch_raises`）未清該 env→開發者 shell 污染會 flaky（本輪改動暴露的既有隱患，屬「清自己 mess」）。**修**：3 測各補 `monkeypatch.delenv("TEI_EMBED_DIMENSIONS")` + hermetic docstring；adapter 邏輯零改。**實證**：`TEI_EMBED_DIMENSIONS=512` 污染下修前會 fail、修後 3 測仍綠；P2 修復未動搖數字（3552 不變）。

---

## §7 結語

本輪（C 軌）完成 90→91→92 設定來源治理三部曲的收尾——把最後一塊 embedder（bge-m3 本地 TEI）的非機密設定收進 config.yaml，**embedder 非機密設定治理至此閉環**（minimax@91 + bge-m3@92）。核心價值不在「加 config 欄位」，而在 zero-trust 重偵察揪出並修掉三個真缺陷：

- **DEF-92-001**（`.env.example` 宣告 `TEI_MODEL_ID` 但 adapter 從未讀取）→ W-92-2 補 env + config 兜底（MUT-92-1 驗牙）。
- **DEF-92-002**（`.env.example` 宣告 `TEI_EMBED_DIMENSIONS` 但 adapter 從未讀取）→ W-92-2 補 env〔`.isdigit()` 檢核〕+ config 兜底（MUT-92-2 驗牙）。
- **DEF-92-003**（adapter 無 config 層 + config.yaml 無 bge-m3 欄位，與 91 輪治理不一致）→ W-92-1 補 EmbedderConfig bge_m3_* + config.yaml + adapter config 層。

**校正**：掌舵者描述「TEI_URL/TEI_MODEL_ID 還是只走 env」——實況比這更嚴重：`TEI_MODEL_ID`/`TEI_EMBED_DIMENSIONS` 兩個 env 白紙黑字宣告卻**從沒被讀過**（兩個漏接，比 91 輪單一漏接更甚），且 adapter 連 config 層都沒有。動工前親驗現況、勿信描述（沿 improving_91 教訓①）。

零退化：fresh 全套 **3552 passed / 0 failed / 122 skipped**（基線 3544 +8，精確）、lint 8 kept、LOC violations=0、snapshot OK、零碰框架本體（維持 v0.27）。`L_合體=min(A,B,C)=L5` 不變。

**下一份 improving_93 候選**：(a) SD_09 W1 觀察期 #1 source-sha 閘門（~6/29 已到期可啟）；(b) DEF-19-001 catch 歸因覆蓋面推進；(c) 真 token session 跑更長 playbook 取 pty/sdk 逐步驟實測差異（載具 improving_76/86 已備 per-step）。
