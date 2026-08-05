#!/usr/bin/env python3
"""雙平台腳本對等機械守護 — .sh / .ps1 三對腳本的 step 標籤一致性 + pytest 釘選一致性
+ 掃描目錄內全部 .sh/.ps1（成對與單邊）的納管完整性（R11 架構改善 C2）。

納管語意（R11 起；R12 ARCH-R12-3 擴面；R13 ARCH-R13-4 增列 tools/lib；**R60 Scan-E
E-A-01 收斂為 SSOT 名冊＋遞迴**）：掃描根一律取自 `tools/_script_scan_surface.py`
的 `SCRIPT_SCAN_ROOTS`＝tools/、AutoClaude/tools/、AISDLC_SDD/scripts/ **三棵樹（遞迴）**
——與 root-infra-ci.yml 第 2 道（pwsh parse ＋ BOM 守門）的 `-Recurse` 掃描面**同形狀**
（R60 前本檔為「非遞迴 4 目錄」自有名冊，新開子目錄放腳本時 CI 掃得到、本檔看不到，
且名冊本身無完整性鎖；WHY 與實測見該 SSOT 模組 docstring）；`tools/lib/` 因遞迴自動
涵蓋，不再單獨列名。再加上 AISDLC_SDD **LATEST 演化版** `<LATEST>/tools/`（**遞迴**；
LATEST 以 scripts/sdd_version.py SSOT 動態解析，解析失敗 fail-loud——parity 只在 repo
內跑，git 必在；凍結版 v0.01~v0.2X 依鐵律不掃）下的每支 .sh/.ps1 必屬五類之一，否則
fail-loud 列出未納管檔名：
  (1) 成對納管（_MARKER_PAIRS 標籤比對）；(2) 薄殼 hash 釘選（_THINNESS_ENROLLED）；
  (3) LATEST 版薄殼 hash 釘選（_LATEST_THINNESS_ENROLLED，R65；🔴 前身是 R12 的
  run_tlc FSM 軌錨點集合鎖 _TLC_TRACK_ENROLLED——ADR-XPLAT-002 §5 Phase 2-A 將
  run_tlc.{sh,ps1} 薄殼化為委派 tools.fsm_runtime.tlc_runner 後，兩側腳本已不再
  內嵌 .tla/.cfg 檔名字面，原鎖失去可抽取對象，退場並升級為 hash 釘選——語意同
  _THINNESS_ENROLLED，但鍵是 LATEST-relative、需動態解析，故不與其共表，見
  _check_latest_thinness 區塊註解）；(4) 成對豁免（_EXEMPT_PAIRS，
  附 (tier, reason)）；(5) 單邊豁免（_SINGLE_SIDED_EXEMPT，附 (tier, reason)）。LATEST 下的納管
  登記一律用「LATEST/tools/…」相對 key（版本升版 copy-on-evolve 時登記不失效）。
  各清單另有 stale 反向檢查（防清單腐化），詳見 _check_pair_enrollment 區塊註解。

  🔴 R66（DEF-101-622）：(3) 的兩張表（_LATEST_THINNESS_ENROLLED／
  _LATEST_PINNED_SHA256）與 (2) 的姊妹表同型（R12 QA-1 病灶：兩份獨立字面清單
  同時腐化即雙工具全綠），但直到 R66 前一直沒有比照 _check_thinness_cross_lock
  建立交叉鎖。已補 _check_latest_thinness_cross_lock()，見該函式區塊註解。

  🔴 R63（ADR-XPLAT-002 §5 Phase 1-C (b)(d)）：(4)(5) 的值由純理由字串升級為
  `(tier, reason)` 二元組，`tier` 取自 §3.1~3.4 定義的六類集合（`_VALID_TIERS`）；
  `tier3_os_primitive`／`tier4_forbidden` 的 reason 另須含硬理由關鍵詞
  （`_HARD_REASON_KEYWORDS`，見 `_check_tier_classification`）。另補 4 組「異名
  對等品」（stem 刻意不同但語意對等的單邊登記對）字典化 + stale 自檢
  （`_EQUIVALENCE_GROUPS` / `_check_equivalence_groups_fresh`，Phase 1-C (a)）。

  🔴 R64（ADR-XPLAT-002 §8 item 12）：R63 只驗證「現況合法」，沒有機制擋「未來把
  某筆 tier3/4 悄悄改回 unpinned、或把 tier1/2 打回 unpinned」，故加 `_check_tier_ratchet()`
  棘輪，只鎖 ADR 逐字指定的兩個降級方向（見 `_TIER_BASELINE` 上方的 `_TIER3_4`／
  `_TIER1_2` 常數），已隨 `main()` 自動執行、非另立 CLI 旗標。

  🔴🔴 R67-H14（**訂正 R64 的比對基準**）：R64 照抄 `TestShrinkOnlyRatchet` 的
  `git show HEAD:<本檔>` 形狀，但該形狀在**所有真正消費本工具 rc 的閘門**裡結構性
  恆真——pre-push 與三支 CI workflow 都跑在 commit 之後（CI 更是乾淨 checkout），
  HEAD 逐字等於工作樹 ⇒ 永遠零違規（沙箱實測：tier4→unpinned 降級 commit 後 rc=0、
  真 pre-push hook 端到端 rc=0）。R67 起基準改為**簽入本檔的凍結常數
  `_TIER_BASELINE`**：commit／checkout 都不會動它，比較在任何時點皆非退化；整條 git
  依賴一併移除（連帶消滅「基準取不到 ⇒ 綠燈空轉」的 fail-open 面）。完整論證與殘餘
  邊界見 `_TIER_BASELINE` 上方區塊註解。R67 另加兩條同族規則：活體登記項未涵蓋於
  基準即紅（擋「刪基準條目迴避棘輪」）、`unpinned` 筆數天花板 `_UNPINNED_CEILING`
  只准下修（R67-E24）。

  🔴 R67 round 2（ARCH-R67-03）：上述逐 key 降級規則對「活體與基準**成對編輯**」無效
  （複審沙箱實測：把 `LATEST/tools/init_project` 於兩處同步由 tier3 改為 tier1，全套
  全綠），而「成對編輯」正是新鮮度鎖強制出來的常規工作流 ⇒ 降級與升級在 diff 上同形。
  故加第三條同族規則：tier3/4 筆數地板 `_TIER34_FLOOR` 只准上修（總量維度，與
  `_UNPINNED_CEILING` 互為鏡像；成對編輯不影響它）。

🔴 本工具的邊界（務必先讀）：本工具只機械比對「標籤序列」（數量、順序、字面文字），
**不比對、也無能力比對**各 step 背後的實作內容是否語意對等。**本工具通過（exit 0）
不代表兩份腳本（.sh/.ps1）行為完全一致——只代表兩邊宣告的 step 名字對得上**；
實作漂移（同名 step 做了不同事）仍需人工審查，不可把本工具的綠燈當成雙平台
行為等價的證明。詳見下方「覆蓋範圍與侷限」。

為何需要：本機制本用來守護「兩側宣稱對等、但實作各自平行維護」的腳本對——
單邊加減 step 不會有任何機械訊號，故抽取兩版的「step 標籤字串」逐一比對，
不一致即 exit 1（供 root-infra-ci 與本機執行）。

（歷史：local_ci_gate 曾為 _MARKER_PAIRS 第四對，以 gate-call 抽取比對；R12
DEF-101-070 ② 收斂為 tools/local_ci_gate.py 單核心＋兩薄殼後，該對改由
check_wrapper_thinness.py hash 釘選守門，gate 清單漂移面已物理消滅、gate-call
抽取隨之退場。R16（Architect 建議 B）比照同一模式，把 bootstrap / integration_gate
/ run_act 三對雙原生實作收斂為「Python 單核心（bootstrap_core.py /
integration_gate_core.py / run_act_core.py）＋兩薄殼」，三對業務邏輯漂移面同樣
物理消滅，改由 check_wrapper_thinness.py hash 釘選守門，_MARKER_PAIRS 標籤比對
隨之退場——`_MARKER_PAIRS` 目前為空清單，保留作為未來若有新對「雙原生實作」腳本
需要標籤比對納管時的既有機制，非死碼。）

覆蓋範圍與侷限（docstring 即契約）：
  - `[n/m]` 標籤先剝除註解行（.sh/.ps1 整行 `#` 註解 + .ps1 `<# … #>` 區塊），再以
    regex 取「`[n/m]` + 其後至引號/反引號/$/反斜線/換行為止的字面文字」比對——
    變數插值（如 `$SDD_REQ` vs `$SddReq`）之後的差異不在比對範圍。
  - 只比對「標籤序列」（數量、順序、字面文字），不比對各 step 的實作內容是否
    語意對等——實作漂移仍靠人工審查與 ONBOARDING 對照表。
  - 內嵌字串裡的行內 `#` 不視為註解（僅剝除「首個非空白字元為 #」的整行）。
  - 抽取數量另設下限釘選 `_MIN_EXTRACT_COUNTS`（R9 跨平台複審）：宣告 pattern 被
    兩側同步改寫時，step 會靜默退出守護範圍且無 diff 訊號——數量低於釘選即紅燈；
    刻意刪減 step 時須同步更新釘選值。

另含 pytest 釘選一致性（P3-2；R4 複審 SA P2 擴充至三處）：AutoClaude/pyproject.toml、
AISDLC_SDD/AISDLC_SDD_v0.01/requirements-ci.txt（凍結基線）與 AISDLC_SDD 下動態解析
出的 LATEST 演化版（R10 DEF-101-133 起委派 AISDLC_SDD/scripts/sdd_version.py 單一真相源，
不再各語言重寫「等價邏輯」）三處 `pytest==X` 版本字串必須相等
（bootstrap 把 AutoClaude 與 v0.01 裝進同一 .venv；`AISDLC_SDD/scripts/ci-gate.sh` 跑
LATEST 版 fsm_runtime 測試時沿用同一共用 venv 的 pytest，從未依 LATEST 自己的
requirements-ci.txt 重新安裝——LATEST 宣告的版本號若漂移即為從未生效的假象）。

🔴 R61 訂正（ADR-XPLAT-002 Phase 1-B）：下段原記載 `AutoClaude/tools/install_git_hooks`／
`AISDLC_SDD/scripts/install-hooks` 兩對「暫緩納入、留在 `_EXEMPT_PAIRS`」——該狀態已於
R61 結束：兩對已改掛 `_THINNESS_ENROLLED`（hash 釘選，見 `check_wrapper_thinness.py`
`_PINNED_SHA256`），不再是零守門的決策豁免。原評估文字逐字保留於下，作為「為何選
hash 釘選、不選 `[n/m]` 標籤」這個判斷的史料依據（該判斷本身未變，只是治理類別從
「豁免」升級為「釘選」）：

已評估但暫緩納入 `_MARKER_PAIRS` 標籤比對的候選（R4 複審 QA P3）：
AutoClaude/tools/install_git_hooks.{sh,ps1}、AISDLC_SDD/scripts/install-hooks.{sh,ps1}
四支腳本。評估結論：這四支腳本本質是「單一動作、無多階段」的線性流程（assert worktree
→ 取 hooks dir → 驗證存在 → git config → 驗證安裝結果），並非像 run_act 那樣有六個語意
獨立的段落；真正曾經重複的判定邏輯已於 DEF-101-082 抽出至
`tools/git_hooks_install_common.py` 單一真相源，兩份呼叫端現僅剩各自平台原生的薄殼
呈現層（見 DEF-101-070/080/082），對這四支腳本加 `[n/m]` 標籤會是為了湊格式而做的
形式主義。行為層已由 windows/macos-compat-ci.yml 的安裝/解除/worktree 拒絕三情境實測
覆蓋（QA 判定風險低）。決策記事見缺陷帳本 DEF-101-088（closed-by-decision：不排入
`_MARKER_PAIRS`；R61 起改掛 hash 釘選，見上）。

使用：
  python3 tools/check_script_parity.py   # 於 repo 內任意 cwd；不一致印 diff 並 exit 1
  python3 tools/check_script_parity.py --print-collapse
      # R61 ADR-XPLAT-002 §4.1/§4.2：印出 UEP／AC 現查值（不跑其餘檢查、恆 rc=0，
      # 純報表；棘輪化時比照 tools/tests/test_adr_xplat001_c1c2_lock.py 的
      # shrink-only 形狀另立鎖，見該 ADR §4.4）。R63 擴充：逐對印出
      # _EXEMPT_PAIRS／_SINGLE_SIDED_EXEMPT 的 tier 與 reason，以及 4 組異名對等品
      # 清單（§5 Phase 1-C (a)(b)(c)）
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cli_flags  # noqa: E402  # 未知旗標 rc=2 fail-loud 的 SSOT（見該檔檔頭 WHY）
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌/⚠) 防崩潰保護
from _script_scan_surface import SCRIPT_SCAN_ROOTS, iter_tree_scripts  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[1]

# `[n/m]` + 其後字面文字（至引號/反引號/$/反斜線/換行為止），rstrip 收尾空白
_MARKER_RE = re.compile(r"\[\d+/\d+\][^\"'`$\\\n]*")
_PS1_BLOCK_COMMENT_RE = re.compile(r"<#.*?#>", re.DOTALL)


def _strip_comments(text: str, is_ps1: bool) -> str:
    if is_ps1:
        text = _PS1_BLOCK_COMMENT_RE.sub("", text)
    kept = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    return "\n".join(kept)


def _extract_markers(path: Path) -> list[str]:
    text = _strip_comments(
        path.read_text(encoding="utf-8-sig"), is_ps1=path.suffix == ".ps1"
    )
    return [m.rstrip() for m in _MARKER_RE.findall(text)]


# 抽取數量下限釘選（R9 跨平台複審）：抽取全靠固定宣告 pattern，pattern 被改寫
# （如兩側同步換引號風格/換函式名）時 step 會「靜默退出守護範圍」且雙邊一致、
# _compare 不會有任何 diff 訊號。以「抽取數量不得低於釘選值」補上機械訊號；
# bootstrap/integration_gate/run_act 三對已隨 R16 薄殼化收斂退場（同 R12
# local_ci_gate 先例，見 _THINNESS_ENROLLED）。刻意刪減 step 時須同步更新
# 本表（工具會在訊息中指路）。
_MIN_EXTRACT_COUNTS = {
    # R65（ADR-XPLAT-002 §5 Phase 2-A）：接替退場的 'run_tlc_tracks'（R12 ARCH-R12-3，
    # 抽 .tla/.cfg 檔名字面——run_tlc.{sh,ps1} 薄殼化後已無此字面，鎖失去可抽取對象）。
    # 新錨點＝薄殼委派 tools.fsm_runtime.tlc_runner 時傳的 --module/--cfg 引數 token
    # multiset：--module SDD_FSM、--module FLEET_FSM（5a 預設 cfg）、--module FLEET_FSM
    # （5b，與 --cfg FLEET_FSM_LIVENESS.cfg 同一行）、--cfg FLEET_FSM_LIVENESS.cfg，
    # 2026-07-31 實跑輸出釘選＝4（見 _check_run_tlc_invocation_parity 區塊註解）。
    "run_tlc_invocations": 4,
}


def _check_extract_floor(label: str, sh_items: list[str], ps1_items: list[str]) -> bool:
    floor = _MIN_EXTRACT_COUNTS[label]
    if len(sh_items) >= floor and len(ps1_items) >= floor:
        return True
    print(f"❌ {label}：抽取數量（.sh {len(sh_items)} / .ps1 {len(ps1_items)}）低於"
          f"釘選下限 {floor} — 最可能是宣告 pattern 被改寫、step 靜默退出守護範圍；"
          f"若確為刻意刪減 step，請同步更新本腳本 _MIN_EXTRACT_COUNTS['{label}'] 釘選值",
          file=sys.stderr)
    return False


def _compare(label: str, sh_items: list[str], ps1_items: list[str]) -> bool:
    if sh_items == ps1_items:
        print(f"✅ {label}：{len(sh_items)} 個 step 標籤一致")
        return True
    print(f"❌ {label}：step 標籤不一致（.sh {len(sh_items)} vs .ps1 {len(ps1_items)}）",
          file=sys.stderr)
    width = max(len(sh_items), len(ps1_items))
    for i in range(width):
        a = sh_items[i] if i < len(sh_items) else "（缺）"
        b = ps1_items[i] if i < len(ps1_items) else "（缺）"
        mark = " " if a == b else "≠"
        print(f"  {mark} .sh: {a!r}\n  {mark} .ps1: {b!r}", file=sys.stderr)
    return False


def _find_latest_sdd_version(aisdlc_sdd_dir: Path) -> Path | None:
    """委派 LATEST 解析 SSOT（AISDLC_SDD/scripts/sdd_version.py，R10 DEF-101-133）。

    歷史：本函式曾以 pathlib 重寫 ci-gate.sh glob 的「等價邏輯」——正是 R10 ARCH-3
    指出的多語言多實作漂移面（bash 未錨定/掃磁碟 vs 此處錨定/掃磁碟，語意已分歧）。
    改為 subprocess 呼叫 SSOT（tracked 過濾＋錨定＋數值排序），解析失敗回傳 None
    （維持原「找不到→None」語意，由呼叫端決定後果）。"""
    resolver = aisdlc_sdd_dir / "scripts" / "sdd_version.py"
    if not resolver.is_file():
        return None
    try:
        proc = subprocess.run(
            [sys.executable, str(resolver), "--sdd-root", str(aisdlc_sdd_dir)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    name = proc.stdout.strip()
    if proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)  # SSOT 警告（未 tracked 目錄等）直通
    if not name:
        return None
    return aisdlc_sdd_dir / name


def _resolve_latest_tools() -> Path | None:
    """LATEST 演化版 tools/ 實體路徑；解析失敗回 None（呼叫端 fail-loud 紅燈）。"""
    latest = _find_latest_sdd_version(_REPO_ROOT / "AISDLC_SDD")
    if latest is None:
        return None
    return latest / "tools"


# ── run_tlc 委派引數集合鎖（R65，取代 R12 ARCH-R12-3 的 FSM 軌錨點集合鎖）─────────
# 背景：ADR-XPLAT-002 §5 Phase 2-A 把 run_tlc.{sh,ps1} 改寫為委派
# `python -m tools.fsm_runtime.tlc_runner` 的薄殼，舊鎖（_TLC_TRACK_RE／
# _extract_tlc_tracks／_check_run_tlc_tracks）抽取的是兩側腳本內嵌的 *_FSM*.tla/.cfg
# 檔名字面（`-config SDD_FSM.cfg ... SDD_FSM.tla` 這種 java 呼叫寫法）——薄殼化後
# 兩側都只剩 `--module <NAME>` 這種不含檔名字面的引數，舊鎖的抽取對象已不存在，
# 依 ADR §4.2 rule 3 dominance test：
#   (a) 「兩側 run_tlc.sh/.ps1 必須存在」——有接手者：下方 _check_latest_thinness
#       的 hash 釘選同樣要求兩側檔案存在，且更嚴格（連內容都鎖）。
#   (b) 「抽取到的軌清單非空」——無直接接手者需要，但薄殼委派的引數本身即是新錨點
#       （見下）。
#   (c) 「兩側軌 multiset 必須相等」（DEF-101-100 攔的正是這條：.ps1 曾缺整條
#       FLEET_FSM 軌而 .sh 有，字面 hash 釘選對此**不設防**——hash 只鎖「這份檔案
#       是否等於上次核准的樣子」，兩側各自更新各自的 pin 即可雙雙綠燈，不會互相
#       比較。此斷言沒有接手者，須保留對應驗證）——改抽兩側薄殼呼叫
#       tools.fsm_runtime.tlc_runner 時傳的 `--module`/`--cfg` 引數 token 做
#       multiset 比對，語意與舊鎖相同（攔「單側少一次委派呼叫＝少一條軌」），
#       只是錨點換成新形態下仍存在的字面（引數字串，非檔名）。
_TLC_RUNNER_ARG_RE = re.compile(r"--(?:module|cfg)[ \t=]+\S+")


def _extract_tlc_runner_invocations(path: Path) -> list[str]:
    """抽取薄殼內委派 tlc_runner 的 --module/--cfg 引數 token（排序、含重複）。"""
    text = _strip_comments(
        path.read_text(encoding="utf-8-sig"), is_ps1=path.suffix == ".ps1"
    )
    return sorted(_TLC_RUNNER_ARG_RE.findall(text))


def _check_run_tlc_invocation_parity(latest_tools: Path) -> bool:
    label = "run_tlc_invocations"
    sh = latest_tools / "fsm_runtime" / "formal" / "run_tlc.sh"
    ps1 = latest_tools / "fsm_runtime" / "formal" / "run_tlc.ps1"
    if not sh.is_file() or not ps1.is_file():
        print(f"❌ {label}：LATEST run_tlc 腳本缺失（{sh} / {ps1}）— 該對若已移除，"
              f"請同步更新 _LATEST_THINNESS_ENROLLED 與本檢查", file=sys.stderr)
        return False
    sh_args = _extract_tlc_runner_invocations(sh)
    ps1_args = _extract_tlc_runner_invocations(ps1)
    if not sh_args or not ps1_args:
        print(f"❌ {label}：抽取到空引數清單（.sh {len(sh_args)} / .ps1 "
              f"{len(ps1_args)}）— 宣告 pattern 可能已改，請同步本腳本",
              file=sys.stderr)
        return False
    ok = _check_extract_floor(label, sh_args, ps1_args)
    return _compare(f"{label}（LATEST tlc_runner 委派引數集合）", sh_args, ps1_args) and ok


# ── run_self_evolution 退出碼契約三方鎖（R69；DEF-101-264 同型漂移的第三次復發）──
# 病灶：`run_self_evolution.{sh,ps1}` 兩側檔頭各自枚舉退出碼，並雙雙宣稱「規格側見
# SDD_SELF_EVOLUTION.md『退出碼契約』節」——**該節 grep 零命中**（R68 落地時只寫了指路、
# 沒建目的地）。同時該腳本對在 `_EXEMPT_PAIRS` 屬 `unpinned`、零機械 parity ⇒ 契約寫下來
# 的當天就是孤兒：任一側改碼、或兩側同時漂離規格，全樹沒有任何訊號。
#
# 修法（三處逐筆比對，而非「兩側互比」）：SSOT ＝ md 的 `<!-- exit-code-contract:begin/end -->`
# 表格；兩側檔頭各自的 `rc=<碼> <代號>` 枚舉必須與該表**逐筆相等**。刻意做成三方而非
# 兩方：兩方互比只能保證「兩份註解一樣」，仍可一起漂離規格（R68 的實際形態就是兩側都寫了
# 同一句指向不存在章節的話）。
#
# 另加第二道（覆蓋面而非一致性）：兩側腳本**非註解行**裡每個字面 `exit <碼>` 都必須在表內
# 有登記——否則新增一個沒人登記的碼仍然零訊號（第一道只看註解，看不到實作）。
# 邊界（誠實揭露，同本檔 docstring 對 `[n/m]` 的自限）：只比對「碼 ↔ 代號」的字面對應與
# 覆蓋面，**不驗證**兩側對同一碼的實際觸發條件是否語意相同——那需要跨語言的行為驗證，
# 不在本工具能力範圍內；語意等價仍靠 md 表的「語意」欄與人工審查。
_EXIT_CONTRACT_BEGIN = "<!-- exit-code-contract:begin -->"
_EXIT_CONTRACT_END = "<!-- exit-code-contract:end -->"
_EXIT_CONTRACT_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*([A-Z][A-Z0-9_]*)\s*\|", re.MULTILINE)
_EXIT_CONTRACT_DECL_RE = re.compile(r"rc=(\d+)\s+([A-Z][A-Z0-9_]*)")
# 字面 `exit <碼>`：bash 側多寫成 `{ …; exit 5; }`（不在行首），故不錨行首；改以「前面不是
# 識別字元/`$`」排除 `$LASTEXITCODE`、`FSE_EXIT` 這類 token 的尾綴誤命中。
_EXIT_LITERAL_RE = re.compile(r"(?<![\w$])exit\s+(\d+)")
# 抽取數量下限（同 `_MIN_EXTRACT_COUNTS` 精神）：三處任一被改成抽不到東西時，逐筆相等會
# 因「空集合 == 空集合」而恆真＝靜默失守。現況 10 碼，刻意刪碼時須同步下修本值。
_EXIT_CONTRACT_FLOOR = 10
_EXIT_CONTRACT_SPEC_REL = "workflow/sdd-self-evolution/SDD_SELF_EVOLUTION.md"


def _exit_contract_from_spec(spec: Path) -> dict[str, str] | None:
    text = spec.read_text(encoding="utf-8")
    start = text.find(_EXIT_CONTRACT_BEGIN)
    end = text.find(_EXIT_CONTRACT_END)
    if start < 0 or end < 0 or end < start:
        return None
    return dict(_EXIT_CONTRACT_ROW_RE.findall(text[start:end]))


def _exit_contract_from_script(path: Path) -> dict[str, str]:
    return dict(_EXIT_CONTRACT_DECL_RE.findall(path.read_text(encoding="utf-8-sig")))


def _check_exit_code_contract(latest_tools: Path) -> bool:
    label = "run_self_evolution 退出碼契約"
    spec = latest_tools.parent / _EXIT_CONTRACT_SPEC_REL
    sh = latest_tools / "arch_fitness" / "run_self_evolution.sh"
    ps1 = latest_tools / "arch_fitness" / "run_self_evolution.ps1"
    for path in (spec, sh, ps1):
        if not path.is_file():
            print(f"❌ {label}：{path} 不存在——契約的三處來源缺一即無法比對",
                  file=sys.stderr)
            return False
    declared = _exit_contract_from_spec(spec)
    if declared is None:
        print(f"❌ {label}：{spec} 找不到 {_EXIT_CONTRACT_BEGIN} … {_EXIT_CONTRACT_END} "
              f"標記區段——SSOT 章節被刪或改名（R68 的原始病灶就是『指向不存在的章節』）",
              file=sys.stderr)
        return False
    ok = True
    if len(declared) < _EXIT_CONTRACT_FLOOR:
        print(f"❌ {label}：SSOT 表只抽到 {len(declared)} 筆（下限 {_EXIT_CONTRACT_FLOOR}）"
              f"——表格結構或抽取 pattern 疑似漂移；刻意刪碼請同步下修 "
              f"_EXIT_CONTRACT_FLOOR", file=sys.stderr)
        ok = False
    for side, path in (("sh", sh), ("ps1", ps1)):
        found = _exit_contract_from_script(path)
        if found != declared:
            only_spec = {k: v for k, v in declared.items() if found.get(k) != v}
            only_side = {k: v for k, v in found.items() if declared.get(k) != v}
            print(f"❌ {label}：.{side} 檔頭枚舉與 SSOT（{_EXIT_CONTRACT_SPEC_REL} §6.1）"
                  f"不一致——SSOT 有而檔頭不符：{only_spec}；檔頭有而 SSOT 不符：{only_side}。"
                  f"先改 SSOT 表，再同步兩側檔頭的 rc= 枚舉行", file=sys.stderr)
            ok = False
        literals = set(_EXIT_LITERAL_RE.findall(
            _strip_comments(path.read_text(encoding="utf-8-sig"), is_ps1=(side == "ps1"))
        ))
        unlisted = sorted(literals - set(declared), key=int)
        if unlisted:
            print(f"❌ {label}：.{side} 實作有未登記的 exit 碼 {unlisted}——"
                  f"新增退出碼必須先寫進 SSOT 表（否則兩側可各自長出碰撞碼，"
                  f"正是 R68 修過的那個病）", file=sys.stderr)
            ok = False
    if ok:
        print(f"✅ {label}：SSOT／.sh／.ps1 三處 {len(declared)} 筆逐筆一致，"
              f"且兩側實作無未登記 exit 碼")
    return ok


# ── LATEST 版薄殼 hash 釘選（R65，ADR-XPLAT-002 §5 Phase 2-A）─────────────────
# WHY 不併入 check_wrapper_thinness._PINNED_SHA256：該表的鍵是「固定 repo-root
# 相對路徑」設計（其自身 tools/tests/test_check_wrapper_thinness.py::
# TestNoHardcodedLineCounts.test_print_lines_reports_real_counts 直接以
# `m.ROOT / rel` 驗證磁碟存在性，是刻意的設計不變量，非疏漏）；LATEST 演化版路徑
# 隨 Copy-on-Evolve 逐版變動，需要動態解析——本檔既有的 _resolve_latest_tools()／
# _registered_path() 已具備這個能力（_EXEMPT_PAIRS／_SINGLE_SIDED_EXEMPT／已退場的
# _TLC_TRACK_ENROLLED 皆走這條路）。故 run_tlc 薄殼化後的 hash 釘選改在本檔自建
# 一份小型登記表，**重用**（非重寫）check_wrapper_thinness 的正規化/hash 純函式
# （normalized_sha256／MAX_LINES），不強行把 LATEST 語意塞進其固定路徑設計、
# 也不動它既有的 10 支釘選與既有測試。
_LATEST_THINNESS_ENROLLED = {"LATEST/tools/fsm_runtime/formal/run_tlc"}
_LATEST_PINNED_SHA256: dict[str, str] = {
    # 2026-07-31 實測
    # （`python -c "import check_wrapper_thinness as t; print(t.normalized_sha256(...))"`）。
    # R65 四方複審 7 項修復落地後的最終內容：(1) 裸執行三軌呼叫恆帶 --download 恢復
    # jar 自動下載、(3) .ps1 python 候選探測順序改 python3 優先（同 .sh）、(4) 新增
    # --tla-version 轉傳（.sh 讀 TLA_VERSION 環境變數／.ps1 讀 -TlaVersion 參數，
    # 皆只在使用者顯式帶值時才轉傳）。
    # 🔴 R67（R67-H35）：`check_wrapper_thinness._normalize()` 改為保留首行 shebang
    # ⇒ `.sh` 側重釘（`.ps1` 側首行非 shebang，hash 逐字不變）。內容未竄改的三段
    # 取證見 check_wrapper_thinness.py `_PINNED_SHA256` 上方 R67 註解。
    # 🔴 R68（Scan-A2）：`.sh` 側重釘——LATEST run_tlc.sh 在 macOS 系統 bash 3.2 下每一條
    # 執行路徑都必死於 `set -u` 空陣列展開（`${arr[@]}` 對空陣列在 bash 3.2 視為 unbound），
    # 且該死法回 rc=1，恰好撞上本檔自訂的「1＝TLC 偵測到 invariant violation」語意 ⇒ 把
    # 環境問題誤報成形式化驗證失敗。修法為 bash 3.2 安全展開 + 環境失敗改用獨立 rc。
    # 變更仍屬薄殼職責（只改展開語法與 rc 分派，未新增業務邏輯），故重釘而非降級豁免。
    "LATEST/tools/fsm_runtime/formal/run_tlc.sh": (
        "76207165469914976ee49b536c9c81e89fee079daa4756b0a57c752e144983fe"
    ),
    "LATEST/tools/fsm_runtime/formal/run_tlc.ps1": (  # R71 DEF-101-762 重釘；根因見帳本列＋該檔:47
        "feb3b9bf2ffdd35b789ca036a39f02cc6390769d3d9fb6fed3a9ef60cc3daf00"
    ),
}


def _check_latest_thinness(latest_tools: Path | None) -> bool:
    """LATEST 版薄殼 hash 釘選守門（同 check_wrapper_thinness.check_wrapper_thinness()
    邏輯，重用其正規化/hash 純函式，範圍限定 _LATEST_PINNED_SHA256 這組
    LATEST-relative 對子）。"""
    import check_wrapper_thinness as _thinness

    ok = True
    for rel in sorted(_LATEST_PINNED_SHA256):
        pinned = _LATEST_PINNED_SHA256[rel]
        path = _registered_path(rel, latest_tools)
        if path is None or not path.is_file():
            print(f"❌ LATEST 薄殼釘選：{rel} 檔案不存在或 LATEST 解析失敗",
                  file=sys.stderr)
            ok = False
            continue
        line_count = len(path.read_text(encoding="utf-8-sig").splitlines())
        if line_count > _thinness.MAX_LINES:
            print(f"❌ LATEST 薄殼釘選：{rel} {line_count} 行超過薄殼上限 "
                  f"{_thinness.MAX_LINES} 行", file=sys.stderr)
            ok = False
        actual = _thinness.normalized_sha256(path)
        if actual != pinned:
            print(f"❌ LATEST 薄殼釘選：{rel} 正規化內容 hash 與釘選不符（釘選 "
                  f"{pinned[:12]}… / 實際 {actual[:12]}…）—— wrapper 實質內容變動；"
                  f"若變更仍屬薄殼職責，請以 check_wrapper_thinness.normalized_sha256() "
                  f"取新值同步更新 _LATEST_PINNED_SHA256", file=sys.stderr)
            ok = False
    if ok:
        print(f"✅ LATEST 薄殼釘選：{len(_LATEST_PINNED_SHA256)} 支 hash 釘選皆正常"
              f"（{len(_LATEST_THINNESS_ENROLLED)} 對）")
    return ok


def _cross_lock(label: str, enrolled: set[str], pinned_map: dict[str, str],
                enrolled_name: str, pinned_name: str) -> bool:
    """「stem 登記表 ↔ hash 釘選表」鍵集合交叉鎖的**唯一實作**（R76 收斂）。

    WHY 收斂：`_check_thinness_cross_lock()` 與 `_check_latest_thinness_cross_lock()`
    的函式體原本逐字相同（只差標籤與兩張表的名字）——而這兩支存在的**唯一理由**正是
    「兩份獨立字面清單會各自腐化」。判準自己複製兩份，等於把它負責攔的病帶進守門層本身
    （R12 QA-1 → R66 DEF-101-622 的復發路徑就是「照著上一份抄一份新的」）。
    訊息字面刻意逐字沿用（ADR-XPLAT-002 §3 引用過成功訊息的形狀）。
    """
    pinned = set(pinned_map)
    expected = {f"{stem}{ext}" for stem in enrolled for ext in (".sh", ".ps1")}
    ok = True
    for rel in sorted(expected - pinned):
        print(f"❌ {label}：{rel} 已登記 {enrolled_name} 但不在 "
              f"{pinned_name} — 薄殼宣稱無 hash 釘選守門", file=sys.stderr)
        ok = False
    for rel in sorted(pinned - expected):
        print(f"❌ {label}：{rel} 在 {pinned_name} 但其 stem 未登記 "
              f"{enrolled_name} — 兩清單腐化（請同步）", file=sys.stderr)
        ok = False
    if ok:
        print(f"✅ {label}：{len(enrolled)} 對薄殼登記與 "
              f"{len(pinned)} 支 hash 釘選鍵集合一致")
    return ok


def _check_thinness_cross_lock() -> bool:
    """parity↔thinness 兩份登記清單交叉鎖（R12 QA 一審 QA-1）。

    WHY：_THINNESS_ENROLLED（本檔）與 check_wrapper_thinness._PINNED_SHA256 是兩份
    獨立字面清單——同一 commit 雙邊各刪一行即雙工具全綠（hash 值不可測，但**鍵集合
    可測**）。此鎖斷言每個 thinness 登記 stem 的 .sh 與 .ps1 都在 pin 表，反向多餘
    pin（表內出現未登記 stem）亦紅，杜絕「登記與釘選各自腐化」的零訊號窗。"""
    import check_wrapper_thinness as _thinness  # 同目錄，頂部已 sys.path 注入

    return _cross_lock("thinness 交叉鎖", _THINNESS_ENROLLED, _thinness._PINNED_SHA256,
                       "_THINNESS_ENROLLED", "check_wrapper_thinness._PINNED_SHA256")


def _check_latest_thinness_cross_lock() -> bool:
    """LATEST 版 parity↔thinness 兩份登記清單交叉鎖（R66 DEF-101-622，同 R12 QA-1
    教訓套用於 R65 新表）。

    WHY：`_LATEST_THINNESS_ENROLLED`（stem 登記）與 `_LATEST_PINNED_SHA256`（hash 釘選）
    是兩份獨立字面清單，與 `_THINNESS_ENROLLED`／`check_wrapper_thinness._PINNED_SHA256`
    同型——`_check_latest_thinness()` 的迴圈只走 `_LATEST_PINNED_SHA256`，若把
    `_LATEST_PINNED_SHA256` 清空但不動 `_LATEST_THINNESS_ENROLLED`，該函式的迴圈
    次數為零、`ok` 從未被設為 False，會印出「0 支 hash 釘選皆正常（1 對）」這種
    自相矛盾的假綠訊息，且 exit code 仍是 0——兩份清單各自腐化即雙訊號雙盲。
    此鎖斷言每個 `_LATEST_THINNESS_ENROLLED` 登記 stem 的 `.sh` 與 `.ps1` 都在
    pin 表，反向多餘 pin（表內出現未登記 stem）亦紅，鍵集合形狀與
    `_check_thinness_cross_lock` 相同，只是鍵改為 LATEST-relative。"""
    return _cross_lock("LATEST thinness 交叉鎖", _LATEST_THINNESS_ENROLLED,
                       _LATEST_PINNED_SHA256, "_LATEST_THINNESS_ENROLLED",
                       "_LATEST_PINNED_SHA256")


def _check_pytest_pin() -> bool:
    pyproject = _REPO_ROOT / "AutoClaude" / "pyproject.toml"
    req_ci_frozen = _REPO_ROOT / "AISDLC_SDD" / "AISDLC_SDD_v0.01" / "requirements-ci.txt"
    latest_dir = _find_latest_sdd_version(_REPO_ROOT / "AISDLC_SDD")

    targets: list[tuple[str, Path]] = [("v0.01 凍結基線", req_ci_frozen)]
    if latest_dir is not None and latest_dir.name != "AISDLC_SDD_v0.01":
        targets.append((f"LATEST（{latest_dir.name}）", latest_dir / "requirements-ci.txt"))

    m1 = re.search(r'"pytest==([^"]+)"', pyproject.read_text(encoding="utf-8"))
    if not m1:
        print(f"❌ pytest 釘選：找不到 pytest== 釘選字串（{pyproject}）", file=sys.stderr)
        return False

    ok = True
    for label, req_ci in targets:
        if not req_ci.is_file():
            print(f"❌ pytest 釘選：{label} 找不到 requirements-ci.txt（{req_ci}）",
                  file=sys.stderr)
            ok = False
            continue
        m2 = re.search(r"(?m)^pytest==(\S+)", req_ci.read_text(encoding="utf-8"))
        if not m2:
            print(f"❌ pytest 釘選：{label}（{req_ci}）找不到 pytest== 釘選字串",
                  file=sys.stderr)
            ok = False
            continue
        if m1.group(1) != m2.group(1):
            print(f"❌ pytest 釘選漂移：{pyproject.name}={m1.group(1)} vs "
                  f"{label} {req_ci.name}={m2.group(1)} — 三處必須同版（同一 .venv 共裝）",
                  file=sys.stderr)
            ok = False

    if ok:
        print(f"✅ pytest 釘選一致：三處皆 pytest=={m1.group(1)}")
    return ok


# git longpaths 旗標內容鎖（R50 四方複審發現）：macos_smoke_local.sh 與
# windows_smoke_local.ps1 各自獨立內嵌 git clone `-c core.longpaths=true` 字面旗標
# （見兩檔各自 fake repo clone 段落）。上方 `_SINGLE_SIDED_EXEMPT`（見下）只登記
# 兩檔互為異名對等品的「存在性」，不解析內容——若其中一側未來意外遺漏或改動此
# 旗標，parity 檢查不會有任何機械訊號。本鎖直接讀檔搜尋此字面字串，兩側缺一即
# 紅，是本檔 docstring 自承「只比對標籤序列、不比對實作內容」邊界之外，針對此
# 一具體旗標另立的窄範圍內容防腐檢查（非全面解除該邊界）。
_GIT_LONGPATHS_FLAG = "-c core.longpaths=true"


def _check_git_longpaths_flag_parity() -> bool:
    macos_sh = _REPO_ROOT / "tools" / "macos_smoke_local.sh"
    windows_ps1 = _REPO_ROOT / "tools" / "windows_smoke_local.ps1"
    for path in (macos_sh, windows_ps1):
        if not path.is_file():
            print(f"❌ git longpaths 旗標鎖：{path} 不存在——請同步更新本檢查",
                  file=sys.stderr)
            return False
    # 剝除註解行後再數（沿用既有 _strip_comments）：只有註解裡提及旗標、
    # 實際 git clone 指令已把旗標拿掉，不得被註解殘留誤判為仍存在（bug-injection
    # 實測重現：只刪指令上的旗標、留下說明性註解，若直接對全文做 substring
    # count 仍會誤判綠燈）。
    macos_hits = _strip_comments(
        macos_sh.read_text(encoding="utf-8"), is_ps1=False
    ).count(_GIT_LONGPATHS_FLAG)
    windows_hits = _strip_comments(
        windows_ps1.read_text(encoding="utf-8"), is_ps1=True
    ).count(_GIT_LONGPATHS_FLAG)
    ok = True
    if macos_hits == 0:
        print(f"❌ git longpaths 旗標鎖：tools/macos_smoke_local.sh 未見 "
              f"'{_GIT_LONGPATHS_FLAG}'——與 windows_smoke_local.ps1（{windows_hits} 處）"
              "不對等", file=sys.stderr)
        ok = False
    if windows_hits == 0:
        print(f"❌ git longpaths 旗標鎖：tools/windows_smoke_local.ps1 未見 "
              f"'{_GIT_LONGPATHS_FLAG}'——與 macos_smoke_local.sh（{macos_hits} 處）"
              "不對等", file=sys.stderr)
        ok = False
    if ok:
        print(f"✅ git longpaths 旗標鎖：兩側皆含 '{_GIT_LONGPATHS_FLAG}'"
              f"（macos {macos_hits} 處／windows {windows_hits} 處）")
    return ok


# ── 成對/單邊腳本註冊完整性（enrollment 發現鎖）— R10 拍板案(a)，DEF-101-134；
#    R11 架構改善 C2 擴充至單邊 ─────────────────────────────────────────────────
# 過去「新增一對同名 .sh/.ps1 而不掛任何守門」零機械訊號（marker_pairs 與 thinness
# 釘選對象皆硬編碼清單，磁碟上長出新對子沒人發現）。此檢查掃描 SSOT 名冊三棵樹
# （**遞迴**，R60 Scan-E E-A-01 起與 CI 第 2 道同形狀）
# 下的**所有** .sh/.ps1，斷言每支必屬四類之一：{成對 parity 標籤比對, 薄殼 thinness
# hash 釘選, 成對明文豁免（附決策依據）, 單邊明文豁免（附決策依據）}，否則
# fail-loud 列出未納管檔名（R11 前單邊腳本零訊號）；並反向檢查各註冊清單無 stale
# 條目（防清單腐化）——單邊豁免的 stale 含兩種：檔案已消失、或對邊已出現（不再
# 是單邊，須改登記為成對類）。
# ── Tier 分類（R63，ADR-XPLAT-002 §3.1~§3.4 Phase 1-C (b)）─────────────────────
# 6 類合法 tier：tier1_contract／tier1_adapter＝CLI port 契約與其薄殼 adapter（§3.1，
# 本檔登記的是 adapter 端）；tier2_spec＝spec port，資料＋判定規則須跨語言各一份
# 實作、由行為表 parity 鎖守（§3.2）；tier3_os_primitive＝明文封頂的 OS 原語（§3.3
# 六類，禁止未來輪重辯）；tier4_forbidden＝明文禁止收斂（§3.4 三成員）；unpinned＝
# 尚未歸類、或評估後判定不落入上述四類的例外項（如 ci-gate 因 §2.2 實測不符
# Tier-1 納編前置條件〔raw 行數 ≤ MAX_LINES〕、或 LATEST 版產生器僅有「輸出逐位元
# 一致」證據而無 Tier-1/2/3/4 定義可套用者）。
_TIER1_CONTRACT = "tier1_contract"
_TIER1_ADAPTER = "tier1_adapter"
_TIER2_SPEC = "tier2_spec"
_TIER3_OS_PRIMITIVE = "tier3_os_primitive"
_TIER4_FORBIDDEN = "tier4_forbidden"
_UNPINNED = "unpinned"
_VALID_TIERS = frozenset({
    _TIER1_CONTRACT, _TIER1_ADAPTER, _TIER2_SPEC,
    _TIER3_OS_PRIMITIVE, _TIER4_FORBIDDEN, _UNPINNED,
})

# tier3_os_primitive／tier4_forbidden 的 reason 必須額外含至少一個硬理由關鍵詞
# （R63 Phase 1-C (d)）。關鍵字比對即可、不做語意驗證——同 ADR-XPLAT-001 §4.3.4
# 對 C1/C2 已劃的同型邊界（防呆，非語意驗證；見 §6 邊界 4）。清單取自 ADR §3.3/§3.4
# 現有六類/三成員的實際措辭，OR 邏輯（含其一即通過）。
#
# 🔴 R67（Scan-H R67-E24）unpinned 退場義務：`unpinned` 的原始門檻只有「reason 非空」
# （實測 `reason="x"` 照樣綠），於是它成為 Tier-1~4 之外「不需要任何理由品質、也沒有
# 退場義務」的永久豁免類別。本輪加一條**最小語意門檻**：unpinned 的 reason 必須以
# `退場：未指派` 或 `退場：R<輪號>…` 結尾形態出現（見 `_UNPINNED_EXIT_RE`），把「這筆
# 有沒有人接」由散文語感升級為可 grep 的機械欄位。
# 邊界（誠實揭露，同 §6 邊界 4 的同型自限）：本鎖**不驗證輪號是否仍在未來**——那需要
# 耦合缺陷帳本的「當前輪號」，而 `CrossPlatform_Scan_Dimensions.md` §191 已明文警告
# 該做法會製造永紅（帳本推進後舊列全紅）。本鎖只保證「每筆 unpinned 都明說了承接
# 對象」，不保證那個承接是真的。數量面的退步由 `_UNPINNED_CEILING` 棘輪另行擋住。
#
# 🔴 R67 round 2（SD-R67-03／ARCH-R67-01 交叉發現）：初版正則寫 `R\d+`，對 `R68+` 這種
# **開放下界**形態是放行的（`re.search` 匹到 `R68` 前綴即成立，尾巴的 `+` 完全不影響
# 判定）——而同輪 ADR-XPLAT-002 §8 表頭規則 1 才剛把 `R<N>+` 明文定為病灶並禁用
# （理由：永遠有一個「之後」可以指，於是從不到期；item 7／8 六輪零異動即為實例）。
# 兩件事在同一輪同時發生 ⇒ 新鎖一出生就把當輪判定為不可接受的寫法制度化了。故收緊為
# 「`R` 後面的數字串結束後不得再接 `+`／`＋`」：半形與全形加號都擋（本 repo 散文中文
# 全形符號常見，只擋半形等於留一條同義逃生口）。承接對象只有兩種合法寫法：**具名輪次**
# （`R68`）或**未指派**——與 §8 表頭規則 1 逐字同源，規則不再只存在於散文裡。
_UNPINNED_EXIT_RE = re.compile(r"退場：(未指派|R\d+(?![\d+＋]))")

_HARD_REASON_KEYWORDS = (
    "launchd", "schtasks", "container", "GNU", "Copy-on-Evolve",
    "驗證載具", "心跳檔", "R12 QA-2", "明文禁止收斂", "無共同 API",
)

# ── 異名對等品（R63 Phase 1-C (a)）────────────────────────────────────────────
# 4 組「stem 刻意不同但語意對等」的單邊登記對（過去只在各自 _SINGLE_SIDED_EXEMPT
# 的 reason 散文互相提及對方，無機械可查的結構）。字典化後可被 stale 自檢：
# 磁碟存在性／仍登記於 _SINGLE_SIDED_EXEMPT／stem 確實不同，三者缺一即紅
# （見 _check_equivalence_groups_fresh）。
_EQUIVALENCE_GROUPS: dict[str, tuple[str, str]] = {
    "smoke_local": ("tools/macos_smoke_local.sh", "tools/windows_smoke_local.ps1"),
    "git_hooks_install_common": ("tools/lib/git_hooks_install_common.sh",
                                 "tools/lib/GitHooksInstallCommon.ps1"),
    "windowsapps_guard": ("tools/lib/windowsapps_guard.sh",
                          "tools/lib/WindowsAppsGuard.ps1"),
    "nightly_installer": ("tools/install_mac_nightly.sh",
                          "tools/install_windows_nightly.ps1"),
}


_MARKER_PAIRS: list[tuple[str, str, str]] = []
# R60 Scan-E E-A-01：掃描根不再由本檔自持名冊，一律取 SSOT
# （`tools/_script_scan_surface.py`）——與 root-infra-ci.yml 第 2 道的 `-Recurse`
# 掃描面同形狀（三棵樹、遞迴）。名稱保留 `_PAIR_SCAN_DIRS` 以免既有訊息／測試錨點
# 大面積改名（Rule 3）；`tools/lib` 由遞迴涵蓋，不再單獨列名。
_PAIR_SCAN_DIRS = SCRIPT_SCAN_ROOTS
# LATEST 納管 key 前綴（R12 ARCH-R12-3）：登記用「相對 LATEST 的路徑」，版本升版
# （copy-on-evolve）時登記不失效；實體路徑由 _resolve_latest_tools() 動態解析。
_LATEST_PREFIX = "LATEST/tools/"
# tools/check_wrapper_thinness.py hash 釘選（R12 起 local_ci_gate 收斂為薄殼＋
# tools/local_ci_gate.py 單核心後加入，DEF-101-070 ②；gate-call 抽取比對隨之退場。
# R16（Architect 建議 B）比照同一模式收斂 bootstrap/integration_gate/run_act 三對，
# 原 _MARKER_PAIRS 標籤比對隨之退場，見上方 docstring）
_THINNESS_ENROLLED = {
    "tools/dev_start",
    "AutoClaude/tools/local_ci_gate",
    "tools/bootstrap",
    "tools/integration_gate",
    "AutoClaude/tools/run_act",
    # R61 ADR-XPLAT-002 Phase 1-B（DEF-101-088 由零守門的決策豁免升級為 hash 釘選）：
    # 四支殼 raw 行數（50/65/40/42）皆 ≤ check_wrapper_thinness.MAX_LINES=100，符合
    # §3.1 納編前置條件；業務邏輯仍下沉 tools/git_hooks_install_common.py 單一真相源
    # 不變，本次只是把「無守門」升級為「hash 釘選＋行數上限＋業務樣板關鍵字並聯」。
    "AutoClaude/tools/install_git_hooks",
    "AISDLC_SDD/scripts/install-hooks",
}
_EXEMPT_PAIRS: dict[str, tuple[str, str]] = {
    "AISDLC_SDD/scripts/ci-gate": (
        _UNPINNED,
        "ci-gate.ps1 為薄委派殼（Find-GitBash → bash ci-gate.sh 單一真相源），非第二實作；"
        "ADR-XPLAT-002 §2.2 實測訂正：ci-gate.sh 是 281 行的閘門本體而非薄殼，raw 行數"
        "超過 MAX_LINES=100，不符 Tier-1 納編前置條件，故不歸為 tier1_adapter；"
        "Phase 2-B（刪 fallback，需 signoff）落地前維持決策豁免；"
        # R67 round 2（SD-R67-03）：原寫 `退場：R68+`，但 ADR §8 item 11 的承接者欄
        # 逐字是「**封存中**；解除前置＝Phase 2-B（使用者／PM signoff）」——沒有任何
        # 具名輪次，寫 R68 是本檔自己編的；且 `R<N>+` 已被同輪 §8 表頭規則 1 禁用。
        # 依 §8 item 7／8 的同款處置（六輪零回執 ⇒ 一律改列未指派）改寫如下。
        "退場：未指派（ADR-XPLAT-002 §8 item 11：封存中，解除前置＝Phase 2-B signoff，"
        "回執容器＝§8.1；該列另有三條解除判準）"
    ),
    "AutoClaude/tools/run_local_nightly": (
        _TIER4_FORBIDDEN,
        ".ps1=Windows 深度 7-stage nightly、.sh=mac 薄聚合器串接既有腳本，"
        "語意刻意不同、不做標籤對等比對；R11 Architect D1 拍板；"
        "ADR-XPLAT-002 §3.4：心跳檔前兩行為三站點契約，明文禁止收斂"
    ),
    # ── LATEST 版 tools（R12 ARCH-R12-3 親讀定類；run_tlc 已於 R65 薄殼化並走
    #    _LATEST_THINNESS_ENROLLED hash 釘選，見上方區塊）──
    "LATEST/tools/init_project": (
        _TIER3_OS_PRIMITIVE,
        "legacy v3.x 初始化精靈雙原生實作，無 [n/m]/gate 宣告錨點可機械抽取；"
        "R12 親讀定類豁免（互動流程差異屬平台原生呈現層）；"
        "ADR-XPLAT-002 §3.3 #6 訂正：真正硬理由為與上游分歧＋Copy-on-Evolve 只覆蓋 "
        "1/30，非原評估的「遠端 one-liner 自足性」"
    ),
    "LATEST/tools/install_hooks/install_post_commit": (
        _UNPINNED,
        "R11 D1：兩產生器輸出逐位元一致取證＋LATEST 解析委派 scripts/sdd_version.py "
        "SSOT（DEF-101-133），殼層無標籤錨點；不符 Tier-1/2/3/4 任一定義，暫列未歸類；"
        "退場：未指派"
    ),
    "LATEST/tools/arch_fitness/run_self_evolution": (
        _UNPINNED,
        "FSE 有界驅動器雙原生實作，無標籤錨點（.sh echo FSE_* vs .ps1 函式化）；"
        "dry-run 安全預設兩側一致，R12 親讀定類豁免；不符 Tier-1/2/3/4 任一定義，"
        "暫列未歸類。🔴 R69 起**不再是零機械 parity**：退出碼契約已由 "
        "_check_exit_code_contract() 三方鎖守門（SSOT ＝ SDD_SELF_EVOLUTION.md §6.1 "
        "↔ 兩側檔頭 rc= 枚舉，另加實作 exit 字面覆蓋面）；tier 維持 unpinned 是因為 "
        "`[n/m]` 標籤對等仍不適用（雙原生、無共同錨點），非因無人守；"
        "退場：未指派"
    ),
}
# 單邊豁免清單（R11 架構改善 C2）：掃描目錄內只有 .sh 或只有 .ps1 單邊存在的腳本，
# 必須在此附決策依據登記，否則 fail-loud（過去單邊腳本零訊號）。
_SINGLE_SIDED_EXEMPT: dict[str, tuple[str, str]] = {
    # 兩平台 smoke 聚合器互為對等品但 stem 刻意不同（macos_smoke_local ↔
    # windows_smoke_local），非同名對；行為層由 macos/windows-compat-ci.yml 覆蓋
    "tools/macos_smoke_local.sh": (
        _TIER4_FORBIDDEN,
        "對等品=windows_smoke_local.ps1（stem 刻意不同）；ADR-XPLAT-002 §3.4：本身"
        "即為驗證載具，判定合流至單一核心會與 R12 QA-2『兩訊號合流即單點化』衝突，"
        "明文禁止收斂"
    ),
    "tools/windows_smoke_local.ps1": (
        _TIER4_FORBIDDEN,
        "對等品=macos_smoke_local.sh（stem 刻意不同）；ADR-XPLAT-002 §3.4：本身即為"
        "驗證載具，判定合流至單一核心會與 R12 QA-2『兩訊號合流即單點化』衝突，"
        "明文禁止收斂"
    ),
    # ── tools/lib（R13 ARCH-R13-4 增列掃描）─────────────────────────────────
    # install 共用層兩支互為「異名對等品」——stem 刻意不同（POSIX snake_case vs
    # PowerShell PascalCase 各依平台慣例），非同名對、_discover_scripts 只認同名
    # 故各以單邊登記（比照 macos/windows smoke 先例）；行為對等另有
    # tools/tests/test_git_hooks_install_common.py 行數守門。
    "tools/lib/git_hooks_install_common.sh": (
        _TIER1_ADAPTER,
        "對等品=GitHooksInstallCommon.ps1（異名對等，stem 刻意不同；"
        "test_git_hooks_install_common.py 守門）；ADR-XPLAT-002 §3.1 活體先例：契約＝"
        "tools/git_hooks_install_common.py，本檔為其薄殼 adapter"
    ),
    "tools/lib/GitHooksInstallCommon.ps1": (
        _TIER1_ADAPTER,
        "對等品=git_hooks_install_common.sh（異名對等，stem 刻意不同；"
        "test_git_hooks_install_common.py 守門）；ADR-XPLAT-002 §3.1 活體先例：契約＝"
        "tools/git_hooks_install_common.py，本檔為其薄殼 adapter"
    ),
    "tools/lib/Find-GitBash.ps1": (
        _TIER2_SPEC,
        "PowerShell 專屬 Git Bash 探測 helper——POSIX 側本來就在 bash 內，無需對等；"
        "ADR-XPLAT-002 §3.2 git_bash_locator 家族（3 份：本檔／"
        "integration_gate_core.py::find_git_bash／AISDLC_SDD/scripts/bash_probe.py），"
        "由行為表 parity 鎖（test_find_git_bash_parity.py）守住判定語意一致"
    ),
    "tools/lib/WindowsAppsGuard.ps1": (
        _TIER2_SPEC,
        "對等品=windowsapps_guard.sh（異名對等，stem 依平台語言慣例刻意不同；"
        "R37 PowerShell 側抽出，R43 Scan-B 訂正原「POSIX 側無 WindowsApps 概念」"
        "誤判——Git Bash on Windows 會繼承 Windows PATH，同樣命中 WindowsApps 空殼，"
        "DEF-101-353 補上 POSIX 側對等實作）；ADR-XPLAT-002 §3.2 real_python_candidate "
        "家族（4 份），bootstrap 悖論定案不收斂，見 CrossPlatform_Scan_Dimensions.md"
    ),
    "tools/lib/windowsapps_guard.sh": (
        _TIER2_SPEC,
        "對等品=WindowsAppsGuard.ps1（異名對等，stem 依平台語言慣例刻意不同；"
        "R43 Scan-B 系統性缺口收斂，DEF-101-353——Git Bash on Windows 繼承 Windows "
        "PATH 同樣會命中 WindowsApps 空殼，原 PowerShell-only guard 留下 9 個 bash "
        "呼叫點缺口，本檔為 POSIX 側對等實作，供 pre-push 等腳本 dot-source）；"
        "ADR-XPLAT-002 §3.2 real_python_candidate 家族（4 份），bootstrap 悖論定案"
        "不收斂"
    ),
    # mac nightly launchd 安裝器（R13 ARCH-R13-3）：launchd 為 macOS 專屬機制，
    # Windows 對等＝schtasks 排程家族（tools/install_windows_nightly.ps1，R19 新增
    # 一鍵建立；設定事後校正另見 fix_nightly_catchup.ps1，見 ONBOARDING §8）
    "tools/install_mac_nightly.sh": (
        _TIER3_OS_PRIMITIVE,
        "launchd 專屬安裝器（macOS-only）；Windows 對等=schtasks 一鍵安裝器 "
        "install_windows_nightly.ps1（stem 刻意不同，ONBOARDING §8）；"
        "ADR-XPLAT-002 §3.3 #1：launchd／schtasks 兩排程機制無共同 API"
    ),
    # Windows nightly 排程一鍵安裝器（R19 修復包 D）：對等品=install_mac_nightly.sh，
    # stem 刻意不同（install_mac_nightly ↔ install_windows_nightly，同上 macos/windows
    # smoke 先例）；本檔（check_script_parity）只比對 step 標籤序列，兩者本質是「兩種
    # 平台慣例、部分能力靠語言原生機制承載」的不同形態，不適合塞進本檔的字面比對。
    # 跨檔能力對照（R22 DEF-101-233 修復，訂正 R19~R21 舊註解「行為對等由
    # test_install_windows_nightly.py 守門」之誤——該檔實際只驗證 Windows 側自身結構，
    # 從未跨檔比對 mac 側能力集合）改由 tools/tests/test_schedule_capability_parity.py
    # 以語意能力對照表比對（install/uninstall/status/render-preview 四能力，非字面
    # 旗標字串集合——mac `--render-only` 與 windows `-WhatIf` 語意對等但字面不同）。
    # 措辭刻意不含「schtasks」/「§8」字面——本項屬 macOS/Windows stem 相異對等品，
    # 不屬 test_onboarding_parity_interlock.py 鎖住的「§8 ops 排程家族（無 .sh 對等
    # 的純 Windows-only 三支）」清單語意，避免誤觸該互鎖交叉比對。R63 補 tier3 硬理由
    # 關鍵詞時延續這條刻意排除（用「launchd」而非「schtasks」，見下方 reason）。
    "tools/install_windows_nightly.ps1": (
        _TIER3_OS_PRIMITIVE,
        "對等品=install_mac_nightly.sh（stem 刻意不同，如 macos/windows_smoke_local 先例）；"
        "能力對照由 test_schedule_capability_parity.py 守門；ADR-XPLAT-002 §3.3 #1："
        "對等 mac 側走 launchd，兩排程原語無共同 API"
    ),
    # Windows schtasks 排程家族兩支（ONBOARDING.md §8 明文 Windows-only、無 .sh 對等；
    # run_local_nightly 於 R11 已成對——mac .sh 薄聚合器落地——移登記至 _EXEMPT_PAIRS）
    # R76：原第三支 reschedule_g0_gatecheck.ps1 已整支刪除（它唯一能做的事是重排
    # AutoClaude_SD09_G0_GateCheck，而該工作於 R71 從本機移除 ⇒ 每條路徑都停在
    # 「Task not found」守衛 exit 1，是真孤兒）。本表刪這一筆＝磁碟已無對應物，
    # 留著會被 _check_pair_enrollment 的「單邊豁免 stale」反向檢查判紅；
    # `_TIER_BASELINE` 那一筆則依該表維護規則**刻意保留**（永久記憶，防同名回鍋降級）。
    "AutoClaude/tools/fix_nightly_catchup.ps1": (
        _TIER3_OS_PRIMITIVE, "schtasks 排程家族（ONBOARDING §8）"
    ),
    "AutoClaude/tools/g0_gate_check.ps1": (
        _TIER3_OS_PRIMITIVE, "schtasks 排程家族（ONBOARDING §8）"
    ),
    # bash-only 工具（ONBOARDING.md §6 明文無 .ps1 對等，Windows 以 Git Bash 執行）
    "AutoClaude/tools/run_mutmut_in_docker.sh": (
        _TIER3_OS_PRIMITIVE,
        "bash-only 工具（ONBOARDING §6）；ADR-XPLAT-002 §3.3 #5：由 "
        "`docker run python:3.11-slim bash …` 送進 Linux container 內執行，"
        "container 內不會有 PowerShell"
    ),
    "AutoClaude/tools/sd06_w3_staging_dryrun.sh": (
        _UNPINNED,
        "bash-only 工具（ONBOARDING §6）；本檔 docstring 自陳為 Linux staging DBA "
        "工具（需 psql/pg_dump/alembic），計時採 GNU coreutils date %N 奈秒擴充——"
        "Linux／現代 macOS BSD date／Windows Git Bash 內建 MSYS2 移植 GNU coreutils "
        "date（DEF-101-340 R40 實測確認支援 %N）三個目標平台皆支援，未證實硬技術"
        "障礙，純屬尚未撰寫 .ps1 對等殼，非 Tier-3 OS 原語；退場：未指派"
    ),
    "AISDLC_SDD/scripts/act-ci.sh": (
        _UNPINNED,
        "bash-only 工具（ONBOARDING §6）；未證實硬技術障礙——act 本身可 winget/choco/"
        "scoop 裝於 Windows（腳本自身錯誤訊息即列出），純屬尚未撰寫 .ps1 對等殼，"
        "非 Tier-3 OS 原語；退場：未指派"
    ),
    "AISDLC_SDD/scripts/copy_on_evolve.sh": (
        _UNPINNED,
        "bash-only 工具（ONBOARDING §6）；核心邏輯是 `git archive`（跨平台原生指令），"
        "未證實硬技術障礙，純屬 repo 慣例（755 入庫僅限 tools/git-hooks/，其餘 .sh 一律 "
        "bash 呼叫）尚未撰寫 .ps1 對等殼；退場：未指派"
    ),
    "AISDLC_SDD/scripts/pytest_passed_count.sh": (
        _UNPINNED,
        "bash-only 工具（ONBOARDING §6）；純 grep/tail 管線純函式，理論上可等價移植 "
        "PowerShell，未證實硬技術障礙，純屬尚未撰寫 .ps1 對等殼；退場：未指派"
    ),
    # LATEST 版 tools（R12 ARCH-R12-3）
    "LATEST/tools/verify_traceability.sh": (
        _UNPINNED,
        "bash-only legacy 追溯鏈驗證工具（v1.1-SDD），歷來無 .ps1 對等；"
        "Windows 以 Git Bash 執行；未證實硬技術障礙（Git Bash 上可正常執行），"
        "純屬歷史遺留未移植，非 Tier-3 OS 原語；退場：未指派"
    ),
}
# R11 P4 清單互斥自檢：同一 stem 不得同時掛成對豁免與單邊豁免——對邊落地轉成對
# 豁免後若殘留單邊條目即「殭屍豁免」，import 即 fail-loud（防清單腐化零訊號）。
_zombie_exempt = sorted(
    s for s in _SINGLE_SIDED_EXEMPT if s.rsplit(".", 1)[0] in _EXEMPT_PAIRS
)
if _zombie_exempt:
    raise AssertionError(
        f"殭屍豁免（stem 已登記 _EXEMPT_PAIRS）：{_zombie_exempt} —— 請自 _SINGLE_SIDED_EXEMPT 移除"
    )


def _enrolled_pairs() -> set[str]:
    parity = {sh_rel[: -len(".sh")] for _label, sh_rel, _ps1 in _MARKER_PAIRS}
    return (parity | _THINNESS_ENROLLED | _LATEST_THINNESS_ENROLLED
            | set(_EXEMPT_PAIRS))


def _registered_path(rel: str, latest_tools: Path | None) -> Path | None:
    """登記 key → 實體路徑（LATEST/tools/… key 需經 LATEST 解析；失敗回 None）。"""
    if rel.startswith(_LATEST_PREFIX):
        if latest_tools is None:
            return None
        return latest_tools / rel[len(_LATEST_PREFIX):]
    return _REPO_ROOT / rel


def _discover_scripts(latest_tools: Path | None) -> tuple[list[str], list[str]]:
    """掃描 SSOT 三棵樹（**遞迴**）＋ LATEST tools（遞迴，R12）→（成對 stem, 單邊相對路徑）。

    R60 Scan-E E-A-01：三棵樹的列舉委派 `_script_scan_surface.iter_tree_scripts()`
    單一實作（遞迴性只寫在那一處），成對判定改以「repo 相對路徑去副檔名」為 key
    ——與舊的「同目錄內 stem 相同」語意等價（key 本來就含目錄），故既有納管登記
    （含 `tools/lib/…` 這類子目錄 key）逐字不變；差別只在新開子目錄不再逸出掃描面。
    """
    pairs: list[str] = []
    singles: list[str] = []
    rels = iter_tree_scripts(_REPO_ROOT)
    sh_stems = {r[: -len(".sh")] for r in rels if r.endswith(".sh")}
    ps1_stems = {r[: -len(".ps1")] for r in rels if r.endswith(".ps1")}
    pairs.extend(sorted(sh_stems & ps1_stems))
    singles.extend(f"{stem}.sh" for stem in sorted(sh_stems - ps1_stems))
    singles.extend(f"{stem}.ps1" for stem in sorted(ps1_stems - sh_stems))
    if latest_tools is not None and latest_tools.is_dir():
        # 遞迴：v0.30 實測四對散在 tools/ 根層與 install_hooks/、fsm_runtime/formal/、
        # arch_fitness/ 子目錄，非遞迴會整片漏掃（R12 病灶本體）。
        sh_rels = {p.relative_to(latest_tools).as_posix()[: -len(".sh")]
                   for p in latest_tools.rglob("*.sh")}
        ps1_rels = {p.relative_to(latest_tools).as_posix()[: -len(".ps1")]
                    for p in latest_tools.rglob("*.ps1")}
        pairs.extend(f"{_LATEST_PREFIX}{stem}" for stem in sorted(sh_rels & ps1_rels))
        singles.extend(f"{_LATEST_PREFIX}{stem}.sh" for stem in sorted(sh_rels - ps1_rels))
        singles.extend(f"{_LATEST_PREFIX}{stem}.ps1" for stem in sorted(ps1_rels - sh_rels))
    return pairs, singles


def _check_pair_enrollment(latest_tools: Path | None = None) -> bool:
    ok = True
    if latest_tools is None:
        latest_tools = _resolve_latest_tools()
    if latest_tools is None:
        # fail-loud：parity 只在 repo 內跑（git 必在），LATEST 解析失敗＝SSOT 壞了，
        # 不得靜默縮小掃描邊界；本輪僅比對非 LATEST 部分後回紅。
        print("❌ LATEST 解析失敗（AISDLC_SDD/scripts/sdd_version.py 缺席或執行失敗）"
              "— LATEST tools 掃描無法進行，LATEST/ 納管條目本輪不比對",
              file=sys.stderr)
        ok = False
    known = _enrolled_pairs()
    single_exempt = dict(_SINGLE_SIDED_EXEMPT)
    if latest_tools is None:  # LATEST 條目無從對磁碟——排除以免誤報 stale（已紅）
        known = {k for k in known if not k.startswith(_LATEST_PREFIX)}
        single_exempt = {k: v for k, v in single_exempt.items()
                         if not k.startswith(_LATEST_PREFIX)}
    pairs, singles = _discover_scripts(latest_tools)
    unknown = [p for p in pairs if p not in known]
    stale = sorted(known - set(pairs))
    unknown_singles = [s for s in singles if s not in single_exempt]
    stale_singles = sorted(set(single_exempt) - set(singles))
    for p in unknown:
        print(
            f"❌ 未註冊的成對腳本：{p}.sh / {p}.ps1 —— 新增成對腳本必須擇一納管："
            f"(1) 有標籤錨點 → 加入 _MARKER_PAIRS；(2) 薄殼 → 掛 check_wrapper_thinness "
            f"hash 釘選；(3) 決策豁免 → 加入 _EXEMPT_PAIRS 並附缺陷帳本依據",
            file=sys.stderr,
        )
        ok = False
    for p in stale:
        print(
            f"❌ 註冊清單 stale：{p} 已不存在同名 .sh/.ps1 對 —— 請自對應清單移除",
            file=sys.stderr,
        )
        ok = False
    for s in unknown_singles:
        print(
            f"❌ 未納管的單邊腳本：{s} —— 新增單邊 .sh/.ps1 必須附決策依據登記至 "
            f"_SINGLE_SIDED_EXEMPT（或補上對邊腳本走成對納管）",
            file=sys.stderr,
        )
        ok = False
    for s in stale_singles:
        p = _registered_path(s, latest_tools)
        if p is not None and p.is_file():
            # SD-R13-8 訊息分流：is_file 有兩個成因——(a) 對邊真的出現（成對了）；
            # (b) 所在目錄被自 _PAIR_SCAN_DIRS 移除（檔案仍在、掃描面縮小）。
            # 兩者都紅，但誤導的排障方向會浪費修復時間，故查對邊實存後分流。
            _other = p.with_suffix(".ps1" if p.suffix == ".sh" else ".sh")
            if _other.is_file():
                print(
                    f"❌ 單邊豁免 stale：{s} 的對邊腳本已出現（不再是單邊）—— 請自 "
                    f"_SINGLE_SIDED_EXEMPT 移除，並將該對依納管類別語意重新納管",
                    file=sys.stderr,
                )
            else:
                print(
                    f"❌ 單邊豁免 stale：{s} 仍在磁碟但未被掃描發現——其所在目錄疑似"
                    f"已自 _PAIR_SCAN_DIRS 移除（守門縮面），請恢復掃描目錄或連同"
                    f"豁免登記一併遷移",
                    file=sys.stderr,
                )
        else:
            print(
                f"❌ 單邊豁免 stale：{s} 已不存在 —— 請自 _SINGLE_SIDED_EXEMPT 移除",
                file=sys.stderr,
            )
        ok = False
    if ok:
        print(f"✅ 腳本註冊完整性：{len(pairs)} 對 + {len(singles)} 支單邊皆已納管"
              f"（遞迴掃描 {len(_PAIR_SCAN_DIRS)} 棵 SSOT 樹 + LATEST tools）")
    return ok


def _check_equivalence_groups_fresh(repo_root: Path | None = None) -> bool:
    """4 組異名對等品 stale 自檢（R63，ADR-XPLAT-002 §5 Phase 1-C (a)）。

    每組宣稱「兩支 stem 不同但語意對等」——stale 情境有三種，皆須捕捉：
      1. 其中一支檔案已從磁碟消失（改名/刪除未同步本表）；
      2. 其中一支不再登記於 _SINGLE_SIDED_EXEMPT（已改列其他納管類別卻忘刪本組）；
      3. 兩支 stem 其實相同（不再是「異名」，該走成對納管，不該留在本表）。
    三者皆非磁碟成對掃描（_discover_scripts）能發現的漂移面——那支只管「有沒有納管」，
    不管「兩個手動配對的登記鍵彼此是否仍然對得上」。
    """
    root = repo_root if repo_root is not None else _REPO_ROOT
    ok = True
    for name, (a, b) in _EQUIVALENCE_GROUPS.items():
        for rel in (a, b):
            if not (root / rel).is_file():
                print(f"❌ 異名對等品 stale：{name} 的成員 {rel} 已不存在於磁碟——"
                      f"請同步更新 _EQUIVALENCE_GROUPS 或確認檔案是否被改名/刪除",
                      file=sys.stderr)
                ok = False
            if rel not in _SINGLE_SIDED_EXEMPT:
                print(f"❌ 異名對等品 stale：{name} 的成員 {rel} 已不在 "
                      f"_SINGLE_SIDED_EXEMPT 登記——已改納管類別或被移除卻未同步本組",
                      file=sys.stderr)
                ok = False
        stem_a, stem_b = Path(a).stem, Path(b).stem
        if stem_a == stem_b:
            print(f"❌ 異名對等品 stale：{name} 兩成員 stem 相同（{stem_a}）——"
                  f"已不是『異名』對等品，應改走成對納管（_THINNESS_ENROLLED 或 "
                  f"_MARKER_PAIRS），不該留在 _EQUIVALENCE_GROUPS", file=sys.stderr)
            ok = False
    if ok:
        print(f"✅ 異名對等品 stale 自檢：{len(_EQUIVALENCE_GROUPS)} 組皆新鮮"
              f"（磁碟存在 + 仍登記於 _SINGLE_SIDED_EXEMPT + stem 確實不同）")
    return ok


def _check_tier_classification() -> bool:
    """(b)(d) tier 分類完整性與 tier3/4 硬理由關鍵詞斷言（R63，ADR-XPLAT-002 §5 Phase 1-C）。

    R63 前 `_EXEMPT_PAIRS`／`_SINGLE_SIDED_EXEMPT` 的值是純理由字串——本檢查驗證升級後
    的 `(tier, reason)` tuple：① 值須為二元組；② tier 必須落在 §3.1~3.4 定義的合法集合
    `_VALID_TIERS`；③ reason 非空；④ `tier3_os_primitive`／`tier4_forbidden` 的 reason
    必須額外含至少一個 `_HARD_REASON_KEYWORDS` 關鍵詞（關鍵字比對，同 ADR-XPLAT-001
    §4.3.4 對 C1/C2 已劃的同型邊界——這是防呆，不是語意驗證，見 ADR-XPLAT-002 §6 邊界 4）。
    """
    ok = True
    tables: tuple[tuple[str, dict[str, tuple[str, str]]], ...] = (
        ("_EXEMPT_PAIRS", _EXEMPT_PAIRS),
        ("_SINGLE_SIDED_EXEMPT", _SINGLE_SIDED_EXEMPT),
    )
    for table_name, table in tables:
        for key, entry in table.items():
            if not (isinstance(entry, tuple) and len(entry) == 2):
                print(f"❌ tier 分類：{table_name}[{key!r}] 值須為 (tier, reason) 二元組，"
                      f"實得 {entry!r}", file=sys.stderr)
                ok = False
                continue
            tier, reason = entry
            entry_ok = True
            if tier not in _VALID_TIERS:
                print(f"❌ tier 分類：{table_name}[{key!r}] 的 tier {tier!r} 不在合法集合 "
                      f"{sorted(_VALID_TIERS)}", file=sys.stderr)
                ok = False
                entry_ok = False
            if not reason.strip():
                print(f"❌ tier 分類：{table_name}[{key!r}] 的 reason 為空", file=sys.stderr)
                ok = False
                entry_ok = False
            if entry_ok and tier in (_TIER3_OS_PRIMITIVE, _TIER4_FORBIDDEN):
                if not any(kw in reason for kw in _HARD_REASON_KEYWORDS):
                    print(f"❌ tier 分類：{table_name}[{key!r}]（tier={tier}）的 reason "
                          f"未含任何硬理由關鍵詞 {_HARD_REASON_KEYWORDS}——{tier} 需明確"
                          f"的不可收斂技術理由，非泛泛決策豁免散文", file=sys.stderr)
                    ok = False
            if entry_ok and tier == _UNPINNED and not _UNPINNED_EXIT_RE.search(reason):
                print(f"❌ tier 分類：{table_name}[{key!r}]（tier=unpinned）的 reason "
                      f"未含退場錨點——unpinned＝『不符任一 Tier 定義』，是分類法的"
                      f"『以上皆非』桶，必須明說誰來接：請在 reason 內寫 "
                      f"`退場：未指派` 或 `退場：R<輪號>…`（R67-E24）", file=sys.stderr)
                ok = False
    if ok:
        n = len(_EXEMPT_PAIRS) + len(_SINGLE_SIDED_EXEMPT)
        print(f"✅ tier 分類完整性：{n} 筆（_EXEMPT_PAIRS {len(_EXEMPT_PAIRS)} + "
              f"_SINGLE_SIDED_EXEMPT {len(_SINGLE_SIDED_EXEMPT)}）tier 合法、reason 非空、"
              f"tier3/4 硬理由關鍵詞齊備、unpinned 退場錨點齊備")
    return ok


# ── UEP tier 棘輪（R64，ADR-XPLAT-002 §8 item 12；R67-H14 改基準）─────────────
# WHY：R63 的 `_check_tier_classification()` 只驗證「現況合法」（tier 落在合法集合、
# reason 非空、tier3/4 附硬理由關鍵詞）——它不阻止未來把某筆已核定的 tier3/4 悄悄
# 改回 unpinned，或把已歸類的 tier1/2 打回 unpinned：那樣改一樣通得過
# `_check_tier_classification`（新 tier 本身合法），只是**退步**。
#
# 降級判準只鎖 ADR §8 item 12 逐字指定的兩個方向：
#   (A) tier3_os_primitive／tier4_forbidden → 非 tier3/4（明文封頂類別被悄悄鬆綁）
#   (B) tier1_contract／tier1_adapter／tier2_spec → unpinned（已歸類的契約/spec 被打回未歸類）
# 反方向（維持、升級、或整筆自兩張登記表移除＝已徹底收斂）皆視為合法，不報告——
# 移除是 ADR 明文承認的合法出口，硬擋它會懲罰真正把缺口收斂掉的人。
#
# 🔴🔴 R67-H14：比對基準由 `git show HEAD:<本檔>` 改為**凍結在本檔內的 `_TIER_BASELINE`**。
# R64 落地時照抄 `TestShrinkOnlyRatchet` 的 HEAD 比對形狀，但該形狀在**所有真正消費
# 本檔 rc 的閘門**裡結構性恆真：`tools/git-hooks/pre-push` 與三支 CI workflow 執行時
# 異動**都已經 commit**（CI 更是 checkout 出乾淨樹），HEAD 逐字等於工作樹 ⇒
# previous_map == current_map ⇒ 永遠零違規。實測（沙箱、R67 掃描）：把
# `run_local_nightly` 由 tier4 降為 unpinned 後 **commit**，`check_script_parity.py`
# rc=0、真 pre-push hook 端到端 rc=0、`tools/tests` 1124 passed 與控制組逐字相同——
# 棘輪從來沒擋過任何東西，而 docstring 卻寫著「一旦本檔進入 HEAD，棘輪即永久生效」。
# 另一面 fail-open：`previous is None`（HEAD 無本檔）走綠燈空轉。
#
# 為什麼換成 `_TIER_BASELINE` 不會重蹈恆真覆轍（這是本修法的核心論證）：
#   舊基準是**由 git 狀態導出**的量，而「commit」這個動作本身就會把它同步成當前值；
#   偏偏每一個閘門都跑在 commit 之後 ⇒ 基準與被檢查值在被比較前必定已經相等，
#   比較是退化的（degenerate），與檢查器寫得多嚴格無關。
#   新基準是**簽入原始碼裡的字面常數**：commit 不會動它、checkout 不會動它、CI 乾淨
#   樹也不會動它——只有人手改那幾行才會變。因此「活體登記表」與「基準」是兩個
#   獨立可變的量，比較在任何時點、任何消費者（髒樹／pre-commit／pre-push／CI）
#   都是非退化的。同時整條 git 依賴消失 ⇒ 上述 fail-open 面一併消滅。
#   （形狀＝本 repo 既有的 `_PINNED_SHA256`／`_MIN_EXTRACT_COUNTS` 釘選慣例：要放寬
#    就得在 diff 上顯式改那一行，被複審看見；不是「commit 一下就自動對齊」。）
#   殘餘面（誠實揭露）：同一個 commit 內**同時**改活體 tier 與 `_TIER_BASELINE` 仍可
#   通過——這是所有釘選式棘輪共有的邊界，與「零成本、隱形、自動」的舊行為是不同量級。
#   本性質有機械鎖：`test_ratchet_is_independent_of_git_state`（禁用 subprocess 仍須
#   完整運作），舊實作在該鎖下會直接紅。
_TIER3_4 = frozenset({_TIER3_OS_PRIMITIVE, _TIER4_FORBIDDEN})
_TIER1_2 = frozenset({_TIER1_CONTRACT, _TIER1_ADAPTER, _TIER2_SPEC})
_SELF_REL = "tools/check_script_parity.py"  # git 路徑一律 posix，不用 os.sep

# 凍結基準（R67-H14）：{登記 key: 核定 tier}。維護規則——
#   · 新增登記項 ⇒ 必須同步在此補一筆（否則 `_check_tier_ratchet()` 紅：未涵蓋）。
#     這一步是刻意的：讓每一筆新豁免都在 diff 上現形，而不是靜悄悄多一筆。
#   · 已收斂移出兩張活體登記表的 key **刻意保留**在本表：日後同名項回鍋且 tier 更低，
#     棘輪仍會紅（＝永久記憶，不是垃圾）。
#   · 要把某筆的核定 tier 往下改（＝放寬），必須在同一 commit 顯式改本表該行並在
#     ADR／缺陷帳本具名理由——這是唯一合法出口。
_TIER_BASELINE: dict[str, str] = {
    # ── _EXEMPT_PAIRS（R67 凍結）──
    "AISDLC_SDD/scripts/ci-gate": _UNPINNED,
    "AutoClaude/tools/run_local_nightly": _TIER4_FORBIDDEN,
    "LATEST/tools/init_project": _TIER3_OS_PRIMITIVE,
    "LATEST/tools/install_hooks/install_post_commit": _UNPINNED,
    "LATEST/tools/arch_fitness/run_self_evolution": _UNPINNED,
    # ── _SINGLE_SIDED_EXEMPT（R67 凍結）──
    "tools/macos_smoke_local.sh": _TIER4_FORBIDDEN,
    "tools/windows_smoke_local.ps1": _TIER4_FORBIDDEN,
    "tools/lib/git_hooks_install_common.sh": _TIER1_ADAPTER,
    "tools/lib/GitHooksInstallCommon.ps1": _TIER1_ADAPTER,
    "tools/lib/Find-GitBash.ps1": _TIER2_SPEC,
    "tools/lib/WindowsAppsGuard.ps1": _TIER2_SPEC,
    "tools/lib/windowsapps_guard.sh": _TIER2_SPEC,
    "tools/install_mac_nightly.sh": _TIER3_OS_PRIMITIVE,
    "tools/install_windows_nightly.ps1": _TIER3_OS_PRIMITIVE,
    "AutoClaude/tools/fix_nightly_catchup.ps1": _TIER3_OS_PRIMITIVE,
    "AutoClaude/tools/g0_gate_check.ps1": _TIER3_OS_PRIMITIVE,
    # R76 已整支刪除（真孤兒），依上方維護規則「已收斂移出活體表的 key 刻意保留」留存；
    # `_TIER34_FLOOR` 的課責數把這種 key 仍計入，故刪檔不必也不得下修那個地板。
    "AutoClaude/tools/reschedule_g0_gatecheck.ps1": _TIER3_OS_PRIMITIVE,
    "AutoClaude/tools/run_mutmut_in_docker.sh": _TIER3_OS_PRIMITIVE,
    "AutoClaude/tools/sd06_w3_staging_dryrun.sh": _UNPINNED,
    "AISDLC_SDD/scripts/act-ci.sh": _UNPINNED,
    "AISDLC_SDD/scripts/copy_on_evolve.sh": _UNPINNED,
    "AISDLC_SDD/scripts/pytest_passed_count.sh": _UNPINNED,
    "LATEST/tools/verify_traceability.sh": _UNPINNED,
}

# unpinned 筆數天花板（R67-E24，只准下修）：unpinned＝「不符任一 Tier 定義」的
# 「以上皆非」桶，R67 現值 8/23＝34.8%。`_TIER_BASELINE` 的涵蓋規則擋得住「悄悄
# 多一筆」，但擋不住「多一筆並同步補進 baseline」——本天花板把**總量**也釘住：
# 要新增 unpinned 就得顯式上修這個數字，讓「以上皆非」桶的成長在 diff 上現形。
# 刻意不由 `_TIER_BASELINE` 自動導出（那會隨 baseline 一起長高＝自我對齊，就是
# R67-H14 的恆真陷阱形狀）。收斂掉一筆時請同步下修，維持棘輪張力。
_UNPINNED_CEILING = 8

# tier3/4 筆數地板（R67 round 2，ARCH-R67-03；只准上修）。
# WHY：`_TIER_BASELINE` 的降級規則 (A)(B) 是**逐 key 比對**，而
# `test_baseline_covers_every_live_entry_and_agrees_on_tier` 又要求活體與基準逐字相等
# ⇒「合法 tier 異動必須同時改活體與基準」是常規工作流。於是降級只要**成對**進行就通得過：
# Architect 沙箱實測（INJ-1c）把 `LATEST/tools/init_project` 於兩處同步由
# tier3_os_primitive 改為 tier1_contract，`check_script_parity.py` rc=0、
# `tools/tests/test_check_script_parity.py` 全綠——明文封頂（ADR §3.3「禁止未來輪重辯」）
# 的項目被降級且零訊號，還順帶卸掉 `_HARD_REASON_KEYWORDS` 對 tier3/4 的硬理由義務。
# 修法＝`_UNPINNED_CEILING` 已示範過的那一招的鏡像：一個**不由基準導出**的獨立總量常數。
# 它把兩種編輯在 diff 上分成不同形狀——升級不必動本行，降級則**必須顯式下修本行**。
# 同樣刻意不寫成 `sum(1 for t in _TIER_BASELINE.values() if t in _TIER3_4)`：那會隨基準
# 自我對齊，正是 R67-H14 的恆真陷阱
# （機械鎖＝`test_tier34_floor_is_not_derived_from_the_baseline`）。
#
# 🔴 被數的量＝**tier3/4 課責數**，不是「活體 tier3/4 筆數」：
#     課責數 = 活體仍為 tier3/4 的 key ∪ 基準記為 tier3/4 而**已整筆移出活體表**的 key
# WHY 要多這一項：ADR §8 item 12 明文承認「整筆移出兩張登記表＝已徹底收斂」是合法出口，
# 且既有對照組 `test_converged_entry_removed_from_live_tables_stays_green` 就是在守這件事。
# 若地板只數活體，收斂掉一筆就會逼人下修地板——「硬擋它會懲罰真正把缺口收斂掉的人」
# 正是那條 ADR 出口在防的東西。把已收斂的 key 仍計入課責數，兩種情形就分得開：
#   · 收斂（key 消失、基準保留該筆 tier3/4 記憶）⇒ 課責數不變 ⇒ 綠，零維護。
#   · 降級（key 還在、tier 被改成別的，不論基準有沒有同步改）⇒ 課責數 -1 ⇒ 紅。
# 唯一會合法讓課責數下降的動作是「連基準那一筆也刪掉」，而基準的維護規則本來就寫著
# 已收斂的 key **刻意保留**（永久記憶）；真要刪就得連同下修本行，在 diff 上現形。
_TIER34_FLOOR = 10


def _extract_tier_map_from_source(source: str, dict_name: str) -> dict[str, str] | None:
    """AST 解析原始碼字串裡名為 `dict_name` 的模組層 dict 常數，回傳 {key: tier}。

    tier 值在本檔慣例上以模組常數參照寫成（如 `_UNPINNED`），故先在同一份原始碼裡
    掃過所有模組層 `NAME = "字面字串"` 賦值建一張回代表，再解析目標 dict 每筆的
    tier 元素（tuple 第一項）——可以是字面字串，也可以是能在回代表查到的名稱參照。

    回傳 `None`（而非空字典）代表**抽取失敗**：字典不存在、或其中任一筆值形態
    無法解析（非二元組／key 非字面字串／tier 元素解不出字面字串）。呼叫端必須把
    `None` 當成「棘輪抽取失敗」處理並拒絕靜默通過——同 `ratchet_problems()`
    對常數改名/改寫的既有處理，不能因為抽不到就當作「這張表現在是空的」。
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    name_table: dict[str, str] = {}
    target_dict: ast.Dict | None = None
    for node in tree.body:
        # 本檔的 _EXEMPT_PAIRS／_SINGLE_SIDED_EXEMPT 用型別註記賦值
        # （`_EXEMPT_PAIRS: dict[...] = {...}` ⇒ ast.AnnAssign，非 ast.Assign）；
        # tier 常數（_UNPINNED 等）用普通賦值（ast.Assign）——兩種都要認得，
        # 否則對本檔自己的原始碼會靜默抽空（R64 落地時實測踩到這個坑）。
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.value is not None:
            target_name = node.target.id
            value = node.value
        else:
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            name_table[target_name] = value.value
        elif target_name == dict_name and isinstance(value, ast.Dict):
            target_dict = value

    if target_dict is None:
        return None

    result: dict[str, str] = {}
    for key_node, value_node in zip(target_dict.keys, target_dict.values):
        if not (isinstance(key_node, ast.Constant) and isinstance(key_node.value, str)):
            return None
        if not (isinstance(value_node, ast.Tuple) and len(value_node.elts) == 2):
            return None
        tier_node = value_node.elts[0]
        if isinstance(tier_node, ast.Constant) and isinstance(tier_node.value, str):
            tier = tier_node.value
        elif isinstance(tier_node, ast.Name) and tier_node.id in name_table:
            tier = name_table[tier_node.id]
        else:
            return None
        result[key_node.value] = tier
    return result


def _tier_downgrade_problems(
    previous_map: dict[str, str], current_map: dict[str, str]
) -> list[str]:
    """降級判準核心（唯一實作）：比對兩張 `{key: tier}`，回傳降級說明。

    `tier_ratchet_problems()`（合成上一版原始碼，測試用鑑別力載具）與
    `baseline_ratchet_problems()`（凍結基準，production 路徑）共用本函式——判準只有
    一份，不會出現「測試驗的那條路和 production 走的那條路判準不同」。
    """
    problems: list[str] = []
    for key, prev_tier in sorted(previous_map.items()):
        if key not in current_map:
            continue  # 整筆自兩張登記表移除 = 已徹底收斂，非降級
        cur_tier = current_map[key]
        if prev_tier in _TIER3_4 and cur_tier not in _TIER3_4:
            problems.append(
                f"{key}：tier 由 {prev_tier!r}（明文封頂類別）降為 {cur_tier!r} —— "
                "tier3_os_primitive／tier4_forbidden 一經核定不得悄悄鬆綁（除非整筆"
                "移出登記表，代表已徹底收斂）"
            )
        elif prev_tier in _TIER1_2 and cur_tier == _UNPINNED:
            problems.append(
                f"{key}：tier 由 {prev_tier!r} 降為 {cur_tier!r} —— "
                "已歸類的契約/spec 不得退回未歸類"
            )
    return problems


def _live_tier_map(
    current_exempt_pairs: dict[str, tuple[str, str]] | None,
    current_single_sided: dict[str, tuple[str, str]] | None,
) -> dict[str, str]:
    """兩張活體登記表 → `{key: tier}`（`None` 代表取本模組現行活體表）。"""
    if current_exempt_pairs is None:
        current_exempt_pairs = _EXEMPT_PAIRS
    if current_single_sided is None:
        current_single_sided = _SINGLE_SIDED_EXEMPT
    return {
        **{k: v[0] for k, v in current_exempt_pairs.items()},
        **{k: v[0] for k, v in current_single_sided.items()},
    }


def _tier34_accounted(
    baseline: dict[str, str], current_map: dict[str, str]
) -> list[str]:
    """tier3/4 課責項（唯一實作，R67 round 2 ARCH-R67-03）。

    ＝ 活體仍為 tier3/4 的 key **∪** 基準記為 tier3/4 而已整筆移出活體表的 key。
    後者讓「徹底收斂」（ADR §8 item 12 明文出口）不被地板懲罰——詳細論證見
    `_TIER34_FLOOR` 上方區塊註解。
    """
    live34 = {k for k, t in current_map.items() if t in _TIER3_4}
    converged34 = {
        k for k, t in baseline.items() if t in _TIER3_4 and k not in current_map
    }
    return sorted(live34 | converged34)


def baseline_ratchet_problems(
    current_exempt_pairs: dict[str, tuple[str, str]] | None = None,
    current_single_sided: dict[str, tuple[str, str]] | None = None,
    baseline: dict[str, str] | None = None,
    unpinned_ceiling: int | None = None,
    tier34_floor: int | None = None,
) -> list[str]:
    """**production 棘輪**：活體登記表 vs 凍結基準 `_TIER_BASELINE`（R67-H14）。

    四條規則：
      (A)(B) 降級偵測（委派 `_tier_downgrade_problems()`，判準與 ADR §8 item 12 同）；
      (C) 涵蓋：任何活體 key 未登記於基準 ⇒ 紅。這條同時擋住「刪掉基準那一筆來
          迴避棘輪」——key 還活著而基準沒有它，就是紅；
      (D) unpinned 總量不得超過 `_UNPINNED_CEILING`（R67-E24）；
      (E) tier3/4 總量不得低於 `_TIER34_FLOOR`（R67 round 2 ARCH-R67-03）——(A) 是逐
          key 比對，成對編輯（活體＋基準一起改）即可繞過，實測有效；本條走**總量**
          維度，與 (D) 互為鏡像，成對編輯不影響它。

    刻意**不呼叫 git**：基準是簽入的字面常數，故本函式在髒樹／乾淨樹／CI checkout
    行為完全相同（見上方 R67-H14 論證）。`test_ratchet_is_independent_of_git_state`
    以「禁用 subprocess」機械守住這個性質。
    """
    if baseline is None:
        baseline = _TIER_BASELINE
    if unpinned_ceiling is None:
        unpinned_ceiling = _UNPINNED_CEILING
    if tier34_floor is None:
        tier34_floor = _TIER34_FLOOR

    current_map = _live_tier_map(current_exempt_pairs, current_single_sided)
    problems = _tier_downgrade_problems(baseline, current_map)

    for key in sorted(current_map):
        if key not in baseline:
            problems.append(
                f"{key}：活體登記表有此筆，凍結基準 _TIER_BASELINE 卻沒有 —— "
                "新增登記項必須同步補進 _TIER_BASELINE（填當前 tier）；若是把既有"
                "基準條目刪掉來迴避棘輪，請還原"
            )

    live_unpinned = sorted(k for k, t in current_map.items() if t == _UNPINNED)
    if len(live_unpinned) > unpinned_ceiling:
        problems.append(
            f"unpinned 筆數 {len(live_unpinned)} 超過天花板 {unpinned_ceiling}"
            f"（R67-E24 只准下修）——unpinned 是分類法的『以上皆非』桶，新增等於"
            f"擴大未歸類面；要放寬請顯式上修 _UNPINNED_CEILING 並具名理由。"
            f"現行 unpinned：{live_unpinned}"
        )

    accounted = _tier34_accounted(baseline, current_map)
    if len(accounted) < tier34_floor:
        problems.append(
            f"tier3/4 課責數 {len(accounted)} 低於地板 {tier34_floor}"
            f"（ARCH-R67-03 只准上修）——tier3_os_primitive／tier4_forbidden 是 ADR "
            f"§3.3／§3.4 明文封頂、禁止未來輪重辯的類別。課責數＝活體仍為 tier3/4 者 "
            f"＋ 基準記為 tier3/4 而已整筆移出活體表者（收斂是合法出口，不扣分）；"
            f"會讓它下降的只有『把某筆改成別的 tier』或『連基準那一筆也刪掉』。"
            f"要放寬請顯式下修 _TIER34_FLOOR 並具名理由。現行課責項：{accounted}"
        )
    return problems


def tier_ratchet_problems(
    previous_source: str,
    current_exempt_pairs: dict[str, tuple[str, str]] | None = None,
    current_single_sided: dict[str, tuple[str, str]] | None = None,
) -> list[str]:
    """比對**任意一份「上一版原始碼」**與現版兩張登記表的 tier，回傳降級說明
    （空清單＝零降級；含「整筆移出登記表」視為合法收斂的情況）。

    🔴 R67-H14：production **不再**以 `git show HEAD:<本檔>` 餵本函式——那是恆真陷阱
    （見上方 `_TIER_BASELINE` 區塊論證）。本函式保留的職責是「降級判準本身的鑑別力
    載具」：測試以合成的上一版原始碼逐一注入每種降級／合法形態，證明判準會紅／不會
    誤紅；而判準核心 `_tier_downgrade_problems()` 與 production 的
    `baseline_ratchet_problems()` 是**同一份實作**，故這些注入測試守的就是 production
    走的那條路。AST 抽取器（`_extract_tier_map_from_source`）亦由本函式維繫其
    「抽不到就紅、不得靜默視為空表」的 fail-loud 語意。

    `current_exempt_pairs`／`current_single_sided` 預設吃本模組現行的活體登記表，
    測試可傳入合成表以隔離真 repo 現況。
    """
    problems: list[str] = []

    prev_exempt = _extract_tier_map_from_source(previous_source, "_EXEMPT_PAIRS")
    prev_single = _extract_tier_map_from_source(previous_source, "_SINGLE_SIDED_EXEMPT")
    if prev_exempt is None:
        problems.append(
            "上一版抽不到 _EXEMPT_PAIRS 字典（或其中至少一筆 tier 值形態無法解析）—— "
            "字典被改名／改寫？棘輪等於失效，拒絕靜默通過"
        )
        prev_exempt = {}
    if prev_single is None:
        problems.append(
            "上一版抽不到 _SINGLE_SIDED_EXEMPT 字典（或其中至少一筆 tier 值形態無法解析）—— "
            "字典被改名／改寫？棘輪等於失效，拒絕靜默通過"
        )
        prev_single = {}

    previous_map = {**prev_exempt, **prev_single}
    current_map = _live_tier_map(current_exempt_pairs, current_single_sided)
    problems.extend(_tier_downgrade_problems(previous_map, current_map))
    return problems


def _check_tier_ratchet() -> bool:
    """production 呼叫端：活體登記表 vs 凍結基準 `_TIER_BASELINE`，零違規才綠
    （ADR-XPLAT-002 §8 item 12；比對基準 R67-H14 由 HEAD 改為凍結常數）。

    本函式**不呼叫 git**，因此沒有「基準取不到 ⇒ 綠燈空轉」這個 fail-open 面：
    基準永遠在（它就是本檔的一部分），行為在髒樹／pre-commit／pre-push／CI 乾淨
    checkout 完全一致。
    """
    problems = baseline_ratchet_problems()
    if problems:
        print("❌ tier 棘輪違反（與凍結基準 _TIER_BASELINE 比對，"
              "ADR-XPLAT-002 §8 item 12 / R67-H14）：", file=sys.stderr)
        for p in problems:
            print(f"  · {p}", file=sys.stderr)
        return False
    live = _live_tier_map(None, None)
    print(f"✅ tier 棘輪：與凍結基準 _TIER_BASELINE（{len(_TIER_BASELINE)} 筆）比對，"
          f"零降級、零未涵蓋、unpinned {sum(1 for t in live.values() if t == _UNPINNED)}"
          f"/{_UNPINNED_CEILING}、tier3/4 課責 {len(_tier34_accounted(_TIER_BASELINE, live))}"
          f"/{_TIER34_FLOOR}（含已收斂移出登記表視為合法）")
    return True


# ── AC（Anti-displacement Criterion）涵蓋面宣告（R67-H34）────────────────────
# WHY：§4.2 的 AC＝「描述性常數登記項的誠實全集」，用途是擋「換個地方複雜」。R67 前
# 這個「全集」只存在於 `_print_collapse()` 內一條寫死的七項加總算式裡——實測：新增第
# 8 張模組層登記表（3 筆）後 `AC` 紋風不動、全套 `tools/tests` 零紅，整張表可從判準
# 逃逸；而號稱「獨立重算」的測試逐字複製同一條算式，對這種逃逸天生無訊號。
#
# 修法：把「AC 涵蓋哪些表」變成**資料**（下列兩張清單），`_print_collapse()` 對它求值，
# 測試側則以 AST 掃描兩支工具的模組層登記表、比對「掃到的全集 == 納入 ∪ 具名排除」。
# 掃描是與 production 完全不同的實作路徑（AST vs 名稱清單），故那支測試不再恆真：
# 新增任何一張登記表，若既不納入 AC 也不具名排除，即紅。
_AC_MODULES = ("parity", "thinness")
# 納入 AC 的登記表（模組別名, 常數名）——與 §4.2「描述性常數登記項」定義對應。
_AC_REGISTRY_NAMES: tuple[tuple[str, str], ...] = (
    ("thinness", "_PINNED_SHA256"),
    ("parity", "_THINNESS_ENROLLED"),
    ("parity", "_EXEMPT_PAIRS"),
    ("parity", "_SINGLE_SIDED_EXEMPT"),
    ("parity", "_LATEST_PINNED_SHA256"),
    ("parity", "_LATEST_THINNESS_ENROLLED"),
    ("parity", "_MIN_EXTRACT_COUNTS"),
)
# 具名排除（不計入 AC）＋逐筆理由。排除是決策，必須寫下來被複審看見；漏排即紅。
_AC_EXCLUDED_REGISTRIES: dict[tuple[str, str], str] = {
    ("parity", "_EQUIVALENCE_GROUPS"):
        "不是新增的描述性常數登記，而是既有 _SINGLE_SIDED_EXEMPT 條目之間的『配對關係』"
        "索引（成員本身已計入 _SINGLE_SIDED_EXEMPT）；計入即同一筆重複計數兩次",
    ("parity", "_TIER_BASELINE"):
        "棘輪的凍結基準（R67-H14），是 _EXEMPT_PAIRS/_SINGLE_SIDED_EXEMPT 的影子副本"
        "而非獨立豁免面；計入即把同一批登記重複計數",
    ("parity", "_VALID_TIERS"):
        "Tier 模型的合法值列舉（§3.1~3.4 的類別名），不是登記項",
    ("parity", "_TIER3_4"): "Tier 類別分組常數，不是登記項",
    ("parity", "_TIER1_2"): "Tier 類別分組常數，不是登記項",
    ("parity", "_AC_EXCLUDED_REGISTRIES"):
        "本表自身（AC 涵蓋面的排除清單）＝判準的後設資料，不是被判準管轄的登記面；"
        "計入即自我指涉。（掃描器確實掃到了它並要求表態——這一筆就是表態）",
    ("thinness", "_FORBIDDEN"):
        "業務邏輯樣板關鍵字黑名單（並聯診斷訊號），登記的是『禁止出現的字串』"
        "而非『被豁免／被釘選的腳本』，不屬 §4.2 的描述性常數登記面",
}


def ac_registries() -> dict[tuple[str, str], object]:
    """`{(模組別名, 常數名): 該登記表物件}`——AC 的**唯一**涵蓋面來源。

    `_print_collapse()` 對本函式求值產生 AC；測試以 AST 掃描交叉比對涵蓋面完整性。
    """
    import check_wrapper_thinness as _thinness  # 同目錄，頂部已 sys.path 注入

    mods = {"parity": sys.modules[__name__], "thinness": _thinness}
    return {(mod, name): getattr(mods[mod], name) for mod, name in _AC_REGISTRY_NAMES}


def _print_collapse() -> int:
    """UEP／AC 現查（ADR-XPLAT-002 §4.1/§4.2 R61 Phase 1-C 最小可行切片；R63 擴充逐對
    tier/reason 與異名對等品清單，見 §5 Phase 1-C (a)(b)(c)）。

    在本 ADR 之前，這兩個判準只能靠手跑一支 scratchpad 腳本現查（§2.1）——本函式
    把它變成本工具的第一等公民輸出，供未來棘輪化沿用同一份計算，不必再各自重寫。
    """
    import check_wrapper_thinness as _thinness  # 同目錄，頂部已 sys.path 注入

    # R65：_TLC_TRACK_ENROLLED 已退場（見檔頭 R65 說明）——UEP 不再含該項；
    # AC 改含 _LATEST_PINNED_SHA256／_LATEST_THINNESS_ENROLLED 兩張新表接手其
    # 「描述性常數登記」角色（§4.2）。
    # R67-H34：AC 不再由寫死的 `len(A)+len(B)+…` 算式產生，改為對具名清單
    # `_AC_REGISTRY_NAMES` 動態求值——如此「AC 涵蓋哪些登記表」成為可被
    # `tools/tests/test_check_script_parity.py` 以 AST 掃描交叉比對的資料，
    # 而不是埋在算式裡、只能靠人記得同步的東西。
    uep = len(_EXEMPT_PAIRS)
    ac = sum(len(reg) for reg in ac_registries().values())
    print(f"UEP={uep}")
    print(f"AC={ac}")
    print(f"THINNESS_ENROLLED={len(_THINNESS_ENROLLED)}")
    print(f"PINNED_SHA256={len(_thinness._PINNED_SHA256)}")
    print(f"EXEMPT_PAIRS={len(_EXEMPT_PAIRS)}")
    print(f"SINGLE_SIDED_EXEMPT={len(_SINGLE_SIDED_EXEMPT)}")
    print(f"LATEST_THINNESS_ENROLLED={len(_LATEST_THINNESS_ENROLLED)}")
    print(f"LATEST_PINNED_SHA256={len(_LATEST_PINNED_SHA256)}")
    print(f"MIN_EXTRACT_COUNTS={len(_MIN_EXTRACT_COUNTS)}")
    print(f"EQUIVALENCE_GROUPS={len(_EQUIVALENCE_GROUPS)}")
    print("--- _EXEMPT_PAIRS（key -> tier / reason）---")
    for key in sorted(_EXEMPT_PAIRS):
        tier, reason = _EXEMPT_PAIRS[key]
        print(f"{key}\ttier={tier}\treason={reason}")
    print("--- _SINGLE_SIDED_EXEMPT（key -> tier / reason）---")
    for key in sorted(_SINGLE_SIDED_EXEMPT):
        tier, reason = _SINGLE_SIDED_EXEMPT[key]
        print(f"{key}\ttier={tier}\treason={reason}")
    print("--- _EQUIVALENCE_GROUPS（name -> 兩成員）---")
    for name in sorted(_EQUIVALENCE_GROUPS):
        a, b = _EQUIVALENCE_GROUPS[name]
        print(f"{name}\t{a} <-> {b}")
    return 0


def main() -> int:
    ok = True

    for label, sh_rel, ps1_rel in _MARKER_PAIRS:
        sh_items = _extract_markers(_REPO_ROOT / sh_rel)
        ps1_items = _extract_markers(_REPO_ROOT / ps1_rel)
        if not sh_items or not ps1_items:
            print(f"❌ {label}：抽取到空標籤清單（.sh {len(sh_items)} / .ps1 "
                  f"{len(ps1_items)}）— 宣告 pattern 可能已改，請同步本腳本",
                  file=sys.stderr)
            ok = False
            continue
        ok = _check_extract_floor(label, sh_items, ps1_items) and ok
        ok = _compare(label, sh_items, ps1_items) and ok

    # local_ci_gate 的 gate-call 抽取比對已於 R12 退場（薄殼化收斂，見檔頭）——
    # 該對現由 _THINNESS_ENROLLED 登記、check_wrapper_thinness.py hash 釘選守門。

    # R12 ARCH-R12-3：LATEST 只解析一次，run_tlc 委派引數鎖／LATEST 薄殼釘選與
    # 納管完整性共用結果（R65：原 run_tlc 軌鎖已退場，見上方區塊說明）
    latest_tools = _resolve_latest_tools()
    if latest_tools is None:
        print("❌ LATEST 解析失敗 — 無法比對 LATEST run_tlc 委派引數與薄殼 hash 釘選"
              "（詳見下方納管完整性紅燈）", file=sys.stderr)
        ok = False
    else:
        ok = _check_run_tlc_invocation_parity(latest_tools) and ok
        ok = _check_latest_thinness(latest_tools) and ok
        ok = _check_exit_code_contract(latest_tools) and ok

    ok = _check_pytest_pin() and ok
    ok = _check_git_longpaths_flag_parity() and ok
    ok = _check_thinness_cross_lock() and ok
    ok = _check_latest_thinness_cross_lock() and ok
    ok = _check_pair_enrollment(latest_tools) and ok
    ok = _check_tier_classification() and ok
    ok = _check_equivalence_groups_fresh() and ok
    ok = _check_tier_ratchet() and ok

    if not ok:
        print("\n❌ 雙平台腳本對等檢查未通過 — .sh/.ps1 必須同步修改（見上列 diff）",
              file=sys.stderr)
        return 1
    print(f"\n✅ 雙平台腳本對等檢查通過（{len(_MARKER_PAIRS)} 對標籤腳本 + "
          "LATEST run_tlc 委派引數鎖 + "
          "LATEST 薄殼釘選 + LATEST 薄殼交叉鎖 + run_self_evolution 退出碼契約三方鎖 + "
          "pytest 釘選 + git longpaths 旗標內容鎖 + "
          "成對/單邊註冊完整性；薄殼對子另由 check_wrapper_thinness 釘選）")
    return 0


def cli(argv: list[str]) -> int:  # 拒收層＝唯一讀 sys.argv 之處（WHY 見 _cli_flags.py 檔頭）
    rc = _cli_flags.reject_unknown_argv("check_script_parity.py", argv, ("--print-collapse",))
    return rc if rc is not None else (_print_collapse() if argv else main())


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
