"""Versioned experiment runtime for the QRS scientific foundation.

Phase 2 provides reproducible experiment records around the existing physics:
an immutable manifest with a content-derived identifier, a manifest runner that
records real result metrics, and a reproducibility check that re-executes a
manifest and compares summaries. It adds no new physics and no persistence.
"""

from qrs.runtime.envelope import ResultEnvelope
from qrs.runtime.manifest import ExperimentManifest, capture_environment
from qrs.runtime.runner import check_reproducibility, run_manifest

__all__ = [
    "ExperimentManifest",
    "ResultEnvelope",
    "capture_environment",
    "check_reproducibility",
    "run_manifest",
]
