"""喚醒鏈 G1＋G2（權限姿態／交接可見性）的胖身體——argv 組裝＋A-PRE 預檢＋handback 判準面。

施工圖＝docs/04_planning/PRD_Amendment_R113_WakeChain_LastMile.md §3(a)（v2.1.13，
2026-08-31 落款）。立案＝2026-08-30 深夜實戰：哨兵四段全通、無頭續跑窗口卻被無人核准
權限牆擋住（Write 新檔全擋，含 scratchpad 任務書）⇒ 收不了尾。機械根因＝spawn argv
兩路（RESUME／FRESH）皆無 `--permission-mode`。

WHY 住這裡而不是 `tools/session_resume_planner.py`：planner 的 `guardrail_cli` LOC
餘裕動工當下只剩 1 行（現查 `python AutoClaude/tools/check_loc_budget.py --json`），
施工圖 §5 判例「胖身體一律下 lib、planner 只留最小接線」。

兩個消費端，同一份 argv 真相：
  · `choose_resume_route()`（planner）——RESUME／FRESH 兩路 argv 由本檔組裝，
    權限姿態旗標因此**結構上**不可能只補到其中一路；
  · `_run_resume()`（planner）——spawn 前呼叫 `preflight_problem()`（A-PRE 增格，
    出處＝PRD_Amendment_R112_WakeChain.md §2 P-3 的喚醒 preflight 節）。

旗標存在性非憑印象：`--permission-mode`（acceptEdits 為合法 choice）與 `--settings`
皆已以本機 `claude --help` 正面核對（複審二輪 SD 實查，施工圖 §3(a) 落點段）。
"""
from __future__ import annotations

import json
from pathlib import Path

import endurance_env

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: 無頭 spawn 專屬的權限姿態檔（三層白名單載體：L1 可寫／L2 可跑／L3 永遠禁止）。
#: 刻意**不動**主 `.claude/settings.json`——無頭姿態塞主檔會讓互動 session 一起變寬，
#: 方向錯（施工圖 §3(a) 鍵名草案前言）。僅由 spawn argv 以 `--settings <本檔>` 載入。
UNATTENDED_SETTINGS = _REPO_ROOT / ".claude" / "settings.unattended.json"


def handback_dir() -> Path:
    """持久交接目錄（施工圖 §3(b) L1 ②；姿態檔 additionalDirectories 指向它）。

    v2.1.13 G2 批 (b)：解析**委派** `endurance_env.handback_dir_status()`（單一定義不得
    雙軌）——逃生口 `AUTOSDD_HANDBACK_DIR`、唯讀／建不出來時退回系統暫存，壽命與逃生口
    紀律與 `~/.autosdd/traces` 同一份 SSOT（§3(b)1「共用」判決）。G1 原版在此自帶
    `Path.home()` 字面，那就是第二個家，本批結清。
    """
    return endurance_env.handback_dir_status()[0]


# ─────────────────── v2.1.13 G2 批 (b)（施工圖 §3(b) 判準 2／4）：handback 交接檔判準面
#: 內容四項的機器可驗 marker（§3(b)2）。planner 後檢與 SessionStart 偵測
#: （`tools/lib/sentinel_lifecycle.py::announce_handbacks`）共用這一份——判準只有一個家。
HANDBACK_MARKERS = ("## 做了什麼", "## 驗了什麼", "## 卡在哪", "## 下一步指令")

#: mtime 比對的寬容秒數。FAT/exFAT 的 mtime 粒度是 2 秒、spawn 時刻與檔案系統時鐘另有
#: 次秒級偏差；不帶寬容會把剛寫好的交接檔誤判成 stale——假警報會讓人把整條警告關掉
#: （本 repo 對「擋到讓人無法工作的守衛」有判例）。代價＝spawn 前 2 秒內寫的舊檔會被
#: 當成本窗產物，而真實續跑窗以分鐘計，方向可接受。
_MTIME_SLACK_SECONDS = 2.0


def handback_report(session_id: str) -> Path:
    """本次續跑窗口的交接檔路徑（§3(b)1：`<handback 目錄>/<sessionId>.md`）。"""
    return handback_dir() / f"{session_id}.md"


def handback_verdict(report: str, spawn_at: float) -> str:
    """planner 側後檢三值（§3(b)4）：`written`／`missing`／`stale`。

    `written`＝存在 ∧ mtime ≥ spawn 時刻（帶 `_MTIME_SLACK_SECONDS` 寬容）∧ 四 marker
    齊；不存在（或 stat／讀取炸掉——量不到往保守側收，同誠實劃界第 6 條方向）＝
    `missing`；其餘（舊檔冒充、或四節不齊）＝`stale`。
    """
    path = Path(report) if report else None
    if path is None or not path.is_file():
        return "missing"
    try:
        fresh = path.stat().st_mtime >= spawn_at - _MTIME_SLACK_SECONDS
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "missing"
    ok = fresh and all(marker in text for marker in HANDBACK_MARKERS)
    return "written" if ok else "stale"


def handback_postcheck(route: dict, spawn_at: float, state: dict,
                       log, append_log, alert) -> str:
    """spawn 返回後的交接後檢（§3(b)4，**不依賴模型合作**）；回 verdict 供 `resumed` 記欄。

    非 `written` ⇒ resume log 落 `handback_missing` 事件＋`alert(..., loud=True)`——G2
    原事故形態＝交接只活在逐字稿與一則推播裡，人回來的終端零回饋（被消耗 9% 且不知情）。
    `append_log`／`alert` 由呼叫端注入：痕跡格式與叫人載體的家分別在 planner 與
    `quota_escalation`，本檔不抄第二份。
    """
    path = str(route.get("handback") or "")
    verdict = handback_verdict(path, spawn_at)
    if verdict != "written":
        append_log(log, "handback_missing", verdict=verdict, handback_path=path,
                   **alert(f"無頭續跑收窗但 handback 交接檔 {verdict}（{path}）——收窗前"
                           "必寫 handback 是 prompt 收尾義務（v2.1.13 G2），本窗交接不可見",
                           state, loud=True))
    return verdict


def _posture_argv() -> list[str]:
    # 🔴 順序約束：這一段必須排在 prompt 之後、`--add-dir` 之**前**——
    # `--add-dir <directories...>` 是變長參數，其後只准剩目錄值（姊妹鎖
    # test_the_variadic_add_dir_does_not_swallow_the_prompt 釘住整條 argv 的尾端形狀）。
    return ["--permission-mode", "acceptEdits", "--settings", str(UNATTENDED_SETTINGS)]


# v2.1.13 C5：settings 檔 `additionalDirectories` 的 `~` 展開 [需核對]（施工圖 §3(a)
# 草案註記②）——harness 是否展開 `~/.autosdd/handback` 這個字面無取證，且 handback
# 目錄的**實際**解析是動態的（`endurance_env.handback_dir_status()`：`AUTOSDD_HANDBACK_DIR`
# 逃生口覆寫／唯讀時退回系統暫存），靜態字面與動態現解可能分歧。修法（SD 複審建議）：
# spawn argv 組裝處**每次現解** `handback_dir()`，讓 L1② 不依賴 `~` 展開這個未經核對的
# harness 行為；settings 檔本身保留原樣字面（repo 檔不可寫死機器絕對路徑）。
# `--add-dir` 是變長參數，兩個目錄值放同一個旗標之後（而不是開第二個 `--add-dir`）——
# 尾端仍是「一個旗標＋其後全部剩餘值」的形狀，姊妹鎖只需認得值的**個數**變成 2。
def _add_dir_argv(task_dir: Path) -> list[str]:
    return ["--add-dir", str(task_dir), str(handback_dir())]


def resume_argv(claude: str, session_id: str, prompt: str, add_dir: Path) -> list[str]:
    """SESSION_RESUME 的完整 argv（prompt 在變長旗標之前；尾端＝--add-dir＋任務書目錄
    ＋現解後的 handback 目錄，v2.1.13 C5）。"""
    return [claude, "-p", "-r", session_id, prompt, *_posture_argv(),
            *_add_dir_argv(add_dir)]


def fresh_argv(claude: str, prompt: str, add_dir: Path) -> list[str]:
    """FRESH_SESSION_WITH_STATE 的完整 argv（不帶 `-r`，其餘形狀與 RESUME 路對稱）。"""
    return [claude, "-p", prompt, *_posture_argv(), *_add_dir_argv(add_dir)]


def preflight_problem(settings: Path | None = None) -> str | None:
    """A-PRE 權限姿態預檢：回 `None`＝通過；回字串＝拒 spawn 理由（呼叫端 fail-loud）。

    判準照施工圖，只有兩條：姿態檔**存在** ∧ **JSON 可解析**。缺席／壞檔時 spawn
    出去的無頭窗口會退回無人核准權限牆（G1 原事故形態），寧可不 spawn、留任務書給人
    ——呼叫端須落 `resume_authz_preflight_failed` 痕跡＋rc≠0＋stderr 出聲。

    通過時順帶 `mkdir` handback 目錄（施工圖批 (b) L1 ② 的前置；姿態檔
    additionalDirectories 指向它）。mkdir 失敗同樣回拒 spawn 理由——這是實作面的
    保守裁量（施工圖未明列此格）：目錄建不出來＝L1 ② 斷、交接檔無處落，方向與
    誠實劃界第 6 條「量不到 ≠ 可以，保守向收斂」同向。
    """
    path = UNATTENDED_SETTINGS if settings is None else settings
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return (f"unattended settings 檔缺席：{path}"
                "（G1 權限姿態載體不在，spawn 出去的無頭窗口收不了尾）")
    except (OSError, ValueError) as exc:
        return f"unattended settings 檔壞掉（讀取／JSON 解析失敗）：{path}——{exc}"
    try:
        handback_dir().mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return (f"handback 目錄建不出來：{handback_dir()}——{exc}"
                "（additionalDirectories 指向它，缺席＝交接檔無處落）")
    return None
