"""額度**撞線訊息**的判讀（純函式 ＋ 只讀逐字稿）——與 context 水位是兩件事。

WHY 這一段從 `.claude/hooks/context_budget_guard.py` 搬出來（R81 收斂的減法那一半）
------------------------------------------------------------------------------
該 hook 落地當回合 raw 1,634 行、`check_loc_budget.py` 的棘輪門檻同為 1,634（餘裕 0），
而 R81 那一輪 +421 行全部灌進同一支——**壓力只作用在已經被量的那一層**。本輪要往裡面
加 B1~B4 的修復，唯一誠實的出口是先做減法（棘輪自己寫的解鎖程序逐字：「先刪死碼／抽共用
模組（先例：`tools/lib/ci_liveness.py`）」）。

搬的是一個**完整的主題**而不是隨手切一刀：本檔全部的輸入都是「一則 harness 合成訊息」
或「一支逐字稿」，全部的輸出都是判讀結果；它一行都不碰 context 水位、不碰 window 分母、
不碰阻斷決策。留在 hook 那一側的是「量 context 水位 ＋ 決定要不要擋」，兩者的失效模式
本來就不同（見 hook docstring 那句「取數與判讀的失效模式不同，必須分開」）。

消費者有兩個，這也是它不該只住在 hook 裡的理由：
  · `.claude/hooks/context_budget_guard.py`（`quota_floor_reading()` 的 L3 地板）
  · `tools/session_resume_planner.py`（哨兵巡邏、續航判定；它以 `guard.<name>` 取用，
    所以 hook 那一側把本檔的符號 import 回自己的命名空間，呼叫端一個字都不必改）

🔴 **這一支的 import 刻意不包 try/except**（與同目錄的 `quota_meter`／`quota_ledger` 不同）。
那兩支是**能力提供者**：不可達時額度軸退化成「量不到」，那是設計好的降級路徑。本檔是
**判讀原語**，hook 自己的程式路徑會無條件呼叫它 ⇒ 給它一組 fallback stub 等於讓
`SYNTHETIC_MODEL`／`LIMIT_*` 這些字面有第二個家（本 repo 的頭號病），而且 stub 會用
**錯的答案**靜默通過。硬 import 失敗時 hook 以 traceback ＋ 非 0/2 的 rc 收場——那在
Claude Code 是「出聲但不阻斷」，是**看得見**的失效，比靜默答錯好。
"""
from __future__ import annotations

import json
import re
import time
import zoneinfo
from datetime import datetime, timedelta
from pathlib import Path

#: 逐字稿裡不代表真實模型的佔位值（本機實測會出現，混進交叉否決會誤殺）。
SYNTHETIC_MODEL = "<synthetic>"

# ─────────────────────────── 額度事件（**與 context 水位是兩件事**，見下方 WHY）
# 🔴 這一段刻意**不接**任何阻斷行為，也不共用上面那條 75/90 的線。
# context 水位＝單次請求的輸入長度（分母是 window）；額度＝計費週期內的用量上限
# （分母是方案，harness 不告訴你）。兩者混為一談是本題最常見的錯誤，而它今天就會出錯：
# 額度耗盡當下本 session 的水位只有 ~20%，`block_verdict` 的四道放行條件會全數放行。
# 本段只提供**純函式的判讀**，由 `tools/session_resume_planner.py` 這個 CLI 消費者去決策。
# 住在這裡而不是住在 planner，是因為「怎麼掃逐字稿」的實作已經在本檔（`scan_transcript`），
# 而 planner 已經 import 本檔；反過來寫會讓逐字稿掃描這份知識有兩個家。

#: 可等待——session 額度，錯誤訊息自帶 reset 時刻。
LIMIT_SESSION = "quota_session"
#: 🔴 **不可等待**——月度支出上限，等到天荒地老都不會自己回來，只有人去提額才行。
#: 全庫實測：`session limit` 151 筆／`monthly spend limit` 71 筆（＝32%）。兩者的字面
#: 前綴都是 `You've hit your `，只認前綴的分類器會把那 71 筆判成可等待，然後排一支
#: 永遠不會成功的工作、每次觸發燒一次探測額度、而真正該做的事（叫人提額）一直沒發生。
LIMIT_SPEND = "quota_spend"
#: 伺服器暫時性錯誤，秒級退避即可，不進續航流程。
LIMIT_TRANSIENT = "transient"
#: 認不出來。**一律當不可等待處理**（fail-closed）：寧可叫人，也不要排一支永遠不成的工作。
LIMIT_UNKNOWN = "unknown"

#: 判讀順序即優先序。spend 必須排在 session 前面——見 `LIMIT_SPEND` 的 WHY。
_LIMIT_MARKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (LIMIT_SPEND, ("monthly spend limit",)),
    (LIMIT_SESSION, ("session limit", "usage limit", "rate limit")),
    (LIMIT_TRANSIENT, ("overloaded", "internal server error", "stalled mid-stream",
                       "connection closed", "api error")),
)

#: `resets 9am` ／ `resets 12:20pm` 兩種格式都要吃。全庫實測到 7 個相異 reset 值
#: （`3:50am` `4am` `9am` `11pm` `12:20pm` `12:30pm` `6pm`），**沒有一個落在 5 小時的
#: 固定格點上** ⇒ reset 時刻是滾動視窗、錨在該區塊第一次用量，只能**觀測**不能算。
#: 這就是 `session_resume_planner.DEFAULT_AT_EXPR` 那個 `AddHours(5)` 是缺陷的證據。
_RESET_RE = re.compile(r"resets\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)", re.IGNORECASE)

#: 訊息自報的 IANA 時區，例：`… resets 9am (Asia/Taipei)`。全庫語料實測**每一筆**
#: session limit 訊息都帶這個括號，所以「9am 是哪個時區的 9am」是**資料自己回答的**，
#: 不需要去問機器。
_ZONE_RE = re.compile(r"\(([A-Za-z]+(?:/[A-Za-z0-9_+-]+)+)\)")


def declared_zone(text: object):
    """訊息自報的時區物件；`None`＝沒寫、或這台機器沒有 tz 資料庫可以解析它。

    🔴 **R80 立案（act 在 Linux 容器抓到、Windows 本機結構上看不見的兩個紅）**：
    `sentinel_decide` 的兩支分支判定實測在 UTC 容器與 UTC+8 本機**翻面**
    （`arm_reset` vs `probe`）。根因是 `resets 9am` 這個牆上時刻**沒有被綁在任何時區
    上**：舊實作拿機器的本地時區去解它，於是同一份語料在不同機器上是不同的絕對時刻。
    訊息括號裡就寫著答案，只是沒有人去讀。

    🔴 誠實劃界（本函式會回 `None` 的第二種情況，不粉飾）：`zoneinfo` 需要 tz 資料庫。
    Linux／macOS 由系統提供；**Windows 沒有**，且本 repo 不得為此新增相依
    （`tzdata` 是 PyPI 套件）。本機實測 `ZoneInfo("Asia/Taipei")` →
    `ZoneInfoNotFoundError` ⇒ 這條路在 Windows 上回 `None`，呼叫端退回「`now` 的時區」。
    那個退路在實務上是對的（訊息本來就是 harness 在**同一台機器**上以本地時區算繪的），
    但它不是機器無關的——所以退路成立與否會被 `parse_reset_at` 的呼叫端看見，
    而不是藏起來。
    """
    match = _ZONE_RE.search(str(text or ""))
    if match is None:
        return None
    try:
        return zoneinfo.ZoneInfo(match.group(1))
    except Exception:  # noqa: BLE001 — 無 tz 資料庫／未知地名一律退回呼叫端的框架
        return None


def reset_literal(text: object) -> str | None:
    """訊息裡 `resets <hh[:mm]><am|pm>` 那一段的**字面**（小寫）；`None`＝沒有。

    🔴 立案（R85／C5，`_RESET_RE` 的第二個消費者踩到的那個洞）：
    `tools/probe/reset_window_distribution.py` 要數「相異 reset 字面有幾個」，本來直接
    伸手拿 `guard._RESET_RE`——而 R81 把判讀原語搬進本檔時，hook 那一側是**具名 import
    清單**，私有符號結構上進不了那份清單 ⇒ 該 probe 從此 `AttributeError` rc=1，
    而根 CLAUDE.md 有兩處要求「reset 分佈的數字一律現查」正是靠它。
    ⇒ 跨模組要用的東西就得有公開出口；把私有正則當公開 API 借用，壞掉時是靜默的
    （沒有人在跑它，直到有人照著文件跑一次）。
    """
    match = _RESET_RE.search(str(text or ""))
    return match.group(0).lower() if match else None


def classify_limit(text: object) -> str:
    """把一則錯誤訊息分成四類之一。純函式，零 I/O。

    `LIMIT_UNKNOWN` 是 fail-closed 的那一側：認不出來時呼叫端**不得**排程等待。
    這與本檔其他地方「量不到就閉嘴」同一個方向——不確定時不要做有後果的事。
    """
    low = str(text or "").lower()
    for kind, marks in _LIMIT_MARKS:
        if any(mark in low for mark in marks):
            return kind
    return LIMIT_UNKNOWN


def parse_reset_at(text: object, now: datetime) -> datetime | None:
    """從 `resets <hh[:mm]><am|pm>` 解出**下一個尚未發生的**該時刻；`None`＝解不出來。

    🔴 「下一個尚未發生」不是文青措辭，是唯一正確的規則：那個字串**不帶日期也不帶年**。
    天真地解成「今天的 9am」在下午跑會得到一個**已經過去**的時刻 ⇒ 觸發時刻算成負值 ⇒
    立刻探測、立刻再撞、把剛回來的額度再吃光。實測值裡已經有 `11pm` 與 `3:50am`，
    跨午夜這條路徑真的會走到。

    `None` 時呼叫端**不准**退回「假設 5 小時」——那是猜的，猜出來的時刻拿去排程會得到
    一個「憑證存在、但憑證不回答那個問題」的假綠（排程成立了，只是醒在錯的時間）。

    🔴 **R80：回傳值一律帶 offset（aware），且時區框架有明確的優先序**——
    ① 訊息自報的時區（`declared_zone`，機器無關）；② `now` 自己的時區；
    ③ `now` 是 naive 時先補上機器本地時區。
    ③ 那一格是「讓時刻一律帶 offset」的最後一道：naive 的牆上時刻被 `isoformat()`
    持久化之後就再也分不出它是哪個框架的，讀回來相減會在 DST 跳點上整整差 3600 秒。
    """
    match = _RESET_RE.search(str(text or ""))
    if match is None:
        return None
    hour, minute, meridiem = int(match.group(1)), int(match.group(2) or 0), match.group(3)
    if not (1 <= hour <= 12) or not (0 <= minute <= 59):
        return None
    hour = hour % 12 + (12 if meridiem.lower() == "pm" else 0)
    if now.tzinfo is None:
        now = now.astimezone()
    now = now.astimezone(declared_zone(text) or now.tzinfo)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


def latest_limit_event(path: Path) -> dict | None:
    """逐字稿裡**最後一筆**額度／錯誤事件；`None`＝這支逐字稿沒有。

    指紋是 `type=assistant` ＋ `message.model == "<synthetic>"`（全庫 135 筆皆然）。
    刻意只認這個形狀而不是「訊息裡有 limit 字樣」：同一句話會被 `queue-operation`／
    `user`／`attachment` 等記錄各複述一次（實測同一次撞線在 4 種記錄型別各留一份），
    只有 assistant 合成記錄那一筆是 harness 自己寫的權威版本，其餘是回音。
    """
    found: dict | None = None
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if SYNTHETIC_MODEL not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict) or record.get("type") != "assistant":
                    continue
                message = record.get("message")
                if not isinstance(message, dict) or message.get("model") != SYNTHETIC_MODEL:
                    continue
                content = message.get("content")
                text = ""
                if isinstance(content, list):
                    text = " ".join(str(part.get("text") or "") for part in content
                                    if isinstance(part, dict))
                elif isinstance(content, str):
                    text = content
                found = {"text": text.strip(),
                         "timestamp": str(record.get("timestamp") or ""),
                         "kind": classify_limit(text)}
    except OSError:
        return None
    return found


# ───────────────── R80 P0：哨兵整晚失明的真正成因，與「已處理」的可證判準
# 事故（掌舵者實證）：2026-08-08 02:00~06:50 真的撞線、兩個修復 agent 與 9 個 verify
# agent 全部死在 `You've hit your session limit · resets 6:50am`，而哨兵那三次巡邏
# （08:37／08:52／09:07）**每一次都判「無未處理撞線」**。
#
# 🔴 三個候選歸因，只有第三個經得起實查（前兩個是推測，當回合逐一證偽）：
#  ① 「主逐字稿裡沒有那個字串」——**證偽**。Grep 實證主逐字稿含 `resets 6:50am`，
#     而且其中 3 筆正是 `type=assistant` ＋ `model=<synthetic>` 的權威形狀。
#  ② 「偵測面沒有涵蓋 subagent」——**成立但不是主因**。同 session 下 263 支 subagent
#     逐字稿中有 109 支抓得到限額事件；擴面是對的，但擴了也救不了本次。
#  ③ **真正的主因：`handled_through` 的立案理由是一句假話。** `_arm_sentinel` 把武裝
#     當下的最後一筆事件記為「已處理」，理由逐字是「我們此刻跑得動這支指令，就證明
#     額度是通的」。**那個推論不成立**——武裝是一個**純本機 subprocess，零 API 呼叫**，
#     額度早就見底時它照樣跑得動、照樣把撞線標成已處理。實證：狀態塊
#     `handled_through = 2026-08-07T18:38:56.348Z`，而那次撞線的事件是
#     `18:36:53.465Z`／`18:36:58.074Z` ⇒ **撞線發生兩分鐘後就被標記成「已解決」**，
#     此後每一次巡邏都合法地判 patrol。機制全程「正常運作」，只是守著一個假前提。
#
# 🔴 正解：把「已處理」從**推論**換成**可證的證據**——額度是帳號層級的資源，所以
# 「額度在某時刻之後是通的」的唯一硬證據，就是那之後**真的有一則成功的 API 回應**
# （`type=assistant` ＋ 真 model ＋ 有 `message.usage`）。這件事寫在逐字稿裡，讀檔
# 即可、**成本為零**，與哨兵「巡邏不花 token」的前提相容。
#
# 誤判率是**量出來的，不是挑的**（掃描面擴大必然放大假陽性，故先量再定判準）：
#   判準 B（擴面、只看每支檔最後一筆、無復原證據）  → 假陽性 14.8%（224/1513 支檔）
#   判準 C（擴面＋**同檔**復原證據）                 → 假陽性 **81.3%**（209/257）
#     ⇒ **被自己的量測否決**，而且成因是結構性的：被額度打死的 subagent 在它自己的
#       檔裡永遠不會再有下一則成功回應（它死了）⇒ 同檔證據對 subagent 恆為 False。
#   判準 D（擴面＋**全域**復原證據）                 → 假陽性 **0.0%**（0/257）✅
# 鑑別力反證（同一支量測腳本，把觀測時點倒推到停機進行中的 18:40:00Z）：判準 D 當時
# 會抓到 **4 筆** `quota_session`／`resets 6:50am` ⇒ 它不是靠「全部判已處理」拿到 0%。
def session_transcripts(transcript: Path, max_age_seconds: float = 86400.0,
                        now: float | None = None) -> list[Path]:
    """本 session 的主逐字稿 ＋ 它底下的 subagent 逐字稿（近期修改過的）。

    佈局是**觀察到的**（非官方契約，故 fail-soft）：`<sid>.jsonl` 旁有一個同名目錄
    `<sid>/`，subagent 落在 `<sid>/subagents/*.jsonl` 與
    `<sid>/subagents/workflows/<wf>/*.jsonl`。這裡用 `rglob` 收整棵，不寫死那兩層——
    多一層 workflow 目錄就漏掉一批，正是本次失明的形態之一。

    `max_age_seconds` 是**成本閘**不是判準：一筆「比全域最後成功回應還新」的事件不可能
    出現在很久沒被寫過的檔裡，而哨兵每 15 分鐘跑一次、母體已有 1,500+ 支檔。預設 24h
    遠大於一個額度視窗（實測最長 3.6h），所以它不會把真的未處理事件濾掉。
    """
    now = now if now is not None else time.time()
    found = [transcript] if transcript.is_file() else []
    folder = transcript.with_suffix("")
    if folder.is_dir():
        for path in folder.rglob("*.jsonl"):
            try:
                if now - path.stat().st_mtime <= max_age_seconds:
                    found.append(path)
            except OSError:
                continue
    return found


def _assistant_records(path: Path):
    """該檔裡的 assistant 記錄 `(timestamp, message)`。壞行跳過（逐字稿常有半截尾行）。"""
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"assistant"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict) or record.get("type") != "assistant":
                    continue
                message = record.get("message")
                if isinstance(message, dict):
                    yield str(record.get("timestamp") or ""), message
    except OSError:
        return


def latest_success_at(paths: list[Path]) -> str:
    """這批逐字稿裡**最後一次成功 API 回應**的 ISO 時間戳（沒有就回空字串）。

    「成功」＝ `type=assistant` ＋ **真的 model**（不是 `<synthetic>`）＋ 有 `message.usage`。
    `usage` 是關鍵：那是伺服器真的計費回來的證據，harness 自己合成的錯誤訊息沒有它。

    這一個字串就是「額度在何時之前確定是通的」的硬證據，取代了原本那句**假的**推論
    （「我跑得動武裝指令 ⇒ 額度是通的」——武裝零 API 呼叫，證明不了任何事）。
    """
    best = ""
    for path in paths:
        for stamp, message in _assistant_records(path):
            if (stamp > best and message.get("model") != SYNTHETIC_MODEL
                    and message.get("model") and isinstance(message.get("usage"), dict)):
                best = stamp
    return best


def unhandled_limit_event(transcript: Path, max_age_seconds: float = 86400.0,
                          now: float | None = None) -> dict | None:
    """**還沒被解決的**限額事件裡最早的那一筆；`None`＝沒有（正常情況）。

    判準 D：事件的時間戳 > 全域最後一次成功回應 ⇒ 那之後 API 再也沒通過 ⇒ 未處理。
    取**最早**一筆而不是最後一筆，是因為要拿它的 reset 時刻去排程——同一次停機裡
    每個 subagent 都會留一筆，最早那筆才是真正的撞線時刻（其餘離 reset 更近）。

    🔴 為何不沿用 `latest_limit_event`：那支只看**最後一筆**，而本次事故裡主逐字稿的
    最後一筆是 `quota_spend`（月度上限），把更早、仍未解決的 `quota_session` 整個蓋掉。

    🔴 **R80 補洞（P0 修復自己引入的反向缺陷）**：第一版把**任何**沒有後續成功回應的
    `<synthetic>` 記錄都登記成候選，而 `<synthetic>` 是 harness 對**所有**合成訊息的
    共同標記——`API Error`、`[Request interrupted by user]` 都長這樣。於是一個以中斷
    或一次 API 錯誤收尾的 session（那是常態，不是例外）會被判成「未處理的撞線」，
    走到 `sentinel_decide` 解不出 reset ⇒ `escalate` ⇒ **哨兵把自己刪掉**。
    舊病是「該醒不醒」，新病是「不該死卻自我刪除」，兩者同樣靜默：痕跡只多一行
    `sentinel_escalate`，而 `Get-ScheduledTask` 查不到那支工作，與「正常下班」外觀相同。
    註解裡那個 0.0% 假陽性是**單一時點對 257 支檔的橫斷面**量測，量不到「session 以
    一則 API 錯誤／中斷收尾」這個**縱向**情境 ⇒ 它背書不了這條路徑。
    修法是把 kind 篩選提前到登記候選那一步：只有真的額度類（`LIMIT_SESSION`／
    `LIMIT_SPEND`）才算撞線，`transient`／`unknown` 一律略過。**這不是把 fail-closed
    翻成 fail-open**——被略過的那些本來就不是額度事件，對它們「什麼都不做」才是正解。
    """
    paths = session_transcripts(transcript, max_age_seconds, now)
    if not paths:
        return None
    recovered_at = latest_success_at(paths)
    best: dict | None = None
    for path in paths:
        for stamp, message in _assistant_records(path):
            if message.get("model") != SYNTHETIC_MODEL or not stamp > recovered_at:
                continue
            content = message.get("content")
            text = (content if isinstance(content, str) else
                    " ".join(str(part.get("text") or "") for part in content or []
                             if isinstance(part, dict))).strip()
            kind = classify_limit(text)
            if kind not in (LIMIT_SESSION, LIMIT_SPEND):
                continue
            if best is None or stamp < best["timestamp"]:
                best = {"text": text, "timestamp": stamp, "kind": kind,
                        "source": path.name, "recovered_at": recovered_at}
    return best


def newest_activity_at(paths: list[Path]) -> float:
    """這批逐字稿裡最新的 mtime（給存活判準用）；空清單回 0.0。

    🔴 為何不只看主逐字稿：扇出模式下主逐字稿可能好一陣子沒被寫，而 subagent 正在狂跑
    ⇒ 只看主檔會把一個很忙的 session 誤判成閒置，而閒置到門檻就會**自我解除**。
    """
    stamps = []
    for path in paths:
        try:
            stamps.append(path.stat().st_mtime)
        except OSError:
            continue
    return max(stamps) if stamps else 0.0
