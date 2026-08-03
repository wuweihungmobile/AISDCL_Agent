# AutoSDD improving_53 — B 軌：清償 routed 框架本體 RFC DEF-CLDREV-030（`hub_sync.py` 對外 yaml 記憶體上限）

> **軌道定位**：軌道① **B 軌**（手腳 AISLDC_SDD 框架本體 dogfooding 缺陷回流，柱②）。標的＝improving_50 第八輪 SA 鏡 F-02 揪出、routed 至框架本體 RFC 的 **DEF-CLDREV-030**（`tools/fsm_runtime/hub_sync.py` 對外/快取 hub yaml 缺記憶體大小上限，billion-laughs／超大檔 DoS 深防禦缺口）。
> **政策**：標的屬 SDD 框架本體（凍結本體）→ **Copy-on-Evolve v0.19 → v0.20**（非就地修）。
> **下一份**：`AutoSDD_improving_54.md`（按需）。
> **日期**：2026-06-24。
> **掌舵者裁定**：本輪以 AskUserQuestion 拍板「**B 軌 清 routed RFC（v0.20）**」。三柱現況＝SDD `.claude` 穩態零缺陷（再全鏡＝零新發現 token 浪費）、C 軌 SD_09 W1 被 06-29 G0 blocked、ConsoleUI 等使用者 UI/UX 視覺指引——無預設方向，掌舵者裁定推 B 軌清上輪 routed 框架本體缺陷。此裁定亦＝DEF-CLDREV-030 的 🔴 人工 signoff（框架本體 RFC 決策點）。
> **結論先行**：🟢 DEF-CLDREV-030 經 Copy-on-Evolve v0.20 就地清償（對外輸入域記憶體上限閘）。零退化（ci-gate exit 0：v0.01:1478 / v0.20:1646〔v0.19 1638 + 8 新測試〕/ scripts:127）。FSM/`*.tla` 逐位元零差異 → 不觸發五軌 TLC。

---

## 1. 本輪輸入（自上輪繼承）

- 上輪＝improving_52（C 軌 BOM hook zero-trust 已結案，commit `6f27d89`）。
- 缺陷帳本 open/routed 可動者盤點：
  - **DEF-CLDREV-030（routed，框架本體 RFC）**：`hub_sync.py` 對外 yaml 缺大小上限 ← **本輪標的**。
  - DEF-19-001（routed，catch 5/39 漸進）、DEF-01-007/009（open，cc-switch 環境/watch，本輪不涉多後端不觸發）、DEF-17-001（routed 遙測）、DEF-32-002（routed 未來 A 軌）、OBS-1（routed scenarios/ 層待裁決）——**本輪不動，維持原狀態**。
- 上輪審計遺留：無 partial、無未竟修復。

## 2. 階段一：現況重偵察（Zero-Trust Re-Audit，Explore agent 親跑）

| 項目 | 命令 | 實測 |
|------|------|------|
| HEAD 真相 | `git log --oneline -3` + `git status --short` | HEAD=`6f27d89`；工作樹乾淨（空） |
| **SDD 框架零退化基線（B 軌主基線）** | `bash scripts/ci-gate.sh` | **exit 0**；逐軌 **v0.01:1478 / v0.19:1638 / scripts:127**，全 lint ✅（arch_fitness fail=0、4 SSOT lint 綠） |
| AutoClaude 架構契約（確認不碰 AutoClaude 仍綠） | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** |
| **標的 DEF-CLDREV-030 仍重現** | 親讀 `hub_sync.py` L141/219/246/334/493/595 | 6 處 `read_text` 前**皆無** `stat().st_size` 上限；最高風險 L334（消費 hub 拉回內容） |
| hub 外部拉取 deny-by-default | 親讀 `knowledge/hub-registry.yaml` | `allowed_endpoints: []`（空清單一律拒連）+ `deny_unlisted: true`（hard-coded）+ `push.enabled: false` |
| invocation 形態（紀律 (f)） | — | hub_sync ＝本地 CLI／subprocess + file://、git+https；非 GUI；headless 可自動化驗證 |

**硬閘**：基線無 failed、未低於上輪（v0.19 1638 == floor）→ 通過，進入階段二。

## 3. 階段二：本輪增量設計（W-53-1）

**精準威脅界定**（zero-trust 親讀後）——6 處 `read_text` 中**僅 3 處消費對外不受信內容**：

| 讀取點 | 內容來源 | 對外不受信？ | 處置 |
|---|---|---|---|
| L141 registry | repo-internal PR-gated config（極小、__init__ 載入） | ❌ 受信 | 不 cap（加註記） |
| L219 cache META | 自寫（`_write_cache_meta`） | ❌ 自產 | 不 cap |
| L246 audit log | 自寫、**隨 push 事件累積增長** | ❌ 自產且會長大 | **絕不 cap**（cap 破壞合法累積） |
| **L334** `_stamp_external_trust_level` | **剛從 hub 拉下的 rules/\*.yaml** | ✅ **惡意 hub 主攻擊面** | **cap → fail-soft skip + audit** |
| **diff()** cached 讀取 | 已快取 hub 內容 | ✅ 對外 | **cap → raise** |
| **promote()** | 可為人工指定的 cached 外部檔 | ✅ 可對外 | **cap → raise（fail-closed）** |

> 「對受信/自寫累積日誌不一律套相同防護」是刻意的精準界定——既對齊 RFC「對外來源 yaml 加大小上限」意圖，又避免對 audit log 套 cap 引入「合法累積被截斷」的新 bug（[[no-defer-unless-justified]] 反面：亂套防護＝引入新債）。

### W-53-1 介面 delta（Copy-on-Evolve v0.20）
1. 模組常數 `MAX_HUB_FILE_BYTES = 1024 * 1024`（1 MiB；SLV 規則僅 KB，~1000× headroom）；registry `sync_policy.pull.max_file_bytes` 可覆寫（`__init__` 讀入 `self._max_file_bytes`，非正值/型別錯 fallback 常數）。
2. 例外 `HubContentTooLarge(HubConfigError)`（CLI `_cli` 既有 `except (HubConfigError, ...)` 自然接住回 exit 2）。
3. 純函式 helper `_read_text_bounded(path) -> str`：`stat().st_size > self._max_file_bytes` 即 raise，否則回 text。
4. 套用三對外點：L334 既有 `except Exception` 接住 → fail-soft skip + audit（兌現 pull `failure_mode=non_blocking`）；diff/promote raise 給呼叫端。
5. `hub-registry.yaml` 補 `sync_policy.pull.max_file_bytes: 1048576`（值＝常數預設，行為等同；自我文件化）。
6. 回歸鎖 `tools/fsm_runtime/tests/test_hub_sync.py::TestHubFileSizeCap` +8 case。

**LOC 預算落點**：hub_sync.py 屬 `tools/fsm_runtime/`（非 `autoclaude/` 套件），不受 AutoClaude `.importlinter` 8 contract 約束；修復為 additive helper + 常數，無暴增。
**`.importlinter` 影響**：N/A（標的在 SDD 框架，非 AutoClaude 微核心）。
**checkpoint additive 欄位**：無（不碰 PlaybookCheckpoint）。

### <Architecture_Design_Review>
1. **架構純潔性**：純函式 helper + 常數 + 例外子類，無 God-object、未動微核心/FSM，維持單一職責。✅
2. **持久化相容**：不碰 FSM-STATE/PlaybookCheckpoint/DAL；audit 走既有 `_record_audit`。✅
3. **安全防護網**：**強化**對外輸入縱深——對不受信 hub yaml 加記憶體上限閘，與既有 `safe_load`（擋 `!!python` RCE）、`deny_unlisted`（擋未授權 endpoint）正交疊加；自寫累積日誌刻意不 cap（避免引入新破口）。promote 同走 helper → fail-closed 不得升入信任階梯。✅
4. **對外 I/O 安全**：本身即 hub 對外路徑強化；`allowed_endpoints: []` deny-by-default 維持；新增測試涵蓋超大檔向量。本輪未新增 `ToolInvocationPort` 外呼路徑。✅

## 4. 階段三：實作與雙重驗證

逐項實作（dev-build-test 循環）：① 常數+例外+helper+__init__ → AST OK；② 三對外點套用；③ registry 補 key → yaml OK；④ +8 測試 → `test_hub_sync.py` 36→44 passed；⑤ **受控突變實證 Rule 9**：暫關 cap → `_read_text_bounded`/pull-skip/promote-reject **3 anchor 轉紅**、還原後 8 passed。
- **誠實記錄**：pull-skip 初版因 pull 寫 cache/audit 至 REPO_ROOT（非 tmp）、24h fresh-cache 遮蔽突變致初次突變未轉紅 → 改 hermetic（cache/meta/audit 導向 tmp + `force=True` 旁路快取）後方具突變敏感性。此為測試非 hermetic 的真實摩擦，已修正並記入 Defect_Log 教訓。
- v0.20 全套 `pytest -m "not chaos"` = **1646 passed / 4 skipped / 0 failed**（v0.19 1638 + 8）。

## 5. 階段四：CI 平價收斂（零退化驗證矩陣，parent 親跑）

| 檢查 | 命令 | 通過條件 | 實測 |
|------|------|---------|------|
| SDD 框架雙軌 + scripts | `bash scripts/ci-gate.sh` | exit 0；v0.20 ≥ floor 1638 / 0 failed | ✅ **exit 0**；**v0.01:1478 / v0.20:1646 / scripts:127** |
| 架構適應度 | arch_fitness --strict | structural fail=0 | ✅ fail=0（僅 FF-16 advisory） |
| SSOT 4 lint | framework_status / skill_header / sync_exposed_skills / router_hook_coverage | 全 fresh/對齊/綠 | ✅ FRESH / 對齊 v0.20（45 檔戳記）/ 父層==LATEST 59 檔 / 三 event 全可達 |
| 其餘 shared-infra lint | rfc / gitignore / agent_template / collaboration / scenario_frequency | 全 ✅ | ✅（gitignore v0.20 block 已補） |
| Copy-on-Evolve 潔淨度 | `git add -A -n` would-add 審查 | 零 runtime 夾帶 | 由 Architect 鏡親驗（859 tracked 純源碼） |
| 五軌 TLC | （僅 FSM/`*.tla` 變更時） | — | **N/A**（formal/ 與 transition_rules.py 對 v0.19 逐位元零差異，不觸發） |

## 6. RTM（本輪需求追溯）

| 需求 | 驗收標準 | 證據 | 狀態 |
|------|---------|------|------|
| R-53-1 清償 routed DEF-CLDREV-030（對外 yaml 大小上限） | 3 對外點加 bounded read、registry 可覆寫 | §3 介面 delta + hub_sync.py | ✅ |
| R-53-2 Copy-on-Evolve v0.19→v0.20，凍結本體不就地改 | git archive 859 tracked、v0.01/v0.19 凍結零觸碰 | §5 + git status | ✅ |
| R-53-3 回歸鎖非空殼（Rule 9） | +8 case、3 anchor 受控突變轉紅 | §4 突變實證 | ✅ |
| R-53-4 零退化 | ci-gate exit 0、v0.20 ≥ floor、SSOT 全綠、FSM 零變更不觸 TLC | §5 矩陣 | ✅ |
| R-53-5 四鏡 zero-trust 全 PASS | Architect/SA/SD/QA 主樹獨立審查 | ZeroTrust_Audit_53.md | ✅ 四鏡全 OVERALL PASS、P0=P1=P2=0 |

## 7. 結論

掌舵者裁定 B 軌清 routed 框架本體 RFC，DEF-CLDREV-030 經 **Copy-on-Evolve v0.20** 就地清償：對 `hub_sync.py` **3 處對外不受信讀取**（pull stamp / diff / promote）加 1 MiB 記憶體上限閘（`_read_text_bounded` + `HubContentTooLarge`，registry 可覆寫），緩解 billion-laughs／超大檔 DoS；受信本地 registry 與自寫累積 audit log 刻意不 cap。+8 回歸測試、3 anchor 受控突變實證非空殼。**零退化**：ci-gate exit 0（v0.01:1478 / v0.20:1646 / scripts:127）、SSOT 4 lint 全綠、gitignore v0.20 block 補齊、FSM/`*.tla` 逐位元零差異不觸發五軌 TLC。

**回流**：DEF-CLDREV-030 routed → fixed@v0.20（人工 signoff＝掌舵者 AskUserQuestion；無 active RFC 檔殘留，rfc_lifecycle_lint 綠）。

**四鏡 zero-trust 結果**：Architect / SA / SD / QA **全 OVERALL PASS、P0=P1=P2=0**（詳見 `docs/06_quality/AutoSDD_ZeroTrust_Audit_53.md`）。2 項 P3 殘餘皆不阻斷：① **P3-1**（DEF-CLDREV-030 接受殘餘）billion-laughs 部分緩解——SA 實測 PyYAML parse/dump 不炸 + deny-by-default 第二防線；② **DEF-53-001**（P3 routed latent）`hub_merge.py` 未 cap 讀 pull-cache，惟 `detect_conflict`/`resolve_or_record` 僅測試呼叫未 wire 進 runtime、當前不可達，附觸發閘「wire hub_merge 前必補 `_read_text_bounded`」。
