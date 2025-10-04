#!/usr/bin/env python3
"""
使用实际配置测试转换功能
使用mix.json中的真实配置进行测试
"""

import sys
import os
import json
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from markdownall.ui.pyside.main_window import MainWindow


def test_with_real_config():
    """使用真实配置测试转换功能"""
    print("🔍 使用真实配置测试转换功能...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    try:
        # 创建主窗口
        root_dir = os.path.dirname(os.path.dirname(__file__))
        main_window = MainWindow(root_dir)
        main_window.show()
        
        print("✅ 主窗口创建成功")
        
        # 加载mix.json配置
        config_file = os.path.join(root_dir, "data", "sessions", "mix.json")
        if not os.path.exists(config_file):
            print(f"❌ 配置文件不存在: {config_file}")
            return False
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"✅ 加载配置文件: {config_file}")
        print(f"📋 配置内容:")
        print(f"  - URLs数量: {len(config['urls'])}")
        print(f"  - 输出目录: {config['output_dir']}")
        print(f"  - 选项: {config}")
        
        # 应用配置到GUI
        main_window.basic_page.set_urls(config['urls'])
        main_window.basic_page.set_output_dir(config['output_dir'])
        
        # 设置转换选项
        webpage_config = {
            "use_proxy": config['use_proxy'],
            "ignore_ssl": config['ignore_ssl'],
            "download_images": config['download_images'],
            "filter_site_chrome": config['filter_site_chrome'],
            "use_shared_browser": config['use_shared_browser']
        }
        main_window.webpage_page.set_config(webpage_config)
        
        print("✅ 配置已应用到GUI")
        
        # 检查输出目录
        output_dir = config['output_dir']
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                print(f"✅ 创建输出目录: {output_dir}")
            except Exception as e:
                print(f"❌ 无法创建输出目录: {e}")
                return False
        else:
            print(f"✅ 输出目录存在: {output_dir}")
        
        # 设置事件处理器
        def detailed_event_handler(ev):
            print(f"📡 事件: {ev.kind}")
            if ev.text:
                print(f"   文本: {ev.text}")
            if ev.data:
                print(f"   数据: {ev.data}")
            
            # 调用原始处理器
            main_window._on_event_thread_safe(ev)
        
        # 替换事件处理器
        main_window._on_event_thread_safe = detailed_event_handler
        
        # 测试第一个URL
        test_url = config['urls'][0]
        print(f"\n🚀 测试第一个URL: {test_url}")
        
        # 设置单个URL进行测试
        main_window.basic_page.url_entry.setText(test_url)
        
        # 启动转换
        print("🚀 启动转换...")
        main_window._on_convert()
        
        print("✅ 转换已启动")
        
        # 等待转换完成
        print("⏰ 等待转换完成...")
        
        def check_status():
            if not main_window.is_running:
                print("✅ 转换已完成")
                app.quit()
            else:
                print("⏳ 转换进行中...")
                QTimer.singleShot(2000, check_status)
        
        QTimer.singleShot(3000, check_status)
        QTimer.singleShot(30000, app.quit)  # 30秒超时
        
        app.exec()
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_url():
    """测试单个URL"""
    print("\n🔍 测试单个URL...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    try:
        # 创建主窗口
        root_dir = os.path.dirname(os.path.dirname(__file__))
        main_window = MainWindow(root_dir)
        main_window.show()
        
        # 使用mix.json中的第一个URL
        test_url = "https://skywind.me/blog/archives/3039"
        output_dir = os.path.join(root_dir, "test_output")
        
        # 设置测试数据
        main_window.basic_page.url_entry.setText(test_url)
        main_window.basic_page.output_entry.setText(output_dir)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"📝 测试设置:")
        print(f"  - URL: {test_url}")
        print(f"  - 输出目录: {output_dir}")
        
        # 设置详细的事件处理器
        def single_url_handler(ev):
            print(f"📡 转换事件: {ev.kind}")
            if ev.text:
                print(f"   消息: {ev.text}")
            if ev.data:
                print(f"   数据: {ev.data}")
            
            # 不要调用原始处理器，避免递归
            # main_window._on_event_thread_safe(ev)
        
        main_window._on_event_thread_safe = single_url_handler
        
        # 启动转换
        print("🚀 启动转换...")
        main_window._on_convert()
        
        # 等待完成
        def check_completion():
            if not main_window.is_running:
                print("✅ 转换完成")
                app.quit()
            else:
                QTimer.singleShot(1000, check_completion)
        
        QTimer.singleShot(2000, check_completion)
        QTimer.singleShot(20000, app.quit)
        
        app.exec()
        
        return True
        
    except Exception as e:
        print(f"❌ 单URL测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🧪 使用真实配置测试MarkdownAll转换功能")
    print("=" * 60)
    
    # 测试单个URL
    test_single_url()
    
    print("\n" + "=" * 60)
    print("✅ 真实配置测试完成")


if __name__ == "__main__":
    main()
