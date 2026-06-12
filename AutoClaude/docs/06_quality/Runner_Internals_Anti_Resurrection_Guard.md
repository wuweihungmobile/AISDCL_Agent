# `_runner_internals` 防復活柵欄（Anti-Resurrection Guard）

| 項目 | 內容 |
|------|------|
| 文件版本 | v1.0（SD_Improving_08 W1-T1-B3 落地） |
| 建立日期 | 2026-05-18 |
| 對應規範 | [ADR-SD06-001](../04_planning/ADR/ADR-SD06-001-coordinator-layer-boundary.md) / [SD06_Migration_Guide.md §7.2](../08_deployment/SD06_Migration_Guide.md) / SD_Improving_07 §5 v2 backlog 第 2 項 |
| 適用版本 | SD_Improving_06 W6 G6（2026-05-18）起永久維護 |
| 對應 importlinter Rules | Rule 3 `runner-internals-isolation` + Rule 6 `runner-no-checkpoint-logic` |
| 對應契約測試 | [tests/contract/test_runner_no_checkpoint_logic.py](../../tests/contract/test_runner_no_checkpoint_logic.py) |
| 維護者 | 專案團隊（SD_07/SD_08 後不得刪除本文件） |

---

## 1. 歷史背景與本文件目的

### 1.1 god-class 拆解史

| 階段 | 事件 | 結果 |
|------|------|------|
| Phase 0 ~ SD_05 | `autoclaude/execution/_runner_internals.py` 為 `PlaybookRunner` 17+ 方法的 mixin 容器，最終膨脹至 **1,694 LOC**（god-object） | 違反 ADR-SD07-001 service tier ≤ 500，且承擔多重職責（checkpoint / boot / strategy / prompt） |
| SD_05 W4 | 將 `_fast_path_test_file_check` / `_persist_mutated_playbook` 等 4 方法搬移至 `fast_path_plugin` / `playbook_persistence_plugin` | mixin LOC 持續精簡 |
| SD_06 W2 | `_save_*_checkpoint` 5 個 mixin shim 物理刪除（搬至 `autoclaude/plugins/checkpoint/{_phase_handlers,_token_halt,_escalation,_interrupt,_evolution}.py`），G2 gate AC2-1 強制 `grep -c "_save_.*_checkpoint" == 0` | 雙寫法絕對禁止（❌13） |
| SD_06 W6 | `_runner_internals.py`（1,694 LOC）+ `_runner_compat.py`（238 LOC）兩檔**物理刪除**（2026-05-18） | execution layer 由 17 個薄 facade 模組接管 |
| SD_07 W4 | `_consecutive_compact_failures` property + `_prepend_global_goal_brief` shim 5 處 patch path 物理拔除 + `PlaybookResult` → factory function + KernelResult `halt_for_token` property alias | 殘留邊角 shim 清零 |
| SD_07 W5 | `runner-no-checkpoint-logic` importlinter Rule 6 新增（5 source × 6 forbidden module 雙向阻擋） | 防復活柵欄升級至 importlinter 原生 |
| **SD_08 W1**（本文件落地） | 防復活柵欄文件化 — Migration Guide v2 backlog 第 2 項 | **永久維護**，SD_07/SD_08 不拔除 |

### 1.2 為何要「文件化」防復活柵欄？

`autoclaude/execution/_runner_internals.py` 已於 SD_06 W6 物理刪除，但**所有相關技術機制都仍在運作**：

1. **importlinter Rule 3 仍在執行** — 禁止 `core` / `plugins` 直接 import `autoclaude.execution._runner_internals`
2. **importlinter Rule 6 仍在執行** — 禁止 `playbook_runner` 等 5 個 facade 模組直接 import `checkpoint._phase_handlers` 等 6 個內部模組
3. **grep-based contract test 仍在執行** — `tests/contract/test_runner_no_checkpoint_logic.py` 掃描 `_save_.*_checkpoint` 出現次數
4. **檔案不存在的事實本身就是「契約」** — 任何人重建同名檔案立即被三層柵欄抓出

但這些機制對「新加入專案的開發者」並不直觀。若無文件，6~12 個月後新人可能誤判：
- 「`_runner_internals.py` 已刪除，那 Rule 3 是不是該拔除？」
- 「為什麼有個叫 `runner-no-checkpoint-logic` 的奇怪 Rule？」
- 「`tests/contract/test_runner_no_checkpoint_logic.py` 第 29 行 `_RUNNER_INTERNALS = Path(...)` 指向不存在的檔案，是不是 dead code？」

本文件即為「**防錯誤拔除**」的單一真相來源：明確記載三層防護的設計動機、互補關係、與「絕對不可移除」的書面理由。

---

## 2. 三層防護全景

```
            ┌─────────────────────────────────────────────────────────┐
            │   Layer 1：importlinter Rule 3 runner-internals-        │
            │            isolation（forbidden import）                 │
            │   - 防止 core/plugins 直接 import _runner_internals     │
            │   - 即使有人重新建立同名 .py 也立刻被擋                  │
            └─────────────────────────────────────────────────────────┘
                                    ↑ 互補
            ┌─────────────────────────────────────────────────────────┐
            │   Layer 2：importlinter Rule 6 runner-no-checkpoint-    │
            │            logic（forbidden import）                     │
            │   - 防止 5 個 facade 模組直接 import checkpoint 6 個    │
            │     internal modules                                    │
            │   - 必須走 CheckpointPlugin 公開 API（SSOT）            │
            └─────────────────────────────────────────────────────────┘
                                    ↑ 互補
            ┌─────────────────────────────────────────────────────────┐
            │   Layer 3：grep-based contract test                     │
            │            test_runner_no_checkpoint_logic.py           │
            │   - 掃描 `_save_.*_checkpoint` 出現次數                 │
            │   - 即使有人不 import，僅 copy-paste 同名函式也擋下     │
            └─────────────────────────────────────────────────────────┘
```

### 2.1 Layer 1：importlinter Rule 3 `runner-internals-isolation`

**配置位置**：[.importlinter:66-73](../../.importlinter#L66-L73)

```ini
[importlinter:contract:runner-internals-isolation]
name = _runner_internals must not be imported by core or plugins
type = forbidden
source_modules =
    autoclaude.core
    autoclaude.plugins
forbidden_modules =
    autoclaude.execution._runner_internals
```

**設計動機**（[CLAUDE.md Architecture Snapshot importlinter Rules](../../CLAUDE.md) Rule 3）：
> `autoclaude.execution._runner_internals` 模組已於 SD_06 W6 G6 物理刪除（2026-05-18），但本 contract 保留作為**防復活柵欄**：禁止未來任何人在 `autoclaude.execution` 內重新建立同名模組並被 core / plugins 直接 import。

**互補性質**：
- 對 source = `autoclaude.core` + `autoclaude.plugins`
- 對 forbidden = `autoclaude.execution._runner_internals`（單一 forbidden module）
- 即使該模組目前不存在，importlinter 仍會在 source 端掃描 import；若未來重建，**任何 import 都會被立刻擋下**

### 2.2 Layer 2：importlinter Rule 6 `runner-no-checkpoint-logic`

**配置位置**：[.importlinter:108-166](../../.importlinter#L108-L166)

```ini
[importlinter:contract:runner-no-checkpoint-logic]
name = playbook_runner / strategy modules must not import checkpoint internal modules (use CheckpointPlugin public API)
type = forbidden
source_modules =
    autoclaude.execution.playbook_runner
    autoclaude.execution.steps_orchestrator
    autoclaude.execution.boot_helper
    autoclaude.execution.prompt_dispatcher
    autoclaude.execution.escalation_dumper
forbidden_modules =
    autoclaude.plugins.checkpoint._phase_handlers
    autoclaude.plugins.checkpoint._token_halt
    autoclaude.plugins.checkpoint._builder
    autoclaude.plugins.checkpoint._escalation
    autoclaude.plugins.checkpoint._interrupt
    autoclaude.plugins.checkpoint._evolution
; 附 9 條 ignore_imports 豁免 CheckpointPlugin 內部組成
```

**設計動機**（[.importlinter:108-123](../../.importlinter#L108-L123)）：
> SD_06 W2-T2-14 原以 `tests/contract/test_runner_no_checkpoint_logic.py`（grep-based）掃描 `_runner_internals.py` 內 `_save_.*_checkpoint` 字串。SD_06 W6 G6 `_runner_internals.py` 已物理刪除（2026-05-18），grep contract 失去 enforce 目標。本 contract 改以 importlinter 原生 forbidden 規則替代——禁止 `playbook_runner` 與所有 strategy / facade 模組直接 import checkpoint package 內部實作。
>
> **唯一允許路徑**：`from autoclaude.plugins.checkpoint import CheckpointPlugin`（公開 entry API；SD_05 W3 拆 package 後唯一可調用面）。
>
> 違反此 contract 即代表 runner 重新引入 checkpoint logic 雙寫法（❌13），與 SSOT 原則衝突。

**互補性質**：
- 對 source = 5 個 execution facade 模組（playbook_runner / steps_orchestrator / boot_helper / prompt_dispatcher / escalation_dumper）
- 對 forbidden = checkpoint package 6 個內部 _module（_phase_handlers / _token_halt / _builder / _escalation / _interrupt / _evolution）
- Rule 6 處理「**checkpoint 子模組的 internal API**」，Rule 3 處理「**_runner_internals 整檔的 import**」，兩者不重疊但互補

### 2.3 Layer 3：grep-based contract test `test_runner_no_checkpoint_logic.py`

**配置位置**：[tests/contract/test_runner_no_checkpoint_logic.py](../../tests/contract/test_runner_no_checkpoint_logic.py)

```python
_RUNNER_INTERNALS = Path(__file__).resolve().parents[2] / "autoclaude" / "execution" / "_runner_internals.py"
_PATTERN = re.compile(r"_save_.*_checkpoint")


def _count_matches() -> int:
    if not _RUNNER_INTERNALS.exists():
        return 0
    text = _RUNNER_INTERNALS.read_text(encoding="utf-8")
    return len(_PATTERN.findall(text))
```

**設計動機**（SD_06 W2-T2-14）：
> importlinter 本身僅能管理 module-level import 圖，無法 grep 函式名稱。本 contract 以「字串掃描」形式 enforce W2 末期應達到的「mixin 內無 `_save_*_checkpoint` logic」目標。

**為何 SD_06 W6 物理刪除後仍保留**：
1. **零誤判價值**：當 `_RUNNER_INTERNALS` 檔案不存在時，`_count_matches()` 直接回 0，測試永遠通過 — 不會 false positive
2. **復活即抓**：任何人重建 `_runner_internals.py` 並寫入 `_save_*_checkpoint` 字串，立即 fail
3. **與 Layer 1/2 互補的最後一道網**：importlinter 只看 import 圖，無法防 copy-paste；grep 測試補上這個漏洞

**互補性質**：
- importlinter Rule 3 防「import 圖違規」
- importlinter Rule 6 防「直接 import checkpoint internal」
- grep test 防「不 import 但 copy-paste 同名函式」

---

## 3. 「絕對不可移除」清單

下列三項在 **SD_07 / SD_08 / SD_09+** 任何 Sprint 都**不得移除或弱化**：

| # | 項目 | 不可移除原因 |
|---|------|-------------|
| 1 | `.importlinter` Rule 3 `runner-internals-isolation` | 防止 god-class 復活；移除即喪失 Layer 1 防護 |
| 2 | `.importlinter` Rule 6 `runner-no-checkpoint-logic` + 9 條 `ignore_imports` | 防止 5 facade 重新引入 checkpoint logic 雙寫法（❌13）；移除即喪失 Layer 2 防護 |
| 3 | `tests/contract/test_runner_no_checkpoint_logic.py` 第 29 行 `_RUNNER_INTERNALS` Path 指向不存在檔案 | 這**不是** dead code，而是 Layer 3 防護的核心邏輯（檔案不存在時回 0，重建時抓 fail） |

**若有後續開發者誤判要拔除**，請先閱讀本文件 §1.2 與 §2，並在 ADR 中說明替代防護機制（理論上沒有更輕量的替代）。

---

## 4. 違規偵測流程

### 4.1 觸發點

| 觸發場景 | 哪一層先 fail？ | 後續處理 |
|---------|--------------|---------|
| 有人在 `autoclaude.execution` 內重建 `_runner_internals.py` 並 `from autoclaude.plugins.foo import _runner_internals` | Layer 1（Rule 3）`PYTHONUTF8=1 lint-imports --config .importlinter` 立即 broken | `git revert HEAD` + Architect 確認 |
| 有人在 `autoclaude.execution.playbook_runner` 內 `from autoclaude.plugins.checkpoint._token_halt import handle` | Layer 2（Rule 6）lint-imports broken | `git revert HEAD` + Architect 確認 |
| 有人在 `autoclaude.execution._runner_internals.py` 內定義 `def _save_xxx_checkpoint(...)` | Layer 3 `pytest tests/contract/test_runner_no_checkpoint_logic.py` fail | `git revert HEAD` + QA 確認 |
| 有人**移除** Rule 3 / Rule 6 / grep test | 既有 CI job（`lint-imports` + `pytest tests/`）跑出與本文件 §3 表格不一致 | PR review 須引用本文件 §3 拒絕合併 |

### 4.2 緊急停止協議

對應 [SD08_Execution_Guide.md §5 緊急停止與回退協議](../05_development/SD08_Execution_Guide.md)：

```bash
# 任一 layer fail
PYTHONUTF8=1 lint-imports --config .importlinter   # 期望 6 kept / 0 broken
python -m pytest tests/contract/test_runner_no_checkpoint_logic.py -v   # 期望 3 case 綠

# 違規則回退
git revert HEAD       # 或 git stash
# 後續行動：找 Architect / QA 雙簽才可重啟相關修改
```

---

## 5. 與 SD_Improving_07 §5 v2 backlog 第 2 項的關係

[SD07_Migration_Guide.md §5](../08_deployment/SD07_Migration_Guide.md) 列出三項 SD_08 v2 backlog 非阻塞優化：

| 項目 | 性質 | 阻塞性 | SD_08 W1 決議 |
|------|------|--------|--------------|
| `_impl.py` 物理行精簡（530 → ≤ 500） | 美學改善 | 否 | **(a) 維持合規**（service tier 邏輯行 ≤ 500 達標）；延 SD_09 評估 |
| `_runner_internals must not be imported` contract 拔除 | **防復活柵欄** | **否** | **不拔除**（本文件落地，永久維護） |
| `prompt_builder.py` 416 LOC 拆 package | 美學改善 | 否 | **(a) 維持 .loc-budget.toml override**（純函式集中可讀性高於分散） |

本文件對應第 2 項決議：**SD_08 W1 確認 `_runner_internals` contract 不拔除，並透過文件化避免後續 Sprint 誤判拔除**。

詳見 [SD08_V2_Backlog_Evaluation.md](SD08_V2_Backlog_Evaluation.md) §2。

---

## 6. 對應參考文件

- [ADR-SD06-001-coordinator-layer-boundary.md](../04_planning/ADR/ADR-SD06-001-coordinator-layer-boundary.md) — Layer 1.5 vs Layer 2 邊界
- [SD06_Migration_Guide.md §7.2](../08_deployment/SD06_Migration_Guide.md) — `_runner_internals` 物理刪除紀錄
- [SD07_Migration_Guide.md §5](../08_deployment/SD07_Migration_Guide.md) v1.0 — v2 backlog 三項
- [SD08_V2_Backlog_Evaluation.md](SD08_V2_Backlog_Evaluation.md) — W1-T1-B5 v2 backlog 3 項評估
- [.importlinter](../../.importlinter) — Rule 3 + Rule 6 配置
- [tests/contract/test_runner_no_checkpoint_logic.py](../../tests/contract/test_runner_no_checkpoint_logic.py) — Layer 3 grep-based contract

---

## 7. 文件版本歷史

| 版本 | 日期 | 內容 |
|------|------|------|
| v1.0 | 2026-05-18 | 首版落地 — SD_Improving_08 W1-T1-B3 三層防護全景文件化，確認 SD_07 §5 v2 backlog 第 2 項決議「不拔除」 |
