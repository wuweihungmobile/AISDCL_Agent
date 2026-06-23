# AutoSDD ZeroTrust Audit 50 — `.claude` hooks/skills 第八輪四鏡複審證據

> 對應計畫：`docs/04_planning/AutoSDD_improving_50.md`。日期 2026-06-23。標的 LATEST `AISDLC_SDD_v0.19`。

## 1. 階段一基線（parent 親跑，非文件宣稱）

```
bash scripts/ci-gate.sh → exit 0
逐軌計數：AISDLC_SDD_v0.01:1478  AISDLC_SDD_v0.19:1636  scripts/tests:124
skills：42 目錄（+README/PLAN/TEMPLATE 3 治理 md）= 與 FRAMEWORK_STATUS SSOT 一致
SLV：14 條（rules/SLV-*.yaml）
父層鏡像：59 檔（sync_exposed_skills --check OK）
工作樹乾淨，HEAD=8aa1846
```
硬閘：無 failed、1636==上輪 floor → 通過。

## 2. 四鏡審查結論（主樹並行獨立 zero-trust）

| 鏡 | 結論 | 維度數 | 缺陷 |
|----|------|--------|------|
| Architect | OVERALL PASS | 6 | 0（1 advisory：timeout 不變量測試強化） |
| SD | OVERALL PASS | 6 | 0（DEF-CLDREV-027 複核真在位、8/8 範本路徑實存） |
| QA | OVERALL PASS | 5 | 0（基線 1636/124/14/42/59 全閉合、抽 6 筆磁碟真實、v0.01 0 觸碰） |
| SA | PASS-with-findings | 5 | **3（F-01 P2 / F-03 P3 / F-02 P3）** |

## 3. parent zero-trust 親驗重現（修復前）

### F-01（DEF-CLDREV-028）路徑注入
`scratchpad/verify_f01.py` 實測：
```
'0.19'                      -> inside_AISDLC_SDD=True   is_file=True   （合法）
'0.19/../../../../Windows'  -> inside_AISDLC_SDD=False  is_file=False  resolved=D:\Windows\.claude\hooks\session_start.py（逃逸！）
'../../../etc'              -> inside_AISDLC_SDD=False  resolved=...\AISDLC_SDD\etc\...（逃逸）
'0.18'                      -> inside_AISDLC_SDD=True   is_file=True   （可成功指向任意版本實體 hook）
```
證實：`_normalize_version` 不擋 `../`/絕對路徑，唯一閘門 `is_file()`，逃逸後若植入檔即 exec → 路徑注入→潛在 RCE。

### F-03（DEF-CLDREV-029）守門繞過
Read `context_ledger_pre.py:255` 證 `tool = inp.get("tool_name","")` 未 `isinstance(str)` 正規化（緊鄰 :257-258 `tool_input` 已正規化，不對稱）；非字串 → :283 `assert_tool_allowed` TypeError → :287 寬接 → warn-pass 繞過守門。

### F-02（DEF-CLDREV-030）yaml 深防禦
Read `hub_sync.py:141/219/…` 證 `safe_load`（已擋 `!!python/object`）無 alias/深度上限；`hub-registry.yaml:37 allowed_endpoints: []` 證 deny-by-default 零外部拉取。判 scope 外（框架本體）routed。

## 4. 修復與非空殼突變實證

| DEF | 修復 | 突變實證 |
|-----|------|---------|
| 028 | router 白名單 `\d+\.\d+` + `is_relative_to` 邊界斷言 | 白名單→`if False`：`test_malicious_version_not_routed` 轉紅；**附帶實證邊界斷言接管**（印「解析逃逸」）；還原後 3 passed |
| 029 | `if not isinstance(tool, str): tool=""` | 移除護欄：`NonStringToolNameTests` 2 紅（spy 收到 list 而非 `""`）；還原後綠 |

## 5. 階段四收斂（parent 親跑，修復後）

```
bash scripts/ci-gate.sh → exit 0
逐軌計數：AISDLC_SDD_v0.01:1478  AISDLC_SDD_v0.19:1638  scripts/tests:127
  v0.19  1636 → 1638（+2 NonStringToolNameTests，0 failed）
  scripts 124 → 127（+3 test_router_version_path_safety）
SSOT 三 lint 全綠：skills-ssot 59 檔==LATEST / skill_header 對齊 v0.19 / framework_status fresh 仍 42 skill
router hook 覆蓋 lint 綠
git status：v0.01 凍結基線 0 變更
FSM/*.tla 零變更 → 五軌 TLC 不觸發
```

## 6. 結論

零退化硬閘成立（1638≥1636、127≥124、v0.01 不變）。DEF-CLDREV-028/029 全閉、030 routed（框架本體 scope 外 RFC）。Architect/SD/QA 三鏡 PASS、SA 鏡 2 真缺陷+1 routed 修復後收斂。本輪首次在 hooks 程式面清償安全級（P2 路徑注入）缺陷。
