# AutoSDD improving_49 — `.claude` hooks/skills 第七輪四鏡複審（B 軌 Dogfooding）

> **軌道定位**：軌道① **B 軌**（手腳框架 AISLDC_SDD dogfooding）。標的＝最新演化版 `AISDLC_SDD_v0.19` 之 `.claude/`（5 hooks + 42 skills + 兩處 settings.json）對 SDD 與整體系統架構之合規性。
> **下一份**：`AutoSDD_improving_50.md`（按需）。
> **政策延續**：掌舵者既定「就地修 v0.19（非 Copy-on-Evolve 遞版，比照 AGTREV/CLDREV 重審輪不動 EVOLUTION_LOG/CHANGELOG）」。
> **日期**：2026-06-23。**最新框架版＝v0.19**（FRAMEWORK_STATUS.md SSOT）。

---

## 1. 本輪輸入（自上輪繼承）

- 上輪＝`.claude` 第六輪複審（commit 5a8a1ba / improving_48），DEF-CLDREV-024~026 + A6-02 全閉、零 routed 殘留。
- 缺陷帳本 `AutoSDD_Defect_Log.md`：DEF-CLDREV-001~026 全 fixed@v0.19；本輪前無 open/routed 的 .claude 缺陷。
- 基線（上輪結案宣稱，本輪階段一親驗）：v0.19 pytest **1636** / scripts/tests **124** / SLV 規則 **14** / skills **42** / 父層鏡像 **59**。

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit）

parent 親自完成（不憑記憶/文件宣稱）：

| 項目 | 命令 | 實測 |
|------|------|------|
| git 真相 | `git log --oneline` / `git cat-file -t 5a8a1ba` | HEAD=**5a8a1ba**（第六輪已提交）；工作樹乾淨；起始系統提示之 git status 為 commit 前舊快照 |
| ci-gate 基線 | `bash scripts/ci-gate.sh` | **exit 0**；v0.01:1478 / v0.19:**1636** / scripts:**124**（與上輪結案宣稱完全吻合） |
| hooks 親讀 | Read ×5 + 根 router + 2 settings.json | 全部前輪 CLDREV 修復在位、fail-soft 紀律完整 |
| router 映射 | `sdd_hook_router.py` `_HOOK_MAP` | 3 session hook（session_start/pre/post）subprocess 轉發 v0.19 同一支實體檔；兩支 post-commit 未映射＝git-native by-design |
| settings matcher | 根 + v0.19 | PreToolUse 皆含 Task、PostToolUse 皆不含（A6-02 by-design） |

**硬閘**：基線無 failed、未低於上輪 passed（1636==1636）→ 通過，進入階段二。

## 3. 階段二/三：四鏡審查 + 增量修復

派 **Architect / SA / SD / QA 四鏡**主樹並行獨立 zero-trust 審查（標的 tracked 乾淨檔 HEAD=5a8a1ba，合 DEF-24-001「審 tracked 乾淨檔→主樹」判準；無 untracked 新檔故無 worktree 假陰性風險）。結果：

- **Architect**：OVERALL PASS（6 維親驗，零新缺陷）。FSM 三層治理閉環、hooks 版本中性（`grep v0.[0-9]`=0）、根 router 一一對應+fail-safe、嵌套 timeout 30⊃25⊃20 機械鎖、三支柱 SCG 無錯置、Rule 9 絕對禁令全守。
- **SA**：OVERALL PASS（5 維親驗，零新缺陷）。對 5 hook 構造 20+ 種畸形 payload 全 fail-soft exit 0；hub allowlist 預設 deny、SSRF/`file://`/指令注入皆擋；SLV 載入對畸形 yaml 防護完整。前六輪輸入域防護家族（012/020/025/026）無新未涵蓋子路徑。
- **SD**：OVERALL **FAIL**（揪 1 真缺陷）。[DEF-CLDREV-027] P2（三支需求/設計 skill 範本來源死鏈）。SLV 14 條規則逐條對齊零問題、版本戳全量在位、frontmatter 授權無過寬。
- **QA**：OVERALL PASS（零新缺陷）。自跑命令核 v0.19:1636/scripts:124/SLV:14/skills:42 全閉合；抽查 DEF-CLDREV-012~026 共 6 筆全對應磁碟真實修復、測試非空殼；v0.01 凍結基線 0 觸碰。

parent 對 SD 鏡缺陷做 zero-trust 親驗重現（`[ -f ]` 三路徑皆 DEAD）+ 權威慣例核對（core agent + greenfield-flow 全指 `docs_template/core/*`）後，確認為真缺陷，依政策就地修 v0.19。

### <Architecture_Design_Review>（本輪僅改 skill .md 文件，無實質 Python）

1. **架構純潔性**：無新增程式、無 God-object、Thin Facade 不受影響。✅
2. **持久化相容**：無狀態/checkpoint 變更。✅
3. **安全防護網**：無新增指令生成/外呼路徑；CONDITIONAL/allowlist 不受影響。✅
4. **對外 I/O 安全**：無新增 `ToolInvocationPort` 路徑。✅
   → 本輪修復屬純文件 surgical（3 行路徑訂正 + SSOT 鏡像重生），不觸及架構紅線。

### 本輪修復（DEF-CLDREV-027，fixed@v0.19）

| 檔 | 行 | 舊（死鏈） | 新（實存，對齊 core agent） |
|----|----|-----------|---------------------------|
| `.claude/skills/sa-analyst/SKILL.md` | 94 | `docs_template/sdd/requirements/FRD-TEMPLATE.md` | `docs_template/core/frd/FRD_Universal_Template.md` |
| `.claude/skills/pm-planning/SKILL.md` | 49 | `docs_template/sdd/requirements/PRD-TEMPLATE.md` | `docs_template/core/prd/PRD_Universal_Template.md` |
| `.claude/skills/sd-architect/SKILL.md` | 132 | `docs_template/sdd/architecture/SRD-TEMPLATE.md` | `docs_template/core/srd/SRD_Module_Template.md` |

修後跑 `sync_exposed_skills.py --write` 同步父層 SSOT（重生 59 檔），v0.19 + 父層鏡像兩處死鏈字串皆 0 殘留。

## 4. 階段四：CI 平價收斂（零退化驗證矩陣）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 + not-chaos 全綠 | ✅ **exit 0** |
| v0.19 pytest | （ci-gate [1/3]） | ≥ floor 1636 / 0 failed | ✅ **1636**（==floor，零退化） |
| v0.01 凍結基線 | （ci-gate [1/3]） | 不變 + 0 觸碰 | ✅ 1478 / git 證 0 觸碰 |
| 共享 infra | （ci-gate scripts/tests） | 不變 | ✅ **124** |
| skills-ssot | `sync_exposed_skills.py --check` | 父層==LATEST | ✅ 59 檔一致 |
| skill_header | （ci-gate lint） | 對齊 v0.19 | ✅ |
| FRAMEWORK_STATUS | `framework_status_snapshot.py --check` | fresh | ✅ 仍 42 skill |
| router hook 覆蓋 | （ci-gate lint） | event 全可達 | ✅ |
| 五軌 TLC | （hooks/`*.tla` 變更才觸發） | N/A | 本輪零 FSM 變更，不觸發 |

**RTM**：DEF-CLDREV-027（唯一本輪缺陷）→ 三檔路徑訂正 + SSOT 同步 → ci-gate exit 0 收斂佐證 → **全閉**。

## 5. 結論

v0.19 `.claude`（5 hooks + 42 skills + settings.json）經第七輪四鏡 zero-trust 複審：**hooks 程式面與治理閉環零新缺陷（Architect/SA/QA 三鏡 PASS）**；skill 面揪出並就地清償 1 條範本死鏈（DEF-CLDREV-027 P2，SD 鏡）。七輪缺陷數 **5→5→5→3→4→3→1** 持續收斂，hooks 面已連續多輪零程式缺陷、本輪僅餘文件層死鏈，框架 `.claude` 治理層對 SDD 與整體架構之合規性高度成熟。零退化（ci-gate exit 0、v0.19 1636==floor、v0.01 凍結基線 0 觸碰）。
