# AutoSDD_ZeroTrust_Audit_47 — 第五輪 `.claude` hooks/skills 四鏡審計 + 複審證據

> 對應計畫：[AutoSDD_improving_47.md](../04_planning/AutoSDD_improving_47.md)｜缺陷帳本：[AutoSDD_Defect_Log.md](AutoSDD_Defect_Log.md)（DEF-CLDREV-020~023）
> 日期：2026-06-23｜標的：`AISDLC_SDD_v0.19/.claude/`（5 hooks + 42 skills + settings.json）

## 1. 基線（階段一硬閘，parent 親跑）

```
$ bash scripts/ci-gate.sh   →   exit 0
逐軌計數：AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.19:1629 scripts/tests:123
$ git status --porcelain    →   (clean)
```
根 router 機制親讀確認：`sdd_hook_router.py:154` `target = REPO_ROOT/AISDLC_SDD/AISDLC_SDD_v{version}/.claude/hooks/<script>`、`:176` `subprocess.run([sys.executable, str(target)], ...)` → 轉發到 v0.19 同一支實體 hook，**根層無獨立副本**。

## 2. 四鏡複審結論（主樹並行，DEF-24-001 tracked 檔主樹判準）

| 鏡 | 視角 | 結論 | 新缺陷 |
|----|------|------|-------|
| Architect | FSM 三層閉環/版本中性/router 對應/SCG 分類/by-design 解耦 | **OVERALL PASS** | 0（前輪修復全在位、router lint 綠 + 22 tests passed） |
| SA | 輸入域/跨平台/stdin 韌性/檔案 I/O/消毒（26 畸形案例） | **FAIL（1 P3）** | DEF-CLDREV-020 |
| SD | 調用名/死鏈/SLV 一致/職責互斥/版本戳（42 skill） | **PASS（無 P0/P1；1 P2+2 P3）** | DEF-CLDREV-021/022/023 |
| QA | 帳本誠實/測試非空殼/數字一致/floor | **OVERALL PASS** | 0 |

### 2.1 parent 對鏡子的 zero-trust 再驗（不盲信鏡報，逐條親測重現）

- **DEF-CLDREV-020**：親測 `echo '{"tool_name":"Task","tool_input":{"subagent_type":["a","b"]}}' | python .claude/hooks/context_ledger_pre.py` → `AttributeError: 'list' object has no attribute 'strip'` @ `:225`，**exit=1**；dict `agent` 同；字串 control → exit=0 + 合法 JSON。**確鑿**。
- **DEF-CLDREV-021**：`grep scope/anchor_type` 親驗 SLV-008~010 `scope: SCG-1`、SLV-011 `scope: SCG-2`、`anchor_type: ui/api/db/c4`；SKILL.md 統計表「Scope」欄填 ui/api/db/c4（=anchor_type）。**確鑿**（parent 將 SD 鏡 P2 校為實判 P3，理由見帳本：CLI 顯式映射無 runtime 後果）。
- **DEF-CLDREV-022**：`grep -rl '基於.*AISDLC-SDD v0.19' */SKILL.md` = 41；missing 唯一 = test-failure-analyzer。**確鑿**。
- **DEF-CLDREV-023**：`README.md:4` v0.19-SDD vs `:248` 「v0.02 改寫後」。**確鑿**。

## 3. 修復與雙重驗證（全能修復 = parent 就地修）

| 缺陷 | 修復檔案 | 驗證 |
|------|---------|------|
| DEF-CLDREV-020 | `context_ledger_pre.py` type-guard + `test_context_ledger_pre_hook.py` +2 測試（`NonStringSubagentTypeTests`） | `pytest` 12→**14 passed**；受控突變（退 `(_raw_agent or "").strip()`）→ 2 紅 `AttributeError`、`git checkout` 還原→ 2 passed＝**非空殼**；`git diff --stat` 確認修復在位 |
| DEF-CLDREV-021 | `spec-logical-validator/SKILL.md`（統計表 Scope 欄 4 列、CLI scope/anchor_type 註記、L113 filter） | 全 14 列 Scope 欄==yaml `scope`；yaml 零改 |
| DEF-CLDREV-022 | `test-failure-analyzer/SKILL.md` footer +「**基於**: AISDLC-SDD v0.19」 | grep 42/42 有戳；`skill_header_sync --check` OK |
| DEF-CLDREV-023 | `README.md:248`「（v0.02 引入，沿用至 v0.19）」 | 章節標題版本錨點不再與頭部衝突 |

父層 SSOT 鏡像：`sync_exposed_skills.py --write` → 重生 59 檔。

## 4. QA 複審（收斂矩陣，parent 親跑）

```
$ bash scripts/ci-gate.sh   →   EXIT=0
逐軌計數：AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.19:1631 scripts/tests:123
```
- v0.19：1629（floor）+ 2（DEF-CLDREV-020 回歸測試）= **1631**，0 failed ＝ **零退化**。
- scripts:123 不變（新測試落 v0.19 軌，非 scripts/tests 軌）；v0.01:1478 不變（凍結基線未動）。
- SSOT lint：`skill_header_sync --check` OK（對齊 v0.19）／`sync_exposed_skills --check` OK（父層==LATEST 59 檔）／`framework_status_snapshot --check` fresh（仍 42 skill）／router hook 覆蓋 lint 綠。
- FSM/`*.tla` 零變更 → 五軌 TLC 不觸發。

## 5. 結案判定

**Architect / SA / SD / QA 四鏡 OVERALL PASS**（SA/SD 揪出之 DEF-CLDREV-020~023 全 fixed@v0.19 並經 ci-gate exit 0 收斂佐證、突變實證測試非空殼）。臨時審查塊 DEF-CLDREV-020~023 全閉、零 routed 殘留。**v0.19 `.claude` hooks/skills 符合 SDD 與整體系統架構，無需結構性調整**——本輪僅輸入域防護 + 文件一致性 surgical 清償。
