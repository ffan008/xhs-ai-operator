# 🎉 多模型图像生成功能 - 更新总结

## 更新内容

### ✨ 新增功能

#### 1. 多模型图像生成支持

现在系统支持**6个主流图像生成服务**：

| 模型 | 特点 | 成本 | 状态 |
|------|------|------|------|
| **Stability AI** | 质量高，风格多样 | $0.01-0.08/图 | ✅ 默认 |
| **OpenAI DALL-E** | 理解力强，质量优秀 | $0.02-0.12/图 | 🔧 可选 |
| **Replicate** | 模型丰富，性价比高 | $0.002-0.06/图 | 🔧 可选 |
| **Hugging Face** | 开源免费 | 免费 | 🔧 可选 |
| **Ideogram** | 文字渲染优秀 | 免费/付费 | 🔧 可选 |
| **Leonardo AI** | 风格独特 | $0.01-0.04/图 | 🔧 可选 |

#### 2. 智能模型选择策略

- **cost_first** - 成本优先（默认）
- **quality_first** - 质量优先
- **speed_first** - 速度优先
- **balanced** - 平衡模式

#### 3. 自动Fallback机制

当主模型不可用时，自动切换到备用模型，确保服务可用性。

---

## 文件变更

### 新增文件

1. **integration-mcp/src/image_model_manager.py** (600+ 行)
   - 图像模型管理器
   - 模型选择逻辑
   - 参数生成器
   - 成本估算

2. **xhs-operator/CONFIG/image_models.json**
   - 模型配置文件
   - 6个服务的配置
   - 策略配置
   - 成本估算

3. **MULTI_MODEL_GUIDE.md** (500+ 行)
   - 完整配置指南
   - 使用示例
   - 成本估算
   - 故障排除

### 更新文件

1. **integration-mcp/src/workflow.py**
   - 添加7个新工具
   - 模型选择功能
   - 多模型生成支持

2. **xhs-operator/PROMPTS/image_generation.md**
   - 添加模型选择说明
   - 策略使用示例

3. **README.md**
   - 核心特性介绍
   - 配置说明
   - 文档链接

---

## 使用示例

### 基础使用

**使用默认策略（成本优先）**
```bash
/xhs 发布 春季穿搭推荐
# 自动选择最便宜的可用模型
```

**指定模型**
```bash
/xhs 发布 春季穿搭推荐 -模型 stability
# 使用Stability AI
```

**指定策略**
```bash
/xhs 发布 春季穿搭推荐 -策略 quality_first
# 使用质量最好的模型
```

### 高级使用

**指定子模型**
```bash
/xhs 发布 春季穿搭推荐 -model stability -submodel sd-turbo
# 使用SD Turbo（快速版）
```

**组合使用**
```bash
/xhs 发布 春季穿搭推荐 -model dall-e -style 治愈
# 使用DALL-E生成治愈风格
```

---

## 配置步骤

### 1. 编辑模型配置

```bash
nano ~/.claude/skills/xhs-operator/CONFIG/image_models.json
```

### 2. 启用模型

将所需模型的 `"enabled"` 设为 `true`：

```json
{
  "stability": {
    "enabled": true  // 启用Stability AI
  },
  "replicate": {
    "enabled": true  // 启用Replicate
  }
}
```

### 3. 配置API密钥

在 `~/.claude/mcp_config.json` 添加：

```json
{
  "mcpServers": {
    "integration-mcp": {
      "env": {
        "STABILITY_API_KEY": "sk-your-key",
        "OPENAI_API_KEY": "sk-your-key",
        "REPLICATE_API_TOKEN": "r8-your-token"
      }
    }
  }
}
```

### 4. 选择默认策略

```json
{
  "model_selection_strategy": "cost_first"
}
```

---

## API密钥获取

### Stability AI
- 网站: https://platform.stability.ai/
- 免费额度: $25
- 成本: $0.01-0.08/图

### OpenAI
- 网站: https://platform.openai.com/
- 按量付费
- 成本: $0.02-0.12/图

### Replicate
- 网站: https://replicate.com/
- 免费试用
- 成本: $0.002-0.06/图

### Hugging Face
- 网站: https://huggingface.co/
- 大部分免费
- 成本: 免费

### Ideogram
- 网站: https://ideogram.ai/
- 有免费额度
- 成本: 免费/付费

### Leonardo AI
- 网站: https://leonardo.ai/
- 有免费额度
- 成本: $0.01-0.04/图

---

## 成本估算

### 每日5篇笔记，每月成本

| 方案 | 主用模型 | 月成本 | 说明 |
|------|---------|--------|------|
| **免费方案** | Hugging Face | $0 | 需要自行部署 |
| **低成本** | Replicate SDXL | ~$3 | 性价比最高 |
| **平衡方案** | Stability SDXL | ~$5 | 质量成本平衡 |
| **高质量** | SD3 + DALL-E 3 | ~$10 | 最佳质量 |

---

## 新增工具

### 1. list_image_models
列出所有可用模型

```python
await list_image_models(include_disabled=False)
```

### 2. select_image_model
根据策略选择模型

```python
await select_image_model(
    strategy="cost_first",
    preferred_model=None,
    aspect_ratio="3:4"
)
```

### 3. get_model_config
获取特定模型配置

```python
await get_model_config(model_id="stability")
```

### 4. enable_image_model / disable_image_model
启用/禁用模型

```python
await enable_image_model(model_id="stability")
await disable_image_model(model_id="openai")
```

### 5. generate_image_with_model
使用指定模型生成图像

```python
await generate_image_with_model(
    prompt="beautiful spring landscape",
    model_id="stability",
    aspect_ratio="3:4",
    strategy="cost_first"
)
```

---

## 文档更新

- ✅ README.md - 添加多模型说明
- ✅ MULTI_MODEL_GUIDE.md - 完整配置指南（新建）
- ✅ PROMPTS/image_generation.md - 更新模板说明
- ✅ image_models.json - 模型配置文件（新建）

---

## 技术实现

### 架构设计

```
用户请求
    ↓
Skill解析
    ↓
integration-mcp
    ↓
ImageModelManager
    ↓
策略选择 → 模型筛选 → 参数生成 → API调用
    ↓
图像返回
```

### 核心类

**ImageModelManager**
- `list_models()` - 列出所有模型
- `select_model()` - 选择模型
- `get_model_params()` - 生成参数
- `estimate_cost()` - 估算成本
- `enable_model()` / `disable_model()` - 启用/禁用

---

## 后续计划

### 短期
- [ ] 添加更多模型（Midjourney、Runway等）
- [ ] 实现模型性能监控
- [ ] 添加批量优化功能

### 中期
- [ ] 支持自定义模型参数
- [ ] 图像质量评分
- [ ] 自动prompt优化

### 长期
- [ ] 模型训练微调
- [ ] A/B测试功能
- [ ] 成本预算管理

---

## 常见问题

**Q: 默认使用哪个模型？**
A: 默认使用Stability AI的SD3模型，策略为成本优先。

**Q: 如何切换到免费模型？**
A: 启用Hugging Face模型并设置为fallback首位。

**Q: 可以同时使用多个模型吗？**
A: 可以通过指定 `-model` 参数选择，或让系统根据策略自动选择。

**Q: 如何查看成本？**
A: 使用 `estimate_cost()` 方法或查看配置文件中的 `cost_estimate`。

**Q: 模型失败会怎样？**
A: 系统会自动fallback到备用模型，确保服务可用。

---

## 反馈与支持

- 📖 文档: [MULTI_MODEL_GUIDE.md](MULTI_MODEL_GUIDE.md)
- 🐛 问题反馈: https://github.com/ffan008/xhs-ai-operator/issues
- 💬 讨论: https://github.com/ffan008/xhs-ai-operator/discussions

---

**更新日期**: 2025-02-06
**版本**: v1.1.0
**提交**: 2f8e98d
