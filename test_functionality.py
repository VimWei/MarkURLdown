#!/usr/bin/env python3
"""
功能测试脚本 - 验证MarkdownAll GUI重构后的所有功能

这个脚本将系统性地测试：
1. 应用程序启动
2. 页面切换
3. 组件功能
4. 信号连接
5. 配置管理
6. 会话管理
7. 转换流程
"""

import sys
import os
import time
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtTest import QTest

from markdownall.ui.pyside.main_window import MainWindow
from markdownall.ui.pyside.pages import BasicPage, WebpagePage, AdvancedPage, AboutPage
from markdownall.ui.pyside.components import CommandPanel, LogPanel


class FunctionalityTester:
    """功能测试器"""
    
    def __init__(self):
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
        
        self.main_window = None
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """记录测试结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} {test_name}"
        if message:
            result += f" - {message}"
        print(result)
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
    
    def test_application_startup(self):
        """测试应用程序启动"""
        print("\n🚀 测试应用程序启动...")
        
        try:
            # 创建主窗口 (需要提供root_dir参数)
            root_dir = os.path.dirname(os.path.dirname(__file__))  # 项目根目录
            self.main_window = MainWindow(root_dir)
            self.main_window.show()
            
            # 检查窗口是否正常显示
            if self.main_window.isVisible():
                self.log_test("应用程序启动", True, "主窗口正常显示")
            else:
                self.log_test("应用程序启动", False, "主窗口未显示")
                return False
                
            # 检查窗口标题
            expected_title = "MarkdownAll"
            if expected_title in self.main_window.windowTitle():
                self.log_test("窗口标题", True, f"标题包含: {expected_title}")
            else:
                self.log_test("窗口标题", False, f"实际标题: {self.main_window.windowTitle()}")
                
            return True
            
        except Exception as e:
            self.log_test("应用程序启动", False, f"异常: {e}")
            return False
    
    def test_page_structure(self):
        """测试页面结构"""
        print("\n📄 测试页面结构...")
        
        try:
            # 检查TabWidget是否存在
            if hasattr(self.main_window, 'tabs'):
                self.log_test("TabWidget存在", True)
            else:
                self.log_test("TabWidget存在", False)
                return False
            
            # 检查页面数量
            tab_count = self.main_window.tabs.count()
            expected_tabs = 4  # Basic, Webpage, Advanced, About
            if tab_count == expected_tabs:
                self.log_test("页面数量", True, f"共{tab_count}个页面")
            else:
                self.log_test("页面数量", False, f"期望{expected_tabs}个，实际{tab_count}个")
            
            # 检查各个页面是否存在
            pages = ['basic_page', 'webpage_page', 'advanced_page', 'about_page']
            for page_name in pages:
                if hasattr(self.main_window, page_name):
                    self.log_test(f"{page_name}存在", True)
                else:
                    self.log_test(f"{page_name}存在", False)
            
            return True
            
        except Exception as e:
            self.log_test("页面结构", False, f"异常: {e}")
            return False
    
    def test_component_structure(self):
        """测试组件结构"""
        print("\n🧩 测试组件结构...")
        
        try:
            # 检查组件是否存在
            components = ['command_panel', 'log_panel']
            for component_name in components:
                if hasattr(self.main_window, component_name):
                    self.log_test(f"{component_name}存在", True)
                else:
                    self.log_test(f"{component_name}存在", False)
            
            # 检查Splitter结构
            if hasattr(self.main_window, 'splitter'):
                splitter_count = self.main_window.splitter.count()
                if splitter_count == 3:  # tabs, command_panel, log_panel
                    self.log_test("Splitter结构", True, f"包含{splitter_count}个组件")
                else:
                    self.log_test("Splitter结构", False, f"期望3个组件，实际{splitter_count}个")
            
            return True
            
        except Exception as e:
            self.log_test("组件结构", False, f"异常: {e}")
            return False
    
    def test_basic_page_functionality(self):
        """测试BasicPage功能"""
        print("\n📝 测试BasicPage功能...")
        
        try:
            basic_page = self.main_window.basic_page
            
            # 测试URL输入
            if hasattr(basic_page, 'url_entry'):
                basic_page.url_entry.setText("https://example.com")
                if basic_page.url_entry.text() == "https://example.com":
                    self.log_test("URL输入", True)
                else:
                    self.log_test("URL输入", False)
            
            # 测试URL列表管理
            if hasattr(basic_page, 'url_listbox'):
                initial_count = basic_page.url_listbox.count()
                basic_page.url_listbox.addItem("https://test.com")
                new_count = basic_page.url_listbox.count()
                if new_count == initial_count + 1:
                    self.log_test("URL列表管理", True)
                else:
                    self.log_test("URL列表管理", False)
            
            # 测试输出目录
            if hasattr(basic_page, 'output_entry'):
                basic_page.output_entry.setText("/tmp/test")
                if basic_page.output_entry.text() == "/tmp/test":
                    self.log_test("输出目录设置", True)
                else:
                    self.log_test("输出目录设置", False)
            
            # 测试配置管理
            config = basic_page.get_config()
            if isinstance(config, dict) and 'urls' in config and 'output_dir' in config:
                self.log_test("BasicPage配置管理", True)
            else:
                self.log_test("BasicPage配置管理", False)
            
            return True
            
        except Exception as e:
            self.log_test("BasicPage功能", False, f"异常: {e}")
            return False
    
    def test_webpage_page_functionality(self):
        """测试WebpagePage功能"""
        print("\n🌐 测试WebpagePage功能...")
        
        try:
            webpage_page = self.main_window.webpage_page
            
            # 测试选项管理
            options = webpage_page.get_options()
            if isinstance(options, dict):
                self.log_test("WebpagePage选项获取", True, f"包含{len(options)}个选项")
            else:
                self.log_test("WebpagePage选项获取", False)
            
            # 测试配置管理
            config = webpage_page.get_config()
            if isinstance(config, dict):
                self.log_test("WebpagePage配置管理", True)
            else:
                self.log_test("WebpagePage配置管理", False)
            
            return True
            
        except Exception as e:
            self.log_test("WebpagePage功能", False, f"异常: {e}")
            return False
    
    def test_advanced_page_functionality(self):
        """测试AdvancedPage功能"""
        print("\n⚙️ 测试AdvancedPage功能...")
        
        try:
            advanced_page = self.main_window.advanced_page
            
            # 测试语言选择
            if hasattr(advanced_page, 'language_combo'):
                advanced_page.set_language('en')
                if advanced_page.get_language() == 'en':
                    self.log_test("语言选择", True)
                else:
                    self.log_test("语言选择", False)
            
            # 测试日志级别
            if hasattr(advanced_page, 'log_level_combo'):
                advanced_page.set_log_level('DEBUG')
                if advanced_page.get_log_level() == 'DEBUG':
                    self.log_test("日志级别设置", True)
                else:
                    self.log_test("日志级别设置", False)
            
            # 测试调试模式
            if hasattr(advanced_page, 'debug_mode_cb'):
                advanced_page.set_debug_mode(True)
                if advanced_page.get_debug_mode() == True:
                    self.log_test("调试模式设置", True)
                else:
                    self.log_test("调试模式设置", False)
            
            # 测试用户数据路径
            advanced_page.set_user_data_path("/test/path")
            if advanced_page.get_user_data_path() == "/test/path":
                self.log_test("用户数据路径设置", True)
            else:
                self.log_test("用户数据路径设置", False)
            
            return True
            
        except Exception as e:
            self.log_test("AdvancedPage功能", False, f"异常: {e}")
            return False
    
    def test_about_page_functionality(self):
        """测试AboutPage功能"""
        print("\nℹ️ 测试AboutPage功能...")
        
        try:
            about_page = self.main_window.about_page
            
            # 测试配置管理
            config = about_page.get_config()
            if isinstance(config, dict) and 'homepage_clicked' in config and 'last_update_check' in config:
                self.log_test("AboutPage配置管理", True)
            else:
                self.log_test("AboutPage配置管理", False)
            
            # 测试版本检查按钮
            if hasattr(about_page, 'check_updates_btn'):
                if about_page.check_updates_btn.isEnabled():
                    self.log_test("版本检查按钮", True, "按钮可用")
                else:
                    self.log_test("版本检查按钮", False, "按钮不可用")
            
            return True
            
        except Exception as e:
            self.log_test("AboutPage功能", False, f"异常: {e}")
            return False
    
    def test_command_panel_functionality(self):
        """测试CommandPanel功能"""
        print("\n🎮 测试CommandPanel功能...")
        
        try:
            command_panel = self.main_window.command_panel
            
            # 测试进度设置
            command_panel.set_progress(50, "测试进度")
            if command_panel.progress.value() == 50:
                self.log_test("进度设置", True)
            else:
                self.log_test("进度设置", False)
            
            # 测试转换状态
            command_panel.setConvertingState(True)
            if not command_panel.btn_convert.isVisible() and command_panel.btn_stop.isVisible():
                self.log_test("转换状态切换", True)
            else:
                self.log_test("转换状态切换", False)
            
            # 测试按钮状态
            command_panel.setEnabled(False)
            if not command_panel.btn_convert.isEnabled():
                self.log_test("按钮状态控制", True)
            else:
                self.log_test("按钮状态控制", False)
            
            # 恢复状态
            command_panel.setEnabled(True)
            command_panel.setConvertingState(False)
            
            return True
            
        except Exception as e:
            self.log_test("CommandPanel功能", False, f"异常: {e}")
            return False
    
    def test_log_panel_functionality(self):
        """测试LogPanel功能"""
        print("\n📋 测试LogPanel功能...")
        
        try:
            log_panel = self.main_window.log_panel
            
            # 测试日志添加
            log_panel.addLog("测试日志消息", "INFO")
            content = log_panel.getLogContent()
            if "测试日志消息" in content:
                self.log_test("日志添加", True)
            else:
                self.log_test("日志添加", False)
            
            # 测试日志清除
            log_panel.clearLog()
            content = log_panel.getLogContent()
            if not content.strip():
                self.log_test("日志清除", True)
            else:
                self.log_test("日志清除", False)
            
            # 测试配置管理
            config = log_panel.get_config()
            if isinstance(config, dict) and 'log_content' in config:
                self.log_test("LogPanel配置管理", True)
            else:
                self.log_test("LogPanel配置管理", False)
            
            return True
            
        except Exception as e:
            self.log_test("LogPanel功能", False, f"异常: {e}")
            return False
    
    def test_direct_log_methods(self):
        """测试直接日志方法"""
        print("\n📝 测试直接日志方法...")
        
        try:
            # 测试各种日志方法
            self.main_window.log_info("信息日志测试")
            self.main_window.log_success("成功日志测试")
            self.main_window.log_warning("警告日志测试")
            self.main_window.log_error("错误日志测试")
            self.main_window.log_debug("调试日志测试")
            
            content = self.main_window.log_panel.getLogContent()
            
            # 检查各种日志是否都添加了
            log_types = ["ℹ️", "✅", "⚠️", "❌", "🐛"]
            all_present = all(log_type in content for log_type in log_types)
            
            if all_present:
                self.log_test("直接日志方法", True, "所有日志类型都正常工作")
            else:
                self.log_test("直接日志方法", False, "部分日志类型未正常工作")
            
            return True
            
        except Exception as e:
            self.log_test("直接日志方法", False, f"异常: {e}")
            return False
    
    def test_signal_connections(self):
        """测试信号连接"""
        print("\n🔗 测试信号连接...")
        
        try:
            # 测试页面信号
            pages = ['basic_page', 'webpage_page', 'advanced_page', 'about_page']
            for page_name in pages:
                page = getattr(self.main_window, page_name)
                if hasattr(page, 'signals'):
                    self.log_test(f"{page_name}信号", True, "信号已定义")
                else:
                    self.log_test(f"{page_name}信号", False, "信号未定义")
            
            # 测试组件信号
            components = ['command_panel', 'log_panel']
            for component_name in components:
                component = getattr(self.main_window, component_name)
                if hasattr(component, 'signals'):
                    self.log_test(f"{component_name}信号", True, "信号已定义")
                else:
                    self.log_test(f"{component_name}信号", False, "信号未定义")
            
            return True
            
        except Exception as e:
            self.log_test("信号连接", False, f"异常: {e}")
            return False
    
    def test_configuration_management(self):
        """测试配置管理"""
        print("\n⚙️ 测试配置管理...")
        
        try:
            # 测试获取当前状态
            state = self.main_window._get_current_state()
            if isinstance(state, dict):
                self.log_test("状态获取", True, f"包含{len(state)}个配置项")
            else:
                self.log_test("状态获取", False)
            
            # 测试应用状态
            test_state = {
                "urls": ["https://example.com"],
                "output_dir": "/tmp/test",
                "use_proxy": False,
                "ignore_ssl": False,
                "download_images": True,
                "filter_site_chrome": True,
                "use_shared_browser": True
            }
            
            self.main_window._apply_state(test_state)
            
            # 验证状态是否应用成功
            applied_state = self.main_window._get_current_state()
            if applied_state.get("urls") == test_state["urls"]:
                self.log_test("状态应用", True)
            else:
                self.log_test("状态应用", False)
            
            return True
            
        except Exception as e:
            self.log_test("配置管理", False, f"异常: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始MarkdownAll GUI功能测试")
        print("=" * 50)
        
        # 运行所有测试
        tests = [
            self.test_application_startup,
            self.test_page_structure,
            self.test_component_structure,
            self.test_basic_page_functionality,
            self.test_webpage_page_functionality,
            self.test_advanced_page_functionality,
            self.test_about_page_functionality,
            self.test_command_panel_functionality,
            self.test_log_panel_functionality,
            self.test_direct_log_methods,
            self.test_signal_connections,
            self.test_configuration_management,
        ]
        
        for test_func in tests:
            try:
                test_func()
                # 处理事件队列
                self.app.processEvents()
                time.sleep(0.1)  # 短暂延迟
            except Exception as e:
                print(f"❌ 测试 {test_func.__name__} 发生异常: {e}")
        
        # 生成测试报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 50)
        print("📊 测试报告")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"失败: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        
        if failed_tests > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n✅ 测试完成!")
        
        # 保存详细报告
        report_file = "test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        print(f"📄 详细报告已保存到: {report_file}")


def main():
    """主函数"""
    tester = FunctionalityTester()
    tester.run_all_tests()
    
    # 保持应用程序运行一段时间以便观察
    print("\n⏰ 保持应用程序运行10秒以便观察...")
    QTimer.singleShot(10000, tester.app.quit)
    tester.app.exec()


if __name__ == "__main__":
    main()
