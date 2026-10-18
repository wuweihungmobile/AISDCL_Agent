# SCG-4 PR Review 報告 — SddEnv（G-116-12：SDD 外部專案模式三件組產生器，DF-C）

**審查日期**: 2026-10-18　**審查者**: 整合輪 116 W3 QA（未參與規格撰寫與實作；規格作者＝W2 SA、實作者＝hooks-ON 的 headless Sonnet，三方不同）
**審查範圍**: `AISDLC_SDD/scripts/sdd_env.py`（新，133 行）、`AISDLC_SDD/scripts/tests/test_sdd_env.py`（新，276 行）；commit `343d583a`，加主控修補 `e73749bf`（stdio UTF-8 重設改走島內共用入口 `rfc_lifecycle_lint.force_utf8_stdio`、`tools/lib/skip_tag_policy.py` 樹下限 26→27）
**基準規格**: `docs/03_testing/contracts/TCS-SddEnv-20261018.md`（Stage-2 凍結摘要 `sha256:cc0988be…0d5a`，當回合重算相符）　**FSM 鍵**: `monorepo-sdd-env`
**證據總檔**: `docs/06_quality/AutoSDD_ZeroTrust_Audit_116.md`（§2.3 本審查全表、§3 閘門、§1.3 hooks-ON 證據）

### A. FRD 功能規格一致性

| AC-ID | 驗收標準（摘要） | 實作座標（`sdd_env.py`） | 測試座標（`scripts/tests/test_sdd_env.py`） | 結論 |
|-------|------------------|--------------------------|--------------------------------------------|------|
| AC-001-1 | 五變數、鍵序固定、狀態目錄查表、版本數值排序、預設根與預設 json、相對根轉絕對、非 ASCII 原樣 | `:44-53、96-102、104-111、121-127、56-58` | AT-001-1-1 `:38-56`；AT-001-1-2 `:59-81`（四個 sub 參數化，`v0.9` 與 `v0.10` 並存取 0.10）與 `:84-110`（相對根、尾端分隔符、`根目錄`） | Pass |
| AC-001-2 | powershell／bash 一變數一行、單引號依各 shell 規則跳脫、行序固定 | `:56-67` | AT-001-2-1 `:117-135`、AT-001-2-2 `:138-156`（根含 `o'brien`，還原後逐值相等） | Pass |
| AC-001-3 | slug 保留字、格式、長度；單字元與 30 字通過；rc 2、stdout 空 | `:33-41、91-94` | AT-001-3-1 `:159-176`（九個壞值＋31 字）；AT-001-3-2 `:178-191`（保留字三種大小寫、邊界三值） | Pass（P：CP2 見必修） |
| AC-001-4 | `--check`：存在 rc 0＋OK 行；不存在 rc 5；不建檔不建目錄 | `:113-119` | AT-001-4-1 `:194-211`；AT-001-4-2 `:214-235`（兩種缺法、目錄樹前後相同） | Pass |
| AC-001-5 | 版本不可解 rc 1、root 非目錄與用法錯誤 rc 2、成功不改 `os.environ`、`--help` rc 0 | `:84-89、96-108` | AT-001-5-1 `:238-276`（五情境） | Pass（R1 的 stdio 重設無斷言，CP1 見必修） |

### B. Contract 一致性
不適用（命令列腳本，無 HTTP 端點）；介面＝旗標與 rc 表（R1～R8）。真跑：`--check` 對三個 dogfood 鍵（`autoclaude-webhook`、`agentconsole-fsm-trail`、`monorepo-sdd-env`）皆 rc 0 並印 `OK <絕對路徑>`；對不存在的鍵 rc 5、stdout 空、stderr `state_not_found <絕對路徑>`。

### C. Business Invariants
不適用。R9 純度逐項核對：無 `subprocess`、無 `sys.platform`、無檔案 I/O、無時間戳、不改 `os.environ`（grep 零命中；`environ` 只出現在 docstring）。

### D. RTM 覆蓋率確認
AC 5／5、AT 9／9 皆有測試（`docs/06_quality/RTM-SddEnv.md`；測試檔共 22 個測試項，其中 AT-001-1-2 與 AT-001-3-1 為參數化）。

### E. 審查證據
| 項目 | 結果（當回合親跑） |
|------|------------------|
| `scripts/tests`（cwd `AISDLC_SDD`） | rc 0；421 通過、1 略過（Unix chmod 分支在 Windows 不可達，既有）、31 個子測試通過；整檔 22 項 |
| `ci-gate.ps1` | rc 0；「本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.30）」，逐軌計數 1478／2149／421 |
| ruff 兩檔（根視角） | All checks passed |
| 根層棘輪相關三模組 | `test_platform_utils_dedup`（43 項）、`test_platform_neutral_paths`、`test_subprocess_encoding_hygiene`（39 項）皆 OK |
| 突變檢驗（記憶體內改寫，repo 零改動） | 29 個突變：核心 26 個全數被殺；探針 3 個，1 個被殺、2 個存活（見必修 F-02） |
| NFR-001-2（`main()` < 2 秒） | 10 次含真實 git 解析：最大 0.049 秒 |
| 範圍守衛（NFR-001-7） | `git show --stat 343d583a` 恰兩個新檔；`e73749bf` 只動 `sdd_env.py` 的 stdio 一處與 `skip_tag_policy.py` 的樹下限（26→27，與 `int(34×0.8)＝27` 相符） |
| 真跑輸出位元組（Windows） | `--shell powershell`／`bash`／`json` 的 stdout 行尾都是 CRLF（bash 形 242 位元組含 5 個 `\r\n`、零個單獨 `\n`）；見必修 F-03 |

**已知偏離（F-04，P3，已由主控於 `e73749bf` 接受）**：TCS 的 R1 寫行內 `reconfigure`、R9 與 NFR-001-1 寫「只用標準庫與同目錄 `sdd_version`」，實作改以同目錄 `rfc_lifecycle_lint.force_utf8_stdio()` 承接（根層 `test_platform_utils_dedup` 對 `AISDLC_SDD/scripts` 的實作數是 shrink-only 棘輪，行內寫法會讓計數 10→11 轉紅）。行為等價（同函式 `reconfigure(encoding="utf-8", errors="replace")` 並以 try 包住），只是 TCS 文字未訂正；TCS 已凍結不改，記於 `RTM-SddEnv.md` 備註。

### 審查結論

| 項目 | 狀態 |
|------|------|
| FRD 功能規格 | Pass（0 項不符） |
| Contract 一致性 | N/A |
| Invariants 保護 | Pass |
| RTM 覆蓋率 | 100%（AC 5／5、AT 9／9） |
| 測試強度（突變） | **Fail**：2 個由 R 條文導出的探針存活（F-02，P2） |

**SCG-4 建議**: [需修正後再審查]

### 必修項目（Fail 項）

| 編號 | 問題 | 需修正內容 | 對應規格 |
|------|------|-----------|----------|
| F-02（P2） | oracle 無鑑別力：CP1 拿掉 `force_utf8_stdio()` 呼叫、CP2 把長度檢查排到格式檢查之前，皆不會讓任何 AT 轉紅 | 只動 `scripts/tests/test_sdd_env.py`：CP1——AT-001-5-1（`:238` 起）用 `monkeypatch.setattr(sdd_env, "force_utf8_stdio", spy)` 斷言一次 `main()` 恰呼叫一次；CP2——AT-001-3-1 的參數表加 `"A" * 31`（`:160`），既有 `"格式" in cap.err` 即可咬住「格式先於長度」 | R1、R7（檢查順序固定） |
| F-03（P3） | `--shell bash` 在 Windows 的輸出帶 CRLF：`eval "$(… --shell bash)"` 於 Git Bash 會把 `\r` 黏進值；違反 NFR-001-3「輸出形態由 --shell 決定而不是由平台決定」與根層鐵律三的行尾項 | `sdd_env.py:128` 改以 `sys.stdout.buffer.write(render(...).encode("utf-8"))`（或 `sys.stdout.reconfigure(newline="\n")`）；並補一支以子行程取原始位元組、斷言無 `\r` 的測試（capsys 看不到此差異） | R6、NFR-001-3 |
