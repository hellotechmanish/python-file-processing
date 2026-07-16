import os
import shutil
import tempfile
import ffmpeg
from fastapi import UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTasks


def resolve_ffmpeg_binary() -> str:
    candidates = []

    env_path = os.getenv("FFMPEG_BINARY")
    if env_path:
        candidates.append(env_path)

    for binary_name in ("ffmpeg", "ffmpeg.exe"):
        resolved = shutil.which(binary_name)
        if resolved:
            candidates.append(resolved)

    candidates.append(
        r"C:\ffmpeg\ffmpeg-2026-07-06-git-c6498178bb-full_build\bin\ffmpeg.exe"
    )

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate

    raise RuntimeError(
        "FFmpeg was not found. Install FFmpeg or set the FFMPEG_BINARY environment variable."
    )


def cleanup_temp_files(*file_paths: str):
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"Error during file cleanup: {e}")


async def compress_video(file: UploadFile):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as input_file:
        input_file.write(await file.read())
        input_path = input_file.name

    output_path = input_path.replace(".mp4", "_compressed.mp4")

    FFFMPEG_BINARY = resolve_ffmpeg_binary()

    try:
        (
            ffmpeg.input(input_path).output(
                output_path,
                vcodec="libx264",
                acodec="aac",
                crf=28,
                preset="medium",
            )
            # Pass the direct path here to bypass Windows environment lookup bugs
            .run(cmd=FFFMPEG_BINARY, overwrite_output=True)
        )

        background_tasks = BackgroundTasks()
        background_tasks.add_task(cleanup_temp_files, input_path, output_path)

        return FileResponse(
            path=output_path,
            media_type="video/mp4",
            filename=f"compressed_{file.filename}",
            background=background_tasks,
        )

    except Exception as e:
        cleanup_temp_files(input_path, output_path)
        raise e


async def convert_video(file: UploadFile, target_format: str):
    FFMPEG_BINARY = resolve_ffmpeg_binary()
    target_format = target_format.lower().strip()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as input_file:
        input_file.write(await file.read())
        input_path = input_file.name

    output_path = input_path.replace(".mp4", f"_converted.{target_format}")

    try:
        output_args = {"preset": "ultrafast"}

        if target_format == "webm":
            output_args["vcodec"] = "libvpx-vp9"
            output_args["acodec"] = "libopus"
        elif target_format == "mp4":
            output_args["vcodec"] = "libx264"
            output_args["acodec"] = "aac"

        (
            ffmpeg.input(input_path)
            .output(output_path, **output_args)
            .run(cmd=FFMPEG_BINARY, overwrite_output=True)
        )

        background_tasks = BackgroundTasks()
        background_tasks.add_task(cleanup_temp_files, input_path, output_path)

        media_types = {
            "mp4": "video/mp4",
            "webm": "video/webm",
            "avi": "video/x-msvideo",
            "mkv": "video/x-matroska",
        }
        selected_media_type = media_types.get(target_format, "application/octet-stream")

        return FileResponse(
            path=output_path,
            media_type=selected_media_type,
            filename=f"converted_{os.path.splitext(file.filename)[0]}.{target_format}",
            background=background_tasks,
        )

    except Exception as e:
        cleanup_temp_files(input_path, output_path)
        raise e


async def extract_audio(file: UploadFile):
    FFMPEG_BINARY = resolve_ffmpeg_binary()

    temp_dir = os.path.join(os.getcwd(), "temp_audio_workspace")
    os.makedirs(temp_dir, exist_ok=True)

    original_ext = os.path.splitext(file.filename)[1] or ".mp4"
    unique_id = f"extract_{os.getpid()}"

    input_path = os.path.join(temp_dir, f"{unique_id}{original_ext}")
    output_path = os.path.join(temp_dir, f"{unique_id}_extracted.mp3")

    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise RuntimeError(f"Failed to write uploaded file to server storage: {str(e)}")

    try:
        process = (
            ffmpeg.input(input_path)
            .output(
                output_path,
                vn=None,
                acodec="libmp3lame",
                audio_bitrate="192k",
                map="0:a:0?",
                map_metadata=-1,
            )
            .run_async(
                cmd=FFMPEG_BINARY,
                overwrite_output=True,
                pipe_stdout=True,
                pipe_stderr=True,
            )
        )

        _, stderr = process.communicate()

        if process.returncode != 0:
            error_output = stderr.decode("utf8", errors="ignore")
            lower_error = error_output.lower()

            if (
                "does not contain any stream" in lower_error
                or "audio stream" in lower_error
            ):
                raise RuntimeError(
                    "The uploaded video does not contain an audio stream. Please upload a video with audio."
                )

            raise RuntimeError(
                f"FFmpeg failed to extract audio: {error_output.strip() or 'No details available.'}"
            )

        background_tasks = BackgroundTasks()
        background_tasks.add_task(cleanup_temp_files, input_path, output_path)

        return FileResponse(
            path=output_path,
            media_type="audio/mpeg",
            filename=f"{os.path.splitext(file.filename)[0]}.mp3",
            background=background_tasks,
        )

    except Exception as e:
        cleanup_temp_files(input_path, output_path)
        raise e
