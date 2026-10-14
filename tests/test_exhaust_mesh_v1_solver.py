import json
from pathlib import Path
from copy import deepcopy

import pytest

from motorsim.engine_configuration import validate
from motorsim.engine_project import load_project
from motorsim.exhaust_mesh_v1 import refine_exhaust_configuration
from motorsim.engine_variants import escape_sections,replace_escape_sections

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/"examples/projects/dino-2t-exhaust-comparison.dino2t.json"

def configured(count):
    source=load_project(PROJECT)["variants"]["Escape original"]
    base=refine_exhaust_configuration(source,[1]*5)
    return refine_exhaust_configuration(base,[count]*5)

def static_state(engine,pressure=101325.0):
    path=engine.exhaust;rows=[];species=[]
    for old,vol,sp in zip(engine.state["ducts"]["exhaust"],path.mesh.volumes,engine.state["species"]["ducts"]["exhaust"]):
        rho=old[0];q=engine.eos.conservative((rho,0.0,pressure,1.0));rows.append(q)
        scale=(q[0]*vol)/sum(sp);species.append(tuple(x*scale for x in sp))
    engine.state["ducts"]["exhaust"]=rows;engine.state["species"]["ducts"]["exhaust"]=species

def test_variable_area_pressure_source_balances_static_pressure_flux_on_internal_faces():
    for cells in (2,4):
        engine=validate(configured(cells));static_state(engine)
        assembled=engine._assemble(engine.state,0.0,3000.0)
        rhs=assembled["q"]["ducts"]["exhaust"]
        areas=engine.exhaust.mesh.areas
        assert any(abs(a-b)>1e-10*max(a,b) for a,b in zip(areas,areas[1:]))
        for i in range(1,len(rhs)-1):
            assert rhs[i][0]==pytest.approx(0.0,abs=2e-9)
            assert rhs[i][1]==pytest.approx(0.0,abs=2e-8)
            assert rhs[i][2]==pytest.approx(0.0,abs=2e-6)

def test_refined_mesh_cfl_uses_cell_width_and_rejects_oversized_step():
    engine=validate(configured(4));static_state(engine)
    assembled=engine._assemble(engine.state,0.0,3000.0)
    cfl=engine._cfl(engine.state,assembled,1e-8)
    assert 0<=cfl<=engine.max_cfl
    with pytest.raises(ValueError,match="CFL limit exceeded"):
        engine._cfl(engine.state,assembled,1.0)

def test_pressure_perturbation_launches_flux_wave_through_refined_cells():
    engine=validate(configured(2));static_state(engine)
    idx=len(engine.state["ducts"]["exhaust"])//2
    old=engine.state["ducts"]["exhaust"][idx];rho=old[0]
    engine.state["ducts"]["exhaust"][idx]=engine.eos.conservative((rho,0.0,105000.0,1.0))
    assembled=engine._assemble(engine.state,0.0,3000.0);rhs=assembled["q"]["ducts"]["exhaust"]
    assert abs(rhs[idx-1][0])+abs(rhs[idx+1][0])>0.0
    assert assembled["faces"]["exhaust"]["face_speeds"][idx]>0.0

def test_mesh_identity_changes_configuration_and_checkpoint_restart_is_exact():
    source=load_project(PROJECT)["variants"]["Escape original"]
    coarse_config=refine_exhaust_configuration(source,[1]*5)
    fine_config=refine_exhaust_configuration(source,[2]*5)
    coarse=validate(coarse_config);fine=validate(fine_config)
    snapshot=coarse.snapshot()
    with pytest.raises(ValueError,match="configuration mismatch"):
        fine.restore(snapshot)
    assert coarse.configuration_identity["configuration_sha256"]!=fine.configuration_identity["configuration_sha256"]
    continuous=validate(fine_config);restored=validate(fine_config)
    restored.restore(continuous.snapshot())
    continuous.step(1e-8,.001);restored.step(1e-8,.001)
    assert continuous.snapshot()==restored.snapshot()


def test_constant_area_exhaust_reduces_to_constant_area_finite_volume_balance():
    source=load_project(PROJECT)["variants"]["Escape original"]
    sections=escape_sections(source)
    for row in sections:
        row["inlet_diameter_mm"]=row["outlet_diameter_mm"]=30.0
    constant=replace_escape_sections(source,sections)
    engine=validate(refine_exhaust_configuration(constant,[2]*5));static_state(engine)
    assert max(engine.exhaust.mesh.areas)-min(engine.exhaust.mesh.areas)==pytest.approx(0.0,abs=1e-18)
    assembled=engine._assemble(engine.state,0.0,3000.0)
    for row in assembled["q"]["ducts"]["exhaust"][1:-1]:
        assert row[0]==pytest.approx(0.0,abs=2e-9)
        assert row[1]==pytest.approx(0.0,abs=2e-8)
        assert row[2]==pytest.approx(0.0,abs=2e-6)
