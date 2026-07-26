#!/usr/bin/env python3
"""GitHub Actions 版本跨 workflow 一致性機械守護（R55，DEF-101-420/424 缺口收斂）。

為何存在：R54 round 1（DEF-101-420）與 round 2（DEF-101-424）連續兩輪都是靠人工
grep 逐檔比對才發現 `actions/checkout`／`actions/setup-python`／
`actions/upload-artifact`／`actions/github-script` 四個常用 action 在 11 支
workflow 間的版本落差，且 round 1 對 `github-script@v7`「已是穩定版」的自我宣稱
本身在 round 2 被證明失準——顯示這類多站點版本宣稱單靠人工複核不可靠，與本
repo 對「多站點宣稱同類問題」一律建機械鎖的既有慣例（pytest 基線有
`check_pytest_baseline_sites.py`、CI paths 覆蓋有
`test_ci_paths_cover_root_consumers.py`）不對稱。

判準：同一 action 名稱（`actions/checkout` 等）在全部 `.github/workflows/*.yml`
與 `*.yaml` 內的 `uses:` 版本字串必須唯一；出現兩種以上版本即 fail-loud 列出每個
`file:line` 對應版本，不嘗試判斷「哪個版本才是對的」（那是人工升版決策，不是
機械鎖的職責——機械鎖只保證「未來任一輪只改單一 workflow 檔的版本、或新增
第 N+1 支 workflow 沿用舊版本」時會立刻發紅，不會重演連兩輪靠人工才發現落差
的模式）。

只掃描本檔 `_TRACKED_ACTIONS` 登記的四個 action 名稱（與本輪四方複審四筆
finding 對應的候選範圍一致）；其餘 action（如 `actions/cache`）目前 repo 內
無跨檔版本宣稱歷史事故，暫不納入——與 `check_script_parity.py` 只鎖已知問題
類別、不做無邊界軍備競賽的比例原則一致，未來若其他 action 也發生跨檔漂移，
擴充 `_TRACKED_ACTIONS` 即可，不需改動比對邏輯。

使用：
  python3 tools/check_gha_action_versions.py   # 於 repo 內任意 cwd；不一致印清單並 exit 1
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOWS_DIR = _REPO_ROOT / ".github" / "workflows"

# 本輪四方複審 finding 對應的四個 action——R54 round 1/2 實際發生跨檔版本落差
# 判斷失準的對象。
_TRACKED_ACTIONS = ("checkout", "setup-python", "upload-artifact", "github-script")

_USES_RE = re.compile(
    r"uses:\s*actions/(" + "|".join(re.escape(a) for a in _TRACKED_ACTIONS) + r")@(v\S+)"
)


def _strip_yaml_comment(line: str) -> str:
    """去除該行的 YAML 註解部分（第一個「不在引號內」的 `#` 之後全部視為註解）。
    與 `test_windowsapps_guard_bash_parity.py::_strip_bash_comment` 同款逐字元
    引號狀態追蹤手法（YAML 同樣以單／雙引號界定字串、`#` 起始註解），避免
    `# uses: actions/checkout@v4`（被暫時註解掉的舊版本行）被誤判為現行宣告。"""
    in_single = in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i]
    return line


def scan(workflows_dir: Path) -> dict[str, dict[str, list[str]]]:
    """回傳 {action名: {版本: [file:line, ...]}}。抽出為獨立函式（非 main 內嵌）
    以便單元測試以 fixture 目錄注入，不依賴真實 repo 現況（比照既有
    `check_pytest_baseline_sites.py::scan` 同款慣例）。file:line 一律以
    `workflows_dir` 的**父目錄**為基準相對化，讓 fixture 測試與正式掃描輸出
    格式一致（皆為 `.github/workflows/xxx.yml:N` 樣式的相對路徑）。掃描
    `*.yml` 與 `*.yaml` 兩種副檔名（GitHub Actions 官方文件皆合法且等效），
    避免掃描邊界靜默縮小到只涵蓋本 repo 現況恰好全用的 `.yml`。"""
    findings: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    base = workflows_dir.parent.parent  # <root>/.github/workflows → <root>
    paths = sorted(set(workflows_dir.glob("*.yml")) | set(workflows_dir.glob("*.yaml")))
    for path in paths:
        try:
            rel = path.relative_to(base).as_posix()
        except ValueError:
            rel = path.name
        text = path.read_text(encoding="utf-8")
        for lineno, raw_line in enumerate(text.splitlines(), start=1):
            line = _strip_yaml_comment(raw_line)
            m = _USES_RE.search(line)
            if not m:
                continue
            action, version = m.group(1), m.group(2)
            findings[action][version].append(f"{rel}:{lineno}")
    return findings


def main() -> int:
    if not _WORKFLOWS_DIR.is_dir():
        print(f"❌ 找不到 workflows 目錄：{_WORKFLOWS_DIR}", file=sys.stderr)
        return 1

    findings = scan(_WORKFLOWS_DIR)
    ok = True
    total_files = 0
    for action in _TRACKED_ACTIONS:
        versions = findings.get(action)
        if not versions:
            continue  # 該 action 本 repo 未使用——非缺陷
        if len(versions) > 1:
            ok = False
            print(f"❌ actions/{action} 版本不一致：發現 {len(versions)} 種版本", file=sys.stderr)
            for version, sites in sorted(versions.items()):
                print(f"  {version}：", file=sys.stderr)
                for site in sites:
                    print(f"    - {site}", file=sys.stderr)
        else:
            (version, sites), = versions.items()
            total_files += len(sites)
            print(f"✅ actions/{action}@{version}：{len(sites)} 處一致")

    if not ok:
        print(
            "\n❌ GitHub Actions 版本一致性檢查未通過 — 同一 action 在不同 "
            "workflow 內必須釘同一版本（見上列 file:line）",
            file=sys.stderr,
        )
        return 1
    print(f"\n✅ GitHub Actions 版本一致性檢查通過（{len(_TRACKED_ACTIONS)} 個追蹤 action，"
          f"共 {total_files} 處 uses: 宣告皆同名同版）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
