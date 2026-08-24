"""LOC budget tiered policy contract tests — SD_07 W0 T0-5.

ADR-SD07-001 v1.0 §4.2 / §5 / §6：驗證分級制 budget 表生效、絕對紅線 750
不可突破、override 機制可控管。
"""
from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

clb = importlib.import_module("tools.check_loc_budget")


# ── 分級表結構驗證 ───────────────────────────────────────────


def test_loc_tiers_table_matches_adr_sd07_001():
    """ADR-SD07-001 §4.2 表格七層：data / plugin_entry / strategy /
    adapter / contract / service + absolute_limit。"""
    expected = {
        "data": 150,
        "plugin_entry": 250,
        "strategy": 300,
        "adapter": 400,
        "contract": 400,
        "service": 500,
    }
    for tier, budget in expected.items():
        assert tier in clb.LOC_TIERS, f"tier '{tier}' missing"
        assert clb.LOC_TIERS[tier]["budget"] == budget, (
            f"tier '{tier}' budget should be {budget}"
        )
    assert clb.ABSOLUTE_LIMIT == 750


# ── 分級判定（classify_file）─────────────────────────────────


@pytest.mark.parametrize(
    "rel_path,expected_tier,expected_budget",
    [
        ("autoclaude/models/playbook.py", "data", 150),
        ("autoclaude/core/ports/brain.py", "data", 150),
        ("autoclaude/plugins/notification_plugin.py", "plugin_entry", 250),
        ("autoclaude/plugins/checkpoint/plugin.py", "plugin_entry", 250),
        ("autoclaude/core/services/mutation/revise_current.py", "strategy", 300),
        ("autoclaude/infra/adapters/minimax_brain.py", "adapter", 400),
        ("autoclaude/infra/repositories/pg_state_repository.py", "adapter", 400),
        ("autoclaude/core/hookspec.py", "contract", 400),
        ("autoclaude/core/wiring.py", "contract", 400),
        ("autoclaude/execution/types.py", "contract", 400),
        ("autoclaude/core/services/auto_resume.py", "service", 500),
        ("autoclaude/execution/playbook_runner.py", "service", 500),
        ("autoclaude/execution/steps_orchestrator/_impl.py", "service", 500),
    ],
)
def test_classify_file_matches_tier(rel_path, expected_tier, expected_budget):
    tier, budget = clb.classify_file(Path(rel_path))
    assert tier == expected_tier, f"{rel_path} should be tier '{expected_tier}', got '{tier}'"
    assert budget == expected_budget


def test_unclassified_file_defaults_to_absolute_limit():
    """未匹配任何 tier 的檔案以 absolute_limit (750) 為預設 budget。"""
    tier, budget = clb.classify_file(Path("autoclaude/some_new_subsystem/foo.py"))
    assert tier == "unclassified"
    assert budget == clb.ABSOLUTE_LIMIT


# ── 各分級邊界（≥ 6 case 對齊執行指南 G0 驗證）──────────────


def test_data_tier_budget_enforced():
    assert clb.LOC_TIERS["data"]["budget"] == 150


def test_plugin_entry_tier_budget_enforced():
    """Plugin 公開 API ≤ 250；SD_06 W3 落地 12/12 plugin 全合規。"""
    assert clb.LOC_TIERS["plugin_entry"]["budget"] == 250


def test_strategy_tier_budget_enforced():
    assert clb.LOC_TIERS["strategy"]["budget"] == 300


def test_adapter_tier_budget_enforced():
    assert clb.LOC_TIERS["adapter"]["budget"] == 400


def test_contract_tier_budget_enforced():
    assert clb.LOC_TIERS["contract"]["budget"] == 400


def test_service_tier_budget_enforced():
    assert clb.LOC_TIERS["service"]["budget"] == 500


def test_absolute_limit_750_enforced():
    """ADR §4.2 #7 全域絕對紅線。"""
    assert clb.ABSOLUTE_LIMIT == 750


# ── override 機制 ────────────────────────────────────────────


def test_override_file_loads_when_present():
    """`.loc-budget.toml` 存在時可被解析。"""
    overrides = clb.load_overrides()
    assert isinstance(overrides, dict)
    # 規劃階段已豁免 prompt_builder.py（純函式集中）
    assert "autoclaude/decision/prompt_builder.py" in overrides
    entry = overrides["autoclaude/decision/prompt_builder.py"]
    assert entry["tier"] == "service"
    assert "reason" in entry and len(entry["reason"]) > 0


def test_override_applied_in_build_reports():
    """override 應將檔案 tier 與 budget 升級至指定層級。"""
    overrides = clb.load_overrides()
    reports = clb.build_reports(overrides)
    pb = next(
        r for r in reports if r.rel_path == "autoclaude/decision/prompt_builder.py"
    )
    assert pb.tier == "service"
    assert pb.budget == 500
    assert pb.override_reason is not None


# ── 絕對紅線真實掃描 ────────────────────────────────────────


def test_no_file_exceeds_absolute_limit_750():
    """任何層級不得超 750 LOC（紅線 ❌14 + ❌16 防 god-class 復活）。

    🔴 ADR-XPLAT-013 之後 `r.loc` 的**值域換了**：由「非空非註解行」變成「斷言行」
    （docstring／裸字串／整行 `#` 一律免費）。本鎖仍是同一個不變量——「沒有 god-class」
    ——但它現在量的是**判斷邏輯的量**而不是「檔案有多長」，這正是紅線 ❌16 本來想守的東西
    （一支 800 行全是 WHY 註記的檔不是 god-class；一支 800 行全是分支的檔才是）。
    落地當回合實測（否決權複審 M2 訂正——原文寫「全樹零檔上升」是**無母體限定的假數字**）：
    閘門計價母體 286 支（`build_reports()` 207 ＋ `root_tools_reports()` 79）
    的 `新值 > 舊值` 檔數＝**0**；放大到全樹 5557 支 tracked `.py` 則有 **2 支**上升
    （`tests/tools/test_scaffold_sprint_section.py` 116→118、
    `tests/tools/test_snapshot_sync_sprint_skeleton.py` 113→116，機制＝指派給變數的字串裡的
    Markdown 標題被舊判準誤判成 Python 註解而免費），兩支皆未破線
    ⇒ 本鎖不因換值域而放寬，方向只有收緊。
    """
    overrides = clb.load_overrides()
    reports = clb.build_reports(overrides)
    over = [r for r in reports if r.loc > clb.ABSOLUTE_LIMIT]
    assert not over, (
        "absolute red line breach (> 750 LOC):\n"
        + "\n".join(f"  {r.rel_path}: {r.loc}" for r in over)
    )


# ── ADR-XPLAT-013：敘事載體互換的計價不變式 ─────────────────


def test_narrative_carrier_swap_is_priced_identically(tmp_path: Path) -> None:
    """🔴 本次修法的**核心不變式**：同一段敘事換載體，`count_loc` 一行都不該變。

    意圖（Rule 9）：改前 `count_loc` 對「整行 `#`」免費、對 docstring 全額計價，於是
    「把 docstring 逐字改寫成 `#` 前綴」可以在 **raw 行數不變、可執行 AST 節點不變**
    的前提下把計價砍掉一大截——那不是把程式改小，那是換一個計價器看不到的口袋。
    這道門還被工具自己的違規訊息逐字教過（`[TIER-WARN]` 段原本寫「說明文字請寫成 `#`
    註解而非 docstring」，同一次變更已移除）。

    本鎖釘的是**值域**上的關閉：兩份合成檔的敘事**逐字相同**、只差載體，計價必須相等。
    判準會在下列任一情形轉紅（＝它真的有牙）：
      · `count_loc` 退回舊實作（docstring 收費）⇒ A 比 B 高出 docstring 行數；
      · 分類器把整行 `#` 誤判成斷言 ⇒ B 比 A 高。
    """
    narrative = ["這一段是敘事：解釋為什麼要這樣做，不是判斷什麼。",
                 "第二行敘事，用來讓兩種載體都跨多行。",
                 "第三行敘事。"]
    body = "\n".join(("import os", "", "", "def f(x):", "    if x:",
                       "        return os.sep", '    return ""', ""))
    as_docstring = '"""' + "\n".join(narrative) + '"""\n' + body
    as_comments = "".join(f"# {line}\n" for line in narrative) + body

    a, b = tmp_path / "as_docstring.py", tmp_path / "as_comments.py"
    a.write_text(as_docstring, encoding="utf-8")
    b.write_text(as_comments, encoding="utf-8")

    # 前提自檢：兩份檔的敘事行數真的相同、且真的只差載體（否則本鎖比的是別的東西）。
    assert len(as_docstring.splitlines()) == len(as_comments.splitlines())

    loc_a, loc_b = clb.count_loc(a), clb.count_loc(b)
    assert loc_a == loc_b, (
        f"敘事載體互換改變了計價（docstring={loc_a} vs `#`={loc_b}）——套利門還開著："
        "同一段話搬進 `#` 就變便宜，等於鼓勵把 WHY 從 docstring 搬走以換預算。"
    )
    # 鑑別力：計價必須真的只剩下斷言（4 行：import／def／if／兩個 return 之一…），
    # 不是「兩邊都回同一個常數」那種恆真。
    assert loc_a == len([ln for ln in body.splitlines() if ln.strip()]), (
        f"計價 {loc_a} 不等於合成檔的斷言行數 ⇒ 相等可能來自兩邊都算錯同一個量"
    )


def test_a_bare_string_prefix_cannot_buy_a_free_line(tmp_path: Path) -> None:
    """🔴 否決權複審 M1 的回歸鎖：`""; x = 1` 這種裸字串前綴**不得**讓該行免費。

    意圖（Rule 9）：ADR-XPLAT-013 落地的第一版只關掉 docstring↔`#` 那一道門，同一次
    改動卻開了一道更寬的：`Expr(Constant(str))` 的 `(lineno, end_lineno)` 涵蓋整個
    **物理行**，於是在任一行前面加一個裸字串 ＋ 分號就能把該行整行判成敘事。實測在真的
    受計價檔上機械套用（raw 行數與每一個 AST 邏輯節點皆逐字不變）：
    `.claude/hooks/block_destructive_git.py` 的計價 558 → 316（−43.4%）。
    **舊計價對這招是懲罰的**（`; ` 破壞行首井號、免費資格消失），新計價若不補判準就變成
    **獎勵** ⇒ 門不是關掉，是搬家並變寬，而且方向翻轉。

    本鎖釘的是值域上的關閉：同一份程式碼加上前綴之後計價必須**一行都不變**。
    判準會在下列任一情形轉紅：
      · `guard_line_taxonomy._shared_code_lines()` 被移除／改成看 span 涵蓋面
        ⇒ 前綴版變便宜（本鎖的 `==` 紅）；
      · 判準過度收緊、把正常 docstring 也打成斷言 ⇒ 對照組 `plain` 的值上升（第二條斷言紅）。
    """
    body = ("import os", "", "", "def f(x):", "    y = os.sep", "    if x:",
            "        return y", "    return x")
    plain = tmp_path / "plain.py"
    plain.write_text('"""模組敘事：解釋為什麼，不是判斷什麼。"""\n' + "\n".join(body) + "\n",
                     encoding="utf-8")
    # 同一份程式碼，逐行前綴 `""; `（單物理行的 simple statement 才貼，語法保持合法）
    prefixed_body = []
    for line in body:
        stripped = line.lstrip()
        if stripped and stripped.split(" ")[0] not in ("def", "if"):
            indent = line[: len(line) - len(stripped)]
            prefixed_body.append(f'{indent}""; {stripped}')
        else:
            prefixed_body.append(line)
    prefixed = tmp_path / "prefixed.py"
    prefixed.write_text('"""模組敘事：解釋為什麼，不是判斷什麼。"""\n'
                        + "\n".join(prefixed_body) + "\n", encoding="utf-8")

    # 前提自檢：兩份檔的 raw 行數相同（否則比的不是「同一份程式碼」）
    assert len(plain.read_text(encoding="utf-8").splitlines()) == len(
        prefixed.read_text(encoding="utf-8").splitlines())
    assert '""; ' in prefixed.read_text(encoding="utf-8"), "前綴沒貼上去 ⇒ 本鎖沒有受測物"

    loc_plain, loc_prefixed = clb.count_loc(plain), clb.count_loc(prefixed)
    assert loc_prefixed == loc_plain, (
        f"裸字串前綴買到了免費行（無前綴={loc_plain} vs 有前綴={loc_prefixed}）——"
        "套利門仍開著：任一行加 `\"\"; ` 就免費，raw 行數與 AST 節點卻一個都沒少。"
    )
    # 鑑別力：對照組不得因判準收緊而漲價（否則相等可能來自「兩邊都被打成斷言」）
    assert loc_plain == len([ln for ln in body if ln.strip()]), (
        f"對照組計價 {loc_plain} 不等於其斷言行數 ⇒ 判準收得太寬，把敘事也計了價"
    )


def test_count_loc_refuses_to_price_an_unparseable_file(tmp_path: Path) -> None:
    """🔴 語法錯誤不得變成零成本（ADR-XPLAT-013 條文二）。

    意圖：分類器對 `SyntaxError` 的契約是「跳過並標記、三桶歸零」，若計價器照抄那個
    0，最省預算的手法就變成「把檔弄壞」——那是本 ADR 要關的套利門的鏡像版本。
    """
    bad = tmp_path / "broken.py"
    bad.write_text("def f(:\n    pass\n", encoding="utf-8")
    with pytest.raises(clb.UnparseableSourceError):
        clb.count_loc(bad)


# ── 政策版本標記 ────────────────────────────────────────────


def test_policy_version_marker_present_in_env_example():
    """`.env.example` 必含 LOC_BUDGET_POLICY_VERSION=v2 以追蹤政策落地版本。"""
    env_path = PROJECT_ROOT / ".env.example"
    text = env_path.read_text(encoding="utf-8")
    assert "LOC_BUDGET_POLICY_VERSION=v2" in text


# ── 總量 cap 預警帶（ADR-SD07-001 §6.3 觸發條件 ②）───────────
#
# R56 round 5 修正：同輪新增的 TOTAL_WARN_MARGIN / total_warn_band 當時零測試覆蓋，
# 且常數 10 與 ADR §6.3 正文的「cap − 10」是兩處硬編、僅靠 ADR 那句「須與本節同步」
# 的人工宣稱維繫。四方複核判此與本輪 [B]「凡兩份硬編實作互稱鏡射，本 repo 一律建鎖」
# 同形（且該訊號存在的理由正是「把 §6.3 觸發條件 ② 從人眼改為機械」，它自己卻沒有
# 機械保護），故補下列三支鎖：SSOT 對齊、邊界＋rc 不變性、JSON/文字兩模式一致。

_ADR_LOC_POLICY = PROJECT_ROOT / "docs" / "04_planning" / "ADR" / "ADR-SD07-001-loc-policy.md"


def test_total_warn_margin_matches_adr_sd07_001_section_6_3():
    """`TOTAL_WARN_MARGIN` 必須等於 ADR §6.3 觸發條件 ② 的 `cap − N`。

    刻意**從 ADR 正文以正則抽數字**而非再寫死一份 expected —— 後者只會變成第三個
    硬編站點（正是本測試要消滅的形狀）。同時鎖住 §6.3 內覆述那句「＝上式的 N」，
    使該句自稱的同步義務本身也有機械保證：任一站點被單獨改動即翻紅。
    形狀比照同檔 test_loc_tiers_table_matches_adr_sd07_001 的常數釘選慣例。
    """
    text = _ADR_LOC_POLICY.read_text(encoding="utf-8")

    trigger = re.findall(r"total\s*≥\s*cap\s*−\s*(\d+)", text)
    assert len(trigger) == 1, (
        f"ADR §6.3 觸發條件 ② 的 `total ≥ cap − N` 應恰好一處（本鎖賴其唯一性），實得 {trigger}"
    )
    assert int(trigger[0]) == clb.TOTAL_WARN_MARGIN, (
        f"ADR §6.3 觸發條件 ② 寫 cap − {trigger[0]}，但 "
        f"check_loc_budget.TOTAL_WARN_MARGIN = {clb.TOTAL_WARN_MARGIN}；兩站點必須一致"
    )

    restated = re.findall(r"＝上式的\s*(\d+)", text)
    assert len(restated) == 1, (
        f"ADR §6.3 覆述句「（＝上式的 N…）」應恰好一處，實得 {restated}"
    )
    assert int(restated[0]) == clb.TOTAL_WARN_MARGIN, (
        f"ADR §6.3 覆述句寫「＝上式的 {restated[0]}」，與 TOTAL_WARN_MARGIN "
        f"= {clb.TOTAL_WARN_MARGIN} 不符"
    )


@pytest.fixture
def frozen_cap(monkeypatch):
    """回傳 `set_cap(cap)`：把總量 cap 固定為指定值，且**絕不觸碰 .loc_baseline**。

    做法是讓 read_baseline 直接回傳目標 cap，並把 TOTAL_INCREASE_LIMIT 暫設 1.0
    （`cap = int(baseline × limit)`）。**刻意不採**「反推一個 baseline 使
    `int(baseline × 1.20) == 目標 cap`」——1.20 的步進讓約 1/6 的整數 cap 根本無解
    （實測 cap=20363／20369／20375 皆無 baseline 可達），而目標 cap 是由真實 total
    位移而來、會隨程式碼演進漂移，總有一天湊不出來而**假紅**。
    write_baseline 一併換成會炸的 stub，讓「測試不得改寫 repo 的 baseline 檔」
    這條前提也是機械保證，而非撰寫者自律。
    """

    def _boom(value: int) -> None:  # pragma: no cover - 觸發即代表測試設計錯誤
        raise AssertionError(f"本測試不得寫入 .loc_baseline（嘗試寫入 {value}）")

    monkeypatch.setattr(clb, "write_baseline", _boom)
    monkeypatch.setattr(clb, "TOTAL_INCREASE_LIMIT", 1.0)
    # R102 收尾：ADR-XPLAT-013 條文五（E4）新增 cap_basis 獨立審核機制後，check() round-label-ok
    # 改先讀磁碟 .loc_cap_basis；若該檔已落地（--repin-cap 執行後即會如此），
    # cap 會改吃磁碟真值而非本 fixture 透過 read_baseline 注入的合成 cap，讓
    # 本測試組的斷言全部落空。這裡把 read_cap_basis 固定回 None（＝模擬「尚未執行
    # --repin-cap」的退回狀態），讓 cap 繼續由 read_baseline 這個唯一注入點決定，
    # 與 fixture 原本「把總量 cap 固定為指定值」的既有設計意圖一致。
    monkeypatch.setattr(clb, "read_cap_basis", lambda: None)

    def set_cap(cap: int) -> None:
        monkeypatch.setattr(clb, "read_baseline", lambda: cap)

    return set_cap


def _real_total() -> int:
    return sum(r.loc for r in clb.build_reports(clb.load_overrides()))


@pytest.mark.parametrize(
    "cap_offset,expect_warn,expect_rc",
    [
        # cap = total + margin + 1 → 餘裕比預警帶多 1 行，仍在帶外
        (clb.TOTAL_WARN_MARGIN + 1, False, 0),
        # cap = total + margin → total == cap − margin，`>=` 的下緣必須亮
        (clb.TOTAL_WARN_MARGIN, True, 0),
        # cap == total → 貼齊但未破線（R53 實際發生過的狀態）
        (0, True, 0),
        # cap = total − 1 → 破線，改由 [TOTAL] 阻塞訊息接手，不得同時印 [WARN]
        (-1, False, 1),
    ],
)
def test_warn_band_boundary_and_rc_invariant(
    cap_offset, expect_warn, expect_rc, capsys, frozen_cap
):
    """預警帶的四態邊界，以及「WARN 非阻塞 → rc 不得改變」這條不變式。

    WHY：這個訊號的唯一用途是把 ADR §6.3 觸發條件 ② 從人眼改為機械。若日後有人
    (a) 把 `>=` 改成 `>`（下緣靜默失效）、(b) 刪掉 WARN 分支、或 (c) 把
    total_warn_band 併進 has_violation（預警帶變成硬阻塞，CI 無故翻紅），
    在沒有本測試時 pytest 全綠、rc 不變、零訊號。
    """
    total = _real_total()
    frozen_cap(total + cap_offset)

    rc = clb.check()
    out = capsys.readouterr().out

    assert ("[WARN]" in out) is expect_warn, (
        f"cap = total{cap_offset:+d} 時 [WARN] 應{'出現' if expect_warn else '不出現'}；"
        f"實際輸出：\n{out}"
    )
    assert ("[TOTAL]" in out) is (expect_rc == 1), (
        f"cap = total{cap_offset:+d} 時 [TOTAL] 應{'出現' if expect_rc == 1 else '不出現'}；"
        f"實際輸出：\n{out}"
    )
    assert rc == expect_rc, (
        f"cap = total{cap_offset:+d} 時 rc 應為 {expect_rc}（預警帶必須非阻塞）；"
        f"實得 {rc}。若非破線態卻得 rc=1，請先確認 repo 是否另有 tier/absolute/special 違規"
    )


@pytest.mark.parametrize(
    "cap_offset,expect_warn,expect_violation",
    [
        (clb.TOTAL_WARN_MARGIN, True, False),
        (-1, False, True),
    ],
)
def test_warn_band_json_payload_matches_text_mode(
    cap_offset, expect_warn, expect_violation, capsys, frozen_cap
):
    """--json 報表的 total_warn_band / total_warn_margin 必須與文字模式一致。

    WHY：ADR §6.3「必要證據」指定 `--json` 報表，走正規 baseline 校準程序的人
    只看 JSON；若哪天 JSON 欄位被漏改或漏出，該程序的人就看不到觸發條件 ②。
    本測試**真的把同一 cap 下的兩種輸出對跑並互比**（而非各自對著寫死的期望值斷言）
    —— 後者會讓方法名「matches_text_mode」名實不符，正是本輪 [E] 的失效形狀。
    """
    total = _real_total()
    frozen_cap(total + cap_offset)

    rc_text = clb.check()
    text_out = capsys.readouterr().out
    rc_json = clb.check(as_json=True)
    payload = json.loads(capsys.readouterr().out)

    assert payload["total_warn_band"] is ("[WARN]" in text_out), (
        f"--json 的 total_warn_band={payload['total_warn_band']} 與文字模式不一致；"
        f"文字輸出：\n{text_out}"
    )
    assert payload["total_violation"] is ("[TOTAL]" in text_out)
    assert rc_json == rc_text

    assert payload["total_warn_band"] is expect_warn
    assert payload["total_violation"] is expect_violation
    assert payload["total_warn_margin"] == clb.TOTAL_WARN_MARGIN
    assert rc_json == (1 if expect_violation else 0)
