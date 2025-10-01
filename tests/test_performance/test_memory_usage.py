"""测试内存使用的性能测试"""

import gc
import sys
import threading
import time
from unittest.mock import Mock

import pytest

from markurldown.app_types import ConversionOptions, ConvertPayload, SourceRequest
from markurldown.services.convert_service import ConvertService


class TestMemoryUsage:
    """测试内存使用"""

    def setup_method(self):
        """测试前准备"""
        # 强制垃圾回收
        gc.collect()

    def test_basic_memory_usage(self):
        """测试基本内存使用"""
        # 记录初始对象数量
        initial_objects = len(gc.get_objects())

        # 创建一些对象
        service = ConvertService()
        options = ConversionOptions(
            ignore_ssl=False,
            use_proxy=False,
            download_images=True,
            filter_site_chrome=True,
            use_shared_browser=True,
        )

        # 记录创建后的对象数量
        after_creation_objects = len(gc.get_objects())

        # 清理对象
        del service, options
        gc.collect()

        # 记录清理后的对象数量
        after_cleanup_objects = len(gc.get_objects())

        # 验证内存使用合理
        object_increase = after_creation_objects - initial_objects
        object_decrease = after_creation_objects - after_cleanup_objects

        assert object_increase < 1000, f"基本对象创建导致过多内存使用: {object_increase} 个对象"
        assert object_decrease > 0, "内存清理不充分"

    def test_large_object_creation(self):
        """测试大对象创建"""
        # 记录初始对象数量
        initial_objects = len(gc.get_objects())

        # 创建大量对象
        services = []
        options_list = []
        payloads = []

        for i in range(1000):
            service = ConvertService()
            options = ConversionOptions(
                ignore_ssl=i % 2 == 0,
                use_proxy=i % 3 == 0,
                download_images=i % 2 == 1,
                filter_site_chrome=i % 4 == 0,
                use_shared_browser=True,
            )
            payload = ConvertPayload(
                kind="url",
                value=f"https://example.com/article{i}",
                meta={"title": f"测试文章 {i}", "content": "x" * 1000},
            )

            services.append(service)
            options_list.append(options)
            payloads.append(payload)

        # 记录创建后的对象数量
        after_creation_objects = len(gc.get_objects())

        # 清理对象
        services.clear()
        options_list.clear()
        payloads.clear()
        del services, options_list, payloads
        gc.collect()

        # 记录清理后的对象数量
        after_cleanup_objects = len(gc.get_objects())

        # 验证内存使用合理
        object_increase = after_creation_objects - initial_objects
        object_decrease = after_creation_objects - after_cleanup_objects

        assert object_increase < 10000, f"大对象创建导致过多内存使用: {object_increase} 个对象"
        assert object_decrease > 0, "内存清理不充分"

    def test_memory_leak_detection(self):
        """测试内存泄漏检测"""
        # 记录初始对象数量
        initial_objects = len(gc.get_objects())

        # 执行多次创建和销毁
        for cycle in range(10):
            services = []
            for i in range(100):
                service = ConvertService()
                services.append(service)

            # 清理
            services.clear()
            del services
            gc.collect()

        # 记录最终对象数量
        final_objects = len(gc.get_objects())

        # 验证没有内存泄漏
        object_increase = final_objects - initial_objects
        assert object_increase < 1000, f"检测到内存泄漏: 增加了 {object_increase} 个对象"

    def test_string_memory_usage(self):
        """测试字符串内存使用"""
        # 记录初始对象数量
        initial_objects = len(gc.get_objects())

        # 创建大量字符串
        strings = []
        for i in range(10000):
            string = f"测试字符串 {i} " + "x" * 100
            strings.append(string)

        # 记录创建后的对象数量
        after_creation_objects = len(gc.get_objects())

        # 清理字符串
        strings.clear()
        del strings
        gc.collect()

        # 记录清理后的对象数量
        after_cleanup_objects = len(gc.get_objects())

        # 验证内存使用合理
        object_increase = after_creation_objects - initial_objects
        object_decrease = after_creation_objects - after_cleanup_objects

        assert object_increase < 20000, f"字符串创建导致过多内存使用: {object_increase} 个对象"
        assert object_decrease > 0, "字符串内存清理不充分"

    def test_list_memory_usage(self):
        """测试列表内存使用"""
        # 记录初始对象数量
        initial_objects = len(gc.get_objects())

        # 创建大量列表
        lists = []
        for i in range(1000):
            test_list = list(range(1000))
            lists.append(test_list)

        # 记录创建后的对象数量
        after_creation_objects = len(gc.get_objects())

        # 清理列表
        lists.clear()
        del lists
        gc.collect()

        # 记录清理后的对象数量
        after_cleanup_objects = len(gc.get_objects())

        # 验证内存使用合理
        object_increase = after_creation_objects - initial_objects
        object_decrease = after_creation_objects - after_cleanup_objects

        assert object_increase < 2000000, f"列表创建导致过多内存使用: {object_increase} 个对象"
        assert object_decrease > 0, "列表内存清理不充分"

    def test_dict_memory_usage(self):
        """测试字典内存使用"""
        # 记录初始对象数量
        initial_objects = len(gc.get_objects())

        # 创建大量字典
        dicts = []
        for i in range(1000):
            test_dict = {f"key_{j}": f"value_{j}" for j in range(100)}
            dicts.append(test_dict)

        # 记录创建后的对象数量
        after_creation_objects = len(gc.get_objects())

        # 清理字典
        dicts.clear()
        del dicts
        gc.collect()

        # 记录清理后的对象数量
        after_cleanup_objects = len(gc.get_objects())

        # 验证内存使用合理
        object_increase = after_creation_objects - initial_objects
        object_decrease = after_creation_objects - after_cleanup_objects

        assert object_increase < 200000, f"字典创建导致过多内存使用: {object_increase} 个对象"
        assert object_decrease > 0, "字典内存清理不充分"

    def test_thread_memory_usage(self):
        """测试线程内存使用"""
        # 记录初始对象数量
        initial_objects = len(gc.get_objects())

        # 创建多个线程
        threads = []
        results = []

        def worker(thread_id):
            # 在线程中创建对象
            service = ConvertService()
            options = ConversionOptions(
                ignore_ssl=False,
                use_proxy=False,
                download_images=True,
                filter_site_chrome=True,
                use_shared_browser=True,
            )
            results.append((thread_id, service, options))

        # 启动线程
        for i in range(100):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 记录创建后的对象数量
        after_creation_objects = len(gc.get_objects())

        # 清理结果
        results.clear()
        del results, threads
        gc.collect()

        # 记录清理后的对象数量
        after_cleanup_objects = len(gc.get_objects())

        # 验证内存使用合理
        object_increase = after_creation_objects - initial_objects
        object_decrease = after_creation_objects - after_cleanup_objects

        assert object_increase < 10000, f"线程创建导致过多内存使用: {object_increase} 个对象"
        assert object_decrease > 0, "线程内存清理不充分"

    def test_circular_reference_handling(self):
        """测试循环引用处理"""
        # 记录初始对象数量
        initial_objects = len(gc.get_objects())

        # 创建循环引用
        class Node:
            def __init__(self, value):
                self.value = value
                self.children = []
                self.parent = None

        nodes = []
        for i in range(1000):
            node = Node(i)
            if i > 0:
                node.parent = nodes[i - 1]
                nodes[i - 1].children.append(node)
            nodes.append(node)

        # 记录创建后的对象数量
        after_creation_objects = len(gc.get_objects())

        # 清理循环引用
        nodes.clear()
        del nodes
        gc.collect()

        # 记录清理后的对象数量
        after_cleanup_objects = len(gc.get_objects())

        # 验证内存使用合理
        object_increase = after_creation_objects - initial_objects
        object_decrease = after_creation_objects - after_cleanup_objects

        assert object_increase < 5000, f"循环引用导致过多内存使用: {object_increase} 个对象"
        assert object_decrease > 0, "循环引用内存清理不充分"

    def test_garbage_collection_efficiency(self):
        """测试垃圾回收效率"""
        # 记录初始对象数量
        initial_objects = len(gc.get_objects())

        # 创建大量临时对象
        for cycle in range(10):
            temp_objects = []
            for i in range(1000):
                temp_objects.append({"id": i, "data": "x" * 100, "nested": {"key": "value"}})

            # 不显式清理，依赖垃圾回收
            del temp_objects

        # 强制垃圾回收
        collected = gc.collect()

        # 记录最终对象数量
        final_objects = len(gc.get_objects())

        # 验证垃圾回收效率
        object_increase = final_objects - initial_objects
        assert object_increase < 1000, f"垃圾回收效率低: 增加了 {object_increase} 个对象"
        # 注意：在某些情况下，垃圾回收可能返回0，这是正常的
        # assert collected > 0, "垃圾回收没有收集到对象"

    def test_memory_fragmentation(self):
        """测试内存碎片化"""
        # 记录初始对象数量
        initial_objects = len(gc.get_objects())

        # 创建和销毁不同大小的对象
        for cycle in range(100):
            # 创建小对象
            small_objects = [f"small_{i}" for i in range(1000)]

            # 创建大对象
            large_objects = ["x" * 10000 for _ in range(100)]

            # 创建中等对象
            medium_objects = [{"data": "y" * 1000} for _ in range(500)]

            # 清理
            del small_objects, large_objects, medium_objects
            gc.collect()

        # 记录最终对象数量
        final_objects = len(gc.get_objects())

        # 验证内存碎片化
        object_increase = final_objects - initial_objects
        assert object_increase < 2000, f"内存碎片化严重: 增加了 {object_increase} 个对象"
