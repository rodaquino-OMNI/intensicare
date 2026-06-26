#!/usr/bin/env python3
"""
Intensicare — Import chain and pytest collection validator.

Validates that:
1. Every module in the intensicare package is importable.
2. pytest can collect the test suite without errors.

Runs with the current Python environment (venv or system) and verifies
the integrity of the source-tree import graph and test suite.

Exit code 0 = all good. Non-zero = broken imports or test collection (stderr has details).
"""

import importlib
import subprocess
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


def verify_imports() -> int:
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


def verify_pytest_collection() -> int:
    """Run `pytest --collect-only` to validate test discovery.

    Uses the pytest from the current Python environment. The test suite
    is collected without executing any tests. All warnings are surfaced.

    Returns 0 if collection succeeds, 1 on failure.
    """
    tests_dir = ROOT / "tests"
    if not tests_dir.is_dir():
        print(f"✗ Tests directory not found: {tests_dir}")
        return 1

    # Build the pytest command — use the same Python interpreter to find pytest
    python_exe = sys.executable
    cmd = [python_exe, "-m", "pytest", str(tests_dir), "--collect-only", "-q"]
    print(f"[pytest collection] Running: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=120,
        )
    except FileNotFoundError:
        print("✗ pytest not found. Install it with: pip install pytest pytest-asyncio")
        return 1
    except subprocess.TimeoutExpired:
        print("✗ pytest collection timed out (120s)")
        return 1

    # Print output for diagnostics
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode == 0:
        # Extract test count from output if possible
        print("✓ pytest collection succeeded.\n")
        return 0
    else:
        print(f"✗ pytest collection failed (exit code {result.returncode}).\n")
        return 1


def verify() -> int:
    """Run all validations. Returns combined exit code."""
    print("=" * 60)
    print("  Intensicare — Verification Suite")
    print("=" * 60)
    print()

    exit_code = 0

    # 1. Import verification
    print("── 1. Import Verification ──")
    if verify_imports() != 0:
        exit_code = 1

    # 2. Pytest collection verification
    print("── 2. Pytest Collection Verification ──")
    if verify_pytest_collection() != 0:
        exit_code = 1

    # Summary
    print("=" * 60)
    if exit_code == 0:
        print("✓ All verifications passed.")
    else:
        print("✗ Some verifications failed. See details above.")
    print("=" * 60)

    return exit_code


if __name__ == "__main__":
    sys.exit(verify())
