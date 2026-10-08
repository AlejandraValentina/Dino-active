"""Regenerate canonical KT100SP provenance and synthetic fixture JSON."""
import argparse
import json
from pathlib import Path

from motorsim.kt100_reference import build_fixture_config, build_provenance_manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    reference = args.root / "configs" / "reference"
    fixture = args.root / "configs" / "fixtures"
    reference.mkdir(parents=True, exist_ok=True)
    fixture.mkdir(parents=True, exist_ok=True)
    outputs = {
        reference / "kt100_reference_v1_provenance.json": build_provenance_manifest(),
        fixture / "kt100_model_fixture_v1.json": build_fixture_config(),
    }
    for path, data in outputs.items():
        path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                   indent=2, allow_nan=False)+"\n", encoding="utf-8")
        print(path.relative_to(args.root))


if __name__ == "__main__":
    main()
