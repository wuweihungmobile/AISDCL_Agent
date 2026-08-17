#!/usr/bin/env python3
"""R83／W2-A：mac 側「額度耗盡 → 排程喚醒 → 續跑」的回歸鎖。

本檔守的是四件事，每一件都附**合成注入的紅**（只有綠的鎖等於沒有鎖）：
  ① 平台問題只有一個提問點（`schedule_backend.select`），四支武裝臂不得自己問 `os.name`；
  ② mac 憑證有鑑別力：回讀不符 ⇒ **不發憑證**，而沒有憑證就不准把 state 寫成 armed；
  ③ 自我解除不得同步 bootout（真機實測會把自己殺掉，見下方 `SelfDisarmTest` 的 WHY）；
  ④ Windows 那一側行為零改變（以替身模擬 `os.name == 'nt'`，不需要真的有 PowerShell）。

🔴 **本檔刻意零 `skipUnless`**：全部走注入，所以在 Windows／mac／Linux 上跑的是同一組
斷言、同一個分母。真機那一半（真的武裝一支 launchd、真的被叫起來、真的解除）不在這裡
——那是 ops 行為，寫進單元測試就會讓「跑測試」變成「動這台機器的排程」，本 repo 判過
（`quota_escalation.gc_plans` 的 `root` 注入點同一條理由）。真機取證留在交付報告。
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import json
import os
import plistlib
import re
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

import context_budget_guard as guard  # noqa: E402
import endurance_env  # noqa: E402
import quota_escalation as escalation  # noqa: E402
import schedule_backend as sb  # noqa: E402
import sentinel_lifecycle  # noqa: E402

import session_resume_planner as planner  # noqa: E402

_GUARD_SRC = (_REPO_ROOT / ".claude" / "hooks" / "context_budget_guard.py")
_SENTINEL_SRC = (_REPO_ROOT / "tools" / "lib" / "sentinel_lifecycle.py")
_BACKEND_SRC = (_REPO_ROOT / "tools" / "lib" / "schedule_backend.py")

#: 武裝臂的命名慣例（module-level `arm_*`／`spawn_*`）。
_ARM_NAME_RE = re.compile(r"^(?:arm|spawn)_")
#: 武裝臂支數的**下限**。與現查分母配套使用：分母只准長，不准縮到這個數以下。
#: 🔴 為什麼下限也要一條斷言：分母改成現查之後，「把命名慣例整批改掉」（例如全部改叫
#: `hook_arm_*`）會讓分母悄悄變成空集合，而**空分母的判準恆綠**——分母 0＝沒有東西可
#: 違反，rc 與「正確地全部通過」一模一樣。本 repo 對這個形態已有判例（R80 hook 佈線
#: 轉 exec form 之後，八個「只讀 `command`」的解析器全部掃出空集合）。
_ARMING_ARMS_FLOOR = 4


def arming_arms(source: str) -> tuple[str, ...]:
    """現查「這台機器要不要掛續航」的全部入口＝module-level `arm_*`／`spawn_*` 函式。

    分母改現查而非寫死四元組（R83 複審 F-05／FC-5 訂正，立案史料原文＝Guard_Repin 證據檔
    §E-1）。改成現查之後，第五支臂一落地就進分母，不需要有人記得回來改這一行。
    """
    tree = ast.parse(source)
    return tuple(sorted(node.name for node in tree.body
                        if isinstance(node, ast.FunctionDef)
                        and _ARM_NAME_RE.match(node.name)))


def _os_name_sites(source: str, names: tuple[str, ...]) -> list[str]:
    """在指定函式的 body 裡找 `os.name` 的**求值站點**（純函式，紅綠由注入自證）。

    走 AST 而不是字串搜尋：那幾支函式的 WHY 註解裡合法地寫著 `os.name`（它們正在
    解釋為什麼不再這樣寫），掃原始碼會把解釋判成違規——本 repo 判過的假紅形態。
    """
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef) or node.name not in names:
            continue
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Attribute) and inner.attr == "name"
                    and isinstance(inner.value, ast.Name) and inner.value.id == "os"):
                found.append(f"{node.name}:{inner.lineno}")
    return found


class SelectIsTheOnlyPlatformQuestionTest(unittest.TestCase):
    """① 平台差異收斂在一個地方（掌舵者訴求 2：架構簡潔／不重複模組）。"""

    def test_each_platform_gets_the_carrier_that_actually_exists_there(self) -> None:
        self.assertIsInstance(sb.select(os_name="nt"), sb.SchtasksBackend)
        self.assertIsInstance(sb.select(os_name="posix", platform_name="darwin"),
                              sb.LaunchdBackend)
        # Linux **明說做不到**，不假裝：假裝支援會讓「排不了」與「不排程」外觀相同。
        self.assertIsInstance(sb.select(os_name="posix", platform_name="linux"),
                              sb.NoCarrierBackend)

    def test_has_carrier_is_true_exactly_where_a_scheduler_is_implemented(self) -> None:
        self.assertTrue(sb.has_carrier(os_name="nt"))
        self.assertTrue(sb.has_carrier(os_name="posix", platform_name="darwin"))
        self.assertFalse(sb.has_carrier(os_name="posix", platform_name="linux"))

    def test_the_two_carriers_write_their_credential_into_different_keys(self) -> None:
        """憑證鍵不共用：`next_run_time` 這個鍵名在 mac 上是假話（launchd 不報 next-run）。"""
        self.assertEqual(sb.select(os_name="nt").credential_key, "next_run_time")
        self.assertEqual(sb.select(os_name="posix", platform_name="darwin").credential_key,
                         "schedule_credential")
        self.assertNotEqual(sb.CRED_KEY_SCHTASKS, sb.CRED_KEY_LAUNCHD)

    def test_the_arming_arm_denominator_is_measured_not_hardwired(self) -> None:
        """🔴 分母本身的鎖（R83 複審 F-05／FC-5）：現查集合必須涵蓋今天那四支，且不得縮小。

        兩個方向：① 現查得到的支數不得低於 `_ARMING_ARMS_FLOOR`（防命名慣例被改掉導致
        空分母恆綠）；② 今天已知的四支必須都在現查集合裡（防判準的正規式被改窄）。
        """
        measured = arming_arms(_GUARD_SRC.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(measured), _ARMING_ARMS_FLOOR,
                                f"武裝臂現查只有 {measured} ⇒ 分母疑似被命名慣例改掉了，"
                                "而空分母的判準恆綠")
        for known in ("spawn_sentinel", "arm_sentinel", "arm_when_earned",
                      "arm_quota_wakeup"):
            self.assertIn(known, measured)

    def test_a_fifth_arming_arm_lands_in_the_denominator_by_itself(self) -> None:
        """合成注入（紅）：複審者用來證偽「寫死四元組」的那一支，現在必須當場被抓到。

        注入的第五支逐字是 `def arm_next_thing(payload): if os.name != "nt": return`
        ——正是本包立案要防的寫法。舊判準（寫死四元組）對它兩支鎖皆綠。
        """
        injected = ("import os\n"
                    "def arm_next_thing(payload):\n"
                    '    if os.name != "nt":\n'
                    "        return\n")
        measured = arming_arms(injected)
        self.assertEqual(measured, ("arm_next_thing",))
        self.assertTrue(_os_name_sites(injected, measured), "第五支臂竟然被放行")
        # 對照組：命名慣例之外的函式不得進分母（否則整支檔案都變成武裝臂）。
        self.assertEqual(arming_arms("def helper():\n    return 1\n"), ())

    def test_no_arming_arm_asks_the_platform_by_itself(self) -> None:
        """成因面：每一支武裝臂一律問 `_has_carrier()`，不得自己求值 `os.name`。"""
        source = _GUARD_SRC.read_text(encoding="utf-8")
        sites = _os_name_sites(source, arming_arms(source))
        self.assertEqual(sites, [], f"武裝臂又自己問了一次平台：{sites}")

    def test_every_arming_arm_is_actually_wired_to_the_single_question(self) -> None:
        """後果面的另一半：不問 `os.name` 也可能是**整條判斷被刪掉**。

        兩條都要有——只驗「沒有 os.name」的話，把平台判斷整個拿掉（於是 Linux 上也去
        spawn 一支不存在的排程器）同樣會綠。
        """
        source = _GUARD_SRC.read_text(encoding="utf-8")
        for arm in arming_arms(source):
            body = ast.parse(source)
            fn = next(n for n in ast.walk(body)
                      if isinstance(n, ast.FunctionDef) and n.name == arm)
            calls = {n.func.id for n in ast.walk(fn)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
            self.assertIn("_has_carrier", calls, f"`{arm}` 沒有接上唯一提問點")

    def test_the_scan_would_actually_catch_a_regression(self) -> None:
        """合成注入（紅）：把 `os.name` 寫回武裝臂就該被抓到。

        沒有這一支，上面那條綠只說明「今天沒有人這樣寫」，而本包的立案正是
        「這種寫法今天在四個地方都成立」。
        """
        injected = ("import os\n"
                    "def arm_sentinel(payload):\n"
                    '    if os.name != "nt":\n'
                    "        return\n")
        self.assertTrue(_os_name_sites(injected, arming_arms(injected)), "注入竟然被放行")
        # 對照組：同一份判準對「只在註解／字串裡提到 os.name」不得誤判（假紅會讓
        # 下一個人把判準整個關掉）。
        innocent = ("def arm_sentinel(payload):\n"
                    '    """此前這裡寫 os.name != \'nt\'，現已改走 _has_carrier。"""\n'
                    "    return _has_carrier()\n")
        self.assertEqual(_os_name_sites(innocent, arming_arms(innocent)), [])


# ═══════════════════════════════════════════════════════════════════════════
# 🔴 R83 複審 A-02／F-6：「唯一提問點」這句宣稱原本**只有一支檔在守**
# ═══════════════════════════════════════════════════════════════════════════
#
# 立案實測史料搬遷，原文＝Guard_Repin 證據檔 §E-2。
#
# 🔴 判準為什麼問「誰在驅動排程器」而不是「誰在問 `os.name`」
# ---------------------------------------------------------
# 因為那個病**不會**被「誰在問 `os.name`」抓到：`sentinel_lifecycle` 一次都沒問平台，它是
# 直接把一個平台的原語寫死。收斂當回合實測（獨立探針、與本檔同一份判準）：「同一個函式
# 既問平台又碰載具」這個形狀在全庫只有 5 個命中，而**沒有一個是 A-01**。
# ⇒ 判準改成：凡把排程器原語（argv 首字 `launchctl`／`schtasks`，或腳本含 `-ScheduledTask`
# cmdlet）餵給 runner 的站點，一律只能住在**宣告過的家**裡。分母是現查出來的檔集合。
_SCHED_CMDLET = "-ScheduledTask"
_SCHED_ARGV0 = ("launchctl", "schtasks", "schtasks.exe")
#: 「真的把它餵出去」的那一層。判準只看**呼叫點的引數**——`print("…用 Get-ScheduledTask
#: 查…")` 這種散文因此一律放行。這個限縮是實測後的決定，不是偏好：改用「字串字面出現」
#: 當判準的話，收斂當回合實測全庫非家命中 **24 筆**（散落 8 支檔），而其中絕大多數是
#: message／docstring 散文（`tools/dev_start.py` 的建議文、`tools/check_script_parity.py`
#: 的說明、`tools/lib/baseline_origin.py` 的檔頭）——那些檔多半不在本包授權面內，會變成
#: 要逐一辯護的假紅，而那種鎖活不過一輪（本 repo 判過）。
#: 🔴 這個限縮的代價寫清楚：**「先把腳本存成模組常數、再餵給 runner」的形態掃不到**
#: （`tools/check_scheduled_task_drift.py` 正是那個形狀，故它不在今天的命中集內）。
#: 這是判準的已知盲區，登記在這裡而不是留給下一個人自己撞到。
_RUNNERS = frozenset({"run", "Popen", "call", "check_call", "check_output",
                      "run_powershell", "_powershell", "_run"})
#: 排程器原語**宣告過的家**。每一項附理由；空理由不算宣告（見下方判準）。
_CARRIER_HOMES = {
    "tools/lib/schedule_backend.py":
        "本檔就是排程載具本身（`select()` 是唯一提問點；三個後端各自持有自己的原語）",
    "tools/session_resume_planner.py":
        "schtasks／PowerShell 那一整套知識（載具、`NO_WINDOW`、UTF-8 前置行、單引號跳脫、"
        "`NextRunTime` 解析）的唯一的家；`SchtasksBackend` 反過來取用它，不是反向複製",
}
#: 具名豁免＝**不在「續航哨兵」這條軸上**的排程器消費者。理由必須寫得出「為什麼它不該
#: 被收斂進 `schedule_backend`」，而不只是「它今天在這裡」。
_CARRIER_EXEMPT = {
    "tools/dev_start.py":
        "查的是 nightly 軌（`com.autoclaude.nightly`）有沒有載入，純 advisory、與續航哨兵"
        "不同軌；launchd 原語今天仍有第二個家（`tools/install_mac_nightly.sh`），"
        "兩家合流是複審 A-05 已登記的交棒項，不在本輪射程內",
}


def _call_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else ""


def carrier_primitive_sites(sources: dict[str, str]) -> list[str]:
    """把排程器原語餵給 runner 的站點清單（`檔:行`）。純函式，紅綠由注入自證。

    解析失敗一律計為違規——掃不到的檔靜默放行正是本 repo 通篇在防的 fail-open。
    """
    hits: list[str] = []
    for rel, src in sorted(sources.items()):
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            hits.append(f"{rel}:0 AST 解析失敗（{exc}）——掃不到的檔不得靜默放行")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _call_name(node) not in _RUNNERS:
                continue
            texts = [inner.value
                     for arg in [*node.args, *(k.value for k in node.keywords)]
                     for inner in ast.walk(arg)
                     if isinstance(inner, ast.Constant) and isinstance(inner.value, str)]
            if any(_SCHED_CMDLET in t for t in texts) or any(
                    t.split()[0] in _SCHED_ARGV0 for t in texts if t.split()):
                hits.append(f"{rel}:{node.lineno}")
    return hits


def _carrier_scan_surface() -> dict[str, str]:
    """分母＝`tools/`／`.claude/` 底下所有**非測試** `.py`（現查，不是寫死清單）。

    測試檔排除的理由是語意的：測試本來就要合成／注入排程器原語（本檔自己就有一堆）。
    """
    out: dict[str, str] = {}
    for tree in ("tools", ".claude"):
        for path in sorted((_REPO_ROOT / tree).rglob("*.py")):
            parts = set(path.parts)
            if "__pycache__" in parts or ".venv" in parts or "tests" in parts:
                continue
            out[path.relative_to(_REPO_ROOT).as_posix()] = path.read_text(
                encoding="utf-8", errors="replace")
    return out


#: 掃描面下限。射程被改窄（例如有人把 rglob 換成一支檔）必須指名道姓地紅，
#: 而不是只讓命中數變成 0——分母 0 的判準恆綠。
#: 收斂當回合實測 **59** 支；下限取 `int(59 × 0.8) = 47`，比例與
#: `tools/lib/skip_tag_policy.TREE_FLOOR_RATIO` 同一個慣例（本檔不 import 它：那會讓兩道
#: 獨立的鎖共用一個失效點，理由與 `test_schedule_capability_parity._SCAN_FLOOR` 逐字同源）。
_CARRIER_SURFACE_FLOOR = 47


class CarrierPrimitivesHaveOneHomeTest(unittest.TestCase):
    """排程器原語只能住在宣告過的家裡（A-02 把 A-01 那條缺口變成會轉紅的事件）。"""

    def test_the_scan_surface_is_measured_and_has_not_shrunk(self) -> None:
        surface = _carrier_scan_surface()
        self.assertGreaterEqual(len(surface), _CARRIER_SURFACE_FLOOR,
                                f"掃描面只有 {len(surface)} 支 < 下限 "
                                f"{_CARRIER_SURFACE_FLOOR} ⇒ 射程疑似被改窄")
        for home in _CARRIER_HOMES:
            self.assertIn(home, surface, f"宣告過的家 {home} 不在掃描面內 ⇒ 這道鎖失去錨點")

    def test_every_declared_home_and_exemption_really_exists_and_has_a_reason(self) -> None:
        """名冊不是免死金牌：指向一個不存在的檔、或理由留空，都不算宣告。

        先例＝`TestR75IronLawMechanismSubstance`（具名機械物必須真的存在），
        以及本檔 `_LAUNCHD_ONLY` 那條「白名單要有代價」的同一條紀律。
        """
        for rel, why in {**_CARRIER_HOMES, **_CARRIER_EXEMPT}.items():
            with self.subTest(rel):
                self.assertTrue((_REPO_ROOT / rel).is_file(), f"{rel} 不存在")
                self.assertTrue(why.strip(), f"{rel} 的理由留空 ⇒ 不算宣告")

    def test_no_file_outside_the_declared_homes_drives_a_scheduler(self) -> None:
        allowed = set(_CARRIER_HOMES) | set(_CARRIER_EXEMPT)
        sites = [s for s in carrier_primitive_sites(_carrier_scan_surface())
                 if s.rsplit(":", 1)[0] not in allowed]
        self.assertEqual(sites, [],
                         "有檔自己驅動排程器（列舉／註冊／移除）而不問 "
                         "`schedule_backend.select()`：" + str(sites))

    def test_red_the_a01_original_form_is_caught(self) -> None:
        """合成注入（紅）＝A-01 的原形逐字。舊判準（只掃 `os.name`）對它完全失明。"""
        injected = ('def sentinel_task_names():\n'
                    '    rc, out = _powershell(\n'
                    '        f"Get-ScheduledTask | Where-Object {{ $_.TaskName -like '
                    '\'{TASK_PREFIX}*\' }}")\n'
                    '    return []\n')
        self.assertTrue(carrier_primitive_sites({"tools/lib/x.py": injected}),
                        "A-01 的原形竟然被放行")

    def test_red_a_raw_launchctl_spawn_is_caught(self) -> None:
        """反方向注入（紅）：mac 側原語也一樣——不是只擋 Windows 那一種寫法。"""
        injected = ('import subprocess\n'
                    'def names():\n'
                    '    return subprocess.run(["launchctl", "list"])\n')
        self.assertTrue(carrier_primitive_sites({"tools/lib/y.py": injected}))

    def test_green_prose_that_merely_mentions_a_cmdlet_is_not_a_site(self) -> None:
        """對照組（綠）：散文／訊息裡提到 cmdlet **不得**判違規。

        沒有這一條，全庫 20 餘筆說明文字會變成要逐一辯護的假紅，而那種鎖活不過一輪。
        """
        innocent = ('def hint():\n'
                    '    print("憑證查法：Get-ScheduledTask | Get-ScheduledTaskInfo")\n'
                    '    return "launchctl print gui/501/<label>"\n')
        self.assertEqual(carrier_primitive_sites({"tools/lib/z.py": innocent}), [])

    def test_a_file_that_cannot_be_parsed_is_a_violation_not_a_pass(self) -> None:
        self.assertTrue(carrier_primitive_sites({"tools/lib/broken.py": "def f(:\n"}))


#: 三個後端**共同**的契約面。`select()` 的呼叫端只准依賴這一組。
_BACKENDS = (sb.SchtasksBackend, sb.LaunchdBackend, sb.NoCarrierBackend)
#: launchd 專屬的公開成員。它們**可以**不對稱，條件是「外面沒有人依賴它」——所以
#: 下面那條測試不是把它們列進白名單就算了，而是要求它們在 repo 內零外部消費者。
_LAUNCHD_ONLY = ("domain", "plist_path")


def surface_of(backend: type) -> set[str]:
    return {n for n in dir(backend) if not n.startswith("_")}


def _outside_consumers(name: str) -> list[Path]:
    """repo 內（扣掉後端自己與本測試）有哪些 `.py` 在呼叫 `.<name>(`。

    `AISDLC_SDD/**` 各版依 Copy-on-Evolve 凍結，不在射程內（掃它只會掃到與本主題
    無關的同名方法）。
    """
    mine = {_REPO_ROOT / "tools" / "lib" / "schedule_backend.py", Path(__file__)}
    return [p for p in _REPO_ROOT.rglob("*.py")
            if p not in mine and ".venv" not in p.parts
            and "AISDLC_SDD" not in p.parts
            and f".{name}(" in p.read_text(encoding="utf-8", errors="replace")]


def symmetry_problems(backends: tuple, launchd_only: tuple[str, ...]) -> list[str]:
    """三個後端的契約面必須逐字相同（扣掉宣告過的 launchd 專屬成員）。純函式。"""
    surfaces = {b.__name__: surface_of(b) - set(launchd_only) for b in backends}
    shared = set.intersection(*surfaces.values())
    return [f"`{name}` 的契約面與其他後端不同：多了 {sorted(members - shared)}"
            for name, members in surfaces.items() if members != shared]


class BackendInterfaceIsSymmetricTest(unittest.TestCase):
    """🔴 R83／F2-⑤：三個排程後端的契約面必須**對稱**。

    立案與 A-01／A-06 訂正史料搬遷，原文＝Guard_Repin 證據檔 §E-3。這道鎖
    **兩個方向都紅**——只給一個後端加方法會紅，從一個後端拿掉共同方法也會紅。
    """

    def test_green_the_three_backends_agree_today(self) -> None:
        self.assertEqual(symmetry_problems(_BACKENDS, _LAUNCHD_ONLY), [])

    def test_list_jobs_is_on_the_shared_contract_face(self) -> None:
        """回補之後它必須是**共同**契約面（三個後端都有），而不是又只補一邊。"""
        for backend in _BACKENDS:
            self.assertIn("list_jobs", surface_of(backend), backend.__name__)

    def test_red_a_method_added_to_only_one_backend(self) -> None:
        """注入①：只有一個後端有的方法必紅。

        🔴 注入用的名字由 `list_jobs` 換成 `list_orphans`（R83 複審 A-01 回補之後，
        `list_jobs` 已經是**真的共同契約面**，拿它當單邊注入就再也構造不出紅 ⇒ 那會讓這一條
        變成恆綠的假鎖）。判準本身一字未改，換的只是注入語料——上一條測試守的才是
        「`list_jobs` 三個後端都有」這件事。
        """
        class OnlyHere(sb.NoCarrierBackend):
            def list_orphans(self, prefix: str) -> list:
                return []

        problems = symmetry_problems((sb.SchtasksBackend, OnlyHere), _LAUNCHD_ONLY)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("list_orphans", problems[0])

    def test_red_a_shared_method_removed_from_one_backend(self) -> None:
        """注入②＝反方向：把共同方法從一個後端拿掉也必須紅。

        兩個方向都要驗——只鎖「不准多」的話，把某個後端的方法刪掉（於是換平台就
        `AttributeError`）同樣會綠，而那正是本輪要治的形狀。
        """
        crippled = type("NoHintBackend", (), {
            k: v for k, v in vars(sb.NoCarrierBackend).items()
            if not k.startswith("__") and k != "evidence_hint"})
        problems = symmetry_problems((sb.SchtasksBackend, crippled), _LAUNCHD_ONLY)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("evidence_hint", problems[0])

    def test_the_launchd_only_exemptions_really_have_no_outside_consumer(self) -> None:
        """白名單不是免死金牌：每一項都必須零外部消費者，否則它就是契約面的一部分。

        少了這一條，下一個人只要把新方法加進 `_LAUNCHD_ONLY` 就能繞過整道鎖（實測：
        把 `evidence_hint` 塞進白名單，對稱判準當場轉綠）——那正是本 repo 判過的
        「有鎖在守假話」：檔案在、判準在、測試全綠。
        """
        for name in (*_LAUNCHD_ONLY, "evidence_hint"):
            users = sorted(p.relative_to(_REPO_ROOT).as_posix()
                           for p in _outside_consumers(name))
            if name == "evidence_hint":
                # 合成紅：本輪 `quota_gate` 真的在消費它 ⇒ 它**不可以**被列為豁免。
                self.assertTrue(users, "控制組失效：evidence_hint 竟然沒有外部消費者，"
                                       "那本測試對『白名單被濫用』就沒有鑑別力")
                continue
            self.assertEqual(users, [], f"`{name}` 有外部消費者 {users} ⇒ 它是契約面，"
                                        "不得列為 launchd 專屬豁免")

    def test_every_backend_can_actually_answer_the_evidence_question(self) -> None:
        """接線面（判定綠不代表接上了電）：三個後端都真的說得出一句取證指引。

        且**三句必須彼此不同**——「有排程載具但查法不同」與「根本沒有載具」外觀相同時，
        就回到本輪 F2-② 的病：憑證是真的、指路是假的。
        """
        hints = [b().evidence_hint() for b in _BACKENDS]
        self.assertEqual(len(set(hints)), 3, hints)
        self.assertIn("NextRunTime", hints[0])
        self.assertIn("launchctl", hints[1])
        self.assertNotIn("Get-ScheduledTask", hints[1],
                         "mac 的取證指引印 Windows cmdlet ⇒ 憑證是真的、指路是假的")
        self.assertNotIn("launchctl", hints[0])
        self.assertIn("沒有排程載具", hints[2])


class RecyclingArmIsWiredTest(unittest.TestCase):
    """🔴 R83 複審 A-01（本輪最嚴重的一筆）：mac 的續航「武裝接通了、回收一行都沒接」。

    立案實測史料搬遷，原文＝Guard_Repin 證據檔 §E-4。

    本類守三件事，缺一個都會讓修復退回去：
      ① 接線（回收臂真的問 `select()`）；
      ② 列舉層把「量不到」與「量到零」分開（`None` vs `[]`）——A-01 的表徵就是這兩者塌成一個；
      ③ **回報**：量不到時 `main()` 不得 rc=0 說「沒有任何工作」。
    """

    def test_both_recycling_arms_go_through_the_single_question(self) -> None:
        source = _SENTINEL_SRC.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for name in ("sentinel_task_names", "_remove_task"):
            with self.subTest(name):
                fn = next(n for n in ast.walk(tree)
                          if isinstance(n, ast.FunctionDef) and n.name == name)
                self.assertIn("schedule_backend.select", ast.unparse(fn),
                              f"`{name}` 沒有問唯一提問點 ⇒ 它又自己決定載具了")

    def test_the_sentinel_module_carries_no_scheduler_primitive_of_its_own(self) -> None:
        """具名斷言（不是只靠上面那道全庫掃描）：射程縮小時必須指名道姓地紅。

        體例同 `test_context_budget_guard.py` 對 `tools/lib/quota_meter.py` 的具名 `assertIn`
        ——有人把 glob 改窄時，只讓總數少一是看不見的。
        """
        rel = "tools/lib/sentinel_lifecycle.py"
        self.assertIn(rel, _carrier_scan_surface())
        self.assertEqual(
            carrier_primitive_sites({rel: _SENTINEL_SRC.read_text(encoding="utf-8")}), [],
            "回收臂又自持排程器原語了（A-01 復發）")

    def test_launchd_enumeration_parses_the_three_column_output(self) -> None:
        """`launchctl list` 是 `PID\\tStatus\\tLabel` 三欄；取最後一欄，並照前綴過濾。"""
        out = ("PID\tStatus\tLabel\n"
               "-\t0\tAutoSDD_Sentinel_abc\n"
               "912\t0\tcom.apple.something\n"
               "-\t0\tAutoSDD_Sentinel_def\n")
        seen: list[list[str]] = []
        real = sb._run
        sb._run = _fake_runner({"list": (0, out)}, seen)
        self.addCleanup(setattr, sb, "_run", real)
        self.assertEqual(sb.LaunchdBackend().list_jobs("AutoSDD_Sentinel_"),
                         ["AutoSDD_Sentinel_abc", "AutoSDD_Sentinel_def"])
        self.assertEqual(seen[0][:2], ["launchctl", "list"])

    def test_a_failed_enumeration_is_unmeasurable_not_empty(self) -> None:
        """🔴 A-01 的核心：rc 非 0 ⇒ `None`（量不到），**不是** `[]`（量到零）。

        修前這一格回 `[]`，而 `[]` 讓 GC 回報「沒有任何工作要收」⇒ 假陰性被回報成成功。
        """
        seen: list[list[str]] = []
        real = sb._run
        sb._run = _fake_runner({"list": (127, "")}, seen)
        self.addCleanup(setattr, sb, "_run", real)
        self.assertIsNone(sb.LaunchdBackend().list_jobs("AutoSDD_Sentinel_"))
        # 對照組：同一支後端在 rc=0、輸出裡真的沒有哨兵時，必須回 `[]` 而不是 `None`
        #（否則 mac 上每一次 GC 都會 fail-loud，而那是假的告警）。
        sb._run = _fake_runner({"list": (0, "-\t0\tcom.apple.x\n")}, seen)
        self.assertEqual(sb.LaunchdBackend().list_jobs("AutoSDD_Sentinel_"), [])

    def test_the_windows_enumeration_uses_the_planner_carrier_and_gates_on_rc(self) -> None:
        """Windows 那一側：載具必須是 `planner.run_powershell`（帶 `NO_WINDOW` ＋ UTF-8 前置行）。

        直接用本檔的 `_run` 會在無 console 的父行程（pythonw hook）下替使用者彈一個視窗，
        而 `schedule_backend._run` 一個旗標都不帶——那正是〈鐵律一之二〉在治的病。
        """
        scripts: list[str] = []

        def _fake(script: str):
            scripts.append(script)
            return subprocess.CompletedProcess(
                args=[], returncode=0, stderr="",
                stdout="AutoSDD_Sentinel_abc\nAutoSDD_Sentinel_def\n")
        real = planner.run_powershell
        planner.run_powershell = _fake
        self.addCleanup(setattr, planner, "run_powershell", real)
        self.assertEqual(sb.select(os_name="nt").list_jobs("AutoSDD_Sentinel_"),
                         ["AutoSDD_Sentinel_abc", "AutoSDD_Sentinel_def"])
        self.assertIn("Get-ScheduledTask", scripts[0])
        self.assertNotIn("schtasks /query", scripts[0],
                         "`schtasks /query` 在本機實測回空＝假陰性（根 CLAUDE.md）")
        # rc 非 0 ⇒ 量不到（不是「沒有工作」）。
        planner.run_powershell = lambda script: subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="boom")
        self.assertIsNone(sb.select(os_name="nt").list_jobs("AutoSDD_Sentinel_"))

    def test_no_carrier_measures_zero_rather_than_unmeasurable(self) -> None:
        """沒有載具的平台上「有幾支哨兵」是有確定答案的——零。回 `None` 會製造假告警。"""
        self.assertEqual(
            sb.select(os_name="posix", platform_name="linux").list_jobs("X"), [])

    def test_gc_reports_unmeasurable_as_unmeasurable(self) -> None:
        """行為鎖：列舉量不到 ⇒ `gc()` 回 `None`；量到零 ⇒ 回 `[]`。兩者不得塌成一個。"""
        with mock.patch.object(sentinel_lifecycle, "sentinel_task_names",
                               return_value=None):
            self.assertIsNone(sentinel_lifecycle.gc())
        with mock.patch.object(sentinel_lifecycle, "sentinel_task_names",
                               return_value=[]):
            self.assertEqual(sentinel_lifecycle.gc(), [])

    def test_the_cli_never_reports_a_false_negative_as_success(self) -> None:
        """🔴 A-01 的**回報**那一半：修前兩個結局共用同一句話與同一個 rc=0。

        這一條走真的 `main()` 並斷言 rc ＋ 印到哪個流——判準看的是使用者真的會看到的東西，
        不是原始碼字面（字面判準會被等價改寫繞過）。
        """
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with mock.patch.object(sentinel_lifecycle, "sentinel_task_names",
                               return_value=None), \
                contextlib.redirect_stdout(buf_out), \
                contextlib.redirect_stderr(buf_err):
            rc = sentinel_lifecycle.main([])
        self.assertEqual(rc, 1, "列舉量不到竟然回 rc=0 ⇒ 假陰性被回報成成功")
        self.assertIn("量不到", buf_err.getvalue())
        self.assertEqual(buf_out.getvalue(), "", "量不到的訊息必須走 stderr")
        # 對照組：量到零 ⇒ rc=0，而且那句話必須說得出「這是量到的零」。
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with mock.patch.object(sentinel_lifecycle, "sentinel_task_names",
                               return_value=[]), \
                contextlib.redirect_stdout(buf_out), \
                contextlib.redirect_stderr(buf_err):
            rc = sentinel_lifecycle.main([])
        self.assertEqual(rc, 0)
        self.assertIn("量到的零", buf_out.getvalue())


#: 憑證鍵字面的唯一的家＝`schedule_backend.CRED_KEY_*`。
_CRED_KEY_LITERALS = (sb.CRED_KEY_SCHTASKS, sb.CRED_KEY_LAUNCHD)


def credential_key_copies(source: str) -> list[str]:
    """在**程式碼**（非註解）裡直接寫出憑證鍵字面的站點。純函式，紅綠由注入自證。

    兩條刻意的排除，各自有理由（都是實測出來的假紅來源）：
      · **註解**：解釋「Windows＝next_run_time、mac＝schedule_credential」是在說明語意，
        不是第二個實作。掃註解會把說明判成違規——本 repo 判過的假紅形態。
      · **同名函式**：`next_run_time` 也是本檔一支解析函式的名字（`def next_run_time(text)`），
        它與「鍵名」毫無關係。所以判準只認鍵**真正會出現的兩種形態**：引號字串，或
        `key=` 這種 kwarg／賦值；`def key(` 與 `key(...)` 這種呼叫一律不算。
    """
    hits = []
    for lineno, line in enumerate(source.splitlines(), 1):
        code = line.split("#")[0]
        for key in _CRED_KEY_LITERALS:
            quoted = f'"{key}"' in code or f"'{key}'" in code
            if quoted or re.search(rf"\b{re.escape(key)}\s*=", code):
                hits.append(f"{lineno}:{key}")
    return hits


class CredentialKeyHasOneHomeTest(unittest.TestCase):
    """🔴 R83／F2-④：憑證鍵名住兩個家，而改鍵名時**不會有東西轉紅**。

    立案實查史料搬遷，原文＝Guard_Repin 證據檔 §E-5。
    """

    def test_the_planner_carries_no_literal_copy(self) -> None:
        source = (_REPO_ROOT / "tools" / "session_resume_planner.py").read_text(
            encoding="utf-8")
        self.assertEqual(credential_key_copies(source), [],
                         "planner 又自己寫了一份憑證鍵字面 ⇒ 改鍵名時只會改到一個家")

    def test_red_the_three_sites_this_round_removed_would_be_caught(self) -> None:
        """注入＝修前的那三行原形 ⇒ 必紅（證明這道鎖抓得到本輪修掉的東西）。"""
        injected = ('state.update(next_run_time="", schedule_credential="")\n'
                    'state.update(next_run_time="", schedule_credential="")\n'
                    '             next_run_time="", schedule_credential="")\n')
        self.assertEqual(len(credential_key_copies(injected)), 6)

    def test_a_comment_that_explains_the_keys_is_not_a_second_home(self) -> None:
        """對照組：註解裡點名兩個鍵**必須**放行（planner 現存兩處就是這種）。"""
        self.assertEqual(credential_key_copies(
            "# 憑證寫進該後端自己的鍵（Windows＝next_run_time、mac＝schedule_credential）\n"
            "state[schedule_backend.select().credential_key] = moment\n"), [])

    def test_clearing_a_credential_clears_both_keys(self) -> None:
        """行為面：終態必須把**兩個**鍵一起清空，只清一個等於留下一個過期憑證。"""
        cleared = planner._cleared_credentials()
        self.assertEqual(set(cleared), set(_CRED_KEY_LITERALS))
        self.assertEqual(set(cleared.values()), {""})
        # 接線：清空之後 `relay_problems()` 必須判「沒有憑證」（否則清了也沒用）。
        base = {**{k: "x" for k in _CRED_KEY_LITERALS}, "state": "armed"}
        self.assertTrue(planner.relay_problems({**base, **cleared}))


class MacCredentialTest(unittest.TestCase):
    """② mac 憑證的鑑別力，以及「沒有憑證就不准宣稱已排程」的等價強度。"""

    _WANT_ARGV = ["/py", "/planner.py", "--sentinel-tick", "--plan", "plan-fixture.md"]
    _GOOD = {"interval": 900, "argv": _WANT_ARGV, "path": "/x/y.plist", "state": "waiting"}

    def test_a_matching_readback_is_a_credential(self) -> None:
        self.assertEqual(sb._descriptor_problems(self._GOOD, self._WANT_ARGV, 900), [])

    def test_each_of_the_three_pieces_can_fail_on_its_own(self) -> None:
        """合成注入（紅）：三件式憑證的每一件單獨壞掉都要轉紅。

        逐件注入而不是只驗「全對」：三件裡若有一件其實沒被比對，全對那條照樣綠。
        """
        for name, broken in (
            ("interval 漂移", {**self._GOOD, "interval": 300}),
            ("interval 量不到", {**self._GOOD, "interval": None}),
            ("argv 不符", {**self._GOOD, "argv": [*self._WANT_ARGV, "--extra"]}),
            ("launchd 沒報 plist path", {**self._GOOD, "path": "   "}),
        ):
            with self.subTest(name):
                self.assertTrue(sb._descriptor_problems(broken, self._WANT_ARGV, 900),
                                f"{name} 竟然被判成合格憑證")

    def test_the_mac_credential_never_states_a_next_run_time(self) -> None:
        """誠實劃界的機械物：憑證字串裡**不得**出現任何時刻。

        launchd 不報「下次幾點跑」（實測：print 輸出裡 next／fire／due 皆不存在），任何
        時刻都只能是我們自己推算的。憑證裡放一個推算時刻，就是把它偽裝成排程器的陳述
        ——而那正是 Windows 側 `NextRunTime` 之所以能當憑證的理由被掏空的方式。
        """
        cred = sb.LaunchdBackend()._credential("AutoSDD_Sentinel_x", self._GOOD)
        import re
        self.assertIsNone(re.search(r"\d{1,2}:\d{2}", cred), f"憑證裡混進了時刻：{cred}")
        for piece in ("launchctl print rc=0", "run interval", "plist ="):
            self.assertIn(piece, cred)

    def test_the_credential_line_says_out_loud_what_it_cannot_prove(self) -> None:
        line = sb.LaunchdBackend().credential_line("cred")
        for piece in ("不是** NextRunTime", "pmset"):
            self.assertIn(piece, line)

    def test_armed_without_any_credential_is_still_refused(self) -> None:
        """mac 的守衛強度必須與 Windows **等價**：兩個憑證鍵皆空 ⇒ 不准 armed／waiting。"""
        base = {"schema": planner.RELAY_SCHEMA, "session_id": "s", "plan_path": "p",
                "state": "armed", "kind": "sentinel", "reset_at": "",
                "reset_source": "operator", "attempts": 0, "max_attempts": 5,
                "allow_resume": False, "task_name": "T"}
        self.assertTrue(planner.relay_problems(base), "兩鍵皆空竟然放行")
        self.assertTrue(planner.relay_problems({**base, "next_run_time": "  ",
                                                "schedule_credential": ""}))
        # 各後端用自己的鍵都要成立（否則等於把 mac 那一側整個關掉）。
        self.assertEqual(planner.relay_problems({**base, "next_run_time": "2026/8/9 09:02"}), [])
        self.assertEqual(planner.relay_problems({**base, "schedule_credential": "launchd …"}), [])


def _fake_runner(table: dict[str, tuple[int, str]], seen: list[list[str]]):
    """`schedule_backend._run` 的替身：依 argv 的第二個字決定回什麼。"""
    def _run(argv: list[str], timeout: int = 60) -> tuple[int, str]:
        seen.append(list(argv))
        key = argv[1] if len(argv) > 1 else argv[0]
        return table.get(key, (0, ""))
    return _run


def _print_output(interval: int, argv: list[str], path: str,
                  calendar: dict | None = None) -> str:
    """合成一份 `launchctl print` 輸出（欄位與真機實測逐字同形）。

    R83／QA 訂正史料搬遷（fixture 從扁平改巢狀），原文＝Guard_Repin 證據檔 §E-6。
    子區塊刻意放在 `arguments` 之後、`run interval` 之前，與真機的欄位順序一致。
    """
    lines = ["gui/501/L = {", f"\tpath = {path}", "\tstate = not running",
             "\targuments = {"]
    lines += [f"\t\t{a}" for a in argv]
    lines += ["\t}"]
    for kind in ("resource", "jetsam"):
        lines += [f"\t{kind} coalition = {{", "\t\tID = 2027", f"\t\ttype = {kind}",
                  "\t\tstate = active", "\t}"]
    lines += [f"\trun interval = {interval} seconds"]
    # 🔴 R83-B：`StartCalendarInterval` 的回讀形狀取自真機實測（`launchctl print
    # gui/501/com.autoclaude.nightly` 當回合逐字）。它**不是**一個扁平欄位——住在
    # `event triggers` → `<label>.<launchd 自編的數字>` → `descriptor` 裡（depth 4），
    # 而同一份輸出後面還有一個 `event channels` 區塊也用 `"鍵" => 值` 的形態。
    # 兩件都照抄進 fixture 的理由與 R83／QA 那次巢狀訂正逐字同構：**fixture 比真實世界簡單
    # 就是最貴的一種假綠**（那一次扁平 fixture 讓 30 條綠全數成立，而真機憑證在說假話）。
    # `event channels` 裡刻意放一個 `"port" => …`：解析器若不用 `_CAL_KEYS` 白名單而是
    # 「看到 `=>` 就收」，它就會把 port 收進 calendar ⇒ 這個誘餌讓那種寫法轉紅。
    if calendar:
        lines += ["\tevent triggers = {", "\t\tcom.example.job.268435470 => {",
                  "\t\t\tkeepalive = 0", "\t\t\tservice = L",
                  "\t\t\tstream = com.apple.launchd.calendarinterval",
                  "\t\t\tmonitor = com.apple.UserEventAgent-Aqua",
                  "\t\t\tdescriptor = {"]
        lines += [f'\t\t\t\t"{k}" => {v}' for k, v in calendar.items()]
        lines += ["\t\t\t}", "\t\t}", "\t}", '\tevent channels = {',
                  '\t\t"com.apple.launchd.calendarinterval" = {',
                  '\t\t\t"port" => 563971', "\t\t}", "\t}"]
    lines += ["}"]
    return "\n".join(lines) + "\n"


class ArmRefusesToClaimWithoutReadbackTest(unittest.TestCase):
    """② 的核心：`arm()` 拿不到相符的回讀就**不准**回傳憑證（＝不准宣稱已排程）。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="r83_agents_"))
        self.plan = self.tmp / "plan.md"
        self.plan.write_text("# plan\n", encoding="utf-8", newline="\n")
        self._real_dir = sb.LAUNCH_AGENTS_DIR
        sb.LAUNCH_AGENTS_DIR = self.tmp / "LaunchAgents"
        self.addCleanup(setattr, sb, "LAUNCH_AGENTS_DIR", self._real_dir)
        self._real_run = sb._run
        self.addCleanup(setattr, sb, "_run", self._real_run)
        self.seen: list[list[str]] = []

    def _arm(self, print_rc: int, print_out: str, task: str = "AutoSDD_Sentinel_t"):
        sb._run = _fake_runner({"-lint": (0, ""), "print": (print_rc, print_out),
                                "bootstrap": (0, ""), "bootout": (0, "")}, self.seen)
        # `at_expr` 傳一個明顯是 PowerShell 語法的字串：launchd 必須把它整個忽略掉，
        # 而不是拿去做任何事（參數被無聲使用與被無聲忽略一樣糟）。
        return sb.LaunchdBackend().arm(str(self.plan), task,
                                       "(Get-Date).AddHours(5)", planner.SENTINEL_TICK)

    def _want_argv(self, task: str = "AutoSDD_Sentinel_t") -> list[str]:
        return sb.LaunchdBackend()._argv(planner, str(self.plan), task, planner.SENTINEL_TICK)

    def _want_path(self, task: str = "AutoSDD_Sentinel_t") -> str:
        return str(sb.LaunchdBackend().plist_path(task))

    def test_a_matching_readback_yields_a_credential_and_rc_zero(self) -> None:
        rc, cred = self._arm(0, _print_output(planner.SENTINEL_INTERVAL_SECONDS,
                                              self._want_argv(), self._want_path()))
        self.assertEqual(rc, 0)
        self.assertIn("launchd", cred)
        self.assertTrue((sb.LAUNCH_AGENTS_DIR / "AutoSDD_Sentinel_t.plist").is_file())

    def test_an_absent_job_is_not_a_credential(self) -> None:
        """合成注入（紅）：bootstrap 回 0 但 launchd 查不到（rc=113）⇒ 一律 rc=1、憑證空。

        這一格就是「我下了指令」≠「它真的排進去了」。
        """
        rc, cred = self._arm(sb.LAUNCHCTL_ENOENT_RC, "")
        self.assertEqual((rc, cred), (1, ""))

    def test_a_drifted_descriptor_is_not_a_credential(self) -> None:
        """合成注入（紅）：有這支 job、但 launchd 拿著的參數不是我要的那組。

        少了這一件，「有一支同名工作」與「有一支會做正確事情的工作」分不開。
        """
        rc, cred = self._arm(0, _print_output(7, self._want_argv(), self._want_path()))
        self.assertEqual((rc, cred), (1, ""))
        rc, cred = self._arm(0, _print_output(planner.SENTINEL_INTERVAL_SECONDS,
                                              ["/wrong/python"], self._want_path()))
        self.assertEqual((rc, cred), (1, ""))

    def test_the_state_in_the_credential_is_the_jobs_own_not_a_nested_blocks(self) -> None:
        """🔴 R83／QA 複驗抓到的真紅：憑證的 `state` 欄回報的是**巢狀子區塊**的值。

        真機實測（QA 當回合）：`launchctl list` 印 PID `-`、`launchctl print` 最外層逐字
        `state = not running`，而同一刻憑證印 `state = active`。成因是 `launchctl print`
        的輸出裡 `state = ` 出現三次，解析器「掃到就覆蓋」⇒ 最後一個（jetsam coalition 的
        `active`，恆為 active）贏。job 第一次執行**之前**那兩個子區塊還不存在，所以這個
        缺陷躲過了武裝當下那一次取證，只在跑過一次之後才出現。

        它不參與閘門判定（`_descriptor_problems` 不看 state）⇒ 不會造成假武裝；但它寫在
        **憑證字串**裡，而憑證是〈反事後諸葛〉那條規則要求貼出來的那一行。憑證裡混一句
        假話，比缺那一欄更難看見——本 repo 對「有鎖在守假話」的判例同型。
        """
        out = _print_output(planner.SENTINEL_INTERVAL_SECONDS, self._want_argv(),
                            self._want_path())
        self.assertEqual(out.count("state = active"), 2, "fixture 沒有真機的巢狀塊")
        sb._run = _fake_runner({"print": (0, out)}, self.seen)
        live = sb.LaunchdBackend()._readback("AutoSDD_Sentinel_t")
        # 綠：取的是最外層那一個。紅（修復前的行為）：這裡會是 "active"。
        self.assertEqual(live["state"], "not running")
        self.assertNotIn("state = active",
                         sb.LaunchdBackend()._credential("AutoSDD_Sentinel_t", live))

    def test_verify_refuses_a_job_it_did_not_arm(self) -> None:
        """🔴 R83／QA 複驗抓到的第二筆真紅：`verify_cli` 只驗「存在」，卻印「相符」。

        真機重現（QA 當回合）：把 label 換成每 7 秒跑一次 `/bin/echo I-AM-NOT-THE-SENTINEL`
        的 plist 再 bootstrap，`--verify-schtasks` 仍回 **rc=0** 並逐字印
        「run interval = 7 seconds〔launchd 回讀，與請求相符〕｜argv 回讀 2 項相符」。
        兩句話都是假的——那條路上 `_descriptor_problems` 一次都沒被呼叫過。
        Windows 那一側沒有對稱的洞：`NextRunTime` 是排程器自己算的值，不需要比對請求。
        """
        good = {"interval": planner.SENTINEL_INTERVAL_SECONDS,
                "argv": self._want_argv(), "path": self._want_path(), "state": "not running"}
        self.assertEqual(sb.LaunchdBackend()._verify_problems("AutoSDD_Sentinel_t", good), [])
        for name, broken in (
            ("間隔不是現行常數", {**good, "interval": 7}),
            ("跑的根本不是 planner", {**good, "argv": ["/bin/echo", "I-AM-NOT-THE-SENTINEL"]}),
            ("載入的是別人的 plist", {**good, "path": "/tmp/someone_elses.plist"}),
        ):
            with self.subTest(name):
                self.assertTrue(
                    sb.LaunchdBackend()._verify_problems("AutoSDD_Sentinel_t", broken),
                    f"{name} 竟然還發得出憑證")

    def _verify_cli(self, out: str) -> tuple[int, str]:
        """跑真的 `verify_cli` 並收 stdout（不是叫內部判準——見下面那條的 WHY）。"""
        sb._run = _fake_runner({"print": (0, out)}, self.seen)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            rc = sb.LaunchdBackend().verify_cli("AutoSDD_Sentinel_t")
        return rc, buf.getvalue()

    def test_the_verify_arm_is_actually_wired_to_its_own_gate(self) -> None:
        """🔴 判準的**接線**也要有人守，不只是判準本身。

        本測試是 QA 自證時抓到的第三個洞：上面兩條分別直呼 `_verify_problems` 與
        `_credential`，於是「把它們從 `verify_cli` 裡拆掉」這種退化**兩條都不會紅**
        （實測：把呼叫點改回 `self._credential(task_name, live)` → 33 條全綠）。
        機制蓋好沒接電，與沒蓋一樣——本 repo 對此有 R77 的判例。故這一條走整支
        `verify_cli`，斷言的是它**印出來的那一行**與它的 rc。
        """
        rc, printed = self._verify_cli(_print_output(
            planner.SENTINEL_INTERVAL_SECONDS, self._want_argv(), self._want_path()))
        self.assertEqual(rc, 0)
        self.assertIn("未逐項比對", printed)
        self.assertNotIn("逐項相符", printed)
        # 冒牌 job：存在（rc=0）但不是我們武裝的那一支 ⇒ 必須拒發憑證。
        rc, printed = self._verify_cli(_print_output(
            7, ["/bin/echo", "I-AM-NOT-THE-SENTINEL"], "/tmp/someone_elses.plist"))
        self.assertEqual(rc, 1)
        self.assertNotIn("✅", printed)

    def test_the_verify_credential_never_claims_a_comparison_it_did_not_make(self) -> None:
        """憑證裡的每一句話都必須對應這一次真的做過的比對（誠實劃界的機械物）。

        `verify_cli` 拿不到當初那份任務書的路徑 ⇒ argv **逐項**比對它做不到。做不到就要
        寫出來，不能沿用 `arm()` 那一句「逐項相符」——那正是把沒做的事說成做過了。
        """
        live = {"interval": 900, "argv": ["a", "b"], "path": "/p", "state": "not running"}
        armed = sb.LaunchdBackend()._credential("L", live)
        checked = sb.LaunchdBackend()._credential("L", live, argv_verified=False)
        self.assertIn("逐項相符", armed)
        self.assertNotIn("逐項相符", checked)
        self.assertIn("未逐項比對", checked)

    def test_a_label_that_could_escape_the_agents_directory_is_refused(self) -> None:
        """label 直接變成 `~/Library/LaunchAgents/<label>.plist` 的檔名 ⇒ 白名單式拒絕。"""
        for bad in ("../evil", "a/b", "with space", "", "..", "tab\there"):
            with self.subTest(bad):
                self.assertTrue(sb._unsafe_name(bad))
                rc, cred = self._arm(0, _print_output(900, [], "/a"), task=bad)
                self.assertEqual((rc, cred), (1, ""))
        self.assertFalse(sb._unsafe_name("AutoSDD_Sentinel_83021fb3-7651-4428"))

    def test_a_missing_plan_file_refuses_the_registration(self) -> None:
        """任務書不存在就不准註冊——與 Windows 註冊腳本第一行同一條規則。"""
        self.plan.unlink()
        rc, cred = self._arm(0, _print_output(900, [], "/a"))
        self.assertEqual((rc, cred), (1, ""))

    def test_the_plist_carries_the_four_things_the_job_cannot_work_without(self) -> None:
        """plist 內容鎖：少任一項，被叫起來的那一跑會**成立但做不了事**。"""
        self._arm(0, _print_output(planner.SENTINEL_INTERVAL_SECONDS,
                                   self._want_argv(), self._want_path()))
        body = plistlib.loads((sb.LAUNCH_AGENTS_DIR / "AutoSDD_Sentinel_t.plist").read_bytes())
        # ① 巡邏間隔取自 planner 的常數（不是本檔自己抄一個數字）。
        self.assertEqual(body["StartInterval"], planner.SENTINEL_INTERVAL_SECONDS)
        # ② cwd＝repo 根：R80 P0 在 mac 的對等（沒有它，續跑那一跑碰不到 repo 一個檔，
        #    而且 `-r` 也找不到 session——逐字稿目錄的 slug 是由 cwd 推出來的）。
        self.assertEqual(body["WorkingDirectory"], str(_REPO_ROOT))
        # ③ PATH：LaunchAgent 預設只有 `/usr/bin:/bin:/usr/sbin:/sbin`（真機實測），而
        #    探針要跑的 `claude` 通常裝在 `~/.local/bin` ⇒ 少了它，每一次真撞線後的探測
        #    都會是 FileNotFoundError → fail-closed → 永遠等下去。
        self.assertEqual(body["EnvironmentVariables"]["PATH"], os.environ.get("PATH", ""))
        # ④ RunAtLoad 必須是 False：哨兵是巡邏不是 nightly，載入即跑只會多一次無意義 tick。
        self.assertIs(body["RunAtLoad"], False)
        self.assertEqual(body["ProgramArguments"][2], planner.SENTINEL_TICK)


class SelfDisarmTest(unittest.TestCase):
    """③ 自我解除：**同步 bootout 會把自己殺掉**（真機實測，不是推論）。

    合成實驗逐字（R83 當回合，本機 macOS 25.5.0）：一支 LaunchAgent 的 job 在自己的
    行程裡跑 `launchctl bootout gui/<uid>/<自己>`，log 只留下 `start <epoch>` 這一行，
    `bootout` 那一行的 rc **從來沒有被寫出來**——行程死在那一句。
    後果不是「少一行 log」：`_sentinel_tick` 的 disarm／escalate 分支在解除**之後**還要
    叫人、還要寫稽核痕跡，同步拆會讓「正常下班」與「需要人介入」兩條路的痕跡一起消失，
    而那正是這整套續航唯一有價值的那一格。
    對照實驗（同一天、同一支 job）：改成 detached 延後拆之後，主行程把該寫的全部寫完、
    正常退場，3 秒後子行程才 bootout，`bootout rc=0`、`launchctl print` 隨即回 113。
    """

    def setUp(self) -> None:
        self._real_run, self._real_popen = sb._run, subprocess.Popen
        self.addCleanup(setattr, sb, "_run", self._real_run)
        self.addCleanup(setattr, subprocess, "Popen", self._real_popen)
        self._real_dir = sb.LAUNCH_AGENTS_DIR
        sb.LAUNCH_AGENTS_DIR = Path(tempfile.mkdtemp(prefix="r83_disarm_"))
        self.addCleanup(setattr, sb, "LAUNCH_AGENTS_DIR", self._real_dir)
        self.seen: list[list[str]] = []
        self.spawned: list[list[str]] = []
        subprocess.Popen = (  # type: ignore[assignment]
            lambda argv, **kw: self.spawned.append(list(argv)))
        self._real_xpc = os.environ.get("XPC_SERVICE_NAME")
        self.addCleanup(self._restore_xpc)

    def _restore_xpc(self) -> None:
        os.environ.pop("XPC_SERVICE_NAME", None)
        if self._real_xpc is not None:
            os.environ["XPC_SERVICE_NAME"] = self._real_xpc

    def test_disarming_from_inside_the_job_never_boots_itself_out_synchronously(self) -> None:
        os.environ["XPC_SERVICE_NAME"] = "AutoSDD_Sentinel_self"
        sb._run = _fake_runner({"print": (0, _print_output(900, [], "/a"))}, self.seen)
        rc = sb.LaunchdBackend().disarm("AutoSDD_Sentinel_self")
        self.assertEqual(rc, 0)
        self.assertEqual([a for a in self.seen if "bootout" in a], [],
                         "在自己身上同步 bootout ⇒ 本行程會被 launchd 當場終止")
        self.assertTrue(self.spawned, "延後拆也沒排 ⇒ 記憶體裡那一份永遠留著")
        self.assertIn("bootout", self.spawned[0][-1])

    def test_the_deferred_child_must_escape_the_job_process_group(self) -> None:
        """成因面：少了 `start_new_session=True`，launchd 拆 job 時會把子行程一起收走。

        那個失效是**靜默的**（延後那一拆永遠不會發生，而且沒有人會知道）。
        """
        recorded: dict = {}
        subprocess.Popen = lambda argv, **kw: recorded.update(kw)  # type: ignore[assignment]
        os.environ["XPC_SERVICE_NAME"] = "AutoSDD_Sentinel_self"
        sb._run = _fake_runner({}, self.seen)
        sb.LaunchdBackend().disarm("AutoSDD_Sentinel_self")
        self.assertIs(recorded.get("start_new_session"), True)

    def test_disarming_from_outside_verifies_by_readback_not_by_rc(self) -> None:
        os.environ.pop("XPC_SERVICE_NAME", None)
        sb._run = _fake_runner({"bootout": (0, ""),
                                "print": (sb.LAUNCHCTL_ENOENT_RC, "")}, self.seen)
        self.assertEqual(sb.LaunchdBackend().disarm("AutoSDD_Sentinel_other"), 0)
        self.assertTrue([a for a in self.seen if "bootout" in a])

    def test_a_job_that_survives_the_bootout_is_reported_as_a_failure(self) -> None:
        """合成注入（紅）：bootout rc=0 但東西還在 ⇒ 不准回 0。

        `launchctl load` 在本機實測對不存在的 plist 也回 **rc=0**（`install_mac_nightly.sh`
        檔頭記載的同一個病）⇒ rc 從來就不是憑證，查得到查不到才是。
        """
        os.environ.pop("XPC_SERVICE_NAME", None)
        sb._run = _fake_runner({"bootout": (0, ""),
                                "print": (0, _print_output(900, [], "/a"))}, self.seen)
        self.assertEqual(sb.LaunchdBackend().disarm("AutoSDD_Sentinel_other"), 1)


class CalendarMomentReachesThePlistTest(unittest.TestCase):
    """🔴 R83-B ⑤：`arm_reset` 要求的**時刻**必須真的到得了 launchd，而憑證必須說實話。

    修前實況的逐位元組實測史料搬遷，原文＝Guard_Repin 證據檔 §E-7。

    本類別守的四件事，每一件都附合成注入的紅：
      ① 真的截止時刻 ⇒ plist 必須帶 `StartCalendarInterval`（相異時刻 ⇒ 相異 plist）；
      ② 回讀不含那個時刻 ⇒ **不准發憑證**（rc=1、憑證空）；
      ③ 巡邏那一支刻意**不**帶 calendar（否則每 15 分鐘就要 bootout+bootstrap 一輪）；
      ④ 分鐘粒度只准往後取整，絕不提早（提早＝白燒一次探測，而探測是唯一花 token 的動作）。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="r83b_cal_"))
        self.plan = self.tmp / "plan.md"
        self.plan.write_text("# plan\n", encoding="utf-8", newline="\n")
        self._real_dir = sb.LAUNCH_AGENTS_DIR
        sb.LAUNCH_AGENTS_DIR = self.tmp / "LaunchAgents"
        self.addCleanup(setattr, sb, "LAUNCH_AGENTS_DIR", self._real_dir)
        self._real_run = sb._run
        self.addCleanup(setattr, sb, "_run", self._real_run)
        self.seen: list[list[str]] = []
        self.task = "AutoSDD_Sentinel_cal"
        self.now = datetime.now().astimezone()

    def _argv(self) -> list[str]:
        return sb.LaunchdBackend()._argv(planner, str(self.plan), self.task,
                                        planner.SENTINEL_TICK)

    def _arm(self, at, readback_cal: dict | None, *, print_rc: int = 0):
        """武裝一次。`readback_cal` ＝**launchd 假裝回讀到**的 calendar（注入縫）。"""
        out = _print_output(planner.SENTINEL_INTERVAL_SECONDS, self._argv(),
                            str(sb.LaunchdBackend().plist_path(self.task)),
                            calendar=readback_cal)
        sb._run = _fake_runner({"-lint": (0, ""), "print": (print_rc, out),
                                "bootstrap": (0, ""), "bootout": (0, "")}, self.seen)
        return sb.LaunchdBackend().arm(str(self.plan), self.task,
                                       "(Get-Date).AddHours(5)", planner.SENTINEL_TICK, at)

    def _plist(self) -> dict:
        return plistlib.loads((sb.LAUNCH_AGENTS_DIR / f"{self.task}.plist").read_bytes())

    def test_a_real_deadline_becomes_a_start_calendar_interval_in_the_plist(self) -> None:
        at = self.now + timedelta(minutes=56)
        want = sb._calendar_of(at, planner.SENTINEL_INTERVAL_SECONDS)
        rc, cred = self._arm(at, want)
        self.assertEqual(rc, 0, cred)
        body = self._plist()
        self.assertEqual(body["StartCalendarInterval"], want)
        # `StartInterval` **必須同時還在**：它是自我修復的底盤（漏掉一次 calendar 不會讓
        # 哨兵死掉、自殺路徑仍結構上不存在）。真機 E3 實測兩者共存且 calendar 真的觸發。
        self.assertEqual(body["StartInterval"], planner.SENTINEL_INTERVAL_SECONDS)
        # 憑證必須把 launchd 自報的那個 descriptor 講出來，而不是含糊帶過。
        self.assertIn("StartCalendarInterval", cred)
        self.assertIn("launchd 自報", cred)

    def test_two_different_deadlines_no_longer_produce_the_same_plist(self) -> None:
        """🔴 這一條是修前那次逐位元組實測的**反向鎖**：相異指紋數必須是 2，不是 1。"""
        digests = []
        for minutes in (56, 240):
            at = self.now + timedelta(minutes=minutes)
            self._arm(at, sb._calendar_of(at, planner.SENTINEL_INTERVAL_SECONDS))
            digests.append(hashlib.sha256(
                (sb.LAUNCH_AGENTS_DIR / f"{self.task}.plist").read_bytes()).hexdigest())
        self.assertEqual(len(set(digests)), 2,
                         "相異截止時刻產出同一份 plist ⇒ 時刻又一次到不了載具（修前實況）")

    def test_red_a_readback_without_the_moment_is_not_a_credential(self) -> None:
        """合成注入（紅）：要求了時刻、launchd 回讀卻沒有 ⇒ 一律 rc=1、憑證空。

        少了這一向，「plist 我寫了」就會被當成「launchd 排了」——那正是 R59 事故的形狀。
        注意 bootstrap 在這個替身裡回 rc=0：**rc 從來不是憑證**，回讀才是。
        """
        at = self.now + timedelta(minutes=56)
        rc, cred = self._arm(at, None)
        self.assertEqual((rc, cred), (1, ""))

    def test_red_a_stale_moment_left_behind_is_not_a_credential(self) -> None:
        """合成注入（紅）：**沒有**要求時刻、回讀卻有一個 ⇒ 同樣不准發憑證。

        單向判準在這裡就是 R83 `verify_cli` 那個「憑證不回答那個問題」的重演：一支殘留
        著舊截止時刻的 job 會被判成相符，而憑證會說「參數就是我要的那組」。
        """
        rc, cred = self._arm(self.now + timedelta(seconds=900),
                             {"Month": 1, "Day": 1, "Hour": 3, "Minute": 0})
        self.assertEqual((rc, cred), (1, ""))

    def test_the_patrol_moment_deliberately_gets_no_calendar(self) -> None:
        """巡邏的 `at` 恆為 `now + interval` ⇒ 不寫 calendar，且必須走**冪等**路徑。

        這不是省事：寫了就代表下一個 tick 的回讀不符 ⇒ 每 15 分鐘 bootout+bootstrap 一輪，
        而 bootstrap 是整條鏈上唯一會讓哨兵消失的動作。憑證此時必須明說「只有巡邏觸發」
        ＋最壞死等秒數，不准留白（留白會讓它與「排到了確切時刻」看起來一樣）。
        """
        rc, cred = self._arm(self.now + timedelta(seconds=900), None)
        self.assertEqual(rc, 0, cred)
        self.assertNotIn("StartCalendarInterval", self._plist())
        self.assertIn("只有巡邏觸發", cred)
        self.assertIn(str(planner.SENTINEL_INTERVAL_SECONDS), cred)
        self.assertEqual([a for a in self.seen if "bootstrap" in a], [],
                         "巡邏走到了非冪等路徑 ⇒ 每一次 tick 都會動排程器")

    def test_the_transient_retry_stays_coarse_on_purpose(self) -> None:
        """`TRANSIENT_RETRY_SECONDS`（<interval）刻意不配 calendar——代價已登記在檔頭。

        用「暫時性錯誤重試慢最多一個巡邏間隔」換掉「每一次 502 都觸發一輪重載」是划算的，
        而這一條把那個取捨釘住：有人把門檻改成「有時刻就寫」時它會紅。
        """
        self.assertLess(planner.TRANSIENT_RETRY_SECONDS, planner.SENTINEL_INTERVAL_SECONDS)
        self.assertIsNone(sb._calendar_of(
            self.now + timedelta(seconds=planner.TRANSIENT_RETRY_SECONDS),
            planner.SENTINEL_INTERVAL_SECONDS))

    def test_the_minute_granularity_only_ever_rounds_later(self) -> None:
        """絕不提早：提早觸發＝在 reset 之前白燒一次探測（唯一花 token 的動作）。

        判準刻意不依賴 `RESET_SKEW_SECONDS`——那是**別人的常數**，把正確性寄託在它上面等於
        讓調小 skew 的人在完全無關的地方靜默破壞這裡。
        """
        for second in (1, 30, 59):
            at = (self.now + timedelta(hours=2)).replace(second=second, microsecond=0)
            cal = sb._calendar_of(at, planner.SENTINEL_INTERVAL_SECONDS)
            fired = at.replace(second=0, microsecond=0) + timedelta(
                minutes=1 if second else 0)
            with self.subTest(second=second):
                self.assertEqual((cal["Hour"], cal["Minute"]), (fired.hour, fired.minute))
                self.assertGreaterEqual(fired, at, "取整後的觸發時刻早於要求的時刻")

    def test_the_calendar_pins_month_and_day_not_just_the_time(self) -> None:
        """只給 Hour/Minute 的 `StartCalendarInterval` 是**每天**觸發的（nightly 的語意）。

        這裡要的是「某一個特定時刻」⇒ 多釘兩個鍵讓殘留退化成一年一次。
        """
        cal = sb._calendar_of(self.now + timedelta(hours=3),
                             planner.SENTINEL_INTERVAL_SECONDS)
        self.assertEqual(sorted(cal), sorted(sb._CAL_KEYS))

    def test_the_readback_parser_survives_the_real_nested_shape(self) -> None:
        """真機的 calendar 住在 depth 4，且同一份輸出裡有 `"port" => …` 這種誘餌。

        fixture 比真實世界簡單就是最貴的一種假綠（R83／QA 那次扁平 fixture 讓 30 條綠全數
        成立、而真機憑證在說假話）⇒ 這一條同時斷言誘餌真的在 fixture 裡。
        """
        want = {"Month": 8, "Day": 10, "Hour": 23, "Minute": 2}
        out = _print_output(900, ["/x"], "/p", calendar=want)
        self.assertIn('"port" => 563971', out, "fixture 少了 event channels 誘餌")
        self.assertIn("descriptor = {", out, "fixture 少了真機的巢狀 descriptor")
        sb._run = _fake_runner({"print": (0, out)}, self.seen)
        live = sb.LaunchdBackend()._readback(self.task)
        self.assertEqual(live["calendar"], want)
        self.assertNotIn("port", live["calendar"], "白名單失效 ⇒ 誤收 event channels 的欄位")


class DeferredActionWaitsForTheParentTest(unittest.TestCase):
    """🔴 R83-B ⑥ — **本輪 P0 的真根因**：延後動作等的是「父行程退場」，不是一個猜的秒數。

    真根因判讀、真機合成實驗與 production 撞線語料的逐字史料搬遷，原文＝Guard_Repin
    證據檔 §E-8。
    """

    def setUp(self) -> None:
        self._real_popen = subprocess.Popen
        self.addCleanup(setattr, subprocess, "Popen", self._real_popen)
        self.scripts: list[str] = []
        subprocess.Popen = (  # type: ignore[assignment]
            lambda argv, **kw: self.scripts.append(argv[-1]))

    def _script(self, method: str = "_defer") -> str:
        getattr(sb.LaunchdBackend(), method)("AutoSDD_Sentinel_x", 'echo "hi";')
        return self.scripts[0]

    def test_the_deferred_script_waits_on_the_parent_pid(self) -> None:
        script = self._script()
        self.assertIn(f"kill -0 {os.getpid()}", script.replace("$p", str(os.getpid())),
                      "沒有在等父行程 ⇒ 它會在父行程做完事之前就動手")
        self.assertIn(f"p={os.getpid()}", script)

    def test_red_a_fixed_sleep_before_the_action_is_the_bug_itself(self) -> None:
        """合成注入（紅）：腳本裡若只有 `sleep <常數>;` 就接動作，這一條必須紅。

        判準取「動作前的等待是否綁在父行程上」而不是「有沒有 sleep 這個字」——輪詢迴圈
        本身就需要 `sleep 1`。所以比的是：`sleep` 之後緊接的是不是 `launchctl`。
        """
        script = self._script()
        wait, _, action = script.partition("done;")
        self.assertTrue(action.strip(), "腳本裡沒有輪詢迴圈 ⇒ 等待不可能綁在父行程上")
        self.assertIn("while kill -0", wait)
        for bad in ("sleep 3; launchctl", "sleep 5; launchctl", "sleep 10; launchctl"):
            self.assertNotIn(bad, script, f"退回寫死的等待（{bad}）＝把 R83-B 的 P0 裝回去")

    def test_the_wait_cap_outlives_the_longest_thing_a_tick_can_do(self) -> None:
        """上界必須大於 `_run_resume` 的 `timeout` ——**現查 planner 原始碼，不抄常數**。

        抄一份就會有兩個家：把 `timeout` 調大而不動這個上界，最長的那一跑又會被砍，而
        表徵與修好之前一模一樣（痕跡少一行、沒有例外）。這一條讓那件事當場紅。
        """
        tree = ast.parse(Path(planner.__file__).read_text(encoding="utf-8"))
        found = [kw.value.value for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef,)) and node.name == "_run_resume"
                 for call in ast.walk(node) if isinstance(call, ast.Call)
                 for kw in call.keywords
                 if kw.arg == "timeout" and isinstance(kw.value, ast.Constant)]
        self.assertEqual(len(found), 1, "`_run_resume` 的 timeout 不是唯一一個字面常數")
        self.assertGreater(sb.DEFER_WAIT_CAP_SECONDS, found[0])

    def test_the_relaunch_records_all_three_return_codes(self) -> None:
        """自我重載的三個 rc（bootout／bootstrap／print）都要落在痕跡檔裡。

        bootstrap 是這條路上唯一會讓哨兵整支消失的一步，而它失敗時沒有人在看
        ⇒ 「沒觸發＝這個檔不會長大」是唯一能給的可偵測性（見 `arm()` 內那段誠實劃界）。
        """
        trace = sb.LaunchdBackend()._defer_relaunch("AutoSDD_Sentinel_x", "/tmp/x.plist")
        script = self.scripts[0]
        for piece in ('echo "bootout rc=$?"', "launchctl bootstrap",
                      'echo "bootstrap rc=$?', 'echo "print rc=$?"'):
            self.assertIn(piece, script)
        self.assertIn(str(trace), script, "三個 rc 沒有被導進痕跡檔")
        self.assertIn("i -le 3", script, "bootstrap 沒有重試 ⇒ 一次失敗就沒有哨兵了")

    def test_the_deferred_credential_refuses_to_claim_the_reload_happened(self) -> None:
        """延後重載那條路上，憑證**不准**宣稱 launchd 已經拿到新參數。

        它此刻手上的回讀還是舊的 ⇒ 能陳述的只有「plist 已落地」＋「重載待完成」＋痕跡檔。
        R83 已有判例（`verify_cli` 只驗存在卻印「相符」）：憑證存在、但憑證不回答那個問題。
        """
        trace = Path("/tmp/t.log")
        cred = sb.LaunchdBackend()._deferred_credential(
            "AutoSDD_Sentinel_x", {"Month": 8, "Day": 10, "Hour": 23, "Minute": 2}, trace)
        self.assertIn("不宣稱重載已完成", cred)
        self.assertIn(str(trace), cred)
        for lie in ("與請求相符", "launchctl print rc=0", "已持久化並已載入"):
            self.assertNotIn(lie, cred, f"延後路徑的憑證混進了一句它證明不了的話：{lie}")

    def test_arming_from_inside_the_job_defers_instead_of_abandoning(self) -> None:
        """在 job 內偵測到漂移時**不再** fail-loud（原處置會把每次撞線都標成 abandoned）。

        `arm_reset` 的決策就是在 tick 裡做的 ⇒ 「本 tick 跑在 job 內」是常態而非例外；
        沿用 rc=1 會讓狀態塊每次撞線都變成 abandoned，比修之前更糟。
        """
        tmp = Path(tempfile.mkdtemp(prefix="r83b_inside_"))
        plan = tmp / "plan.md"
        plan.write_text("# plan\n", encoding="utf-8", newline="\n")
        real_dir, real_run = sb.LAUNCH_AGENTS_DIR, sb._run
        sb.LAUNCH_AGENTS_DIR = tmp / "LaunchAgents"
        self.addCleanup(setattr, sb, "LAUNCH_AGENTS_DIR", real_dir)
        self.addCleanup(setattr, sb, "_run", real_run)
        seen: list[list[str]] = []
        task = "AutoSDD_Sentinel_inside"
        # 回讀刻意**沒有** calendar，而我們要求一個 ⇒ 漂移成立。
        sb._run = _fake_runner({"-lint": (0, ""), "bootout": (0, ""), "bootstrap": (0, ""),
                                "print": (0, _print_output(
                                    planner.SENTINEL_INTERVAL_SECONDS,
                                    sb.LaunchdBackend()._argv(planner, str(plan), task,
                                                              planner.SENTINEL_TICK),
                                    str(sb.LaunchdBackend().plist_path(task))))}, seen)
        real_xpc = os.environ.get("XPC_SERVICE_NAME")
        os.environ["XPC_SERVICE_NAME"] = task
        self.addCleanup(lambda: os.environ.__setitem__("XPC_SERVICE_NAME", real_xpc)
                        if real_xpc is not None else os.environ.pop("XPC_SERVICE_NAME", None))
        rc, cred = sb.LaunchdBackend().arm(
            str(plan), task, "", planner.SENTINEL_TICK,
            datetime.now().astimezone() + timedelta(minutes=56))
        self.assertEqual(rc, 0, "在 job 內偵測到漂移就放棄 ⇒ 每次撞線都會被標成 abandoned")
        self.assertIn("不宣稱重載已完成", cred)
        # **絕不**在自己身上同步 bootout（真機實測會當場被終止）。
        self.assertEqual([a for a in seen if "bootout" in a], [])
        self.assertTrue(self.scripts, "延後重載一次都沒排 ⇒ 新時刻永遠不會生效")
        self.assertIn("launchctl bootstrap", self.scripts[0])


class WindowsPathIsUnchangedTest(unittest.TestCase):
    """④ Windows 那一側行為零改變（以替身模擬，不需要真的有 powershell.exe）。"""

    def test_the_schtasks_arm_still_registers_and_gates_on_next_run_time(self) -> None:
        """`SchtasksBackend.arm` ＝搬家前的 `_register_at_expr`：註冊 → 取 NextRunTime → 沒有就 rc=1。"""
        seen: list[str] = []

        def _fake(script: str):
            seen.append(script)
            return subprocess.CompletedProcess(args=[], returncode=0, stderr="",
                                               stdout="NextRunTime : 2026/8/9 09:02:00\n")
        real = planner.run_powershell
        planner.run_powershell = _fake
        self.addCleanup(setattr, planner, "run_powershell", real)
        rc, moment = sb.select(os_name="nt").arm("plan-fixture.md", "T", "'2026-08-09 09:00:00'",
                                                 planner.RESUME_TICK)
        self.assertEqual((rc, moment), (0, "2026/8/9 09:02:00"))
        self.assertIn("Register-ScheduledTask", seen[0])
        self.assertIn("'2026-08-09 09:00:00'", seen[0])
        self.assertIn(planner.RESUME_TICK, seen[0])

    def test_register_endurance_still_converts_to_the_local_frame_first(self) -> None:
        """R80 的那條教訓在**上一層**（與載具無關）：`strftime` 丟 offset 前必須先 astimezone。

        seam 下移之後這條性質的落點仍在 `_register_at_expr`，兩個平台通用——既有回歸鎖
        `ResetFrameIsNotTheMachineClockTest` 打的就是同一個落點，本支是它的姊妹。
        """
        seen: list[tuple] = []
        real = planner._register_at_expr
        planner._register_at_expr = lambda *a: (seen.append(a), (0, "x"))[1]
        self.addCleanup(setattr, planner, "_register_at_expr", real)
        far = datetime(2026, 8, 9, 1, 2, 3, tzinfo=timezone(timedelta(hours=-7)))
        planner.register_endurance({"plan_path": "plan-fixture.md", "task_name": "T"}, far)
        self.assertEqual(seen[0][:2], ("plan-fixture.md", "T"))
        self.assertEqual(seen[0][2], f"'{far.astimezone().strftime('%Y-%m-%d %H:%M:%S')}'")
        self.assertEqual(seen[0][3], planner.RESUME_TICK)

    def test_the_new_structured_moment_changes_nothing_on_the_schtasks_side(self) -> None:
        """🔴 R83-B 驗收條件：Windows 那一側**行為零改變**。

        `at` 這個新參數在 schtasks 後端刻意不使用——`-Once -At <時刻>` 本來就吃時刻，語意
        已完整由 `at_expr` 表達 ⇒ 再讀一次結構化的 `at` 只會製造第二個真相源。
        判準取「兩次呼叫送出的 PowerShell 腳本逐字相同」：只要有人開始讀 `at`，這一條就紅。
        以替身模擬 `os.name == 'nt'`，不需要真的有 powershell.exe。
        """
        scripts: list[str] = []

        def _fake(script: str):
            scripts.append(script)
            return subprocess.CompletedProcess(args=[], returncode=0, stderr="",
                                               stdout="NextRunTime : 2026/8/9 09:02:00\n")
        real = planner.run_powershell
        planner.run_powershell = _fake
        self.addCleanup(setattr, planner, "run_powershell", real)
        backend = sb.select(os_name="nt")
        self.assertIsInstance(backend, sb.SchtasksBackend)
        base = ("plan-fixture.md", "T", "'2026-08-09 09:00:00'", planner.RESUME_TICK)
        rc_a, moment_a = backend.arm(*base)                     # 舊呼叫形態（不帶 at）
        rc_b, moment_b = backend.arm(*base, datetime(2027, 1, 1).astimezone())
        self.assertEqual((rc_a, moment_a), (rc_b, moment_b))
        self.assertEqual(scripts[0], scripts[1], "`at` 洩進了 schtasks 腳本")
        self.assertNotIn("2027", scripts[1])
        self.assertNotIn("StartCalendarInterval", scripts[1])

    def test_disarm_still_requires_the_removed_sentinel_not_the_rc(self) -> None:
        """`Get-ScheduledTask` 對不存在的工作回 rc=0 ⇒ Windows 那一側只能看輸出字樣。"""
        for stdout, want in (("REMOVED\n", 0), ("STILL-PRESENT\n", 1), ("", 1)):
            with self.subTest(stdout):
                fake = subprocess.CompletedProcess(args=[], returncode=0,
                                                   stdout=stdout, stderr="")
                real = planner.run_powershell
                planner.run_powershell = lambda script: fake
                self.addCleanup(setattr, planner, "run_powershell", real)
                self.assertEqual(sb.select(os_name="nt").disarm("T"), want)

    def test_verify_still_refuses_when_next_run_time_is_missing(self) -> None:
        for stdout, want in (("NextRunTime : 2026/8/9 09:02:00\n", 0),
                             ("NextRunTime :\n", 1), ("（什麼都沒有）\n", 1)):
            with self.subTest(stdout):
                fake = subprocess.CompletedProcess(args=[], returncode=0,
                                                   stdout=stdout, stderr="")
                real = planner.run_powershell
                planner.run_powershell = lambda script: fake
                self.addCleanup(setattr, planner, "run_powershell", real)
                self.assertEqual(sb.select(os_name="nt").verify_cli("T"), want)

    def test_the_windows_credential_line_is_still_the_next_run_time_sentence(self) -> None:
        self.assertIn("NextRunTime = X", sb.select(os_name="nt").credential_line("X"))


class EscapeHatchAndNoProliferationTest(unittest.TestCase):
    """接電那一半：逃生口在 mac 同樣有效，且**不得**另寫一套武裝門檻。"""

    def setUp(self) -> None:
        self._real = os.environ.get(guard.SENTINEL_OFF_ENV)
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        os.environ.pop(guard.SENTINEL_OFF_ENV, None)
        if self._real is not None:
            os.environ[guard.SENTINEL_OFF_ENV] = self._real

    def test_the_sentinel_escape_hatch_stops_every_arm_on_this_platform(self) -> None:
        os.environ[guard.SENTINEL_OFF_ENV] = "1"
        tmp = Path(tempfile.mkdtemp(prefix="r83_off_"))
        transcript = tmp / "s.jsonl"
        transcript.write_text("{}\n", encoding="utf-8", newline="\n")
        self.assertEqual(guard.arm_when_earned(transcript), "disabled")
        self.assertEqual(guard.arm_quota_wakeup(transcript, "plan-fixture.md"),
                         {"armed": False, "sentinel_off": True, "posix": False}
                         if sb.has_carrier() else
                         {"armed": False, "sentinel_off": False, "posix": True})

    def test_mac_reuses_the_very_same_earned_threshold(self) -> None:
        """R82 的 job 增生事故：短命 session 也武裝。mac 必須沿用**同一套**判準。

        走 `sentinel_lifecycle.maybe_arm`（＝武裝臂真正呼叫的那一支），不是自己捏一份
        門檻比較——捏假的會讓「mac 另寫了一套」在整套測試裡完全看不見。
        """
        tmp = Path(tempfile.mkdtemp(prefix="r83_earn_"))
        transcript = tmp / "s.jsonl"
        transcript.write_text("{}\n", encoding="utf-8", newline="\n")
        spawned: list[tuple] = []
        why = sentinel_lifecycle.maybe_arm(
            transcript, "sid", plan_path="plan-fixture.md",
            spawn=lambda *a: (spawned.append(a), True)[1], tmp_dir=str(tmp))
        self.assertTrue(why.startswith("below-threshold"), why)
        self.assertEqual(spawned, [], "空逐字稿竟然拿到了一支排程")
        # 綠的那一半：跨過門檻就會武裝（否則上面那條紅可能只是因為整條路死掉）。
        self.assertEqual(sentinel_lifecycle.maybe_arm(
            transcript, "sid", plan_path="plan-fixture.md",
            spawn=lambda *a: (spawned.append(a), True)[1], tmp_dir=str(tmp),
            min_turns=0, min_span=0.0), "armed")
        self.assertEqual(len(spawned), 1)

    def test_session_start_stays_silent_and_exit_zero_on_this_machine(self) -> None:
        """SessionStart 不得出聲、不得阻塞——它只清閂鎖（武裝延後到 PostToolUse）。"""
        payload = json.dumps({"hook_event_name": "SessionStart",
                              "transcript_path": str(Path(tempfile.gettempdir())
                                                     / "r83-no-such-session.jsonl")})
        proc = subprocess.run([sys.executable, str(_GUARD_SRC)], input=payload,
                              capture_output=True, encoding="utf-8", errors="replace",
                              timeout=60, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((proc.stdout.strip(), proc.stderr.strip()), ("", ""))


class HookWiringReachesThisPlatformTest(unittest.TestCase):
    """R77 的教訓逐字是「機制蓋好沒接電」——這一支就是那條電線的鎖。

    `.claude/settings.json` 的每個 hook 都是「Windows 載具 ＋ POSIX 載具」一組（R80/R81
    的 exec form 轉換）。續航鏈掛在 `context_budget_guard.py` 的 SessionStart 與
    PostToolUse 兩個事件上，**POSIX 那一條不在的話 mac 上整條鏈一次都不會被叫到**，
    而表徵與「這台機器沒有排程載具」完全相同。
    """

    def test_the_guard_has_a_posix_carrier_on_both_endurance_events(self) -> None:
        settings = json.loads((_REPO_ROOT / ".claude" / "settings.json")
                              .read_text(encoding="utf-8"))
        for event in ("SessionStart", "PostToolUse"):
            carriers = [entry.get("command", "")
                        for block in settings["hooks"].get(event, [])
                        for entry in block.get("hooks", [])
                        if any("context_budget_guard.py" in str(a)
                               for a in entry.get("args", []))]
            self.assertTrue(carriers, f"{event} 完全沒有掛 context_budget_guard")
            posix = [c for c in carriers if "Scripts" not in c and "pythonw" not in c]
            self.assertTrue(posix, f"{event} 只有 Windows 載具 ⇒ mac 上整條續航鏈不會被叫到")


# ═══════════════════════════════════════════════════════════════════════════
# 🔴 R84／SA-05：訴求 6e 的**誠實化**——「睡著的 Mac 不會醒」不得只活在一行註解裡
# ═══════════════════════════════════════════════════════════════════════════
# 複審當回合實測的立案史料搬遷，原文＝Guard_Repin 證據檔 §E-9。
# 🔴 本組鎖**不驗「Mac 會醒」**（那件事本專案不做：需 sudo 改動掌舵者機器的電源行為，已被
# 否決）。它驗的是「失效變成可偵測的」：非 0 就出聲、量不到也出聲、而且不對非 mac 發言。
_SLEEPY = "AC Power:\n displaysleep 10\n sleep 25\n disksleep 0\n"
_AWAKE = "AC Power:\n displaysleep 10\n sleep 0\n standby 1\n"


def _pm(rc: int, out: str, seen: list | None = None):
    """`schedule_backend._run` 的替身，只回答 `pmset`（其餘一律 rc=0／空輸出）。"""
    def _run(argv: list[str], timeout: int = 60) -> tuple[int, str]:
        if seen is not None:
            seen.append(list(argv))
        return (rc, out) if argv and argv[0] == "pmset" else (0, "")
    return _run


class MacSleepPostureIsSaidOutLoudTest(unittest.TestCase):
    """電源姿態的判準與它的**鑑別力**（每一條都附合成注入，不依賴這台機器的設定）。"""

    def test_a_sleepy_machine_is_reported(self) -> None:
        trouble = endurance_env.sleep_trouble(_pm(0, _SLEEPY), "darwin")
        self.assertIn("sleep 25", trouble)
        self.assertIn("launchd", trouble, "沒說出「為什麼這件事會弄壞續航」")

    def test_green_a_machine_that_never_sleeps_says_nothing(self) -> None:
        """對照組：`sleep 0` 必須完全安靜——會誤報的警告會被下一個人整個關掉。"""
        self.assertEqual(endurance_env.sleep_trouble(_pm(0, _AWAKE), "darwin"), "")

    def test_displaysleep_is_not_mistaken_for_system_sleep(self) -> None:
        """鑑別力：`displaysleep 10` 與 `sleep 0` 同時存在是**本機實測的常態**。

        螢幕關掉不等於系統睡著（launchd job 照跑）⇒ 子字串比對會把「不會睡的機器」判成
        會睡，而那是一筆必然發生的假紅。`_AWAKE` 這份 fixture 逐字取自本機 `pmset -g custom`。
        """
        self.assertNotIn("displaysleep",
                         endurance_env.posture_note(_pm(0, _AWAKE), "darwin"))

    def test_unmeasurable_is_not_the_same_as_will_not_sleep(self) -> None:
        """`量不到 ≠ 不會睡`（本 repo 通篇那條紀律，見 `reap_verdict` ②）。"""
        trouble = endurance_env.sleep_trouble(_pm(127, "pmset: not found"), "darwin")
        self.assertIn("量不到", trouble)
        self.assertIn("127", trouble, "沒把 rc 寫進訊息 ⇒ 事後分不出是哪一種失效")

    def test_the_probe_never_even_spawns_off_darwin(self) -> None:
        """鐵律三（「這在另一個平台是什麼值」）：`pmset` 在 Windows／Linux **不存在**。

        判準刻意是「連 spawn 都不做」而不是「跑了失敗再說」：後者會在每一次武裝多一個
        必然失敗的子行程，而它的訊息（「這台機器量不到電源姿態」）對非 mac 機器毫無意義。
        """
        for platform_name in ("win32", "linux"):
            with self.subTest(platform_name):
                seen: list = []
                self.assertEqual(
                    endurance_env.sleep_trouble(_pm(0, _SLEEPY, seen), platform_name), "")
                self.assertEqual(seen, [], "非 darwin 竟然去 spawn pmset")

    def test_the_credential_slot_is_never_blank(self) -> None:
        """留白會讓「現查過、不會睡」與「根本沒查」外觀相同（同 calendar 那一欄的處置）。"""
        for platform_name in ("darwin", "linux"):
            with self.subTest(platform_name):
                self.assertTrue(
                    endurance_env.posture_note(_pm(0, _AWAKE), platform_name).strip())

    def test_the_arming_path_really_asks(self) -> None:
        """🔴 接線鎖（「機制蓋好沒接電」是本 repo 反覆記載的形態）。

        判準不是「程式碼裡有那個函式」，而是**武裝真的跑過一次之後 stderr 有那句話**：
        SA-05 的病正是「函式不存在」的下一階——路徑在、但沒有人在那條路上出聲。
        """
        tmp = Path(tempfile.mkdtemp(prefix="r84_pm_"))
        plan = tmp / "plan.md"
        plan.write_text("# plan\n", encoding="utf-8", newline="\n")
        self.addCleanup(setattr, sb, "LAUNCH_AGENTS_DIR", sb.LAUNCH_AGENTS_DIR)
        self.addCleanup(setattr, sb, "_run", sb._run)
        sb.LAUNCH_AGENTS_DIR = tmp / "LaunchAgents"
        sb._run = _pm(0, _SLEEPY)          # print/bootstrap 皆回 (0, "") ⇒ 武裝必然失敗
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            sb.LaunchdBackend().arm(str(plan), "AutoSDD_Sentinel_pm", "", "--sentinel-tick")
        self.assertIn("sleep 25", err.getvalue(),
                      "武裝路徑對「這台機器會睡著」仍然是靜默的（SA-05 的原病）")

    def test_the_wording_has_exactly_one_home(self) -> None:
        """同一句話兩個家是本 repo 反覆判過的形態：措辭只准住 `SLEEP_CAVEAT`。

        🔴 取樣範圍刻意**結構收窄到字串常數**（`ast.Constant`），不拿整份檔當 haystack：
        那兩支檔的**註解**本來就在解釋這件事（本輪新增的 WHY 段就是），而註解不是被測對象
        ——先例＝`TestNoAssertionSamplesALiveDocumentWholesale` 記載的「取樣範圍畫錯」那一族，
        本輪實測就先紅過一次（該鎖點名本測試逐字）。
        """
        needle = endurance_env.SLEEP_CAVEAT[:12]
        for src in (_BACKEND_SRC, _SENTINEL_SRC):
            literals = [node.value for node in ast.walk(ast.parse(src.read_text(
                encoding="utf-8"))) if isinstance(node, ast.Constant)
                and isinstance(node.value, str)]
            self.assertEqual([s for s in literals if needle in s], [],
                             f"{src.name} 自己抄了一份 SLEEP_CAVEAT 的措辭")


# ═══════════════════════════════════════════════════════════════════════════
# 🔴 R84／ZT-03＋ZT-07：續航鏈走過哪幾個分支，必須留下**不會蒸發**的憑證
# ═══════════════════════════════════════════════════════════════════════════
# 複審當回合逐字實測的立案史料搬遷，原文＝Guard_Repin 證據檔 §E-10。
# 🔴 判準刻意**不**斷言「這台機器上那個檔存在」：那是機器狀態，會讓 CI 與任何全新 clone
# 必紅（同 `test_check_hooks_liveness.py` 對載具存在性的既有分工）。它斷言的是**居所的性質**
# ＋ 兩個寫檔點真的用了它。
class DurableTraceHomeTest(unittest.TestCase):
    """痕跡的居所：比 `$TMPDIR` 持久、比 repo 不具權威。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="r84_trace_"))
        self.addCleanup(os.environ.pop, endurance_env.TRACE_DIR_ENV, None)

    def test_the_override_is_honoured_and_created(self) -> None:
        """逃生口：單元測試不得在開發者家目錄留下移動零件。"""
        want = self.tmp / "sandbox" / "traces"
        os.environ[endurance_env.TRACE_DIR_ENV] = str(want)
        self.assertEqual(endurance_env.trace_dir(), want)
        self.assertTrue(want.is_dir(), "逃生口指定的目錄沒有被建出來")

    def test_the_default_home_is_not_the_volatile_tmpdir(self) -> None:
        """本組鎖的**全部價值**：預設居所不得落在會被 OS 清掉的那一棵樹底下。"""
        os.environ.pop(endurance_env.TRACE_DIR_ENV, None)
        default = Path.home().joinpath(*endurance_env.TRACE_HOME_PARTS)
        self.assertNotEqual(default.resolve(strict=False),
                            Path(tempfile.gettempdir()).resolve(strict=False))
        self.assertIn(Path.home(), default.parents, "預設居所不在家目錄底下")

    def test_the_default_home_is_never_inside_the_repo(self) -> None:
        """ZT-03 明文的邊界：痕跡是機器狀態，寫進版控就變成第二個假常數（R73 判例）。"""
        default = Path.home().joinpath(*endurance_env.TRACE_HOME_PARTS)
        self.assertNotIn(_REPO_ROOT.resolve(), [default.resolve(strict=False),
                                                *default.resolve(strict=False).parents])

    def test_an_unwritable_home_degrades_instead_of_raising(self) -> None:
        """痕跡留不下來**絕不可**升級成續航本身的故障源（同 `append_log` 的既有紀律）。"""
        blocked = self.tmp / "ro"
        blocked.mkdir()
        blocked.chmod(0o500)
        self.addCleanup(blocked.chmod, 0o700)
        os.environ[endurance_env.TRACE_DIR_ENV] = str(blocked / "traces")
        self.assertEqual(endurance_env.trace_dir(),
                         Path(tempfile.gettempdir()), "唯讀家目錄沒有退回 $TMPDIR")

    def test_both_writers_really_use_the_durable_home(self) -> None:
        """接線鎖：兩個寫檔點（job 自己的 stdout、延後動作的 rc 痕跡）都必須落在那裡。

        `job stdout` 收的正是「這條鏈走過哪幾個分支」（`哨兵判定 <action>：…`），
        而 `bootout log` 收的是 ZT-03 那個 `parent-gone waited=Ns`。
        """
        want = self.tmp / "durable"
        os.environ[endurance_env.TRACE_DIR_ENV] = str(want)
        self.addCleanup(setattr, sb, "LAUNCH_AGENTS_DIR", sb.LAUNCH_AGENTS_DIR)
        sb.LAUNCH_AGENTS_DIR = self.tmp / "LaunchAgents"
        backend = sb.LaunchdBackend()
        trace = backend._defer("AutoSDD_Sentinel_probe", 'echo "noop";')
        self.assertEqual(trace.parent, want, "延後動作的痕跡仍落在 $TMPDIR")
        # argv 取 `sys.executable` 而不是一個 POSIX 絕對路徑字面值：後者會被
        # `test_platform_neutral_paths` 判紅（Windows 上 Path 渲染成反斜線 ⇒ Mac 全綠、
        # windows-compat-ci 假紅），本輪實測就是這樣紅了一次。
        self.assertTrue(backend._write_plist("AutoSDD_Sentinel_probe", [sys.executable], 900))
        body = plistlib.loads(backend.plist_path("AutoSDD_Sentinel_probe").read_bytes())
        self.assertEqual(Path(body["StandardOutPath"]).parent, want,
                         "job 自己的 stdout（＝分支歷程）仍落在 $TMPDIR")


# ═══════════════════════════════════════════════════════════════════════════
# 🔴 R84／ARCH-06：「什麼時候可以刪任務書」只准有一個判準、一個 unlink 站點
# ═══════════════════════════════════════════════════════════════════════════
# 病：`sentinel_lifecycle._sweep_artifacts` 的既有註解**自陳**「兩個家…改了一邊不會有任何
# 東西轉紅」——而自陳不是機械物。任務書是〈可重啟點四條件〉第 2 條的載體，兩套刪除時機
# 任一邊改動窗口，就可能刪掉另一邊還在等的那一份，且失效是靜默的。
#: 任務書身分的判準（`unlink` 站點的辨識條件之一）。兩種寫法都算：常數引用與字面。
_PLAN_IDENTITY = ("PLAN_PREFIX", "autosdd_resume_plan")
_PLAN_REAPERS = frozenset({"unlink", "remove", "rmtree"})
#: 唯一宣告過的家（`檔:函式`）。多一個就是多一套刪除時機。
_PLAN_UNLINK_HOME = {"tools/lib/quota_escalation.py:reap_plans"}


def plan_unlink_sites(sources: dict[str, str]) -> list[str]:
    """「同一個函式裡既認得任務書、又會刪檔」的站點清單。純函式，紅綠由注入自證。

    判準取**函式**為單位而不是檔案：同一支檔裡本來就會有別的 `unlink`
    （`sentinel_lifecycle` 要刪閂鎖、`schedule_backend` 要刪 plist），以檔為單位會製造假紅。
    解析失敗一律計為違規（掃不到的檔靜默放行正是本 repo 通篇在防的 fail-open）。
    """
    hits: list[str] = []
    for rel, src in sorted(sources.items()):
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            hits.append(f"{rel}:? AST 解析失敗（{exc}）——掃不到的檔不得靜默放行")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            body = ast.dump(node)
            names = {_call_name(c) for c in ast.walk(node) if isinstance(c, ast.Call)}
            if names & _PLAN_REAPERS and any(tag in body for tag in _PLAN_IDENTITY):
                hits.append(f"{rel}:{node.name}")
    return hits


class PlanReapHasOneHomeTest(unittest.TestCase):
    """判準一個家、`unlink` 一個家，且兩個呼叫端只提供輸入。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="r84_reap_"))

    def _plan(self, name: str, age_days: float) -> Path:
        path = self.tmp / f"{guard.PLAN_PREFIX}{name}.md"
        path.write_text("# 任務書\n", encoding="utf-8", newline="\n")
        stamp = time.time() - age_days * 86400
        os.utime(path, (stamp, stamp))
        return path

    def test_the_named_session_is_reaped_and_others_are_not(self) -> None:
        mine, theirs = self._plan("mine", 0.0), self._plan("theirs", 0.0)
        self.assertTrue(escalation.plan_reap_verdict(mine, "mine"))
        self.assertEqual(escalation.plan_reap_verdict(theirs, "mine"), "",
                         "🔴 收了別人那一份 ⇒ 另一個 session 的續航被靜默拆掉")

    def test_age_none_means_the_age_rule_has_no_input(self) -> None:
        """`age=None` **不是**第二套政策：GC 拿的是「這支哨兵已終態」這個裁決，與齡無關。"""
        ancient = self._plan("ancient", 99.0)
        self.assertTrue(escalation.plan_reap_verdict(ancient))
        self.assertEqual(escalation.plan_reap_verdict(ancient, age=None), "")

    def test_a_waiting_plan_survives_a_whole_quota_window(self) -> None:
        """門檻的**方向**（原 `PlanGarbageCollectionTest` 那條紀律，判準搬家後仍成立）。"""
        self.assertGreater(escalation.PLAN_GC_AGE_SECONDS, 5 * 3600)
        self.assertEqual(escalation.plan_reap_verdict(self._plan("waiting", 0.2)), "")

    def test_a_file_that_cannot_be_stat_ed_is_never_reaped(self) -> None:
        """量不到 ≠ 該刪（`reap_verdict` ② 同一條紀律）。"""
        self.assertEqual(escalation.plan_reap_verdict(self.tmp / "ghost.md"), "")

    def test_the_gc_arm_delegates_instead_of_deleting_by_itself(self) -> None:
        """接線鎖：`_sweep_artifacts` 必須真的把任務書那一件交出去。

        判準看**行為**（那一份真的不見了、而別人的超齡檔沒被牽連），不是看 import：
        「程式碼裡有那個呼叫」與「那條路真的走過」是本 repo 分開過的兩件事。
        """
        mine = self._plan("sid", 0.0)
        ancient = self._plan("someone-else", 99.0)
        (self.tmp / f"{sentinel_lifecycle.ARM_MARKER_PREFIX}sid.json").write_text(
            "{}", encoding="utf-8", newline="\n")
        swept = sentinel_lifecycle._sweep_artifacts("sid", self.tmp)
        self.assertIn(mine.name, swept)
        self.assertFalse(mine.is_file())
        self.assertTrue(ancient.is_file(),
                        "GC 順手把別人的超齡檔一起收了 ⇒ 那是把年齡政策偷渡進 GC")

    def test_the_scan_surface_is_shared_and_has_not_shrunk(self) -> None:
        """分母與載具那道鎖**共用同一份現查**（兩個家會各自漂移）。"""
        surface = _carrier_scan_surface()
        self.assertGreaterEqual(len(surface), _CARRIER_SURFACE_FLOOR)
        for home in _PLAN_UNLINK_HOME:
            self.assertIn(home.split(":")[0], surface, "宣告過的家不在掃描面內")

    def test_no_second_home_deletes_a_plan(self) -> None:
        sites = set(plan_unlink_sites(_carrier_scan_surface())) - _PLAN_UNLINK_HOME
        self.assertEqual(sites, set(),
                         "任務書的刪除時機又長出第二個家（改一邊不會有東西轉紅）："
                         f"{sorted(sites)}")

    def test_red_a_second_home_is_caught(self) -> None:
        """合成注入（紅）＝修前 `_sweep_artifacts` 的原形逐字。"""
        injected = ('def _sweep_artifacts(session_id, tmp):\n'
                    '    for name in (f"autosdd_resume_plan_{session_id}.md",):\n'
                    '        (tmp / name).unlink()\n')
        self.assertEqual(plan_unlink_sites({"tools/lib/x.py": injected}),
                         ["tools/lib/x.py:_sweep_artifacts"])

    def test_green_reading_a_plan_without_deleting_is_not_a_site(self) -> None:
        """對照組：讀任務書（`plan_state`／寫回狀態塊）的地方一律放行，否則滿場假紅。"""
        innocent = ('def plan_state(sid, tmp):\n'
                    '    return (tmp / f"autosdd_resume_plan_{sid}.md").read_text()\n')
        self.assertEqual(plan_unlink_sites({"tools/lib/y.py": innocent}), [])

    def test_green_deleting_something_that_is_not_a_plan_is_not_a_site(self) -> None:
        """另一向對照組：刪 plist／閂鎖的既有站點不得被牽連。"""
        innocent = ('def disarm(self, task):\n'
                    '    self.plist_path(task).unlink()\n')
        self.assertEqual(plan_unlink_sites({"tools/lib/z.py": innocent}), [])


if __name__ == "__main__":
    unittest.main()
