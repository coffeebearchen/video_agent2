# 【run_pipeline 行为规则｜V1 冻结版】

This document defines strict rules for modifying `run_pipeline_web.py`.

---

## 一、文件定位（必须明确）

`run_pipeline_web.py` 的唯一职责是：

👉 **主链调度器（Pipeline Orchestrator）**

负责：

- 输入分发（URL / TEXT）
- 调用既有模块
- 按固定顺序执行流程

不负责：

- 内容生成
- 素材选择
- 渲染逻辑
- 复杂算法

---

## 二、允许的操作（白名单）

仅允许以下操作：

### 1. 输入分发（允许）
- 判断 `type = url / text / future`
- 分流到不同入口逻辑

### 2. 调用已有模块（允许）
- 调用 web_capture
- 调用 script 生成模块
- 调用 scene_planner
- 调用 build_scene_assets
- 调用 TTS
- 调用 video_engine

### 3. 最小辅助函数（允许）
仅限：

- text → script.json 的轻量转换
- 不涉及复杂逻辑
- 不超过简单分句、封装

---

## 三、禁止操作（红线）

以下行为一律禁止：

### 1. 禁止变成业务逻辑容器
- 禁止写素材匹配逻辑
- 禁止写卡图渲染逻辑
- 禁止写复杂文本处理
- 禁止写策略逻辑

### 2. 禁止修改主链顺序
主链必须保持：

INPUT → SCRIPT → SCENE → ASSETS → TTS → VIDEO

不得调整顺序、不得跳步、不得重构

---

### 3. 禁止模块侵入
不得：

- 改写 web_capture.py
- 改写 video_engine.py
- 改写 scene_planner.py
- 改写 build_scene_assets.py
- 改写 tts_engine_main.py

---

### 4. 禁止“顺手优化”
不得：

- 重构结构
- 改变量命名
- 统一接口
- 优化性能
- 抽象新架构

---

### 5. 禁止扩展为平台
不得引入：

- 数据库
- 用户系统
- 向量检索
- 知识库
- API 服务层
- 前后端分离

---

## 四、修改原则（必须遵守）

### 1. 最小侵入原则
- 只改必要代码
- 不动无关逻辑

### 2. 分支隔离原则
- URL 模式完全不受影响
- TEXT 模式为新增分支

### 3. 可回滚原则
- 删除新增代码即可恢复原状态

### 4. 单任务原则
- 一次只做一件事
- 不允许叠加多个目标

---

## 五、演进方向（未来允许）

未来演进必须遵守：

👉 新能力优先“外移模块”

例如：

- text_to_script.py
- text_card_renderer.py

而不是继续往 `run_pipeline_web.py` 中堆积逻辑

---

## 六、核心总结

`run_pipeline_web.py` 只负责：

👉 **接入 + 调度**

绝不负责：

👉 **生成 + 决策 + 渲染**

任何偏离该原则的修改，视为违规。