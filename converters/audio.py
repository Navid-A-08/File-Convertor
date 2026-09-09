"""Audio format conversion: mp3, wav, ogg, flac, m4a, aac.

Thin wrapper around pydub, which itself shells out to ffmpeg for the actual
decode/encode work. ffmpeg must be present on the host/container (see
Dockerfile) — we check for it up front and fail with a clear message
instead of a cryptic pydub traceback.
"""
import shutil

from pydub import AudioSegment

from .base import BaseConverter, ConversionError, registry

AUDIO_FORMATS = {"mp3", "wav", "ogg", "flac", "m4a", "aac"}

_EXPORT_FORMAT = {
    "mp3": "mp3",
    "wav": "wav",
    "ogg": "ogg",
    "flac": "flac",
    "m4a": "ipod",  # pydub/ffmpeg's name for the m4a/mp4-audio container
    "aac": "adts",
}


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


class AudioConverter(BaseConverter):
    name = "audio"
    format_map = {ext: AUDIO_FORMATS - {ext} for ext in AUDIO_FORMATS}

    def convert(self, input_path, output_path, target_format, **options):
        target_format = target_format.lower().lstrip(".")
        if target_format not in _EXPORT_FORMAT:
            raise ConversionError(f"Unsupported audio target format: '{target_format}'.")
        if not _ffmpeg_available():
            raise ConversionError(
                "Audio conversion requires 'ffmpeg' to be installed on the server."
            )

        try:
            source_format = input_path.rsplit(".", 1)[-1].lower()
            audio = AudioSegment.from_file(input_path, format=source_format)

            channels = options.get("channels")
            sample_rate = options.get("sample_rate")
            if channels:
                audio = audio.set_channels(int(channels))
            if sample_rate:
                audio = audio.set_frame_rate(int(sample_rate))

            export_kwargs = {}
            if target_format in ("mp3", "aac", "m4a"):
                export_kwargs["bitrate"] = options.get("bitrate", "192k")

            audio.export(output_path, format=_EXPORT_FORMAT[target_format], **export_kwargs)
        except ConversionError:
            raise
        except Exception as exc:
            raise ConversionError(f"Audio conversion failed: {exc}") from exc
        return output_path


registry.register(AudioConverter())
