"""File-Convertor: Flask API + static frontend server.

Endpoints:
  GET  /                -> serves the frontend (frontend/index.html)
  GET  /api/health       -> liveness check
  GET  /api/formats      -> {converter_name: {source_ext: [target_ext, ...]}}
  POST /api/convert      -> multipart form (file, target_format, ...options) -> converted file
"""
import logging
import os
import tempfile
import uuid

from flask import Flask, jsonify, request, send_file, after_this_request
from werkzeug.utils import secure_filename

from converters import registry, ConversionError
from converters.base import unique_filename

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("file_convertor.app")

MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", 50))
# Options a request is allowed to pass through to a converter's convert()
ALLOWED_OPTIONS = {
    "quality", "resize_width", "resize_height",  # images
    "sheet_name",                                # spreadsheets
    "bitrate", "channels", "sample_rate",        # audio
}

app = Flask(__name__, static_folder="frontend", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

UPLOAD_DIR = tempfile.mkdtemp(prefix="fc_uploads_")
OUTPUT_DIR = tempfile.mkdtemp(prefix="fc_outputs_")


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/health")
def health():
    return jsonify(status="ok")


@app.route("/api/formats")
def formats():
    return jsonify(registry.capability_map())


@app.route("/api/convert", methods=["POST"])
def convert():
    if "file" not in request.files:
        return jsonify(error="No file part in request. Attach a file under the 'file' field."), 400

    upload = request.files["file"]
    if not upload.filename:
        return jsonify(error="No file selected."), 400

    target_format = (request.form.get("target_format") or "").lower().lstrip(".")
    if not target_format:
        return jsonify(error="Missing 'target_format' field."), 400

    original_name = secure_filename(upload.filename)
    if "." not in original_name:
        return jsonify(error="Could not determine the source file extension."), 400
    source_ext = original_name.rsplit(".", 1)[-1].lower()

    converter = registry.find(source_ext, target_format)
    if converter is None:
        return jsonify(
            error=f"No converter available for '.{source_ext}' -> '.{target_format}'.",
            supported=registry.capability_map(),
        ), 422

    options = {k: v for k, v in request.form.items() if k in ALLOWED_OPTIONS and v != ""}

    upload_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}-{original_name}")
    output_path = os.path.join(OUTPUT_DIR, unique_filename(original_name, target_format))
    upload.save(upload_path)

    try:
        converter.convert(upload_path, output_path, target_format, **options)
    except ConversionError as exc:
        logger.warning("Conversion failed (%s -> %s): %s", source_ext, target_format, exc)
        return jsonify(error=str(exc)), 422
    except Exception as exc:  # pragma: no cover - safety net for unexpected failures
        logger.exception("Unexpected error during conversion")
        return jsonify(error=f"Unexpected server error: {exc}"), 500
    finally:
        if os.path.exists(upload_path):
            os.remove(upload_path)

    @after_this_request
    def _cleanup(response):
        try:
            os.remove(output_path)
        except OSError:
            pass
        return response

    download_name = os.path.splitext(original_name)[0] + "." + target_format
    return send_file(output_path, as_attachment=True, download_name=download_name)


@app.errorhandler(413)
def too_large(_exc):
    return jsonify(error=f"File exceeds the {MAX_UPLOAD_MB}MB upload limit."), 413


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
