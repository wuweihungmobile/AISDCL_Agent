"""ci-gate 的 pytest 通過數下限（collection-floor lock）不得過期——體檢 S-13 的機械守護。

WHY（Rule 9，測意圖不只測行為）：`scripts/ci-gate.sh` 的 `MIN_TESTS_FROZEN／LATEST／SHARED` 是 DEF-101-386 的
「套件靜默縮小」防線：目錄／pattern 打錯、或誤增 conftest skip-all，通過數會悄悄掉下去而其餘閘門仍全綠。
下限若遠低於實測，這道防線就沒有鑑別力——體檢實測：LATEST 下限 1650 對實測 1979（餘裕 329）、scripts/tests
下限 240 對實測 373（比值 1.55），後者**越過根層 `tools/run_root_unittests.py` 自訂的 `RATCHET_STALE_RATIO`
紅線**（該檔 :38-43 自述 R59 為對齊它才把共享下限由 190 重釘到 240，現又越過同一條紅線）——scripts/tests 可靜默
蒸發約 130 支而全綠。全 repo 搜 `MIN_TESTS_SHARED` 僅 ci-gate.sh 一處、沒有任何測試檢查下限新鮮度，所以「下限
過期」本身不會被任何東西抓到。

判準（本檔 docstring 即規格）：對 ONBOARDING.md §7 表②的 `AISDLC_SDD ci-gate` 三列（凍結基線 v0.01／LATEST／
scripts/tests；macOS 與 Windows 兩欄），取兩欄較大者為「實測」，要求

    實測 ÷ 下限  ≤  `RATCHET_STALE_RATIO`（現為 1.25；一律讀 `tools/run_root_unittests.py` 的常數，不在這裡複寫）

只判**過期**（下限遠低於實測）這一個方向：下限高於實測那一向由閘門自己負責（通過數 < 下限就紅），而表②
是 dated snapshot、本來就可能落後於剛新增的測試（收輪時才由 `sync_onboarding_baselines.py --write --with-slow`
回填），拿落後的文件去判「下限過高」會製造清不掉的假紅。下限的重釘紀律＝「實測值 − 8」（留 8 餘裕吸收跨平台
±1 漂移與 docker daemon 停用的 −3），寫在 ci-gate.sh 各下限旁。

誠實劃界：表②的數字是人（或回填指令）寫的，本測試只能保證「下限不比文件記載的實測低過 20%」；文件本身
落後於真實通過數時，這道鎖看不見（那一面由 `sync_onboarding_baselines.py --check-snapshot` 的指紋機制負責）。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_SDD_ROOT = Path(__file__).resolve().parents[2]  # AISDLC_SDD/
_MONOREPO = _SDD_ROOT.parent
_CI_GATE = _SDD_ROOT / "scripts" / "ci-gate.sh"
_ONBOARDING = _MONOREPO / "ONBOARDING.md"
_ROOT_RUNNER = _MONOREPO / "tools" / "run_root_unittests.py"

_FLOOR_RE = re.compile(r"^MIN_TESTS_(FROZEN|LATEST|SHARED)=(\d+)\b", re.MULTILINE)
_RATIO_RE = re.compile(r"^RATCHET_STALE_RATIO\s*=\s*([0-9]+(?:\.[0-9]+)?)", re.MULTILINE)
# 表②列：`> | AISDLC_SDD `ci-gate` <標籤> | **macOS 數** | **Windows 數** | …`
_ROW_RE = re.compile(
    r"^>\s*\|\s*AISDLC_SDD\s+`ci-gate`\s+(?P<label>[^|]+?)\s*\|\s*\*\*(?P<mac>\d+)\*\*\s*\|\s*\*\*(?P<win>\d+)\*\*\s*\|",
    re.MULTILINE,
)


def parse_floors(ci_gate_text: str) -> dict[str, int]:
    return {name.lower(): int(value) for name, value in _FLOOR_RE.findall(ci_gate_text)}


def parse_table2(onboarding_text: str) -> dict[str, int]:
    """回 `{frozen|latest|shared: 兩欄較大者}`。列的歸類不寫死 LATEST 版號（升版後表②的標籤會跟著變）：
    `v0.01`＝凍結基線、`scripts/tests`＝共享、其餘 `v0.NN`＝LATEST。"""
    out: dict[str, int] = {}
    for match in _ROW_RE.finditer(onboarding_text):
        label = match.group("label").strip()
        if label == "scripts/tests":
            key = "shared"
        elif label == "v0.01":
            key = "frozen"
        elif re.fullmatch(r"v\d+\.\d+", label):
            key = "latest"
        else:
            continue
        out.setdefault(key, max(int(match.group("mac")), int(match.group("win"))))
    return out


def stale_problems(floors: dict[str, int], measured: dict[str, int], limit: float) -> list[str]:
    """純函式：下限過期的清單（空＝健康）。缺列／缺下限一律是問題（fail-loud，不靜默略過）。"""
    problems: list[str] = []
    for key in ("frozen", "latest", "shared"):
        if key not in floors:
            problems.append(f"ci-gate.sh 找不到 MIN_TESTS_{key.upper()} 下限")
            continue
        if key not in measured:
            problems.append(f"ONBOARDING.md §7 表② 找不到 `AISDLC_SDD ci-gate` 的 {key} 列")
            continue
        floor, actual = floors[key], measured[key]
        if floor <= 0:
            problems.append(f"MIN_TESTS_{key.upper()}={floor} 不是正數")
        elif actual / floor > limit:
            problems.append(
                f"MIN_TESTS_{key.upper()}={floor} 對表②實測 {actual} 比值 {actual / floor:.3f} 越過 "
                f"RATCHET_STALE_RATIO={limit}：下限過期，套件可靜默蒸發 {actual - floor} 支仍全綠；"
                f"重釘為 實測 − 8 ＝ {actual - 8}（見 ci-gate.sh 各下限旁的重釘紀律）"
            )
    return problems


def _read(path: Path, what: str) -> str:
    assert path.is_file(), f"找不到 {what}：{path}（本測試需要整個 monorepo 的檔案佈局）"
    return path.read_text(encoding="utf-8")


def test_ci_gate_floors_are_not_stale_against_onboarding_table2() -> None:
    limit = float(_RATIO_RE.search(_read(_ROOT_RUNNER, "tools/run_root_unittests.py")).group(1))  # type: ignore[union-attr]
    floors = parse_floors(_read(_CI_GATE, "scripts/ci-gate.sh"))
    measured = parse_table2(_read(_ONBOARDING, "ONBOARDING.md"))
    assert stale_problems(floors, measured, limit) == []


def test_the_stale_ratio_is_read_from_the_root_runner_not_copied_here() -> None:
    match = _RATIO_RE.search(_read(_ROOT_RUNNER, "tools/run_root_unittests.py"))
    assert match is not None, "根層 run_root_unittests.py 不再有 RATCHET_STALE_RATIO 常數：本測試的判準來源消失"
    assert 1.0 < float(match.group(1)) < 2.0, "常數值不合理（應是略大於 1 的比值）"


def test_the_three_floors_and_three_table_rows_are_all_found() -> None:
    """判準本身不得靜默失明：解析不到任何一列／任何一個下限，上面的比對就是空轉。"""
    assert set(parse_floors(_read(_CI_GATE, "scripts/ci-gate.sh"))) == {"frozen", "latest", "shared"}
    assert set(parse_table2(_read(_ONBOARDING, "ONBOARDING.md"))) == {"frozen", "latest", "shared"}


# ───────────────────── 判準自身的紅綠自證（合成輸入，不靠 repo 現況） ─────────────────────
def test_criterion_is_red_for_the_state_the_review_measured() -> None:
    """體檢實測的過期狀態：scripts/tests 下限 240 對實測 373（1.554 > 1.25）必須紅，且訊息給出重釘值。"""
    problems = stale_problems(
        {"frozen": 1470, "latest": 1650, "shared": 240}, {"frozen": 1478, "latest": 1979, "shared": 373}, 1.25
    )
    assert len(problems) == 1 and "MIN_TESTS_SHARED=240" in problems[0] and "365" in problems[0]
    # LATEST 1650 對 1979 是 1.199，仍在 1.25 之內：本鎖只守紅線，不逼每次都貼著實測
    assert not any("LATEST" in p for p in problems)


def test_criterion_is_green_inside_the_band_and_when_the_floor_is_above_the_doc() -> None:
    assert stale_problems({"frozen": 1470, "latest": 1971, "shared": 365},
                          {"frozen": 1478, "latest": 1979, "shared": 373}, 1.25) == []
    # 文件落後於剛新增的測試（下限高於表②記載值）：不是本鎖的責任（閘門自己會擋），不得誤報
    assert stale_problems({"frozen": 1470, "latest": 2131, "shared": 380},
                          {"frozen": 1478, "latest": 1979, "shared": 373}, 1.25) == []


def test_criterion_is_red_at_the_ratio_boundary() -> None:
    assert stale_problems({"frozen": 100, "latest": 100, "shared": 100},
                          {"frozen": 125, "latest": 125, "shared": 125}, 1.25) == []  # 恰好等於上限＝放行
    assert len(stale_problems({"frozen": 100, "latest": 100, "shared": 100},
                              {"frozen": 126, "latest": 125, "shared": 125}, 1.25)) == 1


@pytest.mark.parametrize("floors,measured", [
    ({"latest": 1, "shared": 1}, {"frozen": 1, "latest": 1, "shared": 1}),   # 缺 frozen 下限
    ({"frozen": 1, "latest": 1, "shared": 1}, {"frozen": 1, "latest": 1}),   # 表② 缺 shared 列
    ({"frozen": 0, "latest": 1, "shared": 1}, {"frozen": 1, "latest": 1, "shared": 1}),  # 下限非正
])
def test_criterion_fails_loudly_on_missing_inputs(floors: dict, measured: dict) -> None:
    assert stale_problems(floors, measured, 1.25), "缺輸入被靜默略過＝判準失明"


def test_table_parser_classifies_rows_without_hardcoding_the_latest_version() -> None:
    text = (
        "> | AISDLC_SDD `ci-gate` v0.01 | **1478** | **1478** | x |\n"
        "> | AISDLC_SDD `ci-gate` v0.31 | **2100** | **2090** | x |\n"
        "> | AISDLC_SDD `ci-gate` scripts/tests | **372** | **373** | x |\n"
        "> | ci-gate v0.30 | **R60 round 3 訂正為 1747** | round 1 | x |\n"  # 史料列：不是表②的格式，不得誤收
    )
    assert parse_table2(text) == {"frozen": 1478, "latest": 2100, "shared": 373}
