"""Archive format conversion: zip, tar, tar.gz, tgz, tar.bz2.

Approach: fully extract the source archive to a scratch directory, then
repack that directory tree into the target container format. Simple and
format-agnostic, at the cost of temporarily materializing the contents on
disk (bounded by MAX_UPLOAD_MB in app.py).
"""
import os
import shutil
import tarfile
import tempfile
import zipfile

from .base import BaseConverter, ConversionError, registry

ARCHIVE_FORMATS = {"zip", "tar", "tar.gz", "tgz", "tar.bz2"}

_TAR_READ_MODE = {"tar": "r:", "tar.gz": "r:gz", "tgz": "r:gz", "tar.bz2": "r:bz2"}
_TAR_WRITE_MODE = {"tar": "w:", "tar.gz": "w:gz", "tgz": "w:gz", "tar.bz2": "w:bz2"}


def _detect_format(path: str) -> str:
    name = os.path.basename(path).lower()
    if name.endswith(".tar.gz"):
        return "tar.gz"
    if name.endswith(".tar.bz2"):
        return "tar.bz2"
    if name.endswith(".tgz"):
        return "tgz"
    if name.endswith(".tar"):
        return "tar"
    if name.endswith(".zip"):
        return "zip"
    raise ConversionError(f"Could not detect archive format for '{os.path.basename(path)}'.")


class ArchiveConverter(BaseConverter):
    name = "archives"
    format_map = {ext: ARCHIVE_FORMATS - {ext} for ext in ARCHIVE_FORMATS}

    def convert(self, input_path, output_path, target_format, **options):
        target_format = target_format.lower().lstrip(".")
        source_format = _detect_format(input_path)

        if target_format not in ARCHIVE_FORMATS:
            raise ConversionError(f"Unsupported archive target format: '{target_format}'.")

        extract_dir = tempfile.mkdtemp(prefix="fc_archive_")
        try:
            self._extract(input_path, source_format, extract_dir)
            self._pack(extract_dir, output_path, target_format)
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError(f"Archive conversion failed: {exc}") from exc
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)
        return output_path

    @staticmethod
    def _extract(input_path: str, source_format: str, extract_dir: str):
        if source_format == "zip":
            with zipfile.ZipFile(input_path) as zf:
                zf.extractall(extract_dir)
        else:
            with tarfile.open(input_path, _TAR_READ_MODE[source_format]) as tf:
                tf.extractall(extract_dir)

    @staticmethod
    def _pack(extract_dir: str, output_path: str, target_format: str):
        if target_format == "zip":
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _dirs, files in os.walk(extract_dir):
                    for name in files:
                        full_path = os.path.join(root, name)
                        zf.write(full_path, os.path.relpath(full_path, extract_dir))
        else:
            with tarfile.open(output_path, _TAR_WRITE_MODE[target_format]) as tf:
                for entry in os.listdir(extract_dir):
                    tf.add(os.path.join(extract_dir, entry), arcname=entry)


registry.register(ArchiveConverter())
