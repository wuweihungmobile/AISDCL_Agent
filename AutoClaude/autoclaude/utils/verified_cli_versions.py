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
}
