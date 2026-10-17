"""SddToPlaybookAdapter — SDD 規格 → PlaybookTask 轉譯器（adapter tier ≤400 LOC）。

對應 AutoSDD_improving_01.md §3（W3）。實作 core/ports/spec_source.ISpecSource。

安全設計（§1.3 三點截斷鏈式攻擊）：
  1. 模板白名單：evaluator_command 僅得由 _EVALUATOR_TEMPLATE 內插生成
  2. 參數消毒：黑名單字元集（⊇ CONDITIONAL 黑名單）+ 白名單 regex
  3. 末端複驗：生成 playbook 執行時仍經 pre_run_validator 整體驗證

凍結偵測（§2.2 / §3.2）：讀 state_loader 管理的 FSM 狀態檔
build/reports/fsm/FSM-STATE-*.yaml，frozen_stages 非空或 current_state
已達 SPEC_FROZEN 之後狀態，否則 raise SpecNotFrozenError（fail-closed）。
improving_115（ADR-XPLAT-016）：選檔、凍結判定與凍結摘要綁定抽到 _sdd_frozen_gate
（以專案鍵選檔、摘要存在時比對）；本檔只接線並負責規格文字的判讀：AT 文法與「出現卻未編成」
出聲（§8.1-8.2）、spec_file（§8.3）、版本與場景宣告（§8.4）。
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ...core.ports.observability import IObservabilityPort, NullObservability
from ...core.ports.spec_source import (
    AT_ID_PATTERN,
    SddSpec,
    SpecContract,
    SpecFormatVersionError,
    SpecNotFrozenError,
    SpecTaintedError,
    ac_id_of_at,
)
from ...models.playbook import PlaybookTask
from ...utils.shell_deny_chars import BASE_DENY_CHARS as _DENY
from . import _sdd_frozen_gate as _gate

# 舊名相容：_POST_FROZEN_STATES 原住在本檔（外部以此名取用），已搬到 _sdd_frozen_gate。
_POST_FROZEN_STATES = _gate.POST_FROZEN_STATES

# §1.3 截斷點 2：黑名單字元集（SSOT：autoclaude/utils/shell_deny_chars.py，DEF-101-238 收斂）
# 白名單 regex：路徑片段僅允許 word / . / / / -（消毒第二層）
_SAFE_FRAGMENT = re.compile(r"^[\w./\\-]+$")

# §1.3 截斷點 1：唯一合法 evaluator 模板（任何自由字串一律拒絕）
# R52 修正：原硬編裸字面值 "python -m pytest"，在 macOS /usr/bin 與多數現代 Linux
# distro 的乾淨 PATH（無 venv/別名）上只有 python3、無裸 python，經
# subprocess.run(shell=True) 執行恆 rc=127；不可比照 evolution 模組改用
# sys.executable——sdd_compile.py 為「編譯期產出 YAML、執行期可能是完全不同行程/
# 環境/機器」兩段式設計，編譯時路徑執行時未必存在。改為不含 python 前綴、假設
# pytest console script 在 PATH 的形式（同 execution/evaluator.py 既有建議）。
# R53：移除原第二模板 'python -m tools.{module} {args}'（死碼：_build_evaluator_cmd()
# 自始只用上一模板，全倉零呼叫點/零測試涵蓋；'tools.{module}' 為 repo 相對模組路徑非
# console script，R52 兩種解法均不適用，需要專屬設計，故移除而非疊加第三種修法）。
_EVALUATOR_TEMPLATE = 'pytest {path} -k "{at}" -q'

# AISDLC-SDD 10 場景（scenarios/ 實況）
_SCENARIOS = (
    "greenfield", "brownfield", "refactoring", "documentation", "devops",
    "integration", "migration", "performance", "security", "testing",
)

# Section 1 AC→AT 映射表列：| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
# AT 欄用 §8.1 的嚴格文法（AT_ID_PATTERN，整格全比對）：尾隨文字、舊編號、E 類 AT-{NNN}-E-n
# 都不編成 step，改由 _unmapped_at_ids 掃出並出聲（ADR §8.2），不再靜默丟棄。
_AT_ROW = re.compile(
    rf"^\|\s*(AC-[\d\-]+)\s*\|[^|]*\|\s*({AT_ID_PATTERN})\s*\|([^|]*)\|[^|]*\|([^|]*)\|",
    re.M,
)
# Section 2 Gherkin 區塊（```gherkin fence，內含 # AT-XXX-Y-Z 標頭）。
# 標頭改取寬鬆字樣再由 _unmapped_at_ids 驗證：不再把 `AT-14-1-1_a` 靜默截成前綴 `AT-14-1-1`。
_GHERKIN_BLOCK = re.compile(r"```gherkin\s*\n(.*?)```", re.S)
_GHERKIN_AT_ID = re.compile(r"#\s*(AT-[\w-]+)")
# 宣告位置掃描（§8.2）：表格列整行；寬鬆 AT 字樣（要抓得到格式錯的 ID）；任意圍欄區塊。
_TABLE_ROW = re.compile(r"^\|.*$", re.M)
_LOOSE_AT = re.compile(r"(?<![\w-])AT-[\w-]+")
_FENCED = re.compile(r"```.*?```", re.S)

# Gherkin Then 斷言轉譯規則（§3.1 實例表）
_QUOTED_LITERAL = re.compile(r"[「\"']([^」\"']+)[」\"']")
_STATUS_CODE = re.compile(r"\b([1-5]\d{2})\b(?:\s+([A-Za-z][A-Za-z ]*[A-Za-z]|[A-Za-z]+))?")
_QUANTITATIVE = re.compile(r"[<>≤≥]|\bms\b|\b秒\b|%")
_FALLBACK_REGEX = r"\bPASS(ED)?\b"
# improving_31 W-31-1：否定標記（須出現在引號「之外、之前」才視為負向斷言）。
# 修正「不應包含「X」」被當成「要求 X 出現」的語意顛倒（mis-specify）缺口。
# improving_33 W-33-1（DEF-31-001）：裸 \bnot\b 排除「not only…（but）」「is not empty」
# 兩慣用語——此處 not 非否定其後引號（"not only X but"＝連接詞、"not empty"＝存在斷言）。
# 強標記（should not / 不應…）與真否定（not contain / not visible）不受影響；.search 左掃
# 特性確保「is not empty but does not contain 'X'」仍因第二個 not 命中 → 'X' 正確負向。
_NEGATION_MARKER = re.compile(
    r"不應|不得|不可|不能|不會|不要|不准|不再|禁止|沒有|無法"
    r"|不存在|不包含|不顯示|不出現|不回傳|不允許|不洩漏|不暴露"
    r"|\bshould\s+not\b|\bmust\s+not\b|\bshall\s+not\b|\bcannot\b"
    r"|\bnot\b(?!\s+(?:only|empty)\b)|\bnever\b|\bno\s+longer\b",
    re.I,
)

# E2E 屬 RTM 層（SCG-5，retry=2）；Unit/Integration/Contract 屬 PR 層（SCG-4，retry=5）
# 對齊 transition_rules RETRY_LIMITS：PR_REVIEW=5 / RTM_VERIFY=2
_RETRY_BY_GATE = {"SCG-4": 5, "SCG-5": 2}

# improving_67 W-67-2：規格格式版本防漂移閘（fail-closed）。
# 缺欄 → 預設 1.0（既有規格皆無此欄，向後相容零退化）；宣告值不在支援集 →
# raise SpecFormatVersionError（拒絕誤解析未來不相容格式）。
# improving_115 S-11／S-12（ADR §8.4）：宣告改為「**行首**（容許裝飾）的 spec-format-version」，
# 值取同行 [^\d\n]{0,16}(\d+\.\d+)；舊樣式 \D{0,4} 對多一個空白、`** : 2.0`、反引號、全形冒號
# 都解不出而退回預設 1.0（fail-open）。行內提及（散文）不算宣告；宣告了卻解析不出值 → 拒絕。
# 裝飾集合＝ADR 列的 `>`、`*`、`_`、反引號、`-`、空白，另容 `<!--`（既有測試與生產端用的
# HTML 註解形）、`|`（舊樣式本來就收的表格列形）與 BOM（檔首第一行也算行首）：
# 不收窄既有放行的宣告形態。圍欄程式碼區塊內的字樣不是宣告（例如 Gherkin 的 `Scenario: Login`）。
_DECL_PREFIX = r"^(?:[ \t>*_`|\-\ufeff]|<!--)*"
_SUPPORTED_SPEC_FORMAT_VERSIONS = frozenset({"1.0"})
_DEFAULT_SPEC_FORMAT_VERSION = "1.0"
_SPEC_VERSION_DECL = re.compile(
    rf"{_DECL_PREFIX}spec[-_ ]format[-_ ]version(?P<rest>[^\n]*)", re.I | re.M)
_SPEC_VERSION_VALUE = re.compile(r"[^\d\n]{0,16}(\d+\.\d+)")
# 場景宣告：行首 `scenario`／`場景` ＋ 半／全形冒號後的英文字；優先於整份文字的子字串推斷。
_SCENARIO_DECL = re.compile(
    rf"{_DECL_PREFIX}(?:scenario|場景)[ \t*_`]*[:：][ \t*_`]*([A-Za-z]+)", re.I | re.M)

# DEF-200-176：官方模板唯一命名（`TEST-CONTRACT-SPEC-*.md`／`TCS-*.md`）；
# `CONTRACT-TEST-SPEC-INTEGRATION-*.md`／`ENV-CONTRACT-SPEC-*.md` 等模板同樣含
# 「CONTRACT」+「SPEC」子字串但語意不同，字母序 `sorted()[0]` 會靜默選錯檔。
_EXACT_CONTRACT_SPEC_RE = re.compile(r"^(TEST-CONTRACT-SPEC-|TCS-)", re.I)


class SddToPlaybookAdapter:
    """ISpecSource 實作：解析凍結後的 TEST-CONTRACT-SPEC，編譯為 PlaybookTask。"""

    def __init__(
        self,
        observability: IObservabilityPort | None = None,
        *,
        fsm_state_path: str | None = None,
        test_path: str = "tests",
        fsm_project: str | None = None,
    ):
        """
        Args:
            observability: weak_regex audit 事件出口（contract #7；未注入 → no-op）
            fsm_state_path: 顯式 FSM 狀態檔路徑（最優先）；None 時自 spec_dir 向上搜尋
                            build/reports/fsm/FSM-STATE-*.yaml
            test_path: evaluator 模板的 pytest 目標路徑（白名單模板參數）
            fsm_project: FSM 專案鍵（ADR §7.1）。None＝建構時讀環境 SDD_PROJECT；
                         空字串＝明確不指定、不讀環境（Bridge 行程內一律顯式傳值，
                         不得讀到 Bridge 自己的環境）；其餘＝用它選 FSM-STATE-<鍵>.yaml
        """
        self._obs = observability or NullObservability()
        self._fsm_state_path = fsm_state_path
        self._test_path = self._sanitize(test_path)
        self._fsm_project = _gate.resolve_project_key(fsm_project)
        self._absent_announced = False  # sdd.frozen_digest_absent 每個實例只出聲一次

    # ──────────────────────────────────────────────
    # ISpecSource 契約
    # ──────────────────────────────────────────────
    def load_spec(self, spec_dir: str, spec_file: str | None = None) -> SddSpec:
        """spec_dir 本身若是檔案，視為 spec_file（引擎 PRE_RUN 以 workflow_path 呼叫，
        port 簽名因此不必改）；spec_file 相對 spec_dir 或絕對，須在其下、副檔名 .md（§8.3）。"""
        root, explicit = self._spec_target(spec_dir, spec_file)
        text, spec_path = self._read_contract_spec(root, explicit)
        digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        # 凍結硬閘（Spec-First Gate）＋凍結摘要綁定（G-06）
        fsm_project, digest_status = self._assert_frozen(root, spec_path, digest)
        # W-67-2 防漂移硬閘（fail-closed）；W-85-2：接回已驗證版本表面化到 SddSpec（不再丟棄）
        version = self._check_spec_format_version(text)
        contracts = tuple(self._parse_contracts(text))
        unmapped = self._unmapped_at_ids(text, {c.at_id for c in contracts})
        if unmapped:  # 出現卻未編成：絕不靜默丟棄（§8.2）。load_spec 不拋：引擎 PRE_RUN 也走它
            self._obs.record_event("sdd.at_unmapped", {
                "at_ids": list(unmapped), "count": len(unmapped),
                "spec_path": str(spec_path), "reasons": dict(unmapped)})
        return SddSpec(
            spec_path=str(spec_path),
            digest=digest,
            scenario=self._scenario_of(text, str(spec_path)),
            contracts=contracts,
            spec_format_version=version,
            fsm_project=fsm_project,
            frozen_digest_status=digest_status,
            unmapped_at_ids=tuple(unmapped),
        )

    def compile_tasks(self, spec: SddSpec) -> list[PlaybookTask]:
        """SddSpec → PlaybookTask 序列。純函數、無 IO。"""
        tasks: list[PlaybookTask] = []
        prev_ac: str | None = None
        digest8 = spec.digest.split(":")[-1][:8]
        for c in spec.contracts:
            tasks.append(PlaybookTask(
                step_id=f"sdd-{spec.scenario}-{c.at_id.lower()}",
                name=c.at_id,
                prompt=(
                    f"依下列契約實作並使測試通過：\n{c.gherkin}\n"
                    f"規格出處：{spec.spec_path}（digest {digest8}）"
                    f"{self._acceptance_gate(c)}"
                ),
                expected_output_regex=c.expected_regex,
                evaluator_command=c.evaluator_cmd,
                max_retries=_RETRY_BY_GATE.get(c.scg_gate),
                # 同一 AC 內連續 AT 維持脈絡；跨 AC 隔離污染（§3.1）
                maintain_context=(c.ac_id == prev_ac),
                # improving_56 W-56-2（DEF-56-001）：權威全 digest 結構化傳遞給逆向橋接，
                # 取代 prompt 內 8 字元截斷（digest8 僅留作 prompt 人類可讀提示）。
                spec_digest=spec.digest,
                # improving_61 W-61-1：搭載 weak_regex 旗標（轉譯保真度第二信號），
                # 供逆向橋接收集為 weak_regex_at_ids 餵轉譯元學習。轉譯輸出語意不變。
                weak_regex=c.weak_regex,
            ))
            prev_ac = c.ac_id
        return tasks

    # F-SBR-001（D-SBR-01／02／03／08）：引擎的兩層驗收——regex 比對 AI 的最後回覆、evaluator
    # 在引擎工作目錄以裸 pytest 執行——所需的資訊原本一樣都不在 prompt 裡，AI 只能碰運氣
    # （真 claude 探針：自然命名的測試被 -k 選到 0 個、工作目錄沒有 tests/、模組在工作目錄根
    # 而無 conftest 時裸 pytest 匯入失敗、輸出契約只靠子字串偶然命中、檔案被寫進規格所在的樹）。
    # evaluator 模板與 regex 推導規則皆不動，只讓 AI 知道既有契約；工作目錄是執行期才知道的量，
    # 編譯期寫不進 playbook，只能在 prompt 裡告知。
    def _acceptance_gate(self, c: SpecContract) -> str:
        tok = c.at_id.replace("-", "_")  # 與 _build_evaluator_cmd 同一個底線化（-k 的 token）
        return (
            "\n驗收閘（由引擎親自執行，AI 自稱完成不算）：\n"
            "1. 程式與測試一律建立在「目前工作目錄」之下；規格出處只供閱讀，"
            "不要因它的路徑而把檔案寫到別處。\n"
            "2. 完成前請在目前工作目錄親自執行評估指令，須通過"
            f"（以裸 pytest 執行，不是 python -m pytest）：{c.evaluator_cmd}\n"
            f"   測試檔須放在 {self._test_path}/ 下，且測試函式、類別或檔名須含 {tok}"
            f"（例：def test_{tok}_basic），否則 -k 篩選會選到 0 個測試而失敗。\n"
            "3. 你的最後一則回覆須符合此 regex（Python re.search；(?=.*X) 表示須含 X、"
            f"(?!.*X) 表示全文不得含 X，引述也算）：{c.expected_regex}"
        )

    # ──────────────────────────────────────────────
    # 凍結偵測（§2.2 docstring 機制）
    # ──────────────────────────────────────────────
    def _assert_frozen(self, root: Path, spec_path: Path, digest: str) -> tuple[str, str]:
        """凍結硬閘＋凍結摘要綁定；回 (採用的 FSM 狀態檔鍵, "verified"｜"absent")。"""
        state_file = _gate.find_fsm_state(
            root, explicit_path=self._fsm_state_path, project_key=self._fsm_project)
        if state_file is None:
            raise SpecNotFrozenError(
                f"{root}: 找不到 FSM 狀態檔（build/reports/fsm/FSM-STATE-*.yaml）"
                "——規格未經 FSMRuntime 凍結，依 Spec-First Gate fail-closed 拒絕"
            )
        status = _gate.check_digest(_gate.read_frozen_stages(state_file), spec_path, digest)
        key = _gate.state_key(state_file)
        if status == "absent" and not self._absent_announced:
            # 舊狀態檔／凍結時沒帶 --digest：維持放行，但「凍結沒綁內容」必須可見（只出聲一次）
            self._absent_announced = True
            self._obs.record_event("sdd.frozen_digest_absent", {
                "state_file": str(state_file), "fsm_project": key, "spec_path": str(spec_path)})
        return key, status

    def _check_spec_format_version(self, text: str) -> str:
        """W-67-2：擷取並驗證規格格式版本（防漂移 fail-closed）。

        缺版本欄 → 預設 1.0 放行（既有規格皆無此欄，向後相容）；宣告值不在支援集、或
        宣告了卻解析不出版本值（S-11）→ raise SpecFormatVersionError。
        無論放行/拒絕皆經 IObservabilityPort 留審計痕。回傳解析（或預設）版本字串。
        """
        decl = _SPEC_VERSION_DECL.search(_FENCED.sub("\n", text))
        m = _SPEC_VERSION_VALUE.match(decl.group("rest")) if decl else None
        if decl and not m:
            self._obs.record_event(
                "sdd.spec_format_version", {"version": "", "declared": True, "accepted": False})
            raise SpecFormatVersionError(
                f"規格宣告了 spec-format-version 卻解析不出版本值（{decl.group(0).strip()!r}）"
                "——無法確認格式版本，依防漂移閘 fail-closed 拒絕（避免靜默退回預設 1.0）"
            )
        version = m.group(1) if m else _DEFAULT_SPEC_FORMAT_VERSION
        declared = bool(m)
        if version not in _SUPPORTED_SPEC_FORMAT_VERSIONS:
            self._obs.record_event(
                "sdd.spec_format_version",
                {"version": version, "declared": declared, "accepted": False},
            )
            raise SpecFormatVersionError(
                f"規格格式版本 {version!r} 不在支援集 "
                f"{sorted(_SUPPORTED_SPEC_FORMAT_VERSIONS)}——疑似 SDD 框架跨版格式漂移，"
                f"依防漂移閘 fail-closed 拒絕（避免靜默誤解析）"
            )
        self._obs.record_event(
            "sdd.spec_format_version",
            {"version": version, "declared": declared, "accepted": True},
        )
        return version

    # ──────────────────────────────────────────────
    # 解析（TEST-CONTRACT-SPEC 結構，F11）
    # ──────────────────────────────────────────────
    def _spec_target(self, spec_dir: str, spec_file: str | None) -> tuple[Path, Path | None]:
        """正規化規格來源 → (spec_dir 目錄, 顯式規格檔 | None)（ADR §8.3）。

        顯式規格檔：相對路徑以 spec_dir 為基準，resolve() 後必須落在 spec_dir 之下、副檔名 .md
        的檔案；**不掃描、不套官方命名規則**（呼叫端已具名）。副檔名與根內限制是縱深防禦：
        檔案內容會進 prompt 與摘要，不能讓路徑指到 spec_dir 內（或外）的任意檔。
        """
        root = Path(spec_dir)
        if root.is_file():  # 路徑可為檔：引擎 PRE_RUN 的 load_spec(workflow_path)
            if spec_file is not None:
                raise ValueError(f"{spec_dir}: spec_dir 本身已是檔案，不得再指定 spec_file")
            root, spec_file = root.parent, str(root.resolve())
        if spec_file is None:
            return root, None
        base = root.resolve()
        picked = Path(spec_file)
        picked = (picked if picked.is_absolute() else base / picked).resolve()
        try:
            picked.relative_to(base)
        except ValueError:
            raise ValueError(f"{spec_file}: 不在 spec_dir（{spec_dir}）之下，拒絕") from None
        if picked.suffix.lower() != ".md":
            raise ValueError(f"{spec_file}: spec_file 副檔名必須是 .md")
        if not picked.is_file():
            raise FileNotFoundError(f"{picked}: 找不到指定的規格檔 spec_file")
        return root, picked

    def _read_contract_spec(self, root: Path, spec_file: Path | None) -> tuple[str, Path]:
        if spec_file is not None:
            return spec_file.read_text(encoding="utf-8"), spec_file
        candidates = sorted(
            p for p in root.rglob("*.md")
            if ("CONTRACT" in p.name.upper() and "SPEC" in p.name.upper())
            or p.name.upper().startswith("TCS-")
        )
        if not candidates:
            raise FileNotFoundError(
                f"{root}: 找不到 TEST-CONTRACT-SPEC（*CONTRACT*SPEC*.md / TCS-*.md）"
            )
        if len(candidates) > 1:
            exact = [p for p in candidates if _EXACT_CONTRACT_SPEC_RE.match(p.name)]
            if len(exact) != 1:
                raise ValueError(
                    f"{root}: {len(candidates)} 份規格檔皆含「CONTRACT+SPEC」，"
                    f"官方命名（TEST-CONTRACT-SPEC-*.md/TCS-*.md）未能唯一鎖定其一，"
                    f"字母序選檔可能選錯（DEF-200-176；可改用 spec_file 指定）："
                    f"{[p.name for p in candidates]}"
                )
            candidates = exact
        picked = candidates[0]
        return picked.read_text(encoding="utf-8"), picked

    def _scenario_of(self, text: str, spec_path: str = "") -> str:
        """場景：行首 `scenario`／`場景` 宣告優先（值須屬 10 場景，否則 ValueError）；
        無宣告才沿用整份文字的子字串推斷（不改既有 step_id，避免舊 checkpoint 失效），
        並出聲 sdd.scenario_inferred 讓推斷可見（S-12）。"""
        decl = _SCENARIO_DECL.search(_FENCED.sub("\n", text))
        if decl:
            declared = decl.group(1).lower()
            if declared not in _SCENARIOS:
                raise ValueError(
                    f"規格宣告的場景 {decl.group(1)!r} 不在 10 場景內：{list(_SCENARIOS)}")
            return declared
        lowered = text.lower()
        inferred = next((s for s in _SCENARIOS if s in lowered), "greenfield")
        self._obs.record_event(
            "sdd.scenario_inferred", {"scenario": inferred, "spec_path": spec_path})
        return inferred

    def _unmapped_at_ids(self, text: str, compiled: set[str]) -> dict[str, str]:
        """宣告位置出現、卻沒編成 step 的 AT → {at_id: 原因}（首見順序、去重；ADR §8.2）。

        只掃**宣告位置**：①AC 映射列（第一欄形如 `AC-…` 的表格列）第三欄的第一個寬鬆 AT 字樣；
        ②每個 gherkin 區塊的第一個 `# AT-…` 標頭。§3 的清單表（第一欄是 AT）、§4 的邊界表
        （第一欄是場景類型）與內文散文都不是宣告位置——所以照模板填 §3／§4 不會讓編譯失敗。
        原因：invalid_id＝不合 §8.1 文法；ac_mismatch＝列的 AC 與 AT 前兩段推得者不同；
        malformed_row＝ID 合法但整列沒進 §1 表（例如 ID 後有尾隨文字）；no_row＝只有 Gherkin 標頭。
        """
        found: list[tuple[int, str, str]] = []
        for row in _TABLE_ROW.finditer(text):
            cells = row.group(0).split("|")
            token = _LOOSE_AT.search(cells[3]) if len(cells) >= 4 else None
            if token and cells[1].strip().startswith("AC-"):
                ac_id, at_id = cells[1].strip(), token.group(0)
                derived = ac_id_of_at(at_id)
                reason = ("invalid_id" if derived is None
                          else "ac_mismatch" if derived != ac_id else "malformed_row")
                found.append((row.start(), at_id, reason))
        for block in _GHERKIN_BLOCK.finditer(text):
            token = _GHERKIN_AT_ID.search(block.group(1))
            if token:
                reason = "no_row" if ac_id_of_at(token.group(1)) else "invalid_id"
                found.append((block.start(1) + token.start(1), token.group(1), reason))
        unmapped: dict[str, str] = {}
        for _pos, at_id, reason in sorted(found):
            if at_id not in compiled:
                unmapped.setdefault(at_id, reason)
        return unmapped

    def _parse_contracts(self, text: str) -> list[SpecContract]:
        gherkin_by_at: dict[str, str] = {}
        for block in _GHERKIN_BLOCK.findall(text):
            m = _GHERKIN_AT_ID.search(block)
            if m:
                gherkin_by_at[m.group(1)] = block.strip()

        contracts: list[SpecContract] = []
        seen: set[str] = set()
        for ac_id, at_id, at_desc, test_type in _AT_ROW.findall(text):
            # 重複列；或列的 AC id ≠ AT 前兩段推得者（逆向 RTM 以前兩段歸 AC，正向若放過不一致的
            # 列，兩邊會悄悄歸到不同 AC）＝未編成，由 _unmapped_at_ids 出聲
            if at_id in seen or ac_id_of_at(at_id) != ac_id:
                continue
            seen.add(at_id)
            gherkin = gherkin_by_at.get(at_id, at_desc.strip())
            regex, weak = self._gherkin_to_regex(gherkin)
            if weak:
                # §3.1：weak_regex 必經 IObservabilityPort 留審計痕，禁 silent fallback
                self._obs.record_event(
                    "sdd.weak_regex", {"at_id": at_id, "gherkin": gherkin}
                )
            scg_gate = "SCG-5" if "E2E" in test_type.upper() else "SCG-4"
            contracts.append(SpecContract(
                ac_id=ac_id,
                at_id=at_id,
                gherkin=gherkin,
                expected_regex=regex,
                evaluator_cmd=self._build_evaluator_cmd(at_id),
                scg_gate=scg_gate,
                weak_regex=weak,
            ))
        return contracts

    # ──────────────────────────────────────────────
    # Gherkin Then → expected_output_regex（§3.1 轉譯實例表）
    # ──────────────────────────────────────────────
    def _gherkin_to_regex(self, gherkin: str) -> tuple[str, bool]:
        then_lines = self._then_assertions(gherkin)
        # §3.1 複雜斷言組合：≥2 個引號字面值 → 順序無關 AND（lookahead），
        # 使 evaluator 驗證全部引號斷言（修正「多引號只取首條」under-specify 缺口）。
        # 僅限同類多引號：刻意保留「quoted wins over status code」既有設計決策
        # （混合 quoted/status 時 status 不納入，見 test_quoted_wins_over_status_code）。
        # W-31-1：依「引號之前是否有否定標記」分流正向/負向斷言，修正負向語意顛倒。
        pos_frags: list[str] = []
        neg_frags: list[str] = []
        for line in then_lines:
            m = _QUOTED_LITERAL.search(line)
            if not m:
                continue
            frag = re.escape(m.group(1))
            if _NEGATION_MARKER.search(line[: m.start()]):
                neg_frags.append(frag)
            else:
                pos_frags.append(frag)
        if neg_frags:
            # 含負向斷言：正向 (?=.*P) 要求出現 + 負向 (?!.*N) 要求不出現。
            # 負向 lookahead 在 re.search 下需 \A 錨定才語意正確（否則於 N 之後位置
            # 恆真）；正向片段一併納入同一 \A 錨定式（順序無關 AND）。
            parts = [f"(?=.*{q})" for q in pos_frags] + [f"(?!.*{q})" for q in neg_frags]
            return "(?s)\\A" + "".join(parts), False
        if len(pos_frags) >= 2:
            # 純正向 ≥2 引號：維持 improving_29 既有格式（不加 \A，零行為變化）。
            return "(?s)" + "".join(f"(?=.*{q})" for q in pos_frags), False
        # 單一正向引號：維持既有逐行推導（向後相容、零行為變化）
        if pos_frags:
            return pos_frags[0], False
        # W-32-1/W-40-1：否定狀態碼（「不應回傳 500」/ must not return 403）→ 要求該碼（與
        # 尾隨片語）不出現，修正原 (?i)(500) 語意顛倒；負向 lookahead 在 re.search 下需 \A 錨定。
        # W-41-1（DEF-41-001）：與引號路徑（244-260）對稱，跨行聚合所有狀態碼斷言——原僅取
        # 「首條」status 行即 return，致多條負向（不應回傳 500 And 不應回傳 403）只擋首條、或正負
        # 混合時負向遭丟棄＝under-specify 漏放。改為收集：負向碼/片語各自 (?!.*x)、正向以
        # (?=.*(?:碼|片語)) 要求出現（片語沿用正向 strip().lower()+re.escape，負正對稱可審）。
        pos_status: list[str] = []  # 每項 "碼|片語"（alternation：任一出現即表該狀態）
        neg_status: list[str] = []  # 每項為禁出現片段（碼或片語，各自獨立 lookahead）
        has_phrase = False
        for line in then_lines:
            if _QUANTITATIVE.search(line):
                continue  # 量化 NFR 斷言不可由文字推導（含 500ms 之 500 不誤判為狀態碼）
            status = _STATUS_CODE.search(line)
            if not status:
                continue
            code = status.group(1)
            phrase = re.escape(status.group(2).strip().lower()) if status.group(2) else None
            has_phrase = has_phrase or bool(phrase)
            if _NEGATION_MARKER.search(line[: status.start()]):
                neg_status.append(code)
                if phrase:
                    neg_status.append(phrase)
            else:
                pos_status.append(code + ("|" + phrase if phrase else ""))
        if neg_status:
            # 含負向：正向 (?=.*(?:碼|片語)) 要求出現 +
            # 負向 (?!.*片段) 要求不出現（同引號路徑 259）。
            # 含字母片語 → 全域 (?i) 與正向 case 一致（W-40-1）；單負向無片語逐位元維持
            # (?s)\A(?!.*碼)、含片語維持 (?is)\A(?!.*碼)(?!.*片語)（哨兵鎖定，零退化）。
            flags = "(?is)" if has_phrase else "(?s)"
            parts = [f"(?=.*(?:{p}))" for p in pos_status] + [f"(?!.*{n})" for n in neg_status]
            return flags + "\\A" + "".join(parts), False
        if pos_status:
            # 純正向：維持既有 alternation 格式 (?i)(碼|片語) 取首條（哨兵鎖定，零行為變化）。
            # 多正向狀態碼語意罕見且歧義，沿用既有「首條 wins」設計，
            # 不臆測聚合（對齊 quoted-wins）。
            return "(?i)(" + pos_status[0] + ")", False
        return _FALLBACK_REGEX, True

    @staticmethod
    def _then_assertions(gherkin: str) -> list[str]:
        """抽出 Then 與其後續 And／But 行（And/But 僅在 Then 之後才算斷言）。

        W-42-1（DEF-42-002）：But 為標準 Gherkin 關鍵字（語意同 And，慣用於負向對比，
        如「Then 回傳 200 But 不應回傳 500」），原僅認 And → But 行連同其負向斷言被靜默
        丟棄＝under-specify 漏放；改與 And 同等處理（負向斷言保真度家族 DEF-31/32/41）。
        """
        out: list[str] = []
        in_then = False
        for raw in gherkin.splitlines():
            line = raw.strip()
            if line.startswith("Then"):
                in_then = True
                out.append(line)
            elif line.startswith(("And", "But")) and in_then:
                out.append(line)
            elif line and not line.startswith(("#", "And", "But")):
                in_then = False
        return out

    # ──────────────────────────────────────────────
    # 消毒 + 白名單模板（§1.3 截斷點 1+2）
    # ──────────────────────────────────────────────
    def _sanitize(self, fragment: str) -> str:
        tainted = [ch for ch in fragment if ch in _DENY]
        if tainted or not _SAFE_FRAGMENT.match(fragment):
            raise SpecTaintedError(
                f"規格片段含非法字元 {tainted or fragment!r}（疑似注入向量）"
            )
        return fragment

    def _build_evaluator_cmd(self, at_id: str) -> str:
        # pytest -k 表達式不接受連字號 → at_id 消毒為底線形式
        at_sanitized = self._sanitize(at_id).replace("-", "_")
        return _EVALUATOR_TEMPLATE.format(path=self._test_path, at=at_sanitized)
