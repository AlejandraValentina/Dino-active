"""Redirect desktop UI tests away from the real per-user registry/settings."""
from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QSettings

_root = Path(tempfile.mkdtemp(prefix="dino-qt-tests-"))
import os
os.environ["DINO_TEST_SETTINGS_ROOT"] = str(_root)
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(_root))
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.SystemScope, str(_root / "system"))
