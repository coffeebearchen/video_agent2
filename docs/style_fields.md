# Style Fields Freeze

本文件冻结当前 style 系统的基础规则，避免未来风格参数分散、重复、失控。

## Single Source Rule

`modules/overlay_style_engine.py` 中的 `STYLE_PRESETS` 是当前唯一风格源。

所有视觉风格参数只允许从 `STYLE_PRESETS` 输出，禁止在以下位置复制或私自补充一份：

- runner 里复制一份 style 参数
- renderer 里写死 style 特例
- 其他模块新增“隐藏 style 参数”

## Default Debug Entry

风格静态调试默认先走 `runner/frame_preview_runner.py`。

建议顺序：

1. 调整字体、字号、颜色、位置、卡片宽度、布局重心
2. 先看 frame preview 图片
3. 视频渲染只做最终验收

## Confirmed Effective Fields

以下字段已经确认会被当前 renderer 实际消费：

- `font_size`
- `max_width`
- `position_y`
- `position_ratio_y`
- `text_color`
- `bg_color`
- `padding_x`
- `padding_y`
- `radius`
- `max_chars`
- `min_start`
- `start_ratio`
- `semantic_min_ratio`
- `semantic_max_ratio`
- `fade_enabled`

## Not Confirmed Or Not Guaranteed Yet

以下字段当前不作为“已确认生效”承诺，未来可扩，但暂不保证 renderer 会使用或稳定使用：

- `position_mode`
- `display_mode`
- `bilingual_mode`
- `duration_mode`
- `fixed_duration`
- `mode`
- `enabled`
- `max_count`
- `allow_style_override`
- `allow_multiple_highlights`
- `conclusion_enabled`

## Skeleton vs Skin

### 风格骨架

先少动，避免误伤整体风格识别：

- title / highlight 相对关系
- 布局重心
- 上下左右倾向
- 节奏倾向
- 表达气质方向

### 风格皮肤

后续可高频调节：

- 字体
- 字号
- 颜色
- 圆角
- padding
- 透明度
- 阴影强弱

原则：

先稳住骨架，再调整皮肤，不要因为换字体和颜色误伤风格骨架。