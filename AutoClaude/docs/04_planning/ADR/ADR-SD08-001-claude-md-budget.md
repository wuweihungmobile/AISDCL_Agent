# ADR-SD08-001：CLAUDE.md 文件治理 — ≤ 400 行 + Architecture Snapshot SSOT + 滾動窗口 N=2

| 項目 | 內容 |
|------|------|
| 狀態 | **APPROVED v1.1（PM 形式核准 / 場景 A 個人開發 dev 自核 2026-05-26）** |
| 建立日期 | 2026-05-18 |
| v1.1 升版日期 | **2026-05-26（SD_09 W3 R22 後，§8 Postscript 升格 §9 結構性決議）** |
| 對應 PM 拍板 | SD_08 PM #1（≤ 400 行 + Snapshot SSOT + 滾動窗口 N=2）+ SD_09 W3 R22 PM #ext（W 期間骨架先行 SOP 升格）|
| 提案人 | Architect / SA / SD / QA（四方整合專家共識）|
| 核准日期 | 2026-05-18（v1.0 W0 T0-ADR1）/ 2026-05-26（v1.1 SD_09 W3 R22）|

---

## 1. 背景

- CLAUDE.md 現況：**712 行**（SD_03~SD_07 各 sprint 摘要佔 ~600 行）
- 三方共識（Architect/SA）：**(b) ≤ 400 行**，比 (a) ≤ 350 強剪保留 SD_06+SD_07 完整摘要，比 (c) ≤ 500 弱剪可制止文件膨脹
- 退化風險警示（Architect）：⚠️ 無 CI 強制 + Snapshot freshness 檢查，6 個月後仍會回到 700+ 行

## 2. 決議

### 2.1 CLAUDE.md 結構約束（≤ 400 行）

CLAUDE.md 必留三大區段（任一不可下沉至 sprint_history.md）：
1. **規範性內容**（語言/開發循環/文檔目錄/Agent 載入）
2. **核心目錄結構 + 模型欄位 + CLI/測試執行**
3. **[Architecture Snapshot] SSOT 區段**（新增）+ **最近 2 個 sprint 摘要**（滾動窗口 N=2，目前為 SD_06 + SD_07）

### 2.2 [Architecture Snapshot] SSOT 設計

新增區段內容由 `tools/snapshot_sync.py` 從程式碼自動回填：

```markdown
## [Architecture Snapshot] — 自動同步（最後更新：YYYY-MM-DD）

### LOC Tiers（ADR-SD07-001）
| Tier | Budget | 範圍 |
|------|--------|------|
| data | ≤ 150 | autoclaude/models/ |
| plugin_entry | ≤ 250 | autoclaude/plugins/*.py |
| strategy | ≤ 300 | autoclaude/core/services/*/ |
| adapter | ≤ 400 | autoclaude/infra/adapters/ |
| service | ≤ 500 | autoclaude/execution/steps_orchestrator/ |
| contract | ≤ 400 | autoclaude/core/ports/ |
| ABSOLUTE | ≤ 750 | 任何檔案 |

### importlinter Rules（目前 6 kept + W4 將升 7 kept）
1. plugin-isolation
2. core-purity
3. runner-internals-isolation
4. brain-executor-isolation
5. executor-brain-isolation
6. runner-no-checkpoint-logic
7. (W4 新增) plugin-no-utils-observability-direct-import

### Plugin 列表（14 個，按 priority）
[由 tools/snapshot_sync.py 從 autoclaude/core/wiring.py `_REGISTER_ORDER` 自動讀取]

### Port 列表（7 個，含 SD_08 W4 新增）
[由 tools/snapshot_sync.py 從 autoclaude/core/ports/ 自動讀取]

### DAL 三後端 mode 矩陣
[由 tools/snapshot_sync.py 從 autoclaude/infra/repositories/factory.py 自動讀取]
```

### 2.3 滾動窗口 N=2 規則

- CLAUDE.md 僅保留**最近 2 個 sprint 摘要**（目前：SD_06 + SD_07；SD_08 完成後：SD_07 + SD_08）
- 更早的 sprint 一律 link 至 `docs/05_development/sprint_history.md`
- 每次 Sprint G6 通過時，由 W6 收尾任務同步將最舊 sprint 下沉至 sprint_history.md（W0 工具支援）

### 2.4 sprint_history.md 結構（交叉索引）

```
docs/05_development/sprint_history.md
├── 主目錄：依 sprint 編號（時間線敘事）
│   ├── SD_Improving_03（Phase 4 Facade 切換）
│   ├── SD_Improving_04（god-object 拆解）
│   ├── SD_Improving_05（Counter SSOT + TokenGuard 下沉 + Mutation v2）
│   ├── SD_Improving_06（PG 三層 + Brain/Executor 分工）
│   ├── SD_Improving_07（LOC 政策 + 肥胖檔案二度拆 + 6 議題 e2e）
│   └── SD_Improving_08（文件治理 + 可觀測性 + mutation/perf baseline）
└── 議題索引表（reverse-link）
    ├── Plugin 化 → SD_05 W4 / SD_06 W6 / SD_07 W5
    ├── DAL → SD_05 / SD_06 W3
    ├── PG production → SD_06 W3 / SD_08 W5 / SD_09
    ├── 可觀測性 → SD_08 W4
    ├── LOC 政策 → SD_07 W0 / SD_07 W5
    └── ...
```

## 3. 工具升級

### 3.1 tools/check_loc_budget.py 加入 CLAUDE.md 規則

於既有 `LOC_TIERS` 中新增專屬 entry：

```python
# tools/check_loc_budget.py（W0 升級）
SPECIAL_FILES = {
    "CLAUDE.md": 400,  # ADR-SD08-001 §2.1
}

def check_special_files(repo_root: Path) -> list[Violation]:
    violations = []
    for file_path, max_lines in SPECIAL_FILES.items():
        f = repo_root / file_path
        if not f.exists():
            continue
        actual = count_lines(f)  # wc -l 等價
        if actual > max_lines:
            violations.append(Violation(
                file=str(f),
                tier="special",
                actual=actual,
                budget=max_lines,
                reason="CLAUDE.md 文件治理（ADR-SD08-001）"
            ))
    return violations
```

### 3.2 tools/snapshot_sync.py（新建，W0 落地）

```python
# 從程式碼自動回填 [Architecture Snapshot] 區段
# 觸發：(1) pre-commit hook / (2) CI 7 天未同步告警
# 輸出：CLAUDE.md 中 [Architecture Snapshot] 區段內容 + 更新 "最後更新" 日期
```

## 4. CI 強制（claude-md-budget job 草稿）

於 `.github/workflows/ci.yml` 新增 job（與 test job 平行）：

```yaml
claude-md-budget:
  name: CLAUDE.md Budget + Snapshot Freshness
  runs-on: ubuntu-latest
  timeout-minutes: 3
  steps:
    - name: Checkout
      uses: actions/checkout@v4
      with:
        fetch-depth: 0  # 需要 git log 拿 Snapshot 區段最後變更日

    - name: Set up Python 3.11
      uses: actions/setup-python@v5
      with:
        python-version: "3.11"

    - name: Check CLAUDE.md ≤ 400 lines
      run: |
        LINES=$(wc -l < CLAUDE.md)
        if [ "$LINES" -gt 400 ]; then
          echo "::error::CLAUDE.md=$LINES lines > 400 (ADR-SD08-001)"
          exit 1
        fi
        echo "::notice::CLAUDE.md=$LINES lines ≤ 400 ✅"

    - name: Check Snapshot freshness ≤ 7 days
      run: |
        LAST_SYNC=$(git log -1 --format="%at" -- CLAUDE.md | head -1)
        NOW=$(date +%s)
        DIFF_DAYS=$(( (NOW - LAST_SYNC) / 86400 ))
        if [ "$DIFF_DAYS" -gt 7 ]; then
          echo "::warning::Architecture Snapshot 區段已 $DIFF_DAYS 天未同步（>7 天告警）；請執行 python tools/snapshot_sync.py"
        fi

    - name: Verify snapshot_sync.py reproducible（dry-run）
      run: |
        python tools/snapshot_sync.py --check  # exit 1 if Snapshot 區段與真實程式碼漂移
```

## 5. 落地 Checklist（W0 task breakdown）

```
[  ] T0-A1 升級 tools/check_loc_budget.py 加入 SPECIAL_FILES = {"CLAUDE.md": 400}
[  ] T0-A2 新建 tools/snapshot_sync.py（從 wiring.py / ports/ / factory.py 自動回填）
[  ] T0-A3 .github/workflows/ci.yml 新增 claude-md-budget job
[  ] T0-A4 CLAUDE.md 加入 [Architecture Snapshot] 區段 + 頂端「快速導覽」3 行
[  ] T0-A5 sprint_history.md 骨架建立（依 §2.4 交叉索引）+ SD_03~SD_05 完整下沉
[  ] T0-A6 補 tests/contract/test_claude_md_budget.py（≥ 3 case：wc-l / Snapshot 區段格式 / 必留章節存在）
```

## 6. 退化風險緩解（連動 R-SD08-A-1 / R-SD08-E-1；v1.1 加入 §9 雙模式並行新風險）

| 風險 | 緩解 |
|------|------|
| 6 個月後再次膨脹 700+ 行 | claude-md-budget CI 強制 + LOC budget 工具支援 |
| Snapshot 區段與真實程式碼漂移 | 7 天 freshness 告警 + pre-commit 觸發 snapshot_sync.py |
| 新人 onboarding context 缺失 | 頂端「快速導覽」3 行指引 + sprint_history.md 交叉索引 + Sprint_Round_Recording_SOP（v1.1）|
| **（v1.1 新增）dev 跑 scaffold 但忘記 CLAUDE.md 加 H3** | sprint_history.md 多 §1.X 但 CLAUDE.md 缺 H3 為「合法滾出狀態」（N=2 規則允許），不阻擋 — 由 G6 末檢核清單 + Sprint_Round_Recording_SOP §2.2 onboarding 兜底 |
| **（v1.1 新增）dev 在 CLAUDE.md 加 H3 但忘跑 scaffold** | `snapshot_sync.py --check` 自動偵測 CLAUDE.md 有新 SD_NN 但 sprint_history.md 缺對應 §1.X 骨架時 exit 1（CI 阻斷）+ `test_each_claude_md_nn_has_history_section` contract test 雙保險 |
| **（v1.1 新增）CLAUDE.md 出現重複 ### SD_Improving_NN H3** | `test_no_duplicate_sprint_h3_in_claude_md` contract test + `snapshot_sync.check_sprint_skeleton_alignment` Counter 偵測（R23 audit P2-4 修復；set 去重會吃掉重複導致誤判）|
| **（v1.1 新增）單行 ≤ 800 限制以 codepoint 計，CJK 字元 byte 數 ≈ 3× codepoint** | 設計選擇：以 codepoint（≈ 視覺字元數）計，符合 markdown 可讀性語義；byte 數約上限 ~2,400（CJK 內容）。test_claude_md_no_long_lines.py docstring 明示此設計選擇 |

## 7. 簽核

| 角色 | 狀態 | 日期 |
|------|------|------|
| Architect | ✅ 共識（議題 2 推薦 b）| 2026-05-18 |
| SA | ✅ 共識（議題 2 推薦 b）| 2026-05-18 |
| PM | ✅ 形式核准（場景 A 個人開發 dev 自核）| 2026-05-18 |

---

**相關文件**：
- [SD_Improving_08.md](../SD_Improving_08.md) v1.0 §6 PM 拍板 #1
- [ADR-SD07-001-loc-policy.md](ADR-SD07-001-loc-policy.md) v1.0 — LOC 分級政策（沿用）

---

## 8. Postscript（SD_09 W3 R18 — 已升格為 §9 結構性決議，保留作歷史脈絡）

**觸發**：SD_09 W3 Round 18 後 CLAUDE.md 累積至 400 行；line 198 SD_09 R11-18 累積敘事 2,397 字元。四方整合專家評估採方案 E（A+B 混合）。**v1.0 階段 §8 為附註形式；R22 後正式升格 §9 結構性決議，本段保留作歷史脈絡。**

---

## 9. W 期間骨架先行 SOP（v1.1 結構性決議，2026-05-26）

### 9.1 核心決議

**SD_10 及之後所有 Sprint 啟動時，W 期間 Round 累積敘事一律直接寫入 `docs/05_development/sprint_history.md §1.N`，不再走 CLAUDE.md → G6 下沉路徑。** CLAUDE.md 該 sprint H3 段永遠保持「摘要 + 連結」**≤ 15 行**。

此決議取代 v1.0 §2.3 原「每 G6 下沉」單軌規則，調和為**雙模式並行**：
- **模式 A（W 期間骨架先行 — 新主軸）**：sprint_history.md §1.N 骨架於 W0 立即建立；所有 W 期間 Round / audit 紀錄直接寫入；CLAUDE.md 該 sprint H3 ≤ 15 行
- **模式 B（G6 末滾動下沉 — N=2 視窗維持）**：N=2 滾動視窗仍生效；G6 通過時，最舊 sprint 的 CLAUDE.md H3 段移除（已直寫於 sprint_history.md 故無需複製，僅替換為 link）+ Snapshot 區段同步

### 9.2 五層抗膨脹保險（contract + hook 雙軌）

| # | 保險 | 對應檔案 | 阻斷層級 |
|---|------|---------|---------|
| 1 | CLAUDE.md ≤ 400 行 | `tests/contract/test_claude_md_budget.py` + `tools/hooks/claude_md_freshness.py`（Stop, rc=2 BLOCK）+ `tools/hooks/loc_budget_check.py`（PostToolUse, rc=2 BLOCK） | CI + Stop hook + PostToolUse hook |
| 2 | per-H2 區段預算 + H3 sprint 段 ≤ 15 行（regex 自動覆蓋 `^### SD_Improving_\d+`） | `tests/contract/test_claude_md_section_budget.py` | CI |
| 3 | 單行 ≤ 800 字元（擋「累積敘事 1 line」反模式） | `tests/contract/test_claude_md_no_long_lines.py` | CI |
| 4 | SSOT 雙向連結驗證（Nightly Discipline + Sprint H3 對應 sprint_history.md §1.N） | `tests/contract/test_nightly_discipline_link.py` + `tests/contract/test_claude_md_sprint_anchor.py`（**新增 R22**） | CI |
| 5 | 380 預警 + W 期間骨架自動產生 | `tools/hooks/loc_budget_check.py`（≥ 380 WARN rc=1）+ `tools/scaffold_sprint_section.py`（**新增 R22**，Sprint W0 第一步） | PostToolUse hook + 一次性 CLI |

### 9.3 SOP 與 onboarding

- **SOP 文件**：[docs/05_development/Sprint_Round_Recording_SOP.md](../../05_development/Sprint_Round_Recording_SOP.md)（R22 新建，≤ 120 行；R23 audit P1-2 修正聲稱 80→120 以符實際 106 行）— SD_10+ Sprint W0 第一步操作流程 + 反例 + 範本
- **CLAUDE.md inline 規範**：§快速導覽末新增 1 行 SOP link，dev 30 秒內可定位
- **sprint_history.md §3.1 修訂**：拆兩段（(a) W 期間骨架直寫；(b) G6 下沉僅做「CLAUDE.md 段落改 link + N=2 滾出」），與 §9.1 雙模式對齊
- **snapshot_sync.py --check 擴充**：當 CLAUDE.md 出現新 `### SD_Improving_NN` 而 sprint_history.md 缺對應 §1.N 骨架時 exit 1（CI 兜底）

### 9.4 R22 落地實測

- CLAUDE.md 383 行（buffer 17）；snapshot sync OK；ADR-SD08-001 升 v1.1
- pytest 預期 2,598 → ≥ 2,601 passed（+3 新 contract case：sprint anchor 雙向 / H2 default budget 反向 / snapshot --check 骨架告警）
- importlinter 維持 7 kept / LOC=0
- 新增檔案：`Sprint_Round_Recording_SOP.md` / `test_claude_md_sprint_anchor.py` / `tools/scaffold_sprint_section.py`
- 修訂檔案：`ADR-SD08-001`（本檔升 v1.1）/ `sprint_history.md §3.1` / `CLAUDE.md`（+1 行 SOP link）/ `tools/snapshot_sync.py`（--check 擴充）/ `tests/contract/test_claude_md_section_budget.py`（補 H2 default budget 反向驗證）

### 9.5 簽核（v1.1）

| 角色 | 狀態 | 日期 |
|------|------|------|
| Architect | ✅ 整合專家共識（§9 雙模式並行設計合理）| 2026-05-26 |
| SA | ✅ 整合專家共識（SOP onboarding 路徑完整）| 2026-05-26 |
| SD | ✅ 整合專家共識（snapshot_sync 擴充技術可行）| 2026-05-26 |
| QA | ✅ 整合專家共識（5 層抗膨脹保險覆蓋 + 反向驗證補齊）| 2026-05-26 |
| PM | ✅ 形式核准（場景 A 個人開發 dev 自核）| 2026-05-26 |
