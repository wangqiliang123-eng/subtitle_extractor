import cv2
import numpy as np
from paddleocr import PaddleOCR
import time
import os
from tqdm import tqdm

class SubtitleExtractor:
    def __init__(self):
        self.ocr = None
        self.initialize_ocr()
        
    def initialize_ocr(self):
        if self.ocr is None:
            try:
                det_model_dir = "C:/subtitle/models/det"
                rec_model_dir = "C:/subtitle/models/rec"
                cls_model_dir = "C:/subtitle/models/cls"
                
                self.ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang='ch',
                    det_model_dir=det_model_dir,
                    rec_model_dir=rec_model_dir,
                    cls_model_dir=cls_model_dir,
                    show_log=True,
                    download_font=False,
                    max_batch_size=7
                )
                return True
            except Exception as e:
                print(f"初始化 OCR 失败: {str(e)}")
                return False
        return True

    def process_video_batch(self, video_files, subtitle_areas, callback=None):
        """
        批量处理视频
        """
        if not video_files or not subtitle_areas:
            return
            
        total_videos = len(video_files)
        processed = 0
        group_size = 5
        
        # 将视频分组
        video_groups = [video_files[i:i + group_size] for i in range(0, len(video_files), group_size)]
        
        for group_idx, group in enumerate(video_groups, 1):
            if callback:
                callback(f"\n开始处理第 {group_idx} 组视频:")
                
            group_processed = 0
            for video_path in group:
                if video_path not in subtitle_areas:
                    continue
                    
                try:
                    if callback:
                        callback(f"- 正在处理: {os.path.basename(video_path)}")
                        
                    output_file = os.path.splitext(os.path.basename(video_path))[0] + ".srt"
                    self.extract_subtitles(video_path, output_file, 'ch', subtitle_areas[video_path], callback=callback)
                    processed += 1
                    group_processed += 1
                    
                    if callback:
                        callback(f"  √ {os.path.basename(video_path)} 处理完成")
                        
                except Exception as e:
                    if callback:
                        callback(f"  × {os.path.basename(video_path)} 处理失败: {str(e)}")
                    continue
            
            # 每组处理完成后的提示
            if callback:
                callback(f"\n第 {group_idx} 组处理完成！")
                callback(f"成功处理: {group_processed}/{len(group)} 个视频")
                callback(f"总进度: {processed}/{total_videos}\n")
                
        # 所有视频处理完成的提示
        if callback:
            callback("\n=== 所有视频处理完成 ===")
            callback(f"总共成功处理: {processed}/{total_videos} 个视频")

    def extract_subtitles(self, video_path, output_file='subtitles.srt', lang='ch', subtitle_area=(0.8, 0.9), callback=None):
        """
        从视频中提取字幕并保存到文本文件
        """
        bottom_ratio, top_ratio = subtitle_area
        
        # 验证字幕区域比例
        if not (0 <= bottom_ratio <= 1 and 0 <= top_ratio <= 1):
            print("错误：字幕区域比例必须在0-1之间")
            return
        if bottom_ratio >= top_ratio:
            print("错误：底部比例必须小于顶部比例")
            return
        
        if not os.path.exists(video_path):
            print(f"错误：视频文件不存在: {video_path}")
            return
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("错误：无法打开视频文件")
            return
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 字幕提取参数
        MIN_DURATION = 0.5  # 最小持续0.5秒
        MAX_DURATION = 3.0  # 最大持续3秒
        EMPTY_FRAMES_THRESHOLD = 6  # 连续6帧无字幕才认为字幕消失
        
        subtitles = []
        last_text = ""
        frame_count = 0
        start_time = None
        empty_frames = 0
        subtitle_index = 1
        
        print(f"开始处理视频 - FPS: {fps:.2f}")
        
        with tqdm(total=total_frames, desc="处理进度") as pbar:
            try:
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    frame_count += 1
                    pbar.update(1)
                    
                    # 每100帧更新一次GUI进度显示
                    if frame_count % 100 == 0 and callback:
                        progress = int((frame_count / total_frames) * 100)
                        progress_bar = '=' * (progress // 2) + '>' + ' ' * (50 - progress // 2)
                        callback(f"\r处理进度: [{progress_bar}] {progress}%")
                    
                    # 每秒处理10帧
                    if frame_count % int(fps/10) != 0:
                        continue
                        
                    # 获取字幕区域
                    height = frame.shape[0]
                    width = frame.shape[1]
                    bottom_margin = int(height * bottom_ratio)
                    top_margin = int(height * top_ratio)
                    subtitle_region = frame[bottom_margin:top_margin, :]
                    
                    try:
                        # OCR识别
                        result = self.ocr.ocr(subtitle_region, cls=True)
                        
                        if result:
                            text_items = []
                            for line in result:
                                for item in line:
                                    if item[1][1] > 0.9:  # 置信度阈值
                                        text = item[1][0].strip()
                                        if len(text) >= 2:  # 最小长度限制
                                            text_items.append(text)
                            
                            text = " ".join(text_items)
                            
                            if text.strip() and len(text) <= 50:  # 最大长度限制
                                empty_frames = 0
                                current_time = frame_count/fps
                                
                                if text != last_text:
                                    if start_time is not None:
                                        duration = current_time - start_time
                                        
                                        if duration >= MIN_DURATION:
                                            if duration > MAX_DURATION:
                                                end_time = start_time + MAX_DURATION
                                            else:
                                                end_time = current_time
                                                
                                            start_str = time.strftime('%H:%M:%S,', time.gmtime(start_time)) + f'{int((start_time % 1) * 1000):03d}'
                                            end_str = time.strftime('%H:%M:%S,', time.gmtime(end_time)) + f'{int((end_time % 1) * 1000):03d}'
                                            
                                            subtitle_entry = f"{subtitle_index}\n{start_str} --> {end_str}\n{last_text}\n"
                                            subtitles.append(subtitle_entry)
                                            subtitle_index += 1
                                    
                                    start_time = current_time
                                    last_text = text
                            else:
                                empty_frames += 1
                                if empty_frames >= EMPTY_FRAMES_THRESHOLD and start_time is not None:
                                    current_time = frame_count/fps
                                    duration = current_time - start_time
                                    
                                    if duration >= MIN_DURATION:
                                        start_str = time.strftime('%H:%M:%S,', time.gmtime(start_time)) + f'{int((start_time % 1) * 1000):03d}'
                                        end_str = time.strftime('%H:%M:%S,', time.gmtime(current_time)) + f'{int((current_time % 1) * 1000):03d}'
                                        subtitle_entry = f"{subtitle_index}\n{start_str} --> {end_str}\n{last_text}\n"
                                        subtitles.append(subtitle_entry)
                                        subtitle_index += 1
                                        
                                    start_time = None
                                    last_text = ""
                                    
                    except Exception as e:
                        continue
            
            except Exception as e:
                print(f"\n处理视频时出错: {str(e)}")
            finally:
                cap.release()
        
        # 处理最后一帧字幕
        if start_time is not None and last_text:
            end_time = frame_count/fps
            start_str = time.strftime('%H:%M:%S,', time.gmtime(start_time)) + f'{int((start_time % 1) * 1000):03d}'
            end_str = time.strftime('%H:%M:%S,', time.gmtime(end_time)) + f'{int((end_time % 1) * 1000):03d}'
            subtitle_entry = f"{subtitle_index}\n{start_str} --> {end_str}\n{last_text}\n"
            subtitles.append(subtitle_entry)
        
        # 保存字幕文件
        if subtitles:
            try:
                # 获取视频所在的目录
                video_dir = os.path.dirname(video_path)
                if not video_dir:
                    video_dir = os.getcwd()
                    
                # 在视频所在目录创建output文件夹
                output_dir = os.path.join(video_dir, 'output')
                os.makedirs(output_dir, exist_ok=True)
                
                # 构建保存路径
                save_path = os.path.join(output_dir, output_file)
                
                # 保存文件
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(subtitles))
                print(f"\n字幕提取完成，共提取 {len(subtitles)} 条字幕")
                print(f"已保存到: {save_path}")
                
            except Exception as e:
                print(f"\n保存字幕文件时出错: {str(e)}")
        else:
            print("\n未能提取到任何字幕")