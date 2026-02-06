# 小红书 AI 运营系统 - 快速开始指南

## 5 分钟快速上手

### 第一步：运行安装脚本

```bash
bash ~/.refly/mcp-servers/setup.sh
```

这将会：
- ✅ 检查环境（Python、Node.js、Docker）
- ✅ 创建目录结构
- ✅ 安装所有依赖
- ✅ 克隆 xiaohongshu-mcp
- ✅ 生成配置文件

### 第二步：配置 API Keys

编辑 `~/.claude/mcp_config.json`，添加你的 Stability AI API Key：

```json
{
  "mcpServers": {
    "stability-mcp": {
      "command": "npx",
      "args": ["-y", "@tadasant/mcp-server-stability-ai"],
      "env": {
        "STABILITY_API_KEY": "sk-your-actual-api-key-here"
      }
    }
  }
}
```

**获取 API Key**：
1. 访问 https://platform.stability.ai/
2. 注册账号
3. 在 Dashboard 获取 API Key
4. 免费额度足够测试使用

### 第三步：重启 Claude Code

完全退出并重新启动 Claude Code 应用。

### 第四步：测试系统

在 Claude Code 中输入：

```
/xhs 账号
```

如果看到账号信息，说明系统运行正常！

### 第五步：发布第一篇笔记

```
/xhs 发布 春天来了，分享3个踏青好去处
```

系统将自动：
1. 📝 生成吸引人的标题
2. ✍️ 创作正文内容
3. 🎨 生成配图
4. 📤 发布到小红书
5. 🔗 返回笔记链接

---

## 常用命令速查

### 基础操作

| 命令 | 说明 | 示例 |
|------|------|------|
| `/xhs 发布 [主题]` | 一键发布 | `/xhs 发布 今日穿搭` |
| `/xhs 创作 [主题] -风格 [风格]` | AI创作 | `/xhs 创作 早餐 -风格 治愈` |
| `/xhs 分析 [时间]` | 数据分析 | `/xhs 分析 最近7天` |
| `/xhs 定时 [cron] [任务]` | 定时发布 | `/xhs 定时 "0 9 * * *" 早安` |
| `/xhs 批量 [数量] [主题]` | 批量操作 | `/xhs 批量 5 美食推荐` |

### 风格选项

- `活泼` - 亲切自然，适合日常
- `专业` - 严谨逻辑，适合干货
- `治愈` - 温柔诗意，适合情感
- `干货` - 信息密集，适合教程
- `种草` - 真实体验，适合推荐

### Cron 表达式速查

```
0 7 * * *      # 每天早上7点
0 9 * * 1-5    # 工作日早上9点
0 */6 * * *    # 每6小时
0 0 * * 0      # 每周日0点
*/30 * * * *   # 每30分钟
```

---

## 故障排除

### 问题：MCP 连接失败

```bash
# 检查配置文件
cat ~/.claude/mcp_config.json

# 测试 Python 脚本
python3 ~/.refly/mcp-servers/scheduler-mcp/src/server.py
```

### 问题：图像生成失败

- 检查 API Key 是否正确
- 验证账户余额
- 确保网络连接正常

### 问题：发布失败

- 检查小红书登录状态
- 降低发布频率
- 查看错误日志

---

## 下一步

1. 📖 阅读完整文档：`README.md`
2. 🎨 自定义内容模板：编辑 `CONFIG/templates.json`
3. ⏰ 设置定时任务：编辑 `CONFIG/schedule.yaml`
4. 📊 查看数据分析：`/xhs 分析 最近30天`

---

**需要帮助？**

- 📧 Email: your-email@example.com
- 🐛 Issues: GitHub Issues
- 📖 文档: README.md

**祝使用愉快！** 🎉
