# SelfImproving 帳本改 DB P0：基準記錄（D8；AC-LD-02-6、AC-LD-11-1）

- 性質：P0 出口的基準值記錄；P0 不改 `tools/`、協定目錄、守衛面，故程式面基準等於下列 commit。後續階段以此驗證「`params.fingerprint()` 與 `CHECK_RULES_REV` 不變」與「`si check` 在 file 模式的輸出不變」。
- 規則：變動只准**追加新列**（新列的取得指令欄註明「取代」哪一列，不覆寫舊列）；同一項有多列時，DT 取檔內最後一列。
- 契約：`docs/03_testing/contracts/TCS-SelfImprovingLedgerDb-P0-20261027.md` 契約節 C5、§5.6。
- 取證環境：Windows 開發機（win32 剖面）；`si check` 與指紋取證一律在清除 `SI_*`、`AUTOSDD_*` 環境變數後執行。

| 項 | 值 | 取得指令 | 取得時 HEAD |
|---|---|---|---|
| 基準 commit | `fdd9a738fbcca6c5abf25c31dca638648697e6ae`（起草時的 HEAD；P0 出口基準 commit 由主控於收尾以 `git rev-parse HEAD` 現取後追加新列，基準檔由緊接其後的獨立 commit 入庫，故不含自身） | `git rev-parse HEAD` | `fdd9a738` |
| 協定目錄 metrics.md | 8022 bytes；sha256 `d4762244fc21cde5c3b617c2c8372e33dab2dfe4770841d08b7a829e9375581b`；CR 0 | `Get-FileHash -Algorithm SHA256 docs/06_quality/SelfImproving_Protocol/metrics.md` | `fdd9a738` |
| 協定目錄 params.json | 1994 bytes；sha256 `fc48653bfa0107012d2b5316a64bb5ec6d2bac3cdb373b967e7f10ddca1bf197`；CR 0 | 同上，檔名換為 `params.json` | `fdd9a738` |
| 協定目錄 research_sources.json（排除於指紋） | 4721 bytes；sha256 `6a3993e985a6fd530c99641414423c2befb67aa83999af39185642804706ef0a`；CR 0；`FINGERPRINT_EXCLUDED` 排除（`tools/lib/selfimproving/params.py`） | 同上，檔名換為 `research_sources.json` | `fdd9a738` |
| 指紋 | `sha256:1d14bfdbd15e1f6832f45832177b9f3278f7d3caf3b415cb5cdbfc7777d625fd`；分量：`manifest`＝`695b70352f5ba6bcb775f9ab77adc5d5c33c2e1591ddf213ce6266cec59afddc`、`metrics_rev`＝1、`check_rules_rev`＝4 | `python tools/selfimproving.py check` 尾行 `fingerprint=`，或 `lib.selfimproving.params.fingerprint(repo, params_dict)` | `fdd9a738` |
| CHECK_RULES_REV | 4（`tools/lib/selfimproving/params.py` 常數；釘於 `tools/tests/test_selfimproving_p3_meta.py:292`） | `git grep -n CHECK_RULES_REV -- tools` | `fdd9a738` |
| items=33 釘（10 處） | `test_selfimproving_capability.py:624`、`test_selfimproving_check.py:722`（`(ITEMS21, 33)`）、`test_selfimproving_check.py:736`、`test_selfimproving_events.py:1200`、`:1490`、`:1907`、`:2273`、`test_selfimproving_events_p2.py:874`、`test_selfimproving_issues.py:1864`、`test_selfimproving_measure_verb.py:80`（皆在 `tools/tests/`；行號僅提示，以關鍵字仍在為準） | `git grep -n -P -e 'items=33' -e 'all_33_items' -e '\b33\b.{0,30}items' -e 'items.{0,30}\b33\b' HEAD -- 'tools/tests/*selfimproving*.py'` 得 10 行，扣 `test_selfimproving_issues.py:1859`（測試名）、加 `test_selfimproving_check.py:722`（該行不被正則涵蓋）；須用 `git grep -P`（Grep 工具引擎會少列 `:1864`） | `fdd9a738` |
| si check 取證程序 | file 模式：rc 0；首行 `si-check rows=337 items=33`；尾行 `overall=PASS rc=0 fingerprint=sha256:1d14bfdbd15e1f6832f45832177b9f3278f7d3caf3b415cb5cdbfc7777d625fd`；含三項非阻塞 NE（`ref.carrier_families` 的 `CARRIER-NOT-ESTABLISHED`、`events.dec_console` 與 `obs.console_audit` 的 `CONSOLE-KEY-MISSING`；後兩者與環境金鑰環有關）；輸出把首行 `rows=` 數字換成 `rows=<N>` 後 sha256 `af1433e52daaac1189459c25d13a4c74bce494d99d7cf73f4e82c7f2f5d36e92`（1119 字元；**僅當次取證**：輸出含 `CARRIER-NOT-ESTABLISHED` 的 `count=` 行，狀態相依，不是不變量；後續階段只比對 rc、`items=33`、尾行指紋，不比對整份輸出的雜湊，見 TCS §7.2 勘誤 1-1）；須在真實 repo 或含歷史的 `git clone --no-local` 副本執行，`git archive` 副本不可用（缺 git 歷史的項目會 FAIL） | 清除 `SI_*`、`AUTOSDD_*` 後於 repo 根 `python tools/selfimproving.py check`（rc 先存變數、不接管線） | `fdd9a738` |
| skip 摘要（win32） | NE（P0 收尾單人窗口以 `python tools/run_root_unittests.py` 全套實跑後追加新列，貼 `[skip census]` 行原文）；TCS §5.6 的參考值（開發機同日全套日誌，非契約依據）：`tools/tests@win32` 共 46 支，其中 env-disabled 4 支為本機無建立 symlink 權限之環境因素 | `python tools/run_root_unittests.py`（不接管線） | NE |
| SKIP-M6（win32） | NE（同上，收尾追加；記該 id 集合行去掉方括號標籤後的文字，形如 `tools/tests@win32：集合關係成立（本次 skip <N> 支）`）；他平台剖面（darwin、linux）標 NE（P1 前由該平台補錄），不得填猜測值 | 同上 | NE |
| skip_id_ledger.json | 23705 bytes；sha256 `212c15925ae286e630ba23373706a57e048fa292815bb8f597d8bf62782dc909`（AC-LD-11-1：落款不需變動；僅作「P0 不動」的雜湊記錄） | `Get-FileHash -Algorithm SHA256 docs/06_quality/skip_id_ledger.json` | `fdd9a738` |
