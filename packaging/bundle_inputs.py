"""Single declaration of explicit Dino bundle source/data inputs.

PyInstaller automatic third-party imports remain identified by the separately
checked build environment. Every explicit repository/data copy uses this
inventory, including dynamic external examples and license preimages.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from motorsim.source_provenance import SOURCE_POLICY_FILES, SOURCE_ROOTS, source_input_paths

ENTRY_POINTS = {"gui": "packaging/gui_entry.py", "dino": "packaging/dino_desktop_entry.py",
                "worker": "packaging/worker_entry.py"}
REPOSITORY_ROOTS = (*SOURCE_ROOTS, *SOURCE_POLICY_FILES, "packaging", "examples/projects")
FIXTURE = "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh/fixture_a_prime-mesh-0.json"
STATIC_DATA = {
    "gui": (("motorsim/theme.qss", "motorsim"), ("motorsim/ayuda.txt", "motorsim")),
    "dino": ((FIXTURE, str(PurePosixPath(FIXTURE).parent)),),
    "worker": (),
}
REQUIRED_BUILD_FILES = (
    *ENTRY_POINTS.values(), "packaging/MotorSim.spec", "packaging/build_windows.py",
    "packaging/build_provenance.py", "packaging/bundle_inputs.py",
    "packaging/requirements-build.txt", "packaging/AVISOS.txt", "packaging/INICIO-DINO.txt",
    "scripts/agents/storage_preflight.py", FIXTURE,
    "packaging/licenses/LGPL-3.0-only.txt", "packaging/licenses/GPL-3.0-only.txt",
    "packaging/licenses/SOURCES.txt",
    "examples/projects/dino-2t-starter.dino2t.json",
    "examples/projects/dino-2t-exhaust-comparison.dino2t.json",
)
POST_BUILD_FILES = (("motorsim/ayuda.txt", "LEEME.txt"), ("packaging/AVISOS.txt", "AVISOS.txt"))


def _portable_path(value: str) -> None:
    path = PurePosixPath(value)
    if (not value or not path.parts or path.is_absolute() or ".." in path.parts
            or ":" in value or "\\" in value or str(path) != value):
        raise ValueError("Input needs a safe portable relative path: " + value)


def _regular_files(base: Path):
    for path in base.rglob("*"):
        if "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".pyo"}:
            continue
        if path.is_symlink():
            raise ValueError("Symlink build input is not an explicit regular-file preimage: " + str(path))
        if path.is_file():
            yield path


def repository_input_paths(root: Path) -> list[Path]:
    root = Path(root).resolve()
    for entries in STATIC_DATA.values():
        for relative, destination in entries:
            _portable_path(relative)
            if destination != ".":
                _portable_path(destination)
    paths = set(source_input_paths(root))
    for prefix in ("packaging", "examples/projects"):
        paths.update(_regular_files(root / prefix))
    paths.update(root / rel for rel in REQUIRED_BUILD_FILES)
    paths.update(root / rel for rel, _ in POST_BUILD_FILES)
    paths.update(root / rel for entries in STATIC_DATA.values() for rel, _ in entries)
    logical = {}
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError("Symlink declared bundle input: " + relative)
        if relative.casefold() in logical and logical[relative.casefold()] != relative:
            raise ValueError("Case-colliding Windows bundle inputs: " + relative)
        logical[relative.casefold()] = relative
    missing = sorted(p.relative_to(root).as_posix() for p in paths if not p.is_file())
    if missing:
        raise FileNotFoundError("Missing declared bundle inputs: " + ", ".join(missing))
    return sorted(paths, key=lambda p: p.relative_to(root).as_posix())


@dataclass(frozen=True)
class BundleData:
    source: Path
    destination: str

    def __post_init__(self):
        if self.destination != ".":
            _portable_path(self.destination)


def bundle_data_inputs(root: Path, target: str, generated: Path) -> list[BundleData]:
    """Exactly the explicit Analysis.datas declaration consumed by the spec."""
    root = Path(root).resolve()
    if target not in STATIC_DATA:
        raise ValueError("Unknown bundle target: " + target)
    values = [BundleData(root / rel, destination) for rel, destination in STATIC_DATA[target]]
    if target == "dino":
        values.extend(BundleData(path, path.parent.relative_to(root).as_posix())
                      for path in source_input_paths(root))
    if target in {"gui", "dino"}:
        values.append(BundleData(Path(generated) / "build.json", "motorsim"))
    return values


def git_input_scope(root: Path, consumed=()) -> list[str]:
    """Directory coverage detects new/deleted inputs as well as enumerated files."""
    root = Path(root).resolve()
    scope = set(REPOSITORY_ROOTS) | set(REQUIRED_BUILD_FILES)
    scope.update(rel for entries in STATIC_DATA.values() for rel, _ in entries)
    scope.update(rel for rel, _ in POST_BUILD_FILES)
    for relative in scope:
        _portable_path(relative)
    for item in consumed:
        try:
            scope.add(Path(item.source).resolve().relative_to(root).as_posix())
        except ValueError:
            pass  # External inputs have raw-byte provenance, not a Git claim.
    return sorted(scope)


@dataclass(frozen=True)
class ConsumedInput:
    source: Path
    logical_path: str
    bundle_path: str | None = None

    def __post_init__(self):
        for value in (self.logical_path, self.bundle_path):
            if value is not None:
                _portable_path(value)


def directory_inputs(source: Path, logical_prefix: str, bundle_prefix: str) -> list[ConsumedInput]:
    source = Path(source).resolve()
    if not source.is_dir():
        raise FileNotFoundError("Missing consumed directory: " + str(source))
    # Copy plans enumerate all regular source files; no later copytree discovery.
    inputs = []
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlink external input is not supported: " + str(path))
        if path.is_file():
            relative = path.relative_to(source).as_posix()
            inputs.append(ConsumedInput(path, logical_prefix + "/" + relative,
                                        bundle_prefix + "/" + relative))
    return inputs
