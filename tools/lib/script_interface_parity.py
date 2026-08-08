"""`.sh` ↔ `.ps1` **可觀察介面**對等判準（R81 包／S8-05 承接）。

住在 `tools/lib/` 而非消費端 `tools/check_script_parity.py` 的理由，同
`self_help_exec_parity.py` 檔頭那一段：消費端受 `check_loc_budget.SPECIAL_FILES`
的 raw-line 棘輪管，且門檻＝納管當下實際行數（**零餘裕**）⇒ 判準本體只能外掛，
消費端留呼叫。**不得**為了讓它留在原地而調高門檻。

🔴 缺口本體（R80 掃描 S8-05，當時狀態＝未落地）：`check_script_parity.py` 驗的是
「存在性 ＋ 位元組釘選 ＋ 幾道具名內容鎖」，**沒有任何一般性的行為判準** ⇒ 一對
`.sh`／`.ps1` 可以做不同的事而全樹零訊號。本模組補的就是這一面。

════════════════════════════════════════════════════════════════════════════
🔴 誠實劃界（先讀這段，否則會把本模組當成它不是的東西）
════════════════════════════════════════════════════════════════════════════
**行為等價不可判定**（停機問題），本模組**不宣稱**驗證行為等價，也沒有能力驗證。
它比對的是**可觀察介面的表面集合**——那是可判定的近似。

抓得到（分歧幾乎必然是真缺陷）：
  · 一側能回而另一側永遠回不出的 **退出碼**——呼叫端 `if rc == N` 的分支會因平台而異；
  · 一側依賴而另一側完全不呼叫的 **外部執行檔**（跨平台同名者）；
  · 一側用而另一側沒用的 **git 子指令**——兩側對 repo 狀態的動作面不同。

**抓不到**（逐條列出，不得把本模組的綠燈當成這些事的證明）：
  · 同一個退出碼在兩側由**不同條件**觸發（集合相等、語意相反照樣綠）；
  · 動作的**順序**、次數、條件分支結構；
  · 訊息文字、輸出格式、寫了哪些檔、寫進什麼內容；
  · 動態構造的指令名（變數展開、`eval`、`&$cmd`）——抽取是字面掃描，看不到；
  · 字串／heredoc 內的字面（例：訊息裡寫 `exit 3`）會被算進去，屬已知假陽性面，
    由基準表吸收而非靠更聰明的正則（正則軍備競賽在本 repo 已翻車兩次，見
    `_script_scan_surface.py` 檔頭 R79 ARCH）。

判準形狀＝**與凍結基準逐筆相等**（雙向）：新分歧＝紅；既有分歧被修好卻沒回來
除帳＝也紅（收斂必須被看見）。體例逐字同 `self_help_exec_parity._SELF_HELP_DEBT_FROZEN`。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

#: 字面 `exit <碼>`。前瞻排除 `$LASTEXITCODE`／`FSE_EXIT` 這類 token 尾綴誤命中，
#: 形狀逐字沿用消費端 `_EXIT_LITERAL_RE`（同一件事不另立第二種寫法）。
_EXIT_RE = re.compile(r"(?<![\w$])exit\s+(\d+)")

#: `git [-C dir] [-c k=v]… <子指令>`。**必須**配下面的白名單過濾：實測不過濾時，
#: 散文（`git repository`／`git would silently ignore…`）會被當成子指令，
#: `install_post_commit` 一對就誤報 3 筆——假紅正是這類判準活不過一輪的死因。
_GIT_RE = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)*(?:-c\s+\S+\s+)*([a-z][a-z0-9-]+)")

#: 真實 git 子指令白名單（只認得的才算數）。
_GIT_SUBCOMMANDS = frozenset({
    "add", "archive", "branch", "checkout", "cherry-pick", "clean", "clone",
    "commit", "config", "diff", "fetch", "init", "log", "ls-files", "ls-remote",
    "merge", "mv", "pull", "push", "rebase", "remote", "reset", "restore",
    "rev-list", "rev-parse", "rm", "show", "stash", "status", "switch",
    "symbolic-ref", "tag", "update-index", "worktree",
})

#: 跨平台同名外部執行檔白名單。刻意**只收兩平台都可能存在、且名字相同**者——
#: 這是本 facet 能跨語言比較的唯一理由。cmdlet（`Test-Path`）與 shell builtin
#: （`[ -f ]`）不在其中：那兩者是同一語意的平台原生寫法，比對它們必然全紅。
_EXTERNAL_BINS = frozenset({
    "act", "alembic", "chmod", "cmp", "curl", "docker", "java", "node", "npm",
    "pytest", "python", "python3", "ruff", "ssh", "tar", "uv", "wget",
})

#: 掃描面下限。0 對＝迴圈跑零次＝恆綠，而 rc 與「正確地全部通過」一模一樣——
#: 本 repo 對這個形態有反覆前科（見消費端 `_check_latest_thinness` 的 `latest_pins`
#: 非空斷言、`_MIN_EXTRACT_COUNTS` 的抽取下限）。刻意刪減時同步下修。
_SCOPE_FLOOR = 3

#: 凍結基準：`{對子 key: {facet: (僅 .sh 有, 僅 .ps1 有, 理由)}}`。
#:
#: 🔴 取值紀律同 `_TIER_BASELINE`：**當回合實測直接填入、零推算、不留餘裕**。
#: 判準是**雙向精確比對**——多一筆＝新分歧；少一筆＝分歧被修好（好事，但必須回來
#: 除帳，否則餘裕就是日後無聲加回去的破口）。
#:
#: 🔴 這三筆都是**可見的欠債，不是豁免**：登記在此不代表它們是對的，只代表它們是
#: 已知的、且今天不在本輪射程內。三筆逐一辯護見各自 reason 欄。
_BASELINE: dict[str, dict[str, tuple[tuple[str, ...], tuple[str, ...], str]]] = {
    "LATEST/tools/arch_fitness/run_self_evolution": {
        "exit_codes": (
            ("64",), ("6", "8"),
            "兩側檔頭皆已用散文登記這三個碼的單側性（.ps1 檔頭逐字寫 "
            "`rc=64 USAGE 未知參數（usage；僅 .sh 側）`）——但**沒有任何機制在比對兩側**："
            "既有的 `_check_exit_code_contract()` 是拿每一側各自去比 SSOT 表那個"
            "**超集**，兩側各自都是子集 ⇒ 兩邊都通過，側對側的不對稱結構上看不見。"
            "本 facet 就是補這一面。64=USAGE：.sh 對未知參數 `exit 64`，.ps1 走 "
            "`param()` 繫結錯誤、永遠回不出 64；6=PLATFORM_PREREQ／8=SSOT_GUARD_MISSING "
            "為 .ps1 側限定。修它要動 LATEST 生產腳本與 SSOT 契約表，非本輪射程。"
        ),
    },
    "LATEST/tools/init_project": {
        "external_bins": (
            ("curl", "wget"), (),
            "`.sh` 的 `check_dependencies()` 硬檢查 `git` ＋ `curl`-or-`wget` 兩項；"
            "`.ps1` 的 `Test-Dependencies` 只檢查 `git`。**可辯護**（PowerShell 內建 "
            "`Invoke-WebRequest`，不需要外部 HTTP 客戶端），故登記而非判紅；"
            "但它是三筆裡唯一**兩側散文都沒提過**的不對稱 ⇒ 在本模組之前，"
            "任何一側增刪相依都不會有人知道。"
        ),
    },
    "LATEST/tools/install_hooks/install_post_commit": {},
}


def facet_sets(text: str) -> dict[str, frozenset[str]]:
    """單側文字 → `{facet: 值集合}`。純函式（測試可注入合成輸入），不碰磁碟。

    呼叫端負責先剝註解——剝法住在消費端（`_strip_comments`，含 `.ps1` 的 `<# … #>`
    區塊），本模組刻意不自己抄一份：同一份知識兩個家正是本 repo 一路在治的病。
    """
    return {
        "exit_codes": frozenset(_EXIT_RE.findall(text)),
        "git_subcommands": frozenset(
            s for s in _GIT_RE.findall(text) if s in _GIT_SUBCOMMANDS
        ),
        "external_bins": frozenset(
            b for b in _EXTERNAL_BINS
            if re.search(r"(?<![\w./-])" + re.escape(b) + r"(?:\.exe)?(?![\w-])", text)
        ),
    }


def side_reader(
    registered_path: Callable[[str, Path | None], Path | None],
    strip_comments: Callable[[str, bool], str],
    latest_tools: Path | None,
) -> Callable[[str], str | None]:
    """`登記 key（含副檔名）→ 已剝註解的內文`；讀不到回 `None`。

    路徑解析與剝註解兩件事都**留在消費端**（`_registered_path`／`_strip_comments`），
    本模組只把它們串起來——那兩份判準各自已有主人，抄一份過來就是第二個家。
    """
    def _read(rel: str) -> str | None:
        path = registered_path(rel, latest_tools)
        if path is None or not path.is_file():
            return None
        return strip_comments(path.read_text(encoding="utf-8-sig"), rel.endswith(".ps1"))
    return _read


def divergences(
    sh_text: str, ps1_text: str
) -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
    """兩側文字 → `{facet: (僅 .sh 有, 僅 .ps1 有)}`，**只收非空者**。純函式。"""
    a, b = facet_sets(sh_text), facet_sets(ps1_text)
    out: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
    for facet in a:
        only_sh, only_ps1 = tuple(sorted(a[facet] - b[facet])), tuple(sorted(b[facet] - a[facet]))
        if only_sh or only_ps1:
            out[facet] = (only_sh, only_ps1)
    return out


def select_pairs(
    pairs: list[str],
    read_side: Callable[[str], str | None],
    thinness_enrolled: frozenset[str] | set[str],
    exempt_tiers: dict[str, str],
) -> list[str]:
    """本判準的**掃描面**（計算得出，不是寫死名單）——三類逐一排除：

      (1) **薄殼釘選對**（`_THINNESS_ENROLLED`）：兩側都只是委派同一個 Python 核心的
          殼，行為同一性由「同一份核心」結構性保證，比對兩層殼的介面沒有意義；
      (2) **`tier4_forbidden`**：ADR-XPLAT-002 §3.4 明文「語意刻意不同、禁止收斂」
          （`run_local_nightly`＝Windows 深度 7-stage vs mac 薄聚合器）⇒ 判它必然全紅，
          而那個紅是**政策要的結果**，不是缺陷；
      (3) **跨語言委派對**：一側檔名出現在另一側內文（`ci-gate.ps1` → `ci-gate.sh`）
          ⇒ 只有一個實作，介面差異全部是「委派殼 vs 本體」的假紅。

    剩下的才是**真的有兩份獨立實作**的對子——分歧在那裡才可能是真缺陷。
    """
    out: list[str] = []
    for stem in sorted(pairs):
        if stem in thinness_enrolled or exempt_tiers.get(stem) == "tier4_forbidden":
            continue
        sh_text, ps1_text = read_side(stem + ".sh"), read_side(stem + ".ps1")
        if sh_text is None or ps1_text is None:
            continue
        sh_name, ps1_name = stem.rsplit("/", 1)[-1] + ".sh", stem.rsplit("/", 1)[-1] + ".ps1"
        if sh_name in ps1_text or ps1_name in sh_text:
            continue
        out.append(stem)
    return out


def baseline_problems(live: dict[str, dict[str, tuple[tuple[str, ...], tuple[str, ...]]]],
                      baseline: dict | None = None) -> list[str]:
    """實況 vs 凍結基準的**雙向**逐筆比對（唯一判準實作，供 production 與注入測試共用）。"""
    base = _BASELINE if baseline is None else baseline
    problems: list[str] = []
    for stem in sorted(set(live) | set(base)):
        got, want = live.get(stem, {}), base.get(stem)
        if want is None:
            problems.append(
                f"{stem}：不在凍結基準內——新的對子進入掃描面卻沒有基準，"
                f"請實測後補一筆（即使是空 dict）。實況分歧：{got or '無'}")
            continue
        for facet in sorted(set(got) | set(want)):
            g, w = got.get(facet), want.get(facet)
            if w is None:
                problems.append(
                    f"{stem} / {facet}：**新的介面分歧**——僅 .sh 有 {list(g[0])}；"
                    f"僅 .ps1 有 {list(g[1])}。兩側請改成對等；確為刻意不對稱者，"
                    f"回 `_BASELINE` 補一筆並寫下為什麼")
            elif g is None:
                problems.append(
                    f"{stem} / {facet}：基準登記的分歧（.sh {list(w[0])} / "
                    f".ps1 {list(w[1])}）**已消失**——分歧被修好是好事，請回 `_BASELINE` "
                    f"把這一筆刪掉除帳（留著就是日後無聲加回去的餘裕）")
            elif (g[0], g[1]) != (w[0], w[1]):
                problems.append(
                    f"{stem} / {facet}：分歧內容變了——基準 .sh {list(w[0])} / "
                    f".ps1 {list(w[1])}；實況 .sh {list(g[0])} / .ps1 {list(g[1])}")
    return problems


def check(
    pairs: list[str],
    read_side: Callable[[str], str | None],
    thinness_enrolled: frozenset[str] | set[str],
    exempt_tiers: dict[str, str],
    fail: Callable[[str], None],
) -> bool:
    """對真實 repo 跑一次；紅燈走呼叫端的 `fail`（紅燈輸出唯一出口），綠燈自己 print。"""
    scope = select_pairs(pairs, read_side, thinness_enrolled, exempt_tiers)
    if len(scope) < _SCOPE_FLOOR:
        fail(f"❌ 介面對等鎖：掃描面只剩 {len(scope)} 對（下限 {_SCOPE_FLOOR}）——"
             f"雙原生對子若真的少了，請同步下修 `_SCOPE_FLOOR`；否則就是選面判準"
             f"被改壞、整道鎖靜默空轉（零迴圈恆綠與全數通過的 rc 一模一樣）")
        return False
    live = {}
    for stem in scope:
        sh_text, ps1_text = read_side(stem + ".sh"), read_side(stem + ".ps1")
        if sh_text is None or ps1_text is None:  # select_pairs 已濾，這裡是防禦
            fail(f"❌ 介面對等鎖：{stem} 的某一側讀不到——取數管道壞掉，結論無效")
            return False
        live[stem] = divergences(sh_text, ps1_text)
    problems = baseline_problems(live)
    if problems:
        fail("❌ 介面對等鎖：.sh／.ps1 兩側的可觀察介面與凍結基準不符"
             "（退出碼／外部執行檔／git 子指令三面；本鎖**不**驗行為等價，"
             "邊界見 tools/lib/script_interface_parity.py 檔頭）：")
        for p in problems:
            fail(f"  · {p}")
        return False
    n = sum(len(v) for v in _BASELINE.values())
    print(f"✅ 介面對等鎖：{len(scope)} 對雙原生腳本的退出碼／外部執行檔／git 子指令"
          f"三面與凍結基準逐筆相符（登記在案的既有分歧 {n} 筆）")
    return True
