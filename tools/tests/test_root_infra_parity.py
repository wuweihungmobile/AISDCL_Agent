"""root-infra-ci.yml ↔ pre-push root-infra leg 守門清單同步鎖（R10 ARCH-2，DEF-101-132）。

WHY（測意圖非僅行為，Rule 9）：
root-infra-ci.yml 的守門 step 與本地 pre-push dispatcher root-infra leg 的守門
清單是兩份獨立硬編碼——R11 若新增第五支守門工具進 CI 而忘改 pre-push，本地
永遠不跑新守門且無任何 diff 訊號（兩處各自綠燈）。本測試機械斷言：
  1. CI 內每個 `python3 tools/<x>.py` 具名守門呼叫，pre-push 內必有對應呼叫
     （DEF-101-112 已明文豁免的四道非 python 步驟不在此列：pwsh parse+BOM、
     EOL(.sh)、EOL(.ps1)、bash -n push 全量——它們不是 `python3 tools/*.py` 形狀，
     天然不進抽取集合；若未來以 python 工具重寫，會自動落入本鎖）。
  2. pre-push 的根層消費檔清單必須機械讀取 aisdlc-sdd-ci.yml（單一真相源），
     不得退化回手抄第二份清單（R10 ARCH-1 接線的防復發鎖）。
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CI_YML = _REPO_ROOT / ".github" / "workflows" / "root-infra-ci.yml"
_SDD_CI_YML = _REPO_ROOT / ".github" / "workflows" / "aisdlc-sdd-ci.yml"
_PRE_PUSH = _REPO_ROOT / "tools" / "git-hooks" / "pre-push"

_PY_TOOL_RE = re.compile(r"python3?\s+(tools/[A-Za-z0-9_]+\.py)")
# 檔頭守門清單的單筆條目：`#   N. …` 起，至下一筆或檔頭「# 注：」段前止。
_HEADER_ITEM_RE = re.compile(
    r"^#\s+(\d+)\.\s(.*?)(?=^#\s+\d+\.\s|^# 注：)", re.MULTILINE | re.DOTALL
)
# `actions/<名>` 字面列舉（用於第 12 道的負面斷言）。
_ACTION_NAME_RE = re.compile(r"actions/[A-Za-z0-9_.-]+")
# pre-push 側的守門工具不全以 `python <tool>` 形狀出現（六支守門走
# `for guard in tools/a.py tools/b.py …; do python "$guard"; done` 迴圈，工具名
# 與 `python` 不同 token），故反向抽取改認「任何 tools/*.py 路徑字面值」。
_ANY_TOOL_PATH_RE = re.compile(r"tools/[A-Za-z0-9_]+\.py")
_GUARD_LOOP_RE = re.compile(r"for guard in\s+(.*?);\s*do", re.DOTALL)
_GUARD_COUNT_CLAIM_RE = re.compile(r"([一二三四五六七八九十]+)支守門工具")
_CJK_DIGITS = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
    "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
}
# 檔頭第 1 道（bash -n）敘述區塊：`#   1. bash -n …` 起，至 `#   2.` 前止。
_FIRST_GUARD_HEADER_RE = re.compile(r"^#\s+1\. bash -n\s+—(.*?)(?=^#\s+2\.)",
                                    re.MULTILINE | re.DOTALL)
# 對應的 step 實作區塊：`- name: bash -n …` 起，至下一個 `- name:` 前止。
_FIRST_GUARD_STEP_RE = re.compile(r"^ +- name: bash -n .*?(?=^ +- name: )",
                                  re.MULTILINE | re.DOTALL)
# 掃描面來源的兩種機制關鍵字（擴面/縮面必經其一改動）。
_SCAN_MECHANISMS = ("git ls-files", "find tools")

# 與 pre-push 消費檔抽取管線同形狀：只認 `- "…"` 雙引號條目（bash 端 grep -E
# '^[[:space:]]*-[[:space:]]*"'）——本 regex 刻意鏡射該限制以便下方下限鎖生效。
_QUOTED_PATH_ENTRY_RE = re.compile(r'^\s*-\s*"([^"]+)"\s*$')


def _yml_python_tools() -> set[str]:
    """抽取 root-infra-ci.yml 內的 `python3 tools/<x>.py` 具名守門呼叫。

    只掃非註解行（yml 檔頭大段說明不算接線）；py_compile 走 `python3 -m`
    形狀、天然不入集合（其 pre-push 對等由 dispatcher 測試覆蓋）。
    """
    tools: set[str] = set()
    for line in _CI_YML.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#"):
            continue
        for match in _PY_TOOL_RE.finditer(line):
            tools.add(match.group(1))
    return tools


def _pre_push_exec_text() -> str:
    """pre-push 的「非註解行」全文（R10 二審 Architect P4 硬化：守門工具名若只
    殘留在註解裡不得滿足同步鎖——子字串比對的假綠縫）。"""
    return "\n".join(
        line for line in _PRE_PUSH.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )


class TestRootInfraParity(unittest.TestCase):
    def test_ci_python_guards_all_wired_in_pre_push(self) -> None:
        ci_tools = _yml_python_tools()
        self.assertGreaterEqual(
            len(ci_tools), 7,
            f"root-infra-ci.yml 抽取到的具名 python 守門異常地少：{sorted(ci_tools)}——"
            f"抽取 pattern 或 yml 疑似被改壞（數量下限釘選精神；現況 7 支，"
            f"新增守門工具時本行必須同步上調——R56 訂正：R13 增第 11 道、R55 增"
            f"第 12 道時本下限都沒跟上，停在 5 而實數已 7，等於還能被靜默刪掉兩支）",
        )
        pre_push_exec_text = _pre_push_exec_text()
        missing = sorted(t for t in ci_tools if t not in pre_push_exec_text)
        self.assertEqual(
            missing, [],
            f"CI 有、本地 pre-push root-infra leg 無（非註解行）：{missing}——"
            f"新增守門工具須同步接線（R9 root-infra leg 的存在理由：CI 停擺期間本地是唯一防線）",
        )
        # R56 補（QA finding）：原鎖只單向（CI ⊆ pre-push），反方向缺口——本地
        # 多跑了一支 CI 沒有的守門時，push 綠燈但 CI 紅（或反之，該守門在雲端
        # 完全沒有兜底）。兩份硬編清單的存在理由是彼此鏡射，斷言集合相等。
        pre_push_tools = set(_ANY_TOOL_PATH_RE.findall(pre_push_exec_text))
        self.assertEqual(
            sorted(pre_push_tools - ci_tools), [],
            f"pre-push root-infra leg 有、root-infra-ci.yml 無："
            f"{sorted(pre_push_tools - ci_tools)}——本地守門必須在雲端有對等兜底",
        )

    def test_guard_count_claims_match_loop(self) -> None:
        """R56 新增：pre-push 內三處以中文數字宣稱「N 支守門工具」的註解必須等於
        守門迴圈的實際項數。R55 把守門由五支增為六支時只改了兩處（L12／L211），
        L185 停在「五支」；同一輪的 `windowsapps_guard.sh`「9 支」也數錯（實為
        15）——同構的「多站點人工計數漂移」一輪內連踩兩起，故機械化而非再數一次。"""
        text = _PRE_PUSH.read_text(encoding="utf-8")
        loop = _GUARD_LOOP_RE.search(text)
        self.assertIsNotNone(loop, "pre-push 找不到 `for guard in …; do` 守門迴圈——結構被改動")
        guards = _ANY_TOOL_PATH_RE.findall(loop.group(1))
        self.assertGreaterEqual(len(guards), 6, f"守門迴圈項數異常地少：{guards}")
        claims = _GUARD_COUNT_CLAIM_RE.findall(text)
        self.assertGreaterEqual(len(claims), 2, f"找不到足夠的「N 支守門工具」計數宣稱：{claims}")
        for cjk in claims:
            self.assertEqual(
                _CJK_DIGITS.get(cjk), len(guards),
                f"pre-push 註解宣稱「{cjk}支守門工具」，但迴圈實際有 {len(guards)} 支："
                f"{guards}——計數宣稱必須與實作同步（本鎖即為防此類漂移而設）",
            )

    def test_first_guard_header_scope_matches_step_implementation(self) -> None:
        """R56 新增（Architect 與 SA 各自獨立回報同一根因）：檔頭第 1 道敘述是
        ONBOARDING.md §6 明文指定的權威來源（原文「詳細內容以 workflow 檔頭註解
        為準，避免每次擴充都要同步改動兩處」）。R56 把該 step 的掃描面由
        `find tools`（10 檔）擴為全庫 `git ls-files`（174 檔）時檔頭漏改，被指定
        的真相源反而成了錯的一方；同形狀的「多站點敘述漂移」本 repo 已連踩四輪
        （R54 DEF-101-431／R55「9 支」／本輪 pre-push「五支」）。故機械斷言：
        step **非註解行**採用的掃描機制關鍵字，必須同時出現在檔頭第 1 道敘述裡
        ——未來任一方向擴面/縮面而檔頭沒跟上即紅。"""
        text = _CI_YML.read_text(encoding="utf-8")
        header = _FIRST_GUARD_HEADER_RE.search(text)
        self.assertIsNotNone(header, "root-infra-ci.yml 找不到檔頭第 1 道（bash -n）敘述區塊")
        step = _FIRST_GUARD_STEP_RE.search(text)
        self.assertIsNotNone(step, "root-infra-ci.yml 找不到 bash -n step 實作區塊")
        # 只看非註解行（step 內註解會提及舊機制 `find tools` 作為沿革記載，
        # 那是史料不是實作——沿用本檔既有 `_yml_python_tools` 同款過濾慣例）。
        step_exec = "\n".join(
            line for line in step.group(0).splitlines()
            if not line.lstrip().startswith("#")
        )
        used = [m for m in _SCAN_MECHANISMS if m in step_exec]
        self.assertEqual(
            len(used), 1,
            f"bash -n step 非註解行抽出的掃描機制不唯一：{used}——"
            f"新增第三種機制時請同步 _SCAN_MECHANISMS 與本鎖",
        )
        self.assertIn(
            used[0], header.group(1),
            f"檔頭第 1 道敘述未提及 step 實際採用的掃描機制 `{used[0]}`——"
            f"檔頭是 ONBOARDING.md 指定的權威來源，擴面/縮面時必須同步"
            f"（現行檔頭敘述：{header.group(1).strip()!r}）",
        )

    def test_header_guard_list_tool_names_match_steps(self) -> None:
        """R56 新增（SA finding；把 R56 前一輪只保護第 1 道的原則推廣到全部守門）：
        ONBOARDING.md §6 明文指定「詳細內容以 workflow 檔頭註解為準，避免每次擴充
        都要同步改動兩處」——檔頭是被指定的權威來源，因此它自己漂移的代價最高。
        前一輪只為第 1 道建了檔頭↔實作鎖，12 道中的其餘 11 道零訊號，第 12 道就
        因此在同一輪內漂掉（檔頭仍列舉已被物理移除的四名 action 白名單）。

        本鎖雙向斷言「檔頭條目提及的 `tools/*.py` 工具名」與「step 非註解行實際
        呼叫的具名 python 守門」為同一集合：
          - 檔頭有、step 無 → 檔頭在描述一個已不存在的守門（本次漂移的形狀）；
          - step 有、檔頭無 → 新增守門忘了寫進被指定為權威來源的檔頭。
        """
        text = _CI_YML.read_text(encoding="utf-8")
        items = _HEADER_ITEM_RE.findall(text)
        self.assertGreaterEqual(
            len(items), 12,
            f"檔頭守門清單只抽到 {len(items)} 筆條目（現況 12 道）——抽取 pattern 或"
            f"檔頭結構疑似漂移（下限釘選精神；刻意刪減守門時同步下修）",
        )
        header_tools = {
            m for _n, body in items for m in _ANY_TOOL_PATH_RE.findall(body)
        }
        step_tools = _yml_python_tools()
        self.assertEqual(
            sorted(header_tools), sorted(step_tools),
            f"root-infra-ci.yml 檔頭守門清單提及的工具與 step 實際呼叫的不一致——"
            f"檔頭有 step 無：{sorted(header_tools - step_tools)}；"
            f"step 有檔頭無：{sorted(step_tools - header_tools)}。檔頭是 ONBOARDING.md"
            f"明文指定的權威來源，任一方增刪必須同步",
        )

    def test_header_item12_does_not_enumerate_action_whitelist(self) -> None:
        """R56 新增（SA finding 的直接修復＋防復發）：第 12 道的實作已於 R56 把
        `_TRACKED_ACTIONS` 四名白名單**物理移除**（該白名單本身是 fail-open：打錯
        一個字即靜默少守 13 處宣告仍印綠燈），改為「凡 `actions/*` 一律納入唯一性
        斷言」的通用規則。檔頭與 step 名稱若仍逐一列舉那四個 action，讀者會據此
        以為掃描面只有四個、也會誤以為新增第五個 action 需要先改白名單。

        鎖的方向刻意做成**條件式**而非硬禁：以工具自身是否仍有白名單常數為準
        ——未來若刻意改回白名單設計，本鎖自動放行，不會逼人繞過。
        """
        tool_text = (_REPO_ROOT / "tools" / "check_gha_action_versions.py").read_text(
            encoding="utf-8"
        )
        # 認「常數**賦值**」而非裸字串：該檔的沿革註解與其測試檔都提到
        # `_TRACKED_ACTIONS` 這個名字，裸 `in` 比對會讓本鎖恆 skip（實測驗證）。
        if re.search(r"^_TRACKED_ACTIONS\s*[:=]", tool_text, re.MULTILINE):
            self.skipTest("check_gha_action_versions.py 已改回白名單設計，本負面斷言自動放行")
        text = _CI_YML.read_text(encoding="utf-8")
        items = dict(_HEADER_ITEM_RE.findall(text))
        self.assertIn("12", items, "檔頭抽不到第 12 道條目——編號或結構已變動")
        listed = sorted(set(_ACTION_NAME_RE.findall(items["12"])))
        self.assertEqual(
            listed, [],
            f"檔頭第 12 道仍逐一列舉 action 名 {listed}，但實作已無 `_TRACKED_ACTIONS` "
            f"白名單、掃描面是全部 `actions/*`——列舉會讓讀者低估掃描面（fail-open "
            f"白名單移除後的敘述殘留）。請改為不列舉的通用敘述",
        )
        step_names = re.findall(r"^ +- name: (.*)$", text, re.MULTILINE)
        gha_steps = [n for n in step_names if "check_gha_action_versions.py" in n]
        self.assertEqual(
            len(gha_steps), 1, f"預期恰一個 check_gha_action_versions step：{gha_steps}"
        )
        self.assertEqual(
            sorted(set(_ACTION_NAME_RE.findall(gha_steps[0]))), [],
            f"第 12 道 step 名稱仍逐一列舉 action 名：{gha_steps[0]!r}——同上理由",
        )

    def test_sdd_ci_yml_consumer_paths_extractable_with_floor(self) -> None:
        """R10 二審 Architect P3：pre-push 消費檔抽取只認雙引號 `- "…"` 條目——
        若真實 aisdlc-sdd-ci.yml 的 paths 條目改成單引號/裸字串（合法 YAML、GitHub
        照常解析），本地抽取靜默變空、消費檔 leg 整條蒸發且零紅燈。本鎖以同形狀
        regex 抽真實 yml，斷言非 AISDLC_SDD 消費檔條目數 ≥5（現況 5 條）——條目
        改寫引號風格或刪減時本測試翻紅，強制同步 pre-push 抽取管線。"""
        entries: set[str] = set()
        for line in _SDD_CI_YML.read_text(encoding="utf-8").splitlines():
            m = _QUOTED_PATH_ENTRY_RE.match(line)
            if m:
                entries.add(m.group(1))
        consumers = sorted(
            e for e in entries
            if not e.startswith("AISDLC_SDD/") and not e.startswith(".github/workflows/")
        )
        self.assertGreaterEqual(
            len(consumers), 5,
            f"aisdlc-sdd-ci.yml 以雙引號形狀抽出的根層消費檔僅 {consumers}——"
            f"若刻意改寫條目引號風格，必須同步 tools/git-hooks/pre-push 的抽取管線"
            f"（否則消費檔 leg 靜默蒸發）",
        )

    def test_pre_push_consumer_list_reads_sdd_ci_yml(self) -> None:
        pre_push_text = _PRE_PUSH.read_text(encoding="utf-8")
        self.assertIn(
            "aisdlc-sdd-ci.yml", pre_push_text,
            "pre-push 的根層消費檔清單必須機械讀取 aisdlc-sdd-ci.yml（單一真相源），"
            "不得退化為手抄清單（R10 ARCH-1）",
        )
        self.assertIn(
            "scripts/tests", pre_push_text,
            "消費檔命中時必須補跑 AISDLC_SDD/scripts/tests 回歸鎖（R10 ARCH-1）",
        )
        # R10 二審 SD P3 錨點：清單 SSOT 自身變更也必須觸發消費檔 leg
        self.assertIn(
            ".github/workflows/aisdlc-sdd-ci.yml) run_sdd_consumer=1", pre_push_text,
            "pre-push 必須在 push 涉 aisdlc-sdd-ci.yml 自身時觸發消費檔 leg——"
            "清單被改壞時守它的 meta 鎖住在 SDD suite，否則零機械訊號",
        )


if __name__ == "__main__":
    unittest.main()
