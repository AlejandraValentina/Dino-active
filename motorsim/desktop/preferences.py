from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSettings


def settings():
    return QSettings("Dino2T", "DinoDesktop")


def artifact_root() -> Path:
    configured=settings().value("artifact_root")
    if isinstance(configured,str) and configured.strip():
        return Path(configured).expanduser()
    env=os.environ.get("DINO_ARTIFACT_ROOT")
    return Path(env).expanduser() if env else Path.home()/"Dino-artifacts"


def set_artifact_root(path: str | Path) -> Path:
    value=Path(path).expanduser()
    settings().setValue("artifact_root",str(value))
    settings().sync()
    return value


def impl2_historical_report_candidate() -> Path:
    return artifact_root()/"engine-physics-v1/full-rpm-sweep-v1-impl2/authorized-extension-26-v1/reports/impl2-full-rpm-sweep-30-points.json"
