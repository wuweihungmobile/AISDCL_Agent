"""conftest.py 的 `[WINDOWS-NATIVE-ONLY]` skip 可見度機制回歸鎖
（R44，DEF-101-348 方向①補完：tools/tests/ 的 unittest 執行路徑 R43 已鎖住
`tools/run_root_unittests.py::report_windows_native_skips()`，但 AutoClaude/tests/
的 pytest 執行路徑此前完全沒有對等回歸鎖）。

WHY（Rule 9，測意圖非僅行為）：純函式 `windows_native_skips()` 好測，但真正容易
被改壞而不被發現的是 `pytest_terminal_summary()` 這個「印出副作用」本身——例如
標籤比對邏輯被改壞、或印出時機被誤搬到不會在 `-q` 下觸發的 hook。只驗證純函式
回傳值鎖不住「真的有印到終端輸出上」這件事。本檔用 pytest 內建 `pytester`
fixture 以子行程方式真跑一個模擬迷你套件（沙盒 conftest.py 直接複製本套件真實
`tests/conftest.py` 原始碼，而非重新實作一份等價邏輯——確保鎖住的是生產程式碼
本身，不是測試自己編造的替身），斷言真實終端輸出裡「該出現的醒目清單有出現、
不該出現時完全沉默」。三個案例對稱比照
`tools/tests/test_run_root_unittests.py::ReportWindowsNativeSkipsTest` 的既有
三案例設計（tagged-only / plain-only / 全部不 skip）。
"""
from __future__ import annotations

import ast
import os
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

pytest_plugins = ["pytester"]

_CONFTEST_SOURCE = (Path(__file__).resolve().parent / "conftest.py").read_text(encoding="utf-8")


def _make_sandbox(pytester, *, tagged_skip: bool, plain_skip: bool) -> None:
    """在 pytester 沙盒內佈署「真實 conftest.py 原始碼」+ 一支迷你測試套件。

    `tagged_skip`/`plain_skip` 控制對應測試是否真的觸發 skip（True＝skip）。
    """
    pytester.makeconftest(_CONFTEST_SOURCE)
    pytester.makepyfile(
        test_fixture_suite=f'''
import pytest

@pytest.mark.skipif({tagged_skip!r}, reason="[WINDOWS-NATIVE-ONLY] 僅原生 Windows 才具驗證價值")
def test_tagged():
    pass

@pytest.mark.skipif({plain_skip!r}, reason="本機缺某工具，一般性 skip")
def test_plain():
    pass

def test_always_runs():
    assert True
'''
    )


def test_tagged_skip_prints_highlighted_section(pytester):
    """帶標籤的 skip 必須被獨立點名，且清單裡要看得到該測試的 nodeid。"""
    _make_sandbox(pytester, tagged_skip=True, plain_skip=False)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=2, skipped=1)
    result.stdout.fnmatch_lines(
        [
            "*WINDOWS-NATIVE-ONLY SKIPS*",
            "*1 * Windows *",
            "*test_tagged*",
        ]
    )


def test_plain_skip_alone_is_not_flagged(pytester):
    """無標籤的一般 skip 不應觸發醒目清單（不能把所有 skip 都誤標成 Windows 專屬）。"""
    _make_sandbox(pytester, tagged_skip=False, plain_skip=True)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=2, skipped=1)
    assert "WINDOWS-NATIVE-ONLY" not in result.stdout.str()


def test_no_skips_prints_nothing(pytester):
    """沒有任何 skip 時，不應印出空的醒目清單區塊（零 skip＝零雜訊）。"""
    _make_sandbox(pytester, tagged_skip=False, plain_skip=False)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=3)
    assert "WINDOWS-NATIVE-ONLY" not in result.stdout.str()


# ══════════════════════════════════════════════════════════════════════════════
# R76（R76-15 ③）：**反方向**區塊的回歸鎖——此前一個都沒有
# ══════════════════════════════════════════════════════════════════════════════
# WHY 這兩支非補不可（Rule 9）：R74 為「因為跑在 Windows 上而失去的覆蓋」新增了
# `non_windows_native_skips()` ＋ `POSIX/MAC-NATIVE-ONLY SKIPS` 區塊，但本檔三支既有
# 案例只覆蓋 Windows 那一向 ⇒ 反方向的純函式與印出副作用**零回歸鎖，整段刪掉仍全綠**。
# 更糟的是它在真實環境裡也沉默：R76 實測 `AutoClaude/tests` 的 6 個 posix-only 站點
# 0/6 帶標籤，於是這個為了「讓 Windows 側看見覆蓋損失」而建的區塊，在每天真的跑
# Windows 的那一側連續兩輪一行都沒印過——**機制在、鎖不在、輸出恆空**三者同時成立時，
# 沒有任何訊號會出現。R76 補標後同一批測試實測印出 17 行（見
# docs/06_quality/Skipped_Test_Inventory_R76.md §4.4）。


# ══════════════════════════════════════════════════════════════════════════════
# R82 包 A2（DEBT-01）：`[DEBT]` 的承接輪次不得停在**已經到了**的那一輪
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 缺陷本體（R82 掃描實測）：`AutoClaude/tests` 裡 7 支 `[DEBT]` skip 的承接輪次逐字
# 寫著 **R82**——而 R82 就是讀到這句話的那一輪。既有的格式判準
# （`tools/lib/skip_tag_policy._EXEMPT_HANDOVER_RE` ＝ `R\d{2,}`）只問「有沒有寫輪號」，
# 對「這個輪號已經過期」結構上失明 ⇒ 同一個數字可以永遠掛著，而每一輪讀到它的人都會
# 以為下一輪有人負責。這與本檔上半段治的病同型：**機制在、鎖不在，於是沉默的方向是
# 「看起來有人在管」**。
#
# 判準：全樹每一個字面 `承接輪次 R<n>` 的 n 必須 **>** 帳本推得的當前輪次
# （`tools/check_defect_log_crossref.current_round()`——本 repo 對「現在第幾輪」的既有
# 唯一真相源，刻意不寫死第二個常數）。追平的那一輪本支轉紅，逼出一個顯式決定。
#
# 🔴 判準面刻意是「**真的會被印給讀者看的那句 reason**」，不是整個檔案的文字：
# 第一版寫成全檔 regex，當場抓到 4 筆——全部是**訂正註記自己引述舊值**
# （「承接輪次由本輪推到下一輪」那類句子）與歷史敘述。那是 R73 已經判過的形態：訂正註記逐字
# 引述假話會被守著那句假話的鎖抓住，而正確的處置是把判準對準它真正該管的東西，
# 不是把註記寫得閃閃躲躲（那會讓下一個人讀不到「原本錯在哪」）。
# ⇒ 只判 `pytest.skip(...)` 與 `reason=` 這兩種位置裡的字串常數。
#
# 誠實劃界（本鎖抓不到什麼）：
#   · 以**常數／變數**組出輪號的站點（例：`test_ac_matrix_scaffolding.py` 的
#     `R{_AC_DEBT_HANDOVER_ROUND}`）不在本靜態掃描的射程內——那一支由它自己檔內的
#     `test_the_debt_handover_round_is_still_in_the_future` 在 runtime 比對。兩者刻意
#     不互相涵蓋，也刻意不互相取代。
#   · 本鎖只讀原始碼字面，不管那支測試這次有沒有真的 skip。
#   · 註解與 docstring 一律不判（見上段）。

_AUTOCLAUDE_TESTS = Path(__file__).resolve().parent
_HANDOVER_LITERAL_RE = re.compile(r"承接輪次\s*R(\d{2,})")


def _current_round() -> int | None:
    tools_dir = _AUTOCLAUDE_TESTS.parent.parent / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    import check_defect_log_crossref as crossref  # noqa: PLC0415

    ledger = (
        _AUTOCLAUDE_TESTS.parent.parent / "docs" / "06_quality" / "AutoSDD_Defect_Log.md"
    )
    if not ledger.is_file():
        return None
    return crossref.current_round(ledger.read_text(encoding="utf-8"))


def _is_skip_reason_site(node: ast.Call) -> bool:
    """這個 Call 是不是「在產生一句 skip reason」？（`pytest.skip(...)`／帶 `reason=`）"""
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in {"skip", "skipif"}:
        return True
    return any(kw.arg == "reason" for kw in node.keywords)


def _handover_literals() -> list[tuple[str, int, int]]:
    """全樹掃描 skip reason 內的字面承接輪號：`(檔案相對路徑, 行號, 輪號)`。"""
    found: list[tuple[str, int, int]] = []
    for path in sorted(_AUTOCLAUDE_TESTS.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(_AUTOCLAUDE_TESTS).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _is_skip_reason_site(node)):
                continue
            for inner in ast.walk(node):
                if not (isinstance(inner, ast.Constant) and isinstance(inner.value, str)):
                    continue
                for hit in _HANDOVER_LITERAL_RE.finditer(inner.value):
                    found.append((rel, inner.lineno, int(hit.group(1))))
    return found


def test_the_handover_scan_surface_is_not_silently_empty():
    """下限釘選：掃描面塌成 0 命中時，下一支會假綠（本 repo 對每道存量掃描的既有慣例）。

    這一支同時是「這個 repo 現在真的還有 `[DEBT]` 欠債」的憑證——欠債全部還清那天
    它會紅，那正確：屆時該把本組整組拿掉，而不是讓一個沒有分母的鎖繼續掛著。

    🔴 R90 包 E 訂正分母（**擴大**而非放寬）：本支原本只認「輪次形態」那一種承接聲明，
    於是把三筆欠債改記成**平台條件**形態（見下一節）之後，它會以「掃不到輪號」轉紅——
    而那個紅講的是假話（欠債一筆都沒少）。分母改成「所有 `[DEBT]` 的承接聲明」＝
    輪次形態 ∪ 平台條件形態：兩種形態同時歸零才算欠債清光，那時本組才該整組拿掉。
    """
    declarations = _handover_literals() + [
        (rel, ln, key) for key, hits in _platform_bound_sites().items() for rel, ln in hits
    ]
    assert declarations, (
        "全樹掃不到任何 `[DEBT]` 承接聲明（`承接輪次 R<n>` 與 `承接平台條件：<KEY>` 皆零）"
        "——若欠債真的清光了，請連同本組鎖一起移除；若只是寫法又變了，請把本鎖的兩個 regex "
        "一併更新，否則它會在零分母上恆綠"
    )


def test_every_debt_handover_round_is_still_in_the_future():
    """每一筆字面承接輪次都必須指向**還沒到**的輪次。

    合法出口只有兩條，兩條都是決定：①把該欠債做掉；②在同一個 commit 顯式把輪號往後
    推並說明為什麼又推遲一輪。不接受的第三條是把本支刪掉——那會讓輪號退回裝飾字串。
    """
    now = _current_round()
    if now is None:
        import pytest  # noqa: PLC0415

        pytest.skip(
            "[TOOL-ABSENCE] 從缺陷帳本推不出當前輪次——量不到 ≠ 量到合格，本支不放行"
        )
    stale = [(rel, ln, r) for rel, ln, r in _handover_literals() if r <= now]
    assert stale == [], (
        f"以下 `[DEBT]` 的承接輪次已經追平／落後於當前輪 R{now}：{stale}"
        "——輪號到了卻什麼都沒發生，就是「有人負責」的假象（R82 實測 7 筆同時寫著 R82，"
        "而 R82 正是讀到它們的那一輪）。合法出口：做掉它，或顯式把輪號往後推並說明理由"
    )


# ══════════════════════════════════════════════════════════════════════════════
# R90 包 E：**平台綁定**的欠債改用平台條件記，並在「債真的還得了」的那一刻才開火
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 先講清楚這**不是**「改判準讓自己過關」（那是本 repo 反覆判紅的形態，若本節其實
# 就是那個，請整節撤回）。判準的**門檻一格都沒有放寬**，改掉的是**記帳的模型**：
#
# 缺陷本體（R90 當回合實測，`_current_round()` ＝ 90）：上面那道輪次鎖對三筆逐字轉紅
#   integration/test_pgvector_hnsw_recall.py:221,263 ／ integration/test_pgvector_real_recall.py:271
#   （**改動前**的行號，本節落地後那三則 reason 已位移——引的是當時的實測輸出，不是現值）
# 而這三筆的阻塞是**平台綁定**的：解除條件是「一台備妥 PG17+pgvector staging、內含
# ≥1k 列真實 BGE-M3（1024 維）向量的機器」，掌舵者 2026-08-14 告知只有 Windows 11
# 那台有。把平台條件記成時間條件的後果是量得到的：同一個檢查點被推了四次
# （R84／R85／R88／R89，逐次理由都寫在那三則 reason 裡），四次的阻塞條件都是同一個，
# 而每一次在沒有 staging 的機器上都要為它付一次全域紅。在那種輪次上，
# 輪號不是承諾，是裝飾字串——正是這道鎖當初立案要消滅的東西，只是換了個殼復發。
#
# ⇒ 修法：承接條件寫成**條件**（`承接平台條件：<KEY>`），KEY 必須登記在
#   `_PLATFORM_BOUND_DEBTS`，且每一筆都要帶一支**真的去量這台機器**的探針。
#
# 🔴 新形態必須比舊的**強**，否則本節作廢。兩者的鑑別力差別是可驗證的：
#   · 舊：輪次到了就紅 ⇒ 在 mac 上必紅，而 mac 上結構上還不了債；對「債能不能還」
#     零鑑別力（它量的是日曆，不是環境）。
#   · 新：**跑在探針判定「還得了」的機器上卻沒還，才紅**。Windows 11 那台一旦把
#     staging 接上，本鎖當場轉紅並指名兩條合法出口；mac 上綠**不是因為不檢查**，
#     是探針真的去量了並量到「這裡還不了」（R90 當回合實測：本機 knowledge_entries
#     內帶向量的 100 列全部是 `mock-1024`，真實 BGE-M3 列 **0** 筆 < 門檻 1000）。
#   · 「量不到」一律紅、不退回綠——量不到 ≠ 量到不可還（同本檔上方 TOOL-ABSENCE 紀律）。
#
# 誠實劃界（本節抓不到什麼）：
#   · 探針量的是**可觀測代理**（列數 × `embedding_model_id`），它分得出 `mock-1024`
#     與 `bge-m3`，但分不出「這些 bge-m3 向量是不是真的由 BGE-M3 權重算出來的」。
#     偽造一份 1000 列假 bge-m3 語料可以騙過它——代價是那台機器會被判「還得了」而
#     持續轉紅，也就是**騙的方向是對自己不利的**，這是刻意選的方向。
#   · 探針只覆蓋這兩個 KEY。第三種平台綁定欠債出現時要自己入表；未入表的 KEY 直接紅。
#   · `DUAL_ADAPTER_FAILOVER_RIG` 只量兩半（staging 列數 ＋ `MINIMAX_API_KEY`），**沒有**
#     去探 BGE-M3 端點是否活著（`embedder.bge_m3_url` 那一側）。方向是刻意的：少量一個
#     前提 ⇒ 條件成立時**偏向開火**，把「其實還差一件」變成一則會被讀到的紅，而不是靜默綠。

_POLICY_LIB = _AUTOCLAUDE_TESTS.parents[1] / "tools" / "lib"
if str(_POLICY_LIB) not in sys.path:
    sys.path.insert(0, str(_POLICY_LIB))
# 🔴 刻意 import 而非自寫一份：`DEBT_SKIP_TAG` 與那條「reason 必須帶 R<n>」的 regex 是
# 下游 `skip_group_policy.skip_group_census_problems()` 判準⑥ 的判斷依據（該檔本輪不在
# 本包持有面）。複寫一份就是 R73 `Find-GitBash` 同型的「同一份知識住兩個家」。
from skip_tag_policy import DEBT_SKIP_TAG, _EXEMPT_HANDOVER_RE  # noqa: E402, I001

#: 平台條件的字面形態。KEY 全大寫底線，避免與散文混淆。判準面是 `_debt_reasons()` 併接
#: 後的整則 reason（以換行併接）⇒ 標記可以跨相鄰字串常數被認出（`\s` 會吃掉那個換行），
#: 但 **KEY 這個 token 本身**被拆開就認不出來——那是刻意的：讀者在原始碼裡也讀不出來。
_PLATFORM_CONDITION_RE = re.compile(r"承接平台條件[：:]\s*([A-Z][A-Z0-9_]{3,})")

#: 第三種合法承接形態：輪號由**同檔常數**供給、並由**同檔具名 runtime 鎖**比對當前輪
#: （既有站點＝`contract/test_ac_matrix_scaffolding.py`）。本檔上方〈誠實劃界〉早就寫著
#: 這一族「不在靜態掃描射程內」，但那時它是一個**沒有人查**的例外；本輪把它升級成
#: 「可以，但兩個指涉都必須解析得到」：常數要真的在那支檔裡、具名鎖也要真的在那支檔裡。
#: ⇒ 這一面比原本的「略過」嚴格（原本連幽靈符號都放行，而 repo 對幽靈機械物已有判例：
#: `test_pgvector_hnsw_recall.py` 檔頭記載的 `SkipReasonChannelClaimTest` 全庫不存在）。
_CONSTANT_HANDOVER_RE = re.compile(r"輪號由本檔常數\s*`?([A-Za-z_][A-Za-z0-9_]*)`?\s*統一供給")
_NAMED_GUARD_RE = re.compile(r"\b(test_[a-z0-9_]{8,})\b")

PAYABLE = "payable"
BLOCKED = "blocked"
UNMEASURABLE = "unmeasurable"

#: 探針門檻。1000 ＝ 三筆欠債 reason 自己逐字寫的解除條件①（「≥1k 列真實 BGE-M3」），
#: 不是本輪發明的數字。`mock-1024` 是 `AutoClaude/tools/seed_kb.py --mock-pg-seed` 寫進
#: `embedding_model_id` 的值 ⇒ 用 model_id 過濾即可把「CI 對等空庫＋mock 語料」與
#: 「真 staging」分開，這就是本探針的鑑別力來源。
_STAGING_MIN_BGE_M3_ROWS = 1000
_BGE_M3_MODEL_LIKE = "%bge-m3%"
_PROBE_CONNECT_TIMEOUT_S = 5
_STAGING_COUNT_SQL = (
    "SELECT count(*) FROM knowledge_entries "
    "WHERE embedding_v IS NOT NULL AND embedding_model_id ILIKE %s"
)


class _Payability(NamedTuple):
    """探針判讀：三態。`detail` 一律寫實測值，讓紅／綠都能被複驗。"""

    state: str
    detail: str


class _PlatformDebt(NamedTuple):
    what: str
    how_to_pay: str
    probe: Callable[[], _Payability]


def _sync_dsn() -> str | None:
    raw = os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ.get("AUTOCLAUDE_DB_DSN")
    return re.sub(r"\+asyncpg", "", raw) if raw else None


def probe_pgvector_bge_m3_staging(connect: Callable[[str], object] | None = None
                                  ) -> _Payability:
    """這台機器上有沒有那份 staging？（`connect` 只為合成注入而存在，正式路徑走 psycopg2）"""
    if os.environ.get("SD07_REAL_PG_E2E_ENABLED", "").lower() != "true":
        return _Payability(BLOCKED, "SD07_REAL_PG_E2E_ENABLED != 'true'：這台機器沒有宣告"
                                    "真實 PG e2e 已啟用 ⇒ staging 不在這裡")
    dsn = _sync_dsn()
    if not dsn:
        return _Payability(BLOCKED, "AUTOCLAUDE_TEST_PG_DSN／AUTOCLAUDE_DB_DSN 皆未設定")
    do_connect = connect
    if do_connect is None:
        try:
            import psycopg2  # noqa: PLC0415
        except ImportError as exc:                       # pragma: no cover — 依機器而定
            return _Payability(UNMEASURABLE, f"宣告了真實 PG e2e 卻載入不到 psycopg2（{exc}）")

        def do_connect(d: str):
            return psycopg2.connect(d, connect_timeout=_PROBE_CONNECT_TIMEOUT_S)

    conn = None
    try:
        conn = do_connect(dsn)
        with conn.cursor() as cur:
            cur.execute(_STAGING_COUNT_SQL, (_BGE_M3_MODEL_LIKE,))
            rows = int(cur.fetchone()[0])
    except Exception as exc:                             # pragma: no cover — 依機器而定
        return _Payability(UNMEASURABLE,
                           f"宣告了真實 PG e2e，但 staging 探針查不下去："
                           f"{type(exc).__name__}: {exc}")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:                            # pragma: no cover — 關檔失敗不改判讀
                pass
    if rows >= _STAGING_MIN_BGE_M3_ROWS:
        return _Payability(PAYABLE, f"knowledge_entries 實測 {rows} 列 model_id 命中 "
                                    f"`{_BGE_M3_MODEL_LIKE}` ≥ 門檻 {_STAGING_MIN_BGE_M3_ROWS}")
    return _Payability(BLOCKED, f"knowledge_entries 實測只有 {rows} 列真實 BGE-M3 向量 "
                                f"< 門檻 {_STAGING_MIN_BGE_M3_ROWS}（mock 語料不算）")


def probe_dual_adapter_failover_rig(connect: Callable[[str], object] | None = None
                                    ) -> _Payability:
    """雙 adapter 故障注入台：staging ＋ Minimax 憑證同時到位才還得了。"""
    staging = probe_pgvector_bge_m3_staging(connect=connect)
    if staging.state != PAYABLE:
        return _Payability(staging.state, f"前置（staging）不成立：{staging.detail}")
    if not os.environ.get("MINIMAX_API_KEY"):
        return _Payability(BLOCKED, f"staging 已到位（{staging.detail}），"
                                    "但 MINIMAX_API_KEY 未設定 ⇒ 切換側量不到")
    return _Payability(PAYABLE, f"staging 到位（{staging.detail}）＋ MINIMAX_API_KEY 已設定")


#: 平台綁定欠債的登記表。**只進不出會被抓**：登記了卻沒有任何站點在用 ⇒ 判紅（見
#: `platform_debt_problems` 的 stale 面），所以它不會退化成一張永久豁免表。
_PLATFORM_BOUND_DEBTS: dict[str, _PlatformDebt] = {
    "PGVECTOR_BGE_M3_STAGING": _PlatformDebt(
        what="PG17+pgvector staging，內含 ≥1000 列真實 BGE-M3（1024 維）向量與 HNSW index，"
             "且 SD07_REAL_PG_E2E_ENABLED=true／DSN 指向它",
        how_to_pay="①把 T1/T2 的 pytest.skip 拿掉，讓 recall@10 ≥ 0.95 與 p95 門檻真的被斷言；"
                   "②或由 PM 顯式廢止這兩支並在缺陷帳本留下廢止紀錄。"
                   "🔴 不接受的第三條：把承接條件換個寫法再掛一輪",
        probe=probe_pgvector_bge_m3_staging,
    ),
    "DUAL_ADAPTER_FAILOVER_RIG": _PlatformDebt(
        what="上面那份 staging ＋ 可對 BGE-M3 做故障注入的 Minimax 憑證（MINIMAX_API_KEY）",
        how_to_pay="①建出 tests/fixtures/dual_adapter_failover.json 並把 `assert True` 換成"
                   "<60s RTO 的真實量測；②或由 PM 顯式廢止該 case 並在帳本留紀錄",
        probe=probe_dual_adapter_failover_rig,
    ),
}


def _debt_reasons() -> list[tuple[str, int, str]]:
    """全樹掃 `[DEBT]` 的 skip reason：`(檔案相對路徑, 行號, 該 reason 的字面文字)`。

    與 `_handover_literals()` 的分工：那一支逐個字串常數看（輪號寫在哪一段都算），
    本支把**同一個 skip 呼叫**的所有字串常數併成一則 reason（承接聲明有沒有寫，是
    一則 reason 的性質，不是某一段的性質）。併接符是換行，所以標記可以跨**相鄰**字串
    常數被認出（那些 regex 的空白類會吃掉換行）——刻意如此：既有站點就是那樣斷行的。
    """
    found: list[tuple[str, int, str]] = []
    for path in sorted(_AUTOCLAUDE_TESTS.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(_AUTOCLAUDE_TESTS).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _is_skip_reason_site(node)):
                continue
            text = "\n".join(
                inner.value for inner in ast.walk(node)
                if isinstance(inner, ast.Constant) and isinstance(inner.value, str)
            )
            if DEBT_SKIP_TAG in text:
                found.append((rel, node.lineno, text))
    return found


def _platform_bound_sites() -> dict[str, list[tuple[str, int]]]:
    """平台條件 KEY → 宣告它的站點清單（磁碟實測，不是常數）。"""
    sites: dict[str, list[tuple[str, int]]] = {}
    for rel, lineno, text in _debt_reasons():
        for hit in _PLATFORM_CONDITION_RE.finditer(text):
            sites.setdefault(hit.group(1), []).append((rel, lineno))
    return sites


def _module_symbols(rel: str) -> tuple[set[str], set[str]]:
    """`(全檔賦值目標名, 全檔 def 名)`——用來解析 reason 裡的指涉是否存在。

    刻意不區分模組層／區域：本判準問的是「這個名字在這支檔裡存在嗎」，把區域名也算進
    來只會讓判準**偏寬**（放行一個其實是區域變數的指涉），不會製造假紅；反過來收緊則要
    處理 class 內常數、`if TYPE_CHECKING` 等一堆例外，代價遠大於它擋下的東西。
    """
    path = _AUTOCLAUDE_TESTS / rel
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    names: set[str] = set()
    defs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            defs.add(node.name)
    return names, defs


def _constant_handover_problems(rel: str, lineno: int, text: str, const: str) -> list[str]:
    """常數形態的兩個指涉都必須解析得到（幽靈常數／幽靈鎖一律紅）。"""
    names, defs = _module_symbols(rel)
    problems: list[str] = []
    if const not in names:
        problems.append(
            f"{rel}:{lineno} 宣稱輪號由本檔常數 `{const}` 供給，但該檔內找不到這個名字"
            "——指涉解析不到的承接聲明＝沒有承接聲明"
        )
    guards = [g for g in _NAMED_GUARD_RE.findall(text) if g in defs]
    if not guards:
        problems.append(
            f"{rel}:{lineno} 走常數形態，卻沒有指名一支**存在於同檔**的 runtime 鎖。"
            "常數形態之所以可以豁免靜態輪號掃描，唯一理由就是「另有一支鎖在 runtime 比對」"
            f"——那支鎖必須被指名且真的存在（本檔可見的 def：{len(defs)} 支）"
        )
    return problems


def debt_declaration_problems(reasons: list[tuple[str, int, str]]) -> list[str]:
    """每一則 `[DEBT]` reason 都必須**恰好**聲明一種承接形態（純函式）。

    這一支是新增的第三個方向：此前「一則 DEBT reason 什麼承接都不寫」只會在 runtime
    census（`skip_group_policy` 判準⑥）那一側被抓，而那條路要那支測試當次真的 skip 到
    才看得到。靜態面補上之後，寫出來的當回合就紅。
    """
    problems: list[str] = []
    for rel, lineno, text in reasons:
        has_round = _HANDOVER_LITERAL_RE.search(text)
        cond = _PLATFORM_CONDITION_RE.search(text)
        by_const = _CONSTANT_HANDOVER_RE.search(text)
        if by_const:
            problems += _constant_handover_problems(rel, lineno, text, by_const.group(1))
            continue
        if not has_round and not cond:
            problems.append(
                f"{rel}:{lineno} 的 `{DEBT_SKIP_TAG}` 沒有任何承接聲明——三種合法形態擇一："
                "`承接輪次 R<n>`（時間綁定）／`承接平台條件：<KEY>`（平台綁定）／"
                "「輪號由本檔常數 <NAME> 統一供給」＋同檔具名 runtime 鎖（常數形態）"
            )
            continue
        if has_round and cond:
            problems.append(
                f"{rel}:{lineno} 同時寫了輪次與平台條件兩種承接形態——必須擇一，"
                "否則「誰在負責」有兩個互相矛盾的答案（輪次到了要紅嗎？機器備妥了要紅嗎？）"
            )
        if cond and not _EXEMPT_HANDOVER_RE.search(text):
            problems.append(
                f"{rel}:{lineno} 是平台綁定欠債，但 reason 內連一個 `R<n>` 都沒有——"
                "下游 `skip_group_policy.skip_group_census_problems()` 判準⑥ 要求 "
                f"`{DEBT_SKIP_TAG}` 的 reason 帶輪號，會在 runtime census 那一側轉紅。"
                "請寫上**立案輪次**（史實，不是承諾），例如「平台綁定登記於 R90」"
            )
    return problems


def platform_debt_problems(
    sites: dict[str, list[tuple[str, int]]],
    registry: dict[str, _PlatformDebt],
) -> list[str]:
    """平台綁定欠債的判準（純函式，四向）。回空 list ＝合格。

    ①站點寫了未登記的 KEY ⇒ 紅（不接受自由文字當條件）；
    ②登記了卻沒有任何站點在用 ⇒ 紅（stale，防止退化成永久豁免表）；
    ③探針判「還得了」⇒ **紅**（本節的主判準：跑在那台機器上卻沒還）；
    ④探針判「量不到」⇒ 紅（量不到 ≠ 量到不可還）。
    """
    problems: list[str] = []
    for key in sorted(sites):
        if key not in registry:
            problems.append(
                f"平台條件 `{key}` 未登記於 `_PLATFORM_BOUND_DEBTS`（站點 {sites[key]}）"
                "——沒有探針的平台條件就是一句沒有人會去量的散文，與寫死輪號同病"
            )
    for key, debt in sorted(registry.items()):
        hits = sites.get(key, [])
        if not hits:
            problems.append(
                f"平台條件 `{key}` 已登記卻沒有任何 `{DEBT_SKIP_TAG}` 站點在用 ⇒ stale，"
                "請自 `_PLATFORM_BOUND_DEBTS` 移除（債還完了就不要留著一支不會開火的探針）"
            )
            continue
        verdict = debt.probe()
        if verdict.state == PAYABLE:
            problems.append(
                f"❌ 平台條件 `{key}` 在**這台機器上已經成立**：{verdict.detail}。"
                f"⇒ 這些欠債現在還得了，卻還掛著 skip：{hits}。"
                f"條件內容＝{debt.what}。合法出口：{debt.how_to_pay}"
            )
        elif verdict.state == UNMEASURABLE:
            problems.append(
                f"❌ 平台條件 `{key}` **量不到**：{verdict.detail}——量不到 ≠ 量到不可還，"
                "本判準不在此情形下放行。要嘛把環境修好讓探針量得到，要嘛把那個宣告"
                "（SD07_REAL_PG_E2E_ENABLED／DSN）關掉，不要留一個測不出來的中間態"
            )
    return problems


def test_every_debt_declares_exactly_one_handover_form():
    """全樹實測：每一則 `[DEBT]` 都要說清楚「誰／什麼條件」會來接。"""
    assert debt_declaration_problems(_debt_reasons()) == []


def test_platform_bound_debt_is_red_on_a_machine_that_can_pay_it():
    """全樹實測 ＋ 真探針：跑在備妥 staging 的機器上卻沒還債，本支就是那個紅。

    WHY（Rule 9）：這條規則要守的不是「有沒有寫承接條件」，而是**承接條件成立的那一刻
    有沒有人會知道**。舊的輪次形態在 mac 上必紅（那裡結構上還不了）、在 Windows 上
    只在「輪號剛好追平」時紅（與 staging 備妥與否無關）——兩邊都量錯了東西。
    """
    assert platform_debt_problems(_platform_bound_sites(), _PLATFORM_BOUND_DEBTS) == []


# ── 合成注入自證：證明上面那一支**真的會紅**，不是在零分母上恆綠 ────────────────

def _fake_debt(state: str, detail: str = "合成") -> _PlatformDebt:
    return _PlatformDebt(what="合成條件", how_to_pay="合成出口",
                         probe=lambda: _Payability(state, detail))


_ONE_SITE = {"K_FAKE": [("integration/test_fake.py", 42)]}


def test_injection_the_criterion_fires_when_the_machine_can_pay():
    """🔴 本節最重要的一支：模擬「這台機器就是有 staging 的那台」⇒ 判準必須紅。"""
    problems = platform_debt_problems(
        _ONE_SITE, {"K_FAKE": _fake_debt(PAYABLE, "合成：1200 列 bge-m3")})
    assert len(problems) == 1, problems
    assert "已經成立" in problems[0] and "test_fake.py" in problems[0]


def test_injection_green_only_because_the_probe_measured_it():
    """反向對照：探針量到「還不了」才綠——綠必須是量出來的結論，不是沒有檢查。"""
    assert platform_debt_problems(_ONE_SITE, {"K_FAKE": _fake_debt(BLOCKED)}) == []


def test_injection_unmeasurable_is_not_read_as_not_payable():
    """量不到 ≠ 量到不可還：第三態不得被折進綠的那一邊。"""
    problems = platform_debt_problems(_ONE_SITE, {"K_FAKE": _fake_debt(UNMEASURABLE)})
    assert len(problems) == 1 and "量不到" in problems[0]


def test_injection_a_stale_registry_entry_is_flagged():
    """登記表只進不出會退化成永久豁免表 ⇒ 沒有站點在用的 KEY 必須紅。"""
    problems = platform_debt_problems({}, {"K_FAKE": _fake_debt(PAYABLE)})
    assert len(problems) == 1 and "stale" in problems[0]


def test_injection_an_unregistered_condition_is_rejected():
    """自由文字不能當平台條件：沒有探針＝沒有人會去量。"""
    problems = platform_debt_problems(_ONE_SITE, {})
    assert any("未登記" in p for p in problems), problems


def test_injection_declaration_forms_are_mutually_exclusive():
    """宣告形態的三種壞法各自要紅（缺／兩種都寫／平台形態漏了立案輪號）。"""
    none_form = [("a.py", 1, f"{DEBT_SKIP_TAG} 沒有人接")]
    both_forms = [("b.py", 2, f"{DEBT_SKIP_TAG} 承接輪次 R99 承接平台條件：K_FAKE")]
    no_round = [("c.py", 3, f"{DEBT_SKIP_TAG} 承接平台條件：K_FAKE")]
    assert any("沒有任何承接聲明" in p for p in debt_declaration_problems(none_form))
    assert any("同時寫了" in p for p in debt_declaration_problems(both_forms))
    assert any("連一個" in p for p in debt_declaration_problems(no_round))
    ok = [("d.py", 4, f"{DEBT_SKIP_TAG} 承接平台條件：K_FAKE（平台綁定登記於 R90）")]
    assert debt_declaration_problems(ok) == []


def test_injection_constant_form_must_resolve_both_of_its_references():
    """常數形態的兩個指涉（常數／runtime 鎖）都要真的存在，幽靈符號一律紅。

    分母用**本檔自己**當真實檔：本檔確實有 `_PLATFORM_CONDITION_RE` 這個常數，也確實有
    `test_injection_the_criterion_fires_when_the_machine_can_pay` 這支 def ⇒ 正例可解析；
    反例換成不存在的名字。這樣不必造假檔，也證明解析走的是真 AST。
    """
    me = Path(__file__).name
    good = (f"{DEBT_SKIP_TAG} 輪號由本檔常數 _PLATFORM_CONDITION_RE 統一供給，由 "
            "test_injection_the_criterion_fires_when_the_machine_can_pay 比對")
    assert debt_declaration_problems([(me, 1, good)]) == []
    ghost_const = good.replace("_PLATFORM_CONDITION_RE", "_NO_SUCH_CONSTANT_XYZ")
    assert any("找不到這個名字" in p for p in debt_declaration_problems([(me, 2, ghost_const)]))
    ghost_guard = (f"{DEBT_SKIP_TAG} 輪號由本檔常數 _PLATFORM_CONDITION_RE 統一供給，由 "
                   "test_no_such_guard_exists_at_all 比對")
    assert any("runtime 鎖" in p for p in debt_declaration_problems([(me, 3, ghost_guard)]))


# ── 合成注入自證（第二層）：**真探針**本身在 staging 存在時回 payable ──────────────
# 上面那組注入的是 `_PlatformDebt.probe`，證的是判準的接線；這一組注入的是資料庫回答，
# 證的是 `probe_pgvector_bge_m3_staging()` 這支真程式碼——門檻比較、model_id 過濾、
# 三態分派全部走真路徑。刻意不去碰本機那顆 PG（六包並行共用同一顆，且 `[DEBT]` 站點
# 的姊妹測試會就地 seed 語料；往共用 DB 塞 1000 列合成資料是跨包污染）。

class _FakeCursor:
    def __init__(self, rows: int) -> None:
        self._rows = rows
        self.executed: list[tuple[str, tuple]] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql: str, params: tuple) -> None:
        self.executed.append((sql, params))

    def fetchone(self):
        return (self._rows,)


class _FakeConn:
    def __init__(self, rows: int) -> None:
        self.cur = _FakeCursor(rows)
        self.closed = False

    def cursor(self):
        return self.cur

    def close(self) -> None:
        self.closed = True


def _staging_env(monkeypatch) -> None:
    monkeypatch.setenv("SD07_REAL_PG_E2E_ENABLED", "true")
    monkeypatch.setenv("AUTOCLAUDE_TEST_PG_DSN", "postgresql://u:p@synthetic:5432/staging")


def test_injection_real_probe_says_payable_when_the_staging_is_really_there(monkeypatch):
    """🔴 模擬 staging 存在（DB 回 1000 列 bge-m3）⇒ 真探針必須回 payable。"""
    _staging_env(monkeypatch)
    conn = _FakeConn(_STAGING_MIN_BGE_M3_ROWS)
    verdict = probe_pgvector_bge_m3_staging(connect=lambda dsn: conn)
    assert verdict.state == PAYABLE, verdict
    assert conn.cur.executed[0][1] == (_BGE_M3_MODEL_LIKE,), conn.cur.executed
    assert conn.closed, "探針必須關掉連線"


def test_injection_real_probe_boundary_is_the_documented_thousand(monkeypatch):
    """門檻鑑別力：999 列不算 staging（否則「≥1k 真實向量」那句話沒有牙）。"""
    _staging_env(monkeypatch)
    verdict = probe_pgvector_bge_m3_staging(
        connect=lambda dsn: _FakeConn(_STAGING_MIN_BGE_M3_ROWS - 1))
    assert verdict.state == BLOCKED and "999" in verdict.detail, verdict


def test_injection_real_probe_reports_unmeasurable_when_the_query_dies(monkeypatch):
    """宣告啟用卻查不下去 ⇒ unmeasurable（不是 blocked）。"""
    _staging_env(monkeypatch)

    def boom(dsn):
        raise RuntimeError("connection refused")

    assert probe_pgvector_bge_m3_staging(connect=boom).state == UNMEASURABLE


def test_injection_real_probe_is_blocked_without_the_env_declaration(monkeypatch):
    """沒宣告真實 PG e2e 的機器一律 blocked，且**不得**去連任何資料庫。"""
    monkeypatch.delenv("SD07_REAL_PG_E2E_ENABLED", raising=False)

    def never(dsn):                                      # pragma: no cover — 被呼叫即失敗
        raise AssertionError("未宣告啟用時不應該連線")

    assert probe_pgvector_bge_m3_staging(connect=never).state == BLOCKED


def test_injection_failover_rig_needs_both_halves(monkeypatch):
    """故障注入台：staging 到位但缺 Minimax 憑證 ⇒ 仍是 blocked（不得只看一半）。"""
    _staging_env(monkeypatch)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    full = lambda dsn: _FakeConn(_STAGING_MIN_BGE_M3_ROWS)  # noqa: E731
    assert probe_dual_adapter_failover_rig(connect=full).state == BLOCKED
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-synthetic")
    assert probe_dual_adapter_failover_rig(connect=full).state == PAYABLE


def test_the_round_form_scanner_keeps_its_teeth_at_zero_denominator():
    """載具自檢：輪次形態的分母本輪已歸零（三筆全改成平台條件），regex 壞掉不會有人發現。

    🔴 為什麼非補不可：上面那道floor（`..._not_silently_empty`）本輪擴成「兩種形態的
    聯集」，於是「輪次掃描器整支壞掉、但平台站點還在」這個組合會**全綠**——那正是本檔
    上半段治的病（機制在、鎖不在）。以合成樣本自證掃描器仍活著，成本一行。
    """
    hit = _HANDOVER_LITERAL_RE.search(f"{DEBT_SKIP_TAG} 需要某某環境。承接輪次 R99")
    assert hit is not None and int(hit.group(1)) == 99
    assert _is_skip_reason_site(ast.parse("pytest.skip('x')").body[0].value)


def _make_reverse_sandbox(pytester, *, posix_tagged: bool, mac_tagged: bool,
                          untagged: bool) -> None:
    """反方向沙盒：`[POSIX-NATIVE-ONLY]`／`[MAC-NATIVE-ONLY]`／無標籤三種 skip。"""
    pytester.makeconftest(_CONFTEST_SOURCE)
    pytester.makepyfile(
        test_reverse_suite=f'''
import pytest

@pytest.mark.skipif({posix_tagged!r}, reason="[POSIX-NATIVE-ONLY] POSIX 專屬行為")
def test_posix_tagged():
    pass

@pytest.mark.skipif({mac_tagged!r}, reason="[MAC-NATIVE-ONLY] macOS 真機專屬")
def test_mac_tagged():
    pass

@pytest.mark.skipif({untagged!r}, reason="POSIX 專屬行為（作者忘了標）")
def test_untagged():
    pass
'''
    )


def test_reverse_direction_tagged_skips_print_their_own_section(pytester):
    """兩種反方向標籤都必須讓區塊印出，且逐支 nodeid 看得到。

    意圖：這一段的價值不在「有沒有 skip」——`skipped=N` 早就印了——而在「哪幾支是
    **因為跑在這個平台上**而失去的覆蓋」。少了本支，把 `NON_WINDOWS_SKIP_TAGS` 改成
    只認一種標籤、或把整個 `posix_ids` 分支刪掉，都不會有任何東西轉紅。
    """
    _make_reverse_sandbox(pytester, posix_tagged=True, mac_tagged=True, untagged=False)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=1, skipped=2)
    result.stdout.fnmatch_lines(
        [
            "*POSIX/MAC-NATIVE-ONLY SKIPS*",
            # 🔴 R82（DOC-01）：錨點由 `*2 * Windows *` 改成 `*2 *{sys.platform}*`。
            # 舊錨點是把「寫死 Windows」這個缺陷同時釘進了鎖裡——修好標題，鎖會紅。
            f"*2 *{sys.platform}*",
        ]
    )
    out = result.stdout.str()
    assert "test_posix_tagged" in out and "test_mac_tagged" in out, out


def test_the_reverse_section_never_hardcodes_a_platform_name(pytester):
    """🔴 R82（DOC-01）：標題與說明行的平台名必須是**這次真的跑在哪**，不得寫死。

    WHY（Rule 9）：修前逐字是「本次跑在 Windows 上失去的覆蓋」，而 2026-08-05 那次
    真的執行過的 macOS CI 輸出裡照樣印著這句話（`gh run view 31021778241 --log`
    實測命中）。這一段的存在理由是「讓這個平台的讀者看見自己這一側的覆蓋損失」，
    標題寫死等於對 macOS 讀者說「這段與你無關」——與它要治的沉默是同一族，方向相反。

    判準刻意分兩半：①實際輸出必須帶 `sys.platform`（動態組字的證據）；②不得出現
    任何其他平台的字面名（否則「f-string 裡再補一句 Windows」照樣能滿足①）。
    """
    _make_reverse_sandbox(pytester, posix_tagged=True, mac_tagged=False, untagged=False)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=2, skipped=1)
    section = [
        ln for ln in result.stdout.str().splitlines()
        if "POSIX/MAC-NATIVE-ONLY SKIPS" in ln or "失去的覆蓋" in ln or "而沒跑" in ln
    ]
    assert section, "反方向區塊一行都沒印出來"
    joined = "\n".join(section)
    assert sys.platform in joined, (
        f"區塊標題／說明行沒有帶本次的 `sys.platform`（{sys.platform}）：{joined!r}"
        "——平台名疑似又被寫死了"
    )
    others = {"Windows", "win32", "darwin", "macOS", "linux", "Linux"} - {sys.platform}
    for name in sorted(others):
        assert name not in joined, (
            f"區塊裡出現了別的平台名 `{name}`：{joined!r}——那是 DOC-01 的迴歸"
            "（在 macOS runner 上逐字印著「本次跑在 Windows 上」）"
        )


def test_reverse_section_stays_silent_without_tags(pytester):
    """未標籤的反方向 skip 不得觸發區塊（否則區塊會變成「所有 skip」的雜訊複本）。

    意圖：負向案例才是鑑別力的來源——沒有它，一支「無條件把每筆 skip 都印進反方向
    區塊」的假實作也會讓上一支通過。同時本支釘住 R76 的前提：**標籤是唯一入口**，
    所以「0/6 站點帶標籤」必然等於「區塊恆空」，那不是巧合而是結構。
    """
    _make_reverse_sandbox(pytester, posix_tagged=False, mac_tagged=False, untagged=True)
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=2, skipped=1)
    assert "POSIX/MAC-NATIVE-ONLY" not in result.stdout.str()
