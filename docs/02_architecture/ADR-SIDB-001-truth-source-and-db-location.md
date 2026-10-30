# ADR-SIDB-001：真相源與 DB 位置（PRD 簡稱 SIDB-01）

## 狀態

Accepted（階段性：P3b 切換前須滿足 PRD §8.1 的 H2〔DB 生命週期隔離〕與 H3〔拓撲決議與他機匯入快照演練〕，兩項未成立前本決定只到影子期）。日期 2026-10-31；決定者＝主控依 `docs/01_requirements/SelfImproving_Ledger_DB_PRD.md` §9.5 SIDB-01 轉正式，OQ-2 的拓撲部分採掌舵者 2026-10-27 裁決（PRD §13.2「全部採建議值」）。

## 脈絡

- 掌舵者 2026-10-27 裁決「廢除帳本機制，改由 DB＋議題中心承載」（PRD 立案段）：自我進化三類帳本的真相源由 git 內的檔改為 Docker PostgreSQL 18 的 `si` schema，P3b 那一個 commit 才換手（PRD §8 三條原則）。
- git 今天兼任四個角色：版本史、跨機同步、離機備份、CI 內容閘的輸入（PRD §2、R-1、R-2）。切換後 DB 只有一份，持久性取決於備份。
- 現場事實（PRD §8.2、`[C-12]`、`[C-13]`）：`aisdlc-pg-primary` 只有容器內 `5432/tcp`、未發布到主機；主機 5432 被獨立容器 `autoclaude_pg` 占用；`docker compose down -v` 是文件化清場手段（17 檔 41 處），`si` 若與 Console 同卷，一次清場等於治理資料全失；離站備份只是本機單碟 MinIO，同機而非離機。
- 跨機（R-1）：git 不記錄寫入機器；2026-09-27 起 132 個 commit 觸及三本帳，主旨標明 Mac 輪的最近一筆是 2026-10-07（`9b9228fd`），其後約 20 日無標示 Mac 的寫帳提交——無證據顯示近期有 Mac 寫入，但不能排除（PRD `[C-15]`、§13.2 OQ-2）。

## 選項與代價

- 選項 A：維持檔（不改真相源，只做影子或完全不做）。
- 代價：「廢除帳本」不成立；缺陷、結構債沒有 CLI 動詞、人會繼續手改 Markdown（PRD §4 觀察 2）；掌舵者的裁決落空，且 10-26 已用「open 觀察歸零」滿足過的較弱讀法會被當成最終解。
- 選項 B：Console 的 PG 加 `si` schema（同一個 `aisdlc-pg-primary`）。
- 代價：沿用現成容器與備份鏈，成本最低；但 `down -v` 對 Console 專案的清場會連 `si` 一起清（H2 的風險），主機連線需疊加 dev 檔並改埠；備份與還原核對清單只數 `console` 表，須補 `si`（`docker/README.md` 〈4.3〉）。
- 選項 C：專屬 PG 容器（獨立卷、獨立 compose 專案與埠，只放 `si`）。
- 代價：多一個容器與埠要維運，Console 直讀 P2 需讓 console-api 與該容器網路可達；專案內沒有現成備份鏈，離機備份要另設（ADR-SIDB-008）；好處是生命週期與 Console 解耦，`down -v` 不再波及。
- 選項 D：借用 `autoclaude_pg`。
- 代價：`autoclaude_pg` 是 AutoClaude 開發與正式棧的資料庫（`AutoClaude/docker-compose.yml:30-43`：pg18、具名卷 `pg_data`、預設發布主機 5432），不是 tmpfs；但它的升級與全新環境步驟本身就含 `docker compose down -v`（`AutoClaude/docs/08_deployment/PG_Version_Upgrade_Guide.md:101,140`），`si` 住進去等於把「單一份、要長期保存」的治理資料交給另一個產品的清場節奏；叢集級角色（`si_owner`、`si_writer`、`si_reader`）也會落在另一個產品的叢集裡。另有 tmpfs、用完即丟的 CI 對等容器 `autoclaude_ci_pg`（pg17，`AutoClaude/docker-compose.ci.yml:25-44`），與它預設都占主機 5432、不能同時起。

## 決定

- 採**選項 C（專屬 PG 容器）為 P3 的建議落點**；**B 在同樣隔離下可接受**——即只要 H2 成立（對 Console 專案做 `down -v` 後 `si` 資料仍在，或有機械式清場前快照），B 與 C 等價可選。否決 A（與裁決衝突）與 D（`si` 的生命週期受制於 AutoClaude 的升級與清場步驟，且與 CI 對等容器搶主機 5432）。
- **影子期任何可達的 PG18 皆可**：P1、P2 的 DB 是可丟可重建的影子（檔案仍是真相），因此不先綁死容器位置；開發者用任何可達的 PG18（含 `autoclaude_pg`）自建即可，不需等本 ADR 的最終落點。落點在 P3 進場前由 H2、H3 定案。影子庫若建在他人的叢集（例如 `autoclaude_pg`），叢集級角色不隨 `DROP DATABASE` 消失，用完須先 `DROP OWNED BY` 再 `DROP ROLE`，並驗 `pg_roles` 無 `si_` 開頭殘留；P0 的 SQL 烟測改用 `docker run --rm` 的一次性容器，就是為了不留這類殘留（TCS G-P0-7）。
- **OQ-2 拓撲裁決**：P1～P2 各機自建影子；P3 前定案；預設 **單一主力機為真相**、他機唯讀（他機匯入快照到本機拋棄式庫，H3 證據含他機匯入演練）。掌舵者未另答「Mac 是否仍寫帳」，依預設處理；若仍要在 Mac 寫帳，改走共用遠端 PG 或限定 Mac 輪的寫入經主力機動詞，P3 進場前再確認。
- 本決定不改既有容器、compose 或卷；P0 只定規則。

## 再開症狀

- 對 Console 專案執行 `docker compose down -v` 後 `si` 資料消失（`si db status` 回 `SCHEMA-BEHIND` 或表不存在），或清場前快照缺席 → 回頭重評 B 與 C 的隔離條件。
- 專屬容器或 dev 檔疊加時出現埠衝突（`port is already allocated`，主機 5432 被 `autoclaude_pg` 占用的同型事件）→ 重評 C 的埠配置，或 B 的 dev 檔疊加方式。
- 他機匯入快照演練失敗（`si db import --from-snapshot` rc≠0 或 `si check` 非全綠）→ 重評單一主力機假設。
- 掌舵者表示近期要在 Mac 或第二台機器寫帳（H3 的拓撲前提改變；可觀測＝他機出現 `git log` 觸及帳本檔的寫帳提交）→ 重評 OQ-2。

## 連動面

- PRD §8.1（H2、H3）、§8.2、§9.5；R-1、R-2；AC-LD-12-2、12-3。
- 後續：P1 的影子庫不綁容器；P3a 的生命週期隔離與離機備份演練、彩排庫；P3b 的 `si db flip --check` 檢查 H2、H3 證據檔。
- 相關 ADR：ADR-SIDB-006（B′ 專屬容器時用 `si.console_requests`）、ADR-SIDB-007（連線憑證）、ADR-SIDB-008（快照與離機備份）。
- 上位規格勘誤（備案於 `docs/06_quality/SelfImproving_LedgerDb_P0_Errata.md`，P0 不套用）：E-1（`SelfImproving_PRD.md:791,793` 改述為模式矩陣並引本 ADR，P1 套用）、E-2（ADR-SI-01 被本 ADR 取代，P3b 起成立；P2 套用）。SI PRD 側六把 FSM 鍵各 `spec-refreeze` 一次：`monorepo-si-p0-ledger`、`monorepo-si-p1-propose`、`monorepo-si-p2-gate-apply`、`monorepo-si-p3-measure-retire`、`agentconsole-si-decide`、`agentconsole-si-mirror`（本清單為「SI PRD 側六鍵」的單一出處）。
- B 方案需補 `AgentConsole/docker/README.md` 〈4.3〉還原核對清單加 `si`；連動補丁已備案於 `docs/02_architecture/SelfImproving_LedgerDb_Architecture_Draft.md`（§7.2 與 docker README〈4.3〉兩塊的 B 方案、C 方案變體），P3 套用；P0 不改 `Architecture.md` 與 `docker/README.md`。
