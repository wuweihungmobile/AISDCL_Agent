"""趕工戳記（ADR-XPLAT-004 §2.15 D2）：自帶到期的人工宣告，只關配速床；讀寫、疊入、痕跡與命令列。"""
# ─────────────────────────────────────────────────────────────────────────────
# WHY：配速床（`quota_pace_floor`）沒有環境變數形態的總開關——逃生口只有這張戳記。
#   形態是「有效期戳記」而非環境變數：到期即失效（讀取端判斷，無常駐程式），忘了關也不會永久放寬。
#   承載＝`quota_gate.policy_env()` 出口呼叫 `overlay()`，把有效戳記疊成
#   `AUTOSDD_QUOTA_PACE_RUSH_UNTIL`（epoch 秒），經 `load_policy` 進 `Policy.pace_rush_until`，
#   `decide()` 以 `now` 判有效。所有走 `policy_env()` 的消費端因此看到同一個 cap；
#   hook 每次觸發都重讀 ⇒ 已在跑的其他 session 下一次呼叫即生效。
# 🔴 fail-closed（較緊方向）：缺檔／壞 JSON／schema 不符／欄位缺或型別錯／naive 時刻／
#   epoch 與時刻不一致／有效期超過上限／無人窗口——一律當「無戳記」＝床照常套用。
#   任何一種誤判有效＝放寬，所以讀取端不寬容。
# 🔴 不引入 `os.replace`／`rename`（Windows 檔案鎖原語鎖）：
#   只用 `write_text`／`open(…,"a")`／`unlink`。
# 🔴 測試圍籬：戳記與痕跡一律落 `endurance_env.trace_dir()`（`AUTOSDD_TRACE_DIR` 可圍住），
#   不寫真實 home。
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import endurance_env
import quota_halt_marker
from quota_pace_floor import RUSH_MAX_SECONDS

SCHEMA = "autosdd.quota_rush/1"
STAMP_NAME = "quota_rush.json"
EVENTS_NAME = "autosdd_pace_floor.jsonl"
RUSH_KEY = "AUTOSDD_QUOTA_PACE_RUSH_UNTIL"
MIN_WHY_CHARS = 8
UNATTENDED_ENV = "AUTOSDD_UNATTENDED"
_USAGE_RC = 3
_EPOCH_TOL = 1.0
_USAGE = ("用法：sessionctl rush --hours <H> --why \"<WHY≥8字>\" [--sid <SID>]｜--off｜--status\n")


def _unattended(env) -> bool:
    """無人窗口判準的**唯一**家：發戳記、讀戳記、狀態文字、環境變數載體都問它。"""
    return bool(str(env.get(UNATTENDED_ENV, "")).strip())


def stamp_path() -> Path:
    return endurance_env.trace_dir() / STAMP_NAME


def _find_stamp():
    """讀取端**唯讀**定位（不 mkdir）：`policy_env()` 在 `--check`／`--pace` 這類唯讀查詢的熱路徑，
    不得像 `stamp_path()`（寫入端，`trace_dir()` 會建目錄）那樣憑空長出 `~/.autosdd/traces`
    （回歸鎖＝`PlannerCliTest::test_check_prints_usage_and_writes_nothing`）。
    只看**寫入端此刻會落腳的那一處**（`endurance_env.trace_dir_peek()`：與 `trace_dir()` 同一份
    判準、不建目錄）——主居所健康時不併讀系統暫存（暫存是任何本機行程都寫得進的面，
    DEF／審查 P3-3）；唯有主居所不可用、寫入端會退回暫存時才讀暫存。"""
    base = endurance_env.trace_dir_peek()[0]
    return base / STAMP_NAME if (base / STAMP_NAME).is_file() else None


def _events_path() -> Path:
    return endurance_env.trace_dir() / EVENTS_NAME


def _aware(text):
    """ISO 字串 → aware datetime；naive／解不出回 `None`。"""
    try:
        when = datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo is not None else None


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(float(value)) else None


def read_stamp(path=None):
    """讀戳記；任何結構異常回 `None`（fail-closed）。"""
    target = Path(path) if path else _find_stamp()
    if target is None:
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        return None
    if not all(isinstance(data.get(k), str) for k in ("issued_at", "until", "why", "sid")):
        return None
    if len(data["why"].strip()) < MIN_WHY_CHARS:  # 與寫入端 `issue` 同一條下限（手寫戳記不得繞過）
        return None
    epoch, hours = _number(data.get("until_epoch")), _number(data.get("hours"))
    issued, until = _aware(data["issued_at"]), _aware(data["until"])
    if epoch is None or hours is None or issued is None or until is None:
        return None
    if abs(until.timestamp() - epoch) > _EPOCH_TOL:
        return None
    if (until - issued).total_seconds() > RUSH_MAX_SECONDS + 1.0:
        return None
    return data


def active(now=None, env=None, path=None):
    """有效戳記（附 `left_minutes`）；無人窗口、無戳記、過期、超上限一律 `None`。"""
    env = os.environ if env is None else env
    if _unattended(env):
        return None
    stamp = read_stamp(path)
    if stamp is None:
        return None
    now = now or datetime.now().astimezone()
    left = float(stamp["until_epoch"]) - now.timestamp()
    if not 0.0 < left <= RUSH_MAX_SECONDS:
        return None
    return dict(stamp, left_minutes=left / 60.0)


def overlay(env, now=None, path=None) -> dict:
    """`env` 的複本；有效戳記且 `RUSH_KEY` 缺席／空白／≤0 ⇒ 疊入。例外一律吞掉（熱路徑）。
    無人窗口：不論載體（戳記或手設的 `RUSH_KEY`）一律無趕工——複本移除 `RUSH_KEY`（規格 D2）。"""
    out = dict(env)
    try:
        if _unattended(out):
            out.pop(RUSH_KEY, None)
            return out
        raw = str(out.get(RUSH_KEY, "")).strip()
        if raw:
            try:
                if float(raw) > 0:
                    return out
            except ValueError:
                return out  # 明示但畸形：交給 load_policy 出聲，不覆蓋操作者意圖
        stamp = active(now, env=out, path=path)
        if stamp is not None:
            out[RUSH_KEY] = str(stamp["until_epoch"])
    except Exception:  # noqa: BLE001 — 疊入失敗＝無戳記（較緊方向）
        return dict(env)
    return out


def log_event(event, path=None, **fields) -> bool:
    """追加一列單行 JSON 到痕跡檔；寫不進去回 `False` 不拋。"""
    try:
        row = json.dumps({"event": event, **fields}, ensure_ascii=False)
        with open(path or _events_path(), "a", encoding="utf-8", newline="\n") as handle:
            handle.write(row + "\n")
    except (OSError, TypeError, ValueError):
        return False
    return True


def log_floor(decision, now, path=None) -> bool:
    """床真的抬了水位才落一列 `pace_floor`（一次決策一列，取超線最多的那一軸）；其餘不寫。"""
    try:
        lifted = [f for f in decision.pace if f.state == "lifted"]
        if not lifted:
            return False
        top = max(lifted, key=lambda f: f.over_pp)
        return log_event("pace_floor", path, at=now.isoformat(), kind=top.kind, pct=top.pct,
                         minutes=top.minutes, allowed_pp=top.allowed_pp, level=top.level,
                         cap=decision.cap, band=decision.band)
    except Exception:  # noqa: BLE001 — 落款失敗不得拖垮 gate
        return False


_AUTO = object()


def issue(hours, why, sid="", now=None, env=None, path=None, account=_AUTO):
    """發戳記（覆寫舊戳記＝延長）。`(rc, 訊息)`：0 成功／2 拒絕（不寫檔）／1 檔案系統錯誤。
    `account`＝帳號指紋（QVD §7.3；缺＝讀額度快取最近一次的指紋；量不到寫 `null` 並出聲）。"""
    env = os.environ if env is None else env
    if _unattended(env):
        return 2, "拒絕：無人窗口無人可宣告趕工（AUTOSDD_UNATTENDED 有設）"
    try:
        span = float(hours)
    except (TypeError, ValueError):
        return 2, f"拒絕：hours={hours!r} 不是數字"
    if not math.isfinite(span) or not 0.0 < span <= RUSH_MAX_SECONDS / 3600.0:
        return 2, f"拒絕：hours 須 0 < H ≤ {RUSH_MAX_SECONDS / 3600.0:g}（實得 {hours!r}）"
    reason = str(why or "").strip()
    if len(reason) < MIN_WHY_CHARS:
        return 2, f"拒絕：why 去頭尾空白後須至少 {MIN_WHY_CHARS} 字（實得 {len(reason)} 字）"
    now = now or datetime.now().astimezone()
    until = now + timedelta(hours=span)
    sid = str(sid or env.get("CLAUDE_CODE_SESSION_ID", "") or "")
    if account is _AUTO:
        account = quota_halt_marker.cache_account()  # 指紋讀法單一家
    stamp = {"schema": SCHEMA, "issued_at": now.isoformat(), "until": until.isoformat(),
             "until_epoch": until.timestamp(), "hours": span, "why": reason, "sid": sid,
             "account": account or None}
    try:
        Path(path or stamp_path()).write_text(json.dumps(stamp, ensure_ascii=False),
                                              encoding="utf-8", newline="\n")
    except OSError as exc:
        return 1, f"戳記寫入失敗：{exc}"
    log_event("pace_rush_on", at=now.isoformat(), until=until.isoformat(), hours=span,
              why=reason, sid=sid)
    note = "" if account else "\n" + quota_halt_marker.unmeasured_account_note("趕工戳記").rstrip()
    left = int(span * 60)
    return 0, f"趕工戳記已發：到期 {until.isoformat()}（剩 {left} 分鐘）；配速床暫停{note}"


def revoke(now=None, path=None):
    """撤銷。有檔：刪除並落 `pace_rush_off`；無檔：rc 0、不落事件。"""
    target = Path(path) if path else _find_stamp()
    if target is None or not target.is_file():
        return 0, "無趕工戳記"
    try:
        target.unlink()
    except OSError as exc:
        return 1, f"戳記刪除失敗：{exc}"
    log_event("pace_rush_off", at=(now or datetime.now().astimezone()).isoformat(),
              reason="revoked")
    return 0, "趕工戳記已撤銷；配速床恢復"


def status_text(now=None, env=None, path=None) -> str:
    """有效／已過期／無戳記與 why（無戳記也是正常狀態）。"""
    stamp = read_stamp(path)
    if stamp is None:
        return "無趕工戳記（配速床照常套用）"
    live = active(now, env=env, path=path)
    if live is not None:
        return (f"趕工戳記有效：到期 {live['until']}（剩 {int(live['left_minutes'])} 分鐘）"
                f"，why={live['why']}")
    env = os.environ if env is None else env
    why = ("無人窗口一律忽略戳記" if _unattended(env) else "已過期")
    return f"趕工戳記無效（{why}）：到期 {stamp['until']}，why={stamp['why']}；配速床照常套用"


def _parse(argv):
    """`(選項 dict, 錯誤或 None)`。已知旗標：--hours／--why／--sid（帶值）、--off／--status。"""
    opts, rest = {}, list(argv)
    while rest:
        flag = rest.pop(0)
        if flag in ("--hours", "--why", "--sid") and rest:
            opts[flag] = rest.pop(0)
        elif flag in ("--off", "--status"):
            opts[flag] = True
        else:
            return opts, f"未知或缺值的旗標：{flag}"
    return opts, None


def cli(argv) -> int:
    """`sessionctl rush` 的實作：0 成功／2 拒絕／1 檔案系統錯誤／3 用法錯誤。"""
    opts, error = _parse(argv)
    off, status, hours = opts.get("--off"), opts.get("--status"), opts.get("--hours")
    bad = (error or not opts or (off and (hours or status or "--why" in opts))
           or (status and (hours or "--why" in opts)) or (not off and not status and (
               hours is None or "--why" not in opts)))
    if bad:
        sys.stderr.write(f"rush：用法錯誤{'：' + error if error else ''}\n{_USAGE}")
        return _USAGE_RC
    if off:
        rc, text = revoke()
    elif status:
        rc, text = 0, status_text()
    else:
        rc, text = issue(hours, opts["--why"], opts.get("--sid", ""))
    (sys.stdout if rc == 0 else sys.stderr).write(text + "\n")
    return rc
