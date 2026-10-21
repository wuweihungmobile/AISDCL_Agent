"""
ESCALATION 或強制中斷時儲存的完整診斷快照。
提供 to_markdown() 讓人類快速接手診斷。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# DEF-101（Mac/Windows 相容性）：step_id 為 PlaybookTask 上完全自由格式、無驗證
# 的欄位（playbook 作者手寫 YAML 可能寫成 "Step 1: Setup" 這種含冒號的自然字串），
# 若未淨化直接組進檔名，在 Windows 上會因禁用字元 / 保留裝置名導致 open() 拋出
# 未捕捉的 OSError。本檔刻意重用 utils/logger.py 既有的 `_sanitize_log_filename()`
# （RawStreamLogger 已用它解決同類問題），而非另寫一份相似邏輯——避免重蹈
# DEF-101-219／DEF-101-295 同一淨化規則被多處獨立實作、其一漏改即復發的根因。
from ..utils.logger import _sanitize_log_filename, write_text_with_fallback


# ESCALATION「重啟指令」的單一出處：`EscalationDump.generate_handover_checklist()` 與落盤的
# 「## 繼續執行指令」（`plugins/checkpoint/_escalation.py` 經本函式組 `checkpoint_resume_hint`）
# 共用，避免同一份 dump 出現兩種寫法（R56 DEF-101-432 第 5 處就是兩處各組一份而漏改）。
# 🔴 Kernel（core/）是純 DAG、不持有 playbook 路徑（持有路徑的是 core/services/auto_resume.py），
# ON_ESCALATION_DUMP_REQUEST 的 payload 因此不帶它，Kernel 路徑的 dump 拿到 `playbook_path==""`。
# 明確決策：缺資訊時印「未記錄」與帶佔位符的註解形態（不可被誤執行），不猜、也不印出
# `autoclaude ""` 這種看似可跑的空參數指令；讓 Kernel 簽名改帶路徑是另一個架構變更，非本函式職責。
# 措辭只講事實：重跑會不會續跑取決於「先前是否已有 checkpoint」（ESCALATION 本身不存 checkpoint；
# 只有 TOKEN_HALT／中斷／演化重載會存），沒有就從第一步重來。
def resume_command(playbook_path: str) -> str:
    if playbook_path:
        return f'autoclaude "{playbook_path}"  # 有 checkpoint 才續跑，否則從頭；--fresh 強制從頭'
    return ("# python -m autoclaude <playbook.yaml> --config <config.yaml>\n"
            "# Kernel 路徑由呼叫端持有 playbook 路徑，請以原指令重啟")


@dataclass
class EscalationDump:
    """ESCALATION 或強制中斷時儲存的完整診斷快照。"""
    playbook_path: str  # "" ＝未記錄（Kernel 路徑不持有它；見 resume_command）
    step_id: str
    step_name: str
    total_attempts: int
    failure_chain: list[dict]  # dict keys 見 to_markdown() 消費處
    final_eval_output: str
    is_stuck: bool
    is_diverging: bool
    suspect_test_file: bool
    is_oscillating: bool = False              # 振盪模式（ABAB 交替）診斷旗標
    is_worsening: bool = False                # Gap-008-A：失敗數遞增（越改越壞）
    suspect_assertion_mismatch: bool = False  # Gap-008-C：測試期望值疑似寫錯
    saved_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    human_hint: str = ""
    last_log_path: str = ""  # "" ＝未取得（to_markdown 印「未取得」，不猜檔名）
    checkpoint_resume_hint: str = ""
    # AutoSDD_improving_14 A 軌（W-14-2）：meta⁸ 互遞迴拓樸審批儀表板（已過 SDD 端 PY-2
    # 拓樸防偽 + AutoClaude 端 fail-closed 稽核的 Markdown）。空字串＝非 SDD recursion
    # signoff / 無儀表板（預設，零退化）；有值時 to_markdown() 嵌入供舵手於指揮官端審批。
    topology_dashboard: str = ""

    def generate_handover_checklist(self) -> list[str]:
        """
        Gap-010-D：根據 ESCALATION 原因，自動生成可執行的接手行動清單。
        每個項目含可直接在終端執行的 shell 命令。
        """
        # R56 修正（DEF-101-432）：本清單由 to_markdown() 包進「## 接手行動清單（可直接
        # 執行）」的 bash 圍欄、再由 save() 落盤成 escalation dump，人類會原樣複製到終端，
        # 故它是「跨平台顯示文字」而非內部字串。原內容多處 POSIX-only，在 Windows 11
        # （cmd.exe / PowerShell 5.1）必失敗，各自的 Windows 等效寫法如下：
        #   * python -m py_compile tests/test_*.py —— 萬用字元展開是 POSIX 殼的職責，
        #     cmd.exe / PowerShell 都不對外部程式引數做 glob，py_compile 會收到字面字串
        #     'tests/test_*.py' 而報 No such file or directory。
        #     Windows 等效：python -m compileall -q tests/
        #   * cat '<log>' | tail -50 —— cmd.exe 無 cat/tail；PowerShell 的 cat 是
        #     Get-Content 別名但無 tail，且管線為物件流；單引號在 cmd.exe 非引號字元。
        #     Windows 等效：Get-Content -Tail 50 '<log>'
        #   * grep -rn 'assert.*==' tests/ | head -20 —— cmd.exe / PowerShell 皆無
        #     grep 與 head。R56 訂正：`Select-String -Path tests\*` **沒有遞迴語意**
        #     （-Path 萬用字元只匹配該層），而 grep -r 是遞迴 —— 本 repo 實測命中
        #     'assert.*==' 的檔案：非遞迴 tests\*.py = 36 個、遞迴 = 237 個（漏 85%），
        #     照著執行卻以為「已檢查完」比沒有提示更危險，故等效寫法必須自帶遞迴：
        #     Windows 等效：Get-ChildItem -Recurse -Filter *.py tests
        #                   | Select-String -Pattern 'assert.*==' | Select-Object -First 20
        #     行尾提示受 ruff line-length=100 限制，改用別名縮寫 `gci -r tests|sls
        #     assert.*==`（省略 -Filter *.py 反而更貼近 grep -r 對 tests/ 下所有檔案
        #     遞迴搜尋的行為；沒有 -First 20，輸出較長但不會漏檔）。已於 PowerShell
        #     7.6.3 實測：bareword pattern 解析正確、`-r` 綁定到 -Recurse 而非
        #     -ReadOnly、管線中的目錄項目被安靜略過不報錯。原生 Windows PowerShell
        #     5.1 未實機驗證（本輪無 Windows 機器），語意依 cmdlet 契約推定相同。
        # 另 playbook_path 補上雙引號：Windows 使用者路徑常含空白（C:\Users\John Smith\
        # My Projects\pb.yaml），未加引號會被切成多個引數；雙引號在 sh 與 cmd.exe 皆為
        # 引號字元，是唯一兩平台通用的引用方式（單引號不可用）。
        # 🔴 本輪選擇與其正規出口（勿讀成「永久修法規範」）：本檔屬 data tier 150/150
        # 零餘裕（ADR-SD07-001），新增 if/else 分支或新清單元素都會直接破 per-file 硬閘，
        # 故 R56 先採「同一邏輯行行尾併入 Windows 提示」的零邏輯行淨增手法完成
        # DEF-101-432 的資訊補全，完整等效指令記於本註解區塊。🔴 括號裡原本寫的理由
        # 「count_loc() 只跳過空行與行首 #」自 ADR-XPLAT-013 起**已不成立**（否決權複審
        # M3 訂正）：現行計價只算**斷言行**，docstring／裸字串／整行 # 一律免費，所以
        # 「把說明搬成註解」省不到預算，R56 那套手法的成本理由已失效——真正省的只有
        # 「少寫斷言」。行尾註解不增斷言行這一半仍然成立。
        # 未來若要改為依 sys.platform 產生平台原生指令（架構正解，可去掉人工翻譯步驟），
        # 應走 ADR-SD07-001 §5.2/§6.2 的 per-file override 核准程序（`.loc-budget.toml`
        # 條目 + 書面理由 + Architect/SD 雙簽），而非繼續以行尾註解規避 tier 上限。
        actions: list[str] = []
        look_back = min(self.total_attempts, 5)

        actions += [
            "# === AutoClaude 接手行動清單 ===",
            "# 1. 確認 Claude Code 最近的修改",
            f"git log --oneline -{look_back}",
            f"git diff HEAD~{look_back} HEAD",
        ]

        if self.suspect_test_file:
            actions += [
                "",
                "# 2. 測試檔語法驗證（suspect_test_file=True）",
                "python -m py_compile tests/test_*.py  # Windows: python -m compileall -q tests/",
                "pytest --collect-only  # 確認測試可被收集",
            ]

        if self.is_stuck:
            actions += [
                "",
                "# 3. 卡死診斷（is_stuck=True，相同錯誤反覆出現）",
                (f"cat '{self.last_log_path}' | tail -50  # 看 log, Windows: Get-Content -Tail 50"
                 if self.last_log_path else "# 最後 log 未取得（見上方「最後執行 Log」節）"),
                "# 手動執行 evaluator_command 確認根本原因",
            ]

        if self.suspect_assertion_mismatch:
            actions += [
                "",
                "# 4. 測試期望值驗證（suspect_assertion_mismatch=True）",
                r"grep -rn 'assert.*==' tests/ | head -20  # Windows: gci -r tests|sls assert.*==",
                "# 請人工確認：assert 的期望值是否符合業務邏輯",
            ]

        # 🔴 OBS-SI-192：本節只給「唯讀診斷＋保全」，不得再建議毀滅性 git。原文曾列裸
        # `git stash` 與 `git checkout HEAD -- .`——前者是 monorepo 根 CLAUDE.md 鐵律五點名
        # 的共用工作樹事故源，後者會不可逆清掉全部未提交內容；兩者在本 repo 都由 PreToolUse
        # 守衛阻斷，照抄只會被擋或毀資料。`git stash create` 只建 commit 物件、不動工作樹，
        # 是鐵律五指定的保全手法。回歸鎖＝tests/test_gap010.py（全旗標掃毀滅形態）。
        if self.is_worsening:
            actions += [
                "",
                "# 5. 失敗數遞增診斷（is_worsening=True，修改越多失敗越多）",
                "git status --short  # 先看工作樹現況（唯讀）",
                "git diff --stat  # 累積修改的檔案與行數（唯讀）",
                "git stash create  # 只印 sha，不動工作樹；再 git tag <輪次>-wip-preserved <sha>",
            ]

        if self.is_oscillating:
            actions += [
                "",
                "# 6. 振盪模式診斷（is_oscillating=True，兩個錯誤交替出現）",
                "# 修改 A 導致錯誤 B，修改 B 導致錯誤 A",
                "# 需要找到根本的設計衝突，而非逐一修補",
            ]

        actions += [
            "",
            "# 7. 手動修正後，恢復執行",
            *resume_command(self.playbook_path).splitlines(),
            "# 若步驟已手動完成：重跑不會自動跳過它，需自行調整 playbook 或 checkpoint",
        ]

        return actions

    def to_markdown(self) -> str:
        lines = [
            "# AutoClaude Escalation Dump",
            f"**步驟**: {self.step_id} — {self.step_name}",
            f"**時間**: {self.saved_at}",
            f"**重試次數**: {self.total_attempts}",
            f"**Playbook**: {self.playbook_path or '（Kernel 路徑未記錄 playbook 路徑）'}",
            "",
            "## 失敗鏈",
        ]
        for rec in self.failure_chain:
            corr_prompt = rec.get("correction_prompt_sent", "")
            corr_preview = f"\n  修正指令（前 200 字）: {corr_prompt[:200]}" if corr_prompt else ""
            error_class = rec.get("error_class", "unknown")
            lines.append(
                f"- Attempt {rec['attempt']} (exit={rec.get('exit_code', '?')}, "
                f"error_class={error_class}): "
                f"`{rec['error_signature'][:100]}`"
                f"\n  Minimax 決策: {rec['minimax_reasoning']}"
                f"{corr_preview}"
            )
        yes = "✅ 是"
        no = "❌ 否"
        lines += [
            "",
            "## 最後評估輸出",
            "```",
            self.final_eval_output[:3000],
            "```",
            "",
            "## 自動診斷",
            f"- 錯誤卡死（特徵相同）: {yes if self.is_stuck else no}",
            f"- 錯誤發散（越改越壞，exit_code）: {yes if self.is_diverging else no}",
            f"- 失敗數惡化（越改越多）: {yes if self.is_worsening else no}",
            f"- 振盪錯誤（ABAB 交替）: {yes if self.is_oscillating else no}",
            f"- 疑似測試檔本身有語法/Import 錯誤: {yes if self.suspect_test_file else no}",
            f"- 疑似測試期望值寫錯: {yes if self.suspect_assertion_mismatch else no}",
            "",
            "## 建議行動",
            self.human_hint or "請檢查上方失敗鏈，優先確認測試檔是否有獨立錯誤。",
        ]
        if self.topology_dashboard:
            lines += ["", "## 🧭 meta⁸ 互遞迴拓樸審批儀表板（指揮官端可審批）",
                      "> SDD 渲染、已過拓樸防偽 + fail-closed 稽核；🔴=耗 fuel、⛔=強制打斷。",
                      "", self.topology_dashboard]
        lines += ["", "## 最後執行 Log",
                  f"`{self.last_log_path}`" if self.last_log_path else "未取得（未提供 log 目錄）"]
        if self.checkpoint_resume_hint:
            lines += ["", "## 繼續執行指令", "```", self.checkpoint_resume_hint, "```"]
        # Gap-010-D：自動生成可執行的接手行動清單
        lines += [
            "",
            "## 接手行動清單（可直接執行）",
            "```bash",
            *self.generate_handover_checklist(),
            "```",
        ]
        return "\n".join(lines)

    def save(self, dump_dir: str) -> Path:
        """將快照儲存為 Markdown 檔案，回傳實際路徑。"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = _sanitize_log_filename(f"escalation_{self.step_id}_{ts}.md")
        path = Path(dump_dir) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        # `_sanitize_log_filename()` 只淨化禁用字元，不截斷長度——超長 step_id（無
        # 驗證的自由格式欄位）仍可能讓檔名超出檔案系統上限；共用 helper 失敗時會
        # fallback 寫入系統暫存目錄，避免 ESCALATION 診斷快照（失敗復盤關鍵材料）
        # 因此完全遺失。
        return write_text_with_fallback(
            path, self.to_markdown(), fallback_prefix="escalation_fallback"
        )
