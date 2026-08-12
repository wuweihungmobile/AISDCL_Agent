"""額度／配速判讀層機械物的**判準本體**（純函式）。消費端住 `tools/tests/`。"""
# ─────────────────────────────────────────────────────────────────────────────
# WHY 這一支檔存在（R86；先例＝`tools/lib/guard_bucket_policy.py`）
# ---------------------------------------------------------------------------
# 判準與消費端分離：`tools/tests/test_quota_policy.py` 原本把「判準本體」與「斷言」寫在
# 同一支檔，於是每加一道判準就同時長大兩件事。搬家之後測試檔只留「呼叫判準 ＋ 斷言」，
# 而判準連同它的 WHY 住在這裡。
#
# 🔴 兩個必須同時成立的理由（缺一就會被讀成「為了逃出行數統計面」）：
#   ① **架構**：這些函式沒有一個依賴 unittest——它們是對「源碼／讀數」的純判定，
#      本來就不屬於測試框架層。M2／M5／M7／M10 四族都是 `(輸入) -> list[str]` 的形狀。
#   ② **行數面**：`tools/tests/*.py` 受護欄層行數棘輪管（非遞迴、含未追蹤檔），而
#      `tools/lib/` 不在那個面內。R86 到期義務要求收工回到基線，而本包的判準若留在測試
#      檔內就得由別包去砍別的東西來抵——那筆帳最後會砍到真的判準上。
#   🔴 **鑑別力不得下降**是硬約束：搬家後全部合成注入自證重跑，結果必須與搬家前逐字相同
#      （R85 教訓 3：收斂時把牙一起收掉，而收斂看起來一定是進步）。
from __future__ import annotations

import ast
import re
from datetime import datetime, timedelta

_INF = float("inf")

# ── M2／M5／M7／M10：自 `tools/tests/test_quota_policy.py` 原地搬入（一字未改）──────


def cap_num(cap) -> float:
    """`None`（不設限）視為 +∞，才能與整數 cap 比大小。"""
    return _INF if cap is None else float(cap)


def m2_problems(cap_fn, rec_fn) -> list[str]:
    """固定 pct=79，cap 必須隨 reset 變遠而**非遞增**，且近端嚴格大於中段。"""
    problems = []
    near, mid, far = cap_fn(79, 3), cap_fn(79, 240), cap_fn(79, 8640)
    if not (cap_num(near) > cap_num(mid) > cap_num(far)):
        problems.append(f"79% 的 cap 未隨期程遞減：{near}/{mid}/{far}")
    seq = [cap_num(cap_fn(79, m)) for m in range(1, 20000, 37)]
    if any(b > a for a, b in zip(seq, seq[1:])):
        problems.append("cap 隨 minutes 增大而變寬（方向掃描失敗）")
    # 反向鑑別力：free 帶的 cap 恆為 None，差別只出現在建議值上
    if cap_fn(20, 3) is not None or cap_fn(20, 240) is not None:
        problems.append("free 帶的 cap 不該被設限")
    if rec_fn(20, 3) <= rec_fn(20, 240):
        problems.append("free 帶的『加速』沒有出口（rec 必須隨 reset 逼近而變大）")
    return problems


#: 決策詞。🔴 規格原表另有 `band`／`budget`——**刻意移除**：規格自己的 `pct_band(pct, p)`
#: 是二元決策合法的前半，把它判紅就是 15 筆假紅裡的第一筆，而那種鎖活不過一輪。
_DECISION_WORDS = ("cap", "tier", "fanout", "throttle", "halt", "gate", "decide")
_SCALAR_PARAMS = ("pct", "percent", "utilization")
#: 🔴 第二軸的證據。規格原文只寫「參數名含 pct 且註記為 float/int」——照抄會把
#: 規格自己宣告的 `axis_cap(pct: float, minutes: float | None, p: Policy)` 判紅。
#: 真正要禁的是「**只**由一個純量決策」，所以判準多一個合取項：沒有任何期程輸入。
#:
#: 🔴 R82 複驗鏡實測的**三條洗白路徑**（此前 `now`／`state` 也在這張表裡）：
#:   · 加一個 `now: datetime` ⇒ 判準放行。但 `now` 不帶任何 reset 時刻，
#:     「現在幾點」單獨存在時對 horizon 零資訊 ⇒ 它從來就不是第二軸的證據。
#:   · 加一個 `state` ⇒ 判準放行。吃 `QuotaState` 的函式根本不需要 `pct` 參數，
#:     兩者同時出現正是「表面上收了狀態、實際上還是照純量決策」的形狀。
#:   · 寫成 `async def` ⇒ `ast.FunctionDef` 比對整片失明（見下方 walk 的型別）。
#: 三條都不是假想：M5-④ 要埋的 `fanout_cap(pct)` 就住在下一階段要接線的
#: `tools/lib/quota_gate.py`，任何一條都能讓它靜默逃出射程。
_HORIZON_PARAMS = ("minutes", "horizon", "resets", "deadline", "remaining", "until")
_FUNC_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


def _is_number_annotation(node) -> bool:
    return node is not None and any(
        tok in ast.unparse(node) for tok in ("float", "int"))


def scalar_decision_defs(source: str) -> list[str]:
    """列出「只吃一個純量水位就做決策」的函式（M5 靜態半 ④）。"""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, _FUNC_NODES):
            continue
        if not any(w in node.name.lower() for w in _DECISION_WORDS):
            continue
        args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
        names = [a.arg.lower() for a in args]
        if any(h in n for n in names for h in _HORIZON_PARAMS):
            continue
        if any(any(s in a.arg.lower() for s in _SCALAR_PARAMS)
               and _is_number_annotation(a.annotation) for a in args):
            found.append(node.name)
    return found


def worst_mentions(source: str) -> list[str]:
    """`worst()` 的墓碑：**定義與呼叫兩邊都算**（只認 `def worst` 會漏掉呼叫端）。"""
    hits = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, _FUNC_NODES) and node.name == "worst":
            hits.append("def worst")
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "")
            if name == "worst":
                hits.append("call worst()")
    return hits


def scalar_escape_problems(cls) -> list[str]:
    """執行期半：型別上**不得**存在任何無參數的取值出口。

    🔴 判準必須走 `__mro__` 的 `__dict__`，**不能**用 `getattr`：`object` 自己就帶
    `__lt__`／`__gt__`（回 `NotImplemented` 的預設實作），`getattr` 版對**任何**
    類別都回非 None ⇒ 那是一支恆紅、因而必然被刪掉的鎖。本註解是實測得來的：
    第一版正是 `getattr`，跑出來 `Axis` 自己就被判了兩筆違規。
    """
    problems = []
    owners = [k for k in cls.__mro__ if k is not object]
    for dunder in ("__float__", "__int__", "__index__", "__lt__", "__gt__"):
        if any(dunder in k.__dict__ for k in owners):
            problems.append(f"{cls.__name__} 定義了 {dunder} ⇒ 不指名軸別就拿得到數字")
    return problems


PCT_RE = re.compile(r"\d+(?:\.\d+)?%")


def m7_problems(text: str) -> list[str]:
    """**逐一個百分比**判：每個 `%` 自己前面要有 `kind=`、後面要有剩餘分鐘。

    🔴 判準由「chunk 級」改成「百分比級」（R82 複驗鏡 ⑦）。舊版先用
    `re.split(r"[；\\n　]", text)` 切段、再問「這一段裡有沒有 kind= 和 分鐘」——
    於是**只要改 `describe()` 的分隔符**（或乾脆不放分隔符），兩個桶就會落進同一段，
    第一個桶的 `kind=`／「分鐘」替第二個裸百分比背書，整段矇混過關。判準去問文字
    怎麼被切，而不是去問每個百分比自己有沒有被指名——那是把鑑別力寄放在被判者手上。

    現在的切法只依**百分比自己的位置**：一個 `%` 的「名牌區」是它與**前一個** `%`
    之間、「期程區」是它與**後一個** `%` 之間。分隔符換成什麼都不影響。
    """
    problems = []
    marks = list(PCT_RE.finditer(text))
    for i, mark in enumerate(marks):
        before = text[marks[i - 1].end() if i else 0: mark.start()]
        after = text[mark.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        shown = text[max(0, mark.start() - 20): mark.end() + 20]
        if "kind=" not in before:
            problems.append(f"裸的百分比，沒說是哪一桶：…{shown}…")
        if "分鐘" not in after and "reset 距離不明" not in after:
            problems.append(f"沒說還剩幾分鐘：…{shown}…")
    return problems


def chunk_level_m7_problems(text: str) -> list[str]:
    """注入形態＝**舊的 chunk 級判準**（只留作對照組，不是現行判準）。"""
    problems = []
    for chunk in re.split(r"[；\n　]", text):
        if not PCT_RE.search(chunk):
            continue
        if "kind=" not in chunk:
            problems.append(f"裸的百分比：{chunk!r}")
        if "分鐘" not in chunk and "reset 距離不明" not in chunk:
            problems.append(f"沒說還剩幾分鐘：{chunk!r}")
    return problems


def decision_constructors(source: str) -> list[str]:
    """列出「自己組出一個 `Decision`」的函式——正解是**恰好一個**（`decide`）。"""
    owners = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef):
            continue
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                    and inner.func.id == "Decision"):
                owners.append(node.name)
                break
    return sorted(set(owners))


# ── R86：缺陷 A（門檻是絕對分鐘數）／B（瞬時 pct 無意義）／C（cap 保護錯的配額）────
# 🔴 **對照組是程式不是散文**：`r85_axis()` 原地重建 R85 版判讀（horizon 只吃兩個絕對
# 門檻、band 只吃裸 pct、無攤提），所以「舊版對這兩個情境給出**相同**答案」是被跑出來
# 的，不是被宣稱的。少了它，每一支都只證明「新版會動」，而不是「舊版不會動」。
# 全部逐項實測數字與治法辯護＝`docs/06_quality/CrossPlatform_R86_Pace_Calibration.md`。

#: 掌舵者 2026-08-12 貼出的 Claude Code CLI 畫面 ＋ 同一刻的 axes 快照。repo 至今**唯一**
#: 一筆外部獨立校準基準（訴求 6z 的調研結論：查不到任何官方通道能回答個人訂閱帳號的
#: 當前水位＋reset）⇒ 它一旦只留在對話裡就等於沒發生（R85 教訓 5）。
#: `(CLI 原文, pct, resets_at, 讀取時刻, CLI 顯示的剩餘分鐘)`
CLI_CALIBRATION = ("Team Current session / Resets in 1 hr 38 min / 1% used",
                   1.0, "2026-08-12T15:00:00+00:00", "2026-08-12T21:27:00+08:00", 98.0)

#: 容差（分鐘）。理由不是「誤差」而是**三個各自有界的錯位**：CLI 與程式不是同一刻讀的
#: ＋ CLI 的分鐘是截斷顯示 ＋ 讀取時刻只記到分。10 分鐘＝三者之和的寬鬆上界；
#: `resets_at` 若真的解錯（差一小時／差一天／時區當成本地）照樣會紅。pct 那一格**不吃容差**。
CLI_TOLERANCE_MINUTES = 10.0

#: 方向鎖掃描網格。刻意含 `None`／負值（時鐘偏移）與兩個絕對門檻的左右鄰點。
_SWEEP_KINDS = ("five_hour", "seven_day", "session", "spend")
_SWEEP_MINUTES = (None, -5.0, 1.0, 29.0, 31.0, 100.0, 200.0, 359.0, 361.0,
                  1008.0, 4000.0, 5041.0, 8640.0)


def r85_axis(policy, quota, pct: float, minutes) -> tuple:
    """R85 版單軸讀數 `(horizon, cap, rec)`——本節的對照組。"""
    if minutes is None:
        horizon = quota.AXIS_NONE
    elif minutes < 0:
        horizon = quota.AXIS_MID
    elif minutes <= policy.accel_window_minutes:
        horizon = quota.AXIS_NEAR
    elif minutes <= policy.far_horizon_minutes:
        horizon = quota.AXIS_MID
    else:
        horizon = quota.AXIS_FAR
    band = quota.pct_band(pct, policy)
    return horizon, quota._cap_for(band, horizon, policy), quota._rec_for(
        band, horizon, policy)


def _state(quota, now: datetime, specs):
    return quota.QuotaState(
        tuple(quota.Axis(k, p, None if m is None
                         else (now + timedelta(minutes=m)).isoformat())
              for k, p, m in specs), now.isoformat(), "endpoint", "ok")


def new_axis(policy, quota, now, kind, pct, minutes, extra=(), ratio=None):
    """新版單軸讀數，**經 `axes_of`**（＝生產路徑，不是直接呼叫判準）。"""
    return quota.axes_of(_state(quota, now, [(kind, pct, minutes), *extra]),
                         now, policy, ratio, "test")[0]


def defect_a_divergence(policy, quota, now) -> tuple:
    """`(舊 horizon 兩格, 新 horizon 兩格)`：同 pct、同距離、不同窗長。"""
    old = tuple(r85_axis(policy, quota, 50, 200)[0] for _ in range(2))
    new = tuple(new_axis(policy, quota, now, k, 50, 200).horizon
                for k in ("five_hour", "seven_day"))
    return old, new


def defect_b_divergence(policy, quota, now) -> tuple:
    """`(舊 cap 兩格, 新 cap 兩格)`：pct=74 ＋ 已過 20%／90%（同一個 7 天窗）。"""
    minutes = (8064.0, 1008.0)
    return (tuple(r85_axis(policy, quota, 74, m)[1] for m in minutes),
            tuple(new_axis(policy, quota, now, "seven_day", 74, m).cap for m in minutes))


def defect_c_divergence(policy, quota, now, ratio: float = 7.0) -> tuple:
    """`(舊 cap 兩格, 新 cap 兩格, 本窗餘裕兩格)`：短窗讀數固定、長窗剩餘窗數不同。"""
    old, caps, headrooms = [], [], []
    for long_minutes in (600.0, 9000.0):
        extra = (("seven_day", 75.0, long_minutes),)
        decision = quota.decide(
            _state(quota, now, [("five_hour", 40.0, 100.0), *extra]),
            now, policy, ratio, "test r=7")
        old.append(r85_axis(policy, quota, 40.0, 100.0)[1])
        headrooms.append(round(decision.amort.headroom_pp, 1))
        caps.append(new_axis(policy, quota, now, "five_hour", 40.0, 100.0,
                             extra, ratio).cap)
    return tuple(old), tuple(caps), tuple(headrooms)


def unlicensed_acceleration(policy, quota, pace, now) -> tuple:
    """`(所有放寬的格子, 其中沒有節省證據的格子)`——方向鎖的本體。

    掃 `(pct, 剩餘分鐘, 桶名)` 網格；凡新版 cap／rec 比 R85 版寬的那一格，該軸的
    `lead_pp`（相對線性預算）**必須 ≤ 0**。加速猜錯會爆額度，減速猜錯只是慢一點
    ⇒ 不對稱是刻意的。回傳兩個清單：第一個為空＝這道判準失去鑑別力（缺陷 A 沒被治）。
    """
    looser = []
    for kind in _SWEEP_KINDS:
        window = pace.window_minutes(kind)
        for pct in range(0, 101, 5):
            for minutes in _SWEEP_MINUTES:
                reading = new_axis(policy, quota, now, kind, float(pct), minutes)
                _h, old_cap, old_rec = r85_axis(policy, quota, float(pct), minutes)
                if (cap_num(reading.cap) > cap_num(old_cap)
                        or reading.recommended > old_rec):
                    looser.append((kind, pct, minutes, old_cap, reading.cap,
                                   pace.lead_pp(float(pct), minutes, window)))
    return looser, [row for row in looser if row[5] is None or row[5] > 0]


def backward_compat_problems(policy, quota, now) -> list[str]:
    """窗長解不出的軸必須**逐格**等於 R85 版（向後相容是跑出來的，不是宣稱的）。

    `AUTOSDD_QUOTA_FAR_HORIZON_MINUTES`／`..._ACCEL_WINDOW_MINUTES` 兩個既有 env 鍵
    因此一格都沒有消失：窗長不明時它們就是門檻本身。
    """
    problems = []
    for pct in (0, 20, 55, 75, 90, 96):
        for minutes in (None, -5.0, 29.0, 31.0, 359.0, 361.0, 8640.0):
            reading = new_axis(policy, quota, now, "session", float(pct), minutes)
            got = (reading.horizon, reading.cap, reading.recommended)
            want = r85_axis(policy, quota, float(pct), minutes)
            if got != want:
                problems.append(f"session {pct}%@{minutes}：{got} != R85 版 {want}")
    return problems


def contract_literal_problems(contract, adapter_src: str, port_src: str) -> list[str]:
    """寫入端與引擎讀取端的**兩個字面**（檔名／schema）必須逐字相等。

    🔴 為何必須有這一支：兩邊結構上不准互相 import（`.importlinter` 的
    `no-harness-import`）⇒ 那個縫只能由判準縫起來。改掉任一邊 ⇒ 寫入者寫一份沒有人讀
    的檔，而**失敗表徵與成功完全相同**（引擎照跑、只是永遠走保守地板）。
    """
    problems = []
    for label, value, source in (("PACE_CACHE_NAME", contract.CONTRACT_NAME, adapter_src),
                                 ("PACE_SCHEMA", contract.CONTRACT_SCHEMA, port_src)):
        if f'{label} = "{value}"' not in source:
            problems.append(f"{label} 兩邊不一致：寫入端是 {value!r}，引擎側找不到同值宣告")
    return problems


def pace_line_problems(report: str) -> list[str]:
    """`--pace` 全文必須答得出「為什麼空著也不能衝」（R86；缺一個中間量即紅）。"""
    return [f"攤提那一行少了 {token}" for token in
            ("攤提", "本窗配額", "本窗餘裕", "kind=five_hour", "kind=seven_day")
            if token not in report]
