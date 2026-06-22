# AutoSDD improving_48 — `.claude` hooks/skills 第六輪四鏡複審（B 軌 Dogfooding）

> **軌道定位**：軌道① **B 軌**（手腳框架 AISLDC_SDD dogfooding）。標的＝最新演化版 `AISDLC_SDD_v0.19` 之 `.claude/`（5 hooks + 42 skills + 兩處 settings.json）對 SDD 與整體系統架構之合規性。
> **下一份**：`AutoSDD_improving_49.md`（按需）。
> **政策延續**：掌舵者既定「就地修 v0.19（非 Copy-on-Evolve 遞版，比照 AGTREV/CLDREV 重審輪不動 EVOLUTION_LOG/CHANGELOG）」。
> **日期**：2026-06-23。**最新框架版＝v0.19**（FRAMEWORK_STATUS.md SSOT）。

---

## 1. 本輪輸入（自上輪繼承）

- 上輪＝`.claude` 第五輪複審（commit c4ae6c3 / improving_47），DEF-CLDREV-020~023 全閉、零 routed 殘留。
- 缺陷帳本 `AutoSDD_Defect_Log.md`：DEF-CLDREV-001~023 全 fixed@v0.19；本輪前無 open/routed 的 .claude 缺陷。
- 基線（上輪結案宣稱，本輪階段一親驗）：v0.19 pytest **1631** / scripts/tests **123** / SLV 測試 **35** / skills **42** / 父層鏡像 **59**。

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit）

parent 親自完成（不憑記憶/文件宣稱）：

| 項目 | 命令 | 實測 |
|------|------|------|
| ci-gate 基線 | `bash scripts/ci-gate.sh` | **exit 0**；v0.01:1478 / v0.19:1631 / scripts:123 |
| hooks 親讀 | Read ×5 + router + 2 settings.json | 全部前輪 CLDREV 修復在位、fail-soft 紀律完整 |
| router 映射 | `_HOOK_MAP` | 3 session hook（session_start/pre/post）；兩支 post-commit 未映射＝by-design |
| settings matcher | 根 + v0.19 | PreToolUse 皆含 Task、PostToolUse 皆不含（DEF-CLDREV-017 在位） |

**硬閘**：基線無 failed、未低於上輪 passed → 通過，進入階段二。

## 3. 階段二/三：四鏡審查 + 增量修復設計

派 **Architect / SA / SD / QA 四鏡**主樹並行獨立 zero-trust 審查（標的 tracked 乾淨檔，合 DEF-24-001 主樹派發判準）。結果：

- **Architect**：OVERALL PASS（7 維親驗）。揪 [A6-01] P2（hub 30s > router 25s 嵌套 timeout 倒置）、[A6-02] P3（PostToolUse Task 排除缺 by-design 註記）。
- **SA**：OVERALL FAIL（揪 1 真缺陷）。[SA-NEW-01] P3（畸形 stdin 頂層/tool_input 非 dict → pre+post crash）。
- **SD**：OVERALL FAIL（揪 1 真缺陷）。[DEF-CLDREV-024] P3（SKILL.md:224 範例 SLV-008 語義錯置）。
- **QA**：OVERALL PASS（零新缺陷）。複核前輪修復真實、帳本數字閉合、測試非空殼。

parent 對每筆做 zero-trust 親驗重現（見 ZeroTrust_Audit_48 §2）後，確認全為真缺陷，依政策就地修 v0.19。

### <Architecture_Design_Review>（寫實質 Python 前自我驗證）

1. **架構純潔性**：修復皆 surgical（hook `main()` 型別正規化 4 行、SKILL.md 1 列、config 1 值、docstring 註記、+6 測試），無 God-object、不動 Thin Facade、不改 FSM/`*.tla`。
2. **持久化相容**：未觸 PlaybookCheckpoint / DAL（本輪標的為 AISLDC_SDD hooks，非 AutoClaude DAL）；hook ledger 寫入路徑不變。
3. **安全防護網**：DEF-CLDREV-025 屬輸入域健壯化（拒畸形 payload 致 crash），強化而非弱化守門；CONDITIONAL/對外 I/O 安全路徑未新增。
4. **對外 I/O 安全**：DEF-CLDREV-026 反而**收緊**對外 git pull 的 timeout 預算（20s），且不新增任何 `ToolInvocationPort` 外呼路徑；hub allowlist（`allowed_endpoints`）預設 deny 機制不動。

### 本輪修復（W 項）

| 缺陷 | 修法 | LOC 落點 | 契約影響 |
|------|------|---------|---------|
| DEF-CLDREV-024 | SKILL.md:224 範例改 SLV-008 真實 UI 錨點語義 | 文件，無 LOC 預算 | 無（引擎不讀範例） |
| DEF-CLDREV-025 | pre+post `main()` 補 inp/tool_input dict 正規化 + 5 測試 | hook 各 +4 行，遠低於上限 | 無 importlinter 影響（hook 非 plugin/adapter） |
| DEF-CLDREV-026 | hub-registry pull timeout 30→20 + scripts/tests 不變量鎖 | config 1 值 + 新測試 | 無 |
| A6-02 | post hook docstring by-design 註記 | 註解 | 無 |

## 4. 階段四：CI 平價收斂（零退化驗證矩陣）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 + 各軌 not-chaos 全綠 | ✅ exit 0 |
| 逐軌 pytest | （同上） | v0.19 ≥ floor 1631、0 failed | ✅ v0.19:**1636**（+5）/ v0.01:1478 |
| scripts/tests | （同上） | ≥ floor 123 | ✅ **124**（+1） |
| skills SSOT | `sync_exposed_skills.py --check` | 父層==LATEST 59 檔 | ✅ |
| skill 版本戳 | `skill_header_sync.py --check` | 全對齊 v0.19 | ✅ |
| FRAMEWORK_STATUS | `framework_status_snapshot.py --check` | fresh 仍 42 skill | ✅ |
| router hook 覆蓋 | router lint | event 全可達 | ✅ |
| 五軌 TLC | — | 僅 FSM 變更時 | 不觸發（FSM/`*.tla` 零變更） |

**零退化成立**：v0.19 1631→1636（只增 5 回歸測試）、scripts 123→124、0 failed；git status 證 0 個 v0.01 凍結基線變更。

## 5. RTM（需求追溯矩陣）

| 需求（缺陷） | 修復構件（file:line） | 驗證構件 | 狀態 |
|------|------|------|------|
| DEF-CLDREV-024 | `spec-logical-validator/SKILL.md:224`（+ 父層鏡像） | SD 鏡親驗 + grep SLV-007/008.yaml 語義 | ✅ fixed |
| DEF-CLDREV-025 | `context_ledger_pre.py:~251`、`context_ledger_post.py:~123` | `test_context_ledger_pre_hook.py::MalformedPayloadTests`(3)、`test_context_ledger_post_hook.py::MalformedPayloadTests`(2) + 突變實證 | ✅ fixed |
| DEF-CLDREV-026 | `knowledge/hub-registry.yaml:25`（30→20） | `scripts/tests/test_session_start_hub_timeout_budget.py` + 突變實證 | ✅ fixed |
| A6-02 | `context_ledger_post.py` docstring | Architect 鏡建議、防退化 | ✅ fixed |

## 6. 結論

本輪四鏡複審揪出並就地清償 3 真缺陷（1 P2 + 2 P3）+ 1 防退化註記，全 fixed@v0.19，零退化（ci-gate exit 0）。**標的 `.claude/`（5 hooks + 42 skills + settings.json）整體合乎 SDD 治理閉環與系統架構，無 P0/P1 結構性問題、無需架構重構。** 第六輪相較前五輪缺陷數續降（5→5→5→3→4→3），收斂趨勢明確：hooks 程式面（版本中性、輸入域、跨平台、嵌套 timeout）與 skills 文件面（調用名、死鏈、版本戳、SLV 一致性）已高度收斂，殘留多為條件式/文件邊角。

> **誠實揭露（沿用前輪）**：DEF-CLDREV-026 的 hub timeout 倒置僅在使用者啟用 Hub（填 `allowed_endpoints`）後可重現，預設配置不觸發；本輪已以機械不變量鎖根除常數漂移，惟「實際慢 pull 撞 router 上限」之 E2E 行為待真實啟用 Hub 之 session 觀察。DEF-CLDREV-025 已單元驗證 hook 收畸形 payload 不 crash；CC 實際是否會傳非 dict payload 屬環境行為，非本環境可 E2E 驗——屬防禦性健壯化，非已觀察到的線上故障。
