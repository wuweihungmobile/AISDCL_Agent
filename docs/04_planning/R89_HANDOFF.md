# R89 交棒書 — 單人輪（額度 halt，四方複審結構上派不出去）

> **Session ID**：`b2e798a7-52c9-4d95-9084-ab0858958641`
> 重啟：`claude -r b2e798a7-52c9-4d95-9084-ab0858958641`
>
> 🔴 **重啟後第一件事是重驗，不採信本書任何「已通過」宣稱**（〈可重啟點四條件〉第 4 條）。

## 0. 本輪為什麼是單人輪

`python tools/session_resume_planner.py --pace` 當回合實測：

```
現在可派 0 個 agent（硬上限 cap=0）｜band=halt｜最緊的一條＝extra_usage 100% reset 距離不明
派工前置：credits 已耗盡、已停用 ⇒ **無 fallback**，訂閱窗即硬牆
⏳ 這一條**沒有 reset 可以等**（例：月度支出上限）；只有人去提額 ⇒ 這道節流不會自己解除。
```

訂閱窗健康（session／five_hour 13%、seven_day 22%），卡住的是 `extra_usage`／`spend`
兩軸（皆 100%、`resets_at=null`）⇒ PreToolUse 守衛結構上擋下**所有**扇出。

🔴 **不得繞過**：R87 正是改取數層繞過 halt ⇒ 13 個 subagent 全滅、1,319,703 tokens
零產出（`DEF-200-107`）。守衛的訊息就是答案。

**解鎖條件（只有掌舵者能做）**：<https://claude.ai/settings/usage>
處理月度支出上限（`used 610 / limit 500`、`can_purchase_credits: false`、
`can_toggle: false`、`disabled_reason: org_level_disabled_until`）。
掌舵者本輪已裁決走這條路，並預告帳號用完會換下一個帳號。

> 🔴 **帳號輪替不做進系統機制**：PRD §1.3 自己把「多帳號輪替或帳號池化以擴大額度」
> 列為非目標，§1.2 原則 7 是「合規優先」。掌舵者手動換帳號登入是他的帳號管理，
> 但本 repo 不建自動輪替。換帳號的**技術**風險已立案，見 `DEF-200-114`。

## 1. 本輪交付（皆附當回合實測）

| # | 項 | 憑證 |
|---|---|---|
| 1 | `DEF-200-112` 治本（①資訊面） | `--pace` rc=0，尾行新增期程句；hook 閂鎖後 stderr 同步 |
| 2 | 訂正 `DEF-200-112` 的**射程**（R88 散文比實際寬） | 見下 §2 |
| 3 | 立案 `DEF-200-114`（`plan_fingerprint` 宣稱的用途零實作<!-- absent-if: invalidate -->） | `grep` 實證：唯一消費端只印字串 |
| 4 | 護欄層**淨額 0** 的減法示範 | `--print-guard-lines` → `83670→83670 (+0)`、逐檔漂移 0 支 |
| 5 | ADR-XPLAT-002 §6 邊界 1 補 R89 列（SC-10） | `test_adr_xplat001_c1c2_lock.py` 138 passed |
| 6 | 立案 `DEF-200-115`（守衛可被受守衛者關閉：模型寫 `.claude/settings.json` 的 `env` 即可設 `AUTOSDD_QUOTA_OFF=1`） | 讀 PRD §15.5 紅線 10 後實查，全 repo 無禁寫保護 |
| 7 | 3 處 pgvector `[DEBT]` 承接輪次 R89→R90（走測試指定的出口②，附推遲理由） | `test_conftest_windows_native_skip_report.py` 8 passed；ruff rc=0 |

🔴 **推進帳本時鐘到 R89 會連帶弄紅四類鎖，下一輪要有心理準備**（本輪逐一實測並修畢）：
①輪號超前鎖（程式碼註解寫 R89 > 帳本當前輪）②ADR §6 SC-10 缺當前輪覆蓋列
③AutoClaude `[DEBT]` 承接輪次被追平 ④交棒書「還沒做」宣稱必須附現查指令
（`TestR78HandoffClaimsCarryLiveCommands`）。①②④在根層、③在 AutoClaude 側。

詳情面（複審者要逐條重驗就讀它）＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。

## 2. 最重要的一筆：R88 對 `DEF-200-112` 的描述過寬

R88 寫「halt 判準**不分**兩型」，並推出「續航哨兵結構上等不到 reset」。
**R89 實查，那一半是假的**：`reset_branch()` 早已分 `arm`／`notify`／`escalate`，
`quota_halt_actions()` 只在 `arm` 才呼叫 waker，`quota_halt_message()` 也早已印出
「沒有 reset 可以等…排程是錯的動作」。

真缺口只在**人機出口**：`--pace`（派工前查的那個）與 halt 閂鎖後每次工具都印的那則。
修法是**接電**既有的 `throttle_horizon_line()`，**不新增 band 值**
（`halt_wait`／`halt_human` 會是同一份知識的第二個家＝R73 判例）。

🔴 **教訓（差一步就犯）**：查證時我曾用**自己捏的** `act` dict 渲染 halt 訊息，
印出「本平台沒有排程載具」，看起來像 mac 上 launchd 失效的重大缺陷。
實查 `schedule_backend.select()` → `LaunchdBackend`，載具完好。
攔下這次誤報的是「驗證載具本身要被驗證」那條紀律。

## 3. 還沒做什麼（誠實劃界）

全部因 `band=halt` 而未執行，現查 `python tools/session_resume_planner.py --pace`：

- **四方複審（Architect／SA／SD／QA）** — 一次都沒跑，本輪所有結論皆為自證。
  <!-- absent-if: CrossPlatform_R89_Review --> 證偽標的就是上一行標記裡那個 pattern：
  四方複審一旦真的跑過，本 repo 既有體例會在 `docs/06_quality/` 產出對應的複審證據檔，
  屆時本行當場被打臉。🔴 **說明句刻意不逐字重複那個字面**——R89 第一版重複了它，
  於是鎖 grep 到的是我自己的說明文字，判定「宣稱為假」（自己命中自己）。
  現查「現在派不派得出去」：`python tools/session_resume_planner.py --pace`
  （`band=halt` 即結構上派不出任何 agent）
- PRD `AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` 只讀完 §1–§4.4（1574 行讀了 628 行），
  §15 執行方法論（動工前必讀）**未讀**
- 訴求 1／3（跨平台全掃、M5 雙向不落差實跑）
- 系統問題 1（skipped 殲滅）：R88 已分類（母體 73，`[WINDOWS-NATIVE-ONLY]` 36／
  `[ENV-DISABLED]` 13／`[DEBT]` 5／`[TOOL-ABSENCE]` 2），本輪**零殲滅**
- 系統問題 2（帳本降到 warn 線下）：未結 **88 → 89**（結 1〔`112`〕立 2〔`114`／`115`〕，
  淨 **+1**；warn 86、fail 98，距 fail 線 9 筆）。🔴 誠實說：這一輪帳本是**變差**的。
  兩筆新案都是真的（挖深挖出來的），但「降到 warn 線下」本輪**沒有進展**。
  現查：`python tools/check_defect_log_crossref.py --unresolved-count`
- 系統問題 3（Plugin 架構裁決）：本輪只給了**部分**答案（見 §4），未做架構裁決
- `DEF-200-114` 的修法（要動配速取數層，需第三方複審）
- Archive／Docker housekeeping／SDD Agents 精進

## 4. 對系統問題 3 的部分答案（「為何每輪都在瘦身」）

不是 Plugin 架構能解的。成因是**新增判準時沒有同步把等量史料搬出量測面**。

本輪示範：新增一道完整回歸鎖（含雙向注入自證），護欄層總量**零成長**。
收斂過程（三次實測）：3 個獨立測試 +38 → `subTest` 參數化 +24 →
搬走 `MacCredentialSourceTest` 的 25 行史料 +4 → 回收自己的註解 **+0**。

做法可重複：**判準留在測試檔，史料進輪次證據檔，兩者以檔名指針相連。**
`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS = 2` 就是逼這件事的機械物
（R87 +140、R88 +60 已連兩輪上升 ⇒ R89 必須 ≤0）。

## 4b. 本輪收官閘門實測（當回合，非引述）

```
python tools/run_root_unittests.py    → rc=0  Ran 3327 tests  OK (skipped=44)  0 FAIL
cd AutoClaude && python -m pytest tests/ -q
                                      → rc=0  4586 passed, 73 skipped in 104.49s
python tools/check_defect_log_crossref.py → rc=0（未結 89）
ruff check <本輪觸碰的 AutoClaude 檔>  → All checks passed!
```

🔴 **取證紀律附記（本輪自己踩到一次）**：第二次雙閘門的 AutoClaude 那半回 `rc=4`、
`no tests ran in 0.06s`——原因不是紅，是**我把 cwd 留在 repo 根**去跑 `pytest tests/`
（掃到的是根層 `tests/` 不是 AutoClaude 的）。`rc≠0` 這次剛好會叫，但**若根層恰好有
可收集的 `tests/`，它會靜默跑錯一批測試然後回 rc=0**＝假綠。上表的數字是用正確 cwd
重跑後取得的。同 `useMacWin.md` 記載的 cwd 跨呼叫持續問題（鐵律二的 POSIX 對應面）。

## 5. 下一輪第一件事

```bash
python tools/session_resume_planner.py --pace          # band 仍 halt 就還是單人輪
python tools/run_root_unittests.py                     # 根層全綠才動工
cd AutoClaude && python -m pytest tests/ -q            # 見 §6 的本輪基線
python tools/check_defect_log_crossref.py              # rc=0；未結 88
```

額度解除後**第一件該做的事**：補跑本輪缺的四方複審（Architect／SA／SD／QA），
標的＝本輪 5 項交付 ＋ `CrossPlatform_R89_Closure_Evidence.md` 的每一條宣稱。

## 6. PRD §15 對照現況：一個**架構級**發現（交下一輪四方複審裁決）

本輪讀完 PRD §15（動工前必讀那一章）。**好消息**：§15.3「最小可行架構」與本 repo
現況高度重合，四項「真正必須自建」的模組本 repo 已有其三：

| PRD §15.2 必建模組 | 本 repo 現況 |
|---|---|
| 治理決策器（配速 + 狀態機） | ✅ `quota_policy.decide()` ＋ `quota_pace`（含攤提、horizon 乘數） |
| 跨 5h 視窗長等待與交棒 | ✅ `session_resume_planner --arm-sentinel`（launchd／schtasks） |
| 治理層狀態持久化 | ✅ 額度快取 ＋ `quota_burn.jsonl` ＋ 任務書 |
| 帳號層級配額仲裁 | ❌ 未見（`fanout_ledger` 是本機 session 面，非跨專案帳號面） |

§15.3 的「PreToolUse 在 `Agent` 工具層攔截」正是 `context_budget_guard.py` 在做的事
⇒ PRD 稱之為「本次核實帶來最大的簡化」，本 repo 已經走在這條路上。

🔴 **PRD 有一條紅線在本專案不成立——已實測，不是推論**：

> §15.5 紅線 1 逐字：「**不要碰未公開的 HTTP 端點。** statusLine 已提供你需要的一切，
> 而且是官方支援的路徑。原 PRD 的 T5 方案現在既無必要也有風險。」
> §0.6 第一列同義：遙測引擎「**採用** statusLine，原 T5 整條刪除」。

`quota_meter.fetch_usage()` 打的正是 `/api/oauth/usage`＝PRD 的 **T5**。
本輪原本把它記成「repo 違反紅線 1，待架構師裁決」——**那個方向錯了**，實測見下。

**當回合實測**（`claude --version` 2.1.226；探針與對照組都在 scratchpad，
逐字與方法見 `CrossPlatform_R89_Closure_Evidence.md` §statusLine 實測）：

| 遙測管道 | headless（`claude -p`）會發生？ | payload 含 `rate_limits`？ |
|---|---|---|
| statusLine | ❌ **一次都沒被呼叫** | 無從得知（根本沒跑） |
| hook（SessionStart） | ✅ 會跑 | ❌ **不含**（只有 `session_id`／`transcript_path`／`cwd`／`hook_event_name`／`source`） |
| `/api/oauth/usage`（T5） | ✅ | ✅ ← repo 現行在用 |

**載具因素已排除**：同一份 `--settings` 檔同時掛 statusLine 與 SessionStart hook，
一次 `claude -p` 之後 `hook_fired=YES`／`statusline_fired=NO` ⇒ 不是 `--settings` 沒生效，
是**非互動模式沒有狀態列可畫，所以不呼叫 statusLine**。

⇒ **結論：對 AutoClaude 的主要使用情境（headless Playbook 執行、續航哨兵 tick），
PRD §0.6 第一列與紅線 1 的前提不成立；repo 走 T5 不是違規，是唯一可行的路。**
這同時解釋了 `core/ports/quota_meter.py` docstring 自陳的那個洞
（「額度軸會在無人看管那一跑上安靜地不存在」）為什麼**不能**用 statusLine 補。

**給下一輪的真題目**（原題目作廢）：headless 情境的刷新者只能是「自己去打 T5」，
那麼 ①誰來打（AutoClaude 不得 import harness ⇒ 要嘛引擎自己有一份取數器、要嘛
由外部排程器打完寫檔案契約）？②T5 失效時的降級路徑是什麼（PRD 對「內部介面」
的要求逐字是「必須有降級路徑，不可硬依賴」）？

其餘值得下一輪查的紅線：**紅線 10**（`.autoclaude/`、`.claude/settings*.json` 應列為
Agent 禁寫，否則「幫我把併發調高」就能拆掉整套治理）——本輪未查本 repo 有無此保護。

## 7. 禁止事項

- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`
- 不准設 `AUTOSDD_QUOTA_OFF`／改 `quota_meter.bucket_readings()` 之類的手法繞過 halt
  （`DEF-200-107` 的原樣重演）
- 不准把 `DEF-200-112`／`114` 的 ID 補進 `OVERSIZE_ROW_GRANDFATHERED` 讓帳本體積道轉綠
- 不准在無第三方複審的輪次改配速**取數層**（`record_burn`／`burn_ratio`／`bucket_readings`）
