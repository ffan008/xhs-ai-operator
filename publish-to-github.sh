#!/bin/bash

###############################################################################
# GitHub 仓库创建和推送脚本
###############################################################################

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}小红书AI运营系统 - GitHub发布助手${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# 检查是否在项目目录
if [ ! -f "README.md" ]; then
    echo -e "${YELLOW}错误: 请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 显示当前状态
echo -e "${GREEN}当前Git状态:${NC}"
git status
echo ""

# 询问仓库名称
read -p "请输入GitHub仓库名称 (默认: xhs-ai-operator): " REPO_NAME
REPO_NAME=${REPO_NAME:-xhs-ai-operator}

# 询问仓库描述
read -p "请输入仓库描述: " REPO_DESC

# 询问是否为私有仓库
read -p "是否为私有仓库? (y/N): " PRIVATE
if [[ $PRIVATE =~ ^[Yy]$ ]]; then
    PRIVATE_FLAG="--private"
else
    PRIVATE_FLAG="--public"
fi

echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}配置摘要:${NC}"
echo -e "${BLUE}======================================${NC}"
echo "仓库名称: $REPO_NAME"
echo "仓库描述: $REPO_DESC"
echo "可见性: $(if [[ $PRIVATE =~ ^[Yy]$ ]]; then echo '私有'; else echo '公开'; fi)"
echo ""

# 确认
read -p "确认创建? (y/N): " CONFIRM
if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo -e "${GREEN}步骤 1/3: 检查GitHub配置...${NC}"

# 检查Git配置
if ! git config user.name >/dev/null 2>&1; then
    read -p "请输入Git用户名: " GIT_USERNAME
    git config --global user.name "$GIT_USERNAME"
fi

if ! git config user.email >/dev/null 2>&1; then
    read -p "请输入Git邮箱: " GIT_EMAIL
    git config --global user.email "$GIT_EMAIL"
fi

echo -e "${GREEN}✓ Git配置完成${NC}"
echo ""
echo -e "${GREEN}步骤 2/3: 创建GitHub仓库...${NC}"

# 提供手动创建仓库的指示
echo ""
echo -e "${YELLOW}请按照以下步骤在GitHub上创建仓库:${NC}"
echo ""
echo "1. 访问: https://github.com/new"
echo "2. 仓库名称: $REPO_NAME"
echo "3. 描述: $REPO_DESC"
echo "4. 可见性: $(if [[ $PRIVATE =~ ^[Yy]$ ]]; then echo 'Private'; else echo 'Public'; fi)"
echo "5. ❌ 不要勾选 'Add a README file' (我们已经有了)"
echo "6. ❌ 不要勾选 '.gitignore' (我们已经有了)"
echo "7. ❌ 不要选择许可证 (我们已经有了 MIT)"
echo "8. 点击 'Create repository'"
echo ""
read -p "按回车键继续，一旦你在GitHub上创建了仓库..."

# 获取GitHub用户名
GITHUB_USERNAME=$(git config user.name)
echo ""
echo -e "${GREEN}检测到的GitHub用户名: $GITHUB_USERNAME${NC}"
read -p "如果不对，请输入正确的GitHub用户名: " CORRECT_USERNAME
GITHUB_USERNAME=${CORRECT_USERNAME:-$GITHUB_USERNAME}

# 添加远程仓库
REMOTE_URL="https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
echo ""
echo -e "${GREEN}步骤 3/3: 推送代码到GitHub...${NC}"
echo "远程仓库URL: $REMOTE_URL"
echo ""

# 检查是否已有远程仓库
if git remote get-url origin >/dev/null 2>&1; then
    echo "检测到已有远程仓库，正在更新..."
    git remote set-url origin "$REMOTE_URL"
else
    echo "添加远程仓库..."
    git remote add origin "$REMOTE_URL"
fi

echo ""
echo "推送代码到GitHub..."
git push -u origin main

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}✓ 发布成功！${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "仓库地址: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
echo ""
echo -e "${BLUE}后续步骤:${NC}"
echo "1. 在GitHub仓库设置中添加分支保护规则"
echo "2. 设置GitHub Actions (如果需要CI/CD)"
echo "3. 添加仓库主题和描述"
echo "4. 在README中添加星标按钮"
echo ""
echo -e "${YELLOW}提示:${NC} 你可以将仓库添加到Claude Code的配置中让其他人使用"
echo ""
