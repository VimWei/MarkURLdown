from __future__ import annotations
import os
import sys
import random
import glob

# 立即显示splash screen，延迟导入重型依赖
def show_immediate_splash():
    """立即显示splash screen，不等待任何重型导入"""
    from PySide6.QtWidgets import QApplication, QSplashScreen
    from PySide6.QtGui import QPixmap
    from PySide6.QtCore import Qt
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # --- 快速Splash Screen Setup ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(script_dir, 'markitdown_app', 'ui', 'assets')
    
    # 预定义splash图片路径，避免glob扫描
    splash_candidates = [
        os.path.join(assets_dir, 'splash_01.png'),
        os.path.join(assets_dir, 'splash_02.png'),
        os.path.join(assets_dir, 'splash_03.png')
    ]
    
    # 找到所有存在的splash图片，然后随机选择
    available_splash_images = [path for path in splash_candidates if os.path.exists(path)]
    
    if available_splash_images:
        # 随机选择一个splash图片
        splash_image_path = random.choice(available_splash_images)
    else:
        splash_image_path = None
    
    if splash_image_path:
        pixmap = QPixmap(splash_image_path)
    else:
        # 创建简单的彩色splash，避免文件I/O
        pixmap = QPixmap(600, 350)
        pixmap.fill(Qt.darkBlue)

    splash = QSplashScreen(pixmap)
    splash.showMessage(
        "Starting...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        Qt.white
    )
    splash.show()
    
    # 立即处理事件确保splash显示
    app.processEvents()
    
    return app, splash

def run_app():
    """
    Creates the application, shows a splash screen immediately, then loads the main window.
    """
    try:
        # 立即显示splash screen
        app, splash = show_immediate_splash()
        
        # 更新splash消息
        from PySide6.QtCore import Qt
        splash.showMessage(
            "Loading UI components...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.white
        )
        app.processEvents()

        # --- 延迟导入重型依赖 ---
        print("Importing main application...")
        from markitdown_app.ui.pyside.gui import PySideApp
        from markitdown_app.io.config import load_json_from_root
        print("Main application imported.")
        
        splash.showMessage(
            "Loading configuration...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.white
        )
        app.processEvents()

        # Load persistent settings (language, etc.)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        settings = load_json_from_root(script_dir, "settings.json")

        # 创建主窗口
        print("Creating main window...")
        main_window = PySideApp(root_dir=script_dir, settings=settings)
        print("Main window created.")

        # --- 从Splash过渡到主窗口 ---
        splash.finish(main_window)
        main_window.show()
        print("Main window displayed.")

        sys.exit(app.exec())
        
    except Exception as e:
        print(f"Error during startup: {e}")
        import traceback
        traceback.print_exc()
        # 如果出错，尝试显示错误对话框
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Startup Error", f"Application failed to start:\n{e}")
        except:
            pass

if __name__ == "__main__":
    run_app()