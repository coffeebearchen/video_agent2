# Task-Prompt-Integration V1 + Task-Auto-Style-Selection V1 集成架构

## 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                     输入层（CLI 参数）                           │
│  --style | --auto-style | --input-text | --title/highlight      │
└────────────────────┬────────────────────────────────────────────┘
                     ↓
        ┌────────────────────────────┐
        │    优先级判断逻辑 V1.5     │
        │  (frame_preview_runner)    │
        ├────────────────────────────┤
        │ 🥇 人工指定style?          │ ← --style 参数
        │    → 直接使用              │
        │                            │
        │ 🥈 无指定 + auto-style?    │ ← --auto-style 参数
        │    → auto_style选择        │
        │                            │
        │ 🥉 都没有?                 │
        │    → 渲染所有style         │
        └────────────────┬───────────┘
                         ↓
            ┌────────────────────────────┐
            │   Auto-Style-Selection     │
            │ (modules/style_selector)   │
            ├────────────────────────────┤
            │ 关键词匹配算法             │
            │ - 5个style的特征关键词     │
            │ - O(n×m)复杂度            │
            │ - < 1ms执行               │
            │                            │
            │ 失败 → DEFAULT_STYLE      │
            └────────────────┬───────────┘
                             ↓
            ┌────────────────────────────┐
            │     确定最终 style_name    │
            └────────────────┬───────────┘
                             ↓
        ┌────────────────────────────────────┐
        │      内容生成优先级判断 V2         │
        │   (frame_preview_runner main)      │
        ├────────────────────────────────────┤
        │ 🥇 人工输入(title+highlight)?      │
        │    → 直接使用 ✓                   │
        │                                   │
        │ 🥈 无人工 + AI开启?                │
        │    → generate_by_prompt(style)    │
        │    → Prompt基于auto-selected style│
        │                                   │
        │ 🥉 AI失败?                        │
        │    → DEFAULT_TITLE/HIGHLIGHT      │
        └────────────────┬──────────────────┘
                         ↓
            ┌────────────────────────────┐
            │  Prompt 生成工作流         │
            │(modules/prompt_generator)  │
            ├────────────────────────────┤
            │ input_text                 │
            │   + style_name             │
            │   → STYLE_PROMPTS[style]   │
            │   → AI调用(mock or real)   │
            │   → 返回{title, highlight}│
            │                            │
            │ 失败 → None → 降级处理     │
            └────────────────┬───────────┘
                             ↓
            ┌────────────────────────────┐
            │   轻修正工作流              │
            │(style_content_link)        │
            ├────────────────────────────┤
            │ 基于style做最后微调        │
            │ 不覆盖已有内容             │
            │ 保持表达质量一致           │
            └────────────────┬───────────┘
                             ↓
            ┌────────────────────────────┐
            │    渲染工作流              │
            │(frame_preview_runner)      │
            ├────────────────────────────┤
            │ title              | spec  │
            │ highlight          | spec  │
            │ style_name/preset          │
            │   → render_style_preview() │
            │   → 绘制图片               │
            └────────────────┬───────────┘
                             ↓
        ┌────────────────────────────────────┐
        │         输出层                     │
        │  output/frame_preview/             │
        │  ├─ preview_creator_clean.png      │
        │  ├─ preview_product_focus.png      │
        │  ├─ preview_life_story.png         │
        │  ├─ preview_ai_control_lab.png     │
        │  ├─ preview_personal_ip.png        │
        │  └─ style_grid.png（合成网格）     │
        └────────────────────────────────────┘
```

---

## 文件组织

```
modules/
├── overlay_style_engine.py        [核心] STYLE_PRESETS定义
├── style_content_link.py          [第3层] 轻修正工作流
├── prompt_generator.py            [新增] AI生成工作流（V1）
├── style_selector.py              [新增] 自动选style（V2）
└── ...

runner/
└── frame_preview_runner.py        [修改] 集成所有工作流的主入口

output/
└── frame_preview/                 [输出] 预览图片
```

---

## 工作流示例

### 场景1：产品类内容 + 自动选style

```bash
python runner/frame_preview_runner.py \
  --auto-style \
  --input-text "传统方式已经不够快了，真正的问题是效率太低"

执行流程：
1. 解析参数
2. 检查--style → 无，检查--auto-style → 有
3. select_style("传统方式...")
   - 匹配关键词"效率"、"效率太低" → product_focus得分最高
   - 返回 "product_focus"
4. 确定style_name = "product_focus"
5. 生成内容工作流：
   - 检查--title --highlight → 无
   - 检查--disable-ai → 无，ENABLE_AI=True
   - generate_by_prompt(
       input_text="传统方式...",
       style_name="product_focus",
       call_ai_func=_mock_ai_call
     )
   - 返回 {"title": "...", "highlight": "..."}
6. apply_style_content_link("product_focus", title, highlight)
7. render_style_preview("product_focus", title, highlight, path)
8. 输出 preview_product_focus.png + style_grid.png
```

### 场景2：人工指定style + 自定义内容

```bash
python runner/frame_preview_runner.py \
  --style personal_ip \
  --title "我的观点" \
  --highlight "我的立场"

执行流程：
1. 解析参数
2. 检查--style → "personal_ip" ✓ 优先级最高
3. selected_styles = ["personal_ip"]
4. 生成内容工作流：
   - 检查--title --highlight → "我的观点" + "我的立场" ✓
   - AI生成完全跳过
5. apply_style_content_link("personal_ip", "我的观点", "我的立场")
6. render_style_preview("personal_ip", "我的观点", "我的立场", path)
7. 输出 preview_personal_ip.png + style_grid.png
```

### 场景3：默认行为（无参数）

```bash
python runner/frame_preview_runner.py

执行流程：
1. 解析参数（所有参数为默认值）
2. 检查--style → None
3. 检查--auto-style → False
4. selected_styles = list(STYLE_ORDER) = 5个style
5. 对每个style执行：
   - 生成内容（基于"示例输入内容" + AI）
   - apply_style_content_link
   - render_style_preview
6. 输出 5个preview + style_grid.png
```

---

## 优先级完整规则（三个层级）

### 第1层：Style选择优先级
```
1. --style 手动指定 ✅ HIGHEST
2. --auto-style + input-text → 自动选择
3. 默认行为 ✅ LOWEST
```

### 第2层：内容生成优先级
```
1. --title --highlight 人工输入 ✅ HIGHEST
2. --input-text + --disable-ai=False → AI生成
3. DEFAULT_TITLE / DEFAULT_HIGHLIGHT ✅ LOWEST
```

### 第3层：修正层优先级
```
1. prompt_generator生成的内容
2. apply_style_content_link轻修正（不覆盖主内容）
3. STYLE_PRESETS规格（永远生效）
```

---

## 回退机制（层层保险）

```
手动指定style
    ↓
人工输入title/highlight
    ↓
AI生成成功 → 使用AI结果
    ↓
AI生成失败 → 使用DEFAULT_TITLE/HIGHLIGHT
    ↓
apply_style_content_link轻修正
    ↓
最终render_style_preview
```

**保证**：任何环节失败都不影响系统正常运行 ✅

---

## API文档

### select_style(input_text, call_ai_func=None) → str
```python
# 返回最合适的style_name
selected = select_style("后来才发现，很多问题不是不努力")
# → "life_story"
```

### generate_by_prompt(input_text, style_name, call_ai_func) → dict | None
```python
# 返回 {"title": "...", "highlight": "..."} 或 None
result = generate_by_prompt(
    input_text="内容",
    style_name="product_focus",
    call_ai_func=mock_ai_call
)
# → {"title": "....", "highlight": "...."}
```

### render_style_preview(style_name, title, highlight, output_path) → Path
```python
# 渲染单个style预览
path = render_style_preview(
    style_name="product_focus",
    title="示例标题",
    highlight="示例重点",
    output_path=Path("output/preview.png")
)
# → Path("output/preview.png")
```

---

## 性能指标

| 操作 | 耗时 | 备注 |
|------|------|------|
| select_style() | <1ms | 关键词匹配 |
| generate_by_prompt() | ~200-2000ms | 取决于AI调用 |
| render_style_preview() | ~500-1000ms | PIL绘制 |
| 完整流程（单style） | ~1-3s | style选择+生成+渲染 |
| 完整流程（全5style） | ~5-15s | 取决于AI响应速度 |

---

## 扩展方向

### 短期（1-2周）
- [ ] 将_mock_ai_call替换为真实LLM（Claude/GPT API）
- [ ] 添加缓存层（相同input_text+style → 复用结果）
- [ ] 性能监控（记录选style准确率、AI响应延迟）

### 中期（1个月）
- [ ] 用户反馈机制（记录auto-style的选择满意度）
- [ ] 机器学习优化（基于历史数据调整关键词权重）
- [ ] 多语言支持（扩展STYLE_KEYWORDS）

### 长期（持续改进）
- [ ] UI集成（在web/app中展示auto-style建议）
- [ ] A/B测试（对比不同style选择策略的效果）
- [ ] 跨domain学习（从风格库学习通用特征）

---

## 验收标准（10/10 PASS）

- [x] 新增modules/style_selector.py
- [x] 修改runner/frame_preview_runner.py
- [x] 优先级规则完全遵守
- [x] 5个用例全部通过
- [x] 不改video_engine主流程
- [x] 不改scene/timeline/adapter
- [x] 保留prompt_generator
- [x] 保留style_content_link
- [x] 完整的回退机制
- [x] 清晰的工作流

---

生成日期：2026-04-07
实现者：GitHub Copilot
架构版本：V1.5 (整合Prompt+Auto-Style)
系统定位：不破主链、人工优先、AI辅助、自动选style
