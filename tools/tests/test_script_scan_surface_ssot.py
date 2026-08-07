#!/usr/bin/env python3
"""腳本掃描面 SSOT 形狀一致性鎖（R60 Scan-E E-A-01）。

WHY（測意圖非僅行為，Rule 9）：本 repo 對 active `.sh`／`.ps1` 有兩套掃描面——
CI 的語法／BOM 掃描面（`root-infra-ci.yml` 第 2 道，`-Recurse` 三棵樹＋LATEST）與
parity 的 enrollment 發現面（`tools/check_script_parity.py`）。R60 前後者自持一份
**非遞迴的四目錄名冊**，且該名冊**沒有任何完整性鎖**（實查：生產碼／測試／缺陷帳本
三面 grep，唯一相關斷言是 `assertIn("tools/lib", _PAIR_SCAN_DIRS)` 的成員存在性）。
兩邊掃到的檔案集合當時恰好相同（各 35 支），純屬「現存腳本剛好都躺在名冊列出的
目錄裡」；任何人在既有樹下新開一層子目錄放成對腳本，CI 掃得到、parity 看不到，
「新增成對腳本必為機械攔截」這個宣稱就靜默失效而沒人會知道。

本鎖守四件事（缺任一件，E-A-01 的修復都會在下一次改動中悄悄退回去）：
  1. **單一來源（Python 消費者）**：`check_script_parity` 與兩支本地鏡射鎖都真的讀
     SSOT，沒有人偷偷回去寫自己的字面名冊。
  2. **單一來源（非 Python 消費者，R79 ARCH）**：`root-infra-ci.yml` 第 2 道與
     `tools/windows_smoke_local.ps1` [1/9] 都**完整**呼叫 SSOT 的 `--list` CLI
     （＝`_REQUIRED_SSOT_CALL` 每一格都在，含 `--with-latest`／`--check-floors`），
     且**沒有**自持第二份 `.ps1` 列舉——取代了原先為偵測三份複本不同步而養的 866 行
     對抗式正則錨（WHY 見下方大段註解）。少一個旗標就是掃描面靜默縮小而 rc 仍為 0，
     R79 四方複審實測到這個縫並補上（見 `_REQUIRED_SSOT_CALL` 的註解）。
  3. **遞迴性**：列舉實作真的遞迴（改回 `glob("*.sh")` 即紅）——用合成假樹驗，
     不依賴 repo 現況剛好有／沒有巢狀腳本。
  4. **完整性**：SSOT 三棵樹底下每一支 git-tracked `.sh`／`.ps1` 都真的被 parity
     的 `_discover_scripts()` 發現（掃描面縮小即紅；沿用 `test_platform_utils_dedup.py`
     的 `git ls-files` fail-loud 慣例）。

執行：python3 -m unittest discover -s tools/tests
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]

sys.path.insert(0, str(_TESTS_DIR))
sys.path.insert(0, str(_REPO_ROOT / "tools"))
import test_ps1_bom  # noqa: E402
import test_ps51_compat  # noqa: E402

from _script_scan_surface import (  # noqa: E402
    LATEST_TREE_KEY,
    PS1_TREE_FLOORS,
    SCRIPT_SCAN_ROOTS,
    iter_tree_scripts,
    ps1_scan_trees,
)


def _load_parity():
    """以絕對路徑載入 `tools/check_script_parity.py`（不依賴 cwd）。"""
    spec = importlib.util.spec_from_file_location(
        "_ssot_lock_check_script_parity", _REPO_ROOT / "tools" / "check_script_parity.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# 🔴 R79 ARCH：本檔第 2 件事（`TestNonPythonSitesCallTheSsot`）取代了 866 行機械。
#
# 舊形狀：`root-infra-ci.yml` 第 2 道與 `tools/windows_smoke_local.ps1` [1/9] 各自
# 用 `Get-ChildItem -Recurse -Filter *.ps1` 列舉同一份掃描面（＝SSOT 的第 2、第 3 份
# 複本）。因為兩者是 YAML／PowerShell、無法 import 本 SSOT，repo 改為「偵測三份是否
# 同步」——`tools/tests/_ci_scan_anchors.py`（154 行）三條對抗式正則錨 ＋
# `tools/tests/test_ci_scan_anchors.py`（712 行，8 class／26 支）鎖那三條錨的鑑別力。
# 該路線已翻車兩次（R56 的 `-Path` 具名參數假設、R57 的大小寫敏感假設），且錨自己的
# docstring 逐條寫著三種**已實測抓不到**的逃逸形態（`[System.IO.Directory]::GetFiles()`／
# `Get-Item`／`Resolve-Path`）——軍備競賽結構上追不完。
#
# 新形狀：兩個非 Python 站點改為**呼叫**本 SSOT 的 `--list` CLI 取得掃描面。「三份
# 不同步」自此在結構上不可能發生（只剩一份），那 866 行連同三種已知逃逸一起退場。
# 殘餘義務只剩兩條，且兩條都不需要解析 PowerShell 參數形態：
#   (a) 兩個站點真的呼叫 SSOT（正面）；
#   (b) 兩個站點沒有自己再長出一份 `.ps1` 列舉（負面）——這一條才是有牙的那條，
#       因為「把 SSOT 呼叫留著、旁邊再加一行 Get-ChildItem」正是複本復活的唯一路徑。
# per-tree 檔數下限值本身由 `test_ps51_compat.TestPs51ScanConfigPinning
# .test_tree_keys_and_floors_pinned` 釘住（讀的就是本 SSOT 的 `PS1_TREE_FLOORS`）。


#: 兩個非 Python 站點呼叫 SSOT 時**必須**出現的識別字／旗標，逐格附「少了它會怎樣」。
#: 這不是風格檢查：每一格對應一種**靜默**失效——CLI 仍回 rc=0，看起來一切正常。
#:
#: 🔴 R79 四方複審（ARCH blocking）補進 `--with-latest`：本表原先只有三格，而少一個
#: `--with-latest` 會讓 AISDLC_SDD LATEST 版整棵樹逸出掃描面。複審實測：掃描面由 20 支
#: 縮成 16 支、LATEST 那一棵的 per-tree 下限**完全沒有被檢查**，而 CLI 回 **rc=0**、
#: 本鎖兩支測試**全綠**。也就是說：本輪拿來取代 866 行對抗式錨的那句立論（「掃描面
#: 靜默縮小必須 rc=1、複本不同步結構上不可能發生」）被這道替代鎖自己重新開了一個縫，
#: 而 LATEST 樹正是 Copy-on-Evolve 每升一版就換路徑、最容易被人順手拿掉的那一格。
#: 同輪落在 pre-push 的姊妹鎖（`tools/tests/test_pre_push_dispatcher.py`）對同一件事有守
#: ——同一輪、同一件事、兩道鎖鑑別力不一致，弱的那道守的正是本次異動的兩個主站點。
#:
#: 「哪些旗標算必要」不是口味問題，是**量測值**：見
#: `TestNonPythonSitesCallTheSsot.test_a_flag_that_changes_the_scan_surface_must_be_required`
#: ——旗標一旦被實測到會改變掃描面，它就必須在本表內。
_REQUIRED_SSOT_CALL: dict[str, str] = {
    "_script_scan_surface.py": "沒有它就不是在呼叫 SSOT，本檔第 2 件事的整條立論不成立",
    "--list": "CLI 的 required 旗標；列在本表是為了讓這張表就是完整的呼叫契約",
    "--with-latest": "少了它，LATEST 版樹整棵逸出掃描面（複審實測 20→16 支）而 rc 仍為 0",
    "--check-floors": "少了它，per-tree 檔數下限一棵都不會被檢查——掃描面靜默縮小的唯一訊號就此消失",
}


def ssot_call_problems(code: str) -> list[str]:
    """站點程式碼有沒有完整呼叫 SSOT；`[]`＝完整。

    純函式（紅綠由合成／真檔注入自證，見 `TestNonPythonSitesCallTheSsot` 下半部）
    ——把判準抽出來的理由是：只斷言「現況為真」的鎖，沒有辦法證明它在違規時會說話。
    """
    return [
        f"未見「{needle}」——{why}"
        for needle, why in _REQUIRED_SSOT_CALL.items()
        if needle not in code
    ]


class TestSsotHasNoSecondRoster(unittest.TestCase):
    """單一來源：三個 Python 消費者都必須真的讀 SSOT，不得自持第二份名冊。"""

    def test_parity_pair_scan_dirs_is_the_ssot_tuple(self) -> None:
        parity = _load_parity()
        self.assertIs(
            parity._PAIR_SCAN_DIRS, SCRIPT_SCAN_ROOTS,
            "check_script_parity._PAIR_SCAN_DIRS 不再指向 SSOT `SCRIPT_SCAN_ROOTS`"
            "——疑似有人把名冊複製回本地字面值（R60 E-A-01 迴歸）",
        )

    def test_parity_source_has_no_literal_roster(self) -> None:
        """負面斷言：生產碼不得再出現「一行列滿掃描根」的字面名冊。

        `assertIs` 只保證「現在指向 SSOT」；有人另加一份平行名冊給別的函式用時
        它仍全綠。本斷言鎖住的是「本檔不再是掃描根的持有者」這個意圖。
        """
        src = (_REPO_ROOT / "tools" / "check_script_parity.py").read_text(
            encoding="utf-8"
        )
        code = "\n".join(
            ln for ln in src.splitlines() if not ln.lstrip().startswith("#")
        )
        for root in ("AutoClaude/tools", "AISDLC_SDD/scripts"):
            self.assertNotIn(
                f'"{root}"', code,
                f"check_script_parity.py 的功能碼出現掃描根字面值 {root!r}"
                "——掃描根一律取自 `_script_scan_surface.SCRIPT_SCAN_ROOTS` SSOT",
            )

    def test_ps51_compat_scan_trees_keys_come_from_ssot(self) -> None:
        keys = [key for key, _files, _floor in test_ps51_compat.scan_trees()]
        self.assertEqual(
            keys, list(SCRIPT_SCAN_ROOTS) + [LATEST_TREE_KEY],
            "test_ps51_compat.scan_trees() 的樹 key 序列與 SSOT 不一致",
        )

    def test_ps1_bom_scan_prefixes_come_from_ssot(self) -> None:
        prefixes = test_ps1_bom._scan_prefixes()
        self.assertEqual(
            list(prefixes[: len(SCRIPT_SCAN_ROOTS)]),
            [f"{root}/" for root in SCRIPT_SCAN_ROOTS],
            "test_ps1_bom._scan_prefixes() 的固定樹前綴與 SSOT 不一致",
        )
        self.assertTrue(
            prefixes[-1].startswith("AISDLC_SDD/")
            and prefixes[-1] != "AISDLC_SDD/scripts/",
            f"最後一項應為 LATEST 版整版目錄前綴，實得 {prefixes[-1]!r}",
        )


class TestNonPythonSitesCallTheSsot(unittest.TestCase):
    """兩個非 Python 消費站點：真的呼叫 SSOT，且沒有自持第二份 `.ps1` 列舉。"""

    #: (標籤, 檔案, 區塊抽取式)。區塊而非整檔：整檔比對會被別處巧合字串滿足。
    _SITES = (
        (
            "root-infra-ci.yml 第 2 道",
            _REPO_ROOT / ".github" / "workflows" / "root-infra-ci.yml",
            r"^ +- name: pwsh 語法解析.*?(?=^ +- name: )",
        ),
        (
            "windows_smoke_local.ps1 [1/9]",
            _REPO_ROOT / "tools" / "windows_smoke_local.ps1",
            r"--- \[1/\d+\] Parser.*?(?=# ── 建立 fake repo)",
        ),
    )

    def _region(self, path: Path, pattern: str, label: str) -> str:
        text = path.read_text(encoding="utf-8")
        m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(m, f"{label} 抽不到區塊——結構已變動，本鎖不得以「抽不到」靜默放行")
        assert m is not None
        return m.group(0)

    def _code_only(self, region: str) -> str:
        """剝掉整行 `#` 註解——註解裡提到 `Get-ChildItem` 不算自持列舉（本檔的
        WHY 段落就會提到它），註解裡寫著 SSOT 檔名也不算真的有呼叫。"""
        return "\n".join(
            ln for ln in region.split("\n") if not ln.lstrip().startswith("#")
        )

    def test_both_sites_invoke_the_ssot_lister(self) -> None:
        """正面：兩個站點的**程式碼**都完整呼叫 SSOT（識別字＋每一個必要旗標）。"""
        for label, path, pattern in self._SITES:
            with self.subTest(site=label):
                code = self._code_only(self._region(path, pattern, label))
                problems = ssot_call_problems(code)
                self.assertEqual(
                    problems, [],
                    f"{label} 的程式碼：" + "；".join(problems) + "。掃描面必須完整向 "
                    "tools/_script_scan_surface.py SSOT 取（含 LATEST 樹與 per-tree "
                    "下限檢查）；少一個旗標＝掃描面靜默縮小而 rc 仍為 0，"
                    "自行列舉則會讓 R79 消滅的「三份複本」形態復活",
                )

    def test_neither_site_grows_its_own_ps1_enumeration(self) -> None:
        """負面（本鎖的鑑別力所在）：站點內不得再出現自持的 `.ps1` 列舉。

        判準刻意**不**解析 PowerShell 參數形態（那正是 866 行對抗式正則錨追不完的
        東西），只認「這段程式碼裡有沒有 `*.ps1` 這個字面」——SSOT 呼叫端不需要它，
        任何自行列舉一定需要它（`-Filter *.ps1`／`-Include *.ps1`／
        `[System.IO.Directory]::GetFiles(x, "*.ps1")`／`Get-Item x\\*.ps1` 全部命中，
        含錨自承抓不到的那三種）。
        """
        for label, path, pattern in self._SITES:
            code = self._code_only(self._region(path, pattern, label))
            self.assertNotIn(
                "*.ps1", code,
                f"{label} 的程式碼出現 `*.ps1` 檔案樣式——掃描面只有一個持有者"
                "（tools/_script_scan_surface.py），站點內自行列舉即為 R79 消滅的"
                "「複本漂移」形態復活；真有需要請改擴 SSOT 的 CLI",
            )

    # ── 鑑別力自證（三支；缺了它們，上面兩支可能對任何輸入都綠）──────────────────

    def test_dropping_any_required_flag_from_a_real_site_is_red(self) -> None:
        """注入（對**真實檔案內容**做，不是合成樣本）：把任一必要格從站點程式碼裡拿掉，
        本鎖必須指名那一格轉紅。

        這一支同時買到第二件事：**表內沒有空轉的格子**——每一格都真的對現行的兩個站點
        生效。「鎖存在但沒有鑑別力」在本 repo 是最大單一失誤類，不准只寫鎖不驗鎖。
        """
        for label, path, pattern in self._SITES:
            code = self._code_only(self._region(path, pattern, label))
            for needle in _REQUIRED_SSOT_CALL:
                with self.subTest(site=label, needle=needle):
                    problems = ssot_call_problems(code.replace(needle, ""))
                    self.assertTrue(
                        any(needle in p for p in problems),
                        f"{label} 拿掉「{needle}」之後本鎖仍未指名它 ⇒ 該格零鑑別力"
                        f"（實得：{problems}）",
                    )

    def test_a_healthy_call_is_green(self) -> None:
        """對照組：完整的呼叫不得被判紅——否則本鎖只是「一律判紅」（同樣沒有鑑別力）。"""
        healthy = ("python3 tools/_script_scan_surface.py --list --suffix .ps1 "
                   "--with-latest --check-floors --absolute")
        self.assertEqual(ssot_call_problems(healthy), [])

    def test_a_flag_that_changes_the_scan_surface_must_be_required(self) -> None:
        """把「哪些旗標算必要」變成**量測值**，不是一句宣稱（本鎖的鎖）。

        `--with-latest` 之所以必要，理由不是有人覺得它重要，而是現場實測它會改變掃描面：
        少了它，`ps1_scan_trees()` 只回三棵樹，LATEST 那一棵連同它的 per-tree 下限一起
        消失。哪天這件事不再成立（例如 LATEST 併進固定樹），本支會先紅——那才是把該格
        從必要表移除的合法時機，而不是「有人覺得它可以拿掉」。
        """
        with_latest = {key for key, _prefix in ps1_scan_trees(_REPO_ROOT, True)}
        without = {key for key, _prefix in ps1_scan_trees(_REPO_ROOT, False)}
        self.assertEqual(
            with_latest - without, {LATEST_TREE_KEY},
            "`--with-latest` 不再是「多掃一棵 LATEST 樹」的意思 ⇒ 下面那條必要性推論失效",
        )
        self.assertGreater(
            PS1_TREE_FLOORS[LATEST_TREE_KEY], 0,
            "LATEST 樹的 per-tree 下限為 0 ⇒ 少寫旗標時「下限沒被檢查」不再是損失",
        )
        self.assertIn(
            "--with-latest", _REQUIRED_SSOT_CALL,
            "這個旗標被實測到會改變掃描面（少一整棵樹＋少一道下限檢查），卻不在必要表內"
            "——站點少寫它就是掃描面靜默縮小，而 CLI 仍回 rc=0（R79 ARCH blocking 本體）",
        )


class TestScanSurfaceIsRecursive(unittest.TestCase):
    """遞迴性（本鎖的核心鑑別力）：用合成假樹驗，不靠 repo 現況。

    R60 實測基線：修復前 `_discover_scripts()` 對 `tools/ops/newpair.{sh,ps1}`、
    `AutoClaude/tools/hooks/hookpair.{sh,ps1}` 一律回 False（非遞迴 glob）。把
    `iter_tree_scripts()` 的 `rglob` 改回 `glob` 本類別即翻紅。
    """

    _NESTED_PAIRS = ("tools/ops/newpair", "AutoClaude/tools/hooks/hookpair")
    _NESTED_SINGLES = ("AISDLC_SDD/scripts/nested/deep.sh", "tools/lib/libonly.ps1")
    _TOP_LEVEL_PAIR = "tools/legitpair"
    _TOP_LEVEL_SINGLE = "tools/legit.sh"

    def _fake_tree(self, td: str) -> Path:
        fake = Path(td)
        rels = [f"{p}{suffix}" for p in self._NESTED_PAIRS for suffix in (".sh", ".ps1")]
        rels += list(self._NESTED_SINGLES)
        rels += [f"{self._TOP_LEVEL_PAIR}{suffix}" for suffix in (".sh", ".ps1")]
        rels.append(self._TOP_LEVEL_SINGLE)
        for rel in rels:
            path = fake / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x\n", encoding="utf-8", newline="")
        return fake

    def test_iter_tree_scripts_walks_subdirectories(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            found = set(iter_tree_scripts(self._fake_tree(td)))
        for rel in self._NESTED_SINGLES:
            self.assertIn(
                rel, found,
                f"{rel} 未被列舉——`iter_tree_scripts()` 疑似退回非遞迴 glob（E-A-01 迴歸）",
            )
        # 正控：非遞迴實作也找得到的頂層檔仍在（證明本測試不是「一律通過」）
        self.assertIn(self._TOP_LEVEL_SINGLE, found)

    def test_parity_discovers_nested_pairs_and_singles(self) -> None:
        parity = _load_parity()
        with tempfile.TemporaryDirectory() as td:
            fake = self._fake_tree(td)
            with mock.patch.object(parity, "_REPO_ROOT", fake):
                pairs, singles = parity._discover_scripts(None)
        for stem in self._NESTED_PAIRS:
            self.assertIn(
                stem, pairs,
                f"巢狀成對腳本 {stem}.sh/.ps1 未被 enrollment 發現——CI 的 -Recurse "
                "掃得到它、parity 卻看不到（E-A-01 本體迴歸）",
            )
        for rel in self._NESTED_SINGLES:
            self.assertIn(rel, singles, f"巢狀單邊腳本 {rel} 未被 enrollment 發現")
        # 兩個正控（掃描面若整體壞掉，這兩條會先紅，可分辨「壞了」與「只是不遞迴」）
        self.assertIn(self._TOP_LEVEL_PAIR, pairs)
        self.assertIn(self._TOP_LEVEL_SINGLE, singles)


class TestScanSurfaceCompleteness(unittest.TestCase):
    """完整性：SSOT 三棵樹底下每支 git-tracked 腳本都真的被 enrollment 發現。"""

    def _tracked_scripts(self) -> list[str]:
        proc = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "-c", "core.quotePath=false",
             "ls-files", "--", "*.sh", "*.ps1"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            raise AssertionError(
                f"git ls-files 失敗（rc={proc.returncode}；stderr="
                f"{proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
            )
        prefixes = tuple(f"{root}/" for root in SCRIPT_SCAN_ROOTS)
        return sorted(
            line for line in proc.stdout.splitlines()
            if line and line.startswith(prefixes)
        )

    def test_every_tracked_script_in_ssot_trees_is_discovered(self) -> None:
        tracked = self._tracked_scripts()
        # 下限釘選：R76 實測 34 支（三棵樹內、不含 LATEST 版樹）。低於此數
        # ＝git ls-files 樣式或 SSOT 前綴被改壞，等同掃描面靜默縮小。
        # R76 由 35 下修為 34：reschedule_g0_gatecheck.ps1 整支刪除（真孤兒，它要重排的
        # AutoClaude_SD09_G0_GateCheck 於 R71 已從本機移除）——刻意刪減，非掃描面縮水。
        self.assertGreaterEqual(
            len(tracked), 34,
            f"SSOT 三棵樹內只找到 {len(tracked)} 支 tracked .sh/.ps1（下限 34）"
            "——掃描面疑似縮小；刻意刪減腳本請同步下修本下限",
        )
        parity = _load_parity()
        pairs, singles = parity._discover_scripts(None)
        discovered = set(singles) | {
            f"{stem}{suffix}" for stem in pairs for suffix in (".sh", ".ps1")
        }
        missing = [rel for rel in tracked if rel not in discovered]
        self.assertEqual(
            missing, [],
            "以下 git-tracked 腳本落在 SSOT 掃描樹內、卻未被 check_script_parity 的 "
            f"enrollment 發現（納管完整性破洞）：{missing}",
        )


if __name__ == "__main__":
    unittest.main()
