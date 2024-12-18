from fastapi import FastAPI
from pydantic import BaseModel
import aiohttp
import os
import uuid
from subtitle_extractor import SubtitleExtractor

app = FastAPI()

class VideoURL(BaseModel):
    url: str

@app.post("/download")
async def download_video(video: VideoURL):
    try:
        # 创建下载目录
        download_dir = "downloads"
        os.makedirs(download_dir, exist_ok=True)
        
        # 生成唯一文件名
        filename = f"{uuid.uuid4()}.mp4"
        filepath = os.path.join(download_dir, filename)
        
        # 下载视频
        async with aiohttp.ClientSession() as session:
            async with session.get(video.url) as response:
                with open(filepath, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
        
        return {"status": "success", "server_path": filepath}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/process")
async def process_videos(request: dict):
    video_paths = request["paths"]
    try:
        # 处理视频并提取字幕
        extractor = SubtitleExtractor()
        results = []
        
        for path in video_paths:
            output_path = f"{path}_subtitles.srt"
            extractor.extract_subtitles(
                path,
                output_path,
                'ch',
                subtitle_area=None  # 可以从请求中获取
            )
            results.append(output_path)
            
        return {"status": "success", "subtitle_paths": results}
    except Exception as e:
        return {"status": "error", "message": str(e)} 