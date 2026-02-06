# 多模型图像生成配置指南

## 概述

小红书AI运营系统支持多个图像生成模型，你可以根据需求选择最合适的模型，实现成本、质量和速度的最优平衡。

---

## 支持的模型

### 1. Stability AI

**模型**:
- SD3 (Stable Diffusion 3) - 最新版本，质量最高
- SDXL - 平衡质量和速度
- SD Turbo - 快速生成，适合批量

**优点**:
- 质量优秀
- 支持多种风格
- 速度快（Turbo版本）

**成本**: $0.01-0.08/图

**配置**:
```json
{
  "stability": {
    "enabled": true,
    "api_key": "your-stability-api-key",
    "default_model": "sd3"
  }
}
```

### 2. OpenAI DALL-E

**模型**:
- DALL-E 3 - 最新版本，理解能力强
- DALL-E 2 - 经典版本，速度快

**优点**:
- 质量最稳定
- 理解提示词能力强
- API简单易用

**成本**: $0.02-0.12/图

**限制**:
- 仅支持1:1比例（需要裁剪）

**配置**:
```json
{
  "openai": {
    "enabled": true,
    "api_key": "your-openai-api-key",
    "default_model": "dall-e-3"
  }
}
```

### 3. Replicate

**模型**:
- SDXL - 多个优化版本
- FLUX.1 - Black Forest Labs最新模型
- Playground v2.5 - 优秀审美

**优点**:
- 模型丰富
- 性价比高
- 按量付费

**成本**: $0.002-0.06/图

**配置**:
```json
{
  "replicate": {
    "enabled": true,
    "api_key": "your-replicate-api-token",
    "default_model": "sdxl"
  }
}
```

### 4. Hugging Face (免费)

**模型**:
- SDXL Turbo - 开源免费
- FLUX.1 Schnell - 开源快速版

**优点**:
- 完全免费
- 开源模型
- 无限额使用

**缺点**:
- 需要自己部署或使用Inference API
- 速度可能较慢

**成本**: 免费

**配置**:
```json
{
  "huggingface": {
    "enabled": true,
    "api_key": "optional-api-key",
    "default_model": "sdxl-turbo"
  }
}
```

### 5. Ideogram

**模型**:
- Ideogram V2 - 擅长文字渲染

**优点**:
- 文字渲染优秀
- 有免费额度
- 质量不错

**适用**: 文字海报、品牌内容

**成本**: 免费(有限额)/付费

**配置**:
```json
{
  "ideogram": {
    "enabled": true,
    "api_key": "your-ideogram-api-key",
    "default_model": "ideogram-v2"
  }
}
```

### 6. Leonardo AI

**模型**:
- Leonardo Phoenix - 自研模型
- SD3 Leonardo - 基于SD3优化

**优点**:
- 独特风格
- 性价比高
- 有免费额度

**成本**: $0.01-0.04/图

**配置**:
```json
{
  "leonardo": {
    "enabled": true,
    "api_key": "your-leonardo-api-key",
    "default_model": "leonardo-phoenix"
  }
}
```

---

## 配置步骤

### 1. 编辑模型配置文件

```bash
nano ~/.claude/skills/xhs-operator/CONFIG/image_models.json
```

### 2. 启用需要的模型

将对应模型的 `"enabled"` 设置为 `true`

### 3. 配置API密钥

在 `~/.claude/mcp_config.json` 中添加环境变量：

```json
{
  "mcpServers": {
    "integration-mcp": {
      "command": "python3",
      "args": ["/path/to/integration-mcp/src/workflow.py"],
      "env": {
        "STABILITY_API_KEY": "sk-your-key",
        "OPENAI_API_KEY": "sk-your-key",
        "REPLICATE_API_TOKEN": "r8-your-token",
        "HUGGINGFACE_API_KEY": "hf-your-key",
        "IDEOGRAM_API_KEY": "your-key",
        "LEONARDO_API_KEY": "your-key"
      }
    }
  }
}
```

### 4. 选择默认策略

在 `image_models.json` 中设置：

```json
{
  "default_model": "stability",
  "model_selection_strategy": "cost_first"
}
```

可选策略：
- `cost_first` - 成本优先
- `quality_first` - 质量优先
- `speed_first` - 速度优先
- `balanced` - 平衡模式

---

## 使用示例

### 基础使用

**使用默认模型（成本优先）**
```
/xhs 发布 春季穿搭推荐
# 自动选择最便宜的可用模型
```

**指定模型**
```
/xhs 发布 春季穿搭推荐 -模型 stability
# 使用Stability AI
```

**指定策略**
```
/xhs 发布 春季穿搭推荐 -策略 quality_first
# 使用质量最好的模型
```

### 高级使用

**指定子模型**
```
/xhs 发布 春季穿搭推荐 -模型 stability -子model sd-turbo
# 使用SD Turbo（快速版）
```

**组合使用**
```
/xhs 发布 春季穿搭推荐 -模型 dall-e -风格 治愈
# 使用DALL-E生成治愈风格
```

**批量指定模型**
```
/xhs 批量 5 春季穿搭 -模型 replicate
# 批量使用Replicate（成本较低）
```

---

## 模型选择建议

### 按场景选择

| 场景 | 推荐模型 | 原因 |
|------|---------|------|
| **日常发布** | Stability SDXL | 质量好，成本适中 |
| **批量生成** | Stability Turbo / Replicate | 速度快，成本低 |
| **重要内容** | DALL-E 3 / SD3 | 质量最高 |
| **文字海报** | Ideogram | 文字渲染优秀 |
| **测试开发** | Hugging Face | 完全免费 |

### 按预算选择

**免费方案**:
- 主用: Hugging Face (SDXL Turbo)
- 备用: Ideogram (免费额度)

**低成本方案** (<$10/月):
- 主用: Replicate SDXL
- 备用: Stability Turbo
- 重要: DALL-E 2

**平衡方案** ($10-50/月):
- 主用: Stability SDXL
- 重要: SD3
- 批量: Turbo

**高质量方案** ($50+/月):
- 日常: Stability SD3
- 重要: DALL-E 3
- 特殊: Ideogram (文字)

---

## 成本估算

### 月度成本计算

假设每天发布5篇笔记，每篇1张图片：

**免费方案**:
- Hugging Face: $0
- **总计**: $0/月

**低成本方案**:
- Replicate SDXL: $0.005 × 150 = $0.75
- Stability Turbo: $0.015 × 150 = $2.25
- **总计**: ~$3/月

**平衡方案**:
- Stability SDXL: $0.03 × 100 = $3.00
- Stability Turbo: $0.015 × 30 = $0.45
- SD3: $0.06 × 20 = $1.20
- **总计**: ~$5/月

**高质量方案**:
- SD3: $0.06 × 80 = $4.80
- DALL-E 3: $0.08 × 50 = $4.00
- DALL-E 2: $0.03 × 20 = $0.60
- **总计**: ~$10/月

### 优化建议

1. **使用免费模型测试**: 在Hugging Face上测试prompt
2. **批量用便宜的**: Turbo/Replicate用于批量
3. **重要的用贵的**: SD3/DALL-E 3用于重要内容
4. **启用fallback**: 配置fallback顺序确保可用性

---

## 故障排除

### 问题1: 模型不可用

**症状**: 提示 "No suitable model found"

**解决**:
1. 检查模型是否启用: `"enabled": true`
2. 检查API密钥是否配置
3. 查看日志: `tail -f ~/.refly/mcp-servers/integration-mcp/data/integration.log`

### 问题2: 生成失败

**症状**: 图像生成报错

**解决**:
1. 检查API余额
2. 验证API密钥
3. 尝试简化prompt
4. 切换到备用模型

### 问题3: 质量不满意

**解决**:
1. 切换到更高质量的模型
2. 优化prompt
3. 调整参数（steps, cfg_scale等）
4. 尝试不同的风格

### 问题4: 成本过高

**解决**:
1. 切换到 `cost_first` 策略
2. 使用免费模型（Hugging Face）
3. 启用Turbo版本
4. 减少生成数量

---

## API密钥获取

### Stability AI
1. 访问: https://platform.stability.ai/
2. 注册账号
3. 在Dashboard获取API Key
4. 免费额度: $25

### OpenAI
1. 访问: https://platform.openai.com/
2. 注册账号
3. 创建API Key
4. 按使用量付费

### Replicate
1. 访问: https://replicate.com/
2. GitHub账号登录
3. 创建API Token
4. 按使用量付费

### Hugging Face
1. 访问: https://huggingface.co/
2. 注册账号
3. 创建Access Token（可选）
4. 大部分模型免费

### Ideogram
1. 访问: https://ideogram.ai/
2. 注册账号
3. 在设置中获取API Key
4. 有免费额度

### Leonardo AI
1. 访问: https://leonardo.ai/
2. 注册账号
3. 在API设置中获取Key
4. 有免费额度

---

## 最佳实践

### 1. 模型配置

```json
{
  "default_model": "stability",
  "model_selection_strategy": "cost_first",
  "models": {
    "stability": {
      "enabled": true,
      "default_model": "sd3"  // 平衡质量和成本
    },
    "replicate": {
      "enabled": true,  // 启用作备用
      "default_model": "sdxl"
    },
    "huggingface": {
      "enabled": true  // 免费fallback
    }
  }
}
```

### 2. Fallback配置

确保至少配置3个模型作为fallback：

```json
{
  "fallback_order": [
    "huggingface",    // 免费先试
    "replicate",      // 便宜
    "stability"       // 质量
  ]
}
```

### 3. 监控成本

定期检查各模型的使用情况和成本：

```
/xhs 分析 模型成本
# 查看各模型使用统计
```

---

## 更新日志

**v1.1.0** (2025-02-06)
- ✅ 添加多模型支持
- ✅ 支持6个图像生成服务
- ✅ 智能模型选择策略
- ✅ 成本估算功能
- ✅ Fallback机制

---

**需要帮助？**

- 查看模型配置: `~/.claude/skills/xhs-operator/CONFIG/image_models.json`
- 查看完整文档: `README.md`
- 提交Issue: https://github.com/ffan008/xhs-ai-operator/issues
