"""S-10／F-8：FSM 專案名規則（`app/fsm_names.py`）——鏡像與輸出域判準。

WHY 這些測試存在：SDD 的 `sanitize_component` 會產生含 CJK、空白、括號、`+`、`@` 的檔名；
舊白名單 `^[A-Za-z0-9._-]{1,128}$` 把它們全拒成 404／errors，Console 看不到那個專案的 FSM 狀態。
鏡像若悄悄與 SDD 側漂移，同樣的缺陷會換個樣子再出現，所以對拍直接載入 SDD 的原始檔逐樣本比。
"""
from __future__ import annotations

import importlib.util
import random
import unicodedata
from pathlib import Path
from types import ModuleType

import pytest

from app.fsm_names import MAX_COMPONENT_LEN, fsm_component, is_fsm_project_name

_SANITIZER = (Path(__file__).resolve().parents[3] / "AISDLC_SDD" / "scripts"
              / "component_sanitizer.py")

#: 體檢 S-10 的五個專案名（SDD 側都能產生檔名、舊白名單全拒）＋ADR §7.4 乾跑樣本中的邊緣案例。
S10_NAMES = ("訂單系統", "Order System", "proj(v2)", "a+b", "名稱含@符號")
EDGE_NAMES = (
    "a:b", "x/y", "a\\b", 'q"r', "p|q", "wh?", "st*r", "<tag>", "CON", "con.txt", "NUL .log",
    "COM1", "COM²", "CONIN$", "LPT9.yaml", "  padded  ", "dots...", "..", ".", "...", "", "   ",
    "a" * 200, "訂" * 200, "e\N{COMBINING ACUTE ACCENT}cole", "école", "tab\there", "nl\nx",
    "del\x7fx", "名稱 含 空白", "line1\r\nline2", "ends with dot.", "ends with space ", " leading",
    "CON" + " " * 3 + "." + "x" * 100, "a" + "\N{IDEOGRAPHIC SPACE}" * 100 + "b",
    "z" * 79 + ".", "z" * 79 + " ",
)


def _load_sanitizer() -> ModuleType:
    if not _SANITIZER.is_file():
        pytest.skip("找不到 AISDLC_SDD/scripts/component_sanitizer.py"
                    "（不在 monorepo 內的 checkout）")
    spec = importlib.util.spec_from_file_location("_sdd_component_sanitizer", _SANITIZER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fuzz_corpus(count: int = 600) -> list[str]:
    """固定種子的屬性測試語料：CJK、空白變體、禁用字元、點、保留名片段、組合記號，長度跨 80 的邊
    界。"""
    rng = random.Random(115)
    pool = list("abcXYZ019 ._-+@()") + list('<>:"|?*\\/') + list("訂單系統名稱專案測試") + [
        "\N{IDEOGRAPHIC SPACE}", "\N{NO-BREAK SPACE}", "\N{EM SPACE}", "\t", "\x00", "\x1f",
        "\x7f", "\N{COMBINING ACUTE ACCENT}", "é", "e\N{COMBINING ACUTE ACCENT}",
        "CON", "NUL", "COM1", "LPT2", ".", "..", " ",
    ]
    corpus = []
    for _ in range(count):
        length = rng.choice((1, 2, 5, 20, 79, 80, 81, 120, 200))
        corpus.append("".join(rng.choice(pool) for _ in range(length)))
    return corpus


# ── 對拍：Bridge 的鏡像＝SDD 的 sanitize_component ───────────────────────────────────────
def test_the_mirror_matches_sdd_sanitize_component_on_every_sample() -> None:
    sdd = _load_sanitizer()
    samples = [*S10_NAMES, *EDGE_NAMES, *_fuzz_corpus()]
    mismatches = [(s, sdd.sanitize_component(s), fsm_component(s)) for s in samples
                  if sdd.sanitize_component(s) != fsm_component(s)]
    assert mismatches == [], f"Bridge 鏡像與 SDD 的 sanitize_component 不一致：{mismatches[:3]}"
    assert MAX_COMPONENT_LEN == sdd._MAX_COMPONENT_LEN


def test_every_sanitizer_output_is_accepted_by_the_read_domain() -> None:
    """F-8 的屬性：sanitize 的任何輸出，Bridge 都列得出、讀得到。"""
    sdd = _load_sanitizer()
    for sample in [*S10_NAMES, *EDGE_NAMES, *_fuzz_corpus(1200)]:
        produced = sdd.sanitize_component(sample)
        assert is_fsm_project_name(produced), (sample, produced)


# ── 淨化本身 ──────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("name", S10_NAMES)
def test_the_five_s10_names_survive_sanitizing_and_are_readable(name: str) -> None:
    """體檢 S-10 的五個例：淨化後仍是可讀的專案鍵（CJK、空白、括號、+、@ 都不再被拒）。"""
    assert fsm_component(name) == name, "這五個名稱不含禁用字元，淨化是恆等"
    assert is_fsm_project_name(fsm_component(name))


def test_sanitizing_is_idempotent_so_a_name_and_its_key_are_equivalent() -> None:
    """傳原名與傳已淨化的鍵等價（ADR §7.4）。唯一例外是下面那個上游邊界案例，這裡明確排除、另案釘
    住。"""
    for sample in [*S10_NAMES, *EDGE_NAMES, *_fuzz_corpus()]:
        once = fsm_component(sample)
        assert is_fsm_project_name(once), (sample, once)
        if once[-1].isspace():
            continue                     # 截斷邊界遇 Unicode 空白：見 test_known_upstream_corner…
        assert fsm_component(once) == once, (sample, once)


def test_known_upstream_corner_truncation_before_unicode_whitespace_is_not_idempotent() -> None:
    """已知上游邊界（回報主控；不在本包持有面）：`sanitize_component` 先 strip 全串、截到 80 字後只
    `rstrip(" .")`——輸入「x＋大量 NBSP＋y」截斷後以 NBSP 結尾，再淨化一次會被開頭那個 `strip()` 吃
    掉，鍵就變了（`x`）。ADR §7.4 的「淨化是冪等的」只在它的 21 個乾跑樣本上成立。
    Bridge 鏡像必須與 SDD 逐字相同（對拍測試），所以這裡只把現況釘住：SDD 日後修掉它，
    對拍測試會先紅（鏡像要跟著改），再來改這支。實務影響：這種名稱（≥80 字、第 80 字落在 Unicode
    空白之前）寫回 `sdd_project` 後再傳進來會對不到檔，其餘名稱不受影響。"""
    first = fsm_component("x" + "\N{NO-BREAK SPACE}" * 100 + "y")
    assert first == "x" + "\N{NO-BREAK SPACE}" * 79 and len(first) == MAX_COMPONENT_LEN
    assert fsm_component(first) == "x"
    assert is_fsm_project_name(first)


@pytest.mark.parametrize(("raw", "key"), [
    ("a:b", "a_b"), ("x/y", "x_y"), ("a\\b", "a_b"), ("..", "untitled"), (".", "untitled"),
    ("", "untitled"), ("   ", "untitled"), ("CON", "_CON"), ("nul.txt", "_nul.txt"),
    ("  padded  ", "padded"), ("dots...", "dots"), ("tab\there", "tab_here"),
])
def test_known_inputs_map_to_known_keys(raw: str, key: str) -> None:
    assert fsm_component(raw) == key


def test_long_names_are_cut_to_the_component_limit_and_nfd_becomes_nfc() -> None:
    assert len(fsm_component("a" * 200)) == MAX_COMPONENT_LEN
    nfd = "e\N{COMBINING ACUTE ACCENT}cole"
    assert fsm_component(nfd) == unicodedata.normalize("NFC", nfd) == "école"


# ── 輸出域判準：該拒的拒、該收的收 ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("name", [
    ".", "..", "a/b", "a\\b", "a:b", 'a"b', "a|b", "a?b", "a*b", "a<b", "a>b", "", "a\x00b",
    "a\nb", "a\tb", "a\x7fb", " lead", "trail ", "trail.", "name..",
    "e\N{COMBINING ACUTE ACCENT}cole", "x" * 81,
])
def test_the_read_domain_rejects_separators_traversal_controls_and_malformed_names(
        name: str) -> None:
    assert not is_fsm_project_name(name)


@pytest.mark.parametrize("name", [
    "alpha", "A.b_c-1", "訂單系統 v2", "Order System", "proj(v2)", "a+b", "名稱含@符號",
    "a..b", "x" * 80, "_CON", "untitled", "a\N{IDEOGRAPHIC SPACE}" * 3, "名稱\N{IDEOGRAPHIC SPACE}",
])
def test_the_read_domain_accepts_what_the_sanitizer_can_produce(name: str) -> None:
    assert is_fsm_project_name(name)


def test_non_strings_are_never_a_project_name() -> None:
    for value in (None, 0, b"abc", ["a"], {"a": 1}):
        assert not is_fsm_project_name(value)


def test_a_sanitizer_output_that_ends_in_unicode_whitespace_is_still_accepted() -> None:
    """與 ADR 字面（「無前後空白」）的差異：截斷後的輸出可能以全形空白結尾（sanitizer 只 rstrip
    ASCII）。照字面判準會拒掉 sanitizer 自己的輸出，F-8 就破功；這裡把那個案例釘住。"""
    produced = fsm_component("a" + "\N{IDEOGRAPHIC SPACE}" * 100 + "b")
    assert produced.endswith("\N{IDEOGRAPHIC SPACE}") and len(produced) == MAX_COMPONENT_LEN
    assert is_fsm_project_name(produced)
