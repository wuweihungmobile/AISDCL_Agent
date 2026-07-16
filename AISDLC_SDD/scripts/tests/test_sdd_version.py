"""sdd_version.py — LATEST 解析 SSOT 的對抗性回歸鎖（R10 拍板案(b)，DEF-101-133）。

WHY（測意圖非僅行為，Rule 9）：
R10 Architect 實測重現 LATEST 解析語意分歧——bash 三重 glob 尾端未錨定會把
`AISDLC_SDD_v0.30.bak`、`AISDLC_SDD_v0.30 - Copy`（檔總管複製品）選成 LATEST，
且所有站點掃磁碟而非 git tracked，未 commit 複製目錄即可讓「閘門綠燈實為測錯樹」。
本測試以對抗性 fixture 鎖死 SSOT 的三條語意支柱：

  1. 錨定：只有完整匹配 ``AISDLC_SDD_v<digits>.<digits>`` 的目錄名才是候選。
  2. tracked 過濾：未 tracked 的合法名目錄不得成為 LATEST（須警告可見）。
  3. 數值排序：(major, minor) 數值比較（v0.9 < v0.10 < v1.0），非字串排序。

任一支柱退化＝bash/pwsh/python 呼叫端全體回到「各說各話」的 R10 前狀態。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts import sdd_version  # isort: skip（首方/三方分組隨 cwd 而異，跳過排序消除歧義）

REPO_ROOT = Path(__file__).resolve().parents[2]
SDD_VERSION_PY = REPO_ROOT / "scripts" / "sdd_version.py"


def _init_repo(root: Path) -> None:
    subprocess.run(
        ["git", "init", "-q", str(root)],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )


def _add_version_dir(root: Path, name: str, *, tracked: bool) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "marker.txt").write_text("x\n", encoding="utf-8")
    if tracked:
        subprocess.run(
            ["git", "-C", str(root), "add", "--", f"{name}/marker.txt"],
            check=True, capture_output=True, text=True, encoding="utf-8",
        )


def test_untracked_pollution_and_copies_are_excluded(tmp_path):
    """核心情境：.bak / ' - Copy' / 未 tracked 合法名 全部不得汙染 LATEST。"""
    _init_repo(tmp_path)
    _add_version_dir(tmp_path, "AISDLC_SDD_v0.30", tracked=True)
    _add_version_dir(tmp_path, "AISDLC_SDD_v0.30.bak", tracked=False)
    _add_version_dir(tmp_path, "AISDLC_SDD_v0.30 - Copy", tracked=False)
    _add_version_dir(tmp_path, "AISDLC_SDD_v0.31", tracked=False)  # 合法名但未 add

    warnings: list[str] = []
    latest = sdd_version.latest_version_name(tmp_path, warn=warnings.append)
    assert latest == "AISDLC_SDD_v0.30"
    # 未 tracked 的「合法名」目錄必須警告可見（Copy-on-Evolve 提醒先 git add）
    assert any("AISDLC_SDD_v0.31" in w for w in warnings), warnings


def test_tracked_but_nonmatching_names_are_excluded(tmp_path):
    """錨定支柱：即使 tracked，.bak 尾綴不匹配錨定 regex 仍被排除。"""
    _init_repo(tmp_path)
    _add_version_dir(tmp_path, "AISDLC_SDD_v0.30", tracked=True)
    _add_version_dir(tmp_path, "AISDLC_SDD_v0.30.bak", tracked=True)
    latest = sdd_version.latest_version_name(tmp_path, warn=lambda _m: None)
    assert latest == "AISDLC_SDD_v0.30"


def test_numeric_version_ordering_v09_v010_v10(tmp_path):
    """數值排序支柱：v0.9 < v0.10 < v1.0（DEF-19-002 / DEF-43-003 邊界同款保護）。"""
    _init_repo(tmp_path)
    _add_version_dir(tmp_path, "AISDLC_SDD_v0.9", tracked=True)
    _add_version_dir(tmp_path, "AISDLC_SDD_v0.10", tracked=True)
    assert sdd_version.latest_version_name(tmp_path, warn=lambda _m: None) == (
        "AISDLC_SDD_v0.10"
    )
    _add_version_dir(tmp_path, "AISDLC_SDD_v1.0", tracked=True)
    assert sdd_version.latest_version_name(tmp_path, warn=lambda _m: None) == (
        "AISDLC_SDD_v1.0"
    )


def test_plain_tracked_file_is_not_a_version_dir(tmp_path):
    """sdd_root 直下 tracked 純檔案（無 `/`）不得被當版本目錄。"""
    _init_repo(tmp_path)
    _add_version_dir(tmp_path, "AISDLC_SDD_v0.30", tracked=True)
    f = tmp_path / "AISDLC_SDD_v9.99"
    f.write_text("我是檔案不是目錄\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "--", "AISDLC_SDD_v9.99"],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    assert sdd_version.latest_version_name(tmp_path, warn=lambda _m: None) == (
        "AISDLC_SDD_v0.30"
    )


def test_git_unavailable_falls_back_to_disk_with_warning(tmp_path, monkeypatch):
    """tarball 場景：git 不可用 → 錨定磁碟掃描 fallback，且警告可見。"""
    _add_version_dir_no_git(tmp_path, "AISDLC_SDD_v0.30")
    _add_version_dir_no_git(tmp_path, "AISDLC_SDD_v0.30.bak")
    monkeypatch.setattr(sdd_version, "tracked_version_dirs", lambda _root: None)
    warnings: list[str] = []
    latest = sdd_version.latest_version_name(tmp_path, warn=warnings.append)
    assert latest == "AISDLC_SDD_v0.30"  # fallback 仍錨定，.bak 不入選
    assert any("fallback" in w for w in warnings), warnings


def _add_version_dir_no_git(root: Path, name: str) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "marker.txt").write_text("x\n", encoding="utf-8")


def test_cli_prints_latest_and_fails_loud_when_none(tmp_path):
    """CLI 契約：stdout 印 LATEST（rc=0）；找不到任何版本目錄 rc=1。"""
    _init_repo(tmp_path)
    _add_version_dir(tmp_path, "AISDLC_SDD_v0.30", tracked=True)
    proc = subprocess.run(
        [sys.executable, str(SDD_VERSION_PY), "--sdd-root", str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "AISDLC_SDD_v0.30"

    empty = tmp_path / "empty"
    empty.mkdir()
    _init_repo(empty)
    proc = subprocess.run(
        [sys.executable, str(SDD_VERSION_PY), "--sdd-root", str(empty)],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert proc.returncode == 1
    assert "找不到任何版本目錄" in proc.stderr


def test_real_repo_resolution_matches_anchored_disk_scan():
    """真 repo 完整性鎖：SSOT 結果＝錨定磁碟掃描最高版（乾淨樹上兩者必相等），
    且結果目錄真實存在——防 resolver 自身迴歸（如 pathspec 打錯回空集合）。"""
    latest = sdd_version.latest_version_name(REPO_ROOT, warn=lambda _m: None)
    assert latest is not None
    disk = sdd_version.disk_version_dirs(REPO_ROOT)
    assert latest == max(disk, key=sdd_version._version_key)
    assert (REPO_ROOT / latest).is_dir()
