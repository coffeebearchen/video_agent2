# TASK 6A 通过状态冻结文档

## 1. 任务名称

**TASK 6A：最小素材匹配器实现**（含 TASK 6A-1 优先级修正）

---

## 2. 任务目标

- 建立独立的素材匹配层，根据 scene 文本返回最合适的资源路径
- 实现硬编码关键词规则的最小实现版本
- 验证多类别关键词匹配能力（冲突类、安全类、门禁类、网页类）
- 确保强语义关键词优先于泛词关键词的匹配优先级

---

## 3. 实际新增/修改文件

### 新增文件：

1. **asset_selector.py**（项目根目录）
   - 主要素材选择器模块
   - 实现 `select_asset_for_text(text: str) → Dict[str, Any]` 函数
   - 包含 4 类关键词规则定义

2. **tools/test_asset_selector.py**
   - 独立测试脚本
   - 5 个核心测试用例 + 5 个额外示例
   - 验证各关键词类别和 fallback 机制

### 未修改文件：

- ✅ run_pipeline_web.py（主链不涉及）
- ✅ build_scene_assets.py
- ✅ modules/video_engine.py
- ✅ scene_planner.py
- ✅ web_capture_to_cards_v2.py
- ✅ tts_engine_main.py
- ✅ web_to_script.py
- ✅ input_handler.py

---

## 4. 匹配规则说明

### 4.1 四大关键词类别及其资源映射

| 优先级 | 关键词类别 | 示例关键词 | 资源文件 | 资源类型 |
|------|---------|--------|-------|--------|
| 1 | 冲突/战争/袭击 | 冲突、战争、袭击、以色列、伊朗、炸弹、轰炸、军事 | conflict.png | image |
| 2 | 安全/验证 | 安全、验证、检查、合法、风险、确认、身份、验证码 | security.png | image |
| 3 | 门禁/保安/小区 | 保安、门禁、小区、放行、进入、门卡、进小区 | gate.png | image |
| 4 | 网页/浏览器 | 网页、浏览器、网站、页面、打开网页、网址、HTTP | browser.png | image |
| 5 | 无匹配 | （任何不匹配的文本） | ""（空） | text_card |

### 4.2 返回数据结构

```python
{
  "matched": bool,                    # 是否匹配成功
  "asset_type": "image" | "text_card", # 资源类型
  "asset_file": str,                  # 资源文件路径（无匹配时为空）
  "keyword": str,                     # 命中的关键词（无匹配时为空）
  "reason": str                       # 匹配理由说明
}
```

**示例：**

```python
# 匹配成功
{
  "matched": True,
  "asset_type": "image",
  "asset_file": "assets/library/security.png",
  "keyword": "安全",
  "reason": "检测到安全/验证相关关键词"
}

# 无匹配（fallback）
{
  "matched": False,
  "asset_type": "text_card",
  "asset_file": "",
  "keyword": "",
  "reason": "未匹配到特定关键词，使用默认 text_card fallback"
}
```

---

## 5. 优先级修正说明（TASK 6A-1）

### 问题发现

**原始优先级顺序（TASK 6A 初版）**在测试时发现问题：

```
测试文本："这其实是网站为了安全，在检查你的访问是否合法。"

当时返回结果：assets/library/browser.png ❌
期望结果：assets/library/security.png ✅
```

**根本原因：** 网页/浏览器类的泛词"网站"过早命中，抢占了更强语义的"安全/检查/合法"。

### 修正方案

**调整后的优先级顺序（TASK 6A-1）**：

```
原来的顺序：
1. BROWSER_KEYWORDS（泛词类）     ← 问题所在
2. SECURITY_KEYWORDS（强语义）    ← 被抢占
3. GATE_KEYWORDS
4. CONFLICT_KEYWORDS

修正后的顺序：
1. CONFLICT_KEYWORDS（强语义）    ✅ 优先级提升
2. SECURITY_KEYWORDS（强语义）    ✅ 优先级提升
3. GATE_KEYWORDS
4. BROWSER_KEYWORDS（泛词类）     ✅ 优先级降低
```

### 修正效果验证

```
测试文本："这其实是网站为了安全，在检查你的访问是否合法。"

修正前返回结果：assets/library/browser.png ❌
修正后返回结果：assets/library/security.png ✅ （通过）

原因：
- 虽然文本中包含"网站"（browser.png 关键词）
- 但也包含"安全"（security.png 关键词）
- 修正后按优先级，先检查 SECURITY_KEYWORDS
- "安全"先于"网站"命中，返回 security.png
```

---

## 6. 独立测试过程

### 6.1 测试执行环境

- Python 版本：3.9+
- 执行命令：`python tools/test_asset_selector.py`
- 执行位置：项目根目录（e:\video_agent）
- 测试框架：无外部依赖，纯标准库

### 6.2 测试用例设计

#### 核心测试用例（5个）

```
测试 #1: 混合文本（包含"网站"和"安全"）
  输入：「这其实是网站为了安全，在检查你的访问是否合法。」
  期望：security.png（强语义优先）
  通过：✅ PASS

测试 #2: 门禁/保安场景
  输入：「就像进小区前，保安会看一眼你的门禁卡。」
  期望：gate.png
  通过：✅ PASS

测试 #3: 冲突/战争场景
  输入：「伊朗和以色列互相袭击了对方的天然气设施。」
  期望：conflict.png
  通过：✅ PASS

测试 #4: 纯网页场景
  输入：「今天我们打开一个网页，看看这个页面的结构。」
  期望：browser.png（无其他强语义词，正常返回）
  通过：✅ PASS

测试 #5: 无关键词场景（fallback）
  输入：「这是一个普通说明，没有特定关键词。」
  期望：text_card（无匹配时使用 fallback）
  通过：✅ PASS
```

#### 额外示例验证（5个）

```
1. 「用户访问了一个恶意网站。」
   → browser.png（命中 BROWSER_KEYWORDS）

2. 「国家安全部门检查电子产品。」
   → security.png（命中 SECURITY_KEYWORDS，优先级高）

3. 「社区门禁系统升级。」
   → gate.png（命中 GATE_KEYWORDS）

4. 「中东地区冲突加剧。」
   → conflict.png（命中 CONFLICT_KEYWORDS）

5. 「天气变冷了。」
   → text_card（无匹配，使用 fallback）
```

### 6.3 测试输出结果

```
======================================================================
🧪 素材选择器测试
======================================================================

测试 #1
  输入文本：这其实是网站为了安全，在检查你的访问是否合法。
  期望关键词：安全 或 验证
  期望素材：security.png
  实际结果：
    - matched: True
    - asset_type: image
    - asset_file: assets/library/security.png
    - keyword: 安全
    - reason: 检测到安全/验证相关关键词
  状态：✅ PASS

测试 #2
  输入文本：就像进小区前，保安会看一眼你的门禁卡。
  期望关键词：保安 或 门禁 或 小区
  期望素材：gate.png
  实际结果：
    - matched: True
    - asset_type: image
    - asset_file: assets/library/gate.png
    - keyword: 保安
    - reason: 检测到门禁/保安/小区相关关键词
  状态：✅ PASS

测试 #3
  输入文本：伊朗和以色列互相袭击了对方的天然气设施。
  期望关键词：伊朗 或 以色列 或 袭击
  期望素材：conflict.png
  实际结果：
    - matched: True
    - asset_type: image
    - asset_file: assets/library/conflict.png
    - keyword: 袭击
    - reason: 检测到冲突/战争/袭击相关关键词
  状态：✅ PASS

测试 #4
  输入文本：今天我们打开一个网页，看看这个页面的结构。
  期望关键词：网页 或 页面
  期望素材：browser.png
  实际结果：
    - matched: True
    - asset_type: image
    - asset_file: assets/library/browser.png
    - keyword: 网页
    - reason: 检测到网页/浏览器相关关键词
  状态：✅ PASS

测试 #5
  输入文本：这是一个普通说明，没有特定关键词。
  期望关键词：无
  期望素材：fallback (text_card)
  实际结果：
    - matched: False
    - asset_type: text_card
    - asset_file:
    - keyword:
    - reason: 未匹配到特定关键词，使用默认 text_card fallback
  状态：✅ PASS

======================================================================
📊 测试统计：5 通过，0 失败
======================================================================
```

---

## 7. 验收结果

### 7.1 功能验收

| 验收项 | 结果 | 说明 |
|------|------|------|
| 冲突/战争类匹配 | ✅ PASS | 正确识别并返回 conflict.png |
| 安全/验证类匹配 | ✅ PASS | 正确识别并返回 security.png |
| 门禁/保安类匹配 | ✅ PASS | 正确识别并返回 gate.png |
| 网页/浏览器类匹配 | ✅ PASS | 正确识别并返回 browser.png |
| 优先级修正 | ✅ PASS | 强语义词优先于泛词（"安全"优先于"网站"） |
| Fallback 机制 | ✅ PASS | 无匹配时正确返回 text_card |
| 独立测试 | ✅ 5/5 通过 | 所有核心测试用例均通过 |
| 返回结构 | ✅ PASS | matched/asset_type/asset_file/keyword/reason 完整 |

### 7.2 非功能性验收

| 验收项 | 结果 | 说明 |
|------|------|------|
| 无外部依赖 | ✅ PASS | 仅使用 re + typing（标准库） |
| 无破坏性修改 | ✅ PASS | 未修改任何受限模块 |
| 不接入主链 | ✅ PASS | 完全独立，尚未集成到 run_pipeline_web |
| 代码可维护性 | ✅ PASS | 规则定义清晰，函数职责单一 |
| 错误处理 | ✅ PASS | 所有分支均有返回值，无异常风险 |

---

## 8. 当前结论

### 8.1 TASK 6A 状态

**✅ TASK 6A 已通过所有验收标准**

- 实现了最小硬编码素材匹配器
- 包含 4 类关键词规则 + fallback 机制
- 通过了 5/5 核心测试用例
- 通过了优先级修正验证（TASK 6A-1）
- 完全独立，不影响现有主链

### 8.2 当前模块性质

**当前 asset_selector.py 为：**

| 属性 | 说明 |
|------|------|
| **状态** | 独立素材匹配层（未集成） |
| **调用方** | 无（目前仅测试脚本调用） |
| **依赖** | 无其他业务模块 |
| **返回值** | Dict[str, Any]（见 4.2 节） |
| **调用时机** | 待 TASK 6B 集成时决定 |
| **风险等级** | 零风险（独立模块） |

### 8.3 软件版本信息

```
asset_selector.py 版本：TASK 6A-1
- 优先级调整：✅ 已完成
- 测试通过率：100%（5/5）
- 代码冻结时间：2026-03-20
```

---

## 9. 当前边界

### 9.1 已完成的功能边界

✅ **已实现**：
- 硬编码关键词匹配（4 大类）
- 优先级控制（强语义优先）
- Fallback 机制（text_card）
- 独立测试验证
- 返回结构标准化

❌ **未实现**：
- 与 build_scene_assets.py 的集成（待 TASK 6B）
- 与 run_pipeline_web.py 的集成（待 TASK 6B）
- AI/向量化匹配（需要新技术栈）
- 数据库存储（设计决策：保持最小实现）
- UI 界面（超出范围）
- 用户自定义规则（待 TASK 5D）

### 9.2 已冻结的代码改动范围

**只涉及以下文件：**

1. ✅ asset_selector.py（新增）
2. ✅ tools/test_asset_selector.py（新增）
3. ✅ backups/asset_selector_task6a_pass.py（备份）
4. ✅ backups/test_asset_selector_task6a_pass.py（备份）
5. ✅ docs/tasks/TASK_6A_PASS.md（文档）

**完全未涉及：**

- run_pipeline_web.py
- build_scene_assets.py
- modules/video_engine.py
- scene_planner.py
- web_capture_to_cards_v2.py
- tts_engine_main.py
- web_to_script.py
- input_handler.py

---

## 10. 下一步建议

### 10.1 推荐的后续任务路线

```
当前状态：TASK 6A ✅ PASS（独立层完成）
            ↓
下一步：TASK 6B（建议但本次不执行）
        - 集成 asset_selector 到 build_scene_assets.py
        - 在生成 scene_assets.json 时同步调用选择器
        - 为每个 scene 添加 asset 字段
            ↓
后续可选：TASK 6C（UI 增强）
        - 可视化素材匹配规则编辑
        - 交互式规则测试工具
            ↓
后续可选：TASK 6D（进阶匹配）
        - 向量化+相似度匹配
        - 多语言支持
        - 用户自定义词库
```

### 10.2 若进入 TASK 6B 的集成建议

**集成点候选：**

| 集成点 | 集成方式 | 优势 | 缺点 |
|------|--------|------|------|
| **build_scene_assets.py** | 在 build_minimal_scene_assets() 中为每个 scene 添加 asset 字段 | 原子化操作，一次性生成完整数据 | 需修改返回结构 |
| **run_pipeline_web.py Step 3.5** | 在生成后遍历 scene_assets.json，调用选择器更新 | 解耦，独立验证 | 两步操作，性能略下降 |

**推荐：** 第一种（在 build_scene_assets.py 中集成），保持数据生成的一致性。

### 10.3 本次停止说明

根据用户要求，TASK 6A-1 完成后立即停止，**不自动进入 TASK 6B**。

如用户需要继续，请明确要求：
- `【进行 TASK 6B】` - 集成到 build_scene_assets
- `【进行 TASK 6C】` - UI 增强
- `【修改某处代码】` - 其他改动

---

## 附录：快速回顾

### A. 核心调用方式

```python
from asset_selector import select_asset_for_text

# 示例 1：安全/验证场景
result = select_asset_for_text("这其实是网站为了安全，在检查你的访问是否合法。")
# → {"matched": True, "asset_type": "image", "asset_file": "assets/library/security.png", ...}

# 示例 2：无关键词
result = select_asset_for_text("天气变冷了。")
# → {"matched": False, "asset_type": "text_card", "asset_file": "", ...}

# 快速判断是否匹配
if result["matched"]:
    print(f"使用素材：{result['asset_file']}")
else:
    print("使用文字卡")
```

### B. 文件结构

```
e:\video_agent\
├── asset_selector.py              ✅ TASK 6A 通过版
├── tools\
│   └── test_asset_selector.py     ✅ TASK 6A 通过版
├── backups\
│   ├── asset_selector_task6a_pass.py           ✅ 备份
│   └── test_asset_selector_task6a_pass.py     ✅ 备份
└── docs\tasks\
    └── TASK_6A_PASS.md             ✅ 本文档
```

---

**文档版本：** v1.0  
**创建时间：** 2026-03-20  
**任务状态：** ✅ 通过 & 冻结  
**下一步：** 等待用户指示（TASK 6B 或其他）
