# R90 跨帳號實驗：`status` 枚舉四通道實測 ＋ `plan_fingerprint` 雙向證偽

> **本檔為什麼存在（＝資格，不是分類）**：掌舵者在 R90 進行中把本機帳號由 Pro 切到 Team，
> 這讓一個此前被判「結構上驗不到」的對照組**在 20 分鐘的窗口內真的成立了**——切換前後的
> 落款同住一份 `quota_burn.jsonl`，兩個帳號的讀數逐列可比。這種一手資料**不可重製**
> （切回去要動掌舵者的帳號），而 R85 教訓 5 逐字判過「做了但不落磁碟＝沒發生」。
>
> 🔴 **命名刻意不用 `CrossPlatform_` 前綴**：`tools/lib/governance_docs.py` 的
> `_GOVERNANCE_DOC_GLOB = "CrossPlatform_*.md"` 會把符合該慣例而未登記者判 rc=1，而登記面
> （`_GOVERNANCE_DOCS`）不在本包持有面內（鐵律七）。本檔主題是額度／帳號，不是跨平台，
> 兩個理由同向。**若四方認為它應受體積守門＋指針稽核**，改名與登記的確切座標見文末
> 〈待主控轉交〉第 3 項。

**量測環境**：macOS darwin 25.5.0；`claude` CLI **2.1.233**
（`/Users/wuweihong/.local/share/claude/versions/2.1.233`，306,981,408 bytes）；
本 repo `.venv`；量測時刻 2026-08-15 13:35~13:37 (+08:00)。
**本包一手實測與轉述的分界**：凡標 `[他包回報]` 者為引用，本包**不可複驗**，理由逐項寫在該處。

---

## 一、`status` 枚舉的四通道實測（本包一手，全部可重跑）

### 1.1 結論

PRD 三處指定 `status`（`allowed` / `allowed_warning` / `rejected`）為權威狀態訊號：
`:79`（§0.6 新發現 2）、`:1372`（§15.5 紅線 7）、`:1529`（附錄 B-13）。
**只有 B-13 那一處說出了它住在哪**——限流回應標頭。另兩處沒有通道限定詞，
照字面實作會寫出一段永遠走不到的死碼。

### 1.2 逐通道量測

| # | 通道 | 判準 | 實測 |
|---|---|---|---|
| ① | `GET /api/oauth/usage` 的 **body** | `status` 鍵／三個枚舉值出現次數 | 全部 **0**；頂層 17 鍵無一為 `status` |
| ② | 同一支 API 的**回應標頭** | 有無 `anthropic-ratelimit-unified-status` | **無**；15 個標頭中含 `ratelimit` 者 **0 個** |
| ③ | **statusLine stdin JSON**（PRD §B-05 指定的通道） | CLI 自帶 schema 內 `rate_limits.*` 的欄位 | 只有 `used_percentage` 與 `resets_at`，**無** `status` |
| ④ | **逐字稿** `~/.claude/projects/<slug>/*.jsonl` | `"status"` 的值域 | 13,834 次命中，值域全為 TodoWrite／Task 狀態；三個枚舉值各 **0** |

**通道①②原始輸出**（探針一次網路呼叫，非模型請求 ⇒ 不吃額度）：

```
HTTP 200  body_bytes=1787
  body 內 'status' 出現次數 = 0
  body 內 'allowed_warning' 出現次數 = 0
  body 內 'allowed' 出現次數 = 0
  body 內 'rejected' 出現次數 = 0
  body 內 'rateLimitType' 出現次數 = 0
  頂層鍵（17）= ['amber_ladder', 'cinder_cove', 'extra_usage', 'five_hour',
   'iguana_necktie', 'limits', 'member_dashboard_available', 'nimbus_quill',
   'omelette_promotional', 'seven_day', 'seven_day_cowork', 'seven_day_oauth_apps',
   'seven_day_omelette', 'seven_day_opus', 'seven_day_sonnet', 'spend', 'tangelo']
  標頭數 = 15
  含 'ratelimit' 的標頭 = []
  'anthropic-ratelimit-unified-status' 在標頭內 = False
```

**通道③原始輸出**（CLI 二進位內自帶的 statusLine schema 註解，逐字）：

```
     "rate_limits": {             // Optional: Claude.ai subscription usage limits. Only present for subscribers after first API response.
       "five_hour": {             // Optional: 5-hour session limit (may be absent)
         "used_percentage": number,   // Percentage of limit used (0-100)
         "resets_at": number          // Unix epoch seconds when this window resets
       },
       "seven_day": {             // Optional: 7-day weekly limit (may be absent)
         "used_percentage": number,   // Percentage of limit used (0-100)
         "resets_at": number          // Unix epoch seconds when this window resets
       }
     },
```

**通道④原始輸出**（54 支逐字稿，遞迴取所有 `status` 鍵的字串值）：

```
逐字稿數 = 54    '"status"' 出現次數 = 13834
值域 = [('completed', 6588), ('pending', 5036), ('in_progress', 1822),
        ('async_launched', 369), ('running', 3)]
  枚舉值 'allowed' 命中 = 0
  枚舉值 'allowed_warning' 命中 = 0
  枚舉值 'rejected' 命中 = 0
```

### 1.3 枚舉確實存在，只是不在這四條路上

CLI 二進位（2.1.233）內：

```
strings 命中行數 allowed_warning                    = 17
strings 命中行數 anthropic-ratelimit-unified-status = 14
```

**相鄰性佐證**（本包補做，比「兩者都存在」強一級）：兩個字面在
**5 個位元組偏移上完全重合**（同一條 `strings` 輸出行同時含兩者）——
`270228902`、`277174577`、`294246342`、`294263808`、`294277472`。
⇒ 標頭名與枚舉值住在同一段程式碼的同一個運算式裡，而非各自獨立出現。

**推論**：枚舉住在**模型 API 呼叫的限流回應標頭**，由 CLI 自己消費、不對外轉發。
而本 repo 護欄層從不發模型請求（`tools/lib/quota_meter.py` 檔頭逐字：
「這個呼叫**不是**模型推論」⇒ 不吃額度、不進 5 小時視窗）
⇒ **護欄層結構上永遠拿不到這個枚舉。**

### 1.4 覆蓋邊界（誠實劃界）

- 「四條通道」是**本機可達**通道的窮舉，不是全世界通道的窮舉。若未來有元件真的去發模型
  請求（例如 AutoClaude 的 Brain adapter），那條路上枚舉是拿得到的——PRD 三處的原始語意
  對**那種**元件仍然完全成立，本輪補的限定詞正是為了把兩種元件分開。
- 通道②的量測是**單一帳號、單一時刻**。標頭在限流「將要發生」時才附帶的可能性未被排除；
  但那不影響結論——護欄層連 `allowed` 都沒收到過，代表這條路上根本沒有這組標頭。
- `strings` 命中數是**行數**不是出現次數（同一行含兩次只算一行）。這對結論無影響
  （判準是「有沒有」與「同不同行」）。

### 1.5 一行複跑

```bash
# 通道①②（發一次非模型請求；不吃額度、不進 5 小時視窗）
python - <<'PY'
import json, sys, urllib.request
sys.path.insert(0, "tools/lib"); import quota_meter as qm
req = urllib.request.Request(qm.USAGE_URL, headers={
    "Authorization": f"Bearer {qm.access_token()}", "anthropic-beta": "oauth-2025-04-20"})
with urllib.request.urlopen(req, timeout=10) as r:
    hdrs, raw = dict(r.headers.items()), r.read().decode()
for t in ("status", "allowed_warning", "allowed", "rejected"):
    print(f"body {t!r} = {raw.count(t)}")
print("含 ratelimit 的標頭 =", [k for k in hdrs if "ratelimit" in k.lower()])
print("org =", hdrs.get("anthropic-organization-id"),
      "| ws =", hdrs.get("anthropic-workspace-id"))
PY
# 通道③
strings -a "$(python -c "import os,shutil;print(os.path.realpath(shutil.which('claude')))")" \
  | grep -A9 '"rate_limits": {'
# 通道④
grep -oh '"status"' ~/.claude/projects/-Users-wuweihong-Antigravity-AISDCL-Agent/*.jsonl | wc -l
```

---

## 二、跨帳號實驗：`plan_fingerprint` 兩個方向都被證偽

### 2.1 對照組是怎麼成立的

`~/.autosdd/traces/quota_burn.jsonl` 是**持久**落款（37 列，
`2026-08-12T22:45:43+08:00` → `2026-08-15T13:35:06+08:00`）。
帳號切換發生在 `13:12:01` 與 `13:32:06` 兩列之間，**兩個帳號的樣本因此同住一份檔**：

```
  2026-08-15T13:05:58+08:00  seven_day=50.0  spend=100.0  extra_usage=100.0
  2026-08-15T13:12:01+08:00  seven_day=53.0  spend=100.0  extra_usage=100.0   ← 舊帳號末列
  2026-08-15T13:32:06+08:00  seven_day=0.0   spend=0.0    extra_usage=None    ← 新帳號首列
  2026-08-15T13:35:06+08:00  seven_day=1.0   spend=0.0    extra_usage=None
```

🔴 **`seven_day` 在 20.1 分鐘內由 53 → 0**。七日窗結構上不可能這樣重置
⇒ 這一列本身就是「換了帳號」的鐵證，而**它不需要任何指紋機制就看得見**。

### 2.2 方向 A — 偽陰性：舊帳號有 10 列的指紋與新帳號**逐字相同**

新帳號指紋（`--pace` 與本包獨立重算皆同）：

```
five_hour+nimbus_quill+session+seven_day+spend+weekly_all+weekly_scoped
```

對 37 列逐列重算 `plan_fingerprint`（＝`sorted(kind)`，與
`tools/lib/quota_meter.py::account_posture` 同式）：

```
  切帳號前列數=35  切後列數=2
  切帳號前指紋與新帳號**逐字相同**的列數 = 10 / 35
    2026-08-12T22:53:14+08:00
    2026-08-12T23:34:56+08:00
    2026-08-13T00:08:21+08:00
    2026-08-15T00:37:08+08:00
    …（共 10 列）
```

⇒ **29% 的舊帳號樣本與新帳號無法區分。** 這不是 Pro→Pro 同方案的邊界情形——
本次是 **Pro→Team 跨方案**，指紋照樣撞。

> 🔴 這比 `quota_meter.py::account_posture` docstring 現有的劃界更嚴重。該處逐字寫
> 「同方案的兩個帳號指紋逐字相同 ⇒ Pro→Pro 換帳號這一型，靠指紋結構上抓不到」——
> 語氣像是「跨方案就抓得到」。本輪實測：**跨方案也撞**。

### 2.3 方向 B — 偽陽性：同一帳號內指紋自己翻 8 次

```
  相鄰列指紋翻動次數 = 8（母體 37 列）
    2026-08-12T22:45:43 → 2026-08-12T22:53:14   間隔    7.5 分  差異軸=['five_hour','nimbus_quill','seven_day','spend','weekly_all','weekly_scoped']
    2026-08-13T00:08:21 → 2026-08-13T22:29:22   間隔 1341.0 分  差異軸=['extra_usage','weekly_scoped']
    2026-08-13T22:29:22 → 2026-08-13T22:32:38   間隔    3.3 分  差異軸=['extra_usage','spend']
    2026-08-13T22:40:56 → 2026-08-13T23:08:46   間隔   27.8 分  差異軸=['extra_usage','spend']
    2026-08-15T00:03:47 → 2026-08-15T00:27:57   間隔   24.2 分  差異軸=['nimbus_quill','weekly_all']
    2026-08-15T00:27:57 → 2026-08-15T00:37:08   間隔    9.2 分  差異軸=['extra_usage','nimbus_quill','weekly_all','weekly_scoped']
    2026-08-15T02:22:34 → 2026-08-15T12:40:36   間隔  618.0 分  差異軸=['extra_usage','weekly_scoped']
    2026-08-15T13:12:01 → 2026-08-15T13:32:06   間隔   20.1 分  差異軸=['extra_usage','weekly_scoped']  ← 唯一真的換帳號
```

8 次翻動裡**只有 1 次是真的換帳號**，其餘 7 次同帳號（含相隔 **3.3 分**與 **9.2 分**兩次）。

### 2.4 🔴 決定性的那一筆：真事件的簽章與非事件**逐字相同**

R89 收尾曾在帳本 `DEF-200-114` 列訂正過一句：「**本次不適用**，live 指紋已變
（`extra_usage` 消失、`weekly_scoped` 出現）⇒ **抓得到**，只是沒人看」。

**本包實測推翻它。** 換帳號那一筆的差異軸是 `['extra_usage', 'weekly_scoped']`，
而同一份落款裡有**兩筆同帳號**轉移的差異軸**一字不差就是這兩軸**：

| 時刻 | 間隔 | 差異軸 | 是不是換帳號 |
|---|---|---|---|
| `08-13T00:08:21 → 22:29:22` | 1341.0 分 | `extra_usage`, `weekly_scoped` | ❌ 否 |
| `08-15T02:22:34 → 12:40:36` | 618.0 分 | `extra_usage`, `weekly_scoped` | ❌ 否 |
| `08-15T13:12:01 → 13:32:06` | 20.1 分 | `extra_usage`, `weekly_scoped` | ✅ **是** |

⇒ 「抓得到」只在**已經知道答案之後**回頭看才成立。作為偵測器它**零鑑別力**：
同一個簽章在同一份資料裡對非事件觸發了兩次。
一個 3 命中裡 2 個是假陽性的訊號，接上「作廢重學」這種破壞性後果會是淨負值。

**根因（為什麼註定如此）**：`plan_fingerprint` 是 `sorted(kind)`，
而 kind 的有無取決於「這一次的 payload 裡那個桶在不在」——`extra_usage` 在餘額用盡／
未啟用時整個消失、`weekly_scoped` 在無 scoped 額度時消失。
**它量的是額度狀態，不是身分。** 拿狀態量當身分訊號，兩個方向的錯都是結構性的。

### 2.5 正解：`account_key` 有鑑別力，且零成本

`GET /api/oauth/usage` 的**回應標頭**（本包一手實測，見 §1.2 那次呼叫）：

```
  anthropic-organization-id = c7716c3e-4510-4d6e-9473-6c639f6c77d6
  anthropic-workspace-id    = wrkspc_01AaQ7rxzXCosJbx4LkJXQnn
  sha256(org:ws)[:12]       = 34cd3507237f
```

| 欄位 | 舊帳號 | 新帳號 | 變了？ |
|---|---|---|---|
| `anthropic-organization-id` | `8b63e143-0d4a-4c6a-a0fc-53229d07b7f5` `[他包回報]` | `c7716c3e-4510-4d6e-9473-6c639f6c77d6`（本包實測） | ✅ |
| `anthropic-workspace-id` | `wrkspc_01RVxG93ofY2Rq2SQyNhqHm5` `[他包回報]` | `wrkspc_01AaQ7rxzXCosJbx4LkJXQnn`（本包實測） | ✅ |

**兩個欄位都變了，且就在取數層已經在發的那一次回應的標頭裡**
⇒ 零額外網路、零額外 token、零額外憑證處理（標頭不是憑證，雜湊後更不是）。

> 🔴 `DEF-200-114` 原本把這條路寫成「涉及憑證處理，另案」——本輪實測**不涉及憑證**：
> 身分就寫在回應標頭上，`quota_meter.fetch_usage()` 現在就拿得到，只是把它丟掉了。

### 2.6 損害是**現在正在發生**的，不是理論風險

`record_burn()` 的去重鍵只有 `measured_at`（`tools/lib/quota_gate.py:280` 逐字
`if path.exists() and state.measured_at in path.read_text(...)`），
`burn_ratio()` 把整份落款無條件餵給 `estimate_ratio()`。本包實跑：

```
落款列數=36  種子觀測=2  ⇒ estimate_ratio r=7.55 note=n=10 ⇒ 取中位數
  切帳號前的落款列 = 34   切後 = 2
  estimate_ratio 的輸入未依帳號分割（rows 全數餵入）⇒ 混用 = True
```

而同一刻 `--pace` 印出的正是這個數：

```
攤提：kind=weekly_all 剩 99pp／距 reset 9623 分鐘 ÷ 32.1 個 kind=session 窗
      = 每窗 3.09pp ×r=7.5（n=10 ⇒ 取中位數）⇒ 本窗配額 23.3pp
```

⇒ **今天派工用的 r，是拿 34 列舊帳號（Pro，訂閱窗小）樣本 ＋ 2 列新帳號（Team）樣本
算出來的。** 且落款是持久的、快取 TTL 只有 180 秒 ⇒ **這個污染不會隨 TTL 自癒**。

### 2.7 覆蓋邊界（誠實劃界）

- **舊帳號的兩個標頭值本包不可複驗**：帳號已切換，那個 token 不在 Keychain 裡了。
  上表標 `[他包回報]` 的兩格引自 SD 於 R90 的量測，本包只能確認「新值與它們不同」。
- 落款只有 **2 列**新帳號樣本 ⇒ 「新帳號的燃燒特性」本身還沒有可用估計。本檔**不**主張
  r=7.55 偏高或偏低，只主張**它的樣本不同質**。
- 方向 A 的 10/35 是**這一份落款**的數，不是普適碰撞率。它足以證偽「指紋能當身分訊號」，
  不足以拿去當常數引用。
- 本檔**未**驗證：`account_key` 在**同一帳號跨機器**是否穩定（例如 org 相同、workspace
  不同）。若要當去重鍵，這一條必須先量——本包無第二台機器。

### 2.8 一行複跑

```bash
python - <<'PY'
import json, pathlib
rows=[json.loads(l) for l in (pathlib.Path.home()/".autosdd/traces/quota_burn.jsonl")
      .read_text(encoding="utf-8").splitlines() if l.strip()]
fp=lambda r: "+".join(sorted(r["pct"]))
for a,b in zip(rows, rows[1:]):
    if fp(a)!=fp(b):
        print(a["ts"], "→", b["ts"], sorted(set(fp(a).split("+"))^set(fp(b).split("+"))))
PY
```

---

## 三、待主控轉交（本包持有面之外，**本包一行都沒有動**）

### 3.1 `DEF-200-114` 帳本列（持有者：他包）

現行列的判讀已被 §2.4 證偽。建議把「狀態／備註」欄的 R89 收尾訂正段換成：

> 🔴 R90 跨帳號對照組（Pro→Team 真實切換）**推翻 R89 收尾訂正**：換帳號那一筆的差異軸
> `['extra_usage','weekly_scoped']` 與同帳號兩次轉移（相隔 1341 分／618 分）**逐字相同**
> ⇒ 3 命中 2 假陽性，作為偵測器零鑑別力；反向另有 10/35 舊帳號列與新帳號指紋逐字相同
> （跨方案也撞，不限 Pro→Pro）。正解＝`account_key`＝`sha256(anthropic-organization-id
> + ":" + anthropic-workspace-id)[:12]`，**就在取數層已經在發的那次回應標頭裡**，
> 零額外網路／token／憑證處理（原列「涉及憑證處理，另案」不成立）。
> 污染現正發生：`r=7.55` 由 34 列舊帳號＋2 列新帳號混算。
> 詳情＝`docs/06_quality/Quota_R90_CrossAccount_Experiment.md` §2。

### 3.2 `quota_meter.py::account_posture` docstring（持有者：他包）

`tools/lib/quota_meter.py:458-459` 現行逐字：
「同方案的兩個帳號指紋逐字相同 ⇒ Pro→Pro 換帳號這一型，靠指紋結構上抓不到，
要抓需要帳號識別（涉及憑證處理，另案）」——**兩個子句都被本輪實測收窄／推翻**：

1. 不限同方案，**跨方案（Pro→Team）也撞**；
2. 帳號識別**不涉及憑證處理**，`fetch_usage()` 那次回應的標頭就有。

### 3.3 若四方認為本檔應受體積守門＋指針稽核（持有者：他包）

改名 `docs/06_quality/CrossPlatform_R90_Quota_CrossAccount_Experiment.md`
並在 `tools/lib/governance_docs.py` 的 `_GOVERNANCE_DOCS`（現止於第 190 行
`CrossPlatform_R86_Scan_Findings.md` 那一筆）後補一筆：

```python
    # R90 跨帳號實驗（Pro→Team 真實切換，對照組不可重製）。資格＝它逐節寫出「某 DEF-ID
    # 的判讀現居本檔某節」的座標宣稱（⇒ 指針稽核），且複審者要重驗四通道與雙向證偽就得
    # 讀完它（⇒ 體積守門）。
    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R90_Quota_CrossAccount_Experiment.md",
```

本包**刻意不做**：登記面不在持有面內（鐵律七），且不改名時本檔不落在
`_GOVERNANCE_DOC_GLOB` 內 ⇒ 現況閘門不因它轉紅。
