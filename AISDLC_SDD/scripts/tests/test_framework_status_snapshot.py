"""框架版本/計數 SSOT 快照閘門意圖鎖.

每個 case 編碼「為何此行為重要」（Rule 9）：本閘門的價值＝讓「版本不斷累積（Copy-on-Evolve）
仍要人去記得改多處文件」這件事從流程消失——計數一律從磁碟/權威源實算成唯一真相源
FRAMEWORK_STATUS.md，ci-gate `--check` 機械守新鮮。故覆蓋三組不變式：
  (1) 計數正確（agents core/spec/runtime、scenarios、skills、governance、templates md+yaml）；
  (2) 版本端點動態正確（baseline=最低、latest=最高，且跨 v0.09→v0.10 十位數邊界不退化，DEF-19-002 教訓）；
  (3) 閘門語意（fresh→0、stale→1、缺檔→1，且新增更高版本 → 自動 stale 直到重生）。
任一退化都會讓「多檔漂移/遺漏」死灰復燃。
"""
from __future__ import annotations

import os

from scripts import framework_status_snapshot as fss


def _touch(path: str, text: str = "") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _mk_version(
    repo: str,
    ver: str,
    *,
    core: int = 7,
    specialized: int = 18,
    runtime: int = 4,
    scenarios: int = 10,
    skills: int = 42,
    rules: int = 38,
    tmpl_md: int = 56,
    tmpl_yaml: int = 3,
    workflows: int | None = 23,
) -> None:
    """建一個資產數量可控的假版本目錄。specialized 含 runtime 個 sdd-* + 其餘一般。"""
    base = os.path.join(repo, ver)
    for i in range(core):
        _touch(os.path.join(base, "agent", "core", f"{i:02d}.core-zh.yaml"))
    for i in range(runtime):
        _touch(os.path.join(base, "agent", "specialized", f"sdd-rt-{i}-zh.yaml"))
    for i in range(specialized - runtime):
        _touch(os.path.join(base, "agent", "specialized", f"spec-{i}-zh.yaml"))
    for i in range(scenarios):
        os.makedirs(os.path.join(base, "scenarios", f"scn{i}"), exist_ok=True)
    for i in range(skills):
        os.makedirs(os.path.join(base, ".claude", "skills", f"skill{i}"), exist_ok=True)
    for i in range(rules):
        _touch(os.path.join(base, "governance", "rules", f"R-9.{i}-x.yaml"))
    # 多數模板放一層深（docs_template/sdd/<cat>/）；但 tmpl_md>=1 時把最後 1 個放「兩層深」
    # （docs_template/sdd/<cat>/<sub>/），確保 count_metrics 的 recursive=True 有鑑別力——
    # 拿掉 recursive 後此深層模板會漏算 → templates_md 期望值對不上 → 測試轉紅（突變可抓）。
    for i in range(max(tmpl_md - 1, 0)):
        _touch(os.path.join(base, "docs_template", "sdd", "cat", f"T{i}-TEMPLATE.md"))
    if tmpl_md >= 1:
        _touch(os.path.join(base, "docs_template", "sdd", "cat", "sub", "T-DEEP-TEMPLATE.md"))
    for i in range(tmpl_yaml):
        _touch(os.path.join(base, "docs_template", "sdd", "api", f"C{i}-TEMPLATE.yaml"))
    if workflows is not None:
        _touch(
            os.path.join(base, "workflow", "README.md"),
            f"提供若干 Workflows，共 {workflows} 個工作流，涵蓋完整生命週期。",
        )


# ── (1) 計數正確 ──────────────────────────────────────────────────────────────

def test_count_metrics_matches_disk(tmp_path):
    """計數＝磁碟實掃；agents_total=core+spec、runtime=sdd-* 子集、templates=md+yaml。"""
    repo = str(tmp_path)
    _mk_version(repo, "AISDLC_SDD_v0.18", core=7, specialized=19, runtime=5,
                rules=39, tmpl_md=56, tmpl_yaml=3, workflows=23)
    m = fss.count_metrics(os.path.join(repo, "AISDLC_SDD_v0.18"))
    assert m["agents_core"] == 7
    assert m["agents_specialized"] == 19
    assert m["agents_total"] == 26
    assert m["agents_runtime"] == 5
    assert m["scenarios"] == 10
    assert m["skills"] == 42
    assert m["governance_rules"] == 39
    assert m["templates_md"] == 56
    assert m["templates_yaml"] == 3
    assert m["templates_total"] == 59
    assert m["workflows"] == 23


def test_workflows_declared_parsed_from_readme(tmp_path):
    """workflows 取 workflow/README.md 宣稱數（curated，非檔數）；缺 README → None。"""
    repo = str(tmp_path)
    _mk_version(repo, "AISDLC_SDD_v0.18", workflows=23)
    assert fss.count_metrics(os.path.join(repo, "AISDLC_SDD_v0.18"))["workflows"] == 23
    _mk_version(repo, "AISDLC_SDD_v0.19", workflows=None)  # 無 README
    assert fss.count_metrics(os.path.join(repo, "AISDLC_SDD_v0.19"))["workflows"] is None


# ── (2) 版本端點動態正確 ──────────────────────────────────────────────────────

def test_baseline_and_latest_endpoints(tmp_path):
    """baseline=最低語意版、latest=最高；不寫死故版本累積自動跟上。"""
    repo = str(tmp_path)
    for v in ["AISDLC_SDD_v0.01", "AISDLC_SDD_v0.07", "AISDLC_SDD_v0.18"]:
        _mk_version(repo, v)
    vers = fss.discover_frozen_versions(repo)
    assert fss._baseline_version(vers) == "AISDLC_SDD_v0.01"
    assert fss.latest_version(vers) == "AISDLC_SDD_v0.18"


def test_two_digit_minor_boundary(tmp_path):
    """DEF-19-002 教訓：v0.09→v0.10 十位數邊界，latest 須選 v0.10 而非字典序的 v0.09。"""
    repo = str(tmp_path)
    for v in ["AISDLC_SDD_v0.09", "AISDLC_SDD_v0.10"]:
        _mk_version(repo, v)
    assert fss.latest_version(fss.discover_frozen_versions(repo)) == "AISDLC_SDD_v0.10"


# ── (3) 閘門語意 ──────────────────────────────────────────────────────────────

def test_check_fresh_then_stale_then_missing(tmp_path):
    """fresh→0；資產變動（新版出現）→stale→1；重生→0；缺檔→1。"""
    repo = str(tmp_path)
    _mk_version(repo, "AISDLC_SDD_v0.01")
    _mk_version(repo, "AISDLC_SDD_v0.18", core=7, specialized=19, runtime=5, rules=39)

    # 缺檔 → 1
    assert fss.main(["--check", "--repo-root", repo]) == 1
    # 生成後 fresh → 0
    assert fss.main(["--write", "--repo-root", repo]) == 0
    assert fss.main(["--check", "--repo-root", repo]) == 0

    # 模擬 Copy-on-Evolve 新增更高版本 → latest 翻新 → 內容變 → stale → 1
    _mk_version(repo, "AISDLC_SDD_v0.19", core=7, specialized=20, runtime=6, rules=40)
    assert fss.main(["--check", "--repo-root", repo]) == 1
    # 重生即恢復新鮮（這就是「版本累積不再多檔漂移」的機械保證）
    assert fss.main(["--write", "--repo-root", repo]) == 0
    assert fss.main(["--check", "--repo-root", repo]) == 0


def test_render_has_both_columns(tmp_path):
    """render 同時呈現凍結基線與最新演化版兩欄，且最新版號出現於輸出。"""
    repo = str(tmp_path)
    _mk_version(repo, "AISDLC_SDD_v0.01")
    _mk_version(repo, "AISDLC_SDD_v0.18", specialized=19, runtime=5, rules=39)
    out = fss.render(repo)
    assert "AISDLC_SDD_v0.01" in out and "AISDLC_SDD_v0.18" in out
    assert "凍結基線" in out and "最新演化版" in out
    assert "version-agnostic" in out  # 自帶「指向本檔、勿重複數字」的治理說明
