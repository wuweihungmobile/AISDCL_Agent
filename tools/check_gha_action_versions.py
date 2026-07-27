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

掃描範圍＝全部 `actions/*` 官方 action（R56 修正，見下方 `_USES_RE` 註解：
原本的 `_TRACKED_ACTIONS` 四名白名單是 fail-open 設計，實測打錯一個字即靜默
少守 13 處宣告卻仍印綠燈）。

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

# R56 修正（三名獨立審查員各自以 bug-injection／fixture 實測揪出的三個靜默繞過）：
# 原式為 `uses:\s*actions/(checkout|setup-python|upload-artifact|github-script)@(v\S+)`，
# 有三個 fail-open 缺口，全部會讓真實版本漂移「從普查中消失」（不是判為第二種
# 版本，而是根本沒被登記），且成功訊息仍印綠燈：
#   ① 白名單列舉：清單打錯一個字（`upload-artefact`）即靜默少守 13 處宣告，
#      main() 仍 rc=0 且宣稱「4 個追蹤 action」（印的是清單長度、非實際命中數）。
#      → 改為「掃到什麼就守什麼」：凡 `actions/*` 官方 action 一律納入唯一性
#      斷言，白名單與其維護負擔一併移除（實測全 repo 只用到 4 個 action、
#      各自單一版本，改為通用規則後判定結果不變且不需再人工同步清單）。
#   ② 引號寫法：`uses: "actions/checkout@v4"`／`uses: 'actions/checkout@v4'`
#      都是合法 YAML 與合法 GHA 語法，原式要求 `uses:` 後緊接 `actions/`，
#      加引號即完全不匹配。→ 容忍可選引號並以反向參照 `\1` 定錨收尾（不可用
#      `\S+` 吃版本，否則會把收尾引號併進版本字串而產生 `v5"` vs `v5` 假不一致）。
#   ③ SHA 釘選：`actions/upload-artifact@11bd7190…`（GitHub 官方建議的供應鏈
#      硬化寫法）版本不以 `v` 開頭，原式的 `@(v\S+)` 連 action 都不會登記。
#      → 版本改收 `[^'"\s]+`。
#   ④ 子路徑 action（R56 round 2，SD 以 fixture 探針實測）：action 名字元類原為
#      `[A-Za-z0-9_.-]+`（不含 `/`），故官方文件正式提供的 `actions/cache/restore`
#      ／`actions/cache/save` 這類子路徑 action 無法在 `@` 前收尾 → 整行不匹配、
#      從普查中消失，與上方 ①②③ 病灶完全同形（且與本檔宣稱的「掃描範圍＝全部
#      `actions/*` 官方 action」自相矛盾）。→ 名稱允許 `/` 分段，仍以 `@` 定錨；
#      `cache`／`cache/restore`／`cache/save` 各自成獨立 key（正確粒度：GitHub
#      對子路徑 action 的版本是各自獨立的 ref）。
_USES_RE = re.compile(
    r"""uses:\s*(['"]?)actions/([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)@([^'"\s]+)\1"""
)

# 引號只有出現在 scalar 起始位置（行首，或空白／`:`／`,`／`[`／`{` 之後）才算
# 開啟 YAML 字串——見 `_strip_yaml_comment` docstring。
_QUOTE_OPENER_PREFIX = " \t:,[{"


def _strip_yaml_comment(line: str) -> str:
    """去除該行的 YAML 註解部分，避免 `# uses: actions/checkout@v4`（被暫時
    註解掉的舊版本行）被誤判為現行宣告。

    R56 修正：原版逐字元追蹤引號狀態的手法直接移植自
    `test_windowsapps_guard_bash_parity.py::_strip_bash_comment`，但 bash 與
    YAML 的引號語意不同——YAML plain scalar 內出現**未成對**引號完全合法
    （英文所有格 `repo's`、中文引號、`printf '%s\\n'` 這類片段），一旦出現，
    引號狀態就外溢到整行末尾，其後真實的 `#` 不再被剝除：
    `- name: Restore the repo's cache  # uses: actions/checkout@v1` 會被當成
    現行宣告而產生假紅——正是本函式自稱要防的情境的反例。改為兩條與 YAML
    實際語法對齊的判準：
      ① `#` 只有在行首或前接空白字元時才是註解起點（YAML 規格）；
      ② 引號只有在 scalar 起始位置才開啟字串狀態，字中撇號不再誤開引號。
    """
    in_single = in_double = False
    for i, ch in enumerate(line):
        at_scalar_start = i == 0 or line[i - 1] in _QUOTE_OPENER_PREFIX
        if ch == "'" and not in_double:
            in_single = False if in_single else at_scalar_start
        elif ch == '"' and not in_single:
            in_double = False if in_double else at_scalar_start
        elif (
            ch == "#"
            and not in_single
            and not in_double
            and (i == 0 or line[i - 1].isspace())
        ):
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
            action, version = m.group(2), m.group(3)
            findings[action][version].append(f"{rel}:{lineno}")
    return findings


def main() -> int:
    if not _WORKFLOWS_DIR.is_dir():
        print(f"❌ 找不到 workflows 目錄：{_WORKFLOWS_DIR}", file=sys.stderr)
        return 1

    findings = scan(_WORKFLOWS_DIR)
    if not findings:
        # R56 補：掃描面整個斷掉（glob/regex 被改壞、workflows 目錄搬家）時，
        # 舊版會印「0 個追蹤 action」並 rc=0——與本工具存在的目的直接矛盾。
        print(
            f"❌ {_WORKFLOWS_DIR} 內找不到任何 `uses: actions/…@…` 宣告 — "
            "掃描面疑似被改壞（本 repo 現況應為數十處）",
            file=sys.stderr,
        )
        return 1
    ok = True
    total_files = 0
    for action in sorted(findings):
        versions = findings[action]
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
    # R56：印「實際掃到的 action 數」而非白名單長度——舊版印 len(_TRACKED_ACTIONS)，
    # 掃描面縮小時這個數字不動，等於把唯一的人工觀測訊號也一併蒙蔽。
    print(f"\n✅ GitHub Actions 版本一致性檢查通過（{len(findings)} 個 actions/* action，"
          f"共 {total_files} 處 uses: 宣告皆同名同版）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
