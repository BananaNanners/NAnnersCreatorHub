"""Run PySide6 GUI tests offscreen with deterministic Qt widget cleanup.

The standard unittest command occasionally crashes at PySide6 interpreter
shutdown on this desktop after all assertions have passed. Delete surviving
top-level test widgets while QApplication is still alive.
"""
from __future__ import annotations

import gc
import os
from pathlib import Path
import sys
import unittest


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication
    import shiboken6

    app = QApplication.instance() or QApplication([])
    suite = unittest.defaultTestLoader.discover(str(root / "tests"))
    try:
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        return 0 if result.wasSuccessful() else 1
    finally:
        for widget in QApplication.topLevelWidgets():
            if shiboken6.isValid(widget):
                shiboken6.delete(widget)
        app.processEvents()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        gc.collect()


if __name__ == "__main__":
    raise SystemExit(main())
