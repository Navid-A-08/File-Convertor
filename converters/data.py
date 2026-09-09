"""Structured data format conversion: json, yaml, xml, toml.

Unlike spreadsheets.py (tabular, row/column oriented), this module is for
nested/hierarchical data — configs, API payloads, etc. Everything is loaded
into plain python dict/list/scalar objects and re-serialized, so any format
here can convert to any other.
"""
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

import yaml
import tomli_w

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover - only hit on Python < 3.11
    import tomli as tomllib

from .base import BaseConverter, ConversionError, registry

DATA_FORMATS = {"json", "yaml", "yml", "xml", "toml"}


def _load(path: str, fmt: str):
    if fmt == "toml":
        with open(path, "rb") as f:
            return tomllib.load(f)

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    if fmt == "json":
        return json.loads(raw)
    if fmt in ("yaml", "yml"):
        return yaml.safe_load(raw)
    if fmt == "xml":
        return _xml_to_obj(ET.fromstring(raw))
    raise ConversionError(f"Unsupported data source format: '{fmt}'.")


def _dump(obj, path: str, fmt: str):
    if fmt == "json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
    elif fmt in ("yaml", "yml"):
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)
    elif fmt == "toml":
        # TOML documents must be tables at the top level
        wrapped = obj if isinstance(obj, dict) else {"data": obj}
        with open(path, "wb") as f:
            tomli_w.dump(wrapped, f)
    elif fmt == "xml":
        root = _obj_to_xml(obj, "root")
        pretty = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        with open(path, "w", encoding="utf-8") as f:
            f.write(pretty)
    else:
        raise ConversionError(f"Unsupported data target format: '{fmt}'.")


def _xml_to_obj(element: ET.Element):
    children = list(element)
    if not children:
        return element.text.strip() if element.text else None
    result = {}
    for child in children:
        value = _xml_to_obj(child)
        if child.tag in result:
            existing = result[child.tag]
            if not isinstance(existing, list):
                existing = [existing]
                result[child.tag] = existing
            existing.append(value)
        else:
            result[child.tag] = value
    return result


def _obj_to_xml(obj, tag: str) -> ET.Element:
    el = ET.Element(tag)
    if isinstance(obj, dict):
        for key, value in obj.items():
            el.append(_obj_to_xml(value, str(key)))
    elif isinstance(obj, list):
        for item in obj:
            el.append(_obj_to_xml(item, "item"))
    else:
        el.text = "" if obj is None else str(obj)
    return el


class DataConverter(BaseConverter):
    name = "data"
    format_map = {ext: DATA_FORMATS - {ext} for ext in DATA_FORMATS}

    def convert(self, input_path, output_path, target_format, **options):
        source_format = input_path.rsplit(".", 1)[-1].lower()
        target_format = target_format.lower().lstrip(".")

        if source_format not in DATA_FORMATS:
            raise ConversionError(f"Unsupported data source format: '{source_format}'.")
        if target_format not in DATA_FORMATS:
            raise ConversionError(f"Unsupported data target format: '{target_format}'.")

        try:
            obj = _load(input_path, source_format)
            _dump(obj, output_path, target_format)
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError(f"Data conversion failed: {exc}") from exc
        return output_path


registry.register(DataConverter())
