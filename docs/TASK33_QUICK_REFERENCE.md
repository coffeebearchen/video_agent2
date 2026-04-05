# Task33 实现总结（快速参考）

## 🎯 核心成果

为 VIDEO_AGENT 系统添加了 **可选的 scene_count 参数控制能力**，支持：
- ✅ 默认模式（自动）→ 3 个 scene
- ✅ 显式指定 → 3 或 5 个 scene
- ✅ 零主链修改，完全向后兼容

## 📁 修改文件（3个）

### 1. scene_planner.py
```python
# 新增函数：切割文本
def split_text_into_parts(text: str, num_parts: int) -> list

# 修改函数签名
def build_scene_plan(..., scene_count=None):
    # 逻辑：
    if scene_count is None:     # 默认
        生成 3 个 scene
    elif scene_count == 5:      # 显式
        拆分 explanation 成 3 部分
        生成：intro + body(3) + outro = 5 scene

# 修改 main()
scene_count = runtime_config.get("scene_count", None)
build_scene_plan(..., scene_count=scene_count)
```

### 2. run_pipeline_user.py
```python
# 新增函数
def _update_config_scene_count(scene_count):
    # 写入 config.json

# 修改函数签名
def run_pipeline(input_data, scene_count: int | None = None)

# 修改 main()
scene_count = None
if len(sys.argv) > 1:
    scene_count = int(sys.argv[1])  # 命令行参数
run_pipeline(input_data, scene_count=scene_count)
```

### 3. config.json
```json
{
  "scene_count": null  // 新增，默认 null=自动
}
```

## 🚀 用法

### 方式 1：Python API
```python
from run_pipeline_user import run_pipeline

# 自动模式
video = run_pipeline(input_data)

# 指定 5 个 scene
video = run_pipeline(input_data, scene_count=5)
```

### 方式 2：命令行
```bash
python run_pipeline_user.py 5  # 指定 5 个 scene
python run_pipeline_user.py    # 默认自动
```

### 方式 3：config.json
```json
{"scene_count": 5}
```

## ✅ 验证

| 功能 | 状态 |
|------|------|
| 默认 3 scene | ✓ |
| 指定 5 scene | ✓ |
| scene_count=5 实际生成 5 scene | ✓ |
| 不破坏 user_override | ✓ |
| 日志输出 [SCENE_COUNT] | ✓ |
| test suite 可执行 | ✓ |

## 🧪 测试

```bash
python tests/test_scene_count_control_runner.py
```

测试 3 个 case：
1. 默认模式 → 3 scene
2. 指定 scene_count=3 → 3 scene
3. 指定 scene_count=5 → 5 scene

## 📊 变更统计

- 修改文件：3 个
- 新增函数：2 个
- 新增代码行：约 150 行
- 删除代码：0 行
- 主链修改：0 行

## ⚡ 关键设计决策

1. **参数透传方案**
   - 通过 config.json 而非环境变量
   - 原因：scene_planner 是独立脚本，最少耦合

2. **默认行为**
   - scene_count=None 保持 3 scene（完全兼容）
   - 避免意外改变现有用户的工作流

3. **拆分策略**
   - 按换行符 / 行比例拆分（简单、可预测）
   - 避免复杂的 NLP（符合最小化原则）

4. **日志标记**
   - [SCENE_COUNT] 前缀便于查找和调试
   - 记录 mode（auto/fixed）和 final count

## 🔐 安全保证

✅ 不改 video_engine 核心  
✅ 不破坏 TTS 流程  
✅ 不修改素材 override 优先级  
✅ 不改动自动场景切分默认行为  
✅ 参数验证（仅接受 3 或 5）  

## 📝 代码示例

### 完整的 scene_count=5 流程

```
输入：text_content
  ↓
run_pipeline(input_data, scene_count=5)
  ↓
_update_config_scene_count(5)  // 写入 config
  ↓
scene_planner.main() // 读取 config
  ↓
if scene_count == 5:
  split_explanation_into_3_parts()
  build: [intro(hook), body1, body2, body3, outro(conclusion)]
  ↓
scene_plan.json: 5 scenes
  ↓
element_builder, timing_engine...
  ↓
video.mp4
```

## 🎓 后续扩展点

（不在 Task33 范围内，仅作记录）

1. 支持任意 scene_count（当前仅限 3|5）
2. NLP 智能拆分（当前为换行符比例）
3. UI 选择器（app.py / app_streamlit.py）
4. A/B 测试不同 scene 数量的质量

---

**Status**: ✅ **TASK33 COMPLETE**  
**Verification**: All 3 code paths tested and working  
**Backward Compatibility**: 100% maintained
