# AutoSDD_improving_73 — A 軌 pty wexpect raw log 觀測缺口修復（DEF-73-001）

> **本輪柱位**：**A 軌（整合）**——pty 後端可觀測性訂正（執行器層 raw 軌跡擷取）。
> **下一份**：`AutoSDD_improving_74.md`。
> **誠實級別**：執行器層**可觀測性缺陷修復輪**（揪修 improving_72 真跑遞延的 pty raw log 0 bytes 觀測缺口 DEF-73-001），**非成熟度推進**。`L_合體 = min(A=L5, B=L5, C=L5) = L5` 維持。
> **Copy-on-Evolve / 五軌 TLC**：本輪純 AutoClaude 整合層、未動 `AISDLC_SDD/` 任一檔、未碰 `*.tla`/FSM/DAL → **免 Copy-on-Evolve、免五軌 TLC、DAL 等價 N/A**。

---

## 1. 本輪輸入（自上輪繼承）

### 1.1 improving_72 RTM / 遺留
- improving_72（commit 475a3ef）已結案：A 軌 pty-vs-sdk 完整統計 A/B（兩後端 smoke 真通過 + N=3）、揪修 DEF-72-001（pty 複雜-prompt 殘缺，fixed）。
- improving_72 §8 遞延 improving_73 候選：**(a) pty raw log 0 bytes 觀測缺口**；(b) 更長/觸發 compaction 的 playbook A/B 分 token 峰值；(c) SD_09 W1（時間閘 ~06-29~07-01）。
- 本輪選 **(a)**：候選 (c) 時間閘未到（今日 2026-06-26 < ~06-29）；候選 (b) 屬「需真模型統計、慢、價值在統計對比」，留待時間閘成熟輪一併；候選 (a) 是**具體、可實證、低風險、可單元測試**的執行器層缺陷，當場修最符合「不要無謂延後」紀律。

### 1.2 缺陷帳本 open/routed（階段一複驗）
- open：DEF-01-007（cc-switch GUI，P3，環境工具缺裝）/ DEF-01-009（sdd_governance_plugin LOC watch，P3）/ DEF-62-001（auto_recovery 註解滯後，P3 routed）。
- 本輪未涉多後端 A/B、未動 sdd_governance_plugin、未動 auto_recovery → 三者皆不觸發，維持原狀態（詳見 Defect_Log 本輪 recap）。

---

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit）— 硬閘 PASS

| 項目 | 命令 | 實測 | 判定 |
|------|------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3374 passed / 122 skipped / 0 failed** | 與 improving_72 宣稱一致，**硬閘 PASS** |
| (b) lint-imports | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** | 過 |
| (c) SDD ci-gate | `bash scripts/ci-gate.sh` | **exit 0**（v0.01:1478 / v0.26:1665 / scripts:129） | 過 |
| (d) 上輪構件存在性 | 開檔確認 `_start_wexpect` arg list 修復、`test_wexpect_spawn_passes_args_as_list_not_shell_joined` | 存在無虛報 | 收斂屬實 |
| (e) 缺陷帳本 open 複驗 | open 3 / routed 3 全 P3 | 無 P0/P1/P2，本輪皆不觸發 | 持平 |
| (f) 外部依賴形態 | 本輪 W 項涉 **wexpect**（Windows-only 模組）；零成本探針實證其 callback 行為（見 §3.3） | wexpect 4.0.0 本機可 import；**不需** headless 外部 CLI/服務 | 已確認，非 GUI/PATH 假設陷阱 |

> **硬閘**：(a) 基線 3374 = improving_72 實測值，無 failed、無低於上輪 → 准進階段二。

---

## 3. 階段二：增量設計

### 3.1 <Architecture_Design_Review>（寫實質 Python 前自審）

1. **架構純潔性**：無 God-object。改動僅 `autoclaude/perception/pty_wrapper.py` 單檔——`_readline_wexpect` 讀到行時加一行**顯式** raw 寫入（鏡像既有 subprocess 路徑 `pty_wrapper.py` `_readline_subprocess` 的 `self._raw_logger.write(raw)`），並移除實證**從不觸發**的 `logfile_read` 掛載 + 其唯一消費者 `_RawLogAdapter` 死碼 class。`playbook_runner.py` Thin Facade 零改動。**淨減行數**（移除 13 行死碼、加 3 行擷取 + 6 行註解）。
2. **持久化相容**：**無新 PlaybookCheckpoint 欄位**、不動 DAL 三後端、不動 checkpoint → 零停機。純 perception 層 raw I/O 擷取訂正。
3. **安全防護網**：**不新增「從文件生成指令」或 shell 字串路徑**、不弱化 CONDITIONAL 三層。raw_logger 寫入為 bytes append（`errors="replace"`），無注入面。實則**移除**一個 callback 間接層、收斂為單一顯式路徑，降低面。
4. **對外 I/O 安全**：**不新增 `ToolInvocationPort` 外呼路徑**、無 Web/HTTP/訊息新能力 → allowlist/SSRF 攻防本輪 N/A。

### 3.2 介面 delta

| 構件 | delta | LOC 落點 |
|------|-------|---------|
| `perception/pty_wrapper.py` `_readline_wexpect` index==0（**DEF-73-001 修**） | 讀到行時 `if self._raw_logger and line: self._raw_logger.write(line.encode(...))` | 加 3 行 |
| `perception/pty_wrapper.py` `_readline_wexpect` index==2（**DEF-73-001 修，audit_73 SA-SD 發現**） | EOF 前未換行殘留 `child.before` 顯式擷取後再 return None（與 subprocess 對稱） | 加 4 行 |
| `perception/pty_wrapper.py` `_start_wexpect` + `_RawLogAdapter` | 移除 `self._child.logfile_read = _RawLogAdapter(...)` 掛載 + 移除死碼 class（唯一消費者已除） | 減 13 行（加 6 行根因註解） |
| `tests/test_perception.py` | `_FakeWexpectChild` helper（含 eof_tail）+ 3 回歸測試 | — |

- **importlinter**：無新跨層 import → **8 kept** 不變。
- **LOC**：`pty_wrapper.py` 由 177 → 約 173 行（淨減），perception <750；`check_loc_budget` violations=0（實測）。

### 3.3 設計關鍵：為何「不依賴 callback、改顯式寫入」是正解（零成本探針實證）

improving_72 真跑遞延的觀測：pty 後端 raw log **0 bytes**。原碼 raw 擷取**完全依賴** `self._child.logfile_read = _RawLogAdapter(...)`（`start()` 掛載 callback，期待 wexpect 內部於讀取時回呼）。

**動手前的零信任查證**（避免雙重記錄誤修）——本機 wexpect 4.0.0 可 import，跑探針：以 `wexpect.spawn("python", args=["-c", "print('LINE1');print('LINE2');print('DONE')"])` + 掛載自製 `logfile_read` callback + 用與 production 相同的 `expect([r".+\r?\n", TIMEOUT, EOF])` 迴圈讀取。結果：

```
READLINE_LINES: ['LINE1\r\nLINE2\r\nDONE\r\n']      # child.after 確實讀到全部行
LOGFILE_READ_CAPTURED_CHARS: 0                       # callback 完全不觸發
```

**結論**：(1) 缺陷為真，且**與 DEF-72-001 無關**——即使簡單正確指令、輸出確被讀到，`logfile_read` callback 在 wexpect 4.0.0 的 `expect()` 路徑**完全不觸發**（捕獲 0 字元）→ raw log 永遠 0 bytes。(2) 因 callback 從不觸發，改為顯式寫入**無雙重記錄之虞**。(3) subprocess 路徑早已是顯式寫入（`_readline_subprocess`），本修復使兩後端路徑**一致**＝顯式擷取讀到的行，移除不可靠的間接 callback 層。

---

## 4. 階段三：實作與雙重驗證

### 4.1 實作（純 AutoClaude A 軌整合層、無 Copy-on-Evolve）

- [autoclaude/perception/pty_wrapper.py](../../AutoClaude/autoclaude/perception/pty_wrapper.py)：`_readline_wexpect` index==0 顯式 raw 擷取 + index==2 EOF 殘留擷取（DEF-73-001）+ 移除 `logfile_read` 掛載與 `_RawLogAdapter` 死碼 + 根因註解。
- [tests/test_perception.py](../../AutoClaude/tests/test_perception.py)：`_FakeWexpectChild` helper（刻意不提供 callback 行為、含 eof_tail，複刻 wexpect 4.0.0 實況）+ 3 回歸測試。

### 4.2 受控突變實證（測試非空殼）

- `_readline_wexpect` index==0 顯式寫入改 `if False and ...`（暫移除）→ `test_wexpect_raw_log_captured_explicitly` + `test_wexpect_raw_log_accumulates_and_no_logfile_read_dependency` **雙雙轉紅**（`AssertionError: b'' == b'L1\r\nL2\r\n'`）。
- `_readline_wexpect` index==2 EOF 殘留擷取改 `if False and ...` → `test_wexpect_raw_log_captures_eof_residual_without_newline` **轉紅**。
- 兩處突變均 Edit 還原（**禁 git checkout**，本輪含 tracked 未 commit 改動 + untracked 新檔，遵 [[git-checkout-mutation-revert-hazard]]）→ 復綠（`tests/test_perception.py` 26 passed）。

### 4.3 測試守界意圖（Rule 9）

- `test_wexpect_raw_log_captured_explicitly`：若退回「只靠 logfile_read callback」必紅（fake child 永不呼叫 callback → raw 檔空）。
- `test_wexpect_raw_log_accumulates_and_no_logfile_read_dependency`：`assert not hasattr(fake_child, "logfile_read")` 固化「start() 不再掛載 callback」決策——任何人重新引入 `self._child.logfile_read = ...` 此測立即紅。

---

## 5. 階段四：零退化驗證矩陣（全項實測，結案）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥3374 / 0 failed | **3377 / 122 / 0**（floor 3374 + 3 新測） ✅ |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全 kept | **8 kept / 0 broken** ✅ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全過 | **violations=0**（pty_wrapper 淨減、tools/ 不受 tier） ✅ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK（FRESH）** ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 | **exit 0**（v0.01:1478 / v0.26:1665 / scripts:129；本輪零 SDD 變更） ✅ |
| 五軌 TLC | — | 僅 FSM 變更時 | **N/A — 條件未觸發**（git diff 鐵證零碰 `*.tla`/FSM；TLC 不在 pytest 全套、需 Java+tla2tools，本輪確實未跑） |
| DAL 等價 | `tests/equivalence/`（隨全套） | 三後端等價 | **既有 86 等價測試隨全套 3377 通過** ✅；本輪無新 DAL/checkpoint 改動 → 無新增針對性 round-trip 契約 |

---

## 6. RTM（需求追溯矩陣）

| 需求 | 來源 | 驗證 |
|------|------|------|
| R-73-1 wexpect 路徑 raw log 不再 0 bytes | `_readline_wexpect` 顯式 `raw_logger.write` | `test_wexpect_raw_log_captured_explicitly`（raw 檔含讀到行 bytes）+ 零成本探針實證 callback 不觸發（§3.3） |
| R-73-2 多行跨 readline 累積 | `_readline_wexpect` 逐行寫入 | `test_wexpect_raw_log_accumulates_and_no_logfile_read_dependency`（`b"L1\r\nL2\r\n"`） |
| R-73-3 不再依賴從不觸發的 callback | `_start_wexpect` 移除 `logfile_read` 掛載 + 移除 `_RawLogAdapter` | `assert not hasattr(fake_child, "logfile_read")` |
| R-73-4 raw_logger 為 None 時不崩 | `if self._raw_logger and line` 守衛 | 既有 wexpect spawn 測試（無 raw_log_path）+ 全套 0 failed |
| R-73-6 EOF 未換行殘留亦擷取（兩後端真正對稱） | `_readline_wexpect` index==2 擷取 `child.before` | `test_wexpect_raw_log_captures_eof_residual_without_newline`（`b"L1\r\nTAIL_NO_NL"`）；audit_73 SA-SD 發現、本輪閉環內修 |
| R-73-5 零退化 | 收斂矩陣 | 3377/0、8 kept、LOC 0、snapshot FRESH、SDD exit 0 |

---

## 7. 多專家 Zero-Trust 審查結論

見 [AutoSDD_ZeroTrust_Audit_73.md](../06_quality/AutoSDD_ZeroTrust_Audit_73.md)。三鏡**主樹**並行（本輪含 tracked 未 commit 改動〔pty_wrapper.py / test_perception.py〕+ untracked 新檔〔計畫/審計文件〕→ 依 DEF-24-001「審 untracked／未 commit 走主樹」鐵律禁 worktree；突變已全數還原、無並行突變鏡）。三鏡**全部 OVERALL PASS、P0=P1=0**：Architect（架構純潔、死碼乾淨、紅線守住、計畫書無虛報）、SA-SD（**獨立重跑探針**確認 callback 捕獲 0 字元、修復方向正確無雙重記錄；並**發現 EOF 未換行殘留不擷取**之 P3 不對稱限制）、QA（全套 3376→親跑核對、雙受控突變實證、工作樹乾淨交還）。**audit 閉環內修**：依 SA-SD 發現，`_readline_wexpect` index==2 補擷取 `child.before`（+1 回歸測 + 受控突變），使兩後端 raw 擷取真正對稱、全套升至 **3377**——發現即修不延後（遵 [[no-defer-unless-justified]]）。

---

## 8. 誠實級別標註

本輪＝**A 軌 pty 後端可觀測性缺陷修復輪（DEF-73-001），非成熟度推進**，`L_合體=min(A=L5,B=L5,C=L5)=L5` 維持。

- **首要成果**：①以零成本探針**實證** wexpect 4.0.0 `logfile_read` callback 於 `expect()` 不觸發（raw log 0 bytes 根因鐵證、且與 DEF-72-001 無關）；②改為顯式擷取讀到的行（鏡像 subprocess 路徑）+ 移除不可靠的 callback 間接層與死碼；③依 audit SA-SD 發現，閉環內補修 EOF 未換行殘留擷取，使兩後端 raw 擷取**真正對稱**；④補先前無覆蓋的 wexpect raw 擷取回歸測試 ×3（含「不依賴 callback」與「EOF 殘留」守界）。
- **本輪新框架缺陷**：DEF-73-001（整合層 AutoClaude 側，當場修；非 SDD 本體 → 免 Copy-on-Evolve、免五軌 TLC）。
- **教訓延續**：連三輪真跑/實證各揪一個 pty 路徑潛伏缺陷（DEF-71-001 接線崩潰、DEF-72-001 prompt 殘缺、DEF-73-001 raw log 觀測缺口），**共同根因＝pty wexpect 路徑長期無測試覆蓋**（wexpect Windows-only + 既有測試全走 `_WEXPECT_AVAILABLE=False` subprocess 分支）。本輪以 `_FakeWexpectChild` 建立 wexpect 路徑的可攜測試樁，逐步補上覆蓋——揭露此類缺陷的唯一途徑是真跑/實證 + 補測試。
- **遞延 improving_74 候選**：(a) 用更長/會觸發 compaction 的 playbook 跑 A/B 分出 token 峰值差異（improving_72 候選 b）；(b) SD_09 W1 觀察期 #1 source-sha 閘門（時間閘 ~06-29~07-01 成熟後）；(c) wexpect 路徑其餘分支（readline TIMEOUT 回 `""` 無內容、`_auto_respond` 授權自動回應 via wexpect `sendline`）的測試覆蓋補強——EOF 殘留分支本輪已補（見上）。

三件套：improving_73 / ZeroTrust_Audit_73 / Defect_Log（DEF-73-001 + recap）。
