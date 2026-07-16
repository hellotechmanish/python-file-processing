import os, io, asyncio
import app.services.video as video

ffmpeg_bin = r'C:\ffmpeg\ffmpeg-2026-07-06-git-c6498178bb-full_build\bin\ffmpeg.exe'
input_path = os.path.join(os.getcwd(), 'test_input.mp4')
os.system(f'"{ffmpeg_bin}" -y -f lavfi -i color=c=blue:s=160x120:d=1 -t 1 -pix_fmt yuv420p "{input_path}" >nul 2>&1')
with open(input_path, 'rb') as f:
    data = f.read()
class DummyUpload:
    def __init__(self, data, filename):
        self.filename = filename
        self.file = io.BytesIO(data)
try:
    result = asyncio.run(video.extract_audio(DummyUpload(data, 'test_input.mp4')))
    print('SUCCESS', result)
except Exception as e:
    print('ERROR', type(e).__name__, e)
