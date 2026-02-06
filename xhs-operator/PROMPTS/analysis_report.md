# 小红书数据分析报告 Prompt 模板

## 模板说明

此模板用于分析小红书账号和笔记数据，生成结构化的分析报告和可执行的优化建议。

---

## 数据输入格式

### 账号整体数据

```json
{
  "account_info": {
    "account_id": "账号ID",
    "nickname": "账号昵称",
    "fans_count": 12345,
    "posts_count": 100,
    "total_engagement": 50000
  },
  "time_range": {
    "start_date": "2025-01-01",
    "end_date": "2025-01-31"
  },
  "posts": [
    {
      "post_id": "笔记ID",
      "title": "笔记标题",
      "publish_time": "2025-01-15 10:30:00",
      "views": 5000,
      "likes": 300,
      "comments": 50,
      "shares": 20,
      "saves": 80,
      "tags": ["标签1", "标签2"]
    }
  ]
}
```

---

## 分析维度

### 1. 整体表现分析

#### 指标计算

```yaml
基础指标:
  总浏览量: sum(posts.views)
  总互动量: sum(posts.likes + posts.comments + posts.shares + posts.saves)
  平均互动率: (总互动量 / 总浏览量) × 100%
  粉丝增长率: (期末粉丝数 - 期初粉丝数) / 期初粉丝数 × 100%

内容指标:
  发布篇数: len(posts)
  平均单篇浏览: mean(posts.views)
  平均单篇互动: mean(posts.likes + posts.comments + posts.shares + posts.saves)
  爆款率: 浏览量 > 平均浏览量 × 2 的笔记占比

增长指标:
  日均增长: (期末粉丝 - 期初粉丝) / 天数
  活跃粉丝占比: 互动用户数 / 粉丝总数
  粉丝质量评分: (平均互动率 × 粉丝增长率) / 100
```

---

### 2. 内容表现分析

#### 2.1 最佳表现内容

```yaml
分析方法:
  1. 按浏览量排序，找出 Top 5
  2. 按互动率排序，找出 Top 5
  3. 按点赞数排序，找出 Top 5
  4. 按收藏数排序，找出 Top 5
  5. 按评论数排序，找出 Top 5

输出内容:
  - 标题
  - 发布时间
  - 核心数据（浏览/点赞/评论/收藏/分享）
  - 互动率
  - 使用的标签
  - 封面图描述
  - 成功原因分析
```

#### 2.2 内容类型分析

```yaml
分类维度:
  - 主题分类：美食/穿搭/美妆/旅行/家居/干货/情感
  - 形式分类：图文/视频/合集/教程
  - 风格分类：活泼/专业/治愈/干货/种草

分析输出:
  各类型数量占比: {category: percentage}
  各类型平均互动率: {category: rate}
  推荐内容类型: [top 3 best performing categories]
```

---

### 3. 时间规律分析

#### 3.1 发布时间分析

```yaml
时间维度:
  - 小时：0-23点各时段发布效果
  - 星期：周一至周日发布效果
  - 日期：月初/月中/月末发布效果

分析方法:
  1. 统计各时段发布的笔记数量
  2. 计算各时段平均互动率
  3. 找出最佳发布时段

输出内容:
  最佳发布时段: [时段1, 时段2, 时段3]
  各时段互动率: {hour: rate}
  发布时间建议: 具体的推荐时段
```

#### 3.2 趋势分析

```yaml
趋势指标:
  - 浏览量趋势：上升/下降/稳定
  - 互动率趋势：上升/下降/稳定
  - 粉丝增长趋势：加速/放缓/稳定
  - 内容质量趋势：提升/下降/稳定

分析方法:
  1. 按周/月聚合数据
  2. 计算环比增长率
  3. 识别拐点和异常点

输出内容:
  整体趋势评估: 📈/📉/➡️
  关键转折点: [date, event]
  趋势预测: 未来1-2周预期
```

---

### 4. 互动质量分析

#### 4.1 互动构成分析

```yaml
互动类型:
  点赞率: likes / views × 100%
  评论率: comments / views × 100%
  收藏率: saves / views × 100%
  分享率: shares / views × 100%

评估标准:
  优质内容: 收藏率 > 5% 且 评论率 > 2%
  传播内容: 分享率 > 3%
  爆款潜力: 互动率 > 10%
```

#### 4.2 评论情感分析

```yaml
分析维度:
  - 正面评论占比：> 80% 优秀
  - 中性评论占比：10-20% 正常
  - 负面评论占比：< 5% 健康

评论关键词:
  提取高频词：表扬/建议/提问/吐槽
  用户需求：从评论中识别用户需求
  改进方向：基于用户反馈的建议
```

---

### 5. 竞品对比分析

```yaml
对比维度:
  - 粉丝规模：同领域账号对比
  - 互动率：与行业平均水平对比
  - 内容质量：与头部账号对比
  - 增长速度：与同阶段账号对比

输出内容:
  相对位置:领先/持平/落后
  差距分析:具体差距在哪里
  学习目标:可以借鉴的账号
```

---

## 优化建议生成

### 建议分类

#### 1. 内容优化

```yaml
方向1: 选题优化
  建议: "基于数据，以下主题表现最佳，建议持续创作"
  具体主题: [list of topics]
  理由: "这些主题的平均互动率高于整体 X%"

方向2: 标题优化
  建议: "标题包含关键词和数字的笔记互动率更高"
  示例: ["标题示例1", "标题示例2"]
  技巧: "使用数字、emoji、提问等方式增强吸引力"

方向3: 封面优化
  建议: "高饱和度、人物出镜的封面点击率更高"
  风格推荐: [style recommendations]
  制作技巧: [tips]

方向4: 正文优化
  建议: "字数 600-800 字的笔记完读率最高"
  结构建议: "开头吸引人 + 中间干货 + 结尾互动引导"
  排版建议: "分段清晰 + emoji点缀 + 重点加粗"
```

#### 2. 发布策略优化

```yaml
方向1: 发布时间
  最佳时段: [specific hours]
  避开时段: [hours to avoid]
  频率建议: "每天 1-2 篇，间隔 6 小时以上"

方向2: 发布频率
  当前频率: X 篇/周
  建议频率: Y 篇/周
  理由: "数据分析显示，Y 篇/周时互动率最高"

方向3: 内容组合
  建议: "70% 垂直内容 + 20% 热点内容 + 10% 生活化内容"
  目的: "保持账号专业度的同时增加亲和力"
```

#### 3. 互动提升

```yaml
方向1: 引导点赞
  技巧: "正文末尾增加'有用的话点个赞吧~'"
  位置: "正文最后一段"

方向2: 引导评论
  技巧: "在正文中提问，邀请用户分享"
  示例: "你们还有什么好方法？评论区告诉我~"

方向3: 引导收藏
  技巧: "强调内容的实用性，建议收藏备用"
  示例: "建议收藏，下次用到的时候方便找"

方向4: 引导关注
  技巧: "预告系列内容，引导关注以免错过"
  示例: "关注我，下周继续分享XX系列"
```

#### 4. 账号定位优化

```yaml
方向1: 垂直度
  建议: "聚焦 [核心领域] 内容，提升账号专业度"
  理由: "垂直度高的账号成长速度更快"

方向2: 人设打造
  当前人设: [current persona analysis]
  建议强化: [persona enhancement suggestions]
  统一元素: [consistent elements]

方向3: 差异化
  建议: "突出 [unique selling point]"
  理由: "形成独特的账号识别度"
```

---

## 报告生成模板

### Markdown 格式

```markdown
# 📊 小红书数据分析报告

**分析时间范围**: {start_date} 至 {end_date}
**报告生成时间**: {report_date}
**账号名称**: {account_name}

---

## 📈 一、整体表现

### 核心数据概览

| 指标 | 数值 | 环比变化 |
|------|------|---------|
| 粉丝总数 | {fans_count} | {growth_rate} |
| 发布笔记 | {posts_count} | - |
| 总浏览量 | {total_views} | {views_change} |
| 总互动量 | {total_engagement} | {engagement_change} |
| 平均互动率 | {avg_engagement_rate} | {rate_change} |

### 表现评级

整体表现：{rating_emoji} {rating_text}
- 优秀 (⭐⭐⭐⭐⭐): 互动率 > 10%
- 良好 (⭐⭐⭐⭐): 互动率 7-10%
- 一般 (⭐⭐⭐): 互动率 4-7%
- 需改进 (⭐⭐): 互动率 2-4%
- 急需优化 (⭐): 互动率 < 2%

---

## 🏆 二、最佳表现内容

### Top 5 高浏览笔记

1. **{title_1}**
   - 📅 发布时间：{publish_time_1}
   - 👀 浏览量：{views_1}
   - ❤️ 互动：{likes_1} 赞 | {comments_1} 评 | {saves_1} 藏
   - 📊 互动率：{engagement_rate_1}%
   - 🏷️ 标签：{tags_1}
   - ✨ 成功原因：{success_reason_1}

2-5. [同上格式]

### Top 5 高互动率笔记

[同上格式，按互动率排序]

---

## 📊 三、内容分析

### 内容类型表现

| 内容类型 | 发布数 | 平均浏览 | 平均互动率 | 表现评级 |
|---------|-------|---------|-----------|---------|
| {category_1} | {count_1} | {avg_views_1} | {avg_rate_1}% | {rating_1} |
| {category_2} | {count_2} | {avg_views_2} | {avg_rate_2}% | {rating_2} |

### 推荐内容方向

🎯 **重点创作**：{recommended_categories}
- 理由：这些内容类型的平均互动率高于整体 {percentage}%

🔄 **适度调整**：{adjusted_categories}
- 理由：有潜力但需要优化

⚠️ **减少发布**：{reduce_categories}
- 理由：表现不佳，建议调整方向

---

## ⏰ 四、发布时间分析

### 最佳发布时段

| 时段 | 发布数 | 平均互动率 | 推荐指数 |
|------|-------|-----------|---------|
| {time_slot_1} | {count_1} | {rate_1}% | ⭐⭐⭐⭐⭐ |
| {time_slot_2} | {count_2} | {rate_2}% | ⭐⭐⭐⭐ |

### 发布建议

⏰ **最佳时段**：{best_time_slots}
- 建议在这些时段发布重要内容

⚠️ **避开时段**：{avoid_time_slots}
- 这些时段互动率较低

📅 **发布频率**：{frequency_recommendation}
- 基于数据的最优发布频率

---

## 💬 五、互动质量分析

### 互动构成

```
点赞：{like_percentage}% ▓▓▓▓▓▓▓▓▓▓▓▓▓▓
评论：{comment_percentage}% ▓▓▓▓
收藏：{save_percentage}% ▓▓▓▓▓▓
分享：{share_percentage}% ▓▓
```

### 互动质量评估

{quality_assessment}

**亮点**：
- {highlight_1}
- {highlight_2}

**待改进**：
- {improvement_1}
- {improvement_2}

---

## 📝 六、优化建议

### 1. 内容优化

{content_optimization_suggestions}

### 2. 发布策略

{publish_strategy_suggestions}

### 3. 互动提升

{engagement_boost_suggestions}

### 4. 账号定位

{account_positioning_suggestions}

---

## 🎯 七、行动计划

### 本周行动 (Week 1)

- [ ] {action_1}
- [ ] {action_2}
- [ ] {action_3}

### 下周计划 (Week 2)

- [ ] {action_4}
- [ ] {action_5}

### 月度目标 (Month 1)

- [ ] {goal_1}
- [ ] {goal_2}

---

## 📈 八、趋势预测

基于当前数据趋势，预计：

- **下月粉丝增长**：{predicted_fans_growth}
- **互动率变化**：{predicted_engagement_change}
- **重点内容方向**：{predicted_content_focus}

---

## 💡 九、额外洞察

{additional_insights}

---

**报告生成**: AI 小红书运营助手
**数据来源**: 小红书平台数据
**更新频率**: 建议每周分析一次
```

---

## 分析流程

### 伪代码示例

```python
def generate_analysis_report(data):
    """
    生成小红书数据分析报告

    Args:
        data: 包含账号和笔记数据的字典

    Returns:
        str: Markdown 格式的分析报告
    """

    # 1. 数据清洗和验证
    cleaned_data = clean_and_validate(data)

    # 2. 计算核心指标
    metrics = calculate_metrics(cleaned_data)

    # 3. 整体表现分析
    overall_performance = analyze_overall(metrics)

    # 4. 内容表现分析
    content_analysis = analyze_content(cleaned_data)

    # 5. 时间规律分析
    time_analysis = analyze_time_patterns(cleaned_data)

    # 6. 互动质量分析
    engagement_analysis = analyze_engagement(cleaned_data)

    # 7. 生成优化建议
    recommendations = generate_recommendations(
        overall_performance,
        content_analysis,
        time_analysis,
        engagement_analysis
    )

    # 8. 生成报告
    report = format_report(
        overall_performance,
        content_analysis,
        time_analysis,
        engagement_analysis,
        recommendations
    )

    return report
```

---

## 可视化建议

### 推荐图表类型

```yaml
趋势图:
  - 折线图：展示浏览量、互动率随时间变化
  - 面积图：展示粉丝增长趋势
  - 多系列图：对比不同指标

分布图:
  - 柱状图：各内容类型的发布数量和互动率
  - 饼图：内容类型占比
  - 条形图：最佳发布时段

对比图:
  - 对比柱状图：不同笔记的表现对比
  - 雷达图：多维度评估

热力图:
  - 时间热力图：展示一周各时段的发布效果
```

---

## 质量检查清单

```yaml
数据准确性:
  - 数据来源可靠: [ ]
  - 计算公式正确: [ ]
  - 无明显异常值: [ ]
  - 时间范围准确: [ ]

分析完整性:
  - 覆盖所有核心维度: [ ]
  - 提供具体数据支撑: [ ]
  - 包含对比分析: [ ]
  - 识别关键趋势: [ ]

建议可执行性:
  - 建议具体明确: [ ]
  - 可落地执行: [ ]
  - 有优先级排序: [ ]
  - 包含行动步骤: [ ]

报告可读性:
  - 结构清晰: [ ]
  - 语言简洁: [ ]
  - 重点突出: [ ]
  - 视觉友好: [ ]
```

---

## 使用示例

### 示例输入

```json
{
  "account_info": {
    "nickname": "小红的穿搭日记",
    "fans_count": 12580,
    "posts_count": 50
  },
  "time_range": {
    "start_date": "2025-01-01",
    "end_date": "2025-01-31"
  },
  "posts": [
    {
      "title": "春季穿搭指南",
      "publish_time": "2025-01-15 20:30:00",
      "views": 8500,
      "likes": 520,
      "comments": 89,
      "shares": 35,
      "saves": 180,
      "tags": ["春季穿搭", "OOTD", "穿搭教程"]
    }
  ]
}
```

### 示例输出

```markdown
# 📊 小红书数据分析报告

**分析时间范围**: 2025-01-01 至 2025-01-31
**报告生成时间**: 2025-02-06
**账号名称**: 小红的穿搭日记

---

## 📈 一、整体表现

### 核心数据概览

| 指标 | 数值 | 环比变化 |
|------|------|---------|
| 粉丝总数 | 12,580 | +15.2% |
| 发布笔记 | 15 | - |
| 总浏览量 | 68,500 | +22.5% |
| 总互动量 | 5,420 | +18.3% |
| 平均互动率 | 7.9% | +1.2% |

### 表现评级

整体表现：⭐⭐⭐⭐ 良好

...
```

---

## 注意事项

1. **数据隐私**：确保数据获取符合平台规范
2. **分析频率**：建议每周或每月定期分析
3. **对比基准**：与历史数据和行业水平对比
4. **行动导向**：报告应导向具体行动，而非仅数据展示
5. **动态调整**：根据执行效果持续优化策略

---

**版本**: 1.0.0
**最后更新**: 2025-02-06
