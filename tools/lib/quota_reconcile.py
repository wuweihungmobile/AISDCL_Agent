#!/usr/bin/env python3
"""外部宣稱讀數的**相容性判別**：`(kind, pct, 距 reset 幾分鐘, 宣稱時刻)` 對得上落款嗎？

立案（2026-08-23 22:53 一起真實的**假陰性**）：畫面一份讀數（session 2%／180 分鐘）與
`--pace` 同一分鐘的量測（53%／6 分鐘）衝突，主控把它寫成「真分歧、我不知道哪一邊對」，
排了一個 8 分鐘實驗才等到第二份畫面（54%／5 分鐘）佐證工具。決定性判別當下就在手上：
`quota_burn.jsonl` 今天有一條**單調遞增**的 session 序列，而 180 分鐘那一點是孤立點。
病灶不是「守衛不夠」而是**守衛只裝在輸出面**——宣稱要出處，而**輸入**沒有人問出處：
主控用「收到它的那一刻」替一份來源不明的讀數蓋了時間戳。本檔補的就是輸入面那一格。

🔴 **這不是「使用者說錯了」的裁決器**。它只回答一個問題：這一組數字與落款相容嗎。
不相容的頭號原因是**面板不是現值**（本次立案逐字命中：2%／180 分鐘與落款
`ts=2026-08-23T19:59:04+08:00` 的 session=2.0 逐格相同，該時刻距真 reset 亦為 180.9 分鐘
⇒ 那是一份約 174 分鐘前的**真**讀數，不是假讀數）。用途是**在主控開始推理之前先跑一次**，
避免把一個孤立點與一條自洽序列等重看待；措辭上不得暗示誰比較不可信。

三態刻意不可折疊（同本層「量不到 ≠ 量到零」的既有紀律）：
  · `compatible`／`incompatible`／`undecidable`。**`undecidable` 不得折進任一邊**，
    否則「落款不足以判斷」會長得像「已核對通過」。

🔴 兩條判準都是**聯合式**：pct 單調性與倒數單調性各自單獨都**不成立**（下段），只有合起來
才是硬結論。這不是保守，是落款資料結構決定的——`quota_pace.row_of()` 一列都沒有寫
`resets_at`，所以「這一列屬於哪一個視窗」在落款裡沒有記載。
🔴 **上一句自 DEF-200-200 ④ 起只對舊列成立**（此處刻意保留原文而非改寫，因為聯合式判準
的立案理由就是它）：`row_of()` 現在會落逐軸 `resets_at`（讀取面＝`resets_from_jsonl()`，
缺這一鍵的舊列回空 dict）。本檔**尚未**改用那一欄——實測本機落款 59 列中只有 1 列帶它，
拿一列去換掉一個已證的聯合式判準會讓判別力倒退；等新格式列累積到足以做假紅普查（同
`estimate_ratio` 的 `n<3 ⇒ 保守取 min` 紀律）才是動它的時機。這是**登記的殘餘**，不是漏改。
  · 倒數給出**隱含視窗**：`R = 宣稱時刻 + 倒數`、`S = R − 窗長`。
  · pct 單調性在那個視窗**內部**才是硬約束（視窗起點 pct≈0、其後只增）。
  R1〈隱含視窗內 pct 必須單調〉落在 `(S, R)` 內的落款列，時刻早於宣稱者 pct 必須 ≤ 宣稱
     pct、晚於宣稱者必須 ≥ 宣稱 pct。任一列違反 ⇒ 不相容（印出它比對到的那一列）。
  R2〈隱含視窗不得包住一次觀測到的 reset〉落款裡 pct 下降處＝一次真的翻頁；若 `(S, R)`
     把某一次下降的**前後兩列都**包在裡面，該視窗就不可能是同一個視窗 ⇒ 不相容。
  這兩條合起來就是任務書講的那個自我矛盾組合：pct 大跌**必然**意味著剛剛 reset 過，而
  reset 會把倒數推回接近窗長 ⇒ 「pct 大跌＋倒數也大跌」在算術上同時成立不了。

🔴 為什麼**不**做「pct 單調性單獨判」（本檔第一版做過，被自己的假紅普查證偽並拆掉）：
  第一版的 C1 是「宣稱 pct 必須被同一個『沒觀測到下降的 run』內前後兩列夾住」。以落款
  自身 143 筆讀數做假紅普查，逐字抓到 5 筆**假紅**，其中 `session 2026-08-12T23:34:56
  pct=24`：前一列 22:53:14=35、後一列 00:08:21=38，而那兩列相距 75 分鐘——一次 reset
  完全放得進那個空隙（同一份落款另有 0→31pp／75 分鐘的實測燒率）。也就是「沒觀測到
  下降」**不能**證明「其間沒有 reset」，第一版把那個前提當成已證。已否決的兩個補法：
  (a) 用「run 的時間跨度 < 窗長」當前提——實測那 5 筆的 run 跨度全部遠小於窗長（82.6／
      116.7／1673.2 分）⇒ 零鑑別力。
  (b) 用「reset 每隔窗長一次」推出 reset 網格——本層既有紀律逐字寫著 reset 時刻是**滾動
      視窗、只能觀測不能算**；實測亦否證（活快取 `resets_at` 減一個窗長＝22:49:59.9，而
      當日真 reset 在 22:59:59.8，差 10 分鐘）。
  ⇒ 只給 pct 與時刻、不給倒數時，本檔一律回 `undecidable`。那是真的判不出，不是保守。

🔴 誠實劃界（擋不到什麼）：
  · **窗長解不出** ⇒ 兩條皆 `undecidable`，不猜。窗長來源見 `resolve_window()`：桶名文法，
    或由「同 `resets_at` 的鄰軸」繼承（`session` 今天靠 `five_hour` 繼承到 300）。繼承讀的是
    **當下**那份快取，若宣稱時刻之後方案／桶結構變過，窗長可能對不上那個時刻。
  · **宣稱落在落款空隙裡**：`(S, R)` 內沒有任何落款列 ⇒ `undecidable`。今天實測落款空隙
    中位數 12.6 分鐘、p90 118.3 分鐘、最大 4214.8 分鐘 ⇒ 長空隙上本檔結構上沉默。
    落款「沒觸發＝檔不長大」，所以「查不到」≠「沒發生」。
  · **使用者讀的是面板另一列**（軸別誤讀，例：`weekly_all` 被當成 `session`）：本檔一律以
    呼叫端指名的 `kind` 為準，認不出軸別誤讀。徵候是「同一組數字對另一軸 compatible」，
    那要呼叫端自己多跑一次別的軸，本檔不代為猜測。
  · **偏差落在容差內**：`PCT_TOL`／`MINUTE_TOL` 以下的錯讀數一律放行。這是設計取捨：
    面板與落款都是整數讀數，容差收小換來的是假紅。
  · **倒數本身不準時，本判別會說不相容**——這是它的定義而不是缺陷，但它決定了假紅怎麼量。
    最終普查數字（母體＝落款自身每一筆真讀數，倒數由觀測到的翻頁區間反推）：
      - 反推區間 ≤10 分（合成倒數誤差 ≤±5 分＝`MINUTE_TOL`）：session／five_hour 各
        **16 筆全數 compatible，假紅 0.0%**；長窗兩軸乾淨母體為 **0 筆**（落款從未把一次
        weekly 翻頁夾到 10 分鐘內，最窄 20.1 分）⇒ **長窗軸上本判別未經實證**。
      - 反推區間全收（合成倒數誤差可達數十分鐘）：session 22/106（20.8%）判不相容，
        且 22 筆全部是 R2、全部來自同一次翻頁事件；改用 run 界定證據之前是 52/106
        （49.1%）。兩組數字之間判準碼一行沒動，變的只有合成倒數的精度。
  · **宣稱時刻晚於落款最後一列**（最常見的真實用法：現在有人貼了一份讀數）：那一段完全
    沒有證據，`compatible` 只代表「與已知的過去不衝突」。判別會把這件事連同差幾分鐘一起
    印出來——沒有這一句，一份 3 小時前的面板會拿到一張看起來像「已核對」的通行證。
  · **證據限定在一個觀測 run 內**（見上方那段 WHY）的代價：run 很短時可用證據就很少，
    判別會偏向 `undecidable`。這是刻意選的方向——寧可判不出，不要把量測誤差算成矛盾。
  · 答案會隨落款長大而改變（`(S, R)` 內多了列）。這是刻意的：落款是累積事實。
  · 本檔只判**單一組**宣稱。同一份面板的多列彼此矛盾（跨軸不自洽）不在射程內。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import quota_pace  # noqa: E402

COMPATIBLE = "compatible"
INCOMPATIBLE = "incompatible"
UNDECIDABLE = "undecidable"

#: pct 容差（pp）。落款與面板都是整數 pp 讀數，各自 ±1 ⇒ 2 是「兩邊都取到最壞」。
PCT_TOL = 2.0
#: 時刻容差（分鐘）。面板的分鐘數是取整的（實測第二份宣稱 5 分鐘 vs 真值 3.6 分鐘），
#: 宣稱時刻本身也只到分鐘 ⇒ 5 分鐘吸收取整與打字延遲，不吸收 3 小時級的錯。
MINUTE_TOL = 5.0
#: 判「翻頁」（reset）的 pct 下降容差。同 `quota_pace._ROLLOVER_EPS` 的理由：pct 是整數 pp。
ROLLOVER_EPS = 0.5
# 🔴 證據範圍由**落款自己的翻頁結構**界定，不由任何邊際常數：
# 起點 `S = 宣稱時刻 + 倒數 − 窗長` 把倒數的誤差整份繼承過來，於是 `S` 常常落到上一個
# 視窗裡去，把**上一窗**的高 pct 列拉進來當違規證據——那是把量測誤差算到宣稱者頭上。
# 假紅普查逐字量到這個懸崖（同一份判準碼、只換合成倒數的精度）：reset 反推括號 ≤10 分
# 時假紅 0/16，放寬到 ≤20 分跳成 22/38（57.9%）。已否決的補法是加一個固定邊際常數
# （試過 0／5／15／30 分：0～15 對那 22 筆零效果，30 才清掉，而 30 是湊出來的）。
# 採用的修法不需要常數：**證據一律限定在宣稱時刻所屬的那一個「觀測 run」內**（run＝落款
# 上沒有觀測到 pct 下降的一段），並且把「開啟該 run 的那一次下降」排除在 R2 的證據外
# ——那一次下降就是開啟本視窗的 reset，它落在 `(S, R)` 裡純粹是 `S` 估計誤差的產物。


def _aware(text: str) -> datetime | None:
    try:
        when = datetime.fromisoformat(str(text).strip())
    except (TypeError, ValueError):
        return None
    return when if when.tzinfo else None


def series(kind: str, text: str) -> list[tuple[datetime, float]]:
    """落款 jsonl → 該軸的 `[(時刻, pct)]`，按時間排序。壞列一律略過（取數不得掛掉）。"""
    out: list[tuple[datetime, float]] = []
    for line in str(text).splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            row = json.loads(stripped)
        except ValueError:
            continue
        pct = (row.get("pct") or {}).get(str(kind))
        when = _aware(row.get("ts") or "")
        if when is None or type(pct) not in (int, float):
            continue
        out.append((when, float(pct)))
    return sorted(out, key=lambda r: r[0])


def drops(rows: list[tuple[datetime, float]]) -> list[tuple]:
    """pct 下降處＝**觀測到**的翻頁。回 `[(t_前, pct_前, t_後, pct_後)]`。"""
    return [(a[0], a[1], b[0], b[1]) for a, b in zip(rows, rows[1:])
            if b[1] < a[1] - ROLLOVER_EPS]


def runs(rows: list[tuple[datetime, float]]) -> list[list[tuple[datetime, float]]]:
    """在 pct 下降處切段。每一段＝落款上「沒有觀測到翻頁」的一段連續讀數。"""
    grouped: list[list[tuple[datetime, float]]] = []
    for row in rows:
        if grouped and row[1] >= grouped[-1][-1][1] - ROLLOVER_EPS:
            grouped[-1].append(row)
        else:
            grouped.append([row])
    return grouped


def run_for(grouped: list, when: datetime) -> list | None:
    """包住 `when` 的那一段。落在最後一列**之後** ⇒ 用最後一段（其後沒有觀測到翻頁）；
    落在第一列**之前** ⇒ `None`（那一段的翻頁結構沒有任何觀測，不得假設）。"""
    for run in grouped:
        if run[0][0] <= when <= run[-1][0]:
            return run
    return grouped[-1] if grouped and when > grouped[-1][-1][0] else None


def window_pct_problems(run: list, when: datetime, pct: float,
                        start: datetime, end: datetime) -> tuple[list[str], int]:
    """R1。`run`＝宣稱時刻所屬的觀測 run。回 `(理由清單, 可用證據列數)`。"""
    inside = [r for r in run if start < r[0] < end]
    grace = timedelta(minutes=MINUTE_TOL)
    problems = []
    for t_row, p_row in inside:
        # 🔴 兩個方向的集合必須**互斥**。第一版把容差用來把兩邊各自**放寬**，於是距宣稱
        # 時刻 ±MINUTE_TOL 內的列同時落進「之前」與「之後」，任何超過 PCT_TOL 的差都會
        # 兩邊各叫一次——假紅普查逐字抓到（落款 22:32:38=6% 距宣稱 22:29:22 只有 3 分 16 秒，
        # 被判成「在宣稱時刻之前卻高於宣稱」）。容差的正解是把緊鄰的那一段**排除**在
        # 方向判定外（那段時間內 pct 真的可以動，而動多少需要燒率模型，本檔不做）。
        if t_row < when - grace and p_row > pct + PCT_TOL:
            problems.append(
                f"R1 隱含視窗內 pct 必須單調：落款 {t_row.isoformat()} = {p_row:g}% 在"
                f"宣稱時刻**之前**、卻高於宣稱的 {pct:g}%。該列落在宣稱自己隱含的視窗"
                f"({start.isoformat()}, {end.isoformat()}) 內 ⇒ 同一視窗內 pct 只能遞增，"
                f"不可能先到 {p_row:g}% 再回到 {pct:g}%")
        if t_row > when + grace and p_row < pct - PCT_TOL:
            problems.append(
                f"R1 隱含視窗內 pct 必須單調：落款 {t_row.isoformat()} = {p_row:g}% 在"
                f"宣稱時刻**之後**、卻低於宣稱的 {pct:g}%（同一視窗內不可能下降）")
    return problems, len(inside)


def window_drop_problems(seen: list, start: datetime, end: datetime,
                         run_start: datetime) -> list[str]:
    """R2。隱含視窗把一次觀測到的翻頁前後兩列都包在裡面 ⇒ 那不可能是同一個視窗。

    `run_start`＝宣稱所屬 run 的第一列時刻。**開啟該 run 的那一次下降**（後緣正好等於
    `run_start`）一律排除：它就是開啟本視窗的 reset，落在 `(S, R)` 內只反映 `S` 的誤差。
    """
    return [f"R2 隱含視窗不得包住一次觀測到的 reset：落款在 {t_a.isoformat()} = {p_a:g}% "
            f"→ {t_b.isoformat()} = {p_b:g}% 下降過（＝真的翻頁），而這兩列都落在宣稱"
            f"隱含的視窗 ({start.isoformat()}, {end.isoformat()}) 內"
            for t_a, p_a, t_b, p_b in seen
            if start < t_a and t_b < end and t_b != run_start]


def reconcile(kind: str, pct: float, minutes: float | None, when: datetime, *,
              text: str, window: float | None,
              rules: tuple[str, ...] = ("pct", "reset")) -> dict:
    """純函式判別。`rules` 只給紅綠自證用：兩條判準都是聯合式，拿掉任一半即失去鑑別力。"""
    out = {"verdict": UNDECIDABLE, "kind": kind, "rows": 0, "inside": 0,
           "reasons": [], "notes": []}
    rows = series(kind, text)
    out["rows"] = len(rows)
    if not rows:
        out["notes"] = [f"落款裡沒有 `{kind}` 這一軸的任何一列 ⇒ 無從比對"]
        return out
    if "reset" not in rules or minutes is None:
        out["notes"] = ["倒數缺席 ⇒ 沒有隱含視窗可用。只給 pct 與時刻時本檔結構上判不出"
                        "（『沒觀測到下降』不能證明『其間沒有 reset』，見檔頭）"]
        return out
    if window is None:
        out["notes"] = ["窗長解不出（桶名文法無解、也無同 reset 的鄰軸可繼承）⇒ 不猜"]
        return out
    end = when + timedelta(minutes=float(minutes))
    start = end - timedelta(minutes=float(window))
    out["window"] = (start.isoformat(), end.isoformat())
    problems: list[str] = []
    inside = 0
    run = run_for(runs(rows), when)
    if run is None:
        out["notes"] = [f"宣稱時刻 {when.isoformat()} 早於落款第一列 "
                        f"{rows[0][0].isoformat()} ⇒ 沒有可界定證據範圍的觀測 run"]
        return out
    if "pct" in rules:
        pct_problems, inside = window_pct_problems(run, when, float(pct), start, end)
        problems += pct_problems
        problems += window_drop_problems(drops(rows), start, end, run[0][0])
    out["inside"] = inside
    if problems:
        out["verdict"], out["reasons"] = INCOMPATIBLE, problems
        return out
    if "pct" not in rules:
        out["notes"] = ["pct 單調性被停用 ⇒ 隱含視窗算得出來但沒有東西可比對"]
        return out
    if inside == 0:
        out["notes"] = [f"宣稱隱含的視窗 ({start.isoformat()}, {end.isoformat()}) 內"
                        f"一列落款都沒有 ⇒ 落款在這一段是空的，判不出"]
        return out
    if when > rows[-1][0]:
        # 🔴 最常見的真實用法就是「現在有人貼了一份讀數」，而那個時刻在落款**最後一列
        # 之後** ⇒ 那一段完全沒有證據。此時 compatible 的意思只是「與已知的過去不衝突」，
        # 不是「是現值」。把這件事說出來，才不會讓一份 3 小時前的面板拿到一張通行證。
        out["notes"].append(
            f"宣稱時刻晚於落款最後一列 {rows[-1][0].isoformat()}（差 "
            f"{(when - rows[-1][0]).total_seconds() / 60:.0f} 分）⇒ 那一段沒有任何落款可比對。"
            "本判決只說「與已知的過去不衝突」，不等於「是現值」——要確認現值請重跑 --pace")
    out["verdict"] = COMPATIBLE
    out["reasons"] = [f"隱含視窗 ({start.isoformat()}, {end.isoformat()}) 內的 {inside} 列"
                      f"落款全部與宣稱的 {pct:g}% 單調相容，且其間沒有觀測到任何翻頁"
                      f"（容差 ±{PCT_TOL:g}pp／±{MINUTE_TOL:g} 分）"]
    return out


def resolve_window(kind: str, axes: list[tuple[str, str | None]] | None = None) -> float | None:
    """窗長：先桶名文法，解不出時由「同 `resets_at` 的鄰軸」繼承（`quota_pace.windows()`）。

    `axes`＝`[(kind, resets_at)]`，由呼叫端從活的額度快取取得。`session` 的文法無解
    （它不是自我描述的時長片語），今天靠與 `five_hour` 共用 `resets_at` 繼承到 300。
    """
    direct = quota_pace.window_minutes(kind)
    if direct is not None:
        return direct
    if not axes:
        return None
    for (name, _resets), win in zip(axes, quota_pace.windows(axes)):
        if name == kind:
            return win
    return None


def cache_axes(path) -> list[tuple[str, str | None]]:
    """額度快取 → `[(kind, resets_at)]`，**刻意繞過 TTL 新鮮度**。

    🔴 為什麼繞得過去：TTL 守的是「pct 這個讀數會過期」，而本函式取的是**軸別→窗長**的
    結構性對映（`session` 與 `five_hour` 共用同一個 `resets_at` ⇒ 同一條底層限制）。
    結構不隨分鐘變化，拿 `read_quota()` 會在 TTL 一過就整批退成「量不到」，於是 `session`
    （唯一一個桶名文法解不出窗長、也正是人會去讀的那一軸）結構上永遠 `undecidable`
    ——實測逐字命中。**只取 kind／resets_at 兩個欄位，一個 pct 都不讀**，所以不存在
    「拿舊 pct 當現值」的風險；讀不到就回空清單，窗長跟著解不出、判別回 undecidable。
    """
    import json as _json
    try:
        data = _json.loads(path.read_text(encoding="utf-8"))
        return [(str(a.get("kind") or ""), a.get("resets_at"))
                for a in data.get("axes") or [] if isinstance(a, dict)]
    except (OSError, ValueError, AttributeError):
        return []


def parse_claim(spec: str) -> tuple[str, float, float | None]:
    """`"session=2%,180m"` → `("session", 2.0, 180.0)`。倒數可省（那時一律 undecidable）。"""
    head, _, rest = str(spec).strip().partition("=")
    if not head.strip() or not rest.strip():
        raise ValueError("格式：<kind>=<pct>%[,<minutes>m]，例 session=2%,180m")
    parts = [p.strip() for p in rest.split(",") if p.strip()]
    pct = float(parts[0].rstrip("%").strip())
    minutes = float(parts[1].rstrip("mM").strip()) if len(parts) > 1 else None
    return head.strip(), pct, minutes


_ICON = {COMPATIBLE: "✅", INCOMPATIBLE: "🔴", UNDECIDABLE: "❔"}


def report(result: dict, when: datetime, window: float | None) -> str:
    """人看的一段。`undecidable` 一律印成「判不出」，絕不印成「通過」。"""
    win = f"{window:g} 分" if window is not None else "不明"
    lines = [f"{_ICON[result['verdict']]} reconcile={result['verdict']}  "
             f"kind={result['kind']}  宣稱於={when.isoformat()}  "
             f"落款列數={result['rows']}  隱含視窗內={result['inside']} 列  窗長={win}"]
    lines += [f"   · {why}" for why in result["reasons"]]
    lines += [f"   ? {why}" for why in result["notes"]]
    if result["verdict"] == INCOMPATIBLE:
        lines.append("   ⇒ 最常見的原因是**那份面板不是現值**（重讀一次面板即可分辨），"
                     "不是誰在說錯。本判別只回答「與落款相容嗎」。")
    if result["verdict"] == UNDECIDABLE:
        lines.append("   ⇒ 判不出 ≠ 相容。落款不足以支持任何一邊，別把它當成核對通過。")
    return "\n".join(lines) + "\n"


def reconcile_report(spec: str, when: datetime, *, ledger_text: str,
                     axes: list | None = None) -> tuple[str, str]:
    """CLI 用的一次到底：`(verdict, 一段可貼的文字)`。"""
    kind, pct, minutes = parse_claim(spec)
    win = resolve_window(kind, axes)
    result = reconcile(kind, pct, minutes, when, text=ledger_text, window=win)
    return result["verdict"], report(result, when, win)


def cli(spec: str, at: str | None) -> int:
    """`--reconcile` 的實作。住這裡而不住呼叫端：呼叫端是 `guardrail_cli` 分級的檔、
    本輪已在上限上，而這段 glue 的內聚對象是本檔的判準。

    `quota_gate` 刻意**延後 import**：本檔的判準是純函式（測試只需要一段落款文字），
    而 `quota_gate` 會把整條額度取數鏈帶進來——純路徑不該為 CLI 路徑付那份相依。

    🔴 rc 刻意**不**編碼三態判決：這是輔助判別、不是閘門。rc 帶判決會誘使呼叫端拿它當
    「使用者說錯了」的證明，而本檔只回答「與落款相容嗎」。rc≠0 只代表判準沒跑起來。
    """
    from datetime import datetime as _dt

    import quota_gate
    try:
        when = _dt.fromisoformat(at) if at else _dt.now().astimezone()
        if when.tzinfo is None:
            raise ValueError("--reconcile-at 必須帶 offset（不帶 offset 算 age 要猜時區）")
        text = quota_gate.burn_ledger_path().read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"❌ --reconcile 前置失敗：{exc}", file=sys.stderr)
        return 2
    axes = cache_axes(quota_gate.quota_cache_path())
    verdict, rendered = reconcile_report(spec, when, ledger_text=text, axes=axes)
    print(rendered, end="")
    return 0 if verdict else 2


# ── `--self-test`：合成注入紅綠自證（DEF-200-213④；體例照 `check_handoff_carriers.py`）。
# R100 §D-14 否決 scratchpad 版測試的理由①③，反例明文：不得讀 `os.environ[...]` 下標
# （零 env 依賴），不得在 import 期開機器本地檔（語料全合成、只在函式內組字）。
def _self_test() -> int:
    """紅綠自證：R1/R2 聯合判準＋三態不可折疊，全部打在合成落款上（不碰任何真檔）。"""
    fails: list[str] = []

    def expect(side: str, cond: bool, what: str) -> None:
        print(f"  {side}  {'PASS' if cond else 'FAIL'}  {what}")
        if not cond:
            fails.append(what)

    rows = [("10:00", 10), ("11:00", 30), ("12:00", 50), ("12:30", 2),
            ("13:00", 5), ("14:00", 40), ("15:00", 3), ("15:30", 6)]
    text = "\n".join(json.dumps({"ts": f"2026-08-23T{hm}:00+08:00",
                                 "pct": {"session": pct}}) for hm, pct in rows)
    when = lambda hm: datetime.fromisoformat(f"2026-08-23T{hm}:00+08:00")  # noqa: E731
    print("[self-test] R1/R2 聯合判準（合成落款 8 列、兩次觀測翻頁；窗長=300）")
    red1 = reconcile("session", 1.0, 240.0, when("13:30"), text=text, window=300.0)
    expect("RED", red1["verdict"] == INCOMPATIBLE
           and any("R1" in why for why in red1["reasons"]),
           "R1：隱含視窗內有早於宣稱且更高的落款列 ⇒ incompatible")
    red2 = reconcile("session", 7.0, 60.0, when("15:45"), text=text, window=300.0)
    expect("RED", red2["verdict"] == INCOMPATIBLE
           and any("R2" in why for why in red2["reasons"]),
           "R2：隱含視窗包住一次**非本 run 開頁**的觀測 reset ⇒ incompatible")
    green = reconcile("session", 4.0, 120.0, when("12:50"), text=text, window=300.0)
    expect("GREEN", green["verdict"] == COMPATIBLE and green["inside"] >= 1,
           "與落款單調相容、視窗內有證據列、開啟本 run 的那次下降被排除 ⇒ compatible")
    print("[self-test] 三態不可折疊（undecidable 不得折進任一邊）＋聯合式對照")
    for what, result in (
        ("倒數缺席 ⇒ undecidable（不猜）",
         reconcile("session", 4.0, None, when("12:50"), text=text, window=300.0)),
        ("窗長解不出 ⇒ undecidable（不猜）",
         reconcile("session", 4.0, 120.0, when("12:50"), text=text, window=None)),
        ("拿掉 pct 半邊 ⇒ 紅側樣本失去鑑別力（兩條判準是聯合式）",
         reconcile("session", 1.0, 240.0, when("13:30"), text=text, window=300.0,
                   rules=("reset",))),
    ):
        expect("GREEN", result["verdict"] == UNDECIDABLE, what)
    print(f"[self-test] {'❌ ' + str(len(fails)) + ' 項失敗' if fails else '✅ 全部通過'}")
    return 1 if fails else 0


if __name__ == "__main__":  # `--self-test` 是本檔唯一的直接執行入口（判準面走 import）。
    # 非 UTF-8 終端印 ✅/❌ 防崩潰（DEF-101-789 族）；走唯一實作而非就地 reconfigure——
    # `test_platform_utils_dedup.py` 的 per-tree 複本棘輪只准變少（落地當回合 6→7 實測紅）。
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import _stdio_utf8  # noqa: F401
    if sys.argv[1:] != ["--self-test"]:
        print("用法：python tools/lib/quota_reconcile.py --self-test", file=sys.stderr)
        sys.exit(2)
    sys.exit(_self_test())
