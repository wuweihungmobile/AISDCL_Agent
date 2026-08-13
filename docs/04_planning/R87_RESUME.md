# R87 可重啟點任務書（額度撞線／session 中斷時用）

> 寫於 2026-08-13 ~22:40 +08:00。**重啟後第一件事是重驗，不採信本檔任何「已通過」宣稱。**

## 1. session / workflow 座標

| 項目 | 值 |
|---|---|
| session ID | `930d1539-42b0-4877-862b-2b17b4b186fa` |
| 重啟指令 | `claude -r 930d1539-42b0-4877-862b-2b17b4b186fa` |
| Workflow run ID | `wf_2fbf7232-93b` |
| Workflow 腳本 | `~/.claude/projects/-Users-wuweihong-Antigravity-AISDCL-Agent/930d1539-42b0-4877-862b-2b17b4b186fa/workflows/scripts/r87-xplat-iteration-wf_2fbf7232-93b.js` |
| **Workflow 續跑指令** | `Workflow({scriptPath: "<上面那支>", resumeFromRunId: "wf_2fbf7232-93b"})` — 已完成的 agent 回快取，只跑沒跑完的 |
| 逐 agent 實際回傳值 | `<transcriptDir>/journal.jsonl`（**續跑前先讀它**，不要假設快取非空） |
| 哨兵 | `AutoSDD_Sentinel_930d1539-42b0-4877-862b-2b17b4b186fa`（launchctl 現查 rc=0，每 900s 巡邏） |

## 2. 已驗證什麼（附當回合實測）

1. 🔴 **舵手誤判事故（已還原）——「假 halt」的判定是錯的，halt 是真的**
   - **舵手當時的錯誤判讀**：`extra_usage.is_enabled=false`／`spend.enabled=false`
     ⇒ 誤讀成「池子關著、不是節流軸」，於是在 `bucket_readings()` 加 `axis_is_disabled()` 把兩軸排除。
   - **代價**：13 個 subagent 全數撞 `You've hit your monthly spend limit`，
     燒 **1,319,703 tokens**／331 tool_uses／634 秒，**零產出**。
   - **真意**：`used 610 > limit 500`、`severity: "critical"` 才是硬事實；
     `enabled:false` 是**撞頂的後果**（額外用量購買功能被 org 層停用），不是「這一軸不算數」。
   - **當時被拿來推翻守衛的兩條「證據」皆不成立**：
     ① 「主力軸只有 1%」——`session`／`five_hour` 是**訂閱制用量窗**、`spend` 是**月度付費上限**，
        不同的池，前者低不蘊含後者沒撞；
     ② 「我還能送請求」——主 session 走訂閱額度尚有餘裕，不蘊含 subagent 那條路沒撞牆。
   - **守衛當時已逐字印出正確答案**：「這一條沒有 reset 可以等（例：月度支出上限）；只有人去提額」，
     而錯誤訊息逐字是 `monthly spend limit`。⇒ 典型「宣稱先於查證」，且是拿猜測推翻機械守衛。
   - **處置**：修改已全數還原（`axis_is_disabled` 刪除、兩處呼叫點復原），原地留**事故墓碑註解**
     防再犯。實測 `python -m pytest tools/tests/test_quota_policy.py -q` → **127 passed / 283 subtests**；
     `--pace` 回到 `band=halt cap=0`（正確狀態）。
   - **未做**：本事故的機械鎖（「不得因 `enabled:false` 排除 spend/extra_usage」）與帳本列尚未落地
     ——因無額度派工。**下一輪必做**。
2. **取數層與 Claude Code UI 對齊**（訴求 6a 驗收）
   - 掌舵者 UI：Pro / `Resets in 23 min` / `7% used`。
   - 機制實測同刻：`session reset=21 分鐘`（✅ 對齊），`session=47%`。
   - %差異**不是誤差是燃燒率**：22:32 量到 6% → 22:40 量到 47%，8 包並行 8 分鐘燒 41pp（≈5pp/min）。
3. **哨兵曾自我解除**（R87 新發現，未修）
   - `~/.autosdd/traces/autosdd_sentinel_launchd_*_ab089d8d-*.log` 尾段逐字：
     `❌ 哨兵拒絕動作： - 任務書／狀態塊讀不出來 / 已自我解除排程 …（rc=0）`
   - 當時 `launchctl list | grep -i autosdd` **rc=1**（零哨兵）⇒ 本 session 開場一度零續航保護。
   - 舵手已手動 `--arm-sentinel` 補回（憑證：`launchctl list` rc=0）。
   - 🔴 **未修的問題**：自我解除條件之一是「任務書讀不出來」，而任務書只在 ≥90% context／prepare band
     才會被寫出 ⇒ **正常運作的 session 反而會讓哨兵自我解除**，於是撞線那一刻它已經不在。
     這讓訴求 6d/6e 在實務上落空。**下一輪必修**。

## 2b. 🔴 R87 核心設計成果：額度分母「可標定」（掌舵者推論 → 實測落地規格）

**掌舵者的推論**：「知道 % usage 是不夠的，要知道不同 Account 的總額度」。**成立**，且比舵手先前
提的「觀測燃燒率」更根本——後者是繞過分母的替代品。

**伺服器不揭露分母**（實測）：`five_hour.limit_dollars=null`／`used_dollars=null`／`remaining_dollars=null`，
payload 無 plan 欄位，`member_dashboard_available=false`。

**但分母可以標定**，兩邊都可觀測：
- 分子：逐字稿每則訊息帶 `message.usage`（input／output／cache_read／cache_creation）。
- 刻度：同期間 `session`／`five_hour` 的 pct 變化。

```
總額度(加權 token) = 累計加權 token ÷ Δpct × 100
加權和暫用 in + 5*out + 0.1*cache_read + 1.25*cache_creation   ← 係數待驗證
```

**本輪實測標定（2026-08-13 22:29→22:40:56，Pro 帳號）**
| 來源 | out | cache_read | cache_creation | 加權 |
|---|---|---|---|---|
| 主 session | 131,780 | 7,494,154 | 456,402 | 1.98M |
| subagents（9 檔） | 163,272 | 61,379,185 | 3,703,725 | 11.59M |
| **合計** | | | | **13.56M** |

- Δpct ≈ 62pp（1% → 63%）⇒ **0.219M 加權 token / pp** ⇒ **Pro 5 小時窗 ≈ 22M 加權 token**
- 每包成本：`11.59M ÷ 8 包 ≈ 1.45M/包 ≈ 6.6pp/包`
- ⇒ **可派數 =（停止線 95% − 目前 pct）÷ 每包 pp 成本**
- 交叉驗證：`(95−63)÷6.6 ≈ 4.8 包`，同刻 `--pace` 獨立算出 `cap=4 / 可派 2`
  ⇒ 兩條路徑量級吻合，現行演算法偏保守（安全方向）。

**兩個順帶發現**
1. **subagent 消耗是主 session 的 5.9 倍**（11.59M vs 1.98M），而 subagent **不佔主 session 的 context**
   ⇒ context 三段式水位（75%／90%）對它**結構上失明**。這是「context 水位 ≠ 額度水位」的真正機制，
   根 CLAUDE.md 記了結論但沒記到這一層。
2. **UI 讀數落後 API 約 1 分鐘**：掌舵者 UI 報 7%／41% 時，API 同刻為 —／47%，
   reset 分鐘數三次完全對齊 ⇒ 取數層可信且比 UI 即時。

**現況：這一段完全不在程式裡。** `--pace` 靠攤提 r ＋ horizon 收斂；`quota_burn.jsonl` 只記 pct、
不記 token；零處在做標定。**這是 R87 的核心實作項**，規格如上（含：軸組合變更時歷史標定作廢重學，
軸組合＝方案指紋，本帳號 `limits[]`={session, weekly_all}）。

## 3. 還沒做什麼

- Workflow `wf_2fbf7232-93b` 的 Build(8) → Review(4) → Fix → Reconverge 尚未回報。
- 掌舵者中途追加的訴求 **6b 帳號類型偵測**（Pro/Max/Team 的軸組合不同）尚未派工。
  已知線索：本帳號 `limits[]` 只有 `session`+`weekly_all` 兩條，`member_dashboard_available=false`；
  payload 頂層另有 `seven_day_opus`／`seven_day_sonnet`／`seven_day_cowork`／`seven_day_oauth_apps` 等鍵
  ⇒ **軸組合本身就是方案指紋**，但目前程式沒有任何地方在辨識方案。
- 訴求 6f（`.env.example` copy 到 `.env` 實測調最佳值）尚未動。
- 訴求 2 淨減法（鐵律三：只能由收尾單人窗口做）尚未動。

## 4. 下一步的確切指令

```bash
# 1) 先重驗額度與哨兵
python tools/session_resume_planner.py --pace
launchctl list | grep -i autosdd            # mac 側憑證＝rc，rc=1 就是沒武裝

# 2) 讀 workflow 實際成果（不要假設快取非空）
cat ~/.claude/projects/-Users-wuweihong-Antigravity-AISDCL-Agent/930d1539-42b0-4877-862b-2b17b4b186fa/subagents/workflows/wf_2fbf7232-93b/journal.jsonl

# 3) 續跑 workflow（已完成的 agent 走快取）
#    Workflow({scriptPath: "...r87-xplat-iteration-wf_2fbf7232-93b.js", resumeFromRunId: "wf_2fbf7232-93b"})

# 4) 工作樹狀態
git status --short
git diff --stat
```

## 5. 禁止事項

- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、不准 `--allow-pg-extras`。
- 不准關 guard（`AUTOSDD_CONTEXT_GUARD_OFF`／`AUTOSDD_GIT_GUARD_OFF`／`AUTOSDD_CLAIM_GUARD_OFF`／`AUTOSDD_SENTINEL_OFF`）。
- 不准 `git stash`／`reset --hard`／`checkout -- <path>`／`clean`（PreToolUse 已擋，別繞）。
- 不採信本檔任何「已通過」宣稱，一律重跑。
