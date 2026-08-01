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
from pathlib import Path

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
        input="x", capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=True, timeout=30,
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
           "dir /f.txt", "trailing./f.txt", "COM0.txt", "lpt0.log"]
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
    # S7 修復：check_ntfs_paths.py 改 import 同目錄的 _stdio_utf8.py（Windows 非
    # UTF-8 終端防崩潰保護）；sandbox 需比照真實部署一併複製此同目錄依賴檔，
    # 否則 sandbox 內 import 會找不到模組。
    shutil.copy(
        os.path.join(os.path.dirname(_ntfs_tool_path()), "_stdio_utf8.py"),
        os.path.join(tools_dir, "_stdio_utf8.py"),
    )
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

# ── 防線 7：_tracked_files 非法 UTF-8 位元組韌性鎖（DEF-101-260）───────────

def test_tracked_files_passes_errors_replace_and_survives_invalid_utf8(monkeypatch):
    """DEF-101-260 回歸鎖：`_tracked_files()` 的 subprocess.run 呼叫必須帶
    `errors="replace"`（與全庫 `text=True, encoding="utf-8"` 慣例一致）。修復前
    只設 `encoding="utf-8"`，一旦 tracked 路徑含非法 UTF-8 位元組序列，
    `.stdout` 解碼會拋出未捕捉的 UnicodeDecodeError，讓這支「NTFS 敵意檔名
    防護」CI 腳本自己先崩潰，而非印出乾淨的違規清單。

    以 mock 模擬 subprocess.run：side_effect 依實際傳入的 encoding/errors kwargs
    對含非法位元組的假輸出做解碼（重現真實 subprocess text-mode 行為），藉此
    證明——若呼叫端漏了 errors="replace"，這裡會先以 UnicodeDecodeError 炸掉；
    修復後應安全通過並確實把 kwargs 傳對。
    """
    mod = _load_ntfs_module()
    raw_bytes = b"good.txt\x00" + b"\xff\xfebad.txt\x00"
    captured: dict = {}

    def _fake_run(*args, **kwargs):
        captured.update(kwargs)
        encoding = kwargs.get("encoding", "utf-8")
        errors = kwargs.get("errors", "strict")  # subprocess 預設即 strict
        decoded = raw_bytes.decode(encoding, errors=errors)
        return subprocess.CompletedProcess(args[0] if args else kwargs.get("args"), 0,
                                            stdout=decoded, stderr="")

    monkeypatch.setattr(mod.subprocess, "run", _fake_run)
    files = mod._tracked_files()  # 修復前：errors 缺省→strict→此處拋 UnicodeDecodeError
    assert captured.get("errors") == "replace", (
        '_tracked_files() 的 subprocess.run 必須傳 errors="replace"（與全庫慣例一致）'
    )
    assert "good.txt" in files


def test_no_existing_tracked_path_exceeds_fail_threshold():
    """閘門本應攔下（>fail）卻已在庫＝自我矛盾。warn 帶（181~200）依政策可入庫，
    不在此斷言（防「合法 warn 路徑入庫 → 無辜後續 commit 在此爆紅」的嫁禍陷阱）。
    上線日實況：全量最長 142，連 warn 帶亦零存量。"""
    mod = _load_ntfs_module()
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
        cwd=_monorepo_root(), capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=True, timeout=60,
    ).stdout
    offenders = [p for p in out.split("\0") if p and len(p) > mod._LEN_FAIL]
    assert not offenders, f"存量 tracked 路徑超過 fail 門檻 {mod._LEN_FAIL}：{offenders}"


# ── R68 防線 8：上標保留裝置名三站點 parity 鎖 ─────────────────────────────

# Microsoft《Naming Files, Paths, and Namespaces》的保留名清單把上標變體與 ASCII
# 數字版**並列**（成因：Windows 裝置名解析把上標數字視同數字；`unicodedata.normalize
# ("NFKC","COM¹") == "COM1"` 可佐證兩者在相容性分解下同值）。四處實作共用的
# `COM[0-9]|LPT[0-9]` 是 ASCII-only ⇒ 修復前實測 'COM¹'／'com².log'／'LPT¹' 在四處
# **全部原樣輸出、零攔截**，而既有四方等值鎖比的是「四處彼此一致」，四處同時缺同一組
# 字元即恆綠——本鎖補的正是這個結構性盲區（樣本表從未含上標）。
#
# 🔴 證據等級誠實揭露：**官方文件 ＋ 靜態分析／本機 NFKC 實測**，**非 Windows 真機
# 實測**（R68 無 Windows 真機，未跑 `core.protectNTFS` update-index／clone 與 Win32
# CreateFile 對照——CONIN$ 納入、CLOCK$ 排除當初都是真機實測後才定案）。取捨刻意選
# 「擋」：誤擋的代價是一個沒人會用的檔名多一個 `_` 前綴／進不了庫；漏擋的代價是每一台
# Windows clone 的 checkout 整體失敗（rc=128、工作樹全空，CONIN$ 已實證此形態）。
# 未來若在 Windows 真機實測到 git 與 Win32 皆 ACCEPT，四處一併移除並比照 CLOCK$ 在
# 各處註記「已實測不納入」，本鎖同步改為 benign 斷言。
SUPERSCRIPT_DEVICE_SEGMENTS = [
    "COM¹.txt", "COM².log", "COM³.yaml", "LPT¹.txt", "LPT².log", "LPT³.md",
    "com¹.tar.gz",   # 大小寫不敏感 ＋ 多重副檔名
    "LPT³ .txt",     # 疊加 R57 的尾隨空白形態
]
# 修復不得擴大攔截面（雙向鎖的另一半）：這些**不是**保留名，四處皆須放行
SUPERSCRIPT_BENIGN_SEGMENTS = ["COM10.txt", "COMx.txt", "LPT.txt", "CONSOLE¹.md", "¹.txt"]


def test_superscript_device_names_flagged_by_ci_scanner():
    """站點 1／3：`tools/check_ntfs_paths.py::_ntfs_seg_bad`。"""
    mod = _load_ntfs_module()
    for seg in SUPERSCRIPT_DEVICE_SEGMENTS:
        assert mod._ntfs_seg_bad(seg) is not None, f"CI 掃描器未攔下上標裝置名：{seg}"
    for seg in SUPERSCRIPT_BENIGN_SEGMENTS:
        assert mod._ntfs_seg_bad(seg) is None, f"CI 掃描器誤攔良性片段：{seg}"


def test_superscript_device_names_prefixed_by_component_sanitizer():
    """站點 2／3：`AISDLC_SDD/scripts/component_sanitizer.py::sanitize_component`
    （生成器側——它產生的檔名會被提交，必須先於 validator 就不生出裝置名）。"""
    from component_sanitizer import sanitize_component
    for seg in SUPERSCRIPT_DEVICE_SEGMENTS:
        out = sanitize_component(seg)
        assert out.startswith("_"), f"sanitizer 未對上標裝置名加前綴：{seg} → {out}"
    for seg in SUPERSCRIPT_BENIGN_SEGMENTS:
        assert not sanitize_component(seg).startswith("_"), f"sanitizer 誤加前綴：{seg}"


@pytestmark_bash
def test_superscript_device_names_flagged_by_pre_commit_hook(tmp_path):
    """站點 3／3：根層 `tools/git-hooks/pre-commit::_ntfs_seg_bad`（bash 實跑）。

    WHY 必須實跑而非靜態比對字面值：bash 3.2 的 glob bracket 在 C locale 下是
    **逐位元組**比對，`COM[¹²³]` 這種寫法（UTF-8 共 6 bytes）會退化成單位元組集合而
    永不匹配 3 bytes 的 `COM¹`——靜態看得到字樣、實跑卻不攔，正是本鎖要防的假綠。
    """
    proc = _run_hook_with_staged_paths(tmp_path, ["COM¹.txt"])
    assert proc.returncode != 0, f"hook 未攔下上標裝置名\nstdout={proc.stdout}\nstderr={proc.stderr}"
    assert "保留裝置名" in proc.stderr


@pytestmark_bash
def test_superscript_fix_does_not_block_benign_paths_in_hook(tmp_path):
    """hook 側的偽陽性鎖：良性片段（COM10 等）不得因本次修復被擋。"""
    proc = _run_hook_with_staged_paths(tmp_path, SUPERSCRIPT_BENIGN_SEGMENTS)
    assert "保留裝置名" not in proc.stderr, f"hook 誤判良性片段\nstderr={proc.stderr}"


# ── R68 防線 9：sanitizer 產物必須通過自家 NFC 閘 ──────────────────────────

def test_component_sanitizer_output_passes_ci_nfc_gate():
    """生成器 ↔ validator 判準對齊鎖。

    WHY（Rule 9 — 鎖住意圖）：`sanitize_component()` 產生的檔名（FSM-STATE-*.yaml／
    SPEC-PATCH-*.md 等，實查 69 筆已入庫）會被提交，而同 repo 的
    `check_ntfs_paths.py::_non_nfc_reason()` 對 index 內非 NFC 路徑 **fail-closed**。
    修復前 sanitizer 零 Unicode 正規化 ⇒ NFD 輸入原樣輸出 ⇒ **自家生成器產出的檔名
    被自家閘門擋下**。macOS 側因 `core.precomposeunicode` 預設 true（`git add` 會
    precompose，index 恆 NFC）而不顯形，故此缺口顯形於 **Linux/CI runner 側**，
    不是 macOS 側——這點與原始回報相反，以實跑 git 端到端對撞確認後據實記載。
    """
    import unicodedata

    from component_sanitizer import sanitize_component
    mod = _load_ntfs_module()
    nfd_inputs = [
        unicodedata.normalize("NFD", s) for s in ("AC-Café-001", "état-1", "한글-track")
    ]
    for nfd in nfd_inputs:
        assert not unicodedata.is_normalized("NFC", nfd), f"樣本非 NFD，本鎖恆綠：{nfd!r}"
        out = sanitize_component(nfd)
        assert unicodedata.is_normalized("NFC", out), f"sanitizer 輸出仍為 NFD：{out!r}"
        assert mod._non_nfc_reason(f"build/reports/fsm/FSM-STATE-{out}.yaml") is None, (
            "sanitizer 產物過不了自家 CI 的 NFC 閘"
        )
    # 對純 ASCII／CJK 零行為變更（否則本修復會改動所有既有輸出）
    for benign in ("my-project", "AC-001", "中文專案", "a b/c:d"):
        assert sanitize_component(benign) == sanitize_component(
            unicodedata.normalize("NFC", benign)
        )


# ── R68 防線 10：三站點長度政策對照登記表 ─────────────────────────────────

def test_length_policy_three_sites_registry():
    """把「三站點長度政策各自的域與理由」機械釘住（R68 idx-46）。

    WHY 這是鎖而不是文件：檔名長度政策在三處有三種數字（80／無上限／200 fail +
    180 warn），已被連續數輪掃描重新回報為「同一政策四份真相」。實查後的結論是
    **刻意不相等**（三者治理不同域），但這個結論此前只存在於審查紀錄裡，沒有任何
    機械物承載 ⇒ 下一輪必然再被當成缺陷重新發現一次。本鎖同時看守兩件事：
      ① 三個數字／「不截斷」設計未被單方面改動（改了就得回來改本鎖與三處註解）；
      ② 三處都留有 `三站點長度政策` 對照註記（註記被刪＝理由消失＝重新發現的前置）。

    誠實劃界：本鎖**不**主張三者數字正確，也**不**覆蓋已知未修的跨平台窄帶——單一
    component ~200–254 字元在 mac/Linux 合法、Windows 未開 longPaths 時總路徑可能破
    260（≥255 為兩平台共同 ENAMETOOLONG，非跨平台落差；本輪 APFS 實測 200/250 OK、
    255/256/300 FAIL errno 63）。該窄帶須先有 Windows 真機實證再設鎖，否則等於再加
    一道從未紅過的鎖。
    """
    import component_sanitizer as cs
    mod = _load_ntfs_module()
    logger_src = os.path.join(
        _monorepo_root(), "AutoClaude", "autoclaude", "utils", "logger.py"
    )

    assert cs._MAX_COMPONENT_LEN == 80, "站點①（FSM state 單一 component）政策已變動"
    assert (mod._LEN_FAIL, mod._LEN_WARN) == (200, 180), "站點③（tracked 整條路徑）政策已變動"

    # 站點②：logger 刻意**不截斷**——以行為斷言，避免只鎖註解而鎖不到實作
    # 🔴 寫成 `Path(__file__).resolve().parents[N] / ...` 而非 `os.path.join(_monorepo_root(), …)`：
    # 後者把基底藏在函式呼叫裡，`test_ci_paths_cover_root_consumers._eval_path_expr()` 無法靜態
    # 解析 ⇒ 該路徑下的根層消費檔會對「CI paths 白名單涵蓋率」那道鎖隱形（R67 盲區 E 同構假綠）。
    # 對齊本 repo `sys.path.insert(0, str(Path(...).parents[N]))` 既有慣例。
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "AutoClaude"))
    from autoclaude.utils.logger import _sanitize_log_filename
    long_name = "a" * 300 + ".log"
    assert _sanitize_log_filename(long_name) == long_name, (
        "站點②（runtime log 檔名）原本刻意不截斷（超長交由 OSError fallback 承接）；"
        "若確要改為截斷，必須同步更新三處註解與本鎖"
    )

    marker = "三站點長度政策"
    for path in (cs.__file__, _ntfs_tool_path(), logger_src):
        with open(path, encoding="utf-8") as fh:
            assert marker in fh.read(), (
                f"{path} 缺少「{marker}」對照註記——理由一旦消失，下一輪掃描會把"
                "「三處三種數字」當成新缺陷重新回報（本鎖存在的唯一理由）"
            )
