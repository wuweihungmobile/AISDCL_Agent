# AutoSDD_improving_89 — C 軌：production logger Windows cp950 編碼容錯（閉合 DEF-87-002）

> **柱位**：C 軌（指揮官 AutoClaude 自身能力）。
> **下一份**：`AutoSDD_improving_90.md`。
> **標的**：閉合 improving_87 真跑揪出、routed 兩輪的 P3 生產缺陷 **DEF-87-002**——AutoClaude
> 生產 logger 的 console handler 在 Windows cp950 撞非 ASCII（✓ U+2713）丟 `UnicodeEncodeError`
> 的非致命噪音。
> **掌舵者裁示**（2026-06-27，AskUserQuestion）：本輪主 W 項鎖定 **DEF-87-002 logger cp950**（單項）。

---

## §1 本輪輸入（自上輪 improving_88 繼承）

### 1.1 上輪（88）完成項與遺留
- improving_88＝C 軌（觸及 A 軌）：production Kernel `_preserve_output_contract` 閉合 DEF-87-001
  （Brain CORRECTION 取代 `task.prompt` 丟失 `expected_output_regex` 隱含輸出約束 → regex 閘永不過
  → escalate）。commit `a946f80` 直推 main。
- 88 結案無「未完成 W 項」；遺留候選三項：**DEF-87-002 logger cp950**（本輪）、真模型端到端真跑驗
  production Kernel 收斂、SD_09 W1 source-sha 閘門（~6/29，今天 6/27 未到期）。

### 1.2 缺陷帳本 open/routed 本輪處置
- **DEF-87-002**（P3，open/routed）→ **本輪閉合**（見 §3）。
- DEF-01-007（cc-switch 未安裝，環境工具缺裝）→ 非本輪範圍，維持 open。
- DEF-01-009（sdd_governance_plugin.py 貼 250 上限 watch）→ 本輪零擴充、不觸發，維持 watch。

### 1.3 上輪審計遺留
- 無標記「延後／下輪」之 QA 條目須在本輪先處理（88 三鏡全 PASS、無遺留）。

---

## §2 階段一實測（Zero-Trust Re-Audit，2026-06-27）

> 全部真實執行，禁文件宣稱當事實。硬閘：基線出現任何 failed 或低於上輪 3519 passed → 停機。

| 檢查 | 命令 | 實測結果 | 對照上輪 | 判定 |
|------|------|---------|---------|------|
| AutoClaude 全套 pytest | `python -m pytest tests/ -q` | **3519 passed / 0 failed / 122 skipped** | = 3519 | ✅ PASS |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | = 8 kept | ✅ PASS |
| LOC 分級 | `python tools/check_loc_budget.py` | **violations=0**（19802 / 20438 cap） | = 0 | ✅ PASS |
| Snapshot 新鮮度 | `python tools/snapshot_sync.py --check` | OK（區段對齊） | 對齊 | ✅ PASS |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | pytest not-chaos 全綠（v0.01 1478＋v0.27 1665＋infra 129）、arch_fitness fail=0（3 advisory warn） | 全綠 | ✅ PASS |

**硬閘判定：PASS**（基線零退化、零虛報）。

### 2.1 缺陷現況實證（DEF-87-002 機制仍在 production 碼）
- 觸發點：`autoclaude/main.py:140` `logger.info("Playbook 結束 | %s", result)`，`result` repr
  含 `step_log` 的 `✓`(U+2713)。
- 病灶：`autoclaude/utils/logger.py:32` `console_handler = logging.StreamHandler(sys.stdout)`；
  Windows 預設 cp950，無法編碼 `✓` → `UnicodeEncodeError`，被 logging 模組自捕成 stderr
  "Logging error" 噪音（非致命：autoclaude 仍 exit 0；utf-8 file handler `autoclaude.log` 完整記錄）。
- **缺口確認**：`autoclaude/utils/logger.py` **目前無任何單元測試**（Glob `**/test*logger*.py`
  零命中）——本輪同時補上測試覆蓋。
- 既有 cp950 處置散見於**載具**（`tools/ab_compare_backends.py:588-591`、
  `tools/correction_loop_verify.py:155-158`、`tools/ac4_progress_check.py:384`）皆用
  `sys.stdout.reconfigure(encoding="utf-8")`；但這是**載具層全域改 stdout**，**不適合搬進 production
  logger**（理由見 §3.2）。DEF-82-001 前例＝「載具修、生產 routed」，本輪正是補生產端。

---

## §3 階段二：本輪增量設計

### 3.1 設計目標
讓 AutoClaude 生產 logger 的 console 輸出在**任何 console 編碼（含 Windows cp950）**下都不丟
`UnicodeEncodeError`，杜絕非致命噪音；同時在 utf-8 環境**位元級零退化**。

### 3.2 方案選型（為何不照搬載具的 `sys.stdout.reconfigure`）

| 方案 | 描述 | 否決/採用理由 |
|------|------|--------------|
| (A) `sys.stdout.reconfigure(errors=...)` | 載具現行做法 | ❌ **全域副作用**：改動整個進程 stdout 行為，影響所有寫 stdout 的模組；且 pytest capture / 已被包裝的 stream 可能無 `reconfigure`（`AttributeError`），blast radius 大、不隔離 |
| (B) 重包 `io.TextIOWrapper(sys.stdout.buffer, errors=...)` | 換 handler 的 stream | ❌ pytest capture 時 `sys.stdout` 無 `.buffer` → 環境分支脆弱 |
| **(C) 自訂 `_EncodingSafeStreamHandler`（採用）** | StreamHandler 子類，`emit` 依目標 stream 編碼做 `backslashreplace` sanitize | ✅ **完全隔離**在 autoclaude logger 自己的 console handler，不動全域 `sys.stdout`；utf-8 環境 sanitize 無損（零退化）；純函式冪等；可用 `io.TextIOWrapper(BytesIO, encoding="cp950")` **在 Linux CI 重現 cp950 行為**（測試跨平台可跑） |

### 3.3 介面 delta（`autoclaude/utils/logger.py`）

新增（additive，不改既有公開介面 `setup_logger` 簽名）：

```python
class _EncodingSafeStreamHandler(logging.StreamHandler):
    """console handler：依目標 stream 編碼 sanitize，杜絕 Windows cp950 對非 ASCII
    （如 ✓ U+2713）丟 UnicodeEncodeError 的非致命噪音（DEF-87-002）。
    utf-8 環境 sanitize 為無損 → 零退化；sanitize 為純函式 → 冪等。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            stream = self.stream
            enc = getattr(stream, "encoding", None) or "utf-8"
            # backslashreplace → 不可編碼字元轉 \uXXXX（ASCII），保證後續 write 必可編碼
            safe = msg.encode(enc, errors="backslashreplace").decode(enc, errors="replace")
            stream.write(safe + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)
```

`setup_logger` 內僅一行改動：`console_handler = logging.StreamHandler(sys.stdout)`
→ `console_handler = _EncodingSafeStreamHandler(sys.stdout)`。其餘（formatter / level / 去重註冊）
完全不動。file handler（utf-8）不受影響。

### 3.4 LOC 預算落點
`autoclaude/utils/logger.py` 不屬任何特定 tier pattern → 套 absolute_limit ≤750。現 52 行，
加 class ~17 行 + 1 行改動 ≈ 70 行，遠低於 750；總量 19802→~19820（cap 20438）安全。

### 3.5 `.importlinter` 各 contract 影響分析
新增 class 僅 import `logging`/`sys`（既有），無跨層 import、無 plugin↔plugin、無 Brain↔Executor、
無 utils.observability。**對 8 條 contract 全部零影響**（維持 8 kept / 0 broken）。

### 3.6 checkpoint additive 欄位需求
無。本輪不涉及 PlaybookCheckpoint / DAL。

### 3.7 RTM 需求列（測試先行，§5 回填實測）

| RTM | 驗證意圖（WHY） | 對應測試 |
|-----|----------------|---------|
| RTM-89-1 | cp950 stream 下 emit 含 ✓ **不丟例外、不觸發 handleError**（消除非致命噪音的核心） | `test_rtm_89_1_cp950_stream_no_raise` |
| RTM-89-2 | cp950 環境下不可編碼字元轉為 backslash escape（`✓`）寫出、**整行不遺失** | `test_rtm_89_2_cp950_backslash_escaped_not_dropped` |
| RTM-89-3 | utf-8 環境**零退化**：✓ 原樣寫出（含 U+2713，位元級無損） | `test_rtm_89_3_utf8_lossless` |
| RTM-89-4 | cp950 可編碼的中文（如「結束」）**不被誤 escape**（只 escape 真正不可編碼者） | `test_rtm_89_4_cp950_encodable_cjk_preserved` |
| RTM-89-5 | `setup_logger` 回傳的 console handler 為 `_EncodingSafeStreamHandler` 型別，且重複呼叫去重註冊行為保持（冪等） | `test_rtm_89_5_setup_logger_uses_safe_handler_idempotent` |

突變驗測試有牙：**MUT-89-1**＝移除 `emit` 的 sanitize（直接 `stream.write(msg)`）→ RTM-89-1/89-2
須轉紅（cp950 stream 丟 `UnicodeEncodeError` / handleError），驗測試確實咬住病灶；驗後以 Edit 還原
（非 `git checkout`）。

### 3.8 <Architecture_Design_Review>（寫任何實質 Python 前必輸出）
1. **架構純潔性**：僅在 `utils/logger.py` 新增一個 StreamHandler 子類，無 God-object、無 Thin
   Facade 破壞（logger 非 facade）、無跨層相依。✅
2. **持久化相容**：不新增/不改動 PlaybookCheckpoint 欄位；DAL 三後端零觸碰、零停機維持。✅（N/A：本輪不涉持久化）
3. **安全防護網（CONDITIONAL）**：本輪不新增「從文件生成指令」路徑；純 logging 輸出 sanitize，
   與 CONDITIONAL 白名單無交集。✅（N/A：非指令路徑）
4. **對外 I/O 安全（ToolInvocationPort）**：本輪不新增任何對外工具呼叫/外呼路徑。✅（N/A：純本地 logging）

---

## §4 階段三：實作與雙重驗證

### 4.1 實作摘要
- `autoclaude/utils/logger.py`：新增 `_EncodingSafeStreamHandler`（StreamHandler 子類）+
  `setup_logger` 內 1 行改動（`StreamHandler` → `_EncodingSafeStreamHandler`）。檔案 52→74 行，
  絕對紅線 750 內。
- `tests/test_logger.py`（新建，原無任何 logger 測試）：**7 個測試**——RTM-89-1~5 + 2 個 except 兜底補測
  （`test_def_87_002_handleerror_fallback_on_broken_stream` 覆蓋 stream.write 崩潰走 handleError 不上拋；
  `test_recursionerror_propagates_not_swallowed` 覆蓋 RecursionError 須上拋不被吞）。
- 設計核心：以 `io.TextIOWrapper(BytesIO, encoding="cp950")` 在 utf-8 平台重現 Windows cp950 行為
  → 測試跨平台可跑（Linux CI 亦能驗 cp950）。
- **三鏡審查當場修（Architect P2）**：emit 補 `except RecursionError: raise`（鏡像 CPython
  `StreamHandler.emit` 防無限遞迴語意，原僅 `except Exception` 會誤吞 RecursionError）+ 對應上拋測試。

### 4.2 真跑/突變結果（MUT-89-1）
- 新測單跑：`pytest tests/test_logger.py -v` → **7 passed**（0.21s）。
- **MUT-89-1 突變驗牙**：把 `emit` 的 sanitize 改為 `safe = msg`（直接 write）→
  `pytest tests/test_logger.py` → **3 failed（RTM-89-1/89-2/89-4）/ 3 passed**；stderr 印出真實
  `UnicodeEncodeError: 'cp950' codec can't encode character '✓'`（正是 DEF-87-002 病灶）。
  → 測試確實咬住病灶、有牙。
- 還原：以 **Edit** 把該行改回 `backslashreplace` sanitize（非 `git checkout`）→ 再跑 **6 passed**。

---

## §5 階段四：CI 平價收斂驗證矩陣（結構內嵌自 improving_01 §5.3；通過條件以實測為準）

| 檢查 | 命令 | 通過條件（floor=上輪實測） | 實測 |
|------|------|--------------------------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3519 passed / 0 failed（新測只增不減） | ✅ **3526 passed / 0 failed / 122 skipped**（+7） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken（上輪 8 kept） | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過（logger.py ≤750 absolute） | ✅ **violations=0**（total 19820 / cap 20438） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | ✅ **OK**（區段+sprint 骨架對齊） |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | pytest not-chaos 全綠 + arch_fitness exit<2 | ✅ **全綠**（v0.01 1478＋v0.27 1665＋scripts 129、arch_fitness fail=0） |
| DAL 等價 | equivalence job | 三後端等價（本輪無新 DAL/checkpoint 改動 → 既有測試隨全套通過，無新增 round-trip 契約） | ✅ **`tests/equivalence/` 86 passed**（隨全套通過、本輪無新契約） |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | 條件未觸發：本輪零碰 `*.tla`/FSM/`_HAPPY_PATH`（附 git diff 鐵證）→ N/A（未跑） | **N/A①（未觸發）**：`git diff --name-only` 僅 `logger.py`，零碰 tla/FSM/_HAPPY_PATH |

> **N/A 標註紀律**：五軌 TLC＝「條件未觸發、本輪確實未跑」（純 Python logging 改動，零碰 FSM/tla，
> 須附 git diff 鐵證）；DAL 等價＝「既有測試隨全套已跑通過、本輪無新契約」（須引測試數/路徑，§4 回填）。

---

## §6 Copy-on-Evolve 判定
本輪僅改 AutoClaude 生產碼（`autoclaude/utils/logger.py`）+ 新增測試，**零碰 AISDLC_SDD 框架本體
與任何 `*.tla`/`_HAPPY_PATH`**。→ **免 Copy-on-Evolve**（維持 v0.27）、五軌 TLC **N/A①（未觸發）**。

---

## §7 結案四件套
1. `docs/04_planning/AutoSDD_improving_89.md`（本檔）
2. `docs/06_quality/AutoSDD_ZeroTrust_Audit_89.md`（三鏡審查+複審證據，階段四產出）
3. `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-87-002 → fixed@improving_89，累積更新）
4. 本體免 Copy-on-Evolve（維持 v0.27）

## §8 誠實性標記
- 規格先行：本檔 §1–§3（含 `<Architecture_Design_Review>`、介面 delta、RTM 需求列）於**階段二先落地**，
  §4 實作摘要 / §4.2 突變結果 / §5 實測欄留待階段三/四回填——符合 SDD 規格先行支柱（工程紀律第 4 條）。
