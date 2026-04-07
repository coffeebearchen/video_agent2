# frame_preview_runner.py 命令参考指南

## 基础命令

### 1. 默认渲染所有style
```bash
python runner/frame_preview_runner.py
```
**效果**：
- 渲染5个style的预览
- 使用AI生成title/highlight（基于"示例输入内容"）
- 生成style_grid.png合成图
- 输出 output/frame_preview/

---

### 2. 手动指定style（优先级最高）
```bash
python runner/frame_preview_runner.py --style product_focus
```
**效果**：
- 仅渲染product_focus
- auto-style被完全忽略
- AI生成内容（基于"示例输入内容"）

**支持的style**：
- creator_clean
- product_focus
- life_story
- ai_control_lab
- personal_ip

---

### 3. 自动选择style
```bash
python runner/frame_preview_runner.py --auto-style --input-text "输入文本"
```
**效果**：
- 根据input-text自动选择最合适的style
- 基于关键词匹配算法
- 与manual --style不能同时使用（style优先）

**示例**：
```bash
# 产品类 → product_focus
python runner/frame_preview_runner.py \
  --auto-style \
  --input-text "传统方式已经不够快了，真正的问题是效率太低"

# 叙事类 → life_story
python runner/frame_preview_runner.py \
  --auto-style \
  --input-text "后来才发现，很多问题不是不努力，而是方法不对"

# 结构类 → ai_control_lab
python runner/frame_preview_runner.py \
  --auto-style \
  --input-text "真正的问题是系统没有闭环，变量没有被约束"

# 观点类 → personal_ip
python runner/frame_preview_runner.py \
  --auto-style \
  --input-text "你必须知道，真正的问题不是努力不够，而是方向错了"

# 信息类 → creator_clean
python runner/frame_preview_runner.py \
  --auto-style \
  --input-text "重点是先理解方法，再执行步骤"
```

---

## 内容控制

### 4. 提供人工标题（优先于AI生成）
```bash
python runner/frame_preview_runner.py \
  --style product_focus \
  --title "我的标题"
```
**效果**：
- 使用"我的标题"作为title
- highlight仍然AI生成

### 5. 提供人工重点表达
```bash
python runner/frame_preview_runner.py \
  --style product_focus \
  --highlight "我的重点"
```
**效果**：
- title仍然AI生成
- 使用"我的重点"作为highlight

### 6. 完全人工内容（无AI生成）
```bash
python runner/frame_preview_runner.py \
  --title "我的标题" \
  --highlight "我的重点"
```
**效果**：
- AI生成完全被跳过
- 直接使用人工输入
- 不指定--style时，渲染所有5个style

---

## AI控制

### 7. 禁用AI生成
```bash
python runner/frame_preview_runner.py --disable-ai
```
**效果**：
- 使用DEFAULT_TITLE和DEFAULT_HIGHLIGHT
- 不调用AI

### 8. 自定义AI输入文本
```bash
python runner/frame_preview_runner.py \
  --input-text "你要总结的关键内容"
```
**效果**：
- AI基于此文本生成title/highlight
- auto-style也基于此文本选择

---

## 组合使用

### 9. Auto-style + 自定义input-text
```bash
python runner/frame_preview_runner.py \
  --auto-style \
  --input-text "后来才发现，很多问题不是不努力"
```

### 10. Auto-style + 人工title + AI highlight
```bash
python runner/frame_preview_runner.py \
  --auto-style \
  --input-text "后来才发现..." \
  --title "我的标题"
```

### 11. Auto-style + 人工title/highlight + 禁用AI
```bash
python runner/frame_preview_runner.py \
  --auto-style \
  --input-text "输入内容" \
  --title "我的标题" \
  --highlight "我的重点" \
  --disable-ai
```
**效果**：
- auto-style选择style
- 使用人工input
- 禁用AI（已有人工input，AI本不会运行）

### 12. 手动style + auto-style冲突（style优先）
```bash
python runner/frame_preview_runner.py \
  --style product_focus \
  --auto-style \
  --input-text "后来才发现..."
```
**效果**：
- 使用product_focus（--style优先级最高）
- auto-style被忽略

---

## 完整场景

### 场景A：内容创作者工作流
```bash
# 第1步：快速预览（所有style）
python runner/frame_preview_runner.py

# 第2步：基于内容自动选style
python runner/frame_preview_runner.py \
  --auto-style \
  --input-text "今天分享的核心内容"

# 第3步：确定人工标题+重点
python runner/frame_preview_runner.py \
  --auto-style \
  --input-text "今天分享的核心内容" \
  --title "真正的核心是这个" \
  --highlight "最关键的一点"

# 第4步：微调style（如需要）
python runner/frame_preview_runner.py \
  --style personal_ip \
  --title "真正的核心是这个" \
  --highlight "最关键的一点"
```

### 场景B：快速原型验证
```bash
# 一行命令快速生成预览
python runner/frame_preview_runner.py --auto-style --input-text "我的内容" --title "我的标题"
```

### 场景C：完全自动化
```bash
# 无参数 = 自动生成所有style的完整预览
python runner/frame_preview_runner.py
```

### 场景D：特定style快速验证
```bash
# 快速验证某个style的风格效果
python runner/frame_preview_runner.py --style product_focus
```

---

## 参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --style | str | None | 手动指定style（优先级最高） |
| --auto-style | flag | False | 启用自动选style |
| --title | str | None | 人工指定标题 |
| --highlight | str | None | 人工指定重点 |
| --input-text | str | "示例..." | AI生成和auto-style的输入文本 |
| --disable-ai | flag | False | 禁用AI生成，使用默认文案 |

---

## 优先级快速参考

### Style选择优先级
```
1. --style 手动指定 ✅ 最高
   ↓（不指定style时）
2. --auto-style 自动选 ✅ 中
   ↓（都不指定时）
3. 默认（渲染全部5个）✅ 最低
```

### 内容生成优先级
```
1. --title 人工标题 ✅ 最高
   ↓（不指定时）
2. AI生成（基于style和input-text） ✅ 中
   ↓（AI失败时）
3. DEFAULT_TITLE ✅ 最低
```

---

## 输出说明

### 正常输出示例
```
[FRAME_PREVIEW] Auto-selected style: product_focus (input: 传统方式已经不够快...)
[FRAME_PREVIEW] Generating content for style=product_focus...
  [AI] title=真正的问题，不是你不够努力
  [AI] highlight=而是你一直在用错误的方法
[FRAME_PREVIEW] generated=output\frame_preview\preview_product_focus.png
[FRAME_PREVIEW] generated=output\frame_preview\style_grid.png
```

### 日志信息说明
| 日志 | 含义 |
|------|------|
| `[FRAME_PREVIEW] Using manually specified style:` | 使用了--style参数 |
| `[FRAME_PREVIEW] Auto-selected style:` | 使用了auto-style选择 |
| `[FRAME_PREVIEW] No style specified` | 默认渲染所有style |
| `[FRAME_PREVIEW] Generating content` | 正在调用AI生成 |
| `[AI] title=` | AI成功生成了title |
| `[AI] highlight=` | AI成功生成了highlight |

---

## 常见问题

### Q: auto-style没有选出我期望的style？
**A**: 检查关键词是否在STYLE_KEYWORDS中。可以修改 `modules/style_selector.py` 添加更多关键词。

### Q: 为什么手动指定--style后auto-style失效？
**A**: 这是设计行为。--style优先级最高，防止冲突。如需auto-style，不要指定--style。

### Q: AI生成的内容质量不好？
**A**: 当前使用mock AI。生产环境应该替换 `runner/frame_preview_runner.py` 中的 `_mock_ai_call()` 为真实LLM调用。

### Q: 如何禁用所有AI功能？
**A**: 使用 `--disable-ai` 参数，系统会使用DEFAULT_TITLE和DEFAULT_HIGHLIGHT。

### Q: 一次能渲染多个style吗？
**A**: 当前V1只支持单个style（不指定--style时渲染全部5个）。如需选择多个style，需要多次运行命令。

---

## 实用快捷命令

```bash
# 快速生成所有style预览
alias preview-all="python runner/frame_preview_runner.py"

# 快速自动选style
alias preview-auto="python runner/frame_preview_runner.py --auto-style --input-text"

# 快速选择特定style
alias preview-product="python runner/frame_preview_runner.py --style product_focus"
alias preview-story="python runner/frame_preview_runner.py --style life_story"
alias preview-ip="python runner/frame_preview_runner.py --style personal_ip"
alias preview-lab="python runner/frame_preview_runner.py --style ai_control_lab"
alias preview-clean="python runner/frame_preview_runner.py --style creator_clean"

# 使用示例
preview-auto "我的内容"
preview-product --title "我的标题"
```

---

生成日期：2026-04-07
版本：frame_preview_runner.py v1.5 + auto-style v1
最后更新：Task-Auto-Style-Selection V1 完成
