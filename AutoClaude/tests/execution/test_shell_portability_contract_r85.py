"""R85 / P7：`shell=True` 跨平台可攜性契約的回歸鎖。

根 `CLAUDE.md` 鐵律三大表的「`shell=True` 的原生殼差異」那一列此前逐字寫「**無機械物**」，
並自陳「存量掃描結構上量不到真實危害面」。本檔是那一格的機械面。

🔴 本鎖存在的**結構性理由**（不是「多一道保險」）：
    真正被送進殼的字串是**執行期才出現的**——`evaluator_command` 來自 playbook YAML，
    `condition_evaluator` 來自 LLM 的 correction 提案（本輪實測：全 repo YAML 內
    `condition_evaluator` 出現 **0 次**，它唯一的產生者是 decision/prompt_builder.py
    的突變 schema）。⇒ 任何「掃 repo 內 .py 字面」的靜態判準對這一族結構上失明，
    會回 0 命中而給出**假的安心**。本檔的主判準因此是**執行期函式**，不是掃描器。

四組判準，各自守不同的失效方向：
  (a) 判準真的會判（正面＋反面）：不可攜必出聲、可攜必不出聲。兩個方向都鎖，
      因為「全部都出聲」與「全部都不出聲」在只鎖單向時各有一半是綠的。
  (b) 射程普查：兩個 `shell=True` 執行面**都**要接上診斷——關掉一扇門只會讓人走另一扇。
      新開第三個執行面即紅。
  (c) 反相關那個事實本身被釘住：`_SHELL_TRUE_COND_WHITELIST` 是**資安**過濾器不是可攜性過濾器。
      不釘住它，下一個人會把它當可攜性閘去「修」，而那會同時弄壞資安與可攜性兩軸。
  (d) `shell=False` 這個候選解的**否決理由**被釘住：殼在 CONDITIONAL 這條路上是承重的。
"""
from __future__ import annotations

import ast
import re
import shlex
import subprocess
from pathlib import Path

import pytest

from autoclaude.execution.evaluator import _SINGLE_PLATFORM_ARGV0, portability_note

_PKG = Path(__file__).resolve().parents[2] / "autoclaude"
_AUTOCLAUDE = Path(__file__).resolve().parents[2]

#: 必出聲：argv[0] 是單平台專屬外部指令。含 docstring **逐字點名**的反例
#: （`test`/`grep`），以及帶路徑前綴、Windows 專屬那幾種形態。
_MUST_WARN = [
    "test -f foo",                 # _conditional.py 註解逐字點名的 POSIX 專屬反例
    "grep -q needle file.txt",     # 同上
    "pgrep -f something",
    "pmset -g custom",
    "launchctl list",
    "sed -i s/a/b/ f",
    "awk '{print $1}' f",
    "ls /tmp",
    "chmod +x foo.sh",
    "/usr/bin/test -f x",          # 帶絕對路徑前綴，仍須認出 basename
    "sudo rm -rf build",
    "taskkill /F /PID 1",          # Windows 專屬
    "where python",
    "dir C:/Windows",
    "powershell -File x.ps1",
    "schtasks /query",
]

#: 必**不**出聲。這一組是本判準能不能活下來的關鍵——repo 已判過「擋到讓人無法工作的
#: 守衛會被整個關掉」。含三類：
#:   ① 真實 playbook 的 evaluator_command 樣貌（pytest / python -c / 專案自帶 CLI）
#:   ② cmd.exe 與 /bin/sh **都有**的 builtin（`exit`/`echo`/`cd`/`set`）＝本來就可攜，
#:      而 `exit 0`/`exit 1` 正是本 repo 自己測試裡 CONDITIONAL 的慣用寫法
#:   ③ 跨平台執行檔（git/npm/node/ruff/make）
_MUST_NOT_WARN = [
    "pytest tests/test_auth.py -v",
    "python -m pytest tests -q",
    'python -c "print(1)"',
    "autoclaude-artifact-check SPEC.md --min-bytes 200",
    "exit 0",
    "exit 1",
    "echo hi",
    "cd build",
    "set FOO=1",
    "git status --porcelain",
    "npm test",
    "node build.js",
    "ruff check .",
    "make test",
    "",
]


class TestTheJudgmentActuallyJudges:
    @pytest.mark.parametrize("cmd", _MUST_WARN)
    def test_single_platform_argv0_is_called_out(self, cmd):
        assert portability_note(cmd) is not None, f"未出聲：{cmd!r}"

    @pytest.mark.parametrize("cmd", _MUST_NOT_WARN)
    def test_portable_commands_are_left_alone(self, cmd):
        """假紅的代價不是「比較嚴格」：對 `exit 0`／`pytest` 出聲會讓每一步都噪音一行，
        而被噪音淹掉的診斷等於沒有診斷。"""
        assert portability_note(cmd) is None, f"假紅：{cmd!r}"

    def test_none_input_is_tolerated(self):
        """`condition_evaluator` 是 Optional[str]，None 必須安全通過而不是拋例外。"""
        assert portability_note(None) is None

    def test_it_says_which_token_it_objected_to(self):
        """只回「有問題」而不說是哪個 token，會讓使用者無從修正。"""
        assert portability_note("test -f foo") == "test"
        assert portability_note("/usr/bin/pgrep -f x") == "pgrep"

    def test_the_judgment_never_blocks(self):
        """🔴 本判準是**診斷**不是閘：它不得改變任何控制流。

        WHY 這一格：repo 已判過「擋到讓人無法工作的守衛會被整個關掉，而被關掉的守衛
        比沒有守衛更糟」。單平台 playbook 是合法的（只在 POSIX 部署跑的專案寫 `grep`
        沒有任何錯），且 Git for Windows 會把 `grep`/`test` 放進 PATH ⇒ 「另一平台上
        一定跑不了」這個推論本身就不可靠，只能當提示。若哪天有人把它改成會擋，
        本格會紅，逼他先回答上面兩個問題。
        """
        for cmd in _MUST_WARN:
            assert portability_note(cmd) in _SINGLE_PLATFORM_ARGV0

    def test_dual_platform_builtins_are_deliberately_excluded(self):
        """`exit`/`echo`/`cd`/`set` 在 cmd.exe 與 /bin/sh **都是** builtin ⇒ 本來就可攜。

        收進詞彙表就是對 repo 自己的慣用寫法製造假紅（`exit 0` 出現在
        tests/test_gap021_028.py 四處）。
        """
        for builtin in ("exit", "echo", "cd", "set", "python", "pytest", "git"):
            assert builtin not in _SINGLE_PLATFORM_ARGV0


class TestEveryShellSurfaceIsDiagnosed:
    #: `autoclaude/` 內以 `shell=True` 起子行程、且必須接上可攜性診斷的站點。
    #: **這是量測值不是設定值**：新開第三個執行面時本鎖轉紅，逼人回答「它接診斷了沒」。
    DIAGNOSED_SHELL_SITES = frozenset({
        "autoclaude/execution/evaluator.py",
        "autoclaude/execution/mutation_applier/_conditional.py",
    })

    def _shell_true_sites(self) -> set[str]:
        found: set[str] = set()
        for py in _PKG.rglob("*.py"):
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except SyntaxError:                                   # pragma: no cover
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and any(
                    kw.arg == "shell" and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True for kw in node.keywords
                ):
                    found.add(py.relative_to(_PKG.parent).as_posix())
        return found

    def test_shell_true_surface_matches_the_diagnosed_set(self):
        assert self._shell_true_sites() == self.DIAGNOSED_SHELL_SITES, (
            "autoclaude/ 的 shell=True 執行面與已接診斷清單不符。"
            "新增執行面 ⇒ 先呼叫 portability_note() 再把它加進 DIAGNOSED_SHELL_SITES；"
            "移除 ⇒ 同步移除。兩個方向都不准靜默。"
        )

    @pytest.mark.parametrize("rel", sorted(DIAGNOSED_SHELL_SITES))
    def test_each_shell_surface_actually_calls_the_judgment(self, rel):
        """🔴 只斷言「檔案在清單裡」會放過「加進清單但沒接線」——那與沒有鎖等價。

        故本格用 AST 確認該檔真的有 `portability_note(...)` 這個**呼叫**，
        而不是只有 import（import 了卻沒呼叫，是最像修好的失效形態）。
        """
        tree = ast.parse((_AUTOCLAUDE / rel).read_text(encoding="utf-8"))
        called = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and getattr(n.func, "id", getattr(n.func, "attr", "")) == "portability_note"
        ]
        assert called, f"{rel} 有 shell=True 卻沒有呼叫 portability_note()"

    def test_the_scanner_itself_can_see_a_new_surface(self, tmp_path):
        """證偽探針：掃描器對「新開的 shell=True 站點」必須真的看得見。

        WHY：本類唯一的失效模式是掃描器回空集合而集合比對照樣綠（分母 0＝沒有東西
        可違反）。repo 已判過這種「有鎖在守假話」比沒有鎖更難看見。
        """
        probe = tmp_path / "probe.py"
        probe.write_text("import subprocess\nsubprocess.Popen('x', shell=True)\n",
                         encoding="utf-8")
        hits = [
            n for n in ast.walk(ast.parse(probe.read_text(encoding="utf-8")))
            if isinstance(n, ast.Call) and any(
                kw.arg == "shell" and getattr(kw.value, "value", None) is True
                for kw in n.keywords
            )
        ]
        assert hits, "掃描器連合成注入的 shell=True 都看不到，本類的綠是假的"


class TestTheSecurityFilterIsNotAPortabilityFilter:
    """🔴 把「反相關」這個事實本身釘住。

    `_SHELL_TRUE_COND_WHITELIST` 是 Gap-046 的**資安字元白名單**（擋 shell metacharacter）。
    它與可攜性的關係是**反相關**——本輪逐句實測：
      · `python -c "print(1)"`（註解逐字建議的可攜正解）→ 被**擋掉**（因為括號）
      · `test -f foo`（註解逐字點名的 POSIX 專屬反例）→ 被**放行**（剛好只用白名單字元）
    不釘住這件事，下一個人會把它當可攜性閘去「修」，而那會同時弄壞兩軸：
    放寬括號＝開資安洞，收緊 `test`＝把資安過濾器變成平台過濾器。
    """

    @staticmethod
    def _pattern() -> re.Pattern:
        from autoclaude.execution.mutation_applier._conditional import _SHELL_TRUE_COND_WHITELIST
        return _SHELL_TRUE_COND_WHITELIST

    def test_it_rejects_the_portable_form_it_recommends(self):
        assert not self._pattern().match('python -c "print(1)"')

    @pytest.mark.parametrize("cmd", ["test -f foo", "grep -q x f", "pgrep -f x", "rm -rf /"])
    def test_it_admits_the_non_portable_forms_it_names(self, cmd):
        assert self._pattern().match(cmd)

    def test_the_two_axes_are_therefore_independent(self):
        """資安判準與可攜性判準對同一句話可以給出相反判決 —— 這正是要兩道的理由。"""
        cmd = "test -f foo"
        assert self._pattern().match(cmd) and portability_note(cmd) is not None


class TestWhyNotShellFalse:
    """🔴 釘住 `shell=False` ＋ argv 陣列這個候選解的**否決理由**（實測，不是意見）。

    它看起來是「治本」——不經殼就沒有 cmd.exe vs /bin/sh 的差異。但 CONDITIONAL 的
    慣用寫法是 shell **builtin**：`exit 0`／`exit 1` 出現在 tests/test_gap021_028.py
    四處，而 builtin 沒有對應的執行檔。不釘住這件事，下一輪會有人「順手治本」而讓
    CONDITIONAL 整個功能停擺——且失敗表徵是 FileNotFoundError → cond_exit=1 →
    **靜默走 false 分支**，與「條件確實不成立」完全相同。
    """

    def test_the_canonical_conditional_idiom_needs_a_shell(self):
        with pytest.raises(FileNotFoundError):
            subprocess.run(shlex.split("exit 0"), capture_output=True, timeout=10)

    def test_and_it_works_through_a_shell(self):
        assert subprocess.run("exit 0", shell=True, timeout=10).returncode == 0

    def test_the_repo_really_does_use_that_idiom(self):
        """否決理由的前提（repo 真的這樣寫）必須是現查的，不是記憶。"""
        src = (_AUTOCLAUDE / "tests" / "test_gap021_028.py").read_text(encoding="utf-8")
        assert 'condition_evaluator="exit 0"' in src


class TestTheRealCorpusIsClean:
    """🔴 假紅普查——母體是**真正會被送進殼的字串**，不是 repo 內的 .py 字面。

    為什麼這是對的母體（同 R84 對 tracked vs transcripts 下過的判決）：
      · `grep shell=True *.py` 回答的是「哪裡有執行面」（＝上面那個射程普查在做的事），
        對「送進去的內容可不可攜」零資訊；
      · **playbook YAML 的 `evaluator_command` 欄位值**才是 `Evaluator.run` 的真實輸入面。
    本輪實測母體：9 支 playbook、19 個 evaluator_command 值，命中 **0**
    ⇒ 這道判準對今天出貨的每一支 playbook 都不出聲，假紅為零。

    這一格會隨新 playbook 自動長大——有人加了一支不可攜的 evaluator_command 就會紅，
    而那正是本判準該說話的時刻。
    """

    @staticmethod
    def _real_evaluator_commands() -> list[tuple[str, str]]:
        pat = re.compile(r"^\s*evaluator_command\s*:\s*(.+?)\s*$")
        out: list[tuple[str, str]] = []
        for y in sorted(_AUTOCLAUDE.rglob("*.y*ml")):
            if any(p in y.parts for p in (".git", "node_modules", ".venv")):
                continue
            for line in y.read_text(encoding="utf-8", errors="replace").splitlines():
                m = pat.match(line)
                if not m:
                    continue
                val = m.group(1).strip().strip("\"'")
                if val and not val.startswith(("|", ">", "{", "[", "#")):
                    out.append((y.relative_to(_AUTOCLAUDE).as_posix(), val))
        return out

    def test_the_corpus_is_not_empty(self):
        """取數管道自證：母體為空時「命中 0」是假的安心，不是好消息。"""
        corpus = self._real_evaluator_commands()
        assert len(corpus) >= 15, f"母體只有 {len(corpus)} 筆，取數管道可能壞了"

    def test_no_shipped_playbook_trips_the_judgment(self):
        offenders = [(f, c, portability_note(c)) for f, c in self._real_evaluator_commands()
                     if portability_note(c) is not None]
        assert not offenders, f"出貨的 playbook 帶不可攜 evaluator_command：{offenders}"


# ─────────────────────────────────────────────────────────────────────────────
# 🔴 R85 F3（SD 複審 B-4 ＋ 判準品質裁決）：輸入面正規化的**射程普查 ＋ 逐欄位判準**。
#
# 病 ①（B-4，blocking）：P7 只把可攜性要求寫進 `condition_evaluator` 那一欄，而
# `new_step_evaluator_command`（INJECT_AFTER／INJECT_BEFORE 各一份）同樣會走到
# `shell=True`——本輪 AST 實測：它是 `PlaybookTask(evaluator_command=...)` 的**唯一**
# StepMutation 來源（3 個站點），而 `PlaybookTask.evaluator_command` 正是
# `Evaluator.run` → `subprocess.Popen(shell=True)` 的輸入（infra/adapters/
# shell_evaluator.py:38 → execution/evaluator.py）。⇒ 輸入面正規化此前只覆蓋一半。
#
# 病 ②（判準品質）：原判準是 `"可攜" in _MUTATION_SCHEMA_SECTION` ——**關鍵字當充分
# 條件**。它有兩個結構性失明方向，兩者的失敗表徵都與「通過」完全相同：
#   · 要求寫在**別的欄位**上照樣綠（section 是一整塊字串，`in` 不分欄位）；
#   · 要求寫成「必須可攜」四個字而**不告訴模型哪些指令不可攜**照樣綠——那句話對
#     生成端零資訊，而 prompt 的用途就是被生成端讀。
# ⇒ 本節的判準改為：①欄位集合由**程式碼**量出來（不是手寫清單）②要求必須落在**該欄位
#   自己的描述**裡 ③要求必須與執行期詞彙表 `_SINGLE_PLATFORM_ARGV0` 對齊，且**推薦區
#   不得出現該詞彙表的詞**（prompt 一邊要求可攜、一邊示範 `test -f` 是最難看見的假綠）。
#
# 誠實劃界：詞彙比對是 `\b<token>\b` 字面比對 ⇒ 抓得到「完全沒點名」與「推薦了不可攜
# 指令」，抓不到「點名了但語氣太弱」。它是必要條件不是充分條件，同 R75 對關鍵詞佐證
# 下過的判決。

_PROHIBITION_MARKERS = ("不得用", "不可用", "禁用", "禁止", "避免")

#: 已登記受本判準管轄的 schema 欄位。**這是量測值的鏡像不是設定值**——下方
#: `test_the_census_and_the_registry_agree` 要求它等於 AST 普查結果。
_SHELL_BOUND_SCHEMA_FIELDS = frozenset({"condition_evaluator", "new_step_evaluator_command"})


def shell_bound_mutation_fields(pkg: Path) -> set[str]:
    """AST 射程普查：哪些 `StepMutation` 欄位的值最終會被送進平台原生殼。

    兩條入口各自量測（**不是寫死清單**，新開第三條入口即改變本函式回傳值）：
      (a) 直接當作 `shell=True` 呼叫的第一個位置引數（`_conditional.py` 走這條）；
      (b) 餵進 `PlaybookTask(evaluator_command=...)`——該欄由 `Evaluator.run(shell=True)`
          消費（`_simple_mutations.py` / `_complex_mutations.py` / `_helpers.py` 三處）。
    只收 `StepMutation` 真實欄位名 ⇒ `Evaluator.run(command, shell=True)` 那個
    區域參數不會被誤收（它是 `ast.Name` 不是 `ast.Attribute`，且不在欄位表內）。
    """
    from autoclaude.models.step_mutation import StepMutation
    known = frozenset(StepMutation.model_fields)
    found: set[str] = set()

    def _attrs(node: ast.AST) -> set[str]:
        return {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)} & known

    for py in sorted(pkg.rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:                                       # pragma: no cover
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            is_shell_true = any(
                kw.arg == "shell" and isinstance(kw.value, ast.Constant)
                and kw.value.value is True for kw in node.keywords
            )
            if is_shell_true and node.args:
                found |= _attrs(node.args[0])
            for kw in node.keywords:
                if kw.arg == "evaluator_command":
                    found |= _attrs(kw.value)
    return found


def schema_field_descriptions(text: str) -> dict[str, list[str]]:
    """把 schema 文字拆成「欄位名 → 該欄位**自己的**描述（可能多份）」。

    這一步就是治病 ②-a 的本體：`in` 對整塊字串沒有欄位概念，拆完之後
    「把要求搬到別的欄位」就再也騙不過去。
    """
    out: dict[str, list[str]] = {}
    pat = re.compile(r'^\s*"(?P<name>\w+)"\s*:\s*(?P<val>.+?),?\s*$')
    for line in text.splitlines():
        m = pat.match(line)
        if m:
            out.setdefault(m.group("name"), []).append(m.group("val"))
    return out


def _names(desc: str) -> set[str]:
    return {t for t in _SINGLE_PLATFORM_ARGV0 if re.search(rf"\b{t}\b", desc)}


def portability_gaps(text: str, fields: frozenset[str] | set[str]) -> list[str]:
    """回傳「哪一個欄位的第幾份描述、缺了什麼」；空 list＝合格。純函式 ⇒ 鑑別力可合成注入證明。"""
    seen = schema_field_descriptions(text)
    gaps: list[str] = []
    for field in sorted(fields):
        descs = seen.get(field, [])
        if not descs:
            gaps.append(f"{field}: 欄位在 schema 內完全不存在")
            continue
        for i, desc in enumerate(descs):
            where = f"{field}#{i}"
            if "可攜" not in desc:
                gaps.append(f"{where}: 該欄位自己的描述未要求可攜")
                continue
            if "cmd.exe" not in desc:
                gaps.append(f"{where}: 未告知模型另一平台的殼是 cmd.exe")
                continue
            cut = min((desc.find(k) for k in _PROHIBITION_MARKERS if k in desc), default=-1)
            if cut < 0:
                gaps.append(f"{where}: 只說「要可攜」卻沒有禁止句，對生成端零資訊")
                continue
            if len(_names(desc[cut:])) < 2:
                gaps.append(f"{where}: 禁止句未點名執行期詞彙表裡的單平台指令")
            bad = _names(desc[:cut])
            if bad:
                gaps.append(f"{where}: 推薦區自己就示範了不可攜指令 {sorted(bad)}")
    return gaps


class TestTheInputSurfaceIsNormalisedAtItsOrigin:
    """🔴 `condition_evaluator`／`new_step_evaluator_command` 的真實產生者是 **LLM**。

    本輪實測：全 repo YAML 內 `condition_evaluator` 出現 **0 次**；兩者唯一的產生者
    都是 decision/prompt_builder.py 的突變 schema。⇒ 對這一族而言「輸入面正規化」的
    正確落點是**那段 prompt**，那是唯一在字串被造出來**之前**就能介入的地方。
    執行期診斷是第二層（模型不一定照做），兩層都要。
    """

    @staticmethod
    def _schema() -> str:
        # 刻意在**呼叫時**才取屬性（而非模組頂層 import）：讓鑑別力可以用
        # monkeypatch／pytest plugin 從外部注入回歸版本，證明本鎖真的會轉紅。
        from autoclaude.decision import prompt_builder
        return prompt_builder._MUTATION_SCHEMA_SECTION

    def test_the_census_and_the_registry_agree(self):
        """🔴 射程普查（B-4 的本體）：受管轄的欄位集合由**程式碼**量出來。

        新增第三個「會被送進殼」的 StepMutation 欄位 ⇒ 本格轉紅，逼人回答
        「它的 schema 描述有沒有一起要求可攜」。移除亦紅（兩個方向都不准靜默）。
        """
        assert shell_bound_mutation_fields(_PKG) == _SHELL_BOUND_SCHEMA_FIELDS

    def test_every_shell_bound_field_demands_portability_in_its_own_description(self):
        assert portability_gaps(self._schema(), _SHELL_BOUND_SCHEMA_FIELDS) == []

    def test_the_registry_is_not_the_whole_schema(self):
        """正控：本判準只管會進殼的欄位，不得擴散成「schema 每一欄都要講可攜」。

        擴散的代價是假紅——`reasoning`／`new_step_prompt` 講可攜毫無意義，
        而被噪音淹掉的判準等於沒有判準。
        """
        every = set(schema_field_descriptions(self._schema()))
        assert _SHELL_BOUND_SCHEMA_FIELDS < every
        assert portability_gaps(self._schema(), every - _SHELL_BOUND_SCHEMA_FIELDS) != []

    def test_yaml_is_not_the_input_surface_for_conditions(self):
        """釘住上面那個前提：一旦有人開始在 YAML 寫 condition_evaluator，
        本格會紅，提醒「輸入面多了一個家，prompt 那一層不再涵蓋全部」。"""
        found = [
            y.relative_to(_AUTOCLAUDE).as_posix()
            for y in _AUTOCLAUDE.rglob("*.y*ml")
            if not any(p in y.parts for p in (".git", "node_modules", ".venv"))
            and "condition_evaluator" in y.read_text(encoding="utf-8", errors="replace")
        ]
        assert not found, f"YAML 出現 condition_evaluator，輸入面假設需重新檢視：{found}"


#: 一份**合格但措辭完全不同**的描述——正控用。若判準是在比對字面，本串會誤紅。
_REWORDED_OK = (
    '  "{name}": "<驗證用的 shell 指令。這一欄會原封不動交給作業系統的殼執行，'
    'Windows 那邊是 cmd.exe、POSIX 那邊是 /bin/sh，因此請務必可攜——'
    'python -c 或 pytest 都可以；請避免 grep、sed、awk、pgrep、taskkill 這類只有'
    '單一平台才有的執行檔>",'
)


class TestTheJudgmentHasDiscriminationNotJustAKeyword:
    """🔴 只證明「有轉紅」不算數——**任何**錯誤都會轉紅。本類證明它抓的是它宣稱要抓的那件事。

    體例照 repo 既有的「純函式 ＋ 合成注入 ＋ 正控不得誤報」判例。注入一律作用在
    **記憶體裡的字串副本**上，不碰磁碟上的 tracked 檔（共用工作樹下就地改再還原
    是不該冒的風險）。
    """

    #: R85 P7 原本的判準，逐字保留當**對照組**。每一筆注入都要證明「舊判準綠、新判準紅」，
    #: 否則新判準只是比較囉唆，不是比較有鑑別力。
    @staticmethod
    def _old_keyword_judgment(text: str) -> bool:
        return "可攜" in text and "cmd.exe" in text

    @staticmethod
    def _real() -> str:
        from autoclaude.decision import prompt_builder
        return prompt_builder._MUTATION_SCHEMA_SECTION

    def _strip_requirement(self, text: str, field: str) -> str:
        """把某欄位描述裡的可攜性要求整段拿掉（回到 P7 之前的樣子）。"""
        out = []
        for line in text.splitlines():
            m = re.match(rf'^(\s*"{field}"\s*:\s*")(.*)$', line)
            out.append(f"{m.group(1)}{re.sub('。?🔴 必須可攜：.*?指令[^>]*', '', m.group(2))}"
                       if m else line)
        return "\n".join(out)

    # ── 該紅的那一組 ────────────────────────────────────────────────────────────
    def test_the_b4_regression_itself_is_caught(self):
        """🔴 本鎖的立案事由：R85 P7 落地當下的**真實狀態**——要求只加在
        `condition_evaluator`，`new_step_evaluator_command` 那兩份沒加。
        舊判準對它全綠（section 裡有「可攜」二字），這正是 B-4 能活下來的原因。"""
        regressed = self._strip_requirement(self._real(), "new_step_evaluator_command")
        assert self._old_keyword_judgment(regressed), "對照組前提失效：舊判準本該對它假綠"
        gaps = portability_gaps(regressed, _SHELL_BOUND_SCHEMA_FIELDS)
        assert [g for g in gaps if g.startswith("new_step_evaluator_command")], gaps

    def test_moving_the_requirement_to_another_field_is_caught(self):
        """把整句要求搬到 `reasoning` ⇒ 關鍵字仍在 section 裡（舊判準綠），但沒有一個
        會進殼的欄位帶著它。這是「關鍵字當充分條件」最典型的失明方向。"""
        moved = self._real()
        for f in sorted(_SHELL_BOUND_SCHEMA_FIELDS):
            moved = self._strip_requirement(moved, f)
        moved = moved.replace(
            '"reasoning": "<為何需要依條件分支>"',
            '"reasoning": "<為何需要依條件分支。必須可攜：cmd.exe 上不得用 test/grep>"')
        assert self._old_keyword_judgment(moved), "對照組前提失效：舊判準本該對它假綠"
        assert len(portability_gaps(moved, _SHELL_BOUND_SCHEMA_FIELDS)) >= 3

    def test_a_slogan_without_vocabulary_is_caught(self):
        """只寫「必須可攜」而不點名哪些指令不可攜 ⇒ 對生成端零資訊。舊判準綠。"""
        slogan = '  "condition_evaluator": "<shell 指令。必須可攜，另一邊是 cmd.exe>",'
        assert self._old_keyword_judgment(slogan)
        assert portability_gaps(slogan, {"condition_evaluator"}) != []

    def test_recommending_a_non_portable_example_is_caught(self):
        """prompt 一邊要求可攜、一邊在推薦區示範 `test -f`——判準必須認出這個自相矛盾。"""
        contradictory = (
            '  "condition_evaluator": "<shell 指令，例如 test -f foo。必須可攜：'
            '另一平台的殼是 cmd.exe，不得用 grep/sed/awk 等單平台指令>",')
        assert self._old_keyword_judgment(contradictory)
        gaps = portability_gaps(contradictory, {"condition_evaluator"})
        assert any("推薦區" in g for g in gaps), gaps

    def test_deleting_the_field_outright_is_caught(self):
        assert portability_gaps("(empty schema)", _SHELL_BOUND_SCHEMA_FIELDS) != []

    # ── 不該紅的那一組（正控；假紅的代價與漏抓一樣大）────────────────────────────
    @pytest.mark.parametrize("field", sorted(_SHELL_BOUND_SCHEMA_FIELDS))
    def test_a_reworded_but_correct_description_stays_green(self, field):
        """措辭、順序、例子、禁止句的動詞全部換掉，只要**語意仍然對**就不得判紅。

        判準若在比對固定字串，本格會紅——而那種鎖第一次有人改文案就會被關掉。
        """
        assert portability_gaps(_REWORDED_OK.format(name=field), {field}) == []

    def test_the_real_schema_is_green_for_every_shell_bound_field(self):
        assert portability_gaps(self._real(), _SHELL_BOUND_SCHEMA_FIELDS) == []

    # ── 取數管道自證：普查器對「新開的站點」真的看得見 ──────────────────────────
    @pytest.mark.parametrize("src,expected", [
        ("import subprocess\nsubprocess.Popen(m.skip_reason, shell=True)\n", "skip_reason"),
        ("PlaybookTask(evaluator_command=m.revised_prompt)\n", "revised_prompt"),
    ])
    def test_the_census_sees_a_newly_opened_site(self, tmp_path, src, expected):
        """本類唯一的失效模式是普查器回空集合而集合比對照樣綠（分母 0＝沒有東西可違反）。

        兩條入口各注入一次——只驗其中一條，另一條可以整條壞掉而無人察覺。
        """
        (tmp_path / "probe.py").write_text(src, encoding="utf-8")
        assert expected in shell_bound_mutation_fields(tmp_path)

    def test_the_census_does_not_invent_hits(self, tmp_path):
        """正控：沒有站點時必須回空集合，否則「兩個欄位」這個結論可能是雜訊湊出來的。"""
        (tmp_path / "probe.py").write_text("x = 1\nsubprocess.Popen(cmd)\n", encoding="utf-8")
        assert shell_bound_mutation_fields(tmp_path) == set()


class TestTheDuplicationIsDeliberateNotAnAccident:
    def test_autoclaude_does_not_import_the_harness_vocabulary(self):
        """`.importlinter` 第 9 條（no-harness-import）禁止 autoclaude 匯入 monorepo 護欄層。

        ⇒ 這份詞彙表是**刻意的第二份**，理由是架構契約而不是疏忽。哪天有人「順手收斂
        重複」而 import 過去，契約與本鎖會同時紅，不會只剩註解在講。
        """
        text = (_PKG / "execution" / "evaluator.py").read_text(encoding="utf-8")
        for forbidden in ("from tools", "import tools", "xplat_hazard_census"):
            assert forbidden not in text, f"可攜性判準不得依賴護欄層：{forbidden}"

    def test_the_vocabulary_only_holds_external_executables(self):
        """詞彙表只收「送給 OS 的外部程式名」——不得混進 Python 符號或字元集，
        那是別的判準（tools/tests 的 _FOREIGN_ATTR_TABLE）的射程。"""
        odd = sorted(t for t in _SINGLE_PLATFORM_ARGV0 if not (t.isalpha() and t.islower()))
        assert not odd, f"詞彙表混進非執行檔名的東西：{odd}"
