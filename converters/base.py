"""Base utilities and registry for the File-Convertor conversion engine.

Every converter module (images, documents, spreadsheets, data, archives, audio)
defines a subclass of ``BaseConverter`` and registers a single instance of it
with the shared ``registry``. The Flask API then looks up the right converter
purely from the source/target file extensions, so new formats can be added
without touching app.py at all.
"""
import os
import uuid
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("file_convertor")


class ConversionError(Exception):
    """Raised whenever a conversion cannot be completed.

    The message is safe to show directly to the end user (no stack traces,
    no internal paths).
    """


class BaseConverter(ABC):
    """Common interface implemented by every format-family converter."""

    #: Human readable name shown in the API/UI, e.g. "images"
    name: str = "base"

    #: Mapping of source extension -> set of target extensions it can produce.
    #: Example: {"png": {"jpg", "webp"}, "jpg": {"png", "webp"}}
    format_map: dict[str, set[str]] = {}

    @abstractmethod
    def convert(self, input_path: str, output_path: str, target_format: str, **options) -> str:
        """Convert the file at input_path into target_format, writing to output_path.

        Returns output_path on success. Raises ConversionError on any
        recoverable failure (bad input, missing system dependency, etc).
        """
        raise NotImplementedError

    def supports(self, source_ext: str, target_ext: str) -> bool:
        source_ext = source_ext.lower().lstrip(".")
        target_ext = target_ext.lower().lstrip(".")
        return target_ext in self.format_map.get(source_ext, set())

    def all_source_formats(self) -> set:
        return set(self.format_map.keys())

    def all_target_formats(self) -> set:
        out = set()
        for targets in self.format_map.values():
            out |= targets
        return out


class ConverterRegistry:
    """Holds every registered converter and answers "who can do X -> Y" lookups."""

    def __init__(self):
        self._converters: list[BaseConverter] = []

    def register(self, converter: BaseConverter) -> BaseConverter:
        self._converters.append(converter)
        logger.info("Registered converter: %s", converter.name)
        return converter

    def find(self, source_ext: str, target_ext: str):
        source_ext = source_ext.lower().lstrip(".")
        target_ext = target_ext.lower().lstrip(".")
        for converter in self._converters:
            if converter.supports(source_ext, target_ext):
                return converter
        return None

    def all(self) -> list:
        return list(self._converters)

    def capability_map(self) -> dict:
        """{converter_name: {source_ext: [target_ext, ...]}} — used by /api/formats."""
        result = {}
        for converter in self._converters:
            result[converter.name] = {
                src: sorted(targets) for src, targets in converter.format_map.items()
            }
        return result


registry = ConverterRegistry()


def unique_filename(original_name: str, new_ext: str) -> str:
    """Build a collision-safe output filename that still resembles the input name."""
    stem = os.path.splitext(os.path.basename(original_name))[0]
    safe_stem = "".join(ch for ch in stem if ch.isalnum() or ch in ("-", "_")) or "file"
    return f"{safe_stem}-{uuid.uuid4().hex[:8]}.{new_ext.lstrip('.')}"
