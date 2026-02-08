# API 密钥配置指南

## 📋 概述

小红书 AI 运营系统需要配置多个 API 密钥才能正常工作。本指南将帮助你安全地配置这些密钥。

---

## 🔐 安全原则

### ✅ 推荐做法

1. **使用环境变量**: 所有密钥通过环境变量配置
2. **最小权限**: 密钥文件权限设置为 600
3. **不要提交**: 永远不要将密钥提交到 Git
4. **定期轮换**: 定期更换 API 密钥

### ❌ 避免做法

1. ❌ 在代码中硬编码密钥
2. ❌ 将密钥提交到版本控制
3. ❌ 在日志中打印密钥
4. ❌ 使用过于宽松的文件权限

---

## 🚀 快速开始

### 步骤 1: 安装 keyring (推荐)

```bash
# macOS
brew install python-keyring

# Linux
sudo apt-get install python3-keyring

# 使用 pip
pip install keyring
```

### 步骤 2: 配置 API 密钥

#### 方法 1: 使用 .env 文件 (推荐)

```bash
# 1. 复制模板
cp .env.template .env

# 2. 编辑 .env 文件，填入你的密钥
nano .env
```

在 `.env` 文件中添加：

```bash
# Stability AI (图像生成)
STABILITY_API_KEY=sk-your-key-here

# OpenAI DALL-E (图像生成)
OPENAI_API_KEY=sk-your-openai-key-here

# Replicate (图像生成)
REPLICATE_API_TOKEN=r8-your-token-here
```

#### 方法 2: 使用环境变量

```bash
# 在 shell 配置文件中添加 (~/.bashrc 或 ~/.zshrc)
export STABILITY_API_KEY="sk-your-key-here"
export OPENAI_API_KEY="sk-your-openai-key-here"
export REPLICATE_API_TOKEN="r8-your-token-here"

# 重新加载配置
source ~/.bashrc  # 或 source ~/.zshrc
```

#### 方法 3: 使用 keyring (最安全)

```bash
# 存储 Stability AI 密钥
python3 -c "
from common.security import key_manager
key_manager.set('STABILITY_API_KEY', 'sk-your-key-here')
"

# 存储 OpenAI 密钥
python3 -c "
from common.security import key_manager
key_manager.set('OPENAI_API_KEY', 'sk-your-openai-key-here')
"
```

### 步骤 3: 验证配置

```bash
# 运行验证脚本
python3 scripts/validate_config.py
```

预期输出：
```
📊 验证结果摘要
============================================================
文件权限: 4/4 安全
API密钥: 2/6 有效
文件格式: 4/4 正确
发现问题: 0 个
安全评分: 90/100
状态: ✅ 良好
============================================================
```

---

## 🔑 获取 API 密钥

### Stability AI

1. 访问: https://platform.stability.ai/
2. 注册账号
3. 在 Dashboard 获取 API Key
4. 免费额度: $25
5. 成本: $0.01-0.08/图

### OpenAI DALL-E

1. 访问: https://platform.openai.com/
2. 注册账号
3. 创建 API Key
4. 按使用量付费
5. 成本: $0.02-0.12/图

### Replicate

1. 访问: https://replicate.com/
2. GitHub 账号登录
3. 创建 API Token
4. 免费试用可用
5. 成本: $0.002-0.06/图

### Hugging Face (可选)

1. 访问: https://huggingface.co/
2. 注册账号
3. 创建 Access Token
4. 大部分模型免费
5. 成本: 免费

### Ideogram (可选)

1. 访问: https://ideogram.ai/
2. 注册账号
3. 在设置中获取 API Key
4. 有免费额度
5. 成本: 免费/付费

### Leonardo AI (可选)

1. 访问: https://leonardo.ai/
2. 注册账号
3. 在 API 设置中获取 Key
4. 有免费额度
5. 成本: $0.01-0.04/图

---

## 🛡️ 安全检查清单

- [ ] 已配置至少 1 个图像生成服务
- [ ] 所有配置文件权限为 600
- [ ] .env 文件已添加到 .gitignore
- [ ] 运行验证脚本无错误
- [ ] API 密钥不在代码中硬编码

---

## 🔧 故障排除

### 问题 1: 密钥验证失败

**症状**: 运行验证脚本时显示密钥无效

**解决方案**:
1. 检查密钥是否正确复制（无多余空格）
2. 确认密钥未过期
3. 检查密钥格式是否正确

### 问题 2: 权限错误

**症状**: 无法读取配置文件

**解决方案**:
```bash
# 修复配置文件权限
chmod 600 ~/.claude/skills/xhs-operator/CONFIG/*
```

### 问题 3: keyring 不可用

**症状**: 警告 "keyring not installed"

**解决方案**:
```bash
# 安装 keyring
pip install keyring

# 或使用环境变量作为替代方案
```

---

## 📚 相关文档

- [多模型配置指南](../MULTI_MODEL_GUIDE.md)
- [优化实施计划](../OPTIMIZATION_PLAN.md)
- [README](../README.md)

---

**更新日期**: 2025-02-06
**版本**: v1.0
