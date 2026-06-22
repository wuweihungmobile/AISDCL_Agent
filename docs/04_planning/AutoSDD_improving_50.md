# AutoSDD improving_50 — `.claude` hooks/skills 第八輪四鏡複審（B 軌 Dogfooding）

> **軌道定位**：軌道① **B 軌**（手腳框架 AISLDC_SDD dogfooding）。標的＝最新演化版 `AISDLC_SDD_v0.19` 之 `.claude/`（5 hooks + 42 skills + 兩處 settings.json + 根 router）對 SDD 與整體系統架構之合規性。
> **下一份**：`AutoSDD_improving_51.md`（按需）。
> **政策延續**：掌舵者既定「就地修 v0.19（非 Copy-on-Evolve 遞版，比照 AGTREV/CLDREV 重審輪不動 EVOLUTION_LOG/CHANGELOG）」。
> **日期**：2026-06-23。**最新框架版＝v0.19**（FRAMEWORK_STATUS.md SSOT）。

---

## 1. 本輪輸入（自上輪繼承）

- 上輪＝`.claude` 第七輪複審（commit 8aa1846 / improving_49），DEF-CLDREV-027 全閉、零 routed 殘留。
- 缺陷帳本 `AutoSDD_Defect_Log.md`：DEF-CLDREV-001~027 全 fixed@v0.19；本輪前無 open/routed 的 .claude 缺陷。
- 基線（上輪結案宣稱，本輪階段一親驗）：v0.19 pytest **1636** / scripts/tests **124** / SLV 規則 **14** / skills **42** / 父層鏡像 **59**。

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit）

parent 親自完成（不憑記憶/文件宣稱）：

| 項目 | 命令 | 實測 |
|------|------|------|
| ci-gate 基線 | `bash scripts/ci-gate.sh` | **exit 0**；v0.01:1478 / v0.19:**1636** / scripts:**124**（與上輪結案宣稱完全吻合） |
| hooks/settings/router 親讀 | Read ×5 hooks + 根 router + 2 settings.json | 全部前七輪 CLDREV 修復在位、fail-soft 紀律完整、版本中性 |
| skills 計數 | `ls .claude/skills/` | 42 目錄 + 3 治理 .md（README/PLAN/TEMPLATE）＝45 項，與 SSOT 42 一致 |
| 工作樹 | git status | 乾淨、HEAD=8aa1846；標的 tracked 乾淨檔 → 依 DEF-24-001「審 tracked 乾淨檔→主樹」派發 |

**硬閘**：基線無 failed、未低於上輪 passed（1636==1636）→ 通過，進入階段二。

## 3. 階段二/三：四鏡審查 + 增量修復

派 **Architect / SA / SD / QA 四鏡**主樹並行獨立 zero-trust 審查。結果：

- **Architect**：OVERALL PASS（6 維親驗，零新缺陷）。FSM 三層治理閉環、hooks 版本中性（`grep v0.[0-9]`=0）、根 router 一一對應+fail-safe、嵌套 timeout 30⊃25⊃20、三支柱 SCG 無錯置、Rule 9 絕對禁令全守（meta-oracle/genesis grep=0）。1 條 advisory：建議加 timeout 不變量機械測試（已有 hub timeout 鎖，屬強化）。
- **SD**：OVERALL PASS（6 維親驗，零缺陷）。42 skill 範本路徑 8/8 實存零死鏈、SLV 14 條對齊、版本戳 42/42 對齊 v0.19、frontmatter 最小權限（無 Bash/全權）、SCG 對應無錯置、DEF-CLDREV-027 真在位。
- **QA**：OVERALL PASS。自跑 ci-gate 核 v0.19:1636/scripts:124/SLV:14/skills:42 全閉合、DEF-CLDREV-012~027 抽 6 筆全對應磁碟真實修復、v0.01 凍結基線 0 觸碰、父層鏡像 59 檔新鮮。
- **SA**：OVERALL PASS-with-findings。揪出 **F-01 P2 路徑注入 / F-03 P3 守門繞過 / F-02 P3 yaml 深防禦**（對 5 hook 構造 16 種畸形 payload 全 fail-soft、hub allowlist 預設 deny、指令注入皆 list-form 無洞）。

parent 對 SA 鏡三缺陷做 zero-trust 親驗重現（`scratchpad/verify_f01.py` 證 `SDD_ACTIVE_VERSION="0.19/../../../../Windows"` 逃逸至 `D:\Windows\...`；Read `context_ledger_pre.py:255` 證 tool_name 未正規化；Read `hub_sync.py` + `hub-registry.yaml` 證 deny-by-default）後分流。

### <Architecture_Design_Review>

1. **架構純潔性**：F-01 修在整合層 router（非凍結本體、非 runtime），F-03 修在 hook facade 輸入正規化，無新增程式邏輯、無 God-object、Thin Facade 不受影響。✅
2. **持久化相容**：無狀態/checkpoint 變更。✅
3. **安全防護網**：F-01 為架構紅線「路徑注入／任何從文件生成指令路徑須等強度消毒」之直接落實——白名單（語法）+ 邊界斷言（resolved 路徑）縱深兩道，對齊框架自身 `_disk_latest_version` 嚴格 regex 慣例；F-03 補齊輸入域型別防護（DEF-CLDREV-020/025 家族）。✅
4. **對外 I/O 安全**：F-01 收緊 `SDD_ACTIVE_VERSION` 注入路徑；hub allowlist 預設 deny 不變。F-02（hub yaml 大小上限）屬框架本體 scope 外，routed RFC。✅

### 本輪修復（DEF-CLDREV-028/029 fixed@v0.19；030 routed）

| DEF | 嚴重度 | 檔 | 修法 |
|-----|--------|----|------|
| 028 | P2 | `.claude/hooks/sdd_hook_router.py:154` | 白名單 `\d+\.\d+` + `is_relative_to` 邊界斷言（縱深兩道）；+3 攻防測試 |
| 029 | P3 | `AISDLC_SDD_v0.19/.claude/hooks/context_ledger_pre.py:255` | 非字串 tool_name 退回空字串；+2 回歸測試（spy 捕捉守門實收值） |
| 030 | P3 | `tools/fsm_runtime/hub_sync.py`（scope 外） | routed → 框架本體 RFC（外部 yaml read_text 前加大小上限；deny-by-default 下風險近零） |

兩處修復皆經受控突變實證非空殼（白名單→`if False` 轉紅、tool_name 護欄移除轉紅），還原後全綠。

## 4. 階段四：CI 平價收斂（零退化驗證矩陣）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 + not-chaos 全綠 | ✅ **exit 0** |
| v0.19 pytest | （ci-gate [1/3]） | ≥ floor 1636 / 0 failed | ✅ **1638**（floor+2 回歸測試，零退化） |
| v0.01 凍結基線 | （ci-gate [1/3]） | 不變 + 0 觸碰 | ✅ 1478 / git 證 0 觸碰 |
| 共享 infra | （ci-gate scripts/tests） | ≥ floor 124 | ✅ **127**（floor+3 攻防測試） |
| skills-ssot | `sync_exposed_skills.py --check` | 父層==LATEST | ✅ 59 檔一致 |
| skill_header | （ci-gate lint） | 對齊 v0.19 | ✅ |
| FRAMEWORK_STATUS | `framework_status_snapshot.py --check` | fresh | ✅ 仍 42 skill |
| router hook 覆蓋 | （ci-gate lint） | event 全可達 | ✅ |
| 五軌 TLC | （FSM/`*.tla` 變更才觸發） | N/A | 本輪零 FSM 變更，不觸發 |

**RTM**：
- DEF-CLDREV-028（P2 路徑注入）→ router 白名單+邊界斷言 → `test_router_version_path_safety.py` 6 惡意向量 + 正例對照 + 突變實證 → **全閉**。
- DEF-CLDREV-029（P3 守門繞過）→ tool_name 正規化 → `NonStringToolNameTests` spy 斷言 + 突變實證 → **全閉**。
- DEF-CLDREV-030（P3 yaml 深防禦）→ routed 框架本體 RFC（scope 外、deny-by-default 風險近零）→ **routed**。

## 5. 結論

v0.19 `.claude`（5 hooks + 42 skills + settings.json + 根 router）經第八輪四鏡 zero-trust 複審：**Architect/SD/QA 三鏡零新缺陷**；SA 鏡首次在 hooks 程式面揪出**安全級 P2 路徑注入**（`SDD_ACTIVE_VERSION` 未消毒 → 潛在 RCE）並就地以縱深兩道清償，另補一條 P3 守門繞過、routed 一條框架本體 yaml 深防禦。八輪缺陷數 **5→5→5→3→4→3→1→2**（其中 1 routed scope 外）。零退化（ci-gate exit 0、v0.19 1638≥floor 1636、scripts 127≥floor 124、v0.01 凍結基線 0 觸碰）。框架 `.claude` 治理層對 SDD 與整體架構之合規性已高度成熟；本輪的價值在於把「整合層 router 的 env→路徑」攻擊面收斂到與框架自身嚴格 regex 慣例一致。
