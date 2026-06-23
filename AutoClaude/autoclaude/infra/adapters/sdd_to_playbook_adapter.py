"""SddToPlaybookAdapter — SDD 規格 → PlaybookTask 轉譯器（adapter tier ≤400 LOC）。

對應 AutoSDD_improving_01.md §3（W3）。實作 core/ports/spec_source.ISpecSource。

安全設計（§1.3 三點截斷鏈式攻擊）：
  1. 模板白名單：evaluator_command 僅得由 _EVALUATOR_TEMPLATES 內插生成
  2. 參數消毒：黑名單字元集（⊇ CONDITIONAL 黑名單）+ 白名單 regex
  3. 末端複驗：生成 playbook 執行時仍經 pre_run_validator 整體驗證

凍結偵測（§2.2 / §3.2）：讀 state_loader 管理的 FSM 狀態檔
build/reports/fsm/FSM-STATE-*.yaml，frozen_stages 非空或 current_state
已達 SPEC_FROZEN 之後狀態，否則 raise SpecNotFrozenError（fail-closed）。
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml

from ...core.ports.observability import IObservabilityPort, NullObservability
from ...core.ports.spec_source import (
    SddSpec,
    SpecContract,
    SpecNotFrozenError,
    SpecTaintedError,
)
from ...models.playbook import PlaybookTask

# §1.3 截斷點 2：黑名單字元集 ⊇ CONDITIONAL 黑名單 {!,`,>,<,~,$}，再加 &;
_DENY = set("!`><~$&;")
# 白名單 regex：路徑片段僅允許 word / . / / / -（消毒第二層）
_SAFE_FRAGMENT = re.compile(r"^[\w./\\-]+$")

# §1.3 截斷點 1：唯二合法 evaluator 模板（任何自由字串一律拒絕）
_EVALUATOR_TEMPLATES = (
    'python -m pytest {path} -k "{at}" -q',
    "python -m tools.{module} {args}",
)

# happy path 上 SPEC_FROZEN 及其後繼狀態（transition_rules._HAPPY_PATH 實況）
_POST_FROZEN_STATES = frozenset({
    "SPEC_FROZEN", "TEST_CONTRACT_NEGOTIATED", "IMPLEMENTATION",
    "SANDBOX_HARDENING_GATE", "EXECUTION_EVALUATION", "ADVERSARIAL_EVALUATION",
    "PR_REVIEW", "SPEC_AUDIT", "RTM_VERIFY", "RELEASE_READY", "RELEASE",
})

# AISDLC-SDD 10 場景（scenarios/ 實況）
_SCENARIOS = (
    "greenfield", "brownfield", "refactoring", "documentation", "devops",
    "integration", "migration", "performance", "security", "testing",
)

# Section 1 AC→AT 映射表列：| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
_AT_ROW = re.compile(
    r"^\|\s*(AC-[\d\-]+)\s*\|[^|]*\|\s*(AT-[\d\-]+)\s*\|([^|]*)\|[^|]*\|([^|]*)\|",
    re.M,
)
# Section 2 Gherkin 區塊（```gherkin fence，內含 # AT-XXX-Y-Z 標頭）
_GHERKIN_BLOCK = re.compile(r"```gherkin\s*\n(.*?)```", re.S)
_GHERKIN_AT_ID = re.compile(r"#\s*(AT-[\d\-]+)")

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


class SddToPlaybookAdapter:
    """ISpecSource 實作：解析凍結後的 TEST-CONTRACT-SPEC，編譯為 PlaybookTask。"""

    def __init__(
        self,
        observability: IObservabilityPort | None = None,
        *,
        fsm_state_path: str | None = None,
        test_path: str = "tests",
    ):
        """
        Args:
            observability: weak_regex audit 事件出口（contract #7；未注入 → no-op）
            fsm_state_path: 顯式 FSM 狀態檔路徑；None 時自 spec_dir 向上搜尋
                            build/reports/fsm/FSM-STATE-*.yaml
            test_path: evaluator 模板的 pytest 目標路徑（白名單模板參數）
        """
        self._obs = observability or NullObservability()
        self._fsm_state_path = fsm_state_path
        self._test_path = self._sanitize(test_path)

    # ──────────────────────────────────────────────
    # ISpecSource 契約
    # ──────────────────────────────────────────────
    def load_spec(self, spec_dir: str) -> SddSpec:
        text, spec_file = self._read_contract_spec(spec_dir)
        self._assert_frozen(spec_dir)  # 凍結硬閘（Spec-First Gate）
        digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        return SddSpec(
            spec_path=str(spec_file),
            digest=digest,
            scenario=self._scenario_of(text),
            contracts=tuple(self._parse_contracts(text)),
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
                ),
                expected_output_regex=c.expected_regex,
                evaluator_command=c.evaluator_cmd,
                max_retries=_RETRY_BY_GATE.get(c.scg_gate),
                # 同一 AC 內連續 AT 維持脈絡；跨 AC 隔離污染（§3.1）
                maintain_context=(c.ac_id == prev_ac),
                # improving_56 W-56-2（DEF-56-001）：權威全 digest 結構化傳遞給逆向橋接，
                # 取代 prompt 內 8 字元截斷（digest8 僅留作 prompt 人類可讀提示）。
                spec_digest=spec.digest,
            ))
            prev_ac = c.ac_id
        return tasks

    # ──────────────────────────────────────────────
    # 凍結偵測（§2.2 docstring 機制）
    # ──────────────────────────────────────────────
    def _assert_frozen(self, spec_dir: str) -> None:
        state_file = self._find_fsm_state(spec_dir)
        if state_file is None:
            raise SpecNotFrozenError(
                f"{spec_dir}: 找不到 FSM 狀態檔（build/reports/fsm/FSM-STATE-*.yaml）"
                "——規格未經 FSMRuntime 凍結，依 Spec-First Gate fail-closed 拒絕"
            )
        doc = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
        root = doc.get("fsm_state", {}) or {}
        frozen_stages = root.get("frozen_stages") or []
        current = root.get("current_state")
        if not frozen_stages and current not in _POST_FROZEN_STATES:
            raise SpecNotFrozenError(
                f"{state_file}: frozen_stages 為空且 current_state={current!r} "
                f"未達 SPEC_FROZEN 之後狀態"
            )

    def _find_fsm_state(self, spec_dir: str) -> Path | None:
        if self._fsm_state_path:
            p = Path(self._fsm_state_path)
            return p if p.is_file() else None
        node = Path(spec_dir).resolve()
        for candidate in (node, *node.parents):
            fsm_dir = candidate / "build" / "reports" / "fsm"
            if fsm_dir.is_dir():
                matches = sorted(fsm_dir.glob("FSM-STATE-*.yaml"))
                if matches:
                    return matches[0]
        return None

    # ──────────────────────────────────────────────
    # 解析（TEST-CONTRACT-SPEC 結構，F11）
    # ──────────────────────────────────────────────
    def _read_contract_spec(self, spec_dir: str) -> tuple[str, Path]:
        root = Path(spec_dir)
        candidates = sorted(
            p for p in root.rglob("*.md")
            if ("CONTRACT" in p.name.upper() and "SPEC" in p.name.upper())
            or p.name.upper().startswith("TCS-")
        )
        if not candidates:
            raise FileNotFoundError(
                f"{spec_dir}: 找不到 TEST-CONTRACT-SPEC（*CONTRACT*SPEC*.md / TCS-*.md）"
            )
        spec_file = candidates[0]
        return spec_file.read_text(encoding="utf-8"), spec_file

    def _scenario_of(self, text: str) -> str:
        lowered = text.lower()
        for s in _SCENARIOS:
            if s in lowered:
                return s
        return "greenfield"

    def _parse_contracts(self, text: str) -> list[SpecContract]:
        gherkin_by_at: dict[str, str] = {}
        for block in _GHERKIN_BLOCK.findall(text):
            m = _GHERKIN_AT_ID.search(block)
            if m:
                gherkin_by_at[m.group(1)] = block.strip()

        contracts: list[SpecContract] = []
        seen: set[str] = set()
        for ac_id, at_id, at_desc, test_type in _AT_ROW.findall(text):
            if "{" in at_id or at_id in seen:  # 模板佔位列 / 重複列
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
            # 含負向：正向 (?=.*(?:碼|片語)) 要求出現 + 負向 (?!.*片段) 要求不出現（同引號路徑 259）。
            # 含字母片語 → 全域 (?i) 與正向 case 一致（W-40-1）；單負向無片語逐位元維持
            # (?s)\A(?!.*碼)、含片語維持 (?is)\A(?!.*碼)(?!.*片語)（哨兵鎖定，零退化）。
            flags = "(?is)" if has_phrase else "(?s)"
            parts = [f"(?=.*(?:{p}))" for p in pos_status] + [f"(?!.*{n})" for n in neg_status]
            return flags + "\\A" + "".join(parts), False
        if pos_status:
            # 純正向：維持既有 alternation 格式 (?i)(碼|片語) 取首條（哨兵鎖定，零行為變化）。
            # 多正向狀態碼語意罕見且歧義，沿用既有「首條 wins」設計，不臆測聚合（對齊 quoted-wins）。
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
        return _EVALUATOR_TEMPLATES[0].format(path=self._test_path, at=at_sanitized)
