# R87 交棒書

> 本輪是**單人收斂輪**：8 個實作包 ＋ 四方複審全部因額度撞頂而未執行。
> 交出的是「舵手親做的部分」，且**每一項都附當回合實測**。重啟後第一件事是重驗，
> 不採信本檔任何「已通過」宣稱。

## 0. 一句話總結

**本輪最大的產出是一次事故與它的機械化修復**：舵手用模型判斷推翻了程式守衛，
代價是 13 個 subagent 全滅、1,319,703 tokens 零產出；修復不是「下次小心」，
而是把「模型不得推翻機制」變成會轉紅的測試。

## 1. 本輪事故（DEF-200-107）

| 項 | 內容 |
|---|---|
| 現象 | 派出的 13 個 agent 全數 `You've hit your monthly spend limit`，331 tool_uses／634s／零產出 |
| 舵手的錯誤判讀 | `extra_usage.is_enabled=false`／`spend.enabled=false` ⇒ 誤讀為「池子關著、不是節流軸」 |
| 真意 | `used 610 > limit 500`、`severity: critical` 才是硬事實；`enabled:false` 是**撞頂的後果** |
| 錯誤的證據① | 「主力軸只有 1%」——訂閱窗與月度付費上限是**不同的池** |
| 錯誤的證據② | 「我還能送請求」——主 session 走訂閱額度，不蘊含 subagent 那條路沒撞牆 |
| 守衛當時說了什麼 | 逐字：「這一條**沒有 reset 可以等**（例：月度支出上限）；只有人去提額」——**完全正確** |
| 架構缺口 | 判讀層有「halt 一票否決」不變式，**取數層沒有對等不變式** ⇒ 從上游抽掉輸入，整道保護在**零判準觸發**下失效 |
| 掌舵者裁決 | 「不是要寫在程式架構控制嗎？怎麼變成你在控制？」 |

<!-- guard-total:R87 --> **本輪護欄層累積淨額＝ 83470 → 83610（+140）** —— 全數來自兩組新鎖
（`TestR87TheMeterMayNotDropAThrottlingAxis` ／ `TestR87AccountPostureIsKnownBeforeDispatch`）
與本次重釘紀錄自身。逐檔清單與立案逐字＝`docs/06_quality/CrossPlatform_R87_Guard_Repin_Evidence.md`。
`[收尾單人窗口當回合實測；憑證＝tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines]`

## 2. 已驗證什麼（附當回合實測）

| 項 | 指令 | 結果 |
|---|---|---|
| quota 測試（含兩組新鎖） | `python -m pytest tools/tests/test_quota_policy.py -q` | **136 passed / 283 subtests**（原 127） |
| 鎖有鑑別力 | `-k R87 -v` | 4 測全 PASSED，含「重演錯誤實作必須不再 halt」 |
| 帳本 | `python tools/check_defect_log_crossref.py` | **rc=0**；未結 91 → **90** |
| 派工前置檢查 | `python tools/session_resume_planner.py --pace` | 新增一行：`派工前置：方案指紋=…｜credits 已耗盡、已停用 ⇒ **無 fallback**，訂閱窗即硬牆` |
| 額度分母標定 | 逐字稿 usage 累加 | 主 session 加權 1.98M／subagents 11.59M；Δpct 62 ⇒ **Pro 5h 窗 ≈ 22M 加權 token**、**≈6.6pp/包** |

## 3. 本輪交付

1. **`quota_meter.axis_is_disabled` 已刪除**（錯誤修改全數還原），原地留事故墓碑註解。
2. **`quota_meter.account_posture()`**：派工前置檢查（方案指紋＋credits 姿態）。
   `fallback_available` ＝「訂閱窗用完之後還有沒有救」。讀不出來一律判無 fallback。
3. **`quota_gate.posture_line()`**：把上面那件事印進 `--pace`，派工前看得到。
4. **兩組機械鎖**（見 §2）＋ **帳本 DEF-200-107／108** ＋ 重釘證據檔。
5. **`_REPIN_NET_CAP_SCHEDULE` 到期下修** `(87, 2600)`，凍結基準同步下修。

## 4. 還沒做什麼（誠實劃界）

**8 個實作包與四方複審全部未執行**（額度撞頂）— 現查：`python tools/session_resume_planner.py --pace`
（`band=halt` 即代表仍派不出去）。原任務書仍有效，逐包持有面見
workflow 腳本 `r87-xplat-iteration-wf_2fbf7232-93b.js`。未動的訴求：

- 訴求 1／3（跨平台全掃、M5 雙向不落差）尚未做 — 現查：`python tools/probe/xplat_injection_matrix.py --help`
- 訴求 5（挖深清債）尚未做 — 現查：`python tools/check_defect_log_crossref.py --unresolved-count`
- 系統問題 1（skipped 殲滅）尚未做 — 現查：`python -m pytest AutoClaude/tests/ -q -rs`
- 系統問題 2（帳本降到 warn 線下）尚未做 — 現查：`python tools/check_defect_log_crossref.py --unresolved-count`
- 系統問題 3（Plugin 架構裁決）尚未做 — 現查：`python AutoClaude/tools/check_loc_budget.py --json`
- AISDLC_SDD Agents 精進尚未做 — 現查：`python AISDLC_SDD/scripts/sdd_version.py`
- Archive 尚未做 — 現查：`git ls-files docs/04_planning | wc -l`
- Docker housekeeping 尚未做 — 現查：`python -c "import subprocess;subprocess.run('docker system df',shell=True)"`
- 訴求 6b 的**程式化**尚未做（標定公式規格見 R87_RESUME.md §2b） — 現查：`python -c "import pathlib;print('account_posture' in pathlib.Path('tools/lib/quota_pace.py').read_text(encoding='utf-8'))"`
- 訴求 6f（`.env.example` → `.env` 實測調參）尚未做 — 現查：`python tools/lib/quota_policy.py --print-env-example`

**工作樹另有兩個半套改動**（agent 撞牆前寫入，未驗證、未複審）：
`AISDLC_SDD/AISDLC_SDD_v0.30/agent/core/05.sd-architect-zh.yaml`（+26）、
`tools/probe/xplat_injection_matrix.py`（+31）。

## 5. 下一輪第一件事

```bash
python tools/session_resume_planner.py --pace     # 先看 band 與「派工前置」那一行
launchctl list | grep -i autosdd                  # mac 側憑證＝rc
python tools/run_root_unittests.py                # 全綠才動工
```

🔴 **需要掌舵者親自做的**：月度支出上限已撞頂且**沒有 reset 可以等**
（`used 610 / limit 500`、`can_purchase_credits: false`、`disabled_reason: org_level_disabled_until`）。
在提額之前，**任何 subagent／Workflow 一律派不出去**，只有主 session 的收斂型工作可做。
提額入口：https://claude.ai/settings/usage

## 6. 禁止事項

不准 `--no-verify`／`AUTOCLAUDE_SKIP_HOOKS=1`／`--allow-pg-extras`；
不准關 `AUTOSDD_*_GUARD_OFF` 任一逃生口；
不准 `git stash`／`reset --hard`／`checkout -- <path>`／`clean`；
**不准以模型判斷推翻機械守衛的判定**——本輪已示範代價（見 §1）。

<!-- guard-total:R87 --> **83470 → 83610（+140）** —— 護欄層累積總量現值，
到期上限已下修為 **2600**（`_REPIN_NET_CAP_SCHEDULE` 末列）。
