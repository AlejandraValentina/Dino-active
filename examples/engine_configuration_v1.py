"""No-step example for the versioned IntegratedEngine2T configuration API."""
import json
from pathlib import Path

from motorsim.engine_configuration import create, identity
from motorsim.engine_variants import escape_sections, replace_escape_sections
from motorsim.engine_project import create_project, save_project, compare_project_engines

ROOT = Path(__file__).resolve().parents[1]
fixture_path = ROOT / "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh/fixture_a_prime-mesh-0.json"
fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
engine = create(
    native_configuration=fixture["engine_configuration"],
    mechanical_loss_model=fixture["mechanical_loss_model"],
    operating_conditions={"reference_rpm": 3000, "load": 1.0,
                          "fuel_id": fixture["fuel_surrogate_snapshot"]["sha256"], "afr": 49.0},
    provenance={"configuration_source": {"path": str(fixture_path.relative_to(ROOT)),
                                           "classification": fixture["classification"]},
                "fuel": fixture["fuel_surrogate_snapshot"]},
    display_name="Synthetic fixture A",
)
sections = escape_sections(engine)
sections[1]["length_mm"] += 10.0
variant_engine = replace_escape_sections(engine, sections, display_name="Longer diffuser")
project = create_project("example-project", engine, variants={"longer-diffuser": variant_engine})
destination = Path("engine-project-example.json")
save_project(destination, project)
print(json.dumps({"base_identity": identity(engine),
                  "variant_diff": compare_project_engines(project, "longer-diffuser"),
                  "project_file": str(destination)}, indent=2))
