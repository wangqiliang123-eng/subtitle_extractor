from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QListWidget, QTextEdit, 
                            QFileDialog, QMessageBox, QProgressBar)
from PyQt5.QtCore import QThread, pyqtSignal
from ..core.video import VideoProcessor
from ..core.extractor import SubtitleExtractor
from ..utils.logger import Logger
import os

# 添加视频处理线程类
class VideoProcessThread(QThread):
    progress_updated = pyqtSignal(str)
    progress_value = pyqtSignal(int, int)
    finished = pyqtSignal()
    
    def __init__(self, extractor, video_path, subtitle_area):
        super().__init__()
        self.extractor = extractor
        self.video_path = video_path
        self.subtitle_area = subtitle_area
        self.is_running = True
        
    def run(self):
        try:
            output_file = os.path.splitext(os.path.basename(self.video_path))[0] + ".srt"
            self.extractor.extract_subtitles(
                self.video_path,
                output_file,
                'ch',
                self.subtitle_area,
                callback=self.progress_updated.emit
            )
            self.progress_updated.emit(f"  √ {os.path.basename(self.video_path)} 处理完成")
        except Exception as e:
            self.progress_updated.emit(f"  × {os.path.basename(self.video_path)} 处理失败: {str(e)}")
        finally:
            self.finished.emit()
            
    def stop(self):
        self.is_running = False

# 修改主处理线程类
class ProcessThread(QThread):
    progress_updated = pyqtSignal(str)
    progress_value = pyqtSignal(int, int)
    finished = pyqtSignal()
    
    def __init__(self, extractor, video_files, subtitle_areas):
        super().__init__()
        self.extractor = extractor
        self.video_files = video_files
        self.subtitle_areas = subtitle_areas
        self.is_running = True
        self.threads = []
        
    def run(self):
        if not self.video_files or not self.subtitle_areas:
            return
            
        total_videos = len(self.video_files)
        processed = 0
        group_size = 5
        
        # 将视频分组
        video_groups = [self.video_files[i:i + group_size] 
                       for i in range(0, len(self.video_files), group_size)]
        
        for group_idx, group in enumerate(video_groups, 1):
            if not self.is_running:
                break
                
            self.progress_updated.emit(f"\n开始处理第 {group_idx} 组视频:")
            
            # 为组内每个视频创建处理线程
            self.threads.clear()
            for video_path in group:
                if video_path not in self.subtitle_areas:
                    continue
                    
                thread = VideoProcessThread(
                    self.extractor,
                    video_path,
                    self.subtitle_areas[video_path]
                )
                thread.progress_updated.connect(self.progress_updated.emit)
                self.threads.append(thread)
                
            # 启动组内所有线程
            for thread in self.threads:
                thread.start()
                
            # 等待组内所有线程完成
            for thread in self.threads:
                thread.wait()
                processed += 1
                self.progress_value.emit(processed, total_videos)
            
            # 每组处理完成后的提示
            if self.is_running:
                self.progress_updated.emit(f"\n第 {group_idx} 组处理完成！")
                self.progress_updated.emit(f"成功处理: {len(self.threads)}/{len(group)} 个视频")
                self.progress_updated.emit(f"总进度: {processed}/{total_videos}\n")
        
        # 所有视频处理完成的提示
        if self.is_running:
            self.progress_updated.emit("\n=== 所有视频处理完成 ===")
            self.progress_updated.emit(f"总共成功处理: {processed}/{total_videos} 个视频")
        
        self.finished.emit()
            
    def stop(self):
        self.is_running = False
        for thread in self.threads:
            thread.stop()
            thread.wait()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_processor = VideoProcessor()
        self.extractor = SubtitleExtractor()
        self.logger = Logger()
        self.video_files = []
        self.subtitle_areas = {}
        self.process_thread = None  # 加线程属性
        self.initUI()
        
        # 连接进度信号
        self.extractor.progress_updated.connect(self.update_progress)

    def initUI(self):
        """初始化UI"""
        self.setWindowTitle('字幕提取器')
        self.setGeometry(300, 300, 800, 600)

        # 创建主widget和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 创建视频文件列表
        list_label = QLabel('视频文件列表:')
        list_label.setStyleSheet('font-weight: bold;')
        layout.addWidget(list_label)
        
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e6f3ff;
                color: black;
            }
        """)
        layout.addWidget(self.file_list)

        # 创建按钮组
        button_layout = QHBoxLayout()
        
        self.open_btn = QPushButton('打开文件')
        self.select_area_btn = QPushButton('框选区域')
        self.start_btn = QPushButton('开始处理')
        self.stop_btn = QPushButton('停止处理')

        # 设置按钮样式
        button_style = """
            QPushButton {
                padding: 8px 16px;
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2a5f9e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """
        
        for btn in [self.open_btn, self.select_area_btn, self.start_btn, self.stop_btn]:
            btn.setStyleSheet(button_style)
            button_layout.addWidget(btn)

        layout.addLayout(button_layout)

        # 创建日志显示区域容器
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        
        # 创建日志标签
        log_label = QLabel('处理日志:')
        log_label.setStyleSheet('font-weight: bold; margin-top: 10px;')
        log_layout.addWidget(log_label)
        
        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # 默认隐藏
        log_layout.addWidget(self.progress_bar)
        
        # 创建日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
                font-family: Consolas, Monaco, monospace;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        # 将日志容器添加到主布局
        layout.addWidget(log_container)
        
        # 连接信号
        self.open_btn.clicked.connect(self.open_files)
        self.select_area_btn.clicked.connect(self.select_area)
        self.start_btn.clicked.connect(self.start_process)
        self.stop_btn.clicked.connect(self.stop_process)
        self.extractor.progress_updated.connect(self.update_progress)

        # 初始状态设置
        self.select_area_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.log_text.append("欢迎使用字幕提取器")

    def open_files(self):
        """打开视频文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv)"
        )
        
        if files:
            self.video_files = files
            self.file_list.clear()
            
            width = len(str(len(self.video_files)))
            for i, file_path in enumerate(self.video_files, 1):
                file_name = os.path.basename(file_path)
                item_text = f"{i:>{width}}. {file_name}"
                self.file_list.addItem(item_text)
            
            msg = f"已添加 {len(files)} 个视频文件"
            self.logger.info(msg)
            self.update_log(msg)
            
            self.select_area_btn.setEnabled(True)
            self.start_btn.setEnabled(False)

    def select_area(self):
        """框选字幕区域"""
        if not self.video_files:
            QMessageBox.warning(self, "警告", "请先选择视频文件")
            return
            
        self.subtitle_areas.clear()
        total_videos = len(self.video_files)
        
        for i, video_path in enumerate(self.video_files, 1):
            file_name = os.path.basename(video_path)
            self.update_log(f"请框选第 {i}/{total_videos} 个视频的字幕区域: {file_name}")
            
            area = self.video_processor.select_subtitle_area(video_path)
            if area:
                self.subtitle_areas[video_path] = area
                bottom_ratio, top_ratio = area
                msg = f"视频 {i:>{len(str(total_videos))}}/{total_videos} {file_name} "
                msg += f"字幕区域：{bottom_ratio:.3f} - {top_ratio:.3f}"
                self.update_log(msg)
                self.start_btn.setEnabled(True)
            else:
                msg = f"跳过视频 {i:>{len(str(total_videos))}}/{total_videos} {file_name}"
                self.update_log(msg)

        if self.subtitle_areas:
            self.update_log(f"\n共完成 {len(self.subtitle_areas)}/{total_videos} 个视频的区域选择")
        else:
            self.start_btn.setEnabled(False)
            self.update_log("\n未选择任何字幕区域")

    def start_process(self):
        """开始处理"""
        if not self.subtitle_areas:
            QMessageBox.warning(self, "警告", "请先框选字幕区域")
            return
            
        # 更新按钮状态
        self.open_btn.setEnabled(False)
        self.select_area_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.update_log("\n开始处理视频...")
        
        # 创建并启动处理线程
        self.process_thread = ProcessThread(
            self.extractor,
            self.video_files,
            self.subtitle_areas
        )
        self.process_thread.progress_updated.connect(self.update_log)
        self.process_thread.progress_value.connect(self.update_progress)  # 连接进度值信号
        self.process_thread.finished.connect(self.on_process_finished)
        self.process_thread.start()

    def stop_process(self):
        """停止处理"""
        if self.process_thread and self.process_thread.isRunning():
            reply = QMessageBox.question(
                self, 
                '确认', 
                "确定要停止处理吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.process_thread.stop()
                self.process_thread.wait()
                self.update_log("处理已停止")
                self.on_process_finished()

    def on_process_finished(self):
        """处理完成的回调"""
        # 恢复按钮状态
        self.open_btn.setEnabled(True)
        self.select_area_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        # 重置进度条
        self.reset_progress()

    def update_log(self, text):
        """更新日志显示"""
        # 获取当前日志行数
        current_lines = self.log_text.document().lineCount()
        
        if text.startswith('\r处理进度:'):
            # 使用等宽字体显示进度条
            text = f'<pre style="margin: 0; font-family: Consolas, monospace;">{text[1:]}</pre>'
            
            # 查找并更新或添加进度条
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.End)
            cursor.movePosition(cursor.StartOfBlock, cursor.KeepAnchor)
            if cursor.selectedText().startswith('处理进度:'):
                cursor.removeSelectedText()
            self.log_text.insertHtml(text)
        else:
            # 添加行号
            line_number = current_lines
            number_width = 4  # 行号宽度
            
            # 其他日志信息正常显示
            if text.startswith('  √'):
                # 成功处理使用绿色
                text = f'<p style="color: #27ae60; margin: 0;">{line_number:>{number_width}}. {text}</p>'
            elif text.startswith('  ×'):
                # 处理失败使用红色
                text = f'<p style="color: #e74c3c; margin: 0;">{line_number:>{number_width}}. {text}</p>'
            elif text.startswith('-'):
                # 正在处理的文件使用普通黑色
                text = f'<p style="margin: 0;">{line_number:>{number_width}}. {text}</p>'
            elif text.startswith('第') and '组处理完成' in text:
                # 组完成提示使用蓝色
                text = f'<p style="color: #3498db; font-weight: bold; margin: 0;">{line_number:>{number_width}}. {text}</p>'
            elif text.startswith('==='):
                # 完成提示使用绿色
                text = f'<p style="color: #2ecc71; font-weight: bold; margin: 0;">{line_number:>{number_width}}. {text}</p>'
            else:
                # 其他信息使用普通段落
                text = f'<p style="margin: 0;">{line_number:>{number_width}}. {text}</p>'
                
            self.log_text.insertHtml(text)
        
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def update_progress(self, current, total):
        """更新进度条"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.progress_bar.setVisible(True)
        
    def reset_progress(self):
        """重置进度条"""
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

    def closeEvent(self, event):
        """关闭窗口时的处理"""
        if self.process_thread and self.process_thread.isRunning():
            self.process_thread.stop()
            self.process_thread.wait()
        self.video_processor.close()
        event.accept()