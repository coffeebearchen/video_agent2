# Mainline Cleanup Report

## A. 当前主运行链识别结果

### 当前页面入口
- 当前 formal dashboard 页面入口：`/content-processor`
- Route 文件：`frontend/routes/content_processor.py`
- Template 文件：`templates/content_processor/dashboard.html`
- 注册入口：`app.py` 中 `register_content_processor_routes(app)`
- 判定依据：`app.py` 明确注册 formal route；route 直接 `render_template("content_processor/dashboard.html")`

### 前端主链文件
- `templates/content_processor/dashboard.html`
  - 作用：当前 dashboard DOM 结构
  - 判定依据：被 `/content-processor` route 直接渲染；内部直接挂载当前 CSS/JS
- `static/js/content_processor/dashboard.js`
  - 作用：当前 dashboard 的 Generate / A/B / Confirm / Regenerate / Structured Editor / Reference Media 前端行为
  - 判定依据：由 `dashboard.html` 直接 `<script type="module">` 引用
- `static/css/content_processor/dashboard.css`
  - 作用：当前 dashboard 的全部样式
  - 判定依据：由 `dashboard.html` 直接 `<link rel="stylesheet">` 引用

### 功能主链
- Generate
  - 前端：`dashboard.js -> handleGenerate() -> requestContentPackage() -> fetchGeneratedPackage()`
  - 后端：`frontend/routes/content_processor.py -> /content-processor/generate -> build_content_package()`
- Generate A/B
  - 前端：`dashboard.js -> requestABPackages()`
  - 后端：复用同一个 `/content-processor/generate`，调用两次
  - 说明：A/B 是前端 compare 层，不是独立后端链
- Confirm
  - 前端：`dashboard.js -> confirmCurrentContentPackage()`
  - 说明：当前是前端状态更新，无后端调用
- Regenerate
  - 前端：`dashboard.js -> regenerateCurrentContentPackage() -> requestContentPackage()`
  - 后端：仍复用 `/content-processor/generate`
- Structured Editor
  - 前端：`dashboard.js -> populateEditorFromPackage() / renderEditor() / handleManualEditOpen()`
  - 说明：当前是前端结构化编辑层
- Apply Edit
  - 前端：`dashboard.js -> buildPackageFromEditor() -> applyManualEdit()`
  - 说明：当前只覆盖前端当前 package，无后端调用
- Reference Media 输入
  - 前端：`dashboard.html` file inputs + `dashboard.js -> handleReferenceFilesChange() / buildGenerateFormData()`
  - 后端：`content_processor.py -> _read_generate_request() -> build_reference_media()`
  - 存储与结构化：`modules/content_processor/reference_media_store.py`
  - 注入生成：`modules/content_processor/content_package_builder.py`

### 后端主链
- `/content-processor`
  - 文件：`frontend/routes/content_processor.py`
  - 函数：`content_processor_dashboard()`
- `/content-processor/generate`
  - 文件：`frontend/routes/content_processor.py`
  - 函数：`content_processor_generate()`
- 当前 content package 真实生成入口
  - 文件：`modules/content_processor/content_package_builder.py`
  - 函数：`build_content_package()`
  - 下游依赖：`feedback_mapper.py`、`feedback_adapter.py`、`modules/prompt_builder.py`、`modules/style_prompt_enhancer.py`、`modules/llm_client.py`

## B. 主链冻结清单

1. `app.py`
   - 分类：Mainline
   - 作用：当前 Flask 进程入口，注册 formal content processor route
   - 当前是否被真实调用：是
   - 是否禁止移动/删除：是

2. `frontend/routes/content_processor.py`
   - 分类：Mainline
   - 作用：formal dashboard route 与 generate API
   - 当前是否被真实调用：是
   - 是否禁止移动/删除：是

3. `templates/content_processor/dashboard.html`
   - 分类：Mainline
   - 作用：当前 dashboard 模板
   - 当前是否被真实调用：是
   - 是否禁止移动/删除：是

4. `static/js/content_processor/dashboard.js`
   - 分类：Mainline
   - 作用：当前 dashboard 交互主链
   - 当前是否被真实调用：是
   - 是否禁止移动/删除：是

5. `static/css/content_processor/dashboard.css`
   - 分类：Mainline
   - 作用：当前 dashboard 样式主链
   - 当前是否被真实调用：是
   - 是否禁止移动/删除：是

6. `modules/content_processor/content_package_builder.py`
   - 分类：Mainline
   - 作用：formal content package 生成入口
   - 当前是否被真实调用：是
   - 是否禁止移动/删除：是

7. `modules/content_processor/reference_media_store.py`
   - 分类：Mainline
   - 作用：reference media 落盘与结构化
   - 当前是否被真实调用：是
   - 是否禁止移动/删除：是

8. `modules/content_processor/feedback_mapper.py`
   - 分类：Mainline
   - 作用：feedback_text 结构化约束映射
   - 当前是否被真实调用：是
   - 是否禁止移动/删除：是

9. `modules/content_processor/feedback_adapter.py`
   - 分类：Mainline
   - 作用：fallback / normalize 后的反馈偏好应用
   - 当前是否被真实调用：是
   - 是否禁止移动/删除：是

10. `modules/prompt_builder.py`
    - 分类：Mainline
    - 作用：formal builder 复用的 prompt 基底
    - 当前是否被真实调用：是
    - 是否禁止移动/删除：是

11. `modules/style_prompt_enhancer.py`
    - 分类：Mainline
    - 作用：style mode prompt 增强
    - 当前是否被真实调用：是
    - 是否禁止移动/删除：是

12. `modules/llm_client.py`
    - 分类：Mainline
    - 作用：formal builder 的 LLM 调用出口
    - 当前是否被真实调用：是
    - 是否禁止移动/删除：是

## C. 旧链 / 备用链清单

1. `templates/index.html`
   - 分类：Legacy
   - 原因：由 `app.py` 的 `/` legacy demo route 使用，不是当前 formal dashboard
   - 当前是否被主页面调用：否
   - 建议：先保留为旧 demo，不删除

2. `static/app.js`
   - 分类：Legacy
   - 原因：只服务 legacy `/generate` 多风格 demo
   - 当前是否被主页面调用：否
   - 建议：归为旧链前端，不接 Expression Layer V1

3. `static/style.css`
   - 分类：Legacy
   - 原因：只服务 legacy `index.html`
   - 当前是否被主页面调用：否
   - 建议：先保留，不删除

4. `static/js/content_processor/mock_content_package.js`
   - 分类：Legacy
   - 原因：文档标注为 reference / fallback sample；当前 dashboard 未 import 未调用
   - 当前是否被主页面调用：否
   - 建议：归档候选，不接主链

5. `run_pipeline_legacy.py`
   - 分类：Legacy
   - 原因：文件名已明确标注 legacy
   - 当前是否被主页面调用：否
   - 建议：先归档候选，不删除

6. `run_pipeline_web - 副本.py`
   - 分类：Legacy
   - 原因：明显人工复制副本，不应作为正式入口
   - 当前是否被主页面调用：否
   - 建议：优先移出主视野

7. `expression_engine_backup.py`
   - 分类：Legacy
   - 原因：backup 文件
   - 当前是否被主页面调用：否
   - 建议：归档候选，不接新链

8. `run_directives_debug_backup.py`
   - 分类：Legacy
   - 原因：backup 文件
   - 当前是否被主页面调用：否
   - 建议：归档候选，不接新链

9. `modules/video_engine_backup.py`
   - 分类：Legacy
   - 原因：backup 文件
   - 当前是否被主页面调用：否
   - 建议：归档候选，不接新链

10. `_archive/`
   - 分类：Legacy
   - 原因：归档目录，明显非当前产品主链
   - 当前是否被主页面调用：否
   - 建议：继续保持归档，不参与接线

11. `backups/`
   - 分类：Legacy
   - 原因：备份目录，含多个历史通过版本
   - 当前是否被主页面调用：否
   - 建议：只作回溯参考，不接主链

## D. 探测 / 实验 / 不确定文件清单

### Probe / Sandbox

1. `runner/`
   - 分类：Probe / Sandbox
   - 原因：任务 runner / eval harness，明显不是当前产品页面链
   - 是否属于产品主链：否
   - 建议：后续统一移入 `sandbox` 体系视野

2. `tests/`
   - 分类：Probe / Sandbox
   - 原因：测试代码，不是产品运行入口
   - 是否属于产品主链：否
   - 建议：保留测试职责，不接 Expression Layer

3. `tools/`
   - 分类：Probe / Sandbox
   - 原因：辅助工具与校验脚本，不是 dashboard 主链
   - 是否属于产品主链：否
   - 建议：保留，但不要误接产品主页面

4. `test_asset_selector.py`
   - 分类：Probe / Sandbox
   - 原因：单文件测试
   - 是否属于产品主链：否
   - 建议：后续整理到 tests 或 sandbox

### Unknown

1. `run_pipeline_user.py`
   - 分类：Unknown
   - 原因：它是独立视频 pipeline 的用户入口，但不是当前 dashboard/content-processor 链
   - 风险：若误当成 dashboard 后端主链，会把 Expression Layer 接到另一套系统
   - 建议：标注为“并行链路”，暂不处理

2. `run_pipeline_web.py`
   - 分类：Unknown
   - 原因：从文档与调用看是现有视频 pipeline 的核心调度器，但当前 dashboard 完全未调用
   - 风险：非常高；误接会把 content processor 与旧视频主链混在一起
   - 建议：暂不移动，不纳入当前 dashboard 主链

3. `scene_planner.py`
   - 分类：Unknown
   - 原因：活跃于视频 pipeline，但不在当前 dashboard 路由链中
   - 风险：把 content package 直接接 сюда 会跨链
   - 建议：仅标为并行链路核心，不在本轮清理中处理

4. `build_scene_assets.py`
   - 分类：Unknown
   - 原因：被 `run_pipeline_user.py` 调用，是视频 pipeline 资产桥接层，不是当前 dashboard 主链
   - 风险：误接会直接跳过 formal content package 层级
   - 建议：保持独立，暂不处理

5. `modules/video_engine.py`
   - 分类：Unknown
   - 原因：活跃于视频生成链，但与当前 dashboard 无真实调用关系
   - 风险：属于后段渲染层，现阶段接入会越过当前 formal UI 主链边界
   - 建议：只做独立链标记，不并入 dashboard 主链

6. `main_generate_video.py`
   - 分类：Unknown
   - 原因：一键 CLI 入口，走 `run_pipeline`，不是当前 dashboard 所在链
   - 风险：入口名容易误导为当前主入口
   - 建议：标记为独立 CLI 入口

7. `app_streamlit.py`
   - 分类：Unknown
   - 原因：独立 UI 入口，调用 `run_pipeline_user`，不是当前 Flask dashboard
   - 风险：容易和当前 formal dashboard 混淆
   - 建议：标记为平行前端，不接当前 formal chain

8. `expression_engine.py`
   - 分类：Unknown
   - 原因：文件名相关，但当前 dashboard/content processor 链没有真实 import / 调用它
   - 风险：若后续 Expression Layer 直接接这里，可能接到旧表达体系
   - 建议：在人工确认前不要接

9. `asset_manager.py` / `asset_selector.py` / `modules/asset_selector.py` / `modules/asset_registry.py`
   - 分类：Unknown
   - 原因：资产层文件活跃于视频侧与工具侧，但当前 dashboard 未直接走到它们
   - 风险：文件名像“下游接点”，但目前不是 formal content-processor 的自然延伸
   - 建议：等待 expression 方案明确后再判断

10. `scene_editor.py`
   - 分类：Unknown
   - 原因：是独立桌面/UI 工具，不是当前 dashboard 页面
   - 风险：UI 名称和当前 editor 概念接近，容易误判
   - 建议：暂不处理

## E. 安全清理建议

### 1. 绝对不要碰的文件
- `app.py`
- `frontend/routes/content_processor.py`
- `templates/content_processor/dashboard.html`
- `static/js/content_processor/dashboard.js`
- `static/css/content_processor/dashboard.css`
- `modules/content_processor/content_package_builder.py`
- `modules/content_processor/reference_media_store.py`
- `modules/content_processor/feedback_mapper.py`
- `modules/content_processor/feedback_adapter.py`
- `modules/prompt_builder.py`
- `modules/style_prompt_enhancer.py`
- `modules/llm_client.py`

### 2. 可以先移出主视野，但当前不要真移动的
- `templates/index.html`
- `static/app.js`
- `static/style.css`
- `static/js/content_processor/mock_content_package.js`
- `run_pipeline_legacy.py`
- `run_pipeline_web - 副本.py`
- `expression_engine_backup.py`
- `run_directives_debug_backup.py`
- `modules/video_engine_backup.py`
- `backups/`
- `_archive/`
- `runner/`
- `tools/`
- root 下零散 `test_*.py`

### 3. 表达层接入时绝对不要接的点
- `static/js/content_processor/mock_content_package.js`
  - 原因：mock 样例，不是真实运行链
- `templates/index.html` / `static/app.js` / `static/style.css`
  - 原因：legacy demo，多风格旧页面
- `run_pipeline_legacy.py`
  - 原因：历史入口
- `run_pipeline_web - 副本.py`
  - 原因：复制副本
- `expression_engine_backup.py`
  - 原因：backup
- `backups/*` / `_archive/*`
  - 原因：历史快照，不应作为新链接点
- `runner/*`
  - 原因：任务验证器，不是产品功能层
- `tests/*`
  - 原因：测试 harness，不是运行入口

### 4. 高风险“看起来像能接，但当前不该接”的点
- `run_pipeline_user.py`
- `run_pipeline_web.py`
- `scene_planner.py`
- `build_scene_assets.py`
- `modules/video_engine.py`
- `expression_engine.py`

这些文件不是废代码，但它们属于另一条并行视频 pipeline。若 Expression Layer V1 以当前 dashboard 为基线，就不应直接接到这里。

## F. Expression Layer V1 的最安全接入点

### A. 最推荐接入点
- 文件：`modules/content_processor/content_package_builder.py`
- 函数：`build_content_package()`
- 层级位置：formal `/content-processor/generate` 后端生成层
- 原因：
  - 它是当前 dashboard Generate / A/B / Regenerate 共用的唯一正式生成入口
  - 已经接住 `feedback_text` 与 `reference_media`
  - 当前 content package 的 `input_sources`、prompt 构造、fallback 都在这里汇合
  - 如果后续要做 Expression Layer V1，最自然方式是：在 `build_content_package()` 生成完成后，新增一个“formal expression planning / handoff”层，而不是跳去旧视频 pipeline

### B. 次级安全接点
- 文件：`frontend/routes/content_processor.py`
- 函数：`content_processor_generate()`
- 层级位置：route / service 边界
- 原因：适合做 request/response 编排，但不适合塞表达细节逻辑

### C. 绝对不要接入的点
- `run_pipeline_web.py`
  - 原因：它是独立视频 pipeline 调度器，不是当前 dashboard 主链
- `run_pipeline_user.py`
  - 原因：CLI / 产品视频入口，不是当前 formal content package 页面
- `scene_planner.py`
  - 原因：已经是下游 scene 层，接这里会跳过当前 formal content package 边界
- `build_scene_assets.py`
  - 原因：已经是 scene asset 适配层，不是 content processor 层
- `modules/video_engine.py`
  - 原因：渲染层过深，接这里会造成结构倒挂
- `expression_engine.py`
  - 原因：当前未被 dashboard 主链调用，贸然接入风险高
