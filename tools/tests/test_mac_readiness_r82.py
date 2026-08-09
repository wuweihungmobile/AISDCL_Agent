#!/usr/bin/env python3
"""R82 包 A3 — mac 真機就緒度的機械物（MAC-01/03/04 的判準面）。

🔴 本檔散文多處指名 **R83**（下一輪），逐行帶具名豁免 `round-label-ok`：那是**交棒**，
不是自稱本批屬於下一輪。把它們改寫成 R82 會把「還沒在 mac 上驗」講成「本輪驗過了」——
而本檔存在的唯一理由就是防那種假宣稱。

WHY（三個 finding 是同一種病，不是三件雜事）：R83 下一輪就切 macOS 真機，而 repo 對 mac  round-label-ok
的三筆宣稱在本輪之前都沒有人在守，且失效方式一模一樣——**話說得像結論、實際是假的，
而假的那一面永遠不會轉紅**：

  · MAC-01：`macos_smoke_local.sh` 說「BSD mktemp 必須帶模板」、`ci-gate.sh` 說「實測現代
    macOS 皆可」。兩句互斥、真值只有一個，兩句都沒有取證位置。判準面在
    `test_bash32_compat.py`（裸 mktemp 進 `_PATTERNS`）；本檔只守「互斥宣稱不得留兩份」。
  · MAC-03：POSIX hook 載具的版本告警在 mac 上 day 1 必響，而它宣稱的後果（「一 import
    就炸」）對現行 hook 集是假的；同時 macos CI 一開頭就 setup-python 3.11，把真實預設態
    整個遮掉 ⇒ 那句假話結構上沒有機會被戳破。
  · MAC-04：launchd 能力表把 `WakeToRun` 判成「結構上沒有對應物」，而真正的對等物是
    `pmset repeat wakeorpoweron`（可安裝、可現查），安裝器卻全檔零 `pmset`。
    「這個 plist 鍵不存在」被寫成了「這件事沒辦法查」。

🔴 誠實劃界（本檔**沒有**買到什麼）：作者在 Windows 上完成本輪，`launchd`／`pmset`／
BSD `date`／BSD `mktemp` 的執行期行為**一次都沒有真跑過**。本檔守的全是「repo 內的話與
repo 內的程式碼是否自洽」，不是「那句話在 mac 上是不是真的」。R83 的落實指令列在  round-label-ok
`R83_VERIFICATION_COMMANDS`，由 `TestR83HandoffIsExecutable` 釘住它不得變成空話。  round-label-ok
"""
from __future__ import annotations

import ast
import json
import re
import sys
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]

sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
sys.path.insert(0, str(_TESTS_DIR))

import hook_wiring  # noqa: E402
import test_bash32_compat as _bash32  # noqa: E402

_SETTINGS = _REPO_ROOT / ".claude" / "settings.json"
_LAUNCHER_REL = ".claude/hooks/_hook_launcher.py"
_MAC_INSTALLER = _REPO_ROOT / "tools" / "install_mac_nightly.sh"
_MACOS_CI = _REPO_ROOT / ".github" / "workflows" / "macos-compat-ci.yml"
_CI_GATE = _REPO_ROOT / "AISDLC_SDD" / "scripts" / "ci-gate.sh"
_MAC_SMOKE = _REPO_ROOT / "tools" / "macos_smoke_local.sh"


# ═════════════════════════════════════════════════════════════════════════════
# MAC-01（散文面）：互斥宣稱不得留兩份
# ═════════════════════════════════════════════════════════════════════════════

#: 被撤回的那句話（`AISDLC_SDD/scripts/ci-gate.sh` 原文）。留著它就等於留著一份與
#: `tools/macos_smoke_local.sh` 檔頭互斥的宣稱，而讀者無從得知該信哪一份。
_RETRACTED_MKTEMP_CLAIM = "實測現代 macOS 皆可"

#: 撤回後仍殘留該句的**活躍** bash 檔（shrink-only 存量債）。落地當回合實測＝
#: LATEST 版框架的 `tools/init_project.sh` 一支（本包在檔案所有權上不得動那棵樹，
#: 見交件回報的 `needs_from_others`）。少一筆＝債已還請把它從表上刪掉；多一筆／
#: 多一個檔＝有人又把互斥宣稱貼回來了。
_RETRACTED_CLAIM_DEBT: dict[str, int] = {
    "tools/init_project.sh": 1,
}


def retracted_claim_census(trees: list[tuple[str, list[str], int]]) -> dict[str, int]:
    """六棵 bash 樹裡，還有哪幾支檔帶著那句被撤回的宣稱（key 取檔名尾段）。

    刻意用**檔名尾段**當 key 而不是完整相對路徑：LATEST 版目錄名每次框架升版都會變
    （`AISDLC_SDD_v0.30` → `v0.31`），拿完整路徑當 key 的表會在升版當天無故轉紅，
    而那種鎖第一次紅就會被改寬。
    """
    census: dict[str, int] = {}
    for _key, files, _floor in trees:
        for rel in files:
            text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
            hits = text.count(_RETRACTED_MKTEMP_CLAIM)
            if hits:
                census["/".join(rel.split("/")[-2:])] = hits
    return census


#: 合法引用的具名出口（行尾）。**為什麼非有不可**：這兩支檔的訂正註記與史料本來就會
#: 逐字寫出被撤回的那句話（「本檔曾寫過『…』，已撤回，理由是…」），而那正是它們該做的事。
#: 拿整份文件當 haystack 去斷言該字樣不出現，等於要求文件永遠不准談論自己撤掉的東西
#: ——Pkg-P12 已經付過這筆錢：載具的假紅逼得帳本改寫了自己的缺陷描述
#: （`test_archive_defect_log.py::TestNoAssertionSamplesALiveDocumentWholesale` 的立案史）。
_RETRACTED_CLAIM_CITE_OK = "retracted-claim-ok"


def retracted_claim_offending_lines(text: str) -> list[tuple[int, str]]:
    """帶著被撤回宣稱、且**沒有**具名引用出口的行（純函式，`[]`＝乾淨）。

    逐行判定而非整檔比對：兩者的差別不在嚴格度，在**假紅的方向**——整檔比對會把
    「訂正註記逐字引述」判成違規，而那種紅只有一種收法：改寫史料去討好載具。
    """
    return [
        (n, line.strip()[:100])
        for n, line in enumerate(text.split("\n"), 1)
        if _RETRACTED_MKTEMP_CLAIM in line and _RETRACTED_CLAIM_CITE_OK not in line
    ]


class TestMutuallyExclusiveMktempClaimIsRetracted(unittest.TestCase):
    """MAC-01(c)：同一件事不得同時存在兩份互斥宣稱。"""

    def test_the_two_owned_files_no_longer_carry_the_retracted_claim(self) -> None:
        for path in (_CI_GATE, _MAC_SMOKE):
            offenders = retracted_claim_offending_lines(
                path.read_text(encoding="utf-8"))
            self.assertEqual(
                offenders, [],
                f"{path.name} 又出現被撤回的宣稱「{_RETRACTED_MKTEMP_CLAIM}」——"
                "它與 tools/macos_smoke_local.sh 檔頭的「BSD mktemp 必須帶模板」互斥，"
                "而兩句都沒有可重跑的取證位置。收斂寫法＝「一律帶模板」（兩種假設下皆正確）。"
                f"確屬訂正註記／史料的逐字引述時，於該行行尾加 `{_RETRACTED_CLAIM_CITE_OK}`："
                f"\n  - " + "\n  - ".join(f"{n}: {s}" for n, s in offenders),
            )

    def test_the_line_criterion_is_red_and_green_on_synthetic_input(self) -> None:
        """紅綠自證：沒有這一條，「掃描面乾淨」與「判準壞掉」在綠燈上長得一樣。"""
        bad = f"# BSD mktemp {_RETRACTED_MKTEMP_CLAIM}，故不帶模板\n"
        self.assertEqual(len(retracted_claim_offending_lines(bad)), 1)
        cited = (f"# 本檔曾寫「{_RETRACTED_MKTEMP_CLAIM}」，R82 撤回  "
                 f"{_RETRACTED_CLAIM_CITE_OK}\n")
        self.assertEqual(retracted_claim_offending_lines(cited), [])
        self.assertEqual(retracted_claim_offending_lines("# 一律帶模板\n"), [])

    def test_the_surviving_copies_only_shrink(self) -> None:
        self.assertEqual(
            retracted_claim_census(_bash32._scan_trees()), dict(_RETRACTED_CLAIM_DEBT),
            "被撤回宣稱的殘留份數與債表不符。多一筆＝互斥宣稱又被貼回來（**不得調高**）；"
            "少一筆＝債已還，請把該列從 `_RETRACTED_CLAIM_DEBT` 刪掉",
        )

    def test_the_prose_ban_list_now_covers_mktemp(self) -> None:
        """散文側與判準側的綁定（`test_bash32_compat` 那道雙向鎖只認登記表內的 token）。"""
        self.assertIn("mktemp", _bash32._BAN_TOKEN_SAMPLES)
        sample = _bash32._BAN_TOKEN_SAMPLES["mktemp"]
        self.assertTrue(
            any(pat.search(sample) for pat, _d in _bash32._PATTERNS),
            f"散文列了裸 mktemp，但 `_PATTERNS` 打不中樣本 {sample!r}＝空頭宣告",
        )


# ═════════════════════════════════════════════════════════════════════════════
# MAC-03：POSIX 載具版本告警說的是不是真話 ＋ hook 鏈的 3.9 可載入性
# ═════════════════════════════════════════════════════════════════════════════

#: 被撤回的因果（原訊息逐字）。實測為假：現行 hook 集在 3.9 下載入得起來。
_FALSE_CAUSAL_CLAIM = "一 import 就炸"

#: 3.11+ 才有的 stdlib 名字（只列「寫程式時真的會順手用上、且一用就在 3.9 炸」的）。
#: 這不是完整表也不需要是——它是近似，鑑別力來自「不在表上的東西不會被誤判」。
_PY311_MODULES = {"tomllib"}
_PY311_FROM_NAMES = {"UTC", "Self", "LiteralString", "Never", "assert_type", "TypeVarTuple"}
_PY311_BUILTINS = {"ExceptionGroup", "BaseExceptionGroup"}

# 🔴 R82／C5：**這一族此前整片失明**（複審鏡實測：對 `quota_policy.py` 回空集合，而該檔
# 有 6 個 3.10+ 構造）。失明的形狀最貴——掃描器照跑、照回報 0 命中，只是那一族從來不在
# 分母裡；而它的下游後果是：mac 原廠 python3（常年 3.9）上 `quota_gate.py` 的 hard import
# 炸掉 → hook 端 try/except 把 `quota_gate` 收成 None → **整條額度軸零訊息消失**。
# 底下五種各自都是「一寫就在 3.9 炸」而且是寫程式時真的會順手用上的：
_PY310_KEYWORDS = {"dataclass": ("slots", "kw_only"), "zip": ("strict",)}
#: `from itertools import pairwise` / `from typing import TypeAlias` 這一族（3.10+）。
_PY310_FROM_NAMES = {"pairwise", "TypeAlias", "TypeGuard", "ParamSpecArgs", "EllipsisType"}


def _annotation_node_ids(tree: ast.AST) -> set[int]:
    """所有「住在型別註記裡」的節點 id。

    `from __future__ import annotations` 之下註記是字串、不在執行期求值 ⇒ 註記裡的
    `A | B` 在 3.9 完全合法；註記**之外**的同一個寫法（`isinstance(x, int | str)`、
    模組層 `X: TypeAlias = int | None` 的右值）才會炸。分不開這兩者的判準會製造整片假紅。
    """
    ids: set[int] = set()
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            targets = [node.returns] + [a.annotation for a in (
                node.args.posonlyargs + node.args.args + node.args.kwonlyargs
                + ([node.args.vararg] if node.args.vararg else [])
                + ([node.args.kwarg] if node.args.kwarg else []))]
        elif isinstance(node, ast.AnnAssign):
            targets = [node.annotation]
        for target in targets:
            if target is not None:
                ids.update(id(child) for child in ast.walk(target))
    return ids


def py39_incompat(source: str) -> list[str]:
    """`source` 裡出現的 3.10+/3.11+ 構造（空清單＝這一支在 3.9 下載得起來）。"""
    found: list[str] = []
    tree = ast.parse(source)
    lazy = any(isinstance(n, ast.ImportFrom) and n.module == "__future__"
               and any(a.name == "annotations" for a in n.names) for n in ast.walk(tree))
    in_annotation = _annotation_node_ids(tree) if lazy else set()
    for node in ast.walk(tree):
        if node.__class__.__name__ == "Match":            # 3.10 結構化模式比對
            found.append(f"match statement@L{node.lineno}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _PY311_MODULES:
                    found.append(f"import {alias.name}@L{node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in _PY311_MODULES:
                found.append(f"from {node.module}@L{node.lineno}")
            for alias in node.names:
                if alias.name in _PY311_FROM_NAMES | _PY310_FROM_NAMES:
                    found.append(f"from {node.module} import {alias.name}@L{node.lineno}")
        elif isinstance(node, ast.Name) and node.id in _PY311_BUILTINS:
            found.append(f"{node.id}@L{node.lineno}")
        elif isinstance(node, ast.Attribute) and node.attr in _PY310_FROM_NAMES:
            found.append(f"{node.attr}@L{node.lineno}")
        elif isinstance(node, ast.Call):
            callee = getattr(node.func, "attr", getattr(node.func, "id", ""))
            for kw in node.keywords:
                if kw.arg in _PY310_KEYWORDS.get(callee, ()):
                    found.append(f"{callee}({kw.arg}=)@L{node.lineno}")
        elif (isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr)
              and id(node) not in in_annotation
              and any(isinstance(x, ast.Constant) and x.value is None
                      for x in (node.left, node.right))):
            # `X | None`：`None` 不支援 `|`，所以這**必定**是型別聯集，不是位元運算
            # ⇒ 零假陽性；判準刻意只認這個形狀（判所有 `|` 會把真的位元運算一起判紅）。
            found.append(f"runtime `X | None`@L{node.lineno}")
    return sorted(found)


def _local_imports(source: str) -> list[tuple[str, bool]]:
    """模組層 import 的 (模組名, 是否包在 try 內)。

    `try` 內＝該相依失效時本檔自己會退化（本 repo 的 fail-open 慣例）；
    `try` 外＝該相依一炸，整支 hook 就不存在了，而不存在是 fail-open ⇒ 守衛靜默消失。
    這個區別就是本判準的全部價值：兩者的螢幕表徵完全相同，只有這裡分得開。
    """
    tree = ast.parse(source)
    guarded_nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for child in ast.walk(node):
                guarded_nodes.add(id(child))
    out: list[tuple[str, bool]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append((alias.name.split(".")[0], id(node) in guarded_nodes))
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.append((node.module.split(".")[0], id(node) in guarded_nodes))
    return out


def hook_chain_py39_census() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """回傳 (無 try 保護的違規, try 保護下的退化) —— 兩者皆 `{相對路徑: [構造]}`。

    起點**現查**而非寫死：`.claude/settings.json` 註冊了哪幾支就掃哪幾支（同
    `hook_wiring` 檔頭的理由——寫死清單會在條目增刪時靜默失明）。
    """
    settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))
    entries = [_LAUNCHER_REL] + [rel for _evt, rel in hook_wiring.settings_targets(settings)]
    pending: list[tuple[Path, bool]] = []
    for rel in dict.fromkeys(entries):
        path = _REPO_ROOT / rel
        if path.is_file():
            pending.append((path, False))
    hard: dict[str, list[str]] = {}
    soft: dict[str, list[str]] = {}
    seen: dict[Path, bool] = {}
    while pending:
        path, guarded = pending.pop()
        if path in seen and seen[path] <= guarded:
            continue
        seen[path] = guarded
        source = path.read_text(encoding="utf-8")
        rel = path.relative_to(_REPO_ROOT).as_posix()
        bad = py39_incompat(source)
        if bad:
            (soft if guarded else hard)[rel] = bad
        for mod, in_try in _local_imports(source):
            for cand in (_REPO_ROOT / "tools" / "lib" / f"{mod}.py", path.parent / f"{mod}.py"):
                if cand.is_file():
                    pending.append((cand, guarded or in_try))
    return hard, soft


#: try/except 保護下的**退化**（不是崩潰）。落地當回合實測＝`quota_meter.py` 的
#: `from datetime import UTC`（3.11+）。後果不是 hook 死掉，是 `context_budget_guard.py`
#: 的額度軸整條變成 `None`＝**靜默失能**，而 hook 仍回 rc=0。
#: shrink-only：多一筆＝又多一個在 mac 預設直譯器下會靜默失能的能力；少一筆＝請改小。
#:
#: 🔴 這張表刻意**不帶行號**（落地當回合就踩到了）：初版把 `@L51` 寫進 key，同一輪另一個
#: 包在 `quota_meter.py` 上游插了一行，本鎖當場紅在一個與它守的主題完全無關的事情上。
#: 「同一個構造換了行號」不是缺陷，判它只會製造要人去改表的假紅——而被改怕的表最後
#: 一定被改寬。行號留在**必須為空**的那一半（`hard`）：那裡不會有存量，故不會腐化。
_PY39_DEGRADATION_DEBT: dict[str, list[str]] = {
    "tools/lib/quota_meter.py": ["from datetime import UTC"],
}


def _without_linenos(items: list[str]) -> list[str]:
    """`"from datetime import UTC@L51"` → `"from datetime import UTC"`（見上方 WHY）。"""
    return sorted({item.rsplit("@L", 1)[0] for item in items})


class TestHookChainLoadsOnTheMacDefaultInterpreter(unittest.TestCase):
    """MAC-03：把「hook 鏈在 3.9 下會怎樣」從散文變成量測值。

    這道鎖在本輪之前**不存在**：`test_dev_start.py` 的 `_PY39_ENTRYPOINTS` 只涵蓋
    `dev_start.py`(prelude) 與 `bootstrap_core.py`(whole)，hook 鏈一支都不在裡面
    （實查：該檔全文不含 `_hook_launcher` 與 `settings_targets` 兩個字串）。
    """

    def test_no_unguarded_py311_construct_in_the_hook_chain(self) -> None:
        hard, _soft = hook_chain_py39_census()
        self.assertEqual(
            hard, {},
            "hook 鏈上**沒有 try/except 保護**的那一段出現 3.10+/3.11+ 構造 ⇒ 在 macOS "
            "預設 python3（常年 3.9）上，六支守衛會一起靜默消失（import 失敗是 fail-open，"
            "CC 只記一行 ERROR、工具照跑，螢幕表徵與『修好了』完全相同）。"
            "修法：改成 3.9 相容寫法，或把該 import 包進 try/except 並讓對應能力誠實退化",
        )

    def test_guarded_degradations_only_shrink(self) -> None:
        _hard, soft = hook_chain_py39_census()
        soft = {rel: _without_linenos(items) for rel, items in soft.items()}
        self.assertEqual(
            soft, dict(_PY39_DEGRADATION_DEBT),
            "try/except 保護下的 3.9 退化清單與債表不符。多一筆＝mac 預設直譯器上又多"
            "一個會**靜默失能**的能力（**不得調高**）；少一筆＝債已還請改小",
        )

    def test_the_scanner_has_teeth(self) -> None:
        """合成注入：三種構造各自必須被抓到，而 3.9 相容寫法不得誤紅。"""
        self.assertEqual(py39_incompat("import json\nfrom pathlib import Path\n"), [])
        self.assertTrue(py39_incompat("import tomllib\n"))
        self.assertTrue(py39_incompat("from datetime import UTC, datetime\n"))
        self.assertTrue(py39_incompat("from typing import Self\n"))
        self.assertTrue(py39_incompat("match x:\n    case 1:\n        pass\n"))

    def test_r82_the_family_that_used_to_be_invisible(self) -> None:
        """🔴 R82／C5：五種此前**整片失明**的形態，逐條合成注入自證。

        失明是靜默的：掃描器照跑、照回報 0 命中，只是那一族從來不在分母裡。實測起點＝
        `quota_policy.py` 有 6 個 3.10+ 構造，而舊版 `py39_incompat` 對它回空集合。
        """
        for label, src in (
            ("dataclass(slots=)",
             "from dataclasses import dataclass\n@dataclass(frozen=True, slots=True)\n"
             "class A:\n    x: int\n"),
            ("dataclass(kw_only=)",
             "from dataclasses import dataclass\n@dataclass(kw_only=True)\n"
             "class A:\n    x: int\n"),
            ("zip(strict=)", "list(zip([1], [2], strict=False))\n"),
            ("itertools.pairwise", "from itertools import pairwise\n"),
            ("typing.TypeAlias", "from typing import TypeAlias\n"),
            ("typing 屬性存取", "import typing\nX = typing.TypeGuard\n"),
            ("執行期 X | None", "import typing\nY: typing.Any = int | None\n"),
        ):
            with self.subTest(form=label):
                self.assertTrue(py39_incompat(src), f"{label} 沒有被抓到＝這一族仍失明")

    def test_r82_the_new_rules_do_not_manufacture_false_reds(self) -> None:
        """鑑別力反證：3.9 合法的寫法一律不得誤紅——否則這支掃描器活不過一輪。"""
        for label, src in (
            ("lazy 註記裡的 X | None",
             "from __future__ import annotations\ndef f(a: int | None) -> str | None:\n"
             "    return None\n"),
            ("真的位元運算", "flags = 1 | 2\nmask = a | b\n"),
            ("不帶 3.10 旗標的 dataclass",
             "from dataclasses import dataclass\n@dataclass(frozen=True)\n"
             "class A:\n    x: int\n"),
            ("不帶 strict 的 zip", "list(zip([1], [2]))\n"),
            ("同名但不同 owner 的 kwarg", "requests.get(url, strict=True)\n"),
        ):
            with self.subTest(form=label):
                self.assertEqual(py39_incompat(src), [], f"{label} 被誤判成 3.10+ 構造")

    def test_r82_the_quota_policy_module_is_loadable_on_39(self) -> None:
        """🔴 C5 的驗收本體：額度判讀層在 mac 原廠直譯器上必須**載得起來**。

        它是 `quota_gate.py` 的 **hard import**（刻意的：判讀原語不給 fallback stub）
        ⇒ 它一炸，hook 端的 try/except 就把 `quota_gate` 收成 `None`，額度軸整條短路，
        而 `note_degraded()` 自己就住在 quota_gate 裡 ⇒ **零訊息、零痕跡**。
        """
        src = (_REPO_ROOT / "tools" / "lib" / "quota_policy.py").read_text(encoding="utf-8")
        self.assertEqual(py39_incompat(src), [])

    def test_the_guard_distinction_is_real(self) -> None:
        """`try` 內外必須分得開——分不開的話兩種後果會被混成同一個數字。"""
        self.assertEqual(
            _local_imports("import quota_meter\n"), [("quota_meter", False)])
        self.assertEqual(
            _local_imports("try:\n    import quota_meter\nexcept Exception:\n    pass\n"),
            [("quota_meter", True)])


class TestPosixCarrierWarningTellsTheTruth(unittest.TestCase):
    """MAC-03：那道 day 1 必響的告警，內容必須是真的。

    WHY：載具失效的螢幕表徵與「修好了」完全相同（根 CLAUDE.md〈鐵律一之二〉），
    所以這行字是**唯一**的訊號。讓它在 mac 上第一天就說一句可被戳破的假話，等於在訓練
    操作者忽略它——而真的全部 hook 死掉時，它印的是一模一樣的話。
    """

    @staticmethod
    def _below_floor_message() -> str:
        settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))
        problems = hook_wiring.posix_carrier_problems(
            settings, str(_REPO_ROOT),
            exists=lambda _p: True,
            is_exec=lambda _p: True,
            probe=lambda _p: ("/usr/bin/python3", (3, 9)),
        )
        assert problems, "版本分支一句話都沒印——判準已失效"
        return "\n".join(problems)

    def test_the_false_causal_claim_is_gone(self) -> None:
        self.assertNotIn(
            _FALSE_CAUSAL_CLAIM, self._below_floor_message(),
            f"版本告警又出現被撤回的因果「{_FALSE_CAUSAL_CLAIM}」——實測為假："
            "現行 hook 集在 3.9 下載入得起來（見 TestHookChainLoadsOnTheMacDefaultInterpreter）。"
            "把風險寫成事實，第一次被戳破之後整行字就沒人看了",
        )

    def test_it_still_names_the_floor_and_the_real_risk(self) -> None:
        message = self._below_floor_message()
        for token in ("3.9", "bootstrap_core", "fail-open", "quota_meter"):
            self.assertIn(token, message, f"版本告警缺少「{token}」——{message}")

    def test_the_measured_degradation_named_in_the_message_is_real(self) -> None:
        """訊息點名 `quota_meter` 不得是空話：它必須真的在退化債表上。"""
        self.assertIn(
            "tools/lib/quota_meter.py", _PY39_DEGRADATION_DEBT,
            "版本告警點名了 quota_meter，但退化債表沒有它 ⇒ 訊息在講一件已經不存在的事",
        )


class TestMacosCiRegistersTheDefaultStateMasking(unittest.TestCase):
    """MAC-03(CI)：setup-python 遮蔽必須被登記，且至少有一條剖面真的量得到預設態。"""

    @staticmethod
    def _job_block(name: str) -> str:
        text = _MACOS_CI.read_text(encoding="utf-8")
        start = text.index(f"\n  {name}:\n")
        rest = text[start + 1:]
        nxt = re.search(r"\n  [a-z0-9-]+:\n", rest)
        return rest[: nxt.start()] if nxt else rest

    def test_the_smoke_job_declares_that_it_masks_the_default_state(self) -> None:
        block = self._job_block("macos-smoke")
        setup_idx = block.index("uses: actions/setup-python")
        head = block[:setup_idx]
        for token in ("R82 MAC-03", "3.9", "不蘊含"):
            self.assertIn(
                token, head,
                f"macos-smoke 的 setup-python 之前缺少遮蔽登記（「{token}」）——"
                "這一步讓本 job 結構上永遠走不到 mac 真機的預設態，那件事必須寫在它旁邊，"
                "否則本 job 的綠會被讀成「mac 預設態沒問題」",
            )

    def test_one_profile_measures_the_system_interpreter_before_setup_python(self) -> None:
        block = self._job_block("macos-nightly-full")
        probe_idx = block.index("/usr/bin/python3 tools/check_hooks_liveness.py")
        setup_idx = block.index("uses: actions/setup-python")
        self.assertLess(
            probe_idx, setup_idx,
            "預設態現查排在 setup-python 之後 ⇒ 量到的是 3.11，不是 runner 的系統直譯器"
            "（那正是本 finding 的病本身：剖面存在但被遮掉）",
        )
        self.assertIn(
            "continue-on-error: true", block[:probe_idx],
            "預設態現查必須 advisory：runner 映像的系統版本會漂移，拿它當阻斷判準"
            "第一次漂移就會被關掉",
        )


# ═════════════════════════════════════════════════════════════════════════════
# MAC-04：launchd 的 WakeToRun／NextRunTime 對等物
# ═════════════════════════════════════════════════════════════════════════════

#: 被撤回的兩句「無從檢查」。前半（plist 沒有這個鍵）為真，後半（沒辦法查）為假。
_RETRACTED_LAUNCHD_CLAIMS = (
    "無對應 plist 鍵可查",
    "launchd 不提供 next-run 憑證",
)

#: 🔴 判準刻意**綁在那兩項身上**，不是整檔禁字：同一句「無對應 plist 鍵可查」用在
#: `LogonType` 那一列**是真的**（LaunchAgent 綁 GUI session，這件事在 macOS 上確實
#: 沒有任何可查的對等物）。整檔禁字會把一句真話一起判紅，而那種鎖的下場是被改寬。
_LAUNCHD_ITEMS_WITH_A_REAL_EQUIVALENT = ("WakeToRun", "NextRunTime")


def retracted_launchd_claim_lines(src: str) -> list[str]:
    """回傳「**有**對等物的那兩項，卻仍宣稱無從檢查」的行（純函式，可注入測鑑別力）。"""
    bad: list[str] = []
    for line in src.splitlines():
        if not any(item in line for item in _LAUNCHD_ITEMS_WITH_A_REAL_EQUIVALENT):
            continue
        if any(claim in line for claim in _RETRACTED_LAUNCHD_CLAIMS):
            bad.append(line.strip())
    return bad


def pmset_capability_rows(src: str) -> list[str]:
    """安裝器裡帶 `(expected …)` 且提到 pmset 的能力列（＝跨平台對稱鎖會計入的那種）。"""
    return [
        line.strip()
        for line in src.splitlines()
        if not line.strip().startswith("#") and "pmset" in line
        and line.strip().startswith("_cap_line")
    ]


class TestWakeToRunHasAMacEquivalent(unittest.TestCase):
    """MAC-04：`WakeToRun` 在 mac 上有對等物，安裝器必須指得出來、查得到、教得會。"""

    def setUp(self) -> None:
        self.src = _MAC_INSTALLER.read_text(encoding="utf-8")

    def test_the_installer_knows_the_exact_command(self) -> None:
        self.assertIn(
            "pmset repeat wakeorpoweron", self.src,
            "安裝器全檔零 pmset ⇒ 睡眠中的 Mac 02:00 不會醒，nightly 延到開蓋才跑，"
            "而 --status 的心跳仍印「✅ 新鮮」（空窗在唯一的每日回饋通道上不可見）",
        )
        self.assertIn(
            "sudo pmset repeat wakeorpoweron MTWRFSU", self.src,
            "必須印出**逐字可執行**的指令：這一項需提權、腳本刻意不代跑，"
            "只給一句「請自行設定」等於沒給",
        )

    def test_the_capability_table_can_actually_check_it(self) -> None:
        rows = pmset_capability_rows(self.src)
        self.assertGreaterEqual(
            len(rows), 2,
            f"能力表只有 {len(rows)} 列提到 pmset（需要 WakeToRun 與 NextRunTime 各一列）："
            f"{rows}。純「－ …無對應鍵可查」的寫法不帶 `(expected …)`，"
            "跨平台對稱鎖 test_schedule_capability_parity 一列都不會計入",
        )
        joined = " ".join(rows)
        self.assertIn("WakeToRun", joined)
        self.assertIn("NextRunTime", joined)

    def test_the_retracted_no_way_to_check_claims_are_gone(self) -> None:
        self.assertEqual(
            retracted_launchd_claim_lines(self.src), [],
            "WakeToRun／NextRunTime 又被宣稱成「無從檢查」——這兩項在 macOS 上有真對等物"
            "（pmset）。把「這個 plist 鍵不存在」寫成「這件事沒辦法查」，"
            "等於把一個真缺口記成一個不存在的缺口，而 --status 照樣全綠",
        )

    def test_the_claim_detector_does_not_swallow_the_true_one(self) -> None:
        """兩個方向：撤回的形態必紅；`LogonType` 那句**真話**不得被連坐。"""
        self.assertTrue(retracted_launchd_claim_lines(
            '  echo "  －  WakeToRun 對等：launchd 原生…，無對應 plist 鍵可查"\n'))
        self.assertTrue(retracted_launchd_claim_lines(
            '  echo "  －  NextRunTime 對等：launchd 不提供 next-run 憑證——改以覆蓋連續性"\n'))
        self.assertEqual(retracted_launchd_claim_lines(
            '  echo "  －  LogonType 對等 = (無對應鍵)；launchd 無對應 plist 鍵可查"\n'), [])

    def test_install_path_surfaces_it_not_only_status(self) -> None:
        """只在 --status 提是不夠的：裝完就走的人永遠不會看到它。"""
        start = self.src.index("cmd_install() {")
        end = self.src.index("cmd_uninstall() {")
        self.assertIn(
            "pmset", self.src[start:end],
            "cmd_install 全段不提 pmset ⇒ 四項排程設定裡唯一需要人工動作的那一項，"
            "只會出現在使用者不一定會跑的 --status 裡",
        )

    def test_the_row_extractor_has_teeth(self) -> None:
        """合成注入：把 `(expected …)` 那個形態拿掉，本判準必須看得出來。"""
        self.assertEqual(
            pmset_capability_rows(
                '  echo "  －  WakeToRun 對等：pmset，無對應 plist 鍵可查"\n'),
            [], "純 echo 的『－』列被誤計成能力列——那種寫法對稱鎖不會計入",
        )
        self.assertEqual(
            len(pmset_capability_rows(
                '  _cap_line "WakeToRun 對等（pmset repeat）" "$(x)" "已排定" \\\n')), 1)


# ═════════════════════════════════════════════════════════════════════════════
# R83 交棒：本輪買不到的那一半，必須是一組可貼可跑的指令  round-label-ok（交棒指名承接輪）
# ═════════════════════════════════════════════════════════════════════════════

#: R83 在 mac 真機上要跑的落實指令（每一條都能一行裁決一句本輪只能靜態推導的宣稱）。  round-label-ok
R83_VERIFICATION_COMMANDS: tuple[tuple[str, str], ...] = (
    ("mktemp", "裁決「BSD mktemp 是否必須帶模板」：mktemp; echo rc=$?"),
    ("date +%s%N", "裁決「BSD date 支不支援 %N」：輸出以字母 N 結尾即不支援"),
    ("pmset -g sched", "WakeToRun／NextRunTime 對等物的憑證值（不是 rc）"),
    ("launchctl print gui/", "launchd 是否真的載入 com.autoclaude.nightly"),
    ("/usr/bin/python3 -c", "runner／真機的系統直譯器版本（POSIX hook 載具解析到的那一支）"),
    ("tools/check_hooks_liveness.py", "以系統直譯器跑一次載具 liveness，看告警響不響"),
    ("--debug hooks", "正面現查：hook 真的還在跑（Hook SessionStart.*success）"),
)


class TestR83HandoffIsExecutable(unittest.TestCase):
    """交棒清單不得退化成散文：每一條都要有可執行的形狀與一句「它裁決什麼」。"""

    def test_every_command_carries_a_verdict_it_settles(self) -> None:
        for cmd, why in R83_VERIFICATION_COMMANDS:
            self.assertTrue(cmd.strip(), "指令欄為空")
            self.assertGreaterEqual(
                len(why), 10, f"{cmd}：理由欄過短＝沒說它裁決什麼（{why!r}）")

    def test_the_docstring_admits_what_this_file_did_not_buy(self) -> None:
        """劃界不得被人順手刪掉——刪了之後本檔會被讀成「mac 已驗過」。"""
        doc = __doc__ or ""
        for token in ("誠實劃界", "一次都沒有真跑過", "R83_VERIFICATION_COMMANDS"):
            self.assertIn(token, doc, f"檔頭劃界缺「{token}」")


if __name__ == "__main__":
    unittest.main()
