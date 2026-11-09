# V1／V7 真機驗證報告（SelfImproving P4 Console 半，HEAD e5f83e02）

## A 判定
- **V1：PASS**。兩次 POST 皆 201；稽核目錄新增兩檔，檔名＝`<auditRef>.json`，body 逐欄位等於送出內容；`patrol --dry-run` rc 0 列出兩份將入帳的 audit_ref，前後快照（`~/.autosdd/selfimproving` 全檔 size／mtime、事件帳本 sha256）相同；`status --json` 的 `console_pending` count 2（sched-set、run-request）。無失敗徵兆。
- **V7：PASS**。V1～V22 於暫存庫套用成功、三筆舊 kind 列 md5 前後相同、V23 rc 0、五值皆可寫、`bogus` 被拒、`si_console_writes_kind_check` 定義含五值；暫存庫已 drop。附帶：正式庫 flyway_schema_history 最大版本 23 success=t，實名 `si_console_writes_kind_check` 存在。

## B 步驟表
1. 重建：`docker compose --profile db --profile app --profile full up -d --build` rc 0；三服務 healthy。映像 Created（UTC）：backend 2026-11-09T11:57:15Z、engine-bridge 11:56:13Z、frontend 11:55:28Z。pg-primary 映像亦重建（資料卷保留）。
2. 登入 admin／operator／viewer（開發預設帳號，經 nginx http://localhost）。`GET /api/v1/si/status` 200，`schedule.periodMin=60`、`periodMax=10080`。
   - POST schedule/set `{"enabled":true,"periodMinutes":120,"reason":"V1 真機探針"}` → 201，auditRef `af2d3d00-8a65-414e-8324-3629d0564392`，kind sched-set，subject null，keyId ca09e52f
   - POST runs/request `{"note":"V1 真機探針"}` → 201，auditRef `cc8e8f04-8ecd-49fc-871b-0ad937279f3d`，kind run-request
   - GET 兩路徑（admin）→ 405；POST VIEWER → 403 ACCESS_DENIED；POST OPERATOR（runs/request）→ 403 ACCESS_DENIED；無 token → 401 UNAUTHENTICATED
   - periodMinutes 59、10081 → 422 invalid_request「須在 60～10080 分鐘之間」；120.5 → 422（須為 JSON 整數）；缺 enabled → 422
   - 回應全文逐字見 `v1_calls.txt`（同目錄）
   - 備註：API 收據 JSON 不含「主機端入帳指令字串」欄位（依契約該字串由前端收據顯示）；本棒未真送 UI 表單。
3. 稽核檔（`%USERPROFILE%\.autosdd\selfimproving\console_audit`，原 5 檔→7 檔）：
   - af2d3d00….json，448 位元組，sha256 `1B1503F7A8908BEC0C07EAFAA854AAA0E58E3E1320B84AA2DC4F0218782F6CEC`；外層鍵序 schema_rev,kind,audit_ref,subject,body,key_id,mac；body 鍵序 schema_rev,audit_ref,kind,user,role,time,enabled,period_minutes,reason，值（enabled true、period_minutes 120、reason「V1 真機探針」、user admin、role ADMIN）與送出一致
   - cc8e8f04….json，410 位元組，sha256 `ED607ACD1722F503636999D917E69042475BAC576551CE5E7FB565B051A89CF8`；body 鍵序 …,time,note
4. 主機：`AUTOSDD_SI_AUDIT_KEY` 取 .env 第一把（未印值）。`patrol --dry-run` rc 0，輸出含 `step=入帳 result=將入帳 sched-set:af2d3d00-…、run-request:cc8e8f04-…`、`step=到期 result=停用`、`step=運轉 result=無待啟動的運轉`；零寫入快照相同。`status --json` rc 0：`console_pending` {status read, count 2, items 兩筆 audit_ref＋kind}；`schedule` 欄位 enabled false、period_minutes 1440、period_min 60、period_max 10080、heartbeat_minutes 15、last_set／cell_start／cell_end／ran_this_cell／last_skip 皆 null、overdue false、armed {task AutoSDD_SI_Patrol, present null, credential NOT-EVALUABLE：not-queried}（全文見 `status.json`）。
5. 未真入帳。
6. 前端（Playwright，`fe_probe.cjs`，唯讀、只開不送出）：admin 於 /self-improving：`si-schedule-panel` 可見；三顆按鈕（啟用排程／修改週期／立即啟動一次演化）存在；橫幅欄位組＝啟用、週期（1440≈1 天）、最近一次設定、本格起訖、本格已執行、本格最近一次略過、逾期、主機排程任務是否武裝（量不到）；啟用對話框週期預填 1440、界 60～10080；主控台錯誤 0。VIEWER 四個 testid 皆 0（零控件），主控台錯誤 0。截圖 `shot_admin.png`、`shot_admin_dialog.png`、`shot_viewer.png`（同目錄）。未覆寫 repo 內截圖。
7. V7：`createdb si_v7_probe`；建 schema console 後以 `search_path=console` 逐檔 psql 套 V1～V22（rc 全 0）；插入 decide／obs-add／obs-close 三列；V23 前插 sched-set 被 CHECK 拒；V23 rc 0（`DO ALTER TABLE ALTER TABLE`）；md5 前後均 e6438ad4570baa9eda6b7ee13ba74c8a；插 sched-set、run-request 成功、bogus 被拒；約束定義含 decide,obs-add,obs-close,sched-set,run-request；`dropdb si_v7_probe` rc 0、pg_database 計數 0。

## C 給掌舵者的 V2／V3 材料
- auditRef：sched-set `af2d3d00-8a65-414e-8324-3629d0564392`；run-request `cc8e8f04-8ecd-49fc-871b-0ad937279f3d`
- 入帳指令（monorepo 根、已設 `AUTOSDD_SI_AUDIT_KEY`）：
  - `python tools/selfimproving.py sched set --carrier console --audit-ref af2d3d00-8a65-414e-8324-3629d0564392`
  - `python tools/selfimproving.py run-open --trigger a --carrier console --audit-ref cc8e8f04-8ecd-49fc-871b-0ad937279f3d --coord console_audit/cc8e8f04-8ecd-49fc-871b-0ad937279f3d.json --by console`
- 注意：sched-set 那份是「啟用、週期 120」，入帳後排程會變啟用，請知情。UI 入口 http://localhost/self-improving（admin）。

## D 誠實劃界
- V7 以 psql 逐檔套 V1～V23，非 Flyway 本身；但正式庫 Flyway 已真實套到 23（success=t）。
- 未真送 UI 表單、未驗 UI 收據的入帳指令字串（mock spec 涵蓋）。
- 「稽核檔位元組＝backend 送出本文」無法直接取得送出端本文，以欄位逐項吻合＋patrol dry-run 讀到並列出（無驗簽失敗輸出）佐證。
- 暫存庫匯入用的 SQL 拷貝留在容器暫存目錄 v7 資料夾：工具護欄擋該路徑的刪除；無害，容器重建即消失。

## E 清場
映像保留；暫存庫 si_v7_probe 已 drop；`git status --short` 為空（實測輸出空）；稽核目錄多出的兩檔保留供 V2／V3 用。
