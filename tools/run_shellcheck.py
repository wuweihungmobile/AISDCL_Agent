#!/usr/bin/env python3
"""shellcheck 接電器（R80 包 F／S8-02）——把 POSIX 側的靜態分析從「沒人在跑」變成閘門。

🔴 為何存在（本輪實測的缺陷本體，不是預防性建設）：
  全庫有 23 處 `# shellcheck disable=` 指令散落在 19 支腳本裡（Grep 實測），
  也就是作者們**相信 shellcheck 在跑**並為它寫了豁免；而 `.github/` 對 `shellcheck`
  這個字的命中數是 **0** ⇒ 它從來沒有被執行過一次。那些 disable 指令是裝飾品。
  這與本 repo 反覆判過的形態同型：「政策有宣告、卻沒有任何機械物在執行它」。

🔴 接電當回合就抓到真缺陷（這才是它值得存在的證據，不是「以後可能有用」）：
  `AutoClaude/tools/run_mutmut_in_docker.sh` 的 `RESULTS_RC=$?` 被 **SC2320** 逐字
  指出「This $? refers to echo/printf, not a previous command」——那個 rc 恆為 0，
  `mutmut results` 真的失敗時完全不會反映出來（本輪已修，見該檔）。
  PowerShell 側的同型缺陷（讀 rc 前接管線）早就有 PreToolUse hook 硬擋，
  POSIX 側在本檔之前一道都沒有。

射程與誠實劃界：
  · 掃描面＝**active**（非凍結）tracked shell script：所有 `*.sh` ＋ 三處 git-hooks
    目錄裡帶 shell shebang 的無副檔名檔。**凍結版 SDD（v0.01~v0.29）刻意排除**——
    Copy-on-Evolve 禁改，把它們納管只會製造修不了的紅（同 root-infra-ci 的
    `bash -n` 那一道既有射程）。
  · 嚴重度門檻＝`warning`（含 error）。`info`／`style` 兩級**今天不納管**：
    實測 `-S style` 只多 7 筆，但那 7 筆全是風格建議，納管它們會把「新缺陷」
    的訊號稀釋在風格噪音裡。要收緊時改 `_SEVERITY` 並重釘基線即可。
  · shellcheck 是**靜態**分析：它看得到語法與資料流形態，看不到 BSD/GNU coreutils
    的執行期差異（`sed -i ''`、`readlink -f`、`stat` 旗標…）。本檔不宣稱涵蓋那一類，
    那一類的機械物是 `tools/tests/test_bash32_compat.py` 的 `_PATTERNS`。
  · 本檔在 Linux CI 與 Windows 本機都跑得起來（PATH 上的 shellcheck 優先，
    否則走 `koalaman/shellcheck:stable` 容器）。兩條路跑的是同一個引擎，
    故 **Linux 已驗 ⇒ mac 亦成立**（shellcheck 是純靜態、不依賴平台 libc）。

基線的形狀（雙向棘輪，不是豁免清單）：
  `_BASELINE` 是 `{"<路徑>::<SCxxxx>": 筆數}`。
    · 出現不在表內的鍵、或某鍵筆數上升 ⇒ 紅（新增缺陷）。
    · 表內的鍵消失、或筆數下降 ⇒ **也紅**，訊息要求把表改小。
  第二向刻意存在：只擋「變多」的表會在債被修掉之後靜默保留一個過期豁免，
  下一個人再犯同一筆時它會被當成「本來就在基線裡」放行（本 repo 已判過的
  stale-exemption 形態）。棘輪只准往下走，`--print-baseline` 產生新表。

用法：
  python tools/run_shellcheck.py                # 判決（rc=0 綠／1 有差異／2 載具缺席）
  python tools/run_shellcheck.py --print-baseline
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SEVERITY = "warning"
_DOCKER_IMAGE = "koalaman/shellcheck:stable"
#: 凍結版 SDD 樹（LATEST 除外）——Copy-on-Evolve 禁改，故不納管（見檔頭射程）。
_FROZEN_RE = re.compile(r"^AISDLC_SDD/AISDLC_SDD_v0\.(?!30(?:/|$))\d+/")
#: git-hooks 目錄：無副檔名、以 shebang 判定是不是 shell 腳本。
_HOOK_DIR_MARKERS = ("/git-hooks/", "/.githooks/")
#: `-f gcc` 的輸出形態：`path:line:col: level: message [SCxxxx]`
_GCC_RE = re.compile(r"^(?P<path>[^:]+):\d+:\d+: \w+: .*\[(?P<code>SC\d+)\]\s*$")

#: 存量基線（R80 包 F 落地當下實測；`--print-baseline` 重產）。
#: 🔴 只准變小。每一筆都是**還沒修**的債，不是「決定不修」。
_BASELINE: dict[str, int] = {
    # SC1090：source 的路徑是變數 ⇒ shellcheck 追不進去。兩支都是刻意的動態 source。
    "AISDLC_SDD/AISDLC_SDD_v0.30/tools/arch_fitness/run_self_evolution.sh::SC1090": 1,
    "AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/formal/run_tlc.sh::SC1090": 1,
    # SC2011：`ls | grep` 對含空白／換行的檔名會壞掉。真缺陷，但改動 LATEST 版
    # init_project.sh 的下載流程屬另一個授權面（本輪只動它的 git 索引模式）。
    "AISDLC_SDD/AISDLC_SDD_v0.30/tools/init_project.sh::SC2011": 4,
    # SC2034：宣告了沒在本檔用到的變數（多為跨檔／呼叫端消費的回傳慣例）。
    "AutoClaude/tools/sd06_w3_staging_dryrun.sh::SC2034": 1,
    "tools/git-hooks/pre-push::SC2034": 1,
    "tools/lib/git_hooks_install_common.sh::SC2034": 2,
    # SC2254：`case` 的 pattern 沒加引號 ⇒ 會被當 glob 而非字面比對。
    "tools/git-hooks/pre-push::SC2254": 1,
}


def shell_targets(repo_root: Path) -> list[str]:
    """active（非凍結）tracked shell script 的 repo 相對路徑清單。

    空清單＝取數管道壞掉，呼叫端必須當成失敗（不是「沒有東西要檢查」）。
    """
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    if proc.returncode != 0:
        return []
    out: list[str] = []
    for rel in proc.stdout.splitlines():
        if _FROZEN_RE.match(rel):
            continue
        if rel.endswith(".sh"):
            out.append(rel)
        elif any(marker in rel for marker in _HOOK_DIR_MARKERS):
            path = repo_root / rel
            if not path.is_file():
                continue
            first = path.read_bytes().split(b"\n", 1)[0]
            if first.startswith(b"#!") and b"sh" in first:
                out.append(rel)
    return sorted(out)


def parse_findings(stdout: str) -> Counter[str]:
    """`-f gcc` 輸出 → `{"<路徑>::<SCxxxx>": 筆數}`。非判決行一律忽略。"""
    counts: Counter[str] = Counter()
    for line in stdout.splitlines():
        match = _GCC_RE.match(line.strip())
        if match:
            counts[f"{match['path'].replace(chr(92), '/')}::{match['code']}"] += 1
    return counts


def resolve_runner(repo_root: Path) -> tuple[str, list[str]] | None:
    """回傳 `(載具名, 指令前綴)`；兩條路都不通時回 None（呼叫端 rc=2 fail-loud）。

    刻意**不** skip：「找不到 shellcheck 就當作通過」正是本檔在治的那種假綠。
    """
    native = shutil.which("shellcheck")
    if native:
        return "PATH", [native]
    docker = shutil.which("docker")
    if docker:
        return "docker", [
            docker, "run", "--rm", "-v", f"{repo_root}:/repo:ro", "-w", "/repo",
            _DOCKER_IMAGE,
        ]
    return None


def collect(repo_root: Path) -> tuple[str, Counter[str]]:
    targets = shell_targets(repo_root)
    if not targets:
        raise RuntimeError("`git ls-files` 回空 ⇒ 取數管道壞掉，本次判決無效")
    runner = resolve_runner(repo_root)
    if runner is None:
        raise RuntimeError(
            "PATH 上沒有 shellcheck、也沒有 docker ⇒ 無法執行。"
            f"修法：安裝 shellcheck，或讓 docker 可用（會拉 {_DOCKER_IMAGE}）。"
            "本檔刻意不在這裡回 0——靜默放行正是它要治的病。"
        )
    name, prefix = runner
    proc = subprocess.run(
        [*prefix, "-f", "gcc", "-S", _SEVERITY, *targets],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(
            f"shellcheck（{name}）以 rc={proc.returncode} 結束＝執行失敗而非判決結果。"
            f"stderr: {proc.stderr.strip()[:500]}"
        )
    return name, parse_findings(proc.stdout)


def baseline_problems(
    counts: Counter[str], baseline: dict[str, int] | None = None
) -> list[str]:
    """雙向棘輪判定（純函式，供測試注入）：新增/上升 ⇒ 紅；消失/下降 ⇒ 也紅。"""
    base = _BASELINE if baseline is None else baseline
    problems: list[str] = []
    for key in sorted(set(counts) | set(base)):
        now, was = counts.get(key, 0), base.get(key, 0)
        if now > was:
            problems.append(
                f"❌ 新增 shellcheck 缺陷 {key}：基線 {was} → 現況 {now}。"
                "請修掉它；基線只准往下改。"
            )
        elif now < was:
            problems.append(
                f"❌ 基線已過期 {key}：基線 {was} → 現況 {now}。"
                "債已變少是好事，但過期的基線會在下次有人犯同一筆時放行它"
                "（stale exemption）⇒ 請以 --print-baseline 重釘。"
            )
    return problems


def format_baseline(counts: Counter[str]) -> str:
    body = "\n".join(f'    "{key}": {counts[key]},' for key in sorted(counts))
    return "_BASELINE: dict[str, int] = {\n" + body + "\n}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="shellcheck 閘門（active shell 腳本）")
    parser.add_argument("--print-baseline", action="store_true",
                        help="印出目前實況的 _BASELINE 字面，供重釘")
    args = parser.parse_args(argv)
    try:
        name, counts = collect(_REPO_ROOT)
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f"❌ shellcheck 閘門無法執行：{exc}", file=sys.stderr)
        return 2
    if args.print_baseline:
        print(format_baseline(counts))
        return 0
    problems = baseline_problems(counts)
    total = sum(counts.values())
    print(f"shellcheck（載具={name}，-S {_SEVERITY}）：{total} 筆 / 基線 "
          f"{sum(_BASELINE.values())} 筆")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print("✅ 與基線一致（無新增、無過期）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
