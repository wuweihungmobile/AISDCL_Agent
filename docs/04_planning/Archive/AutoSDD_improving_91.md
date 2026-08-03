# AutoSDD_improving_91 — embedder 非機密設定收進 config.yaml：補齊 ConfigResolver 早已預留的 embedder 槽位（C 軌）

> **本輪柱位**：**C 軌（指揮官 AutoClaude 自身能力：LLM/設定來源治理收尾）**。對齊北極星第 1 點——AutoClaude＝以微核心 + DAL 三後端管理的 Playbook 引擎，設定來源治理是其可運維性基座。**90 輪統一了 chat（MinimaxBrain）的 base_url/model「非機密預設唯一權威源」（commit 6daa540）；本輪把同一治理紀律延伸到 embedder——目前 embedder 非機密設定完全游離在 config.yaml 之外、且 `config_resolver.py` 早已為 `embedder.api_key` 預留 RBAC 槽位卻無對應 model，本輪補齊此既有缺口。**
> **下一份**：improving_92。
> **掌舵者裁示**：2026-06-27 四選一裁定本輪標的＝**「方案 B：embedder 設定收進 config.yaml」**（AskUserQuestion 紀錄；候選另含 SD_09 W1 source-sha 閘門、DEF-19-001 catch 覆蓋、先掃缺陷帳本再定）。承接 90 輪 §問題 2「方案 B 排入 improving_91」之承諾。
> **框架版**：本輪零碰 AISLDC_SDD 框架本體（生產碼全在 AutoClaude `utils/config.py` + `infra/adapters/minimax_embedder.py` + `config.yaml`/`.env.example` 資料檔 + 測試）→ 免 Copy-on-Evolve、維持 v0.27。`L_合體=min(A,B,C)=L5` 不變（設定來源治理＝可運維性加固，非成熟度推進）。

---

## §1 本輪輸入（自上輪繼承）

### 1.1 improving_90 結案狀態（RTM 收尾）
- improving_90＝C 軌 production Kernel self-correction「regex+evaluator 雙閘並存」真模型端到端真跑 + regex 約束保留可觀測性 marker（commit 65550b3）。
- 已完成 W 項：W-90-1（真 Minimax M2.7 × 真 Claude 端到端真跑首跑即綠）、W-90-2（observability-only marker `=== REGEX CONTRACT PRESERVED ===` + 載具解析 + 3 測 + MUT-90-1 突變驗牙）。未完成 W 項：無。
- 上輪審計三鏡（Architect / SA-SD / QA）全 OVERALL PASS（P0=0/P1=0）。
- 額外：90 輪結尾完成「方案 A」config 治理（commit 6daa540）——config.yaml=非機密預設唯一權威源、.env 刪重複 MINIMAX_BASE_URL/MINIMAX_MODEL；並承諾「方案 B（embedder 收進 config.yaml）排入 improving_91」。**本輪即兌現方案 B。**

### 1.2 階段一基線（2026-06-27 實測）
- AutoClaude 全套 pytest（清 cache 後 fresh）：**3535 passed / 0 failed / 122 skipped**（74.72s）。floor＝3535（90 輪實測值），新測試只增不減。

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
| DEF-91-001 | P3 | MinimaxConfig dataclass 預設值滯後（`config.py:14-15` = `api.minimax.chat`/`MiniMax-Text-01`，vs config.yaml `api.minimax.io`/`MiniMax-M2.7`）——90 輪 config 治理只改 config.yaml、未同步 dataclass 預設；config.yaml 缺 minimax 欄位時 fallback 到舊端點/舊 model（實證見 §3.0）。本輪 W-91-3 修。 |
| DEF-91-002 | P3 | `.env.example:54` 宣告 `MINIMAX_EMBED_MODEL` env，但 `minimax_embedder.py:38,51` `model_id` 硬編簽章預設 `"embo-01"`、**從未讀取該 env**——文件 vs 實況不符（功能上 embo-01 恰等於 .env 範例值故未爆，但宣稱可配置實則不可）。本輪 W-91-2 修（補 env + config 讀取）。 |
| DEF-91-003 | P3 | `config_resolver.py:49`（`_PROTECTED_FIELDS` frozenset 起 :47）已含 `"embedder.api_key"`，但 `AppConfig` 無 `EmbedderConfig`——(a) RBAC 保護一個幽靈欄位（保護無效）；(b) 使用者在 config.yaml 寫 `embedder:` 區塊被 Pydantic `extra=ignore` 靜默丟棄（實證見 §3.0）。本輪 W-91-1 補齊 EmbedderConfig 使 RBAC 槽位生效。 |

---

## §2 階段一實測（Zero-Trust Re-Audit）

| 項目 | 命令 | 實測結果 |
|------|------|---------|
| (a) AutoClaude 全套 pytest | `python -m pytest tests/ -q`（清 cache 後 fresh） | **3535 passed / 0 failed / 122 skipped** |
| (b) lint-imports | （階段四回填） | — |
| (c) AISDLC_SDD ci-gate | N/A（本輪零碰框架本體，見 §5 矩陣 N/A 標註） | — |
| (d) 上輪構件存在性 | 90 輪 marker `=== REGEX CONTRACT PRESERVED ===` 仍在 `core/kernel.py`；config 治理 commit 6daa540 已落地 config.yaml | ✅ |
| (e) 缺陷帳本 open 項重現 | 見 §1.3（本輪 scope 外者維持） | — |
| (f) 外部工具依賴 | 本輪**不需真跑 embedding API**（純設定治理層，新測試以建構參數/env/config 驗優先序，不打真 endpoint）；機密 api_key/group_id 維持只走 env，無新 headless 自動化假設 | ✅ 無 DEF-10-002a 類風險 |

**硬閘**：(a) 基線 3535 passed / 0 failed，未低於上輪、無 failed → **通過，准進階段二**。

---

## §3 增量設計（階段二）

### §3.0 設計依據實證（zero-trust，不憑記憶斷言 Pydantic 行為）
```
$ python -c (verify_defects.py)
has embedder attr: False                 # ← DEF-91-003：embedder 區塊被靜默丟棄
extra policy: default(ignore)            # ← AppConfig 無 model_config，Pydantic v2 預設 extra=ignore
minimax default base_url: https://api.minimax.chat/v1/text/chatcompletion_v2   # ← DEF-91-001 舊值
minimax default model: MiniMax-Text-01                                          # ← DEF-91-001 舊值
```

### §3.1 現況事實（階段一偵察 + 親驗）
- **embedder 設定讀取**（`minimax_embedder.py:44-60`）：全在 adapter `__init__` 內讀 env，無 config 兜底。
  - `api_key` ← 參數 or `MINIMAX_API_KEY` or `""`（**機密**，與 chat 共用同一 key env）
  - `group_id` ← 參數 or `MINIMAX_GROUP_ID` or `""`（**機密/帳號識別**）
  - `base_url` ← 參數 or `MINIMAX_EMBED_BASE_URL` or 硬編 `"https://api.minimax.io/v1/embeddings"`
  - `model_id` ← 僅參數，預設硬編 `"embo-01"`（**連 env 都沒讀** → DEF-91-002）
  - `dimension` ← 參數 or `MINIMAX_EMBED_DIMENSIONS`(env) or 硬編 `1024`
  - `timeout_seconds` ← 僅參數，預設硬編 `30.0`
- **chat 範本模式（要對齊的精神）**（`main.py:103-114`）：`os.environ.get(...) or cfg.minimax.xxx` → **env 優先、config 兜底**。優先序在 wiring 層，`MinimaxClient` 只收最終值。
- **ConfigResolver**（`config_resolver.py`）：4 層解析（global<workflow<step<runtime）；`_PROTECTED_FIELDS` 含 `embedder.api_key`（runtime layer 不可覆寫機密）——**早已預期 EmbedderConfig 存在**。
- **embedder production 消費者**：`infra/services/embedding_writer.py` / `reembed_batch.py`（非 main.py 主鏈，SD_06 W3 落 adapter+port+contract test，未接入 main wiring）。

### §3.2 <Architecture_Design_Review>（寫任何 Python 前必輸出）
1. **架構純潔性**：是否造 God-object / 破壞 Thin Facade？
   → 否。`EmbedderConfig` 為 `utils/config.py` 內一個 ~12 行 Pydantic BaseModel（與既有 MinimaxConfig/StorageConfig 同級同構），收進 `AppConfig` 一個欄位。adapter `__init__` 僅擴充既有 `or` 兜底鏈（additive 參數），無新類別、無業務邏輯下沉。playbook_runner 零碰。
2. **持久化相容**：新狀態是否 additive 寫入 PlaybookCheckpoint？DAL 三後端零停機？
   → N/A——本輪不碰 checkpoint/DAL/狀態機。`EmbedderConfig` 是啟動期設定，非執行期狀態。AppConfig 新增欄位為 additive（有 default_factory），舊 config.yaml 無 embedder 區塊時自動用預設（零退化）。
3. **安全防護網（CONDITIONAL）**：本輪是否新增「從文件生成指令」路徑？
   → 否。EmbedderConfig 是 base_url/model/dimension/timeout 純資料欄位，不進 shell、不組指令。CONDITIONAL 三層防禦無新攻擊面。
4. **對外 I/O 安全（ToolInvocationPort）**：是否新增外呼路徑？
   → 否。本輪只改 embedder 的「設定如何被讀」，不改 embedder「如何呼叫 API」（embed() 路徑零碰）。allowlist/SSRF 攻防無新增需求。
   → **機密邊界守則**：`EmbedderConfig.api_key` 欄位**定義但預設空字串**（呼應 MinimaxConfig.api_key="" 慣例），機密一律由 env `MINIMAX_API_KEY` 提供、**絕不入庫 config.yaml**；`group_id`（帳號識別）**不放入 EmbedderConfig**，維持只走 env `MINIMAX_GROUP_ID`（與 chat config 無 group_id 一致）。ConfigResolver `embedder.api_key` RBAC 保護本輪起真正生效。

### §3.3 W 項（本輪 ≤3 項，聚焦）

#### W-91-1：新增 EmbedderConfig + 收進 AppConfig + config.yaml embedder 非機密區塊（修 DEF-91-003）
- **介面 delta**（`utils/config.py`）：新增
  ```python
  class EmbedderConfig(BaseModel):
      # 非機密預設（入庫共享，與 minimax chat 治理一致）
      base_url: str = "https://api.minimax.io/v1/embeddings"
      model: str = "embo-01"
      dimension: int = 1024
      timeout_seconds: float = 30.0
      # 機密：留空，由 env MINIMAX_API_KEY 提供，絕不入庫（呼應 ConfigResolver RBAC embedder.api_key）
      api_key: str = ""
  ```
  並於 `AppConfig` 加 `embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)`。
- **config.yaml** 加 `embedder:` 區塊（非機密：base_url/model/dimension/timeout_seconds，api_key 留空 + 註解說明）。
- **LOC 預算落點**：config.py 為 data tier（≤150）？實為設定模組，現 277 行——屬既有檔，新增 ~14 行；以實際 `check_loc_budget.py` 分級為準（階段四驗）。
- **importlinter 影響**：EmbedderConfig 居 `utils/config.py`，無新跨層 import → 預期 8 kept 不變。
- **修 DEF-91-003**：補齊後 `AppConfig.model_validate({"embedder": {...}})` 不再丟棄；ConfigResolver `embedder.api_key` RBAC 槽位生效。

#### W-91-2：MinimaxEmbedderAdapter 對齊「建構參數 > env > config 兜底 > 硬編」（修 DEF-91-002）
- **介面 delta**（`minimax_embedder.py:32-60`）：`__init__` 新增 additive 參數 `config: Optional[EmbedderConfig] = None`（或 duck-typed，視 importlinter 決定，見下）；`model_id` 簽章預設 `"embo-01"` → `Optional[str] = None`（向後相容：顯式傳值不變）。兜底鏈改為：
  - `base_url = base_url or env(MINIMAX_EMBED_BASE_URL) or (config.base_url if config) or 硬編`
  - `model_id = model_id or env(MINIMAX_EMBED_MODEL) or (config.model if config) or "embo-01"`（**補 env 讀取＝修 DEF-91-002**）
  - `dimension`：參數 > env > (config.dimension) > 1024
  - `timeout_seconds`：參數 > (config.timeout_seconds) > 30.0
  - `api_key`：參數 > env(MINIMAX_API_KEY) > (config.api_key) > ""（機密，env 優先）
  - `group_id`：參數 > env(MINIMAX_GROUP_ID) > ""（**不吃 config**，維持機密邊界）
- **零退化保證**：`config=None` 時 byte-level 等同現況（所有 `(config.x if config else None)` 短路為 None，兜底鏈塌回原 `or` 鏈）。
- **importlinter 風險點**：adapter（`infra/adapters/`）import `utils.config.EmbedderConfig` 是否破契約？現有 8 規則無「adapter 不可 import utils」條款，預期 kept；若 lint broken 則改 duck-typing（type hint 用 `TYPE_CHECKING` 或接受 `Any` 具 `.base_url/.model` 屬性）。階段四 lint-imports 實測決定。
- **LOC 預算**：minimax_embedder.py 為 adapter tier（≤400），現 ~210 行，新增 ~8 行 → 安全。

#### W-91-3：修 DEF-91-001（dataclass 預設對齊）+ .env.example 校正 + 補測試
- **修 DEF-91-001**（`config.py:14-15`）：MinimaxConfig 預設 `base_url`/`model` 對齊 config.yaml 當前值（`api.minimax.io/.../chatcompletion_v2`、`MiniMax-M2.7`），消除「config.yaml 缺欄位時 fallback 到舊端點」漂移。
- **.env.example 校正**：確認 embedder 相關註解與新 config 兜底語意一致（標明 base_url/model/dimension 可由 config.yaml 兜底，api_key/group_id 機密只走 env）。
- **補測試**（RTM 需求列見 §3.4）：EmbedderConfig 載入 round-trip、優先序（env>config）、config=None 零退化、RBAC `embedder.api_key` runtime 拒寫、DEF-91-002 model env 兜底、DEF-91-001 dataclass 預設對齊。

### §3.4 RTM 需求列（SCG-5 對應，實測欄階段三/四回填）
| RTM | 需求 | 驗證測試 | 實測 |
|-----|------|---------|------|
| RTM-91-1 | EmbedderConfig 可由 config.yaml 載入且不被丟棄（修 DEF-91-003） | `test_config_validation.py::TestEmbedderConfig::test_embedder_block_loaded_not_dropped` + `::test_embedder_defaults_are_non_secret` | ✅ PASS |
| RTM-91-2 | ConfigResolver `embedder.api_key` runtime 覆寫被 RBAC 拒（槽位生效） | `test_config_resolver.py::test_runtime_cannot_override_protected_embedder_api_key` | ✅ PASS |
| RTM-91-3 | adapter 優先序：建構參數 > env > config 兜底 > 硬編 | `test_embedder_contract.py::test_embedder_config_fallback_when_no_env` + `::test_embedder_env_overrides_config` + `::test_embedder_ctor_arg_overrides_env_and_config` | ✅ PASS |
| RTM-91-4 | adapter `config=None` 時 byte-level 零退化（現況行為不變） | `test_embedder_contract.py::test_embedder_no_config_backward_compat` | ✅ PASS |
| RTM-91-5 | DEF-91-002：model 由 `MINIMAX_EMBED_MODEL` env / config 可配置 | `test_embedder_contract.py::test_embedder_model_from_env`（+ MUT-91-1 驗牙） | ✅ PASS |
| RTM-91-6 | DEF-91-001：MinimaxConfig dataclass 預設對齊 config.yaml | `test_config_validation.py::TestEmbedderConfig::test_minimax_dataclass_default_aligns_with_config_yaml` | ✅ PASS |

### §3.5 SCG 進程（B 軌 dogfooding 形式，本輪 C 軌作業）
- SCG-0/1：本計畫書（§1 輸入 + §2 實測 + §3 設計）＝載體。
- SCG-2：§3.3 介面 delta ＝設計。
- SCG-3：無 OpenAPI 契約（純內部設定模組），N/A。
- SCG-4：實作 PR（階段三）。
- SCG-5：§3.4 RTM（階段三/四回填實測）。

---

## §4 實作與雙重驗證（階段三）

### W-91-1：EmbedderConfig + AppConfig + config.yaml（修 DEF-91-003）
- `autoclaude/utils/config.py`：新增 `class EmbedderConfig`（base_url/model/dimension/timeout_seconds/api_key，含機密邊界 docstring）；`AppConfig` 加 `embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)`。
- `config.yaml`：新增 `embedder:` 區塊（非機密預設 + 治理註解；api_key 留空、group_id 不列）。
- 驗證（scratchpad/verify_w91_1.py，已跑）：`hasattr(c,"embedder")=True`、config.yaml 載入 base_url/model/dimension 正確、`RBAC OK: embedder.api_key protected`（runtime 覆寫被 ProtectedFieldError 擋）。

### W-91-2：adapter env>config 兜底（修 DEF-91-002）
- `autoclaude/infra/adapters/minimax_embedder.py`：`from ...utils.config import EmbedderConfig`（同 pty_executor:28 既有慣例）；`__init__` 新增 additive `config` 參數；`model_id`/`timeout_seconds` 簽章預設改 `None`（向後相容）；五欄位兜底鏈改「建構參數 > env > config > 硬編」，**model 補 `os.environ.get("MINIMAX_EMBED_MODEL")`**（DEF-91-002）；group_id 維持只走 env（機密邊界）。
- 驗證：embedder 相關 38 測 + 本輪 5 新優先序測全綠（config=None byte-level 零退化、config 兜底、env>config、ctor>env>config、model from env）。

### W-91-3：DEF-91-001 + .env.example + 測試
- `autoclaude/utils/config.py`：MinimaxConfig 預設 `base_url`/`model` 對齊 config.yaml（`api.minimax.io`/`MiniMax-M2.7`）+ DEF-91-001 註解。
- `.env.example`：embedder 區塊治理註解校正（base_url/model/dimension env 改「覆寫用、預設見 config.yaml」並註解化；標明 api_key 共用、group_id 只走 env、DEF-91-002 修復說明）。
- 新增測試（9 個）：`test_embedder_contract.py` +5（RTM-91-3/4/5）、`test_config_validation.py::TestEmbedderConfig` +3（RTM-91-1/6）、`test_config_resolver.py` +1（RTM-91-2）。

### §4.2 MUT 突變驗牙（DEF-91-002 防復活）
- **MUT-91-1**：拔掉 `minimax_embedder.py` 的 `or os.environ.get("MINIMAX_EMBED_MODEL")` 一行（受控突變）→ `test_embedder_model_from_env`（`assert 'embo-01' == 'env-model'` FAIL）+ `test_embedder_env_overrides_config`（`assert 'cfg-model' == 'env-model'` FAIL）**雙雙轉紅** → 以 **Edit 還原**（非 `git checkout`，遵 git-checkout-mutation-revert-hazard 紀律）→ 2 測轉綠。
- 結論：測試對 DEF-91-002 有牙（env 讀取一旦被移除即被測試攔下），回歸防護成立。突變序列化執行（不與全套並行，避 parallel-mutation-audit-collision 假紅）；還原後 git diff 即本輪正常改動，無突變殘留。

---

## §5 零退化驗證矩陣（階段四回填）

| 檢查 | 命令 | 通過條件（floor=90 輪實測） | 實測 |
|------|------|----------------------------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q`（清 cache fresh） | ≥ 3535 passed / 0 failed（新測只增） | ✅ **3544 passed / 0 failed / 122 skipped**（76.02s；基線 3535 +9 新測，精確零退化） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept / 0 broken | ✅ **8 kept / 0 broken**（adapter import EmbedderConfig 未破契約） |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | ✅ **violations=0**（total=19860 / cap=20438） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ **OK**（Snapshot + sprint 骨架對齊） |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **N/A（種類一）**：本輪零碰 `*.tla`/FSM/框架本體 | ✅ N/A — `git status` 鐵證改動全在 AutoClaude + 根 docs，無 `AISDLC_SDD/` / `*.tla` |
| DAL 等價 | equivalence job | **N/A（種類二）**：`tests/equivalence/` 隨全套通過、本輪無新 DAL/checkpoint 改動 | ✅ N/A — `tests/equivalence/` 9 檔隨全套 3544 通過；本輪零碰 DAL/checkpoint |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | **N/A（種類一）**：未碰 `*.tla`/`_HAPPY_PATH` | ✅ N/A — 同上 git status 鐵證；非 pytest 全套、需 Java |

---

## §6 多專家 Zero-Trust 審查

三鏡並行主樹派發（無並行突變、含 untracked 計畫書 → 主樹；分工避 cache 互踩：僅 SA-SD 跑全套清 cache）。完整證據見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_91.md`。

| 鏡 | 結論 | 重點 |
|----|------|------|
| Architect | **OVERALL PASS（P0=0/P1=0）** | 微核心純潔（adapter→utils.config 同 pty_executor:28 前例、lint 8 kept）、機密邊界（api_key/group_id 不入庫、RBAC 由幽靈欄位修正為生效）、additive 零退化、Thin Facade 零碰 |
| SA-SD | **OVERALL PASS（P0=0/P1=0）** | fresh 全套 **3544 passed**（複核屬實）；計畫書宣稱 vs 程式碼逐項一致；git 鐵證 DEF-91-002「修復前從未讀 MINIMAX_EMBED_MODEL」；四處設定（dataclass/config.yaml/adapter 硬編/.env.example）**零漂移** |
| QA | **OVERALL PASS（P0=0/P1=0，P2=2）** | 9 測皆真回歸鎖（無恆真假測試）、env 全 hermetic、MUT-91-1 驗牙經碼邏輯確認必然成立、6 RTM × 3 DEF 防復活鎖齊備 |

**P2 當場修正（不延後，遵 no-defer-unless-justified 紀律）**：
1. （QA）`test_embedder_no_config_backward_compat` 補 `_api_key`/`_group_id` 斷言，坐實「byte-level 零退化」涵蓋全 6 欄。
2. （QA）`test_runtime_cannot_override_protected_embedder_api_key` docstring 因果修正——RBAC 攔截純靠 `_PROTECTED_FIELDS` 字串比對、不依賴 AppConfig 欄位；DEF-91-003 區塊丟棄由 `test_embedder_block_loaded_not_dropped` 鎖。
3. （SA-SD）行號微飄 `config_resolver.py:50` → `:49`（計畫書 §1.4/§6-DEF + 缺陷帳本 DEF-91-003）。

修正後受影響測試重跑 **49 passed**（生產碼零碰、3544 不變）。

---

## §7 結語

本輪（C 軌）兌現 90 輪承諾的「方案 B」：把 embedder 非機密設定收進 config.yaml，並補齊 `config_resolver.py` 早已預留卻無對應 schema 的 `embedder.api_key` RBAC 槽位。核心價值不在「加一個 config 欄位」，而在 zero-trust 重偵察揪出並修掉三個真缺陷：
- **DEF-91-003**（RBAC 幽靈欄位 + config.yaml embedder 區塊被靜默丟棄）→ W-91-1 補齊 EmbedderConfig。
- **DEF-91-002**（`.env.example` 宣告 `MINIMAX_EMBED_MODEL` 但 adapter 從未讀取）→ W-91-2 補 env+config 兜底。
- **DEF-91-001**（90 輪 config 治理殘留：MinimaxConfig dataclass 預設滯後 config.yaml）→ W-91-3 對齊。

零退化：fresh 全套 **3544 passed / 0 failed / 122 skipped**（基線 3535 +9，精確）、lint 8 kept、LOC violations=0、snapshot OK、零碰框架本體（維持 v0.27）。`L_合體=min(A,B,C)=L5` 不變。

**下一份 improving_92 候選**：SD_09 W1 source-sha 閘門（~6/29 已到期可啟）、DEF-19-001 catch 覆蓋推進、bge-m3 TEI 設定亦收進 config.yaml（本輪聚焦 minimax embedder，bge-m3 的 `TEI_URL`/`TEI_MODEL_ID`/`TEI_EMBED_DIMENSIONS` 仍只走 env，可比照方案 B 收尾）。
