from io import BytesIO

from fastapi import UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image


async def compress_image(file: UploadFile):

    image = Image.open(file.file)

    image.thumbnail((1920, 1920))

    output = BytesIO()

    image.save(
        output,
        format="WEBP",
        quality=80,
        optimize=True,
    )

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="image/webp",
        headers={"Content-Disposition": 'attachment; filename="compressed.webp"'},
    )
