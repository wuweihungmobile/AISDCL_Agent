# AutoSDD_ZeroTrust_Audit_73 — improving_73 多專家 Zero-Trust 審查

> **對應計畫**：[AutoSDD_improving_73.md](../04_planning/AutoSDD_improving_73.md)（A 軌 pty wexpect raw log 觀測缺口修復 DEF-73-001）
> **派發隔離**：三鏡 + 1 複核鏡**全部主樹**並行——本輪含 tracked 未 commit 改動（pty_wrapper.py / test_perception.py / Defect_Log.md）+ untracked 新檔（improving_73.md / 本檔），依 DEF-24-001「審 untracked／未 commit 走主樹」鐵律**禁 worktree**（worktree 由 HEAD 建樹看不到未 commit 內容 → 假陰性）。無並行突變鏡（突變均序列執行、Edit 還原）。

---

## 1. 階段一基線（零信任重偵察，硬閘 PASS）

| 項目 | 命令 | 實測 |
|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3374 passed / 122 skipped / 0 failed**（= improving_72 實測，無退化，硬閘 PASS） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** |
| SDD ci-gate | `bash scripts/ci-gate.sh` | **exit 0**（v0.01:1478 / v0.26:1665 / scripts:129） |
| 缺陷帳本 | open 3 / routed 3（全 P3） | 本輪皆不觸發，維持 |
| 外部依賴形態 (f) | wexpect 4.0.0 本機可 import（非 GUI/PATH 假設陷阱） | 已確認 |

---

## 2. 設計期關鍵零信任查證（動手前實證，避免誤修）

**零成本探針**（本機 wexpect 4.0.0）：`wexpect.spawn("python", args=["-c","print('A');print('B')"], encoding="utf-8")` + 掛自製 `logfile_read` callback + production 同款 `expect([r".+\r?\n", TIMEOUT, EOF])` 迴圈讀。結果（parent 與 SA-SD 鏡各獨立重跑、一致）：

```
READLINE_LINES: ['A\r\nB\r\n']        # child.after 確實讀到全部 6 字元
LOGFILE_READ_CAPTURED_CHARS: 0        # callback 完全不觸發、呼叫清單為空
```

**結論**：(1) DEF-73-001 為真且**與 DEF-72-001 無關**——即使簡單正確指令、輸出確被讀到，`logfile_read` callback 在 wexpect 4.0.0 `expect()` 路徑從不觸發 → raw log 永遠 0 bytes。(2) callback 既從不觸發，改顯式寫入**無雙重記錄**之虞。修復方向正確。

---

## 3. 三鏡審查結論（主樹並行，全 OVERALL PASS、P0=P1=0）

### 3.1 Architect 鏡 — OVERALL PASS（P0=0/P1=0）
- **架構純潔**：生產碼變更僅 `perception/pty_wrapper.py` 單檔（`git diff --stat` 1 file changed），`playbook_runner.py` Thin Facade 零改動；未創 God-object。
- **死碼潔淨**：`_RawLogAdapter` 全倉唯一命中為註解（無活引用）、class 已物理刪除；`logfile_read` 無生產碼掛載；`RawStreamLogger` import 仍被 line 44 使用（非遺留）。
- **微核心紅線**：親跑 lint-imports **8 kept / 0 broken**；無新跨層 import。
- **subprocess 對稱性**：新顯式寫入語意鏡像 `_readline_subprocess`（只寫讀到的行、同 encode/errors 策略）。
- **計畫書無虛報**：§3.2 介面 delta 與實際碼逐項相符。

### 3.2 SA-SD 鏡 — OVERALL PASS（P0=0/P1=0；提出 1 項 P3 並由本輪閉環內修）
- **根因診斷正確**：獨立重跑探針確認 callback 捕獲 0 字元（見 §2）。
- **無雙重記錄 / 治本 / 安全 / 誠實邊界**：皆 PASS（未新增 shell/對外 I/O 路徑；raw_logger.write 無注入面；P3「不影響步驟成功」標註合理）。
- **🔴 發現（P3 非阻擋）**：`_readline_wexpect` index==2（EOF）原直接 `return None`，**未擷取 `child.before` 未換行殘留尾段**（EOF 殘留探針實證 `child.before='TAIL_NO_NEWLINE'` 被丟棄）→ 與 subprocess 路徑（會回傳 EOF 前最後 chunk）**不完全對稱**，計畫書「兩後端一致」需打折。SA-SD 自評 P3 已知限制（不影響步驟評估），建議補記或遞延。
- **獨立複核零退化**：親跑 full pytest 3376/122/0、LOC violations=0、受控突變雙紅→Edit 還原復綠。

### 3.3 QA 鏡 — OVERALL PASS（P0=0/P1=0）
- **全套親跑**：3376 passed / 122 skipped / 0 failed。
- **新測存在 + 受控突變**：2 支 DEF-73-001 回歸測（line 204/225）；突變 `if False and ...` → 雙紅（`b''==b'L1\r\nL2\r\n'`）→ Edit 還原復綠；`git diff` grep `if False`=0、工作樹乾淨交還。
- **lint/LOC/snapshot**：8 kept、violations=0、FRESH。
- **缺陷帳本誠實性**：DEF-73-001 入帳 P3 fixed@improving_73；open 缺陷 recap 與改動範圍一致（僅動 4 檔）。

---

## 4. Audit 閉環內修（SA-SD P3 發現 → 當場修，遵「發現即修不延後」）

依 SA-SD §3.2 發現，於 `_readline_wexpect` index==2 補擷取 `child.before`（EOF 未換行殘留尾段）後再 `return None`，使兩後端 raw 擷取**真正對稱**：

```python
if index == 2:
    # DEF-73-001：EOF 前若有未換行殘留 buffer（child.before），結束前顯式擷取，
    # 與 subprocess 路徑（iter readline 回傳 EOF 前最後一段未換行 chunk）對稱、避免尾段遺失。
    tail = getattr(self._child, "before", None)
    if self._raw_logger and tail:
        self._raw_logger.write(tail.encode(self._encoding, errors="replace"))
    return None
```

+ 新增回歸測 `test_wexpect_raw_log_captures_eof_residual_without_newline`（`_FakeWexpectChild` 加 `eof_tail` → 斷言合成 raw = `b"L1\r\nTAIL_NO_NL"`）+ 受控突變實證（`if False and ...` → 轉紅 `b'L1\r\n'==b'L1\r\nTAIL_NO_NL'`、Edit 還原復綠）。

### 4.1 QA 複核鏡（最終 3377 態獨立複核）— OVERALL PASS（P0=0/P1=0）
> 因 EOF 補修是三鏡通過**後**新增的程式碼變更，依 zero-trust「不自我認證最後一步」紀律（[[no-fabricated-tool-output]]），另派 QA 鏡對最終態獨立複核：

- **全套親跑**：**3377 passed / 122 skipped / 0 failed**（67.09s；= 3374 + 3 新測）。
- **EOF 測非空殼**：`test_wexpect_raw_log_captures_eof_residual_without_newline`（test_perception.py:252）；受控突變 EOF 分支 `if False and ...` → **轉紅**（`AssertionError: b'L1\r\n' == b'L1\r\nTAIL_NO_NL'`）→ Edit 還原 → **復綠**；源碼 `pty_wrapper.py` grep `if False`=0（git diff 中 2 筆 `if False` 皆為文件敘事文字、非源碼殘留，已逐筆查證）。
- **對稱性無雙寫**：index==0 讀 `after`（行匹配時 `before=""`）、index==2 讀 `before`（EOF 殘留），兩不同緩衝段各寫一次，合成 `b"L1\r\nTAIL_NO_NL"` 證無重複。
- **lint/LOC/snapshot**：8 kept、violations=0、FRESH。
- **工作樹**：改動 4 檔（pty_wrapper.py / test_perception.py / Defect_Log.md / improving_73.md）+ 即將新增本 audit 檔，無突變殘留。

---

## 5. 零退化驗證矩陣（最終態實測）

| 檢查 | 通過條件 | 最終實測 |
|------|---------|---------|
| AutoClaude 全套 | ≥3374 / 0 failed | **3377 / 122 / 0** ✅ |
| 架構契約 | 全 kept | **8 kept / 0 broken** ✅ |
| LOC 分級 | 全過 | **violations=0** ✅ |
| Snapshot | 新鮮 | **FRESH** ✅ |
| AISDLC_SDD 閘門 | exit 0 | **exit 0**（v0.01:1478 / v0.26:1665） ✅ |
| 五軌 TLC | 僅 FSM 變更時 | **N/A — 條件未觸發**（git diff 零碰 `*.tla`/FSM；TLC 需 Java+tla2tools、不在 pytest 全套，本輪確實未跑） |
| DAL 等價 | 三後端等價 | **既有 86 等價測試（`tests/equivalence/`）隨全套 3377 通過** ✅；本輪無新 DAL/checkpoint 改動 → 無新增 round-trip 契約 |

---

## 6. 結論

- **三鏡（Architect / SA-SD / QA）+ QA 複核鏡全部 OVERALL PASS、P0=0 / P1=0。**
- SA-SD 鏡唯一 P3 發現（EOF 殘留不對稱）已於本輪閉環內補修並獨立複核，無遺留 routed。
- 零退化矩陣全綠（最終 3377/0），無契約 broken、無 TLC violation（N/A）、缺陷帳本誠實完整。
- 本輪純 AutoClaude 整合層、未動 `AISDLC_SDD/` 任一檔 → 免 Copy-on-Evolve、免五軌 TLC。
- **准予結案。** `L_合體 = min(A=L5, B=L5, C=L5) = L5` 維持。
