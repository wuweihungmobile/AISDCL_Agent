# RTM - 議題中心（Issue Center）根層半（議題聚合與中文對照表、`issues` 動詞、`export --kind issues`）

**版本**: 1.0（SCG-4 一審後回填；一審 FAIL〔P1＝0、P2＝9、P3＝3、P4＝1 組；P2 全屬「規格明文的邊界或值沒被斷言」「所列 AT 殺不到該條突變」「規格漏項」「越出 §5.7 的檔」，實作邏輯零修改〕；修復棒補斷言〔`tools/tests/test_selfimproving_issues.py`、`tools/tests/test_selfimproving_export_status.py`〕經二審 PASS（2026-10-27 12:58，P1 0／P2 0；報告 §E）。表格形沿用 `docs/06_quality/RTM-SelfImproving-P0-20261019.md`；Console 半見 `AgentConsole/docs/06_quality/RTM.md` §2.4）
**日期**: 2026-10-27（回填 13:00 +08:00）
**狀態**: 根層半實作與測試完成、實跑全綠；SCG-4 二審 PASS〔報告 §E〕；TCS 勘誤一、PRD 勘誤一已於 2026-10-27 refreeze（兩鍵 RELEASE_READY，digest 見「規格」欄）。AC 層結案 47／47（根層半；SCG-5 真機與 RELEASE 轉移見報告 §F／§H）。結論與逐項證據見 `docs/06_quality/SCG4-REVIEW-IssueCenter-20261027.md`。
**覆蓋率**: 根層半 AC 47／90（PRD 全部 90 條 AC 之中載具含 RI、RM、RX 或根層審查閘者；另 43 條只有 Console 半 AT，見 `AgentConsole/docs/06_quality/RTM.md` §2.4）；根層半 AT 116／116 有對應（115 個測試函式逐一 `ok`，另 1 個審查閘 AT 以 G-R14 為證）。
**規格**: `docs/03_testing/contracts/TCS-IssueCenter-20261027.md`（FSM 鍵 `monorepo-issue-center`／`agentconsole-issue-center` 的 `frozen_stages` 末筆＝2026-10-27 refreeze `sha256:9cd3286051ecda44c12187334954e944024135a275bb9393fdbd44d74850412d`，含〈勘誤一〉1-1～1-12；Stage-2 原值 `sha256:bc6a94934516fe5c88ad2317c54b0ed322c5f356459b38bb8de8e196578f6cba`）；上游 `docs/01_requirements/Issue_Center_PRD.md`（同次 refreeze `sha256:9765a825973f75722b79268dd827047a712a6db6a694f62f31e9fb90655a9eba`，含勘誤一 P-1～P-3；Stage-1 原值 `sha256:a162a104dc8217730fa42ed00cb7c071105943d4808bc7e5aa05efd5035408a7`）。TCS：R 條文 75、AT 223（根層 AT 116〔RI 104、RM 7、RX 4、GT 1〕＋Console 半 AT 107）、AC 90／90。
**實作**: `488d8e663b2ecbb2c27a5acaf895d67a92fbe426`（`7928b962..488d8e66`，96 檔；根層檔：`tools/lib/selfimproving/{issuemap,issues,issues_items}.py`、`defs.py`／`export.py` 修改、`tools/selfimproving.py` 的 `issues` 動詞與 `export --kind issues`、`tools/tests/test_selfimproving_{issues,issuemap}.py` 新增與 `test_selfimproving_export_status.py` 擴充、三支同步鎖測試、落點規範與兩支 compat-ci 的 `paths`）；一審後的修復棒改動只在 `tools/tests/` 兩支測試檔（加斷言、未加函式），與本檔同一 commit 入庫（行區間以該 commit 為準）。

> 「本次結果」一律是 2026-10-27 當回合真跑的輸出（Windows 11；Python 3.11.9；unittest）。三檔整檔各跑一次（`python -B -m unittest discover -s tools/tests -p "<檔>" -v`，在 repo 根，rc 皆 0）：
>
> - `test_selfimproving_issues.py`：`Ran 104 tests in 29.849s`、`OK`
> - `test_selfimproving_issuemap.py`：`Ran 7 tests in 0.008s`、`OK`
> - `test_selfimproving_export_status.py`：`Ran 15 tests in 19.677s`、`OK`（其中 4 個是本功能 RX 的 AT，另 11 個是既有測試）
>
> 逐 AT 單跑抽樣（同日，各 rc 0）：`-k AT_IC_01_2_E_1_`（issues 檔）、`-k AT_IC_06_2_1_`（export_status 檔，含雜湊種子子行程差分）、`-k AT_IC_01_1_E_2_`（issuemap 檔）各 `Ran 1 test`、`OK`。
>
> 逐 AT 對照：用 `-v` 輸出逐一核對，115 個 AT 測試函式各為 `ok`（無 skip、無 expected failure、無 error）。每個 AT 的單跑判定指令＝TCS §2 的樣板：`python -m unittest discover -s tools/tests -p "<檔>" -k <AT 底線形>_`（例：AT-IC-01-2-1 的 `-k` 為 `AT_IC_01_2_1_`；E 類為 `AT_IC_01_2_E_1_`）。測試檔座標（行區間）以**工作樹現況**為準（實作 commit `488d8e66` 之後，修復棒在兩支測試檔補了斷言，行區間位移）；測試檔一變動行區間即過期，須重抽。「TCS 行」為該 AT 列在 TCS 工作樹檔內的行號（工作樹的 TCS 與 HEAD 的差異只有檔頭 digest 字樣一行與檔尾追加的〈勘誤一〉，223 個 AT 列行號逐一相同，本回合以 `git show HEAD:` 對拍）。macOS／POSIX 與 GitHub Actions 端未驗。

## 1. FR → AC 追溯（根層半 47 個 AC）

AC 編號 PRD 與 TCS 相同（`AC-IC-<FR>-<n>`）；「R 條文」取自 TCS R 條文表的 AT 欄反查；使用者故事 `US-IC-NN` 一 FR 一則（TCS FRD-lite）：US-IC-01＝看到的狀態、結果、來源、嚴重度全是中文，對不上時明說「未歸類」；US-IC-02＝每個議題標明是誰提的（使用者、系統缺陷、研究、改善）；US-IC-03＝只有「已成立」的項目才成為待辦，候選不吵我；US-IC-04＝每列都有下一步一句話、關聯與可展開的原列與時間線；US-IC-05＝最重要、最久沒動的排前面，可分頁、可篩、數字是整本帳；US-IC-06＝議題中心不動帳本、兩個出口一致、不存第二份詞彙；US-IC-12＝快、跨平台、不快取、既有功能不壞、鍵盤可用。

| FR | AC | User Story | R 條文 | PRD 座標 | 對應 AT（根層半） | AT 本次結果 | AC 層結論 |
|----|----|-----------|--------|----------|------------------|------------|----------|
| FR-IC-01 | AC-IC-01-1 | US-IC-01 | R-IC-01、R-IC-02、R-IC-03、R-IC-04 | PRD:281 | AT-IC-01-1-1、AT-IC-01-1-2、AT-IC-01-1-E-1、AT-IC-01-1-E-2（4） | 4/4 通過 | 根層 AT 實跑全綠（4/4） |
| FR-IC-01 | AC-IC-01-2 | US-IC-01 | R-IC-06、R-IC-07、R-IC-20、R-IC-21 | PRD:282 | AT-IC-01-2-1、AT-IC-01-2-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-01 | AC-IC-01-3 | US-IC-01 | R-IC-02、R-IC-06、R-IC-19、R-IC-21 | PRD:283 | AT-IC-01-3-1、AT-IC-01-3-2、AT-IC-01-3-E-1（3） | 3/3 通過 | 根層 AT 實跑全綠（3/3） |
| FR-IC-01 | AC-IC-01-4 | US-IC-01 | R-IC-05、R-IC-06、R-IC-09、R-IC-25 | PRD:284 | AT-IC-01-4-1、AT-IC-01-4-2、AT-IC-01-4-3、AT-IC-01-4-E-1、AT-IC-01-4-E-2（5） | 5/5 通過 | 根層 AT 實跑全綠（5/5） |
| FR-IC-01 | AC-IC-01-5 | US-IC-01 | R-IC-01、R-IC-37 | PRD:285 | AT-IC-01-5-1、AT-IC-01-5-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-01 | AC-IC-01-6 | US-IC-01 | R-IC-07、R-IC-36 | PRD:286 | AT-IC-01-6-1、AT-IC-01-6-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-01 | AC-IC-01-7 | US-IC-01 | R-IC-01、R-IC-03、R-IC-08、R-IC-41 | PRD:287 | AT-IC-01-7-1、AT-IC-01-7-2、AT-IC-01-7-E-1（3） | 3/3 通過 | 根層 AT 實跑全綠（3/3） |
| FR-IC-01 | AC-IC-01-8 | US-IC-01 | R-IC-10、R-IC-36、R-IC-41 | PRD:288 | AT-IC-01-8-1、AT-IC-01-8-2、AT-IC-01-8-3、AT-IC-01-8-4、AT-IC-01-8-E-1、AT-IC-01-8-E-2（6） | 6/6 通過 | 根層 AT 實跑全綠（6/6） |
| FR-IC-01 | AC-IC-01-9 | US-IC-01 | R-IC-12 | PRD:289 | AT-IC-01-9-1、AT-IC-01-9-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-01 | AC-IC-01-10 | US-IC-01 | R-IC-06 | PRD:290 | AT-IC-01-10-1、AT-IC-01-10-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-01 | AC-IC-01-11 | US-IC-01 | R-IC-11 | PRD:291 | AT-IC-01-11-1、AT-IC-01-11-2、AT-IC-01-11-E-1（3） | 3/3 通過 | 根層 AT 實跑全綠（3/3） |
| FR-IC-02 | AC-IC-02-1 | US-IC-02 | R-IC-16 | PRD:293 | AT-IC-02-1-1、AT-IC-02-1-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-02 | AC-IC-02-2 | US-IC-02 | R-IC-16 | PRD:294 | AT-IC-02-2-1、AT-IC-02-2-E-1、AT-IC-02-2-E-2（3） | 3/3 通過 | 根層 AT 實跑全綠（3/3） |
| FR-IC-02 | AC-IC-02-3 | US-IC-02 | R-IC-16 | PRD:295 | AT-IC-02-3-1、AT-IC-02-3-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-02 | AC-IC-02-4 | US-IC-02 | R-IC-16 | PRD:296 | AT-IC-02-4-1、AT-IC-02-4-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-02 | AC-IC-02-5 | US-IC-02 | R-IC-16 | PRD:297 | AT-IC-02-5-1、AT-IC-02-5-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-03 | AC-IC-03-1 | US-IC-03 | R-IC-17 | PRD:299 | AT-IC-03-1-1、AT-IC-03-1-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-03 | AC-IC-03-2 | US-IC-03 | R-IC-17 | PRD:300 | AT-IC-03-2-1、AT-IC-03-2-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-03 | AC-IC-03-3 | US-IC-03 | R-IC-17、R-IC-28 | PRD:301 | AT-IC-03-3-1、AT-IC-03-3-2、AT-IC-03-3-E-1（3） | 3/3 通過 | 根層 AT 實跑全綠（3/3） |
| FR-IC-03 | AC-IC-03-4 | US-IC-03 | R-IC-17、R-IC-20 | PRD:302 | AT-IC-03-4-1、AT-IC-03-4-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-03 | AC-IC-03-5 | US-IC-03 | R-IC-43 | PRD:303 | AT-IC-03-5-1、AT-IC-03-5-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-03 | AC-IC-03-6 | US-IC-03 | R-IC-18 | PRD:304 | AT-IC-03-6-1、AT-IC-03-6-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-03 | AC-IC-03-7 | US-IC-03 | R-IC-19 | PRD:305 | AT-IC-03-7-1、AT-IC-03-7-2、AT-IC-03-7-E-1（3） | 3/3 通過 | 根層 AT 實跑全綠（3/3） |
| FR-IC-04 | AC-IC-04-1 | US-IC-04 | R-IC-31 | PRD:307 | AT-IC-04-1-1、AT-IC-04-1-E-1、AT-IC-04-1-E-2（3） | 3/3 通過 | 根層 AT 實跑全綠（3/3）；Q-04 補斷言（二審 PASS 2026-10-27，報告 §E；QA 重放對應突變 KILLED） |
| FR-IC-04 | AC-IC-04-2 | US-IC-04 | R-IC-09、R-IC-32 | PRD:308 | AT-IC-04-2-1、AT-IC-04-2-E-1、AT-IC-04-2-E-2（3） | 3/3 通過 | 根層 AT 實跑全綠（3/3） |
| FR-IC-04 | AC-IC-04-3 | US-IC-04 | R-IC-09、R-IC-23、R-IC-24 | PRD:309 | AT-IC-04-3-1、AT-IC-04-3-2、AT-IC-04-3-E-1（3） | 3/3 通過 | 根層 AT 實跑全綠（3/3）；Q-03 補斷言（二審 PASS 2026-10-27，報告 §E；QA 重放對應突變 KILLED） |
| FR-IC-04 | AC-IC-04-4 | US-IC-04 | R-IC-27 | PRD:310 | AT-IC-04-4-1、AT-IC-04-4-2、AT-IC-04-4-E-1（3） | 3/3 通過 | 根層 AT 實跑全綠（3/3） |
| FR-IC-04 | AC-IC-04-5 | US-IC-04 | R-IC-15、R-IC-21、R-IC-25 | PRD:311 | AT-IC-04-5-1、AT-IC-04-5-E-1、AT-IC-04-5-E-2（3） | 3/3 通過 | 根層 AT 實跑全綠（3/3） |
| FR-IC-04 | AC-IC-04-6 | US-IC-04 | R-IC-22、R-IC-29、R-IC-30、R-IC-37、R-IC-40 | PRD:312 | AT-IC-04-6-1、AT-IC-04-6-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2）；Q-10 補斷言（二審 PASS 2026-10-27，報告 §E；QA 重放對應突變 KILLED） |
| FR-IC-04 | AC-IC-04-7 | US-IC-04 | R-IC-09、R-IC-23、R-IC-29 | PRD:313 | AT-IC-04-7-1、AT-IC-04-7-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2）；Q-08 補斷言（二審 PASS 2026-10-27，報告 §E；QA 重放對應突變 KILLED） |
| FR-IC-04 | AC-IC-04-8 | US-IC-04 | R-IC-26 | PRD:314 | AT-IC-04-8-1、AT-IC-04-8-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-04 | AC-IC-04-9 | US-IC-04 | R-IC-13、R-IC-14 | PRD:315 | AT-IC-04-9-1、AT-IC-04-9-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-04 | AC-IC-04-10 | US-IC-04 | R-IC-06、R-IC-18、R-IC-20、R-IC-28 | PRD:316 | AT-IC-04-10-1、AT-IC-04-10-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2）；Q-08 補斷言（二審 PASS 2026-10-27，報告 §E；QA 重放對應突變 KILLED） |
| FR-IC-04 | AC-IC-04-11 | US-IC-04 | R-IC-30 | PRD:317 | AT-IC-04-11-1、AT-IC-04-11-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-05 | AC-IC-05-1 | US-IC-05 | R-IC-22、R-IC-33、R-IC-34、R-IC-60 | PRD:319 | AT-IC-05-1-1、AT-IC-05-1-E-1（2）；Console 半另有 AT-IC-05-1-2、AT-IC-05-1-E-2（見 `AgentConsole/docs/06_quality/RTM.md` §2.4） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-05 | AC-IC-05-2 | US-IC-05 | R-IC-35、R-IC-39 | PRD:320 | AT-IC-05-2-1、AT-IC-05-2-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2）；Q-02 補斷言（二審 PASS 2026-10-27，報告 §E；QA 重放對應突變 KILLED） |
| FR-IC-05 | AC-IC-05-3 | US-IC-05 | R-IC-35 | PRD:321 | AT-IC-05-3-1、AT-IC-05-3-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2）；Q-01 補斷言（二審 PASS 2026-10-27，報告 §E；QA 重放對應突變 KILLED） |
| FR-IC-05 | AC-IC-05-4 | US-IC-05 | R-IC-39、R-IC-40 | PRD:322 | AT-IC-05-4-1、AT-IC-05-4-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2）；Q-10 補斷言（二審 PASS 2026-10-27，報告 §E；QA 重放對應突變 KILLED） |
| FR-IC-05 | AC-IC-05-5 | US-IC-05 | R-IC-14、R-IC-36 | PRD:323 | AT-IC-05-5-1、AT-IC-05-5-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-05 | AC-IC-05-6 | US-IC-05 | R-IC-34、R-IC-38 | PRD:324 | AT-IC-05-6-1、AT-IC-05-6-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2）；Q-07 補斷言（二審 PASS 2026-10-27，報告 §E；QA 重放對應突變 KILLED） |
| FR-IC-06 | AC-IC-06-1 | US-IC-06 | R-IC-43、R-IC-45 | PRD:327 | AT-IC-06-1-1、AT-IC-06-1-E-1（2）；Console 半另有 AT-IC-06-1-2、AT-IC-06-1-3（見 `AgentConsole/docs/06_quality/RTM.md` §2.4） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-06 | AC-IC-06-2 | US-IC-06 | R-IC-01、R-IC-38、R-IC-40、R-IC-42、R-IC-64、R-IC-73 | PRD:328 | AT-IC-06-2-1、AT-IC-06-2-2、AT-IC-06-2-E-1（3）；Console 半另有 AT-IC-06-2-3、AT-IC-06-2-4、AT-IC-06-2-E-2、AT-IC-06-2-E-3（見 `AgentConsole/docs/06_quality/RTM.md` §2.4） | 3/3 通過 | 根層 AT 實跑全綠（3/3）；Q-08 補斷言（二審 PASS 2026-10-27，報告 §E；QA 重放對應突變 KILLED） |
| FR-IC-06 | AC-IC-06-3 | US-IC-06 | R-IC-43 | PRD:329 | AT-IC-06-3-1、AT-IC-06-3-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-06 | AC-IC-06-4 | US-IC-06 | R-IC-43 | PRD:330 | AT-IC-06-4-1、AT-IC-06-4-E-1（2） | 1/1 通過；審查閘 AT-IC-06-4-E-1 見 §3 | 根層 AT 實跑全綠（1/1）；審查閘 G-R14 本回合重跑 rc 0（§3） |
| FR-IC-06 | AC-IC-06-5 | US-IC-06 | R-IC-13 | PRD:331 | AT-IC-06-5-1、AT-IC-06-5-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |
| FR-IC-12 | AC-IC-12-1 | US-IC-12 | R-IC-44 | PRD:377 | AT-IC-12-1-1、AT-IC-12-1-2、AT-IC-12-1-E-1（3） | 3/3 通過 | 根層 AT 實跑全綠（3/3） |
| FR-IC-12 | AC-IC-12-2 | US-IC-12 | R-IC-44 | PRD:378 | AT-IC-12-2-1、AT-IC-12-2-E-1（2） | 2/2 通過 | 根層 AT 實跑全綠（2/2） |

## 2. AC → AT → 測試方法 → 本次結果 → 證據座標（根層半 116 個 AT）

測試檔都在 `tools/tests/`；「測試方法」寫 `檔::類別::函式`（`:起–訖` 為工作樹行區間）。「證據座標」只寫與 SCG-4 報告 §B 的對照（一審 FAIL 的 P2、P3 之中落在該 AT 的補斷言）；「—」＝報告未對該 AT 提出發現。

### FR-IC-01　對照表封閉、唯一歸類、fail-loud

| AC | AT | 載具 | TCS 行 | 測試方法 | 本次結果 | 證據座標 |
|----|----|------|--------|----------|----------|----------|
| 01-1 | AT-IC-01-1-1 | RM | TCS:716 | `test_selfimproving_issuemap.py::TestIssueMapClosure::test_AT_IC_01_1_1_every_machine_value_has_exactly_one_classification`（`:41–70`） | 通過（`Ran 7 tests`，`OK`） | — |
| 01-1 | AT-IC-01-1-2 | RM | TCS:717 | `test_selfimproving_issuemap.py::TestIssueMapClosure::test_AT_IC_01_1_2_disposition_probes_and_pattern_branch_count`（`:72–85`） | 通過（`Ran 7 tests`，`OK`） | — |
| 01-1 | AT-IC-01-1-E-1 | RM | TCS:718 | `test_selfimproving_issuemap.py::TestIssueMapClosure::test_AT_IC_01_1_E_1_upstream_additions_are_reported_by_name`（`:87–104`） | 通過（`Ran 7 tests`，`OK`） | — |
| 01-1 | AT-IC-01-1-E-2 | RM | TCS:719 | `test_selfimproving_issuemap.py::TestIssueMapClosure::test_AT_IC_01_1_E_2_table_deletions_and_additions_are_reported_both_ways`（`:106–116`） | 通過（`Ran 7 tests`，`OK`） | — |
| 01-2 | AT-IC-01-2-1 | RI | TCS:720 | `test_selfimproving_issues.py::TestFailLoud::test_AT_IC_01_2_1_unmapped_values_fail_loud`（`:282–299`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-2 | AT-IC-01-2-E-1 | RI | TCS:721 | `test_selfimproving_issues.py::TestFailLoud::test_AT_IC_01_2_E_1_legit_issues_are_not_dragged_along`（`:301–312`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-3 | AT-IC-01-3-1 | RI | TCS:722 | `test_selfimproving_issues.py::TestFailLoud::test_AT_IC_01_3_1_terminal_states_map_to_the_eight_results`（`:314–333`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-3 | AT-IC-01-3-2 | RI | TCS:723 | `test_selfimproving_issues.py::TestFailLoud::test_AT_IC_01_3_2_non_final_states_have_no_result`（`:335–343`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-3 | AT-IC-01-3-E-1 | RI | TCS:724 | `test_selfimproving_issues.py::TestFailLoud::test_AT_IC_01_3_E_1_closed_without_a_measurable_window_is_unmapped`（`:345–361`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-4 | AT-IC-01-4-1 | RM | TCS:725 | `test_selfimproving_issuemap.py::TestIssueMapDictionaries::test_AT_IC_01_4_1_severity_mapping_for_both_groups`（`:122–142`） | 通過（`Ran 7 tests`，`OK`） | — |
| 01-4 | AT-IC-01-4-2 | RM | TCS:726 | `test_selfimproving_issuemap.py::TestIssueMapDictionaries::test_AT_IC_01_4_2_real_defect_ledger_first_codes_are_inside_the_constant`（`:144–150`） | 通過（`Ran 7 tests`，`OK`） | — |
| 01-4 | AT-IC-01-4-3 | RI | TCS:727 | `test_selfimproving_issues.py::TestSeverityLegendLedgers::test_AT_IC_01_4_3_a_proposal_takes_its_most_severe_source`（`:437–446`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-4 | AT-IC-01-4-E-1 | RI | TCS:728 | `test_selfimproving_issues.py::TestSeverityLegendLedgers::test_AT_IC_01_4_E_1_defect_severity_outside_the_constant_is_unmapped`（`:448–456`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-4 | AT-IC-01-4-E-2 | RI | TCS:729 | `test_selfimproving_issues.py::TestSeverityLegendLedgers::test_AT_IC_01_4_E_2_unknown_severity_shows_a_dash_not_low`（`:458–464`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-5 | AT-IC-01-5-1 | RI | TCS:730 | `test_selfimproving_issues.py::TestSeverityLegendLedgers::test_AT_IC_01_5_1_legend_content_counts_and_order`（`:466–493`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-5 | AT-IC-01-5-E-1 | RX | TCS:731 | `test_selfimproving_export_status.py::TestIssuesExport::test_AT_IC_01_5_E_1_a_single_entry_has_no_legend_or_summary`（`:813–821`） | 通過（`Ran 15 tests`，`OK`） | — |
| 01-6 | AT-IC-01-6-1 | RI | TCS:732 | `test_selfimproving_issues.py::TestFailLoud::test_AT_IC_01_6_1_each_unmapped_value_is_its_own_problem`（`:363–371`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-6 | AT-IC-01-6-E-1 | RI | TCS:733 | `test_selfimproving_issues.py::TestFailLoud::test_AT_IC_01_6_E_1_summary_counts_the_unmapped_apart`（`:373–382`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-7 | AT-IC-01-7-1 | RI | TCS:734 | `test_selfimproving_issues.py::TestSeverityLegendLedgers::test_AT_IC_01_7_1_every_code_and_reason_is_in_the_table_and_vice_versa`（`:495–528`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-7 | AT-IC-01-7-2 | RM | TCS:735 | `test_selfimproving_issuemap.py::TestIssueMapDictionaries::test_AT_IC_01_7_2_channel_event_and_decision_dictionaries`（`:152–169`） | 通過（`Ran 7 tests`，`OK`） | — |
| 01-7 | AT-IC-01-7-E-1 | RI | TCS:736 | `test_selfimproving_issues.py::TestSeverityLegendLedgers::test_AT_IC_01_7_E_1_the_closure_self_proof_has_teeth_in_both_directions`（`:530–538`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-8 | AT-IC-01-8-1 | RI | TCS:737 | `test_selfimproving_issues.py::TestSeverityLegendLedgers::test_AT_IC_01_8_1_missing_observation_ledger`（`:540–551`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-8 | AT-IC-01-8-2 | RI | TCS:738 | `test_selfimproving_issues.py::TestSeverityLegendLedgers::test_AT_IC_01_8_2_missing_defect_ledger`（`:553–560`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-8 | AT-IC-01-8-3 | RI | TCS:739 | `test_selfimproving_issues.py::TestSeverityLegendLedgers::test_AT_IC_01_8_3_missing_sibling_ledger`（`:562–569`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-8 | AT-IC-01-8-4 | RI | TCS:740 | `test_selfimproving_issues.py::TestSeverityLegendLedgers::test_AT_IC_01_8_4_missing_event_ledger`（`:571–577`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-8 | AT-IC-01-8-E-1 | RI | TCS:741 | `test_selfimproving_issues.py::TestSeverityLegendLedgers::test_AT_IC_01_8_E_1_unreadable_ledgers_report_exactly_their_own_reason`（`:579–601`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-8 | AT-IC-01-8-E-2 | RI | TCS:742 | `test_selfimproving_issues.py::TestSeverityLegendLedgers::test_AT_IC_01_8_E_2_ledgers_without_a_proper_header_are_unavailable_not_empty`（`:603–614`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-9 | AT-IC-01-9-1 | RI | TCS:743 | `test_selfimproving_issues.py::TestEventLedgerAndLinkage::test_AT_IC_01_9_1_unparseable_and_unsound_lines_are_reported_by_line`（`:646–656`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-9 | AT-IC-01-9-E-1 | RI | TCS:744 | `test_selfimproving_issues.py::TestEventLedgerAndLinkage::test_AT_IC_01_9_E_1_unsound_events_never_reach_the_fold`（`:658–668`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-10 | AT-IC-01-10-1 | RI | TCS:745 | `test_selfimproving_issues.py::TestFailLoud::test_AT_IC_01_10_1_long_unmapped_values_are_cut_for_display_only`（`:384–390`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-10 | AT-IC-01-10-E-1 | RI | TCS:746 | `test_selfimproving_issues.py::TestFailLoud::test_AT_IC_01_10_E_1_the_limit_counts_code_points_not_units_or_graphemes`（`:392–404`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-11 | AT-IC-01-11-1 | RI | TCS:747 | `test_selfimproving_issues.py::TestEventLedgerAndLinkage::test_AT_IC_01_11_1_missing_observation_ledger_blanks_the_proposal_source`（`:670–678`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-11 | AT-IC-01-11-2 | RI | TCS:748 | `test_selfimproving_issues.py::TestEventLedgerAndLinkage::test_AT_IC_01_11_2_missing_event_ledger_keeps_unconfirmed_rows_as_candidates`（`:680–684`） | 通過（`Ran 104 tests`，`OK`） | — |
| 01-11 | AT-IC-01-11-E-1 | RI | TCS:749 | `test_selfimproving_issues.py::TestEventLedgerAndLinkage::test_AT_IC_01_11_E_1_unaffected_rows_are_judged_as_usual`（`:686–693`） | 通過（`Ran 104 tests`，`OK`） | — |

### FR-IC-02　來源判定

| AC | AT | 載具 | TCS 行 | 測試方法 | 本次結果 | 證據座標 |
|----|----|------|--------|----------|----------|----------|
| 02-1 | AT-IC-02-1-1 | RI | TCS:755 | `test_selfimproving_issues.py::TestSourceJudgement::test_AT_IC_02_1_1_user_marks_win_over_everything`（`:705–708`） | 通過（`Ran 104 tests`，`OK`） | — |
| 02-1 | AT-IC-02-1-E-1 | RI | TCS:756 | `test_selfimproving_issues.py::TestSourceJudgement::test_AT_IC_02_1_E_1_agent_marks_alone_are_not_the_user`（`:710–711`） | 通過（`Ran 104 tests`，`OK`） | — |
| 02-2 | AT-IC-02-2-1 | RI | TCS:757 | `test_selfimproving_issues.py::TestSourceJudgement::test_AT_IC_02_2_1_researcher_reports_are_research_proposals`（`:713–714`） | 通過（`Ran 104 tests`，`OK`） | — |
| 02-2 | AT-IC-02-2-E-1 | RI | TCS:758 | `test_selfimproving_issues.py::TestSourceJudgement::test_AT_IC_02_2_E_1_a_researcher_bug_is_still_a_system_defect`（`:716–717`） | 通過（`Ran 104 tests`，`OK`） | — |
| 02-2 | AT-IC-02-2-E-2 | RI | TCS:759 | `test_selfimproving_issues.py::TestSourceJudgement::test_AT_IC_02_2_E_2_the_researcher_test_is_equality_not_substring`（`:719–721`） | 通過（`Ran 104 tests`，`OK`） | — |
| 02-3 | AT-IC-02-3-1 | RI | TCS:760 | `test_selfimproving_issues.py::TestSourceJudgement::test_AT_IC_02_3_1_defect_rows_and_bug_observations_are_system_defects`（`:723–728`） | 通過（`Ran 104 tests`，`OK`） | — |
| 02-3 | AT-IC-02-3-E-1 | RI | TCS:761 | `test_selfimproving_issues.py::TestSourceJudgement::test_AT_IC_02_3_E_1_a_tooling_observation_is_not_a_defect`（`:730–731`） | 通過（`Ran 104 tests`，`OK`） | — |
| 02-4 | AT-IC-02-4-1 | RI | TCS:762 | `test_selfimproving_issues.py::TestSourceJudgement::test_AT_IC_02_4_1_improvement_categories_are_system_improvements`（`:733–736`） | 通過（`Ran 104 tests`，`OK`） | — |
| 02-4 | AT-IC-02-4-E-1 | RI | TCS:763 | `test_selfimproving_issues.py::TestSourceJudgement::test_AT_IC_02_4_E_1_a_bug_is_not_an_improvement`（`:738–739`） | 通過（`Ran 104 tests`，`OK`） | — |
| 02-5 | AT-IC-02-5-1 | RI | TCS:764 | `test_selfimproving_issues.py::TestSourceJudgement::test_AT_IC_02_5_1_a_proposal_takes_the_first_ranked_source`（`:741–747`） | 通過（`Ran 104 tests`，`OK`） | — |
| 02-5 | AT-IC-02-5-E-1 | RI | TCS:765 | `test_selfimproving_issues.py::TestSourceJudgement::test_AT_IC_02_5_E_1_unknown_sources_are_skipped_or_reported_by_id`（`:749–758`） | 通過（`Ran 104 tests`，`OK`） | — |

### FR-IC-03　成為正式議題

| AC | AT | 載具 | TCS 行 | 測試方法 | 本次結果 | 證據座標 |
|----|----|------|--------|----------|----------|----------|
| 03-1 | AT-IC-03-1-1 | RI | TCS:771 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_1_1_an_unsupported_open_row_stays_a_candidate`（`:768–773`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-1 | AT-IC-03-1-E-1 | RI | TCS:772 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_1_E_1_candidates_are_outside_every_tab`（`:775–778`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-2 | AT-IC-03-2-1 | RI | TCS:773 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_2_1_a_confirmed_attr_makes_the_row_established`（`:780–784`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-2 | AT-IC-03-2-E-1 | RI | TCS:774 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_2_E_1_unconfirmed_or_rejected_attrs_do_not_count`（`:786–790`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-3 | AT-IC-03-3-1 | RI | TCS:775 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_3_1_a_user_mark_is_enough_without_any_attr`（`:792–796`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-3 | AT-IC-03-3-2 | RI | TCS:776 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_3_2_decision_rows_go_to_the_decision_tab_on_either_path`（`:798–804`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-3 | AT-IC-03-3-E-1 | RI | TCS:777 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_3_E_1_looking_like_an_improvement_does_not_establish_a_row`（`:806–808`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-4 | AT-IC-03-4-1 | RI | TCS:778 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_4_1_final_and_deferred_rows_are_never_candidates`（`:810–819`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-4 | AT-IC-03-4-E-1 | RI | TCS:779 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_4_E_1_an_established_deferred_row_stays_deferred`（`:821–825`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-5 | AT-IC-03-5-1 | RI | TCS:780 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_5_1_unbooked_console_audit_files_are_not_issues`（`:827–841`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-5 | AT-IC-03-5-E-1 | RI | TCS:781 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_5_E_1_the_row_becomes_an_issue_only_once_it_is_booked`（`:843–850`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-6 | AT-IC-03-6-1 | RI | TCS:782 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_6_1_established_improvements_go_to_pending_not_to_decision`（`:852–861`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-6 | AT-IC-03-6-E-1 | RI | TCS:783 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_6_E_1_the_decision_tab_has_exactly_four_kinds_of_members`（`:871–879`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-7 | AT-IC-03-7-1 | RI | TCS:784 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_7_1_closed_proposals_follow_the_rollback_ledger`（`:881–899`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-7 | AT-IC-03-7-2 | RI | TCS:785 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_7_2_the_decision_members_match_meaplan_rollback_pending`（`:908–919`） | 通過（`Ran 104 tests`，`OK`） | — |
| 03-7 | AT-IC-03-7-E-1 | RI | TCS:786 | `test_selfimproving_issues.py::TestFormalIssues::test_AT_IC_03_7_E_1_a_rollback_decided_before_the_promotion_is_not_counted`（`:921–931`） | 通過（`Ran 104 tests`，`OK`） | — |

### FR-IC-04　下一步與欄位

| AC | AT | 載具 | TCS 行 | 測試方法 | 本次結果 | 證據座標 |
|----|----|------|--------|----------|----------|----------|
| 04-1 | AT-IC-04-1-1 | RI | TCS:792 | `test_selfimproving_issues.py::TestNextStepAndFields::test_AT_IC_04_1_1_every_scenario_has_exactly_its_sentence`（`:1006–1025`） | 通過（`Ran 104 tests`，`OK`） | 一審 Q-04（P2）：姊妹軌解鎖條件截 40 字漏載、無 AT；修復棒補 ≥41 code point 夾具（TCS 勘誤 1-10、1-11） |
| 04-1 | AT-IC-04-1-E-1 | RI | TCS:793 | `test_selfimproving_issues.py::TestNextStepAndFields::test_AT_IC_04_1_E_1_the_english_word_detector_has_teeth`（`:1027–1032`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-1 | AT-IC-04-1-E-2 | RI | TCS:794 | `test_selfimproving_issues.py::TestNextStepAndFields::test_AT_IC_04_1_E_2_deferred_excerpts_are_cut_at_forty_and_may_be_empty`（`:1034–1044`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-2 | AT-IC-04-2-1 | RI | TCS:795 | `test_selfimproving_issues.py::TestNextStepAndFields::test_AT_IC_04_2_1_a_measuring_proposal_shows_the_window_progress`（`:1046–1056`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-2 | AT-IC-04-2-E-1 | RI | TCS:796 | `test_selfimproving_issues.py::TestNextStepAndFields::test_AT_IC_04_2_E_1_unmeasurable_progress_is_a_dash_with_a_note`（`:1058–1067`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-2 | AT-IC-04-2-E-2 | RI | TCS:797 | `test_selfimproving_issues.py::TestNextStepAndFields::test_AT_IC_04_2_E_2_the_aggregator_never_calls_the_window_row_helper`（`:1069–1079`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-3 | AT-IC-04-3-1 | RI | TCS:798 | `test_selfimproving_issues.py::TestNextStepAndFields::test_AT_IC_04_3_1_titles_lose_markup_and_are_cut_at_eighty_code_points`（`:1081–1105`） | 通過（`Ran 104 tests`，`OK`） | 一審 Q-03（P2）：恰 80 code point 不加「…」無斷言；修復棒補恰 80、81 兩例 |
| 04-3 | AT-IC-04-3-2 | RI | TCS:799 | `test_selfimproving_issues.py::TestNextStepAndFields::test_AT_IC_04_3_2_updated_at_takes_the_date_part_of_the_last_known_sign`（`:1107–1119`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-3 | AT-IC-04-3-E-1 | RI | TCS:800 | `test_selfimproving_issues.py::TestNextStepAndFields::test_AT_IC_04_3_E_1_unparseable_times_are_null_and_an_early_close_never_wins`（`:1121–1128`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-4 | AT-IC-04-4-1 | RI | TCS:801 | `test_selfimproving_issues.py::TestLinksOriginAndRows::test_AT_IC_04_4_1_two_way_links_list_each_other_sorted_and_deduplicated`（`:1180–1191`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-4 | AT-IC-04-4-2 | RI | TCS:802 | `test_selfimproving_issues.py::TestLinksOriginAndRows::test_AT_IC_04_4_2_one_way_links_only_list_the_target_from_the_origin`（`:1193–1201`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-4 | AT-IC-04-4-E-1 | RI | TCS:803 | `test_selfimproving_issues.py::TestLinksOriginAndRows::test_AT_IC_04_4_E_1_links_may_point_outside_and_two_way_ones_are_symmetric`（`:1203–1212`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-5 | AT-IC-04-5-1 | RI | TCS:804 | `test_selfimproving_issues.py::TestLinksOriginAndRows::test_AT_IC_04_5_1_deferred_rows_say_what_would_bring_them_back`（`:1214–1223`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-5 | AT-IC-04-5-E-1 | RI | TCS:805 | `test_selfimproving_issues.py::TestLinksOriginAndRows::test_AT_IC_04_5_E_1_a_sibling_row_without_a_main_row_is_an_orphan_issue`（`:1225–1234`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-5 | AT-IC-04-5-E-2 | RI | TCS:806 | `test_selfimproving_issues.py::TestLinksOriginAndRows::test_AT_IC_04_5_E_2_sibling_rows_with_the_wrong_arity_or_duplicates_are_reported`（`:1236–1245`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-6 | AT-IC-04-6-1 | RX | TCS:807 | `test_selfimproving_export_status.py::TestIssuesExport::test_AT_IC_04_6_1_a_single_entry_carries_raw_and_a_chinese_timeline`（`:823–852`） | 通過（`Ran 15 tests`，`OK`） | 一審 Q-10（P3）：補單筆回應形狀絕對釘（頂層鍵序、schema_rev、kind、generated_at 帶 offset、raw 與 timeline 鍵序） |
| 04-6 | AT-IC-04-6-E-1 | RX | TCS:808 | `test_selfimproving_export_status.py::TestIssuesExport::test_AT_IC_04_6_E_1_the_list_is_lean_and_an_unknown_id_is_an_empty_success`（`:854–883`） | 通過（`Ran 15 tests`，`OK`） | 一審 Q-10（P3）：補清單回應形狀絕對釘，含 ne、problems 條目鍵序 |
| 04-7 | AT-IC-04-7-1 | RI | TCS:809 | `test_selfimproving_issues.py::TestLinksOriginAndRows::test_AT_IC_04_7_1_the_title_is_the_card_symptom_or_says_it_cannot_be_built`（`:1251–1271`） | 通過（`Ran 104 tests`，`OK`） | 一審 Q-08（P2）：R-IC-29「raw 截斷」所列 AT 殺不到（實際殺手為 04-3-1）；修復棒補單筆 raw 的提案卡全文逐字斷言（TCS 勘誤 1-12） |
| 04-7 | AT-IC-04-7-E-1 | RI | TCS:810 | `test_selfimproving_issues.py::TestLinksOriginAndRows::test_AT_IC_04_7_E_1_an_unbuildable_card_affects_nothing_else`（`:1273–1300`） | 通過（`Ran 104 tests`，`OK`） | 一審 Q-08（P2）：R-IC-29「raw 截斷」所列 AT 殺不到；修復棒補 raw 其餘各項（摘要碼、來源項目等）值逐字斷言（TCS 勘誤 1-12） |
| 04-8 | AT-IC-04-8-1 | RI | TCS:811 | `test_selfimproving_issues.py::TestLinksOriginAndRows::test_AT_IC_04_8_1_origin_points_at_the_row_the_issue_came_from`（`:1302–1317`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-8 | AT-IC-04-8-E-1 | RI | TCS:812 | `test_selfimproving_issues.py::TestLinksOriginAndRows::test_AT_IC_04_8_E_1_windows_line_endings_and_bom_change_nothing`（`:1319–1333`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-9 | AT-IC-04-9-1 | RI | TCS:813 | `test_selfimproving_issues.py::TestLinksOriginAndRows::test_AT_IC_04_9_1_broken_and_duplicate_rows_never_become_issues`（`:1335–1348`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-9 | AT-IC-04-9-E-1 | RI | TCS:814 | `test_selfimproving_issues.py::TestLinksOriginAndRows::test_AT_IC_04_9_E_1_problems_and_notes_are_one_per_ledger_not_per_page`（`:1350–1358`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-10 | AT-IC-04-10-1 | RI | TCS:815 | `test_selfimproving_issues.py::TestNextStepAndFields::test_AT_IC_04_10_1_only_actionable_states_are_rankable_and_carry_an_action`（`:1130–1152`） | 通過（`Ran 104 tests`，`OK`） | 一審 Q-08（P2）：R-IC-20 所列 AT 殺不到「approved 歸待您決定」；修復棒補提案各態（狀態、rankable、action）逐一對照（TCS 勘誤 1-12） |
| 04-10 | AT-IC-04-10-E-1 | RI | TCS:816 | `test_selfimproving_issues.py::TestNextStepAndFields::test_AT_IC_04_10_E_1_the_rest_are_neither_rankable_nor_actionable`（`:1154–1161`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-11 | AT-IC-04-11-1 | RI | TCS:817 | `test_selfimproving_issues.py::TestTimeline::test_AT_IC_04_11_1_every_action_reads_in_chinese_in_sequence_order`（`:1394–1420`） | 通過（`Ran 104 tests`，`OK`） | — |
| 04-11 | AT-IC-04-11-E-1 | RI | TCS:818 | `test_selfimproving_issues.py::TestTimeline::test_AT_IC_04_11_E_1_unknown_actions_and_verbs_read_unmapped_and_are_counted`（`:1422–1441`） | 通過（`Ran 104 tests`，`OK`） | — |

### FR-IC-05　排序、分頁、篩選、摘要

| AC | AT | 載具 | TCS 行 | 測試方法 | 本次結果 | 證據座標 |
|----|----|------|--------|----------|----------|----------|
| 05-1 | AT-IC-05-1-1 | RI | TCS:824 | `test_selfimproving_issues.py::TestOrderPagingFilters::test_AT_IC_05_1_1_the_two_display_orders_on_the_shared_example_table`（`:1455–1464`） | 通過（`Ran 104 tests`，`OK`） | — |
| 05-1 | AT-IC-05-1-E-1 | RI | TCS:826 | `test_selfimproving_issues.py::TestOrderPagingFilters::test_AT_IC_05_1_E_1_null_keys_sort_last_under_both_rules`（`:1466–1473`） | 通過（`Ran 104 tests`，`OK`） | — |
| 05-2 | AT-IC-05-2-1 | RI | TCS:828 | `test_selfimproving_issues.py::TestOrderPagingFilters::test_AT_IC_05_2_1_cursor_paging_is_complete_unique_and_deterministic`（`:1475–1509`） | 通過（`Ran 104 tests`，`OK`） | 一審 Q-02（P2）：整除邊界 `>`→`>=` 倖存；修復棒補 28 件、limit 7 的整除夾具 |
| 05-2 | AT-IC-05-2-E-1 | RI | TCS:829 | `test_selfimproving_issues.py::TestOrderPagingFilters::test_AT_IC_05_2_E_1_range_errors_are_usage_errors_and_the_edges_are_accepted`（`:1511–1521`） | 通過（`Ran 104 tests`，`OK`） | — |
| 05-3 | AT-IC-05-3-1 | RI | TCS:830 | `test_selfimproving_issues.py::TestOrderPagingFilters::test_AT_IC_05_3_1_an_old_cursor_still_resumes_after_new_rows_arrive`（`:1523–1537`） | 通過（`Ran 104 tests`，`OK`） | — |
| 05-3 | AT-IC-05-3-E-1 | RI | TCS:831 | `test_selfimproving_issues.py::TestOrderPagingFilters::test_AT_IC_05_3_E_1_cursor_bases_do_not_overlap_and_oversized_ids_are_rejected`（`:1539–1582`） | 通過（`Ran 104 tests`，`OK`） | 一審 Q-01（P2）：結構缺陷孤列 4S 與提案號等於 S 的邊界倖存；修復棒補 since 為 4S 加行號 ±0 兩向與 PROP 號等於 S 例 |
| 05-4 | AT-IC-05-4-1 | RI | TCS:832 | `test_selfimproving_issues.py::TestOrderPagingFilters::test_AT_IC_05_4_1_status_and_source_filters_union_intersect_and_precede_paging`（`:1593–1625`） | 通過（`Ran 104 tests`，`OK`） | 一審 Q-10（P3）：匯出形狀無絕對釘；修復棒補清單物件形狀絕對釘（頂層、議題物件、legend、summary 鍵序） |
| 05-4 | AT-IC-05-4-E-1 | RI | TCS:833 | `test_selfimproving_issues.py::TestOrderPagingFilters::test_AT_IC_05_4_E_1_bad_filter_values_are_usage_errors_listing_the_legal_ones`（`:1627–1653`） | 通過（`Ran 104 tests`，`OK`） | — |
| 05-5 | AT-IC-05-5-1 | RI | TCS:834 | `test_selfimproving_issues.py::TestOrderPagingFilters::test_AT_IC_05_5_1_the_summary_is_the_whole_ledger_whatever_the_page`（`:1655–1665`） | 通過（`Ran 104 tests`，`OK`） | — |
| 05-5 | AT-IC-05-5-E-1 | RI | TCS:835 | `test_selfimproving_issues.py::TestOrderPagingFilters::test_AT_IC_05_5_E_1_all_seven_keys_are_always_present_and_empty_ledgers_count_zero`（`:1667–1681`） | 通過（`Ran 104 tests`，`OK`） | — |
| 05-6 | AT-IC-05-6-1 | RI | TCS:836 | `test_selfimproving_issues.py::TestOrderPagingFilters::test_AT_IC_05_6_1_the_text_table_is_chinese_aligned_and_ordered_by_the_page_rule`（`:1700–1730`） | 通過（`Ran 104 tests`，`OK`） | 一審 Q-07（P2）：文字表選規則 `all`→`any` 與 `--json` 套顯示序倖存；修復棒補混合 --status 文字表序與 --json 游標序斷言（TCS 勘誤 1-12） |
| 05-6 | AT-IC-05-6-E-1 | RI | TCS:837 | `test_selfimproving_issues.py::TestOrderPagingFilters::test_AT_IC_05_6_E_1_complete_pages_empty_pages_and_null_columns`（`:1732–1744`） | 通過（`Ran 104 tests`，`OK`） | — |

### FR-IC-06　零寫入與單一真相

| AC | AT | 載具 | TCS 行 | 測試方法 | 本次結果 | 證據座標 |
|----|----|------|--------|----------|----------|----------|
| 06-1 | AT-IC-06-1-1 | RI | TCS:845 | `test_selfimproving_issues.py::TestZeroWriteAndSingleSource::test_AT_IC_06_1_1_the_verbs_leave_ledgers_the_tree_and_the_home_untouched`（`:1781–1793`） | 通過（`Ran 104 tests`，`OK`） | — |
| 06-1 | AT-IC-06-1-E-1 | RI | TCS:848 | `test_selfimproving_issues.py::TestZeroWriteAndSingleSource::test_AT_IC_06_1_E_1_no_write_primitive_is_ever_reached`（`:1795–1806`） | 通過（`Ran 104 tests`，`OK`） | — |
| 06-2 | AT-IC-06-2-1 | RX | TCS:849 | `test_selfimproving_export_status.py::TestIssuesExport::test_AT_IC_06_2_1_both_entries_agree_and_ignore_the_wall_clock`（`:885–909`） | 通過（`Ran 15 tests`，`OK`） | 一審 Q-08（P2）：R-IC-42 所列 AT 殺不到「items 依雜湊序」；修復棒補 PYTHONHASHSEED 0～3 子行程差分（TCS 勘誤 1-12） |
| 06-2 | AT-IC-06-2-2 | RI | TCS:850 | `test_selfimproving_issues.py::TestZeroWriteAndSingleSource::test_AT_IC_06_2_2_the_aggregator_files_hold_no_status_vocabulary_of_their_own`（`:1808–1816`） | 通過（`Ran 104 tests`，`OK`） | — |
| 06-2 | AT-IC-06-2-E-1 | RI | TCS:853 | `test_selfimproving_issues.py::TestZeroWriteAndSingleSource::test_AT_IC_06_2_E_1_the_scanner_counts_distinct_keys_only`（`:1818–1824`） | 通過（`Ran 104 tests`，`OK`） | — |
| 06-3 | AT-IC-06-3-1 | RI | TCS:856 | `test_selfimproving_issues.py::TestZeroWriteAndSingleSource::test_AT_IC_06_3_1_one_more_verb_and_the_new_modules_are_registered_ro`（`:1826–1840`） | 通過（`Ran 104 tests`，`OK`） | — |
| 06-3 | AT-IC-06-3-E-1 | RI | TCS:857 | `test_selfimproving_issues.py::TestZeroWriteAndSingleSource::test_AT_IC_06_3_E_1_a_write_a_child_process_a_socket_or_an_rw_import_is_caught`（`:1842–1857`） | 通過（`Ran 104 tests`，`OK`） | — |
| 06-4 | AT-IC-06-4-1 | RI | TCS:858 | `test_selfimproving_issues.py::TestZeroWriteAndSingleSource::test_AT_IC_06_4_1_si_check_on_the_real_repo_still_passes_all_33_items`（`:1859–1864`） | 通過（`Ran 104 tests`，`OK`） | — |
| 06-4 | AT-IC-06-4-E-1 | GT | TCS:859 | 審查閘（無測試函式）：`git diff --exit-code 7928b962 -- docs/06_quality/SelfImproving_Protocol/params.json` | 通過（G-R14：rc 0、無輸出；params.json sha256 與 TCS 載明的功能前值相同，見 §3） | 報告 §D『G-R11～G-R14』列：params.json 無差異 |
| 06-5 | AT-IC-06-5-1 | RI | TCS:860 | `test_selfimproving_issues.py::TestZeroWriteAndSingleSource::test_AT_IC_06_5_1_the_defect_archive_files_are_never_opened`（`:1866–1880`） | 通過（`Ran 104 tests`，`OK`） | — |
| 06-5 | AT-IC-06-5-E-1 | RI | TCS:861 | `test_selfimproving_issues.py::TestZeroWriteAndSingleSource::test_AT_IC_06_5_E_1_observation_archive_files_are_read_and_the_main_file_wins`（`:1882–1891`） | 通過（`Ran 104 tests`，`OK`） | — |

### FR-IC-12　非功能

| AC | AT | 載具 | TCS 行 | 測試方法 | 本次結果 | 證據座標 |
|----|----|------|--------|----------|----------|----------|
| 12-1 | AT-IC-12-1-1 | RI | TCS:981 | `test_selfimproving_issues.py::TestPerformanceAndEncoding::test_AT_IC_12_1_1_the_real_ledgers_answer_in_two_seconds_and_under_a_megabyte`（`:1921–1927`） | 通過（`Ran 104 tests`，`OK`） | — |
| 12-1 | AT-IC-12-1-2 | RI | TCS:982 | `test_selfimproving_issues.py::TestPerformanceAndEncoding::test_AT_IC_12_1_2_a_synthetic_ledger_of_many_thousands_answers_in_two_seconds`（`:1929–1935`） | 通過（`Ran 104 tests`，`OK`） | — |
| 12-1 | AT-IC-12-1-E-1 | RI | TCS:983 | `test_selfimproving_issues.py::TestPerformanceAndEncoding::test_AT_IC_12_1_E_1_one_huge_cell_does_not_bloat_the_page_or_change_its_shape`（`:1937–1952`） | 通過（`Ran 104 tests`，`OK`） | — |
| 12-2 | AT-IC-12-2-1 | RI | TCS:984 | `test_selfimproving_issues.py::TestPerformanceAndEncoding::test_AT_IC_12_2_1_stdout_is_utf_eight_without_bom_and_with_lf_only`（`:1954–1963`） | 通過（`Ran 104 tests`，`OK`） | — |
| 12-2 | AT-IC-12-2-E-1 | RI | TCS:985 | `test_selfimproving_issues.py::TestPerformanceAndEncoding::test_AT_IC_12_2_E_1_both_flag_spellings_agree_and_the_text_table_is_clean`（`:1970–1981`） | 通過（`Ran 104 tests`，`OK`） | — |

## 3. 審查閘型 AT（GT）與 SCG-4 閘門對照

TCS 的 8 個 GT AT 不入單元測試，以 SCG-4 通過標準的 G 編號指令輸出為證。依 TCS R 條文表的持有面歸屬：R-IC-43（根層半）→ AT-IC-06-4-E-1 歸根層半；R-IC-61、R-IC-62、R-IC-75（Console 半）→ 其餘 7 個歸 Console 半，列於 `AgentConsole/docs/06_quality/RTM.md` §2.4，此處只附對照。

| AT | AC | 歸屬 | G 編號 | 本次結果與出處 |
|----|----|------|--------|----------------|
| AT-IC-06-4-E-1 | AC-IC-06-4 | 根層半（本檔 §2） | G-R14 | 報告 §D『G-R11～G-R14』列：params.json 無差異；本回合重跑：`git diff --exit-code 7928b962 -- docs/06_quality/SelfImproving_Protocol/params.json` rc 0、無輸出，`params.json` sha256 `fc48653bfa0107012d2b5316a64bb5ec6d2bac3cdb373b967e7f10ddca1bf197`、1994 bytes，與 TCS 載明的功能前值相同（`issues` 只用既有鍵） |
| AT-IC-07-8-1 | AC-IC-07-8 | Console 半（RTM.md §2.4） | G-C4 | 報告 §A：G-C1～G-C6 除 Q-09 外全過；§D『G-C1～G-C6』列：reasons.ts、API_Contract_P3-6.md、Architecture.md 零輸出（負控非空） |
| AT-IC-07-8-E-1 | AC-IC-07-8 | Console 半（RTM.md §2.4） | G-C4 自證負控 | 報告 §D『G-C1～G-C6』列：負控非空 |
| AT-IC-11-2-1 | AC-IC-11-2 | Console 半（RTM.md §2.4） | G-C5 | 報告 §D『G-C1～G-C6』列：既有測試 hunk 無被刪 assert |
| AT-IC-11-2-E-1 | AC-IC-11-2 | Console 半（RTM.md §2.4） | G-C5 | 報告 §D『G-C1～G-C6』列：既有測試 hunk 無被刪 assert |
| AT-IC-11-3-E-1 | AC-IC-11-3 | Console 半（RTM.md §2.4） | G-C6 | 報告 §A：G-C1～G-C6 除 Q-09 外全過 |
| AT-IC-12-4-1 | AC-IC-12-4 | Console 半（RTM.md §2.4） | G-R5、G-B2、G-K1、G-F3 | 報告 §D：G-R5 整批 540 個測試 OK；G-B2 Bridge 序列 rc 0；G-K1 BUILD SUCCESSFUL；G-F3 test:cov 全綠 |
| AT-IC-12-4-E-1 | AC-IC-12-4 | Console 半（RTM.md §2.4） | G-C5 | 報告 §D『G-C1～G-C6』列：既有測試 hunk 無被刪 assert |

## 4. 覆蓋率統計與未結事項

| 指標 | 數值 |
|------|------|
| 總 AC 數 | 90（PRD；根層半 47、Console 半 46、兩半都有 AT 的 3 條：05-1、06-1、06-2） |
| 總 AT 數 | 223（TCS §3.1：RI 104、RM 7、RX 4、BR 8、BU 1、BI 26、BM 2、BA 2、BB 2、BC 1、BS 3、FL 7、FV 28、FD 3、FP 3、FG 2、FS 6、FN 3、E2 1、ES 2、GT 8） |
| 根層半 AT | 116（RI 104、RM 7、RX 4、GT 1）；測試函式 115 個，與 TCS 的根層載具 AT 一對一 |
| 整檔實跑 | 三檔各 `OK`（見檔頭引言區塊的逐字輸出） |
| SCG-4 一審（報告 §D，審查者本場自跑） | 根層：issues 檔 104 OK、issuemap 檔 7 OK、p3_meta 檔 10 OK、export_status 檔 15 OK；G-R5 `test_selfimproving_*.py` 整批 540 OK；ruff、`si check`（33 項）、LOC、ci_paths、module_layout 皆綠 |
| SCG-4 突變（報告 §A） | R-IC-01～R-IC-75 每條至少一個突變轉紅（223 次副本執行全部位元組還原 OK）；一審另有突變倖存或「所列 AT 殺不到該條突變」的 P2（逐項見報告 §B 的 Q 列表），修復棒已補斷言，二審重放待填（報告 §E） |
| 發現統計（報告 §B） | 一審：P1＝0；P2＝9；P3＝3；P4＝1 組。根層半相關：Q-01～Q-04、Q-07、Q-08、Q-09（規格勘誤，實作不改）、Q-10 |

**未結與待補（供二審與收尾）**：

1. SCG-4 二審 PASS（報告 §E）：倖存突變 X1、U1、Y8、Z2、U2、U6、D5、V42a／b（PYTHONHASHSEED 0～3）、S1／S3～S6／U9 兩族、B6／C11（所列 AT）全數 KILLED、restored OK；本檔的「本次結果」證明補斷言後整檔仍全綠，突變證據在報告 §E。
2. 修復棒的補斷言（`tools/tests/test_selfimproving_issues.py`、`tools/tests/test_selfimproving_export_status.py`，只加斷言、未加函式）與本檔同一 commit 入庫；行區間以該 commit 為準。
3. TCS 勘誤一（1-1～1-12）與 PRD 勘誤一（P-1～P-3）已於 2026-10-27 refreeze，兩鍵 digest 相同（見「規格」欄；TCS〈凍結後修訂路由〉3、4）。
4. G-R15（`python tools/run_root_unittests.py`，收尾單人窗口、重釘後再跑一次）：報告 §D 未載其輸出、本回合也未跑；根層護欄層棘輪重釘與 `tools/tests` 兩支新測試檔的重釘稅仍由收尾窗口處理。
5. macOS／POSIX 與 GitHub Actions 端未驗（AT-IC-12-2-1 要求兩平台皆跑；本回合只有 Windows）。
6. 真帳本三問可讀性（PRD §11 階段一 (a)）與階段二真機走查屬 SCG-5，由掌舵者親驗，見報告 §F（AT-IC-07-2-2 真機 1 passed；AT-IC-09-6-2 前置未成立＝真帳本無可排議題；掌舵者走查待）；Console 半證據見 `AgentConsole/docs/06_quality/RTM.md` §2.4。

