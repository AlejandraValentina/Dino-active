import pytest

from motorsim.integrated_2t import IntegratedEngine2T
from scripts.diagnostics.boundary_truncation_reference_v1 import fixture,cell_means,diagnose


def test_quadrature_reference_is_resolved_independently():
    e,m=fixture(20)
    a,b=cell_means(m,e.eos,8),cell_means(m,e.eos,16)
    for x,y in zip(a,b):assert x==pytest.approx(y,rel=1e-12)


@pytest.mark.parametrize('n',[20,40,80])
def test_isentropic_mass_energy_and_exact_face_connection(n,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('no time integration allowed')
    monkeypatch.setattr(IntegratedEngine2T,'step',forbidden)
    r=diagnose(n)
    assert r['analytical_mass_flux_spread']<1e-12
    assert r['analytical_energy_flux_spread']<1e-12
    assert r['port_exact_face_relative_mass_flux_error']<1e-10
