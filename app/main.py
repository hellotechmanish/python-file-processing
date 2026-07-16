from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.services.image import compress_image
from app.services.video import compress_video, extract_audio, convert_video

app = FastAPI()

# Make sure this matches your Next.js dev server port
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Server Running 🚀"}


@app.post("/api/image/compress")
async def compress(file: UploadFile = File(...)):
    return await compress_image(file)


# FIX: Route path changed from /compress/video to /api/video/compress
@app.post("/api/video/compress")
async def video(file: UploadFile = File(...)):
    return await compress_video(file)


@app.post("/api/video/convert")
async def video_convert(
    file: UploadFile = File(...),
    target_format: str = Form(...),  # Receives "mp4", "webm", etc. from frontend
):
    return await convert_video(file, target_format)


@app.post("/api/video/to-audio")
async def video_to_audio(file: UploadFile = File(...)):
    try:
        return await extract_audio(file)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
