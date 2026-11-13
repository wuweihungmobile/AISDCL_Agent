"""sessionctl 的選路與過期判準：喚醒選路（RESUME／FRESH／REFUSE）、成本規則 R1～R4、SUPERSEDED。

WHY 住這裡（ADR-XPLAT-004 §2.13.1）：`tools/session_resume_planner.py` 的 `guardrail_cli` LOC
餘裕只剩 2 行，D2／D3 的判準不可能長在它身上 ⇒ WP0 先把 `choose_resume_route` 的判定本體連同它的
常數搬來，planner 留同名委派（測試對 `planner.choose_resume_route`／`planner.STRATEGY_*` 的引用
不動）。本檔純函式＋讀檔，只有兩處寫入：handback 目錄解析的冪等 mkdir（見 `choose_resume_route`
上方註記）、`settle_superseded`／`write_superseded_handback`（SUPERSEDED 命中後的處置，由 planner 的
哨兵與續航兩處呼叫）。三塊：喚醒選路（WP0）、D2 成本規則與門檻（WP1）、D3 過期判準（WP2）。
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import resume_route
import unattended_authz  # DEF-200-575：harness 背景等待上限的唯一家

#: ── R95／Pkg-D：喚醒降級選路（PRD §4.5.4／§8-10）─────────────────────────────
#: `-r <sessionId>` 的前提是逐字稿可用；缺檔／為空／超上限時整條喚醒鏈此前**沒有退路**
#: （指令直接失敗且靜默）。降級目標＝FRESH_SESSION_WITH_STATE：不帶 `-r` 的全新
#: session，state 由磁碟任務書交棒（〈可重啟點四條件〉第 2 條本來就要求它落盤）。
#: 上限預設 32MiB 是量出來的：本機 ~/.claude/projects/ 全量 1,108 支 .jsonl，
#: p50=403KB、p99=3.1MB、max=6.0MB ⇒ 32MiB 只攔病態值（≈觀測 max 的 5 倍）——假降級
#: 會把可用的 session context 丟掉，判準刻意窄。量測逐字與選值理由住
#: docs/06_quality/CrossPlatform_R95_Resume_Strategy_Evidence.md §2。
#: 🔴 ENV 以 `os.environ` 直讀（消費端住本檔）；`quota_policy.ENV_SPEC` 的宣告列已由
#: R95 收尾窗口補上（attr=None ⇒ 不進 Policy——宣告面與消費面刻意分居兩檔）。
RESUME_MAX_TRANSCRIPT_ENV = "AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES"
RESUME_MAX_TRANSCRIPT_DEFAULT = 32 * 1024 * 1024
STRATEGY_RESUME = "SESSION_RESUME"
STRATEGY_FRESH = "FRESH_SESSION_WITH_STATE"
STRATEGY_REFUSE = "REFUSE"
#: 兩條路共用的護欄尾段（重驗＋禁 commit/push）。住常數而不是兩處各自內嵌：降級路
#: 少帶護欄句＝FRESH 那一跑比 RESUME 少一層約束，而漏帶是靜默的。
RESUME_RULES = (
    "🔴 第一件事是重驗，不採信該檔任何「已通過」宣稱。遵守第 4 節〈禁止事項〉。"
    "任務書 §3 為 TODO 時，先讀 handback 與記憶檔〈可重啟點〉再行動。"  # DEF-200-567：只加一句指引
    "🔴 本回合無人看管，禁止 commit／push"
    "（已由 PreToolUse 守衛硬擋，不是請求）——改動留在工作樹讓人回來收。"
    "🔴 收窗前必寫 handback 檔（路徑由 prompt 注入），四節齊備："
    "## 做了什麼／## 驗了什麼（附實測 rc）／## 卡在哪／## 下一步指令。"
    "🔴 本回合是無頭 print 模式（claude -p）：收尾回合後 harness 最多再等背景任務"
    "（子代理／背景 shell）"
    f"{unattended_authz.RESUME_BG_WAIT_CEILING_SECONDS // 60} 分鐘，逾時全部停掉、成果歸零 ⇒ "
    "派棒總預算必須小於它、每棒邊做邊把成果寫進 handback 目錄；等待期間不要自造輪詢迴圈。"
)  # DEF-200-575：背景等待上限告知句（數字取同源常數）


# m5（R95 修復包）：ENV 病態值（非整數字串／零／負值）此前直接 `int()` 炸在喚醒路徑上
# ——那正是「無人看管、沒有人看 stderr」的一跑。退回內建預設並出聲一次，比照「量不到
# ≠不設限」慣例；空字串＝未設，走預設不出聲（`or` 語意本來就如此，不是病態值）。
def _transcript_cap() -> tuple[int, str]:
    """ENV 上限解析：回 `(limit, note)`；`note` 非空＝病態值已退回預設（呼叫端進 reason）。"""
    raw = str(os.environ.get(RESUME_MAX_TRANSCRIPT_ENV) or "").strip()
    try:
        val = int(raw) if raw else RESUME_MAX_TRANSCRIPT_DEFAULT
    except ValueError:
        val = 0
    if val >= 1:
        return val, ""
    note = (f"{RESUME_MAX_TRANSCRIPT_ENV}={raw!r} 是病態值（非正整數）⇒ 退回預設 "
            f"{RESUME_MAX_TRANSCRIPT_DEFAULT:,}B")
    print(f"⚠️ {note}", file=sys.stderr)
    return RESUME_MAX_TRANSCRIPT_DEFAULT, note


# 🔴 選路近乎純函式（stat 一次逐字稿，不 spawn；m5 起病態 ENV 會印一行 stderr，那是出聲
# 不是副作用升級；G2 起另有一次**冪等 mkdir**——handback 目錄解析經 resume_route→
# endurance_env，「不寫檔」的舊宣稱已據實訂正）：四種輸入態都要能在測試裡注入。
# 方向鎖：降級只准 RESUME→FRESH 單向——逐字稿可用且 `weekly` 為空時**必須**回 SESSION_RESUME
# （把可用的 session context 丟掉＝資訊損失），且 FRESH 的 argv 不得帶 `-r`。任務書缺席＝REFUSE：
# 兩條路的 prompt 都指向任務書，它缺席時派出去的是一個空承諾（R59 事故同形），呼叫端
# 必須 fail-loud，不得靜默派空 prompt。argv 順序（prompt 必在 `--add-dir` 之前，且
# --add-dir 後只能有一個值）的立案見 `_run_resume` 上方 R80 段與姊妹鎖
# test_the_variadic_add_dir_does_not_swallow_the_prompt。
def choose_resume_route(claude: str, session_id: str, transcript: Path | None,
                        plan_path: str, max_bytes: int | None = None, weekly: str = "", *,
                        guard=None, handoff_path: str | None = None, env=None,
                        cost_path: Path | None = None) -> dict:
    """喚醒選路：回 `{strategy, reason, argv}`；REFUSE 時 argv=None（呼叫端 fail-loud）。

    WP1（D2）：RESUME 的條件多一條「R1～R3 皆未命中」（`fresh_reasons`；R4＝既有的逐字稿
    上限與 `weekly`），命中即降 FRESH、理由逐條列出。`guard`＝hook 模組（planner 傳入；
    `None`＝只判 R3，測試縫）；`handoff_path`＝交接包路徑的參數縫（下一包注入；`None` 時
    FRESH 的 prompt 沿用任務書路徑）；`env`／`cost_path` 為門檻與成本帳的注入縫。

    🔴 2026-09-07 掌舵者裁決（SA＋SD 兩位獨立審查通過）：此前有一個 `followup_ok` 參數
    （＝INV3「前一窗確實起來」的判準結果，往下傳成 `resume_argv(allow_followup=…)`），
    連同 INV2 一併移除——無人續跑一旦確認 spawn 成功即與互動 session 同等信任，不分窗次。
    兩路的 argv 因此只差 `-r <session_id>`，權限姿態逐字相同。
    `weekly`＝週軸已達 converge 帶的理由（PRD §4.5.4；`resume_route.weekly_why()` 取數、呼叫端
    注入）：非空 ⇒ 逐字稿可用也降級 FRESH（省額度優先），空＝不強制。
    """
    rules = RESUME_RULES
    plan = Path(str(plan_path or ""))
    if not plan.is_file():
        return {"strategy": STRATEGY_REFUSE, "argv": None,
                "reason": f"任務書不存在：{plan_path!r}——state 交棒載體缺席，RESUME 與 "
                          "FRESH 兩條路都無法成立 ⇒ 拒絕武裝（不得靜默派空 prompt）"}
    limit, cap_note = (max_bytes, "") if max_bytes is not None else _transcript_cap()
    suffix = f"；{cap_note}" if cap_note else ""
    # G2：交接檔路徑在**這裡**算一次（prompt 注入與 `_run_resume` 後檢共用 route["handback"]
    # 同一份字串）；解析經 resume_route→endurance_env（冪等 mkdir，見上方純函式註記的訂正）。
    # session id 缺席（FRESH 降級因之一）時退 plan.stem——任務書檔名本就以 sid 命名。
    hb = resume_route.handback_report(str(session_id or "") or plan.stem)
    size = transcript.stat().st_size if (transcript and transcript.is_file()) else None
    hits, notes = fresh_reasons(session_id, transcript, size, guard=guard, env=env, cost_path=cost_path)  # noqa: E501
    if session_id and size and size <= limit and not weekly and not hits:
        return {"strategy": STRATEGY_RESUME, "handback": str(hb),
                "reason": f"逐字稿可用（{size:,}B ≤ 上限 {limit:,}B）⇒ 帶完整 context 續跑{suffix}",  # noqa: E501
                # v2.1.13 G1：argv 組裝（含 --permission-mode/--settings 權限姿態旗標）
                # 下沉 tools/lib/resume_route.py——兩路同一份真相，旗標不可能只補到一路。
                "argv": resume_route.resume_argv(claude, str(session_id), f"讀 {plan}，照它第 3 節做。{rules}🔴 handback 檔路徑＝{hb}", plan.parent)}  # noqa: E501
    why = "；".join(r for r in (resume_route.fresh_why(session_id, size, limit, weekly), *hits, *notes) if r)  # noqa: E501
    head = (f"按磁碟任務書繼續：讀 {plan}，照它第 3 節做。" if handoff_path is None else
            f"按交接包繼續：讀 {handoff_path}（機械層＋主控層），再讀任務書 {plan} 的第 3 節。")
    return {"strategy": STRATEGY_FRESH, "handback": str(hb),
            "reason": f"{why} ⇒ 降級開全新 session，state 由磁碟任務書交棒{suffix}",
            "argv": resume_route.fresh_argv(claude, f"{head}{rules}{FRESH_HARD_RULES}🔴 handback 檔路徑＝{hb}", plan.parent)}  # noqa: E501


# ───────────────────────── WP1（D2）：成本選路——量「續跑成本」不量檔案大小（ADR §2.13.2）
#: 門檻的環境變數名；出廠值與說明只有 `quota_policy_env.ENV_SPEC` 一個家（本檔不寫第二份數字）。
R1_KEY = "AUTOSDD_SWITCH_R1_CTX_TOKENS"
R2_KEY = "AUTOSDD_SWITCH_R2_COMPACTIONS"
R3_KEY = "AUTOSDD_SWITCH_R3_CACHE_CREATION_TOKENS"
STALE_HOURS_KEY = "AUTOSDD_STALE_SESSION_HOURS"
AGENT_TOKENS_KEY = "AUTOSDD_RESUME_AGENT_TOKENS"  # D6 續棒閘（下一包的消費端用 `threshold()` 取）
HANDOFF_TTL_KEY = "AUTOSDD_HANDOFF_TTL_HOURS"  # D4 公告存活（下一包）
ROSTER_QUIET_KEY = "AUTOSDD_ROSTER_QUIET_MINUTES"  # D7 名冊「安靜」門檻（下一包）
MODE_KEY = "AUTOSDD_SESSION_SWITCH_MODE"
#: 方向鎖：這四個只准下修（放寬＝退回 E1：20 MB／60 萬 token 的舊 session 仍被整份重讀）。
#: `STALE_SESSION_HOURS` 刻意不在內：調小更積極拆哨兵、調大更晚拆，兩向都有風險（主控裁決 7）。
_DOWNWARD_ONLY = (R1_KEY, R2_KEY, R3_KEY, AGENT_TOKENS_KEY)
#: R1 在 feed 與逐字稿 usage 皆缺時的估計比值（位元組／token）。🔴 這是量測值不是定律：E1 的
#: 20,518,438 B 逐字稿對應約 60 萬 token ⇒ ≈34 B/token，取 40 偏保守（少估一點）；結果一律標
#: `estimated`，要重量由 `tools/probe/`（現查）做，本檔不當它是真值。
BYTES_PER_TOKEN_ESTIMATE = 40
MODES = ("auto", "notify", "off")
#: FRESH 路追加的兩條硬規則（字面鎖；E1：無人窗口 SendMessage 續 40～60 萬 token 的
#: 舊子代理 44 分鐘）。
FRESH_HARD_RULES = (
    "🔴 硬規則一：不得用 SendMessage 續舊 session 的任何代理"
    "（其上下文動輒數十萬 token，續一次就整份重讀）；一律派新代理＋短任務書。"
    "🔴 硬規則二：第一個動作＝重驗 git status／HEAD，以及交接內一切「已通過」宣稱，不採信。")


def _factory(name: str) -> object:
    import quota_policy_env  # noqa: PLC0415 — lazy：純資料模組，只有取出廠值時才需要

    return next(spec.default for spec in quota_policy_env.ENV_SPEC if spec.name == name)


def threshold(name: str, env=None) -> tuple[int, str]:
    """一個正整數門檻：`(值, note)`。env 缺席／空＝出廠值；病態值（非整數／<1）與方向鎖鍵的放寬值
    （> 出廠值）一律退回出廠值並 stderr 出聲一次（`note` 非空；同 `_transcript_cap` 的紀律）。"""
    base, raw = int(_factory(name)), str((os.environ if env is None else env).get(name) or "").strip()  # noqa: E501
    if not raw:
        return base, ""
    try:
        val = int(raw)
    except ValueError:
        val = 0
    if val < 1:
        note = f"{name}={raw!r} 是病態值（非正整數）⇒ 退回出廠值 {base:,}"
    elif name in _DOWNWARD_ONLY and val > base:
        note = f"{name}={val:,} 大於出廠值 {base:,}（只准下修、不准放寬）⇒ 退回出廠值"
    else:
        return val, ""
    print(f"⚠️ {note}", file=sys.stderr)
    return base, note


def switch_mode(env=None) -> str:
    """`AUTOSDD_SESSION_SWITCH_MODE`：auto／notify／off；缺席或未知值退出廠值 `auto`。"""
    raw = str((os.environ if env is None else env).get(MODE_KEY) or "").strip().lower()
    if raw in MODES:
        return raw
    if raw:
        print(f"⚠️ {MODE_KEY}={raw!r} 不是 {'／'.join(MODES)} ⇒ 退回 auto", file=sys.stderr)
    return "auto"


def fresh_reasons(session_id: str, transcript: Path | None, size: int | None, *, guard=None,
                  env=None, cost_path: Path | None = None) -> tuple[list[str], list[str]]:
    """R1～R3 成本規則：回 `(命中理由, 量不到的說明)`；任一規則命中 ⇒ 呼叫端走 FRESH（R4＝既有判準，
    由 `resume_route.fresh_why` 提供，不在此重寫）。命中理由逐條列出、不合併。

    · R1 上下文：feed（`guard.read_context_feed`）→ 逐字稿最後一筆 assistant usage
      （`guard.scan_transcript`）→ 位元組估計（標 `estimated`）；三者皆缺＝量不到。
    · R2 壓縮次數：逐字稿 `compact_boundary` 計數（`guard.compact_boundary_count`；不用 hook 的
      事件檔——它只記有跑到的壓縮，會少算）。讀不動＝0。
    · R3 上次續跑成本：`resume_cost.last_cost` 的同 sid 最近一筆 cache_creation；無記錄＝不成立。
    `guard=None`（呼叫端沒給 hook 模組）⇒ R1／R2 不判，只判 R3。量不到不觸發該條：FRESH 的
    代價是丟上下文，量不到不該單方面造成資訊損失（缺值處理，ADR §2.13.2）。
    """
    t1, t2, t3 = (threshold(key, env)[0] for key in (R1_KEY, R2_KEY, R3_KEY))
    hits: list[str] = []
    notes: list[str] = []
    ready = guard is not None and transcript is not None and transcript.is_file()
    if guard is not None:
        used, source = None, ""
        feed = guard.read_context_feed(session_id, None) if session_id else {}
        if feed.get("used") is not None:
            used, source = feed["used"], "context_feed"
        elif ready and (last := guard.scan_transcript(transcript)[0]) is not None:
            used, source = last, "transcript"
        elif size:
            used, source = size // BYTES_PER_TOKEN_ESTIMATE, f"estimated（{size:,}B÷{BYTES_PER_TOKEN_ESTIMATE}）"  # noqa: E501
        if used is None:
            notes.append("R1 量不到（feed／逐字稿 usage／檔案大小皆缺）⇒ 本條不判")
        elif used >= t1:
            hits.append(f"R1 上下文 {used:,} ≥ {t1:,} tokens（{source}）")
        compactions = guard.compact_boundary_count(transcript) if ready else 0
        if compactions >= t2:
            hits.append(f"R2 已壓縮 {compactions} 次 ≥ {t2} 次")
    import resume_cost  # noqa: PLC0415 — lazy：只有選路時需要

    cost = resume_cost.last_cost(session_id, cost_path) if session_id else None
    if cost is not None and cost >= t3:
        hits.append(f"R3 上次續跑第一回合寫入快取 {cost:,} ≥ {t3:,} tokens")
    return hits, notes


# ───────────────────── WP2（D3）：過期 session 不續跑（SUPERSEDED；ADR §2.13.3）
def own_last_at(transcript: Path | None) -> float | None:
    """本 session 最後一筆**對話記錄**的 epoch 秒（`transcript_activity` 的尺；主檔＋近期
    subagent 檔，非檔案 mtime——DEF-200-560）；逐字稿不在／一筆對話都沒有 ⇒ `None`。"""
    import quota_limits  # noqa: PLC0415 — lazy
    import transcript_activity  # noqa: PLC0415 — lazy

    if transcript is None or not transcript.is_file():
        return None
    return transcript_activity.newest_conversation_at(quota_limits.session_transcripts(transcript))


def superseded_by(project_dir: Path | None, own_sid: str, own_last_epoch: float | None,
                  now: datetime, *, env=None) -> dict | None:
    """判準唯一的家：本 session 閒置 ≥ `STALE_SESSION_HOURS` **且**同專案逐字稿目錄**直下**另有
    `stem ≠ own_sid` 的 session 於 `own_last_epoch` 之後累積到 `should_arm` 門檻（24 回合且
    600 s，同一把「算不算真的工作」的尺：`claude -p ok` 不會被當成接手；`<sid>/subagents/`
    不是另一個 session）⇒ `{sid, turns, span_seconds, last_at}`，否則 `None`。

    fail 方向＝續航：任何量不到（目錄缺／讀不動／本 session 無對話記錄）一律 `None`——判
    SUPERSEDED 的後果是拆排程（不可逆），量不到≠已接手；整週無人（沒有更新的 session）也落在
    這側，行為與修前同。
    """
    import sentinel_lifecycle_arm  # noqa: PLC0415 — lazy（避開與 sentinel_lifecycle 的成環）

    if project_dir is None or own_last_epoch is None:
        return None
    if now.timestamp() - own_last_epoch < threshold(STALE_HOURS_KEY, env)[0] * 3600:
        return None
    return sentinel_lifecycle_arm.superseding_since(project_dir, own_sid, own_last_epoch)


def stale_for(transcript: Path | None, own_sid: str, now: datetime,
              fallback_dir: Path | None = None, *, env=None) -> dict | None:
    """接線層（哨兵與續航兩處共用）：由逐字稿路徑算 `own_last_at`／專案目錄，餵 `superseded_by`。
    專案目錄＝逐字稿所在目錄（在的話），否則 `fallback_dir`。"""
    project = transcript.parent if transcript is not None and transcript.is_file() else fallback_dir
    return superseded_by(project, own_sid, own_last_at(transcript), now, env=env)


def stale_verdict(stale: dict) -> dict:
    """`sentinel_decide` 的判決字典（鍵集合與既有 `disarm` 同形，另帶 `state`／`superseded_by`／
    `clear_halt`）：不 RESUME 也不 FRESH、自我解除、狀態寫 `superseded`。"""
    sid = str(stale.get("sid") or "")
    turns, span = stale.get("turns"), stale.get("span_seconds")
    return {"action": "disarm", "at": None, "state": "superseded", "superseded_by": sid,
            "clear_halt": True, "turns": turns, "span_seconds": span,
            "reason": (f"本 session 已閒置逾門檻，且同專案 session {sid[:8]} 於其後有 "
                       f"{turns} 回合／{span}s 的真實活動 ⇒ 判定已被接手：不續跑、"
                       "不降級開新 session，自我解除（整週無人時不會走到這裡）")}


def write_superseded_handback(sid: str, decision: dict) -> str:
    """寫一份 handback（四個 marker 齊備），讓下次 SessionStart 由既有 `announce_handbacks` 出聲。
    檔名 `<sid>_superseded.md`——不蓋掉同 sid 可能尚未讀的續跑 handback。寫不進去回 `""`（不拋）。"""
    other = str(decision.get("superseded_by") or "")
    seen = f"{decision.get('turns')} 回合／{decision.get('span_seconds')}s"
    body = (f"## 做了什麼\n判定 session {sid} 已被同專案 session {other} 接手（其後 {seen}），"
            "哨兵自我解除，**未續跑**。\n\n"
            "## 驗了什麼\n本 session 閒置超過門檻，且更新的 session 有真實活動；"
            "沒有探測額度、沒有 spawn。\n\n"
            "## 卡在哪\n無（這是正常下班，不是故障）。\n\n"
            f"## 下一步指令\n要手動續這個舊 session：`claude -r {sid}`；"
            f"要接新的：`claude -r {other}`。\n")
    path = resume_route.handback_report(f"{sid}_superseded")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
    except OSError:
        return ""
    return str(path)


def settle_superseded(plan: Path, state: dict, decision: dict, log: Path, append_log,
                      remove_task, write_relay, cleared: dict) -> int:
    """命中 SUPERSEDED 後的處置（`_sentinel_tick` 與 `_resume_tick` 共用，planner 只留一行）：
    狀態塊寫 `superseded`（終態）→ 清 halt 標記 → 拆排程 → 寫 handback → 落痕跡
    `sentinel_superseded`。回拆排程的 rc；不叫桌面告警（正常下班，不是故障）。
    寫狀態塊失敗不得擋住拆排程。"""
    import sentinel_lifecycle_arm  # noqa: PLC0415 — lazy

    sid = str(state.get("session_id") or "")
    state.update(state="superseded", **cleared)
    try:
        write_relay(plan, state)
    except OSError:
        pass
    cleared_halt = bool(decision.get("clear_halt")
                        and sentinel_lifecycle_arm.clear_halt_marker(sid))
    rc = remove_task(state["task_name"])
    append_log(log, "sentinel_superseded", unregister_rc=rc, why=decision["reason"],
               superseded_by=decision.get("superseded_by"), cleared_halt=cleared_halt,
               handback=write_superseded_handback(sid, decision))
    return rc
