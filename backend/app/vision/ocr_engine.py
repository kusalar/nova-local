import io
import time
import asyncio
import logging
from typing import List, Optional, Tuple
from PIL import Image

from .vision_schemas import OcrResult, OcrLine, OcrWord, OcrRegion
from .privacy_filter import PrivacyFilter

logger = logging.getLogger("nova.vision.ocr")

class OcrEngine:
    """
    Lightweight, CPU-compatible local OCR engine.
    Uses native Windows.Media.Ocr where available with lazy initialization,
    and provides structured extraction and fallback support.
    """

    def __init__(self, auto_redact: bool = True):
        self.auto_redact = auto_redact
        self.engine_name = "windows_media_ocr"
        self._winrt_checked = False
        self._winrt_available = False

    def is_available(self) -> bool:
        """Checks whether native Windows OCR can be loaded."""
        if not self._winrt_checked:
            try:
                import winrt.windows.foundation
                import winrt.windows.media.ocr
                self._winrt_available = True
                self.engine_name = "windows_media_ocr"
            except Exception as e:
                logger.info(f"Native Windows OCR unavailable: {e}")
                self._winrt_available = False
                self.engine_name = "fallback_ocr"
            self._winrt_checked = True
        return self._winrt_available

    async def extract_text(self, image: Image.Image, auto_redact: Optional[bool] = None) -> OcrResult:
        """
        Extracts structured text from a PIL Image.
        """
        start_time = time.perf_counter()
        redact = self.auto_redact if auto_redact is None else auto_redact

        if self.is_available():
            try:
                def _worker():
                    return asyncio.run(self._run_winrt_ocr(image))
                ocr_res = await asyncio.to_thread(_worker)
            except Exception as e:
                logger.warning(f"WinRT OCR extraction failed: {e}. Engaging fallback.")
                ocr_res = self._run_fallback_ocr(image)
        else:
            ocr_res = self._run_fallback_ocr(image)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        ocr_res.duration_ms = round(duration_ms, 2)

        if redact:
            ocr_res = PrivacyFilter.sanitize_ocr_result(ocr_res)

        return ocr_res

    async def _run_winrt_ocr(self, image: Image.Image) -> OcrResult:
        """
        Executes native Windows.Media.Ocr with lazy module importing.
        """
        import winrt.windows.foundation
        import winrt.windows.foundation.collections
        import winrt.windows.graphics.imaging as imaging
        import winrt.windows.media.ocr as winrt_ocr
        import winrt.windows.storage.streams as streams

        # Convert PIL Image to PNG bytes
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        data = buf.getvalue()

        # Write to InMemoryRandomAccessStream
        stream = streams.InMemoryRandomAccessStream()
        writer = streams.DataWriter(stream.get_output_stream_at(0))
        writer.write_bytes(data)
        await writer.store_async()
        await writer.flush_async()
        stream.seek(0)

        # Decode software bitmap
        decoder = await imaging.BitmapDecoder.create_async(stream)
        software_bitmap = await decoder.get_software_bitmap_async()

        # Create OCR engine from user's current profile language
        ocr_engine = winrt_ocr.OcrEngine.try_create_from_user_profile_languages()
        if not ocr_engine:
            lang = winrt_ocr.OcrEngine.available_recognizer_languages[0]
            ocr_engine = winrt_ocr.OcrEngine.try_create_from_language(lang)

        ocr_result = await ocr_engine.recognize_async(software_bitmap)

        lines: List[OcrLine] = []
        regions: List[OcrRegion] = []
        full_lines_text: List[str] = []
        total_words = 0

        current_region_lines: List[OcrLine] = []
        last_y = None

        for line in ocr_result.lines:
            line_words: List[OcrWord] = []
            min_x, min_y = 999999, 999999
            max_x, max_y = 0, 0

            for word in line.words:
                r = word.bounding_rect
                wx, wy, ww, wh = int(r.x), int(r.y), int(r.width), int(r.height)
                min_x = min(min_x, wx)
                min_y = min(min_y, wy)
                max_x = max(max_x, wx + ww)
                max_y = max(max_y, wy + wh)

                line_words.append(OcrWord(
                    text=word.text,
                    confidence=1.0,
                    x=wx,
                    y=wy,
                    width=ww,
                    height=wh
                ))
                total_words += 1

            if min_x == 999999:
                min_x, min_y = 0, 0
                max_x, max_y = 0, 0

            ocr_line = OcrLine(
                text=line.text,
                confidence=1.0,
                words=line_words,
                x=min_x,
                y=min_y,
                width=max(0, max_x - min_x),
                height=max(0, max_y - min_y)
            )
            lines.append(ocr_line)
            full_lines_text.append(line.text)

            # Heuristic paragraph / region segmentation based on vertical line spacing
            if last_y is not None and abs(ocr_line.y - last_y) > (ocr_line.height * 2.5):
                if current_region_lines:
                    reg_text = "\n".join(l.text for l in current_region_lines)
                    rx = min(l.x for l in current_region_lines)
                    ry = min(l.y for l in current_region_lines)
                    rw = max(l.x + l.width for l in current_region_lines) - rx
                    rh = max(l.y + l.height for l in current_region_lines) - ry
                    regions.append(OcrRegion(
                        region_id=len(regions) + 1,
                        lines=list(current_region_lines),
                        text=reg_text,
                        x=rx,
                        y=ry,
                        width=rw,
                        height=rh
                    ))
                    current_region_lines = []

            current_region_lines.append(ocr_line)
            last_y = ocr_line.y

        # Flush final region
        if current_region_lines:
            reg_text = "\n".join(l.text for l in current_region_lines)
            rx = min(l.x for l in current_region_lines)
            ry = min(l.y for l in current_region_lines)
            rw = max(l.x + l.width for l in current_region_lines) - rx
            rh = max(l.y + l.height for l in current_region_lines) - ry
            regions.append(OcrRegion(
                region_id=len(regions) + 1,
                lines=list(current_region_lines),
                text=reg_text,
                x=rx,
                y=ry,
                width=rw,
                height=rh
            ))

        full_text = "\n".join(full_lines_text)

        return OcrResult(
            total_lines=len(lines),
            total_words=total_words,
            full_text=full_text,
            structured_text=full_text,
            lines=lines,
            regions=regions,
            confidence=1.0 if lines else 0.0,
            redacted_count=0,
            duration_ms=0.0
        )

    def _run_fallback_ocr(self, image: Image.Image) -> OcrResult:
        """
        Graceful fallback when native Windows OCR is not available.
        Extracts metadata and basic information without failing.
        """
        return OcrResult(
            total_lines=0,
            total_words=0,
            full_text="[OCR Fallback: Image processed. Native OCR engine not active]",
            structured_text="[OCR Fallback: Image processed. Native OCR engine not active]",
            lines=[],
            regions=[],
            confidence=0.5,
            redacted_count=0,
            duration_ms=0.0
        )
