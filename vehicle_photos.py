"""Vehicle photo validation and local background removal; photos persist in the fleet database."""
import base64
import binascii
from functools import lru_cache
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 24_000_000
MAX_PNG_BYTES = 2 * 1024 * 1024
PNG_PREFIX = "data:image/png;base64,"


def read_photo(raw):
    if not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Envie uma foto JPG, PNG ou WEBP de até 10 MB.")
    try:
        with Image.open(BytesIO(raw)) as opened:
            if opened.format not in ("JPEG", "PNG", "WEBP"):
                raise ValueError("Formato inválido. Envie JPG, PNG ou WEBP.")
            if opened.width * opened.height > MAX_PIXELS:
                raise ValueError("A foto é muito grande. Envie uma imagem de até 24 megapixels.")
            photo = ImageOps.exif_transpose(opened).convert("RGB")
            photo.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            return photo
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("Não foi possível abrir a foto. Envie outra imagem JPG, PNG ou WEBP.") from error


@lru_cache(maxsize=1)
def removal_session():
    import os
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    from rembg import new_session
    return new_session("u2netp", providers=["CPUExecutionProvider"])


def remove_background(raw):
    photo = read_photo(raw)
    try:
        from rembg import remove
        cutout = remove(photo, session=removal_session()).convert("RGBA")
    except Exception as error:
        raise ValueError("Não foi possível remover o fundo agora. Tente novamente; a foto anterior será mantida.") from error
    alpha = cutout.getchannel("A")
    if alpha.getextrema()[0] == 255 or alpha.getbbox() is None:
        raise ValueError("Não foi possível separar o veículo do fundo. Envie outra foto com o veículo em destaque.")
    box = alpha.getbbox()
    cutout = cutout.crop(box)
    cutout.thumbnail((1100, 850), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (cutout.width + 40, cutout.height + 40), (0, 0, 0, 0))
    canvas.paste(cutout, (20, 20))
    output = BytesIO()
    # Build a new PNG to discard EXIF and other metadata from the original.
    canvas.save(output, format="PNG", optimize=True)
    png = output.getvalue()
    if len(png) > MAX_PNG_BYTES:
        raise ValueError("A foto processada ficou muito grande. Envie uma foto menor.")
    return PNG_PREFIX + base64.b64encode(png).decode("ascii")


def photo_bytes(value):
    if not isinstance(value, str) or not value.startswith(PNG_PREFIX):
        return None
    encoded = value[len(PNG_PREFIX):]
    if len(encoded) > ((MAX_PNG_BYTES + 2) // 3) * 4:
        return None
    try:
        png = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        return None
    return png if png.startswith(b"\x89PNG\r\n\x1a\n") else None
