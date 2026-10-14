import json
import math
from pathlib import Path

import pytest

from motorsim.engine_configuration import identity, validate
from motorsim.exhaust_mesh_v1 import IDENTITY, refine_exhaust_configuration
from motorsim.engine_project import load_project, create_project, save_project

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/"examples/projects/dino-2t-exhaust-comparison.dino2t.json"

def base():
    return load_project(PROJECT)["variants"]["Escape original"]

def conserved(config):
    native=config["native_configuration"]
    duct=next(d for d in native["ducts"] if d["id"]=="exhaust")
    gamma=native["eos"]["gamma"]
    mass=energy=0.0
    for (rho,u,p,_),v in zip(native["initial_duct_states"]["exhaust"],duct["mesh"]["volumes"]):
        mass+=rho*v;energy+=(p/(gamma-1)+.5*rho*u*u)*v
    species=[sum(row[k] for row in native["duct_species"]["exhaust"]) for k in range(4)]
    return mass,energy,species

def test_one_two_four_cell_frusta_conserve_geometry_and_interfaces():
    source=base();sections=source["native_configuration"]["geometry_identity"]["chamber"]["sections"]
    for count in (1,2,4):
        refined=refine_exhaust_configuration(source,[count]*len(sections))
        engine=validate(refined);duct=engine.exhaust
        assert duct.mesh.n==count*len(sections)
        assert duct.mesh.faces[0]==validate(source).exhaust.mesh.faces[0]
        assert duct.mesh.faces[-1]-duct.mesh.faces[0]==pytest.approx(sum(x["length_mm"] for x in sections)/1000)
        for si,section in enumerate(sections):
            a,b=sum([count]*si),sum([count]*si)+count
            d0=section["inlet_diameter_mm"]/1000;d1=section["outlet_diameter_mm"]/1000
            assert duct.mesh.areas[a]==pytest.approx(math.pi*d0*d0/4,rel=1e-13)
            assert duct.mesh.areas[b]==pytest.approx(math.pi*d1*d1/4,rel=1e-13)
            length=section["length_mm"]/1000
            exact=math.pi*length*(d0*d0+d0*d1+d1*d1)/12
            assert sum(duct.mesh.volumes[a:b])==pytest.approx(exact,rel=2e-14)
            assert all(duct.mesh.faces[k]<duct.mesh.centers[k]<duct.mesh.faces[k+1] for k in range(a,b))
        for si in range(len(sections)-1):
            face=(si+1)*count
            d=sections[si]["outlet_diameter_mm"]/1000
            assert sections[si]["outlet_diameter_mm"]==pytest.approx(sections[si+1]["inlet_diameter_mm"])
            assert duct.mesh.areas[face]==pytest.approx(math.pi*d*d/4,rel=1e-13)
        meta=refined["native_configuration"]["geometry_identity"]["exhaust_mesh_discretization"]
        assert meta["schema"]==IDENTITY and meta["cells_per_section"]==[count]*len(sections)
        assert len(meta["adapter_sha256"])==len(meta["discrete_geometry_sha256"])==64
        assert identity(refined)!=identity(source)

def test_state_species_and_energy_conserved_across_nested_refinement():
    source=base();expected=conserved(source)
    one=refine_exhaust_configuration(source,[1]*5)
    two=refine_exhaust_configuration(one,[2]*5)
    four=refine_exhaust_configuration(two,[4]*5)
    coarse=refine_exhaust_configuration(four,[1]*5)
    for result in (one,two,four,coarse):
        actual=conserved(result)
        assert actual[0]==pytest.approx(expected[0],rel=2e-14)
        assert actual[1]==pytest.approx(expected[1],rel=2e-14)
        assert actual[2]==pytest.approx(expected[2],rel=2e-14)
        validate(result)

def test_per_section_resolution_project_roundtrip_and_reproducibility(tmp_path):
    source=base();sections=source["native_configuration"]["geometry_identity"]["chamber"]["sections"]
    resolutions=[1,2,4,2,1]
    a=refine_exhaust_configuration(source,resolutions)
    b=refine_exhaust_configuration(source,resolutions)
    assert a==b
    project=create_project("mesh-v1",a)
    path=tmp_path/"project.json";save_project(path,project)
    assert load_project(path)==project

def test_invalid_resolution_and_incompatible_mesh_metadata_fail_closed():
    source=base()
    for invalid in ([0]*5,[3]*5,[True]*5,[1]*4):
        with pytest.raises(ValueError):refine_exhaust_configuration(source,invalid)
    changed=refine_exhaust_configuration(source,[2]*5)
    changed["native_configuration"]["geometry_identity"]["exhaust_mesh_discretization"]["cells_per_section"][0]=4
    from motorsim.engine_configuration import sha256
    changed["native_configuration_sha256"]=sha256(changed["native_configuration"])
    with pytest.raises(ValueError,match="geometry hash mismatch"):
        refine_exhaust_configuration(changed,[1]*5)
    stale=refine_exhaust_configuration(source,[2]*5)
    stale["native_configuration"]["geometry_identity"]["exhaust_mesh_discretization"]["adapter_sha256"]="0"*64
    from motorsim.engine_configuration import sha256
    stale["native_configuration_sha256"]=sha256(stale["native_configuration"])
    with pytest.raises(ValueError,match="adapter source hash mismatch"):
        refine_exhaust_configuration(stale,[4]*5)

def test_legacy_one_cell_adapter_remains_unchanged():
    from motorsim.engine_variants import replace_escape_sections,escape_sections
    source=base();legacy=replace_escape_sections(source,escape_sections(source))
    assert "exhaust_mesh_discretization" not in legacy["native_configuration"]["geometry_identity"]
    assert validate(legacy).exhaust.mesh.n==5
