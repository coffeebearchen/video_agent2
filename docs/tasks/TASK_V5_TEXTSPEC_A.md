# 【Task-V5-TextSpec-A｜文字表达控制系统规格层】

## TASK NAME
Task-V5-TextSpec-A｜文字表达控制系统规格层

## TASK GOAL
只做这一件事：

为现有 overlay 表达系统新增一个独立的文字规格层 `modules/text_spec_engine.py`，统一管理 title / highlight 的文本提炼、清洗、截断、双语拼接与预留字段；仅以最小侵入方式接入 `modules/overlay_renderer.py`。

本任务的定位是“规格层”，不是重做渲染层，不是重构主链，不是引入编辑器。

## CURRENT PROBLEM
当前系统已经完成：

- 主链跑通
- 双层表达稳定（Title 常驻 + Highlight 单卡 3 秒）
- `modules/overlay_style_engine.py` 已负责视觉规格 / 时序规格 / 风格切换

但目前“文字本身如何表达”仍分散在 `modules/overlay_renderer.py` 中，至少包括：

- title 文本提取逻辑
- title 截断逻辑
- highlight 双语拼接逻辑
- translation map 使用逻辑
- 文本清洗与空值回退逻辑

这会带来三个问题：

1. 视觉规格与文字规格混在一起，后续难以独立调优。
2. 当前五风格虽然已经可切换，但“文字表达规则”并未形成独立规格层。
3. V5 后期要做 Preview-A 时，如果文字规格仍埋在渲染代码里，验证效率会继续偏低。

因此，本任务只解决一件事：

把文字表达控制抽成一个独立、可回滚、可验证、默认兼容现状的小模块。

## ALLOWED CHANGES
只允许：

- 新增完整文件：`modules/text_spec_engine.py`
- 最小修改：`modules/overlay_renderer.py`
- 可选新增一个最小验证文件：`tests/test_text_spec_engine.py`
- 如有需要，可新增一个备份文件到 `backups/`，但不允许备份泛滥

允许的接入方式只有一种：

- `modules/overlay_renderer.py` 在生成 title / highlight 文本时，调用 `modules/text_spec_engine.py`

## FORBIDDEN CHANGES
禁止：

- 修改主链结构
- 修改 `run_pipeline_web.py`
- 修改 `modules/video_engine.py`
- 修改 `scene_planner.py`
- 修改 `modules/highlight_extractor.py`
- 修改 TTS / assets / scene / script 任一主链模块
- 引入编辑器系统
- 扩展 UI
- 引入复杂动画系统
- 改写现有五风格视觉表现
- 改写“Title 常驻 + Highlight 单卡 3 秒”的既有稳定策略
- 做跨模块重构
- 顺手修别的模块

## READ WHITELIST
You are ONLY allowed to read:

1. `docs/CODEX_CONSTITUTION.md`
2. `modules/overlay_renderer.py`
3. `modules/overlay_style_engine.py`
4. `modules/highlight_extractor.py`

Do NOT read any other files.

## IMPLEMENTATION REQUIREMENTS
必须新增一个独立模块：`modules/text_spec_engine.py`

该模块只负责“文字表达规格”，不负责：

- 图片绘制
- 视频合成
- clip 组装
- 字体加载
- 时间轴计算
- 素材调度

### 1. 规格层职责边界
`modules/text_spec_engine.py` 只允许负责以下内容：

- title 文本提取规则
- title 文本清洗规则
- title 文本截断规则
- highlight 文本清洗规则
- highlight 双语文本拼接规则
- style_name 对应的文字规格预设
- 未来字段预留（仅返回字段，不实现复杂动画）

### 2. 必须提供的规格结构
模块内部必须提供按 style_name 解析的文字规格，至少覆盖以下五个 preset：

- `creator_clean`
- `personal_ip`
- `product_focus`
- `life_story`
- `ai_control_lab`

每个 preset 的结构必须稳定，至少包含：

```python
{
    "style_name": "creator_clean",
    "title": {
        "source_mode": "first_sentence",
        "cleanup_mode": "compact",
        "max_chars": 20,
        "ellipsis": "...",
        "allow_empty": True,
        "reserved": {
            "line_break_mode": "auto",
            "emphasis_mode": "none",
            "animation_preset": "none",
        },
    },
    "highlight": {
        "source_mode": "primary_only",
        "cleanup_mode": "compact",
        "max_chars": 18,
        "translation_mode": "builtin_map",
        "bilingual_mode": "follow_overlay_style",
        "fallback_to_zh_only": True,
        "allow_empty": True,
        "reserved": {
            "line_break_mode": "auto",
            "emphasis_mode": "none",
            "animation_preset": "none",
        },
    },
}
```

说明：

- `reserved` 字段必须存在，但本任务不实现动画与复杂排版。
- 五个 preset 初始值允许大部分相同，重点是“规格结构成型”，不是做五套复杂差异。
- `bilingual_mode` 的实际视觉排布仍由现有 overlay 体系决定；TextSpec-A 只负责“文本组织方式”。

### 3. 必须提供的函数接口
`modules/text_spec_engine.py` 至少提供以下函数：

```python
get_text_spec(style_name: str | None = None) -> dict
build_title_copy(scene_text: str, style_name: str | None = None) -> str
build_highlight_copy(highlight_text: str, style_name: str | None = None) -> str
build_text_debug_payload(scene_text: str, highlight_text: str, style_name: str | None = None) -> dict
```

要求：

- 所有函数必须安全容错，不允许向上抛异常破坏渲染链。
- 空值、异常值、非字符串输入必须安全处理。
- 未知 style_name 必须回退到 `creator_clean`。

### 4. title 规则要求
`build_title_copy(...)` 的默认行为必须保持接近现状：

- 从 scene_text 中优先提取第一句
- 做轻量清洗：去掉多余空白 / 换行 / 首尾杂质
- 依据 spec 的 `max_chars` 做截断
- 超出长度时使用 `ellipsis`
- 结果为空时安全返回空字符串

不允许做：

- 改写内容含义
- 调用 LLM
- 自动润色成新文案

### 5. highlight 规则要求
`build_highlight_copy(...)` 的默认行为必须保持接近现状：

- 只处理单个 primary highlight
- 做轻量清洗
- 如命中 builtin translation map，则生成中英组合文本
- 如未命中英文映射，则安全回退为仅中文
- 不允许因为翻译缺失而丢失 highlight

不允许做：

- 多 highlight 轮播
- 新增结论卡
- 引入新翻译服务

### 6. overlay_renderer.py 的改动边界
`modules/overlay_renderer.py` 只允许做最小侵入接入：

- 删除或弱化内部散落的 title/highlight 文本构建逻辑
- 改为调用 `modules/text_spec_engine.py`
- 保留现有图层绘制方式
- 保留现有 timing / fade / CompositeVideoClip 逻辑
- 保留现有 `overlay_style_engine` 的 style/timing 读取逻辑

明确要求：

- 不能把 text spec 再塞回 `overlay_style_engine.py`
- 不能在 renderer 内部重新造第二套 style preset
- 不能趁机改 overlay 的视觉参数

### 7. 日志要求
接入后，允许新增少量日志，但只限于文字规格调试：

- `[TEXT_SPEC] style_name=...`
- `[TEXT_SPEC] title=...`
- `[TEXT_SPEC] highlight=...`

禁止输出冗长调试噪音。

## DELIVERY REQUIREMENTS
1. Provide complete files
2. Do not provide partial patches
3. Keep backward compatibility
4. Explain run method
5. Explain validation method
6. Explain rollback method

交付时必须包含：

1. `modules/text_spec_engine.py` 完整文件
2. `modules/overlay_renderer.py` 完整文件
3. 如新增验证文件，则也必须给完整文件
4. 说明“改了什么 / 没改什么”

## ACCEPTANCE CRITERIA
满足以下全部条件，才算完成：

1. 新增 `modules/text_spec_engine.py`，并且它能独立解析五个 style preset 的文字规格。
2. `modules/overlay_renderer.py` 已通过单接入点方式调用 text spec，而不是继续内嵌散乱文本逻辑。
3. 不改主链，不改 `run_pipeline_web.py`，不改 `modules/video_engine.py`。
4. 默认渲染行为保持兼容：Title 仍可常驻，Highlight 仍是单卡显示，不因为本任务破坏现有稳定效果。
5. highlight 无英文映射时，仍能安全显示中文，不允许直接消失。
6. 空 scene_text / 空 highlight / 异常输入时，不报错、不打断渲染。
7. 五种风格在 env 切换下都能跑通文字规格解析。
8. 如新增测试文件，测试可直接执行并通过。

## RUN METHOD
按以下顺序执行，禁止串成一条命令。

### A. 模块级验证
先运行最小验证：

```powershell
e:/video_agent/.venv/Scripts/python.exe tests/test_text_spec_engine.py
```

如果你没有新增测试文件，则至少执行一段最小代码验证以下内容：

- 五个 style 是否可解析
- title 是否会被正常截断
- highlight 是否能中英拼接或中文安全回退

### B. 渲染级验证
按既定防卡死协议执行。

第 1 步：设置环境变量

```powershell
$Env:OVERLAY_STYLE_NAME='creator_clean'
```

第 2 步：只做渲染

```powershell
e:/video_agent/.venv/Scripts/python.exe -u -m modules.video_engine
```

第 3 步：单独看日志

检查是否出现：

- `[TEXT_SPEC] style_name=creator_clean`
- `[TEXT_SPEC] title=...`
- `[TEXT_SPEC] highlight=...`
- 且无异常 traceback

第 4 步：如有需要，再单独抽帧

第 5 步：清理环境变量

```powershell
Remove-Item Env:OVERLAY_STYLE_NAME
```

只要 `creator_clean` 通过，再额外抽查以下两个风格即可：

- `personal_ip`
- `ai_control_lab`

无需在本任务里重跑五风格全量实拍验证。

## VALIDATION METHOD
必须验证以下项目：

1. `build_title_copy` 对长句能截断且不报错。
2. `build_title_copy` 对空输入返回空字符串。
3. `build_highlight_copy` 对已知关键词能生成双语文本。
4. `build_highlight_copy` 对未知关键词能保留中文。
5. `get_text_spec(None)` 能回退到默认风格。
6. `get_text_spec('unknown_style')` 能安全回退。
7. 接入后渲染日志中能看到 `[TEXT_SPEC]` 输出。
8. 最终视频没有因为 TextSpec-A 出现 title/highlight 全部丢失。

## ROLLBACK METHOD
如果任务失败，只按以下方式回滚：

1. 删除新增文件：`modules/text_spec_engine.py`
2. 删除新增测试文件：`tests/test_text_spec_engine.py`（如果有）
3. 恢复 `modules/overlay_renderer.py` 到任务前版本

回滚后，系统应恢复为“由 `overlay_renderer.py` 自己直接生成 title/highlight 文本”的旧状态。

## IMPLEMENTATION NOTES
这是一个“小模块 + 单接入点”任务，不是重构任务。

执行时必须坚持：

- 先新增模块，再最小接入
- 不改变稳定主链
- 不扩展产品边界
- 不把 Preview-A 一起做掉

本任务完成后，下一步才允许进入：

- Preview-A（单帧预览最小版）

但本卡不包含 Preview-A 的任何实现。