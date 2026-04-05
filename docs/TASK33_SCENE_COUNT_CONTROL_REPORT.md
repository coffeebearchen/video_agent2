# Task33 - Scene Count 控制能力完成报告

## 🎯 任务目标
在不重构主链的前提下，为用户提供可选的 scene_count 参数控制能力。系统应支持：
- 默认模式（不传 scene_count）→ 自动逻辑，保持当前行为
- 显式指定 scene_count=3 → 生成 3 个 scene
- 显式指定 scene_count=5 → 生成 5 个 scene

## ✅ 实现状态

**全部完成** ✓

## 📋 修改的文件

### 1. [scene_planner.py](../scene_planner.py)
**目的**：核心 scene 规划器，添加 scene_count 参数支持

**关键改动**：
- 新增 `split_text_into_parts()` 函数（第143-173行）
  - 功能：将文本按换行符或行数比例分割
  - 用途：支持生成不同数量的 scene
  
- 修改 `build_scene_plan()` 函数（第175-229行）
  - 添加 `scene_count=None` 参数
  - 默认行为：scene_count=None 时生成 3 个 scene（保留兼容性）
  - 新增逻辑：scene_count=5 时，把 explanation 拆分成 3 个 body scene
  
- 修改 `main()` 函数（第341-345行）
  - 从 config.json 读取 scene_count 配置
  - 传入 build_scene_plan() 调用
  - 添加日志输出 `[SCENE_COUNT] final_scene_count=N`

**验证**：✓ 已测试，成功生成 5 个 scene

### 2. [run_pipeline_user.py](../run_pipeline_user.py)
**目的**：用户入口层，支持 scene_count 参数传递

**关键改动**：
- 新增 `_update_config_scene_count()` 函数（第116-140行）
  - 功能：更新 config.json 中的 scene_count 字段
  - 说明：使下游 scene_planner.py 能读到该参数

- 修改 `run_pipeline()` 函数（第142-219行）
  - 添加 `scene_count: int | None = None` 参数
  - 在 Step 3 scene_planner 前调用 `_update_config_scene_count()`
  - 添加日志 `[SCENE_COUNT] mode=auto|fixed`
  
- 修改 `main()` 函数（第221-245行）
  - 支持命令行参数：`python run_pipeline_user.py [3|5]`
  - 解析并验证 scene_count 参数
  - 传入 run_pipeline() 调用

- 修复编码问题：
  - 将 ❌ 替换为 `[ERROR]`
  - 将 ✅ 替换为 `[OK]`

### 3. [config.json](../config.json)
**目的**：配置文件，存储 scene_count 参数

**改动**：
- 新增 `"scene_count": null` 字段（行业标准为 null = 默认）
- 可通过 run_pipeline() 或直接编辑来修改

## 🧪 测试文件

### [tests/test_scene_count_control_runner.py](../tests/test_scene_count_control_runner.py)
**目的**：自动化测试 scene_count 功能的三个核心 case

**测试结构**：
```
Case 1：默认自动模式（scene_count=None）
  └─ 验证：使用自动逻辑，生成 3 个 scene

Case 2：显式指定 3（scene_count=3）
  └─ 验证：精确生成 3 个 scene

Case 3：显式指定 5（scene_count=5）
  └─ 验证：精确生成 5 个 scene
```

**运行方式**：
```bash
python tests/test_scene_count_control_runner.py
```

**关键功能**：
- 直接调用 `run_pipeline()` 函数，避免子进程复杂性
- 自动生成测试文本输入
- 读取 scene_plan.json 验证生成的 scene 数量
- 检查输出视频是否生成

## 🔧 使用方式

### 方式 1：Python 代码调用
```python
from run_pipeline_user import run_pipeline

# 方式 A：默认自动模式
input_data = {"type": "text", "content": "..."}
video_path = run_pipeline(input_data)  # 生成 3 个 scene

# 方式 B：指定 scene_count
video_path = run_pipeline(input_data, scene_count=5)  # 生成 5 个 scene
```

### 方式 2：命令行调用
```bash
# 自动模式（与原有行为完全相同）
python run_pipeline_user.py

# 手动指定 3 个 scene
python run_pipeline_user.py 3

# 手动指定 5 个 scene
python run_pipeline_user.py 5
```

### 方式 3：修改 config.json
```json
{
  "scene_count": 5
}
```
然后运行：
```bash
python scene_planner.py
```

## 📊 验证结果

| 功能项 | 状态 | 备注 |
|--------|------|------|
| scene_planner 支持 scene_count | ✓ | 已实现，已测试通过 |
| run_pipeline 参数透传 | ✓ | 已实现 |
| config.json 读写 | ✓ | 正常工作 |
| 默认模式保留 | ✓ | scene_count=None 时生成 3 个 scene |
| 显式指定 3 | ✓ | 生成 3 个 scene |
| 显式指定 5 | ✓ | 已确认生成 5 个 scene |
| 日志输出 [SCENE_COUNT] | ✓ | 已添加标记 |
| 不破坏主链 | ✓ | 仅添加参数，不修改核心逻辑 |

## 🎨 架构设计

### 控制流
```
run_pipeline(scene_count=X)
    ↓
_update_config_scene_count(X)
    ↓
写入 config.json: {"scene_count": X}
    ↓
subprocess: scene_planner.py
    ↓
读取 config.json 中的 scene_count
    ↓
build_scene_plan(scene_count=X)
    ↓
if X == None:    生成 3 个 scene（默认）
if X == 5:       拆分 explanation，生成 5 个 scene
    ↓
写出 scene_plan.json
```

### 数据拆分策略（scene_count=5 时）
```
hook               → scene 0 (intro)
explanation (拆 3) → scenes 1-3 (body_1, body_2, body_3)
conclusion         → scene 4 (outro)
```

拆分方法：按换行符分割，若不足则均匀分配

## ✨ 关键特性

1. **完全向后兼容**
   - 默认不传 scene_count 时，行为完全相同
   - 旧代码无需任何改动

2. **最小化侵入**
   - scene_planner.py：仅添加 split_text_into_parts() + 1 个参数
   - run_pipeline_user.py：仅添加 1 个 helper 函数 + 参数
   - 核心逻辑未修改

3. **清晰的日志**
   - `[SCENE_COUNT] mode=auto/fixed`
   - `[SCENE_COUNT] target_scene_count=X`
   - `[SCENE_COUNT] final_scene_count=X`

4. **灵活的配置**
   - 支持 Python 代码参数
   - 支持命令行参数
   - 支持 config.json 配置

## 🚀 下一步可选改进

当前实现了最小化版本（支持 3 和 5），后续可选改进：

1. **Task34：扩展参数范围**
   - 支持任意整数的 scene_count

2. **Task35：智能拆分算法**
   - 基于 NLP 的句子识别而非换行符
   - 更好的内容均衡分配

3. **Task36：UI 支持**
   - 在 app.py / app_streamlit.py 添加 scene_count 选择器

4. **Task37：性能优化**
   - scene_count 缓存
   - 预计算多版本 scene_plan

## 📝 边界声明

**严格遵守要求的边界**：
- ✅ 不重构主链
- ✅ 不破坏当前自动切分逻辑
- ✅ 不修改 video_engine.py 核心行为
- ✅ 不破坏 user_scene_asset_override 功能
- ✅ 保留当前自动模式（默认）
- ✅ 路径统一via modules/project_paths.py
- ✅ 提供完整文件（非零碎 patch）
- ✅ 包含独立测试脚本
- ✅ 日志可观察

## 🎓 技术总结

| 技术点 | 实现方案 |
|--------|--------|
| 参数透传 | via config.json（最小侵入）|
| 场景拆分 | 按换行符按比例分割 |
| 兼容性 | scene_count=None 保持原逻辑 |
| 测试隔离 | 独立测试脚本，直接调用 API |
| 编码处理 | UTF-8 编码兼容 Windows GBK |

## ✅ 交付清单

- [x] 修改 scene_planner.py，支持 scene_count 参数
- [x] 修改 run_pipeline_user.py，支持参数透传
- [x] 更新 config.json 配置文件
- [x] 创建 tests/test_scene_count_control_runner.py 测试套件
- [x] 创建此完成报告文档
- [x] 验证默认模式保留
- [x] 验证 scene_count=3 生成 3 个 scene
- [x] 验证 scene_count=5 生成 5 个 scene
- [x] 验证日志输出 [SCENE_COUNT]
- [x] 验证不破坏主链

---

**Project Status**: ✅ **COMPLETE AND VERIFIED**

**Last Updated**: 2025-04-05
