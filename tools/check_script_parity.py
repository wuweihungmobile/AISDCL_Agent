#!/usr/bin/env python3
"""雙平台腳本對等機械守護 — .sh / .ps1 三對腳本的 step 標籤一致性 + pytest 釘選一致性
+ 掃描目錄內全部 .sh/.ps1（成對與單邊）的納管完整性（R11 架構改善 C2）。

納管語意（R11 起；R12 ARCH-R12-3 擴面）：tools/、AutoClaude/tools/、AISDLC_SDD/scripts/
三目錄（非遞迴），加上 AISDLC_SDD **LATEST 演化版** `<LATEST>/tools/`（**遞迴**；LATEST
以 scripts/sdd_version.py SSOT 動態解析，解析失敗 fail-loud——parity 只在 repo 內跑，
git 必在；凍結版 v0.01~v0.2X 依鐵律不掃）下的每支 .sh/.ps1 必屬五類之一，否則
fail-loud 列出未納管檔名：
  (1) 成對納管（_MARKER_PAIRS 標籤比對）；(2) 薄殼 hash 釘選（_THINNESS_ENROLLED）；
  (3) run_tlc FSM 軌錨點集合鎖（_TLC_TRACK_ENROLLED，R12）；(4) 成對豁免（_EXEMPT_PAIRS，
  附決策依據）；(5) 單邊豁免（_SINGLE_SIDED_EXEMPT，附決策依據）。LATEST 下的納管
  登記一律用「LATEST/tools/…」相對 key（版本升版 copy-on-evolve 時登記不失效）。
  各清單另有 stale 反向檢查（防清單腐化），詳見 _check_pair_enrollment 區塊註解。

🔴 本工具的邊界（務必先讀）：本工具只機械比對「標籤序列」（數量、順序、字面文字），
**不比對、也無能力比對**各 step 背後的實作內容是否語意對等。**本工具通過（exit 0）
不代表兩份腳本（.sh/.ps1）行為完全一致——只代表兩邊宣告的 step 名字對得上**；
實作漂移（同名 step 做了不同事）仍需人工審查，不可把本工具的綠燈當成雙平台
行為等價的證明。詳見下方「覆蓋範圍與侷限」。

為何需要：bootstrap / integration_gate / run_act 三對腳本的兩側宣稱對等，
但閘門清單過去純靠人工雙改——單邊加減 step 不會有任何機械訊號。本腳本抽取兩版
的「step 標籤字串」逐一比對，不一致即 exit 1（供 root-infra-ci 與本機執行）。
（歷史：local_ci_gate 曾為第四對、以 gate-call 抽取比對；R12 DEF-101-070 ② 收斂為
tools/local_ci_gate.py 單核心＋兩薄殼後，該對改由 check_wrapper_thinness.py hash
釘選守門，gate 清單漂移面已物理消滅、gate-call 抽取隨之退場。）

抽取策略（依各對腳本的固定宣告 pattern）：
  1. tools/bootstrap.{sh,ps1}          — `[n/m]` 步驟標籤（echo / Write-Host 字面值）
  2. tools/integration_gate.{sh,ps1}   — `[n/m]` 段落標籤（run_section / Invoke-Section）
  3. AutoClaude/tools/run_act.{sh,ps1} — `[n/m]` 段落標籤（echo / Write-Host 字面值，
     比照 bootstrap 樣式；R4 複審 Architect P2 補上，原六段僅靠純數字 `# ---- N. ----`
     註解對齊、無機械訊號）

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

已評估但暫緩納入的候選（R4 複審 QA P3）：AutoClaude/tools/install_git_hooks.{sh,ps1}、
AISDLC_SDD/scripts/install-hooks.{sh,ps1} 四支腳本。評估結論：這四支腳本本質是「單一
動作、無多階段」的線性流程（assert worktree → 取 hooks dir → 驗證存在 → git config →
驗證安裝結果），並非像 run_act 那樣有六個語意獨立的段落；真正曾經重複的判定邏輯已於
DEF-101-082 抽出至 `tools/git_hooks_install_common.py` 單一真相源，兩份呼叫端現僅剩
各自平台原生的薄殼呈現層（見 DEF-101-070/080/082），對這四支腳本加 `[n/m]` 標籤會是
為了湊格式而做的形式主義。行為層已由 windows/macos-compat-ci.yml 的安裝/解除/worktree
拒絕三情境實測覆蓋（QA 判定風險低）。決策記事見缺陷帳本 DEF-101-088（closed-by-decision，
本輪暫緩，不排入 marker_pairs）。

使用：
  python3 tools/check_script_parity.py   # 於 repo 內任意 cwd；不一致印 diff 並 exit 1
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌/⚠) 防崩潰保護

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
# 釘選值＝2026-07-16 工具實跑輸出（bootstrap 3 / integration_gate 5 / run_act 6；
# local_ci_gate 9 已隨 R12 薄殼化收斂退場，見檔頭）。刻意刪減 step 時須同步更新
# 本表（工具會在訊息中指路）。
_MIN_EXTRACT_COUNTS = {
    "bootstrap": 3,
    "integration_gate": 5,
    "run_act": 6,
    # R12 ARCH-R12-3：LATEST run_tlc FSM 軌錨點 token multiset（SDD_FSM.cfg/.tla +
    # FLEET_FSM.cfg/.tla×2 + FLEET_FSM_LIVENESS.cfg = 6，2026-07-18 實跑輸出釘選；
    # SD 一審 SD-2 改 multiset 語意後含重複次數）
    "run_tlc_tracks": 6,
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


# ── run_tlc FSM 軌錨點集合鎖（R12 ARCH-R12-3）───────────────────────────────
# WHY：LATEST tools 下四對 .sh/.ps1 過去完全在掃描邊界外，其中 fsm_runtime/formal/
# run_tlc 是唯一有實證漂移前科的對（DEF-101-100：.ps1 曾缺整條 FLEET_FSM 軌），
# 修後零機械鎖。兩側腳本無 [n/m] 標籤，但引用的 FSM 軌檔名（*_FSM*.tla/.cfg）
# 是天然錨點——抽取非註解行的軌 token 做「multiset」比對（排序後含重複次數；
# R12 SD 一審 SD-2：原「排序去重」集合語意對「同 token 多次引用、單側刪其一」
# 不敏感，改保留重複次數即一併攔截），恰好攔「單側缺整條軌」型漂移。
# floor 釘選見 _MIN_EXTRACT_COUNTS['run_tlc_tracks']。
_TLC_TRACK_RE = re.compile(r"\b\w*_FSM\w*\.(?:tla|cfg)\b")


def _extract_tlc_tracks(path: Path) -> list[str]:
    """抽取 FSM 軌錨點：非註解行引用的 *_FSM*.tla/.cfg 檔名 token（排序、含重複）。"""
    text = _strip_comments(
        path.read_text(encoding="utf-8-sig"), is_ps1=path.suffix == ".ps1"
    )
    return sorted(_TLC_TRACK_RE.findall(text))


def _check_run_tlc_tracks(latest_tools: Path) -> bool:
    label = "run_tlc_tracks"
    sh = latest_tools / "fsm_runtime" / "formal" / "run_tlc.sh"
    ps1 = latest_tools / "fsm_runtime" / "formal" / "run_tlc.ps1"
    if not sh.is_file() or not ps1.is_file():
        print(f"❌ {label}：LATEST run_tlc 腳本缺失（{sh} / {ps1}）— 該對若已移除，"
              f"請同步更新 _TLC_TRACK_ENROLLED 與本檢查", file=sys.stderr)
        return False
    sh_tracks = _extract_tlc_tracks(sh)
    ps1_tracks = _extract_tlc_tracks(ps1)
    if not sh_tracks or not ps1_tracks:
        print(f"❌ {label}：抽取到空軌清單（.sh {len(sh_tracks)} / .ps1 "
              f"{len(ps1_tracks)}）— 宣告 pattern 可能已改，請同步本腳本",
              file=sys.stderr)
        return False
    ok = _check_extract_floor(label, sh_tracks, ps1_tracks)
    return _compare(f"{label}（LATEST FSM 軌錨點集合）", sh_tracks, ps1_tracks) and ok


def _check_thinness_cross_lock() -> bool:
    """parity↔thinness 兩份登記清單交叉鎖（R12 QA 一審 QA-1）。

    WHY：_THINNESS_ENROLLED（本檔）與 check_wrapper_thinness._PINNED_SHA256 是兩份
    獨立字面清單——同一 commit 雙邊各刪一行即雙工具全綠（hash 值不可測，但**鍵集合
    可測**）。此鎖斷言每個 thinness 登記 stem 的 .sh 與 .ps1 都在 pin 表，反向多餘
    pin（表內出現未登記 stem）亦紅，杜絕「登記與釘選各自腐化」的零訊號窗。"""
    import check_wrapper_thinness as _thinness  # 同目錄，頂部已 sys.path 注入

    pinned = set(_thinness._PINNED_SHA256)
    expected = {f"{stem}{ext}" for stem in _THINNESS_ENROLLED for ext in (".sh", ".ps1")}
    missing = sorted(expected - pinned)
    extra = sorted(pinned - expected)
    ok = True
    for rel in missing:
        print(f"❌ thinness 交叉鎖：{rel} 已登記 _THINNESS_ENROLLED 但不在 "
              f"check_wrapper_thinness._PINNED_SHA256 — 薄殼宣稱無 hash 釘選守門",
              file=sys.stderr)
        ok = False
    for rel in extra:
        print(f"❌ thinness 交叉鎖：{rel} 在 _PINNED_SHA256 但其 stem 未登記 "
              f"_THINNESS_ENROLLED — 兩清單腐化（請同步）", file=sys.stderr)
        ok = False
    if ok:
        print(f"✅ thinness 交叉鎖：{len(_THINNESS_ENROLLED)} 對薄殼登記與 "
              f"{len(pinned)} 支 hash 釘選鍵集合一致")
    return ok


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


# ── 成對/單邊腳本註冊完整性（enrollment 發現鎖）— R10 拍板案(a)，DEF-101-134；
#    R11 架構改善 C2 擴充至單邊 ─────────────────────────────────────────────────
# 過去「新增一對同名 .sh/.ps1 而不掛任何守門」零機械訊號（marker_pairs 與 thinness
# 釘選對象皆硬編碼清單，磁碟上長出新對子沒人發現）。此檢查掃描宣告目錄（非遞迴）
# 下的**所有** .sh/.ps1，斷言每支必屬四類之一：{成對 parity 標籤比對, 薄殼 thinness
# hash 釘選, 成對明文豁免（附決策依據）, 單邊明文豁免（附決策依據）}，否則
# fail-loud 列出未納管檔名（R11 前單邊腳本零訊號）；並反向檢查各註冊清單無 stale
# 條目（防清單腐化）——單邊豁免的 stale 含兩種：檔案已消失、或對邊已出現（不再
# 是單邊，須改登記為成對類）。
_MARKER_PAIRS = [
    ("bootstrap", "tools/bootstrap.sh", "tools/bootstrap.ps1"),
    ("integration_gate", "tools/integration_gate.sh", "tools/integration_gate.ps1"),
    ("run_act", "AutoClaude/tools/run_act.sh", "AutoClaude/tools/run_act.ps1"),
]
_PAIR_SCAN_DIRS = ("tools", "AutoClaude/tools", "AISDLC_SDD/scripts")
# LATEST 納管 key 前綴（R12 ARCH-R12-3）：登記用「相對 LATEST 的路徑」，版本升版
# （copy-on-evolve）時登記不失效；實體路徑由 _resolve_latest_tools() 動態解析。
_LATEST_PREFIX = "LATEST/tools/"
# tools/check_wrapper_thinness.py hash 釘選（R12 起 local_ci_gate 收斂為薄殼＋
# tools/local_ci_gate.py 單核心後加入，DEF-101-070 ②；gate-call 抽取比對隨之退場）
_THINNESS_ENROLLED = {"tools/dev_start", "AutoClaude/tools/local_ci_gate"}
# run_tlc FSM 軌錨點集合鎖（R12；見 _check_run_tlc_tracks 區塊註解）
_TLC_TRACK_ENROLLED = {"LATEST/tools/fsm_runtime/formal/run_tlc"}
_EXEMPT_PAIRS = {
    "AutoClaude/tools/install_git_hooks": (
        "DEF-101-088 closed-by-decision：判定邏輯已下沉 tools/git_hooks_install_common.py "
        "單一真相源，殼層無標籤錨點"
    ),
    "AISDLC_SDD/scripts/install-hooks": "DEF-101-088 closed-by-decision：同 install_git_hooks",
    "AISDLC_SDD/scripts/ci-gate": (
        "ci-gate.ps1 為薄委派殼（Find-GitBash → bash ci-gate.sh 單一真相源），非第二實作"
    ),
    "AutoClaude/tools/run_local_nightly": (
        ".ps1=Windows 深度 7-stage nightly、.sh=mac 薄聚合器串接既有腳本，"
        "語意刻意不同、不做標籤對等比對；R11 Architect D1 拍板"
    ),
    # ── LATEST 版 tools（R12 ARCH-R12-3 親讀定類；run_tlc 走 _TLC_TRACK_ENROLLED 機械鎖）──
    "LATEST/tools/init_project": (
        "legacy v3.x 初始化精靈雙原生實作，無 [n/m]/gate 宣告錨點可機械抽取；"
        "R12 親讀定類豁免（互動流程差異屬平台原生呈現層）"
    ),
    "LATEST/tools/install_hooks/install_post_commit": (
        "R11 D1：兩產生器輸出逐位元一致取證＋LATEST 解析委派 scripts/sdd_version.py "
        "SSOT（DEF-101-133），殼層無標籤錨點"
    ),
    "LATEST/tools/arch_fitness/run_self_evolution": (
        "FSE 有界驅動器雙原生實作，無標籤錨點（.sh echo FSE_* vs .ps1 函式化）；"
        "dry-run 安全預設兩側一致，R12 親讀定類豁免"
    ),
}
# 單邊豁免清單（R11 架構改善 C2）：掃描目錄內只有 .sh 或只有 .ps1 單邊存在的腳本，
# 必須在此附決策依據登記，否則 fail-loud（過去單邊腳本零訊號）。
_SINGLE_SIDED_EXEMPT = {
    # 兩平台 smoke 聚合器互為對等品但 stem 刻意不同（macos_smoke_local ↔
    # windows_smoke_local），非同名對；行為層由 macos/windows-compat-ci.yml 覆蓋
    "tools/macos_smoke_local.sh": "對等品=windows_smoke_local.ps1（stem 刻意不同）",
    "tools/windows_smoke_local.ps1": "對等品=macos_smoke_local.sh（stem 刻意不同）",
    # Windows schtasks 排程家族三支（ONBOARDING.md §8 明文 Windows-only、無 .sh 對等；
    # run_local_nightly 於 R11 已成對——mac .sh 薄聚合器落地——移登記至 _EXEMPT_PAIRS）
    "AutoClaude/tools/fix_nightly_catchup.ps1": "schtasks 排程家族（ONBOARDING §8）",
    "AutoClaude/tools/g0_gate_check.ps1": "schtasks 排程家族（ONBOARDING §8）",
    "AutoClaude/tools/reschedule_g0_gatecheck.ps1": "schtasks 排程家族（ONBOARDING §8）",
    # bash-only 工具（ONBOARDING.md §6 明文無 .ps1 對等，Windows 以 Git Bash 執行）
    "AutoClaude/tools/run_mutmut_in_docker.sh": "bash-only 工具（ONBOARDING §6）",
    "AutoClaude/tools/sd06_w3_staging_dryrun.sh": "bash-only 工具（ONBOARDING §6）",
    "AISDLC_SDD/scripts/act-ci.sh": "bash-only 工具（ONBOARDING §6）",
    "AISDLC_SDD/scripts/copy_on_evolve.sh": "bash-only 工具（ONBOARDING §6）",
    "AISDLC_SDD/scripts/pytest_passed_count.sh": "bash-only 工具（ONBOARDING §6）",
    # LATEST 版 tools（R12 ARCH-R12-3）
    "LATEST/tools/verify_traceability.sh": (
        "bash-only legacy 追溯鏈驗證工具（v1.1-SDD），歷來無 .ps1 對等；"
        "Windows 以 Git Bash 執行"
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
    return (parity | _THINNESS_ENROLLED | _TLC_TRACK_ENROLLED
            | set(_EXEMPT_PAIRS))


def _registered_path(rel: str, latest_tools: Path | None) -> Path | None:
    """登記 key → 實體路徑（LATEST/tools/… key 需經 LATEST 解析；失敗回 None）。"""
    if rel.startswith(_LATEST_PREFIX):
        if latest_tools is None:
            return None
        return latest_tools / rel[len(_LATEST_PREFIX):]
    return _REPO_ROOT / rel


def _discover_scripts(latest_tools: Path | None) -> tuple[list[str], list[str]]:
    """掃描宣告目錄（非遞迴）＋ LATEST tools（遞迴，R12）→（成對 stem, 單邊相對路徑）。"""
    pairs: list[str] = []
    singles: list[str] = []
    for rel_dir in _PAIR_SCAN_DIRS:
        d = _REPO_ROOT / rel_dir
        if not d.is_dir():
            continue
        sh_stems = {p.stem for p in d.glob("*.sh")}
        ps1_stems = {p.stem for p in d.glob("*.ps1")}
        pairs.extend(f"{rel_dir}/{stem}" for stem in sorted(sh_stems & ps1_stems))
        singles.extend(f"{rel_dir}/{stem}.sh" for stem in sorted(sh_stems - ps1_stems))
        singles.extend(f"{rel_dir}/{stem}.ps1" for stem in sorted(ps1_stems - sh_stems))
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
            print(
                f"❌ 單邊豁免 stale：{s} 的對邊腳本已出現（不再是單邊）—— 請自 "
                f"_SINGLE_SIDED_EXEMPT 移除，並將該對依納管類別語意重新納管",
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
              f"（掃描 {len(_PAIR_SCAN_DIRS)} 目錄 + LATEST tools 遞迴）")
    return ok


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

    # R12 ARCH-R12-3：LATEST 只解析一次，run_tlc 軌鎖與納管完整性共用結果
    latest_tools = _resolve_latest_tools()
    if latest_tools is None:
        print("❌ run_tlc_tracks：LATEST 解析失敗 — 無法比對 LATEST run_tlc FSM 軌"
              "（詳見下方納管完整性紅燈）", file=sys.stderr)
        ok = False
    else:
        ok = _check_run_tlc_tracks(latest_tools) and ok

    ok = _check_pytest_pin() and ok
    ok = _check_thinness_cross_lock() and ok
    ok = _check_pair_enrollment(latest_tools) and ok

    if not ok:
        print("\n❌ 雙平台腳本對等檢查未通過 — .sh/.ps1 必須同步修改（見上列 diff）",
              file=sys.stderr)
        return 1
    print("\n✅ 雙平台腳本對等檢查通過（3 對標籤腳本 + LATEST run_tlc 軌鎖 + "
          "pytest 釘選 + 成對/單邊註冊完整性；薄殼對子另由 check_wrapper_thinness 釘選）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
