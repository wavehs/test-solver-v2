import mss
import mss.tools
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

def capture_screen():
    """
    Captures the screen and returns the image as bytes (PNG).
    Resizes the image to max 1024px width for speed if necessary.
    """
    with mss.mss() as sct:
        # Capture the first monitor (all monitors combined usually, or specifically monitor 1)
        monitor = sct.monitors[1] # Primary monitor
        logger.debug(f"Capturing monitor: {monitor}")
        try:
            sct_img = sct.grab(monitor)
        except mss.exception.ScreenShotError as e:
            logger.error(f"Screen capture failed: {e}. On macOS, ensure Screen Recording permission is granted.")
            raise e

        # Convert to PIL Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        original_size = img.size

        # Resize if too large to speed up upload/processing
        max_width = 1024
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            logger.debug(f"Resized image from {original_size} to {img.size}")
        else:
            logger.debug(f"Image size {original_size} is within limits.")

        # Save to BytesIO
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        logger.debug(f"Image captured. Bytes: {img_byte_arr.getbuffer().nbytes}")
        return img_byte_arr
