# Test Contract Specification — SddEnv（G-116-12：SDD 外部專案模式三件組產生器）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統的單一 Feature（增量條款）；FRD-lite 與 TCS 同檔
**存放位置**: `docs/03_testing/contracts/TCS-SddEnv-20261018.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根）
**spec-format-version**: 1.0
**scenario**: greenfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-001 |
| **Feature 名稱** | SddEnv：依 --sub 與 --slug 機械產生 SDD 外部專案模式三件組與遙測旗標（AISDLC_SDD/scripts/sdd_env.py） |
| **User Story** | US-001 |
| **建立日期** | 2026-10-18 |
| **QA 負責人** | 整合輪 116 W3 QA（獨立審查者；規格作者＝W2 SA、實作者＝hooks-ON 的 headless Sonnet，三方不同） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統（monorepo 根層；上位文件已於 Stage-1 採納凍結，採納程序見 `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md` §8.4）的單一 Feature。
> 未列入追溯表視為未滿足；引用不得指向未凍結文件（必須列在 FSM 狀態檔 `frozen_stages[*].spec_docs`）。

### FRD-lite

**現況與變更（Before／After；greenfield 新腳本）**

- Before：SOP（`SDD_AUTOCLAUDE_BRIDGE.md` §8.1）要求 hooks-ON 視窗設定三件組（`SDD_ACTIVE_VERSION`、`SDD_STATE_DIR`、`SDD_PROJECT`）加兩個遙測旗標；值有慣例，卻沒有機械產生器，只能手抄文件裡的啟動區塊。三件組缺一不可：缺 `SDD_PROJECT` 退回目錄名、缺 `SDD_STATE_DIR` 狀態寫進框架預設目錄且缺檔即建（G-116-12；規劃檔 `docs/04_planning/AutoSDD_improving_116.md` §3，非凍結上位文件，僅供追溯）。
- After：新增腳本 `AISDLC_SDD/scripts/sdd_env.py`，依 `--sub` 與 `--slug` 一次印出五個變數（PowerShell、bash、JSON 三種形態）；`--check` 驗證狀態檔存在。腳本不寫 `$PROFILE`、不啟動 `claude`、不建任何狀態檔。

**F-001 `sdd_env.py`**（新腳本；程式住 `AISDLC_SDD/scripts/`、測試住 `AISDLC_SDD/scripts/tests/`）

```text
python AISDLC_SDD/scripts/sdd_env.py --sub {autoclaude,agentconsole,monorepo,sdd} --slug <slug>
                                     [--shell {powershell,bash,json}] [--root <monorepo 根>] [--check]
```

**〈F-001 行為規則〉**（R1～R10；引數檢查順序：argparse → R7 slug → R4 root → R5 版本）

- **R1 介面與退出碼**：`main(argv: list[str] | None = None) -> int` 回傳 rc，不呼叫 `sys.exit`；argparse 的 `SystemExit` 在 `main` 內攔截轉成回傳值（用法錯誤 rc 2、`--help` rc 0）；檔尾 `if __name__ == "__main__": sys.exit(main())`；進入 `main` 時把 stdout 與 stderr 重設為 UTF-8（`reconfigure(encoding="utf-8", errors="replace")`，以 try 包住，非 TextIO 時略過，比照 `sdd_version.py`）。rc 表：0 成功；1 版本不可解；2 引數不合法（用法錯誤、slug 驗證失敗、root 不是目錄）；5 `--check` 的狀態檔不存在（與 FSM CLI 的 `--must-exist` 同碼）。
- **R2 輸出變數**（固定順序）：`SDD_ACTIVE_VERSION`、`SDD_PROJECT`、`SDD_STATE_DIR`、`SDD_ENABLE_RULE_FIRE_TELEMETRY`、`SDD_ENABLE_RULE_CATCH_TELEMETRY`。`SDD_PROJECT`＝`<sub>-<slug>`；兩個遙測旗標的值恆為 `0`；`SDD_STATE_DIR` 見 R3；`SDD_ACTIVE_VERSION` 見 R5。
- **R3 狀態目錄查表**（`<root>` 為 R4 的絕對根）：`autoclaude` → `<root>/AutoClaude/build/reports/fsm`；`agentconsole` → `<root>/AgentConsole/build/reports/fsm`；`monorepo` → `<root>/build/reports/fsm`；`sdd` → `<root>/AISDLC_SDD/AISDLC_SDD_v<版本>/build/reports/sdd-dogfood`。一律以 `os.path.join` 組成（分隔符隨平台），結果是絕對路徑；不解析 symlink，也不檢查子專案目錄是否存在。
- **R4 `--root`**：預設 `str(Path(__file__).resolve().parents[2])`（腳本所在 repo 根）；有給時取 `os.path.abspath(...)`（相對路徑，以及尾端帶路徑分隔符的值，都先轉成絕對路徑，所以 `SDD_STATE_DIR` 恆為絕對路徑）；須是存在的目錄，否則 rc 2，stderr 一行理由，含 `root` 字樣。
- **R5 版本**：先 `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` 再 `import sdd_version  # noqa: E402`（行尾加 noqa：這行 import 排在 `sys.path.insert` 之後，而根層 ruff 的出廠預設規則含 E402；模組屬性名稱固定為 `sdd_version`，供測試以 `monkeypatch.setattr(sdd_env.sdd_version, ...)` 隔離 git）；`SDD_ACTIVE_VERSION`＝`sdd_version.latest_version_name(Path(root) / "AISDLC_SDD")` 的回傳值去掉前綴 `AISDLC_SDD_v`（例 `0.30`）；不得自行實作 LATEST 解析。回傳 `None`（找不到任何版本目錄）→ rc 1，stdout 空，stderr 一行理由，含 `AISDLC_SDD_v` 字樣。
- **R6 `--shell`**：預設 `json`（平台中立；PowerShell 與 bash 形態須顯式指定）。`powershell`：每個變數一行 `$env:<NAME> = '<VALUE>'`，VALUE 內的單引號雙寫（`'` 變 `''`）；`bash`：每個變數一行 `export <NAME>='<VALUE>'`，VALUE 內的單引號寫成 `'\''`；`json`：單一 JSON 物件（`json.dumps(..., ensure_ascii=False)`），鍵序同 R2，值全是字串；非 ASCII 字元（例如 root 含中文目錄名）原樣輸出，不轉成 `\uXXXX`。成功時 stdout 只有環境區塊（逐行以換行結尾）。
- **R7 slug 驗證**（失敗一律 rc 2、stdout 空、stderr 一行理由；檢查順序固定）：先保留字——`slug.lower() == "aisdlc_sdd"`，理由含 `保留字`；再格式——`re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug)` 不成立，理由含 `格式`；再長度——超過 30 個字元，理由含 `30`。單一字元與恰 30 個字元的合規 slug 必須通過。
- **R8 `--check`**：不印環境區塊；狀態檔路徑＝`os.path.join(<SDD_STATE_DIR>, "FSM-STATE-<SDD_PROJECT>.yaml")`；`os.path.isfile` 為真 → rc 0，stdout 一行 `OK <絕對路徑>`；否則（含狀態目錄不存在）→ rc 5，stdout 空，stderr 一行 `state_not_found <絕對路徑>`。不論結果都不建立任何檔案或目錄，也不讀檔案內容。
- **R9 純度**：只用標準庫與同目錄的 `sdd_version`；`open()` 一律帶 `encoding="utf-8"`（本腳本預期零檔案讀寫）；不持久化時間戳；不修改 `os.environ`；不寫 `$PROFILE` 與任何使用者設定檔；不啟動 `claude`；不建狀態檔；不自行呼叫 `subprocess`。
- **R10 輸出分流**：stdout 只放環境區塊或 `--check` 的 `OK` 行，唯一例外是 `--help` 的 usage 文字（argparse 慣例走 stdout，rc 0）；任何診斷（含 `sdd_version` 的 stderr 警告）一律走 stderr；任何失敗 rc（非 0）時 stdout 為空。

| US ID | User Story | AC ID | AC（Given／When／Then） |
|-------|------------|-------|-----------------------|
| US-001 | 作為要開 hooks-ON SDD 視窗的掌舵者或主控，我要一支腳本依子專案與功能代號機械產生三件組與遙測旗標，以便不手抄、不漏設、不把狀態寫進框架預設目錄（G-116-12） | AC-001-1 | Given 一個含 AISDLC_SDD 版本目錄的 monorepo 根 When 以 --sub 與 --slug 呼叫 Then 輸出五個變數：SDD_PROJECT 為 sub 加連字號加 slug、SDD_STATE_DIR 為依 sub 查表的絕對路徑、SDD_ACTIVE_VERSION 為 LATEST 去前綴（數值排序）、兩個遙測旗標為 0；--root 預設為腳本所在 repo 根、--shell 預設為 json；相對的 --root 先轉成絕對路徑（SDD_STATE_DIR 恆為絕對路徑），非 ASCII 的路徑在 json 形態原樣輸出 |
| US-001 | 同上 | AC-001-2 | Given --shell 為 powershell 或 bash When 輸出 Then 每個變數一行（PowerShell 為 $env:NAME = 單引號包住的值，bash 為 export NAME= 單引號包住的值），值中的單引號依各 shell 規則跳脫，行序固定 |
| US-001 | 同上 | AC-001-3 | Given slug 不合規則（保留字、格式、長度） When 呼叫 Then rc 為 2、stdout 為空、stderr 一行理由（保留字、格式或 30）；合規的邊界值（單字元、30 字）通過 |
| US-001 | 同上 | AC-001-4 | Given 加上 --check When 狀態檔存在 Then rc 0 並印 OK 行；不存在（含狀態目錄不存在）rc 5 並印 state_not_found；任何情況都不建檔、不建目錄 |
| US-001 | 同上 | AC-001-5 | Given 版本目錄不存在、--root 不是目錄、或引數用法錯誤 When 呼叫 Then 分別 rc 1、2、2 且 stdout 為空；成功呼叫不修改 os.environ、不建任何檔案或目錄；--help 例外：rc 0、usage 文字走 stdout |

> 編譯相容提醒：FRD-lite 表的第一欄用 US ID，不把 AC ID 放第一欄（`sdd_compile` 會把「第一欄形如 AC-…」的表格列當成 AC→AT 映射列掃描）。

**INVEST 自檢（US-001）**：獨立（只依賴同目錄 sdd_version）、可協商（輸出順序、預設 shell 與錯誤文字由本檔定義）、有價值（關閉 G-116-12 的人工手抄缺口，從機制上消除「三件組缺一」）、可估計（1 支腳本加 1 個測試檔）、小（腳本約 120 行）、可測（9 個 AT 皆為 Unit，tmp 目錄隔離）。

**非功能需求（量化）**

| NFR ID | 內容 | 驗證方式 |
|--------|------|----------|
| NFR-001-1 | 純度：只用標準庫與同目錄 sdd_version；open 一律帶 encoding="utf-8"；不持久化時間戳；不自行呼叫 subprocess | SCG-4 人工審查（import 與程式碼檢視） |
| NFR-001-2 | 單次 main()（含 LATEST 解析）< 2 秒（本機量測 10 次取最大值；git 子行程占大宗） | SCG-4 審查時以 timeit 量測，不列 AT |
| NFR-001-3 | 跨平台（根層鐵律三）：路徑一律 os.path.join 或 Path，不寫死分隔符；不用單平台 API；輸出形態由 --shell 決定而不是由平台決定，程式碼不使用 sys.platform 分支 | SCG-4 審查；根層 tools/tests 相關鎖 |
| NFR-001-4 | 根層護欄相容：測試檔不新增 skip、skipif、xfail，不用 sys.platform 分支；所有 open、read_text、write_text 帶 encoding="utf-8"；測試字面值不含磁碟機代號開頭的路徑；不碰根層 tools/tests（根層棘輪） | SCG-4：根層 tools/tests 相關鎖與 git diff |
| NFR-001-5 | 靜態檢查：ruff check 對兩個新檔（AISDLC_SDD/scripts/sdd_env.py、AISDLC_SDD/scripts/tests/test_sdd_env.py）0 錯；根層 ruff.toml 不選規則，等於 ruff 出廠預設（E4、E7、E9、F） | SCG-4 實跑 |
| NFR-001-6 | 測試 hermetic：不讀 SDD_ 開頭的環境變數、不碰真實 FSM-STATE-*.yaml、不啟動 claude；一律用 tmp_path 隔離；AT 以 python -m pytest scripts/tests/test_sdd_env.py -q 執行（cwd 為 AISDLC_SDD） | SCG-4 實跑 |
| NFR-001-7 | 零退化與範圍守衛：AISDLC_SDD/scripts/tests 既有測試續綠（python -m pytest scripts/tests -q，cwd 為 AISDLC_SDD；通過數以實跑為準）；git diff --name-only 只准出現兩個新檔（AISDLC_SDD/scripts/sdd_env.py、AISDLC_SDD/scripts/tests/test_sdd_env.py）；只准新增 2 個 `.py`（腳本與它的測試檔），不得多建任何其他 `.py` 或 `test_*.py`。理由：新增測試檔使根層檔案數鎖與基線需重釘——2026-10-18 實測 `AISDLC_SDD/scripts/tests` 遞迴 `test_*.py` 共 33 支，`tools/lib/skip_tag_policy.py` 的 `_TREE_FILE_FLOORS` 對該樹的下限是 26；新增 `test_sdd_env.py` 後為 34 支，`int(34×0.8)＝27` 大於 26，根層 `tree_floor_problems()` 的「下限已過期」向會變紅，須重釘為 27；另有 ci-gate.sh 的 MIN_TESTS_SHARED 與 ONBOARDING §7 的基線；這些都由主控收尾處理，實作者不碰（實作者每多建一個 `test_*.py`，數字就再升一次） | 主控以 git diff 與實跑核對 |

**追溯矩陣**：F-001 ← 缺口 G-116-12 與裁決 D-116-04（規劃檔 `docs/04_planning/AutoSDD_improving_116.md` §3、§6，非凍結上位文件，僅供追溯）；整合輪 116 裁決 D-116-15（DF-C）；SOP 來源 `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md` §8.1（三件組標準值表）；US-001 → AC-001-1～AC-001-5 → AT-001-1-1～AT-001-5-1（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；清單取自 `/sdd-gate` 的 SCG-0～3 檢查表；「已凍結上位文件」均相對 `spec-frozen --root`＝monorepo 根）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定（Status: Approved） | 不適用（根層無獨立 PRD）；需求基線＝軌道①範本驅動的整合輪；功能來源 G-116-12、D-116-04（規劃檔，僅供追溯） | docs/04_planning/AutoSDD_Iteration_Prompt_Template.md | sha256:02f6e22631be375d045da7ac4700abcb3d6c23fd33169522be90f4eb7944ae95 |
| SCG-0／FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯） | F-001（本檔 FRD-lite）；最近依據 ADOPTED CLAUDE.md〈AISDLC_SDD — 快查〉與〈現查指令速查表〉 | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-0／NFR 已量化定義 | NFR-001-1～7（本檔）；最近依據 ADOPTED CLAUDE.md 鐵律三（跨平台自問表）與鐵律一、鐵律二（PowerShell 單一載具） | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-0／User Story 已完成 INVEST 檢查 | US-001（本檔 INVEST 自檢） | docs/04_planning/AutoSDD_Iteration_Prompt_Template.md | sha256:02f6e22631be375d045da7ac4700abcb3d6c23fd33169522be90f4eb7944ae95 |
| SCG-0／利害關係人已確認簽核 | 掌舵者授權代決（整合輪 116 D-116-04、D-116-15；決策出處為規劃檔，僅作 ID 追溯，非上位文件） | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-0／RTM 初版已建立 | 本增量自帶：本檔 §1 與 §6（AC→AT 映射） | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD 完成並通過 Review（Status: Approved） | 不適用（腳本級增量，無 SRD）；最近依據 ADOPTED CLAUDE.md〈AISDLC_SDD — 快查〉 | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-1／API Spec 草稿完成（所有端點清單） | 不適用（無 HTTP 端點）；命令列介面即契約：旗標與 rc 表見本檔 FRD-lite R1 至 R8 | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-1／資料模型設計完成 | 無持久化；輸出五個變數（FRD-lite R2） | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-1／NFR 設計對應完成（架構選型對應 NFR 指標） | NFR-001-3 對應 ADOPTED CLAUDE.md 鐵律三（路徑分隔符、編碼）；NFR-001-1 對應 R9 | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-1／整合架構說明完整（第三方服務已識別） | 無第三方服務；唯一依賴同目錄 scripts/sdd_version.py（LATEST 解析 SSOT；CLAUDE.md〈現查指令速查表〉的「SDD LATEST 版本」列） | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-2／C4 Context 圖完成（系統邊界清晰） | 不適用（腳本級增量，不新增系統邊界）；最近依據 ADOPTED CLAUDE.md〈雙專案 monorepo〉 | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-2／C4 Container 圖完成（主要組件識別） | 不適用（不新增容器）；落點 AISDLC_SDD/scripts/（版本目錄之上的共用 infra，不隨 Copy-on-Evolve） | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-2／所有架構決策有對應 ADR（Status: Accepted） | 本增量無新架構決策；ADR 不新開（整合輪 116 D-116-16），文件瘦身紀律見範本〈產品輪的固定成本瘦身〉 | docs/04_planning/AutoSDD_Iteration_Prompt_Template.md | sha256:02f6e22631be375d045da7ac4700abcb3d6c23fd33169522be90f4eb7944ae95 |
| SCG-2／Trust Boundary Map 完成（Security 情境） | 不適用（scenario 為 greenfield，非 security）；腳本無網路、無子行程、無寫檔，不跨信任邊界；最近依據 ADOPTED CLAUDE.md〈機械守衛總表〉（本腳本不碰守衛面） | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-2／Before／After 架構對比（Brownfield 情境） | 不適用（greenfield）；仍記 Before＝手抄 SOP 的啟動區塊、After＝腳本（本檔 FRD-lite〈現況與變更〉） | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-3／OpenAPI 3.1 規格完整（所有端點含完整 Schema） | 不適用（無 HTTP API）；介面為命令列 | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-3／Request／Response Schema 定義完整 | 輸出形態 powershell、bash、json 三種（FRD-lite R6），五個變數與順序（R2） | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-3／錯誤碼定義（400／401／403／404／500） | rc 表 0、1、2、5（FRD-lite R1 與 R4 至 R8）；5 與 FSM CLI 的 --must-exist 同碼 | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-3／Consumer Contract 完成（整合情境） | 消費者＝人（把輸出貼進 hooks-ON 視窗）與 SDD_AUTOCLAUDE_BRIDGE §8.1 的啟動區塊（本增量不改該文件） | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |
| SCG-3／API ID 與 RTM 已對應 | 無 API ID；AT 到 RTM 見本檔 §1 與 §6 | docs/04_planning/AutoSDD_Iteration_Prompt_Template.md | sha256:02f6e22631be375d045da7ac4700abcb3d6c23fd33169522be90f4eb7944ae95 |
| SCG-3／Contract 已 Review 通過 | 由未參與規格與實作的 QA 於 SCG-4 獨立審查（W3）；裁決 D-116-15 | CLAUDE.md | sha256:9adacf1d47a1a1f86742f5a7d3e7d8d4afb9f0ca03cee8b473b86d84ff0262c1 |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值（`fsm_runtime show` 可查）。本表各值取自 Stage-1 凍結（2026-10-18T10:35:21+08:00，approver 為掌舵者代理（主控），reason 為「baseline adoption；SCG 未重跑」）後 `show` 的逐字輸出，並已用檔案現況獨立重算複驗一致；Stage-1 的兩份上位文件與 HEAD（81faa59a）逐字相同（棕地基線採納）。

---

## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-001-1 | 輸出五個變數（鍵、狀態目錄表、版本去前綴、旗標為 0） | AT-001-1-1 | 預設根與預設 json：monorepo 一組值逐項核對 | ✅ | Unit | □ |
| AC-001-1 | 輸出五個變數（鍵、狀態目錄表、版本去前綴、旗標為 0） | AT-001-1-2 | 明確根與四個 sub 的狀態目錄查表，版本數值排序；相對根與非 ASCII 根 | ✅ | Unit | □ |
| AC-001-2 | 兩種 shell 形態與跳脫 | AT-001-2-1 | powershell 五行、單引號雙寫 | ✅ | Unit | □ |
| AC-001-2 | 兩種 shell 形態與跳脫 | AT-001-2-2 | bash 五行、單引號跳脫序列 | ✅ | Unit | □ |
| AC-001-3 | slug 驗證 | AT-001-3-1 | 格式與長度違規一律 rc 2 且 stdout 空 | ✅ | Unit | □ |
| AC-001-3 | slug 驗證 | AT-001-3-2 | 保留字 rc 2；單字元與 30 字邊界通過 | ✅ | Unit | □ |
| AC-001-4 | --check 狀態檔存在性 | AT-001-4-1 | 狀態檔存在：rc 0 與 OK 行，不建檔 | ✅ | Unit | □ |
| AC-001-4 | --check 狀態檔存在性 | AT-001-4-2 | 狀態檔或目錄不存在：rc 5，不建檔不建目錄 | ✅ | Unit | □ |
| AC-001-5 | 失敗邊界與零副作用 | AT-001-5-1 | 版本不可解 rc 1、root 非目錄與用法錯誤 rc 2、--help rc 0、成功呼叫不改環境不建檔 | ✅ | Unit | □ |

**覆蓋率統計**:
- 總 AC 數: 5
- 已映射 AT 數: 9
- 映射覆蓋率: 100% （目標: 100%）

---

## 2. 可自動化 AT 格式規範

> **驗收字樣**：每個 AT 的最後一個 `And` 行帶一個以雙引號包住的驗收字樣（例 `[AT_OK_001_1_1]`），本節 Then、And 行**只有驗收字樣一組引號**，其餘程式碼字面值一律用反引號，單引號字元則用文字描述（與同輪 DF-A 同型，編譯時引擎會把第一個引號字面值轉成最後回覆的 regex）。本 Feature 走 SDD session-only 路徑：實作者在 session 內自跑 `python -m pytest scripts/tests/test_sdd_env.py -k "<AT 底線形>" -q`（cwd 為 `AISDLC_SDD`），**把輸出逐字貼進證據**（沒貼＝未驗證），並在最終回覆逐 AT 列出驗收字樣。

```gherkin
# AT-001-1-1
# 對應 AC: AC-001-1 輸出五個變數（預設根與預設 json）
# 測試類型: Unit
# 自動化工具: pytest + capsys

Feature: sdd_env 輸出三件組標準值

Scenario: 不帶 --root 與 --shell 時，以腳本所在 repo 根為根、輸出 json，五個變數逐項正確
  Given 在 monorepo 根下，新腳本 `AISDLC_SDD/scripts/sdd_env.py` 提供 `main(argv: list[str] | None = None) -> int`（只用標準庫與同目錄的 `sdd_version`；完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R10，唯讀）
  And 測試放在 `AISDLC_SDD/scripts/tests/test_sdd_env.py`（新檔；以 `from scripts import sdd_env  # isort: skip` 與 `from scripts import sdd_version  # isort: skip` 匯入，cwd 為 `AISDLC_SDD`，比照同目錄既有測試）；本 AT 的測試函式名稱須含 `AT_001_1_1`，例如 `test_AT_001_1_1_default_root_and_json_shell`
  When 用 pytest 的 `capsys`，呼叫 `sdd_env.main(["--sub", "monorepo", "--slug", "demo-feature"])`（不帶 `--root`、不帶 `--shell`），再呼叫一次 `sdd_env.main(["--sub", "monorepo", "--slug", "demo-feature", "--shell", "json"])`
  Then 兩次的回傳值都是 `0`，且兩次的 stdout 逐字相同
  And stdout 是單一 JSON 物件（`json.loads` 可解析），鍵依序恰為 `SDD_ACTIVE_VERSION`、`SDD_PROJECT`、`SDD_STATE_DIR`、`SDD_ENABLE_RULE_FIRE_TELEMETRY`、`SDD_ENABLE_RULE_CATCH_TELEMETRY`，值全是字串
  And `SDD_PROJECT` 為 `monorepo-demo-feature`，兩個遙測旗標的值都是 `0`
  And 令 `root` 為 `str(Path(sdd_env.__file__).resolve().parents[2])`：`SDD_STATE_DIR` 等於以 `os.path.join` 把 `root` 與 `build`、`reports`、`fsm` 三段依序串起來的路徑，且 `os.path.isabs` 為真
  And `SDD_ACTIVE_VERSION` 等於 `sdd_version.latest_version_name` 對 `root` 之下 `AISDLC_SDD` 目錄的回傳值去掉前綴 `AISDLC_SDD_v` 後的字串，且符合正規式 `^\d+\.\d+$`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_1_1]"
```

```gherkin
# AT-001-1-2
# 對應 AC: AC-001-1 四個 sub 的狀態目錄查表與版本數值排序
# 測試類型: Unit
# 自動化工具: pytest + capsys + tmp_path + monkeypatch

Feature: sdd_env 的狀態目錄查表

Scenario: 明確給定 --root 時，四個 sub 各得到對應的狀態目錄，版本取數值最大者
  Given 在 monorepo 根下，`AISDLC_SDD/scripts/sdd_env.py` 已提供 `main(argv: list[str] | None = None) -> int`（完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R10，唯讀；本 AT 只要求 R2、R3、R4（含相對路徑轉絕對）、R5、R6 的 `ensure_ascii=False` 成立）
  And 測試追加到 `AISDLC_SDD/scripts/tests/test_sdd_env.py`，本 AT 的測試函式名稱須含 `AT_001_1_2`，例如 `test_AT_001_1_2_state_dir_table_for_each_sub`；以 `pytest.mark.parametrize` 涵蓋四個 `--sub`；以 `tmp_path / "fake_root"` 造假的 monorepo 根（假根是 `tmp_path` 的子目錄，讓它有個父目錄可供相對路徑測試），其下有 `AISDLC_SDD/AISDLC_SDD_v0.9` 與 `AISDLC_SDD/AISDLC_SDD_v0.10` 兩個空目錄；並以 `monkeypatch.setattr(sdd_env.sdd_version, "tracked_version_dirs", lambda _root: None)` 強制 `sdd_version` 走磁碟掃描（不依賴暫存目錄是否落在 git 樹內）；下面「相對 root」與「非 ASCII 根」兩段與 `sub` 無關，可只在 parametrize 之外的另一個測試函式做一次（該函式名稱同樣須含 `AT_001_1_2`，讓 `-k` 篩得到）
  When 對每個 `sub`（`autoclaude`、`agentconsole`、`monorepo`、`sdd`）呼叫 `sdd_env.main(["--sub", sub, "--slug", "my-feature", "--root", str(假根), "--shell", "json"])`，並先記下假根的目錄樹
  And 再以 `monkeypatch.chdir(tmp_path)`（即假根的父目錄）切換工作目錄，對 `autoclaude` 用相對的 `--root` 值 `fake_root` 呼叫 `sdd_env.main(["--sub", "autoclaude", "--slug", "my-feature", "--root", "fake_root", "--shell", "json"])`，再用尾端帶路徑分隔符的 `--root` 值（`"fake_root" + os.sep`）呼叫一次
  And 另造非 ASCII 的假根 `tmp_path / "根目錄"`（其下同樣有 `AISDLC_SDD/AISDLC_SDD_v0.10` 空目錄），對 `autoclaude` 以 `--slug my-feature`、`--shell json` 與該根的絕對路徑呼叫一次，並保留 stdout 原文（不先經 `json.loads`）
  Then 每次 rc 都是 `0`，`SDD_ACTIVE_VERSION` 為 `0.10`（數值排序，不是字串排序），`SDD_PROJECT` 為 `<sub>-my-feature`
  And `SDD_STATE_DIR` 依 sub 分別等於以 `os.path.join` 串起的絕對路徑：`autoclaude` 為假根之下 `AutoClaude`、`build`、`reports`、`fsm` 四段；`agentconsole` 為假根之下 `AgentConsole`、`build`、`reports`、`fsm` 四段；`monorepo` 為假根之下 `build`、`reports`、`fsm` 三段；`sdd` 為假根之下 `AISDLC_SDD`、`AISDLC_SDD_v0.10`、`build`、`reports`、`sdd-dogfood` 五段
  And 呼叫前後假根的目錄樹相同（沒有建立任何檔案或目錄）
  And 兩次相對 root 呼叫的 rc 都是 `0`，各自 `SDD_STATE_DIR` 的 `os.path.isabs` 皆為真，且都等於以 `os.path.join` 把 `os.path.abspath(<該相對 root>)` 與 `AutoClaude`、`build`、`reports`、`fsm` 串起來的路徑（兩次的值相同）
  And 非 ASCII 根那次的 rc 是 `0`，`SDD_STATE_DIR` 的值含目錄名 `根目錄`，且 stdout 原文逐字含 `根目錄` 這個字串（證明 `ensure_ascii=False`，非 ASCII 字元沒有被轉成 `\uXXXX` 跳脫）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_1_2]"
```

```gherkin
# AT-001-2-1
# 對應 AC: AC-001-2 powershell 形態（單引號雙寫）
# 測試類型: Unit
# 自動化工具: pytest + capsys + tmp_path + monkeypatch

Feature: sdd_env 的 powershell 輸出

Scenario: powershell 形態每個變數一行，值中的單引號雙寫
  Given 在 monorepo 根下，`AISDLC_SDD/scripts/sdd_env.py` 已提供 `main(argv: list[str] | None = None) -> int`（完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R10，唯讀；本 AT 只要求 R2、R6 的 powershell 形態成立）
  And 測試追加到 `AISDLC_SDD/scripts/tests/test_sdd_env.py`，本 AT 的測試函式名稱須含 `AT_001_2_1`，例如 `test_AT_001_2_1_powershell_lines_and_quote_escaping`；以 `tmp_path / "o'brien"` 當假 monorepo 根（其下有空目錄 `AISDLC_SDD/AISDLC_SDD_v0.30`；同樣以 monkeypatch 強制 `sdd_version` 走磁碟掃描），讓狀態目錄路徑含一個單引號
  When 呼叫 `sdd_env.main(["--sub", "autoclaude", "--slug", "webhook", "--root", str(假根), "--shell", "powershell"])`
  Then rc 是 `0`；stdout 以換行切開後恰有 5 個非空行，依序以 `$env:SDD_ACTIVE_VERSION = `、`$env:SDD_PROJECT = `、`$env:SDD_STATE_DIR = `、`$env:SDD_ENABLE_RULE_FIRE_TELEMETRY = `、`$env:SDD_ENABLE_RULE_CATCH_TELEMETRY = ` 開頭
  And 第 1、2、4、5 行等號右邊的值依序是 `0.30`、`autoclaude-webhook`、`0`、`0`，每個值都以單引號包住
  And 第 3 行等號右邊是以單引號包住的狀態目錄絕對路徑，路徑中的每個單引號字元都寫成連續兩個單引號；把外層單引號拿掉並把成對單引號還原成一個後，等於以 `os.path.join` 串起 `os.path.abspath(str(假根))` 與 `AutoClaude`、`build`、`reports`、`fsm` 的路徑
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_2_1]"
```

```gherkin
# AT-001-2-2
# 對應 AC: AC-001-2 bash 形態（單引號跳脫序列）
# 測試類型: Unit
# 自動化工具: pytest + capsys + tmp_path + monkeypatch

Feature: sdd_env 的 bash 輸出

Scenario: bash 形態每個變數一行，值中的單引號以標準跳脫序列表示
  Given 在 monorepo 根下，`AISDLC_SDD/scripts/sdd_env.py` 已提供 `main(argv: list[str] | None = None) -> int`（完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R10，唯讀；本 AT 只要求 R2、R6 的 bash 形態成立）
  And 測試追加到 `AISDLC_SDD/scripts/tests/test_sdd_env.py`，本 AT 的測試函式名稱須含 `AT_001_2_2`，例如 `test_AT_001_2_2_bash_lines_and_quote_escaping`；同 AT-001-2-1 以 `tmp_path / "o'brien"` 當假根並強制 `sdd_version` 走磁碟掃描
  When 呼叫 `sdd_env.main(["--sub", "agentconsole", "--slug", "fsm-trail", "--root", str(假根), "--shell", "bash"])`
  Then rc 是 `0`；stdout 以換行切開後恰有 5 個非空行，依序以 `export SDD_ACTIVE_VERSION=`、`export SDD_PROJECT=`、`export SDD_STATE_DIR=`、`export SDD_ENABLE_RULE_FIRE_TELEMETRY=`、`export SDD_ENABLE_RULE_CATCH_TELEMETRY=` 開頭
  And 第 1、2、4、5 行等號右邊的值依序是 `0.30`、`agentconsole-fsm-trail`、`0`、`0`，每個值都以單引號包住
  And 第 3 行等號右邊是以單引號包住的狀態目錄絕對路徑，路徑中的每個單引號字元都寫成由單引號、反斜線、單引號、單引號依序組成的四字元序列；把外層單引號拿掉並把該四字元序列還原成一個單引號後，等於以 `os.path.join` 串起 `os.path.abspath(str(假根))` 與 `AgentConsole`、`build`、`reports`、`fsm` 的路徑
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_2_2]"
```

```gherkin
# AT-001-3-1
# 對應 AC: AC-001-3 slug 格式與長度違規
# 測試類型: Unit
# 自動化工具: pytest + capsys

Feature: sdd_env 的 slug 驗證（格式與長度）

Scenario: 格式不符與超長的 slug 一律 rc 2，stdout 為空，stderr 給出理由
  Given 在 monorepo 根下，`AISDLC_SDD/scripts/sdd_env.py` 已提供 `main(argv: list[str] | None = None) -> int`（完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R10，唯讀；本 AT 只要求 R7 成立）
  And 測試追加到 `AISDLC_SDD/scripts/tests/test_sdd_env.py`，本 AT 的測試函式名稱須含 `AT_001_3_1`，例如 `test_AT_001_3_1_bad_slugs_are_rejected_with_rc_2`；一律用 `--slug=<值>` 的等號形式傳 slug（讓以連字號開頭的值不被 argparse 當成旗標）
  When 對下列每個 slug 各呼叫一次 `sdd_env.main(["--sub", "monorepo", "--slug=" + slug])`：空字串、`-a`、`a-`、`a--b`、`A`、`a_b`、`a b`、`a.b`、`中文`
  And 另以 31 個小寫字母 `a` 組成的 slug 呼叫一次
  Then 前九次每次 rc 都是 `2`，stdout 為空字串，stderr 非空且含 `格式`
  And 第十次（31 個字元）rc 是 `2`，stdout 為空字串，stderr 含 `30`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_3_1]"
```

```gherkin
# AT-001-3-2
# 對應 AC: AC-001-3 保留字與長度邊界
# 測試類型: Unit
# 自動化工具: pytest + capsys + tmp_path + monkeypatch

Feature: sdd_env 的 slug 驗證（保留字與邊界）

Scenario: 保留字 rc 2 並點名保留字；單字元與恰 30 個字元的合規 slug 通過
  Given 在 monorepo 根下，`AISDLC_SDD/scripts/sdd_env.py` 已提供 `main(argv: list[str] | None = None) -> int`（完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R10，唯讀；本 AT 只要求 R7 成立）
  And 測試追加到 `AISDLC_SDD/scripts/tests/test_sdd_env.py`，本 AT 的測試函式名稱須含 `AT_001_3_2`，例如 `test_AT_001_3_2_reserved_words_and_length_boundaries`；一律用 `--slug=<值>` 形式；以 `tmp_path` 造含 `AISDLC_SDD/AISDLC_SDD_v0.30` 空目錄的假根，並強制 `sdd_version` 走磁碟掃描
  When 對 slug `AISDLC_SDD`、`aisdlc_sdd`、`Aisdlc_Sdd` 各呼叫一次 `sdd_env.main(["--sub", "monorepo", "--slug=" + slug])`
  And 另以 `--root` 指向假根、`--shell json`，對 30 個小寫字母 `a` 組成的 slug、單一字元 `a`、`a-b-c-1` 各呼叫一次
  Then 前三次 rc 都是 `2`，stdout 為空字串，stderr 含 `保留字`
  And 後三次 rc 都是 `0`，且各自輸出的 `SDD_PROJECT` 依序為 `monorepo-` 接上該 slug
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_3_2]"
```

```gherkin
# AT-001-4-1
# 對應 AC: AC-001-4 --check：狀態檔存在
# 測試類型: Unit
# 自動化工具: pytest + capsys + tmp_path + monkeypatch

Feature: sdd_env 的 --check（存在）

Scenario: 狀態檔存在時 rc 0 並印 OK 行，不印環境區塊，不改動任何檔案
  Given 在 monorepo 根下，`AISDLC_SDD/scripts/sdd_env.py` 已提供 `main(argv: list[str] | None = None) -> int`（完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R10，唯讀；本 AT 只要求 R8 的存在分支成立）
  And 測試追加到 `AISDLC_SDD/scripts/tests/test_sdd_env.py`，本 AT 的測試函式名稱須含 `AT_001_4_1`，例如 `test_AT_001_4_1_check_reports_an_existing_state_file`；以 `tmp_path` 造假根（含 `AISDLC_SDD/AISDLC_SDD_v0.30` 空目錄並強制磁碟掃描），並在 `<假根>/AutoClaude/build/reports/fsm/` 下建立檔案 `FSM-STATE-autoclaude-webhook.yaml`（內容任意，建檔時用 `encoding="utf-8"`）
  When 先記下假根的目錄樹與該檔內容，再呼叫 `sdd_env.main(["--sub", "autoclaude", "--slug", "webhook", "--root", str(假根), "--check"])`
  Then rc 是 `0`，stdout 恰有一個非空行，該行以 `OK ` 開頭並含該狀態檔的絕對路徑
  And stdout 不含 `SDD_PROJECT` 字樣（沒有印環境區塊）
  And 呼叫前後假根的目錄樹相同，且該狀態檔的內容沒有被改動
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_4_1]"
```

```gherkin
# AT-001-4-2
# 對應 AC: AC-001-4 --check：狀態檔或目錄不存在
# 測試類型: Unit
# 自動化工具: pytest + capsys + tmp_path + monkeypatch

Feature: sdd_env 的 --check（不存在）

Scenario: 狀態檔或整個狀態目錄不存在時 rc 5，且不建立任何檔案或目錄
  Given 在 monorepo 根下，`AISDLC_SDD/scripts/sdd_env.py` 已提供 `main(argv: list[str] | None = None) -> int`（完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R10，唯讀；本 AT 只要求 R8 的不存在分支成立）
  And 測試追加到 `AISDLC_SDD/scripts/tests/test_sdd_env.py`，本 AT 的測試函式名稱須含 `AT_001_4_2`，例如 `test_AT_001_4_2_check_reports_a_missing_state_file_without_creating_anything`；以 `tmp_path` 造兩個假根（各含 `AISDLC_SDD/AISDLC_SDD_v0.30` 空目錄並強制磁碟掃描）
  When 情境一：第一個假根下先建好空的狀態目錄 `<假根>/AgentConsole/build/reports/fsm/`（沒有任何狀態檔）；情境二：第二個假根下完全沒有 `AgentConsole` 目錄；各自先記下目錄樹，再呼叫 `sdd_env.main(["--sub", "agentconsole", "--slug", "fsm-trail", "--root", str(假根), "--check"])`
  Then 兩個情境的 rc 都是 `5`，stdout 為空字串，stderr 含 `state_not_found` 與預期狀態檔（`FSM-STATE-agentconsole-fsm-trail.yaml`）的絕對路徑
  And 兩個情境呼叫前後的目錄樹都相同（沒有建立任何檔案或目錄；情境二尤其不得建出 `AgentConsole` 或 `build` 目錄）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_4_2]"
```

```gherkin
# AT-001-5-1
# 對應 AC: AC-001-5 失敗邊界與零副作用
# 測試類型: Unit
# 自動化工具: pytest + capsys + tmp_path + monkeypatch

Feature: sdd_env 的失敗邊界

Scenario: 版本不可解、root 不是目錄、用法錯誤各有明確 rc；成功呼叫不改環境、不建檔
  Given 在 monorepo 根下，`AISDLC_SDD/scripts/sdd_env.py` 已提供 `main(argv: list[str] | None = None) -> int`（完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R10，唯讀；本 AT 要求 R1、R4、R5、R9、R10 成立）
  And 測試追加到 `AISDLC_SDD/scripts/tests/test_sdd_env.py`，本 AT 的測試函式名稱須含 `AT_001_5_1`，例如 `test_AT_001_5_1_failure_boundaries_and_zero_side_effects`；以 `tmp_path` 造假根並強制 `sdd_version` 走磁碟掃描
  When 情境一：假根下有 `AISDLC_SDD/` 目錄但其下沒有任何 `AISDLC_SDD_v*` 版本目錄，呼叫 `sdd_env.main(["--sub", "monorepo", "--slug", "demo", "--root", str(假根)])`
  And 情境二：`--root` 分別指向一個不存在的路徑、一個既有的檔案（不是目錄），各呼叫一次（其餘引數合法）
  And 情境三：缺 `--slug`；`--sub` 為 `bogus`；`--shell` 為 `zsh`，各呼叫一次（每次只有這一項不合法，其餘引數合法）
  And 情境四：另一個含 `AISDLC_SDD/AISDLC_SDD_v0.30` 的假根，呼叫 `sdd_env.main(["--sub", "autoclaude", "--slug", "demo", "--root", str(假根), "--shell", "bash"])`，呼叫前後各存一份 `dict(os.environ)` 與假根的目錄樹
  And 情境五：呼叫 `sdd_env.main(["--help"])`
  Then 情境一的 rc 是 `1`，stdout 為空字串，stderr 含 `AISDLC_SDD_v`
  And 情境二兩次的 rc 都是 `2`，stdout 為空字串，stderr 含 `root`
  And 情境三三次的 rc 都是 `2`（argparse 用法錯誤，其 `SystemExit` 已在 `main` 內攔截並轉成回傳值），stdout 為空字串
  And 情境四的 rc 是 `0`，呼叫前後 `os.environ` 逐項相等、假根目錄樹相同（沒有改環境、沒有建檔）
  And 情境五的 rc 是 `0`，stdout 非空且含 `--sub` 與 `--slug`（argparse 的 usage 文字，是 R10 唯一允許 stdout 出現環境區塊以外內容的情形），且沒有拋出任何例外
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_5_1]"
```

---

## 3. AT 完整清單

### 3.1 Unit Tests

| AT ID | 對應 AC | 描述 | 測試方法 | 預期結果 |
|-------|---------|------|---------|---------|
| AT-001-1-1 | AC-001-1 | 預設根與預設 json 的五變數 | AISDLC_SDD/scripts/tests/test_sdd_env.py::test_AT_001_1_1_* | 值逐項正確、兩種呼叫輸出相同 |
| AT-001-1-2 | AC-001-1 | 四個 sub 的狀態目錄查表，版本數值排序；相對根與非 ASCII 根 | test_AT_001_1_2_*（parametrize） | 0.10 勝過 0.9，路徑逐段正確；相對根轉絕對；中文目錄名原樣輸出 |
| AT-001-2-1 | AC-001-2 | powershell 五行與單引號雙寫 | test_AT_001_2_1_* | 行首與值逐行正確 |
| AT-001-2-2 | AC-001-2 | bash 五行與單引號跳脫序列 | test_AT_001_2_2_* | 行首與值逐行正確 |
| AT-001-3-1 | AC-001-3 | 格式與長度違規的 slug | test_AT_001_3_1_* | rc 2、stdout 空、理由含格式或 30 |
| AT-001-3-2 | AC-001-3 | 保留字與 1、30 字邊界 | test_AT_001_3_2_* | 保留字 rc 2；邊界 rc 0 |
| AT-001-4-1 | AC-001-4 | --check 狀態檔存在 | test_AT_001_4_1_* | rc 0、OK 行、不建檔 |
| AT-001-4-2 | AC-001-4 | --check 狀態檔或目錄不存在 | test_AT_001_4_2_* | rc 5、state_not_found、不建檔不建目錄 |
| AT-001-5-1 | AC-001-5 | 版本不可解、root 非目錄、用法錯誤、--help、零副作用 | test_AT_001_5_1_* | rc 1、2、2、0（--help）；環境與目錄樹不變 |

### 3.2 Integration Tests

（無；本 Feature 是命令列腳本，以 tmp_path 隔離，不碰真實狀態檔。）

### 3.3 Contract Tests

（無。）

### 3.4 E2E Tests

（無；hooks-ON 視窗啟動後的活性驗收屬 SOP §8.2(c)，不屬本增量。）

---

## 4. 邊界與錯誤測試規格

邊界與錯誤情境已併入 AC-001-3、AC-001-4、AC-001-5（以 `AT-001-<AC>-<n>` 命名，列於 §1）；本節不另列文件內編號的 `AT-001-E-n`。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|---------|
| 邊界值（最小 slug） | AT-001-3-2 | 單一字元 slug | a | rc 0 |
| 邊界值（最大 slug） | AT-001-3-2 | 恰 30 個字元 | 30 個 a | rc 0 |
| 邊界值（超長） | AT-001-3-1 | 31 個字元 | 31 個 a | rc 2，理由含 30 |
| 空值處理 | AT-001-3-1 | 空字串 slug | 空字串 | rc 2，理由含格式 |
| 非法輸入（格式與保留字） | AT-001-3-1、AT-001-3-2 | 大寫、底線、空白、點、中文、連字號位置不當、保留字三種大小寫 | 見 AT 內清單 | rc 2，理由含格式或保留字 |
| 非法輸入（用法） | AT-001-5-1 | 缺 --slug、--sub 與 --shell 不在選項內 | 見 AT 內清單 | rc 2 |
| 用法求助 | AT-001-5-1 | --help | --help | rc 0，usage 走 stdout（R10 唯一例外） |
| 版本排序邊界 | AT-001-1-2 | v0.9 與 v0.10 並存 | 兩個版本目錄 | 取 0.10 |
| 邊界值（相對 root） | AT-001-1-2 | 相對的 --root，以及尾端帶路徑分隔符的相對值 | fake_root、fake_root 加路徑分隔符 | SDD_STATE_DIR 為絕對路徑，逐段正確且兩次相同 |
| 非 ASCII 輸出 | AT-001-1-2 | root 含中文目錄名時 json 形態原樣輸出 | 根目錄 | stdout 原文逐字含中文目錄名 |
| 檔案系統副作用 | AT-001-4-2、AT-001-5-1 | 不存在的目錄不得被建出；環境不得被改 | 見 AT 內清單 | 目錄樹與 os.environ 前後相同 |
| 並發衝突 | 不適用 | 腳本無共享可變狀態、不寫檔 | — | — |

**刻意不做（附再開症狀）**

| 項目 | 為什麼不做 | 再開症狀 |
|------|-----------|----------|
| 寫入 $PROFILE 或任何使用者設定檔 | 會讓所有視窗靜默帶上同一組三件組，違反「一個 hooks-ON 視窗同時只綁一個功能」（SOP §8.3 第 3 點）；同型先例：D-116-08 不把 SDD_HOOKS_DRY_RUN 寫進 $PROFILE | 掌舵者要求一鍵啟動 hooks-ON 視窗 |
| 啟動 claude | 腳本只產值，環境變數須在 claude 啟動前由使用者貼進視窗；啟動屬 SOP §8.1 的最後一步 | 同上 |
| 建立狀態檔 | `--check` 唯讀；首次建檔由 SOP §8.2(a) 的 show 負責，整個週期唯一允許缺檔即建的一次 | 有人用腳本產出的三件組仍落進框架預設目錄（屆時改收緊 runtime，見 G-116-12） |
| 檢查 --sub 對應的子專案目錄存在 | 腳本只產值；同址驗證由 SOP §8.2(a) 的 show --must-exist 負責 | 使用者因打錯 --root 而把狀態寫到不存在的子專案目錄下 |
| 碰 tools/tests（根層棘輪） | 新增測試只落 AISDLC_SDD/scripts/tests，避免觸發根層 tools/tests 棘輪的重釘儀式 | 根層 CI 需要覆蓋 sdd_env.py 的行為 |
| cmd.exe 與 fish 形態 | SOP 只有 PowerShell 與 bash／zsh 兩種啟動區塊 | 有人在 cmd.exe 或 fish 開 hooks-ON 視窗 |

**需同步的既有測試**：無（只新增兩個檔，不改任何既有檔）。

---

## 5. 測試資料規格

| 資料項目 | 類型 | 說明 | 來源 |
|---------|------|------|------|
| 假 monorepo 根 | 動態生成 | tmp_path 下建 AISDLC_SDD/AISDLC_SDD_v0.30（或 v0.9 與 v0.10）空目錄；含單引號的根用 tmp_path 下名為 o'brien 的子目錄；AT-001-1-2 另用名為 fake_root 的子目錄（以 monkeypatch.chdir 切到其父目錄後，用相對的 --root 值 fake_root 與 fake_root 加路徑分隔符呼叫）與名為「根目錄」的非 ASCII 子目錄 | 各 AT 內聯 |
| git 隔離 | 動態生成 | monkeypatch.setattr(sdd_env.sdd_version, "tracked_version_dirs", lambda _root: None)，強制 sdd_version 走磁碟掃描 | AT-001-1-2 起各 AT |
| 預期路徑 | 動態生成 | 以 os.path.join 與 os.path.abspath 在測試內重新組出，不從腳本輸出反推 | 各 AT 內聯 |
| 狀態檔夾具 | 動態生成 | 空內容或任意內容的 FSM-STATE-<鍵>.yaml（建檔時帶 encoding="utf-8"） | AT-001-4-1 |
| slug 清單 | 靜態字面值 | 非法：空字串、-a、a-、a--b、A、a_b、a b、a.b、中文、31 個 a；保留字：AISDLC_SDD、aisdlc_sdd、Aisdlc_Sdd；合規邊界：a、30 個 a、a-b-c-1 | AT-001-3-1、AT-001-3-2 |

---

## 6. RTM 連結確認

| 追溯項目 | 覆蓋狀態 |
|---------|---------|
| G-116-12 → F-001 | ☑ 已映射（FRD-lite 追溯矩陣） |
| F-001 → US-001 | ☑ 已映射 |
| US-001 → AC-001-1～AC-001-5 | ☑ 已映射 |
| AC-001-1～AC-001-5 → AT-001-1-1～AT-001-5-1 | ☑ 已映射（本文件 §1） |
| AT → CI Pipeline | □ 未整合（測試檔入庫後由 ci-gate 的 scripts/tests 一併執行；下限重釘由主控收尾） |

---

## 📋 SCG-4 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| AC → AT 100% 映射 | 無未映射 AC | □ |
| AT 格式可自動化 | 使用 Given-When-Then 格式 | □ |
| 負向測試覆蓋 | 每個 AC 有至少一個負向 AT（AC-001-1 與 AC-001-2 的負向由 AC-001-3、AC-001-4、AC-001-5 承擔） | □ |
| 邊界值測試 | 關鍵欄位有邊界值測試 | □ |
| 測試資料規格完整 | 資料來源明確定義 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂
