# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""workprogress 家族雜項：RV-OI1（OIR 必敗夾具）、RV-UI1（畫面可見，互動視窗類）、RV-WP22（待驗標記鎖真行程）、
RV-WP09（sandbox 清理＋孤兒 sweep）。全部不開互動視窗、不花額度、不碰真 `~/.claude.json` 與真排程。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

from ..driver import EnvMissing
from ..sandbox import REPO, SANDBOX_PREFIX, Sandbox, projects_dir, slug_of
from . import CaseContext, case
from .prd_px_lib import ev
from .sessionctl_park import PY, run

_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ───────────────────────────── RV-OI1：OIR 必敗夾具 ─────────────────────────────
@case("RV-OI1", "workprogress", refs=("E2E-WP-04", "E2E-WP-33", "E2E-WP-46"))
def rv_oi1(ctx: CaseContext) -> None:
    """OIR 驅動器 E2E 的「必敗」check（E2E-WP-04／33／46 以沙盒 OIR 的 auto 列指向它）。
    只在驅動器環境（驅動器一律注入 `AUTOSDD_UNATTENDED=1`）執行時敗；其他情形判 ENV——
    絕不 PASS：PASS 會讓人誤以為「必敗夾具」有一筆綠色帳列可引。"""
    if not os.environ.get("AUTOSDD_UNATTENDED"):
        raise EnvMissing("RV-OI1 是 OIR 驅動器 E2E 的必敗夾具，不在驅動器環境（AUTOSDD_UNATTENDED）下不執行；一般執行不得算綠")
    ctx.check(False, "RV-OI1 必敗夾具：驅動器 E2E 要的就是這個失敗（E2E-WP-04：第 1 次 fail＋新 drive；第 2 次 escalated）")


# ───────────────────────────── RV-UI1：畫面可見（互動視窗類）─────────────────────────────
_OCR_PROBE = (
    "$ErrorActionPreference='Stop'; "
    "[void][Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]; "
    "$e=[Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages(); "
    "if($null -eq $e){ 'NONE' } else { 'OK ' + $e.RecognizerLanguage.LanguageTag }"
)


@case("RV-UI1", "workprogress", refs=("E2E-WP-61", "REQ-WP-91", "V-SS4", "V-PK4", "V5", "V-W2", "V-C2", "V-F1"))
def rv_ui1(ctx: CaseContext) -> None:
    """畫面可見：沙盒互動視窗觸發 Stop 推回與 `systemMessage`，PrintWindow 擷圖＋Windows.Media.Ocr 比對守衛字樣。
    互動視窗只准經 `interactive.trusted_sandbox`（宿主未受信任＝拒絕開窗＝ENV，不得跳信任框，也不得代寫 `~/.claude.json`）；
    OCR 元件不可用也是 ENV（TCS REQ-WP-91：不算綠）。擷圖與 OCR 比對須在可用桌面互動工作階段真跑——
    目前環境缺任一項即 ENV，這是誠實的未完成，不是通過。"""
    from .. import interactive  # noqa: PLC0415

    if os.name != "nt":
        raise EnvMissing("RV-UI1 的擷圖＋OCR 載具只在 Windows（PrintWindow／Windows.Media.Ocr）")
    r = run(["powershell.exe", "-NoProfile", "-Command", _OCR_PROBE], cwd=REPO, env=dict(os.environ), timeout=60)
    if r.returncode != 0 or not r.stdout.strip().startswith("OK"):
        raise EnvMissing(f"Windows.Media.Ocr 不可用（rc={r.returncode} out={r.stdout.strip()[:80]!r} err={r.stderr.strip()[:120]!r}）⇒ 不算綠")
    sb = interactive.trusted_sandbox(ctx)  # 宿主未信任 ⇒ NotTrusted(EnvMissing)，不開窗
    raise EnvMissing(f"宿主已受信任（{sb.trust_verdict}），但「開窗＋擷圖＋OCR」互動載具需在可用桌面工作階段由掌舵者在場驗證；"
                     "開發棒不得開可見視窗代跑（會干擾使用者桌面），故不假裝通過")


# ───────────────────────────── RV-WP22：待驗標記鎖的真行程 E2E ─────────────────────────────
@case("RV-WP22", "workprogress", refs=("E2E-WP-22", "REQ-WP-23"))
def rv_wp22(ctx: CaseContext) -> None:
    """沙盒 git repo 提交含待驗標記且無 OI id 的 md，子行程真跑 `tools/tests/test_openitems_marker_lock.py`
    （以 `OPENITEMS_LOCK_ROOT` 指向沙盒）：紅並指名 `docs/x.md:2`；補 id 重提交後綠。測試檔的真行程類本身就是這個
    E2E；本案例以 runner 身分再跑一次並核對輸出（不依賴 unittest 回報的字樣以外的東西）。"""
    r = run([PY, str(REPO / "tools" / "tests" / "test_openitems_marker_lock.py"), "MarkerLockRealProcessTest", "-v"],
            cwd=REPO, env={**os.environ, "PYTHONUTF8": "1"}, timeout=240)
    out = r.stdout + r.stderr
    ctx.check(r.returncode == 0, f"標記鎖真行程測試 rc={r.returncode}\n{out[-600:]}")
    ctx.check(re.search(r"Ran 1 test", out) is not None and "OK" in out.splitlines()[-1], f"輸出不是 Ran 1 test／OK：{out[-300:]}")
    ev(ctx, "lock_red_then_green", "沙盒 git repo：無 id 標記 ⇒ 子行程鎖 rc≠0 且指名 docs/x.md:2；補 id 重提交 ⇒ rc 0（Ran 1 test／OK）")


# ───────────────────────────── RV-WP09：沙盒清理＋孤兒 sweep ─────────────────────────────
_SWEEP_SCRIPT = r"""
import json, sys
from pathlib import Path
repo = Path(sys.argv[1]); projects = Path(sys.argv[2]); sessions = Path(sys.argv[3]); tmp = Path(sys.argv[4])
sys.path.insert(0, str(repo / "tools")); sys.path.insert(0, str(repo / "tools" / "lib"))
from lib.realverify import sandbox
res = sandbox.sweep_orphans(projects=projects, sessions=sessions, tmp_root=tmp)
print(json.dumps({"removed": sorted(res["removed"]), "kept": sorted(n for n, _ in res["kept"])}))
"""


@case("RV-WP09", "workprogress", refs=("E2E-WP-09", "REQ-WP-44"))
def rv_wp09(ctx: CaseContext) -> None:
    """① 真沙盒（`Sandbox.create`）＋在真 `~/.claude/projects/<沙盒根 slug>` 放一份逐字稿，`cleanup()` 後沙盒根與該
    slug 目錄都不在（RV 家族結束後不留孤兒的機制）；② 在拋棄式 projects／sessions／tmp 夾具放 2 個孤兒 slug 目錄與 1 個
    「登記檔 cwd 指向」的目錄，子行程真跑 `sweep_orphans`：刪 2 留 1。真機現存孤兒的清除（E2E-WP-09 末句）是破壞性動作，
    由掌舵者同意後 `realverify sweep` 執行，不在本案例範圍。"""
    # ① 沙盒清理
    sb = Sandbox.create(probe_hook=False)
    ctx.sandboxes.append(sb)  # 案例中途失敗也由 runner 清
    slug_dir = projects_dir() / slug_of(sb.root)
    slug_dir.mkdir(parents=True, exist_ok=True)
    (slug_dir / f"{sb.sid}.jsonl").write_text('{"type":"user"}\n', encoding="utf-8", newline="\n")
    ctx.check(slug_dir.is_dir() and sb.root.is_dir(), "夾具沒建起來")
    notes = sb.cleanup()
    ctx.check(not [n for n in notes if n.startswith("RESIDUE")], f"cleanup 回報殘留：{notes}")
    ctx.check(not sb.root.exists() and not slug_dir.exists(), f"cleanup 後沙盒根或 slug 目錄仍在：{sb.root.exists()} {slug_dir.exists()}")
    # ② sweep 夾具（全在拋棄式目錄，不碰真 projects）
    base = Path(tempfile.mkdtemp(prefix=f"{SANDBOX_PREFIX}wp09fx_"))
    try:
        projects, sessions, tmp = base / "projects", base / "sessions", base / "tmp"
        for d in (projects, sessions, tmp):
            d.mkdir()
        orphan1, orphan2, alive = (f"C--Users-x-AppData-Local-Temp-AutoSDD-RV-sbx-{n}" for n in ("orphanaa", "orphanbb", "aliveccc"))
        for name in (orphan1, orphan2, alive):
            (projects / name).mkdir()
            (projects / name / f"{uuid.uuid4()}.jsonl").write_text("{}\n", encoding="utf-8", newline="\n")
        (projects / "C--other-project").mkdir()  # 非沙盒前綴：絕不碰
        # 登記檔：cwd 的 slug＝alive 目錄名（有行程在用）；沙盒根 aliveccc 本身不存在，只靠登記檔保住
        (sessions / "99999.json").write_text(json.dumps({"pid": 99999, "cwd": "C:\\Users\\x\\AppData\\Local\\Temp\\AutoSDD_RV_sbx_aliveccc"}), encoding="utf-8", newline="\n")  # platform-ok: 寫進 session 登記檔的 cwd 文字，不當本機路徑解讀
        r = run([PY, "-I", "-c", _SWEEP_SCRIPT, str(REPO), str(projects), str(sessions), str(tmp)], cwd=REPO, env={**os.environ, "PYTHONUTF8": "1"}, timeout=120)
        ctx.check(r.returncode == 0, f"sweep 子行程 rc={r.returncode} {r.stderr[-400:]}")
        got = json.loads(r.stdout.strip().splitlines()[-1])
        ctx.check(got["removed"] == sorted([orphan1, orphan2]), f"應刪 2 個孤兒：{got}")
        ctx.check(alive in got["kept"] and not (projects / orphan1).exists() and not (projects / orphan2).exists()
                  and (projects / alive).is_dir() and (projects / "C--other-project").is_dir(), f"留／刪結果不對：{got}")
        ev(ctx, "sandbox_cleanup", "Sandbox.cleanup 後沙盒根與其 slug 逐字稿目錄皆不存在")
        ev(ctx, "sweep_two_of_three", f"sweep 刪 2（{got['removed']}）留 1（{[k for k in got['kept'] if k == alive]}）；非沙盒前綴目錄不動")
    finally:
        import shutil  # noqa: PLC0415

        shutil.rmtree(base, ignore_errors=True)
        time.sleep(0)
        _ = sys
