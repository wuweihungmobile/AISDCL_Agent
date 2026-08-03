# AutoSDD improving_52 — C 軌：新 BOM hook（`check_ps1_encoding.py`）zero-trust 審查與加固

> **軌道定位**：軌道① **C 軌**（指揮官 AutoClaude 自身能力，柱①）。標的＝commit `097d196` 新增之 PostToolUse `.ps1` 自動補 UTF-8 BOM hook（`AutoClaude/tools/hooks/check_ps1_encoding.py` + 雙層 wiring + 單元測試）。
> **下一份**：`AutoSDD_improving_53.md`（按需）。
> **政策**：標的屬 AutoClaude（非 SDD 凍結本體）→ **就地修**（走 AutoClaude dev-build-test 循環，**非 Copy-on-Evolve**）。
> **日期**：2026-06-23。
> **掌舵者裁定**：本輪以 AskUserQuestion 確認推進 C 軌「驗證新 BOM hook」（SDD `.claude` B 軌已位元級零變更、四鏡零缺陷穩態，再全鏡＝零新發現的 token 浪費）。
> **結論先行**：🟡 **SA 鏡揪出真 P1（fail-soft 契約破口）+ 2 個 P2（UTF-16/Big5 補 BOM 損毀）已就地清償**；Architect/QA 鏡 OVERALL PASS。零退化（pytest 3241→3248，+7 新測試，0 failed）。

---

## 1. 本輪輸入（自上輪繼承）

- 上輪＝improving_51（第九輪 `.claude` 四鏡，零缺陷穩態）+ round-10 輕量回歸（commit `47018db`，掌舵者裁定接受）。
- 缺陷帳本 `.claude` scope：DEF-CLDREV-001~029 全 fixed@v0.19、030 routed（框架本體 RFC，scope 外）。
- 階段一 git 實證：`git log a2909d7..HEAD -- 'AISDLC_SDD/**/.claude/**'` **空** → SDD 框架 `.claude/` 自第九輪結案位元級零變更（穩態續守）；自 `a2909d7` 以來「真正動過」的全在 **C 軌**——SD_09 W0（schtasks 漏跑修復、`fix_nightly_catchup.ps1` ASCII 化、G0 改排 06-29）+ **新增 BOM hook（`097d196`，觸及根/AutoClaude `.claude/settings.json` + `check_ps1_encoding.py` + 測試）**。
- 本輪標的＝該新 BOM hook（自 `a2909d7` 以來唯一新增、尚未經 zero-trust 四鏡/攻防驗證之程式碼）。

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit，parent 親跑）

| 項目 | 命令 | 實測 |
|------|------|------|
| HEAD 真相 | `git log --oneline -6` | HEAD=`47018db`；工作樹乾淨 |
| **AutoClaude 全套 pytest（C 軌硬閘基線）** | `python -m pytest tests/ -q` | **3241 passed / 122 skipped / 0 failed**（≥ C 軌上輪 floor 3,060） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=**0** |
| Snapshot | `python tools/snapshot_sync.py --check` | fresh |
| 標的構件存在且被測試覆蓋 | Read hook + test + 雙 settings.json | hook 99 行存在；單元測試 **6 passed**；雙層 wiring（根絕對路徑+timeout 10 / 子層相對路徑）皆在位；CLAUDE.md hook 表 6 個對應 |
| invocation 形態確認（紀律 (f)） | — | hook＝PostToolUse(Edit\|Write) subprocess（`python <script>`），非 GUI/PATH CLI；headless 可自動化驗證 |

**硬閘**：基線無 failed、未低於上輪 passed（3241 ≥ 3,060）→ 通過，進入階段二。

## 3. 階段二/三：三鏡 zero-trust 審查 + 就地修復

標的全部已 commit 於 HEAD、tracked 乾淨檔 → 依 DEF-24-001「審 tracked 乾淨檔→主樹派發」，派 **Architect / SA / QA 三鏡**主樹並行獨立 zero-trust 審查。

| 鏡 | 裁定 | 關鍵 finding |
|----|------|------|
| **Architect** | OVERALL PASS | auto-fix（永遠 exit 0）vs `check_sh_eol.py` exit 2 阻斷＝by-design（Write 結構上無法產 BOM，只能事後補；.sh 的 LF 是 Write 可控故可阻斷）；雙層 wiring 必要（root 不遞迴載子目錄 hook）；計數誠實（hook 表 6 個一一對應）；fail-soft/嵌套/無 God-object。findings：P3 UTF-16 雙 BOM 邊界、P3 子層缺 timeout |
| **SA**（4 攻防腳本實跑） | **OVERALL FAIL → 修復後 PASS** | **P1 FIND-1**：錯型別 payload（`file_path` 為 list/int、`tool_input` 非 dict、頂層非 dict）→ 拋 `TypeError`/`AttributeError` rc=1，**違反 docstring「永遠 exit 0、絕不阻斷」契約 + Nightly 紀律 #4**（subprocess 實證 7 類 payload rc=1）；P2 FIND-2 UTF-16(LE/BE) 前置 UTF-8 BOM 損毀；P2 FIND-3 Big5/cp950 補 BOM 製造「宣告 UTF-8 內容卻 Big5」矛盾檔；P3 FIND-4 stderr 中文於 ascii-strict console 直接 import（非 subprocess）UnicodeEncodeError |
| **QA**（親跑 6→驗收覆蓋） | OVERALL PASS | 6 測試非空殼、精確斷言（`== UTF8_BOM + body`）、路徑真實（`parents[3]` 正確）、帳本誠實。覆蓋缺口：P2 G1（`.psm1/.psd1` 未測，1/3 後綴）、P2 G6（`abs_path is None` 未經 CLI 驗證）、可選 G9（壞 JSON） |

### 就地修復（dev-build-test 循環，每改即測）

1. **P1（DEF-52-001）fail-soft 型別守門**：`read_hook_payload()` 回傳前 `isinstance(obj, dict)` 守門（頂層非 dict→`{}`）；`main()` 加 `isinstance(tool_input, dict)` / `isinstance(file_path, str) and file_path` 雙守門；`resolve_path` except 補 `TypeError`。**使 hook 對任意型別 payload 真正 fail-soft（永遠 exit 0），兌現自身契約**。
2. **P2（DEF-52-002）UTF-8 合法性閘**（一閘同時消解 FIND-2 + FIND-3）：補 BOM 前 `raw.decode("utf-8")`，`UnicodeDecodeError` 即 no-op——**僅對「合法 UTF-8 無 BOM」補 BOM**；UTF-16(FF FE/FE FF BOM 開頭)、Big5/cp950 皆非合法 UTF-8 → no-op，杜絕雙 BOM/矛盾檔損毀。docstring 同步精確化此分支。
3. **P3（DEF-52-005）一致性**：子層 `AutoClaude/.claude/settings.json` 的 BOM hook 補 `"timeout": 10` 與根層對齊。
4. **測試補強**（DEF-52-003 G1 / DEF-52-004 G6 + SA 攻擊向量編碼）：新增 7 測試——`.psm1/.psd1` 補 BOM、UTF-16 LE no-op、Big5 no-op、錯型別 file_path（list/int）fail-soft、非 dict tool_input/頂層 fail-soft、空 file_path no-op、壞 JSON fail-open。**`test_cli_wrong_type_file_path_fail_soft` 在舊碼必紅（SA 實證 rc=1）＝Rule 9 真能失敗**。
5. **P3 FIND-4（DEF-52-006）wontfix+理由**：生產 wiring 必為 subprocess（`__main__`→`_init_utf8_streams()` 先行）→ 風險為零；改 module-level stream 替換會干擾 pytest capture，「不做有優點」（[[no-defer-unless-justified]] 兩類正當延後之一）。

### <Architecture_Design_Review>

1. **架構純潔性**：hook 屬 `tools/hooks/`（非 `autoclaude/` 套件），不受 importlinter 8 contract 約束（lint 8 kept 不變）；單一純函式 + thin CLI，無 God-object、未動微核心。✅
2. **持久化相容**：hook 無狀態、不碰 PlaybookCheckpoint/DAL。✅
3. **安全防護網**：本輪修復**強化**對外輸入（hook stdin payload）的型別消毒——錯型別 payload 由「墜入例外網 rc=1」改為「fail-soft no-op exit 0」，縱深符合 fail-soft 契約；UTF-8 合法性閘防止對非 UTF-8 檔誤寫。✅
4. **對外 I/O 安全**：本輪未新增 `ToolInvocationPort` 外呼路徑；hook 僅本地檔案讀寫，無網路 I/O。✅

## 4. 階段四：CI 平價收斂（零退化驗證矩陣，parent 親跑）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ floor 3241 / 0 failed | ✅ **3248 passed / 122 skipped / 0 failed**（基線 3241 + 7 新測試） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | ✅ **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | ✅ violations=**0** |
| Snapshot | `python tools/snapshot_sync.py --check` | fresh | ✅ fresh |
| settings.json JSON 有效性 | `json.load` 雙檔 | valid | ✅ 雙檔 OK |
| hook 單元測試 | `pytest tests/tools/hooks/test_check_ps1_encoding.py -v` | 全綠 | ✅ **13 passed**（6→13） |
| 端到端取證 | 生產命令形態 subprocess | P1 rc=0／正常補 BOM／UTF-16 no-op | ✅ 三筆皆符 |
| 五軌 TLC | （僅 FSM/`*.tla` 變更時） | — | N/A（無 FSM/`*.tla` 變更，不觸發） |

本輪改 **1 hook（`check_ps1_encoding.py`：型別守門 + UTF-8 合法性閘 + docstring）+ 1 測試檔（+7）+ 1 子層 settings.json（timeout）+ 3 件審計文件**；v0.01 凍結基線零觸碰（標的全在 AutoClaude，非 SDD 本體）。

## 5. RTM（本輪需求追溯）

| 需求 | 驗收標準 | 證據 | 狀態 |
|------|---------|------|------|
| R-52-1 全面驗證新 BOM hook 符合架構/安全 | hook + 雙 wiring + 測試逐項親讀，三鏡 zero-trust | §2 親讀 + §3 三鏡 | ✅ |
| R-52-2 派 Architect/SA/QA 專家檢視 | 三鏡主樹並行 zero-trust | §3 三鏡裁定 | ✅ |
| R-52-3 若不符則修復（不留 partial） | SA P1 + 2×P2 + 一致性 P3 全清，新測試固定 | §3 就地修復 5 項 | ✅ |
| R-52-4 零退化 | pytest ≥ floor 3241 / 0 failed、lint/LOC/snapshot 綠 | §4 矩陣全綠（3248/0） | ✅ |

## 6. 結論

C 軌新 BOM hook（`097d196`）經三鏡 zero-trust 審查揪出 **1 真 P1（fail-soft 契約破口）+ 2 真 P2（UTF-16/Big5 補 BOM 損毀）**，皆於本輪**就地清償**（型別守門兌現「永遠 exit 0」契約；UTF-8 合法性閘一閘消解兩個 P2 編碼損毀），並補 7 個測試（含 SA 攻擊向量編碼＝舊碼必紅）固定行為。Architect/QA 鏡 OVERALL PASS。**零退化**：pytest 3241→**3248**（+7 新測試，0 failed）、lint-imports 8 kept、LOC=0、snapshot fresh。

**回流**：本輪缺陷全屬 AutoClaude（C 軌）就地修，無 SDD 框架本體回流；DEF-52-006 wontfix+理由（生產 subprocess 路徑零風險）。
