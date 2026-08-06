# 地端 act runner 映像 —— catthehacker/ubuntu:act-latest ＋ GitHub 真 runner 自帶、
# 但該映像沒有的工具（pwsh／gh）。**唯一消費者＝根層 `.actrc` 的 `-P` 映射。**
#
# ── 為何需要這一層（R77 實測到的破口）─────────────────────────────────────────
# `act -n`（dry-run）對 root-infra-ci.yml 回 rc=0，但**真跑**到第 3 個 step
# （`pwsh 語法解析 + UTF-8 BOM 守門`）就 `exitcode 127`：該 step 的 run: 第一個字就是
# `pwsh`，而 catthehacker 的**中型**映像（act-latest，2.32GB）刻意不含 pwsh；GitHub 的
# ubuntu-latest runner 自帶。於是「act 盤點」只能誠實說「🟡 可解析」，說不出「✅ 可達」。
#
# ── 為何是「自建薄映像」而不是另外兩條路 ──────────────────────────────────────
#   (a) 改 workflow（在 root-infra-ci.yml 加一個 `install pwsh` step）：會**污染真 CI 的
#       定義**——雲端 runner 本來就有 pwsh，為了地端讓雲端每次 push 多裝一次 ≈ 3 分鐘，
#       而且那個 step 在雲端永遠是多餘的。地端的不足不該由雲端埋單。
#   (b) 換 `catthehacker/ubuntu:full-latest`：那顆映像 >60GB 未壓縮量級，且它裝的東西遠
#       多於本 repo 需要的兩支，pull 成本與磁碟成本都不成比例。
#   ⇒ 本檔＝(a)(b) 之外的最小增量：base 不動、只補**雲端有而中型映像沒有**的那幾支。
#
# ── 🔴 等價度是設計目標，不是效能取捨（沿用 `.actrc` 檔頭同一條承諾）──────────
# `.actrc` 已明文寫下「不應為了本機效能犧牲『地端 act ＝ 雲端 CI』的平價承諾」
# （見該檔 `--container-architecture linux/amd64` 那段：Apple Silicon 上寧可走 QEMU 慢，
# 也不改 arm64）。本檔是**同一條承諾往同方向再走一步**——版本號刻意釘成雲端 runner
# **當下真正在跑的那一版**，不是「隨便一個夠新的」：
#
#   PowerShell 7.6.3 ／ GitHub CLI 2.96.0
#
# 取值方式（不是抄來的、也不是猜的；2026-08-07 實查 actions/runner-images 權威源）：
#   curl -fsSL https://raw.githubusercontent.com/actions/runner-images/main/images/ubuntu/Ubuntu2404-Readme.md \
#     | grep -E 'PowerShell [0-9]|GitHub CLI [0-9]'
# 上列輸出逐字為 `- GitHub CLI 2.96.0` 與 `- PowerShell 7.6.3`。GitHub 每隔幾週會更新
# runner 映像 ⇒ **這兩個數字是量測值不是常數**：發現地端與雲端行為分歧時，第一件事是
# 重跑上面那行、比對本檔的 ARG，而不是猜。改 ARG 後必須 `--build-image --no-cache` 重建。
#
# ── 刻意**不**裝 ruff（這一格是誠實劃界，不是遺漏）────────────────────────────
# `run_act_core.RUNNER_IMAGE_MISSING_TOOLS` 把 ruff 與 pwsh／gh 並列為「雲端有、act 映像
# 沒有」——實查上面那份 runner-images 清單，**ruff 不在其中**（同一份 grep 對 `Ruff` 零
# 命中）。root-infra-ci.yml 第 16 道自己會 `pip install 'ruff==0.15.21'`。若在本映像預裝
# ruff，反而會**遮蔽**「那一行 pip install 壞掉」這個雲端會紅、地端卻綠的差異
# ⇒ 預裝它是**降低**等價度。故本映像只補「雲端真的預裝、地端沒有」的那兩支。
#
# ── 用法 ──────────────────────────────────────────────────────────────────────
#   python AutoClaude/tools/run_act_core.py --build-image            # 建（可重跑）
#   python AutoClaude/tools/run_act_core.py --build-image --no-cache # 改 ARG 後重建
# 建出來的 tag 由 `run_act_core.ACT_IMAGE` 單一定義，`.actrc` 的 `-P` 必須與它逐字相同
# （機械鎖＝tools/tests/test_act_local_runner_image.py）。

FROM catthehacker/ubuntu:act-latest

# 見檔頭：這兩個值＝雲端 ubuntu-24.04 runner 當下的實際版本，不是「最新版」。
ARG POWERSHELL_VERSION=7.6.3
ARG GH_VERSION=2.96.0

# 單一 RUN 層：中間產物（tarball／解壓目錄）不落進映像層。
# `dpkg --print-architecture` 而非寫死 amd64：`.actrc` 今天釘 linux/amd64，但把架構寫死在
# 這裡會讓「哪天改了 .actrc」變成靜默壞掉，而不是這裡當場 fail-loud（鐵律三：跨平台判準
# 必須自問「在另一個平台是什麼值」）。未知架構一律 exit 1，不猜。
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) ps_arch=x64;   gh_arch=amd64 ;; \
      arm64) ps_arch=arm64; gh_arch=arm64 ;; \
      *) echo "unsupported dpkg architecture: ${arch}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/powershell.tar.gz \
      "https://github.com/PowerShell/PowerShell/releases/download/v${POWERSHELL_VERSION}/powershell-${POWERSHELL_VERSION}-linux-${ps_arch}.tar.gz"; \
    mkdir -p /opt/microsoft/powershell/7; \
    tar -xzf /tmp/powershell.tar.gz -C /opt/microsoft/powershell/7; \
    chmod +x /opt/microsoft/powershell/7/pwsh; \
    ln -sf /opt/microsoft/powershell/7/pwsh /usr/bin/pwsh; \
    rm -f /tmp/powershell.tar.gz; \
    curl -fsSL -o /tmp/gh.tar.gz \
      "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${gh_arch}.tar.gz"; \
    tar -xzf /tmp/gh.tar.gz -C /tmp; \
    install -m 0755 "/tmp/gh_${GH_VERSION}_linux_${gh_arch}/bin/gh" /usr/bin/gh; \
    rm -rf /tmp/gh.tar.gz "/tmp/gh_${GH_VERSION}_linux_${gh_arch}"; \
    pwsh --version; \
    gh --version

# 建置期自驗（build 失敗＝映像不會產生，勝過「建出一顆缺工具的映像」再讓 job 跑到一半
# 才 127）。`-NoProfile` 對齊 workflow 內的呼叫形態。
RUN pwsh -NoProfile -Command '[void][System.Management.Automation.Language.Parser]::ParseInput("Write-Host ok", [ref]$null, [ref]$null); exit 0'

# base 的 ENTRYPOINT/CMD 刻意不覆寫：act 自己會接管（`.actrc` 另以 `--container-options
# --init` 補 PID 1 reaper，見該檔）。
