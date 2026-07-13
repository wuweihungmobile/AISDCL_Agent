"""MAX_PATH 保守長度閘 + NTFS 檔名閘 contract — DEF-101-039 回歸鎖（hook + CI 兩側）.

為何重要（Rule 9 / Rule 12 fail-loud）：Windows 未開 `core.longpaths` 時絕對路徑
上限 MAX_PATH=260 UTF-16 單位（含結尾 NUL，可用 259）——macOS(APFS) 上合法的超長
路徑一旦入庫，Windows clone/checkout 直接炸掉（`Filename too long`），屬「入庫即
全平台受害」的正確性缺陷。四方複審第四輪 Architect 終裁 (c) 裁定：repo 相對路徑
>200 字元 fail（預留 clone 前綴 59 字元＋NUL）、>180 字元 warn。第五輪四方複審
（QA mutation M1/M5/M6 假綠實證＋Architect/SD 邊界精度）補強為六道防線。

六道防線：
1. CI 側純函式邊界鎖：`_length_level` 的 180/181/200/201 四點＋code point 語意。
2. hook 側行為鎖：同四點實跑釘死（180 靜默／181 warn／200 warn／201 fail）——
   門檻常數在 bash 與 Python 雙處硬編碼、無單一真相源，本鎖是唯一同步機制。
3. 存量一致性鎖：全量 tracked 無 >fail 門檻路徑（閘門本應攔下卻在庫＝自我矛盾）。
   181~200 warn 帶依政策**可入庫**（hook/CI 皆放行），故不以 180 斷言——否則
   合法 warn 路徑入庫後會令無辜的後續 commit 在此爆紅（第五輪 Architect/QA 裁定）。
4. CI main() 接線鎖：實跑 `check_ntfs_paths.py`（sandbox 副本）——201→exit 1、
   190→exit 0＋⚠ stderr；防線 1 鎖不住 main() 集成刪除或 fail 降級（QA M1/M6）。
   複審擴充：seg_bad 接線＋大小寫碰撞段同鎖（QA 複審 M10/M11 探針存活後補殺）。
5. `_ntfs_seg_bad` 跨語言 parity 鎖：Python 表驅動＋hook 實跑（保留名/禁字）——
   第 1~3 項檢查此前零入庫回歸測試（第五輪 Architect F-6）。
6. CJK locale 無關鎖：hook 以「刪 UTF-8 連續位元組」計 code point，LC_ALL=C
   （GUI git client 常態）下 CJK 路徑不再依位元組誤擋（第五輪 SD/QA 實證修復）。

（以 `git update-index --cacheinfo` 暫存路徑，不落地建檔——避免在未開 longpaths
的 Windows 上測試自身先炸。bash 解析經 scripts/bash_probe 排除 WSL 佔位 bash。）
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys

import pytest

from scripts import bash_probe  # isort: skip（首方/三方分組隨 cwd 而異，跳過排序消除歧義）

_BASH = bash_probe.usable_bash()


def _monorepo_root() -> str:
    # scripts/tests/ → scripts/ → AISDLC_SDD/ → monorepo 根
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )


def _ntfs_tool_path() -> str:
    return os.path.join(_monorepo_root(), "tools", "check_ntfs_paths.py")


def _load_ntfs_module():
    spec = importlib.util.spec_from_file_location("check_ntfs_paths", _ntfs_tool_path())
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── 防線 1：CI 側純函式分級邊界 ─────────────────────────────────────────────

def test_length_level_boundaries():
    mod = _load_ntfs_module()
    assert mod._length_level("a" * 180) is None, "180 字元＝合規上限，不該有任何告警"
    assert mod._length_level("a" * 181) == "warn", "181 字元須 warn（>180）"
    assert mod._length_level("a" * 200) == "warn", "200 字元仍是 warn（fail 門檻是 >200）"
    assert mod._length_level("a" * 201) == "fail", "201 字元須 fail（>200）"


def test_length_level_counts_code_points_not_bytes():
    """CJK 路徑語意鎖：長度＝code point 數（≈UTF-16 單位，MAX_PATH 的真實單位），
    絕不可退化為 UTF-8 位元組數——「中」×70（210 bytes / 70 code points）必須合規。"""
    mod = _load_ntfs_module()
    assert mod._length_level("中" * 70) is None
    assert mod._length_level("中" * 181) == "warn"
    assert mod._length_level("中" * 201) == "fail"


# ── sandbox 工具（防線 2/4/5/6 共用）────────────────────────────────────────

pytestmark_bash = pytest.mark.skipif(
    _BASH is None or shutil.which("git") is None,
    reason="hook 行為鎖需可用 bash（非 WSL 佔位）+ git",
)


def _stage_paths(repo: str, rel_paths: list[str]) -> None:
    """在 repo 以 --cacheinfo 暫存 rel_paths（不落地建檔）。

    關閉 core.protectNTFS/protectHFS：這兩項 Git 內建保護預設值因平台而異
    （Windows 上 protectNTFS 預設 true，其餘平台預設 false），會在
    update-index --cacheinfo 階段就搶先擋下保留裝置名（如 CON.txt），
    使本檔測試的「hook 自身邏輯是否正確擋下」永遠測不到——關閉後才輪得到
    hook-under-test 自己判斷。
    """
    subprocess.run(["git", "-C", repo, "init", "-q"], check=True, timeout=30)
    subprocess.run(
        ["git", "-C", repo, "config", "core.protectNTFS", "false"], check=True, timeout=30,
    )
    subprocess.run(
        ["git", "-C", repo, "config", "core.protectHFS", "false"], check=True, timeout=30,
    )
    blob = subprocess.run(
        ["git", "-C", repo, "hash-object", "-w", "--stdin"],
        input="x", capture_output=True, text=True, check=True, timeout=30,
    ).stdout.strip()
    for p in rel_paths:
        subprocess.run(
            ["git", "-C", repo, "update-index", "--add", "--cacheinfo",
             f"100644,{blob},{p}"],
            check=True, timeout=30,
        )


def _run_hook_with_staged_paths(
    tmp_path, rel_paths: list[str], extra_env: dict | None = None
) -> subprocess.CompletedProcess:
    """隔離 repo 暫存 rel_paths 後實跑根層 dispatcher pre-commit。"""
    repo = str(tmp_path)
    _stage_paths(repo, rel_paths)
    env = {**os.environ, "AUTOCLAUDE_SKIP_HOOKS": "0", **(extra_env or {})}
    hook = os.path.join(_monorepo_root(), "tools", "git-hooks", "pre-commit")
    # Windows Git Bash 吃正斜線絕對路徑（C:/...），反斜線會被當跳脫（既有 contract 慣例）
    return subprocess.run(
        [_BASH, hook.replace("\\", "/")],
        cwd=repo, capture_output=True, text=True, encoding="utf-8",
        errors="replace", env=env, timeout=60,
    )


# ── 防線 2：hook 側行為鎖（180/181/200/201 四點釘死）───────────────────────

@pytestmark_bash
def test_hook_blocks_over_200(tmp_path):
    long_name = "a" * 197 + ".txt"  # 201 字元；單段 <255 bytes（APFS/NTFS 段上限內）
    proc = _run_hook_with_staged_paths(tmp_path, [long_name])
    assert proc.returncode != 0, f"201 字元路徑必須被擋下\nstderr={proc.stderr}"
    assert "路徑過長" in proc.stderr


@pytestmark_bash
def test_hook_warns_at_exact_200(tmp_path):
    """200＝fail 門檻的合規側：只 warn 不擋——釘死 -gt 200 不被誤改為 -ge 200。"""
    proc = _run_hook_with_staged_paths(tmp_path, ["a" * 196 + ".txt"])  # 恰 200
    assert proc.returncode == 0, f"200 字元只 warn 不可擋\nstderr={proc.stderr}"
    assert "路徑偏長" in proc.stderr and "路徑過長" not in proc.stderr


@pytestmark_bash
def test_hook_warns_at_exact_181(tmp_path):
    """181＝warn 門檻的告警側：釘死 -gt 180 不向上漂移（QA mutation M5 殺手）。"""
    proc = _run_hook_with_staged_paths(tmp_path, ["a" * 177 + ".txt"])  # 恰 181
    assert proc.returncode == 0, f"181 字元只 warn 不可擋\nstderr={proc.stderr}"
    assert "路徑偏長" in proc.stderr


@pytestmark_bash
def test_hook_silent_at_exact_180(tmp_path):
    """180＝合規上限：零告警——釘死 warn 門檻不向下漂移。"""
    proc = _run_hook_with_staged_paths(tmp_path, ["a" * 176 + ".txt"])  # 恰 180
    assert proc.returncode == 0, f"180 字元必須無擋\nstderr={proc.stderr}"
    assert "路徑偏長" not in proc.stderr and "路徑過長" not in proc.stderr


@pytestmark_bash
def test_hook_silent_on_short_path(tmp_path):
    proc = _run_hook_with_staged_paths(tmp_path, ["ok.txt"])
    assert proc.returncode == 0, f"短路徑必須無擋\nstderr={proc.stderr}"
    assert "路徑過長" not in proc.stderr and "路徑偏長" not in proc.stderr


# ── 防線 6：CJK locale 無關鎖 ───────────────────────────────────────────────

@pytestmark_bash
def test_hook_cjk_counts_code_points_even_in_c_locale(tmp_path):
    """「中」×67＝67 cp／201 bytes：C locale（GUI git client 常態）下必須放行且靜默；
    「中」×181＝181 cp：warn 且訊息計數為 181 非 543——證明 hook 計數 locale 無關、
    與 CI 版 len() 同語意（修復前 ${#f} 在 C locale 對 ×67 誤報「路徑過長 201」）。"""
    proc = _run_hook_with_staged_paths(
        tmp_path, ["中" * 67, "中" * 181],
        extra_env={"LC_ALL": "C", "LANG": "C"},
    )
    assert proc.returncode == 0, f"CJK 67/181 cp 皆不可擋\nstderr={proc.stderr}"
    assert "路徑過長" not in proc.stderr
    assert "路徑偏長（181 > 180" in proc.stderr, (
        f"181 cp 應 warn 且以 cp 計數\nstderr={proc.stderr}"
    )


# ── 防線 5：_ntfs_seg_bad 跨語言 parity 鎖 ─────────────────────────────────

def test_seg_bad_python_table():
    """Python 版第 1~2 項表驅動：保留裝置名／禁字／尾空白句點／正常路徑。"""
    mod = _load_ntfs_module()
    bad = ["CON.txt", "docs/aux.md", "nul.tar.gz", "a<b.txt", "back\\slash.txt",
           "dir /f.txt", "trailing./f.txt"]
    good = ["normal/ok.txt", "COM10.txt", "CONtext.txt", "中文/路徑.md"]
    for p in bad:
        assert mod._ntfs_seg_bad(p) is not None, f"應判違規：{p}"
    for p in good:
        assert mod._ntfs_seg_bad(p) is None, f"不應誤判：{p}"


@pytestmark_bash
def test_hook_seg_bad_reserved_and_forbidden(tmp_path):
    """hook 版第 1~2 項實跑：保留裝置名與禁字必須 fail-loud（此前零入庫回歸鎖）。"""
    proc = _run_hook_with_staged_paths(tmp_path, ["CON.txt", "bad<name.txt"])
    assert proc.returncode != 0, f"保留名/禁字必須擋下\nstderr={proc.stderr}"
    assert "保留裝置名" in proc.stderr and "不允許字元" in proc.stderr


# ── 防線 4：CI main() 接線鎖（QA mutation M1/M6 殺手）──────────────────────

def _run_ci_tool_in_sandbox(tmp_path, rel_paths: list[str]) -> subprocess.CompletedProcess:
    """複製工具至 sandbox/tools/（_REPO_ROOT=parents[1] 自然錨定 sandbox），實跑 main()。"""
    repo = str(tmp_path)
    tools_dir = os.path.join(repo, "tools")
    os.makedirs(tools_dir, exist_ok=True)
    shutil.copy(_ntfs_tool_path(), os.path.join(tools_dir, "check_ntfs_paths.py"))
    _stage_paths(repo, rel_paths)
    env = {**os.environ, "PYTHONUTF8": "1"}
    return subprocess.run(
        [sys.executable, os.path.join(tools_dir, "check_ntfs_paths.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, timeout=60,
    )


@pytest.mark.skipif(shutil.which("git") is None, reason="需 git（cacheinfo 暫存）")
def test_ci_main_fails_on_over_200(tmp_path):
    proc = _run_ci_tool_in_sandbox(tmp_path, ["a" * 197 + ".txt"])  # 201
    assert proc.returncode == 1, f"201 字元須 exit 1\nstdout={proc.stdout}\nstderr={proc.stderr}"
    assert "路徑過長" in proc.stderr


@pytest.mark.skipif(shutil.which("git") is None, reason="需 git（cacheinfo 暫存）")
def test_ci_main_warn_does_not_affect_exit_code(tmp_path):
    proc = _run_ci_tool_in_sandbox(tmp_path, ["a" * 186 + ".txt"])  # 190＝warn 帶
    assert proc.returncode == 0, f"warn 帶不可影響退出碼\nstderr={proc.stderr}"
    assert "路徑偏長" in proc.stderr, "warn 必須可見（stderr）"
    assert "✅" in proc.stdout


@pytest.mark.skipif(shutil.which("git") is None, reason="需 git（cacheinfo 暫存）")
def test_ci_main_seg_bad_and_case_collision_wiring(tmp_path):
    """CI main() 的 seg_bad 接線與大小寫碰撞段鎖（QA 複審 M10/M11 殺手）：
    防線 5 只鎖純函式、防線 4 原僅 stage 長度路徑——main() 刪 seg_bad 接線或
    刪碰撞整段仍假綠。staged 保留名＋大小寫碰撞對必須 exit 1 且兩種訊息俱在。"""
    proc = _run_ci_tool_in_sandbox(tmp_path, ["CON.txt", "Readme.md", "readme.md"])
    assert proc.returncode == 1, f"保留名＋碰撞須 exit 1\nstderr={proc.stderr}"
    assert "NTFS 不相容檔名" in proc.stderr, f"seg_bad 接線失守\nstderr={proc.stderr}"
    assert "大小寫碰撞" in proc.stderr, f"碰撞段失守\nstderr={proc.stderr}"


# ── 防線 3：存量一致性鎖 ────────────────────────────────────────────────────

def test_no_existing_tracked_path_exceeds_fail_threshold():
    """閘門本應攔下（>fail）卻已在庫＝自我矛盾。warn 帶（181~200）依政策可入庫，
    不在此斷言（防「合法 warn 路徑入庫 → 無辜後續 commit 在此爆紅」的嫁禍陷阱）。
    上線日實況：全量最長 142，連 warn 帶亦零存量。"""
    mod = _load_ntfs_module()
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
        cwd=_monorepo_root(), capture_output=True, text=True,
        encoding="utf-8", check=True, timeout=60,
    ).stdout
    offenders = [p for p in out.split("\0") if p and len(p) > mod._LEN_FAIL]
    assert not offenders, f"存量 tracked 路徑超過 fail 門檻 {mod._LEN_FAIL}：{offenders}"
