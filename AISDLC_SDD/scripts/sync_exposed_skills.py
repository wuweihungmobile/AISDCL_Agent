"""對外曝光 skills SSOT 守新鮮（AutoSDD_improving — 方案 C 步驟 ②③；整合輪 116 增第二鏡像目標）。

問題
----
`AISDLC_SDD/.claude/skills`（版本無關的「對外曝光」skill 集，CC 在 AISDLC_SDD/ 下
工作時以 `AISDLC_SDD:<skill>` 曝光）是早期凍結的舊快照，與最新演化版（ci-gate
LATEST）已漂移：個別 skill 語意落後（如 sdd-gate 缺 retry_count/pattern_detection/
ESCALATION 段）、且缺數個後期新增的 runtime skill。它**不受任何機制治理**——
framework_status_snapshot.py 只計數各「版本目錄」內的 skills，從不檢查這份父層副本。

SSOT 決策
---------
對外曝光 skills 的唯一真相源 = **ci-gate LATEST 版**（複用 rfc_lifecycle_lint 磁碟掃描，
對齊 `scripts/sdd_version.py` SSOT 的 LATEST 語意；沿用磁碟掃描之 WHY——copy_on_evolve.sh
建版後新版尚未 git add 即呼叫本腳本 --write——見該檔豁免註記）。父層副本是 LATEST 的
**機械鏡像**，不手動維護（手動維護正是它今天漂移的原因）。

鏡像目標（整合輪 116／G-116-13／DEF-200-549）
---------------------------------------------
  parent      `<repo_root>/.claude/skills`（AISDLC_SDD/ 層；`AISDLC_SDD:<skill>` 前綴的來源）
  autoclaude  `<repo_root>/../AutoClaude/.claude/skills`——Claude Code 對 skills 採「最具體者優先」，在
              `AutoClaude/` 的檔案上它會壓過 `AISDLC_SDD:` 前綴；它曾是 AISDLC v0.09 的 33 支舊版（缺
              sdd-gate 等 9 支 SDD 專屬 skill），於是在 AutoClaude 的檔案上叫到的是非 SDD 版。
兩者都是 LATEST 的機械鏡像，`--check` 預設同時守兩者。`AutoClaude` 專案目錄不存在（框架被獨立
checkout）時該目標一律**略過**（`--check` 印一行說明、不紅；`--write` 不動）；目錄存在但鏡像 stale
才紅，訊息會指出修法 `--write --target autoclaude`。

用法
----
  python scripts/sync_exposed_skills.py            # --check（預設；ci-gate 硬閘，任一目標 stale 即 exit 1）
  python scripts/sync_exposed_skills.py --check --target parent
  python scripts/sync_exposed_skills.py --write     # 由 LATEST 重生全部目標（修復漂移）
  python scripts/sync_exposed_skills.py --write --target autoclaude
      # 只重生 AutoClaude 鏡像：對該目標是「整個目錄取代」（rmtree＋copytree），鏡像裡有而 LATEST 沒有的檔會被刪掉
      # （`--check` 會先把這類檔列為「多餘」，寫入前看一眼；建議收尾單人窗口做）

合規
----
本腳本與父層 `.claude/skills` 皆在版本目錄**之上**（AISDLC_SDD/ 層），不在任何凍結
`v0.0X` 本體內 → 不違反 Copy-on-Evolve；屬「shared infra，不隨 Copy-on-Evolve」
（同 framework_status_snapshot.py / rfc_lifecycle_lint.py）。AutoClaude 目標只寫該專案的
`.claude/skills` 鏡像目錄，不碰它的其他檔案。
"""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rfc_lifecycle_lint import discover_frozen_versions, latest_version  # noqa: E402

# Windows 主控台 cp950 無法輸出中文 → 對齊 sibling 腳本強制 utf-8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

_EXCLUDE_DIRS = {"__pycache__"}
_EXCLUDE_SUFFIX = (".pyc",)


def _rmtree_windows_safe(path: str, label: str = "父層") -> None:
    """Windows 韌性 rmtree（R15 SCAN-B-2）：唯讀屬性檔案會讓裸 shutil.rmtree 炸
    PermissionError 且留下半刪目錄 → 下次 copytree 再炸 FileExistsError。
    onerror 先清唯讀再重試一次（Python 3.11 尚無 3.12 的 onexc；POSIX 上與裸
    rmtree 行為等價零副作用——同 tools/tests/test_dev_start.py::_rmtree_force
    pattern）；重試仍失敗（檔案遭編輯器/防毒暫鎖）則丟出帶可讀訊息的例外，
    不留裸 traceback。`label` 只進錯誤訊息（預設 `父層` ＝舊訊息逐字不變；
    整合輪 116 起 AutoClaude 目標傳 `AutoClaude`，讓訊息指對鏡像）。
    """

    def _on_error(func, p, exc_info):  # onerror 固定簽名
        orig = exc_info[1]
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except (OSError, TypeError):
            # TypeError：Python 3.11 POSIX fd-based rmtree 的 func 可能是
            # os.open（另需 flags 參數），func(p) 重試簽名不符；連同重試仍失敗
            # 的 OSError 一律回拋「原始」錯誤，交外層轉可讀訊息（沙盒煙測實證
            # 盲目 func(p) 會讓 TypeError 逸出 except OSError）。
            raise orig from None

    try:
        shutil.rmtree(path, onerror=_on_error)
    except OSError as exc:
        raise RuntimeError(
            f"[skills-ssot] 無法刪除舊{label}鏡像：{path}（{exc}）；"
            "請關閉佔用該目錄的編輯器/防毒後重試 --write"
        ) from exc


def _skill_files(root: str) -> dict[str, bytes]:
    """收集 root 下所有檔案：relpath（正規化為 /）→ bytes。排除 __pycache__/.pyc。"""
    out: dict[str, bytes] = {}
    if not os.path.isdir(root):
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS]
        for fn in filenames:
            if fn.endswith(_EXCLUDE_SUFFIX):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            with open(full, "rb") as f:
                out[rel] = f.read()
    return out


#: 鏡像目標名（`--target` 另加 `all`）。順序即 `all` 的處理順序。
TARGETS = ("parent", "autoclaude")
#: 目標的短標籤（`--write` 的訊息與 rmtree 失敗訊息用；`parent` 與整合輪 116 之前的舊訊息逐字相同）。
_SHORT_LABEL = {"parent": "父層", "autoclaude": "AutoClaude"}


def _resolve_paths(repo_root: str) -> tuple[str, str] | None:
    """`(LATEST 版本名, LATEST 的 .claude/skills)`；找不到任何版本目錄 → None。"""
    versions = discover_frozen_versions(repo_root)
    latest = latest_version(versions)
    if latest is None:
        return None
    return latest, os.path.join(repo_root, latest, ".claude", "skills")


def _target_info(repo_root: str, name: str) -> tuple[str, str, str | None]:
    """`(鏡像目錄, 訊息用標籤, 錨目錄)`；錨目錄存在才適用該目標（None＝恆適用）。

    `autoclaude` 的錨＝`<repo_root>/../AutoClaude`：框架被獨立 checkout 時它不存在，鏡像目標就沒有
    意義（沒有一個 AutoClaude 專案會去讀它）——此時略過，而不是替一個不存在的專案造目錄。"""
    if name == "parent":
        return os.path.join(repo_root, ".claude", "skills"), "父層 .claude/skills", None
    anchor = os.path.normpath(os.path.join(repo_root, os.pardir, "AutoClaude"))
    return os.path.join(anchor, ".claude", "skills"), "AutoClaude/.claude/skills", anchor


def _selected_targets(target: str) -> tuple[str, ...]:
    return TARGETS if target == "all" else (target,)


def _fix_hint(name: str) -> str:
    # 刻意不寫裸直譯器名（根層 `tools/tests/test_windowsapps_guard_cross_consistency.py` 的
    # 「零 guard 裸 python 站點」登記表會把訊息字串裡的裸名當新站點抓）：以 repo 的 .venv 直譯器執行。
    return f"scripts/sync_exposed_skills.py --write --target {name}（以 repo 的 .venv 直譯器執行）"


def _skip_message(name: str, anchor: str) -> str:
    return f"[skills-ssot] 略過 {name} 目標：找不到 {anchor}（框架被獨立 checkout，無此子專案；不算 stale）"


def _check_one(name: str, mirror: str, label: str, latest: str, want: dict[str, bytes]) -> int:
    have = _skill_files(mirror)
    missing = sorted(set(want) - set(have))      # 鏡像缺（LATEST 有）
    extra = sorted(set(have) - set(want))        # 鏡像多（LATEST 無）
    drift = sorted(k for k in (set(want) & set(have)) if want[k] != have[k])

    if not missing and not extra and not drift:
        print(f"[skills-ssot] OK：{label} == LATEST({latest})（{len(want)} 檔一致）")
        return 0

    print(f"[skills-ssot] STALE：{label} 與 LATEST({latest}) 不一致", file=sys.stderr)
    for k in missing:
        print(f"  - 缺少（LATEST 有）：{k}", file=sys.stderr)
    for k in extra:
        print(f"  - 多餘（LATEST 無）：{k}", file=sys.stderr)
    for k in drift:
        print(f"  - 內容漂移：{k}", file=sys.stderr)
    print(f"  修復：{_fix_hint(name)}", file=sys.stderr)
    return 1


def check(repo_root: str, target: str = "all") -> int:
    resolved = _resolve_paths(repo_root)
    if resolved is None:
        print("[skills-ssot] 找不到任何 AISDLC_SDD_v0.* 版本目錄", file=sys.stderr)
        return 1
    latest, latest_skills = resolved
    want = _skill_files(latest_skills)
    if not want:
        print(f"[skills-ssot] LATEST({latest}) 無 .claude/skills 內容，無法比對", file=sys.stderr)
        return 1

    rc = 0
    for name in _selected_targets(target):
        mirror, label, anchor = _target_info(repo_root, name)
        if anchor is not None and not os.path.isdir(anchor):
            print(_skip_message(name, anchor))
            continue
        rc |= _check_one(name, mirror, label, latest, want)
    return rc


def write(repo_root: str, target: str = "all") -> int:
    resolved = _resolve_paths(repo_root)
    if resolved is None:
        print("[skills-ssot] 找不到任何 AISDLC_SDD_v0.* 版本目錄", file=sys.stderr)
        return 1
    latest, latest_skills = resolved
    if not os.path.isdir(latest_skills):
        print(f"[skills-ssot] LATEST({latest}) 無 .claude/skills，無法鏡像", file=sys.stderr)
        return 1
    for name in _selected_targets(target):
        mirror, _label, anchor = _target_info(repo_root, name)
        if anchor is not None and not os.path.isdir(anchor):
            print(_skip_message(name, anchor))
            continue
        if os.path.isdir(mirror):
            _rmtree_windows_safe(mirror, label=_SHORT_LABEL[name])
        shutil.copytree(
            latest_skills,
            mirror,
            ignore=shutil.ignore_patterns(*_EXCLUDE_DIRS, "*.pyc"),
        )
        n = len(_skill_files(mirror))
        print(f"[skills-ssot] 已由 LATEST({latest}) 重生{_SHORT_LABEL[name]}鏡像（{n} 檔）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="比對鏡像是否 stale（預設；ci-gate 硬閘）")
    parser.add_argument("--write", action="store_true", help="由 LATEST 重生鏡像（預設全部目標）")
    parser.add_argument(
        "--target",
        choices=(*TARGETS, "all"),
        default="all",
        help="鏡像目標：parent＝<repo-root>/.claude/skills；autoclaude＝<repo-root>/../AutoClaude/.claude/skills；"
             "all（預設）＝全部（AutoClaude 專案目錄不存在時該目標略過）",
    )
    parser.add_argument(
        "--repo-root",
        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        help="AISDLC_SDD/ 目錄（含各版本子目錄與 .claude/skills 父層副本）",
    )
    args = parser.parse_args(argv)
    if args.write:
        return write(args.repo_root, args.target)
    return check(args.repo_root, args.target)


if __name__ == "__main__":
    sys.exit(main())
