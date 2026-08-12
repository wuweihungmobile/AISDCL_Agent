from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from ..core.ports.quota_meter import DEGRADED_CAP

# 🔴 R82（C3／C6，掌舵者訴求 b+c）：**額度門檻的名字與出廠預設不在這裡發明**。
# 唯一的家＝monorepo 根層 `tools/lib/quota_policy.py` 的 `ENV_SPEC`（50/70/85/95 四個錨點）。
# AutoClaude **不能** import 它（`.importlinter` 的 autoclaude ↛ tools forbidden contract；
# ADR-XPLAT-004 §4：套件不得依賴 harness 內臟）⇒ 兩側靠**同一組環境變數名**接線，而
# 「預設值必須相等」由 `tests/test_r82_quota_axis_and_shipped_defaults.py` 讀根層原始碼
# 比對（同 SCHEMA 那條既有鎖的體例）。這不是第二份常數表，是同一份宣告的鏡像，鏡子破了會紅。
#
# 🔴 兩份 `.env` 的關係（掌舵者點名要講清楚，判準守住）＝**繼承 ＋ 覆寫**：
#   os.environ  >  AutoClaude/.env  >  <repo 根>/.env  >  出廠預設
#   · 根 `.env` 是兩側共用的基底（harness 的 hook 也讀它）⇒ 只寫一次就兩邊一致；
#   · `AutoClaude/.env` 只在「引擎要與 harness 不同」時才寫，它贏。
# 為什麼是就地讀檔而不是引入 python-dotenv：本專案明文沒有 dotenv 載入器
# （`.env.example` 檔頭逐字），而 `.env` 裡放的是機密（MINIMAX_API_KEY／DB DSN）——
# 全域載入等於把機密灌進行程並隨 subprocess 繼承，那是另一個授權面的決定。
# 這裡只替**這一族鍵**查檔，白名單就是呼叫點寫死的那兩個名字。
# 行內註解一律剝掉：`.env.example` 的手寫版會帶 ` # 說明`，不剝就等於把說明餵給 float()。
_ENV_FILES = (Path(__file__).resolve().parents[2] / ".env",
              Path(__file__).resolve().parents[3] / ".env")

_LOG = logging.getLogger(__name__)
# 明示覆寫的標記。形狀刻意沿用 repo 既有的「行尾 `<name>-ok:` ＋ WHY」豁免慣例
# （PowerShell lint／毀滅性 git 守衛／git 路徑列舉那三支各有一個同族標記），**不發明第三種**；
# 理由必填。🔴 本段刻意**不逐字寫出**那三個標記字面：`tools/tests/test_platform_neutral_
# paths.py::TestGitPathEnumerationIsQuotepathSafe` 會掃全庫找它其中一個的字面，而「帶標記
# 卻不是 git 路徑列舉站點」判為 stale 並轉紅——本行第一版就這樣把一句舉例變成了一個**真的
# 豁免標記**（實測 rc=1）。這正是那道鎖該有的行為：豁免出口不得由散文順手鑄造出來。
_OVERRIDE_MARK = "override-ok:"


def _env_file_value(path: Path, name: str) -> str:
    # 回傳該檔中 `name=` 的**原始右手邊**（含行尾註解，讓上層看得到覆寫標記）；缺席回 ""。
    if not path.is_file():
        return ""
    return next((ln.split("=", 1)[1] for ln
                 in path.read_text(encoding="utf-8", errors="replace").splitlines()
                 if ln.split("=", 1)[0].strip() == name), "")


# 🔴 R86（掌舵者：「根 .env 與 AutoClaude/.env 是否違反 SSOT」）——**判定：不是 SSOT 違反**，
# 是 git system/global/local 那種三層繼承（根層＝兩側共用基底，AutoClaude 那份＝引擎專屬覆寫）。
# 合併成一份會拆掉一個合法需求（無人看管的引擎本來就可能該比互動式 harness 更保守），而且
# 這兩層是**被測試釘住的既有契約**（`test_the_env_file_takes_effect_and_autoclaude_wins_over_
# the_root` 直接 monkeypatch `_ENV_FILES`）⇒ 動它就是動契約。
# 🔴 真正的缺陷是**分歧靜默**：兩檔同名鍵值不同時，引擎用一個值、harness hook 用另一個值，
# 對**同一個額度池**做決策，而沒有任何東西會出聲——本 repo 最貴的教訓逐字是「fail-open 的
# 表徵與修好完全相同」。⇒ 治法不是禁止分歧（那會殺掉合法覆寫），是**讓分歧必須是明示的**。
# 🔴 為什麼偵測住在 `_quota_env` 裡、而不是另寫一支「掃兩份 .env 全部鍵」的比較器（這是
# 本輪的設計判定，不是偷懶）：`.env` 裡有機密（`MINIMAX_API_KEY`／DB DSN），而全鍵比較器
# 必須把機密的值讀進一條會 log 的路徑，再靠一份「像機密的鍵名」關鍵詞表去遮罩——那是啟發
# 式，會漏。本函式的呼叫點是**寫死的白名單**（只有 `AUTOSDD_QUOTA_*`），所以機密的值
# **結構上**到不了這裡，不需要遮罩也不可能外洩。誠實劃界：代價是非配額鍵的分歧不會被偵測。
def _quota_env(name: str, fallback: float) -> float:
    raw = os.environ.get(name, "").split("#")[0].strip()
    hits = [(p, v) for p in _ENV_FILES if (v := _env_file_value(p, name))]
    if len({v.split("#")[0].strip() for _, v in hits}) > 1 \
            and _OVERRIDE_MARK not in hits[0][1]:
        _LOG.warning(
            "[env 分歧] %s 在兩份 .env 值不同：%s ⇒ 引擎吃 %s、harness hook 吃 %s，"
            "對同一個額度池做不同決策。刻意的話在贏的那一行行尾加 `# %s <WHY>`。",
            name, [v.split("#")[0].strip() for _, v in hits],
            hits[0][0].as_posix(), hits[-1][0].as_posix(), _OVERRIDE_MARK)
    if not raw and hits:
        raw = hits[0][1].split("#")[0].strip()
    try:
        return min(100.0, max(0.0, float(raw)))
    except ValueError:
        return fallback   # 壞值不得變成故障源，也不得靜默放寬——退回出廠預設


class MinimaxConfig(BaseModel):
    api_key: str = ""
    # DEF-91-001（improving_91 W-91-3）：dataclass 預設須與 config.yaml 一致，否則 config.yaml
    # 缺 minimax 欄位時 fallback 到舊端點/舊 model（improving_90 commit 6daa540 只改 config.yaml）。
    base_url: str = "https://api.minimax.io/v1/text/chatcompletion_v2"
    model: str = "MiniMax-M2.7"
    timeout_seconds: int = 30
    enable_kernel_brain: bool = False
    # DEF-01-008：是否把 MinimaxBrainAdapter 注入 PlaybookKernel + SddGovernancePlugin。
    # 預設 False＝production 維持 brain=None（無 Minimax 逐步 correction、無 escalation 諮詢，
    # 零退化）。設 True 啟用後：kernel.decide_correction 生效（改寫 prompt + step mutation）
    # 且 Minimax API 故障將觸發 ESCALATION（見 docs/04_planning/AutoSDD_improving_03.md §2.1）
    # —— operator 須知悉行為差異。


class EmbedderConfig(BaseModel):
    """improving_91 W-91-1：embedder 非機密設定的 config.yaml 權威源（對齊 minimax chat 治理）。

    設定來源治理（延續 improving_90 commit 6daa540）：
      - base_url / model / dimension / timeout_seconds 為【非機密預設】，
        入庫共享、config.yaml 為權威源。
      - api_key 為【機密】，此處定義但預設留空（呼應 MinimaxConfig.api_key 慣例），實際值
        由環境變數 MINIMAX_API_KEY 提供、**絕不入庫 config.yaml**；本欄位之存在使
        config_resolver._PROTECTED_FIELDS 的 'embedder.api_key' RBAC 保護真正生效
        （DEF-91-003：補齊前 AppConfig 無此欄位，RBAC 在保護幽靈欄位、且 config.yaml 的
        embedder 區塊被 Pydantic extra=ignore 靜默丟棄）。
      - group_id（帳號識別）刻意不納入本 config，維持只走 env MINIMAX_GROUP_ID（與 chat
        config 無 group_id 一致，避免帳號綁定識別碼入庫）。
    優先序（adapter 端實作，見 minimax_embedder.py）：建構參數 > env > 本 config 兜底 > 硬編預設。
    """
    base_url: str = "https://api.minimax.io/v1/embeddings"
    model: str = "embo-01"
    dimension: int = 1024
    timeout_seconds: float = 30.0
    api_key: str = ""   # 機密：留空，由 env MINIMAX_API_KEY 提供，絕不入庫
    # bge-m3 本地 TEI（improving_92 W-92-1，方案 B 收尾）：TEI 為本地容器端點、全非機密，
    # 對應 .env.example 的 TEI_URL / TEI_MODEL_ID / TEI_EMBED_DIMENSIONS（後兩者先前 adapter
    # 從未讀取＝DEF-92-001/002）。無 api_key/帳號識別＝無機密、無 RBAC 需求（與 Minimax
    # embedder.api_key 不同，故 _PROTECTED_FIELDS 不為 bge-m3 新增任何欄位）。
    # 優先序（adapter 端實作，見 bgem3_local.py）：建構參數 > env > 本 config 兜底 > 硬編預設。
    bge_m3_url: str = "http://localhost:8080"
    bge_m3_model: str = "BAAI/bge-m3"
    bge_m3_dimension: int = 1024
    bge_m3_timeout_seconds: float = 30.0


class ClaudeConfig(BaseModel):
    command: str = "claude"
    # 🔴 R82（ACB-01，P0）：此欄預設值曾是 `["--yes"]`，而 `--yes` **從來就不是**
    # Claude Code CLI 的旗標——實測 `claude --yes mcp list` → rc=1、逐字
    # `error: unknown option '--yes'`（本機 claude 2.1.223）。兩條執行路徑
    # （pty_executor.py / prompt_dispatcher.py）都會把它原樣送出 ⇒ 出廠設定下
    # 每一個步驟都在第一秒失敗。它能活這麼久是因為「用 --version 驗過了」是假綠：
    # `claude --definitelynotaflag --version` 也回 rc=0（--version 短路旗標檢查）。
    # 預設改空清單＝不多送任何旗標。若需要非互動免權限提示，用實測存在的
    # `--permission-mode bypassPermissions` 或 `--dangerously-skip-permissions`
    # （見 scripts/ab_configs/*.yaml 既有用法）——那是安全決策，故不設為出廠預設。
    # 機械物：tests/test_claude_cli_flags.py（拿 `claude --help` 當 fixture 逐旗標比對）。
    extra_args: list[str] = Field(default_factory=list)
    continue_flag: str = "--continue"   # 傳遞給 claude 以維持對話脈絡
    encoding: str = "utf-8"
    # W-82-1 / DEF-81-001 PTY 支根因修復：PtyExecutor 以 `--output-format <fmt>` 啟動 claude -p。
    # 預設 "json"＝啟用真接線（從結構化 usage 推算真實 context% → emit TOKEN_PCT，使 token-guard
    # 在真跑可被觸發）。設 "" 則退回純文字舊行為（不加參數、不 parse，向後相容開關）。
    output_format: str = "json"


class LoopConfig(BaseModel):
    max_iterations: int = 20
    completion_pattern: str = r"執行完畢[,，]\s*報告如下"
    auth_patterns: list[str] = Field(
        default_factory=lambda: [
            r"Do you want to proceed\?",
            r"\(y/n\)",
            r"Press Enter to continue",
            r"Allow this action\?",
        ]
    )
    auth_response: str = "y\n"
    poll_interval_seconds: float = 0.2


class PlaybookConfig(BaseModel):
    step_timeout_seconds: int = 600        # 每個步驟的最大等待時間
    evaluator_timeout_seconds: int = 120   # evaluator_command 的最大執行時間
    global_goal_anchor_chars: int = Field(default=400, ge=100, le=1000)
    # Gap-013-H：/compact MEMORY ANCHOR 中 [GLOBAL_GOAL] 最大字元數（100~1000，預設 400）
    max_evolutions: int = Field(default=3, ge=1, le=10)
    # Gap-020：自動演化最大次數（1~10，預設 3）
    require_evolution_signoff: bool = False
    # DEF-13-004（L5 signoff 守界）：是否在自動重載演化版 Playbook 前要求人工 signoff。
    # 預設 False＝維持 Gap-012-D Level 5 自動重載（零退化）。設 True 後，每次演化重載前
    # 須經注入的 evolution_approver 核可（回傳 True）才放行；approver 缺失或拒絕 → fail-closed
    # 停機不重載並留審計痕（對齊 goal_decomposer signoff 硬閘 + MinimaxConfig.enable_kernel_brain
    # flag-gate 雙前例）。
    enable_rtm_feedback: bool = False
    # AutoSDD_improving_27 W1（A 軌 RTM 反饋迴圈）：是否在 ON_ESCALATION 演化提議時，
    # 讀回上次 RTM coverage 報告把 gap 摘要附 proposal.rationale 作**諮詢**輸入。
    # 預設 False＝EvolutionPlugin 行為與現況完全相同（零退化）。設 True 後僅增補
    # rationale 文字（不改 mutation 決策、不自動套用 RTM/SPEC）；演化仍走
    # require_evolution_signoff + max_evolutions 硬閘（對齊「RTM/SPEC-PATCH 絕不
    # 自動套用」紅線 + enable_kernel_brain flag-gate 前例）。
    goal_synthesis_enabled: bool = True
    # Gap-014：是否啟用 DONE 前的全局目標驗證（預設啟用）
    # R85：Brain 諮詢**失敗**時的姿態。False（預設，零行為變更）＝沿用 fail-open；
    # True＝改注入人工複核步驟，讓「問不到」不再與「已達成」同一個表徵。
    goal_synthesis_fail_closed: bool = False
    global_goal_brief_chars: int = Field(default=150, ge=50, le=500)
    # Gap-015：非首個步驟的精簡 global_goal 字元數（50~500，預設 150）
    conditional_evaluator_timeout_seconds: int = 5
    # Gap-038：CONDITIONAL 突變的 condition_evaluator 執行超時秒數（預設 5 秒）
    max_goto_per_step: int = 3
    # Gap-049：GOTO_STEP 每個目標步驟的最大跳轉次數（預設 3，可配置以支援複雜 TDD 場景）
    enable_translation_auto_propose: bool = True
    # AutoSDD_improving_60 W-60-4（A 軌 A→L5 轉譯策略元學習活體化）：是否於 POST_RUN
    # 自跨 session RTM coverage history 元學習出「轉譯改進候選」並自動提議（proposed）。
    # 預設 True＝**活體**（鏡像 B 軌 SLV 自動提議 default-ON；env
    # AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE=0/false/no/off opt-out 還原零退化）。
    # 🔴 紅線：proposals 純諮詢供人工 review，絕不自動改 SddToPlaybookAdapter 轉譯行為
    # （apply=人工 signoff 守界，對齊 RTM/SPEC-PATCH「絕不自動套用」）。非 SDD playbook
    # 全程 no-op。
    translation_max_proposals_per_run: int = Field(default=3, ge=0, le=20)
    # 每次 POST_RUN 最多新提議數（有界硬閘，0~20，預設 3；超限截斷不重試）。
    translation_min_weak_runs: int = Field(default=2, ge=1, le=20)
    # AutoSDD_improving_61（A→L5 加固）：第二信號 weak_regex 的提議門檻——同一 AT
    # 跨 session 轉譯為 weak_regex 達此 run 數即提議（與 min_failing_runs 獨立降噪，
    # 預設 2；1~20）。weak_regex＝Gherkin 無法編出強斷言而 fallback，反映轉譯保真度
    # 弱點，與「執行失敗」正交。提議仍恆 proposed（apply=人工 signoff，不變）。


class TokenGuardConfig(BaseModel):
    # Token / Context 用量保護設定。
    # （R86 等量減法：docstring → 註解、一字未刪；理由＝`check_loc_budget` 自己印的指引
    #  「docstring 行會被 count_loc 計入」，本輪 total 餘裕實測只有 12 行。R82 先例。）
    #
    # SD_06 W5-T5-12 加強 invariants：
    #   - halt_threshold_pct 必須 > compact_threshold_pct（既有 M-3/X-3）
    #   - resume_delay_minutes ≥ 0（避免負延遲）
    #   - max_auto_resumes ≥ 1（避免 0 次自動恢復產生 dead config）
    enabled: bool = True
    # 觸發 /compact 的 context 使用百分比門檻（應低於 halt_threshold_pct）
    compact_threshold_pct: float = Field(default=80.0, ge=0.0, le=100.0)
    # 觸發儲存檢查點並暫停的 context 使用百分比門檻
    halt_threshold_pct: float = Field(default=90.0, ge=0.0, le=100.0)
    # 🔴 R82（ACQ-01 / ADR-XPLAT-005 §2.4 載體二）：**帳號額度**水位的兩道門。
    # 與上面兩欄**絕對不共用**——上面兩欄的分母是 context window，這兩欄的分母是帳號方案。
    # 數字接近反而更危險：名字像有人守，其實守的是別的東西。
    # 🔴 R82（C3）：門檻改由**根層 ENV_SPEC 的同名環境變數**驅動（見檔頭 `_quota_env`）。
    # throttle 由 80 下修到 **70**＝根層階梯的 `converge`（「開始收斂」）：AutoClaude 這一側
    # 唯一的「可選支出」是 CORRECTION 重試，而每一次重試都是再打一次 claude ⇒ 在收斂帶就
    # 停掉它是嚴格更安全的方向（此處只准往下調，**不得**因為好看而往上放）。
    # halt 維持 95＝根層的 `halt`，那是安全線，出廠預設不放寬。
    # 刻意**不**映射 notice(50)／prepare(85)：AutoClaude 沒有扇出可降、也還沒有「提前準備
    # 下一次 reset」的動作 ⇒ 映射過來就是幽靈鍵。缺口誠實登記在 .env.example，不假裝有。
    quota_throttle_pct: float = Field(ge=0.0, le=100.0, default_factory=lambda: _quota_env(
        "AUTOSDD_QUOTA_CONVERGE_PCT", 70.0))
    quota_halt_pct: float = Field(ge=0.0, le=100.0, default_factory=lambda: _quota_env(
        "AUTOSDD_QUOTA_HALT_PCT", 95.0))
    # 🔴 R86：配速契約量不到（缺檔／過期／壞掉）時的併發上限。**絕不是「不設限」**——
    # 本 repo 已判過這條（根層 `AUTOSDD_QUOTA_DEGRADED_CAP` 就是它的既有實作）。
    # 上面兩欄是「%」故吃 `_quota_env` 的 0~100 夾；本欄是「個數」，夾在同一個上界只是恰好
    # 無害（根層 `max_fanout` 出廠 16 ≪ 100）；下界由 Field(ge=1) 守——0 會讓引擎在量不到
    # 時一個並發單位都不准派＝死鎖，而那不是保守，是壞掉。
    quota_degraded_cap: int = Field(ge=1, le=100, default_factory=lambda: int(_quota_env(
        "AUTOSDD_QUOTA_DEGRADED_CAP", float(DEGRADED_CAP))))
    # 儲存檢查點後等待多少分鐘再自動繼續（0 = 立即繼續）
    # 🔴 R82：**額度**路徑不讀這一欄（改讀觀測到的 resets_at，見 core/services/auto_resume.py）；
    # context 路徑原樣保留——實測額度視窗 min 0.5 分／max 253 分，沒有一段等於固定 30 分。
    resume_delay_minutes: int = Field(default=30, ge=0, le=1440)
    # True = 等待後自動繼續；False = 儲存檢查點後退出，讓人類決定何時重啟
    auto_resume: bool = True
    # 單次 playbook 執行中最多允許多少次自動恢復（防止無限迴圈）
    max_auto_resumes: int = Field(default=10, ge=1, le=100)
    # 從 Claude Code 輸出中偵測 context 使用率的 regex patterns
    # T7（SD_04 §3 / M-4）：補強 Claude Code 實際輸出格式涵蓋率
    #   - 原 4 個：%context、context%、N/M tokens、[CONTEXT_USAGE: N%]
    #   - 新 3 個：Context window N / M tokens、[STATS: usage N%]、Token usage: N tokens / max M
    context_patterns: list[str] = Field(
        default_factory=lambda: [
            r"(\d+(?:\.\d+)?)\s*%\s*(?:context|token)",
            r"(?:context|token)\w*[\s:]+(\d+(?:\.\d+)?)\s*%",
            r"(\d+)\s*/\s*(\d+)\s*tokens?",
            r"\[CONTEXT_USAGE:\s*(\d+(?:\.\d+)?)%\]",
            # 新增：Claude Code "Context window: N / M tokens" 格式
            r"Context window:\s*(\d+)\s*/\s*(\d+)\s*tokens",
            # 新增：[STATS: usage N%] 簡短標記
            r"\[STATS:\s*usage\s*(\d+(?:\.\d+)?)\s*%\]",
            # 新增：Token usage: N tokens / max M
            r"Token usage:\s*(\d+)\s*tokens\s*/\s*max\s*(\d+)",
        ]
    )

    @model_validator(mode="after")
    def halt_greater_than_compact(self) -> TokenGuardConfig:
        """M-3/X-3 防呆：halt 門檻必須高於 compact 門檻。"""
        if self.halt_threshold_pct <= self.compact_threshold_pct:
            raise ValueError(
                f"halt_threshold_pct({self.halt_threshold_pct}%) 必須 > "
                f"compact_threshold_pct({self.compact_threshold_pct}%)"
            )
        # R82（ACQ-01 / ADR M10）：額度那一軸照抄同一條不變量（quota_halt > quota_throttle）。
        if self.quota_halt_pct <= self.quota_throttle_pct:
            raise ValueError(
                f"quota_halt_pct({self.quota_halt_pct}%) 必須 > "
                f"quota_throttle_pct({self.quota_throttle_pct}%)"
            )
        return self

    @field_validator("context_patterns")
    @classmethod
    def validate_regex(cls, v: list[str]) -> list[str]:
        """M-3 防呆：驗證每個 context_patterns 項目都是合法 regex。

        SA-4 修正：加上 re.IGNORECASE 旗標以與 token_tracker.build_patterns()
        的執行時編譯語意一致（避免「validator 通過但執行時行為不同」陷阱）。
        """
        for pattern in v:
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"無效 regex pattern '{pattern}': {exc}") from exc
        return v


class AlertLadderConfig(BaseModel):
    """F-B1 / ADR-AGT-004：漸進式告警階梯（WARNING→HINT→ESCALATE）。

    enabled 預設 on（2026-06-13 SCG-6 人工 waiver：koalawu 拍板提前轉正，免 7 天
    soak；deviation 紀錄見 AutoClaude_Improving_012.md §5 Phase 2 與 Phase3 NextAction）。
    可於 config 設 enabled=False 還原為與既有行為 byte-level 一致之控制流。
    """
    enabled: bool = True
    # F-B2：同 error signature 無改善連續 N 次即提前升級（穿透剩餘階梯）
    no_improve_escalate_threshold: int = Field(default=2, ge=1, le=5)


class NotificationConfig(BaseModel):
    # 🔴 R82（ACC-01）：預設由 True 改 False——桌面彈窗是 NotificationPlugin 在 POST_RUN 發的，
    # 而 plyer 的 Windows 後端把 balloon_tip 丟進一個**非 daemon** 執行緒並 sleep(timeout)，
    # 於是彈窗在「跑完之後」才冒出來、還把行程多吊住 duration 秒。使用者要的是不要彈。
    # 反向證據：本 repo 自己的測試有 6 處逐行寫 `cfg.notification.enabled = False`
    # 並註明「測試不應觸發真實桌面通知」——出廠預設與所有消費端的期望相反。
    enabled: bool = False
    webhook_url: str | None = None
    # 桌面通知泡泡停留秒數。plyer 內部會 sleep 這麼久，直接決定行程被吊住多久（原硬編 10）。
    duration_seconds: int = Field(default=3, ge=1, le=60)

    @model_validator(mode="after")
    def apply_env_switch(self) -> NotificationConfig:
        # opt-in / opt-out 開關（見 .env.example）。刻意雙向：想臨時開來看一次通知的人
        # 不必改入庫的 config.yaml，而 CI／無人看管跑批也能明文關掉。
        raw = os.environ.get("AUTOCLAUDE_DESKTOP_NOTIFY", "").strip().lower()
        if raw in ("1", "true", "yes", "on"):
            self.enabled = True
        elif raw in ("0", "false", "no", "off"):
            self.enabled = False
        return self


class ToolInvocationConfig(BaseModel):
    """F-A2 / ADR-AGT-001：工具自主使用安全閘。

    預設 deny（凍結計畫 §4 風險緩解）：enabled=False 全拒；即使 True，allowlist
    為空仍全拒。allowlist 為 domain（web_search/http_request 比對 target 之 host）
    或通道名（send_message）。flag-off 時不發出任何外部 I/O，零行為變更。
    """
    enabled: bool = False
    allowlist: list[str] = Field(default_factory=list)


class StorageConfig(BaseModel):
    """Phase 6：State / Playbook backend 三段開關（SD_Improving_02.md v1.1 §2.8）。

    模式語義：
      - yaml_only（預設）：所有 Playbook 從 .yaml 載入；checkpoints 寫入 file backend。
                          無 PostgreSQL 依賴，零部署成本，與 v1.x 相容。
      - both：              Playbook 雙源讀（yaml 優先，DB 兜底）；checkpoints 雙寫（File + PG），
                          讀取以 File 為主、PG 為災難回復來源。適合 PG 上線首兩週的灰度驗證。
      - db_only：          Playbook 與 checkpoints 完全使用 PG backend；yaml 僅供匯入。
                          需 PostgreSQL 運行 + AUTOCLAUDE_DB_DSN 環境變數。
    """
    mode: Literal["yaml_only", "both", "db_only"] = "yaml_only"
    # PostgreSQL DSN（asyncpg 格式）；db_only / both 模式必填，可被 AUTOCLAUDE_DB_DSN 覆寫
    db_dsn: str | None = None
    # both 模式下，dual-write 失敗時是否阻斷主寫（False = 僅紀錄 warning，不影響使用者）
    dual_write_strict: bool = False
    # both 模式下，dual-read 不一致時的解決策略（"yaml_wins" / "db_wins" / "fail_loud"）
    dual_read_resolution: Literal["yaml_wins", "db_wins", "fail_loud"] = "yaml_wins"

    @model_validator(mode="after")
    def db_dsn_required_for_pg(self) -> StorageConfig:
        """X-3 防呆：db_only / both 模式必須提供 db_dsn 或環境變數。"""
        if self.mode in ("both", "db_only"):
            has_dsn = bool(self.db_dsn)
            has_env = bool(
                os.environ.get("AUTOCLAUDE_DB_DSN") or os.environ.get("AUTOCLAUDE_PG_DSN")
            )
            if not has_dsn and not has_env:
                raise ValueError(
                    f"storage.mode='{self.mode}' 需要 db_dsn 或環境變數 "
                    "AUTOCLAUDE_DB_DSN / AUTOCLAUDE_PG_DSN"
                )
        return self


class ExecutorConfig(BaseModel):
    """improving_68 W-68-3：執行器後端切換（PtyExecutor / SdkExecutorAdapter 並存）。

    backend="pty"（預設）→ 既有 PtyExecutor，零行為變更；現有測試與 production
    完全不受影響。backend="sdk" 為 opt-in，啟用以 Claude Agent SDK（JSON-over-stdio）
    驅動 Claude Code（需 `pip install 'autoclaude[sdk]'`）。

    permission_mode：傳給 SDK 的權限模式（spike 證實安全值為 "default"，非 acceptEdits）。
    model：SDK 模型覆寫（None＝SDK 預設）。
    act-first 門檻（halt_pct / max_tokens / autocompact_threshold）由 adapter 於執行期
    從 SDK get_context_usage() 即時取得，無需在此設定（見 W-68-1 verify_act_first_ordering）。
    """
    backend: Literal["pty", "sdk"] = "pty"
    permission_mode: Literal[
        "default", "acceptEdits", "plan", "bypassPermissions", "dontAsk", "auto"
    ] = "default"
    model: str | None = None
    # improving_69 W-69-2：SDK 工具 allowlist（can_use_tool production 接線）。
    # None（預設）→ 不注入 predicate，交由 permission_mode 守門（零行為變更，對齊 improving_68）。
    # list → 嚴格 allowlist：僅清單內工具名放行，其餘 deny-by-default（predicate 例外由
    # adapter._wrap_can_use_tool fail-closed deny）；空 list = 全 deny（最嚴格）。
    sdk_tool_allowlist: list[str] | None = None


class AppConfig(BaseModel):
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    minimax: MinimaxConfig = Field(default_factory=MinimaxConfig)
    embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)
    loop: LoopConfig = Field(default_factory=LoopConfig)
    playbook: PlaybookConfig = Field(default_factory=PlaybookConfig)
    token_guard: TokenGuardConfig = Field(default_factory=TokenGuardConfig)
    alert_ladder: AlertLadderConfig = Field(default_factory=AlertLadderConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    tool_invocation: ToolInvocationConfig = Field(default_factory=ToolInvocationConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    executor: ExecutorConfig = Field(default_factory=ExecutorConfig)
    log_dir: str = "logs"
    backup_dir: str = "backups"
    scripts_dir: str = "scripts"
    checkpoint_dir: str = "checkpoints"
    # 工作流程自動偵測的搜尋路徑清單（依序嘗試，找到即回傳）
    # 空列表 → 僅以 CWD 作為最後備援
    workflow_search_paths: list[str] = Field(default_factory=list)
    # F-C1 / ADR-AGT-003 L3：啟動時 seed 至 IPreferenceStore（global scope）
    # 寫入為冪等 last-wins；config 為使用者期望值的 SSOT 來源之一
    preferences: dict[str, str] = Field(default_factory=dict)


def load_config(path: str = "config.yaml") -> AppConfig:
    p = Path(path)
    if not p.exists():
        return AppConfig()
    with p.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return AppConfig.model_validate(raw)
