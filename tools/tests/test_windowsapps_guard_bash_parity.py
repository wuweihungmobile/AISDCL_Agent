#!/usr/bin/env python3
"""WindowsApps 空殼排除 guard — bash 側對稱實作收斂鎖（R43 Scan-B，DEF-101-353）。

背景：`tools/lib/WindowsAppsGuard.ps1::Test-IsRealPython`（R37 抽出）與
`bootstrap_core.py::_is_windows_apps_stub`（Python 側）皆只涵蓋各自語言的
呼叫端，repo 內另有多支 tracked bash 腳本（含 `tools/git-hooks/pre-push` 這個
每次 push 都會實際執行的 dispatcher 本體）各自用裸 `command -v python`／
`command -v python3` 判斷可用性，從未排除 Windows Store App Execution Alias
空殼——Git Bash on Windows 會繼承 Windows PATH，同樣會命中
`%LOCALAPPDATA%\\Microsoft\\WindowsApps` 底下系統自動註冊的空殼
`python.exe`/`python3.exe`（`command -v` 判定為「存在」，實際執行只會跳出
Microsoft Store 安裝提示，對 `pre-push` 這類阻斷式 hook 而言即為掛起）。

本檔比照既有 `test_windowsapps_guard_cross_consistency.py`（.ps1 側）的兩段式
結構鎖住 bash 側對稱實作：
  ① 共用函式本身的行為測試：以真實 subprocess 建構假 PATH 目錄（真直譯器 stub /
     WindowsApps 路徑 stub / 不存在），驗證 `is_real_python_candidate` 判斷邏輯。
  ② 存在性檢查：所有已知呼叫端須 dot-source 共用檔案並改用
     `is_real_python_candidate`，不得殘留繞過共用函式的裸 `command -v python`／
     `command -v python3` 判斷。

`_has_ssot_guard`（判斷一段 `.sh` 內文是否已正確接上共用 guard）沿革：R46 一審
只判斷「兩關鍵字是否曾出現在文字中」，QA 二審 bug-injection 揪出可被「no-op
前綴＋尾隨註解」／「一般尾隨註解」／「純文字提及」三種手法繞過，改為
`_strip_bash_comment`（剝離不在引號內的 `#` 註解）+ `_SOURCE`/`_CALL` 陳述式位置
錨定正則（`_has_real_source_statement`／`_has_real_call_statement`）；Architect
三審再揪出兩者排除純訊息輸出指令行（`_PRINT_COMMAND_RE`）的保護不對稱並補齊；
`TestHasSsotGuardBypassResistance` 對這三種繞過手法各自構造專屬回歸測試。

方法論邊界（誠實記載，非本檔涵蓋範圍——R46 QA 三審 bug-injection 揪出，比照
`AISDLC_SDD/scripts/component_sanitizer_callsite_scan.py` 同款 Rule 2 比例原則
不強修的先例）：`_has_ssot_guard` 是逐行文字掃描 + 位置錨定正則，不是真正的
bash 語法解析，因此對下列兩種刻意構造的偽裝手法無鑑別力：
  - heredoc（`cat <<'EOF' ... EOF`）內把兩個關鍵字包成「使用範例」說明文字，
    真正選 `PY` 的邏輯改用裸 `command -v python`——逐行掃描看不出 heredoc
    邊界，會把說明文字誤判為真陳述式。
  - 把 `is_real_python_candidate` 包進一個語法正確、但整檔從未被呼叫的死
    函式裡（source 行是真的）——本檔不做可達性分析，無法分辨「定義了」與
    「真的被呼叫到」。
  這兩種繞過會讓 `_has_ssot_guard` 誤判為已收斂，但風險有界：對已知白名單
  呼叫端（`_CALLER_FILES`），`test_no_raw_unguarded_python_check_remains`
  是另一支**不依賴** `_has_ssot_guard` 的獨立安全網（直接對這些檔案做裸
  `command -v python >/dev/null` 字面值 regex 比對），不受此限制影響；只有
  repo-wide 防增生掃描（`test_repo_wide_scan_finds_no_unmigrated_sh_scripts`／
  `test_repo_wide_scan_finds_no_zero_guard_python_calls`，鎖定「未知的新檔案」）
  對這兩種刻意構造的偽裝手法會失明。徹底解決需要真正的 bash 語法解析（含
  heredoc 邊界追蹤與基本可達性分析），複雜度遠超本檔工具定位，留待出現真實
  呼叫點再評估。

執行：python -m pytest tools/tests/test_windowsapps_guard_bash_parity.py -v
"""
from __future__ import annotations

import functools
import re
import subprocess
import sys
import unittest
from pathlib import Path, PurePosixPath

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GUARD_SH = _REPO_ROOT / "tools" / "lib" / "windowsapps_guard.sh"

sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import sdd_latest  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
# 🔴 R80 S5-03：本檔原有一份 `_bash_exe()`，檔頭逐字宣稱它是「各消費者獨立重寫執行
# 邏輯」的架構慣例。當回合實測推翻該慣例對本站點的適用性：全庫七份「找可用 bash」
# 中，本檔這份與 `test_windowsapps_guard_cross_consistency.py` 那份是同一段程式碼的
# 兩份手抄，而**兩份已經漂移**——本檔寫 `except Exception`、對面寫 `except OSError`。
# 差別不是風格：`subprocess.TimeoutExpired` 繼承 `SubprocessError` 而**不是** `OSError`，
# 所以候選一旦卡住，`except OSError` 那份會讓例外逸出、整個 module import 期炸掉，
# 另一份則會安靜換下一個候選。也就是說「獨立重寫」在這裡沒有換到任何鑑別力，
# 換到的是兩種不同的失敗模式，而且沒有任何一支測試在比對它們。
# 量測見 `docs/06_quality/CrossPlatform_R80_Subtraction_Evidence.md` S5-03 節。
from _platform_helpers import usable_bash_for_fixture as _bash_exe  # noqa: E402


def _latest_sdd_version_name() -> str:
    """LATEST 版本名（sdd_version.py SSOT；解析失敗即 AssertionError）。委派
    tools/lib/sdd_latest.py 單一真相源（ADR-XPLAT-002 Phase 2-C，R66 收斂）。

    R56：定義位置上移至 `_CALLER_FILES` 之前——該清單內的 LATEST 版呼叫端須以
    本函式動態組出路徑（原寫死 `AISDLC_SDD_v0.30`），不得再有第二種版本解析方式。
    """
    return sdd_latest.resolve_latest_name(_REPO_ROOT / "AISDLC_SDD")


# LATEST 版 SDD 根目錄（模組載入期求值；解析失敗即 fail-loud，不靜默縮面）。
_LATEST_SDD_ROOT = _REPO_ROOT / "AISDLC_SDD" / _latest_sdd_version_name()

# 目前已知呼叫端（皆已改用 is_real_python_candidate；DEF-101-353 收斂範圍）。
# 🔴 本清單不得手動維護到「以為對」為止：`test_caller_files_matches_repo_wide_scan`
# 會以全庫掃描機械斷言本清單恰等於實況（R43 記 9 支、R55 訂為 12 支、R56 實測
# 15 支——連續三輪人工重數皆錯，故改由機械求值，新增／移除呼叫端時該鎖會指名
# 差集要求同步）。
_CALLER_FILES = [
    _REPO_ROOT / "tools" / "git-hooks" / "pre-push",
    # R82 新增：根層 pre-commit 的**機密外洩閘第二層**（內容掃描）需要一個真 python
    # 去跑 tools/lib/secret_scan.py，故它也成了本 SSOT 的呼叫端。此前根層 pre-commit
    # 完全不碰 python（純 bash），是本輪才長出來的呼叫點。
    _REPO_ROOT / "tools" / "git-hooks" / "pre-commit",
    _REPO_ROOT / "tools" / "lib" / "git_hooks_install_common.sh",
    _REPO_ROOT / "tools" / "dev_start.sh",
    _REPO_ROOT / "tools" / "bootstrap.sh",
    _REPO_ROOT / "tools" / "integration_gate.sh",
    _REPO_ROOT / "AutoClaude" / "tools" / "local_ci_gate.sh",
    _REPO_ROOT / "AutoClaude" / "tools" / "run_act.sh",
    _REPO_ROOT / "AutoClaude" / "tools" / "sd06_w3_staging_dryrun.sh",
    _REPO_ROOT / "AISDLC_SDD" / "scripts" / "ci-gate.sh",
    # R46 新增：AutoClaude 專屬 git hooks——先前完全繞過本 SSOT（DEF-101-381），
    # 因無副檔名而連 repo-wide `*.sh` 掃描本身都看不到，見
    # `_tracked_extensionless_hook_files()` 對此方法論盲區的補強。
    _REPO_ROOT / "AutoClaude" / "tools" / "git-hooks" / "pre-commit",
    _REPO_ROOT / "AutoClaude" / "tools" / "git-hooks" / "pre-push",
    # R55 新增：原登記於 _EXEMPT_SH_FILES，豁免理由「WindowsApps 資料夾不可能
    # 出現在 macOS PATH 上」論證方向錯誤——真正風險是本腳本是否會被跑在
    # Windows 上，而腳本自身檔頭（[2b] 段落註解、`-c core.longpaths=true`
    # 註解）與根層 ONBOARDING.md 皆記載過 Windows Git Bash 實跑情境，已改用
    # 共用 guard。
    _REPO_ROOT / "tools" / "macos_smoke_local.sh",
    # R56 新增：三支「早已收斂、只是從未登記」的呼叫端（實測 grep 全庫命中 15 支、
    # 本清單只有 12 支）。未登記的代價＝不受 `test_all_known_callers_source_shared_guard`
    # 與 `test_no_raw_unguarded_python_check_remains` 兩道白名單斷言保護，只剩
    # repo-wide 前瞻掃描這層（該層對「已收斂→退化為裸判斷」有鑑別力，但對本檔
    # docstring 記載的兩種偽裝手法失明）。補登記不需改任何 shell 程式碼。
    # 後兩筆一律以 `_LATEST_SDD_ROOT`（sdd_version.py SSOT 動態解析）組出，不可
    # 寫死版本目錄名——R56 訂正：初版寫死 `AISDLC_SDD_v0.30`，與
    # `test_caller_files_matches_repo_wide_scan` 實掃側的動態解析結構性不對稱，
    # 下一次 Copy-on-Evolve 建 v0.31 時 v0.30 淪為凍結版被實掃排除 →
    # `declared - actual` 出現這兩筆而打紅 CI，且 LATEST 新版的同名呼叫端反而
    # 脫離三道白名單斷言保護。
    _REPO_ROOT / "AISDLC_SDD" / "scripts" / "copy_on_evolve.sh",
    _LATEST_SDD_ROOT / "tools" / "arch_fitness" / "run_self_evolution.sh",
    _LATEST_SDD_ROOT / "tools" / "install_hooks" / "install_post_commit.sh",
    # R65（ADR-XPLAT-002 §5 Phase 2-A）：run_tlc.sh 由委派 java/TLC 呼叫的實作
    # 改寫為委派 tools.fsm_runtime.tlc_runner 的薄殼，新增裸 python 探測，已改用
    # 共用 guard（`is_real_python_candidate`）而非獨立重寫。
    _LATEST_SDD_ROOT / "tools" / "fsm_runtime" / "formal" / "run_tlc.sh",
]

# 裸 `command -v python`／`command -v python3` 可用性判斷殘留偵測——只認本 repo
# 既有慣例「重導向 /dev/null 作為條件判斷」的用法（`command -v python >/dev/null`），
# 不誤判註解文字或純資訊性 `$(command -v python)` 顯示用途（如 dev_start.sh 成功
# 訊息內嵌已解析路徑，非可用性判斷、不繞過 guard）。
_RAW_CHECK_RE = re.compile(r"command\s+-v\s+python3?\s*>\s*/dev/null")

# 較寬鬆的裸判斷偵測（供 repo-wide 前瞻掃描用，逐行比對、跳過註解行；涵蓋
# `command -v python || command -v python3 || true` 這類無 `>/dev/null` 的變體，
# 這是 install_post_commit.sh／run_local_nightly.sh 等實際存在的寫法，
# _RAW_CHECK_RE 的窄比對抓不到）。
_LOOSE_RAW_CHECK_RE = re.compile(r"command\s+-v\s+python3?\b")

# R43 二審 Architect 一審複查揪出：TestBashCallersEnrollment 原本只驗證固定
# 白名單（_CALLER_FILES），不是真正的 repo-wide 前瞻鎖——同一類「防增生鎖只
# 蓋到已知案例」缺陷（R41 對 _sanitize_component 呼叫點也犯過一次）。改為對
# git-tracked 全部 `*.sh` 做前瞻掃描；下列為明確判斷「WindowsApps 空殼排除
# guard 不適用」而豁免的檔案，皆附理由，供未來覆核：
# R56 修正（SA／SD 各自獨立回報同一根因）：本集合的豁免理由一律須**自足**證明
# 「該腳本不存在 Windows 執行情境」。禁止以「同上一筆」或「某平台 PATH 上不會有
# WindowsApps」作為唯一依據——後者已於 R55 被判定論證方向錯誤（見下方
# `_CALLER_FILES` 內 macos_smoke_local.sh 那一筆的 R55 註解：只證明「本平台 PATH
# 乾淨」不足以豁免，必須另證「本腳本無 Windows 執行情境」），該筆亦因此被移出本
# 集合。此告示存在的理由：同一錯誤論證已被複製兩次。
_EXEMPT_SH_FILES = {
    # macOS 專屬 nightly 薄聚合器（docstring 明文「bash 3.2（macOS /bin/bash）」+
    # Windows 對等品是完全獨立的 run_local_nightly.ps1）→ 結構性只在 macOS 執行，
    # Windows Store App Execution Alias 空殼是 Windows 原生 PATH 專屬機制，不會
    # 出現在 macOS PATH 上。（R56 訂正：原寫「同上理由豁免」，但 R55 已把被指涉
    # 的前一筆 macos_smoke_local.sh 移出本集合，理由句成為懸空引用。）
    "AutoClaude/tools/run_local_nightly.sh",
    # R44 Architect 深度架構評估新增：本檔docstring 第 2 行明文「由
    # tools/run_local_nightly.ps1 透過 `docker run python:3.11-slim bash
    # /workspace/tools/run_mutmut_in_docker.sh` 呼叫」——結構性只在 Linux
    # container 內執行（官方 python:3.11-slim image 為 base，python3 保證存在於
    # 該映像檔），Windows Store App Execution Alias 空殼是 Windows 原生 PATH
    # 專屬機制，Linux container 內不可能出現；且本腳本無任何 Windows 直接執行
    # 情境——唯一呼叫端是 run_local_nightly.ps1 的 `docker run`，宿主端只負責啟
    # 容器、腳本本體始終在容器內跑。
    # （R56 訂正：原文結尾援引「同 macos_smoke_local.sh／run_local_nightly.sh 的
    # 『非 Windows 執行環境』豁免精神」，但 macos_smoke_local.sh 已於 R55 因該論證
    # 方向錯誤被移出本集合、成為懸空且已被否決的先例引用。改為上述自足論證：
    # 前半證「容器內 PATH 不可能有 WindowsApps」，後半證「無 Windows 執行情境」，
    # 後者才是本集合的真正判準。）
    "AutoClaude/tools/run_mutmut_in_docker.sh",
}


def _has_unmigrated_raw_check(text: str) -> bool:
    """純函式（供直接單元測試）：判斷一段 `.sh` 內文是否仍殘留未收斂的裸
    `command -v python`/`python3` 判斷。「已收斂」定義為同時含
    `windowsapps_guard.sh`（source）與 `is_real_python_candidate`（實際呼叫）；
    只有 source 行、沒有任何呼叫（如被局部退化改回裸判斷）不算已收斂
    （R43 三審 QA bug-injection 揪出，訂正二審初版「只要有 source 行就整檔
    豁免」的鑑別力缺口）。R46 QA 一審修正：改呼叫 `_has_ssot_guard`（要求兩個
    關鍵字皆出現在非註解行），消滅原本此處內嵌的純子字串比對重複邏輯，同時
    修掉「guard 區塊被整段 `#` 注釋掉但文字仍在」會被誤判為已收斂的漏洞。"""
    if _has_ssot_guard(text):
        return False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if _LOOSE_RAW_CHECK_RE.search(line):
            return True
    return False


def _tracked_sh_files() -> list[str]:
    """git tracked 的全部 `*.sh` repo-relative 路徑（含子專案），比照既有
    `test_windowsapps_guard_cross_consistency.py::_tracked_files` 慣例，用
    `git ls-files` 而非 `Path.rglob`（天然排除 `.git`/`.venv`/`__pycache__`）。"""
    proc = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "-c", "core.quotePath=false",
         "ls-files", "--", "*.sh"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"git ls-files 失敗（rc={proc.returncode}；stderr={proc.stderr.strip()!r}）"
            "——掃描邊界不得靜默縮小"
        )
    return [line for line in proc.stdout.splitlines() if line]


# 檔頭 shebang 是否指向某種 shell（`#!/usr/bin/env bash`／`#!/bin/sh`／`#!/bin/zsh`
# …）。判定方式比照 `tools/tests/test_bash32_compat.py::_iter_scripts` 的既有慣例
# （git hook 依慣例無副檔名，只能看檔頭），但**掃描面**不同：那支仍是固定樹名冊，
# 本檔改為全庫推導（見 `_tracked_non_sh_shell_scripts`）。
_SHELL_SHEBANG_RE = re.compile(r"^#!.*\b(?:ba|z|da|k)?sh\b")

# 🔴 R67 B4：已知的 hooks 目錄「快照」——**不是掃描面來源**（掃描面已改為全庫推導，
# 見下方兩個函式），而是給 `test_hook_dir_roster_matches_repo_state` 當完整性自檢的
# 對照基準：repo 長出第 4 個 hooks 目錄時要有人**當場知道**（新目錄的 hook 是否已
# 接進根層 dispatcher 的扇出段？是否走了 Copy-on-Evolve 該排除？），而不是靜默被
# 涵蓋。順序無意義，比對走 set。
_KNOWN_HOOK_DIRS: frozenset[str] = frozenset({
    "tools/git-hooks",
    "AutoClaude/tools/git-hooks",
    "AISDLC_SDD/.githooks",
})


@functools.lru_cache(maxsize=1)
def _tracked_files() -> tuple[str, ...]:
    """git tracked 的**全部**檔案（repo-relative）。快取一次供全庫推導使用。"""
    proc = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "-c", "core.quotePath=false", "ls-files"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"git ls-files 失敗（rc={proc.returncode}；stderr={proc.stderr.strip()!r}）"
            "——掃描邊界不得靜默縮小"
        )
    return tuple(line for line in proc.stdout.splitlines() if line)


@functools.lru_cache(maxsize=1)
def _tracked_non_sh_shell_scripts() -> tuple[str, ...]:
    """git tracked、**非 `*.sh` 但檔頭 shebang 指向 shell** 的檔案（repo-relative）。

    🔴 R67 B4（本函式的存在理由，取代原本的硬編目錄名冊）：git hook 依慣例沒有
    副檔名，`_tracked_sh_files()`（`git ls-files -- "*.sh"`）天生掃不到——那是
    DEF-101-381 的根因。R46 補的第一版用 `git ls-files -- tools/git-hooks/*
    AutoClaude/tools/git-hooks/* AISDLC_SDD/.githooks/*` 三個**寫死的目錄**補洞，
    於是掃描面本身變成一份人工名冊：本 monorepo 的 hooks 目錄數已從 1 長到 3，
    第 4 個（新子專案／`.husky/`／Copy-on-Evolve 新版樹自帶 hooks）是可預期的
    演進，而屆時在該目錄放一支裸 `command -v python` 的 hook，**全部 29 支測試
    仍全綠、零訊號**（R67 實測：連根層 1139 支 unittest 也全數逃過）——正是
    R60 對 `tools/_script_scan_surface.py` 治過的「名冊沒有完整性鎖」同一個病，
    只是換了一條腿。

    改法：不再問「有哪些 hooks 目錄」，改問「repo 裡有哪些 shell 腳本」——以
    `git ls-files` 全庫逐檔讀檔頭 shebang 推導。名冊消失，掃描面即與 repo 實況
    同步，第 4 個目錄自動落入掃描。只讀前 128 bytes（二進位檔不會被整檔載入）。

    涵蓋面不縮：R67 實測本函式在乾淨樹回傳的 6 支與舊名冊版逐字相同（三個 hooks
    目錄下的 tracked 檔案恰好全是 bash hook，無 `.md`/`.ps1` 需要排除）。
    """
    hits: list[str] = []
    for rel in _tracked_files():
        if rel.endswith(".sh"):
            continue  # 已由 `_tracked_sh_files()` 涵蓋
        try:
            with (_REPO_ROOT / rel).open("rb") as fh:
                head = fh.read(128)
        except OSError:
            continue
        first_line = head.split(b"\n", 1)[0].decode("utf-8", errors="replace")
        if _SHELL_SHEBANG_RE.match(first_line):
            hits.append(rel)
    return tuple(hits)


def _tracked_extensionless_hook_files() -> list[str]:
    """既有三個呼叫端的相容外殼——內容自 R67 起改由 `_tracked_non_sh_shell_scripts()`
    全庫推導（見該函式的 R67 B4 說明），不再有硬編目錄名冊。"""
    return list(_tracked_non_sh_shell_scripts())


# 注：`_latest_sdd_version_name()` 定義於本檔前段（`_CALLER_FILES` 之前），
# 因該清單的 LATEST 版條目須在模組載入期即以其動態組出路徑（R56）。
#
# R66 ADR-XPLAT-002 Phase 2-D 收斂（DEF-101-624）：`_FROZEN_SDD_VERSION_RE` 與
# 本函式本體改委派 tools/lib/sdd_latest.py 單一真相源（同批收斂另四份複本，見
# tools/tests/test_windows_forbidden_filename_parity.py 檔內 R59/R66 沿革註解）。


def _exclude_frozen_sdd_versions(paths: list[str], latest_name: str) -> list[str]:
    """排除 AISDLC_SDD 凍結版本（v0.01 ~ 除 LATEST 以外者）——凍結版依鐵律
    (CLAUDE.md「Copy-on-Evolve」慣例) 不應被新規則追殺歷史快照。R44 新增：
    `run_self_evolution.sh` 等模板檔案透過 Copy-on-Evolve 逐字複製進每個凍結
    版本，若不排除，新掃描會把 29 份歷史快照全部誤判為新缺口。"""
    return sdd_latest.exclude_frozen_sdd_versions(paths, latest_name)


def _strip_bash_comment(line: str) -> str:
    """去除該行的 bash 註解部分（第一個「不在引號內」的 `#` 之後全部視為註解）。
    R46 QA 二審 bug-injection 揪出：R46 一審版只判斷「整行是否以 `#` 開頭」，
    抓不到 `: # 真代碼` 這種 no-op 前綴＋尾隨註解，或 `真代碼  # 提及關鍵字`
    這種一般尾隨註解——這兩種寫法整行都不是以 `#` 開頭，卻讓關鍵字實際上只活在
    註解裡。逐字元掃描並追蹤單／雙引號狀態，只在引號外才承認 `#` 起始註解。"""
    in_single = in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i]
    return line


# 排除純訊息輸出指令（echo/printf/print）——`windowsapps_guard.sh` 若只出現在
# 這類指令的字串引數裡，是「印出來的文字」而非「真正的 source 目標」（R46 QA
# 二審 bug-injection 揪出：`echo "reminder: source windowsapps_guard.sh ..."`
# 這種純文字提及）。不要求 dot-source 與檔名字面值在同一行——本 repo 存在
# 「先賦值到變數、稍後才 dot-source 該變數」的合法間接寫法（如
# `install_post_commit.sh` 的降級回退設計：`GUARD_SRC="...windowsapps_guard.sh"`
# 接著 `. "$GUARD_SRC"`），且複雜的 command-substitution 路徑（如
# `sd06_w3_staging_dryrun.sh` 用 `$(cd "$(dirname ...)" && pwd)/.../
# windowsapps_guard.sh`）本身就含空白字元，無法用單一行的緊鄰 token 比對。
_PRINT_COMMAND_RE = re.compile(r"^\s*(?:echo|printf|print)\b")

# 要求 is_real_python_candidate 出現在陳述式起始位置：行首、`;`、`&&`、`||` 之後，
# 可選 `if`/`elif` 與可選 `!` 否定——涵蓋本 repo 全部既有真實呼叫語法（含
# `if ! is_real_python_candidate ...`／`is_real_python_candidate ... || {...}`／
# `elif is_real_python_candidate ...`），但排除任意包含該子字串的位置（如 echo
# 字串內的純文字提及，R46 QA 二審 bug-injection 揪出）。
#
# 🔴 R69 P2：SSOT 的**入口函式**由一個變成兩個——`pick_python_ge_min`（挑 >= 3.11
# 直譯器的候選鏈）同樣定義在 `tools/lib/windowsapps_guard.sh`、內部**逐個候選**
# 呼叫 `is_real_python_candidate`，故呼叫它與直接呼叫 `is_real_python_candidate`
# 對「有沒有繞過空殼 guard」是等價的（強度不變，不是放寬：兩個名字都只存在於
# SSOT 一份實作裡，自行內嵌判斷式的檔案照樣抓得到）。同時補上 `$(` 前綴——候選
# 鏈函式的回傳值走 stdout，呼叫端寫法必然是 `py="$(pick_python_ge_min)"`，
# 舊的四種陳述式起始錨點涵蓋不到。
_SSOT_ENTRYPOINTS = r"(?:is_real_python_candidate|pick_python_ge_min)"
_CALL_STATEMENT_RE = re.compile(
    r"(?:^\s*|;\s*|&&\s*|\|\|\s*|\$\(\s*)(?:if\s+|elif\s+)?!?\s*" + _SSOT_ENTRYPOINTS + r"\b"
)


def _has_real_source_statement(text: str) -> bool:
    """檔案內是否有一個非註解、非純訊息輸出的行提及 `windowsapps_guard.sh`
    （涵蓋直接 dot-source 與先賦值到變數的間接寫法，見上方常數註解），排除
    「純粹印出訊息文字剛好含這個檔名」這種偽裝。"""
    for raw_line in text.splitlines():
        line = _strip_bash_comment(raw_line)
        if _PRINT_COMMAND_RE.match(line):
            continue
        if "windowsapps_guard.sh" in line:
            return True
    return False


def _has_real_call_statement(text: str) -> bool:
    """檔案內是否有一行「真正」呼叫 is_real_python_candidate（非純文字提及/
    註解），要求該識別字出現在陳述式起始位置而非任意包含該子字串的位置。

    R46 Architect 三審揪出的不對稱修正：本函式原本沒有比照孿生函式
    `_has_real_source_statement` 排除純訊息輸出指令行（`echo`/`printf`），導致
    `echo "usage: run this; if is_real_python_candidate python; then use it"`
    這類說明文字裡的分號會被 `_CALL_STATEMENT_RE` 的 `;` 錨點誤判為陳述式邊界
    （regex 不理解字串引號語意）。改為整行是 echo/printf 時直接跳過，不管其
    引數內容是否恰好含符合位置錨定樣式的文字。"""
    for raw_line in text.splitlines():
        line = _strip_bash_comment(raw_line)
        if _PRINT_COMMAND_RE.match(line):
            continue
        if _CALL_STATEMENT_RE.search(line):
            return True
    return False


def _has_ssot_guard(text: str) -> bool:
    """R44 抽出：與 `_has_unmigrated_raw_check` 開頭判斷同義，供
    `_has_zero_guard_python_call` 共用。R46 一審修正：兩個關鍵字皆須出現在
    非整行註解行；R46 二審再修正（QA bug-injection 揪出一審版仍可被「no-op
    前綴＋尾隨註解」「一般尾隨註解」「純文字提及」三種手法繞過）：改用
    `_has_real_source_statement`／`_has_real_call_statement`，要求陳述式出現在
    正確的語法位置（見兩者 docstring），並正確剝離不在引號內的 `#` 註解
    （`_strip_bash_comment`），而非只判斷整行是否以 `#` 開頭。"""
    return _has_real_source_statement(text) and _has_real_call_statement(text)


def _has_any_raw_availability_check(text: str) -> bool:
    """檔案是否**存在**（非「已收斂」）裸 `command -v python`/`python3` 判斷
    ——不管有沒有搭配 SSOT。逐行跳過註解，比對 `_LOOSE_RAW_CHECK_RE`。"""
    for line in text.splitlines():
        if line.strip().startswith("#"):
            continue
        if _LOOSE_RAW_CHECK_RE.search(line):
            return True
    return False


_BARE_PYTHON_WORD_RE = re.compile(r"\bpython3?\b")


def _invokes_python_bare(text: str) -> bool:
    """檔案是否有呼叫 python/python3 的痕跡（逐行掃描、跳過整行註解）。刻意
    採寬鬆的全字匹配（不要求特定呼叫語法）——R44 目標形狀本身就包含
    `copy_on_evolve.sh` 這種透過變數預設值間接呼叫（`_PY="${PYTHON:-python}"`）
    的寫法，比對呼叫語法反而會漏放此類間接呼叫。"""
    for line in text.splitlines():
        if line.strip().startswith("#"):
            continue
        if _BARE_PYTHON_WORD_RE.search(line):
            return True
    return False


def _has_zero_guard_python_call(text: str) -> bool:
    """R44 Architect 深度架構評估找到的系統性缺口：既有
    `_has_unmigrated_raw_check` 只認得『有做可用性判斷（command -v）但沒有
    SSOT guard』這一種繞過形狀（如殘留 `command -v python >/dev/null` 卻沒
    source guard 檔），完全抓不到『整支檔案從頭到尾根本沒有任何 python 可用性
    判斷、直接裸呼叫 python』這種更原始也更危險的形狀（如
    `run_self_evolution.sh` 只檢查 `command -v claude`、`copy_on_evolve.sh`
    完全不檢查就呼叫 `"${_PY}"`）——WindowsApps 空殼會被直接呼叫執行，連
    『找不到就報錯』這道最基本防線都沒有。

    判準：非 SSOT 已收斂（`_has_ssot_guard`）、且非既有『有裸判斷但無 SSOT』
    形狀（`_has_any_raw_availability_check`，那是 `_has_unmigrated_raw_check`
    既有測試涵蓋的範圍，不重複計）、且確實呼叫 python/python3
    （`_invokes_python_bare`）者，才視為本形狀的新缺口。"""
    if _has_ssot_guard(text):
        return False
    if _has_any_raw_availability_check(text):
        return False
    return _invokes_python_bare(text)


@unittest.skipUnless(_bash_exe(), "本機找不到 bash，略過 shell 行為驗證")
class TestSharedGuardShellFunctionBehavior(unittest.TestCase):
    """實際以 subprocess 執行共用函式，驗證三種情境判斷正確。

    fixture 的暫存目錄與候選可執行檔全部由 **bash 自身**的 `mktemp -d` 建立，
    不透過 Python `tempfile` 產生 Windows 樣式路徑（`C:\\Users\\...`）字面塞進
    `$PATH`——R43 實測發現 `C:/...` 這類含磁碟機代號冒號的路徑塞進以 `:` 分隔的
    `$PATH` 字串會被冒號本身腰斬（`C` 與 `/Users/...` 誤判為兩個獨立、皆不存在
    的路徑片段），導致 fixture 目錄從未真正被搜尋到、`command -v python` 悄悄
    改為命中繼承自呼叫端行程環境的其他 `python`（如已啟用的 `.venv`），使本測試
    看似「跑過」卻完全沒驗證到目標邏輯——與本輪（R43 baseline agent）在真實
    `test_bash_probe_spec_contract.py` 上踩到的路徑格式陷阱同一根因類別。"""

    def _run(self, subdir_name: str, candidate: str = "python") -> bool:
        script = (
            'set -e\n'
            'tmp="$(mktemp -d)"\n'
            'trap \'rm -rf "$tmp"\' EXIT\n'
            f'mkdir -p "$tmp/{subdir_name}"\n'
            f'cat > "$tmp/{subdir_name}/python" <<\'EOS\'\n'
            '#!/usr/bin/env bash\n'
            'echo real\n'
            'EOS\n'
            f'chmod +x "$tmp/{subdir_name}/python"\n'
            f'PATH="$tmp/{subdir_name}:$PATH"\n'
            f'. "{_GUARD_SH.as_posix()}"\n'
            f'is_real_python_candidate {candidate}\n'
        )
        r = subprocess.run(
            [_bash_exe(), "-c", script],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        return r.returncode == 0

    def test_missing_candidate_rejected(self) -> None:
        """候選名稱在 PATH 上根本不存在 → 必須判否。

        🔴 R80 S5-07：本類原有 5 支，其餘 4 支（真候選接受／`WindowsApps` 空殼拒絕／
        `WINDOWSAPPS` 大小寫變體拒絕／`MyWindowsAppsBackup` 子字串誘餌接受）已刪——
        它們問的都是**路徑段判準**，而那件事已被
        `test_windowsapps_guard_cross_consistency.py::_VERDICT_CASES` 這張 11 列樣本表
        **嚴格覆蓋且更嚴**：該表把同一個暫存樣本檔同時餵給四份實作（`windowsapps_guard.sh`
        即本檔測的那一份、`WindowsAppsGuard.ps1`、`bootstrap_core.py`、以及 PS 呼叫端），
        逐列比對四方判定是否一致。逐案對照——
          · 「真直譯器路徑」`C:\\Python311\\python.exe`（expected_stub=False）承接「真候選接受」；
          · 反斜線／正斜線／混用分隔符／MSYS 掛載路徑共 6 列（expected_stub=True）承接
            「`WindowsApps` 空殼拒絕」，且多守住本類**從未測過**的分隔符變體；
          · 「大小寫變體」`…\\WINDOWSAPPS\\python.exe` 承接大小寫那支；
          · 「誘餌：子字串非完整段」`C:\\Users\\me\\MyWindowsAppsBackup\\python.exe` 承接誘餌
            那支，樣本連目錄名都逐字相同。
        本支**不刪**，因為它問的是另一件事：`command -v` 找不到候選時的行為。那條路徑
        一次都沒有被 `_VERDICT_CASES` 走到（那張表餵的是既有路徑字串，不做 PATH 查找）。
        """
        self.assertFalse(self._run("real", candidate="totally_nonexistent_xyz"))


class TestHasUnmigratedRawCheck(unittest.TestCase):
    """R43 三審 QA bug-injection 揪出的鑑別力缺口回歸鎖：直接對 `_has_unmigrated_raw_check`
    純函式單元測試「已 migrate 但被局部退化」情境（source 行還在、呼叫被整段
    改回裸判斷），確認不再被誤判為已收斂。"""

    def test_fully_unmigrated_file_is_flagged(self) -> None:
        text = 'command -v python >/dev/null 2>&1 || echo missing\n'
        self.assertTrue(_has_unmigrated_raw_check(text))

    def test_properly_migrated_file_is_not_flagged(self) -> None:
        text = (
            '. "$root/tools/lib/windowsapps_guard.sh"\n'
            'if is_real_python_candidate python; then PY=python; fi\n'
        )
        self.assertFalse(_has_unmigrated_raw_check(text))

    def test_migrated_with_fallback_branch_is_not_flagged(self) -> None:
        """install_post_commit.sh 這類「guard 檔缺席時降級回退裸判斷」的合法設計
        不應被誤判為未收斂（fallback 分支本身就是刻意保留的裸 command -v）。"""
        text = (
            'GUARD_SRC="$MAIN_CHECKOUT_ROOT/tools/lib/windowsapps_guard.sh"\n'
            'if [ -f "$GUARD_SRC" ]; then\n'
            '  . "$GUARD_SRC"\n'
            '  is_real_python_candidate python && PY=python\n'
            'else\n'
            '  PY="$(command -v python || command -v python3 || true)"\n'
            'fi\n'
        )
        self.assertFalse(_has_unmigrated_raw_check(text))

    def test_sourced_but_never_called_is_flagged(self) -> None:
        """R43 三審 QA 揪出的真實鑑別力缺口：source 行還在，但呼叫端已被整段改回
        裸判斷（如遭局部退化/regression）——舊版「只要含 windowsapps_guard.sh 字串
        就整檔豁免」會誤放行，本測試鎖住訂正後的行為。"""
        text = (
            '. "$root/tools/lib/windowsapps_guard.sh"\n'
            'if command -v python >/dev/null 2>&1; then PY=python; fi\n'
        )
        self.assertTrue(_has_unmigrated_raw_check(text))

    def test_comment_only_mention_is_not_flagged(self) -> None:
        text = '# 比照 tools/integration_gate.sh 的 command -v python 判斷慣例\n'
        self.assertFalse(_has_unmigrated_raw_check(text))


class TestHasZeroGuardPythonCall(unittest.TestCase):
    """R44 Architect 深度架構評估新增的鑑別力回歸鎖：直接對
    `_has_zero_guard_python_call` 純函式單元測試各種情境，確認它只認『完全
    沒有任何可用性判斷卻直接呼叫 python』這一種形狀，不與既有
    `_has_unmigrated_raw_check` 涵蓋的『有裸判斷但無 SSOT』形狀重疊誤判。"""

    def test_fully_unguarded_bare_call_is_flagged(self) -> None:
        text = 'python -c "import json,sys;print(1)"\n'
        self.assertTrue(_has_zero_guard_python_call(text))

    def test_variable_default_indirection_is_flagged(self) -> None:
        """`copy_on_evolve.sh` 的真實形狀：透過 `${PYTHON:-python}` 預設值間接
        呼叫，全程沒有任何 command -v／SSOT 判斷。"""
        text = (
            '_PY="${PYTHON:-python}"\n'
            '"${_PY}" "$SCRIPT_DIR/foo.py" --write\n'
        )
        self.assertTrue(_has_zero_guard_python_call(text))

    def test_file_with_raw_check_but_no_ssot_is_not_flagged_by_this_helper(self) -> None:
        """有裸 `command -v python` 判斷（即使沒有 SSOT）屬於既有
        `_has_unmigrated_raw_check` 測試涵蓋的形狀，本 helper 不應重複計。"""
        text = 'command -v python >/dev/null 2>&1 || echo missing\n'
        self.assertFalse(_has_zero_guard_python_call(text))

    def test_ssot_guarded_file_is_not_flagged(self) -> None:
        text = (
            '. "$root/tools/lib/windowsapps_guard.sh"\n'
            'if is_real_python_candidate python; then PY=python; fi\n'
        )
        self.assertFalse(_has_zero_guard_python_call(text))

    def test_no_python_mention_at_all_is_not_flagged(self) -> None:
        self.assertFalse(_has_zero_guard_python_call('echo hello\ncommand -v git\n'))

    def test_comment_only_mention_is_not_flagged(self) -> None:
        text = '# 見 tools/dev_start.py，此處無需直接呼叫 python\n'
        self.assertFalse(_has_zero_guard_python_call(text))


class TestHasSsotGuardBypassResistance(unittest.TestCase):
    """R46 Architect 三審要求：直接針對 `_has_ssot_guard`/`_strip_bash_comment`
    構造 R46 QA 二審揪出的三種繞過手法之專屬回歸測試，鎖住這幾個函式本身的
    鑑別力（不能只靠既有整合性測試如 `test_all_known_callers_source_shared_guard`
    間接覆蓋——那類測試對「這幾個新函式被局部退化」是否有鑑別力並不直接）。"""

    _REAL_GUARD = (
        '. "$ROOT/../tools/lib/windowsapps_guard.sh"\n'
        'if is_real_python_candidate python; then PY=python; fi\n'
    )

    def test_real_guard_is_recognized(self) -> None:
        """正向對照組：真正生效的 guard 必須判定為已收斂。"""
        self.assertTrue(_has_ssot_guard(self._REAL_GUARD))

    def test_noop_prefix_with_trailing_comment_is_not_recognized(self) -> None:
        """R46 QA 二審繞過①：`: #` no-op 前綴＋尾隨註解，整行不以 `#` 開頭
        （`strip().startswith("#")` 判斷會誤放行），但兩行實際上完全是註解。"""
        text = (
            ': # . "$ROOT/../tools/lib/windowsapps_guard.sh"\n'
            ': # if is_real_python_candidate python; then\n'
        )
        self.assertFalse(_has_ssot_guard(text))

    def test_trailing_comment_after_real_code_is_not_recognized(self) -> None:
        """R46 QA 二審繞過②：一般尾隨註解——真正執行的程式碼是裸
        `command -v python`（未收斂），關鍵字只出現在該行的尾隨註解裡。"""
        text = 'command -v python >/dev/null 2>&1  # windowsapps_guard.sh is_real_python_candidate (disabled)\n'
        self.assertFalse(_has_ssot_guard(text))

    def test_echo_pure_mention_is_not_recognized(self) -> None:
        """R46 QA 二審繞過③：純文字提及——整行是 `echo` 訊息輸出，關鍵字只是
        被印出的說明文字，不是真正的 source/呼叫陳述式。"""
        text = (
            'echo "reminder: source windowsapps_guard.sh and call '
            'is_real_python_candidate before use"\n'
        )
        self.assertFalse(_has_ssot_guard(text))

    def test_echo_mention_inside_call_statement_position_is_not_recognized(self) -> None:
        """R46 Architect 三審揪出的不對稱繞過：echo 說明文字裡剛好含分號，讓
        `_CALL_STATEMENT_RE` 的 `;` 錨點在字串內部誤判為陳述式邊界。"""
        text = 'echo "usage: run this; if is_real_python_candidate python; then use it"\n'
        self.assertFalse(_has_ssot_guard(text))

    def test_indirect_variable_assignment_is_still_recognized(self) -> None:
        """正向對照組（防止修復矯枉過正）：先賦值到變數、稍後才 dot-source 該
        變數的合法降級回退寫法（`install_post_commit.sh` 既有設計）仍須判定為
        已收斂。"""
        text = (
            'GUARD_SRC="$MAIN_CHECKOUT_ROOT/tools/lib/windowsapps_guard.sh"\n'
            'if [ -f "$GUARD_SRC" ]; then\n'
            '  . "$GUARD_SRC"\n'
            '  is_real_python_candidate python && PY=python\n'
            'fi\n'
        )
        self.assertTrue(_has_ssot_guard(text))

    def test_complex_command_substitution_path_is_still_recognized(self) -> None:
        """正向對照組：複雜 command-substitution 路徑（含空白字元，
        `sd06_w3_staging_dryrun.sh` 既有寫法）仍須判定為已收斂。"""
        text = (
            '. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)'
            '/../../tools/lib/windowsapps_guard.sh"\n'
            'is_real_python_candidate python || { echo err; exit 1; }\n'
        )
        self.assertTrue(_has_ssot_guard(text))


class TestHookDirRosterIntegrity(unittest.TestCase):
    """🔴 R67 B4：無副檔名那條腿的**完整性自檢**（掃描面自己也要被掃）。

    WHY（這不是文件潔癖，是 R60 治過的同一個病）：`_tracked_extensionless_hook_files()`
    在 R46~R66 是硬編 3 個目錄名冊，於是「防增生鎖」本身有一塊只有人工記憶守著的
    邊界——第 4 個 hooks 目錄一出現，該目錄下的裸 `command -v python` 就完全在掃描
    面之外，29 支測試全綠、零訊號（R67 沙箱實測連根層 1139 支 unittest 也全逃過）。
    R67 已把掃描面改為全庫 shebang 推導（名冊不再參與掃描），本類別補的是另一半：
    **repo 長出名冊外的 shell 腳本／hooks 目錄時要當場 fail-loud**，讓人去確認

      ① 該目錄的 hook 是否已接進根層 dispatcher 的扇出段（`tools/git-hooks/pre-push`
         對子專案 hook 是逐一 `if [ -f ... ]` 明列扇出，新目錄不接就根本不會被執行）；
      ② 是否屬於 Copy-on-Evolve 凍結版樹（該類路徑另有 `_exclude_frozen_sdd_versions`
         的排除語意，不可與 active hooks 混為一談）。

    自檢一旦翻紅，正解是「看懂新目錄再更新 `_KNOWN_HOOK_DIRS`」，不是把斷言放寬。
    """

    def test_derived_scan_surface_is_not_silently_empty(self) -> None:
        """推導結果不得為空——空集合會讓整條無副檔名腿靜默失效（假綠），
        且與 DEF-101-381 的原始形狀完全相同（掃不到 ⇒ 永遠沒有發現）。"""
        derived = _tracked_non_sh_shell_scripts()
        self.assertGreater(
            len(derived), 0,
            "全庫推導不到任何『非 *.sh 但檔頭是 shell shebang』的 tracked 檔案——"
            "推導器壞了（git ls-files 空／shebang 正則失效），此時整條無副檔名"
            "掃描腿靜默失效，等同 DEF-101-381 未修",
        )

    def test_hook_dir_roster_matches_repo_state(self) -> None:
        """名冊 vs 實況：出現名冊外的 hooks 目錄（或名冊內目錄消失）即 fail-loud。"""
        derived_dirs = {
            str(PurePosixPath(rel).parent) for rel in _tracked_non_sh_shell_scripts()
        }
        unknown = sorted(derived_dirs - _KNOWN_HOOK_DIRS)
        vanished = sorted(_KNOWN_HOOK_DIRS - derived_dirs)
        self.assertEqual(
            unknown, [],
            f"發現 `_KNOWN_HOOK_DIRS` 名冊外的 shell 腳本目錄：{unknown}——"
            "掃描面已自動涵蓋（不必補掃描），但請人工確認：(a) 若是新的 git-hooks "
            "目錄，其 hook 是否已接進 tools/git-hooks/* dispatcher 的扇出段？"
            "(b) 該目錄下的腳本是否已改用 is_real_python_candidate？"
            "確認後把目錄補進 `_KNOWN_HOOK_DIRS`",
        )
        self.assertEqual(
            vanished, [],
            f"`_KNOWN_HOOK_DIRS` 內的目錄已推導不到任何 shell 腳本：{vanished}——"
            "可能是目錄被移除／改名（請同步名冊），也可能是該目錄下的 hook 檔頭 "
            "shebang 被改掉而**靜默退出掃描面**（那才是要修的東西）",
        )

    def test_known_hook_dirs_exist_on_disk(self) -> None:
        """名冊條目必須是真實存在的目錄——寫錯字的條目會讓上面的比對永遠有一筆
        `vanished` 或永遠對不上，是另一種靜默腐化。"""
        for rel in sorted(_KNOWN_HOOK_DIRS):
            with self.subTest(hook_dir=rel):
                self.assertTrue(
                    (_REPO_ROOT / rel).is_dir(), f"`_KNOWN_HOOK_DIRS` 條目不存在：{rel}"
                )


class TestBashCallersEnrollment(unittest.TestCase):
    """所有已知呼叫端須改用共用函式，且不得殘留繞過它的裸 command -v 判斷。"""

    def test_shared_guard_file_exists_and_defines_the_function(self) -> None:
        self.assertTrue(_GUARD_SH.is_file(), f"{_GUARD_SH} 不存在")
        text = _GUARD_SH.read_text(encoding="utf-8")
        self.assertIn(
            "is_real_python_candidate()", text,
            "tools/lib/windowsapps_guard.sh 未定義 is_real_python_candidate 共用函式",
        )
        self.assertIn("WindowsApps", text)

    def test_all_known_callers_source_shared_guard(self) -> None:
        """R46 QA 一審 bug-injection 揪出：原本用兩個獨立 `assertIn` 純子字串比對，
        把整段 guard 區塊（source 行 + 呼叫行）逐行加 `#` 注釋掉後兩個子字串仍在
        檔案文字中，測試完全不會轉紅（看似鎖住存在性、實際只鎖到「字串曾經出現
        過」）。改用 `_has_ssot_guard`（要求兩關鍵字皆出現在非註解行）。"""
        for f in _CALLER_FILES:
            with self.subTest(file=str(f.relative_to(_REPO_ROOT))):
                self.assertTrue(f.is_file(), f"{f} 不存在")
                text = f.read_text(encoding="utf-8")
                self.assertTrue(
                    _has_ssot_guard(text),
                    f"{f} 未在非註解行同時 dot-source 共用 guard 檔案並呼叫 "
                    "is_real_python_candidate 判斷 python 可用性（或該區塊已被注釋掉）",
                )

    def test_caller_files_matches_repo_wide_scan(self) -> None:
        """R56 新增（三名審查員各自獨立回報同一根因）：`_CALLER_FILES` 是人工
        維護的白名單，歷輪計數 R43 記 9 支、R55 花一整項（DEF-101-428）訂為
        12 支、R56 實測 15 支——「每輪人工重數、每輪都數錯」。單純再把 12 改成
        15 只會讓同形狀漂移在下一輪復發，故本鎖改為機械求值：以全庫 git-tracked
        bash 檔（排除 AISDLC_SDD 凍結版與 SSOT 自身）掃出「真正接上共用 guard」
        （`_has_ssot_guard`）的集合，斷言其恰等於 `_CALLER_FILES`。

        未登記的代價（為何這不只是文件潔癖）：落單呼叫端不受
        `test_all_known_callers_source_shared_guard` 與
        `test_no_raw_unguarded_python_check_remains` 兩道白名單斷言保護，只剩
        repo-wide 前瞻掃描一層——而本檔 docstring 已明文記載該層對 heredoc 偽裝
        與死函式兩種手法失明。

        LATEST 版演進（Copy-on-Evolve 產生新版路徑）不會使本鎖翻紅——清單側的
        LATEST 版條目與本鎖的實掃側同走 `_latest_sdd_version_name()`（R56 訂正：
        初版清單側寫死 `AISDLC_SDD_v0.30`，兩側解析方式不對稱，建新版即打紅
        CI）。真正會翻紅的只有「呼叫端新增／移除／退化為裸判斷而清單未同步」，
        那是刻意的 fail-loud。此模式與 .ps1 側既有
        `test_known_call_sites_still_exist` 同源。"""
        latest_name = _latest_sdd_version_name()
        ssot_rel = str(_GUARD_SH.relative_to(_REPO_ROOT)).replace("\\", "/")
        scoped = _exclude_frozen_sdd_versions(
            _tracked_sh_files() + _tracked_extensionless_hook_files(), latest_name
        )
        actual: set[str] = set()
        for rel in scoped:
            if rel == ssot_rel:
                continue
            path = _REPO_ROOT / rel
            if not path.is_file():
                continue
            if _has_ssot_guard(path.read_text(encoding="utf-8", errors="replace")):
                actual.add(rel)
        declared = {str(f.relative_to(_REPO_ROOT)).replace("\\", "/") for f in _CALLER_FILES}
        # R56 防復發（立即訊號，不等到下次 Copy-on-Evolve 才炸）：清單側若出現
        # 非 LATEST 的版本目錄字面值，即代表又寫死了版本路徑——建新版當下才翻紅
        # 的鎖等於把成本轉嫁給建版者，此處提前擋。
        frozen_declared = sorted(
            rel for rel in declared
            if (m := sdd_latest.FROZEN_SDD_PATH_PREFIX_RE.match(rel)) and m.group(1) != latest_name
        )
        self.assertEqual(
            frozen_declared, [],
            f"_CALLER_FILES 出現非 LATEST（{latest_name}）的版本目錄字面值："
            f"{frozen_declared}——LATEST 版條目一律用 `_LATEST_SDD_ROOT` 組出，"
            f"寫死版本名會在下一次 Copy-on-Evolve 建版時打紅本鎖",
        )
        self.assertEqual(
            actual, declared,
            f"_CALLER_FILES 與全庫實掃不符——實掃有、清單無（請補登記）："
            f"{sorted(actual - declared)}；清單有、實掃無（已移除／改名／退化，"
            f"或 AISDLC_SDD LATEST 版已演進需改寫路徑）：{sorted(declared - actual)}",
        )

    def test_no_raw_unguarded_python_check_remains(self) -> None:
        for f in _CALLER_FILES:
            with self.subTest(file=str(f.relative_to(_REPO_ROOT))):
                text = f.read_text(encoding="utf-8")
                hits = _RAW_CHECK_RE.findall(text)
                self.assertEqual(
                    hits, [],
                    f"{f} 殘留繞過共用 guard 的裸 `command -v python`/`python3` 判斷：{hits}",
                )

    def test_repo_wide_scan_finds_no_unmigrated_sh_scripts(self) -> None:
        """R43 二審 Architect 一審複查揪出的真實系統性缺口：本類別原本只驗證固定
        白名單 `_CALLER_FILES`，本身就是「防增生鎖只蓋到已知案例」——Architect 用
        全 repo grep 實測找到 3 支未列入清單、仍是裸判斷的既有 tracked 腳本
        （`tools/macos_smoke_local.sh`／`AutoClaude/tools/run_local_nightly.sh`／
        `AISDLC_SDD/AISDLC_SDD_v0.30/tools/install_hooks/install_post_commit.sh`）。
        本測試改為對 git-tracked 全部 `*.sh` 做前瞻掃描：逐行跳過註解，命中裸
        `command -v python`/`python3` 判斷、且該檔案既不在 `_CALLER_FILES`（已收斂）
        也不在 `_EXEMPT_SH_FILES`（明確記載豁免理由）者視為未收斂新缺口。

        R43 三審 QA 用 bug-injection 揪出的鑑別力缺口（訂正二審初版）：原本只要
        檔案內文字含有 `"windowsapps_guard.sh"` 字串（即有 source 這一行）就整檔
        跳過，不管該檔是否仍殘留裸判斷——「已 migrate 但被局部退化」（source 行
        還在、但呼叫端改回裸判斷）的情境會被誤放行。改為要求同時含
        `is_real_python_candidate`（實際呼叫共用函式）才視為已收斂，只 source
        不呼叫（或呼叫被整段刪掉、只留 source 行）不再豁免。"""
        known_relpaths = {str(f.relative_to(_REPO_ROOT)).replace("\\", "/") for f in _CALLER_FILES}
        unmigrated: list[str] = []
        scanned = _tracked_sh_files() + _tracked_extensionless_hook_files()
        for rel in scanned:
            if rel in known_relpaths or rel in _EXEMPT_SH_FILES:
                continue
            path = _REPO_ROOT / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if _has_unmigrated_raw_check(text):
                unmigrated.append(rel)
        self.assertEqual(
            unmigrated, [],
            f"發現未收斂的裸 python 可用性判斷（未 source windowsapps_guard.sh 且未登記"
            f"豁免）：{unmigrated}——請改用 is_real_python_candidate 或於 "
            f"_EXEMPT_SH_FILES 附理由登記豁免",
        )

    def test_repo_wide_scan_finds_no_zero_guard_python_calls(self) -> None:
        """R44 Architect 深度架構評估找到的系統性缺口：上一測試
        （`test_repo_wide_scan_finds_no_unmigrated_sh_scripts`）與 .ps1 側對應
        測試都只認得『有做可用性判斷（command -v / Get-Command）但沒有
        dot-source SSOT guard』這一種繞過形狀，完全抓不到『整支檔案從頭到尾
        根本沒有任何 python 可用性判斷、直接裸呼叫 python』這種更原始也更
        危險的形狀。本測試 repo-wide 掃描全部 git-tracked `*.sh`（排除
        AISDLC_SDD 凍結版本目錄 AISDLC_SDD_v0.01~v0.29，只掃 LATEST 演化版與
        其餘 monorepo 檔案——凍結版依 Copy-on-Evolve 鐵律不回改），找出符合
        此形狀的檔案。

        已知真實命中（本輪稍後步驟修復，本測試只建立/驗證掃描鎖本身）：
        `AISDLC_SDD/AISDLC_SDD_v0.30/tools/arch_fitness/run_self_evolution.sh`
        （只檢查 `command -v claude`，從未檢查 python 本身）與
        `AISDLC_SDD/scripts/copy_on_evolve.sh`（透過 `${PYTHON:-python}` 預設值
        間接呼叫，全程零檢查）。
        """
        latest_name = _latest_sdd_version_name()
        known_relpaths = {str(f.relative_to(_REPO_ROOT)).replace("\\", "/") for f in _CALLER_FILES}
        # R69 P2：SSOT 自己也要跳過（比照姊妹掃描 `test_caller_files_matches_
        # repo_wide_scan` 早就有的 `if rel == ssot_rel: continue`）——本檔內的
        # `pick_python_ge_min` 候選鏈含 `python3.11` 等字面值 ⇒ 會被
        # `_invokes_python_bare` 判為「呼叫 python」，而 `_has_ssot_guard` 要求檔案
        # 內有 source `windowsapps_guard.sh` 的陳述式，SSOT 不可能 source 自己 ⇒
        # 結構性偽陽性。判準本身（「非 SSOT 檔案不得零 guard 呼叫 python」）不變。
        ssot_rel = str(_GUARD_SH.relative_to(_REPO_ROOT)).replace("\\", "/")
        scoped = _exclude_frozen_sdd_versions(
            _tracked_sh_files() + _tracked_extensionless_hook_files(), latest_name
        )

        unmigrated: list[str] = []
        for rel in scoped:
            if rel == ssot_rel or rel in known_relpaths or rel in _EXEMPT_SH_FILES:
                continue
            path = _REPO_ROOT / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if _has_zero_guard_python_call(text):
                unmigrated.append(rel)

        self.assertEqual(
            unmigrated, [],
            f"發現完全沒有任何 python 可用性判斷（既無 SSOT guard 也無裸 "
            f"command -v 判斷）卻直接呼叫 python/python3 的檔案：{unmigrated}"
            f"——請改用 is_real_python_candidate（source tools/lib/"
            f"windowsapps_guard.sh），或於 _EXEMPT_SH_FILES 附理由登記豁免",
        )


if __name__ == "__main__":
    unittest.main()
