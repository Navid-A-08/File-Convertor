# File Convertor

A self-hosted file conversion service: a Flask API backed by six pluggable
converter modules, plus a single-page drag-and-drop frontend. Convert
images, documents, spreadsheets, structured data, archives, and audio
without uploading files to a third-party service.

## Supported formats

| Category      | Formats                                              |
|----------------|-------------------------------------------------------|
| Images         | png, jpg/jpeg, webp, bmp, gif, tiff, ico               |
| Documents      | pdf, docx, doc, odt, rtf, txt, md, html                |
| Spreadsheets   | xlsx, xls, csv, tsv, ods, json                         |
| Data           | json, yaml/yml, xml, toml                              |
| Archives       | zip, tar, tar.gz, tgz, tar.bz2                         |
| Audio          | mp3, wav, ogg, flac, m4a, aac                          |

Any source format in a row can convert to any other target format in that
same row. Query `GET /api/formats` for the exact machine-readable map.

## Architecture

```
file-convertor/
├── app.py                 # Flask API + serves the frontend
├── converters/
│   ├── base.py             # BaseConverter interface + ConverterRegistry
│   ├── images.py           # Pillow
│   ├── documents.py        # LibreOffice (office formats) + pure-python (txt/md/html)
│   ├── spreadsheets.py      # pandas
│   ├── data.py              # json/yaml/xml/toml, pure python
│   ├── archives.py          # zipfile/tarfile
│   └── audio.py             # pydub + ffmpeg
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── requirements.txt
├── Dockerfile
└── .dockerignore
```

Each converter module defines one `BaseConverter` subclass and registers a
single instance of it. The subclass declares a `format_map` (which source
extensions can become which target extensions) and implements `convert()`.
`app.py` never hardcodes format logic — it asks the shared `registry` to
find whichever converter can handle `source_ext -> target_ext`, so adding a
seventh converter module is a matter of dropping in a new file and
importing it from `converters/__init__.py`.

## Local setup

Requires Python 3.11+. For document and audio conversions you also need
`soffice` (LibreOffice) and `ffmpeg` on your PATH — everything else
(images, spreadsheets, data, archives) works with just the pip packages.

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# optional, for full functionality:
#   macOS:   brew install libreoffice ffmpeg
#   Ubuntu:  sudo apt install libreoffice-writer ffmpeg

python app.py
```

The app starts on `http://localhost:5000` — the frontend is served at `/`.

## Docker

The provided Dockerfile bundles LibreOffice and ffmpeg so every conversion
works out of the box.

```bash
docker build -t file-convertor .
docker run -p 5000:5000 file-convertor
```

Open `http://localhost:5000`.

### Environment variables

| Variable        | Default | Description                                |
|-----------------|---------|----------------------------------------------|
| `PORT`          | `5000`  | Port the server listens on                   |
| `MAX_UPLOAD_MB` | `50`    | Maximum accepted upload size, in megabytes   |
| `FLASK_DEBUG`   | unset   | Set to `1` to run the dev server with debug on (local `python app.py` only) |

## API reference

### `GET /api/health`

Liveness check. Returns `{"status": "ok"}`.

### `GET /api/formats`

Returns the full capability map:

```json
{
  "images": { "png": ["bmp", "gif", "ico", "jpg", "jpeg", "tiff", "webp"], "...": "..." },
  "documents": { "docx": ["doc", "html", "md", "odt", "pdf", "rtf", "txt"], "...": "..." },
  "spreadsheets": { "...": "..." },
  "data": { "...": "..." },
  "archives": { "...": "..." },
  "audio": { "...": "..." }
}
```

### `POST /api/convert`

`multipart/form-data` body:

| Field           | Required | Description                                          |
|------------------|----------|-------------------------------------------------------|
| `file`           | yes      | The file to convert                                   |
| `target_format`  | yes      | Target extension, without the dot (e.g. `webp`)       |
| `resize_width`   | no       | Images only — resize to this width (px)               |
| `resize_height`  | no       | Images only — resize to this height (px)               |
| `quality`        | no       | Images only (jpg/jpeg/webp) — 1-100, default 90         |
| `sheet_name`     | no       | Spreadsheets only — sheet index/name to read, default 0 |
| `bitrate`        | no       | Audio only — e.g. `192k`, default `192k`                |
| `channels`       | no       | Audio only — force mono (`1`) or stereo (`2`)           |
| `sample_rate`    | no       | Audio only — e.g. `44100`                               |

On success, returns the converted file as a binary attachment
(`Content-Disposition: attachment; filename=...`).

On failure, returns JSON: `{"error": "human-readable message"}` with
status `400` (bad request), `422` (unsupported conversion / conversion
failed), or `413` (file too large).

**Example:**

```bash
curl -X POST http://localhost:5000/api/convert \
  -F "file=@photo.png" \
  -F "target_format=webp" \
  -F "quality=85" \
  -o photo.webp
```

## Adding a new converter

1. Create `converters/your_format.py`.
2. Define a `YourConverter(BaseConverter)` with a `name`, a `format_map`
   (`{source_ext: {target_ext, ...}}`), and a `convert(self, input_path,
   output_path, target_format, **options)` method that raises
   `ConversionError` on failure.
3. Call `registry.register(YourConverter())` at module import time.
4. Add `from . import your_format` to `converters/__init__.py`.

No changes to `app.py` or the frontend are required — the format dropdown
and the `/api/convert` dispatch both read from the registry at request
time.

## Limitations

- Document conversions that touch `docx`/`doc`/`odt`/`rtf`/`pdf` require
  LibreOffice on the server; `txt`/`md`/`html` conversions do not.
- Audio conversions require ffmpeg on the server.
- Legacy `.xls` output is actually written in the modern `.xlsx` container
  (pandas/openpyxl no longer support writing legacy `.xls`).
- Conversions run synchronously within a single request; very large files
  or slow office/audio conversions can hit the request timeout (180s in
  the provided gunicorn config). For heavier workloads, put a job queue
  (e.g. Celery/RQ) in front of `converter.convert()`.
- No authentication, rate limiting, or virus scanning is included — add
  these before exposing the service on the public internet.

## License

Free to use it, fork it, ship it.
