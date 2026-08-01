#!/usr/bin/env bash
# AISDLC 專案初始化腳本 (Mac/Linux)
# 版本: v3.3-SDD
# 最後更新: 2026-04-15
# 用途: 從 GitHub 下載並初始化 AISDLC / AISDLC-SDD 框架到專案目錄
# 支援: 公開倉庫 (HTTPS) / 私有倉庫 (SSH/PAT)
# 新增: SDD 模式（--sdd）、本地模式偵測

set -e  # 遇到錯誤立即停止

# ===== 配置 =====
GITHUB_REPO="wuweihungmobile/AISDLC"
GITHUB_URL_HTTPS="https://github.com/${GITHUB_REPO}.git"
GITHUB_URL_SSH="git@github.com:${GITHUB_REPO}.git"
DEFAULT_VERSION="0.09"
DEFAULT_SDD_VERSION="0.01"
USE_SSH=false
PAT_TOKEN=""
LOCAL_SOURCE=""  # 本地框架路徑（自動偵測或手動指定）
USE_SDD=false    # SDD 模式（使用 AISDLC_SDD_v{version} 目錄）

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ===== 輔助函數 =====

show_banner() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║       AISDLC 專案初始化工具 v3.2                      ║${NC}"
    echo -e "${CYAN}║       AI-assisted Software Development Lifecycle       ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

show_usage() {
    echo -e "${BLUE}使用方式:${NC}"
    echo -e "  ./init_project.sh [選項]"
    echo ""
    echo -e "${BLUE}選項:${NC}"
    echo -e "  -v, --version VERSION   指定版本 (預設: ${DEFAULT_VERSION}；SDD 預設: ${DEFAULT_SDD_VERSION})"
    echo -e "  -d, --dir DIRECTORY     指定安裝目錄 (預設: 當前目錄)"
    echo -e "  -s, --ssh               使用 SSH 連線 (私有倉庫需要)"
    echo -e "  -t, --token TOKEN       使用 PAT Token 連線 (私有倉庫，無 SSH 時使用)"
    echo -e "  -l, --local PATH        指定本地框架路徑 (跳過下載)"
    echo -e "  --sdd                   使用 SDD 模式（Spec-First Design，安裝 AISDLC_SDD_v{version}）"
    echo -e "  -h, --help              顯示此說明"
    echo ""
    echo -e "${BLUE}🌐 遠端安裝 (從 GitHub 直接執行):${NC}"
    echo ""
    echo -e "  ${GREEN}# 公開倉庫 - 一行安裝${NC}"
    echo -e "  curl -fsSL https://raw.githubusercontent.com/${GITHUB_REPO}/main/AISDLC_v${DEFAULT_VERSION}/tools/init_project.sh | bash"
    echo ""
    echo -e "  ${GREEN}# 公開倉庫 - 指定版本和目錄${NC}"
    echo -e "  curl -fsSL https://raw.githubusercontent.com/${GITHUB_REPO}/main/AISDLC_v${DEFAULT_VERSION}/tools/init_project.sh | bash -s -- -v 0.09 -d ./my-project"
    echo ""
    echo -e "  ${GREEN}# 私有倉庫 - 需先下載後執行${NC}"
    echo -e "  curl -fsSL https://raw.githubusercontent.com/${GITHUB_REPO}/main/AISDLC_v${DEFAULT_VERSION}/tools/init_project.sh -o init.sh && bash init.sh --ssh"
    echo ""
    echo -e "${BLUE}📁 本地安裝:${NC}"
    echo ""
    echo -e "  # 公開倉庫 - 安裝預設版本到當前目錄"
    echo -e "  ./init_project.sh"
    echo ""
    echo -e "  # 私有倉庫 - 使用 SSH 連線"
    echo -e "  ./init_project.sh --ssh"
    echo ""
    echo -e "  # 安裝指定版本到指定目錄"
    echo -e "  ./init_project.sh -v 0.09 -d ~/my-project --ssh"
    echo ""
    echo -e "${YELLOW}💡 提示:${NC}"
    echo -e "  • 公開倉庫: 直接使用 HTTPS (預設)"
    echo -e "  • 私有倉庫: 使用 --ssh 並確保已設定 SSH Key"
    echo ""
}

check_dependencies() {
    echo -e "${YELLOW}⏳ 檢查必要工具...${NC}"

    local missing_deps=()

    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    fi

    if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
        missing_deps+=("curl 或 wget")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo -e "${RED}❌ 缺少必要工具: ${missing_deps[*]}${NC}"
        echo -e "${YELLOW}   請先安裝缺少的工具後再執行此腳本${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ 所有必要工具已安裝${NC}"
    echo ""
}

detect_local_framework() {
    # 自動偵測：腳本所在目錄的上層是否就是框架根目錄
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local parent_dir
    parent_dir="$(dirname "${script_dir}")"
    local grandparent_dir
    grandparent_dir="$(dirname "${parent_dir}")"

    # 檢查 1: 腳本位於 AISDLC_vX.XX/tools/ 內，且上上層包含 AISDLC_vX.XX/
    if [ -d "${parent_dir}/agent" ] && [ -d "${parent_dir}/docs_template" ] && [ -f "${parent_dir}/AISDLC_INIT.md" ]; then
        # 上層就是版本目錄，上上層就是 repo 根目錄
        LOCAL_SOURCE="${grandparent_dir}"
        echo -e "${GREEN}🔍 偵測到本地框架: ${LOCAL_SOURCE}${NC}"
        return 0
    fi

    return 1
}

download_aisdlc() {
    local version=$1
    local target_dir=$2
    # SDD 模式使用 AISDLC_SDD_v{version}，一般模式使用 AISDLC_v{version}
    local aisdlc_dir
    if [ "$USE_SDD" = true ]; then
        aisdlc_dir="AISDLC_SDD_v${version}"
    else
        aisdlc_dir="AISDLC_v${version}"
    fi
    local source_dir=""

    # === 本地模式：優先使用本地框架 ===
    if [ -n "$LOCAL_SOURCE" ]; then
        source_dir="${LOCAL_SOURCE}"
        echo -e "${GREEN}📁 使用本地框架: ${source_dir}${NC}"

        if [ ! -d "${source_dir}/${aisdlc_dir}" ]; then
            echo -e "${RED}❌ 本地路徑找不到版本 v${version}${NC}"
            echo -e "${YELLOW}   可用版本:${NC}"
            # SDD 模式目錄命名為 AISDLC_SDD_v*，非 SDD 模式為 AISDLC_v*——固定用後者
            # 過濾會使 --sdd 模式印出空清單（R16 相容性掃描）
            if [ "$USE_SDD" = true ]; then
                ls -d "${source_dir}"/AISDLC_SDD_v* 2>/dev/null | xargs -n1 basename | sed 's/AISDLC_SDD_v/   - v/'
            else
                ls -d "${source_dir}"/AISDLC_v* 2>/dev/null | xargs -n1 basename | sed 's/AISDLC_v/   - v/'
            fi
            exit 1
        fi

        echo -e "${GREEN}✅ 偵測到本地 AISDLC v${version}，跳過網路下載${NC}"
    else
        # === 遠端模式：從 GitHub 下載 ===
        # mktemp 帶模板（R11）：repo 對 BSD mktemp 是否需模板存在兩套假設（實測現代 macOS 皆可，統一帶模板為最保守跨平台寫法）
        # 宣告與賦值分離（R15 SCAN-A-1）：`local x=$(cmd)` 整行 rc 恆為 local 的 0，
        # set -e 下 mktemp 失敗被遮蔽 → temp_dir 空字串 → 後續路徑退化成 /repo 誤導；
        # 分離後賦值失敗即觸發 set -e 停機（bash 3.2 相容寫法）。
        local temp_dir
        temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/aisdlc_init.XXXXXX")"
        source_dir="${temp_dir}/repo"

        # 選擇 URL
        local git_url
        if [ "$USE_SSH" = true ]; then
            git_url="${GITHUB_URL_SSH}"
            echo -e "${YELLOW}⏳ 從 GitHub 下載 AISDLC v${version} (SSH)...${NC}"
        elif [ -n "$PAT_TOKEN" ]; then
            git_url="https://${PAT_TOKEN}@github.com/${GITHUB_REPO}.git"
            echo -e "${YELLOW}⏳ 從 GitHub 下載 AISDLC v${version} (HTTPS + PAT)...${NC}"
        else
            git_url="${GITHUB_URL_HTTPS}"
            echo -e "${YELLOW}⏳ 從 GitHub 下載 AISDLC v${version} (HTTPS)...${NC}"
        fi
        echo -e "${BLUE}   倉庫: ${GITHUB_REPO}${NC}"

        # Clone with depth 1 for speed
        if ! git clone --depth 1 --quiet "${git_url}" "${source_dir}" 2>&1; then
            echo -e "${RED}❌ 無法連線到 GitHub 倉庫${NC}"
            if [ "$USE_SSH" = false ] && [ -z "$PAT_TOKEN" ]; then
                echo -e "${YELLOW}   若為私有倉庫，請使用 --ssh 或 --token YOUR_PAT 選項${NC}"
            elif [ "$USE_SSH" = true ]; then
                echo -e "${YELLOW}   請確認 SSH Key 已正確設定${NC}"
            else
                echo -e "${YELLOW}   請確認 PAT Token 是否有效且具有 repo 權限${NC}"
            fi
            rm -rf "${temp_dir}"
            exit 1
        fi

        # Check if version directory exists
        if [ ! -d "${source_dir}/${aisdlc_dir}" ]; then
            echo -e "${RED}❌ 找不到版本 v${version}${NC}"
            echo -e "${YELLOW}   可用版本:${NC}"
            # SDD 模式目錄命名為 AISDLC_SDD_v*，非 SDD 模式為 AISDLC_v*——固定用後者
            # 過濾會使 --sdd 模式印出空清單（R16 相容性掃描）
            if [ "$USE_SDD" = true ]; then
                ls -d "${source_dir}"/AISDLC_SDD_v* 2>/dev/null | xargs -n1 basename | sed 's/AISDLC_SDD_v/   - v/'
            else
                ls -d "${source_dir}"/AISDLC_v* 2>/dev/null | xargs -n1 basename | sed 's/AISDLC_v/   - v/'
            fi
            rm -rf "${temp_dir}"
            exit 1
        fi

        echo -e "${GREEN}✅ 下載完成${NC}"
    fi

    # Copy to target directory
    echo -e "${YELLOW}⏳ 複製 AISDLC v${version} 到專案目錄...${NC}"

    # Create target directory if not exists
    mkdir -p "${target_dir}"

    # Copy AISDLC version directory
    cp -r "${source_dir}/${aisdlc_dir}" "${target_dir}/"

    # Copy PROJECT_CLAUDE_Template.md as project CLAUDE.md
    local claude_template="${source_dir}/${aisdlc_dir}/tools/PROJECT_CLAUDE_Template.md"
    if [ -f "${claude_template}" ]; then
        cp "${claude_template}" "${target_dir}/CLAUDE.md"
        echo -e "${GREEN}   ✅ 產生 CLAUDE.md (from PROJECT_CLAUDE_Template.md)${NC}"
    elif [ -f "${source_dir}/CLAUDE.md" ]; then
        cp "${source_dir}/CLAUDE.md" "${target_dir}/"
        echo -e "${YELLOW}   ⚠️  複製 CLAUDE.md (fallback: root CLAUDE.md)${NC}"
    fi

    # Copy .claude/skills/ to project root (Claude Code Skills discovery)
    if [ -d "${target_dir}/${aisdlc_dir}/.claude/skills" ]; then
        mkdir -p "${target_dir}/.claude/skills"
        cp -r "${target_dir}/${aisdlc_dir}/.claude/skills/"* "${target_dir}/.claude/skills/"
        echo -e "${GREEN}   ✅ 複製 .claude/skills/ (Claude Code Skills)${NC}"
    fi

    echo -e "${GREEN}✅ 複製完成${NC}"

    # Cleanup temp directory if used
    if [ -n "${temp_dir:-}" ]; then
        rm -rf "${temp_dir}"
    fi

    echo ""
}

create_docs_directories() {
    local base_dir=$1

    echo -e "${YELLOW}⏳ 建立 docs/ 標準子目錄...${NC}"

    # 定義標準子目錄（開發專注版）
    local docs_dirs=(
        "docs/01_requirements"
        "docs/02_architecture"
        "docs/03_testing"
        "docs/04_planning"
        "docs/05_development"
        "docs/06_quality"
        "docs/07_design"
        "docs/08_deployment"
    )

    local created_count=0
    local existing_count=0
    local target_path="${base_dir}"

    for dir in "${docs_dirs[@]}"; do
        local full_path="${target_path}/${dir}"
        if [ ! -d "${full_path}" ]; then
            mkdir -p "${full_path}"
            echo -e "${GREEN}   ✅ 建立 ${dir}/${NC}"
            created_count=$((created_count + 1))
        else
            echo -e "${BLUE}   ℹ️  ${dir}/ 已存在${NC}"
            existing_count=$((existing_count + 1))
        fi
    done

    echo ""
    echo -e "${GREEN}📊 統計結果:${NC}"
    echo -e "   - 已存在: ${existing_count} 個目錄"
    echo -e "   - 新建立: ${created_count} 個目錄"
    echo ""
}

show_completion_message() {
    local target_dir=$1
    local version=$2
    local aisdlc_dir
    if [ "$USE_SDD" = true ]; then
        aisdlc_dir="AISDLC_SDD_v${version}"
    else
        aisdlc_dir="AISDLC_v${version}"
    fi

    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              ✅ 初始化完成！                           ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}📋 已完成的工作:${NC}"
    if [ -n "$LOCAL_SOURCE" ]; then
        echo -e "   ✅ 從本地複製 AISDLC v${version}"
    else
        echo -e "   ✅ 從 GitHub 下載 AISDLC v${version}"
    fi
    echo -e "   ✅ 複製框架到 ${target_dir}/${aisdlc_dir}/"
    echo -e "   ✅ 建立 docs/ 標準子目錄"
    if [ -f "${target_dir}/CLAUDE.md" ]; then
        echo -e "   ✅ 複製 CLAUDE.md 設定檔"
    fi
    if [ -d "${target_dir}/.claude/skills" ]; then
        echo -e "   ✅ 部署 .claude/skills/ (Claude Code Skills)"
    fi
    echo ""
    echo -e "${YELLOW}📝 下一步:${NC}"
    echo -e "   1. 使用 Claude Code 開啟目錄: ${target_dir}"
    if [ "$USE_SDD" = true ]; then
        echo -e "   2. 閱讀 ${aisdlc_dir}/AISDLC_SDD_INIT.md 了解 SDD 框架使用"
        echo -e "   3. 選擇場景：greenfield / brownfield / refactoring / documentation"
        echo -e "   4. 確認 SCG 閘門：參考 ${aisdlc_dir}/workflow/sdd-spec-first-gate/"
        echo -e "   5. 開始規格設計（PRD 先行）：docs/01_requirements/"
    else
        echo -e "   2. 閱讀 ${aisdlc_dir}/AISDLC_INIT.md 了解框架使用"
        echo -e "   3. PRD 寫入 docs/01_requirements/"
        echo -e "   4. SRD 寫入 docs/02_architecture/"
        echo -e "   5. 參考: ${aisdlc_dir}/guides/user/onboarding/QUICK_START_GUIDE.md"
    fi
    echo ""
    echo -e "${CYAN}🔗 專案結構:${NC}"
    echo -e "   ${target_dir}/"
    echo -e "   ├── ${aisdlc_dir}/          # AISDLC 框架"
    echo -e "   │   ├── agent/              # AI Agent 定義"
    echo -e "   │   ├── workflow/           # 工作流程"
    echo -e "   │   ├── docs_template/      # 文件模板"
    echo -e "   │   ├── guides/             # 參考指南"
    echo -e "   │   └── AISDLC_INIT.md      # 框架入口"
    echo -e "   ├── docs/                   # 📄 您的專案文件放這裡"
    echo -e "   │   ├── 01_requirements/"
    echo -e "   │   ├── 02_architecture/"
    echo -e "   │   └── ..."
    # R68（Scan-H 判準③：不得在使用者面輸出寫死可由程式現查的數字）：原本寫死
    # 「(33個)」，實測部署後為 42（權威源 AISDLC_SDD/FRAMEWORK_STATUS.md 的
    # `.claude/skills` 列），且 .ps1 對應物不印計數＝單邊 stale。改為對已部署目錄
    # 現算。只數子目錄（一個 skill＝一個含 SKILL.md 的目錄）——不可用 `ls | wc -l`，
    # 該目錄另含 README.md 等非 skill 檔（正是原缺陷報告誤算成 45 的來源）。
    # `| tr -d ' '` 吸收 BSD wc 的前導空白（同本樹 verify_traceability.sh:77 手法）。
    local skill_count
    skill_count="$(find "${target_dir}/.claude/skills" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')"
    echo -e "   ├── .claude/skills/         # Claude Code Skills (${skill_count}個)"
    echo -e "   └── CLAUDE.md               # Claude Code 設定"
    echo ""
}

# ===== 主程式 =====

main() {
    local version="${DEFAULT_VERSION}"
    local target_dir="."

    # 解析參數
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--version)
                version="$2"
                shift 2
                ;;
            -d|--dir)
                target_dir="$2"
                shift 2
                ;;
            -s|--ssh)
                USE_SSH=true
                shift
                ;;
            -t|--token)
                PAT_TOKEN="$2"
                shift 2
                ;;
            -l|--local)
                LOCAL_SOURCE="$2"
                shift 2
                ;;
            --sdd)
                USE_SDD=true
                # SDD 模式下預設版本改為 0.01
                if [ "${version}" = "${DEFAULT_VERSION}" ]; then
                    version="${DEFAULT_SDD_VERSION}"
                fi
                shift
                ;;
            -h|--help)
                show_banner
                show_usage
                exit 0
                ;;
            *)
                echo -e "${RED}未知選項: $1${NC}"
                show_usage
                exit 1
                ;;
        esac
    done

    # 轉換為絕對路徑（先建立目錄確保 cd 能成功解析）
    mkdir -p "${target_dir}"
    target_dir=$(cd "${target_dir}" && pwd)

    show_banner

    # 自動偵測本地框架（如果未手動指定 --local）
    if [ -z "$LOCAL_SOURCE" ]; then
        detect_local_framework || true
    fi

    echo -e "${BLUE}📦 安裝配置:${NC}"
    echo -e "   版本: v${version}"
    echo -e "   目錄: ${target_dir}"
    if [ -n "$LOCAL_SOURCE" ]; then
        echo -e "   來源: 本地 (${LOCAL_SOURCE})"
    elif [ "$USE_SSH" = true ]; then
        echo -e "   來源: GitHub (SSH)"
    elif [ -n "$PAT_TOKEN" ]; then
        echo -e "   來源: GitHub (HTTPS + PAT)"
    else
        echo -e "   來源: GitHub (HTTPS)"
    fi
    echo ""

    check_dependencies
    download_aisdlc "${version}" "${target_dir}"
    create_docs_directories "${target_dir}"
    show_completion_message "${target_dir}" "${version}"
}

# 執行主程式
main "$@"
