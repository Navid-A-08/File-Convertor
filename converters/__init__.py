"""File-Convertor conversion engine.

Importing this package registers every converter module (images, documents,
spreadsheets, data, archives, audio) with the shared registry. app.py only
ever needs `from converters import registry, ConversionError`.
"""
from .base import registry, ConversionError
from . import images, documents, spreadsheets, data, archives, audio  # noqa: F401

__all__ = ["registry", "ConversionError"]
