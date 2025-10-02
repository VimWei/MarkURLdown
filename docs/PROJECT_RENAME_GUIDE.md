# 项目重命名指南：MarkURLdown → MarkdownAll

本文档详细说明了将项目从 `MarkURLdown` 重命名为 `MarkdownAll` 的完整步骤。

## 概述

项目重命名涉及以下几个层面的更改：
- GitHub 仓库名称和 URL
- 本地 Git 配置
- Python 包名和目录结构
- 项目配置文件
- 文档和脚本文件
- 测试文件中的引用

## 执行顺序

### 第一阶段：Git 和远程仓库处理

#### 1. GitHub 仓库重命名

1. 登录 GitHub，进入 `MarkURLdown` 仓库
2. 点击 **Settings** 标签页
3. 滚动到 **Repository name** 部分
4. 将仓库名从 `MarkURLdown` 改为 `MarkdownAll`
5. 点击 **Rename** 按钮确认

> **注意**：GitHub 会自动设置从旧名称到新名称的重定向，但建议尽快更新所有引用。

#### 2. 更新本地 Git 远程地址

```bash
# 查看当前远程地址
git remote -v

# 更新远程地址（开发者使用 SSH 格式）
git remote set-url origin git@github.com:VimWei/MarkdownAll.git

# 验证更改
git remote -v
```

> **说明**：
> - **开发者**：使用 SSH 格式 (`git@github.com:VimWei/MarkdownAll.git`)，需要配置 SSH 密钥，便于推送代码
> - **普通用户**：克隆时使用 HTTPS 格式 (`https://github.com/VimWei/MarkdownAll.git`)，无需额外配置

#### 3. 更新项目配置中的 GitHub 地址

需要手动更新以下文件中的 GitHub URL：

**文件：`pyproject.toml`**
```toml
# 第24行，更改：
Homepage = "https://github.com/VimWei/MarkdownAll"
```

**文件：`README.md`**
```markdown
# 第49行，更改：
git clone https://github.com/VimWei/MarkdownAll
```

> **说明**：`scripts/release.py` 会自动从 `pyproject.toml` 读取 URL，无需单独更改。

### 第二阶段：项目内容重命名

#### 4. 备份项目

```bash
# 创建备份（可选但推荐）
git add .
git commit -m "Backup before project rename"
git push
```

#### 5. 包目录重命名

```bash
# 重命名主包目录
mv src/markurldown src/markdownall
```

#### 6. 批量更新 import 语句

需要在所有 Python 文件中进行以下替换：

**替换规则：**
- `from markurldown` → `from markdownall`
- `import markurldown` → `import markdownall`

**涉及的文件类型：**
- 所有 `.py` 文件
- 测试文件
- 配置文件

**具体执行：**

使用文本编辑器的全局搜索替换功能，或使用命令行工具：

```bash
# 使用 sed 进行批量替换（Linux/macOS）
find . -name "*.py" -type f -exec sed -i 's/from markurldown/from markdownall/g' {} \;
find . -name "*.py" -type f -exec sed -i 's/import markurldown/import markdownall/g' {} \;

# Windows PowerShell 替换
Get-ChildItem -Recurse -Include *.py | ForEach-Object {
    (Get-Content $_.FullName) -replace 'from markurldown', 'from markdownall' | Set-Content $_.FullName
    (Get-Content $_.FullName) -replace 'import markurldown', 'import markdownall' | Set-Content $_.FullName
}
```

#### 7. 更新项目配置文件

**文件：`pyproject.toml`**

需要更新以下配置项：

```toml
# 第2行：项目名称
name = "MarkdownAll"

# 第31行：包含的包
include = ["markdownall*"]

# 第35行：命令行入口点
markdownall = "markdownall.launch:main"

# 第77行：测试覆盖率源码目录
source = ["markdownall"]
```

#### 8. 重命名和更新脚本文件

```bash
# 重命名 VBS 脚本文件
mv MarkURLdown.vbs MarkdownAll.vbs
```

**更新 `MarkdownAll.vbs` 内容：**

```vbscript
# 第14行：更新命令
uvCmd = "uv run markdownall"
```

#### 9. 更新文档文件

**文件：`README.md`**

需要更新的内容：
- 第1行：`# MarkdownAll`
- 第3行：项目描述中的项目名称
- 第71行：启动器文件名 `MarkdownAll.vbs`
- 第74行：命令行工具名 `uv run markdownall`

**其他文档文件：**

检查并更新以下文档中的项目名称引用：
- `docs/Version_management_guide.md`
- `docs/Testing_Guide.md`
- `docs/HANDLER_DEVELOPMENT_GUIDE.md`

> **注意**：`docs/changelog.md` 是历史记录，应保持原样，不要修改其中的项目名称。

### 第三阶段：测试和验证

#### 10. 重新同步环境

```bash
# 重新同步 Python 环境（包含开发依赖）
uv sync --group dev
```

#### 11. 验证命令行工具

```bash
# 测试新的命令行工具
uv run markdownall --help

# 或者测试启动 GUI
uv run markdownall
```

#### 12. 运行测试套件

```bash
# 运行所有测试
uv run pytest

# 运行特定测试类别
uv run pytest tests/test_core/
uv run pytest tests/test_integration/
```

#### 13. 检查代码质量

```bash
# 代码格式检查
uv run black --check .
uv run isort --check-only .

# 类型检查（如果配置了 mypy）
uv run mypy src/
```

### 第四阶段：提交和发布

#### 14. 提交更改

```bash
# 添加所有更改
git add .

# 提交更改
git commit -m "Rename project from MarkURLdown to MarkdownAll

- Rename package directory: src/markurldown → src/markdownall  
- Update all import statements
- Update project configuration in pyproject.toml
- Update GitHub URLs and documentation
- Update VBS launcher script
- Update command line entry point"

# 推送到远程仓库
git push origin main
```

#### 15. 更新版本和发布

```bash
# 使用发布脚本创建新版本
python scripts/release.py minor
```

## 验证清单

完成重命名后，请检查以下项目：

### 功能验证
- [ ] 命令行工具 `markdownall` 可以正常启动
- [ ] GUI 应用程序可以正常运行
- [ ] 所有测试通过
- [ ] 包可以正常构建和安装

### 配置验证
- [ ] `pyproject.toml` 中的项目名称已更新
- [ ] GitHub URL 已更新
- [ ] 命令行入口点已更新
- [ ] 包目录结构正确

### 文档验证
- [ ] README.md 中的项目名称已更新
- [ ] 所有文档文件中的引用已更新
- [ ] VBS 启动脚本已重命名和更新

### Git 验证
- [ ] 远程仓库地址已更新
- [ ] 可以正常推送和拉取代码
- [ ] GitHub 仓库名称已更改

## 常见问题

### Q: 重命名后导入错误怎么办？
A: 检查是否有遗漏的 import 语句未更新，使用全局搜索确保所有 `markurldown` 都已替换为 `markdownall`。

### Q: 命令行工具找不到怎么办？
A: 运行 `uv sync` 重新同步环境，确保 `pyproject.toml` 中的入口点配置正确。

### Q: 测试失败怎么办？
A: 检查测试文件中的 import 语句是否已更新，确保所有模块路径正确。

### Q: GitHub 重定向问题？
A: GitHub 会自动处理重定向，但建议更新所有克隆的本地仓库的远程地址。

## 回滚方案

如果重命名过程中出现问题，可以按以下步骤回滚：

1. 恢复 Git 提交：`git reset --hard HEAD~1`
2. 重命名包目录：`mv src/markdownall src/markurldown`
3. 恢复配置文件的更改
4. 重新同步环境：`uv sync`

## 总结

项目重命名是一个涉及多个层面的复杂操作，需要系统性地处理 Git 仓库、Python 包结构、配置文件和文档。按照本指南的步骤执行，可以确保重命名过程的完整性和正确性。

重命名完成后，项目将以新的名称 `MarkdownAll` 继续开发和维护，所有功能保持不变，只是名称和相关引用得到了更新。
