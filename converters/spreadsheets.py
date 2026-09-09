"""Spreadsheet / tabular format conversion: xlsx, xls, csv, tsv, ods, json.

Built on pandas, which gives us a single tabular in-memory representation
(DataFrame) to pivot every format through — read once, write to any target.
"""
import pandas as pd

from .base import BaseConverter, ConversionError, registry

SPREADSHEET_FORMATS = {"xlsx", "xls", "csv", "tsv", "ods", "json"}

_READERS = {
    "xlsx": lambda p, **kw: pd.read_excel(p, engine="openpyxl", **kw),
    "xls": lambda p, **kw: pd.read_excel(p, **kw),
    "ods": lambda p, **kw: pd.read_excel(p, engine="odf", **kw),
    "csv": lambda p, **kw: pd.read_csv(p),
    "tsv": lambda p, **kw: pd.read_csv(p, sep="\t"),
    "json": lambda p, **kw: pd.read_json(p),
}


class SpreadsheetConverter(BaseConverter):
    name = "spreadsheets"
    format_map = {ext: SPREADSHEET_FORMATS - {ext} for ext in SPREADSHEET_FORMATS}

    def convert(self, input_path, output_path, target_format, **options):
        source_format = input_path.rsplit(".", 1)[-1].lower()
        target_format = target_format.lower().lstrip(".")

        if source_format not in _READERS:
            raise ConversionError(f"Unsupported spreadsheet source format: '{source_format}'.")
        if target_format not in SPREADSHEET_FORMATS:
            raise ConversionError(f"Unsupported spreadsheet target format: '{target_format}'.")

        try:
            reader_kwargs = {}
            if source_format in ("xlsx", "xls", "ods"):
                reader_kwargs["sheet_name"] = options.get("sheet_name", 0)

            df = _READERS[source_format](input_path, **reader_kwargs)
            if isinstance(df, dict):  # sheet_name returned every sheet
                df = next(iter(df.values()))

            if target_format == "csv":
                df.to_csv(output_path, index=False)
            elif target_format == "tsv":
                df.to_csv(output_path, sep="\t", index=False)
            elif target_format == "json":
                df.to_json(output_path, orient="records", indent=2)
            elif target_format in ("xlsx", "xls"):
                # pandas/openpyxl only write the modern xlsx container; that's
                # what we produce even when the user asked for legacy .xls.
                df.to_excel(output_path, index=False, engine="openpyxl")
            elif target_format == "ods":
                df.to_excel(output_path, index=False, engine="odf")
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError(f"Spreadsheet conversion failed: {exc}") from exc
        return output_path


registry.register(SpreadsheetConverter())
