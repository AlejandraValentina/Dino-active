import json

import pytest

from motorsim.fuel_library import (
    FuelDefinition, FuelLibrary, FuelSimulationSnapshot, FuelSource,
    builtin_defaults,
)


def user_fuel(**changes):
    values = dict(
        id="test-fuel", version="1.0.0", display_name="Test fuel",
        family_category="SYNTHETIC_HYDROCARBON",
        provenance="MODELED_SURROGATE", builtin=False, enabled=True,
        ron=100.0, density_kg_m3=690.0, lower_heating_value_j_kg=44_000_000.0,
        stoichiometric_afr=None,
        elemental_mass_fractions={"C": 0.8421052631578947,
                                  "H": 0.15789473684210525},
        oxygen_fraction=None, oxygen_fraction_basis=None,
        ethanol_fraction=None, ethanol_fraction_basis=None,
        reference_temperature_K=293.15,
        sources=(FuelSource("Synthetic fixture", "https://example.invalid/fuel",
                            "2026-10-06", "test-only fixture, not a real fuel"),),
        note="Test fixture.",
    )
    values.update(changes)
    return FuelDefinition(**values)


def test_elemental_composition_derives_stoichiometry_with_versioned_method():
    definition = user_fuel()
    assert definition.effective_stoichiometric_afr == pytest.approx(15.07, abs=0.03)
    assert definition.missing_combustion_properties() == ()
    assert definition.to_dict()["schema"] == "FUEL_DEFINITION_V1"
    explicit = user_fuel(stoichiometric_afr=14.7,
                         stoichiometry_method_version="EXPLICIT_STOICHIOMETRIC_AFR_V1")
    assert explicit.effective_stoichiometric_afr == 14.7


def test_uruguay_builtins_record_only_documented_identity_and_known_ron():
    profiles = {fuel.id: fuel for fuel in builtin_defaults()}
    super95 = profiles["ANCAP_SUPER_95"]
    premium97 = profiles["ANCAP_PREMIUM_97"]
    assert (super95.id, super95.ron) == ("ANCAP_SUPER_95", 95.0)
    assert (premium97.id, premium97.ron) == ("ANCAP_PREMIUM_97", 97.0)
    for fuel in (super95, premium97):
        assert fuel.density_kg_m3 is None
        assert fuel.lower_heating_value_j_kg is None
        assert fuel.stoichiometric_afr is None
        assert fuel.ethanol_fraction is None  # source publishes a maximum only
        assert fuel.effective_stoichiometric_afr is None
        assert fuel.missing_combustion_properties()


def test_pure_isooctane_surrogate_is_explicit_and_not_an_ancap_fuel():
    surrogate = next(fuel for fuel in builtin_defaults()
                     if fuel.id == "MOTORSIM_ISOOCTANE_SURROGATE_V1")
    assert surrogate.provenance == "MODELED_SURROGATE"
    assert surrogate.ron is None
    assert surrogate.reference_temperature_K == 293.15
    assert surrogate.density_kg_m3 == 691.853
    assert surrogate.lower_heating_value_j_kg == pytest.approx(44_343_551.3904)
    assert surrogate.effective_stoichiometric_afr == pytest.approx(15.0923574, abs=1e-7)
    assert surrogate.missing_combustion_properties() == ()
    assert "not ANCAP" in surrogate.note
    assert "LHV is derived" in surrogate.sources[0].claim


def test_snapshot_freezes_identity_version_and_full_definition():
    elemental = {"C": 0.8421052631578947, "H": 0.15789473684210525}
    original = user_fuel(elemental_mass_fractions=elemental)
    elemental["C"] = 0.0  # caller mutation cannot rewrite the stored record
    assert original.elemental_mass_fractions["C"] == pytest.approx(0.8421052631578947)
    with pytest.raises(TypeError):
        original.elemental_mass_fractions["C"] = 0.5
    snapshot = FuelSimulationSnapshot.freeze(original)
    frozen = FuelSimulationSnapshot.from_dict(snapshot.to_dict())
    assert frozen.validate() == original
    with pytest.raises(ValueError, match="hash"):
        FuelSimulationSnapshot(snapshot.fuel_id, snapshot.version,
                               snapshot.content_hash, snapshot.full_definition + " ").validate()
    library = FuelLibrary()
    library.create(original)
    updated = user_fuel(version="1.0.1", lower_heating_value_j_kg=45_000_000.0)
    library.edit_user(updated)
    assert FuelSimulationSnapshot.from_dict(snapshot.to_dict()).validate() == original
    assert library.freeze(original.id).validate() == updated


def test_library_lifecycle_and_atomic_persistence(tmp_path):
    library = FuelLibrary()
    library.create(user_fuel())
    copied = library.duplicate("test-fuel", new_id="test-fuel-copy", new_version="1.0.0")
    assert copied.provenance == "USER_DEFINED_UNVERIFIED"
    assert copied.id == "test-fuel-copy"

    exported = library.export_user_fuel(copied.id)
    other = FuelLibrary()
    imported = other.import_user_fuel(exported)
    assert imported == copied
    with pytest.raises(ValueError, match="already exists"):
        other.import_user_fuel(exported)

    path = tmp_path / "fuel-library.json"
    library.set_enabled("ANCAP_SUPER_95", False)
    library.save(path)
    loaded = FuelLibrary.load(path)
    assert not loaded.get("ANCAP_SUPER_95").enabled
    with pytest.raises(ValueError, match="disabled"):
        loaded.freeze("ANCAP_SUPER_95")
    loaded.restore_defaults()
    assert loaded.get("ANCAP_SUPER_95").enabled
    loaded.delete_user("test-fuel-copy")
    with pytest.raises(KeyError):
        loaded.get("test-fuel-copy")
    with pytest.raises(ValueError, match="physically deleted"):
        loaded.delete_user("ANCAP_SUPER_95")
    assert json.loads(path.read_text(encoding="utf-8"))["schema"] == "FUEL_LIBRARY_V1"


@pytest.mark.parametrize("changes", [
    {"ron": True},
    {"density_kg_m3": 0.0},
    {"lower_heating_value_j_kg": float("inf")},
    {"ethanol_fraction": 0.1},  # requires a basis
    {"oxygen_fraction": 0.03},  # requires a basis
    {"elemental_mass_fractions": {"C": 0.5, "H": 0.4}},
])
def test_invalid_properties_and_provenance_are_rejected(changes):
    with pytest.raises(ValueError):
        user_fuel(**changes).validate()


def test_library_cannot_replace_builtin_record_or_create_user_over_builtin_id():
    library = FuelLibrary()
    with pytest.raises(ValueError, match="immutable"):
        FuelLibrary((user_fuel(id="ANCAP_SUPER_95", provenance="USER_DEFINED_UNVERIFIED"),))
    with pytest.raises(ValueError, match="built-in"):
        library.create(user_fuel(id="new-built-in", builtin=True))


def test_user_edit_must_advance_version_and_keep_user_identity():
    library = FuelLibrary()
    library.create(user_fuel())
    with pytest.raises(ValueError, match="increment"):
        library.edit_user(user_fuel())
    with pytest.raises(ValueError, match="increment"):
        library.edit_user(user_fuel(version="1.0.1", builtin=True))
