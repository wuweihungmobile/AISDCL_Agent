# dry_run_e2e perf 連紅鑑識與基線重播種（Windows；2026-08-31）

> 本檔＝帳本 DEF-200-237（新立）與 DEF-200-229（結案）的具名證據檔。掌舵者
> 2026-08-31 互動拍板：「A 重播種基線」＋「（229）當場修」。刻意不帶輪號——
> 不推當前輪時鐘。

## 一、事件（DEF-200-237）

Windows 機 nightly `perf-baseline` stage 自 2026-08-27 起連四晚 BLOCK：
`dry_run_e2e` p95 對鎖定基線 4.55ms（2026-08-08、git_sha 8314939、本機自量）
+105%～+184%。逐晚實測（nightly log 逐字）：

| 夜 | p95 | delta | 備註 |
|---|---|---|---|
| 08-25 | ~4.9ms | +8.1% | 綠（最後一個綠夜） |
| 08-26 | — | — | 無 nightly log（機器未開；08-27 09:05 有補跑但無 perf 行） |
| 08-27 | 12.9ms | +184.5% | 首紅；**當日 15:19 本機曾重開機** |
| 08-28 | 12.8ms | +181.1% | |
| 08-29 | 10.0ms | +119.0% | |
| 08-30 | 9.3ms | +105.5% | 趨勢遞減但仍 >2 倍 |

## 二、歸因實驗：code 迴歸被 A/B 實測否決

窗口（08-25 22:08～08-27 20:55）內 AutoClaude 生產碼僅動 2 支檔（62 行；
`file_quota_meter.py`＋`file_state_repository.py`，commit 50c5f45／903ceca），
`_cleanup_orphan_tmp` 的逐次 glob 掃描一度是頭號嫌疑。**否決方法**：臨時
worktree（543cb4b＝窗口前）與主樹（70f12b2＝當日 HEAD）同載具、暖機後交錯各量
兩輪（`pytest tests/perf/test_dry_run_e2e.py`，n=20）：

| 輪 | 543c b4b（舊 code）p50 | 70f12b2（新 code）p50 |
|---|---|---|
| 1 | 5.532ms | 5.421ms |
| 2 | 5.462ms | 5.702ms |

差距 <5%，遠低於 nightly 的 +105% ⇒ **窗口內 commit 無罪，屬環境位移**。
（量測期間背景有 pre-push 全套在跑＝兩臂同受干擾，相對比較仍有效；絕對值不可
與基線相比。）另兩個同場景（decide_correction／token_halt_roundtrip）逐晚貼著
基線 ⇒ 非整機均勻變慢，是對 I/O／排程敏感的場景選擇性受影響。

## 三、分鐘級環境現查（凶手未定位，如實留檔）

- 重開機 2026-08-27 15:19（`Win32_OperatingSystem.LastBootUpTime`）＝唯一與首紅
  同日的環境事件。
- HotFix 最後安裝 2026-08-12（窗口外，排除）。
- `autoclaude_pg` 容器現行實例 Up 3 days（≈08-28 起，晚於首紅，排除為首因）。
- 電源計畫「平衡」（預設 GUID）、i5-14600K 時脈正常 ⇒ 無省電模式嫌疑。

深度鑑識（選項 C）經掌舵者拍板不做。

## 四、處置：刪基線段＝機制內建的重播種路徑

- `perf_regression_check.py` 對無基線 section 的場景＝`::warning` 後 `continue`
  （不進 block 計數）⇒ 刪段當晚 perf stage 不再因本場景 BLOCK。
- `perf_baseline_lock.py::should_lock` 對 `baseline_p95=None` 走「無舊 baseline」
  分支：尾 7 筆 history 樣本數達標即自動重鎖，取 **max(p95)**（含 08-27 的
  12.9ms ⇒ 新基線約 12.9ms，最保守值）。
- 環境若恢復，連續 7 晚在容忍內時 lock 會以新尾窗 max 改寫基線 ⇒ **自動向下收緊**，
  不需人工再介入。
- 已知代價（拍板時已告知）：環境恢復前，4.5～12.9ms 之間的 code 退化暫時攔不到。

## 五、DEF-200-229：Windows 併發 checkpoint 寫入殘留競態（結案）

> 誠實訂正：本次 push 被擋時我一度對掌舵者稱「新發現」——實為**已立案 open 缺陷**
> （QA 於 2026-08-27 四方複審發現並登記，且已證非該輪引入）。我未先查帳本即宣稱，
> 屬「宣稱先於查證」同型失誤，據實記錄。
>
> 該列原修法欄原文逐字保全（結案時依 ROW_MAX_BYTES 改短）：「架構決策待定：同
> playbook_id 併發寫入是否需加鎖序列化，或改 last-writer-wins 明確語意」——本次
> 處置的回答＝兩者都不採：有界重試消除瞬態把手假失敗即足以滿足既有斷言；
> 序列化與否留給未來真需要順序保證的功能需求再議。

pre-push 攔下的紅：`tests/integration/test_concurrent_runs.py::
test_two_concurrent_writers_to_the_same_playbook_id_do_not_share_a_tmp_file` 機率性紅
（3 寫入者 1 err）。失敗幀＝`tmp_p.replace(p)` 撞 `PermissionError [WinError 5]`：
CPython 開檔不帶 FILE_SHARE_DELETE ⇒ 讀者（另一 writer 讀 prev、
`load_latest_by_playbook`、外部檢視器）持有目的檔把手的瞬間，`os.replace` 拒絕換名。
POSIX rename 對開著的檔恆成功 ⇒ mac 結構上看不到；DEF-200-043 的 unique-tmp 修復把
碰撞從「共用 tmp」搬到「目的檔 replace」後首次在 Windows 真機現形（觸發需重負載：
閒置機器單測 5/5 綠；鐵律三危害表「目錄項原語」列早已登記本形態，winerror=5）。

修法＝`_replace_waiting_out_readers()` 有界重試（15×20ms=300ms 預算，等不到照舊
拋出）＋確定性測試 `test_a_reader_briefly_holding_the_destination_open_does_not_fail_
the_writer`（Windows 未修確定性紅、修後綠；POSIX 天然綠＝落差本體）。當回合驗證：
驗紅 rc=1 → 修 → `test_concurrent_runs.py`＋`tests/infra` 336 passed、ruff 全過、
`TestDirEntryPrimitivesAreAccountedFor` 7 tests OK（普查帳面免動——原站點的
`except Exception` 包裹已計為有處置，重試僅收窄語意）。
