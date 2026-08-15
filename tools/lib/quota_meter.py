"""額度水位取數器 — **唯一會為了額度碰網路的地方**（訴求 a）。"""
# WHY —— 為什麼新開這一支檔，以及它與既有三個家的分工
# ---------------------------------------------------------------------------
# 本 repo 判過「護欄層自我增殖是最大缺陷來源」，所以新開檔要辯護。三個理由都是量出來的：
#
#  ① `tools/session_resume_planner.py` 塞不下：落地當回合 `check_loc_budget.py` 實測
#     `[guardrail_cli<=750] tools/session_resume_planner.py: 749 （餘裕 1 行）`。
#     這是硬牆不是偏好，本包因此**一行都沒有動它**。
#     🔴 R84／ARCH-03 訂正這個數字的**性質**（不是訂正結論）：749／餘裕 1 是**立案當時的
#     量測值**，本檔此前把它寫成現況 ⇒ 今天已過期（R84 實測 734）。牆仍然在（同一個
#     tier、同一個 750），過期的是那個讀數。一律現查：
#     `python AutoClaude/tools/check_loc_budget.py --json`（`root_tools_*` 那幾格）。
#  ② 不能放進 `.claude/hooks/context_budget_guard.py` 的主路徑：那支 hook 在**每一次**
#     PreToolUse／PostToolUse 都會跑。把 HTTP 呼叫放進去＝給每一次工具呼叫加上網路延遲，
#     而該檔自己記載過 P0「hook 誤觸 deny 會把所有工具硬鎖死」。
#     **取數（會失敗、會慢、會逾時）與判讀（必須快、必須確定性）的失效模式不同，必須分開。**
#  ③ `tools/lib/quota_escalation.py`（R81 另一包）管的是**撞線之後**：叫人、快照被打死的
#     扇出。本檔管的是**撞線之前**：現在幾 %。兩者的輸入、失效模式、觸發時機都不同。
#
# 分工一句話：**本檔是唯一的取數者與唯一的寫者。**
#   quota_meter（本檔） ──寫──▶ 快取檔（檔名有**兩個必要的家**，見下方 `CACHE_NAME`）
#                                   ├──讀──▶ tools/lib/quota_gate.py（判讀＋動作）
#                                   │         └─由 .claude/hooks/context_budget_guard.py
#                                   │           try/except import（該 hook 本身**零**
#                                   │           `import quota_meter`）
#                                   └──讀──▶ AutoClaude adapter
#                                             （`autoclaude/infra/adapters/file_quota_meter.py`，
#                                              **已落地**，走檔案契約）
# 🔴 R84／ARCH-03 訂正上圖（原圖把讀者寫成 `context_budget_guard`、把 adapter 標成
# 「未落地」——兩者今天都為假，故不留著當現行說法）。改變的是**誰讀**：R82／Q2-02 把整條
# 額度軸搬進 `quota_gate.py` 之後，hook 只 import `quota_gate`，本檔的消費者是 `quota_gate`。
# 這種失真在本檔特別貴：分工圖就是「誰壞了要去看哪一支」的地圖。現查：
#   grep -rn "import quota_meter" tools .claude AutoClaude
#   grep -rn "autosdd_quota.json" AutoClaude
#
# 🔴 **R81 收斂訂正上面 ② 與本段原本的「消費端零網路」宣稱**（原說法不留著當現行說法）：
# 那個形狀有一個沒被看見的淨效果——快取一過期，`read_quota()` 正確地降級成「量不到」，
# 而「量不到就不節流」⇒ **過期就等於對任意規模的扇出全數放行**（複審探針實測：過期 600s／
# 額度 99% 時 42 次 `Agent` 派發放行 42）。且「過期」是常態：唯一的刷新呼叫點就在那條
# 支線上、哨兵巡邏不刷快取、TTL 只有 180 秒。
# ⇒ 現況是 hook 會在**扇出型工具 ＋ 已經量不到 ＋ 本 TTL 還沒人量過**三個條件同時成立時，
#   **同步**呼叫本檔的 `measure()`（有界逾時 4 秒，端點 RTT 實測 0.33～0.41 秒）。
#   ② 那條理由仍然成立的部分是它真正的射程：**不得讓每一次工具呼叫都碰網路**——今天
#   收斂型工具（讀檔／寫檔／跑 git）一次都碰不到這條路，那才是當初要避開的東西。
#
# 🔴 沒有東西被刪除或合併（本輪架構減法的誠實帳）：本檔是**淨增**。理由見上面三條；
# 唯一可以合併掉它的方式是把 planner 先做 ADR-XPLAT-004 已登記的 `session_endurance.py`
# 抽離，那不在本包射程內。這一筆要照實記進 Q2 的非淨減法帳。
#
# ── 口徑（訴求 a 逐字要求「要能說出它取的是哪一種計費口徑」）────────────────────
# server 依帳號方案自己算好 utilization 並回百分比 ⇒ **本機不再自行推導分母**。
# 🔴 這句話與「本 repo 不再擁有分母這個概念」不同（SA-B2 訂正）：payload 自己就把分母
# 命名出來了（`limit_dollars`／`used_dollars`／`remaining_dollars`，美元計價）。本帳號
# 這三格恰好是 `None`，但「這個帳號現在是 null」不等於「分母不存在」⇒ `denominator`
# 一律**從 payload 推導**，不得輸出一句對所有帳號都宣稱為真的散文。
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

#: 權威端點。來源不是猜的：`claude.exe` 內的實作逐字 `fetchUtilization: GET
#: /api/oauth/usage`。**這個呼叫不是模型推論** ⇒ 不吃額度、不進 5 小時視窗。
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"

#: 憑證檔（Claude Code 自己維護；互動 session 活著時它會自己 refresh 並回寫）。
#: Windows／Linux／WSL 走這一條；macOS 見 `_keychain_token()`。
CREDENTIALS = Path(os.path.expanduser("~")) / ".claude" / ".credentials.json"

#: 🔴 **R82／L4-03：macOS 的憑證不在檔案系統上，在 login Keychain。**
#: R81 版**刻意不加平台分支**，理由是「沒有 mac 真機，寫一個驗不了的分支正是 DEF-101-766
#: 的形狀」——那個理由對「寫一個猜出來的判準」成立，但它同時買下了一個更大的代價：
#: 切到 mac 之後 `CREDENTIALS` 恆不存在 ⇒ `measure_detail()` 一律回 `no-credentials`
#: ⇒ 整條額度軸永久 `unmeasurable` ⇒ R81 落地的 80%／95% 兩道門**結構上一次都到不了**，
#: 而外觀與「額度水位很低、很健康」完全相同（本輪 Windows 模擬實測：`quota_gate` rc=0、
#: `fanout_cap(None) is None`）。⇒ 「無法驗證」不是「不做」的理由，是「做成可被單元測試
#: 注入、並把未驗的那一半明說」的理由。
#:
#: 🔴 **上面那段的「誠實劃界」已由 mac 真機實測結清**（原文寫「service 名與 `-w` 取值
#: 形態是依已知行為寫的、沒有在 mac 真機上跑過」，並把真機驗證列為交棒項）。該段話今天
#: 起是假的，故不留著當現行說法——它假在「會讓人以為這條路仍未驗」的方向，而下一個人
#: 因此可能去重寫一條已經量得到的路。實測（darwin 25.5.0、本 repo `.venv` 3.11.15）：
#:     security find-generic-password -s 'Claude Code-credentials' -w
#:         → rc=0，stdout 568 bytes、首字元 `{`（JSON 形態，走 `_token_of` 那條）
#:     python tools/lib/quota_meter.py
#:         → rc=0，`axes=7`（session／weekly_all／weekly_scoped／five_hour／seven_day／
#:           nimbus_quill／spend），而**不是** `no-credentials-darwin`
#: ⇒ service 名正確、`-w` 吐的是 JSON 而非裸 token、整條 mac 額度軸真的量得到。
#: 仍未驗的是**沒有 Keychain 條目的那台 mac**（本機無法構造：清掉條目就等於把使用者
#: 登出）——那一半由 `_keychain_token` 的 `runner` 注入覆蓋，見 `MacCredentialSourceTest`。
KEYCHAIN_SERVICE = "Claude Code-credentials"
KEYCHAIN_TIMEOUT_SECONDS = 5

#: 無視窗旗標。語意（為何是 `CNW|NEWGRP` 而不是 `DETACHED`、四種載具的實測矩陣）唯一的
#: 家＝`.claude/hooks/context_budget_guard.NO_WINDOW`；本行是**同一個表達式的第二份字面**。
#: 🔴 為什麼不 import 過來（同一份知識住兩個家是本 repo 判過的形態，所以要辯護）：那條路
#: 是**死的**——`context_budget_guard` → `quota_gate` → 本檔（該檔第 52 行 `import
#: quota_meter`），反向 import 直接成環。既然只能複製，就必須有東西守著兩份不漂開：
#: `tools/tests/test_context_budget_guard.py::ConsoleFreeSpawnTest
#: ::test_the_duplicated_no_window_expression_still_equals_the_ssot`（相等鎖，漂開即紅）。
#: `getattr` 而不是直接取屬性：這兩個常數在 POSIX 的 `subprocess` 上**不存在**（鐵律三
#: 「這在另一個平台是什麼值」），取 0 ＝不加任何旗標，正是 POSIX 上正確的值。
NO_WINDOW = (getattr(subprocess, "CREATE_NO_WINDOW", 0)
             | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))

#: `measure_detail()` 的失效字面。**它們就是 B4 要的那個可觀測面**：token 過期、
#: 斷網、schema 升版、憑證檔不在，四種情況在本輪之前與「額度很健康」外觀完全一致。
REASON_OK = "ok"
REASON_NO_CREDENTIALS = "no-credentials"
#: 🔴 mac 專屬：與上一個刻意分開。混成同一個字面時，「這台 mac 的 Keychain 沒接上」
#: 與「token 真的過期了」在痕跡裡讀起來一模一樣，而兩者要做的事完全不同。
REASON_NO_CREDENTIALS_DARWIN = "no-credentials-darwin"
#: 🔴 R83／F2-③：**逾時與「沒有條目」刻意是兩個字面。** 此前兩者都回
#: `no-credentials-darwin`，而它們要做的事**完全相反**：
#:   · 沒有條目 ⇒ 這台 mac 沒登入過 Claude Code，人要去 `claude login`，等下去沒有意義；
#:   · 逾時 ⇒ Keychain 跳了鎖定／授權提示而**沒有人在螢幕前按它**（`security` 會阻塞到
#:     `KEYCHAIN_TIMEOUT_SECONDS`），憑證其實在，解鎖後下一次就量得到 ⇒ 這一格該做的是
#:     「解鎖 login keychain／改成 always-allow」，不是去重新登入。
#: 混成一個字面時，痕跡裡讀起來一模一樣，而「量不到」在本 repo 的語意是**不節流**
#: ⇒ 一個無人看管的排程會在「其實只要解鎖」的情況下永久不節流，且完全靜默。
REASON_KEYCHAIN_TIMEOUT = "keychain-timeout"
REASON_UNREACHABLE = "meter-unreachable"
REASON_NO_BUCKETS = "no-buckets"

#: 快取檔。🔴 **刻意不帶 session id**：額度是 **per-account** 的單一池，而
#: `%TEMP%` 實測有 20 個以上相異 session 各持一份自己的狀態檔。帶 sid 的快取會讓
#: N 個併發載體各自量一份、各自判一次，那與「一個帳號一個池」在單位上就不匹配
#: （SA-B5／SD-B1 的同一個病）。一個帳號、一份快取。
#:
#: 🔴 **R84／ARCH-07：這個字面有「兩個必要的家」，不是一個。** 本行此前自稱是檔名的唯一
#: 的家，而實測 AutoClaude 側另有兩處硬編同一個字面（`autoclaude/infra/adapters/
#: file_quota_meter.py` 的 `self._path` ＋同檔檔頭那張路徑表；另有 `.importlinter` 與
#: port 檔的散文各一處）。那不是疏漏而是**契約所迫**：`AutoClaude/.importlinter` 明文
#: 禁止引擎 import monorepo 根層護欄層，唯一合規路徑就是「adapter 只讀
#: `%TEMP%/autosdd_quota.json`」這條**檔案契約** ⇒ 兩側必須各自持有字面。
#: ⇒ 誠實的說法是：**字面兩個家、算法一個判準**。對齊由具名機械物守，不靠人記得：
#:   `tools/tests/test_quota_policy.py::TestM8bCacheHomeStaysInSync`
#:   （比的是**目錄運算式**：只有一側搬家即紅，兩側同一次 commit 一起搬才綠）
#:   `tools/tests/test_quota_policy.py::TestM8SchemaStaysInSync`（schema 那一半）
#: 搬家或改名時**必須同一次 commit 動兩支檔**；只改本行的人會讓 adapter 讀不到檔，
#: 而它對「檔不在」的反應是回 `None`＝量不到，且那個 `None` 被它自己的測試釘成正確行為
#: ⇒ 失效全綠、完全靜默。現查另一個家：`grep -rn "autosdd_quota.json" AutoClaude`
CACHE_NAME = "autosdd_quota.json"

#: 內部唯一表示：**0..100 的 float**。每個通道在自己的入口寫死該通道的單位。
#: 🔴 這是本包唯一能抓到「差 100 倍」的地方：`0.3` 拿去比 `80` 永遠不觸發（閘門恆綠）、
#: `30.0` 拿去比 `0.8` 永遠觸發（閘門恆紅），兩個方向都在 rc=0 的外觀下失效。
SCALE_PERCENT = 1.0        # REST `utilization`(float 0..100)／`limits[].percent`(int 0..100)
SCALE_FRACTION = 100.0     # headless stream-json `rate_limit_event.utilization`(0..1)

#: HTTP 逾時。取數失敗的正確方向是「量不到」，不是「慢慢等」——本檔的消費者是
#: 15 分鐘一次的巡邏與 fire-and-forget 刷新，沒有人在等這個值。
HTTP_TIMEOUT_SECONDS = 10

#: 🔴 `/2` 改的不是版號而是**形狀**（R82 接線階段；缺陷本體就在這一格）：頂層不再有
#: `pct`／`kind`／`resets_at`／`via` 這組投影，改吐 `axes[]`，**每一格自帶自己的
#: `resets_at` 與 `group`**。舊形態先用 `worst()` 挑出 pct 最大的一桶、再把它的
#: 三個欄位投影到頂層 ⇒ 其餘每一桶的 reset 期程在**那兩行**被丟掉，於是下游拿到的是
#: 一個純量，「30 分鐘後 reset」與「5 天後 reset」在程式裡變成同一件事。
#: 判讀層要的是 (pct, 距 reset 幾分鐘) 這個**二元組**（見 `tools/lib/quota_policy.py`
#: 檔頭），取數層少給一半，判讀層再聰明也補不回來。
#: 升版的雙向鎖：`tools/tests/test_quota_policy.py::TestM8SchemaStaysInSync`
#: （AutoClaude 的 adapter 必須**同一次**跟著改；只升一邊時 adapter 會回 `None`＝
#: 「量不到」，而那個 `None` 被它自己的測試釘成正確行為 ⇒ 失效全綠、完全靜默）。
SCHEMA = "autosdd.quota/2"


def cache_path() -> Path:
    # `tempfile.gettempdir()` 而不是 `$env:TEMP`：後者在 macOS/Linux 的 PS Core 上
    # **不存在**，`Join-Path $env:TEMP …` 會直接拋 null 綁定例外（鐵律三，本 repo 已有
    # 專屬判準 `TestPowerShellPlatformSensitiveSites`）。
    return Path(tempfile.gettempdir()) / CACHE_NAME


def _token_of(blob: object) -> str:
    """從已解析的憑證 payload 取 `claudeAiOauth.accessToken`；取不到回空字串。
    檔案與 Keychain 兩條路的**內容**是同一份 JSON，所以解析只有一個家。"""
    oauth = blob.get("claudeAiOauth") if isinstance(blob, dict) else None
    token = oauth.get("accessToken") if isinstance(oauth, dict) else None
    return token if isinstance(token, str) else ""


def _keychain_token(runner: object = None) -> tuple[str, str]:
    """macOS：從 login Keychain 取憑證。回 `(token, 取不到時該叫什麼名字)`。

    `runner` 是為了讓這條路**在沒有 mac 的機器上也測得到**而存在的注入點：它必須是一個
    `(argv) -> (rc, stdout)` 的可呼叫物（**契約未變**，回二元組即可）。預設值走真的
    `security`。要構造「Keychain 跳提示而沒有人按」那條臂，讓 runner 拋
    `subprocess.TimeoutExpired`——那正是真 `_run_security` 逾時的形狀。

    🔴 回二元組而不是只回 token（R83／F2-③）：逾時與「沒有條目」在本函式**內部**才分得
    開（`security` 阻塞 vs `rc != 0`），一旦壓成 `""` 送出去就再也還原不回來——那正是
    「取數層少給一半，判讀層再聰明也補不回來」（見 `SCHEMA` 那一段）的同一個形狀。
    """
    call = runner or _run_security
    try:
        rc, out = call(["security", "find-generic-password",
                        "-s", KEYCHAIN_SERVICE, "-w"])
    except subprocess.TimeoutExpired:
        # 🔴 這一條**必須排在 `except Exception` 前面**：`TimeoutExpired` 是
        # `SubprocessError` 的子類，順序反過來就會被寬的那一條吃掉，而失效是靜默的
        # （逾時退回 `no-credentials-darwin`＝回到本缺陷修前的行為，且全套測試照綠）。
        return "", REASON_KEYCHAIN_TIMEOUT
    except Exception:  # noqa: BLE001 — 取不到憑證最多是量不到，不得變成故障源
        return "", REASON_NO_CREDENTIALS_DARWIN
    if rc != 0:
        return "", REASON_NO_CREDENTIALS_DARWIN
    try:
        return _token_of(json.loads(out)), REASON_NO_CREDENTIALS_DARWIN
    except ValueError:
        # Keychain 也可能存的是裸 token 而不是 JSON（本機實測是 JSON，見 `KEYCHAIN_SERVICE`
        # 的實測欄；但一台機器的形態不是常數，另一種形態的機器仍要收）⇒ 兩種都收，
        # 但**不得**把一段錯誤訊息當成 token 送出去（那會變成一個永遠 401 的假綠：取數
        # 看起來有在跑，只是每一次都失敗）。判準取「不含任何空白且夠長」——`security`
        # 的失敗訊息一定帶空白（`security: ... not found`），OAuth token 一定不帶。
        stripped = out.strip()
        # 🔴 R82：`isascii()`／`isprintable()` 兩條是補上面那句話自己漏掉的洞。上方
        # `_run_security` 的註解逐字說「降解後的字串仍可能通過『不含空白且夠長』的判準
        # ⇒ 送出一個永遠 401 的假 token」，然後用 `encoding="utf-8"` 去治它——但它同時
        # 帶了 `errors="replace"`，於是非 UTF-8 位元組會變成一串 U+FFFD，那串東西**不含
        # 任何空白、長度也遠超過 20**，原判準照樣放行。⇒ 守衛與它自己宣稱要防的東西之間
        # 差一個字。OAuth token 是 base64url 形態（純 ASCII 可列印），所以這兩條對真
        # token 零假陽性；控制字元同理（`isprintable()` 擋 `\x00` 這種不算 `isspace()`
        # 的東西）。空白那一條保留：空格是可列印的，`isprintable()` 擋不掉它。
        ok = (len(stripped) >= 20 and not any(ch.isspace() for ch in stripped)
              and stripped.isascii() and stripped.isprintable())
        return (stripped if ok else ""), REASON_NO_CREDENTIALS_DARWIN


def _run_security(argv: list[str]) -> tuple[int, str]:
    # `text=True` 不指名 encoding ⇒ 走 locale 預設。本檔在 mac 上讀的是 Keychain 吐的
    # token，非 ASCII 的錯誤訊息在非 UTF-8 locale 下會 UnicodeDecodeError 或降解，而降解
    # 後的字串仍可能通過下方「不含空白且夠長」的判準 ⇒ 送出一個永遠 401 的假 token。
    # 🔴 `creationflags`：本檔的呼叫端一路是 hook（`context_budget_guard` → `quota_gate`
    # → 本檔）與 schtasks 的 `pythonw.exe`，兩者都是**無 console 的父行程** ⇒ 在那個條件下
    # spawn 一個 console 子系統應用，Windows 必定新配置一個 console＝跳到使用者臉上的視窗。
    # 🔴 誠實劃界（不要把這一行讀成「治好了掌舵者看到的黑框」）：本函式只在
    # `sys.platform == "darwin"` 那條路上被呼叫（`access_token()` 的平台分支），而 macOS
    # 上這兩個常數不存在、`NO_WINDOW` 恆為 0 ⇒ **這一行在今天的 Windows 上一次都不會執行**。
    # 補它的理由是「顯式表態」與「平台分支哪天挪動時不會靜默漏掉」，不是它現在有效果。
    # 🔴 `TimeoutExpired` **刻意不在這裡吞掉**（R83／F2-③）：它是本檔唯一能區分
    # 「Keychain 跳了提示而沒有人按」與「這台 mac 沒有條目」的訊號，吞掉就等於把兩件事
    # 壓成同一個 `rc != 0`。呼叫端 `_keychain_token` 專門收它，並給它自己的理由字面。
    proc = subprocess.run(argv, capture_output=True, text=True, check=False,
                          encoding="utf-8", errors="replace",
                          timeout=KEYCHAIN_TIMEOUT_SECONDS, creationflags=NO_WINDOW)
    return proc.returncode, proc.stdout


# 🔴 R83／F2-③：**平台分支只有這一個家。** 它回二元組是因為「去哪裡拿」與「拿不到時
# 叫什麼名字」是同一個平台事實的兩面——分成兩個函式各讀一次 `plat`，就是 `token_detail`
# 檔頭記載過的那個病（兩個家可以無聲分岔）。`access_token` 與 `token_detail` 現在都只是
# 本函式的投影：前者丟掉理由、後者留著，**沒有第二次平台判斷**。
def _fetch_token(plat: str, runner: object = None) -> tuple[str, str]:
    """`(token, 取不到時的理由字面)`。理由只在 token 為空時有意義。"""
    if plat == "darwin":
        return _keychain_token(runner)
    try:
        data = json.loads(CREDENTIALS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "", REASON_NO_CREDENTIALS
    return _token_of(data), REASON_NO_CREDENTIALS


def access_token(platform: str | None = None, runner: object = None) -> str:
    # 🔴 token 值**永遠不回傳給呼叫端以外的任何地方**：不進 log、不進痕跡、不進任務書
    # （調研 S1-08 的逐字要求）。讀不出來一律回空字串，由呼叫端判「量不到」。
    # `platform` 是注入點（預設讀 `sys.platform`）：mac 分支必須在 Windows 上也驗得到，
    # 否則這一格就是「寫了但沒有任何東西在守」——本 repo 判過的最貴形態。
    return _fetch_token(platform or sys.platform, runner)[0]


def token_detail(platform: str | None = None,
                 runner: object = None) -> tuple[str, str]:
    """取 token，並在取不到時給出**該平台專屬**的失效字面。

    回 `(token, reason)`；取到時 `reason` 是 `REASON_OK`（沿用既有字面，不另發明一個
    只有這裡看得懂的 sentinel）。**token 值只回給呼叫端，不進 log／痕跡／任務書。**

    🔴 R82 立案（本函式是純粹的減法：把同一個平台分支的**第二個家**併回來）。
    分支原本住兩個地方——`access_token()` 決定「去哪裡拿」、`measure_detail()` 另外用
    `sys.platform == "darwin"` 決定「取不到時叫什麼名字」。兩個家各自讀一次平台，於是
    「拿的地方」與「說出來的名字」可以無聲地分岔：只要有人給 `access_token()` 傳了
    `platform="darwin"` 而主機是 Windows，取數走 Keychain、理由卻印 `no-credentials`。
    現在兩者讀同一個 `plat`，結構上不可能分岔。

    `platform`／`runner` 是注入點，理由與 `access_token()` 同一條、但**更硬**：
    `measure_detail()` 在本函式出現之前**沒有任何**憑證來源的注入點，於是它的每一條
    臂（憑證讀得到 → 打得到 401／憑證讀不到 → no-credentials）只能靠改動**主機自己的**
    憑證存放處來構造 ⇒ 每一條臂都只在一個平台上量得到，另一個平台靜默落到另一個 reason。
    R82 mac 真機實測就是這個形狀：`MeterFailureShapesTest` 把 `CREDENTIALS` 指到不存在
    的檔來構造「憑證讀不到」，而 darwin 根本不讀那個檔（本機 `~/.claude/.credentials.json`
    實測不存在、Keychain 實測 rc=0 有真 token）⇒ 拿到的是 `http-401`，該臂在 mac 上
    結構性量不到。**而且它更糟**：那條測試每跑一次就真的去讀一次使用者的 login Keychain，
    綠不綠取決於這台機器有沒有登入過 Claude Code。

    🔴 R83／F2-③ 訂正本段的實作宣稱（原文寫「現在兩者讀同一個 `plat`」——那句話對修前
    的形狀為真，但它把「只有一次平台判斷」與「兩個函式各讀一次同名變數」混為一談，
    而後者仍然是兩個家）。平台分支現在的唯一的家是 `_fetch_token()`；本函式與
    `access_token()` 都只是它的投影，差別只在「留不留理由」。同一次修正也讓 mac 的
    **逾時**能有自己的字面（`REASON_KEYCHAIN_TIMEOUT`）——那個區別在 `_keychain_token`
    內部才存在，壓成 `""` 之後任何上層都還原不回來。
    """
    token, reason = _fetch_token(platform or sys.platform, runner)
    return (token, REASON_OK) if token else ("", reason)


def normalize_pct(value: object, scale: float) -> float | None:
    """把某通道的原始值換算成 0..100 的 float；`None`＝這不是一個可用的數字。"""
    # `bool` 是 `int` 的子類，混進來會讓 `True` 算成 1.0——與 `used_of()` 同一條紀律。
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    pct = float(value) * scale
    # 負值／NaN 一律當「量不到」。超過 100 不夾（overage 是真的存在的狀態），
    # 但 0..100 之外的**負**方向沒有任何合法語意。
    if pct != pct or pct < 0:
        return None
    return pct


# 🔴 SA-B3 的修法：**兩個來源取聯集**，不是只讀 `limits[]`。
# 實測（本包當回合，22:18 +08:00）：`nimbus_quill` 有 `utilization=0.0` 的**真值**，卻
# **沒有**對應的 `limits[]` 條目 ⇒ 只讀 `limits[]` 對「有真值但不在 limits[] 裡」的桶
# 結構上失明；哪天是它先滿，取 max(limits[].percent) 會讀到一個低值而永不節流，
# 而且沒有任何東西轉紅。
# 🔴 桶名一律**動態列舉**，禁止寫死清單：live payload 當回合 17 個頂層鍵，而
# `claude.exe` 內嵌名單只有 8 個 ⇒ schema 正在長，寫死名單的失明是靜默的。
# 第三條規則（頂層 dict 的 `percent`）是為了把 `spend` 收進來——它沒有 `utilization`
# 只有 `percent`，而它是「沒有 reset 可以等」的那一條線（見 `reset_branch`）。
# 🔴 R87 事故墓碑（`DEF-200-R87-spend`）：**不要**因為桶自報 `enabled: false` /
# `is_enabled: false` 就把它排除在軸之外。R87 舵手這樣做過，代價是 13 個 subagent 全數
# 撞 `You've hit your monthly spend limit`、燒掉 1,319,703 tokens、零產出。
#
# 當時的 payload 逐字：`extra_usage {"is_enabled": false, "monthly_limit": 500,
# "used_credits": 610.0, "utilization": 100.0, "disabled_reason": "org_level_disabled_until"}`、
# `spend {"used": 610, "limit": 500, "percent": 100, "severity": "critical", "enabled": false}`。
# 誤讀＝「池子關著 ⇒ 它不在管制我」；**真意＝`used > limit` 已撞月度支出上限，額外用量
# 購買功能因此被 org 層停用**。`enabled:false` 是撞頂的**後果**，不是「這一軸不算數」。
#
# 反證當時被舵手拿來推翻守衛的兩條「證據」，兩條都不成立：
#   ① 「主力軸只有 1%」——`session`／`five_hour` 是**訂閱制用量窗**，`spend` 是**月度付費
#      上限**，不同的池；前者低不蘊含後者沒撞。
#   ② 「我還能送請求」——主 session 走訂閱額度尚有餘裕，不蘊含 subagent 那條路沒撞牆。
# 而 hook 當時已逐字印出正確答案：「這一條**沒有 reset 可以等**（例：月度支出上限）；
# 只有人去提額」。⇒ 這一族撞線時 **halt 是對的**，且**排程是錯的動作**。
# 🔴 R89：`is_active`／`severity` 是**純觀測欄位**，本輪補上的是「接好卻沒有電的線」。
# 立案事實（三處全部實查，不是推論）：
#   ① `quota_policy.Axis` 自 R82 起就宣告了這兩欄（`:179-180`）；
#   ② `quota_gate.read_quota()` 逐字 `a.get("is_active"), a.get("severity")` 在讀它們；
#   ③ 而本函式從來沒有寫過 ⇒ live 快取 7 軸 × 2 欄 = **14 格全部 `None`**，
#      伺服器每一次都有給值（本輪實測 `limits[]` 三筆皆帶 `severity`＋`is_active`）。
#   失效是靜默的：`.get()` 對「欄位不存在」與「伺服器真的給 null」回同一個 `None`。
# 🔴 **這兩欄一格都不得參與分類／選桶／band／cap／rec**，只准被人看見。三條理由各自成立：
#   · `quota_policy` 檔頭既有紀律逐字禁止拿 `is_active` 選桶（五次觀測都等於
#     argmax(percent)，但五次一致不構成契約——伺服器無文件）；
#   · `severity` 至今只觀測到 `normal`／`critical` 兩值，而 `critical` 只出現在已被
#     R89 判為**保險軸**的 `spend` ⇒ 對主力軸零鑑別力；
#   · R87 墓碑（見上方）：讀了一個自報欄位就讓程式少判一軸，代價是 13 個 subagent 全滅。
#     ⇒ 本輪的方向是**只准讓人多看見，不准讓程式少判**。
# 🔴 `SCHEMA` **刻意不升版**：純追加鍵，向後相容。AutoClaude adapter（`file_quota_meter.
#   _pick()`）只讀 `pct`／`kind`／`resets_at` 三鍵、其餘 `.get()` 忽略 ⇒ 未知鍵不影響它；
#   升版反而會讓 `TestM8SchemaStaysInSync` 要求 adapter 同一次 commit 跟著改（那是別的
#   持有面，鐵律七）。舊快取被新程式讀到時 `.get()` 回 `None`＝與本輪之前逐字相同。
# 🔴 頂層桶那一支**不是**「一律 `None`」：`spend` 實測自帶 `severity`（事故當時是
#   `critical`、今天是 `normal`），寫死 `None` 會把伺服器真的給了的值丟掉。兩支都走
#   `.get()`，讓「沒有這個欄位」與「伺服器給 null」照樣壓成 `None`（那是既有語意）。
#
# ── 〈R89 觀測欄〉判準的立案史料（**史料住這裡、判準住測試檔**）──────────────────
# 機械物＝`tools/tests/test_quota_policy.py::TestR89ObservationFieldsAreWiredButInert`
# ＋ 同檔 `r89_decision_drift_problems()`；桶列舉那一面＝`tools/tests/
# test_context_budget_guard.py::QuotaBucketUnionTest` 的三支 R89 測試。史料所以搬到本檔，
# 是因為根層護欄層有**淨額棘輪**（量測面＝`tools/tests/*.py` 的**原始行數**，
# `test_adr_xplat001_c1c2_lock._FROZEN_GUARD_LINES`）：新增判準時把史料一起寫進測試檔，
# 等於用「不可壓縮的真實功能」的名義讓量測面長大。本檔不在那個量測面內，而 `count_loc()`
# 也不計註解行 ⇒ 史料放這裡對兩條棘輪皆零成本，且它本來就是這段實作的 WHY。
#
# 🔴 交付條件「加欄位前後的 `Decision` 必須完全相等（逐位元）」**結構上不可滿足**，故判準
# 不取它的字面（不可滿足的驗收條件會逼人去滿足一個假的）。理由：`Decision.per_axis[i].axis`
# 與 `Decision.binding` 是**被回聲回來的輸入 `Axis` 物件本身**，而 `Axis` 是帶結構化
# `__eq__` 的 frozen dataclass ⇒ 欄位只要真的送達，`d_old == d_new` 恆為 `False`
# （實測：`False`）。要它為 `True` 只剩兩條路——欄位根本沒接上（＝這一包什麼都沒做），
# 或去動 `Axis.__eq__`（判讀層＝另一個持有面）。
# ⇒ 判準改成**可滿足且更強**的形狀：把回聲那兩格抹成 `None` 之後，整個 `Decision` 物件
# 必須 `==` 舊決策。它比「逐一比對幾個欄位」強——`cap`／`recommended_fanout`／`band`／
# `binding`／`reason`／`amort`／`per_axis`（含每一列的 horizon／minutes／note）全在這**一個**
# `==` 底下，漏掉任何一格結構上不可能。實測四組（新帳號 Team／舊帳號 R87 事故形狀
# × `ratio` 缺席／7.5）：原始 `==` 皆 `False`、抹掉回聲欄後皆 `True`。
#
# 🔴 反向判準是必要的，不是補強：「通電前後相同」那一族在**欄位根本沒接上**時兩邊都是
# `None` ⇒ 同樣全綠（沙箱實測：把本檔那兩對 `.get()` 整行拿掉後，該族仍回 `[]`）。
# 所以另有一條釘住「電真的通了」，否則整包可以靠什麼都不做通過驗收。
def bucket_readings(payload: object) -> list[dict]:
    """payload 裡每一個看得到水位的桶：`{kind, pct, resets_at, group,
    is_active, severity, via}`。

    🔴 `resets_at` 與 `group` **逐桶保留**（R82）：判讀層的分類只由 `resets_at` 導出，
    而 `group` 是伺服器自己的分組欄（實測多數桶沒有它 ⇒ 一律允許 `None`，
    **不得**拿它當分類依據，那會對沒有 group 的桶整片失明）。
    `resets_at` 一律是**伺服器原字串**：不轉本地、不重新格式化（naive 本地時間戳跨
    DST 相減實測差 3600 秒且完全靜默，本 repo 已有具名機械物禁止持久化它）。
    `is_active`／`severity` 同屬「帶出來但不許參與判讀」那一族（理由見上方 R89 段）。
    """
    if not isinstance(payload, dict):
        return []
    out: list[dict] = []
    for item in payload.get("limits") or []:
        if not isinstance(item, dict):
            continue
        pct = normalize_pct(item.get("percent"), SCALE_PERCENT)
        if pct is not None:
            out.append({"kind": str(item.get("kind") or "?"), "pct": pct,
                        "resets_at": item.get("resets_at"),
                        "group": item.get("group"),
                        "is_active": item.get("is_active"),
                        "severity": item.get("severity"),
                        "via": "limits[].percent"})
    for key, val in payload.items():
        if key == "limits" or not isinstance(val, dict):
            continue
        for field, scale in (("utilization", SCALE_PERCENT), ("percent", SCALE_PERCENT)):
            pct = normalize_pct(val.get(field), scale)
            if pct is not None:
                out.append({"kind": key, "pct": pct, "resets_at": val.get("resets_at"),
                            "group": val.get("group"),
                            "is_active": val.get("is_active"),
                            "severity": val.get("severity"),
                            "via": f"{key}.{field}"})
                break
    return out


# 🔴 `worst()` 的墓碑（R82，**刻意不留 deprecated 版本**）。它回的是 pct 數值最大的那
# 一桶，**與該桶的 reset 期程無關**，然後把那一桶的三個欄位投影到快取頂層——其餘每一桶
# 的 `resets_at` 就是在那裡被丟掉的。留一個「暫時沒人叫」的版本等於把缺陷留在原地等
# 下一個呼叫端；判讀改由 `tools/lib/quota_policy.decide()` 對**全部軸**做，取數層不再
# 挑桶。回歸鎖：`tools/tests/test_quota_policy.py::TestM5EveryScanSurfaceIsGatedHard`
# （定義與呼叫兩邊都算——只認 `def worst` 會漏掉「別處定義、這裡呼叫」的版本）。
# 🔴 R82／C4 訂正：本行原先指向 `tools/tests/test_quota_gate_wiring.py::
# TestWorstIsGoneFromEveryQuotaFile`，而**那支檔全庫不存在**（grep 只命中這一行註解自己）。
# 幽靈引用比沒有引用更糟：它讓下一個人以為查過了。複審鏡以沙箱注入實測，把 `worst()`
# 放回本檔、放回 `quota_gate.py`，把 `fanout_cap(pct)` 放回 hook 與 AutoClaude adapter，
# **五組全部 rc=0 GREEN**——因為當時的斷言只套在 `quota_policy.py` 自己身上。


#: credits 池在 payload 裡的兩種表述。**兩個都要看**：`extra_usage` 用 dollars 記
#: (`used_credits`／`monthly_limit`)，`spend` 用 minor units 記 (`used.amount_minor`／
#: `limit.amount_minor`) ⇒ **不得跨來源比絕對值**，只比各自的 used/limit 比值。
#: 🔴 R89 收尾／SA 複審 B-3：本常數與 `quota_policy.FALLBACK_KINDS` 是**兩件事**，關係是
#: 「本常數 ⊆ 保險軸」而不是相等。本常數的成員必須是 payload **頂層**的鍵、且 `_credit_pool()`
#: 認得它的欄位形狀（所以補 `overage`／`seven_day_overage_included` 是錯的——那兩個是
#: `limits[].kind`，不是頂層 dollar 池）；`FALLBACK_KINDS` 的成員是 **bucket kind**。
#: 兩者今天恰好在 `extra_usage`／`spend` 這兩個字面上重疊，鏡射鎖曾因此被寫成 `==`＝把巧合
#: 焊成契約，結果是**補齊保險軸這件事本身會轉紅**。判準已改為子集。
CREDIT_POOL_KEYS = ("extra_usage", "spend")


def _credit_pool(payload: dict, key: str) -> dict | None:
    """把一個 credits 表述正規化成 `{enabled, used, limit}`；讀不出來回 `None`。"""
    val = payload.get(key)
    if not isinstance(val, dict):
        return None
    if key == "extra_usage":
        used, limit = val.get("used_credits"), val.get("monthly_limit")
        enabled = val.get("is_enabled")
    else:
        used = (val.get("used") or {}).get("amount_minor")
        limit = (val.get("limit") or {}).get("amount_minor")
        enabled = val.get("enabled")
    if not isinstance(used, int | float) or not isinstance(limit, int | float):
        return None
    return {"enabled": enabled is True, "used": float(used), "limit": float(limit)}


def account_posture(payload: object) -> dict:
    """**派工前**必須先知道的兩件事：這是什麼帳號、它有沒有**可用的** credits。

    🔴 立案（R87 真實事故 ＋ 掌舵者裁決逐字：「配置 Agents 前，要先知道 Account Type
    and Account 是否有 Usage credits 再進行配置」）：本輪 13 個 subagent 全數撞
    `You've hit your monthly spend limit`、燒 1,319,703 tokens、零產出。事故當下
    **訂閱窗（five_hour）還有 37% 餘裕**，但 credits 池已爆（`used 610 > limit 500`、
    `severity: critical`）且被 org 層停用（`disabled_reason: org_level_disabled_until`）
    ⇒ **扇出全滅，而主 session 照常運作**。

    ⇒ 本函式把 credits 從「另一條節流軸」重新表述成它真正的角色：
    **`fallback_available` ＝ 訂閱窗用完之後還有沒有救。**
    掌舵者同時指出「（通常沒有）」——多數帳號未啟用 credits ⇒ 預設就是
    `fallback_available=False`，也就是**訂閱窗本身即硬牆**，這是保守且正確的方向。

    🔴 `plan_fingerprint` 是**軸組合**不是方案名稱：payload 沒有 plan 欄位
    （實測 `member_dashboard_available=false`、頂層 17 鍵無一為方案名），
    而軸組合本身就是指紋。它**不是**拿去查一組寫死的參數——那就是本 repo 判過的
    「寫死的數字必過期」。

    🔴 R89 訂正本段此前的一句假話（`DEF-200-114`），故不逐字保留：它宣稱這個指紋的
    「用途是偵測方案變更（組合變了 ⇒ 歷史標定／燃燒率作廢重學）」，而那件事**一行都
    沒有實作**——現查唯一消費端是 `quota_gate.posture_line()` 拿去印一段字串，全庫
    「作廢／invalidate」零命中。宣稱的用途沒接電，比沒有那句話更難看見：下一個人讀到
    它會以為換方案時歷史會自己作廢，於是不會去建那道機制。
    實際後果（與換帳號直接相關）：`quota_burn.jsonl` 的去重鍵只有 `measured_at`
    ⇒ 換帳號／換方案後**新舊樣本混在同一份落款裡**，`burn_ratio()` 會拿 A 帳號的燃燒
    特性去算 B 帳號的攤提配額，而它**不會隨 TTL 自癒**（快取 TTL 180s，落款是持久的）。
    本輪**刻意不修**：修法要動 `record_burn`／`burn_ratio`＝配速取數層，而 R87 的教訓
    正是「不得以模型判斷改取數層」，需第三方複審——本輪額度 halt、結構上沒有第三方。
    誠實劃界：指紋只分得出**方案**變更；同方案的兩個帳號指紋逐字相同 ⇒ Pro→Pro 換帳號
    這一型，靠指紋結構上抓不到，要抓需要帳號識別（涉及憑證處理，另案）。
    """
    if not isinstance(payload, dict):
        return {"plan_fingerprint": (), "credits_present": False,
                "credits_enabled": False, "credits_exhausted": False,
                "fallback_available": False, "pools": {}}
    pools = {k: p for k in CREDIT_POOL_KEYS if (p := _credit_pool(payload, k))}
    # 🔴 任一池可用即算有 fallback；**全部**不可用才算沒有。方向刻意保守：
    # 讀不出來（`None`）不計入「可用」，同 repo 通篇的「量不到 ≠ 量到零」。
    enabled = any(p["enabled"] for p in pools.values())
    exhausted = all(p["used"] >= p["limit"] for p in pools.values()) if pools else False
    return {
        "plan_fingerprint": tuple(sorted(r["kind"] for r in bucket_readings(payload))),
        "credits_present": bool(pools),
        "credits_enabled": enabled,
        "credits_exhausted": exhausted,
        "fallback_available": bool(pools) and enabled and not exhausted,
        "pools": pools,
    }


# 🔴 SA-B2 的修法：分母**從 payload 推導**，不寫死一句散文。
# 兩個 dollars 欄皆非 null 時另做交叉核對，讓 utilization 壞掉／過期變成**可偵測**
# 而不是靜默採信——這是「當某個數字有權威來源時」也仍然要有的第二個觀測者。
def denominator_of(payload: object) -> dict:
    """口徑：server 用什麼當分母、我們有沒有辦法核對它。"""
    fh = (payload or {}).get("five_hour") if isinstance(payload, dict) else None
    fh = fh if isinstance(fh, dict) else {}
    limit, used = fh.get("limit_dollars"), fh.get("used_dollars")
    numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool)
                  for v in (limit, used))
    if not numeric:
        return {"kind": "undisclosed",
                "text": "伺服器未揭露分母（five_hour.limit_dollars 為 null）"
                        "；utilization 由 server 依帳號方案算出，本機不自行推導",
                "cross_check": None}
    derived = (float(used) / float(limit) * 100.0) if float(limit) else None
    util = normalize_pct(fh.get("utilization"), SCALE_PERCENT)
    ok = (derived is not None and util is not None and abs(derived - util) <= 1.0)
    return {"kind": "usd",
            "text": f"美元計價：limit_dollars={limit} used_dollars={used}",
            "cross_check": {"derived_pct": derived, "reported_pct": util, "agrees": ok}}


def fetch_usage(token: str, timeout: int = HTTP_TIMEOUT_SECONDS) -> tuple[int, object]:
    """打端點。回 `(http_status, payload)`；status 0＝連線層就失敗。"""
    # 🔴 header 只帶這兩個是**實測**結論（Architect 的對照組）：`anthropic-beta` 與
    # claude-cli 的 User-Agent 都不是必要條件 ⇒ 不必偽裝成 CLI，少一個會隨版本漂移的耦合面。
    req = urllib.request.Request(USAGE_URL, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return int(resp.status), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 🔴 401 與「額度真的沒回來」必須在痕跡裡分得開（調研 S1-08）：OAuth token 4 小時
        # 到期，而無人看管那條路上沒有人在 refresh。混在一起會讓排程器把認證失敗誤判成
        # 額度未恢復而一直等下去——那與 R80 哨兵整晚失明是同一個形狀。
        return int(exc.code), None
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return 0, None


def measure_detail(timeout: int = HTTP_TIMEOUT_SECONDS,
                   platform: str | None = None,
                   runner: object = None) -> tuple[dict | None, str]:
    """量一次，回 `(讀數 dict 或 None, 失效字面)`。**這是 B4 的修法本體。**

    🔴 立案（SD-B4）：`fetch_usage()` 檔頭 §S1-08 逐字要求「401 與『額度真的沒回來』
    必須在痕跡裡分得開」，而它**做到了**——回 `(status, payload)`。真正掉東西的是它
    唯一的呼叫端：舊 `measure()` 把 status 丟掉、四種失效一律回同一個 `None`
    ⇒ token 過期（401）、斷網、憑證檔不在、schema 升版，在消費端外觀完全相同。

    🔴 R82 新增的兩個參數**只有測試會傳**（production 三個呼叫端——`measure()`／
    `refresh_detail()`／`quota_gate.refresh_quota_cache()`——全部照舊只傳 timeout，
    行為逐字不變）。它們存在的理由不是「讓測試方便」，是**讓兩個平台的憑證來源在任何
    一台機器上都量得到**：見 `token_detail()` 的 WHY。沒有它們時，判準只能去改主機
    自己的憑證存放處，於是每一條臂只在一個平台成立、另一個平台靜默回別的 reason——
    那正是「把一台機器上量到的值寫成常數」的同一個病，只是這次寫死的是「憑證住哪裡」。
    """
    # 🔴 「量不到 ≠ 量到零」是本 repo 通篇的紀律，在這裡尤其致命：回 0 ＝永遠正常
    # （靜默失明），回 100 ＝永遠 halt。兩個方向都不可接受，所以只能回 `None`。
    token, reason = token_detail(platform, runner)
    if not token:
        return None, reason
    status, payload = fetch_usage(token, timeout)
    if status == 0:
        return None, REASON_UNREACHABLE
    if status != 200 or not isinstance(payload, dict):
        return None, f"http-{status}"
    axes = bucket_readings(payload)
    if not axes:
        return None, REASON_NO_BUCKETS
    # 🔴 **不排序、不挑桶、不投影**：軸的順序照伺服器給的，判讀層自己會對全部軸求值。
    # 舊版另有一個 `buckets`（只帶 kind/pct 的排序摘要）——那是同一份知識的第二個家，
    # 且它正是「把二元組壓成純量」的那個形狀的縮影，故一併刪除而不是留著相容。
    return {
        "schema": SCHEMA, "axes": axes, "source": "endpoint",
        "http_status": status,
        "measured_at": datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
        "denominator": denominator_of(payload),
        "schema_keys": sorted(payload),
        # 🔴 R87：派工前置檢查的資料來源（見 `account_posture`）。快取裡沒有它，
        # `--pace` 就只能講水位、講不出「訂閱窗用完之後還有沒有救」。
        "posture": {k: v for k, v in account_posture(payload).items() if k != "pools"},
    }, REASON_OK


def measure(timeout: int = HTTP_TIMEOUT_SECONDS) -> dict | None:
    """量一次。回讀數 dict；**任何一種失敗一律回 `None`，絕不回 0**。

    既有呼叫端的窄介面（簽章與回傳形狀逐字不變）。要知道「為什麼量不到」的人改用
    `measure_detail()`——把理由塞進本函式的回傳值會逼每一個呼叫端一起改，而它們裡面
    有一個是 hook 的關鍵路徑。
    """
    return measure_detail(timeout)[0]


# 🔴 SA-N09 的 schema 漂移偵測：本輪光是兩次觀測之間，`nimbus_quill` 就由「代號桶」
# 變成帶真值的 dict。這個面是會動的，而「新桶滿了但我們看不到」是靜默失明。
# 判準刻意只**記錄**不阻斷：schema 長出新鍵不是錯誤，看不見它才是。
def drift_against(previous: object, reading: dict) -> list[str]:
    """與上一次快取比對頂層鍵集合；回新出現的鍵（空＝沒漂移）。"""
    if not isinstance(previous, dict):
        return []
    old = set(previous.get("schema_keys") or [])
    return sorted(set(reading.get("schema_keys") or []) - old) if old else []


def read_cache(path: Path | None = None) -> dict | None:
    """讀快取；讀不出來回 `None`（同樣不回 0）。"""
    try:
        data = json.loads((path or cache_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("schema") == SCHEMA else None


def write_cache(reading: dict, path: Path | None = None) -> bool:
    """把讀數寫進快取；回「寫成功了沒」。寫不進去不得升級為失敗。"""
    target = path or cache_path()
    payload = dict(reading)
    payload["schema_new_keys"] = drift_against(read_cache(target), reading)
    try:
        # `newline="\n"`：本 repo 判過「Python 寫檔不指定 newline，Windows 會寫出 CRLF」。
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                          encoding="utf-8", newline="\n")
    except OSError:
        return False
    return True


def refresh_detail(timeout: int = HTTP_TIMEOUT_SECONDS) -> tuple[dict | None, str]:
    """量一次並寫快取，連失效字面一起回（`measure_detail` 的寫快取版）。"""
    reading, reason = measure_detail(timeout)
    if reading is not None:
        write_cache(reading)
    return reading, reason


def refresh(timeout: int = HTTP_TIMEOUT_SECONDS) -> dict | None:
    """量一次並寫快取（fire-and-forget 刷新器與巡邏共用的那一支；窄介面）。"""
    return refresh_detail(timeout)[0]


def _report(reading: dict) -> str:
    # 🔴 逐軸一行，而且**每一個百分比自己帶 `kind=` 與自己的 `resets_at`**。裸的
    # 「54%」正是掌舵者當場誤讀的那個形狀——它之所以會被誤讀，就是因為那個數字沒有
    # 說自己是哪一桶、什麼時候 reset。本函式不挑桶也不排序：挑桶是判讀層的事。
    den = reading["denominator"]
    lines = [f"measured_at={reading['measured_at']}  axes={len(reading['axes'])}"]
    # 🔴 R89：`is_active`／`severity` 走 `.get()` 而不是 `[...]`——`--from-cache` 讀得到
    # **本輪之前寫下的舊快取**（那些軸沒有這兩鍵），下標會當場 KeyError，而它的表徵是
    # 「額度工具壞了」而不是「這格沒有值」。兩者都印成 `None`＝與缺席語意一致。
    lines += [f"  kind={a['kind']} {a['pct']:.1f}%  resets_at={a['resets_at']}"
              f"  group={a['group']}  is_active={a.get('is_active')}"
              f"  severity={a.get('severity')}  via={a['via']}" for a in reading["axes"]]
    lines.append(f"denominator[{den['kind']}]={den['text']}")
    if den["cross_check"]:
        lines.append(f"cross_check={den['cross_check']}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="額度水位取數器（0..100 float）")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="印出完整讀數 JSON（含口徑欄）並寫快取")
    parser.add_argument("--refresh", action="store_true",
                        help="只量並寫快取，不印（fire-and-forget 刷新器用）")
    parser.add_argument("--from-cache", action="store_true", dest="from_cache",
                        help="只讀快取，不碰網路")
    parser.add_argument("--watch", type=int, metavar="SECONDS", default=0,
                        help="每 N 秒量一次並印一行（**漂移率的重量入口**，不另開探針檔）")
    args = parser.parse_args(argv)

    if args.watch:
        # 🔴 這支旗標存在的理由是 SA-B4：ADR 曾以「1.2pp/min」兩點外推推導出 TTL，
        # 而第三個量測點證明那個量**非單調**（視窗翻頁時 utilization 會驟降 48pp）。
        # ⇒ 漂移率不得由兩點外推，要就重量。這裡是那個入口。
        while True:
            reading = refresh()
            print(f"{datetime.now().astimezone().isoformat(timespec='seconds')} "
                  + ("  ".join(f"kind={a['kind']} {a['pct']:.1f}%"
                               for a in reading["axes"]) if reading else "量不到"),
                  flush=True)
            time.sleep(max(1, args.watch))

    reading, reason = ((read_cache(), "cache") if args.from_cache
                       else refresh_detail())
    if reading is None:
        # 斷網／401／欄位缺／型別不對 ⇒ 印「量不到」且**不得印任何百分比**。
        # 🔴 R81／SD-B4：**理由必須印出來**。四種失效在本輪之前共用同一句話，於是
        # 「token 過期了」與「這個帳號真的沒有桶」讀起來一模一樣。
        print(f"❌ 量不到額度水位（reason={reason}）。"
              "本工具刻意不回 0——量不到 ≠ 量到零。", file=sys.stderr)
        return 1
    print(json.dumps(reading, ensure_ascii=False, indent=2) if args.as_json
          else _report(reading))
    return 0


if __name__ == "__main__":
    # 🔴 本檔印中文（「量不到」「❌ 量不到額度水位…」），而非 UTF-8 locale 下 stdout 會直接
    # UnicodeEncodeError、stderr 降解成 \uXXXX（DEF-101-798 同型）。保護只掛在 `__main__`：
    # 本檔同時被 test_context_budget_guard 以模組 import，import 期換串流會污染測試載具。
    # 走 SSOT（`tools/lib/platform_utils.py` → `tools/_stdio_utf8.py`）而不是就地 reconfigure，
    # 理由見 platform_utils 檔頭：那段實作曾被複製 8 份、其中 6 份漏了分支。
    from platform_utils import init_utf8_streams

    init_utf8_streams()
    sys.exit(main(sys.argv[1:]))
