"""测试转换性能的性能测试"""

import time
from unittest.mock import Mock, patch

import pytest

from markdownall.app_types import ConversionOptions, ConvertPayload
from markdownall.core.filename import derive_md_filename
from markdownall.core.handlers.generic_handler import convert_url
from markdownall.core.normalize import normalize_markdown_headings
from markdownall.services.convert_service import ConvertService


class TestConversionPerformance:
    """测试转换性能"""

    def setup_method(self):
        """测试前准备"""
        self.service = ConvertService()
        self.options = ConversionOptions(
            ignore_ssl=False,
            use_proxy=False,
            download_images=True,
            filter_site_chrome=True,
            use_shared_browser=True,
        )
        self.mock_session = Mock()

    def test_filename_derivation_performance(self):
        """测试文件名生成性能"""
        # 测试大量文件名生成
        start_time = time.time()

        for i in range(1000):
            filename = derive_md_filename(f"测试文章标题 {i}", f"https://example.com/article{i}")
            assert filename.endswith(".md")

        end_time = time.time()
        duration = end_time - start_time

        # 1000个文件名生成应该在1秒内完成
        assert duration < 1.0, f"文件名生成耗时过长: {duration:.3f}秒"

    def test_markdown_normalization_performance(self):
        """测试Markdown标准化性能"""
        # 测试大量内容标准化
        test_content = """
        # 标题1
        这是内容1
        
        ## 标题2
        这是内容2
        
        ### 标题3
        这是内容3
        """

        start_time = time.time()

        for i in range(1000):
            normalized = normalize_markdown_headings(test_content, f"测试标题 {i}")
            assert normalized is not None

        end_time = time.time()
        duration = end_time - start_time

        # 1000次标准化应在1.5秒内完成（放宽以适配不同环境）
        assert duration < 1.5, f"Markdown标准化耗时过长: {duration:.3f}秒"

    def test_convert_payload_creation_performance(self):
        """测试转换载荷创建性能"""
        start_time = time.time()

        for i in range(10000):
            payload = ConvertPayload(
                kind="url", value=f"https://example.com/article{i}", meta={"title": f"测试文章 {i}"}
            )
            assert payload.kind == "url"
            assert f"article{i}" in payload.value

        end_time = time.time()
        duration = end_time - start_time

        # 10000个载荷创建应该在1秒内完成
        assert duration < 1.0, f"载荷创建耗时过长: {duration:.3f}秒"

    def test_conversion_options_creation_performance(self):
        """测试转换选项创建性能"""
        start_time = time.time()

        for i in range(10000):
            options = ConversionOptions(
                ignore_ssl=i % 2 == 0,
                use_proxy=i % 3 == 0,
                download_images=i % 2 == 1,
                filter_site_chrome=i % 4 == 0,
                use_shared_browser=True,
            )
            assert hasattr(options, "ignore_ssl")
            assert hasattr(options, "use_proxy")

        end_time = time.time()
        duration = end_time - start_time

        # 10000个选项创建应该在1秒内完成
        assert duration < 1.0, f"选项创建耗时过长: {duration:.3f}秒"

    def test_service_initialization_performance(self):
        """测试服务初始化性能"""
        start_time = time.time()

        for i in range(1000):
            service = ConvertService()
            assert service is not None
            assert not service._should_stop

        end_time = time.time()
        duration = end_time - start_time

        # 1000个服务初始化应该在1秒内完成
        assert duration < 1.0, f"服务初始化耗时过长: {duration:.3f}秒"

    def test_memory_usage_patterns(self):
        """测试内存使用模式"""
        import gc
        import sys

        # 记录初始内存使用
        gc.collect()
        initial_objects = len(gc.get_objects())

        # 创建大量对象
        services = []
        for i in range(1000):
            service = ConvertService()
            services.append(service)

        # 记录创建后的内存使用
        gc.collect()
        after_creation_objects = len(gc.get_objects())

        # 清理对象
        services.clear()
        del services
        gc.collect()

        # 记录清理后的内存使用
        after_cleanup_objects = len(gc.get_objects())

        # 验证内存使用合理
        object_increase = after_creation_objects - initial_objects
        object_decrease = after_creation_objects - after_cleanup_objects

        # 对象数量应该显著减少
        assert object_decrease > 0, "内存清理不充分"

        # 对象增加应该在合理范围内
        assert object_increase < 10000, f"内存使用过多: 增加了 {object_increase} 个对象"

    def test_concurrent_service_creation(self):
        """测试并发服务创建"""
        import queue
        import threading

        def create_service(result_queue):
            service = ConvertService()
            result_queue.put(service)

        # 创建多个线程同时创建服务
        threads = []
        result_queue = queue.Queue()

        start_time = time.time()

        for i in range(100):
            thread = threading.Thread(target=create_service, args=(result_queue,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        end_time = time.time()
        duration = end_time - start_time

        # 验证所有服务都创建成功
        services = []
        while not result_queue.empty():
            service = result_queue.get()
            services.append(service)
            assert service is not None

        assert len(services) == 100, f"期望100个服务，实际创建了{len(services)}个"

        # 100个并发服务创建应该在2秒内完成
        assert duration < 2.0, f"并发服务创建耗时过长: {duration:.3f}秒"

    def test_large_content_processing(self):
        """测试大内容处理性能"""
        # 创建大内容
        large_content = "# 大标题\n\n" + "这是测试内容。\n\n" * 10000

        start_time = time.time()

        # 处理大内容
        normalized = normalize_markdown_headings(large_content, "大标题")

        end_time = time.time()
        duration = end_time - start_time

        assert normalized is not None
        assert "大标题" in normalized

        # 大内容处理应该在3秒内完成
        assert duration < 3.0, f"大内容处理耗时过长: {duration:.3f}秒"

    def test_string_operations_performance(self):
        """测试字符串操作性能"""
        test_strings = [
            "https://example.com/article1",
            "https://example.com/article2",
            "https://example.com/article3",
        ] * 1000

        start_time = time.time()

        # 执行大量字符串操作
        results = []
        for i, url in enumerate(test_strings):
            # 模拟URL处理
            if url.startswith("https://"):
                domain = url.split("//")[1].split("/")[0]
                path = url.split("/")[-1]
                result = f"{domain}_{path}_{i}"
                results.append(result)

        end_time = time.time()
        duration = end_time - start_time

        assert len(results) == len(test_strings)

        # 字符串操作应该在1秒内完成
        assert duration < 1.0, f"字符串操作耗时过长: {duration:.3f}秒"

    def test_data_structure_operations_performance(self):
        """测试数据结构操作性能"""
        start_time = time.time()

        # 测试列表操作
        test_list = []
        for i in range(10000):
            test_list.append(f"item_{i}")

        # 测试字典操作
        test_dict = {}
        for i in range(10000):
            test_dict[f"key_{i}"] = f"value_{i}"

        # 测试集合操作
        test_set = set()
        for i in range(10000):
            test_set.add(f"item_{i}")

        end_time = time.time()
        duration = end_time - start_time

        assert len(test_list) == 10000
        assert len(test_dict) == 10000
        assert len(test_set) == 10000

        # 数据结构操作应该在1秒内完成
        assert duration < 1.0, f"数据结构操作耗时过长: {duration:.3f}秒"

    def test_import_performance(self):
        """测试导入性能"""
        import importlib
        import sys

        # 清除模块缓存
        modules_to_clear = [name for name in sys.modules.keys() if name.startswith("markdownall")]
        for module_name in modules_to_clear:
            if module_name in sys.modules:
                del sys.modules[module_name]

        start_time = time.time()

        # 重新导入模块
        import markdownall.app_types
        import markdownall.core.handlers.generic_handler
        import markdownall.services.convert_service

        end_time = time.time()
        duration = end_time - start_time

        # 模块导入应在2秒内完成（放宽以适配不同环境）
        assert duration < 2.0, f"模块导入耗时过长: {duration:.3f}秒"

    def test_function_call_overhead(self):
        """测试函数调用开销"""

        def simple_function(x):
            return x * 2

        start_time = time.time()

        # 执行大量函数调用
        results = []
        for i in range(100000):
            result = simple_function(i)
            results.append(result)

        end_time = time.time()
        duration = end_time - start_time

        assert len(results) == 100000
        assert results[0] == 0
        assert results[99999] == 199998

        # 函数调用应该在1秒内完成
        assert duration < 1.0, f"函数调用耗时过长: {duration:.3f}秒"
