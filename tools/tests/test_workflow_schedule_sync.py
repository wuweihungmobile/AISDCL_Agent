"""GitHub Actions schedule cron ↔ job if 比對字串同步機械鎖（R14 QA-R14-REV-2）。

WHY（測意圖非僅行為，Rule 9）：
`autoclaude-ci.yml` 的 nightly job 以 `github.event.schedule == '<cron>'` 過濾自身
cron（DEF-01-004 修復模式）——代價是 cron 與 if 字串**逐字耦合**：改 cron 忘改 if
＝該 job 從此永不觸發且零告警（R14 降頻時三處 if 同步改，變更註記自承此風險；
本 repo 先前對此零機械鎖，只靠人工記得）。本測試把耦合鎖成雙向集合相等：

  1. 每個被 if 引用的 cron 字串必須存在於 schedule 區塊（防「改 cron 忘 if」）。
  2. 每個 schedule cron 必須被至少一個 if 引用（防「加 cron 忘 job / 刪 job 忘 cron」
     ——未被引用的 cron 會觸發整個 workflow 卻無對應 nightly job，push 閘四 job 又
     已 `!= 'schedule'` 過濾，等於白燒 runner 冷啟動）。

以 regex 抽取而非 yaml 解析：零第三方依賴（根層 unittest 環境不保證 pyyaml），
且 `# - cron:` 註解態（dormant）天然不被行首錨定匹配吸入。

R15 SCAN-C-9：`_IF_REF_RE` 無行首錨定、掃全文——若未來刪 job 時留下含
`github.event.schedule == '...'` 字樣的整行註解（本檔 dormant cron 註記慣例正是
這種形態），集合仍相等、cron 白燒 runner 而零訊號。修法：比對前先剝除「整行註解」
（`\\s*#` 起頭的行）。取捨說明：只剝整行、不剝行尾註解——(1) 行尾註解形態在受掃
workflow 現況不存在，主要風險面（刪 job 留整行註解）已被覆蓋；(2) 行尾剝法需分辨
字串常值內的 `#`（如 cron 欄位雖不含 # 但 run 指令行可能含），保守整行剝除
零誤剝風險。若未來出現行尾註解含 schedule 字樣的形態，再擴充剝法。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

# 目前唯一「多 cron × per-job if 過濾」形態的 workflow；新增同形態檔時加入此清單。
_WORKFLOWS_WITH_CRON_IF_PAIRING = [".github/workflows/autoclaude-ci.yml"]

_CRON_RE = re.compile(r'^\s*- cron: "([^"]+)"', re.MULTILINE)
_IF_REF_RE = re.compile(r"github\.event\.schedule == '([^']+)'")


def _strip_full_line_comments(text: str) -> str:
    """剝除 YAML 整行註解（`\\s*#` 起頭的行），防註解殘骸誤入集合比對。

    R15 SCAN-C-9：不剝行尾註解——取捨理由見模組 docstring。
    """
    return "\n".join(
        ln for ln in text.splitlines() if not ln.lstrip().startswith("#")
    )


class TestWorkflowScheduleSync(unittest.TestCase):
    def test_cron_and_if_reference_sets_are_equal(self) -> None:
        for rel in _WORKFLOWS_WITH_CRON_IF_PAIRING:
            path = _REPO_ROOT / rel
            self.assertTrue(path.is_file(), f"workflow 缺席：{rel}（掃描面不得靜默縮小）")
            text = _strip_full_line_comments(path.read_text(encoding="utf-8"))
            crons = set(_CRON_RE.findall(text))
            refs = set(_IF_REF_RE.findall(text))
            self.assertTrue(crons, f"{rel}：未抽到任何 active cron——regex 或檔案結構疑似改版")
            self.assertEqual(
                refs, crons,
                f"{rel}：schedule cron 集合與 job if 引用字串集合不一致——"
                f"改 cron 忘 if（job 永不觸發）或加 cron 忘 job（白燒 runner）。"
                f"cron={sorted(crons)}，if 引用={sorted(refs)}",
            )

    def test_comment_residue_not_counted_as_reference(self) -> None:
        """R15 SCAN-C-9 自證：刪 job 留下的整行註解殘骸不得再被計為 if 引用。

        先前 _IF_REF_RE 掃全文含註解：真 job 刪除後只要註解殘骸仍含
        `github.event.schedule == '...'` 字樣，集合照樣相等（假綠）。
        """
        cron_and_job = (
            "on:\n"
            "  schedule:\n"
            '    - cron: "0 9 * * 1"\n'
            "jobs:\n"
            "  # 殘骸範例：if: github.event.schedule == '0 9 * * 1'\n"
            "  real:\n"
            "    if: github.event.schedule == '0 9 * * 1'\n"
        )
        stripped = _strip_full_line_comments(cron_and_job)
        # 真 job 在場：剝註解後引用仍抽得到（不誤剝有效行）
        self.assertEqual(set(_IF_REF_RE.findall(stripped)), {"0 9 * * 1"})
        self.assertEqual(set(_CRON_RE.findall(stripped)), {"0 9 * * 1"})
        # 真 job 已刪、只剩註解殘骸：引用集合須為空 → 與 cron 集合不等 → 守門紅
        job_deleted = cron_and_job.replace(
            "  real:\n    if: github.event.schedule == '0 9 * * 1'\n", ""
        )
        stripped_deleted = _strip_full_line_comments(job_deleted)
        self.assertEqual(set(_IF_REF_RE.findall(stripped_deleted)), set())
        self.assertEqual(set(_CRON_RE.findall(stripped_deleted)), {"0 9 * * 1"})


# ══════════════════════════════════════════════════════════════════════════════
# 本輪 R77-20：job **顯示名**裡的 `HH:MM UTC` 宣稱必須對應到一條 active cron
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 缺陷本體（唯讀實查即可證）：`autoclaude-ci.yml` 兩支 dormant mutation job 的顯示名
# 各自寫死了一個排程時刻，而 schedule 區塊裡對應的兩條 cron **是註解掉的**；兩支 job 的
# `if:` 只認 workflow_dispatch，而全歷史零筆 workflow_dispatch ⇒ 它們在可觀測歷史內
# 執行次數為 0，排程 run 上一律 `skipped`／`steps=0`。而 GitHub UI 只顯示 job 名，讀的人
# 會以為它們每週各跑一次——**名字在說謊，而說的正好是「我有在跑」這種最貴的謊**。
#
# 為何用「顯示名 ↔ active cron」當判準（而不是去禁止 dormant job）：dormant job 本身是
# ADR-SD09-002 的刻意設計（單一時間 1 個 active pilot module），不是缺陷；缺陷是**名字
# 宣稱了一個不存在的排程**。判準因此只問一件可機械判定的事：名字裡若出現時刻，該時刻
# 必須真的能從這支檔的 active cron 算出來。註解掉的 cron 天然不算（同本檔既有的
# `_strip_full_line_comments` 紀律——dormant 軌不是期望軌）。
#
# 這與本檔上半部的 `cron ↔ if` 集合鎖互補：那道守「job 會不會被觸發」，本道守
# 「job 名有沒有在對人說謊」。兩者都不是對方的替代品（實測：本輪的兩支 job 名說謊，
# 而 cron↔if 集合鎖全綠——它結構上看不到 `name:`）。

#: job 層顯示名（恰 4 空白縮排；step 的 `- name:` 是 6 空白 ＋ `- `，天然不進集合）。
_JOB_NAME_RE = re.compile(r"^    name:\s*(.+?)\s*$", re.MULTILINE)
#: 顯示名裡的時刻宣稱。刻意只認帶 `UTC` 字樣的形態——job 名裡出現的其他數字
#: （版本號、百分比、`p95`）不是排程宣稱，收進來只會製造誤報。
_UTC_CLAIM_RE = re.compile(r"(\d{1,2}):(\d{2})\s*UTC")
#: 掃描面下限：至少要有一支 job 名真的帶時刻宣稱，否則下方斷言恆真而假綠。
_MIN_JOB_NAME_SCHEDULE_CLAIMS = 1


def active_cron_times(text: str) -> set[str]:
    """該 workflow **未被註解掉**的 cron 換算成 `HH:MM`（UTC）。

    分／時欄位非純數字（`*`、`*/15`、清單）者略過——那種 cron 沒有單一時刻可對，
    對它做等值比對只會製造誤報。略過的方向是「本鎖對它零判準」，已在下方訊息明說。
    """
    times: set[str] = set()
    for expr in _CRON_RE.findall(_strip_full_line_comments(text)):
        fields = expr.split()
        if len(fields) >= 2 and fields[0].isdigit() and fields[1].isdigit():
            times.add(f"{int(fields[1]):02d}:{int(fields[0]):02d}")
    return times


def job_name_schedule_claims(text: str) -> list[tuple[str, str]]:
    """`(job 顯示名, 'HH:MM')` —— 顯示名裡宣稱的排程時刻。"""
    claims: list[tuple[str, str]] = []
    for name in _JOB_NAME_RE.findall(_strip_full_line_comments(text)):
        for hh, mm in _UTC_CLAIM_RE.findall(name):
            claims.append((name, f"{int(hh):02d}:{mm}"))
    return claims


class TestJobNameScheduleClaims(unittest.TestCase):
    """R77-20：job 名不得宣稱一個沒有 active cron 的排程時刻。"""

    def _workflow_dir(self):
        return _REPO_ROOT / ".github" / "workflows"

    def test_every_job_name_time_claim_matches_an_active_cron(self) -> None:
        offenders: list[str] = []
        total_claims = 0
        for path in sorted(self._workflow_dir().glob("*.yml")):
            text = path.read_text(encoding="utf-8")
            active = active_cron_times(text)
            for name, hhmm in job_name_schedule_claims(text):
                total_claims += 1
                if hhmm not in active:
                    offenders.append(
                        f"{path.name}：job 名 {name!r} 宣稱 {hhmm} UTC，"
                        f"而該檔的 active cron 時刻為 {sorted(active) or '（無）'}"
                    )
        self.assertGreaterEqual(
            total_claims, _MIN_JOB_NAME_SCHEDULE_CLAIMS,
            f"全 workflow 抽不到任何帶時刻的 job 名（實得 {total_claims}）——"
            f"抽取式壞掉時本鎖會恆真；若真的刻意移除了全部時刻宣稱，請同步下修 "
            f"_MIN_JOB_NAME_SCHEDULE_CLAIMS 並在 commit 訊息寫明",
        )
        self.assertEqual(
            offenders, [],
            "下列 job 的**顯示名**宣稱了一個沒有 active cron 的排程時刻。GitHub UI 只"
            "顯示 job 名，讀的人會以為它定期在跑；而註解掉的 cron 不會觸發任何東西。\n"
            f"  命中：{offenders}\n"
            "  處置二擇一：(a) 真的把那條 cron 從註解態放出來（同時要讓 `cron ↔ if` "
            "集合鎖通過，見本檔上半部）；(b) 把時刻從 job 名拿掉，改寫成它實際的觸發"
            "方式。\n"
            "  射程劃界：分/時欄位非純數字的 cron（`*`、`*/15`、清單）本鎖零判準。",
        )

    def test_criterion_flags_a_name_backed_only_by_a_commented_cron(self) -> None:
        """鑑別力（Rule 9）：註解態 cron 不得替 job 名的時刻宣稱背書。"""
        text = (
            "on:\n"
            "  schedule:\n"
            '    - cron: "7 3 * * 1"\n'
            '    # - cron: "0 4 * * 1"   # dormant\n'
            "jobs:\n"
            "  live:\n"
            "    name: Live job - 03:07 UTC\n"
            "  dormant:\n"
            "    name: Dormant job - 04:00 UTC\n"
        )
        self.assertEqual(active_cron_times(text), {"03:07"})
        bad = [c for c in job_name_schedule_claims(text) if c[1] not in active_cron_times(text)]
        self.assertEqual(bad, [("Dormant job - 04:00 UTC", "04:00")])

    def test_step_level_names_are_not_mistaken_for_job_names(self) -> None:
        """反向：step 的 `- name:` 不得被當成 job 名（縮排不同，收進來會誤報）。"""
        text = (
            "jobs:\n"
            "  a:\n"
            "    name: Job A\n"
            "    steps:\n"
            "      - name: 補跑提醒 05:00 UTC\n"
        )
        self.assertEqual([n for n, _ in job_name_schedule_claims(text)], [])


# ══════════════════════════════════════════════════════════════════════════════
# 本輪 R77-38：「五軌完整 TLC 留 nightly」這句話與實況的**雙向**綁定
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 缺陷本體：`aisdlc-sdd-ci.yml` 檔頭把 chaos 與五軌完整 TLC 併寫成同一句「仍留
# nightly」。chaos 那一半是真的（有專屬 workflow ＋ 本機 nightly stage），TLC 那一半
# 是假的——全庫零命中。後果不只是「一句不準的話」：根 CLAUDE.md 明文要求「改
# `_HAPPY_PATH` 必須同步 `formal/SDD_FSM.tla` 並重跑 TLC」，而能抓到那個漂移的測試
# 正是被 skip 的其中一支 ⇒ 那條紀律零機械強制，卻有一句 workflow 註解在替它背書。
#
# 本鎖刻意做成**雙向**（這是它與「補一句揭露就結案」的差別）：
#   · 通道不存在 ⇒ 揭露標記必須在（不准把它悄悄刪掉、回到那句好聽話）；
#   · 通道存在   ⇒ 揭露標記必須**不**在（建了通道卻留著「沒有通道」的揭露，就是在
#     樹裡留下一句方向相反的舊話——本 repo 已為這種形態付過學費）。
# 單向鎖只能防前者，而後者才是「補完之後沒人回來清」的常態。

#: 揭露標記（機器讀這個 token，散文可自由改寫；同 repo 內既有 `# platform-ok:` 體例）。
_TLC_DISCLOSURE_TOKEN = "TLC-NO-AUTOMATED-CHANNEL"
#: 「完整 TLC 真的被啟用」的兩種寫法（ci-gate.sh 的旗標／其環境變數開關）。
_TLC_ENABLERS = ("--full-tlc", "SDD_RUN_TLC")
#: 承接「自動通道」的載具：雲端 workflow 全體 ＋ 兩支 nightly 聚合器。
#: 刻意含本機 nightly——揭露文字說的是「任何自動通道」，只掃雲端會讓它半真半假。
_TLC_CARRIERS = (
    "AutoClaude/tools/run_local_nightly.ps1",
    "AutoClaude/tools/run_local_nightly.sh",
)


def full_tlc_channel_sites() -> list[str]:
    """回傳「真的啟用完整 TLC」的站點（`檔:行`）；空 list＝零自動通道。

    只看**非註解行**：本 repo 的載具檔大量以註解記載沿革，把「曾經想過要做」讀成
    「已經有通道」正是本鎖要防的病（同 test_root_infra_parity 的 `_pre_push_exec_text`
    既有慣例）。
    """
    sites: list[str] = []
    paths = sorted((_REPO_ROOT / ".github" / "workflows").glob("*.yml"))
    paths += [_REPO_ROOT / rel for rel in _TLC_CARRIERS]
    for path in paths:
        if not path.is_file():
            continue
        rel = path.relative_to(_REPO_ROOT).as_posix()
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            stripped = line.lstrip()
            if stripped.startswith("#") or not stripped:
                continue
            if any(tok in line for tok in _TLC_ENABLERS):
                sites.append(f"{rel}:{lineno}")
    return sites


class TestFullTlcChannelDisclosure(unittest.TestCase):
    """R77-38：揭露文字與「通道存不存在」雙向綁定。"""

    def _sdd_ci_text(self) -> str:
        return (_REPO_ROOT / ".github" / "workflows" / "aisdlc-sdd-ci.yml").read_text(
            encoding="utf-8"
        )

    def test_disclosure_matches_whether_the_channel_actually_exists(self) -> None:
        sites = full_tlc_channel_sites()
        disclosed = _TLC_DISCLOSURE_TOKEN in self._sdd_ci_text()
        if sites:
            self.assertFalse(
                disclosed,
                f"完整 TLC 的自動通道已經存在（{sites}），但 aisdlc-sdd-ci.yml 檔頭仍留著 "
                f"`{_TLC_DISCLOSURE_TOKEN}` 揭露——那是一句方向相反的舊話。處置：刪掉那段"
                f"揭露，並把 chaos／TLC 兩件事在檔頭寫清楚各自走哪條通道",
            )
        else:
            self.assertTrue(
                disclosed,
                f"全庫找不到任何啟用完整 TLC 的站點（掃 {_TLC_ENABLERS} 於根層 workflow "
                f"與 {list(_TLC_CARRIERS)} 的非註解行），而 aisdlc-sdd-ci.yml 檔頭沒有 "
                f"`{_TLC_DISCLOSURE_TOKEN}` 揭露 ⇒ 讀者會以為 TLC 有在跑。處置：要嘛真的"
                f"建通道，要嘛把揭露寫回去；不得兩者皆無",
            )

    def test_carrier_list_is_not_silently_empty(self) -> None:
        """反向守門：載具全部不存在時，上一條會因 `sites` 恆空而變成單向鎖。"""
        missing = [rel for rel in _TLC_CARRIERS if not (_REPO_ROOT / rel).is_file()]
        self.assertEqual(
            missing, [],
            f"下列 TLC 通道載具在磁碟上不存在：{missing}——它們被改名／搬走後，"
            f"本鎖對「本機 nightly 建了通道」這一側就失明了，請同步 _TLC_CARRIERS",
        )

    def test_enabler_detection_ignores_comments(self) -> None:
        """判準自證：註解裡提到旗標不等於通道存在（否則本檔的說明文字自己會滿足它）。"""
        self.assertTrue(any(tok in self._sdd_ci_text() for tok in _TLC_ENABLERS),
                        "前提：檔頭揭露文字本來就會提到那兩個旗標名")
        self.assertEqual(
            [s for s in full_tlc_channel_sites() if s.startswith(".github/")], [],
            "註解裡的旗標名被當成了真通道——`full_tlc_channel_sites` 的註解過濾失效",
        )


if __name__ == "__main__":
    unittest.main()
