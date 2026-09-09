FROM python:3.11-slim

# System dependencies:
#   libreoffice-writer  -> docx/doc/odt/rtf/pdf conversions (converters/documents.py)
#   ffmpeg              -> audio conversions (converters/audio.py)
#   fonts-dejavu-core   -> decent default fonts for LibreOffice-rendered output
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-writer \
        ffmpeg \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5000 \
    MAX_UPLOAD_MB=50 \
    PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "180", "app:app"]
