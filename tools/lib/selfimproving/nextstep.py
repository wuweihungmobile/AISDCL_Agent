"""SelfImproving 原因碼→白話對照表與「下一步」判定（TCS-SelfImproving-P7 附錄 A；AC-SI-47-6、12）。

能力類別 `ro`：純函式、不讀時鐘、不讀檔、不讀環境。**白話句的單一住所**：快照（`patrolreport`）、
提案詳情（`propdetail`）與其他模組一律經 `reason()`／`of()` 取字，不得內嵌第二份（AT-747-12-3）。
`REASON` 每筆 `{who, permanent, text}`：`who` 為五值之一；`permanent` 為真＝條件不解除不會自動
入帳（需人處理）；`text` 單行、≤80 字元、不含 `｜`，`{detail}` 為占位（`reason()` 填入消毒後細節）。
"""

from __future__ import annotations

from dataclasses import dataclass

WHO = ("掌舵者", "巡邏器", "無人運轉", "主機管理者", "無")
TEXT_MAX = 80
DETAIL_MAX = 80
HEAD_KEEP = 20  # 超長細節保留的頭段字元數（其餘額度給尾段）
LINE_MAX = 120  # 快照單句白話的上界（含填入的細節；須容得下 80 字元的細節加最長前綴）
UNKNOWN_STATE = "UNKNOWN-STATE"
MIN_KEY = "min_heldout"  # 評估集案例數下限的參數鍵（`propdetail` 經此取名，不自持字面）


@dataclass(frozen=True)
class Reason:
    code: str
    who: str
    permanent: bool
    text: str


def _rows(who: str, permanent: bool, text: str, *codes: str) -> dict[str, dict]:
    return {c: {"who": who, "permanent": permanent, "text": text} for c in codes}


def _build() -> dict[str, dict]:
    admin, host, me = "主機管理者", "巡邏器", "掌舵者"
    t: dict[str, dict] = {}
    # ── A.1 入帳被拒碼 ──
    t |= _rows(me, True, "提案卡面已更新，你按的是舊卡面；請看新卡面重新決定", "STALE-CARD")
    t |= _rows(me, True, "卡面變更或尚未發卡；請等新卡面", "CARD-CHANGED", "CARD-NOT-ISSUED")
    t |= _rows(me, True, "提案目前的狀態不允許這個決定（可能已被處理）",
               "PRECONDITION-STATE", "STATE-ILLEGAL", "TRANSITION-ILLEGAL")
    t |= _rows(me, True, "決定的式樣與驗證結果不符（NE 須用「未驗採納」式）",
               "PRECONDITION-VERDICT", "PROMOTE-FORM-MISMATCH")
    t |= _rows(me, True, "沙盒前提不成立（回滾乾跑或觸及範圍），不能晉升",
               "PROMOTE-PREMISE-ROLLBACK", "PROMOTE-PREMISE-TOUCHED")
    t |= _rows(me, True, "這種提案不能用這個決定（轉交型與迴圈型動詞不同）",
               "ROUTE-VERB-MISMATCH", "ROUTE-HANDOFF", "KIND-MISMATCH")
    t |= _rows(me, True, "解除或恢復的對象狀態不對或已不存在",
               "NOT-IN-COOLDOWN", "NOT-SUSPENDED", "RUN-MISMATCH", "RUN-NOT-FOUND")
    t |= _rows(me, True, "找不到對象，或觀察已不是 open",
               "PROP-NOT-FOUND", "OBS-NOT-FOUND", "OBS-ARCHIVED", "NOT-OPEN")
    t |= _rows(me, True, "送出的內容格式不合（理由、類別、處置欄）；請修正後重送",
               "REASON-CLASS-MISSING", "REASON-CLASS-INVALID", "REASON-CLASS-UNEXPECTED",
               "REASON-CLASS-MISMATCH", "REASON-EMPTY", "DISPOSITION-INVALID",
               "DISPOSITION-TEXT-MISSING", "PIPE-IN-FIELD", "CTRL-CHAR", "FIELD-BLANK",
               "FIELD-TOO-LONG", "AUDIT-BODY-INVALID")
    t |= _rows(admin, True, "稽核檔本身格式有誤，需查 Console 與主機版本是否一致",
               "AUDIT-SCHEMA", "AUDIT-REF-MISMATCH", "AUDIT-KIND-MISMATCH", "AUDIT-KIND-UNKNOWN",
               "AUDIT-USER-FORMAT", "AUDIT-TIME-FORMAT", "AUDIT-SUBJECT-MISMATCH",
               "AUDIT-FILE-MISSING", "AUDIT-FILE-TOO-LARGE")
    t |= _rows(admin, True, "送出者不是管理員，主機不受理", "ROLE-NOT-ADMIN")
    t |= _rows(admin, True, "簽章不符：金鑰錯誤或稽核檔被改過", "AUDIT-MAC-MISMATCH")
    t |= _rows(admin, False, "主機沒有或找不到對應金鑰；修好後下一心跳自動入帳",
               "AUDIT-KEY-MISSING", "AUDIT-KEY-UNKNOWN")
    t |= _rows(host, False, "暫時性衝突或寫入失敗；下一心跳自動重試",
               "LOCK-BUSY", "LEDGER-WRITE-FAILED", "HOME-UNWRITABLE", "GIT-UNAVAILABLE",
               "STATE-CHANGED")
    t |= _rows(admin, True,
               "這個稽核編號已入帳過（重複送出），不會再入帳；請看帳本是否已有對應結果",
               "AUDIT-REF-REUSED")
    t |= _rows(me, True, "研究來源登記同步被拒；請在 Console 重新同步", "REG-STALE")
    t |= _rows(me, True, "排程設定不被接受（週期超界或未啟用）",
               "PERIOD-OUT-OF-RANGE", "SCHED-QUOTE-REQUIRED", "SCHED-NOT-ENABLED")
    # ── A.2 依帳本推導的狀態 ──
    t |= _rows(me, False, "等你核准、否決或退回", "WAIT-DECISION")
    t |= _rows(me, False, "等你決定是否轉交給對應流程", "WAIT-HANDOFF")
    t |= _rows(admin, True,
               "尚未凍結評估集；需有人用 heldout-freeze，巡邏器不會自己湊", "NO-HELDOUT")
    t |= _rows(host, False,
               "會照常驗證，但案例數低於下限，驗證必判 NE（未驗證）", "HELDOUT-BELOW-MIN")
    t |= _rows(host, False, "等巡邏器下一次心跳做沙盒套用", "WAIT-SANDBOX")
    t |= _rows(host, False, "等巡邏器下一次心跳做驗證", "WAIT-VERIFY")
    t |= _rows(host, False, "驗證完成，等巡邏器重發卡面", "WAIT-CARD")
    t |= _rows(me, False, "驗證通過，等你決定是否晉升", "WAIT-PROMOTE-DECISION")
    t |= _rows(host, False, "你已決定晉升，等巡邏器下一次心跳套用", "WAIT-PROMOTE")
    t |= _rows(host, False, "你已決定回滾，等巡邏器下一次心跳執行", "WAIT-ROLLBACK")
    t |= _rows("無", False, "已晉升，量測成效中", "MEASURING")
    t |= _rows("無", False, "已結案", "CLOSED")
    t |= _rows(admin, True,
               "已被退回；需有人用 prop-revise 修訂後重送（第二波起可由 Console 請求）",
               "WAIT-REVISION")
    t |= _rows(me, False, "已否決並進冷卻；可由你解除", "COOLDOWN")
    t |= _rows("無", False, "提案已被否決並結束", "REJECTED")
    t |= _rows("無", False, "已轉交對應流程", "HANDED-OFF")
    t |= _rows("無", False, "狀態未知", UNKNOWN_STATE)
    # ── A.3 巡邏器本心跳的 note ──
    t |= _rows(admin, True,
               "巡邏器不晉升／回滾：有非 SI 自有的未提交改動，請先提交或還原", "dirty-tree")
    t |= _rows(host, False, "正在推送，等推送結束後再晉升／回滾", "PUSH-IN-PROGRESS")
    t |= _rows(admin, True, "巡邏器找不到記憶目錄 {detail}", "MEMORY-DIR-UNRESOLVED")
    t |= _rows(admin, True, "記憶檔在驗證後被改過，需重新上卡", "PREIMAGE-MISMATCH")
    t |= _rows(admin, True,
               "晉升後記憶檔與預期不符，請人工檢查（不自動回滾）", "POSTIMAGE-MISMATCH")
    t |= _rows(admin, True,
               "巡邏器的本機提交失敗（可能是 git hook 拒絕）；需人處理，不重試", "COMMIT-FAILED")
    t |= _rows(admin, True, "帳本或提案檔有不合規則的改動，巡邏器沒有提交，請人工檢查",
               "COMMIT-LEDGER-RULE")
    t |= _rows(admin, True, "還有不在本次提交範圍的相關未提交檔（{detail}），巡邏器沒有提交它們",
               "COMMIT-LEFTOVER")
    t |= _rows(admin, True,
               "提交已完成但巡邏器的提交紀錄寫入失敗，這個提交不會自動推送，請人工檢查後推送",
               "COMMIT-RECORD-FAILED")
    t |= _rows(admin, True, "晉升／回滾被前置檢查擋下；碼為原因，詳見日誌",
               "APPLY-FAILED", "NON-EVOLVABLE-NOW", "DIGEST-MISMATCH", "STATE-NOT-VERIFIED",
               "NO-PROMOTE-DEC", "NO-ROLLBACK-DEC", "TREE-CHANGED", "ROLLBACK-NOT-EXACT",
               "MEMORY-DIR-MISSING")
    t |= _rows(admin, True, "沙盒套用失敗；提案需退回或修訂",
               "SANDBOX-NOT-APPLIED", "SANDBOX-EXPORT-FAILED", "SANDBOX-APPLY-TIMEOUT",
               "TOUCHED-SUPERSET", "ROLLBACK-DRYRUN-FAILED")
    # ── A.4 推送（固定白話句） ──
    t |= _rows(admin, True, "自動推送未啟用（預設關閉；需由主機管理者明確開啟）", "PUSH-OFF")
    t |= _rows(host, False, "正在推送，請稍候", "PUSH-RUNNING")
    t |= _rows("無", False, "已推送成功", "PUSH-OK")
    t |= _rows("無", False, "沒有待推送的提交", "PUSH-NOT-AHEAD")
    t |= _rows(admin, True,
               "目前不在 main 分支或沒有 origin/main 上游，不自動推送", "PUSH-NOT-MAIN")
    t |= _rows(admin, True, "工作樹有未提交改動，請先提交或還原", "PUSH-DIRTY-TREE")
    t |= _rows(admin, True,
               "待推送的提交含非巡邏器產生者（{detail}），請由人推送", "PUSH-FOREIGN-COMMITS")
    t |= _rows(admin, True, "提交的 APP 標記不是晉升或回滾（{detail}），疑似照抄格式，不自動推送",
               "PUSH-APP-KIND-INVALID")
    t |= _rows(admin, True,
               "同一個 APP 標記出現在多個提交（{detail}），不自動推送", "PUSH-APP-REUSED")
    t |= _rows(admin, True, "提交改了允許範圍外的檔案（{detail}），不自動推送", "PUSH-PATH-OUTSIDE")
    t |= _rows(admin, True,
               "提交內容與帳本記錄不符（{detail}），不自動推送", "PUSH-CONTENT-MISMATCH")
    t |= _rows(admin, True,
               "這個提交沒有巡邏器的紀錄，請人工檢查後推送（{detail}）", "PUSH-NOT-RECORDED")
    t |= _rows(admin, True,
               "提交與巡邏器的紀錄不符（{detail}），請人工檢查後推送", "PUSH-RECORD-MISMATCH")
    t |= _rows(admin, True, "提交對帳本或提案檔的改動超出允許規則（{detail}），不自動推送",
               "PUSH-LEDGER-RULE")
    t |= _rows(admin, True, "提案目錄的新檔內容與帳本記錄的雜湊不符（{detail}），不自動推送",
               "PUSH-PROPOSAL-MISMATCH")
    t |= _rows(admin, True, "git 不可用或逾時，無法判定推送條件", "PUSH-GIT-UNAVAILABLE")
    t |= _rows(admin, True, "提交含符號連結、子模組或檔案模式變更（{detail}），不自動推送",
               "PUSH-FILE-MODE-INVALID")
    t |= _rows(admin, True, "提交新增的內容疑似含機密（{detail}），不自動推送，請人工檢查",
               "PUSH-SECRET-PATTERN")
    t |= _rows(admin, True, "repo 的 git 設定含不允許的項目（{detail}），不自動推送，請人檢查",
               "PUSH-GIT-CONFIG-UNSAFE")
    t |= _rows(admin, True, "repo 的替換物件、grafts、shallow 或屬性檔會改變守門所見內容"
               "（{detail}），不自動推送", "PUSH-REPO-STATE-UNSAFE")
    t |= _rows(admin, True, "遠端網址與安裝推送排程時記錄的不同（{detail}），不自動推送",
               "PUSH-REMOTE-URL-CHANGED")
    t |= _rows(admin, True,
               "遠端 main 的實際位置與本機記錄不同（{detail}），請先 fetch 並確認，不自動推送",
               "PUSH-REMOTE-DRIFT")
    t |= _rows(admin, True,
               "遠端 main 不是待推送提交的祖先（{detail}），推送會覆寫遠端，不自動推送",
               "PUSH-REMOTE-DIVERGED")
    t |= _rows(host, False, "判定之後本機分支或 HEAD 被改動，這次不推送，下個心跳重判",
               "PUSH-HEAD-MOVED")
    t |= _rows(admin, True, "推送前的本機檢查沒通過，請看檢查輸出後由人推送", "PUSH-HOOK-FAILED")
    t |= _rows(admin, True, "遠端有新提交，請先整合（rebase 或 merge）再由人推送", "PUSH-REJECTED")
    t |= _rows(admin, True, "遠端認證失敗，請在互動視窗手動 git push 一次更新憑證", "PUSH-AUTH")
    t |= _rows(host, False,
               "推送逾時被終止；稍後自動重試（用盡後請由人推送）", "PUSH-WALL-EXCEEDED")
    t |= _rows(host, False, "推送失敗（多為網路）；稍後自動重試（用盡後請由人推送）", "PUSH-FAILED")
    t |= _rows(admin, True, "推送程式發生未預期錯誤（{detail}），請查 push 目錄的 last_error",
               "PUSH-INTERNAL-ERROR")
    t |= _rows(host, False, "等推送任務下一次執行（每個心跳一次）", "PUSH-PENDING")
    t |= _rows(admin, True, "等使用者登入後自動推送", "PUSH-WAITING-LOGIN")
    # ── A.5 驗證 reasons（說明性） ──
    t |= _rows("無", False, "沒有探針，驗證無法判定", "NO-PROBES")
    t |= _rows("無", False, "載具自證失敗", "CARRIER-PROOF-FAILED")
    t |= _rows("無", False, "評估集 digest 不符", "HELDOUT-DIGEST-MISMATCH")
    t |= _rows("無", False, "評估集案例數低於下限", "HELDOUT-TOO-SMALL")
    t |= _rows("無", False, "評估集內容曾外露，驗證不可信", "HELDOUT-EXPOSED")
    t |= _rows("無", False, "無法確認評估集是否外露", "EXPOSURE-UNKNOWN")
    t |= _rows("無", False, "探針執行逾時", "PROBE-TIMEOUT")
    t |= _rows("無", False, "修復前探針沒有變紅", "BASELINE-NOT-RED")
    t |= _rows("無", False, "套用後探針仍紅", "PATCHED-NOT-GREEN")
    t |= _rows("無", False, "突變後探針沒有變紅，探針鑑別力不足", "MUTATION-NOT-RED")
    t |= _rows("無", False, "沒有提供突變檔，無法檢驗探針鑑別力", "MUTATION-ABSENT")
    # ── A.6 排程跳過與運轉等待 ──
    t |= _rows(me, False, "自動演化排程目前停用（Console 立即啟動仍可用）", "SCHED-DISABLED")
    t |= _rows("無", False, "本期已經跑過一次，等下一期", "SCHED-CELL-RAN")
    t |= _rows(host, False, "本期到期，巡邏器正在開運轉", "SCHED-DUE")
    t |= _rows("無", False, "現在在黑窗時段（{detail}），不開運轉", "SKIP-BLACKOUT")
    t |= _rows("無", False, "額度帶不允許（{detail}），不開運轉", "SKIP-QUOTA-BAND")
    t |= _rows("無", False, "近期有人在互動視窗工作，巡邏器先不開運轉", "SKIP-OTHER-DRIVER")
    t |= _rows(admin, True, "工作樹有非自我進化的未提交改動，不開運轉", "SKIP-DIRTY-TREE")
    t |= _rows(admin, True,
               "已有未關運轉（{detail}），排程與立即啟動都會等它關閉（第二波起可由 Console 處理）",
               "SKIP-RUN-OPEN")
    t |= _rows(admin, True, "無人運轉主控無法啟動（{detail}），請查巡邏日誌", "SKIP-SPAWN-FAILED")
    t |= _rows(host, False, "已有進行中的無人運轉，這個運轉等它結束後再啟動", "RUN-BUSY")
    t |= _rows(admin, True,
               "運轉逾時但行程身分與記錄不符，沒有終止它（避免誤殺他人行程），請人工檢查",
               "RUN-KILL-SKIPPED")
    # ── A.7 匯出 ne 新碼 ──
    t |= _rows(admin, True, "讀不到提案的 patch 檔", "PATCH-UNREADABLE")
    t |= _rows(admin, True, "讀不到提案本文檔", "BODY-UNREADABLE")
    t |= _rows(admin, True, "讀不到觀察帳本，來源觀察無法顯示", "OBS-LEDGER-UNREADABLE")
    t |= _rows(admin, True, "讀不到評估集下限參數，無法判斷案例數是否足夠", "HELDOUT-MIN-UNKNOWN")
    t |= _rows("無", False, "事件太多，時間線只顯示最後 500 筆", "TIMELINE-TRUNCATED")
    return t


REASON: dict[str, dict] = _build()
# 研究來源登記的前綴族（A.1 的 `REGISTRY-*`／`REG-*`）：同一句白話
_PREFIX = (("REGISTRY-", REASON["REG-STALE"]), ("REG-", REASON["REG-STALE"]))
_GENERIC = {"who": "主機管理者", "permanent": True, "text": "主機拒收（碼 {detail}）；請讀巡邏日誌"}
_GENERIC_STEP = {"who": "主機管理者", "permanent": True,
                 "text": "巡邏器的這一步被拒（碼 {detail}）；請讀日誌"}
_PROMOTE_VARIANT = {
    "NE": "驗證未能判定（NE），要晉升須勾「未驗採納」；否則不晉升",
    "FAIL": "驗證未通過（FAIL），只能退回或不晉升",
}


def clip(text: str, limit: int) -> str:
    """超長時中段省略：頭（至多 20 字元，TCS-P7 E-14）＋「…」＋尾，使路徑的尾段（如
    `…\\memory`）仍看得到；`limit`＝80 時恰為前 20＋…＋後 59。"""
    if len(text) <= limit:
        return text
    if limit < 2:
        return text[:max(0, limit)]
    head = max(0, min(HEAD_KEEP, (limit - 1) // 3))
    return text[:head] + "…" + text[len(text) - (limit - 1 - head):]


def sanitize(detail) -> str:
    """細節消毒：去換行與 `|`／`｜`、壓縮空白、超過 `DETAIL_MAX` 字元時中段省略（保留尾段）。"""
    return clip(" ".join(str(detail).replace("｜", " ").replace("|", " ").split()), DETAIL_MAX)


def reason(code: str, detail=None, *, step: bool = False) -> Reason:
    """碼→`Reason`（`.text` 已填 `{detail}`）；未登記碼走通用列（`step=True` 取巡邏步驟版）。"""
    row = REASON.get(code)
    if row is None:
        row = next((r for p, r in _PREFIX if code.startswith(p)), None)
    if row is None:
        row = _GENERIC_STEP if step else _GENERIC
        detail = code if detail is None else detail
    text = row["text"]
    if "{detail}" in text:
        room = max(0, min(DETAIL_MAX, LINE_MAX - len(text.replace("{detail}", ""))))
        text = text.replace("{detail}", clip(sanitize("-" if detail is None else detail), room))
    return Reason(code, row["who"], row["permanent"], text)


def below_min_note(n: int, minimum: int) -> str:
    """`detail.heldout.neNote`：案例數低於下限時的白話（含 n 與下限）。"""
    return (f"評估集只有 {n} 個案例，低於下限 {minimum}，驗證必判 NE（未驗證）；"
            "晉升只能走「未驗採納」式")


def _freeze_n(events, p) -> int | None:
    ev = next((e for e in events or () if e.get("seq") == p.freeze_seq), None)
    n = ev.get("n") if ev else None
    return n if isinstance(n, int) and not isinstance(n, bool) else None


def _carded(events, pid: str) -> bool:
    last = max((e["seq"] for e in events if e["kind"] == "app.verify" and e.get("prop") == pid),
               default=0)
    return any(e["kind"] == "card" and e.get("prop") == pid and e["seq"] > last for e in events)


def _code_of(fold, p, params, events) -> tuple[str, str | None]:
    """（碼, 白話句覆寫或 None）。`events` 為 None＝不判發卡與案例數（視為已發卡、案例數不明）。"""
    st = p.state
    minimum = (params or {}).get(MIN_KEY)
    if st == "proposed":
        return ("WAIT-DECISION", None) if p.route == "loop" else (
            ("WAIT-HANDOFF", None) if p.route.startswith("handoff:") else (UNKNOWN_STATE, None))
    if st in ("approved", "sandboxed"):
        if st == "approved" and p.freeze_seq is None:
            return "NO-HELDOUT", None
        n = _freeze_n(events, p)
        if isinstance(minimum, int) and n is not None and n < minimum:
            return "HELDOUT-BELOW-MIN", None
        return ("WAIT-SANDBOX" if st == "approved" else "WAIT-VERIFY"), None
    if st == "verified":
        if p.pending_promote is not None:
            return "WAIT-PROMOTE", None
        if events is not None and not _carded(events, p.id):
            return "WAIT-CARD", None
        return "WAIT-PROMOTE-DECISION", _PROMOTE_VARIANT.get(p.verdict or "")
    if st in ("promoted", "measuring", "closed"):
        if p.pending_rollbacks >= 1:
            return "WAIT-ROLLBACK", None
        return ("CLOSED" if st == "closed" else "MEASURING"), None
    if st == "returned":
        return "WAIT-REVISION", None
    if st == "rejected":
        cooling = any(c["prop"] == p.id for c in fold.cooldowns)
        return ("COOLDOWN" if cooling else "REJECTED"), None
    return ("HANDED-OFF" if st == "handed-off" else UNKNOWN_STATE), None


def of(fold, prop, params, events=None) -> dict:
    """某 PROP 的下一步 `{code, who, text}`（附錄 A.2；只看帳本）。`prop` 可為 `Prop` 或其編號；
    `events`（已過 `sound` 的事件列）供判「驗證後是否已發卡」與評估集案例數——這兩項不在 `Folded`
    內；缺省時不判（視為已發卡、案例數不明）。未知狀態＝`UNKNOWN-STATE`、不拋例外。"""
    p = fold.props.get(prop) if isinstance(prop, str) else prop
    if p is None:
        r = reason(UNKNOWN_STATE)
        return {"code": r.code, "who": r.who, "text": r.text}
    code, text = _code_of(fold, p, params, events)
    r = reason(code)
    return {"code": r.code, "who": r.who, "text": text or r.text}
