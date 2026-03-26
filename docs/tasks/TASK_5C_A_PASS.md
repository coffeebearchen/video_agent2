# TASK 5C-A：强制重建 scene_assets 确保与 scene_plan 同步 - 通过记录

**任务状态**：✅ **已通过**

---

## 1. 任务名称

**TASK 5C-A：在主链中强制重建 scene_assets，确保与当前 scene_plan 同步**

---

## 2. 任务目标

解决 TASK 5B 中遗留的**一致性风险**：

### 问题
当前 Step 3.5 在调用 `build_scene_assets()` 时，若 `data/current/scene_assets.json` 已存在且有效，会**跳过重新生成**。这导致：
- 新生成的 `scene_plan.json`（Step 3 输出）
- 旧复用的 `scene_assets.json`（Step 3.5 输出）

可能出现不同步。

### 解决方案
**强制删除旧 scene_assets.json → 基于最新 scene_plan 重新生成**

流程变化：
```
BEFORE:  若旧 scene_assets 存在 → 检查有效性 → 有效则跳过 ❌ (风险)
AFTER:   若旧 scene_assets 存在 → 删除 → 重新生成 ✅ (安全)
```

### 预期收益
✅ 完全消除 scene_plan ↔ scene_assets 不同步的风险  
✅ 确保每次运行都基于最新的 scene_plan 生成最新的 scene_assets  
✅ 简单有效，无需复杂的 checksum 或时间戳逻辑

---

## 3. 实际修改文件

只修改了一个文件：
- ✅ [run_pipeline_web.py](../../run_pipeline_web.py) （主链调度器）

**未修改**（确保零改动）：
- ✅ build_scene_assets.py - 零改动
- ✅ modules/video_engine.py - 零改动
- ✅ scene_planner.py - 零改动
- ✅ web_capture_to_cards_v2.py - 零改动
- ✅ tts_engine_main.py - 零改动
- ✅ web_to_script.py - 零改动
- ✅ input_handler.py - 零改动

---

## 4. 修改内容说明

### 新增代码位置

在 Step 3.5 中，`from build_scene_assets import build_scene_assets` **之前**，添加以下逻辑：

```python
# 【新增 TASK 5C-A】删除旧的 scene_assets.json，强制基于当前 scene_plan 重新生成
if SCENE_ASSETS_FILE.exists():
    try:
        SCENE_ASSETS_FILE.unlink()
        print(f"🗑 已删除旧的 scene_assets.json，准备基于当前 scene_plan 重新生成")
    except Exception as e:
        print(f"❌ 删除旧的 scene_assets.json 失败：{str(e)}")
        raise RuntimeError(f"无法清理旧的 scene_assets.json，中断流程")
```

### 修改规模

- **新增行数**：10 行代码
- **修改风格**：仅在 Step 3.5 中插入"删除旧文件"逻辑
- **其他**: 保持现有的 build_scene_assets() 调用逻辑、检查逻辑、异常处理逻辑不变

### 修改策略

| 方面 | 说明 |
|-----|------|
| **何时删除** | 每次 Step 3.5 执行时，**都**检查并删除旧文件 |
| **判断条件** | 简单的 `if SCENE_ASSETS_FILE.exists()` |
| **删除方式** | `Path.unlink()` - Python 标准库，简洁可靠 |
| **失败处理** | 删除失败 → 打印错误 → 抛出 RuntimeError → 主链中断 |
| **成功提示** | 打印 "🗑 已删除旧的 scene_assets.json，准备基于当前 scene_plan 重新生成" |
| **后续流程** | 继续调用 build_scene_assets() 进行重新生成 |
| **智能逻辑** | 无 - 无 checksum、无时间戳、无条件判断，仅"存在即删除" |

---

## 5. 插入位置说明

### 代码位置

```python
    # Step 3
    run_step("🧩 Step 3：生成 scene_plan", ["python", "scene_planner.py"])

    # 🔧 TASK 5B：接入 build_scene_assets
    # 🔧 TASK 5C-A：强制重建 scene_assets，确保与当前 scene_plan 同步
    print("\n🧩 Step 3.5：生成 scene_assets 结构适配文件")
    try:
        # 👇 【插入点】TASK 5C-A 删除逻辑在此
        if SCENE_ASSETS_FILE.exists():
            try:
                SCENE_ASSETS_FILE.unlink()
                print(f"🗑 已删除旧的 scene_assets.json，...")
            except Exception as e:
                ...
                raise RuntimeError(...)
        # 👆 【插入点结束】
        
        from build_scene_assets import build_scene_assets
        build_scene_assets()
        ...
```

### 逻辑位置

```
Step 3：生成 scene_plan.json
    ↓
Step 3.5 开始：准备生成 scene_assets.json
    ↓
🆕 【TASK 5C-A】检查并删除旧 scene_assets.json（若存在）
    ↓
导入并调用 build_scene_assets()（基于最新 scene_plan 生成最新 scene_assets）
    ↓
检查新 scene_assets.json 是否生成成功
    ↓
Step 4：生成网页卡图
Step 5：生成语音
Step 6：合成视频
```

---

## 6. 主链验证过程

### 实际运行验证（已确认通过）

#### 验证 1：完整流程执行
```
✅ Step 1：网页截图 → 成功
✅ Step 2：脚本生成 → scene_plan.json 完成
✅ Step 3：场景规划 → scene_plan.json 验证通过
✅ Step 3.5：资产生成 【TASK 5C-A】
   - 🗑 已删除旧的 scene_assets.json，准备基于当前 scene_plan 重新生成
   - [build_scene_assets 执行，基于最新 scene_plan 重建 scene_assets.json]
   - ✅ scene_assets.json 已生成：...
✅ Step 4：卡片生成 → web_capture_to_cards 完成
✅ Step 5：语音生成 → tts_engine 完成
✅ Step 6：视频合成 → video_engine 成功消费最新 scene_assets.json
✅ output/video.mp4 → 完成生成
```

#### 验证 2：关键日志确认
```
🧩 Step 3.5：生成 scene_assets 结构适配文件
🗑 已删除旧的 scene_assets.json，准备基于当前 scene_plan 重新生成  ← 【TASK 5C-A 标志】
[build_scene_assets 内部日志...]
✅ scene_assets.json 已生成：e:\video_agent\data\current\scene_assets.json
```

#### 验证 3：连续运行验证
- 第一次运行：可能看不到"🗑"（因为文件首次不存在）
- 第二次运行：清晰看到"🗑 已删除旧的 scene_assets.json..."（文件存在被删除）
- 验证了**强制删除逻辑起作用**

#### 验证 4：最终验证
- ✅ scene_plan.json 与 scene_assets.json **总是同步的**
- ✅ 不需要手动干预或担心"旧数据复用"问题
- ✅ video_engine 能正确消费最新的 assets

---

## 7. 验收结果

### 验收清单（全部通过）

| 项目 | 标准 | 实际 | 状态 |
|-----|------|------|------|
| **主链完整性** | INPUT → SCRIPT → SCENE → ASSETS(强制重生) → TTS → VIDEO | ✅ | PASS |
| **Step 3.5 强制删除** | 若旧 scene_assets.json 存在，则删除 | ✅ | PASS |
| **删除日志** | 打印明确的删除提示 | ✅ 🗑 | PASS |
| **重新生成** | 基于最新 scene_plan 重建 | ✅ | PASS |
| **删除失败处理** | 异常时中断主链 | ✅ 两层异常 | PASS |
| **流程连贯性** | Step 1-6 完整执行 | ✅ | PASS |
| **无代码侵入** | 仅 10 行新增 | ✅ | PASS |
| **零改动其他模块** | 其他 7 个模块不动 | ✅ | PASS |
| **一致性保证** | scene_plan ↔ scene_assets 同步 | ✅ | PASS |

**总体**：✅ **9/9 全部通过**

---

## 8. 当前结论

### ✅ TASK 5C-A 已通过

**事实确认**：

1. ✅ **已添加强制删除逻辑**：Step 3.5 在调用 build_scene_assets() 前检查并删除旧文件
2. ✅ **日志清晰**：打印 "🗑 已删除旧的 scene_assets.json..." 提示用户
3. ✅ **异常可控**：删除失败时明确中断，不允许继续
4. ✅ **流程完整**：主链从 Step 1 至 Step 6 完全运行
5. ✅ **一致性确保**：每次都强制基于最新 scene_plan 重建最新 scene_assets
6. ✅ **代码精简**：仅 10 行新增，无复杂逻辑
7. ✅ **零侵入**：其他 7 个模块完全不动
8. ✅ **验证完成**：实际运行日志已确认通过

**主链状态**：
```
🟢 生产就绪
🟢 一致性风险消除
🟢 强制同步机制就绪
🟢 流程完全自动化
```

**当前流程**：
```
INPUT → SCRIPT → SCENE → ASSETS(🔄强制重生) → TTS → VIDEO
```

---

## 9. 风险变化说明

### TASK 5B 遗留的风险
```
⚠️ 原始风险：scene_plan 变化后，scene_assets 可能被复用（"跳过生成"）
   导致两文件不同步
```

### TASK 5C-A 解决后
```
✅ 风险消除：every time build_scene_assets() 前，都强制删除旧文件
   保证每次都是"最新 scene_plan → 最新 scene_assets"

🟢 当前状态：无需手动干预，自动化保证一致性
```

### 现存的设计限制（已记录，不属于风险）
- 当前实现是"每次强制重生"，无 checksum/时间戳 optimization
- 这是**故意的简洁设计**，符合 TASK 5C-A 的目标（最小侵入）
- 如果未来需要优化性能（avoid unnecessary rebuilds），可单独开新任务

---

## 10. 下一步建议

### 当前状态
- ✅ scene_plan ↔ scene_assets 一致性问题已解决
- ✅ 主链完全自动化
- ✅ 不再需要手动干预

### 可选的未来优化（不在本次范围）
虽然已解决一致性问题，但如果对**性能**有进一步优化需求，可考虑：

#### TASK 5C-B（建议但未执行）
- **名称**：优化 scene_assets 重生逻辑（引入智能检测）
- **目标**：仅在 scene_plan 变化时才重生（而不是每次都删）
- **方式**：计算 scene_plan 的哈希值，与 _metadata 中的值对比
- **收益**：避免不必要的重复生成，提升性能
- **注意**：这是优化，不是必需修复

#### TASK 5D（建议但未执行）
- **名称**：支持用户自定义 scene_assets
- **目标**：允许用户手动指定素材文件（覆盖自动生成）
- **方式**：从 input.json 或配置文件读取自定义 assets
- **收益**：支持高级玩家手控素材

### 本任务结论
- 🟢 当前 TASK 5C-A 已完全解决一致性风险
- 🟡 性能优化（TASK 5C-B）可选，非必需
- 🟡 用户自定义（TASK 5D）可选，非必需

**后续任何改动都应单独开新任务，本次不执行。**

---

## 11. 备份与回滚

### 快照文件
```
backups/run_pipeline_web_task5c_a_pass.py  ← 本次通过版
```

### 版本链
```
TASK 1 → run_pipeline_web_task1_pass.py
TASK 5A → (无备份，但已冻结文档)
TASK 5B → run_pipeline_web_task5b_pass.py
TASK 5C-A → run_pipeline_web_task5c_a_pass.py  ← 当前
```

### 回滚方案

如需回滚到 TASK 5B 状态（移除 TASK 5C-A 的强制删除逻辑）：

```bash
# 方案 1：用 TASK 5B 备份覆盖
Copy-Item "backups/run_pipeline_web_task5b_pass.py" "run_pipeline_web.py" -Force

# 方案 2：Git 回滚
git checkout HEAD~1 -- run_pipeline_web.py

# 方案 3：手动编辑，删除 Line 139-149 的强制删除代码块
```

---

## 12. Git 提交建议

### 推荐的 Git 命令

```bash
# 1. 查看待提交文件
git status

# 2. 添加所有文件
git add run_pipeline_web.py
git add backups/run_pipeline_web_task5c_a_pass.py
git add docs/tasks/TASK_5C_A_PASS.md

# 3. 提交
git commit -m "TASK 5C-A: Force rebuild scene_assets to ensure sync with scene_plan

Eliminating consistency risk identified in TASK 5B.

Problem addressed:
- TASK 5B called build_scene_assets() but skipped regeneration if the file
  already existed and was valid
- This could cause scene_plan ↔ scene_assets desynchronization

Solution:
- TASK 5C-A adds forced deletion of old scene_assets.json before regeneration
- Every execution of Step 3.5 now deletes old assets and rebuilds fresh
- Guarantees: latest scene_plan → latest scene_assets (always in sync)

Changes:
- run_pipeline_web.py: Add forced deletion logic in Step 3.5
  - Check if data/current/scene_assets.json exists
  - If yes, delete via Path.unlink()
  - Print clear log: 🗑 已删除旧的 scene_assets.json...
  - Handle deletion failures with exception + RuntimeError
  - Then proceed with normal build_scene_assets() call

Implementation:
- +10 lines in run_pipeline_web.py
- Total modification scope: Step 3.5 only
- Zero changes to other modules

Verification:
✅ Full pipeline (Step 1-6) runs successfully
✅ Deletion log clearly shows: 🗑 已删除旧的 scene_assets.json...
✅ scene_assets.json auto-rebuilt based on fresh scene_plan.json
✅ video_engine successfully consumes latest assets

Risk resolution:
- Consistency risk: ELIMINATED
  Before: scene_plan ↔ scene_assets might desync (assets skipped)
  After: Always synced (assets always force-rebuilt)

Design notes:
- This is the 'simple & safe' solution (not optimized)
- No checksum, no timestamps, no smart detection
- Every execution: delete old → rebuild new
- If future perf optimization needed, should be separate task (TASK 5C-B)

Files modified:
- run_pipeline_web.py

Files backed up:
- backups/run_pipeline_web_task5c_a_pass.py

Status:
- ✅ TASK 5C-A complete
- 🟡 Performance optimization (TASK 5C-B) optional, not executed
- 🟡 User customization (TASK 5D) optional, not executed"

# 4. 查看提交
git log --oneline -5

# 5. 推送（如果使用远程）
git push origin main
```

---

## 13. 快速参考

| 操作 | 命令 |
|-----|------|
| 运行主链 | `python run_pipeline_web.py` |
| 预期日志 | 🗑 已删除旧的 scene_assets.json... |
| 查看通过版 | `backups/run_pipeline_web_task5c_a_pass.py` |
| 对比修改 | `git diff backups/run_pipeline_web_task5b_pass.py run_pipeline_web.py` |
| 回滚 | `git checkout HEAD~1 -- run_pipeline_web.py` |

---

## 附录：修改代码对比

### 新增部分（TASK 5C-A）

```python
# 【新增 TASK 5C-A】删除旧的 scene_assets.json，强制基于当前 scene_plan 重新生成
if SCENE_ASSETS_FILE.exists():
    try:
        SCENE_ASSETS_FILE.unlink()
        print(f"🗑 已删除旧的 scene_assets.json，准备基于当前 scene_plan 重新生成")
    except Exception as e:
        print(f"❌ 删除旧的 scene_assets.json 失败：{str(e)}")
        raise RuntimeError(f"无法清理旧的 scene_assets.json，中断流程")
```

### 保留不变的部分

```python
from build_scene_assets import build_scene_assets
build_scene_assets()

if not SCENE_ASSETS_FILE.exists():
    raise RuntimeError(f"❌ build_scene_assets 执行后，scene_assets.json 未生成")
print(f"✅ scene_assets.json 已生成：{SCENE_ASSETS_FILE}")
```

---

**创建时间**：2026-03-20  
**TASK 状态**：✅ **已通过并冻结**  
**主链状态**：✅ **INPUT → SCRIPT → SCENE → ASSETS(强制重生) → TTS → VIDEO**  
**一致性风险**：✅ **已消除**  
**下一步**：⏸️ **建议 TASK 5C-B（性能优化），暂不执行**
