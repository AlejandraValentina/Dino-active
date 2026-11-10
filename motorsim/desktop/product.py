"""Commercial product identity, diagnostics, recent projects and recovery."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import zipfile

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QTabWidget,
                               QTextBrowser, QVBoxLayout, QWidget)

from ..runtime import APP_VERSION, build_info
from .preferences import default_artifact_root, repository_root_containing, settings

SCIENTIFIC_STATUS = {
    "calibration": "NOT_PERFORMED",
    "experimental_validation": "NOT_PERFORMED",
    "predictive_capability": "NOT_CLAIMED",
}
PROJECT_SCHEMAS = {
    "2T": "MOTORSIM_ENGINE_PROJECT_V3",
    "4T_0D": "MOTORSIM_4T_REFERENCE_PROJECT_V1",
    "4T_native": "DINO_DESKTOP_ENGINE_PROJECT_4T_V1",
}


def recovery_root() -> Path:
    """Recovery/autosave root outside the repository, honoring E: policy overrides.

    ``DINO_RECOVERY_ROOT`` is the most specific override; otherwise the durable
    ``DINO_ARTIFACT_ROOT`` (or the normal artifact root) is used.  A root inside
    a Git worktree is rejected so recovery never dirties the source tree.
    """
    explicit = os.environ.get("DINO_RECOVERY_ROOT")
    artifact = os.environ.get("DINO_ARTIFACT_ROOT")
    if explicit:
        root = Path(explicit).expanduser()
    elif artifact:
        root = Path(artifact).expanduser() / "recovery"
    else:
        root = default_artifact_root() / "recovery"
    if repository_root_containing(root) is not None:
        root = default_artifact_root() / "recovery"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_metadata() -> dict:
    try:
        return dict(build_info())
    except Exception:
        pass
    candidates = []
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        candidates.append(Path(frozen_root) / "build.json")
    candidates.extend([
        Path(sys.executable).resolve().parent / "build.json",
        Path(sys.executable).resolve().parent / "_internal" / "build.json",
        Path(__file__).resolve().parents[1] / "build.json",
        Path(__file__).resolve().parents[2] / "build.json",
    ])
    for candidate in candidates:
        try:
            if candidate.is_file():
                value = json.loads(candidate.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    return value
        except (OSError, ValueError):
            continue
    return {"app_version": APP_VERSION, "source_commit": "NOT_AVAILABLE",
            "trial": True, "packaged_inputs_clean": False}


def _license_names() -> list[str]:
    roots = [
        Path(sys.executable).resolve().parent / "Licencias",
        Path(__file__).resolve().parents[2] / "packaging" / "licenses",
        Path(sys.executable).resolve().parent / "packaging" / "licenses",
    ]
    names = set()
    for root in roots:
        if root.is_dir():
            for item in root.rglob("*"):
                if item.is_file():
                    names.add(item.relative_to(root).as_posix())
    return sorted(names)


def product_info() -> dict:
    build = _build_metadata()
    version = build.get("app_version") or APP_VERSION
    return {
        "schema": "DINO_PRODUCT_INFO_V1",
        "product": "Dino Desktop",
        "version": version,
        "source_commit": build.get("source_commit"),
        "trial": bool(build.get("trial", True)),
        "build": build,
        "project_schemas": dict(PROJECT_SCHEMAS),
        "scientific_status": dict(SCIENTIFIC_STATUS),
        "licenses": _license_names(),
        "support": "Soporte: distribuidor autorizado y documentación de la licencia.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


class AboutDialog(QDialog):
    def __init__(self, info=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acerca de Dino Desktop")
        self.resize(720, 520)
        info = info or product_info()
        layout = QVBoxLayout(self)
        title = QLabel(f"Dino Desktop {info['version']}")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)
        tabs = QTabWidget()
        tabs.addTab(_text_page(self._product_text(info)), "Producto")
        tabs.addTab(_text_page(self._build_text(info)), "Build y procedencia")
        tabs.addTab(_text_page(self._science_text(info)), "Estado científico")
        tabs.addTab(_text_page(self._license_text(info)), "Licencias")
        tabs.addTab(_text_page(self._support_text(info)), "Soporte")
        layout.addWidget(tabs, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @staticmethod
    def _product_text(info):
        return (f"Producto: {info['product']}\n"
                f"Versión: {info['version']}\n"
                f"Commit: {info.get('source_commit') or 'no identificado'}\n"
                f"TRIAL: {'sí' if info.get('trial') else 'no'}\n\n"
                "Dino es una herramienta de ingeniería. La funcionalidad comercial "
                "no equivale a validación experimental, calibración ni capacidad "
                "predictiva.")

    @staticmethod
    def _build_text(info):
        build = info.get("build") or {}
        lines = [f"{key}: {value}" for key, value in sorted(build.items())
                 if isinstance(value, (str, int, float, bool)) or value is None]
        return "\n".join(lines) or "Sin metadatos de build."

    @staticmethod
    def _science_text(info):
        status = info.get("scientific_status") or {}
        return ("\n".join(f"{key}: {value}" for key, value in status.items())
                + "\n\nLos resultados sintéticos y las diferencias de diseño no "
                  "son validación experimental ni mejora demostrada.")

    @staticmethod
    def _license_text(info):
        names = info.get("licenses") or []
        if not names:
            return "No se encontraron avisos de licencias junto a esta instalación."
        return "Componentes y avisos incluidos:\n" + "\n".join(names)

    @staticmethod
    def _support_text(info):
        return (f"{info.get('support', 'Soporte no declarado.')}\n\n"
                "Para soporte, exporte un diagnóstico desde el menú Ayuda. "
                "El diagnóstico no se envía automáticamente ni incluye telemetría.")


def _text_page(text):
    page = QWidget()
    layout = QVBoxLayout(page)
    browser = QTextBrowser()
    browser.setPlainText(text)
    layout.addWidget(browser)
    return page


def _system_info() -> dict:
    return {
        "platform": platform.platform(),
        "python": sys.version,
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
        "frozen": bool(getattr(sys, "frozen", False)),
        "cwd": os.getcwd(),
        "app_version": APP_VERSION,
    }


def _safe_settings() -> dict:
    result = {}
    try:
        store = settings()
        for key in ("artifact_root", "last_page"):
            value = store.value(key)
            if isinstance(value, (str, int, float, bool)) or value is None:
                result[key] = value
        result["recent_families"] = sorted(
            key.split("/", 1)[1] for key in store.allKeys()
            if key.startswith("recent/"))
    except Exception:
        pass
    return result


def _recent_logs(limit=4, max_bytes=200_000) -> list[tuple[str, bytes]]:
    roots = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        roots.append(Path(local) / "MotorSim" / "Diagnostico")
    roots.append(default_artifact_root() / "logs")
    files = []
    for root in roots:
        try:
            if root.is_dir():
                files.extend(item for item in root.glob("*.txt") if item.is_file())
                files.extend(item for item in root.glob("*.log") if item.is_file())
        except OSError:
            continue
    files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    values = []
    for item in files[:limit]:
        try:
            raw = item.read_bytes()[-max_bytes:]
        except OSError:
            continue
        values.append((item.name, raw))
    return values


def create_diagnostics_bundle(path, *, include_project=None, project=None,
                              settings_snapshot=None, log_limit=4) -> Path:
    target = Path(path)
    if target.suffix.lower() != ".zip":
        target = target.with_suffix(".zip")
    target.parent.mkdir(parents=True, exist_ok=True)
    info = product_info()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("product.json", json.dumps(info, ensure_ascii=False, indent=2))
        bundle.writestr("build.json", json.dumps(info.get("build") or {}, ensure_ascii=False, indent=2))
        bundle.writestr("system.json", json.dumps(_system_info(), ensure_ascii=False, indent=2))
        snapshot = settings_snapshot if settings_snapshot is not None else _safe_settings()
        bundle.writestr("settings.json", json.dumps(snapshot, ensure_ascii=False, indent=2))
        if include_project and project is not None:
            bundle.writestr("project.json", json.dumps(project, ensure_ascii=False, indent=2,
                                                       allow_nan=False))
        for name, raw in _recent_logs(log_limit):
            bundle.writestr("logs/" + name, raw)
        bundle.writestr("README.txt",
                        "Diagnóstico de Dino Desktop. No incluye credenciales ni "
                        "telemetría. El proyecto sólo se incluye si el usuario lo "
                        "autorizó. Revise el contenido antes de compartirlo.\n")
    return target


class RecentProjects:
    LIMIT = 8

    def __init__(self, store=None):
        self.store = store or settings()

    @staticmethod
    def _key(family):
        return f"recent/{family}"

    def items(self, family) -> list[str]:
        value = self.store.value(self._key(family), [])
        if isinstance(value, str):
            values = [value]
        elif isinstance(value, (list, tuple)):
            values = [str(item) for item in value]
        else:
            values = []
        seen, result = set(), []
        for item in values:
            path = str(Path(item).expanduser())
            if path not in seen:
                seen.add(path)
                result.append(path)
        return result[:self.LIMIT]

    def add(self, family, path) -> list[str]:
        target = str(Path(path).expanduser().resolve())
        values = [item for item in self.items(family) if item != target]
        values.insert(0, target)
        values = values[:self.LIMIT]
        self.store.setValue(self._key(family), values)
        self.store.sync()
        return values

    def prune(self, family) -> list[str]:
        values = [item for item in self.items(family) if Path(item).is_file()]
        self.store.setValue(self._key(family), values)
        self.store.sync()
        return values

    def clear(self, family):
        self.store.remove(self._key(family))
        self.store.sync()


class RecoveryController(QObject):
    SCHEMA = "DINO_RECOVERY_V1"

    def __init__(self, family, context, serialize, parent=None, interval_ms=15000):
        super().__init__(parent)
        self.family = str(family)
        self.context = context
        self.serialize = serialize
        self.timer = QTimer(self)
        self.timer.setInterval(interval_ms)
        self.timer.timeout.connect(self.autosave)
        self.timer.start()

    def _root(self) -> Path:
        return recovery_root()

    def _project_id(self) -> str:
        project = getattr(self.context, "project", {})
        if isinstance(project, dict):
            value = project.get("project_id") or project.get("name")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "proyecto"

    def path(self) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in self._project_id())
        return self._root() / f"{self.family}-{safe[:80]}.json"

    def autosave(self) -> Path | None:
        if not getattr(self.context, "dirty", False):
            return None
        project = self.serialize()
        payload = {
            "schema": self.SCHEMA,
            "family": self.family,
            "project_id": self._project_id(),
            "original_path": str(self.context.path) if getattr(self.context, "path", None) else None,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "project": project,
        }
        target = self.path()
        fd, temporary = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, allow_nan=False, indent=1)
            os.replace(temporary, target)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
        return target

    def clear(self):
        try:
            self.path().unlink(missing_ok=True)
        except OSError:
            pass

    @classmethod
    def pending(cls, family) -> list[dict]:
        root = recovery_root()
        if not root.is_dir():
            return []
        entries = []
        for item in root.glob(f"{family}-*.json"):
            try:
                payload = json.loads(item.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(payload, dict) and payload.get("schema") == cls.SCHEMA:
                payload["_path"] = str(item)
                entries.append(payload)
        entries.sort(key=lambda item: str(item.get("saved_at", "")), reverse=True)
        return entries

    @classmethod
    def discard(cls, family, project_id=None):
        for payload in cls.pending(family):
            if project_id is None or payload.get("project_id") == project_id:
                try:
                    Path(payload["_path"]).unlink(missing_ok=True)
                except OSError:
                    pass
