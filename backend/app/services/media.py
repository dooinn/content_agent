def image_type(data: bytes) -> tuple[str, str] | None:
    """(extension, media type) for PNG, JPEG, and WebP bytes; None for anything else."""
    if data.startswith(b"\x89PNG"):
        return "png", "image/png"
    if data.startswith(b"\xff\xd8"):
        return "jpg", "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None
