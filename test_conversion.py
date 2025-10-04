#!/usr/bin/env python3
"""
转换功能诊断脚本
用于测试和诊断转换功能的问题
"""

import sys
import os
import traceback

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from markdownall.ui.pyside.main_window import MainWindow
from markdownall.app_types import SourceRequest, ConversionOptions


def test_conversion_functionality():
    """测试转换功能"""
    print("🔍 开始转换功能诊断...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    try:
        # 创建主窗口
        root_dir = os.path.dirname(os.path.dirname(__file__))
        main_window = MainWindow(root_dir)
        main_window.show()
        
        print("✅ 主窗口创建成功")
        
        # 检查ViewModel
        if hasattr(main_window, 'vm'):
            print("✅ ViewModel存在")
        else:
            print("❌ ViewModel不存在")
            return False
        
        # 检查信号
        if hasattr(main_window, 'signals'):
            print("✅ ProgressSignals存在")
        else:
            print("❌ ProgressSignals不存在")
            return False
        
        # 检查转换相关方法
        if hasattr(main_window, '_on_convert'):
            print("✅ _on_convert方法存在")
        else:
            print("❌ _on_convert方法不存在")
            return False
        
        # 测试URL设置
        test_url = "https://example.com"
        main_window.basic_page.url_entry.setText(test_url)
        print(f"✅ 设置测试URL: {test_url}")
        
        # 测试输出目录设置
        test_output = os.path.join(root_dir, "test_output")
        main_window.basic_page.output_entry.setText(test_output)
        print(f"✅ 设置输出目录: {test_output}")
        
        # 检查转换选项
        options = main_window.webpage_page.get_options()
        print(f"✅ 获取转换选项: {options}")
        
        # 尝试创建转换对象
        try:
            reqs = [SourceRequest(kind="url", value=test_url)]
            options_obj = ConversionOptions(**options)
            print("✅ 转换对象创建成功")
        except Exception as e:
            print(f"❌ 转换对象创建失败: {e}")
            traceback.print_exc()
            return False
        
        # 检查ViewModel的start方法
        if hasattr(main_window.vm, 'start'):
            print("✅ ViewModel.start方法存在")
        else:
            print("❌ ViewModel.start方法不存在")
            return False
        
        # 尝试调用转换（但不实际执行）
        print("🔍 准备测试转换调用...")
        
        # 设置事件处理器
        def test_event_handler(ev):
            print(f"📡 收到事件: {ev.kind} - {ev.text}")
        
        # 检查所有必要的参数
        print(f"📋 转换参数检查:")
        print(f"  - URLs: {[req.value for req in reqs]}")
        print(f"  - 输出目录: {test_output}")
        print(f"  - 选项: {options}")
        print(f"  - 事件处理器: {test_event_handler}")
        print(f"  - 信号: {main_window.signals}")
        
        print("✅ 转换功能诊断完成 - 所有组件都存在")
        return True
        
    except Exception as e:
        print(f"❌ 转换功能诊断失败: {e}")
        traceback.print_exc()
        return False


def test_actual_conversion():
    """测试实际转换"""
    print("\n🚀 开始实际转换测试...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    try:
        # 创建主窗口
        root_dir = os.path.dirname(os.path.dirname(__file__))
        main_window = MainWindow(root_dir)
        main_window.show()
        
        # 设置测试数据
        test_url = "https://httpbin.org/html"  # 一个简单的测试页面
        main_window.basic_page.url_entry.setText(test_url)
        
        test_output = os.path.join(root_dir, "test_output")
        os.makedirs(test_output, exist_ok=True)
        main_window.basic_page.output_entry.setText(test_output)
        
        print(f"📝 设置测试数据:")
        print(f"  - URL: {test_url}")
        print(f"  - 输出目录: {test_output}")
        
        # 设置事件处理器
        def conversion_event_handler(ev):
            print(f"📡 转换事件: {ev.kind} - {ev.text}")
            if ev.data:
                print(f"   数据: {ev.data}")
        
        # 尝试启动转换
        print("🚀 启动转换...")
        
        # 获取URLs和选项
        urls = main_window.basic_page.get_urls()
        if not urls:
            url = main_window.basic_page.url_entry.text().strip()
            if not url:
                print("❌ 没有URL可转换")
                return False
            if not url.lower().startswith(("http://", "https://")):
                url = "https://" + url
            urls = [url]
        
        out_dir = main_window.basic_page.get_output_dir().strip() or os.getcwd()
        options_dict = main_window.webpage_page.get_options()
        
        print(f"📋 转换参数:")
        print(f"  - URLs: {urls}")
        print(f"  - 输出目录: {out_dir}")
        print(f"  - 选项: {options_dict}")
        
        # 创建转换对象
        reqs = [SourceRequest(kind="url", value=u) for u in urls]
        options = ConversionOptions(**options_dict)
        
        # 启动转换
        main_window.is_running = True
        main_window.command_panel.setConvertingState(True)
        main_window.command_panel.set_progress(0, "Starting conversion...")
        main_window.log_info(f"Starting conversion of {len(urls)} URLs")
        
        # 调用ViewModel的start方法
        main_window.vm.start(reqs, out_dir, options, conversion_event_handler, main_window.signals)
        
        print("✅ 转换已启动")
        
        # 等待一段时间看结果
        print("⏰ 等待转换完成...")
        
        # 设置定时器来检查状态
        def check_status():
            if not main_window.is_running:
                print("✅ 转换已完成")
                app.quit()
            else:
                print("⏳ 转换进行中...")
        
        QTimer.singleShot(5000, check_status)  # 5秒后检查状态
        QTimer.singleShot(10000, app.quit)      # 10秒后强制退出
        
        app.exec()
        
        return True
        
    except Exception as e:
        print(f"❌ 实际转换测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🧪 MarkdownAll 转换功能诊断")
    print("=" * 50)
    
    # 第一步：诊断转换功能组件
    if not test_conversion_functionality():
        print("❌ 转换功能诊断失败，停止测试")
        return
    
    # 第二步：测试实际转换
    print("\n" + "=" * 50)
    test_actual_conversion()
    
    print("\n✅ 转换功能测试完成")


if __name__ == "__main__":
    main()
