import sys
import os

# 将项目根目录添加到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from src.gui.main_window import MainWindow
from PyQt5.QtWidgets import QApplication

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())