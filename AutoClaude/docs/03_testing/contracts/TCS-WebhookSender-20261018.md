# Test Contract Specification — WebhookSender（TD-1：ESCALATION 的 Webhook HTTP 發送）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統的單一 Feature（增量條款）；FRD-lite 與 TCS 同檔
**存放位置**: `docs/03_testing/contracts/TCS-WebhookSender-20261018.md`（相對 AutoClaude 專案根）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-001 |
| **Feature 名稱** | WebhookSender：以 httpx 發送 ESCALATION 的 Webhook（有界重試、永不拋例外、日誌遮罩 URL） |
| **User Story** | US-001 |
| **建立日期** | 2026-10-18 |
| **QA 負責人** | 整合輪 116 W3 QA（獨立審查者；規格作者＝W2 SA、實作者＝真 haiku 經 Bridge 委派，三方不同） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統（AutoClaude；上位文件已於 Stage-1 採納凍結，採納程序見 `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md` §8.4）的單一 Feature。
> 未列入追溯表視為未滿足；引用不得指向未凍結文件（必須列在 FSM 狀態檔 `frozen_stages[*].spec_docs`）。

### FRD-lite

**現況與變更（Before／After；棕地）**

- Before：`autoclaude/utils/notifier.py` 的 `notify_escalation()` 在 `cfg.notification.webhook_url` 有值時，只記一筆 WARNING「Webhook 通知尚未實作，跳過 webhook_url=<完整 URL>」（第 67～71 行）。Webhook 沒有送出；而且那行日誌把完整 URL（可能夾帶 token）寫進日誌。需求來源：AutoClaude backlog TD-1（`docs/05_development/Phase6_P1_Backlog.md` §5；規劃檔，非凍結上位文件，僅供追溯）。
- After：新增葉節點模組 `autoclaude/utils/webhook_sender.py`；`notify_escalation()` 在 `webhook_url` 有值時改呼叫 `send_webhook(url, payload)`，結果只寫日誌；`webhook_url` 為空時行為逐字不變。

**F-001 `send_webhook`**（新模組 `autoclaude/utils/webhook_sender.py`；唯一消費者是 `notify_escalation()`）

```python
@dataclass(frozen=True)
class WebhookResult:
    ok: bool
    status: int | None
    attempts: int
    error: str | None

def send_webhook(url, payload, *, timeout_s=5.0, max_attempts=3,
                 transport=None, sleep=None) -> WebhookResult: ...
```

**〈F-001 行為規則〉**（R1～R12；先命中者勝的是 R1～R3 的驗證順序）

- **R1 位址驗證**：`url` 須是 `str`，且 `urllib.parse.urlsplit(url)` 的 scheme（轉小寫）等於 `https`、`hostname` 非空；否則回 `WebhookResult(ok=False, status=None, attempts=0, error="invalid_url")`，不發送。空字串、僅空白、非字串、`http`／`ftp` 等其他 scheme、無 scheme、無主機都屬此類；`urlsplit` 本身拋出 `ValueError`（例 `https://[::1`，IPv6 方括號沒閉合；實測 `urlsplit` 對它拋 `ValueError`）也屬 `invalid_url`，不外洩例外。
- **R2 payload 驗證**：`payload` 須是 `dict` 且 `json.dumps(payload, allow_nan=False)` 不拋例外；否則 `error="invalid_payload"`、`attempts=0`、`status=None`，不發送。`allow_nan=False` 是必要的：預設的 `json.dumps` 對 `NaN`、`Infinity` 照樣通過，但 httpx 的 `json=` 編碼會對它們拋 `ValueError`（實測 httpx 0.28.1），不加此旗標會讓 `{"x": float("nan")}` 溜過驗證、到發送時才失敗。
- **R3 參數驗證**：`max_attempts` 須是 `int`（非 `bool`）且 ≥ 1；`timeout_s` 須是 `int` 或 `float`（非 `bool`）且 > 0；否則 `error="invalid_argument"`、`attempts=0`、`status=None`，不發送。`transport`、`sleep` 不驗證（型別由呼叫端負責）。驗證順序固定為 R1 → R2 → R3。
- **R4 發送**：每次嘗試以 `httpx.Client(transport=transport, timeout=timeout_s, follow_redirects=False)` 對 `url` 發一次 `POST`，本文為 payload 的 JSON（`client.post(url, json=payload)`）；`transport=None` 時用 httpx 預設傳輸；每次嘗試用完即關閉 client。`timeout_s` 由 httpx 套到 connect、read、write、pool 四個階段各自的上限（實測 `request.extensions["timeout"]` 的四個鍵都等於 `timeout_s`）。3xx 須帶 `Location` 標頭才會被 httpx 跟隨，所以驗證「不跟隨重導」的 AT 一律用帶 `Location` 的 302（實測 httpx 0.28.1：把 `follow_redirects` 改成 `True` 時，帶 `Location` 的 302 讓 handler 被呼叫兩次，不帶 `Location` 的 302 仍只被呼叫一次，光用裸 302 分辨不出有沒有跟隨）。
- **R5 結果分類**（以該次嘗試為準）：2xx＝成功（`ok=True`、`status=<狀態碼>`、`error=None`）；5xx＝可重試失敗（`error="http_<狀態碼>"`）；`httpx.TransportError`（含逾時等子類）＝可重試失敗（`status=None`、`error=<例外類別名稱>`，例 `ConnectError`、`ReadTimeout`）；其他 HTTP 狀態（含 3xx 與 4xx，含 429；不跟隨重導）＝不重試的失敗（`error="http_<狀態碼>"`）；其他例外（不是 `httpx.TransportError`，例 `RuntimeError`）＝不重試的失敗（`status=None`、`error=<例外類別名稱>`）。只攔截 `Exception`，不攔截 `BaseException`。
- **R6 重試與退避**：只有「可重試失敗」且已嘗試次數小於 `max_attempts` 才再試；第 n 次失敗（n 從 1 起算）之後、下一次嘗試之前呼叫 `sleep(min(0.5 * 2 ** (n - 1), 8.0))`（秒；序列為 0.5、1.0、2.0、4.0、8.0，之後恆為 8.0）；最後一次嘗試之後、成功之後都不睡眠。`sleep=None` 時用 `time.sleep`。`max_attempts` 含第一次嘗試（`max_attempts=3` 至多發 3 次請求）。
- **R7 終局結果**：取**最後一次**嘗試的 `status` 與 `error`，不殘留較早嘗試的值（先 503、再 `httpx.ConnectError`、最後 502，終局是 `status=502`、`error=http_502`；先 502、再 503、最後 `httpx.ReadTimeout`，終局是 `status=None`、`error=ReadTimeout`）；`attempts`＝實際發出的請求次數（R1～R3 驗證失敗為 0）。
- **R8 永不拋例外**：除 `BaseException` 外，任何輸入與任何傳輸層、序列化例外都轉為失敗結果，不外洩例外。
- **R9 日誌**：logger 名稱 `autoclaude.utils.webhook_sender`；**絕不記錄原始 URL**（含 R1 驗證失敗的非 https 位址），也**不記錄 payload 的任何內容**（鍵與值皆然）；只記遮罩後 URL＝`<scheme>://<hostname>`（不含 userinfo、port、path、query、fragment）。每次嘗試前記一筆 DEBUG（訊息含 `attempt=<n>/<max_attempts>`，n 自 1 起逐次加 1，例如 `attempt=1/3`、`attempt=2/3`，以及遮罩後 URL）；終局失敗記一筆 WARNING（訊息含遮罩後 URL、`error`、`attempts`）；R1～R3 驗證失敗記一筆 WARNING，訊息只含 `error` 代碼（不含原始 URL 與 payload 內容）；除此之外不記其他日誌（成功路徑沒有 INFO）。結果的 `error` 欄位同樣不含 URL 的任何部分（只用上述代碼或例外類別名稱）。本規則只管本模組與 notifier 自己寫的日誌：第三方函式庫 httpx 自己的 INFO 日誌（logger 名稱 `httpx`，訊息形如 `HTTP Request: POST <完整 URL> "HTTP/1.1 200 OK"`，實測 httpx 0.28.1 會帶完整 URL，含 userinfo、query 與 fragment）不在本規則範圍；預設 root 為 WARNING 時它不會輸出，AutoClaude 的 `setup_logger` 也只掛 `autoclaude` logger，見 §4 刻意不做。
- **R10 接線呼叫**：`autoclaude/utils/notifier.py` 以模組層級 `from .webhook_sender import send_webhook` 匯入；`notify_escalation(title, message, dump_path, cfg)` 在 `cfg.notification.webhook_url` 為真值時，於寫完 `escalation_alert.log` 之後以位置參數呼叫 `send_webhook(url, payload)`（不帶其他參數）；`payload` 恰有四個鍵 `title`、`message`、`dump_path`、`timestamp`，前三者取自同名引數，`timestamp` 是 `datetime.now(timezone.utc).isoformat()`（帶 `+00:00` 偏移的 ISO 8601 字串）。
- **R11 接線日誌**：結果只寫日誌（logger `autoclaude.utils.notifier`）：成功記 INFO，訊息含 `Webhook`、`status=<n>`、`attempts=<n>`；失敗記 WARNING，訊息含 `Webhook`、`error=<代碼>`、`attempts=<n>`；notifier 的日誌不含 webhook URL。舊的「Webhook 通知尚未實作，跳過 webhook_url=…」警告整段移除。
- **R12 空位址不變**：`webhook_url` 是 `None` 或空字串時：不呼叫 `send_webhook`、不產生任何含 `Webhook` 字樣的日誌；`escalation_alert.log` 與其餘行為逐字不變。特別是 alert log 每行開頭由 `datetime.now().isoformat()` 產生的 naive 本地時間戳不得改動：根層 `tools/tests/test_platform_neutral_paths.py` 的 `_NAIVE_TS_PERSIST_DEBT` 對 `autoclaude/utils/notifier.py` 做雙向精確比對（該檔仍有未帶時區的時間戳持久化站點才算相符），把它改成帶時區的值會讓根層鎖變紅；R10 的 payload `timestamp` 是另一個值（帶時區），不受影響。

| US ID | User Story | AC ID | AC（Given／When／Then） |
|-------|------------|-------|-----------------------|
| US-001 | 作為設定了 notification.webhook_url 的維運者，我要 ESCALATION 發生時 AutoClaude 把事件以 HTTPS POST 送到我的 webhook，且失敗時有界重試、不拖垮引擎、不把密鑰寫進日誌，以便離機收到告警（TD-1） | AC-001-1 | Given 一個 https 位址與可序列化的 payload When 呼叫 send_webhook 且對端回 2xx Then 以 POST 送出 JSON 本文，回傳 ok 為 True、status 為該狀態碼、attempts 為 1、error 為 None，結果物件是 frozen dataclass，timeout_s 傳進 httpx 的逾時設定 |
| US-001 | 同上 | AC-001-2 | Given 位址不是 https 字串（其他 scheme、空值、無主機、非字串，或位址解析本身拋 ValueError） When 呼叫 send_webhook Then 不發送任何請求，回傳 ok 為 False、attempts 為 0、error 為 invalid_url，且不拋例外 |
| US-001 | 同上 | AC-001-3 | Given 對端回 5xx 或發生網路錯誤 When 呼叫 send_webhook Then 以 0.5 秒起倍增、上限 8 秒的退避重試至多 max_attempts 次；回 3xx 或 4xx（含 429）不重試；終局結果取最後一次嘗試 |
| US-001 | 同上 | AC-001-4 | Given payload 不可序列化、參數不合法或傳輸層拋出非預期例外 When 呼叫 send_webhook Then 轉為失敗結果（invalid_payload、invalid_argument 或例外類別名稱），不拋例外；BaseException 不在此列，原樣傳播 |
| US-001 | 同上 | AC-001-5 | Given 位址含 userinfo、port、path、query 與 fragment When 發送（成功或失敗） Then 本模組寫的日誌只含遮罩後的 scheme 加 hostname，結果的 error 不含其餘任何部分（第三方函式庫 httpx 自己的日誌不在此列，見 §4） |
| US-001 | 同上 | AC-001-6 | Given notification.webhook_url 有值 When notify_escalation 被呼叫 Then 以固定四鍵 payload 呼叫 send_webhook 一次、結果只寫日誌；webhook_url 為空時不呼叫、行為逐字不變 |

> 編譯相容提醒：FRD-lite 表的第一欄用 US ID，不把 AC ID 放第一欄（`sdd_compile` 會把「第一欄形如 AC-…」的表格列當成 AC→AT 映射列掃描）。

**INVEST 自檢（US-001）**：獨立（葉節點模組加單一接線點）、可協商（退避常數與錯誤代碼由本檔定義）、有價值（關閉 TD-1，ESCALATION 可離機告警）、可估計（1 個模組、1 處接線、1 個測試檔）、小（模組約 150 行）、可測（9 個 AT 皆為 Unit：網路層一律用 httpx.MockTransport，接線層用 patch 與 caplog）。

**非功能需求（量化）**

| NFR ID | 內容 | 驗證方式 |
|--------|------|----------|
| NFR-001-1 | 依賴與分層：webhook_sender.py 只 import 標準庫與 httpx（pyproject.toml 已宣告 httpx>=0.27），不 import autoclaude 內其他模組（葉節點）；lint-imports 的 rc 為 0（契約條數以 AutoClaude/.importlinter 為準） | SCG-4：lint-imports 實跑與 import 檢視 |
| NFR-001-2 | 規模：新模組 ≤ 200 行（含 docstring）；check_loc_budget.py --json 的 rc 為 0，且新檔不在違規清單 | SCG-4 實跑 |
| NFR-001-3 | 最壞阻塞時間（預設參數、同步呼叫）的名目值＝3×5.0＋0.5＋1.0＝16.5 秒（推算值，非量測；稱名目值是因為 httpx 的 `timeout=5.0` 是 connect、read、write、pool 各階段各自的上限，單次嘗試的實際最壞耗時可高於 5.0 秒，所以 16.5 秒不是硬上限）；測試以注入的 sleep 與 MockTransport 執行、不真的睡眠，整個測試檔牆鐘 < 5 秒（pytest tests/utils/test_webhook_sender.py -q -n 0 實測） | SCG-4 實跑 |
| NFR-001-4 | 測試不碰網路、不真睡眠：只經 httpx.MockTransport 發送；不呼叫 httpx.get、httpx.post 等模組層便利函式，不開 socket | SCG-4：grep 檢視 |
| NFR-001-5 | 靜態檢查：ruff check 對三個異動檔（autoclaude/utils/webhook_sender.py、autoclaude/utils/notifier.py、tests/utils/test_webhook_sender.py）0 錯；規則集與行寬 100 以 AutoClaude/pyproject.toml 為準，E501 以東亞寬度計（一個中文字佔 2 欄） | SCG-4 實跑 |
| NFR-001-6 | 根層護欄相容：測試檔不新增 skip、skipif、xfail，不用 sys.platform 分支；所有 open、read_text、write_text 帶 encoding="utf-8"；測試字面值不含磁碟機代號開頭的路徑；含 userinfo 的假 URL 一律用 example.com 子網域當主機（機密掃描的佔位符判準放行） | SCG-4：根層 tools/tests 相關鎖 |
| NFR-001-7 | 零退化：AutoClaude 既有測試（含 tests/utils/test_notifier.py、tests/plugins/test_notification_plugin.py、tests/integration/test_kernel_escalation_artifacts_def_200_518.py）續綠；既有測試沒有任何一支斷言「尚未實作」字樣（實查 AutoClaude/tests：零命中） | SCG-4 實跑 |
| NFR-001-8 | 覆蓋：根層 .venv 沒有 pytest-cov 與 coverage（2026-10-18 實查），也不得為了量覆蓋率把它們裝進根層 .venv（那會改動全專案共用環境）；本檔不以覆蓋率百分比為閘。若 SCG-4 審查者要量覆蓋率，須在隔離環境（獨立的臨時 venv，不碰根層 .venv、不改任何 repo 檔）自行安裝後量測；通過判準仍是審查逐條核對 R1～R12 每一條至少被一個 AT 觸及（R1→AT-001-2-1、R2 與 R3→AT-001-4-E-1、R4 與 R5→AT-001-1-1 與 AT-001-3-E-1、R6 與 R7→AT-001-3-1 與 AT-001-3-2、R8→AT-001-4-E-1、R9→AT-001-5-1、R10 與 R11→AT-001-6-1、R12→AT-001-6-2） | SCG-4 人工逐條核對；覆蓋率（若量）在隔離環境量 |
| NFR-001-9 | 評估環境：評估指令（`pytest tests -k "<AT 底線形>" -q`，在 AutoClaude 專案根）由引擎行程執行，不是由 haiku 的 shell 執行，所以 haiku 在自己的 shell 設環境變數救不了 evaluator。本機（Windows，本機 PG 容器在場）裸跑時，`tests/conftest.py` 的護欄會在 0.6 秒內以 rc 4 中止（訊息「PG 在場但未用 --dist loadgroup」；2026-10-18 實測）。因此 Bridge 路徑要在 `POST /autoclaude/runs` 的請求層 `env` 帶 `AUTOCLAUDE_NO_PG_AUTODETECT: "1"`（Bridge 的 `_ENV_DENY` 不含此變數，實查 `AgentConsole/engine-bridge/app/security.py`）；啟動前在同一個環境先跑 `pytest tests -k "AT_NONE" -q`，確認 rc 為 5（沒有測試被選中）而不是 4。設定後整棵 tests 收集約 8.6 秒（2026-10-18 實測，全部 deselect 時的牆鐘，rc 5），遠低於 evaluator 預設 120 秒逾時 | 啟動 DF-A 的人（主控或操作員）在引擎環境現驗；QA 重跑時同樣要設 |
| NFR-001-10 | 異動範圍守衛：實作完成後，相對實作開始前的乾淨基線（本檔與凍結狀態由主控先落版，實作者開工時工作樹沒有其他未提交變更），`git diff --name-only` 加上未追蹤檔（`git status --porcelain` 的 `??` 列）列出的檔案恰為三個：`autoclaude/utils/webhook_sender.py`、`autoclaude/utils/notifier.py`、`tests/utils/test_webhook_sender.py`；不得新增其他 `.py`，也不得動 `tests/conftest.py`、`pyproject.toml`、任何設定檔、`tools/` 與根層檔案。理由：根層檔案數鎖的餘裕極薄（2026-10-18 實測：`AutoClaude/tests` 遞迴 `test_*.py` 共 302 支，`tools/lib/skip_tag_policy.py` 的 `_TREE_FILE_FLOORS` 對 `AutoClaude/tests` 的下限是 241，`int(302×0.8)＝241` 恰好相等）；新增本 Feature 唯一的測試檔後為 303 支，`int(303×0.8)＝242` 大於 241，根層 `tree_floor_problems()` 的「下限已過期」向會變紅，須由主控在收尾把下限重釘為 242；實作者每多建一個 `test_*.py`，數字就再升一次 | SCG-4：`git diff --name-only` 與 `git status --porcelain` 實跑核對；根層下限重釘由主控在收尾做，實作者不動 |

**追溯矩陣**：F-001 ← AutoClaude backlog TD-1（`docs/05_development/Phase6_P1_Backlog.md` §5；規劃檔、非凍結上位文件，僅供追溯）與 `autoclaude/utils/notifier.py` 的「尚未實作」註記；整合輪 116 裁決 D-116-15（DF-A）；US-001 → AC-001-1～AC-001-6 → AT-001-1-1～AT-001-6-2（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；清單取自 `/sdd-gate` 的 SCG-0～3 檢查表；「已凍結上位文件」均相對 `spec-frozen --root`＝AutoClaude 專案根）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定（Status: Approved） | ADOPTED；棕地增量，AutoClaude 無獨立 PRD，需求基線＝專案規範與三份 SRD 增補；功能來源 TD-1（規劃檔，僅供追溯） | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-0／FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯） | F-001（本檔 FRD-lite）；最近依據 ADOPTED CLAUDE.md〈AutoClaude 專案架構〉的 utils／notifier 與〈PlaybookRunner 關鍵行為〉的 ESCALATION 條 | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-0／NFR 已量化定義 | NFR-001-1～10（本檔）；最近依據 ADOPTED SRD-AGT-Phase1 §4 共通約束（LOC 分級、新模組測試、純新增可回滾） | docs/02_architecture/SRD_AGT_Phase1_Memory.md | sha256:7b13674e2c29d22f1442e4e3650284765badeb419820513cf7cb010ca670cc2a |
| SCG-0／User Story 已完成 INVEST 檢查 | US-001（本檔 INVEST 自檢） | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-0／利害關係人已確認簽核 | 掌舵者授權代決（整合輪 116 D-116-15；決策出處為規劃檔 AutoSDD_improving_116.md，僅作 ID 追溯，非上位文件） | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-0／RTM 初版已建立 | 本增量自帶：本檔 §1 與 §6（AC→AT 映射） | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD 完成並通過 Review（Status: Approved） | ADOPTED SRD-AGT-Phase2 §0 擴充點實證表（收斂升級與重試耗盡兩處升級入口）；升級後經 ON_ESCALATION 觸發通知的路徑見 CLAUDE.md〈PlaybookRunner 關鍵行為〉ESCALATION 條 | docs/02_architecture/SRD_AGT_Phase2_Closedloop.md | sha256:d69ecf6eaec3fd348e78ab1102e4f573cb47caacc81e7e5f7041bf0c70b8be4e |
| SCG-1／API Spec 草稿完成（所有端點清單） | 不適用（本功能是出站 client，無對外 HTTP 端點）；函式簽名契約＝本檔 FRD-lite；最近先例 ADOPTED SRD-AGT-Phase3 §1.1（Port 介面規格） | docs/02_architecture/SRD_AGT_Phase3_Autonomy.md | sha256:1916b5a972717fe1b40cb82189b8c10720b93b734f885ad93892ae48dab84571 |
| SCG-1／資料模型設計完成 | WebhookResult 四欄 frozen dataclass 與 payload 四鍵（本檔 FRD-lite）；無持久化；最近依據 ADOPTED CLAUDE.md〈模型欄位〉 | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-1／NFR 設計對應完成（架構選型對應 NFR 指標） | NFR-001-1～10 對應 R4～R9（NFR-001-10 為異動範圍守衛）；有界重試與 SRD-AGT-Phase2 §1.2「有界性」同向 | docs/02_architecture/SRD_AGT_Phase2_Closedloop.md | sha256:d69ecf6eaec3fd348e78ab1102e4f573cb47caacc81e7e5f7041bf0c70b8be4e |
| SCG-1／整合架構說明完整（第三方服務已識別） | 第三方＝使用者設定的 https webhook 端點；經 httpx 出站（已是依賴）；出站安全先例 ADOPTED SRD-AGT-Phase3 §1.2（allowlist 安全閘） | docs/02_architecture/SRD_AGT_Phase3_Autonomy.md | sha256:1916b5a972717fe1b40cb82189b8c10720b93b734f885ad93892ae48dab84571 |
| SCG-2／C4 Context 圖完成（系統邊界清晰） | 不適用（不新增系統邊界；出站對象是使用者自備端點）；最近依據 ADOPTED CLAUDE.md〈AutoClaude 專案架構〉 | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-2／C4 Container 圖完成（主要組件識別） | 不適用（落在既有 utils 層，不新增容器）；最近依據 ADOPTED CLAUDE.md〈核心目錄結構〉 | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-2／所有架構決策有對應 ADR（Status: Accepted） | 本增量無新架構決策（沿用既有 httpx 依賴與 utils 葉節點慣例）；ADR 索引見 CLAUDE.md〈快速導覽〉 | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-2／Trust Boundary Map 完成（Security 情境） | 不適用（scenario 為 brownfield，非 security）；新增一條出站信任邊界，SSRF 與 payload 外送風險已登 §4 刻意不做；最近依據 ADOPTED SRD-AGT-Phase3 §1.2、§1.3 | docs/02_architecture/SRD_AGT_Phase3_Autonomy.md | sha256:1916b5a972717fe1b40cb82189b8c10720b93b734f885ad93892ae48dab84571 |
| SCG-2／Before／After 架構對比（Brownfield 情境） | 本檔 FRD-lite〈現況與變更〉；Before 的既有行為見 ADOPTED CLAUDE.md〈PlaybookRunner 關鍵行為〉ESCALATION 條（桌面通知加 escalation_alert.log） | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-3／OpenAPI 3.1 規格完整（所有端點含完整 Schema） | 不適用（無對外 HTTP API；出站 client）；契約＝函式簽名（本檔 FRD-lite） | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-3／Request／Response Schema 定義完整 | payload 四鍵 title、message、dump_path、timestamp 與 WebhookResult 四欄（R10、FRD-lite） | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-3／錯誤碼定義（400／401／403／404／500） | error 代碼表（invalid_url、invalid_payload、invalid_argument、http_<狀態碼>、例外類別名稱；R1～R5）；HTTP 狀態分類見 R5 | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-3／Consumer Contract 完成（整合情境） | 唯一消費者 notify_escalation()（R10～R12、AC-001-6） | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-3／API ID 與 RTM 已對應 | 無 API ID；AT 到 RTM 見本檔 §1 與 §6 | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |
| SCG-3／Contract 已 Review 通過 | 由未參與規格與實作的 QA 於 SCG-4 獨立審查（W3）；裁決 D-116-15 | CLAUDE.md | sha256:2baac9fe1ed9c36cb016d0c018bfde7d2421017ab12b2805b1f6e35ebb904d41 |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值（`fsm_runtime show` 可查）。本表各值取自 Stage-1 凍結（2026-10-18T10:35:20+08:00，approver 為掌舵者代理（主控），reason 為「baseline adoption；SCG 未重跑」）後 `show` 的逐字輸出，並已用檔案現況獨立重算複驗一致；Stage-1 的四份上位文件與 HEAD（81faa59a）逐字相同（棕地基線採納）。

---

## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC；`AT-001-3-E-1` 這類邊界 AT 掛在其所屬 AC 之下，符合文法並由引擎執行。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-001-1 | 成功路徑：2xx 即成功，POST JSON | AT-001-1-1 | 200、201、204 皆回成功結果，請求為 POST 加 JSON，結果物件為 frozen；timeout_s 傳進 httpx 的逾時設定 | ✅ | Unit | □ |
| AC-001-2 | 只接受 https 位址 | AT-001-2-1 | 非 https、空值、無主機、非字串、位址解析拋 ValueError 的位址一律不發送 | ✅ | Unit | □ |
| AC-001-3 | 5xx 與網路錯誤才重試（指數退避） | AT-001-3-1 | 先失敗後成功：退避為 0.5 與 1.0 秒 | ✅ | Unit | □ |
| AC-001-3 | 5xx 與網路錯誤才重試（指數退避） | AT-001-3-2 | 重試用盡：終局為最後一次結果（含混合失敗序列不殘留前次值），退避封頂 8 秒 | ✅ | Unit | □ |
| AC-001-3 | 5xx 與網路錯誤才重試（指數退避） | AT-001-3-E-1 | 帶 Location 的 302 與 4xx（含 429）不重試且不跟隨；max_attempts 為 1 時 5xx 也不重試 | ✅ | Unit | □ |
| AC-001-4 | 永不拋例外 | AT-001-4-E-1 | 非預期例外、壞 payload（含 NaN）、壞參數（含 bool）皆轉為失敗結果；BaseException 原樣傳播 | ✅ | Unit | □ |
| AC-001-5 | 日誌只印遮罩後 URL | AT-001-5-1 | userinfo、port、path、query、fragment 與 payload 內容不出現在本模組的日誌與 error（含驗證失敗路徑） | ✅ | Unit | □ |
| AC-001-6 | notify_escalation 接線 | AT-001-6-1 | 有 webhook_url：以固定四鍵 payload 呼叫一次並寫日誌（以含 Webhook 的記錄篩出計數） | ✅ | Unit | □ |
| AC-001-6 | notify_escalation 接線 | AT-001-6-2 | 無 webhook_url：不呼叫、不留 Webhook 日誌、行為逐字不變（含 alert log 的 naive 時間戳） | ✅ | Unit | □ |

**覆蓋率統計**:
- 總 AC 數: 6
- 已映射 AT 數: 9
- 映射覆蓋率: 100% （目標: 100%）

---

## 2. 可自動化 AT 格式規範

> **驗收字樣**：每個 AT 的最後一個 `And` 行帶一個以雙引號包住的驗收字樣（例 `[AT_OK_001_1_1]`）。編譯時引擎把 Then 與其後 And 行中「第一個引號字面值」轉成**模型最後一則回覆必須含有的 regex**，所以本節 Then、And 行**只有驗收字樣一組引號**；其餘程式碼字面值一律用反引號。真正的通過判準是引擎另行執行的評估指令（`pytest tests -k "<AT 底線形>" -q`，在 AutoClaude 專案根），驗收字樣只是回報用。

```gherkin
# AT-001-1-1
# 對應 AC: AC-001-1 成功路徑（2xx 即成功，POST JSON）
# 測試類型: Unit
# 自動化工具: pytest + httpx.MockTransport

Feature: send_webhook 成功路徑

Scenario: https 位址收到 2xx，回傳成功結果，請求為 POST 加 JSON 本文
  Given 在 AutoClaude 專案根下，模組 `autoclaude/utils/webhook_sender.py` 提供 `send_webhook(url, payload, *, timeout_s=5.0, max_attempts=3, transport=None, sleep=None) -> WebhookResult`（檔案不存在就新建；已存在就沿用並擴充）
  And `WebhookResult` 是 `@dataclass(frozen=True)`，欄位依序為 `ok: bool`、`status: int | None`、`attempts: int`、`error: str | None`
  And 完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R9（唯讀，不得修改該檔）；本 AT 只要求其中成功路徑（R4 含 `timeout_s` 傳遞、R5 的 2xx、R7）成立
  And 測試放在 `tests/utils/test_webhook_sender.py`（檔案不存在就新建，已存在就追加並保留其他 AT 的測試函式）；本 AT 的測試函式名稱須含 `AT_001_1_1`，例如 `test_AT_001_1_1_success_posts_json`；只用 `httpx.MockTransport` 發送，不碰網路
  And 若評估指令因本機 PG 護欄以 rc 4 中止（訊息含 PG 在場但未用 --dist loadgroup），就在同一個 shell 先設環境變數 `AUTOCLAUDE_NO_PG_AUTODETECT=1` 再重跑（這只對你自己 shell 內的驗證有效；引擎另行執行評估指令時的環境由啟動者負責，見 NFR-001-9）；不得修改任何 conftest 或設定檔
  When 以 `transport=httpx.MockTransport(handler)` 呼叫 `send_webhook("https://hooks.example.com/escalation", {"title": "T", "message": "M"})`，其中 `handler` 記錄收到的 request 並回傳狀態碼 200（另以 201、204 各重做一次）
  And 另以 `timeout_s=2.5` 再呼叫一次（handler 回傳 200，並把該次的 `request.extensions["timeout"]` 存下來）
  Then 每次回傳 `WebhookResult(ok=True, status=<該次狀態碼>, attempts=1, error=None)`
  And `handler` 每次恰被呼叫一次，request 的 method 是 `POST`、URL 是 `https://hooks.example.com/escalation`、`json.loads(request.content)` 等於傳入的 payload、`content-type` 標頭含 `application/json`
  And 那次 `timeout_s=2.5` 存下來的 `timeout` 項（一個 dict）的 `read` 值等於 `2.5`（證明 `timeout_s` 確實傳進了 httpx 的逾時設定）
  And 對結果物件指派屬性（例如 `result.ok = False`）會拋出 `dataclasses.FrozenInstanceError`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_1_1]"
```

```gherkin
# AT-001-2-1
# 對應 AC: AC-001-2 只接受 https 位址（其餘不發送、不拋例外）
# 測試類型: Unit
# 自動化工具: pytest + httpx.MockTransport

Feature: send_webhook 位址驗證

Scenario: 非 https、空值、無主機與非字串位址一律不發送，回傳 invalid_url
  Given 在 AutoClaude 專案根下，`autoclaude/utils/webhook_sender.py` 已提供 `send_webhook(url, payload, *, timeout_s=5.0, max_attempts=3, transport=None, sleep=None) -> WebhookResult`（先讀既有模組再修改，不得破壞其他 AT 的測試）
  And 完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R9（唯讀）；本 AT 只要求 R1（位址驗證，含 `urlsplit` 拋 `ValueError` 也算 `invalid_url`）與 R8（永不拋例外）成立
  And 測試追加到 `tests/utils/test_webhook_sender.py`，函式名稱須含 `AT_001_2_1`，例如 `test_AT_001_2_1_non_https_urls_are_never_sent`；只用 `httpx.MockTransport`，不碰網路
  And 若評估指令因本機 PG 護欄以 rc 4 中止（訊息含 PG 在場但未用 --dist loadgroup），就在同一個 shell 先設環境變數 `AUTOCLAUDE_NO_PG_AUTODETECT=1` 再重跑（這只對你自己 shell 內的驗證有效；引擎另行執行評估指令時的環境由啟動者負責，見 NFR-001-9）；不得修改任何 conftest 或設定檔
  When 以一個會累計呼叫次數的 `httpx.MockTransport` 為 `transport`，對下列每個位址各呼叫一次 `send_webhook(url, {"k": "v"}, transport=transport)`：字串 `http://hooks.example.com/x`、`ftp://hooks.example.com/x`、`hooks.example.com/x`、`https://`、`https:///path`、`https://[::1`（IPv6 方括號沒閉合，`urlsplit` 會拋 `ValueError`）、空字串、僅含空白的字串；以及非字串的 `None`、整數 `123`、bytes `b"https://hooks.example.com/x"`、列表 `["https://hooks.example.com/x"]`
  Then 每次回傳的 `ok` 為 `False`、`status` 為 `None`、`attempts` 為 `0`、`error` 為字串 `invalid_url`
  And `transport` 的 handler 從未被呼叫（累計次數為 0），且全程沒有拋出任何例外
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_2_1]"
```

```gherkin
# AT-001-3-1
# 對應 AC: AC-001-3 5xx 與網路錯誤才重試，指數退避（先失敗後成功）
# 測試類型: Unit
# 自動化工具: pytest + httpx.MockTransport

Feature: send_webhook 重試與退避（先失敗後成功）

Scenario: 5xx 或網路錯誤後重試成功，退避秒數自 0.5 起倍增
  Given 在 AutoClaude 專案根下，`autoclaude/utils/webhook_sender.py` 已提供 `send_webhook(url, payload, *, timeout_s=5.0, max_attempts=3, transport=None, sleep=None) -> WebhookResult`（先讀既有模組再修改，不得破壞其他 AT 的測試）
  And 完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R9（唯讀）；本 AT 只要求 R5（5xx 與 `httpx.TransportError` 可重試）與 R6（退避序列 0.5、1.0、2.0…，`sleep` 可注入）成立
  And 測試追加到 `tests/utils/test_webhook_sender.py`，函式名稱須含 `AT_001_3_1`，例如 `test_AT_001_3_1_retries_then_succeeds_with_backoff`；以 `sleep=sleeps.append` 注入睡眠（`sleeps` 是測試內的空 list），測試不真的睡眠；只用 `httpx.MockTransport`
  And 若評估指令因本機 PG 護欄以 rc 4 中止（訊息含 PG 在場但未用 --dist loadgroup），就在同一個 shell 先設環境變數 `AUTOCLAUDE_NO_PG_AUTODETECT=1` 再重跑（這只對你自己 shell 內的驗證有效；引擎另行執行評估指令時的環境由啟動者負責，見 NFR-001-9）；不得修改任何 conftest 或設定檔
  When 情境一：handler 依序回傳 503、503、200，呼叫 `send_webhook(url, payload, transport=transport, sleep=sleeps.append)`（預設 `max_attempts=3`）
  And 情境二：另一個 handler 第一次拋出 `httpx.ConnectError`，第二次回傳 200，同樣呼叫（`sleeps` 先清空）
  Then 情境一回傳 `WebhookResult(ok=True, status=200, attempts=3, error=None)`，handler 被呼叫 3 次，`sleeps` 等於 `[0.5, 1.0]`
  And 情境二回傳 `WebhookResult(ok=True, status=200, attempts=2, error=None)`，handler 被呼叫 2 次，`sleeps` 等於 `[0.5]`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_3_1]"
```

```gherkin
# AT-001-3-2
# 對應 AC: AC-001-3 重試用盡，終局取最後一次結果，退避封頂 8 秒
# 測試類型: Unit
# 自動化工具: pytest + httpx.MockTransport

Feature: send_webhook 重試用盡

Scenario: 持續失敗時嘗試次數用盡，終局結果取最後一次，睡眠只在兩次嘗試之間
  Given 在 AutoClaude 專案根下，`autoclaude/utils/webhook_sender.py` 已提供 `send_webhook(url, payload, *, timeout_s=5.0, max_attempts=3, transport=None, sleep=None) -> WebhookResult`（先讀既有模組再修改，不得破壞其他 AT 的測試）
  And 完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R9（唯讀）；本 AT 只要求 R5、R6（含 8 秒上限與「最後一次之後不睡眠」）與 R7（終局取最後一次嘗試，不殘留較早嘗試的 `status` 與 `error`）成立
  And 測試追加到 `tests/utils/test_webhook_sender.py`，函式名稱須含 `AT_001_3_2`，例如 `test_AT_001_3_2_exhausts_attempts_and_reports_last_result`；以 `sleep=sleeps.append` 注入睡眠；只用 `httpx.MockTransport`
  And 若評估指令因本機 PG 護欄以 rc 4 中止（訊息含 PG 在場但未用 --dist loadgroup），就在同一個 shell 先設環境變數 `AUTOCLAUDE_NO_PG_AUTODETECT=1` 再重跑（這只對你自己 shell 內的驗證有效；引擎另行執行評估指令時的環境由啟動者負責，見 NFR-001-9）；不得修改任何 conftest 或設定檔
  When 情境一：handler 永遠回傳 503，呼叫 `send_webhook(url, payload, transport=transport, sleep=sleeps.append)`（預設 `max_attempts=3`）
  And 情境二：handler 永遠拋出 `httpx.ReadTimeout`，其餘同情境一（`sleeps` 先清空）
  And 情境三：handler 永遠回傳 500，並以 `max_attempts=7` 呼叫（`sleeps` 先清空）
  And 情境四：handler 依序回傳 503、拋出 `httpx.ConnectError`、回傳 502，預設 `max_attempts=3`（`sleeps` 先清空）
  And 情境五：handler 依序回傳 502、回傳 503、拋出 `httpx.ReadTimeout`，預設 `max_attempts=3`（`sleeps` 先清空）
  Then 情境一回傳 `ok` 為 `False`、`status` 為 `503`、`attempts` 為 `3`、`error` 為字串 `http_503`，handler 被呼叫 3 次，`sleeps` 等於 `[0.5, 1.0]`
  And 情境二回傳 `ok` 為 `False`、`status` 為 `None`、`attempts` 為 `3`、`error` 為字串 `ReadTimeout`，`sleeps` 等於 `[0.5, 1.0]`
  And 情境三回傳 `ok` 為 `False`、`status` 為 `500`、`attempts` 為 `7`、`error` 為字串 `http_500`，`sleeps` 等於 `[0.5, 1.0, 2.0, 4.0, 8.0, 8.0]`
  And 情境四回傳 `ok` 為 `False`、`status` 為 `502`、`attempts` 為 `3`、`error` 為字串 `http_502`，handler 被呼叫 3 次，`sleeps` 等於 `[0.5, 1.0]`（終局取最後一次嘗試，不殘留第二次的 `ConnectError`）
  And 情境五回傳 `ok` 為 `False`、`status` 為 `None`、`attempts` 為 `3`、`error` 為字串 `ReadTimeout`，handler 被呼叫 3 次，`sleeps` 等於 `[0.5, 1.0]`（`status` 不殘留較早嘗試的 `503`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_3_2]"
```

```gherkin
# AT-001-3-E-1
# 對應 AC: AC-001-3 3xx 與 4xx（含 429）不重試，max_attempts 為 1 時 5xx 也不重試（邊界）
# 測試類型: Unit
# 自動化工具: pytest + httpx.MockTransport

Feature: send_webhook 不重試的邊界

Scenario: 3xx 與 4xx 一次即止，max_attempts 為 1 時 503 也只發一次
  Given 在 AutoClaude 專案根下，`autoclaude/utils/webhook_sender.py` 已提供 `send_webhook(url, payload, *, timeout_s=5.0, max_attempts=3, transport=None, sleep=None) -> WebhookResult`（先讀既有模組再修改，不得破壞其他 AT 的測試）
  And 完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R9（唯讀）；本 AT 只要求 R4（不跟隨重導）、R5（其他 HTTP 狀態不重試）與 R6（`max_attempts` 含第一次）成立
  And 測試追加到 `tests/utils/test_webhook_sender.py`，函式名稱須含 `AT_001_3_E_1`，例如 `test_AT_001_3_E_1_non_retryable_statuses_stop_after_one_attempt`；以 `sleep=sleeps.append` 注入睡眠；只用 `httpx.MockTransport`
  And 若評估指令因本機 PG 護欄以 rc 4 中止（訊息含 PG 在場但未用 --dist loadgroup），就在同一個 shell 先設環境變數 `AUTOCLAUDE_NO_PG_AUTODETECT=1` 再重跑（這只對你自己 shell 內的驗證有效；引擎另行執行評估指令時的環境由啟動者負責，見 NFR-001-9）；不得修改任何 conftest 或設定檔
  When 對狀態碼 302、400、401、404、429 各用一個新的 handler 與一次獨立呼叫，預設 `max_attempts=3`，五次呼叫共用同一個 `sleeps` list；其中 302 的 handler 回傳 `httpx.Response(302, headers={"Location": "https://other.example.com/next"})`（3xx 須帶 `Location` 才會被 httpx 跟隨，光用裸 302 驗不出有沒有跟隨），並記錄每個收到的請求主機；其餘四個狀態碼的 handler 回傳不帶標頭的 `httpx.Response(<狀態碼>)`
  And 另以 handler 固定回傳 503、`max_attempts=1` 呼叫一次
  Then 前五次呼叫各回傳 `ok` 為 `False`、`status` 為該狀態碼、`attempts` 為 `1`、`error` 為 `http_<狀態碼>`（例如 `http_404`），對應 handler 各只被呼叫一次
  And 302 那次的 handler 恰被呼叫一次，且收到的請求主機只有 `hooks.example.com`（沒有任何請求送往 `other.example.com`，即不跟隨重導）
  And 第六次（503 加 `max_attempts=1`）回傳 `ok` 為 `False`、`status` 為 `503`、`attempts` 為 `1`、`error` 為 `http_503`
  And 六次呼叫之後 `sleeps` 仍是空 list（沒有任何一次睡眠）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_3_E_1]"
```

```gherkin
# AT-001-4-E-1
# 對應 AC: AC-001-4 永不拋例外：非預期例外、壞 payload、壞參數（邊界）
# 測試類型: Unit
# 自動化工具: pytest + httpx.MockTransport

Feature: send_webhook 永不拋例外

Scenario: 非預期例外、不合法 payload 與不合法參數都轉為失敗結果
  Given 在 AutoClaude 專案根下，`autoclaude/utils/webhook_sender.py` 已提供 `send_webhook(url, payload, *, timeout_s=5.0, max_attempts=3, transport=None, sleep=None) -> WebhookResult`（先讀既有模組再修改，不得破壞其他 AT 的測試）
  And 完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R9（唯讀）；本 AT 只要求 R2（含 `allow_nan=False`）、R3（含 `bool` 不算 `int`、驗證順序 R1 → R2 → R3）、R5 的「其他例外不重試」與 R8（`BaseException` 例外）成立
  And 測試追加到 `tests/utils/test_webhook_sender.py`，函式名稱須含 `AT_001_4_E_1`，例如 `test_AT_001_4_E_1_never_raises_on_bad_input`；以 `sleep=sleeps.append` 注入睡眠；只用 `httpx.MockTransport`
  And 若評估指令因本機 PG 護欄以 rc 4 中止（訊息含 PG 在場但未用 --dist loadgroup），就在同一個 shell 先設環境變數 `AUTOCLAUDE_NO_PG_AUTODETECT=1` 再重跑（這只對你自己 shell 內的驗證有效；引擎另行執行評估指令時的環境由啟動者負責，見 NFR-001-9）；不得修改任何 conftest 或設定檔
  When 情境一：handler 拋出 `RuntimeError`（不是 httpx 例外），預設 `max_attempts=3`
  And 情境二：位址合法，payload 分別為 `{"x": object()}`、`{"x": {1, 2}}`、`{"x": float("nan")}`，以及不是 dict 的 `None`、字串 `text`、列表 `[1]`（各呼叫一次）
  And 情境三：位址與 payload 合法，`max_attempts` 分別為 `0`、`-1`、`True`、字串 `3`、浮點數 `2.5`，`timeout_s` 分別為 `0`、`-1`、`True`、字串 `5`、`None`（各呼叫一次，其餘參數合法）
  And 情境四：測試內定義 `class _Stop(BaseException): pass`，handler 拋出 `_Stop()`，預設參數呼叫一次（以 `pytest.raises(_Stop)` 包住這次呼叫）
  Then 情境一回傳 `ok` 為 `False`、`status` 為 `None`、`attempts` 為 `1`、`error` 為字串 `RuntimeError`，handler 只被呼叫一次且 `sleeps` 為空 list
  And 情境二的每次呼叫回傳 `ok` 為 `False`、`status` 為 `None`、`attempts` 為 `0`、`error` 為字串 `invalid_payload`，handler 未被呼叫
  And 情境三的每次呼叫回傳 `ok` 為 `False`、`status` 為 `None`、`attempts` 為 `0`、`error` 為字串 `invalid_argument`，handler 未被呼叫
  And 情境四的呼叫把 `_Stop` 原樣拋到呼叫端（R5 與 R8 只攔截 `Exception`，不攔截 `BaseException`），handler 只被呼叫一次且 `sleeps` 為空 list
  And 情境一至情境三的所有呼叫都沒有拋出任何例外（情境四除外）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_4_E_1]"
```

```gherkin
# AT-001-5-1
# 對應 AC: AC-001-5 日誌只印遮罩後 URL（scheme 加 hostname）
# 測試類型: Unit
# 自動化工具: pytest + httpx.MockTransport + caplog

Feature: send_webhook 日誌遮罩

Scenario: 含 userinfo、port、path、query、fragment 的位址不會出現在日誌與結果中
  Given 在 AutoClaude 專案根下，`autoclaude/utils/webhook_sender.py` 已提供 `send_webhook(url, payload, *, timeout_s=5.0, max_attempts=3, transport=None, sleep=None) -> WebhookResult`（先讀既有模組再修改，不得破壞其他 AT 的測試）
  And 完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R9（唯讀）；本 AT 只要求 R9（日誌：logger 名稱 `autoclaude.utils.webhook_sender`、每次嘗試前一筆 DEBUG、終局失敗一筆 WARNING、遮罩後 URL 為 scheme 加 hostname、R1～R3 驗證失敗只記一筆只含 `error` 代碼的 WARNING、任何日誌都不含原始 URL 與 payload 內容、其餘不記）成立
  And 測試追加到 `tests/utils/test_webhook_sender.py`，函式名稱須含 `AT_001_5_1`，例如 `test_AT_001_5_1_logs_only_the_masked_url`；使用 pytest 的 `caplog`，每次呼叫前先 `caplog.clear()`；斷言只針對 logger `autoclaude.utils.webhook_sender` 的記錄（以 `record.name` 篩出再取各筆 `getMessage()`），不要對整個 `caplog.text` 斷言，因為 root logger 若被調到 INFO，httpx 自己的 HTTP Request 日誌（帶完整 URL）會混進去，那不屬本模組；以 `sleep=sleeps.append` 注入睡眠；只用 `httpx.MockTransport`
  And 若評估指令因本機 PG 護欄以 rc 4 中止（訊息含 PG 在場但未用 --dist loadgroup），就在同一個 shell 先設環境變數 `AUTOCLAUDE_NO_PG_AUTODETECT=1` 再重跑（這只對你自己 shell 內的驗證有效；引擎另行執行評估指令時的環境由啟動者負責，見 NFR-001-9）；不得修改任何 conftest 或設定檔
  When 先以 `caplog.set_level(logging.DEBUG, logger="autoclaude.utils.webhook_sender")` 設定擷取，再依序呼叫四次（含 userinfo 的位址字面值，行尾都加註解 `# secret-scan-ok: 合成假值（遮蔽器測試輸入）`）：第一次用位址 `https://u5er:p4ss@hooks.example.com:8443/s3cret/path?tok=t0k3n#frag` 與 payload `{"title": "T", "message": "leak-me-42"}`，handler 依序回傳 503、200
  And 第二次：同位址與同 payload，handler 永遠回傳 500（預設 `max_attempts=3`）
  And 第三次：位址改成 `http://u5er:p4ss@hooks.example.com:8443/s3cret/path?tok=t0k3n#frag`（scheme 是 http，違反 R1），payload 同上，handler 會累計呼叫次數
  And 第四次：位址同第一次（合法的 https），payload 改成 `{"x": object()}`（不可序列化，違反 R2），handler 會累計呼叫次數
  Then 第一次呼叫期間，該 logger 恰有 2 筆 DEBUG 記錄且沒有 WARNING 記錄；兩筆 DEBUG 依序含 `attempt=1/3`、`attempt=2/3`，且每筆都含 `https://hooks.example.com`
  And 第二次呼叫期間，該 logger 恰有 1 筆 WARNING 記錄，訊息含 `https://hooks.example.com` 與 `http_500`
  And 第三次回傳 `error` 為字串 `invalid_url`、`attempts` 為 `0`，該 logger 恰有 1 筆 WARNING 記錄，訊息含 `invalid_url`，handler 未被呼叫
  And 第四次回傳 `error` 為字串 `invalid_payload`、`attempts` 為 `0`，該 logger 恰有 1 筆 WARNING 記錄，訊息含 `invalid_payload`，handler 未被呼叫
  And 四次呼叫中，該 logger 的全部記錄文字（以 `record.name` 篩出，取各筆 `getMessage()`）與四次回傳結果的 `error` 欄位，都不含下列任一字串：`u5er`、`p4ss`、`8443`、`s3cret`、`t0k3n`、`frag`、`leak-me-42`
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_5_1]"
```

```gherkin
# AT-001-6-1
# 對應 AC: AC-001-6 notify_escalation 有 webhook_url 時的接線
# 測試類型: Unit
# 自動化工具: pytest + unittest.mock.patch + caplog

Feature: notify_escalation 的 Webhook 接線（有位址）

Scenario: webhook_url 有值時以固定四鍵 payload 呼叫 send_webhook 一次，結果只寫日誌
  Given 在 AutoClaude 專案根下，`autoclaude/utils/notifier.py` 的 `notify_escalation(title, message, dump_path, cfg)` 依規格出處檔 FRD-lite 的〈F-001 行為規則〉R10～R12 接上 Webhook（先讀既有檔案再修改；不得破壞既有測試）
  And `notifier.py` 以模組層級 `from .webhook_sender import send_webhook` 匯入，使測試能以 `patch("autoclaude.utils.notifier.send_webhook")` 取代；舊的「Webhook 通知尚未實作」警告整段移除
  And 測試追加到 `tests/utils/test_webhook_sender.py`，函式名稱須含 `AT_001_6_1`，例如 `test_AT_001_6_1_notify_escalation_posts_via_send_webhook`；`cfg = AppConfig()`（`from autoclaude.utils.config import AppConfig`），`cfg.checkpoint_dir` 設為 `str(tmp_path)`，並明確設 `cfg.notification.enabled = False`（不彈桌面通知；出廠預設雖已是 `False`，仍要明寫，不依賴預設值）
  And 若評估指令因本機 PG 護欄以 rc 4 中止（訊息含 PG 在場但未用 --dist loadgroup），就在同一個 shell 先設環境變數 `AUTOCLAUDE_NO_PG_AUTODETECT=1` 再重跑（這只對你自己 shell 內的驗證有效；引擎另行執行評估指令時的環境由啟動者負責，見 NFR-001-9）；不得修改任何 conftest 或設定檔
  When 設 `cfg.notification.webhook_url` 為 `https://hooks.example.com/escalation`，以 patch 取代 `send_webhook`（第一輪回傳 `WebhookResult(ok=True, status=200, attempts=1, error=None)`，第二輪回傳 `WebhookResult(ok=False, status=503, attempts=3, error="http_503")`），並以 `caplog.set_level(logging.INFO, logger="autoclaude.utils.notifier")` 擷取日誌，各輪呼叫一次 `notify_escalation("ESC", "step failed", str(tmp_path / "dump.md"), cfg)`（每輪呼叫前先 `caplog.clear()`）
  Then 每一輪 `send_webhook` 都恰被呼叫一次，`call_args.args` 是 `(url, payload)`、`call_args.kwargs` 是空 dict，且 `url` 等於 `cfg.notification.webhook_url`
  And `payload` 恰有四個鍵 `title`、`message`、`dump_path`、`timestamp`，前三者等於呼叫引數；以 `datetime.fromisoformat` 解析 `timestamp` 鍵的值會成功，且結果的 `tzinfo` 不是 `None`
  And 以訊息含 `Webhook` 篩出 `autoclaude.utils.notifier` logger 的記錄：第一輪恰有一筆，等級是 INFO，訊息含 `status=200`、`attempts=1`；第二輪恰有一筆，等級是 WARNING，訊息含 `error=http_503`、`attempts=3`（既有的落檔記錄，訊息含 `已記錄至`、不含 `Webhook`，不計入這個篩選，也不得被移除）
  And 兩輪的記錄文字都不含 `尚未實作`，也都不含 `hooks.example.com`
  And `tmp_path` 下的 `escalation_alert.log` 仍被寫入（既有行為不變）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_6_1]"
```

```gherkin
# AT-001-6-2
# 對應 AC: AC-001-6 notify_escalation 無 webhook_url 時行為逐字不變
# 測試類型: Unit
# 自動化工具: pytest + unittest.mock.patch + caplog

Feature: notify_escalation 的 Webhook 接線（無位址）

Scenario: webhook_url 為 None 或空字串時不呼叫 send_webhook，也不留任何 Webhook 日誌
  Given 在 AutoClaude 專案根下，`autoclaude/utils/notifier.py` 的 `notify_escalation(title, message, dump_path, cfg)` 已依規格出處檔 FRD-lite 的〈F-001 行為規則〉R10～R12 接上 Webhook（先讀既有檔案再修改；不得破壞既有測試）
  And 本 AT 只要求 R12 成立：`webhook_url` 為空時既有行為逐字不變（`escalation_alert.log` 照寫，且每行開頭由既有的 `datetime.now().isoformat()` 產生的 naive 時間戳不得改動，原因見 R12 末句）
  And 測試追加到 `tests/utils/test_webhook_sender.py`，函式名稱須含 `AT_001_6_2`，例如 `test_AT_001_6_2_no_webhook_url_keeps_behaviour_unchanged`；`cfg = AppConfig()`，`cfg.checkpoint_dir` 設為 `str(tmp_path)`，並明確設 `cfg.notification.enabled = False`（不依賴出廠預設值）
  And 若評估指令因本機 PG 護欄以 rc 4 中止（訊息含 PG 在場但未用 --dist loadgroup），就在同一個 shell 先設環境變數 `AUTOCLAUDE_NO_PG_AUTODETECT=1` 再重跑（這只對你自己 shell 內的驗證有效；引擎另行執行評估指令時的環境由啟動者負責，見 NFR-001-9）；不得修改任何 conftest 或設定檔
  When 以 patch 取代 `autoclaude.utils.notifier.send_webhook`，並以 `caplog.set_level(logging.DEBUG, logger="autoclaude.utils.notifier")` 擷取日誌；先把 `cfg.notification.webhook_url` 設為 `None`、再設為空字串，各呼叫一次 `notify_escalation("ESC", "step failed", dump_path, cfg)`，其中 `dump_path` 是 `str(tmp_path / "dump.md")`
  Then `send_webhook` 完全沒有被呼叫
  And 擷取到的所有記錄都不含 `Webhook` 字樣
  And `tmp_path` 下的 `escalation_alert.log` 存在，恰有兩行，每行都含 ` | ESC | step failed | ` 並以 `dump=` 加上 `dump_path` 結尾
  And `escalation_alert.log` 每行開頭、第一個 ` | ` 之前的字串，以 `datetime.fromisoformat` 解析會成功，且結果的 `tzinfo` 是 `None`（既有的 naive 本地時間戳，不得改成帶時區）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_6_2]"
```

---

## 3. AT 完整清單

### 3.1 Unit Tests

| AT ID | 對應 AC | 描述 | 測試方法 | 預期結果 |
|-------|---------|------|---------|---------|
| AT-001-1-1 | AC-001-1 | 2xx 成功路徑、frozen 結果與 timeout_s 傳遞 | tests/utils/test_webhook_sender.py::test_AT_001_1_1_* | ok、status、attempts 為 1、POST JSON、extensions 的 timeout 項 read 為 2.5 |
| AT-001-2-1 | AC-001-2 | 非 https、非字串與解析拋 ValueError 的位址 | test_AT_001_2_1_* | invalid_url、attempts 為 0、零請求 |
| AT-001-3-1 | AC-001-3 | 先失敗後成功與退避序列 | test_AT_001_3_1_* | attempts 為 3 與 2、sleeps 為 [0.5, 1.0] 與 [0.5] |
| AT-001-3-2 | AC-001-3 | 重試用盡、退避封頂與混合失敗序列 | test_AT_001_3_2_* | attempts 為 3、3、7、3、3，封頂 8.0，終局取最後一次 |
| AT-001-3-E-1 | AC-001-3 | 帶 Location 的 302 與 4xx 不重試且不跟隨、max_attempts 為 1 | test_AT_001_3_E_1_* | attempts 為 1、302 的 handler 恰呼叫一次、sleeps 為空 |
| AT-001-4-E-1 | AC-001-4 | 非預期例外、壞輸入與 BaseException | test_AT_001_4_E_1_* | RuntimeError、invalid_payload（含 NaN）、invalid_argument（含 bool）、_Stop 原樣傳播 |
| AT-001-5-1 | AC-001-5 | 日誌遮罩（含驗證失敗路徑） | test_AT_001_5_1_*（caplog） | 只有 scheme 加 hostname；attempt=1/3 與 2/3；invalid_url 與 invalid_payload 各一筆 WARNING；無 payload 內容 |
| AT-001-6-1 | AC-001-6 | notify_escalation 接線（有位址） | test_AT_001_6_1_*（patch、caplog） | 四鍵 payload、含 Webhook 的 INFO 與 WARNING 各一 |
| AT-001-6-2 | AC-001-6 | notify_escalation 接線（無位址） | test_AT_001_6_2_*（patch、caplog） | 不呼叫、無 Webhook 日誌、alert log 時間戳為 naive |

### 3.2 Integration Tests

（無；本 Feature 以 httpx.MockTransport 隔離網路，不做真實外連。）

### 3.3 Contract Tests

（無。）

### 3.4 E2E Tests

（無。）

---

## 4. 邊界與錯誤測試規格

邊界與錯誤情境已併入對應 AC，並以 `AT-001-3-E-1`、`AT-001-4-E-1` 命名掛在 AC-001-3、AC-001-4 之下（符合 AT 文法，列於 §1，由引擎執行）；下表彙整它們與同樣帶邊界性質的 AT。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|---------|
| 邊界值（最小 max_attempts） | AT-001-3-E-1 | max_attempts 為 1 時 5xx 也只發一次 | 503、max_attempts=1 | attempts 為 1、無睡眠 |
| 邊界值（退避上限） | AT-001-3-2 | max_attempts=7 時退避封頂 | 永遠 500 | 末兩次睡眠皆為 8.0 |
| 邊界值（逾時參數傳遞） | AT-001-1-1 | timeout_s 為 2.5 時確實傳進 httpx | timeout_s=2.5、回 200 | extensions 的 timeout 項 read 為 2.5 |
| 非法輸入（位址） | AT-001-2-1 | 非 https、空值、無主機、非字串、解析拋 ValueError | 見 AT 內清單（含 https://[::1） | invalid_url、零請求 |
| 非法輸入（payload 與參數） | AT-001-4-E-1 | 不可序列化 payload（含 NaN）、max_attempts 與 timeout_s 非法（含 True） | 見 AT 內清單 | invalid_payload、invalid_argument |
| 混合失敗序列 | AT-001-3-2 | 終局取最後一次，不殘留較早嘗試的值 | 503、ConnectError、502；502、503、ReadTimeout | 502 與 http_502；None 與 ReadTimeout |
| BaseException 不攔截 | AT-001-4-E-1 | handler 拋自訂 BaseException | `_Stop` | 原樣拋到呼叫端、無睡眠 |
| 日誌洩漏（驗證失敗路徑） | AT-001-5-1 | 帶機密的非 https 位址、不可序列化 payload | 見 AT 內清單 | 各一筆只含代碼的 WARNING、無機密字串 |
| 不重試的 HTTP 狀態 | AT-001-3-E-1 | 302（帶 Location）、400、401、404、429 | 各固定回該碼 | attempts 為 1、302 不跟隨 |
| 並發衝突 | 不適用 | 每次呼叫自建 client、無共享可變狀態 | — | — |

**刻意不做（附再開症狀）**

| 項目 | 為什麼不做 | 再開症狀 |
|------|-----------|----------|
| SSRF 與私網封鎖（127.0.0.0/8、10/8、169.254/16、RFC1918） | 位址來自管理者設定（config.yaml）；另外 Console／Bridge 路徑可經 `config_overrides.notification.webhook_url` 帶入，該路徑受 Bridge 的 `outbound_allowlist` 把關（實查 `AgentConsole/engine-bridge/app/security.py`：`_OVERRIDE_SECTIONS` 含 `notification`、`_URL_KEYS` 含 `notification.webhook_url`）；本輪只要求 https 與設定來源 | webhook URL 可由非管理者輸入，或 Bridge 的 allowlist 放行了內網主機 |
| 重導跟隨 | 3xx 視為不重試的失敗，與 follow_redirects=False 一致 | 使用者回報 webhook 端點以 3xx 轉址而收不到告警 |
| 自訂標頭與簽章（HMAC） | 本輪只送 JSON | 對端要求簽章驗證 |
| 非同步版本 | notify_escalation 目前同步呼叫；最壞阻塞 16.5 秒（NFR-001-3 推算） | ESCALATION 路徑被 webhook 阻塞，拖慢 checkpoint 排程或 TokenGuard |
| 429 的 Retry-After 特別處理 | 429 與其他 4xx 同樣不重試 | 對端以 429 限流造成告警遺失 |
| payload 內容遮罩（title、message 可能含機密） | message 原樣外送；現有 redaction 模組不在本輪接線 | ESCALATION 訊息含機密字串被送到第三方 webhook |
| httpx 自身的 INFO 請求日誌（logger 名稱 httpx） | 屬第三方函式庫的日誌政策，不在本模組控制內；實測 root logger 調到 INFO 時，httpx 0.28.1 會記 HTTP Request 一行，內含完整 URL（含 userinfo、query、fragment）；預設 root 為 WARNING 時不輸出，AutoClaude 的 setup_logger 只掛 autoclaude logger，所以現行預設不會寫進 AutoClaude 日誌檔 | 行程內有人把 root 或 httpx logger 調到 INFO 以下，而 webhook URL 夾帶 token（屆時由 webhook_sender 或 setup_logger 把 httpx logger 壓到 WARNING） |
| Phase6_P1_Backlog.md 的 TD-1 列更新 | 無法以 pytest 判定、不屬 AT；由主控於 SCG-4 通過後處理，實作者不動該檔 | TD-1 列仍寫「尚未實作」 |

**需同步的既有測試**：無（實查 `AutoClaude/tests`：沒有任何測試斷言「Webhook 通知尚未實作」字樣；`webhook_url` 只出現在 `tests/integration/test_config_audit_log.py` 的 PII 分類斷言（第 96、97、102 行），沒有任何既有測試設定 `notification.webhook_url` 來走 `notify_escalation`，所以本變更不會讓既有測試變紅）。

---

## 5. 測試資料規格

| 資料項目 | 類型 | 說明 | 來源 |
|---------|------|------|------|
| webhook 位址 | 靜態字面值 | `https://hooks.example.com/escalation`（example.com 子網域） | 各 AT 內聯 |
| 含 userinfo 的假位址 | 靜態字面值 | `https://u5er:p4ss@hooks.example.com:8443/s3cret/path?tok=t0k3n#frag`，以及 scheme 為 http 的同形字面值 `http://u5er:p4ss@hooks.example.com:8443/s3cret/path?tok=t0k3n#frag`（違反 R1）；所在行行尾都加 `# secret-scan-ok: 合成假值（遮蔽器測試輸入）` | AT-001-5-1 |
| payload | 靜態字面值 | `{"title": "T", "message": "M"}`、`{"k": "v"}`；日誌洩漏用 `{"title": "T", "message": "leak-me-42"}`；壞 payload 用 `{"x": object()}`、`{"x": {1, 2}}`、`{"x": float("nan")}` | 各 AT 內聯 |
| 傳輸替身 | 動態生成 | `httpx.MockTransport(handler)`，handler 為測試內函式並累計呼叫次數；302 的 handler 帶 `Location: https://other.example.com/next` 標頭；AT-001-4-E-1 另在測試內定義 `class _Stop(BaseException)` | 各 AT 內聯 |
| 睡眠替身 | 動態生成 | `sleeps: list[float]`，以 `sleep=sleeps.append` 注入；測試不真的睡眠 | AT-001-3-1、3-2、3-E-1、4-E-1、5-1 |
| 設定物件 | 動態生成 | `AppConfig()`，`checkpoint_dir` 設為 `str(tmp_path)`，`notification.enabled` 明確設為 `False`（不依賴出廠預設值） | AT-001-6-1、6-2 |

---

## 6. RTM 連結確認

| 追溯項目 | 覆蓋狀態 |
|---------|---------|
| TD-1 → F-001 | ☑ 已映射（FRD-lite 追溯矩陣） |
| F-001 → US-001 | ☑ 已映射 |
| US-001 → AC-001-1～AC-001-6 | ☑ 已映射 |
| AC-001-1～AC-001-6 → AT-001-1-1～AT-001-6-2 | ☑ 已映射（本文件 §1） |
| AT → CI Pipeline | □ 未整合（評估指令由 AutoClaude 引擎執行；測試檔入庫後由雲端 autoclaude-ci 的 pytest 一併執行） |

---

## 📋 SCG-4 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| AC → AT 100% 映射 | 無未映射 AC | □ |
| AT 格式可自動化 | 使用 Given-When-Then 格式 | □ |
| 負向測試覆蓋 | 每個 AC 有至少一個負向 AT（AC-001-1 的負向由 AC-001-2、AC-001-3、AC-001-4 承擔） | □ |
| 邊界值測試 | 關鍵欄位有邊界值測試 | □ |
| 測試資料規格完整 | 資料來源明確定義 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂
