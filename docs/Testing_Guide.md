# MarkdownAll 测试指南

我们将采用 pytest，它是 Python 中最流行且功能强大的第三方单元测试框架，广泛应用
于单元测试、集成测试、功能测试等自动化测试场景。相比 Python 自带的 unittest 框
架，pytest 以简洁灵活、插件丰富而著称。

## 项目特点

MarkdownAll 是一个网页转 Markdown 的桌面应用，具有以下特点：
- **多站点处理器**：微信、知乎、WordPress、Next.js、少数派等专用处理器
- **多策略爬虫**：支持 Playwright、httpx、requests 等多种爬取策略
- **内容过滤**：智能清理广告、导航等无关内容
- **图片处理**：自动下载和重写图片链接
- **批处理**：支持批量转换多个 URL

## 测试的价值

测试是项目的**质量保证基石**，为开发、重构和维护提供可靠的安全网。

- **🛡️ 质量保护**: 防止代码修改时破坏现有功能
- **📚 学习资源**: 展示 API 使用方法和最佳实践
- **🔍 功能验证**: 确保所有功能按预期工作
- **🚀 重构支持**: 重构时提供安全保障
- **👥 团队协作**: 帮助团队成员理解代码行为

## 测试文件结构

* tests/ 放在项目根目录下，按功能分组。

```
tests/
├── __init__.py
├── test_handlers/                    # Handler 测试目录
│   ├── __init__.py
│   ├── test_generic_handler.py      # 通用处理器测试
│   ├── test_weixin_handler.py       # 微信处理器测试
│   ├── test_zhihu_handler.py        # 知乎处理器测试
│   ├── test_wordpress_handler.py    # WordPress处理器测试
│   ├── test_nextjs_handler.py       # Next.js处理器测试
│   └── test_sspai_handler.py        # 少数派处理器测试
├── test_services/                    # 服务层测试
│   ├── __init__.py
│   ├── test_convert_service.py      # 转换服务测试
│   └── test_playwright_driver.py    # 浏览器驱动测试
├── test_core/                        # 核心模块测试
│   ├── __init__.py
│   ├── test_common_utils.py         # 通用工具测试
│   ├── test_html_to_md.py          # HTML转Markdown测试
│   ├── test_images.py              # 图片处理测试
│   ├── test_normalize.py           # 内容标准化测试
│   └── test_filename.py            # 文件名处理测试
├── test_io/                          # IO模块测试
│   ├── __init__.py
│   ├── test_config.py              # 配置管理测试
│   ├── test_session.py             # 会话管理测试
│   └── test_writer.py              # 文件写入测试
└── test_integration/                 # 集成测试
    ├── __init__.py
    ├── test_end_to_end.py          # 端到端测试
    └── test_batch_conversion.py    # 批量转换测试
```

## 运行测试

### 基础命令

#### 运行所有测试
```bash
# 快速运行所有测试（简洁输出）
uv run pytest tests/ --tb=no -q

# 详细运行所有测试
uv run pytest tests/ -v

# 运行所有测试并显示失败详情
uv run pytest tests/ --tb=short
```

#### 运行特定测试文件
```bash
# 运行所有 handler 测试
uv run pytest tests/test_handlers/ -v

# 运行特定 handler 测试
uv run pytest tests/test_handlers/test_weixin_handler.py -v

# 运行服务层测试
uv run pytest tests/test_services/ -v

# 运行核心模块测试
uv run pytest tests/test_core/ -v

# 运行 IO 模块测试
uv run pytest tests/test_io/ -v
```

#### 运行特定测试方法
```bash
# 运行特定测试方法
uv run pytest tests/test_handlers/test_weixin_handler.py::test_fetch_weixin_article_basic -v

# 运行多个特定测试
uv run pytest tests/test_handlers/test_weixin_handler.py::test_fetch_weixin_article_basic tests/test_handlers/test_zhihu_handler.py::test_fetch_zhihu_article_basic -v
```

#### 输出首个失败

```python
uv run pytest -q -x
```

### 高级测试选项

#### 性能分析
```bash
# 显示最慢的 10 个测试
uv run pytest tests/ --durations=10

# 显示所有测试的执行时间
uv run pytest tests/ --durations=0
```

#### 失败重试
```bash
# 只运行上次失败的测试
uv run pytest tests/ --lf

# 运行失败的测试并显示详细信息
uv run pytest tests/ --lf -v --tb=long
```

#### 并行测试（如果支持）
```bash
# 并行运行测试（需要安装 pytest-xdist）
uv run pytest tests/ -n auto
```

## 覆盖率（Coverage）

### 基本用法
```bash
# 生成覆盖率报告（终端缺失行 + HTML 报告至 tests/htmlcov/）
uv run pytest tests/ --cov=markdownall --cov-report=term-missing --cov-report=html:tests/htmlcov

# 安静模式，仅显示覆盖率摘要
uv run pytest tests/ --cov=markdownall --cov-report=term -q

# 指定子模块覆盖率（例如 core 与 services）
uv run pytest tests/test_core/ --cov=markdownall.core --cov-report=term-missing
uv run pytest tests/test_services/ --cov=markdownall.services --cov-report=term-missing
```

### 常用选项
- **--cov=PACKAGE_OR_PATH**: 指定需要统计覆盖率的包或路径（可多次传入）。
- **--cov-report=REPORT**: 输出报告类型，常用值：`term`, `term-missing`, `html`, `xml`。
- **--cov-append**: 追加到已有的覆盖率数据，便于分目录/分模块分别执行后合并。
- **--cov-branch**: 统计分支覆盖率（更严格，建议开启）。

示例：
```bash
uv run pytest tests/ --cov=markdownall --cov-branch --cov-report=term-missing
```

### 在 pyproject.toml 中配置（推荐）
```toml
[tool.pytest.ini_options]
addopts = "--cov=markdownall --cov-branch --cov-report=term-missing --cov-report=html:tests/htmlcov"
testpaths = ["tests"]
```

配置后可直接运行：
```bash
uv run pytest
```

### 生成多种报告
```bash
# 终端 + HTML + XML（CI 工具常用，如 Codecov/Sonar）
uv run pytest tests/ \
  --cov=markdownall \
  --cov-report=term-missing \
  --cov-report=html:tests/htmlcov \
  --cov-report=xml:tests/coverage.xml
```

### 设定最低覆盖率阈值（发布前门槛）
在 CI 或本地强制最低覆盖率：
```bash
uv run pytest tests/ --cov=markdownall --cov-report=term --cov-fail-under=50
```

### 排除不需要统计的文件
在项目根目录添加 `.coveragerc`：
```ini
[run]
omit =
    markdownall/ui/*
    markdownall/services/playwright_driver.py
    tests/*

[report]
exclude_lines =
    pragma: no cover
    if __name__ == .__main__.:
```

代码中也可以使用 `# pragma: no cover` 标记特定行不计入覆盖率。

### 分步执行并合并覆盖率
```bash
# 步骤1：先跑核心模块
uv run pytest tests/test_core/ --cov=markdownall --cov-append --cov-report=term
# 步骤2：再跑处理器与服务层
uv run pytest tests/test_handlers/ tests/test_services/ --cov=markdownall --cov-append --cov-report=term
# 步骤3：最终输出 HTML 报告
uv run pytest tests/ --cov=markdownall --cov-report=html:tests/htmlcov
```

### 常见问题
- 覆盖率低：优先增加对 `core/` 与关键 `handlers/` 的功能测试；使用 Mock 隔离网络/IO。
- 统计不到：确认 `--cov` 指向的是可导入的包名或源码路径，而不是测试路径。
- HTML 报告空白：确保 `--cov=markdownall` 指定了正确的包，且测试确实导入并执行了相应代码。

## 开发工作流中的测试

### 1. 日常开发流程

#### 修改现有功能
```bash
# 1. 运行相关测试了解当前状态
uv run pytest tests/test_handlers/test_weixin_handler.py -v

# 2. 进行代码修改
# ... 你的修改 ...

# 3. 验证修改没有破坏功能
uv run pytest tests/test_handlers/test_weixin_handler.py -v

# 4. 运行所有测试确保整体稳定
uv run pytest tests/ --tb=short -q
```

#### 添加新功能
```bash
# 1. 确保基础功能正常
uv run pytest tests/ --tb=short -q

# 2. 添加新功能
# ... 你的新功能 ...

# 3. 为新功能编写测试
# ... 编写测试代码 ...

# 4. 验证新功能
uv run pytest tests/test_your_new_feature.py -v

# 5. 确保没有破坏现有功能
uv run pytest tests/ --tb=short -q
```

#### 重构代码
```bash
# 1. 重构前：记录当前状态
uv run pytest tests/ --tb=short -q > before_refactor.txt

# 2. 进行重构
# ... 你的重构 ...

# 3. 重构后：验证功能一致
uv run pytest tests/ --tb=short -q > after_refactor.txt

# 4. 比较结果确保没有回归
diff before_refactor.txt after_refactor.txt
```

### 2. 问题调试流程

#### 功能异常时
```bash
# 1. 运行相关测试定位问题
uv run pytest tests/test_handlers/test_weixin_handler.py -v --tb=long

# 2. 查看具体失败的测试
uv run pytest tests/test_handlers/test_weixin_handler.py::test_fetch_weixin_article_basic -v --tb=long

# 3. 修复问题后重新验证
uv run pytest tests/test_handlers/test_weixin_handler.py -v
```

#### 性能问题时
```bash
# 1. 分析测试执行时间
uv run pytest tests/ --durations=10

# 2. 识别慢速测试
uv run pytest tests/test_converter.py --durations=0

# 3. 优化后重新测试
uv run pytest tests/test_converter.py --durations=0
```

### 3. 发布前验证

#### 完整测试套件
```bash
# 运行所有测试确保发布质量
uv run pytest tests/ --tb=short -q

# 如果所有测试通过，输出应该显示：231 passed
```

#### 关键功能验证
```bash
# 验证核心转换功能
uv run pytest tests/test_handlers/ tests/test_core/ -v

# 验证配置功能
uv run pytest tests/test_io/test_config.py -v

# 验证服务层功能
uv run pytest tests/test_services/ -v
```

## 测试文件管理

### 1. Git 版本控制

#### 应该纳入 Git 的文件
```
tests/
├── test_*.py              # 所有测试文件 ✅
└── __init__.py           # 如果存在 ✅
```

#### 应该忽略的文件
```
tests/
├── __pycache__/          # Python 缓存 ❌
├── .pytest_cache/       # pytest 缓存 ❌
├── temp_*.py            # 临时测试文件 ❌
└── test_data/           # 大型测试数据 ❌
```

#### .gitignore 配置
```gitignore
# test
tests/__pycache__/
tests/.pytest_cache/
tests/temp_*
tests/test_data/
tests/*.tmp
!tests/test_*.py
!tests/__init__.py
```

### .pytest_cache 存放位置

```toml
# 在 pyproject.toml 中添加
[tool.pytest.ini_options]
testpaths = ["tests"]
cache_dir = "tests/.pytest_cache"
```

## 故障排除

### 1. 常见测试失败

#### Mock 对象错误
```bash
# 错误：AttributeError: Mock object has no attribute 'method_name'
# 解决：正确设置 Mock 对象
mock_object.method_name.return_value = expected_value
```

#### 断言失败
```bash
# 错误：AssertionError: expected 'value1', got 'value2'
# 解决：检查期望值与实际值的差异
# 使用 -v 参数查看详细输出
uv run pytest tests/test_specific.py -v --tb=long
```

### 2. 测试环境问题

#### 依赖缺失
```bash
# 错误：ModuleNotFoundError: No module named 'pytest'
# 解决：安装测试依赖
uv add pytest
```

#### 环境变量问题
```bash
# 错误：测试依赖特定环境变量
# 解决：设置测试环境变量
export TEST_MODE=true
uv run pytest tests/
```

### 3. 性能问题

#### 测试执行缓慢
```bash
# 问题：测试执行时间过长
# 解决：使用并行测试
uv run pytest tests/ -n auto

# 或跳过慢速测试
uv run pytest tests/ -m "not slow"
```

#### 内存使用过高
```bash
# 问题：测试消耗过多内存
# 解决：限制并发数
uv run pytest tests/ -n 2
```

## 最佳实践

### 1. 测试编写原则

#### 测试命名
```python
# 好的测试命名
def test_fetch_weixin_article_basic():
    """测试基础微信文章获取功能"""
    pass

def test_fetch_weixin_article_with_images():
    """测试带图片的微信文章获取"""
    pass

def test_fetch_weixin_article_invalid_url():
    """测试无效URL时的错误处理"""
    pass

def test_generic_handler_multiple_strategies():
    """测试通用处理器的多策略爬取"""
    pass
```

#### 测试结构
```python
def test_functionality():
    """测试功能描述"""
    # 1. 准备测试数据
    input_data = "test data"
    expected_result = "expected output"

    # 2. 执行被测试的功能
    actual_result = function_under_test(input_data)

    # 3. 验证结果
    assert actual_result == expected_result
```

### 2. 测试维护原则

#### 保持测试更新
- 修改功能时同步更新测试
- 重构时保持测试覆盖度
- 定期运行测试确保稳定性

#### 测试独立性
- 每个测试应该独立运行
- 测试之间不应该有依赖关系
- 使用 Mock 对象隔离外部依赖

#### 测试可读性
- 使用描述性的测试名称
- 添加必要的注释说明
- 保持测试代码简洁明了

### 3. 团队协作原则

#### 提交前验证
```bash
# 提交代码前运行测试
uv run pytest tests/ --tb=short -q

# 确保所有测试通过
# 输出应该显示：231 passed
```

#### 代码审查
- 审查代码时同时审查测试
- 确保新功能有对应测试
- 验证测试覆盖度是否充分

#### 持续集成
- 设置自动化测试流程
- 测试失败时阻止代码合并
- 定期分析测试执行报告

## MarkdownAll 特定测试建议

### 1. Handler 测试重点

#### 微信处理器测试
```python
def test_fetch_weixin_article_basic():
    """测试基础微信文章获取"""
    # 测试正常微信文章URL
    # 验证标题提取
    # 验证内容清理
    # 验证图片处理

def test_fetch_weixin_article_with_ads():
    """测试包含广告的微信文章"""
    # 测试广告内容过滤
    # 验证正文内容完整性

def test_fetch_weixin_article_playwright_fallback():
    """测试Playwright策略回退"""
    # 模拟httpx失败
    # 验证Playwright策略生效
```

#### 通用处理器测试
```python
def test_generic_handler_strategy_fallback():
    """测试多策略回退机制"""
    # 测试轻量级MarkItDown失败
    # 验证增强MarkItDown策略
    # 验证直接httpx策略

def test_generic_handler_content_filtering():
    """测试内容过滤功能"""
    # 测试常见广告元素过滤
    # 测试导航栏过滤
    # 测试页脚过滤
```

### 2. 核心模块测试重点

#### 图片处理测试
```python
def test_download_images_and_rewrite():
    """测试图片下载和重写"""
    # 测试相对路径图片
    # 测试绝对路径图片
    # 测试图片下载失败处理
    # 验证Markdown链接重写
```

#### 内容标准化测试
```python
def test_normalize_markdown_headings():
    """测试Markdown标题标准化"""
    # 测试标题层级调整
    # 测试重复标题处理
    # 测试空标题处理
```

### 3. 集成测试重点

#### 端到端测试
```python
def test_end_to_end_weixin_conversion():
    """测试微信文章完整转换流程"""
    # 从URL到Markdown文件的完整流程
    # 验证文件输出
    # 验证图片下载

def test_batch_conversion():
    """测试批量转换功能"""
    # 测试多个URL同时转换
    # 验证进度报告
    # 验证错误处理
```

### 4. Mock 策略建议

#### 网络请求 Mock
```python
# 使用 pytest-httpx 或 requests-mock
# Mock 不同网站的响应
# 模拟网络错误和超时
```

#### 浏览器 Mock
```python
# Mock Playwright 浏览器操作
# 模拟页面加载失败
# 模拟JavaScript执行错误
```

### 5. 测试数据管理

#### 测试用例数据
```
tests/
├── test_data/                    # 测试数据目录
│   ├── html_samples/            # HTML样本
│   │   ├── weixin_article.html
│   │   ├── zhihu_answer.html
│   │   └── wordpress_post.html
│   ├── markdown_samples/        # 期望的Markdown输出
│   │   ├── weixin_expected.md
│   │   ├── zhihu_expected.md
│   │   └── wordpress_expected.md
│   └── images/                  # 测试图片
│       ├── test_image_1.jpg
│       └── test_image_2.png
```

* Created:  2025/09/28 02:27:20
* Modified: 2025/10/08 13:47:24
