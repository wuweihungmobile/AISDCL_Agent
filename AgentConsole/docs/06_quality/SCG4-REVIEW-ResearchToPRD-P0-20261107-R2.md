# SCG-4 二審（R2）審查報告——ResearchToPRD P0（鍵 `agentconsole-research-to-prd-p0`）

| 項目 | 內容 |
|------|------|
| 審查日期 | 2026-11-07（一審報告：[SCG4-REVIEW-ResearchToPRD-P0-20261103.md](SCG4-REVIEW-ResearchToPRD-P0-20261103.md)） |
| 審查者 | SCG-4 QA 鏡（Sonnet；與一審同一面鏡，沿用一審方法與判準）；主控（Fable）落檔與親驗 |
| 基準 | HEAD 自 85b9d0b0 前進到 14f01b16；runtime 樹自 FIX-FE 2254a468 起只有 `ErrorReasons.java` 與 `evidence.py` 兩處註解改動，11-03 建置的 Docker 映像＝HEAD 行為 |
| 一審後落地 | FIX-BR 4d239986、FIX-API f2369e7b、FIX-FE 2254a468、勘誤批次 77859c73＋cdc5ddde、RTM 回填 14f01b16 |
| 範圍 | 只重跑受一審 F-01～F-14 與 INT-01～14 影響的 AT、一審存活突變（git archive 副本）、勘誤後條文 vs 實作抽查、一審 P1／P2 逐條判定 |
| **判定** | **PASS（二審）**：P1 0／P2 0 殘留；P3 0；P4 6（不阻擋）；新發現 2（皆 P4） |

一審 F-01～F-14 與 INT-01～14 逐項：已修 25、部分 3（F-11、F-13、INT-14）、不成立 0、未修 0。一審 P2 四條（F-01～F-04）全部已修。

## A. 當回合真跑（QA 鏡）

1. Bridge 研究相關 36 檔（真樹，BRIDGE_TEST_DSN＋SDD_ROOT 在，3 個 pytest 程序 -n 6）：158＋353＋485＝996 通過、0 失敗、0 略過，rc 0；sdd 三檔（cli／freeze／fsm）382 通過／2 略過（既有 symlink），rc 0。
2. backend 全套（git archive 副本，`gradlew cleanTest test`）：2,338 案全數成功、0 失敗、0 略過，BUILD SUCCESSFUL 5m59s；較一審多 14 案。
3. frontend vitest 全套（副本，2,231 案）：兩次各 2,230 通過、1 紅＝`labels.test.ts` 在副本缺 monorepo `docs/` 的環境相依（真樹單檔 5 通過）；首輪另有兩案負載逾時（N-02）。
4. 真棧 Playwright（Docker 全棧、nginx 80、Bridge 釘 pass 劇本、workers 1、分兩輪各 rc 0）：AT_960_22_5（1.8 分）、AT_960_22_3（46 秒）、AT_960_22_E_1（3.2 分）、AT_960_22_4（17 秒）＝4 通過。AT_960_22_2（fail3）QA 不能切劇本（禁 compose 重建），引用主控 INT 重驗補記（[INT-ResearchToPRD-P0-Reverify-20261103.md](INT-ResearchToPRD-P0-Reverify-20261103.md)：fail3 1 通過）[他包回報]。跑完 DB 未封存研究專案為 0。
5. 靜態與指令核對：ruff 兩視角 rc 0；根層 dirent 鎖 7 OK；`check_pytest_baseline_sites` rc 0；`check_loc_budget` rc 0；`os.replace` 族掃描 4 處皆 docstring；tsc／eslint／prettier rc 0；衛生掃描 296 檔零 CR；AT-960-20-4 layout 差異僅 `ToolsRegion.test.tsx`；AT-960-24-1：CLAUDE.md 167／README.md 78 行、RTM-P0「待實作」0、三 ID 家族只出現在本鍵 3 檔。
6. 突變 34 個（git archive 85b9d0b0 副本）：全 KILLED，存活 0——一審 15 個存活者在新碼重做（BRC-2／13／14／20／22／23、BRA-7、BRB-11、API-9／10、DB-15、FB-5、FD-2／3／4）加 FB-6、FB-7 共 17；另 17 個針對 INT／FIX 新碼（見 F）。一審 2 個等價突變仍等價。

## B. 逐項判定（涵蓋 AT 的通過案例數／案例數，(+n)＝一審後新增；突變存活數皆 0）

| 一審項 | 判定 | 證據 |
|--------|------|------|
| F-01（P2）地板邊界 | 已修 | AT-960-12-2 2/2，新增「最低維度恰 60⇒PASS」正例；BRC-2 KILLED |
| F-02（P2）授權待查兩端相反 | 已修 | 9-6 3/3(+2)、10-6 14/14(+1)；D-80 共用期望表 26 案；差分探針 94 輸入：76 寫實輸入 0 分歧、18 特殊空白字元 5 分歧（N-01）；FB-5／6／7 KILLED |
| F-03（P2）邊界 AT 缺 | 已修 | 9-1 28/28(+1)、9-4 3/3(+1)、12-3 5/5(+3)、4-1 3/3(+1)、1-5 1/1；BRC-13／14／22／23、API-9／10、DB-15 KILLED |
| F-04（P2）skipped 載體 | 已修 | 8-E-3 8/8(+2)；BRC-20 KILLED |
| F-05（P3）D-72 錯碼 | 已修 | 14-2、14-3、14-E-1(+1)、14-E-2、5-6；422 digest_mismatch／missing_digests 三端一致；退役鎖保證 spec_digest_changed 不在五處；J-3 KILLED |
| F-06（P3）events limit | 已修 | 10-3 4/4(+1)；BRA-7 KILLED |
| F-07（P3）真棧 spec | 已修（22-2 未獨立驗） | `research-docker.stack.spec.ts`；22-3／22-4／22-5／22-E-1 親跑 PASS；TCS 勘誤 38／39／40 |
| F-08（P3）徽章 class 斷言 | 已修 | 19-1 18/18；FD-2／3／4 KILLED |
| F-09（P3）reason 清單 | 已修（尾巴 R-2） | 後端 22＝前端 22＝契約 §0.2＝Architecture §11.1 四方雙向鎖 |
| F-10（P4）衛生閘 | 已修 | 23-1／23-2／23-4 重跑；勘誤 46 維護 commit 例外 |
| F-11（P4）允許集合 | 部分（R-4） | §5.7 補列已追認 FE 四處；FIX 三包無允許集合 |
| F-12（P4）Content-Length | 已修 | 8-5 12/12(+1)；BRB-11 KILLED |
| F-13（P4）測試檔名／逾時 | 部分（R-3） | 14-8 1/1、2-E-1 26/26（600 秒）；20-4 掃描自我命中仍在 |
| F-14（P4）RTM／ADR-003 §D9 | 已修 | RTM-P0 238 列四格無空白；§D9 已回寫 |
| INT-01 對帳欄位 | 已修 | 4-6 2/2(+1)、21-2 25/25(+1)；J-1 KILLED；真棧 22-3 對帳一致 |
| INT-02 取消後死路 | 已修 | 7-5 5/5、6-4 8/8；N-11 KILLED |
| INT-03 scope 大小寫 | 已修 | 4-2、4-6；J-2 KILLED |
| INT-04 失敗不顯示 | 已修 | 7-5、7-7 3/3、19-7 20/20(+2)；N-1 KILLED |
| INT-05 存稿後對帳誤報 | 已修 | 6-6 6/6(+2)；N-7 KILLED |
| INT-06 非 hermetic | 已修 | 7-3 8/8、8-8 47/47、22-1 17/17、`test_research_offline.py`；N-4 KILLED |
| INT-07 MiniMax 外呼 | 已修 | 7-3、7-E-2 2/2、`test_D_79_*`；N-2／N-3 KILLED |
| INT-08 capabilities 鍵 | 已修 | 2-7 1/1；Bridge 13 鍵；`CapabilitiesDto.sddRoot`；N-10 KILLED；真棧 22-5 |
| INT-09 凍結後標過期 | 已修 | 16-5 8/8；`isReviewStale` 比 sha；F-1 KILLED；真棧 22-3 |
| INT-10 對帳重複計入 | 已修 | 21-2、21-4 3/3；N-5／N-6 KILLED |
| INT-11 劇本六軸 | 已修（文件） | 22-1 17/17；兩份 README |
| INT-12 離線手法／補抓 | 已修 | 10-5 15/15(+2)；F-2 KILLED；真棧 22-4 |
| INT-13 D-72 錯碼 | 已修 | 14-2、14-3；J-3 KILLED |
| INT-14 ①～⑥ | 部分（② 見 R-1） | ① 通用文案、③ 契約勘誤 20、④ host_powershell（N-9 KILLED）、⑤ 節錨點（F-3 KILLED）、⑥ 失敗徽章 |

## C. 殘留清單（P1 無、P2 無 ⇒ PASS；以下 P4，建議勘誤或另案）

- **R-1** INT-14②：`ResearchBridgeErrors.java:50` 所有 404 一律「研究專案不存在或已刪除」，allowlist 條目不存在時訊息誤導（reason `research_not_found` 本身正確）。
- **R-2** F-09 尾巴：Bridge 另有 `compile_failed`（503）、`sdd_cli_failed`（502）、`fsm_state_unreadable`（422）、`invalid_request`（422；console-api 區域常數）不在 22 個 reason 四方鎖與契約 §0.2 表內；console-api 對 502／503 轉通用上游失敗、422 逐字透傳；前端無文案退回伺服器訊息。
- **R-3** F-13b：`ResearchFlowHeader.test.tsx:123` 反向斷言正則含四區塊名，AT-960-20-4 字面掃描自我命中 1 筆。
- **R-4** F-11 尾巴：PKG-FIX-BR／FIX-API 無允許集合；集合外兩檔：`engine-bridge/tests/test_si_deploy_config.py`（FIX-BR 連動，主控授權）與 `backend/build.gradle.kts`（勘誤 commit）。

## D. 新發現（皆 P4）

- **N-01** D-80 兩端空白字元修剪定義不同：Bridge `evidence.py:528` 用 `strip().casefold()`，前端 `research.ts:1155-1156` 用 `trim()`＋`toLowerCase()`；U+FEFF 只有 JS 修剪、U+0085／U+001C／U+001F 只有 Python 修剪 ⇒ 18 個特殊輸入中 5 個兩端判相反；76 個寫實輸入 0 分歧，實務不可達。建議共用期望表加列或兩端同用顯式修剪集。
- **N-02** `StudioPanel.test.tsx` AT_960_16_1 兩案在機器滿載的首輪全套失敗（找不到 `prd-preview`／5000ms 逾時），單檔與重跑全套皆通過；預覽管線 `next/dynamic` 對時間敏感，建議等待就緒或加大 per-test timeout。

## E. 勘誤後條文 vs 實作抽查（皆一致）

TCS-P0 抽 8 列（reinit 只看 FAILED、capabilities 十三鍵、`prd_save_cursor`、`host_powershell`、哨兵雜湊只在劇本模式、離線夾具紀錄、兩列以突變驗證）；PRD 抽 5（核准檢查序、flow_status 優先序、徽章優先序與對比、600 秒、衍生相態八值）；API 契約抽 5（只比對送來的鍵、十三鍵與 sddRoot、對帳 id＋camelCase、prdVersion 整數、inScope 下界由 Bridge 驗）；ADR-003 5 列（第 5 列 Stack Exchange 官方頁事實為外部網頁，Web 工具禁用未驗）；ADR-XPLAT-017 2 列（Gate 0 檢查序、子行程環境剝除與 `enable_kernel_brain=false`）。

## F. 新碼突變（17 個，全 KILLED）

Bridge：N-1 FAILED 優先序改 IDLE、N-2 不剝 MINIMAX_、N-3 Brain 釘開、N-4 mock-only 不離線、N-5 矩陣重複計入、N-6 kind 不依檔、N-7 存稿不降級、N-8 reinit 前置放寬、N-9 去 host_powershell、N-10 fetch_hosts 清空、N-11 取消不 settle。前端：F-1 過期改比版號、F-2 去重連補抓、F-3 不隱藏節錨點。Java：J-1 對帳項取 name、J-2 scope 不轉 camelCase、J-3 零鍵閘放寬。

## G. 誠實劃界

- 突變只重跑一審存活者與新碼 17 個；第一批後三副本全樹 sha256 比對一致，第二批後未重驗（副本已丟棄）。
- Bridge 真樹只跑研究相關 36 檔＋sdd 三檔；前端與 backend 全套在副本跑。
- AT-960-23-3 部分獨立驗：test／ruff／tsc／eslint／prettier 已跑；JaCoCo 閘、vitest coverage、`npm run build`、`docker build` 沿用一審。
- 真棧 22-2（fail3）未獨立驗；Bridge volume 留有兩輪 spec 的工作區目錄（封存不刪檔）。
- RTM-P0 只核「待實作＝0」與四格無空白；V 系列人工或真機項（V-R2／V-R3／V-C1 部分、V-H1／V-H2）不在本判定內。

## H. 主控處置（2026-11-07）

- RTM-P0 的「二審待定」48 列依本報告改為「已實作·AT PASS（二審）」（AT-960-22-2 註記 [他包回報]、AT-960-23-3 註記部分獨立驗）；AT-960-24-1 與 AC-960-24 維持「部分」至 refreeze／RELEASE。
- R-1～R-4、N-01、N-02 登記為 P1 候選（不阻擋 RELEASE）。
- 一審遺留的 `D:\qa_r2a／b／c` 與 subst Q:／R:／S: 已由 QA 鏡自清；一審殘留的四個閒置 vitest 行程由主控結束。
