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

判準：同一 action 名稱（`actions/checkout` 等）在 **repo 根層** `.github/workflows/`
單層（非遞迴）的 `*.yml` 與 `*.yaml` 內的 `uses:` 版本字串必須唯一（R57 SA-R57-05
訂正：原文寫「全部 `.github/workflows/*.yml`」，措辭誇大於實際掃描面，見下方
〈掃描面邊界〉區塊的明文裁定與 `_audit_scan_surface()` 的機械守門）；出現兩種以上
版本即 fail-loud 列出每個
`file:line` 對應版本，不嘗試判斷「哪個版本才是對的」（那是人工升版決策，不是
機械鎖的職責——機械鎖只保證「未來任一輪只改單一 workflow 檔的版本、或新增
第 N+1 支 workflow 沿用舊版本」時會立刻發紅，不會重演連兩輪靠人工才發現落差
的模式）。

掃描範圍＝全部 `actions/*` 官方 action（R56 修正，見下方 `_USES_RE` 註解：
原本的 `_TRACKED_ACTIONS` 四名白名單是 fail-open 設計，實測打錯一個字即靜默
少守 13 處宣告卻仍印綠燈）。

人工升版決策紀錄（**不是**機械鎖的一部分，寫在此處是因為本檔是唯一會列舉全部
`uses:` 版本的地方；本工具只斷言唯一性、不判斷「哪版才對」）：
  - R57 C4 覆核（2026-07-27，WebSearch 查證）：`actions/upload-artifact@v5` 的
    `action.yml` 宣告 `runs.using: node20`（v5 對 Node24 只是「預備支援」、預設仍跑
    Node20），v6.0.0 才把預設改為 `node24`（並要求 runner ≥ 2.327.1，GitHub-hosted
    runner 早已滿足）。GitHub 官方時程經查證仍如帳本 DEF-101-434 所載：2026-06-16
    起 runner 預設改用 Node24、**2026-09-16 自 runner 移除 Node20**。故本輪把根層
    13 處 `upload-artifact@v5` 一次升至 `@v6`（本工具斷言同名唯一，13 處必須同動）。
    刻意不升 v7：v7 的變更是 ESM 化 + 新增 `archive:` 直傳單檔功能（預設 `true`
    向後相容），與本次要解的 Node20 問題無關；且本 repo 因 DEF-101-081 帳單問題
    連 GitHub Actions 都跑不起來、無法實測驗證，故取「剛好解決問題、行為變動最小」
    的 v6。若日後帳單恢復且需要 v7 的直傳功能再議。

使用：
  python3 tools/check_gha_action_versions.py   # 於 repo 內任意 cwd；不一致印清單並 exit 1
"""
from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cli_flags  # noqa: E402  # 未知旗標 rc=2 fail-loud 的 SSOT（見該檔檔頭 WHY）
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOWS_DIR = _REPO_ROOT / ".github" / "workflows"

# ─── 掃描面邊界（R57 SA-R57-05：整類盲區的明文裁定 + 機械守門）───────────────
# 掃描面＝**根層** `.github/workflows/` 單層。GitHub Actions 只會執行 repo 根層
# `.github/workflows/` 下的 workflow，巢狀目錄內的同名檔案永遠不會被觸發。
# 但「不會被執行」≠「已經想過要不要管」——實查本 repo 另有 30 份 git-tracked 的
# `AISDLC_SDD/AISDLC_SDD_v0.NN/.github/workflows/hub-push.yml`（30 份 md5 相同，是框架
# 各版目錄的隨版複製品，隨框架散佈給下游後才會成為對方的根層 workflow），此前從未被
# 任何掃描維度覆蓋。裁定：**不納入**本工具的跨 workflow 版本唯一性斷言，理由三點：
#   ① 它們在本 repo 內是惰性資產，本 repo 的 CI 行為完全不受其影響；
#   ② v0.01~v0.29 是凍結版快照（框架政策禁止回頭改），併入唯一性斷言會讓「根層升版」
#      與「凍結版不可改」兩條政策直接互斥、本工具將永久紅燈且無合法解法；
#   ③ LATEST（v0.30）的 action 版本屬「散佈給下游的模板品質」命題，與本工具要守的
#      「本 repo 各 workflow 版本不得互相漂移」是不同命題，混在一起會兩邊都守不好。
# ⚠️ 誠實揭露的到期風險（**R60 已完成分流，不再是懸空請求**）：那些巢狀檔實測全為
#   Node20 世代（`checkout@v4`／`setup-python@v5`／`upload-artifact@v4`；份數由
#   `nested_excluded_workflows()` 每次執行實查後印出，**刻意不在註解寫死支數**——寫死
#   即下一輪必過期，同 R57 立下的政策）。GitHub 官方時程（R60 以 WebSearch 重新查證，
#   與 R57／DEF-101-434 所載一致）：2026-06-16 runner 預設改用 Node24、**2026-09-16 自
#   runner 完全移除 Node20**（過渡期可用 `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true`
#   續用 Node20，但該旁路在移除後失效）。下游使用者複製 LATEST 模板後會踩到。
#   分流結論（R60 Scan-C C-03；延伸自 DEF-101-490／DEF-101-434，已記入
#   `docs/06_quality/AutoSDD_Defect_Log.md`）：
#     - 凍結版（`v0.01`~ 前一版）依 Copy-on-Evolve **不動**，這一點無爭議；
#     - LATEST 那份**是否**隨根層升版，本工具刻意**不代為決定**——該檔自述是「給尚未
#       存在的 Hub Registry repo 的 sample」（見其檔頭），要不要升版屬**框架散佈品質**
#       命題，擁有者是 AISDLC_SDD 凍結/LATEST 政策側，不是 CI 工具鏈側；且升 LATEST
#       會讓「各版此檔為同一 git blob」這個目前可機械核對的不變量首次分裂，代價需由
#       該側評估。
#   ⚠️→🔒 為避免本段再退化成寫一次就沒人看的孤兒揭露（C-03 的實質指控就是「承接者
#   不存在」），`_NESTED_DISCLOSED_GENERATION` 把上述「Node20 世代」這個事實宣稱升為
#   **機械斷言**：巢狀排除區的 action 版本一旦與登記快照不符（有人升了 LATEST、或新版
#   目錄帶進不同世代），本工具即紅燈並要求同步更新本段揭露與帳本狀態。也就是說，這段
#   文字從此不可能與實況靜默背離。
# 📌 複核者陷阱（R60 實測，寫下以免下一輪重蹈）：用 `md5sum` 比對這些巢狀檔會看到**兩
#   群不同雜湊**，很像「內容已分裂」的鐵證——那是本機 checkout 的 CRLF 殘留
#   （`git ls-files --eol` 顯示部分版本工作樹為 `w/crlf`）。正確的載具是
#   `git ls-files -s -- '*/.github/workflows/hub-push.yml' | awk '{print $2}' | sort -u`
#   ——實測收斂為**單一 blob**，committed 內容逐位元組相同。
# 為避免上述「排除」日後退化回「沒人想過」：`_audit_scan_surface()` 實查 git-tracked
# 檔案，凡掃描面外、又不符下列已登記排除樣式的 workflow 檔一律 fail-loud（新冒出的
# 巢狀 `.github/workflows/`——例如 AutoClaude 側日後自建一份——不會再靜默漏掉）。
_EXCLUDED_NESTED_WORKFLOW_RE = re.compile(
    r"^AISDLC_SDD/AISDLC_SDD_v0\.\d+/\.github/workflows/[^/]+\.ya?ml$"
)
_ANY_WORKFLOW_FILE_RE = re.compile(r"(?:^|/)\.github/workflows/[^/]+\.ya?ml$")

# 巢狀排除區「目前實況」的登記快照（R60 Scan-C C-03）。語意＝上方 ⚠️ 段那句
# 「實測全為 Node20 世代」的機械化身：值必須是該區**唯一**出現的版本（多版本即分裂）。
# 紅燈指路：本快照與實查不符時，正確的處置**不是**改這裡了事，而是先回答「LATEST 該不該
# 升版」（見 ⚠️ 段的分流結論與擁有者），再把答案同步進 ⚠️ 段與缺陷帳本，最後才更新本快照。
_NESTED_DISCLOSED_GENERATION = {
    "checkout": "v4",
    "setup-python": "v5",
    "upload-artifact": "v4",
}

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


def _tracked_workflow_files() -> list[str]:
    """git-tracked 的全部 workflow 檔（相對 repo 根的 POSIX 路徑，未排序）。

    R60 自 `_audit_scan_surface()` 抽出：巢狀排除區的世代稽核需要同一份清單的
    **另一半**（被排除者），抽出後兩邊共用同一次 `git ls-files`、同一組正則，
    不會出現「兩處各自維護一份 workflow 檔判準」這種本 repo 反覆吃過的漂移。
    git 不可用時 raise RuntimeError——本工具是 CI 閘門，寧可 fail-loud 也不靜默跳過。
    """
    try:
        out = subprocess.run(
            ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
            cwd=_REPO_ROOT, check=True, capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        ).stdout
    # R57 round 3：本分支已由 tools/tests/test_gha_action_versions.py
    # ::TestAuditScanSurface::test_git_unavailable_is_fail_loud_not_silent_skip
    # 覆蓋（原標 `pragma: no cover - 環境層`，已不再是無法覆蓋的環境層分支）。
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"無法以 `git ls-files` 實查掃描面邊界：{exc}") from exc
    return [rel for rel in out.split("\0") if rel and _ANY_WORKFLOW_FILE_RE.search(rel)]


def _audit_scan_surface() -> list[str]:
    """回傳「掃描面外、且未登記於明文排除樣式」的 git-tracked workflow 檔清單
    （相對 repo 根的 POSIX 路徑，已排序）。git 不可用時 raise RuntimeError。"""
    return sorted(
        rel
        for rel in _tracked_workflow_files()
        if not rel.startswith(".github/workflows/")
        and not _EXCLUDED_NESTED_WORKFLOW_RE.match(rel)
    )


def nested_excluded_workflows() -> list[str]:
    """回傳「已登記於明文排除樣式」的巢狀 workflow 檔清單（`_audit_scan_surface()`
    的補集那一半）。刻意不回傳份數常數——份數隨框架版數成長，寫死必過期。"""
    return sorted(
        rel for rel in _tracked_workflow_files() if _EXCLUDED_NESTED_WORKFLOW_RE.match(rel)
    )


def nested_action_generation(rels: list[str]) -> dict[str, set[str]]:
    """回傳巢狀排除區實測的 {action名: {版本, ...}}。

    共用 `_strip_yaml_comment()` 與 `_USES_RE`（與根層掃描同一套判準，含引號／SHA
    釘選／子路徑 action 四種形態）。git-tracked 但磁碟上不存在時 raise OSError——
    index 與工作樹不一致屬環境異常，不得靜默少讀一份而讓稽核假綠。
    """
    generation: dict[str, set[str]] = defaultdict(set)
    for rel in rels:
        path = _REPO_ROOT / rel
        if not path.is_file():
            raise OSError(f"git-tracked 但磁碟上不存在：{rel}（index 與工作樹不一致）")
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            found = _USES_RE.search(_strip_yaml_comment(raw_line))
            if found:
                generation[found.group(2)].add(found.group(3))
    return dict(generation)


def nested_generation_drift(generation: dict[str, set[str]]) -> list[str]:
    """比對實測世代 vs `_NESTED_DISCLOSED_GENERATION` 登記快照，回傳人類可讀的
    差異描述清單（空＝一致）。雙向比對：登記了卻消失、實測有卻沒登記、版本不符。"""
    problems: list[str] = []
    for action in sorted(set(_NESTED_DISCLOSED_GENERATION) | set(generation)):
        expected = _NESTED_DISCLOSED_GENERATION.get(action)
        actual = sorted(generation.get(action, ()))
        if expected is None:
            problems.append(f"actions/{action}：實測 {actual}，但登記快照未列此 action")
        elif not actual:
            problems.append(f"actions/{action}：登記快照列為 {expected}，但實測已不存在")
        elif actual != [expected]:
            problems.append(f"actions/{action}：登記快照 {expected} ≠ 實測 {actual}")
    return problems


# ─── 早退遮蔽的解藥：accumulate-then-report（本輪 H-01）──────────────────────
# 🔴 缺陷本體（端到端實測，非推論）：本檔 `main()` 原本有 7 個 `return 1`、對應 4 道
# 彼此獨立的檢查，任一道紅就當場返回。以 mock 讓第①道回報一筆未登記 workflow 後實測：
# 控制組的 7 行 stdout（含巢狀世代對帳與逐 action 一致性）**整批消失**，換成 2 行
# stderr，而沒有任何一句話告訴讀者「後面 3 道一行都沒跑」。遮蔽方向是「看起來變乾淨」
# ——讀者拿到一個短短的紅，會以為問題只有那一筆。這與 `check_defect_log_crossref.py`
# 已被治好的那個事故逐字同型（該支的鎖自陳「其他工具不在射程內」，本檔就是那句劃界
# 的另一半）。本檔是 pre-push 硬閘 ＋ root-infra-ci 的一道，且它同時守著「AISDLC_SDD
# 各版巢狀 workflow 的 Node20 到期風險」這種**只有它在看**的東西。
#
# 修法刻意選 accumulate-then-report 而不是抄 `_bail()`：本檔的四道彼此**無資料相依**
# （只有③→④ 一條），沒有理由在第一道就停手。跑得完的全部跑完、一次報完；真的因為
# 前置條件不成立而跑不了的，逐名列進「未執行」清單——**未執行 ≠ 通過**。
_CHECK_ORDER: tuple[str, ...] = (
    "①掃描面邊界稽核（git-tracked workflow 全部已納管或已明文排除）",
    "②巢狀排除區 action 世代 vs 登記快照",
    "③workflows 目錄存在且掃得到 uses: 宣告",
    "④跨 workflow 的 actions/* 版本唯一性",
)


def _report(notes: list[str], problems: list[str], unrun: list[str]) -> int:
    """把綠／紅／未執行三塊各自完整印出，最後才收斂 rc。

    順序刻意是「綠先、紅後」：紅印在最後一行附近才不會被其後十幾行綠捲走
    （原版逐 action 依字典序印，`checkout` 的紅後面接 12 行綠）。
    """
    for line in notes:
        print(line)
    for block in problems:
        print(block, file=sys.stderr)
    if unrun:
        print(
            f"\n⚠️ 尚有 {len(unrun)} 道檢查**未執行**（前置條件不成立；其結果**未知**，"
            f"不是通過）：",
            file=sys.stderr,
        )
        for name in unrun:
            print(f"    - {name}", file=sys.stderr)
    if problems:
        print(
            f"\n❌ 本工具 {len(_CHECK_ORDER)} 道檢查中有 {len(problems)} 道未通過。"
            f"上列是本次**跑得完的全部問題**（accumulate-then-report），不是第一筆——"
            f"修掉最上面那筆之後不要預期其餘會自己消失",
            file=sys.stderr,
        )
        return 1
    print(f"\n✅ GitHub Actions workflow 檢查全數通過（{len(_CHECK_ORDER)} 道）")
    return 0


def main(argv: list[str] | None = None) -> int:
    # 本工具**不接受任何引數**（`argv` 只為既有程式化呼叫端的簽章相容保留）。
    # 🔴 本層**絕不讀 `sys.argv`**——未知引數的拒收在 `cli()`，WHY 見該處。
    del argv
    notes: list[str] = []
    problems: list[str] = []
    unrun: list[str] = []

    # 只有掃描真實根層目錄時才做結構性邊界稽核；單元測試以 fixture 目錄注入
    # `_WORKFLOWS_DIR` 時跳過（那時談「repo 掃描面」沒有意義）——這是**射程外**
    # 而非「未執行」，故走 notes 不走 unrun（把它算進未執行清單會讓每次 fixture
    # 測試都印出一段假警告，警告一旦有雜訊就沒人讀）。
    if _WORKFLOWS_DIR != _REPO_ROOT / ".github" / "workflows":
        notes.append(
            f"ℹ️  _WORKFLOWS_DIR 為注入的 fixture 目錄 ⇒ {_CHECK_ORDER[0]}／"
            f"{_CHECK_ORDER[1]} 射程外（談「repo 掃描面」對 fixture 沒有意義）"
        )
    else:
        git_ok = True
        try:
            unregistered = _audit_scan_surface()
        except RuntimeError as exc:
            git_ok = False
            problems.append(f"❌ [{_CHECK_ORDER[0]}] {exc}")
        else:
            if unregistered:
                problems.append(
                    f"❌ [{_CHECK_ORDER[0]}] 發現掃描面外、未登記於排除樣式的 workflow 檔"
                    " — 請先做出納管與否的明文裁定（見本檔〈掃描面邊界〉區塊），不可讓它"
                    "退回「沒人想過」狀態：\n"
                    + "\n".join(f"    - {rel}" for rel in unregistered)
                )
        if not git_ok:
            # ②與①共用同一次 `git ls-files`：①拿不到清單時②結構上無從執行。
            unrun.append(f"{_CHECK_ORDER[1]}（前置：①的 `git ls-files` 未成功）")
        else:
            # R60 Scan-C C-03：巢狀排除區的「Node20 世代」事實宣稱由此升為機械斷言，
            # 讓 ⚠️ 段那份到期風險揭露不可能與實況靜默背離（原缺陷＝承接者不存在）。
            nested = nested_excluded_workflows()
            try:
                generation = nested_action_generation(nested)
            except OSError as exc:
                problems.append(f"❌ [{_CHECK_ORDER[1]}] 巢狀排除區世代稽核失敗：{exc}")
            else:
                drift = nested_generation_drift(generation)
                if drift:
                    problems.append(
                        f"❌ [{_CHECK_ORDER[1]}] 巢狀排除區（AISDLC_SDD 各版 "
                        ".github/workflows/）的 action 世代與本檔〈掃描面邊界〉⚠️ 段的"
                        "登記快照不符 — 請先回答「LATEST 該不該隨根層升版」（擁有者＝"
                        "AISDLC_SDD 凍結/LATEST 政策側），把答案同步進 ⚠️ 段與缺陷帳本，"
                        "最後才更新 _NESTED_DISCLOSED_GENERATION：\n"
                        + "\n".join(f"    - {p}" for p in drift)
                    )
                else:
                    gen_text = "／".join(
                        f"{a}@{_NESTED_DISCLOSED_GENERATION[a]}"
                        for a in sorted(_NESTED_DISCLOSED_GENERATION)
                    )
                    notes.append(
                        f"ℹ️  巢狀排除區實查：{len(nested)} 份 workflow，action 世代 "
                        f"{gen_text} 與登記快照一致（Node20 於 2026-09-16 自 runner "
                        f"移除，到期風險與分流結論見本檔〈掃描面邊界〉⚠️ 段）"
                    )

    if not _WORKFLOWS_DIR.is_dir():
        problems.append(f"❌ [{_CHECK_ORDER[2]}] 找不到 workflows 目錄：{_WORKFLOWS_DIR}")
        unrun.append(f"{_CHECK_ORDER[3]}（前置：③的 workflows 目錄不存在）")
        return _report(notes, problems, unrun)

    findings = scan(_WORKFLOWS_DIR)
    if not findings:
        # R56 補：掃描面整個斷掉（glob/regex 被改壞、workflows 目錄搬家）時，
        # 舊版會印「0 個追蹤 action」並 rc=0——與本工具存在的目的直接矛盾。
        problems.append(
            f"❌ [{_CHECK_ORDER[2]}] {_WORKFLOWS_DIR} 內找不到任何 "
            "`uses: actions/…@…` 宣告 — 掃描面疑似被改壞（本 repo 現況應為數十處）"
        )
        unrun.append(f"{_CHECK_ORDER[3]}（前置：③掃到零筆 `uses:` 宣告）")
        return _report(notes, problems, unrun)

    inconsistent: list[str] = []
    total_files = 0
    for action in sorted(findings):
        versions = findings[action]
        if len(versions) > 1:
            detail = "\n".join(
                f"  {version}：\n" + "\n".join(f"    - {site}" for site in sites)
                for version, sites in sorted(versions.items())
            )
            inconsistent.append(
                f"  · actions/{action}：發現 {len(versions)} 種版本\n{detail}"
            )
        else:
            (version, sites), = versions.items()
            total_files += len(sites)
            notes.append(f"✅ actions/{action}@{version}：{len(sites)} 處一致")
    if inconsistent:
        problems.append(
            f"❌ [{_CHECK_ORDER[3]}] {len(inconsistent)} 個 action 的版本跨 workflow "
            "不一致（同一 action 在不同 workflow 內必須釘同一版本）：\n"
            + "\n".join(inconsistent)
        )
    else:
        # R56：印「實際掃到的 action 數」而非白名單長度——舊版印 len(_TRACKED_ACTIONS)，
        # 掃描面縮小時這個數字不動，等於把唯一的人工觀測訊號也一併蒙蔽。
        notes.append(
            f"✅ [{_CHECK_ORDER[3]}] {len(findings)} 個 actions/* action、"
            f"共 {total_files} 處 uses: 宣告皆同名同版"
        )
    return _report(notes, problems, unrun)


def cli(argv: list[str]) -> int:
    """CLI 入口：未知引數 rc=2 fail-loud（R67-D20 同一個洞，射程擴張至本檔）。

    🔴 為何拒收待在這一層（R75 統一四支，理由同 `tools/_cli_flags.py` 檔頭〈接線紀律〉）：
    `main(argv=None) → sys.argv[1:]` 會誤傷程式化呼叫端。**本檔就是那筆實例的現場**——
    `python -m unittest tools.tests.test_gha_action_versions` 時 unittest 把模組名放進
    `sys.argv`，`m.main()` 於是把它當未知旗標拒收 rc=2，而該測試斷言 rc=1
    ⇒ HEAD 既存 3 支假紅（R75 本機實測 `Ran 14 / FAILED (failures=3)`）。
    """
    rc = _cli_flags.reject_unknown_argv("check_gha_action_versions.py", argv, ())
    return main(argv) if rc is None else rc


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
