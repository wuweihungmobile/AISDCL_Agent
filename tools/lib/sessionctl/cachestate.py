"""sessionctl 快取冷熱判準（純讀檔、不 spawn）：目標代理的 prompt cache 現在還熱不熱。

WHY：續一個冷掉的大上下文代理＝整份重寫快取（0.1× 讀變 1.25～2× 寫）；熱的續棒只付讀價、
比新代理便宜。判準取**證據**不取設定：尾端 256 KB 內任一筆 assistant usage 的
`cache_creation.ephemeral_1h_input_tokens > 0` ⇒ 1 小時壽命，否則 5 分鐘
（缺欄＝5 分鐘，較早判冷＝較嚴）。計時只看最後一筆**帶 usage 的 assistant 記錄**
（tool_result／user 記錄不重設快取計時器）。
量不到一律 fail-open（`cold=False`）：誤擋只差一步的代理，代價高於誤放。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import procstop

#: hook 判斷時刻早於模型實際送請求時刻的偏差補償（更早判冷＝更嚴）；常數、不開 env（避免放寬出口）。
CACHE_MARGIN_SECONDS = 30
TTL_SECONDS = {"5m": 300, "1h": 3600}
OVERRIDE_PREFIX = "續棒理由："  # 全形冒號
OVERRIDE_MIN_CHARS = 8


def cache_state(path, now: datetime | None = None) -> dict:
    """`{"tier": "5m"|"1h", "idle_s": float|None, "cold": bool}`；讀不到任何 assistant usage ⇒
    `{"tier": "5m", "idle_s": None, "cold": False}`，不拋。"""
    from . import roster  # noqa: PLC0415 — lazy：roster 與本檔同屬套件，避免頂層循環

    out = {"tier": "5m", "idle_s": None, "cold": False}
    try:
        last_at = None
        for rec in roster._records(Path(path), tail=True):
            use = roster._usage(rec)
            if use is None:
                continue
            made = use.get("cache_creation")
            h1 = made.get("ephemeral_1h_input_tokens") if isinstance(made, dict) else None
            if type(h1) is int and h1 > 0:
                out["tier"] = "1h"
            stamp = procstop.parse_iso(rec.get("timestamp"))
            if stamp is not None and (last_at is None or stamp >= last_at):
                last_at = stamp
        if last_at is None:
            return out
        now_ts = (now or datetime.now().astimezone()).timestamp()
        out["idle_s"] = now_ts - last_at
        out["cold"] = out["idle_s"] >= TTL_SECONDS[out["tier"]] - CACHE_MARGIN_SECONDS
    except Exception:  # noqa: BLE001 — 量不到不得單方面阻斷
        return {"tier": "5m", "idle_s": None, "cold": False}
    return out


def override_reason(message) -> str | None:
    """`message`（str）內 `續棒理由：` 之後取到行尾；strip 後 ≥ `OVERRIDE_MIN_CHARS` 字才回。"""
    if not isinstance(message, str) or OVERRIDE_PREFIX not in message:
        return None
    rest = message.split(OVERRIDE_PREFIX, 1)[1].splitlines()
    reason = rest[0].strip() if rest else ""
    return reason if len(reason) >= OVERRIDE_MIN_CHARS else None
