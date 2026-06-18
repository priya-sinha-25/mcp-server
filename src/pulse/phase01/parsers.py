"""CSV parsers for App Store and Play Store exports."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from pulse.models import Platform
from pulse.phase01.config import IngestConfig, PlatformColumnMap


class ParseError(Exception):
    """Raised when a file cannot be read at all."""

    def __init__(self, path: Path, message: str):
        self.path = path
        super().__init__(f"{path}: {message}")


@dataclass
class RawReviewRow:
    platform: Platform
    review_date: date
    rating: int
    title: str
    body: str
    source_row: int
    version: str | None = None
    country: str | None = None


def _resolve_column(fieldnames: list[str] | None, candidates: list[str]) -> str | None:
    if not fieldnames:
        return None
    lower_map = {name.strip().lower(): name for name in fieldnames if name}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in lower_map:
            return lower_map[key]
    return None


def _get_cell(row: dict[str, str], column: str | None) -> str:
    if column is None:
        return ""
    return (row.get(column) or "").strip()


def _parse_date(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    # Try ISO date first (YYYY-MM-DD)
    for fmt in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(value[:19], fmt).date()
        except ValueError:
            continue
    # Play Store sometimes uses "March 15, 2026"
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_rating(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        rating = int(float(value))
    except ValueError:
        return None
    if 1 <= rating <= 5:
        return rating
    return None


def detect_platform(path: Path, cfg: IngestConfig) -> Platform:
    """Infer platform from filename or header row."""
    name = path.name.lower()
    if "play" in name or "google" in name or "android" in name:
        return Platform.PLAY_STORE
    if "app" in name and "store" in name:
        return Platform.APP_STORE
    if "itunes" in name or "ios" in name:
        return Platform.APP_STORE

    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = [h.lower() for h in (reader.fieldnames or [])]
    except OSError as e:
        raise ParseError(path, str(e)) from e

    play_signals = {"review text", "star rating", "review submit date"}
    app_signals = {"review", "rating", "username"}

    if any(h in headers for h in play_signals):
        return Platform.PLAY_STORE
    if "review submit date and time" in headers:
        return Platform.PLAY_STORE
    if "username" in headers and "review" in headers:
        return Platform.APP_STORE
    if any(h in headers for h in app_signals):
        return Platform.APP_STORE

    raise ParseError(
        path,
        "Could not detect platform from filename or headers; "
        "rename file (app_store / play_store) or fix export columns.",
    )


def _column_map_for(platform: Platform, cfg: IngestConfig) -> PlatformColumnMap:
    return cfg.app_store if platform == Platform.APP_STORE else cfg.play_store


def parse_csv_file(
    path: Path,
    platform: Platform | None,
    cfg: IngestConfig,
) -> tuple[list[RawReviewRow], list[str], int]:
    """Parse one CSV export. Returns rows, warnings, and data rows scanned."""
    warnings: list[str] = []
    path = Path(path)
    if not path.is_file():
        raise ParseError(path, "file not found")

    plat = platform or detect_platform(path, cfg)
    colmap = _column_map_for(plat, cfg)

    rows: list[RawReviewRow] = []
    rows_scanned = 0
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ParseError(path, "CSV has no header row")

            date_col = _resolve_column(reader.fieldnames, colmap.date)
            rating_col = _resolve_column(reader.fieldnames, colmap.rating)
            title_col = _resolve_column(reader.fieldnames, colmap.title)
            body_col = _resolve_column(reader.fieldnames, colmap.body)
            version_col = _resolve_column(reader.fieldnames, colmap.version)
            country_col = _resolve_column(reader.fieldnames, colmap.country)

            if not date_col or not rating_col or not body_col:
                raise ParseError(
                    path,
                    f"Missing required columns for {plat.value}; "
                    f"need date, rating, body. Found headers: {reader.fieldnames}",
                )

            for i, row in enumerate(reader, start=2):
                rows_scanned += 1
                try:
                    raw_date = _get_cell(row, date_col)
                    parsed_date = _parse_date(raw_date)
                    if parsed_date is None:
                        warnings.append(f"{path.name} row {i}: skipped (unparseable date)")
                        continue

                    raw_rating = _get_cell(row, rating_col)
                    rating = _parse_rating(raw_rating)
                    if rating is None:
                        warnings.append(f"{path.name} row {i}: skipped (invalid rating)")
                        continue

                    title = _get_cell(row, title_col)
                    body = _get_cell(row, body_col)
                    if not body:
                        continue

                    version = _get_cell(row, version_col) or None
                    country = _get_cell(row, country_col) or None

                    rows.append(
                        RawReviewRow(
                            platform=plat,
                            review_date=parsed_date,
                            rating=rating,
                            title=title,
                            body=body,
                            source_row=i,
                            version=version,
                            country=country,
                        )
                    )
                except Exception as e:
                    warnings.append(f"{path.name} row {i}: skipped ({e})")
    except ParseError:
        raise
    except UnicodeDecodeError as e:
        raise ParseError(path, f"encoding error: {e}") from e
    except OSError as e:
        raise ParseError(path, str(e)) from e

    return rows, warnings, rows_scanned
