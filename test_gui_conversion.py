#!/usr/bin/env python3
"""
GUI转换功能测试
测试GUI界面上的转换按钮是否正常工作
"""

import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest

from markdownall.ui.pyside.main_window import MainWindow


def test_gui_conversion():
    """测试GUI转换功能"""
    print("🖥️ 开始GUI转换功能测试...")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    try:
        # 创建主窗口
        root_dir = os.path.dirname(os.path.dirname(__file__))
        main_window = MainWindow(root_dir)
        main_window.show()
        
        print("✅ 主窗口创建成功")
        
        # 设置测试数据
        test_url = "https://httpbin.org/html"
        main_window.basic_page.url_entry.setText(test_url)
        print(f"✅ 设置URL: {test_url}")
        
        test_output = os.path.join(root_dir, "test_output")
        os.makedirs(test_output, exist_ok=True)
        main_window.basic_page.output_entry.setText(test_output)
        print(f"✅ 设置输出目录: {test_output}")
        
        # 检查转换按钮状态
        convert_btn = main_window.command_panel.btn_convert
        if convert_btn.isEnabled():
            print("✅ 转换按钮可用")
        else:
            print("❌ 转换按钮不可用")
            return False
        
        # 检查按钮文本
        btn_text = convert_btn.text()
        print(f"✅ 转换按钮文本: {btn_text}")
        
        # 设置事件处理器来监控转换过程
        original_handler = main_window._on_event_thread_safe
        
        def test_event_handler(ev):
            print(f"📡 GUI事件: {ev.kind} - {ev.text}")
            if ev.data:
                print(f"   数据: {ev.data}")
            # 调用原始处理器
            original_handler(ev)
        
        # 替换事件处理器
        main_window._on_event_thread_safe = test_event_handler
        
        print("🚀 点击转换按钮...")
        
        # 直接调用转换方法（模拟按钮点击）
        main_window._on_convert()
        
        print("✅ 转换按钮已点击")
        
        # 等待转换完成
        print("⏰ 等待转换完成...")
        
        def check_conversion_status():
            if not main_window.is_running:
                print("✅ 转换已完成")
                app.quit()
            else:
                print("⏳ 转换进行中...")
                # 再次检查状态
                QTimer.singleShot(2000, check_conversion_status)
        
        # 开始检查状态
        QTimer.singleShot(3000, check_conversion_status)
        
        # 设置超时
        QTimer.singleShot(15000, app.quit)
        
        app.exec()
        
        print("✅ GUI转换功能测试完成")
        return True
        
    except Exception as e:
        print(f"❌ GUI转换功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🧪 MarkdownAll GUI转换功能测试")
    print("=" * 50)
    
    test_gui_conversion()
    
    print("\n✅ GUI转换功能测试完成")


if __name__ == "__main__":
    main()
