"""ONBOARDING §7 表② 逐平台欄的**基線三態**語意，與 nightly 落地產物的唯讀探針。

抽出成獨立模組的理由（R70）：`tools/sync_onboarding_baselines.py` 受 ADR-SD08-001 的
**shrink-only 行數棘輪**管轄（`AutoClaude/tools/check_loc_budget.py` 的 `SPECIAL_FILES`），
該棘輪明訂「先刪死碼／抽共用模組（先例：`tools/lib/ci_liveness.py`），確認為不可壓縮的
真實功能後才具名調高」。本模組即依該先例抽出；呼叫端只留薄包裝。

本模組全部是**純函式 ＋ 一支唯讀檔案探針**，不 import 呼叫端，故無循環相依。

═══════════════════════════════════════════════════════════════════════════════
🔴 事故先於設計，逐字記錄（DEF-101-756）
═══════════════════════════════════════════════════════════════════════════════
R70 主控讀 `--check-snapshot` 印出的「Windows 欄**尚未建立基線**（provenance 四項全為
unrecorded）」，據此宣稱「**Windows 側從未有真機輪**」  <!-- stale-premise-ok: 逐字保全原話 -->
——被使用者當場以開發史
駁回：本 repo 本來就是在 Windows 上開發的（R20／R42／R59／R64／R66 皆為 Windows 真機輪，
每日 02:00 另有 Windows Task Scheduler 的 nightly 全套回歸）。而**同一份輸出的下三行就印著
Windows 欄的 `3767 passed / 208 skipped`**，那正是 Windows 實機量得的值——訊息與它自己的
資料自相矛盾，而讀者採信先看到的那一句。

根因：**用同一個 `unrecorded` 同時表達兩件相反的事**——
  ① 該平台**從未量測**  → **平台覆蓋缺口**，只能去那台機器跑一輪才補得起來
  ② 該平台**量測過，但早於 provenance 機制** → **後設資料缺口**，量測本身仍然有效
而輸出一律用①的措辭。**缺 provenance ≠ 缺量測**：前者補記錄，後者要真的去跑；把後者
寫成前者，就是把「不知道在什麼環境量的」講成「不知道有沒有量過」。

判準刻意**不**新增一個要人手宣告「量過沒」的旗標——那只會是下一個會漂移的手寫真相。
「有沒有量過」由**表② 該欄有沒有裝著數字**決定：數字本身就是量測存在的證據。
`baseline-origin` 只回答「這些數字是**哪一種來源**」，並與前者交叉驗證（`validate_state`）
⇒ **宣告「從未量測」而表上卻有數字，在結構上會 fail-loud**，那正是本次事故的那句話。
"""

from __future__ import annotations

import datetime
from pathlib import Path

# 「該欄的量測樹已不可考」的合法佔位值：**刻意讓它與任何 live 指紋都不相等**，於是該欄
# 恆判 presumed stale。這比填一個猜的指紋誠實——猜的指紋會讓一欄假裝新鮮。
UNRECORDED = "unrecorded"

# 量測**環境** provenance（缺任一欄即 fail-loud）：docker／pgextras 各自都會改變計數
# （docker 停用 → v0.01／v0.30 各 −3；PG extras 存在 → AutoClaude PG-gated 測試由 skip
# 轉 pass 使 passed 虛高），不入帳就是下一位驗證者把環境差異誤判為退化。
ENV_PROVENANCE_FIELDS: tuple[str, ...] = ("measured-at", "host", "docker", "pgextras")

ORIGIN_FIELD = "baseline-origin"
ORIGIN_SELF = "self-recorded"                     # 本工具當場記錄，env provenance 四項齊全
ORIGIN_PRE_MECHANISM = "pre-provenance-mechanism"  # 量測過，但早於機制 ⇒ env 不可考
ORIGIN_NEVER = "never-measured"                   # 真的沒量過（表② 該欄必須也沒有數字）
ORIGIN_VALUES: tuple[str, ...] = (ORIGIN_SELF, ORIGIN_PRE_MECHANISM, ORIGIN_NEVER)

# 🔴 **新增 provenance 欄位時的回溯紀律（本次事故的根因 (b)）**：R67 引入 provenance 機制
# 時，既有的 Windows 欄資料**沒有被回溯處理**，只是整欄填 `unrecorded` 了事 ⇒「機制引入前
# 就存在的量測」與「不存在的量測」變成同一個字。`ORIGIN_FIELD` 之所以列入必備欄位
# （缺席即 fail-loud），就是要讓**下一次有人加欄位時，既有欄非表態不可**：它無法靠沉默通過。
PROVENANCE_FIELDS: tuple[str, ...] = (*ENV_PROVENANCE_FIELDS, ORIGIN_FIELD)

# 平台覆蓋的權威來源。**基線工具不是**——它只知道「這一欄的數字在什麼環境量的」。
# 逐字寫進訊息裡，讓下一個讀者不必再從 provenance 欄位反推平台覆蓋。
COVERAGE_SOURCES = (
    "docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md §6 逐輪覆蓋表"
    "／docs/06_quality/AutoSDD_Defect_Log.md 的「發現情境」欄／ONBOARDING.md §8 nightly"
)

# ── nightly 落地產物：每日在該平台真機跑完整回歸的證據（DEF-101-757）──────────────
#
# 🔴 **這是 DEF-101-756 事故裡「證據明明每天都在產生、卻沒有任何通道流進判定」的那一半。**
# 每日 02:00 的 nightly 排在 **Windows 11 真機**的 Task Scheduler（`AutoClaude_Nightly`，
# 見 `tools/install_windows_nightly.ps1`）。那是本 repo **最密集的平台真機證據來源**——
# 每天一輪完整回歸——而在本輪之前**沒有任何工具或文件讀過它**：基線工具的 provenance 只認
# 「有人手動跑過 `--write --with-slow`」，`dev_start` 的心跳哨兵只讀**本機平台那一支**
# （在 macOS 上結構上看不到 Windows 那支），`install_mac_nightly.sh --status` 的缺跑掃描
# glob 是 `nightly_mac_*` ⇒ 連檔名都對不上 Windows 家族。於是「這台機器每天凌晨都在跑」
# 對判定完全隱形。
#
# 本探針刻意**兩個平台的心跳檔都讀**（不看 `sys.platform`），且**不新增任何要人維護的
# 站點**——讀的就是 nightly 自己每晚會寫的落地產物。誠實劃界寫死在輸出裡：心跳檔是
# untracked（`AutoClaude/.gitignore: logs/`）、14 天輪替、只存在於產出它的那台機器上，
# 故**「本機看不到」只代表「這台機器不是它」，絕不代表「那個平台沒在跑」**——把後者寫成
# 結論，就是 DEF-101-756 換一個載體復發。
NIGHTLY_HEARTBEATS: dict[str, str] = {
    "win32": "AutoClaude/logs/nightly_latest.log",
    "darwin": "AutoClaude/logs/nightly_mac_latest.log",
}


def validate_state(label: str, prov: dict[str, str], measured: bool, fix: str) -> str:
    """回傳 `ORIGIN_VALUES` 之一；**宣告與資料矛盾一律 fail-loud**（DEF-101-756 的機械鎖）。

    每一種矛盾都會讓讀者得到與事實相反的結論：
      - 宣告 `never-measured` 而表② 有數字 ⇒ 就是本次事故那句「該平台從未量測」；
      - 宣告有量測而表② 抽不到數字     ⇒ 反向的假宣稱（表上沒有的東西被說成有）；
      - 宣告 `self-recorded` 而 env 欄位卻是 `unrecorded` ⇒ 假裝有 provenance；
      - 宣告 `pre-provenance-mechanism` 而 env 欄位有值 ⇒ 那就不是機制引入前的資料，
        該改宣告 `self-recorded`，否則等於自願放棄一份已經有的 provenance。
    """
    origin = prov[ORIGIN_FIELD]
    if origin not in ORIGIN_VALUES:
        raise AssertionError(
            f"{label} 欄的 {ORIGIN_FIELD}={origin!r} 不是合法值 ⇒ 無從判斷該欄是"
            f"「沒量過」還是「量過但 provenance 不可考」，而這兩者的處置相反。\n{fix}"
        )
    recorded_env = [f for f in ENV_PROVENANCE_FIELDS if prov[f] != UNRECORDED]
    if origin == ORIGIN_NEVER and measured:
        raise AssertionError(
            f"{label} 欄宣告 {ORIGIN_NEVER}，但 §7 表② 該欄四格都裝著實測數字 ⇒ "
            f"**這正是 DEF-101-756 那句被使用者駁回的錯話**（「該平台從未有真機輪」，"
            f"而表上的數字正是該平台實機量得的）。缺 provenance 不等於缺量測。\n{fix}"
        )
    if origin != ORIGIN_NEVER and not measured:
        raise AssertionError(
            f"{label} 欄宣告 {origin}（＝量測存在），但 §7 表② 該欄抽不到完整數字 ⇒ "
            f"宣稱有一份表上並不存在的量測。\n{fix}"
        )
    if origin == ORIGIN_SELF and len(recorded_env) != len(ENV_PROVENANCE_FIELDS):
        raise AssertionError(
            f"{label} 欄宣告 {ORIGIN_SELF}（＝當場記錄），但 env provenance 有 "
            f"{sorted(set(ENV_PROVENANCE_FIELDS) - set(recorded_env))} 仍是 {UNRECORDED}"
            f" ⇒ 假裝有一份其實沒有的 provenance。\n{fix}"
        )
    if origin == ORIGIN_PRE_MECHANISM and recorded_env:
        raise AssertionError(
            f"{label} 欄宣告 {ORIGIN_PRE_MECHANISM}（＝機制引入前、環境不可考），"
            f"但 {recorded_env} 其實有值 ⇒ 白白丟掉一份已經有的 provenance。\n{fix}"
        )
    return origin


def measurement_age_days(measured_at: str) -> int | None:
    """`measured-at` 距今天數；`unrecorded` 或無法解析（人手寫壞）時回 None，不猜。"""
    try:
        return (datetime.date.today() - datetime.date.fromisoformat(measured_at)).days
    except ValueError:
        return None


def status_line(label: str, prov: dict[str, str], state: str) -> str:
    """該欄基線狀態的**單行**人話。三態措辭必須彼此不可混淆——這是本模組的全部重點。"""
    if state == ORIGIN_NEVER:
        return (
            f"{label} 欄**從未量測**（表② 該欄無數字、{ORIGIN_FIELD}={ORIGIN_NEVER}）"
            f"——這是**平台覆蓋缺口**，只能在該平台實跑一輪才補得起來"
        )
    if state == ORIGIN_PRE_MECHANISM:
        return (
            f"{label} 欄**已有實機量測基線**（表② 該欄裝著該平台實機量得的數字），"
            f"但量測早於 provenance 機制 ⇒ **量測環境不可考**"
            f"（{'／'.join(ENV_PROVENANCE_FIELDS)} 皆 {UNRECORDED}）。"
            f"🔴 這是 **provenance 缺口，不是平台覆蓋缺口**——"
            f"**不得**據本行宣稱「{label} 從未驗證過／從未有真機輪」"
            f"（DEF-101-756：主控就是這樣誤判並向使用者做出錯誤平台建議的）；"
            f"平台覆蓋請查 {COVERAGE_SOURCES}"
        )
    age = measurement_age_days(prov["measured-at"])
    age_text = (
        f"距今 {age} 天" if age is not None
        else f"measured-at={prov['measured-at']!r} 無法解析"
    )
    return (
        f"{label} 欄 provenance 完整：上次量測 {prov['measured-at']}"
        f"（{age_text}）於 {prov['host']}"
    )


def nightly_evidence(repo_root: Path, platform_key: str) -> str:
    """該平台 nightly 心跳的**單行**現況。純唯讀，找不到就說找不到、不猜。"""
    rel = NIGHTLY_HEARTBEATS.get(platform_key)
    if rel is None:
        return "本平台無已知 nightly 心跳檔"
    path = repo_root / rel
    if not path.is_file():
        return (
            f"本機無 {rel}——**這只代表本機不是跑該 nightly 的那台機器**"
            f"（心跳檔 untracked＋14 天輪替，只存在於產出它的機器上），"
            f"**不得**據此推論該平台沒有 nightly 或沒有真機"
        )
    try:
        head = path.read_text(encoding="utf-8", errors="replace").splitlines()[:3]
    except OSError as exc:  # 讀不到就說讀不到，不靜默當作缺席
        return f"{rel} 存在但讀取失敗：{exc}"
    mtime = datetime.date.fromtimestamp(path.stat().st_mtime).isoformat()
    summary = next((ln.strip() for ln in head if "PASS=" in ln), "（心跳無彙總行）")
    return f"{rel} 最後寫入 {mtime}：{summary}"
