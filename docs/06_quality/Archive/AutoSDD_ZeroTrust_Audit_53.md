# AutoSDD ZeroTrust Audit 53 — improving_53（B 軌 DEF-CLDREV-030，Copy-on-Evolve v0.19→v0.20）

> **審查標的**：`AISDLC_SDD_v0.20/tools/fsm_runtime/hub_sync.py`（對外/快取 hub yaml 記憶體上限）+ `knowledge/hub-registry.yaml` + 回歸測試 + Copy-on-Evolve 機制（EVOLUTION_LOG/CHANGELOG/SSOT/gitignore）。
> **派發紀律**：v0.20 為**全新 untracked 目錄** → 依 DEF-24-001「審 untracked 新檔走主樹（worktree `git archive` 不攜 untracked，會假陰性）」，四鏡一律**主樹並行、唯讀**（禁 Edit/Write/mutation；突變實證由 parent 於階段三親跑並記錄）。
> **日期**：2026-06-24。
> **總結論**：🟢 **Architect / SA / SD / QA 四鏡全部 OVERALL PASS、P0=P1=P2=0**；2 項 P3 殘餘（billion-laughs 部分緩解接受殘餘、hub_merge latent routed=DEF-53-001），皆不阻斷。

---

## 1. 階段一基線（parent 親跑，Explore agent 實測）

| 項目 | 實測 |
|------|------|
| HEAD / 工作樹 | `6f27d89` / 乾淨 |
| ci-gate 基線 | **exit 0**；v0.01:1478 / v0.19:1638 / scripts:127；全 lint ✅ |
| AutoClaude lint-imports | 8 kept / 0 broken |
| DEF-CLDREV-030 重現 | 6 處 `read_text` 前皆無 `stat().st_size` 上限；L334 最高風險 |
| hub deny-by-default | `allowed_endpoints: []` + `deny_unlisted: true`（hard-coded）+ `push.enabled: false` |

**硬閘通過**（v0.19 1638 == floor、0 failed）→ 進入修復。

## 2. 修復摘要（階段三）

- 模組常數 `MAX_HUB_FILE_BYTES = 1 MiB`（registry `sync_policy.pull.max_file_bytes` 可覆寫，非正值/型別錯 fallback）；
- `HubContentTooLarge(HubConfigError)` + 純函式 `_read_text_bounded()`（`stat().st_size` 超限即 raise）；
- 套用 **3 處對外不受信讀取**：L334 pull stamp（fail-soft skip+audit）、`diff()` cached、`promote()`（fail-closed）；
- 受信本地 registry / 自寫累積 audit-log / cache-meta **刻意不 cap**；
- `hub-registry.yaml` 補 `max_file_bytes: 1048576`（值＝常數）；
- 回歸鎖 `TestHubFileSizeCap` +8 case；3 anchor 受控突變實證（暫關 cap → 轉紅、還原 8 passed）。

## 3. 四鏡 zero-trust 裁定（皆主樹獨立、不採信審計文件、親讀/親跑取證）

### 3.1 Architect 鏡 — OVERALL PASS（零 P0~P2，1 P3 觀察）
- **架構純潔性**：純加法 696→752 行；常數/例外/helper(10 行)/`__init__` override 防禦性 fallback；3 對外點走同一 helper（DRY）；無 God-object、未動微核心。
- **對外/受信界定**：親讀 `_record_audit`(L288–306) 確認 audit log 為 **append 語意**（讀→`setdefault("events",[]).append`→覆寫），cap 會誤殺合法成長 → 不 cap 正確；registry/cache-meta 受信/自寫不 cap 正確。
- **Copy-on-Evolve 潔淨度（DEF-11-002）**：`git add -A -n` 859 行，逐類副檔名實掃（429 md/199 yaml/164 py/18 gitkeep，**0 pyc**）+ 實掃 runtime 路徑（build/reports、formal/states、pull-cache、PUSH-AUDIT、push-outbox、quarantine）**零夾帶**；唯二命中為良性（`build/logs/README.md` 說明檔、`data/slo_events/quarantine/.gitkeep` 佔位）。**非僅憑 .pyc 數宣稱**。v0.01/v0.19 凍結 `git status --short` 空。
- **FSM/TLA 零變更**：`diff -rq formal/` 全同（含 5 `*.tla`）、`diff transition_rules.py` 無輸出 → 不觸五軌 TLC 成立。
- **P3 觀察**：752 行貼近 ≤750 名目線（該紅線屬 AutoClaude `check_loc_budget` 政策、非 SDD `arch_fitness` 範疇；含 ~30 行註解、實質在界內、arch_fitness fail=0）。**非缺陷。**

### 3.2 SD 鏡 — OVERALL PASS（零缺陷）
- 修復對齊 DEF-CLDREV-030 routed 意圖（L74 `1024*1024`==routing「如 1 MiB」），範圍精準無蔓延（6 處僅 3 處加 cap，註解說明受信點不 cap）；連帶縱深 promote fail-closed 屬實。
- 文件↔磁碟逐項一致：EVOLUTION_LOG v0.19→v0.20、CHANGELOG v0.20、Defect_Log round-53 + 狀態 fixed@v0.20、registry `1048576`==常數、註解一字不差。
- 測試 Rule 9：8 case 非空殼、3 anchor 斷言設計支持突變宣稱；親跑 `test_hub_sync.py` 44 passed、v0.19 同檔 36（無 `TestHubFileSizeCap`）→ 差量 **+8** 機械證。
- EVOLUTION_LOG 標頭已更新至「v0.01~v0.19 凍結、v0.20 可修改」。

### 3.3 QA 鏡 — OVERALL PASS（P0=P1=P2=P3=0）
- 親跑 `bash scripts/ci-gate.sh` **EXIT=0**：**v0.01:1478 / v0.20:1646 / scripts:127**；全 lint 綠（4 SSOT：FRAMEWORK_STATUS fresh / skill_header 對齊 v0.20 / skills-ssot 父層==LATEST 59 檔 / router 3 event 全可達；rfc/gitignore〔v0.20 block〕/agent_template/collaboration/scenario_frequency）。
- 新測試非空殼：讀 8 case + 單跑 **8 passed**；實作存於 hub_sync.py（常數:74/例外:81/helper:209/三點 388/620/651）。
- 零退化：1646=1638+8、v0.01 1478 不變、scripts 127 不變；v0.01/v0.19 `git status` 空。
- Defect_Log 誠實：DEF-CLDREV-030 fixed@v0.20、round-53 數字與親跑完全一致無虛報；45 檔 skill footer modified 為 Copy-on-Evolve 合理產物。

### 3.4 SA 鏡 — OVERALL PASS（零 P0/P1/P2，2 P3 殘餘；scratchpad 實跑攻防）
- **威脅緩解實證**：(c) 邊界 cap=100→100B OK/101B raise（`>` 嚴格大於正確）；(a) cap=1024+5051B `SLV-BIG.yaml`(偽 verified) pull→`error=None`(fail-soft)、audit 1 筆 `hub_pull_stamp_error(HubContentTooLarge)`、大檔未被改寫、同批小檔仍正常 stamp external；(b) 5051B cached promote→raise `HubContentTooLarge`（fail-closed、未升信任階梯），對照小檔 external→verified 正常。
- **未 cap 點論證駁回為破口**：CLI `HubSyncClient()` 僅用 `DEFAULT_REGISTRY_PATH`、**無 `--registry` 參數** → 攻擊者無法注入外部 registry；cache-meta/audit 自寫帳本，audit 按設計累積。
- **既有控制零弱化**：實投 `!!python/object/apply:os.system` → bounded read→safe_load `ConstructorError` 攔下，**未執行 PWNED**、落 audit；`deny_unlisted=True`(L175 硬編碼) 未動；external-stamp 未弱化；override 防呆（垃圾/負/0 皆 fallback 1 MiB、合法 4096 生效）。
- **P3-1 殘餘（接受）**：billion-laughs——SA 實測 266B/475B alias bomb 全程 pull 0.01s 零爆炸（PyYAML alias 為共享引用、parse/dump 不展開），風險僅存假想下游深 materialize；deny-by-default 第二防線。
- **P3-2 latent（routed=DEF-53-001）**：`hub_merge.py` `_read_yaml`(L70)/copy(L238) 未 cap 讀 pull-cache，但實查 `detect_conflict`/`resolve_or_record` **僅測試呼叫、未 wire 進 runtime** → 當前不可達、本輪 scope 內無破口；觸發閘＝wire hub_merge 前必補 cap。

## 4. 零退化驗證矩陣（階段四，parent 親跑 + QA 鏡複核一致）

| 檢查 | 通過條件 | 實測 |
|------|---------|------|
| SDD 雙軌 + scripts | exit 0；v0.20 ≥ floor 1638 / 0 failed | ✅ exit 0；v0.01:1478 / v0.20:1646 / scripts:127 |
| arch_fitness | structural fail=0 | ✅ fail=0（僅 FF-16 advisory） |
| SSOT 4 lint | fresh/對齊/綠 | ✅ FRESH / 對齊 v0.20(45) / 父層 59 / 3 event |
| 其餘 shared-infra lint | 全 ✅ | ✅（gitignore v0.20 block 補齊） |
| Copy-on-Evolve 潔淨 | 零 runtime 夾帶 | ✅ 859 tracked 純源碼（Architect 鏡實掃） |
| 五軌 TLC | 僅 FSM/`*.tla` 變更時 | **N/A**（逐位元零差異不觸發） |

## 5. 缺陷處置總表

| 缺陷 | 嚴重度 | 狀態 | 備註 |
|------|--------|------|------|
| DEF-CLDREV-030 | P3 | **fixed@v0.20** | 對外 yaml 大小上限；四鏡 PASS、SA 實證緩解 |
| DEF-CLDREV-030 / P3-1 | P3 | **接受殘餘** | billion-laughs 部分緩解；SA 實測 parse 不炸 + deny-by-default |
| DEF-53-001 | P3 | **routed（latent）** | hub_merge 未 cap pull-cache 讀取，當前不可達；wire 前必補 cap |

## 6. 結案判定

DEF-CLDREV-030 經 Copy-on-Evolve v0.20 就地清償，四鏡 zero-trust 全 OVERALL PASS、零 P0~P2 缺陷、零退化（ci-gate exit 0、v0.20 1646=floor 1638+8、SSOT 全綠、FSM 零變更不觸 TLC）。2 項 P3 殘餘皆經實證/論證為不阻斷（P3-1 接受殘餘、P3-2 routed DEF-53-001 附觸發閘）。**據實結案，無虛構缺陷、無虛報數字。**
