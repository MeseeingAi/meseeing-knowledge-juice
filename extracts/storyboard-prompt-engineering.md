# 从故事到镜头：视频 Prompt 工程的核心技术

> **知识提取物 · 密心 (Meseeing)**
> 对应技能：`skills/video-script-factory/`

---

## 1. 问题背景

视频生成模型（Kling、Runway Gen-3、Sora 等）对 prompt 质量极其敏感。

一个粗糙的 prompt：
```
a bird on a branch
```
→ 输出模糊、缺乏风格、动态不足

一个工程化 prompt：
```
Cinematic, film grain, 4K, professional lighting, shallow depth of field,
a colorful bird perched on a mossy branch in the morning forest,
dolly zoom in, camera slowly moving forward,
masterpiece, highest quality, trending on artstation
```
→ 输出清晰、风格统一、镜头感强

**差距不在模型能力，而在 prompt 工程。**

---

## 2. 核心技术：三层模板拼装

```
┌──────────────────────────────────────────┐
│           专业视频 Prompt                  │
├──────────────────────────────────────────┤
│  前缀（风格引导词）                         │
│  · Cinematic, film grain, 4K...          │
├──────────────────────────────────────────┤
│  主体（场景描述）                           │
│  · 用户输入的叙事内容                       │
├──────────────────────────────────────────┤
│  运动（镜头语言注入）                       │
│  · push_in → "camera slowly moving..."   │
├──────────────────────────────────────────┤
│  后缀（质量收尾词）                         │
│  · masterpiece, highest quality...       │
└──────────────────────────────────────────┘
```

### 2.1 风格前缀/后缀

每种风格定义了固定的视觉基调词汇。前缀引导模型理解画面风格，后缀收尾锁定质量。

| 风格 | 前缀特征 | 后缀特征 |
|------|----------|----------|
| cinematic | 胶片颗粒、浅景深、专业布光 | 杰作、最高质量 |
| anime | 赛璐珞上色、吉卜力风 | 高质动画、精美构图 |
| dark_fantasy | 暗黑氛围、体积雾 | 史诗感、暗黑美学 |
| cyberpunk | 霓虹灯、雨夜、赛博都市 | 合成波美学、银翼杀手 |
| realistic | 照片级写实、8K纹理 | 真实世界、锐利焦点 |

### 2.2 镜头运动词库

视频与图片最大的不同在于 **时间维度**。镜头运动直接决定了观众的沉浸感。

核心设计原则：**每种运动对应一段可读的自然语言描述**，而非机械的标记。

```python
CAMERA_MOTIONS = {
    "push_in":     "dolly zoom in, camera slowly moving forward",
    "pull_out":    "camera slowly pulling back, revealing the scene",
    "pan_left":    "panning left, following the subject",
    "aerial":      "aerial view, drone shot, birds eye view",
    "handheld":    "handheld camera, slight shake, documentary style",
    # ... 共 11 种
}
```

---

## 3. 从一句话到完整分镜板

完整流程分为四步：

### 步骤 A：叙事拆解

输入的一句话/一段描述，需要被拆解为若干镜头单元。每个镜头对应一个**独立的叙事节拍**。

当前实现使用**规则模板**（手动设计的叙事节奏），未来将升级为 **LLM 自动拆解**。

典型广告片 6 镜头节奏：
```
镜头1：定场（建立环境）      → aerial
镜头2：引入（用户痛点）      → push_in
镜头3：亮相（产品特写）      → track_right
镜头4：演示（功能展示）      → push_in
镜头5：体验（情感反应）      → pull_out
镜头6：升华（品牌收尾）      → crane_up
```

### 步骤 B：风格注入

对每个镜头独立应用风格模板（前缀 + 后缀）。

### 步骤 C：运动注入

根据分镜设计，将镜头运动标记扩展为自然语言描述。

### 步骤 D：拼装输出

```
{prefix}, {scene_description}, {motion_text}, {suffix}
```

---

## 4. 设计决策说明

### 为什么不用纯 LLM 生成？

| 方案 | 优点 | 缺点 |
|------|------|------|
| 纯模板引擎 | ⚡ 快、确定、可控、零成本 | 分镜刻板、缺乏创意 |
| LLM 自动分镜 | 🧠 创意强、动态适配 | 慢、贵、prompt 质量不稳定 |
| **模板+LLM混合** | ✅ 兼顾速度与创意 | 需要两套系统协同 |

当前版本定位 **"模板引擎"** 阶段，暴露核心工程逻辑。LLM 增强作为路线图保留。

### 为什么把镜头运动单独拎出来？

因为这是 **Prompt 工程中最容易被忽视的变量**。同一段场景描述，配上 `push_in` 和 `aerial` 生成的内容完全不同。把运动作为一等公民，是让视频 prompt 工程超越图片 prompt 工程的关键一步。

---

## 5. 评价维度

一个工程化的视频 prompt 可以从四个维度评价：

| 维度 | 说明 | 好 prompt 的特征 |
|------|------|------------------|
| 🎨 **风格一致性** | 所有镜头的视觉风格是否统一 | 共用一套前缀/后缀模板 |
| 🎥 **镜头语言** | 是否有意识使用了镜头运动 | 11种运动各司其职 |
| 📝 **叙事完整性** | 分镜是否能讲清一件事 | 定场→发展→高潮→收尾 |
| ⚡ **生成确定性** | 模型是否稳定输出预期内容 | 工程化模板降低随机性 |

---

## 6. 关联阅读

- 技能包：[skills/video-script-factory/](/skills/video-script-factory/)
- 演示输出：[demo_example.json](/skills/video-script-factory/demo_example.json)

---

*密心 (Meseeing) · knowledge-juice · Apache 2.0*
