"""tests/tools/test_run_local_nightly_sh_static.py — mac 側 nightly .sh 靜態檢查
（R31 Architect 架構深度評估發現：測試嚴謹度不對稱的補強）。

背景：Windows 側 `tools/run_local_nightly.ps1` 有 25 個結構化 pytest case
（`test_run_local_nightly_static.py`），逐項鎖心跳／保留期輪替／trigger 標註／
去重鎖／exit 語意；mac 側 `AutoClaude/tools/run_local_nightly.sh` 此前**沒有對等
的 pytest 靜態測試**，同款行為只在 `tools/macos_smoke_local.sh` [7/7] 步驟以粗
粒度 grep 驗證 5 個錨點字串（打包在 shell smoke 腳本裡當一個 pass/fail 項），
沒有負向測試。這降低了 mac 側 nightly 契約走樣（尤其近幾輪才新增的 mkdir atomic
lock／trigger 歸因欄位）的偵測靈敏度，與本 repo「驗證鏡子自身要被驗證」的紀律
精神（`docs/06_quality/Nightly_Forensic_Discipline.md`）不符。

本檔不取代 `macos_smoke_local.sh` [7/7]（該步驟仍作為端到端 smoke 補充保留），
而是補上 pytest 靜態層級的結構化正向 + 負向 case，涵蓋現有 5 個 smoke 錨點
（exec >>／nightly_mac_2*.log／-mtime +14／--force／RunAtLoad 補跑去重文案）之外
的 mkdir atomic lock、trigger= 四態枚舉、終端 exit 語意、心跳三站點契約格式。
"""
from __future__ import annotations

import ast
import fnmatch
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path, PureWindowsPath

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_NIGHTLY_SH = _REPO_ROOT / "tools" / "run_local_nightly.sh"
# monorepo 根（AutoClaude/ 的上一層）——跨檔字面一致性鎖要讀根層安裝器。
_MONOREPO_ROOT = _REPO_ROOT.parent
_MAC_INSTALLER = _MONOREPO_ROOT / "tools" / "install_mac_nightly.sh"

# 🔴 R82 包 A2（CARRIER-01）：Git Bash 解析走 monorepo 根層既有 SSOT，不在本檔重寫第二份。
# `test_bash_probe_spec_contract.py::TestNoBareBashInvocationInToolsTests` 的失敗訊息逐字
# 指定「AutoClaude 樹用 integration_gate_core.find_git_bash()」，本行即照做。
if str(_MONOREPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_MONOREPO_ROOT / "tools"))
from integration_gate_core import find_git_bash  # noqa: E402


@pytest.fixture(scope="module")
def sh_content() -> str:
    assert _NIGHTLY_SH.exists(), f"nightly sh missing: {_NIGHTLY_SH}"
    return _NIGHTLY_SH.read_text(encoding="utf-8")


def _code_only(text: str) -> str:
    """剝除整行註解（`^\\s*#` 起頭），比照 macos_smoke_local.sh [7/7] 既有手法——
    防「功能碼被改壞、但同名舊註解字樣仍在」造成靜態比對假陽性。"""
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("#")
    )


# --- 正向 case：現有 smoke 5 錨點的 pytest 對等版（更精確——剝註解後比對） -----

def test_run_id_log_exec_redirect_present(sh_content: str) -> None:
    """RunId log 必須以 `exec >>`（非互動）將輸出改道獨立日誌檔。"""
    code = _code_only(sh_content)
    assert "exec >>" in code, "缺 RunId log exec 改道（非互動路徑）"
    assert 'exec > >(tee -a "${RUN_LOG}")' in code, "缺互動終端機 tee 雙寫路徑"


def test_dated_log_retention_pattern_and_window(sh_content: str) -> None:
    """dated log 保留期輪替：pattern 必須是 `nightly_mac_2*.log`，保留 14 天。"""
    code = _code_only(sh_content)
    assert "nightly_mac_2*.log" in code, "缺 dated log pattern"
    assert "-mtime +14" in code, "保留期必須為 14 天"


def _rotation_glob(code: str) -> str | None:
    """抽出 dated log 輪替 `find -name '<pattern>'` 的 glob 字面值；找不到回傳 None。"""
    m = re.search(r"-name\s+'([^']+)'", code)
    return m.group(1) if m else None


def _rotation_pattern_excludes_heartbeat(code: str) -> bool:
    """輪替 pattern 是否真的不會（以 shell glob 語意，非純字串子字串）誤配到
    `nightly_mac_latest.log` 心跳指標檔，且輪替行確有 `-delete`。用 `fnmatch`
    做真正的 glob 比對，而非只查字面子字串——`nightly_mac_*.log` 這種寬鬆版本
    字面上不含 "nightly_mac_latest.log"，但 glob 語意上會命中它，純子字串比對
    抓不到這個退化，必須用 fnmatch 才驗證得出來。"""
    pattern = _rotation_glob(code)
    if pattern is None:
        return False
    line = next((line for line in code.splitlines() if pattern in line), "")
    if "-delete" not in line:
        return False
    return not fnmatch.fnmatch("nightly_mac_latest.log", pattern)


def test_retention_rotation_excludes_heartbeat_file(sh_content: str) -> None:
    """輪替必須實際執行刪除（非只是掃描），且絕不誤刪 nightly_mac_latest.log 心跳檔
    ——以 `fnmatch` 對 glob pattern 本身做語意比對，而非只查字面子字串。"""
    code = _code_only(sh_content)
    assert _rotation_glob(code) is not None, "找不到輪替 -name pattern"
    assert _rotation_pattern_excludes_heartbeat(code), (
        "輪替 pattern 必須實際執行 -delete，且以 glob 語意（非純字面）確認不會"
        "誤配到 nightly_mac_latest.log 心跳指標檔"
    )


def test_force_flag_bypasses_dedup(sh_content: str) -> None:
    """`--force` 必須能繞過當日去重（手動重跑逃生門）。"""
    code = _code_only(sh_content)
    assert '"${1:-}" != "--force"' in code or '"${1:-}" = "--force"' in code, (
        "缺 --force 旗標判斷（手動重跑必須能繞過當日去重）"
    )
    assert "RunAtLoad 補跑去重" in sh_content, "缺 RunAtLoad 補跑去重說明文案（取證可讀性）"


# --- 補強 case：mkdir atomic lock、trigger 枚舉、終端 exit 語意（此前無鏡子） ---

def test_mkdir_atomic_lock_present(sh_content: str) -> None:
    """並行防護：必須用 `mkdir` 原子鎖（非 flock/shlock——macOS 無 flock，shlock
    非所有版本保證存在），且鎖不到時必須 exit 0（跳過本輪，不阻斷排程）。"""
    code = _code_only(sh_content)
    assert "NIGHTLY_LOCK_DIR=" in code, "缺 mkdir atomic lock 目錄變數定義"
    assert 'mkdir "${NIGHTLY_LOCK_DIR}"' in code, "缺 mkdir 原子鎖建立呼叫"
    lock_guard_idx = code.find("_nightly_lock_acquire")
    assert lock_guard_idx > 0, "缺去重鎖 acquire 函式"
    assert "trap _nightly_lock_release EXIT" in code, (
        "必須在 EXIT trap 釋放鎖——否則行程正常結束後鎖永久卡死下一輪"
    )


def _has_stale_lock_liveness_check(code: str) -> bool:
    """陳舊鎖清除是否用 `kill -0 <pid>` 存活性檢查（而非固定逾時秒數判斷）。"""
    return bool(re.search(r"kill\s+-0\s+", code))


def test_stale_lock_uses_liveness_check_not_fixed_timeout(sh_content: str) -> None:
    """陳舊鎖清除必須依「鎖檔內 PID 是否仍存活」（kill -0）判斷，而非固定逾時秒數
    ——整套 stage gate 執行時間會變動，固定逾時容易誤殺仍在跑的合法行程（同 dev_start.py
    `_acquire_bootstrap_lock()` 慣例）。"""
    code = _code_only(sh_content)
    assert _has_stale_lock_liveness_check(code), (
        "陳舊鎖清除必須用 `kill -0 <pid>` 存活性檢查，不可用固定逾時秒數判斷"
    )
    assert re.search(r"echo\s+\"\$\$\"\s*>\s*", code), (
        "取得鎖後必須把自身 PID（$$）寫入鎖檔，供陳舊鎖判斷讀取"
    )


def test_trigger_source_four_state_enum(sh_content: str) -> None:
    """trigger 歸因必須涵蓋四態：manual-force／launchd／manual-interactive／
    non-interactive-unknown（BEGIN log 需可歸因觸發來源，防「同日兩輪 PASS」
    無法判讀是合理手動重跑還是去重漏洞）。"""
    code = _code_only(sh_content)
    for expected in (
        "manual-force",
        "XPC_SERVICE_NAME",
        "manual-interactive",
        "non-interactive-unknown",
    ):
        assert expected in code, f"trigger 歸因缺少 {expected!r} 分支"
    assert "trigger=%s" in sh_content or "trigger=${TRIGGER_SRC}" in sh_content, (
        "BEGIN log 必須把 trigger 來源寫入輸出（取證可讀）"
    )


def test_terminal_exit_reflects_fail_count(sh_content: str) -> None:
    """終端 exit 語意：FAIL>0 必須 exit 1；否則 exit 0（對齊 .ps1 R9 ③ exit 語意，
    防止 stage 真失敗卻靜默 exit 0 讓排程 Last Result 恆綠）。"""
    code = _code_only(sh_content)
    assert re.search(r'if \[ "\$FAIL" -gt 0 \]', code), "缺 FAIL 計數守門判斷"
    tail = code[code.find('if [ "$FAIL" -gt 0 ]'):]
    assert re.search(r"exit 1", tail), "FAIL>0 分支必須 exit 1"
    assert re.search(r"exit 0\s*$", code.strip()), "腳本結尾必須有明確 exit 0（全數通過語意）"


def test_heartbeat_three_site_contract_lines(sh_content: str) -> None:
    """心跳檔前兩行格式為三站點契約（dev_start.py mtime 讀取／install_mac_nightly.sh
    --status／本函式寫入），絕不可變。"""
    code = _code_only(sh_content)
    assert "nightly_mac heartbeat（UTC）" in code, "心跳檔第一行格式（三站點契約）不得變動"
    assert "nightly 彙總：PASS=" in code, "心跳檔彙總行格式不得變動"


# --- R67-F10：CLI 契約（--help 不得開跑整套 nightly；未知旗標 fail-loud）--------
#
# WHY：修復前全檔對 `$1` 只有兩處 `= "--force"` 二元比對——無 usage 分支、無未知
# 旗標拒絕。實測兩種失敗形態：(a) 剛 clone／logs 已被輪替掉的樹上，`--help` 直接
# 啟動 macos_smoke → root_unittests → autoclaude_gate → sdd_ci_gate（沙箱實測落下
# nightly_mac_*.log 並跑進 smoke 的 7 個子步驟，被 kill 才停）；(b) 當日已有心跳時
# `--help` rc=0 並印「今日已有心跳…跳過本輪」——查說明的動作被記成一次成功的
# nightly 去重，事後從 log 看不出使用者輸錯了旗標。`--forse`／`-f`／`--Force`／
# `--FORCE`／裸位置參數七種變體實測 rc 全為 0，無一被拒。

# 🔴 R82 包 A2（CARRIER-01）：述詞由「平台」改成「解不解得到一支能跑 .sh 的 bash」。
#
# 舊述詞是 `sys.platform == "win32" or shutil.which("bash") is None`，於是這 25 支在
# Windows 上**恆 skip**、被歸類成 `[POSIX-NATIVE-ONLY]`（＝「這支測試在別的平台才有
# 驗證價值」）。R82 掃描實測推翻了那個分類：把 skip 拿掉、只把載具換成 Git Bash 絕對
# 路徑並將腳本路徑轉正斜線，25 支**在 Windows 上全綠**。也就是說它們驗的是 `.sh` 的
# CLI 契約（`--help` 不開跑 stage、未知旗標 rc=2…），那件事**與宿主平台無關**——真正
# 壞掉的是載具：`shutil.which("bash")` 在本機回 `C:\WINDOWS\system32\bash.EXE`（WSL
# 佔位版），argv 又給反斜線路徑，於是 `/bin/bash: D:CursorProject...: No such file`
# （分隔符被整批吃掉，rc=127）——一個純粹的載具故障被寫成了平台語意。
#
# 舊註解逐字宣稱「Windows 上恆 skip ⇒ 無 WSL 佔位版劫持面」，那正是這條 skip 賴以
# 存在的理由，而該理由已被上述實測推翻，故連同 `# bash-ok:` 豁免一併刪除。
_BASH = find_git_bash() if sys.platform == "win32" else shutil.which("bash")
_POSIX_ONLY = pytest.mark.skipif(
    _BASH is None,
    reason="[TOOL-ABSENCE] 本機解不到任何可用的 bash（Windows 上＝Git for Windows 未安裝；"
           "POSIX 上＝PATH 無 bash）——受測物是 .sh 的 CLI 契約，與宿主平台無關，"
           "缺的只是能把它跑起來的直譯器",
)


def _bash_argv(script: Path, *args: str) -> list[str]:
    """argv[0] 一律是**絕對路徑**的 bash，腳本路徑一律 `as_posix()`。

    🔴 兩者的份量**不相等**，別把它們寫成同一件事（R82 當回合逐項注入實測）：
      · argv[0] 給裸名 ⇒ `CreateProcess` 先搜 System32、必定命中 WSL 啟動器
        （DEF-101-753）。**這一項是致命的**：本機注入後 12 支當場 skip／WSL 路徑下
        受測腳本一行都沒被執行。
      · argv[1] 給反斜線 ⇒ 注入實測 **25 支仍全綠**（`27 passed, 1 failed`，唯一的
        紅是下方那支正規化鎖自己）。也就是說 **Git Bash 吃得下反斜線**；掃描期看到的
        `/bin/bash: D:CursorProjectAISDCL_Agent...`（分隔符整批消失）是 **WSL 啟動器**
        造成的，不是 Git Bash。把它記成「Git Bash 會吃掉反斜線」就是製造一句假話。
        保留正規化的理由因此不是「不改會壞」，而是根 CLAUDE.md 鐵律一對「執行一支
        .sh」明文要求正斜線腳本路徑（跨機器／跨殼一致），屬**慣例一致性**。
    """
    assert _BASH is not None, "呼叫端必須掛 _POSIX_ONLY"
    return [_BASH, Path(script).as_posix(), *args]


# --- R82 包 A2：CARRIER-01 的回歸鎖（三支，缺一都有實證盲區）--------------------
#
# 🔴 為何非有這組不可：上面把 25 支 skip 變成 25 支真跑，**「真跑」這件事本身沒有任何
# 東西在守**——把述詞改回 `sys.platform == "win32"` 就會靜默退回 25 支 skip，而 25 支
# skip 的 pytest 摘要行是綠的、rc 是 0，失效方向正是本 repo 反覆記過的「看起來很乾淨」。
# 分群天花板（`skip_group_policy._RUNTIME_SKIP_CEILING`）會抓到總量上升，但那是**收輪
# 者跑整棵樹**才看得到的訊號；本檔自己被單獨跑時（開發迴圈、`-k` 篩選）零訊號。

def test_the_bash_gate_is_carrier_availability_not_host_platform() -> None:
    """`_POSIX_ONLY` 的述詞不得再出現任何平台判斷——那正是 CARRIER-01 的病灶本體。

    Rule 9（鎖意圖）：這條規則要守的不是「別寫 sys.platform」這個字面，而是
    「**分類必須對應真實原因**」。25 支測的是 `.sh` 的 CLI 契約（rc、usage 文字、
    有沒有落 log），沒有一支碰到 POSIX 專屬語意；把它們標成 `[POSIX-NATIVE-ONLY]`
    等於宣稱「這件事只有在別的平台驗才有意義」，而實測證明那句話是假的。
    分類寫錯的代價不是美觀：S3「徹底解決 skipped」的分流者照標籤讀，會把「換個載具
    就會跑」的 25 支歸進「結構上不可能跑」那一桶，於是永遠沒有人去修它。
    """
    src = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    predicate: str | None = None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "_POSIX_ONLY" for t in node.targets)
            and isinstance(node.value, ast.Call)
            and node.value.args
        ):
            predicate = ast.get_source_segment(src, node.value.args[0])
    assert predicate is not None, (
        "找不到 `_POSIX_ONLY = pytest.mark.skipif(<述詞>, …)`——結構已變動，"
        "請同步本鎖（結構抽不到時必須 fail-loud，不得靜默放行）"
    )
    for banned in ("sys.platform", "os.name", "platform.system", "platform.machine"):
        assert banned not in predicate, (
            f"skip 述詞又出現平台判斷 `{banned}`：{predicate!r}——CARRIER-01 迴歸。"
            "這 25 支在 Windows 上實測全綠（R82），述詞只准問「解不解得到 bash」"
        )
    assert "_BASH" in predicate, (
        f"skip 述詞不再依賴 `_BASH`（載具解析結果）：{predicate!r}——"
        "述詞若改問別的東西，載具與 skip 的對應關係就斷了"
    )


def test_the_resolved_interpreter_is_absolute_and_never_the_wsl_stub() -> None:
    """載具本身的判準：絕對路徑 ＋ 不得落在 System32（WSL 啟動器）。

    沒有這一支，把 `_BASH` 改回 `shutil.which("bash")` 仍能讓上一支綠（述詞照樣只問
    `_BASH`），而本機實測 `shutil.which("bash")` 回的就是 `C:\\WINDOWS\\system32\\
    bash.EXE`——DEF-101-753 的原坑，且它在裝了 WSL 發行版的機器上不會紅，只會把 repo
    的腳本丟進 Linux 真的跑起來（沒有錯誤訊息、沒有非零 rc，只有語意換了一個作業系統）。
    """
    if _BASH is None:
        pytest.skip("[TOOL-ABSENCE] 本機解不到 bash——載具判準無標的可驗")
    assert Path(_BASH).is_absolute(), (
        f"argv[0] 必須是絕對路徑，實得 {_BASH!r}——裸名在 Windows 上必定先命中 "
        "System32 的 WSL 啟動器（CreateProcess 搜尋順序把 System32 排在 PATH 之前）"
    )
    parts = [p.lower() for p in PureWindowsPath(_BASH).parts]
    assert "system32" not in parts, (
        f"解析到的 bash 落在 System32：{_BASH!r}——那是 WSL 啟動器，不是 Git Bash"
    )


def test_bash_argv_normalises_the_script_path_to_forward_slashes(tmp_path: Path) -> None:
    """argv[1] 必須是正斜線（根 CLAUDE.md 鐵律一對「執行一支 .sh」的明文慣例）。

    🔴 **誠實劃界**：這一支守的是慣例，不是「不這樣寫就會壞」。當回合把
    `as_posix()` 換回 `str(script)` 實測 `27 passed, 1 failed`——25 支受測物**全綠**，
    唯一的紅就是本支。所以它的價值是「讓 argv 形態在任何機器／任何殼上都一樣」，
    以及擋住有人把 argv[1] 換成別的東西（末段兩條斷言）；把它宣傳成「反斜線會讓
    Git Bash 壞掉」則是假話（那個現象出自 WSL 啟動器）。
    """
    if _BASH is None:
        pytest.skip("[TOOL-ABSENCE] 本機解不到 bash——載具判準無標的可驗")
    argv = _bash_argv(tmp_path / "a b" / "run.sh", "--force")
    assert "\\" not in argv[1], f"argv[1] 仍帶反斜線：{argv[1]!r}"
    assert argv[1].endswith("/a b/run.sh"), f"路徑正規化把內容改掉了：{argv[1]!r}"
    assert argv[2:] == ["--force"], f"位置參數未原樣附加：{argv!r}"


def _sandbox_nightly(tmp_path: Path) -> Path:
    """把真的 run_local_nightly.sh 放進臨時樹（ROOT 由 BASH_SOURCE/../.. 推得）。

    在沙箱而非真 repo 執行：本組要斷言的正是「有沒有產生 nightly log／有沒有開跑
    stage」，在真 repo 上跑會污染真心跳與 RunId log；沙箱裡 `$ROOT/tools/*.sh`
    全不存在，萬一契約退化也會在第一個 stage 立刻失敗而非真的跑完整套 gate。
    """
    dest = tmp_path / "AutoClaude" / "tools"
    dest.mkdir(parents=True)
    shutil.copy2(_NIGHTLY_SH, dest / "run_local_nightly.sh")
    return dest / "run_local_nightly.sh"


def _run_sh(
    script: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    full_env = dict(os.environ)
    if env is not None:
        full_env.update(env)
    return subprocess.run(
        _bash_argv(script, *args),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120, env=full_env,
    )


@_POSIX_ONLY
def test_help_prints_usage_rc_zero_and_starts_no_stage(tmp_path: Path) -> None:
    script = _sandbox_nightly(tmp_path)
    proc = _run_sh(script, "--help")
    assert proc.returncode == 0, f"`--help` 必須 rc=0，實得 {proc.returncode}：{proc.stderr}"
    assert "用法：" in proc.stdout, f"`--help` 必須印出用法，實得 stdout={proc.stdout!r}"
    for token in ("--force", "macos_smoke", "nightly_anchor", "nightly_mac_latest.log"):
        assert token in proc.stdout, f"usage 應說明 {token}（旗標語意／stage 名／log 落點）"
    logs = tmp_path / "AutoClaude" / "logs"
    assert not logs.exists() or not list(logs.glob("nightly_mac_*.log")), (
        "`--help` 絕不得產生 RunId log／心跳——那代表它其實開跑了 nightly"
    )


@_POSIX_ONLY
@pytest.mark.parametrize("bad", ["--forse", "-f", "--Force", "--FORCE", "bogus-positional"])
def test_unknown_flag_fails_loud_and_starts_no_stage(tmp_path: Path, bad: str) -> None:
    """typo 一律 rc=2 且指名該字——修復前這七種變體全部 rc=0 靜默走去重路徑。"""
    script = _sandbox_nightly(tmp_path)
    proc = _run_sh(script, bad)
    assert proc.returncode == 2, f"未知參數 {bad!r} 必須 rc=2，實得 {proc.returncode}"
    assert bad in proc.stderr, f"錯誤訊息必須逐字指名 {bad!r}，實得 {proc.stderr!r}"
    logs = tmp_path / "AutoClaude" / "logs"
    assert not logs.exists() or not list(logs.glob("nightly_mac_*.log")), (
        f"{bad!r} 被拒後不得留下任何 nightly log"
    )


@_POSIX_ONLY
def test_extra_arguments_fail_loud(tmp_path: Path) -> None:
    proc = _run_sh(_sandbox_nightly(tmp_path), "--force", "--bogus")
    assert proc.returncode == 2, "多個參數必須 fail-loud（本腳本最多接受一個旗標）"


@_POSIX_ONLY
def test_no_args_is_not_rejected(tmp_path: Path) -> None:
    """鑑別力對照組：無參數＝排程路徑，**不得**被新的參數檢查誤擋。

    少了這條，把腳本改成「一律 exit 2」也能讓上面全綠——那會讓 launchd 每天空跑。
    無參數時沙箱裡的 stage 腳本不存在故必然失敗（rc=1），關鍵是它**確實走進了
    stage 執行**（印得出 BEGIN／stage 標題），而不是在參數關卡就被擋掉。
    """
    script = _sandbox_nightly(tmp_path)
    proc = _run_sh(script)
    assert proc.returncode != 2, f"無參數不得被當成參數錯誤，實得 rc=2：{proc.stderr!r}"
    logs = list((tmp_path / "AutoClaude" / "logs").glob("nightly_mac_2*.log"))
    assert logs, "無參數時應照舊產生 RunId log（證明真的進入了排程執行路徑）"
    assert "BEGIN nightly_mac" in logs[0].read_text(encoding="utf-8", errors="replace")


# --- R67-F26：觸發來源歸因（XPC_SERVICE_NAME 值比對，而非存在性）---------------
#
# WHY：`XPC_SERVICE_NAME=0` 是 macOS 對**一般使用者行程**注入的常態值（Darwin
# 25.5.0 實測 `/bin/bash -c 'echo ${XPC_SERVICE_NAME}'` → `0`），舊判定用
# `[ -n ... ]` 測存在性，於是任何手動／agent／CI 呼叫都被標成 `launchd(...)`，
# 而 manual-interactive／non-interactive-unknown 兩態成為死碼。此欄位存在的唯一
# 目的就是「同日兩輪 PASS 時能機械判讀是手動重跑還是去重漏洞」——舊判定正好在
# 那個情境給出反向結論（把去重漏洞歸因給無辜的排程器）。


def _extract_trigger_block(code: str) -> str:
    """抽出「label 常數 ＋ 觸發來源判定」兩段真實碼，供實跑對照（非字串比對）。"""
    label = re.search(r'^NIGHTLY_LAUNCHD_LABEL=.*$', code, re.M)
    block = re.search(
        r'^if \[ "\$\{1:-\}" = "--force" \]; then$.*?^fi$', code, re.M | re.DOTALL
    )
    assert label and block, "找不到 label 常數或觸發來源判定區塊——抽取正則已與實作漂移"
    return f"{label.group(0)}\n{block.group(0)}\n"


def _trigger_for(tmp_path: Path, code: str, *, xpc: str | None, args: tuple[str, ...] = ()) -> str:
    probe = tmp_path / "trigger_probe.sh"
    probe.write_text(
        "set -u\n" + _extract_trigger_block(code) + 'printf "%s" "${TRIGGER_SRC}"\n',
        # 🔴 `newline="\n"`（R82 包 A2）：Windows 上 `write_text` 預設會把 `\n` 轉成
        # `\r\n`，而 bash 會把行尾的 `\r` 當成指令的一部分（`then\r` 之類的語法錯）。
        # 這一行在「Windows 恆 skip」的年代永遠沒被執行過，故從未顯形。
        encoding="utf-8", newline="\n",
    )
    env = dict(os.environ)
    env.pop("XPC_SERVICE_NAME", None)
    if xpc is not None:
        env["XPC_SERVICE_NAME"] = xpc
    return subprocess.run(
        _bash_argv(probe, *args),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=30, env=env,
    ).stdout


@_POSIX_ONLY
def test_sentinel_xpc_value_is_not_attributed_to_launchd(tmp_path: Path, sh_content: str) -> None:
    """真機常態值 `XPC_SERVICE_NAME=0`（非 launchd job）不得被標成 launchd。"""
    got = _trigger_for(tmp_path, sh_content, xpc="0")
    assert "launchd" not in got, (
        f"XPC_SERVICE_NAME=0 是一般使用者行程的常態值，不得歸因為 launchd，實得 {got!r}"
    )
    assert got == "non-interactive-unknown", (
        f"非互動且非排程應為 non-interactive-unknown，實得 {got!r}"
    )


@_POSIX_ONLY
def test_real_launchd_label_is_attributed_to_launchd(tmp_path: Path, sh_content: str) -> None:
    """對照組：真 launchd 注入的值是 job Label，必須仍被正確歸因。

    沒有這條，把判定改成「永不回 launchd」也能讓上一條綠——那會把歸因能力整個
    拆掉（本機 7 份真排程 log 皆為 XPC_SERVICE_NAME=com.autoclaude.nightly）。
    """
    label = re.search(r'^LABEL="([^"]+)"', _MAC_INSTALLER.read_text(encoding="utf-8"), re.M)
    assert label, "install_mac_nightly.sh 找不到 LABEL 常數"
    got = _trigger_for(tmp_path, sh_content, xpc=label.group(1))
    assert got == f"launchd(XPC_SERVICE_NAME={label.group(1)})", (
        f"真 launchd Label 必須歸因為 launchd，實得 {got!r}"
    )


@_POSIX_ONLY
def test_force_flag_wins_over_environment(tmp_path: Path, sh_content: str) -> None:
    got = _trigger_for(tmp_path, sh_content, xpc="0", args=("--force",))
    assert got == "manual-force", f"--force 應優先於環境判定，實得 {got!r}"


@_POSIX_ONLY
def test_unset_xpc_is_non_interactive_unknown(tmp_path: Path, sh_content: str) -> None:
    got = _trigger_for(tmp_path, sh_content, xpc=None)
    assert got == "non-interactive-unknown", (
        f"未設定 XPC 時應為 non-interactive-unknown，實得 {got!r}"
    )


def test_launchd_label_matches_the_installer_verbatim(sh_content: str) -> None:
    """跨檔字面一致性：歸因基準值必須與 tools/install_mac_nightly.sh 的 LABEL 同字。

    測意圖：兩邊一旦漂移，真排程觸發會被靜默降級成 non-interactive-unknown——
    沒有任何錯誤訊息，只是取證欄位開始說謊（正是 R67-F26 的失敗形態）。
    """
    ours = re.search(r'^NIGHTLY_LAUNCHD_LABEL="([^"]+)"', _code_only(sh_content), re.M)
    theirs = re.search(r'^LABEL="([^"]+)"', _MAC_INSTALLER.read_text(encoding="utf-8"), re.M)
    assert ours and theirs, "兩側 label 常數至少一支抽不到——正則已與實作漂移"
    assert ours.group(1) == theirs.group(1), (
        f"run_local_nightly.sh 的 launchd label {ours.group(1)!r} 與安裝器的 "
        f"{theirs.group(1)!r} 不一致——真排程觸發會被誤標為手動"
    )


def test_trigger_uses_value_comparison_not_mere_presence(sh_content: str) -> None:
    """靜態面補刀：判定式不得退回 `[ -n "${XPC_SERVICE_NAME:-}" ]` 存在性寫法。

    與上面的實跑對照組互補——實跑證明「當前行為對」，本條把「用什麼判準」釘住，
    讓退化在 code review／grep 層面也留下痕跡。
    """
    block = _extract_trigger_block(_code_only(sh_content))
    assert '[ -n "${XPC_SERVICE_NAME:-}" ]' not in block, (
        "存在性判定會把 XPC_SERVICE_NAME=0（macOS 對一般行程注入的常態值）"
        "誤判為 launchd 觸發——必須與 job Label 做值比對"
    )
    assert "${NIGHTLY_LAUNCHD_LABEL}" in block, "判定式必須以 label 常數為比對基準"


# --- 對抗式（負向）case：真突變（mutate）真實 sh_content 後重跑正向斷言邏輯 -----
# R31 QA 一審必修條件 1：原版本對著測試檔內手刻的 degraded_sample／degraded_line
# 字面字串做斷言，從未讀取或修改真正的 sh_content——是恆真的裝飾性測試（tautology），
# 沒有任何鑑別力。改為：對真實 sh_content 做文字替換模擬退化，重跑上面同一組
# `_has_stale_lock_liveness_check()` / `_rotation_pattern_excludes_heartbeat()`
# 判斷式本身，確認其在退化樣本上真的翻轉為 False，才算真正驗證了鑑別力。

def test_bug_injection_missing_stale_lock_liveness_check_is_caught(sh_content: str) -> None:
    """真突變：把真實 sh_content 裡的 `kill -0` 存活性檢查行換成固定逾時判斷，
    重跑 `_has_stale_lock_liveness_check()` 本身，確認會由 True 翻轉為 False。"""
    code = _code_only(sh_content)
    assert _has_stale_lock_liveness_check(code), "測試前提不成立：真實 sh 應含 kill -0"

    liveness_line = next(line for line in code.splitlines() if "kill -0" in line)
    degraded_line = (
        '      _age=$(( $(date +%s) - $(stat -f %m "${NIGHTLY_LOCK_DIR}") )); '
        '[ "${_age}" -gt 300 ]  # mutated: 固定逾時取代存活性檢查'
    )
    mutated = code.replace(liveness_line, degraded_line)
    assert mutated != code, "突變未生效——找不到可替換的 kill -0 那一行"
    assert not _has_stale_lock_liveness_check(mutated), (
        "退化為固定逾時判斷後，_has_stale_lock_liveness_check() 必須翻轉為 False"
        "——若仍為 True，代表該判斷式本身沒有鑑別力"
    )


def test_bug_injection_dedup_pattern_matching_heartbeat_file_is_caught(sh_content: str) -> None:
    """真突變：把真實 sh_content 裡的輪替 pattern `nightly_mac_2*.log` 改壞為會
    誤配到心跳檔的寬鬆版本 `nightly_mac_*.log`，重跑
    `_rotation_pattern_excludes_heartbeat()` 本身，確認會由 True 翻轉為 False。"""
    code = _code_only(sh_content)
    assert _rotation_pattern_excludes_heartbeat(code), "測試前提不成立：真實 sh 應排除心跳檔"

    mutated = code.replace("nightly_mac_2*.log", "nightly_mac_*.log")
    assert mutated != code, "突變未生效——找不到可替換的輪替 pattern"
    assert fnmatch.fnmatch("nightly_mac_latest.log", "nightly_mac_*.log"), (
        "測試前提檢查：退化 pattern 必須真的以 glob 語意命中心跳檔案名"
    )
    assert not _rotation_pattern_excludes_heartbeat(mutated), (
        "退化為寬鬆 pattern 後，_rotation_pattern_excludes_heartbeat() 必須翻轉為"
        " False——若仍為 True，代表該判斷式本身沒有鑑別力（純字面子字串比對"
        "抓不到這個退化，這正是本 case 存在的理由）"
    )


# --- DEF-200-450：樹身分（`git context:`／`SAMPLE VALIDITY:`）-----------------------
#
# WHY：2026-09-28～10-01 連續四晚 nightly 跑在舊樹上（立案時落後 30 個 commit），RunId
# log 逐字相同（「發現 4662 個測試（下限 4543）」）而無人察覺——log 沒有「跑的是哪棵
# 樹」，跑舊樹與跑 HEAD 的日誌無從區分，驗收力為零。Windows 側 .ps1 早有這兩行
# （DEF-101-887），本節鎖 .sh 的對等實作。心跳檔三站點契約一個位元組都不准動。

_TREE_IDENTITY_LINE_SHAPES = (
    "git context: branch=%s sha=%s head_date=%s origin_main=%s origin_main_date=%s "
    "behind_origin_main=%s",
    "SAMPLE VALIDITY: tree_state=%s dirty_entries=%s tree_fingerprint=%s head=%s",
)
# 兩平台共用的欄位名（.ps1 用 {0}／字串內插組行，故只比欄位名、不比整行）。
_TREE_IDENTITY_FIELDS = (
    "git context: branch=", " sha=", "tree_state=", "dirty_entries=",
    "tree_fingerprint=", " head=",
)
_TREE_IDENTITY_TOKENS = ("SAMPLE VALIDITY", "git context", "tree_state", "print_tree_identity")


def _function_body(code: str, name: str) -> str:
    """抽出頂層 `name() {` 至行首 `}` 的函式本體；抽不到即 fail-loud（不回空字串）。"""
    m = re.search(rf"^{re.escape(name)}\(\) \{{$.*?^\}}$", code, re.M | re.DOTALL)
    assert m, f"找不到頂層函式 {name}()——抽取正則已與實作漂移"
    return m.group(0)


def _tree_identity_is_wired_in_place(code: str) -> bool:
    """樹身分函式的定義與呼叫都在 `python 直譯器：` 之後、第一個 `run_stage 1` 之前。"""
    banner = code.find("python 直譯器：")
    definition = re.search(r"^print_tree_identity\(\) \{$", code, re.M)
    call = re.search(r"^print_tree_identity$", code, re.M)
    first_stage = re.search(r"^run_stage 1 ", code, re.M)
    if banner < 0 or not (definition and call and first_stage):
        return False
    return banner < definition.start() < call.start() < first_stage.start()


def _heartbeat_is_free_of_tree_identity(code: str) -> bool:
    body = _function_body(code, "write_heartbeat")
    return not any(token in body for token in _TREE_IDENTITY_TOKENS)


def test_tree_identity_lines_exist_and_share_field_names_with_the_ps1(sh_content: str) -> None:
    """.sh 必須印 `git context:`／`SAMPLE VALIDITY:` 兩行，欄位名與 .ps1 逐字相同。

    沒有樹身分，四晚跑舊樹的日誌與跑 HEAD 的日誌逐字相同，驗收力為零（DEF-200-450）。
    欄位名對稱是第二層意圖：兩平台 log 要能被同一條 grep／同一支解析器讀，任何一側改名
    而另一側沒跟，下游就只剩一個平台看得見樹身分。
    """
    code = _code_only(sh_content)
    for shape in _TREE_IDENTITY_LINE_SHAPES:
        assert shape in code, f"nightly.sh 缺樹身分輸出行：{shape!r}"
    for anchor in ("rev-parse --short HEAD", "status --porcelain", "diff-index -p --no-ext-diff"):
        assert anchor in code, f"nightly.sh 缺樹身分取樣指令 {anchor!r}（指紋要含 diff 內容）"
    ps1 = (_REPO_ROOT / "tools" / "run_local_nightly.ps1").read_text(encoding="utf-8")
    for field in _TREE_IDENTITY_FIELDS:
        assert field in ps1, f"run_local_nightly.ps1 沒有欄位 {field!r}——兩平台欄位名已分歧"
        assert field in code, f"nightly.sh 沒有欄位 {field!r}——兩平台欄位名已分歧"


def test_tree_identity_is_emitted_after_the_interpreter_banner_and_before_the_first_stage(
    sh_content: str,
) -> None:
    """位置鎖：樹身分要在 `$PY` 釘死並印出之後（指紋用它算）、第一個 stage 之前。

    放在 stage 之後，stage 1 一旦把整支腳本拖死或被 kill 就永遠印不出來——而「跑的是哪
    棵樹」正是 stage 失敗時最需要的證據。
    """
    code = _code_only(sh_content)
    assert _tree_identity_is_wired_in_place(code), (
        "樹身分必須在 `python 直譯器：` 之後、第一個 `run_stage 1` 之前定義並呼叫"
    )
    # 真突變（驗證鏡子自身）：把呼叫移到所有 stage 之後，判準必須翻轉為 False。
    mutated = re.sub(
        r"^print_tree_identity$\n", "", code, count=1, flags=re.M
    ) + "print_tree_identity\n"
    assert mutated != code, "突變未生效——找不到獨占一行的 print_tree_identity 呼叫"
    assert not _tree_identity_is_wired_in_place(mutated), (
        "呼叫被移到 stage 之後，位置判準仍為 True——判準本身沒有鑑別力"
    )


def test_tree_identity_never_enters_the_heartbeat_function(sh_content: str) -> None:
    """心跳三站點契約（dev_start.py／install_mac_nightly.sh／baseline_origin.py 皆以固定
    行位置讀它）一個位元組都不准動：樹身分只進 RunId log，不得出現在 write_heartbeat。"""
    code = _code_only(sh_content)
    body = _function_body(code, "write_heartbeat")
    # 對照組：抽到的確實是心跳本體（抽成空殼會讓下面的否定斷言恆真）。
    assert "nightly_mac heartbeat（UTC）" in body and "nightly 彙總：PASS=" in body
    assert _heartbeat_is_free_of_tree_identity(code), "樹身分漏進了心跳函式"
    # 真突變：在心跳寫入群組裡塞一行樹身分，判準必須翻轉為 False。
    mutated = code.replace(
        "printf 'log=%s\\n'", "printf 'SAMPLE VALIDITY: x\\n'; printf 'log=%s\\n'", 1
    )
    assert mutated != code, "突變未生效——找不到心跳的 log= 指標行"
    assert not _heartbeat_is_free_of_tree_identity(mutated), "漏入心跳的樹身分沒被判準抓到"


# 功能面：把真的 .sh 放進一棵「真 git repo ＋ 假 .venv」的沙箱，實跑到 stage 失敗為止
# （沙箱內 stage 腳本全不存在 ⇒ 全部 stage 立刻失敗、整趟不到兩秒），再讀 RunId log。
# 不改用「把函式抽進探針腳本」：位置（直譯器橫幅之後、stage 之前）與 `exec` 改道後的
# 落點正是要驗的東西，抽出來就驗不到了。

@pytest.fixture
def hermetic_git(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """切斷繼承來的 git 環境：hook 行程（pre-commit／pre-push 跑本檔時）會帶 GIT_DIR／
    GIT_INDEX_FILE，使用者的 ~/.gitconfig 可能帶 gpgsign／hooksPath／templateDir——沙箱
    repo 的 init／commit 不該被任何一個左右，更不該碰到真 repo 的索引。

    `GIT_CONFIG_GLOBAL` 只管 config，管不到全域排除檔：git 還會讀
    `$XDG_CONFIG_HOME/git/ignore`（未設則 `$HOME/.config/git/ignore`）。使用者在那裡忽略的
    檔名（如 half_done.py）會讓沙箱裡的未追蹤檔憑空消失，髒樹測試因此假紅；所以 HOME 與
    XDG_CONFIG_HOME 也要改指一個空的兄弟目錄（不能放在沙箱 repo 之內，否則它自己就成了
    未追蹤條目）。"""
    for key in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    home = tmp_path_factory.mktemp("hermetic_home")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, env={**os.environ, **(env or {})},
    )
    assert proc.returncode == 0, f"git {args} rc={proc.returncode}: {proc.stderr}"
    return proc.stdout


def _tree_sandbox(
    root: Path, *, age_days: int = 0, git_repo: bool = True, origin_ahead: bool = False
) -> Path:
    """`_sandbox_nightly` ＋ 假 `.venv/bin/python`（過 .venv 守門、轉呼叫本機直譯器）＋
    已 commit 的 git repo（HEAD 往前撥 age_days 天；origin_ahead＝origin/main 領先一個
    commit，樹內容相同故工作樹仍乾淨）。`.gitignore` 照真 repo 蓋掉 .venv／logs。"""
    script = _sandbox_nightly(root)
    py = root / ".venv" / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text(
        f'#!/bin/sh\nexec "{Path(sys.executable).as_posix()}" "$@"\n',
        encoding="utf-8", newline="\n",
    )
    py.chmod(0o755)
    (root / ".gitignore").write_text(".venv/\nAutoClaude/logs/\n", encoding="utf-8", newline="\n")
    if not git_repo:
        return script
    stamp = f"{int(time.time()) - age_days * 86400} +0000"
    ident = {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_AUTHOR_DATE": stamp,
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "GIT_COMMITTER_DATE": stamp,
    }
    _git(root, "init", "-q")
    _git(root, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed", env=ident)
    if origin_ahead:
        child = _git(root, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "ahead", env=ident)
        _git(root, "update-ref", "refs/remotes/origin/main", child.strip())
    return script


def _nightly_log(root: Path) -> str:
    logs = sorted((root / "AutoClaude" / "logs").glob("nightly_mac_2*.log"))
    assert logs, "沙箱沒有產生 RunId log——腳本在寫 log 之前就死了"
    return logs[0].read_text(encoding="utf-8", errors="replace")


@_POSIX_ONLY
@pytest.mark.usefixtures("hermetic_git")
def test_tree_identity_names_the_real_head_and_how_far_behind_origin_it_is(
    tmp_path: Path,
) -> None:
    """乾淨樹：log 裡印的 sha 必須就是這棵樹實際的 HEAD、落後數必須是真的落後數。

    DEF-200-450 的失敗形態是「log 對跑的是哪個 commit 一個字也沒說」。這裡不只查欄位
    存在，而是拿沙箱 repo 自己的 `rev-parse` 當對照：印出來的 sha 與 origin/main 的 sha
    刻意不同，才分得出腳本印的是 HEAD 還是別的東西。
    """
    _run_sh(_tree_sandbox(tmp_path, origin_ahead=True))
    log = _nightly_log(tmp_path)
    head = _git(tmp_path, "rev-parse", "--short", "HEAD").strip()
    origin = _git(tmp_path, "rev-parse", "--short", "origin/main").strip()
    assert head != origin, "測試前提不成立：HEAD 與 origin/main 應是不同 commit"
    iso = r"\d{4}-\d\d-\d\dT\S+"
    assert re.search(
        rf"^git context: branch=main sha={head} head_date={iso} origin_main={origin} "
        rf"origin_main_date={iso} behind_origin_main=1（本機 ref",
        log, re.M,
    ), f"git context 行與沙箱 repo 的實況對不上：{log!r}"
    assert re.search(
        rf"^SAMPLE VALIDITY: tree_state=clean dirty_entries=0 "
        rf"tree_fingerprint=[0-9a-f]{{12}} head={head}$",
        log, re.M,
    ), f"乾淨樹的樣本效度行不對：{log!r}"
    assert "⚠️ SAMPLE VALIDITY" not in log, "乾淨且新鮮的樹不該出任何樣本效度警告"
    marks = ("python 直譯器：", "git context:", "SAMPLE VALIDITY: tree_state=", "--- [1/5]")
    positions = [log.index(m) for m in marks]
    assert positions == sorted(positions), f"樹身分不在直譯器橫幅與第一個 stage 之間：{marks}"


@_POSIX_ONLY
@pytest.mark.usefixtures("hermetic_git")
def test_dirty_tree_is_flagged_and_the_fingerprint_sees_content_not_just_status(
    tmp_path: Path,
) -> None:
    """髒樹：標 dirty＋筆數＋警告；指紋含內容——同一支檔、同一個 ` M` 狀態列、只改內容，
    指紋必須不同（只雜湊 status 的話，「對已在清單內的檔再改一次」完全不可見）。"""
    def run(name: str, note: str, extra_untracked: bool = False) -> tuple[str, str]:
        root = tmp_path / name
        script = _tree_sandbox(root)
        with (root / ".gitignore").open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(note)
        if extra_untracked:
            (root / "half_done.py").write_text("print('wip')\n", encoding="utf-8")
        entries = 2 if extra_untracked else 1
        _run_sh(script)
        log = _nightly_log(root)
        m = re.search(
            rf"^SAMPLE VALIDITY: tree_state=dirty dirty_entries={entries} "
            r"tree_fingerprint=([0-9a-f]{12}) head=",
            log, re.M,
        )
        assert m, f"髒樹沒被標成 dirty/{entries}：{log!r}"
        return m.group(1), log

    fp_a1, log_a1 = run("a1", "# edit-A\n")
    fp_a2, _ = run("a2", "# edit-A\n")
    fp_b, _ = run("b", "# edit-B\n")
    assert fp_a1 == fp_a2, "同一份髒樹內容，指紋必須可重現（否則 differ 斷言無意義）"
    assert fp_a1 != fp_b, "只改內容、狀態列相同的兩棵髒樹指紋相同——指紋沒含 diff 內容"
    assert "⚠️ SAMPLE VALIDITY: 本輪在**非乾淨**工作樹上採集（1 筆未提交變更）" in log_a1
    # 還沒 `git add` 的新檔是最常見的半成品形態：未追蹤條目也必須計入筆數。
    fp_c, log_c = run("c", "# edit-A\n", extra_untracked=True)
    assert "（2 筆未提交變更）" in log_c, "未追蹤的新檔沒被計入 dirty_entries"
    assert fp_c != fp_a1, "多了一個未追蹤檔，指紋卻沒變"


@_POSIX_ONLY
@pytest.mark.usefixtures("hermetic_git")
@pytest.mark.parametrize(("age_days", "warns"), [(2, False), (4, True)])
def test_stale_head_warning_fires_only_beyond_72_hours(
    tmp_path: Path, age_days: int, warns: bool
) -> None:
    """HEAD 超過 72 小時未更新才警告：48 小時不得喊（否則每個週末都誤報）、96 小時必須
    喊——後者正是 DEF-200-450 那四晚的訊號（本機沒 git pull，跑的一直是舊樹）。"""
    _run_sh(_tree_sandbox(tmp_path, age_days=age_days))
    log = _nightly_log(tmp_path)
    m = re.search(r"^⚠️ SAMPLE VALIDITY: HEAD 已 (\d+) 小時未更新（(\S+)）", log, re.M)
    if not warns:
        assert m is None, f"{age_days} 天前的 HEAD 不該觸發陳舊警告：{m and m.group(0)}"
        return
    assert m, f"{age_days} 天前的 HEAD 必須觸發陳舊警告：{log!r}"
    assert abs(int(m.group(1)) - age_days * 24) <= 1, f"小時數算錯：{m.group(0)}"
    assert f"head_date={m.group(2)} " in log, "警告裡的日期必須就是 git context 印的 head_date"
    assert "本機可能尚未 git pull" in log


@_POSIX_ONLY
@pytest.mark.usefixtures("hermetic_git")
def test_tree_identity_degrades_to_unknown_outside_a_git_repo_without_aborting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """取樣失敗必須攤開成 unknown，且絕不拖垮 nightly：非 git 樹印 unknown＋樣本效度未知
    警告，之後全部 stage 照跑完、彙總行照印、exit 1 仍反映 stage 失敗。"""
    # 禁止 git 往上找到外層 repo（tmp_path 若恰好位於某個 repo 內，會讓本測試假紅）。
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.resolve().parent))
    proc = _run_sh(_tree_sandbox(tmp_path, git_repo=False))
    log = _nightly_log(tmp_path)
    assert (
        "git context: branch=unknown sha=unknown head_date=unknown origin_main=unknown "
        "origin_main_date=unknown behind_origin_main=unknown"
    ) in log, f"非 git 樹的 git context 行應全為 unknown：{log!r}"
    assert (
        "SAMPLE VALIDITY: tree_state=unknown dirty_entries=-1 "
        "tree_fingerprint=unknown head=unknown"
    ) in log
    assert "樣本效度**未知**，不得當成乾淨" in log
    assert "小時未更新" not in log, "取不到 commit 時間不得憑空判陳舊"
    assert "--- [4/5] sdd_ci_gate FAIL" in log, "樣本取失敗後，stage 必須照跑完"
    assert "--- [5/5] nightly_anchor FAIL" in log, "最後一個 stage 也必須照跑（沙箱內腳本不存在）"
    assert "===== nightly 彙總：PASS=0 FAIL=5 =====" in log
    assert proc.returncode == 1, f"stage 失敗的 exit 語意被取樣失敗改掉了：rc={proc.returncode}"


def _stub_fingerprint_python(root: Path, on_hashlib: str) -> None:
    """換掉沙箱的 `.venv/bin/python`：引數含 `hashlib`（＝指紋那一行）時改跑 `on_hashlib`
    這段 sh，其餘呼叫照舊轉給本機直譯器。.venv 在 .gitignore 內，不影響樹狀態。"""
    py = root / ".venv" / "bin" / "python"
    py.write_text(
        f'#!/bin/sh\ncase "$*" in\n  *hashlib*) {on_hashlib} ;;\nesac\n'
        f'exec "{Path(sys.executable).as_posix()}" "$@"\n',
        encoding="utf-8", newline="\n",
    )


@_POSIX_ONLY
@pytest.mark.usefixtures("hermetic_git")
@pytest.mark.parametrize(
    "on_hashlib",
    [
        pytest.param("echo 'NOT-A-HASH garbage line'", id="garbage-on-stdout"),
        pytest.param("exit 3", id="exits-nonzero-silently"),
    ],
)
def test_a_fingerprint_that_is_not_a_hash_degrades_to_unknown_without_aborting(
    tmp_path: Path, on_hashlib: str
) -> None:
    """指紋子行程印垃圾或直接失敗 ⇒ `tree_fingerprint=unknown`，全部 stage 照跑、exit 語意不變。

    WHY：指紋是「這份 log 跑的是哪棵樹」的身分欄。舊版只判空字串，子行程往 stdout 印的任何
    東西（sitecustomize 橫幅、警告、被包裝過的 python）都會被照單全收成「指紋」——垃圾值比
    unknown 更糟：unknown 會被讀者當成「沒量到」，垃圾值卻會被當成一個合法但對不上任何一棵
    樹的指紋，把「兩晚是不是同一棵樹」的比對帶歪。
    """
    script = _tree_sandbox(tmp_path)
    _stub_fingerprint_python(tmp_path, on_hashlib)
    proc = _run_sh(script)
    log = _nightly_log(tmp_path)
    assert re.search(
        r"^SAMPLE VALIDITY: tree_state=clean dirty_entries=0 "
        r"tree_fingerprint=unknown head=[0-9a-f]+$",
        log, re.M,
    ), f"垃圾指紋沒被降級成 unknown：{log!r}"
    assert "NOT-A-HASH" not in log
    assert "--- [4/5] sdd_ci_gate FAIL" in log, "指紋取樣失敗後，stage 必須照跑完"
    assert "===== nightly 彙總：PASS=0 FAIL=5 =====" in log
    assert proc.returncode == 1, f"stage 失敗的 exit 語意被取樣失敗改掉了：rc={proc.returncode}"


# 把 stdout 開成 newline="\r\n" 的直譯器墊片：重現 Windows 原生 python.exe 的文字模式行為。
# 🔴 這**不是**強制 stdio-UTF-8 的站點（不帶 encoding、只改 newline 翻譯），所以刻意把
# `sys.stdout.buffer` 先取進區域變數再包：R75 的「stdio-UTF-8 唯一實作」shrink-only 棘輪
# （tools/tests/test_platform_utils_dedup.py `_STDIO_FORCE_RE` b 判準）寬判
# 「`TextIOWrapper(` 直接包 std 串流 `.buffer`」的字面，直寫會被算成第 24 處複本而紅；本墊片與該
# 棘輪守的「第二套 UTF-8 強制實作」無關。
_CRLF_STDOUT_SHIM = (
    "import io, sys\n"
    "_raw_stdout = sys.stdout.buffer\n"
    'sys.stdout = io.TextIOWrapper(_raw_stdout, newline="\\r\\n", write_through=True)\n'
    "exec(sys.argv[2])\n"  # argv = [本墊片, "-c", <原本要跑的程式碼>]
)


@_POSIX_ONLY
@pytest.mark.usefixtures("hermetic_git")
def test_the_fingerprint_survives_a_python_whose_stdout_turns_newlines_into_crlf(
    tmp_path: Path,
) -> None:
    """Windows 原生 python.exe 的文字模式 stdout 會把 `\\n` 譯成 `\\r\\n`；bash 的 `$(…)` 只剝
    `\\n`，CR 黏進指紋 ⇒ 被「只認十六進位」的判準當垃圾丟成 unknown，樹身分白白失去。

    所以指紋那一行不得輸出換行（`print(..., end="")`）。mac／Linux 的直譯器不譯換行，這個
    回歸只有 Windows 才看得到——這裡用墊片重現該行為，並以控制組證明替身確實會輸出 CRLF
    （否則下面的斷言對任何實作都成立）。
    """
    script = _tree_sandbox(tmp_path)
    shim = tmp_path / ".venv" / "crlf_stdout_shim.py"
    shim.write_text(_CRLF_STDOUT_SHIM, encoding="utf-8", newline="\n")
    exe = Path(sys.executable).as_posix()
    _stub_fingerprint_python(tmp_path, f'exec "{exe}" "{shim.as_posix()}" "$@"')
    # 控制組也走 `_BASH` 載具：替身是 `#!/bin/sh` 腳本，直接當 argv[0] 執行只有 POSIX 的
    # execve 認得 shebang；Windows 的 CreateProcess 回 WinError 193（不是有效的 Win32 應用
    # 程式）——本檔其餘測試全部經 `_run_sh`（bash 絕對路徑）跑替身，唯獨這一行例外。
    control = subprocess.run(
        [str(_BASH), (tmp_path / ".venv" / "bin" / "python").as_posix(), "-c",
         "import hashlib; print(hashlib.sha256(b'').hexdigest()[:12])"],
        capture_output=True, timeout=30,
    )
    assert control.stdout.endswith(b"\r\n"), f"控制組失敗：替身沒輸出 CRLF：{control.stdout!r}"
    _run_sh(script)
    log = _nightly_log(tmp_path)
    assert re.search(r"tree_fingerprint=[0-9a-f]{12} head=", log), (
        f"指紋被換行弄壞（CR 黏進欄位）或被降成 unknown：{log!r}"
    )
    assert "\r" not in log, "log 裡不該出現 CR——指紋那一行不得輸出換行"


@_POSIX_ONLY
@pytest.mark.usefixtures("hermetic_git")
def test_tree_identity_is_read_only_the_git_index_stays_byte_identical(tmp_path: Path) -> None:
    """唯讀鎖：凌晨取樣不得與使用者同時進行的 git 操作搶 index.lock。

    `git status` 在 stat 資訊過期時會順手改寫 index（要取 index.lock）；只有
    GIT_OPTIONAL_LOCKS=0 才不會。構造：撥動一支 tracked 檔的 mtime（內容不變）⇒ stat-dirty。
    控制組（腳本跑完後的一次裸 `git status`）證明這個構造確實會讓 index 被改寫，否則
    「位元組相同」的斷言對任何實作都成立。
    """
    script = _tree_sandbox(tmp_path)
    touched = tmp_path / ".gitignore"
    st = touched.stat()
    os.utime(touched, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    index = tmp_path / ".git" / "index"
    before = index.read_bytes()
    _run_sh(script)
    assert "SAMPLE VALIDITY: tree_state=clean" in _nightly_log(tmp_path), "前提：沙箱應已取樣"
    assert index.read_bytes() == before, "樹身分取樣改寫了 git index——它不是唯讀的"
    _git(tmp_path, "status", "--porcelain")
    assert index.read_bytes() != before, "控制組失敗：裸 git status 沒改寫 index，構造無效"


def test_nightly_anchor_is_the_fifth_stage_and_runs_after_sdd_ci_gate(sh_content: str) -> None:
    """寫回 ONBOARDING 的 stage 必須排最後：樣本效度戳記在所有 stage 之前取完，寫回才不會
    汙染本輪樣本；直譯器用 `$PY` 絕對路徑、不得退回裸 python（DEF-200-506）。"""
    code = _code_only(sh_content)
    assert re.search(r"^STAGE_TOTAL=5\b", code, re.M), "stage 分母單一定義點必須是 5"
    i4 = code.index("run_stage 4 sdd_ci_gate")
    m5 = re.search(
        r'run_stage 5 nightly_anchor\s+"\$PY" "\$ROOT/tools/refresh_nightly_anchor\.py" --write',
        code)
    assert m5 and m5.start() > i4, "第 5 個 stage 必須存在且排在 sdd_ci_gate 之後"
    call = re.search(r"^print_tree_identity$", code, re.M)
    assert call and call.start() < i4, "樣本效度取樣必須先於所有 stage"
