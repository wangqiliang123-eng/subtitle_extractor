from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QListWidget, QTextEdit, 
                            QFileDialog, QMessageBox, QProgressBar)
from PyQt5.QtCore import QThread, pyqtSignal
from src.core.video import VideoProcessor
from src.core.extractor import SubtitleExtractor
from src.utils.logger import Logger
import os

class VideoProcessThread(QThread):
    progress_updated = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    video_progress = pyqtSignal(int, int)  # (视频索引, 进度值)
    finished = pyqtSignal()
    
    def __init__(self, extractor, video_path, subtitle_area, video_index):
        super().__init__()
        self.extractor = extractor
        self.video_path = video_path
        self.subtitle_area = subtitle_area
        self.video_index = video_index
        self.is_running = True
        
    def run(self):
        try:
            if not self.is_running:
                return
                
            base_name = os.path.splitext(os.path.basename(self.video_path))[0]
            video_name = os.path.basename(self.video_path)
            
            video_dir = os.path.dirname(self.video_path)
            output_dir = os.path.join(video_dir, 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            counter = 1
            output_file = f"{base_name}.srt"
            output_path = os.path.join(output_dir, output_file)
            
            while os.path.exists(output_path):
                output_file = f"{base_name}_{counter}.srt"
                output_path = os.path.join(output_dir, output_file)
                counter += 1
            
            def progress_callback(frame_progress):
                if not self.is_running:
                    raise InterruptedError("处理被用户中断")
                if frame_progress == 0:
                    frame_progress = 0.01
                progress = int(frame_progress * 100)
                self.video_progress.emit(self.video_index, progress)
                self.progress_updated.emit(f"视频 {self.video_index + 1} 处理进度: {progress}%")
            
            if self.is_running:
                self.extractor.extract_subtitles(
                    self.video_path,
                    output_path,
                    'ch',
                    self.subtitle_area,
                    callback=progress_callback
                )
                self.progress_updated.emit(f"  √ {video_name} 处理完成，保存为: {output_file}")
            
        except InterruptedError as e:
            self.progress_updated.emit(f"  × {video_name} 处理被中断: {str(e)}")
        except Exception as e:
            self.progress_updated.emit(f"  × {video_name} 处理失败: {str(e)}")
        finally:
            self.finished.emit()
            
    def stop(self):
        self.is_running = False
        self.quit()

class ProcessThread(QThread):
    progress_updated = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    finished = pyqtSignal()
    
    def __init__(self, extractor, video_files, subtitle_areas):
        super().__init__()
        self.extractor = extractor
        self.video_files = video_files
        self.subtitle_areas = subtitle_areas
        self.is_running = True
        self.threads = []
        self.video_progresses = {}
        
    def calculate_total_progress(self):
        if not self.video_progresses:
            return 0
        return int(sum(self.video_progresses.values()) / len(self.video_files))
    
    def update_video_progress(self, video_index, progress):
        if not self.is_running:
            return
        self.video_progresses[video_index] = progress
        total_progress = self.calculate_total_progress()
        self.progress_value.emit(total_progress)
    
    def run(self):
        if not self.video_files or not self.subtitle_areas:
            return
            
        total_videos = len(self.video_files)
        processed = 0
        group_size = 5
        output_paths = []
        
        try:
            video_groups = [self.video_files[i:i + group_size] 
                           for i in range(0, len(self.video_files), group_size)]
            
            current_video_index = 0
            for group_idx, group in enumerate(video_groups, 1):
                if not self.is_running:
                    raise InterruptedError("处理被用户中断")
                    
                self.progress_updated.emit(f"\n========== 开始处理第 {group_idx} 组视频 ==========")
                
                self.threads.clear()
                for video_path in group:
                    if not self.is_running:
                        raise InterruptedError("处理被用户中断")
                        
                    if video_path not in self.subtitle_areas:
                        continue
                        
                    base_name = os.path.splitext(os.path.basename(video_path))[0]
                    video_dir = os.path.dirname(video_path)
                    output_dir = os.path.join(video_dir, 'output')
                    output_path = os.path.join(output_dir, f"{base_name}.srt")
                    output_paths.append(output_path)
                    
                    thread = VideoProcessThread(
                        self.extractor,
                        video_path,
                        self.subtitle_areas[video_path],
                        current_video_index
                    )
                    thread.progress_updated.connect(self.progress_updated.emit)
                    thread.video_progress.connect(self.update_video_progress)
                    self.threads.append(thread)
                    current_video_index += 1
                
                for thread in self.threads:
                    if not self.is_running:
                        raise InterruptedError("处理被用户中断")
                    thread.start()
                    
                for thread in self.threads:
                    if not self.is_running:
                        raise InterruptedError("处理被用户中断")
                    thread.wait()
                    processed += 1
                
                if self.is_running:
                    self.progress_updated.emit(f"\n========== 第 {group_idx} 组处理完成 ==========")
                    self.progress_updated.emit(f"成功处理: {len(self.threads)}/{len(group)} 个视频")
            
            if self.is_running:
                self.progress_updated.emit("\n=== 所有视频处理完成 ===")
                self.progress_updated.emit(f"总共成功处理: {processed}/{total_videos} 个视频")
                self.progress_updated.emit("\n字幕文件保存在以下位置：")
                for path in output_paths:
                    self.progress_updated.emit(path)
                    
        except InterruptedError as e:
            self.progress_updated.emit(f"\n处理已中断: {str(e)}")
        finally:
            self.finished.emit()

    def stop(self):
        self.is_running = False
        for thread in self.threads:
            thread.stop()
            thread.wait()
        self.quit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_processor = VideoProcessor()
        self.extractor = SubtitleExtractor()
        self.logger = Logger()
        self.video_files = []
        self.subtitle_areas = {}
        self.process_thread = None
        self.current_video_number = 1
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('字幕提取器')
        self.setGeometry(300, 300, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

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

        button_layout = QHBoxLayout()
        
        self.open_btn = QPushButton('打开文件')
        self.select_area_btn = QPushButton('框选区域')
        self.start_btn = QPushButton('开始处理')
        self.stop_btn = QPushButton('停止处理')

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

        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        
        log_label = QLabel('处理日志:')
        log_label.setStyleSheet('font-weight: bold; margin-top: 10px;')
        log_layout.addWidget(log_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 1px;
            }
        """)
        log_layout.addWidget(self.progress_bar)
        
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
        
        layout.addWidget(log_container)
        
        self.open_btn.clicked.connect(self.open_files)
        self.select_area_btn.clicked.connect(self.select_area)
        self.start_btn.clicked.connect(self.start_process)
        self.stop_btn.clicked.connect(self.stop_process)

        self.select_area_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

    def open_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv)"
        )
        
        if files:
            # 添加新文件，避免重复
            existing_files = set(self.video_files)
            new_files = []
            for file in files:
                if file not in existing_files:
                    new_files.append(file)
                    existing_files.add(file)
            
            # 更新文件列表
            self.video_files.extend(new_files)
            
            # 更新显示
            self.file_list.clear()
            width = len(str(len(self.video_files)))
            for i, file_path in enumerate(self.video_files, 1):
                file_name = os.path.basename(file_path)
                self.file_list.addItem(f"{i:>{width}}. {file_name}")
            
            # 更新日志
            if new_files:
                self.log_text.append(f"添加了 {len(new_files)} 个新视频文件，"
                                   f"当前共有 {len(self.video_files)} 个文件")
            else:
                self.log_text.append("没有添加新文件（选择的文件已存在）")
            
            # 更新按钮状态
            self.select_area_btn.setEnabled(True)
            self.start_btn.setEnabled(False)

    def select_area(self):
        if not self.video_files:
            QMessageBox.warning(self, "警告", "请先选择视频文件")
            return
            
        self.subtitle_areas.clear()
        self.current_video_number = 1
        total_videos = len(self.video_files)
        
        for i, video_path in enumerate(self.video_files, 1):
            file_name = os.path.basename(video_path)
            self.update_log(f"{i}、请框选第 {i}/{total_videos} 个视频的字幕区域: {file_name}")
            
            area = self.video_processor.select_subtitle_area(video_path)
            if area:
                self.subtitle_areas[video_path] = area
            self.current_video_number += 1

        if self.subtitle_areas:
            self.start_btn.setEnabled(True)
        else:
            self.start_btn.setEnabled(False)

    def start_process(self):
        if not self.subtitle_areas:
            QMessageBox.warning(self, "警告", "请先框选字幕区域")
            return
        
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_bar.setFormat('%p%')
        
        self.open_btn.setEnabled(False)
        self.select_area_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.process_thread = ProcessThread(
            self.extractor,
            self.video_files,
            self.subtitle_areas
        )
        
        self.process_thread.progress_updated.connect(self.update_log)
        self.process_thread.progress_value.connect(lambda v: self.progress_bar.setValue(v))
        self.process_thread.finished.connect(self.on_process_finished)
        
        self.process_thread.start()

    def stop_process(self):
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
                self.update_log("正在停止处理，请稍候...")

    def on_process_finished(self):
        self.open_btn.setEnabled(True)
        self.select_area_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.reset_progress()

    def update_log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def reset_progress(self):
        self.progress_bar.setValue(0)

    def closeEvent(self, event):
        if self.process_thread and self.process_thread.isRunning():
            self.process_thread.stop()
            self.process_thread.wait()
        self.video_processor.close()
        event.accept()

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())