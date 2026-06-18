"""Load ingest configuration from product.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "product.yaml"


@dataclass
class PlatformColumnMap:
    date: list[str] = field(default_factory=list)
    rating: list[str] = field(default_factory=list)
    title: list[str] = field(default_factory=list)
    body: list[str] = field(default_factory=list)
    username: list[str] = field(default_factory=list)
    version: list[str] = field(default_factory=list)
    country: list[str] = field(default_factory=list)
    device: list[str] = field(default_factory=list)


@dataclass
class IngestConfig:
    lookback_weeks: int = 10
    min_lookback_weeks: int = 8
    max_lookback_weeks: int = 12
    min_word_count: int = 6
    english_only: bool = True
    cross_platform_dedupe_days: int = 1
    app_store: PlatformColumnMap = field(default_factory=PlatformColumnMap)
    play_store: PlatformColumnMap = field(default_factory=PlatformColumnMap)

    def validate_lookback(self) -> None:
        if not (self.min_lookback_weeks <= self.lookback_weeks <= self.max_lookback_weeks):
            raise ValueError(
                f"lookback_weeks={self.lookback_weeks} must be between "
                f"{self.min_lookback_weeks} and {self.max_lookback_weeks}"
            )


def _column_map(raw: dict[str, Any] | None) -> PlatformColumnMap:
    raw = raw or {}
    return PlatformColumnMap(
        date=list(raw.get("date", [])),
        rating=list(raw.get("rating", [])),
        title=list(raw.get("title", [])),
        body=list(raw.get("body", [])),
        username=list(raw.get("username", [])),
        version=list(raw.get("version", [])),
        country=list(raw.get("country", [])),
        device=list(raw.get("device", [])),
    )


def load_ingest_config(path: Path | None = None) -> IngestConfig:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        raise FileNotFoundError(f"Ingest config not found: {config_path}")

    with config_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    ingest = data.get("ingest", {})
    platforms = data.get("platforms", {})

    cfg = IngestConfig(
        lookback_weeks=int(ingest.get("lookback_weeks", 10)),
        min_lookback_weeks=int(ingest.get("min_lookback_weeks", 8)),
        max_lookback_weeks=int(ingest.get("max_lookback_weeks", 12)),
        min_word_count=int(ingest.get("min_word_count", 6)),
        english_only=bool(ingest.get("english_only", True)),
        cross_platform_dedupe_days=int(ingest.get("cross_platform_dedupe_days", 1)),
        app_store=_column_map(platforms.get("app_store", {}).get("columns")),
        play_store=_column_map(platforms.get("play_store", {}).get("columns")),
    )
    cfg.validate_lookback()
    return cfg
