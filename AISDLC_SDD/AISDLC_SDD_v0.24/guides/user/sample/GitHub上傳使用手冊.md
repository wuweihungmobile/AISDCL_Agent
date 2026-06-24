# GitHub 上傳使用手冊

> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---
# GitHub Upload Manual

> **文檔類型**: 使用者指南 | User Guide
> **適用對象**: AISDLC 框架使用者、開發團隊
> **版本**: v1.0
> **最後更新**: 2025-01-10

---

## 📋 目錄 (Table of Contents)

1. [前置準備](#前置準備)
2. [完整步驟指南](#完整步驟指南)
3. [完整指令總覽](#完整指令總覽)
4. [後續操作（選用）](#後續操作選用)
5. [常見問題排解](#常見問題排解)
6. [注意事項](#注意事項)

---

## 🎯 文檔目的

本手冊提供完整的 **AISDLC 框架上傳到 GitHub** 的操作指南，包含：

- ✅ 詳細的步驟說明
- ✅ 完整的 Git 指令
- ✅ 常見問題解決方案
- ✅ 最佳實踐建議

**目標讀者**: 需要將 AISDLC 專案上傳到 GitHub 的開發者

---

## 前置準備

### 環境檢查

在開始之前，請確認以下環境：

```bash
# 1. 確認當前工作目錄
pwd
# 預期結果: /path/to/AISDLC_ALL

# 2. 檢查 Git 是否已安裝
git --version
# 預期結果: git version 2.x.x

# 3. 檢查 Git 使用者設定
git config --global user.name
git config --global user.email
# 如果沒有設定，請執行步驟 1 的設定

# 4. 檢查是否已初始化 Git repository
ls -la .git
# 如果顯示 "No such file or directory"，表示尚未初始化
```

### 需要準備的資訊

- ✅ GitHub 帳號（如果沒有，請先註冊：https://github.com/signup）
- ✅ Git 使用者名稱和 Email
- ✅ Repository 名稱（建議：`AISDLC` 或 `AISDLC_Framework`）
- ✅ Repository 描述（選用）

---

## 完整步驟指南

### 步驟 1：配置 Git 使用者資訊

**目的**: 設定提交者的身份資訊

```bash
# 設定你的 Git 使用者名稱
git config --global user.name "wuweihungmobile"

# 設定你的 Git Email（建議使用 GitHub 帳號的 Email）
git config --global user.email "wuweihung.mobile@gmail.com"

# 驗證設定
git config --global user.name
git config --global user.email
```

**說明**:
- 這是首次使用 Git 的必要設定
- 使用者名稱和 Email 會記錄在每次提交中
- 建議使用與 GitHub 帳號相同的 Email

**預期結果**:
```
你的名字
your.email@example.com
```

---

### 步驟 2：初始化本地 Git Repository

**目的**: 將專案目錄轉換為 Git repository

```bash
# 進入專案目錄
cd /path/to/AISDLC_ALL

# 初始化 Git repository
git init

# 驗證初始化成功
ls -la .git
```

**說明**:
- `git init` 會在當前目錄創建 `.git` 子目錄
- `.git` 目錄包含所有版本控制資訊
- 這個操作只需要執行一次

**預期結果**:
```
Initialized empty Git repository in /path/to/AISDLC_ALL/.git/
```

---

### 步驟 3：創建 .gitignore 檔案

**目的**: 排除不需要版控的檔案

```bash
# 創建 .gitignore 檔案
cat > .gitignore << 'EOF'
# macOS
.DS_Store
.AppleDouble
.LSOverride

# Thumbnails
._*

# Files that might appear in the root of a volume
.DocumentRevisions-V100
.fseventsd
.Spotlight-V100
.TemporaryItems
.Trashes
.VolumeIcon.icns
.com.apple.timemachine.donotpresent

# Directories potentially created on remote AFP share
.AppleDB
.AppleDesktop
Network Trash Folder
Temporary Items
.apdisk

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Logs
*.log
logs/
build/logs/*.log

# Temporary files
*.tmp
*.temp
tmp/
temp/

# Environment variables
.env
.env.local
.env.*.local

# OS generated files
Thumbs.db
ehthumbs.db
Desktop.ini
EOF

# 查看 .gitignore 內容
cat .gitignore
```

**說明**:
- `.gitignore` 定義了哪些檔案不應該被加入版控
- 排除系統檔案、IDE 設定檔、日誌檔等
- 可以根據專案需求自行調整

**預期結果**:
顯示 `.gitignore` 檔案的完整內容

---

### 步驟 4：將檔案加入 Git 暫存區

**目的**: 選擇要提交的檔案

```bash
# 查看目前狀態
git status

# 將所有檔案加入暫存區
git add .

# 再次查看狀態（確認哪些檔案被加入）
git status
```

**說明**:
- `git add .` 會將所有未被 `.gitignore` 排除的檔案加入暫存區
- 暫存區（Staging Area）是提交前的準備區
- 可以使用 `git add <file>` 選擇性地加入特定檔案

**預期結果**:
```
Changes to be committed:
  (use "git rm --cached <file>..." to unstage)
        new file:   AISDLC_SDD_v0.01/...
        new file:   CLAUDE.md
        ...
```

---

### 步驟 5：創建第一個 Commit

**目的**: 記錄專案的初始狀態

```bash
# 創建初始提交
git commit -m "Initial commit: AISDLC Framework v0.01

- Complete AISDLC framework structure
- 7 Core Agents (Chinese version)
- 14 Specialized Agents
- 9 Development Scenarios
- Complete workflow definitions
- Document templates and guides
- Integration guide and SOP

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# 查看提交歷史
git log --oneline
```

**說明**:
- Commit 是 Git 的基本單位，記錄一次完整的變更
- Commit message 應該清楚描述變更內容
- 使用多行 commit message 提供更詳細的說明

**預期結果**:
```
[main (root-commit) abc1234] Initial commit: AISDLC Framework v0.01
 XXX files changed, XXXX insertions(+)
 create mode 100644 AISDLC_SDD_v0.01/...
 ...
```

---

### 步驟 6：在 GitHub 上創建 Repository

**目的**: 在 GitHub 建立遠端儲存庫

#### 手動操作步驟

1. **前往 GitHub 網站**
   - 打開瀏覽器，前往 [https://github.com](https://github.com)
   - 登入你的 GitHub 帳號

2. **創建新 Repository**
   - 點擊右上角的 `+` 按鈕
   - 選擇 `New repository`

3. **填寫 Repository 資訊**

   | 欄位 | 填寫內容 | 說明 |
   |------|---------|------|
   | **Repository name** | `AISDLC` 或 `AISDLC_Framework` | 必填，Repository 名稱 |
   | **Description** | `AI-assisted Software Development Lifecycle Framework - 結構化 AI 輔助軟體開發生命週期框架` | 選填，Repository 描述 |
   | **Public / Private** | `Public` 或 `Private` | Public = 公開，Private = 私有 |
   | **Initialize this repository with** | ⚠️ **全部不勾選** | 重要！避免衝突 |

4. **重要：不要勾選以下選項**
   - ❌ **不要**勾選 `Add a README file`
   - ❌ **不要**勾選 `Add .gitignore`
   - ❌ **不要**選擇 `Choose a license`

5. **創建 Repository**
   - 點擊 `Create repository` 按鈕

**為什麼不勾選這些選項？**

因為你的本地已經有完整的專案內容和 `.gitignore`，如果 GitHub 自動創建這些檔案，會造成衝突。

**預期結果**:

創建完成後，你會看到一個頁面，顯示 Repository URL，類似：
```
https://github.com/wuweihungmobile/AISDLC.git
```

**複製這個 URL，下一步驟會用到！**

---

### 步驟 7：連接本地 Repository 到 GitHub

**目的**: 建立本地和遠端的連接

```bash
# 添加 GitHub remote
git remote add origin https://github.com/wuweihungmobile/AISDLC.git

# 驗證 remote 設定
git remote -v
```

**說明**:
- `origin` 是遠端 repository 的預設名稱
- 這個指令建立了本地和 GitHub 的連接
- 已經使用你的 GitHub 使用者名稱：`wuweihungmobile`

**預期結果**:
```
origin  https://github.com/wuweihungmobile/AISDLC.git (fetch)
origin  https://github.com/wuweihungmobile/AISDLC.git (push)
```

---

### 步驟 8：推送到 GitHub

**目的**: 將本地 commit 上傳到 GitHub

```bash
# 推送到 GitHub（第一次推送需要使用 -u 參數）
git push -u origin main
```

**說明**:
- `push` 是將本地 commit 上傳到遠端的操作
- `-u origin main` 設定預設的上游分支
- 第一次推送可能需要身份驗證

---

#### 可能遇到的問題

##### 問題 1：分支名稱不是 main

**錯誤訊息**:
```
error: src refspec main does not match any
```

**解決方案**:
```bash
# 檢查當前分支名稱
git branch

# 如果是 master，重新命名為 main
git branch -M main

# 然後推送
git push -u origin main
```

---

##### 問題 2：需要驗證身份

**錯誤訊息**:
```
remote: Support for password authentication was removed
```

**說明**: GitHub 已停用密碼驗證，你需要使用 **Personal Access Token (PAT)** 或 **SSH Key**

#### 方案 A：使用 Personal Access Token（建議新手）

**步驟 1：獲取 Personal Access Token**

1. 前往 GitHub → **Settings**
2. 點擊左側的 **Developer settings**
3. 點擊 **Personal access tokens** → **Tokens (classic)**
4. 點擊 **Generate new token (classic)**
5. 填寫以下資訊：
   - **Note**: `AISDLC Upload Token`（自訂名稱）
   - **Expiration**: 選擇有效期限（建議 90 days）
   - **Select scopes**: 勾選 `repo`（完整的 repository 權限）
6. 點擊 **Generate token**
7. **⚠️ 重要**：複製 Token（只會顯示一次，請妥善保管）

**步驟 2：使用 Token 推送**

```bash
# 當提示輸入密碼時，貼上你的 Token
git push -u origin main

# 或者在 URL 中包含 Token（僅限測試，不安全）
git remote set-url origin https://你的Token@github.com/wuweihungmobile/AISDLC.git
git push -u origin main
```

#### 方案 B：使用 SSH（建議進階使用者）

**步驟 1：生成 SSH Key**

```bash
# 生成 SSH Key（如果還沒有）
ssh-keygen -t ed25519 -C "your.email@example.com"

# 按 Enter 使用預設路徑
# 可以設定 passphrase（建議）或直接按 Enter 跳過

# 查看公鑰
cat ~/.ssh/id_ed25519.pub
```

**步驟 2：添加 SSH Key 到 GitHub**

1. 複製 `cat ~/.ssh/id_ed25519.pub` 輸出的完整內容
2. 前往 GitHub → **Settings** → **SSH and GPG keys**
3. 點擊 **New SSH key**
4. 填寫：
   - **Title**: `AISDLC Laptop`（自訂名稱）
   - **Key**: 貼上公鑰內容
5. 點擊 **Add SSH key**

**步驟 3：修改 remote URL 為 SSH**

```bash
# 修改 remote URL 為 SSH 格式
git remote set-url origin git@github.com:wuweihungmobile/AISDLC.git

# 驗證設定
git remote -v

# 推送
git push -u origin main
```

**預期結果**:
```
Enumerating objects: XXX, done.
Counting objects: 100% (XXX/XXX), done.
...
To https://github.com/wuweihungmobile/AISDLC.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

---

##### 問題 3：推送資料量太大（HTTP 400 錯誤）

**錯誤訊息**:
```
error: RPC failed; HTTP 400 curl 22 The requested URL returned error: 400
send-pack: unexpected disconnect while reading sideband packet
Writing objects: 100% (1097/1097), 10.93 MiB | 6.22 MiB/s, done.
fatal: the remote end hung up unexpectedly
```

**原因分析**:
- AISDLC 專案包含大量文檔（1000+ 個檔案，10+ MB）
- 超過了 GitHub 預設的 HTTP 緩衝區限制（通常是 1-2 MB）
- HTTPS 協定對大型推送的支援較弱

**解決方案（按推薦順序）**:

#### 方案 A：增加 HTTP 緩衝區大小（最簡單）

```bash
# 增加 HTTP 緩衝區到 500MB
git config --global http.postBuffer 524288000

# 再次推送
git push -u origin main
```

**說明**:
- `http.postBuffer` 設定 Git HTTP 傳輸的最大緩衝區大小
- `524288000` = 500 MB（500 × 1024 × 1024 bytes）
- 這個設定會套用到所有 Git repository

**驗證設定**:
```bash
# 查看當前設定
git config --global http.postBuffer
```

---

#### 方案 B：使用 SSH 替代 HTTPS（最穩定，強烈建議）

SSH 協定比 HTTPS 更適合大型推送，而且之後不需要每次輸入密碼/Token。

**步驟 1：檢查是否已有 SSH Key**

```bash
# 查看現有的 SSH Key
ls -la ~/.ssh/id_*.pub

# 如果看到 id_ed25519.pub 或 id_rsa.pub，表示已有 SSH Key
# 可以直接跳到步驟 2
```

**步驟 2：生成 SSH Key（如果沒有）**

```bash
# 生成新的 SSH Key
ssh-keygen -t ed25519 -C "wuweihung.mobile@gmail.com"

# 提示問題的回答：
# 1. "Enter file in which to save the key" → 按 Enter（使用預設路徑）
# 2. "Enter passphrase" → 輸入密碼保護（建議），或按 Enter 跳過
# 3. "Enter same passphrase again" → 再次輸入密碼，或按 Enter
```

**步驟 3：查看並複製公鑰**

```bash
# 查看公鑰
cat ~/.ssh/id_ed25519.pub

# 輸出類似：
# ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG... wuweihung.mobile@gmail.com
```

**複製整行內容（從 `ssh-ed25519` 到 Email 結尾）**

**步驟 4：將公鑰添加到 GitHub**

1. 前往 GitHub → **Settings** → **SSH and GPG keys**
   - 直接連結：https://github.com/settings/keys
2. 點擊 **New SSH key** 按鈕
3. 填寫：
   - **Title**: `AISDLC MacBook`（自訂名稱，用於識別這台電腦）
   - **Key**: 貼上剛才複製的公鑰內容
4. 點擊 **Add SSH key**
5. 如果提示輸入密碼，輸入你的 GitHub 密碼確認

**步驟 5：測試 SSH 連接**

```bash
# 測試 SSH 連接
ssh -T git@github.com

# 第一次連接會詢問：
# "Are you sure you want to continue connecting (yes/no/[fingerprint])?"
# 輸入 yes 並按 Enter

# 成功的話會顯示：
# Hi wuweihungmobile! You've successfully authenticated, but GitHub does not provide shell access.
```

**步驟 6：修改 remote URL 為 SSH**

```bash
# 修改 remote URL 為 SSH 格式
git remote set-url origin git@github.com:wuweihungmobile/AISDLC.git

# 驗證修改
git remote -v

# 應該顯示：
# origin  git@github.com:wuweihungmobile/AISDLC.git (fetch)
# origin  git@github.com:wuweihungmobile/AISDLC.git (push)
```

**步驟 7：使用 SSH 推送**

```bash
# 推送到 GitHub
git push -u origin main
```

**預期結果**:
```
Enumerating objects: 1097, done.
Counting objects: 100% (1097/1097), done.
Delta compression using up to 4 threads
Compressing objects: 100% (1049/1049), done.
Writing objects: 100% (1097/1097), 10.93 MiB | 8.50 MiB/s, done.
Total 1097 (delta 284), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (284/284), done.
To git@github.com:wuweihungmobile/AISDLC.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

**SSH vs HTTPS 比較**:

| 特性 | HTTPS | SSH |
|------|-------|-----|
| **設定難度** | 簡單（只需 Token） | 中等（需生成 Key） |
| **大型推送** | ❌ 容易失敗 | ✅ 穩定可靠 |
| **身份驗證** | 每次需輸入 Token | ✅ 自動驗證 |
| **安全性** | 🔒 安全（需保管 Token） | 🔒🔒 更安全 |
| **推薦用於** | 臨時存取、公共電腦 | 日常開發、個人電腦 |

**建議**:
- ✅ 如果是你的個人電腦 → **使用 SSH**
- ✅ 如果需要頻繁推送 → **使用 SSH**
- ✅ 如果推送大型專案 → **使用 SSH**

---

#### 方案 C：分批推送（最後手段）

如果方案 A 和 B 都失敗，可以嘗試分批推送 commit。

```bash
# 查看 commit 歷史
git log --oneline

# 假設有 3 個 commit，先推送前 2 個
git push -u origin HEAD~1:main

# 再推送最後一個
git push -u origin main
```

**注意**: 這個方法較複雜，通常不需要使用。優先嘗試方案 A 和 B。

---

##### 問題 4：遠端 URL 設定錯誤

**情境**:
你不小心使用了錯誤的 URL（例如：`https://github.com/你的使用者名稱/AISDLC.git`）

**錯誤訊息**:
```
error: remote origin already exists.
```

**解決方案**:

```bash
# 方法 1：修改現有的 remote URL（推薦）
git remote set-url origin https://github.com/wuweihungmobile/AISDLC.git

# 方法 2：刪除後重新新增
git remote remove origin
git remote add origin https://github.com/wuweihungmobile/AISDLC.git

# 驗證修改
git remote -v
```

**其他 remote 管理指令**:

```bash
# 查看 remote 的詳細資訊
git remote show origin

# 重新命名 remote
git remote rename origin new-name

# 列出所有 remote
git remote -v
```

---

### 步驟 9：驗證上傳成功

**目的**: 確認所有檔案已成功上傳

#### 命令行驗證

```bash
# 檢查遠端狀態
git remote show origin

# 查看本地和遠端分支
git branch -a

# 查看最後一次 commit
git log -1
```

#### 網頁驗證

1. 打開瀏覽器
2. 前往 `https://github.com/wuweihungmobile/AISDLC`
3. 確認以下內容：
   - ✅ 所有目錄和檔案都已上傳
   - ✅ Commit message 顯示正確
   - ✅ Repository 描述正確
   - ✅ 檔案數量和結構正確

**預期結果**:

GitHub 網頁上應該顯示：
- `AISDLC_SDD_v0.01/` 目錄
- `CLAUDE.md` 檔案
- 其他專案檔案
- Commit message: "Initial commit: AISDLC Framework v0.01"

---

## 完整指令總覽

### 快速複製貼上版

```bash
# ========== 步驟 1: 配置 Git ==========
git config --global user.name "你的名字"
git config --global user.email "your.email@example.com"

# ========== 步驟 2: 初始化 Repository ==========
cd /path/to/AISDLC_ALL
git init

# ========== 步驟 3: 創建 .gitignore ==========
cat > .gitignore << 'EOF'
# macOS
.DS_Store
.AppleDouble
.LSOverride
._*

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Logs
*.log
logs/
build/logs/*.log

# Temporary files
*.tmp
*.temp
tmp/
temp/

# Environment
.env
.env.local

# OS files
Thumbs.db
Desktop.ini
EOF

# ========== 步驟 4: 加入檔案 ==========
git add .
git status

# ========== 步驟 5: 創建 Commit ==========
git commit -m "Initial commit: AISDLC Framework v0.01

- Complete AISDLC framework structure
- 7 Core Agents (Chinese version)
- 14 Specialized Agents
- 9 Development Scenarios
- Complete workflow definitions
- Document templates and guides

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# ========== 步驟 6: 在 GitHub 創建 Repository（手動操作）==========
# 前往 https://github.com/new
# 創建名為 AISDLC 的 repository（不要勾選任何選項）

# ========== 步驟 7: 連接 GitHub ==========
git remote add origin https://github.com/wuweihungmobile/AISDLC.git
git remote -v

# ========== 步驟 8: 推送到 GitHub ==========
git branch -M main
git push -u origin main
```

### 指令執行順序圖

```
┌─────────────────────────────────────────┐
│ 1. Git 使用者設定                        │
│    git config --global user.name/email  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 2. 初始化 Git Repository                │
│    git init                             │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 3. 創建 .gitignore                      │
│    cat > .gitignore << 'EOF' ...        │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 4. 加入檔案到暫存區                      │
│    git add .                            │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 5. 創建 Commit                          │
│    git commit -m "..."                  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 6. 在 GitHub 創建 Repository（手動）     │
│    https://github.com/new               │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 7. 連接本地和遠端                        │
│    git remote add origin <URL>          │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 8. 推送到 GitHub                        │
│    git push -u origin main              │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ 9. 驗證上傳成功                          │
│    網頁檢查 + git remote show origin    │
└─────────────────────────────────────────┘
```

---

## 後續操作（選用）

### 添加 README.md 到 GitHub 首頁

**目的**: 讓專案說明顯示在 GitHub Repository 首頁

```bash
# 複製 Project_README.md 為 README.md
cp AISDLC_SDD_v0.01/Project_README.md README.md

# 加入變更
git add README.md
git commit -m "Add README for GitHub homepage"
git push
```

**說明**:
- GitHub 會自動顯示根目錄的 `README.md` 在首頁
- 方便訪客快速了解專案內容

---

### 創建 Release Tag

**目的**: 標記版本發布點

```bash
# 創建 v0.01 標籤
git tag -a v0.01 -m "AISDLC Framework v0.01

Release highlights:
- Core maintenance document mechanism enhancement
- FILE_DIRECTORY_RULES.md reorganization
- Complete Chinese Core Agents
- 9 development scenarios
- Comprehensive guides and documentation"

# 推送標籤到 GitHub
git push origin v0.01

# 或推送所有標籤
git push origin --tags
```

**說明**:
- Tag 是 Git 的輕量級標記，用於標記重要版本
- GitHub 會自動在 Releases 頁面顯示 Tag
- 可以為 Tag 創建 Release Notes

---

### 設定 Repository 設定（GitHub 網頁）

**建議設定項目**:

1. **About 區塊**（Repository 首頁右上角）
   - Description: `AI-assisted Software Development Lifecycle Framework`
   - Website: 專案網站（如果有）
   - Topics: `ai`, `framework`, `software-development`, `sdlc`, `agents`

2. **Settings → General**
   - Features: 勾選 `Issues`, `Discussions`（如果需要）
   - Pull Requests: 勾選 `Allow merge commits`

3. **Settings → Branches**
   - Default branch: `main`
   - Branch protection rules（建議）:
     - Require pull request reviews before merging
     - Require status checks to pass before merging

4. **Settings → Pages**（如果需要 GitHub Pages）
   - Source: Deploy from a branch
   - Branch: `main` / `docs`

---

### 添加 License（開源授權）

**目的**: 明確專案的使用授權

```bash
# 創建 MIT License（最常見的開源授權）
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2025 [你的名字]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

# 提交 License
git add LICENSE
git commit -m "Add MIT License"
git push
```

**其他常見授權**:
- **MIT License**: 最寬鬆，允許商業使用
- **Apache License 2.0**: 提供專利授權保護
- **GPL v3**: 要求衍生作品也必須開源

---

## 常見問題排解

### Q1: `git push` 時提示 "Permission denied"

**錯誤訊息**:
```
remote: Permission to 使用者名稱/AISDLC.git denied to 其他使用者名稱.
fatal: unable to access 'https://github.com/使用者名稱/AISDLC.git/': The requested URL returned error: 403
```

**原因**:
- 沒有正確的身份驗證
- 使用了錯誤的帳號

**解決方案**:

1. **使用 Personal Access Token**（步驟 8 - 問題 2 - 方案 A）
2. **使用 SSH Key**（步驟 8 - 問題 2 - 方案 B）
3. **檢查 Git Credential**:
   ```bash
   # 清除儲存的密碼
   git credential-osxkeychain erase
   # 然後輸入：
   # host=github.com
   # protocol=https
   # 按兩次 Enter

   # 重新推送（會提示輸入密碼）
   git push -u origin main
   ```

---

### Q2: `git push` 時提示 "Updates were rejected"

**錯誤訊息**:
```
! [rejected]        main -> main (fetch first)
error: failed to push some refs to 'https://github.com/使用者名稱/AISDLC.git'
hint: Updates were rejected because the remote contains work that you do not have locally.
```

**原因**:
- 遠端 repository 有你本地沒有的 commit
- 通常發生在創建 repository 時勾選了 "Initialize with README"

**解決方案**:

```bash
# 方案 1: 拉取遠端變更後再推送（建議）
git pull origin main --rebase
git push origin main

# 方案 2: 強制推送（⚠️ 危險！會覆蓋遠端）
git push -f origin main
```

**注意**: 只在確定遠端沒有重要 commit 時才使用 `git push -f`

---

### Q3: 不小心提交了敏感資訊怎麼辦？

**情境**:
- 提交了密碼、API Key、Token 等敏感資訊
- 已經推送到 GitHub

**解決方案**:

#### 方案 1: 使用 Git 修改歷史（簡單情況）

```bash
# 如果只是最後一次 commit
git reset HEAD~1
# 編輯檔案，移除敏感資訊
git add .
git commit -m "Remove sensitive data"
git push -f origin main
```

#### 方案 2: 使用 BFG Repo-Cleaner（複雜情況）

```bash
# 安裝 BFG（macOS）
brew install bfg

# 創建包含敏感資訊的檔案列表
echo "password123" > passwords.txt

# 清理 repository
bfg --replace-text passwords.txt AISDLC_ALL/.git

# 清理 reflog
cd AISDLC_ALL
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 強制推送
git push -f origin main
```

**⚠️ 重要**:
- 敏感資訊一旦推送到 GitHub，應立即撤銷（如更改密碼、撤銷 Token）
- 修改歷史會影響所有協作者，需要協調

---

### Q4: `.gitignore` 沒有生效

**情境**:
- 已經創建了 `.gitignore`
- 但某些檔案還是被追蹤

**原因**:
- 檔案在創建 `.gitignore` 之前就已經被 `git add`

**解決方案**:

```bash
# 移除已追蹤的檔案（不會刪除實際檔案）
git rm --cached 檔案名稱

# 或移除整個目錄
git rm -r --cached 目錄名稱/

# 重新加入所有檔案（會套用 .gitignore 規則）
git add .
git commit -m "Apply .gitignore rules"
```

---

### Q5: 如何更改 Repository 名稱？

**情境**:
- 想要更改 GitHub Repository 名稱
- 已經有本地 clone

**解決方案**:

1. **在 GitHub 網頁更改名稱**
   - 前往 Repository → Settings → Repository name
   - 輸入新名稱，點擊 Rename

2. **更新本地 remote URL**
   ```bash
   # 更新 remote URL
   git remote set-url origin https://github.com/使用者名稱/新名稱.git

   # 驗證
   git remote -v
   ```

---

### Q6: 如何刪除遠端 Repository？

**⚠️ 危險操作！無法復原！**

**步驟**:
1. 前往 GitHub Repository 頁面
2. 點擊 **Settings**
3. 滾動到最下方的 **Danger Zone**
4. 點擊 **Delete this repository**
5. 輸入 Repository 完整名稱確認
6. 輸入密碼確認

**本地清理**:
```bash
# 移除 remote（本地檔案不受影響）
git remote remove origin

# 驗證
git remote -v
```

---

### Q7: 多人協作時如何同步？

**情境**:
- 團隊成員修改了遠端 repository
- 需要同步到本地

**解決方案**:

```bash
# 拉取最新變更
git pull origin main

# 如果有衝突，解決衝突後
git add .
git commit -m "Resolve merge conflicts"
git push origin main
```

**最佳實踐**:
1. 每次開始工作前先 `git pull`
2. 頻繁提交和推送
3. 使用分支進行功能開發
4. 使用 Pull Request 進行程式碼審查

---

## 注意事項

### ⚠️ 安全性注意事項

1. **敏感資訊檢查**
   - ✅ 確認專案中沒有密碼、API Key、Token
   - ✅ 檢查 `.env` 檔案是否已加入 `.gitignore`
   - ✅ 檢查 `config.json` 等設定檔是否包含敏感資訊
   - ✅ 使用 `git log -p` 檢查歷史 commit 是否包含敏感資訊

2. **Personal Access Token 保管**
   - 🔒 Token 具有完整的 repository 權限
   - 🔒 不要將 Token 寫入程式碼或提交到 Git
   - 🔒 定期更新 Token（建議每 90 天）
   - 🔒 不再使用的 Token 應立即撤銷

3. **SSH Key 保管**
   - 🔒 私鑰（`id_ed25519`）不應分享給任何人
   - 🔒 私鑰應設定 passphrase 保護
   - 🔒 公鑰（`id_ed25519.pub`）可以安全地添加到 GitHub

---

### 📏 GitHub 限制

1. **檔案大小限制**
   - 單檔限制：100 MB
   - 建議上限：50 MB
   - Repository 總大小建議：< 1 GB

2. **Git LFS（Large File Storage）**
   - 用於儲存大型檔案（影片、模型、資料集）
   - 免費帳號：1 GB 儲存空間，每月 1 GB 頻寬
   - 需要額外設定

3. **Commit 限制**
   - 每次 push 最多 2048 個檔案
   - 每次 commit 建議 < 100 個檔案

---

### 🔒 Public vs Private Repository 選擇

| 特性 | Public | Private |
|------|--------|---------|
| **可見性** | 所有人可見 | 僅授權成員可見 |
| **協作者** | 無限（可 fork） | 免費帳號：無限 |
| **費用** | 免費 | 免費 |
| **適用場景** | 開源專案、作品集 | 商業專案、內部工具 |
| **GitHub Pages** | 可用 | 付費帳號可用 |
| **推薦用於 AISDLC** | ✅ 如果想分享給社群 | ✅ 如果包含商業資訊 |

**建議**:
- 如果 AISDLC 用於公司專案 → **Private**
- 如果想建立開源社群 → **Public**
- 不確定 → 先選 **Private**，之後可以改為 Public

---

### 📋 最佳實踐

1. **Commit Message 規範**
   - 使用清楚的描述性訊息
   - 第一行簡短總結（< 50 字元）
   - 第二行空白
   - 第三行開始詳細說明
   - 範例格式：
     ```
     feat: Add user authentication module

     - Implement JWT token generation
     - Add login/logout endpoints
     - Add password hashing with bcrypt

     Closes #123
     ```

2. **分支策略**
   - `main` / `master`: 穩定版本
   - `develop`: 開發版本
   - `feature/功能名稱`: 功能開發分支
   - `hotfix/問題名稱`: 緊急修復分支

3. **README.md 內容建議**
   - 專案簡介
   - 功能特色
   - 安裝步驟
   - 使用範例
   - 授權資訊
   - 貢獻指南

4. **定期備份**
   - GitHub 本身就是遠端備份
   - 建議定期 `git pull` 到多個裝置
   - 重要版本可以額外下載 ZIP 備份

---

### 🎯 下一步建議

完成上傳後，建議執行以下操作：

1. **✅ 設定 Repository 說明和標籤**（步驟見「後續操作」）
2. **✅ 添加 LICENSE 檔案**（明確專案授權）
3. **✅ 創建 Release Tag**（標記版本發布點）
4. **✅ 設定 Branch Protection Rules**（保護主分支）
5. **✅ 啟用 GitHub Issues**（追蹤問題和需求）
6. **✅ 啟用 GitHub Discussions**（社群討論）
7. **✅ 設定 GitHub Actions**（自動化測試和部署）

---

## 📚 相關資源

### Git 學習資源

- **官方文檔**: [https://git-scm.com/doc](https://git-scm.com/doc)
- **Pro Git 書籍**（繁體中文）: [https://git-scm.com/book/zh-tw/v2](https://git-scm.com/book/zh-tw/v2)
- **Git 指令速查表**: [https://training.github.com/downloads/zh_TW/github-git-cheat-sheet/](https://training.github.com/downloads/zh_TW/github-git-cheat-sheet/)

### GitHub 學習資源

- **GitHub Docs**: [https://docs.github.com/](https://docs.github.com/)
- **GitHub Learning Lab**: [https://lab.github.com/](https://lab.github.com/)
- **GitHub Skills**: [https://skills.github.com/](https://skills.github.com/)

### AISDLC 相關文檔

- **Project README**: [AISDLC_SDD_v0.01/Project_README.md](../../Project_README.md)
- **Integration Guide**: [AISDLC_SDD_v0.01/INTEGRATION_GUIDE.md](../../INTEGRATION_GUIDE.md)
- **Quick Start**: [guides/user/onboarding/QUICK_START_GUIDE.md](../onboarding/QUICK_START_GUIDE.md)

---

## 🔄 版本歷史

| 版本 | 日期 | 變更說明 | 作者 |
|------|------|---------|------|
| v1.0 | 2025-01-10 | 初始版本，完整的 GitHub 上傳指南 | AISDLC Team |

---

## 📝 文檔維護

**維護者**: AISDLC Framework Team
**最後審查**: 2025-01-10
**下次審查**: 2025-04-10（每季審查）

**回饋與建議**:
- 如發現文檔錯誤或有改進建議，請提交 GitHub Issue
- 或直接提交 Pull Request 修改本文檔

---

## ✅ 檢查清單

完成以下所有步驟後，你的 AISDLC 專案就成功上傳到 GitHub 了！

- [ ] 步驟 1: 配置 Git 使用者資訊
- [ ] 步驟 2: 初始化本地 Git Repository
- [ ] 步驟 3: 創建 .gitignore 檔案
- [ ] 步驟 4: 將檔案加入 Git 暫存區
- [ ] 步驟 5: 創建第一個 Commit
- [ ] 步驟 6: 在 GitHub 上創建 Repository
- [ ] 步驟 7: 連接本地 Repository 到 GitHub
- [ ] 步驟 8: 推送到 GitHub
- [ ] 步驟 9: 驗證上傳成功
- [ ] （選用）添加 README.md 到首頁
- [ ] （選用）創建 Release Tag
- [ ] （選用）添加 LICENSE 檔案
- [ ] （選用）設定 Repository 設定

---

**🎉 恭喜！你已經成功將 AISDLC 專案上傳到 GitHub！🎉**

如有任何問題，請參考「常見問題排解」章節，或提交 GitHub Issue 尋求幫助。
