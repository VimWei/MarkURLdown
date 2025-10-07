## MarkdownAll 启动流程梳理（基于当前 develop 分支）

本文档梳理自 commit e70666e7f9fa05ca16142758da527331d6d9e0a7 以来的 GUI 启动相关结构与职责，并对比旧版（v0.9.4，commit 46aae8c3…）的设计，提出清理与收敛建议。

### 1. 旧版启动结构（v0.9.4 时代）
- `ui/pyside/gui.py`
  - 承担“主窗口类 + 业务逻辑 + UI 控件”的单体职责。
  - 含 `Translator`、主界面构建、事件处理、会话读写等。
- `ui/pyside/splash.py`
  - 选择/构造启动图并显示 `QSplashScreen`。
- `launch.py`
  - 程序入口：创建 `QApplication`、显示 Splash、构造 `gui.PySideApp`（或等价窗口）、进入事件循环。

特征：职责集中在 `gui.py`，启动入口简单直接，但 UI 与配置/服务等逻辑高度耦合，可测试性较弱。

### 2. 新版启动结构（当前）
涉及文件：
- `src/markdownall/launch.py`
- `src/markdownall/ui/pyside/splash.py`
- `src/markdownall/ui/pyside/main_window.py`
- `src/markdownall/ui/pyside/startup_manager.py`
- `src/markdownall/ui/pyside/error_handler.py`
- `src/markdownall/ui/pyside/gui.py`（保留旧名，但已演化/重构用途）

#### 2.1 入口 `launch.py`
职责：
- 通过 `show_immediate_splash()` 创建 `QApplication` + `QSplashScreen`。
- 读取 `data/sessions/settings.json`，解析语言等轻量设置。
- 基于语言决定启动提示文案，显示进度信息。
- 构造新版 `MainWindow(root_dir, settings)`，显示窗口，结束 Splash，并进入 `app.exec()`。

特征：
- `launch.py` 不承载 UI 结构，只负责“引导 + 总装配”。

#### 2.2 启动画面 `splash.py`
职责：
- 选择启动图片（assets 下多张 webp，或用纯色占位）。
- 创建 `QSplashScreen` 并显示，设置 Qt 样式（Fusion）以统一观感。

特征：
- 纯 UI 辅助模块，与业务无关。

#### 2.3 主窗口 `main_window.py`
职责：
- 新版主窗口（`MainWindow`）的实现：分页（`Basic/Webpage/Advanced/About`）、
  组件（`CommandPanel/LogPanel`）、Splitter 布局、现代主题应用、进度与事件处理等。
- 通过服务层访问业务：
  - `ConfigService`（封装 `config/` 层的 `ConfigManager` 模型与持久化）
  - `StartupService`（启动期业务初始化）
- 组合 UI 辅助与系统能力：
  - `StartupManager`（UI 启动阶段反馈/节拍）
  - `ErrorHandler`（集中错误处理与上报）
  - `MemoryOptimizer`（运行期内存调优）

特征：
- 职责更清晰：UI 仅做展示与交互，业务通过 service 层对接，提升可测试性与扩展性。

#### 2.4 UI 启动管理 `startup_manager.py`
职责：
- 负责 UI 侧的“启动阶段”节拍（计时器驱动），发出阶段进度信号。
- 委托 `StartupService` 完成业务初始化（配置加载、设置加载等），自身专注于 UI 分阶段描述与反馈。

特征：
- 将“业务初始化”和“UI 启动阶段”解耦，便于测试与维护。

#### 2.5 集中错误处理 `error_handler.py`
职责：
- 统一捕获与记录错误（文件 `data/log/errors.log`），提供用户提示（QMessageBox）。
- 提供基础恢复策略与性能告警（依赖 `QTimer`、可选 `psutil`）。

特征：
- 从主窗口抽离错误与性能方面关注点，保持主窗口聚焦 UI 交互逻辑。

#### 2.6 `gui.py` 的现状与定位
- 旧文件名延续，但新版已将“核心主窗口”迁移到 `main_window.py`；
- 如需保留 `PySideApp` 符号给外部/测试使用，建议仅作为“别名或轻量包装”指向 `MainWindow`；
- 若无强依赖，长期建议对外统一入口为 `MainWindow`，并在 `__init__.py` 导出。

### 3. 启动调用链（当前）
1. `launch.main()`
   - `app, splash = show_immediate_splash()`
   - 读取 `settings.json`（语言等）
   - 计算启动消息文案并调用 `_emit_startup_progress`
   - `window = MainWindow(root_dir, settings)`
   - `window.show(); splash.finish(window); app.exec()`
2. `MainWindow.__init__`
   - 组装页面与组件、应用主题、连接信号、创建服务层对象
   - 通过 `ConfigService`/`StartupService` 完成配置与设置加载
   - `StartupManager` 驱动 UI 启动阶段反馈（可选）
3. 运行期
   - `ErrorHandler` 处理错误并记录日志
   - `MemoryOptimizer` 在需要时优化运行期参数

### 4. 与旧版的关键差异
- 旧版：`gui.py` 单体包揽 UI + 业务；入口直接构造 `PySideApp`。
- 新版：
  - UI 与业务分层：`MainWindow` 只负责 UI，业务通过 `services/` 接口；
  - 启动解耦：`launch.py` 聚焦装配与引导，`splash.py` 只负责启动画面；
  - 增强可测试性：可对 `services`、`startup_manager`、`error_handler` 分别做单测/桩替换；
  - 增强可维护性：职责分散到更小的模块，便于迭代。

### 5. 可以删除或合并的历史遗留项（建议）
- 若无外部代码再直接依赖旧版 `gui.PySideApp` 的具体实现：
  - 将 `PySideApp` 明确设为 `MainWindow` 的别名或极薄包装；
  - 在 `ui/pyside/__init__.py` 导出 `MainWindow` 为主入口，逐步引导外部改用 `MainWindow`。
- 清理 UI 层中不应存在的配置持久化逻辑：
  - 已迁移到 `config/` + `services/`，确保 UI 仅通过服务访问配置；
- `startup_manager.py` 如仅用于进度演示且未被调用：
  - 可在 `MainWindow` 内部统一使用或暂时下线，避免“概念存在但未参与流程”；
- `error_handler.py` 的性能监控（`psutil`）若非强需求：
  - 可降级为可选特性（捕获 ImportError 静默），或转移到服务层；
- 资源定位、主题加载等若在 `main_window.py` 与页面/组件重复：
  - 收敛到 `styles/theme_loader.py` 或统一工具模块。

### 6. 推荐的目标结构（对外 API 与内部职责）
- 对外启动：
  - CLI/入口脚本调用 `markdownall.launch:main`
  - `main()` 只做：Splash + 读取轻量设置 + 构造 `MainWindow` + 进入事件循环
- UI 层：
  - `ui/pyside/main_window.py`：主窗口 + 分页 + 组件 + 主题 + 事件
  - `ui/pyside/splash.py`：Splash 纯 UI
  - `ui/pyside/__init__.py`：导出 `MainWindow`、`show_immediate_splash`
  - `ui/pyside/gui.py`：若必须保留旧符号，保持为 `PySideApp = MainWindow`
- 业务与服务：
  - `config/`：配置模型与持久化
  - `services/`：封装业务流程，供 UI 调用
  - `utils/`：`memory_optimizer` 等通用工具
- 辅助：
  - `startup_manager.py`（可选）：若确有 UI 启动阶段需求，确保确实被调用；否则下线。
  - `error_handler.py`：集中错误处理（保留，但确保弱依赖、可测试）

### 7. 近期清理建议（行动项）
- 收敛入口：
  - 保持 `launch.py` → `MainWindow`（不要回退到旧 GUI）；
  - `gui.py` 若无必要逻辑，改为显式 `PySideApp = MainWindow`，并注明兼容用途；
- 移除 UI 内直接读写配置的代码段，统一走 `ConfigService`；
- 若 `StartupManager` 当前未被流程实际使用：
  - 在 `MainWindow` 中接入其进度信号；或暂时移除该模块，待后续确立使用场景再恢复；
- `error_handler`：
  - 确保不会在无事件循环/无显示环境下触发 GUI 操作（测试中可桩替换 QMessageBox）；
  - `psutil` 导入失败时静默降级。
- 测试对齐：
  - 将仍依赖旧 UI 包路径/符号的测试更新为新结构（如已迁移 `ConfigManager` 导入路径）。

---
如需，我可以在后续提交中：
- 将 `gui.py` 明确简化为 `PySideApp = MainWindow`；
- 在 `ui/pyside/__init__.py` 统一导出入口；
- 标注/移除未使用的 UI 启动管理逻辑；
- 提交一份具体的删除/合并清单与对应 edits。
