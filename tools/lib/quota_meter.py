"""額度水位取數器 — **唯一會為了額度碰網路的地方**（訴求 a）。"""
# WHY —— 為什麼新開這一支檔，以及它與既有三個家的分工
# ---------------------------------------------------------------------------
# 本 repo 判過「護欄層自我增殖是最大缺陷來源」，所以新開檔要辯護。三個理由都是量出來的：
#
#  ① `tools/session_resume_planner.py` 塞不下：落地當回合 `check_loc_budget.py` 實測
#     `[guardrail_cli<=750] tools/session_resume_planner.py: 749 （餘裕 1 行）`。
#     這是硬牆不是偏好，本包因此**一行都沒有動它**。
#  ② 不能放進 `.claude/hooks/context_budget_guard.py` 的主路徑：那支 hook 在**每一次**
#     PreToolUse／PostToolUse 都會跑。把 HTTP 呼叫放進去＝給每一次工具呼叫加上網路延遲，
#     而該檔自己記載過 P0「hook 誤觸 deny 會把所有工具硬鎖死」。
#     **取數（會失敗、會慢、會逾時）與判讀（必須快、必須確定性）的失效模式不同，必須分開。**
#  ③ `tools/lib/quota_escalation.py`（R81 另一包）管的是**撞線之後**：叫人、快照被打死的
#     扇出。本檔管的是**撞線之前**：現在幾 %。兩者的輸入、失效模式、觸發時機都不同。
#
# 分工一句話：**本檔是唯一的取數者與唯一的寫者。**
#   quota_meter（本檔） ──寫──▶ 快取檔（檔名的唯一的家＝下方 `CACHE_NAME`）
#                                   ├──讀──▶ context_budget_guard（判讀＋動作）
#                                   └──讀──▶ AutoClaude adapter（未落地，檔案契約）
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
#:
#: 🔴 **R81 收斂／SD-B4：這條路只有一個假設、沒有替代來源，且它在本輪之前是靜默的。**
#: 本包新增／改動的 production 碼裡，平台敏感構件全部帶分支（`os.name != "nt"` 早退、
#: `NO_WINDOW` 走 `getattr`、`notify()` 三分支），**只有這一行沒有**；而全 repo 對
#: 「另一個平台的憑證存在哪」零次討論。
#:
#: 本輪**刻意不加平台分支**，理由是誠實而不是省事：我手上沒有 mac 真機，寫一個驗不了的
#: 分支正是 `DEF-101-766` 的形狀（在 Windows 語境裡寫出只在 Windows 成立的判準）。
#: 改成可觀測的那一半——`measure_detail()` 把「憑證讀不到」與「HTTP 非 200／哪個碼」
#: 分開回報（見 `REASON_*`），於是假設不成立時它會**說出來**而不是整條額度軸靜默 no-op。
#: 非 Windows 的憑證來源**未驗**，已登記在 ADR-XPLAT-005 與缺陷帳本，交由下一輪承接
#: （承接輪號寫在帳本那一列，不寫進程式碼檔）。
CREDENTIALS = Path(os.path.expanduser("~")) / ".claude" / ".credentials.json"

#: `measure_detail()` 的失效字面。**它們就是 B4 要的那個可觀測面**：token 過期、
#: 斷網、schema 升版、憑證檔不在，四種情況在本輪之前與「額度很健康」外觀完全一致。
REASON_OK = "ok"
REASON_NO_CREDENTIALS = "no-credentials"
REASON_UNREACHABLE = "meter-unreachable"
REASON_NO_BUCKETS = "no-buckets"

#: 快取檔。🔴 **刻意不帶 session id**：額度是 **per-account** 的單一池，而
#: `%TEMP%` 實測有 20 個以上相異 session 各持一份自己的狀態檔。帶 sid 的快取會讓
#: N 個併發載體各自量一份、各自判一次，那與「一個帳號一個池」在單位上就不匹配
#: （SA-B5／SD-B1 的同一個病）。一個帳號、一份快取。
CACHE_NAME = "autosdd_quota.json"

#: 內部唯一表示：**0..100 的 float**。每個通道在自己的入口寫死該通道的單位。
#: 🔴 這是本包唯一能抓到「差 100 倍」的地方：`0.3` 拿去比 `80` 永遠不觸發（閘門恆綠）、
#: `30.0` 拿去比 `0.8` 永遠觸發（閘門恆紅），兩個方向都在 rc=0 的外觀下失效。
SCALE_PERCENT = 1.0        # REST `utilization`(float 0..100)／`limits[].percent`(int 0..100)
SCALE_FRACTION = 100.0     # headless stream-json `rate_limit_event.utilization`(0..1)

#: HTTP 逾時。取數失敗的正確方向是「量不到」，不是「慢慢等」——本檔的消費者是
#: 15 分鐘一次的巡邏與 fire-and-forget 刷新，沒有人在等這個值。
HTTP_TIMEOUT_SECONDS = 10

SCHEMA = "autosdd.quota/1"


def cache_path() -> Path:
    # `tempfile.gettempdir()` 而不是 `$env:TEMP`：後者在 macOS/Linux 的 PS Core 上
    # **不存在**，`Join-Path $env:TEMP …` 會直接拋 null 綁定例外（鐵律三，本 repo 已有
    # 專屬判準 `TestPowerShellPlatformSensitiveSites`）。
    return Path(tempfile.gettempdir()) / CACHE_NAME


def access_token() -> str:
    # 🔴 token 值**永遠不回傳給呼叫端以外的任何地方**：不進 log、不進痕跡、不進任務書
    # （調研 S1-08 的逐字要求）。讀不出來一律回空字串，由呼叫端判「量不到」。
    try:
        data = json.loads(CREDENTIALS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    oauth = data.get("claudeAiOauth") if isinstance(data, dict) else None
    token = oauth.get("accessToken") if isinstance(oauth, dict) else None
    return token if isinstance(token, str) else ""


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
def bucket_readings(payload: object) -> list[dict]:
    """payload 裡每一個看得到水位的桶：`{kind, pct, resets_at, via}`。"""
    if not isinstance(payload, dict):
        return []
    out: list[dict] = []
    for item in payload.get("limits") or []:
        if not isinstance(item, dict):
            continue
        pct = normalize_pct(item.get("percent"), SCALE_PERCENT)
        if pct is not None:
            out.append({"kind": str(item.get("kind") or "?"), "pct": pct,
                        "resets_at": item.get("resets_at"), "via": "limits[].percent"})
    for key, val in payload.items():
        if key == "limits" or not isinstance(val, dict):
            continue
        for field, scale in (("utilization", SCALE_PERCENT), ("percent", SCALE_PERCENT)):
            pct = normalize_pct(val.get(field), scale)
            if pct is not None:
                out.append({"kind": key, "pct": pct, "resets_at": val.get("resets_at"),
                            "via": f"{key}.{field}"})
                break
    return out


def worst(readings: list[dict]) -> dict | None:
    """最緊的那一桶。空清單回 `None`（量不到 ≠ 量到零）。"""
    # 🔴 刻意**不用 `is_active` 篩**：兩次獨立觀測（ADR 那次 session=True、本包這次
    # weekly_all=True）都顯示它只是在追蹤 max ⇒ 取 max 與它一致，且不依賴一個沒有
    # 契約的欄位語意。取 max 的錯誤方向是「太早節流」，那是可接受的方向。
    return max(readings, key=lambda r: r["pct"]) if readings else None


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


def measure_detail(timeout: int = HTTP_TIMEOUT_SECONDS) -> tuple[dict | None, str]:
    """量一次，回 `(讀數 dict 或 None, 失效字面)`。**這是 B4 的修法本體。**

    🔴 立案（SD-B4）：`fetch_usage()` 檔頭 §S1-08 逐字要求「401 與『額度真的沒回來』
    必須在痕跡裡分得開」，而它**做到了**——回 `(status, payload)`。真正掉東西的是它
    唯一的呼叫端：舊 `measure()` 把 status 丟掉、四種失效一律回同一個 `None`
    ⇒ token 過期（401）、斷網、憑證檔不在、schema 升版，在消費端外觀完全相同。
    """
    # 🔴 「量不到 ≠ 量到零」是本 repo 通篇的紀律，在這裡尤其致命：回 0 ＝永遠正常
    # （靜默失明），回 100 ＝永遠 halt。兩個方向都不可接受，所以只能回 `None`。
    token = access_token()
    if not token:
        return None, REASON_NO_CREDENTIALS
    status, payload = fetch_usage(token, timeout)
    if status == 0:
        return None, REASON_UNREACHABLE
    if status != 200 or not isinstance(payload, dict):
        return None, f"http-{status}"
    readings = bucket_readings(payload)
    top = worst(readings)
    if top is None:
        return None, REASON_NO_BUCKETS
    return {
        "schema": SCHEMA, "pct": top["pct"], "kind": top["kind"],
        "resets_at": top["resets_at"], "via": top["via"], "source": "endpoint",
        "http_status": status,
        "measured_at": datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
        "denominator": denominator_of(payload),
        "buckets": sorted(({"kind": r["kind"], "pct": r["pct"]} for r in readings),
                          key=lambda r: -r["pct"]),
        "schema_keys": sorted(payload),
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
    den = reading["denominator"]
    lines = [f"pct={reading['pct']:.1f}%  kind={reading['kind']}  via={reading['via']}",
             f"resets_at={reading['resets_at']}  measured_at={reading['measured_at']}",
             f"denominator[{den['kind']}]={den['text']}"]
    if den["cross_check"]:
        lines.append(f"cross_check={den['cross_check']}")
    lines.append("buckets=" + ", ".join(
        f"{b['kind']}:{b['pct']:.1f}" for b in reading["buckets"]))
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
                  + (f"{reading['pct']:.1f}% {reading['kind']}" if reading else "量不到"),
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
