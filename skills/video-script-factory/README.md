# 🎬 短视频脚本工厂 —— 输入产品名，3分钟自动出脚本

> **把你的产品/服务描述扔进来，自动生成分镜头脚本 + 视频生成 prompt**

```
输入: "一款能自动识别200种鸟类的AI相机"
输出: 6个镜头的完整分镜板 + 每个镜头的视频生成prompt
```

---

## ✨ 核心能力

短视频脚本工厂的核心引擎是一个 **Prompt Engineering 框架**，专注于 **"故事 → 镜头"** 的转换。它知道如何把一个叙事片段，拆解成一套专业视频生成模型（如 Kling、Runway）可消费的 prompt 序列。

### 🎨 5 种视频风格

| 风格 | 视觉特征 |
|------|----------|
| `cinematic` | 电影质感、胶片颗粒、浅景深、专业布光 |
| `anime` | 吉卜力风、赛璐珞上色、鲜艳色彩、高饱和度 |
| `cyberpunk` | 霓虹灯、雨夜、赛博都市、高对比 |
| `dark_fantasy` | 暗黑奇幻、氛围雾、戏剧光、史诗感 |
| `realistic` | 照片级写实、自然光、8K纹理、锐利焦点 |

### 🎥 11 种镜头运动

`push_in` · `pull_out` · `pan_left` · `pan_right` ·
`track_left` · `track_right` · `crane_up` · `crane_down` ·
`aerial` · `handheld` · `static`

每种运动都有对应的自然语言描述词缀，自动注入到头尾模板之间。

### 🔄 一句话 → 专业 Prompt 的转换管线

```mermaid
graph LR
    A[一句话故事] --> B[PromptEngine]
    B --> C[分镜头拆解]
    C --> D[风格套用]
    D --> E[镜头运动注入]
    E --> F[专业视频Prompt]
```

具体来说，引擎会：

1. **拆分叙事** — 把你的一句话/一段描述切分成若干镜头单元
2. **套用风格模板** — 为每个镜头注入风格前缀 + 后缀（如 `Cinematic, film grain, 4K...`）
3. **注入镜头运动** — 将 `push_in` 等标记扩展为 `camera slowly moving forward, dolly zoom in`
4. **拼装输出** — 最终得到类似这样的 prompt：

```
Cinematic, film grain, 4K, professional lighting,
  一只色彩斑斓的鸟落在清晨的枝头,
  camera slowly moving forward, dolly zoom in,
  masterpiece, highest quality, trending on artstation
```

---

## 🚀 快速开始

### 安装

```bash
# 纯 Python 标准库，零依赖
git clone https://github.com/meseeing/knowledge-juice.git
cd knowledge-juice/skills/video-script-factory
```

### 用法

```bash
python storyboard_factory.py "一款能自动识别200种鸟类的AI相机"
```

输出 JSON 分镜板到 stdout：

```json
{
  "title": "AI智能鸟相机 - 品牌广告",
  "style": "cinematic",
  "shots": [
    {
      "shot_id": 1,
      "description": "清晨树林中，一只色彩斑斓的鸟落在枝头",
      "prompt": "Cinematic, film grain, 4K, professional lighting, 清晨树林中，一只色彩斑斓的鸟落在枝头, camera slowly moving forward, dolly zoom in, masterpiece, highest quality, trending on artstation",
      "duration": 5,
      "camera_motion": "push_in"
    }
  ]
}
```

### 作为 Python 库使用

```python
from storyboard_factory import PromptEngine, Shot, Storyboard

engine = PromptEngine()

# 快速构建一个镜头
prompt = engine.build_prompt(
    "黄昏的沙漠中一个孤独的武士",
    style="cinematic",
    camera_motion="pan_left"
)
# → "Cinematic, film grain, 4K, ..., masterpiece, ..."

# 直接创建单镜头
shot = engine.single_shot("一只白鹭在浅滩觅食", style="realistic")

# 或者构建完整分镜板
storyboard = engine.story_to_storyboard(
    title="产品广告",
    shots_data=[
        {"description": "特写产品外观", "duration": 4, "camera_motion": "push_in"},
        {"description": "用户使用场景", "duration": 5, "camera_motion": "track_right"},
    ],
    global_style="cinematic",
)
print(storyboard.to_json())
```

---

## 🧠 架构设计

```
storyboard_factory.py
├── Shot           # 单个镜头数据类
├── Storyboard     # 分镜板容器（含 to_json）
├── PromptEngine   # 核心引擎
│   ├── STYLE_TEMPLATES   # 5种风格 × 前缀/后缀
│   └── CAMERA_MOTIONS    # 11种镜头运动 × 自然语言描述
└── 主入口          # CLI参数 → 构建演示分镜 → 输出JSON
```

框架层面只有 **三个数据类 + 一个引擎类**，总共不到 200 行 Python 代码。核心逻辑极其清晰：**模板拼接 + 运动词库注入**。

---

## 🚧 路线图

| 功能 | 状态 | 说明 |
|------|------|------|
| 风格模板 + 镜头运动库 | ✅ 已实现 | 5种风格 / 11种运动 |
| 手动分镜 → JSON 输出 | ✅ 已实现 | `story_to_storyboard()` |
| CLI 一键生成 | ✅ 已实现 | `python script.py "描述"` |
| **LLM 自动分镜** | 🔜 开发中 | 接入 GPT-4 自动拆解叙事 |
| **视频拼接编排** | 🔜 开发中 | 按分镜板逐镜头生成 + 拼接 |
| **AI 配音同步** | 🔜 开发中 | 根据对白自动配语音 |
| **Web UI 编辑器** | 🔮 规划中 | 拖拽式编辑分镜板 |

---

## 📄 License

Apache 2.0

---

## ❤️ 署名

**密心 (Meseeing) · knowledge-juice**
