import cv2
import numpy as np
from paddleocr import PaddleOCR
import time
import os
import logging
import subprocess

# 在文件开头添加颜色常量
PURPLE = '\033[95m'  # 紫色（亮紫色）
RESET = '\033[0m'  # 重置颜色

class SubtitleExtractor:
    def __init__(self):
        # 配置日志级别
        logging.basicConfig(level=logging.WARNING)
        paddleocr_logger = logging.getLogger("paddleocr")
        paddleocr_logger.setLevel(logging.WARNING)
        
        try:
            # 检查项目本地模型路径
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            models_dir = os.path.join(project_root, 'models')
            
            # 检查模型文件
            det_path = os.path.join(models_dir, 'det')
            rec_path = os.path.join(models_dir, 'rec')
            cls_path = os.path.join(models_dir, 'cls')
            
            print("\n=== 检查本地模型文件 ===")
            print(f"模型根目录: {models_dir}")
            
            # 检查每个模型文件
            model_files = ['inference.pdiparams', 'inference.pdiparams.info', 'inference.pdmodel']
            models = {
                '检测模型(det)': det_path,
                '识别模型(rec)': rec_path,
                '方向分类模型(cls)': cls_path
            }
            
            models_status = {}
            for model_name, model_path in models.items():
                if not os.path.exists(model_path):
                    print(f"{model_name}: 目录不存在")
                    models_status[model_name] = False
                    continue
                
                missing_files = []
                for file in model_files:
                    file_path = os.path.join(model_path, file)
                    if not os.path.exists(file_path):
                        missing_files.append(file)
                    elif os.path.getsize(file_path) == 0:
                        missing_files.append(f"{file}(空文件)")
                
                if missing_files:
                    print(f"{model_name}: 缺少文件 {', '.join(missing_files)}")
                    models_status[model_name] = False
                else:
                    print(f"{model_name}: 完整")
                    models_status[model_name] = True
            
            if all(models_status.values()):
                print("\n所有模型文件完整，使用本地模型")
                self.ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang='ch',
                    show_log=True,
                    enable_mkldnn=True,
                    det_model_dir=det_path,
                    rec_model_dir=rec_path,
                    cls_model_dir=cls_path
                )
            else:
                print("\n使用默认配置（将使用已下载的模型）")
                self.ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang='ch',
                    show_log=True
                )
            
            print("OCR引擎初始化成功")
            
        except Exception as e:
            print(f"初始化失败: {str(e)}")
            print("使用基础配置...")
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang='ch'
            )
    
    def extract_subtitles(self, video_path, output_path, lang, subtitle_area, callback=None):
        """从视频中提取字幕并保存到文本文件"""
        print(f"开始处理视频: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"无法打开视频文件: {video_path}")
            return
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"视频信息 - FPS: {fps}, 总帧数: {total_frames}")
        
        current_text = ""
        start_time = 0
        subtitle_index = 1
        subtitles = []
        frame_count = 0
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_count += 1
                
                # 更新进度显示
                if frame_count % 10 == 0:  # 每10帧更新一次
                    progress = frame_count / total_frames
                    if callback:
                        callback(progress)
                    print(f"{PURPLE}处理进度: {progress*100:.0f}%{RESET}")  # 紫色显示进度
                
                # 每3帧处理一次OCR，提高性能
                if frame_count % 3 != 0:
                    continue
                    
                current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                current_time = current_frame / fps
                
                # 1. 提取字幕区域
                if subtitle_area:
                    height = frame.shape[0]
                    y1 = int(height * subtitle_area[0])  # bottom ratio
                    y2 = int(height * subtitle_area[1])  # top ratio
                    subtitle_region = frame[y1:y2, :]
                    print(f"字幕区域: {y1}-{y2}")
                else:
                    subtitle_region = frame
                
                # 2. 图像预处理
                gray = cv2.cvtColor(subtitle_region, cv2.COLOR_BGR2GRAY)
                # 使用自适应阈值
                binary = cv2.adaptiveThreshold(
                    gray,
                    255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY,
                    11,
                    2
                )
                # 添加一些图像增强
                kernel = np.ones((1, 1), np.uint8)
                binary = cv2.dilate(binary, kernel, iterations=1)
                binary = cv2.erode(binary, kernel, iterations=1)
                
                try:
                    # 3. OCR识别
                    result = self.ocr.ocr(binary, cls=True)
                    
                    # 4. 提取文本
                    text = ""
                    if result:
                        for line in result:
                            try:
                                # 处理单个文本框的情况
                                if isinstance(line, list) and len(line) >= 2:
                                    # 直接获取文本和置信度
                                    text_info = line[1]
                                    if isinstance(text_info, tuple):
                                        text_content, confidence = text_info
                                        if confidence > 0.5:
                                            text += text_content + " "
                                            print(f"识别文本: {text_content} (置信度: {confidence})")
                                # 处理多个文本框的情况
                                elif isinstance(line, list):
                                    for box_text in line:
                                        if isinstance(box_text, list) and len(box_text) >= 2:
                                            text_info = box_text[1]
                                            if isinstance(text_info, tuple):
                                                text_content, confidence = text_info
                                                if confidence > 0.5:
                                                    text += text_content + " "
                                                    print(f"识别文本: {text_content} (置信度: {confidence})")
                            except Exception as e:
                                print(f"处理OCR结果出错: {str(e)}, line={line}")
                                continue
                        
                        text = text.strip()
                        if text:
                            print(f"最终文本: {text}")
                            
                            # 5. 处理字幕
                            if text != current_text:
                                if current_text:
                                    # 添加当前字幕
                                    end_time = current_time - 0.1
                                    subtitle = self._format_subtitle(
                                        subtitle_index,
                                        start_time,
                                        end_time,
                                        current_text
                                    )
                                    subtitles.append(subtitle)
                                    subtitle_index += 1
                                    print(f"添加字幕: {subtitle}")
                                
                                # 开始新字幕
                                current_text = text
                                start_time = current_time
                    
                except Exception as e:
                    print(f"OCR处理失败: {str(e)}, result={result}")
                    continue
                    
        except Exception as e:
            print(f"视频处理失败: {str(e)}")
        finally:
            # 处理后一条字幕
            if current_text:
                subtitle = self._format_subtitle(
                    subtitle_index,
                    start_time,
                    current_time,
                    current_text
                )
                subtitles.append(subtitle)
            
            # 保存字幕文件
            if subtitles:
                print(f"提取到 {len(subtitles)} 条字幕，正在保存...")
                # 确保输出目录存在
                output_dir = os.path.dirname(output_path)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                
                try:
                    print(f"准备保存字幕到: {output_path}")
                    with open(output_path, 'w', encoding='utf-8') as f:
                        content = '\n\n'.join(subtitles)
                        f.write(content)
                        print(f"写入内容长度: {len(content)} 字节")
                    
                    if os.path.exists(output_path):
                        size = os.path.getsize(output_path)
                        print(f"文件创建成功，大小: {size} 字节")
                        if size == 0:
                            print("告：文件大小为0！")
                            print("字幕内容:", subtitles)  # 打印字幕内容以便调试
                except Exception as e:
                    print(f"存字幕文件时出错: {str(e)}")
                    print("尝试保存的字幕内容:", subtitles)  # 打印字幕内容以便调试
            else:
                print("未提取到任何字幕！")
            
            cap.release()
            
            if callback:
                callback(1.0)
    
    def _format_subtitle(self, index, start_time, end_time, text):
        """格式化为SRT格式字幕"""
        start_str = time.strftime('%H:%M:%S,', time.gmtime(start_time)) + f'{int((start_time % 1) * 1000):03d}'
        end_str = time.strftime('%H:%M:%S,', time.gmtime(end_time)) + f'{int((end_time % 1) * 1000):03d}'
        return f"{index}\n{start_str} --> {end_str}\n{text}\n"