from __future__ import annotations

import os
import sys

from markitdown_app.ui.pyside.gui import main as pyside_main


def main() -> None:
    """PySide GUI 入口点"""
    try:
        # 设置 Qt 环境变量以减少警告
        os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        
        pyside_main()
    except ImportError as e:
        print("错误：无法导入 PySide6")
        print("请安装: pip install PySide6")
        sys.exit(1)
    except Exception as e:
        print(f"启动 PySide GUI 时出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
