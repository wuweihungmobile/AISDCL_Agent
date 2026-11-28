"""park 失敗鏈終局的出聲（QuotaWall DES §7.5 第 3 步；S-11、S-17；R218 Q3）。

必達管道：handback（指向痕跡）＋`quota_escalation.notify_queue_path()` 佇列；
桌面通知本身照使用者偏好
（預設關，R82／HELM-01「預設就不敲」是掌舵者直接指令），所以通知與佇列分開：佇列一律寫、`notify()`
只在「登記時的 `AUTOSDD_DESKTOP_NOTIFY` 原值（標記 `desktop_notify`）為開 ∧ job 轉送值不是關閉值」
時才呼叫。
job 是排程器以登入者真環境跑起來的，行程環境不會帶使用者的通知偏好，所以偏好必須在登記時存進標記。
本檔是 `sandbox_scope.SITES` 的 notify 站點：入口先過 L1（沙盒租約過期後不得敲真桌面）。
`quota_escalation` 重（引入整串額度模組），一律在函式內才 import（hook 鏈不為它付載入成本）。
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from . import qw_schema, se_gate, switch

_REPO = Path(__file__).resolve().parents[3]
OFF_VALUES = ("", "0", "false", "off", "no")


def notify_enabled(marker: dict, env=None) -> bool:
    """標記 `desktop_notify` 為開 ∧ job 行程環境（argv 轉送值）沒有關閉。"""
    import quota_escalation  # noqa: PLC0415

    env = os.environ if env is None else env
    saved = qw_schema.marker_primary(marker).desktop_notify
    now = env.get(quota_escalation.NOTIFY_ENV)
    return saved.strip().lower() not in OFF_VALUES and (
        now is None or str(now).strip().lower() not in OFF_VALUES)


def _handback(sid: str, pkg, attempts: list, tail: str = "park_failed", text: str | None = None) -> None:
    import resume_route  # noqa: PLC0415

    tried = "\n".join(f"- {a.get('route')}（fork={a.get('fork')}）attempted={a.get('attempted')} "
                      f"rc={a.get('rc')} 原因={a.get('reason') or '—'}" for a in attempts)
    body = text or ("## 做了什麼\npark 排程到點，所有續航嘗試都失敗了"
                    "（痕跡 `park_chain_failed`、`park_attempt`，"
                    f"在 autosdd_session_switch.jsonl）。\n\n## 驗了什麼\n逐次嘗試的實際結果：\n{tried}\n\n"
                    f"## 卡在哪\n見上列原因；交接包 {pkg}。\n\n"
                    f"## 下一步指令\n`claude -r {sid}` 手動回舊 session，或 "
                    f"`python tools/sessionctl.py handoff --spawn {pkg}`。\n")
    try:
        path = resume_route.handback_report(f"{sid}_{tail}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8", newline="\n")
    except OSError:
        pass


def _enqueue(title: str, body: str, rc: int) -> None:
    """通知補投佇列入列（不論桌面通知開關）；寫不進去不拋。"""
    import quota_escalation  # noqa: PLC0415
    import quota_ledger  # noqa: PLC0415

    path = quota_escalation.notify_queue_path()

    def _append() -> bool:
        items = quota_escalation._load_queue(path)  # noqa: SLF001 — 佇列格式的唯一實作
        items.append({"title": title, "body": body, "queued_at": datetime.now().timestamp(),
                      "attempts": 0, "last_rc": rc})
        return quota_escalation._save_queue(path, items)  # noqa: SLF001

    try:
        quota_ledger.with_lock(path.with_suffix(".lock"), _append)
    except OSError:
        pass


def announce(sid: str, pkg, marker: dict, attempts: list, *, claude: str | None = None,
             env=None, notify=None, repo=None, title: str | None = None, body: str | None = None,
             tail: str = "park_failed", handback_text: str | None = None) -> None:
    """handback → 佇列 → 桌面通知（依偏好）。`notify` 是測試縫；`repo`＝呼叫端 job 的 repo
    （缺省＝本檔所在 repo；job 與判準必須同一個根，L1 才不會誤判根不一致）。`title`／`body`／`tail`
    （handback 檔名尾碼）／`handback_text` 由呼叫端傳入（WP-SW REQ-CTL-52 泛化）；缺省＝失敗鏈字面逐字不變。"""
    import quota_escalation  # noqa: PLC0415

    if se_gate.check("park_announce.announce", repo=repo or _REPO, pkg=pkg, sid=sid,
                     claude=claude):
        return
    _handback(sid, pkg, attempts, tail, handback_text)
    title = title or "park 到點續航失敗"
    body = body or (f"session {sid[:8]} 的 park 排程到點後所有嘗試都失敗；"
                    "請看 handback 或 sessionctl status。")
    rc = quota_escalation.NOTIFY_OFF_RC
    if notify_enabled(marker, env):
        key, saved = quota_escalation.NOTIFY_ENV, os.environ.get(quota_escalation.NOTIFY_ENV)
        os.environ[key] = qw_schema.marker_primary(marker).desktop_notify
        try:
            rc = (notify or quota_escalation.notify)(title, body)
        finally:
            if saved is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = saved
    _enqueue(title, body, rc)
    switch.trace("park_failure_announced", sid=sid, notify_rc=rc, attempts=len(attempts))
