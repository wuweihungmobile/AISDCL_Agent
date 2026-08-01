# AutoSDD ZeroTrust Audit 48 — `.claude` hooks/skills 第六輪四鏡複審證據

> 對應 `docs/04_planning/AutoSDD_improving_48.md`。標的＝`AISDLC_SDD_v0.19/.claude/`（5 hooks + 42 skills + settings.json）。日期 2026-06-23。

## 1. 階段一基線（parent 親跑，非文件宣稱）

```
$ bash scripts/ci-gate.sh   # 改動前
✅ 本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.19）
   逐軌計數：AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.19:1631 scripts/tests:123
```

親讀 5 hooks + 根 router + 兩處 settings.json：前輪 DEF-CLDREV-001~023 修復全部在位（pre/post MAX_CONTEXT 三類輸入域防護、subagent_type 非字串防護、Windows ThreadPoolExecutor timeout、PreToolUse matcher 含 Task）。

## 2. 四鏡發現 + parent zero-trust 親驗重現

### Architect 鏡（OVERALL PASS）
- **[A6-01]→DEF-CLDREV-026 P2**：parent 親驗常數——`sdd_hook_router.py:63 _CHILD_TIMEOUT["SessionStart"]=25.0`、`hub-registry.yaml:25 timeout_seconds: 30`、`hub_sync.py:408-409` 讀該值。30>25 屬實；`allowed_endpoints: []`（:33）預設不觸發＝條件式。**確認真缺陷**。
- **[A6-02] P3**：兩處 settings PostToolUse matcher 皆無 Task、PreToolUse 皆含 Task。by-design 但缺註記。**確認防退化價值**。

### SA 鏡（OVERALL FAIL → 揪 DEF-CLDREV-025 P3）
parent 親測（實際跑 hook）：
```
echo '[1,2,3]' | python .claude/hooks/context_ledger_pre.py
  → AttributeError 'list' object has no attribute 'get'  (context_ledger_pre.py:249)  exit=1
echo '{"tool_name":"Read","tool_input":[1,2,3]}' | ...pre.py   → :252 AttributeError  exit=1
echo '{"tool_name":"Read","tool_input":"abc"}'  | ...pre.py    → :252 AttributeError  exit=1
echo '[1,2,3]' | ...post.py                                    → :123 AttributeError  exit=1
echo '{"tool_name":"Read","tool_input":[1,2,3],"tool_response":"x"}' | ...post.py → :126  exit=1
echo '{"tool_name":"Read","tool_input":{"file_path":"x"}}' | ...pre.py → exit=0（正常對照）
```
**確認真缺陷**（與 DEF-CLDREV-012/020 同類輸入域、前輪測試未涵蓋 `tool_input` 本身/頂層非 dict）。

### SD 鏡（OVERALL FAIL → 揪 DEF-CLDREV-024 P3）
parent 親驗：
```
SKILL.md:224  | SLV-008 (proposed) | ... | AC-015-1 缺穩態條件 | ...
SKILL.md:155  | [SLV-008] | UI mockup ↔ FRD AC 錨點一致 | ... anchor_type=ui
$ grep ^name: rules/SLV-007.yaml → 時序語義矛盾（N+1 vs N 無穩態條件）
$ grep ^name: rules/SLV-008.yaml → UI mockup 與 FRD AC 不一致
```
「缺穩態條件」屬 SLV-007 非 SLV-008，範例自相矛盾。**確認真缺陷**（純文件、引擎動態掃 yaml 不讀範例、不影響行為）。

### QA 鏡（OVERALL PASS，零新缺陷）
親 collect/親跑：v0.19 pytest 1631 passed / 4 skipped / 34 chaos deselected（1669 collect 閉合）；scripts/tests 123；SLV 35；skills 42；父層鏡像 59。抽查 DEF-CLDREV-012~023 共 6 筆 fixed 證據全對應磁碟、測試斷言非空殼、帳本「39 SLV」殘留 2 命中皆在缺陷描述引述文字內（非活躍數字）。

## 3. 修復 + 雙重驗證（突變實證非空殼）

```
# DEF-CLDREV-025 修復後親驗（畸形 stdin 應 exit=0）
pre/post × {頂層 list, tool_input list, tool_input str} → 全 exit=0
$ pytest test_context_ledger_pre_hook.py test_context_ledger_post_hook.py -q → 24 passed
# 突變：暫退 pre tool_input isinstance 護欄 → MalformedPayloadTests 2 failed（AttributeError :259）；還原綠

# DEF-CLDREV-026 不變量鎖 + 突變
$ pytest scripts/tests/test_session_start_hub_timeout_budget.py -q → 1 passed
  突變 hub 20→30 → 1 failed；還原 → 1 passed
```

## 4. 最終收斂（parent 親跑，2026-06-23）

```
$ bash scripts/ci-gate.sh   # 修復後
✅ 本機 CI 閘門全數通過（版本：AISDLC_SDD_v0.01 AISDLC_SDD_v0.19）
   逐軌計數：AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.19:1636 scripts/tests:124
[skills-ssot] OK：父層 .claude/skills == LATEST(AISDLC_SDD_v0.19)（59 檔一致）
[skill-header] OK：LATEST 框架版本戳全對齊 v0.19
✅ FRAMEWORK_STATUS.md 新鮮（仍 42 skill）
✅ router hook 覆蓋 lint：PostToolUse/PreToolUse/SessionStart 全可達
```

- v0.19：1631→**1636**（+5 MalformedPayload 回歸測試〔pre 3 + post 2〕，0 failed＝零退化）
- scripts/tests：123→**124**（+1 hub timeout 不變量鎖）
- `git status`：8 改動檔，**0 個 v0.01** 凍結基線變更（Copy-on-Evolve 邊界守住）
- FSM/`*.tla` 零變更 → 不觸發五軌 TLC（Rule 9.18.1 不啟動）

## 5. 裁定

**四鏡 OVERALL PASS**。臨時審查塊 DEF-CLDREV-024~026 + A6-02 全閉、零 routed 殘留。標的 `.claude/` 整體合乎 SDD 與系統架構，無 P0/P1、無需結構性重構。
