"""Phase 2: Theming & pulse generation + validation (architecture §5.2, §5.3)."""

from pulse.phase02.config import Phase2Config, load_phase2_config
from pulse.phase02.drafter import PulseDraftError, draft_pulse
from pulse.phase02.sampler import SampleResult, pre_sample, stratified_sample
from pulse.phase02.themer import ThemeDiscoveryError, discover_themes
from pulse.phase02.validator import validate_pulse

__all__ = [
    "load_phase2_config",
    "Phase2Config",
    "pre_sample",
    "stratified_sample",
    "SampleResult",
    "discover_themes",
    "ThemeDiscoveryError",
    "draft_pulse",
    "PulseDraftError",
    "validate_pulse",
]
