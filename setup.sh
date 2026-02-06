#!/bin/bash

###############################################################################
# 小红书 AI 运营系统 - 环境设置脚本
# 自动安装和配置所有依赖
###############################################################################

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}#############################################${NC}"
    echo -e "${BLUE}# $1${NC}"
    echo -e "${BLUE}#############################################${NC}"
    echo ""
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 主安装目录
INSTALL_DIR="$HOME/.refly/mcp-servers"
SKILL_DIR="$HOME/.claude/skills/xhs-operator"

###############################################################################
# 1. 环境检查
###############################################################################
print_header "步骤 1/7: 环境检查"

# 检查 Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python 已安装: $PYTHON_VERSION"
else
    print_error "Python 3 未安装，请先安装 Python 3.9+"
    exit 1
fi

# 检查 Node.js
if command_exists node && command_exists npm; then
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    print_success "Node.js 已安装: $NODE_VERSION"
    print_success "npm 已安装: $NPM_VERSION"
else
    print_error "Node.js 或 npm 未安装，请先安装 Node.js 18+"
    exit 1
fi

# 检查 Docker (可选)
if command_exists docker; then
    DOCKER_VERSION=$(docker --version)
    print_success "Docker 已安装: $DOCKER_VERSION"
    DOCKER_AVAILABLE=true
else
    print_warning "Docker 未安装，xiaohongshu-mcp 需要 Docker"
    print_info "如需使用完整功能，请安装 Docker: https://docs.docker.com/get-docker/"
    DOCKER_AVAILABLE=false
fi

###############################################################################
# 2. 创建目录结构
###############################################################################
print_header "步骤 2/7: 创建目录结构"

print_info "创建 MCP 服务器目录..."
mkdir -p "$INSTALL_DIR"/{scheduler-mcp,analytics-mcp,integration-mcp}/{src,config,data}
print_success "MCP 服务器目录已创建"

print_info "创建 Skill 目录..."
mkdir -p "$SKILL_DIR"/{PROMPTS,CONFIG}
print_success "Skill 目录已创建"

###############################################################################
# 3. 安装 Python 依赖
###############################################################################
print_header "步骤 3/7: 安装 Python 依赖"

print_info "安装 scheduler-mcp 依赖..."
cd "$INSTALL_DIR/scheduler-mcp"
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --quiet
    print_success "scheduler-mcp 依赖已安装"
else
    print_warning "requirements.txt 未找到"
fi

print_info "安装 analytics-mcp 依赖..."
cd "$INSTALL_DIR/analytics-mcp"
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --quiet
    print_success "analytics-mcp 依赖已安装"
else
    print_warning "requirements.txt 未找到"
fi

print_info "安装 integration-mcp 依赖..."
cd "$INSTALL_DIR/integration-mcp"
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --quiet
    print_success "integration-mcp 依赖已安装"
else
    print_warning "requirements.txt 未找到"
fi

###############################################################################
# 4. 克隆 xiaohongshu-mcp (可选)
###############################################################################
print_header "步骤 4/7: 安装 xiaohongshu-mcp"

if [ "$DOCKER_AVAILABLE" = true ]; then
    print_info "克隆 xiaohongshu-mcp 仓库..."
    if [ ! -d "$INSTALL_DIR/xiaohongshu-mcp" ]; then
        git clone https://github.com/xpzouying/xiaohongshu-mcp.git "$INSTALL_DIR/xiaohongshu-mcp" --quiet
        print_success "xiaohongshu-mcp 已克隆"

        print_info "启动 xiaohongshu-mcp 服务..."
        cd "$INSTALL_DIR/xiaohongshu-mcp"
        docker compose up -d --quiet
        print_success "xiaohongshu-mcp 服务已启动"
    else
        print_info "xiaohongshu-mcp 已存在，跳过克隆"
        print_info "如需更新，请运行: cd $INSTALL_DIR/xiaohongshu-mcp && git pull && docker compose restart"
    fi
else
    print_warning "Docker 不可用，跳过 xiaohongshu-mcp 安装"
fi

###############################################################################
# 5. 安装 stability-mcp (可选)
###############################################################################
print_header "步骤 5/7: 安装 stability-mcp"

print_info "安装 stability-mcp..."
if npm list -g @tadasant/mcp-server-stability-ai >/dev/null 2>&1; then
    print_info "stability-mcp 已安装"
else
    print_warning "stability-mcp 需要手动安装"
    print_info "安装命令: npm install -g @tadasant/mcp-server-stability-ai"
    print_info "注意: 需要 Stability AI API Key"
fi

###############################################################################
# 6. 配置 Claude Code MCP
###############################################################################
print_header "步骤 6/7: 配置 Claude Code MCP"

MCP_CONFIG_FILE="$HOME/.claude/mcp_config.json"

print_info "检查 MCP 配置文件..."

if [ ! -f "$MCP_CONFIG_FILE" ]; then
    print_warning "MCP 配置文件不存在，创建示例配置"
    mkdir -p "$(dirname "$MCP_CONFIG_FILE")"
    cat > "$MCP_CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
    "xiaohongshu-mcp": {
      "command": "docker",
      "args": ["compose", "-f", "/Users/fans/.refly/mcp-servers/xiaohongshu-mcp/docker-compose.yml", "up", "xiaohongshu-mcp"],
      "env": {}
    },
    "stability-mcp": {
      "command": "npx",
      "args": ["-y", "@tadasant/mcp-server-stability-ai"],
      "env": {
        "STABILITY_API_KEY": "your-stability-api-key-here"
      }
    },
    "scheduler-mcp": {
      "command": "python3",
      "args": ["/Users/fans/.refly/mcp-servers/scheduler-mcp/src/server.py"]
    },
    "analytics-mcp": {
      "command": "python3",
      "args": ["/Users/fans/.refly/mcp-servers/analytics-mcp/src/server.py"]
    },
    "integration-mcp": {
      "command": "python3",
      "args": ["/Users/fans/.refly/mcp-servers/integration-mcp/src/workflow.py"]
    }
  }
}
EOF
    print_success "示例配置已创建: $MCP_CONFIG_FILE"
    print_warning "请编辑配置文件，添加您的 API Keys"
else
    print_info "MCP 配置文件已存在"
    print_info "如需添加新服务器，请手动编辑: $MCP_CONFIG_FILE"
fi

###############################################################################
# 7. 设置完成
###############################################################################
print_header "步骤 7/7: 安装完成"

print_success "小红书 AI 运营系统环境设置完成！"
echo ""
print_info "下一步操作:"
echo ""
echo "1. 编辑 MCP 配置文件:"
echo "   nano $MCP_CONFIG_FILE"
echo ""
echo "2. 添加必要的 API Keys:"
echo "   - Stability AI API Key (用于图像生成)"
echo ""
echo "3. (可选) 配置小红书账号:"
echo "   nano $SKILL_DIR/CONFIG/accounts.json"
echo ""
echo "4. 重启 Claude Code 以加载新配置"
echo ""
echo "5. 测试系统:"
echo "   在 Claude Code 中输入: /xhs 账号"
echo ""

###############################################################################
# 快速测试
###############################################################################
print_info "运行快速测试..."

# 测试 Python 脚本
print_info "测试 scheduler-mcp..."
cd "$INSTALL_DIR/scheduler-mcp"
if python3 -c "import sys; sys.path.insert(0, 'src'); from server import SchedulerMCP; print('OK')" 2>/dev/null; then
    print_success "scheduler-mcp 导入正常"
else
    print_warning "scheduler-mcp 导入测试失败"
fi

print_info "测试 analytics-mcp..."
cd "$INSTALL_DIR/analytics-mcp"
if python3 -c "import sys; sys.path.insert(0, 'src'); from server import AnalyticsMCP; print('OK')" 2>/dev/null; then
    print_success "analytics-mcp 导入正常"
else
    print_warning "analytics-mcp 导入测试失败"
fi

print_info "测试 integration-mcp..."
cd "$INSTALL_DIR/integration-mcp"
if python3 -c "import sys; sys.path.insert(0, 'src'); from workflow import IntegrationMCP; print('OK')" 2>/dev/null; then
    print_success "integration-mcp 导入正常"
else
    print_warning "integration-mcp 导入测试失败"
fi

###############################################################################
# 文件清单
###############################################################################
echo ""
print_info "已创建文件清单:"
echo ""
echo "Skill 文件:"
echo "  - $SKILL_DIR/SKILL.md"
echo "  - $SKILL_DIR/PROMPTS/content_generation.md"
echo "  - $SKILL_DIR/PROMPTS/image_generation.md"
echo "  - $SKILL_DIR/PROMPTS/analysis_report.md"
echo "  - $SKILL_DIR/CONFIG/accounts.json"
echo "  - $SKILL_DIR/CONFIG/templates.json"
echo "  - $SKILL_DIR/CONFIG/schedule.yaml"
echo ""
echo "MCP 服务器:"
echo "  - $INSTALL_DIR/scheduler-mcp/"
echo "  - $INSTALL_DIR/analytics-mcp/"
echo "  - $INSTALL_DIR/integration-mcp/"
echo "  - $INSTALL_DIR/xiaohongshu-mcp/ (如 Docker 可用)"
echo ""

###############################################################################
# 故障排除提示
###############################################################################
print_header "故障排除"

echo "如遇到问题，请检查:"
echo ""
echo "1. Python 依赖是否安装:"
echo "   pip3 list | grep -E 'mcp|apscheduler'"
echo ""
echo "2. MCP 服务器是否可运行:"
echo "   python3 $INSTALL_DIR/scheduler-mcp/src/server.py --help"
echo ""
echo "3. Docker 服务是否运行:"
echo "   docker ps"
echo ""
echo "4. Claude Code 日志:"
echo "   查看开发者工具控制台"
echo ""
echo "5. 获取帮助:"
echo "   GitHub: https://github.com/xpzouying/xiaohongshu-mcp"
echo ""

print_success "安装脚本执行完成！"
