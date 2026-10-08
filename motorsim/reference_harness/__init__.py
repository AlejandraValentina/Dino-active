"""Reusable reference-engine campaign orchestration and evidence tools."""

from .config import validate_config
from .convergence import PeriodicDetector, compare_cycles

__all__ = ["validate_config", "PeriodicDetector", "compare_cycles"]
