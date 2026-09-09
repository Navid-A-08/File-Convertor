"""Image format conversion: png, jpg, jpeg, webp, bmp, gif, tiff, ico."""
from PIL import Image

from .base import BaseConverter, ConversionError, registry

RASTER_FORMATS = {"png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "ico"}

_PIL_SAVE_FORMAT = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "bmp": "BMP",
    "gif": "GIF",
    "tiff": "TIFF",
    "ico": "ICO",
}


class ImageConverter(BaseConverter):
    name = "images"
    format_map = {ext: RASTER_FORMATS - {ext} for ext in RASTER_FORMATS}

    def convert(self, input_path, output_path, target_format, **options):
        target_format = target_format.lower().lstrip(".")
        if target_format not in _PIL_SAVE_FORMAT:
            raise ConversionError(f"Unsupported image target format: '{target_format}'.")

        try:
            with Image.open(input_path) as img:
                pil_format = _PIL_SAVE_FORMAT[target_format]
                save_kwargs = {}

                if pil_format == "JPEG":
                    # JPEG has no alpha channel
                    img = img.convert("RGB")
                    save_kwargs["quality"] = int(options.get("quality", 90))
                elif pil_format == "WEBP":
                    save_kwargs["quality"] = int(options.get("quality", 90))
                elif pil_format == "PNG":
                    save_kwargs["optimize"] = True

                width = options.get("resize_width")
                height = options.get("resize_height")
                if width or height:
                    img = self._resize(img, width, height)

                img.save(output_path, format=pil_format, **save_kwargs)
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError(f"Image conversion failed: {exc}") from exc
        return output_path

    @staticmethod
    def _resize(img: Image.Image, width, height) -> Image.Image:
        orig_w, orig_h = img.size
        if width and not height:
            width = int(width)
            height = round(orig_h * (width / orig_w))
        elif height and not width:
            height = int(height)
            width = round(orig_w * (height / orig_h))
        else:
            width, height = int(width), int(height)
        return img.resize((width, height), Image.LANCZOS)


registry.register(ImageConverter())
