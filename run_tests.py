#!/usr/bin/env python3
"""Test runner for RTC-Tools QGIS Plugin.

Initializes QgsApplication in headless (offscreen) mode, discovers all tests
in the 'tests' directory, executes them, and reports results.
"""

import sys
import os
import unittest

def main():
    # Set Qt offscreen platform before importing QGIS / Qt
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    # Ensure workspace root and parent directory are in sys.path
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(plugin_dir)

    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    # Initialize GUI-enabled QGIS Application in offscreen mode for widget/canvas tests
    from qgis.core import QgsApplication
    app = QgsApplication([], True)
    app.initQgis()

    try:
        # Discover and run all tests in tests/ directory
        loader = unittest.TestLoader()
        suite = loader.discover(
            start_dir=os.path.join(plugin_dir, "tests"),
            pattern="test_*.py",
            top_level_dir=parent_dir
        )

        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        return 0 if result.wasSuccessful() else 1
    finally:
        app.exitQgis()

if __name__ == "__main__":
    sys.exit(main())

