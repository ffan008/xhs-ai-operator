# 贡献指南

感谢你对小红书AI运营系统的关注！我们欢迎任何形式的贡献。

## 如何贡献

### 报告问题

如果你发现了bug或有功能建议：

1. 在 [Issues](https://github.com/your-username/xhs-ai-operator/issues) 中搜索是否已有类似问题
2. 如果没有，创建新的Issue，详细描述问题或建议
3. 对于bug，请提供：
   - 复现步骤
   - 预期行为
   - 实际行为
   - 系统环境信息
   - 相关日志

### 提交代码

#### 1. Fork 仓库

点击页面右上角的 Fork 按钮

#### 2. 克隆你的 Fork

```bash
git clone https://github.com/your-username/xhs-ai-operator.git
cd xhs-ai-operator
```

#### 3. 创建特性分支

```bash
git checkout -b feature/your-feature-name
```

#### 4. 进行修改

- 遵循现有代码风格
- 添加必要的测试
- 更新相关文档

#### 5. 提交更改

```bash
git add .
git commit -m "feat: 添加某功能的描述"
```

#### 6. 推送到你的 Fork

```bash
git push origin feature/your-feature-name
```

#### 7. 创建 Pull Request

1. 访问原仓库的 Pull Requests 页面
2. 点击 "New Pull Request"
3. 选择你的分支
4. 填写 PR 描述模板
5. 等待审查

## 开发规范

### 代码风格

#### Python

- 遵循 PEP 8
- 使用有意义的变量和函数名
- 添加必要的注释和文档字符串

#### JavaScript/Node.js

- 使用 ESLint
- 遵循 AirBnB 风格指南

### 提交信息规范

使用约定式提交格式：

```
<类型>(<范围>): <描述>

[可选的正文]

[可选的脚注]
```

**类型**：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具链相关

**示例**：
```
feat(scheduler): 添加任务暂停和恢复功能

- 添加 pause_job 工具
- 添加 resume_job 工具
- 更新任务状态管理

Closes #123
```

### 文档规范

- 使用清晰简洁的中文
- 代码注释使用英文
- Markdown 文档每行不超过 80 字符
- 及时更新相关文档

## 测试

在提交PR前，请确保：

1. 代码能正常运行
2. 添加了必要的测试
3. 所有测试通过
4. 文档已更新

## 项目结构

```
.
├── xhs-operator/          # Skill 主目录
│   ├── SKILL.md          # 核心配置
│   ├── PROMPTS/          # Prompt 模板
│   └── CONFIG/           # 配置文件
│
├── scheduler-mcp/        # 定时任务 MCP
├── analytics-mcp/        # 数据分析 MCP
├── integration-mcp/      # 工作流协调 MCP
│
├── README.md             # 项目文档
├── QUICKSTART.md         # 快速开始
└── CONTRIBUTING.md       # 贡献指南（本文件）
```

## 获取帮助

如果你在贡献过程中遇到问题：

- 查看项目文档
- 搜索或创建 Issue
- 在讨论区提问

## 行为准则

请尊重所有贡献者，保持友好和专业。不允许：

- 骚扰或歧视性言论
- 人身攻击
- 未经许可发布他人信息
- 其他不专业行为

## 许可证

通过贡献代码，你同意你的贡献将使用与项目相同的 [MIT 许可证](LICENSE)。

---

再次感谢你的贡献！🎉
