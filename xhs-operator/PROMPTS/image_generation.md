# 小红书图像生成 Prompt 模板

## 模板说明

此模板用于生成适配小红书平台的配图，包括封面图和内容配图。所有图片遵循 3:4 竖屏比例，符合小红书最佳实践。

---

## 多模型支持

本系统支持多个图像生成模型，可根据需求灵活选择：

### 可用模型

| 模型 | 特点 | 适用场景 | 成本 |
|------|------|---------|------|
| **Stability AI** | 质量高，风格多样 | 通用场景 | 中 |
| **OpenAI DALL-E** | 理解能力强，质量优秀 | 复杂场景 | 高 |
| **Replicate** | 模型丰富，性价比高 | 平衡选择 | 低-中 |
| **Hugging Face** | 开源免费 | 测试开发 | 免费 |
| **Ideogram** | 擅长文字渲染 | 文字海报 | 免费-付费 |
| **Leonardo AI** | 风格独特，质量好 | 艺术创作 | 低-中 |

### 模型选择策略

```yaml
# 成本优先（默认）
strategy: cost_first
# 推荐模型顺序: Hugging Face → Replicate → Leonardo → Stability → OpenAI

# 质量优先
strategy: quality_first
# 推荐模型顺序: OpenAI → Stability → Ideogram → Replicate → Leonardo

# 速度优先
strategy: speed_first
# 推荐模型顺序: Hugging Face → Stability → Replicate → Leonardo → OpenAI

# 平衡模式
strategy: balanced
# 综合考虑质量、速度和成本
```

### 使用方式

**1. 默认策略（成本优先）**
```
/xhs 发布 春游穿搭
# 系统自动选择性价比最高的模型
```

**2. 指定模型**
```
/xhs 发布 春游穿搭 -模型 stability
# 使用Stability AI生成
```

**3. 指定策略**
```
/xhs 发布 春游穿搭 -策略 quality_first
# 使用质量最高的模型
```

**4. 指定子模型**
```
/xhs 发布 春游穿搭 -模型 stability -子模型 sdxl
# 使用Stability AI的SDXL模型
```

---

## 基础配置

### 图像规格
```yaml
aspect_ratio: "3:4"  # 小红书标准比例
width: 1080
height: 1440
format: "PNG"
quality: "high"
```

### 支持的风格
- **简约风格** (minimalist): 干净、简洁、留白
- **插画风格** (illustration): 手绘、卡通、扁平化
- **摄影风格** (photography): 真实、自然、生活化
- **艺术风格** (artistic): 创意、设计感、抽象

---

## Prompt 构建规则

### 基础结构

```
[主体描述] + [风格修饰] + [环境/背景] + [光影效果] + [构图方式] + [质量关键词]
```

### 示例

```
Prompt: "A beautiful spring landscape with cherry blossoms in full bloom,
soft pink and white flowers, blue sky background, natural sunlight,
wide angle shot, high quality, detailed, 8K resolution"

中文: "盛开的樱花春日风景，粉白色花朵，蓝天背景，
自然光，广角镜头，高质量，细节丰富，8K分辨率"
```

---

## 分类 Prompt 模板

### 1. 美食类 (Food & Beverage)

#### 1.1 简约风格
```
英文:
Professional food photography of {dish_name}, clean white background,
soft natural lighting, top-down or 45-degree angle,
minimalist composition, garnish with {garnish_items},
high contrast, appetizing, restaurant quality, sharp focus

中文:
专业美食摄影，{菜品名称}，干净的白色背景，
柔和自然光，俯拍或45度角，
简约构图，装饰{配菜}，
高对比度，诱人，餐厅品质，清晰对焦
```

**示例**：
```
Prompt: "Professional food photography of a fresh avocado toast,
clean white background, soft natural lighting, top-down angle,
minimalist composition, garnish with cherry tomatoes and microgreens,
high contrast, appetizing, restaurant quality, sharp focus"
```

#### 1.2 生活化风格
```
英文:
Cozy home-cooked meal photography of {dish_name},
warm indoor lighting, wooden table texture,
candid casual style,用餐场景,
soft bokeh background, inviting atmosphere,
lifestyle photography, natural and authentic

中文:
温馨家常菜摄影，{菜品名称}，
温暖的室内光，木质桌纹理，
随意的生活风格，用餐场景，
柔和虚化背景，诱人氛围，
生活方式摄影，自然真实
```

**示例**：
```
Prompt: "Cozy home-cooked meal photography of a steaming hot pot,
warm indoor lighting, wooden table texture,
candid casual style, family dining scene,
soft bokeh background, inviting atmosphere,
lifestyle photography, natural and authentic"
```

---

### 2. 穿搭类 (Fashion & OOTD)

#### 2.1 街拍风格
```
英文:
Street style photography of {outfit_description},
urban city background, natural daylight,
candid pose, fashion magazine quality,
trendy and chic, sharp focus on outfit,
blurred background, high fashion aesthetic

中文:
街拍风格摄影，{穿搭描述}，
城市背景，自然日光，
随意姿势，时尚杂志品质，
潮流别致，焦点在服装，
虚化背景，高级时尚美学
```

**示例**：
```
Prompt: "Street style photography of spring outfit,
white blouse and blue jeans combo, urban city background,
natural daylight, candid pose, fashion magazine quality,
trendy and chic, sharp focus on outfit,
blurred background, high fashion aesthetic"
```

#### 2.2 平面风格
```
英文:
Fashion flat lay of {clothing_items},
clean background (white/light gray/minimal color),
professional styling, accessories arranged,
editorial layout, high-end brand catalog style,
perfect lighting, crisp and clean

中文:
时尚平铺拍摄，{服装单品}，
干净的背景（白色/浅灰/简约色），
专业造型，配饰搭配，
杂志排版，高端品牌目录风格，
完美光线，清晰干净
```

**示例**：
```
Prompt: "Fashion flat lay of spring wardrobe essentials,
white blouse, denim jacket, floral dress,
clean light gray background,
professional styling, accessories arranged,
editorial layout, high-end brand catalog style,
perfect lighting, crisp and clean"
```

---

### 3. 美妆类 (Beauty & Makeup)

#### 3.1 产品特写
```
英文:
Close-up product photography of {beauty_product},
elegant reflective surface, soft studio lighting,
luxury aesthetic, minimal composition,
brand name visible, premium packaging,
professional commercial photography, sharp focus

中文:
产品特写摄影，{美妆产品}，
优雅反光表面，柔和影棚光，
奢华美学，简约构图，
品牌名称可见，高级包装，
专业商业摄影，清晰对焦
```

**示例**：
```
Prompt: "Close-up product photography of luxury lipstick,
elegant reflective surface, soft studio lighting,
luxury aesthetic, minimal composition,
brand packaging visible, premium design,
professional commercial photography, sharp focus"
```

#### 3.2 妆容展示
```
英文:
Beauty portrait photography, {makeup_style},
professional model, soft flattering lighting,
clean background, natural makeup look,
flawless complexion, fashionable,
editorial beauty shot, high quality

中文:
美妆人像摄影，{妆容风格}，
专业模特，柔和讨喜的光线，
干净背景，自然妆容，
无瑕肌肤，时尚，
杂志美妆大片，高质量
```

**示例**：
```
Prompt: "Beauty portrait photography, natural spring makeup look,
professional model, soft flattering lighting,
clean background, natural makeup look,
flawless complexion, fashionable,
editorial beauty shot, high quality"
```

---

### 4. 旅行类 (Travel & Scenery)

#### 4.1 风景大片
```
英文:
Breathtaking landscape photography of {location/scenery},
golden hour lighting (sunrise or sunset),
wide angle shot, vibrant colors,
epic composition, travel magazine quality,
high resolution, atmospheric and cinematic

中文:
壮丽风景摄影，{地点/景色}，
黄金时刻光线（日出或日落），
广角镜头，鲜艳色彩，
史诗级构图，旅行杂志品质，
高分辨率，氛围感和电影感
```

**示例**：
```
Prompt: "Breathtaking landscape photography of cherry blossom valley,
golden hour lighting at sunset,
wide angle shot, vibrant pink colors,
epic composition, travel magazine quality,
high resolution, atmospheric and cinematic"
```

#### 4.2 旅行打卡
```
英文:
Travel lifestyle photography, {location},
candid shot of traveler enjoying the view,
natural authentic moment, landmark visible,
blue sky and good weather,
happy and relaxed atmosphere,
travel diary style

中文:
旅行生活方式摄影，{地点}，
旅行者享受风景的随意镜头，
自然真实的瞬间，地标可见，
蓝天好天气，
快乐轻松的氛围，
旅行日记风格
```

**示例**：
```
Prompt: "Travel lifestyle photography, famous spring temple,
candid shot of traveler enjoying the cherry blossoms,
natural authentic moment, landmark visible,
blue sky and good weather,
happy and relaxed atmosphere,
travel diary style"
```

---

### 5. 家居类 (Home & Decor)

#### 5.1 空间展示
```
英文:
Interior design photography of {room_type},
{design_style} style, natural light from window,
cozy and inviting atmosphere,
plants and decorations,
real estate or magazine quality,
wide angle, bright and airy

中文:
室内设计摄影，{房间类型}，
{设计风格}风格，窗边自然光，
舒适诱人氛围，
植物和装饰品，
房地产或杂志品质，
广角，明亮通透
```

**示例**：
```
Prompt: "Interior design photography of living room,
Scandinavian minimalist style, natural light from window,
cozy and inviting atmosphere,
indoor plants and simple decorations,
real estate or magazine quality,
wide angle, bright and airy"
```

#### 5.2 物品特写
```
英文:
Home decor product photography of {item},
stylish home setting, natural lighting,
lifestyle composition,
bokeh background, warm tones,
Pinterest aesthetic, interior design magazine quality

中文:
家居装饰产品摄影，{物品}，
时尚家居环境，自然光，
生活方式构图，
虚化背景，暖色调，
Pinterest美学，室内设计杂志品质
```

**示例**：
```
Prompt: "Home decor product photography of ceramic vase,
stylish living room setting, natural lighting,
lifestyle composition,
bokeh background, warm tones,
Pinterest aesthetic, interior design magazine quality"
```

---

### 6. 干货类 (Educational & Tips)

#### 6.1 图解教程
```
英文:
Clean infographic design about {topic},
modern illustration style, flat design,
pastel color palette, clear typography,
step-by-step visual guide,
professional instructional design,
engaging and easy to understand

中文:
清晰的图解设计，关于{主题}，
现代插画风格，扁平化设计，
柔和色彩调色板，清晰排版，
分步视觉指南，
专业教学设计，
引人入胜且易于理解
```

**示例**：
```
Prompt: "Clean infographic design about morning routine,
modern illustration style, flat design,
pastel color palette, clear typography,
step-by-step visual guide,
professional instructional design,
engaging and easy to understand"
```

#### 6.2 笔记风格
```
英文:
Styled note-taking layout, {topic},
handwritten aesthetic, clean notebook paper background,
colorful highlights and annotations,
studygram aesthetic, organized information,
bullet journal style, aesthetic and functional

中文:
样式化的笔记布局，{主题}，
手写美学，干净的笔记本纸张背景，
彩色高亮和注释，
学习美学，信息组织化，
子弹笔记风格，美学与功能兼备
```

**示例**：
```
Prompt: "Styled note-taking layout, time management tips,
handwritten aesthetic, clean notebook paper background,
colorful highlights and annotations,
studygram aesthetic, organized information,
bullet journal style, aesthetic and functional"
```

---

### 7. 情感类 (Emotional & Healing)

#### 7.1 治愈系场景
```
英文:
Healing and cozy scene, {mood/subject},
soft natural lighting, warm color tones,
dreamy atmosphere, shallow depth of field,
emotional and peaceful,
Japanese aesthetic, quiet and serene

中文:
治愈舒适场景，{情绪/主题}，
柔和自然光，暖色调，
梦幻氛围，浅景深，
情感宁静，
日式美学，安静祥和
```

**示例**：
```
Prompt: "Healing and cozy scene, reading alone in coffee shop,
soft natural lighting, warm color tones,
dreamy atmosphere, shallow depth of field,
emotional and peaceful,
Japanese aesthetic, quiet and serene"
```

#### 7.2 抽象意境
```
英文:
Abstract artistic composition representing {emotion/concept},
soft gradient colors, watercolor or digital art style,
ethereal and dreamlike, minimalist,
emotional resonance, poetic atmosphere,
fine art quality, meditative

中文:
抽象艺术构图，表现{情绪/概念}，
柔和渐变色彩，水彩或数字艺术风格，
空灵梦幻，简约主义，
情感共鸣，诗意氛围，
艺术品品质，冥想感
```

**示例**：
```
Prompt: "Abstract artistic composition representing self-love,
soft gradient colors in pink and peach,
watercolor art style,
ethereal and dreamlike, minimalist,
emotional resonance, poetic atmosphere,
fine art quality, meditative"
```

---

## 高级技巧

### 1. 颜色方案控制

```
色彩搭配建议：
- 春季：粉嫩色系（#FFB7B2, #B5EAD7, #E2F0CB）
- 夏季：明亮色系（#FF6F69, #FFCC5C, #88D8B0）
- 秋季：温暖色系（#E29578, #FFD166, #06D6A0）
- 冬季：冷色调（#118AB2, #073B4C, #EF476F）
- 治愈系：莫兰迪色（低饱和度灰调）
- 活泼系：马卡龙色（高饱和明亮色）
```

### 2. 光影效果

```
光线类型：
- 自然光（Natural Light）：真实、柔和
- 黄金时刻（Golden Hour）：温暖、浪漫
- 蓝调时刻（Blue Hour）：冷静、神秘
- 影棚光（Studio Light）：专业、清晰
- 侧光（Side Light）：立体感强
- 背光（Backlight）：剪影效果
```

### 3. 构图技巧

```
构图方式：
- 三分法（Rule of Thirds）：经典平衡
- 居中构图（Centered）：突出主体
- 对角线（Diagonal）：动感活力
- 框架构图（Frame）：层次感
- 留白（Negative Space）：简约高级
- 引导线（Leading Lines）：视觉引导
```

### 4. 质量关键词

```
必加关键词：
- high quality（高质量）
- sharp focus（清晰对焦）
- detailed（细节丰富）
- professional（专业）
- 8K resolution（8K分辨率）
- masterpiece（杰作）
- best quality（最佳质量）

可选关键词：
- trending on ArtStation（ArtStation热门）
- award winning（获奖作品）
- photorealistic（照片级真实）
- highly detailed（高度细节）
- digital art（数字艺术）
```

---

## Prompt 生成函数

### 伪代码示例

```python
def generate_image_prompt(topic, style="minimalist", category="general"):
    """
    生成小红书图片 Prompt

    Args:
        topic: 内容主题
        style: 图片风格 (minimalist/illustration/photography/artistic)
        category: 内容分类 (food/fashion/beauty/travel/home/education/emotional)

    Returns:
        str: Stability AI 使用的 Prompt
    """

    # 基础配置
    base_config = {
        "aspect_ratio": "3:4",
        "quality": "high quality, sharp focus, detailed, 8K resolution"
    }

    # 根据分类选择模板
    templates = {
        "food": get_food_prompt(style, topic),
        "fashion": get_fashion_prompt(style, topic),
        "beauty": get_beauty_prompt(style, topic),
        "travel": get_travel_prompt(style, topic),
        "home": get_home_prompt(style, topic),
        "education": get_education_prompt(style, topic),
        "emotional": get_emotional_prompt(style, topic),
    }

    prompt = templates.get(category, get_general_prompt(style, topic))

    return f"{prompt}, {base_config['quality']}"
```

---

## 质量检查清单

```yaml
技术检查:
  - 比例 3:4: [ ]
  - 分辨率 ≥ 1080x1440: [ ]
  - 文件大小 < 10MB: [ ]
  - 格式 PNG/JPG: [ ]

内容检查:
  - 主体清晰: [ ]
  - 光线适中: [ ]
  - 色彩和谐: [ ]
  - 无明显瑕疵: [ ]

风格检查:
  - 符合内容主题: [ ]
  - 风格一致: [ ]
  - 吸引眼球: [ ]
  - 小红书审美: [ ]

合规检查:
  - 无水印/Logo: [ ]
  - 无敏感内容: [ ]
  - 原创或合规素材: [ ]
  - 不侵犯版权: [ ]
```

---

## 常见问题

### Q1: 生成的图片质量不稳定？
**A**: 在 Prompt 中加强质量关键词：
```
", ultra high quality, 8K, masterpiece, best quality, professional, award winning"
```

### Q2: 图片风格不符合小红书审美？
**A**: 参考热门账号，使用以下关键词：
```
", Instagram aesthetic, Pinterest style, trendy, chic, minimal, clean"
```

### Q3: 如何让图片更有辨识度？
**A**: 添加个人风格元素：
```
", consistent color palette, unique style, brand identity"
```

### Q4: 生成速度慢怎么办？
**A**: 简化 Prompt，移除过于复杂的描述：
```
核心描述 + 主要风格 + 质量关键词（不超过50词）
```

---

## 使用示例

### 示例 1: 美食 + 简约风格

```
输入：
{
  "topic": "春季限定草莓蛋糕",
  "style": "minimalist",
  "category": "food"
}

输出：
"Professional food photography of strawberry spring cake,
clean white background, soft natural lighting,
top-down angle, minimalist composition,
garnish with fresh strawberries and mint leaves,
high contrast, appetizing, restaurant quality,
sharp focus, high quality, 8K resolution"
```

### 示例 2: 穿搭 + 街拍风格

```
输入：
{
  "topic": "春季清新穿搭",
  "style": "photography",
  "category": "fashion"
}

输出：
"Street style photography of spring fresh outfit,
white floral dress and denim jacket,
urban city street background, natural daylight,
candid pose, fashion magazine quality,
trendy and chic, sharp focus on outfit,
blurred background, high fashion aesthetic,
high quality, 8K resolution"
```

### 示例 3: 干货 + 图解风格

```
输入：
{
  "topic": "时间管理技巧",
  "style": "illustration",
  "category": "education"
}

输出：
"Clean infographic design about time management tips,
modern flat illustration style, pastel color palette,
clear typography, step-by-step visual guide,
professional instructional design,
engaging and easy to understand,
minimalist, high quality, sharp focus"
```

---

## 批量生成策略

### 同系列图片保持一致性

```yaml
策略1: 固定风格词
  所有图片使用相同的关键风格描述
  例如：", minimalist style, pastel colors, clean background"

策略2: 统一色调
  定义调色板，所有图片使用相同色系
  例如：", warm color palette, soft pink and peach tones"

策略3: 重复核心元素
  在不同图片中重复某些元素
  例如：每张图都包含相同的花卉/道具

策略4: 使用模板
  基于固定模板，只修改主体描述
  例如：模板 + 主题词 + 统一后缀
```

---

## 注意事项

1. **版权合规**：确保生成的图片不侵犯他人版权
2. **平台规范**：遵守小红书社区规范和内容政策
3. **原创性**：尽量生成原创内容，避免直接复制
4. **质量优先**：宁可少发，也要保证图片质量
5. **测试优化**：不断测试不同 Prompt，找到最佳效果

---

**版本**: 1.0.0
**最后更新**: 2025-02-06
