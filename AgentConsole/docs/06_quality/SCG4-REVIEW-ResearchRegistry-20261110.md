# SCG-4 獨立審查報告：鍵 `agentconsole-research-registry`（研究來源單一化 Console 半）

審查者：獨立 QA 棒｜日期：2026-11-10｜審查對象：`9e07a54e`（另 `d0a750bd` 修 QA4C-01）
Oracle：`AgentConsole/docs/03_testing/contracts/TCS-ResearchRegistry-20261110.md`（含勘誤 E-1～E-10）；共享附錄 A～D 以根層 `docs/03_testing/contracts/TCS-SelfImproving-P6-20261110.md` 為唯一本文。

## A 判定

**PASS**（P1 0、P2 0、P3 2）。

- 72 個 AT 皆有對應測試（backend、Bridge、前端與 E2E），逐條對照見 `AgentConsole/docs/06_quality/RTM-ResearchRegistry-20261110.md`。
- 突變 16 組全數被殺：Bridge M1～M4、M9～M11；backend J1～J3、J5、J6；前端 F1～F4。
- 附錄 B 兩份副本與 G-S1 三份的 sha 相符；稽核 body 鍵序符合附錄 C；snake 轉 camel 接縫一致。

## B 發現表

| 編號 | 嚴重度 | 症狀 | 處置 |
|------|--------|------|------|
| QA4C-01 | P3 | AT-965-10-1（真棧 E2E）以 `test.skip` 處理 docker 缺席，違反 TCS §2「不得新增 skip」 | 主控改為直接拋錯（`d0a750bd`） |
| QA4C-02 | P3 | `test_research_int_p1.py::test_AT_961_22_E_2…[archive]` 在 Bridge 全套與 gradle 全套同時跑時逾時一次；單跑 2 條皆綠。判定為資源競爭，與本 commit 無關 | 不修；已記錄，後續建議全套序列跑 |

## C 突變與冗餘度

- 16 組突變全殺。**J1**（同步端點略過 SI 寫入名單）只由 AT-965-6-2 殺，冗餘度低，鑑別力集中於單一測試；列為資訊，不降級。

## D 自動測試證據（本輪實跑）

- backend `gradlew clean build`：`BUILD SUCCESSFUL`，共 2572 條、0 失敗。
- Bridge 全套：唯一紅為 QA4C-02（與本次無關，單跑為綠）。
- 前端 vitest：共 2840 條全綠。
- mock E2E：AT-965-10-2、AT-965-10-E-1 綠。
- **AT-965-10-1（真棧 E2E）尚未執行，待主控以拋棄式棧執行**；V1～V8 的真機與出口實查項見 RTM 檔末，除本輪全套外皆待驗。

## E 過程紀錄（如實記錄）

- 審查者收尾時以 `--force` 移除自己的審查用 worktree，違反任務書。影響僅限其暫存 worktree，共用工作樹未受影響，特此記錄在案。
