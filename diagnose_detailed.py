#!/usr/bin/env python3
"""
详细诊断脚本 - 检查应用程序启动和转换功能的具体问题
"""

import sys
import os
import traceback

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_imports():
    """检查所有必要的导入"""
    print("🔍 检查导入...")
    
    try:
        from PySide6.QtWidgets import QApplication
        print("✅ PySide6.QtWidgets 导入成功")
    except Exception as e:
        print(f"❌ PySide6.QtWidgets 导入失败: {e}")
        return False
    
    try:
        from markdownall.ui.pyside.main_window import MainWindow
        print("✅ MainWindow 导入成功")
    except Exception as e:
        print(f"❌ MainWindow 导入失败: {e}")
        traceback.print_exc()
        return False
    
    try:
        from markdownall.app_types import SourceRequest, ConversionOptions
        print("✅ app_types 导入成功")
    except Exception as e:
        print(f"❌ app_types 导入失败: {e}")
        traceback.print_exc()
        return False
    
    try:
        from markdownall.ui.viewmodel import ViewModel
        print("✅ ViewModel 导入成功")
    except Exception as e:
        print(f"❌ ViewModel 导入失败: {e}")
        traceback.print_exc()
        return False
    
    return True


def test_basic_startup():
    """测试基本启动"""
    print("\n🚀 测试基本启动...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from markdownall.ui.pyside.main_window import MainWindow
        
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        root_dir = os.path.dirname(os.path.dirname(__file__))
        print(f"📁 根目录: {root_dir}")
        
        main_window = MainWindow(root_dir)
        print("✅ MainWindow 创建成功")
        
        # 检查基本组件
        if hasattr(main_window, 'basic_page'):
            print("✅ basic_page 存在")
        else:
            print("❌ basic_page 不存在")
            return False
        
        if hasattr(main_window, 'webpage_page'):
            print("✅ webpage_page 存在")
        else:
            print("❌ webpage_page 不存在")
            return False
        
        if hasattr(main_window, 'command_panel'):
            print("✅ command_panel 存在")
        else:
            print("❌ command_panel 不存在")
            return False
        
        if hasattr(main_window, 'log_panel'):
            print("✅ log_panel 存在")
        else:
            print("❌ log_panel 不存在")
            return False
        
        if hasattr(main_window, 'vm'):
            print("✅ ViewModel 存在")
        else:
            print("❌ ViewModel 不存在")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 基本启动测试失败: {e}")
        traceback.print_exc()
        return False


def test_conversion_setup():
    """测试转换设置"""
    print("\n🔧 测试转换设置...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from markdownall.ui.pyside.main_window import MainWindow
        
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        root_dir = os.path.dirname(os.path.dirname(__file__))
        main_window = MainWindow(root_dir)
        
        # 测试URL设置
        test_url = "https://example.com"
        main_window.basic_page.url_entry.setText(test_url)
        print(f"✅ 设置URL: {test_url}")
        
        # 测试输出目录设置
        test_output = os.path.join(root_dir, "test_output")
        main_window.basic_page.output_entry.setText(test_output)
        print(f"✅ 设置输出目录: {test_output}")
        
        # 测试获取URLs
        urls = main_window.basic_page.get_urls()
        print(f"✅ 获取URLs: {urls}")
        
        # 测试获取输出目录
        output_dir = main_window.basic_page.get_output_dir()
        print(f"✅ 获取输出目录: {output_dir}")
        
        # 测试获取转换选项
        options = main_window.webpage_page.get_options()
        print(f"✅ 获取转换选项: {options}")
        
        return True
        
    except Exception as e:
        print(f"❌ 转换设置测试失败: {e}")
        traceback.print_exc()
        return False


def test_conversion_objects():
    """测试转换对象创建"""
    print("\n🏗️ 测试转换对象创建...")
    
    try:
        from markdownall.app_types import SourceRequest, ConversionOptions
        
        # 测试SourceRequest
        req = SourceRequest(kind="url", value="https://example.com")
        print(f"✅ SourceRequest 创建成功: {req}")
        
        # 测试ConversionOptions
        options = ConversionOptions(
            use_proxy=False,
            ignore_ssl=False,
            download_images=True,
            filter_site_chrome=True,
            use_shared_browser=True
        )
        print(f"✅ ConversionOptions 创建成功: {options}")
        
        return True
        
    except Exception as e:
        print(f"❌ 转换对象创建失败: {e}")
        traceback.print_exc()
        return False


def test_viewmodel_start():
    """测试ViewModel启动"""
    print("\n🎯 测试ViewModel启动...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from markdownall.ui.pyside.main_window import MainWindow
        from markdownall.app_types import SourceRequest, ConversionOptions
        
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        root_dir = os.path.dirname(os.path.dirname(__file__))
        main_window = MainWindow(root_dir)
        
        # 检查ViewModel的start方法
        if hasattr(main_window.vm, 'start'):
            print("✅ ViewModel.start 方法存在")
        else:
            print("❌ ViewModel.start 方法不存在")
            return False
        
        # 检查start方法的签名
        import inspect
        sig = inspect.signature(main_window.vm.start)
        print(f"✅ ViewModel.start 签名: {sig}")
        
        return True
        
    except Exception as e:
        print(f"❌ ViewModel启动测试失败: {e}")
        traceback.print_exc()
        return False


def test_actual_conversion():
    """测试实际转换"""
    print("\n🚀 测试实际转换...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        from markdownall.ui.pyside.main_window import MainWindow
        from markdownall.app_types import SourceRequest, ConversionOptions
        
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        root_dir = os.path.dirname(os.path.dirname(__file__))
        main_window = MainWindow(root_dir)
        
        # 设置测试数据
        test_url = "https://httpbin.org/html"
        main_window.basic_page.url_entry.setText(test_url)
        
        test_output = os.path.join(root_dir, "test_output")
        os.makedirs(test_output, exist_ok=True)
        main_window.basic_page.output_entry.setText(test_output)
        
        print(f"📝 测试设置:")
        print(f"  - URL: {test_url}")
        print(f"  - 输出目录: {test_output}")
        
        # 获取转换参数
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
        
        print("✅ 转换对象创建成功")
        
        # 设置简单的事件处理器
        def simple_handler(ev):
            print(f"📡 事件: {ev.kind} - {ev.text}")
        
        # 尝试启动转换
        print("🚀 启动转换...")
        main_window.vm.start(reqs, out_dir, options, simple_handler, main_window.signals)
        
        print("✅ 转换已启动")
        
        # 等待一段时间
        def check_status():
            print("⏰ 检查转换状态...")
            app.quit()
        
        QTimer.singleShot(5000, check_status)
        app.exec()
        
        return True
        
    except Exception as e:
        print(f"❌ 实际转换测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🔍 MarkdownAll 详细诊断")
    print("=" * 60)
    
    # 第一步：检查导入
    if not check_imports():
        print("❌ 导入检查失败，停止诊断")
        return
    
    # 第二步：测试基本启动
    if not test_basic_startup():
        print("❌ 基本启动测试失败，停止诊断")
        return
    
    # 第三步：测试转换设置
    if not test_conversion_setup():
        print("❌ 转换设置测试失败，停止诊断")
        return
    
    # 第四步：测试转换对象创建
    if not test_conversion_objects():
        print("❌ 转换对象创建测试失败，停止诊断")
        return
    
    # 第五步：测试ViewModel启动
    if not test_viewmodel_start():
        print("❌ ViewModel启动测试失败，停止诊断")
        return
    
    # 第六步：测试实际转换
    if not test_actual_conversion():
        print("❌ 实际转换测试失败，停止诊断")
        return
    
    print("\n✅ 所有诊断测试通过！")


if __name__ == "__main__":
    main()
