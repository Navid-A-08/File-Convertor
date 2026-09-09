"""Document format conversion: pdf, docx, doc, odt, rtf, txt, md, html.

Two code paths are used:

1. Pure-python text path — for txt/md/html <-> txt/md/html. Fast, no
   external dependencies, works anywhere.
2. LibreOffice path — for anything touching docx/doc/odt/rtf/pdf. Shells
   out to `soffice --headless --convert-to`, which is the most reliable
   way to get faithful office-document conversion without a paid API.
"""
import os
import shutil
import subprocess
import tempfile

from .base import BaseConverter, ConversionError, registry

OFFICE_FORMATS = {"docx", "doc", "odt", "rtf", "pdf"}
TEXT_FORMATS = {"txt", "md", "html"}
ALL_FORMATS = OFFICE_FORMATS | TEXT_FORMATS


def _soffice_path():
    return shutil.which("soffice") or shutil.which("libreoffice")


class DocumentConverter(BaseConverter):
    name = "documents"
    format_map = {ext: ALL_FORMATS - {ext} for ext in ALL_FORMATS}

    def convert(self, input_path, output_path, target_format, **options):
        target_format = target_format.lower().lstrip(".")
        source_format = os.path.splitext(input_path)[1].lower().lstrip(".")

        if target_format not in ALL_FORMATS:
            raise ConversionError(f"Unsupported document target format: '{target_format}'.")

        if source_format in TEXT_FORMATS and target_format in TEXT_FORMATS:
            return self._convert_text(input_path, output_path, source_format, target_format)

        return self._convert_via_office(input_path, output_path, target_format)

    # ---- pure-python path for plain-text-ish formats -----------------------
    def _convert_text(self, input_path, output_path, source_format, target_format):
        try:
            with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if source_format == "md" and target_format == "html":
                import markdown
                body = markdown.markdown(content, extensions=["extra", "tables", "sane_lists"])
                content = (
                    "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
                    f"<body>\n{body}\n</body></html>"
                )
            elif source_format == "html" and target_format in ("md", "txt"):
                import html2text
                content = html2text.html2text(content)
            elif source_format == "md" and target_format == "txt":
                import markdown
                import html2text
                body = markdown.markdown(content)
                content = html2text.html2text(body)
            elif source_format == "txt" and target_format == "html":
                escaped = (
                    content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                )
                content = (
                    "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
                    f"<body><pre>{escaped}</pre></body></html>"
                )
            # txt -> md and same-format passthroughs need no transformation

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as exc:
            raise ConversionError(f"Text document conversion failed: {exc}") from exc
        return output_path

    # ---- LibreOffice path for office formats --------------------------------
    def _convert_via_office(self, input_path, output_path, target_format):
        soffice = _soffice_path()
        if not soffice:
            raise ConversionError(
                "This conversion requires LibreOffice ('soffice') to be installed on the server."
            )

        out_dir = tempfile.mkdtemp(prefix="fc_office_")
        try:
            cmd = [
                soffice,
                "--headless",
                "--norestore",
                "--convert-to",
                target_format,
                "--outdir",
                out_dir,
                input_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise ConversionError(
                    f"LibreOffice conversion failed: {result.stderr.strip() or result.stdout.strip()}"
                )

            produced = [f for f in os.listdir(out_dir) if f.lower().endswith(f".{target_format}")]
            if not produced:
                raise ConversionError("LibreOffice did not produce an output file.")
            shutil.move(os.path.join(out_dir, produced[0]), output_path)
        except subprocess.TimeoutExpired as exc:
            raise ConversionError("Document conversion timed out after 120 seconds.") from exc
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)
        return output_path


registry.register(DocumentConverter())
