# 已驗證的 Claude Code CLI 版本清單（PRD §6.2 R-6.2-2 第 2 點）。
#
# 🔴 為什麼是這裡而不是本機狀態檔：本機檔不隨 clone 走 ⇒ 換一台機器就變成「全部未知」
#    或「全部已驗證」，兩種都錯。本檔是 git-tracked 的 .py，隨 clone 走、也隨
#    `pip install` 進套件（放 .json 得再動打包設定，而漏掉打包的失效形態是「裝好之後
#    清單不存在」＝全部未知，一樣靜默）。機械物＝G6（`git ls-files` 命中本檔路徑）。
#
# 🔴 為什麼每一版必須帶「這一版核實過什麼」而不能只有版號：附錄 B 已把「核實來源是實作
#    內部字串，不是官方文件承諾的公開介面」寫成前提 ⇒ 只有版號的清單在下一次介面變動時
#    給不出任何判斷依據。
#
# 🔴 誠實劃界：`verified` 欄位列的是**本 repo 真的跑過並記錄下來的那幾件事**，不是
#    「這一版的介面全部相容」。沒有人核實過整個 CLI 介面，本檔不得被讀成那個意思。
from __future__ import annotations

VERIFIED_CLI_VERSIONS: dict[str, dict] = {
    "2.1.223": {
        "verified": [
            "`--yes` 不是合法旗標：實測 `claude --yes mcp list` → rc=1、逐字 "
            "`error: unknown option '--yes'`（立案＝R82 ACB-01，見 utils/config.py "
            "ClaudeConfig.extra_args 的註解）",
            "`--version` 會短路旗標檢查：`claude --definitelynotaflag --version` 亦回 "
            "rc=0 ⇒ 不得拿它當旗標存在性的憑證",
        ],
        "source": "autoclaude/utils/config.py（R82 ACB-01 逐字紀錄）",
    },
    "2.1.233": {
        "verified": [
            "`claude --version` 可讀且格式為 `<semver> (Claude Code)`：本輪實測逐字 "
            "`2.1.233 (Claude Code)`",
        ],
        "source": "R100 P2-C 落地當回合實測（macOS/darwin）",
    },
    # 🔴 improving_113 的誠實劃界（刻意寫在 `verified` 之外）：`--max-turns` **不在**本版
    #    `claude --help`（`claude --help | grep -c -- '--max-turns'` 逐字輸出 `0`）。PRD §4.5.4 的
    #    喚醒指令範例含該旗標並標 [需核對] ⇒ 本版**沒有**核實它存在；`verified` 只列核實成立的事，
    #    不得為了「看起來完整」補一條它（鎖：tests/test_r100_boot_self_check.py 的
    #    test_improving_113_the_verified_text_never_claims_the_flag_the_cli_help_lacks）。
    #    另：本版沒有實跑任何會燒 token 的呼叫（`claude -p`），所以各旗標的執行期語意同樣未核實，
    #    下面只證明版本字串、help 文字、`--permission-mode` 的選項值驗證。
    "2.1.295": {
        "verified": [
            "`claude --version` 輸出逐字 `2.1.295 (Claude Code)`（rc=0）：格式仍是 "
            "`<semver> (Claude Code)`，`read_cli_version` 取第一個 token 即得 `2.1.295`",
            "`claude --help` 文字內可見 `--settings <file-or-json>`、`--add-dir <directories...>`、"
            "`--allowedTools, --allowed-tools <tools...>`、`-r, --resume [value]`、"
            "`--model <model>`、`--permission-mode <mode>`（只證明 help 有這些字面，"
            "不證明各旗標的語意與先前版本相容）",
            "`--permission-mode default` 被接受：實測 `claude --permission-mode default --version` "
            "→ rc=0、輸出 `2.1.295 (Claude Code)`；選項值驗證先於 `--version` 短路，故此實測有"
            "鑑別力：非法值 `definitelynotamode` → rc=1、逐字 `error: option '--permission-mode "
            "<mode>' argument 'definitelynotamode' is invalid. Allowed choices are acceptEdits, "
            "auto, bypassPermissions, manual, dontAsk, plan.`（注意 `default` 不在該 choices 清單"
            "內：屬『被接受但 help 未列出』，不得當作官方承諾的公開值）",
        ],
        "source": "improving_113 W3 落地當回合零 token 實測（macOS/darwin；`claude --version`／"
                  "`claude --help`／`claude --permission-mode <值> --version`）",
    },
}
