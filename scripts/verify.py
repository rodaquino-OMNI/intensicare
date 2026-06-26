#!/usr/bin/env python3
"""
Intensicare — Import chain validator.

Validates that every module in the intensicare package is importable.
Runs with the current Python environment (venv or system) and verifies
the integrity of the source-tree import graph.

Exit code 0 = all good. Non-zero = broken imports (stderr has details).
"""

import importlib
import sys
import traceback
from pathlib import Path
from typing import Sequence

# Ensure the project root is on sys.path so that "import intensicare" works
# regardless of whether the package is installed in editable mode.
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ---------------------------------------------------------------------------
# Module list — every importable module in intensicare
# ---------------------------------------------------------------------------
MODULES: Sequence[str] = (
    # Top-level
    "intensicare",
    "intensicare.config",
    "intensicare.main",
    "intensicare.auth",
    "intensicare.mllp_listener",
    # Core
    "intensicare.core",
    "intensicare.core.database",
    "intensicare.core.redis",
    "intensicare.core.websocket",
    # Models
    "intensicare.models",
    "intensicare.models.alert",
    "intensicare.models.clinical_score",
    "intensicare.models.patient_cache",
    "intensicare.models.threshold_config",
    "intensicare.models.user",
    "intensicare.models.vital_sign",
    # Schemas
    "intensicare.schemas",
    "intensicare.schemas.dashboard",
    "intensicare.schemas.patients",
    "intensicare.schemas.thresholds",
    "intensicare.schemas.vitals",
    # Services
    "intensicare.services",
    "intensicare.services.alert_engine",
    "intensicare.services.dashboard",
    "intensicare.services.mews",
    "intensicare.services.news2",
    "intensicare.services.patients",
    "intensicare.services.qsofa",
    "intensicare.services.sofa",
    "intensicare.services.vitals",
    # Auth
    "intensicare.auth.dependencies",
    "intensicare.auth.jwt",
    # API
    "intensicare.api",
    "intensicare.api.patients",
    "intensicare.api.thresholds",
    "intensicare.api.vitals",
    "intensicare.api.v1",
    "intensicare.api.v1.alerts",
    "intensicare.api.v1.auth",
    "intensicare.api.v1.dashboard",
)


def verify() -> int:
    """Try to import every module and report results. Returns exit code."""
    failures: list[tuple[str, str]] = []
    successes: list[str] = []

    for module_name in MODULES:
        try:
            importlib.import_module(module_name)
            successes.append(module_name)
        except Exception:
            failures.append((module_name, traceback.format_exc()))

    # Report
    print(f"✓ Imported {len(successes)}/{len(MODULES)} modules successfully.\n")

    if failures:
        print(f"✗ {len(failures)} module(s) failed to import:\n")
        for name, tb in failures:
            print(f"── {name} ──")
            # Only show the last few lines of the traceback (the actual error)
            lines = tb.strip().splitlines()
            for line in lines[-6:]:
                print(f"   {line}")
            print()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(verify())
