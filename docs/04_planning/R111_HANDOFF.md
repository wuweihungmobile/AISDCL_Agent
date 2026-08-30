# R111 交接書 — 護欄層判準修補輪（DEF-200-116/121/129/195/209/212/213④，單人窗口）

<!-- guard-total:R111 --> **本輪護欄層累積淨額（稽核痕跡合計，同輪多列合併）＝ 89467 → 89452（-15）** —— 新增判準（116 值域紅綠＋213④ 薄調用：`test_quota_policy.py` 3152→3198；129/195 取數面＋2×2：`test_check_defect_log_crossref.py` 3722→3794；209 同步鎖：`test_subprocess_encoding_hygiene.py` 1599 持平；121 lookahead＋兌現＋稽核鏈：`test_adr_xplat001_c1c2_lock.py` 6341→6391；取證邊界段依披露鎖回遷 `test_smoke_ci_sync.py` 1298→1334）全數由 16 塊史料搬遷 `CrossPlatform_Guard_Line_History.md` 抵銷（品質收輪追提 2 塊：`test_check_hooks_liveness.py` 3604→3581、`test_archive_defect_log.py` 4008→3986）；連續上升計數（R108 +190、R109 +153）歸零。逐檔清單見 `CrossPlatform_R106_Scan_Findings.md` 的 R111 標記行。

> 本檔由 R111 修復包（單人窗口）寫下；量測值皆為寫下當回合的實測，讀者的第一動作是重量，不是採信。
> 規格書＝`docs/04_planning/AutoSDD_R111_Repair_Spec.md`（逐筆修復規格與偏差對照見交件回報）。

---

## 一、`R112` 排程約束

- 重釘淨額三輪走勢：`R108`＝+190、`R109`＝+153、`R111`＝**−15** ⇒ 款(11) 連續上升計數已歸零。
- 到期義務：`(111, 595)` 已於本輪兌現，並重武裝為 `_REPIN_NET_CAP_DUE_ROUND=113`／
  `_REPIN_NET_CAP_DUE_TARGET=585`（步伐 10 < 前段 15）——`R113` 前 cap 須降到 585 以下。
  新增後設鎖：到期輪自身不可推遲（`[到期日被推遲]`，`_REPIN_DUE_ROUND_MAX_LOOKAHEAD=2`）。
- 🔴 **Phase 2 觀察時效將於下一輪逾期**：`_PHASE2_REVIEW_LOG` 末列＝(106, [維持觀察])、
  視窗 5 ⇒ 到期輪＝R111；判準是 `live > due`，本輪 live=111 恰好貼線仍綠，**稽核痕跡一走到
  R112 即 `[時效逾期]` 紅**。出口＝往 `_PHASE2_REVIEW_LOG` 追加一列 §6 決議
  （`[提案]`／`[維持觀察]`（連續第 2 次會撞 `[連續空轉]`）／`[退場]`），屬四方／掌舵者
  裁決面（載體＝ADR-XPLAT-012 條文五 §6；`DEF-200-217` 列亦掛著 E1 重投票同族裁決）。
- 本節數字的現查：`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`。

## 二、已驗證什麼（皆本輪當回合實測；收尾最後全套 rc 依 `R108` 慣例見交件回報）

- 116：紅側重演（舊公式同注入）＝`headroom=0.0`、新實作＝`23.0`（binding=session
  band=converge cap=8）；`pytest -k "Def200116 or TestR86"` → `13 passed`。
- 213④：`python tools/lib/quota_reconcile.py --self-test` rc=0 全 PASS（R1/R2 紅綠＋三態
  不可折疊）；薄調用 `1 passed`。該檔已為 tracked（R100 commit `7fbdf9b` 先行 add，
  規格書「untracked」半句已 stale）。
- 212：`check_handoff_carriers --self-test` 16 PASS；`--census` 改前後同值
  （105 份／前瞻 8 筆／commit 451 則）；主判準 rc=0。
- 129/195：`_receipt_rounds()` 上鎖後真帳本重量「@R 排除後跨列出口失效轉紅 = 0 筆」；
  crossref 測試檔全套 `249 passed, 46 subtests passed`。
- 209：`ruff check tools/ .claude/hooks/ --no-cache` → `All checks passed!`；
  `check_loc_budget --json` special/root_tools violations 全空；hook 三測試檔
  `650 passed, 8 skipped`。
- 121：注入 `due_round=9999` → 含 `[到期日被推遲]`；`due_round=live+2` → 綠（測試
  `test_the_due_round_itself_cannot_be_postponed` 四格）。

## 三、還沒做（每項附載體與現查指令；本檔不新增帳本列）

- **129 自列出口尚未接線**：cur 滯後 R100 窗口實測轉紅 14 筆
  （DEF-101-018/060/398/796/856/863/867/887/938/951/960/974/980/981，狀態欄最大輪號
  79~91）——函式已落、接線＝結案輪帳本收斂（cur→R111 後重量轉紅=0）再做；
  載體＝`DEF-200-129` 帳本回執；現狀釘在
  `python -m pytest tools/tests/test_check_defect_log_crossref.py -k Def200129 -q`
  （TestDef200129SelfRowExitAwaitsWiring；接線時必翻紅）。
- **212① 閘門尚未接線**：`ledger_def_ids(unresolved_only=True)` 已落、預設關——cur=R100 下
  3 筆真紅（R102_HANDOFF.md:45→DEF-200-204／CrossPlatform_R100_Scan_Findings.md:252→
  DEF-200-208／CrossPlatform_R107_Ledger_Closure.md:125→DEF-101-559，目標輪 R101/R101/R108
  皆 < R111 ⇒ cur 進位後自動祖父化出局）；載體＝`DEF-200-212` 帳本回執；strict 路徑紅綠
  現查 `python tools/check_handoff_carriers.py --self-test`。
- **217-E2／E5 與 191 仍未處置**：本輪任務書九項未列（規格書「行有餘力」項）——載體＝
  `DEF-200-217`／`DEF-200-191` 既有未結列（前者狀態欄已載 E2/E5 未動；後者屬裁決筆，
  單人窗口不得自裁）；現查 `python tools/check_defect_log_crossref.py --unresolved-count`。
- **`S102`（ruff S 系列）尚未納入 select**：刻意不隨 209 落地（select 動一字兩樹連動）；
  載體＝`DEF-200-217` E2 軸；現查 `python -c "import tomllib;print('S' in tomllib.load(open('tools/ruff.toml','rb'))['lint']['select'])"`。
- **帳本七列狀態欄整格替換的原文指針尚未補存**（四方審查劃界照登）：R112 結案證據檔補存
  被替換前的原文快照；在那之前原文仍可自 git 歷史重驗：
  `git log -p -- docs/06_quality/AutoSDD_Defect_Log.md`。

## 四、禁止事項（沿規格書任務書條款）

- 不准 `--no-verify`；不准調高 `_REPIN_ROUND_NET_CAP`／`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS`／
  `_REPIN_DUE_ROUND_MAX_LOOKAHEAD`（只准下修）；不准自加 `_REPIN_APPROVED_ROUND_OVERAGE` 條目。
- 129 上鎖（自列出口接線）前必以結案後帳本重跑量測、轉紅=0 才接閘門。
- 帳本原文列 append-only；搬遷史料原文全文保全。
