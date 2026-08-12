"""Copy-on-Evolve `.gitignore` 覆蓋 lint 意圖鎖（DEF-37-001）.

每個 case 編碼「為何此行為重要」（Rule 9）：lint 的價值＝在每輪 Copy-on-Evolve 建新版後，
機械偵測「最新演化版缺 runtime 產物排除 block」並 advisory warn，取代「人工記得手補 block」。
故正例（缺 block→回報）與負例（齊備→空清單）對稱覆蓋，並鎖死兩種既有 idiom 相容、註解不偽命中、
只掃最新版（語意版本）三個邊界——其中任一退化都會讓 DEF-37-001 的自動偵測失效（cruft 重新漏網）。
"""
from __future__ import annotations

import os

from scripts import gitignore_coverage_lint as lint


def _mk_repo(tmp_path, versions: list[str], gitignore_text: str | None = None) -> str:
    """建假 repo：建版本目錄 + 選擇性寫 .gitignore；回傳 repo_root。"""
    repo = str(tmp_path)
    for v in versions:
        os.makedirs(os.path.join(repo, v), exist_ok=True)
    if gitignore_text is not None:
        with open(os.path.join(repo, ".gitignore"), "w", encoding="utf-8") as f:
            f.write(gitignore_text)
    return repo


def _full_block(ver: str) -> str:
    """整樹 idiom（v0.13+）：一版三類 runtime 產物排除行。"""
    return (
        f"{ver}/build/reports/\n"
        f"{ver}/arch-fitness.json\n"
        f"{ver}/chaos-report.json\n"
    )


# ── 齊備（負例，不得回報）─────────────────────────────────────────────────────

def test_full_block_passes(tmp_path):
    """最新版三類產物排除行齊備 → 無缺漏。"""
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.20"], _full_block("AISDLC_SDD_v0.20"))
    latest, missing = lint.missing_artifact_tokens(repo)
    assert latest == "AISDLC_SDD_v0.20" and missing == []


def test_negate_idiom_counts_as_covered(tmp_path):
    """v0.05~v0.12 negate idiom（``<ver>/build/reports/*`` + negate）亦算覆蓋（子串命中）。

    為何重要：偵測須相容兩種既有 idiom；若只認整樹 ``/`` 結尾，會對舊 negate 版偽 warn，
    開發者會關掉 lint。``<ver>/build/reports`` 子串對 ``…/build/reports/*`` 亦命中。
    """
    ver = "AISDLC_SDD_v0.08"
    text = (
        f"{ver}/build/reports/*\n"
        f"!{ver}/build/reports/fsm/\n"
        f"{ver}/arch-fitness.json\n"
        f"{ver}/chaos-report.json\n"
    )
    repo = _mk_repo(tmp_path, [ver], text)
    _, missing = lint.missing_artifact_tokens(repo)
    assert missing == []


# ── 缺漏（正例，須回報——DEF-37-001 本體）────────────────────────────────────

def test_new_version_no_block_reports_all(tmp_path):
    """新版建立但 .gitignore 尚無對應 block → 回報三類全缺（DEF-37-001 機械再現）。

    為何重要：這正是缺陷本體——每輪 Copy-on-Evolve 後新版 block 全靠人工手補，
    lint 須在缺漏當下回報，否則 ci-gate runtime 產物會被 git add 夾帶。
    """
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.20"], _full_block("AISDLC_SDD_v0.19"))
    latest, missing = lint.missing_artifact_tokens(repo)
    assert latest == "AISDLC_SDD_v0.20"
    assert missing == [
        "AISDLC_SDD_v0.20/build/reports",
        "AISDLC_SDD_v0.20/arch-fitness.json",
        "AISDLC_SDD_v0.20/chaos-report.json",
    ]


def test_partial_block_missing_detected(tmp_path):
    """部分缺（只補 build/reports，漏 arch-fitness/chaos）→ 精準回報缺的兩類。

    為何重要（突變鎖）：若 RUNTIME_ARTIFACTS 漏掉任一類，部分缺 block 將漏偵測；
    此 case 釘死三類各自獨立檢查（移除任一類即此 case 紅）。
    """
    ver = "AISDLC_SDD_v0.20"
    repo = _mk_repo(tmp_path, [ver], f"{ver}/build/reports/\n")
    _, missing = lint.missing_artifact_tokens(repo)
    assert missing == [f"{ver}/arch-fitness.json", f"{ver}/chaos-report.json"]


def test_comment_line_not_false_positive(tmp_path):
    """``#`` 註解行提及 ``<ver>/build/reports`` 不算覆蓋（須過濾註解）→ 仍回報缺。

    為何重要（突變鎖）：.gitignore 註解常引用路徑說明；若不過濾 ``#`` 行，註解會造成
    偽命中而漏報真缺漏。移除註解過濾即此 case 紅。
    """
    ver = "AISDLC_SDD_v0.20"
    text = (
        f"# {ver}/build/reports/ 為 runtime 取證輸出，須排除（僅註解、非規則）\n"
        f"{ver}/arch-fitness.json\n"
        f"{ver}/chaos-report.json\n"
    )
    repo = _mk_repo(tmp_path, [ver], text)
    _, missing = lint.missing_artifact_tokens(repo)
    assert missing == [f"{ver}/build/reports"]


def test_scans_only_latest_semantic(tmp_path):
    """只掃最新版（語意版本 v0.10 > v0.9）：舊版齊備、最新版缺 → 仍回報最新版缺。

    為何重要：cruft 風險只在最新（實際被 ci-gate 跑而生成產物）的演化版；對齊
    scripts/sdd_version.py SSOT 的 LATEST 數值排序語意（本 lint 為磁碟掃描面），
    且舊版 block 齊備不得掩蓋最新版缺漏。
    """
    repo = _mk_repo(
        tmp_path,
        ["AISDLC_SDD_v0.9", "AISDLC_SDD_v0.10"],
        _full_block("AISDLC_SDD_v0.9"),  # 只補舊版
    )
    latest, missing = lint.missing_artifact_tokens(repo)
    assert latest == "AISDLC_SDD_v0.10" and len(missing) == 3


# ── 邊界 ────────────────────────────────────────────────────────────────────

def test_no_version_dirs_passes(tmp_path):
    """無演化版目錄 → (None, [])，略過。"""
    repo = _mk_repo(tmp_path, [], "")
    assert lint.missing_artifact_tokens(repo) == (None, [])


def test_no_gitignore_treated_as_all_missing(tmp_path):
    """版本存在但無 .gitignore → 無任何排除規則 → 三類全缺（正確：須補）。"""
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.20"], gitignore_text=None)
    _, missing = lint.missing_artifact_tokens(repo)
    assert len(missing) == 3


# ── CLI advisory（不阻擋硬閘）───────────────────────────────────────────────

def test_main_missing_warns_exits_zero(tmp_path, capsys):
    """缺 block → 印 ::warning:: + DEF-37-001 但 exit 0（advisory 不改 ci-gate exit 語意）。"""
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.20"], "")
    assert lint.main([repo]) == 0
    out = capsys.readouterr().out
    assert "::warning::" in out and "DEF-37-001" in out and "AISDLC_SDD_v0.20" in out


def test_main_clean_exits_zero(tmp_path, capsys):
    """齊備 → exit 0 + 『齊備』訊息（無 warning）。"""
    repo = _mk_repo(tmp_path, ["AISDLC_SDD_v0.20"], _full_block("AISDLC_SDD_v0.20"))
    assert lint.main([repo]) == 0
    out = capsys.readouterr().out
    assert "齊備" in out and "::warning::" not in out


def test_main_no_version_exits_nonzero(tmp_path, capsys):
    """AGT-12（R85）：定位不到任何演化版 ⇒ 硬閘非零（advisory 的射程不含「找不到標的」）。

    🔴 被訂正的原意圖逐字保留（訂正協議：禁止靜默覆寫）——本 case 原名
    ``test_main_no_version_exits_zero``，docstring 為「無演化版 → exit 0 + 略過訊息」，
    斷言 ``lint.main([repo]) == 0`` 且輸出含「略過」，即**把 fail-open 釘成契約**。

    為何原意圖是錯的：本 lint 是 advisory（DEF-37-001 P3：缺 block 只 warn 不阻擋），
    但 **advisory 講的是「發現」的處置，不是「找不到標的」的處置**。一個版本目錄都定位
    不到時，它什麼都沒檢查過；此時回 0、且畫面上印的還是 **✅ 綠勾**，與「檢查通過」
    逐字同形 ⇒ 路徑判斷漂掉時失效是靜默的。下方 ``test_main_missing_*`` 系列守的
    advisory 語意（發現 → warn + rc 0）不受本次訂正影響，仍然成立。
    """
    repo = _mk_repo(tmp_path, [], "")
    assert lint.main([repo]) == 1
    assert "::error::" in capsys.readouterr().err


# ── 真實 repo 回歸鎖 ─────────────────────────────────────────────────────────

def test_real_repo_latest_covered():
    """真實 repo 鎖：當前最新演化版的 runtime 產物排除 block 現況齊備（improving_43 前手補維持）。

    為何重要：(1) 證 lint 對真實 .gitignore 不誤報；(2) 此鎖在未來某輪 Copy-on-Evolve
    建新版卻忘補 block 時會轉紅（missing 非空），即 DEF-37-001 自動偵測之回歸保護落地點。
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    latest, missing = lint.missing_artifact_tokens(repo_root)
    assert latest is not None
    assert missing == [], f"最新版 {latest} 缺 .gitignore runtime 產物排除行：{missing}"
