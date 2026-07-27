#!/usr/bin/env python3
"""active .ps1 UTF-8 BOM 政策機械守門（R15 SCAN-C-2；DEF-101-002 政策）。

WHY：root-infra-ci.yml 第 2 道（pwsh parse + BOM 守門）在 CI 停擺期間無本地
對等——人工以編輯器改 .ps1 存成「UTF-8 無 BOM」時零訊號直推，zh-TW Windows
PowerShell 5.1 會以 CP950 誤讀非 ASCII 內容（中文註解/訊息變亂碼、字串比對
靜默失效）。本測試把該 step 的 BOM 判準搬進 unittest 載具（root-infra-ci
第 8 道＋pre-push root-infra leg＋mac nightly 三處自動執行，零接線），純位元
組檢查、平台中立。

政策（DEF-101-002；.editorconfig utf-8-bom）：
  - 含非 ASCII bytes 的 active .ps1 **必須**以 UTF-8 BOM（EF BB BF）開頭；
  - 純 ASCII 無 BOM 合法；
  - 反向斷言：檔案首 byte 為 0xEF 但首 3 bytes 非恰為 EF BB BF → 半殘 BOM，
    一律違規（防編輯器截斷/手拼 BOM）。

掃描範圍鏡射 root-infra-ci.yml「pwsh 語法解析 + UTF-8 BOM 守門」step 的樹清單
（R56 round 5：該「鏡射」自此有機械互鎖，見 TestScanConfigPinning 第二支測試；
同一組四棵 .ps1 掃描樹的硬編共四處，四處已全數互鎖，勿再只數到三處）：
根 tools/、AutoClaude/tools/、AISDLC_SDD/scripts/（皆遞迴）＋ AISDLC_SDD
LATEST 整版目錄（LATEST 以 scripts/sdd_version.py SSOT 解析，解析失敗
fail-loud 不得縮面；凍結版 v0.01~v0.2X 排除）。列舉以 `git ls-files '*.ps1'`
過濾樹（排除未追蹤垃圾；CI 端 Get-ChildItem 掃磁碟，checkout 下兩者等價）。
掃描檔數下限釘選＝2026-07-20 實測 19 支打八折（15），防掃描面靜默縮小；
樹前綴清單另由 TestScanConfigPinning 釘選。
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]
_BOM = b"\xef\xbb\xbf"
# 下限釘選：低於此數＝掃描面疑似縮小（前綴打錯/樹改名/ls-files 異常），紅燈。
# ＝2026-07-20 實測 19 支 active .ps1 打八折取整；刻意刪減腳本時同步下修。
_MIN_FILES = 15


def _latest_root() -> Path:
    """LATEST 版根目錄（sdd_version.py SSOT；解析失敗即 AssertionError）。"""
    sdd_root = _REPO_ROOT / "AISDLC_SDD"
    resolver = sdd_root / "scripts" / "sdd_version.py"
    proc = subprocess.run(
        [sys.executable, str(resolver), "--sdd-root", str(sdd_root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    name = proc.stdout.strip()
    if proc.returncode != 0 or not name:
        raise AssertionError(
            f"LATEST 解析失敗（sdd_version.py rc={proc.returncode}；stderr="
            f"{proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
        )
    return sdd_root / name


def _scan_prefixes() -> tuple[str, ...]:
    """掃描樹前綴（鏡射 root-infra-ci.yml 第 2 道；LATEST 為整版目錄）。"""
    return (
        "tools/",
        "AutoClaude/tools/",
        "AISDLC_SDD/scripts/",
        f"AISDLC_SDD/{_latest_root().name}/",
    )


def _active_ps1_files() -> list[str]:
    """git tracked 且位於掃描樹內的 .ps1 相對路徑清單（fail-loud）。"""
    proc = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "-c", "core.quotePath=false",
         "ls-files", "--", "*.ps1"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"git ls-files 失敗（rc={proc.returncode}；stderr="
            f"{proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
        )
    prefixes = _scan_prefixes()
    return sorted(
        line for line in proc.stdout.splitlines() if line.startswith(prefixes)
    )


def classify_ps1_bytes(data: bytes) -> str | None:
    """純函式核心：回傳違規說明；合規回傳 None。

    判準順序：完整 BOM → 合規；首 byte 0xEF 但非完整 BOM → 半殘 BOM 違規
    （反向斷言）；含任一 >0x7F byte → 缺 BOM 違規；純 ASCII → 合規。
    """
    if data.startswith(_BOM):
        return None
    if data[:1] == b"\xef":
        return "半殘 BOM（首 byte 0xEF 但首 3 bytes 非恰為 EF BB BF）"
    if any(b > 0x7F for b in data):
        return (
            "含非 ASCII bytes 但無 UTF-8 BOM"
            "（.editorconfig utf-8-bom 政策；zh-TW Windows PS5.1 會以 CP950 誤讀）"
        )
    return None


def scan_files(rels: list[str], repo_root: Path) -> tuple[list[str], list[str]]:
    """回傳 (offenders, read_failures)——讀檔失敗一律列報不靜默跳過。"""
    offenders: list[str] = []
    read_failures: list[str] = []
    for rel in rels:
        try:
            data = (repo_root / rel).read_bytes()
        except OSError as exc:
            read_failures.append(f"{rel}: {type(exc).__name__}: {exc}")
            continue
        verdict = classify_ps1_bytes(data)
        if verdict is not None:
            offenders.append(f"{rel}: {verdict}")
    return offenders, read_failures


# R56 round 6（QA B-1）：CI 第 2 道掃描樹抽取式。字元類必須容納 `.`／`-`，
# 否則 `.github/scripts` 這類路徑被插進 CI 時本鎖靜默失效（實測 11 支全綠）。
_CI_TREE_RE = r"Get-ChildItem -Path ([A-Za-z0-9_.\-/]+) -Recurse"

class TestPs1Bom(unittest.TestCase):
    def test_active_ps1_bom_policy(self) -> None:
        files = _active_ps1_files()
        # 掃描檔數下限釘選：掃描面縮小必紅
        self.assertGreaterEqual(
            len(files), _MIN_FILES,
            f"active .ps1 掃描檔數 {len(files)} < 下限 {_MIN_FILES}——掃描面疑似"
            f"縮小（樹前綴打錯/腳本大規模消失）；刻意刪減請同步下修 _MIN_FILES",
        )
        offenders, read_failures = scan_files(files, _REPO_ROOT)
        self.assertEqual(
            read_failures, [],
            "以下 .ps1 無法讀取——掃描面不得靜默縮小：\n" + "\n".join(read_failures),
        )
        self.assertEqual(
            offenders, [],
            "發現違反 UTF-8 BOM 政策的 active .ps1（DEF-101-002：含非 ASCII 必須"
            "帶 EF BB BF，否則 zh-TW Windows PS5.1 以 CP950 誤讀）——請以帶 BOM 的"
            "UTF-8 重存（或經 Claude Code hook check_ps1_encoding.py 補 BOM）：\n"
            + "\n".join(offenders),
        )

    # ── 以下以注入 fixture 自證判準紅綠（fixture 僅存在於 tmp，不留違規樣本於 repo）──

    def _scan_fixture(self, data: bytes) -> list[str]:
        """tempfile 寫 bytes 後走檔案讀取路徑掃描（不落 repo 樹內）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "fixture_case.ps1").write_bytes(data)
            offenders, read_failures = scan_files(["fixture_case.ps1"], root)
            assert read_failures == [], read_failures
            return offenders

    def test_non_ascii_without_bom_is_detected(self) -> None:
        """假違規 fixture 必紅：非 ASCII bytes（中文註解）且無 BOM。"""
        offenders = self._scan_fixture("# 中文註解\nWrite-Host 'ok'\n".encode("utf-8"))
        self.assertEqual(len(offenders), 1, offenders)
        self.assertIn("無 UTF-8 BOM", offenders[0])

    def test_partial_bom_is_detected(self) -> None:
        """反向斷言：首 byte 0xEF 但非完整 EF BB BF ＝半殘 BOM，必紅。"""
        offenders = self._scan_fixture(b"\xef\xbbWrite-Host 'ok'\n")
        self.assertEqual(len(offenders), 1, offenders)
        self.assertIn("半殘 BOM", offenders[0])

    def test_compliant_files_are_green(self) -> None:
        """合規兩形態＝綠：BOM＋非 ASCII、純 ASCII 無 BOM（BOM＋純 ASCII 亦合法）。"""
        self.assertEqual(
            self._scan_fixture(_BOM + "# 中文註解\nWrite-Host 'ok'\n".encode("utf-8")),
            [],
        )
        self.assertEqual(self._scan_fixture(b"Write-Host 'ascii only'\n"), [])
        self.assertEqual(self._scan_fixture(_BOM + b"Write-Host 'ascii only'\n"), [])


class TestScanConfigPinning(unittest.TestCase):
    """掃描樹前綴釘選（防「刪清單一項」整樹靜默出界；LATEST 正規化升版不失效）。"""

    def _ci_pwsh_step(self) -> str:
        """root-infra-ci.yml「pwsh 語法解析 + UTF-8 BOM 守門」step 全文（抽不到即紅）。"""
        ci = (_REPO_ROOT / ".github" / "workflows" / "root-infra-ci.yml").read_text(
            encoding="utf-8"
        )
        step = re.search(
            r"^ +- name: pwsh 語法解析.*?(?=^ +- name: )", ci, re.MULTILINE | re.DOTALL
        )
        self.assertIsNotNone(
            step, "root-infra-ci.yml 找不到 pwsh 語法解析 step——結構已變動"
        )
        return step.group(0)

    def test_scan_prefixes_pinned(self) -> None:
        latest_name = _latest_root().name
        prefixes = {p.replace(latest_name, "LATEST") for p in _scan_prefixes()}
        self.assertEqual(
            prefixes,
            {
                "tools/",
                "AutoClaude/tools/",
                "AISDLC_SDD/scripts/",
                "AISDLC_SDD/LATEST/",
            },
        )

    def test_scan_prefixes_match_root_infra_ci_pwsh_step(self) -> None:
        """R56 round 5 新增（Architect）：與 root-infra-ci.yml 第 2 道機械互鎖。

        WHY：上一支測試只釘住本檔**自己的**字面前綴、完全不看 CI——CI 第 2 道擴面
        （新增第 5 棵樹）時它仍全綠，反倒是「有人記得同步改本檔」時才紅，激勵方向
        相反。而本檔檔頭自述的存在理由正是「該 step 在 CI 停擺期間無本地對等」：
        掃描面一旦漂移，新樹下「含非 ASCII 但無 UTF-8 BOM」的 .ps1 會在 pre-push／
        兩平台 smoke 全綠通過，只有燒 CI 額度才發現，而該政策（DEF-101-002／
        .editorconfig utf-8-bom）本身正是純 Windows 議題（zh-TW Windows PowerShell
        5.1 以 CP950 誤讀）。

        同一組「四棵 .ps1 掃描樹」硬編共**四處**：root-infra-ci.yml 第 2 道、
        `test_ps51_compat.scan_trees()`、`windows_smoke_local.ps1` [1/9] 的
        `$ps1Trees`、以及本檔 `_scan_prefixes()`。前三處已由 test_ps51_compat 與
        test_smoke_ci_sync 的三向鎖互鎖，本測試補上第四處（原判定「現存三處」漏數
        了本檔），四處自此全數互鎖——即 test_smoke_ci_sync.py 立下的「凡兩份硬編
        實作互稱鏡射，本 repo 一律建鎖」原則。形狀直接鏡射
        `test_ps51_compat.TestPs51ScanConfigPinning.test_tree_set_matches_root_infra_ci_pwsh_step`。
        """
        step = self._ci_pwsh_step()
        # R56 round 6 修正（QA B-1）：原字元類 `[A-Za-z0-9_/]` 無法表達含 `.`／`-`
        # 的路徑——實測往 CI 第 2 道插入第 5 棵樹 `.github/scripts` 時，本鎖與姊妹
        # 兩鎖共 11 支全部靜默通過（擴面完全隱形）。另補抽取數量下限：`.ps1` 側已有
        # `len(ps1_trees) == 4` 守門，CI 側原本沒有對等物＝fail-open。
        ci_trees = set(re.findall(_CI_TREE_RE, step))
        self.assertEqual(
            len(ci_trees), 3,
            f"root-infra-ci.yml 第 2 道抽到 {len(ci_trees)} 棵固定樹（預期 3，LATEST 另以 Join-Path 表示）：{sorted(ci_trees)}——抽取數量異動代表 CI 掃描面增刪，請同步四處樹清單站點",
        )
        # R56 round 7 修正（Architect F2 ／ QA ② 交叉發現）：上面的 `len(ci_trees)`
        # 等值斷言只對「_CI_TREE_RE 抽得到的樹」有效，對「抽不到的形態」天生零訊號
        # ——實測 `-Path "docs/scripts"`（引號界定）與 `-Path (Join-Path ".github"
        # "scripts")`（計算式，該 step 第 4 棵樹就是這種寫法、照抄最自然）插入第 5 棵
        # 樹時三支鎖全綠。故補一條**與字元類完全無關**的出現次數斷言：不論路徑長什麼
        # 樣，多一棵樹必紅。（round 6 宣稱「補抽取數量下限堵 fail-open」不精確——
        # QA 實證那條下限被既有 set-equality 涵蓋、是冗餘的，真正生效的只有字元類擴充。）
        self.assertEqual(
            len(re.findall(r"Get-ChildItem\s+-Path", step)), 4,
            "root-infra-ci.yml 第 2 道的 `Get-ChildItem -Path` 出現次數已變動（預期 4＝三棵固定樹＋LATEST 計算式樹）——任何形態的掃描樹增刪都會命中此斷言，請同步四處樹清單站點",
        )
        self.assertIn(
            'Join-Path "AISDLC_SDD" $latestName', step,
            "root-infra-ci.yml 第 2 道未見 LATEST 樹（Join-Path AISDLC_SDD "
            "$latestName）——第 4 棵樹疑似被移除",
        )
        ci_trees.add("AISDLC_SDD/LATEST")
        latest_name = _latest_root().name
        local = {p.rstrip("/").replace(latest_name, "LATEST") for p in _scan_prefixes()}
        self.assertEqual(
            local, ci_trees,
            f"本檔 _scan_prefixes() 的掃描樹 {sorted(local)} 與 root-infra-ci.yml 第 2 "
            f"道的 {sorted(ci_trees)} 不一致——本檔自述鏡射該 step 的樹清單（它是本鎖"
            "在 CI 上的姊妹守門），任一方增刪樹必須同步四處（另兩處：test_ps51_compat"
            ".scan_trees()、windows_smoke_local.ps1 [1/9] $ps1Trees）",
        )


if __name__ == "__main__":
    unittest.main()
