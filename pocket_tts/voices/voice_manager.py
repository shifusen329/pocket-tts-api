import logging
import threading
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class VoiceInfo:
    """Information about a voice."""

    name: str
    source: str  # "predefined" or "file"
    file_path: str | None = None
    transcript: str | None = None


class VoiceManager:
    """Manages predefined and file-based voices with hot loading support."""

    def __init__(self, voices_directory: Path, predefined_voices: dict[str, str]):
        self._voices_directory = voices_directory
        self._predefined_voices = predefined_voices
        self._file_voices: list[VoiceInfo] = []
        self._lock = threading.Lock()
        self.refresh()

    def refresh(self) -> None:
        """Rescan the voices directory to detect new or removed voice files."""
        new_file_voices: list[VoiceInfo] = []

        if self._voices_directory.exists() and self._voices_directory.is_dir():
            wav_files = sorted(self._voices_directory.glob("*.wav"))
            for wav_path in wav_files:
                voice_name = wav_path.stem
                transcript = None

                # Check for corresponding transcript file
                txt_path = wav_path.with_suffix(".txt")
                if txt_path.exists():
                    try:
                        transcript = txt_path.read_text(encoding="utf-8").strip()
                    except Exception as e:
                        logger.warning("Failed to read transcript %s: %s", txt_path, e)

                new_file_voices.append(
                    VoiceInfo(
                        name=voice_name,
                        source="file",
                        file_path=str(wav_path.resolve()),
                        transcript=transcript,
                    )
                )

        with self._lock:
            self._file_voices = new_file_voices

        logger.info(
            "Voice manager refreshed: %d predefined, %d file-based voices",
            len(self._predefined_voices),
            len(new_file_voices),
        )

    def get_all_voices(self) -> list[VoiceInfo]:
        """Get combined list of predefined and file-based voices."""
        voices: list[VoiceInfo] = []

        # Add predefined voices
        for name in sorted(self._predefined_voices.keys()):
            voices.append(VoiceInfo(name=name, source="predefined"))

        # Add file-based voices
        with self._lock:
            voices.extend(self._file_voices)

        return voices

    def get_predefined_voices(self) -> list[VoiceInfo]:
        """Get only predefined voices."""
        return [
            VoiceInfo(name=name, source="predefined")
            for name in sorted(self._predefined_voices.keys())
        ]

    def get_file_voices(self) -> list[VoiceInfo]:
        """Get only file-based voices."""
        with self._lock:
            return list(self._file_voices)

    @property
    def predefined_count(self) -> int:
        """Number of predefined voices."""
        return len(self._predefined_voices)

    @property
    def file_count(self) -> int:
        """Number of file-based voices."""
        with self._lock:
            return len(self._file_voices)

    @property
    def total_count(self) -> int:
        """Total number of voices."""
        return self.predefined_count + self.file_count
