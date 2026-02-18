"""
Image compression for book uploads (e.g. large iPhone photos).
"""
import io
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile


# Target: keep images under this size and dimension for fast loading
MAX_DIMENSION = 1200  # max width or height in pixels
JPEG_QUALITY = 82
MAX_OUTPUT_BYTES = 800 * 1024  # 800 KB target; reduce quality if still over


def compress_image(uploaded_file, max_dimension=MAX_DIMENSION, quality=JPEG_QUALITY, max_bytes=MAX_OUTPUT_BYTES):
    """
    Compress an uploaded image (e.g. from iPhone) to reduce file size.
    Resizes so the longest side is at most max_dimension, then saves as JPEG with given quality.
    Returns an InMemoryUploadedFile suitable for Django ImageField (name will be .jpg).
    """
    if not uploaded_file or not uploaded_file.name:
        return uploaded_file

    try:
        img = Image.open(uploaded_file).copy()
    except Exception:
        return uploaded_file

    # Handle EXIF orientation so the image is not rotated wrongly
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # Convert to RGB if necessary (for JPEG)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Resize if larger than max_dimension
    w, h = img.size
    if w > max_dimension or h > max_dimension:
        if w >= h:
            new_w = max_dimension
            new_h = int(h * (max_dimension / w))
        else:
            new_h = max_dimension
            new_w = int(w * (max_dimension / h))
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS
        img = img.resize((new_w, new_h), resample)

    # Save to bytes with target quality; if still too big, reduce quality
    out = io.BytesIO()
    q = quality
    img.save(out, format='JPEG', quality=q, optimize=True)
    while out.tell() > max_bytes and q > 40:
        out.seek(0)
        out.truncate()
        q -= 10
        img.save(out, format='JPEG', quality=q, optimize=True)

    out.seek(0)
    # Preserve original name base but force .jpg for compressed output
    base_name = uploaded_file.name.rsplit('.', 1)[0] if '.' in uploaded_file.name else 'image'
    safe_name = f"{base_name}.jpg"
    return InMemoryUploadedFile(
        out,
        'ImageField',
        safe_name,
        'image/jpeg',
        out.getbuffer().nbytes,
        None,
    )
