# 测试指南

我们将采用 pytest，它是 Python 中最流行且功能强大的第三方单元测试框架，广泛应用
于单元测试、集成测试、功能测试等自动化测试场景。相比 Python 自带的 unittest 框
架，pytest 以简洁灵活、插件丰富而著称。

## 测试的价值

测试是项目的**质量保证基石**，为开发、重构和维护提供可靠的安全网。

- **🛡️ 质量保护**: 防止代码修改时破坏现有功能
- **📚 学习资源**: 展示 API 使用方法和最佳实践
- **🔍 功能验证**: 确保所有功能按预期工作
- **🚀 重构支持**: 重构时提供安全保障
- **👥 团队协作**: 帮助团队成员理解代码行为

## 测试文件结构

* tests/ 放在项目根目录下，按功能分组。
* 鉴于本项目的重要特点——有很多 handler，且每个handler各有特点，因此不同 handler 的 test 应该按 handler 来分组，放在相应的目录下。

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
# 运行转换功能测试
uv run pytest tests/test_converter.py -v

# 运行配置相关测试
uv run pytest tests/test_config_*.py -v

# 运行协调器测试
uv run pytest tests/test_*_coordinator.py -v
```

#### 运行特定测试方法
```bash
# 运行特定测试方法
uv run pytest tests/test_converter.py::test_mdx2html_basic -v

# 运行多个特定测试
uv run pytest tests/test_converter.py::test_mdx2html_basic tests/test_converter.py::test_mdx2pdf_basic -v
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

## 开发工作流中的测试

### 1. 日常开发流程

#### 修改现有功能
```bash
# 1. 运行相关测试了解当前状态
uv run pytest tests/test_converter.py -v

# 2. 进行代码修改
# ... 你的修改 ...

# 3. 验证修改没有破坏功能
uv run pytest tests/test_converter.py -v

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
uv run pytest tests/test_converter.py -v --tb=long

# 2. 查看具体失败的测试
uv run pytest tests/test_converter.py::test_mdx2html_basic -v --tb=long

# 3. 修复问题后重新验证
uv run pytest tests/test_converter.py -v
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
uv run pytest tests/test_converter.py tests/test_dictionary.py -v

# 验证配置功能
uv run pytest tests/test_settings_service.py tests/test_config_coordinator.py -v

# 验证协调器功能
uv run pytest tests/test_*_coordinator.py -v
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
# 测试相关忽略
tests/__pycache__/
tests/.pytest_cache/
tests/temp_*
tests/test_data/

# 但保留正式测试文件
!tests/test_*.py
!tests/__init__.py
```

### .pytest_cache 存放位置

```toml
# 在 pyproject.toml 中添加
[tool.pytest.ini_options]
cache_dir = "tests/.pytest_cache"
```

## 故障排除

### 1. 常见测试失败

#### 导入错误
```bash
# 错误：ImportError: No module named 'mdxscraper.gui.models'
# 解决：更新导入路径
# 从：from mdxscraper.gui.models import ConfigModel
# 到：from mdxscraper.models import ConfigModel
```

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
def test_mdx2html_basic():
    """测试基础 HTML 转换功能"""
    pass

def test_mdx2html_with_css_styles():
    """测试带 CSS 样式的 HTML 转换"""
    pass

def test_mdx2html_file_not_found():
    """测试文件不存在时的错误处理"""
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

* Created:  2025/09/28 02:27:20
* Modified: 2025/09/30 09:01:44
