# AutoSDD improving_69 — SDK 整合收尾：can_use_tool production 接線 + 活體 A/B 去風險

> **軌道**：① 整合迭代（範本驅動）。**本輪柱位**：**C/A 軌**（指揮官 AutoClaude 自身能力 × 整合端點）。
> **承接**：improving_68（commit fda0caa）的唯一 PENDING＝R-68-7 活體 A/B。
> **下一份**：improving_70。
> **日期**：2026-06-25 ｜ **driver**：掌舵者 AskUserQuestion 裁「小規模真跑 A/B + W-69-2（W-69-3 延後）」。

---

## 1. 本輪範圍（掌舵者拍板）

| W 項 | 內容 | 狀態 |
|------|------|------|
| **W-69-1** | 活體 A/B（R-68-7 去風險）— 真正以 SDK 驅動 Claude Code 端到端，實證連線/事件映射/act-first 真值/can_use_tool deny | ✅ 完成（決定性活體證據） |
| **W-69-2** | `can_use_tool` production 接線 — config 驅動泛型工具 allowlist predicate（deny-by-default、fail-closed） | ✅ 完成（16 單元測 + 活體驗證） |
| ~~W-69-3~~ | act-first warn→硬擋 | **延後 improving_70**（掌舵者裁） |

**環境前提變化（階段一 (f) 紀律實測）**：本輪沙箱**外網通**（api.anthropic.com HTTP 405＝可達、github 200）+ `~/.claude/.credentials.json` 存在（訂閱 OAuth）+ `claude` CLI 在 PATH + `claude-agent-sdk 0.2.110` 已裝 → R-68-7 活體 A/B 客觀條件具備（上輪 improving_68 因沙箱無外網據實標 PENDING）。

---

## 2. 階段一：零信任重偵察（硬閘通過，全部實測）

| 檢查 | 實測 | floor 對比 |
|------|------|-----------|
| AutoClaude 全套 pytest | **3345 passed / 122 skipped / 0 failed**（72s） | = 上輪 floor 3345，硬閘未觸發 |
| lint-imports | 8 kept / 0 broken（196 files / 492 deps） | 持平 |
| LOC 分級 | violations=0（total 19344 / cap 20438） | 過 |
| snapshot --check | FRESH | 過 |
| improving_68 構件 | SdkExecutorAdapter（288 行）+ 12 mock 測 + ExecutorConfig 預設 pty + .importlinter 雙向隔離 + pyproject [sdk] — 全部真實存在且被覆蓋 | 收斂屬實 |
| SDD ci-gate | exit 0（v0.01:1478 / v0.26:1665 / scripts:129，arch_fitness fail=0） | 全綠 |
| SDD LATEST | v0.26 | 持平 |
| 缺陷帳本 | open 3（DEF-01-007 / DEF-01-009 / DEF-62-001）/ routed 3（DEF-17-001 / DEF-19-001 / DEF-42-001），全 P3 | 健康，無 P0/P1/P2 |

---

## 3. 階段二：增量設計

### 3.1 <Architecture_Design_Review>（寫實質 Python 前自審）

1. **架構純潔性**：無 God-object。`SdkExecutorAdapter` 類別**零改動**、維持 policy-free（仍只接注入 predicate）；新增 `build_tool_allowlist_predicate` 為 module-level 純函式（policy 與 adapter 解耦）。main.py 維持 composition root，只做 wiring。
2. **持久化相容**：無新 checkpoint 狀態。`ExecutorConfig` 新增 `sdk_tool_allowlist: list[str] | None = None`（**additive**，預設 None → 零行為變更）；config 不入 PlaybookCheckpoint，DAL 三後端不受影響。
3. **安全防護網**：SDK 工具閘路徑（非 shell CONDITIONAL）。predicate **deny-by-default**（僅清單內工具名放行，空 list = 全 deny）；`_wrap_can_use_tool` 已對 predicate 例外 fail-closed deny。以真實 CLI 活體驗證 deny 生效（非僅 mock）。
4. **對外 I/O 安全**：本項閘的是工具**名**（非 `ToolInvocationPort` 的 domain，故無 SSRF/URL 面）。預設 None＝維持 permission_mode 守門（零退化）；設定後 deny-by-default。活體實證「被拒工具真的不執行」。

### 3.2 介面 delta

| 構件 | delta | LOC 落點 |
|------|-------|---------|
| `utils/config.py` `ExecutorConfig` | +`sdk_tool_allowlist: list[str] \| None = None` | +5 行（不影響 tier） |
| `infra/adapters/sdk_executor_adapter.py` | +module-level `build_tool_allowlist_predicate(allowed_tools) -> CanUseToolPredicate` | +16 行（288→304，adapter tier ≤400） |
| `main.py` | sdk 分支 lazy-import builder + 由 config 建 predicate 注入 | +19 / -6（composition root） |
| `.importlinter` | **無需改動**——`sdk_executor_adapter` 已在 executor 雙向隔離契約內，新函式為同模組純函式 | — |

---

## 4. 階段三：實作與雙重驗證

### 4.1 程式碼變更（4 檔，84 insertions / 6 deletions，全 tracked 修改）

- `ExecutorConfig.sdk_tool_allowlist`（additive，預設 None）
- `build_tool_allowlist_predicate(allowed_tools)`：`frozenset` 成員判定，deny-by-default，純函式
- `main.py`：`backend=="sdk"` 時，`allowlist=None → predicate=None`（permission_mode 守門，零退化）；`allowlist 為清單 → 注入嚴格 allowlist predicate`

### 4.2 單元測試（test_sdk_executor_adapter.py：12 → 16，+4）

- `test_sdk_tool_allowlist_defaults_to_none`（零退化邊界：預設 None）
- `test_build_predicate_allows_listed_denies_others`（deny-by-default）
- `test_build_predicate_empty_list_denies_all`（空 list = 最嚴格）
- `test_build_predicate_injected_denies_unlisted_via_sdk_hook`（整合：注入後 SDK hook 對清單外回 Deny）

### 4.3 W-69-1 活體 A/B 證據（真實 Claude Code CLI，去風險 R-68-7）

**活體探針 #1（連線 + 事件 + act-first 真值）**：
- 連上真實 bundled CLI（claude.exe），8.6s；`out.text='PONG'`、exit_code=0、completed=True
- 事件串流（真實訊息）：partial_output / token_pct / completion 全到位
- `get_context_usage()` 真值（dict/TypedDict）：percentage=5、**maxTokens=1,000,000**、**autoCompactThreshold=967,000**、isAutoCompactEnabled=True
- **act-first 在真值上跑得到**：`_act_first_safe=True`，且驗算為**真安全**——AutoClaude halt = 90% × 1,000,000 = **900,000** < SDK autocompact **967,000**，AutoClaude 先停，SDK 不會搶先 autocompact。

> **澄清留證（zero-trust 對自己）**：偵察時曾疑 `get_context_usage()` 回 `ContextUsageResponse` 物件（非 dict）會使 adapter 的 `isinstance(usage, dict)` 守門靜默跳過 act-first。**親驗後否定**：`ContextUsageResponse` 是 `TypedDict`，runtime 即 dict，鍵名 `percentage/maxTokens/autoCompactThreshold` 與 adapter 取用完全一致 → 非缺陷。先驗證再下結論，未記假缺陷。

**活體探針 #2/#3（can_use_tool deny — 決定性副作用對照）**：
- 探針 #2（單純字串）**不夠決定性**：Claude 發 Bash TOOL_USE 但最終文字 `HELLO_FROM_BASH` 無法區分「真跑」vs「被擋後 Claude 自打預期輸出」（prompt 內含 echo 字串）→ 據實判為不可信，改用副作用。
- 探針 #3（副作用對照，決定性）：
  - **負例** allowlist=`["Read"]`（無 Bash）：哨兵檔**不存在**；且 Claude transcript 出現 `<error>blocked by allowlist: Bash</error>`（正是 `_wrap_can_use_tool` 的 deny 訊息原文）→ Bash 真被擋、未執行。
  - **正例** allowlist=`["Read","Write","Bash"]`：哨兵檔**存在**、回 DONE → 放行時 Bash 真跑、真建檔。
  - **判決：W-69-2 allowlist deny 在真實 CLI 生效（負 deny + 正 allow 雙證）。**

---

## 5. 階段四：CI 平價收斂（零退化矩陣）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ floor 3345 / 0 failed | **3349 / 122 / 0**（=3345+4 新測）✅ |
| 架構契約 | `lint-imports` | 全 kept / 0 broken | 8 kept / 0 broken ✅ |
| LOC 分級 | `check_loc_budget.py` | 全過 | violations=0（19367 / cap 20438）✅ |
| Snapshot | `snapshot_sync.py --check` | 新鮮 | OK ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | 全綠 | exit 0（階段一實測；**本輪零 SDD 變更**，git 證 `AISDLC_SDD/` 0 改）✅ |
| 五軌 TLC | — | 僅 FSM 變更時 | **不適用**（無 `*.tla` / 凍結本體變更，免 Copy-on-Evolve、免 TLC） |

---

## 6. RTM（需求 → 驗證對應）

| 需求 | 驗證 | 證據 |
|------|------|------|
| R-69-1 活體連線 SDK→真實 CLI | 活體探針 #1 | out.text='PONG'、bundled claude.exe、8.6s |
| R-69-2 事件串流真實訊息映射 | 活體探針 #1 | partial_output/token_pct/completion |
| R-69-3 act-first 在真值上判定 | 活體探針 #1 | _act_first_safe=True；900k halt < 967k autocompact |
| R-69-4 can_use_tool predicate production 接線 | main.py wiring + 16 單元測 | test_build_predicate_*、test_sdk_tool_allowlist_defaults_to_none |
| R-69-5 deny-by-default 在真實 CLI 生效 | 活體探針 #3（副作用對照） | 負例檔不存在 + `blocked by allowlist: Bash`；正例檔存在 |
| R-69-6 零退化（預設行為不變） | 收斂矩陣 | 預設 sdk_tool_allowlist=None → can_use_tool=None；3349/0、8 kept、LOC 0 |

---

## 7. B 軌缺陷帳本

**本輪無新框架缺陷**（純 AutoClaude 整合層、SDD 本體零變更）。上輪 open/routed 複驗見 `AutoSDD_Defect_Log.md` improving_69 收尾註記（3 open / 3 routed 全 P3 carried，無重現惡化）。

`get_context_usage` 的 TypedDict 疑慮親驗為非缺陷（§4.3 留證）；探針 #2 不決定性屬本輪測試方法自我修正（非框架缺陷）。

---

## 8. 誠實級別標註

本輪＝**C/A 軌 SDK 整合收尾輪（活體去風險 + production 安全閘接線），非成熟度推進**，`L_合體=min(A=L5,B=L5,C=L5)=L5` 維持。

- **首次達成**：R-68-7 活體 A/B 在真實 Claude Code CLI 去風險（連線/映射/act-first 真值/can_use_tool deny 四項決定性實證）——improving_68 標的「正確性需對真實 CLI 驗才算數」本輪兌現。
- **誠實邊界**：探針 #2 不決定性時據實改用副作用對照（未用模糊證據宣稱 deny 生效）；TypedDict 疑慮親驗後否定（未記假缺陷）。
- **未做**：完整 pty-vs-sdk 指標 A/B（掌舵者選「小規模真跑」非「完整 A/B」）；W-69-3 act-first 硬擋（延 improving_70）；richer domain-allowlist（本輪泛型工具名 allowlist 已足 production 接線，domain 層屬 ToolInvocationPort 既有路徑）。
