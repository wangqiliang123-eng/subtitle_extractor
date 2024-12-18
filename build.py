import PyInstaller.__main__
import sys
import os

# 确保在正确的目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 配置打包参数
PyInstaller.__main__.run([
    'main.py',  # 主程序入口
    '--name=字幕提取器',  # 程序名称
    '--windowed',  # 使用GUI模式
    '--onefile',  # 打包成单个文件
    '--icon=resources/icon.ico',  # 程序图标（如果有）
    # 添加所需数据文件
    '--add-data=resources;resources',  # 资源文件
    # 确保包含所有必要的依赖
    '--hidden-import=paddleocr',
    '--hidden-import=cv2',
    '--hidden-import=numpy',
    '--hidden-import=PyQt5',
    # 设置日志等级
    '--log-level=INFO',
]) 