#!/usr/bin/env python3
"""
简单GUI测试 - 启动应用程序并测试基本操作
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from markdownall.ui.pyside.main_window import MainWindow


def main():
    """主函数"""
    print("🖥️ 启动MarkdownAll GUI测试")
    print("=" * 50)
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    try:
        # 创建主窗口
        root_dir = os.path.dirname(os.path.dirname(__file__))
        main_window = MainWindow(root_dir)
        
        print("✅ 主窗口创建成功")
        print("📋 窗口组件检查:")
        
        # 检查各个页面
        if hasattr(main_window, 'basic_page'):
            print("  ✅ Basic页面存在")
            if hasattr(main_window.basic_page, 'url_entry'):
                print("    ✅ URL输入框存在")
            if hasattr(main_window.basic_page, 'output_entry'):
                print("    ✅ 输出目录输入框存在")
        
        if hasattr(main_window, 'webpage_page'):
            print("  ✅ Webpage页面存在")
        
        if hasattr(main_window, 'advanced_page'):
            print("  ✅ Advanced页面存在")
        
        if hasattr(main_window, 'about_page'):
            print("  ✅ About页面存在")
        
        # 检查组件
        if hasattr(main_window, 'command_panel'):
            print("  ✅ Command面板存在")
            if hasattr(main_window.command_panel, 'btn_convert'):
                print("    ✅ 转换按钮存在")
                print(f"    按钮文本: {main_window.command_panel.btn_convert.text()}")
        
        if hasattr(main_window, 'log_panel'):
            print("  ✅ Log面板存在")
        
        # 显示窗口
        main_window.show()
        print("✅ 窗口已显示")
        
        # 设置一些测试数据
        main_window.basic_page.url_entry.setText("https://example.com")
        main_window.basic_page.output_entry.setText(os.path.join(root_dir, "test_output"))
        
        print("✅ 测试数据已设置")
        print("📝 测试数据:")
        print(f"  - URL: {main_window.basic_page.url_entry.text()}")
        print(f"  - 输出目录: {main_window.basic_page.output_entry.text()}")
        
        print("\n🎯 现在您可以:")
        print("  1. 在Basic页面输入要转换的URL")
        print("  2. 设置输出目录")
        print("  3. 点击'转换为 Markdown'按钮开始转换")
        print("  4. 在Log面板查看转换日志")
        print("  5. 在Command面板查看转换进度")
        
        print("\n⏰ 应用程序将运行30秒，然后自动退出...")
        
        # 运行应用程序
        from PySide6.QtCore import QTimer
        QTimer.singleShot(30000, app.quit)  # 30秒后退出
        
        app.exec()
        
        print("✅ GUI测试完成")
        
    except Exception as e:
        print(f"❌ GUI测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
