# AutoSDD_ZeroTrust_Audit_91 — improving_91 審計 + 三鏡複審證據（C 軌：embedder 設定收進 config.yaml）

> 對應計畫書：`docs/04_planning/AutoSDD_improving_91.md`。本輪柱位＝C 軌（指揮官 AutoClaude 自身能力：LLM/設定來源治理收尾）。零碰 AISLDC_SDD 框架本體（維持 v0.27）。

---

## 1. 階段一 Zero-Trust 重偵察（實測事實，禁文件宣稱當事實）

| 項目 | 命令 | 實測 |
|------|------|------|
| (a) AutoClaude 全套 pytest（清 cache fresh） | `rm -rf .pytest_cache .hypothesis && python -m pytest tests/ -q` | **3535 passed / 0 failed / 122 skipped**（74.72s） |
| (d) 上輪構件 | 90 輪 marker `=== REGEX CONTRACT PRESERVED ===` 仍在 `core/kernel.py`；config 治理 commit 6daa540 已落地 | ✅ |
| (f) 外部工具依賴 | 本輪純設定治理、不需真跑 embedding API；機密 api_key/group_id 維持只走 env | ✅ 無 DEF-10-002a 類風險 |

**硬閘**：基線 3535 / 0 failed → 通過，准進階段二。

### 1.1 階段一揪出三缺陷（皆有鐵證，入 Defect_Log）
- **DEF-91-001**：MinimaxConfig dataclass 預設滯後 config.yaml。實證：`AppConfig.model_validate({"minimax": {}})` → `base_url=api.minimax.chat...` / `model=MiniMax-Text-01`（舊值）。
- **DEF-91-002**：`.env.example:54` 宣告 `MINIMAX_EMBED_MODEL`，但 `minimax_embedder.py` 修復前 `model_id` 簽章硬編、`__init__` 無該 env 讀取。git 鐵證：`git show HEAD:.../minimax_embedder.py` line 38=`model_id: str = "embo-01"`、line 51=`self.model_id = model_id`，無 `MINIMAX_EMBED_MODEL`。
- **DEF-91-003**：`config_resolver.py:49` `_PROTECTED_FIELDS` 含 `"embedder.api_key"`，但 AppConfig 無 EmbedderConfig。實證：`AppConfig.model_validate({"embedder": {...}})` → `hasattr=False`、`extra=ignore`。

---

## 2. 階段三實作（W-91-1/2/3）+ MUT 驗牙

| W 項 | 改動檔 | 驗證 |
|------|--------|------|
| W-91-1 | `utils/config.py`（+EmbedderConfig +AppConfig.embedder）、`config.yaml`（+embedder 區塊） | scratchpad 驗證：embedder 區塊不再丟棄、RBAC `embedder.api_key` runtime 覆寫被擋 |
| W-91-2 | `infra/adapters/minimax_embedder.py`（+config 參數 + 兜底鏈 + model env 讀取） | embedder 38 既有測 + 5 新優先序測全綠 |
| W-91-3 | `utils/config.py`（MinimaxConfig 預設對齊）、`.env.example`（註解校正）、3 測試檔（+9 測） | 9 新測全綠 |

**MUT-91-1**（DEF-91-002 防復活）：拔 `minimax_embedder.py` 的 `or os.environ.get("MINIMAX_EMBED_MODEL")` → `test_embedder_model_from_env`（`'embo-01' != 'env-model'`）+ `test_embedder_env_overrides_config`（`'cfg-model' != 'env-model'`）**雙轉紅** → Edit 還原（非 git checkout）→ 2 測轉綠。突變序列化執行，無殘留。

---

## 3. 階段四 CI 平價收斂（實測命令輸出）

| 檢查 | 實測 |
|------|------|
| AutoClaude 全套（fresh） | **3544 passed / 0 failed / 122 skipped**（76.02s；基線 3535 +9，精確零退化） |
| lint-imports | **8 kept / 0 broken** |
| LOC budget | **violations=0**（total=19860 / cap=20438） |
| snapshot --check | **OK** |
| AISDLC_SDD ci-gate / 五軌 TLC | **N/A（種類一）**：`git status` 鐵證零碰 `AISDLC_SDD/` 與 `*.tla` |
| DAL 等價 | **N/A（種類二）**：`tests/equivalence/` 9 檔隨全套通過、本輪零碰 DAL/checkpoint |

---

## 4. 多專家三鏡 Zero-Trust 複審（並行主樹派發，僅 SA-SD 跑全套清 cache 避互踩）

### 4.1 Architect 鏡 — OVERALL PASS（P0=0/P1=0）
- 微核心純潔：EmbedderConfig 居 utils/config.py（同 MinimaxConfig 慣例）；adapter import 它與 `pty_executor.py:28`/`shell_evaluator.py:16`/`factory.py:23` 同模式前例，`config.py` 無任何 infra import → 依賴方向正確。
- lint-imports 8 kept / 0 broken；check_loc_budget violations=0（config.py 301 行 data tier、minimax_embedder.py 235 行 adapter≤400）。
- 機密邊界：EmbedderConfig.api_key 預設 ""、config.yaml embedder.api_key ""、group_id 不入 config（adapter:55 無 config 分支）；RBAC 由幽靈欄位修正為生效（補齊 AppConfig.embedder 後 effective() 不再被 extra=ignore 丟棄）；pii_filter.py:64 亦標 embedder.api_key SECRET。
- additive 零退化：config=None 時兜底鏈塌回原行為；model_id/timeout_seconds 簽章改 Optional 向後相容。Thin Facade：playbook_runner 零改動。

### 4.2 SA-SD 鏡 — OVERALL PASS（P0=0/P1=0）
- fresh 全套複核：**3544 passed / 122 skipped**，與計畫書宣稱吻合、0 failed、未低於 floor 3535、精確 +9。
- 計畫書宣稱 vs 程式碼：W-91-1/2/3 介面 delta 與實際 config.py/minimax_embedder.py/config.yaml/.env.example 逐項一致，無虛報。
- RTM：9 測函式名與 §3.4 逐字相符，focused 跑 9 passed。
- 缺陷帳本誠實性：DEF-91-002 以 git 鐵證修復前無 env 讀取；DEF-91-001/003 與程式碼一致。
- 設定治理一致性：dataclass / config.yaml / adapter 硬編兜底 / .env.example 四處 base_url/model/dimension **零漂移**，未自製新漂移。
- 觀察（非缺陷）：行號 :50 實為 :49（已當場修）；dataclass 預設測試以字面值斷言（可接受）。

### 4.3 QA 鏡 — OVERALL PASS（P0=0/P1=0，P2=2）
- Rule 9：9 測皆「業務邏輯改變即會紅」，無恆真假測試。
- 零退化證明：backward_compat hermetic（delenv 三 EMBED env）；原僅斷言 4 欄 → 當場補 _api_key/_group_id 涵蓋全 6 欄。
- env hermetic：所有 MINIMAX_EMBED_* 測試用 monkeypatch，無 flaky。
- MUT-91-1：經碼邏輯確認拔 env 讀取兩測必然 FAIL，驗牙可信。
- 覆蓋：6 RTM × 3 DEF 防復活鎖齊備。
- 兩 P2（皆當場修，不延後）：①backward_compat 補 _api_key/_group_id 斷言；②RBAC 測試 docstring 因果修正。

### 4.4 P2 當場修正後驗證
- 三處修正（補斷言 + docstring 因果 + 行號 :50→:49）後，受影響測試重跑 **49 passed**；生產碼零碰、3544 不變。

---

## 5. 結論

三鏡全 **OVERALL PASS / P0=0 / P1=0**。零退化鐵證 fresh 3544（基線 3535 +9）、lint 8 kept、LOC=0、snapshot OK、零碰框架本體。三缺陷（DEF-91-001/002/003）全 fixed@improving_91 且各有回歸測試防復活。本輪兌現 90 輪「方案 B」承諾，消除設定漂移、不製造新漂移。
