"""Phase 2 configuration: sampling caps and Groq settings (DEC-011, DEC-012)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "product.yaml"


@dataclass
class SamplingConfig:
    """Stratified sampling parameters (DEC-012)."""

    # Step 1: proportional pre-sample cap (working-set size).
    pre_sample_n: int = 1000
    # Step 2: per-tier per-week caps.
    neg_cap: int = 7    # negative tier (≤2★)
    neu_cap: int = 3    # neutral tier (3★)
    pos_cap: int = 5    # positive tier (4–5★)
    # Reproducibility seed.
    seed: int = 42


@dataclass
class GroqConfig:
    """Groq API settings (DEC-011)."""

    model: str = "llama-3.3-70b-versatile"
    stage_a_temperature: float = 0.2
    stage_b_temperature: float = 0.5
    max_themes: int = 5
    max_retries: int = 2
    # Safety guard: abort retry if remaining TPD headroom is below this.
    min_tpd_headroom: int = 3000


@dataclass
class Phase2Config:
    sampling: SamplingConfig = field(default_factory=SamplingConfig)
    groq: GroqConfig = field(default_factory=GroqConfig)
    product_name: str = "Unknown"


def load_phase2_config(path: Path | None = None) -> Phase2Config:
    """Load Phase 2 config from product.yaml, falling back to defaults."""
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with config_path.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    product_name: str = data.get("product", {}).get("name", "Unknown")

    raw_sampling: dict[str, Any] = data.get("sampling", {})
    sampling = SamplingConfig(
        pre_sample_n=int(raw_sampling.get("pre_sample_n", 1000)),
        neg_cap=int(raw_sampling.get("neg_cap", 7)),
        neu_cap=int(raw_sampling.get("neu_cap", 3)),
        pos_cap=int(raw_sampling.get("pos_cap", 5)),
        seed=int(raw_sampling.get("seed", 42)),
    )

    raw_groq: dict[str, Any] = data.get("groq", {})
    groq = GroqConfig(
        model=str(raw_groq.get("model", "llama-3.3-70b-versatile")),
        stage_a_temperature=float(raw_groq.get("stage_a_temperature", 0.2)),
        stage_b_temperature=float(raw_groq.get("stage_b_temperature", 0.5)),
        max_themes=int(raw_groq.get("max_themes", 5)),
        max_retries=int(raw_groq.get("max_retries", 2)),
        min_tpd_headroom=int(raw_groq.get("min_tpd_headroom", 3000)),
    )

    return Phase2Config(sampling=sampling, groq=groq, product_name=product_name)
