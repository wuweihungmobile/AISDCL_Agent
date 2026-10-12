"""清倉模式（BURN-DOWN）：操作者落款的授權疊層——載體、生效判準、逐軸放寬、出聲。"""
# ─────────────────────────────────────────────────────────────────────────────
# WHY 這一支檔存在（DEF-200-528；規範本體＝清倉增補檔〔Adopted〕，掌舵者對其 QB1~QB6 的
# 裁決見裁決記錄）
# ---------------------------------------------------------------------------
# 病：掌舵者明示「把快作廢的額度用掉」，而 `--pace` 仍把派工壓在 cap≤2——機制面沒有任何輸入
# 能表達「操作者要清倉」。實測（見證據檔）擋住它的不是 cap 階梯，而是**跨窗攤提**把 free 帶
# 的短窗水位抬成 prepare。缺的不是一個數字，是一個**授權事實的載體**：它不能是 Policy 欄位
# （那會把授權偽裝成門檻）、不能是 env 開關（沒有「誰」「何時」「哪個視窗」，且跨窗殘留）。
#
# 🔴 載體「三收」（QB3）：state 落款檔（持久目錄，活過重開機）＋ CLI 唯一寫入口（本檔
#   `--issue`）＋ env 只做 kill-switch（`AUTOSDD_QUOTA_BURNDOWN_OFF`，只准關）。
#   **載體不具防偽性質**——落款檔是磁碟上的 JSON，模型也寫得出來；它交付的是「可稽核／偽造
#   可對帳／失效可偵測」三件，不是「已驗證是人下的令」。
# 🔴 生效判準全部合取、fail-closed（`verdict`）：任一不成立 ⇒ 整段不套用 ⇒ 逐字退回今天的
#   行為。效期只綁被點名軸的下一次 reset（QB5，伺服器原字串；解不出＝拒絕武裝，寫入端與
#   消費端兩側都擋）。
#
# 🔴 放寬語意（逐軸，不是全域開關；聚合律／must-finish／model_hint 一字不改，只改逐軸輸入）：
#   Q-same（增補檔 §4.1＋QB6）＝被點名軸，或 `resets_at` **字串全等**的同窗鄰軸；享 BD-1
#     （視野檔位夾在 mid＝乘數地板 1.0，收回 far／none 的減速，**不送 near 的加速**）與 BD-2′。
#   Q-cross（主控裁決；增補檔 BD-2 對立案情境「入憲了但治不到」的補洞）＝進 cap gate 的短窗軸，
#     且本次攤提的長窗供給軸 `Amort.total_kind` 是 Q-same：該軸餵給 `pct_band` 的水位改用原始
#     pct（攤提上調暫停）。理由：攤提存在的唯一目的是保護長窗軸；操作者點名那條長窗軸清倉＝
#     明示解除該保護。Q-cross 不享 BD-1。
#   四條底線寫成**資格的合取項**（`_eligible`）：halt 帶不放寬（①）、FALLBACK 永不（②，連
#     點名也不行）、MODEL_SCOPED 永不（③＋QB4）、reset 分鐘解不出或已過期不放寬（時鐘偏移
#     不得換來放寬）。
#   上限夾層（QB1，`_merge`）：逐軸 `cap = max(原 cap, min(放寬後 cap, cap_notice))`、`rec`
#     同法再夾回 cap；原 cap 為 None 的格逐格不動；**只准往上、不得用 ceil 去夾原值**
#     （增補檔 §0.2 的實測反例：free×near 的 rec 16→8 會損傷加速錨點）。
# 🔴 為何 BD-1 動視野 label 而不是只改逐軸 `recommended`：`_cap_for`／`_rec_for`／`_pace_of`／
#   `_rec_of_gate` 對 label 單調，夾住 label 同時夾住 cap 與 rec，聚合出來的
#   `recommended_fanout`（`--pace` 的「現在可派幾個」）才真的放寬；只改逐軸欄位，聚合值原地
#   不動。BD-2′ 動的是 `band_inputs()` 的遮罩。`amortize()` 取數面一個字沒動。
#
# 🔴 誠實劃界：
#   · 放寬後的 cap 仍要過 `quota_stability`（PRD §4.2.4：增加方向每次至多 +1、距上次變更
#     ≥ 300 秒）——落款後穩定值會逐步爬升，不是一步到位；收緊（過期／撤銷）一步到位。
#   · 「同窗鄰軸」取字串全等＝零容差：實測 `weekly_all` 與 `weekly_scoped` 的 resets_at 差
#     微秒（`seven_day` 與 `weekly_all` 全等），伺服器若對同窗軸吐出微秒差，鄰軸判定會靜默
#     不觸發（保守側；增補檔 §9-5 觀察項）。
#   · `--pace` 的清倉全文只印**一行**（`full_line`）：標題行只帶 `Applied.mark`、逐軸那一行用
#     `describe(burndown=False)`；hook 阻斷訊息走 `describe()` 預設（那條路徑沒有別處可看全文）。
#   · `--pace` 與派工 hook 以外的 `decide()` 呼叫端（`draining()`／接力／哨兵／簡報）刻意不帶
#     授權：它們答的是壓縮與續航，不是派工上限。決策事件列只由 `--pace` 寫（hook 熱路徑不落檔）。
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import endurance_env
import quota_pace as W
import quota_policy as Q

#: env kill-switch（只准關、不准開；註冊在 `quota_policy_env.ENV_SPEC` 的逃生口區）。
OFF_ENV = "AUTOSDD_QUOTA_BURNDOWN_OFF"
DIRECTIVE_NAME = "autosdd_burndown_directive.json"
EVENTS_NAME = "autosdd_burndown_events.jsonl"
SCHEMA = "autosdd.burndown/1"
#: 落款必填欄（增補檔 §3.2 六欄＋id）：缺任一欄、前五欄非空字串、後兩欄非 list＝不合格落款。
FIELDS = ("id", "directive_verbatim", "issued_at", "axis_kind", "until_resets_at",
          "core_signature", "readings_at_issue")
NOTE_HONESTY = ("載體不具防偽性質：落款只讓事後可稽核、偽造可對帳、失效可偵測，"
                "不代表「已驗證是人下的令」。")
#: 清倉生效時，節流期程行的「隨 reset 逼近才放寬／改做不吃額度的工作」與降級建議行會與下令
#: 意圖相反：渲染端（`quota_messages`）改取這兩句；文字只住本檔。
NOTE_HORIZON = "清倉模式生效：cap 不隨 reset 逼近再放寬（遠期減速已由 BD-1 收回）"
NOTE_HINT = "（清倉模式下僅供參考，不影響 cap）"
_INF = float("inf")


class Applied(NamedTuple):
    """一次決策裡清倉授權的落地結果（`Decision.burndown`）；`effect`＝relaxed／inert。

    `text`＝全文（原值→放寬值、未放寬軸與具名理由）；`mark`＝標題行用的短標記（≤40 字）。
    """

    id: str
    effect: str
    text: str
    mark: str
    relaxed: tuple = ()  # 本次真的被放寬的軸 kind（期程行替代句只對 binding ∈ 此集合為真）


def directive_path() -> Path:
    """落款檔：持久目錄（`endurance_env.trace_dir()`），不是暫存——效期是 reset 視窗不是行程壽命。"""
    return endurance_env.trace_dir() / DIRECTIVE_NAME


def read_directive(path: Path | None = None) -> dict | None:
    """讀落款；缺檔／壞 JSON／schema 不符／缺欄一律 `None`（fail-closed）。"""
    try:
        data = json.loads((path or directive_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    ok = isinstance(data, dict) and data.get("schema") == SCHEMA
    ok = ok and all(isinstance(data.get(k), str) and data[k].strip() for k in FIELDS[:5])
    return data if ok and all(isinstance(data.get(k), list) for k in FIELDS[5:]) else None


def _left(until: object, now: datetime) -> float | None:
    """距效期終點幾分鐘；解不出／naive／已過期（含恰好相等）一律 `None`（拒絕武裝）。"""
    minutes, note = W.expiry_of(until, now)
    return minutes if note == W.EXPIRY_FUTURE and minutes is not None and minutes > 0 else None


def verdict(d, state, now, env, signature_of, full: bool = False) -> list:
    """增補檔 §3.3 生效判準逐項 `(標籤, 成立?)`；`full=False` 時第一個不成立即止。

    `signature_of`＝`quota_gate.core_signature`（傳函式而不是值：沒有落款時一次都不會被叫；
    它在帳號指紋缺席時會出聲，不得因為「查有沒有落款」就多出一則降級訊息）。
    """
    kind = str(d["axis_kind"]) if d else ""
    steps = (
        ("落款檔存在且六欄齊全", lambda: d is not None),
        (f"{OFF_ENV} 未設", lambda: not str(env.get(OFF_ENV, "")).strip()),
        ("被點名軸不是 fallback／model-scoped（底線②③，QB4）",
         lambda: kind not in Q.FALLBACK_KINDS and kind not in Q.MODEL_SCOPED_KINDS),
        ("方案指紋與落款相同", lambda: tuple(d["core_signature"]) == tuple(signature_of(state))),
        ("被點名軸仍在本次讀數", lambda: any(a.kind == kind for a in state.axes)),
        ("now < until_resets_at（解得出且未過期）",
         lambda: _left(d["until_resets_at"], now) is not None),
    )
    out = []
    for label, test in steps:
        try:
            ok = bool(test())
        except Exception:  # noqa: BLE001 — 解不出就是不成立（fail-closed），不得拋進決策路徑
            ok = False
        out.append((label, ok))
        if not ok and not full:
            break
    return out


def _eligible(a: Q.Axis, minutes: float | None, p: Q.Policy) -> bool:
    """四條底線＋時鐘的合取（Q-same／Q-cross 共同前置）；`minutes`＝帶號分鐘，`None`＝解不出。"""
    return (a.kind not in Q.FALLBACK_KINDS and a.kind not in Q.MODEL_SCOPED_KINDS
            and 0.0 <= a.pct < p.halt_pct and minutes is not None and minutes >= 0)


def _why(b: Q.AxisReading, minutes: float | None, same: bool, held: bool, amort,
         p: Q.Policy) -> str:
    """未放寬的具名理由（每一句都必為真）：「授權在但結構上沒生效」與「沒有授權」要分得開。

    `b`＝這一軸無授權時的讀數、`same`／`held`＝Q-same（BD-1）／Q-cross（BD-2′）遮罩、`amort`＝本次攤提。
    """
    a = b.axis
    if a.kind in Q.MODEL_SCOPED_KINDS:
        return "model-scoped 不納入"
    if a.kind in Q.FALLBACK_KINDS:
        return "fallback 不納入"
    if not 0.0 <= a.pct < p.halt_pct:
        return "halt 帶或水位不合法，不放寬"
    if minutes is None or minutes < 0:
        return "reset 時刻不明或已過期，不放寬"
    if W.NOTE_AMORT in b.note and not held:  # 本軸正被攤提抬高，而供給軸沒有資格被暫停
        supply = amort.total_kind if amort else "?"
        return f"攤提供給軸 kind={supply} 不 qualifying（model-scoped／fallback／不同窗）"
    if same:  # Q-same 軸只吃 BD-1：不是 far 就沒有遠期減速可收回
        return "視野已不在 far，無遠期減速可收回"
    if held:
        return "攤提在此帶未收緊（無可放寬）"
    return "本軸無攤提上調可暫停（Q-cross 不享視野地板）"


def _merge(b: Q.AxisReading, n: Q.AxisReading, on: bool, p: Q.Policy) -> Q.AxisReading:
    """上限夾層（QB1）：`b`＝今天的逐軸讀數、`n`＝放寬後的自然值；只准往上，不得用 ceil 夾原值。"""
    if not on:
        return b
    top = _INF if n.cap is None else n.cap
    cap = b.cap if b.cap is None else max(b.cap, min(top, p.cap_notice))
    rec = max(b.recommended, min(n.recommended, p.cap_notice))
    return b._replace(band=n.band, horizon=n.horizon, cap=cap, note=n.note,
                      recommended=rec if cap is None else min(rec, cap))


class Burn(NamedTuple):
    """已驗證生效的清倉授權（`active()` 的產物）；方法吃 `quota_policy` 的型別，反向不 import。"""

    id: str
    issued_at: str
    axis_kind: str
    until: str
    left: float
    named_resets_at: str | None

    def masks(self, state, deltas, ratio, ratio_note, p, active_model) -> tuple:
        """`(floor, hold, amort)`：Q-same（BD-1）／Q-cross（BD-2′攤提暫停）逐軸遮罩＋本次攤提。"""
        axes = state.axes
        ok = tuple(_eligible(a, d[0], p) and Q._in_cap_gate(
            Q.AxisReading(a, "", "", None, 0, None, ""), active_model)
            for a, d in zip(axes, deltas))
        same = tuple(o and (a.kind == self.axis_kind or (
            bool(a.resets_at) and a.resets_at == self.named_resets_at))
            for a, o in zip(axes, ok))
        amort = W.amort_for(Q._rows(state), deltas, ratio, ratio_note,
                            Q._amort_skip(state, active_model))
        named = any(s and a.kind == self.axis_kind for a, s in zip(axes, same))
        total = amort is not None and any(
            s and a.kind == amort.total_kind for a, s in zip(axes, same))
        return same, tuple(named and total and o for o in ok), amort

    def apply(self, state, now, p, ratio, ratio_note, active_model, base) -> tuple:
        """`(放寬後的逐軸讀數, Applied)`；`base`＝無授權時的 `axes_of`（`decide()` 本來就算過）。"""
        deltas = tuple(Q._delta_minutes(a.resets_at, now, state.measured_at) for a in state.axes)
        floor, hold, amort = self.masks(state, deltas, ratio, ratio_note, p, active_model)
        natural = Q.axes_of(state, now, p, ratio, ratio_note, active_model, relax=(floor, hold))
        out = tuple(_merge(b, n, f or h, p) for b, n, f, h in zip(base, natural, floor, hold))
        moved, kept = [], []
        for b, o, f, h, d in zip(base, out, floor, hold, deltas):
            if (b.band, b.cap, b.recommended) == (o.band, o.cap, o.recommended):
                kept.append(f"kind={b.axis.kind}（{_why(b, d[0], f, h, amort, p)}）")
                continue
            band = f" band {b.band}→{o.band}" if b.band != o.band else ""
            moved.append(f"kind={b.axis.kind}{band} cap {b.cap}→{o.cap} "
                         f"rec {b.recommended}→{o.recommended}")
        head = (f"｜🔥清倉模式生效中（落款 {self.id}，發令 {self.issued_at}，"
                f"作用至 kind={self.axis_kind} reset {self.until}；效期剩 {int(self.left)} 分鐘／"
                f"must-finish 門檻 {p.wrap_minutes:g} 分鐘）")
        mark = f"｜🔥清倉 {self.id}：放寬 {len(moved)} 軸／未放寬 {len(kept)} 軸"
        rest = "；未放寬：" + "、".join(kept) if kept else ""
        text = head + ("⇒ 本次放寬：" + "、".join(moved) + rest if moved
                       else "⇒ 本次未放寬任何軸：" + "、".join(kept))
        relaxed = tuple(b.axis.kind for b, o in zip(base, out)
                        if (b.band, b.cap, b.recommended) != (o.band, o.cap, o.recommended))
        return out, Applied(self.id, "relaxed" if moved else "inert", text, mark, relaxed)


def active(state, now, env, signature_of, path: Path | None = None) -> Burn | None:
    """生效中的清倉授權或 `None`。不拋例外：任何不確定一律退回無授權（放寬方向唯一的判準）。"""
    try:
        if str(env.get(OFF_ENV, "")).strip():
            return None
        d = read_directive(path)
        if not all(ok for _label, ok in verdict(d, state, now, env, signature_of)):
            return None
        named = next(a for a in state.axes if a.kind == d["axis_kind"])
        return Burn(str(d["id"]), str(d["issued_at"]), named.kind, str(d["until_resets_at"]),
                    float(_left(d["until_resets_at"], now)), named.resets_at)
    except Exception:  # noqa: BLE001 — fail-closed：授權路徑絕不能成為決策路徑的故障源
        return None


def full_line(decision) -> str:
    """`--pace` 的清倉全文段（獨立一行、只印一次；標題行只帶 `Applied.mark`）。無授權＝空字串。"""
    return f"  {decision.burndown.text.lstrip('｜')}\n" if decision.burndown else ""


def log_decision(decision, now: datetime, path: Path | None = None) -> bool:
    """增補檔 §6.3 兩個計數器的 JSONL 等價物：授權在場的每次 `--pace` 決策 append 一列。"""
    applied = decision.burndown
    if not applied:
        return False
    # 🔴 欄名帶 `decided_`：這是 `decide()` 原值，**早於** `quota_stability` 穩定化（≠標題行 cap）。
    row = {"ts": now.isoformat(), "bd": applied.id, "effect": applied.effect,
           "decided_cap": decision.cap, "decided_rec": decision.recommended_fanout}
    try:
        with (path or endurance_env.trace_dir() / EVENTS_NAME).open(
                "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        return False
    return True


# ── CLI（落款唯一寫入口；零網路：只讀 `quota_meter` 的快取檔，絕不 refresh）─────────────────
def _now() -> datetime:
    return datetime.now().astimezone()


def issue(kind: str, text: str, now: datetime | None = None, cache: Path | None = None,
          path: Path | None = None) -> tuple:
    """`--issue`：讀快取 → 驗 → 落款。回 `(rc, 訊息)`；任何拒絕都**不落檔**（BD-7）。

    快取超過 TTL 仍可落款（設計上刻意，不改行為）：`resets_at` 在視窗內不變，reset 之後舊
    `until` 已在過去 ⇒ 落款立即失效（fail-closed）；逾 TTL 時訊息多一句警示（落款以快取內的
    `resets_at` 為準）。
    """
    import quota_gate  # noqa: PLC0415 — 熱路徑上的 quota_gate 反向 import 本檔，只能延後到呼叫時
    import quota_meter  # noqa: PLC0415

    now = now or _now()
    if kind in Q.FALLBACK_KINDS or kind in Q.MODEL_SCOPED_KINDS:
        return 1, f"拒絕：kind={kind} 屬付費保險軸或模型分軌軸（底線②③；QB4：指令不得點名）"
    if not (text or "").strip():
        return 1, "拒絕：--directive 為空（指令逐字原文是落款欄位之一）"
    data = quota_meter.read_cache(cache)
    measured = quota_gate._aware(data.get("measured_at")) if data else None
    if measured is None:
        return 1, "拒絕：額度快取缺席或不合 schema（本指令零網路、不補量；先跑 --pace 讓快取就位）"
    # 以「量測當下」當 now 讀：過期的快取仍讀得出它自己的軸（resets_at 在視窗內不變）。
    state = quota_gate.read_quota(measured, cache)
    named = next((a for a in state.axes if a.kind == kind), None)
    if named is None:
        have = "、".join(a.kind for a in state.axes) or f"無（{state.reason}）"
        return 1, f"拒絕：快取沒有 kind={kind} 這一軸（現有：{have}）"
    left, note = W.expiry_of(named.resets_at, now, state.measured_at)
    if left is None or left <= 0 or note:
        return 1, (f"拒絕武裝：kind={kind} 的 resets_at={named.resets_at!r} "
                   f"解不出或已過期（{note or 'missing'}）")
    issued = now.isoformat()
    digest = hashlib.sha256("|".join((issued, kind, named.resets_at, text)).encode("utf-8"))
    record = {"schema": SCHEMA, "id": digest.hexdigest()[:10], "directive_verbatim": text,
              "issued_at": issued, "axis_kind": kind, "until_resets_at": named.resets_at,
              "core_signature": list(quota_gate.core_signature(state)),
              "readings_at_issue": [[a.kind, a.pct, a.resets_at] for a in state.axes]}
    target = path or directive_path()
    old = read_directive(target)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    except OSError as exc:
        return 1, f"拒絕：落款寫不進去（{target}：{exc}）"
    over = f"（覆蓋舊落款 {old['id']}）" if old else ""
    age = int((now - measured).total_seconds())
    warn = (f"\n⚠️ 快取已逾 TTL（{age} 秒），落款以快取內的 resets_at 為準"
            if age > quota_gate.QUOTA_CACHE_TTL_SECONDS else "")
    return 0, (f"已落款 {record['id']}{over}：kind={kind} 作用至 reset {named.resets_at}"
               f"（距今 {int(left)} 分鐘）；檔案 {target}{warn}\n{NOTE_HONESTY}")


def status(now: datetime | None = None, env=None, path: Path | None = None,
           model: str | None = None) -> tuple:
    """`--status`：生效判準逐項 ✓／✗，生效時再印「這一刻會放寬什麼」。rc＝0 生效、1 不生效。"""
    import quota_gate  # noqa: PLC0415

    now = now or _now()
    env = quota_gate.policy_env() if env is None else env
    d = read_directive(path)
    state = quota_gate.read_quota(now)
    steps = verdict(d, state, now, env, quota_gate.core_signature, full=True)
    if d is None:
        steps = steps[:1]  # 沒有落款時，後面各項無從判起，只留「落款檔存在」那一項
    lines = [f"清倉授權：落款 {d['id']}（發令 {d['issued_at']}；kind={d['axis_kind']} 作用至 "
             f"reset {d['until_resets_at']}）\n指令逐字：{d['directive_verbatim']}"
             if d else "清倉授權：沒有有效落款"]
    lines += [f"  {'✓' if ok else '✗'} {label}" for label, ok in steps]
    if not state.usable():
        lines.append(f"  （本次額度讀數不可用：{state.reason}；先跑 --pace 讓快取就位）")
    burn = active(state, now, env, quota_gate.core_signature, path)
    if burn is not None:
        ratio, ratio_note, _plan = quota_gate.burn_ratio(state)
        decision = Q.decide(state, now, Q.load_policy(env)[0], ratio, ratio_note,
                            active_model=model, burndown=burn)
        lines.append("  " + decision.burndown.text.lstrip("｜"))
    return (0 if burn is not None else 1), "\n".join(lines + [NOTE_HONESTY])


def revoke(path: Path | None = None) -> tuple:
    """`--revoke`：刪落款檔（沒有也算成功）。撤銷＝收緊方向，一步到位。"""
    target = path or directive_path()
    old = read_directive(target)
    try:
        target.unlink(missing_ok=True)
    except OSError as exc:
        return 1, f"撤銷失敗（{target}：{exc}）"
    return 0, (f"已撤銷清倉落款 {old['id']}" if old else "沒有有效落款可撤銷（檔案已確保不存在）")


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="quota_burndown.py", description="清倉模式（BURN-DOWN）落款唯一寫入口；零網路。")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--issue", metavar="AXIS_KIND", help="落款：點名一條進 cap gate 的訂閱軸")
    mode.add_argument("--status", action="store_true", help="判準逐項與會放寬什麼（rc 0＝生效）")
    mode.add_argument("--revoke", action="store_true", help="撤銷落款")
    ap.add_argument("--directive", default="", help="--issue 必填：掌舵者指令逐字原文")
    ap.add_argument("--model", default=None, help="--status 用：目標模型（決定分軌軸成員資格）")
    args = ap.parse_args(argv)
    if args.issue is not None:
        if not args.directive.strip():
            ap.error('--issue 必須帶 --directive "<指令逐字>"')
        rc, text = issue(args.issue, args.directive)
    elif args.status:
        rc, text = status(model=args.model)
    else:
        rc, text = revoke()
    print(text)
    return rc


if __name__ == "__main__":  # pragma: no cover
    # 本檔的 CLI 印中文：非 UTF-8 locale 下 stdout 直接 UnicodeEncodeError（同 `quota_policy`）。
    from platform_utils import init_utf8_streams

    init_utf8_streams()
    raise SystemExit(main(sys.argv[1:]))
