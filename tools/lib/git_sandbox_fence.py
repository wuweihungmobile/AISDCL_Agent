"""全套測試期間讓「新建」的沙盒 git repo 一出生就關掉背景自動維護（DEF-200-648）。

WHY（真實事故）：macOS CI run 45427135743 attempt 2，`test_openitems_gate` 在暫存 repo `git commit`
之後，git 依預設啟動 detached `git maintenance run --auto`／`gc --auto`；teardown 的 `rmtree`
與它競速，撞上 `.git/objects/maintenance.lock` 而 FileNotFoundError。單點修法
（`test_openitems_gate._git` 帶 `-c maintenance.auto=false -c gc.auto=0`）只救一個 helper；
`tools/tests` 另有約 55 處 `["git", "-C", …]` 子行程、46 處 `init` 站點，每處自帶一份 `-c`
就是把同一件事抄 55 次，下一個新站點照樣漏。

為什麼是 `GIT_TEMPLATE_DIR`、不是 `GIT_CONFIG_COUNT`／`KEY_n`／`VALUE_n`（實測否決）：
SelfImproving 的推送守門（`tools/lib/selfimproving/pushcontent.py`、`git.py::ENV_RULES`）把
行程環境裡**任何** `GIT_CONFIG_*` 視為設定注入、一律拒絕；全套級的環境變數若是 `GIT_CONFIG_COUNT`，
那一族測試會整批改判成拒絕。模板目錄的 `config` 檔則在 `git init`／`git clone` 當下被複製成新
repo 的 `.git/config`——之後無論哪個 helper、帶不帶 `-c`，該 repo 的所有 git 指令都吃得到，
而且 SelfImproving 的環境審查不認得這個變數（實測：經 `GIT_TEMPLATE_DIR` 建出的 repo
`git config --get maintenance.auto` 為 `false`）。

誠實劃界：①只涵蓋「經 runner 起跑」的執行（pre-push／nightly／三支 CI 都走
`tools/run_root_unittests.py`）；單檔直跑 `python -m unittest` 不受圍籬、行為與修前相同。
②只管**新建**的 repo；測試若複製既有 `.git`（不經 init／clone）則不涵蓋。③自訂模板會取代 git
預設模板，故本模組先把預設模板（`<exec-path>/../../share/git-core/templates`）整份複製進來，
找不到預設模板時只缺 `.git/hooks/*.sample` 等範例檔，不影響行為。呼叫端自己已設的
`GIT_TEMPLATE_DIR` 優先當底、不被吞掉。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

TEMPLATE_ENV = "GIT_TEMPLATE_DIR"
#: 寫進模板 `config` 的內容：兩個鍵都要關（`gc.auto` 管 `gc --auto`；`maintenance.auto` 管
#: git 2.29+ 在 commit 之後起的 detached `maintenance run --auto`）。
QUIET_CONFIG = "[maintenance]\n\tauto = false\n[gc]\n\tauto = 0\n"


def _default_template_dir() -> Path | None:
    """git 內建預設模板目錄；解析不到回 None（不猜路徑）。"""
    try:
        cp = subprocess.run(
            ["git", "--exec-path"], capture_output=True, encoding="utf-8", errors="replace",
            timeout=30, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return None
    if cp.returncode != 0 or not cp.stdout.strip():
        return None
    cand = Path(cp.stdout.strip()).parent.parent / "share" / "git-core" / "templates"
    return cand if cand.is_dir() else None


def build_template(dest: Path, inherited: str | None = None) -> Path:
    """在 `dest` 組一份模板：底＝呼叫端自設的模板，否則 git 預設模板；再附上關閉維護的 `config`。"""
    base = Path(inherited) if inherited and Path(inherited).is_dir() else _default_template_dir()
    if base is not None:
        shutil.copytree(base, dest, dirs_exist_ok=True)
    dest.mkdir(parents=True, exist_ok=True)
    cfg = dest / "config"
    kept = cfg.read_text(encoding="utf-8") if cfg.is_file() else ""
    cfg.write_text(kept + QUIET_CONFIG, encoding="utf-8")
    return dest


def fence(run: Callable[[], int]) -> int:
    """進入前組模板並設 `GIT_TEMPLATE_DIR`，`run()` 結束後原值還原、模板刪除；回傳 `run()` 的 rc。

    與 `unattended_authz.posture_fence` 同形（runner 一行串接）：還原放 finally、不吞例外；
    設在 runner 的 `os.environ`，平行 worker 與測試生出的子行程都繼承到。
    """
    had, kept = TEMPLATE_ENV in os.environ, os.environ.get(TEMPLATE_ENV)
    tmp = Path(tempfile.mkdtemp(prefix="autosdd_git_tpl_"))
    try:
        os.environ[TEMPLATE_ENV] = str(build_template(tmp / "t", kept))
        return run()
    finally:
        if had:
            os.environ[TEMPLATE_ENV] = str(kept)
        else:
            os.environ.pop(TEMPLATE_ENV, None)
        shutil.rmtree(tmp, ignore_errors=True)
