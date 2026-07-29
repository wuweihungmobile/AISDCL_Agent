"""tests/tools/test_local_ci_gate_shell_arg_parity.py — 兩支薄殼「送進核心的 pytest
參數集合必須相同」跨檔鎖（R60 F-refuter-1）。

WHY 需要這一道、而既有的鎖為何攔不住：
  * tools/check_wrapper_thinness.py 對 local_ci_gate.{sh,ps1} 做正規化內容 sha256
    釘選。它守的是「這支殼有沒有被改過」，**不是**「這支殼內嵌的常數與核心的常數
    是否還同義」。R59 在核心 local_ci_gate.py 的 DEFAULT_PYTEST_ARGS 加了 `-rs`，
    .ps1 那份寫死的 `'tests/ -q --tb=short'` 完全沒被碰到 → hash 一直綠，而
    Windows 側（含 nightly Stage L）從此靜默少一個 `-rs`：208 支 skip 的理由全部
    被吞回一個數字，兩支被宣告等價的薄殼實際給出不同的 pytest 報告面。
    hash 釘選對這個形狀天生盲目，這正是它的盲區。
  * tests/tools/test_local_ci_gate.py 只釘核心的 DEFAULT_PYTEST_ARGS，從不讀薄殼。
    R60 掃描前 `grep -rn PytestArgs` 全 repo 沒有任何測試碰過那個預設值。

本檔鎖的不變量（不是 hash、是語意）：
  1. 兩支薄殼在「使用者未給 pytest 參數」時，轉呼叫核心後得到的 pytest 參數清單
     必須逐字相同，且必須等於核心的 DEFAULT_PYTEST_ARGS（＝單一真相源生效）。
  2. 薄殼不得成為第二個 pytest 參數真相源：.ps1 的 $PytestArgs 預設必須是空的、
     $CliArgs 只准附加 gate 旗標與 $PytestArgs 的切割結果；.sh 只准 `"$@"` 透傳。

  3. （R60 round 2 SD-R60-06 補）`$PytestArgs` 的切割轉送必須被真值守門包住 ——
     見 `_assert_ps1_guards_empty_pytestargs()`。原本本檔只是 .ps1 的**靜態模型**，
     對唯一承載語意的 `if ($PytestArgs)` 守門零感知（實測移除守門後 5 支鎖全綠）。
     🔴 **R60 round 3（SD-R60-R2-09）收緊**：不變量 3 的第一版判準是
     `if\\s*\\(\\s*[^)]*\\$PytestArgs`，`[^)]*` 容許任意前置，於是**寬化守門**
     `if ($Act -or $PytestArgs) { … }` 假綠（實測 total=7 red=0）——而它的實跑後果與
     原缺陷相同（`-Act` 為真但沒給 pytest 參數時 `['']` 照樣進核心）。判準已收緊為
     「條件必須**恰好**是 `$PytestArgs`」（`_PS1_PYTESTARGS_GUARD_RE`）。
     代價與邊界（誠實劃界）：本鎖自此是「符合單一寫法」型守門——寬化／窄化守門會
     **正確**轉紅；而行為上可接受的等價寫法（`IsNullOrWhiteSpace` 等，見
     `_GUARD_KNOWN_FALSE_RED_SAMPLES`）會**誤紅**，須實測新形態行為後同步本鎖。
     未採「用 `_ps_engine.production_engine()` 真跑 .ps1 取回真實 argv」的形態無關路徑
     （tools/tests/test_windowsapps_guard_cross_consistency.py 那種），理由是成本；
     若未來誤紅頻繁，那是正確的升級方向。

鑑別力（R60 實測）：把 .ps1 第一項改回 `'tests/ -q --tb=short'`，本檔
test_both_shells_forward_identical_pytest_args 等 4 支立刻 FAIL 並印出差異
（`-rs` 缺失）；改回空字串即全綠。移除 `if ($PytestArgs)` 守門則凡呼叫
`_ps1_default_forwarded()` 者 FAIL —— 補上不變量 3 之前是 0 支。

R60 round 3 實測（把 `.ps1` 副本放進沙箱、以 pytest 外掛把本檔的 `_PS1` 指過去，
**不觸碰 tracked 生產檔**；三種形態各跑一次，total 皆 17 項）：
  * `clean`（現行寫法）      → 17 passed / rc=0    ← 收緊未造成誤紅
  * `widened_or`（`if ($Act -or $PytestArgs)`）→ **5 failed** / rc=1（收緊前 red=0＝假綠）
  * `no_guard`（守門整段移除）→ **5 failed** / rc=1（不變量 3 的原始鑑別力未被破壞）
  5 項＝3 支函式，其中 `test_gate_flags_do_not_change_pytest_arg_parity` parametrize ×3
  （本段舊版寫「3 支」是以函式計、與 pytest 報的項數不同口徑，round 3 改以實測項數為準）。
判準自身的紅綠邊界另由 `test_guard_criterion_*` 三組對抗式樣本鎖住，複審員可直接複跑。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_AC_ROOT = Path(__file__).resolve().parent.parent.parent
_TOOLS_DIR = _AC_ROOT / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import local_ci_gate as m  # noqa: E402

_PS1 = _TOOLS_DIR / "local_ci_gate.ps1"
_SH = _TOOLS_DIR / "local_ci_gate.sh"

# .ps1 param 區塊的 $PytestArgs 宣告（[string] / [string[]] 皆容許；預設值可省略）
_PS1_PARAM_RE = re.compile(
    r"^\s*\[string(?:\[\])?\]\s*\$PytestArgs\s*(?:=\s*(?P<default>\S.*?))?\s*$",
    re.MULTILINE,
)
# $CliArgs 的每一次附加（用來排除「薄殼偷偷多塞一個 pytest 參數」）
_PS1_CLIARGS_APPEND_RE = re.compile(r"\$CliArgs\s*\+=\s*(?P<rhs>.+?)\s*(?:}|$)")
# 允許的 $CliArgs 附加形態：gate 旗標字面值，或 $PytestArgs 的空白切割
_PS1_ALLOWED_APPENDS = {"'--act'", "'--pg'", "($PytestArgs -split '\\s+')"}
# .sh 轉呼叫核心那一行：只准 "$@" 透傳，不得夾帶任何字面參數
_SH_CORE_CALL_RE = re.compile(
    r'^\s*python\s+"\$SCRIPT_DIR/local_ci_gate\.py"\s+"\$@"\s*$', re.MULTILINE
)
# `$PytestArgs` 轉送的守門判準：條件必須**恰好**是 `$PytestArgs` 真值判斷。
# 🔴 R60 round 3（SD-R60-R2-09）收緊：原判準 `if\s*\(\s*[^)]*\$PytestArgs` 的 `[^)]*`
# 容許任意前置，`if ($Act -or $PytestArgs) { … }` 這種**寬化守門**照樣全綠（實測
# MODE=guard_widened_or total=7 red=0＝假綠），而它的實跑後果與原缺陷相同：`-Act` 為真
# 卻沒給 pytest 參數時，`'' -split '\s+'` 的 `['']` 仍會被送進核心。
_PS1_PYTESTARGS_GUARD_RE = re.compile(r"if\s*\(\s*\$PytestArgs\s*\)")


def _line_has_exact_pytestargs_guard(line: str) -> bool:
    """該行是否被「恰好 `if ($PytestArgs)`」守門包住（判準本體，與對抗式自測共用）。"""
    return _PS1_PYTESTARGS_GUARD_RE.search(line) is not None


# 對抗式樣本（下方 test_guard_criterion_* 三支直接餵給 `_line_has_exact_pytestargs_guard`，
# 讓判準自身的紅綠邊界可被機械複跑，而不是只寫在散文裡）。
_GUARD_ACCEPT_SAMPLES = [
    # 現行 .ps1 的實際寫法（本鎖必須放行，否則是誤紅）
    "if ($PytestArgs) { $CliArgs += ($PytestArgs -split '\\s+') }",
    # 空白寬鬆形態（PowerShell 等價寫法，仍為「恰好真值判斷」）
    "  if ( $PytestArgs ) { $CliArgs += ($PytestArgs -split '\\s+') }",
    "if($PytestArgs){ $CliArgs += ($PytestArgs -split '\\s+') }",
]
_GUARD_REJECT_SAMPLES = [
    # ① 完全無守門＝SD-R60-06 的原始缺陷形狀
    "$CliArgs += ($PytestArgs -split '\\s+')",
    # ② 恆真守門（舊判準已能擋，保留為回歸樣本）
    "if ($true) { $CliArgs += ($PytestArgs -split '\\s+') }",
    # ③🔴 寬化守門＝SD-R60-R2-09 的窄縫（舊判準假綠）。`-Act` 為真而未給 pytest 參數時
    #    `['']` 進核心，後果同原缺陷 → 轉紅是**正確**的紅，不是誤紅。
    "if ($Act -or $PytestArgs) { $CliArgs += ($PytestArgs -split '\\s+') }",
    "if ($PytestArgs -or $Act) { $CliArgs += ($PytestArgs -split '\\s+') }",
    # ④ 窄化守門：$Act 為假時使用者給的 pytest 參數被靜默丟棄（反方向的真缺陷）
    "if ($PytestArgs -and $Act) { $CliArgs += ($PytestArgs -split '\\s+') }",
]
# 🔴 已知**誤紅**方向（如實劃界，不是缺陷）：下列形態行為上不劣於現行守門
# （`IsNullOrWhiteSpace` 甚至更嚴——現行 `if ($PytestArgs)` 對純空白字串會放行，
# 而 `'   ' -split '\s+'` 回傳含兩個空字串的陣列，仍會把空參數送進核心），但收緊後的
# 判準看不懂它們而會轉紅。**這是刻意的代價**：本鎖是「符合單一寫法」型的守門，
# 誰要改寫守門就必須親自實測新形態的行為、再同步本鎖（勿直接刪鎖）。
_GUARD_KNOWN_FALSE_RED_SAMPLES = [
    "if (-not [string]::IsNullOrWhiteSpace($PytestArgs))"
    " { $CliArgs += ($PytestArgs -split '\\s+') }",
    "if ($PytestArgs.Length -gt 0) { $CliArgs += ($PytestArgs -split '\\s+') }",
]


def _strip_ps1_comments(text: str) -> str:
    """剝除 <# … #> 區塊註解與整行 # 註解（判準對齊 check_wrapper_thinness._normalize）。"""
    text = re.sub(r"<#.*?#>", "", text, flags=re.DOTALL)
    kept = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    return "\n".join(kept)


def _strip_sh_comments(text: str) -> str:
    return "\n".join(
        ln for ln in text.splitlines() if not ln.lstrip().startswith("#")
    )


def _assert_ps1_guards_empty_pytestargs(body: str) -> None:
    """每個 `$CliArgs += ($PytestArgs -split …)` 都必須被 `$PytestArgs` 真值守門包住。

    🔴 R60 round 2 SD-R60-06：本檔原本是「.ps1 的**靜態模型**」——只讀 `param` 區塊
    的預設值，對真正承載語意的 `if ($PytestArgs)` 守門零感知。實測（把守門移除的
    臨時副本餵給本鎖）**5 支鎖全綠、零訊號**，而實跑會壞：PowerShell 的
    `'' -split '\\s+'` 回傳「含一個空字串的陣列」而不是空陣列（`count=1 first=[]`），
    守門一旦消失，Windows 側每一次無參數呼叫都會把 `['']` 當位置參數送進核心
    → 核心拿 `['']` 去跑 pytest（找不到該路徑而失敗），而非落回
    `DEFAULT_PYTEST_ARGS`。`check_wrapper_thinness` 的 hash 釘選攔不住這個形狀：
    更新 pin 是正常維護動作（本輪 E-A-02 的訂正理由），並聯訊號會一起失效。
    """
    split_lines = [ln for ln in body.splitlines() if "$PytestArgs -split" in ln]
    assert split_lines, (
        f"{_PS1.name}：找不到 `$PytestArgs -split` 轉送行 —— 參數映射被改寫，"
        f"本鎖需同步更新（勿直接刪鎖）"
    )
    for line in split_lines:
        assert _line_has_exact_pytestargs_guard(line), (
            f"{_PS1.name}：`$PytestArgs` 的切割轉送缺少「恰好 `if ($PytestArgs)`」真值"
            f"守門 —— 實際該行為 {line.strip()!r}。PowerShell 的 `'' -split '\\s+'` 回傳 "
            f"`['']`（一個空字串），守門缺失**或被寬化**（如 `if ($Act -or $PytestArgs)`）"
            f"時，無 pytest 參數的呼叫都會把空字串當位置參數送進核心，核心不會落回 "
            f"DEFAULT_PYTEST_ARGS。若守門被改成其他等價形態（如 IsNullOrWhiteSpace）或"
            f"跨多行，請**先實測新形態的實際轉送清單**再同步本鎖（勿直接刪鎖）"
        )
    # 守門為何是必要的（若核心哪天把空位置參數視為「沒給參數」，此斷言會轉紅，
    # 屆時該重新評估守門是否還有存在意義——兩個方向都對讀者有資訊）。
    assert m.parse_args([""])[2] != list(m.DEFAULT_PYTEST_ARGS), (
        "核心已能把單一空字串位置參數視同「未給參數」—— 上面的 .ps1 守門鎖失去"
        "理由，請重新評估本斷言與該守門"
    )


def _ps1_default_forwarded() -> list[str]:
    """回傳 .ps1 在「呼叫端未給 -PytestArgs」時，實際附加給核心的位置參數清單。"""
    body = _strip_ps1_comments(_PS1.read_text(encoding="utf-8-sig"))
    _assert_ps1_guards_empty_pytestargs(body)
    match = _PS1_PARAM_RE.search(body)
    assert match is not None, (
        f"{_PS1.name}：找不到 [string]$PytestArgs 參數宣告 —— 薄殼介面被改動，"
        f"本鎖需同步更新（勿直接刪鎖）"
    )
    raw = (match.group("default") or "").strip().rstrip(",")
    if raw in ("", "''", '""', "@()", "$null"):
        return []
    literal = re.fullmatch(r"'(?P<v>.*)'|\"(?P<w>.*)\"", raw)
    assert literal is not None, (
        f"{_PS1.name}：$PytestArgs 預設值 {raw!r} 不是可靜態判讀的字串字面值 —— "
        f"薄殼不得用運算式決定 pytest 參數（單一真相源在 local_ci_gate.py 的 "
        f"DEFAULT_PYTEST_ARGS）"
    )
    value = literal.group("v") if literal.group("v") is not None else literal.group("w")
    return value.split()


def _sh_default_forwarded() -> list[str]:
    """回傳 .sh 在「呼叫端未給參數」時，實際附加給核心的位置參數清單（應為空）。"""
    body = _strip_sh_comments(_SH.read_text(encoding="utf-8"))
    assert _SH_CORE_CALL_RE.search(body) is not None, (
        f'{_SH.name}：找不到 `python "$SCRIPT_DIR/local_ci_gate.py" "$@"` 透傳行 —— '
        f"薄殼若改為夾帶字面 pytest 參數，即成為第二個真相源"
    )
    return []


# --- 不變量 1：兩支殼的有效 pytest 參數逐字相同、且等於核心單一真相源 ---

def test_both_shells_forward_identical_pytest_args() -> None:
    ps1_args = m.parse_args(_ps1_default_forwarded())[2]
    sh_args = m.parse_args(_sh_default_forwarded())[2]
    assert ps1_args == sh_args, (
        "兩支薄殼給出不同的 pytest 參數面（被 check_wrapper_thinness hash 釘選"
        f"宣告為等價）：.ps1={ps1_args} / .sh={sh_args}"
    )


def test_both_shells_resolve_to_core_default_pytest_args() -> None:
    expected = list(m.DEFAULT_PYTEST_ARGS)
    assert m.parse_args(_ps1_default_forwarded())[2] == expected, (
        f"{_PS1.name} 未落回核心 DEFAULT_PYTEST_ARGS —— 薄殼寫死了自己的一份"
        f"（R60 F-refuter-1 的原始缺陷形狀：核心加 -rs、薄殼沒跟上）"
    )
    assert m.parse_args(_sh_default_forwarded())[2] == expected


@pytest.mark.parametrize("flag_argv", [["--act"], ["--pg"], ["--act", "--pg"]])
def test_gate_flags_do_not_change_pytest_arg_parity(flag_argv: list[str]) -> None:
    """-Act/-Pg（→ --act/--pg）只影響 gate 清單，不得動到 pytest 參數面。"""
    ps1 = m.parse_args(flag_argv + _ps1_default_forwarded())[2]
    sh = m.parse_args(flag_argv + _sh_default_forwarded())[2]
    assert ps1 == sh == list(m.DEFAULT_PYTEST_ARGS)


# --- 不變量 2：薄殼不得成為第二個 pytest 參數真相源 ---

def test_ps1_cliargs_appends_are_flags_or_pytestargs_only() -> None:
    body = _strip_ps1_comments(_PS1.read_text(encoding="utf-8-sig"))
    appends = [mt.group("rhs").strip() for mt in _PS1_CLIARGS_APPEND_RE.finditer(body)]
    assert appends, f"{_PS1.name}：找不到任何 $CliArgs += —— 參數映射被改寫，本鎖需同步更新"
    unexpected = [a for a in appends if a not in _PS1_ALLOWED_APPENDS]
    assert not unexpected, (
        f"{_PS1.name}：$CliArgs 出現未預期的附加 {unexpected} —— 薄殼只准附加 gate "
        f"旗標與 $PytestArgs 的切割結果，pytest 參數的真相源是 local_ci_gate.py"
    )


# --- 判準自證（紀律 #4：驗證鏡子自身要被驗證）---
# WHY：不變量 3 的守門判準本身就出過一次假綠（SD-R60-R2-09 的 `-or` 寬化窄縫），
# 而那次是靠人手注入副本才發現的。下列三支把判準的紅綠邊界機械化，讓下一輪複審員
# 不必再自己造副本注入。

@pytest.mark.parametrize("line", _GUARD_ACCEPT_SAMPLES)
def test_guard_criterion_accepts_correct_forms(line: str) -> None:
    assert _line_has_exact_pytestargs_guard(line), (
        f"判準誤紅：{line!r} 是「恰好 $PytestArgs 真值判斷」的合法形態，不該被擋"
    )


@pytest.mark.parametrize("line", _GUARD_REJECT_SAMPLES)
def test_guard_criterion_rejects_missing_widened_and_narrowed_guards(line: str) -> None:
    """缺守門／恆真守門／寬化守門／窄化守門四類都必須被擋（皆為真缺陷形狀）。"""
    assert not _line_has_exact_pytestargs_guard(line), (
        f"判準漏抓（假綠風險，SD-R60-R2-09 同族）：{line!r}"
    )


@pytest.mark.parametrize("line", _GUARD_KNOWN_FALSE_RED_SAMPLES)
def test_guard_criterion_known_false_red_boundary_is_documented(line: str) -> None:
    """已知誤紅邊界的機械化記載：這些形態行為上可接受，但收緊後的判準會擋。

    刻意寫成測試而非只寫在檔頭散文：若哪天有人放寬判準去接納這些形態，本支會轉紅並
    強迫他回頭讀 `_GUARD_KNOWN_FALSE_RED_SAMPLES` 上方那段（放寬會同時把 `-or` 窄縫
    放回來）。這不是「宣稱誤紅是對的」，而是「誤紅的範圍必須是已知且不會靜默漂移的」。
    """
    assert not _line_has_exact_pytestargs_guard(line), (
        f"判準已能接納 {line!r} —— 若這是刻意放寬，請同時證明 `-or` 寬化形態仍被擋"
        f"（否則 SD-R60-R2-09 的假綠窄縫會一起回來），並更新本清單"
    )


def test_ps1_does_not_embed_core_pytest_arg_literals() -> None:
    """.ps1 本體不得出現核心預設 pytest 參數的字面值（原始缺陷正是這種過期複本）。"""
    body = _strip_ps1_comments(_PS1.read_text(encoding="utf-8-sig"))
    leaked = [tok for tok in m.DEFAULT_PYTEST_ARGS if tok in body]
    assert not leaked, (
        f"{_PS1.name}：內嵌了核心 pytest 參數字面值 {leaked} —— 這正是 R60 "
        f"F-refuter-1 的缺陷形狀（核心改了、薄殼的複本沒跟上，hash 釘選全綠）"
    )
