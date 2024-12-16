import cv2
import numpy as np
import time
import os
from ..utils.logger import Logger

class VideoProcessor:
    def __init__(self):
        self.logger = Logger()
        self.cap = None
        # 全局变量用于框选
        self.drawing = False
        self.ix, self.iy = -1, -1
        self.selection = None
        self.last_frame = None
        self.display_buffer = None
        self.base_frame = None

    def draw_rectangle(self, event, x, y, flags, param):
        """鼠标框选事件处理函数"""
        window_name = param['window_name']
        
        # 创建静态显示缓冲
        if not hasattr(self, 'display_buffer'):
            self.display_buffer = param['frame'].copy()
            self.base_frame = param['frame'].copy()
        
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.ix, self.iy = x, y
            self.selection = None
            # 保存原始帧
            self.base_frame = param['frame'].copy()
            # 重置显示缓冲
            self.display_buffer = self.base_frame.copy()
            
        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            # 使用基础帧
            self.display_buffer = self.base_frame.copy()
            
            # 绘制矩形和文本
            cv2.rectangle(self.display_buffer, (self.ix, self.iy), (x, y), (0, 255, 0), 2)
            
            # 计算比例
            height = self.base_frame.shape[0]
            current_bottom = min(self.iy, y) / height
            current_top = max(self.iy, y) / height
            
            # 添加文本（带背景）
            text = f'区域: {current_bottom:.3f} - {current_top:.3f}'
            (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            cv2.rectangle(self.display_buffer, (10, 5), 
                         (10 + text_w, 35), (0, 0, 0), -1)
            cv2.putText(self.display_buffer, text, (10, 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            cv2.imshow(window_name, self.display_buffer)
            
        elif event == cv2.EVENT_LBUTTONUP:
            if self.drawing:
                self.drawing = False
                if abs(x - self.ix) > 10 and abs(y - self.iy) > 10:  # 确保选择区域足够大
                    x1, y1 = min(self.ix, x), min(self.iy, y)
                    x2, y2 = max(self.ix, x), max(self.iy, y)
                    self.selection = (x1, y1, x2, y2)
                    
                    # 最终显示缓冲上绘制确认框
                    final_frame = self.base_frame.copy()
                    cv2.rectangle(final_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    height = final_frame.shape[0]
                    bottom_ratio = y1 / height
                    top_ratio = y2 / height
                    
                    # 添加确认文本（带背景）
                    text = f'已选区域: {bottom_ratio:.3f} - {top_ratio:.3f}'
                    (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                    cv2.rectangle(final_frame, (10, 5), 
                                (10 + text_w, 35), (0, 0, 0), -1)
                    cv2.putText(final_frame, text, (10, 25),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    
                    cv2.imshow(window_name, final_frame)

    def select_subtitle_area(self, video_path):
        """选择字幕区域"""
        try:
            if not self.open_video(video_path):
                return None
                
            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            # 创建窗口
            window_name = '视频播放 (空格键暂停后框选，ESC重选，ENTER确认)'
            cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
            
            paused = False
            frame = None
            self.selection = None
            
            print("\n播放控制：")
            print("空格键 - 暂停/继续")
            print("→ - 快进5秒")
            print("← - 快退5秒")
            print("暂停后可以框选字幕区域")
            print("ESC - 重新选择")
            print("ENTER - 确认选择")
            
            while True:
                if not paused:
                    ret, frame = self.cap.read()
                    if not ret:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 循环播放
                        continue
                    
                    # 调整帧大小以便显示
                    max_height = 720
                    if frame.shape[0] > max_height:
                        scale = max_height / frame.shape[0]
                        new_width = int(frame.shape[1] * scale)
                        frame = cv2.resize(frame, (new_width, max_height))
                    
                    # 显示当前时间
                    current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                    current_time = current_frame / fps
                    time_str = time.strftime('%H:%M:%S', time.gmtime(current_time))
                    cv2.putText(frame, time_str, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    cv2.imshow(window_name, frame)
                
                # 处理按键
                key = cv2.waitKey(25) & 0xFF
                
                if key == 27:  # ESC
                    self.selection = None  # 重置选择
                    if frame is not None:
                        cv2.imshow(window_name, frame.copy())
                elif key == 32:  # 空格键
                    paused = not paused
                    if paused and frame is not None:
                        # 设置鼠标回调
                        param = {'frame': frame.copy(), 'window_name': window_name}
                        cv2.setMouseCallback(window_name, self.draw_rectangle, param)
                elif key == 83 and not paused:  # →
                    current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, min(total_frames - 1, current_frame + int(fps * 5)))
                elif key == 81 and not paused:  # ←
                    current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, current_frame - int(fps * 5)))
                elif key == 13 and self.selection and paused:  # Enter
                    x1, y1, x2, y2 = self.selection
                    height = frame.shape[0]
                    bottom_ratio = y1 / height
                    top_ratio = y2 / height
                    self.close()
                    return (bottom_ratio, top_ratio)
                elif key == ord('q'):  # Q
                    break
                    
            self.close()
            return None
            
        except Exception as e:
            self.logger.error(f"选择字幕区域失败: {str(e)}")
            self.close()
            return None

    def open_video(self, video_path):
        """打开视频文件"""
        try:
            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                raise Exception(f"Cannot open video file: {video_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to open video: {str(e)}")
            return False
            
    def close(self):
        """关闭视频"""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()