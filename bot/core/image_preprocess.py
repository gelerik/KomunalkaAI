from __future__ import annotations

import io

from PIL import Image, ImageEnhance, ImageOps


def build_preprocessed_rotations(image_bytes: bytes) -> list[tuple[int, bytes]]:
    """
    Возвращает 4 предобработанных варианта изображения: 0/90/180/270 градусов.

    Для каждого варианта выполняем:
    1) поворот;
    2) кроп по содержимому (обрезаем большие пустые поля);
    3) повышение контраста для более читаемого OCR.
    """
    with Image.open(io.BytesIO(image_bytes)) as source:
        base_image = source.convert("RGB")

    prepared: list[tuple[int, bytes]] = []
    for angle in (0, 90, 180, 270):
        rotated = base_image.rotate(angle, expand=True)
        cropped = _crop_to_content(rotated)
        enhanced = _enhance_contrast(cropped)
        prepared.append((angle, _to_jpeg_bytes(enhanced)))

    return prepared


def _crop_to_content(image: Image.Image) -> Image.Image:
    # Переводим в grayscale, повышаем контраст автоматически и ищем "не белые" пиксели.
    gray = ImageOps.autocontrast(image.convert("L"))
    # Инвертируем: тёмный текст станет светлым, так getbbox() проще находит содержимое.
    inverted = ImageOps.invert(gray)
    bbox = inverted.getbbox()
    if not bbox:
        return image

    left, top, right, bottom = bbox
    # Небольшой запас вокруг контента, чтобы не обрезать крайние символы.
    pad = 20
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(image.width, right + pad)
    bottom = min(image.height, bottom + pad)
    return image.crop((left, top, right, bottom))


def _enhance_contrast(image: Image.Image) -> Image.Image:
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(1.8)


def _to_jpeg_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=95, optimize=True)
    return buffer.getvalue()

