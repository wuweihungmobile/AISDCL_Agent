"""換帳號偵測與舊帳號標記作廢（QVD §7；PRD §4.1.7 R-4.1.7-1～6；TCS REQ-AP-AC-01～04）。

立案（暴露證據）：2026-11-26 11:39 單一判決讀到舊帳號殘留、無帳號欄的 halt 標記
（`halt_406454ea-….json`，寫於 11-24 21:32:50，早於 /login 21:36:47），新帳號 weekly 77% 卻判
`HALT_WEEKLY … cap=0`，派工閘死鎖。本檔讓「換帳號後舊標記仍當輸入」機械地不再發生：

· 觸發器（只負責「該重量了」，R-4.1.7-2）：T① 憑證檔 (mtime_ns, size) 與上次記錄不同（macOS 缺席，
  照實出聲一次）；T② 逐字稿自上次位移後出現 `/login` 指令記錄（增量讀、記 byte offset）；T③ 補量
  到的帳號指紋與上次不同（`reconcile` 內判）。成立 ⇒ 記 `pending`（事件時刻），讀數早於它 ⇒ 呼叫端
  （`ruling_io.gather`）在紅線 1 的 TTL 名額內補量一次。觸發器本身**從不**作廢任何標記（R-4.1.7-3）。
· 判定與作廢（`reconcile`）：以**這一次量到**的 `state.account_key` 為權威，逐個持久標記交
  `quota_ruling.marker_disposition`（門檻比較只住判決家）；`void` ⇒ 改名 `.void-<ts>` 保留史料、
  落 `account_switch` 痕跡、同一對 old→new 只出聲一次；`backfill` ⇒ 補寫 `account`。park 標記不在
  本流程（沿用 `parkprobe.account_changed` 提前恢復，R-4.1.7-4）。
· 狀態檔 `trace_dir()/acct_probe.json`（測試圍籬 `AUTOSDD_TRACE_DIR` 可攔）。

本檔只做 I/O 與事件判讀，不讀額度快取、不比門檻（單一判讀家，QVD §3.5.3）。不偵測、不建議、不觸發
換帳號（§7.4）。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import endurance_env
import quota_halt_marker
import quota_ruling as QR
import quota_rush

from . import switch

PROBE_NAME = "acct_probe.json"
LOGIN_TAG = "<command-name>/login</command-name>"
_MAX_OFFSETS = 64  # 逐字稿位移表上限（舊 sid 先汰除）
_MAX_VOICED = 32


def probe_path(*, write: bool = False) -> Path:
    root = endurance_env.trace_dir() if write else endurance_env.trace_dir_peek()[0]
    return root / PROBE_NAME


def load_probe() -> dict:
    try:
        data = json.loads(probe_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_probe(data: dict) -> bool:
    try:
        probe_path(write=True).write_text(json.dumps(data, ensure_ascii=False),
                                          encoding="utf-8", newline="\n")
    except OSError:
        return False
    return True


def _aware(raw) -> datetime | None:
    try:
        when = datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo is not None else None


def _sec(when: datetime) -> str:
    """事件時刻截到秒（快取 `measured_at` 也截到秒；同一秒內的補量視為晚於事件）。"""
    return when.replace(microsecond=0).isoformat()


def credentials_path() -> Path:
    from platform_utils import claude_home  # noqa: PLC0415 — 尊重 CLAUDE_CONFIG_DIR（同 quota_meter）

    return claude_home() / ".credentials.json"


def cred_sig(path: Path) -> list | None:
    try:
        st = Path(path).stat()
    except OSError:
        return None
    return [st.st_mtime_ns, st.st_size]


def scan_login(transcript: Path, offset: int) -> tuple[datetime | None, int]:
    """自 `offset` 起增量讀逐字稿（只讀完整行）；回 `(最後一筆 /login 記錄時刻｜None, 新 offset)`。
    只認主鏈 `type=user`、`content` 為字串且以 `<command-name>/login</command-name>` 開頭者（引用
    這個字面的對話、工具結果、api-request-blob 不算）。檔變短（輪替）⇒ 從 0 重讀。"""
    try:
        with Path(transcript).open("rb") as handle:
            size = handle.seek(0, 2)
            start = offset if 0 <= offset <= size else 0
            handle.seek(start)
            chunk = handle.read()
    except OSError:
        return None, offset
    end = chunk.rfind(b"\n") + 1
    seen = None
    tag = LOGIN_TAG.encode()
    for raw in chunk[:end].splitlines():
        if tag not in raw:
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        msg = rec.get("message") if isinstance(rec, dict) else None
        body = msg.get("content") if isinstance(msg, dict) else None
        if (rec.get("type") == "user" and not rec.get("isSidechain") and isinstance(body, str)
                and body.lstrip().startswith(LOGIN_TAG)):
            seen = _aware(rec.get("timestamp")) or seen
    return seen, start + end


def tick(sid: str, transcript, now: datetime | None = None, *,
         platform: str | None = None) -> tuple[datetime | None, list[str]]:
    """T①／T② 檢查（零 API）：回 `(pending 事件時刻｜None, 本次新成立的觸發器)`。
    首次看到憑證檔只記基準、不觸發（無從比較）；逐字稿從 0 起讀（首見的 /login 觸發一次補量，
    安全方向）。只在狀態有變時寫檔。"""
    now = now or datetime.now().astimezone()
    probe, changed, fired, events = load_probe(), False, [], []
    if (platform or sys.platform) == "darwin":
        if not probe.get("t1_absent_said"):
            sys.stderr.write("ℹ️ 換帳號觸發器 T①（憑證檔時刻）在 macOS 缺席（憑證在 Keychain）"
                             "⇒ 只靠 T②（逐字稿 /login）與 T③（指紋變化）\n")
            probe["t1_absent_said"], changed = True, True
    else:
        path = credentials_path()
        sig, old = cred_sig(path), probe.get("cred")
        if sig is not None and sig != old:
            if old is not None:
                fired.append("T1")
                events.append(datetime.fromtimestamp(sig[0] / 1e9).astimezone())
            probe["cred"], changed = sig, True
    if sid and transcript is not None:
        offsets = probe.setdefault("offsets", {})
        seen, new = scan_login(Path(transcript), int(offsets.get(sid, 0) or 0))
        if new != offsets.get(sid):
            offsets.pop(sid, None)
            offsets[sid] = new
            while len(offsets) > _MAX_OFFSETS:
                offsets.pop(next(iter(offsets)))
            changed = True
        if seen is not None:
            fired.append("T2")
            events.append(seen)
    if fired:
        when = max(events + [p for p in (_aware(probe.get("pending")),) if p])
        probe.update(pending=_sec(min(when, now)), trigger=fired[-1])
        changed = True
    if changed:
        save_probe(probe)
    return _aware(probe.get("pending")), fired


def needs_remeasure(state, pending: datetime | None) -> bool:
    """觸發器成立而手上讀數量於事件之前 ⇒ 該補量（呼叫端仍受 TTL 名額節流，紅線 1）。"""
    if pending is None or not state.usable():
        return False
    measured = _aware(getattr(state, "measured_at", None))
    return measured is None or measured < pending


def _void(path: Path, now: datetime) -> Path | None:
    target = path.with_name(f"{path.stem}.void-{now.strftime('%Y%m%dT%H%M%S%z')}{path.suffix}")
    try:
        path.rename(target)  # Windows 被開著＝PermissionError（OSError）⇒ 本次不作廢、下次再判
    except OSError:
        return None
    return target


def _backfill(path: Path, data: dict, acct: str) -> None:
    try:
        path.write_text(json.dumps({**data, "account": acct}, ensure_ascii=False),
                        encoding="utf-8", newline="\n")
    except OSError:
        pass


def reconcile(sid: str, state, policy, now: datetime, *, halt_marker=None) -> int:
    """QVD §7.2：以本次讀數的帳號指紋判 halt 標記與趕工戳記；回本次作廢數（判決行附「已作廢 n 個」）。
    `halt_marker`＝呼叫端（判決家 `compose`）已讀到的標記內容。另結 T③ 與 pending。"""
    acct = getattr(state, "account_key", None) or None
    items = []
    if sid and isinstance(halt_marker, dict):
        items.append((quota_halt_marker.halt_marker_path(sid), halt_marker))
    stamp_at = quota_rush._find_stamp()  # noqa: SLF001 — 唯讀定位（不 mkdir），同一份判準
    stamp = quota_rush.read_stamp(stamp_at) if stamp_at else None
    if stamp:
        items.append((stamp_at, stamp))
    voided, olds = [], []
    for path, data in items:
        how = QR.marker_disposition(data, acct, state, policy, now)
        if how == QR.VOID and (target := _void(path, now)) is not None:
            voided.append(target.name)
            olds.append(data.get("account") or "legacy")
        elif how == QR.BACKFILL and acct:
            _backfill(path, data, acct)
    probe = load_probe()
    changed, last = False, probe.get("account")
    trigger = probe.get("trigger") or ""
    if acct and acct != last:
        trigger = trigger or ("T3" if last else "")
        probe["account"], changed = acct, True
    pending, measured = _aware(probe.get("pending")), _aware(getattr(state, "measured_at", None))
    if pending is not None and measured is not None and acct and measured >= pending:
        probe.pop("pending", None)
        probe.pop("trigger", None)
        changed = True
    if voided:
        old = olds[0] if len(set(olds)) == 1 else ",".join(sorted(set(olds)))
        switch.trace("account_switch", sid=sid, old=old, new=acct, at=now.isoformat(),
                     trigger=trigger or "T3", voided=voided)
        pair = f"{old}>{acct or 'none'}"
        said = probe.setdefault("voiced", [])
        if pair not in said:
            sys.stderr.write(f"ℹ️ 帳號指紋 {old}→{acct or 'none'}（觸發 {trigger or 'T3'}）："
                             f"已作廢 {len(voided)} 個舊帳號標記（改名保留：{'、'.join(voided)}）\n")
            said.append(pair)
            del said[:-_MAX_VOICED]
        probe["last_switch"] = {"old": old, "new": acct, "at": now.isoformat(), "n": len(voided)}
        changed = True
    if changed:
        save_probe(probe)
    return len(voided)


def status_line() -> str:
    """`sessionctl status` 的帳號指紋行（R-4.1.7-6；F-18）：`acct=<12 碼>` 或 `acct=none`。"""
    acct = quota_halt_marker.cache_account()
    last = load_probe().get("last_switch") or {}
    tail = (f"；最近換帳號 {last.get('old')}→{last.get('new')} 於 {last.get('at')}，"
            f"已作廢 {last.get('n')} 個舊帳號標記" if last else "")
    return f"帳號指紋：acct={(acct or 'none')[:12]}{tail}"


__all__ = ["tick", "reconcile", "needs_remeasure", "scan_login", "status_line", "load_probe",
           "probe_path", "credentials_path", "cred_sig", "PROBE_NAME", "LOGIN_TAG"]
