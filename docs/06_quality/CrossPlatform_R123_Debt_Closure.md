# R123 精準修復輪第二棒 — 缺陷結案存證

> **性質**：技術債總清償循環令第五投的第二棒。上一棒（R122）已 commit／push／雲端全綠＝
> 已收輪；本棒是其後的新一批，故另立輪號（守衛線款(11) 的「拆輪次不是拆列」＝判準自己
> 列出的合法出口，逐字理由寫在 `_GUARD_LINES_REPIN_LOG` 的 R123 列）。
> **帳本未結列**：起 41 → 訖 **40**（結 `DEF-200-200`／`DEF-200-205` 兩筆；`DEF-200-183`
> 轉 `partial`〔判準仍計為未結〕；新立 `DEF-200-246` 承接 205 的殘餘）⇒ 淨減 1。
> **護欄層**：`91668→91990`（淨額 +322），款(10) 上限 559 未撞；上一棒 −125 已使款(11)
> streak 歸零，本棒為其後第一個正淨額輪。
> **體例**：不使用「延後到R／交給R／留給R／承接輪次：R」等前瞻輪號句型。轉述並行包交件
> 一律標 `[他包回報]`；主控親跑者不標。

---

## §0 派工與防互踩

三筆取自 `docs/04_planning/AutoSDD_TechDebt_Paydown_Playbook.md` §A.1 標 `dev｜M/L｜高信心`
且**鎖持有面互不重疊**者（鐵律七的並行前置檢查）：AutoClaude 子專案／quota 族／skip 族。
三包各自拿到**行數預算 ≤200**（上一棒的教訓：加回歸鎖會撞守衛線款(10)(11)，抵銷搬遷必須
與修復同批規劃，不是事後補）。實測三包合計 `tools/tests` 淨增 +310，皆在預算內、無人超支。

每份任務書另加一條：**先自己複驗「缺陷今天還在不在」**——這些列是數十輪前寫的，可能早已
被順手修掉而沒人回頭結案。本棒三筆複驗結果皆「仍成立」，其中一筆的**卡點**已過期（見下）。

---

## §DEF-200-200 「已過去的 resets_at」四層各自誤判

**缺陷**：同一個欄位（額度視窗「幾點重置」）在四層各自誤判——① 快取在 TTL 內但已跨窗
⇒ `--pace` 拿死窗值當現值；② `_delta_minutes` 把**任何**負值標 `clock-skew`（本機時鐘
實測無偏移）⇒ 指向錯的子系統；③ 呈現層把已過去的時刻播報成「很快會自己解除」；
④ `row_of()` 不落 `resets_at`（是驗證①②③ 的前提）。

**四項今天全部仍成立**（`[他包回報]` 親跑探針，逐項貼出實測）：

| 項 | 實測 |
|---|---|
| ① | `cache age=60s TTL=180s usable=True` ／ `resets_at` 已過去 30 秒 ／ `decide → band='halt' cap=0`（拿死窗 pct 當現值） |
| ② | `resets_at` 過去 5 分鐘 → `(-5.0, 'clock-skew')` |
| ③ | `reset_branch(past) → arm`；`throttle_horizon_line` 逐字輸出「（6 小時內）⇒ 這道節流很快就會自己解除」 |
| ④ | `row_of()` keys = `['fp', 'live', 'pct', 'ts']` |

③ 原記「未複驗」，**本棒首次複驗即成立**：負的時間差當然 `≤6h`，於是句子逐字說「很快就會
自己解除」。

**落地**：共用述詞 `expiry_of()`／`expired()` 落 `tools/lib/quota_pace.py`（葉子模組、零同層
import ⇒ 無循環），四層改為委派。🔴 **它把兩義分流**（這是本筆的驗收核心，不是把同一個
bug 集中到一處）：

- `resets_at < measured_at` ⇒ 伺服器在發問那一刻就給了已過去的視窗，活著的視窗結構上不
  可能如此 ⇒ `clock-skew`（先校時）
- `measured_at ≤ resets_at < now` ⇒ 量的時候還沒到、現在到了 ⇒ `elapsed`（重量一次）
- **參考時刻解不出時退回 `elapsed`，不得指控時鐘**——那正是 ② 的病灶（無證據的歸因）

`read_quota()` 對跨窗讀數降級為 `expired-window`，與既有 `stale-cache` **reason 分得開**。
`row_of()` 加 `resets=`、新增 `resets_from_jsonl()` 讀取面，**舊列缺欄位仍可讀**。

**回歸鎖**：`tools/tests/test_quota_policy.py::TestDef200200ExpiryPredicate` 六支。
`[他包回報]` 五次突變逐一驗紅，其中 MUT-2（`expiry_of` 恆回 `EXPIRY_SKEW`）紅字為
`Tuples differ: ('clock-skew', 'clock-skew') != ('elapsed', 'clock-skew')`——那就是「兩義
分流真的有鑑別力」的機械證明。

**生產落款實證**（`[他包回報]`，同一次 `--pace` 寫下）：`rows with resets_at: 1 / legacy
rows without it: 58`、`rows_from_jsonl still parses: 59 rows` ⇒ 58 列舊樣本沒整批作廢也沒炸。

**殘留（誠實列，不阻結案）**：① 的降級粒度是「整份讀數」而非單軸（快取是單一
`measured_at` 的快照，per-axis 動刀需新造「部分可用狀態」這個概念；已加對照組鎖住「reset
在未來的讀數不得被一起吃掉」）；halt 訊息路徑只拿到 `now`、拿不到 `measured_at`，故該路徑
只能回「已過去（成因未定）」——**無參考時刻不得指控時鐘**，這是劃界不是漏接；
`quota_reconcile.py` 尚未改用新欄（本機落款只有一列帶它，不足以做假紅普查），理由已寫進
該檔檔頭並登記為殘餘。

---

## §DEF-200-205 兩支 PRD 模組零生產呼叫端

**缺陷**：`dirty_worktree_rescue.py`（PRD §4.5.9）與 `boot_self_check.py`（§6.2）**機制蓋好
沒接電**——排除自身與 `/tests/` 後全 repo 零生產呼叫端。

**今天仍成立**（`[他包回報]` 親跑 Grep）：兩組符號的生產碼命中**只有模組自己**，其餘全是
`docs/*.md`、`AutoClaude/tests/`、與兩句註解。另補查坐實「啟動面 100% 由 `main()` 覆蓋」：
`AutoResumeService(` 全 `autoclaude/` 只有一個建構點（`main.py`），而兩個 production entry
（`python -m autoclaude` 的 `__main__.py`、`pyproject.toml` 的 console script）都走
`autoclaude.main:main`。

**接點與理由**（不是「哪裡塞得進去」）：

| 模組 | 接點 | 為什麼語意正確 |
|---|---|---|
| `boot_self_check`（§6.2） | `main.main()`，`state_repo` 建好之後、`build_kernel` 之前 | §6.2 三項條文逐字都是「**啟動時**判一次」，而本實作的「一次啟動」＝一個被叫起來的行程 ⇒ 行程入口才是那一刻（放進 auto-resume 迴圈會變成「每輪重判」＝另一個語意）。且 `problems` 非空須以**非零退出碼**結束，只有 `main()` 握得到行程 rc |
| `dirty_worktree_rescue`（§4.5.9） | `AutoResumeService.run()` 的 halt 分支，`_persist_halt_checkpoint` 之後、等待／auto-resume 之前 | R-4.5.9-4 的進入條件就是「即將轉入 `WAITING_RESET`／`LONG_HIBERNATE`」，而 halt→等待是本實作唯一的凍結點。救援回 `DIRTY_UNSAVED` ⇒ 就地 `return`，**不睡、不續跑**（絕不 fail-open） |

**跨的架構邊界**：消費端 `core/services/auto_resume.py` 受 core-purity contract 管、不得
import infra ⇒ 新增 port `core/ports/worktree_rescue.py`，adapter 實作它、`core/wiring.py`
建構、`main.py` 注入。狀態字面搬進 port（消費端讀不到 adapter；字面留兩份時漂移方向是
「消費端沒跟著改」⇒ 比不中 ⇒ fail-open）。

**兩個「為了不硬塞」而加的東西**（`[他包回報]`，皆附理由）：adapter 先
`rev-parse --show-toplevel` 正規化工作樹（`diff HEAD --name-only` 回根相對、
`ls-files --others` 回 cwd 相對 ⇒ 從子目錄跑會讓 untracked 那半靜默判失敗）；新增第三個
狀態 `CLEAN`——乾淨工作樹送進救援序列會產生 0 bytes patch 而被判 `DIRTY_UNSAVED`
⇒ 每一次乾淨的 halt 都拒絕續跑＝假紅。判準因此收在 `status ∈ UNSAFE_TO_FREEZE`
（明確不安全那一側），不是 `== SAVED`。

**回歸鎖**：`AutoClaude/tests/integration/test_def_200_205_production_wiring.py` 二十一支，
一律從**入口**驅動（真 `main.main()`／真 `AutoResumeService.run()` ＋真 git 工作樹），斷言
磁碟產物與外部可觀測效果，不斷言「某個 mock 被叫到」。`[他包回報]` 三次拔線突變各自轉紅
（拔救援呼叫 3 紅／拔 boot 自檢呼叫 3 紅／拔 port 注入 1 紅）。

**閘門**（`[他包回報]`）：`lint-imports` rc=0、`Contracts: 9 kept, 0 broken`（含 core-purity
與 no-harness-import）；`check_loc_budget` rc=0 零違反；AutoClaude 全套
`4813 passed, 10 skipped`；`snapshot_sync.py --check` 修前 rc=1 DRIFT、重生後 rc=0。

🔴 **主控裁決一件越界**：該包改了 `AutoClaude/CLAUDE.md`——`snapshot_sync.py` 機械重生
Architecture Snapshot（Port 數隨新 port 上升）＋移除一個多餘空行以維持該檔 400/400
（餘裕為 0，加一行即破 `special<=400` 棘輪）。**接受**：快照重生是該檔自己的機械義務
（不重生則 `--check` 恆紅），等量減法是該棘輪指定的償付方式。

**殘留已切獨立列 `DEF-200-246`**（見下）：PRD §6.2 的另兩個半邊在生產上仍不可達。不併回
本列的理由＝本列判準逐字是「零生產呼叫端……接上生產呼叫端」，而那兩件事是**條文的其他
半邊未實作**，語意已漂；留在本列會讓它變成一個永遠關不掉的列。

---

## §DEF-200-183 剖面鍵欠一軸（partial，不結案）

**缺陷**：skip 統計的剖面鍵少了 pgextras 這一軸 ⇒ 同一鍵在兩種環境量到兩個值，任填一值
必然「一邊零鑑別力、另一邊恆假紅」。

**今天仍成立，且同數復現**（`[他包回報]`，同一棵樹、唯一變因＝pg extras 可否 import）：

```
AutoClaude/tests@win32+nopg+nested  extras PRESENT：untagged=96   （census rc=0）
AutoClaude/tests@win32+nopg+nested  extras ABSENT ：untagged=162  （census rc=1）
```

untagged 96／162／差 66 與帳本記的 darwin 實測**逐字同數** ⇒ 缺陷在鍵的**文法**，不是
mac 特例；一邊零鑑別力、另一邊恆假紅兩向今天都實測到了。

🔴 **登記面實測十三層，不是帳本以為的四層**。其中四層（`local_ci_gate._skip_profile()`／
marker 傳輸鏈／`conftest.py` 發射端／`test_local_ci_gate.py` 回歸鎖）住 `AutoClaude/`
持有面 ⇒ **依鐵律七，任一並行包手上都做不完**。

**已落地**：鍵文法 SSOT 新檔 `tools/lib/skip_profile_key.py`（軸宣告／唯一產生器
`census_profile()`／`profile_axis_problems()`／`legacy_profile()`／`keys_missing_axes()`）；
`skip_group_policy.py` 改為消費該 SSOT 並把軸判準接到兩條 advisory 通道；root 樹生產者
`skip_census_profile()` 改由文法產生（鍵字面零變更）；方向鎖比對面改走 `legacy_profile()`
＋裂鍵每個後代都受約束＋凍結鍵落空改出聲。九支新測試、`[他包回報]` 八次突變逐一驗紅。

**刻意不做的事（這是判斷，不是漏做）**：生產者未帶軸時**先** re-key 那幾張表，會讓
AutoClaude 那一棵的天花板整批退回 advisory＝比今天更沒有牙（假綠）。改為上一道機械化的
完成度棘輪 `PRE_AXIS_KEY_DEBT_MAX`（今天缺軸的鍵數，**只准降**，新增歧義鍵當場紅）；
生產者落地那一輪 re-key 完就把它降到 0。

**為何仍 `partial` 而非 `fixed`**：缺陷本體是「生產出來的鍵少一軸」，而今天實跑
`--census-only` 吐出的鍵仍是三軸、仍然歧義。advisory 現在會逐字說出這件事，但那是**診斷**
不是**修好**。

**「是否由 advisory 轉登記」——本棒不轉**（`[他包回報]` 建議，主控採納）。轉登記＝把實測值
填進天花板，而今天填哪一個值都仍是那個歧義鍵的值：填 96 則 ABSENT 環境恆假紅、填 162 則
PRESENT 環境的空窗由二十二格擴大到六十六格（鑑別力更差）。正確前置順序＝(a) 生產者帶上
第四軸 →(b) 兩個剖面各自實測 →(c) 三張表同 commit 入表且無餘裕 →(d) 完成度棘輪降為 0。
顛倒順序（先填數字）只會得到一個沒有消費者的常數。

**其餘殘留**：extras ABSENT 剖面是以 meta_path finder **模擬**（對 `import`／`find_spec`／
`importorskip` 三種偵測面等價，但不等於真的沒安裝）——刻意不動共用 `.venv`，因為兩個並行包
正在用它；`AISDLC_SDD/fsm_runtime` 樹宣告零軸是「尚未接閘門」的現況登記，不是查證過它沒有
能力軸；darwin／linux 剖面本棒未實測（本機 Windows）。

---

## §DEF-200-246 PRD §6.2 兩個半邊在生產上不可達（本棒新立）

自 `DEF-200-205` 結案時切出的獨立載體。兩項皆**刻意未做**且附理由：

1. **`dry_run` 判決未接到執行器**：R-6.2-2 的「DRY_RUN 真的不動作（不派工）」那一半刻意
   未接——已驗證清單現況只有兩個版號，接上去等於幾乎所有使用者的 playbook 都被靜默降級
   成不動作，而那種守衛會被整個關掉。本棒只交付另一半：桌面通道 loud 一次 ＋ 自檢輸出印
   「本次以 DRY_RUN 執行」與確認方式。
2. **`integration_queue` 零生產寫者**：`autoclaude/` 只有欄位定義與讀者，零寫入點（多 agent
   worktree 整合本身還沒實作）⇒ R-6.2-1 的佇列掃描雖已接電，其輸入在生產上結構性恆空。

另兩項**不併入本列**、已有別的承接：`CONFLICT_POLICY` 仍無 config／env 家（預設
`HUMAN_REVIEW` ⇒ 重排分支在生產上不可達）與 `DIRTY_SAVE_RETRIES` 零 env 讀取路徑，皆屬
`DEF-200-206` ③ 的射程（該列註明需四方裁決「修實作 vs 修憲」）。legacy `PlaybookRunner`
facade 的 halt 路徑未接救援，已查證它不在任何 production entry 的可達鏈上，判為非缺口。

---

## §誠實劃界

1. **本棒三筆修復皆未經四方定點複審**，依成熟度判準 M3「作者自證不計分」屬自證。
2. `DEF-200-183` 的 re-key 主體仍在 `AutoClaude/` 持有面，需獨立的收尾單人窗口。
3. 三包皆未跑根層全套（任務書禁令，避免並行互踩）；全套由收尾單人窗口在所有包停工後跑。
4. 帳面淨減只有 1（結兩筆、轉一筆 partial、立一筆新列）——**新立列是誠實成本**，不立會讓
   205 結案後那兩件事失去載體（`DEF-200-213` 的教訓：結案前必查是否令他處失承接目標）。
