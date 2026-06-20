import base64
from PIL import Image
from io import BytesIO
import os

def compress_image_to_base64(image_path: str, max_size=(1024, 1024), quality=85) -> str:
    """Compress image using PIL resize + JPEG, then base64."""
    with Image.open(image_path) as img:
        # Resize if larger than max_size (maintain aspect ratio)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB for JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Compress to BytesIO
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        buffer.seek(0)
        
        # Base64 encode
        img_b64 = base64.b64encode(buffer.read()).decode()
        
        orig_size = os.path.getsize(image_path)
        compressed_size = len(img_b64) * 3/4  # b64 overhead
        print(f"Compressed: {orig_size/1024:.1f}KB → {compressed_size/1024:.1f}KB ({compressed_size/orig_size*100:.1f}%)")
        
        return img_b64

# Test
if __name__ == "__main__":
    b64 = compress_image_to_base64("PHOTO.jpg")
    print("✅ Compressed base64 ready (first 100 chars):", b64[:100])

