from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSettings


def settings():
    test_root=os.environ.get("DINO_TEST_SETTINGS_ROOT")
    if test_root:
        root=Path(test_root);root.mkdir(parents=True,exist_ok=True)
        QSettings.setPath(QSettings.Format.IniFormat,QSettings.Scope.UserScope,str(root))
        return QSettings(QSettings.Format.IniFormat,QSettings.Scope.UserScope,"Dino2T","DinoDesktop")
    return QSettings("Dino2T", "DinoDesktop")


def repository_root_containing(path: str | Path) -> Path | None:
    """Return the enclosing Git worktree root, if ``path`` is inside one."""
    candidate=Path(path).expanduser().resolve()
    for parent in (candidate,*candidate.parents):
        marker=parent/".git"
        if marker.exists():
            return parent
    return None


def default_artifact_root() -> Path:
    """Choose a safe default outside any repository, without moving old data."""
    env=os.environ.get("DINO_ARTIFACT_ROOT")
    if env:
        candidate=Path(env).expanduser()
        if repository_root_containing(candidate) is None:
            return candidate
    local=os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local)/"MotorSim"/"Artifacts"
    xdg=os.environ.get("XDG_DATA_HOME")
    return (Path(xdg) if xdg else Path.home()/".local"/"share")/"MotorSim"/"Artifacts"


def artifact_root() -> Path:
    configured=settings().value("artifact_root")
    if isinstance(configured,str) and configured.strip():
        return Path(configured).expanduser()
    return default_artifact_root()


def set_artifact_root(path: str | Path, *, allow_repository: bool = False) -> Path:
    value=Path(path).expanduser()
    repository=repository_root_containing(value)
    if repository is not None and not allow_repository:
        raise ValueError(f"La raíz de artifacts no puede estar dentro del repositorio {repository}; elegí una carpeta externa.")
    settings().setValue("artifact_root",str(value))
    settings().sync()
    return value


def impl2_historical_report_candidate() -> Path:
    return artifact_root()/"engine-physics-v1/full-rpm-sweep-v1-impl2/authorized-extension-26-v1/reports/impl2-full-rpm-sweep-30-points.json"
