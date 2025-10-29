"""Legacy filter wrapper maintained for backwards compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from services.radar_processing import ProcessedImage, process_level3_bytes


@dataclass
class FilterResult:
    """Result returned from the legacy Filter helper."""

    image_path: Path
    bounds: Optional[dict]


class Filter:
    """Compatibility wrapper around :func:`process_level3_bytes`."""

    def __init__(self, file_reference):
        if isinstance(file_reference, (str, Path)):
            file_path = Path(file_reference)
            self._file_bytes = file_path.read_bytes()
        elif isinstance(file_reference, (bytes, bytearray)):
            self._file_bytes = bytes(file_reference)
        else:
            # file-like object
            data = file_reference.read()
            self._file_bytes = data if isinstance(data, bytes) else bytes(data)

    def filter_dbz(self, filtered_amount: Optional[int] = None) -> Path:
        """Render the radar product and store it under ``static/``."""

        processed: ProcessedImage = process_level3_bytes(self._file_bytes, filtered_amount)
        output_path = Path("static/radar_filter.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(processed.content)
        return output_path

    def filter_dbz_with_metadata(
        self, filtered_amount: Optional[int] = None
    ) -> FilterResult:
        processed: ProcessedImage = process_level3_bytes(self._file_bytes, filtered_amount)
        output_path = Path("static/radar_filter.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(processed.content)
        return FilterResult(image_path=output_path, bounds=processed.bounds)

    
