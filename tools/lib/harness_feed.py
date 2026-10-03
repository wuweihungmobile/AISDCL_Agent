"""D32b-2（DEF-200-275 第七輪修後複審 Q-1）：狀態列 feed 的合併與 `--check` 旁註，
從 `tools/session_resume_planner.py` 抽出——那支檔的 `guardrail_cli` tier（≤750
計價行）本輪破線（760），本檔是抽走的那一份職責，不是新主題。

stdlib only（同 `tools/lib/endurance_env.py` 的既有慣例）：不 import
`context_budget_guard`，一律由呼叫端注入（`guard` 參數）。理由同該檔既有的
`_AUTOCOMPACT_KILL_ENVS` 說明——這裡只是「怎麼合併證據／怎麼印旁註」這個主題
的家，不是第二個知道怎麼判定 window 的地方；也讓根層 hook 的零相依契約不必
反過來 import 本檔。
"""
from __future__ import annotations

from pathlib import Path

#: DEF-200-408：差值非 0 最常見的成因是 feed 與逐字稿**各自獨立落盤**的時序差——status line
#: 先把新一則的 usage 寫進 feed，逐字稿那一則 assistant 記錄還沒寫完，下一次呼叫即歸零
#: （Windows 真機實測：一次印 差=15,580 ＝該則的 cache_creation，下一次 差=0）。少了這句，
#: 一個瞬間差值會被讀成「數字不符＝新缺陷」；差=0 時不附，免得每次都多一截噪音。
DIFF_HINT = "（差值非 0 常見於 feed 與逐字稿寫入時序差，下一次呼叫通常歸零；持續非 0 才需查）"

#: DEF-200-431：Claude Code 注入工具子行程（與 hook 子行程）環境的「本視窗 session id」。
#: 真機實測：PowerShell 工具內 `$env:CLAUDE_CODE_SESSION_ID` 即本視窗的逐字稿檔名。
SESSION_ID_ENV = "CLAUDE_CODE_SESSION_ID"
#: `pick_transcript()` 回的來源標籤（`session_line()` 原樣印給使用者看，不用猜這份數字是誰的）。
SOURCE_TRANSCRIPT = "參數 --transcript"
SOURCE_ARG = "參數 --session-id"
SOURCE_ENV = f"環境變數 {SESSION_ID_ENV}"
_LATEST_CAVEAT = "；同 slug 有多個視窗時可能不是本視窗，要精準請帶 --session-id"


def _plain_id(value: str) -> bool:
    """只認 ASCII 英數與 `-`／`_`：sid 不得變成路徑片段或 glob 萬用字元。"""
    bare = value.replace("-", "").replace("_", "")
    return bare.isascii() and bare.isalnum()


def _find_by_sid(base: Path, sid: str) -> tuple[Path | None, str]:
    """DEF-200-471：`<sid>.jsonl` 在哪，回 `(路徑或 None, 命中的他 slug 目錄名)`。
    本 slug 命中或找不到時，slug 名為空字串。

    逐字稿住在**啟動 cwd** 的 slug 目錄下，`base` 卻是 repo 根的 slug：從子目錄啟動的 session
    （例如 `AutoClaude/`）落在別的 slug，只看 `base` 就找不到、轉而讀到他窗。先看 `base`，再看
    同層其他 slug 目錄（多份取最近寫入者）；sid 不合格時不搜（glob 元字元不得進樣式）。
    """
    if (own := base / f"{sid}.jsonl").is_file():
        return own, ""
    if _plain_id(sid):
        hits = [p for p in base.parent.glob(f"*/{sid}.jsonl") if p.is_file()]
        if hits:
            newest = max(hits, key=lambda p: p.stat().st_mtime)
            return newest, newest.parent.name
    return None, ""


def _tag(source: str, slug: str) -> str:
    return source + (f"（跨 slug 命中 {slug}）" if slug else "")


def pick_transcript(base: Path, session_id: str | None, environ) -> tuple[Path | None, str]:
    """DEF-200-431：在逐字稿目錄 `base` 下決定「本視窗」是哪一支，回 `(路徑或 None, 來源標籤)`。

    優先序：`--session-id` 明示（本 slug → 同層他 slug 都沒有＝`None`，明示的參數不退用）→ 環境變數
    `CLAUDE_CODE_SESSION_ID` 且對應檔存在（同樣兩段查找，DEF-200-471）→ 最後修改（退用，只看本
    slug）。此前只有最後一階：掌舵者慣開多視窗，另一個視窗（或 headless `claude -p`）一寫檔就成為
    「最後修改」，`--check`／`--pace` 便讀到別人的逐字稿——連「重啟指令 claude -r <id>」都是別人的
    id，而「差=0」交叉比對看不出被劫持（feed 依 sid 取，跟著錯的逐字稿走）。環境變數只認
    `[A-Za-z0-9_-]`（不讓它變成路徑）。
    """
    if session_id:
        hit, slug = _find_by_sid(base, session_id)
        return hit, _tag(SOURCE_ARG, slug)
    env_sid = str(environ.get(SESSION_ID_ENV) or "").strip()
    if _plain_id(env_sid):  # 只認 ASCII 英數：docstring 與程式同一句話
        hit, slug = _find_by_sid(base, env_sid)
        if hit:
            return hit, _tag(SOURCE_ENV, slug)
    found = [p for p in base.glob("*.jsonl") if p.is_file()]
    latest = max(found, key=lambda p: p.stat().st_mtime) if found else None
    why = (f"{SESSION_ID_ENV}={env_sid} 對應的逐字稿不存在，已退用" if env_sid
           else f"未設 {SESSION_ID_ENV}")
    return latest, f"最後修改（{why}{_LATEST_CAVEAT}）"


def session_line(source: str, sid: str) -> str:
    """DEF-200-431：`--check`／`--pace`／任務書輸出的「session 來源」那一行。"""
    return f"session 來源＝{source}（sid={sid}）"


def measure(transcript: Path, guard) -> dict:
    """水位量測（純資料）。判定一律走 `guard`（`context_budget_guard`）的實作，
    本檔不重寫一份判準。

    `feed` 只讀一次（D32b-1a 同型修復）：`guard.window_evidence()` 收下已讀好的
    `feed`，不再自己重讀一次 status line 進料。

    `fresh_window`（DEF-200-425）＝新視窗首輪：逐字稿還沒有任何帶 usage 的 assistant 記錄（`used` 與
    `model` 皆 `None`），而 feed 這一側讀得通（`reason is None`＝存在、session 相符、window
    為正）。feed 有沒有 `current_usage` 不論：TUI 剛開時為 null；首輪自己的 `--check` 則實測
    遇到 feed 已有值、逐字稿仍無任何 usage 記錄（本機頂層逐字稿裡兩次真跑出 ❌ 的首輪
    `--check`，`check_lines()` 都回空，那只有 `harness_used` 非 None 才會發生；成因推測＝逐字稿
    要等整則回應收完才落盤，首輪的工具呼叫在那之前就跑了）。feed 不存在（reason 非空）分不出
    是新視窗還是欄位格式漂移 ⇒ 不算；逐字稿已見到 model 卻沒有可用 usage ⇒ 不算（格式漂移的
    警報要留著）。`endurance_env.check_report()` 只讀這個旗標，不 import 本檔。
    """
    used, peak, model = guard.scan_transcript(transcript)
    sid = guard.session_id_of(transcript)
    feed = guard.read_context_feed(sid, model)
    window, source = guard.resolve_window(
        peak, **guard.window_evidence(model, feed=feed))
    return {
        "session_id": sid,
        "transcript": str(transcript),
        "used": used,
        "peak_used": peak,
        "model": model,
        "window": window,
        "window_source": source,
        "harness_used": feed["used"],
        "harness_reason": feed["reason"],
        "fresh_window": (used is None and model is None and feed["reason"] is None
                         and not _has_any_assistant_record(transcript)),
        "may_block": guard.may_block(source),
        "ratio": (used / window) if (used is not None and window > 0) else None,
        "tier": guard.tier_of(used, window) if used is not None else None,
    }


def _has_any_assistant_record(transcript: Path) -> bool:
    """DEF-200-425 複審鏡 S1：`scan_transcript()` 只看含 `usage` 字樣的行，assistant 記錄若
    整個沒有 usage 鍵（欄位改名／只有 `<synthetic>` 記錄）`model` 也會是 None，`fresh_window`
    就把「欄位格式漂移」誤判成「新視窗」。這裡便宜地再掃一次：逐字稿裡**有任何** assistant
    記錄就不是新視窗（❌ 警報留著）。讀不到一律當「有」——方向是維持警報，不是靜音。"""
    try:
        with transcript.open(encoding="utf-8", errors="replace") as fh:
            return any('"type": "assistant"' in line or '"type":"assistant"' in line
                       for line in fh)
    except OSError:
        return True


def check_lines(data: dict) -> list[str]:
    """`--check` 要印的 harness 相關旁註（D32-4／D32b-3，一份判準給 CLI 與 hook 共用
    的道理見 `context_budget_guard.cross_check_note()`）：feed 有可比的 `used` 時印
    分子交叉比對；沒有時把 `harness_reason` 印出來（沒有 feed 也是一種 reason，不
    得被悄悄吞掉）。兩者互斥（`harness_used` 有值時 `harness_reason` 恆為 `None`，
    見 `context_budget_guard.read_context_feed()`）。

    🔴 R158（refute_q3q4ci.md §1a／§1d 反駁者實測）：compact 後、下一次 API 回應前的 round-label-ok
    空窗（官方契約 `current_usage: null`）會讓 `read_context_feed()` 同時回
    `used=None, reason=None`——這是該函式**唯一**兩欄同時為 `None` 的分支（其餘每一個
    「不採用」分支都會賦一個非空 `reason` 字串，見該函式最後一行與上面兩行對照）。
    此前這個分支落到 `return []`，連「不採用」這件事本身都被悄悄吞掉，違反本函式與
    `read_context_feed()` 自己 docstring 的設計意圖——現在補一行明講原因。新視窗首輪
    （TUI 剛開、第一次 API 回應之前）同樣是 `current_usage: null`，措辭因此兩種成因並列，
    不把根本沒 compact 過的新視窗說成 compact 後空窗。
    """
    if data.get("harness_used") is not None and data.get("used") is not None:
        diff = abs(data["harness_used"] - data["used"])
        line = f"harness used={data['harness_used']:,} 逐字稿 used={data['used']:,} 差={diff:,}"
        return [line + (DIFF_HINT if diff else "")]
    if data.get("harness_reason"):
        return [f"harness feed 未採用：{data['harness_reason']}"]
    if data.get("harness_used") is None and data.get("harness_reason") is None:
        return ["harness feed 存在但當下無 current_usage"
                "（新視窗尚無第一次 API 回應，或 compact 後空窗），本次無交叉比對"]
    return []


def _feed_model_family(transcript: Path, guard) -> str | None:
    """DEF-200-424（DEF-200-420 延伸）：新視窗首輪逐字稿還沒有任何 assistant 記錄
    （`scan_transcript` 回不出 model），模型只有 status line feed 知道——feed 在 TUI 啟動時
    就寫了 `model.id`，`current_usage` 為 null 也一樣。

    DEF-200-433：解析本體改走 `guard.read_context_feed()` 的 `note`（`model=<id>`，`model_family`
    是子字串比對，直接認得出家族），不再自己讀一次 feed 檔——PreToolUse hook 的退路（守衛不得
    import 本檔）用的正是同一條，三個消費者（hook／`--pace`／SessionStart 簡報）從此只有一種
    解析，不會在「feed 缺 `context_window_size`」這類邊角各說各話。

    feed 不存在、壞 JSON、`session_id` 不符、缺 `model.id`、認不出家族一律回 `None`（fail-soft）。
    """
    note = guard.read_context_feed(guard.session_id_of(transcript), None)["note"]
    return guard.model_family(note) or None


def active_model_of(transcript: Path | None, guard) -> str | None:
    """DEF-200-420：本 session 逐字稿最後跑過的模型家族字——與 PreToolUse hook
    （`context_budget_guard.py` 的 `active_model = model_family(scanned[2]) if
    scanned and scanned[2] else None`）同一組轉換規則，讓 `--pace` 與守衛看同一把尺。
    此前 `--pace` 沒有這一步，模型分軌軸（`MODEL_SCOPED_KINDS`）就一律被排除出 cap
    聚合，給出比守衛寬鬆的假數字（同一份快取下 `--pace` 與 `--pace --model fable`
    七軸讀數逐字相同，差異全來自 active_model 有無）。

    逐字稿優先：它有 model 字串就以它為準（與 hook 同尺）；只有逐字稿還沒有任何 assistant
    記錄（新視窗首輪）才退用 status line feed 的 `model.id`（`_feed_model_family`）。此前
    新視窗首輪 `--pace` 因此排除模型軸、印出比守衛寬鬆的 cap，等到第一則回應落盤後 hook
    才從逐字稿解到模型而收緊——同一個視窗前後兩種說法。DEF-200-433：hook 端此前只讀逐字稿
    （本函式的 docstring 曾宣稱與它同尺，新視窗首輪並不成立），現已補上同一條 feed 退路，
    兩邊才真的同尺（鎖：`ActiveModelFallsBackToFeedInTheGuardTest`）。

    `transcript` 為 `None`／不是檔案，或掃描途中出任何例外，一律回 `None`（fail-soft：
    解不出就維持既有「不確定 → 保守排除」行為，不用猜的頂替）。呼叫端的顯式 `--model`
    優先於本函式——本函式只補「沒給 `--model` 時」的自動推導。
    """
    if transcript is None:
        return None
    try:
        if not transcript.is_file():
            return None
        _, _, seen_model = guard.scan_transcript(transcript)
        if seen_model:
            return guard.model_family(seen_model) or None
        return _feed_model_family(transcript, guard)
    except Exception:
        return None


def start_model_of(payload: dict, transcript: Path | None, guard) -> str | None:
    """DEF-200-432：SessionStart 簡報額度行的 active model（`decide(active_model=…)` 用）。

    此前簡報的 `decide()` 一律沒帶 active_model ⇒ 新鮮快取下模型分軌軸被排除，簡報印
    `cap=4 band=notice`，同一份快取數秒後 `--pace`／守衛印 `cap=1 band=prepare`（Fable）。

    順序：payload 的 `model`（新視窗那一刻逐字稿檔常還沒建、feed 與 hook 賽跑差 0～1 秒，
    只有它保證在場；真機實測 headless `-p` 的 payload 不帶此鍵，互動式 startup／resume 為
    靜態閱讀所見、runtime 未擷取）→ 逐字稿存在時與 `--pace` 同一個函式（`active_model_of`，
    含它「逐字稿無 model 才退 feed」的規則）→ 逐字稿檔還不存在時直接查同 sid 的 feed
    （`active_model_of` 對不存在的檔回 None，故補直呼 `_feed_model_family`——它只取路徑的
    stem，不要求檔在）。皆解不出回 `None`＝與此前行為逐字相同。
    """
    family = guard.model_family(payload.get("model")) if isinstance(payload, dict) else ""
    if family or transcript is None:
        return family or None
    if transcript.is_file():
        return active_model_of(transcript, guard)
    return _feed_model_family(transcript, guard)
