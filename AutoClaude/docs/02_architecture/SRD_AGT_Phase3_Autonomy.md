# SRD 增補 — Improving_012 Phase 3 自主拆解與工具（A 能力）

**版本**: v1.0 — **SCG-1 ✅ 凍結（koalawu 2026-06-13）** | **建立日期**: 2026-06-13 | **建立者**: sd-architect
**對應計畫**: [AutoClaude_Improving_012.md](../04_planning/AutoClaude_Improving_012.md)（SCG-0 已凍結）
**閘門**: SCG-1（SRD 增補 + Port 介面規格）✅ 已凍結（§SCG-1 確認欄）；其後 **SCG-2（ADR-AGT-001/002）🔴 待確認** → SCG-3 凍結介面後才實作
**涵蓋**: F-A2（ToolInvocationPort + allowlist 安全閘，**先行**）/ F-A1（GoalDecomposer：goal→步驟 DAG→🔴 signoff）

> ✅ **SCG-1 已凍結**（koalawu 2026-06-13 親簽）：本 SRD 範圍與介面規格凍結。**下一道閘門 SCG-2（ADR-AGT-001/002）仍待 🔴 確認**，且任何程式碼實作須待 SCG-2 + SCG-3 介面契約凍結後才啟動。範圍以凍結計畫 §1（F-A2/F-A1）/ §2 / §4 為準，凍結後變更須重開變更單。

---

## 0. 凍結計畫精化聲明（Rule 7 + 流程改善 #1「擴充點實證」+ 本輪 #8「引穩定錨點而非行號」）

| 項目 | 凍結計畫原文 | 本 SRD 精化（附**穩定錨點**：函式/類別名，非行號） |
|------|-------------|--------------------------------|
| Port 數量 | §2「10 ports → 12 ports」（含 ToolInvocationPort / PreferenceStorePort） | 修正：Phase 1 已落 `IPreferenceStore` + `IKbMetricStore`（10→**12**，現況實證 `core/ports/` 12 檔）；本 Phase 僅新增 `IToolInvocation`（**12→13**）。`PreferenceStorePort` 已於 Phase 1 交付，不重複 |
| 訊息發送 | §1 F-A2「訊息發送（延伸現有 notification）」 | AutoClaude 現況：notification 為 **plugin**（`notification_plugin.py`），無正式 `NotifierPort`。F-A2 的 `send_message` 能力**經 EventBus 委派既有 notification plugin**，不直接 import；不新建 notification port |
| Brain 拆解能力 | §1 F-A1「輸入高階 goal → Brain 產出步驟 DAG」 | `IBrain`（`core/ports/brain.py`）現有 `decide_correction` / `decide_escalation` / `capabilities`。F-A1 **新增 `IBrain.decide_decomposition`**（capability flag 守門，舊 adapter 不支援即 raise NotImplemented → GoalDecomposer 拒絕拆解，不靜默退化） |
| 工具能力來源 | §「能力總判定 A」：PtyExecutor 委派之 Claude Code CLI 內建 WebSearch/WebFetch | F-A2 係在 **AutoClaude 層**新增統一抽象 + allowlist 治理（與 CLI 內建工具正交）；adapter 可選擇實作為「呼叫外部 HTTP」或「no-op stub（預設）」，allowlist 為唯一放行依據 |

> 以上為實作層精化，非範圍變更。**待 SCG-1 🔴 確認時逐條覆核**。

### 擴充點實證表（所有宣稱之新增/注入點附**穩定錨點**，實作期須回填 `檔案:行號` + 觸發測試）

| 擴充點 | 規劃落點（穩定錨點） | 觸發驗證（實作期回填） |
|--------|---------------------|----------------------|
| `IToolInvocation` port | `core/ports/tool_invocation.py`（Protocol，零 infra 依賴） | 介面契約測試 |
| Tool adapter | `infra/adapters/tool_invocation_adapter.py`（allowlist 閘 + 審計 log；adapter ≤400） | allowlist 放行/拒絕往返測試 |
| allowlist 設定 | `config.py` 新增 `tool_invocation` 區段（預設 `enabled=False`、`allowlist=[]` = 全 deny） | 預設 deny 測試 |
| send_message 委派 | EventBus event（不直接 import notification plugin，遵守 importlinter Rule 1） | EventBus 委派測試 |
| `IBrain.decide_decomposition` | `core/ports/brain.py`（+ `BrainCapabilities` flag） | capability 守門測試（不支援即拒絕） |
| GoalDecomposer | `execution/goal_decomposer.py`（strategy tier ≤300；DAG 驗證 + ≤24 步硬上限 + 無環檢查） | 超限/含環/signoff 前不執行 三測試 |
| Playbook 草稿產出 | 既有 `models/playbook.py` 序列化（不改 schema，產 YAML 草稿檔） | 草稿可被既有 validator 載入測試 |

---

## 1. F-A2 — ToolInvocationPort + allowlist 安全閘（P1，先行）

### 1.1 介面規格（SCG-3 凍結後才實作 adapter）

```python
# core/ports/tool_invocation.py（Protocol）
@dataclass(frozen=True)
class ToolRequest:
    kind: str          # "web_search" | "http_request" | "send_message"
    target: str        # URL / domain / 通道名
    payload: dict      # 查詢字串 / body / 訊息內容

@dataclass(frozen=True)
class ToolResult:
    allowed: bool      # 是否通過 allowlist
    ok: bool           # 實際呼叫成功與否
    data: dict
    audit_id: str      # 審計 log 關聯鍵

class IToolInvocation(Protocol):
    def invoke(self, request: ToolRequest) -> ToolResult: ...
```

### 1.2 行為（安全閘）

1. **預設 deny**：`config.tool_invocation.enabled` 預設 `False`；即使 `True`，`allowlist` 為空 = 全部拒絕。
2. **allowlist 比對**：`web_search`/`http_request` 比對 `target` 之 domain；不在 allowlist → `ToolResult(allowed=False, ok=False)` + **審計 log（WARN）**，不發出任何外部 I/O。
3. **審計 log**：所有 invoke（放行與拒絕皆然）寫一筆審計記錄（經 `IObservabilityPort`），含 `kind/target/allowed/audit_id`。
4. **send_message**：僅延伸既有 notification 通道，經 EventBus 委派 `notification_plugin`，不開放任意外部端點。
5. **無 Brain 呼叫**：安全閘為純本地判定（domain 比對），不呼叫 Brain。

### 1.3 邊界與約束

- importlinter：新 port 為 Protocol（core 不依賴 infra）；adapter 落 infra；plugin（若需）不直接 import port（走既有 routing / EventBus）。若 GoalDecomposer 需查 allowlist 可用性，經 constructor 注入 port，不 import infra。
- 預設關閉上線：feature flag `tool_invocation.enabled=False`，與 AlertLadder 同模式（flag-off 零行為變更）。

---

## 2. F-A1 — GoalDecomposer（自主任務拆解，P2）

### 2.1 流程

```
高階 goal（字串）
  → IBrain.decide_decomposition(goal, context) 產出候選步驟 DAG（nodes + edges）
  → GoalDecomposer 驗證：
       (a) 步驟數 ≤ MAX_DECOMPOSITION_STEPS（預設 24，config 可調但硬上限 24）
       (b) DAG 無環（拓撲排序成功）
       (c) 每節點具備可執行 prompt（非空）
     任一不通過 → 拒絕（raise + 審計 log），**不重試、不自我放大**
  → 通過 → 產出 Playbook 草稿 YAML（既有 models/playbook.py schema，不改 schema）
  → 🔴 人工 signoff（AskUserQuestion 或 signoff 檔）
  → signoff 前不執行任何步驟；signoff 後交既有 PlaybookRunner 執行
```

### 2.2 有界性保證（對齊 R-9.23 / Rule 8 棘輪）

| 保證 | 機制 |
|------|------|
| 步驟數有界 | `MAX_DECOMPOSITION_STEPS=24` 硬上限；超限直接拒絕（非截斷、非重試） |
| 無環 | 拓撲排序；偵測到環即拒絕 |
| 不自我放大 | 每 run 拆解僅 1 次（不遞迴拆解子步驟）；拆解結果不可再觸發 GoalDecomposer |
| 人工棘輪 | 🔴 signoff 為執行前置硬閘；signoff 記錄（人/日期/goal hash）入審計 |
| Token 成本 | 拆解僅 1 次 Brain 呼叫；驗證走本地（拓撲排序，不呼叫 Brain） |

### 2.3 與既有元件關係

- `IBrain.decide_decomposition` 為新增方法，受 `BrainCapabilities.supports_decomposition`（新 flag）守門；MinimaxBrain 實作，stub/mock brain 回 `False` → GoalDecomposer 對不支援之 brain 拒絕拆解（不靜默降級）。
- 產出之 Playbook 草稿須能被既有 `main.py` Playbook validator 無誤載入（往返測試）。

---

## 3. 風險與緩解（承凍結計畫 §4）

| 風險 | 等級 | 緩解 |
|------|------|------|
| 自主拆解失控 | 高 | ≤24 步硬上限 + 無環 + 🔴 signoff + 不遞迴；超限拒絕不重試 |
| 任意 URL/API 呼叫 | 高 | allowlist + 預設 deny + 審計 log；send_message 僅延伸 notification |
| 回歸（既有閉環） | 中 | 兩 feature flag 預設 off；flag-off 零行為變更（byte-level 控制流一致，比照 F-B1） |
| importlinter/LOC 違規 | 低 | 新 port Protocol；adapter ≤400；GoalDecomposer strategy ≤300；超出拆 package |

---

## 4. 驗收 TC（SCG-5 RTM 對應；實作期須機械核對每條對應測試函式存在 — 流程改善 #6/#7）

| 驗收項 | 規劃測試（實作期落點 + glob 校驗） |
|--------|-----------------------------------|
| allowlist 外呼叫被拒並留審計 log | `tests/test_tool_invocation.py`：預設 deny、空 allowlist 全拒、不在 allowlist 拒絕 + 審計 log 落筆 |
| allowlist 內呼叫放行 + 審計 | `tests/test_tool_invocation.py`：放行路徑 + audit_id 關聯 |
| send_message 經 EventBus 委派 notification | `tests/test_tool_invocation.py`：不直接 import、EventBus 委派 |
| flag-off 零行為變更 | `tests/test_tool_invocation.py`：`enabled=False` 既有流程 byte-level 控制流一致 |
| 拆解超限被拒 | `tests/test_goal_decomposer.py`：> 24 步拒絕、不重試 |
| 拆解含環被拒 | `tests/test_goal_decomposer.py`：環偵測拒絕 |
| signoff 前不執行 | `tests/test_goal_decomposer.py`：signoff 缺失 → 零步驟執行 |
| 不支援 decomposition 的 brain 被拒 | `tests/test_goal_decomposer.py`：capability=False → 拒絕拆解 |
| Playbook 草稿可被既有 validator 載入 | `tests/test_goal_decomposer.py`：往返載入 |

---

## SCG-1 🔴 人工確認（✅ 已確認 koalawu 2026-06-13）

- [x] F-A2/F-A1 範圍與凍結計畫 §1 一致（無範圍擴張）
- [x] §0 精化逐條覆核（Port 13、Brain 新方法、send_message 委派模式）
- [x] 介面規格（`IToolInvocation` / `IBrain.decide_decomposition`）凍結
- [x] 有界性設計（≤24 步 + 無環 + 🔴 signoff + 不遞迴）接受
- [x] 安全閘設計（預設 deny + allowlist + 審計）接受

**確認人**: koalawu　**確認日期**: 2026-06-13　**方式**: 親簽（互動核准後回填，流程改善 #4：文件為唯一追溯源）

---

**相關文件**: ADR-AGT-001（工具安全閘）/ ADR-AGT-002（拆解有界性）— 同屬 SCG-2 待凍結草案。
