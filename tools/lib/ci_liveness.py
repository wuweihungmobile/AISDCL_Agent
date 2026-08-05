#!/usr/bin/env python3
"""GitHub Actions「逐軌」活性偵測（R68，tools/dev_start.py 的 CI 活性哨兵用）。

🔴 為何獨立成模組而不是留在 dev_start.py：
  ① **粒度缺陷本身**——原哨兵只跑 `gh run list --limit 1`（跨 workflow 取最新一筆），
     任何一次 push 的綠燈都會遮蔽週頻／日頻兜底軌的長期死亡。實測 2026-08-01：該哨兵
     印「✅ GitHub CI 活性正常」的同一刻，windows-compat-ci／macos-compat-ci 的
     schedule 軌已死 18 天。這是結構性偵測不到（週頻軌永遠不可能是「最新一筆」），
     不是機率問題，故必須改為逐軌查。
  ② **LOC**——dev_start.py 已逼近 DEF-101-271/274 的 2000 行「該輪必修」門檻
     （R68 現查 1918 行、餘裕 82 行）。把這段 ~70 行的新邏輯留在該檔會當場推過門檻，
     等於自己製造一筆必修債。行數守門見 AutoClaude/tools/check_loc_budget.py 的
     SPECIAL_FILES（R68 新增 `../tools/dev_start.py` 棘輪）。

期望軌與週期一律**現查** `.github/workflows/*.yml` 的 `on.schedule.cron`，不存第二份
會腐化的字面清單（DEF-101-289/515「文件寫死機器算得出的數字」同一家族）。
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

# 只匹配「未被註解掉」的 cron 行：行首 `#` 的 dormant 軌不會被誤列為期望軌。
_CRON_LINE_RE = re.compile(r"^\s*-\s*cron:\s*[\"']([^\"']+)[\"']", re.M)

# 陳舊判準：超過「cron 週期 × 本倍數」仍無成功 run 即視為該軌已死。取 2 是為了容忍
# 一次跳過（單次 runner 排隊／額度抖動不該一跑出來就吵）。
STALE_PERIOD_FACTOR = 2.0


def cron_period_days(expr: str) -> float:
    """粗估 cron 週期（天）：dow 指定→週頻 7、dom 指定→月頻 30、否則日頻 1。"""
    fields = expr.split()
    if len(fields) < 5:
        return 1.0
    return 7.0 if fields[4] != "*" else (30.0 if fields[2] != "*" else 1.0)


def scheduled_workflow_periods(root: Path) -> dict[str, float]:
    """{workflow 檔名: 期望間隔天數}；同檔多條 cron 取最短（最嚴）。"""
    out: dict[str, float] = {}
    for f in sorted((root / ".github" / "workflows").glob("*.yml")):
        try:
            crons = _CRON_LINE_RE.findall(f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if crons:
            out[f.name] = min(cron_period_days(c) for c in crons)
    return out


# 計入活性的事件：排程觸發，**加上**手動補跑。
# 🔴 R69（DEF-101-703）：原版只查 `schedule`，與「陳舊時該怎麼辦」的唯一處置
# （`gh workflow run <wf>.yml`，產生的是 `event=workflow_dispatch` 的 run）**實證互斥**
# ——照著處置做，哨兵仍看不到任何成功紀錄、照樣天天喊陳舊，於是它會被當成狼來了而被
# 忽略，正好複製它要消滅的那個病（root-infra-ci.yml 第 15 道同一處訂正）。
# 語意上兩事件也等價：兩者都會把 `*-nightly-full` 這個 job 真的拉起來跑（該 job 的
# `if:` 逐字就是 `schedule || workflow_dispatch`），對「這條通道還活著嗎」是等價證據。
_LIVENESS_EVENTS = ("schedule", "workflow_dispatch")


def _latest_success_run(workflow: str) -> str | None:
    """該 workflow 最近一次成功 run 的 updatedAt（ISO8601）；查不到回 None。

    掃 `_LIVENESS_EVENTS` 每個事件各取最近一筆成功，取其中**最新**者。ISO8601 的
    `...Z` 字串字典序即時序，故可直接 `max()`。
    任一事件查得到（含「查得到但零筆」＝空字串）就不算無訊號；**全部**事件都查失敗
    才回 None（無訊號 ≠ 壞訊號，見 `stale_schedule_tracks` docstring）。
    """
    stamps: list[str] = []
    saw_signal = False
    for event in _LIVENESS_EVENTS:
        try:
            r = subprocess.run(
                ["gh", "run", "list", "--workflow", workflow, "--event", event,
                 "--status", "success", "--limit", "1", "--json", "updatedAt"],
                timeout=10, capture_output=True, encoding="utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            continue
        if r.returncode != 0:
            continue
        try:
            runs = json.loads(r.stdout or "[]")
        except ValueError:
            continue
        saw_signal = True
        try:
            if runs:
                stamps.append(runs[0]["updatedAt"])
        except (TypeError, KeyError, IndexError):
            continue
    if not saw_signal:
        return None
    return max(stamps) if stamps else ""


# ── R71 D-2：「最近一次**嘗試**」軸（與上面的「最近一次**成功**」軸互補）──────
#
# 🔴 為何一個軸不夠：`_latest_success_run` 帶 `--status success`，於是三種處置完全
# 不同的狀態被壓成同一句「最近成功於 N 天前」：
#   (a) cron 根本沒觸發（帳務阻擋／workflow 被停用）→ 去看帳務／workflow state；
#   (b) 觸發了但 run 紅（真的測試壞了）           → 去看那次 run 紅在哪；
#   (c) 週頻軌還沒輪到                            → 什麼都不用做。
# 混成一句話等於沒有診斷價值。本軸**不帶** `--status`，直接回報最近一次 run 的結論。
#
# 🔴 為何是**新增**一個軸而不是改掉舊的：`_latest_success_run` 的「兩事件取較新」
# 語意是 DEF-101-703 的修復本體（處置指令 `gh workflow run` 產生的 dispatch run
# 必須算數，否則閘門解不開）。把它改成 schedule-only 就是讓那個死鎖復發。兩軸並存
# ⇒ 主判準不變，但陳述句能分辨「誰讓它變新鮮的」。
def _latest_attempt(workflow: str, event: str = "schedule") -> dict[str, str] | None:
    """該 workflow 在 `event` 下最近一次 run（**不分結論**）。

    回傳三態，缺一即回到「無訊號 ≠ 壞訊號」被壓平的原病：
      · `None` ＝ 無訊號（gh 不在／逾時／rc≠0／回應無法解析）；
      · `{}`   ＝ 查得到但**零筆**（該事件從未產生過任何 run ⇒ cron 沒觸發）；
      · dict   ＝ `conclusion`／`createdAt`／`updatedAt`／`url` 四鍵（值恆為 str，
                  尚未結束的 run `conclusion` 為 `null` ⇒ 正規化成空字串）。
    """
    try:
        r = subprocess.run(
            ["gh", "run", "list", "--workflow", workflow, "--event", event,
             "--limit", "1", "--json", "conclusion,createdAt,updatedAt,url"],
            timeout=10, capture_output=True, encoding="utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    try:
        runs = json.loads(r.stdout or "[]")
    except ValueError:
        return None
    if not isinstance(runs, list):
        return None
    if not runs or not isinstance(runs[0], dict):
        return {}
    return {k: str(runs[0].get(k) or "")
            for k in ("conclusion", "createdAt", "updatedAt", "url")}


def _attempt_suffix(att: dict[str, str] | None) -> str:
    """把「最近一次嘗試」軸接到陳舊訊息尾巴——(a)/(b)/(c) 的可分辨性就在這一句。"""
    if att is None:
        return ""  # 無訊號：不編造，保持原句
    if not att:
        return "；schedule 軌**從未產生過任何 run**（cron 沒觸發／workflow 被停用，非測試紅）"
    url = f" {att['url']}" if att.get("url") else ""
    return (f"；schedule 軌最近一次觸發於 {att.get('createdAt') or '?'}、結論 "
            f"{att.get('conclusion') or '(尚未結束)'}{url}")


def _schedule_axis_note(agg: str, att: dict[str, str] | None) -> str | None:
    """D-3／D-5：run 層判定為「新鮮」時，那份新鮮度是不是**排程軌自己**掙來的。

    D-3（遮蔽）：`_LIVENESS_EVENTS` 含 `workflow_dispatch` 是刻意的（DEF-101-703），
    但副作用是**一次手動補跑成功就買到 `STALE_PERIOD_FACTOR × period` 天的靜默**。
    2026-08-03 唯讀 gh 實查，這件事**正在發生**：`aisdlc-sdd-arch-fitness.yml` 於
    2026-08-02T14:24 被一次 workflow_dispatch「治好」了警告，而它的 schedule 軌
    最後一次成功是 2026-07-14、最近一次觸發（2026-07-27）是 failure。
    本函式讓 dispatch 繼續計入主判準（死鎖不復發），但把「排程軌本身已死」單獨說出來。

    D-5（同一函式順手覆蓋）：`STALE_PERIOD_FACTOR=2.0` 讓週頻軌的門檻是 14 天，
    結構上不可能「當場發現」。本函式不動那個門檻（動它會讓「容忍一次跳過」的
    `test_weekly_track_tolerates_one_skip` 失去理由、哨兵回到天天狼來了），改為：
    只要**最近一次排程觸發已經紅了、且晚於被採計的最後成功**，就當場出聲——
    「cron 觸發後 run 紅」不是「跳過一次」，不該被容忍窗吃掉。
    """
    if att is None:
        return None
    if not att:
        return ("目前的成功紀錄**不是排程軌掙來的**：該 workflow 從未產生過任何 "
                "schedule run（cron 沒觸發／workflow 被停用），新鮮度只可能來自 "
                "workflow_dispatch 手動補跑")
    concl = att.get("conclusion") or ""
    if concl == "success":
        return None  # 排程軌自己最近一次就是綠的 ⇒ 沒有遮蔽、也沒有新的紅
    if not concl:
        return None  # 尚未結束（GitHub 對 queued/in_progress 的 conclusion 為 null）
    when = att.get("createdAt") or "?"
    url = f" {att['url']}" if att.get("url") else ""
    stamp = att.get("updatedAt") or att.get("createdAt") or ""
    if stamp and stamp > agg:
        # D-5：排程觸發**晚於**被採計的最後成功且已轉紅 ⇒ 這是新鮮的壞消息，
        # 不該被 STALE_PERIOD_FACTOR 的容忍窗吃掉（容忍的是「跳過一次」，不是
        # 「跑了而且紅了」）。
        return (f"schedule 軌最近一次觸發於 {when}、結論 {concl}，且**晚於**被採計的"
                f"最後成功（{agg}）⇒ 排程軌剛轉紅，別等容忍窗到期才看{url}")
    # D-3：被採計的最後成功晚於最近一次排程觸發，而那次觸發是紅的 ⇒ 那份新鮮度
    # 只可能來自 workflow_dispatch（`_LIVENESS_EVENTS` 的另一半）。
    return (f"run 層判定為新鮮，但那份新鮮度**不是排程軌掙來的**：schedule 軌最近一次"
            f"觸發於 {when}、結論 {concl}，其後排程軌未再成功；被採計的最後成功"
            f"（{agg}）晚於該次 ⇒ 只可能來自 workflow_dispatch 手動補跑{url}")


# ── R71 E-1：同檔多條 cron 驅動**不相交** job 集合 ⇒ run 層結論天生分辨不出 ──────
#
# 實證（2026-08-03 唯讀 gh 實查，零 Actions 額度）：`autoclaude-ci.yml` 有兩條 cron，
# `7 2 * * 1` 驅動 pg-e2e-nightly + perf-baseline、`7 3 * * 1` 驅動 mutation-TG。
# 被本模組採計為「最後一次成功」的 run 29308467958 裡，PG E2E 與 Perf Baseline 的
# `conclusion=skipped`、`steps=0`——它根本沒跑那兩個 job；而同一天 `7 2` 那次
# （run 29306905483）Perf Baseline 是 `failure`、`steps=11`＝真實測試紅。
# 於是 `7 3` 的綠**遮蔽**了 `7 2` 的死亡，而 `scheduled_workflow_periods` 以**檔案**
# 為單位、多 cron 取 min，兩層粒度對不上，run 層永遠看不出來。
#
# 誠實劃界：本函式做的是**靜態結構偵測**（宣告「這支檔的 run 層判定不構成證據」），
# **不是**逐 cron 軌的活性量測——後者需要對每個候選 run 再打一次 `gh run view --json
# jobs` 逐 job 比對，成本與 dev_start 的 25 秒掃描預算不成比例。要真正消滅這個盲區，
# 治本是把兩條 cron 拆成兩支 workflow 檔（那樣 run 層粒度就等於軌粒度）。
_JOB_ID_RE = re.compile(r"^  (?P<jid>[A-Za-z0-9_][A-Za-z0-9_-]*):\s*$")
_JOB_NAME_RE = re.compile(r"^    name:\s*(?P<name>.+?)\s*$")
_SCHEDULE_EQ_RE = re.compile(r"github\.event\.schedule\s*==\s*'([^']+)'")


def cron_job_map(path: Path) -> dict[str, list[str]]:
    """{cron 表達式: 受該條驅動的 job 顯示名清單}；靜態解析 workflow YAML，零網路。

    只認 job 層 `if:` 內的 `github.event.schedule == '<expr>'`——那是 GitHub Actions
    唯一能把 job 綁到特定 cron 的寫法，因此也是唯一可靠的靜態判準。
    """
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    out: dict[str, list[str]] = {}
    label = ""
    for ln in lines:
        m = _JOB_ID_RE.match(ln)
        if m:
            label = m.group("jid")
            continue
        if not label:
            continue
        nm = _JOB_NAME_RE.match(ln)
        if nm:
            label = nm.group("name").strip().strip("\"'")
            continue
        if ln.startswith("    if:"):
            for expr in _SCHEDULE_EQ_RE.findall(ln):
                if label not in out.setdefault(expr, []):
                    out[expr].append(label)
    return out


def multi_cron_blind_spot(root: Path, workflow: str) -> str | None:
    """該 workflow 是否存在 E-1 形態的 run 層盲區；沒有就回 None（零噪音）。"""
    mapping = cron_job_map(root / ".github" / "workflows" / workflow)
    if len(mapping) < 2:
        return None
    sets = [frozenset(v) for v in mapping.values()]
    if all(s == sets[0] for s in sets):
        return None  # 多條 cron 但驅動同一組 job ⇒ run 層結論仍然代表得了它們
    detail = "；".join(f"`{c}`→{sorted(j)}" for c, j in sorted(mapping.items()))
    return (f"{workflow}（結構性偵測盲區：{len(mapping)} 條 cron 驅動**不相交**的 job "
            f"集合——{detail}。run 層結論只要其中一條的 run 綠就整體算綠，另一條的死亡"
            f"會被遮蔽 ⇒ 本模組對這支檔的「新鮮」判定不構成證據。治本＝拆成兩支 "
            f"workflow 檔，讓 run 粒度等於軌粒度）")


# ── R74 DEF-101-703 殘留：`continue-on-error: true` 讓 run 層結論**結構上**看不到紅 ──
#
# 🔴 這是本模組最嚴重的一種假綠，而且是**活體**（本輪唯讀實查磁碟即可證，零網路）：
# `_latest_success_run` 的判準是「該 workflow 有沒有 `--status success` 的 run」。
# 但 `.github/workflows/windows-compat-ci.yml` 的 `windows-nightly-full` 帶
# **job 層 `continue-on-error: true`**（該檔檔頭逐字寫著「非阻斷」），語意就是
# 「這個 job 紅了不要影響 run 結論」⇒ 深度回歸整包爛掉，run 仍然是 success，
# 於是哨兵**照樣判新鮮、照樣不出聲**。三道 R69/R71 偵測（D-2 嘗試軸／D-3 遮蔽／
# E-1 多 cron）沒有一道看得到它：那三道問的都是「有沒有 run／run 是哪個事件帶來的
# ／run 結論代不代表這條軌」，而這一筆的病在**run 結論本身就不代表那個 job**。
#
# 誠實劃界（與 `multi_cron_blind_spot` 同款，刻意不假裝在量測）：本函式做的是
# **靜態結構偵測**——宣告「這支檔的 run 層綠燈不構成該 job 健康的證據」，
# 而不是去問那個 job 這次到底紅不紅（後者要對候選 run 再打一次
# `gh run view <id> --json jobs`，且必須先取得 run id，成本與 dev_start 的 25 秒
# 掃描預算不成比例）。**但宣告本身就消滅了假綠**：讀者不會再把 ✅ 讀成
# 「深度回歸也綠」，而處置指令就寫在訊息裡。
#
# 為何**不**把這類 workflow 從活性判準裡剔除：那會讓 DEF-101-703 的死鎖復發
# （剔除後它永遠「查無成功 run」⇒ 天天喊、被當狼來了）。主判準不動，只加一句自白。
#: 🔴 **job 層 `continue-on-error: true` 的唯一判準（SSOT）**。R76 複審 SA-02 之前，
#: 這條正則有**兩份逐字相同的複本**（本檔 ＋
#: `tools/tests/test_doc_loc_baseline_freshness_r60.py::_JOB_FAIL_OPEN_RE`），且兩份
#: 都寫成 `…true\s*$`＝**行尾不得有註解**。磁碟上當時就有一個活體逃逸案例：
#: `.github/workflows/autoclaude-pg-e2e-on-label.yml:35` 是
#: `    continue-on-error: true  # 同 nightly：警示不阻塞 PR merge`——YAML 最普通的寫法，
#: 兩支消費者同時失明。實測：對 `windows-compat-ci.yml` 的那一行加個行尾註解，本檔的
#: `non_blocking_scheduled_jobs()` 就從回報一筆變成回報零筆，R74 那道「run 層 fail-open
#: 自白」跟著一起啞掉。故 (a) 容許行尾註解、(b) 兩處合併成本常數一份（掌舵者第 2 點
#: 「不重複模組」；先例＝`archive_defect_log.ACTIVE_STATUS_RE = _ledger_index.ACTIVE_STATUS_RE`）。
#: 射程仍刻意只認**恰 4 空白縮排**（＝job 層）與**字面 `true`**：step 層縮排更深、
#: `${{ … }}` 運算式判不出真假值，兩者皆出射程（後者若出現，判準會漏——已知邊界）。
JOB_FAIL_OPEN_RE = re.compile(r"^    continue-on-error:\s*true\s*(?:#.*)?$")
_JOB_CONTINUE_ON_ERROR_RE = JOB_FAIL_OPEN_RE
_EVENT_GATED_RE = re.compile(r"github\.event_name\s*==\s*'(?:schedule|workflow_dispatch)'")


def non_blocking_scheduled_jobs(path: Path) -> list[str]:
    """該 workflow 內「只在 schedule／workflow_dispatch 跑」且 job 層非阻斷的 job 名。

    兩個條件都必要：
      · **非阻斷**（`continue-on-error: true`）⇒ 它紅了 run 仍是 success；
      · **只在排程／手動觸發**⇒ 它正是本模組宣稱在守的那條軌，而 push 觸發的 job
        紅了會讓 run 紅、本來就看得見，納入只會製造噪音。
    """
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out: list[str] = []
    label, non_blocking, event_gated = "", False, False
    for ln in [*lines, "  _sentinel_:"]:  # 尾端哨兵：讓最後一個 job 也被結算
        m = _JOB_ID_RE.match(ln)
        if m:
            if label and non_blocking and event_gated:
                out.append(label)
            label, non_blocking, event_gated = m.group("jid"), False, False
            continue
        if not label:
            continue
        nm = _JOB_NAME_RE.match(ln)
        if nm:
            label = nm.group("name").strip().strip("\"'")
            continue
        if _JOB_CONTINUE_ON_ERROR_RE.match(ln):
            non_blocking = True
        elif ln.startswith("    if:") and _EVENT_GATED_RE.search(ln):
            event_gated = True
    return out


def run_level_fail_open(root: Path, workflow: str) -> str | None:
    """該 workflow 的 run 層結論是否**結構上**遮蔽得住排程軌的紅；沒有就回 None。"""
    jobs = non_blocking_scheduled_jobs(root / ".github" / "workflows" / workflow)
    if not jobs:
        return None
    return (f"{workflow}（**run 層 fail-open**：{sorted(jobs)} 為 job 層 "
            f"`continue-on-error: true` ＋ 只在 schedule／workflow_dispatch 觸發 ⇒ "
            f"該 job 整包紅掉時 run 結論仍是 success，而本模組的活性判準帶 "
            f"`--status success` ⇒ **哨兵會把紅讀成綠**。本行不是量測值、是結構宣告："
            f"要知道那個 job 這次到底紅不紅，看該 workflow 的 `*-nightly-alert` job "
            f"或 `gh run view <run-id> --json jobs`；**不得**把上方的新鮮判定讀成"
            f"「深度回歸也綠」）")


def _scan_order(periods: dict[str, float], ref: datetime) -> list[tuple[str, float]]:
    """掃描順序：依日期輪轉起點（R71 E-2）。

    🔴 為何不能用固定字典序：`stale_schedule_tracks` 每軌前先檢查掃描預算、超時即
    `break`，而 `scheduled_workflow_periods` 用 `sorted()` ⇒ 順序固定 ⇒ **排最後的
    那支永遠第一個被丟掉**。實測本 repo 的 7 支含 cron workflow 排序後最後一名正是
    `windows-compat-ci.yml`——也就是說，這個哨兵的系統性盲區恰好落在它最該看的那一支
    （DEF-101-703 的主角）。以 `ref` 的日序輪轉起點後，截斷面隨日期均攤、任何一軌都
    不會被永久跳過；`ref` 可注入 ⇒ 本行為可被機械驗證，不是靠隨機。
    """
    items = sorted(periods.items())
    if not items:
        return []
    offset = ref.toordinal() % len(items)
    return items[offset:] + items[:offset]


def stale_schedule_tracks(root: Path, deadline: float,
                          now: datetime | None = None) -> list[str]:
    """逐軌查活性，回傳需要人看一眼的描述清單（空 list＝全部新鮮／全部查不到）。

    `deadline`＝`time.monotonic()` 基準的總預算上限（多次 gh 呼叫可能各約 1 秒），
    超時即中止掃描——本哨兵是 advisory，寧可少報也不可拖住開工流程。
    查不到（gh 失敗／逾時／回應無法解析）一律**跳過而非報陳舊**：無訊號 ≠ 壞訊號。

    R71 起回傳的清單含三類項目（全部都是「請人看一眼」，不只是「陳舊」）：
      ① 陳舊軌（判準與 R68/R69 完全相同，尾巴多接「最近一次嘗試」軸供分辨 a/b/c）；
      ② 新鮮但**新鮮度不是排程軌掙來的**（D-3 遮蔽／D-5 排程觸發後轉紅）；
      ③ 掃描面本身的自白：預算截斷未查了哪幾軌（E-2）、哪支檔的 run 層判定
         結構上不構成證據（E-1 多 cron／R74 `continue-on-error` run 層 fail-open）。
         **未查 ≠ 健康**，靜默截斷正是哨兵自己的盲區。
    """
    ref = now or datetime.now(UTC)
    findings: list[str] = []
    tracks = _scan_order(scheduled_workflow_periods(root), ref)
    for index, (wf, period) in enumerate(tracks):
        if time.monotonic() > deadline:
            skipped = [name for name, _ in tracks[index:]]
            findings.append(
                f"掃描未完成——預算用盡，{len(skipped)} 軌未查（{'／'.join(skipped)}）："
                "其狀態**未知**，不是健康。起掃點依日期輪轉，下次會換一批先查")
            break
        blind = multi_cron_blind_spot(root, wf)
        if blind:
            findings.append(blind)
        fail_open = run_level_fail_open(root, wf)
        if fail_open:
            findings.append(fail_open)
        ts = _latest_success_run(wf)
        if ts is None:
            continue
        att = _latest_attempt(wf)
        if ts == "":
            findings.append(f"{wf}（查無任何成功的 schedule／workflow_dispatch run）"
                            + _attempt_suffix(att))
            continue
        try:
            when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        age = (ref - when).total_seconds() / 86400.0
        if age > STALE_PERIOD_FACTOR * period:
            findings.append(f"{wf}（最近成功於 {age:.0f} 天前，cron 週期 {period:.0f} 天）"
                            + _attempt_suffix(att))
            continue
        note = _schedule_axis_note(ts, att)
        if note:
            findings.append(f"{wf}（{note}）")
    return findings
