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

掃描範圍鏡射 root-infra-ci.yml「pwsh 語法解析 + UTF-8 BOM 守門」step 的樹清單：
根 tools/、AutoClaude/tools/、AISDLC_SDD/scripts/（皆遞迴）＋ AISDLC_SDD
LATEST 整版目錄（LATEST 以 scripts/sdd_version.py SSOT 解析，解析失敗
fail-loud 不得縮面；凍結版 v0.01~v0.2X 排除）。列舉以 `git ls-files '*.ps1'`
過濾樹（排除未追蹤垃圾；CI 端 Get-ChildItem 掃磁碟，checkout 下兩者等價）。
掃描檔數下限釘選＝2026-07-20 實測 19 支打八折（15），防掃描面靜默縮小；
樹前綴清單另由 TestScanConfigPinning 釘選。
"""
from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
