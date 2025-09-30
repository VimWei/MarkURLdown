## MarkURLdown 源码迁移至现代 src 架构规划

本规划旨在将当前项目从根目录直放包的结构迁移为现代的 src 架构，并将运行时包重命名为 `src/markurldown/`，以与 `pyproject.toml` 中的项目名称语义一致且符合社区惯例。

### 目标
- 将所有源代码移动至 `src/` 目录下
- 将包从 `markitdown_app` 重命名为 `markurldown`
- 不引入兼容导入层，统一切换至新包名 `markurldown`
- 更新构建、测试与覆盖率配置，保持最小变更影响

### 新目录结构（目标）
- 源代码
  - `src/markurldown/` ← 由 `markitdown_app/` 平移并重命名
    - `__init__.py`（新增，导出公共 API）
    - 现有子模块平移：`core/`, `io/`, `services/`, `ui/`, `version.py`, `app_types.py` 等
- 顶层保留：`pyproject.toml`, `README.md`, `tests/`, `docs/`, `scripts/`
  - 入口文件将迁移为 `project.scripts` 控制的 console-script（见下文），不再需要根目录 `MarkURLdown.pyw/.py`

### 文件移动与映射
- `markitdown_app/*` → `src/markurldown/*`
  - `markitdown_app/core/...` → `src/markurldown/core/...`
  - `markitdown_app/io/...` → `src/markurldown/io/...`
  - `markitdown_app/services/...` → `src/markurldown/services/...`
  - `markitdown_app/ui/...` → `src/markurldown/ui/...`
  - `markitdown_app/app_types.py` → `src/markurldown/app_types.py`
  - `markitdown_app/version.py` → `src/markurldown/version.py`



### pyproject.toml 调整
切换为 src 布局并更新包名与覆盖率来源：

```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["markurldown*"]
exclude = ["log*", "output*", "sessions*", "tests*", "docs*"]

[tool.coverage.run]
source = ["markurldown"]
omit = [
  "*/tests/*",
  "*/test_*",
  "*/__pycache__/*",
  "*/migrations/*"
]
data_file = "tests/.coverage"
```

如需更强约束，可增加：

```toml
[tool.setuptools.package-dir]
"" = "src"
```

### 代码导入调整策略
- 批量将代码库中的 `import markitdown_app...` 替换为 `import markurldown...`
- 测试代码与脚本内的导入同样替换

建议替换顺序（可分 PR）：
1. 入口与应用层（如 `MarkURLdown.pyw`）
2. `services/`、`io/`
3. `core/`
4. `ui/` 与资源加载
5. `tests/` 与 `scripts/`

### 资源路径与文档更新
- `README.md` 与文档内的截图相对路径需要从 `markitdown_app/ui/assets/...` 更新为 `src/markurldown/ui/assets/...`
- 若运行时通过包内相对路径访问资源，推荐使用 `importlib.resources`，避免依赖工作目录：
  - `importlib.resources.files("markurldown.ui.assets")/...`
- 若发布轮子（wheel），确保打包包含静态资源：
  - 可启用 `include-package-data = true` 或使用 `package_data` 指定资源

### 测试与工具链
- pytest 配置无需大改（仍使用 `tests/`），覆盖率来源已切至 `markurldown`
- mypy/ruff/black/isort 等如基于包名或路径，需一并更新至新包名或 `src/` 根

### 入口脚本与启动方式（console-script）
- 统一采用 console-script 作为入口（推荐 `uv run markurldown`），移除根目录 `MarkURLdown.pyw/.py`
- 在 `pyproject.toml` 中新增脚本入口，例如：

```toml
[project.scripts]
markurldown = "markurldown.ui.pyside.gui:run_gui"
```

- 在代码侧新增/补充入口函数（若尚不存在）：
  - 复用或新增 `src/markurldown/ui/pyside/gui.py`，实现 `run_gui()`，负责初始化与启动 PySide 应用
  - 如需拆分，将 splash 相关逻辑放入 `src/markurldown/ui/pyside/splash.py`
- 可选：同时提供模块入口，支持 `python -m markurldown`：

```python
# src/markurldown/__main__.py
from markurldown.ui.pyside.gui import run_gui

def main() -> None:
    run_gui()

if __name__ == "__main__":
    main()
```

- 启动方式将从：
  - 旧：`uv run python MarkURLdown.pyw`
  - 新：`uv run markurldown`

### 迁移启动优化与 Splash 逻辑
为保留 `STARTUP_OPTIMIZATION.md` 描述的即时 Splash 与分阶段加载体验，需要将 `MarkURLdown.pyw` 中的启动逻辑迁移并模块化：

1) 新建模块与职责划分
- `src/markurldown/ui/pyside/splash.py`
  - 提供 `show_immediate_splash()`：创建 `QApplication`、尽快显示 `QSplashScreen`，返回 `(app, splash)`
  - 负责选择 `ui/assets` 下的随机 splash 图（若无则使用纯色 pixmap）
- `src/markurldown/ui/pyside/gui.py`
  - 提供 `run_gui()`：
    - 调用 `show_immediate_splash()`
    - 延迟导入重型依赖（如 `PySideApp`、配置加载）
    - 初始化主窗口、将 splash 切换至主窗体、进入事件循环
- 可选：`src/markurldown/__main__.py`
  - 提供 `main()` 调用 `run_gui()`，支持 `python -m markurldown`

2) 资源路径与定位
- 将原来通过根目录定位 `markitdown_app/ui/assets` 的方式，改为包内资源路径：
  - 推荐使用 `importlib.resources.files("markurldown.ui.assets")` 定位资源目录，避免依赖工作目录
  - Windows 与打包环境下路径一致，便于分发

3) 错误处理与用户提示
- 保留原有 try/except 包装，启动失败时打印堆栈，并使用 `QMessageBox.critical` 提示
- 确保异常分支也能安全创建最小 `QApplication` 环境以显示提示

4) 配置加载与会话目录
- 维持 portable app 现状：`sessions/`, `output/`, `log/` 均位于项目根目录，便于用户整体迁移与备份
- 未来计划：将上述目录统一迁移至项目根目录下的 `data/`（形成 `data/sessions/`, `data/output/`, `data/log/`），但本次迁移不做变动，仅在后续版本中执行并提供迁移脚本

5) 与现有 UI 的对接
- 原 `from markitdown_app.ui.pyside.gui import PySideApp` 替换为 `from markurldown.ui.pyside.gui import PySideApp`
- `run_gui()` 中按原顺序更新 splash 的提示文案，确保用户感知加载阶段

6) 验证要点
- `uv run markurldown` 能在 1s 内显示 splash（取决于本机环境）
- 随机 splash 图片可正常显示，或在缺失时使用纯色回退
- 主窗口稳定启动，功能与旧入口一致

7) 清理与启动脚本改造
- 删除根目录 `MarkURLdown.pyw`
- 保留并改造 VBS 启动脚本，使其调用新入口 `uv run markurldown`
  - 示例（`MarkURLdown.vbs`）：

```vb
Set oShell = CreateObject("WScript.Shell")
' 隐藏窗口启动（0），不等待（False）。如需等待结束，改为 True
oShell.Run "cmd /c uv run markurldown", 0, False
Set oShell = Nothing
```

- 更新 `README.md` 与 `STARTUP_OPTIMIZATION.md` 的启动命令与路径示例：统一为 `uv run markurldown`

 

### 版本管理与发布体系适配（release.py / .github / version.py）
为兼容 src 布局与新包名，需要同步更新版本管理与发布相关文件：

1) 版本模块位置与导入
- 移动：`markitdown_app/version.py` → `src/markurldown/version.py`
- 全局替换导入：

```diff
- from markitdown_app.version import get_version, get_app_title
+ from markurldown.version import get_version, get_app_title
```

- 更新文档：`docs/Version_management_guide.md` 中的示例导入替换为 `markurldown.version`

2) 发布脚本 `scripts/release.py`
- 若脚本直接读取/写入版本模块或导入它，更新为 `markurldown.version`
- 如脚本按路径定位包根，确保以 `src/` 为根解析（或使用 `importlib.resources`/`importlib.metadata` 从已安装包读取）
- 使用 `uv run` 执行检查与测试，确保与本项目工作流一致：

```bash
uv run pytest -q
uv run black --check .
uv run isort --check-only .
```

3) GitHub Actions（.github/workflows）
- CI 中安装 uv（官方安装脚本）并执行 `uv sync`
- 测试与构建步骤使用 `uv run`（如 `uv run pytest`、`uv build`）
- 覆盖率与测试路径已在本计划中切换为 `markurldown`

4) 自检清单
- 代码与文档不再出现 `markitdown_app.version` 的导入
- `uv run python scripts/release.py patch` 可正常运行（可 dry-run 验证）
- CI 能在新布局下成功安装依赖并通过测试

### 回滚策略
- 如需回滚：撤销 `src/` 物理移动、恢复包名 `markitdown_app`、移除 `project.scripts` 条目

### 风险与缓解
- 导入路径替换范围大：分批提交，确保每步测试通过
- 资源路径打包缺失：统一通过 `importlib.resources` 访问并确认打包配置
- 启动入口切换：在变更说明与 README 中明确从 `uv run python MarkURLdown.pyw` 迁移为 `uv run markurldown`

---

### 建议迁移步骤（最终顺序，可复用命令）

1) 建分支并准备移动

```powershell
git checkout -b feat/src-layout
```

2) 物理移动与重命名（不含兼容层）

```powershell
git mv markitdown_app src
Rename-Item src\markitdown_app src\markurldown
```

3) 更新 pyproject（src 布局 + 包名 + 覆盖率来源）
- 设置 `tool.setuptools.packages.find.where = ["src"]`
- `include = ["markurldown*"]`
- 覆盖率 `source = ["markurldown"]`

4) 设置 console-script 入口并实现入口函数

```toml
[project.scripts]
markurldown = "markurldown.ui.pyside.gui:run_gui"
```

- 在 `src/markurldown/ui/pyside/gui.py` 中实现/补充 `run_gui()`
- 将 splash 逻辑抽取到 `src/markurldown/ui/pyside/splash.py`
- 可选：添加 `src/markurldown/__main__.py` 支持 `python -m markurldown`

5) 替换导入路径（按模块分批）

```powershell
rg -n "markitdown_app" -g "!tests/htmlcov/**"
# 分批替换为 markurldown
```

6) 迁移启动优化逻辑与资源定位
- 将 `MarkURLdown.pyw` 的启动流程迁移至上一步入口函数
- 资产路径改为 `importlib.resources.files("markurldown.ui.assets")`

7) 删除旧入口并改造 VBS 启动脚本
- 删除根目录 `MarkURLdown.pyw`
- 将 `MarkURLdown.vbs` 改为调用：

```vb
Set oShell = CreateObject("WScript.Shell")
oShell.Run "cmd /c uv run markurldown", 0, False
Set oShell = Nothing
```

8) 版本管理与发布体系适配
- 移动 `version.py` 至 `src/markurldown/version.py`
- 全局替换导入为 `from markurldown.version import ...`
- 更新 `docs/Version_management_guide.md` 示例
- 校正 `scripts/release.py` 与 `.github/workflows`（使用 `uv sync`/`uv run`）

9) 本地验证（更新测试并运行）
- 更新/新增测试用例，覆盖导入路径、入口脚本、资源定位与版本模块变更

```powershell
uv sync
uv run markurldown
uv run pytest -q
uv run coverage run -m pytest
uv run coverage html
```

10) 文档与说明
- 更新 `README.md`、`STARTUP_OPTIMIZATION.md`（入口命令、路径、截图位置）
- 更新 `docs/Version_management_guide.md`（导入示例改为 `markurldown.version`、release 命令示例保持 `uv run`）
- 更新 `docs/HANDLER_DEVELOPMENT_GUIDE.md`（所有 `markitdown_app` 路径替换为 `markurldown`，目录结构示例更新为 `src/markurldown/core/handlers/`）
- 更新 `docs/new_site_handler_template.py`（导入从 `markitdown_app.*` 改为 `markurldown.*`）
- 在变更说明中明确 portable 数据目录保持不变，未来统一迁移至 `data/`

11) 合并分支
- 创建 PR、完成代码评审与合并

若无异议，可按以上步骤实施迁移。


