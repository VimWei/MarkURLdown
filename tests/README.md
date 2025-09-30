# MarkURLdown 测试说明

## 测试结构

```
tests/
├── __init__.py
├── conftest.py                    # pytest 配置和公共 fixtures
├── test_handlers/                 # Handler 测试
│   ├── __init__.py
│   └── test_generic_handler.py   # 通用处理器测试
├── test_services/                 # 服务层测试
│   ├── __init__.py
│   └── test_convert_service.py   # 转换服务测试
├── test_core/                     # 核心模块测试
│   ├── __init__.py
│   ├── test_filename.py          # 文件名处理测试
│   └── test_normalize.py         # 内容标准化测试
├── test_io/                       # IO 模块测试
│   └── __init__.py
├── test_integration/              # 集成测试
│   ├── __init__.py
│   └── test_end_to_end.py        # 端到端测试
└── test_data/                     # 测试数据
    ├── html_samples/              # HTML 样本
    ├── markdown_samples/          # 期望的 Markdown 输出
    └── images/                    # 测试图片
```

## 运行测试

### 基础命令

```bash
# 运行所有测试
uv run pytest

# 运行特定模块测试
uv run pytest tests/test_handlers/
uv run pytest tests/test_services/
uv run pytest tests/test_core/

# 运行特定测试文件
uv run pytest tests/test_handlers/test_generic_handler.py

# 运行特定测试方法
uv run pytest tests/test_handlers/test_generic_handler.py::TestGenericHandler::test_convert_url_basic
```

### 高级选项

```bash
# 显示详细输出
uv run pytest -v

# 显示失败详情
uv run pytest --tb=long

# 只运行失败的测试
uv run pytest --lf

# 运行特定标记的测试
uv run pytest -m "unit"
uv run pytest -m "integration"
uv run pytest -m "not slow"

# 显示测试覆盖率
uv run pytest --cov=markitdown_app

# 并行运行测试
uv run pytest -n auto
```

## 测试标记

- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.handler` - 处理器测试
- `@pytest.mark.service` - 服务层测试
- `@pytest.mark.slow` - 慢速测试

## 编写测试

### 测试命名规范

- 测试文件：`test_*.py`
- 测试类：`Test*`
- 测试方法：`test_*`

### 测试结构

```python
class TestFeature:
    """测试功能描述"""
    
    def setup_method(self):
        """测试前准备"""
        pass
    
    def test_basic_functionality(self):
        """测试基础功能"""
        # 1. 准备测试数据
        # 2. 执行被测试的功能
        # 3. 验证结果
        pass
    
    def test_edge_cases(self):
        """测试边界情况"""
        pass
```

### 使用 Fixtures

```python
def test_with_fixtures(mock_session, default_options):
    """使用预定义的 fixtures"""
    # 使用 mock_session 和 default_options
    pass
```

## 测试数据

测试数据放在 `test_data/` 目录下：

- `html_samples/` - HTML 样本文件
- `markdown_samples/` - 期望的 Markdown 输出
- `images/` - 测试图片文件

## Mock 策略

### 网络请求 Mock

```python
@patch('markitdown_app.core.handlers.generic_handler._try_lightweight_markitdown')
def test_with_mock(mock_lightweight):
    mock_lightweight.return_value = Mock(success=True, title="测试标题")
    # 测试代码
```

### 文件操作 Mock

```python
@patch('builtins.open', mock_open(read_data="test content"))
def test_file_operations():
    # 测试文件操作
    pass
```

## 持续集成

在 CI/CD 环境中运行测试：

```bash
# 安装依赖
uv sync --dev

# 运行测试
uv run pytest --tb=short -q

# 生成覆盖率报告
uv run pytest --cov=markitdown_app --cov-report=xml
```
