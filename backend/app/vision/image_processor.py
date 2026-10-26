import os
import io
import time
import base64
import uuid
import glob
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
from .vision_schemas import ImageFormat, CaptureMetadata, CaptureTarget, WindowInfo, MonitorInfo

TEMP_CAPTURES_DIR = Path(__file__).resolve().parent.parent.parent / "temp_captures"

class ImageProcessor:
    """
    Handles image processing, smart downscaling, format conversion,
    base64 encoding, and ephemeral temporary storage management.
    """

    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = temp_dir or TEMP_CAPTURES_DIR
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def resize_for_efficiency(self, image: Image.Image, max_dimension: int = 1280) -> Tuple[Image.Image, Tuple[int, int]]:
        """
        Resizes an image down if its width or height exceeds max_dimension,
        preserving aspect ratio. Returns (resized_image, original_dimensions).
        """
        orig_w, orig_h = image.size
        if orig_w <= max_dimension and orig_h <= max_dimension:
            return image.copy(), (orig_w, orig_h)

        if orig_w > orig_h:
            new_w = max_dimension
            new_h = int((orig_h / orig_w) * max_dimension)
        else:
            new_h = max_dimension
            new_w = int((orig_w / orig_h) * max_dimension)

        # Ensure minimum 1px dimension
        new_w = max(1, new_w)
        new_h = max(1, new_h)

        resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        return resized, (orig_w, orig_h)

    def image_to_base64(self, image: Image.Image, format: ImageFormat = ImageFormat.PNG, quality: int = 85) -> str:
        """
        Encodes a PIL Image into a base64 data URL string.
        """
        buf = io.BytesIO()
        fmt_str = "JPEG" if format == ImageFormat.JPEG else "PNG"
        
        # JPEG requires RGB mode
        if fmt_str == "JPEG" and image.mode in ("RGBA", "P"):
            rgb_img = image.convert("RGB")
            rgb_img.save(buf, format="JPEG", quality=quality, optimize=True)
        else:
            image.save(buf, format=fmt_str, optimize=True)
            
        b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
        mime = "image/jpeg" if format == ImageFormat.JPEG else "image/png"
        return f"data:{mime};base64,{b64_data}"

    def base64_to_image(self, b64_str: str) -> Image.Image:
        """
        Decodes a base64 string or data URL into a PIL Image.
        """
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        data = base64.b64decode(b64_str)
        return Image.open(io.BytesIO(data))

    def save_ephemeral(
        self,
        image: Image.Image,
        target: CaptureTarget = CaptureTarget.PRIMARY,
        format: ImageFormat = ImageFormat.PNG,
        quality: int = 85,
        max_dimension: int = 1280,
        window_info: Optional[WindowInfo] = None,
        monitor_info: Optional[MonitorInfo] = None
    ) -> Tuple[CaptureMetadata, Image.Image]:
        """
        Processes and saves an ephemeral screenshot to disk, returning its metadata
        and the processed PIL Image.
        """
        capture_id = str(uuid.uuid4())
        ext = "jpg" if format == ImageFormat.JPEG else "png"
        filename = f"capture_{capture_id[:8]}_{int(time.time())}.{ext}"
        file_path = self.temp_dir / filename

        resized_img, (orig_w, orig_h) = self.resize_for_efficiency(image, max_dimension=max_dimension)
        
        fmt_str = "JPEG" if format == ImageFormat.JPEG else "PNG"
        if fmt_str == "JPEG" and resized_img.mode in ("RGBA", "P"):
            save_img = resized_img.convert("RGB")
            save_img.save(file_path, format="JPEG", quality=quality, optimize=True)
        else:
            resized_img.save(file_path, format=fmt_str, optimize=True)

        file_size = os.path.getsize(file_path)
        base64_preview = self.image_to_base64(resized_img, format=format, quality=quality)

        metadata = CaptureMetadata(
            capture_id=capture_id,
            target=target,
            format=format,
            width=resized_img.width,
            height=resized_img.height,
            original_width=orig_w,
            original_height=orig_h,
            file_path=str(file_path),
            file_size_bytes=file_size,
            window_info=window_info,
            monitor_info=monitor_info,
            base64_preview=base64_preview
        )

        return metadata, resized_img

    def get_temporary_captures_count(self) -> int:
        """
        Returns number of files in the temporary captures directory.
        """
        if not self.temp_dir.exists():
            return 0
        return len(glob.glob(str(self.temp_dir / "capture_*.*")))

    def clear_temporary_files(self) -> int:
        """
        Deletes all temporary capture files in the directory.
        Returns the count of deleted files.
        """
        if not self.temp_dir.exists():
            return 0

        count = 0
        for p in self.temp_dir.glob("capture_*.*"):
            try:
                p.unlink()
                count += 1
            except Exception:
                pass
        return count
